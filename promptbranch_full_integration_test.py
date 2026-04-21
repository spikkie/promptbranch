from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from dotenv import load_dotenv

from promptbranch_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings
from promptbranch_service_client import ChatGPTServiceClient
from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
)

DEFAULT_PROJECT_URL = "https://chatgpt.com/"
DEFAULT_PROFILE_DIR = "./profile"
DEFAULT_MAX_RETRIES = 1

CANONICAL_STEP_ORDER: tuple[str, ...] = (
    "login_check",
    "project_resolve_before_create",
    "project_ensure_create_or_reuse",
    "project_ensure_idempotent",
    "project_resolve_after_ensure",
    "project_source_capabilities",
    "project_source_add_link",
    "project_source_add_text",
    "project_source_add_file",
    "ask_question",
    "project_source_remove_link",
    "project_source_remove_text",
    "project_source_remove_file",
    "project_remove_cleanup",
)
OPTIONAL_STEP_ORDER: tuple[str, ...] = (
    "project_list_debug",
)
FULL_STEP_ORDER: tuple[str, ...] = CANONICAL_STEP_ORDER + OPTIONAL_STEP_ORDER

STEP_ALIASES: dict[str, tuple[str, ...]] = {
    "all": CANONICAL_STEP_ORDER,
    "project_list": ("project_list_debug",),
    "project_list_debug": ("project_list_debug",),
    "login": ("login_check",),
    "project_ensure": (
        "project_resolve_before_create",
        "project_ensure_create_or_reuse",
        "project_ensure_idempotent",
        "project_resolve_after_ensure",
    ),
    "source_capabilities": ("project_source_capabilities",),
    "source_add_link": ("project_source_add_link",),
    "source_add_text": ("project_source_add_text",),
    "source_add_file": ("project_source_add_file",),
    "source_remove_link": ("project_source_remove_link",),
    "source_remove_text": ("project_source_remove_text",),
    "source_remove_file": ("project_source_remove_file",),
    "source_add": (
        "project_source_add_link",
        "project_source_add_text",
        "project_source_add_file",
    ),
    "source_remove": (
        "project_source_remove_link",
        "project_source_remove_text",
        "project_source_remove_file",
    ),
    "ask": ("ask_question",),
    "project_remove": ("project_remove_cleanup",),
    "cleanup": ("project_remove_cleanup",),
}

SOURCE_FLOW_STEPS = {
    "project_source_add_link",
    "project_source_add_text",
    "project_source_add_file",
    "project_source_remove_link",
    "project_source_remove_text",
    "project_source_remove_file",
}
PROJECT_CONTEXT_REQUIRED_STEPS = {
    "project_source_capabilities",
    *SOURCE_FLOW_STEPS,
    "ask_question",
    "project_remove_cleanup",
}
REMOVAL_STEPS = {
    "project_source_remove_link",
    "project_source_remove_text",
    "project_source_remove_file",
}
ALLOWED_STEP_TOKENS = set(FULL_STEP_ORDER) | set(STEP_ALIASES)


@dataclass
class StepResult:
    name: str
    ok: bool
    duration_seconds: float
    details: Any


@dataclass(frozen=True)
class StepSelection:
    requested_only: tuple[str, ...]
    requested_skip: tuple[str, ...]
    enabled_steps: tuple[str, ...]


class IntegrationAssertionError(RuntimeError):
    pass


def _record_step(steps: list[StepResult], name: str, *, ok: bool, details: Any, duration_seconds: float = 0.0) -> Any:
    steps.append(
        StepResult(
            name=name,
            ok=ok,
            duration_seconds=round(duration_seconds, 3),
            details=details,
        )
    )
    return details


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _configure_logging(debug: bool) -> None:
    import logging

    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )



def _split_step_tokens(values: Sequence[str]) -> tuple[str, ...]:
    tokens: list[str] = []
    for value in values:
        for token in value.split(","):
            normalized = token.strip()
            if normalized:
                tokens.append(normalized)
    return tuple(tokens)



def _expand_step_token(token: str) -> tuple[str, ...]:
    if token in STEP_ALIASES:
        return STEP_ALIASES[token]
    if token in FULL_STEP_ORDER:
        return (token,)
    raise ValueError(f"Unknown step selector: {token}")



def resolve_step_selection(
    *,
    only_values: Sequence[str],
    skip_values: Sequence[str],
    keep_project: bool = False,
) -> StepSelection:
    requested_only = _split_step_tokens(only_values)
    requested_skip = _split_step_tokens(skip_values)

    invalid = [token for token in (*requested_only, *requested_skip) if token not in ALLOWED_STEP_TOKENS]
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_STEP_TOKENS))
        raise ValueError(f"Unknown step selector(s): {', '.join(sorted(set(invalid)))}. Allowed values: {allowed}")

    enabled = set(CANONICAL_STEP_ORDER if not requested_only else ())
    if requested_only:
        for token in requested_only:
            enabled.update(_expand_step_token(token))

    for token in requested_skip:
        enabled.difference_update(_expand_step_token(token))

    if keep_project:
        enabled.discard("project_remove_cleanup")

    if enabled - {"project_remove_cleanup"}:
        enabled.add("login_check")

    if enabled & SOURCE_FLOW_STEPS:
        enabled.add("project_source_capabilities")

    enabled_steps = tuple(step for step in FULL_STEP_ORDER if step in enabled)
    if not enabled_steps:
        raise ValueError("No steps remain after applying --only/--skip/--keep-project")

    return StepSelection(
        requested_only=requested_only,
        requested_skip=requested_skip,
        enabled_steps=enabled_steps,
    )



def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a full ChatGPT integration flow against either the direct Python automation stack or the Docker HTTP service. "
            "This script exercises login, project ensure/resolve/remove, project sources (link/text/file), and ask()."
        )
    )
    parser.add_argument("--dotenv", default=".env", help="Optional .env file to load before reading env vars.")
    parser.add_argument("--project-url", default=os.getenv("CHATGPT_PROJECT_URL", DEFAULT_PROJECT_URL))
    parser.add_argument("--email", default=os.getenv("CHATGPT_EMAIL"))
    parser.add_argument("--password", default=os.getenv("CHATGPT_PASSWORD"))
    parser.add_argument("--password-file", default=os.getenv("CHATGPT_PASSWORD_FILE"))
    parser.add_argument("--profile-dir", default=os.getenv("CHATGPT_PROFILE_DIR", DEFAULT_PROFILE_DIR))
    parser.add_argument("--headless", action="store_true", default=_env_flag("CHATGPT_HEADLESS", False))
    parser.add_argument("--use-playwright", action="store_true", help="Use playwright instead of patchright.")
    parser.add_argument("--browser-channel", default=os.getenv("CHATGPT_BROWSER_CHANNEL"))
    parser.add_argument("--enable-fedcm", action="store_true", help="Do not disable FedCM browser flags.")
    parser.add_argument("--keep-no-sandbox", action="store_true", help="Keep default no-sandbox args instead of filtering them.")
    parser.add_argument("--max-retries", type=int, default=int(os.getenv("CHATGPT_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))))
    parser.add_argument("--retry-backoff-seconds", type=float, default=float(os.getenv("CHATGPT_RETRY_BACKOFF_SECONDS", "2.0")))
    parser.add_argument("--debug", action="store_true", default=_env_flag("CHATGPT_DEBUG", True))
    parser.add_argument("--keep-open", action="store_true", help="Pass keep_open through to each browser action.")
    parser.add_argument("--keep-project", action="store_true", help="Do not delete the test project at the end.")
    parser.add_argument("--step-delay-seconds", type=float, default=float(os.getenv("CHATGPT_STEP_DELAY_SECONDS", "8.0")), help="Delay inserted before each step after the first to reduce ChatGPT rate-limit pressure during end-to-end runs.")
    parser.add_argument("--skip", action="append", default=[], help="Comma-separated step selectors to skip.")
    parser.add_argument("--only", action="append", default=[], help="Comma-separated step selectors to run.")
    parser.add_argument("--strict-remove-ui", action="store_true", help="Require at least one source removal to succeed through the actual UI path.")
    parser.add_argument("--project-name", help="Explicit project name to use. Defaults to a generated unique name.")
    parser.add_argument("--project-name-prefix", default="itest-promptbranch")
    parser.add_argument("--run-id", help="Optional run identifier used when generating names.")
    parser.add_argument("--memory-mode", choices=["default", "project-only"], default="default")
    parser.add_argument("--link-url", default="https://example.com/")
    parser.add_argument("--ask-prompt", default="Reply with exactly the single token INTEGRATION_OK and nothing else.")
    parser.add_argument("--json-out", help="Optional file path where the final JSON summary will be written.")
    parser.add_argument("--project-list-debug-scroll-rounds", type=int, default=12, help="Scroll rounds for the local project-list debug step.")
    parser.add_argument("--project-list-debug-wait-ms", type=int, default=350, help="Per-round wait in milliseconds for the local project-list debug step.")
    parser.add_argument("--project-list-debug-manual-pause", action="store_true", help="Pause between project-list debug phases in headed local runs.")
    parser.add_argument("--service-base-url", default=os.getenv("CHATGPT_SERVICE_BASE_URL"), help="Optional Docker service base URL, e.g. http://localhost:8000. When set, this script runs against the HTTP service instead of importing the browser automation directly.")
    parser.add_argument("--service-token", default=os.getenv("CHATGPT_SERVICE_TOKEN") or os.getenv("CHATGPT_API_TOKEN"), help="Optional bearer token for the Docker service.")
    parser.add_argument("--service-timeout-seconds", type=float, default=float(os.getenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", "300.0")), help="HTTP timeout when running against the Docker service.")
    parser.add_argument("--clear-singleton-locks", action="store_true", help="Clear stale Chrome Singleton* lock artifacts from the profile before launching a persistent browser context. Useful when reusing the same profile across host and Docker runs.")
    return parser



def build_settings(args: argparse.Namespace, *, project_url: str) -> ChatGPTAutomationSettings:
    return ChatGPTAutomationSettings(
        project_url=project_url,
        email=args.email,
        password=args.password,
        profile_dir=args.profile_dir,
        headless=args.headless,
        use_patchright=not args.use_playwright,
        browser_channel=args.browser_channel,
        password_file=args.password_file,
        disable_fedcm=not args.enable_fedcm,
        filter_no_sandbox=not args.keep_no_sandbox,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        clear_singleton_locks=bool(getattr(args, 'clear_singleton_locks', False)),
    )



class DockerServiceAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        token: Optional[str],
        timeout_seconds: float,
        project_url: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.project_url = project_url

    def _client(self) -> ChatGPTServiceClient:
        return ChatGPTServiceClient(
            self.base_url,
            token=self.token,
            timeout=self.timeout_seconds,
        )

    async def run_login_check(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await asyncio.to_thread(self._run_login_check_sync, keep_open)

    def _run_login_check_sync(self, keep_open: bool) -> dict[str, Any]:
        with self._client() as client:
            return client.login_check(keep_open=keep_open)

    async def resolve_project(self, *, name: str, keep_open: bool = False) -> dict[str, Any]:
        return await asyncio.to_thread(self._resolve_project_sync, name, keep_open)

    def _resolve_project_sync(self, name: str, keep_open: bool) -> dict[str, Any]:
        with self._client() as client:
            return client.resolve_project(name=name, keep_open=keep_open, project_url=self.project_url)

    async def debug_project_list(
        self,
        *,
        scroll_rounds: int = 12,
        wait_ms: int = 350,
        manual_pause: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        raise UnsupportedOperationError(
            "project_list_debug is only supported in direct local mode; omit --service-base-url for this step"
        )

    async def ensure_project(
        self,
        *,
        name: str,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._ensure_project_sync,
            name,
            icon,
            color,
            memory_mode,
            keep_open,
        )

    def _ensure_project_sync(
        self,
        name: str,
        icon: Optional[str],
        color: Optional[str],
        memory_mode: str,
        keep_open: bool,
    ) -> dict[str, Any]:
        with self._client() as client:
            return client.ensure_project(
                name=name,
                icon=icon,
                color=color,
                memory_mode=memory_mode,
                keep_open=keep_open,
                project_url=self.project_url,
            )

    async def remove_project(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await asyncio.to_thread(self._remove_project_sync, keep_open)

    def _remove_project_sync(self, keep_open: bool) -> dict[str, Any]:
        with self._client() as client:
            return client.remove_project(keep_open=keep_open, project_url=self.project_url)

    async def discover_project_source_capabilities(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await asyncio.to_thread(self._discover_project_source_capabilities_sync, keep_open)

    def _discover_project_source_capabilities_sync(self, keep_open: bool) -> dict[str, Any]:
        with self._client() as client:
            return client.discover_project_source_capabilities(
                keep_open=keep_open,
                project_url=self.project_url,
            )

    async def add_project_source(
        self,
        *,
        source_kind: str,
        value: Optional[str] = None,
        file_path: Optional[str] = None,
        display_name: Optional[str] = None,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._add_project_source_sync,
            source_kind,
            value,
            file_path,
            display_name,
            keep_open,
        )

    def _add_project_source_sync(
        self,
        source_kind: str,
        value: Optional[str],
        file_path: Optional[str],
        display_name: Optional[str],
        keep_open: bool,
    ) -> dict[str, Any]:
        with self._client() as client:
            return client.add_project_source(
                source_kind=source_kind,
                value=value,
                file_path=file_path,
                display_name=display_name,
                keep_open=keep_open,
                project_url=self.project_url,
            )

    async def remove_project_source(
        self,
        *,
        source_name: str,
        exact: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._remove_project_source_sync,
            source_name,
            exact,
            keep_open,
        )

    def _remove_project_source_sync(self, source_name: str, exact: bool, keep_open: bool) -> dict[str, Any]:
        with self._client() as client:
            return client.remove_project_source(
                source_name,
                exact=exact,
                keep_open=keep_open,
                project_url=self.project_url,
            )

    async def ask_question(
        self,
        *,
        prompt: str,
        file_path: Optional[str] = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
    ) -> Any:
        return await asyncio.to_thread(
            self._ask_question_sync,
            prompt,
            file_path,
            expect_json,
            keep_open,
            retries,
        )

    def _ask_question_sync(
        self,
        prompt: str,
        file_path: Optional[str],
        expect_json: bool,
        keep_open: bool,
        retries: Optional[int],
    ) -> Any:
        with self._client() as client:
            return client.ask(
                prompt,
                file_path=file_path,
                expect_json=expect_json,
                keep_open=keep_open,
                retries=retries,
                project_url=self.project_url,
            )


def build_service(args: argparse.Namespace, *, project_url: str):
    if args.service_base_url:
        return DockerServiceAdapter(
            base_url=args.service_base_url,
            token=args.service_token,
            timeout_seconds=args.service_timeout_seconds,
            project_url=project_url,
        )
    return ChatGPTAutomationService(build_settings(args, project_url=project_url))


async def _run_step(steps: list[StepResult], name: str, coro, *, step_delay_seconds: float = 0.0) -> Any:
    if steps and step_delay_seconds > 0:
        await asyncio.sleep(step_delay_seconds)
    started = time.perf_counter()
    try:
        result = await coro
        steps.append(
            StepResult(
                name=name,
                ok=True,
                duration_seconds=round(time.perf_counter() - started, 3),
                details=result,
            )
        )
        return result
    except Exception as exc:
        steps.append(
            StepResult(
                name=name,
                ok=False,
                duration_seconds=round(time.perf_counter() - started, 3),
                details={
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
        )
        raise



def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IntegrationAssertionError(message)



def _generated_run_id() -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"



def _extract_project_id(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    import re
    from urllib.parse import urlparse

    path = urlparse(url).path or ""
    match = re.search(r"/g/(g-p-[a-z0-9]+)", path, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None



def _same_project(left: Optional[str], right: Optional[str]) -> bool:
    left_id = _extract_project_id(left)
    right_id = _extract_project_id(right)
    if left_id and right_id:
        return left_id == right_id
    return (left or "") == (right or "")


async def run_integration(args: argparse.Namespace) -> dict[str, Any]:
    selection = resolve_step_selection(
        only_values=args.only,
        skip_values=args.skip,
        keep_project=args.keep_project,
    )
    enabled_steps = set(selection.enabled_steps)

    steps: list[StepResult] = []
    cleanup_steps: list[StepResult] = []
    run_id = args.run_id or _generated_run_id()
    project_name = args.project_name or f"{args.project_name_prefix}-{run_id}"
    base_service = build_service(args, project_url=args.project_url)
    project_url: Optional[str] = None
    project_id: Optional[str] = None

    temp_dir = Path(tempfile.mkdtemp(prefix="chatgpt-itest-"))
    file_source_path = temp_dir / f"itest-file-{run_id}.txt"
    file_source_path.write_text(
        "integration-file-source\nThis file is uploaded as a project source during the end-to-end test.\n",
        encoding="utf-8",
    )

    link_source_name = f"itest-link-{run_id}"
    link_source_match = link_source_name
    text_source_name = f"itest-text-{run_id}"
    text_source_match = text_source_name
    file_source_match = file_source_path.name

    cleanup_enabled = "project_remove_cleanup" in enabled_steps
    summary: dict[str, Any] = {
        "ok": False,
        "run_id": run_id,
        "project_name": project_name,
        "project_url": None,
        "project_id": None,
        "kept_project": not cleanup_enabled,
        "strict_remove_ui": bool(args.strict_remove_ui),
        "requested_only": list(selection.requested_only),
        "requested_skip": list(selection.requested_skip),
        "enabled_steps": list(selection.enabled_steps),
        "steps": [],
        "cleanup_steps": [],
        "artifacts": {
            "temp_dir": str(temp_dir),
            "file_source_path": str(file_source_path),
            "link_source_name": link_source_name,
            "text_source_name": text_source_name,
        },
    }

    def should_run(step_name: str) -> bool:
        return step_name in enabled_steps

    remove_results: list[dict[str, Any]] = []

    try:
        if should_run("login_check"):
            login = await _run_step(
                steps,
                "login_check",
                base_service.run_login_check(keep_open=args.keep_open),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(login.get("logged_in") is True, f"login_check did not report an active session: {login}")

        project_url = args.project_url if _extract_project_id(args.project_url) else None
        project_id = _extract_project_id(project_url)
        summary["project_url"] = project_url
        summary["project_id"] = project_id

        if should_run("project_resolve_before_create"):
            initial_resolve = await _run_step(
                steps,
                "project_resolve_before_create",
                base_service.resolve_project(name=project_name, keep_open=args.keep_open),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(initial_resolve.get("match_count") in {0, 1}, f"unexpected pre-create resolve result: {initial_resolve}")
            _require(
                initial_resolve.get("match_count") == 0 or bool(args.project_name),
                (
                    "generated project name already exists before test start; refusing to continue because the run would not be isolated. "
                    "Pass --project-name only when you intentionally want to reuse an existing project."
                ),
            )

        if should_run("project_ensure_create_or_reuse"):
            ensure_created = await _run_step(
                steps,
                "project_ensure_create_or_reuse",
                base_service.ensure_project(
                    name=project_name,
                    icon=None,
                    color=None,
                    memory_mode=args.memory_mode,
                    keep_open=args.keep_open,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(ensure_created.get("ok") is True, f"project_ensure failed: {ensure_created}")
            project_url = ensure_created.get("project_url")
            _require(bool(project_url), f"project_ensure did not return project_url: {ensure_created}")
            project_id = _extract_project_id(project_url)
            _require(bool(project_id), f"project_ensure returned a project_url without a project_id: {ensure_created}")
            summary["project_url"] = project_url
            summary["project_id"] = project_id

        if should_run("project_ensure_idempotent"):
            _require(bool(project_url), "project_ensure_idempotent requires a project_url from project_ensure_create_or_reuse or --project-url")
            ensure_idempotent = await _run_step(
                steps,
                "project_ensure_idempotent",
                base_service.ensure_project(
                    name=project_name,
                    icon=None,
                    color=None,
                    memory_mode=args.memory_mode,
                    keep_open=args.keep_open,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(ensure_idempotent.get("ok") is True, f"second project_ensure failed: {ensure_idempotent}")
            _require(ensure_idempotent.get("created") is False, f"second project_ensure was not idempotent: {ensure_idempotent}")
            _require(
                _same_project(ensure_idempotent.get("project_url"), project_url),
                f"second project_ensure returned a different project identity: {ensure_idempotent}",
            )

        if should_run("project_resolve_after_ensure"):
            _require(bool(project_url), "project_resolve_after_ensure requires a project_url from project_ensure_create_or_reuse or --project-url")
            resolved = await _run_step(
                steps,
                "project_resolve_after_ensure",
                base_service.resolve_project(name=project_name, keep_open=args.keep_open),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(resolved.get("ok") is True, f"project_resolve failed after ensure: {resolved}")
            _require(resolved.get("match_count") == 1, f"project_resolve did not uniquely match the project: {resolved}")
            _require(
                _same_project(resolved.get("project_url"), project_url),
                f"project_resolve returned a mismatched project identity: {resolved}",
            )

        if should_run("project_list_debug"):
            debug_result = await _run_step(
                steps,
                "project_list_debug",
                base_service.debug_project_list(
                    scroll_rounds=args.project_list_debug_scroll_rounds,
                    wait_ms=args.project_list_debug_wait_ms,
                    manual_pause=args.project_list_debug_manual_pause,
                    keep_open=args.keep_open,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(debug_result.get("ok") is True, f"project_list_debug failed: {debug_result}")
            summary["project_list_debug"] = {
                "artifact_dir": debug_result.get("artifact_dir"),
                "helper_collected_count": debug_result.get("helper_collected_count"),
                "final_dom_project_count": debug_result.get("final_dom_project_count"),
                "opened_more": debug_result.get("opened_more"),
            }

        project_context_needed = bool(enabled_steps & PROJECT_CONTEXT_REQUIRED_STEPS)
        if project_context_needed:
            _require(
                bool(project_url) and bool(project_id),
                (
                    "A project-scoped step was selected, but no project context is available. "
                    "Run project_ensure or pass --project-url pointing at an existing /g/g-p-.../project page."
                ),
            )

        project_service = build_service(args, project_url=project_url or args.project_url)

        source_capabilities: Optional[dict[str, Any]] = None
        available_source_kinds: list[str] = []
        link_supported = False
        if should_run("project_source_capabilities"):
            source_capabilities = await _run_step(
                steps,
                "project_source_capabilities",
                project_service.discover_project_source_capabilities(keep_open=args.keep_open),
                step_delay_seconds=args.step_delay_seconds,
            )
            available_source_kinds = list(source_capabilities.get("available_source_kinds") or [])
            link_supported = "link" in set(available_source_kinds)
            summary["available_source_kinds"] = available_source_kinds
            summary["link_source_supported"] = link_supported

        if should_run("project_source_add_link"):
            if link_supported:
                link_add = await _run_step(
                    steps,
                    "project_source_add_link",
                    project_service.add_project_source(
                        source_kind="link",
                        value=args.link_url,
                        display_name=link_source_name,
                        keep_open=args.keep_open,
                    ),
                    step_delay_seconds=args.step_delay_seconds,
                )
                _require(link_add.get("ok") is True, f"link source add failed: {link_add}")
                link_source_match = str(link_add.get("source_match") or link_source_name)
            else:
                _record_step(
                    steps,
                    "project_source_add_link",
                    ok=True,
                    details={
                        "skipped": True,
                        "reason": "unsupported",
                        "requested_source_kind": "link",
                        "available_source_kinds": available_source_kinds,
                    },
                )

        if should_run("project_source_add_text"):
            text_add = await _run_step(
                steps,
                "project_source_add_text",
                project_service.add_project_source(
                    source_kind="text",
                    value=f"Integration note for run {run_id}",
                    display_name=text_source_name,
                    keep_open=args.keep_open,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(text_add.get("ok") is True, f"text source add failed: {text_add}")
            text_source_match = str(text_add.get("source_match") or text_source_name)

        if should_run("project_source_add_file"):
            file_add = await _run_step(
                steps,
                "project_source_add_file",
                project_service.add_project_source(
                    source_kind="file",
                    file_path=str(file_source_path),
                    display_name=None,
                    keep_open=args.keep_open,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(file_add.get("ok") is True, f"file source add failed: {file_add}")
            file_source_match = str(file_add.get("source_match") or file_source_match)

        if should_run("ask_question"):
            ask_result = await _run_step(
                steps,
                "ask_question",
                project_service.ask_question(
                    prompt=args.ask_prompt,
                    expect_json=False,
                    keep_open=args.keep_open,
                    retries=0,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            if isinstance(ask_result, (dict, list)):
                ask_text = json.dumps(ask_result, ensure_ascii=False)
            else:
                ask_text = str(ask_result)
            _require(
                "INTEGRATION_OK" in ask_text.upper(),
                f"ask_question did not contain the expected token. response={ask_text!r}",
            )

        if should_run("project_source_remove_link"):
            if link_supported:
                link_remove = await _run_step(
                    steps,
                    "project_source_remove_link",
                    project_service.remove_project_source(
                        source_name=link_source_match,
                        exact=True,
                        keep_open=args.keep_open,
                    ),
                    step_delay_seconds=args.step_delay_seconds,
                )
                _require(link_remove.get("ok") is True, f"link source remove failed: {link_remove}")
                remove_results.append(link_remove)
            else:
                _record_step(
                    steps,
                    "project_source_remove_link",
                    ok=True,
                    details={
                        "skipped": True,
                        "reason": "unsupported",
                        "requested_source_kind": "link",
                        "available_source_kinds": available_source_kinds,
                    },
                )

        if should_run("project_source_remove_text"):
            text_remove = await _run_step(
                steps,
                "project_source_remove_text",
                project_service.remove_project_source(
                    source_name=text_source_match,
                    exact=True,
                    keep_open=args.keep_open,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(text_remove.get("ok") is True, f"text source remove failed: {text_remove}")
            remove_results.append(text_remove)

        if should_run("project_source_remove_file"):
            file_remove = await _run_step(
                steps,
                "project_source_remove_file",
                project_service.remove_project_source(
                    source_name=file_source_match,
                    exact=False,
                    keep_open=args.keep_open,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(file_remove.get("ok") is True, f"file source remove failed: {file_remove}")
            remove_results.append(file_remove)

        if args.strict_remove_ui:
            _require(
                bool(enabled_steps & REMOVAL_STEPS),
                "--strict-remove-ui requires at least one enabled source-removal step",
            )
            _require(bool(remove_results), "--strict-remove-ui was requested, but no source removals executed")
            _require(
                any(result.get("removed_via_ui") is True for result in remove_results),
                f"--strict-remove-ui failed: no source removal used the actual UI path. remove_results={remove_results}",
            )

        summary["ok"] = True
        return summary
    finally:
        summary["artifacts"]["link_source_match"] = link_source_match
        summary["artifacts"]["text_source_match"] = text_source_match
        summary["artifacts"]["file_source_match"] = file_source_match
        summary["steps"] = [asdict(step) for step in steps]

        if project_url and cleanup_enabled:
            try:
                project_service = build_service(args, project_url=project_url)
                removal_result = await _run_step(
                    cleanup_steps,
                    "project_remove_cleanup",
                    project_service.remove_project(keep_open=args.keep_open),
                    step_delay_seconds=args.step_delay_seconds,
                )
                if removal_result.get("ok") is not True:
                    raise IntegrationAssertionError(f"project_remove cleanup failed: {removal_result}")
            except Exception as exc:
                cleanup_steps.append(
                    StepResult(
                        name="project_remove_cleanup_assertion",
                        ok=False,
                        duration_seconds=0.0,
                        details={
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                )
                if summary.get("ok"):
                    summary["ok"] = False
                    summary["cleanup_error"] = str(exc)

        summary["cleanup_steps"] = [asdict(step) for step in cleanup_steps]



def render_summary(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2, ensure_ascii=False)


async def _async_main(argv: Optional[list[str]] = None) -> int:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--dotenv", default=".env")
    bootstrap_args, _ = bootstrap.parse_known_args(argv)
    if bootstrap_args.dotenv:
        load_dotenv(bootstrap_args.dotenv, override=False)

    parser = make_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.debug)

    try:
        summary = await run_integration(args)
    except ValueError as exc:
        summary = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(render_summary(summary))
        return 16
    except ManualLoginRequiredError as exc:
        summary = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(render_summary(summary))
        return 10
    except BotChallengeError as exc:
        summary = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(render_summary(summary))
        return 11
    except ResponseTimeoutError as exc:
        summary = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(render_summary(summary))
        return 12
    except UnsupportedOperationError as exc:
        summary = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(render_summary(summary))
        return 15
    except AuthenticationError as exc:
        summary = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(render_summary(summary))
        return 13
    except IntegrationAssertionError as exc:
        summary = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(render_summary(summary))
        return 20
    except FileNotFoundError as exc:
        summary = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(render_summary(summary))
        return 14

    if args.json_out:
        Path(args.json_out).write_text(render_summary(summary) + "\n", encoding="utf-8")
    print(render_summary(summary))
    return 0 if summary.get("ok") else 1



def main(argv: Optional[list[str]] = None) -> int:
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())



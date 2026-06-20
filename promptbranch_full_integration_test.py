from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
import time
from io import StringIO
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from dotenv import load_dotenv

from promptbranch_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings
from promptbranch_service_client import ChatGPTServiceClient
from promptbranch_project_delete_safety import is_project_delete_disabled_payload
from promptbranch_mcp import handle_mcp_jsonrpc_message, mcp_host_config, mcp_host_smoke, mcp_tool_manifest, serve_mcp_stdio
from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    BrowserProfileBusyError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
)

DEFAULT_PROJECT_URL = "https://chatgpt.com/"
DEFAULT_PROFILE_DIR = "./.pb_profile"
DEFAULT_MAX_RETRIES = 1
SOURCE_MUTATION_PROFILE_WAIT_SECONDS = float(os.getenv("PROMPTBRANCH_SOURCE_MUTATION_PROFILE_WAIT_SECONDS", os.getenv("PROMPTBRANCH_BROWSER_PROFILE_LOCK_WAIT_SECONDS", os.getenv("CHATGPT_BROWSER_PROFILE_LOCK_WAIT_SECONDS", "600.0"))))
SOURCE_MUTATION_BUSY_RETRY_MIN_SECONDS = 0.25
SOURCE_MUTATION_BUSY_RETRY_MAX_SECONDS = 5.0
SOURCE_MUTATION_OPERATIONS = {"add_project_source", "remove_project_source"}

CANONICAL_STEP_ORDER: tuple[str, ...] = (
    "mcp_smoke",
    "login_check",
    "project_resolve_before_create",
    "project_ensure_create_or_reuse",
    "project_ensure_idempotent",
    "project_resolve_after_ensure",
    "project_source_capabilities",
    "project_source_add_link",
    "project_source_add_text",
    "project_source_add_file",
    "project_source_overwrite_file",
    "ask_question",
    "task_message_flow",
    "project_source_remove_link",
    "project_source_remove_text",
    "project_source_remove_file",
    "project_remove_cleanup",
)
OPTIONAL_STEP_ORDER: tuple[str, ...] = (
    "mcp_host_smoke",
    "project_list_debug",
)
FULL_STEP_ORDER: tuple[str, ...] = CANONICAL_STEP_ORDER + OPTIONAL_STEP_ORDER

STEP_ALIASES: dict[str, tuple[str, ...]] = {
    "all": CANONICAL_STEP_ORDER,
    "mcp": ("mcp_smoke",),
    "mcp_smoke": ("mcp_smoke",),
    "mcp_host": ("mcp_host_smoke",),
    "mcp_host_smoke": ("mcp_host_smoke",),
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
    "source_overwrite_file": ("project_source_overwrite_file",),
    "source_remove_link": ("project_source_remove_link",),
    "source_remove_text": ("project_source_remove_text",),
    "source_remove_file": ("project_source_remove_file",),
    "source_add": (
        "project_source_add_link",
        "project_source_add_text",
        "project_source_add_file",
        "project_source_overwrite_file",
    ),
    "source_remove": (
        "project_source_remove_link",
        "project_source_remove_text",
        "project_source_remove_file",
    ),
    "ask": ("ask_question",),
    "task_message_flow": ("task_message_flow",),
    "task_messages": ("task_message_flow",),
    "task": ("task_message_flow",),
    "project_remove": ("project_remove_cleanup",),
    "cleanup": ("project_remove_cleanup",),
}

SOURCE_FLOW_STEPS = {
    "project_source_add_link",
    "project_source_add_text",
    "project_source_add_file",
    "project_source_overwrite_file",
    "project_source_remove_link",
    "project_source_remove_text",
    "project_source_remove_file",
}
PROJECT_CONTEXT_REQUIRED_STEPS = {
    "project_source_capabilities",
    *SOURCE_FLOW_STEPS,
    "ask_question",
    "task_message_flow",
    "project_remove_cleanup",
}
REMOVAL_STEPS = {
    "project_source_remove_link",
    "project_source_remove_text",
    "project_source_remove_file",
}
LOCAL_ONLY_STEPS = {
    "mcp_smoke",
    "mcp_host_smoke",
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

    if enabled - {"project_remove_cleanup", *LOCAL_ONLY_STEPS}:
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
    parser.add_argument("--profile-dir", default=os.getenv("PROMPTBRANCH_PROFILE_DIR", DEFAULT_PROFILE_DIR))
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
    parser.add_argument("--post-ask-delay-seconds", type=float, default=float(os.getenv("CHATGPT_POST_ASK_DELAY_SECONDS", "20.0")), help="Additional cooldown after ask steps before reading task/conversation history. This reduces ChatGPT conversation-history rate-limit pressure without slowing every step.")
    parser.add_argument("--task-list-visible-timeout-seconds", type=float, default=float(os.getenv("CHATGPT_TASK_LIST_VISIBLE_TIMEOUT_SECONDS", "120.0")), help="Maximum bounded wait for a task created by ask() to become visible in project task listing.")
    parser.add_argument("--task-list-visible-poll-min-seconds", type=float, default=float(os.getenv("CHATGPT_TASK_LIST_VISIBLE_POLL_MIN_SECONDS", "20.0")), help="Initial backoff between task-list visibility probes after ask().")
    parser.add_argument("--task-list-visible-poll-max-seconds", type=float, default=float(os.getenv("CHATGPT_TASK_LIST_VISIBLE_POLL_MAX_SECONDS", "45.0")), help="Maximum backoff between task-list visibility probes after ask().")
    parser.add_argument("--task-list-visible-max-attempts", type=int, default=int(os.getenv("CHATGPT_TASK_LIST_VISIBLE_MAX_ATTEMPTS", "4")), help="Maximum number of task-list visibility probes after ask(); keeps live smoke tests from hammering conversation APIs.")
    parser.add_argument("--allow-recent-state-task-fallback", action="store_true", help="Allow task_message_flow to pass when the created task is visible only through local recent_state fallback. Default requires indexed task visibility.")
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
        profile_lock_wait_seconds=SOURCE_MUTATION_PROFILE_WAIT_SECONDS,
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

    @staticmethod
    def _browser_busy_payload(exc: Exception) -> dict[str, Any] | None:
        response = getattr(exc, "response", None)
        if response is None:
            return None
        try:
            payload = response.json()
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        detail = payload.get("detail")
        if isinstance(detail, dict):
            return dict(detail)
        return None

    @classmethod
    def _is_fresh_same_family_source_busy(cls, exc: Exception) -> bool:
        payload = cls._browser_busy_payload(exc)
        if not payload or payload.get("status") != "browser_profile_busy":
            return False
        active_operation = str(payload.get("active_operation") or "")
        requested_operation = str(payload.get("operation") or "")
        if active_operation not in SOURCE_MUTATION_OPERATIONS:
            return False
        if requested_operation and requested_operation not in SOURCE_MUTATION_OPERATIONS:
            return False
        if payload.get("stale_lock_expired") is True:
            return False
        return True

    @classmethod
    def _source_busy_retry_delay(cls, exc: Exception, attempt: int) -> float:
        payload = cls._browser_busy_payload(exc) or {}
        raw_retry_after = payload.get("retry_after_seconds")
        try:
            retry_after = float(raw_retry_after)
        except (TypeError, ValueError):
            retry_after = SOURCE_MUTATION_BUSY_RETRY_MIN_SECONDS * attempt
        return max(
            SOURCE_MUTATION_BUSY_RETRY_MIN_SECONDS,
            min(SOURCE_MUTATION_BUSY_RETRY_MAX_SECONDS, retry_after),
        )

    async def _run_source_mutation_with_profile_retry(
        self,
        operation: Callable[[], dict[str, Any]],
        *,
        max_wait_seconds: float = SOURCE_MUTATION_PROFILE_WAIT_SECONDS,
    ) -> dict[str, Any]:
        started = time.monotonic()
        attempt = 0
        last_busy_payload: dict[str, Any] | None = None
        while True:
            attempt += 1
            try:
                result = await asyncio.to_thread(operation)
            except Exception as exc:
                if not self._is_fresh_same_family_source_busy(exc):
                    raise
                last_busy_payload = self._browser_busy_payload(exc)
                elapsed = time.monotonic() - started
                if elapsed >= max_wait_seconds:
                    raise
                delay = min(self._source_busy_retry_delay(exc, attempt), max(0.001, max_wait_seconds - elapsed))
                await asyncio.sleep(delay)
                continue
            if isinstance(result, dict) and last_busy_payload is not None:
                result = dict(result)
                result.setdefault("profile_contention_retried", True)
                result.setdefault("profile_contention_retry_attempts", max(0, attempt - 1))
                result.setdefault("profile_contention_last_busy", last_busy_payload)
            return result

    async def run_login_check(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await asyncio.to_thread(self._run_login_check_sync, keep_open)

    def _run_login_check_sync(self, keep_open: bool) -> dict[str, Any]:
        with self._client() as client:
            return client.login_check(keep_open=keep_open)

    async def resolve_project(
        self,
        *,
        name: str,
        keep_open: bool = False,
        project_url: str | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._resolve_project_sync, name, keep_open, project_url)

    def _resolve_project_sync(self, name: str, keep_open: bool, project_url: str | None = None) -> dict[str, Any]:
        effective_project_url = project_url or self.project_url
        with self._client() as client:
            return client.resolve_project(name=name, keep_open=keep_open, project_url=effective_project_url)

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

    async def remove_project(
        self,
        *,
        keep_open: bool = False,
        project_url: str | None = None,
        project_name: str | None = None,
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(self._remove_project_sync, keep_open, project_url, project_name)
        except TypeError:
            return await asyncio.to_thread(self._remove_project_sync, keep_open, project_url)

    def _remove_project_sync(
        self,
        keep_open: bool,
        project_url: str | None = None,
        project_name: str | None = None,
    ) -> dict[str, Any]:
        effective_project_url = project_url or self.project_url
        with self._client() as client:
            return client.remove_project(
                keep_open=keep_open,
                project_url=effective_project_url,
                project_name=project_name,
                profile_lock_wait_seconds=SOURCE_MUTATION_PROFILE_WAIT_SECONDS,
            )

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
        overwrite_existing: bool = True,
    ) -> dict[str, Any]:
        return await self._run_source_mutation_with_profile_retry(
            lambda: self._add_project_source_sync(
                source_kind,
                value,
                file_path,
                display_name,
                keep_open,
                overwrite_existing,
            )
        )

    def _add_project_source_sync(
        self,
        source_kind: str,
        value: Optional[str],
        file_path: Optional[str],
        display_name: Optional[str],
        keep_open: bool,
        overwrite_existing: bool,
    ) -> dict[str, Any]:
        with self._client() as client:
            return client.add_project_source(
                source_kind=source_kind,
                value=value,
                file_path=file_path,
                display_name=display_name,
                keep_open=keep_open,
                overwrite_existing=overwrite_existing,
                project_url=self.project_url,
                profile_lock_wait_seconds=SOURCE_MUTATION_PROFILE_WAIT_SECONDS,
            )

    async def remove_project_source(
        self,
        *,
        source_name: str,
        exact: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self._run_source_mutation_with_profile_retry(
            lambda: self._remove_project_source_sync(source_name, exact, keep_open)
        )

    def _remove_project_source_sync(self, source_name: str, exact: bool, keep_open: bool) -> dict[str, Any]:
        with self._client() as client:
            return client.remove_project_source(
                source_name,
                exact=exact,
                keep_open=keep_open,
                project_url=self.project_url,
                profile_lock_wait_seconds=SOURCE_MUTATION_PROFILE_WAIT_SECONDS,
            )

    async def list_project_chats(
        self,
        *,
        keep_open: bool = False,
        include_history_fallback: bool = True,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._list_project_chats_sync, keep_open, include_history_fallback)

    def _list_project_chats_sync(self, keep_open: bool, include_history_fallback: bool) -> dict[str, Any]:
        with self._client() as client:
            return client.list_project_chats(
                keep_open=keep_open,
                project_url=self.project_url,
                include_history_fallback=include_history_fallback,
            )

    async def get_chat(self, *, conversation_url: str, keep_open: bool = False) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_chat_sync, conversation_url, keep_open)

    def _get_chat_sync(self, conversation_url: str, keep_open: bool) -> dict[str, Any]:
        with self._client() as client:
            return client.get_chat(conversation_url=conversation_url, keep_open=keep_open, project_url=self.project_url)

    async def ask_question_result(
        self,
        *,
        prompt: str,
        file_path: Optional[str] = None,
        conversation_url: str | None = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._ask_question_result_sync,
            prompt,
            file_path,
            conversation_url,
            expect_json,
            keep_open,
            retries,
        )

    def _ask_question_result_sync(
        self,
        prompt: str,
        file_path: Optional[str],
        conversation_url: str | None,
        expect_json: bool,
        keep_open: bool,
        retries: Optional[int],
    ) -> dict[str, Any]:
        with self._client() as client:
            return client.ask_result(
                prompt,
                file_path=file_path,
                conversation_url=conversation_url,
                expect_json=expect_json,
                keep_open=keep_open,
                retries=retries,
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
        result_ok = not (isinstance(result, dict) and result.get("ok") is False)
        steps.append(
            StepResult(
                name=name,
                ok=result_ok,
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


async def _post_ask_cooldown(steps: list[StepResult], *, seconds: float, reason: str) -> None:
    delay = max(0.0, float(seconds or 0.0))
    if delay <= 0:
        return
    started = time.perf_counter()
    await asyncio.sleep(delay)
    steps.append(
        StepResult(
            name="rate_limit_cooldown",
            ok=True,
            duration_seconds=round(time.perf_counter() - started, 3),
            details={
                "reason": reason,
                "delay_seconds": delay,
                "scope": "post_ask",
            },
        )
    )



def _exception_payload(exc: BaseException) -> dict[str, Any]:
    """Best-effort structured payload extraction from service HTTP errors."""
    payload: Any = None
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            payload = response.json()
        except Exception:
            payload = None
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            stripped = detail.strip()
            if stripped.startswith("{"):
                try:
                    detail_payload = json.loads(stripped)
                    if isinstance(detail_payload, dict):
                        return detail_payload
                except json.JSONDecodeError:
                    pass
        return payload

    text = str(exc or "")
    start = text.find("{")
    while start >= 0:
        candidate = text[start:].strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        break
    return {}


def _is_browser_profile_busy_payload(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("status") == "browser_profile_busy":
        return True
    if payload.get("error_type") == "BrowserProfileBusyError":
        return True
    haystack = " ".join(str(payload.get(key) or "") for key in ("error", "detail", "message"))
    return "browser_profile_busy" in haystack or "browser profile is busy" in haystack.lower()


def _is_browser_profile_busy_exception(exc: BaseException) -> bool:
    payload = _exception_payload(exc)
    return _is_browser_profile_busy_payload(payload) or "browser_profile_busy" in str(exc) or "browser profile is busy" in str(exc).lower()


def _is_project_already_missing_cleanup_payload(payload: Any) -> bool:
    """Return true when cleanup confirms the temporary project is already absent.

    Project removal is a cleanup operation at the end of the full browser suite.
    If every functional browser step already passed and cleanup can no longer find
    the configured project in the sidebar, the desired postcondition is already
    true: the temporary project is absent. Treat that condition as idempotent
    cleanup success instead of failing an otherwise green release gate.
    """
    if not isinstance(payload, dict):
        return False
    status = str(payload.get("status") or "").strip().lower()
    if status in {"project_missing", "project_not_found", "already_missing", "expected_missing"}:
        return True
    haystack = " ".join(str(payload.get(key) or "") for key in ("error", "detail", "message", "diagnostic"))
    haystack = haystack.lower()
    return (
        "could not find the configured project in the sidebar" in haystack
        or "configured project" in haystack and "not found" in haystack and "sidebar" in haystack
    )


def _is_project_already_missing_cleanup_exception(exc: BaseException) -> bool:
    payload = _exception_payload(exc)
    text = str(exc).lower()
    return _is_project_already_missing_cleanup_payload(payload) or (
        "could not find the configured project in the sidebar" in text
        or "configured project" in text and "not found" in text and "sidebar" in text
    )


def _project_already_missing_cleanup_details(
    *,
    exc: BaseException | None,
    payload: Any,
    attempt: int,
    max_attempts: int,
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "ok": True,
        "status": "project_remove_cleanup_already_missing",
        "cleanup_idempotent": True,
        "postcondition": "temporary_project_absent",
        "attempt": attempt,
        "max_attempts": max_attempts,
    }
    if exc is not None:
        details["error_type"] = type(exc).__name__
        details["error"] = str(exc)
    if isinstance(payload, dict) and payload:
        details["missing_payload"] = payload
    return details


async def _verify_project_absent_for_cleanup(
    project_service: Any,
    *,
    project_name: str | None,
    keep_open: bool,
    project_url: str | None = None,
) -> dict[str, Any]:
    """Verify cleanup postcondition before treating a not-found removal as success.

    A remove-project sidebar lookup failure is not by itself proof that the
    temporary project was deleted. The sidebar may be stale, collapsed, or not
    hydrated. Only classify cleanup as successful when an explicit resolve by
    project name confirms there are zero matches.
    """
    if not project_name:
        return {
            "ok": False,
            "status": "project_absence_unverified",
            "reason": "project_name_missing",
        }
    resolver = getattr(project_service, "resolve_project", None)
    if resolver is None:
        return {
            "ok": False,
            "status": "project_absence_unverified",
            "reason": "resolve_project_unavailable",
            "project_name": project_name,
        }
    try:
        try:
            result = await resolver(name=project_name, keep_open=keep_open, project_url=project_url)
        except TypeError:
            result = await resolver(name=project_name, keep_open=keep_open)
    except Exception as exc:  # noqa: BLE001 - convert cleanup diagnostics to structured data
        return {
            "ok": False,
            "status": "project_absence_unverified",
            "reason": "resolve_project_failed",
            "project_name": project_name,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "resolve_payload": _exception_payload(exc),
        }
    if isinstance(result, dict) and result.get("match_count") == 0:
        error = str(result.get("error") or "")
        return {
            "ok": True,
            "status": "project_absence_verified",
            "project_name": project_name,
            "resolve_result": result,
            "project_not_found": error in {"", "project_not_found"},
        }
    return {
        "ok": False,
        "status": "project_still_present_or_ambiguous",
        "project_name": project_name,
        "resolve_result": result,
    }


def _rate_limit_telemetry_from_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    telemetry = payload.get("rate_limit_telemetry")
    if isinstance(telemetry, dict):
        return telemetry
    result = payload.get("resolve_result")
    if isinstance(result, dict):
        telemetry = result.get("rate_limit_telemetry")
        if isinstance(telemetry, dict):
            return telemetry
    return {}


def _payload_has_rate_limit_telemetry(payload: Any) -> bool:
    telemetry = _rate_limit_telemetry_from_payload(payload)
    if not telemetry:
        return False
    if bool(telemetry.get("rate_limit_modal_detected")):
        return True
    if bool(telemetry.get("conversation_history_429_seen")):
        return True
    if bool(telemetry.get("backend_api_guardrail_seen")):
        return True
    events = telemetry.get("service_rate_limit_events")
    return isinstance(events, list) and bool(events)


def _retry_after_seconds_from_busy_payload(payload: Any, *, default_seconds: float = 10.0, max_seconds: float = 30.0) -> float:
    if isinstance(payload, dict):
        for key in ("retry_after_seconds", "waited_seconds"):
            try:
                value = float(payload.get(key))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return min(max_seconds, value)
        telemetry = _rate_limit_telemetry_from_payload(payload)
        if telemetry:
            waits: list[float] = []
            for key in ("cooldown_remaining_seconds", "cooldown_wait_seconds_total"):
                try:
                    value = float(telemetry.get(key))
                except (TypeError, ValueError):
                    continue
                if value > 0:
                    waits.append(value)
            events = telemetry.get("service_rate_limit_events")
            if isinstance(events, list):
                for event in events:
                    if not isinstance(event, dict):
                        continue
                    try:
                        value = float(event.get("wait_seconds"))
                    except (TypeError, ValueError):
                        continue
                    if value > 0:
                        waits.append(value)
            if waits:
                return min(max_seconds, max(waits))
            if _payload_has_rate_limit_telemetry(payload):
                return min(max_seconds, max(default_seconds, 60.0))
    return min(max_seconds, default_seconds)


async def _remove_project_cleanup_with_retry(
    cleanup_steps: list[StepResult],
    project_service: Any,
    *,
    keep_open: bool,
    step_delay_seconds: float,
    max_attempts: int = 3,
    project_name: str | None = None,
) -> dict[str, Any]:
    """Remove the temporary project and prove the cleanup postcondition.

    Project cleanup must fail closed: a sidebar lookup failure is not proof that
    the temporary project disappeared. When the sidebar cannot find the configured
    URL but a name-based resolve still finds the project, retry removal instead
    of silently leaking an integration-test project.
    """

    active_project_url = str(getattr(project_service, "project_url", "") or "").strip() or None

    async def _remove_project_call() -> dict[str, Any]:
        remover = getattr(project_service, "remove_project")
        if active_project_url:
            try:
                return await remover(keep_open=keep_open, project_url=active_project_url, project_name=project_name)
            except TypeError:
                try:
                    return await remover(keep_open=keep_open, project_url=active_project_url)
                except TypeError:
                    return await remover(keep_open=keep_open)
        if project_name:
            try:
                return await remover(keep_open=keep_open, project_name=project_name)
            except TypeError:
                return await remover(keep_open=keep_open)
        return await remover(keep_open=keep_open)

    def _resolved_project_url(absence: dict[str, Any]) -> str | None:
        result = absence.get("resolve_result") if isinstance(absence, dict) else None
        if not isinstance(result, dict):
            return None
        direct = str(result.get("project_url") or "").strip()
        if direct:
            return direct
        matches = result.get("matches")
        if isinstance(matches, list) and len(matches) == 1 and isinstance(matches[0], dict):
            url = str(matches[0].get("url") or matches[0].get("project_url") or "").strip()
            return url or None
        return None

    def _retarget_project_url(absence: dict[str, Any]) -> dict[str, Any]:
        nonlocal active_project_url
        url = _resolved_project_url(absence)
        if not url:
            return {"retargeted": False, "reason": "resolved_project_url_missing"}
        previous = active_project_url or str(getattr(project_service, "project_url", "") or "").strip()
        if previous == url:
            return {"retargeted": False, "reason": "already_using_resolved_project_url", "project_url": url}
        active_project_url = url
        try:
            setattr(project_service, "project_url", url)
            attribute_updated = True
        except Exception:
            attribute_updated = False
        return {
            "retargeted": True,
            "project_url": url,
            "previous_project_url": previous,
            "active_project_url": active_project_url,
            "project_url_attribute_updated": attribute_updated,
        }

    async def _retry_after_unverified_absence(
        *,
        details: dict[str, Any],
        absence: dict[str, Any],
        attempt: int,
    ) -> bool:
        if attempt >= attempts:
            return False
        retarget = _retarget_project_url(absence)
        delay = _retry_after_seconds_from_busy_payload(
            absence if isinstance(absence, dict) else None,
            default_seconds=max(1.0, step_delay_seconds or 1.0),
            max_seconds=180.0 if _payload_has_rate_limit_telemetry(absence) else 30.0,
        )
        details["status"] = "project_remove_cleanup_missing_unverified_retry_wait"
        details["next_attempt"] = attempt + 1
        details["delay_seconds"] = delay
        details["retryable"] = True
        details["retarget"] = retarget
        cleanup_steps.append(
            StepResult(
                name="project_remove_cleanup_retry_wait",
                ok=True,
                duration_seconds=0.0,
                details=details,
            )
        )
        await asyncio.sleep(delay)
        return True

    async def _verify_success_result_absence(result: dict[str, Any], *, attempt: int) -> dict[str, Any] | None:
        if not project_name:
            return None
        absence = await _verify_project_absent_for_cleanup(
            project_service,
            project_name=project_name,
            keep_open=keep_open,
            project_url=active_project_url,
        )
        if absence.get("ok") is True:
            result["absence_verification"] = absence
            result["postcondition"] = "temporary_project_absent"
            return None
        details = {
            **result,
            "ok": False,
            "status": "project_remove_cleanup_success_unverified",
            "attempt": attempt,
            "max_attempts": attempts,
            "absence_verification": absence,
        }
        if await _retry_after_unverified_absence(details=details, absence=absence, attempt=attempt):
            return {"retry": True}
        cleanup_steps.append(
            StepResult(
                name="project_remove_cleanup",
                ok=False,
                duration_seconds=0.0,
                details=details,
            )
        )
        raise IntegrationAssertionError(f"project_remove cleanup could not verify project absence after success: {details}")

    attempts = max(1, int(max_attempts or 1))
    attempt = 1
    while True:
        if cleanup_steps and step_delay_seconds > 0:
            await asyncio.sleep(step_delay_seconds)
        started = time.perf_counter()
        try:
            result = await _remove_project_call()
        except Exception as exc:  # noqa: BLE001 - cleanup must become structured report data
            payload = _exception_payload(exc)
            if _is_project_already_missing_cleanup_exception(exc):
                absence = await _verify_project_absent_for_cleanup(
                    project_service,
                    project_name=project_name,
                    keep_open=keep_open,
                    project_url=active_project_url,
                )
                if absence.get("ok") is True:
                    details = _project_already_missing_cleanup_details(
                        exc=exc,
                        payload=payload,
                        attempt=attempt,
                        max_attempts=attempts,
                    )
                    details["status"] = "project_remove_cleanup_absence_verified"
                    details["cleanup_idempotent"] = True
                    details["absence_verification"] = absence
                    cleanup_steps.append(
                        StepResult(
                            name="project_remove_cleanup",
                            ok=True,
                            duration_seconds=round(time.perf_counter() - started, 3),
                            details=details,
                        )
                    )
                    return details
                details = {
                    "ok": False,
                    "status": "project_remove_cleanup_missing_unverified",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "missing_payload": payload,
                    "absence_verification": absence,
                }
                if await _retry_after_unverified_absence(details=details, absence=absence, attempt=attempt):
                    attempt += 1
                    continue
                cleanup_steps.append(
                    StepResult(
                        name="project_remove_cleanup",
                        ok=False,
                        duration_seconds=round(time.perf_counter() - started, 3),
                        details=details,
                    )
                )
                raise IntegrationAssertionError(f"project_remove cleanup could not verify project absence: {details}") from exc
            retryable = _is_browser_profile_busy_exception(exc)
            if retryable and attempt < attempts:
                delay = _retry_after_seconds_from_busy_payload(payload)
                cleanup_steps.append(
                    StepResult(
                        name="project_remove_cleanup_retry_wait",
                        ok=True,
                        duration_seconds=0.0,
                        details={
                            "ok": True,
                            "status": "browser_profile_busy_retry_wait",
                            "attempt": attempt,
                            "next_attempt": attempt + 1,
                            "max_attempts": attempts,
                            "delay_seconds": delay,
                            "retryable": True,
                            "busy_payload": payload,
                        },
                    )
                )
                await asyncio.sleep(delay)
                attempt += 1
                continue
            details = {
                "ok": False,
                "status": "project_remove_cleanup_failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "attempt": attempt,
                "max_attempts": attempts,
                "retryable": retryable,
                "busy_payload": payload,
            }
            cleanup_steps.append(
                StepResult(
                    name="project_remove_cleanup",
                    ok=False,
                    duration_seconds=round(time.perf_counter() - started, 3),
                    details=details,
                )
            )
            raise IntegrationAssertionError(f"project_remove cleanup failed: {details}") from exc

        if is_project_delete_disabled_payload(result):
            details = dict(result)
            details.update({
                "ok": True,
                "status": "project_remove_cleanup_skipped_delete_frozen",
                "postcondition": "temporary_project_retained_delete_frozen",
                "cleanup_policy": "no_project_delete_until_secure_protocol",
                "attempt": attempt,
                "max_attempts": attempts,
            })
            cleanup_steps.append(
                StepResult(
                    name="project_remove_cleanup",
                    ok=True,
                    duration_seconds=round(time.perf_counter() - started, 3),
                    details=details,
                )
            )
            return details

        if _is_project_already_missing_cleanup_payload(result):
            absence = await _verify_project_absent_for_cleanup(
                project_service,
                project_name=project_name,
                keep_open=keep_open,
                project_url=active_project_url,
            )
            if absence.get("ok") is True:
                details = _project_already_missing_cleanup_details(
                    exc=None,
                    payload=result,
                    attempt=attempt,
                    max_attempts=attempts,
                )
                details["status"] = "project_remove_cleanup_absence_verified"
                details["cleanup_idempotent"] = True
                details["absence_verification"] = absence
                cleanup_steps.append(
                    StepResult(
                        name="project_remove_cleanup",
                        ok=True,
                        duration_seconds=round(time.perf_counter() - started, 3),
                        details=details,
                    )
                )
                return details
            details = result if isinstance(result, dict) else {"result": result}
            details = {
                **details,
                "ok": False,
                "status": "project_remove_cleanup_missing_unverified",
                "attempt": attempt,
                "max_attempts": attempts,
                "absence_verification": absence,
            }
            if await _retry_after_unverified_absence(details=details, absence=absence, attempt=attempt):
                attempt += 1
                continue
            cleanup_steps.append(
                StepResult(
                    name="project_remove_cleanup",
                    ok=False,
                    duration_seconds=round(time.perf_counter() - started, 3),
                    details=details,
                )
            )
            raise IntegrationAssertionError(f"project_remove cleanup could not verify project absence: {details}")
        retryable_result = _is_browser_profile_busy_payload(result)
        result_ok = bool(isinstance(result, dict) and result.get("ok") is True)
        if result_ok:
            if isinstance(result, dict):
                result = {**result, "attempt": attempt, "retry_count": attempt - 1}
            maybe_retry = await _verify_success_result_absence(result, attempt=attempt)
            if maybe_retry and maybe_retry.get("retry") is True:
                attempt += 1
                continue
            cleanup_steps.append(
                StepResult(
                    name="project_remove_cleanup",
                    ok=True,
                    duration_seconds=round(time.perf_counter() - started, 3),
                    details=result,
                )
            )
            return result
        if retryable_result and attempt < attempts:
            delay = _retry_after_seconds_from_busy_payload(result)
            cleanup_steps.append(
                StepResult(
                    name="project_remove_cleanup_retry_wait",
                    ok=True,
                    duration_seconds=0.0,
                    details={
                        "ok": True,
                        "status": "browser_profile_busy_retry_wait",
                        "attempt": attempt,
                        "next_attempt": attempt + 1,
                        "max_attempts": attempts,
                        "delay_seconds": delay,
                        "retryable": True,
                        "busy_payload": result,
                    },
                )
            )
            await asyncio.sleep(delay)
            attempt += 1
            continue
        details = result if isinstance(result, dict) else {"result": result}
        cleanup_steps.append(
            StepResult(
                name="project_remove_cleanup",
                ok=False,
                duration_seconds=round(time.perf_counter() - started, 3),
                details={**details, "attempt": attempt, "max_attempts": attempts},
            )
        )
        raise IntegrationAssertionError(f"project_remove cleanup failed: {details}")

def _run_mcp_smoke(*, repo_path: Path, profile_dir: Optional[str]) -> dict[str, Any]:
    manifest = mcp_tool_manifest()
    tool_names = [tool.get("name") for tool in manifest.get("tools", []) if isinstance(tool, dict)]
    init = handle_mcp_jsonrpc_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    listed = handle_mcp_jsonrpc_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    host_config = mcp_host_config(repo_path=repo_path, profile_dir=profile_dir)

    stdin = StringIO('{"jsonrpc":"2.0","id":3,"method":"tools/list"}\n')
    stdout = StringIO()
    rc = serve_mcp_stdio(
        repo_path=repo_path,
        profile_dir=profile_dir,
        input_stream=stdin,
        output_stream=stdout,
    )
    stdio_lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    stdio_payload = json.loads(stdio_lines[0]) if stdio_lines else {}

    ok = (
        manifest.get("ok") is True
        and bool(tool_names)
        and init is not None
        and init.get("result", {}).get("serverInfo", {}).get("name") == "promptbranch"
        and listed is not None
        and "tools" in listed.get("result", {})
        and host_config.get("ok") is True
        and "mcpServers" in host_config.get("config", {})
        and rc == 0
        and "tools" in stdio_payload.get("result", {})
    )
    if not ok:
        raise IntegrationAssertionError(
            f"mcp_smoke failed: manifest={manifest!r} init={init!r} listed={listed!r} host_config={host_config!r} stdio={stdio_payload!r}"
        )
    return {
        "ok": True,
        "action": "mcp_smoke",
        "manifest_tool_count": manifest.get("tool_count"),
        "tools": tool_names,
        "server_info": init.get("result", {}).get("serverInfo") if isinstance(init, dict) else None,
        "host_config": host_config.get("config"),
        "command_resolution": host_config.get("command_resolution"),
        "stdio_tool_count": len(stdio_payload.get("result", {}).get("tools", [])) if isinstance(stdio_payload.get("result"), dict) else None,
    }


def _run_mcp_host_smoke(*, repo_path: Path, profile_dir: Optional[str]) -> dict[str, Any]:
    result = mcp_host_smoke(repo_path=repo_path, profile_dir=profile_dir)
    if result.get("ok") is not True:
        raise IntegrationAssertionError(f"mcp_host_smoke failed: {result!r}")
    return result


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


def _normalize_expected_result(
    result: Any,
    *,
    status: str,
    expected_flag: str,
    message: str,
) -> Any:
    if not isinstance(result, dict):
        return result
    normalized = dict(result)
    normalized["service_ok"] = normalized.get("ok")
    normalized["ok"] = True
    normalized["status"] = status
    normalized[expected_flag] = True
    normalized["message"] = message
    return normalized


def _normalize_expected_missing_resolve_result(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    match_count = result.get("match_count")
    error = str(result.get("error") or "")
    if match_count != 0:
        return result
    if not (result.get("ok") is False and error == "project_not_found"):
        return result
    return _normalize_expected_result(
        result,
        status="expected_missing",
        expected_flag="expected_missing",
        message="Project does not exist yet; this is expected before ensure/create.",
    )


def _normalize_expected_skip_result(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    if result.get("skipped") is not True:
        return result
    reason = str(result.get("reason") or "").strip().lower()
    if reason == "unsupported":
        return _normalize_expected_result(
            result,
            status="expected_unsupported",
            expected_flag="expected_unsupported",
            message="Step skipped because the current ChatGPT UI/account does not support this source kind.",
        )
    return _normalize_expected_result(
        result,
        status="expected_skip",
        expected_flag="expected_skip",
        message="Step skipped as an expected suite precondition or capability limitation.",
    )


def _one_line_preview(value: Any, *, max_chars: int = 96) -> str:
    import re

    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _message_text_from_any_payload(raw: dict[str, Any]) -> str:
    direct = raw.get("text")
    if direct is not None:
        return str(direct)

    content = raw.get("content") if isinstance(raw.get("content"), dict) else None
    if not content:
        return ""

    parts = content.get("parts")
    if isinstance(parts, list):
        rendered: list[str] = []
        for part in parts:
            if isinstance(part, str):
                rendered.append(part)
            elif isinstance(part, dict):
                if isinstance(part.get("text"), str):
                    rendered.append(part["text"])
                elif isinstance(part.get("content"), str):
                    rendered.append(part["content"])
        return "\n".join(item for item in rendered if item).strip()

    if isinstance(content.get("text"), str):
        return content["text"]
    return ""


def _role_from_any_payload(raw: dict[str, Any]) -> str:
    author = raw.get("author") if isinstance(raw.get("author"), dict) else {}
    return str(raw.get("role") or author.get("role") or "").strip().lower()


def _turns_from_raw_conversation_mapping(payload: dict[str, Any]) -> list[dict[str, Any]]:
    mapping = payload.get("mapping") if isinstance(payload.get("mapping"), dict) else {}
    current_node = payload.get("current_node") or payload.get("currentNode")
    if not mapping or not current_node:
        return []

    node_ids: list[str] = []
    seen: set[str] = set()
    cursor = str(current_node)
    while cursor and cursor not in seen:
        seen.add(cursor)
        node_ids.append(cursor)
        node = mapping.get(cursor)
        if not isinstance(node, dict):
            break
        parent = node.get("parent")
        cursor = str(parent) if parent is not None else ""

    turns: list[dict[str, Any]] = []
    for node_id in reversed(node_ids):
        node = mapping.get(node_id)
        if not isinstance(node, dict):
            continue
        message = node.get("message") if isinstance(node.get("message"), dict) else None
        if not message:
            continue
        role = _role_from_any_payload(message)
        if role in {"", "system", "tool"}:
            continue
        text = _message_text_from_any_payload(message)
        if not text:
            continue
        turns.append({
            "index": len(turns) + 1,
            "id": node_id,
            "role": role,
            "text": text,
            "create_time": message.get("create_time") or message.get("createTime") or node.get("create_time") or node.get("createTime"),
            "status": message.get("status") or node.get("status") or "complete",
        })
    return turns


def _normalized_chat_turns(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_turns = payload.get("turns")
    if isinstance(raw_turns, list):
        turns: list[dict[str, Any]] = []
        for raw in raw_turns:
            if not isinstance(raw, dict):
                continue
            role = _role_from_any_payload(raw)
            text = _message_text_from_any_payload(raw)
            if not role or not text:
                continue
            turns.append({
                "index": raw.get("index") or len(turns) + 1,
                "id": raw.get("id"),
                "role": role,
                "text": text,
                "create_time": raw.get("create_time") or raw.get("createTime"),
                "status": raw.get("status") or "complete",
            })
        return turns

    raw_messages = payload.get("messages")
    if isinstance(raw_messages, list):
        return _normalized_chat_turns({"turns": raw_messages})

    return _turns_from_raw_conversation_mapping(payload)


def _messages_from_chat_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_turns = _normalized_chat_turns(payload)
    messages: list[dict[str, Any]] = []
    current_message: Optional[dict[str, Any]] = None

    for raw_turn in raw_turns:
        role = str(raw_turn.get("role") or "").strip().lower()
        text = str(raw_turn.get("text") or "")
        if role == "user":
            current_message = {
                "index": len(messages) + 1,
                "id": raw_turn.get("id"),
                "role": "user",
                "turn_index": raw_turn.get("index"),
                "text": text,
                "preview": _one_line_preview(text),
                "create_time": raw_turn.get("create_time"),
                "answers": [],
                "answer_count": 0,
                "answered": False,
            }
            messages.append(current_message)
            continue

        if role == "assistant" and current_message is not None:
            answers = current_message.setdefault("answers", [])
            answer = {
                "index": len(answers) + 1,
                "id": raw_turn.get("id"),
                "role": "assistant",
                "turn_index": raw_turn.get("index"),
                "text": text,
                "preview": _one_line_preview(text),
                "create_time": raw_turn.get("create_time"),
                "status": raw_turn.get("status") or "complete",
            }
            answers.append(answer)
            current_message["answer_count"] = len(answers)
            current_message["answered"] = bool(answers)

    return messages


def _task_messages_payload(chat_payload: dict[str, Any]) -> dict[str, Any]:
    messages = _messages_from_chat_payload(chat_payload)
    return {
        "ok": bool(chat_payload.get("ok", True)),
        "action": "task_messages_list",
        "project_url": chat_payload.get("project_url"),
        "conversation_url": chat_payload.get("conversation_url"),
        "conversation_id": chat_payload.get("conversation_id"),
        "title": chat_payload.get("title"),
        "message_count": len(messages),
        "messages": messages,
    }


def _latest_message(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    if not messages:
        raise IntegrationAssertionError(f"task transcript contained no user messages: {payload}")
    latest = messages[-1]
    if not isinstance(latest, dict):
        raise IntegrationAssertionError(f"task transcript latest message had unexpected shape: {latest!r}")
    return latest


def _extract_conversation_url_from_ask_result(result: Any) -> Optional[str]:
    if not isinstance(result, dict):
        return None
    for key in ("conversation_url", "chat_url", "url"):
        value = result.get(key)
        if isinstance(value, str) and "/c/" in value:
            return value
    conversation_id = result.get("conversation_id") or result.get("conversationId")
    project_url = result.get("project_url") or result.get("projectUrl")
    if isinstance(conversation_id, str) and isinstance(project_url, str):
        return project_url.rstrip("/").removesuffix("/project") + "/c/" + conversation_id
    return None


def _conversation_id_from_task_url(conversation_url: str) -> str:
    return str(conversation_url or "").rstrip("/").split("/c/", 1)[-1].split("/", 1)[0]


def _task_entries_from_list_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw_entries = payload.get("chats") or payload.get("items") or payload.get("conversations") or []
    return [item for item in raw_entries if isinstance(item, dict)] if isinstance(raw_entries, list) else []


def _task_entry_matches_conversation(item: dict[str, Any], *, conversation_url: str, conversation_id: str) -> bool:
    candidate_url = str(item.get("conversation_url") or item.get("url") or "").rstrip("/")
    candidate_id = str(item.get("conversation_id") or item.get("id") or "")
    return (
        bool(candidate_url) and candidate_url == str(conversation_url).rstrip("/")
    ) or (
        bool(candidate_id) and candidate_id == conversation_id
    )


def _task_entry_is_indexed(item: dict[str, Any]) -> bool:
    return str(item.get("source") or "").strip().lower() in {"snorlax", "project_endpoint", "dom", "history", "current_page", ""}


def _task_list_visibility_status_for_match(matched: dict[str, Any] | None) -> str:
    if matched is None:
        return "missing"
    return "indexed" if _task_entry_is_indexed(matched) else "recent_state_only"


async def _wait_for_task_visible_in_list(
    steps: list[StepResult],
    service: Any,
    *,
    conversation_url: str,
    keep_open: bool,
    timeout_seconds: float,
    poll_min_seconds: float,
    poll_max_seconds: float,
    max_attempts: int,
    allow_recent_state_fallback: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    conversation_id = _conversation_id_from_task_url(conversation_url)
    deadline = time.monotonic() + max(0.0, float(timeout_seconds or 0.0))
    delay = max(1.0, float(poll_min_seconds or 1.0))
    max_delay = max(delay, float(poll_max_seconds or delay))
    attempts_allowed = max(1, int(max_attempts or 1))
    attempts: list[dict[str, Any]] = []
    started = time.perf_counter()
    last_payload: dict[str, Any] = {}
    last_entries: list[dict[str, Any]] = []

    try:
        for attempt_index in range(1, attempts_allowed + 1):
            include_history_fallback = attempt_index == attempts_allowed
            payload = await service.list_project_chats(
                keep_open=keep_open,
                include_history_fallback=include_history_fallback,
            )
            last_payload = payload if isinstance(payload, dict) else {}
            entries = _task_entries_from_list_payload(last_payload)
            last_entries = entries
            matched = next(
                (
                    item
                    for item in entries
                    if _task_entry_matches_conversation(
                        item,
                        conversation_url=conversation_url,
                        conversation_id=conversation_id,
                    )
                ),
                None,
            )
            visibility_status = _task_list_visibility_status_for_match(matched)
            attempts.append(
                {
                    "attempt": attempt_index,
                    "count": len(entries),
                    "matched": matched is not None,
                    "matched_source": matched.get("source") if isinstance(matched, dict) else None,
                    "visibility_status": visibility_status,
                    "include_history_fallback": include_history_fallback,
                    "history_fallback_used": last_payload.get("history_fallback_used"),
                    "source_counts": last_payload.get("source_counts"),
                }
            )
            if matched is not None and (visibility_status == "indexed" or allow_recent_state_fallback):
                details = {
                    "ok": True,
                    "conversation_url": conversation_url,
                    "conversation_id": conversation_id,
                    "attempts": attempts,
                    "visibility_status": visibility_status,
                    "allow_recent_state_fallback": allow_recent_state_fallback,
                    "task_list_count": len(entries),
                    "matched_task": matched,
                    "last_task_list": last_payload,
                }
                if visibility_status != "indexed":
                    details["degraded"] = True
                    details["warning"] = "task matched only via recent_state fallback, not indexed task sources"
                steps.append(
                    StepResult(
                        name="task_message_flow.task_list_visible",
                        ok=True,
                        duration_seconds=round(time.perf_counter() - started, 3),
                        details=details,
                    )
                )
                return last_payload, entries, matched

            now = time.monotonic()
            if attempt_index >= attempts_allowed or now >= deadline:
                break
            sleep_for = min(delay, max(0.0, deadline - now))
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            delay = min(max_delay, delay * 1.75)

        raise IntegrationAssertionError(
            "task_message_flow created task was not visible in indexed task list after bounded polling. recent_state is a degraded fallback and does not count unless explicitly allowed. "
            f"conversation_url={conversation_url!r} attempts={attempts} task_list={last_payload}"
        )
    except Exception as exc:
        steps.append(
            StepResult(
                name="task_message_flow.task_list_visible",
                ok=False,
                duration_seconds=round(time.perf_counter() - started, 3),
                details={
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "conversation_url": conversation_url,
                    "conversation_id": conversation_id,
                    "attempts": attempts,
                    "last_task_list_count": len(last_entries),
                    "last_task_list": last_payload,
                    "allow_recent_state_fallback": allow_recent_state_fallback,
                },
            )
        )
        raise


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
        "error": None,
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
        if should_run("mcp_smoke"):
            await _run_step(
                steps,
                "mcp_smoke",
                asyncio.to_thread(_run_mcp_smoke, repo_path=Path.cwd(), profile_dir=args.profile_dir),
                step_delay_seconds=args.step_delay_seconds,
            )

        if should_run("mcp_host_smoke"):
            await _run_step(
                steps,
                "mcp_host_smoke",
                asyncio.to_thread(_run_mcp_host_smoke, repo_path=Path.cwd(), profile_dir=args.profile_dir),
                step_delay_seconds=args.step_delay_seconds,
            )

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
            initial_resolve_raw = await _run_step(
                steps,
                "project_resolve_before_create",
                base_service.resolve_project(name=project_name, keep_open=args.keep_open),
                step_delay_seconds=args.step_delay_seconds,
            )
            initial_resolve = _normalize_expected_missing_resolve_result(initial_resolve_raw)
            if steps and steps[-1].name == "project_resolve_before_create":
                steps[-1].details = initial_resolve
            _require(initial_resolve_raw.get("match_count") in {0, 1}, f"unexpected pre-create resolve result: {initial_resolve_raw}")
            _require(
                initial_resolve_raw.get("match_count") == 0 or bool(args.project_name),
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
                    details=_normalize_expected_skip_result(
                        {
                            "skipped": True,
                            "reason": "unsupported",
                            "requested_source_kind": "link",
                            "available_source_kinds": available_source_kinds,
                        }
                    ),
                )

        if should_run("project_source_add_text"):
            # Keep the release-blocking Project Sources text-add check focused on
            # text-source persistence.  Large-paste document conversion is a
            # volatile ChatGPT UI behavior and is characterized separately by
            # add_project_source diagnostics; it must not make the core text
            # source add step depend on a generated filename contract.
            text_source_value = "\n".join(
                [
                    f"Integration note for run {run_id}",
                    f"Promptbranch text-source add smoke proof for run {run_id}.",
                    "This body is intentionally below the configured document-conversion threshold.",
                ]
            )
            text_add = await _run_step(
                steps,
                "project_source_add_text",
                project_service.add_project_source(
                    source_kind="text",
                    value=text_source_value,
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

        if should_run("project_source_overwrite_file"):
            file_overwrite = await _run_step(
                steps,
                "project_source_overwrite_file",
                project_service.add_project_source(
                    source_kind="file",
                    file_path=str(file_source_path),
                    display_name=None,
                    keep_open=args.keep_open,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(file_overwrite.get("ok") is True, f"file source overwrite failed: {file_overwrite}")
            _require(file_overwrite.get("already_exists") is True, f"file source overwrite did not detect an existing source: {file_overwrite}")
            _require(file_overwrite.get("overwritten") is True, f"file source overwrite did not report overwritten=true: {file_overwrite}")
            _require(file_overwrite.get("removed_existing") is True, f"file source overwrite did not verify removal before re-upload: {file_overwrite}")
            _require(file_overwrite.get("persistence_verified") is True, f"file source overwrite did not verify persistence: {file_overwrite}")
            overwrite_remove_result = file_overwrite.get("overwrite_remove_result")
            if isinstance(overwrite_remove_result, dict):
                remove_results.append(overwrite_remove_result)
            file_source_match = str(file_overwrite.get("source_match") or file_source_match)

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
            await _post_ask_cooldown(steps, seconds=args.post_ask_delay_seconds, reason="after ask_question")

        if should_run("task_message_flow"):
            task_prompt = (
                f"Promptbranch task/message live smoke {run_id}. "
                "Reply with exactly the single token TASK_MESSAGE_OK and nothing else."
            )
            task_ask = await _run_step(
                steps,
                "task_message_flow.ask",
                project_service.ask_question_result(
                    prompt=task_prompt,
                    expect_json=False,
                    keep_open=args.keep_open,
                    retries=0,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            _require(isinstance(task_ask, dict), f"task_message_flow ask did not return a structured payload: {task_ask!r}")
            task_answer_text = str(task_ask.get("answer") or "")
            _require(
                "TASK_MESSAGE_OK" in task_answer_text.upper(),
                f"task_message_flow ask answer did not contain TASK_MESSAGE_OK. response={task_answer_text!r}",
            )
            task_conversation_url = _extract_conversation_url_from_ask_result(task_ask)
            _require(
                bool(task_conversation_url),
                f"task_message_flow ask did not return a conversation URL/id: {task_ask}",
            )
            await _post_ask_cooldown(steps, seconds=args.post_ask_delay_seconds, reason="after task_message_flow.ask")

            task_list, task_entries, listed_match = await _wait_for_task_visible_in_list(
                steps,
                project_service,
                conversation_url=str(task_conversation_url),
                keep_open=args.keep_open,
                timeout_seconds=args.task_list_visible_timeout_seconds,
                poll_min_seconds=args.task_list_visible_poll_min_seconds,
                poll_max_seconds=args.task_list_visible_poll_max_seconds,
                max_attempts=args.task_list_visible_max_attempts,
                allow_recent_state_fallback=getattr(args, "allow_recent_state_task_fallback", False),
            )

            task_chat = await _run_step(
                steps,
                "task_message_flow.task_get",
                project_service.get_chat(
                    conversation_url=str(task_conversation_url),
                    keep_open=args.keep_open,
                ),
                step_delay_seconds=args.step_delay_seconds,
            )
            task_messages = _task_messages_payload(task_chat)
            latest_message = _latest_message(task_messages)
            latest_answers = latest_message.get("answers") if isinstance(latest_message.get("answers"), list) else []
            latest_answer_text = "\n".join(str(answer.get("text") or "") for answer in latest_answers if isinstance(answer, dict))
            _require(
                task_prompt in str(latest_message.get("text") or ""),
                f"task_message_flow latest message did not contain the smoke prompt. latest_message={latest_message}",
            )
            _require(
                "TASK_MESSAGE_OK" in latest_answer_text.upper(),
                f"task_message_flow latest answer did not contain TASK_MESSAGE_OK. latest_message={latest_message}",
            )
            _record_step(
                steps,
                "task_message_flow",
                ok=True,
                details={
                    "ok": True,
                    "action": "task_message_flow",
                    "conversation_url": task_conversation_url,
                    "task_list_count": len(task_entries) if isinstance(task_entries, list) else None,
                    "message_count": task_messages.get("message_count"),
                    "latest_message_index": latest_message.get("index"),
                    "latest_answer_count": len(latest_answers),
                },
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
                    details=_normalize_expected_skip_result(
                        {
                            "skipped": True,
                            "reason": "unsupported",
                            "requested_source_kind": "link",
                            "available_source_kinds": available_source_kinds,
                        }
                    ),
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
    except Exception as exc:
        summary["ok"] = False
        summary["error"] = {
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        summary["artifacts"]["link_source_match"] = link_source_match
        summary["artifacts"]["text_source_match"] = text_source_match
        summary["artifacts"]["file_source_match"] = file_source_match
        summary["steps"] = [asdict(step) for step in steps]

        if project_url and cleanup_enabled:
            try:
                project_service = build_service(args, project_url=project_url)
                await _remove_project_cleanup_with_retry(
                    cleanup_steps,
                    project_service,
                    keep_open=args.keep_open,
                    step_delay_seconds=args.step_delay_seconds,
                    max_attempts=5,
                    project_name=project_name,
                )
            except Exception as exc:
                if not cleanup_steps or bool(cleanup_steps[-1].ok):
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

        cleanup_failures = [step for step in cleanup_steps if not bool(step.ok)]
        if cleanup_failures:
            summary["ok"] = False
            summary.setdefault("cleanup_error", str(cleanup_failures[-1].details))
        summary["cleanup_failure_count"] = len(cleanup_failures)
        summary["cleanup_failed_steps"] = [asdict(step) for step in cleanup_failures]
        summary["cleanup_steps"] = [asdict(step) for step in cleanup_steps]

    return summary



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



from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from chatgpt_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings
from chatgpt_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
)

DEFAULT_PROJECT_URL = "https://chatgpt.com/"
DEFAULT_PROFILE_DIR = "./profile"
DEFAULT_MAX_RETRIES = 1


@dataclass
class StepResult:
    name: str
    ok: bool
    duration_seconds: float
    details: Any


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


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a full browser-backed ChatGPT integration flow against the current client/service layer. "
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
    parser.add_argument("--project-name", help="Explicit project name to use. Defaults to a generated unique name.")
    parser.add_argument("--project-name-prefix", default="itest-chatgpt-workflow")
    parser.add_argument("--run-id", help="Optional run identifier used when generating names.")
    parser.add_argument("--memory-mode", choices=["default", "project-only"], default="default")
    parser.add_argument("--link-url", default="https://example.com/")
    parser.add_argument("--ask-prompt", default="Reply with exactly the single token INTEGRATION_OK and nothing else.")
    parser.add_argument("--json-out", help="Optional file path where the final JSON summary will be written.")
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
    )


def build_service(args: argparse.Namespace, *, project_url: str) -> ChatGPTAutomationService:
    return ChatGPTAutomationService(build_settings(args, project_url=project_url))


async def _run_step(steps: list[StepResult], name: str, coro) -> Any:
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
    text_source_name = f"itest-text-{run_id}"
    file_source_match = file_source_path.name

    summary: dict[str, Any] = {
        "ok": False,
        "run_id": run_id,
        "project_name": project_name,
        "project_url": None,
        "project_id": None,
        "kept_project": bool(args.keep_project),
        "steps": [],
        "cleanup_steps": [],
        "artifacts": {
            "temp_dir": str(temp_dir),
            "file_source_path": str(file_source_path),
        },
    }

    try:
        login = await _run_step(
            steps,
            "login_check",
            base_service.run_login_check(keep_open=args.keep_open),
        )
        _require(login.get("logged_in") is True, f"login_check did not report an active session: {login}")

        initial_resolve = await _run_step(
            steps,
            "project_resolve_before_create",
            base_service.resolve_project(name=project_name, keep_open=args.keep_open),
        )
        _require(initial_resolve.get("match_count") in {0, 1}, f"unexpected pre-create resolve result: {initial_resolve}")
        _require(
            initial_resolve.get("match_count") == 0 or bool(args.project_name),
            (
                "generated project name already exists before test start; refusing to continue because the run would not be isolated. "
                "Pass --project-name only when you intentionally want to reuse an existing project."
            ),
        )

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
        )
        _require(ensure_created.get("ok") is True, f"project_ensure failed: {ensure_created}")
        project_url = ensure_created.get("project_url")
        _require(bool(project_url), f"project_ensure did not return project_url: {ensure_created}")
        project_id = _extract_project_id(project_url)
        _require(bool(project_id), f"project_ensure returned a project_url without a project_id: {ensure_created}")
        summary["project_url"] = project_url
        summary["project_id"] = project_id

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
        )
        _require(ensure_idempotent.get("ok") is True, f"second project_ensure failed: {ensure_idempotent}")
        _require(ensure_idempotent.get("created") is False, f"second project_ensure was not idempotent: {ensure_idempotent}")
        _require(
            _same_project(ensure_idempotent.get("project_url"), project_url),
            f"second project_ensure returned a different project identity: {ensure_idempotent}",
        )

        resolved = await _run_step(
            steps,
            "project_resolve_after_ensure",
            base_service.resolve_project(name=project_name, keep_open=args.keep_open),
        )
        _require(resolved.get("ok") is True, f"project_resolve failed after ensure: {resolved}")
        _require(resolved.get("match_count") == 1, f"project_resolve did not uniquely match the project: {resolved}")
        _require(
            _same_project(resolved.get("project_url"), project_url),
            f"project_resolve returned a mismatched project identity: {resolved}",
        )

        project_service = build_service(args, project_url=project_url)

        source_capabilities = await _run_step(
            steps,
            "project_source_capabilities",
            project_service.discover_project_source_capabilities(keep_open=args.keep_open),
        )
        available_source_kinds = list(source_capabilities.get("available_source_kinds") or [])
        summary["available_source_kinds"] = available_source_kinds
        link_supported = "link" in set(available_source_kinds)
        summary["link_source_supported"] = link_supported

        link_add: Optional[dict[str, Any]] = None
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
            )
            _require(link_add.get("ok") is True, f"link source add failed: {link_add}")
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

        text_add = await _run_step(
            steps,
            "project_source_add_text",
            project_service.add_project_source(
                source_kind="text",
                value=f"Integration note for run {run_id}",
                display_name=text_source_name,
                keep_open=args.keep_open,
            ),
        )
        _require(text_add.get("ok") is True, f"text source add failed: {text_add}")

        file_add = await _run_step(
            steps,
            "project_source_add_file",
            project_service.add_project_source(
                source_kind="file",
                file_path=str(file_source_path),
                display_name=None,
                keep_open=args.keep_open,
            ),
        )
        _require(file_add.get("ok") is True, f"file source add failed: {file_add}")

        ask_result = await _run_step(
            steps,
            "ask_question",
            project_service.ask_question(
                prompt=args.ask_prompt,
                expect_json=False,
                keep_open=args.keep_open,
                retries=0,
            ),
        )
        if isinstance(ask_result, (dict, list)):
            ask_text = json.dumps(ask_result, ensure_ascii=False)
        else:
            ask_text = str(ask_result)
        _require(
            "INTEGRATION_OK" in ask_text.upper(),
            f"ask_question did not contain the expected token. response={ask_text!r}",
        )

        if link_supported:
            link_remove = await _run_step(
                steps,
                "project_source_remove_link",
                project_service.remove_project_source(
                    source_name=link_source_name,
                    exact=True,
                    keep_open=args.keep_open,
                ),
            )
            _require(link_remove.get("ok") is True, f"link source remove failed: {link_remove}")
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

        text_remove = await _run_step(
            steps,
            "project_source_remove_text",
            project_service.remove_project_source(
                source_name=text_source_name,
                exact=True,
                keep_open=args.keep_open,
            ),
        )
        _require(text_remove.get("ok") is True, f"text source remove failed: {text_remove}")

        file_remove = await _run_step(
            steps,
            "project_source_remove_file",
            project_service.remove_project_source(
                source_name=file_source_match,
                exact=False,
                keep_open=args.keep_open,
            ),
        )
        _require(file_remove.get("ok") is True, f"file source remove failed: {file_remove}")

        summary["ok"] = True
        return summary
    finally:
        summary["steps"] = [asdict(step) for step in steps]

        if project_url and not args.keep_project:
            try:
                project_service = build_service(args, project_url=project_url)
                removal_result = await _run_step(
                    cleanup_steps,
                    "project_remove_cleanup",
                    project_service.remove_project(keep_open=args.keep_open),
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

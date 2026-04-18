from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any, Optional, Protocol

from dotenv import load_dotenv

from chatgpt_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings
from chatgpt_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
)
from chatgpt_service_client import ChatGPTServiceClient

DEFAULT_PROJECT_URL = "https://chatgpt.com/"
DEFAULT_PROFILE_DIR = "./profile"
DEFAULT_MAX_RETRIES = 2
DEFAULT_SERVICE_TIMEOUT_SECONDS = 300.0
COMMANDS = {
    "login-check",
    "ask",
    "shell",
    "project-create",
    "project-resolve",
    "project-ensure",
    "project-remove",
    "project-source-add",
    "project-source-remove",
}
GLOBAL_OPTION_HAS_VALUE = {
    "--project-url": True,
    "--email": True,
    "--password": True,
    "--password-file": True,
    "--profile-dir": True,
    "--headless": False,
    "--use-playwright": False,
    "--browser-channel": True,
    "--enable-fedcm": False,
    "--keep-no-sandbox": False,
    "--max-retries": True,
    "--retry-backoff-seconds": True,
    "--debug": False,
    "--dotenv": True,
    "--service-base-url": True,
    "--service-token": True,
    "--service-timeout-seconds": True,
}


class CommandBackend(Protocol):
    async def login_check(self, *, keep_open: bool = False) -> dict[str, Any]: ...

    async def create_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]: ...

    async def resolve_project(self, name: str, *, keep_open: bool = False) -> dict[str, Any]: ...

    async def ensure_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]: ...

    async def remove_project(self, *, keep_open: bool = False) -> dict[str, Any]: ...

    async def add_project_source(
        self,
        *,
        source_kind: str,
        value: Optional[str] = None,
        file_path: Optional[str] = None,
        display_name: Optional[str] = None,
        keep_open: bool = False,
    ) -> dict[str, Any]: ...

    async def remove_project_source(
        self,
        source_name: str,
        *,
        exact: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]: ...

    async def ask(
        self,
        prompt: str,
        *,
        file_path: Optional[str] = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
    ) -> Any: ...


class DirectBackend:
    def __init__(self, service: ChatGPTAutomationService) -> None:
        self._service = service

    async def login_check(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._service.run_login_check(keep_open=keep_open)

    async def create_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self._service.create_project(
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
        )

    async def resolve_project(self, name: str, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._service.resolve_project(name=name, keep_open=keep_open)

    async def ensure_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self._service.ensure_project(
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
        )

    async def remove_project(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._service.remove_project(keep_open=keep_open)

    async def add_project_source(
        self,
        *,
        source_kind: str,
        value: Optional[str] = None,
        file_path: Optional[str] = None,
        display_name: Optional[str] = None,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self._service.add_project_source(
            source_kind=source_kind,
            value=value,
            file_path=file_path,
            display_name=display_name,
            keep_open=keep_open,
        )

    async def remove_project_source(
        self,
        source_name: str,
        *,
        exact: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self._service.remove_project_source(
            source_name=source_name,
            exact=exact,
            keep_open=keep_open,
        )

    async def ask(
        self,
        prompt: str,
        *,
        file_path: Optional[str] = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
    ) -> Any:
        return await self._service.ask_question(
            prompt=prompt,
            file_path=file_path,
            expect_json=expect_json,
            keep_open=keep_open,
            retries=retries,
        )


class ServiceBackend:
    def __init__(
        self,
        *,
        base_url: str,
        token: Optional[str],
        timeout: float,
        project_url: Optional[str],
    ) -> None:
        self._client = ChatGPTServiceClient(base_url, token=token, timeout=timeout)
        self._project_url = project_url

    async def _call(self, fn, /, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def login_check(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._call(self._client.login_check, keep_open=keep_open)

    async def create_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self._call(
            self._client.create_project,
            name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
            project_url=self._project_url,
        )

    async def resolve_project(self, name: str, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._call(
            self._client.resolve_project,
            name,
            keep_open=keep_open,
            project_url=self._project_url,
        )

    async def ensure_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self._call(
            self._client.ensure_project,
            name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
            project_url=self._project_url,
        )

    async def remove_project(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._call(
            self._client.remove_project,
            keep_open=keep_open,
            project_url=self._project_url,
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
        return await self._call(
            self._client.add_project_source,
            source_kind=source_kind,
            value=value,
            file_path=file_path,
            display_name=display_name,
            keep_open=keep_open,
            project_url=self._project_url,
        )

    async def remove_project_source(
        self,
        source_name: str,
        *,
        exact: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self._call(
            self._client.remove_project_source,
            source_name,
            exact=exact,
            keep_open=keep_open,
            project_url=self._project_url,
        )

    async def ask(
        self,
        prompt: str,
        *,
        file_path: Optional[str] = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
    ) -> Any:
        return await self._call(
            self._client.ask,
            prompt,
            file_path=file_path,
            expect_json=expect_json,
            keep_open=keep_open,
            retries=retries,
            project_url=self._project_url,
        )


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


def build_service(args: argparse.Namespace) -> ChatGPTAutomationService:
    settings = ChatGPTAutomationSettings(
        project_url=args.project_url,
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
    return ChatGPTAutomationService(settings)


def build_backend(args: argparse.Namespace) -> CommandBackend:
    if args.service_base_url:
        return ServiceBackend(
            base_url=args.service_base_url,
            token=args.service_token,
            timeout=args.service_timeout_seconds,
            project_url=args.project_url,
        )
    return DirectBackend(build_service(args))


async def cmd_login_check(backend: CommandBackend, args: argparse.Namespace) -> int:
    result = await backend.login_check(keep_open=args.keep_open)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


async def cmd_project_create(backend: CommandBackend, args: argparse.Namespace) -> int:
    result = await backend.create_project(
        name=args.name,
        icon=args.icon,
        color=args.color,
        memory_mode=args.memory_mode,
        keep_open=args.keep_open,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


async def cmd_project_resolve(backend: CommandBackend, args: argparse.Namespace) -> int:
    result = await backend.resolve_project(
        name=args.name,
        keep_open=args.keep_open,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


async def cmd_project_ensure(backend: CommandBackend, args: argparse.Namespace) -> int:
    result = await backend.ensure_project(
        name=args.name,
        icon=args.icon,
        color=args.color,
        memory_mode=args.memory_mode,
        keep_open=args.keep_open,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


async def cmd_project_remove(backend: CommandBackend, args: argparse.Namespace) -> int:
    result = await backend.remove_project(keep_open=args.keep_open)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


async def cmd_project_source_add(backend: CommandBackend, args: argparse.Namespace) -> int:
    source_kind = args.type
    value = args.value
    file_path = args.file
    if source_kind == "file" and not file_path:
        print("error: --file is required when --type=file", file=sys.stderr)
        return 2
    if source_kind in {"link", "text"} and not value:
        print(f"error: --value is required when --type={source_kind}", file=sys.stderr)
        return 2

    result = await backend.add_project_source(
        source_kind=source_kind,
        value=value,
        file_path=file_path,
        display_name=args.name,
        keep_open=args.keep_open,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


async def cmd_project_source_remove(backend: CommandBackend, args: argparse.Namespace) -> int:
    result = await backend.remove_project_source(
        source_name=args.source_name,
        exact=args.exact,
        keep_open=args.keep_open,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


async def cmd_ask(backend: CommandBackend, args: argparse.Namespace) -> int:
    prompt = args.prompt
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    if not prompt:
        print("error: prompt is required", file=sys.stderr)
        return 2

    response = await backend.ask(
        prompt=prompt,
        file_path=args.file,
        expect_json=args.json,
        keep_open=args.keep_open,
        retries=args.retries,
    )
    if isinstance(response, (dict, list)):
        print(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        print(response)
    return 0


HELP_TEXT = """Commands:
  :help                 show this help
  :quit                 exit the shell
  :login                run login-check
  :json on|off          toggle JSON response mode
  :file <path>          attach a file for subsequent prompts
  :clearfile            remove attached file
  :show                 display current shell settings
  :retry <n>            set per-prompt retries
Anything else is sent as a prompt to ChatGPT.
"""


async def cmd_shell(backend: CommandBackend, args: argparse.Namespace) -> int:
    json_mode = args.json
    attached_file: Optional[str] = args.file
    retries: Optional[int] = args.retries

    print("ChatGPT CLI shell")
    print("Type :help for commands.")

    while True:
        try:
            line = input("chatgpt> ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 130

        if not line:
            continue
        if line == ":help":
            print(HELP_TEXT)
            continue
        if line in {":quit", ":exit"}:
            return 0
        if line == ":login":
            result = await backend.login_check(keep_open=args.keep_open)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            continue
        if line.startswith(":json "):
            value = line.split(None, 1)[1].strip().lower()
            if value not in {"on", "off"}:
                print("usage: :json on|off", file=sys.stderr)
                continue
            json_mode = value == "on"
            print(f"json_mode={json_mode}")
            continue
        if line.startswith(":file "):
            try:
                parts = shlex.split(line)
            except ValueError as exc:
                print(f"file parse error: {exc}", file=sys.stderr)
                continue
            if len(parts) < 2:
                print("usage: :file <path>", file=sys.stderr)
                continue
            path = str(Path(parts[1]).expanduser().resolve())
            if not os.path.exists(path):
                print(f"file not found: {path}", file=sys.stderr)
                continue
            attached_file = path
            print(f"attached_file={attached_file}")
            continue
        if line == ":clearfile":
            attached_file = None
            print("attached_file=None")
            continue
        if line == ":show":
            print(json.dumps({"json_mode": json_mode, "attached_file": attached_file, "retries": retries}, indent=2))
            continue
        if line.startswith(":retry "):
            value = line.split(None, 1)[1].strip()
            try:
                retries = int(value)
                if retries < 0:
                    raise ValueError("must be >= 0")
            except ValueError as exc:
                print(f"invalid retry value: {exc}", file=sys.stderr)
                continue
            print(f"retries={retries}")
            continue

        print("\n--- response ---")
        try:
            response = await backend.ask(
                prompt=line,
                file_path=attached_file,
                expect_json=json_mode,
                keep_open=args.keep_open,
                retries=retries,
            )
            if isinstance(response, (dict, list)):
                print(json.dumps(response, indent=2, ensure_ascii=False))
            else:
                print(response)
        except KeyboardInterrupt:
            print("interrupted", file=sys.stderr)
            return 130
        print("--- end ---\n")


def _normalize_global_options(argv: list[str]) -> list[str]:
    """Allow global options before or after the subcommand.

    Argparse normally requires root-parser options to appear before the subcommand.
    For CLI ergonomics we lift known global options out of argv, preserving the
    subcommand-local arguments in place.
    """
    normalized_globals: list[str] = []
    normalized_rest: list[str] = []

    i = 0
    while i < len(argv):
        token = argv[i]

        if token in COMMANDS and token not in normalized_rest:
            normalized_rest.append(token)
            i += 1
            continue

        if token.startswith("--"):
            option_name, has_inline_value = (token.split("=", 1)[0], "=" in token)
            expects_value = GLOBAL_OPTION_HAS_VALUE.get(option_name)
            if expects_value is not None:
                normalized_globals.append(token)
                if expects_value and not has_inline_value and i + 1 < len(argv):
                    normalized_globals.append(argv[i + 1])
                    i += 2
                    continue
                i += 1
                continue

        normalized_rest.append(token)
        i += 1

    return normalized_globals + normalized_rest


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Single CLI tool for ChatGPT browser automation or the Docker service API.",
    )
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
    parser.add_argument("--dotenv", default=".env", help="Optional .env file to load before reading env vars.")
    parser.add_argument("--service-base-url", default=os.getenv("CHATGPT_SERVICE_BASE_URL"), help="Use the Docker service API instead of local browser automation.")
    parser.add_argument("--service-token", default=os.getenv("CHATGPT_SERVICE_TOKEN"), help="Bearer token for the Docker service API.")
    parser.add_argument("--service-timeout-seconds", type=float, default=float(os.getenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", str(DEFAULT_SERVICE_TIMEOUT_SECONDS))))

    subparsers = parser.add_subparsers(dest="command", required=True)

    login = subparsers.add_parser("login-check", help="Open the browser and verify whether the profile is logged in.")
    login.add_argument("--keep-open", action="store_true")

    project_create = subparsers.add_parser(
        "project-create",
        help="Create a new ChatGPT project and return its URL.",
    )
    project_create.add_argument("name", help="Project name to create.")
    project_create.add_argument("--icon", help="Optional project icon name/value to select when available.")
    project_create.add_argument("--color", help="Optional project color name/value to select when available.")
    project_create.add_argument(
        "--memory-mode",
        choices=["default", "project-only"],
        default="default",
        help="Project memory mode to request during creation.",
    )
    project_create.add_argument("--keep-open", action="store_true")

    project_resolve = subparsers.add_parser(
        "project-resolve",
        help="Resolve a ChatGPT project by exact name and return its URL when uniquely matched.",
    )
    project_resolve.add_argument("name", help="Project name to resolve by exact visible name.")
    project_resolve.add_argument("--keep-open", action="store_true")

    project_ensure = subparsers.add_parser(
        "project-ensure",
        help="Resolve a ChatGPT project by exact name, creating it only when missing.",
    )
    project_ensure.add_argument("name", help="Project name to resolve or create.")
    project_ensure.add_argument("--icon", help="Optional project icon name/value to select when creation is needed.")
    project_ensure.add_argument("--color", help="Optional project color name/value to select when creation is needed.")
    project_ensure.add_argument(
        "--memory-mode",
        choices=["default", "project-only"],
        default="default",
        help="Project memory mode to request during creation when a project does not already exist.",
    )
    project_ensure.add_argument("--keep-open", action="store_true")

    project_remove = subparsers.add_parser(
        "project-remove",
        help="Delete the configured ChatGPT project referenced by --project-url.",
    )
    project_remove.add_argument("--keep-open", action="store_true")

    source_add = subparsers.add_parser(
        "project-source-add",
        help="Add a source to the configured ChatGPT project (Sources tab).",
    )
    source_add.add_argument("--type", choices=["link", "text", "file"], required=True)
    source_add.add_argument("--value", help="Source payload for link/text sources.")
    source_add.add_argument("--file", help="Local file path for file sources.")
    source_add.add_argument("--name", help="Optional display name/title to set when the UI supports it.")
    source_add.add_argument("--keep-open", action="store_true")

    source_remove = subparsers.add_parser(
        "project-source-remove",
        help="Remove a source from the configured ChatGPT project (Sources tab).",
    )
    source_remove.add_argument("source_name", help="Visible source name or unique snippet to remove.")
    source_remove.add_argument("--exact", action="store_true", help="Require an exact visible text match.")
    source_remove.add_argument("--keep-open", action="store_true")

    ask = subparsers.add_parser("ask", help="Send one prompt and print the response.")
    ask.add_argument("prompt", nargs="?", help="Prompt text. If omitted, stdin is read.")
    ask.add_argument("--file", help="Optional file to upload with the prompt.")
    ask.add_argument("--json", action="store_true", help="Request strict JSON mode.")
    ask.add_argument("--keep-open", action="store_true")
    ask.add_argument("--retries", type=int)

    shell = subparsers.add_parser("shell", help="Interactive prompt loop.")
    shell.add_argument("--file", help="Optional file to attach by default.")
    shell.add_argument("--json", action="store_true", help="Start shell in JSON mode.")
    shell.add_argument("--keep-open", action="store_true")
    shell.add_argument("--retries", type=int)

    return parser


def _extract_dotenv_path(argv: list[str]) -> Optional[str]:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--dotenv", default=".env")
    args, _ = bootstrap.parse_known_args(argv)
    return args.dotenv


def _max_retries_was_configured(argv: list[str]) -> bool:
    if "CHATGPT_MAX_RETRIES" in os.environ:
        return True
    for token in argv:
        if token == "--max-retries" or token.startswith("--max-retries="):
            return True
    return False


async def _async_main(args: argparse.Namespace) -> int:
    backend = build_backend(args)
    if args.command == "login-check":
        return await cmd_login_check(backend, args)
    if args.command == "project-create":
        return await cmd_project_create(backend, args)
    if args.command == "project-resolve":
        return await cmd_project_resolve(backend, args)
    if args.command == "project-ensure":
        return await cmd_project_ensure(backend, args)
    if args.command == "project-remove":
        return await cmd_project_remove(backend, args)
    if args.command == "project-source-add":
        return await cmd_project_source_add(backend, args)
    if args.command == "project-source-remove":
        return await cmd_project_source_remove(backend, args)
    if args.command == "ask":
        return await cmd_ask(backend, args)
    if args.command == "shell":
        return await cmd_shell(backend, args)
    raise RuntimeError(f"Unknown command: {args.command}")


def main(argv: Optional[list[str]] = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    normalized_argv = _normalize_global_options(raw_argv)

    dotenv_path = _extract_dotenv_path(normalized_argv)
    if dotenv_path:
        load_dotenv(dotenv_path, override=False)

    parser = make_parser()
    args = parser.parse_args(normalized_argv)
    if args.debug and not _max_retries_was_configured(normalized_argv):
        args.max_retries = 1
    _configure_logging(args.debug)

    try:
        return asyncio.run(_async_main(args))
    except ManualLoginRequiredError as exc:
        print(f"manual login required: {exc}", file=sys.stderr)
        return 10
    except BotChallengeError as exc:
        print(f"browser challenge detected: {exc}", file=sys.stderr)
        return 11
    except ResponseTimeoutError as exc:
        print(f"response timeout: {exc}", file=sys.stderr)
        return 12
    except UnsupportedOperationError as exc:
        print(f"unsupported operation: {exc}", file=sys.stderr)
        return 15
    except AuthenticationError as exc:
        print(f"authentication error: {exc}", file=sys.stderr)
        return 13
    except FileNotFoundError as exc:
        print(f"file not found: {exc}", file=sys.stderr)
        return 14


if __name__ == "__main__":
    raise SystemExit(main())

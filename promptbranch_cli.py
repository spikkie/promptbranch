from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Optional, Protocol

from dotenv import load_dotenv

from promptbranch_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings
from promptbranch_artifacts import ArtifactRegistry, create_repo_snapshot, verify_zip_artifact
from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
)
from promptbranch_service_client import ChatGPTServiceClient
from promptbranch_test_suite import run_test_suite_async
from promptbranch_state import (
    DEFAULT_PROJECT_URL,
    STATE_FILE_NAME,
    ConversationStateStore,
    GlobalProjectCache,
    PROFILE_DIR_NAME,
    resolve_profile_dir,
    conversation_id_from_url,
    project_home_url_from_url,
    project_name_from_url,
)

DEFAULT_MAX_RETRIES = 2
DEFAULT_SERVICE_TIMEOUT_SECONDS = 900.0
DEFAULT_CONFIG_PATH = "~/.config/promptbranch/config.json"
LEGACY_CONFIG_PATH = "~/.config/chatgpt-cli/config.json"
CLI_VERSION = "0.0.130"
COMMANDS = {
    "login-check",
    "ask",
    "shell",
    "ws",
    "task",
    "src",
    "artifact",
    "test",
    "doctor",
    "debug",
    "project-create",
    "project-list",
    "project-resolve",
    "project-ensure",
    "project-remove",
    "project-source-add",
    "project-source-list",
    "project-source-remove",
    "chat-list",
    "chats",
    "chat-use",
    "use-chat",
    "chat-leave",
    "cq",
    "chat-show",
    "show",
    "chat-summarize",
    "summarize",
    "state",
    "prompt",
    "state-clear",
    "use",
    "completion",
    "version",
    "test-suite",
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
    "--config": True,
    "--service-base-url": True,
    "--service-token": True,
    "--service-timeout-seconds": True,
}


def _split_ask_response(response: Any) -> tuple[Any, Optional[str]]:
    if isinstance(response, dict) and "answer" in response:
        conversation_url = response.get("conversation_url")
        return response["answer"], conversation_url if isinstance(conversation_url, str) else None
    return response, None


class DirectBackend:
    def __init__(
        self,
        service: ChatGPTAutomationService,
        *,
        conversation_state: Optional[ConversationStateStore] = None,
        project_url: Optional[str] = None,
    ) -> None:
        self._service = service
        self._conversation_state = conversation_state
        self._project_url = project_url or service.settings.project_url

    async def login_check(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._service.run_login_check(keep_open=keep_open)

    def _effective_project_home_url(self) -> Optional[str]:
        if self._conversation_state is None:
            return self._project_url
        return self._conversation_state.project_url_for_operations(self._project_url)

    async def list_projects(self, *, keep_open: bool = False) -> dict[str, Any]:
        original_project_url = self._service.settings.project_url
        effective_project_url = self._effective_project_home_url()
        try:
            self._service.settings.project_url = effective_project_url or original_project_url
            return await self._service.list_projects(keep_open=keep_open)
        finally:
            self._service.settings.project_url = original_project_url

    async def list_project_chats(
        self,
        *,
        keep_open: bool = False,
        include_history_fallback: bool = True,
    ) -> dict[str, Any]:
        original_project_url = self._service.settings.project_url
        effective_project_url = self._effective_project_home_url()
        try:
            self._service.settings.project_url = effective_project_url or original_project_url
            return await self._service.list_project_chats(
                keep_open=keep_open,
                include_history_fallback=include_history_fallback,
            )
        finally:
            self._service.settings.project_url = original_project_url

    async def debug_project_chats(
        self,
        *,
        keep_open: bool = False,
        scroll_rounds: int = 20,
        wait_ms: int = 600,
        include_history: bool = True,
        history_max_pages: int = 5,
        history_max_detail_probes: int = 80,
        manual_pause: bool = False,
    ) -> dict[str, Any]:
        original_project_url = self._service.settings.project_url
        effective_project_url = self._effective_project_home_url()
        try:
            self._service.settings.project_url = effective_project_url or original_project_url
            return await self._service.debug_project_chats(
                keep_open=keep_open,
                scroll_rounds=scroll_rounds,
                wait_ms=wait_ms,
                include_history=include_history,
                history_max_pages=history_max_pages,
                history_max_detail_probes=history_max_detail_probes,
                manual_pause=manual_pause,
            )
        finally:
            self._service.settings.project_url = original_project_url

    async def list_project_sources(self, *, keep_open: bool = False) -> dict[str, Any]:
        original_project_url = self._service.settings.project_url
        effective_project_url = self._effective_project_home_url()
        try:
            self._service.settings.project_url = effective_project_url or original_project_url
            return await self._service.list_project_sources(keep_open=keep_open)
        finally:
            self._service.settings.project_url = original_project_url

    async def get_chat(self, conversation_url: str, *, keep_open: bool = False) -> dict[str, Any]:
        original_project_url = self._service.settings.project_url
        effective_project_url = project_home_url_from_url(conversation_url) or self._effective_project_home_url()
        try:
            self._service.settings.project_url = effective_project_url or original_project_url
            return await self._service.get_chat(conversation_url=conversation_url, keep_open=keep_open)
        finally:
            self._service.settings.project_url = original_project_url

    async def create_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        result = await self._service.create_project(
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
        )
        if self._conversation_state is not None:
            self._conversation_state.remember_project(result.get("project_url"), project_name=name)
        return result

    async def resolve_project(self, name: str, *, keep_open: bool = False) -> dict[str, Any]:
        result = await self._service.resolve_project(name=name, keep_open=keep_open)
        if self._conversation_state is not None and result.get("ok"):
            self._conversation_state.remember_project(result.get("project_url"), project_name=name)
        return result

    async def ensure_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        result = await self._service.ensure_project(
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
        )
        if self._conversation_state is not None and result.get("ok"):
            self._conversation_state.remember_project(result.get("project_url"), project_name=name)
        return result

    async def remove_project(self, *, keep_open: bool = False) -> dict[str, Any]:
        effective_project_url = self._effective_project_home_url()
        original_project_url = self._service.settings.project_url
        try:
            self._service.settings.project_url = effective_project_url or original_project_url
            result = await self._service.remove_project(keep_open=keep_open)
        finally:
            self._service.settings.project_url = original_project_url
        if self._conversation_state is not None:
            self._conversation_state.forget_project(effective_project_url)
        return result

    async def add_project_source(
        self,
        *,
        source_kind: str,
        value: Optional[str] = None,
        file_path: Optional[str] = None,
        display_name: Optional[str] = None,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        effective_project_url = self._effective_project_home_url()
        original_project_url = self._service.settings.project_url
        try:
            self._service.settings.project_url = effective_project_url or original_project_url
            return await self._service.add_project_source(
                source_kind=source_kind,
                value=value,
                file_path=file_path,
                display_name=display_name,
                keep_open=keep_open,
            )
        finally:
            self._service.settings.project_url = original_project_url

    async def remove_project_source(
        self,
        source_name: str,
        *,
        exact: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        effective_project_url = self._effective_project_home_url()
        original_project_url = self._service.settings.project_url
        try:
            self._service.settings.project_url = effective_project_url or original_project_url
            return await self._service.remove_project_source(
                source_name=source_name,
                exact=exact,
                keep_open=keep_open,
            )
        finally:
            self._service.settings.project_url = original_project_url

    async def ask(
        self,
        prompt: str,
        *,
        file_path: Optional[str] = None,
        conversation_url: Optional[str] = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
    ) -> Any:
        effective_project_url = conversation_url or (
            self._conversation_state.resolve(self._project_url)
            if self._conversation_state is not None
            else self._project_url
        )
        original_project_url = self._service.settings.project_url
        try:
            self._service.settings.project_url = effective_project_url or original_project_url
            result = await self._service.ask_question_result(
                prompt=prompt,
                file_path=file_path,
                conversation_url=conversation_url,
                expect_json=expect_json,
                keep_open=keep_open,
                retries=retries,
            )
        finally:
            self._service.settings.project_url = original_project_url

        _, conversation_url = _split_ask_response(result)
        if self._conversation_state is not None:
            self._conversation_state.remember(self._project_url, conversation_url)
        return result

    def state_snapshot(self) -> dict[str, Any]:
        if self._conversation_state is None:
            return {}
        return self._conversation_state.snapshot(self._project_url)

    def clear_state(self) -> None:
        if self._conversation_state is not None:
            self._conversation_state.clear()

    def clear_conversation(self) -> None:
        if self._conversation_state is not None:
            self._conversation_state.forget_conversation(self._project_url)


class ServiceBackend:
    def __init__(
        self,
        *,
        base_url: str,
        token: Optional[str],
        timeout: float,
        project_url: Optional[str],
        conversation_state: ConversationStateStore,
    ) -> None:
        self._client = ChatGPTServiceClient(base_url, token=token, timeout=timeout)
        self._project_url = project_url
        self._conversation_state = conversation_state

    def _effective_project_home_url(self) -> Optional[str]:
        return self._conversation_state.project_url_for_operations(self._project_url)

    async def _call(self, fn, /, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def login_check(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._call(self._client.login_check, keep_open=keep_open)

    async def list_projects(self, *, keep_open: bool = False) -> dict[str, Any]:
        result = await self._call(
            self._client.list_projects,
            keep_open=keep_open,
            project_url=self._effective_project_home_url(),
        )
        return result

    async def list_project_chats(
        self,
        *,
        keep_open: bool = False,
        include_history_fallback: bool = True,
    ) -> dict[str, Any]:
        return await self._call(
            self._client.list_project_chats,
            keep_open=keep_open,
            project_url=self._effective_project_home_url(),
            include_history_fallback=include_history_fallback,
        )

    async def debug_project_chats(
        self,
        *,
        keep_open: bool = False,
        scroll_rounds: int = 20,
        wait_ms: int = 600,
        include_history: bool = True,
        history_max_pages: int = 5,
        history_max_detail_probes: int = 80,
        manual_pause: bool = False,
    ) -> dict[str, Any]:
        return await self._call(
            self._client.debug_project_chats,
            keep_open=keep_open,
            project_url=self._effective_project_home_url(),
            scroll_rounds=scroll_rounds,
            wait_ms=wait_ms,
            include_history=include_history,
            history_max_pages=history_max_pages,
            history_max_detail_probes=history_max_detail_probes,
            manual_pause=manual_pause,
        )

    async def list_project_sources(self, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._call(
            self._client.list_project_sources,
            keep_open=keep_open,
            project_url=self._effective_project_home_url(),
        )

    async def get_chat(self, conversation_url: str, *, keep_open: bool = False) -> dict[str, Any]:
        return await self._call(
            self._client.get_chat,
            conversation_url,
            keep_open=keep_open,
            project_url=project_home_url_from_url(conversation_url) or self._effective_project_home_url(),
        )


    async def create_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        result = await self._call(
            self._client.create_project,
            name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
            project_url=self._project_url,
        )
        self._conversation_state.remember_project(result.get("project_url"), project_name=name)
        return result

    async def resolve_project(self, name: str, *, keep_open: bool = False) -> dict[str, Any]:
        result = await self._call(
            self._client.resolve_project,
            name,
            keep_open=keep_open,
            project_url=self._project_url,
        )
        if result.get("ok"):
            self._conversation_state.remember_project(result.get("project_url"), project_name=name)
        return result

    async def ensure_project(
        self,
        name: str,
        *,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        result = await self._call(
            self._client.ensure_project,
            name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
            project_url=self._project_url,
        )
        if result.get("ok"):
            self._conversation_state.remember_project(result.get("project_url"), project_name=name)
        return result

    async def remove_project(self, *, keep_open: bool = False) -> dict[str, Any]:
        effective_project_url = self._effective_project_home_url()
        result = await self._call(
            self._client.remove_project,
            keep_open=keep_open,
            project_url=effective_project_url,
        )
        self._conversation_state.forget_project(effective_project_url)
        return result

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
            project_url=self._effective_project_home_url(),
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
            project_url=self._effective_project_home_url(),
        )

    async def ask(
        self,
        prompt: str,
        *,
        file_path: Optional[str] = None,
        conversation_url: Optional[str] = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
    ) -> Any:
        effective_project_url = conversation_url or self._conversation_state.resolve(self._project_url)
        result = await self._call(
            self._client.ask_result,
            prompt,
            file_path=file_path,
            conversation_url=conversation_url,
            expect_json=expect_json,
            keep_open=keep_open,
            retries=retries,
            project_url=effective_project_url,
        )
        _, conversation_url = _split_ask_response(result)
        self._conversation_state.remember(self._project_url, conversation_url)
        return result

    def state_snapshot(self) -> dict[str, Any]:
        return self._conversation_state.snapshot(self._project_url)

    def clear_state(self) -> None:
        self._conversation_state.clear()

    def clear_conversation(self) -> None:
        self._conversation_state.forget_conversation(self._project_url)


def _env_or(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return None


def _load_cli_config(path: Optional[str]) -> dict[str, Any]:
    if not path:
        return {}
    primary = Path(path).expanduser()
    candidates = [primary]
    if primary == Path(DEFAULT_CONFIG_PATH).expanduser():
        candidates.append(Path(LEGACY_CONFIG_PATH).expanduser())
    for config_path in candidates:
        if not config_path.exists():
            continue
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _option_was_provided(argv: list[str], option_name: str) -> bool:
    return any(token == option_name or token.startswith(f"{option_name}=") for token in argv)


def _apply_cli_config_defaults(args: argparse.Namespace, argv: list[str]) -> argparse.Namespace:
    config = _load_cli_config(args.config)
    mapping: dict[str, str] = {
        "service_base_url": "service_base_url",
        "service_token": "service_token",
        "service_timeout_seconds": "service_timeout_seconds",
    }
    for arg_name, config_key in mapping.items():
        option_name = f"--{arg_name.replace("_", "-")}"
        if _option_was_provided(argv, option_name):
            continue
        current_value = getattr(args, arg_name)
        if current_value is not None:
            continue
        if config_key in config:
            setattr(args, arg_name, config[config_key])
    if args.service_timeout_seconds is None:
        args.service_timeout_seconds = DEFAULT_SERVICE_TIMEOUT_SECONDS
    else:
        args.service_timeout_seconds = float(args.service_timeout_seconds)
    return args


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
    resolved_profile_dir = str(resolve_profile_dir(getattr(args, "profile_dir", None)))
    args.profile_dir = resolved_profile_dir
    settings = ChatGPTAutomationSettings(
        project_url=args.project_url,
        email=args.email,
        password=args.password,
        profile_dir=resolved_profile_dir,
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
    resolved_profile_dir = str(resolve_profile_dir(getattr(args, "profile_dir", None)))
    args.profile_dir = resolved_profile_dir
    conversation_state = ConversationStateStore(resolved_profile_dir)
    if args.service_base_url:
        return ServiceBackend(
            base_url=args.service_base_url,
            token=args.service_token,
            timeout=args.service_timeout_seconds,
            project_url=args.project_url,
            conversation_state=conversation_state,
        )
    return DirectBackend(
        build_service(args),
        conversation_state=conversation_state,
        project_url=args.project_url,
    )


async def cmd_login_check(backend: CommandBackend, args: argparse.Namespace) -> int:
    result = await backend.login_check(keep_open=args.keep_open)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _project_list_payload(result: Any, *, current_only: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = dict(result) if isinstance(result, dict) else {"ok": False, "projects": []}
    raw_projects = payload.get("projects") if isinstance(payload.get("projects"), list) else []
    projects = [item for item in raw_projects if isinstance(item, dict)]
    if current_only:
        projects = [item for item in projects if item.get("is_current")]
    payload["projects"] = projects
    payload["count"] = len(projects)
    if current_only:
        payload["current_only"] = True
    return projects, payload


def _project_source_list_payload(result: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = dict(result) if isinstance(result, dict) else {"ok": False, "sources": []}
    raw_sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    sources = [item for item in raw_sources if isinstance(item, dict)]
    payload["sources"] = sources
    payload["count"] = len(sources)
    return sources, payload


def _project_cache_from_args(args: argparse.Namespace) -> GlobalProjectCache:
    return GlobalProjectCache()


def _cache_project_list_result(args: argparse.Namespace, result: Any) -> dict[str, Any] | None:
    raw_projects = result.get("projects") if isinstance(result, dict) and isinstance(result.get("projects"), list) else None
    if not raw_projects:
        return None
    cache = _project_cache_from_args(args)
    return cache.store_projects([item for item in raw_projects if isinstance(item, dict)])


def _resolve_project_from_cache(args: argparse.Namespace, target: str) -> dict[str, Any] | None:
    cache = _project_cache_from_args(args)
    cached = cache.resolve(target)
    if not isinstance(cached, dict):
        return None
    project_url = str(cached.get("project_home_url") or cached.get("url") or "")
    if not project_url:
        return None
    return {
        "ok": True,
        "action": "project_resolve",
        "resolved_via": "global_cache",
        "project_url": project_url,
        "project_name": cached.get("name") or project_name_from_url(project_url),
        "project_slug": cached.get("project_slug"),
        "cache_file": str(cache.path),
    }


async def cmd_project_list(backend: CommandBackend, args: argparse.Namespace) -> int:
    result = await backend.list_projects(keep_open=args.keep_open)
    cache_payload = _cache_project_list_result(args, result)
    projects, payload = _project_list_payload(result, current_only=args.current)
    if cache_payload is not None:
        payload["cache_file"] = cache_payload.get("cache_file", str(_project_cache_from_args(args).path)) if isinstance(cache_payload, dict) else str(_project_cache_from_args(args).path)
        payload["cache_updated_at"] = cache_payload.get("updated_at") if isinstance(cache_payload, dict) else None
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if not projects:
        print("(no current project found)" if args.current else "(no projects found)")
        return 0
    for item in projects:
        marker = "*" if item.get("is_current") else " "
        name = str(item.get("name") or "<unnamed>")
        url = str(item.get("url") or "")
        print(f"{marker} {name}	{url}")
    return 0


def _choose_project_from_list(projects: list[dict[str, Any]], *, filter_text: Optional[str] = None) -> dict[str, Any]:
    filtered = projects
    if filter_text:
        needle = filter_text.strip().lower()
        filtered = [item for item in projects if needle in str(item.get("name") or "").lower()]
    if not filtered:
        raise ValueError("no projects matched the requested filter")
    if len(filtered) == 1:
        return filtered[0]

    print("Available projects:", file=sys.stderr)
    current_index = None
    for idx, item in enumerate(filtered, start=1):
        is_current = bool(item.get("is_current"))
        if is_current and current_index is None:
            current_index = idx
        marker = "*" if is_current else " "
        name = str(item.get("name") or "<unnamed>")
        url = str(item.get("url") or "")
        print(f"  {idx:>2}. {marker} {name}\t{url}", file=sys.stderr)

    prompt = "Select project number"
    if current_index is not None:
        prompt += f" [{current_index}]"
    prompt += ": "

    while True:
        print(prompt, end="", file=sys.stderr, flush=True)
        selection = input().strip()
        if not selection and current_index is not None:
            return filtered[current_index - 1]
        if selection.isdigit():
            index = int(selection)
            if 1 <= index <= len(filtered):
                return filtered[index - 1]
        exact = [item for item in filtered if str(item.get("name") or "") == selection]
        if len(exact) == 1:
            return exact[0]
        print("Invalid selection. Enter a number from the list or an exact visible project name.", file=sys.stderr)


def _selected_project_home_url(snapshot: dict[str, Any]) -> Optional[str]:
    candidate = snapshot.get('resolved_project_home_url') if isinstance(snapshot, dict) else None
    if isinstance(candidate, str):
        return project_home_url_from_url(candidate)
    return None


def _chat_list_payload(result: Any, *, current_conversation_url: Optional[str] = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = dict(result) if isinstance(result, dict) else {"ok": False, "chats": []}
    raw_chats = payload.get("chats") if isinstance(payload.get("chats"), list) else []
    chats = [item for item in raw_chats if isinstance(item, dict)]
    current_id = conversation_id_from_url(current_conversation_url)
    normalized: list[dict[str, Any]] = []
    for item in chats:
        chat = dict(item)
        conversation_url = str(chat.get('conversation_url') or '')
        chat_id = str(chat.get('id') or conversation_id_from_url(conversation_url) or '')
        chat['id'] = chat_id
        chat['conversation_url'] = conversation_url
        chat['title'] = str(chat.get('title') or '(untitled)')
        chat['is_current'] = bool(current_id and chat_id == current_id)
        normalized.append(chat)
    if current_id and not any(str(item.get('id') or '') == current_id for item in normalized):
        normalized.append({
            'id': current_id,
            'title': '(current task)',
            'conversation_url': current_conversation_url,
            'is_current': True,
            'source': 'current_state',
        })
    payload['chats'] = normalized
    payload['count'] = len(normalized)
    payload['current_conversation_url'] = current_conversation_url
    source_counts = dict(payload.get('source_counts') or {}) if isinstance(payload.get('source_counts'), dict) else {}
    visibility_status, indexed_count, recent_count, indexed_observation_count = _task_list_visibility_status(source_counts, normalized)
    payload['source_counts'] = source_counts
    payload['visibility_status'] = payload.get('visibility_status') or visibility_status
    payload['indexed_task_count'] = indexed_count
    payload['indexed_observation_count'] = payload.get('indexed_observation_count', indexed_observation_count)
    payload['recent_state_count'] = payload.get('recent_state_count', recent_count)
    return normalized, payload



_INDEXED_TASK_SOURCES = {"snorlax", "project_endpoint", "dom", "history", "history_detail", "current_page"}
_LOCAL_TASK_SOURCES = {"recent_state", "current_state"}


def _indexed_observation_count(source_counts: dict[str, Any]) -> int:
    total = 0
    for source in _INDEXED_TASK_SOURCES:
        try:
            total += int(source_counts.get(source) or 0)
        except (TypeError, ValueError):
            continue
    return total


def _unique_indexed_task_count(chats: list[dict[str, Any]]) -> int:
    """Count unique task entries backed by indexed/backend observations.

    `source_counts` counts observations per source. When the same task appears
    in both snorlax and DOM, summing those source counts overstates the number
    of indexed tasks. The public `indexed_task_count` diagnostic is therefore
    derived from the merged task list, excluding local-only fallback rows.
    """
    indexed_ids: set[str] = set()
    anonymous_indexed_rows = 0
    for item in chats:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "").strip()
        if source in _LOCAL_TASK_SOURCES:
            continue
        if source and source not in _INDEXED_TASK_SOURCES:
            continue
        task_id = str(item.get("id") or conversation_id_from_url(item.get("conversation_url")) or "").strip()
        if task_id:
            indexed_ids.add(task_id)
        else:
            anonymous_indexed_rows += 1
    return len(indexed_ids) + anonymous_indexed_rows


def _task_list_visibility_status(source_counts: dict[str, Any], chats: list[dict[str, Any]]) -> tuple[str, int, int, int]:
    indexed_count = _unique_indexed_task_count(chats)
    indexed_observations = _indexed_observation_count(source_counts)
    recent_count = 0
    try:
        recent_count = int(source_counts.get("recent_state") or 0)
    except (TypeError, ValueError):
        recent_count = 0
    if indexed_count > 0:
        return "indexed", indexed_count, recent_count, indexed_observations
    if recent_count > 0 or any(str(item.get("source") or "") == "recent_state" for item in chats):
        return "recent_state_only", indexed_count, recent_count, indexed_observations
    return "missing", indexed_count, recent_count, indexed_observations

def _normalize_chat_title(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '')).strip().casefold()


def _looks_like_conversation_id(value: str) -> bool:
    return bool(re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(value or '').strip(), re.IGNORECASE))


def _select_chat_from_list(chats: list[dict[str, Any]], target: str) -> dict[str, Any]:
    if not chats:
        raise ValueError('no chats were found for the current project')

    if str(target).isdigit():
        index = int(str(target))
        if 1 <= index <= len(chats):
            return chats[index - 1]
        raise ValueError(f'chat index out of range: {target}')

    exact_id = [item for item in chats if str(item.get('id') or '') == target]
    if len(exact_id) == 1:
        return exact_id[0]

    prefix_id = [item for item in chats if str(item.get('id') or '').startswith(str(target))]
    if len(prefix_id) == 1:
        return prefix_id[0]
    if len(prefix_id) > 1:
        raise ValueError(f'multiple chats matched id prefix: {target}')

    normalized_target = _normalize_chat_title(str(target))
    exact_title = [item for item in chats if _normalize_chat_title(str(item.get('title') or '')) == normalized_target]
    if len(exact_title) == 1:
        return exact_title[0]
    if len(exact_title) > 1:
        raise ValueError(f'multiple chats matched exact title: {target}')

    contains_title = [item for item in chats if normalized_target in _normalize_chat_title(str(item.get('title') or ''))]
    if len(contains_title) == 1:
        return contains_title[0]
    if len(contains_title) > 1:
        raise ValueError(f'multiple chats matched title fragment: {target}')

    raise ValueError(f'chat not found: {target}')


async def _resolve_chat_target(
    backend: Any,
    args: argparse.Namespace,
    target: Optional[str],
    *,
    keep_open: bool = False,
) -> dict[str, Any]:
    snapshot = backend.state_snapshot()
    current_conversation_url = snapshot.get('conversation_url') if isinstance(snapshot, dict) else None
    if not target:
        if isinstance(current_conversation_url, str) and current_conversation_url:
            return {
                'title': snapshot.get('conversation_id') or '(current chat)',
                'conversation_url': current_conversation_url,
                'id': conversation_id_from_url(current_conversation_url),
                'is_current': True,
            }
        raise ValueError('no current task is selected; run "pb task list" then "pb task use <task>", or pass "--task <task>"')

    if _looks_like_chatgpt_url(target) and conversation_id_from_url(target):
        return {
            'title': target,
            'conversation_url': target,
            'id': conversation_id_from_url(target),
            'is_current': bool(current_conversation_url and target == current_conversation_url),
        }

    if _looks_like_conversation_id(str(target)):
        project_home_url = _selected_project_home_url(snapshot) if isinstance(snapshot, dict) else None
        if project_home_url:
            conversation_url = (project_home_url[:-len('/project')] if project_home_url.endswith('/project') else project_home_url.rstrip('/')) + f'/c/{target}'
            return {
                'title': target,
                'conversation_url': conversation_url,
                'id': str(target),
                'is_current': bool(current_conversation_url and conversation_id_from_url(current_conversation_url) == str(target)),
            }

    async def load_chats(*, include_history_fallback: bool) -> list[dict[str, Any]]:
        result = await backend.list_project_chats(
            keep_open=keep_open,
            include_history_fallback=include_history_fallback,
        )
        chats, _ = _chat_list_payload(
            result,
            current_conversation_url=current_conversation_url if isinstance(current_conversation_url, str) else None,
        )
        return chats

    # Most `pb task use <n>` calls refer to an entry already present in the
    # indexed snorlax/DOM list. Resolve against that lightweight list first so
    # selection does not repeat the expensive global conversation-history scan.
    lightweight_chats = await load_chats(include_history_fallback=False)
    try:
        return _select_chat_from_list(lightweight_chats, str(target))
    except ValueError as light_error:
        if str(target).isdigit():
            # Numeric indexes beyond the lightweight list may require the deep
            # task list. Fall through to full enumeration only for that case.
            pass
        elif lightweight_chats and (
            str(light_error).startswith('multiple chats matched')
            or str(light_error).startswith('chat not found')
        ):
            pass
        elif lightweight_chats:
            raise

    full_chats = await load_chats(include_history_fallback=True)
    return _select_chat_from_list(full_chats, str(target))


async def cmd_chat_list(backend: Any, args: argparse.Namespace) -> int:
    snapshot = backend.state_snapshot()
    project_home_url = _selected_project_home_url(snapshot)
    if not project_home_url:
        print('error: no current project is selected', file=sys.stderr)
        return 2
    result = await backend.list_project_chats(keep_open=args.keep_open)
    chats, payload = _chat_list_payload(result, current_conversation_url=snapshot.get('conversation_url'))
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if not chats:
        print('(no chats found)')
        return 0
    for idx, item in enumerate(chats, start=1):
        marker = '*' if item.get('is_current') else ' '
        print(f"{idx:>3}. {marker} {item.get('title') or '(untitled)'}\t{item.get('id') or ''}\t{item.get('conversation_url') or ''}")
    source_counts = payload.get('source_counts') if isinstance(payload.get('source_counts'), dict) else {}
    if source_counts:
        source_summary = ', '.join(f"{name}={source_counts.get(name) or 0}" for name in ('snorlax', 'project_endpoint', 'dom', 'history', 'history_detail', 'current_page', 'recent_state') if name in source_counts)
        visibility = payload.get('visibility_status') or 'unknown'
        print(f"# count={payload.get('count', len(chats))} visibility={visibility} sources: {source_summary}")
        if payload.get('history_supplement_used'):
            print('# history_supplement_used=true')
    return 0


async def cmd_chat_use(backend: Any, args: argparse.Namespace) -> int:
    store = _state_store_from_args(args)
    try:
        selected = await _resolve_chat_target(backend, args, args.target, keep_open=args.keep_open)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    conversation_url = str(selected.get('conversation_url') or '')
    project_home_url = project_home_url_from_url(conversation_url)
    if not project_home_url:
        print('error: could not determine project for the selected chat', file=sys.stderr)
        return 2
    store.remember(project_home_url, conversation_url)
    snapshot = store.snapshot(project_home_url)
    payload = {
        'ok': True,
        'action': 'chat_use',
        'project_home_url': snapshot.get('resolved_project_home_url'),
        'conversation_url': snapshot.get('conversation_url'),
        'conversation_id': snapshot.get('conversation_id'),
        'chat_title': selected.get('title'),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


async def cmd_chat_leave(backend: Any, args: argparse.Namespace) -> int:
    snapshot_before = backend.state_snapshot()
    backend.clear_conversation()
    snapshot_after = backend.state_snapshot()
    payload = {
        'ok': True,
        'action': 'chat_leave',
        'project_home_url': snapshot_after.get('resolved_project_home_url') or snapshot_before.get('resolved_project_home_url'),
        'conversation_url': snapshot_after.get('conversation_url'),
        'conversation_id': snapshot_after.get('conversation_id'),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _render_chat_payload(payload: dict[str, Any]) -> str:
    lines = [
        f"title={payload.get('title') or '(untitled)'}",
        f"conversation_id={payload.get('conversation_id') or 'none'}",
        f"conversation_url={payload.get('conversation_url') or 'none'}",
        f"turn_count={payload.get('turn_count') or 0}",
        '',
    ]
    turns = payload.get('turns') if isinstance(payload.get('turns'), list) else []
    for turn in turns:
        role = str(turn.get('role') or 'unknown')
        index = turn.get('index')
        lines.append(f"[{index}] {role}")
        lines.append(str(turn.get('text') or ''))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def _one_line_preview(value: Any, *, max_chars: int = 96) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _message_text_from_any_payload(raw: dict[str, Any]) -> str:
    """Extract text from either normalized turns or raw ChatGPT message payloads."""
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
    """Best-effort fallback for raw conversation payloads returned by live backends."""
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
    """Group a transcript into user messages with zero or more answers."""
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


def _resolve_task_message(messages: list[dict[str, Any]], id_or_index: str) -> dict[str, Any]:
    target = str(id_or_index).strip()
    if not target:
        raise ValueError("message id or index is required")

    if target.lower() in {"last", "latest"}:
        if messages:
            return messages[-1]
        raise ValueError("message index out of range: last")

    if target.isdigit():
        index = int(target)
        if 1 <= index <= len(messages):
            return messages[index - 1]
        raise ValueError(f"message index out of range: {target}")

    exact = [item for item in messages if str(item.get("id") or "") == target]
    if len(exact) == 1:
        return exact[0]

    prefix = [item for item in messages if str(item.get("id") or "").startswith(target)]
    if len(prefix) == 1:
        return prefix[0]
    if len(prefix) > 1:
        raise ValueError(f"multiple messages matched id prefix: {target}")

    raise ValueError(f"message not found: {target}")


def _render_task_messages_list(payload: dict[str, Any]) -> str:
    lines = [
        f"title={payload.get('title') or '(untitled)'}",
        f"conversation_id={payload.get('conversation_id') or 'none'}",
        f"message_count={payload.get('message_count') or 0}",
        "",
    ]
    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    for item in messages:
        lines.append(
            f"{item.get('index'):>3}. answers={item.get('answer_count') or 0}\t"
            f"{item.get('id') or ''}\t{item.get('preview') or ''}"
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_task_message_show(message: dict[str, Any]) -> str:
    lines = [
        f"message_index={message.get('index')}",
        f"message_id={message.get('id') or 'none'}",
        f"answer_count={message.get('answer_count') or 0}",
        "",
        str(message.get("text") or ""),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _render_task_message_answers(message: dict[str, Any]) -> str:
    answers = message.get("answers") if isinstance(message.get("answers"), list) else []
    if not answers:
        return "(no answer)\n"
    lines: list[str] = []
    for answer in answers:
        if len(answers) > 1:
            lines.append(f"[answer {answer.get('index')}]")
        lines.append(str(answer.get("text") or ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


async def cmd_chat_show(backend: Any, args: argparse.Namespace) -> int:
    try:
        selected = await _resolve_chat_target(backend, args, args.target, keep_open=args.keep_open)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    result = await backend.get_chat(str(selected.get('conversation_url') or ''), keep_open=args.keep_open)
    store = _state_store_from_args(args)
    store.remember(project_home_url_from_url(str(selected.get('conversation_url') or '')), str(selected.get('conversation_url') or ''), project_name=None)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    print(_render_chat_payload(result), end='')
    return 0


async def _fetch_task_messages_payload(
    backend: Any,
    args: argparse.Namespace,
    target: Optional[str] = None,
) -> dict[str, Any]:
    selected = await _resolve_chat_target(backend, args, target, keep_open=getattr(args, "keep_open", False))
    conversation_url = str(selected.get("conversation_url") or "")
    result = await backend.get_chat(conversation_url, keep_open=getattr(args, "keep_open", False))
    store = _state_store_from_args(args)
    store.remember(project_home_url_from_url(conversation_url), conversation_url, project_name=None)
    return _task_messages_payload(result)


async def cmd_task_messages_list(backend: Any, args: argparse.Namespace) -> int:
    try:
        payload = await _fetch_task_messages_payload(backend, args, getattr(args, "target", None))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(_render_task_messages_list(payload), end="")
    return 0


async def cmd_task_message_show(backend: Any, args: argparse.Namespace) -> int:
    try:
        payload = await _fetch_task_messages_payload(backend, args, getattr(args, "target", None))
        message = _resolve_task_message(payload["messages"], args.id_or_index)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    result = {**payload, "action": "task_message_show", "message": message}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    print(_render_task_message_show(message), end="")
    return 0


async def cmd_task_message_answer(backend: Any, args: argparse.Namespace) -> int:
    try:
        payload = await _fetch_task_messages_payload(backend, args, getattr(args, "target", None))
        message = _resolve_task_message(payload["messages"], args.id_or_index)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    answers = message.get("answers") if isinstance(message.get("answers"), list) else []
    result = {
        **payload,
        "action": "task_message_answer",
        "message": {key: value for key, value in message.items() if key != "answers"},
        "answer_count": len(answers),
        "answers": answers,
    }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    print(_render_task_message_answers(message), end="")
    return 0


async def cmd_chat_summarize(backend: Any, args: argparse.Namespace) -> int:
    try:
        selected = await _resolve_chat_target(backend, args, args.target, keep_open=args.keep_open)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    summary_prompt = (
        'Summarize this chat so far as JSON with keys topic, key_points, decisions, unresolved_questions, next_steps.'
        if args.json
        else 'Summarize this chat so far. Include the main topic, key points, decisions, unresolved questions, and next steps. Keep it concise.'
    )
    response = await backend.ask(
        prompt=summary_prompt,
        conversation_url=str(selected.get('conversation_url') or ''),
        expect_json=args.json,
        keep_open=args.keep_open,
        retries=args.retries,
    )
    answer, conversation_url = _split_ask_response(response)
    payload = {
        'ok': True,
        'action': 'chat_summarize',
        'conversation_url': conversation_url or selected.get('conversation_url'),
        'conversation_id': conversation_id_from_url(conversation_url or str(selected.get('conversation_url') or '')),
        'chat_title': selected.get('title'),
        'answer': answer,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if isinstance(answer, (dict, list)):
        print(json.dumps(answer, indent=2, ensure_ascii=False))
    else:
        print(answer)
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
    if not result.get("ok"):
        cached = _resolve_project_from_cache(args, args.name)
        if cached is not None:
            _state_store_from_args(args).remember_project(cached.get("project_url"), project_name=cached.get("project_name"))
            result = cached
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


async def cmd_project_source_list(backend: Any, args: argparse.Namespace) -> int:
    result = await backend.list_project_sources(keep_open=args.keep_open)
    sources, payload = _project_source_list_payload(result)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if not sources:
        print('(no project sources found)')
        return 0
    for idx, item in enumerate(sources, start=1):
        title = str(item.get('title') or item.get('name') or item.get('identity') or '(untitled)')
        subtitle = str(item.get('subtitle') or '')
        identity = str(item.get('identity') or '')
        columns = [f"{idx:>3}. {title}"]
        if subtitle:
            columns.append(subtitle)
        if identity and identity != title and identity != subtitle:
            columns.append(identity)
        print("	".join(columns))
    return 0


async def cmd_project_source_add(backend: CommandBackend, args: argparse.Namespace) -> int:
    source_kind = args.type or "file"
    value = args.value
    file_path = args.file
    display_name = args.name
    if source_kind == "file" and not file_path:
        print("error: --file is required when --type=file", file=sys.stderr)
        return 2
    if source_kind in {"link", "text"} and not value:
        print(f"error: --value is required when --type={source_kind}", file=sys.stderr)
        return 2
    if source_kind == "file" and display_name:
        display_name = Path(display_name).name
    elif source_kind == "file" and file_path and not display_name:
        display_name = Path(file_path).name

    result = await backend.add_project_source(
        source_kind=source_kind,
        value=value,
        file_path=file_path,
        display_name=display_name,
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
        conversation_url=args.conversation_url,
        expect_json=args.json,
        keep_open=args.keep_open,
        retries=args.retries,
    )
    if args.json:
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 0

    answer, _ = _split_ask_response(response)
    if isinstance(answer, (dict, list)):
        print(json.dumps(answer, indent=2, ensure_ascii=False))
    else:
        print(answer)
    return 0


def _cli_command_name(argv0: Optional[str] = None) -> str:
    return "promptbranch"


def _completion_function_name(command_name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", command_name)
    return f"_{sanitized}_complete"


def _compact_prompt_text(snapshot: dict[str, Any], *, command_name: str = "promptbranch") -> str:
    project_name = snapshot.get("project_name") or snapshot.get("project_slug") or "no-project"
    conversation_id = snapshot.get("conversation_id")
    if conversation_id:
        return f"{command_name}:{project_name}#{str(conversation_id)[:8]}"
    return f"{command_name}:{project_name}"



def _looks_like_chatgpt_url(value: str) -> bool:
    return value.startswith("https://") or value.startswith("http://")


def _completion_command_names() -> list[str]:
    return sorted(COMMANDS)


def _global_option_names() -> list[str]:
    return sorted(GLOBAL_OPTION_HAS_VALUE.keys())


def _subcommand_option_names() -> dict[str, list[str]]:
    return {
        "login-check": ["--keep-open"],
        "ws": ["list", "use", "current", "leave", "--json", "--current", "--pick", "--conversation-url", "--project-name", "--keep-open"],
        "task": ["list", "use", "current", "leave", "show", "messages", "message", "answer", "--json", "--keep-open", "--task"],
        "src": ["list", "add", "rm", "remove", "sync", "--type", "--value", "--file", "--name", "--exact", "--keep-open", "--json", "--no-upload", "--output-dir", "--filename"],
        "artifact": ["current", "list", "release", "verify", "--json", "--output-dir", "--filename"],
        "test": ["smoke", "--json", "--keep-open", "--keep-project", "--only", "--skip", "--allow-recent-state-task-fallback"],
        "doctor": ["--json"],
        "debug": ["chats", "task-list", "tasks", "--json", "--scroll-rounds", "--wait-ms", "--no-history", "--history-max-pages", "--history-max-detail-probes", "--manual-pause", "--keep-open"],
        "project-create": ["--icon", "--color", "--memory-mode", "--keep-open"],
        "project-list": ["--json", "--current", "--keep-open"],
        "project-resolve": ["--keep-open"],
        "project-ensure": ["--icon", "--color", "--memory-mode", "--keep-open"],
        "project-remove": ["--keep-open"],
        "project-source-add": ["--type", "--value", "--file", "--name", "--keep-open"],
        "project-source-list": ["--json", "--keep-open"],
        "project-source-remove": ["--exact", "--keep-open"],
        "chat-list": ["--json", "--keep-open"],
        "chats": ["--json", "--keep-open"],
        "chat-use": ["--json", "--keep-open"],
        "use-chat": ["--json", "--keep-open"],
        "chat-leave": ["--json"],
        "cq": ["--json"],
        "chat-show": ["--json", "--keep-open"],
        "show": ["--json", "--keep-open"],
        "chat-summarize": ["--json", "--keep-open", "--retries"],
        "summarize": ["--json", "--keep-open", "--retries"],
        "state": ["--json"],
        "prompt": ["--json"],
        "state-clear": [],
        "use": ["--pick", "--conversation-url", "--project-name", "--json", "--keep-open"],
        "completion": [],
        "version": [],
        "ask": ["--file", "--json", "--conversation-url", "--keep-open", "--retries"],
        "shell": ["--file", "--json", "--keep-open", "--retries"],
        "test-suite": ["--json", "--keep-open", "--keep-project", "--only", "--skip", "--allow-recent-state-task-fallback", "--task-list-visible-timeout-seconds", "--task-list-visible-max-attempts"],
    }


def _render_completion_bash(command_name: str) -> str:
    commands = " ".join(_completion_command_names())
    global_opts = " ".join(_global_option_names())
    sub_opts = _subcommand_option_names()
    function_name = _completion_function_name(command_name)
    case_lines: list[str] = []
    for name, options in sub_opts.items():
        opts = " ".join(options)
        case_lines.append(f'        {name}) opts="{opts} $global_opts" ;;')
    case_block = "\n".join(case_lines)
    command_case = "|".join(_completion_command_names())
    return f"""{function_name}() {{
    local cur prev cmd global_opts
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    global_opts="{global_opts}"

    case "$prev" in
        --file|--password-file|--dotenv|--config)
            COMPREPLY=( $(compgen -f -- "$cur") )
            return 0
            ;;
        --type)
            COMPREPLY=( $(compgen -W "link text file" -- "$cur") )
            return 0
            ;;
    esac

    for word in "${{COMP_WORDS[@]:1}}"; do
        case "$word" in
            {command_case})
                cmd="$word"
                break
                ;;
        esac
    done

    if [[ "$cur" == -* ]]; then
        local opts="$global_opts"
        if [[ -n "$cmd" ]]; then
            case "$cmd" in
{case_block}
            esac
        fi
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
        return 0
    fi

    if [[ -z "$cmd" ]]; then
        COMPREPLY=( $(compgen -W "{commands}" -- "$cur") )
        return 0
    fi

    return 0
}}

complete -F {function_name} {command_name}
"""


def _render_completion_zsh(command_name: str) -> str:
    command_specs = " ".join(f'"{name}:{name}"' for name in _completion_command_names())
    sub_lines: list[str] = []
    for name, options in _subcommand_option_names().items():
        opts = " ".join(f'"{opt}[{opt}]"' for opt in options)
        sub_lines.append(f"        {name}) _arguments {opts} ;;")
    sub_block = "\n".join(sub_lines)
    return f"""#compdef {command_name}
local context state line
typeset -A opt_args

_arguments -C \
  "--project-url[project or conversation URL]:url:" \
  "--email[ChatGPT email]:email:" \
  "--password[ChatGPT password]:password:" \
  "--password-file[path to password file]:file:_files" \
  "--profile-dir[path to browser profile]:dir:_files -/" \
  "--headless[run browser headless]" \
  "--use-playwright[use playwright instead of patchright]" \
  "--browser-channel[browser channel]:channel:" \
  "--enable-fedcm[do not disable FedCM]" \
  "--keep-no-sandbox[keep no-sandbox args]" \
  "--max-retries[max retries]:count:" \
  "--retry-backoff-seconds[retry backoff seconds]:seconds:" \
  "--debug[enable debug logging]" \
  "--dotenv[path to .env file]:file:_files" \
  "--config[path to CLI config]:file:_files" \
  "--service-base-url[service base URL]:url:" \
  "--service-token[bearer token]:token:" \
  "--service-timeout-seconds[service timeout seconds]:seconds:" \
  "1:command:(({command_specs}))" \
  '*::arg:->args'

case $state in
  args)
    case $words[1] in
{sub_block}
    esac
  ;;
esac
"""


def _render_completion_fish(command_name: str) -> str:
    needs_arg = {
        "--project-url", "--email", "--password", "--password-file", "--profile-dir", "--browser-channel",
        "--max-retries", "--retry-backoff-seconds", "--dotenv", "--config", "--service-base-url",
        "--service-token", "--service-timeout-seconds", "--type", "--value", "--file", "--name",
        "--conversation-url", "--project-name", "--retries", "--icon", "--color", "--memory-mode",
        "--post-ask-delay-seconds", "--step-delay-seconds", "--task-list-visible-timeout-seconds",
        "--task-list-visible-poll-min-seconds", "--task-list-visible-poll-max-seconds", "--task-list-visible-max-attempts",
    }
    lines = [f"complete -c {command_name} -f"]
    for opt in _global_option_names():
        long_opt = opt[2:]
        flag = " -r" if opt in needs_arg else ""
        lines.append(f"complete -c {command_name} -l {long_opt}{flag}")
    for cmd in _completion_command_names():
        lines.append(f"complete -c {command_name} -n '__fish_use_subcommand' -a '{cmd}'")
    for cmd, options in _subcommand_option_names().items():
        for opt in options:
            long_opt = opt[2:]
            flag = " -r" if opt in needs_arg else ""
            lines.append(f"complete -c {command_name} -n '__fish_seen_subcommand_from {cmd}' -l {long_opt}{flag}")
    lines.append(f"complete -c {command_name} -n '__fish_seen_subcommand_from project-source-add; and __fish_prev_arg_in --type' -a 'link text file'")
    return "\n".join(lines) + "\n"


def _render_completion(shell_name: str, command_name: str) -> str:
    if shell_name == "bash":
        return _render_completion_bash(command_name)
    if shell_name == "zsh":
        return _render_completion_zsh(command_name)
    if shell_name == "fish":
        return _render_completion_fish(command_name)
    raise ValueError(f"unsupported shell: {shell_name}")


def _state_store_from_args(args: argparse.Namespace) -> ConversationStateStore:
    return ConversationStateStore(args.profile_dir)


async def cmd_test_suite(args: argparse.Namespace) -> int:
    payload = {
        'project_url': args.project_url,
        'email': args.email,
        'password': args.password,
        'password_file': args.password_file,
        'profile_dir': args.profile_dir,
        'headless': args.headless,
        'use_playwright': args.use_playwright,
        'browser_channel': args.browser_channel,
        'enable_fedcm': args.enable_fedcm,
        'keep_no_sandbox': args.keep_no_sandbox,
        'max_retries': args.max_retries,
        'retry_backoff_seconds': args.retry_backoff_seconds,
        'debug': args.debug,
        'keep_open': args.keep_open,
        'keep_project': args.keep_project,
        'step_delay_seconds': args.step_delay_seconds,
        'post_ask_delay_seconds': args.post_ask_delay_seconds,
        'task_list_visible_timeout_seconds': args.task_list_visible_timeout_seconds,
        'task_list_visible_poll_min_seconds': args.task_list_visible_poll_min_seconds,
        'task_list_visible_poll_max_seconds': args.task_list_visible_poll_max_seconds,
        'task_list_visible_max_attempts': args.task_list_visible_max_attempts,
        'allow_recent_state_task_fallback': getattr(args, 'allow_recent_state_task_fallback', False),
        'skip': list(args.skip),
        'only': list(args.only),
        'strict_remove_ui': args.strict_remove_ui,
        'project_name': args.project_name,
        'project_name_prefix': args.project_name_prefix,
        'run_id': args.run_id,
        'memory_mode': args.memory_mode,
        'link_url': args.link_url,
        'ask_prompt': args.ask_prompt,
        'json_out': args.json_out,
        'project_list_debug_scroll_rounds': args.project_list_debug_scroll_rounds,
        'project_list_debug_wait_ms': args.project_list_debug_wait_ms,
        'project_list_debug_manual_pause': args.project_list_debug_manual_pause,
        'service_base_url': args.service_base_url,
        'service_token': args.service_token,
        'service_timeout_seconds': args.service_timeout_seconds,
        'clear_singleton_locks': args.clear_singleton_locks,
    }
    summary = await run_test_suite_async(**payload)
    if args.json or True:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary.get('ok') else 1


async def cmd_state(backend: CommandBackend, args: argparse.Namespace) -> int:
    snapshot = backend.state_snapshot()
    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0
    print(f"state_file={snapshot.get('state_file')}")
    print(f"project={snapshot.get('project_name') or snapshot.get('project_slug') or 'none'}")
    print(f"project_home_url={snapshot.get('resolved_project_home_url') or 'none'}")
    print(f"conversation_url={snapshot.get('conversation_url') or 'none'}")
    print(f"conversation_id={snapshot.get('conversation_id') or 'none'}")
    return 0


async def cmd_prompt(backend: CommandBackend, args: argparse.Namespace) -> int:
    snapshot = backend.state_snapshot()
    if args.json:
        print(json.dumps({"prompt": _compact_prompt_text(snapshot, command_name=_cli_command_name()), "state": snapshot}, indent=2, ensure_ascii=False))
        return 0
    print(_compact_prompt_text(snapshot, command_name=_cli_command_name()))
    return 0


async def cmd_state_clear(backend: CommandBackend, args: argparse.Namespace) -> int:
    backend.clear_state()
    print(json.dumps({"ok": True, "cleared": True}, indent=2, ensure_ascii=False))
    return 0



async def cmd_use(backend: CommandBackend, args: argparse.Namespace) -> int:
    store = _state_store_from_args(args)
    project_name = args.project_name
    target = args.target
    conversation_url = args.conversation_url

    if args.pick:
        result = await backend.list_projects(keep_open=args.keep_open)
        _cache_project_list_result(args, result)
        projects, _ = _project_list_payload(result, current_only=False)
        selected_via = "pick"
        if not projects:
            cache_snapshot = _project_cache_from_args(args).snapshot()
            cached_projects = cache_snapshot.get("projects") if isinstance(cache_snapshot.get("projects"), list) else []
            projects = [item for item in cached_projects if isinstance(item, dict)]
            selected_via = "global_cache"
        if not projects:
            print(json.dumps({"ok": False, "action": "use", "error": "no_projects_found"}, indent=2, ensure_ascii=False))
            return 1
        try:
            selected = _choose_project_from_list(projects, filter_text=target)
        except ValueError as exc:
            print(json.dumps({"ok": False, "action": "use", "error": "project_not_found", "detail": str(exc)}, indent=2, ensure_ascii=False))
            return 1
        resolved_url = str(selected.get("url") or "")
        resolved_name = project_name or str(selected.get("name") or target or "")
        store.remember_project(resolved_url, project_name=resolved_name)
        if conversation_url:
            store.remember(resolved_url, conversation_url, project_name=resolved_name)
        snapshot = store.snapshot(resolved_url)
        payload = {
            "ok": True,
            "action": "use",
            "selected_via": selected_via,
            "project_name": snapshot.get("project_name"),
            "project_slug": snapshot.get("project_slug"),
            "project_home_url": snapshot.get("resolved_project_home_url"),
            "conversation_url": snapshot.get("conversation_url"),
        }
        print(json.dumps(payload if args.json else payload, indent=2, ensure_ascii=False))
        return 0

    if not target:
        print("error: target is required unless --pick is used", file=sys.stderr)
        return 2

    if _looks_like_chatgpt_url(target):
        home_url = project_home_url_from_url(target) or target
        if conversation_id_from_url(target):
            conversation_url = target
            home_url = project_home_url_from_url(target) or home_url
        store.remember_project(home_url, project_name=project_name or project_name_from_url(home_url))
        if conversation_url:
            store.remember(home_url, conversation_url, project_name=project_name)
        payload = store.snapshot(home_url)
        if not args.json:
            payload = {
                "ok": True,
                "action": "use",
                "project_home_url": payload.get("resolved_project_home_url"),
                "conversation_url": payload.get("conversation_url"),
                "project_name": payload.get("project_name"),
                "project_slug": payload.get("project_slug"),
            }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    result = await backend.resolve_project(name=target, keep_open=args.keep_open)
    if not result.get("ok"):
        cached = _resolve_project_from_cache(args, target)
        if cached is not None:
            result = cached
    if result.get("ok"):
        resolved_url = result.get("project_url")
        resolved_name = project_name or result.get("project_name") or target
        store.remember_project(resolved_url, project_name=resolved_name)
        if conversation_url:
            store.remember(resolved_url, conversation_url, project_name=resolved_name)
        snapshot = store.snapshot(resolved_url)
        result = {
            **result,
            "action": "use",
            "current_project_home_url": snapshot.get("resolved_project_home_url"),
            "current_conversation_url": snapshot.get("conversation_url"),
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1



async def cmd_ws_current(backend: CommandBackend, args: argparse.Namespace) -> int:
    """Show only the active workspace/project scope."""
    snapshot = backend.state_snapshot()
    payload = {
        "ok": True,
        "action": "ws_current",
        "state_file": snapshot.get("state_file"),
        "project_name": snapshot.get("project_name"),
        "project_slug": snapshot.get("project_slug"),
        "project_home_url": snapshot.get("resolved_project_home_url"),
        "workspace": snapshot.get("workspace") if isinstance(snapshot.get("workspace"), dict) else None,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(f"state_file={payload.get('state_file')}")
    print(f"workspace={payload.get('project_name') or payload.get('project_slug') or 'none'}")
    print(f"project_home_url={payload.get('project_home_url') or 'none'}")
    return 0


async def cmd_task_current(backend: CommandBackend, args: argparse.Namespace) -> int:
    """Show only the active task/chat scope."""
    snapshot = backend.state_snapshot()
    payload = {
        "ok": True,
        "action": "task_current",
        "state_file": snapshot.get("state_file"),
        "project_home_url": snapshot.get("resolved_project_home_url"),
        "conversation_url": snapshot.get("conversation_url"),
        "conversation_id": snapshot.get("conversation_id"),
        "task": snapshot.get("task") if isinstance(snapshot.get("task"), dict) else None,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(f"state_file={payload.get('state_file')}")
    print(f"project_home_url={payload.get('project_home_url') or 'none'}")
    print(f"conversation_url={payload.get('conversation_url') or 'none'}")
    print(f"conversation_id={payload.get('conversation_id') or 'none'}")
    return 0


async def cmd_ws(backend: CommandBackend, args: argparse.Namespace) -> int:
    if args.ws_command == "list":
        return await cmd_project_list(backend, args)
    if args.ws_command == "use":
        return await cmd_use(backend, args)
    if args.ws_command == "current":
        return await cmd_ws_current(backend, args)
    if args.ws_command == "leave":
        return await cmd_state_clear(backend, args)
    raise RuntimeError(f"Unknown ws command: {args.ws_command}")


async def cmd_task(backend: CommandBackend, args: argparse.Namespace) -> int:
    if args.task_command == "list":
        return await cmd_chat_list(backend, args)
    if args.task_command == "use":
        return await cmd_chat_use(backend, args)
    if args.task_command == "current":
        return await cmd_task_current(backend, args)
    if args.task_command == "leave":
        return await cmd_chat_leave(backend, args)
    if args.task_command == "show":
        return await cmd_chat_show(backend, args)
    if args.task_command == "messages":
        if args.task_messages_command == "list":
            return await cmd_task_messages_list(backend, args)
        raise RuntimeError(f"Unknown task messages command: {args.task_messages_command}")
    if args.task_command == "message":
        if args.task_message_command == "show":
            return await cmd_task_message_show(backend, args)
        if args.task_message_command == "answer":
            return await cmd_task_message_answer(backend, args)
        raise RuntimeError(f"Unknown task message command: {args.task_message_command}")
    raise RuntimeError(f"Unknown task command: {args.task_command}")


def _artifact_registry_from_args(args: argparse.Namespace) -> ArtifactRegistry:
    return ArtifactRegistry(resolve_profile_dir(getattr(args, "profile_dir", None)))


def _artifact_output_dir(args: argparse.Namespace, registry: ArtifactRegistry) -> Path:
    output_dir = getattr(args, "output_dir", None)
    return Path(output_dir).expanduser() if output_dir else registry.artifact_dir


def _artifact_state_project_url(backend: Any) -> Optional[str]:
    snapshot = backend.state_snapshot()
    candidate = snapshot.get("resolved_project_home_url") if isinstance(snapshot, dict) else None
    return candidate if isinstance(candidate, str) else None


async def cmd_src_sync(backend: Any, args: argparse.Namespace) -> int:
    """Package a repo snapshot and optionally upload it as a project source."""
    registry = _artifact_registry_from_args(args)
    repo_path = Path(args.path).expanduser().resolve()
    try:
        record, included = create_repo_snapshot(
            repo_path,
            output_dir=_artifact_output_dir(args, registry),
            filename=getattr(args, "filename", None),
            kind="source_snapshot",
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "action": "src_sync", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 2

    project_url = _artifact_state_project_url(backend)
    upload_result: dict[str, Any] | None = None
    uploaded = False
    if not getattr(args, "no_upload", False):
        if not project_url:
            payload = {
                "ok": False,
                "action": "src_sync",
                "status": "no_workspace_selected",
                "artifact": record.to_dict(),
                "included_count": len(included),
                "error": "no current workspace is selected; run `pb ws use <project>` or pass --no-upload",
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 2
        upload_result = await backend.add_project_source(
            source_kind="file",
            file_path=record.path,
            display_name=record.filename,
            keep_open=args.keep_open,
        )
        uploaded = bool(isinstance(upload_result, dict) and upload_result.get("ok"))

    artifact_payload = registry.add(record)
    store = _state_store_from_args(args)
    if project_url:
        if uploaded:
            store.remember_artifact(
                project_url=project_url,
                artifact_ref=record.filename,
                artifact_version=record.version,
                source_ref=record.filename,
                source_version=record.version,
            )
        else:
            store.remember_artifact(
                project_url=project_url,
                artifact_ref=record.filename,
                artifact_version=record.version,
            )
    payload = {
        "ok": bool(getattr(args, "no_upload", False) or uploaded),
        "action": "src_sync",
        "status": "uploaded" if uploaded else ("packaged" if getattr(args, "no_upload", False) else "upload_failed"),
        "artifact": artifact_payload,
        "included_count": len(included),
        "upload_result": upload_result,
        "project_url": project_url,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"artifact={record.path}")
        print(f"file_count={record.file_count}")
        print(f"sha256={record.sha256}")
        print(f"status={payload['status']}")
    return 0 if payload["ok"] else 1


async def cmd_artifact_current(backend: Any, args: argparse.Namespace) -> int:
    registry = _artifact_registry_from_args(args)
    snapshot = backend.state_snapshot()
    payload = {
        "ok": True,
        "action": "artifact_current",
        "state": {
            "artifact_ref": snapshot.get("artifact_ref"),
            "artifact_version": snapshot.get("artifact_version"),
            "source_ref": snapshot.get("source_ref"),
            "source_version": snapshot.get("source_version"),
            "project_home_url": snapshot.get("resolved_project_home_url"),
        },
        "registry_current": registry.current(),
        "registry_file": str(registry.path),
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        state = payload["state"]
        print(f"artifact_ref={state.get('artifact_ref') or 'none'}")
        print(f"artifact_version={state.get('artifact_version') or 'none'}")
        current = payload.get("registry_current") or {}
        print(f"registry_current={current.get('filename') or 'none'}")
    return 0


async def cmd_artifact_list(backend: Any, args: argparse.Namespace) -> int:
    registry = _artifact_registry_from_args(args)
    artifacts = registry.list()
    payload = {
        "ok": True,
        "action": "artifact_list",
        "count": len(artifacts),
        "artifacts": artifacts,
        "registry_file": str(registry.path),
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if not artifacts:
            print("(no artifacts found)")
        for idx, item in enumerate(artifacts, start=1):
            print(f"{idx:>3}. {item.get('filename')}\t{item.get('version') or ''}\t{item.get('path')}")
    return 0


async def cmd_artifact_release(backend: Any, args: argparse.Namespace) -> int:
    registry = _artifact_registry_from_args(args)
    repo_path = Path(args.path).expanduser().resolve()
    try:
        record, included = create_repo_snapshot(
            repo_path,
            output_dir=_artifact_output_dir(args, registry),
            filename=getattr(args, "filename", None),
            kind="release",
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "action": "artifact_release", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 2
    artifact_payload = registry.add(record)
    project_url = _artifact_state_project_url(backend)
    if project_url:
        _state_store_from_args(args).remember_artifact(
            project_url=project_url,
            artifact_ref=record.filename,
            artifact_version=record.version,
        )
    verify = verify_zip_artifact(record.path)
    payload = {
        "ok": bool(verify.get("ok")),
        "action": "artifact_release",
        "artifact": artifact_payload,
        "included_count": len(included),
        "verify": verify,
        "project_url": project_url,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"artifact={record.path}")
        print(f"file_count={record.file_count}")
        print(f"sha256={record.sha256}")
        print(f"verified={payload['ok']}")
    return 0 if payload["ok"] else 1


async def cmd_artifact_verify(backend: Any, args: argparse.Namespace) -> int:
    registry = _artifact_registry_from_args(args)
    target = getattr(args, "path", None)
    if not target:
        current = registry.current()
        target = current.get("path") if isinstance(current, dict) else None
    if not target:
        payload = {"ok": False, "action": "artifact_verify", "error": "no artifact path provided and no registry artifact exists"}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 2
    verify = verify_zip_artifact(target)
    payload = {"action": "artifact_verify", **verify}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"ok={payload.get('ok')}")
        print(f"path={payload.get('path')}")
        print(f"entry_count={payload.get('entry_count')}")
        print(f"wrapper_folder={payload.get('wrapper_folder') or 'none'}")
    return 0 if payload.get("ok") else 1


async def cmd_artifact(backend: Any, args: argparse.Namespace) -> int:
    if args.artifact_command == "current":
        return await cmd_artifact_current(backend, args)
    if args.artifact_command == "list":
        return await cmd_artifact_list(backend, args)
    if args.artifact_command == "release":
        return await cmd_artifact_release(backend, args)
    if args.artifact_command == "verify":
        return await cmd_artifact_verify(backend, args)
    raise RuntimeError(f"Unknown artifact command: {args.artifact_command}")


async def cmd_src(backend: CommandBackend, args: argparse.Namespace) -> int:
    if args.src_command == "list":
        return await cmd_project_source_list(backend, args)
    if args.src_command == "add":
        return await cmd_project_source_add(backend, args)
    if args.src_command == "sync":
        return await cmd_src_sync(backend, args)
    if args.src_command in {"rm", "remove"}:
        return await cmd_project_source_remove(backend, args)
    raise RuntimeError(f"Unknown src command: {args.src_command}")


def _apply_test_suite_defaults(args: argparse.Namespace) -> None:
    defaults = {
        "json": False,
        "keep_open": False,
        "keep_project": False,
        "step_delay_seconds": 8.0,
        "post_ask_delay_seconds": 20.0,
        "task_list_visible_timeout_seconds": 120.0,
        "task_list_visible_poll_min_seconds": 20.0,
        "task_list_visible_poll_max_seconds": 45.0,
        "task_list_visible_max_attempts": 4,
        "allow_recent_state_task_fallback": False,
        "skip": [],
        "only": [],
        "strict_remove_ui": False,
        "project_name": None,
        "project_name_prefix": "itest-promptbranch",
        "run_id": None,
        "memory_mode": "default",
        "link_url": "https://example.com/",
        "ask_prompt": "Reply with exactly the single token INTEGRATION_OK and nothing else.",
        "json_out": None,
        "project_list_debug_scroll_rounds": 12,
        "project_list_debug_wait_ms": 350,
        "project_list_debug_manual_pause": False,
        "clear_singleton_locks": False,
    }
    for name, value in defaults.items():
        if not hasattr(args, name):
            setattr(args, name, value)


async def cmd_test(backend: CommandBackend, args: argparse.Namespace) -> int:
    del backend
    if args.test_command == "smoke":
        _apply_test_suite_defaults(args)
        return await cmd_test_suite(args)
    raise RuntimeError(f"Unknown test command: {args.test_command}")


async def cmd_doctor(backend: CommandBackend, args: argparse.Namespace) -> int:
    snapshot = backend.state_snapshot()
    project_home_url = snapshot.get("resolved_project_home_url")
    conversation_url = snapshot.get("conversation_url")
    payload = {
        "ok": True,
        "action": "doctor",
        "version": CLI_VERSION,
        "checks": {
            "workspace_selected": bool(project_home_url),
            "task_selected": bool(conversation_url),
            "state_file": bool(snapshot.get("state_file")),
        },
        "state": snapshot,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(f"promptbranch={CLI_VERSION}")
    print(f"state_file={snapshot.get('state_file')}")
    print(f"workspace_selected={str(bool(project_home_url)).lower()}")
    print(f"task_selected={str(bool(conversation_url)).lower()}")
    return 0


async def cmd_debug(backend: CommandBackend, args: argparse.Namespace) -> int:
    if args.debug_command in {"chats", "task-list", "tasks"}:
        result = await backend.debug_project_chats(
            keep_open=args.keep_open,
            scroll_rounds=args.scroll_rounds,
            wait_ms=args.wait_ms,
            include_history=not args.no_history,
            history_max_pages=args.history_max_pages,
            history_max_detail_probes=args.history_max_detail_probes,
            manual_pause=args.manual_pause,
        )
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        counts = result.get("counts") if isinstance(result.get("counts"), dict) else {}
        print(f"artifact_dir={result.get('artifact_dir')}")
        print(f"project_url={result.get('project_url')}")
        print(f"chats_tab_active={str(bool(result.get('chats_tab_active'))).lower()}")
        print(
            "counts="
            f"dom={counts.get('final_dom_project_anchors')}, "
            f"visible_dom={counts.get('final_dom_visible_project_anchors')}, "
            f"snorlax={counts.get('snorlax')}, "
            f"history={counts.get('history')}, "
            f"history_detail={counts.get('history_detail')}, "
            f"combined={counts.get('combined_unique_ids')}"
        )
        print(f"summary={result.get('artifact_dir')}/summary.json")
        return 0
    raise RuntimeError(f"Unknown debug command: {args.debug_command}")


async def cmd_completion(backend: CommandBackend, args: argparse.Namespace) -> int:
    del backend
    print(_render_completion(args.shell, _cli_command_name()), end="")
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

    print(f"{_cli_command_name()} shell")
    print("Type :help for commands.")

    while True:
        try:
            line = input(f"{_cli_command_name()}> ").strip()
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
            answer, _ = _split_ask_response(response)
            if isinstance(answer, (dict, list)):
                print(json.dumps(answer, indent=2, ensure_ascii=False))
            else:
                print(answer)
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
        prog=_cli_command_name(),
        description=f"promptbranch v{CLI_VERSION}: stateful ChatGPT workflow CLI for browser automation or the service API.",
    )
    parser.add_argument("--project-url", default=os.getenv("CHATGPT_PROJECT_URL", DEFAULT_PROJECT_URL))
    parser.add_argument("--email", default=os.getenv("CHATGPT_EMAIL"))
    parser.add_argument("--password", default=os.getenv("CHATGPT_PASSWORD"))
    parser.add_argument("--password-file", default=os.getenv("CHATGPT_PASSWORD_FILE"))
    parser.add_argument("--profile-dir", default=None, help=f"Path to browser profile. Defaults to nearest inherited {PROFILE_DIR_NAME} directory or ./{PROFILE_DIR_NAME}.")
    parser.add_argument("--headless", action="store_true", default=_env_flag("CHATGPT_HEADLESS", False))
    parser.add_argument("--use-playwright", action="store_true", help="Use playwright instead of patchright.")
    parser.add_argument("--browser-channel", default=os.getenv("CHATGPT_BROWSER_CHANNEL"))
    parser.add_argument("--enable-fedcm", action="store_true", help="Do not disable FedCM browser flags.")
    parser.add_argument("--keep-no-sandbox", action="store_true", help="Keep default no-sandbox args instead of filtering them.")
    parser.add_argument("--max-retries", type=int, default=int(os.getenv("CHATGPT_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))))
    parser.add_argument("--retry-backoff-seconds", type=float, default=float(os.getenv("CHATGPT_RETRY_BACKOFF_SECONDS", "2.0")))
    parser.add_argument("--debug", action="store_true", default=_env_flag("CHATGPT_DEBUG", True))
    parser.add_argument("--dotenv", default=".env", help="Optional .env file to load before reading env vars.")
    parser.add_argument(
        "--config",
        default=os.getenv("CHATGPT_CLI_CONFIG", DEFAULT_CONFIG_PATH),
        help=f"Optional JSON config file for CLI defaults. Defaults to {DEFAULT_CONFIG_PATH} (falls back to {LEGACY_CONFIG_PATH} when present).",
    )
    parser.add_argument("--service-base-url", default=_env_or("CHATGPT_SERVICE_BASE_URL", "CHATGPT_API_BASE_URL"), help="Use the Docker service API instead of local browser automation.")
    parser.add_argument("--service-token", default=_env_or("CHATGPT_SERVICE_TOKEN", "CHATGPT_API_TOKEN"), help="Bearer token for the Docker service API.")
    parser.add_argument("--service-timeout-seconds", type=float, default=(_env_or("CHATGPT_SERVICE_TIMEOUT_SECONDS") or None))

    parser.add_argument("--version", action="version", version=f"%(prog)s {CLI_VERSION}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("version", help="Show the installed promptbranch version and exit.")

    login = subparsers.add_parser("login-check", help="Open the browser and verify whether the profile is logged in.")
    login.add_argument("--keep-open", action="store_true")

    ws = subparsers.add_parser("ws", help="Workspace commands for the active ChatGPT project.")
    ws_subparsers = ws.add_subparsers(dest="ws_command", required=True)

    ws_list = ws_subparsers.add_parser("list", help="List available workspaces/projects.")
    ws_list.add_argument("--json", action="store_true", help="Emit the full project list payload as JSON.")
    ws_list.add_argument("--current", action="store_true", help="Show only the current remembered/currently matched workspace.")
    ws_list.add_argument("--keep-open", action="store_true")

    ws_use = ws_subparsers.add_parser("use", help="Select the active workspace/project.")
    ws_use.add_argument("target", nargs="?", help="Project name, project URL, conversation URL, or optional name filter when used with --pick.")
    ws_use.add_argument("--pick", action="store_true", help="Interactively pick from visible ChatGPT projects instead of resolving one exact name.")
    ws_use.add_argument("--conversation-url", help="Optional conversation URL to remember alongside the selected project.")
    ws_use.add_argument("--project-name", help="Optional display name override when selecting by URL.")
    ws_use.add_argument("--json", action="store_true", help="Emit the resulting selection as JSON.")
    ws_use.add_argument("--keep-open", action="store_true")

    ws_current = ws_subparsers.add_parser("current", help="Show the current workspace/project scope.")
    ws_current.add_argument("--json", action="store_true", help="Emit workspace state as JSON.")

    ws_subparsers.add_parser("leave", help="Clear the active workspace and task state.")

    task = subparsers.add_parser("task", help="Task commands for the active workspace.")
    task_subparsers = task.add_subparsers(dest="task_command", required=True)

    task_list = task_subparsers.add_parser("list", help="List indexed tasks for the current workspace, including rows below the initial project chat viewport.")
    task_list.add_argument("--json", action="store_true", help="Emit the full task list payload as JSON.")
    task_list.add_argument("--keep-open", action="store_true")

    task_use = task_subparsers.add_parser("use", help="Select the active task.")
    task_use.add_argument("target", help="Conversation URL, conversation id, id prefix, exact title, or numeric index from task list.")
    task_use.add_argument("--json", action="store_true", help="Emit the resulting selection as JSON.")
    task_use.add_argument("--keep-open", action="store_true")

    task_current = task_subparsers.add_parser("current", help="Show the current task scope.")
    task_current.add_argument("--json", action="store_true", help="Emit task state as JSON.")

    task_leave = task_subparsers.add_parser("leave", help="Leave the current task while keeping the current workspace selected.")
    task_leave.add_argument("--json", action="store_true", help="Emit the resulting state as JSON.")

    task_show = task_subparsers.add_parser("show", help="Show the transcript for the current task or a specified task.")
    task_show.add_argument("target", nargs="?", help="Optional conversation URL, id, id prefix, exact title, or numeric index from task list.")
    task_show.add_argument("--json", action="store_true", help="Emit the full task payload as JSON.")
    task_show.add_argument("--keep-open", action="store_true")

    task_messages = task_subparsers.add_parser("messages", help="Inspect user messages in the current task.")
    task_messages_subparsers = task_messages.add_subparsers(dest="task_messages_command", required=True)
    task_messages_list = task_messages_subparsers.add_parser("list", help="List user messages in the current task.")
    task_messages_list.add_argument("target", nargs="?", help="Optional conversation URL, id, id prefix, exact title, or numeric index from task list.")
    task_messages_list.add_argument("--json", action="store_true", help="Emit grouped message/answer payload as JSON.")
    task_messages_list.add_argument("--keep-open", action="store_true")

    task_message = task_subparsers.add_parser("message", help="Inspect one message subresource in the current task.")
    task_message_subparsers = task_message.add_subparsers(dest="task_message_command", required=True)
    task_message_show = task_message_subparsers.add_parser("show", help="Show one user message by index or id.")
    task_message_show.add_argument("id_or_index", help="Message index, exact id, or unique id prefix.")
    task_message_show.add_argument("--task", dest="target", help="Optional conversation URL, id, id prefix, exact title, or numeric index from task list.")
    task_message_show.add_argument("--json", action="store_true", help="Emit the selected message as JSON.")
    task_message_show.add_argument("--keep-open", action="store_true")

    task_message_answer = task_message_subparsers.add_parser("answer", help="Show assistant answer(s) for one user message.")
    task_message_answer.add_argument("id_or_index", help="Message index, exact id, or unique id prefix.")
    task_message_answer.add_argument("--task", dest="target", help="Optional conversation URL, id, id prefix, exact title, or numeric index from task list.")
    task_message_answer.add_argument("--json", action="store_true", help="Emit answer payload as JSON.")
    task_message_answer.add_argument("--keep-open", action="store_true")

    src = subparsers.add_parser("src", help="Source commands for the active workspace.")
    src_subparsers = src.add_subparsers(dest="src_command", required=True)

    src_list = src_subparsers.add_parser("list", help="List sources for the current workspace.")
    src_list.add_argument("--json", action="store_true", help="Emit the full source list payload as JSON.")
    src_list.add_argument("--keep-open", action="store_true")

    src_add = src_subparsers.add_parser("add", help="Add a source to the current workspace.")
    src_add.add_argument("--type", choices=["link", "text", "file"], default="file")
    src_add.add_argument("--value", help="Source payload for link/text sources.")
    src_add.add_argument("--file", help="Local file path for file sources.")
    src_add.add_argument("--name", help="Optional display name/title to set when the UI supports it.")
    src_add.add_argument("--keep-open", action="store_true")

    src_remove = src_subparsers.add_parser("rm", aliases=["remove"], help="Remove a source from the current workspace.")
    src_remove.add_argument("source_name", help="Visible source name or unique snippet to remove.")
    src_remove.add_argument("--exact", action="store_true", help="Require an exact visible text match.")
    src_remove.add_argument("--keep-open", action="store_true")

    src_sync = src_subparsers.add_parser("sync", help="Package a repo snapshot and upload it as a source for the current workspace.")
    src_sync.add_argument("path", nargs="?", default=".", help="Repo path to package. Defaults to the current directory.")
    src_sync.add_argument("--output-dir", help="Directory for the generated ZIP. Defaults to .pb_profile/artifacts.")
    src_sync.add_argument("--filename", help="Override the generated artifact filename.")
    src_sync.add_argument("--no-upload", action="store_true", help="Only package and register the artifact locally; do not upload as a project source.")
    src_sync.add_argument("--json", action="store_true", help="Emit the sync result as JSON.")
    src_sync.add_argument("--keep-open", action="store_true")

    artifact = subparsers.add_parser("artifact", help="Artifact lifecycle commands for local repo snapshots and release ZIPs.")
    artifact_subparsers = artifact.add_subparsers(dest="artifact_command", required=True)

    artifact_current = artifact_subparsers.add_parser("current", help="Show the current artifact/source state.")
    artifact_current.add_argument("--json", action="store_true")

    artifact_list = artifact_subparsers.add_parser("list", help="List locally registered artifacts.")
    artifact_list.add_argument("--json", action="store_true")

    artifact_release = artifact_subparsers.add_parser("release", help="Create a local release ZIP from a repo path.")
    artifact_release.add_argument("path", nargs="?", default=".", help="Repo path to package. Defaults to the current directory.")
    artifact_release.add_argument("--output-dir", help="Directory for the generated ZIP. Defaults to .pb_profile/artifacts.")
    artifact_release.add_argument("--filename", help="Override the generated artifact filename.")
    artifact_release.add_argument("--json", action="store_true")

    artifact_verify = artifact_subparsers.add_parser("verify", help="Verify ZIP layout and integrity.")
    artifact_verify.add_argument("path", nargs="?", help="ZIP path. Defaults to the latest registered artifact.")
    artifact_verify.add_argument("--json", action="store_true")

    test = subparsers.add_parser("test", help="Reliability test commands.")
    test_subparsers = test.add_subparsers(dest="test_command", required=True)
    test_smoke = test_subparsers.add_parser("smoke", help="Run the standard Promptbranch smoke suite.")
    test_smoke.add_argument("--json", action="store_true", help="Emit the full test-suite summary as JSON.")
    test_smoke.add_argument("--keep-open", action="store_true", help="Keep the browser open between steps where supported.")
    test_smoke.add_argument("--keep-project", action="store_true", help="Do not delete the test project at the end.")
    test_smoke.add_argument("--step-delay-seconds", type=float, default=8.0, help="Delay inserted before each step after the first to reduce ChatGPT rate-limit pressure.")
    test_smoke.add_argument("--post-ask-delay-seconds", type=float, default=20.0, help="Additional cooldown after ask steps before reading task/conversation history.")
    test_smoke.add_argument("--task-list-visible-timeout-seconds", type=float, default=120.0, help="Maximum bounded wait for a task created by ask() to become visible in task listing.")
    test_smoke.add_argument("--task-list-visible-poll-min-seconds", type=float, default=20.0, help="Initial backoff between task-list visibility probes after ask().")
    test_smoke.add_argument("--task-list-visible-poll-max-seconds", type=float, default=45.0, help="Maximum backoff between task-list visibility probes after ask().")
    test_smoke.add_argument("--task-list-visible-max-attempts", type=int, default=4, help="Maximum number of task-list visibility probes after ask().")
    test_smoke.add_argument("--allow-recent-state-task-fallback", action="store_true", help="Allow task_message_flow to pass when a new task is visible only from local recent_state fallback. Default is strict indexed visibility.")
    test_smoke.add_argument("--skip", action="append", default=[], help="Comma-separated step selectors to skip.")
    test_smoke.add_argument("--only", action="append", default=[], help="Comma-separated step selectors to run.")
    test_smoke.add_argument("--strict-remove-ui", action="store_true", help="Require at least one source removal to succeed through the actual UI path.")
    test_smoke.add_argument("--project-name", help="Explicit project name to use. Defaults to a generated unique name.")
    test_smoke.add_argument("--project-name-prefix", default="itest-promptbranch")
    test_smoke.add_argument("--run-id", help="Optional run identifier used when generating names.")
    test_smoke.add_argument("--memory-mode", choices=["default", "project-only"], default="default")
    test_smoke.add_argument("--link-url", default="https://example.com/")
    test_smoke.add_argument("--ask-prompt", default="Reply with exactly the single token INTEGRATION_OK and nothing else.")
    test_smoke.add_argument("--json-out", help="Optional file path where the final JSON summary will be written.")
    test_smoke.add_argument("--project-list-debug-scroll-rounds", type=int, default=12)
    test_smoke.add_argument("--project-list-debug-wait-ms", type=int, default=350)
    test_smoke.add_argument("--project-list-debug-manual-pause", action="store_true")
    test_smoke.add_argument("--clear-singleton-locks", action="store_true", help="Clear stale Chrome Singleton* lock artifacts before launch.")

    doctor = subparsers.add_parser("doctor", help="Run cheap local health checks for the active Promptbranch state.")
    doctor.add_argument("--json", action="store_true", help="Emit doctor checks as JSON.")

    debug = subparsers.add_parser("debug", help="Emit diagnostic artifacts for brittle ChatGPT surfaces.")
    debug_subparsers = debug.add_subparsers(dest="debug_command", required=True)
    debug_chats = debug_subparsers.add_parser("chats", aliases=["task-list", "tasks"], help="Debug project task/chat enumeration and write DOM/network artifacts.")
    debug_chats.add_argument("--json", action="store_true", help="Emit the debug summary as JSON.")
    debug_chats.add_argument("--scroll-rounds", type=int, default=20, help="Maximum project Chats-tab scroll diagnostic rounds.")
    debug_chats.add_argument("--wait-ms", type=int, default=600, help="Wait after each scroll attempt in milliseconds.")
    debug_chats.add_argument("--no-history", action="store_true", help="Skip backend conversation-history/detail probing and only collect DOM/snorlax diagnostics.")
    debug_chats.add_argument("--history-max-pages", type=int, default=5, help="Maximum /backend-api/conversations pages to inspect during debug.")
    debug_chats.add_argument("--history-max-detail-probes", type=int, default=80, help="Maximum conversation detail probes for history classification during debug.")
    debug_chats.add_argument("--manual-pause", action="store_true", help="Pause between key browser states in headed mode for manual inspection.")
    debug_chats.add_argument("--keep-open", action="store_true", help="Keep the browser open after debug collection.")

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

    project_list = subparsers.add_parser(
        "project-list",
        help="List all ChatGPT projects visible in the sidebar for the current account/profile.",
    )
    project_list.add_argument("--json", action="store_true", help="Emit the full project list payload as JSON.")
    project_list.add_argument("--current", action="store_true", help="Show only the current remembered/currently matched project.")
    project_list.add_argument("--keep-open", action="store_true")

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
    source_add.add_argument("--type", choices=["link", "text", "file"], default="file")
    source_add.add_argument("--value", help="Source payload for link/text sources.")
    source_add.add_argument("--file", help="Local file path for file sources.")
    source_add.add_argument("--name", help="Optional display name/title to set when the UI supports it.")
    source_add.add_argument("--keep-open", action="store_true")

    source_list = subparsers.add_parser(
        "project-source-list",
        help="List sources for the configured ChatGPT project (Sources tab).",
    )
    source_list.add_argument("--json", action="store_true", help="Emit the full source list payload as JSON.")
    source_list.add_argument("--keep-open", action="store_true")

    source_remove = subparsers.add_parser(
        "project-source-remove",
        help="Remove a source from the configured ChatGPT project (Sources tab).",
    )
    source_remove.add_argument("source_name", help="Visible source name or unique snippet to remove.")
    source_remove.add_argument("--exact", action="store_true", help="Require an exact visible text match.")
    source_remove.add_argument("--keep-open", action="store_true")

    chat_list = subparsers.add_parser("chat-list", aliases=["chats"], help="Legacy alias. Prefer: pb task list; uses the same deeper task enumeration.")
    chat_list.add_argument("--json", action="store_true", help="Emit the full task list payload as JSON.")
    chat_list.add_argument("--keep-open", action="store_true")

    chat_use = subparsers.add_parser("chat-use", aliases=["use-chat"], help="Legacy alias. Prefer: pb task use.")
    chat_use.add_argument("target", help="Conversation URL, conversation id, id prefix, exact title, or numeric index from chat-list.")
    chat_use.add_argument("--json", action="store_true", help="Emit the resulting selection as JSON.")
    chat_use.add_argument("--keep-open", action="store_true")

    chat_leave = subparsers.add_parser("chat-leave", aliases=["cq"], help="Legacy alias. Prefer: pb task leave.")
    chat_leave.add_argument("--json", action="store_true", help="Emit the resulting state as JSON.")

    chat_show = subparsers.add_parser("chat-show", aliases=["show"], help="Legacy alias. Prefer: pb task show.")
    chat_show.add_argument("target", nargs="?", help="Optional conversation URL, id, id prefix, exact title, or numeric index from chat-list.")
    chat_show.add_argument("--json", action="store_true", help="Emit the full task payload as JSON.")
    chat_show.add_argument("--keep-open", action="store_true")

    chat_summarize = subparsers.add_parser("chat-summarize", aliases=["summarize"], help="Legacy alias for task summarization.")
    chat_summarize.add_argument("target", nargs="?", help="Optional conversation URL, id, id prefix, exact title, or numeric index from chat-list.")
    chat_summarize.add_argument("--json", action="store_true", help="Request a JSON summary response.")
    chat_summarize.add_argument("--keep-open", action="store_true")
    chat_summarize.add_argument("--retries", type=int)

    state = subparsers.add_parser("state", help="Show remembered current project/chat state for the active profile.")
    state.add_argument("--json", action="store_true", help="Emit state as JSON.")

    prompt = subparsers.add_parser("prompt", help="Emit a compact one-line state string for shell prompts or menu bars.")
    prompt.add_argument("--json", action="store_true", help="Emit prompt and backing state as JSON.")

    state_clear = subparsers.add_parser("state-clear", help="Clear remembered current project/chat state for the active profile.")

    use = subparsers.add_parser("use", help="Set the current project/chat state from a project name or ChatGPT URL.")
    use.add_argument("target", nargs="?", help="Project name, project URL, conversation URL, or optional name filter when used with --pick.")
    use.add_argument("--pick", action="store_true", help="Interactively pick from visible ChatGPT projects instead of resolving one exact name.")
    use.add_argument("--conversation-url", help="Optional conversation URL to remember alongside the selected project.")
    use.add_argument("--project-name", help="Optional display name override when selecting by URL.")
    use.add_argument("--json", action="store_true", help="Emit the resulting selection as JSON.")
    use.add_argument("--keep-open", action="store_true")

    completion = subparsers.add_parser("completion", help="Emit shell completion script for bash, zsh, or fish.")
    completion.add_argument("shell", choices=["bash", "zsh", "fish"])

    test_suite = subparsers.add_parser("test-suite", help="Run the standard end-to-end smoke suite for daily verification.")
    test_suite.add_argument("--json", action="store_true", help="Emit the full test-suite summary as JSON.")
    test_suite.add_argument("--keep-open", action="store_true", help="Keep the browser open between steps where supported.")
    test_suite.add_argument("--keep-project", action="store_true", help="Do not delete the test project at the end.")
    test_suite.add_argument("--step-delay-seconds", type=float, default=8.0, help="Delay inserted before each step after the first to reduce ChatGPT rate-limit pressure.")
    test_suite.add_argument("--post-ask-delay-seconds", type=float, default=20.0, help="Additional cooldown after ask steps before reading task/conversation history.")
    test_suite.add_argument("--task-list-visible-timeout-seconds", type=float, default=120.0, help="Maximum bounded wait for a task created by ask() to become visible in task listing.")
    test_suite.add_argument("--task-list-visible-poll-min-seconds", type=float, default=20.0, help="Initial backoff between task-list visibility probes after ask().")
    test_suite.add_argument("--task-list-visible-poll-max-seconds", type=float, default=45.0, help="Maximum backoff between task-list visibility probes after ask().")
    test_suite.add_argument("--task-list-visible-max-attempts", type=int, default=4, help="Maximum number of task-list visibility probes after ask().")
    test_suite.add_argument("--allow-recent-state-task-fallback", action="store_true", help="Allow task_message_flow to pass when a new task is visible only from local recent_state fallback. Default is strict indexed visibility.")
    test_suite.add_argument("--skip", action="append", default=[], help="Comma-separated step selectors to skip.")
    test_suite.add_argument("--only", action="append", default=[], help="Comma-separated step selectors to run.")
    test_suite.add_argument("--strict-remove-ui", action="store_true", help="Require at least one source removal to succeed through the actual UI path.")
    test_suite.add_argument("--project-name", help="Explicit project name to use. Defaults to a generated unique name.")
    test_suite.add_argument("--project-name-prefix", default="itest-promptbranch")
    test_suite.add_argument("--run-id", help="Optional run identifier used when generating names.")
    test_suite.add_argument("--memory-mode", choices=["default", "project-only"], default="default")
    test_suite.add_argument("--link-url", default="https://example.com/")
    test_suite.add_argument("--ask-prompt", default="Reply with exactly the single token INTEGRATION_OK and nothing else.")
    test_suite.add_argument("--json-out", help="Optional file path where the final JSON summary will be written.")
    test_suite.add_argument("--project-list-debug-scroll-rounds", type=int, default=12)
    test_suite.add_argument("--project-list-debug-wait-ms", type=int, default=350)
    test_suite.add_argument("--project-list-debug-manual-pause", action="store_true")
    test_suite.add_argument("--clear-singleton-locks", action="store_true", help="Clear stale Chrome Singleton* lock artifacts before launch.")

    ask = subparsers.add_parser("ask", help="Send one prompt and print the response.")
    ask.add_argument("prompt", nargs="?", help="Prompt text. If omitted, stdin is read.")
    ask.add_argument("--file", help="Optional file to upload with the prompt.")
    ask.add_argument("--json", action="store_true", help="Request strict JSON mode.")
    ask.add_argument("--conversation-url", help="Continue a specific ChatGPT conversation URL instead of the project home or remembered conversation.")
    ask.add_argument("--keep-open", action="store_true")
    ask.add_argument("--retries", type=int)

    shell = subparsers.add_parser("shell", help="Interactive prompt loop.")
    shell.add_argument("--file", help="Optional file to attach by default.")
    shell.add_argument("--json", action="store_true", help="Start shell in JSON mode.")
    shell.add_argument("--keep-open", action="store_true")
    shell.add_argument("--retries", type=int)

    return parser


def _extract_bootstrap_config(argv: list[str]) -> tuple[Optional[str], Optional[str]]:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--dotenv", default=".env")
    bootstrap.add_argument("--config", default=os.getenv("CHATGPT_CLI_CONFIG", DEFAULT_CONFIG_PATH))
    args, _ = bootstrap.parse_known_args(argv)
    return args.dotenv, args.config


def _max_retries_was_configured(argv: list[str]) -> bool:
    if "CHATGPT_MAX_RETRIES" in os.environ:
        return True
    for token in argv:
        if token == "--max-retries" or token.startswith("--max-retries="):
            return True
    return False


def _try_handle_help_command(parser: argparse.ArgumentParser, argv: list[str]) -> Optional[int]:
    if not argv or argv[0] != "help":
        return None
    help_target = argv[1:]
    if not help_target or help_target[0] in {"-h", "--help"}:
        parser.print_help()
        return 0
    try:
        parser.parse_args([help_target[0], "--help", *help_target[1:]])
    except SystemExit as exc:
        return int(exc.code)
    return 0


async def _async_main(args: argparse.Namespace) -> int:
    if args.command == "version":
        print(f"promptbranch {CLI_VERSION}")
        return 0
    if args.command == "completion":
        print(_render_completion(args.shell, _cli_command_name()), end="")
        return 0
    if args.command == "test-suite":
        return await cmd_test_suite(args)
    if args.command == "test" and getattr(args, "test_command", None) == "smoke":
        _apply_test_suite_defaults(args)
        return await cmd_test_suite(args)

    backend = build_backend(args)
    if args.command == "login-check":
        return await cmd_login_check(backend, args)
    if args.command == "ws":
        return await cmd_ws(backend, args)
    if args.command == "task":
        return await cmd_task(backend, args)
    if args.command == "src":
        return await cmd_src(backend, args)
    if args.command == "artifact":
        return await cmd_artifact(backend, args)
    if args.command == "test":
        return await cmd_test(backend, args)
    if args.command == "doctor":
        return await cmd_doctor(backend, args)
    if args.command == "debug":
        return await cmd_debug(backend, args)
    if args.command == "project-create":
        return await cmd_project_create(backend, args)
    if args.command == "project-list":
        return await cmd_project_list(backend, args)
    if args.command == "project-resolve":
        return await cmd_project_resolve(backend, args)
    if args.command == "project-ensure":
        return await cmd_project_ensure(backend, args)
    if args.command == "project-remove":
        return await cmd_project_remove(backend, args)
    if args.command == "project-source-add":
        return await cmd_project_source_add(backend, args)
    if args.command == "project-source-list":
        return await cmd_project_source_list(backend, args)
    if args.command == "project-source-remove":
        return await cmd_project_source_remove(backend, args)
    if args.command in {"chat-list", "chats"}:
        return await cmd_chat_list(backend, args)
    if args.command in {"chat-use", "use-chat"}:
        return await cmd_chat_use(backend, args)
    if args.command in {"chat-leave", "cq"}:
        return await cmd_chat_leave(backend, args)
    if args.command in {"chat-show", "show"}:
        return await cmd_chat_show(backend, args)
    if args.command in {"chat-summarize", "summarize"}:
        return await cmd_chat_summarize(backend, args)
    if args.command == "state":
        return await cmd_state(backend, args)
    if args.command == "prompt":
        return await cmd_prompt(backend, args)
    if args.command == "state-clear":
        return await cmd_state_clear(backend, args)
    if args.command == "use":
        return await cmd_use(backend, args)
    if args.command == "completion":
        return await cmd_completion(backend, args)
    if args.command == "version":
        print(f"promptbranch {CLI_VERSION}")
        return 0
    if args.command == "test-suite":
        return await cmd_test_suite(args)
    if args.command == "ask":
        return await cmd_ask(backend, args)
    if args.command == "shell":
        return await cmd_shell(backend, args)
    raise RuntimeError(f"Unknown command: {args.command}")


def main(argv: Optional[list[str]] = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    normalized_argv = _normalize_global_options(raw_argv)

    dotenv_path, _ = _extract_bootstrap_config(normalized_argv)
    if dotenv_path:
        load_dotenv(dotenv_path, override=False)

    parser = make_parser()
    help_exit_code = _try_handle_help_command(parser, normalized_argv)
    if help_exit_code is not None:
        return help_exit_code
    args = parser.parse_args(normalized_argv)
    args = _apply_cli_config_defaults(args, normalized_argv)
    args.profile_dir = str(resolve_profile_dir(args.profile_dir))
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

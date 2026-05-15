from __future__ import annotations

import argparse
import copy
import asyncio
import hashlib
import json
import io
import os
import shutil
import re
import shlex
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Optional, Protocol

from dotenv import load_dotenv

from promptbranch_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings
from promptbranch_artifacts import ArtifactRecord, ArtifactRegistry, build_source_sync_preflight, create_repo_snapshot, plan_repo_snapshot, utc_now, valid_version_text, verify_zip_artifact
from promptbranch_mcp import (
    DEFAULT_OLLAMA_TOOL_MODEL,
    agent_ask,
    agent_doctor,
    agent_mcp_llm_smoke,
    agent_run,
    agent_summarize_log,
    agent_tool_call,
    mcp_tool_call_via_stdio,
    inspect_local_context,
    mcp_host_config,
    mcp_host_smoke,
    mcp_tool_manifest,
    ollama_models,
    ollama_propose_mcp_tool_call,
    plan_agent_request,
    serve_mcp_stdio,
    skill_list,
    skill_show,
    skill_validate,
)
from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
)
from promptbranch_service_client import ChatGPTServiceClient
from promptbranch_test_suite import package_import_smoke, run_test_suite_async
from promptbranch_test_report import build_test_report, build_test_status, render_test_report_text
from promptbranch_version import PACKAGE_VERSION as CLI_VERSION
from promptbranch_ask_protocol import build_ask_request_envelope, classify_artifact_candidates, parse_promptbranch_reply, render_protocol_ask_prompt
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
DEFAULT_PROTOCOL_ASK_TIMEOUT_SECONDS = 120.0
DEFAULT_PROTOCOL_FRESH_TURN_TIMEOUT_SECONDS = 12.0
DEFAULT_PROTOCOL_FRESH_TURN_POLL_SECONDS = 1.0
DEFAULT_PROTOCOL_SERVICE_TIMEOUT_BUFFER_SECONDS = 90.0
DEFAULT_CONFIG_PATH = "~/.config/promptbranch/config.json"
LEGACY_CONFIG_PATH = "~/.config/chatgpt-cli/config.json"
COMMANDS = {
    "login-check",
    "ask",
    "shell",
    "ws",
    "task",
    "src",
    "artifact",
    "agent",
    "mcp",
    "skill",
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


def _read_prompt_file(path_value: str) -> str:
    if path_value == "-":
        return sys.stdin.read()
    return Path(path_value).read_text(encoding="utf-8")


def _merge_prompt_text(prompt: Optional[str], prompt_file: Optional[str]) -> str:
    parts: list[str] = []
    if prompt:
        parts.append(prompt)
    if prompt_file:
        parts.append(_read_prompt_file(prompt_file).strip())
    elif not prompt and not sys.stdin.isatty():
        parts.append(sys.stdin.read().strip())
    return "\n\n".join(part for part in parts if part)


def _collect_ask_attachment_paths(args: argparse.Namespace) -> list[str]:
    paths: list[str] = []
    legacy_file = getattr(args, "file", None)
    if legacy_file:
        paths.append(legacy_file)
    paths.extend(getattr(args, "attachments", None) or [])
    return paths


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
        overwrite_existing: bool = True,
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
                overwrite_existing=overwrite_existing,
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
        attachment_paths: Optional[list[str]] = None,
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
                attachment_paths=attachment_paths,
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

    def remember_task_list(self, project_url: Optional[str], chats: list[dict[str, Any]]) -> None:
        if self._conversation_state is not None:
            self._conversation_state.remember_task_list(project_url, chats)

    def task_list_cache(self, project_url: Optional[str], *, max_age_seconds: float = 900.0) -> list[dict[str, Any]]:
        if self._conversation_state is None:
            return []
        return self._conversation_state.task_list_cache(project_url, max_age_seconds=max_age_seconds)

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
        overwrite_existing: bool = True,
    ) -> dict[str, Any]:
        return await self._call(
            self._client.add_project_source,
            source_kind=source_kind,
            value=value,
            file_path=file_path,
            display_name=display_name,
            keep_open=keep_open,
            overwrite_existing=overwrite_existing,
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
        attachment_paths: Optional[list[str]] = None,
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
            attachment_paths=attachment_paths,
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

    def remember_task_list(self, project_url: Optional[str], chats: list[dict[str, Any]]) -> None:
        self._conversation_state.remember_task_list(project_url, chats)

    def task_list_cache(self, project_url: Optional[str], *, max_age_seconds: float = 900.0) -> list[dict[str, Any]]:
        return self._conversation_state.task_list_cache(project_url, max_age_seconds=max_age_seconds)

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

    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
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
    payload['visibility_status'] = visibility_status
    payload['indexed_task_count'] = indexed_count
    payload['indexed_observation_count'] = indexed_observation_count
    payload['recent_state_count'] = recent_count
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

    if str(target).isdigit():
        project_home_url = _selected_project_home_url(snapshot) if isinstance(snapshot, dict) else None
        cache_loader = getattr(backend, 'task_list_cache', None)
        if callable(cache_loader):
            try:
                cached_chats = cache_loader(project_home_url, max_age_seconds=900.0)
            except TypeError:
                cached_chats = cache_loader(project_home_url)
            except Exception:
                cached_chats = []
            if cached_chats:
                try:
                    selected = _select_chat_from_list(cached_chats, str(target))
                    selected['_selected_from_task_list_cache'] = True
                    return selected
                except ValueError:
                    # A stale/short cache must not block live resolution.
                    pass

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
    result = await backend.list_project_chats(
        keep_open=args.keep_open,
        include_history_fallback=bool(getattr(args, 'deep_history', False)),
    )
    chats, payload = _chat_list_payload(result, current_conversation_url=snapshot.get('conversation_url'))
    cache_writer = getattr(backend, 'remember_task_list', None)
    if callable(cache_writer):
        try:
            cache_writer(project_home_url, chats)
        except Exception:
            pass
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
        'selected_from_task_list_cache': bool(selected.get('_selected_from_task_list_cache')),
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



def _resolve_task_answer(message: dict[str, Any], *, answer_index: str | None = None, answer_id: str | None = None) -> dict[str, Any]:
    answers = message.get("answers") if isinstance(message.get("answers"), list) else []
    if not answers:
        raise ValueError("selected message has no assistant answers")

    if answer_id:
        target = str(answer_id).strip()
        exact = [item for item in answers if str(item.get("id") or "") == target]
        if len(exact) == 1:
            return exact[0]
        prefix = [item for item in answers if str(item.get("id") or "").startswith(target)]
        if len(prefix) == 1:
            return prefix[0]
        if len(prefix) > 1:
            raise ValueError(f"multiple answers matched id prefix: {target}")
        raise ValueError(f"answer not found: {target}")

    target = str(answer_index or "latest").strip().lower()
    if target in {"last", "latest"}:
        return answers[-1]
    if target.isdigit():
        index = int(target)
        if 1 <= index <= len(answers):
            return answers[index - 1]
        raise ValueError(f"answer index out of range: {target}")
    raise ValueError(f"invalid answer index: {answer_index}")


def _render_task_answer_parse_result(result: dict[str, Any]) -> str:
    lines = [
        f"status={result.get('status')}",
        f"ok={str(bool(result.get('ok'))).lower()}",
        f"message_id={((result.get('message') or {}) if isinstance(result.get('message'), dict) else {}).get('id') or 'none'}",
        f"answer_id={((result.get('answer') or {}) if isinstance(result.get('answer'), dict) else {}).get('id') or 'none'}",
        f"artifact_candidate_count={result.get('artifact_candidate_count') or 0}",
    ]
    candidates = result.get("artifact_candidates") if isinstance(result.get("artifact_candidates"), list) else []
    for candidate in candidates:
        lines.append(
            f"- {candidate.get('filename') or '(missing filename)'}\t"
            f"version={candidate.get('version') or 'unknown'}\t"
            f"role={candidate.get('role') or 'unknown'}\t"
            f"status={candidate.get('status') or 'unknown'}"
        )
    detail = result.get("detail")
    if detail:
        lines.append(f"detail={detail}")
    errors = result.get("validation_errors")
    if errors:
        lines.append("validation_errors=" + ",".join(str(item) for item in errors))
    return "\n".join(lines).rstrip() + "\n"


async def cmd_task_answer_parse(backend: Any, args: argparse.Namespace) -> int:
    try:
        payload = await _fetch_task_messages_payload(backend, args, getattr(args, "target", None))
        message_selector = "latest" if getattr(args, "latest", False) or not getattr(args, "id_or_index", None) else args.id_or_index
        message = _resolve_task_message(payload["messages"], message_selector)
        answer = _resolve_task_answer(
            message,
            answer_index=getattr(args, "answer_index", None),
            answer_id=getattr(args, "answer_id", None),
        )
    except ValueError as exc:
        result = {
            "ok": False,
            "action": "task_answer_parse",
            "status": "answer_selection_failed",
            "error": str(exc),
        }
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1

    parsed = parse_promptbranch_reply(str(answer.get("text") or ""))
    result = {
        **parsed,
        "action": "task_answer_parse",
        "project_url": payload.get("project_url"),
        "conversation_url": payload.get("conversation_url"),
        "conversation_id": payload.get("conversation_id"),
        "title": payload.get("title"),
        "message": {key: value for key, value in message.items() if key != "answers"},
        "answer": {key: value for key, value in answer.items() if key != "text"},
        "selected_answer": _protocol_answer_metadata(message, answer),
        "answer_text_length": len(str(answer.get("text") or "")),
        "automation_performed": False,
        "download_performed": False,
        "migration_performed": False,
        "adoption_performed": False,
    }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(_render_task_answer_parse_result(result), end="")
    return 0 if result.get("ok") else 1


def _artifact_intake_from_parsed_answer(
    parsed: dict[str, Any],
    *,
    expected_filename: str | None = None,
    expected_version: str | None = None,
    expected_repo: str | None = None,
) -> dict[str, Any]:
    candidates = parsed.get("artifact_candidates") if isinstance(parsed.get("artifact_candidates"), list) else []
    classification = classify_artifact_candidates(
        candidates,
        expected_filename=expected_filename,
        expected_version=expected_version,
        expected_repo=expected_repo,
    )
    parse_ok = bool(parsed.get("ok"))
    status = classification.get("status") if parse_ok else parsed.get("status")
    return {
        **classification,
        "ok": bool(parse_ok and classification.get("ok")),
        "action": "artifact_intake",
        "status": status,
        "reply_parse_status": parsed.get("status"),
        "reply_parse_ok": parse_ok,
        "reply_request_id": parsed.get("request_id"),
        "reply_correlation_id": parsed.get("correlation_id"),
        "reply_status": parsed.get("reply_status"),
        "result_type": parsed.get("result_type"),
        "baseline": parsed.get("baseline"),
        "validation": parsed.get("validation"),
        "next_step": parsed.get("next_step"),
        "intake_stage": "candidate_extraction",
        "operator_instruction": "No artifact was downloaded or migrated. Use a later explicit download/verify/migrate intake step after candidate selection is valid.",
    }




def _safe_artifact_inbox_component(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._-")
    return text[:96] or fallback


def _selected_candidate_download_url(candidate: dict[str, Any]) -> str | None:
    download = candidate.get("download") if isinstance(candidate.get("download"), dict) else {}
    url = download.get("url") or candidate.get("url") or candidate.get("download_url")
    if not url:
        link_text = download.get("link_text")
        if isinstance(link_text, str) and urllib.parse.urlparse(link_text.strip()).scheme in {"file", "http", "https"}:
            url = link_text.strip()
    if isinstance(url, str) and url.strip():
        return url.strip()
    return None


def _safe_artifact_filename(filename: Any) -> str | None:
    name = Path(str(filename or "")).name
    if not name or name in {".", ".."}:
        return None
    if name != str(filename or ""):
        return None
    if not name.endswith(".zip"):
        return None
    return name


def _artifact_inbox_dir(*, profile_dir: str | Path, conversation_id: Any, answer_id: Any, request_id: Any) -> Path:
    root = Path(profile_dir).expanduser().resolve() / "artifact_inbox"
    conversation_component = _safe_artifact_inbox_component(conversation_id, fallback="conversation_unknown")
    answer_component = _safe_artifact_inbox_component(answer_id, fallback="answer_unknown")
    request_component = _safe_artifact_inbox_component(request_id, fallback="request_unknown")
    return root / conversation_component / answer_component / request_component


def _copy_or_download_to_path(url: str, target_path: Path, *, timeout_seconds: float) -> None:
    parsed = urllib.parse.urlparse(url)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")
    if parsed.scheme in {"", "file"}:
        source = Path(urllib.request.url2pathname(parsed.path if parsed.scheme == "file" else url)).expanduser()
        if not source.is_file():
            raise FileNotFoundError(str(source))
        with source.open("rb") as src, tmp_path.open("wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
    elif parsed.scheme in {"http", "https"}:
        request = urllib.request.Request(url, headers={"User-Agent": "promptbranch-artifact-intake/0.0.219"})
        with urllib.request.urlopen(request, timeout=max(1.0, float(timeout_seconds))) as response, tmp_path.open("wb") as dst:  # noqa: S310 - operator-supplied artifact URL, explicit command
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
    else:
        raise ValueError(f"unsupported download URL scheme: {parsed.scheme}")
    tmp_path.replace(target_path)


def _artifact_file_metadata(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return {
        "path": str(path),
        "filename": path.name,
        "size_bytes": size,
        "sha256": digest.hexdigest(),
    }


def _artifact_candidates_registry_path(profile_dir: str | Path) -> Path:
    return Path(profile_dir).expanduser().resolve() / "artifact_candidates.json"


def _load_artifact_candidate_registry(profile_dir: str | Path) -> dict[str, Any]:
    path = _artifact_candidates_registry_path(profile_dir)
    if not path.exists():
        return {"schema_version": 1, "candidates": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "candidates": []}
    if not isinstance(payload, dict):
        return {"schema_version": 1, "candidates": []}
    if not isinstance(payload.get("candidates"), list):
        payload["candidates"] = []
    payload.setdefault("schema_version", 1)
    return payload


def _record_artifact_candidate(profile_dir: str | Path, record: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = _artifact_candidates_registry_path(profile_dir)
    payload = _load_artifact_candidate_registry(profile_dir)
    candidates = [item for item in payload.get("candidates", []) if isinstance(item, dict)]
    record_path = str(record.get("path") or "")
    record_filename = str(record.get("filename") or "")
    candidates = [item for item in candidates if not (str(item.get("path") or "") == record_path or (record_filename and str(item.get("filename") or "") == record_filename))]
    candidates.append(record)
    candidates.sort(key=lambda item: str(item.get("migrated_at") or item.get("created_at") or ""), reverse=True)
    payload["schema_version"] = 1
    payload["updated_at"] = utc_now()
    payload["candidates"] = candidates
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path, record


def _candidate_version_normalized(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not text.startswith("v"):
        text = "v" + text
    return text if valid_version_text(text) else None


def _select_artifact_candidate_record(
    profile_dir: str | Path,
    *,
    artifact: str | None = None,
    version: str | None = None,
) -> tuple[Path, dict[str, Any] | None, dict[str, Any]]:
    registry_path = _artifact_candidates_registry_path(profile_dir)
    payload = _load_artifact_candidate_registry(profile_dir)
    candidates = [item for item in payload.get("candidates", []) if isinstance(item, dict)]
    requested_artifact = Path(str(artifact or "")).name if artifact else None
    requested_version = _candidate_version_normalized(version)

    matches: list[dict[str, Any]] = []
    for item in candidates:
        filename = str(item.get("filename") or Path(str(item.get("path") or "")).name)
        item_version = _candidate_version_normalized(item.get("version") or item.get("zip_version") or item.get("filename_version") or _artifact_version_from_filename(filename))
        if requested_artifact and filename != requested_artifact:
            continue
        if requested_version and item_version != requested_version:
            continue
        matches.append(item)

    if not requested_artifact and not requested_version:
        matches = candidates[:1] if candidates else []

    if len(matches) == 1:
        return registry_path, matches[0], {"status": "candidate_selected", "candidate_count": len(candidates), "match_count": 1}
    if not matches:
        return registry_path, None, {"status": "candidate_not_found", "candidate_count": len(candidates), "match_count": 0}
    return registry_path, None, {"status": "candidate_ambiguous", "candidate_count": len(candidates), "match_count": len(matches), "matches": matches[:5]}


def _mark_artifact_candidate_accepted(profile_dir: str | Path, *, candidate: dict[str, Any], current_payload: dict[str, Any]) -> tuple[Path, dict[str, Any] | None]:
    path = _artifact_candidates_registry_path(profile_dir)
    payload = _load_artifact_candidate_registry(profile_dir)
    candidates = [item for item in payload.get("candidates", []) if isinstance(item, dict)]
    target_path = str(candidate.get("path") or "")
    target_filename = str(candidate.get("filename") or "")
    accepted_at = utc_now()
    updated: dict[str, Any] | None = None
    next_candidates: list[dict[str, Any]] = []
    for item in candidates:
        item_path = str(item.get("path") or "")
        item_filename = str(item.get("filename") or "")
        if (target_path and item_path == target_path) or (target_filename and item_filename == target_filename):
            item = {
                **item,
                "status": "accepted_candidate",
                "accepted": True,
                "accepted_at": accepted_at,
                "adoption_performed": True,
                "artifact_current": current_payload,
            }
            updated = item
        next_candidates.append(item)
    payload["schema_version"] = 1
    payload["updated_at"] = accepted_at
    payload["candidates"] = next_candidates
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path, updated


def _report_artifact_current_matches_candidate(current_payload: dict[str, Any], *, filename: str, version: str) -> tuple[bool, dict[str, bool]]:
    state = current_payload.get("state") if isinstance(current_payload.get("state"), dict) else {}
    registry_current = current_payload.get("registry_current") if isinstance(current_payload.get("registry_current"), dict) else {}
    consistency = current_payload.get("consistency") if isinstance(current_payload.get("consistency"), dict) else {}
    checks = {
        "state_artifact_ref_matches_candidate": state.get("artifact_ref") == filename,
        "state_source_ref_matches_candidate": state.get("source_ref") == filename,
        "state_artifact_version_matches_candidate": state.get("artifact_version") == version,
        "state_source_version_matches_candidate": state.get("source_version") == version,
        "registry_current_matches_candidate": registry_current.get("filename") == filename and registry_current.get("version") == version,
        "registry_current_matches_state_artifact": consistency.get("registry_current_matches_state_artifact") is True,
        "state_source_matches_state_artifact": consistency.get("state_source_matches_state_artifact") is True,
        "code_version_matches_state_source": consistency.get("code_version_matches_state_source") is True,
    }
    return all(checks.values()), checks


def _release_control_command_for_candidate(
    repo_root: Path,
    *,
    version: str,
    release_log_keep: int,
    skip_docker_logs: bool = True,
    prune_release_logs: bool = True,
) -> list[str]:
    script = repo_root / "chatgpt_claudecode_workflow_release_control.sh"
    command = [str(script), "--version", version, "--tests-only", "--adopt-if-green"]
    if skip_docker_logs:
        command.append("--skip-docker-logs")
    if prune_release_logs:
        command.append("--prune-release-logs")
    command.extend(["--release-log-keep", str(int(release_log_keep))])
    return command


def _run_release_control_candidate_acceptance(command: list[str], *, repo_root: Path, timeout_seconds: float) -> dict[str, Any]:
    started_at = utc_now()
    try:
        completed = subprocess.run(
            command,
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=max(1.0, float(timeout_seconds)),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "status": "candidate_acceptance_timeout",
            "command": command,
            "started_at": started_at,
            "timeout_seconds": timeout_seconds,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }
    return {
        "ok": completed.returncode == 0,
        "status": "candidate_acceptance_command_ok" if completed.returncode == 0 else "candidate_acceptance_command_failed",
        "command": command,
        "returncode": completed.returncode,
        "started_at": started_at,
        "finished_at": utc_now(),
        "stdout_tail": (completed.stdout or "")[-4000:],
        "stderr_tail": (completed.stderr or "")[-4000:],
    }


def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _migrate_verified_intake_artifact_candidate(result: dict[str, Any], *, profile_dir: str | Path, repo_path: str | Path, conversation_id: Any, answer_id: Any) -> dict[str, Any]:
    if result.get("status") != "verified_candidate" or not result.get("verification_performed"):
        return {**result, "ok": False, "status": "candidate_not_verified", "migration_performed": False, "migration_error": "candidate must be verified before migration; run artifact intake with --verify --migrate", "intake_stage": result.get("intake_stage") or "migration_requested", "adoption_performed": False}

    candidate = result.get("selected_candidate") if isinstance(result.get("selected_candidate"), dict) else None
    filename = _safe_artifact_filename((candidate or {}).get("filename"))
    if not candidate or not filename:
        return {**result, "ok": False, "status": "artifact_wrong_filename", "migration_performed": False, "migration_error": "verified candidate filename must be a basename ending in .zip", "intake_stage": "migration_requested", "adoption_performed": False}

    profile_root = Path(profile_dir).expanduser().resolve()
    inbox_root = profile_root / "artifact_inbox"
    download = result.get("download") if isinstance(result.get("download"), dict) else {}
    source_value = str(download.get("path") or "")
    if source_value:
        source_path = Path(source_value).expanduser().resolve()
    else:
        source_path = (_artifact_inbox_dir(profile_dir=profile_root, conversation_id=conversation_id, answer_id=answer_id, request_id=result.get("reply_request_id")) / filename).resolve()
    if not source_path.is_file():
        return {**result, "ok": False, "status": "artifact_inbox_candidate_missing", "migration_performed": False, "migration_error": "verified candidate ZIP is missing from artifact_inbox", "artifact_inbox_path": str(source_path), "intake_stage": "migration_requested", "adoption_performed": False}
    if not _path_is_relative_to(source_path, inbox_root):
        return {**result, "ok": False, "status": "artifact_inbox_boundary_violation", "migration_performed": False, "migration_error": "migration source must be inside .pb_profile/artifact_inbox", "artifact_inbox_path": str(source_path), "intake_stage": "migration_requested", "adoption_performed": False}

    verification = verify_zip_artifact(source_path)
    if not verification.get("ok"):
        return {**result, "ok": False, "status": "artifact_zip_invalid", "migration_performed": False, "migration_error": str(verification.get("error") or "artifact_zip_invalid"), "verification": verification, "intake_stage": "migration_requested", "adoption_performed": False}

    repo_root = Path(repo_path).expanduser().resolve()
    if not repo_root.is_dir():
        return {**result, "ok": False, "status": "repo_path_invalid", "migration_performed": False, "migration_error": f"repo path is not a directory: {repo_root}", "repo_path": str(repo_root), "intake_stage": "migration_requested", "adoption_performed": False}
    target_path = (repo_root / filename).resolve()
    if target_path.parent != repo_root:
        return {**result, "ok": False, "status": "artifact_wrong_filename", "migration_performed": False, "migration_error": "migration target must stay directly under repo root", "target_path": str(target_path), "intake_stage": "migration_requested", "adoption_performed": False}

    source_metadata = _artifact_file_metadata(source_path)
    target_existed = target_path.exists()
    copy_performed = False
    if target_existed:
        target_metadata_before = _artifact_file_metadata(target_path)
        if target_metadata_before.get("sha256") != source_metadata.get("sha256"):
            return {**result, "ok": False, "status": "artifact_migration_target_exists", "migration_performed": False, "migration_error": "repo-root artifact already exists with different content", "source": source_metadata, "target": target_metadata_before, "target_path": str(target_path), "intake_stage": "migration_requested", "adoption_performed": False}
    else:
        shutil.copy2(source_path, target_path)
        copy_performed = True

    target_metadata = _artifact_file_metadata(target_path)
    zip_version = _read_zip_version_file(target_path) or result.get("zip_version")
    filename_version = _artifact_version_from_filename(filename) or result.get("filename_version")
    migrated_at = utc_now()
    candidate_record = {
        "schema": "promptbranch.artifact.candidate",
        "schema_version": "1.0",
        "kind": "candidate_release",
        "status": "candidate_release",
        "accepted": False,
        "verified": True,
        "filename": filename,
        "version": zip_version or filename_version or candidate.get("version"),
        "path": str(target_path),
        "sha256": target_metadata.get("sha256"),
        "size_bytes": target_metadata.get("size_bytes"),
        "source_inbox_path": str(source_path),
        "source_inbox_sha256": source_metadata.get("sha256"),
        "reply_request_id": result.get("reply_request_id"),
        "reply_correlation_id": result.get("reply_correlation_id"),
        "conversation_id": conversation_id,
        "answer_id": answer_id,
        "verification": verification,
        "zip_version": zip_version,
        "filename_version": filename_version,
        "migrated_at": migrated_at,
        "migration_performed": True,
        "adoption_performed": False,
    }
    registry_path, registry_record = _record_artifact_candidate(profile_root, candidate_record)

    inbox_dir = _artifact_inbox_dir(profile_dir=profile_root, conversation_id=conversation_id, answer_id=answer_id, request_id=result.get("reply_request_id"))
    intake_record_path = inbox_dir / "intake.json"
    try:
        existing: dict[str, Any] = {}
        if intake_record_path.is_file():
            loaded = json.loads(intake_record_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        existing.update({
            "status": "migrated_candidate",
            "migration_performed": True,
            "migration": {"source_path": str(source_path), "target_path": str(target_path), "target_existed": target_existed, "copy_performed": copy_performed, "migrated_at": migrated_at},
            "candidate_registry_path": str(registry_path),
            "candidate_registry_entry": registry_record,
            "adoption_performed": False,
        })
        intake_record_path.parent.mkdir(parents=True, exist_ok=True)
        intake_record_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        return {**result, "ok": False, "status": "artifact_migration_metadata_failed", "migration_performed": True, "migration_error": str(exc), "migration": {"source_path": str(source_path), "target_path": str(target_path), "target_existed": target_existed, "copy_performed": copy_performed}, "candidate_registry_path": str(registry_path), "candidate_registry_entry": registry_record, "intake_stage": "migrated", "adoption_performed": False}

    return {
        **result,
        "ok": True,
        "status": "migrated_candidate",
        "intake_stage": "migrated",
        "migration_performed": True,
        "migration": {"source_path": str(source_path), "target_path": str(target_path), "target_existed": target_existed, "copy_performed": copy_performed, "migrated_at": migrated_at},
        "candidate_registry_path": str(registry_path),
        "candidate_registry_entry": registry_record,
        "intake_record_path": str(intake_record_path),
        "adoption_performed": False,
        "operator_instruction": "Verified candidate ZIP was migrated to the repo root and registered as candidate_release only. Adoption and Project Source mutation were not performed.",
    }


def _download_selected_artifact_candidate(
    result: dict[str, Any],
    *,
    profile_dir: str | Path,
    conversation_id: Any,
    answer_id: Any,
    timeout_seconds: float,
) -> dict[str, Any]:
    if result.get("status") != "candidate_selected" or not isinstance(result.get("selected_candidate"), dict):
        return {
            **result,
            "ok": False,
            "status": "artifact_candidate_not_selected",
            "download_performed": False,
            "download_error": "a single valid candidate must be selected before download",
            "intake_stage": "candidate_extraction",
        }
    candidate = dict(result["selected_candidate"])
    filename = _safe_artifact_filename(candidate.get("filename"))
    if not filename:
        return {
            **result,
            "ok": False,
            "status": "artifact_wrong_filename",
            "download_performed": False,
            "download_error": "selected candidate filename must be a basename ending in .zip",
            "intake_stage": "candidate_extraction",
        }
    url = _selected_candidate_download_url(candidate)
    if not url:
        return {
            **result,
            "ok": False,
            "status": "artifact_download_url_missing",
            "download_performed": False,
            "download_error": "selected candidate has no download.url",
            "intake_stage": "download_requested",
        }
    inbox_dir = _artifact_inbox_dir(
        profile_dir=profile_dir,
        conversation_id=conversation_id,
        answer_id=answer_id,
        request_id=result.get("reply_request_id"),
    )
    target_path = inbox_dir / filename
    overwritten = target_path.exists()
    try:
        _copy_or_download_to_path(url, target_path, timeout_seconds=timeout_seconds)
        metadata = _artifact_file_metadata(target_path)
    except Exception as exc:  # noqa: BLE001 - report explicit operator-facing download failure
        return {
            **result,
            "ok": False,
            "status": "artifact_download_failed",
            "download_performed": False,
            "download_error": str(exc),
            "download_url": url,
            "artifact_inbox_dir": str(inbox_dir),
            "intake_stage": "download_requested",
        }
    if metadata["size_bytes"] <= 0:
        return {
            **result,
            "ok": False,
            "status": "artifact_download_empty",
            "download_performed": True,
            "download": metadata,
            "download_url": url,
            "artifact_inbox_dir": str(inbox_dir),
            "intake_stage": "downloaded",
            "migration_performed": False,
            "adoption_performed": False,
        }
    intake_record = {
        "schema": "promptbranch.artifact.intake.download",
        "schema_version": "1.0",
        "status": "downloaded",
        "candidate": candidate,
        "download": metadata,
        "download_url": url,
        "reply_request_id": result.get("reply_request_id"),
        "reply_correlation_id": result.get("reply_correlation_id"),
        "conversation_id": conversation_id,
        "answer_id": answer_id,
        "created_at": utc_now(),
        "verification_performed": False,
        "migration_performed": False,
        "adoption_performed": False,
    }
    try:
        (inbox_dir / "intake.json").write_text(json.dumps(intake_record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as exc:
        return {
            **result,
            "ok": False,
            "status": "artifact_download_metadata_failed",
            "download_performed": True,
            "download": metadata,
            "download_error": str(exc),
            "download_url": url,
            "artifact_inbox_dir": str(inbox_dir),
            "intake_stage": "downloaded",
        }
    return {
        **result,
        "ok": True,
        "status": "downloaded",
        "intake_stage": "downloaded",
        "download_performed": True,
        "download": metadata,
        "download_url": url,
        "download_overwrote_existing": overwritten,
        "artifact_inbox_dir": str(inbox_dir),
        "intake_record_path": str(inbox_dir / "intake.json"),
        "verification_performed": False,
        "migration_performed": False,
        "adoption_performed": False,
        "operator_instruction": "Artifact was downloaded to .pb_profile/artifact_inbox only. ZIP verification, migration, and adoption were not performed.",
    }


def _verify_intake_artifact_candidate(
    result: dict[str, Any],
    *,
    profile_dir: str | Path,
    conversation_id: Any,
    answer_id: Any,
) -> dict[str, Any]:
    """Verify a selected artifact candidate already present in artifact_inbox.

    This is intentionally an inbox-only verification step. It never migrates the
    ZIP to the repo root, never adopts it, and never mutates Project Sources.
    """

    candidate = result.get("selected_candidate") if isinstance(result.get("selected_candidate"), dict) else None
    if result.get("status") not in {"candidate_selected", "downloaded"} or candidate is None:
        return {
            **result,
            "ok": False,
            "status": "artifact_candidate_not_selected",
            "verification_performed": False,
            "verification_error": "a single valid candidate must be selected before verification",
            "intake_stage": result.get("intake_stage") or "candidate_extraction",
            "migration_performed": False,
            "adoption_performed": False,
        }

    filename = _safe_artifact_filename(candidate.get("filename"))
    if not filename:
        return {
            **result,
            "ok": False,
            "status": "artifact_wrong_filename",
            "verification_performed": False,
            "verification_error": "selected candidate filename must be a basename ending in .zip",
            "intake_stage": result.get("intake_stage") or "candidate_extraction",
            "migration_performed": False,
            "adoption_performed": False,
        }

    inbox_dir = _artifact_inbox_dir(
        profile_dir=profile_dir,
        conversation_id=conversation_id,
        answer_id=answer_id,
        request_id=result.get("reply_request_id"),
    )
    download = result.get("download") if isinstance(result.get("download"), dict) else {}
    candidate_path = Path(str(download.get("path") or inbox_dir / filename)).expanduser().resolve()
    if not candidate_path.is_file():
        return {
            **result,
            "ok": False,
            "status": "artifact_inbox_candidate_missing",
            "verification_performed": False,
            "verification_error": "candidate ZIP is not present in artifact_inbox; run with --download first or provide a persisted intake artifact",
            "artifact_inbox_dir": str(inbox_dir),
            "expected_artifact_path": str(candidate_path),
            "intake_stage": "verification_requested",
            "migration_performed": False,
            "adoption_performed": False,
        }

    verification = verify_zip_artifact(candidate_path)
    zip_version = _read_zip_version_file(candidate_path)
    filename_version = _artifact_version_from_filename(filename) or candidate.get("filename_version")
    expected_version = result.get("expected_version") or candidate.get("expected_version") or candidate.get("version") or filename_version
    expected_version = _artifact_version_from_filename(f"artifact_{expected_version}.zip") if expected_version and valid_version_text(str(expected_version)) else expected_version
    verification_errors: list[str] = []

    if not verification.get("ok"):
        verification_errors.append(str(verification.get("error") or "artifact_zip_invalid"))
    if not verification.get("has_version_file"):
        verification_errors.append("artifact_version_file_missing")
    if zip_version and filename_version and str(zip_version) != str(filename_version):
        verification_errors.append("artifact_version_mismatch")
    if zip_version and expected_version and str(zip_version) != str(expected_version):
        verification_errors.append("artifact_wrong_version")
    if not zip_version and verification.get("has_version_file"):
        verification_errors.append("artifact_version_invalid")

    # Prefer specific semantic errors over the generic artifact_zip_invalid when possible.
    if not verification_errors:
        status = "verified_candidate"
        ok = True
        intake_stage = "verified"
    else:
        status = next((item for item in verification_errors if item != "artifact_zip_invalid"), verification_errors[0])
        ok = False
        intake_stage = "verification_failed"

    verification_record = {
        "schema": "promptbranch.artifact.intake.verification",
        "schema_version": "1.0",
        "status": status,
        "ok": ok,
        "candidate": candidate,
        "download": _artifact_file_metadata(candidate_path),
        "verification": verification,
        "zip_version": zip_version,
        "filename_version": filename_version,
        "expected_version": expected_version,
        "verification_errors": verification_errors,
        "reply_request_id": result.get("reply_request_id"),
        "reply_correlation_id": result.get("reply_correlation_id"),
        "conversation_id": conversation_id,
        "answer_id": answer_id,
        "verified_at": utc_now(),
        "verification_performed": True,
        "migration_performed": False,
        "adoption_performed": False,
    }
    intake_record_path = inbox_dir / "intake.json"
    persisted_record = dict(verification_record)
    try:
        if intake_record_path.is_file():
            existing = json.loads(intake_record_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                persisted_record = {**existing, **verification_record}
        intake_record_path.parent.mkdir(parents=True, exist_ok=True)
        intake_record_path.write_text(json.dumps(persisted_record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        return {
            **result,
            "ok": False,
            "status": "artifact_verification_metadata_failed",
            "verification_performed": True,
            "verification": verification,
            "verification_error": str(exc),
            "artifact_inbox_dir": str(inbox_dir),
            "intake_stage": intake_stage,
            "migration_performed": False,
            "adoption_performed": False,
        }

    return {
        **result,
        "ok": ok,
        "status": status,
        "intake_stage": intake_stage,
        "artifact_inbox_dir": str(inbox_dir),
        "intake_record_path": str(intake_record_path),
        "download": _artifact_file_metadata(candidate_path),
        "verification": verification,
        "zip_version": zip_version,
        "filename_version": filename_version,
        "expected_version": expected_version,
        "verification_errors": verification_errors,
        "verification_performed": True,
        "migration_performed": False,
        "adoption_performed": False,
        "operator_instruction": "Artifact ZIP was verified inside .pb_profile/artifact_inbox only. Migration and adoption were not performed.",
    }

def _render_artifact_intake_result(result: dict[str, Any]) -> str:
    lines = [
        f"status={result.get('status')}",
        f"ok={str(bool(result.get('ok'))).lower()}",
        f"reply_parse_status={result.get('reply_parse_status')}",
        f"artifact_candidate_count={result.get('artifact_candidate_count') or 0}",
        f"zip_candidate_count={result.get('zip_candidate_count') or 0}",
        f"valid_zip_candidate_count={result.get('valid_zip_candidate_count') or 0}",
    ]
    selected = result.get("selected_candidate") if isinstance(result.get("selected_candidate"), dict) else None
    if selected:
        lines.append(f"selected={selected.get('filename')} version={selected.get('filename_version') or selected.get('version')}")
    if result.get("download_performed"):
        download = result.get("download") if isinstance(result.get("download"), dict) else {}
        lines.append(f"downloaded={download.get('path')} size={download.get('size_bytes')} sha256={download.get('sha256')}")
    if result.get("download_error"):
        lines.append(f"download_error={result.get('download_error')}")
    if result.get("verification_performed"):
        lines.append(f"verification={result.get('status')} zip_version={result.get('zip_version')} filename_version={result.get('filename_version')}")
    if result.get("verification_error"):
        lines.append(f"verification_error={result.get('verification_error')}")
    if result.get("migration_performed"):
        migration = result.get("migration") if isinstance(result.get("migration"), dict) else {}
        lines.append(f"migrated={migration.get('target_path')} copy_performed={migration.get('copy_performed')}")
    if result.get("migration_error"):
        lines.append(f"migration_error={result.get('migration_error')}")
    candidates = result.get("artifact_candidates") if isinstance(result.get("artifact_candidates"), list) else []
    for candidate in candidates:
        errors = candidate.get("classification_errors") if isinstance(candidate.get("classification_errors"), list) else []
        lines.append(
            f"- {candidate.get('filename') or '(missing filename)'}\t"
            f"version={candidate.get('filename_version') or candidate.get('version') or 'unknown'}\t"
            f"repo={candidate.get('repo_prefix') or 'unknown'}\t"
            f"status={candidate.get('status') or 'unknown'}\t"
            f"errors={','.join(str(item) for item in errors) if errors else 'none'}"
        )
    return "\n".join(lines).rstrip() + "\n"


async def cmd_artifact_intake(backend: Any, args: argparse.Namespace) -> int:
    if not getattr(args, "from_last_answer", False):
        payload = {
            "ok": False,
            "action": "artifact_intake",
            "status": "intake_source_required",
            "error": "v0.0.219 supports --from-last-answer only",
            "automation_performed": False,
            "download_performed": False,
            "migration_performed": False,
            "adoption_performed": False,
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("error: v0.0.219 supports --from-last-answer only", file=sys.stderr)
        return 1
    try:
        task_target = getattr(args, "target", None)
        payload = await _fetch_task_messages_payload(backend, args, task_target)
        message = _resolve_task_message(payload["messages"], "latest")
        answer = _resolve_task_answer(message, answer_index="latest")
    except ValueError as exc:
        result = {
            "ok": False,
            "action": "artifact_intake",
            "status": "answer_selection_failed",
            "error": str(exc),
            "automation_performed": False,
            "download_performed": False,
            "migration_performed": False,
            "adoption_performed": False,
        }
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1

    parsed = parse_promptbranch_reply(str(answer.get("text") or ""))
    result = _artifact_intake_from_parsed_answer(
        parsed,
        expected_filename=getattr(args, "expect_artifact", None),
        expected_version=getattr(args, "expect_version", None),
        expected_repo=getattr(args, "expect_repo", None),
    )
    result.update(
        {
            "project_url": payload.get("project_url"),
            "conversation_url": payload.get("conversation_url"),
            "conversation_id": payload.get("conversation_id"),
            "title": payload.get("title"),
            "message": {key: value for key, value in message.items() if key != "answers"},
            "answer": {key: value for key, value in answer.items() if key != "text"},
            "answer_text_length": len(str(answer.get("text") or "")),
        }
    )
    if getattr(args, "download", False):
        result = _download_selected_artifact_candidate(
            result,
            profile_dir=getattr(args, "profile_dir", None) or PROFILE_DIR_NAME,
            conversation_id=payload.get("conversation_id"),
            answer_id=answer.get("id"),
            timeout_seconds=float(getattr(args, "download_timeout", 120.0) or 120.0),
        )
    if getattr(args, "verify", False):
        result = _verify_intake_artifact_candidate(
            result,
            profile_dir=getattr(args, "profile_dir", None) or PROFILE_DIR_NAME,
            conversation_id=payload.get("conversation_id"),
            answer_id=answer.get("id"),
        )
    if getattr(args, "migrate", False):
        result = _migrate_verified_intake_artifact_candidate(
            result,
            profile_dir=getattr(args, "profile_dir", None) or PROFILE_DIR_NAME,
            repo_path=getattr(args, "repo_path", ".") or ".",
            conversation_id=payload.get("conversation_id"),
            answer_id=answer.get("id"),
        )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(_render_artifact_intake_result(result), end="")
    return 0 if result.get("ok") else 1


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


def _project_source_add_exception_payload(
    exc: Exception,
    *,
    source_kind: str,
    file_path: Optional[str],
    display_name: Optional[str],
    overwrite_existing: bool,
) -> dict[str, Any]:
    error_text = str(exc)
    status = "source_add_failed"
    if "remove/delete action" in error_text:
        status = "overwrite_remove_failed"
    elif "already exists" in error_text.lower():
        status = "source_already_exists"
    return {
        "ok": False,
        "action": "source_add",
        "status": status,
        "source_kind": source_kind,
        "file_path": file_path,
        "display_name": display_name,
        "overwrite_existing": overwrite_existing,
        "project_source_mutated": False,
        "persistence_verified": False,
        "operator_review_required": status == "overwrite_remove_failed",
        "error": error_text,
    }


async def cmd_project_source_add(backend: CommandBackend, args: argparse.Namespace) -> int:
    source_kind = args.type or "file"
    value = args.value
    positional_file_path = getattr(args, "file_path", None)
    file_path = args.file or positional_file_path
    display_name = args.name
    if args.file and positional_file_path and args.file != positional_file_path:
        print("error: pass the file path either positionally or with --file, not both", file=sys.stderr)
        return 2
    if source_kind != "file" and positional_file_path:
        print("error: positional source path is only supported when --type=file", file=sys.stderr)
        return 2
    if source_kind == "file" and not file_path:
        print("error: file path is required when --type=file", file=sys.stderr)
        return 2
    if source_kind in {"link", "text"} and not value:
        print(f"error: --value is required when --type={source_kind}", file=sys.stderr)
        return 2
    if source_kind == "file" and display_name:
        display_name = Path(display_name).name
    elif source_kind == "file" and file_path and not display_name:
        display_name = Path(file_path).name

    overwrite_existing = not getattr(args, "no_overwrite", False)
    try:
        result = await backend.add_project_source(
            source_kind=source_kind,
            value=value,
            file_path=file_path,
            display_name=display_name,
            keep_open=args.keep_open,
            overwrite_existing=overwrite_existing,
        )
    except Exception as exc:
        result = _project_source_add_exception_payload(
            exc,
            source_kind=source_kind,
            file_path=file_path,
            display_name=display_name,
            overwrite_existing=overwrite_existing,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


async def cmd_project_source_remove(backend: CommandBackend, args: argparse.Namespace) -> int:
    result = await backend.remove_project_source(
        source_name=args.source_name,
        exact=args.exact,
        keep_open=args.keep_open,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _protocol_request_from_current_baseline(
    backend: Any,
    args: argparse.Namespace,
    *,
    prompt: str,
) -> dict[str, Any]:
    registry = _artifact_registry_from_args(args)
    current_payload = _artifact_current_payload(backend, registry)
    state = current_payload.get("state") if isinstance(current_payload.get("state"), dict) else {}
    registry_current = current_payload.get("registry_current") if isinstance(current_payload.get("registry_current"), dict) else {}
    snapshot = backend.state_snapshot()
    current_artifact = state.get("artifact_ref") or registry_current.get("filename")
    current_version = state.get("artifact_version") or registry_current.get("version")
    current_source = state.get("source_ref") or current_artifact
    source_version = state.get("source_version") or current_version
    repo_name = _repo_name_from_artifact_name(str(current_artifact or registry_current.get("filename") or ""))
    request_id = getattr(args, "request_id", None) or f"req_{utc_now().replace('-', '').replace(':', '').replace('.', '').replace('+', 'Z')}"
    artifact = {
        "repo": repo_name,
        "current_baseline": current_artifact,
        "current_version": current_version,
        "source_ref": current_source,
        "source_version": source_version,
        "registry_current": registry_current.get("filename"),
        "registry_current_version": registry_current.get("version"),
    }
    envelope = build_ask_request_envelope(
        prompt=prompt,
        request_id=request_id,
        correlation_id=getattr(args, "correlation_id", None),
        workspace={
            "project_name": snapshot.get("project_name") or project_name_from_url(snapshot.get("resolved_project_home_url") or ""),
            "project_home_url": snapshot.get("resolved_project_home_url"),
        },
        task={
            "conversation_url": getattr(args, "conversation_url", None) or snapshot.get("conversation_url"),
            "conversation_id": conversation_id_from_url(getattr(args, "conversation_url", None) or snapshot.get("conversation_url") or "") or "current",
            "turn_policy": "assistant_may_return_one_protocol_reply",
        },
        artifact=artifact,
        target_version=getattr(args, "target_version", None),
        release_type=getattr(args, "release_type", "normal"),
        intent_kind=getattr(args, "intent_kind", "software_release_request"),
    )
    return {
        "ok": True,
        "action": "ask_protocol_request",
        "status": "request_built",
        "request": envelope,
        "artifact_current": current_payload,
        "automation_performed": False,
        "download_performed": False,
        "migration_performed": False,
        "adoption_performed": False,
    }



def _baseline_from_protocol_request(envelope: dict[str, Any]) -> dict[str, Any]:
    artifact = envelope.get("artifact") if isinstance(envelope.get("artifact"), dict) else {}
    return {
        "input_artifact": artifact.get("current_baseline"),
        "input_version": artifact.get("current_version"),
        "source_ref": artifact.get("source_ref"),
        "source_version": artifact.get("source_version"),
        "target_version": artifact.get("target_version"),
        "release_type": artifact.get("release_type"),
    }


def _validate_protocol_reply_against_request(parsed: dict[str, Any], envelope: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not parsed.get("ok"):
        errors.append(str(parsed.get("status") or "reply_parse_failed"))
        return False, errors

    expected_request_id = envelope.get("request_id")
    expected_correlation_id = envelope.get("correlation_id")
    if expected_request_id and parsed.get("request_id") != expected_request_id:
        errors.append("request_id_mismatch")
    if expected_correlation_id and parsed.get("correlation_id") != expected_correlation_id:
        errors.append("correlation_id_mismatch")

    artifact = envelope.get("artifact") if isinstance(envelope.get("artifact"), dict) else {}
    baseline = parsed.get("baseline") if isinstance(parsed.get("baseline"), dict) else {}
    if artifact.get("current_baseline") and baseline.get("input_artifact") != artifact.get("current_baseline"):
        errors.append("baseline_artifact_mismatch")
    if artifact.get("current_version") and baseline.get("input_version") != artifact.get("current_version"):
        errors.append("baseline_version_mismatch")
    if artifact.get("target_version") and baseline.get("output_version") != artifact.get("target_version"):
        errors.append("target_version_mismatch")
    if artifact.get("release_type") and baseline.get("release_type") != artifact.get("release_type"):
        errors.append("release_type_mismatch")
    return not errors, errors



def _protocol_run_record_path(args: argparse.Namespace, request_id: Any) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(request_id or "unknown")).strip("._") or "unknown"
    return Path(args.profile_dir).expanduser().resolve() / "ask_protocol_runs" / f"{safe}.json"


def _persist_protocol_run_record(args: argparse.Namespace, result: dict[str, Any]) -> str | None:
    request = result.get("request") if isinstance(result.get("request"), dict) else {}
    request_id = request.get("request_id") or result.get("request_id")
    try:
        path = _protocol_run_record_path(args, request_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return str(path)
    except OSError:
        return None


def _protocol_ask_record_dir(args: argparse.Namespace, request_id: Any) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(request_id or "unknown")).strip("._") or "unknown"
    return Path(args.profile_dir).expanduser().resolve() / "ask_records" / safe


def _write_protocol_record_json(path: Path, value: Any) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def _persist_protocol_ask_debug_record(args: argparse.Namespace, result: dict[str, Any]) -> dict[str, str]:
    request = result.get("request") if isinstance(result.get("request"), dict) else {}
    request_id = request.get("request_id") or result.get("request_id")
    record_dir = _protocol_ask_record_dir(args, request_id)
    written: dict[str, str] = {}

    def write_json(name: str, value: Any) -> None:
        if value is None:
            return
        path = record_dir / name
        if _write_protocol_record_json(path, value):
            written[name] = str(path)

    write_json("request.json", request or None)
    write_json("submit_evidence.json", result.get("ask_submit_evidence"))
    pre_marker = result.get("pre_ask_marker") if isinstance(result.get("pre_ask_marker"), dict) else {}
    write_json("before_backend_snapshot.json", pre_marker.get("transcript_snapshot") if isinstance(pre_marker, dict) else None)
    fresh_turn = result.get("fresh_turn_evidence") if isinstance(result.get("fresh_turn_evidence"), dict) else {}
    attempts = fresh_turn.get("attempts") if isinstance(fresh_turn.get("attempts"), list) else []
    if attempts:
        path = record_dir / "after_backend_snapshots.jsonl"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                for attempt in attempts:
                    snapshot = attempt.get("snapshot") if isinstance(attempt, dict) else None
                    if isinstance(snapshot, dict):
                        handle.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n")
            written["after_backend_snapshots.jsonl"] = str(path)
        except OSError:
            pass
    write_json("classification.json", {
        "ok": result.get("ok"),
        "status": result.get("status"),
        "error": result.get("error"),
        "error_type": result.get("error_type"),
        "request_id": result.get("request_id") or request.get("request_id"),
        "conversation_id": result.get("conversation_id"),
        "fresh_turn_evidence": fresh_turn or None,
        "answer_selection": result.get("answer_selection"),
    })
    parsed_reply = {key: result.get(key) for key in ("schema", "schema_version", "request_id", "correlation_id", "result_type", "summary", "baseline", "changes", "artifacts", "validation", "next_step", "confidence") if key in result}
    write_json("reply.parsed.json", parsed_reply or None)
    return written


def _recent_debug_artifacts(limit: int = 12) -> list[str]:
    root = Path.cwd() / "debug_artifacts"
    if not root.is_dir():
        return []
    artifacts: list[Path] = []
    try:
        artifacts = [item for item in root.iterdir() if item.is_file()]
    except OSError:
        return []
    artifacts.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0.0, reverse=True)
    return [str(path) for path in artifacts[: max(0, int(limit))]]


def _protocol_failure_result(
    args: argparse.Namespace,
    *,
    envelope: dict[str, Any],
    status: str,
    error: str,
    error_type: str | None = None,
    ask_response: dict[str, Any] | None = None,
    pre_ask_marker: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = envelope.get("artifact") if isinstance(envelope.get("artifact"), dict) else {}
    return {
        "ok": False,
        "action": "ask_protocol_run",
        "status": status,
        "error": error,
        "error_type": error_type or status,
        "request_id": envelope.get("request_id"),
        "correlation_id": envelope.get("correlation_id"),
        "request": envelope,
        "request_baseline": _baseline_from_protocol_request(envelope),
        "current_baseline": artifact.get("current_baseline"),
        "current_version": artifact.get("current_version"),
        "target_version": artifact.get("target_version"),
        "release_type": artifact.get("release_type"),
        "protocol_timeout_seconds": float(getattr(args, "protocol_timeout_seconds", DEFAULT_PROTOCOL_ASK_TIMEOUT_SECONDS) or DEFAULT_PROTOCOL_ASK_TIMEOUT_SECONDS),
        "service_timeout_seconds": float(getattr(args, "service_timeout_seconds", DEFAULT_SERVICE_TIMEOUT_SECONDS) or DEFAULT_SERVICE_TIMEOUT_SECONDS),
        "ask_response": ask_response,
        "ask_submit_evidence": _protocol_ask_submit_evidence(ask_response),
        "pre_ask_marker": pre_ask_marker,
        "debug_artifacts": _recent_debug_artifacts(),
        "automation_performed": True,
        "download_performed": False,
        "migration_performed": False,
        "adoption_performed": False,
        "operator_instruction": "Protocol ask failed before a validated reply was available. No artifact download, migration, adoption, or Project Source mutation was performed.",
    }




def _protocol_expected_conversation_id(envelope: dict[str, Any]) -> str:
    task = envelope.get("task") if isinstance(envelope.get("task"), dict) else {}
    value = str(task.get("conversation_id") or "").strip()
    if value and value != "current":
        return value
    from_url = conversation_id_from_url(task.get("conversation_url"))
    return str(from_url or "").strip()


def _protocol_expected_conversation_url(envelope: dict[str, Any]) -> str:
    task = envelope.get("task") if isinstance(envelope.get("task"), dict) else {}
    return str(task.get("conversation_url") or "").strip()


def _protocol_conversation_id_from_response(ask_response: dict[str, Any] | None) -> str:
    if not isinstance(ask_response, dict):
        return ""
    value = str(ask_response.get("conversation_id") or "").strip()
    if value:
        return value
    return str(conversation_id_from_url(ask_response.get("conversation_url")) or "").strip()


def _protocol_conversation_lock_mismatch(envelope: dict[str, Any], ask_response: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return mismatch metadata when the service response points to another task.

    Protocol ask parsing is conversation-locked. A response from another
    conversation may contain a valid-looking stale assistant answer, but it is
    not operationally admissible for the current protocol request.
    """

    expected_id = _protocol_expected_conversation_id(envelope)
    if not expected_id:
        return None
    actual_id = _protocol_conversation_id_from_response(ask_response)
    if not actual_id or actual_id == expected_id:
        return None
    return {
        "expected_conversation_id": expected_id,
        "expected_conversation_url": _protocol_expected_conversation_url(envelope) or None,
        "actual_conversation_id": actual_id,
        "actual_conversation_url": ask_response.get("conversation_url") if isinstance(ask_response, dict) else None,
        "status": "submit_clicked_target_conversation_lost",
        "diagnostic": "ask_response conversation_url/conversation_id differs from the protocol request target; parser refused to use the returned assistant text",
    }


def _protocol_ask_submit_evidence(ask_response: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(ask_response, dict):
        return None
    evidence = ask_response.get("submit_evidence")
    return evidence if isinstance(evidence, dict) else None


def _classify_protocol_submit_visibility_failure(
    ask_response: dict[str, Any],
    fresh_turn_evidence: dict[str, Any],
) -> tuple[str, str, str]:
    """Classify failure between browser submit and transcript visibility.

    v0.0.219 keeps submit/click evidence separate from backend transcript
    evidence so the operator can distinguish a failed submit from a stale
    transcript reader or wrong conversation context.
    """

    submit = _protocol_ask_submit_evidence(ask_response)
    source_agreement = fresh_turn_evidence.get("source_agreement") if isinstance(fresh_turn_evidence.get("source_agreement"), dict) else {}
    backend_refresh = fresh_turn_evidence.get("backend_refresh") if isinstance(fresh_turn_evidence.get("backend_refresh"), dict) else {}
    if source_agreement and source_agreement.get("same_conversation_id") is False:
        return (
            "submit_clicked_target_conversation_lost",
            "submit_clicked_target_conversation_lost: post-submit transcript refresh read a different conversation than the protocol request expected",
            "Protocol ask submit evidence was collected, but the task transcript source or ask response points at a different conversation. The parser remained locked to the requested conversation and refused the returned assistant text. No artifact download, migration, adoption, or Project Source mutation was performed.",
        )
    if not submit:
        return (
            "ask_submission_not_visible",
            "ask_submission_not_visible: no newer user message or request_id-matched user turn was visible after the protocol ask submit; browser submit evidence was unavailable",
            "Protocol ask submit evidence was unavailable and no fresh user turn was visible after post-submit refresh/poll. No artifact download, migration, adoption, or Project Source mutation was performed.",
        )
    clicked = bool(submit.get("clicked"))
    enter_fallback = bool(submit.get("enter_fallback_used"))
    dom = submit.get("dom_user_turn_evidence") if isinstance(submit.get("dom_user_turn_evidence"), dict) else {}
    dom_visible = bool(dom.get("visible"))
    if not clicked and not enter_fallback:
        return (
            "ask_submit_not_triggered",
            "ask_submit_not_triggered: browser submit evidence does not show a clicked send button or Enter fallback",
            "Protocol ask was not proven submitted in the browser. No artifact download, migration, adoption, or Project Source mutation was performed.",
        )
    if dom_visible and not fresh_turn_evidence.get("fresh_user_turn_visible"):
        return (
            "submit_visible_but_task_reader_stale",
            "submit_visible_but_task_reader_stale: browser DOM shows the submitted user turn but backend/task transcript did not expose it after polling",
            "Protocol ask was visible in the browser DOM, but not in the backend/task transcript. No artifact download, migration, adoption, or Project Source mutation was performed.",
        )
    composer_cleared = bool(submit.get("composer_cleared"))
    if composer_cleared and backend_refresh and not backend_refresh.get("snapshot_changed"):
        return (
            "submit_visible_but_backend_snapshot_stale",
            "submit_visible_but_backend_snapshot_stale: browser submit cleared the composer, but backend transcript snapshots did not change across refresh attempts",
            "Protocol ask appears submitted because the composer cleared, but backend transcript snapshots stayed stale. No artifact download, migration, adoption, or Project Source mutation was performed.",
        )
    before_user_turns = submit.get("before_user_turns") if isinstance(submit.get("before_user_turns"), dict) else {}
    before_generic = before_user_turns.get("generic_turns") if isinstance(before_user_turns.get("generic_turns"), dict) else {}
    if composer_cleared and not dom_visible and int(before_user_turns.get("count") or 0) == 0 and int(before_generic.get("count") or 0) > 0:
        return (
            "ask_clicked_composer_cleared_dom_selector_missed",
            "ask_clicked_composer_cleared_dom_selector_missed: browser click cleared the composer, but role-specific user-turn selectors did not see existing or new user turns",
            "Protocol ask appears submitted because the composer cleared, but DOM role selectors missed user turns and backend/task transcript stayed stale. No artifact download, migration, adoption, or Project Source mutation was performed.",
        )
    if composer_cleared and not fresh_turn_evidence.get("fresh_user_turn_visible"):
        return (
            "ask_clicked_composer_cleared_backend_stale",
            "ask_clicked_composer_cleared_backend_stale: browser submit cleared the composer, but no newer user turn was exposed by DOM/backend transcript refresh",
            "Protocol ask appears submitted because the composer cleared, but the task transcript did not expose the new turn after polling. No artifact download, migration, adoption, or Project Source mutation was performed.",
        )
    return (
        "ask_clicked_but_no_turn_materialized",
        "ask_clicked_but_no_turn_materialized: browser submit was attempted, but no DOM or backend evidence of a fresh user turn materialized",
        "Protocol ask was submitted or attempted, but no fresh user turn was visible after post-submit refresh/poll. No artifact download, migration, adoption, or Project Source mutation was performed.",
    )


def _emit_protocol_result(args: argparse.Namespace, result: dict[str, Any]) -> int:
    record_path = _persist_protocol_run_record(args, result)
    if record_path:
        result["protocol_run_record_path"] = record_path
        result["request_persisted"] = True
    else:
        result["request_persisted"] = False
    debug_files = _persist_protocol_ask_debug_record(args, result)
    if debug_files:
        result["ask_debug_record_files"] = debug_files
        result["ask_debug_record_dir"] = str(Path(next(iter(debug_files.values()))).parent)
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(_render_task_answer_parse_result(result), end="")
    return 0 if result.get("ok") else 1


def _protocol_turn_number(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _latest_protocol_task_marker(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    latest_message = messages[-1] if messages else None
    latest_answer: dict[str, Any] | None = None
    latest_answer_message: dict[str, Any] | None = None
    for message in reversed(messages):
        answers = message.get("answers") if isinstance(message.get("answers"), list) else []
        if answers:
            latest_answer = answers[-1]
            latest_answer_message = message
            break
    return {
        "available": True,
        "conversation_url": payload.get("conversation_url"),
        "conversation_id": payload.get("conversation_id"),
        "message_count": len(messages),
        "latest_user_message_id": latest_message.get("id") if isinstance(latest_message, dict) else None,
        "latest_user_message_index": latest_message.get("index") if isinstance(latest_message, dict) else None,
        "latest_user_turn_index": latest_message.get("turn_index") if isinstance(latest_message, dict) else None,
        "latest_answer_id": latest_answer.get("id") if isinstance(latest_answer, dict) else None,
        "latest_answer_index": latest_answer.get("index") if isinstance(latest_answer, dict) else None,
        "latest_answer_turn_index": latest_answer.get("turn_index") if isinstance(latest_answer, dict) else None,
        "latest_answer_message_id": latest_answer_message.get("id") if isinstance(latest_answer_message, dict) else None,
        "latest_answer_message_index": latest_answer_message.get("index") if isinstance(latest_answer_message, dict) else None,
    }


def _protocol_prompt_prefix(envelope: dict[str, Any], *, max_length: int = 96) -> str:
    intent = envelope.get("intent") if isinstance(envelope.get("intent"), dict) else {}
    summary = str(intent.get("summary") or "").strip()
    summary = re.sub(r"\s+", " ", summary)
    return summary[:max_length]


def _protocol_flat_turns(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        turns.append({
            "role": "user",
            "id": message.get("id"),
            "index": message.get("index"),
            "turn_index": message.get("turn_index"),
            "create_time": message.get("create_time"),
            "preview": message.get("preview"),
            "text": message.get("text"),
        })
        answers = message.get("answers") if isinstance(message.get("answers"), list) else []
        for answer in answers:
            if not isinstance(answer, dict):
                continue
            turns.append({
                "role": "assistant",
                "id": answer.get("id"),
                "index": answer.get("index"),
                "turn_index": answer.get("turn_index"),
                "create_time": answer.get("create_time"),
                "status": answer.get("status"),
                "preview": answer.get("preview"),
                "text": answer.get("text"),
            })
    return turns


def _protocol_transcript_fingerprint(turns: list[dict[str, Any]]) -> str:
    stable: list[dict[str, Any]] = []
    for turn in turns:
        stable.append({
            "role": turn.get("role"),
            "id": turn.get("id"),
            "index": turn.get("index"),
            "turn_index": turn.get("turn_index"),
            "create_time": turn.get("create_time"),
            "status": turn.get("status"),
            "text_hash": hashlib.sha256(str(turn.get("text") or turn.get("preview") or "").encode("utf-8", errors="replace")).hexdigest(),
        })
    blob = json.dumps(stable, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()


def _protocol_transcript_snapshot(
    payload: dict[str, Any],
    *,
    source: str,
    envelope: dict[str, Any] | None = None,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    turns = _protocol_flat_turns(messages)
    user_turns = [turn for turn in turns if turn.get("role") == "user"]
    assistant_turns = [turn for turn in turns if turn.get("role") == "assistant"]
    latest_turn = turns[-1] if turns else None
    latest_user = user_turns[-1] if user_turns else None
    latest_assistant = assistant_turns[-1] if assistant_turns else None
    request_id = str((envelope or {}).get("request_id") or "")
    prompt_prefix = _protocol_prompt_prefix(envelope or {})
    text_blob = "\n".join(str(message.get("text") or "") for message in messages if isinstance(message, dict))
    return {
        "available": True,
        "source": source,
        "fetched_at": fetched_at or utc_now(),
        "conversation_url": payload.get("conversation_url"),
        "conversation_id": payload.get("conversation_id"),
        "title": payload.get("title"),
        "message_count": len(messages),
        "user_message_count": len(user_turns),
        "assistant_message_count": len(assistant_turns),
        "latest_message_id": latest_turn.get("id") if isinstance(latest_turn, dict) else None,
        "latest_message_role": latest_turn.get("role") if isinstance(latest_turn, dict) else None,
        "latest_create_time": latest_turn.get("create_time") if isinstance(latest_turn, dict) else None,
        "latest_user_message_id": latest_user.get("id") if isinstance(latest_user, dict) else None,
        "latest_user_message_index": latest_user.get("index") if isinstance(latest_user, dict) else None,
        "latest_user_turn_index": latest_user.get("turn_index") if isinstance(latest_user, dict) else None,
        "latest_user_create_time": latest_user.get("create_time") if isinstance(latest_user, dict) else None,
        "latest_assistant_message_id": latest_assistant.get("id") if isinstance(latest_assistant, dict) else None,
        "latest_assistant_message_index": latest_assistant.get("index") if isinstance(latest_assistant, dict) else None,
        "latest_assistant_turn_index": latest_assistant.get("turn_index") if isinstance(latest_assistant, dict) else None,
        "latest_assistant_create_time": latest_assistant.get("create_time") if isinstance(latest_assistant, dict) else None,
        "message_ids_tail": [turn.get("id") for turn in turns[-8:]],
        "roles_tail": [turn.get("role") for turn in turns[-8:]],
        "turn_indexes_tail": [turn.get("turn_index") for turn in turns[-8:]],
        "request_id_found": bool(request_id and request_id in text_blob),
        "prompt_prefix": prompt_prefix,
        "prompt_prefix_found": bool(prompt_prefix and prompt_prefix in text_blob),
        "raw_fingerprint": _protocol_transcript_fingerprint(turns),
    }


def _compare_protocol_transcript_snapshots(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(before, dict) or not before.get("available"):
        return {"available": False, "reason": "before_snapshot_missing"}
    if not isinstance(after, dict) or not after.get("available"):
        return {"available": False, "reason": "after_snapshot_missing"}
    message_count_before = _protocol_turn_number(before.get("message_count")) or 0
    message_count_after = _protocol_turn_number(after.get("message_count")) or 0
    return {
        "available": True,
        "same_conversation_id": before.get("conversation_id") == after.get("conversation_id"),
        "message_count_before": message_count_before,
        "message_count_after": message_count_after,
        "message_count_delta": message_count_after - message_count_before,
        "latest_message_id_changed": before.get("latest_message_id") != after.get("latest_message_id"),
        "latest_user_message_id_changed": before.get("latest_user_message_id") != after.get("latest_user_message_id"),
        "latest_assistant_message_id_changed": before.get("latest_assistant_message_id") != after.get("latest_assistant_message_id"),
        "fingerprint_changed": before.get("raw_fingerprint") != after.get("raw_fingerprint"),
    }


def _protocol_backend_refresh_summary(attempts: list[dict[str, Any]], before_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    comparisons = [attempt.get("snapshot_comparison") for attempt in attempts if isinstance(attempt.get("snapshot_comparison"), dict)]
    available = [item for item in comparisons if item.get("available")]
    last = available[-1] if available else {}
    return {
        "attempt_count": len(attempts),
        "before_snapshot_available": bool(isinstance(before_snapshot, dict) and before_snapshot.get("available")),
        "snapshot_changed": any(bool(item.get("fingerprint_changed")) for item in available),
        "message_count_delta": last.get("message_count_delta"),
        "latest_message_id_changed": any(bool(item.get("latest_message_id_changed")) for item in available),
        "latest_user_message_id_changed": any(bool(item.get("latest_user_message_id_changed")) for item in available),
        "latest_assistant_message_id_changed": any(bool(item.get("latest_assistant_message_id_changed")) for item in available),
        "fingerprint_changed": any(bool(item.get("fingerprint_changed")) for item in available),
        "latest_comparison": last or None,
    }


def _message_after_protocol_marker(message: dict[str, Any], marker: dict[str, Any] | None) -> bool:
    if not isinstance(marker, dict) or not marker.get("available"):
        return True
    msg_index = _protocol_turn_number(message.get("index"))
    marker_msg_index = _protocol_turn_number(marker.get("message_count") or marker.get("latest_user_message_index"))
    if msg_index is not None and marker_msg_index is not None and msg_index > marker_msg_index:
        return True
    msg_turn = _protocol_turn_number(message.get("turn_index"))
    marker_turn = _protocol_turn_number(marker.get("latest_user_turn_index"))
    if msg_turn is not None and marker_turn is not None and msg_turn > marker_turn:
        return True
    return False


def _answer_after_protocol_marker(answer: dict[str, Any], marker: dict[str, Any] | None) -> bool:
    if not isinstance(marker, dict) or not marker.get("available"):
        return True
    answer_turn = _protocol_turn_number(answer.get("turn_index"))
    marker_turn = _protocol_turn_number(marker.get("latest_answer_turn_index"))
    if answer_turn is not None and marker_turn is not None:
        return answer_turn > marker_turn
    answer_id = str(answer.get("id") or "")
    marker_id = str(marker.get("latest_answer_id") or "")
    return bool(answer_id and marker_id and answer_id != marker_id)


def _protocol_answer_metadata(message: dict[str, Any] | None, answer: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "message_id": message.get("id") if isinstance(message, dict) else None,
        "message_index": message.get("index") if isinstance(message, dict) else None,
        "message_turn_index": message.get("turn_index") if isinstance(message, dict) else None,
        "answer_id": answer.get("id") if isinstance(answer, dict) else None,
        "answer_index": answer.get("index") if isinstance(answer, dict) else None,
        "answer_turn_index": answer.get("turn_index") if isinstance(answer, dict) else None,
    }


def _select_protocol_reply_message_answer(
    messages: list[dict[str, Any]],
    *,
    args: argparse.Namespace,
    envelope: dict[str, Any],
    pre_ask_marker: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request_id = str(envelope.get("request_id") or "")

    if getattr(args, "answer_id", None):
        for message in messages:
            answers = message.get("answers") if isinstance(message.get("answers"), list) else []
            try:
                answer = _resolve_task_answer(message, answer_id=getattr(args, "answer_id", None))
            except ValueError:
                continue
            is_after = _message_after_protocol_marker(message, pre_ask_marker) or _answer_after_protocol_marker(answer, pre_ask_marker)
            if not is_after and request_id and request_id not in str(answer.get("text") or ""):
                raise ValueError("stale_answer_detected: explicit answer id selected an answer older than the protocol ask")
            return message, answer, {
                "policy": "explicit_answer_id",
                "fresh_request_message_matched": request_id in str(message.get("text") or "") if request_id else False,
                "selected_answer_is_after_pre_ask_marker": is_after,
            }
        raise ValueError(f"answer not found: {getattr(args, 'answer_id', None)}")

    request_messages = [message for message in messages if request_id and request_id in str(message.get("text") or "")]
    if request_messages:
        candidate_messages = request_messages
        policy = "request_id_message_match"
        fresh_match = True
    elif isinstance(pre_ask_marker, dict) and pre_ask_marker.get("available"):
        candidate_messages = [message for message in messages if _message_after_protocol_marker(message, pre_ask_marker)]
        policy = "newer_than_pre_ask_marker"
        fresh_match = False
        if not candidate_messages:
            raise ValueError("stale_answer_detected: no user message newer than the protocol ask pre-marker was found")
    else:
        candidate_messages = messages[-1:] if messages else []
        policy = "latest_without_pre_ask_marker"
        fresh_match = False

    if not candidate_messages:
        raise ValueError("assistant_not_detected: no candidate user message is available for protocol reply parsing")

    for message in reversed(candidate_messages):
        answers = message.get("answers") if isinstance(message.get("answers"), list) else []
        if not answers:
            continue
        answer = _resolve_task_answer(message, answer_index=getattr(args, "answer_index", None), answer_id=None)
        is_after = _message_after_protocol_marker(message, pre_ask_marker) or _answer_after_protocol_marker(answer, pre_ask_marker)
        if isinstance(pre_ask_marker, dict) and pre_ask_marker.get("available") and not is_after and not fresh_match:
            raise ValueError("stale_answer_detected: selected assistant answer is not newer than the protocol ask pre-marker")
        return message, answer, {
            "policy": policy,
            "fresh_request_message_matched": fresh_match,
            "selected_answer_is_after_pre_ask_marker": is_after,
        }

    if policy == "request_id_message_match":
        raise ValueError("assistant_not_detected: protocol request message was found but it has no assistant answer yet")
    raise ValueError("stale_answer_detected: no newer assistant answer was found after the protocol ask")


async def _capture_pre_ask_protocol_marker(backend: Any, args: argparse.Namespace) -> dict[str, Any] | None:
    conversation_url = str(
        getattr(args, "conversation_url", None)
        or _state_store_from_args(args).snapshot(getattr(args, "project_url", None)).get("conversation_url")
        or ""
    )
    if not conversation_url:
        return None
    try:
        chat = await backend.get_chat(conversation_url, keep_open=getattr(args, "keep_open", False))
        payload = _task_messages_payload(chat)
        marker = _latest_protocol_task_marker(payload)
        marker["capture_status"] = "captured"
        marker["transcript_snapshot"] = _protocol_transcript_snapshot(payload, source="pre_ask_task_messages", envelope=None)
        return marker
    except Exception as exc:
        return {
            "available": False,
            "capture_status": "failed",
            "conversation_url": conversation_url,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }


def _is_protocol_parse_ask(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "command", None) == "ask" and getattr(args, "protocol", False) and getattr(args, "parse_reply", False))


def _protocol_service_timeout_floor(args: argparse.Namespace) -> float:
    """Minimum HTTP read timeout for a protocol ask transaction.

    The browser service has to submit the ask, wait for the assistant response
    or service-side timeout, and return submit evidence. The client read
    timeout must therefore be larger than the protocol response wait budget,
    not equal to or smaller than it.
    """

    protocol_timeout = max(1.0, float(getattr(args, "protocol_timeout_seconds", DEFAULT_PROTOCOL_ASK_TIMEOUT_SECONDS) or DEFAULT_PROTOCOL_ASK_TIMEOUT_SECONDS))
    fresh_turn_timeout = max(0.0, float(getattr(args, "protocol_fresh_turn_timeout_seconds", DEFAULT_PROTOCOL_FRESH_TURN_TIMEOUT_SECONDS) or 0.0))
    buffer_seconds = max(30.0, float(DEFAULT_PROTOCOL_SERVICE_TIMEOUT_BUFFER_SECONDS))
    return protocol_timeout + fresh_turn_timeout + buffer_seconds


def _apply_protocol_timeout(args: argparse.Namespace) -> None:
    if not _is_protocol_parse_ask(args):
        return
    timeout = max(1.0, float(getattr(args, "protocol_timeout_seconds", DEFAULT_PROTOCOL_ASK_TIMEOUT_SECONDS) or DEFAULT_PROTOCOL_ASK_TIMEOUT_SECONDS))
    args.protocol_timeout_seconds = timeout
    if getattr(args, "service_base_url", None):
        current = float(getattr(args, "service_timeout_seconds", DEFAULT_SERVICE_TIMEOUT_SECONDS) or DEFAULT_SERVICE_TIMEOUT_SECONDS)
        args.service_timeout_seconds = max(current, _protocol_service_timeout_floor(args))



def _protocol_request_message_matches(messages: list[dict[str, Any]], envelope: dict[str, Any]) -> list[dict[str, Any]]:
    request_id = str(envelope.get("request_id") or "")
    if not request_id:
        return []
    return [message for message in messages if request_id in str(message.get("text") or "")]


def _protocol_new_user_messages(messages: list[dict[str, Any]], pre_ask_marker: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(pre_ask_marker, dict) or not pre_ask_marker.get("available"):
        return messages[-1:] if messages else []
    return [message for message in messages if _message_after_protocol_marker(message, pre_ask_marker)]


def _protocol_fresh_turn_evidence(
    payload: dict[str, Any],
    *,
    pre_ask_marker: dict[str, Any] | None,
    envelope: dict[str, Any],
    attempts: list[dict[str, Any]] | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    request_matches = _protocol_request_message_matches(messages, envelope)
    newer_messages = _protocol_new_user_messages(messages, pre_ask_marker)
    marker_count = _protocol_turn_number(pre_ask_marker.get("message_count") if isinstance(pre_ask_marker, dict) else None) if isinstance(pre_ask_marker, dict) else None
    message_count = len(messages)
    latest_marker = _latest_protocol_task_marker(payload)
    transcript_snapshot = snapshot or _protocol_transcript_snapshot(payload, source="task_messages", envelope=envelope)
    before_snapshot = pre_ask_marker.get("transcript_snapshot") if isinstance(pre_ask_marker, dict) and isinstance(pre_ask_marker.get("transcript_snapshot"), dict) else None
    backend_refresh = _protocol_backend_refresh_summary(attempts or [], before_snapshot)
    task = envelope.get("task") if isinstance(envelope.get("task"), dict) else {}
    expected_conversation_id = _protocol_expected_conversation_id(envelope)
    actual_conversation_id = str(payload.get("conversation_id") or "")
    same_conversation_id = (not expected_conversation_id) or expected_conversation_id == actual_conversation_id
    prompt_prefix = _protocol_prompt_prefix(envelope)
    prompt_prefix_matches = [message for message in messages if prompt_prefix and prompt_prefix in str(message.get("text") or "")]
    fresh_user_turn_visible = bool(same_conversation_id and (request_matches or newer_messages or prompt_prefix_matches))
    return {
        "fresh_user_turn_visible": fresh_user_turn_visible,
        "request_message_found": bool(request_matches),
        "prompt_prefix_found": bool(prompt_prefix_matches),
        "newer_user_message_count": len(newer_messages),
        "request_message_count": len(request_matches),
        "prompt_prefix_message_count": len(prompt_prefix_matches),
        "message_count_before": marker_count,
        "message_count_after": message_count,
        "message_count_delta": (message_count - marker_count) if marker_count is not None else None,
        "expected_conversation_id": expected_conversation_id or None,
        "actual_conversation_id": actual_conversation_id or None,
        "source_agreement": {
            "same_conversation_id": same_conversation_id,
            "expected_conversation_id": expected_conversation_id or None,
            "actual_conversation_id": actual_conversation_id or None,
        },
        "latest_marker": latest_marker,
        "backend_refresh": backend_refresh,
        "transcript_snapshot": transcript_snapshot,
        "attempt_count": len(attempts or []),
        "attempts": attempts or [],
    }

async def _wait_for_protocol_fresh_turn(
    backend: Any,
    args: argparse.Namespace,
    *,
    conversation_url: str,
    envelope: dict[str, Any],
    pre_ask_marker: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch/poll chat state until the protocol ask is visible as a fresh user turn."""

    timeout = max(0.0, float(getattr(args, "protocol_fresh_turn_timeout_seconds", DEFAULT_PROTOCOL_FRESH_TURN_TIMEOUT_SECONDS) or 0.0))
    poll_seconds = max(0.1, float(getattr(args, "protocol_fresh_turn_poll_seconds", DEFAULT_PROTOCOL_FRESH_TURN_POLL_SECONDS) or DEFAULT_PROTOCOL_FRESH_TURN_POLL_SECONDS))
    deadline = time.monotonic() + timeout
    attempts: list[dict[str, Any]] = []
    last_payload: dict[str, Any] | None = None
    attempt = 0
    while True:
        attempt += 1
        chat = await backend.get_chat(conversation_url, keep_open=getattr(args, "keep_open", False))
        payload = _task_messages_payload(chat)
        last_payload = payload
        before_snapshot = pre_ask_marker.get("transcript_snapshot") if isinstance(pre_ask_marker, dict) and isinstance(pre_ask_marker.get("transcript_snapshot"), dict) else None
        snapshot = _protocol_transcript_snapshot(payload, source="post_ask_task_messages", envelope=envelope)
        comparison = _compare_protocol_transcript_snapshots(before_snapshot, snapshot)
        evidence = _protocol_fresh_turn_evidence(payload, pre_ask_marker=pre_ask_marker, envelope=envelope, attempts=attempts, snapshot=snapshot)
        attempts.append({
            "attempt": attempt,
            "message_count_after": evidence.get("message_count_after"),
            "message_count_delta": evidence.get("message_count_delta"),
            "request_message_found": evidence.get("request_message_found"),
            "prompt_prefix_found": evidence.get("prompt_prefix_found"),
            "newer_user_message_count": evidence.get("newer_user_message_count"),
            "fresh_user_turn_visible": evidence.get("fresh_user_turn_visible"),
            "snapshot": snapshot,
            "snapshot_comparison": comparison,
            "latest_user_message_id": (evidence.get("latest_marker") or {}).get("latest_user_message_id") if isinstance(evidence.get("latest_marker"), dict) else None,
            "latest_user_message_index": (evidence.get("latest_marker") or {}).get("latest_user_message_index") if isinstance(evidence.get("latest_marker"), dict) else None,
            "latest_answer_id": (evidence.get("latest_marker") or {}).get("latest_answer_id") if isinstance(evidence.get("latest_marker"), dict) else None,
        })
        evidence = _protocol_fresh_turn_evidence(payload, pre_ask_marker=pre_ask_marker, envelope=envelope, attempts=attempts, snapshot=snapshot)
        if evidence["fresh_user_turn_visible"]:
            evidence["status"] = "fresh_turn_visible"
            evidence["timeout_seconds"] = timeout
            evidence["poll_seconds"] = poll_seconds
            return payload, evidence
        remaining = deadline - time.monotonic()
        if timeout <= 0.0 or remaining <= 0.0:
            evidence["status"] = "ask_submission_not_visible"
            evidence["timeout_seconds"] = timeout
            evidence["poll_seconds"] = poll_seconds
            return payload, evidence
        await asyncio.sleep(min(poll_seconds, max(0.0, remaining)))


def _protocol_ask_response_failure_result(
    args: argparse.Namespace,
    *,
    envelope: dict[str, Any],
    ask_response: dict[str, Any],
    pre_ask_marker: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Convert a service-returned ask failure into protocol-run JSON.

    v0.0.219 relies on the browser service returning partial submit evidence
    when assistant response waiting times out. Such a response is a terminal
    protocol failure, not a reply to parse.
    """

    if not isinstance(ask_response, dict) or ask_response.get("ok", True):
        return None
    status = str(ask_response.get("status") or "ask_failed")
    error = str(ask_response.get("error") or status)
    result = _protocol_failure_result(
        args,
        envelope=envelope,
        status=status,
        error=error,
        error_type=str(ask_response.get("error_type") or status),
        ask_response=ask_response,
        pre_ask_marker=pre_ask_marker,
    )
    result["partial_submit_evidence_returned"] = _protocol_ask_submit_evidence(ask_response) is not None
    result["timeout_layer"] = ask_response.get("timeout_layer") or ("assistant_response" if "timeout" in status else "service")
    if "debug_artifacts" in ask_response and isinstance(ask_response.get("debug_artifacts"), list):
        result["debug_artifacts"] = ask_response.get("debug_artifacts")
    result["operator_instruction"] = "Protocol ask reached the browser service but failed before a validated reply was available. Partial submit evidence is included when available. No artifact download, migration, adoption, or Project Source mutation was performed."
    return result


async def _parse_protocol_reply_after_ask(
    backend: Any,
    args: argparse.Namespace,
    *,
    envelope: dict[str, Any],
    ask_response: dict[str, Any],
    pre_ask_marker: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected_conversation_url = _protocol_expected_conversation_url(envelope)
    expected_conversation_id = _protocol_expected_conversation_id(envelope)
    response_conversation_id = _protocol_conversation_id_from_response(ask_response)
    lock_mismatch = _protocol_conversation_lock_mismatch(envelope, ask_response)
    conversation_url = str(
        expected_conversation_url
        or getattr(args, "conversation_url", None)
        or _state_store_from_args(args).load().conversation_url
        or ask_response.get("conversation_url")
        or ""
    )
    if lock_mismatch is not None:
        result = {
            "ok": False,
            "action": "ask_protocol_run",
            "status": "submit_clicked_target_conversation_lost",
            "error": "submit_clicked_target_conversation_lost: browser/service returned a different conversation than the protocol request target; refusing to parse stale or wrong-conversation assistant text",
            "error_type": "conversation_lock_mismatch",
            "request": envelope,
            "request_baseline": _baseline_from_protocol_request(envelope),
            "ask_response": ask_response,
            "ask_submit_evidence": _protocol_ask_submit_evidence(ask_response),
            "conversation_url": conversation_url,
            "conversation_id": expected_conversation_id or None,
            "response_conversation_id": response_conversation_id or None,
            "conversation_lock": lock_mismatch,
            "answer_selection": {"policy": "conversation_locked_protocol_reply_required", "selected": None},
            "debug_artifacts": _recent_debug_artifacts(),
            "automation_performed": True,
            "download_performed": False,
            "migration_performed": False,
            "adoption_performed": False,
            "operator_instruction": "Protocol ask submit returned or followed a different conversation. The parser stayed locked to the requested conversation and refused to use returned assistant text. No artifact download, migration, adoption, or Project Source mutation was performed.",
        }
        return result
    if not conversation_url:
        return {
            "ok": False,
            "action": "ask_protocol_run",
            "status": "conversation_url_missing",
            "error": "ask response did not include a conversation_url and no current task is selected",
            "request": envelope,
            "ask_response": ask_response,
            "automation_performed": True,
            "download_performed": False,
            "migration_performed": False,
            "adoption_performed": False,
        }

    payload, fresh_turn_evidence = await _wait_for_protocol_fresh_turn(
        backend,
        args,
        conversation_url=conversation_url,
        envelope=envelope,
        pre_ask_marker=pre_ask_marker,
    )
    post_ask_marker = _latest_protocol_task_marker(payload)
    if not fresh_turn_evidence.get("fresh_user_turn_visible"):
        failure_status, failure_error, operator_instruction = _classify_protocol_submit_visibility_failure(ask_response, fresh_turn_evidence)
        return {
            "ok": False,
            "action": "ask_protocol_run",
            "status": failure_status,
            "error": failure_error,
            "request": envelope,
            "request_baseline": _baseline_from_protocol_request(envelope),
            "ask_response": ask_response,
            "ask_submit_evidence": _protocol_ask_submit_evidence(ask_response),
            "conversation_url": conversation_url,
            "conversation_id": payload.get("conversation_id"),
            "title": payload.get("title"),
            "pre_ask_marker": pre_ask_marker,
            "post_ask_marker": post_ask_marker,
            "fresh_turn_evidence": fresh_turn_evidence,
            "answer_selection": {"policy": "fresh_protocol_reply_required", "selected": None},
            "debug_artifacts": _recent_debug_artifacts(),
            "automation_performed": True,
            "download_performed": False,
            "migration_performed": False,
            "adoption_performed": False,
            "operator_instruction": operator_instruction,
        }
    try:
        message, answer, selection = _select_protocol_reply_message_answer(
            payload["messages"],
            args=args,
            envelope=envelope,
            pre_ask_marker=pre_ask_marker,
        )
    except ValueError as exc:
        status = "answer_selection_failed"
        error_text = str(exc)
        if error_text.startswith("stale_answer_detected"):
            status = "stale_answer_detected"
        elif error_text.startswith("assistant_not_detected"):
            status = "fresh_user_turn_visible_reply_timeout"
        return {
            "ok": False,
            "action": "ask_protocol_run",
            "status": status,
            "error": error_text,
            "request": envelope,
            "request_baseline": _baseline_from_protocol_request(envelope),
            "ask_response": ask_response,
            "ask_submit_evidence": _protocol_ask_submit_evidence(ask_response),
            "conversation_url": conversation_url,
            "conversation_id": payload.get("conversation_id"),
            "title": payload.get("title"),
            "pre_ask_marker": pre_ask_marker,
            "post_ask_marker": post_ask_marker,
            "fresh_turn_evidence": fresh_turn_evidence,
            "answer_selection": {"policy": "fresh_protocol_reply_required", "selected": None},
            "automation_performed": True,
            "download_performed": False,
            "migration_performed": False,
            "adoption_performed": False,
        }

    selected_answer_text = str(answer.get("text") or "")
    parsed = parse_promptbranch_reply(selected_answer_text)
    validation_ok, validation_errors = _validate_protocol_reply_against_request(parsed, envelope)
    status = "reply_validated" if validation_ok else "reply_validation_failed"
    normalized_ask_response = _normalize_protocol_ask_response_for_selected_reply(
        ask_response,
        selected_answer_text=selected_answer_text,
        selected_answer=answer,
        validation_ok=validation_ok,
    )
    result = {
        **parsed,
        "ok": bool(parsed.get("ok") and validation_ok),
        "action": "ask_protocol_run",
        "status": status,
        "request": envelope,
        "request_baseline": _baseline_from_protocol_request(envelope),
        "reply_validation_ok": validation_ok,
        "reply_validation_errors": validation_errors,
        "ask_response": normalized_ask_response,
        "ask_submit_evidence": _protocol_ask_submit_evidence(ask_response),
        "conversation_url": payload.get("conversation_url") or conversation_url,
        "conversation_id": payload.get("conversation_id"),
        "title": payload.get("title"),
        "message": {key: value for key, value in message.items() if key != "answers"},
        "answer": {key: value for key, value in answer.items() if key != "text"},
        "selected_answer": _protocol_answer_metadata(message, answer),
        "answer_selection": {**selection, "selected": _protocol_answer_metadata(message, answer)},
        "pre_ask_marker": pre_ask_marker,
        "post_ask_marker": post_ask_marker,
        "fresh_turn_evidence": fresh_turn_evidence,
        "answer_text_length": len(str(answer.get("text") or "")),
        "automation_performed": True,
        "download_performed": False,
        "migration_performed": False,
        "adoption_performed": False,
        "operator_instruction": "Protocol ask was sent and the latest reply was parsed/validated only. No artifact download, migration, adoption, or Project Source mutation was performed.",
    }
    return result



def _normalize_protocol_ask_response_for_selected_reply(
    ask_response: dict[str, Any] | None,
    *,
    selected_answer_text: str,
    selected_answer: dict[str, Any] | None,
    validation_ok: bool,
) -> dict[str, Any] | None:
    """Keep browser-stream text diagnostic and prevent stale answer misuse.

    The service/browser ``ask_response.answer`` field may contain an
    intermediate stream value such as "Thinking ... Streaming interrupted"
    even when protocol parsing succeeds from the authoritative task transcript.
    Protocol automation must not treat that browser stream value as the final
    answer source.
    """

    if not isinstance(ask_response, dict):
        return ask_response
    normalized = copy.deepcopy(ask_response)
    raw_answer = normalized.get("answer")
    raw_answer_text = raw_answer if isinstance(raw_answer, str) else (json.dumps(raw_answer, ensure_ascii=False) if raw_answer is not None else "")
    selected_text = str(selected_answer_text or "")
    normalized["answer"] = None
    normalized["answer_source"] = "protocol_reply_authoritative" if validation_ok else "protocol_reply_candidate"
    normalized["authoritative_reply_location"] = "reply" if validation_ok else "selected_answer"
    normalized["answer_suppressed_reason"] = "browser_stream_answer_may_be_intermediate; use top-level reply and reply_validation_ok for protocol automation"
    normalized["raw_browser_answer_preview"] = raw_answer_text[:500] if raw_answer_text else ""
    normalized["raw_browser_answer_length"] = len(raw_answer_text)
    normalized["raw_browser_answer_complete"] = bool(raw_answer_text and raw_answer_text.strip() == selected_text.strip())
    normalized["selected_answer_source"] = "task_messages"
    normalized["selected_answer_text_length"] = len(selected_text)
    if isinstance(selected_answer, dict):
        normalized["selected_answer_id"] = selected_answer.get("id")
        normalized["selected_answer_index"] = selected_answer.get("index")
        normalized["selected_answer_turn_index"] = selected_answer.get("turn_index")
    return normalized

def _repo_name_from_artifact_name(filename: str) -> str | None:
    name = Path(filename).name
    if name.endswith(".zip"):
        name = name[:-4]
    match = re.search(r"_?v?\d+\.\d+\.\d+(?:\.\d+)?$", name)
    if not match:
        return None
    return name[: match.start()].rstrip("_.-") or None


async def cmd_ask(backend: CommandBackend, args: argparse.Namespace) -> int:
    try:
        prompt = _merge_prompt_text(args.prompt, getattr(args, "prompt_file", None))
    except (OSError, UnicodeError) as exc:
        print(f"error: could not read prompt file: {exc}", file=sys.stderr)
        return 2
    if not prompt:
        print("error: prompt is required", file=sys.stderr)
        return 2

    protocol_payload: dict[str, Any] | None = None
    envelope: dict[str, Any] | None = None
    if getattr(args, "protocol", False):
        protocol_payload = _protocol_request_from_current_baseline(backend, args, prompt=prompt)
        envelope = protocol_payload["request"]
        if getattr(args, "print_request_json", False):
            print(json.dumps(protocol_payload, indent=2, ensure_ascii=False))
            return 0
        prompt = render_protocol_ask_prompt(envelope, user_prompt=prompt)
    elif getattr(args, "parse_reply", False):
        print("error: --parse-reply requires --protocol", file=sys.stderr)
        return 2

    attachment_paths = _collect_ask_attachment_paths(args)
    for attachment_path in attachment_paths:
        if not Path(attachment_path).is_file():
            print(f"error: attachment file not found: {attachment_path}", file=sys.stderr)
            return 2

    legacy_single_file = args.file if args.file and not getattr(args, "attachments", None) else None
    repeatable_attachments = attachment_paths if not legacy_single_file else None

    protocol_parse = bool(getattr(args, "parse_reply", False))
    pre_ask_marker = await _capture_pre_ask_protocol_marker(backend, args) if protocol_parse else None
    try:
        response = await backend.ask(
            prompt=prompt,
            file_path=legacy_single_file,
            attachment_paths=repeatable_attachments,
            conversation_url=args.conversation_url,
            # Protocol replies are envelope text, not raw JSON. Let the ask
            # operation return first, then parse/validate deterministically.
            expect_json=False if protocol_parse else args.json,
            keep_open=args.keep_open,
            retries=args.retries,
        )
    except Exception as exc:
        if protocol_parse and envelope is not None:
            lowered = f"{exc.__class__.__name__}: {exc}".lower()
            if exc.__class__.__name__ in {"ReadTimeout", "TimeoutException"}:
                status = "service_read_timeout"
            else:
                status = "response_timeout" if "timeout" in lowered or "timed out" in lowered else "ask_failed"
            result = _protocol_failure_result(
                args,
                envelope=envelope,
                status=status,
                error=str(exc),
                error_type=exc.__class__.__name__,
                pre_ask_marker=pre_ask_marker,
            )
            if status == "service_read_timeout":
                result["timeout_layer"] = "service_client"
            elif status == "response_timeout":
                result["timeout_layer"] = "unknown_response_wait"
            return _emit_protocol_result(args, result)
        raise
    if protocol_parse:
        assert envelope is not None
        if isinstance(response, dict):
            response_failure = _protocol_ask_response_failure_result(args, envelope=envelope, ask_response=response, pre_ask_marker=pre_ask_marker)
            if response_failure is not None:
                return _emit_protocol_result(args, response_failure)
        try:
            result = await _parse_protocol_reply_after_ask(backend, args, envelope=envelope, ask_response=response, pre_ask_marker=pre_ask_marker)
        except Exception as exc:
            result = _protocol_failure_result(
                args,
                envelope=envelope,
                status="reply_parse_failed",
                error=str(exc),
                error_type=exc.__class__.__name__,
                ask_response=response if isinstance(response, dict) else {"answer": response},
                pre_ask_marker=pre_ask_marker,
            )
        return _emit_protocol_result(args, result)

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
        "task": ["list", "use", "current", "leave", "show", "messages", "message", "answer", "parse", "--latest", "--json", "--keep-open", "--deep-history", "--task"],
        "src": ["list", "add", "rm", "remove", "sync", "--type", "--value", "--file", "--name", "--no-overwrite", "--exact", "--keep-open", "--json", "--no-upload", "--output-dir", "--filename"],
        "artifact": ["current", "list", "release", "verify", "--json", "--output-dir", "--filename"],
        "agent": ["inspect", "doctor", "plan", "ask", "run", "host-smoke", "mcp-call", "tool-call", "models", "ollama-propose", "mcp-llm-smoke", "--json", "--path", "--max-files", "--model", "--skill"],
        "skill": ["list", "show", "validate", "--json", "--path"],
        "mcp": ["manifest", "serve", "config", "--json", "--path", "--include-controlled-processes", "--host", "--server-name", "--command"],
        "test": ["smoke", "browser", "agent", "full", "report", "status", "import-smoke", "--json", "--path", "--log", "--service-log", "--keep-open", "--keep-project", "--only", "--skip", "--allow-recent-state-task-fallback"],
        "doctor": ["--json"],
        "debug": ["chats", "task-list", "tasks", "--json", "--scroll-rounds", "--wait-ms", "--no-history", "--history-max-pages", "--history-max-detail-probes", "--manual-pause", "--keep-open"],
        "project-create": ["--icon", "--color", "--memory-mode", "--keep-open"],
        "project-list": ["--json", "--current", "--keep-open"],
        "project-resolve": ["--keep-open"],
        "project-ensure": ["--icon", "--color", "--memory-mode", "--keep-open"],
        "project-remove": ["--keep-open"],
        "project-source-add": ["--type", "--value", "--file", "--name", "--no-overwrite", "--keep-open"],
        "project-source-list": ["--json", "--keep-open"],
        "project-source-remove": ["--exact", "--keep-open"],
        "chat-list": ["--json", "--keep-open", "--deep-history"],
        "chats": ["--json", "--keep-open", "--deep-history"],
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
        "ask": ["--file", "--json", "--conversation-url", "--keep-open", "--retries", "--protocol", "--from-current-baseline", "--target-version", "--release-type", "--request-id", "--correlation-id", "--intent-kind", "--print-request-json", "--parse-reply", "--protocol-timeout-seconds", "--protocol-fresh-turn-timeout-seconds", "--protocol-fresh-turn-poll-seconds", "--answer-index", "--answer-id"],
        "shell": ["--file", "--json", "--keep-open", "--retries"],
        "test-suite": ["--json", "--profile", "--path", "--package-zip", "--keep-open", "--keep-project", "--only", "--skip", "--allow-recent-state-task-fallback", "--task-list-visible-timeout-seconds", "--task-list-visible-max-attempts"],
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
    _apply_test_suite_defaults(args)
    _apply_rate_limit_safe_defaults(args)
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
        'profile': getattr(args, 'profile', 'browser'),
        'path': getattr(args, 'path', '.'),
        'package_zip': getattr(args, 'package_zip', None),
        'rate_limit_safe': getattr(args, 'rate_limit_safe', None),
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
    if args.task_command == "answer":
        if args.task_answer_command == "parse":
            return await cmd_task_answer_parse(backend, args)
        raise RuntimeError(f"Unknown task answer command: {args.task_answer_command}")
    raise RuntimeError(f"Unknown task command: {args.task_command}")


def _artifact_registry_from_args(args: argparse.Namespace) -> ArtifactRegistry:
    return ArtifactRegistry(resolve_profile_dir(getattr(args, "profile_dir", None)))


def _artifact_output_dir(args: argparse.Namespace, registry: ArtifactRegistry) -> Path:
    output_dir = getattr(args, "output_dir", None)
    return Path(output_dir).expanduser() if output_dir else registry.artifact_dir


def _artifact_state_project_url(backend: Any) -> Optional[str]:
    snapshot = backend.state_snapshot()
    candidate = snapshot.get("resolved_project_home_url") if isinstance(snapshot, dict) else None
    if not isinstance(candidate, str) or candidate == DEFAULT_PROJECT_URL:
        return None
    return candidate


def _artifact_registry_snapshot(registry: ArtifactRegistry) -> dict[str, Any]:
    artifacts = registry.list()
    return {
        "path": str(registry.path),
        "exists": registry.path.exists(),
        "current": registry.current(),
        "artifact_count": len(artifacts),
        "filenames": [str(item.get("filename")) for item in artifacts if item.get("filename")],
    }


def _state_artifact_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    return {
        "project_home_url": snapshot.get("resolved_project_home_url"),
        "artifact_ref": snapshot.get("artifact_ref"),
        "artifact_version": snapshot.get("artifact_version"),
        "source_ref": snapshot.get("source_ref"),
        "source_version": snapshot.get("source_version"),
    }




def _src_sync_upload_confirm_command(repo_path: Path, transaction_id: str, *, force_required: bool = False) -> str:
    parts = [
        "pb",
        "src",
        "sync",
        str(repo_path),
        "--upload",
        "--confirm-upload",
        "--confirm-transaction-id",
        transaction_id,
    ]
    if force_required:
        parts.append("--force")
    parts.append("--json")
    return shlex.join(parts)


def _artifact_release_upload_confirm_command(repo_path: Path, transaction_id: str, *, force_required: bool = False) -> str:
    parts = [
        "pb",
        "artifact",
        "release",
        str(repo_path),
        "--sync-source",
        "--upload",
        "--confirm-upload",
        "--confirm-transaction-id",
        transaction_id,
    ]
    if force_required:
        parts.append("--force")
    parts.append("--json")
    return shlex.join(parts)


def _artifact_release_status_from_source_sync(status: str | None) -> str:
    if status in {"planned", "upload_confirmation_required", "sync_mode_required"}:
        return "planned"
    if status == "verified_packaged":
        return "packaged"
    if status == "uploaded":
        return "uploaded"
    if status == "upload_ambiguous":
        return "upload_ambiguous"
    return "failed"


def _redact_source_sync_payload_for_artifact_release(payload: dict[str, Any]) -> dict[str, Any]:
    """Return diagnostic src_sync payload without executable delegated confirm commands.

    The artifact-release workflow intentionally exposes only one executable
    confirmation command at the top level: ``confirmation.confirm_command``.
    Nested src_sync details are retained for diagnostics, but their delegated
    confirmation commands are redacted to avoid operator confusion.
    """

    redacted = copy.deepcopy(payload)
    confirmation = redacted.get("confirmation")
    if isinstance(confirmation, dict):
        if confirmation.get("confirm_command"):
            confirmation.pop("confirm_command", None)
            confirmation["confirm_command_redacted"] = True
            confirmation["confirm_command_redacted_reason"] = "use top-level artifact_release confirmation.confirm_command exactly"
        confirmation.pop("source_sync_confirm_command", None)
    return redacted


def _rewrite_source_sync_payload_for_artifact_release(payload: dict[str, Any], *, repo_path: Path) -> dict[str, Any]:
    source_status = str(payload.get("status") or "")
    release_status = _artifact_release_status_from_source_sync(source_status)
    source_sync_diagnostics = _redact_source_sync_payload_for_artifact_release(payload)
    rewritten = {
        **payload,
        "action": "artifact_release",
        "status": release_status,
        "release_workflow": "artifact_release_source_sync_v1",
        "source_sync_status": source_status,
        "source_sync_action": payload.get("action"),
        "status_vocabulary": ["planned", "packaged", "uploaded", "upload_ambiguous", "failed"],
        "operator_instruction": "Run confirmation.confirm_command exactly; nested source_sync payload is diagnostic only.",
        "source_sync": source_sync_diagnostics,
    }
    confirmation = payload.get("confirmation")
    if isinstance(confirmation, dict) and payload.get("transaction_id"):
        force_required = bool((confirmation.get("force_required") is True) or ("--force" in str(confirmation.get("confirm_command") or "")))
        rewritten["confirmation"] = {
            **confirmation,
            "confirm_command": _artifact_release_upload_confirm_command(
                repo_path,
                str(payload.get("transaction_id")),
                force_required=force_required,
            ),
            "operator_instruction": "Run this top-level artifact release confirm command exactly.",
        }
        rewritten["confirmation"].pop("source_sync_confirm_command", None)
    next_commands = payload.get("next_commands")
    if isinstance(next_commands, dict):
        rewritten["next_commands"] = {
            **next_commands,
            "artifact_local_package": f"pb artifact release {shlex.quote(str(repo_path))} --sync-source --no-upload --json",
            "artifact_upload_preflight": f"pb artifact release {shlex.quote(str(repo_path))} --sync-source --upload --json",
        }
    return rewritten

def _registry_contains_artifact(registry: ArtifactRegistry, *, path: str, filename: str, sha256: str) -> bool:
    for item in registry.list():
        if not isinstance(item, dict):
            continue
        if str(item.get("path") or "") == path and str(item.get("filename") or "") == filename and str(item.get("sha256") or "") == sha256:
            return True
    return False


def _local_source_sync_verification(
    *,
    record: Any,
    registry: ArtifactRegistry,
    before_registry: dict[str, Any],
    before_state: dict[str, Any],
    after_state: dict[str, Any],
    project_url: Optional[str],
) -> dict[str, Any]:
    zip_check = verify_zip_artifact(record.path)
    after_registry = _artifact_registry_snapshot(registry)
    state_before = _state_artifact_summary(before_state)
    state_after = _state_artifact_summary(after_state)
    registry_contains = _registry_contains_artifact(
        registry,
        path=record.path,
        filename=record.filename,
        sha256=record.sha256,
    )
    state_artifact_updated = True
    if project_url:
        state_artifact_updated = (
            state_after.get("artifact_ref") == record.filename
            and state_after.get("artifact_version") == record.version
        )
    checks = {
        "zip_exists": Path(record.path).is_file(),
        "zip_crc_ok": bool(zip_check.get("ok")) and zip_check.get("testzip") is None,
        "zip_sha256_matches_record": bool(Path(record.path).is_file()) and verify_zip_artifact(record.path).get("sha256") == record.sha256,
        "registry_contains_artifact": registry_contains,
        "registry_current_matches_artifact": bool(after_registry.get("current")) and str((after_registry.get("current") or {}).get("filename") or "") == record.filename,
        "state_artifact_updated": state_artifact_updated,
        "project_source_not_mutated": True,
        "project_source_mutated": False,
    }
    required_checks = {key: value for key, value in checks.items() if key != "project_source_mutated"}
    ok = all(bool(value) for value in required_checks.values())
    return {
        "ok": ok,
        "status": "verified" if ok else "verification_failed",
        "scope": "local_artifact_only",
        "checks": checks,
        "zip": zip_check,
        "before_snapshot": {
            "artifact_registry": before_registry,
            "state": state_before,
        },
        "after_snapshot": {
            "artifact_registry": after_registry,
            "state": state_after,
        },
    }



def _source_identity_values(source: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    if not isinstance(source, dict):
        return values
    for key in (
        "title",
        "name",
        "filename",
        "display_name",
        "source_ref",
        "id",
        "identity",
        "text",
        "label",
    ):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            values.add(value.strip())
    return values


def _source_stable_key(source: dict[str, Any]) -> str:
    if not isinstance(source, dict):
        return ""
    for key in ("id", "source_id", "source_ref", "title", "name", "filename", "display_name", "identity", "text"):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return json.dumps(source, sort_keys=True, ensure_ascii=False)


def _source_matches_filename(source: dict[str, Any], filename: str) -> bool:
    target = str(filename or "").strip()
    if not target:
        return False
    target_lower = target.lower()
    for value in _source_identity_values(source):
        value_lower = value.lower()
        if value_lower == target_lower:
            return True
        # Source cards sometimes render a filename plus type/subtitle in one text
        # blob. Allow substring matching for the exact filename, but not for an
        # empty or generic token.
        if target_lower in value_lower:
            return True
    return False



def _operation_error_payload(operation: str, exc: Exception) -> dict[str, Any]:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    response_text = None
    if response is not None:
        try:
            response_text = getattr(response, "text", None)
        except Exception:
            response_text = None
    payload: dict[str, Any] = {
        "ok": False,
        "action": operation,
        "status": "service_error",
        "exception_type": type(exc).__name__,
        "error": str(exc),
    }
    if status_code is not None:
        payload["http_status_code"] = status_code
    if response_text:
        payload["response_text"] = str(response_text)[:2000]
    return payload

def _project_sources_snapshot_from_result(result: Any) -> dict[str, Any]:
    sources, payload = _project_source_list_payload(result)
    return {
        "ok": bool(payload.get("ok")),
        "status": payload.get("status"),
        "count": len(sources),
        "sources": sources,
        "source_keys": [_source_stable_key(item) for item in sources],
        "raw": payload,
    }


def _verify_project_source_upload_change(
    *,
    before_result: Any,
    after_result: Any,
    upload_result: Any,
    expected_filename: str,
) -> dict[str, Any]:
    before = _project_sources_snapshot_from_result(before_result)
    after = _project_sources_snapshot_from_result(after_result)
    before_sources = before.get("sources") if isinstance(before.get("sources"), list) else []
    after_sources = after.get("sources") if isinstance(after.get("sources"), list) else []
    before_keys = {key for key in before.get("source_keys", []) if isinstance(key, str) and key}
    after_keys = {key for key in after.get("source_keys", []) if isinstance(key, str) and key}

    matched_before = [item for item in before_sources if isinstance(item, dict) and _source_matches_filename(item, expected_filename)]
    matched_after = [item for item in after_sources if isinstance(item, dict) and _source_matches_filename(item, expected_filename)]
    removed_keys = sorted(before_keys - after_keys)
    added_keys = sorted(after_keys - before_keys)

    upload_ok = bool(isinstance(upload_result, dict) and upload_result.get("ok"))
    checks = {
        "upload_result_ok": upload_ok,
        "before_source_list_ok": bool(before.get("ok")),
        "after_source_list_ok": bool(after.get("ok")),
        "expected_source_present_after": bool(matched_after),
        "collateral_sources_removed": bool(removed_keys),
    }
    ok = (
        checks["upload_result_ok"]
        and checks["before_source_list_ok"]
        and checks["after_source_list_ok"]
        and checks["expected_source_present_after"]
        and not checks["collateral_sources_removed"]
    )
    ambiguous = (
        not checks["upload_result_ok"]
        and checks["before_source_list_ok"]
        and checks["after_source_list_ok"]
        and checks["expected_source_present_after"]
        and not checks["collateral_sources_removed"]
    )
    status = "verified" if ok else ("upload_ambiguous" if ambiguous else "source_upload_not_verified")
    ambiguity_reason = "upload_result_failed_but_expected_source_present_after" if ambiguous else None
    return {
        "ok": ok,
        "status": status,
        "expected_filename": expected_filename,
        "checks": checks,
        "operator_review_required": bool(ambiguous),
        "ambiguity_reason": ambiguity_reason,
        "before_snapshot": {
            "ok": before.get("ok"),
            "status": before.get("status"),
            "count": before.get("count"),
            "matching_expected_count": len(matched_before),
            "source_keys": before.get("source_keys"),
        },
        "after_snapshot": {
            "ok": after.get("ok"),
            "status": after.get("status"),
            "count": after.get("count"),
            "matching_expected_count": len(matched_after),
            "source_keys": after.get("source_keys"),
        },
        "matched_after": matched_after[:3],
        "added_source_keys": added_keys,
        "removed_source_keys": removed_keys,
        "collateral_change_detected": bool(removed_keys),
        "upload_result_status": upload_result.get("status") if isinstance(upload_result, dict) else None,
    }


async def cmd_src_sync(backend: Any, args: argparse.Namespace) -> int:
    """Package a repo snapshot and optionally upload it as a project source."""
    registry = _artifact_registry_from_args(args)
    repo_path = Path(args.path).expanduser().resolve()
    project_url = _artifact_state_project_url(backend)

    no_upload_requested = bool(getattr(args, "no_upload", False))
    upload_requested = bool(getattr(args, "upload", False) or getattr(args, "confirm_upload", False))
    confirm_upload = bool(getattr(args, "confirm_upload", False))
    confirm_transaction_id = str(getattr(args, "confirm_transaction_id", None) or "").strip()

    if no_upload_requested and upload_requested:
        payload = {
            "ok": False,
            "action": "src_sync",
            "status": "conflicting_sync_modes",
            "dry_run": bool(getattr(args, "dry_run", False)),
            "no_upload": no_upload_requested,
            "upload_requested": upload_requested,
            "confirm_upload": confirm_upload,
            "mutating_actions_executed": False,
            "project_source_mutated": False,
            "repo_path": str(repo_path),
            "error": "choose either --no-upload or --upload/--confirm-upload, not both",
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 2

    if getattr(args, "dry_run", False):
        output_dir = _artifact_output_dir(args, registry)
        try:
            plan, included = build_source_sync_preflight(
                repo_path,
                output_dir=output_dir,
                filename=getattr(args, "filename", None),
                profile_dir=registry.profile_dir,
                project_url=project_url,
                upload_requested=upload_requested,
            )
        except ValueError as exc:
            print(json.dumps({"ok": False, "action": "src_sync", "status": "plan_failed", "error": str(exc)}, indent=2, ensure_ascii=False))
            return 2
        prechecks = plan["preflight"]["preflight"]
        transaction_plan = {
            "transaction_id": plan["preflight"]["transaction_id"],
            "would_package_repo_snapshot": True,
            "would_update_artifact_registry": True,
            "would_upload_project_source": bool(upload_requested),
            "would_update_promptbranch_artifact_state": bool(project_url),
            "required_settle_conditions": plan["preflight"]["verification_plan"].get("commit_wait", []),
            "verification_plan": plan["preflight"]["verification_plan"],
            "collateral_checks": plan["preflight"]["collateral_checks"],
        }
        warnings: list[str] = []
        if upload_requested and not project_url:
            warnings.append("no current workspace is selected; live upload would fail unless you run `pb ws use <project>` first")
        artifact_plan = {**plan, "would_upload_source": bool(upload_requested)}
        payload = {
            "ok": True,
            "action": "src_sync",
            "status": "planned",
            "dry_run": True,
            "mutating_actions_executed": False,
            "repo_path": str(repo_path),
            "project_url": project_url,
            "artifact": artifact_plan,
            "included_count": len(included),
            "prechecks": prechecks,
            "before_snapshot": plan["preflight"]["before_snapshot"],
            "collateral_checks": plan["preflight"]["collateral_checks"],
            "transaction_id": plan["preflight"]["transaction_id"],
            "transaction_plan": transaction_plan,
            "warnings": warnings,
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"status={payload['status']}")
            print(f"artifact={artifact_plan['path']}")
            print(f"file_count={artifact_plan['file_count']}")
            if warnings:
                print(f"warning={warnings[0]}")
        return 0

    output_dir = _artifact_output_dir(args, registry)
    try:
        preflight_plan, planned_included = build_source_sync_preflight(
            repo_path,
            output_dir=output_dir,
            filename=getattr(args, "filename", None),
            profile_dir=registry.profile_dir,
            project_url=project_url,
            upload_requested=upload_requested,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "action": "src_sync", "status": "preflight_failed", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 2

    collateral = preflight_plan["preflight"]["collateral_checks"]
    collision_keys = ("output_path_exists", "registry_path_collision", "registry_filename_collision")
    collisions = {key: collateral.get(key) for key in collision_keys if collateral.get(key)}
    upload_force_required = bool(upload_requested and collisions)

    if not no_upload_requested and not upload_requested:
        payload = {
            "ok": False,
            "action": "src_sync",
            "status": "sync_mode_required",
            "dry_run": False,
            "no_upload": False,
            "upload_requested": False,
            "confirm_upload": False,
            "mutating_actions_executed": False,
            "project_source_mutated": False,
            "repo_path": str(repo_path),
            "project_url": project_url,
            "artifact": {**preflight_plan, "would_upload_source": False},
            "included_count": len(planned_included),
            "preflight": preflight_plan["preflight"],
            "error": "explicit sync mode required; use --no-upload for local packaging or --upload for upload preflight",
            "next_commands": {
                "local_package": f"pb src sync {repo_path} --no-upload --json",
                "upload_preflight": f"pb src sync {repo_path} --upload --json",
            },
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 2

    if upload_requested and not confirm_upload:
        warnings: list[str] = []
        if not project_url:
            warnings.append("no current workspace is selected; confirmed upload would fail unless you run `pb ws use <project>` first")
        if upload_force_required:
            warnings.append("local artifact collision detected; confirmation command includes --force to overwrite/re-register the local package before upload")
        payload = {
            "ok": False,
            "action": "src_sync",
            "status": "upload_confirmation_required",
            "dry_run": False,
            "no_upload": False,
            "upload_requested": True,
            "confirm_upload": False,
            "mutating_actions_executed": False,
            "project_source_mutated": False,
            "repo_path": str(repo_path),
            "project_url": project_url,
            "artifact": {**preflight_plan, "would_upload_source": True},
            "included_count": len(planned_included),
            "preflight": preflight_plan["preflight"],
            "transaction_id": preflight_plan["preflight"]["transaction_id"],
            "confirmation": {
                "required": True,
                "reason": "live ChatGPT project source upload is mutating and requires explicit confirmation",
                "confirm_flag": "--confirm-upload",
                "confirm_transaction_id_flag": "--confirm-transaction-id",
                "transaction_id": preflight_plan["preflight"]["transaction_id"],
                "force_required": upload_force_required,
                "force_reason": "local artifact collision must be intentionally overwritten before upload" if upload_force_required else None,
                "confirm_command": _src_sync_upload_confirm_command(
                    repo_path,
                    preflight_plan["preflight"]["transaction_id"],
                    force_required=upload_force_required,
                ),
            },
            "warnings": warnings,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 2

    if upload_requested and confirm_upload:
        expected_transaction_id = str(preflight_plan["preflight"].get("transaction_id") or "")
        if not confirm_transaction_id:
            payload = {
                "ok": False,
                "action": "src_sync",
                "status": "upload_transaction_id_required",
                "dry_run": False,
                "no_upload": False,
                "upload_requested": True,
                "confirm_upload": True,
                "mutating_actions_executed": False,
                "project_source_mutated": False,
                "repo_path": str(repo_path),
                "project_url": project_url,
                "artifact": {**preflight_plan, "would_upload_source": True},
                "included_count": len(planned_included),
                "preflight": preflight_plan["preflight"],
                "transaction_id": expected_transaction_id,
                "confirmation": {
                    "required": True,
                    "reason": "confirmed upload requires the transaction id from a reviewed upload preflight",
                    "confirm_flag": "--confirm-upload",
                    "confirm_transaction_id_flag": "--confirm-transaction-id",
                    "force_required": upload_force_required,
                    "force_reason": "local artifact collision must be intentionally overwritten before upload" if upload_force_required else None,
                    "confirm_command": _src_sync_upload_confirm_command(repo_path, expected_transaction_id, force_required=upload_force_required),
                },
                "error": "confirmed upload requires --confirm-transaction-id from the upload preflight",
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 2
        if confirm_transaction_id != expected_transaction_id:
            payload = {
                "ok": False,
                "action": "src_sync",
                "status": "upload_transaction_id_mismatch",
                "dry_run": False,
                "no_upload": False,
                "upload_requested": True,
                "confirm_upload": True,
                "mutating_actions_executed": False,
                "project_source_mutated": False,
                "repo_path": str(repo_path),
                "project_url": project_url,
                "artifact": {**preflight_plan, "would_upload_source": True},
                "included_count": len(planned_included),
                "preflight": preflight_plan["preflight"],
                "transaction_id": expected_transaction_id,
                "provided_transaction_id": confirm_transaction_id,
                "error": "confirmed upload transaction id does not match current preflight",
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 2

    if collisions and not getattr(args, "force", False):
        payload = {
            "ok": False,
            "action": "src_sync",
            "status": "local_artifact_collision",
            "dry_run": False,
            "no_upload": bool(getattr(args, "no_upload", False)),
            "mutating_actions_executed": False,
            "repo_path": str(repo_path),
            "project_url": project_url,
            "artifact": {**preflight_plan, "would_upload_source": bool(upload_requested)},
            "included_count": len(planned_included),
            "preflight": preflight_plan["preflight"],
            "collisions": collisions,
            "confirmation": ({
                "required": True,
                "reason": "confirmed upload also requires explicit --force because the local artifact path or registry entry already exists",
                "confirm_flag": "--confirm-upload",
                "confirm_transaction_id_flag": "--confirm-transaction-id",
                "transaction_id": preflight_plan["preflight"]["transaction_id"],
                "force_required": True,
                "force_flag": "--force",
                "confirm_command": _src_sync_upload_confirm_command(
                    repo_path,
                    preflight_plan["preflight"]["transaction_id"],
                    force_required=True,
                ),
            } if upload_requested else None),
            "error": "local artifact collision detected; rerun with --force to overwrite/register this artifact",
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 2

    if upload_requested and not project_url:
        payload = {
            "ok": False,
            "action": "src_sync",
            "status": "no_workspace_selected",
            "dry_run": False,
            "no_upload": False,
            "mutating_actions_executed": False,
            "repo_path": str(repo_path),
            "project_url": project_url,
            "artifact": {**preflight_plan, "would_upload_source": True},
            "included_count": len(planned_included),
            "preflight": preflight_plan["preflight"],
            "error": "no current workspace is selected; run `pb ws use <project>` or pass --no-upload",
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 2

    before_registry = _artifact_registry_snapshot(registry)
    before_state = backend.state_snapshot()

    try:
        record, included = create_repo_snapshot(
            repo_path,
            output_dir=output_dir,
            filename=getattr(args, "filename", None),
            kind=getattr(args, "artifact_kind", "source_snapshot"),
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "action": "src_sync", "status": "package_failed", "error": str(exc), "preflight": preflight_plan["preflight"]}, indent=2, ensure_ascii=False))
        return 2

    upload_result: dict[str, Any] | None = None
    upload_source_before_result: Any = None
    upload_source_after_result: Any = None
    source_upload_verification: dict[str, Any] | None = None
    uploaded = False
    if upload_requested:
        if not project_url:
            payload = {
                "ok": False,
                "action": "src_sync",
                "status": "no_workspace_selected",
                "artifact": record.to_dict(),
                "included_count": len(included),
                "preflight": preflight_plan["preflight"],
                "error": "no current workspace is selected; run `pb ws use <project>` or pass --no-upload",
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 2
        try:
            upload_source_before_result = await backend.list_project_sources(keep_open=args.keep_open)
        except Exception as exc:
            upload_source_before_result = _operation_error_payload("source_list_before_upload", exc)

        before_sources_snapshot = _project_sources_snapshot_from_result(upload_source_before_result)
        if not before_sources_snapshot.get("ok"):
            upload_result = {
                "ok": False,
                "action": "source_add",
                "status": "before_source_list_unavailable",
                "error": "project source list before upload was not readable; upload was not attempted",
            }
            upload_source_after_result = upload_source_before_result
        else:
            try:
                upload_result = await backend.add_project_source(
                    source_kind="file",
                    file_path=record.path,
                    display_name=record.filename,
                    keep_open=args.keep_open,
                )
            except Exception as exc:
                upload_result = _operation_error_payload("source_add", exc)
            try:
                upload_source_after_result = await backend.list_project_sources(keep_open=args.keep_open)
            except Exception as exc:
                upload_source_after_result = _operation_error_payload("source_list_after_upload", exc)

        source_upload_verification = _verify_project_source_upload_change(
            before_result=upload_source_before_result,
            after_result=upload_source_after_result,
            upload_result=upload_result,
            expected_filename=record.filename,
        )
        uploaded = bool(source_upload_verification.get("ok"))

    # Transaction rule: a live upload may write the local ZIP before the UI/API
    # trigger, but the artifact registry and Promptbranch artifact/source state
    # must not be advanced unless the project source upload verifies. Otherwise a
    # failed ChatGPT source mutation would leave local state falsely claiming the
    # new source is current. The no-upload path is intentionally local-only and
    # remains verified via _local_source_sync_verification below.
    artifact_payload: dict[str, Any] = record.to_dict()
    registry_updated = False
    state_artifact_updated = False
    state_source_updated = False
    store = _state_store_from_args(args)
    if no_upload_requested or uploaded:
        artifact_payload = registry.add(record)
        registry_updated = True
        if project_url:
            if uploaded:
                store.remember_artifact(
                    project_url=project_url,
                    artifact_ref=record.filename,
                    artifact_version=record.version,
                    source_ref=record.filename,
                    source_version=record.version,
                )
                state_artifact_updated = True
                state_source_updated = True
            else:
                store.remember_artifact(
                    project_url=project_url,
                    artifact_ref=record.filename,
                    artifact_version=record.version,
                )
                state_artifact_updated = True
    after_state = backend.state_snapshot()
    local_verification = _local_source_sync_verification(
        record=record,
        registry=registry,
        before_registry=before_registry,
        before_state=before_state,
        after_state=after_state,
        project_url=project_url,
    )
    no_upload = no_upload_requested
    upload_ambiguous = bool(
        upload_requested
        and isinstance(source_upload_verification, dict)
        and source_upload_verification.get("status") == "upload_ambiguous"
    )
    upload_status = (
        "verified_packaged"
        if no_upload and local_verification.get("ok")
        else ("uploaded" if uploaded else ("packaged_unverified" if no_upload else ("upload_ambiguous" if upload_ambiguous else "upload_failed")))
    )
    project_source_mutation = "verified" if uploaded else ("ambiguous" if upload_ambiguous else ("not_requested" if not upload_requested else "not_verified"))
    payload = {
        "ok": bool((no_upload and local_verification.get("ok")) or uploaded),
        "action": "src_sync",
        "status": upload_status,
        "dry_run": False,
        "no_upload": no_upload,
        "upload_requested": upload_requested,
        "confirm_upload": confirm_upload,
        "mutating_actions_executed": True,
        "project_source_mutated": bool(uploaded),
        "project_source_mutation": project_source_mutation,
        "operator_review_required": bool(upload_ambiguous),
        "local_artifact_written": True,
        "artifact_registry_updated": registry_updated,
        "state_artifact_updated": state_artifact_updated,
        "state_source_updated": state_source_updated,
        "artifact": artifact_payload,
        "included_count": len(included),
        "preflight": preflight_plan["preflight"],
        "transaction_id": preflight_plan["preflight"]["transaction_id"],
        "local_verification": local_verification,
        "upload_verification": {
            "ok": bool(uploaded),
            "status": "verified" if uploaded else ("not_requested" if not upload_requested else ("upload_ambiguous" if upload_ambiguous else "upload_not_verified")),
            "project_source_mutated": bool(uploaded),
            "project_source_mutation": project_source_mutation,
            "operator_review_required": bool(upload_ambiguous),
            "artifact_registry_updated_after_upload": registry_updated if upload_requested else False,
            "state_source_updated_after_upload": state_source_updated if upload_requested else False,
            "registry_update_deferred_until_upload_verified": bool(upload_requested and not uploaded),
            "source_list_verification": source_upload_verification,
        },
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


def _artifact_version_from_filename(filename: str) -> str | None:
    value = Path(str(filename or "")).name
    match = re.search(r"_(v?\d+\.\d+\.\d+(?:\.\d+)?)\.zip$", value)
    if not match:
        return None
    version = match.group(1)
    return version if valid_version_text(version) else None


def _read_zip_version_file(path: str | Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as archive:
            if "VERSION" not in archive.namelist():
                return None
            value = archive.read("VERSION").decode("utf-8", errors="replace").strip()
    except (OSError, zipfile.BadZipFile, KeyError):
        return None
    return value if valid_version_text(value) else None


def _resolve_adopt_local_zip(artifact_name: str, *, local_path: str | None, registry: ArtifactRegistry) -> Path | None:
    candidates: list[Path] = []
    if local_path:
        candidates.append(Path(local_path).expanduser())
    raw = Path(artifact_name).expanduser()
    candidates.append(raw)
    if not raw.is_absolute():
        candidates.append(Path.cwd() / raw)
        candidates.append(registry.artifact_dir / raw.name)
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate.absolute()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def _project_sources_matching_filename(result: Any, filename: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sources, payload = _project_source_list_payload(result)
    matched = [item for item in sources if isinstance(item, dict) and _source_matches_filename(item, filename)]
    payload["matching_expected_count"] = len(matched)
    payload["matching_expected"] = matched[:5]
    return matched, payload


def _artifact_current_payload(backend: Any, registry: ArtifactRegistry) -> dict[str, Any]:
    snapshot = backend.state_snapshot()
    state = {
        "artifact_ref": snapshot.get("artifact_ref"),
        "artifact_version": snapshot.get("artifact_version"),
        "source_ref": snapshot.get("source_ref"),
        "source_version": snapshot.get("source_version"),
        "project_home_url": snapshot.get("resolved_project_home_url"),
    }
    registry_current = registry.current()
    registry_filename = str((registry_current or {}).get("filename") or "") if registry_current else ""
    registry_version = str((registry_current or {}).get("version") or "") if registry_current else ""
    state_artifact_ref = str(state.get("artifact_ref") or "")
    state_artifact_version = str(state.get("artifact_version") or "")
    state_source_ref = str(state.get("source_ref") or "")
    state_source_version = str(state.get("source_version") or "")
    runtime_version = f"v{CLI_VERSION}" if not str(CLI_VERSION).startswith("v") else str(CLI_VERSION)
    registry_matches_state = bool(registry_current) and registry_filename == state_artifact_ref and registry_version == state_artifact_version
    state_source_matches_artifact = bool(state_artifact_ref or state_source_ref) and state_artifact_ref == state_source_ref and state_artifact_version == state_source_version
    code_matches_adopted_source = runtime_version == state_source_version
    return {
        "ok": True,
        "action": "artifact_current",
        "runtime": {
            "package_version": CLI_VERSION,
            "version": runtime_version,
        },
        "state": state,
        "registry_current": registry_current,
        "baseline_roles": {
            "runtime_code_version": runtime_version,
            "adopted_artifact_ref": state_artifact_ref or None,
            "adopted_artifact_version": state_artifact_version or None,
            "adopted_source_ref": state_source_ref or None,
            "adopted_source_version": state_source_version or None,
            "registry_current_ref": registry_filename or None,
            "registry_current_version": registry_version or None,
            "registry_current_kind": (registry_current or {}).get("kind") if registry_current else None,
            "code_matches_adopted_source": code_matches_adopted_source,
            "note": "runtime code release may intentionally differ from the adopted Project Source baseline",
        },
        "consistency": {
            "registry_current_matches_state_artifact": registry_matches_state,
            "state_source_matches_state_artifact": state_source_matches_artifact,
            "code_version_matches_state_source": code_matches_adopted_source,
            "project_home_url_present": bool(state.get("project_home_url")),
        },
        "registry_file": str(registry.path),
    }


async def cmd_artifact_current(backend: Any, args: argparse.Namespace) -> int:
    registry = _artifact_registry_from_args(args)
    payload = _artifact_current_payload(backend, registry)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        state = payload["state"]
        print(f"artifact_ref={state.get('artifact_ref') or 'none'}")
        print(f"artifact_version={state.get('artifact_version') or 'none'}")
        current = payload.get("registry_current") or {}
        print(f"registry_current={current.get('filename') or 'none'}")
        roles = payload.get("baseline_roles") or {}
        print(f"runtime_code_version={roles.get('runtime_code_version') or 'none'}")
        print(f"code_matches_adopted_source={roles.get('code_matches_adopted_source')}")
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



async def cmd_artifact_accept_candidate(backend: Any, args: argparse.Namespace) -> int:
    """Guardedly run tests/adoption for a migrated candidate_release artifact."""

    registry = _artifact_registry_from_args(args)
    profile_root = resolve_profile_dir(getattr(args, "profile_dir", None))
    repo_root = Path(getattr(args, "repo_path", ".") or ".").expanduser().resolve()
    project_url = _artifact_state_project_url(backend)
    artifact_arg = getattr(args, "artifact", None)
    version_arg = getattr(args, "version", None)
    registry_path, candidate, selection = _select_artifact_candidate_record(profile_root, artifact=artifact_arg, version=version_arg)

    base_payload: dict[str, Any] = {
        "ok": False,
        "action": "artifact_accept_candidate",
        "status": selection.get("status"),
        "project_url": project_url,
        "repo_path": str(repo_root),
        "candidate_registry_path": str(registry_path),
        "candidate_selection": selection,
        "project_source_mutated": False,
        "download_performed": False,
        "migration_performed": False,
        "adoption_performed": False,
    }

    def emit(payload: dict[str, Any], code: int) -> int:
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"status={payload.get('status')}")
            print(f"ok={str(bool(payload.get('ok'))).lower()}")
            if payload.get("error"):
                print(f"error={payload.get('error')}")
            if payload.get("artifact_ref"):
                print(f"artifact_ref={payload.get('artifact_ref')}")
        return code

    if candidate is None:
        return emit({**base_payload, "error": "candidate_release not found or ambiguous; pass --artifact or --version to select exactly one candidate"}, 1)

    filename = _safe_artifact_filename(candidate.get("filename") or Path(str(candidate.get("path") or "")).name)
    if not filename:
        return emit({**base_payload, "status": "artifact_wrong_filename", "candidate": candidate, "error": "candidate filename must be a basename ending in .zip"}, 1)
    candidate_version = _candidate_version_normalized(candidate.get("version") or candidate.get("zip_version") or candidate.get("filename_version") or _artifact_version_from_filename(filename))
    if not candidate_version:
        return emit({**base_payload, "status": "artifact_wrong_version", "candidate": candidate, "artifact_ref": filename, "error": "candidate version is missing or invalid"}, 1)

    candidate_path_value = str(candidate.get("path") or "")
    candidate_path = Path(candidate_path_value).expanduser().resolve() if candidate_path_value else (repo_root / filename).resolve()
    payload = {
        **base_payload,
        "status": "candidate_selected",
        "candidate": candidate,
        "artifact_ref": filename,
        "artifact_version": candidate_version,
        "candidate_path": str(candidate_path),
    }

    if candidate.get("kind") != "candidate_release" or candidate.get("status") not in {"candidate_release", "migrated_candidate", "accepted_candidate"}:
        return emit({**payload, "ok": False, "status": "candidate_not_release", "error": "selected record is not a candidate_release"}, 1)
    if candidate.get("verified") is not True:
        return emit({**payload, "ok": False, "status": "candidate_not_verified", "error": "candidate must be verified before acceptance"}, 1)
    if not candidate_path.is_file():
        return emit({**payload, "ok": False, "status": "candidate_zip_missing", "error": "candidate ZIP does not exist at the registered path"}, 1)
    if candidate_path.parent != repo_root:
        return emit({**payload, "ok": False, "status": "candidate_not_repo_root", "error": "candidate ZIP must be migrated directly under the selected repo root before acceptance"}, 1)

    metadata = _artifact_file_metadata(candidate_path)
    expected_sha = str(candidate.get("sha256") or "")
    if expected_sha and metadata.get("sha256") != expected_sha:
        return emit({**payload, "ok": False, "status": "candidate_sha_mismatch", "file": metadata, "error": "candidate ZIP sha256 differs from candidate registry metadata"}, 1)

    zip_check = verify_zip_artifact(candidate_path)
    zip_version = _read_zip_version_file(candidate_path)
    if not bool(zip_check.get("ok")):
        return emit({**payload, "ok": False, "status": "candidate_zip_invalid", "zip": zip_check, "error": "candidate ZIP failed verification"}, 1)
    if zip_version != candidate_version:
        return emit({**payload, "ok": False, "status": "candidate_version_mismatch", "zip": zip_check, "zip_version": zip_version, "error": "candidate ZIP VERSION does not match candidate version"}, 1)

    if not getattr(args, "from_project_source", False):
        return emit({**payload, "ok": False, "status": "project_source_verification_required", "zip": zip_check, "error": "accept-candidate requires --from-project-source so local state advances only after Project Source verification"}, 2)
    if not project_url:
        return emit({**payload, "ok": False, "status": "workspace_not_selected", "zip": zip_check, "error": "select a workspace before accepting a candidate"}, 2)

    source_result = await backend.list_project_sources(keep_open=getattr(args, "keep_open", False))
    matched_sources, source_payload = _project_sources_matching_filename(source_result, filename)
    if not bool(source_payload.get("ok")):
        return emit({**payload, "ok": False, "status": "source_list_unavailable", "zip": zip_check, "source_list": source_payload, "error": "could not verify Project Sources"}, 1)
    if len(matched_sources) != 1:
        return emit({**payload, "ok": False, "status": "project_source_match_count_invalid", "zip": zip_check, "source_list": source_payload, "matching_expected_count": len(matched_sources), "error": f"expected exactly one matching Project Source named {filename}, found {len(matched_sources)}"}, 1)

    preflight = {
        **payload,
        "ok": True,
        "status": "candidate_acceptance_preflight_verified",
        "candidate_file": metadata,
        "zip": zip_check,
        "source_verified": True,
        "source_list": source_payload,
        "matched_source": matched_sources[0],
        "checks": {
            "candidate_record_selected": True,
            "candidate_verified": True,
            "candidate_zip_exists": True,
            "candidate_sha_matches_registry": not expected_sha or metadata.get("sha256") == expected_sha,
            "zip_verified": bool(zip_check.get("ok")),
            "zip_version_matches_candidate": zip_version == candidate_version,
            "source_verified": len(matched_sources) == 1,
            "project_source_mutated": False,
        },
    }

    if not getattr(args, "adopt_if_green", False):
        return emit({**preflight, "operator_instruction": "Candidate acceptance preflight verified. Re-run with --run-release-control --adopt-if-green to run guarded tests and adoption."}, 0)
    if not getattr(args, "run_release_control", False):
        return emit({**preflight, "ok": False, "status": "candidate_acceptance_runner_required", "error": "--adopt-if-green requires --run-release-control for guarded test/adopt execution"}, 2)

    release_control_script = repo_root / "chatgpt_claudecode_workflow_release_control.sh"
    if not release_control_script.is_file():
        return emit({**preflight, "ok": False, "status": "release_control_missing", "error": f"release-control script not found: {release_control_script}"}, 1)
    if not os.access(release_control_script, os.X_OK):
        return emit({**preflight, "ok": False, "status": "release_control_not_executable", "error": f"release-control script is not executable: {release_control_script}"}, 1)

    command = _release_control_command_for_candidate(
        repo_root,
        version=candidate_version,
        release_log_keep=int(getattr(args, "release_log_keep", 12) or 12),
        skip_docker_logs=bool(getattr(args, "skip_docker_logs", True)),
        prune_release_logs=bool(getattr(args, "prune_release_logs", True)),
    )
    runner = _run_release_control_candidate_acceptance(command, repo_root=repo_root, timeout_seconds=float(getattr(args, "test_timeout", 3600.0) or 3600.0))
    if not runner.get("ok"):
        return emit({**preflight, "ok": False, "status": runner.get("status") or "candidate_acceptance_command_failed", "release_control": runner, "adoption_performed": False, "error": "release-control tests/adoption did not complete green"}, 1)

    current_payload = _artifact_current_payload(backend, registry)
    current_ok, current_checks = _report_artifact_current_matches_candidate(current_payload, filename=filename, version=candidate_version)
    if not current_ok:
        return emit({**preflight, "ok": False, "status": "artifact_current_mismatch", "release_control": runner, "artifact_current": current_payload, "current_checks": current_checks, "adoption_performed": True, "error": "release-control returned success, but artifact current does not match the accepted candidate"}, 1)

    candidate_registry_path, accepted_record = _mark_artifact_candidate_accepted(profile_root, candidate=candidate, current_payload=current_payload)
    result = {
        **preflight,
        "ok": True,
        "status": "accepted_candidate",
        "release_control": runner,
        "artifact_current": current_payload,
        "current_checks": current_checks,
        "candidate_registry_path": str(candidate_registry_path),
        "candidate_registry_entry": accepted_record,
        "artifact_registry_updated": True,
        "state_artifact_updated": True,
        "state_source_updated": True,
        "project_source_mutated": False,
        "adoption_performed": True,
        "operator_instruction": "Candidate passed guarded release-control validation/adoption and now matches artifact current.",
    }
    return emit(result, 0)


async def cmd_artifact_adopt(backend: Any, args: argparse.Namespace) -> int:
    """Adopt an already-present Project Source ZIP as the local current baseline."""

    registry = _artifact_registry_from_args(args)
    requested = str(getattr(args, "artifact", "") or "").strip()
    filename = Path(requested).name
    project_url = _artifact_state_project_url(backend)
    before_state = backend.state_snapshot()
    before_registry = _artifact_registry_snapshot(registry)

    base_payload: dict[str, Any] = {
        "ok": False,
        "action": "artifact_adopt",
        "artifact_ref": filename,
        "source_ref": filename,
        "project_url": project_url,
        "project_source_mutated": False,
        "project_source_mutation": "not_requested",
        "before_snapshot": {
            "artifact_registry": before_registry,
            "state": _state_artifact_summary(before_state),
        },
    }

    def emit(payload: dict[str, Any], code: int) -> int:
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"status={payload.get('status')}")
            if payload.get("error"):
                print(f"error={payload.get('error')}")
            if payload.get("artifact_ref"):
                print(f"artifact_ref={payload.get('artifact_ref')}")
        return code

    if not requested or filename != requested and (Path(requested).name != filename):
        payload = {**base_payload, "status": "invalid_artifact_argument", "error": "artifact filename or path is required"}
        return emit(payload, 2)
    if not filename.endswith(".zip"):
        payload = {**base_payload, "status": "invalid_artifact_filename", "error": "artifact must be a .zip file"}
        return emit(payload, 2)
    filename_version = _artifact_version_from_filename(filename)
    if not filename_version:
        payload = {**base_payload, "status": "invalid_artifact_filename", "error": "artifact filename must end with _vX.Y.Z.zip or _vX.Y.Z.N.zip"}
        return emit(payload, 2)
    if not getattr(args, "from_project_source", False):
        payload = {**base_payload, "status": "project_source_verification_required", "artifact_version": filename_version, "source_version": filename_version, "error": "adopt requires --from-project-source so local state advances only after Project Source verification"}
        return emit(payload, 2)
    if not project_url:
        payload = {**base_payload, "status": "workspace_not_selected", "artifact_version": filename_version, "source_version": filename_version, "error": "select a workspace before adopting a Project Source artifact"}
        return emit(payload, 2)

    source_result = await backend.list_project_sources(keep_open=getattr(args, "keep_open", False))
    matched_sources, source_payload = _project_sources_matching_filename(source_result, filename)
    if not bool(source_payload.get("ok")):
        payload = {**base_payload, "status": "source_list_unavailable", "artifact_version": filename_version, "source_version": filename_version, "source_list": source_payload, "error": "could not verify Project Sources"}
        return emit(payload, 1)
    if len(matched_sources) != 1:
        payload = {
            **base_payload,
            "status": "project_source_match_count_invalid",
            "artifact_version": filename_version,
            "source_version": filename_version,
            "source_list": source_payload,
            "source_verified": False,
            "matching_expected_count": len(matched_sources),
            "error": f"expected exactly one matching Project Source named {filename}, found {len(matched_sources)}",
        }
        return emit(payload, 1)

    local_zip = _resolve_adopt_local_zip(filename if not Path(requested).is_file() else requested, local_path=getattr(args, "local_path", None), registry=registry)
    if local_zip is None:
        payload = {
            **base_payload,
            "status": "local_artifact_not_found",
            "artifact_version": filename_version,
            "source_version": filename_version,
            "source_verified": True,
            "source_list": source_payload,
            "matched_source": matched_sources[0],
            "error": "matching Project Source exists, but no local ZIP was found to verify/register; pass the ZIP path or --local-path",
        }
        return emit(payload, 1)
    if local_zip.name != filename:
        payload = {
            **base_payload,
            "status": "local_artifact_filename_mismatch",
            "artifact_version": filename_version,
            "source_version": filename_version,
            "local_path": str(local_zip),
            "error": f"local ZIP filename {local_zip.name} does not match requested artifact {filename}",
        }
        return emit(payload, 1)

    zip_check = verify_zip_artifact(local_zip)
    zip_version = _read_zip_version_file(local_zip)
    if not bool(zip_check.get("ok")):
        payload = {
            **base_payload,
            "status": "local_artifact_verification_failed",
            "artifact_version": filename_version,
            "source_version": filename_version,
            "source_verified": True,
            "local_path": str(local_zip),
            "zip": zip_check,
            "error": "local ZIP failed artifact verification",
        }
        return emit(payload, 1)
    if zip_version != filename_version:
        payload = {
            **base_payload,
            "status": "version_mismatch",
            "artifact_version": filename_version,
            "source_version": filename_version,
            "zip_version": zip_version,
            "local_path": str(local_zip),
            "zip": zip_check,
            "error": "filename version and ZIP VERSION differ",
        }
        return emit(payload, 1)

    record = ArtifactRecord(
        path=str(local_zip),
        filename=filename,
        kind="adopted_release",
        version=filename_version,
        repo_path=None,
        sha256=str(zip_check.get("sha256") or ""),
        size_bytes=int(zip_check.get("size_bytes") or local_zip.stat().st_size),
        file_count=int(zip_check.get("entry_count") or 0),
        created_at=utc_now(),
        source_ref=filename,
        project_url=project_url,
    )
    artifact_payload = registry.add(record)
    _state_store_from_args(args).remember_artifact(
        project_url=project_url,
        artifact_ref=filename,
        artifact_version=filename_version,
        source_ref=filename,
        source_version=filename_version,
    )
    after_state = backend.state_snapshot()
    after_registry = _artifact_registry_snapshot(registry)
    checks = {
        "source_verified": len(matched_sources) == 1,
        "zip_verified": bool(zip_check.get("ok")),
        "zip_version_matches_filename": zip_version == filename_version,
        "registry_current_matches_artifact": bool(after_registry.get("current")) and str((after_registry.get("current") or {}).get("filename") or "") == filename,
        "state_artifact_updated": _state_artifact_summary(after_state).get("artifact_ref") == filename and _state_artifact_summary(after_state).get("artifact_version") == filename_version,
        "state_source_updated": _state_artifact_summary(after_state).get("source_ref") == filename and _state_artifact_summary(after_state).get("source_version") == filename_version,
        "project_source_mutated": False,
    }
    ok = all(value for key, value in checks.items() if key != "project_source_mutated")
    payload = {
        **base_payload,
        "ok": ok,
        "status": "adopted" if ok else "adoption_verification_failed",
        "artifact_ref": filename,
        "artifact_version": filename_version,
        "source_ref": filename,
        "source_version": filename_version,
        "source_verified": True,
        "artifact_registry_updated": True,
        "state_artifact_updated": bool(checks["state_artifact_updated"]),
        "state_source_updated": bool(checks["state_source_updated"]),
        "project_source_mutated": False,
        "project_source_mutation": "not_requested",
        "mutating_actions_executed": True,
        "mutated_local_state_only": True,
        "local_artifact": artifact_payload,
        "local_path": str(local_zip),
        "zip": zip_check,
        "source_list": source_payload,
        "matched_source": matched_sources[0],
        "checks": checks,
        "after_snapshot": {
            "artifact_registry": after_registry,
            "state": _state_artifact_summary(after_state),
        },
    }
    return emit(payload, 0 if ok else 1)


async def cmd_artifact_release(backend: Any, args: argparse.Namespace) -> int:
    registry = _artifact_registry_from_args(args)
    repo_path = Path(args.path).expanduser().resolve()
    sync_source = bool(
        getattr(args, "sync_source", False)
        or getattr(args, "no_upload", False)
        or getattr(args, "upload", False)
        or getattr(args, "confirm_upload", False)
        or getattr(args, "dry_run", False)
    )
    if sync_source:
        source_args = argparse.Namespace(**vars(args))
        source_args.no_upload = bool(getattr(args, "no_upload", False))
        source_args.upload = bool(getattr(args, "upload", False))
        source_args.confirm_upload = bool(getattr(args, "confirm_upload", False))
        source_args.confirm_transaction_id = getattr(args, "confirm_transaction_id", None)
        source_args.force = bool(getattr(args, "force", False))
        source_args.dry_run = bool(getattr(args, "dry_run", False))
        source_args.keep_open = bool(getattr(args, "keep_open", False))
        source_args.artifact_kind = "release"
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = await cmd_src_sync(backend, source_args)
        raw = buffer.getvalue().strip()
        try:
            source_payload = json.loads(raw) if raw else {"ok": False, "status": "empty_source_sync_payload"}
        except json.JSONDecodeError as exc:
            source_payload = {
                "ok": False,
                "action": "src_sync",
                "status": "source_sync_payload_parse_failed",
                "error": str(exc),
                "raw_output": raw[:4000],
            }
            exit_code = 1
        payload = _rewrite_source_sync_payload_for_artifact_release(source_payload, repo_path=repo_path)
        if getattr(args, "print_confirm_command", False):
            confirmation = payload.get("confirmation") if isinstance(payload.get("confirmation"), dict) else None
            confirm_command = str(confirmation.get("confirm_command") or "") if confirmation else ""
            if confirm_command:
                print(confirm_command)
                return 0
            if args.json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print("ERROR: confirmation.confirm_command is not available for this artifact release result")
            return exit_code if exit_code else 2
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"status={payload.get('status')}")
            artifact = payload.get("artifact") if isinstance(payload.get("artifact"), dict) else {}
            if artifact.get("path"):
                print(f"artifact={artifact.get('path')}")
            confirmation = payload.get("confirmation") if isinstance(payload.get("confirmation"), dict) else None
            if confirmation and confirmation.get("confirm_command"):
                print(f"confirm_command={confirmation.get('confirm_command')}")
        return exit_code
    try:
        record, included = create_repo_snapshot(
            repo_path,
            output_dir=_artifact_output_dir(args, registry),
            filename=getattr(args, "filename", None),
            kind="release",
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "action": "artifact_release", "status": "failed", "error": str(exc)}, indent=2, ensure_ascii=False))
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
        "status": "packaged" if verify.get("ok") else "failed",
        "release_workflow": "artifact_release_local_v1",
        "artifact": artifact_payload,
        "included_count": len(included),
        "verify": verify,
        "project_url": project_url,
        "artifact_registry_updated": True,
        "state_artifact_updated": bool(project_url),
        "state_source_updated": False,
        "project_source_mutated": False,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"artifact={record.path}")
        print(f"file_count={record.file_count}")
        print(f"sha256={record.sha256}")
        print(f"status={payload['status']}")
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
    if args.artifact_command == "adopt":
        return await cmd_artifact_adopt(backend, args)
    if args.artifact_command == "accept-candidate":
        return await cmd_artifact_accept_candidate(backend, args)
    if args.artifact_command == "release":
        return await cmd_artifact_release(backend, args)
    if args.artifact_command == "verify":
        return await cmd_artifact_verify(backend, args)
    if args.artifact_command == "intake":
        return await cmd_artifact_intake(backend, args)
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
        "profile": "browser",
        "path": ".",
        "package_zip": None,
        "rate_limit_safe": None,
    }
    for name, value in defaults.items():
        if not hasattr(args, name):
            setattr(args, name, value)


def _apply_rate_limit_safe_defaults(args: argparse.Namespace) -> None:
    """Apply conservative pacing for the live full browser profile.

    ChatGPT may temporarily limit conversation-history access when repeated
    browser contexts cause the web app to fetch `/backend-api/conversations`
    too quickly. The full profile is intentionally broad, so make it slower by
    default while still allowing operators to opt out with
    `--no-rate-limit-safe` or explicit delay flags.
    """
    profile = str(getattr(args, "profile", "browser") or "browser").lower()
    requested = getattr(args, "rate_limit_safe", None)
    rate_limit_safe = (profile == "full") if requested is None else bool(requested)
    setattr(args, "rate_limit_safe", rate_limit_safe)
    if not rate_limit_safe or profile not in {"browser", "full"}:
        return

    conservative = {
        "step_delay_seconds": 20.0,
        "post_ask_delay_seconds": 60.0,
        "task_list_visible_poll_min_seconds": 45.0,
        "task_list_visible_poll_max_seconds": 90.0,
        "task_list_visible_max_attempts": 2,
    }
    legacy_defaults = {
        "step_delay_seconds": 8.0,
        "post_ask_delay_seconds": 20.0,
        "task_list_visible_poll_min_seconds": 20.0,
        "task_list_visible_poll_max_seconds": 45.0,
        "task_list_visible_max_attempts": 4,
    }
    for name, value in conservative.items():
        current = getattr(args, name, None)
        if current is None or current == legacy_defaults.get(name):
            setattr(args, name, value)


async def cmd_test_report(args: argparse.Namespace) -> int:
    report = build_test_report(args.log, service_log=getattr(args, "service_log", None))
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_test_report_text(report), end="")
    return 0 if report.get("ok") else 1


async def cmd_test_status(args: argparse.Namespace) -> int:
    status = build_test_status(
        path=getattr(args, "path", "."),
        log=getattr(args, "log", None),
        service_log=getattr(args, "service_log", None),
    )
    if getattr(args, "json", False):
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print(f"ok={bool(status.get('ok'))}")
        print(f"status={status.get('status')}")
        selected = status.get("selected_log") if isinstance(status.get("selected_log"), dict) else None
        if selected:
            print(f"log_path={selected.get('path')}")
            print(f"log_mtime={selected.get('mtime_iso')}")
        suite = status.get("suite") if isinstance(status.get("suite"), dict) else {}
        if suite:
            print(f"version={suite.get('version')}")
            print(f"profile={suite.get('profile')}")
            print(f"failure_count={suite.get('failure_count')}")
            telemetry = suite.get("rate_limit_telemetry") if isinstance(suite.get("rate_limit_telemetry"), dict) else {}
            if telemetry:
                print(
                    "rate_limit="
                    f"modal={telemetry.get('rate_limit_modal_detected')} "
                    f"429={telemetry.get('conversation_history_429_seen')} "
                    f"cooldowns={telemetry.get('cooldown_wait_count')} "
                    f"planned={telemetry.get('planned_cooldown_wait_count')}"
                )
    return 0 if status.get("ok") else 1


async def cmd_test_import_smoke(args: argparse.Namespace) -> int:
    result = package_import_smoke(repo_path=getattr(args, "path", "."), python_executable=getattr(args, "python_executable", None))
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"package_import_smoke: {result.get('status')}")
        for failure in result.get("failures") or []:
            print(f"- {failure.get('module')}: {failure.get('error_type')} {failure.get('error')}")
    return 0 if result.get("ok") else 1


async def cmd_test(backend: CommandBackend, args: argparse.Namespace) -> int:
    del backend
    if args.test_command == "report":
        return await cmd_test_report(args)
    if args.test_command == "status":
        return await cmd_test_status(args)
    if args.test_command == "import-smoke":
        return await cmd_test_import_smoke(args)
    if args.test_command == "smoke":
        _apply_test_suite_defaults(args)
        return await cmd_test_suite(args)
    if args.test_command in {"browser", "agent", "full"}:
        _apply_test_suite_defaults(args)
        args.profile = args.test_command
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



async def cmd_agent(backend: CommandBackend, args: argparse.Namespace) -> int:
    snapshot = backend.state_snapshot()
    if args.agent_command == "inspect":
        payload = inspect_local_context(
            repo_path=args.path,
            profile_dir=getattr(args, "profile_dir", None),
            max_files=args.max_files,
            state_snapshot=snapshot,
        )
    elif args.agent_command == "doctor":
        payload = agent_doctor(
            repo_path=args.path,
            profile_dir=getattr(args, "profile_dir", None),
            state_snapshot=snapshot,
        )
    elif args.agent_command == "plan":
        payload = plan_agent_request(args.request, repo_path=args.path)
    elif args.agent_command == "ask":
        payload = agent_ask(
            args.request,
            repo_path=args.path,
            profile_dir=getattr(args, "profile_dir", None),
            model=getattr(args, "model", None),
            ollama_host=getattr(args, "ollama_host", "http://localhost:11434"),
            ollama_timeout_seconds=getattr(args, "ollama_timeout_seconds", 8.0),
            summarize=getattr(args, "summarize", False),
        )
    elif args.agent_command == "run":
        payload = agent_run(
            args.request,
            repo_path=args.path,
            profile_dir=getattr(args, "profile_dir", None),
            skill=getattr(args, "skill", None),
            model=getattr(args, "model", None),
            proposal_mode=getattr(args, "proposal_mode", "deterministic"),
            ollama_host=getattr(args, "ollama_host", "http://localhost:11434"),
            ollama_timeout_seconds=getattr(args, "ollama_timeout_seconds", 8.0),
            command=getattr(args, "mcp_executable", None),
            mcp_timeout_seconds=getattr(args, "mcp_timeout_seconds", 8.0),
        )
    elif args.agent_command == "host-smoke":
        payload = mcp_host_smoke(
            repo_path=args.path,
            profile_dir=getattr(args, "profile_dir", None),
            command=getattr(args, "mcp_executable", None),
            timeout_seconds=getattr(args, "mcp_timeout_seconds", 8.0),
        )
    elif args.agent_command == "mcp-call":
        try:
            tool_args = json.loads(args.arguments or "{}")
        except json.JSONDecodeError as exc:
            payload = {"ok": False, "action": "agent_mcp_call", "status": "invalid_arguments_json", "error": str(exc), "tool": args.tool}
        else:
            if not isinstance(tool_args, dict):
                payload = {"ok": False, "action": "agent_mcp_call", "status": "invalid_arguments_json", "error": "arguments must decode to a JSON object", "tool": args.tool}
            else:
                payload = mcp_tool_call_via_stdio(
                    args.tool,
                    tool_args,
                    repo_path=args.path,
                    profile_dir=getattr(args, "profile_dir", None),
                    command=getattr(args, "mcp_executable", None),
                    timeout_seconds=getattr(args, "mcp_timeout_seconds", 8.0),
                )
    elif args.agent_command == "tool-call":
        try:
            tool_args = json.loads(args.arguments or "{}")
        except json.JSONDecodeError as exc:
            payload = {"ok": False, "action": "agent_tool_call", "status": "invalid_arguments_json", "error": str(exc), "tool": args.tool}
        else:
            if not isinstance(tool_args, dict):
                payload = {"ok": False, "action": "agent_tool_call", "status": "invalid_arguments_json", "error": "arguments must decode to a JSON object", "tool": args.tool}
            else:
                payload = agent_tool_call(args.tool, tool_args, repo_path=args.path, profile_dir=getattr(args, "profile_dir", None))
    elif args.agent_command == "ollama-propose":
        payload = ollama_propose_mcp_tool_call(
            getattr(args, "request", "read VERSION"),
            model=getattr(args, "model", DEFAULT_OLLAMA_TOOL_MODEL),
            ollama_host=getattr(args, "ollama_host", "http://localhost:11434"),
            ollama_timeout_seconds=getattr(args, "ollama_timeout_seconds", 8.0),
            allow_schema_fallback=not getattr(args, "no_schema_fallback", False),
        )
    elif args.agent_command == "mcp-llm-smoke":
        payload = agent_mcp_llm_smoke(
            getattr(args, "request", "read VERSION"),
            repo_path=args.path,
            profile_dir=getattr(args, "profile_dir", None),
            model=getattr(args, "model", DEFAULT_OLLAMA_TOOL_MODEL),
            ollama_host=getattr(args, "ollama_host", "http://localhost:11434"),
            ollama_timeout_seconds=getattr(args, "ollama_timeout_seconds", 8.0),
            command=getattr(args, "mcp_executable", None),
            mcp_timeout_seconds=getattr(args, "mcp_timeout_seconds", 8.0),
        )
    elif args.agent_command == "summarize-log":
        payload = agent_summarize_log(
            args.log_path,
            repo_path=args.path,
            model=getattr(args, "model", "llama3.2:3b"),
            ollama_host=getattr(args, "ollama_host", "http://localhost:11434"),
            ollama_timeout_seconds=getattr(args, "ollama_timeout_seconds", 8.0),
            max_bytes=getattr(args, "max_bytes", 12000),
        )
    elif args.agent_command == "models":
        payload = ollama_models(
            host=getattr(args, "ollama_host", "http://localhost:11434"),
            timeout_seconds=getattr(args, "ollama_timeout_seconds", 8.0),
        )
    else:
        raise RuntimeError(f"Unknown agent command: {args.agent_command}")

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload.get("ok") else 1

    if args.agent_command == "inspect":
        repo = payload.get("repo") if isinstance(payload.get("repo"), dict) else {}
        state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
        print(f"repo={repo.get('path')}")
        print(f"version={repo.get('version') or 'none'}")
        print(f"files={repo.get('file_count')}")
        print(f"workspace={state.get('project_name') or state.get('resolved_project_home_url') or 'none'}")
        print(f"task={state.get('conversation_id') or 'none'}")
        return 0

    if args.agent_command == "doctor":
        checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
        for name, value in checks.items():
            print(f"{name}={str(bool(value)).lower()}")
        return 0 if payload.get("ok") else 1

    if args.agent_command == "models":
        print(f"status={payload.get('status')}")
        print(f"count={payload.get('count', 0)}")
        for name in payload.get("model_names", []) if isinstance(payload.get("model_names"), list) else []:
            print(f"model={name}")
        return 0 if payload.get("ok") else 1

    if args.agent_command == "tool-call":
        print(f"status={payload.get('status')}")
        print(f"tool={payload.get('tool')}")
        return 0 if payload.get("ok") else 1

    if args.agent_command == "ask":
        print(f"mode={payload.get('mode')}")
        print(f"planner={payload.get('planner')}")
        for call in payload.get("tool_calls", []) if isinstance(payload.get("tool_calls"), list) else []:
            if isinstance(call, dict):
                print(f"tool={call.get('name')}")
        return 0 if payload.get("ok") else 1

    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
    print(f"intent={plan.get('intent')}")
    print(f"risk={plan.get('risk')}")
    print(f"auto_allowed={str(bool(plan.get('auto_allowed'))).lower()}")
    commands = plan.get("suggested_commands") if isinstance(plan.get("suggested_commands"), list) else []
    for command in commands:
        if isinstance(command, list):
            print("command=" + " ".join(str(part) for part in command))
    return 0 if payload.get("ok") else 1


async def cmd_skill(backend: CommandBackend, args: argparse.Namespace) -> int:
    if args.skill_command == "list":
        payload = skill_list(repo_path=args.path, profile_dir=getattr(args, "profile_dir", None))
    elif args.skill_command == "show":
        payload = skill_show(args.skill, repo_path=args.path, profile_dir=getattr(args, "profile_dir", None), include_content=not getattr(args, "no_content", False))
    elif args.skill_command == "validate":
        payload = skill_validate(args.skill, repo_path=args.path, profile_dir=getattr(args, "profile_dir", None))
    else:
        raise RuntimeError(f"Unknown skill command: {args.skill_command}")

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload.get("ok") else 1

    if args.skill_command == "list":
        for item in payload.get("skills", []) if isinstance(payload.get("skills"), list) else []:
            if isinstance(item, dict):
                print(f"{item.get('name')}	{item.get('risk')}	{item.get('source')}")
        return 0 if payload.get("ok") else 1

    print(f"status={payload.get('status')}")
    validation = payload.get("validation") if isinstance(payload.get("validation"), dict) else payload
    skill_info = validation.get("skill") if isinstance(validation.get("skill"), dict) else {}
    if skill_info.get("name"):
        print(f"name={skill_info.get('name')}")
    errors = validation.get("errors") if isinstance(validation.get("errors"), list) else []
    for error in errors:
        print(f"error={error}")
    return 0 if payload.get("ok") else 1


async def cmd_mcp(backend: CommandBackend, args: argparse.Namespace) -> int:
    if args.mcp_command == "serve":
        profile_dir = getattr(args, "profile_dir", None)
        if not profile_dir and hasattr(backend, "profile_dir"):
            profile_dir = getattr(backend, "profile_dir")
        return serve_mcp_stdio(
            repo_path=getattr(args, "path", "."),
            profile_dir=profile_dir,
            include_controlled_processes=getattr(args, "include_controlled_processes", False),
        )

    if args.mcp_command == "manifest":
        payload = mcp_tool_manifest(include_controlled_processes=args.include_controlled_processes)
    elif args.mcp_command == "config":
        profile_dir = getattr(args, "profile_dir", None)
        if not profile_dir and hasattr(backend, "profile_dir"):
            profile_dir = getattr(backend, "profile_dir")
        payload = mcp_host_config(
            repo_path=getattr(args, "path", "."),
            profile_dir=profile_dir,
            server_name=getattr(args, "server_name", "promptbranch"),
            command=getattr(args, "mcp_executable", None),
            resolve_command=not getattr(args, "no_resolve_command", False),
            include_controlled_processes=getattr(args, "include_controlled_processes", False),
            host=getattr(args, "host", "generic"),
        )
    elif args.mcp_command == "host-smoke":
        profile_dir = getattr(args, "profile_dir", None)
        if not profile_dir and hasattr(backend, "profile_dir"):
            profile_dir = getattr(backend, "profile_dir")
        payload = mcp_host_smoke(
            repo_path=getattr(args, "path", "."),
            profile_dir=profile_dir,
            server_name=getattr(args, "server_name", "promptbranch"),
            command=getattr(args, "mcp_executable", None),
            resolve_command=not getattr(args, "no_resolve_command", False),
            include_controlled_processes=getattr(args, "include_controlled_processes", False),
            host=getattr(args, "host", "generic"),
            timeout_seconds=getattr(args, "timeout_seconds", 8.0),
        )
    else:
        raise RuntimeError(f"Unknown mcp command: {args.mcp_command}")
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload.get("ok", True) else 1
    if args.mcp_command == "config":
        print(json.dumps(payload.get("config"), indent=2, ensure_ascii=False))
        return 0
    if args.mcp_command == "host-smoke":
        checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
        print(f"status={payload.get('status')}")
        print(f"ok={str(bool(payload.get('ok'))).lower()}")
        for name, value in checks.items():
            print(f"{name}={str(bool(value)).lower()}")
        return 0 if payload.get("ok") else 1
    print(f"mode={payload.get('mode')}")
    print(f"tool_count={payload.get('tool_count')}")
    for tool in payload.get("tools", []):
        if isinstance(tool, dict):
            print(f"{tool.get('name')}	{tool.get('risk')}	read_only={str(bool(tool.get('read_only'))).lower()}")
    return 0



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


def _add_test_suite_profile_options(parser: argparse.ArgumentParser) -> None:
    """Attach the shared options used by pb test-suite profile aliases."""
    parser.add_argument("--json", action="store_true", help="Emit the full test-suite summary as JSON.")
    parser.add_argument("--path", default=".", help="Repo path used by agent/full profiles. Defaults to current directory.")
    parser.add_argument("--package-zip", help="Optional release ZIP path for package hygiene checks in agent/full profiles.")
    parser.add_argument("--keep-open", action="store_true", help="Keep the browser open between steps where supported.")
    parser.add_argument("--keep-project", action="store_true", help="Do not delete the test project at the end.")
    parser.add_argument("--step-delay-seconds", type=float, default=8.0, help="Delay inserted before each step after the first to reduce ChatGPT rate-limit pressure.")
    parser.add_argument("--post-ask-delay-seconds", type=float, default=20.0, help="Additional cooldown after ask steps before reading task/conversation history.")
    parser.add_argument("--rate-limit-safe", dest="rate_limit_safe", action="store_true", default=None, help="Use conservative live-browser pacing for ChatGPT conversation-history rate limits. Default for full profile.")
    parser.add_argument("--no-rate-limit-safe", dest="rate_limit_safe", action="store_false", help="Disable conservative full-profile pacing.")
    parser.add_argument("--task-list-visible-timeout-seconds", type=float, default=120.0, help="Maximum bounded wait for a task created by ask() to become visible in task listing.")
    parser.add_argument("--task-list-visible-poll-min-seconds", type=float, default=20.0, help="Initial backoff between task-list visibility probes after ask().")
    parser.add_argument("--task-list-visible-poll-max-seconds", type=float, default=45.0, help="Maximum backoff between task-list visibility probes after ask().")
    parser.add_argument("--task-list-visible-max-attempts", type=int, default=4, help="Maximum number of task-list visibility probes after ask().")
    parser.add_argument("--allow-recent-state-task-fallback", action="store_true", help="Allow task_message_flow to pass when a new task is visible only from local recent_state fallback. Default is strict indexed visibility.")
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
    parser.add_argument("--project-list-debug-scroll-rounds", type=int, default=12)
    parser.add_argument("--project-list-debug-wait-ms", type=int, default=350)
    parser.add_argument("--project-list-debug-manual-pause", action="store_true")
    parser.add_argument("--clear-singleton-locks", action="store_true", help="Clear stale Chrome Singleton* lock artifacts before launch.")


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
    parser.add_argument("--debug", action="store_true", default=_env_flag("CHATGPT_DEBUG", False))
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
    task_list.add_argument("--deep-history", action="store_true", help="Also scan global conversation history. Slow and may trigger ChatGPT 429s; normally unnecessary when project backend/indexed sources work.")

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

    task_answer = task_subparsers.add_parser("answer", help="Parse assistant answers as Promptbranch protocol data.")
    task_answer_subparsers = task_answer.add_subparsers(dest="task_answer_command", required=True)
    task_answer_parse = task_answer_subparsers.add_parser("parse", help="Parse one assistant answer for a Promptbranch reply envelope.")
    task_answer_parse.add_argument("id_or_index", nargs="?", help="User message index/id. Defaults to latest when --latest is used or no selector is provided.")
    task_answer_parse.add_argument("--latest", action="store_true", help="Parse the latest assistant answer on the latest user message.")
    task_answer_parse.add_argument("--answer-index", help="Assistant answer index for the selected user message. Defaults to latest.")
    task_answer_parse.add_argument("--answer-id", help="Assistant answer exact id or unique id prefix.")
    task_answer_parse.add_argument("--task", dest="target", help="Optional conversation URL, id, id prefix, exact title, or numeric index from task list.")
    task_answer_parse.add_argument("--json", action="store_true", help="Emit parsed protocol reply as JSON.")
    task_answer_parse.add_argument("--keep-open", action="store_true")

    src = subparsers.add_parser("src", help="Source commands for the active workspace.")
    src_subparsers = src.add_subparsers(dest="src_command", required=True)

    src_list = src_subparsers.add_parser("list", help="List sources for the current workspace.")
    src_list.add_argument("--json", action="store_true", help="Emit the full source list payload as JSON.")
    src_list.add_argument("--keep-open", action="store_true")

    src_add = src_subparsers.add_parser("add", help="Add a source to the current workspace.")
    src_add.add_argument("file_path", nargs="?", help="Local file path for file sources. Equivalent to --file.")
    src_add.add_argument("--type", choices=["link", "text", "file"], default="file")
    src_add.add_argument("--value", help="Source payload for link/text sources.")
    src_add.add_argument("--file", help="Local file path for file sources.")
    src_add.add_argument("--name", help="Optional display name/title to set when the UI supports it.")
    src_add.add_argument("--no-overwrite", action="store_true", help="Do not replace an existing file source with the same display name.")
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
    src_sync.add_argument("--upload", action="store_true", help="Request a live ChatGPT project source upload preflight. Requires --confirm-upload to execute.")
    src_sync.add_argument("--confirm-upload", action="store_true", help="Explicitly confirm live ChatGPT project source upload. Use only after reviewing upload preflight.")
    src_sync.add_argument("--confirm-transaction-id", help="Transaction id from a reviewed --upload preflight. Required with --confirm-upload for live source upload.")
    src_sync.add_argument("--force", action="store_true", help="Allow local artifact overwrite/collision during --no-upload sync.")
    src_sync.add_argument("--dry-run", "--plan", dest="dry_run", action="store_true", help="Plan source sync without creating a ZIP, updating local state, or uploading a source.")
    src_sync.add_argument("--json", action="store_true", help="Emit the sync result as JSON.")
    src_sync.add_argument("--keep-open", action="store_true")

    artifact = subparsers.add_parser("artifact", help="Artifact lifecycle commands for local repo snapshots and release ZIPs.")
    artifact_subparsers = artifact.add_subparsers(dest="artifact_command", required=True)

    artifact_current = artifact_subparsers.add_parser("current", help="Show the current artifact/source state.")
    artifact_current.add_argument("--json", action="store_true")

    artifact_list = artifact_subparsers.add_parser("list", help="List locally registered artifacts.")
    artifact_list.add_argument("--json", action="store_true")

    artifact_adopt = artifact_subparsers.add_parser("adopt", help="Adopt an existing Project Source ZIP as the current local artifact/source baseline.")
    artifact_adopt.add_argument("artifact", help="Artifact ZIP filename or local ZIP path to adopt, for example chatgpt_claudecode_workflow_v0.0.219.zip.")
    artifact_adopt.add_argument("--from-project-source", action="store_true", help="Verify the ZIP exists exactly once in current Project Sources before updating local registry/state.")
    artifact_adopt.add_argument("--local-path", help="Explicit local ZIP path to verify/register when the positional artifact is only a filename.")
    artifact_adopt.add_argument("--keep-open", action="store_true")
    artifact_adopt.add_argument("--json", action="store_true")

    artifact_accept_candidate = artifact_subparsers.add_parser("accept-candidate", help="Guardedly test/adopt a migrated candidate_release artifact.")
    artifact_accept_candidate.add_argument("artifact", nargs="?", help="Candidate ZIP filename. Optional when --version selects exactly one candidate.")
    artifact_accept_candidate.add_argument("--version", help="Candidate version such as v0.0.219. Used to select the candidate registry entry.")
    artifact_accept_candidate.add_argument("--repo-path", default=".", help="Repository root containing the migrated candidate ZIP and release-control script. Defaults to current directory.")
    artifact_accept_candidate.add_argument("--from-project-source", action="store_true", help="Require exactly one matching Project Source before guarded adoption.")
    artifact_accept_candidate.add_argument("--run-release-control", action="store_true", help="Run the fixed release-control --tests-only --adopt-if-green command for the selected candidate.")
    artifact_accept_candidate.add_argument("--adopt-if-green", action="store_true", help="Adopt only if release-control tests/report are green and final artifact current matches the candidate.")
    artifact_accept_candidate.add_argument("--test-timeout", type=float, default=3600.0, help="Timeout in seconds for release-control test/adopt execution. Defaults to 3600.")
    artifact_accept_candidate.add_argument("--release-log-keep", type=int, default=12, help="Release log directories to keep when pruning. Defaults to 12.")
    artifact_accept_candidate.add_argument("--skip-docker-logs", action="store_true", default=True, help="Skip docker log capture in release-control. Default: true.")
    artifact_accept_candidate.add_argument("--no-prune-release-logs", dest="prune_release_logs", action="store_false", help="Do not pass --prune-release-logs to release-control.")
    artifact_accept_candidate.set_defaults(prune_release_logs=True)
    artifact_accept_candidate.add_argument("--keep-open", action="store_true")
    artifact_accept_candidate.add_argument("--json", action="store_true")

    artifact_release = artifact_subparsers.add_parser("release", help="Create a release ZIP from a repo path, optionally through the source-sync transaction workflow.")
    artifact_release.add_argument("path", nargs="?", default=".", help="Repo path to package. Defaults to the current directory.")
    artifact_release.add_argument("--output-dir", help="Directory for the generated ZIP. Defaults to .pb_profile/artifacts.")
    artifact_release.add_argument("--filename", help="Override the generated artifact filename.")
    artifact_release.add_argument("--sync-source", action="store_true", help="Use the canonical artifact release -> source sync transaction workflow.")
    artifact_release.add_argument("--no-upload", action="store_true", help="With --sync-source, package and register locally without uploading as a project source.")
    artifact_release.add_argument("--upload", action="store_true", help="With --sync-source, run live upload preflight. Requires --confirm-upload to execute.")
    artifact_release.add_argument("--confirm-upload", action="store_true", help="With --sync-source, confirm a reviewed live source upload.")
    artifact_release.add_argument("--confirm-transaction-id", help="Transaction id from a reviewed --upload preflight.")
    artifact_release.add_argument("--force", action="store_true", help="Allow local artifact overwrite/collision during sync-source release.")
    artifact_release.add_argument("--print-confirm-command", "--confirm-command-only", dest="print_confirm_command", action="store_true", help="Print only the top-level confirmation.confirm_command when available. Useful for shell command substitution.")
    artifact_release.add_argument("--dry-run", "--plan", dest="dry_run", action="store_true", help="Plan release/source transaction without packaging, registering, or uploading.")
    artifact_release.add_argument("--keep-open", action="store_true")
    artifact_release.add_argument("--json", action="store_true")

    artifact_verify = artifact_subparsers.add_parser("verify", help="Verify ZIP layout and integrity.")
    artifact_verify.add_argument("path", nargs="?", help="ZIP path. Defaults to the latest registered artifact.")
    artifact_verify.add_argument("--json", action="store_true")


    artifact_intake = artifact_subparsers.add_parser("intake", help="Extract candidate artifacts from a parsed Promptbranch ask/reply answer; optional explicit download/verification in .pb_profile/artifact_inbox/.")
    artifact_intake.add_argument("--from-last-answer", action="store_true", help="Read the latest assistant answer from the current task and extract artifact candidates.")
    artifact_intake.add_argument("--expect-artifact", help="Expected artifact filename, used to reject wrong or ambiguous candidates.")
    artifact_intake.add_argument("--expect-version", help="Expected artifact version such as v0.0.219 or 0.0.219.")
    artifact_intake.add_argument("--expect-repo", help="Expected artifact project/repo prefix such as chatgpt_claudecode_workflow.")
    artifact_intake.add_argument("--task", dest="target", help="Optional conversation URL, id, id prefix, exact title, or numeric index from task list.")
    artifact_intake.add_argument("--download", action="store_true", help="Explicitly download the selected candidate into .pb_profile/artifact_inbox/. No verification, migration, or adoption is performed.")
    artifact_intake.add_argument("--download-timeout", type=float, default=120.0, help="Artifact download timeout in seconds for --download. Defaults to 120.")
    artifact_intake.add_argument("--verify", action="store_true", help="Verify the selected candidate ZIP inside .pb_profile/artifact_inbox/.")
    artifact_intake.add_argument("--migrate", action="store_true", help="Migrate a verified candidate ZIP from .pb_profile/artifact_inbox/ to the repo root and register it as candidate_release. No adoption or Project Source mutation is performed.")
    artifact_intake.add_argument("--repo-path", default=".", help="Repository root for --migrate. Defaults to the current directory.")
    artifact_intake.add_argument("--json", action="store_true", help="Emit artifact intake candidate extraction/download/verification/migration result as JSON.")
    artifact_intake.add_argument("--keep-open", action="store_true")

    agent = subparsers.add_parser("agent", help="Read-only MCP/Ollama planning scaffold commands.")
    agent_subparsers = agent.add_subparsers(dest="agent_command", required=True)

    agent_inspect = agent_subparsers.add_parser("inspect", help="Inspect local repo, git, artifact, and Promptbranch state without mutating anything.")
    agent_inspect.add_argument("path", nargs="?", default=".", help="Repo path to inspect. Defaults to current directory.")
    agent_inspect.add_argument("--max-files", type=int, default=80, help="Maximum repo file sample size to include.")
    agent_inspect.add_argument("--json", action="store_true")

    agent_doctor_parser = agent_subparsers.add_parser("doctor", help="Run read-only MCP/agent readiness checks.")
    agent_doctor_parser.add_argument("path", nargs="?", default=".", help="Repo path to inspect. Defaults to current directory.")
    agent_doctor_parser.add_argument("--json", action="store_true")

    agent_plan = agent_subparsers.add_parser("plan", help="Classify a request into a policy-gated Promptbranch/MCP plan without executing it.")
    agent_plan.add_argument("request", help="Natural-language request to classify.")
    agent_plan.add_argument("--path", default=".", help="Repo path used for command suggestions. Defaults to current directory.")
    agent_plan.add_argument("--json", action="store_true")

    agent_ask_parser = agent_subparsers.add_parser("ask", help="Execute a deterministic read-only local-agent request through MCP tools.")
    agent_ask_parser.add_argument("request", help="Natural-language read-only request, for example: read VERSION and git status.")
    agent_ask_parser.add_argument("--path", default=".", help="Repo path exposed to read-only MCP tools. Defaults to current directory.")
    agent_ask_parser.add_argument("--model", help="Optional Ollama model used only for summary, never for tool planning.")
    agent_ask_parser.add_argument("--summarize", action="store_true", help="Ask Ollama to summarize the deterministic tool results. Non-fatal if Ollama fails.")
    agent_ask_parser.add_argument("--ollama-host", default="http://localhost:11434", help="Ollama base URL used only for optional summary/model listing.")
    agent_ask_parser.add_argument("--ollama-timeout-seconds", type=float, default=8.0, help="Timeout for optional Ollama calls.")
    agent_ask_parser.add_argument("--json", action="store_true")

    agent_run_parser = agent_subparsers.add_parser("run", help="Canonical Promptbranch-native host/client run command over MCP stdio.")
    agent_run_parser.add_argument("request", help="Natural-language read-only request, for example: read VERSION and git status.")
    agent_run_parser.add_argument("--path", default=".", help="Repo path exposed to read-only MCP tools. Defaults to current directory.")
    agent_run_parser.add_argument("--skill", help="Optional local skill name/path, for example repo-inspection.")
    agent_run_parser.add_argument("--model", help="Optional Ollama tool-use model for proposal mode. Defaults to deterministic planning unless --proposal-mode ollama is set.")
    agent_run_parser.add_argument("--proposal-mode", choices=["deterministic", "ollama"], default="deterministic", help="Planning source. Ollama mode still passes through policy validation.")
    agent_run_parser.add_argument("--ollama-host", default="http://localhost:11434", help="Ollama base URL for proposal mode.")
    agent_run_parser.add_argument("--ollama-timeout-seconds", type=float, default=8.0, help="Timeout for Ollama proposal calls.")
    agent_run_parser.add_argument("--command", dest="mcp_executable", help="Executable used to launch pb mcp serve. Defaults to promptbranch resolved on PATH.")
    agent_run_parser.add_argument("--mcp-timeout-seconds", type=float, default=8.0, help="Timeout for each MCP stdio tool call.")
    agent_run_parser.add_argument("--json", action="store_true")

    agent_host_smoke_parser = agent_subparsers.add_parser("host-smoke", help="Smoke-test Promptbranch as an MCP host/client by launching pb mcp serve over stdio.")
    agent_host_smoke_parser.add_argument("--path", default=".", help="Repo path exposed to read-only MCP tools. Defaults to current directory.")
    agent_host_smoke_parser.add_argument("--command", dest="mcp_executable", help="Executable used to launch pb mcp serve. Defaults to promptbranch resolved on PATH.")
    agent_host_smoke_parser.add_argument("--mcp-timeout-seconds", type=float, default=8.0, help="Timeout for the MCP stdio smoke run.")
    agent_host_smoke_parser.add_argument("--json", action="store_true")

    agent_mcp_call_parser = agent_subparsers.add_parser("mcp-call", help="Call one read-only MCP tool through the actual stdio server boundary.")
    agent_mcp_call_parser.add_argument("tool", help="Read-only MCP tool name, for example filesystem.read.")
    agent_mcp_call_parser.add_argument("arguments", nargs="?", default="{}", help="JSON object with tool arguments.")
    agent_mcp_call_parser.add_argument("--path", default=".", help="Repo path exposed to read-only MCP tools. Defaults to current directory.")
    agent_mcp_call_parser.add_argument("--command", dest="mcp_executable", help="Executable used to launch pb mcp serve. Defaults to promptbranch resolved on PATH.")
    agent_mcp_call_parser.add_argument("--mcp-timeout-seconds", type=float, default=8.0, help="Timeout for the MCP stdio tool call.")
    agent_mcp_call_parser.add_argument("--json", action="store_true")

    agent_tool_call_parser = agent_subparsers.add_parser("tool-call", help="Call one read-only MCP tool through the deterministic local executor.")
    agent_tool_call_parser.add_argument("tool", help="Read-only MCP tool name, for example filesystem.read.")
    agent_tool_call_parser.add_argument("arguments", nargs="?", default="{}", help="JSON object with tool arguments.")
    agent_tool_call_parser.add_argument("--path", default=".", help="Repo path exposed to read-only MCP tools. Defaults to current directory.")
    agent_tool_call_parser.add_argument("--json", action="store_true")

    agent_ollama_propose_parser = agent_subparsers.add_parser("ollama-propose", help="Ask Ollama to propose one read-only MCP tool call, then validate without executing it.")
    agent_ollama_propose_parser.add_argument("request", nargs="?", default="read VERSION", help="Read-only request for the model to map to one MCP tool call.")
    agent_ollama_propose_parser.add_argument("--path", default=".", help="Accepted for symmetry with other agent commands; proposal itself does not read the repo.")
    agent_ollama_propose_parser.add_argument("--model", default=DEFAULT_OLLAMA_TOOL_MODEL, help="Ollama tool-use model. Defaults to llama3-groq-tool-use:8b.")
    agent_ollama_propose_parser.add_argument("--ollama-host", default="http://localhost:11434", help="Ollama base URL.")
    agent_ollama_propose_parser.add_argument("--ollama-timeout-seconds", type=float, default=8.0, help="Timeout for the Ollama proposal call.")
    agent_ollama_propose_parser.add_argument("--no-schema-fallback", action="store_true", help="Disable JSON-schema fallback after native chat-tools fail.")
    agent_ollama_propose_parser.add_argument("--json", action="store_true")

    agent_mcp_llm_smoke_parser = agent_subparsers.add_parser("mcp-llm-smoke", help="Diagnostic: ask Ollama to propose one read-only MCP tool call, validate it, then execute via MCP stdio.")
    agent_mcp_llm_smoke_parser.add_argument("request", nargs="?", default="read VERSION", help="Read-only request for the model to map to one MCP tool call.")
    agent_mcp_llm_smoke_parser.add_argument("--path", default=".", help="Repo path exposed to read-only MCP tools. Defaults to current directory.")
    agent_mcp_llm_smoke_parser.add_argument("--model", default=DEFAULT_OLLAMA_TOOL_MODEL, help="Ollama model used to propose the MCP tool call. Defaults to llama3-groq-tool-use:8b.")
    agent_mcp_llm_smoke_parser.add_argument("--ollama-host", default="http://localhost:11434", help="Ollama base URL.")
    agent_mcp_llm_smoke_parser.add_argument("--ollama-timeout-seconds", type=float, default=8.0, help="Timeout for the Ollama proposal call.")
    agent_mcp_llm_smoke_parser.add_argument("--command", dest="mcp_executable", help="Executable used to launch pb mcp serve. Defaults to promptbranch resolved on PATH.")
    agent_mcp_llm_smoke_parser.add_argument("--mcp-timeout-seconds", type=float, default=8.0, help="Timeout for the MCP stdio tool call.")
    agent_mcp_llm_smoke_parser.add_argument("--json", action="store_true")

    agent_summarize_log_parser = agent_subparsers.add_parser("summarize-log", help="Summarize a repo-bounded log file with optional Ollama; never executes tools or writes state.")
    agent_summarize_log_parser.add_argument("log_path", help="Repo-relative log file path to summarize.")
    agent_summarize_log_parser.add_argument("--path", default=".", help="Repo path used to bound the log read. Defaults to current directory.")
    agent_summarize_log_parser.add_argument("--model", default="llama3.2:3b", help="Ollama model used only for summarization.")
    agent_summarize_log_parser.add_argument("--ollama-host", default="http://localhost:11434", help="Ollama base URL.")
    agent_summarize_log_parser.add_argument("--ollama-timeout-seconds", type=float, default=8.0, help="Timeout for the Ollama summary call.")
    agent_summarize_log_parser.add_argument("--max-bytes", type=int, default=12000, help="Maximum bytes to read from the log before summarization.")
    agent_summarize_log_parser.add_argument("--json", action="store_true")

    agent_models_parser = agent_subparsers.add_parser("models", help="List local Ollama models, if Ollama is available.")
    agent_models_parser.add_argument("--ollama-host", default="http://localhost:11434", help="Ollama base URL.")
    agent_models_parser.add_argument("--ollama-timeout-seconds", type=float, default=8.0, help="Timeout for Ollama model listing.")
    agent_models_parser.add_argument("--json", action="store_true")

    skill = subparsers.add_parser("skill", help="Local Promptbranch skill registry commands.")
    skill_subparsers = skill.add_subparsers(dest="skill_command", required=True)

    skill_list_parser = skill_subparsers.add_parser("list", help="List built-in and local skills.")
    skill_list_parser.add_argument("--path", default=".", help="Repo path used to discover local .promptbranch/skills.")
    skill_list_parser.add_argument("--json", action="store_true")

    skill_show_parser = skill_subparsers.add_parser("show", help="Show a skill by name or path.")
    skill_show_parser.add_argument("skill", help="Skill name or path, for example repo-inspection.")
    skill_show_parser.add_argument("--path", default=".", help="Repo path used to discover local .promptbranch/skills.")
    skill_show_parser.add_argument("--no-content", action="store_true", help="Omit SKILL.md content from JSON output.")
    skill_show_parser.add_argument("--json", action="store_true")

    skill_validate_parser = skill_subparsers.add_parser("validate", help="Validate a skill by name or path.")
    skill_validate_parser.add_argument("skill", help="Skill name or path, for example .promptbranch/skills/repo-inspection.")
    skill_validate_parser.add_argument("--path", default=".", help="Repo path used to discover local .promptbranch/skills.")
    skill_validate_parser.add_argument("--json", action="store_true")

    mcp = subparsers.add_parser("mcp", help="MCP tool surface helpers.")
    mcp_subparsers = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_manifest = mcp_subparsers.add_parser("manifest", help="Emit the Promptbranch MCP tool manifest.")
    mcp_manifest.add_argument("--include-controlled-processes", action="store_true", help="Include the bounded controlled process tool surface in addition to read-only tools.")
    mcp_manifest.add_argument("--include-controlled-writes", dest="include_controlled_processes", action="store_true", help=argparse.SUPPRESS)
    mcp_manifest.add_argument("--json", action="store_true")

    mcp_serve = mcp_subparsers.add_parser("serve", help="Run the read-only Promptbranch MCP stdio server.")
    mcp_serve.add_argument("--path", default=".", help="Repo path exposed to read-only filesystem/git tools. Defaults to current directory.")
    mcp_serve.add_argument("--include-controlled-processes", action="store_true", help="List and allow the bounded controlled process tool surface; source/artifact writes remain blocked.")
    mcp_serve.add_argument("--include-controlled-writes", dest="include_controlled_processes", action="store_true", help=argparse.SUPPRESS)

    mcp_config = mcp_subparsers.add_parser("config", help="Emit an MCP host config snippet for pb mcp serve.")
    mcp_config.add_argument("--path", default=".", help="Repo path exposed to the MCP host. Defaults to current directory.")
    mcp_config.add_argument("--host", default="generic", choices=["generic", "claude-desktop", "cursor"], help="Host label for documentation. Output shape stays mcpServers JSON.")
    mcp_config.add_argument("--server-name", default="promptbranch", help="MCP server name to place under mcpServers.")
    mcp_config.add_argument("--command", dest="mcp_executable", help="Executable used by the MCP host. Defaults to resolving promptbranch to an absolute path when possible.")
    mcp_config.add_argument("--no-resolve-command", action="store_true", help="Do not resolve the MCP executable to an absolute path.")
    mcp_config.add_argument("--include-controlled-processes", action="store_true", help="List the bounded controlled process tool surface in the server manifest; source/artifact writes remain blocked.")
    mcp_config.add_argument("--include-controlled-writes", dest="include_controlled_processes", action="store_true", help=argparse.SUPPRESS)
    mcp_config.add_argument("--json", action="store_true", help="Emit metadata and config as JSON. Without this flag, print only the config snippet.")

    mcp_host_smoke_parser = mcp_subparsers.add_parser("host-smoke", help="Launch the generated MCP host config and verify read-only tool calls.")
    mcp_host_smoke_parser.add_argument("--path", default=".", help="Repo path exposed to the MCP host. Defaults to current directory.")
    mcp_host_smoke_parser.add_argument("--host", default="generic", choices=["generic", "claude-desktop", "cursor"], help="Host label for diagnostics. Output shape stays mcpServers JSON.")
    mcp_host_smoke_parser.add_argument("--server-name", default="promptbranch", help="MCP server name to place under mcpServers.")
    mcp_host_smoke_parser.add_argument("--command", dest="mcp_executable", help="Executable used by the MCP host. Defaults to resolving promptbranch to an absolute path when possible.")
    mcp_host_smoke_parser.add_argument("--no-resolve-command", action="store_true", help="Do not resolve the MCP executable to an absolute path.")
    mcp_host_smoke_parser.add_argument("--include-controlled-processes", action="store_true", help="List the bounded controlled process tool surface in the server manifest; source/artifact writes remain blocked.")
    mcp_host_smoke_parser.add_argument("--include-controlled-writes", dest="include_controlled_processes", action="store_true", help=argparse.SUPPRESS)
    mcp_host_smoke_parser.add_argument("--timeout-seconds", type=float, default=8.0, help="Timeout for the host-smoke stdio subprocess.")
    mcp_host_smoke_parser.add_argument("--json", action="store_true", help="Emit the full host-smoke result as JSON.")

    test = subparsers.add_parser("test", help="Reliability test commands.")
    test_subparsers = test.add_subparsers(dest="test_command", required=True)
    test_smoke = test_subparsers.add_parser("smoke", help="Run the standard Promptbranch smoke suite.")
    test_smoke.add_argument("--json", action="store_true", help="Emit the full test-suite summary as JSON.")
    test_smoke.add_argument("--keep-open", action="store_true", help="Keep the browser open between steps where supported.")
    test_smoke.add_argument("--keep-project", action="store_true", help="Do not delete the test project at the end.")
    test_smoke.add_argument("--step-delay-seconds", type=float, default=8.0, help="Delay inserted before each step after the first to reduce ChatGPT rate-limit pressure.")
    test_smoke.add_argument("--post-ask-delay-seconds", type=float, default=20.0, help="Additional cooldown after ask steps before reading task/conversation history.")
    test_smoke.add_argument("--rate-limit-safe", dest="rate_limit_safe", action="store_true", default=None, help="Use conservative live-browser pacing for ChatGPT conversation-history rate limits.")
    test_smoke.add_argument("--no-rate-limit-safe", dest="rate_limit_safe", action="store_false", help="Disable conservative live-browser pacing.")
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


    test_browser = test_subparsers.add_parser("browser", help="Run the browser/project/source/task integration test profile.")
    _add_test_suite_profile_options(test_browser)

    test_agent = test_subparsers.add_parser("agent", help="Run the local MCP/agent/skill/controlled-process/package hygiene test profile.")
    _add_test_suite_profile_options(test_agent)

    test_full = test_subparsers.add_parser("full", help="Run browser and agent test profiles through one command.")
    _add_test_suite_profile_options(test_full)

    test_report = test_subparsers.add_parser("report", help="Summarize a pb test-suite / pb test full JSON log.")
    test_report.add_argument("log", help="Path to a log produced by pb test-suite --json or pb test full --json.")
    test_report.add_argument("--service-log", help="Optional Docker/service log to scan for rate-limit modal/429 evidence.")
    test_report.add_argument("--json", action="store_true", help="Emit the machine-readable report as JSON.")

    test_status = test_subparsers.add_parser("status", help="Show the last known full-suite status from local logs without rerunning tests.")
    test_status.add_argument("--path", default=".", help="Directory to scan for pb_test.full*.log files; defaults to current directory.")
    test_status.add_argument("--log", help="Explicit full-suite log to use instead of scanning --path.")
    test_status.add_argument("--service-log", help="Optional Docker/service log to scan alongside the selected test log.")
    test_status.add_argument("--json", action="store_true", help="Emit the machine-readable status as JSON.")

    test_import_smoke = test_subparsers.add_parser("import-smoke", help="Verify installed Promptbranch package modules import from outside the source tree.")
    test_import_smoke.add_argument("--path", default=".", help="Repo path containing pyproject.toml; defaults to current directory.")
    test_import_smoke.add_argument("--python-executable", help="Python executable to use for the isolated import subprocess. Defaults to the current interpreter.")
    test_import_smoke.add_argument("--json", action="store_true", help="Emit the import-smoke result as JSON.")

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
    source_add.add_argument("file_path", nargs="?", help="Local file path for file sources. Equivalent to --file.")
    source_add.add_argument("--type", choices=["link", "text", "file"], default="file")
    source_add.add_argument("--value", help="Source payload for link/text sources.")
    source_add.add_argument("--file", help="Local file path for file sources.")
    source_add.add_argument("--name", help="Optional display name/title to set when the UI supports it.")
    source_add.add_argument("--no-overwrite", action="store_true", help="Do not replace an existing file source with the same display name.")
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
    chat_list.add_argument("--deep-history", action="store_true", help="Also scan global conversation history. Slow and may trigger ChatGPT 429s; normally unnecessary when project backend/indexed sources work.")

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
    test_suite.add_argument("--profile", choices=["browser", "agent", "full"], default="browser", help="Test profile: browser keeps the existing live integration suite; agent runs local MCP/agent/skill/package checks; full runs both.")
    test_suite.add_argument("--path", default=".", help="Repo path used by agent/full profiles. Defaults to current directory.")
    test_suite.add_argument("--package-zip", help="Optional release ZIP path for package hygiene checks in agent/full profiles.")
    test_suite.add_argument("--keep-open", action="store_true", help="Keep the browser open between steps where supported.")
    test_suite.add_argument("--keep-project", action="store_true", help="Do not delete the test project at the end.")
    test_suite.add_argument("--step-delay-seconds", type=float, default=8.0, help="Delay inserted before each step after the first to reduce ChatGPT rate-limit pressure.")
    test_suite.add_argument("--post-ask-delay-seconds", type=float, default=20.0, help="Additional cooldown after ask steps before reading task/conversation history.")
    test_suite.add_argument("--rate-limit-safe", dest="rate_limit_safe", action="store_true", default=None, help="Use conservative live-browser pacing for ChatGPT conversation-history rate limits. Default for full profile.")
    test_suite.add_argument("--no-rate-limit-safe", dest="rate_limit_safe", action="store_false", help="Disable conservative full-profile pacing.")
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
    ask.add_argument("--prompt-file", help="Read additional prompt text from a UTF-8 file. If prompt text is also provided, both are joined with a blank line.")
    ask.add_argument("--file", help="Legacy single chat attachment. Prefer repeatable --attach for multiple files.")
    ask.add_argument("--attach", "--attachment", dest="attachments", action="append", default=[], help="Attach a local file to this chat message without adding it to Project Sources. May be repeated.")
    ask.add_argument("--json", action="store_true", help="Request strict JSON mode.")
    ask.add_argument("--conversation-url", help="Continue a specific ChatGPT conversation URL instead of the project home or remembered conversation.")
    ask.add_argument("--protocol", action="store_true", help="Wrap the prompt in a Promptbranch ask.request envelope.")
    ask.add_argument("--from-current-baseline", action="store_true", help="Build protocol artifact fields from pb artifact current. Currently implied by --protocol.")
    ask.add_argument("--target-version", help="Target output version to include in the protocol request envelope.")
    ask.add_argument("--release-type", choices=["normal", "repair"], default="normal", help="Release type to include in the protocol request envelope.")
    ask.add_argument("--request-id", help="Explicit protocol request_id. Defaults to a generated timestamp id.")
    ask.add_argument("--correlation-id", help="Explicit protocol correlation_id. Defaults to request_id.")
    ask.add_argument("--intent-kind", default="software_release_request", help="Protocol intent.kind. Defaults to software_release_request.")
    ask.add_argument("--print-request-json", action="store_true", help="Print the built protocol request envelope without sending the ask.")
    ask.add_argument("--parse-reply", action="store_true", help="After a protocol ask, fetch the latest answer and validate the Promptbranch reply envelope. No artifact intake is performed.")
    ask.add_argument("--protocol-timeout-seconds", type=float, default=DEFAULT_PROTOCOL_ASK_TIMEOUT_SECONDS, help="Bounded timeout for protocol ask/parse-reply service calls. Defaults to 120 seconds.")
    ask.add_argument("--protocol-fresh-turn-timeout-seconds", type=float, default=DEFAULT_PROTOCOL_FRESH_TURN_TIMEOUT_SECONDS, help="Seconds to poll after submit until a fresh user turn or request_id-matched turn is visible. Defaults to 12 seconds.")
    ask.add_argument("--protocol-fresh-turn-poll-seconds", type=float, default=DEFAULT_PROTOCOL_FRESH_TURN_POLL_SECONDS, help="Polling interval for fresh-turn visibility after protocol submit. Defaults to 1 second.")
    ask.add_argument("--answer-index", help="Assistant answer index to parse after --parse-reply. Defaults to latest.")
    ask.add_argument("--answer-id", help="Assistant answer id or unique prefix to parse after --parse-reply.")
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

def _debug_option_was_provided(argv: list[str]) -> bool:
    return any(token == "--debug" or token.startswith("--debug=") for token in argv)


def _json_output_requested(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False))



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
    if args.command == "test" and getattr(args, "test_command", None) == "report":
        return await cmd_test_report(args)
    if args.command == "test" and getattr(args, "test_command", None) == "status":
        return await cmd_test_status(args)
    if args.command == "test" and getattr(args, "test_command", None) == "import-smoke":
        return await cmd_test_import_smoke(args)

    _apply_protocol_timeout(args)
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
    if args.command == "agent":
        return await cmd_agent(backend, args)
    if args.command == "skill":
        return await cmd_skill(backend, args)
    if args.command == "mcp":
        return await cmd_mcp(backend, args)
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
    debug_option_provided = _debug_option_was_provided(normalized_argv)
    if _json_output_requested(args) and not debug_option_provided:
        args.debug = False
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

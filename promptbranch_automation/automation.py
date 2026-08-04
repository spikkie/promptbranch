from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Any, Optional, Sequence

from promptbranch_browser_auth import ChatGPTBrowserClient, ChatGPTBrowserConfig
from promptbranch_project_delete_safety import project_delete_disabled_result, validate_ephemeral_test_project_cleanup_request


_JSON_PROMPT_DEFAULT_RULES = """
JSON GENERATION STRICT RULES:

    Your goal is to generate exactly one valid JSON object.

    JSON must be strictly valid (Python json.loads() must parse it without error).

    Do not add explanation, comments, markdown outside the code block, or any extra text.

    Include the key-value pair "finished": "finished" as the last field in the JSON object.

    Wrap the JSON inside a single ```json code block.

    After generating the JSON: stop immediately. Do not repeat the JSON or add examples.

JSON GENERATION ADDITIONAL RULES:

    All keys must use double quotes.

    No trailing commas.

    Return only the JSON code block.
"""
_JSON_PROMPT_END_STATEMENT = """

    --- END OF INSTRUCTION ---
"""


def _read_secret_file(path_value: str) -> str:
    secret_path = Path(path_value).expanduser().resolve()
    if not secret_path.exists():
        raise FileNotFoundError(f"Password file does not exist: {secret_path}")
    if not secret_path.is_file():
        raise ValueError(f"Password path is not a file: {secret_path}")
    secret_value = secret_path.read_text(encoding="utf-8").strip()
    if not secret_value:
        raise ValueError(f"Password file is empty: {secret_path}")
    return secret_value


def _resolve_password_file_path(explicit_password_file: Optional[str] = None) -> Optional[str]:
    env_candidates = [
        explicit_password_file,
        os.getenv("CHATGPT_PASSWORD_FILE"),
        os.getenv("CHATGPT_PASSWORD_SECRET_FILE"),
        os.getenv("GOOGLE_PASSWORD_FILE"),
        os.getenv("PASSWORD_FILE"),
    ]
    first_candidate: Optional[str] = None
    for candidate in env_candidates:
        if not candidate:
            continue
        resolved = str(Path(candidate).expanduser().resolve())
        if first_candidate is None:
            first_candidate = resolved
        if Path(resolved).exists() and Path(resolved).is_file():
            return resolved

    default_candidates = [
        Path("/run/secrets/chatgpt_password"),
        Path("~/.config/chatgpt/password.txt"),
        Path("~/.config/chatgpt/google_password.txt"),
        Path("~/.config/bonnetjesapp/chatgpt_password.txt"),
        Path("~/.secrets/chatgpt_password.txt"),
        Path("~/.chatgpt_password"),
    ]
    for candidate in default_candidates:
        resolved = candidate.expanduser().resolve()
        if resolved.exists() and resolved.is_file():
            return str(resolved)

    return first_candidate


def _resolve_password(password: Optional[str], password_file: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if password:
        return password, "direct"

    resolved_password_file = _resolve_password_file_path(password_file)
    if not resolved_password_file:
        return None, None

    return _read_secret_file(resolved_password_file), resolved_password_file




def _split_browser_args(value: Optional[str]) -> tuple[str, ...]:
    text = str(value or "").strip()
    if not text:
        return ()
    try:
        return tuple(shlex.split(text))
    except ValueError:
        return tuple(part for part in text.split() if part)

def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class ChatGPTAutomation:
    def __init__(
        self,
        project_url: str,
        email: Optional[str],
        password: Optional[str],
        profile_dir: str = "/app/.pb_profile",
        *,
        headless: Optional[bool] = None,
        use_patchright: Optional[bool] = None,
        browser_channel: Optional[str] = None,
        navigation_timeout_ms: Optional[int] = None,
        response_timeout_ms: Optional[int] = None,
        manual_login_timeout_ms: Optional[int] = None,
        slow_mo_ms: int = 0,
        debug: Optional[bool] = None,
        debug_artifact_dir: Optional[str] = None,
        save_trace: Optional[bool] = None,
        save_html: Optional[bool] = None,
        save_screenshot: Optional[bool] = None,
        disable_fedcm: Optional[bool] = None,
        fail_fast_on_challenge: Optional[bool] = None,
        filter_no_sandbox: Optional[bool] = None,
        password_file: Optional[str] = None,
        min_context_spacing_seconds: Optional[float] = None,
        conversation_history_rate_limit_cooldown_seconds: Optional[float] = None,
        rate_limit_modal_wait_timeout_ms: Optional[int] = None,
        rate_limit_modal_poll_interval_ms: Optional[int] = None,
        conversation_history_request_shield_mode: Optional[str] = None,
        clear_singleton_locks: Optional[bool] = None,
        dom_diagnostic_mode: Optional[str] = None,
        pause_before_fill: Optional[bool] = None,
        pause_after_fill: Optional[bool] = None,
        pause_before_submit: Optional[bool] = None,
        extra_browser_args: Optional[Sequence[str]] = None,
    ):
        self.project_url = project_url
        self.email = email
        self.password, self.password_source = _resolve_password(password, password_file)
        self.password_file = None if self.password_source in {None, "direct"} else self.password_source
        self.profile_dir = profile_dir
        self.headless = _env_flag("CHATGPT_HEADLESS", False) if headless is None else headless
        self.use_patchright = (
            _env_flag("CHATGPT_USE_PATCHRIGHT", True)
            if use_patchright is None
            else use_patchright
        )
        env_channel = os.getenv("CHATGPT_BROWSER_CHANNEL")
        self.browser_channel = browser_channel or env_channel
        if self.use_patchright and not self.browser_channel:
            self.browser_channel = "chrome"
        self.navigation_timeout_ms = navigation_timeout_ms or int(
            os.getenv("CHATGPT_NAVIGATION_TIMEOUT_MS", "45000")
        )
        self.response_timeout_ms = response_timeout_ms or int(
            os.getenv("CHATGPT_RESPONSE_TIMEOUT_MS", "1800000")
        )
        self.manual_login_timeout_ms = manual_login_timeout_ms or int(
            os.getenv("CHATGPT_MANUAL_LOGIN_TIMEOUT_MS", "600000")
        )
        self.slow_mo_ms = slow_mo_ms or int(os.getenv("CHATGPT_SLOW_MO_MS", "0"))
        self.debug = _env_flag("CHATGPT_DEBUG", True) if debug is None else debug
        self.debug_artifact_dir = debug_artifact_dir or os.getenv(
            "CHATGPT_DEBUG_ARTIFACT_DIR", "debug_artifacts"
        )
        self.save_trace = _env_flag("CHATGPT_SAVE_TRACE", True) if save_trace is None else save_trace
        self.save_html = _env_flag("CHATGPT_SAVE_HTML", True) if save_html is None else save_html
        self.save_screenshot = (
            _env_flag("CHATGPT_SAVE_SCREENSHOT", True)
            if save_screenshot is None
            else save_screenshot
        )
        self.disable_fedcm = (
            _env_flag("CHATGPT_DISABLE_FEDCM", False)
            if disable_fedcm is None
            else disable_fedcm
        )
        self.fail_fast_on_challenge = (
            _env_flag("CHATGPT_FAIL_FAST_ON_CHALLENGE", False)
            or _env_flag("PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE", False)
            if fail_fast_on_challenge is None
            else bool(fail_fast_on_challenge)
        )
        self.filter_no_sandbox = (
            _env_flag("CHATGPT_FILTER_NO_SANDBOX", True)
            if filter_no_sandbox is None
            else filter_no_sandbox
        )
        self.min_context_spacing_seconds = (
            float(os.getenv("CHATGPT_MIN_CONTEXT_SPACING_SECONDS", "8.0"))
            if min_context_spacing_seconds is None
            else float(min_context_spacing_seconds)
        )
        self.conversation_history_rate_limit_cooldown_seconds = (
            float(os.getenv("CHATGPT_CONVERSATION_HISTORY_RATE_LIMIT_COOLDOWN_SECONDS", "180.0"))
            if conversation_history_rate_limit_cooldown_seconds is None
            else float(conversation_history_rate_limit_cooldown_seconds)
        )
        self.rate_limit_modal_wait_timeout_ms = (
            int(os.getenv("CHATGPT_RATE_LIMIT_MODAL_WAIT_TIMEOUT_MS", "180000"))
            if rate_limit_modal_wait_timeout_ms is None
            else int(rate_limit_modal_wait_timeout_ms)
        )
        self.rate_limit_modal_poll_interval_ms = (
            int(os.getenv("CHATGPT_RATE_LIMIT_MODAL_POLL_INTERVAL_MS", "1000"))
            if rate_limit_modal_poll_interval_ms is None
            else int(rate_limit_modal_poll_interval_ms)
        )
        self.conversation_history_request_shield_mode = (
            os.getenv("CHATGPT_CONVERSATION_HISTORY_REQUEST_SHIELD_MODE", "fulfill_empty")
            if conversation_history_request_shield_mode is None
            else str(conversation_history_request_shield_mode)
        )
        self.clear_singleton_locks = (
            _env_flag("CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS", False)
            if clear_singleton_locks is None
            else bool(clear_singleton_locks)
        )
        self.dom_diagnostic_mode = (
            os.getenv("CHATGPT_DOM_DIAGNOSTIC_MODE", "light")
            if dom_diagnostic_mode is None
            else str(dom_diagnostic_mode)
        ).strip().lower()
        self.pause_before_fill = (
            _env_flag("CHATGPT_PAUSE_BEFORE_FILL", False)
            if pause_before_fill is None
            else bool(pause_before_fill)
        )
        self.pause_after_fill = (
            _env_flag("CHATGPT_PAUSE_AFTER_FILL", False)
            if pause_after_fill is None
            else bool(pause_after_fill)
        )
        self.pause_before_submit = (
            _env_flag("CHATGPT_PAUSE_BEFORE_SUBMIT", False)
            if pause_before_submit is None
            else bool(pause_before_submit)
        )
        self.extra_browser_args = tuple(
            extra_browser_args
            if extra_browser_args is not None
            else _split_browser_args(os.getenv("CHATGPT_BROWSER_EXTRA_ARGS"))
        )

    @property
    def client(self) -> ChatGPTBrowserClient:
        return ChatGPTBrowserClient(
            ChatGPTBrowserConfig(
                project_url=self.project_url,
                email=self.email,
                password=self.password,
                profile_dir=self.profile_dir,
                headless=self.headless,
                browser_channel=self.browser_channel,
                no_viewport=(True if self.use_patchright else None),
                challenge_wait_timeout_ms=int(os.getenv("CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS", "20000")),
                use_patchright=self.use_patchright,
                navigation_timeout_ms=self.navigation_timeout_ms,
                response_timeout_ms=self.response_timeout_ms,
                manual_login_timeout_ms=self.manual_login_timeout_ms,
                slow_mo_ms=self.slow_mo_ms,
                debug=self.debug,
                debug_artifact_dir=self.debug_artifact_dir,
                save_trace=self.save_trace,
                save_html=self.save_html,
                save_screenshot=self.save_screenshot,
                disable_fedcm=self.disable_fedcm,
                fail_fast_on_challenge=self.fail_fast_on_challenge,
                filter_no_sandbox=self.filter_no_sandbox,
                min_context_spacing_seconds=self.min_context_spacing_seconds,
                conversation_history_rate_limit_cooldown_seconds=self.conversation_history_rate_limit_cooldown_seconds,
                rate_limit_modal_wait_timeout_ms=self.rate_limit_modal_wait_timeout_ms,
                rate_limit_modal_poll_interval_ms=self.rate_limit_modal_poll_interval_ms,
                conversation_history_request_shield_mode=self.conversation_history_request_shield_mode,
                clear_singleton_locks=self.clear_singleton_locks,
                dom_diagnostic_mode=self.dom_diagnostic_mode,
                pause_before_fill=self.pause_before_fill,
                pause_after_fill=self.pause_after_fill,
                pause_before_submit=self.pause_before_submit,
                extra_browser_args=self.extra_browser_args,
            )
        )

    async def ask_question(
        self,
        prompt: str,
        file_path: Optional[str] = None,
        attachment_paths: Optional[list[str]] = None,
        expect_json: bool = False,
        keep_open: bool = False,
        service_timeout_seconds: Optional[float] = None,
        prefer_button_submit: bool = False,
    ) -> Any:
        result = await self.ask_question_result(
            prompt=prompt,
            file_path=file_path,
            attachment_paths=attachment_paths,
            expect_json=expect_json,
            keep_open=keep_open,
            service_timeout_seconds=service_timeout_seconds,
            prefer_button_submit=prefer_button_submit,
        )
        return result["answer"]

    async def ask_question_result(
        self,
        prompt: str,
        file_path: Optional[str] = None,
        attachment_paths: Optional[list[str]] = None,
        conversation_url: str | None = None,
        expect_json: bool = False,
        keep_open: bool = False,
        service_timeout_seconds: Optional[float] = None,
        prefer_button_submit: bool = False,
    ) -> dict[str, Any]:
        if expect_json:
            prompt = prompt + _JSON_PROMPT_DEFAULT_RULES + _JSON_PROMPT_END_STATEMENT

        return await self.client.ask_question_result(
            prompt=prompt,
            file_path=file_path,
            attachment_paths=attachment_paths,
            conversation_url=conversation_url,
            expect_json=expect_json,
            keep_open=keep_open,
            service_timeout_seconds=service_timeout_seconds,
            prefer_button_submit=prefer_button_submit,
        )

    async def run_login_check(self, keep_open: bool = False) -> dict[str, Any]:
        return await self.client.run_login_check(keep_open=keep_open)

    async def run_passive_auth_readiness(self, keep_open: bool = False) -> dict[str, Any]:
        return await self.client.run_passive_auth_readiness(keep_open=keep_open)

    async def auth_readiness_session_status(self) -> dict[str, Any]:
        return await self.client.auth_readiness_session_status()

    async def list_projects(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.list_projects(
            keep_open=keep_open,
        )

    async def list_project_chats(
        self,
        *,
        keep_open: bool = False,
        include_history_fallback: bool = True,
    ) -> dict[str, Any]:
        return await self.client.list_project_chats(
            keep_open=keep_open,
            include_history_fallback=include_history_fallback,
        )

    async def list_project_sources(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.list_project_sources(
            keep_open=keep_open,
        )

    async def get_chat(
        self,
        *,
        conversation_url: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.get_chat(
            conversation_url=conversation_url,
            keep_open=keep_open,
        )

    async def download_chat_artifact(
        self,
        *,
        conversation_url: str,
        artifact_url: str | None,
        filename: str,
        target_path: str,
        timeout_seconds: float = 120.0,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.download_chat_artifact(
            conversation_url=conversation_url,
            artifact_url=artifact_url,
            filename=filename,
            target_path=target_path,
            timeout_seconds=timeout_seconds,
            keep_open=keep_open,
        )

    async def debug_project_list(
        self,
        *,
        scroll_rounds: int = 12,
        wait_ms: int = 350,
        manual_pause: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.debug_project_list(
            scroll_rounds=scroll_rounds,
            wait_ms=wait_ms,
            manual_pause=manual_pause,
            keep_open=keep_open,
        )

    async def debug_project_chats(
        self,
        *,
        scroll_rounds: int = 20,
        wait_ms: int = 600,
        include_history: bool = True,
        history_max_pages: int = 5,
        history_max_detail_probes: int = 80,
        manual_pause: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.debug_project_chats(
            scroll_rounds=scroll_rounds,
            wait_ms=wait_ms,
            include_history=include_history,
            history_max_pages=history_max_pages,
            history_max_detail_probes=history_max_detail_probes,
            manual_pause=manual_pause,
            keep_open=keep_open,
        )

    async def debug_rate_limit(
        self,
        *,
        keep_open: bool = False,
        probe_backend: bool = False,
        wait_ms: int = 750,
    ) -> dict[str, Any]:
        return await self.client.debug_rate_limit(
            keep_open=keep_open,
            probe_backend=probe_backend,
            wait_ms=wait_ms,
        )

    async def release_live_bootstrap_and_ask(
        self,
        *,
        project_name: str,
        bootstrap_prompt: str,
        ask_prompt: str,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "project-only",
        service_timeout_seconds: Optional[float] = None,
        warmup_conversation_url: Optional[str] = None,
    ) -> dict[str, Any]:
        return await self.client.release_live_bootstrap_and_ask(
            project_name=project_name,
            bootstrap_prompt=bootstrap_prompt,
            ask_prompt=ask_prompt,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            service_timeout_seconds=service_timeout_seconds,
            warmup_conversation_url=warmup_conversation_url,
        )

    async def create_project(
        self,
        *,
        name: str,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        memory_mode: str = "default",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.create_project(
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
        )

    async def resolve_project(
        self,
        *,
        name: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.resolve_project(
            name=name,
            keep_open=keep_open,
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
        return await self.client.ensure_project(
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
        )

    async def remove_project(
        self,
        *,
        keep_open: bool = False,
        project_name: Optional[str] = None,
        project_url: Optional[str] = None,
        allow_ephemeral_test_cleanup: bool = False,
        created_project_url: Optional[str] = None,
        created_project_name: Optional[str] = None,
        created_project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        effective_project_url = project_url or self.project_url
        validation = validate_ephemeral_test_project_cleanup_request(
            allow_ephemeral_test_cleanup=allow_ephemeral_test_cleanup,
            project_url=effective_project_url,
            project_name=project_name,
            created_project_url=created_project_url,
            created_project_name=created_project_name,
            created_project_id=created_project_id,
        )
        return project_delete_disabled_result(
            project_url=effective_project_url,
            project_name=project_name,
            blocked_at_layer="automation_wrapper",
            validation=validation,
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
        transaction_mode: str = "current",
        protected_release_version: Optional[str] = None,
        protected_release_filename: Optional[str] = None,
    ) -> dict[str, Any]:
        return await self.client.add_project_source(
            source_kind=source_kind,
            value=value,
            file_path=file_path,
            display_name=display_name,
            keep_open=keep_open,
            overwrite_existing=overwrite_existing,
            transaction_mode=transaction_mode,
            protected_release_version=protected_release_version,
            protected_release_filename=protected_release_filename,
        )

    async def run_library_backend_protocol_reupload_diagnostic(
        self,
        *,
        project_name_prefix: str = "itest-pb-library-backend",
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.run_library_backend_protocol_reupload_diagnostic(
            project_name_prefix=project_name_prefix,
            keep_open=keep_open,
        )

    async def delete_library_backing_object_diagnostic(
        self,
        *,
        processed_file_id: str,
        library_metadata_object_id: str,
        filename: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.delete_library_backing_object_diagnostic(
            processed_file_id=processed_file_id,
            library_metadata_object_id=library_metadata_object_id,
            filename=filename,
            keep_open=keep_open,
        )

    async def discover_project_source_capabilities(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.discover_project_source_capabilities(
            keep_open=keep_open,
        )

    async def remove_project_source(
        self,
        *,
        source_name: str,
        exact: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        return await self.client.remove_project_source(
            source_name=source_name,
            exact=exact,
            keep_open=keep_open,
        )


async def ask_chatgpt(
    project_url: str,
    email: Optional[str],
    password: Optional[str],
    prompt: str,
    file_path: Optional[str] = None,
    conversation_url: Optional[str] = None,
    expect_json: bool = False,
    profile_dir: str = "/app/.pb_profile",
    *,
    headless: Optional[bool] = None,
    use_patchright: Optional[bool] = None,
    browser_channel: Optional[str] = None,
    password_file: Optional[str] = None,
    disable_fedcm: Optional[bool] = None,
    filter_no_sandbox: Optional[bool] = None,
) -> Any:
    bot = ChatGPTAutomation(
        project_url=project_url,
        email=email,
        password=password,
        profile_dir=profile_dir,
        headless=headless,
        use_patchright=use_patchright,
        browser_channel=browser_channel,
        password_file=password_file,
        disable_fedcm=disable_fedcm,
        filter_no_sandbox=filter_no_sandbox,
    )
    result = await bot.ask_question_result(
        prompt=prompt,
        file_path=file_path,
        conversation_url=conversation_url,
        expect_json=expect_json,
    )
    return result["answer"]

from __future__ import annotations

import asyncio
import json
import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse, urlunparse

from .config import ChatGPTBrowserConfig
from .exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
)

LOGIN_BUTTON_SELECTOR = 'button[data-testid="login-button"]'
LOGIN_BUTTON_SELECTORS = [
    'button[data-testid="login-button"]',
    'header button:has-text("Log in")',
    'button:has-text("Log in")',
]
SIGNUP_BUTTON_SELECTORS = [
    'button[data-testid="signup-button"]',
    'button:has-text("Sign up for free")',
]
ANONYMOUS_STATE_SELECTORS = [
    'text=Get responses tailored to you',
    'text=Log in to get answers based on saved chats',
]
COOKIE_BANNER_SELECTORS = [
    'button:has-text("Accept all")',
    'button:has-text("Reject non-essential")',
    'button[data-testid="close-button"]',
]
CHAT_INPUT_SELECTORS = [
    '#prompt-textarea',
    'div[contenteditable="true"]#prompt-textarea',
    'div[contenteditable="true"][data-testid="composer"]',
    'div[contenteditable="true"]',
    'textarea[placeholder]',
    'textarea',
]
AUTHENTICATED_INDICATORS = [
    'button[data-testid="profile-button"]',
    '[data-testid="user-menu-button"]',
    '[data-testid="share-chat-button"]',
    'nav button[aria-haspopup="menu"]:not([aria-label="Help"]):not([aria-label="Model selector"])',
]
ASSISTANT_MESSAGE_SELECTORS = [
    '[data-message-author-role="assistant"]',
    'article[data-testid*="conversation-turn"]',
    'div[data-testid*="conversation-turn"]',
    'main article',
    'main [role="article"]',
]
PRIMARY_ASSISTANT_MESSAGE_SELECTOR = ASSISTANT_MESSAGE_SELECTORS[0]
COMPOSER_SUBMIT_BUTTON_SELECTORS = [
    '#composer-submit-button',
    'button[data-testid="send-button"]',
    'button[aria-label="Send prompt"]',
]
COMPOSER_STOP_BUTTON_SELECTORS = [
    '#thread-bottom #composer-submit-button[data-testid="stop-button"]',
    '#thread-bottom button[data-testid="stop-button"]',
    '#thread-bottom button[aria-label*="Stop" i]',
]
COMPOSER_SEND_READY_SELECTORS = [
    '#thread-bottom #composer-submit-button[data-testid="send-button"]',
    '#thread-bottom #composer-submit-button[aria-label="Send prompt"]',
    '#thread-bottom button[data-testid="send-button"]',
    '#thread-bottom button[aria-label="Send prompt"]',
]
COMPOSER_IDLE_INDICATOR_SELECTORS = [
    '#thread-bottom button[aria-label="Start Voice"]',
    '#thread-bottom button[aria-label="Start dictation"]',
    '#thread-bottom #prompt-textarea',
]
SEND_READY_ARIA_HINTS = ('send prompt', 'send')
SEND_READY_ID_HINTS = ('composer-submit-button', 'send-button')
SEND_READY_CLASS_HINTS = ('composer-submit', 'send-button')
STOP_GENERATING_ARIA_HINTS = ('stop', 'stop generating', 'stop streaming')
STOP_GENERATING_CLASS_HINTS = ('stop', 'square')
ASSISTANT_TURN_SCOPE_SELECTORS = [
    'section[data-turn="assistant"]',
    '[data-testid*="conversation-turn"][data-turn="assistant"]',
    'section:has([data-message-author-role="assistant"])',
    '[data-message-author-role="assistant"]',
]
THINKING_MARKER_SELECTORS = [
    '[data-testid*="thinking"]',
    '[aria-label*="Thinking"]',
]
THINKING_TEXT_PATTERNS = [
    re.compile(r'^\s*Thinking(?:\s|$)', re.IGNORECASE),
]
PROJECT_SOURCES_TAB_SELECTORS = [
    '[role="tab"]:has-text("Sources")',
    'button:has-text("Sources")',
    'a:has-text("Sources")',
]
PROJECT_ADD_SOURCE_BUTTON_SELECTORS = [
    'button:has-text("Add source")',
    'button:has-text("Add Source")',
    '[aria-label*="Add source" i]',
]
PROJECT_SOURCE_DIALOG_SCOPE_SELECTORS = [
    '[role="dialog"]',
    'dialog[open]',
]
PROJECT_SOURCE_LINK_TYPE_SELECTORS = [
    '[role="menuitem"]:has-text("Link")',
    'button:has-text("Link")',
    'button:has-text("Slack")',
    'button:has-text("Google Drive")',
]
PROJECT_SOURCE_TEXT_TYPE_SELECTORS = [
    '[role="menuitem"]:has-text("Text")',
    'button:has-text("Text")',
    'button:has-text("Quick text")',
    'button:has-text("Notes")',
]
PROJECT_SOURCE_FILE_TYPE_SELECTORS = [
    '[role="menuitem"]:has-text("File")',
    'button:has-text("File")',
    'button:has-text("Upload")',
    'button:has-text("Files")',
]
PROJECT_SOURCE_LINK_INPUT_SELECTORS = [
    '[role="dialog"] input[type="url"]',
    '[role="dialog"] input[placeholder*="Paste" i]',
    '[role="dialog"] input[type="text"]',
    'dialog[open] input[type="url"]',
    'dialog[open] input[placeholder*="Paste" i]',
    'dialog[open] input[type="text"]',
]
PROJECT_SOURCE_TEXT_INPUT_SELECTORS = [
    '[role="dialog"] textarea',
    '[role="dialog"] [contenteditable="true"]',
    '[role="dialog"] input[type="text"]',
    'dialog[open] textarea',
    'dialog[open] [contenteditable="true"]',
    'dialog[open] input[type="text"]',
]
PROJECT_SOURCE_TITLE_INPUT_SELECTORS = [
    '[role="dialog"] input[placeholder*="Title" i]',
    '[role="dialog"] input[aria-label*="Title" i]',
    'dialog[open] input[placeholder*="Title" i]',
    'dialog[open] input[aria-label*="Title" i]',
]
PROJECT_SOURCE_FILE_INPUT_SELECTORS = [
    '[role="dialog"] input[type="file"]',
    'dialog[open] input[type="file"]',
    'input[type="file"]',
]
PROJECT_SOURCE_SAVE_BUTTON_SELECTORS = [
    '[role="dialog"] button:has-text("Add")',
    '[role="dialog"] button:has-text("Save")',
    '[role="dialog"] button:has-text("Done")',
    'dialog[open] button:has-text("Add")',
    'dialog[open] button:has-text("Save")',
    'dialog[open] button:has-text("Done")',
]
PROJECT_SOURCE_REMOVE_ACTION_SELECTORS = [
    '[role="menuitem"]:has-text("Remove")',
    '[role="menuitem"]:has-text("Delete")',
    'button:has-text("Remove")',
    'button:has-text("Delete")',
]
PROJECT_SOURCE_CONFIRM_REMOVE_SELECTORS = [
    '[role="dialog"] button:has-text("Remove")',
    '[role="dialog"] button:has-text("Delete")',
    'dialog[open] button:has-text("Remove")',
    'dialog[open] button:has-text("Delete")',
]
PROJECT_SOURCE_OPTIONS_ARIA_HINTS = (
    'options',
    'more',
    'menu',
    'source',
)
PROJECT_SIDEBAR_OPEN_BUTTON_SELECTORS = [
    'button[aria-label="Open sidebar"]',
    'button[aria-label*="Open sidebar" i]',
]
PROJECT_SIDEBAR_CLOSE_BUTTON_SELECTORS = [
    'button[data-testid="close-sidebar-button"]',
    'button[aria-label="Close sidebar"]',
    'button[aria-label*="Close sidebar" i]',
]
PROJECT_NEW_BUTTON_SELECTORS = [
    'button:has-text("New project")',
    'a:has-text("New project")',
    'button[data-sidebar-item="true"]:has-text("New project")',
    'a[data-sidebar-item="true"]:has-text("New project")',
    'nav button:has-text("New project")',
    'aside button:has-text("New project")',
    '[data-testid="new-project-button"]',
    '[aria-label*="New project" i]',
]
PROJECT_SECTION_TOGGLE_SELECTORS = [
    'button:has-text("Projects")',
    '[role="button"]:has-text("Projects")',
    'summary:has-text("Projects")',
]
PROJECT_CREATE_DIALOG_SELECTORS = [
    '[role="dialog"]',
    'dialog[open]',
]
PROJECT_CREATE_NAME_INPUT_SELECTORS = [
    '[role="dialog"] input[placeholder*="project" i]',
    '[role="dialog"] input[aria-label*="project" i]',
    'dialog[open] input[placeholder*="project" i]',
    'dialog[open] input[aria-label*="project" i]',
    '[role="dialog"] input[type="text"]',
    'dialog[open] input[type="text"]',
]
PROJECT_CREATE_SUBMIT_SELECTORS = [
    '[role="dialog"] button:has-text("Create")',
    '[role="dialog"] button:has-text("Done")',
    'dialog[open] button:has-text("Create")',
    'dialog[open] button:has-text("Done")',
]
PROJECT_REMOVE_ACTION_SELECTORS = [
    '[role="menuitem"]:has-text("Delete project")',
    '[role="menuitem"]:has-text("Delete")',
    'button:has-text("Delete project")',
    'button:has-text("Delete")',
]
PROJECT_CONFIRM_REMOVE_SELECTORS = [
    '[role="dialog"] button:has-text("Delete project")',
    '[role="dialog"] button:has-text("Delete")',
    'dialog[open] button:has-text("Delete project")',
    'dialog[open] button:has-text("Delete")',
]
PROJECT_OPTIONS_ARIA_HINTS = (
    'project options',
    'open project options',
    'project menu',
)
PROJECT_MEMORY_PROJECT_ONLY_SELECTORS = [
    '[role="dialog"] label:has-text("Project-only memory")',
    '[role="dialog"] button:has-text("Project-only memory")',
    '[role="dialog"] [role="radio"]:has-text("Project-only memory")',
    '[role="dialog"] [role="option"]:has-text("Project-only memory")',
    'dialog[open] label:has-text("Project-only memory")',
    'dialog[open] button:has-text("Project-only memory")',
    'dialog[open] [role="radio"]:has-text("Project-only memory")',
    'dialog[open] [role="option"]:has-text("Project-only memory")',
]
PROJECT_ICON_CONTROL_SELECTORS = [
    '[role="dialog"] button[aria-label*="icon" i]',
    '[role="dialog"] [role="combobox"][aria-label*="icon" i]',
    '[role="dialog"] button:has-text("Icon")',
    'dialog[open] button[aria-label*="icon" i]',
    'dialog[open] [role="combobox"][aria-label*="icon" i]',
    'dialog[open] button:has-text("Icon")',
]
PROJECT_COLOR_CONTROL_SELECTORS = [
    '[role="dialog"] button[aria-label*="color" i]',
    '[role="dialog"] [role="combobox"][aria-label*="color" i]',
    '[role="dialog"] button:has-text("Color")',
    'dialog[open] button[aria-label*="color" i]',
    'dialog[open] [role="combobox"][aria-label*="color" i]',
    'dialog[open] button:has-text("Color")',
]
PROJECT_VALUE_OPTION_PATTERNS = [
    '[role="option"]:has-text("{value}")',
    '[role="menuitem"]:has-text("{value}")',
    '[role="radio"]:has-text("{value}")',
    'button:has-text("{value}")',
    '[title*="{value}" i]',
    '[aria-label*="{value}" i]',
]
JSON_BLOCK_SELECTORS = [
    '#code-block-viewer .cm-content',
    'code.language-json',
    'div[data-message-author-role="assistant"] pre',
    'div[data-message-author-role="assistant"] code',
]
CLOUDFLARE_CHALLENGE_HINTS = [
    '__cf_chl_rt_tk=',
    'Just a moment',
    'Checking your browser',
    'cf-challenge',
]


class ChatGPTBrowserClient:
    def __init__(self, config: ChatGPTBrowserConfig):
        self.config = config
        self._artifact_dir = Path(self.config.debug_artifact_dir)
        if self.config.debug:
            self._artifact_dir.mkdir(parents=True, exist_ok=True)

    async def run_login_check(self, keep_open: bool = False) -> dict[str, Any]:
        self._log(
            "login-check",
            "starting login check",
            project_url=self.config.project_url,
            profile_dir=self.config.profile_dir,
            headless=self.config.headless,
            driver=self.driver_name,
            channel=self.config.browser_channel or "default",
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="login_check",
            operation=self._run_login_check_operation,
            keep_open=keep_open,
        )

    async def ask_question(
        self,
        prompt: str,
        file_path: Optional[str] = None,
        expect_json: bool = False,
        keep_open: bool = False,
    ) -> Any:
        self._log(
            "ask",
            "starting ask_question",
            project_url=self.config.project_url,
            profile_dir=self.config.profile_dir,
            headless=self.config.headless,
            driver=self.driver_name,
            prompt_length=len(prompt),
            file_path=file_path,
            expect_json=expect_json,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="ask_question",
            operation=self._ask_question_operation,
            prompt=prompt,
            file_path=file_path,
            expect_json=expect_json,
            keep_open=keep_open,
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
        self._log(
            "project-create",
            "starting create_project",
            project_url=self.config.project_url,
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="project_create",
            operation=self._create_project_operation,
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
        self._log(
            "project-resolve",
            "starting resolve_project",
            project_url=self.config.project_url,
            name=name,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="project_resolve",
            operation=self._resolve_project_operation,
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
        self._log(
            "project-ensure",
            "starting ensure_project",
            project_url=self.config.project_url,
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="project_ensure",
            operation=self._ensure_project_operation,
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
    ) -> dict[str, Any]:
        self._log(
            "project-remove",
            "starting remove_project",
            project_url=self.config.project_url,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="project_remove",
            operation=self._remove_project_operation,
            keep_open=keep_open,
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
        self._log(
            "project-source-add",
            "starting add_project_source",
            project_url=self.config.project_url,
            source_kind=source_kind,
            value_preview=self._preview_text(value, 120) if value else None,
            file_path=file_path,
            display_name=display_name,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="project_source_add",
            operation=self._add_project_source_operation,
            source_kind=source_kind,
            value=value,
            file_path=file_path,
            display_name=display_name,
            keep_open=keep_open,
        )

    async def remove_project_source(
        self,
        *,
        source_name: str,
        exact: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        self._log(
            "project-source-remove",
            "starting remove_project_source",
            project_url=self.config.project_url,
            source_name=source_name,
            exact=exact,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="project_source_remove",
            operation=self._remove_project_source_operation,
            source_name=source_name,
            exact=exact,
            keep_open=keep_open,
        )

    @property
    def driver_name(self) -> str:
        return "patchright" if self.config.use_patchright else "playwright"

    async def _run_with_context(self, operation_name: str, operation, **kwargs) -> Any:
        Path(self.config.profile_dir).mkdir(parents=True, exist_ok=True)
        playwright_module = await self._start_driver()
        async with playwright_module as p:
            browser_args = list(self.config.extra_browser_args)
            if self.config.disable_fedcm:
                browser_args.extend([
                    "--disable-features=FedCm,FedCmAutoReauthn,FedCmWithoutThirdPartyCookies,FedCmIdpSigninStatusEnabled,FedCmIdpSigninStatusMetrics",
                    "--disable-blink-features=FedCm",
                ])
            ignore_default_args = []
            if self.config.filter_no_sandbox:
                ignore_default_args.extend(["--no-sandbox", "--disable-setuid-sandbox"])

            self._log(
                "driver",
                "launching persistent chromium context",
                disable_fedcm=self.config.disable_fedcm,
                filter_no_sandbox=self.config.filter_no_sandbox,
                no_viewport=self.config.no_viewport,
                channel=self.config.browser_channel or "default",
                running_as_root=(os.geteuid() == 0 if hasattr(os, "geteuid") else None),
                browser_args=browser_args,
                ignore_default_args=ignore_default_args,
            )
            launch_kwargs = {
                "user_data_dir": self.config.profile_dir,
                "headless": self.config.headless,
                "channel": self.config.browser_channel,
                "slow_mo": self.config.slow_mo_ms,
                "accept_downloads": True,
                "args": browser_args,
                "ignore_default_args": ignore_default_args or None,
            }
            if self.config.no_viewport is True:
                launch_kwargs["no_viewport"] = True
                launch_kwargs["screen"] = {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }
            else:
                launch_kwargs["viewport"] = {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }

            context = await p.chromium.launch_persistent_context(**launch_kwargs)
            context.set_default_timeout(self.config.navigation_timeout_ms)
            page = context.pages[0] if context.pages else await context.new_page()
            self._attach_context_debug(context, page, operation_name)
            if self.config.debug and self.config.save_trace:
                self._log("trace", "starting browser trace")
                await context.tracing.start(screenshots=True, snapshots=True, sources=True)

            try:
                result = await operation(context=context, page=page, **kwargs)
                self._log("result", f"{operation_name} completed", result_type=type(result).__name__)
                return result
            except Exception as exc:
                self._log(
                    "error",
                    f"{operation_name} failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                    current_url=await self._safe_page_url(page),
                )
                await self._dump_failure_artifacts(page, operation_name, exc)
                raise
            finally:
                await self._finalize_context(context, operation_name)

    async def _run_login_check_operation(
        self,
        *,
        context: Any,
        page: Any,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        logged_in = await self.ensure_logged_in(page, context)
        result = {
            "logged_in": logged_in,
            "profile_dir": self.config.profile_dir,
            "headless": self.config.headless,
            "url": self.config.project_url,
            "driver": self.driver_name,
            "debug": self.config.debug,
            "debug_artifact_dir": self.config.debug_artifact_dir,
        }
        self._log("login-check", "login result", **result)
        if keep_open and self.config.is_headed:
            await asyncio.to_thread(
                input,
                "Login check passed. Press Enter to close the browser... ",
            )
        return result

    async def _ask_question_operation(
        self,
        *,
        context: Any,
        page: Any,
        prompt: str,
        file_path: Optional[str],
        expect_json: bool,
        keep_open: bool = False,
    ) -> Any:
        await self.ensure_logged_in(page, context)
        await self._goto(page, self.config.project_url, label="chat-home-after-login")
        input_locator = await self._wait_for_chat_input(page)
        self._log("composer", "chat input resolved; clicking")
        await input_locator.click()
        self._log("composer", "filling prompt", prompt_length=len(prompt))
        await input_locator.fill(prompt)

        if file_path:
            self._log("upload", "upload requested", file_path=file_path)
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)
            file_input = page.locator('input[type="file"]')
            file_count = await file_input.count()
            self._log("upload", "file input selector count", selector='input[type="file"]', count=file_count)
            if not file_count:
                raise ResponseTimeoutError("File upload input was not found")
            await file_input.first.set_input_files(file_path)
            self._log("upload", "file uploaded to browser input", file_path=file_path)

        response_context = await self._capture_response_context(page)
        await self._submit_prompt(page)
        result = (
            await self._wait_and_get_json(page, response_context=response_context)
            if expect_json
            else await self._wait_and_get_response(page, response_context=response_context)
        )
        if keep_open and self.config.is_headed:
            await asyncio.to_thread(
                input,
                "Question completed. Press Enter to close the browser... ",
            )
        return result

    async def _create_project_operation(
        self,
        *,
        context: Any,
        page: Any,
        name: str,
        icon: Optional[str],
        color: Optional[str],
        memory_mode: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        home_url = self._chatgpt_home_url()
        await self._goto(page, home_url, label="project-create-home")
        await self._ensure_sidebar_open(page)

        result = await self._create_project_from_sidebar(
            page,
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
        )
        self._log("project-create", "project created", **result)
        if keep_open and self.config.is_headed:
            await asyncio.to_thread(input, "Project created. Press Enter to close the browser... ")
        return result

    async def _resolve_project_operation(
        self,
        *,
        context: Any,
        page: Any,
        name: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        resolution = await self._resolve_projects_by_name(page, name=name, label="project-resolve-home")
        result = {
            "ok": resolution["error"] is None and resolution["match_count"] == 1,
            "action": "resolve_project",
            "project_name": name,
            "project_url": resolution["project_url"],
            "match_count": resolution["match_count"],
            "matches": resolution["matches"],
            "matched_by": resolution["matched_by"],
            "error": resolution["error"],
            "current_url": await self._safe_page_url(page),
        }
        self._log("project-resolve", "project resolution completed", **result)
        if keep_open and self.config.is_headed:
            await asyncio.to_thread(input, "Project resolution finished. Press Enter to close the browser... ")
        return result

    async def _ensure_project_operation(
        self,
        *,
        context: Any,
        page: Any,
        name: str,
        icon: Optional[str],
        color: Optional[str],
        memory_mode: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        resolution = await self._resolve_projects_by_name(page, name=name, label="project-ensure-home")

        if resolution["match_count"] == 1 and resolution["project_url"]:
            result = {
                "ok": True,
                "action": "ensure_project",
                "project_name": name,
                "project_url": resolution["project_url"],
                "created": False,
                "match_count": 1,
                "matches": resolution["matches"],
                "matched_by": resolution["matched_by"],
                "error": None,
                "current_url": await self._safe_page_url(page),
                "icon": icon,
                "color": color,
                "memory_mode": memory_mode,
                "icon_applied": False,
                "color_applied": False,
                "memory_mode_applied": False,
                "warnings": [],
            }
            self._log("project-ensure", "project already exists", **result)
            if keep_open and self.config.is_headed:
                await asyncio.to_thread(input, "Project already exists. Press Enter to close the browser... ")
            return result

        if resolution["match_count"] > 1:
            result = {
                "ok": False,
                "action": "ensure_project",
                "project_name": name,
                "project_url": None,
                "created": False,
                "match_count": resolution["match_count"],
                "matches": resolution["matches"],
                "matched_by": resolution["matched_by"],
                "error": resolution["error"] or "ambiguous_project_name",
                "current_url": await self._safe_page_url(page),
                "icon": icon,
                "color": color,
                "memory_mode": memory_mode,
                "warnings": ["Multiple existing projects matched the requested exact name."],
            }
            self._log("project-ensure", "project ensure blocked by ambiguity", **result)
            if keep_open and self.config.is_headed:
                await asyncio.to_thread(input, "Project ensure failed. Press Enter to close the browser... ")
            return result

        created = await self._create_project_from_sidebar(
            page,
            name=name,
            icon=icon,
            color=color,
            memory_mode=memory_mode,
        )
        result = {
            **created,
            "action": "ensure_project",
            "created": True,
            "match_count": 0,
            "matches": [],
            "matched_by": None,
            "error": None,
        }
        self._log("project-ensure", "project created during ensure", **result)
        if keep_open and self.config.is_headed:
            await asyncio.to_thread(input, "Project ensured. Press Enter to close the browser... ")
        return result

    async def _create_project_from_sidebar(
        self,
        page: Any,
        *,
        name: str,
        icon: Optional[str],
        color: Optional[str],
        memory_mode: str,
    ) -> dict[str, Any]:

        new_project_button = await self._wait_for_visible_locator(
            page,
            PROJECT_NEW_BUTTON_SELECTORS,
            label="project-new-button",
            total_timeout_ms=20_000,
            poll_interval_ms=500,
            visibility_timeout_ms=1_000,
        )
        if new_project_button is None:
            raise ResponseTimeoutError("New project button did not become visible")
        await new_project_button.click(timeout=5_000)
        await page.wait_for_timeout(750)

        name_input = await self._wait_for_visible_locator(
            page,
            PROJECT_CREATE_NAME_INPUT_SELECTORS,
            label="project-create-name-input",
            total_timeout_ms=10_000,
        )
        if name_input is None:
            raise ResponseTimeoutError("Project name input did not become visible")
        await self._fill_locator_text(name_input, name)

        warnings: list[str] = []
        icon_applied = False
        color_applied = False
        memory_mode_applied = (memory_mode == "default")

        if icon:
            icon_applied = await self._try_select_project_dialog_value(
                page,
                control_selectors=PROJECT_ICON_CONTROL_SELECTORS,
                value=icon,
                label="project-icon",
            )
            if not icon_applied:
                warnings.append(f"Could not apply icon selection: {icon}")

        if color:
            color_applied = await self._try_select_project_dialog_value(
                page,
                control_selectors=PROJECT_COLOR_CONTROL_SELECTORS,
                value=color,
                label="project-color",
            )
            if not color_applied:
                warnings.append(f"Could not apply color selection: {color}")

        if memory_mode == "project-only":
            memory_mode_applied = await self._try_activate_project_only_memory(page)
            if not memory_mode_applied:
                warnings.append("Project-only memory option was not found in the create-project dialog")

        submit_button = await self._wait_for_visible_locator(
            page,
            PROJECT_CREATE_SUBMIT_SELECTORS,
            label="project-create-submit",
            total_timeout_ms=10_000,
        )
        if submit_button is None:
            raise ResponseTimeoutError("Create project submit button did not become visible")

        before_url = await self._safe_page_url(page)
        await submit_button.click(timeout=5_000)
        await page.wait_for_timeout(750)

        project_url = await self._wait_for_created_project_url(page, project_name=name, previous_url=before_url)
        return {
            "ok": True,
            "action": "create_project",
            "project_name": name,
            "project_url": project_url,
            "current_url": await self._safe_page_url(page),
            "icon": icon,
            "color": color,
            "memory_mode": memory_mode,
            "icon_applied": icon_applied,
            "color_applied": color_applied,
            "memory_mode_applied": memory_mode_applied,
            "warnings": warnings,
        }

    async def _remove_project_operation(
        self,
        *,
        context: Any,
        page: Any,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        project_home_url = self._project_home_url()
        await self._goto(page, project_home_url, label="project-remove-home")
        await self._ensure_sidebar_open(page)

        container = await self._find_current_project_sidebar_container(page)
        if container is None:
            raise ResponseTimeoutError("Could not find the configured project in the sidebar")

        options_button = await self._find_project_options_button(container)
        if options_button is None:
            raise ResponseTimeoutError("Could not find the options button for the configured project")
        await options_button.click(timeout=5_000)

        delete_action = await self._wait_for_visible_locator(
            page,
            PROJECT_REMOVE_ACTION_SELECTORS,
            label="project-remove-action",
            total_timeout_ms=8_000,
        )
        if delete_action is None:
            raise ResponseTimeoutError("Could not find the delete action for the configured project")
        await delete_action.click(timeout=5_000)

        confirm_button = await self._wait_for_visible_locator(
            page,
            PROJECT_CONFIRM_REMOVE_SELECTORS,
            label="project-remove-confirm",
            total_timeout_ms=8_000,
        )
        if confirm_button is None:
            raise ResponseTimeoutError("Could not find the delete confirmation button for the configured project")
        await confirm_button.click(timeout=5_000)

        await self._wait_for_project_absence(page, deleted_project_url=project_home_url)
        result = {
            "ok": True,
            "action": "remove_project",
            "deleted_project_url": project_home_url,
            "deleted_project_id": self._extract_project_id_from_url(project_home_url),
            "current_url": await self._safe_page_url(page),
        }
        self._log("project-remove", "project removed", **result)
        if keep_open and self.config.is_headed:
            await asyncio.to_thread(input, "Project removed. Press Enter to close the browser... ")
        return result

    async def _add_project_source_operation(
        self,
        *,
        context: Any,
        page: Any,
        source_kind: str,
        value: Optional[str],
        file_path: Optional[str],
        display_name: Optional[str],
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        project_home_url = self._project_home_url()
        await self._goto(page, project_home_url, label="project-source-add-home")
        await self._open_project_sources_tab(page)

        normalized_kind = (source_kind or "").strip().lower()
        if normalized_kind not in {"link", "text", "file"}:
            raise ValueError(f"Unsupported source kind: {source_kind!r}")

        expected_match: Optional[str]
        if normalized_kind == "file":
            if not file_path:
                raise ValueError("file_path is required when source_kind='file'")
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)
            await self._add_project_file_source(page, file_path=file_path)
            expected_match = display_name or Path(file_path).name
        else:
            if not value:
                raise ValueError(f"value is required when source_kind={normalized_kind!r}")
            await self._add_project_textual_source(
                page,
                source_kind=normalized_kind,
                value=value,
                display_name=display_name,
            )
            expected_match = display_name or self._infer_source_match_text(normalized_kind, value)

        await self._wait_for_source_presence(page, expected_match)
        result = {
            "ok": True,
            "action": "add",
            "project_url": project_home_url,
            "source_kind": normalized_kind,
            "source_match": expected_match,
            "current_url": await self._safe_page_url(page),
        }
        self._log("project-source-add", "project source added", **result)
        if keep_open and self.config.is_headed:
            await asyncio.to_thread(input, "Source added. Press Enter to close the browser... ")
        return result

    async def _remove_project_source_operation(
        self,
        *,
        context: Any,
        page: Any,
        source_name: str,
        exact: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        project_home_url = self._project_home_url()
        await self._goto(page, project_home_url, label="project-source-remove-home")
        await self._open_project_sources_tab(page)

        container = await self._find_project_source_container(page, source_name, exact=exact)
        if container is None:
            raise ResponseTimeoutError(f"Project source was not found: {source_name}")

        options_button = await self._find_source_options_button(container)
        if options_button is None:
            raise ResponseTimeoutError(f"Could not find options button for project source: {source_name}")
        await options_button.click(timeout=5_000)
        remove_button = await self._wait_for_visible_locator(
            page,
            PROJECT_SOURCE_REMOVE_ACTION_SELECTORS,
            label="project-source-remove-action",
            total_timeout_ms=8_000,
        )
        if remove_button is None:
            raise ResponseTimeoutError("Could not find the remove/delete action for the selected project source")
        await remove_button.click(timeout=5_000)

        confirm_button = await self._wait_for_visible_locator(
            page,
            PROJECT_SOURCE_CONFIRM_REMOVE_SELECTORS,
            label="project-source-remove-confirm",
            total_timeout_ms=4_000,
        )
        if confirm_button is not None:
            await confirm_button.click(timeout=5_000)

        await self._wait_for_source_absence(page, source_name, exact=exact)
        result = {
            "ok": True,
            "action": "remove",
            "project_url": project_home_url,
            "source_name": source_name,
            "exact": exact,
            "current_url": await self._safe_page_url(page),
        }
        self._log("project-source-remove", "project source removed", **result)
        if keep_open and self.config.is_headed:
            await asyncio.to_thread(input, "Source removed. Press Enter to close the browser... ")
        return result

    async def ensure_logged_in(self, page: Any, context: Any) -> bool:
        self._log("auth", "checking login state")
        await self._goto(page, self.config.project_url, label="initial-auth-check")
        await self._wait_for_challenge_resolution(page, label="initial-auth-check")
        if await self._is_logged_in(page):
            self._log("auth", "session already active")
            return True

        await self._dismiss_cookie_banner(page)

        login_button = await self._find_visible_locator(page, LOGIN_BUTTON_SELECTORS, label="login-button")
        login_count = 1 if login_button is not None else 0
        self._log("auth", "login button probe complete", selectors=LOGIN_BUTTON_SELECTORS, count=login_count)
        if not login_count:
            if self.config.headless:
                current_url = await self._safe_page_url(page)
                current_title = await self._safe_page_title(page)
                if self._looks_like_challenge(current_url, current_title):
                    raise BotChallengeError(
                        "Headless browser hit a Cloudflare/browser challenge before ChatGPT loaded. "
                        "Reuse works in headed mode, but this headless session is being challenged."
                    )
                raise ManualLoginRequiredError(
                    "No active session was found in the browser profile after the page settled. "
                    "Run the login test once with --headed to establish a persistent session."
                )
            self._log("auth", "no login button found; waiting for manual login in headed mode")
            return await self._wait_for_manual_login(page)

        if self.config.headless and not (self.config.email and self.config.password):
            raise ManualLoginRequiredError(
                "Headless login without a saved session is not supported. "
                "Run headed once to create the profile session."
            )

        self._log("auth", "clicking chatgpt login button")
        try:
            await login_button.click(timeout=5_000)
        except Exception as exc:
            self._log("auth", "login button click failed; retrying after cookie dismissal", error=str(exc))
            await self._dismiss_cookie_banner(page)
            await login_button.click(timeout=5_000, force=True)
        try:
            auth_page = await self._resolve_google_entry_page(page, context)
        except ManualLoginRequiredError:
            self._log(
                "auth",
                "google entry page could not be resolved automatically; switching to manual confirmation mode",
                current_url=await self._safe_page_url(page),
            )
            if self.config.headless:
                raise
            return await self._wait_for_manual_login(page, auth_page=page)

        try:
            await self._attempt_google_login(auth_page)
        except ManualLoginRequiredError:
            self._log(
                "auth",
                "automatic google login could not finish; manual intervention required",
                auth_page_url=await self._safe_page_url(auth_page),
            )
            if self.config.headless:
                raise
            return await self._wait_for_manual_login(page, auth_page=auth_page)

        if await self._wait_for_session_after_google(page, auth_page, context):
            self._log("auth", "session detected after google flow")
            return True

        if self.config.headless:
            raise AuthenticationError(
                "Google login steps completed but ChatGPT session was not detected. "
                "Complete login once in headed mode and retry headless."
            )
        self._log("auth", "google flow returned but session not detected; waiting for manual login")
        return await self._wait_for_manual_login(page, auth_page=auth_page)

    async def _start_driver(self):
        self._log("driver", "resolving browser driver", driver=self.driver_name)
        if self.config.use_patchright:
            from patchright.async_api import async_playwright
        else:
            from playwright.async_api import async_playwright
        return async_playwright()

    async def _is_logged_in(self, page: Any) -> bool:
        self._log("auth-check", "probing logged-in indicators")

        auth_selector = await self._find_visible_locator(page, AUTHENTICATED_INDICATORS, label="authenticated-indicator")
        auth_visible = auth_selector is not None

        login_button = await self._find_visible_locator(page, LOGIN_BUTTON_SELECTORS, label="login-indicator")
        login_visible = login_button is not None

        signup_button = await self._find_visible_locator(page, SIGNUP_BUTTON_SELECTORS, label="signup-indicator")
        signup_visible = signup_button is not None

        anonymous_marker = await self._find_visible_locator(page, ANONYMOUS_STATE_SELECTORS, label="anonymous-indicator")
        anonymous_visible = anonymous_marker is not None

        composer_visible = await self._has_chat_input(page)

        self._log(
            "auth-check",
            "auth state summary",
            auth_visible=auth_visible,
            login_visible=login_visible,
            signup_visible=signup_visible,
            anonymous_visible=anonymous_visible,
            composer_visible=composer_visible,
            current_url=await self._safe_page_url(page),
        )

        if auth_visible:
            self._log("auth-check", "authenticated indicator is visible; session considered active")
            return True

        if login_visible or signup_visible or anonymous_visible:
            self._log("auth-check", "anonymous markers detected; session considered inactive")
            return False

        if composer_visible:
            self._log("auth-check", "composer visible without anonymous markers; tentatively treating session as active")
            return True

        return False

    async def _has_chat_input(self, page: Any) -> bool:
        for selector in CHAT_INPUT_SELECTORS:
            locator = page.locator(selector)
            try:
                count = await locator.count()
                visible = False
                if count:
                    try:
                        visible = await locator.first.is_visible(timeout=1_500)
                    except Exception:
                        visible = False
                self._log("composer-check", "chat input selector probe", selector=selector, count=count, visible=visible)
                if count and visible:
                    return True
            except Exception as exc:
                self._log("composer-check", "chat input selector probe failed", selector=selector, error=str(exc))
                continue
        return False

    async def _wait_for_chat_input(self, page: Any) -> Any:
        last_error: Optional[Exception] = None
        self._log("composer", "waiting for chat input selectors")
        for selector in CHAT_INPUT_SELECTORS:
            locator = page.locator(selector).first
            try:
                await locator.wait_for(state="visible", timeout=10_000)
                self._log("composer", "chat input selector became visible", selector=selector)
                return locator
            except Exception as exc:  # pragma: no cover - depends on page state
                self._log("composer", "chat input selector wait failed", selector=selector, error=str(exc))
                last_error = exc
        raise ResponseTimeoutError("Chat input did not become visible") from last_error


    async def _wait_for_visible_locator(
        self,
        page: Any,
        selectors: list[str],
        *,
        label: str,
        total_timeout_ms: int = 10_000,
        poll_interval_ms: int = 500,
        visibility_timeout_ms: int = 500,
    ) -> Optional[Any]:
        deadline = asyncio.get_running_loop().time() + (total_timeout_ms / 1000)
        attempt = 0
        while asyncio.get_running_loop().time() < deadline:
            attempt += 1
            locator = await self._find_visible_locator(
                page,
                selectors,
                label=label,
                timeout_ms=visibility_timeout_ms,
            )
            if locator is not None:
                self._log("selector", "wait-for-visible locator resolved", label=label, attempt=attempt)
                return locator
            await page.wait_for_timeout(poll_interval_ms)
        self._log("selector", "wait-for-visible locator timed out", label=label, total_timeout_ms=total_timeout_ms)
        return None

    async def _find_visible_locator(
        self,
        page: Any,
        selectors: list[str],
        *,
        label: str,
        timeout_ms: int = 1_500,
    ) -> Optional[Any]:
        for selector in selectors:
            try:
                locator = page.locator(selector)
                count = await locator.count()
                visible = False
                if count:
                    try:
                        visible = await locator.first.is_visible(timeout=timeout_ms)
                    except Exception:
                        visible = False
                self._log("selector", "selector probe", label=label, selector=selector, count=count, visible=visible)
                if count and visible:
                    return locator.first
            except Exception as exc:
                self._log("selector", "selector probe failed", label=label, selector=selector, error=str(exc))
        return None

    async def _dismiss_cookie_banner(self, page: Any) -> bool:
        self._log("cookie", "probing cookie banner controls")
        for selector in COOKIE_BANNER_SELECTORS:
            try:
                locator = page.locator(selector)
                count = await locator.count()
                visible = False
                if count:
                    try:
                        visible = await locator.first.is_visible(timeout=1_000)
                    except Exception:
                        visible = False
                self._log("cookie", "cookie control probe", selector=selector, count=count, visible=visible)
                if count and visible:
                    await locator.first.click(timeout=3_000)
                    self._log("cookie", "cookie control clicked", selector=selector)
                    await page.wait_for_timeout(750)
                    return True
            except Exception as exc:
                self._log("cookie", "cookie control click failed", selector=selector, error=str(exc))
        self._log("cookie", "no visible cookie banner control clicked")
        return False

    async def _resolve_google_entry_page(self, page: Any, context: Any) -> Any:
        google_button_patterns = [
            re.compile(r"continue with google", re.I),
            re.compile(r"google", re.I),
        ]

        self._log("google", "waiting for auth popup or redirect page")
        existing_pages = list(context.pages)
        existing_page_ids = {id(p) for p in existing_pages}
        self._log(
            "google",
            "captured pre-click page set",
            page_count=len(existing_pages),
            page_urls=[await self._safe_page_url(p) for p in existing_pages],
        )

        clicked_selector = None
        for attempt in range(1, 7):
            self._log("google", "probing google entry controls", attempt=attempt, current_url=await self._safe_page_url(page))
            for pattern in google_button_patterns:
                button = page.get_by_role("button", name=pattern)
                count = await button.count()
                visible = False
                if count:
                    try:
                        visible = await button.first.is_visible(timeout=1_000)
                    except Exception:
                        visible = False
                self._log("google", "google button role probe", pattern=pattern.pattern, count=count, visible=visible, attempt=attempt)
                if count and visible:
                    await button.first.click()
                    clicked_selector = f"role=button name=/{pattern.pattern}/i"
                    break
            if clicked_selector:
                break

            fallback_selectors = [
                'button[value="google"]',
                'button:has-text("Continue with Google")',
                'button:has-text("Google")',
            ]
            for selector in fallback_selectors:
                button = page.locator(selector)
                count = await button.count()
                visible = False
                if count:
                    try:
                        visible = await button.first.is_visible(timeout=1_000)
                    except Exception:
                        visible = False
                self._log("google", "google fallback probe", selector=selector, count=count, visible=visible, attempt=attempt)
                if count and visible:
                    await button.first.click()
                    clicked_selector = selector
                    break
            if clicked_selector:
                break

            await page.wait_for_timeout(1_000)

        if not clicked_selector:
            raise ManualLoginRequiredError(
                "The Google sign-in button was not found automatically."
            )

        self._log("google", "google entry button clicked", selector=clicked_selector)

        deadline = asyncio.get_running_loop().time() + 15
        last_seen_url = await self._safe_page_url(page)
        while asyncio.get_running_loop().time() < deadline:
            current_url = await self._safe_page_url(page)
            if current_url != last_seen_url:
                self._log("google", "google entry page url changed", from_url=last_seen_url, to_url=current_url)
                last_seen_url = current_url

            if self._is_google_auth_url(current_url):
                self._log("google", "detected same-page redirect to google auth", url=current_url)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15_000)
                except Exception as exc:
                    self._log("google", "same-page domcontentloaded wait failed; continuing", url=current_url, error=str(exc))
                self._log("google", "returning same redirected page for google auth", url=await self._safe_page_url(page))
                return page

            for candidate in list(context.pages):
                candidate_url = await self._safe_page_url(candidate)
                candidate_is_new = id(candidate) not in existing_page_ids
                candidate_is_google = self._is_google_auth_url(candidate_url)
                if candidate_is_new or candidate_is_google:
                    self._log(
                        "google",
                        "detected candidate auth page in browser context",
                        candidate_url=candidate_url,
                        candidate_is_new=candidate_is_new,
                        candidate_is_google=candidate_is_google,
                    )
                    try:
                        await candidate.wait_for_load_state("domcontentloaded", timeout=15_000)
                    except Exception as exc:
                        self._log("google", "candidate auth page domcontentloaded wait failed; continuing", candidate_url=candidate_url, error=str(exc))
                    self._log("google", "returning candidate auth page", candidate_url=await self._safe_page_url(candidate))
                    return candidate

            await page.wait_for_timeout(250)

        raise ManualLoginRequiredError(
            "Google sign-in was started, but no popup or redirect page became detectable within the timeout."
        )

    async def _wait_for_session_after_google(
        self,
        page: Any,
        auth_page: Any,
        context: Any,
        *,
        total_timeout_ms: int = 30_000,
        poll_interval_ms: int = 750,
    ) -> bool:
        self._log(
            "auth-post-google",
            "waiting for post-google redirect and ChatGPT session establishment",
            total_timeout_ms=total_timeout_ms,
        )
        deadline = asyncio.get_running_loop().time() + (total_timeout_ms / 1000)
        seen_urls: dict[int, str] = {}

        while asyncio.get_running_loop().time() < deadline:
            open_pages: list[Any] = []
            for candidate in list(context.pages):
                try:
                    if hasattr(candidate, "is_closed") and candidate.is_closed():
                        continue
                except Exception:
                    continue
                open_pages.append(candidate)

            if not open_pages:
                self._log("auth-post-google", "no open browser pages remain while waiting for session")
                return False

            for candidate in open_pages:
                candidate_url = await self._safe_page_url(candidate)
                candidate_id = id(candidate)
                if seen_urls.get(candidate_id) != candidate_url:
                    self._log(
                        "auth-post-google",
                        "candidate page observed",
                        candidate_id=candidate_id,
                        candidate_url=candidate_url,
                    )
                    seen_urls[candidate_id] = candidate_url

            for candidate in open_pages:
                candidate_url = await self._safe_page_url(candidate)
                if self._is_google_auth_url(candidate_url):
                    continue
                if "chatgpt.com" in candidate_url or "openai.com" in candidate_url:
                    try:
                        await candidate.wait_for_load_state("domcontentloaded", timeout=5_000)
                    except Exception as exc:
                        self._log(
                            "auth-post-google",
                            "candidate domcontentloaded wait failed; continuing",
                            candidate_url=candidate_url,
                            error=str(exc),
                        )
                    if await self._is_logged_in(candidate):
                        self._log(
                            "auth-post-google",
                            "authenticated session detected on candidate page",
                            candidate_url=await self._safe_page_url(candidate),
                        )
                        return True

            await page.wait_for_timeout(poll_interval_ms)

        self._log(
            "auth-post-google",
            "timed out waiting for authenticated ChatGPT session after google flow",
            total_timeout_ms=total_timeout_ms,
        )
        return False

    async def _attempt_google_login(self, google_page: Any) -> None:
        self._log("google", "starting google login flow", page_url=await self._safe_page_url(google_page))
        if not self.config.email or not self.config.password:
            raise ManualLoginRequiredError(
                "Email/password were not provided, so manual login is required."
            )

        await google_page.wait_for_load_state("domcontentloaded", timeout=20_000)
        self._log("google", "google page ready", page_url=await self._safe_page_url(google_page))

        email_selectors = [
            'input[type="email"]',
            'input[autocomplete="username"]',
            'input[name="identifier"]',
        ]
        password_selectors = [
            'input[type="password"]',
            'input[autocomplete="current-password"]',
            'input[name="Passwd"]',
        ]

        email_input = None
        for attempt in range(1, 11):
            self._log("google", "probing identifier step", attempt=attempt, page_url=await self._safe_page_url(google_page))

            account_chooser = google_page.get_by_text(self.config.email, exact=True)
            try:
                chooser_count = await account_chooser.count()
                chooser_visible = False
                if chooser_count:
                    try:
                        chooser_visible = await account_chooser.first.is_visible(timeout=1_000)
                    except Exception:
                        chooser_visible = False
                self._log("google", "account chooser probe", email=self.config.email, count=chooser_count, visible=chooser_visible, attempt=attempt)
                if chooser_count and chooser_visible:
                    await account_chooser.first.click(timeout=3_000)
                    self._log("google", "clicked existing google account chooser entry", email=self.config.email)
                    await google_page.wait_for_timeout(1_000)
                    break
            except Exception as exc:
                self._log("google", "account chooser click failed", error=str(exc), attempt=attempt)

            email_input = await self._find_visible_locator(
                google_page,
                email_selectors,
                label="google-email-input",
                timeout_ms=1_000,
            )
            if email_input is not None:
                self._log("google", "filling google email field")
                await email_input.fill(self.config.email)
                await self._click_next_button(google_page)
                break

            password_probe = await self._find_visible_locator(
                google_page,
                password_selectors,
                label="google-password-precheck",
                timeout_ms=1_000,
            )
            if password_probe is not None:
                self._log("google", "password step already visible; skipping email entry")
                break

            await google_page.wait_for_timeout(1_000)

        password_input = await self._wait_for_visible_locator(
            google_page,
            password_selectors,
            label="google-password-input",
            total_timeout_ms=20_000,
            poll_interval_ms=750,
            visibility_timeout_ms=1_000,
        )
        if password_input is None:
            raise ManualLoginRequiredError(
                "Password input did not appear. Google likely requires a manual challenge step."
            )

        self._log("google", "password input became visible")
        await password_input.fill(self.config.password)
        self._log("google", "password field filled; clicking next")
        await self._click_next_button(google_page)

        challenge_indicators = [
            'input[name="totpPin"]',
            'input[name="idvPin"]',
            'text=Verify it\'s you',
            'text=2-Step Verification',
        ]
        for selector in challenge_indicators:
            try:
                locator = google_page.locator(selector)
                count = await locator.count()
                visible = False
                if count:
                    try:
                        visible = await locator.first.is_visible(timeout=2_000)
                    except Exception:
                        visible = False
                self._log("google", "challenge indicator probe", selector=selector, count=count, visible=visible)
                if count and visible:
                    raise ManualLoginRequiredError(
                        "Google requested additional verification. Complete it manually in headed mode."
                    )
            except ManualLoginRequiredError:
                raise
            except Exception as exc:
                self._log("google", "challenge probe failed", selector=selector, error=str(exc))
                continue

    async def _click_next_button(self, page: Any) -> None:
        button_patterns = [re.compile(r"^next$", re.I), re.compile(r"volgende", re.I)]
        for pattern in button_patterns:
            button = page.get_by_role("button", name=pattern)
            count = await button.count()
            self._log("google", "next button role probe", pattern=pattern.pattern, count=count)
            if count:
                await button.first.click()
                self._log("google", "clicked next button", pattern=pattern.pattern)
                return
        fallback_selector = 'button:has-text("Next"), button:has-text("Volgende")'
        fallback = page.locator(fallback_selector)
        fallback_count = await fallback.count()
        self._log("google", "next button fallback probe", selector=fallback_selector, count=fallback_count)
        if fallback_count:
            await fallback.first.click()
            self._log("google", "clicked fallback next button", selector=fallback_selector)
            return
        raise ManualLoginRequiredError("Could not find the Google Next button.")

    async def _wait_for_manual_login(self, page: Any, auth_page: Any | None = None) -> bool:
        if self.config.headless:
            raise ManualLoginRequiredError(
                "Manual login is required, but the browser is headless."
            )

        deadline_seconds = self.config.manual_login_timeout_ms / 1000
        end_time = asyncio.get_running_loop().time() + deadline_seconds
        self._log("manual-login", "waiting for manual login", timeout_seconds=deadline_seconds)
        iteration = 0
        while asyncio.get_running_loop().time() < end_time:
            iteration += 1
            if auth_page is not None:
                auth_page_url = await self._safe_page_url(auth_page)
                page_url = await self._safe_page_url(page)
                self._log(
                    "manual-login",
                    "manual-login poll state",
                    iteration=iteration,
                    page_url=page_url,
                    auth_page_url=auth_page_url,
                    auth_page_closed=auth_page.is_closed() if hasattr(auth_page, "is_closed") else None,
                )
                if auth_page_url != "<url-unavailable>" and self._is_google_auth_url(auth_page_url):
                    self._log(
                        "manual-login",
                        "google auth page still active; waiting on Google/browser-mediated confirmation before polling ChatGPT",
                        iteration=iteration,
                        auth_page_url=auth_page_url,
                    )
                    await asyncio.sleep(2)
                    continue
            try:
                if hasattr(page, "is_closed") and page.is_closed():
                    self._log("manual-login", "chatgpt page is closed during manual-login poll", iteration=iteration)
                    raise AuthenticationError("ChatGPT page closed while waiting for manual login.")
                await self._goto(page, self.config.project_url, label=f"manual-login-poll-{iteration}")
            except AuthenticationError:
                raise
            except Exception as exc:
                self._log("manual-login", "navigation during manual-login poll failed", iteration=iteration, error=str(exc))
            if await self._is_logged_in(page):
                self._log("manual-login", "manual login detected", iteration=iteration)
                return True
            remaining = max(0.0, end_time - asyncio.get_running_loop().time())
            self._log("manual-login", "manual login not detected yet", iteration=iteration, seconds_remaining=round(remaining, 1))
            await asyncio.sleep(2)

        raise AuthenticationError(
            "Timed out while waiting for manual login to complete in the visible browser."
        )

    async def _probe_first_matching_control(
        self,
        page: Any,
        selectors: list[str],
        *,
        allow_disabled: bool = False,
    ) -> dict[str, Any]:
        for selector in selectors:
            try:
                locator = page.locator(selector)
                count = await locator.count()
            except Exception as exc:
                self._log("submit", "control probe failed", selector=selector, error=str(exc))
                continue

            if not count:
                continue

            limit = min(count, 5)
            for index in range(limit):
                item = locator.nth(index)
                try:
                    visible = await item.is_visible(timeout=500)
                except Exception:
                    visible = False
                if not visible:
                    continue

                try:
                    enabled = await item.is_enabled(timeout=750)
                except Exception:
                    enabled = False
                if not allow_disabled and not enabled:
                    continue

                try:
                    aria_label = (await item.get_attribute("aria-label") or "").strip()
                except Exception:
                    aria_label = ""
                try:
                    data_testid = (await item.get_attribute("data-testid") or "").strip()
                except Exception:
                    data_testid = ""
                try:
                    class_name = (await item.get_attribute("class") or "").strip()
                except Exception:
                    class_name = ""
                try:
                    element_id = (await item.get_attribute("id") or "").strip()
                except Exception:
                    element_id = ""

                return {
                    "selector": selector,
                    "index": index,
                    "count": count,
                    "visible": visible,
                    "enabled": enabled,
                    "aria_label": aria_label,
                    "data_testid": data_testid,
                    "class_name": class_name,
                    "id": element_id,
                }

        return {
            "selector": None,
            "index": None,
            "count": 0,
            "visible": False,
            "enabled": False,
            "aria_label": "",
            "data_testid": "",
            "class_name": "",
            "id": "",
        }

    async def _probe_submit_button_state(self, page: Any) -> dict[str, Any]:
        stop_state = await self._probe_first_matching_control(page, COMPOSER_STOP_BUTTON_SELECTORS, allow_disabled=True)
        stop_visible = bool(stop_state.get("visible"))

        send_state = await self._probe_first_matching_control(page, COMPOSER_SEND_READY_SELECTORS)
        send_ready = bool(send_state.get("visible") and send_state.get("enabled") and not stop_visible)

        idle_indicator_state = await self._probe_first_matching_control(
            page,
            COMPOSER_IDLE_INDICATOR_SELECTORS,
            allow_disabled=True,
        )
        idle_visible = bool(idle_indicator_state.get("visible") and not stop_visible)

        primary_match = stop_state if stop_visible else send_state if send_ready else idle_indicator_state
        if primary_match.get("selector") is None:
            primary_match = stop_state if stop_state.get("selector") is not None else send_state

        return {
            **primary_match,
            "send_ready": send_ready,
            "stop_visible": stop_visible,
            "idle_visible": idle_visible,
            "visible_enabled_count": int(stop_visible) + int(send_ready) + int(idle_visible),
        }

    async def _get_last_assistant_turn_locator(self, page: Any) -> tuple[Any | None, Optional[str]]:
        for selector in ASSISTANT_TURN_SCOPE_SELECTORS:
            try:
                locator = page.locator(selector)
                count = await locator.count()
            except Exception:
                continue
            if count:
                return locator.nth(count - 1), selector
        return None, None

    async def _probe_thinking_state(self, page: Any) -> dict[str, Any]:
        assistant_turn, assistant_selector = await self._get_last_assistant_turn_locator(page)
        if assistant_turn is None:
            return {
                "visible": False,
                "source": None,
                "text": "",
            }

        for selector in THINKING_MARKER_SELECTORS:
            scoped_selector = f':scope {selector}'
            try:
                locator = assistant_turn.locator(scoped_selector)
                count = await locator.count()
            except Exception:
                continue
            if not count:
                continue
            limit = min(count, 5)
            for index in range(limit):
                item = locator.nth(index)
                try:
                    visible = await item.is_visible(timeout=500)
                except Exception:
                    visible = False
                if not visible:
                    continue
                try:
                    text = (await item.inner_text(timeout=500) or "").strip()
                except Exception:
                    text = ""
                return {
                    "visible": True,
                    "source": f"{assistant_selector} >> {selector}",
                    "text": text,
                }

        for pattern in THINKING_TEXT_PATTERNS:
            try:
                locator = assistant_turn.get_by_text(pattern)
                count = await locator.count()
            except Exception:
                continue
            if not count:
                continue
            limit = min(count, 5)
            for index in range(limit):
                item = locator.nth(index)
                try:
                    visible = await item.is_visible(timeout=500)
                except Exception:
                    visible = False
                if not visible:
                    continue
                try:
                    text = (await item.inner_text(timeout=500) or "").strip()
                except Exception:
                    text = ""
                return {
                    "visible": True,
                    "source": f"{assistant_selector} >> {getattr(pattern, 'pattern', str(pattern))}",
                    "text": text,
                }

        return {
            "visible": False,
            "source": None,
            "text": "",
        }

    async def _submit_prompt(self, page: Any) -> None:
        submit_wait_timeout_s = 20.0
        poll_interval_ms = 500
        deadline = asyncio.get_running_loop().time() + submit_wait_timeout_s
        attempt = 0
        self._log(
            "submit",
            "attempting to submit prompt",
            wait_timeout_s=submit_wait_timeout_s,
            selectors=COMPOSER_SUBMIT_BUTTON_SELECTORS,
        )
        while asyncio.get_running_loop().time() < deadline:
            attempt += 1
            for selector in COMPOSER_SUBMIT_BUTTON_SELECTORS:
                try:
                    button = page.locator(selector).first
                    count = await button.count()
                    enabled = False
                    visible = False
                    if count:
                        try:
                            visible = await button.is_visible(timeout=1_000)
                        except Exception:
                            visible = False
                        try:
                            enabled = await button.is_enabled(timeout=1_500)
                        except Exception:
                            enabled = False
                    self._log(
                        "submit",
                        "submit selector probe",
                        attempt=attempt,
                        selector=selector,
                        count=count,
                        visible=visible,
                        enabled=enabled,
                    )
                    if count and enabled:
                        await button.click()
                        self._log("submit", "clicked submit button", attempt=attempt, selector=selector)
                        return
                except Exception as exc:
                    self._log("submit", "submit selector failed", attempt=attempt, selector=selector, error=str(exc))
                    continue
            await page.wait_for_timeout(poll_interval_ms)

        self._log(
            "submit",
            "no enabled submit button found after wait; pressing Enter as fallback",
            wait_timeout_s=submit_wait_timeout_s,
        )
        await page.keyboard.press("Enter")

    def _extract_json_from_text(self, text: Optional[str]) -> Optional[Any]:
        source_text = (text or "").strip()
        if not source_text:
            return None

        fenced_match = re.search(r"```(?:json)?\s*(.*?)```", source_text, flags=re.IGNORECASE | re.DOTALL)
        if fenced_match:
            source_text = fenced_match.group(1).strip()

        decoder = json.JSONDecoder()
        for match in re.finditer(r"[\[{]", source_text):
            candidate = source_text[match.start():].strip()
            try:
                parsed, _ = decoder.raw_decode(candidate)
                return parsed
            except Exception:
                continue
        return None

    async def _extract_text_from_locator(self, locator: Any, *, timeout_ms: int = 1_500) -> str:
        try:
            return ((await locator.inner_text(timeout=timeout_ms)) or "").strip()
        except Exception:
            try:
                return ((await locator.text_content(timeout=timeout_ms)) or "").strip()
            except Exception:
                return ""

    async def _extract_last_text_from_selector(self, page: Any, selector: str) -> tuple[int, str]:
        locator = page.locator(selector)
        try:
            count = await locator.count()
        except Exception:
            return 0, ""
        if count <= 0:
            return 0, ""

        try:
            texts = await locator.evaluate_all(
                "els => els.map(el => ((el.innerText || el.textContent || '').trim()))"
            )
            if texts:
                for candidate in reversed(texts):
                    normalized = (candidate or "").strip()
                    if normalized:
                        return count, normalized
                return count, (texts[-1] or "").strip()
        except Exception:
            pass

        try:
            for index in range(count - 1, -1, -1):
                candidate = await self._extract_text_from_locator(locator.nth(index), timeout_ms=1_000)
                if candidate:
                    return count, candidate
        except Exception:
            pass

        return count, ""

    async def _extract_last_text_from_selectors(
        self,
        page: Any,
        selectors: list[str],
    ) -> tuple[Optional[str], int, str, list[dict[str, Any]]]:
        probes: list[dict[str, Any]] = []
        first_nonempty: Optional[tuple[str, int, str]] = None
        best_fallback: Optional[tuple[str, int, str]] = None

        for selector in selectors:
            locator = page.locator(selector)
            try:
                count = await locator.count()
            except Exception:
                count = 0

            visible = False
            if count:
                try:
                    visible = await locator.last.is_visible(timeout=1_000)
                except Exception:
                    visible = False

            _, text = await self._extract_last_text_from_selector(page, selector)
            probe = {
                "selector": selector,
                "count": count,
                "visible": visible,
                "text_length": len(text),
                "parsed": False,
                "preview": self._preview_text(text, 220),
            }
            probes.append(probe)

            if count and text and first_nonempty is None:
                first_nonempty = (selector, count, text)
            if count and best_fallback is None:
                best_fallback = (selector, count, text)

        if first_nonempty is not None:
            return (*first_nonempty, probes)
        if best_fallback is not None:
            return (*best_fallback, probes)
        return None, 0, "", probes

    def _chatgpt_home_url(self) -> str:
        parsed = urlparse(self.config.project_url)
        return urlunparse(parsed._replace(path='/', query='', fragment=''))

    def _project_home_url_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path or '/'
        match = re.search(r'(/g/g-p-[^/]+/project)(?:/.*)?$', path.rstrip('/'))
        if match:
            return urlunparse(parsed._replace(path=match.group(1), query='', fragment=''))
        if path.rstrip('/').endswith('/project'):
            return urlunparse(parsed._replace(path=path.rstrip('/'), query='', fragment=''))
        if '/c/' in path and '/g/g-p-' in path:
            base = path.split('/c/', 1)[0].rstrip('/') + '/project'
            return urlunparse(parsed._replace(path=base, query='', fragment=''))
        return urlunparse(parsed._replace(path=path, query='', fragment=''))

    def _extract_project_id_from_url(self, url: str) -> Optional[str]:
        path = urlparse(url).path or ''
        match = re.search(r'/g/(g-p-[a-z0-9]+)', path, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return None

    def _project_identity_key_from_url(self, url: str) -> str:
        project_id = self._extract_project_id_from_url(url)
        if project_id:
            return project_id
        return self._project_home_url_from_url(url)

    def _project_urls_refer_to_same_project(self, left: str, right: str) -> bool:
        return self._project_identity_key_from_url(left) == self._project_identity_key_from_url(right)

    async def _ensure_sidebar_open(self, page: Any) -> None:
        new_project_button = await self._find_visible_locator(
            page,
            PROJECT_NEW_BUTTON_SELECTORS,
            label='project-new-button-visible',
            timeout_ms=800,
        )
        if new_project_button is not None:
            return

        close_sidebar = await self._find_visible_locator(
            page,
            PROJECT_SIDEBAR_CLOSE_BUTTON_SELECTORS,
            label='project-close-sidebar',
            timeout_ms=800,
        )
        if close_sidebar is not None:
            self._log('sidebar', 'sidebar already open for project flow')
            await page.wait_for_timeout(400)
            return

        open_sidebar = await self._find_visible_locator(
            page,
            PROJECT_SIDEBAR_OPEN_BUTTON_SELECTORS,
            label='project-open-sidebar',
            timeout_ms=800,
        )
        if open_sidebar is None:
            return

        click_error: Optional[Exception] = None
        try:
            await open_sidebar.click(timeout=2_500)
            self._log('sidebar', 'clicked open sidebar button')
        except Exception as exc:
            click_error = exc
            self._log('sidebar', 'normal open sidebar click failed; retrying with force', error=str(exc))
            try:
                await open_sidebar.click(timeout=2_500, force=True)
                click_error = None
                self._log('sidebar', 'forced open sidebar click succeeded')
            except Exception as force_exc:
                click_error = force_exc
                self._log('sidebar', 'forced open sidebar click failed; retrying via dom click', error=str(force_exc))
                try:
                    await open_sidebar.evaluate('(el) => el.click()')
                    click_error = None
                    self._log('sidebar', 'dom open sidebar click succeeded')
                except Exception as dom_exc:
                    click_error = dom_exc
                    self._log('sidebar', 'dom open sidebar click failed', error=str(dom_exc))

        await page.wait_for_timeout(800)

        if click_error is not None:
            raise click_error

    async def _try_activate_project_only_memory(self, page: Any) -> bool:
        locator = await self._find_visible_locator(
            page,
            PROJECT_MEMORY_PROJECT_ONLY_SELECTORS,
            label='project-memory-project-only',
            timeout_ms=1_000,
        )
        if locator is None:
            return False
        try:
            await locator.click(timeout=5_000)
            await page.wait_for_timeout(300)
            return True
        except Exception:
            return False

    async def _try_select_project_dialog_value(
        self,
        page: Any,
        *,
        control_selectors: list[str],
        value: str,
        label: str,
    ) -> bool:
        control = await self._find_visible_locator(page, control_selectors, label=f'{label}-control', timeout_ms=1_000)
        if control is None:
            return False
        try:
            await control.click(timeout=5_000)
            await page.wait_for_timeout(300)
        except Exception:
            return False

        escaped = value.replace('"', '\"')
        selectors = [pattern.format(value=escaped) for pattern in PROJECT_VALUE_OPTION_PATTERNS]
        option = await self._wait_for_visible_locator(
            page,
            selectors,
            label=f'{label}-value',
            total_timeout_ms=2_000,
            poll_interval_ms=250,
            visibility_timeout_ms=500,
        )
        if option is None:
            try:
                await page.keyboard.press('Escape')
            except Exception:
                pass
            return False
        try:
            await option.click(timeout=5_000)
            await page.wait_for_timeout(300)
            return True
        except Exception:
            return False

    async def _wait_for_created_project_url(self, page: Any, *, project_name: str, previous_url: str, timeout_ms: int = 20_000) -> str:
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        clicked_sidebar_link = False
        while asyncio.get_running_loop().time() < deadline:
            current_url = await self._safe_page_url(page)
            project_url = self._project_home_url_from_url(current_url)
            if self._is_project_home_url(project_url) and project_url != self._project_home_url_from_url(previous_url):
                return project_url

            if not clicked_sidebar_link:
                project_link = await self._find_project_link_by_name(page, project_name)
                if project_link is not None:
                    try:
                        await project_link.click(timeout=5_000)
                        clicked_sidebar_link = True
                    except Exception:
                        pass
            await page.wait_for_timeout(500)
        raise ResponseTimeoutError(f'Timed out waiting for created project URL after creating project: {project_name}')

    async def _find_project_link_by_name(self, page: Any, project_name: str) -> Optional[Any]:
        normalized_name = re.sub(r'\s+', ' ', (project_name or '')).strip()
        if not normalized_name:
            return None
        try:
            locator = page.locator('a[href*="/project"], button').filter(has_text=normalized_name)
            count = await locator.count()
        except Exception:
            return None
        for index in range(min(count, 6)):
            item = locator.nth(index)
            try:
                if await item.is_visible(timeout=500):
                    return item
            except Exception:
                continue
        return None

    def _normalize_project_name(self, value: str) -> str:
        normalized = re.sub(r'\s+', ' ', (value or '')).strip()
        return normalized.casefold()

    async def _expand_projects_section(self, page: Any) -> bool:
        toggle = await self._find_visible_locator(
            page,
            PROJECT_SECTION_TOGGLE_SELECTORS,
            label='project-section-toggle',
            timeout_ms=800,
        )
        if toggle is not None:
            try:
                expanded = await toggle.get_attribute('aria-expanded')
            except Exception:
                expanded = None
            if expanded == 'true':
                return False
            try:
                await toggle.click(timeout=2_500)
                self._log('project-resolve', 'expanded Projects section via toggle control')
                await page.wait_for_timeout(500)
                return True
            except Exception as exc:
                self._log('project-resolve', 'Projects toggle click failed; falling back to DOM expansion', error=str(exc))

        try:
            expanded = await page.evaluate(
                r'''
                () => {
                    const normalizeText = value => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
                    const controls = Array.from(document.querySelectorAll('button,[role="button"],summary'));
                    for (const control of controls) {
                        const text = normalizeText(control.innerText || control.textContent || control.getAttribute('aria-label') || '');
                        if (text !== 'projects') continue;
                        const ariaExpanded = (control.getAttribute('aria-expanded') || '').toLowerCase();
                        if (ariaExpanded === 'true') return false;
                        control.click();
                        return true;
                    }
                    return false;
                }
                '''
            )
        except Exception:
            return False
        if expanded:
            self._log('project-resolve', 'expanded Projects section via DOM fallback')
            await page.wait_for_timeout(500)
            return True
        return False

    async def _prime_project_sidebar(self, page: Any) -> None:
        try:
            await page.evaluate(
                r'''
                () => {
                    const candidates = Array.from(document.querySelectorAll('aside, nav, [data-testid*="sidebar"], [class*="sidebar"]'));
                    for (const element of candidates) {
                        if (!(element instanceof HTMLElement)) continue;
                        try {
                            element.scrollTop = 0;
                            element.dispatchEvent(new Event('scroll', { bubbles: true }));
                            element.scrollTop = element.scrollHeight;
                            element.dispatchEvent(new Event('scroll', { bubbles: true }));
                            element.scrollTop = 0;
                        } catch (_) {}
                    }
                    window.scrollTo(0, 0);
                }
                '''
            )
        except Exception:
            return
        await page.wait_for_timeout(400)

    def _dedupe_projects(self, projects: list[dict[str, str]]) -> list[dict[str, str]]:
        deduped: list[dict[str, str]] = []
        seen_keys: set[str] = set()
        for project in projects:
            display_name = re.sub(r'\s+', ' ', str(project.get('name') or '')).strip()
            raw_url = str(project.get('url') or '').strip()
            if not display_name or not raw_url:
                continue
            project_url = self._project_home_url_from_url(raw_url)
            if not self._is_project_home_url(project_url):
                continue
            project_key = self._project_identity_key_from_url(project_url)
            if project_key in seen_keys:
                continue
            seen_keys.add(project_key)
            deduped.append({'name': display_name, 'url': project_url})
        return deduped

    async def _resolve_projects_by_name(self, page: Any, *, name: str, label: str) -> dict[str, Any]:
        home_url = self._chatgpt_home_url()
        await self._goto(page, home_url, label=label)
        await self._ensure_sidebar_open(page)

        normalized_name = self._normalize_project_name(name)
        collected: list[dict[str, str]] = []
        for attempt in range(3):
            if attempt == 1:
                await self._expand_projects_section(page)
            elif attempt == 2:
                await self._prime_project_sidebar(page)
                await self._expand_projects_section(page)

            projects = await self._collect_sidebar_projects(page)
            collected = self._dedupe_projects([*collected, *projects])
            matches = [project for project in collected if self._normalize_project_name(project.get('name', '')) == normalized_name]
            self._log(
                'project-resolve',
                'project enumeration attempt completed',
                attempt=attempt + 1,
                discovered_count=len(projects),
                total_count=len(collected),
                match_count=len(matches),
            )
            if len(matches) == 1:
                return {
                    'project_url': matches[0]['url'],
                    'match_count': 1,
                    'matches': matches,
                    'matched_by': 'exact_name',
                    'error': None,
                }
            if len(matches) > 1:
                return {
                    'project_url': None,
                    'match_count': len(matches),
                    'matches': matches,
                    'matched_by': None,
                    'error': 'ambiguous_project_name',
                }
            await page.wait_for_timeout(350)

        return {
            'project_url': None,
            'match_count': 0,
            'matches': [],
            'matched_by': None,
            'error': 'project_not_found',
        }

    async def _collect_sidebar_projects(self, page: Any) -> list[dict[str, str]]:
        try:
            projects = await page.evaluate(
                r'''
                () => {
                    const normalizeText = value => (value || '').replace(/\s+/g, ' ').trim();
                    const normalizePath = value => {
                        try {
                            const url = new URL(value, window.location.origin);
                            return (url.pathname || '').replace(/\/+$/, '');
                        } catch (_) {
                            return '';
                        }
                    };
                    const toAbsolute = value => {
                        try {
                            const url = new URL(value, window.location.origin);
                            url.search = '';
                            url.hash = '';
                            return url.toString();
                        } catch (_) {
                            return '';
                        }
                    };
                    const isProjectPath = value => /\/g\/g-p-[^/]+(?:-[^/]+)?\/project$/.test(value || '') || /\/project$/.test(value || '');
                    const namePartsForAnchor = anchor => {
                        const parts = [];
                        const push = value => {
                            const normalized = normalizeText(value);
                            if (normalized) parts.push(normalized);
                        };
                        push(anchor.getAttribute('title'));
                        push(anchor.getAttribute('aria-label'));
                        push(anchor.innerText);
                        push(anchor.textContent);
                        for (const node of Array.from(anchor.querySelectorAll('[title],[aria-label],span,div,p')).slice(0, 12)) {
                            push(node.getAttribute?.('title'));
                            push(node.getAttribute?.('aria-label'));
                            push(node.textContent);
                        }
                        const container = anchor.closest('[data-sidebar-item], li, [role="treeitem"], [role="listitem"], [class*="sidebar"]');
                        push(container?.getAttribute?.('aria-label'));
                        push(container?.textContent);
                        return parts;
                    };

                    const roots = [];
                    const seenRoots = new Set();
                    const addRoot = root => {
                        if (!root || seenRoots.has(root)) return;
                        seenRoots.add(root);
                        roots.push(root);
                    };

                    for (const root of Array.from(document.querySelectorAll('aside, nav, [data-testid*="sidebar"], [class*="sidebar"]'))) {
                        addRoot(root);
                    }
                    addRoot(document.body);

                    const seen = new Set();
                    const results = [];
                    for (const root of roots) {
                        for (const anchor of Array.from(root.querySelectorAll('a[href*="/project"]'))) {
                            const absoluteUrl = toAbsolute(anchor.getAttribute('href') || '');
                            const normalizedPath = normalizePath(absoluteUrl);
                            if (!isProjectPath(normalizedPath)) continue;
                            if (seen.has(normalizedPath)) continue;

                            const name = namePartsForAnchor(anchor).find(Boolean) || '';
                            if (!name) continue;

                            seen.add(normalizedPath);
                            results.push({ name, url: absoluteUrl });
                        }
                    }
                    return results;
                }
                '''
            )
        except Exception:
            return []

        if not isinstance(projects, list):
            return []

        normalized_projects: list[dict[str, str]] = []
        for item in projects:
            if not isinstance(item, dict):
                continue
            raw_name = str(item.get("name") or "")
            raw_url = str(item.get("url") or "").strip()
            if not raw_name or not raw_url:
                continue
            normalized_projects.append({"name": raw_name, "url": raw_url})
        return self._dedupe_projects(normalized_projects)
    def _project_home_url(self) -> str:
        return self._project_home_url_from_url(self.config.project_url)

    def _infer_source_match_text(self, source_kind: str, value: str) -> str:
        normalized = (value or "").strip()
        if source_kind == "link":
            parsed = urlparse(normalized)
            return parsed.netloc or normalized
        return self._preview_text(normalized, 80)

    async def _open_project_sources_tab(self, page: Any) -> None:
        tab = await self._wait_for_visible_locator(
            page,
            PROJECT_SOURCES_TAB_SELECTORS,
            label="project-sources-tab",
            total_timeout_ms=15_000,
        )
        if tab is None:
            raise ResponseTimeoutError("Project Sources tab did not become visible")
        await tab.click(timeout=5_000)
        await page.wait_for_timeout(750)
        self._log("project-source", "sources tab opened", current_url=await self._safe_page_url(page))

    async def _click_add_source_button(self, page: Any) -> None:
        button = await self._wait_for_visible_locator(
            page,
            PROJECT_ADD_SOURCE_BUTTON_SELECTORS,
            label="project-add-source-button",
            total_timeout_ms=10_000,
        )
        if button is None:
            raise ResponseTimeoutError("Add source button did not become visible")
        await button.click(timeout=5_000)
        await page.wait_for_timeout(500)

    async def _click_source_kind_option(self, page: Any, source_kind: str) -> None:
        selector_map = {
            "link": PROJECT_SOURCE_LINK_TYPE_SELECTORS,
            "text": PROJECT_SOURCE_TEXT_TYPE_SELECTORS,
            "file": PROJECT_SOURCE_FILE_TYPE_SELECTORS,
        }
        selectors = selector_map[source_kind]
        option = await self._wait_for_visible_locator(
            page,
            selectors,
            label=f"project-source-kind-{source_kind}",
            total_timeout_ms=2_500,
            poll_interval_ms=250,
        )
        if option is None:
            self._log("project-source", "source kind option not shown; continuing with default dialog", source_kind=source_kind)
            return
        await option.click(timeout=5_000)
        await page.wait_for_timeout(500)

    async def _fill_locator_text(self, locator: Any, text: str) -> None:
        try:
            await locator.click(timeout=3_000)
        except Exception:
            pass
        try:
            await locator.fill(text)
            return
        except Exception:
            pass
        try:
            await locator.evaluate(
                """
                (el, value) => {
                    const tag = (el.tagName || '').toLowerCase();
                    if (tag === 'input' || tag === 'textarea') {
                        el.value = value;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return;
                    }
                    el.focus();
                    if ('innerText' in el) {
                        el.innerText = value;
                    } else {
                        el.textContent = value;
                    }
                    el.dispatchEvent(new InputEvent('input', { bubbles: true, data: value }));
                }
                """,
                text,
            )
            return
        except Exception:
            pass
        await locator.type(text, delay=10)

    async def _add_project_textual_source(
        self,
        page: Any,
        *,
        source_kind: str,
        value: str,
        display_name: Optional[str],
    ) -> None:
        await self._click_add_source_button(page)
        await self._click_source_kind_option(page, source_kind)
        selectors = PROJECT_SOURCE_LINK_INPUT_SELECTORS if source_kind == "link" else PROJECT_SOURCE_TEXT_INPUT_SELECTORS
        input_locator = await self._wait_for_visible_locator(
            page,
            selectors,
            label=f"project-source-{source_kind}-input",
            total_timeout_ms=10_000,
        )
        if input_locator is None:
            raise ResponseTimeoutError(f"Input for project source kind {source_kind!r} did not become visible")
        await self._fill_locator_text(input_locator, value)

        if display_name:
            title_locator = await self._find_visible_locator(
                page,
                PROJECT_SOURCE_TITLE_INPUT_SELECTORS,
                label="project-source-title-input",
                timeout_ms=800,
            )
            if title_locator is not None:
                await self._fill_locator_text(title_locator, display_name)

        save_button = await self._wait_for_visible_locator(
            page,
            PROJECT_SOURCE_SAVE_BUTTON_SELECTORS,
            label="project-source-save-button",
            total_timeout_ms=10_000,
        )
        if save_button is None:
            raise ResponseTimeoutError("Project source save/add button did not become visible")
        await save_button.click(timeout=5_000)
        await page.wait_for_timeout(1_000)

    async def _add_project_file_source(self, page: Any, *, file_path: str) -> None:
        before_count = await page.locator('input[type="file"]').count()
        await self._click_add_source_button(page)
        await self._click_source_kind_option(page, "file")
        await page.wait_for_timeout(500)

        target = None
        for selector in PROJECT_SOURCE_FILE_INPUT_SELECTORS:
            locator = page.locator(selector)
            count = await self._safe_count(locator, selector)
            if count:
                target = locator.nth(count - 1)
                break
        if target is None:
            raise ResponseTimeoutError(
                f"Project source file input was not found after opening Add source (baseline file inputs={before_count})"
            )
        await target.set_input_files(file_path)
        await page.wait_for_timeout(1_500)

    async def _wait_for_source_presence(self, page: Any, source_match: Optional[str], *, timeout_ms: int = 20_000) -> None:
        if not source_match:
            await page.wait_for_timeout(1_500)
            return
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        while asyncio.get_running_loop().time() < deadline:
            container = await self._find_project_source_container(page, source_match, exact=False)
            if container is not None:
                return
            await page.wait_for_timeout(500)
        raise ResponseTimeoutError(f"Timed out waiting for project source to appear: {source_match}")

    async def _wait_for_source_absence(self, page: Any, source_name: str, *, exact: bool, timeout_ms: int = 20_000) -> None:
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        while asyncio.get_running_loop().time() < deadline:
            container = await self._find_project_source_container(page, source_name, exact=exact)
            if container is None:
                return
            await page.wait_for_timeout(500)
        raise ResponseTimeoutError(f"Timed out waiting for project source to disappear: {source_name}")

    async def _find_project_source_container(self, page: Any, source_name: str, *, exact: bool) -> Optional[Any]:
        needle = re.sub(r"\s+", " ", (source_name or "")).strip()
        if not needle:
            return None
        handle = await page.evaluate_handle(
            """
            ({ needle, exact }) => {
                const normalize = value => (value || '').replace(/\\s+/g, ' ').trim();
                const isVisible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                const nodes = Array.from(document.querySelectorAll('main *, [role="main"] *, body *'));
                for (const el of nodes) {
                    if (!isVisible(el)) continue;
                    const text = normalize(el.textContent);
                    if (!text) continue;
                    const matched = exact ? text === needle : text.includes(needle);
                    if (!matched) continue;
                    let current = el;
                    while (current && current !== document.body) {
                        const buttons = Array.from(current.querySelectorAll('button,[role="button"]')).filter(isVisible);
                        if (buttons.length) return current;
                        current = current.parentElement;
                    }
                }
                return null;
            }
            """,
            {"needle": needle, "exact": exact},
        )
        try:
            return handle.as_element()
        except Exception:
            return None

    async def _find_source_options_button(self, container: Any) -> Optional[Any]:
        try:
            buttons = await container.query_selector_all('button,[role="button"]')
        except Exception:
            return None

        visible_buttons = []
        for button in buttons:
            try:
                if not await button.is_visible():
                    continue
                visible_buttons.append(button)
            except Exception:
                continue

        for button in visible_buttons:
            aria_label = ((await button.get_attribute('aria-label')) or '').strip().lower()
            data_testid = ((await button.get_attribute('data-testid')) or '').strip().lower()
            has_popup = ((await button.get_attribute('aria-haspopup')) or '').strip().lower()
            if any(hint in aria_label for hint in PROJECT_SOURCE_OPTIONS_ARIA_HINTS):
                return button
            if any(hint in data_testid for hint in PROJECT_SOURCE_OPTIONS_ARIA_HINTS):
                return button
            if has_popup == 'menu':
                return button

        return visible_buttons[-1] if visible_buttons else None

    async def _find_current_project_sidebar_container(self, page: Any) -> Optional[Any]:
        project_id = self._extract_project_id_from_url(self._project_home_url())
        if not project_id:
            return None
        handle = await page.evaluate_handle(
            r"""
            ({ projectId, ariaHints }) => {
                const extractProjectId = value => {
                    try {
                        const url = new URL(value, window.location.origin);
                        const match = (url.pathname || '').match(/\/g\/(g-p-[a-z0-9]+)/i);
                        return match ? match[1].toLowerCase() : '';
                    } catch (_) {
                        return '';
                    }
                };
                const isVisible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                const anchors = Array.from(document.querySelectorAll('a[href]')).filter(isVisible);
                for (const anchor of anchors) {
                    const hrefProjectId = extractProjectId(anchor.getAttribute('href') || '');
                    if (!hrefProjectId || hrefProjectId !== projectId) continue;
                    let current = anchor;
                    while (current && current !== document.body) {
                        const buttons = Array.from(current.querySelectorAll('button,[role="button"]')).filter(isVisible);
                        for (const button of buttons) {
                            const aria = (button.getAttribute('aria-label') || '').toLowerCase();
                            const hasPopup = (button.getAttribute('aria-haspopup') || '').toLowerCase();
                            const trailing = button.hasAttribute('data-trailing-button');
                            if (ariaHints.some(hint => aria.includes(hint)) || trailing || hasPopup === 'menu') {
                                return current;
                            }
                        }
                        current = current.parentElement;
                    }
                }
                return null;
            }
            """,
            {"projectId": project_id, "ariaHints": list(PROJECT_OPTIONS_ARIA_HINTS)},
        )
        try:
            return handle.as_element()
        except Exception:
            return None

    async def _find_project_options_button(self, container: Any) -> Optional[Any]:
        try:
            buttons = await container.query_selector_all('button,[role="button"]')
        except Exception:
            return None

        visible_buttons = []
        for button in buttons:
            try:
                if not await button.is_visible():
                    continue
                visible_buttons.append(button)
            except Exception:
                continue

        for button in visible_buttons:
            aria_label = ((await button.get_attribute('aria-label')) or '').strip().lower()
            has_popup = ((await button.get_attribute('aria-haspopup')) or '').strip().lower()
            if any(hint in aria_label for hint in PROJECT_OPTIONS_ARIA_HINTS):
                return button
            if has_popup == 'menu':
                return button
            try:
                if await button.get_attribute('data-trailing-button') is not None:
                    return button
            except Exception:
                pass

        return visible_buttons[-1] if visible_buttons else None

    async def _wait_for_project_absence(self, page: Any, *, deleted_project_url: str, timeout_ms: int = 20_000) -> None:
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        deleted_project_key = self._project_identity_key_from_url(deleted_project_url)
        while asyncio.get_running_loop().time() < deadline:
            current_url = await self._safe_page_url(page)
            current_project_key = self._project_identity_key_from_url(current_url)
            if current_project_key != deleted_project_key or not self._is_project_home_url(current_url):
                return
            container = await self._find_current_project_sidebar_container(page)
            if container is None:
                return
            await page.wait_for_timeout(500)
        raise ResponseTimeoutError(f"Timed out waiting for project to disappear: {deleted_project_url}")

    def _is_project_home_url(self, url: str) -> bool:
        path = urlparse(url).path.rstrip("/")
        return bool(re.search(r'/g/g-p-[^/]+/project$', path)) or path.endswith('/project')

    def _project_conversation_path_prefix(self) -> Optional[str]:
        parsed = urlparse(self.config.project_url)
        path = parsed.path.rstrip("/")
        if path.endswith("/project"):
            return path[:-len("/project")] + "/c/"
        return None

    async def _extract_project_conversation_links(self, page: Any) -> list[str]:
        locator = page.locator('main a[href*="/c/"]')
        try:
            hrefs = await locator.evaluate_all(
                "els => els.map(el => el.getAttribute('href') || '').filter(Boolean)"
            )
        except Exception:
            return []

        prefix = self._project_conversation_path_prefix()
        normalized: list[str] = []
        seen: set[str] = set()
        for href in hrefs or []:
            absolute = urljoin(self.config.project_url, href)
            path = urlparse(absolute).path
            if prefix and not path.startswith(prefix):
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            normalized.append(absolute)
        return normalized

    async def _maybe_open_new_project_conversation(
        self,
        page: Any,
        *,
        response_context: Optional[dict[str, Any]],
        attempt: int,
        elapsed_s: float,
    ) -> Optional[str]:
        current_url = await self._safe_page_url(page)
        if not self._is_project_home_url(current_url):
            return None

        project_links = await self._extract_project_conversation_links(page)
        baseline_links = set((response_context or {}).get("project_conversation_links") or [])
        opened_links = set((response_context or {}).get("opened_project_conversation_links") or [])

        candidate = None
        candidate_reason = None

        # Only follow a conversation that is new relative to the baseline project page.
        # Re-opening an existing link can attach this run to an older thread, which is not desired.
        for href in project_links:
            if href not in baseline_links and href not in opened_links:
                candidate = href
                candidate_reason = "new-project-link"
                break

        if candidate is None:
            if attempt == 1 or attempt % 10 == 0:
                self._log(
                    "response",
                    "project page still waiting for a brand-new conversation link",
                    attempt=attempt,
                    elapsed_s=round(elapsed_s, 1),
                    current_url=current_url,
                    baseline_link_count=len(baseline_links),
                    current_link_count=len(project_links),
                    baseline_first_link=(next(iter(baseline_links)) if baseline_links else None),
                    current_first_link=(project_links[0] if project_links else None),
                )
            return None

        self._log(
            "response",
            "opening project conversation from project page",
            attempt=attempt,
            elapsed_s=round(elapsed_s, 1),
            current_url=current_url,
            candidate_url=candidate,
            reason=candidate_reason,
            baseline_link_count=len(baseline_links),
            current_link_count=len(project_links),
            baseline_first_link=(next(iter(baseline_links)) if baseline_links else None),
            current_first_link=(project_links[0] if project_links else None),
        )
        if response_context is not None:
            response_context.setdefault("opened_project_conversation_links", []).append(candidate)

        await self._goto(page, candidate, label="project-conversation-follow")
        await page.wait_for_timeout(1_500)
        return candidate

    def _preview_text(self, text: Optional[str], max_len: int = 240) -> str:
        normalized = re.sub(r"\s+", " ", (text or "").strip())
        if len(normalized) <= max_len:
            return normalized
        return normalized[: max_len - 3] + "..."

    async def _capture_response_context(self, page: Any) -> dict[str, Any]:
        assistant_selector, assistant_count, assistant_text, assistant_probes = await self._extract_last_text_from_selectors(
            page,
            ASSISTANT_MESSAGE_SELECTORS,
        )
        project_conversation_links = await self._extract_project_conversation_links(page)
        context = {
            "url": await self._safe_page_url(page),
            "assistant_selector": assistant_selector,
            "assistant_count": assistant_count,
            "assistant_text": assistant_text,
            "assistant_probes": assistant_probes,
            "project_conversation_links": project_conversation_links,
        }
        self._log(
            "response",
            "captured baseline response context",
            url=context["url"],
            assistant_selector=assistant_selector,
            assistant_count=assistant_count,
            assistant_text_length=len(assistant_text),
            assistant_preview=self._preview_text(assistant_text, 160),
            project_conversation_link_count=len(project_conversation_links),
        )
        return context

    def _summarize_probes(self, probes: list[dict[str, Any]]) -> str:
        parts = []
        for probe in probes:
            selector = probe.get("selector", "<unknown>")
            parts.append(
                f"{selector}:count={probe.get('count', 0)},visible={probe.get('visible', False)},"
                f"text_length={probe.get('text_length', 0)},parsed={probe.get('parsed', False)}"
            )
        return " || ".join(parts)

    async def _build_response_diagnostics(
        self,
        page: Any,
        *,
        probes: list[dict[str, Any]],
        response_context: Optional[dict[str, Any]],
        attempt: int,
        elapsed_s: float,
    ) -> str:
        current_url = await self._safe_page_url(page)
        assistant_selector, assistant_count, assistant_text, live_probes = await self._extract_last_text_from_selectors(
            page,
            ASSISTANT_MESSAGE_SELECTORS,
        )

        submit_state = await self._probe_submit_button_state(page)

        lines = [
            f"timestamp: {self._timestamp()}",
            f"driver: {self.driver_name}",
            f"project_url: {self.config.project_url}",
            f"current_url: {current_url}",
            f"attempt: {attempt}",
            f"elapsed_s: {elapsed_s:.1f}",
            f"assistant_selector: {assistant_selector}",
            f"assistant_count: {assistant_count}",
            f"assistant_text_length: {len(assistant_text)}",
            f"assistant_preview: {self._preview_text(assistant_text, 1200)}",
            f"submit_selector: {submit_state.get('selector')}",
            f"submit_count: {submit_state.get('count')}",
            f"submit_visible: {submit_state.get('visible')}",
            f"submit_enabled: {submit_state.get('enabled')}",
            f"submit_aria_label: {submit_state.get('aria_label')}",
            f"submit_data_testid: {submit_state.get('data_testid')}",
            f"submit_send_ready: {submit_state.get('send_ready')}",
            f"submit_stop_visible: {submit_state.get('stop_visible')}",
        ]
        current_project_links = await self._extract_project_conversation_links(page)
        lines.extend([
            f"project_conversation_link_count: {len(current_project_links)}",
            f"project_conversation_links: {' | '.join(current_project_links[:10])}",
        ])
        if response_context:
            baseline_text = response_context.get("assistant_text", "") or ""
            baseline_links = response_context.get("project_conversation_links") or []
            opened_links = response_context.get("opened_project_conversation_links") or []
            lines.extend([
                f"baseline_url: {response_context.get('url')}",
                f"baseline_assistant_selector: {response_context.get('assistant_selector')}",
                f"baseline_assistant_count: {response_context.get('assistant_count')}",
                f"baseline_assistant_text_length: {len(baseline_text)}",
                f"baseline_assistant_preview: {self._preview_text(baseline_text, 400)}",
                f"assistant_text_changed: {assistant_text != baseline_text}",
                f"baseline_project_conversation_link_count: {len(baseline_links)}",
                f"baseline_project_conversation_links: {' | '.join(baseline_links[:10])}",
                f"opened_project_conversation_links: {' | '.join(opened_links[:10])}",
            ])
        lines.append("live_selector_probes:")
        if not live_probes:
            lines.append("  <no live probes>")
        for probe in live_probes:
            lines.extend([
                f"  selector: {probe.get('selector')}",
                f"    count: {probe.get('count')}",
                f"    visible: {probe.get('visible')}",
                f"    text_length: {probe.get('text_length')}",
                f"    preview: {probe.get('preview')}",
            ])
        lines.append("selector_probes:")
        if not probes:
            lines.append("  <no probes>")
        for probe in probes:
            lines.extend([
                f"  selector: {probe.get('selector')}",
                f"    count: {probe.get('count')}",
                f"    visible: {probe.get('visible')}",
                f"    text_length: {probe.get('text_length')}",
                f"    parsed: {probe.get('parsed')}",
                f"    preview: {probe.get('preview')}",
            ])
        return "\n".join(lines)

    async def _save_response_diagnostics(
        self,
        page: Any,
        *,
        probes: list[dict[str, Any]],
        response_context: Optional[dict[str, Any]],
        attempt: int,
        elapsed_s: float,
        include_page_artifacts: bool,
    ) -> None:
        if not self.config.debug:
            return
        stamp = self._timestamp_for_filename()
        base = self._artifact_dir / f"response_wait_{stamp}"
        report = await self._build_response_diagnostics(
            page,
            probes=probes,
            response_context=response_context,
            attempt=attempt,
            elapsed_s=elapsed_s,
        )
        await self._write_text(base.with_suffix(".txt"), report)

        if not include_page_artifacts:
            return

        if self.config.save_html:
            try:
                html_path = base.with_suffix(".html")
                html = await page.content()
                await self._write_text(html_path, html)
                self._log("artifact", "saved response wait html snapshot", path=str(html_path))
            except Exception as artifact_exc:
                self._log("artifact", "failed to save response wait html snapshot", error=str(artifact_exc))

        if self.config.save_screenshot:
            try:
                screenshot_path = base.with_suffix(".png")
                await page.screenshot(path=str(screenshot_path), full_page=True)
                self._log("artifact", "saved response wait screenshot", path=str(screenshot_path))
            except Exception as artifact_exc:
                self._log("artifact", "failed to save response wait screenshot", error=str(artifact_exc))

    async def _try_extract_json_payload(
        self,
        page: Any,
    ) -> tuple[Optional[Any], Optional[str], int, list[dict[str, Any]]]:
        probes: list[dict[str, Any]] = []
        for selector in JSON_BLOCK_SELECTORS:
            locator = page.locator(selector)
            count = await locator.count()
            visible = False
            payload_text = ""
            if count:
                last = locator.last
                try:
                    visible = await last.is_visible(timeout=1_000)
                except Exception:
                    visible = False
                payload_text = await self._extract_text_from_locator(last)
            parsed = self._extract_json_from_text(payload_text) if payload_text else None
            probes.append({
                "selector": selector,
                "count": count,
                "visible": visible,
                "text_length": len(payload_text),
                "parsed": parsed is not None,
                "preview": self._preview_text(payload_text, 220),
            })
            if count:
                self._log(
                    "response",
                    "json selector probe",
                    selector=selector,
                    count=count,
                    visible=visible,
                    text_length=len(payload_text),
                    parsed=parsed is not None,
                )
            if parsed is not None:
                return parsed, selector, len(payload_text), probes

        assistant_selector, assistant_count, assistant_text, assistant_probes = await self._extract_last_text_from_selectors(
            page,
            ASSISTANT_MESSAGE_SELECTORS,
        )
        parsed = self._extract_json_from_text(assistant_text) if assistant_text else None
        probes.extend(assistant_probes)
        if assistant_count:
            self._log(
                "response",
                "assistant text fallback probe",
                selector=assistant_selector,
                count=assistant_count,
                text_length=len(assistant_text),
                parsed=parsed is not None,
            )
        if parsed is not None:
            return parsed, assistant_selector, len(assistant_text), probes

        return None, None, 0, probes

    def _assistant_response_changed(self, response_context: Optional[dict[str, Any]], *, count: int, text: str) -> bool:
        if not text.strip():
            return False
        if response_context is None:
            return True
        baseline_count = int(response_context.get("assistant_count") or 0)
        baseline_text = (response_context.get("assistant_text") or "").strip()
        if count > baseline_count:
            return True
        if text != baseline_text:
            return True
        return False

    async def _wait_and_get_response(
        self,
        page: Any,
        *,
        response_context: Optional[dict[str, Any]] = None,
    ) -> str:
        self._log(
            "response",
            "waiting for assistant response",
            selectors=ASSISTANT_MESSAGE_SELECTORS,
            timeout_ms=self.config.response_timeout_ms,
        )
        start = asyncio.get_running_loop().time()
        deadline = start + (self.config.response_timeout_ms / 1000)
        attempt = 0
        last_diagnostic_dump = -30.0
        last_probe_summary = ""
        stable_required = 3
        poll_interval_ms = 500
        last_candidate_text = ""
        stable_polls = 0
        first_response_seen_at: Optional[float] = None
        observed_running_state = False
        observed_idle_after_running = False
        min_completion_delay_s = 1.0

        while asyncio.get_running_loop().time() < deadline:
            attempt += 1
            elapsed_s = asyncio.get_running_loop().time() - start

            await self._maybe_open_new_project_conversation(
                page,
                response_context=response_context,
                attempt=attempt,
                elapsed_s=elapsed_s,
            )

            assistant_selector, assistant_count, assistant_text, probes = await self._extract_last_text_from_selectors(
                page,
                ASSISTANT_MESSAGE_SELECTORS,
            )
            probe_summary = self._summarize_probes(probes)
            submit_state = await self._probe_submit_button_state(page)
            thinking_state = await self._probe_thinking_state(page)
            running_now = bool(submit_state.get("stop_visible") or thinking_state.get("visible"))
            idle_now = bool(observed_running_state and not submit_state.get("stop_visible") and not thinking_state.get("visible"))

            if running_now:
                observed_running_state = True
            elif idle_now:
                observed_idle_after_running = True

            has_response = self._assistant_response_changed(response_context, count=assistant_count, text=assistant_text)
            candidate_text = assistant_text.strip()
            if has_response and candidate_text:
                if first_response_seen_at is None:
                    first_response_seen_at = asyncio.get_running_loop().time()
                    self._log(
                        "response",
                        "assistant response detected; waiting for completion signals",
                        selector=assistant_selector,
                        attempt=attempt,
                        elapsed_s=round(elapsed_s, 1),
                        text_length=len(candidate_text),
                        preview=self._preview_text(candidate_text, 160),
                    )

                if candidate_text == last_candidate_text:
                    stable_polls += 1
                else:
                    previous_length = len(last_candidate_text)
                    last_candidate_text = candidate_text
                    stable_polls = 0
                    self._log(
                        "response",
                        "assistant response updated",
                        selector=assistant_selector,
                        attempt=attempt,
                        elapsed_s=round(elapsed_s, 1),
                        text_length=len(candidate_text),
                        previous_length=previous_length,
                        preview=self._preview_text(candidate_text, 160),
                    )

                stable_elapsed_s = 0.0
                if first_response_seen_at is not None:
                    stable_elapsed_s = asyncio.get_running_loop().time() - first_response_seen_at

                completion_ready = bool(
                    observed_running_state
                    and observed_idle_after_running
                    and not submit_state.get("stop_visible")
                    and not thinking_state.get("visible")
                )
                if completion_ready and stable_polls >= stable_required and stable_elapsed_s >= min_completion_delay_s:
                    self._log(
                        "response",
                        "assistant response stabilized",
                        selector=assistant_selector,
                        attempt=attempt,
                        elapsed_s=round(elapsed_s, 1),
                        text_length=len(candidate_text),
                        stable_polls=stable_polls,
                        submit_selector=submit_state.get("selector"),
                        submit_aria_label=submit_state.get("aria_label"),
                        submit_data_testid=submit_state.get("data_testid"),
                        submit_idle_visible=submit_state.get("idle_visible"),
                        submit_visible_enabled_count=submit_state.get("visible_enabled_count"),
                        thinking_visible=thinking_state.get("visible"),
                        thinking_text=thinking_state.get("text"),
                        observed_running_state=observed_running_state,
                        observed_idle_after_running=observed_idle_after_running,
                        preview=self._preview_text(candidate_text, 160),
                    )
                    if self.config.debug:
                        await self._save_response_diagnostics(
                            page,
                            probes=probes,
                            response_context=response_context,
                            attempt=attempt,
                            elapsed_s=elapsed_s,
                            include_page_artifacts=False,
                        )
                    return candidate_text

            if attempt == 1 or attempt % 10 == 0 or probe_summary != last_probe_summary:
                self._log(
                    "response",
                    "assistant wait poll",
                    attempt=attempt,
                    elapsed_s=round(elapsed_s, 1),
                    current_url=await self._safe_page_url(page),
                    probe_summary=probe_summary,
                    stable_polls=stable_polls,
                    submit_selector=submit_state.get("selector"),
                    submit_send_ready=submit_state.get("send_ready"),
                    submit_idle_visible=submit_state.get("idle_visible"),
                    submit_visible_enabled_count=submit_state.get("visible_enabled_count"),
                    submit_aria_label=submit_state.get("aria_label"),
                    submit_data_testid=submit_state.get("data_testid"),
                    submit_stop_visible=submit_state.get("stop_visible"),
                    thinking_visible=thinking_state.get("visible"),
                    thinking_text=thinking_state.get("text"),
                    running_now=running_now,
                    observed_running_state=observed_running_state,
                    observed_idle_after_running=observed_idle_after_running,
                )
                last_probe_summary = probe_summary

            if self.config.debug and (elapsed_s - last_diagnostic_dump >= 30.0):
                await self._save_response_diagnostics(
                    page,
                    probes=probes,
                    response_context=response_context,
                    attempt=attempt,
                    elapsed_s=elapsed_s,
                    include_page_artifacts=False,
                )
                last_diagnostic_dump = elapsed_s

            await page.wait_for_timeout(poll_interval_ms)

        elapsed_s = asyncio.get_running_loop().time() - start
        await self._maybe_open_new_project_conversation(
            page,
            response_context=response_context,
            attempt=attempt,
            elapsed_s=elapsed_s,
        )
        assistant_selector, assistant_count, assistant_text, probes = await self._extract_last_text_from_selectors(
            page,
            ASSISTANT_MESSAGE_SELECTORS,
        )
        submit_state = await self._probe_submit_button_state(page)
        if self.config.debug:
            await self._save_response_diagnostics(
                page,
                probes=probes,
                response_context=response_context,
                attempt=attempt,
                elapsed_s=elapsed_s,
                include_page_artifacts=True,
            )
        raise ResponseTimeoutError(
            f"Timed out waiting for an assistant response (last selector={assistant_selector}, count={assistant_count}, text_length={len(assistant_text)}, stable_polls={stable_polls}, send_ready={submit_state.get('send_ready')})"
        )

    async def _wait_and_get_json(self, page: Any, response_context: Optional[dict[str, Any]] = None) -> Any:
        self._log(
            "response",
            "waiting for parseable JSON response",
            selectors=JSON_BLOCK_SELECTORS,
            timeout_ms=self.config.response_timeout_ms,
        )
        start = asyncio.get_running_loop().time()
        deadline = start + (self.config.response_timeout_ms / 1000)
        attempt = 0
        last_diagnostic_dump = -30.0
        last_probe_summary = ""
        stable_required = 2
        poll_interval_ms = 500
        last_payload_signature = ""
        stable_polls = 0
        first_payload_seen_at: Optional[float] = None
        observed_running_state = False
        observed_idle_after_running = False
        min_completion_delay_s = 1.0

        while asyncio.get_running_loop().time() < deadline:
            attempt += 1
            elapsed_s = asyncio.get_running_loop().time() - start

            await self._maybe_open_new_project_conversation(
                page,
                response_context=response_context,
                attempt=attempt,
                elapsed_s=elapsed_s,
            )

            payload, selector, text_length, probes = await self._try_extract_json_payload(page)
            probe_summary = self._summarize_probes(probes)
            submit_state = await self._probe_submit_button_state(page)
            thinking_state = await self._probe_thinking_state(page)
            running_now = bool(submit_state.get("stop_visible") or thinking_state.get("visible"))
            idle_now = bool(observed_running_state and not submit_state.get("stop_visible") and not thinking_state.get("visible"))

            if running_now:
                observed_running_state = True
            elif idle_now:
                observed_idle_after_running = True

            if payload is not None:
                payload_signature = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                if first_payload_seen_at is None:
                    first_payload_seen_at = asyncio.get_running_loop().time()
                    self._log(
                        "response",
                        "parseable json payload detected; waiting for completion signals",
                        selector=selector,
                        attempt=attempt,
                        elapsed_s=round(elapsed_s, 1),
                        text_length=text_length,
                    )

                if payload_signature == last_payload_signature:
                    stable_polls += 1
                else:
                    last_payload_signature = payload_signature
                    stable_polls = 0
                    self._log(
                        "response",
                        "parseable json payload updated",
                        selector=selector,
                        attempt=attempt,
                        elapsed_s=round(elapsed_s, 1),
                        text_length=text_length,
                        stable_polls=stable_polls,
                    )

                stable_elapsed_s = 0.0
                if first_payload_seen_at is not None:
                    stable_elapsed_s = asyncio.get_running_loop().time() - first_payload_seen_at

                completion_ready = bool(
                    observed_running_state
                    and observed_idle_after_running
                    and not submit_state.get("stop_visible")
                    and not thinking_state.get("visible")
                )
                if completion_ready and stable_polls >= stable_required and stable_elapsed_s >= min_completion_delay_s:
                    self._log(
                        "response",
                        "parseable json payload stabilized",
                        selector=selector,
                        attempt=attempt,
                        elapsed_s=round(elapsed_s, 1),
                        text_length=text_length,
                        stable_polls=stable_polls,
                        submit_selector=submit_state.get("selector"),
                        submit_aria_label=submit_state.get("aria_label"),
                        submit_data_testid=submit_state.get("data_testid"),
                        submit_idle_visible=submit_state.get("idle_visible"),
                        submit_visible_enabled_count=submit_state.get("visible_enabled_count"),
                        thinking_visible=thinking_state.get("visible"),
                        thinking_text=thinking_state.get("text"),
                        observed_running_state=observed_running_state,
                        observed_idle_after_running=observed_idle_after_running,
                    )
                    if self.config.debug:
                        await self._save_response_diagnostics(
                            page,
                            probes=probes,
                            response_context=response_context,
                            attempt=attempt,
                            elapsed_s=elapsed_s,
                            include_page_artifacts=False,
                        )
                    return payload

            if attempt == 1 or attempt % 10 == 0 or probe_summary != last_probe_summary:
                self._log(
                    "response",
                    "json wait poll",
                    attempt=attempt,
                    elapsed_s=round(elapsed_s, 1),
                    current_url=await self._safe_page_url(page),
                    probe_summary=probe_summary,
                    stable_polls=stable_polls,
                    submit_selector=submit_state.get("selector"),
                    submit_send_ready=submit_state.get("send_ready"),
                    submit_idle_visible=submit_state.get("idle_visible"),
                    submit_visible_enabled_count=submit_state.get("visible_enabled_count"),
                    submit_aria_label=submit_state.get("aria_label"),
                    submit_data_testid=submit_state.get("data_testid"),
                    submit_stop_visible=submit_state.get("stop_visible"),
                    thinking_visible=thinking_state.get("visible"),
                    thinking_text=thinking_state.get("text"),
                    running_now=running_now,
                    observed_running_state=observed_running_state,
                    observed_idle_after_running=observed_idle_after_running,
                )
                last_probe_summary = probe_summary

            if self.config.debug and (elapsed_s - last_diagnostic_dump >= 30.0):
                await self._save_response_diagnostics(
                    page,
                    probes=probes,
                    response_context=response_context,
                    attempt=attempt,
                    elapsed_s=elapsed_s,
                    include_page_artifacts=False,
                )
                last_diagnostic_dump = elapsed_s

            await page.wait_for_timeout(poll_interval_ms)

        elapsed_s = asyncio.get_running_loop().time() - start
        await self._maybe_open_new_project_conversation(
            page,
            response_context=response_context,
            attempt=attempt,
            elapsed_s=elapsed_s,
        )
        payload, selector, text_length, probes = await self._try_extract_json_payload(page)
        submit_state = await self._probe_submit_button_state(page)
        if self.config.debug:
            await self._save_response_diagnostics(
                page,
                probes=probes,
                response_context=response_context,
                attempt=attempt,
                elapsed_s=elapsed_s,
                include_page_artifacts=True,
            )
        raise ResponseTimeoutError(
            f"Timed out waiting for parseable JSON in the assistant response (last selector={selector}, text_length={text_length}, stable_polls={stable_polls}, send_ready={submit_state.get('send_ready')})"
        )

    async def _goto(self, page: Any, url: str, *, label: str) -> None:
        current_url = await self._safe_page_url(page)
        self._log("nav", "navigating", label=label, from_url=current_url, to_url=url)
        await page.goto(url, wait_until="domcontentloaded")
        self._log("nav", "domcontentloaded reached", label=label, current_url=await self._safe_page_url(page), title=await self._safe_page_title(page))

    async def _wait_for_challenge_resolution(self, page: Any, *, label: str) -> None:
        current_url = await self._safe_page_url(page)
        current_title = await self._safe_page_title(page)
        if not self._looks_like_challenge(current_url, current_title):
            return

        timeout_ms = self.config.challenge_wait_timeout_ms
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        attempt = 0
        self._log(
            "challenge",
            "challenge indicators detected; waiting for page to settle",
            label=label,
            current_url=current_url,
            title=current_title,
            timeout_ms=timeout_ms,
        )
        while asyncio.get_running_loop().time() < deadline:
            attempt += 1
            await page.wait_for_timeout(1000)
            current_url = await self._safe_page_url(page)
            current_title = await self._safe_page_title(page)
            has_input = await self._has_chat_input(page)
            login_visible = await self._find_visible_locator(page, LOGIN_BUTTON_SELECTORS, label="challenge-login-indicator") is not None
            if has_input or login_visible or not self._looks_like_challenge(current_url, current_title):
                self._log(
                    "challenge",
                    "challenge settle loop finished",
                    label=label,
                    attempt=attempt,
                    current_url=current_url,
                    title=current_title,
                    has_input=has_input,
                    login_visible=login_visible,
                )
                return
            self._log(
                "challenge",
                "challenge still active",
                label=label,
                attempt=attempt,
                current_url=current_url,
                title=current_title,
            )

    def _looks_like_challenge(self, url: str, title: str) -> bool:
        normalized_url = (url or "").lower()
        normalized_title = (title or "").strip().lower()
        if "__cf_chl_rt_tk=" in normalized_url:
            return True
        if normalized_title in {"", "just a moment...", "just a moment", "checking your browser"}:
            return True
        return any(hint.lower() in normalized_url or hint.lower() in normalized_title for hint in CLOUDFLARE_CHALLENGE_HINTS)

    async def _safe_count(self, locator: Any, selector: str) -> int:
        try:
            return await locator.count()
        except Exception as exc:
            self._log("selector", "count failed", selector=selector, error=str(exc))
            return 0

    async def _safe_page_url(self, page: Any) -> str:
        try:
            return page.url
        except Exception:
            return "<url-unavailable>"

    async def _safe_page_title(self, page: Any) -> str:
        try:
            return await page.title()
        except Exception:
            return "<title-unavailable>"

    def _is_google_auth_url(self, url: str) -> bool:
        normalized = (url or "").lower()
        return (
            "accounts.google.com" in normalized
            or "signin/oauth" in normalized
            or "servicelogin" in normalized
            or "oauth" in normalized and "google" in normalized
        )

    def _attach_context_debug(self, context: Any, page: Any, operation_name: str) -> None:
        if not self.config.debug:
            return

        def log_console(msg: Any) -> None:
            try:
                self._log("browser-console", msg.text, msg_type=msg.type, location=str(getattr(msg, "location", None)))
            except Exception as exc:
                self._log("browser-console", "failed to process console event", error=str(exc))

        def log_pageerror(exc: Any) -> None:
            self._log("browser-pageerror", str(exc))

        def log_request_failed(req: Any) -> None:
            failure_text = None
            try:
                failure = req.failure
                failure_text = failure if isinstance(failure, str) else getattr(failure, "error_text", None)
            except Exception:
                failure_text = None
            self._log(
                "browser-requestfailed",
                "request failed",
                method=req.method,
                url=req.url,
                failure=failure_text,
            )

        def log_response(resp: Any) -> None:
            status = getattr(resp, "status", None)
            if status and status >= 400:
                self._log("browser-response", "http error response", status=status, url=resp.url)

        def log_page_created(new_page: Any) -> None:
            self._log("browser-page", "new page detected", operation=operation_name, url=new_page.url)
            self._attach_page_debug(new_page)

        context.on("page", log_page_created)
        self._attach_page_debug(page)
        context.on("requestfailed", log_request_failed)
        context.on("response", log_response)
        self._log("debug", "browser debug hooks attached", operation=operation_name)

    def _attach_page_debug(self, page: Any) -> None:
        if not self.config.debug:
            return
        page.on("console", lambda msg: self._log("browser-console", msg.text, msg_type=msg.type))
        page.on("pageerror", lambda exc: self._log("browser-pageerror", str(exc)))
        page.on("framenavigated", lambda frame: self._on_frame_navigated(frame, page))
        self._log("debug", "page debug hooks attached", url=page.url)

    def _on_frame_navigated(self, frame: Any, page: Any) -> None:
        if not self.config.debug:
            return
        try:
            if frame == page.main_frame:
                self._log("browser-nav", "main frame navigated", url=frame.url)
        except Exception as exc:
            self._log("browser-nav", "frame navigation logging failed", error=str(exc))

    async def _dump_failure_artifacts(self, page: Any, operation_name: str, exc: Exception) -> None:
        if not self.config.debug:
            return
        stamp = self._timestamp_for_filename()
        base = self._artifact_dir / f"{operation_name}_{stamp}"
        await self._write_text(base.with_suffix(".txt"), self._format_failure_report(page, exc))

        if self.config.save_html:
            try:
                html_path = base.with_suffix(".html")
                html = await page.content()
                await self._write_text(html_path, html)
                self._log("artifact", "saved html snapshot", path=str(html_path))
            except Exception as artifact_exc:
                self._log("artifact", "failed to save html snapshot", error=str(artifact_exc))

        if self.config.save_screenshot:
            try:
                screenshot_path = base.with_suffix(".png")
                await page.screenshot(path=str(screenshot_path), full_page=True)
                self._log("artifact", "saved screenshot", path=str(screenshot_path))
            except Exception as artifact_exc:
                self._log("artifact", "failed to save screenshot", error=str(artifact_exc))

    async def _finalize_context(self, context: Any, operation_name: str) -> None:
        if self.config.debug and self.config.save_trace:
            trace_path = self._artifact_dir / f"{operation_name}_{self._timestamp_for_filename()}.trace.zip"
            try:
                await context.tracing.stop(path=str(trace_path))
                self._log("artifact", "saved trace archive", path=str(trace_path))
            except Exception as exc:
                self._log("artifact", "failed to save trace archive", error=str(exc))
        self._log("driver", "closing browser context")
        await context.close()
        self._log("driver", "browser context closed")

    async def _write_text(self, path: Path, text: str) -> None:
        await asyncio.to_thread(path.write_text, text, "utf-8")
        self._log("artifact", "saved text artifact", path=str(path))

    def _format_failure_report(self, page: Any, exc: Exception) -> str:
        return "\n".join(
            [
                f"timestamp: {self._timestamp()}",
                f"driver: {self.driver_name}",
                f"project_url: {self.config.project_url}",
                f"profile_dir: {self.config.profile_dir}",
                f"headless: {self.config.headless}",
                f"current_url: {getattr(page, 'url', '<url-unavailable>')}",
                f"error_type: {type(exc).__name__}",
                f"error: {exc}",
                "traceback:",
                traceback.format_exc(),
            ]
        )

    def _log(self, stage: str, message: str, **fields: Any) -> None:
        timestamp = self._timestamp()
        base = f"[{timestamp}] [{stage}] {message}"
        if fields:
            rendered = " ".join(f"{key}={self._safe_repr(value)}" for key, value in fields.items())
            print(f"{base} | {rendered}", flush=True)
        else:
            print(base, flush=True)

    @staticmethod
    def _safe_repr(value: Any) -> str:
        text = repr(value)
        return text if len(text) <= 240 else text[:237] + "..."

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    @staticmethod
    def _timestamp_for_filename() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


async def ask_chatgpt(
    project_url: str,
    email: Optional[str],
    password: Optional[str],
    prompt: str,
    file_path: Optional[str] = None,
    expect_json: bool = False,
    profile_dir: str = ".profiles/chatgpt",
    headless: bool = False,
    use_patchright: bool = True,
) -> Any:
    client = ChatGPTBrowserClient(
        ChatGPTBrowserConfig(
            project_url=project_url,
            email=email,
            password=password,
            profile_dir=profile_dir,
            headless=headless,
            use_patchright=use_patchright,
        )
    )
    return await client.ask_question(
        prompt=prompt,
        file_path=file_path,
        expect_json=expect_json,
    )

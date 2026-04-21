from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from .config import ChatGPTBrowserConfig
from .exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
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
    'section[data-testid*="conversation-turn"][data-turn="assistant"]',
    'section[data-turn="assistant"]',
    '[data-testid*="conversation-turn"][data-turn="assistant"]',
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
PROJECT_CHATS_TAB_SELECTORS = [
    '[role="tab"]:has-text("Chats")',
    'button:has-text("Chats")',
    'a:has-text("Chats")',
]
PROJECT_SOURCES_PANEL_SELECTORS = [
    '[role="tabpanel"][data-state="active"]',
    '[role="tabpanel"]',
]
PROJECT_ADD_SOURCE_BUTTON_SELECTORS = [
    '[role="tabpanel"][data-state="active"] button:has-text("Add source")',
    '[role="tabpanel"][data-state="active"] button:has-text("Add Source")',
    '[role="tabpanel"][data-state="active"] [aria-label*="Add source" i]',
    '[role="tabpanel"][data-state="active"] button:has-text("Add")',
    '[role="tabpanel"] button:has-text("Add")',
    'button:has-text("Add source")',
    'button:has-text("Add Source")',
    '[aria-label*="Add source" i]',
]
PROJECT_SOURCE_DIALOG_SCOPE_SELECTORS = [
    '[role="dialog"]',
    'dialog[open]',
]
PROJECT_SOURCE_OPTION_DISCOVERY_ROOT_SELECTORS = [
    '[role="dialog"]',
    'dialog[open]',
    '[role="menu"]',
    '[data-radix-popper-content-wrapper]',
]
PROJECT_SOURCE_OPTION_KIND_ALIASES: dict[str, tuple[str, ...]] = {
    'link': ('link', 'website', 'url'),
    'text': ('text input', 'text'),
    'file': ('upload', 'file', 'files'),
    'gdrive': ('google drive', 'drive'),
    'slack': ('slack',),
}
PROJECT_SOURCE_LINK_TYPE_SELECTORS = [
    '[role="dialog"] [role="menuitem"]:has-text("Link")',
    'dialog[open] [role="menuitem"]:has-text("Link")',
    '[role="menu"] [role="menuitem"]:has-text("Link")',
    '[data-radix-popper-content-wrapper] [role="menuitem"]:has-text("Link")',
    '[role="dialog"] button:has-text("Link")',
    'dialog[open] button:has-text("Link")',
    '[role="menu"] button:has-text("Link")',
    '[data-radix-popper-content-wrapper] button:has-text("Link")',
    '[role="dialog"] button:has-text("Website")',
    '[role="menu"] button:has-text("Website")',
    'button:has-text("Link")',
]
PROJECT_SOURCE_TEXT_TYPE_SELECTORS = [
    '[role="dialog"] [role="menuitem"]:has-text("Text")',
    'dialog[open] [role="menuitem"]:has-text("Text")',
    '[role="menu"] [role="menuitem"]:has-text("Text")',
    '[data-radix-popper-content-wrapper] [role="menuitem"]:has-text("Text")',
    '[role="dialog"] button:has-text("Text")',
    '[role="dialog"] button:has-text("Text input")',
    'dialog[open] button:has-text("Text")',
    'dialog[open] button:has-text("Text input")',
    '[role="menu"] button:has-text("Text")',
    '[role="menu"] button:has-text("Text input")',
    '[data-radix-popper-content-wrapper] button:has-text("Text")',
    '[data-radix-popper-content-wrapper] button:has-text("Text input")',
    '[role="dialog"] button:has-text("Quick text")',
    '[role="menu"] button:has-text("Quick text")',
    '[role="dialog"] button:has-text("Notes")',
    '[role="menu"] button:has-text("Notes")',
    'button:has-text("Text")',
    'button:has-text("Text input")',
]
PROJECT_SOURCE_FILE_TYPE_SELECTORS = [
    '[role="dialog"] [role="menuitem"]:has-text("File")',
    'dialog[open] [role="menuitem"]:has-text("File")',
    '[role="menu"] [role="menuitem"]:has-text("File")',
    '[data-radix-popper-content-wrapper] [role="menuitem"]:has-text("File")',
    '[role="dialog"] button:has-text("File")',
    'dialog[open] button:has-text("File")',
    '[role="menu"] button:has-text("File")',
    '[data-radix-popper-content-wrapper] button:has-text("File")',
    '[role="dialog"] button:has-text("Upload")',
    '[role="menu"] button:has-text("Upload")',
    '[role="dialog"] button:has-text("Files")',
    '[role="menu"] button:has-text("Files")',
    'button:has-text("File")',
    'button:has-text("Upload")',
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
    '[role="dialog"] [role="textbox"]',
    '[role="dialog"] input[type="text"]',
    'dialog[open] textarea',
    'dialog[open] [contenteditable="true"]',
    'dialog[open] [role="textbox"]',
    'dialog[open] input[type="text"]',
]
PROJECT_SOURCE_TEXT_BODY_SELECTORS = [
    '[role="dialog"] textarea',
    '[role="dialog"] [contenteditable="true"]',
    '[role="dialog"] [role="textbox"]:not(input)',
    'dialog[open] textarea',
    'dialog[open] [contenteditable="true"]',
    'dialog[open] [role="textbox"]:not(input)',
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
RATE_LIMIT_MODAL_SELECTORS = [
    '[data-testid="modal-conversation-history-rate-limit"]',
    '#modal-conversation-history-rate-limit',
    '[role="dialog"]:has-text("Too many requests")',
    '[role="dialog"]:has-text("temporarily limited access to your conversations")',
    '[role="dialog"]:has-text("protect your data")',
    'dialog[open]:has-text("Too many requests")',
    'dialog[open]:has-text("temporarily limited access to your conversations")',
    'div[role="alertdialog"]:has-text("Too many requests")',
    'div:has-text("Too many requests"):has-text("protect your data")',
]
RATE_LIMIT_MODAL_ACK_SELECTORS = [
    '[data-testid="modal-conversation-history-rate-limit"] button:has-text("Got it")',
    '#modal-conversation-history-rate-limit button:has-text("Got it")',
    '[role="dialog"]:has-text("Too many requests") button:has-text("Got it")',
    '[role="dialog"]:has-text("protect your data") button:has-text("Got it")',
    'dialog[open]:has-text("Too many requests") button:has-text("Got it")',
    'div[role="alertdialog"]:has-text("Too many requests") button:has-text("Got it")',
    'button:has-text("Got it")',
]
CONVERSATION_HISTORY_RATE_LIMIT_PATH_FRAGMENTS = (
    '/backend-api/conversations',
    '/backend-api/conversation/',
)
_PROFILE_LAST_CONTEXT_CLOSED_AT: dict[str, float] = {}
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
PROJECT_MORE_BUTTON_SELECTORS = [
    '[data-sidebar-item="true"][aria-haspopup="menu"]:has-text("More")',
    '[data-sidebar-item="true"]:has-text("More")',
    'div[data-sidebar-item="true"]:has-text("More")',
    'aside [data-sidebar-item="true"]:has-text("More")',
    'nav [data-sidebar-item="true"]:has-text("More")',
    'button:has-text("More")',
    'a:has-text("More")',
    '[role="button"]:has-text("More")',
    'summary:has-text("More")',
    '[aria-haspopup="menu"]:has-text("More")',
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
    '[role="menuitem"]:has-text("Delete Project")',
    '[role="menuitem"]:has-text("Delete this project")',
    '[role="menuitem"]:has-text("Remove project")',
    '[role="menuitem"]:has-text("Delete")',
    '[role="menuitem"]:has-text("Remove")',
    'button:has-text("Delete project")',
    'button:has-text("Delete Project")',
    'button:has-text("Delete this project")',
    'button:has-text("Remove project")',
    'button:has-text("Delete")',
    'button:has-text("Remove")',
    '[aria-label*="Delete project" i]',
]
PROJECT_REMOVE_SETTINGS_SELECTORS = [
    '[role="menuitem"]:has-text("Settings")',
    'button:has-text("Settings")',
    '[aria-label*="settings" i]',
]
PROJECT_CONFIRM_REMOVE_SELECTORS = [
    '[role="dialog"] button:has-text("Delete project")',
    '[role="dialog"] button:has-text("Delete Project")',
    '[role="dialog"] button:has-text("Delete this project")',
    '[role="dialog"] button:has-text("Remove project")',
    '[role="dialog"] button:has-text("Delete")',
    '[role="dialog"] button:has-text("Remove")',
    'dialog[open] button:has-text("Delete project")',
    'dialog[open] button:has-text("Delete Project")',
    'dialog[open] button:has-text("Delete this project")',
    'dialog[open] button:has-text("Remove project")',
    'dialog[open] button:has-text("Delete")',
    'dialog[open] button:has-text("Remove")',
]
PROJECT_PAGE_DETAILS_MENU_SELECTORS = [
    'button[aria-label="Show project details"]',
    'button[aria-label*="project details" i]',
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
        self._profile_key = str(Path(self.config.profile_dir).expanduser().resolve())
        self._rate_limit_cooldown_path = Path(self._profile_key) / '.conversation_history_rate_limit_until'
        if self.config.debug:
            self._artifact_dir.mkdir(parents=True, exist_ok=True)

    def _is_conversation_history_url(self, url: str) -> bool:
        normalized = (url or '').lower()
        return any(fragment in normalized for fragment in CONVERSATION_HISTORY_RATE_LIMIT_PATH_FRAGMENTS)

    def _read_rate_limit_cooldown_until(self) -> float:
        try:
            raw = self._rate_limit_cooldown_path.read_text(encoding='utf-8').strip()
            return float(raw) if raw else 0.0
        except FileNotFoundError:
            return 0.0
        except Exception as exc:
            self._log('rate-limit', 'failed reading cooldown file', path=str(self._rate_limit_cooldown_path), error=str(exc))
            return 0.0

    def _write_rate_limit_cooldown_until(self, cooldown_until: float) -> None:
        try:
            self._rate_limit_cooldown_path.parent.mkdir(parents=True, exist_ok=True)
            self._rate_limit_cooldown_path.write_text(f'{cooldown_until:.6f}', encoding='utf-8')
        except Exception as exc:
            self._log('rate-limit', 'failed writing cooldown file', path=str(self._rate_limit_cooldown_path), error=str(exc))

    def _note_conversation_history_rate_limit(self, *, trigger: str, url: str, status: int | None = None) -> None:
        cooldown_seconds = max(0.0, float(self.config.conversation_history_rate_limit_cooldown_seconds))
        if cooldown_seconds <= 0:
            return
        cooldown_until = time.time() + cooldown_seconds
        existing = self._read_rate_limit_cooldown_until()
        if existing > cooldown_until:
            cooldown_until = existing
        self._write_rate_limit_cooldown_until(cooldown_until)
        self._log(
            'rate-limit',
            'conversation history rate limit noted',
            trigger=trigger,
            status=status,
            url=url,
            cooldown_seconds=cooldown_seconds,
            cooldown_until=cooldown_until,
        )

    async def _respect_context_spacing(self) -> None:
        spacing = max(0.0, float(self.config.min_context_spacing_seconds))
        if spacing <= 0:
            return
        last_closed_at = _PROFILE_LAST_CONTEXT_CLOSED_AT.get(self._profile_key)
        if last_closed_at is None:
            return
        wait_seconds = (last_closed_at + spacing) - time.monotonic()
        if wait_seconds <= 0:
            return
        self._log('rate-limit', 'waiting before launching next browser context', wait_seconds=round(wait_seconds, 3), profile_dir=self._profile_key)
        await asyncio.sleep(wait_seconds)

    async def _respect_rate_limit_cooldown(self) -> None:
        cooldown_until = self._read_rate_limit_cooldown_until()
        remaining = cooldown_until - time.time()
        if remaining <= 0:
            return
        self._log('rate-limit', 'waiting for persisted conversation history cooldown', wait_seconds=round(remaining, 3), path=str(self._rate_limit_cooldown_path))
        await asyncio.sleep(remaining)

    def _can_wait_for_keep_open(self) -> bool:
        stdin = getattr(sys, "stdin", None)
        if stdin is None:
            return False
        is_tty = getattr(stdin, "isatty", None)
        if not callable(is_tty):
            return False
        try:
            return bool(is_tty())
        except Exception as exc:
            self._log('debug', 'stdin tty check failed during keep-open evaluation', error=repr(exc))
            return False

    async def _pause_for_keep_open(self, prompt: str) -> None:
        if not self._can_wait_for_keep_open():
            self._log('debug', 'skipping keep-open wait because stdin is not interactive', prompt=prompt)
            return
        try:
            await asyncio.to_thread(input, prompt)
        except EOFError:
            self._log('debug', 'skipping keep-open wait after stdin EOF', prompt=prompt)

    def _locator_page(self, locator: Any) -> Any | None:
        page = getattr(locator, 'page', None)
        if page is not None:
            return page
        try:
            impl = getattr(locator, '_impl_obj', None)
            frame = getattr(impl, '_frame', None)
            page = getattr(frame, '_page', None)
            if page is not None:
                return page
        except Exception:
            return None
        return None

    async def _wait_for_rate_limit_modal_to_clear(
        self,
        page: Any,
        *,
        label: str,
        timeout_ms: int | None = None,
    ) -> bool:
        timeout_ms = self.config.rate_limit_modal_wait_timeout_ms if timeout_ms is None else timeout_ms
        poll_interval_ms = self.config.rate_limit_modal_poll_interval_ms
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        saw_modal = False
        while True:
            modal = await self._find_visible_locator(page, RATE_LIMIT_MODAL_SELECTORS, label=f'{label}-rate-limit-modal')
            if modal is None:
                if saw_modal:
                    self._log('rate-limit', 'rate limit modal cleared', label=label)
                    await self._respect_rate_limit_cooldown()
                return saw_modal
            if not saw_modal:
                saw_modal = True
                self._note_conversation_history_rate_limit(
                    trigger='modal',
                    url=await self._safe_page_url(page),
                    status=429,
                )
                self._log('rate-limit', 'rate limit modal detected', label=label, current_url=await self._safe_page_url(page), timeout_ms=timeout_ms)
            ack = await self._find_visible_locator(page, RATE_LIMIT_MODAL_ACK_SELECTORS, label=f'{label}-rate-limit-ack')
            if ack is not None:
                try:
                    await self._click_locator_with_fallback(
                        ack,
                        label=f'{label}-rate-limit-ack',
                        timeout_ms=min(5_000, timeout_ms),
                        handle_rate_limit=False,
                    )
                except Exception as exc:
                    self._log('rate-limit', 'rate limit modal acknowledgement click failed', label=label, error=repr(exc))
            if asyncio.get_running_loop().time() >= deadline:
                raise ResponseTimeoutError('Rate limit modal did not clear before continuing')
            await page.wait_for_timeout(poll_interval_ms)

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
        result = await self.ask_question_result(
            prompt=prompt,
            file_path=file_path,
            expect_json=expect_json,
            keep_open=keep_open,
        )
        return result["answer"]

    async def ask_question_result(
        self,
        prompt: str,
        file_path: Optional[str] = None,
        conversation_url: str | None = None,
        expect_json: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
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
            conversation_url=conversation_url,
            expect_json=expect_json,
            keep_open=keep_open,
        )

    async def list_projects(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        self._log(
            "project-list",
            "starting list_projects",
            project_url=self.config.project_url,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="project_list",
            operation=self._list_projects_operation,
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
        self._log(
            "project-list-debug",
            "starting debug_project_list",
            project_url=self.config.project_url,
            keep_open=keep_open,
            scroll_rounds=scroll_rounds,
            wait_ms=wait_ms,
            manual_pause=manual_pause,
        )
        return await self._run_with_context(
            operation_name="project_list_debug",
            operation=self._debug_project_list_operation,
            scroll_rounds=scroll_rounds,
            wait_ms=wait_ms,
            manual_pause=manual_pause,
            keep_open=keep_open,
        )

    async def list_project_chats(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        self._log(
            "chat-list",
            "starting list_project_chats",
            project_url=self.config.project_url,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="chat_list",
            operation=self._list_project_chats_operation,
            keep_open=keep_open,
        )

    async def get_chat(
        self,
        *,
        conversation_url: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        self._log(
            "chat-show",
            "starting get_chat",
            project_url=self.config.project_url,
            conversation_url=conversation_url,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="chat_show",
            operation=self._get_chat_operation,
            conversation_url=conversation_url,
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

    async def discover_project_source_capabilities(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        self._log(
            "project-source-capabilities",
            "starting discover_project_source_capabilities",
            project_url=self.config.project_url,
            keep_open=keep_open,
        )
        return await self._run_with_context(
            operation_name="project_source_capabilities",
            operation=self._discover_project_source_capabilities_operation,
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

    def _clear_profile_singleton_locks(self) -> list[str]:
        if not self.config.clear_singleton_locks:
            return []

        removed: list[str] = []
        profile_dir = Path(self.config.profile_dir)
        for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            target = profile_dir / name
            try:
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                    removed.append(name)
                elif target.exists() or target.is_symlink():
                    target.unlink()
                    removed.append(name)
            except FileNotFoundError:
                continue
            except Exception as exc:
                self._log(
                    'driver',
                    'failed to clear profile singleton lock artifact',
                    artifact=name,
                    path=str(target),
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        if removed:
            self._log('driver', 'cleared profile singleton lock artifacts', artifacts=removed, profile_dir=self.config.profile_dir)
        return removed

    async def _run_with_context(self, operation_name: str, operation, **kwargs) -> Any:
        Path(self.config.profile_dir).mkdir(parents=True, exist_ok=True)
        self._clear_profile_singleton_locks()
        await self._respect_rate_limit_cooldown()
        await self._respect_context_spacing()
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
                current_url = await self._safe_page_url(page)
                self._log(
                    "error",
                    f"{operation_name} failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                    current_url=current_url,
                )
                await self._dump_failure_artifacts(page, operation_name, exc)
                raise
            finally:
                await self._finalize_context(context, operation_name)
                _PROFILE_LAST_CONTEXT_CLOSED_AT[self._profile_key] = time.monotonic()

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
            await self._pause_for_keep_open("Login check passed. Press Enter to close the browser... ")
        return result

    async def _ask_question_operation(
        self,
        *,
        context: Any,
        page: Any,
        prompt: str,
        file_path: Optional[str],
        conversation_url: str | None = None,
        expect_json: bool,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        target_url = conversation_url or self.config.project_url
        await self._goto(page, target_url, label="chat-home-after-login")
        input_locator = await self._wait_for_chat_input(page)
        await self._wait_for_rate_limit_modal_to_clear(page, label="ask-question-before-composer-click")
        self._log("composer", "chat input resolved; clicking")
        await self._click_locator_with_fallback(input_locator, label="ask-question-composer-input", timeout_ms=5_000)
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
        answer = (
            await self._wait_and_get_json(page, response_context=response_context)
            if expect_json
            else await self._wait_and_get_response(page, response_context=response_context)
        )
        current_url = await self._safe_page_url(page)
        conversation_url = current_url if self._is_conversation_url(current_url) else None
        self._log(
            "ask",
            "ask_question completed",
            current_url=current_url,
            conversation_url=conversation_url,
            expect_json=expect_json,
        )
        if keep_open and self.config.is_headed:
            await self._pause_for_keep_open("Question completed. Press Enter to close the browser... ")
        return {
            "answer": answer,
            "conversation_url": conversation_url,
        }

    async def _list_projects_operation(
        self,
        *,
        context: Any,
        page: Any,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        home_url = self._chatgpt_home_url()
        await self._goto(page, home_url, label="project-list-home")
        await self._ensure_sidebar_open(page)

        current_project_url = self._project_home_url_from_url(self.config.project_url)
        collected: list[dict[str, str]] = []
        try:
            collected = await self._collect_all_projects_via_snorlax_sidebar(page, label='project-list')
        except Exception as exc:
            self._log('project-list', 'snorlax sidebar enumeration failed; falling back to DOM enumeration', error=str(exc))
            collected = []

        for attempt in range(3):
            if collected:
                break
            prep = await self._prepare_project_discovery(page, label='project-list', attempt=attempt)

            discovered = await self._collect_all_sidebar_projects(page, label="project-list")
            collected = self._dedupe_projects([*collected, *discovered])
            self._log(
                "project-list",
                "project enumeration attempt completed",
                attempt=attempt + 1,
                discovered_count=len(discovered),
                total_count=len(collected),
                discovery_mode=prep.get('mode'),
                opened_more=prep.get('opened_more'),
            )
            if collected:
                break
            await page.wait_for_timeout(350)

        normalized_projects: list[dict[str, Any]] = []
        for project in collected:
            project_url = project.get("url") or ""
            normalized_projects.append({
                "name": project.get("name") or "",
                "url": project_url,
                "project_id": self._extract_project_id_from_url(project_url),
                "project_slug": self._project_slug_from_url(project_url),
                "is_current": bool(project_url and current_project_url and self._project_urls_refer_to_same_project(project_url, current_project_url)),
            })

        result = {
            "ok": True,
            "action": "list_projects",
            "count": len(normalized_projects),
            "current_project_url": current_project_url,
            "projects": normalized_projects,
            "current_url": await self._safe_page_url(page),
        }
        self._log("project-list", "project enumeration completed", **result)
        if keep_open and self.config.is_headed:
            await self._pause_for_keep_open("Project list completed. Press Enter to close the browser... ")
        return result

    async def _debug_project_list_operation(
        self,
        *,
        context: Any,
        page: Any,
        scroll_rounds: int = 12,
        wait_ms: int = 350,
        manual_pause: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        home_url = self._chatgpt_home_url()
        await self._goto(page, home_url, label="project-list-debug-home")
        await self._ensure_sidebar_open(page)

        artifact_dir = self._artifact_dir / f"project_list_debug_{self._timestamp_for_filename()}"
        await self._ensure_dir(artifact_dir)

        snorlax_sidebar_requests: list[dict[str, Any]] = []
        snorlax_sidebar_responses: list[dict[str, Any]] = []
        response_tasks: list[asyncio.Task[Any]] = []
        loop = asyncio.get_running_loop()

        def observe_request(req: Any) -> None:
            try:
                url = getattr(req, 'url', '') or ''
                if not self._is_snorlax_sidebar_url(url):
                    return
                snorlax_sidebar_requests.append({
                    'method': getattr(req, 'method', None),
                    'url': url,
                    'resource_type': getattr(req, 'resource_type', None),
                })
                self._log('project-list-debug', 'observed snorlax sidebar request', method=getattr(req, 'method', None), url=url)
            except Exception as exc:
                self._log('project-list-debug', 'failed to inspect snorlax sidebar request', error=str(exc))

        async def capture_snorlax_response(resp: Any) -> None:
            url = getattr(resp, 'url', '') or ''
            if not self._is_snorlax_sidebar_url(url):
                return
            try:
                headers = await resp.all_headers()
            except Exception:
                headers = {}
            try:
                body_text = await resp.text()
            except Exception as exc:
                body_text = f'<failed to read body: {exc}>'
            body_preview = body_text[:4000]
            json_keys = None
            try:
                parsed = json.loads(body_text)
                if isinstance(parsed, dict):
                    json_keys = sorted(str(key) for key in parsed.keys())[:40]
            except Exception:
                pass
            payload = {
                'status': getattr(resp, 'status', None),
                'url': url,
                'content_type': headers.get('content-type') if isinstance(headers, dict) else None,
                'body_preview': body_preview,
                'json_keys': json_keys,
            }
            snorlax_sidebar_responses.append(payload)
            self._log('project-list-debug', 'observed snorlax sidebar response', status=payload['status'], url=url, content_type=payload['content_type'], json_keys=json_keys)

        def observe_response(resp: Any) -> None:
            try:
                url = getattr(resp, 'url', '') or ''
                if not self._is_snorlax_sidebar_url(url):
                    return
                response_tasks.append(loop.create_task(capture_snorlax_response(resp)))
            except Exception as exc:
                self._log('project-list-debug', 'failed to schedule snorlax sidebar response capture', error=str(exc))

        if hasattr(context, 'on'):
            context.on('request', observe_request)
            context.on('response', observe_response)

        async def capture(label: str) -> dict[str, Any]:
            safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", label).strip("-")[:80] or "item"
            screenshot_path = artifact_dir / f"{safe}.png"
            html_path = artifact_dir / f"{safe}.html"
            json_path = artifact_dir / f"{safe}.json"
            await self._ensure_parent_dir(screenshot_path)
            await self._ensure_parent_dir(html_path)
            await self._ensure_parent_dir(json_path)
            await page.screenshot(path=str(screenshot_path), full_page=True)
            await self._write_text(html_path, await page.content())
            payload = {
                "label": label,
                "url": await self._safe_page_url(page),
                "title": await page.title(),
                "project_links": await self._project_link_debug_snapshot(page),
                "dialog_like_nodes": await self._dialog_like_debug_snapshot(page),
                "candidate_scrollables": await self._scrollable_debug_snapshot(page),
                "more_candidates": await self._more_candidate_debug_snapshot(page),
            }
            await self._write_json(json_path, payload)
            return payload

        if manual_pause and self.config.is_headed:
            await self._pause_for_keep_open("Inspect state before project discovery. Press Enter to continue...")
        before_expand = await capture("01-before-discovery")

        discovery_mode = await self._determine_project_discovery_mode(page)
        opened_more = False
        if discovery_mode == 'more-first':
            opened_more = await self._open_more_projects_menu(page)
            await page.wait_for_timeout(wait_ms)
            after_more = await capture("02-after-open-more")
            await self._expand_projects_section(page)
            await page.wait_for_timeout(wait_ms)
            after_expand = await capture("03-after-expand")
        else:
            await self._expand_projects_section(page)
            await page.wait_for_timeout(wait_ms)
            after_expand = await capture("02-after-expand")
            if manual_pause and self.config.is_headed:
                await self._pause_for_keep_open("Inspect state after expanding Projects. Press Enter to continue...")
            opened_more = await self._open_more_projects_menu(page)
            await page.wait_for_timeout(wait_ms)
            after_more = await capture("03-after-open-more")
        if manual_pause and self.config.is_headed:
            await self._pause_for_keep_open("Inspect state after opening More. Press Enter to continue...")

        manual_collected: list[dict[str, str]] = []
        rounds: list[dict[str, Any]] = []
        for round_index in range(max(1, scroll_rounds)):
            visible = await self._collect_sidebar_projects(page)
            manual_collected = self._dedupe_projects([*manual_collected, *visible])
            dom_state = await capture(f"round-{round_index + 1:02d}")
            moved = await self._scroll_project_sidebar_step(page)
            rounds.append({
                "round": round_index + 1,
                "visible_count": len(visible),
                "manual_collected_count": len(manual_collected),
                "moved": bool(moved),
                "visible_projects": visible,
                "dom_project_count": len(dom_state["project_links"]),
            })
            if not moved:
                break
            await page.wait_for_timeout(wait_ms)

        try:
            helper_projects = await self._collect_all_projects_via_snorlax_sidebar(page, label="project-list-debug")
        except Exception as exc:
            self._log('project-list-debug', 'snorlax sidebar enumeration failed during debug; falling back to DOM enumeration', error=str(exc))
            helper_projects = await self._collect_all_sidebar_projects(page, label="project-list-debug")
        final_state = await capture("99-final")
        current_project_url = self._project_home_url_from_url(self.config.project_url)
        normalized_helper: list[dict[str, Any]] = []
        for project in helper_projects:
            project_url = project.get("url") or ""
            normalized_helper.append({
                "name": project.get("name") or "",
                "url": project_url,
                "project_id": self._extract_project_id_from_url(project_url),
                "project_slug": self._project_slug_from_url(project_url),
                "is_current": bool(project_url and current_project_url and self._project_urls_refer_to_same_project(project_url, current_project_url)),
            })

        if response_tasks:
            await asyncio.gather(*response_tasks, return_exceptions=True)

        summary = {
            "ok": True,
            "action": "project_list_debug",
            "artifact_dir": str(artifact_dir),
            "opened_more": bool(opened_more),
            "scroll_rounds_requested": scroll_rounds,
            "wait_ms": wait_ms,
            "discovery_mode": discovery_mode,
            "snorlax_sidebar_requests": snorlax_sidebar_requests,
            "snorlax_sidebar_responses": snorlax_sidebar_responses,
            "before_expand_count": len(before_expand["project_links"]),
            "after_expand_count": len(after_expand["project_links"]),
            "after_more_count": len(after_more["project_links"]),
            "manual_scroll_rounds": rounds,
            "manual_collected_projects": manual_collected,
            "manual_collected_count": len(manual_collected),
            "helper_collected_projects": normalized_helper,
            "helper_collected_count": len(normalized_helper),
            "final_dom_project_count": len(final_state["project_links"]),
            "final_dom_projects": final_state["project_links"],
            "dialog_like_nodes_after_more": after_more["dialog_like_nodes"],
            "candidate_scrollables_after_more": after_more["candidate_scrollables"][:10],
            "more_candidates_after_more": after_more["more_candidates"],
            "current_url": await self._safe_page_url(page),
            "current_project_url": current_project_url,
        }
        await self._write_json(artifact_dir / "snorlax-sidebar-network.json", {"requests": snorlax_sidebar_requests, "responses": snorlax_sidebar_responses})
        await self._write_json(artifact_dir / "summary.json", summary)
        self._log(
            "project-list-debug",
            "debug_project_list completed",
            artifact_dir=str(artifact_dir),
            helper_collected_count=len(normalized_helper),
            final_dom_project_count=len(final_state["project_links"]),
            opened_more=bool(opened_more),
        )
        if keep_open and self.config.is_headed:
            await self._pause_for_keep_open("Project-list debug completed. Press Enter to close the browser...")
        return summary

    async def _list_project_chats_operation(
        self,
        *,
        context: Any,
        page: Any,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        project_url = self._project_home_url_from_url(self.config.project_url)
        project_id = self._extract_project_id_from_url(project_url)
        project_slug = self._project_slug_from_url(project_url)
        if not project_id or not project_slug:
            raise RuntimeError('A project must be selected before listing chats')
        await self._goto(page, project_url, label='chat-list-home')
        await self._open_project_chats_tab(page)
        dom_chats = await self._collect_project_chats_from_home_dom(page, project_url=project_url, label='chat-list-dom')
        history_chats = await self._collect_all_project_chats(page, project_url=project_url, label='chat-list')
        chats = self._merge_project_chat_lists(history_chats, dom_chats)
        result = {
            'ok': True,
            'action': 'list_chats',
            'project_url': project_url,
            'project_id': project_id,
            'project_slug': project_slug,
            'count': len(chats),
            'chats': chats,
            'current_url': await self._safe_page_url(page),
        }
        self._log('chat-list', 'chat enumeration completed', count=len(chats), project_id=project_id, history_count=len(history_chats), dom_count=len(dom_chats))
        if keep_open and self.config.is_headed:
            await self._pause_for_keep_open('Chat list completed. Press Enter to close the browser...')
        return result

    async def _get_chat_operation(
        self,
        *,
        context: Any,
        page: Any,
        conversation_url: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        conversation_id = self._conversation_id_from_url(conversation_url)
        if not conversation_id:
            raise RuntimeError('conversation_url must point to a project conversation')
        await self._goto(page, conversation_url, label='chat-show-home')
        detail = await self._fetch_conversation_detail(page, conversation_id=conversation_id)
        status = detail.get('status')
        if status != 200:
            raise RuntimeError(f'conversation detail returned unexpected status {status}')
        payload = detail.get('payload')
        turns = self._extract_chat_turns_from_conversation_payload(payload)
        project_url = self._project_home_url_from_url(conversation_url)
        result = {
            'ok': True,
            'action': 'get_chat',
            'project_url': project_url,
            'conversation_url': self._project_conversation_url_from_id(conversation_id, project_url=project_url) or conversation_url,
            'conversation_id': conversation_id,
            'title': (payload.get('title') if isinstance(payload, dict) else None) or '(untitled)',
            'create_time': payload.get('create_time') if isinstance(payload, dict) else None,
            'update_time': payload.get('update_time') if isinstance(payload, dict) else None,
            'turn_count': len(turns),
            'turns': turns,
            'current_url': await self._safe_page_url(page),
        }
        self._log('chat-show', 'chat detail fetched', conversation_id=conversation_id, turn_count=len(turns))
        if keep_open and self.config.is_headed:
            await self._pause_for_keep_open('Chat show completed. Press Enter to close the browser...')
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
            await self._pause_for_keep_open("Project created. Press Enter to close the browser... ")
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
            await self._pause_for_keep_open("Project resolution finished. Press Enter to close the browser... ")
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
                await self._pause_for_keep_open("Project already exists. Press Enter to close the browser... ")
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
                await self._pause_for_keep_open("Project ensure failed. Press Enter to close the browser... ")
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
            await self._pause_for_keep_open("Project ensured. Press Enter to close the browser... ")
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
        project_id = self._extract_project_id_from_url(project_home_url)
        await self._goto(page, project_home_url, label="project-remove-home")
        await self._ensure_sidebar_open(page)

        current_url = await self._safe_page_url(page)
        delete_action = None

        if self._project_urls_refer_to_same_project(current_url, project_home_url) and self._is_project_home_url(current_url):
            page_details_button = await self._find_visible_locator(
                page,
                PROJECT_PAGE_DETAILS_MENU_SELECTORS,
                label="project-page-details-menu",
                timeout_ms=1_500,
            )
            if page_details_button is not None:
                try:
                    await page_details_button.scroll_into_view_if_needed(timeout=2_000)
                except Exception:
                    pass
                try:
                    await page_details_button.click(timeout=5_000)
                except Exception:
                    await page_details_button.click(timeout=5_000, force=True)
                delete_action = await self._wait_for_visible_locator(
                    page,
                    PROJECT_REMOVE_ACTION_SELECTORS,
                    label="project-remove-action",
                    total_timeout_ms=3_000,
                    poll_interval_ms=250,
                )

        if delete_action is None:
            container = None
            for attempt in range(3):
                if attempt == 1:
                    await self._expand_projects_section(page)
                elif attempt == 2:
                    await self._prime_project_sidebar(page)
                    await self._expand_projects_section(page)

                container = await self._find_project_sidebar_container(page, project_url=project_home_url)
                if container is not None:
                    break
                await page.wait_for_timeout(350)

            if container is None:
                raise ResponseTimeoutError("Could not find the configured project in the sidebar")

            try:
                await container.hover(timeout=2_000)
            except Exception:
                pass

            options_button = await self._find_project_options_button(container)
            if options_button is None:
                raise ResponseTimeoutError("Could not find the options button for the configured project")
            try:
                await options_button.scroll_into_view_if_needed(timeout=2_000)
            except Exception:
                pass
            try:
                await self._click_locator_with_fallback(
            options_button,
            label="project-source-remove-options",
            timeout_ms=5_000,
        )
            except Exception:
                await options_button.click(timeout=5_000, force=True)

            delete_action = await self._wait_for_visible_locator(
                page,
                PROJECT_REMOVE_ACTION_SELECTORS,
                label="project-remove-action",
                total_timeout_ms=3_000,
                poll_interval_ms=250,
            )
            if delete_action is None:
                settings_action = await self._wait_for_visible_locator(
                    page,
                    PROJECT_REMOVE_SETTINGS_SELECTORS,
                    label="project-remove-settings-action",
                    total_timeout_ms=3_000,
                    poll_interval_ms=250,
                )
                if settings_action is not None:
                    await settings_action.click(timeout=5_000)
                    delete_action = await self._wait_for_visible_locator(
                        page,
                        PROJECT_REMOVE_ACTION_SELECTORS,
                        label="project-remove-action-after-settings",
                        total_timeout_ms=8_000,
                        poll_interval_ms=250,
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
            "deleted_project_id": project_id,
            "current_url": await self._safe_page_url(page),
        }
        self._log("project-remove", "project removed", **result)
        if keep_open and self.config.is_headed:
            await self._pause_for_keep_open("Project removed. Press Enter to close the browser... ")
        return result

    async def _discover_project_source_capabilities_operation(
        self,
        *,
        context: Any,
        page: Any,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        await self.ensure_logged_in(page, context)
        project_home_url = self._project_home_url()
        await self._goto(page, project_home_url, label="project-source-capabilities-home")
        await self._open_project_sources_tab(page)
        await self._click_add_source_button(page)
        capabilities = await self._discover_project_source_capabilities(page)
        result = {
            "ok": True,
            "action": "discover_project_source_capabilities",
            "project_url": project_home_url,
            "available_source_kinds": [item.get("kind") for item in capabilities],
            "available_source_labels": [item.get("label") for item in capabilities],
            "capabilities": capabilities,
            "current_url": await self._safe_page_url(page),
        }
        self._log("project-source-capabilities", "discovered project source capabilities", **result)
        if keep_open and self.config.is_headed:
            await self._pause_for_keep_open("Project source capabilities discovered. Press Enter to close the browser... ")
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

        before_sources = await self._snapshot_project_source_cards(page)
        save_request_watch = None
        if normalized_kind in {"text", "file"}:
            save_request_watch = self._install_project_source_save_request_watch(
                context,
                source_kind=normalized_kind,
            )

        try:
            source_match_candidates: list[str]
            if normalized_kind == "file":
                if not file_path:
                    raise ValueError("file_path is required when source_kind='file'")
                if not os.path.exists(file_path):
                    raise FileNotFoundError(file_path)
                await self._add_project_file_source(page, file_path=file_path)
                source_match_candidates = self._build_source_match_candidates(
                    normalized_kind,
                    value=None,
                    display_name=display_name,
                    file_path=file_path,
                )
            else:
                if not value:
                    raise ValueError(f"value is required when source_kind={normalized_kind!r}")
                await self._add_project_textual_source(
                    page,
                    source_kind=normalized_kind,
                    value=value,
                    display_name=display_name,
                )
                source_match_candidates = self._build_source_match_candidates(
                    normalized_kind,
                    value=value,
                    display_name=display_name,
                    file_path=None,
                )

            matched_source = await self._wait_for_source_presence(
                page,
                source_match_candidates=source_match_candidates,
                before_sources=before_sources,
                accept_single_new_card=normalized_kind == "text",
            )
            if normalized_kind in {"text", "file"}:
                await self._wait_for_project_source_post_save_settle(
                    page,
                    source_kind=normalized_kind,
                )
                await self._wait_for_project_source_save_request_quiet(
                    page,
                    save_request_watch,
                    source_kind=normalized_kind,
                )
        finally:
            if save_request_watch is not None:
                self._dispose_project_source_save_request_watch(context, save_request_watch)
        requested_match = source_match_candidates[0] if source_match_candidates else None
        actual_match = self._preferred_source_card_identity(matched_source) or (matched_source or {}).get("text") or requested_match
        persistence_candidates = self._build_persistence_source_candidates(
            requested_match=requested_match,
            source_match_candidates=source_match_candidates,
            matched_card=matched_source,
        )
        persisted_source = await self._verify_project_source_persistence(
            page,
            project_url=project_home_url,
            source_match_candidates=persistence_candidates,
        )
        persisted_match = self._preferred_source_card_identity(persisted_source) or (persisted_source or {}).get("text") or actual_match
        result = {
            "ok": True,
            "action": "add",
            "project_url": project_home_url,
            "source_kind": normalized_kind,
            "source_match": persisted_match,
            "source_match_requested": requested_match,
            "source_match_candidates": persistence_candidates,
            "persistence_verified": True,
            "current_url": await self._safe_page_url(page),
        }
        self._log("project-source-add", "project source added", **result)
        if keep_open and self.config.is_headed:
            await self._pause_for_keep_open("Source added. Press Enter to close the browser... ")
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

        source_cards = await self._snapshot_project_source_cards(page)
        matched_card = self._match_source_card(source_cards, [source_name])
        match_candidates = self._source_lookup_candidates(source_name, matched_card)

        options_button, matched_card, match_candidates = await self._wait_for_project_source_action_button(
            page,
            match_candidates,
            exact=exact,
            timeout_ms=18_000,
        )
        if options_button is None:
            if await self._project_source_is_stably_absent(page, match_candidates, exact=exact):
                source_identity_used = match_candidates[0] if match_candidates else source_name
                result = {
                    "ok": True,
                    "action": "remove",
                    "project_url": project_home_url,
                    "source_name": source_name,
                    "source_match": source_identity_used,
                    "source_identity_used": source_identity_used,
                    "source_match_candidates": match_candidates,
                    "exact": exact,
                    "already_absent": True,
                    "removed_via_ui": False,
                    "current_url": await self._safe_page_url(page),
                }
                self._log(
                    "project-source-remove",
                    "project source already absent; treating remove as idempotent success",
                    **result,
                )
                if keep_open and self.config.is_headed:
                    await self._pause_for_keep_open("Source already absent. Press Enter to close the browser... ")
                return result
            raise ResponseTimeoutError(f"Project source was not found: {source_name}")
        source_removed = False
        removal_triggered = False
        max_remove_attempts = 3

        for remove_attempt in range(1, max_remove_attempts + 1):
            await self._click_locator_with_fallback(
                options_button,
                label="project-source-remove-options",
                timeout_ms=5_000,
            )
            remove_button = await self._wait_for_visible_locator(
                page,
                PROJECT_SOURCE_REMOVE_ACTION_SELECTORS,
                label="project-source-remove-action",
                total_timeout_ms=8_000,
            )
            if remove_button is None:
                raise ResponseTimeoutError("Could not find the remove/delete action for the selected project source")
            await self._click_locator_with_fallback(
                remove_button,
                label="project-source-remove-action",
                timeout_ms=5_000,
            )

            confirm_button = await self._wait_for_visible_locator(
                page,
                PROJECT_SOURCE_CONFIRM_REMOVE_SELECTORS,
                label="project-source-remove-confirm",
                total_timeout_ms=4_000,
            )
            if confirm_button is not None:
                await self._click_locator_with_fallback(
                    confirm_button,
                    label="project-source-remove-confirm",
                    timeout_ms=5_000,
                )
                removal_triggered = True
                break

            try:
                await self._wait_for_source_absence(page, match_candidates, exact=exact, timeout_ms=4_000)
                source_removed = True
                removal_triggered = True
                break
            except ResponseTimeoutError as exc:
                self._log(
                    "project-source-remove",
                    "remove action did not trigger confirmation or disappearance yet",
                    attempt=remove_attempt,
                    max_attempts=max_remove_attempts,
                    source_candidates=match_candidates,
                    error=str(exc),
                    current_url=await self._safe_page_url(page),
                )
                if remove_attempt >= max_remove_attempts:
                    raise ResponseTimeoutError(
                        f"Project source remove action did not trigger confirmation or disappearance: {source_name}"
                    ) from exc
                try:
                    keyboard = getattr(page, "keyboard", None)
                    if keyboard is not None:
                        await keyboard.press("Escape")
                except Exception:
                    pass
                await page.wait_for_timeout(400)
                options_button, matched_card, match_candidates = await self._wait_for_project_source_action_button(
                    page,
                    match_candidates,
                    exact=exact,
                    timeout_ms=8_000,
                )
                if options_button is None:
                    if await self._project_source_is_stably_absent(page, match_candidates, exact=exact):
                        source_removed = True
                        removal_triggered = True
                        break
                    raise ResponseTimeoutError(f"Project source was not found during remove retry: {source_name}")

        if removal_triggered and not source_removed:
            await self._wait_for_source_absence(page, match_candidates, exact=exact)
        source_identity_used = self._preferred_source_card_identity(matched_card) or source_name
        result = {
            "ok": True,
            "action": "remove",
            "project_url": project_home_url,
            "source_name": source_name,
            "source_match": source_identity_used,
            "source_identity_used": source_identity_used,
            "source_match_candidates": match_candidates,
            "exact": exact,
            "already_absent": False,
            "removed_via_ui": True,
            "current_url": await self._safe_page_url(page),
        }
        self._log("project-source-remove", "project source removed", **result)
        if keep_open and self.config.is_headed:
            await self._pause_for_keep_open("Source removed. Press Enter to close the browser... ")
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

        current_url = await self._safe_page_url(page)

        auth_selector = await self._find_visible_locator(page, AUTHENTICATED_INDICATORS, label="authenticated-indicator")
        auth_visible = auth_selector is not None

        login_button = await self._find_visible_locator(page, LOGIN_BUTTON_SELECTORS, label="login-indicator")
        login_visible = login_button is not None

        signup_button = await self._find_visible_locator(page, SIGNUP_BUTTON_SELECTORS, label="signup-indicator")
        signup_visible = signup_button is not None

        anonymous_marker = await self._find_visible_locator(page, ANONYMOUS_STATE_SELECTORS, label="anonymous-indicator")
        anonymous_visible = anonymous_marker is not None

        composer_visible = await self._has_chat_input(page)
        project_page_visible = self._is_project_home_url(current_url)

        self._log(
            "auth-check",
            "auth state summary",
            auth_visible=auth_visible,
            login_visible=login_visible,
            signup_visible=signup_visible,
            anonymous_visible=anonymous_visible,
            composer_visible=composer_visible,
            project_page_visible=project_page_visible,
            current_url=current_url,
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

        if project_page_visible:
            self._log("auth-check", "valid project page without anonymous markers; treating session as active")
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
        handle_rate_limit: bool = True,
    ) -> Optional[Any]:
        deadline = asyncio.get_running_loop().time() + (total_timeout_ms / 1000)
        attempt = 0
        while asyncio.get_running_loop().time() < deadline:
            attempt += 1
            if handle_rate_limit:
                await self._wait_for_rate_limit_modal_to_clear(page, label=f'{label}-wait')
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

    def _project_slug_from_url(self, url: str) -> Optional[str]:
        path = urlparse(url).path or ''
        match = re.search(r'/g/([^/]+)/', path, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_project_id_from_url(self, url: str) -> Optional[str]:
        path = urlparse(url).path or ''
        match = re.search(r'/g/(g-p-[a-z0-9]+)', path, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return None

    def _conversation_id_from_url(self, url: str) -> Optional[str]:
        path = urlparse(url).path or ''
        parts = [part for part in path.split('/') if part]
        if len(parts) >= 4 and parts[0] == 'g' and parts[2] == 'c':
            return parts[3]
        return None

    def _project_conversation_url_from_id(self, conversation_id: str, *, project_url: Optional[str] = None) -> Optional[str]:
        project_slug = self._project_slug_from_url(project_url or self.config.project_url)
        if not project_slug or not conversation_id:
            return None
        return urljoin(self._chatgpt_home_url(), f'g/{project_slug}/c/{conversation_id}')

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

    def _is_snorlax_sidebar_url(self, url: str) -> bool:
        return '/backend-api/gizmos/snorlax/sidebar' in (url or '').lower()

    def _project_url_from_short_url(self, short_url: str) -> Optional[str]:
        slug = re.sub(r'^/+', '', str(short_url or '').strip())
        if not slug:
            return None
        if slug.startswith('g/'):
            slug = slug[2:]
        if slug.startswith('g-p-'):
            return urljoin(self._chatgpt_home_url(), f'g/{slug}/project')
        return None

    def _extract_projects_from_snorlax_sidebar_payload(self, payload: Any) -> tuple[list[dict[str, str]], Optional[str]]:
        if not isinstance(payload, dict):
            return [], None

        items = payload.get('items')
        if not isinstance(items, list):
            return [], None

        extracted: list[dict[str, str]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            gizmo = item.get('gizmo')
            if isinstance(gizmo, dict):
                gizmo = gizmo.get('gizmo', gizmo)
            if not isinstance(gizmo, dict):
                continue

            short_url = gizmo.get('short_url') or gizmo.get('shortUrl') or gizmo.get('slug') or gizmo.get('id')
            project_url = self._project_url_from_short_url(str(short_url or ''))
            if not project_url:
                continue

            display = gizmo.get('display') if isinstance(gizmo.get('display'), dict) else {}
            name = (display.get('name') or gizmo.get('display_name') or gizmo.get('name') or '').strip()
            if not name:
                continue

            extracted.append({'name': name, 'url': project_url})

        cursor = payload.get('cursor')
        if cursor is not None:
            cursor = str(cursor).strip() or None
        return self._dedupe_projects(extracted), cursor

    async def _fetch_snorlax_sidebar_page(
        self,
        page: Any,
        *,
        cursor: Optional[str] = None,
        limit: int = 20,
        conversations_per_gizmo: int = 5,
    ) -> dict[str, Any]:
        result = await page.evaluate(
            r'''
            async ({ cursor, limit, conversationsPerGizmo }) => {
                const base = new URL('/backend-api/gizmos/snorlax/sidebar', window.location.origin);
                base.searchParams.set('owned_only', 'true');
                base.searchParams.set('conversations_per_gizmo', String(conversationsPerGizmo));
                base.searchParams.set('limit', String(limit));
                if (cursor) {
                    base.searchParams.set('cursor', cursor);
                }

                let accessToken = null;
                try {
                    const bootstrap = document.getElementById('client-bootstrap');
                    if (bootstrap && bootstrap.textContent) {
                        const payload = JSON.parse(bootstrap.textContent);
                        accessToken = payload?.session?.accessToken || payload?.accessToken || null;
                    }
                } catch (_err) {
                    accessToken = null;
                }

                const headers = { accept: 'application/json' };
                if (accessToken) {
                    headers.authorization = `Bearer ${accessToken}`;
                }

                const response = await fetch(base.toString(), {
                    credentials: 'include',
                    headers,
                });
                const text = await response.text();
                const responseHeaders = {};
                for (const [key, value] of response.headers.entries()) {
                    responseHeaders[key] = value;
                }
                return {
                    ok: response.ok,
                    status: response.status,
                    url: response.url || base.toString(),
                    text,
                    headers: responseHeaders,
                    usedAuthorization: Boolean(accessToken),
                };
            }
            ''',
            {
                'cursor': cursor,
                'limit': limit,
                'conversationsPerGizmo': conversations_per_gizmo,
            },
        )
        if not isinstance(result, dict):
            raise RuntimeError('Unexpected snorlax sidebar response shape')
        text_body = str(result.get('text') or '')
        parsed_payload: Any = None
        if text_body:
            try:
                parsed_payload = json.loads(text_body)
            except json.JSONDecodeError:
                parsed_payload = None
        return {
            'ok': bool(result.get('ok')),
            'status': result.get('status'),
            'url': result.get('url'),
            'headers': result.get('headers') if isinstance(result.get('headers'), dict) else {},
            'payload': parsed_payload,
            'text': text_body,
            'used_authorization': bool(result.get('usedAuthorization')),
        }

    async def _collect_all_projects_via_snorlax_sidebar(
        self,
        page: Any,
        *,
        label: str,
        max_pages: int = 25,
    ) -> list[dict[str, str]]:
        collected: list[dict[str, str]] = []
        cursor: Optional[str] = None
        seen_cursors: set[str] = set()

        for page_index in range(max_pages):
            response = await self._fetch_snorlax_sidebar_page(page, cursor=cursor)
            status = response.get('status')
            payload = response.get('payload')
            projects, next_cursor = self._extract_projects_from_snorlax_sidebar_payload(payload)
            collected = self._dedupe_projects([*collected, *projects])
            self._log(
                label,
                'collected projects via snorlax sidebar',
                page=page_index + 1,
                status=status,
                discovered_count=len(projects),
                total_count=len(collected),
                cursor=cursor,
                next_cursor=next_cursor,
                used_authorization=response.get('used_authorization'),
            )
            if status != 200:
                if collected:
                    self._log(
                        label,
                        'stopping snorlax pagination after non-200 response and keeping collected projects',
                        page=page_index + 1,
                        status=status,
                        retained_count=len(collected),
                    )
                    break
                raise RuntimeError(f'snorlax sidebar returned unexpected status {status}')
            if not projects and collected:
                self._log(
                    label,
                    'stopping snorlax pagination after empty project page and keeping collected projects',
                    page=page_index + 1,
                    status=status,
                    retained_count=len(collected),
                )
                break
            if not next_cursor:
                break
            if next_cursor in seen_cursors:
                self._log(label, 'stopping snorlax pagination because cursor repeated', repeated_cursor=next_cursor)
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor

        return collected

    def _extract_project_chats_from_conversations_payload(
        self,
        payload: Any,
        *,
        project_id: str,
        project_url: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        items: list[Any]
        if isinstance(payload, dict):
            raw_items = payload.get('items')
            items = raw_items if isinstance(raw_items, list) else []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        project_slug = self._project_slug_from_url(project_url or self.config.project_url)
        if not project_slug:
            return []

        chats: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        normalized_project_id = (project_id or '').strip().lower()
        for item in items:
            if not isinstance(item, dict):
                continue
            candidate_project_id = str(
                item.get('conversation_template_id')
                or item.get('conversationTemplateId')
                or item.get('gizmo_id')
                or item.get('gizmoId')
                or item.get('project_id')
                or item.get('projectId')
                or ''
            ).strip().lower()
            if normalized_project_id:
                if not candidate_project_id:
                    continue
                if candidate_project_id != normalized_project_id:
                    continue
            conversation_id = str(item.get('id') or '').strip()
            if not conversation_id or conversation_id in seen_ids:
                continue
            seen_ids.add(conversation_id)
            title = re.sub(r'\s+', ' ', str(item.get('title') or '')).strip() or '(untitled)'
            conversation_url = self._project_conversation_url_from_id(conversation_id, project_url=project_url)
            if not conversation_url:
                continue
            chats.append({
                'id': conversation_id,
                'title': title,
                'conversation_url': conversation_url,
                'create_time': item.get('create_time') or item.get('createTime'),
                'update_time': item.get('update_time') or item.get('updateTime'),
            })
        return chats

    async def _fetch_conversations_page(
        self,
        page: Any,
        *,
        offset: int = 0,
        limit: int = 100,
        order: str = 'updated',
    ) -> dict[str, Any]:
        result = await page.evaluate(
            r'''
            async ({ offset, limit, order }) => {
                const base = new URL('/backend-api/conversations', window.location.origin);
                base.searchParams.set('offset', String(offset));
                base.searchParams.set('limit', String(limit));
                base.searchParams.set('order', String(order));
                base.searchParams.set('is_archived', 'false');
                base.searchParams.set('is_starred', 'false');

                let accessToken = null;
                try {
                    const bootstrap = document.getElementById('client-bootstrap');
                    if (bootstrap && bootstrap.textContent) {
                        const payload = JSON.parse(bootstrap.textContent);
                        accessToken = payload?.session?.accessToken || payload?.accessToken || null;
                    }
                } catch (_err) {
                    accessToken = null;
                }

                const headers = { accept: 'application/json' };
                if (accessToken) {
                    headers.authorization = `Bearer ${accessToken}`;
                }

                const response = await fetch(base.toString(), {
                    credentials: 'include',
                    headers,
                });
                const text = await response.text();
                return {
                    ok: response.ok,
                    status: response.status,
                    url: response.url || base.toString(),
                    text,
                    usedAuthorization: Boolean(accessToken),
                };
            }
            ''',
            {'offset': offset, 'limit': limit, 'order': order},
        )
        if not isinstance(result, dict):
            raise RuntimeError('Unexpected conversation history response shape')
        text_body = str(result.get('text') or '')
        parsed_payload: Any = None
        if text_body:
            try:
                parsed_payload = json.loads(text_body)
            except json.JSONDecodeError:
                parsed_payload = None
        return {
            'ok': bool(result.get('ok')),
            'status': result.get('status'),
            'url': result.get('url'),
            'payload': parsed_payload,
            'text': text_body,
            'used_authorization': bool(result.get('usedAuthorization')),
        }

    async def _collect_all_project_chats(
        self,
        page: Any,
        *,
        project_url: str,
        label: str,
        limit: int = 100,
        max_pages: int = 25,
    ) -> list[dict[str, Any]]:
        project_id = self._extract_project_id_from_url(project_url)
        if not project_id:
            raise RuntimeError('project id could not be derived from project url')

        collected: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        offset = 0
        for page_index in range(max_pages):
            response = await self._fetch_conversations_page(page, offset=offset, limit=limit)
            status = response.get('status')
            if status == 429:
                self._note_conversation_history_rate_limit(trigger='fetch', url=str(response.get('url') or ''), status=429)
            if status != 200:
                if collected:
                    self._log(label, 'stopping conversation pagination after non-200 response and keeping collected chats', page=page_index + 1, status=status, retained_count=len(collected))
                    break
                raise RuntimeError(f'conversation history returned unexpected status {status}')
            page_chats = self._extract_project_chats_from_conversations_payload(response.get('payload'), project_id=project_id, project_url=project_url)
            new_count = 0
            for chat in page_chats:
                chat_id = str(chat.get('id') or '')
                if not chat_id or chat_id in seen_ids:
                    continue
                seen_ids.add(chat_id)
                collected.append(chat)
                new_count += 1
            self._log(label, 'collected project chats via conversation history', page=page_index + 1, offset=offset, limit=limit, status=status, discovered_count=new_count, total_count=len(collected), used_authorization=response.get('used_authorization'))
            raw_payload = response.get('payload')
            raw_items = raw_payload.get('items') if isinstance(raw_payload, dict) else raw_payload if isinstance(raw_payload, list) else []
            item_count = len(raw_items) if isinstance(raw_items, list) else 0
            if item_count < limit:
                break
            offset += limit
        return collected

    async def _fetch_conversation_detail(self, page: Any, *, conversation_id: str) -> dict[str, Any]:
        result = await page.evaluate(
            r'''
            async ({ conversationId }) => {
                const base = new URL(`/backend-api/conversation/${conversationId}`, window.location.origin);
                let accessToken = null;
                try {
                    const bootstrap = document.getElementById('client-bootstrap');
                    if (bootstrap && bootstrap.textContent) {
                        const payload = JSON.parse(bootstrap.textContent);
                        accessToken = payload?.session?.accessToken || payload?.accessToken || null;
                    }
                } catch (_err) {
                    accessToken = null;
                }
                const headers = { accept: 'application/json' };
                if (accessToken) {
                    headers.authorization = `Bearer ${accessToken}`;
                }
                const response = await fetch(base.toString(), {
                    credentials: 'include',
                    headers,
                });
                const text = await response.text();
                return {
                    ok: response.ok,
                    status: response.status,
                    url: response.url || base.toString(),
                    text,
                    usedAuthorization: Boolean(accessToken),
                };
            }
            ''',
            {'conversationId': conversation_id},
        )
        if not isinstance(result, dict):
            raise RuntimeError('Unexpected conversation detail response shape')
        text_body = str(result.get('text') or '')
        parsed_payload: Any = None
        if text_body:
            try:
                parsed_payload = json.loads(text_body)
            except json.JSONDecodeError:
                parsed_payload = None
        return {
            'ok': bool(result.get('ok')),
            'status': result.get('status'),
            'url': result.get('url'),
            'payload': parsed_payload,
            'text': text_body,
            'used_authorization': bool(result.get('usedAuthorization')),
        }

    def _message_text_from_payload(self, message: Any) -> str:
        if not isinstance(message, dict):
            return ''
        content = message.get('content')
        parts: list[str] = []

        def _append(value: Any) -> None:
            if isinstance(value, str):
                normalized = re.sub(r'\s+', ' ', value).strip()
                if normalized:
                    parts.append(normalized)
            elif isinstance(value, dict):
                for key in ('text', 'result', 'value'):
                    maybe = value.get(key)
                    if isinstance(maybe, str):
                        _append(maybe)
            elif isinstance(value, list):
                for item in value:
                    _append(item)

        if isinstance(content, dict):
            _append(content.get('parts'))
            _append(content.get('text'))
        else:
            _append(content)
        return '\n\n'.join(parts).strip()

    def _extract_chat_turns_from_conversation_payload(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        mapping = payload.get('mapping') if isinstance(payload.get('mapping'), dict) else {}
        current_node = payload.get('current_node') or payload.get('currentNode')
        node_ids: list[str] = []
        seen: set[str] = set()
        cursor = str(current_node) if current_node is not None else ''
        while cursor and cursor not in seen:
            seen.add(cursor)
            node_ids.append(cursor)
            node = mapping.get(cursor) if isinstance(mapping, dict) else None
            if not isinstance(node, dict):
                break
            parent = node.get('parent')
            cursor = str(parent) if parent is not None else ''
        ordered_ids = list(reversed(node_ids))
        turns: list[dict[str, Any]] = []
        turn_index = 0
        for node_id in ordered_ids:
            node = mapping.get(node_id) if isinstance(mapping, dict) else None
            if not isinstance(node, dict):
                continue
            message = node.get('message')
            if not isinstance(message, dict):
                continue
            author = message.get('author') if isinstance(message.get('author'), dict) else {}
            role = str(author.get('role') or message.get('role') or '').strip().lower()
            if role in {'', 'system', 'tool'}:
                continue
            text = self._message_text_from_payload(message)
            if not text:
                continue
            turn_index += 1
            turns.append({
                'index': turn_index,
                'id': node_id,
                'role': role,
                'text': text,
                'create_time': message.get('create_time') or message.get('createTime') or node.get('create_time') or node.get('createTime'),
            })
        return turns

    async def _determine_project_discovery_mode(self, page: Any) -> str:
        has_project_entrypoint = bool(
            await self._find_visible_locator(
                page,
                PROJECT_NEW_BUTTON_SELECTORS + PROJECT_SECTION_TOGGLE_SELECTORS,
                label='project-discovery-entrypoint',
                timeout_ms=500,
            )
        )
        if has_project_entrypoint:
            mode = 'sidebar-first'
        else:
            has_more_entrypoint = bool(
                await self._find_visible_locator(
                    page,
                    PROJECT_MORE_BUTTON_SELECTORS,
                    label='project-more-entrypoint',
                    timeout_ms=500,
                )
            )
            mode = 'more-first' if has_more_entrypoint else 'sidebar-first'
        self._log('project-list', 'selected project discovery mode', mode=mode, has_project_entrypoint=has_project_entrypoint)
        return mode

    async def _prepare_project_discovery(self, page: Any, *, label: str, attempt: int = 0) -> dict[str, Any]:
        mode = await self._determine_project_discovery_mode(page)
        opened_more = False
        if mode == 'more-first':
            opened_more = await self._open_more_projects_menu(page)
            await page.wait_for_timeout(250)
            if attempt > 0:
                await self._prime_project_sidebar(page)
            await self._expand_projects_section(page)
        else:
            if attempt > 0:
                await self._prime_project_sidebar(page)
            await self._expand_projects_section(page)
            opened_more = await self._open_more_projects_menu(page)
        self._log(label, 'prepared project discovery surface', mode=mode, opened_more=opened_more, attempt=attempt + 1)
        return {'mode': mode, 'opened_more': opened_more}

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

    async def _open_more_projects_menu(self, page: Any) -> bool:
        button = await self._find_visible_locator(
            page,
            PROJECT_MORE_BUTTON_SELECTORS,
            label='project-more-button',
            timeout_ms=800,
        )
        if button is not None:
            try:
                await button.click(timeout=2_500)
                self._log('project-list', 'opened More projects menu via locator click')
                await page.wait_for_timeout(350)
                return True
            except Exception as exc:
                self._log('project-list', 'More projects locator click failed; falling back to DOM click', error=str(exc))

        try:
            opened = await page.evaluate(
                r'''
                () => {
                    const normalizeText = value => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
                    const normalizeMore = value => normalizeText(value).replace(/^[^a-z]+/i, '');
                    const roots = Array.from(document.querySelectorAll('aside, nav, [data-testid*="sidebar"], [class*="sidebar"], [class*="Sidebar"]'));
                    const isVisible = element => {
                        if (!(element instanceof HTMLElement)) return false;
                        const style = window.getComputedStyle(element);
                        const rect = element.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                    };
                    for (const root of roots) {
                        for (const control of Array.from(root.querySelectorAll('[data-sidebar-item="true"], button, [role="button"], summary, a, [tabindex]'))) {
                            const text = normalizeMore(control.innerText || control.textContent || control.getAttribute('aria-label') || '');
                            if (text !== 'more') continue;
                            if (!isVisible(control)) continue;
                            control.click();
                            return true;
                        }
                    }
                    return false;
                }
                '''
            )
        except Exception:
            return False
        if opened:
            self._log('project-list', 'opened More projects menu via DOM fallback')
            await page.wait_for_timeout(350)
            return True
        return False

    async def _scroll_project_sidebar_step(self, page: Any) -> bool:
        try:
            moved = await page.evaluate(
                r'''
                () => {
                    const candidates = Array.from(document.querySelectorAll(
                        'aside, nav, [data-testid*="sidebar"], [class*="sidebar"], [class*="Sidebar"], [role="navigation"], [role="tree"], [role="list"], [role="menu"], [role="dialog"], [role="listbox"], [data-radix-popper-content-wrapper], [data-radix-menu-content]'
                    ));
                    const containers = [];
                    const seen = new Set();
                    for (const element of candidates) {
                        if (!(element instanceof HTMLElement)) continue;
                        if (seen.has(element)) continue;
                        seen.add(element);
                        const style = window.getComputedStyle(element);
                        const overflowY = style?.overflowY || '';
                        const text = element.innerText || element.textContent || '';
                        const hasProjects = !!element.querySelector('a[href*="/project"]') || /projects|new project|folder/i.test(text);
                        const canScroll = (element.scrollHeight - element.clientHeight) > 24 || /(auto|scroll)/i.test(overflowY);
                        if (hasProjects && canScroll) containers.push(element);
                    }

                    let moved = false;
                    for (const element of containers) {
                        const maxTop = Math.max(0, element.scrollHeight - element.clientHeight);
                        const step = Math.max(Math.floor(element.clientHeight * 0.85), 280);
                        const nextTop = Math.min(maxTop, element.scrollTop + step);
                        if (nextTop > element.scrollTop + 1) {
                            element.scrollTop = nextTop;
                            element.dispatchEvent(new Event('scroll', { bubbles: true }));
                            moved = true;
                        }
                    }

                    if (!moved) {
                        const doc = document.scrollingElement || document.documentElement || document.body;
                        if (doc instanceof HTMLElement) {
                            const maxTop = Math.max(0, doc.scrollHeight - doc.clientHeight);
                            const step = Math.max(Math.floor(window.innerHeight * 0.85), 400);
                            const nextTop = Math.min(maxTop, doc.scrollTop + step);
                            if (nextTop > doc.scrollTop + 1) {
                                doc.scrollTop = nextTop;
                                window.dispatchEvent(new Event('scroll'));
                                moved = true;
                            }
                        }
                    }
                    return moved;
                }
                '''
            )
        except Exception:
            return False
        return bool(moved)

    async def _collect_all_sidebar_projects(
        self,
        page: Any,
        *,
        label: str,
        max_scroll_rounds: int = 40,
    ) -> list[dict[str, str]]:
        collected: list[dict[str, str]] = []
        more_opened = False
        for round_index in range(max_scroll_rounds):
            projects = await self._collect_sidebar_projects(page)
            collected = self._dedupe_projects([*collected, *projects])

            if not more_opened:
                more_opened = await self._open_more_projects_menu(page)
                if more_opened:
                    more_projects = await self._collect_sidebar_projects(page)
                    collected = self._dedupe_projects([*collected, *more_projects])
                    self._log(
                        label,
                        'opened More projects menu during enumeration',
                        round=round_index + 1,
                        discovered_count=len(more_projects),
                        total_count=len(collected),
                    )

            moved = await self._scroll_project_sidebar_step(page)
            self._log(
                label,
                'sidebar project scroll round completed',
                round=round_index + 1,
                discovered_count=len(projects),
                total_count=len(collected),
                moved=moved,
                more_opened=more_opened,
            )
            if not moved:
                break
            await page.wait_for_timeout(250)

        return collected


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
        try:
            collected = await self._collect_all_projects_via_snorlax_sidebar(page, label='project-resolve')
        except Exception as exc:
            self._log('project-resolve', 'snorlax sidebar enumeration failed; falling back to DOM enumeration', error=str(exc))
            collected = []

        for attempt in range(3):
            matches = [project for project in collected if self._normalize_project_name(project.get('name', '')) == normalized_name]
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

            prep = await self._prepare_project_discovery(page, label='project-resolve', attempt=attempt)

            discovered = await self._collect_all_sidebar_projects(page, label='project-resolve')
            collected = self._dedupe_projects([*collected, *discovered])
            matches = [project for project in collected if self._normalize_project_name(project.get('name', '')) == normalized_name]
            self._log(
                'project-resolve',
                'project enumeration attempt completed',
                attempt=attempt + 1,
                discovered_count=len(discovered),
                total_count=len(collected),
                match_count=len(matches),
                discovery_mode=prep.get('mode'),
                opened_more=prep.get('opened_more'),
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
                        const container = anchor.closest('[data-sidebar-item], li, [role="treeitem"], [role="listitem"], [class*="sidebar"], [role="menu"], [role="dialog"], [role="listbox"], [data-radix-popper-content-wrapper], [data-radix-menu-content], [popover]');
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
                        for (const anchor of Array.from(root.querySelectorAll('a[href*="/project"], [role="menu"] a[href*="/project"], [role="dialog"] a[href*="/project"], [data-radix-popper-content-wrapper] a[href*="/project"]'))) {
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

    def _normalize_source_match_text(self, value: Optional[str]) -> str:
        return re.sub(r"\s+", " ", (value or "").strip())

    def _build_persistence_source_candidates(
        self,
        *,
        requested_match: Optional[str],
        source_match_candidates: Optional[list[str]],
        matched_card: Optional[dict[str, str]],
    ) -> list[str]:
        candidates: list[str] = []

        def add(candidate: Optional[str]) -> None:
            normalized = self._normalize_source_match_text(candidate)
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        add(requested_match)
        for candidate in source_match_candidates or []:
            add(candidate)
        for candidate in self._source_card_identity_candidates(matched_card):
            add(candidate)
        return candidates

    def _build_source_match_candidates(
        self,
        source_kind: str,
        *,
        value: Optional[str],
        display_name: Optional[str],
        file_path: Optional[str],
    ) -> list[str]:
        candidates: list[str] = []

        def add(candidate: Optional[str]) -> None:
            normalized = self._normalize_source_match_text(candidate)
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        if source_kind == "file":
            add(display_name)
            add(Path(file_path).name if file_path else None)
            return candidates

        normalized_value = self._normalize_source_match_text(value)
        preview_value = self._preview_text(normalized_value, 80) if normalized_value else ""
        add(self._infer_source_match_text(source_kind, normalized_value))
        add(preview_value)
        if source_kind == "text":
            add(normalized_value)
            add(display_name)
            return candidates

        parsed = urlparse(normalized_value)
        add(parsed.netloc)
        add(display_name)
        add(normalized_value)
        return candidates

    async def _snapshot_project_source_cards(self, page: Any) -> list[dict[str, str]]:
        try:
            cards = await page.evaluate(
                r"""
                () => {
                    const normalize = value => (value || '').replace(/\s+/g, ' ').trim();
                    const normalizeLower = value => normalize(value).toLowerCase();
                    const isVisible = el => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        if (!style) return false;
                        if (style.display === 'none' || style.visibility === 'hidden') return false;
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    };
                    const isSourceActionButton = button => {
                        if (!button || !isVisible(button)) return false;
                        const aria = normalizeLower(button.getAttribute('aria-label') || '');
                        const testid = normalizeLower(button.getAttribute('data-testid') || '');
                        const hasPopup = normalizeLower(button.getAttribute('aria-haspopup') || '');
                        return aria.includes('source actions') || testid.includes('source') || hasPopup === 'menu';
                    };
                    const rootCandidates = Array.from(
                        document.querySelectorAll(
                            '[data-project-home-sources-surface="true"], section[aria-label="Sources"], [role="tabpanel"][data-state="active"], [role="tabpanel"]'
                        )
                    ).filter(isVisible);
                    const roots = rootCandidates.length
                        ? rootCandidates
                        : Array.from(document.querySelectorAll('main, [role="main"], body')).filter(isVisible);
                    const seen = new Set();
                    const results = [];

                    const isEmptyStateText = text => {
                        const lower = normalizeLower(text);
                        return lower.includes('give chatgpt more context');
                    };

                    const candidateRowsForRoot = root => {
                        const rows = [];
                        const rowSet = new Set();
                        const addRow = row => {
                            if (!row || rowSet.has(row) || !isVisible(row)) return;
                            rowSet.add(row);
                            rows.push(row);
                        };

                        for (const button of Array.from(root.querySelectorAll('button,[role="button"]'))) {
                            if (!isSourceActionButton(button)) continue;
                            let current = button.closest('[data-testid*="source"], [class*="file-row"], [class*="source"], li, article, [role="listitem"], div') || button.parentElement;
                            while (current && current !== root && current !== document.body) {
                                if (!isVisible(current)) {
                                    current = current.parentElement;
                                    continue;
                                }
                                const text = normalize(current.innerText || current.textContent || '');
                                if (!text || text.length > 600 || isEmptyStateText(text) || /^add\s*$/i.test(text) || /^add\s+source$/i.test(text)) {
                                    current = current.parentElement;
                                    continue;
                                }
                                addRow(current);
                                break;
                            }
                        }
                        return rows;
                    };

                    for (const root of roots) {
                        for (const row of candidateRowsForRoot(root)) {
                            const text = normalize(row.innerText || row.textContent || '');
                            if (!text || text.length > 600 || isEmptyStateText(text)) continue;

                            const rawLines = String(row.innerText || row.textContent || '').split('\n');
                            const lines = rawLines.map(value => normalize(value)).filter(Boolean);
                            const titleNode =
                                Array.from(row.querySelectorAll('[title], [aria-label], .truncate, .font-semibold, [class*="font-semibold"]'))
                                    .find(el => {
                                        if (!isVisible(el)) return false;
                                        const aria = normalizeLower(el.getAttribute('aria-label') || '');
                                        return !aria.includes('source actions') && !el.closest('button,[role="button"]');
                                    }) || null;
                            const title = normalize(
                                (titleNode && (titleNode.getAttribute('title') || titleNode.getAttribute('aria-label') || titleNode.innerText || titleNode.textContent)) ||
                                lines[0] ||
                                ''
                            );
                            const subtitle = Array.from(row.querySelectorAll('.text-token-text-secondary, time'))
                                .filter(isVisible)
                                .map(el => normalize(el.innerText || el.textContent || ''))
                                .filter(Boolean)
                                .join(' ') || (lines.length > 1 ? lines[1] : '');
                            const subtitlePrefix = normalize((subtitle.split('·')[0] || '').trim());
                            const identity = normalize([title, subtitlePrefix].filter(Boolean).join(' '));
                            const key = normalize((title || identity || text)).toLowerCase();
                            if (!key || seen.has(key)) continue;
                            seen.add(key);
                            results.push({ text, key, title, subtitle, identity });
                        }
                    }
                    return results;
                }
                """
            )
        except Exception:
            return []
        if not isinstance(cards, list):
            return []
        normalized_cards: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in cards:
            if not isinstance(item, dict):
                continue
            text_value = self._normalize_source_match_text(item.get("text"))
            if not text_value:
                continue
            title_value = self._normalize_source_match_text(item.get("title"))
            subtitle_value = self._normalize_source_match_text(item.get("subtitle"))
            identity_value = self._normalize_source_match_text(item.get("identity"))
            key = self._normalize_source_match_text(item.get("key")) or (title_value or identity_value or text_value).lower()
            if key in seen:
                continue
            seen.add(key)
            normalized_cards.append(
                {
                    "text": text_value,
                    "key": key,
                    "title": title_value,
                    "subtitle": subtitle_value,
                    "identity": identity_value,
                }
            )
        return normalized_cards

    def _source_card_identity_candidates(self, card: Optional[dict[str, str]]) -> list[str]:
        if not isinstance(card, dict):
            return []
        candidates: list[str] = []
        for value in (
            card.get("identity"),
            card.get("title"),
            card.get("subtitle"),
            card.get("text"),
        ):
            normalized = self._normalize_source_match_text(value)
            if normalized and normalized not in candidates:
                candidates.append(normalized)
        subtitle = self._normalize_source_match_text(card.get("subtitle"))
        if subtitle:
            subtitle_prefix = self._normalize_source_match_text((subtitle.split("·")[0] or "").strip())
            if subtitle_prefix and subtitle_prefix not in candidates:
                candidates.append(subtitle_prefix)
        return candidates

    def _source_lookup_candidates(self, requested: Optional[str], matched_card: Optional[dict[str, str]] = None) -> list[str]:
        candidates: list[str] = []
        for value in [requested, *self._source_card_identity_candidates(matched_card)]:
            normalized = self._normalize_source_match_text(value)
            if normalized and normalized not in candidates:
                candidates.append(normalized)
        return candidates

    def _preferred_source_card_identity(self, card: Optional[dict[str, str]]) -> Optional[str]:
        candidates = self._source_card_identity_candidates(card)
        return candidates[0] if candidates else None

    def _match_source_card(
        self,
        cards: list[dict[str, str]],
        source_match_candidates: Optional[list[str]],
    ) -> Optional[dict[str, str]]:
        normalized_candidates = [
            self._normalize_source_match_text(candidate).lower()
            for candidate in (source_match_candidates or [])
            if self._normalize_source_match_text(candidate)
        ]
        if not normalized_candidates:
            return cards[0] if cards else None

        best_card: Optional[dict[str, str]] = None
        best_score = -1
        for card in cards:
            card_fields = [
                self._normalize_source_match_text(value).lower()
                for value in self._source_card_identity_candidates(card)
                if self._normalize_source_match_text(value)
            ]
            if not card_fields:
                continue
            card_score = -1
            for index, candidate in enumerate(normalized_candidates):
                if not candidate:
                    continue
                score = -1
                for field in card_fields:
                    if not field:
                        continue
                    field_score = -1
                    if candidate == field:
                        field_score = 1_000 - index
                    elif candidate in field:
                        field_score = min(len(candidate), 900) - index
                    elif len(candidate) >= 16 and field in candidate:
                        field_score = min(len(field), 700) - index
                    elif len(candidate) >= 24:
                        overlap = candidate[:48]
                        if overlap and overlap in field:
                            field_score = min(len(overlap), 500) - index
                    if field_score > score:
                        score = field_score
                if score > card_score:
                    card_score = score
            if card_score > best_score:
                best_score = card_score
                best_card = card
        if best_score >= 0:
            return best_card
        return None


    async def _open_project_chats_tab(self, page: Any) -> None:
        tab = await self._wait_for_visible_locator(
            page,
            PROJECT_CHATS_TAB_SELECTORS,
            label="project-chats-tab",
            total_timeout_ms=7_500,
        )
        if tab is None:
            self._log("chat-list", "project chats tab not found; continuing with current surface", current_url=await self._safe_page_url(page))
            return
        try:
            await self._click_locator_with_fallback(
                tab,
                label="project-chats-tab",
                timeout_ms=5_000,
            )
            await page.wait_for_timeout(500)
        except Exception as exc:
            self._log("chat-list", "project chats tab click failed; continuing", error=repr(exc), current_url=await self._safe_page_url(page))

    def _merge_project_chat_lists(self, primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        by_id: dict[str, dict[str, Any]] = {}
        for item in list(primary or []) + list(secondary or []):
            if not isinstance(item, dict):
                continue
            chat_id = str(item.get('id') or '').strip()
            if not chat_id:
                continue
            existing = by_id.get(chat_id)
            if existing is None:
                normalized = dict(item)
                normalized.setdefault('title', '(untitled)')
                by_id[chat_id] = normalized
                merged.append(normalized)
                continue
            for key, value in item.items():
                if value in (None, '', [], {}):
                    continue
                if key not in existing or existing.get(key) in (None, '', [], {}):
                    existing[key] = value
        return merged

    async def _collect_project_chats_from_home_dom(
        self,
        page: Any,
        *,
        project_url: str,
        label: str,
        max_scroll_rounds: int = 6,
    ) -> list[dict[str, Any]]:
        prefix = self._project_conversation_path_prefix() or self._project_conversation_path_prefix_from_url(project_url)
        if not prefix:
            return []

        collected: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        stagnant_rounds = 0
        for round_index in range(max_scroll_rounds):
            snapshot = await page.evaluate(
                r'''
                ({ prefix }) => {
                    const normalize = value => (value || '').replace(/\s+/g, ' ').trim();
                    const isVisible = el => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        if (!style) return false;
                        if (style.display === 'none' || style.visibility === 'hidden') return false;
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    };
                    const isScrollable = el => {
                        if (!el || !isVisible(el)) return false;
                        const style = window.getComputedStyle(el);
                        if (!style) return false;
                        const overflowY = (style.overflowY || '').toLowerCase();
                        if (!['auto', 'scroll', 'overlay'].includes(overflowY)) return false;
                        return el.scrollHeight > el.clientHeight + 24;
                    };
                    const rows = [];
                    const seen = new Set();
                    for (const anchor of Array.from(document.querySelectorAll('main a[href*="/c/"], [role="main"] a[href*="/c/"]'))) {
                        if (!isVisible(anchor)) continue;
                        const href = anchor.getAttribute('href') || '';
                        const absolute = new URL(href, window.location.origin).toString();
                        const path = new URL(absolute).pathname;
                        if (!path.startsWith(prefix)) continue;
                        const row = anchor.closest('li, article, [role="listitem"], a, div');
                        const text = normalize((row || anchor).innerText || (row || anchor).textContent || '');
                        if (!text) continue;
                        const lines = text.split('\n').map(normalize).filter(Boolean);
                        const id = path.split('/c/')[1]?.split(/[/?#]/)[0] || '';
                        if (!id || seen.has(id)) continue;
                        seen.add(id);
                        rows.push({
                            id,
                            title: lines[0] || '(untitled)',
                            preview: lines.slice(1).join(' '),
                            conversation_url: absolute,
                        });
                    }
                    const scrollables = Array.from(document.querySelectorAll('main, [role="main"], main *')).filter(isScrollable);
                    return {
                        rows,
                        scrollables: scrollables.map((el, index) => ({ index, top: el.scrollTop, height: el.clientHeight, scrollHeight: el.scrollHeight })),
                    };
                }
                ''',
                {'prefix': prefix},
            )
            rows = snapshot.get('rows') if isinstance(snapshot, dict) else []
            new_count = 0
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    chat_id = str(row.get('id') or '').strip()
                    if not chat_id or chat_id in seen_ids:
                        continue
                    seen_ids.add(chat_id)
                    collected.append({
                        'id': chat_id,
                        'title': re.sub(r'\s+', ' ', str(row.get('title') or '')).strip() or '(untitled)',
                        'conversation_url': str(row.get('conversation_url') or ''),
                        'preview': re.sub(r'\s+', ' ', str(row.get('preview') or '')).strip() or None,
                        'create_time': None,
                        'update_time': None,
                    })
                    new_count += 1
            self._log(label, 'collected project chats from home DOM', round=round_index + 1, discovered_count=new_count, total_count=len(collected))
            if new_count == 0:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
            if stagnant_rounds >= 2:
                break
            scrolled = await page.evaluate(
                r'''
                () => {
                    const isVisible = el => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        if (!style) return false;
                        if (style.display === 'none' || style.visibility === 'hidden') return false;
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    };
                    const isScrollable = el => {
                        if (!el || !isVisible(el)) return false;
                        const style = window.getComputedStyle(el);
                        if (!style) return false;
                        const overflowY = (style.overflowY || '').toLowerCase();
                        if (!['auto', 'scroll', 'overlay'].includes(overflowY)) return false;
                        return el.scrollHeight > el.clientHeight + 24;
                    };
                    const candidates = Array.from(document.querySelectorAll('main, [role="main"], main *')).filter(isScrollable);
                    let moved = false;
                    for (const el of candidates) {
                        const before = el.scrollTop;
                        el.scrollTop = Math.min(el.scrollTop + Math.max(el.clientHeight * 0.9, 200), el.scrollHeight);
                        if (el.scrollTop > before + 1) moved = true;
                    }
                    if (!moved) {
                        const before = window.scrollY;
                        window.scrollTo(0, before + Math.max(window.innerHeight * 0.9, 300));
                        moved = window.scrollY > before + 1;
                    }
                    return moved;
                }
                '''
            )
            if not scrolled:
                break
            await page.wait_for_timeout(400)
        return collected

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
            raise ResponseTimeoutError("Add source button did not become visible on the Sources tab")
        await self._click_locator_with_fallback(
            button,
            label="project-add-source-button",
            timeout_ms=5_000,
        )
        await page.wait_for_timeout(500)

    async def _click_locator_with_fallback(
        self,
        locator: Any,
        *,
        label: str,
        timeout_ms: int = 5_000,
        allow_force: bool = True,
        allow_evaluate: bool = True,
        handle_rate_limit: bool = True,
    ) -> None:
        page = self._locator_page(locator) if handle_rate_limit else None
        if page is not None:
            await self._wait_for_rate_limit_modal_to_clear(page, label=f'{label}-before-click')
        try:
            await locator.scroll_into_view_if_needed(timeout=min(timeout_ms, 2_000))
        except Exception:
            pass

        last_error: Exception | None = None
        try:
            await locator.click(timeout=timeout_ms)
            return
        except Exception as exc:
            last_error = exc
            self._log("click", "primary locator click failed", label=label, error=repr(exc))
            if page is not None:
                await self._wait_for_rate_limit_modal_to_clear(page, label=f'{label}-after-primary-click-failure')

        if allow_force:
            try:
                await locator.click(timeout=timeout_ms, force=True)
                return
            except Exception as exc:
                last_error = exc
                self._log("click", "force locator click failed", label=label, error=repr(exc))
                if page is not None:
                    await self._wait_for_rate_limit_modal_to_clear(page, label=f'{label}-after-force-click-failure')

        if allow_evaluate:
            try:
                await locator.evaluate("(el) => el.click()")
                return
            except Exception as exc:
                last_error = exc
                self._log("click", "evaluate locator click failed", label=label, error=repr(exc))
                if page is not None:
                    await self._wait_for_rate_limit_modal_to_clear(page, label=f'{label}-after-evaluate-click-failure')

        if last_error is not None:
            raise last_error
        raise ResponseTimeoutError(f"Could not click locator: {label}")

    def _project_source_input_selectors(self, source_kind: str) -> list[str]:
        if source_kind == "link":
            return PROJECT_SOURCE_LINK_INPUT_SELECTORS
        if source_kind == "text":
            return PROJECT_SOURCE_TEXT_INPUT_SELECTORS
        return PROJECT_SOURCE_FILE_INPUT_SELECTORS

    def _project_source_option_kinds(self, source_kind: str) -> list[str]:
        return [source_kind]

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
            input_locator = await self._find_visible_locator(
                page,
                self._project_source_input_selectors(source_kind),
                label=f"project-source-kind-{source_kind}-input-already-visible",
                timeout_ms=800,
            )
            if input_locator is not None:
                self._log(
                    "project-source",
                    "source input already visible without explicit kind selection",
                    source_kind=source_kind,
                )
                return
            self._log(
                "project-source",
                "source kind option not shown; not using unrelated fallback controls",
                source_kind=source_kind,
            )
            return
        try:
            await option.scroll_into_view_if_needed(timeout=2_000)
        except Exception:
            pass
        try:
            await option.click(timeout=5_000)
        except Exception:
            await option.click(timeout=5_000, force=True)
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

    async def _locator_is_enabled(self, locator: Any) -> bool:
        try:
            if hasattr(locator, "is_enabled") and await locator.is_enabled():
                disabled = await locator.get_attribute("disabled")
                aria_disabled = await locator.get_attribute("aria-disabled")
                visually_disabled = await locator.get_attribute("data-visually-disabled")
                return disabled is None and (aria_disabled or "").lower() != "true" and visually_disabled is None
        except Exception:
            pass
        try:
            disabled = await locator.get_attribute("disabled")
            aria_disabled = await locator.get_attribute("aria-disabled")
            visually_disabled = await locator.get_attribute("data-visually-disabled")
            return disabled is None and (aria_disabled or "").lower() != "true" and visually_disabled is None
        except Exception:
            return False

    async def _wait_for_enabled_locator(self, locator: Any, *, timeout_ms: int = 5_000) -> bool:
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        while asyncio.get_running_loop().time() < deadline:
            if await self._locator_is_enabled(locator):
                return True
            await asyncio.sleep(0.2)
        return await self._locator_is_enabled(locator)

    def _project_source_value_selectors(self, source_kind: str, *, option_kind: Optional[str] = None) -> list[str]:
        effective_kind = option_kind or source_kind
        return self._project_source_input_selectors(effective_kind)

    def _normalize_project_source_option_label(self, label: Any) -> Optional[str]:
        text = self._normalize_source_match_text(label)
        if not text:
            return None
        normalized = re.sub(r'\s+', ' ', text).strip()
        return normalized

    def _project_source_kind_from_label(self, label: Any) -> Optional[str]:
        normalized = self._normalize_project_source_option_label(label)
        if not normalized:
            return None
        lowered = normalized.lower()
        for kind, aliases in PROJECT_SOURCE_OPTION_KIND_ALIASES.items():
            for alias in aliases:
                if alias in lowered:
                    return kind
        return None

    def _project_source_capability_summary(self, option_labels: list[str]) -> list[dict[str, str]]:
        summary: list[dict[str, str]] = []
        seen_kinds: set[str] = set()
        for label in option_labels:
            normalized = self._normalize_project_source_option_label(label)
            if not normalized:
                continue
            kind = self._project_source_kind_from_label(normalized)
            if kind is None or kind in seen_kinds:
                continue
            summary.append({'kind': kind, 'label': normalized})
            seen_kinds.add(kind)
        return summary

    async def _discover_project_source_capabilities(self, page: Any) -> list[dict[str, str]]:
        try:
            option_labels = await page.evaluate(
                r"""
                (roots) => {
                    const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
                    const isVisible = (el) => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        if (!style) return false;
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    };
                    const results = [];
                    const seen = new Set();
                    const rootNodes = [];
                    for (const selector of roots) {
                        for (const node of document.querySelectorAll(selector)) {
                            if (isVisible(node)) rootNodes.push(node);
                        }
                    }
                    const targets = [
                        'button',
                        '[role=\"button\"]',
                        '[role=\"menuitem\"]',
                        '[role=\"option\"]',
                        'a',
                    ];
                    for (const root of rootNodes) {
                        for (const selector of targets) {
                            for (const node of root.querySelectorAll(selector)) {
                                if (!isVisible(node)) continue;
                                const text = normalize(node.innerText || node.textContent || '');
                                if (!text || text.length > 120) continue;
                                const key = text.toLowerCase();
                                if (seen.has(key)) continue;
                                seen.add(key);
                                results.push(text);
                            }
                        }
                    }
                    return results;
                }
                """,
                PROJECT_SOURCE_OPTION_DISCOVERY_ROOT_SELECTORS,
            )
        except Exception:
            return []
        if not isinstance(option_labels, list):
            return []
        normalized_labels = [
            self._normalize_project_source_option_label(label)
            for label in option_labels
            if self._normalize_project_source_option_label(label)
        ]
        return self._project_source_capability_summary(normalized_labels)

    async def _require_project_source_capability(self, page: Any, source_kind: str) -> list[dict[str, str]]:
        capabilities = await self._discover_project_source_capabilities(page)
        if capabilities:
            self._log(
                'project-source',
                'discovered add-source capabilities',
                requested_source_kind=source_kind,
                available_source_kinds=[item['kind'] for item in capabilities],
                available_source_labels=[item['label'] for item in capabilities],
            )
            available_kinds = {item['kind'] for item in capabilities}
            if source_kind not in available_kinds:
                raise UnsupportedOperationError(
                    f"Project source kind {source_kind!r} is not exposed in the current Add sources modal; available_source_kinds={[item['kind'] for item in capabilities]!r}"
                )
        return capabilities

    async def _add_project_textual_source(
        self,
        page: Any,
        *,
        source_kind: str,
        value: str,
        display_name: Optional[str],
    ) -> None:
        await self._click_add_source_button(page)
        input_locator = await self._find_visible_locator(
            page,
            self._project_source_value_selectors(source_kind),
            label=f"project-source-{source_kind}-input-preopened",
            timeout_ms=800,
        )
        selected_option_kind = source_kind
        if input_locator is None:
            await self._require_project_source_capability(page, source_kind)
            for option_kind in self._project_source_option_kinds(source_kind):
                await self._click_source_kind_option(page, option_kind)
                input_locator = await self._find_visible_locator(
                    page,
                    self._project_source_value_selectors(source_kind, option_kind=option_kind),
                    label=f"project-source-{source_kind}-input-after-{option_kind}",
                    timeout_ms=1_200,
                )
                if input_locator is not None:
                    selected_option_kind = option_kind
                    if option_kind != source_kind:
                        self._log(
                            "project-source",
                            "source kind resolved via scoped fallback option",
                            requested_source_kind=source_kind,
                            selected_option_kind=option_kind,
                        )
                    break
            if input_locator is None:
                await self._require_project_source_capability(page, source_kind)
                input_locator = await self._wait_for_visible_locator(
                    page,
                    self._project_source_value_selectors(source_kind),
                    label=f"project-source-{source_kind}-input",
                    total_timeout_ms=10_000,
                )
        else:
            self._log(
                "project-source",
                "source input became visible immediately after clicking Add",
                source_kind=source_kind,
            )
        if input_locator is None:
            raise ResponseTimeoutError(f"Input for project source kind {source_kind!r} did not become visible")

        await self._fill_locator_text(input_locator, value)

        title_value = display_name
        if source_kind == "link" and selected_option_kind == "text" and not title_value:
            parsed = urlparse(value)
            title_value = parsed.netloc or value

        title_locator = await self._find_visible_locator(
            page,
            PROJECT_SOURCE_TITLE_INPUT_SELECTORS,
            label="project-source-title-input",
            timeout_ms=800,
        )
        if title_locator is None and source_kind == "link" and selected_option_kind == "text" and title_value:
            title_locator = await self._find_visible_locator(
                page,
                [
                    '[role="dialog"] input[type="text"]',
                    'dialog[open] input[type="text"]',
                ],
                label="project-source-title-input-fallback",
                timeout_ms=800,
            )
        if title_locator is not None and title_value:
            await self._fill_locator_text(title_locator, title_value)

        save_button = await self._wait_for_visible_locator(
            page,
            PROJECT_SOURCE_SAVE_BUTTON_SELECTORS,
            label="project-source-save-button",
            total_timeout_ms=10_000,
        )
        if save_button is None:
            raise ResponseTimeoutError("Project source save/add button did not become visible")
        if not await self._wait_for_enabled_locator(save_button, timeout_ms=5_000):
            raise ResponseTimeoutError(
                f"Project source save/add button stayed disabled (source_kind={source_kind}, selected_option_kind={selected_option_kind})"
            )
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


    def _is_project_source_commit_request(self, request_or_url: Any, *, source_kind: str) -> bool:
        try:
            url = request_or_url.url if hasattr(request_or_url, "url") else str(request_or_url)
        except Exception:
            return False
        normalized_url = (url or "").lower()
        if not normalized_url:
            return False
        if '/backend-api/gizmos/snorlax/upsert' in normalized_url:
            return True
        if source_kind in {"text", "file"} and '/backend-api/files/process_upload_stream' in normalized_url:
            return True
        return False

    def _is_project_source_save_request(self, request_or_url: Any, *, source_kind: str) -> bool:
        try:
            url = request_or_url.url if hasattr(request_or_url, "url") else str(request_or_url)
        except Exception:
            return False
        normalized_url = (url or "").lower()
        if not normalized_url:
            return False
        if self._is_project_source_commit_request(normalized_url, source_kind=source_kind):
            return True
        if source_kind in {"text", "file"} and 'oaiusercontent.com/files/' in normalized_url and '/raw' in normalized_url:
            return True
        return False

    def _install_project_source_save_request_watch(self, context: Any, *, source_kind: str) -> dict[str, Any]:
        watch: dict[str, Any] = {
            "source_kind": source_kind,
            "installed": False,
            "started": 0,
            "finished": 0,
            "failed": 0,
            "saw_relevant": False,
            "saw_commit": False,
            "inflight": set(),
            "last_activity": None,
            "handlers": None,
        }
        if context is None or not hasattr(context, "on"):
            return watch

        loop = asyncio.get_running_loop()

        def on_request(req: Any) -> None:
            if not self._is_project_source_save_request(req, source_kind=source_kind):
                return
            inflight = watch.setdefault("inflight", set())
            inflight.add(id(req))
            watch["started"] = int(watch.get("started") or 0) + 1
            watch["saw_relevant"] = True
            is_commit = self._is_project_source_commit_request(req, source_kind=source_kind)
            if is_commit:
                watch["saw_commit"] = True
            watch["last_activity"] = loop.time()
            self._log(
                "project-source-add",
                "observed project source save request start",
                source_kind=source_kind,
                method=getattr(req, "method", None),
                url=getattr(req, "url", None),
                is_commit=is_commit,
                started=watch.get("started"),
                inflight=len(inflight),
            )

        def on_request_finished(req: Any) -> None:
            inflight = watch.setdefault("inflight", set())
            token = id(req)
            if token not in inflight:
                return
            inflight.discard(token)
            watch["finished"] = int(watch.get("finished") or 0) + 1
            watch["last_activity"] = loop.time()
            self._log(
                "project-source-add",
                "observed project source save request finish",
                source_kind=source_kind,
                method=getattr(req, "method", None),
                url=getattr(req, "url", None),
                finished=watch.get("finished"),
                inflight=len(inflight),
            )

        def on_request_failed(req: Any) -> None:
            token = id(req)
            relevant = self._is_project_source_save_request(req, source_kind=source_kind)
            inflight = watch.setdefault("inflight", set())
            was_inflight = token in inflight
            if not relevant and not was_inflight:
                return
            inflight.discard(token)
            watch["failed"] = int(watch.get("failed") or 0) + 1
            watch["saw_relevant"] = True
            is_commit = self._is_project_source_commit_request(req, source_kind=source_kind)
            if is_commit:
                watch["saw_commit"] = True
            watch["last_activity"] = loop.time()
            failure_text = None
            try:
                failure = req.failure
                failure_text = failure if isinstance(failure, str) else getattr(failure, "error_text", None)
            except Exception:
                failure_text = None
            self._log(
                "project-source-add",
                "observed project source save request failure",
                source_kind=source_kind,
                method=getattr(req, "method", None),
                url=getattr(req, "url", None),
                is_commit=is_commit,
                failure=failure_text,
                failed=watch.get("failed"),
                inflight=len(inflight),
            )

        context.on("request", on_request)
        context.on("requestfinished", on_request_finished)
        context.on("requestfailed", on_request_failed)
        watch["installed"] = True
        watch["handlers"] = {
            "request": on_request,
            "requestfinished": on_request_finished,
            "requestfailed": on_request_failed,
        }
        return watch

    def _dispose_project_source_save_request_watch(self, context: Any, watch: Optional[dict[str, Any]]) -> None:
        if context is None or not watch or not watch.get("installed"):
            return
        handlers = watch.get("handlers") or {}
        for event_name, handler in handlers.items():
            if handler is None:
                continue
            try:
                if hasattr(context, "remove_listener"):
                    context.remove_listener(event_name, handler)
                elif hasattr(context, "off"):
                    context.off(event_name, handler)
            except Exception as exc:
                self._log(
                    "project-source-add",
                    "failed to dispose project source save request watch",
                    source_kind=watch.get("source_kind"),
                    event_name=event_name,
                    error=str(exc),
                )

    async def _wait_for_project_source_save_request_quiet(
        self,
        page: Any,
        watch: Optional[dict[str, Any]],
        *,
        source_kind: str,
        timeout_ms: int = 15_000,
        observation_window_ms: int = 8_000,
        quiet_window_ms: int = 2_000,
        poll_interval_ms: int = 150,
    ) -> dict[str, Any]:
        if watch is None:
            await page.wait_for_timeout(observation_window_ms)
            return {
                "source_kind": source_kind,
                "saw_relevant": False,
                "started": 0,
                "finished": 0,
                "failed": 0,
                "inflight": 0,
                "quiet_window_ms": quiet_window_ms,
                "observation_window_ms": observation_window_ms,
            }

        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        observation_deadline = min(deadline, asyncio.get_running_loop().time() + (observation_window_ms / 1000))
        quiet_window_s = quiet_window_ms / 1000
        last_state: dict[str, Any] = {}

        while asyncio.get_running_loop().time() < deadline:
            now = asyncio.get_running_loop().time()
            saw_relevant = bool(watch.get("saw_relevant"))
            saw_commit = bool(watch.get("saw_commit"))
            inflight = watch.get("inflight") or set()
            started = int(watch.get("started") or 0)
            finished = int(watch.get("finished") or 0)
            failed = int(watch.get("failed") or 0)
            last_activity = watch.get("last_activity")
            idle_for_s = None if last_activity is None else max(0.0, now - float(last_activity))
            observation_window_elapsed = now >= observation_deadline
            quiet_enough = (idle_for_s is not None and idle_for_s >= quiet_window_s)
            waiting_for_late_commit = source_kind in {"text", "file"} and saw_relevant and not saw_commit
            quiet_now = not inflight and (
                (
                    saw_relevant
                    and quiet_enough
                    and (not waiting_for_late_commit or observation_window_elapsed)
                )
                or (not saw_relevant and observation_window_elapsed)
            )
            last_state = {
                "source_kind": source_kind,
                "saw_relevant": saw_relevant,
                "saw_commit": saw_commit,
                "started": started,
                "finished": finished,
                "failed": failed,
                "inflight": len(inflight),
                "idle_for_s": idle_for_s,
                "observation_window_elapsed": observation_window_elapsed,
                "waiting_for_late_commit": waiting_for_late_commit,
                "quiet_now": quiet_now,
            }
            self._log(
                "project-source-add",
                "project source save quiet probe",
                quiet_window_ms=quiet_window_ms,
                observation_window_ms=observation_window_ms,
                **last_state,
            )
            if quiet_now:
                return last_state
            await page.wait_for_timeout(poll_interval_ms)

        raise ResponseTimeoutError(
            "Timed out waiting for project source save requests to go quiet "
            f"(source_kind={source_kind}, saw_relevant={last_state.get('saw_relevant')}, "
            f"saw_commit={last_state.get('saw_commit')}, started={last_state.get('started')}, "
            f"finished={last_state.get('finished')}, failed={last_state.get('failed')}, "
            f"inflight={last_state.get('inflight')})"
        )

    async def _verify_project_source_persistence(
        self,
        page: Any,
        *,
        project_url: str,
        source_match_candidates: list[str],
        timeout_ms: int = 15_000,
        max_refresh_attempts: int = 3,
        retry_backoff_ms: tuple[int, ...] = (2_000, 4_000),
    ) -> Optional[dict[str, str]]:
        if not source_match_candidates:
            raise ResponseTimeoutError("Project source persistence check requires at least one source match candidate")
        sources_url = self._project_sources_url(project_url)
        last_error: ResponseTimeoutError | None = None

        for attempt in range(max(max_refresh_attempts, 1)):
            label = "project-source-add-persistence-refresh"
            if attempt:
                label = f"project-source-add-persistence-refresh-retry-{attempt + 1}"
            self._log(
                "project-source-add",
                "verifying project source persistence after refresh",
                project_url=project_url,
                sources_url=sources_url,
                source_match_candidates=source_match_candidates,
                attempt=attempt + 1,
                max_refresh_attempts=max(max_refresh_attempts, 1),
            )
            await self._goto(page, sources_url, label=label)
            try:
                return await self._wait_for_source_presence(
                    page,
                    source_match_candidates=source_match_candidates,
                    before_sources=None,
                    accept_single_new_card=False,
                    timeout_ms=timeout_ms,
                )
            except ResponseTimeoutError as exc:
                last_error = exc
                empty_state_visible = await self._project_sources_empty_state_visible(page)
                source_cards = await self._snapshot_project_source_cards(page)
                self._log(
                    "project-source-add",
                    "project source persistence attempt timed out",
                    attempt=attempt + 1,
                    max_refresh_attempts=max(max_refresh_attempts, 1),
                    source_match_candidates=source_match_candidates,
                    empty_state_visible=empty_state_visible,
                    source_card_count=len(source_cards),
                    current_url=await self._safe_page_url(page),
                    error=str(exc),
                )
                if attempt + 1 >= max(max_refresh_attempts, 1):
                    raise
                backoff_ms = retry_backoff_ms[min(attempt, max(len(retry_backoff_ms) - 1, 0))] if retry_backoff_ms else 0
                if backoff_ms > 0:
                    await page.wait_for_timeout(backoff_ms)

        if last_error is not None:
            raise last_error
        raise ResponseTimeoutError(
            f"Timed out waiting for project source to appear: {source_match_candidates[0]}"
        )

    async def _wait_for_source_presence(
        self,
        page: Any,
        source_match: Optional[str] = None,
        *,
        source_match_candidates: Optional[list[str]] = None,
        before_sources: Optional[list[dict[str, str]]] = None,
        accept_single_new_card: bool = False,
        timeout_ms: int = 20_000,
    ) -> Optional[dict[str, str]]:
        candidates = [
            self._normalize_source_match_text(candidate)
            for candidate in (source_match_candidates or ([] if source_match is None else [source_match]))
            if self._normalize_source_match_text(candidate)
        ]
        if not candidates and not before_sources:
            await page.wait_for_timeout(1_500)
            return None

        before_keys = {
            self._normalize_source_match_text(item.get('key') or item.get('title') or item.get('identity') or item.get('text')).lower()
            for item in (before_sources or [])
            if self._normalize_source_match_text(item.get('key') or item.get('title') or item.get('identity') or item.get('text'))
        }
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        while asyncio.get_running_loop().time() < deadline:
            cards = await self._snapshot_project_source_cards(page)

            if accept_single_new_card and not before_keys and len(cards) == 1:
                return cards[0]

            if before_keys:
                new_cards = [
                    card for card in cards
                    if self._normalize_source_match_text(card.get('key') or card.get('title') or card.get('identity') or card.get('text')).lower() not in before_keys
                ]
                matched_new_card = self._match_source_card(new_cards, candidates)
                if matched_new_card is not None:
                    return matched_new_card
                if accept_single_new_card and len(new_cards) == 1:
                    return new_cards[0]
                if new_cards and not candidates:
                    return new_cards[0]

            matched_card = self._match_source_card(cards, candidates)
            if matched_card is not None:
                return matched_card

            for candidate in candidates:
                container = await self._find_project_source_container(page, candidate, exact=False)
                if container is not None:
                    return {'text': candidate, 'title': candidate, 'key': candidate.lower()}

            await page.wait_for_timeout(500)
        target = candidates[0] if candidates else '<new source>'
        raise ResponseTimeoutError(f"Timed out waiting for project source to appear: {target}")

    async def _wait_for_project_source_post_save_settle(
        self,
        page: Any,
        *,
        source_kind: str,
        timeout_ms: int = 12_000,
        poll_interval_ms: int = 400,
        required_observations: int = 3,
    ) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        stable_observations = 0
        last_url: Optional[str] = None
        last_state: dict[str, Any] = {}

        while asyncio.get_running_loop().time() < deadline:
            dialog_visible = await self._find_visible_locator(
                page,
                PROJECT_SOURCE_DIALOG_SCOPE_SELECTORS,
                label=f"project-source-{source_kind}-post-save-dialog",
                timeout_ms=250,
            ) is not None
            add_button_visible = await self._find_visible_locator(
                page,
                PROJECT_ADD_SOURCE_BUTTON_SELECTORS,
                label=f"project-source-{source_kind}-post-save-add-button",
                timeout_ms=250,
            ) is not None
            source_cards = await self._snapshot_project_source_cards(page)
            empty_state_visible = await self._project_sources_empty_state_visible(page)
            current_url = await self._safe_page_url(page)
            url_stable = bool(last_url and current_url == last_url)
            sources_surface_ready = add_button_visible and (bool(source_cards) or empty_state_visible)
            settled_now = not dialog_visible and sources_surface_ready and url_stable
            last_state = {
                "source_kind": source_kind,
                "dialog_visible": dialog_visible,
                "add_button_visible": add_button_visible,
                "source_card_count": len(source_cards),
                "empty_state_visible": empty_state_visible,
                "sources_surface_ready": sources_surface_ready,
                "url_stable": url_stable,
                "current_url": current_url,
            }
            self._log(
                "project-source-add",
                "post-save settle probe",
                stable_observations=stable_observations,
                required_observations=max(required_observations, 1),
                settled_now=settled_now,
                **last_state,
            )
            if settled_now:
                stable_observations += 1
                if stable_observations >= max(required_observations, 1):
                    return last_state
            else:
                stable_observations = 0
            last_url = current_url
            await page.wait_for_timeout(poll_interval_ms)

        raise ResponseTimeoutError(
            "Timed out waiting for project source post-save UI to settle "
            f"(source_kind={source_kind}, dialog_visible={last_state.get('dialog_visible')}, "
            f"add_button_visible={last_state.get('add_button_visible')}, "
            f"source_card_count={last_state.get('source_card_count')}, "
            f"empty_state_visible={last_state.get('empty_state_visible')}, "
            f"url_stable={last_state.get('url_stable')})"
        )

    async def _project_source_is_stably_absent(
        self,
        page: Any,
        source_names: str | list[str],
        *,
        exact: bool,
        required_observations: int = 3,
        poll_interval_ms: int = 500,
    ) -> bool:
        candidates = self._normalize_source_lookup_inputs(source_names)
        if not candidates:
            return True

        stable_observations = 0
        for _ in range(max(required_observations, 1)):
            source_cards = await self._snapshot_project_source_cards(page)
            matched_card = self._match_source_card(source_cards, candidates)
            action_button = await self._find_project_source_action_button(page, candidates, exact=exact)
            container = None
            if action_button is None and matched_card is None:
                for candidate in candidates:
                    container = await self._find_project_source_container(page, candidate, exact=exact)
                    if container is not None:
                        break
            empty_state_visible = await self._project_sources_empty_state_visible(page)
            cards_empty = len(source_cards) == 0
            absent_now = action_button is None and matched_card is None and container is None and (empty_state_visible or cards_empty)
            self._log(
                'project-source-remove',
                'stable absence probe',
                source_candidates=candidates,
                source_card_count=len(source_cards),
                matched_card=(matched_card or {}).get('identity') if isinstance(matched_card, dict) else None,
                empty_state_visible=empty_state_visible,
                cards_empty=cards_empty,
                absent_now=absent_now,
                current_url=await self._safe_page_url(page),
            )
            if not absent_now:
                return False
            stable_observations += 1
            if stable_observations >= max(required_observations, 1):
                return True
            await page.wait_for_timeout(poll_interval_ms)
        return False

    async def _wait_for_source_absence(
        self,
        page: Any,
        source_name: str | list[str],
        *,
        exact: bool,
        timeout_ms: int = 20_000,
    ) -> None:
        candidates = self._normalize_source_lookup_inputs(source_name)
        if not candidates:
            return
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        while asyncio.get_running_loop().time() < deadline:
            action_button = await self._find_project_source_action_button(page, candidates, exact=exact)
            if action_button is None:
                return
            await page.wait_for_timeout(500)
        raise ResponseTimeoutError(f"Timed out waiting for project source to disappear: {candidates[0]}")

    def _normalize_source_lookup_inputs(self, source_names: str | list[str] | tuple[str, ...] | None) -> list[str]:
        raw_values: list[str] = []
        if isinstance(source_names, str):
            raw_values = [source_names]
        elif source_names:
            raw_values = list(source_names)
        normalized: list[str] = []
        for value in raw_values:
            normalized_value = self._normalize_source_match_text(value)
            if normalized_value and normalized_value not in normalized:
                normalized.append(normalized_value)
        return normalized

    def _project_sources_url(self, project_url: Optional[str] = None) -> str:
        base_url = project_url or self._project_home_url()
        parsed = urlparse(base_url)
        query_pairs: list[tuple[str, str]] = []
        existing_tab = False
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            if key == 'tab':
                query_pairs.append((key, 'sources'))
                existing_tab = True
            else:
                query_pairs.append((key, value))
        if not existing_tab:
            query_pairs.append(('tab', 'sources'))
        query = urlencode(query_pairs)
        return urlunparse(parsed._replace(query=query))

    async def _project_sources_empty_state_visible(self, page: Any) -> bool:
        try:
            visible = await page.evaluate(
                r"""
                () => {
                    const normalize = value => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
                    const isVisible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                    const surfaces = Array.from(
                        document.querySelectorAll('[data-project-home-sources-surface="true"], section[aria-label="Sources"], [role="tabpanel"][data-state="active"]')
                    ).filter(isVisible);
                    for (const surface of (surfaces.length ? surfaces : [document.body])) {
                        const text = normalize(surface.innerText || surface.textContent || '');
                        if (!text) continue;
                        if (text.includes('give chatgpt more context')) return true;
                    }
                    return false;
                }
                """
            )
        except Exception:
            return False
        return bool(visible)

    async def _wait_for_project_source_action_button(
        self,
        page: Any,
        source_names: str | list[str],
        *,
        exact: bool,
        timeout_ms: int = 18_000,
        poll_interval_ms: int = 750,
    ) -> tuple[Optional[Any], Optional[dict[str, str]], list[str]]:
        candidates = self._normalize_source_lookup_inputs(source_names)
        if not candidates:
            return None, None, []

        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        refresh_attempted = False
        last_matched_card: Optional[dict[str, str]] = None
        last_empty_state = False
        while asyncio.get_running_loop().time() < deadline:
            source_cards = await self._snapshot_project_source_cards(page)
            matched_card = self._match_source_card(source_cards, candidates)
            if matched_card is not None:
                last_matched_card = matched_card
                candidates = self._source_lookup_candidates(candidates[0], matched_card)
            action_button = await self._find_project_source_action_button(page, candidates, exact=exact)
            if action_button is not None:
                return action_button, last_matched_card, candidates

            last_empty_state = await self._project_sources_empty_state_visible(page)
            self._log(
                'project-source-remove',
                'project source action button not ready yet',
                source_candidates=candidates,
                source_card_count=len(source_cards),
                matched_card=(last_matched_card or {}).get('identity') if isinstance(last_matched_card, dict) else None,
                empty_state_visible=last_empty_state,
                current_url=await self._safe_page_url(page),
            )
            if last_empty_state and not refresh_attempted:
                refresh_attempted = True
                await self._goto(page, self._project_sources_url(), label='project-source-remove-sources-refresh')
                await page.wait_for_timeout(max(poll_interval_ms, 1_000))
                continue
            await page.wait_for_timeout(poll_interval_ms)

        self._log(
            'project-source-remove',
            'project source action button lookup timed out',
            source_candidates=candidates,
            matched_card=(last_matched_card or {}).get('identity') if isinstance(last_matched_card, dict) else None,
            empty_state_visible=last_empty_state,
            current_url=await self._safe_page_url(page),
        )
        return None, last_matched_card, candidates

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

    async def _find_project_source_action_button(
        self,
        page: Any,
        source_names: list[str],
        *,
        exact: bool,
    ) -> Optional[Any]:
        normalized_needles = [
            self._normalize_source_match_text(candidate)
            for candidate in (source_names or [])
            if self._normalize_source_match_text(candidate)
        ]
        if not normalized_needles:
            return None
        handle = await page.evaluate_handle(
            r"""
            ({ needles, exact }) => {
                const normalize = value => (value || '').replace(/\s+/g, ' ').trim();
                const normalizeLower = value => normalize(value).toLowerCase();
                const isVisible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                const rootCandidates = Array.from(
                    document.querySelectorAll(
                        '[data-project-home-sources-surface="true"], section[aria-label="Sources"], [role="tabpanel"][data-state="active"], [role="tabpanel"]'
                    )
                ).filter(isVisible);
                const roots = rootCandidates.length
                    ? rootCandidates
                    : Array.from(document.querySelectorAll('main, [role="main"], body')).filter(isVisible);
                const normalizedNeedles = needles.map(normalizeLower).filter(Boolean);
                const isEmptyStateText = text => normalizeLower(text).includes('give chatgpt more context');
                const scoreValue = value => {
                    const haystack = normalizeLower(value);
                    if (!haystack) return -1;
                    let best = -1;
                    for (const needle of normalizedNeedles) {
                        if (!needle) continue;
                        let score = -1;
                        if (haystack === needle) {
                            score = 1000;
                        } else if (!exact && haystack.includes(needle)) {
                            score = Math.min(needle.length, 900);
                        } else if (!exact && needle.length >= 16 && needle.includes(haystack)) {
                            score = Math.min(haystack.length, 700);
                        }
                        if (score > best) best = score;
                    }
                    return best;
                };
                const isSourceActionButton = button => {
                    if (!button || !isVisible(button)) return false;
                    const aria = normalizeLower(button.getAttribute('aria-label') || '');
                    const testid = normalizeLower(button.getAttribute('data-testid') || '');
                    const hasPopup = normalizeLower(button.getAttribute('aria-haspopup') || '');
                    if (aria.includes('source actions')) return true;
                    if (hasPopup !== 'menu') return false;
                    return aria.includes('source') || testid.includes('source') || !!button.closest('[data-project-home-sources-surface="true"], section[aria-label="Sources"], [role="tabpanel"]');
                };
                let bestButton = null;
                let bestScore = -1;
                for (const root of roots) {
                    const buttons = Array.from(root.querySelectorAll('button,[role="button"]')).filter(isSourceActionButton);
                    for (const button of buttons) {
                        let current = button.closest('[data-testid*="source"], [class*="file-row"], [class*="source"], li, article, [role="listitem"], div') || button.parentElement;
                        while (current && current !== root && current !== document.body) {
                            if (!isVisible(current)) {
                                current = current.parentElement;
                                continue;
                            }
                            const text = normalize(current.innerText || current.textContent || '');
                            if (!text || text.length > 600 || isEmptyStateText(text) || /^add\s*$/i.test(text) || /^add\s+source$/i.test(text)) {
                                current = current.parentElement;
                                continue;
                            }
                            const rawLines = String(current.innerText || current.textContent || '').split('\n');
                            const lines = rawLines.map(value => normalize(value)).filter(Boolean);
                            const titleNode = Array.from(current.querySelectorAll('[title], [aria-label], .truncate, .font-semibold, [class*="font-semibold"]'))
                                .find(el => {
                                    if (!isVisible(el)) return false;
                                    const aria = normalizeLower(el.getAttribute('aria-label') || '');
                                    return !aria.includes('source actions') && !el.closest('button,[role="button"]');
                                }) || null;
                            const title = normalize(
                                (titleNode && (titleNode.getAttribute('title') || titleNode.getAttribute('aria-label') || titleNode.innerText || titleNode.textContent)) ||
                                lines[0] ||
                                ''
                            );
                            const subtitle = Array.from(current.querySelectorAll('.text-token-text-secondary, time'))
                                .filter(isVisible)
                                .map(el => normalize(el.innerText || el.textContent || ''))
                                .filter(Boolean)
                                .join(' ') || (lines.length > 1 ? lines[1] : '');
                            const subtitlePrefix = normalize((subtitle.split('·')[0] || '').trim());
                            const identity = normalize([title, subtitlePrefix].filter(Boolean).join(' '));
                            const values = [identity, title, subtitle, text].filter(Boolean);
                            let score = -1;
                            for (const value of values) {
                                const valueScore = scoreValue(value);
                                if (valueScore > score) score = valueScore;
                            }
                            if (score > bestScore) {
                                bestScore = score;
                                bestButton = button;
                            }
                            break;
                        }
                    }
                }
                return bestScore >= 0 ? bestButton : null;
            }
            """,
            {"needles": normalized_needles, "exact": exact},
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

    async def _find_project_sidebar_container(self, page: Any, *, project_url: Optional[str] = None) -> Optional[Any]:
        target_url = project_url or self._project_home_url()
        project_id = self._extract_project_id_from_url(target_url)
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
                const hasVisibleLayout = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                const anchors = Array.from(
                    document.querySelectorAll(
                        'a[data-sidebar-item="true"][href*="/project"], aside a[href*="/project"], nav a[href*="/project"], a[href*="/project"]'
                    )
                );
                for (const anchor of anchors) {
                    const hrefProjectId = extractProjectId(anchor.getAttribute('href') || '');
                    if (!hrefProjectId || hrefProjectId !== projectId) continue;
                    let current = anchor.closest('li') || anchor;
                    while (current && current !== document.body) {
                        const buttons = Array.from(current.querySelectorAll('button,[role="button"]')).filter(hasVisibleLayout);
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
                    return anchor.closest('li') || anchor;
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

        prioritized: list[Any] = []
        for button in visible_buttons:
            try:
                aria_label = ((await button.get_attribute('aria-label')) or '').strip().lower()
                has_popup = ((await button.get_attribute('aria-haspopup')) or '').strip().lower()
                data_trailing = await button.get_attribute('data-trailing-button')
            except Exception:
                continue
            if aria_label.startswith('open project options for '):
                prioritized.append(button)
                continue
            if any(hint in aria_label for hint in PROJECT_OPTIONS_ARIA_HINTS):
                prioritized.append(button)
                continue
            if data_trailing is not None and has_popup == 'menu':
                prioritized.append(button)
                continue
            if has_popup == 'menu':
                prioritized.append(button)

        if prioritized:
            return prioritized[0]
        return visible_buttons[-1] if visible_buttons else None

    async def _wait_for_project_absence(self, page: Any, *, deleted_project_url: str, timeout_ms: int = 20_000) -> None:
        deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
        deleted_project_key = self._project_identity_key_from_url(deleted_project_url)
        while asyncio.get_running_loop().time() < deadline:
            current_url = await self._safe_page_url(page)
            current_project_key = self._project_identity_key_from_url(current_url)
            if current_project_key != deleted_project_key or not self._is_project_home_url(current_url):
                return
            container = await self._find_project_sidebar_container(page, project_url=deleted_project_url)
            if container is None:
                return
            await page.wait_for_timeout(500)
        raise ResponseTimeoutError(f"Timed out waiting for project to disappear: {deleted_project_url}")

    def _is_project_home_url(self, url: str) -> bool:
        path = urlparse(url).path.rstrip("/")
        return bool(re.search(r'/g/g-p-[^/]+/project$', path)) or path.endswith('/project')

    def _is_conversation_url(self, url: str) -> bool:
        path = urlparse(url).path
        return '/c/' in path

    def _response_completion_signal_ready(
        self,
        *,
        current_url: str,
        content_present: bool,
        stop_visible: bool,
        thinking_visible: bool,
        observed_running_state: bool,
        observed_idle_after_running: bool,
    ) -> bool:
        ui_idle = not stop_visible and not thinking_visible
        if not ui_idle:
            return False
        if observed_running_state and observed_idle_after_running:
            return True
        return bool(content_present and self._is_conversation_url(current_url))

    def _project_conversation_path_prefix(self) -> Optional[str]:
        parsed = urlparse(self.config.project_url)
        path = parsed.path.rstrip("/")
        if path.endswith("/project"):
            return path[:-len("/project")] + "/c/"
        return None


    def _project_conversation_path_prefix_from_url(self, project_url: str) -> Optional[str]:
        parsed = urlparse(project_url)
        path = parsed.path.rstrip('/')
        if path.endswith('/project'):
            return path[:-len('/project')] + '/c/'
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
            current_url = await self._safe_page_url(page)
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
                text_length = len(candidate_text)

                completion_ready = self._response_completion_signal_ready(
                    current_url=current_url,
                    content_present=bool(text_length),
                    stop_visible=bool(submit_state.get("stop_visible")),
                    thinking_visible=bool(thinking_state.get("visible")),
                    observed_running_state=observed_running_state,
                    observed_idle_after_running=observed_idle_after_running,
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
                    current_url=current_url,
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

            conversation_url = page.url
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
            current_url = await self._safe_page_url(page)
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

                completion_ready = self._response_completion_signal_ready(
                    current_url=current_url,
                    content_present=bool(text_length),
                    stop_visible=bool(submit_state.get("stop_visible")),
                    thinking_visible=bool(thinking_state.get("visible")),
                    observed_running_state=observed_running_state,
                    observed_idle_after_running=observed_idle_after_running,
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
        await self._wait_for_rate_limit_modal_to_clear(page, label=label)

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
        def observe_response(resp: Any) -> None:
            status = getattr(resp, "status", None)
            url = getattr(resp, "url", "")
            if status == 429 and self._is_conversation_history_url(url):
                self._note_conversation_history_rate_limit(trigger="response", url=url, status=status)
            if self._is_snorlax_sidebar_url(url):
                self._log("browser-response", "snorlax sidebar response", status=status, url=url)
            if self.config.debug and status and status >= 400:
                self._log("browser-response", "http error response", status=status, url=url)

        context.on("response", observe_response)

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

        def log_page_created(new_page: Any) -> None:
            self._log("browser-page", "new page detected", operation=operation_name, url=new_page.url)
            self._attach_page_debug(new_page)

        context.on("page", log_page_created)
        self._attach_page_debug(page)
        context.on("requestfailed", log_request_failed)
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

    async def _write_json(self, path: Path, payload: Any) -> None:
        await self._write_text(path, json.dumps(payload, indent=2, ensure_ascii=False))

    async def _ensure_dir(self, path: Path) -> None:
        await asyncio.to_thread(path.mkdir, parents=True, exist_ok=True)

    async def _ensure_parent_dir(self, path: Path) -> None:
        await self._ensure_dir(path.parent)

    async def _project_link_debug_snapshot(self, page: Any) -> list[dict[str, Any]]:
        links = await page.evaluate(
            """
            () => {
              const anchors = Array.from(document.querySelectorAll('a[href*="/g/g-p-"][href$="/project"]'));
              return anchors.map((a, idx) => {
                const href = a.href || a.getAttribute("href") || "";
                const text = (a.innerText || a.textContent || "").replace(/\s+/g, " ").trim();
                const rect = a.getBoundingClientRect();
                const style = getComputedStyle(a);
                return {
                  index: idx,
                  href,
                  text,
                  visible: !!(rect.width && rect.height && style.visibility !== "hidden" && style.display !== "none"),
                  top: rect.top,
                  left: rect.left,
                  width: rect.width,
                  height: rect.height,
                  outer_html: a.outerHTML.slice(0, 800),
                };
              });
            }
            """
        )
        dedup: dict[str, dict[str, Any]] = {}
        for item in links:
            href = str(item.get("href") or "")
            item["project_id"] = self._extract_project_id_from_url(href)
            dedup[href] = item
        return sorted(dedup.values(), key=lambda x: (x.get("top", 0), x.get("left", 0), x.get("text", ""), x.get("href", "")))

    async def _dialog_like_debug_snapshot(self, page: Any) -> list[dict[str, Any]]:
        return await page.evaluate(
            """
            () => {
              const sels = ['[role="dialog"]', '[role="menu"]', '[role="listbox"]', '[data-radix-popper-content-wrapper]', '[data-radix-menu-content]'];
              const out = [];
              for (const sel of sels) {
                for (const el of document.querySelectorAll(sel)) {
                  const rect = el.getBoundingClientRect();
                  if (!(rect.width && rect.height)) continue;
                  out.push({
                    selector: sel,
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute("role"),
                    aria_label: el.getAttribute("aria-label"),
                    top: rect.top,
                    left: rect.left,
                    width: rect.width,
                    height: rect.height,
                    text_preview: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 240),
                    outer_html: el.outerHTML.slice(0, 1500),
                  });
                }
              }
              return out;
            }
            """
        )

    async def _scrollable_debug_snapshot(self, page: Any) -> list[dict[str, Any]]:
        return await page.evaluate(
            """
            () => {
              const nodes = Array.from(document.querySelectorAll('*'));
              const out = [];
              for (const el of nodes) {
                const style = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                const scrollable = el.scrollHeight > el.clientHeight + 20 || el.scrollWidth > el.clientWidth + 20;
                const overflowY = style.overflowY;
                const overflowX = style.overflowX;
                if (!scrollable && !["auto", "scroll"].includes(overflowY) && !["auto", "scroll"].includes(overflowX)) continue;
                out.push({
                  tag: el.tagName.toLowerCase(),
                  id: el.id || null,
                  cls: (el.className && String(el.className)) || null,
                  role: el.getAttribute("role"),
                  aria_label: el.getAttribute("aria-label"),
                  clientHeight: el.clientHeight,
                  scrollHeight: el.scrollHeight,
                  scrollTop: el.scrollTop,
                  clientWidth: el.clientWidth,
                  scrollWidth: el.scrollWidth,
                  top: rect.top,
                  left: rect.left,
                  width: rect.width,
                  height: rect.height,
                  text_preview: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 240),
                  outer_html: el.outerHTML.slice(0, 1000),
                });
              }
              out.sort((a, b) => {
                const diff = (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight);
                if (diff !== 0) return diff;
                return (b.height * b.width) - (a.height * a.width);
              });
              return out.slice(0, 25);
            }
            """
        )

    async def _more_candidate_debug_snapshot(self, page: Any) -> list[dict[str, Any]]:
        return await page.evaluate(
            """
            () => {
              const matches = [];
              const nodes = Array.from(document.querySelectorAll('[data-sidebar-item="true"], button, [role="button"], a, div, span, summary, [tabindex]'));
              for (const el of nodes) {
                const text = (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
                if (!/\bmore\b/i.test(text)) continue;
                const rect = el.getBoundingClientRect();
                if (!(rect.width && rect.height)) continue;
                matches.push({
                  text,
                  tag: el.tagName.toLowerCase(),
                  role: el.getAttribute("role"),
                  aria_label: el.getAttribute("aria-label"),
                  data_sidebar_item: el.getAttribute('data-sidebar-item'),
                  aria_haspopup: el.getAttribute('aria-haspopup'),
                  top: rect.top,
                  left: rect.left,
                  width: rect.width,
                  height: rect.height,
                  outer_html: el.outerHTML.slice(0, 1000),
                });
              }
              matches.sort((a, b) => a.top - b.top || a.left - b.left);
              return matches;
            }
            """
        )

    async def _write_text(self, path: Path, text: str) -> None:
        await self._ensure_parent_dir(path)
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
    conversation_url: Optional[str] = None,
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
    result = await client.ask_question_result(
        prompt=prompt,
        file_path=file_path,
        conversation_url=conversation_url,
        expect_json=expect_json,
    )
    return result["answer"]

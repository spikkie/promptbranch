from __future__ import annotations

import asyncio
import json
import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

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
ASSISTANT_MESSAGE_SELECTOR = '[data-message-author-role="assistant"]'
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
            else await self._wait_and_get_response(page)
        )
        if keep_open and self.config.is_headed:
            await asyncio.to_thread(
                input,
                "Question completed. Press Enter to close the browser... ",
            )
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

    async def _submit_prompt(self, page: Any) -> None:
        submit_candidates = [
            '#composer-submit-button',
            'button[data-testid="send-button"]',
            'button[aria-label="Send prompt"]',
        ]
        submit_wait_timeout_s = 20.0
        poll_interval_ms = 500
        deadline = asyncio.get_running_loop().time() + submit_wait_timeout_s
        attempt = 0
        self._log(
            "submit",
            "attempting to submit prompt",
            wait_timeout_s=submit_wait_timeout_s,
            selectors=submit_candidates,
        )
        while asyncio.get_running_loop().time() < deadline:
            attempt += 1
            for selector in submit_candidates:
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
                last_text = (texts[-1] or "").strip()
                if last_text:
                    return count, last_text
        except Exception:
            pass

        try:
            last = locator.nth(count - 1)
            return count, await self._extract_text_from_locator(last, timeout_ms=1_000)
        except Exception:
            return count, ""

    def _is_project_home_url(self, url: str) -> bool:
        return urlparse(url).path.rstrip("/").endswith("/project")

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
        assistant_count, assistant_text = await self._extract_last_text_from_selector(page, ASSISTANT_MESSAGE_SELECTOR)
        project_conversation_links = await self._extract_project_conversation_links(page)
        context = {
            "url": await self._safe_page_url(page),
            "assistant_count": assistant_count,
            "assistant_text": assistant_text,
            "project_conversation_links": project_conversation_links,
        }
        self._log(
            "response",
            "captured baseline response context",
            url=context["url"],
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
        assistant_count, assistant_text = await self._extract_last_text_from_selector(page, ASSISTANT_MESSAGE_SELECTOR)

        lines = [
            f"timestamp: {self._timestamp()}",
            f"driver: {self.driver_name}",
            f"project_url: {self.config.project_url}",
            f"current_url: {current_url}",
            f"attempt: {attempt}",
            f"elapsed_s: {elapsed_s:.1f}",
            f"assistant_count: {assistant_count}",
            f"assistant_text_length: {len(assistant_text)}",
            f"assistant_preview: {self._preview_text(assistant_text, 1200)}",
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
                f"baseline_assistant_count: {response_context.get('assistant_count')}",
                f"baseline_assistant_text_length: {len(baseline_text)}",
                f"baseline_assistant_preview: {self._preview_text(baseline_text, 400)}",
                f"assistant_text_changed: {assistant_text != baseline_text}",
                f"baseline_project_conversation_link_count: {len(baseline_links)}",
                f"baseline_project_conversation_links: {' | '.join(baseline_links[:10])}",
                f"opened_project_conversation_links: {' | '.join(opened_links[:10])}",
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

        assistant_count, assistant_text = await self._extract_last_text_from_selector(page, ASSISTANT_MESSAGE_SELECTOR)
        parsed = self._extract_json_from_text(assistant_text) if assistant_text else None
        probes.append({
            "selector": ASSISTANT_MESSAGE_SELECTOR,
            "count": assistant_count,
            "visible": bool(assistant_count),
            "text_length": len(assistant_text),
            "parsed": parsed is not None,
            "preview": self._preview_text(assistant_text, 220),
        })
        if assistant_count:
            self._log(
                "response",
                "assistant text fallback probe",
                selector=ASSISTANT_MESSAGE_SELECTOR,
                count=assistant_count,
                text_length=len(assistant_text),
                parsed=parsed is not None,
            )
        if parsed is not None:
            return parsed, ASSISTANT_MESSAGE_SELECTOR, len(assistant_text), probes

        return None, None, 0, probes

    async def _wait_and_get_response(self, page: Any) -> str:
        self._log("response", "waiting for assistant response", selector=ASSISTANT_MESSAGE_SELECTOR, timeout_ms=self.config.response_timeout_ms)
        try:
            await page.locator(ASSISTANT_MESSAGE_SELECTOR).last.wait_for(
                state="visible",
                timeout=self.config.response_timeout_ms,
            )
        except Exception as exc:
            raise ResponseTimeoutError("Timed out waiting for an assistant response") from exc

        assistant_locator = page.locator(ASSISTANT_MESSAGE_SELECTOR)
        assistant_count = await assistant_locator.count()
        assistant = assistant_locator.last
        self._log("response", "assistant response became visible", count=assistant_count)
        try:
            markdown = assistant.locator(".markdown").first
            markdown_count = await markdown.count()
            self._log("response", "markdown probe", selector=".markdown", count=markdown_count)
            if markdown_count:
                text = await markdown.text_content()
                result = (text or "").strip()
                self._log("response", "returning markdown response text", text_length=len(result))
                return result
        except Exception as exc:
            self._log("response", "markdown extraction failed", error=str(exc))

        result = await self._extract_text_from_locator(assistant, timeout_ms=1_500)
        self._log("response", "returning assistant text content", text_length=len(result))
        return result

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
            if payload is not None:
                self._log(
                    "response",
                    "parseable json payload captured",
                    selector=selector,
                    attempt=attempt,
                    elapsed_s=round(elapsed_s, 1),
                    text_length=text_length,
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

            if attempt == 1 or attempt % 15 == 0 or probe_summary != last_probe_summary:
                self._log(
                    "response",
                    "json wait poll",
                    attempt=attempt,
                    elapsed_s=round(elapsed_s, 1),
                    current_url=await self._safe_page_url(page),
                    probe_summary=probe_summary,
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

            await page.wait_for_timeout(1000)

        elapsed_s = asyncio.get_running_loop().time() - start
        await self._maybe_open_new_project_conversation(
            page,
            response_context=response_context,
            attempt=attempt,
            elapsed_s=elapsed_s,
        )
        payload, selector, text_length, probes = await self._try_extract_json_payload(page)
        if self.config.debug:
            await self._save_response_diagnostics(
                page,
                probes=probes,
                response_context=response_context,
                attempt=attempt,
                elapsed_s=elapsed_s,
                include_page_artifacts=True,
            )
        raise ResponseTimeoutError("Timed out waiting for parseable JSON in the assistant response")

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

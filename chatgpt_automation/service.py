from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

from chatgpt_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
)

from .automation import ChatGPTAutomation

logger = logging.getLogger(__name__)


def _mask_email(value: Optional[str]) -> str:
    if not value:
        return "<unset>"
    if "@" not in value:
        return "***"
    local, domain = value.split("@", 1)
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[:2] + "***"
    return f"{masked_local}@{domain}"


@dataclass(slots=True)
class ChatGPTAutomationSettings:
    project_url: str
    email: Optional[str]
    password: Optional[str]
    profile_dir: str
    headless: bool
    use_patchright: bool
    browser_channel: Optional[str] = None
    password_file: Optional[str] = None
    disable_fedcm: bool = True
    filter_no_sandbox: bool = True
    max_retries: int = 2
    retry_backoff_seconds: float = 2.0


class ChatGPTAutomationService:
    """Serialize browser/profile access and add bounded retries.

    This is intentionally conservative: one persistent profile should not be
    driven concurrently by multiple requests.
    """

    def __init__(self, settings: ChatGPTAutomationSettings):
        self.settings = settings
        self._lock = asyncio.Lock()

    def _build_bot(self) -> ChatGPTAutomation:
        logger.debug(
            "Building ChatGPT automation bot with email=%s password_set=%s password_file=%s profile_dir=%s headed=%s driver=%s",
            _mask_email(self.settings.email),
            bool(self.settings.password),
            self.settings.password_file or "<unset>",
            self.settings.profile_dir,
            not self.settings.headless,
            "patchright" if self.settings.use_patchright else "playwright",
        )
        return ChatGPTAutomation(
            project_url=self.settings.project_url,
            email=self.settings.email,
            password=self.settings.password,
            profile_dir=self.settings.profile_dir,
            headless=self.settings.headless,
            use_patchright=self.settings.use_patchright,
            browser_channel=self.settings.browser_channel,
            password_file=self.settings.password_file,
            disable_fedcm=self.settings.disable_fedcm,
            filter_no_sandbox=self.settings.filter_no_sandbox,
        )

    async def run_login_check(self, keep_open: bool = False) -> dict[str, Any]:
        async with self._lock:
            logger.info("Running ChatGPT browser login check")
            return await self._build_bot().run_login_check(keep_open=keep_open)

    async def add_project_source(
        self,
        *,
        source_kind: str,
        value: Optional[str] = None,
        file_path: Optional[str] = None,
        display_name: Optional[str] = None,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        async with self._lock:
            logger.info("Adding ChatGPT project source")
            return await self._build_bot().add_project_source(
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
        async with self._lock:
            logger.info("Removing ChatGPT project source")
            return await self._build_bot().remove_project_source(
                source_name=source_name,
                exact=exact,
                keep_open=keep_open,
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
        max_retries = self.settings.max_retries if retries is None else max(0, retries)

        async with self._lock:
            last_error: Optional[Exception] = None
            for attempt in range(1, max_retries + 2):
                try:
                    logger.info(
                        "Running ChatGPT browser question",
                        extra={
                            "attempt": attempt,
                            "expect_json": expect_json,
                            "file_path": file_path,
                        },
                    )
                    return await self._build_bot().ask_question(
                        prompt=prompt,
                        file_path=file_path,
                        expect_json=expect_json,
                    )
                except (ResponseTimeoutError, BotChallengeError) as exc:
                    last_error = exc
                    logger.warning(
                        "Transient ChatGPT browser failure on attempt %s/%s: %s",
                        attempt,
                        max_retries + 1,
                        exc,
                    )
                    if attempt >= max_retries + 1:
                        break
                    await asyncio.sleep(self.settings.retry_backoff_seconds * attempt)
                except (ManualLoginRequiredError, AuthenticationError):
                    raise
                except Exception as exc:  # pragma: no cover - defensive fallback
                    last_error = exc
                    logger.exception("Unexpected ChatGPT browser failure")
                    if attempt >= max_retries + 1:
                        break
                    await asyncio.sleep(self.settings.retry_backoff_seconds * attempt)

            if last_error is None:
                raise RuntimeError("ChatGPT browser automation failed without an exception")
            raise last_error

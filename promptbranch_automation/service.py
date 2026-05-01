from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    BotChallengeError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
    UnsupportedOperationError,
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
    clear_singleton_locks: bool = False


class ChatGPTAutomationService:
    """Serialize browser/profile access and add bounded retries.

    This is intentionally conservative: one persistent profile should not be
    driven concurrently by multiple requests.
    """

    def __init__(self, settings: ChatGPTAutomationSettings):
        self.settings = settings
        self._lock = asyncio.Lock()
        self._recent_project_chats: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _extract_project_id(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        match = re.search(r"/g/(g-p-[a-z0-9]+)", str(url), re.IGNORECASE)
        return match.group(1).lower() if match else None

    @staticmethod
    def _conversation_id_from_url(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        text = str(url).rstrip("/")
        if "/c/" not in text:
            return None
        return text.split("/c/", 1)[-1].split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]

    def _remember_recent_project_chat(self, conversation_url: Optional[str]) -> None:
        conversation_id = self._conversation_id_from_url(conversation_url)
        project_id = self._extract_project_id(conversation_url) or self._extract_project_id(self.settings.project_url)
        settings_project_id = self._extract_project_id(self.settings.project_url)
        if not conversation_url or not conversation_id or not project_id:
            return
        if settings_project_id and project_id != settings_project_id:
            return
        self._recent_project_chats[conversation_id] = {
            "id": conversation_id,
            "title": "(recent task)",
            "conversation_url": conversation_url,
            "source": "recent_state",
            "project_id": project_id,
            "seen_at": time.time(),
        }

    _INDEXED_TASK_SOURCES = {"snorlax", "dom", "history", "history_detail", "current_page"}
    _LOCAL_TASK_SOURCES = {"recent_state", "current_state"}

    @classmethod
    def _indexed_observation_count(cls, source_counts: dict[str, Any]) -> int:
        total = 0
        for source in cls._INDEXED_TASK_SOURCES:
            try:
                total += int(source_counts.get(source) or 0)
            except (TypeError, ValueError):
                continue
        return total

    @classmethod
    def _indexed_task_count(cls, chats: list[dict[str, Any]]) -> int:
        """Count unique indexed tasks, not duplicate observations per source."""
        indexed_ids: set[str] = set()
        anonymous_indexed_rows = 0
        for item in chats:
            if not isinstance(item, dict):
                continue
            source = str(item.get("source") or "").strip()
            if source in cls._LOCAL_TASK_SOURCES:
                continue
            if source and source not in cls._INDEXED_TASK_SOURCES:
                continue
            task_id = str(item.get("id") or cls._conversation_id_from_url(item.get("conversation_url")) or "").strip()
            if task_id:
                indexed_ids.add(task_id)
            else:
                anonymous_indexed_rows += 1
        return len(indexed_ids) + anonymous_indexed_rows

    @classmethod
    def _chat_visibility_status(cls, source_counts: dict[str, Any], chats: list[dict[str, Any]]) -> str:
        """Classify task-list visibility without treating local memory as indexing."""
        if cls._indexed_task_count(chats) > 0:
            return "indexed"
        try:
            recent_count = int(source_counts.get("recent_state") or 0)
        except (TypeError, ValueError):
            recent_count = 0
        if recent_count > 0 or any(str(item.get("source") or "") == "recent_state" for item in chats):
            return "recent_state_only"
        return "missing"

    def _augment_chat_list_with_recent_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return payload
        project_id = self._extract_project_id(str(payload.get("project_url") or self.settings.project_url))
        raw_chats = payload.get("chats") if isinstance(payload.get("chats"), list) else []
        chats = [dict(item) for item in raw_chats if isinstance(item, dict)]
        known_ids = {str(item.get("id") or self._conversation_id_from_url(item.get("conversation_url")) or "") for item in chats}
        known_urls = {str(item.get("conversation_url") or "").rstrip("/") for item in chats}
        added = 0
        for item in self._recent_project_chats.values():
            if project_id and item.get("project_id") and item.get("project_id") != project_id:
                continue
            conversation_id = str(item.get("id") or "")
            conversation_url = str(item.get("conversation_url") or "").rstrip("/")
            if (conversation_id and conversation_id in known_ids) or (conversation_url and conversation_url in known_urls):
                continue
            chats.append(dict(item))
            if conversation_id:
                known_ids.add(conversation_id)
            if conversation_url:
                known_urls.add(conversation_url)
            added += 1
        source_counts = dict(payload.get("source_counts") or {}) if isinstance(payload.get("source_counts"), dict) else {}
        source_counts["recent_state"] = source_counts.get("recent_state", 0) + added
        augmented = dict(payload)
        augmented["chats"] = chats
        augmented["count"] = len(chats)
        augmented["recent_state_fallback_used"] = bool(added)
        augmented["source_counts"] = source_counts
        augmented["visibility_status"] = self._chat_visibility_status(source_counts, chats)
        augmented["indexed_task_count"] = self._indexed_task_count(chats)
        augmented["indexed_observation_count"] = self._indexed_observation_count(source_counts)
        try:
            augmented["recent_state_count"] = int(source_counts.get("recent_state") or 0)
        except (TypeError, ValueError):
            augmented["recent_state_count"] = 0
        return augmented

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
            clear_singleton_locks=self.settings.clear_singleton_locks,
        )


    async def _with_retries(self, operation_name: str, func):
        max_retries = max(0, self.settings.max_retries)
        last_error: Optional[Exception] = None
        for attempt in range(1, max_retries + 2):
            try:
                return await func()
            except (ResponseTimeoutError, BotChallengeError) as exc:
                last_error = exc
                logger.warning(
                    "Transient ChatGPT browser failure during %s on attempt %s/%s: %s",
                    operation_name,
                    attempt,
                    max_retries + 1,
                    exc,
                )
                if attempt >= max_retries + 1:
                    break
                await asyncio.sleep(self.settings.retry_backoff_seconds * attempt)
            except (ManualLoginRequiredError, UnsupportedOperationError, AuthenticationError, EOFError):
                raise
            except Exception as exc:  # pragma: no cover - defensive fallback
                last_error = exc
                logger.exception("Unexpected ChatGPT browser failure during %s", operation_name)
                if attempt >= max_retries + 1:
                    break
                await asyncio.sleep(self.settings.retry_backoff_seconds * attempt)

        if last_error is None:
            raise RuntimeError(f"{operation_name} failed without an exception")
        raise last_error

    async def list_projects(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        logger.info("Listing ChatGPT projects")
        async with self._lock:
            return await self._with_retries(
                "list_projects",
                lambda: self._build_bot().list_projects(
                    keep_open=keep_open,
                ),
            )

    async def list_project_chats(
        self,
        *,
        keep_open: bool = False,
        include_history_fallback: bool = True,
    ) -> dict[str, Any]:
        logger.info("Listing ChatGPT project chats")
        async with self._lock:
            payload = await self._with_retries(
                "list_project_chats",
                lambda: self._build_bot().list_project_chats(
                    keep_open=keep_open,
                    include_history_fallback=include_history_fallback,
                ),
            )
            return self._augment_chat_list_with_recent_state(payload)

    async def list_project_sources(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        logger.info("Listing ChatGPT project sources")
        async with self._lock:
            return await self._with_retries(
                "list_project_sources",
                lambda: self._build_bot().list_project_sources(
                    keep_open=keep_open,
                ),
            )

    async def get_chat(
        self,
        *,
        conversation_url: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        logger.info("Fetching ChatGPT chat transcript")
        async with self._lock:
            return await self._with_retries(
                "get_chat",
                lambda: self._build_bot().get_chat(
                    conversation_url=conversation_url,
                    keep_open=keep_open,
                ),
            )

    async def debug_project_list(
        self,
        *,
        scroll_rounds: int = 12,
        wait_ms: int = 350,
        manual_pause: bool = False,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        logger.info("Debugging ChatGPT project list locally")
        async with self._lock:
            return await self._with_retries(
                "debug_project_list",
                lambda: self._build_bot().debug_project_list(
                    scroll_rounds=scroll_rounds,
                    wait_ms=wait_ms,
                    manual_pause=manual_pause,
                    keep_open=keep_open,
                ),
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
        logger.info("Debugging ChatGPT project task list locally")
        async with self._lock:
            return await self._with_retries(
                "debug_project_chats",
                lambda: self._build_bot().debug_project_chats(
                    scroll_rounds=scroll_rounds,
                    wait_ms=wait_ms,
                    include_history=include_history,
                    history_max_pages=history_max_pages,
                    history_max_detail_probes=history_max_detail_probes,
                    manual_pause=manual_pause,
                    keep_open=keep_open,
                ),
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
        logger.info("Creating ChatGPT project")
        async with self._lock:
            return await self._with_retries(
                "create_project",
                lambda: self._build_bot().create_project(
                    name=name,
                    icon=icon,
                    color=color,
                    memory_mode=memory_mode,
                    keep_open=keep_open,
                ),
            )

    async def resolve_project(
        self,
        *,
        name: str,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        logger.info("Resolving ChatGPT project by name")
        async with self._lock:
            return await self._with_retries(
                "resolve_project",
                lambda: self._build_bot().resolve_project(
                    name=name,
                    keep_open=keep_open,
                ),
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
        logger.info("Ensuring ChatGPT project exists")
        async with self._lock:
            return await self._with_retries(
                "ensure_project",
                lambda: self._build_bot().ensure_project(
                    name=name,
                    icon=icon,
                    color=color,
                    memory_mode=memory_mode,
                    keep_open=keep_open,
                ),
            )

    async def run_login_check(self, keep_open: bool = False) -> dict[str, Any]:
        async with self._lock:
            logger.info("Running ChatGPT browser login check")
            return await self._build_bot().run_login_check(keep_open=keep_open)

    async def remove_project(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        logger.info("Removing ChatGPT project")
        async with self._lock:
            result = await self._with_retries(
                "remove_project",
                lambda: self._build_bot().remove_project(
                    keep_open=keep_open,
                ),
            )
            self._recent_project_chats.clear()
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
        async with self._lock:
            logger.info("Adding ChatGPT project source")
            return await self._build_bot().add_project_source(
                source_kind=source_kind,
                value=value,
                file_path=file_path,
                display_name=display_name,
                keep_open=keep_open,
                overwrite_existing=overwrite_existing,
            )

    async def discover_project_source_capabilities(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        async with self._lock:
            logger.info("Discovering ChatGPT project source capabilities")
            return await self._build_bot().discover_project_source_capabilities(
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
        result = await self.ask_question_result(
            prompt=prompt,
            file_path=file_path,
            expect_json=expect_json,
            keep_open=keep_open,
            retries=retries,
        )
        return result["answer"]

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
                    result = await self._build_bot().ask_question_result(
                        prompt=prompt,
                        file_path=file_path,
                        conversation_url=conversation_url,
                        expect_json=expect_json,
                        keep_open=keep_open,
                    )
                    if isinstance(result, dict):
                        self._remember_recent_project_chat(result.get("conversation_url"))
                    return result
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
                except (ManualLoginRequiredError, UnsupportedOperationError, AuthenticationError):
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

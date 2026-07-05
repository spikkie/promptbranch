from __future__ import annotations

import asyncio
import fcntl
import logging
import os
import re
import shlex
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from promptbranch_project_delete_safety import (
    project_delete_disabled_result,
    validate_ephemeral_test_project_cleanup_request,
)
from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    AuthChallengeRequiredError,
    BotChallengeError,
    ManualLoginRequiredError,
    BrowserProfileBusyError,
    BrowserContextUnavailableError,
    RateLimitDetectedError,
    ResponseTimeoutError,
    UnsupportedOperationError,
)

from .automation import ChatGPTAutomation

logger = logging.getLogger(__name__)

DEFAULT_BROWSER_PROFILE_QUEUE_WAIT_SECONDS = 600.0



def _split_browser_args(value: Optional[str]) -> tuple[str, ...]:
    text = str(value or "").strip()
    if not text:
        return ()
    try:
        return tuple(shlex.split(text))
    except ValueError:
        return tuple(part for part in text.split() if part)

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


class _SharedProfileAsyncLock:
    """Async-compatible, profile-scoped lock for browser profile ownership.

    The service may create multiple ChatGPTAutomationService instances for
    different project URLs. Those instances can still point at the same
    persistent Chromium profile directory, so an instance-level asyncio.Lock is
    insufficient. This lock serializes browser/profile operations for the same
    resolved profile path inside the current process and also takes an advisory
    flock so a second Promptbranch process does not race the same profile.

    v0.0.278.2 intentionally bounds lock waiting. A queued browser-backed
    request should fail with browser_profile_busy before the outer HTTP client
    reaches its read timeout.
    """

    _locks_guard = threading.Lock()
    _locks: dict[str, threading.Lock] = {}
    _active_operations: dict[str, dict[str, Any]] = {}

    def __init__(
        self,
        profile_dir: str,
        *,
        wait_timeout_seconds: float = 30.0,
        stale_lock_seconds: float = 300.0,
    ):
        self.profile_dir = str(Path(profile_dir).expanduser().resolve())
        self.wait_timeout_seconds = max(0.001, float(wait_timeout_seconds))
        self.stale_lock_seconds = max(0.001, float(stale_lock_seconds))
        self._thread_lock = self._lock_for_profile(self.profile_dir)
        self._lock_file = None
        self._operation_name = "browser_operation"
        self._operation_id: str | None = None
        self._acquired_at = None
        self.last_waited_seconds = 0.0

    @classmethod
    def _lock_for_profile(cls, profile_dir: str) -> threading.Lock:
        with cls._locks_guard:
            lock = cls._locks.get(profile_dir)
            if lock is None:
                lock = threading.Lock()
                cls._locks[profile_dir] = lock
            return lock

    @classmethod
    def _active_operation_for_profile(cls, profile_dir: str) -> dict[str, Any]:
        with cls._locks_guard:
            return dict(cls._active_operations.get(profile_dir) or {})

    @classmethod
    def _set_active_operation(cls, profile_dir: str, operation_name: str, *, operation_id: str, owner: "_SharedProfileAsyncLock") -> None:
        now = time.time()
        task = None
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        with cls._locks_guard:
            cls._active_operations[profile_dir] = {
                "operation_name": operation_name,
                "operation_id": operation_id,
                "pid": os.getpid(),
                "started_at": now,
                "started_monotonic": time.monotonic(),
                "owner": owner,
                "task": task,
                "task_name": task.get_name() if task is not None else None,
            }

    @classmethod
    def _clear_active_operation(cls, profile_dir: str, *, operation_id: str | None = None) -> None:
        with cls._locks_guard:
            if operation_id is None:
                cls._active_operations.pop(profile_dir, None)
                return
            active = cls._active_operations.get(profile_dir)
            if not active or active.get("operation_id") == operation_id:
                cls._active_operations.pop(profile_dir, None)

    @staticmethod
    def _active_task_done(active: dict[str, Any]) -> bool:
        task = active.get("task")
        try:
            return bool(task is not None and task.done())
        except Exception:
            return False

    @staticmethod
    def _active_elapsed_seconds(active: dict[str, Any]) -> float | None:
        started_monotonic = active.get("started_monotonic")
        if started_monotonic is None:
            started_at = active.get("started_at")
            if started_at is None:
                return None
            try:
                return max(0.0, time.time() - float(started_at))
            except (TypeError, ValueError):
                return None
        try:
            return max(0.0, time.monotonic() - float(started_monotonic))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _active_lock_expired(cls, active: dict[str, Any], *, stale_lock_seconds: float) -> bool:
        if not active:
            return False
        if cls._active_task_done(active):
            return True
        elapsed = cls._active_elapsed_seconds(active)
        return bool(elapsed is not None and elapsed >= stale_lock_seconds)

    @classmethod
    def _active_public_payload(cls, active: dict[str, Any], *, stale_lock_seconds: float) -> dict[str, Any]:
        elapsed = cls._active_elapsed_seconds(active)
        return {
            "active_operation": active.get("operation_name"),
            "active_operation_id": active.get("operation_id"),
            "active_pid": active.get("pid"),
            "active_elapsed_seconds": round(elapsed, 3) if elapsed is not None else None,
            "active_task_done": cls._active_task_done(active),
            "active_task_name": active.get("task_name"),
            "stale_lock_seconds": stale_lock_seconds,
            "stale_lock_expired": cls._active_lock_expired(active, stale_lock_seconds=stale_lock_seconds),
        }

    @property
    def lock_path(self) -> Path:
        return Path(self.profile_dir) / ".promptbranch-browser-profile.lock"

    def operation(
        self,
        operation_name: str,
        *,
        wait_timeout_seconds: float | None = None,
    ) -> "_SharedProfileAsyncLockLease":
        return _SharedProfileAsyncLockLease(self, operation_name, wait_timeout_seconds=wait_timeout_seconds)

    @classmethod
    def status_for_profile(cls, profile_dir: str, *, stale_lock_seconds: float = 300.0) -> dict[str, Any]:
        resolved = str(Path(profile_dir).expanduser().resolve())
        active = cls._active_operation_for_profile(resolved)
        lock_path = Path(resolved) / ".promptbranch-browser-profile.lock"
        lock_file_exists = lock_path.exists()
        external_lock_held = False
        lock_file_payload: dict[str, str] = {}
        if lock_file_exists:
            try:
                for line in lock_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if "=" in line:
                        key, value = line.split("=", 1)
                        lock_file_payload[key.strip()] = value.strip()
            except OSError:
                lock_file_payload = {}
            try:
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                with lock_path.open("a+", encoding="utf-8") as handle:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        external_lock_held = True
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                external_lock_held = False
        active_public = cls._active_public_payload(active, stale_lock_seconds=stale_lock_seconds) if active else {}
        owner_active = bool(active) or external_lock_held
        active_operation = active_public.get("active_operation") if owner_active else None
        active_pid = active_public.get("active_pid") if owner_active else None
        if owner_active and not active_operation:
            active_operation = lock_file_payload.get("operation")
        if owner_active and not active_pid:
            active_pid = lock_file_payload.get("pid")
        stale_lock_file = bool(lock_file_payload and not owner_active)
        stale_lock_expired = bool(active_public.get("stale_lock_expired")) if active else False
        return {
            "ok": True,
            "action": "browser_status",
            "status": "busy" if owner_active else "available",
            "profile_dir": resolved,
            "lock_path": str(lock_path),
            "owner_active": owner_active,
            "active_operation": active_operation,
            "active_operation_id": active_public.get("active_operation_id"),
            "active_pid": active_pid,
            "active_elapsed_seconds": active_public.get("active_elapsed_seconds") if owner_active else None,
            "active_task_done": active_public.get("active_task_done") if owner_active else None,
            "active_task_name": active_public.get("active_task_name") if owner_active else None,
            "stale_lock_seconds": stale_lock_seconds,
            "stale_lock_expired": stale_lock_expired if owner_active else False,
            "stale_lock_recoverable": bool(active and stale_lock_expired),
            "last_operation": lock_file_payload.get("operation") if stale_lock_file else None,
            "last_pid": lock_file_payload.get("pid") if stale_lock_file else None,
            "last_acquired_at": lock_file_payload.get("acquired_at") if stale_lock_file else None,
            "stale_lock_file": stale_lock_file,
            "lock_file_exists": lock_file_exists,
            "external_lock_held": external_lock_held,
            "lock_file": lock_file_payload,
            "scheduler_model": "single_owner_profile_wait_queue",
            "queue_enabled": True,
            "queue_mode": "bounded_wait_for_single_service_profile",
            "default_queue_wait_timeout_seconds": DEFAULT_BROWSER_PROFILE_QUEUE_WAIT_SECONDS,
        }

    async def __aenter__(self) -> "_SharedProfileAsyncLock":
        return await self._acquire("browser_operation")

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._release()

    async def _acquire(self, operation_name: str, wait_timeout_seconds: float | None = None) -> "_SharedProfileAsyncLock":
        self._operation_name = str(operation_name or "browser_operation")
        wait_timeout = self.wait_timeout_seconds if wait_timeout_seconds is None else max(0.001, float(wait_timeout_seconds))
        started = time.monotonic()
        acquired = await asyncio.to_thread(self._thread_lock.acquire, True, wait_timeout)
        waited = time.monotonic() - started
        self.last_waited_seconds = round(waited, 3)
        stale_recovery_result: dict[str, Any] | None = None
        if not acquired:
            active = self._active_operation_for_profile(self.profile_dir)
            stale_recovery_result = await self._recover_stale_active_operation(
                active,
                reason="thread_lock_wait_timeout",
            )
            if stale_recovery_result.get("expired"):
                reacquire_started = time.monotonic()
                acquired = await asyncio.to_thread(self._thread_lock.acquire, True, 0.001)
                waited += time.monotonic() - reacquire_started
                self.last_waited_seconds = round(waited, 3)

        if not acquired:
            active = self._active_operation_for_profile(self.profile_dir)
            active_payload = self._active_public_payload(active, stale_lock_seconds=self.stale_lock_seconds) if active else {}
            active_operation = active_payload.get("active_operation") or "unknown_browser_operation"
            raise BrowserProfileBusyError(
                f"browser profile is busy; waited {waited:.1f}s for {self._operation_name} while {active_operation} owns the profile",
                operation_name=self._operation_name,
                active_operation=active_operation,
                active_operation_id=active_payload.get("active_operation_id"),
                active_elapsed_seconds=active_payload.get("active_elapsed_seconds"),
                stale_lock_seconds=self.stale_lock_seconds,
                stale_lock_expired=active_payload.get("stale_lock_expired"),
                stale_lock_recovery_attempted=bool(stale_recovery_result),
                stale_lock_recovery_result=stale_recovery_result,
                waited_seconds=round(waited, 3),
                retry_after_seconds=max(1.0, wait_timeout),
                profile_dir=self.profile_dir,
                queue_wait_seconds=round(waited, 3),
                queue_timeout_seconds=wait_timeout,
                scheduler_path="shared_profile_async_lock",
                bypass_detected=False,
            )
        try:
            Path(self.profile_dir).mkdir(parents=True, exist_ok=True)
            lock_path = self.lock_path
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._lock_file = lock_path.open("a+", encoding="utf-8")
            try:
                await asyncio.to_thread(fcntl.flock, self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                active = self._active_operation_for_profile(self.profile_dir)
                active_payload = self._active_public_payload(active, stale_lock_seconds=self.stale_lock_seconds) if active else {}
                active_operation = active_payload.get("active_operation") or "external_promptbranch_process"
                raise BrowserProfileBusyError(
                    f"browser profile is locked by another process for {active_operation}",
                    operation_name=self._operation_name,
                    active_operation=active_operation,
                    active_operation_id=active_payload.get("active_operation_id"),
                    active_elapsed_seconds=active_payload.get("active_elapsed_seconds"),
                    stale_lock_seconds=self.stale_lock_seconds,
                    stale_lock_expired=active_payload.get("stale_lock_expired"),
                    stale_lock_recovery_attempted=bool(stale_recovery_result),
                    stale_lock_recovery_result=stale_recovery_result,
                    waited_seconds=round(waited, 3),
                    retry_after_seconds=max(1.0, wait_timeout),
                    profile_dir=self.profile_dir,
                    queue_wait_seconds=round(waited, 3),
                    queue_timeout_seconds=wait_timeout,
                    scheduler_path="shared_profile_async_lock",
                    bypass_detected=False,
                ) from exc
            self._acquired_at = time.time()
            self._operation_id = uuid.uuid4().hex
            self._set_active_operation(
                self.profile_dir,
                self._operation_name,
                operation_id=self._operation_id,
                owner=self,
            )
            self._lock_file.seek(0)
            self._lock_file.truncate()
            self._lock_file.write(f"pid={os.getpid()}\n")
            self._lock_file.write(f"operation={self._operation_name}\n")
            self._lock_file.write(f"operation_id={self._operation_id}\n")
            self._lock_file.write(f"profile_dir={self.profile_dir}\n")
            self._lock_file.write(f"acquired_at={self._acquired_at}\n")
            self._lock_file.write(f"stale_lock_seconds={self.stale_lock_seconds}\n")
            self._lock_file.flush()
            return self
        except Exception:
            self._release_file_lock_handle()
            self._release_thread_lock()
            self._operation_id = None
            raise

    async def _recover_stale_active_operation(self, active: dict[str, Any], *, reason: str) -> dict[str, Any]:
        if not active:
            return {"attempted": False, "reason": "no_active_operation"}
        active_payload = self._active_public_payload(active, stale_lock_seconds=self.stale_lock_seconds)
        if not active_payload.get("stale_lock_expired"):
            return {"attempted": False, "reason": "active_operation_not_stale", **active_payload}
        owner = active.get("owner")
        operation_id = active.get("operation_id")
        if not isinstance(owner, _SharedProfileAsyncLock) or not operation_id:
            return {"attempted": False, "reason": "active_owner_unavailable", **active_payload}
        return await owner._force_release_stale_operation(str(operation_id), reason=reason, active_payload=active_payload)

    async def _force_release_stale_operation(self, operation_id: str, *, reason: str, active_payload: dict[str, Any]) -> dict[str, Any]:
        active = self._active_operation_for_profile(self.profile_dir)
        if active.get("operation_id") != operation_id:
            return {"attempted": True, "expired": False, "reason": "active_operation_changed", **active_payload}
        if not self._active_lock_expired(active, stale_lock_seconds=self.stale_lock_seconds):
            return {"attempted": True, "expired": False, "reason": "active_operation_no_longer_stale", **active_payload}
        self._release_file_lock_handle()
        self._clear_active_operation(self.profile_dir, operation_id=operation_id)
        self._release_thread_lock()
        if self._operation_id == operation_id:
            self._operation_id = None
            self._acquired_at = None
        return {
            "attempted": True,
            "expired": True,
            "reason": reason,
            "recovery_action": "force_released_stale_profile_lock",
            **active_payload,
        }

    def _release_file_lock_handle(self) -> None:
        if self._lock_file is None:
            return
        handle = self._lock_file
        self._lock_file = None
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            handle.close()
        except OSError:
            pass

    async def _release(self) -> None:
        operation_id = self._operation_id
        try:
            if self._lock_file is not None:
                await asyncio.to_thread(fcntl.flock, self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
                self._lock_file = None
        finally:
            self._clear_active_operation(self.profile_dir, operation_id=operation_id)
            self._operation_id = None
            self._acquired_at = None
            self._release_thread_lock()

    def _release_thread_lock(self) -> None:
        try:
            self._thread_lock.release()
        except RuntimeError:
            pass


class _SharedProfileAsyncLockLease:
    def __init__(self, parent: _SharedProfileAsyncLock, operation_name: str, *, wait_timeout_seconds: float | None = None):
        self.parent = parent
        self.operation_name = operation_name
        self.wait_timeout_seconds = wait_timeout_seconds

    async def __aenter__(self) -> _SharedProfileAsyncLock:
        return await self.parent._acquire(self.operation_name, wait_timeout_seconds=self.wait_timeout_seconds)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.parent._release()


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
    disable_fedcm: bool = False
    fail_fast_on_challenge: bool = False
    filter_no_sandbox: bool = True
    max_retries: int = 2
    retry_backoff_seconds: float = 2.0
    clear_singleton_locks: bool = False
    profile_lock_wait_seconds: float = DEFAULT_BROWSER_PROFILE_QUEUE_WAIT_SECONDS
    profile_stale_lock_seconds: float = 300.0
    slow_mo_ms: int = 0
    debug: bool = False
    debug_artifact_dir: str = "debug_artifacts"
    dom_diagnostic_mode: str = "light"
    pause_before_fill: bool = False
    pause_after_fill: bool = False
    pause_before_submit: bool = False
    extra_browser_args: tuple[str, ...] = ()


class ChatGPTAutomationService:
    """Serialize browser/profile access and add bounded retries.

    This is intentionally conservative: one persistent profile should not be
    driven concurrently by multiple requests.
    """

    def __init__(self, settings: ChatGPTAutomationSettings):
        self.settings = settings
        self._lock = _SharedProfileAsyncLock(
            settings.profile_dir,
            wait_timeout_seconds=settings.profile_lock_wait_seconds,
            stale_lock_seconds=settings.profile_stale_lock_seconds,
        )
        self._recent_project_chats: dict[str, dict[str, Any]] = {}
        self._recent_project_sources: dict[tuple[str, str, str], dict[str, Any]] = {}

    def browser_status(self) -> dict[str, Any]:
        return _SharedProfileAsyncLock.status_for_profile(
            self.settings.profile_dir,
            stale_lock_seconds=self.settings.profile_stale_lock_seconds,
        )

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

    @staticmethod
    def _normalize_source_identity(value: Optional[str]) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        return text.lower()

    @classmethod
    def _file_source_memory_names(cls, *, file_path: Optional[str], display_name: Optional[str]) -> list[str]:
        names: list[str] = []

        def add(value: Optional[str]) -> None:
            normalized = cls._normalize_source_identity(value)
            if normalized and normalized not in names:
                names.append(normalized)

        if display_name:
            add(display_name)
        if file_path:
            try:
                add(Path(file_path).name)
            except TypeError:
                pass
        return names

    def _project_source_scope(self, project_url: Optional[str] = None) -> str:
        project_id = self._extract_project_id(project_url) or self._extract_project_id(self.settings.project_url)
        if project_id:
            return project_id
        return str(project_url or self.settings.project_url or "").rstrip("/").lower()

    def _project_source_memory_keys(
        self,
        *,
        source_kind: str,
        file_path: Optional[str],
        display_name: Optional[str],
        project_url: Optional[str] = None,
    ) -> list[tuple[str, str, str]]:
        normalized_kind = str(source_kind or "").strip().lower()
        if normalized_kind != "file":
            return []
        scope = self._project_source_scope(project_url)
        return [(scope, normalized_kind, name) for name in self._file_source_memory_names(file_path=file_path, display_name=display_name)]

    def _lookup_recent_project_source(
        self,
        *,
        source_kind: str,
        file_path: Optional[str],
        display_name: Optional[str],
        project_url: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        for key in self._project_source_memory_keys(
            source_kind=source_kind,
            file_path=file_path,
            display_name=display_name,
            project_url=project_url,
        ):
            remembered = self._recent_project_sources.get(key)
            if remembered:
                return dict(remembered)
        return None

    @staticmethod
    def _clean_file_source_display_name(value: Optional[str]) -> Optional[str]:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            return None
        markers = (
            " File contents may not be accessible",
            " Document",
        )
        for marker in markers:
            if text.endswith(marker):
                text = text[: -len(marker)].strip()
        if not text:
            return None
        try:
            return Path(text).name or text
        except Exception:
            return text

    def _remembered_file_source_exact_name(
        self,
        remembered_source: Optional[dict[str, Any]],
        *,
        file_path: Optional[str],
        display_name: Optional[str],
    ) -> Optional[str]:
        # The local file path/display name is the safest exact selector because it
        # comes from the operator's current upload request, not from stale UI card
        # text. Do not strip suffixes such as " Document" from these request-side
        # values because they may be part of a legitimate filename.
        for request_value in (Path(file_path).name if file_path else None, display_name):
            text = re.sub(r"\s+", " ", str(request_value or "")).strip()
            if not text:
                continue
            try:
                return Path(text).name or text
            except Exception:
                return text

        candidates: list[Optional[str]] = []
        if isinstance(remembered_source, dict):
            candidates.extend([
                remembered_source.get("source_match_requested"),
                remembered_source.get("file_basename"),
                remembered_source.get("display_name"),
                remembered_source.get("source_name"),
                remembered_source.get("source_match"),
            ])
            raw_candidates = remembered_source.get("source_match_candidates")
            if isinstance(raw_candidates, list):
                candidates.extend(str(value) for value in raw_candidates if value)
        for candidate in candidates:
            clean = self._clean_file_source_display_name(candidate)
            if clean:
                return clean
        return None

    def _remember_verified_project_source(
        self,
        result: dict[str, Any],
        *,
        source_kind: str,
        file_path: Optional[str],
        display_name: Optional[str],
    ) -> None:
        normalized_kind = str(source_kind or "").strip().lower()
        if normalized_kind != "file":
            return
        if not isinstance(result, dict) or not result.get("ok") or not result.get("persistence_verified"):
            return
        source_name = self._remembered_file_source_exact_name(
            {
                "source_match": result.get("source_match"),
                "source_match_requested": result.get("source_match_requested"),
                "source_match_candidates": result.get("source_match_candidates"),
            },
            file_path=file_path,
            display_name=display_name,
        )
        if not source_name:
            return
        project_url = result.get("project_url") or self.settings.project_url
        record = {
            "source_name": source_name,
            "source_match": result.get("source_match"),
            "source_match_requested": result.get("source_match_requested"),
            "source_match_candidates": result.get("source_match_candidates"),
            "project_url": project_url,
            "source_kind": normalized_kind,
            "file_basename": Path(file_path).name if file_path else None,
            "display_name": display_name,
            "source": "remembered_verified_before_state",
            "seen_at": time.time(),
        }
        for key in self._project_source_memory_keys(
            source_kind=normalized_kind,
            file_path=file_path,
            display_name=display_name,
            project_url=project_url,
        ):
            self._recent_project_sources[key] = dict(record)

    def _forget_recent_project_source(
        self,
        *,
        source_kind: str,
        file_path: Optional[str],
        display_name: Optional[str],
        project_url: Optional[str] = None,
    ) -> None:
        for key in self._project_source_memory_keys(
            source_kind=source_kind,
            file_path=file_path,
            display_name=display_name,
            project_url=project_url,
        ):
            self._recent_project_sources.pop(key, None)

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
            fail_fast_on_challenge=self.settings.fail_fast_on_challenge,
            filter_no_sandbox=self.settings.filter_no_sandbox,
            clear_singleton_locks=self.settings.clear_singleton_locks,
            slow_mo_ms=self.settings.slow_mo_ms,
            debug=self.settings.debug,
            debug_artifact_dir=self.settings.debug_artifact_dir,
            dom_diagnostic_mode=self.settings.dom_diagnostic_mode,
            pause_before_fill=self.settings.pause_before_fill,
            pause_after_fill=self.settings.pause_after_fill,
            pause_before_submit=self.settings.pause_before_submit,
            extra_browser_args=self.settings.extra_browser_args,
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
            except RateLimitDetectedError:
                # Guardrail/rate-limit responses are not transient browser
                # glitches. The browser client has already persisted cooldown
                # state; retrying here would make the restriction worse.
                raise
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
        async with self._lock.operation("list_projects"):
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
        async with self._lock.operation("list_project_chats"):
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
        async with self._lock.operation("list_project_sources"):
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
        async with self._lock.operation("get_chat"):
            return await self._with_retries(
                "get_chat",
                lambda: self._build_bot().get_chat(
                    conversation_url=conversation_url,
                    keep_open=keep_open,
                ),
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
        logger.info("Downloading ChatGPT artifact through browser session")
        async with self._lock.operation("download_chat_artifact"):
            return await self._with_retries(
                "download_chat_artifact",
                lambda: self._build_bot().download_chat_artifact(
                    conversation_url=conversation_url,
                    artifact_url=artifact_url,
                    filename=filename,
                    target_path=target_path,
                    timeout_seconds=timeout_seconds,
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
        async with self._lock.operation("debug_project_list"):
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
        async with self._lock.operation("debug_project_chats"):
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

    async def debug_rate_limit(
        self,
        *,
        keep_open: bool = False,
        probe_backend: bool = False,
        wait_ms: int = 750,
    ) -> dict[str, Any]:
        logger.info("Debugging ChatGPT rate-limit state locally")
        async with self._lock.operation("debug_rate_limit"):
            return await self._with_retries(
                "debug_rate_limit",
                lambda: self._build_bot().debug_rate_limit(
                    keep_open=keep_open,
                    probe_backend=probe_backend,
                    wait_ms=wait_ms,
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
        async with self._lock.operation("create_project"):
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
        async with self._lock.operation("resolve_project"):
            return await self._with_retries(
                "resolve_project",
                lambda: self._build_bot().resolve_project(
                    name=name,
                    keep_open=keep_open,
                ),
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
        logger.info("Running release-live continuous bootstrap and ask")
        async with self._lock.operation("release_live_continuous"):
            return await self._build_bot().release_live_bootstrap_and_ask(
                project_name=project_name,
                bootstrap_prompt=bootstrap_prompt,
                ask_prompt=ask_prompt,
                icon=icon,
                color=color,
                memory_mode=memory_mode,
                service_timeout_seconds=service_timeout_seconds,
                warmup_conversation_url=warmup_conversation_url,
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
        async with self._lock.operation("ensure_project"):
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
        async with self._lock.operation("login_check"):
            logger.info("Running ChatGPT browser login check")
            return await self._build_bot().run_login_check(keep_open=keep_open)

    async def run_passive_auth_readiness(self, keep_open: bool = False) -> dict[str, Any]:
        async with self._lock.operation("auth_readiness"):
            logger.info("Running passive ChatGPT browser auth readiness check")
            return await self._build_bot().run_passive_auth_readiness(keep_open=keep_open)

    async def auth_readiness_session_status(self) -> dict[str, Any]:
        async with self._lock.operation("auth_readiness_session_status"):
            logger.info("Inspecting held passive ChatGPT browser auth readiness session")
            return await self._build_bot().auth_readiness_session_status()

    async def remove_project(
        self,
        *,
        keep_open: bool = False,
        project_name: Optional[str] = None,
        profile_lock_wait_seconds: float | None = None,
        allow_ephemeral_test_cleanup: bool = False,
        created_project_url: Optional[str] = None,
        created_project_name: Optional[str] = None,
        created_project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        validation = validate_ephemeral_test_project_cleanup_request(
            allow_ephemeral_test_cleanup=allow_ephemeral_test_cleanup,
            project_url=self.settings.project_url,
            project_name=project_name,
            created_project_url=created_project_url,
            created_project_name=created_project_name,
            created_project_id=created_project_id,
        )
        logger.warning("Project deletion requested but blocked by immutable delete safety freeze")
        return project_delete_disabled_result(
            project_url=self.settings.project_url,
            project_name=project_name,
            blocked_at_layer="automation_service",
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
        profile_lock_wait_seconds: float | None = None,
    ) -> dict[str, Any]:
        async with self._lock.operation("add_project_source", wait_timeout_seconds=profile_lock_wait_seconds):
            logger.info("Adding ChatGPT project source")
            normalized_kind = str(source_kind or "").strip().lower()
            remembered_source: Optional[dict[str, Any]] = None
            remembered_remove_result: Optional[dict[str, Any]] = None
            bot = self._build_bot()

            if normalized_kind == "file" and overwrite_existing:
                remembered_source = self._lookup_recent_project_source(
                    source_kind=normalized_kind,
                    file_path=file_path,
                    display_name=display_name,
                )
                if remembered_source:
                    source_name = self._remembered_file_source_exact_name(
                        remembered_source,
                        file_path=file_path,
                        display_name=display_name,
                    )
                    if source_name:
                        logger.info(
                            "Removing remembered verified ChatGPT project file source before overwrite using exact source name: %s",
                            source_name,
                        )
                        try:
                            remembered_remove_result = await bot.remove_project_source(
                                source_name=source_name,
                                exact=True,
                                keep_open=False,
                            )
                        except ResponseTimeoutError as exc:
                            self._forget_recent_project_source(
                                source_kind=normalized_kind,
                                file_path=file_path,
                                display_name=display_name,
                            )
                            return {
                                "ok": False,
                                "action": "add",
                                "status": "remembered_overwrite_remove_failed",
                                "source_kind": normalized_kind,
                                "source_match": remembered_source.get("source_match") or source_name,
                                "source_match_requested": remembered_source.get("source_match_requested") or source_name,
                                "source_match_candidates": remembered_source.get("source_match_candidates"),
                                "persistence_verified": False,
                                "already_exists": True,
                                "added": False,
                                "overwritten": False,
                                "removed_existing": False,
                                "overwrite_classification_source": "remembered_verified_before_state",
                                "overwrite_source_name": source_name,
                                "overwrite_remove_error": str(exc),
                                "operator_review_required": True,
                            }
                        if not (isinstance(remembered_remove_result, dict) and remembered_remove_result.get("ok")):
                            self._forget_recent_project_source(
                                source_kind=normalized_kind,
                                file_path=file_path,
                                display_name=display_name,
                            )
                            return {
                                "ok": False,
                                "action": "add",
                                "status": "remembered_overwrite_remove_not_verified",
                                "source_kind": normalized_kind,
                                "source_match": remembered_source.get("source_match") or source_name,
                                "source_match_requested": remembered_source.get("source_match_requested") or source_name,
                                "source_match_candidates": remembered_source.get("source_match_candidates"),
                                "persistence_verified": False,
                                "already_exists": True,
                                "added": False,
                                "overwritten": False,
                                "removed_existing": False,
                                "overwrite_classification_source": "remembered_verified_before_state",
                                "overwrite_source_name": source_name,
                                "overwrite_remove_result": remembered_remove_result,
                                "operator_review_required": True,
                            }

            result = await bot.add_project_source(
                source_kind=source_kind,
                value=value,
                file_path=file_path,
                display_name=display_name,
                keep_open=keep_open,
                overwrite_existing=overwrite_existing,
            )

            if remembered_remove_result is not None and isinstance(result, dict) and result.get("ok") and result.get("persistence_verified"):
                result = dict(result)
                result["already_exists"] = True
                result["overwritten"] = True
                result["removed_existing"] = True
                result["overwrite_classification_source"] = "remembered_verified_before_state"
                result["remembered_source"] = remembered_source
                result["remembered_overwrite_remove_result"] = remembered_remove_result

            if isinstance(result, dict) and result.get("ok") and result.get("persistence_verified"):
                self._remember_verified_project_source(
                    result,
                    source_kind=source_kind,
                    file_path=file_path,
                    display_name=display_name,
                )
            elif normalized_kind == "file":
                self._forget_recent_project_source(
                    source_kind=normalized_kind,
                    file_path=file_path,
                    display_name=display_name,
                )
            return result

    async def discover_project_source_capabilities(
        self,
        *,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        async with self._lock.operation("discover_project_source_capabilities"):
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
        profile_lock_wait_seconds: float | None = None,
    ) -> dict[str, Any]:
        async with self._lock.operation("remove_project_source", wait_timeout_seconds=profile_lock_wait_seconds):
            logger.info("Removing ChatGPT project source")
            result = await self._build_bot().remove_project_source(
                source_name=source_name,
                exact=exact,
                keep_open=keep_open,
            )
            if isinstance(result, dict) and result.get("ok"):
                normalized_name = self._normalize_source_identity(source_name)
                for key, remembered in list(self._recent_project_sources.items()):
                    remembered_names = {
                        self._normalize_source_identity(remembered.get("source_name")),
                        self._normalize_source_identity(remembered.get("source_match")),
                        self._normalize_source_identity(remembered.get("source_match_requested")),
                    }
                    if normalized_name and normalized_name in remembered_names:
                        self._recent_project_sources.pop(key, None)
            return result

    async def ask_question(
        self,
        *,
        prompt: str,
        file_path: Optional[str] = None,
        attachment_paths: Optional[list[str]] = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
        service_timeout_seconds: Optional[float] = None,
        prefer_button_submit: bool = False,
    ) -> Any:
        result = await self.ask_question_result(
            prompt=prompt,
            file_path=file_path,
            attachment_paths=attachment_paths,
            expect_json=expect_json,
            keep_open=keep_open,
            retries=retries,
            service_timeout_seconds=service_timeout_seconds,
            prefer_button_submit=prefer_button_submit,
        )
        return result["answer"]

    async def ask_question_result(
        self,
        *,
        prompt: str,
        file_path: Optional[str] = None,
        attachment_paths: Optional[list[str]] = None,
        conversation_url: str | None = None,
        expect_json: bool = False,
        keep_open: bool = False,
        retries: Optional[int] = None,
        service_timeout_seconds: Optional[float] = None,
        prefer_button_submit: bool = False,
    ) -> dict[str, Any]:
        max_retries = self.settings.max_retries if retries is None else max(0, retries)

        async with self._lock.operation("ask_question") as profile_lock:
            last_error: Optional[Exception] = None
            for attempt in range(1, max_retries + 2):
                try:
                    logger.info(
                        "Running ChatGPT browser question",
                        extra={
                            "attempt": attempt,
                            "expect_json": expect_json,
                            "file_path": file_path,
                            "attachment_count": len(attachment_paths or []),
                            "prefer_button_submit": prefer_button_submit,
                        },
                    )
                    result = await self._build_bot().ask_question_result(
                        prompt=prompt,
                        file_path=file_path,
                        attachment_paths=attachment_paths,
                        conversation_url=conversation_url,
                        expect_json=expect_json,
                        keep_open=keep_open,
                        service_timeout_seconds=service_timeout_seconds,
                        prefer_button_submit=prefer_button_submit,
                    )
                    if isinstance(result, dict):
                        timings = result.setdefault("ask_phase_timings", {})
                        if isinstance(timings, dict):
                            timings.setdefault("lock_wait_seconds", getattr(profile_lock, "last_waited_seconds", 0.0))
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
                except BrowserContextUnavailableError as exc:
                    logger.warning("ChatGPT browser launch failed: %s", exc)
                    payload = exc.to_payload()
                    payload.setdefault("action", "ask")
                    payload.setdefault("answer", None)
                    payload.setdefault("answer_text", "")
                    payload.setdefault("answer_text_length", 0)
                    payload.setdefault("partial_result", True)
                    payload.setdefault("conversation_url", conversation_url or self.settings.project_url)
                    payload.setdefault("submit_evidence", None)
                    payload.setdefault("ask_phase_timings", {})
                    timings = payload.get("ask_phase_timings")
                    if isinstance(timings, dict):
                        timings.setdefault("lock_wait_seconds", getattr(profile_lock, "last_waited_seconds", 0.0))
                        timings.setdefault("submit_method", None)
                    return payload
                except AuthChallengeRequiredError as exc:
                    logger.warning("ChatGPT authentication challenge required: %s", exc)
                    payload = exc.to_payload()
                    payload.setdefault("action", "ask")
                    payload.setdefault("answer", None)
                    payload.setdefault("answer_text", "")
                    payload.setdefault("answer_text_length", 0)
                    payload.setdefault("partial_result", True)
                    payload.setdefault("conversation_url", conversation_url or self.settings.project_url)
                    payload.setdefault("submit_evidence", None)
                    payload.setdefault("ask_phase_timings", {})
                    timings = payload.get("ask_phase_timings")
                    if isinstance(timings, dict):
                        timings.setdefault("lock_wait_seconds", getattr(profile_lock, "last_waited_seconds", 0.0))
                        timings.setdefault("submit_method", None)
                    return payload
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

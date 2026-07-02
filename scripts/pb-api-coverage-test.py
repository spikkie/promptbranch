#!/usr/bin/env python3
"""Promptbranch container API coverage smoke runner.

This runner is intentionally conservative by default:
- status/read-only endpoints are exercised directly;
- browser-owning endpoints are exercised sequentially;
- destructive endpoints are recorded as skipped or guard-tested;
- Project Source mutation only runs with --allow-source-add and --source-file.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 300.0


@dataclass
class Step:
    name: str
    method: str
    path: str
    category: str
    status: str
    ok: bool
    expected_statuses: list[int] = field(default_factory=list)
    http_status: int | None = None
    elapsed_seconds: float | None = None
    url: str | None = None
    error: str | None = None
    skip_reason: str | None = None
    classification: str | None = None
    response_summary: dict[str, Any] | None = None


def _json_loads_maybe(data: bytes) -> Any:
    text = data.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_text": text[:4000], "raw_text_length": len(text)}


def _payload_text(payload: Any) -> str:
    try:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
    except Exception:
        return repr(payload)


def _nested_get(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        if key in payload:
            return payload.get(key)
        detail = payload.get("detail")
        if isinstance(detail, dict) and key in detail:
            return detail.get(key)
    return None


def _diagnostic_text(payload: Any | None, error: str | None) -> str:
    parts: list[str] = []
    if error:
        parts.append(str(error))
    if isinstance(payload, dict):
        for key in ("error", "detail", "status", "reason", "message"):
            value = payload.get(key)
            if isinstance(value, dict):
                for nested_key in ("error", "detail", "status", "reason", "message"):
                    nested_value = value.get(nested_key)
                    if isinstance(nested_value, (str, int, float, bool)):
                        parts.append(str(nested_value))
            elif isinstance(value, (str, int, float, bool)):
                parts.append(str(value))
    elif payload is not None:
        parts.append(_payload_text(payload))
    return " ".join(parts)


def _classify_response(status: int | None, payload: Any | None, error: str | None) -> str | None:
    """Classify only real endpoint conditions, not incidental response text.

    v0.1.103.10.20 attached classifications by scanning the entire JSON
    payload. That produced false labels when successful responses contained
    words like ``challenge_detected=false``, ``status=clear``, or historical
    conversation text mentioning profile contention.  Keep classification tied
    to explicit top-level/detail status fields and actual error diagnostics.
    """
    diagnostic = _diagnostic_text(payload, error)
    diagnostic_lower = diagnostic.lower()
    payload_ok = _nested_get(payload, "ok")
    payload_status = str(_nested_get(payload, "status") or "").strip().lower()
    challenge_detected = _nested_get(payload, "challenge_detected") is True
    release_blocking = _nested_get(payload, "release_blocking") is True
    rate_limited_flag = _nested_get(payload, "rate_limited") is True
    http_failure = status is None or int(status) >= 400

    if "browser_context_unavailable_held_auth_session_active" in diagnostic:
        return "browser_profile_busy"
    if payload_status == "browser_context_unavailable_held_auth_session_active":
        return "browser_profile_busy"

    if "project_source_mutation_gate_closed" in diagnostic or payload_status == "project_source_mutation_gate_closed":
        return "project_source_mutation_gate_closed"

    rate_limited_statuses = {"rate_limited", "conversation_history_rate_limit", "too_many_requests"}
    if rate_limited_flag or payload_status in rate_limited_statuses:
        return "rate_limited"
    if http_failure and ("too many requests" in diagnostic_lower or "conversation_history_rate_limit" in diagnostic_lower):
        return "rate_limited"

    if challenge_detected:
        return "auth_challenge_or_cloudflare"
    challenge_status_markers = ("cloudflare", "challenge", "auth_challenge")
    if release_blocking and any(marker in payload_status for marker in challenge_status_markers):
        return "auth_challenge_or_cloudflare"
    if http_failure and ("cloudflare" in diagnostic_lower or "challenge_detected" in diagnostic_lower):
        return "auth_challenge_or_cloudflare"

    if payload_ok is False and release_blocking and any(marker in diagnostic_lower for marker in challenge_status_markers):
        return "auth_challenge_or_cloudflare"

    return None




def _payload_bool(payload: Any | None, key: str) -> bool | None:
    value = _nested_get(payload, key)
    if isinstance(value, bool):
        return value
    return None


def _payload_status(payload: Any | None) -> str:
    return str(_nested_get(payload, "status") or "").strip()


def _answer_text(payload: Any | None) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("answer_text", "text", "final_answer", "response_text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    answer = payload.get("answer")
    if isinstance(answer, str):
        return answer
    if isinstance(answer, dict):
        for key in ("text", "answer_text", "content"):
            value = answer.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return ""




def _chatgpt_conversation_identity(url: str | None) -> str:
    """Return a stable ChatGPT conversation identity for compatibility checks.

    ChatGPT conversation URLs can carry transient query strings such as
    ``?tab=sources``.  A held auth-readiness session is compatible with API
    coverage only when it is visibly on the same conversation path as the
    selected ask target.  Ignore query/fragment for identity, but do not
    broaden project pages into conversation compatibility.
    """
    raw = str(url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urllib.parse.urlsplit(raw)
    except Exception:
        return raw.split("#", 1)[0].split("?", 1)[0]
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""
    if "/c/" not in path:
        return ""
    return f"{host}{path}" if host else path


def _same_chatgpt_conversation(left: str | None, right: str | None) -> bool:
    left_id = _chatgpt_conversation_identity(left)
    right_id = _chatgpt_conversation_identity(right)
    return bool(left_id and right_id and left_id == right_id)

def _summarize_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"type": type(payload).__name__, "repr": repr(payload)[:500]}
    keys = [
        "ok",
        "action",
        "status",
        "service",
        "version",
        "logged_in",
        "challenge_detected",
        "composer_visible",
        "release_blocking",
        "current_url",
        "conversation_url",
        "project_url",
        "project_source_mutated",
        "persistence_verified",
        "project_source_mutation_intent",
        "project_source_mutation_gate",
        "error",
        "detail",
    ]
    summary: dict[str, Any] = {k: payload.get(k) for k in keys if k in payload}
    if not summary:
        summary["keys"] = sorted(payload.keys())[:40]
    if "detail" in summary and isinstance(summary["detail"], dict):
        detail = summary["detail"]
        summary["detail"] = {k: detail.get(k) for k in keys if k in detail}
        if not summary["detail"]:
            summary["detail"] = {"keys": sorted(detail.keys())[:40]}
    if "sources" in payload and isinstance(payload.get("sources"), list):
        summary["source_count"] = len(payload["sources"])
    if "projects" in payload and isinstance(payload.get("projects"), list):
        summary["project_count"] = len(payload["projects"])
    if "chats" in payload and isinstance(payload.get("chats"), list):
        summary["chat_count"] = len(payload["chats"])
    if "answer_text" in payload:
        answer = str(payload.get("answer_text") or "")
        summary["answer_text_preview"] = answer[:120]
    return summary


class ApiRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.base_url = args.base_url.rstrip("/")
        self.token = args.token or os.getenv("CHATGPT_SERVICE_TOKEN") or os.getenv("CHATGPT_API_TOKEN") or ""
        self.steps: list[Step] = []
        self.report_dir = Path(args.report_dir or ".pb_profile/api_test_reports")
        self.run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        self.project_url = args.project_url or self._state_value(
            "current_project_home_url", "project_home_url", "project_url", fallback="https://chatgpt.com/"
        )
        self.conversation_url = args.conversation_url or self._current_state_value(
            "conversation_url", "current_conversation_url", fallback=""
        )
        self.preflight: dict[str, Any] = {
            "browser_profile_busy": False,
            "held_auth_readiness_session_active": False,
            "compatible_held_auth_readiness_session_active": False,
            "auto_reuse_compatible_held_session": bool(getattr(args, "auto_reuse_compatible_held_session", True)),
            "auto_reuse_applied": False,
            "checked": False,
            "probes": [],
        }

    def _read_state_payload(self) -> dict[str, Any]:
        state_path = Path(self.args.state_file or ".pb_profile/.promptbranch_state.json")
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return state if isinstance(state, dict) else {}

    def _state_value(self, *keys: str, fallback: str = "") -> str:
        state = self._read_state_payload()
        for key in keys:
            value = state.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        current = state.get("current")
        if isinstance(current, dict):
            for key in keys:
                value = current.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return fallback

    def _current_state_value(self, *keys: str, fallback: str = "") -> str:
        """Return state.current values before legacy top-level state values.

        Conversation state schema v2 keeps the current operator-selected task
        under ``current.conversation_url`` while legacy/top-level
        ``conversation_url`` may still reference an older task.  API coverage
        ask must target the same current task as normal ``pb ask`` and must
        preserve query parameters exactly as stored.
        """
        state = self._read_state_payload()
        current = state.get("current")
        if isinstance(current, dict):
            for key in keys:
                value = current.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        for key in keys:
            value = state.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return fallback

    def _ask_conversation_url(self) -> str:
        if self.args.conversation_url:
            return str(self.args.conversation_url).strip()
        return self._current_state_value("conversation_url", "current_conversation_url", fallback=self.conversation_url or "")

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = dict(extra or {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _url(self, path: str, query: dict[str, Any] | None = None) -> str:
        url = f"{self.base_url}{path}"
        if query:
            cleaned = {k: v for k, v in query.items() if v is not None and v != ""}
            if cleaned:
                url += "?" + urllib.parse.urlencode(cleaned, doseq=True)
        return url

    def skip(self, name: str, method: str, path: str, category: str, reason: str) -> None:
        self.steps.append(
            Step(
                name=name,
                method=method,
                path=path,
                category=category,
                status="skipped",
                ok=True,
                skip_reason=reason,
            )
        )

    def _browser_body(self, *, keep_open: bool = False) -> dict[str, Any]:
        return {"keep_open": bool(keep_open), "project_url": self.project_url}

    def _browser_query(self, **extra: Any) -> dict[str, Any]:
        query: dict[str, Any] = {"keep_open": False, "project_url": self.project_url}
        query.update(extra)
        return query

    def _should_keep_auth_session_open(self) -> bool:
        return bool(self.args.hold_auth_session or self.args.keep_open)

    def _record_busy_classification(self, step: Step, payload: Any | None) -> None:
        classification = _classify_response(step.http_status, payload, step.error)
        if classification:
            step.classification = classification
            if step.response_summary is None:
                step.response_summary = {}
            step.response_summary["classification"] = classification

    def _raw_json_get(self, path: str, query: dict[str, Any] | None = None) -> tuple[int | None, Any | None, str | None, str]:
        url = self._url(path, query)
        req = urllib.request.Request(url, method="GET", headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=min(self.args.timeout_seconds, 30.0)) as resp:
                status = int(resp.status)
                payload = _json_loads_maybe(resp.read())
            return status, payload, None, url
        except urllib.error.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            payload = _json_loads_maybe(raw or str(exc).encode("utf-8"))
            return int(exc.code), payload, str(exc), url
        except Exception as exc:  # pragma: no cover - defensive live-run reporting
            return None, None, f"{type(exc).__name__}: {exc}", url

    def _held_session_payload_active(self, payload: Any | None) -> bool:
        if not isinstance(payload, dict):
            return False
        held = payload.get("held_session")
        if isinstance(held, dict) and held.get("active") is True:
            return True
        status = str(payload.get("status") or "").strip()
        if status and status != "no_held_auth_readiness_session" and payload.get("action") == "auth_readiness_session_status":
            # auth_readiness_session_status returns no_held_auth_readiness_session
            # for an empty slot.  Any other status means the status endpoint found
            # a session/probe for the checked key.
            return True
        return False

    def _preflight_check_held_auth_sessions(self) -> None:
        """Detect held auth sessions before browser-owning API coverage.

        The status endpoint key includes project URL.  Live v0.1.103.10.23
        evidence showed ``project_url=/project`` could report no held session
        while a compatible held session for the same profile existed under the
        conversation/default service key.  Probe all known scopes and record a
        single preflight result so the runner can fail early instead of running
        many doomed browser-owning endpoints.
        """

        probes: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        candidates: list[tuple[str, str | None]] = [
            ("default_service", None),
            ("project_url", self.project_url),
            ("conversation_url", self.conversation_url or None),
        ]
        busy = False
        active_probe_count = 0
        compatible_active_probe_count = 0
        selected_conversation_url = self._ask_conversation_url() or self.conversation_url or ""
        for label, project_url in candidates:
            query = {"project_url": project_url} if project_url else None
            key = (label, project_url or "")
            if key in seen:
                continue
            seen.add(key)
            status, payload, error, url = self._raw_json_get("/v1/auth-readiness/session/status", query=query)
            active = self._held_session_payload_active(payload)
            summary = _summarize_payload(payload) if payload is not None else None
            current_url = summary.get("current_url") if isinstance(summary, dict) else None
            compatible = bool(active and _same_chatgpt_conversation(str(current_url or ""), selected_conversation_url))
            busy = busy or active
            if active:
                active_probe_count += 1
                if compatible:
                    compatible_active_probe_count += 1
            probe = {
                "label": label,
                "project_url": project_url,
                "url": url,
                "http_status": status,
                "active": active,
                "compatible_with_selected_conversation": compatible,
                "classification": _classify_response(status, payload, error),
                "response_summary": summary,
                "error": error,
            }
            probes.append(probe)

        compatible_busy = bool(active_probe_count and active_probe_count == compatible_active_probe_count)
        auto_reuse_enabled = bool(getattr(self.args, "auto_reuse_compatible_held_session", True))
        auto_reuse_applied = bool(busy and compatible_busy and auto_reuse_enabled and not self.args.reuse_held_session)
        self.preflight = {
            "browser_profile_busy": busy,
            "held_auth_readiness_session_active": busy,
            "compatible_held_auth_readiness_session_active": compatible_busy,
            "auto_reuse_compatible_held_session": auto_reuse_enabled,
            "auto_reuse_applied": auto_reuse_applied,
            "checked": True,
            "reuse_held_session": bool(self.args.reuse_held_session or auto_reuse_applied),
            "reuse_held_session_requested": bool(self.args.reuse_held_session),
            "selected_conversation_url": selected_conversation_url,
            "probes": probes,
        }

    def _record_held_session_preflight_failure(self) -> None:
        self.steps.append(
            Step(
                name="held_auth_session_preflight",
                method="GET",
                path="/v1/auth-readiness/session/status",
                category="preflight",
                status="failed",
                ok=False,
                expected_statuses=[200],
                classification="browser_profile_busy",
                error="held auth-readiness session is active before browser-owning API coverage; rerun after releasing the held session or use --reuse-held-session",
                response_summary={
                    "preflight": {
                        "browser_profile_busy": True,
                        "held_auth_readiness_session_active": True,
                        "reuse_held_session": bool(self.args.reuse_held_session),
                        "compatible_held_auth_readiness_session_active": bool(self.preflight.get("compatible_held_auth_readiness_session_active")),
                        "auto_reuse_compatible_held_session": bool(self.preflight.get("auto_reuse_compatible_held_session")),
                        "auto_reuse_applied": bool(self.preflight.get("auto_reuse_applied")),
                    }
                },
            )
        )

    def _skip_due_preflight_busy(self, name: str, method: str, path: str, category: str) -> None:
        self.skip(name, method, path, category, "preflight.browser_profile_busy=true; browser-owning API coverage skipped to avoid repeated held-session failures")

    def _finish_after_held_session_preflight_failure(self) -> dict[str, Any]:
        self._record_held_session_preflight_failure()
        self._skip_due_preflight_busy("login_check", "POST", "/v1/login-check", "browser")
        self._skip_due_preflight_busy("projects_list", "GET", "/v1/projects", "projects")
        self._skip_due_preflight_busy("projects_resolve", "POST", "/v1/projects/resolve", "projects")
        self.skip("projects_create", "POST", "/v1/projects/create", "dangerous", "creates a real ChatGPT Project")
        self.skip("projects_ensure", "POST", "/v1/projects/ensure", "dangerous", "may create a real ChatGPT Project")
        self.request(
            "projects_remove_guard",
            "POST",
            "/v1/projects/remove",
            category="guard",
            json_body={
                "project_name": self.args.project_name,
                "project_url": self.project_url,
                "allow_ephemeral_test_cleanup": False,
                "keep_open": False,
            },
            expected_statuses=[200, 400, 403, 423],
        )
        self._skip_due_preflight_busy("chats_list", "GET", "/v1/chats", "chats")
        self._skip_due_preflight_busy("chats_debug_light", "GET", "/v1/chats/debug", "chats")
        self._skip_due_preflight_busy("chats_get", "POST", "/v1/chats/get", "chats")
        self.skip("chats_download_artifact", "POST", "/v1/chats/download-artifact", "artifact", "requires known artifact URL/filename")
        self._skip_due_preflight_busy("debug_rate_limit", "GET", "/v1/debug/rate-limit", "debug")
        self._skip_due_preflight_busy("project_source_capabilities", "GET", "/v1/project-source-capabilities", "sources")
        self._skip_due_preflight_busy("project_sources_list", "GET", "/v1/project-sources", "sources")
        self._skip_due_preflight_busy("project_sources_add_file", "POST", "/v1/project-sources", "mutation")
        self.skip(
            "project_sources_add_gate_closed",
            "POST",
            "/v1/project-sources",
            "guard",
            "skipped by default because non-standard service modes may allow mutation; use --include-source-gate-test after confirming standard-browser gate mode",
        )
        self.skip("project_sources_remove", "POST", "/v1/project-sources/remove", "mutation", "requires --allow-source-remove and --remove-source-name")
        self._skip_due_preflight_busy("ask", "POST", "/v1/ask", "ask")
        self._skip_due_preflight_busy("auth_readiness", "POST", "/v1/auth-readiness", "browser")
        self.skip("test_suite_run", "POST", "/v1/test-suite/run", "heavy", "use pb test browser/full explicitly; skipped by API coverage by default")
        self.request("ui_test_suite", "GET", "/ui/test-suite", category="status")
        return self.report()

    def _mark_semantic_failure(self, step: Step, reason: str, *, classification: str | None = None) -> None:
        if step.response_summary is None:
            step.response_summary = {}
        step.response_summary["semantic_error"] = reason
        step.status = "failed"
        step.ok = False
        step.error = reason
        if classification:
            step.classification = classification
            step.response_summary["classification"] = classification

    def _require_body_ok(self, step: Step, payload: Any | None, label: str) -> None:
        if not step.ok:
            return
        if _nested_get(payload, "ok") is not True:
            self._mark_semantic_failure(step, f"{label} response body did not report ok=true")

    def _require_debug_rate_limit_clear(self, step: Step, payload: Any | None) -> None:
        if not step.ok:
            return
        self._require_body_ok(step, payload, "debug_rate_limit")
        if not step.ok:
            return
        if _payload_status(payload) != "clear":
            self._mark_semantic_failure(step, "debug_rate_limit status was not clear", classification="rate_limited")

    def _require_auth_readiness_ready(self, step: Step, payload: Any | None) -> None:
        if not step.ok:
            return
        checks = {
            "ok": _nested_get(payload, "ok") is True,
            "logged_in": _payload_bool(payload, "logged_in") is True,
            "challenge_detected": _payload_bool(payload, "challenge_detected") is False,
            "release_blocking": _payload_bool(payload, "release_blocking") is False,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            classification = "auth_challenge_or_cloudflare" if "challenge_detected" in failed or "release_blocking" in failed else None
            self._mark_semantic_failure(step, "auth_readiness semantic checks failed: " + ", ".join(failed), classification=classification)

    def _require_source_add_success(self, step: Step, payload: Any | None) -> None:
        if not step.ok:
            return
        ok = _nested_get(payload, "ok") is True
        added = _nested_get(payload, "project_source_mutated") is True or str(_nested_get(payload, "action") or "") == "add"
        persisted = _nested_get(payload, "persistence_verified") is True
        failed = []
        if not ok:
            failed.append("ok=true")
        if not added:
            failed.append("project_source_mutated=true or action=add")
        if not persisted:
            failed.append("persistence_verified=true")
        if failed:
            self._mark_semantic_failure(step, "project source add semantic checks failed: missing " + ", ".join(failed))

    def _require_ask_success(self, step: Step, payload: Any | None) -> None:
        if not step.ok:
            return
        ok = _nested_get(payload, "ok") is True
        answer_text = _answer_text(payload)
        token_observed = bool(self.args.ask_token and self.args.ask_token in answer_text)
        failed = []
        if not ok:
            failed.append("ok=true")
        if not token_observed:
            failed.append(f"expected token {self.args.ask_token!r} not observed in answer_text")
        if failed:
            self._mark_semantic_failure(step, "ask semantic checks failed: missing " + ", ".join(failed))

    def request(
        self,
        name: str,
        method: str,
        path: str,
        *,
        category: str,
        query: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        multipart: dict[str, Any] | None = None,
        expected_statuses: list[int] | None = None,
        timeout: float | None = None,
    ) -> tuple[Step, Any | None]:
        expected = expected_statuses or [200]
        url = self._url(path, query)
        data: bytes | None = None
        headers: dict[str, str] = {}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif multipart is not None:
            data, content_type = self._encode_multipart(multipart)
            headers["Content-Type"] = content_type
        req = urllib.request.Request(url, method=method.upper(), data=data, headers=self._headers(headers))
        started = time.monotonic()
        payload: Any | None = None
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.args.timeout_seconds) as resp:
                status = int(resp.status)
                raw = resp.read()
            payload = _json_loads_maybe(raw)
            step = Step(
                name=name,
                method=method.upper(),
                path=path,
                category=category,
                status="passed" if status in expected else "failed",
                ok=status in expected,
                expected_statuses=expected,
                http_status=status,
                elapsed_seconds=round(time.monotonic() - started, 3),
                url=url,
                response_summary=_summarize_payload(payload),
            )
        except urllib.error.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            payload = _json_loads_maybe(raw or str(exc).encode("utf-8"))
            status = int(exc.code)
            step = Step(
                name=name,
                method=method.upper(),
                path=path,
                category=category,
                status="passed" if status in expected else "failed",
                ok=status in expected,
                expected_statuses=expected,
                http_status=status,
                elapsed_seconds=round(time.monotonic() - started, 3),
                url=url,
                error=str(exc),
                response_summary=_summarize_payload(payload),
            )
        except Exception as exc:
            step = Step(
                name=name,
                method=method.upper(),
                path=path,
                category=category,
                status="failed",
                ok=False,
                expected_statuses=expected,
                elapsed_seconds=round(time.monotonic() - started, 3),
                url=url,
                error=f"{type(exc).__name__}: {exc}",
                response_summary={"traceback": traceback.format_exc(limit=5)},
            )
        self._record_busy_classification(step, payload)
        self.steps.append(step)
        if self.args.step_delay_seconds > 0 and category in {"browser", "ask", "sources", "projects", "chats", "mutation"}:
            time.sleep(self.args.step_delay_seconds)
        return step, payload

    def _encode_multipart(self, fields: dict[str, Any]) -> tuple[bytes, str]:
        boundary = "----promptbranch-api-test-" + uuid.uuid4().hex
        parts: list[bytes] = []
        for name, value in fields.items():
            if value is None:
                continue
            if isinstance(value, tuple) and len(value) == 2 and isinstance(value[1], (str, Path)):
                filename = str(value[0])
                path = Path(value[1])
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                parts.append(f"--{boundary}\r\n".encode())
                parts.append(
                    f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
                )
                parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
                parts.append(path.read_bytes())
                parts.append(b"\r\n")
            else:
                parts.append(f"--{boundary}\r\n".encode())
                parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
                parts.append(str(value).encode("utf-8"))
                parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        return b"".join(parts), f"multipart/form-data; boundary={boundary}"

    def run(self) -> dict[str, Any]:
        # Root and health are intentionally unauthenticated/read-only.  They
        # never take browser ownership and are safe before browser smoke tests.
        self.request("root_redirect", "GET", "/", category="status", expected_statuses=[200, 307, 308])
        self.request("healthz", "GET", "/healthz", category="status")
        self.request("docker_browser_runtime", "GET", "/v1/docker/browser-runtime", category="status")
        self.request("browser_status", "GET", "/v1/browser/status", category="status")
        self.request("auth_readiness_session_status", "GET", "/v1/auth-readiness/session/status", category="status", query={"project_url": self.project_url})

        self._preflight_check_held_auth_sessions()
        if self.preflight.get("browser_profile_busy") and not self.preflight.get("reuse_held_session"):
            return self._finish_after_held_session_preflight_failure()

        # Serial browser mode deliberately avoids holding an auth-readiness
        # session before unrelated browser-owning endpoints.  v0.1.103.10.19
        # proved that auth-readiness keep-open poisons later projects/chats/
        # sources calls with browser_context_unavailable_held_auth_session_active.
        if self.args.include_browser:
            login_step, login_payload = self.request("login_check", "POST", "/v1/login-check", category="browser", json_body=self._browser_body(keep_open=False))
            if login_step.ok and _nested_get(login_payload, "logged_in") is not True:
                self._mark_semantic_failure(login_step, "login_check response body did not report logged_in=true")
        else:
            self.skip("login_check", "POST", "/v1/login-check", "browser", "--no-browser")

        projects_list_step, projects_list_payload = self.request("projects_list", "GET", "/v1/projects", category="projects", query=self._browser_query())
        self._require_body_ok(projects_list_step, projects_list_payload, "projects_list")
        projects_resolve_step, projects_resolve_payload = self.request(
            "projects_resolve",
            "POST",
            "/v1/projects/resolve",
            category="projects",
            json_body={"name": self.args.project_name, "keep_open": False, "project_url": self.project_url},
        )
        self._require_body_ok(projects_resolve_step, projects_resolve_payload, "projects_resolve")
        self.skip("projects_create", "POST", "/v1/projects/create", "dangerous", "creates a real ChatGPT Project")
        self.skip("projects_ensure", "POST", "/v1/projects/ensure", "dangerous", "may create a real ChatGPT Project")
        self.request(
            "projects_remove_guard",
            "POST",
            "/v1/projects/remove",
            category="guard",
            json_body={
                "project_name": self.args.project_name,
                "project_url": self.project_url,
                "allow_ephemeral_test_cleanup": False,
                "keep_open": False,
            },
            expected_statuses=[200, 400, 403, 423],
        )

        chats_list_step, chats_list_payload = self.request("chats_list", "GET", "/v1/chats", category="chats", query=self._browser_query())
        self._require_body_ok(chats_list_step, chats_list_payload, "chats_list")
        chats_debug_step, chats_debug_payload = self.request("chats_debug_light", "GET", "/v1/chats/debug", category="chats", query=self._browser_query(scroll_rounds=1, wait_ms=100, include_history="false"))
        self._require_body_ok(chats_debug_step, chats_debug_payload, "chats_debug_light")
        if self.conversation_url:
            chats_get_step, chats_get_payload = self.request(
                "chats_get",
                "POST",
                "/v1/chats/get",
                category="chats",
                json_body={"conversation_url": self.conversation_url, "keep_open": False, "project_url": self.project_url},
            )
            self._require_body_ok(chats_get_step, chats_get_payload, "chats_get")
        else:
            self.skip("chats_get", "POST", "/v1/chats/get", "chats", "no conversation_url in state or arguments")
        self.skip("chats_download_artifact", "POST", "/v1/chats/download-artifact", "artifact", "requires known artifact URL/filename")

        rate_step, rate_payload = self.request("debug_rate_limit", "GET", "/v1/debug/rate-limit", category="debug", query=self._browser_query(probe_backend="false", wait_ms=100))
        self._require_debug_rate_limit_clear(rate_step, rate_payload)
        source_caps_step, source_caps_payload = self.request("project_source_capabilities", "GET", "/v1/project-source-capabilities", category="sources", query=self._browser_query())
        self._require_body_ok(source_caps_step, source_caps_payload, "project_source_capabilities")
        sources_list_step, sources_list_payload = self.request("project_sources_list", "GET", "/v1/project-sources", category="sources", query=self._browser_query())
        self._require_body_ok(sources_list_step, sources_list_payload, "project_sources_list")

        if self.args.source_file and self.args.allow_source_add:
            source_path = Path(self.args.source_file)
            source_add_step, source_add_payload = self.request(
                "project_sources_add_file",
                "POST",
                "/v1/project-sources",
                category="mutation",
                multipart={
                    "type": "file",
                    "name": self.args.source_name or source_path.name,
                    "overwrite_existing": "true",
                    "keep_open": "false",
                    "project_url": self.project_url,
                    "allow_project_source_mutation": "true",
                    "file": (source_path.name, source_path),
                },
                timeout=max(self.args.timeout_seconds, 300.0),
            )
            self._require_source_add_success(source_add_step, source_add_payload)
        else:
            self.skip(
                "project_sources_add_file",
                "POST",
                "/v1/project-sources",
                "mutation",
                "requires --allow-source-add and --source-file",
            )

        if self.args.include_source_gate_test:
            self.request(
                "project_sources_add_gate_closed",
                "POST",
                "/v1/project-sources",
                category="guard",
                multipart={
                    "type": "text",
                    "name": f"api-coverage-gate-{self.run_id}.txt",
                    "value": "gate should remain closed without explicit mutation intent",
                    "overwrite_existing": "false",
                    "keep_open": "false",
                    "project_url": self.project_url,
                    "allow_project_source_mutation": "false",
                },
                expected_statuses=[403],
            )
        else:
            self.skip(
                "project_sources_add_gate_closed",
                "POST",
                "/v1/project-sources",
                "guard",
                "skipped by default because non-standard service modes may allow mutation; use --include-source-gate-test after confirming standard-browser gate mode",
            )

        if self.args.remove_source_name and self.args.allow_source_remove:
            self.request(
                "project_sources_remove",
                "POST",
                "/v1/project-sources/remove",
                category="mutation",
                json_body={"source_name": self.args.remove_source_name, "exact": True, "keep_open": False, "project_url": self.project_url},
            )
        else:
            self.skip("project_sources_remove", "POST", "/v1/project-sources/remove", "mutation", "requires --allow-source-remove and --remove-source-name")

        if self.args.include_ask:
            target = self._ask_conversation_url() or self.project_url
            ask_step, ask_payload = self.request(
                "ask",
                "POST",
                "/v1/ask",
                category="ask",
                multipart={
                    "prompt": f"Reply with exactly the single token {self.args.ask_token} and nothing else.",
                    "expect_json": "false",
                    "keep_open": "false",
                    "prefer_button_submit": "true",
                    "project_url": self.project_url,
                    "conversation_url": target,
                    "service_timeout_seconds": str(self.args.ask_timeout_seconds),
                },
                timeout=max(self.args.timeout_seconds, self.args.ask_timeout_seconds + 15),
            )
            self._require_ask_success(ask_step, ask_payload)
        else:
            self.skip("ask", "POST", "/v1/ask", "ask", "--no-ask")

        if self.args.include_browser:
            auth_step, auth_payload = self.request(
                "auth_readiness",
                "POST",
                "/v1/auth-readiness",
                category="browser",
                json_body=self._browser_body(keep_open=self._should_keep_auth_session_open()),
            )
            self._require_auth_readiness_ready(auth_step, auth_payload)
        else:
            self.skip("auth_readiness", "POST", "/v1/auth-readiness", "browser", "--no-browser")

        self.skip("test_suite_run", "POST", "/v1/test-suite/run", "heavy", "use pb test browser/full explicitly; skipped by API coverage by default")
        self.request("ui_test_suite", "GET", "/ui/test-suite", category="status")

        return self.report()

    def report(self) -> dict[str, Any]:
        failed = [s for s in self.steps if not s.ok]
        executed = [s for s in self.steps if s.status != "skipped"]
        skipped = [s for s in self.steps if s.status == "skipped"]
        by_category: dict[str, dict[str, int]] = {}
        for step in self.steps:
            bucket = by_category.setdefault(step.category, {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
            bucket["total"] += 1
            bucket[step.status if step.status in {"passed", "failed", "skipped"} else "failed"] += 1
        payload = {
            "ok": not failed,
            "action": "api_coverage_test",
            "status": "passed" if not failed else "failed",
            "run_id": self.run_id,
            "base_url": self.base_url,
            "project_url": self.project_url,
            "conversation_url": self.conversation_url,
            "counts": {
                "total": len(self.steps),
                "executed": len(executed),
                "passed": sum(1 for s in self.steps if s.status == "passed"),
                "failed": len(failed),
                "skipped": len(skipped),
                "browser_profile_busy": sum(1 for s in self.steps if s.classification == "browser_profile_busy"),
            },
            "preflight": self.preflight,
            "by_category": by_category,
            "steps": [s.__dict__ for s in self.steps],
        }
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.report_dir / f"api-coverage-{self.run_id}.json"
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        payload["report_path"] = str(report_path)
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Promptbranch container API coverage tests sequentially.")
    parser.add_argument("--base-url", default=os.getenv("PROMPTBRANCH_SERVICE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--token", default=os.getenv("CHATGPT_SERVICE_TOKEN") or os.getenv("CHATGPT_API_TOKEN"))
    parser.add_argument("--state-file", default=".pb_profile/.promptbranch_state.json")
    parser.add_argument("--project-url")
    parser.add_argument("--conversation-url")
    parser.add_argument("--project-name", default="promptbranch3")
    parser.add_argument("--run-id")
    parser.add_argument("--report-dir")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--step-delay-seconds", type=float, default=0.0)
    parser.add_argument("--hold-auth-session", action="store_true", help="Leave the final auth-readiness session open. Off by default to avoid self-conflicts.")
    parser.add_argument("--reuse-held-session", action="store_true", help="Reuse an active held auth-readiness session instead of failing API coverage preflight.")
    parser.add_argument("--no-auto-reuse-compatible-held-session", dest="auto_reuse_compatible_held_session", action="store_false", help="Disable automatic reuse when a held auth-readiness session is already on the selected conversation.")
    parser.add_argument("--serial-browser-mode", action="store_true", default=True, help="Run browser-owning endpoints one at a time without holding auth-readiness between unrelated calls. Default: enabled.")
    parser.add_argument("--keep-open", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-browser", dest="include_browser", action="store_false", help="Skip browser-owning auth/login endpoints.")
    parser.add_argument("--no-ask", dest="include_ask", action="store_false", help="Skip the /v1/ask endpoint.")
    parser.add_argument("--ask-token", default="API_ASK_OK")
    parser.add_argument("--ask-timeout-seconds", type=float, default=300.0)
    parser.add_argument("--allow-source-add", action="store_true", help="Actually call /v1/project-sources with explicit mutation intent.")
    parser.add_argument("--source-file", help="File to upload when --allow-source-add is set.")
    parser.add_argument("--source-name", help="Display name for --source-file upload.")
    parser.add_argument("--allow-source-remove", action="store_true", help="Actually call /v1/project-sources/remove for --remove-source-name.")
    parser.add_argument("--include-source-gate-test", action="store_true", help="Attempt a Project Source add without mutation intent and expect a 403 gate. Only safe in gated standard-browser mode.")
    parser.add_argument("--remove-source-name")
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    parser.add_argument("--summary", action="store_true", help="Print a compact summary even when --json is used.")
    parser.set_defaults(include_browser=True, include_ask=True, auto_reuse_compatible_held_session=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = ApiRunner(args).run()
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"api coverage: {payload['status']}")
        print(f"report_path={payload['report_path']}")
        print("counts=" + json.dumps(payload["counts"], sort_keys=True))
        for step in payload["steps"]:
            marker = "PASS" if step["status"] == "passed" else ("SKIP" if step["status"] == "skipped" else "FAIL")
            extra = ""
            if step.get("http_status") is not None:
                extra += f" http={step['http_status']}"
            if step.get("skip_reason"):
                extra += f" reason={step['skip_reason']}"
            if step.get("error"):
                extra += f" error={step['error']}"
            print(f"{marker} {step['name']} [{step['method']} {step['path']}]{extra}")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

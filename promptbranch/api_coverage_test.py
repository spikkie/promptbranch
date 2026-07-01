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
    response_summary: dict[str, Any] | None = None


def _json_loads_maybe(data: bytes) -> Any:
    text = data.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_text": text[:4000], "raw_text_length": len(text)}


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
        self.conversation_url = args.conversation_url or self._state_value(
            "current_conversation_url", "conversation_url", fallback=""
        )

    def _state_value(self, *keys: str, fallback: str = "") -> str:
        state_path = Path(self.args.state_file or ".pb_profile/.promptbranch_state.json")
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            return fallback
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
        # Root and health are intentionally unauthenticated/read-only.
        self.request("root_redirect", "GET", "/", category="status", expected_statuses=[200, 307, 308])
        self.request("healthz", "GET", "/healthz", category="status")
        self.request("docker_browser_runtime", "GET", "/v1/docker/browser-runtime", category="status")
        self.request("browser_status", "GET", "/v1/browser/status", category="status")
        self.request("auth_readiness_session_status", "GET", "/v1/auth-readiness/session/status", category="status", query={"project_url": self.project_url})

        if self.args.include_browser:
            self.request("auth_readiness", "POST", "/v1/auth-readiness", category="browser", json_body={"keep_open": self.args.keep_open})
            self.request("login_check", "POST", "/v1/login-check", category="browser", json_body={"keep_open": False})
        else:
            self.skip("auth_readiness", "POST", "/v1/auth-readiness", "browser", "--no-browser")
            self.skip("login_check", "POST", "/v1/login-check", "browser", "--no-browser")

        if self.args.include_ask:
            target = self.conversation_url or self.project_url
            self.request(
                "ask",
                "POST",
                "/v1/ask",
                category="ask",
                multipart={
                    "prompt": f"Reply with exactly the single token {self.args.ask_token} and nothing else.",
                    "expect_json": "false",
                    "keep_open": "false",
                    "project_url": self.project_url,
                    "conversation_url": target,
                    "service_timeout_seconds": str(self.args.ask_timeout_seconds),
                },
                timeout=max(self.args.timeout_seconds, self.args.ask_timeout_seconds + 15),
            )
        else:
            self.skip("ask", "POST", "/v1/ask", "ask", "--no-ask")

        self.request("projects_list", "GET", "/v1/projects", category="projects", query={"keep_open": False, "project_url": self.project_url})
        self.request(
            "projects_resolve",
            "POST",
            "/v1/projects/resolve",
            category="projects",
            json_body={"name": self.args.project_name, "keep_open": False, "project_url": self.project_url},
        )
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

        self.request("chats_list", "GET", "/v1/chats", category="chats", query={"keep_open": False, "project_url": self.project_url})
        self.request("chats_debug_light", "GET", "/v1/chats/debug", category="chats", query={"keep_open": False, "project_url": self.project_url, "scroll_rounds": 1, "wait_ms": 100, "include_history": "false"})
        if self.conversation_url:
            self.request(
                "chats_get",
                "POST",
                "/v1/chats/get",
                category="chats",
                json_body={"conversation_url": self.conversation_url, "keep_open": False, "project_url": self.project_url},
            )
        else:
            self.skip("chats_get", "POST", "/v1/chats/get", "chats", "no conversation_url in state or arguments")
        self.skip("chats_download_artifact", "POST", "/v1/chats/download-artifact", "artifact", "requires known artifact URL/filename")

        self.request("debug_rate_limit", "GET", "/v1/debug/rate-limit", category="debug", query={"keep_open": False, "project_url": self.project_url, "probe_backend": "false", "wait_ms": 100})
        self.request("project_source_capabilities", "GET", "/v1/project-source-capabilities", category="sources", query={"keep_open": False, "project_url": self.project_url})
        self.request("project_sources_list", "GET", "/v1/project-sources", category="sources", query={"keep_open": False, "project_url": self.project_url})

        if self.args.source_file and self.args.allow_source_add:
            source_path = Path(self.args.source_file)
            self.request(
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
            },
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
    parser.add_argument("--keep-open", action="store_true", help="Ask auth-readiness to keep the browser session open.")
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
    parser.set_defaults(include_browser=True, include_ask=True)
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

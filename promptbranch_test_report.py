from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable
from datetime import datetime, timezone


def _decode_json_objects(text: str) -> list[tuple[int, int, Any]]:
    decoder = json.JSONDecoder()
    objects: list[tuple[int, int, Any]] = []
    index = 0
    while True:
        start = text.find("{", index)
        if start < 0:
            break
        try:
            obj, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            index = start + 1
            continue
        objects.append((start, start + end, obj))
        index = start + max(end, 1)
    return objects


def _looks_like_test_suite(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("action") == "test_suite":
        return True
    if payload.get("profile") in {"browser", "agent", "full"} and ("steps" in payload or "browser" in payload or "agent" in payload):
        return True
    return False


def extract_test_suite_payload(text: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    candidates = [(start, end, obj) for start, end, obj in _decode_json_objects(text) if _looks_like_test_suite(obj)]
    if not candidates:
        return None, {"json_object_count": 0, "selected": None}
    start, end, payload = candidates[-1]
    return payload, {
        "json_object_count": len(candidates),
        "selected": {"start_offset": start, "end_offset": end},
    }


def _step_count(section: dict[str, Any] | None) -> int:
    steps = section.get("steps") if isinstance(section, dict) else None
    return len(steps) if isinstance(steps, list) else 0


def _classify_failure_text(text: object) -> str | None:
    haystack = str(text or "")
    if any(token in haystack for token in ("net::ERR_ADDRESS_UNREACHABLE", "net::ERR_NAME_NOT_RESOLVED", "net::ERR_INTERNET_DISCONNECTED")):
        return "browser_navigation_unavailable"
    if "net::ERR_CONNECTION_REFUSED" in haystack or "net::ERR_CONNECTION_RESET" in haystack:
        return "browser_connection_unavailable"
    if "HTTPStatusError" in haystack and " 500 " in haystack:
        return "service_http_500"
    return None


def _failed_steps(section_name: str, section: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(section, dict):
        return []
    steps = section.get("steps")
    if not isinstance(steps, list):
        return []
    failures: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        if bool(step.get("ok")):
            continue
        payload = step.get("payload") if isinstance(step.get("payload"), dict) else {}
        diagnostic = payload.get("diagnostic") or payload.get("error")
        classification = _classify_failure_text(" ".join(str(item or "") for item in (
            step.get("status"),
            diagnostic,
            payload.get("exception"),
            payload.get("error"),
            payload.get("message"),
        )))
        item = {
            "section": section_name,
            "name": step.get("name"),
            "status": step.get("status") or payload.get("status"),
            "expected_failure": bool(step.get("expected_failure")),
            "expected_status": step.get("expected_status"),
            "diagnostic": diagnostic,
        }
        if classification:
            item["classification"] = classification
        failures.append(item)
    return failures


def _find_step(section: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    if not isinstance(section, dict):
        return None
    steps = section.get("steps")
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and step.get("name") == name:
            return step
    return None


def _step_payload_from(section: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    step = _find_step(section, name)
    if not isinstance(step, dict):
        return None
    payload = step.get("payload")
    if not isinstance(payload, dict):
        return None
    return {"ok": bool(step.get("ok")), **payload}


def _version_consistency_from(section: dict[str, Any] | None) -> dict[str, Any] | None:
    source = _step_payload_from(section, "version_consistency")
    metadata = _step_payload_from(section, "package_import_metadata")
    smoke = _step_payload_from(section, "package_import_smoke")
    version_sources: dict[str, Any] = {}
    if source:
        version_sources["source"] = source
    if metadata and isinstance(metadata.get("version_consistency"), dict):
        version_sources["package_metadata"] = metadata.get("version_consistency")
    if smoke and isinstance(smoke.get("version_consistency"), dict):
        version_sources["installed_runtime"] = smoke.get("version_consistency")
    if not version_sources:
        return None
    return {
        "ok": all(bool(item.get("ok")) for item in version_sources.values() if isinstance(item, dict)),
        "sources": version_sources,
    }


def _package_hygiene_from(section: dict[str, Any] | None) -> dict[str, Any] | None:
    step = _find_step(section, "package_hygiene")
    if not isinstance(step, dict):
        return None
    payload = step.get("payload")
    if not isinstance(payload, dict):
        return None
    return {
        "ok": bool(step.get("ok")),
        "status": payload.get("status"),
        "zip_path": payload.get("zip_path"),
        "testzip": payload.get("testzip"),
        "bad_entry_count": len(payload.get("bad_entries") or []) if isinstance(payload.get("bad_entries"), list) else None,
        "wrapper_folder": payload.get("wrapper_folder"),
    }


def _section_summary(name: str, section: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(section.get("ok")) if isinstance(section, dict) else False,
        "step_count": _step_count(section),
        "failure_count": len(_failed_steps(name, section)),
        "failed_steps": _failed_steps(name, section),
    }


def _derive_sections(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    profile = payload.get("profile")
    if profile == "full":
        browser = payload.get("browser") if isinstance(payload.get("browser"), dict) else None
        agent = payload.get("agent") if isinstance(payload.get("agent"), dict) else None
        return browser, agent
    if profile == "browser":
        return payload, None
    if profile == "agent":
        return None, payload
    return None, None


def summarize_test_suite_payload(payload: dict[str, Any]) -> dict[str, Any]:
    browser, agent = _derive_sections(payload)
    browser_summary = _section_summary("browser", browser) if browser is not None else None
    agent_summary = _section_summary("agent", agent) if agent is not None else None
    failures: list[dict[str, Any]] = []
    if browser_summary:
        failures.extend(browser_summary["failed_steps"])
    if agent_summary:
        failures.extend(agent_summary["failed_steps"])
    rate_limit_telemetry = payload.get("rate_limit_telemetry")
    if rate_limit_telemetry is None and isinstance(browser, dict):
        rate_limit_telemetry = browser.get("rate_limit_telemetry")
    safety = payload.get("safety")
    if safety is None and isinstance(agent, dict):
        safety = agent.get("safety")
    return {
        "ok": bool(payload.get("ok")),
        "action": payload.get("action"),
        "profile": payload.get("profile"),
        "version": (agent or payload).get("version") if isinstance(agent or payload, dict) else None,
        "browser": browser_summary,
        "agent": agent_summary,
        "failure_count": len(failures),
        "failed_steps": failures,
        "rate_limit_telemetry": rate_limit_telemetry if isinstance(rate_limit_telemetry, dict) else {},
        "safety": safety if isinstance(safety, dict) else {},
        "package_hygiene": _package_hygiene_from(agent or payload),
        "version_consistency": _version_consistency_from(agent or payload),
    }



def _path_mtime_payload(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError:
        return {"path": str(path), "mtime": None, "mtime_iso": None, "size_bytes": None}
    return {
        "path": str(path),
        "mtime": stat.st_mtime,
        "mtime_iso": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "size_bytes": stat.st_size,
    }


def _is_full_suite_log_candidate(path: Path) -> bool:
    """Return True for primary full-suite log files.

    `pb test status` is meant to summarize logs produced by commands such as::

        pb test full --json 2>&1 | tee pb_test.full.v0.0.173.log

    Operator-created derivatives such as `.log.report` and `.log.status` are
    outputs of report/status commands, not full-suite evidence.  Treating them
    as candidates can make a fresh redirected status file mask a valid full-suite
    run.  A trailing dot after `.log` is accepted because an earlier operator run
    accidentally produced `pb_test-suite.full.v0.0.154.log.` and that should
    remain parseable.
    """
    name = path.name
    allowed_prefixes = (
        "pb_test.full",
        "pb_test-suite.full",
        "pb_test_suite.full",
    )
    if not name.startswith(allowed_prefixes):
        return False
    return name.endswith(".log") or name.endswith(".log.")


def find_test_status_logs(path: str | Path = ".") -> list[dict[str, Any]]:
    """Return primary candidate full-suite logs newest first.

    This deliberately looks only for full-suite style log names so `pb test status`
    remains a lightweight "last accepted full validation" view instead of a loose
    log scanner. The parser still validates the JSON payload before a log is
    accepted as status evidence.
    """
    root = Path(path).expanduser()
    patterns = (
        "pb_test.full*.log*",
        "pb_test-suite.full*.log*",
        "pb_test_suite.full*.log*",
    )
    seen: set[Path] = set()
    candidates: list[Path] = []
    if root.is_file():
        candidates.append(root)
    elif root.is_dir():
        for pattern in patterns:
            for item in root.glob(pattern):
                if item.is_file() and item not in seen and _is_full_suite_log_candidate(item):
                    seen.add(item)
                    candidates.append(item)
    candidates.sort(key=lambda item: item.stat().st_mtime if item.exists() else 0.0, reverse=True)
    return [_path_mtime_payload(item) for item in candidates]


def build_test_status(
    *,
    path: str | Path = ".",
    log: str | Path | None = None,
    service_log: str | Path | None = None,
    max_candidates: int = 25,
) -> dict[str, Any]:
    """Build a lightweight status from the newest valid full-suite log.

    No tests are executed here. The command is intentionally read-only and relies
    on a previously captured `pb test full --json` log. When scanning a directory,
    the newest candidate is authoritative: if it exists but is invalid, the
    command returns ``latest_full_suite_log_invalid`` instead of silently falling
    back to an older green run. Older valid runs are still reported under
    ``last_valid`` for operator context.
    """
    explicit_log = log is not None
    if explicit_log:
        candidates = [_path_mtime_payload(Path(log).expanduser())]
    else:
        candidates = find_test_status_logs(path)
    checked: list[dict[str, Any]] = []
    first_checked: dict[str, Any] | None = None
    first_valid: dict[str, Any] | None = None

    for candidate in candidates[:max_candidates]:
        candidate_path = candidate.get("path")
        if not candidate_path:
            continue
        report = build_test_report(candidate_path, service_log=service_log)
        suite = report.get("suite") if isinstance(report.get("suite"), dict) else {}
        profile = suite.get("profile") if isinstance(suite, dict) else None
        accepted = bool(report.get("suite")) and profile == "full"
        checked_entry = {
            **candidate,
            "status": report.get("status"),
            "ok": report.get("ok"),
            "profile": profile,
            "accepted": accepted,
        }
        checked.append(checked_entry)
        if first_checked is None:
            first_checked = checked_entry
        if accepted:
            valid_payload = {
                "selected_log": candidate,
                "suite": suite,
                "source": report.get("source"),
                **({"service_log": report.get("service_log")} if isinstance(report.get("service_log"), dict) else {}),
            }
            if first_valid is None:
                first_valid = valid_payload
            # The newest candidate is valid, so this is the authoritative status.
            if first_checked is checked_entry or explicit_log:
                return {
                    "ok": bool(report.get("ok")),
                    "action": "test_status",
                    "status": "verified" if report.get("ok") else "suite_failed",
                    "path": str(Path(path).expanduser()),
                    "selected_log": candidate,
                    "checked": checked,
                    "suite": suite,
                    "source": report.get("source"),
                    **({"service_log": report.get("service_log")} if isinstance(report.get("service_log"), dict) else {}),
                }
            # A newer candidate was invalid. Do not hide that by returning ok=true.
            break

    if first_checked is not None and first_valid is not None and not first_checked.get("accepted"):
        return {
            "ok": False,
            "action": "test_status",
            "status": "latest_full_suite_log_invalid",
            "path": str(Path(path).expanduser()),
            "latest_log": first_checked,
            "checked": checked,
            "last_valid": first_valid,
        }

    return {
        "ok": False,
        "action": "test_status",
        "status": "no_full_suite_log_found" if not candidates else "no_valid_full_suite_log_found",
        "path": str(Path(path).expanduser()),
        "candidate_count": len(candidates),
        "checked": checked,
    }

def parse_service_log(path: str | Path, *, max_event_lines: int = 40) -> dict[str, Any]:
    service_path = Path(path).expanduser()
    try:
        lines = service_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return {
            "ok": False,
            "path": str(service_path),
            "status": "read_failed",
            "error": str(exc),
        }

    event_lines: list[dict[str, Any]] = []
    rate_limit_visible_count = 0
    rate_limit_probe_count = 0
    http_429_count = 0
    conversation_429_count = 0
    modal_text_count = 0
    cooldown_line_count = 0

    for lineno, line in enumerate(lines, start=1):
        lower = line.lower()
        is_rate_selector = "rate-limit" in lower or "temporarily limited access" in lower or "protect your data" in lower or "too many requests" in lower
        if is_rate_selector:
            rate_limit_probe_count += 1
            if "visible=true" in lower:
                rate_limit_visible_count += 1
            if "temporarily limited access" in lower or "protect your data" in lower or "too many requests" in lower:
                modal_text_count += 1
        if "429" in lower:
            http_429_count += 1
            if "conversation" in lower or "backend-api/conversations" in lower:
                conversation_429_count += 1
        if "cooldown" in lower and ("rate" in lower or "429" in lower or "conversation" in lower):
            cooldown_line_count += 1
        if (is_rate_selector and ("visible=true" in lower or "modal" in lower)) or "429" in lower or ("cooldown" in lower and "rate" in lower):
            if len(event_lines) < max_event_lines:
                event_lines.append({"line": lineno, "text": line[:500]})

    return {
        "ok": True,
        "path": str(service_path),
        "line_count": len(lines),
        "rate_limit_probe_count": rate_limit_probe_count,
        "rate_limit_modal_detected": rate_limit_visible_count > 0,
        "rate_limit_visible_true_count": rate_limit_visible_count,
        "modal_text_line_count": modal_text_count,
        "http_429_seen": http_429_count > 0,
        "http_429_count": http_429_count,
        "conversation_history_429_seen": conversation_429_count > 0,
        "conversation_history_429_count": conversation_429_count,
        "cooldown_line_count": cooldown_line_count,
        "events": event_lines,
    }


def build_test_report(log_path: str | Path, *, service_log: str | Path | None = None) -> dict[str, Any]:
    path = Path(log_path).expanduser()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "ok": False,
            "action": "test_report",
            "status": "read_failed",
            "log_path": str(path),
            "error": str(exc),
        }

    payload, extraction = extract_test_suite_payload(text)
    if payload is None:
        return {
            "ok": False,
            "action": "test_report",
            "status": "json_not_found",
            "log_path": str(path),
            "source": {"bytes": len(text.encode("utf-8", errors="replace")), **extraction},
        }

    suite = summarize_test_suite_payload(payload)
    result: dict[str, Any] = {
        "ok": bool(suite.get("ok")),
        "action": "test_report",
        "status": "verified" if suite.get("ok") else "suite_failed",
        "log_path": str(path),
        "source": {"bytes": len(text.encode("utf-8", errors="replace")), **extraction},
        "suite": suite,
    }
    if service_log:
        result["service_log"] = parse_service_log(service_log)
    return result


def render_test_report_text(report: dict[str, Any]) -> str:
    lines = [
        f"ok={bool(report.get('ok'))}",
        f"status={report.get('status')}",
        f"log_path={report.get('log_path')}",
    ]
    suite = report.get("suite") if isinstance(report.get("suite"), dict) else {}
    if suite:
        lines.extend([
            f"profile={suite.get('profile')}",
            f"suite_ok={suite.get('ok')}",
            f"failure_count={suite.get('failure_count')}",
        ])
        for key in ("browser", "agent"):
            section = suite.get(key)
            if isinstance(section, dict):
                lines.append(f"{key}.ok={section.get('ok')} steps={section.get('step_count')} failures={section.get('failure_count')}")
        telemetry = suite.get("rate_limit_telemetry") if isinstance(suite.get("rate_limit_telemetry"), dict) else {}
        if telemetry:
            lines.append(
                "rate_limit="
                f"modal={telemetry.get('rate_limit_modal_detected')} "
                f"429={telemetry.get('conversation_history_429_seen')} "
                f"cooldowns={telemetry.get('cooldown_wait_count')} "
                f"planned={telemetry.get('planned_cooldown_wait_count')}"
            )
        package = suite.get("package_hygiene") if isinstance(suite.get("package_hygiene"), dict) else None
        if package:
            lines.append(f"package_hygiene.ok={package.get('ok')} status={package.get('status')}")
        for failure in suite.get("failed_steps") or []:
            if isinstance(failure, dict):
                lines.append(f"failed={failure.get('section')}.{failure.get('name')} status={failure.get('status')} diagnostic={failure.get('diagnostic')}")
    service = report.get("service_log") if isinstance(report.get("service_log"), dict) else None
    if service:
        lines.append(
            "service_log="
            f"ok={service.get('ok')} "
            f"modal={service.get('rate_limit_modal_detected')} "
            f"429={service.get('conversation_history_429_seen')} "
            f"probes={service.get('rate_limit_probe_count')}"
        )
    return "\n".join(lines).rstrip() + "\n"

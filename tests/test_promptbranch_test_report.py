from __future__ import annotations

import json

from promptbranch_test_report import build_test_report, parse_service_log


def _suite_payload(ok: bool = True) -> dict:
    return {
        "ok": ok,
        "action": "test_suite",
        "profile": "full",
        "browser": {"ok": ok, "steps": [{"name": "browser_step", "ok": ok, "status": "verified" if ok else "failed"}]},
        "agent": {
            "ok": True,
            "version": "v0.0.159",
            "steps": [
                {"name": "package_hygiene", "ok": True, "payload": {"status": "verified", "zip_path": "release.zip", "bad_entries": [], "wrapper_folder": False}}
            ],
        },
        "rate_limit_telemetry": {
            "rate_limit_modal_detected": False,
            "conversation_history_429_seen": False,
            "cooldown_wait_seconds_total": 0.0,
            "cooldown_wait_count": 0,
            "planned_cooldown_wait_seconds_total": 90.0,
            "planned_cooldown_wait_count": 2,
            "service_rate_limit_events": [],
            "event_count": 0,
        },
        "safety": {
            "write_tools_blocked": True,
            "model_has_execution_authority": False,
            "source_or_artifact_mutation_allowed": False,
        },
    }


def test_build_test_report_extracts_last_test_suite_json_from_noisy_log(tmp_path):
    log = tmp_path / "suite.log"
    log.write_text("prefix\n" + json.dumps({"not": "suite"}) + "\n" + json.dumps(_suite_payload(), indent=2) + "\nsuffix\n", encoding="utf-8")

    report = build_test_report(log)

    assert report["ok"] is True
    assert report["status"] == "verified"
    assert report["suite"]["profile"] == "full"
    assert report["suite"]["browser"]["step_count"] == 1
    assert report["suite"]["agent"]["step_count"] == 1
    assert report["suite"]["rate_limit_telemetry"]["planned_cooldown_wait_count"] == 2
    assert report["suite"]["safety"]["write_tools_blocked"] is True
    assert report["suite"]["package_hygiene"]["ok"] is True


def test_build_test_report_marks_failed_suite(tmp_path):
    log = tmp_path / "suite_fail.log"
    log.write_text(json.dumps(_suite_payload(ok=False), indent=2), encoding="utf-8")

    report = build_test_report(log)

    assert report["ok"] is False
    assert report["status"] == "suite_failed"
    assert report["suite"]["failure_count"] == 1
    assert report["suite"]["failed_steps"][0]["name"] == "browser_step"


def test_parse_service_log_detects_modal_and_conversation_429(tmp_path):
    service = tmp_path / "service.log"
    service.write_text(
        "[selector] selector probe | label='initial-auth-check-rate-limit-modal' count=1 visible=True\n"
        "[network] response 429 url='https://chatgpt.com/backend-api/conversations?offset=0'\n"
        "[rate-limit] persisted cooldown wait seconds=180\n",
        encoding="utf-8",
    )

    payload = parse_service_log(service)

    assert payload["ok"] is True
    assert payload["rate_limit_modal_detected"] is True
    assert payload["conversation_history_429_seen"] is True
    assert payload["cooldown_line_count"] == 1


def test_promptbranch_test_report_is_declared_as_installable_module():
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    modules = pyproject["tool"]["setuptools"]["py-modules"]

    assert "promptbranch_test_report" in modules

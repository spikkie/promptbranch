from __future__ import annotations

import json
from pathlib import Path

from promptbranch_test_report import build_test_report, parse_service_log


def _suite_payload(ok: bool = True) -> dict:
    return {
        "ok": ok,
        "action": "test_suite",
        "profile": "full",
        "browser": {"ok": ok, "steps": [{"name": "browser_step", "ok": ok, "status": "verified" if ok else "failed"}]},
        "agent": {
            "ok": True,
            "version": "v0.0.163",
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


def test_build_test_status_selects_latest_valid_full_suite_log(tmp_path):
    old = tmp_path / "pb_test.full.v0.0.160.log"
    new = tmp_path / "pb_test.full.v0.0.163.log"
    old.write_text(json.dumps(_suite_payload(), indent=2), encoding="utf-8")
    payload = _suite_payload()
    payload["agent"]["version"] = "v0.0.163"
    new.write_text("noise\n" + json.dumps(payload, indent=2), encoding="utf-8")

    import os
    os.utime(old, (1000, 1000))
    os.utime(new, (2000, 2000))

    from promptbranch_test_report import build_test_status

    status = build_test_status(path=tmp_path)

    assert status["ok"] is True
    assert status["action"] == "test_status"
    assert status["status"] == "verified"
    assert status["selected_log"]["path"].endswith("pb_test.full.v0.0.163.log")
    assert status["suite"]["version"] == "v0.0.163"
    assert status["suite"]["profile"] == "full"
    assert status["suite"]["package_hygiene"]["ok"] is True


def test_build_test_status_reports_missing_full_suite_log(tmp_path):
    from promptbranch_test_report import build_test_status

    status = build_test_status(path=tmp_path)

    assert status["ok"] is False
    assert status["status"] == "no_full_suite_log_found"
    assert status["candidate_count"] == 0




def test_build_test_status_ignores_report_and_status_derivative_logs(tmp_path):
    from promptbranch_test_report import build_test_status, find_test_status_logs
    import os

    suite_log = tmp_path / "pb_test.full.v0.0.163.log"
    report_log = tmp_path / "pb_test.full.v0.0.163.log.report"
    status_log = tmp_path / "pb_test.full.v0.0.163.log.status"
    trailing_dot_log = tmp_path / "pb_test-suite.full.v0.0.154.log."

    suite_log.write_text(json.dumps(_suite_payload(), indent=2), encoding="utf-8")
    report_log.write_text("", encoding="utf-8")
    status_log.write_text("", encoding="utf-8")
    trailing_dot_log.write_text(json.dumps(_suite_payload(), indent=2), encoding="utf-8")

    os.utime(suite_log, (2000, 2000))
    os.utime(report_log, (4000, 4000))
    os.utime(status_log, (5000, 5000))
    os.utime(trailing_dot_log, (1000, 1000))

    candidates = find_test_status_logs(tmp_path)
    candidate_names = [Path(item["path"]).name for item in candidates]

    assert "pb_test.full.v0.0.163.log.status" not in candidate_names
    assert "pb_test.full.v0.0.163.log.report" not in candidate_names
    assert "pb_test.full.v0.0.163.log" in candidate_names
    assert "pb_test-suite.full.v0.0.154.log." in candidate_names

    status = build_test_status(path=tmp_path)

    assert status["ok"] is True
    assert status["status"] == "verified"
    assert status["selected_log"]["path"].endswith("pb_test.full.v0.0.163.log")


def test_build_test_status_does_not_hide_newest_invalid_full_suite_log(tmp_path):
    from promptbranch_test_report import build_test_status
    import os

    old = tmp_path / "pb_test.full.v0.0.162.log"
    new = tmp_path / "pb_test.full.v0.0.163.log"
    old.write_text(json.dumps(_suite_payload(), indent=2), encoding="utf-8")
    new.write_text("not json\n", encoding="utf-8")
    os.utime(old, (1000, 1000))
    os.utime(new, (2000, 2000))

    status = build_test_status(path=tmp_path)

    assert status["ok"] is False
    assert status["status"] == "latest_full_suite_log_invalid"
    assert status["latest_log"]["path"].endswith("pb_test.full.v0.0.163.log")
    assert status["latest_log"]["accepted"] is False
    assert status["last_valid"]["selected_log"]["path"].endswith("pb_test.full.v0.0.162.log")
    assert status["last_valid"]["suite"]["profile"] == "full"


def test_pyproject_declares_pb_console_script_alias():
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["project"]["scripts"]

    assert scripts["promptbranch"] == "promptbranch.cli:main"
    assert scripts["pb"] == "promptbranch.cli:main"


def test_report_classifies_browser_navigation_network_failure(tmp_path: Path) -> None:
    log = tmp_path / "pb_test.full.v0.0.166.log"
    log.write_text(json.dumps({
        "ok": False,
        "action": "test_suite",
        "profile": "full",
        "browser": {
            "ok": False,
            "steps": [
                {
                    "name": "task_message_flow.ask",
                    "ok": False,
                    "status": "failed",
                    "payload": {"error": "Page.goto: net::ERR_ADDRESS_UNREACHABLE https://chatgpt.com/g/demo/project"},
                }
            ],
        },
        "agent": {"ok": True, "steps": []},
    }), encoding="utf-8")

    report = build_test_report(log)

    assert report["suite"]["failed_steps"][0]["classification"] == "browser_navigation_unavailable"

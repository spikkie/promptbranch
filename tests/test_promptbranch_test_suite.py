from __future__ import annotations

import asyncio
import zipfile
from pathlib import Path

import promptbranch_test_suite as suite


def _ok(action: str = "ok", status: str = "verified") -> dict:
    return {"ok": True, "action": action, "status": status}


def test_agent_profile_runs_local_checks_and_expected_negatives(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v0.0.test\n", encoding="utf-8")
    (tmp_path / ".promptbranch").mkdir()
    (tmp_path / ".promptbranch" / "skills").mkdir()

    monkeypatch.setattr(suite, "mcp_host_smoke", lambda **kwargs: _ok("mcp_host_smoke"))
    monkeypatch.setattr(suite, "mcp_tool_call_via_stdio", lambda *args, **kwargs: _ok("mcp_tool_call"))
    monkeypatch.setattr(suite, "skill_list", lambda **kwargs: _ok("skill_list"))
    monkeypatch.setattr(suite, "skill_show", lambda *args, **kwargs: _ok("skill_show"))
    monkeypatch.setattr(suite, "skill_validate", lambda *args, **kwargs: _ok("skill_validate", "valid"))
    monkeypatch.setattr(suite, "agent_tool_call", lambda *args, **kwargs: _ok("agent_tool_call"))

    def fake_agent_run(request: str, **kwargs) -> dict:
        if request in {"sync sources", "create artifact release", "run pytest"}:
            return {"ok": False, "action": "agent_run", "status": "risk_rejected"}
        return _ok("agent_run")

    def fake_summarize(log_path: str, **kwargs) -> dict:
        if str(log_path).startswith("/"):
            return {"ok": False, "action": "agent_summarize_log", "status": "path_outside_repo"}
        return {"ok": True, "action": "agent_summarize_log", "status": "deterministic_summary"}

    monkeypatch.setattr(suite, "agent_run", fake_agent_run)
    monkeypatch.setattr(suite, "agent_summarize_log", fake_summarize)
    monkeypatch.setattr(suite, "package_import_smoke", lambda **kwargs: _ok("package_import_smoke"))
    monkeypatch.setattr(suite, "source_version_consistency", lambda **kwargs: _ok("version_consistency"))

    result = asyncio.run(suite.run_test_suite_async(profile="agent", path=str(tmp_path)))

    assert result["ok"] is True
    assert result["profile"] == "agent"
    names = [step["name"] for step in result["steps"]]
    assert "agent_summarize_log_path_escape" in names
    assert "agent_reject_artifact_release" in names
    assert result["safety"]["write_tools_blocked"] is True


def test_package_hygiene_detects_cache_entries(tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as archive:
        archive.writestr("VERSION", "v0.0.test\n")
        archive.writestr(".pytest_cache/CACHEDIR.TAG", "bad")
        archive.writestr("pkg/__pycache__/mod.cpython-312.pyc", b"bad")

    result = suite._package_hygiene(str(bad_zip), repo_path=tmp_path)

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert any(".pytest_cache" in entry for entry in result["bad_entries"])
    assert any("__pycache__" in entry for entry in result["bad_entries"])


def test_package_import_metadata_detects_undeclared_cli_import(tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad.zip"
    pyproject = """[tool.setuptools]
py-modules = ["promptbranch_cli"]
"""
    with zipfile.ZipFile(bad_zip, "w") as archive:
        archive.writestr("VERSION", "v0.0.test\n")
        archive.writestr("pyproject.toml", pyproject)
        archive.writestr("promptbranch_cli.py", "from promptbranch_test_report import build_test_report\n")
        archive.writestr("promptbranch_test_report.py", "def build_test_report(): pass\n")

    result = suite._package_import_metadata(str(bad_zip), repo_path=tmp_path)

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert "promptbranch_test_report" in result["missing_import_declarations"]


def test_package_import_smoke_runs_outside_repo(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.setuptools]\npy-modules = ["promptbranch_cli", "promptbranch_test_report"]\n',
        encoding="utf-8",
    )
    captured = {}

    class Completed:
        returncode = 0
        stdout = '{"imports":[{"module":"promptbranch_cli","ok":true}],"version_consistency":{"ok":true,"expected_version":"0.0.test","observations":[],"missing":[],"mismatches":[]}}'
        stderr = ''

    def fake_run(cmd, cwd, env, text, stdout, stderr, timeout, check):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["env"] = env
        return Completed()

    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    monkeypatch.setattr(suite.subprocess, "run", fake_run)

    result = suite.package_import_smoke(repo_path=tmp_path, python_executable="python-test")

    assert result["ok"] is True
    assert result["source_tree_masking_prevented"] is True
    assert captured["cmd"][0] == "python-test"
    assert str(tmp_path) not in captured["env"].get("PYTHONPATH", "")
    assert captured["cwd"] != str(tmp_path)


def test_agent_profile_reports_rate_limit_strategy_without_browser(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v0.0.test\n", encoding="utf-8")
    (tmp_path / ".promptbranch" / "skills" / "repo-inspection").mkdir(parents=True)

    monkeypatch.setattr(suite, "mcp_host_smoke", lambda **kwargs: _ok("mcp_host_smoke"))
    monkeypatch.setattr(suite, "mcp_tool_call_via_stdio", lambda *args, **kwargs: _ok("mcp_tool_call"))
    monkeypatch.setattr(suite, "skill_list", lambda **kwargs: _ok("skill_list"))
    monkeypatch.setattr(suite, "skill_show", lambda *args, **kwargs: _ok("skill_show"))
    monkeypatch.setattr(suite, "skill_validate", lambda *args, **kwargs: _ok("skill_validate", "valid"))
    monkeypatch.setattr(suite, "agent_tool_call", lambda *args, **kwargs: _ok("agent_tool_call"))
    def fake_summarize(log_path: str, **kwargs) -> dict:
        if str(log_path).startswith("/"):
            return {"ok": False, "action": "agent_summarize_log", "status": "path_outside_repo"}
        return {"ok": True, "status": "deterministic_summary"}

    monkeypatch.setattr(suite, "agent_summarize_log", fake_summarize)

    def fake_agent_run(request: str, **kwargs) -> dict:
        if request in {"sync sources", "create artifact release", "run pytest"}:
            return {"ok": False, "action": "agent_run", "status": "risk_rejected"}
        return _ok("agent_run")

    monkeypatch.setattr(suite, "agent_run", fake_agent_run)
    monkeypatch.setattr(suite, "package_import_smoke", lambda **kwargs: _ok("package_import_smoke"))
    monkeypatch.setattr(suite, "source_version_consistency", lambda **kwargs: _ok("version_consistency"))

    result = asyncio.run(suite.run_test_suite_async(profile="agent", path=str(tmp_path)))

    assert result["ok"] is True
    assert result["rate_limit_strategy"]["browser_required"] is False
    assert result["rate_limit_strategy"]["enabled"] is False


def test_extract_rate_limit_telemetry_aggregates_operation_and_planned_cooldowns() -> None:
    summary = {
        "steps": [
            {
                "name": "login_check",
                "details": {
                    "rate_limit_telemetry": {
                        "rate_limit_modal_detected": True,
                        "conversation_history_429_seen": True,
                        "cooldown_wait_seconds_total": 12.345,
                        "cooldown_wait_count": 1,
                        "service_rate_limit_events": [
                            {"kind": "modal_detected", "status": 429, "label": "login"}
                        ],
                    }
                },
            },
            {
                "name": "rate_limit_cooldown",
                "details": {"delay_seconds": 45.0, "reason": "after ask_question"},
            },
        ],
        "cleanup_steps": [
            {
                "name": "project_remove_cleanup",
                "details": {
                    "rate_limit_telemetry": {
                        "rate_limit_modal_detected": False,
                        "conversation_history_429_seen": False,
                        "cooldown_wait_seconds_total": 3.0,
                        "cooldown_wait_count": 1,
                        "service_rate_limit_events": [
                            {"kind": "cooldown_wait", "wait_seconds": 3.0}
                        ],
                    }
                },
            }
        ],
    }

    telemetry = suite.extract_rate_limit_telemetry(summary)

    assert telemetry["rate_limit_modal_detected"] is True
    assert telemetry["conversation_history_429_seen"] is True
    assert telemetry["cooldown_wait_seconds_total"] == 15.345
    assert telemetry["cooldown_wait_count"] == 2
    assert telemetry["planned_cooldown_wait_seconds_total"] == 45.0
    assert telemetry["planned_cooldown_wait_count"] == 1
    assert telemetry["event_count"] == 2


def test_browser_profile_reports_rate_limit_telemetry(monkeypatch) -> None:
    async def fake_run_integration(args):
        return {
            "ok": True,
            "action": "test_suite",
            "profile": "browser",
            "steps": [
                {
                    "name": "project_resolve_before_create",
                    "ok": True,
                    "duration_seconds": 0.1,
                    "details": {
                        "rate_limit_telemetry": {
                            "rate_limit_modal_detected": False,
                            "conversation_history_429_seen": True,
                            "cooldown_wait_seconds_total": 5.0,
                            "cooldown_wait_count": 1,
                            "service_rate_limit_events": [
                                {"kind": "conversation_history_rate_limit", "status": 429}
                            ],
                        }
                    },
                },
                {
                    "name": "rate_limit_cooldown",
                    "ok": True,
                    "duration_seconds": 45.0,
                    "details": {"delay_seconds": 45.0},
                },
            ],
            "cleanup_steps": [],
        }

    monkeypatch.setattr(suite, "run_integration", fake_run_integration)

    result = asyncio.run(suite.run_test_suite_async(profile="browser", rate_limit_safe=True))

    assert result["ok"] is True
    assert result["rate_limit_telemetry"]["conversation_history_429_seen"] is True
    assert result["rate_limit_telemetry"]["cooldown_wait_seconds_total"] == 5.0
    assert result["rate_limit_telemetry"]["planned_cooldown_wait_seconds_total"] == 45.0
    assert "rate_limit_modal_detected" in result["rate_limit_strategy"]["telemetry_fields"]


def test_source_version_consistency_detects_pyproject_drift(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")

    result = suite.source_version_consistency(repo_path=tmp_path)

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert any(item["name"] == "pyproject.project.version" for item in result["mismatches"])


def test_package_import_metadata_checks_zip_versions(tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad-version.zip"
    pyproject = """[project]
version = "0.0.166"

[tool.setuptools]
py-modules = ["promptbranch_version"]
"""
    with zipfile.ZipFile(bad_zip, "w") as archive:
        archive.writestr("VERSION", "v0.0.166\n")
        archive.writestr("pyproject.toml", pyproject)
        archive.writestr("promptbranch_version.py", 'PACKAGE_VERSION = "0.0.165"\n')

    result = suite._package_import_metadata(str(bad_zip), repo_path=tmp_path)

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert result["version_consistency"]["ok"] is False
    assert result["version_consistency"]["mismatches"]


def test_package_import_smoke_fails_on_runtime_version_drift(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v0.0.166\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[tool.setuptools]\npy-modules = ["promptbranch_version"]\n', encoding="utf-8")

    class Completed:
        returncode = 1
        stdout = '{"imports":[{"module":"promptbranch_version","ok":true}],"version_consistency":{"ok":false,"expected_version":"0.0.166","observations":[{"name":"mcp server_info.version","value":"0.0.164","normalized":"0.0.164"}],"missing":[],"mismatches":[{"name":"mcp server_info.version","value":"0.0.164","normalized":"0.0.164"}]}}'
        stderr = ""

    monkeypatch.setattr(suite.subprocess, "run", lambda *args, **kwargs: Completed())

    result = suite.package_import_smoke(repo_path=tmp_path, python_executable="python-test")

    assert result["ok"] is False
    assert result["version_consistency"]["mismatches"][0]["name"] == "mcp server_info.version"


def test_agent_profile_includes_src_sync_dry_run_plan(tmp_path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    (tmp_path / ".promptbranch" / "skills" / "repo-inspection").mkdir(parents=True)
    (tmp_path / ".promptbranch" / "skills" / "repo-inspection" / "SKILL.md").write_text("""---
name: repo-inspection
description: Inspect repository.
risk: read
allowed_tools:
  - filesystem.read
  - git.status
  - git.diff.summary
---
Read VERSION.
""", encoding="utf-8")

    result = suite._src_sync_dry_run_plan(repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile")

    assert result["ok"] is True
    assert result["status"] == "planned"
    assert result["mutating_actions_executed"] is False
    assert result["artifact"]["filename"].endswith("_v9.9.9.zip")
    assert result["transaction_id"]
    assert result["before_snapshot"]["repo"]["included_count"] >= 2
    assert result["collateral_checks"]["requires_before_after_source_snapshot"] is False
    assert result["transaction_plan"]["verification_plan"]["after"]
    assert not (tmp_path / ".pb_profile" / "artifacts" / "repo_v9.9.9.zip").exists()


def test_agent_profile_includes_src_sync_upload_preflight_plan(tmp_path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")

    result = suite._src_sync_upload_preflight_plan(repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile")

    assert result["ok"] is True
    assert result["status"] == "upload_confirmation_required"
    assert result["mutating_actions_executed"] is False
    assert result["project_source_mutated"] is False
    assert result["artifact"]["would_upload_source"] is True
    assert result["collateral_checks"]["requires_before_after_source_snapshot"] is True
    assert result["confirmation"]["confirm_transaction_id_flag"] == "--confirm-transaction-id"
    assert result["transaction_id"] in result["confirmation"]["confirm_command"]
    assert not (tmp_path / ".pb_profile" / "artifacts" / "repo_v9.9.9.zip").exists()


def test_package_hygiene_flags_generated_transcript(tmp_path: Path) -> None:
    from promptbranch_test_suite import _package_hygiene

    repo = tmp_path / "repo"
    repo.mkdir()
    zip_path = repo / "chatgpt_claudecode_workflow_v0.0.191.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("VERSION", "v0.0.191\n")
        archive.writestr("task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt", "transcript")

    payload = _package_hygiene(str(zip_path), repo_path=repo)

    assert payload["ok"] is False
    assert payload["status"] == "failed"
    assert payload["bad_entries"] == ["task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt"]

from __future__ import annotations

import asyncio
import os
import shutil
import time
import zipfile
from pathlib import Path

import promptbranch_test_suite as suite


def _ok(action: str = "ok", status: str = "verified") -> dict:
    return {"ok": True, "action": action, "status": status}


def _release_groups_ok() -> dict:
    return {
        "ok": True,
        "action": "release_validation_groups",
        "status": "passed",
        "missing_required_groups": [],
        "groups": {
            name: {"ok": True, "status": "passed", "group": name, "required": True}
            for name in suite.RELEASE_VALIDATION_GROUPS
        },
    }



def _preflight_ok(*, repo_path: Path, isolation_root: Path, env: dict[str, str], timeout_seconds: float = 10.0) -> dict:
    root = isolation_root.resolve()
    profile = Path(env["PROMPTBRANCH_PROFILE_DIR"]).resolve()
    return {
        "ok": True,
        "status": "isolation_preflight_passed",
        "isolation_root": str(root),
        "resolved_paths": {"profile_dir": str(profile)},
        "outside_isolation_root": {},
        "profile_inside_isolation_root": True,
        "ambient_repo_profile_lock": {
            "profile_dir": str((repo_path / ".pb_profile").resolve()),
            "lock_path": str((repo_path / ".pb_profile" / ".promptbranch-browser-profile.lock").resolve()),
            "lock_file_exists": False,
            "reachable_from_resolved_profile": False,
            "contents_read": False,
            "wait_attempted": False,
        },
        "stdout_tail": "",
        "stderr_tail": "",
    }

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
    monkeypatch.setattr(suite, "run_release_validation_groups", lambda **kwargs: _release_groups_ok())

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
        stdout = '{"imports":[{"module":"promptbranch_cli","ok":true}],"version_consistency":{"ok":true,"expected_version":"0.0.test","observations":[],"missing":[],"mismatches":[]},"runtime_identity":{"ok":true,"expected_python":"python-test","actual_python":"python-test","expected_prefix":".","actual_prefix":"."},"dependency_consistency":{"ok":true,"expected":{},"observations":[],"mismatches":[]}}'
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
    assert result["runtime_identity"]["ok"] is True
    assert result["dependency_consistency"]["ok"] is True


def test_package_import_smoke_fails_on_candidate_python_identity_drift(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v0.0.166\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[tool.setuptools]\npy-modules = ["promptbranch_version"]\n', encoding="utf-8")

    class Completed:
        returncode = 1
        stdout = '{"imports":[{"module":"promptbranch_version","ok":true}],"version_consistency":{"ok":true,"expected_version":"0.0.166","observations":[],"missing":[],"mismatches":[]},"runtime_identity":{"ok":false,"expected_python":"/candidate/bin/python","actual_python":"/shadow/bin/python","expected_prefix":"/candidate","actual_prefix":"/shadow"},"dependency_consistency":{"ok":true,"expected":{},"observations":[],"mismatches":[]}}'
        stderr = ""

    monkeypatch.setattr(suite.subprocess, "run", lambda *args, **kwargs: Completed())

    result = suite.package_import_smoke(repo_path=tmp_path, python_executable="/candidate/bin/python")

    assert result["ok"] is False
    assert result["runtime_identity"]["ok"] is False
    assert result["runtime_identity"]["actual_python"] == "/shadow/bin/python"


def test_package_import_smoke_fails_on_fastapi_starlette_drift(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v0.0.166\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["fastapi==0.128.2", "pytest==9.0.2", "starlette==0.50.0"]\n\n[tool.setuptools]\npy-modules = ["promptbranch_version"]\n',
        encoding="utf-8",
    )

    class Completed:
        returncode = 1
        stdout = '{"imports":[{"module":"promptbranch_version","ok":true}],"version_consistency":{"ok":true,"expected_version":"0.0.166","observations":[],"missing":[],"mismatches":[]},"runtime_identity":{"ok":true,"expected_python":"python-test","actual_python":"python-test","expected_prefix":".","actual_prefix":"."},"dependency_consistency":{"ok":false,"expected":{"fastapi":"0.128.2","pytest":"9.0.2","starlette":"0.50.0"},"observations":[{"name":"fastapi","expected":"0.128.2","actual":"0.128.2"},{"name":"starlette","expected":"0.50.0","actual":"0.49.0"}],"mismatches":[{"name":"starlette","expected":"0.50.0","actual":"0.49.0"}]}}'
        stderr = ""

    monkeypatch.setattr(suite.subprocess, "run", lambda *args, **kwargs: Completed())

    result = suite.package_import_smoke(repo_path=tmp_path, python_executable="python-test")

    assert result["ok"] is False
    assert result["expected_dependency_versions"] == {"fastapi": "0.128.2", "pytest": "9.0.2", "starlette": "0.50.0"}
    assert result["dependency_consistency"]["mismatches"][0]["name"] == "starlette"


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
    monkeypatch.setattr(suite, "run_release_validation_groups", lambda **kwargs: _release_groups_ok())

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
    assert telemetry["conversation_history_fetch_attempt_count"] == 0
    assert telemetry["conversation_history_fetch_skipped_count"] == 0
    assert telemetry["conversation_history_cooldown_skip_count"] == 0
    assert telemetry["navigation_noop_skip_count"] == 0
    assert telemetry["planned_cooldown_wait_seconds_total"] == 45.0
    assert telemetry["planned_cooldown_wait_count"] == 1
    assert telemetry["event_count"] == 2




def test_rate_limit_summary_none() -> None:
    summary = suite.classify_rate_limit_summary(suite._empty_rate_limit_telemetry(), suite_ok=True)

    assert summary["status"] == "none"
    assert summary["blocking"] is False
    assert summary["event_count"] == 0


def test_rate_limit_summary_recovered() -> None:
    summary = suite.classify_rate_limit_summary(
        {
            "rate_limit_modal_detected": True,
            "conversation_history_429_seen": True,
            "cooldown_wait_seconds_total": 118.5,
            "cooldown_wait_count": 1,
            "service_rate_limit_events": [{"kind": "cooldown_wait", "wait_seconds": 118.5}],
            "event_count": 1,
        },
        suite_ok=True,
    )

    assert summary["status"] == "rate_limited_recovered"
    assert summary["blocking"] is False
    assert summary["cooldown_wait_count"] == 1


def test_rate_limit_summary_excessive() -> None:
    summary = suite.classify_rate_limit_summary(
        {
            "rate_limit_modal_detected": True,
            "conversation_history_429_seen": True,
            "cooldown_wait_seconds_total": 918.189,
            "cooldown_wait_count": 8,
            "service_rate_limit_events": [{"kind": "cooldown_wait"}] * 30,
            "event_count": 30,
        },
        suite_ok=True,
    )

    assert summary["status"] == "rate_limited_excessive"
    assert summary["blocking"] is False
    assert "excessive" in summary["recommendation"]

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
    assert result["rate_limit_summary"]["status"] == "rate_limited_recovered"
    assert "rate_limit_modal_detected" in result["rate_limit_strategy"]["telemetry_fields"]
    assert "conversation_history_fetch_skipped_count" in result["rate_limit_strategy"]["telemetry_fields"]
    assert "navigation_noop_skip_count" in result["rate_limit_strategy"]["telemetry_fields"]


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
        stdout = '{"imports":[{"module":"promptbranch_version","ok":true}],"version_consistency":{"ok":false,"expected_version":"0.0.166","observations":[{"name":"mcp server_info.version","value":"0.0.164","normalized":"0.0.164"}],"missing":[],"mismatches":[{"name":"mcp server_info.version","value":"0.0.164","normalized":"0.0.164"}]},"runtime_identity":{"ok":true,"expected_python":"python-test","actual_python":"python-test","expected_prefix":".","actual_prefix":"."},"dependency_consistency":{"ok":true,"expected":{},"observations":[],"mismatches":[]}}'
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
    zip_path = repo / "chatgpt_claudecode_workflow_v0.0.201.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("VERSION", "v0.0.201\n")
        archive.writestr("task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt", "transcript")

    payload = _package_hygiene(str(zip_path), repo_path=repo)

    assert payload["ok"] is False
    assert payload["status"] == "failed"
    assert payload["bad_entries"] == ["task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt"]


def test_source_version_consistency_detects_promptbranch_version_file_drift(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "promptbranch_version.py").write_text('PACKAGE_VERSION = "9.9.8"\n', encoding="utf-8")
    (tmp_path / "docker-compose.chatgpt-service.yml").write_text("services:\n  chatgpt-service:\n    image: promptbranch-service:9.9.9\n", encoding="utf-8")

    result = suite.source_version_consistency(repo_path=tmp_path)

    assert result["ok"] is False
    assert any(item["name"] == "promptbranch_version.py.PACKAGE_VERSION" for item in result["mismatches"])



def test_source_version_consistency_ignores_compose_image_tag_and_uses_version_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(suite, "PACKAGE_VERSION", "9.9.9")
    (tmp_path / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "promptbranch_version.py").write_text('PACKAGE_VERSION = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "docker-compose.chatgpt-service.yml").write_text("services:\n  chatgpt-service:\n    image: promptbranch-service:9.9.8\n", encoding="utf-8")

    result = suite.source_version_consistency(repo_path=tmp_path)

    assert result["ok"] is True
    assert all(item["name"] != "docker_compose.chatgpt_service.image" for item in result["observations"])


def test_package_import_metadata_ignores_zip_compose_image_tag(tmp_path: Path) -> None:
    candidate = tmp_path / "compose-version-ignored.zip"
    pyproject = """[project]
version = "9.9.9"

[tool.setuptools]
py-modules = ["promptbranch_version"]
"""
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr("VERSION", "v9.9.9\n")
        archive.writestr("pyproject.toml", pyproject)
        archive.writestr("promptbranch_version.py", 'PACKAGE_VERSION = "9.9.9"\n')
        archive.writestr("docker-compose.chatgpt-service.yml", "services:\n  chatgpt-service:\n    image: promptbranch-service:9.9.8\n")

    result = suite._package_import_metadata(str(candidate), repo_path=tmp_path)

    assert result["version_consistency"]["ok"] is True
    assert all(item["name"] != "zip.docker_compose.chatgpt_service.image" for item in result["version_consistency"]["observations"])


def test_artifact_roundtrip_smoke_is_deterministic_and_docker_safe(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.9\n", encoding="utf-8")

    result = suite.artifact_roundtrip_smoke(repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile", run_id="UNIT")

    assert result["ok"] is True
    assert result["status"] == "verified"
    assert result["profile"] == "artifact-roundtrip"
    assert result["browser_required"] is False
    assert result["chatgpt_required"] is False
    assert result["network_required"] is False
    assert result["docker_safe"] is True
    assert result["mutating_actions_executed"] is False
    names = [step["name"] for step in result["steps"]]
    assert "parse_valid_reply" in names
    assert "classify_expected_candidate" in names
    assert "smoke_zip_verify" in names
    assert "malformed_reply_fails_closed" in names
    assert "wrong_filename_fails_closed" in names
    assert "wrong_content_fails_closed" in names
    assert "wrapper_folder_fails_closed" in names


def test_agent_profile_includes_artifact_roundtrip(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v0.0.test\n", encoding="utf-8")
    (tmp_path / ".promptbranch" / "skills" / "repo-inspection").mkdir(parents=True)

    monkeypatch.setattr(suite, "mcp_host_smoke", lambda **kwargs: _ok("mcp_host_smoke"))
    monkeypatch.setattr(suite, "mcp_tool_call_via_stdio", lambda *args, **kwargs: _ok("mcp_tool_call"))
    monkeypatch.setattr(suite, "skill_list", lambda **kwargs: _ok("skill_list"))
    monkeypatch.setattr(suite, "skill_show", lambda *args, **kwargs: _ok("skill_show"))
    monkeypatch.setattr(suite, "skill_validate", lambda *args, **kwargs: _ok("skill_validate", "valid"))
    monkeypatch.setattr(suite, "agent_tool_call", lambda *args, **kwargs: _ok("agent_tool_call"))
    monkeypatch.setattr(suite, "agent_summarize_log", lambda *args, **kwargs: _ok("agent_summarize_log"))
    monkeypatch.setattr(suite, "package_import_smoke", lambda **kwargs: _ok("package_import_smoke"))
    monkeypatch.setattr(suite, "source_version_consistency", lambda **kwargs: _ok("version_consistency"))

    def fake_agent_run(request: str, **kwargs) -> dict:
        if request in {"sync sources", "create artifact release", "run pytest"}:
            return {"ok": False, "action": "agent_run", "status": "risk_rejected"}
        return _ok("agent_run")

    monkeypatch.setattr(suite, "agent_run", fake_agent_run)

    result = suite._run_agent_profile_sync(repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile")

    names = [step["name"] for step in result["steps"]]
    assert "artifact_roundtrip" in names
    artifact_step = next(step for step in result["steps"] if step["name"] == "artifact_roundtrip")
    assert artifact_step["ok"] is True
    assert artifact_step["payload"]["docker_safe"] is True


def test_browser_profile_summary_counts_cleanup_failures(monkeypatch) -> None:
    async def fake_run_integration(args):
        return {
            "ok": False,
            "action": "test_suite",
            "profile": "browser",
            "steps": [{"name": "login_check", "ok": True, "duration_seconds": 0.1, "details": {"ok": True}}],
            "cleanup_steps": [
                {
                    "name": "project_remove_cleanup",
                    "ok": False,
                    "duration_seconds": 30.0,
                    "details": {
                        "status": "browser_profile_busy",
                        "error": "browser profile is busy",
                    },
                }
            ],
        }

    monkeypatch.setattr(suite, "run_integration", fake_run_integration)

    result = asyncio.run(suite.run_test_suite_async(profile="browser", rate_limit_safe=True))

    assert result["ok"] is False
    assert result["failure_count"] == 1
    assert result["failed_steps"][0]["scope"] == "cleanup"
    assert result["failed_steps"][0]["name"] == "project_remove_cleanup"
    assert result["failed_steps"][0]["status"] == "browser_profile_busy"



def test_release_validation_group_manifest_contains_required_release_gate_groups() -> None:
    manifest = suite.release_validation_group_manifest()
    required = {
        "project_control_surface",
        "application_architecture_structural",
        "application_architecture_registry",
        "application_architecture_executable",
        "version_surface",
        "artifact_json_contracts",
        "repo_project_registry",
        "browser_scheduler_source_lifecycle",
        "release_lifecycle_plan",
        "execution_envelope_validation_gate",
        "compileall",
    }
    assert required.issubset(manifest)
    for name in required:
        assert manifest[name]["required"] is True
        assert manifest[name]["command"]



def test_release_validation_groups_default_to_current_promptbranch_python(monkeypatch) -> None:
    monkeypatch.delenv(suite.RELEASE_VALIDATION_PYTHON_ENV, raising=False)
    monkeypatch.delenv("PROMPTBRANCH_CANDIDATE_PYTHON", raising=False)
    manifest = suite.release_validation_group_manifest()

    for group in suite.RELEASE_VALIDATION_GROUPS:
        assert manifest[group]["command"][0] == suite.sys.executable
        assert suite.RELEASE_VALIDATION_PYTHON_PLACEHOLDER not in manifest[group]["command"]


def test_release_validation_groups_support_python_override(monkeypatch) -> None:
    monkeypatch.setenv(suite.RELEASE_VALIDATION_PYTHON_ENV, "/opt/project-python")
    manifest = suite.release_validation_group_manifest()

    assert manifest["project_control_surface"]["command"][0] == "/opt/project-python"
    assert manifest["artifact_json_contracts"]["command"][0] == "/opt/project-python"


def test_run_release_validation_group_resolves_python_override(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Completed()

    monkeypatch.setenv(suite.RELEASE_VALIDATION_PYTHON_ENV, "/opt/project-python")
    monkeypatch.setattr(suite, "_release_validation_isolation_preflight", _preflight_ok)
    monkeypatch.setattr(suite.subprocess, "run", fake_run)

    result = suite._run_release_validation_group(
        "demo",
        {
            "required": True,
            "description": "demo",
            "command": [suite.RELEASE_VALIDATION_PYTHON_PLACEHOLDER, "-m", "pytest"],
        },
        repo_path=tmp_path,
    )

    assert result["ok"] is True
    assert captured["command"] == ["/opt/project-python", "-m", "pytest"]


def test_run_release_validation_group_disables_ambient_pytest_plugins(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["env"] = kwargs.get("env")

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Completed()

    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)
    monkeypatch.setattr(suite, "_release_validation_isolation_preflight", _preflight_ok)
    monkeypatch.setattr(suite.subprocess, "run", fake_run)

    result = suite._run_release_validation_group(
        "demo",
        {
            "required": True,
            "description": "demo",
            "command": [suite.RELEASE_VALIDATION_PYTHON_PLACEHOLDER, "-m", "pytest"],
        },
        repo_path=tmp_path,
    )

    assert result["ok"] is True
    assert captured["env"]["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"

def test_agent_profile_reports_release_validation_groups(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v0.0.test\n", encoding="utf-8")
    (tmp_path / ".promptbranch" / "skills" / "repo-inspection").mkdir(parents=True)

    monkeypatch.setattr(suite, "mcp_host_smoke", lambda **kwargs: _ok("mcp_host_smoke"))
    monkeypatch.setattr(suite, "mcp_tool_call_via_stdio", lambda *args, **kwargs: _ok("mcp_tool_call"))
    monkeypatch.setattr(suite, "skill_list", lambda **kwargs: _ok("skill_list"))
    monkeypatch.setattr(suite, "skill_show", lambda *args, **kwargs: _ok("skill_show"))
    monkeypatch.setattr(suite, "skill_validate", lambda *args, **kwargs: _ok("skill_validate", "valid"))
    monkeypatch.setattr(suite, "agent_tool_call", lambda *args, **kwargs: _ok("agent_tool_call"))
    monkeypatch.setattr(suite, "agent_run", lambda *args, **kwargs: {"ok": False, "action": "agent_run", "status": "risk_rejected"} if args and args[0] in {"sync sources", "create artifact release", "run pytest"} else _ok("agent_run"))
    monkeypatch.setattr(suite, "agent_summarize_log", lambda path, **kwargs: {"ok": False, "status": "path_outside_repo"} if str(path).startswith("/") else _ok("agent_summarize_log"))
    monkeypatch.setattr(suite, "package_import_smoke", lambda **kwargs: _ok("package_import_smoke"))
    monkeypatch.setattr(suite, "source_version_consistency", lambda **kwargs: _ok("version_consistency"))
    monkeypatch.setattr(suite, "run_release_validation_groups", lambda **kwargs: _release_groups_ok())

    result = asyncio.run(suite.run_test_suite_async(profile="agent", path=str(tmp_path)))

    assert result["ok"] is True
    groups = result["release_validation_groups"]
    assert groups["ok"] is True
    assert groups["missing_required_groups"] == []
    assert set(suite.RELEASE_VALIDATION_GROUPS).issubset(groups["groups"])
    assert any(step["name"] == "release_validation_groups" for step in result["steps"])


def test_browser_scheduler_release_validation_group_uses_short_timeout() -> None:
    import promptbranch_test_suite as suite

    manifest = suite.release_validation_group_manifest()
    group = manifest["browser_scheduler_source_lifecycle"]

    assert group["timeout_seconds"] == 300.0


def test_browser_scheduler_release_validation_group_uses_explicit_fast_nodeids() -> None:
    import promptbranch_test_suite as suite

    manifest = suite.release_validation_group_manifest()
    command = manifest["browser_scheduler_source_lifecycle"]["command"]

    assert "-k" not in command
    assert "cleanup" not in " ".join(command)
    assert any("test_source_remove_waits_behind_source_list_with_same_profile" in item for item in command)
    assert any("test_src_add_promotes_browser_profile_busy_to_top_level_payload" in item for item in command)


def test_release_validation_groups_skip_duplicate_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(suite.RELEASE_VALIDATION_SKIP_DUPLICATE_ENV, "1")

    result = suite.run_release_validation_groups(repo_path=tmp_path)

    assert result["ok"] is True
    assert result["status"] == "skipped_duplicate_already_passed"
    assert result["missing_required_groups"] == []
    assert result["duplicate_skip"] is True
    assert result["groups"]
    assert all(group["status"] == "skipped_duplicate_already_passed" for group in result["groups"].values())


def test_release_validation_group_strips_browser_service_env(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        captured["env"] = kwargs.get("env")
        return Completed()

    monkeypatch.setenv("CHATGPT_SERVICE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CHATGPT_EMAIL", "operator@example.test")
    monkeypatch.setenv("CHATGPT_PROJECT_URL", "https://chatgpt.com/g/g-p-live/project")
    monkeypatch.setenv("PROMPTBRANCH_SERVICE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("PROMPTBRANCH_SERVICE_IMAGE", "promptbranch-service:live")
    monkeypatch.setenv("PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SEED_DIR", "./.pb_profile_local_debug")
    monkeypatch.setenv("PYTEST_ADDOPTS", "--maxfail=1")
    monkeypatch.setattr(suite, "_release_validation_isolation_preflight", _preflight_ok)
    monkeypatch.setattr(suite.subprocess, "run", fake_run)

    spec = {"required": True, "description": "unit", "command": ["python3", "-c", "pass"]}
    result = suite._run_release_validation_group("unit", spec, repo_path=tmp_path)

    assert result["ok"] is True
    assert not any(key.startswith("CHATGPT_") for key in captured["env"])
    assert "PROMPTBRANCH_SERVICE_BASE_URL" not in captured["env"]
    assert "PROMPTBRANCH_SERVICE_IMAGE" not in captured["env"]
    assert "PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SEED_DIR" not in captured["env"]
    assert "PYTEST_ADDOPTS" not in captured["env"]
    assert captured["env"]["PROMPTBRANCH_RELEASE_VALIDATION_ISOLATED"] == "1"
    isolation_root = Path(captured["env"]["PROMPTBRANCH_RELEASE_VALIDATION_ROOT"])
    for key in (
        "HOME",
        "TMPDIR",
        "XDG_CONFIG_HOME",
        "XDG_STATE_HOME",
        "PROMPTBRANCH_PROFILE_DIR",
        "PROMPTBRANCH_PROJECT_STATE_HOME",
        "PROMPTBRANCH_PROJECT_CONFIG_HOME",
        "PROMPTBRANCH_PROJECT_CACHE_PATH",
    ):
        assert Path(captured["env"][key]).resolve().is_relative_to(isolation_root.resolve())


def test_browser_scheduler_release_validation_group_uses_nodeid_progress() -> None:
    manifest = suite.release_validation_group_manifest()
    group = manifest["browser_scheduler_source_lifecycle"]

    assert group["nodeid_progress"] is True


def test_release_validation_group_nodeid_progress_reports_completed_nodeids(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    envs: list[dict[str, str]] = []

    class Completed:
        returncode = 0
        stdout = "passed node\n"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(list(command))
        envs.append(dict(kwargs.get("env") or {}))
        return Completed()

    monkeypatch.setattr(suite, "_release_validation_isolation_preflight", _preflight_ok)
    monkeypatch.setattr(suite.subprocess, "run", fake_run)

    result = suite._run_release_validation_group(
        "browser_scheduler_source_lifecycle",
        {
            "required": True,
            "description": "nodeid progress demo",
            "timeout_seconds": 300.0,
            "nodeid_progress": True,
            "command": [
                suite.RELEASE_VALIDATION_PYTHON_PLACEHOLDER,
                "-m",
                "pytest",
                "-q",
                "tests/test_demo.py::test_one",
                "tests/test_demo.py::test_two",
            ],
        },
        repo_path=tmp_path,
    )

    assert result["ok"] is True
    assert result["status"] == "passed"
    assert result["command_mode"] == "per_nodeid_progress"
    assert result["completed_nodeids"] == ["tests/test_demo.py::test_one", "tests/test_demo.py::test_two"]
    assert result["failed_nodeids"] == []
    assert result["timed_out_nodeids"] == []
    assert calls == [
        [suite.sys.executable, "-m", "pytest", "-q", "tests/test_demo.py::test_one"],
        [suite.sys.executable, "-m", "pytest", "-q", "tests/test_demo.py::test_two"],
    ]
    assert envs[0]["PROMPTBRANCH_RELEASE_VALIDATION_NODEID"] == "tests/test_demo.py::test_one"
    assert envs[1]["PROMPTBRANCH_RELEASE_VALIDATION_NODEID"] == "tests/test_demo.py::test_two"
    assert envs[0]["HOME"] != envs[1]["HOME"]
    assert envs[0]["TMPDIR"] != envs[1]["TMPDIR"]
    assert result["environment_isolation"]["enabled"] is True
    assert result["environment_isolation"]["mode"] == "explicit_runtime_path_authority_per_nodeid"
    assert all(item["ok"] for item in result["environment_isolation"]["node_preflights"])
    assert envs[0]["PROMPTBRANCH_PROFILE_DIR"].startswith(result["environment_isolation"]["root"])
    assert envs[0]["XDG_STATE_HOME"].startswith(result["environment_isolation"]["root"])
    assert envs[0]["PROMPTBRANCH_PROJECT_STATE_HOME"].startswith(result["environment_isolation"]["root"])
    assert "release_validation_group_progress: group=browser_scheduler_source_lifecycle index=1/2 nodeid=tests/test_demo.py::test_one" in result["stdout_tail"]


def test_release_validation_group_nodeid_progress_timeout_reports_active_nodeid(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, **kwargs):
        if command[-1].endswith("test_two"):
            raise suite.subprocess.TimeoutExpired(command, timeout=kwargs.get("timeout"), output="started two\n", stderr="waiting\n")

        class Completed:
            returncode = 0
            stdout = "passed one\n"
            stderr = ""

        return Completed()

    monkeypatch.setattr(suite, "_release_validation_isolation_preflight", _preflight_ok)
    monkeypatch.setattr(suite.subprocess, "run", fake_run)

    result = suite._run_release_validation_group(
        "browser_scheduler_source_lifecycle",
        {
            "required": True,
            "description": "nodeid timeout demo",
            "timeout_seconds": 300.0,
            "nodeid_progress": True,
            "command": [
                suite.RELEASE_VALIDATION_PYTHON_PLACEHOLDER,
                "-m",
                "pytest",
                "-q",
                "tests/test_demo.py::test_one",
                "tests/test_demo.py::test_two",
            ],
        },
        repo_path=tmp_path,
    )

    assert result["ok"] is False
    assert result["status"] == "timeout"
    assert result["command_mode"] == "per_nodeid_progress"
    assert result["active_nodeid"] == "tests/test_demo.py::test_two"
    assert result["completed_nodeids"] == ["tests/test_demo.py::test_one"]
    assert result["failed_nodeids"] == []
    assert result["timed_out_nodeids"] == ["tests/test_demo.py::test_two"]
    assert result["nodeid_results"][-1]["status"] == "timeout"
    assert "release_validation_group_progress: group=browser_scheduler_source_lifecycle index=2/2 nodeid=tests/test_demo.py::test_two" in result["stdout_tail"]


def test_release_validation_scheduler_node_is_hermetic_from_real_ambient_lock(monkeypatch, tmp_path: Path) -> None:
    source_repo = Path(__file__).resolve().parents[1]
    repo = tmp_path / "repo"
    shutil.copytree(
        source_repo,
        repo,
        ignore=shutil.ignore_patterns(".git", ".pb_profile", ".pytest_cache", "__pycache__", "*.pyc", "*.zip"),
    )
    ambient_profile = repo / ".pb_profile"
    ambient_profile.mkdir()
    ambient_lock = ambient_profile / ".promptbranch-browser-profile.lock"
    ambient_lock.write_text("pid=123\noperation=add_project_source\n", encoding="utf-8")

    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args, **kwargs):
        if path.resolve() == ambient_lock.resolve():
            raise AssertionError("ambient repository browser lock contents must not be read")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    started = time.monotonic()
    result = suite._run_release_validation_group(
        "browser_scheduler_source_lifecycle",
        {
            "required": True,
            "description": "exact scheduler isolation regression",
            "timeout_seconds": 300.0,
            "nodeid_progress": True,
            "command": [
                suite.RELEASE_VALIDATION_PYTHON_PLACEHOLDER,
                "-m",
                "pytest",
                "-q",
                "tests/test_promptbranch_automation_service.py::test_project_remove_is_frozen_before_profile_scheduler",
            ],
        },
        repo_path=repo,
    )
    elapsed = time.monotonic() - started

    assert result["ok"] is True
    assert elapsed < 30.0
    preflight = result["environment_isolation"]["node_preflights"][0]
    assert preflight["profile_inside_isolation_root"] is True
    assert preflight["ambient_repo_profile_lock"]["lock_file_exists"] is True
    assert preflight["ambient_repo_profile_lock"]["reachable_from_resolved_profile"] is False
    assert preflight["ambient_repo_profile_lock"]["contents_read"] is False
    assert preflight["ambient_repo_profile_lock"]["wait_attempted"] is False
    assert result["completed_nodeids"] == [
        "tests/test_promptbranch_automation_service.py::test_project_remove_is_frozen_before_profile_scheduler"
    ]


def test_release_validation_fails_before_node_when_repo_profile_is_resolved(monkeypatch, tmp_path: Path) -> None:
    source_repo = Path(__file__).resolve().parents[1]
    repo = tmp_path / "repo"
    shutil.copytree(
        source_repo,
        repo,
        ignore=shutil.ignore_patterns(".git", ".pb_profile", ".pytest_cache", "__pycache__", "*.pyc", "*.zip"),
    )
    ambient_profile = repo / ".pb_profile"
    ambient_profile.mkdir()
    (ambient_profile / ".promptbranch-browser-profile.lock").write_text(
        "pid=123\noperation=add_project_source\n", encoding="utf-8"
    )
    original_env_builder = suite._release_validation_group_env
    real_run = suite.subprocess.run
    calls: list[list[str]] = []

    def poisoned_env(*, isolation_root: Path, nodeid: str | None = None) -> dict[str, str]:
        env = original_env_builder(isolation_root=isolation_root, nodeid=nodeid)
        env["PROMPTBRANCH_PROFILE_DIR"] = str(ambient_profile)
        return env

    def tracked_run(command, **kwargs):
        calls.append(list(command))
        return real_run(command, **kwargs)

    monkeypatch.setattr(suite, "_release_validation_group_env", poisoned_env)
    monkeypatch.setattr(suite.subprocess, "run", tracked_run)
    result = suite._run_release_validation_group(
        "browser_scheduler_source_lifecycle",
        {
            "required": True,
            "description": "fail before ambient lock reachability",
            "timeout_seconds": 300.0,
            "nodeid_progress": True,
            "command": [
                suite.RELEASE_VALIDATION_PYTHON_PLACEHOLDER,
                "-m",
                "pytest",
                "-q",
                "tests/test_promptbranch_automation_service.py::test_project_remove_is_frozen_before_profile_scheduler",
            ],
        },
        repo_path=repo,
    )

    assert result["ok"] is False
    assert result["status"] == "isolation_preflight_failed"
    assert len(calls) == 1
    preflight = result["environment_isolation"]["node_preflights"][0]
    assert preflight["ambient_repo_profile_lock"]["reachable_from_resolved_profile"] is True
    assert preflight["outside_isolation_root"]["profile_dir"] == str(ambient_profile.resolve())


def test_src_sync_dry_run_missing_registry_is_read_only_planned(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.10\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    profile = tmp_path / ".pb_profile"

    result = suite._src_sync_dry_run_plan(repo_path=tmp_path, profile_dir=profile)

    assert result["ok"] is True
    assert result["status"] == "planned"
    assert result["registry_status"] == "missing"
    registry = result["before_snapshot"]["artifact_registry"]
    assert registry["status"] == "artifact_registry_missing"
    assert registry["artifact_count"] == 0
    assert result["mutating_actions_executed"] is False
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_src_sync_upload_preflight_missing_registry_requires_confirmation_without_mutation(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.10\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    profile = tmp_path / ".pb_profile"

    result = suite._src_sync_upload_preflight_plan(repo_path=tmp_path, profile_dir=profile)

    assert result["ok"] is True
    assert result["status"] == "upload_confirmation_required"
    assert result["registry_status"] == "missing"
    assert result["mutating_actions_executed"] is False
    assert result["project_source_mutated"] is False
    assert result["confirmation"]["required"] is True
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_src_sync_preflight_invalid_registry_is_structured_failed_step(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.10\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    profile = tmp_path / ".pb_profile"
    profile.mkdir()
    (profile / "promptbranch_artifacts.json").write_text("{broken", encoding="utf-8")

    dry_run = suite._src_sync_dry_run_plan(repo_path=tmp_path, profile_dir=profile)
    upload = suite._src_sync_upload_preflight_plan(repo_path=tmp_path, profile_dir=profile)

    assert dry_run["ok"] is False
    assert dry_run["status"] == "preflight_failed"
    assert dry_run["registry_status"] == "artifact_registry_invalid"
    assert dry_run["mutating_actions_executed"] is False
    assert upload["ok"] is False
    assert upload["status"] == "preflight_failed"
    assert upload["registry_status"] == "artifact_registry_invalid"
    assert upload["project_source_mutated"] is False


def test_agent_profile_with_missing_registry_completes_suite_json(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.10\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    monkeypatch.setattr(suite, "mcp_host_smoke", lambda **kwargs: _ok("mcp_host_smoke"))
    monkeypatch.setattr(suite, "mcp_tool_call_via_stdio", lambda *args, **kwargs: _ok("mcp_tool_call"))
    monkeypatch.setattr(suite, "agent_run", lambda *args, **kwargs: _ok("agent_run"))
    monkeypatch.setattr(suite, "skill_list", lambda **kwargs: _ok("skill_list"))
    monkeypatch.setattr(suite, "skill_show", lambda *args, **kwargs: _ok("skill_show"))
    monkeypatch.setattr(suite, "skill_validate", lambda *args, **kwargs: _ok("skill_validate"))
    monkeypatch.setattr(suite, "agent_tool_call", lambda *args, **kwargs: _ok("agent_tool_call"))
    monkeypatch.setattr(suite, "agent_summarize_log", lambda *args, **kwargs: _ok("agent_summarize_log"))
    monkeypatch.setattr(suite, "source_version_consistency", lambda **kwargs: _ok("version_consistency"))
    monkeypatch.setattr(suite, "_package_import_metadata", lambda *args, **kwargs: _ok("package_import_metadata"))
    monkeypatch.setattr(suite, "package_import_smoke", lambda **kwargs: _ok("package_import_smoke"))
    monkeypatch.setattr(suite, "artifact_roundtrip_smoke", lambda **kwargs: _ok("artifact_roundtrip"))
    monkeypatch.setattr(suite, "run_release_validation_groups", lambda **kwargs: _release_groups_ok())
    monkeypatch.setattr(suite, "_package_hygiene", lambda *args, **kwargs: _ok("package_hygiene"))

    result = suite._run_agent_profile_sync(repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile")

    assert result["action"] == "test_suite"
    assert result["profile"] == "agent"
    dry_run = next(step for step in result["steps"] if step["name"] == "src_sync_dry_run_plan")
    upload = next(step for step in result["steps"] if step["name"] == "src_sync_upload_preflight_plan")
    assert dry_run["payload"]["registry_status"] == "missing"
    assert upload["payload"]["registry_status"] == "missing"


def test_full_profile_with_missing_registry_emits_complete_suite(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.10\n", encoding="utf-8")
    browser = {"ok": True, "action": "test_suite", "profile": "browser", "steps": []}
    agent = {"ok": True, "action": "test_suite", "profile": "agent", "steps": [], "safety": {"write_tools_blocked": True}}

    async def fake_run_integration(args):
        return browser

    monkeypatch.setattr(suite, "run_integration", fake_run_integration)
    monkeypatch.setattr(suite, "_run_agent_profile_sync", lambda **kwargs: agent)

    result = asyncio.run(suite.run_test_suite_async(profile="full", path=tmp_path, profile_dir=tmp_path / ".pb_profile"))

    assert result["action"] == "test_suite"
    assert result["profile"] == "full"
    assert result["browser"] is browser
    assert result["agent"] is agent
    assert "failure_count" in result
    assert "failed_steps" in result


def test_release_validation_manifest_requires_sandbox_mutation_rollback_gate() -> None:
    manifest = suite.release_validation_group_manifest()
    gate = manifest["sandbox_mutation_rollback_gate"]
    assert gate["required"] is True
    assert gate["timeout_seconds"] == 180.0
    assert gate["command"] == [
        suite.sys.executable,
        "scripts/verify-sandbox-mutation-rollback-release-gate.py",
        "--repo",
        ".",
    ]


def test_release_validation_manifest_requires_execution_envelope_validation_gate() -> None:
    manifest = suite.release_validation_group_manifest()
    gate = manifest["execution_envelope_validation_gate"]
    assert gate["required"] is True
    assert gate["timeout_seconds"] == 120.0
    assert gate["command"] == [
        suite.sys.executable,
        "promptbranch_cli.py",
        "loop",
        "execution-envelope-validation",
        "--target",
        "examples/loop-targets/sandboxed-file-mutation-target.json",
        "--json",
    ]


def test_project_source_file_reliability_profile_runs_independent_scenarios(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "VERSION").write_text("v0.1.108.1\n", encoding="utf-8")
    calls: list[dict] = []

    async def fake_run_integration(args):
        calls.append({
            "project_name": args.project_name,
            "only": list(args.only),
            "strict_remove_ui": args.strict_remove_ui,
            "keep_project": args.keep_project,
        })
        if args.project_name.endswith("staged-overwrite"):
            return {
                "ok": False,
                "steps": [],
                "failed_steps": [{
                    "section": "browser",
                    "scope": "main",
                    "name": "project_source_overwrite_file",
                    "status": "source_overwrite_upload_not_started",
                }],
                "failure_count": 1,
            }
        return {
            "ok": True,
            "steps": [],
            "failed_steps": [],
            "failure_count": 0,
        }

    monkeypatch.setattr(suite, "run_integration", fake_run_integration)

    result = asyncio.run(
        suite.run_project_source_file_reliability_async(
            path=str(tmp_path),
            project_name="itest-focused",
            profile_dir=str(tmp_path / ".pb_profile"),
        )
    )

    assert len(calls) == 2
    assert calls[0]["project_name"] == "itest-focused-staged-overwrite"
    assert calls[0]["only"] == ["project_ensure,source_add_file,source_overwrite_file"]
    assert calls[0]["keep_project"] is True
    assert calls[1]["project_name"] == "itest-focused-removal-proof"
    assert calls[1]["only"] == ["project_ensure,source_add_file,source_remove_file"]
    assert calls[1]["strict_remove_ui"] is True
    assert result["ok"] is False
    assert result["profile"] == "project-source-file-reliability"
    assert result["scenarios"]["removal_proof"]["ok"] is True
    assert result["failure_count"] == 1
    assert result["full_release_validation_required"] is True


def test_progress_ledger_reports_counts_percent_and_eta(capsys) -> None:
    ledger = suite.TestProgressLedger(("browser.one", "browser.two"), enabled=True)
    ledger.start("browser.one")
    ledger.finish("browser.one", ok=True)
    output = capsys.readouterr().out
    assert "pb_test_progress:" in output
    assert "current=browser.one" in output
    assert "completed=1/2" in output
    assert "passed=1" in output
    assert "failed=0" in output
    assert "percent=50.0" in output
    assert "active_remaining=" in output
    assert "eta_approx=" in output
    assert "eta_range=" in output
    assert "eta_confidence=" in output
    assert "eta_basis=" in output
    snapshot = ledger.snapshot()
    assert snapshot["completed_units"] == 1
    assert snapshot["percent_complete"] == 50.0


def test_release_validation_groups_fail_fast_skips_remaining(monkeypatch, tmp_path: Path) -> None:
    manifest = {
        "first": {"required": True, "description": "first", "command": ["python3", "-V"]},
        "second": {"required": True, "description": "second", "command": ["python3", "-V"]},
        "third": {"required": True, "description": "third", "command": ["python3", "-V"]},
    }
    calls: list[str] = []

    def fake_run(group_name, spec, *, repo_path, timeout_seconds=600.0):
        calls.append(group_name)
        return {
            "ok": False,
            "status": "failed",
            "group": group_name,
            "required": True,
        }

    monkeypatch.setattr(suite, "RELEASE_VALIDATION_GROUPS", manifest)
    monkeypatch.setattr(suite, "_run_release_validation_group", fake_run)
    progress = suite.TestProgressLedger(tuple(f"validation.{name}" for name in manifest), enabled=False)
    result = suite.run_release_validation_groups(repo_path=tmp_path, progress=progress, fail_fast=True)

    assert calls == ["first"]
    assert result["ok"] is False
    assert result["groups"]["first"]["status"] == "failed"
    assert result["groups"]["second"]["status"] == "skipped_fail_fast"
    assert result["groups"]["third"]["status"] == "skipped_fail_fast"
    snapshot = progress.snapshot()
    assert snapshot["failed_units"] == 1
    assert snapshot["skipped_units"] == 2
    assert snapshot["percent_complete"] == 100.0


def test_full_profile_fail_fast_skips_agent_after_browser_failure(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.11\n", encoding="utf-8")

    async def fake_run_integration(args):
        args._progress_callback(event="started", step_name="mcp_smoke", ok=None, duration_seconds=0.0)
        args._progress_callback(event="finished", step_name="mcp_smoke", ok=False, duration_seconds=0.1)
        return {
            "ok": False,
            "action": "test_suite",
            "profile": "browser",
            "steps": [{"name": "mcp_smoke", "ok": False, "details": {"status": "failed"}}],
        }

    def forbidden_agent(**kwargs):
        raise AssertionError("agent profile must not run after browser failure in fail-fast mode")

    monkeypatch.setattr(suite, "run_integration", fake_run_integration)
    monkeypatch.setattr(suite, "_run_agent_profile_sync", forbidden_agent)

    result = asyncio.run(
        suite.run_test_suite_async(
            profile="full",
            path=tmp_path,
            profile_dir=tmp_path / ".pb_profile",
            only=["mcp_smoke"],
            fail_fast=True,
            progress=False,
        )
    )

    assert result["ok"] is False
    assert result["agent"]["status"] == "skipped_fail_fast"
    assert result["progress"]["fail_fast"] is True
    assert result["progress"]["percent_complete"] == 100.0
    assert result["progress"]["failed_units"] == 1
    assert result["progress"]["skipped_units"] > 0

def test_browser_profile_fail_fast_marks_remaining_browser_units_skipped(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v9.9.12\n", encoding="utf-8")

    async def fake_run_integration(args):
        args._progress_callback(event="started", step_name="mcp_smoke", ok=None, duration_seconds=0.0)
        args._progress_callback(event="finished", step_name="mcp_smoke", ok=False, duration_seconds=0.1)
        return {
            "ok": False,
            "status": "failed_fast",
            "fail_fast_triggered": True,
            "fail_fast_step": "mcp_smoke",
            "steps": [{"name": "mcp_smoke", "ok": False, "details": {"status": "failed"}}],
        }

    monkeypatch.setattr(suite, "run_integration", fake_run_integration)

    result = asyncio.run(
        suite.run_test_suite_async(
            profile="browser",
            path=tmp_path,
            profile_dir=tmp_path / ".pb_profile",
            only=["mcp_smoke,login_check"],
            fail_fast=True,
            progress=False,
        )
    )

    assert result["ok"] is False
    assert result["progress"]["percent_complete"] == 100.0
    assert result["progress"]["failed_units"] == 1
    assert result["progress"]["skipped_units"] == 1
    assert result["progress"]["states"]["browser.mcp_smoke"] == "failed"
    assert result["progress"]["states"]["browser.login_check"] == "skipped:browser_failure"

def test_release_validation_runner_preflight_verifies_pinned_pytest(monkeypatch) -> None:
    monkeypatch.setenv(suite.RELEASE_VALIDATION_PYTHON_ENV, suite.sys.executable)
    monkeypatch.setenv(suite.RELEASE_VALIDATION_PYTEST_VERSION_ENV, "9.0.2")

    result = suite.release_validation_runner_preflight()

    assert result["ok"] is True, result
    assert result["status"] == "release_validation_runner_verified"
    assert result["checks"]["python_executable_match"] is True
    assert result["checks"]["pytest_version_match"] is True
    assert result["checks"]["pytest_module_inside_python_prefix"] is True


def test_release_validation_runner_preflight_fails_on_pytest_version_drift(monkeypatch) -> None:
    monkeypatch.setenv(suite.RELEASE_VALIDATION_PYTHON_ENV, suite.sys.executable)
    monkeypatch.setenv(suite.RELEASE_VALIDATION_PYTEST_VERSION_ENV, "0.0.0")

    result = suite.release_validation_runner_preflight()

    assert result["ok"] is False
    assert result["status"] == "release_validation_runner_invalid"
    assert result["checks"]["pytest_version_match"] is False


def test_release_validation_groups_fail_closed_before_first_group_on_runner_drift(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        suite,
        "release_validation_runner_preflight",
        lambda: {"ok": False, "status": "release_validation_runner_invalid"},
    )

    result = suite.run_release_validation_groups(repo_path=tmp_path, fail_fast=True)

    assert result["ok"] is False
    assert result["status"] == "runner_preflight_failed"
    assert result["missing_required_groups"]
    assert all(
        payload["status"] == "skipped_runner_preflight_failed"
        for payload in result["groups"].values()
    )

def test_package_import_smoke_fails_on_pytest_drift(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v0.0.166\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        """[project]
dependencies = ["fastapi==0.128.2", "pytest==9.0.2", "starlette==0.50.0"]

[tool.setuptools]
py-modules = ["promptbranch_version"]
""",
        encoding="utf-8",
    )

    class Completed:
        returncode = 1
        stdout = '{"imports":[{"module":"promptbranch_version","ok":true}],"version_consistency":{"ok":true,"expected_version":"0.0.166","observations":[],"missing":[],"mismatches":[]},"runtime_identity":{"ok":true,"expected_python":"python-test","actual_python":"python-test","expected_prefix":".","actual_prefix":"."},"dependency_consistency":{"ok":false,"expected":{"fastapi":"0.128.2","pytest":"9.0.2","starlette":"0.50.0"},"observations":[{"name":"pytest","expected":"9.0.2","actual":"8.4.1"}],"mismatches":[{"name":"pytest","expected":"9.0.2","actual":"8.4.1"}]}}'
        stderr = ""

    monkeypatch.setattr(suite.subprocess, "run", lambda *args, **kwargs: Completed())

    result = suite.package_import_smoke(repo_path=tmp_path, python_executable="python-test")

    assert result["ok"] is False
    assert result["dependency_consistency"]["mismatches"][0]["name"] == "pytest"

def test_release_validation_runner_preserves_candidate_launcher_path() -> None:
    source = Path(suite.__file__).read_text(encoding="utf-8")
    assert 'Path(release_validation_python()).expanduser().absolute()' in source
    assert 'Path(release_validation_python()).expanduser().resolve()' not in source
    assert 'Path(sys.executable).absolute()' in source


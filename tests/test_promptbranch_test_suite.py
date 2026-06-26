from __future__ import annotations

import asyncio
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
        "version_surface",
        "artifact_json_contracts",
        "repo_project_registry",
        "browser_scheduler_source_lifecycle",
        "release_lifecycle_plan",
        "compileall",
    }
    assert required.issubset(manifest)
    for name in required:
        assert manifest[name]["required"] is True
        assert manifest[name]["command"]



def test_release_validation_groups_default_to_repo_python(monkeypatch) -> None:
    monkeypatch.delenv(suite.RELEASE_VALIDATION_PYTHON_ENV, raising=False)
    manifest = suite.release_validation_group_manifest()

    for group in suite.RELEASE_VALIDATION_GROUPS:
        assert manifest[group]["command"][0] == "python3"
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
    monkeypatch.setenv("PROMPTBRANCH_SERVICE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(suite.subprocess, "run", fake_run)

    spec = {"required": True, "description": "unit", "command": ["python3", "-c", "pass"]}
    result = suite._run_release_validation_group("unit", spec, repo_path=tmp_path)

    assert result["ok"] is True
    assert "CHATGPT_SERVICE_BASE_URL" not in captured["env"]
    assert "PROMPTBRANCH_SERVICE_BASE_URL" not in captured["env"]


def test_browser_scheduler_release_validation_group_uses_nodeid_progress() -> None:
    manifest = suite.release_validation_group_manifest()
    group = manifest["browser_scheduler_source_lifecycle"]

    assert group["nodeid_progress"] is True


def test_release_validation_group_nodeid_progress_reports_completed_nodeids(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    class Completed:
        returncode = 0
        stdout = "passed node\n"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(list(command))
        return Completed()

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
        ["python3", "-m", "pytest", "-q", "tests/test_demo.py::test_one"],
        ["python3", "-m", "pytest", "-q", "tests/test_demo.py::test_two"],
    ]
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

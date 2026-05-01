from __future__ import annotations

from pathlib import Path

from promptbranch_mcp import agent_doctor, inspect_local_context, mcp_tool_manifest, plan_agent_request


def test_mcp_manifest_is_read_only_by_default() -> None:
    payload = mcp_tool_manifest()

    assert payload["ok"] is True
    assert payload["mode"] == "read_only"
    assert payload["tool_count"] >= 1
    assert all(tool["read_only"] is True for tool in payload["tools"])
    assert "promptbranch.state.read" in {tool["name"] for tool in payload["tools"]}


def test_mcp_manifest_can_include_controlled_writes() -> None:
    payload = mcp_tool_manifest(include_controlled_writes=True)

    assert payload["mode"] == "read_only_plus_controlled_writes"
    tools = {tool["name"]: tool for tool in payload["tools"]}
    assert tools["promptbranch.src.sync"]["risk"] == "write"
    assert tools["test.smoke.run"]["risk"] == "external_process"


def test_agent_inspect_is_read_only_and_reports_repo_state(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    profile = tmp_path / ".pb_profile"
    profile.mkdir()

    payload = inspect_local_context(repo_path=tmp_path, profile_dir=profile, max_files=5)

    assert payload["ok"] is True
    assert payload["mode"] == "read_only"
    assert payload["repo"]["version"] == "v1.2.3"
    assert "README.md" in payload["repo"]["file_sample"]
    assert payload["ollama"]["enabled"] is False


def test_agent_plan_allows_read_only_intent_automatically() -> None:
    payload = plan_agent_request("show current workspace state", repo_path=".")
    plan = payload["plan"]

    assert plan["intent"] == "read_state"
    assert plan["risk"] == "read"
    assert plan["auto_allowed"] is True
    assert plan["requires_confirmation"] is False


def test_agent_plan_blocks_destructive_source_remove_from_auto_execution() -> None:
    payload = plan_agent_request("remove source old.zip", repo_path=".")
    plan = payload["plan"]

    assert plan["action"] == "src_rm"
    assert plan["risk"] == "destructive"
    assert plan["auto_allowed"] is False
    assert plan["requires_confirmation"] is True
    assert "collateral_change_detection" in plan["prechecks"]


def test_agent_doctor_reports_workspace_check(tmp_path: Path) -> None:
    profile = tmp_path / ".pb_profile"
    profile.mkdir()
    payload = agent_doctor(repo_path=tmp_path, profile_dir=profile)

    assert payload["action"] == "agent_doctor"
    assert payload["checks"]["repo_path_exists"] is True
    assert payload["checks"]["mcp_default_manifest_read_only"] is True

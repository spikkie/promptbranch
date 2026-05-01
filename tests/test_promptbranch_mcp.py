from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from promptbranch_mcp import (
    agent_doctor,
    handle_mcp_jsonrpc_message,
    inspect_local_context,
    mcp_tool_manifest,
    plan_agent_request,
    serve_mcp_stdio,
)


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


def test_mcp_jsonrpc_initialize_and_tools_list() -> None:
    init = handle_mcp_jsonrpc_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init is not None
    assert init["result"]["capabilities"]["tools"]["listChanged"] is False
    assert init["result"]["serverInfo"]["version"] == "0.0.139"

    listed = handle_mcp_jsonrpc_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert listed is not None
    tools = {tool["name"]: tool for tool in listed["result"]["tools"]}
    assert "filesystem.list" in tools
    assert tools["filesystem.list"]["annotations"]["readOnlyHint"] is True


def test_mcp_jsonrpc_filesystem_read_is_repo_bounded(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")

    ok = handle_mcp_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "filesystem.read", "arguments": {"path": "README.md"}},
        },
        repo_path=tmp_path,
        profile_dir=tmp_path / ".pb_profile",
    )
    assert ok is not None
    assert ok["result"]["isError"] is False
    assert ok["result"]["structuredContent"]["text"] == "hello\n"

    blocked = handle_mcp_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "filesystem.read", "arguments": {"path": "../secret.txt"}},
        },
        repo_path=tmp_path,
        profile_dir=tmp_path / ".pb_profile",
    )
    assert blocked is not None
    assert blocked["result"]["isError"] is True
    assert blocked["result"]["structuredContent"]["error"] == "path_outside_repo"


def test_mcp_controlled_write_tool_is_listed_but_not_executed(tmp_path: Path) -> None:
    response = handle_mcp_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "promptbranch.src.sync", "arguments": {"path": "."}},
        },
        repo_path=tmp_path,
        profile_dir=tmp_path / ".pb_profile",
        include_controlled_writes=True,
    )
    assert response is not None
    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["error"] == "write_tool_not_executable_via_mcp_serve"


def test_mcp_stdio_serves_newline_delimited_json(tmp_path: Path) -> None:
    stdin = StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n')
    stdout = StringIO()

    rc = serve_mcp_stdio(repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile", input_stream=stdin, output_stream=stdout)

    assert rc == 0
    payload = json.loads(stdout.getvalue().strip())
    assert payload["id"] == 1
    assert "tools" in payload["result"]

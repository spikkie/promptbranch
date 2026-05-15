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
    mcp_host_config,
    mcp_host_smoke,
)


def test_mcp_manifest_is_read_only_by_default() -> None:
    payload = mcp_tool_manifest()

    assert payload["ok"] is True
    assert payload["mode"] == "read_only"
    assert payload["tool_count"] >= 1
    assert all(tool["read_only"] is True for tool in payload["tools"])
    assert "promptbranch.state.read" in {tool["name"] for tool in payload["tools"]}


def test_mcp_manifest_can_include_controlled_processes() -> None:
    payload = mcp_tool_manifest(include_controlled_processes=True)

    assert payload["mode"] == "read_only_plus_controlled_process"
    tools = {tool["name"]: tool for tool in payload["tools"]}
    assert tools["test.smoke"]["risk"] == "external_process"
    assert "promptbranch.src.sync" not in tools
    assert "artifact.release.create" not in tools
    assert set(payload["blocked_write_tools"]) == {"promptbranch.src.sync", "artifact.release.create"}


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
    assert init["result"]["serverInfo"]["version"] == "0.0.218"

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


def test_mcp_write_tool_is_not_exposed_under_controlled_processes(tmp_path: Path) -> None:
    response = handle_mcp_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "promptbranch.src.sync", "arguments": {"path": "."}},
        },
        repo_path=tmp_path,
        profile_dir=tmp_path / ".pb_profile",
        include_controlled_processes=True,
    )
    assert response is not None
    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["error"] == "unknown_tool"


def test_mcp_stdio_serves_newline_delimited_json(tmp_path: Path) -> None:
    stdin = StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n')
    stdout = StringIO()

    rc = serve_mcp_stdio(repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile", input_stream=stdin, output_stream=stdout)

    assert rc == 0
    payload = json.loads(stdout.getvalue().strip())
    assert payload["id"] == 1
    assert "tools" in payload["result"]


def test_mcp_host_config_emits_stdio_server_config(tmp_path: Path) -> None:
    payload = mcp_host_config(
        repo_path=tmp_path,
        profile_dir=tmp_path / ".pb_profile",
        command="promptbranch",
        resolve_command=False,
    )

    assert payload["ok"] is True
    assert payload["action"] == "mcp_config"
    assert payload["command_resolution"]["source"] == "raw"
    server = payload["config"]["mcpServers"]["promptbranch"]
    assert server["command"] == "promptbranch"
    assert "mcp" in server["args"]
    assert "serve" in server["args"]
    assert str(tmp_path.resolve()) in server["args"]


def test_mcp_host_config_resolves_absolute_command(tmp_path: Path) -> None:
    payload = mcp_host_config(repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile", command="/bin/echo")

    assert payload["command_resolution"]["is_absolute"] is True
    assert payload["config"]["mcpServers"]["promptbranch"]["command"] == "/bin/echo"


def test_mcp_host_smoke_launches_configured_read_only_server(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("v0.0.test\n", encoding="utf-8")
    wrapper = tmp_path / "promptbranch-wrapper"
    cli = Path(__file__).resolve().parents[1] / "promptbranch_cli.py"
    wrapper.write_text(
        "#!/bin/sh\n"
        f"exec {__import__('sys').executable} -S -c "
        + repr(
            "import sys; "
            f"sys.path.insert(0, {str(cli.parent)!r}); "
            "from promptbranch_mcp import serve_mcp_stdio; "
            f"raise SystemExit(serve_mcp_stdio(repo_path={str(tmp_path)!r}, profile_dir={str(tmp_path / '.pb_profile')!r}))"
        )
        + "\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    payload = mcp_host_smoke(
        repo_path=tmp_path,
        profile_dir=tmp_path / ".pb_profile",
        command=str(wrapper),
        resolve_command=True,
        timeout_seconds=10.0,
    )

    assert payload["ok"] is True
    assert payload["action"] == "mcp_host_smoke"
    assert payload["checks"]["command_is_absolute"] is True
    assert payload["checks"]["filesystem_read_ok"] is True




def test_mcp_host_smoke_reports_missing_file_target_without_reading_directory(tmp_path: Path) -> None:
    wrapper = tmp_path / "promptbranch-wrapper"
    wrapper.write_text("#!/bin/sh\necho should-not-launch\n", encoding="utf-8")
    wrapper.chmod(0o755)

    payload = mcp_host_smoke(
        repo_path=tmp_path,
        profile_dir=tmp_path / ".pb_profile",
        command=str(wrapper),
        resolve_command=True,
        timeout_seconds=10.0,
    )

    assert payload["ok"] is False
    assert payload["status"] == "read_target_missing"
    assert payload["read_path"] is None
    assert payload["read_candidates"] == ["VERSION", "README.md"]
    assert payload["checks"]["filesystem_read_ok"] is False
    assert "filesystem.read on a directory" in payload["diagnostic"]


def test_skill_validate_resolves_repo_relative_path_from_git_subdirectory(tmp_path: Path) -> None:
    import subprocess

    from promptbranch_mcp import skill_validate

    repo = tmp_path / "repo"
    skill_dir = repo / ".promptbranch" / "skills" / "repo-inspection"
    nested = repo / "test"
    skill_dir.mkdir(parents=True)
    nested.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: repo-inspection\n"
        "description: Inspect repo\n"
        "risk: read\n"
        "allowed_tools:\n"
        "  - filesystem.read\n"
        "  - git.status\n"
        "---\n"
        "Read-only.\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    payload = skill_validate(".promptbranch/skills/repo-inspection", repo_path=nested)

    assert payload["ok"] is True
    assert payload["status"] == "valid"
    assert payload["source"].endswith(".promptbranch/skills/repo-inspection/SKILL.md")


def test_agent_tool_call_executes_only_read_only_tool(tmp_path: Path) -> None:
    from promptbranch_mcp import agent_tool_call

    (tmp_path / "VERSION").write_text("v9.9.9\n", encoding="utf-8")

    ok = agent_tool_call("filesystem.read", {"path": "VERSION"}, repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile")
    assert ok["ok"] is True
    assert ok["result"]["text"] == "v9.9.9\n"

    blocked = agent_tool_call("promptbranch.src.sync", {"path": "."}, repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile")
    assert blocked["ok"] is False
    assert blocked["status"] == "blocked"


def test_agent_ask_uses_rule_based_read_only_planner(tmp_path: Path) -> None:
    from promptbranch_mcp import agent_ask

    (tmp_path / "VERSION").write_text("v1.0.0\n", encoding="utf-8")

    payload = agent_ask("read VERSION and git status", repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile")

    assert payload["ok"] is True
    assert payload["planner"] == "rule_based_v1"
    assert payload["ollama"]["used_for_planning"] is False
    names = [call["name"] for call in payload["tool_calls"]]
    assert "filesystem.read" in names
    assert "git.status" in names


def test_ollama_models_unavailable_is_clean() -> None:
    from promptbranch_mcp import ollama_models

    payload = ollama_models(host="http://127.0.0.1:9", timeout_seconds=0.2)

    assert payload["ok"] is False
    assert payload["action"] == "agent_models"
    assert payload["models"] == []


def test_llm_mcp_tool_call_validation_blocks_write_tool() -> None:
    from promptbranch_mcp import _validate_llm_mcp_tool_call

    valid = _validate_llm_mcp_tool_call({"tool": "filesystem.read", "arguments": {"path": "VERSION"}})
    assert valid["ok"] is True
    assert valid["tool"] == "filesystem.read"

    blocked = _validate_llm_mcp_tool_call({"tool": "promptbranch.src.sync", "arguments": {"path": "."}})
    assert blocked["ok"] is False
    assert blocked["status"] == "tool_not_allowed"


def test_mcp_tool_call_via_stdio_uses_real_server_boundary(tmp_path: Path) -> None:
    from promptbranch_mcp import mcp_tool_call_via_stdio

    (tmp_path / "VERSION").write_text("v0.0.boundary\n", encoding="utf-8")
    wrapper = tmp_path / "promptbranch-wrapper"
    wrapper.write_text(
        "#!/bin/sh\n"
        f"exec {__import__('sys').executable} -S -c "
        + repr(
            "import sys; "
            f"sys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r}); "
            "from promptbranch_mcp import serve_mcp_stdio; "
            f"raise SystemExit(serve_mcp_stdio(repo_path={str(tmp_path)!r}, profile_dir={str(tmp_path / '.pb_profile')!r}))"
        )
        + "\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    payload = mcp_tool_call_via_stdio(
        "filesystem.read",
        {"path": "VERSION"},
        repo_path=tmp_path,
        profile_dir=tmp_path / ".pb_profile",
        command=str(wrapper),
        timeout_seconds=10.0,
    )

    assert payload["ok"] is True
    assert payload["transport"] == "stdio"
    assert payload["tool_response"]["result"]["structuredContent"]["text"] == "v0.0.boundary\n"


def test_agent_mcp_llm_smoke_validates_model_then_calls_mcp(monkeypatch, tmp_path: Path) -> None:
    from promptbranch_mcp import agent_mcp_llm_smoke
    import promptbranch_mcp

    (tmp_path / "VERSION").write_text("v0.0.llm\n", encoding="utf-8")
    wrapper = tmp_path / "promptbranch-wrapper"
    wrapper.write_text(
        "#!/bin/sh\n"
        f"exec {__import__('sys').executable} -S -c "
        + repr(
            "import sys; "
            f"sys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r}); "
            "from promptbranch_mcp import serve_mcp_stdio; "
            f"raise SystemExit(serve_mcp_stdio(repo_path={str(tmp_path)!r}, profile_dir={str(tmp_path / '.pb_profile')!r}))"
        )
        + "\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    monkeypatch.setattr(
        promptbranch_mcp,
        "_call_ollama_generate_json",
        lambda **kwargs: {
            "ok": True,
            "status": "parsed",
            "model": kwargs.get("model"),
            "response_text": '{"tool":"filesystem.read","arguments":{"path":"VERSION","max_bytes":2000}}',
            "parsed": {"tool": "filesystem.read", "arguments": {"path": "VERSION", "max_bytes": 2000}},
        },
    )

    payload = agent_mcp_llm_smoke(
        "read VERSION",
        repo_path=tmp_path,
        profile_dir=tmp_path / ".pb_profile",
        model="fake-local-model",
        command=str(wrapper),
        mcp_timeout_seconds=10.0,
    )

    assert payload["ok"] is True
    assert payload["mode"] == "ollama_proposes_validated_mcp_stdio"
    assert payload["validation"]["tool"] == "filesystem.read"
    assert payload["mcp"]["ok"] is True
    assert payload["safety"]["model_has_execution_authority"] is False


def test_agent_mcp_llm_smoke_fails_when_model_output_is_invalid(monkeypatch, tmp_path: Path) -> None:
    from promptbranch_mcp import agent_mcp_llm_smoke
    import promptbranch_mcp

    monkeypatch.setattr(
        promptbranch_mcp,
        "_call_ollama_generate_json",
        lambda **kwargs: {"ok": True, "status": "parsed", "model": kwargs.get("model"), "parsed": {}},
    )

    payload = agent_mcp_llm_smoke("read VERSION", repo_path=tmp_path, profile_dir=tmp_path / ".pb_profile", model="fake-local-model")

    assert payload["ok"] is False
    assert payload["status"] == "model_tool_call_invalid"
    assert payload["mcp"] is None


def test_request_risk_classifier_blocks_destructive_original_intent() -> None:
    from promptbranch_mcp import classify_agent_request_risk

    payload = classify_agent_request_risk("delete VERSION")

    assert payload["risk"] == "destructive"
    assert payload["auto_allowed"] is False
    assert payload["status"] == "blocked_original_request_destructive"


def test_llm_validation_rejects_read_tool_for_destructive_request() -> None:
    from promptbranch_mcp import _validate_llm_mcp_tool_call

    payload = _validate_llm_mcp_tool_call(
        {"tool": "read_file", "arguments": {"path": "VERSION"}},
        original_request="delete VERSION",
    )

    assert payload["ok"] is False
    assert payload["status"] == "original_request_not_read_only"
    assert payload["request_risk"]["risk"] == "destructive"


def test_ollama_proposal_blocks_original_write_intent_before_model(monkeypatch) -> None:
    import promptbranch_mcp
    from promptbranch_mcp import ollama_propose_mcp_tool_call

    def fail_if_called(**kwargs):  # pragma: no cover - should never be called
        raise AssertionError("model should not be called for destructive requests")

    monkeypatch.setattr(promptbranch_mcp, "_call_ollama_chat_tool_call", fail_if_called)
    monkeypatch.setattr(promptbranch_mcp, "_call_ollama_generate_json", fail_if_called)

    payload = ollama_propose_mcp_tool_call("delete VERSION", model="fake-local-model")

    assert payload["ok"] is False
    assert payload["status"] == "risk_rejected"
    assert payload["request_risk"]["risk"] == "destructive"
    assert payload["proposals"] == []


def test_ollama_proposal_accepts_alias_tool_call(monkeypatch) -> None:
    import promptbranch_mcp
    from promptbranch_mcp import ollama_propose_mcp_tool_call

    monkeypatch.setattr(
        promptbranch_mcp,
        "_call_ollama_chat_tool_call",
        lambda **kwargs: {
            "ok": True,
            "status": "tool_call",
            "source": "ollama_chat_tools_aliases",
            "model": kwargs.get("model"),
            "parsed": {"tool": "read_file", "arguments": {"path": "VERSION", "max_bytes": 2000}},
        },
    )

    payload = ollama_propose_mcp_tool_call("read VERSION", model="fake-local-model")

    assert payload["ok"] is True
    assert payload["status"] == "validated"
    assert payload["selected"]["tool"] == "filesystem.read"
    assert payload["selected"]["alias_tool"] == "read_file"

from promptbranch_mcp import agent_run, skill_list, skill_show, skill_validate


def test_skill_list_includes_builtin_repo_inspection() -> None:
    payload = skill_list()
    names = {item["name"] for item in payload["skills"]}
    assert payload["ok"] is True
    assert "repo-inspection" in names


def test_skill_validate_builtin_repo_inspection_is_read_only() -> None:
    payload = skill_validate("repo-inspection")
    assert payload["ok"] is True
    assert payload["status"] == "valid"
    assert payload["skill"]["risk"] == "read"
    assert set(payload["skill"]["allowed_tools"]) == {"filesystem.read", "git.status", "git.diff.summary"}


def test_skill_show_can_omit_content() -> None:
    payload = skill_show("repo-inspection", include_content=False)
    assert payload["ok"] is True
    assert "content" not in payload


def test_agent_run_rejects_destructive_original_request() -> None:
    payload = agent_run("delete VERSION")
    assert payload["ok"] is False
    assert payload["status"] == "risk_rejected"
    assert payload["results"] == []


def test_agent_run_uses_mcp_stdio_boundary_for_deterministic_plan(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_mcp(tool, arguments=None, **kwargs):
        calls.append((tool, arguments or {}, kwargs))
        return {"ok": True, "tool": tool, "arguments": arguments or {}, "status": "verified"}

    monkeypatch.setattr("promptbranch_mcp.mcp_tool_call_via_stdio", fake_mcp)
    (tmp_path / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    payload = agent_run("read VERSION and git status", repo_path=tmp_path)
    assert payload["ok"] is True
    assert payload["planner"] == "rule_based_v1"
    assert [item[0] for item in calls] == ["filesystem.read", "git.status"]


def test_agent_run_skill_repo_inspection_enforces_skill_allowed_tools(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_mcp(tool, arguments=None, **kwargs):
        calls.append((tool, arguments or {}, kwargs))
        return {"ok": True, "tool": tool, "arguments": arguments or {}, "status": "verified"}

    monkeypatch.setattr("promptbranch_mcp.mcp_tool_call_via_stdio", fake_mcp)
    (tmp_path / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    payload = agent_run("inspect repo", repo_path=tmp_path, skill="repo-inspection")
    assert payload["ok"] is True
    assert payload["planner"] == "skill:repo-inspection"
    assert [item[0] for item in calls] == ["filesystem.read", "git.status", "git.diff.summary"]


def test_agent_risk_classifier_allows_controlled_smoke_only() -> None:
    from promptbranch_mcp import classify_agent_request_risk

    smoke = classify_agent_request_risk("run smoke tests")
    assert smoke["risk"] == "external_process"
    assert smoke["auto_allowed"] is True
    assert smoke["controlled_tool"] == "test.smoke"

    pytest_req = classify_agent_request_risk("run pytest")
    assert pytest_req["risk"] == "external_process"
    assert pytest_req["auto_allowed"] is False


def test_agent_run_wires_controlled_smoke_tool(monkeypatch, tmp_path: Path) -> None:
    import promptbranch_mcp

    calls = []

    def fake_mcp(tool, arguments=None, **kwargs):
        calls.append((tool, arguments or {}, kwargs))
        return {"ok": True, "status": "verified", "tool": tool, "arguments": arguments or {}}

    monkeypatch.setattr(promptbranch_mcp, "mcp_tool_call_via_stdio", fake_mcp)
    payload = promptbranch_mcp.agent_run("run smoke tests", repo_path=tmp_path, command="/tmp/promptbranch", mcp_timeout_seconds=9)

    assert payload["ok"] is True
    assert payload["planner"] == "controlled_process_v1"
    assert payload["request_risk"]["controlled_tool"] == "test.smoke"
    assert [item[0] for item in calls] == ["test.smoke"]
    assert calls[0][1]["timeout_seconds"] == 60.0
    assert calls[0][1]["command"] == "/tmp/promptbranch"


def test_agent_tool_call_allows_controlled_test_smoke(monkeypatch, tmp_path: Path) -> None:
    import promptbranch_mcp

    def fake_controlled(tool, arguments=None, **kwargs):
        return {"ok": True, "tool": tool, "status": "verified", "arguments": arguments or {}}

    monkeypatch.setattr(promptbranch_mcp, "call_controlled_process_mcp_tool", fake_controlled)
    payload = promptbranch_mcp.agent_tool_call("test.smoke", {"timeout_seconds": 5}, repo_path=tmp_path)

    assert payload["ok"] is True
    assert payload["tool"] == "test.smoke"
    assert payload["result"]["status"] == "verified"


def test_agent_summarize_log_is_repo_bounded_and_summary_only(monkeypatch, tmp_path: Path) -> None:
    import promptbranch_mcp

    log = tmp_path / "session.log"
    log.write_text("ok=true\nstatus=verified\n", encoding="utf-8")

    monkeypatch.setattr(
        promptbranch_mcp,
        "_call_ollama_generate",
        lambda **kwargs: {
            "ok": True,
            "status": "generated",
            "model": kwargs.get("model"),
            "text": "The run verified successfully.",
        },
    )

    payload = promptbranch_mcp.agent_summarize_log("session.log", repo_path=tmp_path, model="fake-local-model")

    assert payload["ok"] is True
    assert payload["action"] == "agent_summarize_log"
    assert payload["status"] == "summarized"
    assert payload["read"]["relative_path"] == "session.log"
    assert payload["deterministic_summary"]["status"] == "generated"
    assert payload["ollama"]["used_for_planning"] is False
    assert payload["ollama"]["used_for_summary"] is True
    assert payload["safety"]["model_has_execution_authority"] is False

    outside = promptbranch_mcp.agent_summarize_log("../secret.log", repo_path=tmp_path, model="fake-local-model")
    assert outside["ok"] is False
    assert outside["status"] == "path_outside_repo"


def test_agent_summarize_log_model_failure_preserves_read_metadata(monkeypatch, tmp_path: Path) -> None:
    import promptbranch_mcp

    (tmp_path / "failure.log").write_text("FAIL test_example\n", encoding="utf-8")
    monkeypatch.setattr(
        promptbranch_mcp,
        "_call_ollama_generate",
        lambda **kwargs: {"ok": False, "status": "unavailable", "error": "connection refused", "model": kwargs.get("model")},
    )

    payload = promptbranch_mcp.agent_summarize_log("failure.log", repo_path=tmp_path, model="fake-local-model")

    assert payload["ok"] is True
    assert payload["status"] == "deterministic_summary"
    assert payload["read"]["ok"] is True
    assert payload["read"]["relative_path"] == "failure.log"
    assert payload["deterministic_summary"]["ok"] is True
    assert payload["deterministic_summary"]["status"] == "generated"
    assert payload["deterministic_summary"]["counts"]["ok_false"] == 0
    assert payload["ollama"]["summary"]["status"] == "unavailable"
    assert payload["ollama"]["fallback_used"] is True

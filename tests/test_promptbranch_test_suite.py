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

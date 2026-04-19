from __future__ import annotations

import json

import pytest

from chatgpt_cli_sequence_v5 import CommandResult, Runner, SmokeError, State


def test_remove_lookup_candidates_prefers_authoritative_matches() -> None:
    runner = Runner("chatgpt_cli.py", "python", timeout=5)
    state = State(
        project_name="demo",
        source_path="/tmp/smoke-source-abc123.txt",
        source_name="smoke-source-abc123",
        source_match="smoke-source-abc123.txt Document",
        source_match_candidates=[
            "smoke-source-abc123.txt Document",
            "smoke-source-abc123.txt",
            "smoke-source-abc123",
        ],
    )

    candidates = runner.remove_lookup_candidates(state)

    assert candidates[0] == "smoke-source-abc123.txt Document"
    assert candidates[1] == "smoke-source-abc123.txt"
    assert candidates[2] == "smoke-source-abc123"
    assert candidates.count("smoke-source-abc123.txt Document") == 1


def test_project_source_remove_idempotent_requires_already_absent_flag() -> None:
    runner = Runner("chatgpt_cli.py", "python", timeout=5)
    state = State(
        project_name="demo",
        source_path="/tmp/smoke-source-abc123.txt",
        source_name="smoke-source-abc123",
        project_url_created="https://chatgpt.com/g/g-p-123/project",
        source_identity_used="smoke-source-abc123.txt Document",
    )

    payload = {
        "ok": True,
        "action": "remove",
        "source_identity_used": "smoke-source-abc123.txt Document",
        "already_absent": False,
        "removed_via_ui": True,
    }

    def fake_try_variants(*args, **kwargs):
        return CommandResult(
            argv=["project-source-remove", "--exact", state.source_identity_used or ""],
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    runner.try_variants = fake_try_variants  # type: ignore[method-assign]

    with pytest.raises(SmokeError, match="already_absent=true"):
        runner.project_source_remove_idempotent(state)

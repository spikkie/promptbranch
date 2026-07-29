from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "docs/backlog/backlog.json"


def test_tracked_backlog_contract_is_valid_and_references_existing_tickets() -> None:
    data = json.loads(BACKLOG.read_text(encoding="utf-8"))
    assert data["schema"] == "promptbranch.backlog"
    assert data["schema_version"] == "1.0"
    assert data["repo_id"] == "chatgpt_claudecode_workflow-2"
    tickets = data["tickets"]
    assert isinstance(tickets, list)
    assert len(tickets) == 2
    ids = [ticket["id"] for ticket in tickets]
    assert ids == ["ISSUE-001", "PBAI-001"]
    assert len(ids) == len(set(ids))
    assert tickets[0]["status"] == "implemented_candidate"
    assert tickets[0]["implemented_in"] == "v0.1.111"
    assert tickets[1]["status"] == "in_progress"
    assert tickets[1]["started_in"] == "v0.1.112"
    assert [ticket["implementation_order"] for ticket in tickets] == [1, 2]
    assert tickets[1]["depends_on"] == ["ISSUE-001"]
    for ticket in tickets:
        path = ROOT / ticket["path"]
        assert path.is_file()
        assert path.read_text(encoding="utf-8").strip()


def test_backlog_architectural_invariant_is_exact() -> None:
    data = json.loads(BACKLOG.read_text(encoding="utf-8"))
    assert data["architectural_invariant"] == (
        "Promptbranch controls the release lifecycle. "
        "Each project defines what must be validated and how its artifact is built."
    )

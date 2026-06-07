from __future__ import annotations

from pathlib import Path


DOC = Path("docs/design/promptbranch-parallel-execution-architecture.md")


def _doc_text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_parallel_architecture_doc_status_matches_current_release_history() -> None:
    text = _doc_text()
    assert "Status: implementation current through `v0.1.50`" in text
    assert "`v0.1.47` | Add read-only parallel task fan-out." in text
    assert "`v0.1.48` | Add protocol-bound parallel ask planning" in text
    assert "`v0.1.48.1` | Repair parallel ask protocol planning" in text
    assert "`v0.1.49` | Add planning-only source mutation queue" in text
    assert "`v0.1.50` | Integrate release lifecycle with scheduler locks" in text
    assert "## v0.1.48 — Protocol-bound parallel ask planning" in text
    assert "## Repair v0.1.48.1 — Parallel ask stale-baseline guard" in text
    assert "## v0.1.49 — Source mutation queue planning per workspace" in text
    assert "## v0.1.50 — Release lifecycle scheduler integration" in text


def test_parallel_architecture_slice_plan_has_no_duplicate_v0146_row() -> None:
    text = _doc_text()
    slice_lines = [line for line in text.splitlines() if line.startswith("| `v0.1.46` |")]
    assert len(slice_lines) == 1


def test_parallel_architecture_doc_declares_repair_does_not_advance_line() -> None:
    text = _doc_text()
    repair_section = text.split("## Documentation consistency repair (`v0.1.47.1`)", 1)[1]
    assert "does not advance the parallel execution line" in repair_section
    assert "does not widen any write path" in repair_section

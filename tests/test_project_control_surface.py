from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_DOCS = ROOT / "docs" / "project"

REQUIRED_FILES = [
    "README.md",
    "mvp.md",
    "definition-of-done.md",
    "plan.md",
    "status.md",
    "release-status.md",
    "decisions.md",
    "migration.md",
]


def read_doc(name: str) -> str:
    return (PROJECT_DOCS / name).read_text(encoding="utf-8")


def test_project_control_surface_required_files_exist() -> None:
    missing = [name for name in REQUIRED_FILES if not (PROJECT_DOCS / name).is_file()]
    assert missing == []


def test_definition_of_done_has_evidence_table() -> None:
    text = read_doc("definition-of-done.md")
    assert "| ID | DoD item | Status | Evidence | Last release |" in text
    assert "DOD-001" in text
    assert "DOD-008" in text
    assert "open" in text
    assert "done" in text


def test_release_status_has_allowed_table_and_current_baseline() -> None:
    text = read_doc("release-status.md")
    assert "| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |" in text
    assert "v0.1.66" in text
    assert "accepted_current" in text
    assert "v0.1.67" in text
    assert "v0.1.68" in text
    assert "v0.1.69" in text
    assert "v0.1.70" in text
    assert "candidate" in text


def test_migration_has_mapping_table_and_preserves_old_docs() -> None:
    text = read_doc("migration.md")
    assert "| Existing file | Current role | Migrated to | Migration status | Notes |" in text
    assert "docs/mvp-definition-of-done.md" in text
    assert "docs/design/orchestration/docs/current_status.md" in text
    assert "not deleted" in text or "preserved" in text


def test_status_has_next_safe_action_and_accepted_baseline() -> None:
    text = read_doc("status.md")
    assert "## Next safe action" in text
    assert "accepted/current baseline with adoption evidence:" in text
    assert "chatgpt_claudecode_workflow-2_v0.1.73.1.zip" in text
    assert "chatgpt_claudecode_workflow-2_v0.1.73.2.zip" in text

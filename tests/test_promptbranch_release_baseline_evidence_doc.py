from __future__ import annotations

from pathlib import Path


BASELINE_DOC = Path("docs/design/promptbranch-release-baseline-evidence.md")


def test_release_baseline_evidence_doc_declares_authoritative_accepted_artifact() -> None:
    text = BASELINE_DOC.read_text(encoding="utf-8")

    assert "Release: `v0.1.66`" in text
    assert "After adoption, the locally accepted Promptbranch artifact is authoritative." in text
    assert "transient sandbox ZIP" in text
    assert "locally accepted artifact" in text
    assert "Project Source baseline" in text
    assert "runtime package version" in text


def test_release_baseline_evidence_doc_covers_promptbranch_read_commands() -> None:
    text = BASELINE_DOC.read_text(encoding="utf-8")

    assert "pb artifact current --json" in text
    assert "pb release baseline-status --json" in text
    assert "registry_current.kind = adopted_release" in text
    assert "code_matches_adopted_source = true" in text


def test_release_baseline_evidence_doc_separates_validation_evidence_classes() -> None:
    text = BASELINE_DOC.read_text(encoding="utf-8")

    assert "full-test evidence may be stale" in text
    assert "focused-validation evidence" in text
    assert "focused-validation accepted" in text
    assert "full-test-green" in text


def test_release_docs_status_includes_baseline_evidence_guard(capsys) -> None:
    import argparse
    import asyncio
    import json

    from promptbranch_cli import cmd_release_docs_status

    args = argparse.Namespace(
        version="v0.1.125",
        design_doc="docs/design/promptbranch-mvp-living-design.md",
        drawio="docs/design/promptbranch-mvp-living-design.drawio",
        repo_path=".",
        json=True,
    )

    exit_code = asyncio.run(cmd_release_docs_status(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "verified"
    assert payload["baseline_evidence"]["ok"] is True
    assert payload["baseline_evidence"]["doc"]["path"] == "docs/design/promptbranch-release-baseline-evidence.md"
    assert payload["baseline_evidence"]["missing_phrase_count"] == 0
    assert payload["baseline_evidence"]["blocker_codes"] == []

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


DESIGN_DOC = Path("docs/design/promptbranch-application-design.md")
CLASS_DRAWIO = Path("docs/design/promptbranch-class-diagram.drawio")
LIVING_DRAWIO = Path("docs/design/promptbranch-mvp-living-design.drawio")
LIFECYCLE_DRAWIO = Path("docs/diagrams/promptbranch-lifecycle/promptbranch_lifecycle_commands.drawio")


def _diagram_names(path: Path) -> set[str]:
    root = ET.parse(path).getroot()
    return {str(item.attrib.get("name") or "") for item in root.findall("diagram")}


def test_promptbranch_application_design_doc_declares_pb_and_chatgpt_roles() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    assert "Release: `v0.1.66`" in text
    assert "pb          = local deterministic control plane" in text
    assert "ChatGPT     = reasoning/conversation surface" in text
    assert "Assistant prose is advisory" in text
    assert "Validated JSON, ZIP checks, tests, and Promptbranch current-state reads are operational" in text
    assert "Workspace = current ChatGPT Project" in text
    assert "Task      = current chat/conversation inside that project" in text
    assert "Artifact  = current repo/source bundle/release ZIP" in text
    assert "backend-first reads" in text
    assert "transactional writes" in text
    assert "accepted baseline / artifact continuity" in text


def test_promptbranch_application_design_doc_contains_required_diagram_sections() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    assert "## Activity diagram" in text
    assert "## Data-flow diagram" in text
    assert "## State-transition diagram" in text
    assert "```mermaid" in text
    assert "pb CLI / local host" in text
    assert "ChatGPT.com / Project" in text


def test_promptbranch_application_design_doc_references_existing_drawio_sources() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    for path in (CLASS_DRAWIO, LIVING_DRAWIO, LIFECYCLE_DRAWIO):
        assert str(path) in text
        assert path.is_file()


def test_existing_drawio_files_are_extended_with_pb_application_design_pages() -> None:
    assert "PB Application Role Components" in _diagram_names(CLASS_DRAWIO)

    living_names = _diagram_names(LIVING_DRAWIO)
    assert "PB Application Activity — pb and ChatGPT Roles" in living_names
    assert "PB Application Data Flow" in living_names
    assert "PB Application State Transitions" in living_names

    assert "PB Release State Transitions" in _diagram_names(LIFECYCLE_DRAWIO)


def test_docs_status_includes_pb_application_design_freshness_guard(capsys) -> None:
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
    assert payload["application_design"]["ok"] is True
    assert payload["application_design"]["missing_phrase_count"] == 0
    assert payload["application_design"]["blocker_codes"] == []
    assert payload["baseline_evidence"]["ok"] is True
    assert payload["baseline_evidence"]["missing_phrase_count"] == 0
    assert payload["baseline_evidence"]["blocker_codes"] == []
    guarded_paths = {item["path"] for item in payload["application_design"]["drawio_sources"]}
    assert guarded_paths == {
        "docs/design/promptbranch-class-diagram.drawio",
        "docs/design/promptbranch-mvp-living-design.drawio",
        "docs/diagrams/promptbranch-lifecycle/promptbranch_lifecycle_commands.drawio",
    }

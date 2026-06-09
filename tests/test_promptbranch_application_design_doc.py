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

    assert "Release: `v0.1.58`" in text
    assert "pb          = local deterministic control plane" in text
    assert "ChatGPT     = reasoning/conversation surface" in text
    assert "Assistant prose is advisory" in text
    assert "Validated JSON, ZIP checks, tests, and Promptbranch current-state reads are operational" in text


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

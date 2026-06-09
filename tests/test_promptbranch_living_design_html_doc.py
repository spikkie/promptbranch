from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from promptbranch_cli import cmd_release_docs_status


HTML_DOC = Path("docs/design/promptbranch-living-design-overview.html")
DRAWIO_SOURCE = "docs/design/promptbranch-mvp-living-design.drawio"


def test_living_design_html_overview_exists_and_references_drawio_source() -> None:
    text = HTML_DOC.read_text(encoding="utf-8")

    assert "Promptbranch Living Design" in text
    assert "v0.1.62" in text
    assert DRAWIO_SOURCE in text
    assert "12 documented pages" in text
    assert "Material for MkDocs" in text


def test_living_design_html_overview_documents_pb_authority_model() -> None:
    text = HTML_DOC.read_text(encoding="utf-8")

    assert "PB authority model" in text
    assert "Promptbranch is the deterministic control plane" in text
    assert "ChatGPT is the reasoning" in text
    assert "Workspace" in text
    assert "Task" in text
    assert "Artifact" in text
    assert "backend-first reads" in text
    assert "transactional writes" in text
    assert "artifact baseline model" in text
    assert "MCP/agent layer" in text
    assert "release lifecycle" in text


def test_release_docs_status_includes_living_design_overview_guard(capsys) -> None:
    args = argparse.Namespace(
        version="v0.1.62",
        design_doc="docs/design/promptbranch-mvp-living-design.md",
        drawio="docs/design/promptbranch-mvp-living-design.drawio",
        repo_path=".",
        json=True,
    )

    exit_code = asyncio.run(cmd_release_docs_status(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["living_design_overview"]["ok"] is True
    assert payload["living_design_overview"]["html"]["path"] == str(HTML_DOC)
    assert payload["living_design_overview"]["missing_phrase_count"] == 0
    assert payload["warning_codes"] == []
    assert payload["blocker_codes"] == []
    assert payload["mutating_actions_executed"] is False

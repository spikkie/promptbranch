from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from promptbranch_cli import cmd_release_docs_status


MKDOCS_CONFIG = Path("mkdocs.yml")
DOCS_INDEX = Path("docs/index.md")
DESIGN_INDEX = Path("docs/design/index.md")
RELEASES_INDEX = Path("docs/releases/index.md")
SITE_OPERATION = Path("docs/site.md")


def test_mkdocs_scaffold_declares_material_theme_without_rendered_site() -> None:
    config = MKDOCS_CONFIG.read_text(encoding="utf-8")

    assert "site_name: Promptbranch Documentation" in config
    assert "name: material" in config
    assert "site.md" in config
    assert "docs/site.md" in config
    assert "docs/design/promptbranch-living-design-overview.html" in config
    assert "docs/design/promptbranch-application-design.md" in config
    assert "docs/design/promptbranch-release-baseline-evidence.md" in config
    assert not Path("site").exists()


def test_documentation_indices_link_pb_architecture_entrypoints() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in [DOCS_INDEX, SITE_OPERATION, DESIGN_INDEX, RELEASES_INDEX]
    )

    assert "Release: `v0.1.66`" in combined
    assert "Material for MkDocs" in combined
    assert "Promptbranch is the deterministic control plane" in combined
    assert "ChatGPT is the reasoning" in combined
    assert "Workspace" in combined
    assert "Task" in combined
    assert "Artifact" in combined
    assert "backend-first reads" in combined
    assert "transactional writes" in combined
    assert "artifact baseline semantics" in combined
    assert "release lifecycle" in combined
    assert "docs/site.md" in combined
    assert "mkdocs serve" in combined
    assert "mkdocs build" in combined
    assert "docs/design/promptbranch-living-design-overview.html" in combined
    assert "docs/design/promptbranch-living-design-overview.md" in combined
    assert "docs/design/promptbranch-application-design.md" in combined
    assert "docs/design/promptbranch-release-baseline-evidence.md" in combined
    assert "docs/design/orchestration/docs/current_status.md" in combined
    assert "docs/release-v0.1.66.md" in combined


def test_documentation_site_links_resolve_to_repo_files() -> None:
    files = [MKDOCS_CONFIG, DOCS_INDEX, SITE_OPERATION, DESIGN_INDEX, RELEASES_INDEX, Path("docs/design/promptbranch-living-design-overview.md")]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

    assert "docs/site.md" in combined
    assert "docs/design/promptbranch-mvp-living-design.drawio" in combined
    assert "docs/site.md" in combined
    assert "mkdocs serve" in combined
    assert "mkdocs build" in combined
    assert "docs/design/promptbranch-living-design-overview.html" in combined
    assert "docs/release-v0.1.66.md" in combined
    assert SITE_OPERATION.is_file()
    assert Path("docs/design/promptbranch-mvp-living-design.drawio").is_file()
    assert Path("docs/design/promptbranch-living-design-overview.html").is_file()
    assert Path("docs/release-v0.1.66.md").is_file()


def test_release_docs_status_includes_docs_site_guard(capsys) -> None:
    args = argparse.Namespace(
        version="v0.1.66",
        design_doc="docs/design/promptbranch-mvp-living-design.md",
        drawio="docs/design/promptbranch-mvp-living-design.drawio",
        repo_path=".",
        json=True,
    )

    exit_code = asyncio.run(cmd_release_docs_status(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["docs_site"]["ok"] is True
    assert payload["docs_site"]["config"]["path"] == "mkdocs.yml"
    assert payload["docs_site"]["config"]["theme"] == "material"
    assert payload["docs_site"]["missing_reference_count"] == 0
    assert payload["docs_site"]["missing_phrase_count"] == 0
    assert payload["docs_site"]["generated_site_present"] is False
    assert payload["docs_site"]["link_integrity"]["ok"] is True
    assert payload["docs_site"]["build_readiness"]["ok"] is True
    assert payload["docs_site"]["build_readiness"]["docs_site_policy"] == "docs/site.md"
    assert payload["docs_site"]["build_readiness"]["preview_command_documented"] is True
    assert payload["docs_site"]["build_readiness"]["build_command_documented"] is True
    assert payload["docs_site"]["build_readiness"]["generated_site_forbidden"] is True
    assert payload["docs_site"]["build_readiness"]["requires_committed_site_output"] is False
    assert payload["docs_site"]["link_integrity"]["checked_link_count"] > 0
    assert payload["docs_site"]["link_integrity"]["missing_targets"] == []
    assert payload["warning_codes"] == []
    assert payload["blocker_codes"] == []
    assert payload["mutating_actions_executed"] is False

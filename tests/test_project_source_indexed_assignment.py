from __future__ import annotations

import argparse
import asyncio
import json
import zipfile
from pathlib import Path

import promptbranch_cli as cli
from promptbranch_artifacts import ArtifactRegistry


class _Backend:
    def __init__(self, project_url: str, sources: list[dict[str, object]]) -> None:
        self.project_url = project_url
        self.sources = sources

    def state_snapshot(self) -> dict[str, object]:
        return {"resolved_project_home_url": self.project_url}

    async def list_project_sources(self, *, keep_open: bool = False) -> dict[str, object]:
        return {"ok": True, "status": "verified", "sources": self.sources}


def _release_zip(path: Path, version: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("VERSION", version + "\n")
        archive.writestr("README.md", "demo\n")


def test_source_filename_matching_accepts_exact_or_indexed_family() -> None:
    canonical = "platform-gitops_v0.0.6.6.zip"
    exact = cli._source_filename_match_details({"title": canonical}, canonical)
    indexed = cli._source_filename_match_details({"title": "platform-gitops_v0.0.6.6(14).zip"}, canonical)
    unrelated = cli._source_filename_match_details({"title": "platform-gitops_v0.0.6.60(14).zip"}, canonical)

    assert exact == {
        "matched": True,
        "requested_filename": canonical,
        "assigned_filename": canonical,
        "match_kind": "exact_canonical",
    }
    assert indexed == {
        "matched": True,
        "requested_filename": canonical,
        "assigned_filename": "platform-gitops_v0.0.6.6(14).zip",
        "match_kind": "backend_assigned_indexed",
    }
    assert unrelated["matched"] is False


def test_project_source_matching_keeps_multiple_indexed_matches_ambiguous() -> None:
    canonical = "platform-gitops_v0.0.6.6.zip"
    matched, payload = cli._project_sources_matching_filename(
        {
            "ok": True,
            "sources": [
                {"title": "platform-gitops_v0.0.6.6(14).zip"},
                {"title": "platform-gitops_v0.0.6.6(15).zip"},
            ],
        },
        canonical,
    )

    assert len(matched) == 2
    assert payload["matching_expected_count"] == 2
    assert payload["matching_assigned_filenames"] == [
        "platform-gitops_v0.0.6.6(14).zip",
        "platform-gitops_v0.0.6.6(15).zip",
    ]


def test_artifact_adopt_accepts_one_correlated_indexed_project_source(monkeypatch, capsys, tmp_path: Path) -> None:
    canonical = "platform-gitops_v0.0.6.6.zip"
    assigned = "platform-gitops_v0.0.6.6(14).zip"
    zip_path = tmp_path / canonical
    _release_zip(zip_path, "v0.0.6.6")
    registry = ArtifactRegistry(tmp_path / "project-state")
    registry.initialize()
    monkeypatch.setattr(cli, "_artifact_registry_from_args", lambda _args: registry)

    backend = _Backend("https://chatgpt.com/g/g-p-demo/project", [{"title": assigned, "id": "src_14"}])
    args = argparse.Namespace(
        artifact=canonical,
        from_project_source=True,
        local_only=False,
        local_path=str(zip_path),
        keep_open=False,
        json=True,
        profile_dir=None,
        repo="platform-gitops",
    )

    exit_code = asyncio.run(cli.cmd_artifact_adopt(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "adopted"
    assert payload["artifact_ref"] == canonical
    assert payload["requested_source_ref"] == canonical
    assert payload["assigned_source_ref"] == assigned
    assert payload["source_ref"] == assigned
    assert payload["matched_source"]["filename_match_kind"] == "backend_assigned_indexed"
    assert payload["matched_source"]["assigned_filename"] == assigned
    assert payload["after_snapshot"]["state"]["artifact_ref"] == canonical
    assert payload["after_snapshot"]["state"]["source_ref"] == assigned
    assert registry.current(repo_id="platform-gitops")["filename"] == canonical
    assert registry.current(repo_id="platform-gitops")["source_ref"] == assigned


def test_artifact_adopt_blocks_multiple_indexed_project_sources(monkeypatch, capsys, tmp_path: Path) -> None:
    canonical = "platform-gitops_v0.0.6.6.zip"
    zip_path = tmp_path / canonical
    _release_zip(zip_path, "v0.0.6.6")
    registry = ArtifactRegistry(tmp_path / "project-state")
    registry.initialize()
    monkeypatch.setattr(cli, "_artifact_registry_from_args", lambda _args: registry)

    backend = _Backend(
        "https://chatgpt.com/g/g-p-demo/project",
        [
            {"title": "platform-gitops_v0.0.6.6(14).zip"},
            {"title": "platform-gitops_v0.0.6.6(15).zip"},
        ],
    )
    args = argparse.Namespace(
        artifact=canonical,
        from_project_source=True,
        local_only=False,
        local_path=str(zip_path),
        keep_open=False,
        json=True,
        profile_dir=None,
        repo="platform-gitops",
    )

    exit_code = asyncio.run(cli.cmd_artifact_adopt(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "project_source_match_count_invalid"
    assert payload["matching_expected_count"] == 2
    assert registry.current(repo_id="platform-gitops") is None

from __future__ import annotations

import argparse
import asyncio
import json
import zipfile
from pathlib import Path

from promptbranch_cli import cmd_release_doctor


class _DoctorBackend:
    def __init__(self, state: dict[str, object]) -> None:
        self._state = state

    def state_snapshot(self) -> dict[str, object]:
        return dict(self._state)

    async def list_project_sources(self, *, keep_open: bool = False) -> dict[str, object]:  # pragma: no cover - skipped in these tests
        return {"ok": True, "sources": []}


def _write_release_config(repo: Path) -> None:
    (repo / ".promptbranch-release.yml").write_text(
        """
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow-2_
  version_prefix: v
  suffix: .zip
  version_file: VERSION
  policy_file: .pb_profile/promptbranch_artifacts.json
install:
  preserve:
    - .git/
    - .env
    - .generated/
    - .pb_profile/
git:
  unsafe_paths:
    - .env
    - .generated/
    - .pb_profile/
    - '*.zip'
    - '*.log'
hooks:
  doctor:
    command: pb release doctor --version {version} --artifact {artifact} --repo-path {repo_path} --json
""".lstrip(),
        encoding="utf-8",
    )


def _write_candidate_zip(path: Path, version: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("VERSION", f"{version}\n")
        archive.writestr("README.md", "# candidate\n")


def _write_registry(profile: Path, repo: Path, version: str) -> None:
    profile.mkdir(parents=True, exist_ok=True)
    filename = f"chatgpt_claudecode_workflow-2_{version}.zip"
    (profile / "promptbranch_artifacts.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifacts": [
                    {
                        "path": str(repo / filename),
                        "filename": filename,
                        "kind": "adopted_release",
                        "version": version,
                        "sha256": "accepted-demo",
                        "size_bytes": 1,
                        "file_count": 1,
                        "created_at": "2026-06-10T00:00:00Z",
                        "source_ref": filename,
                        "project_url": "https://chatgpt.com/g/g-p-demo/project",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _args(repo: Path, profile: Path, artifact: Path, version: str) -> argparse.Namespace:
    return argparse.Namespace(
        version=version,
        target_version=None,
        artifact=str(artifact),
        config=".promptbranch-release.yml",
        repo_path=str(repo),
        health_url=None,
        health_timeout=0.2,
        source_timeout=1.0,
        skip_service_health=True,
        skip_project_sources=True,
        keep_open=False,
        json=True,
        profile_dir=str(profile),
        service_base_url=None,
    )


def test_release_doctor_consumes_config_for_candidate_zip_precheck(capsys, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"
    accepted_version = "v0.1.65"
    candidate_version = "v0.1.66"
    (repo / "VERSION").write_text(f"{candidate_version}\n", encoding="utf-8")
    _write_release_config(repo)
    _write_registry(profile, repo, accepted_version)
    artifact = repo / f"chatgpt_claudecode_workflow-2_{candidate_version}.zip"
    _write_candidate_zip(artifact, candidate_version)
    backend = _DoctorBackend(
        {
            "artifact_ref": f"chatgpt_claudecode_workflow-2_{accepted_version}.zip",
            "artifact_version": accepted_version,
            "source_ref": f"chatgpt_claudecode_workflow-2_{accepted_version}.zip",
            "source_version": accepted_version,
            "resolved_project_home_url": "https://chatgpt.com/g/g-p-demo/project",
        }
    )

    exit_code = asyncio.run(cmd_release_doctor(backend, _args(repo, profile, artifact, candidate_version)))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["read_only"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["release_config"]["ok"] is True
    assert payload["release_config"]["artifact_prefix"] == "chatgpt_claudecode_workflow-2_"
    candidate = payload["candidate_artifact"]
    assert candidate["ok"] is True
    assert candidate["filename"] == artifact.name
    assert candidate["filename_matches_config"] is True
    assert candidate["version"] == candidate_version
    assert candidate["version_matches_requested"] is True
    assert candidate["zip_opens"] is True
    assert candidate["zip_root_is_repo_contents"] is True
    assert candidate["version_file_present"] is True
    assert candidate["version_file_value"] == candidate_version
    assert candidate["hygiene_ok"] is True
    assert candidate["baseline_continuity"]["ok"] is True
    assert candidate["baseline_continuity"]["current_baseline_version"] == accepted_version
    assert candidate["baseline_continuity"]["expected_next_normal_version"] == candidate_version
    assert candidate["blocker_codes"] == []
    assert "candidate_artifact_baseline_mismatch" not in payload["blocker_codes"]
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False


def test_release_doctor_blocks_candidate_filename_that_violates_config(capsys, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = tmp_path / "profile"
    candidate_version = "v0.1.66"
    (repo / "VERSION").write_text(f"{candidate_version}\n", encoding="utf-8")
    _write_release_config(repo)
    _write_registry(profile, repo, "v0.1.65")
    artifact = repo / f"wrong-prefix_{candidate_version}.zip"
    _write_candidate_zip(artifact, candidate_version)
    backend = _DoctorBackend(
        {
            "artifact_ref": "chatgpt_claudecode_workflow-2_v0.1.65.zip",
            "artifact_version": "v0.1.65",
            "source_ref": "chatgpt_claudecode_workflow-2_v0.1.65.zip",
            "source_version": "v0.1.65",
            "resolved_project_home_url": "https://chatgpt.com/g/g-p-demo/project",
        }
    )

    exit_code = asyncio.run(cmd_release_doctor(backend, _args(repo, profile, artifact, candidate_version)))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert "candidate_artifact_wrong_filename" in payload["blocker_codes"]
    assert payload["candidate_artifact"]["filename_matches_config"] is False
    assert payload["candidate_artifact"]["expected_filename_from_config"] == f"chatgpt_claudecode_workflow-2_{candidate_version}.zip"
    assert payload["project_source_mutated"] is False
    assert payload["adoption_performed"] is False

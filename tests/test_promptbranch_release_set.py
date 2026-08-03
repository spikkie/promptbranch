from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from promptbranch_artifacts import ArtifactRecord, ArtifactRegistry, sha256_file
from promptbranch_cli import make_parser
from promptbranch_project import (
    join_local_repo,
    load_repo_identity,
    project_registry_dir,
    write_repo_identity,
)
from promptbranch_release_set import build_release_set_plan, version_satisfies

PROJECT_ID = "kubernetes"
PROJECT_URL = "https://chatgpt.com/g/g-p-demo-kubernetes/project"


def _join(tmp_path: Path, repo_id: str, role: str = "member") -> Path:
    repo = tmp_path / repo_id
    write_repo_identity(
        repo,
        project_id=PROJECT_ID,
        project_home_url=PROJECT_URL,
        repo_id=repo_id,
        artifact_pattern=f"{repo_id}_<version>.zip",
        role=role,
    )
    identity = load_repo_identity(repo)
    assert identity is not None
    join_local_repo(identity)
    return repo


def _artifact(repo: Path, repo_id: str, version: str) -> tuple[str, str]:
    filename = f"{repo_id}_{version}.zip"
    path = repo / filename
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("VERSION", version + "\n")
        archive.writestr("README.md", f"{repo_id} {version}\n")
    return filename, sha256_file(path)


def _add_current(project_dir: Path, repo_id: str, version: str) -> None:
    filename = f"{repo_id}_{version}.zip"
    ArtifactRegistry(project_dir).add(
        ArtifactRecord(
            path=str(project_dir / filename),
            filename=filename,
            kind="adopted_release",
            version=version,
            repo_path=None,
            repo_id=repo_id,
            sha256="a" * 64,
            size_bytes=1,
            file_count=1,
            created_at="2026-08-03T08:00:00Z",
            source_ref=filename,
            project_url=PROJECT_URL,
        )
    )


def _write_manifest(repo: Path, repositories: list[dict], *, project_id: str = PROJECT_ID) -> Path:
    path = repo / ".promptbranch-release-set.json"
    path.write_text(
        json.dumps(
            {
                "schema": "promptbranch.release_set",
                "schema_version": "1.0",
                "release_set_id": "kubernetes-2026-08-03",
                "project_id": project_id,
                "repositories": repositories,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _target(repo: Path, repo_id: str, version: str) -> dict:
    filename, digest = _artifact(repo, repo_id, version)
    return {
        "version": version,
        "artifact": filename,
        "sha256": digest,
        "local_path": filename,
    }


def _setup(monkeypatch, tmp_path: Path) -> dict[str, Path]:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repos = {
        "platform-gitops": _join(tmp_path, "platform-gitops", "deployment_dependency"),
        "my_awx": _join(tmp_path, "my_awx", "consumer"),
        "my_gitlab": _join(tmp_path, "my_gitlab", "consumer"),
        "vault-config": _join(tmp_path, "vault-config", "dependency"),
    }
    _add_current(project_registry_dir(PROJECT_ID), "vault-config", "v1.2.0")
    return repos


def test_version_constraints_use_numeric_canonical_versions() -> None:
    assert version_satisfies("v1.2.3", ">=v1.2.0,<v2.0.0") is True
    assert version_satisfies("v1.2.3", "v1.2.3") is True
    assert version_satisfies("v1.2.3", ">v1.2.3") is False


def test_release_set_plan_builds_dependency_order_waves_and_compatibility_matrix(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    manifest = _write_manifest(
        repos["platform-gitops"],
        [
            {
                "repo_id": "my_gitlab",
                "target": _target(repos["my_gitlab"], "my_gitlab", "v0.0.16"),
                "depends_on": [
                    {"repo_id": "platform-gitops", "constraint": ">=v0.0.7,<v0.1.0"},
                    {"repo_id": "vault-config", "constraint": ">=v1.0.0,<v2.0.0"},
                ],
            },
            {
                "repo_id": "platform-gitops",
                "target": _target(repos["platform-gitops"], "platform-gitops", "v0.0.7"),
                "depends_on": [],
            },
            {
                "repo_id": "my_awx",
                "target": _target(repos["my_awx"], "my_awx", "v0.0.237"),
                "depends_on": [{"repo_id": "platform-gitops", "constraint": ">=v0.0.7"}],
            },
        ],
    )

    result = build_release_set_plan(repos["platform-gitops"], manifest=manifest)

    assert result["ok"] is True
    assert result["status"] == "release_set_plan_ready"
    assert result["execution_ready"] is True
    assert result["execution_order"] == ["platform-gitops", "my_awx", "my_gitlab"]
    assert result["execution_waves"] == [["platform-gitops"], ["my_awx", "my_gitlab"]]
    assert result["compatibility_matrix"]["row_count"] == 3
    assert all(row["compatible"] for row in result["compatibility_matrix"]["rows"])
    external = next(row for row in result["compatibility_matrix"]["rows"] if row["dependency_repo_id"] == "vault-config")
    assert external["resolved_source"] == "project_current"
    assert external["resolved_version"] == "v1.2.0"
    assert len(result["plan_sha256"]) == 64
    assert result["safety"] == {
        "read_only": True,
        "state_mutated": False,
        "repository_mutated": False,
        "registry_mutated": False,
        "project_source_mutated": False,
        "publication_performed": False,
        "adoption_performed": False,
        "execution_performed": False,
    }


def test_release_set_plan_is_deterministic_and_read_only(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    manifest = _write_manifest(
        repos["platform-gitops"],
        [{"repo_id": "platform-gitops", "target": _target(repos["platform-gitops"], "platform-gitops", "v0.0.7"), "depends_on": []}],
    )
    watched = [
        manifest,
        repos["platform-gitops"] / ".promptbranch-repo.json",
        tmp_path / "config" / PROJECT_ID / "repos.json",
        project_registry_dir(PROJECT_ID) / "promptbranch_artifacts.json",
    ]
    before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in watched}

    first = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    second = build_release_set_plan(repos["platform-gitops"], manifest=manifest)

    after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in watched}
    assert first == second
    assert before == after


def test_release_set_plan_rejects_dependency_cycle(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    manifest = _write_manifest(
        repos["platform-gitops"],
        [
            {"repo_id": "platform-gitops", "target": _target(repos["platform-gitops"], "platform-gitops", "v0.0.7"), "depends_on": [{"repo_id": "my_awx", "constraint": ">=v0.0.237"}]},
            {"repo_id": "my_awx", "target": _target(repos["my_awx"], "my_awx", "v0.0.237"), "depends_on": [{"repo_id": "platform-gitops", "constraint": ">=v0.0.7"}]},
        ],
    )

    result = build_release_set_plan(repos["platform-gitops"], manifest=manifest)

    assert result["ok"] is False
    assert any(item["code"] == "release_set_dependency_cycle" for item in result["blockers"])


def test_release_set_plan_rejects_incompatible_target(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    manifest = _write_manifest(
        repos["platform-gitops"],
        [
            {"repo_id": "platform-gitops", "target": _target(repos["platform-gitops"], "platform-gitops", "v0.0.7"), "depends_on": []},
            {"repo_id": "my_awx", "target": _target(repos["my_awx"], "my_awx", "v0.0.237"), "depends_on": [{"repo_id": "platform-gitops", "constraint": ">=v0.0.8"}]},
        ],
    )

    result = build_release_set_plan(repos["platform-gitops"], manifest=manifest)

    assert result["ok"] is False
    assert any(item["code"] == "release_set_dependency_incompatible" for item in result["blockers"])


def test_release_set_plan_rejects_unknown_external_dependency(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    manifest = _write_manifest(
        repos["my_awx"],
        [{"repo_id": "my_awx", "target": _target(repos["my_awx"], "my_awx", "v0.0.237"), "depends_on": [{"repo_id": "missing-repo", "constraint": ">=v1.0.0"}]}],
    )

    result = build_release_set_plan(repos["my_awx"], manifest=manifest)

    assert result["ok"] is False
    assert any(item["code"] == "release_set_dependency_repo_unknown" for item in result["blockers"])


def test_release_set_plan_rejects_project_mismatch(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    manifest = _write_manifest(
        repos["platform-gitops"],
        [{"repo_id": "platform-gitops", "target": _target(repos["platform-gitops"], "platform-gitops", "v0.0.7"), "depends_on": []}],
        project_id="other-project",
    )

    result = build_release_set_plan(repos["platform-gitops"], manifest=manifest)

    assert result["ok"] is False
    assert any(item["code"] == "project_id_mismatch" for item in result["blockers"])


def test_release_set_plan_rejects_noncanonical_artifact_name(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    target = _target(repos["platform-gitops"], "platform-gitops", "v0.0.7")
    target["artifact"] = "wrong_v0.0.7.zip"
    manifest = _write_manifest(repos["platform-gitops"], [{"repo_id": "platform-gitops", "target": target, "depends_on": []}])

    result = build_release_set_plan(repos["platform-gitops"], manifest=manifest)

    assert result["ok"] is False
    assert any(item["code"] == "release_set_target_artifact_noncanonical" for item in result["blockers"])


def test_release_set_plan_rejects_local_artifact_sha_mismatch(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    target = _target(repos["platform-gitops"], "platform-gitops", "v0.0.7")
    target["sha256"] = "b" * 64
    manifest = _write_manifest(repos["platform-gitops"], [{"repo_id": "platform-gitops", "target": target, "depends_on": []}])

    result = build_release_set_plan(repos["platform-gitops"], manifest=manifest)

    assert result["ok"] is False
    assert any(item["code"] == "release_set_target_sha256_mismatch" for item in result["blockers"])


def test_release_set_plan_allows_compatible_unbound_target_but_not_execution_ready(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    manifest = _write_manifest(
        repos["platform-gitops"],
        [{"repo_id": "platform-gitops", "target": {"version": "v0.0.7", "artifact": "platform-gitops_v0.0.7.zip"}, "depends_on": []}],
    )

    result = build_release_set_plan(repos["platform-gitops"], manifest=manifest)

    assert result["ok"] is True
    assert result["execution_ready"] is False
    assert any(item["code"] == "release_set_target_artifact_unbound" for item in result["warnings"])


def test_release_set_cli_parser_exposes_read_only_plan_command() -> None:
    args = make_parser().parse_args([
        "release",
        "set",
        "plan",
        "--repo-path",
        "/tmp/repo",
        "--manifest",
        "set.json",
        "--json",
    ])
    assert args.command == "release"
    assert args.release_command == "set"
    assert args.release_set_command == "plan"
    assert args.repo_path == "/tmp/repo"
    assert args.manifest == "set.json"
    assert args.json is True


def test_release_set_plan_rejects_target_local_path_escape(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    manifest = _write_manifest(
        repos["platform-gitops"],
        [{
            "repo_id": "platform-gitops",
            "target": {
                "version": "v0.0.7",
                "artifact": "platform-gitops_v0.0.7.zip",
                "local_path": "../outside.zip",
            },
            "depends_on": [],
        }],
    )
    result = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    assert result["ok"] is False
    assert any(item["code"] == "release_set_target_local_path_invalid" for item in result["blockers"])


def test_release_set_plan_rejects_zip_version_mismatch(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    filename, digest = _artifact(repos["platform-gitops"], "platform-gitops", "v0.0.8")
    wrong_name = repos["platform-gitops"] / "platform-gitops_v0.0.7.zip"
    (repos["platform-gitops"] / filename).replace(wrong_name)
    manifest = _write_manifest(
        repos["platform-gitops"],
        [{
            "repo_id": "platform-gitops",
            "target": {
                "version": "v0.0.7",
                "artifact": wrong_name.name,
                "sha256": digest,
                "local_path": wrong_name.name,
            },
            "depends_on": [],
        }],
    )
    result = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    assert result["ok"] is False
    assert any(item["code"] == "release_set_target_version_mismatch" for item in result["blockers"])


def test_release_set_command_emits_plan_json(monkeypatch, tmp_path: Path, capsys) -> None:
    import asyncio
    from promptbranch_cli import cmd_release_set

    repos = _setup(monkeypatch, tmp_path)
    manifest = _write_manifest(
        repos["platform-gitops"],
        [{"repo_id": "platform-gitops", "target": _target(repos["platform-gitops"], "platform-gitops", "v0.0.7"), "depends_on": []}],
    )
    args = make_parser().parse_args([
        "release", "set", "plan",
        "--repo-path", str(repos["platform-gitops"]),
        "--manifest", str(manifest),
        "--json",
    ])
    rc = asyncio.run(cmd_release_set(None, args))
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["status"] == "release_set_plan_ready"
    assert payload["execution_order"] == ["platform-gitops"]


def test_release_set_schema_and_example_are_checked_in() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "promptbranch_protocol" / "schemas" / "release-set.schema.json").read_text(encoding="utf-8"))
    example = json.loads((root / "examples" / "release-set" / "kubernetes-release-set.example.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "promptbranch.release_set"
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert example["schema"] == "promptbranch.release_set"
    assert example["schema_version"] == "1.0"

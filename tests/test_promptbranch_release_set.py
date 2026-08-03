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
            source_requested_ref=filename,
            source_processed_file_id=f"file_{repo_id.replace('-', '')}_{version.replace('.', '').replace('v', '')}",
            source_library_metadata_object_id=f"libfile_{repo_id.replace('-', '')}_{version.replace('.', '').replace('v', '')}",
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


def _setup_rollout_currents(tmp_path: Path) -> None:
    project_dir = project_registry_dir(PROJECT_ID)
    _add_current(project_dir, "platform-gitops", "v0.0.6")
    _add_current(project_dir, "my_awx", "v0.0.236")
    _add_current(project_dir, "my_gitlab", "v0.0.15")


def _rollout_manifest(repos: dict[str, Path]) -> Path:
    return _write_manifest(
        repos["platform-gitops"],
        [
            {"repo_id": "platform-gitops", "target": _target(repos["platform-gitops"], "platform-gitops", "v0.0.7"), "depends_on": []},
            {"repo_id": "my_awx", "target": _target(repos["my_awx"], "my_awx", "v0.0.237"), "depends_on": [{"repo_id": "platform-gitops", "constraint": ">=v0.0.7"}]},
            {"repo_id": "my_gitlab", "target": _target(repos["my_gitlab"], "my_gitlab", "v0.0.16"), "depends_on": [{"repo_id": "platform-gitops", "constraint": ">=v0.0.7"}]},
        ],
    )


def _rollout_runner(plan: dict, *, fail_repo: str | None = None, fail_rollback: bool = False):
    import subprocess
    from datetime import datetime, timezone

    registry = ArtifactRegistry(project_registry_dir(PROJECT_ID))
    rows = {row["repo_id"]: row for row in plan["repositories"]}
    calls: list[dict] = []
    counter = {"value": 0}

    def add_current(
        repo_id: str, version: str, filename: str, sha256: str, *,
        source_ref: str | None = None, processed_file_id: str | None = None, library_id: str | None = None,
    ) -> None:
        counter["value"] += 1
        ArtifactRegistry(project_registry_dir(PROJECT_ID)).add(
            ArtifactRecord(
                path=str(Path(rows.get(repo_id, {}).get("repo_root") or "/tmp") / filename),
                filename=filename,
                kind="adopted_release",
                version=version,
                repo_path=None,
                repo_id=repo_id,
                sha256=sha256,
                size_bytes=1,
                file_count=1,
                created_at=datetime.now(timezone.utc).isoformat() + f"-{counter['value']}",
                source_ref=source_ref or filename,
                source_requested_ref=filename if processed_file_id else None,
                source_processed_file_id=processed_file_id,
                source_library_metadata_object_id=library_id,
                project_url=PROJECT_URL,
            )
        )

    def runner(argv, **kwargs):
        calls.append({"argv": list(argv), "env": dict(kwargs.get("env") or {})})
        command = list(argv)
        stdout = {"ok": True, "status": "simulated"}
        rc = 0
        if "pipeline" in command and "apply" in command:
            repo_root = Path(command[command.index("--repo-path") + 1])
            repo_id = repo_root.name
            if repo_id == fail_repo:
                rc = 1
                stdout = {"ok": False, "status": "simulated_apply_failure"}
            else:
                row = rows[repo_id]
                add_current(repo_id, row["target_version"], row["target_artifact"], row["target_sha256"])
                stdout = {"ok": True, "status": "release_adopted_and_verified"}
        elif "contract-execute" in command and "rollback" in command:
            env = kwargs.get("env") or {}
            repo_id = str(env["PROMPTBRANCH_ROLLBACK_REPO_ID"])
            if fail_rollback:
                rc = 1
                stdout = {"ok": False, "status": "simulated_rollback_failure"}
            else:
                add_current(
                    repo_id,
                    str(env["PROMPTBRANCH_ROLLBACK_VERSION"]),
                    str(env["PROMPTBRANCH_ROLLBACK_ARTIFACT"]),
                    str(env["PROMPTBRANCH_ROLLBACK_SHA256"]),
                    source_ref=str(env["PROMPTBRANCH_ROLLBACK_SOURCE_REF"]),
                    processed_file_id=str(env["PROMPTBRANCH_ROLLBACK_PROCESSED_FILE_ID"]),
                    library_id=str(env["PROMPTBRANCH_ROLLBACK_LIBRARY_METADATA_ID"]),
                )
                stdout = {"ok": True, "status": "rollback_artifact_restored"}
        return subprocess.CompletedProcess(command, rc, stdout=json.dumps(stdout), stderr="")

    return runner, calls


def _execute_rollout(repos: dict[str, Path], manifest: Path, plan: dict, runner):
    from promptbranch_release_set_rollout import execute_release_set

    return execute_release_set(
        repos["platform-gitops"],
        manifest=manifest,
        confirm_release_set_id=plan["release_set_id"],
        confirm_plan_sha256=plan["plan_sha256"],
        execute=True,
        rollback_on_failure=True,
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=runner,
    )


def test_release_set_apply_requires_exact_plan_and_complete_authorization(monkeypatch, tmp_path: Path) -> None:
    from promptbranch_release_set_rollout import execute_release_set

    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    called = False

    def runner(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("runner must not be called")

    result = execute_release_set(repos["platform-gitops"], manifest=manifest, runner=runner)
    assert result["ok"] is False
    assert called is False
    codes = {item["code"] for item in result["blockers"]}
    assert "release_set_confirmation_id_mismatch" in codes
    assert "release_set_confirmation_plan_sha256_mismatch" in codes
    assert "release_set_execute_flag_required" in codes
    assert "release_set_rollback_on_failure_required" in codes
    assert "release_set_pipeline_flags_required" in codes


def test_release_set_apply_executes_dependency_waves_and_writes_valid_hash_chain(monkeypatch, tmp_path: Path) -> None:
    from promptbranch_release_set_rollout import validate_rollout_evidence

    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    plan = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    runner, calls = _rollout_runner(plan)

    result = _execute_rollout(repos, manifest, plan, runner)

    assert result["ok"] is True
    assert result["status"] == "release_set_rollout_verified"
    assert [item["repo_id"] for item in result["repository_results"]] == ["platform-gitops", "my_awx", "my_gitlab"]
    assert result["rollback_results"] == []
    assert all(item["registry_verified"] for item in result["repository_results"])
    assert all("--verify-current" in item["argv"] for item in calls)
    validation = validate_rollout_evidence(result["summary_path"])
    assert validation["ok"] is True
    assert validation["event_count"] == len(result["events"])


def test_release_set_apply_failure_rolls_back_completed_repositories_in_reverse_order(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    plan = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    runner, calls = _rollout_runner(plan, fail_repo="my_awx")

    result = _execute_rollout(repos, manifest, plan, runner)

    assert result["ok"] is False
    assert result["status"] == "release_set_rollout_failed_rollback_verified"
    assert result["failed_repo_id"] == "my_awx"
    assert [item["repo_id"] for item in result["rollback_results"]] == ["platform-gitops"]
    assert result["rollback_results"][0]["registry_restored"] is True
    rollback_call = next(item for item in calls if "rollback" in item["argv"])
    assert rollback_call["env"]["PROMPTBRANCH_ROLLBACK_VERSION"] == "v0.0.6"
    assert rollback_call["env"]["PROMPTBRANCH_ROLLBACK_PROCESSED_FILE_ID"].startswith("file_")
    assert rollback_call["env"]["PROMPTBRANCH_ROLLBACK_LIBRARY_METADATA_ID"].startswith("libfile_")
    assert rollback_call["env"]["PROMPTBRANCH_RELEASE_SET_PLAN_SHA256"] == plan["plan_sha256"]


def test_release_set_apply_reports_incomplete_rollback_fail_closed(monkeypatch, tmp_path: Path) -> None:
    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    plan = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    runner, _ = _rollout_runner(plan, fail_repo="my_awx", fail_rollback=True)

    result = _execute_rollout(repos, manifest, plan, runner)

    assert result["ok"] is False
    assert result["status"] == "release_set_rollout_failed_rollback_incomplete"
    assert result["rollback_verified"] is False
    assert result["rollback_results"][0]["ok"] is False


def test_release_set_rollout_evidence_detects_tampering(monkeypatch, tmp_path: Path) -> None:
    from promptbranch_release_set_rollout import validate_rollout_evidence

    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    plan = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    runner, _ = _rollout_runner(plan)
    result = _execute_rollout(repos, manifest, plan, runner)
    summary = Path(result["summary_path"])
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["events"][1]["details"]["wave_index"] = 999
    summary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    validation = validate_rollout_evidence(summary)
    assert validation["ok"] is False
    assert any("hash mismatch" in item for item in validation["errors"])


def test_release_set_cli_parser_exposes_guarded_apply_and_evidence_validation() -> None:
    apply_args = make_parser().parse_args([
        "release", "set", "apply",
        "--confirm-release-set-id", "set-1",
        "--confirm-plan-sha256", "a" * 64,
        "--execute", "--rollback-on-failure", "--stage-all", "--commit", "--push", "--publish", "--adopt", "--verify-current",
        "--json",
    ])
    assert apply_args.release_set_command == "apply"
    assert apply_args.rollback_on_failure is True
    evidence_args = make_parser().parse_args(["release", "set", "evidence-validate", "--evidence", "/tmp/evidence", "--json"])
    assert evidence_args.release_set_command == "evidence-validate"


def test_release_contract_parser_allows_repository_owned_rollback_operation() -> None:
    args = make_parser().parse_args(["release", "contract-execute", "rollback", "--repo-path", "/tmp/repo", "--json"])
    assert args.operation == "rollback"


def test_release_set_rollout_schema_module_and_rollback_script_are_packaged() -> None:
    import os
    import tomllib

    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "promptbranch_protocol" / "schemas" / "release-set-rollout-evidence.schema.json").read_text(encoding="utf-8"))
    reconciliation_schema = json.loads((root / "promptbranch_protocol" / "schemas" / "release-set-rollout-reconciliation.schema.json").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    rollback_script = root / "scripts" / "rollback-release-artifact.py"
    assert schema["properties"]["schema"]["const"] == "promptbranch.release_set.rollout.evidence"
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert reconciliation_schema["properties"]["schema"]["const"] == "promptbranch.release_set.rollout.reconciliation"
    assert reconciliation_schema["properties"]["schema_version"]["const"] == "1.0"
    assert "promptbranch_release_set_rollout" in pyproject["tool"]["setuptools"]["py-modules"]
    assert rollback_script.is_file()
    assert os.access(rollback_script, os.X_OK)


def _latest_rollout_checkpoint(repo: Path, release_set_id: str) -> Path:
    root = repo / ".pb_profile" / "release_set_rollouts" / release_set_id
    checkpoints = sorted(root.glob(f"*/release-set-rollout-checkpoint.json"))
    assert checkpoints
    return checkpoints[-1]


def _resume_rollout(repos: dict[str, Path], manifest: Path, plan: dict, evidence: Path, reconciliation: dict, runner):
    from promptbranch_release_set_rollout import resume_release_set

    return resume_release_set(
        repos["platform-gitops"],
        manifest=manifest,
        evidence=evidence,
        confirm_release_set_id=plan["release_set_id"],
        confirm_plan_sha256=plan["plan_sha256"],
        confirm_reconciliation_sha256=reconciliation["reconciliation_sha256"],
        execute=True,
        rollback_on_failure=True,
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=runner,
    )


def test_release_set_reconcile_classifies_interrupted_rollout_without_mutation(monkeypatch, tmp_path: Path) -> None:
    import pytest
    from promptbranch_release_set_rollout import execute_release_set, reconcile_rollout_evidence

    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    plan = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    base_runner, calls = _rollout_runner(plan)

    def interrupt_after_first(argv, **kwargs):
        command = list(argv)
        if "pipeline" in command and "apply" in command:
            repo_root = Path(command[command.index("--repo-path") + 1])
            if repo_root.name == "my_awx":
                raise KeyboardInterrupt("simulated interruption")
        return base_runner(argv, **kwargs)

    with pytest.raises(KeyboardInterrupt):
        _execute_rollout(repos, manifest, plan, interrupt_after_first)

    checkpoint = _latest_rollout_checkpoint(repos["platform-gitops"], plan["release_set_id"])
    before = checkpoint.read_bytes()
    first = reconcile_rollout_evidence(repos["platform-gitops"], manifest=manifest, evidence=checkpoint)
    second = reconcile_rollout_evidence(repos["platform-gitops"], manifest=manifest, evidence=checkpoint)

    assert first == second
    assert first["ok"] is True
    assert first["status"] == "release_set_rollout_resume_ready"
    assert first["mode"] == "continue_rollout"
    assert first["pending_execution_order"] == ["my_awx", "my_gitlab"]
    assert next(item for item in first["repository_states"] if item["repo_id"] == "platform-gitops")["classification"] == "target_current"
    assert checkpoint.read_bytes() == before
    assert [Path(item["argv"][item["argv"].index("--repo-path") + 1]).name for item in calls if "pipeline" in item["argv"]] == ["platform-gitops"]


def test_release_set_resume_continues_without_replaying_verified_repository(monkeypatch, tmp_path: Path) -> None:
    import pytest
    from promptbranch_release_set_rollout import execute_release_set, reconcile_rollout_evidence, validate_rollout_evidence

    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    plan = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    base_runner, calls = _rollout_runner(plan)

    def interrupt_after_first(argv, **kwargs):
        command = list(argv)
        if "pipeline" in command and "apply" in command:
            repo_root = Path(command[command.index("--repo-path") + 1])
            if repo_root.name == "my_awx":
                raise KeyboardInterrupt("simulated interruption")
        return base_runner(argv, **kwargs)

    with pytest.raises(KeyboardInterrupt):
        execute_release_set(
            repos["platform-gitops"],
            manifest=manifest,
            confirm_release_set_id=plan["release_set_id"],
            confirm_plan_sha256=plan["plan_sha256"],
            execute=True,
            rollback_on_failure=True,
            stage_all=True,
            commit=True,
            push=True,
            publish=True,
            adopt=True,
            verify_current=True,
            runner=interrupt_after_first,
        )

    checkpoint = _latest_rollout_checkpoint(repos["platform-gitops"], plan["release_set_id"])
    reconciliation = reconcile_rollout_evidence(repos["platform-gitops"], manifest=manifest, evidence=checkpoint)
    result = _resume_rollout(repos, manifest, plan, checkpoint, reconciliation, base_runner)

    assert result["ok"] is True
    assert result["status"] == "release_set_rollout_verified"
    assert result["resume_count"] == 1
    assert validate_rollout_evidence(result["summary_path"])["ok"] is True
    apply_repos = [
        Path(item["argv"][item["argv"].index("--repo-path") + 1]).name
        for item in calls
        if "pipeline" in item["argv"] and "apply" in item["argv"]
    ]
    assert apply_repos == ["platform-gitops", "my_awx", "my_gitlab"]
    assert any(item["kind"] == "rollout_resume_started" for item in result["events"])


def test_release_set_resume_continues_interrupted_reverse_rollback(monkeypatch, tmp_path: Path) -> None:
    import pytest
    from promptbranch_release_set_rollout import execute_release_set, reconcile_rollout_evidence

    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    plan = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    failing_runner, _ = _rollout_runner(plan, fail_repo="my_awx")

    def interrupt_rollback(argv, **kwargs):
        command = list(argv)
        if "contract-execute" in command and "rollback" in command:
            raise KeyboardInterrupt("simulated rollback interruption")
        return failing_runner(argv, **kwargs)

    with pytest.raises(KeyboardInterrupt):
        _execute_rollout(repos, manifest, plan, interrupt_rollback)

    checkpoint = _latest_rollout_checkpoint(repos["platform-gitops"], plan["release_set_id"])
    reconciliation = reconcile_rollout_evidence(repos["platform-gitops"], manifest=manifest, evidence=checkpoint)
    assert reconciliation["mode"] == "resume_rollback"
    assert reconciliation["rollback_order"] == ["platform-gitops"]

    recovery_runner, recovery_calls = _rollout_runner(plan)
    result = _resume_rollout(repos, manifest, plan, checkpoint, reconciliation, recovery_runner)

    assert result["ok"] is False
    assert result["status"] == "release_set_rollout_failed_rollback_verified"
    assert result["rollback_verified"] is True
    assert [item["repo_id"] for item in result["rollback_results"]][-1:] == ["platform-gitops"]
    assert any("rollback" in item["argv"] for item in recovery_calls)
    assert not any("pipeline" in item["argv"] and "apply" in item["argv"] for item in recovery_calls)


def test_release_set_reconcile_finalizes_operator_repaired_incomplete_rollback(monkeypatch, tmp_path: Path) -> None:
    from datetime import datetime, timezone
    from promptbranch_release_set_rollout import reconcile_rollout_evidence

    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    plan = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    runner, _ = _rollout_runner(plan, fail_repo="my_awx", fail_rollback=True)
    failed = _execute_rollout(repos, manifest, plan, runner)
    assert failed["status"] == "release_set_rollout_failed_rollback_incomplete"

    previous = failed["pre_rollout_current"]["platform-gitops"]
    ArtifactRegistry(project_registry_dir(PROJECT_ID)).add(ArtifactRecord(
        path=str(repos["platform-gitops"] / previous["filename"]),
        filename=previous["filename"],
        kind="adopted_release",
        version=previous["version"],
        repo_path=None,
        repo_id="platform-gitops",
        sha256=previous["sha256"],
        size_bytes=1,
        file_count=1,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_ref=previous["source_ref"],
        source_requested_ref=previous["filename"],
        source_processed_file_id=previous["source_processed_file_id"],
        source_library_metadata_object_id=previous["source_library_metadata_object_id"],
        project_url=PROJECT_URL,
    ))

    reconciliation = reconcile_rollout_evidence(
        repos["platform-gitops"], manifest=manifest, evidence=failed["summary_path"]
    )
    assert reconciliation["ok"] is True
    assert reconciliation["mode"] == "finalize_rollback"
    no_calls: list[list[str]] = []

    def no_runner(argv, **kwargs):
        no_calls.append(list(argv))
        raise AssertionError("operator-repaired rollback finalization must not replay commands")

    result = _resume_rollout(
        repos, manifest, plan, Path(failed["summary_path"]), reconciliation, no_runner
    )
    assert result["status"] == "release_set_rollout_failed_rollback_verified"
    assert result["rollback_verified"] is True
    assert no_calls == []


def test_release_set_reconcile_blocks_ambiguous_current_identity(monkeypatch, tmp_path: Path) -> None:
    import pytest
    from datetime import datetime, timezone
    from promptbranch_release_set_rollout import execute_release_set, reconcile_rollout_evidence

    repos = _setup(monkeypatch, tmp_path)
    _setup_rollout_currents(tmp_path)
    manifest = _rollout_manifest(repos)
    plan = build_release_set_plan(repos["platform-gitops"], manifest=manifest)
    base_runner, _ = _rollout_runner(plan)

    def interrupt_after_first(argv, **kwargs):
        command = list(argv)
        if "pipeline" in command and "apply" in command:
            repo_root = Path(command[command.index("--repo-path") + 1])
            if repo_root.name == "my_awx":
                raise KeyboardInterrupt("simulated interruption")
        return base_runner(argv, **kwargs)

    with pytest.raises(KeyboardInterrupt):
        _execute_rollout(repos, manifest, plan, interrupt_after_first)
    checkpoint = _latest_rollout_checkpoint(repos["platform-gitops"], plan["release_set_id"])

    ArtifactRegistry(project_registry_dir(PROJECT_ID)).add(ArtifactRecord(
        path=str(repos["platform-gitops"] / "platform-gitops_v9.9.9.zip"),
        filename="platform-gitops_v9.9.9.zip",
        kind="adopted_release",
        version="v9.9.9",
        repo_path=None,
        repo_id="platform-gitops",
        sha256="f" * 64,
        size_bytes=1,
        file_count=1,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_ref="platform-gitops_v9.9.9.zip",
        source_requested_ref="platform-gitops_v9.9.9.zip",
        source_processed_file_id="file_ambiguous",
        source_library_metadata_object_id="libfile_ambiguous",
        project_url=PROJECT_URL,
    ))

    reconciliation = reconcile_rollout_evidence(repos["platform-gitops"], manifest=manifest, evidence=checkpoint)
    assert reconciliation["ok"] is False
    assert reconciliation["status"] == "release_set_rollout_reconciliation_blocked"
    assert any(item["code"] == "release_set_operator_reconciliation_required" for item in reconciliation["blockers"])


def test_release_set_cli_parser_exposes_reconcile_and_resume_commands() -> None:
    reconcile_args = make_parser().parse_args([
        "release", "set", "reconcile", "--evidence", "/tmp/checkpoint", "--json"
    ])
    assert reconcile_args.release_set_command == "reconcile"
    resume_args = make_parser().parse_args([
        "release", "set", "resume",
        "--evidence", "/tmp/checkpoint",
        "--confirm-release-set-id", "set-1",
        "--confirm-plan-sha256", "a" * 64,
        "--confirm-reconciliation-sha256", "b" * 64,
        "--execute", "--rollback-on-failure", "--stage-all", "--commit", "--push", "--publish", "--adopt", "--verify-current",
        "--json",
    ])
    assert resume_args.release_set_command == "resume"
    assert resume_args.confirm_reconciliation_sha256 == "b" * 64

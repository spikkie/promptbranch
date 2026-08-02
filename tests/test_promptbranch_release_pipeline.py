from __future__ import annotations

import json
import subprocess
import zipfile
import faulthandler
faulthandler.dump_traceback_later(20, repeat=True)
from pathlib import Path

from promptbranch_release_engine import load_contract
from promptbranch_release_pipeline import (
    build_pbai_compliance_inventory,
    build_release_pipeline_import_plan,
    build_release_pipeline_plan,
    execute_release_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]


def _write_minimal_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / ".promptbranch-repo.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_id": "g-p-demo",
                "project_home_url": "https://chatgpt.com/g/g-p-demo/project",
                "repo_id": "demo-repo",
                "artifact_pattern": "demo-repo_<version>.zip",
                "role": "release_authority",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "build_artifact.py").write_text(
        """from pathlib import Path\nimport zipfile\nroot=Path(__file__).resolve().parent\nout=root/'demo-repo_v1.2.3.zip'\nwith zipfile.ZipFile(out,'w') as z:\n    z.write(root/'VERSION','VERSION')\n""",
        encoding="utf-8",
    )
    contract = {
        "schema": "promptbranch.release.contract",
        "schema_version": "1.0",
        "repository": {"repo_id": "demo-repo"},
        "version_authority": {"path": "VERSION", "format": "plain"},
        "artifact": {
            "path": "demo-repo_v1.2.3.zip",
            "kind": "zip",
            "required_root_entries": ["VERSION"],
        },
        "operations": {
            "validate": [
                {"id": "validate", "argv": ["python3", "-c", "print('ok')"], "timeout_seconds": 30}
            ],
            "test": [
                {"id": "test", "argv": ["python3", "-c", "print('ok')"], "timeout_seconds": 30}
            ],
            "build": [
                {"id": "build", "argv": ["python3", "build_artifact.py"], "timeout_seconds": 30}
            ],
            "verify": [
                {"id": "verify", "argv": ["python3", "-c", "print('ok')"], "timeout_seconds": 30}
            ],
            "publish": [],
            "adopt": [],
            "verify_current": [],
        },
        "preserve": [".pb_profile/", ".promptbranch-repo.json"],
        "forbid_mutation": [".git/"],
        "environment": ["PATH", "HOME", "LANG"],
        "evidence": {"directory": ".pb_profile/release_runs"},
        "delegation": {
            "promptbranch_owns": ["state_machine", "evidence", "publication", "adoption"],
            "repository_owns": ["validation", "tests", "packaging"],
        },
        "git": {
            "unsafe_paths": [".pb_profile/", "*.zip"],
            "expected_paths": ["VERSION", "build_artifact.py", ".promptbranch-release.json"],
            "commit_message": "Release {version}",
        },
    }
    (repo / ".promptbranch-release.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return repo


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.adopted = False
        self.commit_sha = "a" * 40

    def __call__(self, argv, **kwargs):
        args = [str(value) for value in argv]
        self.calls.append(args)
        stdout = ""
        if args == ["python3", "build_artifact.py"]:
            repo = Path(kwargs.get("cwd", "."))
            with zipfile.ZipFile(repo / "demo-repo_v1.2.3.zip", "w") as archive:
                archive.write(repo / "VERSION", "VERSION")
        elif args[:2] == ["python3", "-c"]:
            stdout = "ok\n"
        elif args[:3] == ["git", "status", "--porcelain=v1"]:
            stdout = " M VERSION\n"
        elif args[:3] == ["git", "rev-parse", "HEAD"]:
            stdout = self.commit_sha + "\n"
        elif "src" in args and "add" in args:
            import hashlib
            artifact_path = Path(kwargs.get("cwd", ".")) / "demo-repo_v1.2.3.zip"
            stdout = json.dumps(
                {
                    "ok": True,
                    "status": "source_added",
                    "persistence_verified": True,
                    "requested_filename": "demo-repo_v1.2.3.zip",
                    "assigned_filename": "demo-repo_v1.2.3(1).zip",
                    "processed_file_id": "file_demo",
                    "library_metadata_object_id": "libfile_demo",
                    "local_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                }
            )
        elif "artifact" in args and "adopt" in args:
            self.adopted = True
            stdout = json.dumps(
                {
                    "ok": True,
                    "status": "adopted",
                    "source_verified": True,
                    "source_evidence_verified": True,
                    "artifact_registry_updated": True,
                    "state_artifact_updated": True,
                    "state_source_updated": True,
                }
            )
        elif "artifact" in args and "current" in args:
            if not self.adopted:
                stdout = json.dumps({"ok": True, "missing_repo_count": 1, "repos": {}})
                return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")
            artifact_path = Path(kwargs.get("cwd", ".")) / "demo-repo_v1.2.3.zip"
            import hashlib
            artifact_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            stdout = json.dumps(
                {
                    "ok": True,
                    "missing_repo_count": 0,
                    "repos": {
                        "demo-repo": {
                            "ok": True,
                            "state": {
                                "artifact_ref": "demo-repo_v1.2.3.zip",
                                "artifact_version": "v1.2.3",
                                "source_ref": "demo-repo_v1.2.3(1).zip",
                                "source_version": "v1.2.3",
                            },
                            "registry_current": {
                                "filename": "demo-repo_v1.2.3.zip",
                                "version": "v1.2.3",
                                "sha256": artifact_sha,
                            },
                            "consistency": {
                                "registry_current_matches_state_artifact": True,
                                "state_source_matches_state_artifact": True,
                            },
                        }
                    },
                }
            )
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")


def test_pipeline_plan_is_read_only_and_orders_publication_after_push(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    runner = FakeRunner()
    payload = build_release_pipeline_plan(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=runner,
    )
    assert payload["ok"] is True
    assert payload["status"] == "pipeline_planned_read_only"
    enabled = [item["id"] for item in payload["phases"] if item["enabled"]]
    assert enabled.index("git_push") < enabled.index("project_source_publish")
    assert enabled.index("project_source_publish") < enabled.index("artifact_adopt")
    assert enabled.index("artifact_adopt") < enabled.index("accepted_current_verify")
    assert payload["safety"]["state_mutated"] is False


def test_pipeline_plan_fails_closed_on_missing_dependencies(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    payload = build_release_pipeline_plan(repo, confirm_version="v1.2.3", publish=True)
    assert payload["ok"] is False
    assert "pipeline_publish_requires_push" in payload["blocker_codes"]


def test_pipeline_apply_captures_source_evidence_and_verifies_current(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    runner = FakeRunner()
    payload = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=runner,
    )
    assert payload["ok"] is True
    assert payload["status"] == "release_pipeline_completed"
    assert payload["source"]["assigned_filename"] == "demo-repo_v1.2.3(1).zip"
    assert payload["adoption"]["source_evidence_verified"] is True
    assert payload["current"]["repos"]["demo-repo"]["state"]["artifact_version"] == "v1.2.3"
    summary = Path(payload["evidence_dir"]) / "release-pipeline-summary.json"
    assert summary.is_file()
    adopt_call = next(call for call in runner.calls if "adopt" in call)
    assert "--source-evidence-json" in adopt_call
    source_call = next(call for call in runner.calls if "src" in call and "add" in call)
    assert "--no-overwrite" in source_call


def test_tracked_contract_declares_pipeline_git_safety():
    contract = load_contract(ROOT)
    assert contract["git"]["unsafe_paths"]
    assert contract["git"]["commit_message"] == "Release {version}"


def test_runtime_repository_is_rollout_ready_at_structural_level():
    payload = build_pbai_compliance_inventory([ROOT], level="structural")
    assert payload["ok"] is True
    assert payload["repository_count"] == 1
    item = payload["repositories"][0]
    assert item["application_id"] == "promptbranch"
    assert item["application_kind"] == "runtime_application"
    assert item["validation"]["ok"] is True
    assert item["release_contract"]["ok"] is True
    assert item["rollout_ready"] is True


class MismatchedCurrentRunner(FakeRunner):
    def __call__(self, argv, **kwargs):
        args = [str(value) for value in argv]
        if "artifact" in args and "current" in args and self.adopted:
            self.calls.append(args)
            artifact_path = Path(kwargs.get("cwd", ".")) / "demo-repo_v1.2.3.zip"
            import hashlib
            artifact_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            stdout = json.dumps(
                {
                    "ok": True,
                    "missing_repo_count": 0,
                    "repos": {
                        "demo-repo": {
                            "ok": True,
                            "state": {
                                "artifact_ref": "demo-repo_v1.2.3.zip",
                                "artifact_version": "v1.2.3",
                                "source_ref": "demo-repo_v1.2.3(99).zip",
                                "source_version": "v1.2.3",
                            },
                            "registry_current": {
                                "filename": "demo-repo_v1.2.3.zip",
                                "version": "v1.2.3",
                                "sha256": artifact_sha,
                            },
                            "consistency": {
                                "registry_current_matches_state_artifact": True,
                                "state_source_matches_state_artifact": True,
                            },
                        }
                    },
                }
            )
            return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")
        return super().__call__(args, **kwargs)


def test_pipeline_current_verification_requires_exact_assigned_source(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    runner = MismatchedCurrentRunner()
    payload = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=runner,
    )
    assert payload["ok"] is False
    assert payload["status"] == "release_pipeline_failed"
    assert payload["stop_reason"] == "accepted_current_verify_failed"
    current_phase = payload["phase_results"][-1]["payload"]
    assert current_phase["expected_source_ref"] == "demo-repo_v1.2.3(1).zip"
    assert current_phase["selected_repo_state"]["source_ref"] == "demo-repo_v1.2.3(99).zip"


def test_pipeline_cli_plan_is_read_only(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "promptbranch_cli.py"),
            "release",
            "pipeline",
            "plan",
            "--repo-path",
            str(repo),
            "--confirm-version",
            "v1.2.3",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "pipeline_planned_read_only"
    assert payload["safety"]["state_mutated"] is False
    assert not any(call for call in payload["requested_mutations"].values())

def test_release_validation_group_runner_help_and_contract_binding():
    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "run-release-validation-groups.py"),
            "--help",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert "required deterministic release-validation groups" in completed.stdout

    contract = json.loads((ROOT / ".promptbranch-release.json").read_text(encoding="utf-8"))
    test_steps = contract["operations"]["test"]
    assert any(
        step.get("argv")
        == [
            "python3",
            "scripts/run-release-validation-groups.py",
            "--repo",
            ".",
            "--json",
        ]
        for step in test_steps
    )



class ExistingIdentityRunner(FakeRunner):
    def __init__(self, *, conflict: bool) -> None:
        super().__init__()
        self.conflict = conflict

    def __call__(self, argv, **kwargs):
        args = [str(value) for value in argv]
        if "artifact" in args and "current" in args:
            self.calls.append(args)
            artifact_path = Path(kwargs.get("cwd", ".")) / "demo-repo_v1.2.3.zip"
            import hashlib
            artifact_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            current_sha = ("f" * 64) if self.conflict else artifact_sha
            stdout = json.dumps({
                "ok": True,
                "missing_repo_count": 0,
                "repos": {"demo-repo": {
                    "ok": True,
                    "state": {"artifact_ref": "demo-repo_v1.2.3.zip", "artifact_version": "v1.2.3", "source_ref": "demo-repo_v1.2.3(1).zip", "source_version": "v1.2.3"},
                    "registry_current": {"filename": "demo-repo_v1.2.3.zip", "version": "v1.2.3", "sha256": current_sha},
                    "consistency": {"registry_current_matches_state_artifact": True, "state_source_matches_state_artifact": True},
                }},
            })
            return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")
        return super().__call__(args, **kwargs)


def test_pipeline_same_version_same_hash_is_idempotent_and_skips_publication(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    runner = ExistingIdentityRunner(conflict=False)
    payload = execute_release_pipeline(repo, confirm_version="v1.2.3", stage_all=True, commit=True, push=True, publish=True, adopt=True, verify_current=True, runner=runner)
    assert payload["ok"] is True
    assert payload["status"] == "release_pipeline_completed_idempotent"
    assert payload["already_current"] is True
    assert not any("src" in call and "add" in call for call in runner.calls)
    assert not any("artifact" in call and "adopt" in call for call in runner.calls)


def test_pipeline_same_version_different_hash_fails_before_publication(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    runner = ExistingIdentityRunner(conflict=True)
    payload = execute_release_pipeline(repo, confirm_version="v1.2.3", stage_all=True, commit=True, push=True, publish=True, adopt=True, verify_current=True, runner=runner)
    assert payload["ok"] is False
    assert payload["stop_reason"] == "immutable_release_identity_conflict"
    assert not any("src" in call and "add" in call for call in runner.calls)
    assert not any("artifact" in call and "adopt" in call for call in runner.calls)


class PublishFailureRunner(FakeRunner):
    def __call__(self, argv, **kwargs):
        args = [str(value) for value in argv]
        if "src" in args and "add" in args:
            self.calls.append(args)
            return subprocess.CompletedProcess(
                args,
                1,
                stdout=json.dumps({
                    "ok": False,
                    "status": "source_add_failed",
                    "persistence_verified": False,
                }),
                stderr="",
            )
        return super().__call__(args, **kwargs)


class AdoptionFailureRunner(FakeRunner):
    def __call__(self, argv, **kwargs):
        args = [str(value) for value in argv]
        if "artifact" in args and "adopt" in args:
            self.calls.append(args)
            return subprocess.CompletedProcess(
                args,
                1,
                stdout=json.dumps({
                    "ok": False,
                    "status": "adoption_failed",
                    "source_verified": True,
                    "source_evidence_verified": True,
                }),
                stderr="",
            )
        return super().__call__(args, **kwargs)


def _run_failed_publish(repo: Path) -> tuple[dict, PublishFailureRunner]:
    runner = PublishFailureRunner()
    payload = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=runner,
    )
    assert payload["ok"] is False
    assert payload["stop_reason"] == "project_source_publish_failed"
    return payload, runner


def test_pipeline_failure_writes_incremental_checkpoint(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    payload, _ = _run_failed_publish(repo)
    checkpoint = Path(payload["checkpoint_path"])
    assert checkpoint.is_file()
    data = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert data["status"] == "release_pipeline_failed"
    assert data["stop_reason"] == "project_source_publish_failed"
    assert data["evidence_binding"]["artifact_sha256"] == payload["artifact"]["sha256"]
    assert data["evidence_binding"]["git_commit"] == "a" * 40
    assert any(item["phase"] == "git-sync" and item["ok"] for item in data["phase_results"])


def test_pipeline_import_is_read_only_and_recovers_git_boundary(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    payload, _ = _run_failed_publish(repo)
    before = sorted(str(path.relative_to(repo)) for path in repo.rglob("*"))
    plan = build_release_pipeline_import_plan(
        repo,
        evidence=payload["checkpoint_path"],
        confirm_version="v1.2.3",
        runner=FakeRunner(),
    )
    after = sorted(str(path.relative_to(repo)) for path in repo.rglob("*"))
    assert plan["ok"] is True
    assert plan["status"] == "pipeline_evidence_importable"
    assert plan["state_mutated"] is False
    assert "git-sync" in plan["reusable_mutation_phases"]
    assert "project-source-publish" not in plan["reusable_mutation_phases"]
    assert plan["first_incomplete_phase"] == "project-source-publish"
    assert before == after


def test_pipeline_resume_after_publish_failure_skips_git_and_recovers(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    failed, _ = _run_failed_publish(repo)
    runner = FakeRunner()
    recovered = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        resume_from=failed["checkpoint_path"],
        runner=runner,
    )
    assert recovered["ok"] is True
    assert recovered["status"] == "release_pipeline_recovered"
    assert "git-sync" in recovered["recovery"]["reused_phases"]
    assert any("src" in call and "add" in call for call in runner.calls)
    assert not any(call[:2] == ["git", "add"] for call in runner.calls)
    assert not any(call[:2] == ["git", "commit"] for call in runner.calls)
    assert not any(call[:2] == ["git", "push"] for call in runner.calls)
    reused_git = next(item for item in recovered["phase_results"] if item["phase"] == "git-sync")
    assert reused_git["payload"]["status"] == "reused_imported_git_sync"
    assert reused_git["payload"]["state_mutated"] is False


def test_pipeline_resume_reuses_published_source_after_adoption_failure(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    failing_runner = AdoptionFailureRunner()
    failed = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=failing_runner,
    )
    assert failed["stop_reason"] == "artifact_adopt_failed"

    runner = FakeRunner()
    recovered = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        resume_from=failed["checkpoint_path"],
        runner=runner,
    )
    assert recovered["ok"] is True
    assert recovered["status"] == "release_pipeline_recovered"
    assert "git-sync" in recovered["recovery"]["reused_phases"]
    assert "project-source-publish" in recovered["recovery"]["reused_phases"]
    assert not any("src" in call and "add" in call for call in runner.calls)
    assert any("artifact" in call and "adopt" in call for call in runner.calls)
    source_phase = next(item for item in recovered["phase_results"] if item["phase"] == "project-source-publish")
    assert source_phase["payload"]["status"] == "reused_imported_project_source"


def test_pipeline_resume_after_adoption_uses_current_identity_instead_of_replaying(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    mismatch = MismatchedCurrentRunner()
    failed = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=mismatch,
    )
    assert failed["stop_reason"] == "accepted_current_verify_failed"

    runner = FakeRunner()
    runner.adopted = True
    recovered = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        resume_from=failed["checkpoint_path"],
        runner=runner,
    )
    assert recovered["ok"] is True
    assert recovered["status"] == "release_pipeline_recovered_idempotent"
    assert recovered["already_current"] is True
    assert not any("src" in call and "add" in call for call in runner.calls)
    assert not any("artifact" in call and "adopt" in call for call in runner.calls)


def test_pipeline_import_rejects_changed_local_artifact_bytes(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    failed, _ = _run_failed_publish(repo)
    artifact = repo / "demo-repo_v1.2.3.zip"
    artifact.write_bytes(artifact.read_bytes() + b"changed")
    plan = build_release_pipeline_import_plan(
        repo,
        evidence=failed["checkpoint_path"],
        confirm_version="v1.2.3",
        runner=FakeRunner(),
    )
    assert plan["ok"] is False
    assert "pipeline_import_local_artifact_hash_mismatch" in plan["blocker_codes"]


def test_pipeline_cli_import_and_resume_commands(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    initial = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        runner=FakeRunner(),
    )
    assert initial["ok"] is True

    imported = subprocess.run(
        [
            "python3",
            str(ROOT / "promptbranch_cli.py"),
            "release",
            "pipeline",
            "import",
            "--repo-path",
            str(repo),
            "--confirm-version",
            "v1.2.3",
            "--evidence",
            initial["checkpoint_path"],
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert imported.returncode == 0, imported.stderr + imported.stdout
    import_payload = json.loads(imported.stdout)
    assert import_payload["status"] == "pipeline_evidence_importable"
    assert import_payload["state_mutated"] is False

    resumed = subprocess.run(
        [
            "python3",
            str(ROOT / "promptbranch_cli.py"),
            "release",
            "pipeline",
            "resume",
            "--repo-path",
            str(repo),
            "--confirm-version",
            "v1.2.3",
            "--evidence",
            initial["checkpoint_path"],
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert resumed.returncode == 0, resumed.stderr + resumed.stdout
    resume_payload = json.loads(resumed.stdout)
    assert resume_payload["status"] == "release_pipeline_recovered"
    assert resume_payload["recovery"]["mode"] == "resumed"


class MissingSourceHashRunner(FakeRunner):
    def __call__(self, argv, **kwargs):
        result = super().__call__(argv, **kwargs)
        args = [str(value) for value in argv]
        if "src" in args and "add" in args:
            payload = json.loads(result.stdout)
            payload.pop("local_sha256", None)
            return subprocess.CompletedProcess(args, result.returncode, stdout=json.dumps(payload), stderr=result.stderr)
        return result


class MissingCurrentHashRunner(FakeRunner):
    def __call__(self, argv, **kwargs):
        result = super().__call__(argv, **kwargs)
        args = [str(value) for value in argv]
        if "artifact" in args and "current" in args and self.adopted:
            payload = json.loads(result.stdout)
            payload["repos"]["demo-repo"]["registry_current"].pop("sha256", None)
            return subprocess.CompletedProcess(args, result.returncode, stdout=json.dumps(payload), stderr=result.stderr)
        return result


def test_pipeline_resume_requires_exact_imported_mutation_scope(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    failed, _ = _run_failed_publish(repo)
    runner = FakeRunner()
    blocked = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        resume_from=failed["checkpoint_path"],
        runner=runner,
    )
    assert blocked["ok"] is False
    assert blocked["status"] == "pipeline_resume_blocked"
    assert "pipeline_resume_commit_scope_mismatch" in blocked["blocker_codes"]
    assert "pipeline_resume_publish_scope_mismatch" in blocked["blocker_codes"]
    assert runner.calls
    assert not any("src" in call and "add" in call for call in runner.calls)
    assert not any(call[:2] == ["git", "add"] for call in runner.calls)


def test_pipeline_import_rejects_unsupported_schema_version(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    initial = execute_release_pipeline(repo, confirm_version="v1.2.3", runner=FakeRunner())
    checkpoint = Path(initial["checkpoint_path"])
    evidence = json.loads(checkpoint.read_text(encoding="utf-8"))
    evidence["schema_version"] = "99.0"
    altered = tmp_path / "unsupported-pipeline-evidence.json"
    altered.write_text(json.dumps(evidence), encoding="utf-8")

    plan = build_release_pipeline_import_plan(
        repo,
        evidence=altered,
        confirm_version="v1.2.3",
        runner=FakeRunner(),
    )
    assert plan["ok"] is False
    assert "pipeline_import_schema_version_unsupported" in plan["blocker_codes"]
    assert plan["state_mutated"] is False


def test_pipeline_publication_requires_exact_canonical_artifact_hash(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    payload = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=MissingSourceHashRunner(),
    )
    assert payload["ok"] is False
    assert payload["stop_reason"] == "project_source_publish_failed"
    publish_phase = next(item for item in payload["phase_results"] if item["phase"] == "project-source-publish")
    assert publish_phase["payload"]["status"] == "project_source_publication_unverified"


def test_pipeline_current_verification_requires_registry_sha256(tmp_path: Path):
    repo = _write_minimal_repo(tmp_path)
    payload = execute_release_pipeline(
        repo,
        confirm_version="v1.2.3",
        stage_all=True,
        commit=True,
        push=True,
        publish=True,
        adopt=True,
        verify_current=True,
        runner=MissingCurrentHashRunner(),
    )
    assert payload["ok"] is False
    assert payload["stop_reason"] == "accepted_current_verify_failed"
    current_phase = next(item for item in payload["phase_results"] if item["phase"] == "accepted-current-verify")
    assert current_phase["payload"]["status"] == "accepted_current_mismatch"

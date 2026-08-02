from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

from promptbranch_release_engine import load_contract
from promptbranch_release_pipeline import (
    build_pbai_compliance_inventory,
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

    def __call__(self, argv, **kwargs):
        args = [str(value) for value in argv]
        self.calls.append(args)
        stdout = ""
        if args[:3] == ["git", "status", "--porcelain=v1"]:
            stdout = " M VERSION\n"
        elif "src" in args and "add" in args:
            stdout = json.dumps(
                {
                    "ok": True,
                    "status": "source_added",
                    "persistence_verified": True,
                    "requested_filename": "demo-repo_v1.2.3.zip",
                    "assigned_filename": "demo-repo_v1.2.3(1).zip",
                    "processed_file_id": "file_demo",
                    "library_metadata_object_id": "libfile_demo",
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

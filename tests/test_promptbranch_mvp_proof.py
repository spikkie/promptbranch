from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from promptbranch_mvp_proof import (
    evaluate_mvp_proof_cycle,
    evaluate_mvp_proof_cycle_files,
    evaluate_mvp_proof_preflight,
)

REPO_ID = "chatgpt_claudecode_workflow-2"
VERSION = "v0.1.123"
BASELINE = "v0.1.122.1"
NEXT_VERSION = "v0.1.124"
ARTIFACT = f"{REPO_ID}_{VERSION}.zip"
ARTIFACT_SHA = hashlib.sha256(b"canonical candidate bytes").hexdigest()


def evidence() -> dict[str, dict]:
    return {
        "artifact_intake": {
            "ok": True,
            "status": "download_verified",
            "download_performed": True,
            "verification_performed": True,
            "candidate_version": VERSION,
            "candidate_artifact": ARTIFACT,
            "download": {
                "filename": ARTIFACT,
                "sha256": ARTIFACT_SHA,
            },
        },
        "all_tests": {
            "tested": 10,
            "succeeded": 10,
            "failed": 0,
            "skipped": 0,
            "final_verdict": "GO",
        },
        "visual_artifact": {
            "ok": True,
            "status": "smoke_zip_verified",
        },
        "adoption": {
            "ok": True,
            "status": "adopted",
            "artifact_version": VERSION,
            "artifact_ref": ARTIFACT,
            "local_artifact": {
                "filename": ARTIFACT,
                "version": VERSION,
                "sha256": ARTIFACT_SHA,
            },
        },
        "current": {
            "ok": True,
            "repos": {
                REPO_ID: {
                    "ok": True,
                    "state": {
                        "artifact_version": VERSION,
                        "artifact_ref": ARTIFACT,
                    },
                    "registry_current": {
                        "version": VERSION,
                        "filename": ARTIFACT,
                        "sha256": ARTIFACT_SHA,
                    },
                }
            },
        },
        "continuation_ask": {
            "ok": True,
            "request": {
                "schema": "promptbranch.ask.request",
                "baseline": {"version": VERSION},
                "target": {"version": NEXT_VERSION},
            },
        },
    }


def evaluate(parts: dict[str, dict]) -> dict:
    return evaluate_mvp_proof_cycle(
        cycle=1,
        version=VERSION,
        baseline_version=BASELINE,
        next_version=NEXT_VERSION,
        repo_id=REPO_ID,
        artifact_name=ARTIFACT,
        artifact_sha256=ARTIFACT_SHA,
        **parts,
    )


def test_mvp_proof_cycle_passes_only_with_complete_evidence() -> None:
    result = evaluate(evidence())
    assert result["ok"] is True
    assert result["status"] == "mvp_proof_cycle_passed"
    assert result["failed_checks"] == []
    assert result["artifact_sha256"] == ARTIFACT_SHA
    assert result["details"]["sha256_binding"] == {
        "candidate": ARTIFACT_SHA,
        "intake": ARTIFACT_SHA,
        "adoption": ARTIFACT_SHA,
        "current": ARTIFACT_SHA,
    }
    assert len(result["proof_sha256"]) == 64


def test_project_level_current_result_selects_repos_repo_id() -> None:
    result = evaluate(evidence())
    assert result["checks"]["current_repo_selected"] is True
    assert result["checks"]["current_version_matches"] is True
    assert result["details"]["current"]["repo_id"] == REPO_ID
    assert result["details"]["current"]["version"] == VERSION


def test_mvp_proof_cycle_rejects_missing_real_download_proof() -> None:
    parts = evidence()
    parts["artifact_intake"]["download_performed"] = False
    result = evaluate(parts)
    assert result["ok"] is False
    assert "artifact_download_performed" in result["failed_checks"]


def test_mvp_proof_cycle_rejects_repair_version_as_normal_cycle() -> None:
    parts = evidence()
    result = evaluate_mvp_proof_cycle(
        cycle=1,
        version="v0.1.123.1",
        baseline_version=VERSION,
        next_version="v0.1.124",
        repo_id=REPO_ID,
        artifact_name="chatgpt_claudecode_workflow-2_v0.1.123.1.zip",
        artifact_sha256=ARTIFACT_SHA,
        **parts,
    )
    assert result["ok"] is False
    assert "candidate_is_normal_release" in result["failed_checks"]


def test_mvp_proof_cycle_rejects_stale_continuation_baseline() -> None:
    parts = evidence()
    parts["continuation_ask"]["request"]["baseline"]["version"] = BASELINE
    result = evaluate(parts)
    assert result["ok"] is False
    assert "continuation_uses_adopted_baseline" in result["failed_checks"]


def test_mvp_proof_preflight_rejects_intake_sha_mismatch() -> None:
    parts = evidence()
    parts["artifact_intake"]["download"]["sha256"] = "0" * 64
    result = evaluate_mvp_proof_preflight(
        cycle=1,
        version=VERSION,
        baseline_version=BASELINE,
        next_version=NEXT_VERSION,
        repo_id=REPO_ID,
        artifact_name=ARTIFACT,
        artifact_sha256=ARTIFACT_SHA,
        artifact_intake=parts["artifact_intake"],
        all_tests=parts["all_tests"],
        visual_artifact=parts["visual_artifact"],
        adoption=parts["adoption"],
        current=parts["current"],
    )
    assert result["ok"] is False
    assert "artifact_intake_sha256_matches_candidate" in result["failed_checks"]
    assert "sha256_identity_all_equal" in result["failed_checks"]


def test_mvp_proof_cycle_rejects_adoption_sha_mismatch() -> None:
    parts = evidence()
    parts["adoption"]["local_artifact"]["sha256"] = "1" * 64
    result = evaluate(parts)
    assert result["ok"] is False
    assert "adoption_sha256_matches_candidate" in result["failed_checks"]
    assert "sha256_identity_all_equal" in result["failed_checks"]


def test_mvp_proof_cycle_rejects_current_sha_mismatch() -> None:
    parts = evidence()
    parts["current"]["repos"][REPO_ID]["registry_current"]["sha256"] = "2" * 64
    result = evaluate(parts)
    assert result["ok"] is False
    assert "current_sha256_matches_candidate" in result["failed_checks"]
    assert "sha256_identity_all_equal" in result["failed_checks"]


def test_file_evaluator_accepts_json_embedded_in_log(tmp_path: Path) -> None:
    parts = evidence()
    paths: dict[str, Path] = {}
    for name, payload in parts.items():
        path = tmp_path / f"{name}.log"
        path.write_text("noise before\n" + json.dumps(payload) + "\n", encoding="utf-8")
        paths[name] = path
    result = evaluate_mvp_proof_cycle_files(
        cycle=1,
        version=VERSION,
        baseline_version=BASELINE,
        next_version=NEXT_VERSION,
        repo_id=REPO_ID,
        artifact_name=ARTIFACT,
        artifact_sha256=ARTIFACT_SHA,
        artifact_intake_path=paths["artifact_intake"],
        all_tests_path=paths["all_tests"],
        visual_artifact_path=paths["visual_artifact"],
        adoption_path=paths["adoption"],
        current_path=paths["current"],
        continuation_ask_path=paths["continuation_ask"],
    )
    assert result["ok"] is True


def _write_finalizer_fixture(tmp_path: Path, *, invalid_intake: bool = False) -> tuple[Path, Path, Path, Path]:
    artifact_path = tmp_path / ARTIFACT
    artifact_path.write_bytes(b"canonical candidate bytes")
    assert hashlib.sha256(artifact_path.read_bytes()).hexdigest() == ARTIFACT_SHA

    release_log_dir = tmp_path / "logs"
    release_log_dir.mkdir()
    parts = evidence()
    if invalid_intake:
        parts["artifact_intake"]["download_performed"] = False
        parts["artifact_intake"]["ok"] = False
        parts["artifact_intake"]["status"] = "candidate_not_verified"
    intake_path = tmp_path / "artifact-intake.json"
    intake_path.write_text(json.dumps(parts["artifact_intake"]), encoding="utf-8")
    (release_log_dir / f"pb_test.all.{VERSION}.summary.json").write_text(json.dumps(parts["all_tests"]), encoding="utf-8")
    (release_log_dir / f"pb_test.visual_artifact_roundtrip.{VERSION}.log").write_text(json.dumps(parts["visual_artifact"]), encoding="utf-8")
    (release_log_dir / f"pb_artifact_adopt.{VERSION}.json").write_text(json.dumps(parts["adoption"]), encoding="utf-8")
    (release_log_dir / f"pb_artifact_current.{VERSION}.json").write_text(json.dumps(parts["current"]), encoding="utf-8")

    marker = tmp_path / "pb-called"
    fake_pb = tmp_path / "fake-pb"
    fake_pb.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called >> {marker!s}\n"
        "if [[ \" $* \" == *\" --print-request-json \"* ]]; then\n"
        f"  printf '%s\\n' '{json.dumps(parts['continuation_ask'])}'\n"
        "else\n"
        "  printf '%s\\n' '{\"ok\":true,\"status\":\"reply_validated\"}'\n"
        "fi\n",
        encoding="utf-8",
    )
    fake_pb.chmod(0o755)
    return artifact_path, release_log_dir, intake_path, fake_pb


def _run_finalizer(
    tmp_path: Path,
    *,
    invalid_intake: bool = False,
    stale_continuation: bool = False,
) -> subprocess.CompletedProcess[str]:
    artifact_path, release_log_dir, intake_path, fake_pb = _write_finalizer_fixture(
        tmp_path,
        invalid_intake=invalid_intake,
    )
    if stale_continuation:
        fake_pb.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s\\n' called >> {tmp_path / 'pb-called'}\n"
            "if [[ \" $* \" == *\" --print-request-json \"* ]]; then\n"
            f"  printf '%s\\n' '{{\"ok\":true,\"request\":{{\"schema\":\"promptbranch.ask.request\",\"baseline\":{{\"version\":\"{BASELINE}\"}},\"target\":{{\"version\":\"{NEXT_VERSION}\"}}}}}}'\n"
            "else\n"
            "  printf '%s\\n' '{\"ok\":true,\"status\":\"reply_validated\"}'\n"
            "fi\n",
            encoding="utf-8",
        )
        fake_pb.chmod(0o755)

    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "finalize-mvp-proof-cycle.sh"
    return subprocess.run(
        [
            str(script),
            "--cycle", "1",
            "--version", VERSION,
            "--baseline-version", BASELINE,
            "--next-version", NEXT_VERSION,
            "--repo-id", REPO_ID,
            "--artifact-intake", str(intake_path),
            "--artifact-path", str(artifact_path),
            "--release-log-dir", str(release_log_dir),
            "--pb-cmd", str(fake_pb),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_finalizer_invalid_intake_stops_before_continuation_ask(tmp_path: Path) -> None:
    completed = _run_finalizer(tmp_path, invalid_intake=True)
    combined = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert not (tmp_path / "pb-called").exists()
    assert "continuation ask was not issued" in combined
    assert "MVP proof cycle 1 verified" not in combined
    preflight = json.loads((tmp_path / "logs" / f"mvp-proof-cycle-1.preflight.{VERSION}.json").read_text(encoding="utf-8"))
    assert preflight["status"] == "mvp_proof_preflight_failed"


def test_finalizer_success_prints_verified_only_after_passed_proof(tmp_path: Path) -> None:
    completed = _run_finalizer(tmp_path)
    combined = completed.stdout + completed.stderr
    assert completed.returncode == 0, combined
    assert (tmp_path / "pb-called").read_text(encoding="utf-8").splitlines() == ["called", "called"]
    assert "MVP proof preflight passed" in combined
    assert "MVP proof cycle 1 verified" in combined
    proof = json.loads((tmp_path / "logs" / f"mvp-proof-cycle-1.{VERSION}.json").read_text(encoding="utf-8"))
    assert proof["status"] == "mvp_proof_cycle_passed"
    assert proof["ok"] is True


def test_finalizer_failed_full_proof_never_prints_verified_or_exits_zero(tmp_path: Path) -> None:
    completed = _run_finalizer(tmp_path, stale_continuation=True)
    combined = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert (tmp_path / "pb-called").read_text(encoding="utf-8").splitlines() == ["called", "called"]
    assert "MVP proof preflight passed" in combined
    assert "MVP proof cycle 1 verified" not in combined
    assert "failed verification" in combined
    proof = json.loads((tmp_path / "logs" / f"mvp-proof-cycle-1.{VERSION}.json").read_text(encoding="utf-8"))
    assert proof["status"] == "mvp_proof_cycle_failed"
    assert "continuation_uses_adopted_baseline" in proof["failed_checks"]


def test_finalize_wrapper_executes_continuation_and_forbids_release_mutation() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "finalize-mvp-proof-cycle.sh"
    text = script.read_text(encoding="utf-8")
    assert "set -Eeuo pipefail" in text
    assert "--preflight-only" in text
    assert text.index("--preflight-only") < text.index("--from-current-baseline")
    assert "--from-current-baseline" in text
    assert "--intent-kind mvp_proof_continuation" in text
    assert "--parse-reply" in text
    assert "scripts/verify-mvp-proof-cycle.py" in text
    assert "pb artifact adopt" not in text
    assert "pb src add" not in text
    assert "git commit" not in text
    assert "git push" not in text

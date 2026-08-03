from __future__ import annotations

import json
from pathlib import Path

from promptbranch_mvp_proof import evaluate_mvp_proof_cycle, evaluate_mvp_proof_cycle_files


def evidence() -> dict[str, dict]:
    version = "v0.1.122"
    artifact = "chatgpt_claudecode_workflow-2_v0.1.122.zip"
    return {
        "artifact_intake": {
            "ok": True,
            "download_performed": True,
            "verification_performed": True,
            "candidate_version": version,
            "candidate_artifact": artifact,
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
            "version": version,
        },
        "current": {
            "ok": True,
            "version": version,
            "filename": artifact,
        },
        "continuation_ask": {
            "ok": True,
            "request": {
                "schema": "promptbranch.ask.request",
                "baseline": {"version": version},
                "target": {"version": "v0.1.123"},
            },
        },
    }


def evaluate(parts: dict[str, dict]) -> dict:
    return evaluate_mvp_proof_cycle(
        cycle=1,
        version="v0.1.122",
        baseline_version="v0.1.121.1",
        next_version="v0.1.123",
        artifact_name="chatgpt_claudecode_workflow-2_v0.1.122.zip",
        **parts,
    )


def test_mvp_proof_cycle_passes_only_with_complete_evidence() -> None:
    result = evaluate(evidence())
    assert result["ok"] is True
    assert result["status"] == "mvp_proof_cycle_passed"
    assert result["failed_checks"] == []
    assert len(result["proof_sha256"]) == 64


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
        version="v0.1.122.1",
        baseline_version="v0.1.121.1",
        next_version="v0.1.123",
        artifact_name="chatgpt_claudecode_workflow-2_v0.1.122.1.zip",
        **parts,
    )
    assert result["ok"] is False
    assert "candidate_is_normal_release" in result["failed_checks"]


def test_mvp_proof_cycle_rejects_stale_continuation_baseline() -> None:
    parts = evidence()
    parts["continuation_ask"]["request"]["baseline"]["version"] = "v0.1.121.1"
    result = evaluate(parts)
    assert result["ok"] is False
    assert "continuation_uses_adopted_baseline" in result["failed_checks"]


def test_file_evaluator_accepts_json_embedded_in_log(tmp_path: Path) -> None:
    parts = evidence()
    paths: dict[str, Path] = {}
    for name, payload in parts.items():
        path = tmp_path / f"{name}.log"
        path.write_text("noise before\n" + json.dumps(payload) + "\n", encoding="utf-8")
        paths[name] = path
    result = evaluate_mvp_proof_cycle_files(
        cycle=1,
        version="v0.1.122",
        baseline_version="v0.1.121.1",
        next_version="v0.1.123",
        artifact_name="chatgpt_claudecode_workflow-2_v0.1.122.zip",
        artifact_intake_path=paths["artifact_intake"],
        all_tests_path=paths["all_tests"],
        visual_artifact_path=paths["visual_artifact"],
        adoption_path=paths["adoption"],
        current_path=paths["current"],
        continuation_ask_path=paths["continuation_ask"],
    )
    assert result["ok"] is True


def test_finalize_wrapper_executes_continuation_and_forbids_release_mutation() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "finalize-mvp-proof-cycle.sh"
    text = script.read_text(encoding="utf-8")
    assert "--from-current-baseline" in text
    assert "--intent-kind mvp_proof_continuation" in text
    assert "--parse-reply" in text
    assert "scripts/verify-mvp-proof-cycle.py" in text
    assert "pb artifact adopt" not in text
    assert "pb src add" not in text
    assert "git commit" not in text
    assert "git push" not in text

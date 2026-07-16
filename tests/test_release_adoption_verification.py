from __future__ import annotations

import json
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify-release-adoption-current.py"


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def _current_payload(*, processed_file_id: str = "file_exact", library_id: str = "libfile_exact") -> dict:
    version = "v1.2.3.4"
    canonical = "name.zip"
    assigned = "name(1).zip"
    return {
        "ok": True,
        "action": "artifact_current_all",
        "repos": {
            "repo": {
                "runtime": {"version": version},
                "state": {
                    "artifact_version": version,
                    "source_version": version,
                    "artifact_ref": canonical,
                    "source_ref": assigned,
                },
                "registry_current": {
                    "version": version,
                    "filename": canonical,
                    "source_ref": assigned,
                    "source_processed_file_id": processed_file_id,
                    "source_library_metadata_object_id": library_id,
                },
                "consistency": {
                    "registry_current_matches_state_artifact": True,
                    "state_source_matches_state_artifact": True,
                    "code_version_matches_state_source": True,
                },
            }
        },
    }


def _evidence_payload() -> dict:
    return {
        "ok": True,
        "status": "source_evidence_verified",
        "repo_id": "repo",
        "requested_filename": "name.zip",
        "assigned_filename": "name(1).zip",
        "processed_file_id": "file_exact",
        "library_metadata_object_id": "libfile_exact",
    }


def test_assigned_source_aware_fixture_passes(tmp_path: Path) -> None:
    current = _write_json(tmp_path / "current.json", _current_payload())
    evidence = _write_json(tmp_path / "evidence.json", _evidence_payload())

    result = subprocess.run(
        [str(SCRIPT), str(current), "v1.2.3.4", "name.zip", "--source-evidence-json", str(evidence)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "release_adopted_and_verified"
    assert payload["canonical_artifact_filename"] == "name.zip"
    assert payload["assigned_source_filename"] == "name(1).zip"
    assert payload["checks"]["state_source_ref_matches_assigned"] is True
    assert payload["checks"]["registry_processed_file_id_matches_evidence"] is True
    assert payload["checks"]["registry_library_metadata_object_id_matches_evidence"] is True


def test_backing_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    current = _write_json(tmp_path / "current.json", _current_payload(processed_file_id="file_wrong"))
    evidence = _write_json(tmp_path / "evidence.json", _evidence_payload())

    result = subprocess.run(
        [str(SCRIPT), str(current), "v1.2.3.4", "name.zip", "--source-evidence-json", str(evidence)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["status"] == "release_adoption_verification_failed"
    assert payload["checked"][0]["checks"]["registry_processed_file_id_matches_evidence"] is False


def test_canonical_source_ref_is_rejected_when_evidence_assigns_indexed_name(tmp_path: Path) -> None:
    payload = _current_payload()
    payload["repos"]["repo"]["state"]["source_ref"] = "name.zip"
    current = _write_json(tmp_path / "current.json", payload)
    evidence = _write_json(tmp_path / "evidence.json", _evidence_payload())

    result = subprocess.run(
        [str(SCRIPT), str(current), "v1.2.3.4", "name.zip", "--source-evidence-json", str(evidence)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["status"] == "release_adoption_verification_failed"
    assert output["checked"][0]["checks"]["state_source_ref_matches_assigned"] is False


def test_manual_canonical_source_verification_remains_supported(tmp_path: Path) -> None:
    payload = _current_payload()
    payload["repos"]["repo"]["state"]["source_ref"] = "name.zip"
    current = _write_json(tmp_path / "current.json", payload)

    result = subprocess.run([str(SCRIPT), str(current), "v1.2.3.4", "name.zip"], text=True, capture_output=True)

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["status"] == "release_adopted_and_verified"
    assert output["verification_mode"] == "canonical_source_ref"

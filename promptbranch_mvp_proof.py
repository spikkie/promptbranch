from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_REPO_ID = "chatgpt_claudecode_workflow-2"


def _read_json_payload(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        raise ValueError(f"empty JSON evidence: {source}")
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    objects: list[tuple[int, int, dict[str, Any]]] = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, consumed = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            objects.append((consumed, index, value))
    if not objects:
        raise ValueError(f"no JSON object found in evidence: {source}")
    # Prefer the largest complete object. This avoids selecting a nested object
    # when a command log contains one top-level JSON payload plus leading text.
    objects.sort(key=lambda item: (item[0], item[1]))
    return objects[-1][2]


def _deep_get(payload: Mapping[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = payload
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                break
            current = current[key]
        else:
            return current
    return None


def _normal_version(value: str) -> bool:
    return bool(VERSION_RE.fullmatch(value))


def _normal_sha256(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if SHA256_RE.fullmatch(normalized) else None


def _artifact_version(payload: Mapping[str, Any]) -> str | None:
    value = _deep_get(
        payload,
        ("candidate_version",),
        ("artifact_version",),
        ("version",),
        ("zip_version",),
        ("expected_version",),
        ("artifact", "version"),
        ("selected_artifact", "version"),
        ("selected_candidate", "version"),
        ("candidate", "version"),
        ("local_artifact", "version"),
        ("zip", "version"),
    )
    return value if isinstance(value, str) else None


def _artifact_filename(payload: Mapping[str, Any]) -> str | None:
    value = _deep_get(
        payload,
        ("candidate_artifact",),
        ("artifact_ref",),
        ("filename",),
        ("artifact", "filename"),
        ("selected_artifact", "filename"),
        ("selected_candidate", "filename"),
        ("candidate", "filename"),
        ("download", "filename"),
        ("local_artifact", "filename"),
        ("zip", "filename"),
    )
    return value if isinstance(value, str) else None


def _artifact_sha256(payload: Mapping[str, Any]) -> str | None:
    value = _deep_get(
        payload,
        ("candidate_sha256",),
        ("artifact_sha256",),
        ("sha256",),
        ("artifact", "sha256"),
        ("selected_artifact", "sha256"),
        ("selected_candidate", "sha256"),
        ("candidate", "sha256"),
        ("download", "sha256"),
        ("verification", "sha256"),
        ("local_artifact", "sha256"),
        ("zip", "sha256"),
        ("after_snapshot", "artifact_registry", "current", "sha256"),
        ("source_evidence", "raw_evidence", "local_sha256"),
    )
    return _normal_sha256(value)


def _request_envelope(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = _deep_get(
        payload,
        ("request",),
        ("request_envelope",),
        ("protocol_request",),
        ("result", "request"),
    )
    return candidate if isinstance(candidate, Mapping) else payload


def _current_repo_payload(current: Mapping[str, Any], repo_id: str) -> tuple[Mapping[str, Any] | None, str | None]:
    repos = current.get("repos") if isinstance(current.get("repos"), Mapping) else None
    if repos is None:
        return current, None
    selected = repos.get(repo_id)
    if isinstance(selected, Mapping):
        return selected, repo_id
    return None, None


def _current_identity(current: Mapping[str, Any], repo_id: str) -> dict[str, Any]:
    selected, selected_repo_id = _current_repo_payload(current, repo_id)
    if selected is None:
        return {
            "selected_repo_id": None,
            "selected_repo": None,
            "version": None,
            "filename": None,
            "sha256": None,
        }
    version = _deep_get(
        selected,
        ("version",),
        ("current_version",),
        ("artifact", "version"),
        ("state", "artifact_version"),
        ("current", "version"),
        ("registry_current", "version"),
        ("baseline_roles", "registry_current_version"),
    )
    filename = _deep_get(
        selected,
        ("filename",),
        ("current_artifact",),
        ("artifact", "filename"),
        ("state", "artifact_ref"),
        ("current", "filename"),
        ("registry_current", "filename"),
        ("baseline_roles", "registry_current_ref"),
    )
    sha256 = _deep_get(
        selected,
        ("sha256",),
        ("current_sha256",),
        ("artifact", "sha256"),
        ("current", "sha256"),
        ("registry_current", "sha256"),
    )
    return {
        "selected_repo_id": selected_repo_id,
        "selected_repo": selected,
        "version": version if isinstance(version, str) else None,
        "filename": filename if isinstance(filename, str) else None,
        "sha256": _normal_sha256(sha256),
    }


def _base_checks(
    *,
    cycle: int,
    version: str,
    baseline_version: str,
    next_version: str,
    repo_id: str,
    artifact_name: str,
    artifact_sha256: str,
    artifact_intake: Mapping[str, Any],
    all_tests: Mapping[str, Any],
    visual_artifact: Mapping[str, Any],
    adoption: Mapping[str, Any],
    current: Mapping[str, Any],
) -> tuple[dict[str, bool], dict[str, Any]]:
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    normalized_candidate_sha = _normal_sha256(artifact_sha256)
    checks["cycle_is_positive"] = cycle >= 1
    checks["candidate_is_normal_release"] = _normal_version(version)
    checks["next_is_normal_release"] = _normal_version(next_version)
    checks["baseline_differs_from_candidate"] = baseline_version != version
    checks["candidate_sha256_valid"] = normalized_candidate_sha is not None

    intake_version = _artifact_version(artifact_intake)
    intake_filename = _artifact_filename(artifact_intake)
    intake_sha256 = _artifact_sha256(artifact_intake)
    intake_status = artifact_intake.get("status")
    checks["artifact_intake_ok"] = artifact_intake.get("ok") is True
    checks["artifact_download_performed"] = artifact_intake.get("download_performed") is True
    checks["artifact_verification_performed"] = artifact_intake.get("verification_performed") is True
    checks["artifact_intake_status_verified"] = intake_status in {
        "download_verified",
        "verified_candidate",
        "manual_import_verified",
        "migrated_candidate",
    }
    checks["artifact_intake_version_matches"] = intake_version == version
    checks["artifact_intake_filename_matches"] = intake_filename == artifact_name
    checks["artifact_intake_sha256_present"] = intake_sha256 is not None
    checks["artifact_intake_sha256_matches_candidate"] = (
        normalized_candidate_sha is not None and intake_sha256 == normalized_candidate_sha
    )
    details["artifact_intake"] = {
        "status": intake_status,
        "version": intake_version,
        "filename": intake_filename,
        "sha256": intake_sha256,
    }

    tested = _deep_get(all_tests, ("tested",), ("totals", "tested"), ("summary", "tested"), ("release_summary", "tested"), ("step_count",))
    failed = _deep_get(all_tests, ("failed",), ("totals", "failed"), ("summary", "failed"), ("release_summary", "failed"), ("failure_count",))
    skipped = _deep_get(all_tests, ("skipped",), ("totals", "skipped"), ("summary", "skipped"), ("release_summary", "skipped"), ("skipped_count",))
    succeeded = _deep_get(all_tests, ("succeeded",), ("totals", "succeeded"), ("summary", "succeeded"), ("release_summary", "succeeded"))
    if succeeded is None and all(isinstance(value, int) for value in (tested, failed, skipped)):
        succeeded = tested - failed - skipped
    verdict = _deep_get(all_tests, ("final_verdict",), ("all_tests_final_verdict",), ("summary", "final_verdict"), ("release_summary", "final_verdict"))
    checks["all_tests_go"] = str(verdict).upper() == "GO"
    checks["all_tests_10_of_10"] = tested in (10, "10/10", "10") and succeeded in (10, "10")
    checks["all_tests_no_failure_or_skip"] = failed in (0, "0") and skipped in (0, "0")
    details["all_tests"] = {"tested": tested, "succeeded": succeeded, "failed": failed, "skipped": skipped, "verdict": verdict}

    visual_status = _deep_get(visual_artifact, ("verification_status",), ("smoke_verification", "status"), ("status",), ("download_transport", "status"), ("verification", "status"))
    visual_ok = visual_artifact.get("ok") is True or _deep_get(visual_artifact, ("smoke_verification", "ok")) is True or _deep_get(visual_artifact, ("verification", "ok")) is True
    checks["visual_artifact_transport_verified"] = visual_ok and visual_status in {
        "smoke_zip_verified",
        "visual_artifact_roundtrip_verified",
        "verified",
        "passed",
    }
    details["visual_artifact_status"] = visual_status

    adoption_status = adoption.get("status")
    adopted_version = _artifact_version(adoption)
    adopted_filename = _artifact_filename(adoption)
    adopted_sha256 = _artifact_sha256(adoption)
    checks["adoption_ok"] = adoption.get("ok") is True and adoption_status in {"adopted", "adopted_local"}
    checks["adoption_version_matches"] = adopted_version == version
    checks["adoption_artifact_matches"] = adopted_filename == artifact_name
    checks["adoption_sha256_present"] = adopted_sha256 is not None
    checks["adoption_sha256_matches_candidate"] = (
        normalized_candidate_sha is not None and adopted_sha256 == normalized_candidate_sha
    )
    details["adoption"] = {
        "status": adoption_status,
        "version": adopted_version,
        "filename": adopted_filename,
        "sha256": adopted_sha256,
    }

    current_identity = _current_identity(current, repo_id)
    current_selected = current_identity["selected_repo"]
    current_ok = current.get("ok") is True and isinstance(current_selected, Mapping) and current_selected.get("ok") is not False
    current_version = current_identity["version"]
    current_filename = current_identity["filename"]
    current_sha256 = current_identity["sha256"]
    checks["current_ok"] = current_ok
    checks["current_repo_selected"] = current_identity["selected_repo_id"] == repo_id or "repos" not in current
    checks["current_version_matches"] = current_version == version
    checks["current_artifact_matches"] = current_filename == artifact_name
    checks["current_sha256_present"] = current_sha256 is not None
    checks["current_sha256_matches_candidate"] = (
        normalized_candidate_sha is not None and current_sha256 == normalized_candidate_sha
    )
    details["current"] = {
        "repo_id": current_identity["selected_repo_id"],
        "version": current_version,
        "filename": current_filename,
        "sha256": current_sha256,
    }

    identity_values = [normalized_candidate_sha, intake_sha256, adopted_sha256, current_sha256]
    checks["sha256_identity_all_equal"] = (
        normalized_candidate_sha is not None
        and all(value == normalized_candidate_sha for value in identity_values)
    )
    details["sha256_binding"] = {
        "candidate": normalized_candidate_sha,
        "intake": intake_sha256,
        "adoption": adopted_sha256,
        "current": current_sha256,
    }
    return checks, details


def _finalize_result(
    *,
    schema: str,
    status_passed: str,
    status_failed: str,
    cycle: int,
    version: str,
    baseline_version: str,
    next_version: str,
    repo_id: str,
    artifact_name: str,
    artifact_sha256: str,
    checks: Mapping[str, bool],
    details: Mapping[str, Any],
    digest_field: str,
) -> dict[str, Any]:
    failed_checks = sorted(name for name, ok in checks.items() if not ok)
    canonical: dict[str, Any] = {
        "schema": schema,
        "schema_version": "1.1",
        "cycle": cycle,
        "release_mode": "normal",
        "version": version,
        "baseline_version": baseline_version,
        "next_version": next_version,
        "repo_id": repo_id,
        "artifact": artifact_name,
        "artifact_sha256": artifact_sha256,
        "checks": dict(checks),
        "details": dict(details),
        "failed_checks": failed_checks,
        "ok": not failed_checks,
        "status": status_passed if not failed_checks else status_failed,
    }
    digest_payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    canonical[digest_field] = hashlib.sha256(digest_payload).hexdigest()
    return canonical


def evaluate_mvp_proof_preflight(
    *,
    cycle: int,
    version: str,
    baseline_version: str,
    next_version: str,
    repo_id: str = DEFAULT_REPO_ID,
    artifact_name: str,
    artifact_sha256: str,
    artifact_intake: Mapping[str, Any],
    all_tests: Mapping[str, Any],
    visual_artifact: Mapping[str, Any],
    adoption: Mapping[str, Any],
    current: Mapping[str, Any],
) -> dict[str, Any]:
    checks, details = _base_checks(
        cycle=cycle,
        version=version,
        baseline_version=baseline_version,
        next_version=next_version,
        repo_id=repo_id,
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha256,
        artifact_intake=artifact_intake,
        all_tests=all_tests,
        visual_artifact=visual_artifact,
        adoption=adoption,
        current=current,
    )
    return _finalize_result(
        schema="promptbranch.mvp.proof_cycle_preflight",
        status_passed="mvp_proof_preflight_passed",
        status_failed="mvp_proof_preflight_failed",
        cycle=cycle,
        version=version,
        baseline_version=baseline_version,
        next_version=next_version,
        repo_id=repo_id,
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha256,
        checks=checks,
        details=details,
        digest_field="preflight_sha256",
    )


def evaluate_mvp_proof_cycle(
    *,
    cycle: int,
    version: str,
    baseline_version: str,
    next_version: str,
    repo_id: str = DEFAULT_REPO_ID,
    artifact_name: str,
    artifact_sha256: str,
    artifact_intake: Mapping[str, Any],
    all_tests: Mapping[str, Any],
    visual_artifact: Mapping[str, Any],
    adoption: Mapping[str, Any],
    current: Mapping[str, Any],
    continuation_ask: Mapping[str, Any],
) -> dict[str, Any]:
    checks, details = _base_checks(
        cycle=cycle,
        version=version,
        baseline_version=baseline_version,
        next_version=next_version,
        repo_id=repo_id,
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha256,
        artifact_intake=artifact_intake,
        all_tests=all_tests,
        visual_artifact=visual_artifact,
        adoption=adoption,
        current=current,
    )

    request = _request_envelope(continuation_ask)
    request_baseline = _deep_get(
        request,
        ("baseline", "version"),
        ("artifact", "current_version"),
        ("artifact", "baseline_version"),
        ("baseline_version",),
        ("current_version",),
    )
    request_target = _deep_get(
        request,
        ("target", "version"),
        ("artifact", "target_version"),
        ("target_version",),
    )
    continuation_run = continuation_ask.get("run") if isinstance(continuation_ask.get("run"), Mapping) else continuation_ask
    continuation_ok = continuation_run.get("ok") is True and request.get("schema") == "promptbranch.ask.request"
    checks["continuation_ask_ok"] = continuation_ok
    checks["continuation_uses_adopted_baseline"] = request_baseline == version
    checks["continuation_targets_next_normal"] = request_target == next_version
    details["continuation"] = {
        "baseline_version": request_baseline,
        "target_version": request_target,
    }

    return _finalize_result(
        schema="promptbranch.mvp.proof_cycle",
        status_passed="mvp_proof_cycle_passed",
        status_failed="mvp_proof_cycle_failed",
        cycle=cycle,
        version=version,
        baseline_version=baseline_version,
        next_version=next_version,
        repo_id=repo_id,
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha256,
        checks=checks,
        details=details,
        digest_field="proof_sha256",
    )


def evaluate_mvp_proof_preflight_files(
    *,
    cycle: int,
    version: str,
    baseline_version: str,
    next_version: str,
    repo_id: str = DEFAULT_REPO_ID,
    artifact_name: str,
    artifact_sha256: str,
    artifact_intake_path: str | Path,
    all_tests_path: str | Path,
    visual_artifact_path: str | Path,
    adoption_path: str | Path,
    current_path: str | Path,
) -> dict[str, Any]:
    return evaluate_mvp_proof_preflight(
        cycle=cycle,
        version=version,
        baseline_version=baseline_version,
        next_version=next_version,
        repo_id=repo_id,
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha256,
        artifact_intake=_read_json_payload(artifact_intake_path),
        all_tests=_read_json_payload(all_tests_path),
        visual_artifact=_read_json_payload(visual_artifact_path),
        adoption=_read_json_payload(adoption_path),
        current=_read_json_payload(current_path),
    )


def evaluate_mvp_proof_cycle_files(
    *,
    cycle: int,
    version: str,
    baseline_version: str,
    next_version: str,
    repo_id: str = DEFAULT_REPO_ID,
    artifact_name: str,
    artifact_sha256: str,
    artifact_intake_path: str | Path,
    all_tests_path: str | Path,
    visual_artifact_path: str | Path,
    adoption_path: str | Path,
    current_path: str | Path,
    continuation_ask_path: str | Path,
) -> dict[str, Any]:
    return evaluate_mvp_proof_cycle(
        cycle=cycle,
        version=version,
        baseline_version=baseline_version,
        next_version=next_version,
        repo_id=repo_id,
        artifact_name=artifact_name,
        artifact_sha256=artifact_sha256,
        artifact_intake=_read_json_payload(artifact_intake_path),
        all_tests=_read_json_payload(all_tests_path),
        visual_artifact=_read_json_payload(visual_artifact_path),
        adoption=_read_json_payload(adoption_path),
        current=_read_json_payload(current_path),
        continuation_ask=_read_json_payload(continuation_ask_path),
    )

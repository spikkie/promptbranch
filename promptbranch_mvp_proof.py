from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+$")


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


def _artifact_version(payload: Mapping[str, Any]) -> str | None:
    value = _deep_get(
        payload,
        ("candidate_version",),
        ("artifact_version",),
        ("version",),
        ("artifact", "version"),
        ("selected_artifact", "version"),
        ("candidate", "version"),
    )
    return value if isinstance(value, str) else None


def _request_envelope(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = _deep_get(
        payload,
        ("request",),
        ("request_envelope",),
        ("protocol_request",),
        ("result", "request"),
    )
    return candidate if isinstance(candidate, Mapping) else payload


def evaluate_mvp_proof_cycle(
    *,
    cycle: int,
    version: str,
    baseline_version: str,
    next_version: str,
    artifact_name: str,
    artifact_intake: Mapping[str, Any],
    all_tests: Mapping[str, Any],
    visual_artifact: Mapping[str, Any],
    adoption: Mapping[str, Any],
    current: Mapping[str, Any],
    continuation_ask: Mapping[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    checks["cycle_is_positive"] = cycle >= 1
    checks["candidate_is_normal_release"] = _normal_version(version)
    checks["next_is_normal_release"] = _normal_version(next_version)
    checks["baseline_differs_from_candidate"] = baseline_version != version

    intake_version = _artifact_version(artifact_intake)
    intake_filename = _deep_get(
        artifact_intake,
        ("candidate_artifact",),
        ("artifact", "filename"),
        ("selected_artifact", "filename"),
        ("filename",),
    )
    checks["artifact_intake_ok"] = artifact_intake.get("ok") is True
    checks["artifact_download_performed"] = artifact_intake.get("download_performed") is True
    checks["artifact_verification_performed"] = artifact_intake.get("verification_performed") is True
    checks["artifact_intake_version_matches"] = intake_version in (None, version)
    checks["artifact_intake_filename_matches"] = intake_filename in (None, artifact_name)
    details["artifact_intake_version"] = intake_version
    details["artifact_intake_filename"] = intake_filename

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
    checks["adoption_ok"] = adoption.get("ok") is True and adoption_status in {"adopted", "adopted_local"}
    checks["adoption_version_matches"] = adopted_version in (None, version)
    details["adoption_status"] = adoption_status
    details["adoption_version"] = adopted_version

    current_version = _deep_get(
        current,
        ("version",),
        ("current_version",),
        ("artifact", "version"),
        ("state", "artifact_version"),
        ("current", "version"),
        ("registry_current", "version"),
    )
    current_filename = _deep_get(
        current,
        ("filename",),
        ("current_artifact",),
        ("artifact", "filename"),
        ("state", "artifact_ref"),
        ("current", "filename"),
        ("registry_current", "filename"),
    )
    checks["current_ok"] = current.get("ok") is True
    checks["current_version_matches"] = current_version == version
    checks["current_artifact_matches"] = current_filename in (None, artifact_name)
    details["current_version"] = current_version
    details["current_filename"] = current_filename

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
    details["continuation_baseline_version"] = request_baseline
    details["continuation_target_version"] = request_target

    failed_checks = sorted(name for name, ok in checks.items() if not ok)
    canonical = {
        "schema": "promptbranch.mvp.proof_cycle",
        "schema_version": "1.0",
        "cycle": cycle,
        "release_mode": "normal",
        "version": version,
        "baseline_version": baseline_version,
        "next_version": next_version,
        "artifact": artifact_name,
        "checks": checks,
        "details": details,
        "failed_checks": failed_checks,
        "ok": not failed_checks,
        "status": "mvp_proof_cycle_passed" if not failed_checks else "mvp_proof_cycle_failed",
    }
    digest_payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    canonical["proof_sha256"] = hashlib.sha256(digest_payload).hexdigest()
    return canonical


def evaluate_mvp_proof_cycle_files(
    *,
    cycle: int,
    version: str,
    baseline_version: str,
    next_version: str,
    artifact_name: str,
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
        artifact_name=artifact_name,
        artifact_intake=_read_json_payload(artifact_intake_path),
        all_tests=_read_json_payload(all_tests_path),
        visual_artifact=_read_json_payload(visual_artifact_path),
        adoption=_read_json_payload(adoption_path),
        current=_read_json_payload(current_path),
        continuation_ask=_read_json_payload(continuation_ask_path),
    )

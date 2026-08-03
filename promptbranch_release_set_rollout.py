from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from promptbranch_artifacts import ArtifactRegistry, canonical_version_tag
from promptbranch_project import configured_repos, project_registry_dir
from promptbranch_release_set import build_release_set_plan

ROLLOUT_EVIDENCE_SCHEMA = "promptbranch.release_set.rollout.evidence"
ROLLOUT_EVIDENCE_SCHEMA_VERSION = "1.0"
ROLLOUT_CHECKPOINT_FILENAME = "release-set-rollout-checkpoint.json"
ROLLOUT_SUMMARY_FILENAME = "release-set-rollout-summary.json"
Runner = Callable[..., subprocess.CompletedProcess[str]]


class ReleaseSetRolloutError(ValueError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseSetRolloutError(f"invalid rollout evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseSetRolloutError(f"rollout evidence root must be an object: {path}")
    return value


def _pb_command() -> list[str]:
    override = str(os.environ.get("PROMPTBRANCH_RELEASE_SET_PB_COMMAND") or "").strip()
    return [override] if override else [sys.executable, "-m", "promptbranch.cli"]


def _command(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    runner: Runner,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started_at = _utc()
    try:
        completed = runner(
            list(argv),
            cwd=str(cwd),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "status": "command_timeout",
            "argv": list(argv),
            "cwd": str(cwd),
            "started_at": started_at,
            "finished_at": _utc(),
            "timeout_seconds": timeout_seconds,
            "stdout": exc.stdout if isinstance(exc.stdout, str) else "",
            "stderr": exc.stderr if isinstance(exc.stderr, str) else "",
        }
    except OSError as exc:
        return {
            "ok": False,
            "status": "command_execution_error",
            "argv": list(argv),
            "cwd": str(cwd),
            "started_at": started_at,
            "finished_at": _utc(),
            "error": str(exc),
        }
    parsed: dict[str, Any] | None = None
    if completed.stdout.strip():
        try:
            candidate = json.loads(completed.stdout)
            if isinstance(candidate, dict):
                parsed = candidate
        except json.JSONDecodeError:
            parsed = None
    ok = completed.returncode == 0 and (parsed is None or parsed.get("ok", True) is True)
    return {
        "ok": ok,
        "status": (parsed or {}).get("status") or ("command_passed" if ok else "command_failed"),
        "argv": list(argv),
        "cwd": str(cwd),
        "started_at": started_at,
        "finished_at": _utc(),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": parsed,
    }


def _event(events: list[dict[str, Any]], *, kind: str, repo_id: str | None, details: dict[str, Any]) -> dict[str, Any]:
    previous = events[-1]["event_sha256"] if events else None
    body = {
        "sequence": len(events) + 1,
        "recorded_at": _utc(),
        "kind": kind,
        "repo_id": repo_id,
        "previous_event_sha256": previous,
        "details": details,
    }
    body["event_sha256"] = _canonical_digest(body)
    events.append(body)
    return body


def _current_identity(registry: ArtifactRegistry, repo_id: str) -> dict[str, Any] | None:
    current = registry.current(repo_id=repo_id)
    if not isinstance(current, dict):
        return None
    return {
        "repo_id": repo_id,
        "version": current.get("version"),
        "filename": current.get("filename"),
        "sha256": current.get("sha256"),
        "source_ref": current.get("source_ref"),
        "source_processed_file_id": current.get("source_processed_file_id"),
        "source_library_metadata_object_id": current.get("source_library_metadata_object_id"),
    }


def _identity_matches(observed: dict[str, Any] | None, expected: dict[str, Any]) -> bool:
    if not isinstance(observed, dict):
        return False
    keys = (
        "repo_id", "version", "filename", "sha256", "source_ref",
        "source_processed_file_id", "source_library_metadata_object_id",
    )
    required = [key for key in keys if expected.get(key) not in (None, "")]
    return bool(required) and all(observed.get(key) == expected.get(key) for key in required)


def _evidence_dir(repo: Path, release_set_id: str, run_id: str) -> Path:
    safe_id = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in release_set_id)
    return repo / ".pb_profile" / "release_set_rollouts" / safe_id / run_id


def _base_payload(repo: Path, manifest: str | Path, plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "schema": ROLLOUT_EVIDENCE_SCHEMA,
        "schema_version": ROLLOUT_EVIDENCE_SCHEMA_VERSION,
        "action": "release_set_apply",
        "status": "release_set_rollout_blocked",
        "repo_path": str(repo),
        "manifest_path": str(Path(manifest)),
        "release_set_id": plan.get("release_set_id"),
        "project_id": plan.get("project_id"),
        "plan_sha256": plan.get("plan_sha256"),
        "execution_order": plan.get("execution_order") or [],
        "execution_waves": plan.get("execution_waves") or [],
        "blockers": [],
        "warnings": [],
        "events": [],
        "repository_results": [],
        "rollback_results": [],
        "safety": {
            "explicit_execution_confirmation_required": True,
            "exact_plan_binding_required": True,
            "automatic_rollback_on_failure_required": True,
            "project_source_mutation_possible": False,
            "publication_possible": False,
            "adoption_possible": False,
            "execution_performed": False,
            "rollback_performed": False,
        },
    }


def _validate_authorization(
    payload: dict[str, Any],
    plan: dict[str, Any],
    *,
    confirm_release_set_id: str | None,
    confirm_plan_sha256: str | None,
    execute: bool,
    rollback_on_failure: bool,
    stage_all: bool,
    commit: bool,
    push: bool,
    publish: bool,
    adopt: bool,
    verify_current: bool,
    timeout_seconds: float,
) -> None:
    blockers = payload["blockers"]
    if not plan.get("ok"):
        blockers.append({"code": "release_set_plan_blocked", "message": "release-set plan is not compatible", "details": {"plan_blockers": plan.get("blockers") or []}})
    if not plan.get("execution_ready"):
        blockers.append({"code": "release_set_plan_not_execution_ready", "message": "all target artifacts must be locally verified and SHA-256 bound"})
    if str(confirm_release_set_id or "") != str(plan.get("release_set_id") or ""):
        blockers.append({"code": "release_set_confirmation_id_mismatch", "message": "--confirm-release-set-id must exactly match the plan"})
    if str(confirm_plan_sha256 or "").lower() != str(plan.get("plan_sha256") or "").lower():
        blockers.append({"code": "release_set_confirmation_plan_sha256_mismatch", "message": "--confirm-plan-sha256 must exactly match the recomputed plan"})
    if not execute:
        blockers.append({"code": "release_set_execute_flag_required", "message": "--execute is required for rollout mutation"})
    if not rollback_on_failure:
        blockers.append({"code": "release_set_rollback_on_failure_required", "message": "--rollback-on-failure is required"})
    if timeout_seconds <= 0 or timeout_seconds > 14400:
        blockers.append({"code": "release_set_timeout_invalid", "message": "--timeout-seconds must satisfy 0 < timeout <= 14400"})
    required_flags = {
        "stage_all": stage_all,
        "commit": commit,
        "push": push,
        "publish": publish,
        "adopt": adopt,
        "verify_current": verify_current,
    }
    missing = sorted(name for name, enabled in required_flags.items() if not enabled)
    if missing:
        blockers.append({"code": "release_set_pipeline_flags_required", "message": "guarded rollout requires the complete per-repository release pipeline", "details": {"missing": missing}})


def execute_release_set(
    repo_path: str | Path = ".",
    *,
    manifest: str | Path = ".promptbranch-release-set.json",
    confirm_release_set_id: str | None = None,
    confirm_plan_sha256: str | None = None,
    execute: bool = False,
    rollback_on_failure: bool = False,
    stage_all: bool = False,
    commit: bool = False,
    push: bool = False,
    publish: bool = False,
    adopt: bool = False,
    verify_current: bool = False,
    timeout_seconds: float = 14400.0,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    plan = build_release_set_plan(repo, manifest=manifest)
    payload = _base_payload(repo, manifest, plan)
    _validate_authorization(
        payload,
        plan,
        confirm_release_set_id=confirm_release_set_id,
        confirm_plan_sha256=confirm_plan_sha256,
        execute=execute,
        rollback_on_failure=rollback_on_failure,
        stage_all=stage_all,
        commit=commit,
        push=push,
        publish=publish,
        adopt=adopt,
        verify_current=verify_current,
        timeout_seconds=timeout_seconds,
    )
    if payload["blockers"]:
        return payload

    run_id = _run_id()
    evidence_dir = _evidence_dir(repo, str(plan["release_set_id"]), run_id)
    checkpoint = evidence_dir / ROLLOUT_CHECKPOINT_FILENAME
    summary = evidence_dir / ROLLOUT_SUMMARY_FILENAME
    payload.update({"run_id": run_id, "evidence_dir": str(evidence_dir), "checkpoint_path": str(checkpoint), "summary_path": str(summary)})
    payload["safety"].update({
        "project_source_mutation_possible": True,
        "publication_possible": True,
        "adoption_possible": True,
    })

    registry = ArtifactRegistry(project_registry_dir(str(plan["project_id"])))
    configured = configured_repos(str(plan["project_id"]))
    rows = {str(row["repo_id"]): row for row in plan.get("repositories") or []}
    pre_current = {repo_id: _current_identity(registry, repo_id) for repo_id in rows}
    payload["pre_rollout_current"] = pre_current
    _event(payload["events"], kind="rollout_started", repo_id=None, details={"plan_sha256": plan["plan_sha256"], "pre_rollout_current": pre_current})
    _atomic_write_json(checkpoint, payload)

    completed: list[str] = []
    failed_repo: str | None = None
    for wave_index, wave in enumerate(plan.get("execution_waves") or [], start=1):
        _event(payload["events"], kind="wave_started", repo_id=None, details={"wave_index": wave_index, "repositories": list(wave)})
        _atomic_write_json(checkpoint, payload)
        for repo_id in wave:
            row = rows[repo_id]
            cfg = configured.get(repo_id) or {}
            repo_root = Path(str(cfg.get("repo_root") or row.get("repo_root") or "")).expanduser().resolve()
            argv = [
                *_pb_command(), "release", "pipeline", "apply",
                "--repo-path", str(repo_root),
                "--confirm-version", str(row["target_version"]),
                "--stage-all", "--commit", "--push", "--publish", "--adopt", "--verify-current", "--json",
            ]
            result = _command(argv, cwd=repo_root, timeout_seconds=timeout_seconds, runner=runner, env=dict(os.environ))
            observed = _current_identity(registry, repo_id)
            expected = {
                "repo_id": repo_id,
                "version": row.get("target_version"),
                "filename": row.get("target_artifact"),
                "sha256": row.get("target_sha256"),
            }
            registry_verified = _identity_matches(observed, expected)
            repo_result = {
                "repo_id": repo_id,
                "wave_index": wave_index,
                "target": expected,
                "command": result,
                "registry_observed": observed,
                "registry_verified": registry_verified,
                "ok": bool(result.get("ok")) and registry_verified,
                "status": "repository_rollout_verified" if bool(result.get("ok")) and registry_verified else "repository_rollout_failed",
            }
            payload["repository_results"].append(repo_result)
            _event(payload["events"], kind="repository_rollout_result", repo_id=repo_id, details=repo_result)
            _atomic_write_json(checkpoint, payload)
            if not repo_result["ok"]:
                failed_repo = repo_id
                break
            completed.append(repo_id)
        if failed_repo:
            break
        _event(payload["events"], kind="wave_completed", repo_id=None, details={"wave_index": wave_index, "repositories": list(wave)})
        _atomic_write_json(checkpoint, payload)

    if failed_repo is not None:
        payload["status"] = "release_set_rollout_failed_rolling_back"
        for repo_id in reversed(completed):
            cfg = configured.get(repo_id) or {}
            repo_root = Path(str(cfg.get("repo_root") or rows[repo_id].get("repo_root") or "")).expanduser().resolve()
            previous = pre_current.get(repo_id)
            env = dict(os.environ)
            env.update({
                "PROMPTBRANCH_RELEASE_SET_ID": str(plan["release_set_id"]),
                "PROMPTBRANCH_RELEASE_SET_PLAN_SHA256": str(plan["plan_sha256"]),
                "PROMPTBRANCH_ROLLBACK_REPO_ID": repo_id,
                "PROMPTBRANCH_ROLLBACK_VERSION": str((previous or {}).get("version") or ""),
                "PROMPTBRANCH_ROLLBACK_ARTIFACT": str((previous or {}).get("filename") or ""),
                "PROMPTBRANCH_ROLLBACK_SHA256": str((previous or {}).get("sha256") or ""),
                "PROMPTBRANCH_ROLLBACK_SOURCE_REF": str((previous or {}).get("source_ref") or ""),
                "PROMPTBRANCH_ROLLBACK_PROCESSED_FILE_ID": str((previous or {}).get("source_processed_file_id") or ""),
                "PROMPTBRANCH_ROLLBACK_LIBRARY_METADATA_ID": str((previous or {}).get("source_library_metadata_object_id") or ""),
                "PROMPTBRANCH_ROLLBACK_PROJECT_ID": str(plan["project_id"]),
            })
            argv = [*_pb_command(), "release", "contract-execute", "rollback", "--repo-path", str(repo_root), "--json"]
            result = _command(argv, cwd=repo_root, timeout_seconds=timeout_seconds, runner=runner, env=env)
            observed = _current_identity(registry, repo_id)
            restored = previous is not None and _identity_matches(observed, previous)
            rollback_result = {
                "repo_id": repo_id,
                "previous_identity": previous,
                "command": result,
                "registry_observed": observed,
                "registry_restored": restored,
                "ok": bool(result.get("ok")) and restored,
                "status": "repository_rollback_verified" if bool(result.get("ok")) and restored else "repository_rollback_failed",
            }
            payload["rollback_results"].append(rollback_result)
            _event(payload["events"], kind="repository_rollback_result", repo_id=repo_id, details=rollback_result)
            _atomic_write_json(checkpoint, payload)
        rollback_ok = len(payload["rollback_results"]) == len(completed) and all(item.get("ok") for item in payload["rollback_results"])
        payload["ok"] = False
        payload["status"] = "release_set_rollout_failed_rollback_verified" if rollback_ok else "release_set_rollout_failed_rollback_incomplete"
        payload["failed_repo_id"] = failed_repo
        payload["rollback_verified"] = rollback_ok
        payload["safety"]["execution_performed"] = True
        payload["safety"]["rollback_performed"] = bool(completed)
    else:
        payload["ok"] = True
        payload["status"] = "release_set_rollout_verified"
        payload["rollback_verified"] = None
        payload["safety"]["execution_performed"] = True
        _event(payload["events"], kind="rollout_completed", repo_id=None, details={"repository_count": len(completed)})

    payload["final_event_sha256"] = payload["events"][-1]["event_sha256"] if payload["events"] else None
    evidence_body = {key: value for key, value in payload.items() if key != "evidence_sha256"}
    payload["evidence_sha256"] = _canonical_digest(evidence_body)
    _atomic_write_json(checkpoint, payload)
    _atomic_write_json(summary, payload)
    return payload



_TERMINAL_ROLLOUT_STATUSES = {
    "release_set_rollout_verified",
    "release_set_rollout_failed_rollback_verified",
    "release_set_rollout_failed_rollback_incomplete",
}


def _resolve_rollout_evidence_path(path: str | Path, *, prefer_checkpoint: bool = True) -> Path:
    evidence_path = Path(path).expanduser().resolve()
    if evidence_path.is_dir():
        names = (
            (ROLLOUT_CHECKPOINT_FILENAME, ROLLOUT_SUMMARY_FILENAME)
            if prefer_checkpoint
            else (ROLLOUT_SUMMARY_FILENAME, ROLLOUT_CHECKPOINT_FILENAME)
        )
        for name in names:
            candidate = evidence_path / name
            if candidate.is_file():
                return candidate
    return evidence_path


def _checkpoint_validation_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != ROLLOUT_EVIDENCE_SCHEMA:
        errors.append("unsupported rollout evidence schema")
    if payload.get("schema_version") != ROLLOUT_EVIDENCE_SCHEMA_VERSION:
        errors.append("unsupported rollout evidence schema version")
    if payload.get("action") != "release_set_apply":
        errors.append("unsupported rollout evidence action")
    previous: str | None = None
    events = payload.get("events") if isinstance(payload.get("events"), list) else []
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            errors.append(f"event {index} is not an object")
            break
        expected_hash = event.get("event_sha256")
        body = {key: value for key, value in event.items() if key != "event_sha256"}
        if event.get("sequence") != index:
            errors.append(f"event {index} sequence mismatch")
        if event.get("previous_event_sha256") != previous:
            errors.append(f"event {index} previous hash mismatch")
        if expected_hash != _canonical_digest(body):
            errors.append(f"event {index} hash mismatch")
        previous = str(expected_hash or "") or None
    if payload.get("final_event_sha256") not in (None, "") and payload.get("final_event_sha256") != previous:
        errors.append("final event hash mismatch")
    if payload.get("evidence_sha256") not in (None, ""):
        expected_evidence = payload.get("evidence_sha256")
        body = {key: value for key, value in payload.items() if key != "evidence_sha256"}
        if expected_evidence != _canonical_digest(body):
            errors.append("evidence SHA-256 mismatch")
    return errors


def _target_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo_id": str(row.get("repo_id") or ""),
        "version": row.get("target_version"),
        "filename": row.get("target_artifact"),
        "sha256": row.get("target_sha256"),
    }


def _previous_identity_matches(observed: dict[str, Any] | None, previous: dict[str, Any] | None) -> bool:
    if previous is None:
        return observed is None
    return _identity_matches(observed, previous)


def _recovered_plan_sha256(plan: dict[str, Any], pre_current: dict[str, Any]) -> str:
    repositories: list[dict[str, Any]] = []
    for row in plan.get("repositories") or []:
        recovered = dict(row)
        previous = pre_current.get(str(row.get("repo_id") or "")) if isinstance(pre_current, dict) else None
        recovered["current_version"] = (previous or {}).get("version")
        recovered["current_artifact"] = (previous or {}).get("filename")
        recovered["current_sha256"] = (previous or {}).get("sha256")
        recovered["change_required"] = bool(
            recovered.get("target_version")
            and canonical_version_tag((previous or {}).get("version")) != recovered.get("target_version")
        )
        repositories.append(recovered)
    digest_input = {
        "schema": plan.get("schema"),
        "schema_version": plan.get("schema_version"),
        "release_set_id": plan.get("release_set_id"),
        "project_id": plan.get("project_id"),
        "repositories": repositories,
        "compatibility_matrix": (plan.get("compatibility_matrix") or {}).get("rows") or [],
        "execution_order": plan.get("execution_order") or [],
        "execution_waves": plan.get("execution_waves") or [],
    }
    return _canonical_digest(digest_input)


def _repository_reconciliation_state(
    *,
    repo_id: str,
    observed: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    target: dict[str, Any],
) -> dict[str, Any]:
    target_current = _identity_matches(observed, target)
    previous_current = _previous_identity_matches(observed, previous)
    if target_current:
        classification = "target_current"
    elif previous_current:
        classification = "previous_current"
    elif observed is None:
        classification = "missing_current"
    else:
        classification = "ambiguous_current"
    return {
        "repo_id": repo_id,
        "classification": classification,
        "target_current": target_current,
        "previous_current": previous_current,
        "observed_identity": observed,
        "previous_identity": previous,
        "target_identity": target,
    }


def reconcile_rollout_evidence(
    repo_path: str | Path = ".",
    *,
    manifest: str | Path = ".promptbranch-release-set.json",
    evidence: str | Path,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    evidence_path = _resolve_rollout_evidence_path(evidence, prefer_checkpoint=True)
    try:
        checkpoint_payload = _read_json(evidence_path)
    except ReleaseSetRolloutError as exc:
        return {
            "ok": False,
            "action": "release_set_reconcile",
            "status": "release_set_rollout_reconciliation_blocked",
            "repo_path": str(repo),
            "manifest_path": str(Path(manifest)),
            "evidence_path": str(evidence_path),
            "blockers": [{"code": "release_set_evidence_invalid", "message": str(exc)}],
            "state_mutated": False,
        }

    blockers: list[dict[str, Any]] = []
    for error in _checkpoint_validation_errors(checkpoint_payload):
        blockers.append({"code": "release_set_evidence_invalid", "message": error})

    plan = build_release_set_plan(repo, manifest=manifest)
    if not plan.get("ok"):
        blockers.append({
            "code": "release_set_plan_blocked",
            "message": "current release-set plan is not compatible",
            "details": {"plan_blockers": plan.get("blockers") or []},
        })
    pre_current = checkpoint_payload.get("pre_rollout_current") if isinstance(checkpoint_payload.get("pre_rollout_current"), dict) else {}
    recovered_plan_sha256 = _recovered_plan_sha256(plan, pre_current)
    binding_checks = {
        "release_set_id": (
            checkpoint_payload.get("release_set_id"),
            plan.get("release_set_id"),
        ),
        "project_id": (
            checkpoint_payload.get("project_id"),
            plan.get("project_id"),
        ),
        "plan_sha256": (
            checkpoint_payload.get("plan_sha256"),
            recovered_plan_sha256,
        ),
    }
    for name, (recorded, current) in binding_checks.items():
        if str(recorded or "") != str(current or ""):
            blockers.append({
                "code": f"release_set_reconciliation_{name}_mismatch",
                "message": f"checkpoint {name} does not match the recomputed release-set plan",
                "details": {"recorded": recorded, "current": current},
            })

    rows = {str(row["repo_id"]): row for row in plan.get("repositories") or []}
    registry = ArtifactRegistry(project_registry_dir(str(plan.get("project_id") or checkpoint_payload.get("project_id") or "")))
    states: list[dict[str, Any]] = []
    for repo_id in plan.get("execution_order") or []:
        row = rows.get(str(repo_id)) or {}
        states.append(_repository_reconciliation_state(
            repo_id=str(repo_id),
            observed=_current_identity(registry, str(repo_id)),
            previous=pre_current.get(str(repo_id)) if isinstance(pre_current, dict) else None,
            target=_target_identity(row),
        ))

    ambiguous = [item["repo_id"] for item in states if item["classification"] in {"missing_current", "ambiguous_current"}]
    target_current = [item["repo_id"] for item in states if item["target_current"]]
    previous_current = [item["repo_id"] for item in states if item["previous_current"]]
    checkpoint_status = str(checkpoint_payload.get("status") or "")
    failed_repo_id = str(checkpoint_payload.get("failed_repo_id") or "") or None
    if failed_repo_id is None:
        latest_failed = next(
            (item for item in reversed(checkpoint_payload.get("repository_results") or []) if isinstance(item, dict) and not item.get("ok")),
            None,
        )
        failed_repo_id = str((latest_failed or {}).get("repo_id") or "") or None
    failure_context = bool(
        failed_repo_id
        or checkpoint_status in {
            "release_set_rollout_failed_rolling_back",
            "release_set_rollout_failed_rollback_verified",
            "release_set_rollout_failed_rollback_incomplete",
        }
    )

    if ambiguous:
        mode = "blocked"
        blockers.append({
            "code": "release_set_operator_reconciliation_required",
            "message": "one or more repository current identities match neither the pre-rollout identity nor the release-set target",
            "details": {"repositories": ambiguous},
        })
    elif checkpoint_status == "release_set_rollout_verified":
        if len(target_current) == len(states):
            mode = "already_terminal"
        else:
            mode = "blocked"
            blockers.append({
                "code": "release_set_terminal_evidence_drift",
                "message": "terminal successful evidence no longer matches authoritative current identities",
                "details": {"target_current": target_current, "previous_current": previous_current},
            })
    elif checkpoint_status == "release_set_rollout_failed_rollback_verified":
        if len(previous_current) == len(states):
            mode = "already_terminal"
        else:
            mode = "blocked"
            blockers.append({
                "code": "release_set_terminal_rollback_evidence_drift",
                "message": "terminal rollback evidence no longer matches authoritative pre-rollout identities",
                "details": {"target_current": target_current, "previous_current": previous_current},
            })
    elif failure_context:
        mode = "finalize_rollback" if not target_current else "resume_rollback"
    else:
        mode = "finalize_success" if len(target_current) == len(states) and bool(states) else "continue_rollout"

    rollback_order = [repo_id for repo_id in reversed(plan.get("execution_order") or []) if repo_id in target_current]
    pending_order = [repo_id for repo_id in plan.get("execution_order") or [] if repo_id in previous_current]
    checkpoint_sha256 = _canonical_digest(checkpoint_payload)
    digest_body = {
        "schema": "promptbranch.release_set.rollout.reconciliation",
        "schema_version": "1.0",
        "release_set_id": plan.get("release_set_id"),
        "project_id": plan.get("project_id"),
        "plan_sha256": checkpoint_payload.get("plan_sha256"),
        "current_plan_sha256": plan.get("plan_sha256"),
        "recovered_plan_sha256": recovered_plan_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_status": checkpoint_status,
        "failed_repo_id": failed_repo_id,
        "mode": mode,
        "repository_states": states,
        "pending_execution_order": pending_order,
        "rollback_order": rollback_order,
    }
    reconciliation_sha256 = _canonical_digest(digest_body)
    status_by_mode = {
        "blocked": "release_set_rollout_reconciliation_blocked",
        "continue_rollout": "release_set_rollout_resume_ready",
        "resume_rollback": "release_set_rollout_rollback_resume_ready",
        "finalize_success": "release_set_rollout_success_reconciliation_ready",
        "finalize_rollback": "release_set_rollout_rollback_reconciliation_ready",
        "already_terminal": "release_set_rollout_already_terminal",
    }
    result = {
        "ok": not blockers,
        "schema": "promptbranch.release_set.rollout.reconciliation",
        "schema_version": "1.0",
        "action": "release_set_reconcile",
        "status": status_by_mode[mode],
        "repo_path": str(repo),
        "manifest_path": str(Path(manifest)),
        "evidence_path": str(evidence_path),
        "release_set_id": plan.get("release_set_id"),
        "project_id": plan.get("project_id"),
        "plan_sha256": checkpoint_payload.get("plan_sha256"),
        "current_plan_sha256": plan.get("plan_sha256"),
        "recovered_plan_sha256": recovered_plan_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_status": checkpoint_status,
        "failed_repo_id": failed_repo_id,
        "mode": mode,
        "repository_states": states,
        "pending_execution_order": pending_order,
        "rollback_order": rollback_order,
        "reconciliation_sha256": reconciliation_sha256,
        "blockers": blockers,
        "warnings": [],
        "state_mutated": False,
        "mutation_performed": False,
    }
    result["recommended_command"] = (
        None
        if blockers or mode == "already_terminal"
        else " ".join([
            "pb release set resume",
            f"--repo-path {repo}",
            f"--manifest {Path(manifest)}",
            f"--evidence {evidence_path}",
            f"--confirm-release-set-id {plan.get('release_set_id')}",
            f"--confirm-plan-sha256 {checkpoint_payload.get('plan_sha256')}",
            f"--confirm-reconciliation-sha256 {reconciliation_sha256}",
            "--execute --rollback-on-failure --stage-all --commit --push --publish --adopt --verify-current --json",
        ])
    )
    return result


def _append_reconciled_repository_result(
    payload: dict[str, Any],
    *,
    repo_id: str,
    target: dict[str, Any],
    observed: dict[str, Any] | None,
) -> None:
    latest = next(
        (item for item in reversed(payload.get("repository_results") or []) if item.get("repo_id") == repo_id and item.get("ok")),
        None,
    )
    if latest is not None:
        return
    result = {
        "repo_id": repo_id,
        "wave_index": None,
        "target": target,
        "command": None,
        "registry_observed": observed,
        "registry_verified": True,
        "ok": True,
        "status": "repository_rollout_reconciled_verified",
    }
    payload.setdefault("repository_results", []).append(result)
    _event(payload.setdefault("events", []), kind="repository_rollout_reconciled", repo_id=repo_id, details=result)


def _rollback_repository(
    *,
    payload: dict[str, Any],
    plan: dict[str, Any],
    configured: dict[str, dict[str, Any]],
    rows: dict[str, dict[str, Any]],
    registry: ArtifactRegistry,
    repo_id: str,
    previous: dict[str, Any] | None,
    timeout_seconds: float,
    runner: Runner,
) -> dict[str, Any]:
    cfg = configured.get(repo_id) or {}
    repo_root = Path(str(cfg.get("repo_root") or rows[repo_id].get("repo_root") or "")).expanduser().resolve()
    env = dict(os.environ)
    env.update({
        "PROMPTBRANCH_RELEASE_SET_ID": str(plan["release_set_id"]),
        "PROMPTBRANCH_RELEASE_SET_PLAN_SHA256": str(plan["plan_sha256"]),
        "PROMPTBRANCH_ROLLBACK_REPO_ID": repo_id,
        "PROMPTBRANCH_ROLLBACK_VERSION": str((previous or {}).get("version") or ""),
        "PROMPTBRANCH_ROLLBACK_ARTIFACT": str((previous or {}).get("filename") or ""),
        "PROMPTBRANCH_ROLLBACK_SHA256": str((previous or {}).get("sha256") or ""),
        "PROMPTBRANCH_ROLLBACK_SOURCE_REF": str((previous or {}).get("source_ref") or ""),
        "PROMPTBRANCH_ROLLBACK_PROCESSED_FILE_ID": str((previous or {}).get("source_processed_file_id") or ""),
        "PROMPTBRANCH_ROLLBACK_LIBRARY_METADATA_ID": str((previous or {}).get("source_library_metadata_object_id") or ""),
        "PROMPTBRANCH_ROLLBACK_PROJECT_ID": str(plan["project_id"]),
    })
    argv = [*_pb_command(), "release", "contract-execute", "rollback", "--repo-path", str(repo_root), "--json"]
    command = _command(argv, cwd=repo_root, timeout_seconds=timeout_seconds, runner=runner, env=env)
    observed = _current_identity(registry, repo_id)
    restored = previous is not None and _identity_matches(observed, previous)
    result = {
        "repo_id": repo_id,
        "previous_identity": previous,
        "command": command,
        "registry_observed": observed,
        "registry_restored": restored,
        "ok": bool(command.get("ok")) and restored,
        "status": "repository_rollback_verified" if bool(command.get("ok")) and restored else "repository_rollback_failed",
    }
    payload.setdefault("rollback_results", []).append(result)
    _event(payload.setdefault("events", []), kind="repository_rollback_result", repo_id=repo_id, details=result)
    return result


def resume_release_set(
    repo_path: str | Path = ".",
    *,
    manifest: str | Path = ".promptbranch-release-set.json",
    evidence: str | Path,
    confirm_release_set_id: str | None = None,
    confirm_plan_sha256: str | None = None,
    confirm_reconciliation_sha256: str | None = None,
    execute: bool = False,
    rollback_on_failure: bool = False,
    stage_all: bool = False,
    commit: bool = False,
    push: bool = False,
    publish: bool = False,
    adopt: bool = False,
    verify_current: bool = False,
    timeout_seconds: float = 14400.0,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    reconciliation = reconcile_rollout_evidence(repo, manifest=manifest, evidence=evidence)
    plan = build_release_set_plan(repo, manifest=manifest)
    plan = dict(plan)
    plan["plan_sha256"] = reconciliation.get("plan_sha256")
    blocked_payload = _base_payload(repo, manifest, plan)
    blocked_payload["action"] = "release_set_resume"
    blocked_payload["status"] = "release_set_rollout_resume_blocked"
    blocked_payload["reconciliation"] = reconciliation
    _validate_authorization(
        blocked_payload,
        plan,
        confirm_release_set_id=confirm_release_set_id,
        confirm_plan_sha256=confirm_plan_sha256,
        execute=execute,
        rollback_on_failure=rollback_on_failure,
        stage_all=stage_all,
        commit=commit,
        push=push,
        publish=publish,
        adopt=adopt,
        verify_current=verify_current,
        timeout_seconds=timeout_seconds,
    )
    if not reconciliation.get("ok"):
        blocked_payload["blockers"].extend(reconciliation.get("blockers") or [])
    if str(confirm_reconciliation_sha256 or "").lower() != str(reconciliation.get("reconciliation_sha256") or "").lower():
        blocked_payload["blockers"].append({
            "code": "release_set_confirmation_reconciliation_sha256_mismatch",
            "message": "--confirm-reconciliation-sha256 must exactly match the latest read-only reconciliation",
        })
    if blocked_payload["blockers"]:
        return blocked_payload
    if reconciliation.get("mode") == "already_terminal":
        return {
            "ok": True,
            "action": "release_set_resume",
            "status": "release_set_rollout_already_terminal",
            "release_set_id": plan.get("release_set_id"),
            "plan_sha256": plan.get("plan_sha256"),
            "reconciliation": reconciliation,
            "mutation_performed": False,
        }

    evidence_path = Path(str(reconciliation["evidence_path"]))
    payload = _read_json(evidence_path)
    checkpoint = Path(str(payload.get("checkpoint_path") or evidence_path)).expanduser().resolve()
    summary = Path(str(payload.get("summary_path") or checkpoint.with_name(ROLLOUT_SUMMARY_FILENAME))).expanduser().resolve()
    previous_evidence_sha256 = payload.pop("evidence_sha256", None)
    payload.pop("final_event_sha256", None)
    history = payload.setdefault("resume_history", [])
    history.append({
        "resume_sequence": len(history) + 1,
        "resumed_at": _utc(),
        "prior_evidence_sha256": previous_evidence_sha256,
        "checkpoint_sha256": reconciliation.get("checkpoint_sha256"),
        "reconciliation_sha256": reconciliation.get("reconciliation_sha256"),
        "mode": reconciliation.get("mode"),
    })
    payload["resume_count"] = len(history)
    payload["last_reconciliation"] = reconciliation
    payload["status"] = "release_set_rollout_resuming"
    payload["ok"] = False
    payload.setdefault("safety", {})["execution_performed"] = True
    payload["safety"]["resume_performed"] = True
    _event(payload.setdefault("events", []), kind="rollout_resume_started", repo_id=None, details={
        "resume_count": payload["resume_count"],
        "mode": reconciliation.get("mode"),
        "reconciliation_sha256": reconciliation.get("reconciliation_sha256"),
    })
    _atomic_write_json(checkpoint, payload)

    registry = ArtifactRegistry(project_registry_dir(str(plan["project_id"])))
    configured = configured_repos(str(plan["project_id"]))
    rows = {str(row["repo_id"]): row for row in plan.get("repositories") or []}
    pre_current = payload.get("pre_rollout_current") if isinstance(payload.get("pre_rollout_current"), dict) else {}
    state_by_repo = {item["repo_id"]: item for item in reconciliation.get("repository_states") or []}
    failed_repo: str | None = None

    if reconciliation.get("mode") == "continue_rollout":
        for repo_id in plan.get("execution_order") or []:
            row = rows[repo_id]
            state = state_by_repo.get(repo_id) or {}
            target = _target_identity(row)
            if state.get("target_current"):
                _append_reconciled_repository_result(
                    payload,
                    repo_id=repo_id,
                    target=target,
                    observed=state.get("observed_identity"),
                )
                _atomic_write_json(checkpoint, payload)
                continue
            cfg = configured.get(repo_id) or {}
            repo_root = Path(str(cfg.get("repo_root") or row.get("repo_root") or "")).expanduser().resolve()
            argv = [
                *_pb_command(), "release", "pipeline", "apply",
                "--repo-path", str(repo_root),
                "--confirm-version", str(row["target_version"]),
                "--stage-all", "--commit", "--push", "--publish", "--adopt", "--verify-current", "--json",
            ]
            command = _command(argv, cwd=repo_root, timeout_seconds=timeout_seconds, runner=runner, env=dict(os.environ))
            observed = _current_identity(registry, repo_id)
            registry_verified = _identity_matches(observed, target)
            repo_result = {
                "repo_id": repo_id,
                "wave_index": None,
                "target": target,
                "command": command,
                "registry_observed": observed,
                "registry_verified": registry_verified,
                "ok": bool(command.get("ok")) and registry_verified,
                "status": "repository_rollout_verified" if bool(command.get("ok")) and registry_verified else "repository_rollout_failed",
                "resumed": True,
            }
            payload.setdefault("repository_results", []).append(repo_result)
            _event(payload.setdefault("events", []), kind="repository_rollout_result", repo_id=repo_id, details=repo_result)
            _atomic_write_json(checkpoint, payload)
            if not repo_result["ok"]:
                failed_repo = repo_id
                break

        if failed_repo is None:
            payload["ok"] = True
            payload["status"] = "release_set_rollout_verified"
            payload["rollback_verified"] = None
            payload.pop("failed_repo_id", None)
            _event(payload["events"], kind="rollout_resumed_completed", repo_id=None, details={"repository_count": len(rows)})
        else:
            payload["failed_repo_id"] = failed_repo
            payload["status"] = "release_set_rollout_failed_rolling_back"
            _atomic_write_json(checkpoint, payload)
            rollback_candidates = []
            for repo_id in reversed(plan.get("execution_order") or []):
                if _identity_matches(_current_identity(registry, repo_id), _target_identity(rows[repo_id])):
                    rollback_candidates.append(repo_id)
            rollback_attempts = []
            for repo_id in rollback_candidates:
                rollback_attempts.append(_rollback_repository(
                    payload=payload,
                    plan=plan,
                    configured=configured,
                    rows=rows,
                    registry=registry,
                    repo_id=repo_id,
                    previous=pre_current.get(repo_id),
                    timeout_seconds=timeout_seconds,
                    runner=runner,
                ))
                _atomic_write_json(checkpoint, payload)
            rollback_ok = len(rollback_attempts) == len(rollback_candidates) and all(item.get("ok") for item in rollback_attempts)
            payload["ok"] = False
            payload["rollback_verified"] = rollback_ok
            payload["status"] = "release_set_rollout_failed_rollback_verified" if rollback_ok else "release_set_rollout_failed_rollback_incomplete"
            _event(payload["events"], kind="rollout_resume_rollback_completed", repo_id=None, details={"rollback_verified": rollback_ok})

    elif reconciliation.get("mode") == "resume_rollback":
        payload["status"] = "release_set_rollout_failed_rolling_back"
        rollback_attempts = []
        for repo_id in reconciliation.get("rollback_order") or []:
            rollback_attempts.append(_rollback_repository(
                payload=payload,
                plan=plan,
                configured=configured,
                rows=rows,
                registry=registry,
                repo_id=repo_id,
                previous=pre_current.get(repo_id),
                timeout_seconds=timeout_seconds,
                runner=runner,
            ))
            _atomic_write_json(checkpoint, payload)
        all_restored = all(
            _previous_identity_matches(_current_identity(registry, repo_id), pre_current.get(repo_id))
            for repo_id in plan.get("execution_order") or []
        )
        rollback_ok = all_restored and all(item.get("ok") for item in rollback_attempts)
        payload["ok"] = False
        payload["rollback_verified"] = rollback_ok
        payload["status"] = "release_set_rollout_failed_rollback_verified" if rollback_ok else "release_set_rollout_failed_rollback_incomplete"
        _event(payload["events"], kind="rollout_resume_rollback_completed", repo_id=None, details={"rollback_verified": rollback_ok})

    elif reconciliation.get("mode") == "finalize_success":
        payload["ok"] = True
        payload["status"] = "release_set_rollout_verified"
        payload["rollback_verified"] = None
        payload.pop("failed_repo_id", None)
        _event(payload["events"], kind="rollout_reconciliation_finalized_success", repo_id=None, details={
            "reconciliation_sha256": reconciliation.get("reconciliation_sha256"),
        })

    elif reconciliation.get("mode") == "finalize_rollback":
        payload["ok"] = False
        payload["status"] = "release_set_rollout_failed_rollback_verified"
        payload["rollback_verified"] = True
        _event(payload["events"], kind="rollout_reconciliation_finalized_rollback", repo_id=None, details={
            "reconciliation_sha256": reconciliation.get("reconciliation_sha256"),
        })

    payload["final_event_sha256"] = payload["events"][-1]["event_sha256"] if payload.get("events") else None
    evidence_body = {key: value for key, value in payload.items() if key != "evidence_sha256"}
    payload["evidence_sha256"] = _canonical_digest(evidence_body)
    _atomic_write_json(checkpoint, payload)
    _atomic_write_json(summary, payload)
    return payload

def validate_rollout_evidence(path: str | Path) -> dict[str, Any]:
    evidence_path = Path(path).expanduser().resolve()
    if evidence_path.is_dir():
        candidate = evidence_path / ROLLOUT_SUMMARY_FILENAME
        if not candidate.is_file():
            candidate = evidence_path / ROLLOUT_CHECKPOINT_FILENAME
        evidence_path = candidate
    try:
        payload = _read_json(evidence_path)
    except ReleaseSetRolloutError as exc:
        return {"ok": False, "action": "release_set_evidence_validate", "status": "release_set_evidence_invalid", "evidence_path": str(evidence_path), "errors": [str(exc)]}
    errors: list[str] = []
    if payload.get("schema") != ROLLOUT_EVIDENCE_SCHEMA or payload.get("schema_version") != ROLLOUT_EVIDENCE_SCHEMA_VERSION:
        errors.append("unsupported rollout evidence schema")
    previous: str | None = None
    events = payload.get("events") if isinstance(payload.get("events"), list) else []
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            errors.append(f"event {index} is not an object")
            break
        expected_hash = event.get("event_sha256")
        body = {key: value for key, value in event.items() if key != "event_sha256"}
        if event.get("sequence") != index:
            errors.append(f"event {index} sequence mismatch")
        if event.get("previous_event_sha256") != previous:
            errors.append(f"event {index} previous hash mismatch")
        if expected_hash != _canonical_digest(body):
            errors.append(f"event {index} hash mismatch")
        previous = str(expected_hash or "") or None
    if payload.get("final_event_sha256") != previous:
        errors.append("final event hash mismatch")
    expected_evidence = payload.get("evidence_sha256")
    body = {key: value for key, value in payload.items() if key != "evidence_sha256"}
    if expected_evidence != _canonical_digest(body):
        errors.append("evidence SHA-256 mismatch")
    return {
        "ok": not errors,
        "action": "release_set_evidence_validate",
        "status": "release_set_evidence_valid" if not errors else "release_set_evidence_invalid",
        "evidence_path": str(evidence_path),
        "release_set_id": payload.get("release_set_id"),
        "plan_sha256": payload.get("plan_sha256"),
        "event_count": len(events),
        "errors": errors,
        "evidence": payload if not errors else None,
    }

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from promptbranch_application_architecture import (
    ApplicationArchitectureError,
    load_application_declaration,
    validate_application_architecture,
)
from promptbranch_application_migration import (
    ApplicationMigrationError,
    build_application_migration_report,
)
from promptbranch_release_identity import evaluate_current_release_identity, sha256_file
from promptbranch_release_engine import (
    ReleaseContractError,
    execute as execute_release_contract,
    load_contract,
    plan as plan_release_contract,
)

PIPELINE_SCHEMA = "promptbranch.release.pipeline"
PIPELINE_SCHEMA_VERSION = "1.1"
INVENTORY_SCHEMA = "promptbranch.pbai.compliance-inventory"
INVENTORY_SCHEMA_VERSION = "1.0"
CANONICAL_VERSION_RE = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)*")
LOCAL_OPERATIONS = ("validate", "test", "build", "verify")
PIPELINE_CHECKPOINT_FILENAME = "release-pipeline-checkpoint.json"
PIPELINE_SUMMARY_FILENAME = "release-pipeline-summary.json"
PIPELINE_PHASE_ORDER = (
    "local-validate",
    "local-test",
    "local-build",
    "local-verify",
    "git-sync",
    "committed-tree-build",
    "committed-tree-verify",
    "release-identity-preflight",
    "project-source-publish",
    "artifact-adopt",
    "accepted-current-verify",
)
PIPELINE_MUTATION_PHASES = (
    "git-sync",
    "project-source-publish",
    "artifact-adopt",
    "accepted-current-verify",
)
DEFAULT_UNSAFE_GIT_PATTERNS = (
    ".env",
    ".generated/",
    ".pb_profile/",
    "debug_artifacts/",
    "*.zip",
    "*.log",
    "__pycache__/",
    ".pytest_cache/",
)


class ReleasePipelineError(ValueError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id(version: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{version.removeprefix('v')}"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleasePipelineError(f"invalid JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleasePipelineError(f"JSON evidence root must be an object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    """Write evidence crash-consistently so interruption cannot truncate the last checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, indent=2, sort_keys=True) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _canonical_version(repo: Path, contract: dict[str, Any]) -> str:
    version_path = repo / str(contract["version_authority"]["path"])
    try:
        value = version_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ReleasePipelineError(f"cannot read version authority {version_path}: {exc}") from exc
    if not CANONICAL_VERSION_RE.fullmatch(value):
        raise ReleasePipelineError(f"VERSION must be canonical and v-prefixed; got {value!r}")
    return value


def _artifact_path(repo: Path, contract: dict[str, Any]) -> Path:
    return (repo / str(contract["artifact"]["path"])).resolve()


def _path_matches(path_text: str, patterns: Sequence[str]) -> bool:
    normalized = path_text.strip().replace("\\", "/")
    for raw in patterns:
        pattern = str(raw or "").strip().replace("\\", "/").strip("/")
        if not pattern:
            continue
        if (
            fnmatch.fnmatch(normalized, pattern)
            or normalized == pattern
            or normalized.startswith(pattern.rstrip("/") + "/")
        ):
            return True
    return False


def _git_status(repo: Path, *, runner: Runner = subprocess.run) -> dict[str, Any]:
    try:
        result = runner(
            ["git", "status", "--porcelain=v1"],
            cwd=str(repo),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "status": "git_status_error", "error": str(exc), "entries": []}
    if result.returncode != 0:
        return {
            "ok": False,
            "status": "git_status_error",
            "error": result.stderr.strip(),
            "entries": [],
        }
    entries: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path_text = line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        entries.append({"status": status, "path": path_text})
    return {
        "ok": True,
        "status": "git_status_loaded",
        "entries": entries,
        "dirty_paths": [item["path"] for item in entries],
        "dirty": bool(entries),
    }


def _git_config(contract: dict[str, Any]) -> dict[str, Any]:
    configured = contract.get("git") if isinstance(contract.get("git"), dict) else {}
    unsafe = [str(value) for value in configured.get("unsafe_paths", DEFAULT_UNSAFE_GIT_PATTERNS)]
    expected = [str(value) for value in configured.get("expected_paths", [])]
    message = str(configured.get("commit_message") or "Release {version}")
    return {"unsafe_paths": unsafe, "expected_paths": expected, "commit_message": message}


def _git_stage_plan(repo: Path, contract: dict[str, Any], *, runner: Runner = subprocess.run) -> dict[str, Any]:
    status = _git_status(repo, runner=runner)
    cfg = _git_config(contract)
    entries = status.get("entries") if isinstance(status.get("entries"), list) else []
    dirty_paths = [str(item.get("path") or "") for item in entries if isinstance(item, dict)]
    unsafe = [path for path in dirty_paths if _path_matches(path, cfg["unsafe_paths"])]
    if cfg["expected_paths"]:
        allowed = [path for path in dirty_paths if _path_matches(path, cfg["expected_paths"])]
        unexpected = [path for path in dirty_paths if path not in allowed and path not in unsafe]
    else:
        allowed = [path for path in dirty_paths if path not in unsafe]
        unexpected = []
    ok = bool(status.get("ok")) and not unsafe and not unexpected
    return {
        "ok": ok,
        "status": "safe_to_stage" if ok else "unsafe_or_unexpected_dirty_paths",
        "git_status": status,
        "paths_to_stage": allowed,
        "unsafe_dirty_paths": unsafe,
        "unexpected_dirty_paths": unexpected,
        "unsafe_patterns": cfg["unsafe_paths"],
        "expected_patterns": cfg["expected_paths"],
    }


def _command_result(
    argv: Sequence[str],
    *,
    repo: Path,
    evidence_path: Path,
    timeout: float,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    started_at = _utc()
    try:
        result = runner(
            list(argv),
            cwd=str(repo),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        payload = {
            "ok": False,
            "status": "command_timeout",
            "argv": list(argv),
            "started_at": started_at,
            "finished_at": _utc(),
            "timeout_seconds": timeout,
            "stdout": exc.stdout if isinstance(exc.stdout, str) else "",
            "stderr": exc.stderr if isinstance(exc.stderr, str) else "",
        }
        _write_json(evidence_path, payload)
        return payload
    except OSError as exc:
        payload = {
            "ok": False,
            "status": "command_execution_error",
            "argv": list(argv),
            "started_at": started_at,
            "finished_at": _utc(),
            "error": str(exc),
        }
        _write_json(evidence_path, payload)
        return payload
    parsed: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            candidate = json.loads(result.stdout)
            if isinstance(candidate, dict):
                parsed = candidate
        except json.JSONDecodeError:
            parsed = None
    ok = result.returncode == 0 and (parsed is None or parsed.get("ok", True) is True)
    payload = {
        "ok": ok,
        "status": (parsed or {}).get("status") or ("command_passed" if ok else "command_failed"),
        "argv": list(argv),
        "started_at": started_at,
        "finished_at": _utc(),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "payload": parsed,
    }
    _write_json(evidence_path, payload)
    return payload


def _pb_command() -> list[str]:
    override = str(os.environ.get("PROMPTBRANCH_PIPELINE_PB_COMMAND") or "").strip()
    if override:
        return [override]
    return [sys.executable, "-m", "promptbranch.cli"]


def _contract_sha256(repo: Path, config: str) -> str:
    path = (repo / config).resolve()
    if not path.is_file():
        raise ReleasePipelineError(f"release contract not found: {path}")
    return sha256_file(path)


def _git_head(repo: Path, *, runner: Runner = subprocess.run) -> dict[str, Any]:
    try:
        result = runner(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "status": "git_head_error", "error": str(exc), "commit": None}
    commit = result.stdout.strip().lower()
    ok = result.returncode == 0 and bool(re.fullmatch(r"[0-9a-f]{7,40}", commit))
    return {
        "ok": ok,
        "status": "git_head_loaded" if ok else "git_head_error",
        "commit": commit if ok else None,
        "error": None if ok else (result.stderr.strip() or "git rev-parse HEAD did not return a commit"),
    }


def _resolve_pipeline_evidence_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    if path.is_dir():
        for name in (PIPELINE_CHECKPOINT_FILENAME, PIPELINE_SUMMARY_FILENAME):
            candidate = path / name
            if candidate.is_file():
                return candidate
        raise ReleasePipelineError(
            f"pipeline evidence directory contains neither {PIPELINE_CHECKPOINT_FILENAME} nor {PIPELINE_SUMMARY_FILENAME}: {path}"
        )
    if not path.is_file():
        raise ReleasePipelineError(f"pipeline evidence not found: {path}")
    return path


def _phase_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    values = payload.get("phase_results")
    if not isinstance(values, list):
        return result
    for item in values:
        if not isinstance(item, dict):
            continue
        phase = str(item.get("phase") or "").strip()
        if phase:
            result[phase] = item
    return result


def _successful_phase(payload: dict[str, Any], phase_id: str) -> dict[str, Any] | None:
    item = _phase_map(payload).get(phase_id)
    if isinstance(item, dict) and item.get("ok") is True:
        return item
    return None


def _extract_git_commit_sha(phase: dict[str, Any] | None) -> str | None:
    if not isinstance(phase, dict):
        return None
    payload = phase.get("payload") if isinstance(phase.get("payload"), dict) else {}
    candidates = [
        payload.get("git_commit_sha"),
        ((payload.get("evidence_binding") or {}) if isinstance(payload.get("evidence_binding"), dict) else {}).get("git_commit"),
    ]
    command = payload.get("git_commit") if isinstance(payload.get("git_commit"), dict) else {}
    candidates.extend([command.get("commit"), command.get("git_commit_sha")])
    stdout = str(command.get("stdout") or "")
    match = re.search(r"\[[^\]\n]+\s+([0-9a-fA-F]{7,40})\]", stdout)
    if match:
        candidates.append(match.group(1))
    for value in candidates:
        text = str(value or "").strip().lower()
        if re.fullmatch(r"[0-9a-f]{7,40}", text):
            return text
    return None


def _extract_source_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    source = payload.get("source")
    if isinstance(source, dict):
        return source
    phase = _successful_phase(payload, "project-source-publish")
    if phase:
        phase_payload = phase.get("payload") if isinstance(phase.get("payload"), dict) else {}
        source = phase_payload.get("source")
        if isinstance(source, dict):
            return source
    return None


def _artifact_sha_candidates(payload: dict[str, Any]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []

    def add(origin: str, value: Any) -> None:
        text = str(value or "").strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", text):
            candidates.append({"origin": origin, "sha256": text})

    binding = payload.get("evidence_binding") if isinstance(payload.get("evidence_binding"), dict) else {}
    add("evidence_binding", binding.get("artifact_sha256"))
    artifact = payload.get("artifact") if isinstance(payload.get("artifact"), dict) else {}
    add("artifact", artifact.get("sha256"))
    identity = payload.get("release_identity") if isinstance(payload.get("release_identity"), dict) else {}
    add("release_identity.candidate_sha256", identity.get("candidate_sha256"))
    add("release_identity.artifact_sha256", identity.get("artifact_sha256"))
    source = _extract_source_payload(payload) or {}
    add("source.local_sha256", source.get("local_sha256"))
    for phase_id in ("committed-tree-verify", "committed-tree-build", "local-verify", "local-build"):
        phase = _successful_phase(payload, phase_id)
        phase_payload = phase.get("payload") if phase and isinstance(phase.get("payload"), dict) else {}
        phase_artifact = phase_payload.get("artifact") if isinstance(phase_payload.get("artifact"), dict) else {}
        add(f"{phase_id}.artifact", phase_artifact.get("sha256"))
    current = payload.get("current") if isinstance(payload.get("current"), dict) else {}
    repos = current.get("repos") if isinstance(current.get("repos"), dict) else {}
    for repo_id, item in repos.items():
        if not isinstance(item, dict):
            continue
        registry = item.get("registry_current") if isinstance(item.get("registry_current"), dict) else {}
        add(f"current.{repo_id}.registry_current", registry.get("sha256"))
    return candidates


def _extract_artifact_sha256(payload: dict[str, Any]) -> tuple[str | None, list[dict[str, str]], bool]:
    candidates = _artifact_sha_candidates(payload)
    values = sorted({item["sha256"] for item in candidates})
    return (values[0] if len(values) == 1 else None, candidates, len(values) > 1)


def _valid_source_evidence(source: dict[str, Any] | None, *, artifact_sha256: str | None) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if not isinstance(source, dict):
        return False, ["pipeline_import_source_evidence_missing"]
    for field in ("assigned_filename", "processed_file_id", "library_metadata_object_id"):
        if not str(source.get(field) or "").strip():
            blockers.append(f"pipeline_import_source_{field}_missing")
    if source.get("persistence_verified") is not True:
        blockers.append("pipeline_import_source_persistence_unverified")
    source_sha = str(source.get("local_sha256") or "").strip().lower()
    if artifact_sha256:
        if not re.fullmatch(r"[0-9a-f]{64}", source_sha):
            blockers.append("pipeline_import_source_hash_missing")
        elif source_sha != artifact_sha256:
            blockers.append("pipeline_import_source_hash_mismatch")
    return not blockers, blockers


def build_release_pipeline_import_plan(
    repo_path: str | Path = ".",
    *,
    evidence: str | Path,
    config: str = ".promptbranch-release.json",
    confirm_version: str | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    try:
        contract = load_contract(repo, config)
        version = _canonical_version(repo, contract)
        evidence_path = _resolve_pipeline_evidence_path(evidence)
        imported = _read_json(evidence_path)
    except (ReleaseContractError, ReleasePipelineError) as exc:
        return {
            "ok": False,
            "schema": PIPELINE_SCHEMA,
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "action": "release_pipeline_import",
            "status": "pipeline_evidence_import_blocked",
            "repo_path": str(repo),
            "evidence_path": str(evidence),
            "blockers": [{"code": "pipeline_import_invalid_input", "message": str(exc)}],
            "state_mutated": False,
        }
    repo_id = str(contract["repository"]["repo_id"])
    artifact = _artifact_path(repo, contract)
    imported_repo = imported.get("repository") if isinstance(imported.get("repository"), dict) else {}
    imported_artifact = imported.get("artifact") if isinstance(imported.get("artifact"), dict) else {}
    if imported.get("schema") != PIPELINE_SCHEMA:
        blockers.append({"code": "pipeline_import_schema_mismatch", "message": "evidence schema is not promptbranch.release.pipeline"})
    imported_schema_version = str(imported.get("schema_version") or "")
    if imported_schema_version not in {"1.0", PIPELINE_SCHEMA_VERSION}:
        blockers.append({
            "code": "pipeline_import_schema_version_unsupported",
            "message": f"unsupported pipeline evidence schema_version: {imported_schema_version or '<missing>'}",
        })
    if imported.get("action") != "release_pipeline_apply":
        blockers.append({"code": "pipeline_import_action_mismatch", "message": "evidence action must be release_pipeline_apply"})
    if str(imported_repo.get("repo_id") or "") != repo_id:
        blockers.append({"code": "pipeline_import_repository_mismatch", "message": "evidence repository does not match the selected repository"})
    if str(imported.get("version") or "") != version:
        blockers.append({"code": "pipeline_import_version_mismatch", "message": "evidence version does not match VERSION"})
    if confirm_version is not None and str(confirm_version) != version:
        blockers.append({"code": "pipeline_import_confirmation_mismatch", "message": "--confirm-version does not match VERSION"})
    if str(imported_artifact.get("filename") or "") != artifact.name:
        blockers.append({"code": "pipeline_import_artifact_filename_mismatch", "message": "evidence artifact filename does not match the release contract"})
    phases = _phase_map(imported)
    if not phases:
        blockers.append({"code": "pipeline_import_phase_evidence_missing", "message": "evidence has no phase_results"})

    artifact_sha, artifact_sha_evidence, artifact_sha_conflict = _extract_artifact_sha256(imported)
    if artifact_sha_conflict:
        blockers.append({"code": "pipeline_import_artifact_hash_conflict", "message": "evidence contains conflicting artifact SHA-256 values"})
    current_artifact_sha = sha256_file(artifact) if artifact.is_file() else None
    if artifact_sha and current_artifact_sha and artifact_sha != current_artifact_sha:
        blockers.append({"code": "pipeline_import_local_artifact_hash_mismatch", "message": "local artifact bytes do not match imported evidence"})
    if artifact_sha is None:
        warnings.append({"code": "pipeline_import_artifact_hash_pending", "message": "artifact hash will be established by the resumed committed-tree build before mutation"})

    binding = imported.get("evidence_binding") if isinstance(imported.get("evidence_binding"), dict) else {}
    imported_contract_sha = str(binding.get("contract_sha256") or "").strip().lower()
    current_contract_sha = _contract_sha256(repo, config)
    if imported_contract_sha:
        if imported_contract_sha != current_contract_sha:
            blockers.append({"code": "pipeline_import_contract_hash_mismatch", "message": "release contract differs from imported evidence"})
    else:
        warnings.append({"code": "pipeline_import_legacy_contract_binding", "message": "legacy evidence has no contract hash; phase-specific immutable bindings are required for reuse"})

    completed_phases = [phase_id for phase_id in PIPELINE_PHASE_ORDER if _successful_phase(imported, phase_id)]
    failed_phases = [phase_id for phase_id, item in phases.items() if item.get("ok") is False]
    first_incomplete = next((phase_id for phase_id in PIPELINE_PHASE_ORDER if phase_id not in completed_phases), None)
    reusable: list[str] = []
    git_commit_sha: str | None = None
    git_phase = _successful_phase(imported, "git-sync")
    if git_phase:
        git_commit_sha = _extract_git_commit_sha(git_phase)
        git_payload = git_phase.get("payload") if isinstance(git_phase.get("payload"), dict) else {}
        if not git_commit_sha:
            blockers.append({"code": "pipeline_import_git_commit_unbound", "message": "successful Git phase lacks an immutable commit id"})
        else:
            head = _git_head(repo, runner=runner)
            head_commit = str(head.get("commit") or "")
            if not head.get("ok") or not (head_commit == git_commit_sha or head_commit.startswith(git_commit_sha) or git_commit_sha.startswith(head_commit)):
                blockers.append({"code": "pipeline_import_git_head_mismatch", "message": "repository HEAD does not match imported successful Git phase"})
            elif imported.get("push_requested") and git_payload.get("push_performed") is not True:
                blockers.append({"code": "pipeline_import_push_proof_missing", "message": "imported run requested push but successful Git evidence lacks push proof"})
            else:
                reusable.append("git-sync")

    source = _extract_source_payload(imported)
    source_phase = _successful_phase(imported, "project-source-publish")
    if source_phase:
        if artifact_sha is None:
            blockers.append({
                "code": "pipeline_import_source_artifact_hash_unbound",
                "message": "successful Project Source evidence cannot be reused without one unambiguous artifact SHA-256",
            })
        else:
            source_ok, source_blockers = _valid_source_evidence(source, artifact_sha256=artifact_sha)
            if source_ok:
                reusable.append("project-source-publish")
            else:
                blockers.extend({"code": code, "message": code.replace("_", " ")} for code in source_blockers)
    for phase_id in ("artifact-adopt", "accepted-current-verify"):
        if _successful_phase(imported, phase_id):
            if artifact_sha is None:
                blockers.append({
                    "code": f"pipeline_import_{phase_id.replace('-', '_')}_artifact_hash_unbound",
                    "message": f"successful {phase_id} evidence cannot be reused without one unambiguous artifact SHA-256",
                })
            else:
                reusable.append(phase_id)

    return {
        "ok": not blockers,
        "schema": PIPELINE_SCHEMA,
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "action": "release_pipeline_import",
        "status": "pipeline_evidence_importable" if not blockers else "pipeline_evidence_import_blocked",
        "repo_path": str(repo),
        "repository": contract["repository"],
        "version": version,
        "artifact": {
            "path": str(artifact),
            "filename": artifact.name,
            "exists": artifact.is_file(),
            "sha256": current_artifact_sha,
        },
        "evidence_path": str(evidence_path),
        "imported_status": imported.get("status"),
        "imported_schema_version": imported.get("schema_version"),
        "imported_evidence_dir": imported.get("evidence_dir"),
        "completed_phases": completed_phases,
        "failed_phases": failed_phases,
        "first_incomplete_phase": first_incomplete,
        "reusable_mutation_phases": reusable,
        "artifact_sha256": artifact_sha,
        "artifact_sha256_evidence": artifact_sha_evidence,
        "git_commit": git_commit_sha,
        "source": source,
        "imported_requested_mutations": {
            "stage_all": imported.get("stage_all_requested"),
            "commit": imported.get("commit_requested"),
            "push": imported.get("push_requested"),
            "publish": imported.get("publish_requested"),
            "adopt": imported.get("adopt_requested"),
            "verify_current": imported.get("verify_current_requested"),
        },
        "blockers": blockers,
        "blocker_codes": [item["code"] for item in blockers],
        "warnings": warnings,
        "state_mutated": False,
        "safety": {
            "read_only": True,
            "successful_mutation_phases_must_not_replay": True,
            "artifact_hash_match_required_before_mutation": True,
            "git_head_match_required_for_git_reuse": True,
            "adoption_reuse_requires_current_identity_reconfirmation": True,
        },
    }


def _pipeline_dependencies(
    *,
    commit: bool,
    push: bool,
    publish: bool,
    adopt: bool,
    verify_current: bool,
    stage_all: bool,
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if commit and not stage_all:
        blockers.append({"code": "pipeline_commit_requires_stage_all", "message": "--commit requires explicit --stage-all"})
    if push and not commit:
        blockers.append({"code": "pipeline_push_requires_commit", "message": "--push requires --commit in the same pipeline run"})
    if publish and not push:
        blockers.append({"code": "pipeline_publish_requires_push", "message": "--publish requires a successful same-run --push"})
    if adopt and not publish:
        blockers.append({"code": "pipeline_adopt_requires_publish", "message": "--adopt requires same-run Project Source publication"})
    if verify_current and not adopt:
        blockers.append({"code": "pipeline_verify_current_requires_adopt", "message": "--verify-current requires same-run adoption"})
    return blockers


def build_release_pipeline_plan(
    repo_path: str | Path = ".",
    *,
    config: str = ".promptbranch-release.json",
    confirm_version: str | None = None,
    stage_all: bool = False,
    commit: bool = False,
    push: bool = False,
    publish: bool = False,
    adopt: bool = False,
    verify_current: bool = False,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    blockers = _pipeline_dependencies(
        commit=commit,
        push=push,
        publish=publish,
        adopt=adopt,
        verify_current=verify_current,
        stage_all=stage_all,
    )
    try:
        contract = load_contract(repo, config)
        version = _canonical_version(repo, contract)
    except (ReleaseContractError, ReleasePipelineError) as exc:
        return {
            "ok": False,
            "schema": PIPELINE_SCHEMA,
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "action": "release_pipeline_plan",
            "status": "pipeline_contract_invalid",
            "repo_path": str(repo),
            "blockers": [{"code": "pipeline_contract_invalid", "message": str(exc)}],
            "safety": {"read_only": True, "state_mutated": False},
        }
    if confirm_version is not None and str(confirm_version).strip() != version:
        blockers.append({
            "code": "pipeline_confirm_version_mismatch",
            "message": f"--confirm-version must equal {version}",
        })
    artifact = _artifact_path(repo, contract)
    git_plan = _git_stage_plan(repo, contract, runner=runner)
    if commit and not git_plan.get("ok"):
        blockers.append({
            "code": "pipeline_git_stage_blocked",
            "message": "Git staging preflight is not safe",
        })
    contract_plan = plan_release_contract(repo, contract)
    phases = [
        {"id": "local_validate", "operation": "validate", "enabled": True, "mutating": False},
        {"id": "local_test", "operation": "test", "enabled": True, "mutating": False},
        {"id": "local_build", "operation": "build", "enabled": True, "mutating": True},
        {"id": "local_verify", "operation": "verify", "enabled": True, "mutating": False},
        {"id": "git_commit", "operation": "git_commit", "enabled": commit, "mutating": commit},
        {"id": "git_push", "operation": "git_push", "enabled": push, "mutating": push},
        {"id": "committed_tree_rebuild", "operation": "build", "enabled": commit, "mutating": commit},
        {"id": "committed_tree_reverify", "operation": "verify", "enabled": commit, "mutating": False},
        {"id": "project_source_publish", "operation": "publish", "enabled": publish, "mutating": publish},
        {"id": "artifact_adopt", "operation": "adopt", "enabled": adopt, "mutating": adopt},
        {"id": "accepted_current_verify", "operation": "verify_current", "enabled": verify_current, "mutating": False},
    ]
    return {
        "ok": not blockers,
        "schema": PIPELINE_SCHEMA,
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "action": "release_pipeline_plan",
        "status": "pipeline_planned_read_only" if not blockers else "pipeline_plan_blocked",
        "repo_path": str(repo),
        "repository": contract["repository"],
        "version": version,
        "confirmed_version": confirm_version,
        "artifact": {"path": str(artifact), "filename": artifact.name, "exists": artifact.is_file()},
        "contract_plan": contract_plan,
        "phases": phases,
        "git_stage_plan": git_plan,
        "requested_mutations": {
            "stage_all": stage_all,
            "commit": commit,
            "push": push,
            "publish": publish,
            "adopt": adopt,
            "verify_current": verify_current,
        },
        "blockers": blockers,
        "blocker_codes": [item["code"] for item in blockers],
        "safety": {
            "read_only": True,
            "state_mutated": False,
            "publication_separate": True,
            "adoption_requires_source_evidence": True,
            "accepted_current_verification_separate": True,
        },
    }


def _record_phase(evidence_dir: Path, phase_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    path = evidence_dir / f"{phase_id}.json"
    _write_json(path, payload)
    return {
        "phase": phase_id,
        "ok": bool(payload.get("ok")),
        "status": payload.get("status"),
        "evidence_path": str(path),
        "payload": payload,
    }


def _run_git_commit_push(
    repo: Path,
    contract: dict[str, Any],
    *,
    version: str,
    message: str | None,
    push: bool,
    evidence_dir: Path,
    runner: Runner,
) -> dict[str, Any]:
    plan = _git_stage_plan(repo, contract, runner=runner)
    if not plan.get("ok"):
        return {
            "ok": False,
            "status": "git_stage_preflight_blocked",
            "git_stage_plan": plan,
            "commit_performed": False,
            "push_performed": False,
        }
    paths = [str(value) for value in plan.get("paths_to_stage", []) if str(value).strip()]
    if not paths:
        return {
            "ok": False,
            "status": "git_commit_no_changes",
            "git_stage_plan": plan,
            "commit_performed": False,
            "push_performed": False,
        }
    stage = _command_result(
        ["git", "add", "--", *paths],
        repo=repo,
        evidence_path=evidence_dir / "git-stage-command.json",
        timeout=60.0,
        runner=runner,
    )
    if not stage.get("ok"):
        return {"ok": False, "status": "git_stage_failed", "git_stage": stage, "commit_performed": False, "push_performed": False}
    template = _git_config(contract)["commit_message"]
    commit_message = message or template.replace("{version}", version)
    commit = _command_result(
        ["git", "commit", "-m", commit_message],
        repo=repo,
        evidence_path=evidence_dir / "git-commit-command.json",
        timeout=120.0,
        runner=runner,
    )
    if not commit.get("ok"):
        return {"ok": False, "status": "git_commit_failed", "git_stage": stage, "git_commit": commit, "commit_performed": False, "push_performed": False}
    head = _git_head(repo, runner=runner)
    if not head.get("ok"):
        return {
            "ok": False,
            "status": "git_commit_identity_unverified",
            "git_stage": stage,
            "git_commit": commit,
            "git_head": head,
            "commit_performed": True,
            "push_performed": False,
        }
    git_commit_sha = str(head["commit"])
    push_result: dict[str, Any] | None = None
    if push:
        push_result = _command_result(
            ["git", "push"],
            repo=repo,
            evidence_path=evidence_dir / "git-push-command.json",
            timeout=180.0,
            runner=runner,
        )
        if not push_result.get("ok"):
            return {
                "ok": False,
                "status": "git_push_failed",
                "git_stage": stage,
                "git_commit": commit,
                "git_push": push_result,
                "commit_performed": True,
                "push_performed": False,
            }
    return {
        "ok": True,
        "status": "git_committed_and_pushed" if push else "git_committed",
        "git_stage_plan": plan,
        "git_stage": stage,
        "git_commit": commit,
        "git_commit_sha": git_commit_sha,
        "git_head": head,
        "git_push": push_result,
        "commit_performed": True,
        "push_performed": push,
    }


def execute_release_pipeline(
    repo_path: str | Path = ".",
    *,
    config: str = ".promptbranch-release.json",
    confirm_version: str,
    stage_all: bool = False,
    commit: bool = False,
    push: bool = False,
    publish: bool = False,
    adopt: bool = False,
    verify_current: bool = False,
    message: str | None = None,
    resume_from: str | Path | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    plan = build_release_pipeline_plan(
        repo,
        config=config,
        confirm_version=confirm_version,
        stage_all=stage_all,
        commit=commit,
        push=push,
        publish=publish,
        adopt=adopt,
        verify_current=verify_current,
        runner=runner,
    )
    if not plan.get("ok"):
        return {
            **plan,
            "action": "release_pipeline_apply",
            "status": "pipeline_apply_blocked",
            "applied": False,
            "mutating_actions_executed": False,
        }

    import_plan: dict[str, Any] | None = None
    imported: dict[str, Any] | None = None
    imported_evidence_path: Path | None = None
    reusable_phases: set[str] = set()
    if resume_from is not None:
        import_plan = build_release_pipeline_import_plan(
            repo,
            evidence=resume_from,
            config=config,
            confirm_version=confirm_version,
            runner=runner,
        )
        if not import_plan.get("ok"):
            return {
                **import_plan,
                "action": "release_pipeline_resume",
                "status": "pipeline_resume_blocked",
                "applied": False,
                "mutating_actions_executed": False,
            }
        imported_evidence_path = _resolve_pipeline_evidence_path(resume_from)
        imported = _read_json(imported_evidence_path)
        reusable_phases = set(str(value) for value in import_plan.get("reusable_mutation_phases", []))
        requested_scope = {
            "stage_all": bool(stage_all),
            "commit": bool(commit),
            "push": bool(push),
            "publish": bool(publish),
            "adopt": bool(adopt),
            "verify_current": bool(verify_current),
        }
        imported_scope = import_plan.get("imported_requested_mutations") if isinstance(import_plan.get("imported_requested_mutations"), dict) else {}
        scope_blockers: list[dict[str, str]] = []
        for name, requested in requested_scope.items():
            imported_value = imported_scope.get(name)
            if imported_value is not None and bool(imported_value) != requested:
                scope_blockers.append({
                    "code": f"pipeline_resume_{name}_scope_mismatch",
                    "message": f"resume {name}={str(requested).lower()} does not match imported request {name}={str(bool(imported_value)).lower()}",
                })
        if scope_blockers:
            return {
                **import_plan,
                "ok": False,
                "action": "release_pipeline_resume",
                "status": "pipeline_resume_blocked",
                "blockers": [*(import_plan.get("blockers") or []), *scope_blockers],
                "blocker_codes": [*(import_plan.get("blocker_codes") or []), *[item["code"] for item in scope_blockers]],
                "requested_mutations": requested_scope,
                "applied": False,
                "mutating_actions_executed": False,
            }

    contract = load_contract(repo, config)
    version = str(plan["version"])
    artifact = _artifact_path(repo, contract)
    repo_id = str(contract["repository"]["repo_id"])
    run_id = _run_id(version)
    evidence_dir = repo / str(contract["evidence"]["directory"]) / "pipeline" / run_id
    evidence_dir.mkdir(parents=True, exist_ok=False)
    imported_copy_path: Path | None = None
    if imported is not None:
        imported_copy_path = evidence_dir / "imported-pipeline-evidence.json"
        _write_json(imported_copy_path, imported)

    phases: list[dict[str, Any]] = []
    stop_reason: str | None = None
    binding_artifact_sha = sha256_file(artifact) if artifact.is_file() else None
    binding_git_commit = str((import_plan or {}).get("git_commit") or "") or None
    imported_artifact_sha = str((import_plan or {}).get("artifact_sha256") or "") or None
    recovery: dict[str, Any] = {
        "mode": "resumed" if imported is not None else "fresh",
        "imported_evidence_path": str(imported_evidence_path) if imported_evidence_path else None,
        "imported_copy_path": str(imported_copy_path) if imported_copy_path else None,
        "imported_status": (import_plan or {}).get("imported_status"),
        "imported_completed_phases": list((import_plan or {}).get("completed_phases") or []),
        "imported_failed_phases": list((import_plan or {}).get("failed_phases") or []),
        "first_incomplete_phase": (import_plan or {}).get("first_incomplete_phase"),
        "reusable_mutation_phases": sorted(reusable_phases),
        "reused_phases": [],
        "replayed_phases": [],
        "recovery_status": "not_requested" if imported is None else "in_progress",
    }

    def checkpoint(status: str) -> None:
        payload = {
            "ok": status in {"release_pipeline_completed", "release_pipeline_completed_idempotent", "release_pipeline_recovered", "release_pipeline_recovered_idempotent"},
            "schema": PIPELINE_SCHEMA,
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "action": "release_pipeline_apply",
            "status": status,
            "run_id": run_id,
            "repo_path": str(repo),
            "repository": contract["repository"],
            "version": version,
            "artifact": {
                "path": str(artifact),
                "filename": artifact.name,
                "exists": artifact.is_file(),
                "sha256": binding_artifact_sha,
                "size_bytes": artifact.stat().st_size if artifact.is_file() else None,
            },
            "evidence_dir": str(evidence_dir),
            "phase_results": phases,
            "phase_count": len(phases),
            "stop_reason": stop_reason,
            "stage_all_requested": stage_all,
            "commit_requested": commit,
            "push_requested": push,
            "publish_requested": publish,
            "adopt_requested": adopt,
            "verify_current_requested": verify_current,
            "evidence_binding": {
                "repository_id": repo_id,
                "version": version,
                "artifact_filename": artifact.name,
                "artifact_sha256": binding_artifact_sha,
                "git_commit": binding_git_commit,
                "contract_path": config,
                "contract_sha256": _contract_sha256(repo, config),
            },
            "recovery": recovery,
            "updated_at": _utc(),
        }
        _write_json(evidence_dir / PIPELINE_CHECKPOINT_FILENAME, payload)

    def add_phase(phase_id: str, payload: dict[str, Any], *, reused: bool = False) -> dict[str, Any]:
        nonlocal binding_artifact_sha, binding_git_commit
        payload = dict(payload)
        payload["reused"] = bool(reused)
        item = _record_phase(evidence_dir, phase_id, payload)
        phases.append(item)
        if reused:
            recovery["reused_phases"].append(phase_id)
        elif imported is not None:
            recovery["replayed_phases"].append(phase_id)
        artifact_payload = payload.get("artifact") if isinstance(payload.get("artifact"), dict) else {}
        artifact_sha = str(artifact_payload.get("sha256") or "").strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", artifact_sha):
            binding_artifact_sha = artifact_sha
        if phase_id == "git-sync":
            commit_sha = str(payload.get("git_commit_sha") or "").strip().lower()
            if re.fullmatch(r"[0-9a-f]{7,40}", commit_sha):
                binding_git_commit = commit_sha
        checkpoint("pipeline_running")
        return item

    checkpoint("pipeline_running")

    def run_local(phase_id: str, operation: str) -> bool:
        nonlocal stop_reason
        payload = execute_release_contract(repo, contract, operation, runner=runner)
        add_phase(phase_id, payload)
        if not payload.get("ok"):
            stop_reason = f"{phase_id}_failed"
            checkpoint("release_pipeline_recovery_failed" if imported is not None else "release_pipeline_failed")
            return False
        return True

    for phase_id, operation in (
        ("local-validate", "validate"),
        ("local-test", "test"),
        ("local-build", "build"),
        ("local-verify", "verify"),
    ):
        if not run_local(phase_id, operation):
            break

    if stop_reason is None and commit:
        if "git-sync" in reusable_phases:
            git_payload = {
                "ok": True,
                "status": "reused_imported_git_sync",
                "git_commit_sha": str((import_plan or {}).get("git_commit") or ""),
                "commit_performed": True,
                "push_performed": bool(push),
                "imported_evidence_path": str(imported_evidence_path),
                "state_mutated": False,
            }
            add_phase("git-sync", git_payload, reused=True)
        else:
            git_payload = _run_git_commit_push(
                repo,
                contract,
                version=version,
                message=message,
                push=push,
                evidence_dir=evidence_dir,
                runner=runner,
            )
            add_phase("git-sync", git_payload)
            if not git_payload.get("ok"):
                stop_reason = "git_sync_failed"

    if stop_reason is None and commit:
        if not run_local("committed-tree-build", "build"):
            stop_reason = "committed_tree_build_failed"
        elif not run_local("committed-tree-verify", "verify"):
            stop_reason = "committed_tree_verify_failed"

    if stop_reason is None and imported_artifact_sha:
        current_sha = sha256_file(artifact) if artifact.is_file() else None
        binding_artifact_sha = current_sha
        bind_ok = current_sha == imported_artifact_sha
        bind_payload = {
            "ok": bind_ok,
            "status": "imported_artifact_identity_verified" if bind_ok else "imported_artifact_identity_mismatch",
            "expected_sha256": imported_artifact_sha,
            "actual_sha256": current_sha,
            "artifact": str(artifact),
            "state_mutated": False,
        }
        add_phase("recovery-artifact-bind", bind_payload)
        if not bind_ok:
            stop_reason = "imported_artifact_identity_mismatch"

    release_identity: dict[str, Any] | None = None
    identity_current_payload: dict[str, Any] | None = None
    if stop_reason is None and (publish or adopt or verify_current):
        identity_current_result = _command_result(
            [*_pb_command(), "artifact", "current", "--all", "--json"],
            repo=repo,
            evidence_path=evidence_dir / "release-identity-current-command.json",
            timeout=180.0,
            runner=runner,
        )
        identity_current_payload = identity_current_result.get("payload") if isinstance(identity_current_result.get("payload"), dict) else None
        if not artifact.is_file():
            release_identity = {"ok": False, "status": "release_identity_artifact_missing", "artifact": str(artifact)}
        else:
            binding_artifact_sha = sha256_file(artifact)
            release_identity = evaluate_current_release_identity(
                identity_current_payload,
                repo_id=repo_id,
                version=version,
                artifact_filename=artifact.name,
                artifact_sha256=binding_artifact_sha,
            )
        phase_payload = {
            "ok": bool(identity_current_result.get("ok") or identity_current_payload is not None) and bool(release_identity.get("ok")),
            "status": release_identity.get("status"),
            "command_result": identity_current_result,
            "identity": release_identity,
        }
        add_phase("release-identity-preflight", phase_payload)
        if not phase_payload.get("ok"):
            stop_reason = str(release_identity.get("status") or "release_identity_preflight_failed")

    already_current = bool((release_identity or {}).get("already_current"))

    if stop_reason is None and imported is not None and not already_current:
        if "artifact-adopt" in reusable_phases or "accepted-current-verify" in reusable_phases:
            reconcile_payload = {
                "ok": False,
                "status": "imported_adoption_not_current",
                "message": "Imported evidence reports successful adoption/current verification, but the authoritative current identity no longer matches. Automatic replay is forbidden.",
                "imported_adoption_completed": "artifact-adopt" in reusable_phases,
                "imported_current_completed": "accepted-current-verify" in reusable_phases,
                "state_mutated": False,
            }
            add_phase("recovery-adoption-reconcile", reconcile_payload)
            stop_reason = "imported_adoption_not_current"

    source_evidence_path = evidence_dir / "project-source-add.json"
    source_payload: dict[str, Any] | None = None
    if stop_reason is None and publish and not already_current:
        if "project-source-publish" in reusable_phases:
            source_payload = dict((import_plan or {}).get("source") or {})
            source_ok, source_blockers = _valid_source_evidence(source_payload, artifact_sha256=binding_artifact_sha)
            if source_ok:
                _write_json(source_evidence_path, source_payload)
                publish_payload = {
                    "ok": True,
                    "status": "reused_imported_project_source",
                    "source_evidence_path": str(source_evidence_path),
                    "source": source_payload,
                    "imported_evidence_path": str(imported_evidence_path),
                    "state_mutated": False,
                }
                add_phase("project-source-publish", publish_payload, reused=True)
            else:
                publish_payload = {
                    "ok": False,
                    "status": "imported_project_source_evidence_invalid",
                    "blocker_codes": source_blockers,
                    "source": source_payload,
                    "state_mutated": False,
                }
                add_phase("project-source-publish", publish_payload, reused=True)
                stop_reason = "project_source_import_failed"
        else:
            source_command = [*_pb_command(), "src", "add", str(artifact), "--no-overwrite", "--json"]
            source_result = _command_result(
                source_command,
                repo=repo,
                evidence_path=evidence_dir / "project-source-add-command.json",
                timeout=1200.0,
                runner=runner,
            )
            source_payload = source_result.get("payload") if isinstance(source_result.get("payload"), dict) else None
            if source_payload is not None:
                _write_json(source_evidence_path, source_payload)
            required_source = bool(
                source_result.get("ok")
                and source_payload
                and source_payload.get("ok") is True
                and source_payload.get("persistence_verified") is True
                and source_payload.get("assigned_filename")
                and source_payload.get("processed_file_id")
                and source_payload.get("library_metadata_object_id")
                and bool(re.fullmatch(r"[0-9a-f]{64}", str(source_payload.get("local_sha256") or "").strip().lower()))
                and str(source_payload.get("local_sha256") or "").strip().lower() == binding_artifact_sha
            )
            publish_payload = {
                "ok": required_source,
                "status": "project_source_published" if required_source else "project_source_publication_unverified",
                "command_result": source_result,
                "source_evidence_path": str(source_evidence_path) if source_payload is not None else None,
                "source": source_payload,
            }
            add_phase("project-source-publish", publish_payload)
            if not publish_payload.get("ok"):
                stop_reason = "project_source_publish_failed"

    adoption_payload: dict[str, Any] | None = None
    if stop_reason is None and adopt and not already_current:
        adopt_command = [
            *_pb_command(),
            "artifact",
            "adopt",
            artifact.name,
            "--from-project-source",
            "--local-path",
            str(artifact),
            "--repo",
            repo_id,
            "--source-evidence-json",
            str(source_evidence_path),
            "--json",
        ]
        adoption_result = _command_result(
            adopt_command,
            repo=repo,
            evidence_path=evidence_dir / "artifact-adopt-command.json",
            timeout=1200.0,
            runner=runner,
        )
        adoption_payload = adoption_result.get("payload") if isinstance(adoption_result.get("payload"), dict) else None
        adoption_status = str((adoption_payload or {}).get("status") or "")
        adopted_with_updates = bool(
            adoption_status == "adopted"
            and adoption_payload.get("source_evidence_verified") is True
            and adoption_payload.get("artifact_registry_updated") is True
            and adoption_payload.get("state_artifact_updated") is True
            and adoption_payload.get("state_source_updated") is True
        ) if adoption_payload else False
        idempotent_adoption = bool(
            adoption_status == "already_adopted"
            and adoption_payload.get("idempotent") is True
            and adoption_payload.get("mutating_actions_executed") is False
            and adoption_payload.get("artifact_registry_updated") is False
            and adoption_payload.get("state_artifact_updated") is False
            and adoption_payload.get("state_source_updated") is False
        ) if adoption_payload else False
        adoption_verified = bool(
            adoption_result.get("ok")
            and adoption_payload
            and adoption_payload.get("ok") is True
            and adoption_payload.get("source_verified") is True
            and (adopted_with_updates or idempotent_adoption)
        )
        phase_payload = {
            "ok": adoption_verified,
            "status": "artifact_adopted" if adoption_verified else "artifact_adoption_unverified",
            "command_result": adoption_result,
            "adoption": adoption_payload,
        }
        add_phase("artifact-adopt", phase_payload)
        if not phase_payload.get("ok"):
            stop_reason = "artifact_adopt_failed"

    current_payload: dict[str, Any] | None = None
    if stop_reason is None and verify_current:
        if already_current:
            current_result = {"ok": True, "status": "reused_release_identity_preflight", "payload": identity_current_payload}
            current_payload = identity_current_payload
            _write_json(evidence_dir / "artifact-current-command.json", current_result)
        else:
            current_result = _command_result(
                [*_pb_command(), "artifact", "current", "--all", "--json"],
                repo=repo,
                evidence_path=evidence_dir / "artifact-current-command.json",
                timeout=180.0,
                runner=runner,
            )
            current_payload = current_result.get("payload") if isinstance(current_result.get("payload"), dict) else None
        selected_repo = ((current_payload or {}).get("repos") or {}).get(repo_id) or {}
        repo_state = selected_repo.get("state") or {}
        registry_current = selected_repo.get("registry_current") or {}
        consistency = selected_repo.get("consistency") or {}
        expected_source_ref = str((source_payload or {}).get("assigned_filename") or repo_state.get("source_ref") or "")
        current_verified = bool(
            current_result.get("ok")
            and current_payload
            and current_payload.get("ok") is True
            and current_payload.get("missing_repo_count", 0) == 0
            and selected_repo.get("ok", True) is True
            and repo_state.get("artifact_ref") == artifact.name
            and repo_state.get("artifact_version") == version
            and repo_state.get("source_ref") == expected_source_ref
            and repo_state.get("source_version") == version
            and registry_current.get("filename") == artifact.name
            and registry_current.get("version") == version
            and bool(re.fullmatch(r"[0-9a-f]{64}", str(registry_current.get("sha256") or "").strip().lower()))
            and str(registry_current.get("sha256") or "").strip().lower() == binding_artifact_sha
            and consistency.get("registry_current_matches_state_artifact") is True
            and consistency.get("state_source_matches_state_artifact") is True
        )
        phase_payload = {
            "ok": current_verified,
            "status": "accepted_current_verified" if current_verified else "accepted_current_mismatch",
            "command_result": current_result,
            "current": current_payload,
            "expected_source_ref": expected_source_ref,
            "selected_repo_state": repo_state,
            "selected_registry_current": registry_current,
            "selected_consistency": consistency,
        }
        add_phase("accepted-current-verify", phase_payload, reused=bool(already_current and imported is not None))
        if not phase_payload.get("ok"):
            stop_reason = "accepted_current_verify_failed"

    final_ok = stop_reason is None
    if imported is None:
        final_status = "release_pipeline_completed_idempotent" if final_ok and already_current else ("release_pipeline_completed" if final_ok else "release_pipeline_failed")
    else:
        final_status = "release_pipeline_recovered_idempotent" if final_ok and already_current else ("release_pipeline_recovered" if final_ok else "release_pipeline_recovery_failed")
        recovery["recovery_status"] = "completed" if final_ok else "failed"
    binding_artifact_sha = sha256_file(artifact) if artifact.is_file() else binding_artifact_sha
    summary = {
        "ok": final_ok,
        "schema": PIPELINE_SCHEMA,
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "action": "release_pipeline_apply",
        "status": final_status,
        "run_id": run_id,
        "repo_path": str(repo),
        "repository": contract["repository"],
        "version": version,
        "artifact": {
            "path": str(artifact),
            "filename": artifact.name,
            "exists": artifact.is_file(),
            "sha256": binding_artifact_sha,
            "size_bytes": artifact.stat().st_size if artifact.is_file() else None,
        },
        "evidence_binding": {
            "repository_id": repo_id,
            "version": version,
            "artifact_filename": artifact.name,
            "artifact_sha256": binding_artifact_sha,
            "git_commit": binding_git_commit,
            "contract_path": config,
            "contract_sha256": _contract_sha256(repo, config),
        },
        "evidence_dir": str(evidence_dir),
        "checkpoint_path": str(evidence_dir / PIPELINE_CHECKPOINT_FILENAME),
        "phase_results": phases,
        "phase_count": len(phases),
        "stop_reason": stop_reason,
        "stage_all_requested": stage_all,
        "commit_requested": commit,
        "push_requested": push,
        "publish_requested": publish,
        "adopt_requested": adopt,
        "verify_current_requested": verify_current,
        "source_evidence_path": str(source_evidence_path) if source_payload is not None else None,
        "source": source_payload,
        "adoption": adoption_payload,
        "current": current_payload,
        "release_identity": release_identity,
        "already_current": already_current,
        "recovery": recovery,
        "mutating_actions_executed": any(
            not bool((item.get("payload") or {}).get("reused"))
            and (
                bool((item.get("payload") or {}).get("commit_performed"))
                or item.get("phase") in {"local-build", "committed-tree-build", "project-source-publish", "artifact-adopt"}
            )
            for item in phases
        ),
        "safety": {
            "explicit_version_confirmation": True,
            "publication_after_push": not publish or push,
            "adoption_evidence_bound": not adopt or already_current or source_payload is not None,
            "accepted_current_verified": not verify_current or final_ok,
            "later_phases_skipped_after_failure": True,
            "successful_mutation_phases_not_replayed": imported is None or all(
                phase_id in recovery["reused_phases"] or phase_id not in reusable_phases
                for phase_id in PIPELINE_MUTATION_PHASES
            ),
            "recovery_evidence_imported_read_only": imported is None or bool(import_plan and import_plan.get("state_mutated") is False),
        },
    }
    _write_json(evidence_dir / PIPELINE_SUMMARY_FILENAME, summary)
    checkpoint(final_status)
    return summary


def build_pbai_compliance_inventory(
    repo_paths: Sequence[str | Path],
    *,
    level: str = "executable",
    config: str = ".promptbranch-ai.json",
    release_config: str = ".promptbranch-release.json",
) -> dict[str, Any]:
    repositories: list[dict[str, Any]] = []
    for value in repo_paths:
        repo = Path(value).expanduser().resolve()
        item: dict[str, Any] = {
            "repo_path": str(repo),
            "exists": repo.is_dir(),
            "application_id": None,
            "application_kind": None,
            "version": None,
            "migration": None,
            "validation": None,
            "release_contract": None,
            "rollout_ready": False,
            "errors": [],
        }
        if not repo.is_dir():
            item["errors"].append("repository path not found")
            repositories.append(item)
            continue
        declaration: dict[str, Any] | None = None
        try:
            declaration = load_application_declaration(repo, config)
            application = declaration.get("application") if isinstance(declaration.get("application"), dict) else {}
            item["application_id"] = application.get("id")
            item["application_kind"] = application.get("kind")
            authority = declaration.get("version_authority") if isinstance(declaration.get("version_authority"), dict) else {}
            version_path = repo / str(authority.get("path") or "VERSION")
            if version_path.is_file():
                item["version"] = version_path.read_text(encoding="utf-8").strip()
        except (ApplicationArchitectureError, OSError) as exc:
            item["errors"].append(str(exc))
        try:
            item["migration"] = build_application_migration_report(
                repo,
                kind=item.get("application_kind") or "domain_module",
                application_id=item.get("application_id") or repo.name.replace("_", "-"),
                config=config,
            )
        except ApplicationMigrationError as exc:
            item["errors"].append(str(exc))
        try:
            item["validation"] = validate_application_architecture(repo, config, level=level)
        except (ApplicationArchitectureError, OSError, ValueError) as exc:
            item["errors"].append(str(exc))
            item["validation"] = {
                "ok": False,
                "status": "application_validation_failed",
                "error": str(exc),
            }
        try:
            release_contract = load_contract(repo, release_config)
            item["release_contract"] = plan_release_contract(repo, release_contract)
        except (ReleaseContractError, OSError, ValueError) as exc:
            item["errors"].append(str(exc))
            item["release_contract"] = {
                "ok": False,
                "status": "release_contract_invalid",
                "error": str(exc),
            }
        item["rollout_ready"] = bool(
            (item.get("migration") or {}).get("status") == "already_migrated"
            and (item.get("validation") or {}).get("ok") is True
            and (item.get("release_contract") or {}).get("ok") is True
        )
        repositories.append(item)
    ready_count = sum(1 for item in repositories if item.get("rollout_ready"))
    return {
        "ok": all(item.get("exists") for item in repositories),
        "schema": INVENTORY_SCHEMA,
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "action": "pbai_compliance_inventory",
        "status": "inventory_complete",
        "requested_level": level,
        "repository_count": len(repositories),
        "rollout_ready_count": ready_count,
        "blocked_count": len(repositories) - ready_count,
        "repositories": repositories,
        "safety": {
            "read_only": True,
            "state_mutated": False,
            "publication_performed": False,
            "adoption_performed": False,
        },
    }

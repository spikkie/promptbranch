from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from promptbranch_source_fingerprint import SOURCE_PRESERVE_ROOTS, SOURCE_TRANSIENT_PARTS, source_fingerprint
from promptbranch_release_eta import (
    append_release_eta_observation,
    build_release_eta_snapshot,
    sync_release_eta_history_from_attempts,
    write_release_eta_snapshot,
)

from promptbranch_artifacts import (
    canonical_artifact_filename,
    infer_repo_id_from_artifact_filename,
    parse_canonical_artifact_filename,
    valid_version_text,
    verify_zip_artifact,
)

SCHEMA = "promptbranch.release_attempt"
SCHEMA_VERSION = "2.0"
ACTION_RUN = "release_state_machine_run"
ACTION_VERIFY = "release_state_machine_verify"
REQUIRED_PYTEST_VERSION = "9.0.2"
REQUIRED_ARTIFACT_ROOT_ENTRIES: tuple[str, ...] = (
    "VERSION",
    "pyproject.toml",
    ".promptbranch-release.json",
    ".promptbranch-repo.json",
    "promptbranch_cli.py",
    "promptbranch_release_state_machine.py",
)

NORMAL_STATES: tuple[str, ...] = (
    "DECLARED",
    "ARTIFACT_BOUND",
    "ARTIFACT_VERIFIED",
    "CANDIDATE_REGISTERED",
    "RUNTIME_PREPARED",
    "TESTED_GREEN",
    "ACCEPTED",
    "ADOPTED_CURRENT",
    "FINAL_VERIFIED",
)
FAILURE_STATES: tuple[str, ...] = ("BLOCKED_RETRYABLE", "FAILED_TERMINAL")
STATE_INDEX = {state: index for index, state in enumerate(NORMAL_STATES)}

STATE_ALIASES = {
    "declared": "DECLARED",
    "artifact-bound": "ARTIFACT_BOUND",
    "artifact_bound": "ARTIFACT_BOUND",
    "artifact-verified": "ARTIFACT_VERIFIED",
    "artifact_verified": "ARTIFACT_VERIFIED",
    "candidate-registered": "CANDIDATE_REGISTERED",
    "candidate_registered": "CANDIDATE_REGISTERED",
    "runtime-prepared": "RUNTIME_PREPARED",
    "runtime_prepared": "RUNTIME_PREPARED",
    "tested-green": "TESTED_GREEN",
    "tested_green": "TESTED_GREEN",
    "accepted": "ACCEPTED",
    "adopted-current": "ADOPTED_CURRENT",
    "adopted_current": "ADOPTED_CURRENT",
    "final-verified": "FINAL_VERIFIED",
    "final_verified": "FINAL_VERIFIED",
    "complete": "FINAL_VERIFIED",
}

LEGAL_TRANSITIONS = {
    "DECLARED": "ARTIFACT_BOUND",
    "ARTIFACT_BOUND": "ARTIFACT_VERIFIED",
    "ARTIFACT_VERIFIED": "CANDIDATE_REGISTERED",
    "CANDIDATE_REGISTERED": "RUNTIME_PREPARED",
    "RUNTIME_PREPARED": "TESTED_GREEN",
    "TESTED_GREEN": "ACCEPTED",
    "ACCEPTED": "ADOPTED_CURRENT",
    "ADOPTED_CURRENT": "FINAL_VERIFIED",
    "FINAL_VERIFIED": None,
}


class ReleaseStateMachineError(RuntimeError):
    """State-machine contract violation."""


class TransitionBlocked(ReleaseStateMachineError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class TransitionTerminalFailure(ReleaseStateMachineError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_state(value: str | None) -> str:
    text = str(value or "").strip()
    if text in NORMAL_STATES:
        return text
    normalized = text.lower().replace(" ", "-")
    if normalized in STATE_ALIASES:
        return STATE_ALIASES[normalized]
    raise ReleaseStateMachineError(f"unknown release state: {value}")


def _conversation_id_from_url(value: str | None) -> str | None:
    text=str(value or "").strip()
    if not text.startswith("https://chatgpt.com/g/") or "/c/" not in text: return None
    tail=text.split("/c/",1)[1].split("/",1)[0].split("?",1)[0].strip(); return tail or None


def _version_tuple(value: str) -> tuple[int, ...]:
    text = str(value or "").strip().removeprefix("v")
    try:
        return tuple(int(part) for part in text.split("."))
    except ValueError as exc:
        raise ReleaseStateMachineError(f"invalid numeric version: {value}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if tmp.exists():
            tmp.unlink()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReleaseStateMachineError(f"JSON root must be an object: {path}")
    return value


def _accepted_runtime_exact_checks(snapshot: dict[str, Any], *, expected_version: str) -> dict[str, bool]:
    container = snapshot.get("container") if isinstance(snapshot.get("container"), dict) else {}
    health = snapshot.get("health") if isinstance(snapshot.get("health"), dict) else {}
    labels = snapshot.get("image_labels") if isinstance(snapshot.get("image_labels"), dict) else {}
    artifact_sha = str(labels.get("promptbranch.artifact_sha256") or "").strip()
    return {
        "docker_ps_ok": snapshot.get("docker_ps_returncode") == 0,
        "exactly_one_authoritative_container": snapshot.get("container_count") == 1,
        "accepted_runtime_present": snapshot.get("present") is True and bool(container.get("container_id")),
        "accepted_health_ok": health.get("ok") is True,
        "accepted_health_version_exact": str(health.get("version") or "") == expected_version,
        "accepted_image_inspect_ok": snapshot.get("image_inspect_ok") is True,
        "accepted_image_version_label_exact": str(labels.get("promptbranch.version") or "") == expected_version,
        "accepted_image_artifact_sha_present": bool(artifact_sha),
    }


def _accepted_runtime_preservation_checks(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    expected_version: str,
) -> dict[str, bool]:
    before_exact = _accepted_runtime_exact_checks(before, expected_version=expected_version)
    after_exact = _accepted_runtime_exact_checks(after, expected_version=expected_version)
    before_container = before.get("container") if isinstance(before.get("container"), dict) else {}
    after_container = after.get("container") if isinstance(after.get("container"), dict) else {}
    before_labels = before.get("image_labels") if isinstance(before.get("image_labels"), dict) else {}
    after_labels = after.get("image_labels") if isinstance(after.get("image_labels"), dict) else {}
    before_container_id = str(before_container.get("container_id") or "").strip()
    after_container_id = str(after_container.get("container_id") or "").strip()
    before_image_id = str(before.get("image_id") or "").strip()
    after_image_id = str(after.get("image_id") or "").strip()
    before_sha = str(before_labels.get("promptbranch.artifact_sha256") or "").strip()
    after_sha = str(after_labels.get("promptbranch.artifact_sha256") or "").strip()
    container_unchanged = bool(before_container_id) and before_container_id == after_container_id
    image_unchanged = bool(before_image_id) and before_image_id == after_image_id
    artifact_sha_unchanged = bool(before_sha) and before_sha == after_sha
    before_ok = all(before_exact.values())
    after_ok = all(after_exact.values())
    return {
        "accepted_runtime_before_exact": before_ok,
        "accepted_runtime_after_exact": after_ok,
        "accepted_runtime_container_unchanged": container_unchanged,
        "accepted_runtime_image_unchanged": image_unchanged,
        "accepted_runtime_artifact_sha_unchanged": artifact_sha_unchanged,
        "accepted_runtime_unchanged": before_ok and after_ok and container_unchanged and image_unchanged and artifact_sha_unchanged,
    }


def _safe_extract(artifact: Path, destination: Path) -> None:
    """Extract a verified ZIP while preserving executable bits deterministically."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(artifact) as archive:
        for info in archive.infolist():
            target = (root / info.filename).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise TransitionTerminalFailure(
                    "unsafe_zip_path",
                    f"unsafe ZIP entry: {info.filename}",
                    details={"entry": info.filename},
                ) from exc
            archive.extract(info, destination)
            if target.exists() and not target.is_symlink():
                archived_mode = (info.external_attr >> 16) & 0o777
                if info.is_dir():
                    target.chmod(archived_mode or 0o755)
                elif archived_mode:
                    target.chmod(archived_mode)
                elif target.suffix == ".sh" or info.filename in {"pb", "promptbranch"}:
                    target.chmod(0o755)
                else:
                    target.chmod(0o644)


def _read_zip_version(path: Path) -> str | None:
    with zipfile.ZipFile(path) as archive:
        try:
            return archive.read("VERSION").decode("utf-8").strip()
        except (KeyError, UnicodeDecodeError):
            return None


def _parse_json_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            objects.append(value)
    return objects


def _last_json_object(text: str) -> dict[str, Any] | None:
    objects = _parse_json_objects(text)
    return objects[-1] if objects else None


TEST_REPORT_SCHEMA = "promptbranch.test_suite.report"
TEST_REPORT_SCHEMA_VERSION = "1.0"
ACCEPT_CANDIDATE_ACTION = "artifact_accept_candidate"
CURRENT_STATUS_ACTIONS = ("artifact_current", "artifact_current_all")


def _parse_json_documents(text: str) -> list[dict[str, Any]]:
    """Parse complete top-level JSON documents embedded in mixed stdout.

    Unlike ``_parse_json_objects``, this scanner advances past a successfully
    decoded document. Nested dictionaries inside a report are therefore not
    returned as independent candidate reports.
    """

    decoder = json.JSONDecoder()
    documents: list[dict[str, Any]] = []
    index = 0
    while index < len(text):
        next_object = text.find("{", index)
        if next_object < 0:
            break
        try:
            value, consumed = decoder.raw_decode(text[next_object:])
        except json.JSONDecodeError:
            index = next_object + 1
            continue
        if isinstance(value, dict):
            documents.append(value)
        index = next_object + max(consumed, 1)
    return documents


def _select_action_document(
    text: str,
    *,
    actions: tuple[str, ...],
    result_name: str,
    require_status: bool = True,
) -> dict[str, Any]:
    """Select exactly one complete top-level command result by action.

    Command stdout may contain nested JSON objects. Only complete top-level
    documents returned by ``_parse_json_documents`` are eligible.
    """

    documents = _parse_json_documents(text)
    matches = [item for item in documents if str(item.get("action") or "") in actions]
    if not matches:
        return {
            "ok": False,
            "status": f"{result_name}_report_missing",
            "failure_code": f"{result_name}_report_missing",
            "document_count": len(documents),
            "match_count": 0,
            "result": None,
            "errors": ["no_matching_action"],
        }
    if len(matches) != 1:
        return {
            "ok": False,
            "status": f"{result_name}_report_ambiguous",
            "failure_code": f"{result_name}_report_ambiguous",
            "document_count": len(documents),
            "match_count": len(matches),
            "result": None,
            "errors": ["multiple_matching_actions"],
        }
    payload = matches[0]
    errors: list[str] = []
    if not isinstance(payload.get("ok"), bool):
        errors.append("ok_not_boolean")
    if require_status and (not isinstance(payload.get("status"), str) or not str(payload.get("status") or "").strip()):
        errors.append("status_missing")
    if errors:
        return {
            "ok": False,
            "status": f"{result_name}_report_invalid",
            "failure_code": f"{result_name}_report_invalid",
            "document_count": len(documents),
            "match_count": 1,
            "result": payload,
            "errors": errors,
        }
    return {
        "ok": True,
        "status": f"{result_name}_report_selected",
        "failure_code": None,
        "document_count": len(documents),
        "match_count": 1,
        "result": payload,
        "errors": [],
    }


def _select_accept_candidate_result(text: str) -> dict[str, Any]:
    return _select_action_document(
        text,
        actions=(ACCEPT_CANDIDATE_ACTION,),
        result_name="candidate_acceptance",
    )


def _select_current_status_result(text: str) -> dict[str, Any]:
    return _select_action_document(
        text,
        actions=CURRENT_STATUS_ACTIONS,
        result_name="artifact_current",
    )


def _current_repo_entry(payload: dict[str, Any], *, repo_id: str) -> dict[str, Any] | None:
    action = str(payload.get("action") or "")
    if action == "artifact_current_all":
        repos = payload.get("repos") if isinstance(payload.get("repos"), dict) else {}
        entry = repos.get(repo_id)
        return entry if isinstance(entry, dict) else None
    if action == "artifact_current":
        scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
        scoped_repo = str(scope.get("repo_id") or payload.get("repo_id") or "")
        if scoped_repo and scoped_repo != repo_id:
            return None
        return payload
    return None


def _current_candidate_alignment_checks(
    payload: dict[str, Any],
    *,
    repo_id: str,
    filename: str,
    version: str,
    sha256: str,
) -> dict[str, bool]:
    entry = _current_repo_entry(payload, repo_id=repo_id)
    state = entry.get("state") if isinstance(entry, dict) and isinstance(entry.get("state"), dict) else {}
    current = entry.get("registry_current") if isinstance(entry, dict) and isinstance(entry.get("registry_current"), dict) else {}
    return {
        "repo_entry_present": isinstance(entry, dict),
        "state_artifact_ref_exact": str(state.get("artifact_ref") or "") == filename,
        "state_artifact_version_exact": str(state.get("artifact_version") or "") == version,
        "state_source_ref_exact": str(state.get("source_ref") or "") == filename,
        "state_source_version_exact": str(state.get("source_version") or "") == version,
        "registry_current_ref_exact": str(current.get("filename") or current.get("artifact_ref") or "") == filename,
        "registry_current_version_exact": str(current.get("version") or "") == version,
        "registry_current_sha_exact": str(current.get("sha256") or "").lower() == sha256.lower(),
    }


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _test_report_shape_errors(payload: dict[str, Any], *, profile: str, version: str) -> list[str]:
    errors: list[str] = []
    expected_action = "test_smoke" if profile == "smoke" else "test_suite"
    if payload.get("action") != expected_action:
        errors.append("action_mismatch")
    if payload.get("profile") != profile:
        errors.append("profile_mismatch")
    if payload.get("version") != version:
        errors.append("version_mismatch")
    if payload.get("schema") != TEST_REPORT_SCHEMA:
        errors.append("schema_mismatch")
    if payload.get("schema_version") != TEST_REPORT_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if not isinstance(payload.get("ok"), bool):
        errors.append("ok_not_boolean")

    if profile == "full":
        progress = payload.get("progress")
        if not isinstance(progress, dict):
            errors.append("progress_missing")
            return errors
        required_integer_fields = (
            "total_units",
            "completed_units",
            "passed_units",
            "failed_units",
            "skipped_units",
        )
        for key in required_integer_fields:
            value = progress.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"progress_{key}_invalid")
        if isinstance(progress.get("total_units"), int) and isinstance(progress.get("completed_units"), int):
            if progress["completed_units"] != progress["total_units"]:
                errors.append("progress_incomplete")
        if not isinstance(progress.get("states"), dict):
            errors.append("progress_states_invalid")
        if not isinstance(progress.get("unresolved_steps"), list):
            errors.append("progress_unresolved_steps_invalid")
    else:
        if not isinstance(payload.get("steps"), list):
            errors.append("steps_missing")
        if not isinstance(payload.get("step_count"), int):
            errors.append("step_count_invalid")
    return errors


def _select_candidate_test_report(text: str, *, profile: str, version: str) -> dict[str, Any]:
    expected_action = "test_smoke" if profile == "smoke" else "test_suite"
    documents = _parse_json_documents(text)
    identity_matches = [
        item
        for item in documents
        if item.get("action") == expected_action
        and item.get("profile") == profile
        and item.get("version") == version
    ]
    if not identity_matches:
        return {
            "ok": False,
            "status": "candidate_test_report_missing",
            "failure_code": "candidate_test_report_missing",
            "document_count": len(documents),
            "match_count": 0,
            "report": None,
            "errors": ["no_action_profile_version_match"],
        }
    if len(identity_matches) != 1:
        return {
            "ok": False,
            "status": "candidate_test_report_ambiguous",
            "failure_code": "candidate_test_report_ambiguous",
            "document_count": len(documents),
            "match_count": len(identity_matches),
            "report": None,
            "errors": ["multiple_action_profile_version_matches"],
        }
    report = identity_matches[0]
    errors = _test_report_shape_errors(report, profile=profile, version=version)
    if errors:
        return {
            "ok": False,
            "status": "candidate_test_report_invalid",
            "failure_code": "candidate_test_report_invalid",
            "document_count": len(documents),
            "match_count": 1,
            "report": report,
            "errors": errors,
        }
    return {
        "ok": True,
        "status": "candidate_test_report_selected",
        "failure_code": None,
        "document_count": len(documents),
        "match_count": 1,
        "report": report,
        "errors": [],
    }


def _test_report_counts(payload: dict[str, Any], *, profile: str) -> dict[str, Any]:
    if profile == "full":
        progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else {}
        states = progress.get("states") if isinstance(progress.get("states"), dict) else {}
        failed_groups = [
            name.removeprefix("validation.")
            for name, state in states.items()
            if str(name).startswith("validation.") and str(state).startswith("failed")
        ]
        failed_steps = [
            name
            for name, state in states.items()
            if str(state).startswith("failed")
        ]
        return {
            "completed": progress.get("completed_units"),
            "passed": progress.get("passed_units"),
            "failed": progress.get("failed_units"),
            "skipped": progress.get("skipped_units"),
            "failed_group": failed_groups[0] if failed_groups else None,
            "failed_groups": failed_groups,
            "failed_steps": failed_steps,
        }
    steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
    failed_steps = [str(item.get("name")) for item in steps if isinstance(item, dict) and item.get("ok") is not True]
    passed = sum(1 for item in steps if isinstance(item, dict) and item.get("ok") is True)
    failed = len(failed_steps)
    return {
        "completed": len(steps),
        "passed": passed,
        "failed": failed,
        "skipped": 0,
        "failed_group": None,
        "failed_groups": [],
        "failed_steps": failed_steps,
    }


def _candidate_registry_path(profile_dir: Path) -> Path:
    return profile_dir / "artifact_candidates.json"


def _candidate_test_dir(profile_dir: Path, version: str) -> Path:
    return profile_dir / "artifact_candidate_tests" / version


def _load_candidate_registry(profile_dir: Path) -> dict[str, Any]:
    path = _candidate_registry_path(profile_dir)
    if not path.exists():
        return {"schema_version": 1, "candidates": []}
    try:
        payload = _read_json(path)
    except (OSError, json.JSONDecodeError, ReleaseStateMachineError):
        return {"schema_version": 1, "candidates": []}
    if not isinstance(payload.get("candidates"), list):
        payload["candidates"] = []
    payload.setdefault("schema_version", 1)
    return payload


def _write_candidate_registry(profile_dir: Path, payload: dict[str, Any]) -> Path:
    path = _candidate_registry_path(profile_dir)
    payload = dict(payload)
    payload["schema_version"] = 1
    payload["updated_at"] = utc_now()
    _atomic_write_json(path, payload)
    return path


def _candidate_matches(item: dict[str, Any], *, repo_id: str, version: str, sha256: str) -> bool:
    filename = str(item.get("filename") or Path(str(item.get("path") or "")).name)
    item_repo = str(item.get("repo_id") or infer_repo_id_from_artifact_filename(filename) or "")
    item_version = str(item.get("version") or item.get("zip_version") or item.get("filename_version") or "")
    return item_repo == repo_id and item_version == version and str(item.get("sha256") or "").lower() == sha256.lower()


def _candidate_conflicts(item: dict[str, Any], *, repo_id: str, version: str, sha256: str) -> bool:
    filename = str(item.get("filename") or Path(str(item.get("path") or "")).name)
    item_repo = str(item.get("repo_id") or infer_repo_id_from_artifact_filename(filename) or "")
    item_version = str(item.get("version") or item.get("zip_version") or item.get("filename_version") or "")
    item_sha = str(item.get("sha256") or "").lower()
    return item_repo == repo_id and item_version == version and bool(item_sha) and item_sha != sha256.lower()


class ReleaseExecutor(Protocol):
    def prepare_runtime(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]: ...

    def run_tests(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]: ...

    def accept_candidate(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]: ...

    def current_status(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]: ...

    def authoritative_runtime_status(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]: ...

    def promote_authoritative_runtime(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]: ...

    def cleanup_candidate_runtimes(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]: ...

    def optional_publication(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ReleaseStateMachineConfig:
    repo_root: Path
    profile_dir: Path
    artifact: Path
    version: str
    baseline_version: str
    release_type: str = "repair"
    profile: str = "full"
    test_timeout: float = 3600.0
    until: str = "TESTED_GREEN"
    adopt: bool = False
    commit: bool = False
    push: bool = False
    upload_project_source: bool = False
    candidate_python: str | None = None
    artifact_conversation_url: str | None = None

    def normalized(self) -> "ReleaseStateMachineConfig":
        repo_root = self.repo_root.expanduser().resolve()
        profile_dir = self.profile_dir.expanduser().resolve()
        artifact = self.artifact.expanduser().resolve()
        version = self.version if self.version.startswith("v") else f"v{self.version}"
        baseline = self.baseline_version if self.baseline_version.startswith("v") else f"v{self.baseline_version}"
        if not valid_version_text(version):
            raise ReleaseStateMachineError(f"invalid target version: {version}")
        if not valid_version_text(baseline):
            raise ReleaseStateMachineError(f"invalid baseline version: {baseline}")
        if self.release_type not in {"normal", "repair"}:
            raise ReleaseStateMachineError(f"invalid release type: {self.release_type}")
        if self.profile not in {"smoke", "full"}:
            raise ReleaseStateMachineError(f"invalid test profile: {self.profile}")
        if _version_tuple(version) <= _version_tuple(baseline):
            raise ReleaseStateMachineError(f"target version must be newer than baseline: {version} <= {baseline}")
        if self.push and not self.commit:
            raise ReleaseStateMachineError("--push requires --commit")
        return ReleaseStateMachineConfig(
            repo_root=repo_root,
            profile_dir=profile_dir,
            artifact=artifact,
            version=version,
            baseline_version=baseline,
            release_type=self.release_type,
            profile=self.profile,
            test_timeout=float(self.test_timeout),
            until=canonical_state(self.until),
            adopt=bool(self.adopt),
            commit=bool(self.commit),
            push=bool(self.push),
            upload_project_source=bool(self.upload_project_source),
            candidate_python=self.candidate_python,
            artifact_conversation_url=str(self.artifact_conversation_url or "").strip() or None,
        )


class SubprocessReleaseExecutor:
    SOURCE_PRESERVE_ROOTS = SOURCE_PRESERVE_ROOTS
    SOURCE_TRANSIENT_PARTS = SOURCE_TRANSIENT_PARTS

    """Production adapter that executes the exact extracted candidate code.

    Runtime preparation is phase-checkpointed and uses an attempt-specific
    Compose project, image and host port. The accepted service remains on its
    canonical port until an explicit later adoption/promotion policy acts.
    """

    RUNTIME_PHASES: tuple[str, ...] = (
        "candidate_extracted",
        "candidate_cli_installed",
        "candidate_image_built",
        "candidate_container_started",
        "candidate_health_verified",
        "candidate_identity_verified",
    )

    def _python(self, machine: "ReleaseStateMachine") -> Path:
        explicit = machine.config.candidate_python or os.environ.get("PROMPTBRANCH_CANDIDATE_PYTHON")
        if explicit:
            candidate = Path(explicit).expanduser().resolve()
            if candidate.is_file():
                return candidate
        pipx = Path.home() / ".local/share/pipx/venvs/promptbranch/bin/python"
        return pipx if pipx.is_file() else Path(sys.executable).resolve()

    def _runtime_paths(self, machine: "ReleaseStateMachine") -> dict[str, Path]:
        root = machine.attempt_dir / "runtime"
        return {
            "root": root,
            "extracted": root / "extracted",
            "pycache": root / "pycache",
            "project_state": root / "project-state",
            "project_config": root / "project-config",
            "xdg_state": root / "xdg-state",
            "xdg_config": root / "xdg-config",
            "home": root / "home",
            "logs": root / "logs",
            "diagnostics": root / "diagnostics",
            "checkpoint": root / "runtime-checkpoint.json",
        }

    def _load_runtime_checkpoint(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        paths = self._runtime_paths(machine)
        checkpoint_path = paths["checkpoint"]
        if checkpoint_path.is_file():
            checkpoint = _read_json(checkpoint_path)
            if checkpoint.get("attempt_id") != record.get("attempt_id"):
                raise TransitionTerminalFailure(
                    "runtime_checkpoint_identity_conflict",
                    "runtime checkpoint belongs to another release attempt",
                    details={"checkpoint_path": str(checkpoint_path)},
                )
            if checkpoint.get("artifact_sha256") != record.get("artifact", {}).get("sha256"):
                raise TransitionTerminalFailure(
                    "runtime_checkpoint_identity_conflict",
                    "runtime checkpoint artifact identity differs from the release attempt",
                    details={"checkpoint_path": str(checkpoint_path)},
                )
            return checkpoint
        checkpoint = {
            "schema": "promptbranch.release_runtime_checkpoint",
            "schema_version": "1.0",
            "attempt_id": record.get("attempt_id"),
            "artifact_sha256": record.get("artifact", {}).get("sha256"),
            "target_version": machine.config.version,
            "completed_phases": [],
            "phase_evidence": {},
            "last_phase": None,
            "failure": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        self._save_runtime_checkpoint(machine, checkpoint)
        return checkpoint

    def _save_runtime_checkpoint(self, machine: "ReleaseStateMachine", checkpoint: dict[str, Any]) -> None:
        checkpoint["updated_at"] = utc_now()
        _atomic_write_json(self._runtime_paths(machine)["checkpoint"], checkpoint)

    def _clear_runtime_phases_from(
        self,
        machine: "ReleaseStateMachine",
        checkpoint: dict[str, Any],
        phase: str,
        *,
        reason: str,
    ) -> None:
        start = self.RUNTIME_PHASES.index(phase)
        invalidated = set(self.RUNTIME_PHASES[start:])
        checkpoint["completed_phases"] = [
            item for item in checkpoint.get("completed_phases", []) if item not in invalidated
        ]
        phase_evidence = checkpoint.setdefault("phase_evidence", {})
        for name in invalidated:
            phase_evidence.pop(name, None)
        checkpoint.setdefault("reconciliations", []).append(
            {
                "invalidated_from": phase,
                "invalidated_phases": list(self.RUNTIME_PHASES[start:]),
                "reason": reason,
                "recorded_at": utc_now(),
            }
        )
        checkpoint["failure"] = None
        self._save_runtime_checkpoint(machine, checkpoint)

    def _mark_phase(
        self,
        machine: "ReleaseStateMachine",
        checkpoint: dict[str, Any],
        phase: str,
        evidence: dict[str, Any],
    ) -> None:
        completed = [str(item) for item in checkpoint.get("completed_phases", [])]
        if phase not in completed:
            completed.append(phase)
        checkpoint["completed_phases"] = completed
        checkpoint.setdefault("phase_evidence", {})[phase] = evidence
        checkpoint["last_phase"] = phase
        checkpoint["failure"] = None
        self._save_runtime_checkpoint(machine, checkpoint)

    def _record_runtime_failure(
        self,
        machine: "ReleaseStateMachine",
        checkpoint: dict[str, Any],
        *,
        phase: str,
        code: str,
        message: str,
        details: dict[str, Any],
    ) -> None:
        checkpoint["last_phase"] = phase
        checkpoint["failure"] = {
            "code": code,
            "message": message,
            "details": details,
            "recorded_at": utc_now(),
        }
        self._save_runtime_checkpoint(machine, checkpoint)

    def _env(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, str]:
        paths = self._runtime_paths(machine)
        for key, path in paths.items():
            if key == "checkpoint":
                continue
            path.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.update(
            {
                "PYTHONPYCACHEPREFIX": str(paths["pycache"]),
                "PROMPTBRANCH_PROJECT_STATE_HOME": str(paths["project_state"]),
                "PROMPTBRANCH_PROJECT_CONFIG_HOME": str(paths["project_config"]),
                "XDG_STATE_HOME": str(paths["xdg_state"]),
                "XDG_CONFIG_HOME": str(paths["xdg_config"]),
                "HOME": str(paths["home"]),
                "PYTHONPATH": str(paths["extracted"]),
                "PROMPTBRANCH_RELEASE_VALIDATION_PYTHON": str(self._python(machine)),
                "PROMPTBRANCH_RELEASE_STATE_MACHINE_ATTEMPT_ID": str(record.get("attempt_id") or ""),
                "PROMPTBRANCH_RELEASE_STATE_MACHINE_ATTEMPT_DIR": str(machine.attempt_dir),
                "PROMPTBRANCH_RELEASE_STATE_MACHINE_ARTIFACT": str(record.get("artifact", {}).get("object_path") or ""),
            }
        )
        runtime = record.get("evidence", {}).get("RUNTIME_PREPARED", {})
        service_base = str(runtime.get("candidate_service_base_url") or "")
        if not service_base:
            checkpoint_path = paths["checkpoint"]
            if checkpoint_path.is_file():
                checkpoint = _read_json(checkpoint_path)
                service_base = str(checkpoint.get("candidate_service_base_url") or "")
        if service_base:
            env["CHATGPT_SERVICE_BASE_URL"] = service_base
            env["PROMPTBRANCH_CANDIDATE_SERVICE_BASE_URL"] = service_base
        return env

    def _control_env(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, str]:
        """Use exact candidate code without redirecting persistent control-plane state."""
        paths = self._runtime_paths(machine)
        control_pycache = paths["root"] / "control-pycache"
        control_pycache.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.update(
            {
                "PYTHONPYCACHEPREFIX": str(control_pycache),
                "PYTHONPATH": str(paths["extracted"]),
                "PROMPTBRANCH_RELEASE_VALIDATION_PYTHON": str(self._python(machine)),
                "PROMPTBRANCH_RELEASE_STATE_MACHINE_ATTEMPT_ID": str(record.get("attempt_id") or ""),
                "PROMPTBRANCH_RELEASE_STATE_MACHINE_ATTEMPT_DIR": str(machine.attempt_dir),
                "PROMPTBRANCH_RELEASE_STATE_MACHINE_ARTIFACT": str(record.get("artifact", {}).get("object_path") or ""),
            }
        )
        return env

    @classmethod
    def _source_fingerprint(cls, root: Path) -> str:
        """Return the canonical shared immutable release-source fingerprint."""
        return source_fingerprint(root)

    def _runtime_source_fingerprint(
        self,
        machine: "ReleaseStateMachine",
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve runtime source identity from the authoritative runtime checkpoint.

        RUNTIME_PREPARED projects the checkpoint fingerprint for observability, but the
        persisted runtime checkpoint remains the authority. Publication fails closed if
        either side is missing or if the projection disagrees with the checkpoint.
        """
        runtime = record.get("evidence", {}).get("RUNTIME_PREPARED", {})
        runtime = runtime if isinstance(runtime, dict) else {}
        projected = str(runtime.get("source_fingerprint") or "").strip()

        checkpoint = runtime.get("runtime_checkpoint")
        checkpoint = checkpoint if isinstance(checkpoint, dict) else {}
        checkpoint_path_text = str(runtime.get("runtime_checkpoint_path") or "").strip()
        checkpoint_path = Path(checkpoint_path_text) if checkpoint_path_text else None
        if checkpoint_path is not None and checkpoint_path.is_file():
            persisted = _read_json(checkpoint_path)
            if isinstance(persisted, dict):
                checkpoint = persisted

        authoritative = str(checkpoint.get("source_fingerprint") or "").strip()
        if not authoritative or not projected:
            return {
                "ok": False,
                "status": "runtime_source_fingerprint_missing",
                "failure_code": "runtime_source_fingerprint_missing",
                "source_fingerprint": authoritative or projected,
                "checkpoint_source_fingerprint": authoritative,
                "projected_source_fingerprint": projected,
                "checkpoint_path": checkpoint_path_text,
            }
        if projected != authoritative:
            return {
                "ok": False,
                "status": "runtime_source_fingerprint_disagreement",
                "failure_code": "runtime_source_fingerprint_disagreement",
                "source_fingerprint": authoritative,
                "checkpoint_source_fingerprint": authoritative,
                "projected_source_fingerprint": projected,
                "checkpoint_path": checkpoint_path_text,
            }
        return {
            "ok": True,
            "status": "runtime_source_fingerprint_exact",
            "source_fingerprint": authoritative,
            "checkpoint_source_fingerprint": authoritative,
            "projected_source_fingerprint": projected,
            "authority": "runtime_checkpoint",
            "checkpoint_path": checkpoint_path_text,
        }

    @staticmethod
    def _http_json(url: str, *, timeout: float = 5.0) -> tuple[dict[str, Any], str | None]:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return (payload if isinstance(payload, dict) else {}, None)
        except Exception as exc:  # pragma: no cover - transport detail is environment dependent
            return {}, f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _port_is_free(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                return False
        return True

    def _choose_candidate_port(self, checkpoint: dict[str, Any], artifact_sha: str) -> int:
        persisted = int(checkpoint.get("candidate_service_port") or 0)
        if persisted:
            return persisted
        start = 18000 + (int(artifact_sha[:8], 16) % 1000)
        for offset in range(200):
            port = 18000 + ((start - 18000 + offset) % 1000)
            if self._port_is_free(port):
                return port
        raise TransitionBlocked(
            "runtime_port_allocation_failed",
            "no isolated candidate service port is available in the reserved range",
            details={"range": "18000-18999"},
        )

    @staticmethod
    def _run_logged(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        log_path: Path,
        timeout: float,
        append: bool = False,
    ) -> dict[str, Any]:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        started = time.monotonic()
        with log_path.open(mode, encoding="utf-8") as handle:
            handle.write("$ " + " ".join(command) + "\n")
            handle.flush()
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    env=env,
                    text=True,
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                )
            except OSError as exc:
                handle.write(f"{type(exc).__name__}: {exc}\n")
                return {
                    "returncode": 127,
                    "timed_out": False,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "error": f"{type(exc).__name__}: {exc}",
                    "command": command,
                    "log_path": str(log_path),
                }
            timed_out = False
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                returncode = process.wait(timeout=30)
                handle.write(f"\nPROMPTBRANCH_TIMEOUT after {timeout:.1f}s\n")
            handle.flush()
        return {
            "returncode": 124 if timed_out else returncode,
            "timed_out": timed_out,
            "duration_seconds": round(time.monotonic() - started, 3),
            "error": None,
            "command": command,
            "log_path": str(log_path),
        }

    @staticmethod
    def _run_capture(command: list[str], *, cwd: Path, env: dict[str, str], timeout: float = 60.0) -> dict[str, Any]:
        try:
            result = subprocess.run(
                command,
                cwd=str(cwd),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "returncode": 124 if isinstance(exc, subprocess.TimeoutExpired) else 127,
                "stdout": getattr(exc, "stdout", "") or "",
                "stderr": f"{type(exc).__name__}: {exc}",
                "command": command,
            }

    def _snapshot_accepted_runtime(self, *, cwd: Path, env: dict[str, str]) -> dict[str, Any]:
        ps = self._run_capture(
            ["docker", "ps", "--format", "{{.ID}}|{{.Names}}|{{.Image}}|{{.Ports}}"],
            cwd=cwd,
            env=env,
        )
        candidates: list[dict[str, str]] = []
        for line in str(ps.get("stdout") or "").splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4 and (":8000->8000" in parts[3] or "0.0.0.0:8000->8000" in parts[3]):
                candidates.append({"container_id": parts[0], "name": parts[1], "image": parts[2], "ports": parts[3]})
        health, health_error = self._http_json("http://127.0.0.1:8000/healthz")
        selected = candidates[0] if len(candidates) == 1 else {}
        image_id = None
        image_labels: dict[str, Any] = {}
        image_inspect_ok = False
        image_inspect_error = None
        image = str(selected.get("image") or "")
        if image:
            inspected = self._run_capture(
                ["docker", "image", "inspect", image, "--format", "{{json .}}"],
                cwd=cwd,
                env=env,
            )
            if inspected.get("returncode") == 0:
                try:
                    payload = json.loads(str(inspected.get("stdout") or "{}").strip() or "{}")
                except json.JSONDecodeError as exc:
                    image_inspect_error = f"JSONDecodeError: {exc}"
                else:
                    if isinstance(payload, dict):
                        image_id = payload.get("Id")
                        config = payload.get("Config") if isinstance(payload.get("Config"), dict) else {}
                        labels = config.get("Labels") if isinstance(config.get("Labels"), dict) else {}
                        image_labels = labels
                        image_inspect_ok = bool(image_id)
                    else:
                        image_inspect_error = "docker image inspect returned a non-object payload"
            else:
                image_inspect_error = str(inspected.get("stderr") or "docker image inspect failed")[-2000:]
        return {
            "present": bool(selected),
            "container": selected,
            "container_count": len(candidates),
            "health": health,
            "health_error": health_error,
            "docker_ps_returncode": ps.get("returncode"),
            "image_id": image_id,
            "image_labels": image_labels,
            "image_inspect_ok": image_inspect_ok,
            "image_inspect_error": image_inspect_error,
        }

    def _candidate_compose_context(
        self,
        machine: "ReleaseStateMachine",
        record: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        paths = self._runtime_paths(machine)
        artifact_sha = str(record["artifact"]["sha256"])
        expected_package = machine.config.version.removeprefix("v")
        project = str(checkpoint.get("candidate_compose_project") or f"pb-candidate-{expected_package.replace('.', '-')}-{artifact_sha[:12]}")
        image = str(checkpoint.get("candidate_service_image") or f"promptbranch-candidate:{expected_package}-{artifact_sha[:12]}")
        port = self._choose_candidate_port(checkpoint, artifact_sha)
        service_base = f"http://127.0.0.1:{port}"
        checkpoint.update(
            {
                "candidate_compose_project": project,
                "candidate_service_image": image,
                "candidate_service_port": port,
                "candidate_service_base_url": service_base,
                "source_fingerprint": self._source_fingerprint(paths["extracted"]),
            }
        )
        self._save_runtime_checkpoint(machine, checkpoint)
        env = self._control_env(machine, record)
        env.update(
            {
                "COMPOSE_PROJECT_NAME": project,
                "PROMPTBRANCH_SERVICE_PORT": str(port),
                "CHATGPT_SERVICE_BASE_URL": service_base,
                "PROMPTBRANCH_SERVICE_IMAGE": image,
                "PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE": "1",
                "PROMPTBRANCH_VERSION": expected_package,
                "PROMPTBRANCH_ARTIFACT_SHA256": artifact_sha,
                "PROMPTBRANCH_SOURCE_FINGERPRINT": str(checkpoint["source_fingerprint"]),
                "PROMPTBRANCH_RELEASE_ATTEMPT_ID": str(record.get("attempt_id") or ""),
                "PROMPTBRANCH_HOST_PROFILE_DIR": str(machine.config.profile_dir / "browser" / "default"),
                "PROMPTBRANCH_HOST_STATE_PROFILE_DIR": str(paths["extracted"] / ".pb_profile"),
                "PROMPTBRANCH_HOST_DEBUG_ARTIFACT_DIR": str(paths["extracted"] / "debug_artifacts"),
                "PROMPTBRANCH_PROFILE_DIR": "/app/profile",
                "BUILDKIT_PROGRESS": "plain",
            }
        )
        return {
            "project": project,
            "image": image,
            "port": port,
            "service_base": service_base,
            "env": env,
            "compose_file": paths["extracted"] / "docker-compose.chatgpt-service.yml",
        }

    def _collect_runtime_diagnostics(
        self,
        machine: "ReleaseStateMachine",
        record: dict[str, Any],
        context: dict[str, Any],
        *,
        label: str,
    ) -> dict[str, Any]:
        paths = self._runtime_paths(machine)
        diagnostic_dir = paths["diagnostics"] / label
        diagnostic_dir.mkdir(parents=True, exist_ok=True)
        cwd = paths["extracted"]
        env = context["env"]
        compose = ["docker", "compose", "-p", context["project"], "-f", str(context["compose_file"])]
        commands = {
            "compose_ps": compose + ["ps", "-a", "--format", "json"],
            "docker_ps": ["docker", "ps", "-a", "--format", "{{json .}}"],
            "image_inspect": ["docker", "image", "inspect", context["image"]],
            "container_id": compose + ["ps", "-q", "chatgpt-service"],
            "compose_logs": compose + ["logs", "--no-color", "--tail", "500", "chatgpt-service"],
        }
        captures: dict[str, Any] = {}
        for name, command in commands.items():
            result = self._run_capture(command, cwd=cwd, env=env, timeout=60)
            captures[name] = {
                "returncode": result["returncode"],
                "command": command,
                "stdout_path": str(diagnostic_dir / f"{name}.stdout.log"),
                "stderr_path": str(diagnostic_dir / f"{name}.stderr.log"),
            }
            (diagnostic_dir / f"{name}.stdout.log").write_text(str(result.get("stdout") or ""), encoding="utf-8")
            (diagnostic_dir / f"{name}.stderr.log").write_text(str(result.get("stderr") or ""), encoding="utf-8")
        candidate_health, candidate_error = self._http_json(context["service_base"] + "/healthz")
        accepted = self._snapshot_accepted_runtime(cwd=cwd, env=env)
        payload = {
            "label": label,
            "captured_at": utc_now(),
            "attempt_id": record.get("attempt_id"),
            "candidate_compose_project": context["project"],
            "candidate_service_image": context["image"],
            "candidate_service_port": context["port"],
            "candidate_service_base_url": context["service_base"],
            "candidate_health": candidate_health,
            "candidate_health_error": candidate_error,
            "accepted_runtime": accepted,
            "captures": captures,
        }
        _atomic_write_json(diagnostic_dir / "summary.json", payload)
        return {**payload, "summary_path": str(diagnostic_dir / "summary.json")}

    def _runtime_failure_result(
        self,
        machine: "ReleaseStateMachine",
        record: dict[str, Any],
        checkpoint: dict[str, Any],
        context: dict[str, Any],
        *,
        phase: str,
        code: str,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        diagnostics = self._collect_runtime_diagnostics(machine, record, context, label=f"failure-{phase}")
        details = {"phase": phase, "diagnostics": diagnostics, **(extra or {})}
        self._record_runtime_failure(machine, checkpoint, phase=phase, code=code, message=message, details=details)
        return {
            "ok": False,
            "status": code,
            "failure_code": code,
            "error": message,
            "runtime_phase": phase,
            "runtime_checkpoint_path": str(self._runtime_paths(machine)["checkpoint"]),
            "runtime_checkpoint": checkpoint,
            "diagnostics": diagnostics,
        }

    def prepare_runtime(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        paths = self._runtime_paths(machine)
        for key, path in paths.items():
            if key != "checkpoint":
                path.mkdir(parents=True, exist_ok=True)
        artifact = Path(record["artifact"]["object_path"])
        expected_package = machine.config.version.removeprefix("v")
        artifact_sha = str(record["artifact"]["sha256"])
        checkpoint = self._load_runtime_checkpoint(machine, record)
        completed_phases = set(str(item) for item in checkpoint.get("completed_phases", []))

        if "candidate_extracted" not in completed_phases:
            _safe_extract(artifact, paths["extracted"])
            extracted_profile = paths["extracted"] / ".pb_profile"
            if extracted_profile.exists() or extracted_profile.is_symlink():
                if extracted_profile.is_dir() and not extracted_profile.is_symlink():
                    shutil.rmtree(extracted_profile)
                else:
                    extracted_profile.unlink()
            extracted_profile.mkdir(parents=True, exist_ok=True)
            executable_paths = [
                paths["extracted"] / "run_chatgpt_service.sh",
                paths["extracted"] / "run_chatgpt_service_dev.sh",
                paths["extracted"] / "docker" / "run-chatgpt-service-in-container.sh",
            ]
            for executable in executable_paths:
                if executable.is_file():
                    executable.chmod(executable.stat().st_mode | 0o111)
            self._mark_phase(
                machine,
                checkpoint,
                "candidate_extracted",
                {
                    "artifact_sha256": artifact_sha,
                    "extraction_path": str(paths["extracted"]),
                    "version": (paths["extracted"] / "VERSION").read_text(encoding="utf-8").strip(),
                    "run_service_executable": (paths["extracted"] / "run_chatgpt_service.sh").is_file()
                    and os.access(paths["extracted"] / "run_chatgpt_service.sh", os.X_OK),
                    "recorded_at": utc_now(),
                },
            )
            completed_phases.add("candidate_extracted")

        context = self._candidate_compose_context(machine, record, checkpoint)
        baseline_package = machine.config.baseline_version.removeprefix("v")
        accepted_before = self._snapshot_accepted_runtime(cwd=paths["extracted"], env=context["env"])
        accepted_before_checks = _accepted_runtime_exact_checks(accepted_before, expected_version=baseline_package)
        checkpoint["accepted_runtime_before"] = accepted_before
        checkpoint["accepted_runtime_before_checks"] = accepted_before_checks
        self._save_runtime_checkpoint(machine, checkpoint)
        if not all(accepted_before_checks.values()):
            availability_checks = (
                accepted_before_checks.get("docker_ps_ok"),
                accepted_before_checks.get("exactly_one_authoritative_container"),
                accepted_before_checks.get("accepted_runtime_present"),
                accepted_before_checks.get("accepted_health_ok"),
            )
            failure_code = (
                "accepted_runtime_unavailable"
                if not all(availability_checks)
                else "accepted_runtime_baseline_mismatch"
            )
            return self._runtime_failure_result(
                machine,
                record,
                checkpoint,
                context,
                phase="accepted_runtime_precondition",
                code=failure_code,
                message="accepted/current production runtime must be a single healthy exact-baseline service before candidate runtime preparation",
                extra={
                    "expected_baseline_version": baseline_package,
                    "checks": accepted_before_checks,
                    "accepted_runtime_before": accepted_before,
                    "operator_recovery_required": True,
                },
            )

        control_env = self._control_env(machine, record)
        install_log = paths["logs"] / "runtime-install.log"
        build_log = paths["logs"] / "runtime-image-build.log"
        start_log = paths["logs"] / "runtime-container-start.log"
        candidate_python = self._python(machine)
        isolated_env = self._env(machine, record)

        probe_payload: dict[str, Any] = {}
        cli_version = ""
        install_result: dict[str, Any] = checkpoint.get("phase_evidence", {}).get("candidate_cli_installed", {})
        if "candidate_cli_installed" not in completed_phases:
            pipx_executable = shutil.which("pipx")
            if not pipx_executable:
                return self._runtime_failure_result(
                    machine,
                    record,
                    checkpoint,
                    context,
                    phase="candidate_cli_installed",
                    code="runtime_pipx_missing",
                    message="pipx executable is required to prepare the candidate runtime",
                )
            install_command = [pipx_executable, "install", "--force", str(paths["extracted"])]
            install_run = self._run_logged(
                install_command,
                cwd=paths["extracted"],
                env=control_env,
                log_path=install_log,
                timeout=900,
            )
            if install_run["returncode"] != 0:
                return self._runtime_failure_result(
                    machine,
                    record,
                    checkpoint,
                    context,
                    phase="candidate_cli_installed",
                    code="runtime_cli_install_timeout" if install_run["timed_out"] else "runtime_cli_install_failed",
                    message="candidate CLI installation failed",
                    extra={"install": install_run},
                )
            candidate_python = self._python(machine)
            probe = self._run_capture(
                [
                    str(candidate_python),
                    "-c",
                    "import json,sys,pytest,promptbranch_version; print(json.dumps({'python':sys.executable,'python_prefix':sys.prefix,'pytest_version':pytest.__version__,'pytest_module':pytest.__file__,'package_version':promptbranch_version.PACKAGE_VERSION}))",
                ],
                cwd=paths["extracted"],
                env=isolated_env,
            )
            probe_payload = _last_json_object(str(probe.get("stdout") or "")) or {}
            cli_command = [str(candidate_python), str(paths["extracted"] / "promptbranch_cli.py"), "--version"]
            cli_probe = self._run_capture(cli_command, cwd=paths["extracted"], env=control_env)
            cli_stdout = str(cli_probe.get("stdout") or "")
            cli_version = expected_package if expected_package in cli_stdout else cli_stdout.strip()
            checks = {
                "install_returncode_zero": install_run["returncode"] == 0,
                "python_probe_returncode_zero": probe["returncode"] == 0,
                "python_executable_exact": str(probe_payload.get("python") or "") == str(candidate_python),
                "package_version_exact": str(probe_payload.get("package_version") or "") == expected_package,
                "pytest_version_exact": str(probe_payload.get("pytest_version") or "") == REQUIRED_PYTEST_VERSION,
                "cli_returncode_zero": cli_probe["returncode"] == 0,
                "cli_version_exact": cli_version == expected_package,
            }
            if not all(checks.values()):
                return self._runtime_failure_result(
                    machine,
                    record,
                    checkpoint,
                    context,
                    phase="candidate_cli_installed",
                    code="runtime_candidate_identity_mismatch",
                    message="candidate CLI/Python identity verification failed",
                    extra={"checks": checks, "probe": probe, "probe_payload": probe_payload, "cli_probe": cli_probe},
                )
            install_result = {
                "candidate_python": str(candidate_python),
                "candidate_pytest_version": probe_payload.get("pytest_version"),
                "candidate_pytest_module": probe_payload.get("pytest_module"),
                "candidate_package_version": probe_payload.get("package_version"),
                "candidate_cli_version": cli_version,
                "install": install_run,
                "checks": checks,
                "recorded_at": utc_now(),
            }
            self._mark_phase(machine, checkpoint, "candidate_cli_installed", install_result)
            completed_phases.add("candidate_cli_installed")
        else:
            candidate_python = Path(str(install_result.get("candidate_python") or self._python(machine)))
            probe_payload = {
                "pytest_version": install_result.get("candidate_pytest_version"),
                "pytest_module": install_result.get("candidate_pytest_module"),
                "package_version": install_result.get("candidate_package_version"),
                "python": str(candidate_python),
            }
            cli_version = str(install_result.get("candidate_cli_version") or "")

        compose = ["docker", "compose", "-p", context["project"], "-f", str(context["compose_file"])]
        if "candidate_image_built" in completed_phases:
            image_recheck = self._run_capture(
                ["docker", "image", "inspect", context["image"], "--format", "{{json .Config.Labels}}"],
                cwd=paths["extracted"],
                env=context["env"],
            )
            try:
                image_recheck_labels = json.loads(str(image_recheck.get("stdout") or "{}").strip() or "{}")
            except json.JSONDecodeError:
                image_recheck_labels = {}
            image_recheck_ok = (
                image_recheck.get("returncode") == 0
                and str(image_recheck_labels.get("promptbranch.version") or "") == expected_package
                and str(image_recheck_labels.get("promptbranch.artifact_sha256") or "") == artifact_sha
                and str(image_recheck_labels.get("promptbranch.release_attempt_id") or "") == str(record.get("attempt_id") or "")
            )
            if not image_recheck_ok:
                self._clear_runtime_phases_from(
                    machine, checkpoint, "candidate_image_built", reason="candidate image missing or identity labels drifted"
                )
                completed_phases = set(str(item) for item in checkpoint.get("completed_phases", []))
        if "candidate_image_built" not in completed_phases:
            build_command = compose + ["build", "chatgpt-service"]
            build = self._run_logged(
                build_command,
                cwd=paths["extracted"],
                env=context["env"],
                log_path=build_log,
                timeout=1800,
            )
            if build["returncode"] != 0:
                return self._runtime_failure_result(
                    machine,
                    record,
                    checkpoint,
                    context,
                    phase="candidate_image_built",
                    code="runtime_image_build_timeout" if build["timed_out"] else "runtime_image_build_failed",
                    message="isolated candidate image build failed",
                    extra={"build": build},
                )
            image_probe = self._run_capture(
                ["docker", "image", "inspect", context["image"], "--format", "{{json .Config.Labels}}"],
                cwd=paths["extracted"],
                env=context["env"],
            )
            try:
                image_labels = json.loads(str(image_probe.get("stdout") or "{}").strip() or "{}")
            except json.JSONDecodeError:
                image_labels = {}
            image_checks = {
                "image_inspect_ok": image_probe["returncode"] == 0,
                "version_label_exact": str(image_labels.get("promptbranch.version") or "") == expected_package,
                "artifact_sha_label_exact": str(image_labels.get("promptbranch.artifact_sha256") or "") == artifact_sha,
                "source_fingerprint_label_exact": str(image_labels.get("promptbranch.source_fingerprint") or "") == str(checkpoint.get("source_fingerprint") or ""),
                "attempt_id_label_exact": str(image_labels.get("promptbranch.release_attempt_id") or "") == str(record.get("attempt_id") or ""),
            }
            if not all(image_checks.values()):
                return self._runtime_failure_result(
                    machine,
                    record,
                    checkpoint,
                    context,
                    phase="candidate_image_built",
                    code="runtime_image_identity_mismatch",
                    message="candidate image labels do not match the release attempt",
                    extra={"build": build, "image_probe": image_probe, "image_labels": image_labels, "checks": image_checks},
                )
            self._mark_phase(
                machine,
                checkpoint,
                "candidate_image_built",
                {"build": build, "image_labels": image_labels, "checks": image_checks, "recorded_at": utc_now()},
            )
            completed_phases.add("candidate_image_built")

        if "candidate_container_started" in completed_phases:
            existing_container = self._run_capture(
                compose + ["ps", "-q", "chatgpt-service"],
                cwd=paths["extracted"],
                env=context["env"],
            )
            existing_container_id = str(existing_container.get("stdout") or "").strip()
            existing_health, _ = self._http_json(context["service_base"] + "/healthz")
            if not existing_container_id or str(existing_health.get("version") or "") != expected_package:
                self._clear_runtime_phases_from(
                    machine, checkpoint, "candidate_container_started", reason="candidate container or health projection is no longer available"
                )
                completed_phases = set(str(item) for item in checkpoint.get("completed_phases", []))
        if "candidate_container_started" not in completed_phases:
            if not self._port_is_free(context["port"]):
                existing_health, _ = self._http_json(context["service_base"] + "/healthz")
                if str(existing_health.get("version") or "") != expected_package:
                    return self._runtime_failure_result(
                        machine,
                        record,
                        checkpoint,
                        context,
                        phase="candidate_container_started",
                        code="runtime_port_conflict",
                        message="isolated candidate port is already owned by another runtime",
                        extra={"port": context["port"], "existing_health": existing_health},
                    )
            start_command = compose + ["up", "-d", "--force-recreate", "--no-build", "chatgpt-service"]
            start = self._run_logged(
                start_command,
                cwd=paths["extracted"],
                env=context["env"],
                log_path=start_log,
                timeout=300,
            )
            if start["returncode"] != 0:
                return self._runtime_failure_result(
                    machine,
                    record,
                    checkpoint,
                    context,
                    phase="candidate_container_started",
                    code="runtime_container_start_timeout" if start["timed_out"] else "runtime_container_start_failed",
                    message="isolated candidate container start failed",
                    extra={"start": start},
                )
            container_probe = self._run_capture(compose + ["ps", "-q", "chatgpt-service"], cwd=paths["extracted"], env=context["env"])
            container_id = str(container_probe.get("stdout") or "").strip()
            if container_probe["returncode"] != 0 or not container_id:
                return self._runtime_failure_result(
                    machine,
                    record,
                    checkpoint,
                    context,
                    phase="candidate_container_started",
                    code="runtime_container_missing",
                    message="candidate Compose project did not expose a container after start",
                    extra={"start": start, "container_probe": container_probe},
                )
            self._mark_phase(
                machine,
                checkpoint,
                "candidate_container_started",
                {"start": start, "container_id": container_id, "recorded_at": utc_now()},
            )
            completed_phases.add("candidate_container_started")

        health_payload: dict[str, Any] = {}
        health_error: str | None = None
        if "candidate_health_verified" not in completed_phases:
            deadline = time.monotonic() + 240.0
            attempts: list[dict[str, Any]] = []
            while time.monotonic() < deadline:
                health_payload, health_error = self._http_json(context["service_base"] + "/healthz")
                attempts.append(
                    {
                        "at": utc_now(),
                        "version": health_payload.get("version"),
                        "ok": health_payload.get("ok"),
                        "error": health_error,
                    }
                )
                if health_payload.get("ok") is True and str(health_payload.get("version") or "") == expected_package:
                    break
                time.sleep(2.0)
            if health_payload.get("ok") is not True or str(health_payload.get("version") or "") != expected_package:
                return self._runtime_failure_result(
                    machine,
                    record,
                    checkpoint,
                    context,
                    phase="candidate_health_verified",
                    code="runtime_health_timeout",
                    message="candidate service did not become healthy with the exact target version",
                    extra={"health_attempts": attempts, "last_health": health_payload, "last_error": health_error},
                )
            self._mark_phase(
                machine,
                checkpoint,
                "candidate_health_verified",
                {"health": health_payload, "attempts": attempts, "recorded_at": utc_now()},
            )
            completed_phases.add("candidate_health_verified")
        else:
            health_payload = checkpoint.get("phase_evidence", {}).get("candidate_health_verified", {}).get("health", {})

        identity_evidence = checkpoint.get("phase_evidence", {}).get("candidate_identity_verified", {})
        if "candidate_identity_verified" not in completed_phases:
            image_probe = self._run_capture(
                ["docker", "image", "inspect", context["image"], "--format", "{{json .Config.Labels}}"],
                cwd=paths["extracted"],
                env=context["env"],
            )
            try:
                labels = json.loads(str(image_probe.get("stdout") or "{}").strip() or "{}")
            except json.JSONDecodeError:
                labels = {}
            container_probe = self._run_capture(compose + ["ps", "-q", "chatgpt-service"], cwd=paths["extracted"], env=context["env"])
            container_id = str(container_probe.get("stdout") or "").strip()
            container_inspect = self._run_capture(
                ["docker", "inspect", container_id, "--format", "{{json .Config.Labels}}"],
                cwd=paths["extracted"],
                env=context["env"],
            ) if container_id else {"returncode": 1, "stdout": "", "stderr": "container missing", "command": []}
            try:
                container_labels = json.loads(str(container_inspect.get("stdout") or "{}").strip() or "{}")
            except json.JSONDecodeError:
                container_labels = {}
            accepted_after = self._snapshot_accepted_runtime(cwd=paths["extracted"], env=context["env"])
            preservation_checks = _accepted_runtime_preservation_checks(
                accepted_before,
                accepted_after,
                expected_version=baseline_package,
            )
            identity_checks = {
                "candidate_health_version_exact": str(health_payload.get("version") or "") == expected_package,
                "candidate_health_ok": health_payload.get("ok") is True,
                "candidate_container_present": bool(container_id),
                "image_version_label_exact": str(labels.get("promptbranch.version") or "") == expected_package,
                "image_artifact_sha_label_exact": str(labels.get("promptbranch.artifact_sha256") or "") == artifact_sha,
                "image_source_fingerprint_label_exact": str(labels.get("promptbranch.source_fingerprint") or "") == str(checkpoint.get("source_fingerprint") or ""),
                "image_attempt_id_label_exact": str(labels.get("promptbranch.release_attempt_id") or "") == str(record.get("attempt_id") or ""),
                "container_compose_project_exact": str(container_labels.get("com.docker.compose.project") or "") == context["project"],
                **preservation_checks,
                "candidate_port_isolated": context["port"] != 8000,
            }
            if not all(identity_checks.values()):
                return self._runtime_failure_result(
                    machine,
                    record,
                    checkpoint,
                    context,
                    phase="candidate_identity_verified",
                    code="runtime_identity_mismatch",
                    message="candidate runtime identity or accepted-runtime isolation check failed",
                    extra={
                        "checks": identity_checks,
                        "image_labels": labels,
                        "container_labels": container_labels,
                        "accepted_runtime_before": accepted_before,
                        "accepted_runtime_after": accepted_after,
                    },
                )
            identity_evidence = {
                "checks": identity_checks,
                "image_labels": labels,
                "container_labels": container_labels,
                "container_id": container_id,
                "accepted_runtime_before": accepted_before,
                "accepted_runtime_after": accepted_after,
                "recorded_at": utc_now(),
            }
            self._mark_phase(machine, checkpoint, "candidate_identity_verified", identity_evidence)
            completed_phases.add("candidate_identity_verified")

        checkpoint["status"] = "runtime_prepared"
        checkpoint["failure"] = None
        self._save_runtime_checkpoint(machine, checkpoint)
        diagnostics = self._collect_runtime_diagnostics(machine, record, context, label="runtime-prepared")
        isolated_environment = {
            "PYTHONPYCACHEPREFIX": str(paths["pycache"]),
            "PROMPTBRANCH_PROJECT_STATE_HOME": str(paths["project_state"]),
            "PROMPTBRANCH_PROJECT_CONFIG_HOME": str(paths["project_config"]),
            "XDG_STATE_HOME": str(paths["xdg_state"]),
            "XDG_CONFIG_HOME": str(paths["xdg_config"]),
            "HOME": str(paths["home"]),
        }
        checks = {
            "all_runtime_phases_complete": all(phase in completed_phases for phase in self.RUNTIME_PHASES),
            "candidate_python_explicit": bool(candidate_python),
            "candidate_package_version_exact": str(probe_payload.get("package_version") or install_result.get("candidate_package_version") or "") == expected_package,
            "candidate_pytest_version_exact": str(probe_payload.get("pytest_version") or install_result.get("candidate_pytest_version") or "") == REQUIRED_PYTEST_VERSION,
            "candidate_cli_version_exact": cli_version == expected_package,
            "candidate_service_version_exact": str(health_payload.get("version") or "") == expected_package,
            "candidate_service_healthy": health_payload.get("ok") is True,
            "candidate_service_port_isolated": context["port"] != 8000,
            "candidate_compose_project_isolated": context["project"] != "chatgpt_claudecode_workflow",
            "accepted_runtime_before_exact": bool(identity_evidence.get("checks", {}).get("accepted_runtime_before_exact")),
            "accepted_runtime_after_exact": bool(identity_evidence.get("checks", {}).get("accepted_runtime_after_exact")),
            "accepted_runtime_unchanged": bool(identity_evidence.get("checks", {}).get("accepted_runtime_unchanged")),
        }
        runtime_ok = all(checks.values())
        result = {
            "ok": runtime_ok,
            "status": "runtime_prepared" if runtime_ok else "runtime_identity_mismatch",
            "candidate_python": str(candidate_python),
            "candidate_pytest_version": probe_payload.get("pytest_version") or install_result.get("candidate_pytest_version"),
            "required_pytest_version": REQUIRED_PYTEST_VERSION,
            "candidate_pytest_module": probe_payload.get("pytest_module") or install_result.get("candidate_pytest_module"),
            "candidate_package_version": probe_payload.get("package_version") or install_result.get("candidate_package_version"),
            "candidate_cli_version": cli_version,
            "service_version": str(health_payload.get("version") or ""),
            "service_health": health_payload,
            "service_error": health_error,
            "candidate_service_base_url": context["service_base"],
            "candidate_service_port": context["port"],
            "candidate_compose_project": context["project"],
            "candidate_service_image": context["image"],
            "candidate_container_id": identity_evidence.get("container_id"),
            "accepted_runtime_before": identity_evidence.get("accepted_runtime_before", accepted_before),
            "accepted_runtime_after": identity_evidence.get("accepted_runtime_after"),
            "extraction_path": str(paths["extracted"]),
            "isolated_environment": isolated_environment,
            "runtime_phases": list(self.RUNTIME_PHASES),
            "completed_runtime_phases": list(checkpoint.get("completed_phases", [])),
            "runtime_checkpoint_path": str(paths["checkpoint"]),
            "runtime_checkpoint": checkpoint,
            "source_fingerprint": str(checkpoint.get("source_fingerprint") or ""),
            "diagnostics": diagnostics,
            "checks": checks,
        }
        if not runtime_ok:
            result["failure_code"] = "runtime_identity_mismatch"
        return result

    def run_tests(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        paths = self._runtime_paths(machine)
        candidate_python = self._python(machine)
        env = self._env(machine, record)
        runtime_evidence = record.get("evidence", {}).get("RUNTIME_PREPARED", {})
        pytest_version = runtime_evidence.get("candidate_pytest_version")
        if pytest_version:
            env["PROMPTBRANCH_RELEASE_VALIDATION_PYTEST_VERSION"] = str(pytest_version)
        service_base = str(runtime_evidence.get("candidate_service_base_url") or "")
        if service_base:
            env["CHATGPT_SERVICE_BASE_URL"] = service_base
            env["PROMPTBRANCH_CANDIDATE_SERVICE_BASE_URL"] = service_base
        env.update(
            {
                "PROMPTBRANCH_RUN_DOCKER_INTEGRATION": "1",
                "PROMPTBRANCH_CANDIDATE_COMPOSE_PROJECT": str(runtime_evidence.get("candidate_compose_project") or ""),
                "PROMPTBRANCH_CANDIDATE_SERVICE_IMAGE": str(runtime_evidence.get("candidate_service_image") or ""),
                "PROMPTBRANCH_CANDIDATE_SERVICE_PORT": str(runtime_evidence.get("candidate_service_port") or ""),
                "PROMPTBRANCH_CANDIDATE_CONTAINER_ID": str(runtime_evidence.get("candidate_container_id") or ""),
                "PROMPTBRANCH_ACCEPTED_RUNTIME_BEFORE_JSON": json.dumps(runtime_evidence.get("accepted_runtime_before") or {}, sort_keys=True),
            }
        )
        current_probe=self.current_status(machine,record); current_result=current_probe.get("result") if isinstance(current_probe,dict) and isinstance(current_probe.get("result"),dict) else {}; repos=current_result.get("repos") if isinstance(current_result.get("repos"),dict) else {}; repo_current=repos.get(machine.repo_id) if isinstance(repos.get(machine.repo_id),dict) else {}; baseline_record=repo_current.get("registry_current") if isinstance(repo_current.get("registry_current"),dict) else {}
        baseline_origin_url=str(baseline_record.get("origin_conversation_url") or "").strip(); baseline_origin_id=str(baseline_record.get("origin_conversation_id") or "").strip(); baseline_exact=str(baseline_record.get("version") or "")==machine.config.baseline_version; origin_exact=bool(baseline_origin_url and baseline_origin_id and _conversation_id_from_url(baseline_origin_url)==baseline_origin_id)
        if current_probe.get("ok") is not True or not baseline_exact or not origin_exact:
            return {"ok":False,"status":"baseline_artifact_conversation_provenance_missing","failure_code":"baseline_artifact_conversation_provenance_missing","artifact_sha256":record.get("artifact",{}).get("sha256"),"baseline_version":machine.config.baseline_version,"baseline_registry_record":baseline_record,"checks":{"current_probe_ok":current_probe.get("ok") is True,"baseline_artifact_exact":baseline_exact,"baseline_conversation_provenance_exact":origin_exact},"operator_action":f"pb artifact bind-conversation --repo {machine.repo_id} --version {machine.config.baseline_version} --conversation-url <chat-url> --json","test_subprocess_executed":False}

        active_attempt = record.get("active_test_attempt") if isinstance(record.get("active_test_attempt"), dict) else {}
        retry_number = int(active_attempt.get("retry_number") or 1)
        test_run_id = str(active_attempt.get("test_run_id") or f"candidate-test-r{retry_number:04d}")
        project_name = str(active_attempt.get("project_name") or f"itest-pb-sm-{record['artifact']['sha256'][:12]}-r{retry_number:04d}")[:50]
        command = [
            str(candidate_python),
            str(paths["extracted"] / "promptbranch_cli.py"),
            "--profile-dir",
            str(machine.config.profile_dir),
            "test",
            machine.config.profile,
            "--project-name",
            project_name,
            "--keep-project",
            "--fail-fast",
            "--ask-conversation-url",
            baseline_origin_url,
            "--json",
        ]
        started = utc_now()
        stdout_path = paths["logs"] / f"candidate-test.r{retry_number:04d}.stdout.log"
        stderr_path = paths["logs"] / f"candidate-test.r{retry_number:04d}.stderr.log"
        try:
            completed = subprocess.run(
                command,
                cwd=str(paths["extracted"]),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=machine.config.test_timeout,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            stdout = str(exc.stdout or "")
            stderr = str(exc.stderr or "") + f"\nPROMPTBRANCH_TIMEOUT after {machine.config.test_timeout:.1f}s\n"
            returncode = 124
            timed_out = True
        finished = utc_now()
        paths["logs"].mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        stdout_bytes = stdout.encode("utf-8")
        stderr_bytes = stderr.encode("utf-8")
        selection = _select_candidate_test_report(
            stdout,
            profile=machine.config.profile,
            version=machine.config.version,
        )
        payload = selection.get("report") if isinstance(selection.get("report"), dict) else None
        base_result = {
            "started_at": started,
            "finished_at": finished,
            "profile": machine.config.profile,
            "artifact_sha256": record["artifact"]["sha256"],
            "candidate_python": str(candidate_python),
            "candidate_pytest_version": pytest_version,
            "baseline_conversation_url": baseline_origin_url,
            "baseline_conversation_id": baseline_origin_id,
            "baseline_conversation_routing_source": "baseline_artifact_provenance",
            "candidate_service_base_url": service_base,
            "candidate_compose_project": runtime_evidence.get("candidate_compose_project"),
            "candidate_service_port": runtime_evidence.get("candidate_service_port"),
            "test_run_id": test_run_id,
            "retry_number": retry_number,
            "project_name": project_name,
            "command": command,
            "returncode": returncode,
            "timeout_seconds": machine.config.test_timeout,
            "timed_out": timed_out,
            "stdout_log_path": str(stdout_path),
            "stderr_log_path": str(stderr_path),
            "stdout_sha256": _sha256_bytes(stdout_bytes),
            "stderr_sha256": _sha256_bytes(stderr_bytes),
            "report_selection": {key: value for key, value in selection.items() if key != "report"},
            "report_selected": selection.get("ok") is True,
        }
        if selection.get("ok") is not True or payload is None:
            return {
                **base_result,
                "ok": False,
                "status": str(selection.get("status") or "candidate_test_report_invalid"),
                "failure_code": str(selection.get("failure_code") or "candidate_test_report_invalid"),
                "result": payload,
                "report_schema": None,
                "report_schema_version": None,
                "report_sha256": None,
                "report_path": None,
                "completed": None,
                "passed": None,
                "failed": None,
                "skipped": None,
                "failed_group": None,
                "failed_groups": [],
                "failed_steps": [],
            }

        report_bytes = _canonical_json_bytes(payload)
        report_path = paths["logs"] / f"candidate-test.r{retry_number:04d}.report.json"
        report_path.write_bytes(report_bytes)
        counts = _test_report_counts(payload, profile=machine.config.profile)
        failed = counts.get("failed")
        skipped = counts.get("skipped")
        counts_valid = isinstance(failed, int) and isinstance(skipped, int)
        ok = bool(
            returncode == 0
            and not timed_out
            and payload.get("ok") is True
            and counts_valid
            and failed == 0
            and skipped == 0
        )
        status = "candidate_test_passed" if ok else ("candidate_test_timeout" if timed_out else "candidate_test_failed")
        browser_payload = payload.get("browser") if isinstance(payload.get("browser"), dict) else {}
        result = {
            **base_result,
            "ok": ok,
            "status": status,
            "result": payload,
            "project_url": browser_payload.get("project_url"),
            "report_schema": payload.get("schema"),
            "report_schema_version": payload.get("schema_version"),
            "report_sha256": _sha256_bytes(report_bytes),
            "report_path": str(report_path),
            **counts,
        }
        if not ok:
            result["failure_code"] = "candidate_test_failed"
        return result

    def accept_candidate(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        runtime = record.get("evidence", {}).get("RUNTIME_PREPARED", {})
        extracted = Path(str(runtime.get("extraction_path") or ""))
        candidate_python = Path(str(runtime.get("candidate_python") or self._python(machine)))
        command = [
            str(candidate_python),
            str(extracted / "promptbranch_cli.py"),
            "--profile-dir",
            str(machine.config.profile_dir),
            "artifact",
            "accept-candidate",
            "--version",
            machine.config.version,
            "--adopt-if-green",
            "--repo-path",
            str(machine.config.repo_root),
            "--json",
        ]
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=str(machine.config.repo_root),
                env=self._control_env(machine, record),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,
                check=False,
            )
            returncode = int(completed.returncode)
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = 124
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")

        selection = _select_accept_candidate_result(stdout)
        payload = selection.get("result") if isinstance(selection.get("result"), dict) else {}
        ok = bool(
            not timed_out
            and returncode == 0
            and selection.get("ok") is True
            and payload.get("ok") is True
            and payload.get("status") == "accepted_candidate"
        )
        status = (
            "candidate_acceptance_timeout"
            if timed_out
            else (str(payload.get("status") or "") if selection.get("ok") is True else str(selection.get("status") or "candidate_acceptance_failed"))
        )
        result = {
            "ok": ok,
            "status": status or "candidate_acceptance_failed",
            "returncode": returncode,
            "timed_out": timed_out,
            "command": command,
            "result": payload,
            "result_selection": {key: value for key, value in selection.items() if key != "result"},
            "stdout_sha256": _sha256_bytes(stdout.encode("utf-8", errors="replace")),
            "stderr_sha256": _sha256_bytes(stderr.encode("utf-8", errors="replace")),
            "stderr_tail": stderr[-4000:],
        }
        if not ok:
            if timed_out:
                result["failure_code"] = "candidate_acceptance_timeout"
            elif selection.get("ok") is not True:
                result["failure_code"] = str(selection.get("failure_code") or "candidate_acceptance_report_invalid")
            else:
                result["failure_code"] = "candidate_acceptance_failed"
        return result

    def current_status(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        runtime = record.get("evidence", {}).get("RUNTIME_PREPARED", {})
        extracted = Path(str(runtime.get("extraction_path") or ""))
        candidate_python = Path(str(runtime.get("candidate_python") or self._python(machine)))
        command = [
            str(candidate_python),
            str(extracted / "promptbranch_cli.py"),
            "--profile-dir",
            str(machine.config.profile_dir),
            "artifact",
            "current",
            "--repo",
            machine.repo_id,
            "--json",
        ]
        completed = subprocess.run(
            command,
            cwd=str(machine.config.repo_root),
            env=self._control_env(machine, record),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        selection = _select_current_status_result(stdout)
        payload = selection.get("result") if isinstance(selection.get("result"), dict) else {}
        ok = completed.returncode == 0 and selection.get("ok") is True and payload.get("ok") is True
        result = {
            "ok": ok,
            "status": str(payload.get("status") or selection.get("status") or "artifact_current_failed"),
            "returncode": completed.returncode,
            "command": command,
            "result": payload,
            "result_selection": {key: value for key, value in selection.items() if key != "result"},
            "stdout_sha256": _sha256_bytes(stdout.encode("utf-8", errors="replace")),
            "stderr_sha256": _sha256_bytes(stderr.encode("utf-8", errors="replace")),
            "stderr_tail": stderr[-4000:],
        }
        if not ok:
            result["failure_code"] = str(selection.get("failure_code") or "artifact_current_failed")
        return result


    def authoritative_runtime_status(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        runtime = self._snapshot_accepted_runtime(cwd=machine.config.repo_root, env=self._control_env(machine, record))
        container = runtime.get("container") if isinstance(runtime.get("container"), dict) else {}
        image = str(container.get("image") or "")
        labels: dict[str, Any] = {}
        image_id = None
        inspect_error = None
        if image:
            inspected = self._run_capture(
                ["docker", "image", "inspect", image, "--format", "{{json .}}"],
                cwd=machine.config.repo_root,
                env=self._control_env(machine, record),
                timeout=60,
            )
            if inspected.get("returncode") == 0:
                try:
                    image_payload = json.loads(str(inspected.get("stdout") or "{}"))
                    if isinstance(image_payload, dict):
                        image_id = image_payload.get("Id")
                        config = image_payload.get("Config") if isinstance(image_payload.get("Config"), dict) else {}
                        labels = config.get("Labels") if isinstance(config.get("Labels"), dict) else {}
                except json.JSONDecodeError as exc:
                    inspect_error = f"JSONDecodeError: {exc}"
            else:
                inspect_error = str(inspected.get("stderr") or "docker image inspect failed")[-2000:]
        expected_version = machine.config.version.removeprefix("v")
        expected_sha = str(record.get("artifact", {}).get("sha256") or "")
        expected_attempt = str(record.get("attempt_id") or "")
        checks = {
            "exactly_one_authoritative_container": runtime.get("container_count") == 1,
            "health_ok": isinstance(runtime.get("health"), dict) and runtime["health"].get("ok") is True,
            "health_version_exact": isinstance(runtime.get("health"), dict) and str(runtime["health"].get("version") or "") == expected_version,
            "image_version_label_exact": str(labels.get("promptbranch.version") or "") == expected_version,
            "image_artifact_sha_label_exact": str(labels.get("promptbranch.artifact_sha256") or "") == expected_sha,
            "image_attempt_id_label_exact": str(labels.get("promptbranch.release_attempt_id") or "") == expected_attempt,
        }
        ok = all(checks.values())
        return {
            "ok": ok,
            "status": "authoritative_runtime_exact" if ok else "authoritative_runtime_mismatch",
            "runtime": runtime,
            "image": image,
            "image_id": image_id,
            "image_labels": labels,
            "image_inspect_error": inspect_error,
            "checks": checks,
        }

    def _production_context(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        runtime = record.get("evidence", {}).get("RUNTIME_PREPARED", {})
        extracted = Path(str(runtime.get("extraction_path") or self._runtime_paths(machine)["extracted"]))
        expected_version = machine.config.version.removeprefix("v")
        artifact_sha = str(record.get("artifact", {}).get("sha256") or "")
        checkpoint_path = self._runtime_paths(machine)["checkpoint"]
        checkpoint = _read_json(checkpoint_path) if checkpoint_path.is_file() else {}
        source_fingerprint = str(checkpoint.get("source_fingerprint") or self._source_fingerprint(extracted))
        candidate_image = str(runtime.get("candidate_service_image") or checkpoint.get("candidate_service_image") or "")
        env = self._control_env(machine, record)
        env.update(
            {
                "COMPOSE_PROJECT_NAME": "chatgpt_claudecode_workflow",
                "PROMPTBRANCH_SERVICE_PORT": "8000",
                "CHATGPT_SERVICE_BASE_URL": "http://127.0.0.1:8000",
                "PROMPTBRANCH_SERVICE_IMAGE": f"promptbranch-service:{expected_version}",
                "PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE": "1",
                "PROMPTBRANCH_VERSION": expected_version,
                "PROMPTBRANCH_ARTIFACT_SHA256": artifact_sha,
                "PROMPTBRANCH_SOURCE_FINGERPRINT": source_fingerprint,
                "PROMPTBRANCH_RELEASE_ATTEMPT_ID": str(record.get("attempt_id") or ""),
                "PROMPTBRANCH_HOST_PROFILE_DIR": str(machine.config.profile_dir / "browser" / "default"),
                "PROMPTBRANCH_HOST_STATE_PROFILE_DIR": str(machine.config.profile_dir),
                "PROMPTBRANCH_HOST_DEBUG_ARTIFACT_DIR": str(machine.config.repo_root / "debug_artifacts"),
                "PROMPTBRANCH_PROFILE_DIR": "/app/profile",
                "PROMPTBRANCH_DOCKER_UID": str(os.getuid()),
                "PROMPTBRANCH_DOCKER_GID": str(os.getgid()),
            }
        )
        return {
            "project": "chatgpt_claudecode_workflow",
            "image": f"promptbranch-service:{expected_version}",
            "candidate_image": candidate_image,
            "compose_file": extracted / "docker-compose.chatgpt-service.yml",
            "cwd": extracted,
            "env": env,
            "source_fingerprint": source_fingerprint,
        }

    def _wait_authoritative_health(self, expected_version: str, *, timeout: float = 120.0) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        attempts: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            health, error = self._http_json("http://127.0.0.1:8000/healthz")
            attempts.append({"at": utc_now(), "ok": health.get("ok") if health else None, "version": health.get("version") if health else None, "error": error})
            if health.get("ok") is True and str(health.get("version") or "") == expected_version:
                return {"ok": True, "health": health, "attempts": attempts}
            time.sleep(2)
        return {"ok": False, "health": {}, "attempts": attempts}

    def _restore_authoritative_runtime(
        self,
        machine: "ReleaseStateMachine",
        record: dict[str, Any],
        context: dict[str, Any],
        previous: dict[str, Any],
    ) -> dict[str, Any]:
        container = previous.get("container") if isinstance(previous.get("container"), dict) else {}
        previous_image = str(container.get("image") or "")
        previous_health = previous.get("health") if isinstance(previous.get("health"), dict) else {}
        previous_version = str(previous_health.get("version") or "")
        if not previous_image:
            return {"ok": False, "status": "authoritative_runtime_rollback_unavailable", "reason": "previous image is unknown"}
        rollback_env = dict(context["env"])
        rollback_env["PROMPTBRANCH_SERVICE_IMAGE"] = previous_image
        compose = ["docker", "compose", "-p", context["project"], "-f", str(context["compose_file"])]
        log_path = self._runtime_paths(machine)["logs"] / "production-rollback.log"
        started = self._run_logged(
            compose + ["up", "-d", "--force-recreate", "--no-build", "chatgpt-service"],
            cwd=context["cwd"],
            env=rollback_env,
            log_path=log_path,
            timeout=300,
        )
        health = self._wait_authoritative_health(previous_version, timeout=120) if started.get("returncode") == 0 and previous_version else {"ok": False, "health": {}, "attempts": []}
        return {
            "ok": started.get("returncode") == 0 and health.get("ok") is True,
            "status": "authoritative_runtime_rolled_back" if started.get("returncode") == 0 and health.get("ok") is True else "authoritative_runtime_rollback_failed",
            "previous_image": previous_image,
            "previous_version": previous_version,
            "start": started,
            "health": health,
        }

    def promote_authoritative_runtime(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        context = self._production_context(machine, record)
        candidate_image = str(context.get("candidate_image") or "")
        if not candidate_image:
            return {
                "ok": False,
                "status": "authoritative_runtime_candidate_image_missing",
                "failure_code": "authoritative_runtime_candidate_image_missing",
                "error": "candidate image identity is missing from runtime evidence",
            }
        candidate_inspect = self._run_capture(
            ["docker", "image", "inspect", candidate_image, "--format", "{{.Id}}"],
            cwd=context["cwd"],
            env=context["env"],
            timeout=60,
        )
        if candidate_inspect.get("returncode") != 0:
            return {
                "ok": False,
                "status": "authoritative_runtime_candidate_image_missing",
                "failure_code": "authoritative_runtime_candidate_image_missing",
                "error": "tested candidate image is not available for promotion",
                "candidate_image": candidate_image,
            }
        candidate_image_id = str(candidate_inspect.get("stdout") or "").strip()
        if not candidate_image_id:
            return {
                "ok": False,
                "status": "authoritative_runtime_candidate_image_identity_missing",
                "failure_code": "authoritative_runtime_candidate_image_identity_missing",
                "error": "tested candidate image did not expose an immutable Docker image id",
                "candidate_image": candidate_image,
            }

        already = self.authoritative_runtime_status(machine, record)
        if already.get("ok") is True:
            production_image_id = str(already.get("image_id") or "").strip()
            if not production_image_id:
                production_inspect = self._run_capture(
                    ["docker", "image", "inspect", context["image"], "--format", "{{.Id}}"],
                    cwd=context["cwd"],
                    env=context["env"],
                    timeout=60,
                )
                production_image_id = str(production_inspect.get("stdout") or "").strip()
            if production_image_id != candidate_image_id:
                return {
                    "ok": False,
                    "status": "authoritative_runtime_image_identity_mismatch",
                    "failure_code": "authoritative_runtime_image_identity_mismatch",
                    "error": "authoritative runtime is healthy at the target version but is not the exact tested candidate image",
                    "candidate_image": candidate_image,
                    "candidate_image_id": candidate_image_id,
                    "production_image": context["image"],
                    "production_image_id": production_image_id,
                    "authoritative_runtime": already,
                }
            return {
                "ok": True,
                "status": "authoritative_runtime_already_promoted",
                "recovered": True,
                "promotion_performed": False,
                "candidate_image": candidate_image,
                "candidate_image_id": candidate_image_id,
                "production_image": context["image"],
                "production_image_id": production_image_id,
                "tested_image_identity_exact": True,
                "authoritative_runtime": already,
            }

        previous = self._snapshot_accepted_runtime(cwd=context["cwd"], env=context["env"])
        tag_result = self._run_capture(["docker", "tag", candidate_image, context["image"]], cwd=context["cwd"], env=context["env"], timeout=60)
        if tag_result.get("returncode") != 0:
            return {"ok": False, "status": "authoritative_runtime_tag_failed", "failure_code": "authoritative_runtime_tag_failed", "error": "failed to tag tested candidate image as the authoritative runtime image", "previous_runtime": previous, "candidate_image": candidate_image, "production_image": context["image"], "stderr_tail": str(tag_result.get("stderr") or "")[-2000:]}
        production_inspect = self._run_capture(["docker", "image", "inspect", context["image"], "--format", "{{.Id}}"], cwd=context["cwd"], env=context["env"], timeout=60)
        production_image_id = str(production_inspect.get("stdout") or "").strip()
        if production_image_id != candidate_image_id:
            return {"ok": False, "status": "authoritative_runtime_image_identity_mismatch", "failure_code": "authoritative_runtime_image_identity_mismatch", "error": "production image tag does not reference the exact tested candidate image", "previous_runtime": previous, "candidate_image_id": candidate_image_id, "production_image_id": production_image_id}
        compose = ["docker", "compose", "-p", context["project"], "-f", str(context["compose_file"])]
        start = self._run_logged(
            compose + ["up", "-d", "--force-recreate", "--no-build", "chatgpt-service"],
            cwd=context["cwd"],
            env=context["env"],
            log_path=self._runtime_paths(machine)["logs"] / "production-promotion.log",
            timeout=300,
        )
        expected_version = machine.config.version.removeprefix("v")
        health = self._wait_authoritative_health(expected_version, timeout=120) if start.get("returncode") == 0 else {"ok": False, "health": {}, "attempts": []}
        final_status = self.authoritative_runtime_status(machine, record) if health.get("ok") is True else {"ok": False, "status": "authoritative_runtime_mismatch"}
        if start.get("returncode") == 0 and health.get("ok") is True and final_status.get("ok") is True:
            return {
                "ok": True,
                "status": "authoritative_runtime_promoted",
                "promotion_performed": True,
                "previous_runtime": previous,
                "candidate_image": candidate_image,
                "candidate_image_id": candidate_image_id,
                "production_image": context["image"],
                "production_image_id": production_image_id,
                "tested_image_identity_exact": True,
                "start": start,
                "health": health,
                "authoritative_runtime": final_status,
            }
        rollback = self._restore_authoritative_runtime(machine, record, context, previous)
        return {
            "ok": False,
            "status": "authoritative_runtime_promotion_failed" if rollback.get("ok") is True else "authoritative_runtime_promotion_rollback_failed",
            "failure_code": "authoritative_runtime_promotion_failed" if rollback.get("ok") is True else "authoritative_runtime_promotion_rollback_failed",
            "error": "authoritative runtime promotion did not converge to the exact tested candidate" if rollback.get("ok") is True else "authoritative runtime promotion failed and rollback did not restore the previous healthy service",
            "previous_runtime": previous,
            "candidate_image": candidate_image,
            "candidate_image_id": candidate_image_id,
            "production_image": context["image"],
            "production_image_id": production_image_id,
            "start": start,
            "health": health,
            "authoritative_runtime": final_status,
            "rollback": rollback,
        }

    def cleanup_candidate_runtimes(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        env = self._control_env(machine, record)
        attempt_root = machine.config.profile_dir / "release_attempts_v2" / machine.repo_id
        allowed_projects: set[str] = set()
        if attempt_root.is_dir():
            for checkpoint_path in attempt_root.glob("*/*/runtime/runtime-checkpoint.json"):
                try:
                    checkpoint = _read_json(checkpoint_path)
                except (OSError, json.JSONDecodeError, ReleaseStateMachineError):
                    continue
                project = str(checkpoint.get("candidate_compose_project") or "")
                if project.startswith("pb-candidate-"):
                    allowed_projects.add(project)
        listed = self._run_capture(
            ["docker", "ps", "-a", "--format", "{{.ID}}|{{.Label \"com.docker.compose.project\"}}|{{.Label \"com.docker.compose.service\"}}"],
            cwd=machine.config.repo_root,
            env=env,
            timeout=60,
        )
        if listed.get("returncode") != 0:
            return {"ok": False, "status": "candidate_runtime_cleanup_inventory_failed", "failure_code": "candidate_runtime_cleanup_inventory_failed", "error": "unable to enumerate isolated candidate runtimes", "allowed_projects": sorted(allowed_projects)}
        targets: list[dict[str, str]] = []
        for line in str(listed.get("stdout") or "").splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3 and parts[1] in allowed_projects and parts[2] == "chatgpt-service":
                targets.append({"container_id": parts[0], "project": parts[1], "service": parts[2]})
        removed: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for target in targets:
            result = self._run_capture(["docker", "rm", "-f", target["container_id"]], cwd=machine.config.repo_root, env=env, timeout=60)
            item = {**target, "returncode": result.get("returncode"), "stderr_tail": str(result.get("stderr") or "")[-1000:]}
            (removed if result.get("returncode") == 0 else failures).append(item)
        return {
            "ok": not failures,
            "status": "candidate_runtimes_cleaned" if not failures else "candidate_runtime_cleanup_failed",
            "failure_code": None if not failures else "candidate_runtime_cleanup_failed",
            "allowed_projects": sorted(allowed_projects),
            "inventory_count": len(targets),
            "removed": removed,
            "failures": failures,
        }

    @staticmethod
    def _source_family_key(name: str) -> str:
        return re.sub(r"\(\d+\)(?=\.zip$)", "", Path(name).name, flags=re.IGNORECASE)

    def _set_publication_subphase(self, machine: "ReleaseStateMachine", record: dict[str, Any], step: str | None, started_at: str | None = None) -> None:
        timing = record.setdefault("publication_timing", {})
        timing["active_subphase"] = step
        timing["active_subphase_started_at"] = started_at if step else None
        machine._refresh_release_eta(record, active_transition="TESTED_GREEN" if step else None, active_transition_started_at=(record.get("release_eta") or {}).get("active_transition_started_at"))
        machine.save(record)

    def _finish_publication_subphase(self, machine: "ReleaseStateMachine", record: dict[str, Any], step: str, started_at: str, outcome: str, detail: dict[str, Any]) -> None:
        finished_at = machine.clock()
        machine._record_release_eta_observation(step=step, started_at=started_at, finished_at=finished_at, outcome=outcome)
        timing = record.setdefault("publication_timing", {})
        timing.setdefault("completed_subphases", []).append(step) if outcome == "passed" and step not in timing.setdefault("completed_subphases", []) else None
        timing.setdefault("observations", []).append({"step": step, "started_at": started_at, "finished_at": finished_at, "outcome": outcome, "detail": detail})
        timing["active_subphase"] = None
        timing["active_subphase_started_at"] = None
        machine._refresh_release_eta(record)
        machine.save(record)

    def _materialize_tested_source(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        fingerprint = self._runtime_source_fingerprint(machine, record)
        if fingerprint.get("ok") is not True:
            return {
                "ok": False,
                "status": str(fingerprint.get("status") or "runtime_source_fingerprint_missing"),
                "failure_code": str(fingerprint.get("failure_code") or "runtime_source_fingerprint_missing"),
                "runtime_source_fingerprint": fingerprint,
            }
        expected_fingerprint = str(fingerprint["source_fingerprint"])
        artifact = Path(str(record.get("artifact", {}).get("object_path") or ""))
        if not artifact.is_file():
            return {
                "ok": False,
                "status": "worktree_materialization_artifact_missing",
                "failure_code": "worktree_materialization_artifact_missing",
                "runtime_source_fingerprint": fingerprint,
            }
        pre_status = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=machine.config.repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        stage_root = machine.attempt_dir / "publication-source"
        if stage_root.exists():
            shutil.rmtree(stage_root)
        stage_root.mkdir(parents=True, exist_ok=True)
        _safe_extract(artifact, stage_root)
        clean_fingerprint = self._source_fingerprint(stage_root)
        if clean_fingerprint != expected_fingerprint:
            return {"ok": False, "status": "candidate_source_fingerprint_mismatch", "failure_code": "candidate_source_fingerprint_mismatch", "expected": expected_fingerprint, "clean_extraction": clean_fingerprint}
        removed: list[str] = []
        for child in list(machine.config.repo_root.iterdir()):
            if child.name in self.SOURCE_PRESERVE_ROOTS:
                continue
            removed.append(child.name)
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)
        copied: list[str] = []
        for child in stage_root.iterdir():
            if child.name in self.SOURCE_PRESERVE_ROOTS:
                return {"ok": False, "status": "candidate_contains_protected_root", "failure_code": "candidate_contains_protected_root", "root": child.name}
            destination = machine.config.repo_root / child.name
            copied.append(child.name)
            if child.is_dir():
                shutil.copytree(child, destination, copy_function=shutil.copy2)
            else:
                shutil.copy2(child, destination)
        observed = self._source_fingerprint(machine.config.repo_root)
        return {
            "ok": observed == expected_fingerprint,
            "status": "tested_source_materialized" if observed == expected_fingerprint else "materialized_source_fingerprint_mismatch",
            "failure_code": None if observed == expected_fingerprint else "materialized_source_fingerprint_mismatch",
            "tested_source_fingerprint": expected_fingerprint,
            "runtime_source_fingerprint": fingerprint,
            "clean_extraction_fingerprint": clean_fingerprint,
            "materialized_worktree_fingerprint": observed,
            "pre_materialization_git_status_returncode": pre_status.returncode,
            "pre_materialization_dirty_paths": [line[3:] for line in pre_status.stdout.splitlines() if len(line) > 3],
            "removed_root_entries": sorted(removed),
            "copied_root_entries": sorted(copied),
            "preserved_roots": sorted(self.SOURCE_PRESERVE_ROOTS),
        }

    def _git_head_source_fingerprint(self, machine: "ReleaseStateMachine") -> dict[str, Any]:
        archive = subprocess.run(["git", "archive", "--format=zip", "HEAD"], cwd=machine.config.repo_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if archive.returncode != 0:
            return {"ok": False, "status": "git_head_archive_failed", "stderr_tail": archive.stderr.decode("utf-8", errors="replace")[-2000:]}
        with tempfile.TemporaryDirectory(prefix="pb-git-head-") as tmp:
            target = Path(tmp)
            archive_path = target / "head.zip"
            archive_path.write_bytes(archive.stdout)
            extracted = target / "tree"; extracted.mkdir()
            _safe_extract(archive_path, extracted)
            return {"ok": True, "status": "git_head_fingerprinted", "fingerprint": self._source_fingerprint(extracted)}

    def _run_publication_command(self, machine: "ReleaseStateMachine", record: dict[str, Any], *, kind: str, command: list[str], actions: tuple[str, ...] | None, timeout: float, require_status: bool = False) -> dict[str, Any]:
        logs = machine.attempt_dir / "runtime" / "logs"; logs.mkdir(parents=True, exist_ok=True)
        started = machine.clock()
        self._set_publication_subphase(machine, record, kind, started)
        completed = subprocess.run(command, cwd=str(machine.config.repo_root), env=self._control_env(machine, record), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
        stdout_path = logs / f"publication-{kind.lower()}.stdout.log"; stderr_path = logs / f"publication-{kind.lower()}.stderr.log"
        stdout_path.write_text(completed.stdout or "", encoding="utf-8"); stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        selection = _select_action_document(completed.stdout or "", actions=actions, result_name=kind.lower(), require_status=require_status) if actions else {"ok": True, "result": None, "document_count": len(_parse_json_documents(completed.stdout or "")), "match_count": 0, "errors": []}
        payload = selection.get("result") if isinstance(selection.get("result"), dict) else {}
        ok = completed.returncode == 0 and (selection.get("ok") is True if actions else True) and (payload.get("ok") is True if actions else True)
        result = {
            "kind": kind, "ok": ok, "command": command, "returncode": completed.returncode, "result": payload, "selection": selection,
            "stdout_path": str(stdout_path), "stderr_path": str(stderr_path),
            "stdout_sha256": sha256_file(stdout_path), "stderr_sha256": sha256_file(stderr_path),
            "stdout_tail": (completed.stdout or "")[-4000:], "stderr_tail": (completed.stderr or "")[-4000:],
        }
        self._finish_publication_subphase(machine, record, kind, started, "passed" if ok else "failed", {"returncode": completed.returncode, "stdout_sha256": result["stdout_sha256"], "stderr_sha256": result["stderr_sha256"]})
        return result

    def _list_project_sources(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        runtime = record.get("evidence", {}).get("RUNTIME_PREPARED", {})
        extracted = Path(str(runtime.get("extraction_path") or ""))
        candidate_python = Path(str(runtime.get("candidate_python") or self._python(machine)))
        command = [str(candidate_python), str(extracted / "promptbranch_cli.py"), "--profile-dir", str(machine.config.profile_dir), "src", "list", "--json"]
        completed = subprocess.run(command, cwd=str(machine.config.repo_root), env=self._control_env(machine, record), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, check=False)
        selected = _select_action_document(completed.stdout or "", actions=("list",), result_name="project_source_list", require_status=False)
        payload = selected.get("result") if isinstance(selected.get("result"), dict) else {}
        return {"ok": completed.returncode == 0 and selected.get("ok") is True and payload.get("ok") is True, "returncode": completed.returncode, "result": payload, "selection": selected, "stderr_tail": (completed.stderr or "")[-2000:]}

    def _matching_source_family(self, listing: dict[str, Any], requested_name: str) -> list[dict[str, Any]]:
        target = self._source_family_key(requested_name)
        payload = listing.get("result") if isinstance(listing.get("result"), dict) else {}
        sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
        return [item for item in sources if isinstance(item, dict) and self._source_family_key(str(item.get("name") or item.get("title") or "")) == target]

    def optional_publication(self, machine: "ReleaseStateMachine", record: dict[str, Any]) -> dict[str, Any]:
        requested = {"commit": machine.config.commit, "push": machine.config.push, "upload_project_source": machine.config.upload_project_source}
        if not any(requested.values()):
            return {"ok": True, "status": "not_requested", "requested": requested, "mutations_performed": []}
        runtime = record.get("evidence", {}).get("RUNTIME_PREPARED", {})
        extracted = Path(str(runtime.get("extraction_path") or ""))
        candidate_python = Path(str(runtime.get("candidate_python") or self._python(machine)))
        results: list[dict[str, Any]] = []
        mutations: list[str] = []

        if machine.config.commit:
            started = machine.clock(); self._set_publication_subphase(machine, record, "WORKTREE_MATERIALIZE", started)
            materialized = self._materialize_tested_source(machine, record)
            self._finish_publication_subphase(machine, record, "WORKTREE_MATERIALIZE", started, "passed" if materialized.get("ok") else "failed", materialized)
            results.append({"kind": "worktree_materialize", **materialized})
            if materialized.get("ok") is not True:
                return {"ok": False, "status": "failed", "requested": requested, "results": results, "mutations_performed": mutations, "failure_code": materialized.get("failure_code")}
            mutations.append("worktree_materialize")

            command = [str(candidate_python), str(extracted / "promptbranch_cli.py"), "release", "pipeline", "apply", "--repo-path", str(machine.config.repo_root), "--confirm-version", machine.config.version, "--stage-all", "--commit", "--json"]
            git_result = self._run_publication_command(machine, record, kind="GIT_COMMIT", command=command, actions=("release_pipeline_apply",), timeout=1800, require_status=True)
            payload = git_result.get("result") if isinstance(git_result.get("result"), dict) else {}
            runtime_fingerprint = self._runtime_source_fingerprint(machine, record)
            if runtime_fingerprint.get("ok") is not True:
                results.append({"kind": "git_commit_identity", **runtime_fingerprint})
                return {
                    "ok": False,
                    "status": "failed",
                    "requested": requested,
                    "results": results,
                    "mutations_performed": mutations,
                    "failure_code": runtime_fingerprint.get("failure_code") or "runtime_source_fingerprint_missing",
                }
            expected_fp = str(runtime_fingerprint["source_fingerprint"])
            worktree_fp = self._source_fingerprint(machine.config.repo_root)
            head_fp = self._git_head_source_fingerprint(machine)
            binding = payload.get("evidence_binding") if isinstance(payload.get("evidence_binding"), dict) else {}
            guards = {
                "pipeline_version_exact": str(payload.get("version") or "") == machine.config.version,
                "pipeline_artifact_sha_exact": str((payload.get("artifact") or {}).get("sha256") or "") == str(record.get("artifact", {}).get("sha256") or ""),
                "pipeline_git_commit_bound": bool(binding.get("git_commit")),
                "materialized_worktree_fingerprint_exact": worktree_fp == expected_fp,
                "committed_tree_fingerprint_exact": head_fp.get("ok") is True and head_fp.get("fingerprint") == expected_fp,
            }
            git_result["guards"] = guards; git_result["worktree_fingerprint"] = worktree_fp; git_result["git_head_fingerprint"] = head_fp; git_result["runtime_source_fingerprint"] = runtime_fingerprint
            git_result["ok"] = git_result.get("ok") is True and all(guards.values())
            results.append({"kind": "git_commit", **git_result})
            if git_result.get("ok") is not True:
                return {"ok": False, "status": "failed", "requested": requested, "results": results, "mutations_performed": mutations, "failure_code": "git_commit_publication_failed"}
            mutations.append("commit")

            if machine.config.push:
                push_command = ["git", "push"]
                push_result = self._run_publication_command(machine, record, kind="GIT_PUSH", command=push_command, actions=None, timeout=600)
                head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=machine.config.repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                upstream = subprocess.run(["git", "rev-parse", "@{u}"], cwd=machine.config.repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                push_result["head"] = head.stdout.strip(); push_result["upstream"] = upstream.stdout.strip()
                push_result["guards"] = {"head_resolved": head.returncode == 0, "upstream_resolved": upstream.returncode == 0, "upstream_matches_head": head.returncode == 0 and upstream.returncode == 0 and head.stdout.strip() == upstream.stdout.strip()}
                push_result["ok"] = push_result.get("ok") is True and all(push_result["guards"].values())
                results.append({"kind": "git_push", **push_result})
                if push_result.get("ok") is not True:
                    return {"ok": False, "status": "failed", "requested": requested, "results": results, "mutations_performed": mutations, "failure_code": "git_push_publication_failed"}
                mutations.append("push")

        if machine.config.upload_project_source:
            artifact_name = str(record.get("artifact", {}).get("filename") or "")
            before = self._list_project_sources(machine, record)
            before_matches = self._matching_source_family(before, artifact_name) if before.get("ok") else []
            prior = record.get("failure") if isinstance(record.get("failure"), dict) else {}
            prior_text = json.dumps(prior, sort_keys=True)
            prior_matching_attempt = artifact_name in prior_text and "PROJECT_SOURCE_UPLOAD" in prior_text
            if before_matches and prior_matching_attempt:
                result = {"kind": "project_source", "ok": True, "status": "reconciled_existing_publication", "reconciled": True, "matching_sources": before_matches, "requested_filename": artifact_name}
                results.append(result); mutations.append("upload_project_source")
            else:
                command = [str(candidate_python), str(extracted / "promptbranch_cli.py"), "--profile-dir", str(machine.config.profile_dir), "src", "add", str(record["artifact"]["object_path"]), "--json"]
                upload = self._run_publication_command(machine, record, kind="PROJECT_SOURCE_UPLOAD", command=command, actions=("add",), timeout=900, require_status=False)
                after = self._list_project_sources(machine, record)
                matches = self._matching_source_family(after, artifact_name) if after.get("ok") else []
                upload["post_upload_listing"] = after; upload["matching_sources"] = matches; upload["requested_filename"] = artifact_name
                # Rendered surface reconciliation is authoritative for an ambiguous JSON result.
                upload["ok"] = bool(matches) and upload.get("returncode") == 0
                upload["status"] = "uploaded_and_reconciled" if upload["ok"] else "project_source_publication_unverified"
                results.append({"kind": "project_source", **upload})
                if upload.get("ok") is not True:
                    return {"ok": False, "status": "failed", "requested": requested, "results": results, "mutations_performed": mutations, "failure_code": "project_source_publication_failed"}
                mutations.append("upload_project_source")

        return {"ok": True, "status": "completed", "requested": requested, "results": results, "mutations_performed": mutations}



class ReleaseStateMachine:
    def __init__(
        self,
        config: ReleaseStateMachineConfig,
        *,
        executor: ReleaseExecutor | None = None,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.config = config.normalized()
        self.executor = executor or SubprocessReleaseExecutor()
        self.clock = clock
        if not self.config.artifact.is_file():
            raise ReleaseStateMachineError(f"artifact not found: {self.config.artifact}")
        parsed = parse_canonical_artifact_filename(self.config.artifact.name)
        if not parsed:
            raise ReleaseStateMachineError("artifact filename must use canonical <repo_id>_v<version>.zip grammar")
        self.repo_id = parsed["repo_id"]
        if parsed["version"] != self.config.version:
            raise ReleaseStateMachineError(
                f"artifact filename version {parsed['version']} does not match target {self.config.version}"
            )
        self.input_sha256 = sha256_file(self.config.artifact)
        safe_sha = self.input_sha256[:16]
        self.attempt_id = f"{self.repo_id}:{self.config.version}:{self.input_sha256}"
        self.attempt_dir = self.config.profile_dir / "release_attempts_v2" / self.repo_id / self.config.version / safe_sha
        self.attempt_path = self.attempt_dir / "attempt.json"
        self.release_eta_history_path = self.config.profile_dir / "release-eta-history.json"
        self.release_eta_snapshot_path = self.attempt_dir / "release-eta.json"
        self._eta_history_synced = False

    def _ensure_release_eta_history(self) -> dict[str, Any]:
        if self._eta_history_synced:
            return {"ok": True, "status": "already_synced"}
        try:
            result = sync_release_eta_history_from_attempts(self.config.profile_dir, self.release_eta_history_path)
            self._eta_history_synced = True
            return {**result, "status": "synced"}
        except Exception as exc:
            return {
                "ok": False,
                "status": "eta_history_sync_degraded",
                "error": f"{type(exc).__name__}: {exc}",
            }

    def _refresh_release_eta(
        self,
        record: dict[str, Any],
        *,
        active_transition: str | None = None,
        active_transition_started_at: str | None = None,
        configured_outer_timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        sync = self._ensure_release_eta_history()
        try:
            snapshot = build_release_eta_snapshot(
                attempt_id=self.attempt_id,
                current_state=str(record.get("state") or "DECLARED"),
                target_state="FINAL_VERIFIED",
                profile=self.config.profile,
                release_type=self.config.release_type,
                history_path=self.release_eta_history_path,
                configured_test_timeout_seconds=self.config.test_timeout,
                active_transition=active_transition,
                active_transition_started_at=active_transition_started_at,
                configured_outer_timeout_seconds=configured_outer_timeout_seconds,
                generated_at=self.clock(),
                publication_plan={"commit": self.config.commit, "push": self.config.push, "upload_project_source": self.config.upload_project_source},
                active_subphase=str((record.get("publication_timing") or {}).get("active_subphase") or "") or None,
                active_subphase_started_at=str((record.get("publication_timing") or {}).get("active_subphase_started_at") or "") or None,
                completed_subphases=list((record.get("publication_timing") or {}).get("completed_subphases") or []),
                failure_state=str(record.get("failure_state") or "") or None,
            )
            snapshot["history_sync"] = sync
            record["release_eta"] = snapshot
            write_release_eta_snapshot(self.release_eta_snapshot_path, snapshot)
            return snapshot
        except Exception as exc:
            degraded = {
                "schema": "promptbranch.release_eta.snapshot",
                "schema_version": "1.2",
                "generated_at": self.clock(),
                "attempt_id": self.attempt_id,
                "current_state": str(record.get("state") or "DECLARED"),
                "target_state": "FINAL_VERIFIED",
                "profile": self.config.profile,
                "release_type": self.config.release_type,
                "status": "eta_degraded",
                "error": f"{type(exc).__name__}: {exc}",
                "advisory_only": True,
                "validation_authority_unchanged": True,
                "history_sync": sync,
            }
            record["release_eta"] = degraded
            try:
                write_release_eta_snapshot(self.release_eta_snapshot_path, degraded)
            except Exception:
                pass
            return degraded

    def _record_release_eta_observation(
        self,
        *,
        step: str,
        started_at: str,
        finished_at: str,
        outcome: str,
    ) -> dict[str, Any] | None:
        try:
            return append_release_eta_observation(
                self.release_eta_history_path,
                attempt_id=self.attempt_id,
                version=self.config.version,
                baseline_version=self.config.baseline_version,
                release_type=self.config.release_type,
                profile=self.config.profile,
                step=step,
                started_at=started_at,
                finished_at=finished_at,
                outcome=outcome,
            )
        except Exception:
            return None

    def eta_status(self, *, configured_outer_timeout_seconds: float | None = None) -> tuple[dict[str, Any], int]:
        if not self.attempt_path.is_file():
            return {
                "ok": False,
                "action": "release_eta_status",
                "status": "attempt_not_found",
                "attempt_path": str(self.attempt_path),
                "version": self.config.version,
            }, 2
        record = _read_json(self.attempt_path)
        self._validate_record_identity(record)
        active = record.get("release_eta") if isinstance(record.get("release_eta"), dict) else {}
        active_transition = active.get("active_transition") if active.get("status") == "eta_available" else None
        active_started_at = active.get("active_transition_started_at") if active_transition else None
        snapshot = self._refresh_release_eta(
            record,
            active_transition=str(active_transition) if active_transition else None,
            active_transition_started_at=str(active_started_at) if active_started_at else None,
            configured_outer_timeout_seconds=configured_outer_timeout_seconds,
        )
        payload = {
            "ok": snapshot.get("status") in {"eta_available", "blocked_retryable"},
            "action": "release_eta_status",
            "status": snapshot.get("status"),
            "attempt_id": self.attempt_id,
            "attempt_path": str(self.attempt_path),
            "eta_snapshot_path": str(self.release_eta_snapshot_path),
            "current_state": record.get("state"),
            "failure_state": record.get("failure_state"),
            "eta": snapshot,
            "mutation_performed": False,
        }
        return payload, 0 if payload["ok"] else 1

    def _new_record(self) -> dict[str, Any]:
        now = self.clock()
        return {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "attempt_id": self.attempt_id,
            "repo_id": self.repo_id,
            "baseline_version": self.config.baseline_version,
            "target_version": self.config.version,
            "release_type": self.config.release_type,
            "state": "DECLARED",
            "failure_state": None,
            "failure": None,
            "created_at": now,
            "updated_at": now,
            "request": {
                "artifact_input": str(self.config.artifact),
                "artifact_input_sha256": self.input_sha256,
                "profile": self.config.profile,
                "test_timeout": self.config.test_timeout,
                "artifact_conversation_url": self.config.artifact_conversation_url,
                "mutation_policy": {
                    "adopt": self.config.adopt,
                    "commit": self.config.commit,
                    "push": self.config.push,
                    "upload_project_source": self.config.upload_project_source,
                },
            },
            "artifact": None,
            "evidence": {
                "DECLARED": {
                    "repo_id": self.repo_id,
                    "target_version": self.config.version,
                    "baseline_version": self.config.baseline_version,
                    "release_type": self.config.release_type,
                    "attempt_id": self.attempt_id,
                    "recorded_at": now,
                }
            },
            "transitions": [],
            "optional_publication": None,
            "release_eta": None,
            "lifecycle_complete": False,
            "next_transition": "ARTIFACT_BOUND",
        }

    def load_or_create(self) -> dict[str, Any]:
        version_root = self.config.profile_dir / "release_attempts_v2" / self.repo_id / self.config.version
        for existing_path in sorted(version_root.glob("*/attempt.json")):
            if existing_path == self.attempt_path:
                continue
            try:
                existing = _read_json(existing_path)
            except Exception:
                continue
            existing_request = existing.get("request") if isinstance(existing.get("request"), dict) else {}
            existing_artifact = existing.get("artifact") if isinstance(existing.get("artifact"), dict) else {}
            existing_sha = str(existing_artifact.get("sha256") or existing_request.get("artifact_input_sha256") or "").lower()
            if existing_sha and existing_sha != self.input_sha256.lower():
                raise TransitionTerminalFailure(
                    "artifact_identity_conflict",
                    "target version is already bound to different artifact bytes",
                    details={
                        "existing_attempt_path": str(existing_path),
                        "existing_sha256": existing_sha,
                        "requested_sha256": self.input_sha256,
                    },
                )
        if self.attempt_path.exists():
            record = _read_json(self.attempt_path)
            self._validate_record_identity(record)
            request = record.setdefault("request", {})
            mutation_policy = request.setdefault("mutation_policy", {})
            changed = False
            stored_origin=str(request.get("artifact_conversation_url") or "").strip() or None; requested_origin=str(self.config.artifact_conversation_url or "").strip() or None
            if stored_origin and requested_origin and stored_origin != requested_origin:
                raise TransitionTerminalFailure("artifact_conversation_provenance_conflict","release attempt is already bound to a different artifact origin conversation",details={"existing":stored_origin,"requested":requested_origin})
            if requested_origin and not stored_origin:
                request["artifact_conversation_url"]=requested_origin; changed=True
            for key, requested in {
                "adopt": self.config.adopt,
                "commit": self.config.commit,
                "push": self.config.push,
                "upload_project_source": self.config.upload_project_source,
            }.items():
                if requested and mutation_policy.get(key) is not True:
                    mutation_policy[key] = True
                    changed = True
            eta_added = False
            if not isinstance(record.get("release_eta"), dict):
                self._refresh_release_eta(record)
                eta_added = True
            if changed or eta_added:
                self.save(record)
            return record
        record = self._new_record()
        self._refresh_release_eta(record)
        _atomic_write_json(self.attempt_path, record)
        return record

    def _validate_record_identity(self, record: dict[str, Any]) -> None:
        expected = {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "attempt_id": self.attempt_id,
            "repo_id": self.repo_id,
            "baseline_version": self.config.baseline_version,
            "target_version": self.config.version,
        }
        mismatches = {key: {"expected": value, "actual": record.get(key)} for key, value in expected.items() if record.get(key) != value}
        if mismatches:
            raise ReleaseStateMachineError(f"release attempt identity mismatch: {json.dumps(mismatches, sort_keys=True)}")
        artifact = record.get("artifact") if isinstance(record.get("artifact"), dict) else None
        if artifact and str(artifact.get("sha256") or "").lower() != self.input_sha256.lower():
            raise TransitionTerminalFailure(
                "artifact_identity_conflict",
                "attempt is already bound to different artifact bytes",
                details={"expected": artifact.get("sha256"), "actual": self.input_sha256},
            )

    def save(self, record: dict[str, Any]) -> None:
        record["updated_at"] = self.clock()
        record["next_transition"] = LEGAL_TRANSITIONS.get(str(record.get("state") or ""))
        record["lifecycle_complete"] = record.get("state") == "FINAL_VERIFIED"
        _atomic_write_json(self.attempt_path, record)

    def _transition(
        self,
        record: dict[str, Any],
        destination: str,
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        source = str(record.get("state") or "")
        required = LEGAL_TRANSITIONS.get(source)
        if required != destination:
            raise TransitionBlocked(
                "illegal_transition",
                f"illegal transition {source} -> {destination}; required next state is {required}",
                details={"source_state": source, "requested_state": destination, "required_next_state": required},
            )
        if destination in record.get("evidence", {}):
            return {
                "ok": True,
                "status": "already_complete",
                "state": source,
                "destination": destination,
                "mutation_performed": False,
            }
        started = self.clock()
        self._refresh_release_eta(record, active_transition=destination, active_transition_started_at=started)
        self.save(record)
        try:
            evidence = handler(record)
        except (TransitionBlocked, TransitionTerminalFailure):
            finished = self.clock()
            self._record_release_eta_observation(step=destination, started_at=started, finished_at=finished, outcome="failed")
            self._refresh_release_eta(record)
            self.save(record)
            raise
        if evidence.get("ok") is not True:
            finished = self.clock()
            self._record_release_eta_observation(step=destination, started_at=started, finished_at=finished, outcome="failed")
            self._refresh_release_eta(record)
            self.save(record)
            raise TransitionBlocked(
                str(evidence.get("failure_code") or f"{destination.lower()}_failed"),
                str(evidence.get("error") or evidence.get("status") or f"transition to {destination} failed"),
                details=evidence,
            )
        finished = self.clock()
        self._record_release_eta_observation(step=destination, started_at=started, finished_at=finished, outcome="passed")
        record.setdefault("evidence", {})[destination] = {**evidence, "recorded_at": finished}
        record.setdefault("transitions", []).append(
            {
                "source_state": source,
                "destination_state": destination,
                "status": "completed",
                "guards": evidence.get("guards") or {},
                "effects": evidence.get("effects") or {},
                "started_at": started,
                "finished_at": finished,
            }
        )
        record["state"] = destination
        record["failure_state"] = None
        record["failure"] = None
        self._refresh_release_eta(record)
        self.save(record)
        return {
            "ok": True,
            "status": "transition_completed",
            "source_state": source,
            "state": destination,
            "mutation_performed": True,
            "evidence": evidence,
        }

    def _bind_artifact(self, record: dict[str, Any]) -> dict[str, Any]:
        object_dir = self.config.profile_dir / "release_objects" / self.input_sha256
        object_path = object_dir / self.config.artifact.name
        object_dir.mkdir(parents=True, exist_ok=True)
        if object_path.exists():
            observed = sha256_file(object_path)
            if observed != self.input_sha256:
                raise TransitionTerminalFailure(
                    "artifact_identity_conflict",
                    "immutable artifact object exists with different bytes",
                    details={"path": str(object_path), "expected": self.input_sha256, "actual": observed},
                )
            copy_performed = False
        else:
            temp = object_path.with_suffix(".zip.tmp")
            shutil.copy2(self.config.artifact, temp)
            if sha256_file(temp) != self.input_sha256:
                temp.unlink(missing_ok=True)
                raise TransitionTerminalFailure("artifact_copy_verification_failed", "artifact copy SHA verification failed")
            temp.replace(object_path)
            copy_performed = True
        with zipfile.ZipFile(object_path) as archive:
            entry_count = len(archive.infolist())
        artifact = {
            "filename": object_path.name,
            "sha256": self.input_sha256,
            "size_bytes": object_path.stat().st_size,
            "file_count": entry_count,
            "embedded_version": _read_zip_version(object_path),
            "object_path": str(object_path),
            "input_path": str(self.config.artifact),
        }
        if artifact["embedded_version"] != self.config.version:
            raise TransitionTerminalFailure(
                "artifact_version_mismatch",
                "ZIP VERSION does not match target version",
                details={"expected": self.config.version, "actual": artifact["embedded_version"]},
            )
        record["artifact"] = artifact
        return {
            "ok": True,
            "status": "artifact_bound",
            "artifact": artifact,
            "guards": {
                "artifact_exists": True,
                "filename_canonical": True,
                "embedded_version_matches": True,
                "sha256_matches_input": True,
            },
            "effects": {"object_copy_performed": copy_performed, "object_path": str(object_path)},
        }

    def _verify_artifact(self, record: dict[str, Any]) -> dict[str, Any]:
        artifact = Path(record["artifact"]["object_path"])
        verification = verify_zip_artifact(artifact)
        with zipfile.ZipFile(artifact) as archive:
            names = set(archive.namelist())
        missing_required_root_entries = [name for name in REQUIRED_ARTIFACT_ROOT_ENTRIES if name not in names]
        checks = {
            "zip_crc_valid": verification.get("bad_entry") is None,
            "safe_paths_only": not verification.get("unsafe_entries"),
            "no_hygiene_violations": not verification.get("hygiene_violations"),
            "no_nested_zip": int(verification.get("nested_zip_count") or 0) == 0,
            "root_layout": verification.get("wrapper_folder") is None,
            "version_file_present": verification.get("has_version_file") is True,
            "sha256_exact": verification.get("sha256") == record["artifact"]["sha256"],
            "size_exact": int(verification.get("size_bytes") or -1) == int(record["artifact"]["size_bytes"]),
            "entry_count_exact": int(verification.get("entry_count") or -1) == int(record["artifact"]["file_count"]),
            "embedded_version_exact": _read_zip_version(artifact) == self.config.version,
            "required_root_entries_present": not missing_required_root_entries,
        }
        verified = bool(verification.get("ok")) and all(checks.values())
        result = {
            "ok": verified,
            "status": "artifact_verified" if verified else "artifact_verification_failed",
            "verification": verification,
            "missing_required_root_entries": missing_required_root_entries,
            "guards": checks,
            "effects": {"artifact_mutated": False},
        }
        if not verified:
            result["failure_code"] = "artifact_verification_failed"
            result["error"] = "artifact structural verification failed"
        return result

    def _candidate_record(self, record: dict[str, Any], repo_path: Path) -> dict[str, Any]:
        artifact = record["artifact"]
        return {
            "schema": "promptbranch.artifact.candidate",
            "schema_version": "1.0",
            "kind": "candidate_release",
            "status": "candidate_release",
            "accepted": False,
            "verified": True,
            "filename": artifact["filename"],
            "version": self.config.version,
            "repo_id": self.repo_id,
            "path": str(repo_path),
            "sha256": artifact["sha256"],
            "size_bytes": artifact["size_bytes"],
            "source_inbox_path": artifact["object_path"],
            "source_inbox_sha256": artifact["sha256"],
            "reply_request_id": self.attempt_id,
            "reply_correlation_id": self.attempt_id,
            "selected_protocol_reply": {
                "request_id": self.attempt_id,
                "correlation_id": self.attempt_id,
                "conversation_url": self.config.artifact_conversation_url,
                "conversation_id": _conversation_id_from_url(self.config.artifact_conversation_url),
                "source": "canonical_release_state_machine",
            },
            "verification": record["evidence"]["ARTIFACT_VERIFIED"]["verification"],
            "zip_version": self.config.version,
            "filename_version": self.config.version,
            "migrated_at": self.clock(),
            "migration_performed": True,
            "adoption_performed": False,
            "release_attempt_id": self.attempt_id,
            "authoritative_release_attempt": str(self.attempt_path),
        }

    def _register_candidate(self, record: dict[str, Any]) -> dict[str, Any]:
        artifact = record["artifact"]
        repo_candidate = self.config.repo_root / artifact["filename"]
        copy_performed = False
        if repo_candidate.exists():
            observed = sha256_file(repo_candidate)
            if observed != artifact["sha256"]:
                raise TransitionTerminalFailure(
                    "candidate_path_identity_conflict",
                    "repo-root candidate path already exists with different bytes",
                    details={"path": str(repo_candidate), "expected": artifact["sha256"], "actual": observed},
                )
        else:
            shutil.copy2(artifact["object_path"], repo_candidate)
            copy_performed = True
        registry = _load_candidate_registry(self.config.profile_dir)
        candidates = [item for item in registry.get("candidates", []) if isinstance(item, dict)]
        conflicts = [item for item in candidates if _candidate_conflicts(item, repo_id=self.repo_id, version=self.config.version, sha256=artifact["sha256"])]
        if conflicts:
            raise TransitionTerminalFailure(
                "candidate_identity_conflict",
                "candidate registry contains same repo/version with different SHA",
                details={"conflicts": conflicts},
            )
        candidates = [
            item
            for item in candidates
            if not (
                str(item.get("repo_id") or infer_repo_id_from_artifact_filename(str(item.get("filename") or "")) or "") == self.repo_id
                and str(item.get("version") or item.get("zip_version") or "") == self.config.version
            )
        ]
        candidate = self._candidate_record(record, repo_candidate)
        candidates.append(candidate)
        registry["candidates"] = candidates
        registry_path = _write_candidate_registry(self.config.profile_dir, registry)
        exact = [item for item in candidates if _candidate_matches(item, repo_id=self.repo_id, version=self.config.version, sha256=artifact["sha256"])]
        registered = len(exact) == 1
        result = {
            "ok": registered,
            "status": "candidate_registered" if registered else "candidate_registration_failed",
            "candidate_registry_path": str(registry_path),
            "candidate": candidate,
            "exact_match_count": len(exact),
            "guards": {
                "artifact_verified": True,
                "no_conflicting_candidate": not conflicts,
                "exactly_one_candidate": registered,
            },
            "effects": {
                "candidate_projection_written": True,
                "repo_candidate_copy_performed": copy_performed,
                "repo_candidate_path": str(repo_candidate),
            },
        }
        if not registered:
            result["failure_code"] = "candidate_registration_failed"
        return result

    def _prepare_runtime(self, record: dict[str, Any]) -> dict[str, Any]:
        result = self.executor.prepare_runtime(self, record)
        payload = {
            **result,
            "guards": {
                "candidate_registered": True,
                "candidate_python_explicit": bool(result.get("candidate_python")),
                "pytest_version_explicit": bool(result.get("candidate_pytest_version")),
                "candidate_version_exact": result.get("candidate_package_version") == self.config.version.removeprefix("v"),
                "candidate_cli_version_exact": result.get("candidate_cli_version") == self.config.version.removeprefix("v"),
                "service_version_exact": result.get("service_version") == self.config.version.removeprefix("v"),
                "pytest_version_exact": result.get("candidate_pytest_version") == REQUIRED_PYTEST_VERSION,
                "clean_extraction_present": bool(result.get("extraction_path") and Path(str(result.get("extraction_path"))).is_dir()),
                "isolated_environment_present": bool(result.get("isolated_environment")),
            },
            "effects": {
                "runtime_prepared": result.get("ok") is True,
                "implicit_git_mutation": False,
                "implicit_project_source_mutation": False,
                "implicit_adoption": False,
            },
        }
        if payload.get("ok") is True:
            payload.pop("failure_code", None)
        else:
            payload["failure_code"] = result.get("failure_code") or "runtime_prepare_failed"
        return payload

    def _record_test_projection(self, record: dict[str, Any], test_result: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
        record_dir = _candidate_test_dir(self.config.profile_dir, self.config.version)
        record_dir.mkdir(parents=True, exist_ok=True)
        safe_time = re.sub(r"[^0-9A-Za-z_.-]+", "_", self.clock())
        path = record_dir / f"candidate_test.state_machine.{safe_time}.json"
        candidate_registry = _load_candidate_registry(self.config.profile_dir)
        candidates = [item for item in candidate_registry.get("candidates", []) if isinstance(item, dict)]
        exact = [item for item in candidates if _candidate_matches(item, repo_id=self.repo_id, version=self.config.version, sha256=record["artifact"]["sha256"])]
        if len(exact) != 1:
            raise TransitionBlocked("candidate_projection_missing", "exact candidate projection is missing before test recording")
        candidate = exact[0]
        canonical_result = {
            "ok": bool(test_result.get("ok")),
            "status": "candidate_test_passed" if test_result.get("ok") else "candidate_test_failed",
            "started_at": test_result.get("started_at"),
            "finished_at": test_result.get("finished_at"),
            "artifact_sha256": record["artifact"]["sha256"],
            "profile": self.config.profile,
            "state_machine_attempt_id": self.attempt_id,
            "test_run_id": test_result.get("test_run_id"),
            "retry_number": test_result.get("retry_number"),
            "project_name": test_result.get("project_name"),
            "project_url": test_result.get("project_url"),
            "report_schema": test_result.get("report_schema"),
            "report_schema_version": test_result.get("report_schema_version"),
            "report_sha256": test_result.get("report_sha256"),
            "stdout_sha256": test_result.get("stdout_sha256"),
            "stderr_sha256": test_result.get("stderr_sha256"),
            "completed": test_result.get("completed"),
            "passed": test_result.get("passed"),
            "failed": test_result.get("failed"),
            "skipped": test_result.get("skipped"),
            "failed_group": test_result.get("failed_group"),
            "failed_groups": test_result.get("failed_groups") or [],
            "failed_steps": test_result.get("failed_steps") or [],
            "detail": test_result,
        }
        test_record = {
            "schema": "promptbranch.artifact.candidate_test",
            "schema_version": "1.0",
            "candidate": candidate,
            "result": canonical_result,
            "adoption_performed": False,
            "project_source_mutated": False,
            "project_source_mutation": "not_requested",
            "source_upload_verification": None,
            "artifact_registry_updated": False,
            "state_artifact_updated": False,
            "state_source_updated": False,
            "release_attempt_id": self.attempt_id,
        }
        _atomic_write_json(path, test_record)
        updated_candidate: dict[str, Any] | None = None
        next_candidates: list[dict[str, Any]] = []
        for item in candidates:
            if _candidate_matches(item, repo_id=self.repo_id, version=self.config.version, sha256=record["artifact"]["sha256"]):
                item = {
                    **item,
                    "latest_test": {
                        "ok": bool(test_result.get("ok")),
                        "status": canonical_result["status"],
                        "record_path": str(path),
                        "tested_at": test_result.get("finished_at") or self.clock(),
                        "adoption_performed": False,
                        "artifact_sha256": record["artifact"]["sha256"],
                        "release_attempt_id": self.attempt_id,
                        "test_run_id": test_result.get("test_run_id"),
                        "retry_number": test_result.get("retry_number"),
                        "project_name": test_result.get("project_name"),
                        "project_url": test_result.get("project_url"),
                        "report_schema": test_result.get("report_schema"),
                        "report_schema_version": test_result.get("report_schema_version"),
                        "report_sha256": test_result.get("report_sha256"),
                        "stdout_sha256": test_result.get("stdout_sha256"),
                        "stderr_sha256": test_result.get("stderr_sha256"),
                        "completed": test_result.get("completed"),
                        "passed": test_result.get("passed"),
                        "failed": test_result.get("failed"),
                        "skipped": test_result.get("skipped"),
                        "failed_group": test_result.get("failed_group"),
                    },
                    "tested": bool(test_result.get("ok")),
                    "test_status": canonical_result["status"],
                }
                updated_candidate = item
            next_candidates.append(item)
        candidate_registry["candidates"] = next_candidates
        _write_candidate_registry(self.config.profile_dir, candidate_registry)
        if updated_candidate is None:
            raise TransitionBlocked("candidate_projection_update_failed", "candidate test projection was not updated")
        return path, updated_candidate

    def _start_test_attempt(self, record: dict[str, Any]) -> dict[str, Any]:
        attempts = record.setdefault("test_attempts", [])
        if not isinstance(attempts, list):
            attempts = []
            record["test_attempts"] = attempts
        now = self.clock()
        retry_number = len(attempts) + 1
        previous = attempts[-1] if attempts and isinstance(attempts[-1], dict) else None
        compact_time = re.sub(r"[^0-9A-Za-z]+", "", now)[-14:] or f"r{retry_number:04d}"
        test_run_id = f"{record['artifact']['sha256'][:12]}-r{retry_number:04d}-{compact_time}"
        project_name = f"itest-pb-sm-{record['artifact']['sha256'][:12]}-r{retry_number:04d}-{compact_time[-6:]}"[:50]
        if previous is not None and previous.get("status") != "passed":
            previous["superseded_by_test_run_id"] = test_run_id
            previous["superseded_at"] = now
            if previous.get("status") == "running":
                previous["status"] = "interrupted"
        attempt = {
            "test_run_id": test_run_id,
            "retry_number": retry_number,
            "project_name": project_name,
            "project_url": None,
            "started_at": now,
            "finished_at": None,
            "status": "running",
            "failed_step": None,
            "report_schema": None,
            "report_sha256": None,
            "stdout_sha256": None,
            "stderr_sha256": None,
            "retained_for_forensics": True,
            "superseded_by_test_run_id": None,
        }
        attempts.append(attempt)
        record["active_test_attempt"] = dict(attempt)
        self.save(record)
        return attempt

    def _finish_test_attempt(self, record: dict[str, Any], result: dict[str, Any]) -> None:
        attempts = record.setdefault("test_attempts", [])
        active = record.get("active_test_attempt") if isinstance(record.get("active_test_attempt"), dict) else {}
        test_run_id = str(result.get("test_run_id") or active.get("test_run_id") or "")
        failed_steps = result.get("failed_steps") if isinstance(result.get("failed_steps"), list) else []
        failed_step = str(failed_steps[0]) if failed_steps else None
        for attempt in reversed(attempts if isinstance(attempts, list) else []):
            if not isinstance(attempt, dict) or str(attempt.get("test_run_id") or "") != test_run_id:
                continue
            attempt.update({
                "project_url": result.get("project_url"),
                "finished_at": result.get("finished_at") or self.clock(),
                "status": "passed" if result.get("ok") is True else ("timeout" if result.get("timed_out") else "failed"),
                "failed_step": failed_step,
                "report_schema": result.get("report_schema"),
                "report_sha256": result.get("report_sha256"),
                "stdout_sha256": result.get("stdout_sha256"),
                "stderr_sha256": result.get("stderr_sha256"),
                "stdout_log_path": result.get("stdout_log_path"),
                "stderr_log_path": result.get("stderr_log_path"),
                "report_path": result.get("report_path"),
                "retained_for_forensics": result.get("ok") is not True,
            })
            break
        record.pop("active_test_attempt", None)
        self.save(record)

    def _recover_validated_candidate_test(self, record: dict[str, Any]) -> dict[str, Any] | None:
        cached = record.get("validated_candidate_test") if isinstance(record.get("validated_candidate_test"), dict) else None
        if not cached or cached.get("artifact_sha256") != record.get("artifact", {}).get("sha256") or cached.get("profile") != self.config.profile:
            return None
        report_path = Path(str(cached.get("report_path") or "")); stdout_path = Path(str(cached.get("stdout_path") or "")); stderr_path = Path(str(cached.get("stderr_path") or ""))
        if not report_path.is_file() or sha256_file(report_path) != cached.get("report_sha256"):
            return None
        if stdout_path and str(stdout_path) != "." and (not stdout_path.is_file() or sha256_file(stdout_path) != cached.get("stdout_sha256")):
            return None
        if stderr_path and str(stderr_path) != "." and (not stderr_path.is_file() or sha256_file(stderr_path) != cached.get("stderr_sha256")):
            return None
        return {**cached, "ok": True, "status": "candidate_test_reused_green", "report_selected": True, "failed": 0, "skipped": 0, "reused_green_test": True}

    def _persist_validated_candidate_test(self, record: dict[str, Any], result: dict[str, Any], test_record_path: Path) -> None:
        record["validated_candidate_test"] = {
            key: result.get(key) for key in ("started_at", "finished_at", "artifact_sha256", "profile", "candidate_python", "candidate_pytest_version", "report_schema", "report_schema_version", "report_sha256", "stdout_sha256", "stderr_sha256", "completed", "passed", "failed", "skipped", "test_run_id", "retry_number", "project_name", "project_url")
        }
        record["validated_candidate_test"].update({"report_selected": True, "report_path": result.get("report_path"), "stdout_path": result.get("stdout_log_path") or result.get("stdout_path"), "stderr_path": result.get("stderr_log_path") or result.get("stderr_path"), "test_record_path": str(test_record_path)})
        self.save(record)

    def _test_candidate(self, record: dict[str, Any]) -> dict[str, Any]:
        result = self._recover_validated_candidate_test(record)
        reused_green = result is not None
        if result is None:
            active_attempt = self._start_test_attempt(record)
            started_subphase = self.clock()
            record.setdefault("publication_timing", {})["active_subphase"] = "CANDIDATE_TEST"
            record["publication_timing"]["active_subphase_started_at"] = started_subphase
            self._refresh_release_eta(record, active_transition="TESTED_GREEN", active_transition_started_at=started_subphase)
            self.save(record)
            result = self.executor.run_tests(self, record)
            result.setdefault("test_run_id", active_attempt["test_run_id"])
            result.setdefault("retry_number", active_attempt["retry_number"])
            result.setdefault("project_name", active_attempt["project_name"])
            self._finish_test_attempt(record, result)
            finished_subphase = self.clock()
            self._record_release_eta_observation(step="CANDIDATE_TEST", started_at=started_subphase, finished_at=finished_subphase, outcome="passed" if result.get("ok") is True else "failed")
            timing = record.setdefault("publication_timing", {})
            if result.get("ok") is True and "CANDIDATE_TEST" not in timing.setdefault("completed_subphases", []): timing["completed_subphases"].append("CANDIDATE_TEST")
            timing["active_subphase"] = None; timing["active_subphase_started_at"] = None
            self._refresh_release_eta(record); self.save(record)
        failed_value = result.get("failed")
        skipped_value = result.get("skipped")
        report_selected = result.get("report_selected") is True
        failure_guards = {
            "exact_candidate_sha_bound": result.get("artifact_sha256") == record["artifact"]["sha256"],
            "test_profile_exact": result.get("profile") == self.config.profile,
            "report_selected": report_selected,
            "failed_count_zero": failed_value == 0 if isinstance(failed_value, int) and not isinstance(failed_value, bool) else False,
            "required_skips_zero": skipped_value == 0 if isinstance(skipped_value, int) and not isinstance(skipped_value, bool) else False,
        }
        if result.get("ok") is not True:
            return {
                **result,
                "guards": failure_guards,
                "effects": {"acceptance_performed": False},
                "failure_code": result.get("failure_code") or "candidate_test_failed",
            }
        guard_checks = {
            **failure_guards,
            "candidate_python_explicit": bool(result.get("candidate_python")),
            "pytest_version_exact": str(result.get("candidate_pytest_version") or "") == REQUIRED_PYTEST_VERSION,
            "report_schema_exact": result.get("report_schema") == TEST_REPORT_SCHEMA,
            "report_schema_version_exact": result.get("report_schema_version") == TEST_REPORT_SCHEMA_VERSION,
            "report_sha256_present": bool(result.get("report_sha256")),
            "stdout_sha256_present": bool(result.get("stdout_sha256")),
            "stderr_sha256_present": bool(result.get("stderr_sha256")),
            "completed_count_present": isinstance(result.get("completed"), int),
            "passed_count_present": isinstance(result.get("passed"), int),
        }
        if not all(guard_checks.values()):
            return {
                **result,
                "ok": False,
                "status": "candidate_test_evidence_invalid",
                "guards": guard_checks,
                "effects": {"acceptance_performed": False},
                "failure_code": "candidate_test_evidence_invalid",
                "error": "candidate test returned success without satisfying all exact-evidence guards",
            }
        if reused_green:
            record_path = Path(str(result.get("test_record_path") or ""))
            registry = _load_candidate_registry(self.config.profile_dir)
            candidate = next((item for item in registry.get("candidates", []) if isinstance(item, dict) and _candidate_matches(item, repo_id=self.repo_id, version=self.config.version, sha256=record["artifact"]["sha256"])), {})
            if not record_path.is_file() or not candidate:
                return {**result, "ok": False, "status": "reused_candidate_test_projection_missing", "failure_code": "reused_candidate_test_projection_missing"}
        else:
            record_path, candidate = self._record_test_projection(record, result)
            self._persist_validated_candidate_test(record, result, record_path)
        publication = self.executor.optional_publication(self, record)
        record["optional_publication"] = publication
        if publication.get("ok") is not True:
            return {
                **result,
                "ok": False,
                "status": "optional_publication_failed",
                "publication": publication,
                "failure_code": "optional_publication_failed",
                "error": "explicitly requested publication action failed",
            }
        success = {
            **result,
            "test_record_path": str(record_path),
            "candidate_projection": candidate,
            "publication": publication,
            "guards": {**guard_checks, "test_evidence_readable": record_path.is_file()},
            "effects": {
                "candidate_test_projection_written": True,
                "acceptance_performed": False,
                "implicit_mutations": False,
                "reused_green_candidate_test": reused_green,
            },
        }
        success.pop("failure_code", None)
        return success

    def _accepted_candidate_projection(self, record: dict[str, Any]) -> dict[str, Any] | None:
        artifact = record.get("artifact") if isinstance(record.get("artifact"), dict) else {}
        registry = _load_candidate_registry(self.config.profile_dir)
        candidates = [item for item in registry.get("candidates", []) if isinstance(item, dict)]
        exact = [
            item
            for item in candidates
            if _candidate_matches(
                item,
                repo_id=self.repo_id,
                version=self.config.version,
                sha256=str(artifact.get("sha256") or ""),
            )
        ]
        if len(exact) != 1:
            return None
        candidate = exact[0]
        if candidate.get("accepted") is not True or candidate.get("adoption_performed") is not True:
            return None
        return {"path": str(_candidate_registry_path(self.config.profile_dir)), "candidate": candidate}

    def _recover_completed_acceptance(self, record: dict[str, Any]) -> dict[str, Any] | None:
        artifact = record.get("artifact") if isinstance(record.get("artifact"), dict) else {}
        projection = self._accepted_candidate_projection(record)
        if projection is None:
            return None
        current = self.executor.current_status(self, record)
        current_payload = current.get("result") if isinstance(current.get("result"), dict) else {}
        alignment = _current_candidate_alignment_checks(
            current_payload,
            repo_id=self.repo_id,
            filename=str(artifact.get("filename") or ""),
            version=self.config.version,
            sha256=str(artifact.get("sha256") or ""),
        )
        checks = {
            "exactly_one_accepted_candidate": True,
            "current_probe_ok": current.get("ok") is True,
            **alignment,
        }
        if not all(checks.values()):
            return None
        return {
            "ok": True,
            "status": "accepted_candidate_recovered",
            "recovered": True,
            "candidate": projection["candidate"],
            "accepted_candidate_projection": projection,
            "current": current,
            "checks": checks,
        }

    def _accept(self, record: dict[str, Any]) -> dict[str, Any]:
        if not self.config.adopt:
            raise TransitionBlocked(
                "adoption_not_authorized",
                "transition to ACCEPTED requires explicit --adopt",
                details={"required_flag": "--adopt"},
            )
        runtime = record.get("evidence", {}).get("RUNTIME_PREPARED", {})
        tested = record.get("evidence", {}).get("TESTED_GREEN", {})
        prechecks = {
            "runtime_package_version_exact": runtime.get("candidate_package_version") == self.config.version.removeprefix("v"),
            "runtime_cli_version_exact": runtime.get("candidate_cli_version") == self.config.version.removeprefix("v"),
            "service_version_exact": runtime.get("service_version") == self.config.version.removeprefix("v"),
            "test_evidence_green": tested.get("ok") is True,
            "test_evidence_sha_bound": tested.get("artifact_sha256") == record.get("artifact", {}).get("sha256"),
            "test_profile_exact": tested.get("profile") == self.config.profile,
        }
        if not all(prechecks.values()):
            raise TransitionBlocked(
                "acceptance_guard_failed",
                "candidate acceptance prerequisites are not converged",
                details={"checks": prechecks},
            )

        result = self._recover_completed_acceptance(record)
        acceptance_command: dict[str, Any] | None = None
        recovered_after_command = False
        if result is None:
            acceptance_command = self.executor.accept_candidate(self, record)
            if acceptance_command.get("ok") is True:
                result = acceptance_command
            else:
                recovered = self._recover_completed_acceptance(record)
                if recovered is not None:
                    result = {
                        **recovered,
                        "status": "accepted_candidate_reconciled",
                        "recovered_after_acceptance_command": True,
                        "acceptance_command": acceptance_command,
                    }
                    recovered_after_command = True
                else:
                    result = acceptance_command

        projection = self._accepted_candidate_projection(record) if result.get("ok") is True else None
        if result.get("ok") is True and projection is None:
            result = {
                "ok": False,
                "status": "accepted_projection_missing_after_acceptance",
                "failure_code": "accepted_projection_missing_after_acceptance",
                "error": "acceptance completed without the canonical accepted-candidate projection",
                "acceptance_result": result,
            }

        payload = {
            **result,
            "accepted_candidate_projection": projection,
            "guards": {
                **prechecks,
                "artifact_identity_exact": True,
                "candidate_registered": True,
                "test_evidence_green": True,
                "test_evidence_sha_bound": True,
                "adoption_explicitly_authorized": True,
                "accepted_projection_written": projection is not None,
            },
            "effects": {
                "acceptance_and_local_adoption_performed": result.get("ok") is True,
                "recovered_after_ambiguous_or_failed_command": recovered_after_command,
                "projection_reused": projection is not None,
                "projection_written_by_state_machine": False,
            },
        }
        if acceptance_command is not None and "acceptance_command" not in payload:
            payload["acceptance_command"] = acceptance_command
        if payload.get("ok") is True:
            payload.pop("failure_code", None)
        else:
            payload["failure_code"] = result.get("failure_code") or "candidate_acceptance_failed"
        return payload

    def _adopt_current(self, record: dict[str, Any]) -> dict[str, Any]:
        current_before = self.executor.current_status(self, record)
        result_before = current_before.get("result") if isinstance(current_before.get("result"), dict) else {}
        alignment_before = _current_candidate_alignment_checks(
            result_before,
            repo_id=self.repo_id,
            filename=str(record.get("artifact", {}).get("filename") or ""),
            version=self.config.version,
            sha256=str(record.get("artifact", {}).get("sha256") or ""),
        )
        prechecks = {"current_command_ok": current_before.get("ok") is True, **alignment_before}
        if not all(prechecks.values()):
            return {
                "ok": False,
                "status": "adopted_current_projection_mismatch",
                "failure_code": "adopted_current_projection_mismatch",
                "error": "accepted/current projection does not match candidate before runtime promotion",
                "current_before": current_before,
                "guards": prechecks,
            }

        promotion = self.executor.promote_authoritative_runtime(self, record)
        if promotion.get("ok") is not True:
            return {
                "ok": False,
                "status": str(promotion.get("status") or "authoritative_runtime_promotion_failed"),
                "failure_code": str(promotion.get("failure_code") or "authoritative_runtime_promotion_failed"),
                "error": str(promotion.get("error") or "authoritative runtime promotion failed"),
                "current_before": current_before,
                "promotion": promotion,
                "guards": {**prechecks, "authoritative_runtime_promoted": False},
            }

        production = self.executor.authoritative_runtime_status(self, record)
        current_after = self.executor.current_status(self, record)
        result_after = current_after.get("result") if isinstance(current_after.get("result"), dict) else {}
        alignment_after = _current_candidate_alignment_checks(
            result_after,
            repo_id=self.repo_id,
            filename=str(record.get("artifact", {}).get("filename") or ""),
            version=self.config.version,
            sha256=str(record.get("artifact", {}).get("sha256") or ""),
        )
        cleanup = self.executor.cleanup_candidate_runtimes(self, record)
        checks = {
            **alignment_after,
            "current_command_ok": current_after.get("ok") is True,
            "authoritative_runtime_exact": production.get("ok") is True,
            "candidate_runtime_cleanup_ok": cleanup.get("ok") is True,
        }
        adopted = all(checks.values())
        payload = {
            "ok": adopted,
            "status": "adopted_current_verified" if adopted else "adopted_current_mismatch",
            "current_before": current_before,
            "current": current_after,
            "promotion": promotion,
            "authoritative_runtime": production,
            "candidate_runtime_cleanup": cleanup,
            "guards": checks,
            "effects": {
                "authoritative_runtime_promotion_performed": bool(promotion.get("promotion_performed")),
                "authoritative_runtime_recovered": bool(promotion.get("recovered")),
                "candidate_runtimes_cleaned": cleanup.get("ok") is True,
            },
        }
        if not adopted:
            payload["failure_code"] = "adopted_current_mismatch"
            payload["error"] = "accepted/current projection and authoritative runtime did not converge to the exact candidate"
        return payload

    def _final_verify(self, record: dict[str, Any]) -> dict[str, Any]:
        verification = self.verify_record(record, repair_projections=True)
        production = self.executor.authoritative_runtime_status(self, record)
        checks = {
            "all_prior_states_verified": all(
                item.get("verified") is True
                for item in verification.get("states", [])
                if item.get("state") != "FINAL_VERIFIED"
            ),
            "failed_invariants_empty": not verification.get("failed_invariants"),
            "candidate_test_passed": bool(record.get("evidence", {}).get("TESTED_GREEN", {}).get("ok")),
            "candidate_accepted": bool(record.get("evidence", {}).get("ACCEPTED", {}).get("ok")),
            "accepted_candidate_matches_current": bool(record.get("evidence", {}).get("ADOPTED_CURRENT", {}).get("ok")),
            "authoritative_runtime_exact": production.get("ok") is True,
        }
        final_ok = all(checks.values())
        payload = {
            "ok": final_ok,
            "status": "final_verified" if final_ok else "final_verification_failed",
            "verification": verification,
            "authoritative_runtime": production,
            "guards": checks,
            "effects": {"lifecycle_complete": final_ok},
        }
        if not final_ok:
            payload["failure_code"] = "final_verification_failed"
            payload["error"] = "final state convergence failed"
        return payload

    def execute_next(self, record: dict[str, Any]) -> dict[str, Any]:
        state = str(record.get("state") or "")
        destination = LEGAL_TRANSITIONS.get(state)
        if destination is None:
            return {"ok": True, "status": "already_complete", "state": state, "mutation_performed": False}
        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "ARTIFACT_BOUND": self._bind_artifact,
            "ARTIFACT_VERIFIED": self._verify_artifact,
            "CANDIDATE_REGISTERED": self._register_candidate,
            "RUNTIME_PREPARED": self._prepare_runtime,
            "TESTED_GREEN": self._test_candidate,
            "ACCEPTED": self._accept,
            "ADOPTED_CURRENT": self._adopt_current,
            "FINAL_VERIFIED": self._final_verify,
        }
        return self._transition(record, destination, handlers[destination])

    def run(self) -> tuple[dict[str, Any], int]:
        target = canonical_state(self.config.until)
        transitions_executed: list[dict[str, Any]] = []
        try:
            record = self.load_or_create()
            while STATE_INDEX[str(record["state"])] < STATE_INDEX[target]:
                result = self.execute_next(record)
                transitions_executed.append(result)
                record = _read_json(self.attempt_path)
            status = "already_complete" if not transitions_executed else "target_state_reached"
            payload = {
                "ok": True,
                "action": ACTION_RUN,
                "status": status,
                "attempt_id": self.attempt_id,
                "attempt_path": str(self.attempt_path),
                "current_state": record["state"],
                "target_state": target,
                "failure_state": record.get("failure_state"),
                "lifecycle_complete": record.get("state") == "FINAL_VERIFIED",
                "next_transition": LEGAL_TRANSITIONS.get(record["state"]),
                "transitions_executed": transitions_executed,
                "mutation_performed": any(item.get("mutation_performed") for item in transitions_executed),
                "artifact": record.get("artifact"),
                "eta": record.get("release_eta"),
                "eta_snapshot_path": str(self.release_eta_snapshot_path),
            }
            return payload, 0
        except TransitionTerminalFailure as exc:
            existing_path = str(exc.details.get("existing_attempt_path") or self.attempt_path)
            current_state = None
            if "record" in locals() and isinstance(record, dict):
                record["failure_state"] = "FAILED_TERMINAL"
                record["failure"] = {"code": exc.code, "message": str(exc), "details": exc.details, "recorded_at": self.clock()}
                self._refresh_release_eta(record)
                self.save(record)
                current_state = record.get("state")
            return {
                "ok": False,
                "action": ACTION_RUN,
                "status": "failed_terminal",
                "attempt_id": self.attempt_id,
                "attempt_path": existing_path,
                "current_state": current_state,
                "target_state": target,
                "failure_state": "FAILED_TERMINAL",
                "failure": {"code": exc.code, "message": str(exc), "details": exc.details, "recorded_at": self.clock()},
                "next_transition": None,
                "transitions_executed": transitions_executed,
                "mutation_performed": any(item.get("mutation_performed") for item in transitions_executed),
                "eta": record.get("release_eta") if "record" in locals() and isinstance(record, dict) else None,
                "eta_snapshot_path": str(self.release_eta_snapshot_path),
            }, 2
        except TransitionBlocked as exc:
            record["failure_state"] = "BLOCKED_RETRYABLE"
            record["failure"] = {
                "code": exc.code,
                "message": str(exc),
                "details": exc.details,
                "recorded_at": self.clock(),
            }
            self._refresh_release_eta(record)
            self.save(record)
            return {
                "ok": False,
                "action": ACTION_RUN,
                "status": "blocked_retryable",
                "attempt_id": self.attempt_id,
                "attempt_path": str(self.attempt_path),
                "current_state": record["state"],
                "target_state": target,
                "failure_state": "BLOCKED_RETRYABLE",
                "failure": record["failure"],
                "next_transition": LEGAL_TRANSITIONS.get(record["state"]),
                "transitions_executed": transitions_executed,
                "mutation_performed": any(item.get("mutation_performed") for item in transitions_executed),
                "eta": record.get("release_eta"),
                "eta_snapshot_path": str(self.release_eta_snapshot_path),
            }, 1

    def _reconstruct_candidate_projection(self, record: dict[str, Any]) -> dict[str, Any]:
        artifact = record.get("artifact") if isinstance(record.get("artifact"), dict) else {}
        repo_candidate = self.config.repo_root / str(artifact.get("filename") or "")
        if not repo_candidate.is_file() or sha256_file(repo_candidate) != artifact.get("sha256"):
            source = Path(str(artifact.get("object_path") or ""))
            if not source.is_file():
                return {"ok": False, "status": "authoritative_artifact_missing"}
            shutil.copy2(source, repo_candidate)
        registry = _load_candidate_registry(self.config.profile_dir)
        candidates = [item for item in registry.get("candidates", []) if isinstance(item, dict)]
        conflicts = [item for item in candidates if _candidate_conflicts(item, repo_id=self.repo_id, version=self.config.version, sha256=str(artifact.get("sha256") or ""))]
        if conflicts:
            return {"ok": False, "status": "candidate_projection_conflict", "conflicts": conflicts}
        candidates = [
            item
            for item in candidates
            if not (
                str(item.get("repo_id") or infer_repo_id_from_artifact_filename(str(item.get("filename") or "")) or "") == self.repo_id
                and str(item.get("version") or item.get("zip_version") or "") == self.config.version
            )
        ]
        candidate = self._candidate_record(record, repo_candidate)
        tested = record.get("evidence", {}).get("TESTED_GREEN", {})
        if tested.get("ok") is True and tested.get("test_record_path"):
            candidate.update(
                {
                    "latest_test": {
                        "ok": True,
                        "status": "candidate_test_passed",
                        "record_path": tested.get("test_record_path"),
                        "tested_at": tested.get("finished_at") or tested.get("recorded_at"),
                        "adoption_performed": False,
                        "artifact_sha256": artifact.get("sha256"),
                        "release_attempt_id": self.attempt_id,
                    },
                    "tested": True,
                    "test_status": "candidate_test_passed",
                }
            )
        if STATE_INDEX.get(str(record.get("state") or ""), -1) >= STATE_INDEX["ACCEPTED"]:
            candidate.update({"accepted": True, "status": "accepted_candidate", "adoption_performed": True})
        candidates.append(candidate)
        registry["candidates"] = candidates
        path = _write_candidate_registry(self.config.profile_dir, registry)
        return {"ok": True, "status": "candidate_projection_reconstructed", "path": str(path), "candidate": candidate}

    def verify_record(self, record: dict[str, Any], *, repair_projections: bool) -> dict[str, Any]:
        state = str(record.get("state") or "")
        reached_index = STATE_INDEX.get(state, -1)
        results: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        projection_repair: dict[str, Any] | None = None

        for target in NORMAL_STATES:
            reached = reached_index >= STATE_INDEX[target]
            evidence = record.get("evidence", {}).get(target) if isinstance(record.get("evidence"), dict) else None
            checks: dict[str, bool] = {}
            details: dict[str, Any] = {}
            if not reached:
                results.append({"state": target, "reached": False, "verified": False, "checks": {}})
                continue
            if target == "DECLARED":
                checks = {
                    "schema_exact": record.get("schema") == SCHEMA,
                    "schema_version_exact": record.get("schema_version") == SCHEMA_VERSION,
                    "attempt_id_exact": record.get("attempt_id") == self.attempt_id,
                    "repo_id_exact": record.get("repo_id") == self.repo_id,
                    "target_version_exact": record.get("target_version") == self.config.version,
                    "baseline_version_exact": record.get("baseline_version") == self.config.baseline_version,
                    "target_is_legal_successor": _version_tuple(self.config.version) > _version_tuple(self.config.baseline_version),
                    "evidence_present": isinstance(evidence, dict),
                }
            elif target == "ARTIFACT_BOUND":
                artifact = record.get("artifact") if isinstance(record.get("artifact"), dict) else {}
                object_path = Path(str(artifact.get("object_path") or ""))
                checks = {
                    "evidence_present": isinstance(evidence, dict),
                    "object_exists": object_path.is_file(),
                    "sha256_exact": object_path.is_file() and sha256_file(object_path) == artifact.get("sha256"),
                    "size_exact": object_path.is_file() and object_path.stat().st_size == artifact.get("size_bytes"),
                    "embedded_version_exact": object_path.is_file() and _read_zip_version(object_path) == self.config.version,
                }
            elif target == "ARTIFACT_VERIFIED":
                artifact = record.get("artifact") if isinstance(record.get("artifact"), dict) else {}
                object_path = Path(str(artifact.get("object_path") or ""))
                verification = verify_zip_artifact(object_path) if object_path.is_file() else {"ok": False}
                if object_path.is_file():
                    with zipfile.ZipFile(object_path) as archive:
                        artifact_names = set(archive.namelist())
                else:
                    artifact_names = set()
                checks = {
                    "evidence_present": isinstance(evidence, dict),
                    "verification_recomputed_green": verification.get("ok") is True,
                    "sha256_exact": verification.get("sha256") == artifact.get("sha256"),
                    "entry_count_exact": verification.get("entry_count") == artifact.get("file_count"),
                    "no_nested_zip": int(verification.get("nested_zip_count") or 0) == 0,
                    "no_hygiene_violations": not verification.get("hygiene_violations"),
                    "required_root_entries_present": all(name in artifact_names for name in REQUIRED_ARTIFACT_ROOT_ENTRIES),
                }
                details["recomputed_verification"] = verification
            elif target == "CANDIDATE_REGISTERED":
                artifact = record.get("artifact") if isinstance(record.get("artifact"), dict) else {}
                registry = _load_candidate_registry(self.config.profile_dir)
                candidates = [item for item in registry.get("candidates", []) if isinstance(item, dict)]
                exact = [item for item in candidates if _candidate_matches(item, repo_id=self.repo_id, version=self.config.version, sha256=str(artifact.get("sha256") or ""))]
                conflicts = [item for item in candidates if _candidate_conflicts(item, repo_id=self.repo_id, version=self.config.version, sha256=str(artifact.get("sha256") or ""))]
                if reached and not exact and not conflicts and repair_projections:
                    projection_repair = self._reconstruct_candidate_projection(record)
                    registry = _load_candidate_registry(self.config.profile_dir)
                    candidates = [item for item in registry.get("candidates", []) if isinstance(item, dict)]
                    exact = [item for item in candidates if _candidate_matches(item, repo_id=self.repo_id, version=self.config.version, sha256=str(artifact.get("sha256") or ""))]
                checks = {"evidence_present": isinstance(evidence, dict),"exactly_one_candidate": len(exact) == 1,"no_conflicting_candidate": not conflicts,"candidate_verified": len(exact) == 1 and exact[0].get("verified") is True}
                expected_origin_url=str(self.config.artifact_conversation_url or "").strip()
                if expected_origin_url:
                    selected=exact[0].get("selected_protocol_reply") if len(exact)==1 and isinstance(exact[0].get("selected_protocol_reply"),dict) else {}
                    checks["artifact_conversation_provenance_exact"]=(selected.get("conversation_url")==expected_origin_url and selected.get("conversation_id")==_conversation_id_from_url(expected_origin_url))
                details.update({"exact_match_count": len(exact), "conflict_count": len(conflicts)})
            elif target == "RUNTIME_PREPARED":
                runtime = evidence if isinstance(evidence, dict) else {}
                extracted = Path(str(runtime.get("extraction_path") or ""))
                version_file = extracted / "VERSION"
                isolated = runtime.get("isolated_environment") if isinstance(runtime.get("isolated_environment"), dict) else {}
                required_isolation = {
                    "PYTHONPYCACHEPREFIX",
                    "PROMPTBRANCH_PROJECT_STATE_HOME",
                    "PROMPTBRANCH_PROJECT_CONFIG_HOME",
                    "XDG_STATE_HOME",
                    "XDG_CONFIG_HOME",
                    "HOME",
                }
                isolation_paths = [Path(str(isolated.get(name) or "")) for name in required_isolation]
                runtime_phases = [str(item) for item in runtime.get("runtime_phases", [])]
                completed_runtime_phases = [str(item) for item in runtime.get("completed_runtime_phases", [])]
                checkpoint_path = Path(str(runtime.get("runtime_checkpoint_path") or ""))
                checkpoint = _read_json(checkpoint_path) if checkpoint_path.is_file() else {}
                projected_source_fingerprint = str(runtime.get("source_fingerprint") or "")
                checkpoint_source_fingerprint = str(checkpoint.get("source_fingerprint") or "")
                candidate_port = int(runtime.get("candidate_service_port") or 0)
                candidate_project = str(runtime.get("candidate_compose_project") or "")
                candidate_base = str(runtime.get("candidate_service_base_url") or "")
                phase_evidence = checkpoint.get("phase_evidence") if isinstance(checkpoint.get("phase_evidence"), dict) else {}
                health_phase = phase_evidence.get("candidate_health_verified") if isinstance(phase_evidence.get("candidate_health_verified"), dict) else {}
                identity_phase = phase_evidence.get("candidate_identity_verified") if isinstance(phase_evidence.get("candidate_identity_verified"), dict) else {}
                recorded_health = health_phase.get("health") if isinstance(health_phase.get("health"), dict) else {}
                identity_checks = identity_phase.get("checks") if isinstance(identity_phase.get("checks"), dict) else {}
                required_identity_checks = {
                    "candidate_health_version_exact",
                    "candidate_health_ok",
                    "candidate_container_present",
                    "image_version_label_exact",
                    "image_artifact_sha_label_exact",
                    "image_source_fingerprint_label_exact",
                    "image_attempt_id_label_exact",
                    "container_compose_project_exact",
                    "accepted_runtime_before_exact",
                    "accepted_runtime_after_exact",
                    "accepted_runtime_unchanged",
                    "candidate_port_isolated",
                }
                recorded_candidate_health_exact = (
                    recorded_health.get("ok") is True
                    and str(recorded_health.get("version") or "") == self.config.version.removeprefix("v")
                )
                recorded_candidate_identity_exact = required_identity_checks.issubset(identity_checks) and all(
                    identity_checks.get(name) is True for name in required_identity_checks
                )
                post_adoption = reached_index >= STATE_INDEX["ADOPTED_CURRENT"]
                live_health: dict[str, Any] = {}
                live_health_error: str | None = None
                if not post_adoption and candidate_base and hasattr(self.executor, "_http_json"):
                    live_health, live_health_error = self.executor._http_json(candidate_base + "/healthz")  # type: ignore[attr-defined]
                accepted_before = runtime.get("accepted_runtime_before") if isinstance(runtime.get("accepted_runtime_before"), dict) else {}
                accepted_after = runtime.get("accepted_runtime_after") if isinstance(runtime.get("accepted_runtime_after"), dict) else {}
                accepted_preservation = _accepted_runtime_preservation_checks(
                    accepted_before,
                    accepted_after,
                    expected_version=self.config.baseline_version.removeprefix("v"),
                )
                checks = {
                    "evidence_present": isinstance(evidence, dict),
                    "extraction_present": extracted.is_dir(),
                    "version_exact": version_file.is_file() and version_file.read_text(encoding="utf-8").strip() == self.config.version,
                    "candidate_package_version_exact": runtime.get("candidate_package_version") == self.config.version.removeprefix("v"),
                    "candidate_cli_version_exact": runtime.get("candidate_cli_version") == self.config.version.removeprefix("v"),
                    "service_version_exact": runtime.get("service_version") == self.config.version.removeprefix("v"),
                    "candidate_python_explicit": bool(runtime.get("candidate_python")),
                    "pytest_version_explicit": bool(runtime.get("candidate_pytest_version")),
                    "pytest_version_exact": str(runtime.get("candidate_pytest_version") or "") == REQUIRED_PYTEST_VERSION,
                    "isolated_environment_present": required_isolation.issubset(isolated),
                    "isolation_paths_under_attempt": all(path.is_relative_to(self.attempt_dir) for path in isolation_paths),
                    "runtime_checkpoint_present": checkpoint_path.is_file(),
                    "runtime_checkpoint_identity_exact": checkpoint.get("attempt_id") == self.attempt_id and checkpoint.get("artifact_sha256") == record.get("artifact", {}).get("sha256"),
                    "runtime_source_fingerprint_projected_exact": bool(checkpoint_source_fingerprint) and projected_source_fingerprint == checkpoint_source_fingerprint,
                    "runtime_phases_complete": bool(runtime_phases) and completed_runtime_phases == runtime_phases,
                    "candidate_port_isolated": candidate_port > 0 and candidate_port != 8000,
                    "candidate_compose_project_isolated": bool(candidate_project) and candidate_project != "chatgpt_claudecode_workflow",
                    "accepted_runtime_before_exact": accepted_preservation["accepted_runtime_before_exact"],
                    "accepted_runtime_after_exact": accepted_preservation["accepted_runtime_after_exact"],
                    "accepted_runtime_unchanged": accepted_preservation["accepted_runtime_unchanged"],
                    "recorded_candidate_health_exact": recorded_candidate_health_exact,
                    "recorded_candidate_identity_exact": recorded_candidate_identity_exact,
                }
                if post_adoption:
                    adopted = record.get("evidence", {}).get("ADOPTED_CURRENT", {}) if isinstance(record.get("evidence"), dict) else {}
                    promotion = adopted.get("promotion") if isinstance(adopted.get("promotion"), dict) else {}
                    cleanup = adopted.get("candidate_runtime_cleanup") if isinstance(adopted.get("candidate_runtime_cleanup"), dict) else {}
                    candidate_image_id = str(promotion.get("candidate_image_id") or "").strip()
                    production_image_id = str(promotion.get("production_image_id") or "").strip()
                    checks.update(
                        {
                            "candidate_retired_after_adoption": adopted.get("ok") is True and cleanup.get("ok") is True,
                            "tested_image_promoted_exact": (
                                promotion.get("ok") is True
                                and promotion.get("tested_image_identity_exact") is True
                                and bool(candidate_image_id)
                                and candidate_image_id == production_image_id
                            ),
                        }
                    )
                    details["candidate_verification_mode"] = "historical_after_adoption"
                    details["candidate_retirement"] = {
                        "cleanup_status": cleanup.get("status"),
                        "candidate_image_id": candidate_image_id,
                        "production_image_id": production_image_id,
                    }
                else:
                    checks["live_candidate_health_exact"] = (
                        bool(candidate_base)
                        and live_health.get("ok") is True
                        and str(live_health.get("version") or "") == self.config.version.removeprefix("v")
                    )
                    details["candidate_verification_mode"] = "live_before_adoption"
                    details["live_candidate_health"] = live_health
                    details["live_candidate_health_error"] = live_health_error
                details["runtime_checkpoint"] = checkpoint
            elif target == "TESTED_GREEN":
                tested = evidence if isinstance(evidence, dict) else {}
                test_path = Path(str(tested.get("test_record_path") or ""))
                test_record = _read_json(test_path) if test_path.is_file() else {}
                result = test_record.get("result") if isinstance(test_record.get("result"), dict) else {}
                checks = {
                    "evidence_present": isinstance(evidence, dict),
                    "evidence_ok": tested.get("ok") is True,
                    "test_record_present": test_path.is_file(),
                    "test_record_green": result.get("ok") is True and result.get("status") == "candidate_test_passed",
                    "test_record_sha_exact": result.get("artifact_sha256") == record.get("artifact", {}).get("sha256"),
                    "profile_exact": result.get("profile") == self.config.profile,
                    "attempt_id_exact": result.get("state_machine_attempt_id") == self.attempt_id,
                    "detail_sha_exact": isinstance(result.get("detail"), dict) and result["detail"].get("artifact_sha256") == record.get("artifact", {}).get("sha256"),
                    "detail_python_explicit": isinstance(result.get("detail"), dict) and bool(result["detail"].get("candidate_python")),
                    "detail_pytest_exact": isinstance(result.get("detail"), dict) and str(result["detail"].get("candidate_pytest_version") or "") == REQUIRED_PYTEST_VERSION,
                    "failed_count_zero": isinstance(result.get("detail"), dict) and int(result["detail"].get("failed") or 0) == 0,
                    "required_skips_zero": isinstance(result.get("detail"), dict) and int(result["detail"].get("skipped") or 0) == 0,
                }
            elif target == "ACCEPTED":
                accepted = evidence if isinstance(evidence, dict) else {}
                mutation_policy = record.get("request", {}).get("mutation_policy", {}) if isinstance(record.get("request"), dict) else {}
                accepted_guards = accepted.get("guards") if isinstance(accepted.get("guards"), dict) else {}
                artifact = record.get("artifact") if isinstance(record.get("artifact"), dict) else {}
                registry = _load_candidate_registry(self.config.profile_dir)
                candidates = [item for item in registry.get("candidates", []) if isinstance(item, dict)]
                exact = [item for item in candidates if _candidate_matches(item, repo_id=self.repo_id, version=self.config.version, sha256=str(artifact.get("sha256") or ""))]
                checks = {
                    "evidence_present": isinstance(evidence, dict),
                    "acceptance_ok": accepted.get("ok") is True,
                    "explicit_adoption_authorized": bool(mutation_policy.get("adopt") or accepted_guards.get("adoption_explicitly_authorized")),
                    "exactly_one_accepted_candidate": len(exact) == 1 and exact[0].get("accepted") is True and exact[0].get("adoption_performed") is True,
                }
            elif target == "ADOPTED_CURRENT":
                adopted = evidence if isinstance(evidence, dict) else {}
                current_probe = self.executor.current_status(self, record) if reached else {"ok": False, "result": {}}
                current_payload = current_probe.get("result") if isinstance(current_probe.get("result"), dict) else {}
                alignment = _current_candidate_alignment_checks(
                    current_payload,
                    repo_id=self.repo_id,
                    filename=str(record.get("artifact", {}).get("filename") or ""),
                    version=self.config.version,
                    sha256=str(record.get("artifact", {}).get("sha256") or ""),
                )
                production_probe = self.executor.authoritative_runtime_status(self, record) if reached else {"ok": False}
                cleanup = adopted.get("candidate_runtime_cleanup") if isinstance(adopted.get("candidate_runtime_cleanup"), dict) else {}
                checks = {"evidence_present": isinstance(evidence, dict),"current_alignment_ok": adopted.get("ok") is True,"current_probe_ok": current_probe.get("ok") is True,"authoritative_runtime_exact": production_probe.get("ok") is True,"candidate_runtime_cleanup_ok": cleanup.get("ok") is True,**alignment}
                expected_origin_url=str(self.config.artifact_conversation_url or "").strip()
                if expected_origin_url:
                    repos=current_payload.get("repos") if isinstance(current_payload.get("repos"),dict) else {}; repo_payload=repos.get(self.repo_id) if isinstance(repos.get(self.repo_id),dict) else {}; current_record=repo_payload.get("registry_current") if isinstance(repo_payload.get("registry_current"),dict) else {}
                    checks["registry_origin_conversation_exact"]=(current_record.get("origin_conversation_url")==expected_origin_url and current_record.get("origin_conversation_id")==_conversation_id_from_url(expected_origin_url))
                details["current_probe"] = current_probe
                details["authoritative_runtime_probe"] = production_probe
            elif target == "FINAL_VERIFIED":
                final = evidence if isinstance(evidence, dict) else {}
                production_probe = self.executor.authoritative_runtime_status(self, record) if reached else {"ok": False}
                checks = {
                    "evidence_present": isinstance(evidence, dict),
                    "final_evidence_ok": final.get("ok") is True,
                    "lifecycle_complete": record.get("lifecycle_complete") is True,
                    "next_transition_none": record.get("next_transition") is None,
                    "authoritative_runtime_exact": production_probe.get("ok") is True,
                }
                details["authoritative_runtime_probe"] = production_probe
            verified = (not reached) or all(checks.values())
            item = {
                "state": target,
                "reached": reached,
                "verified": verified if reached else False,
                "checks": checks,
                **details,
            }
            results.append(item)
            if reached and not verified:
                failed.append({"state": target, "failed_checks": [key for key, value in checks.items() if not value]})

        return {
            "ok": not failed,
            "action": ACTION_VERIFY,
            "attempt_id": self.attempt_id,
            "attempt_path": str(self.attempt_path),
            "version": self.config.version,
            "current_state": state,
            "failure_state": record.get("failure_state"),
            "states": results,
            "all_reached_states_verified": not failed,
            "failed_invariants": failed,
            "next_transition": LEGAL_TRANSITIONS.get(state),
            "lifecycle_complete": state == "FINAL_VERIFIED" and not failed,
            "projection_repair": projection_repair,
            "mutation_performed": bool(projection_repair and projection_repair.get("ok")),
        }

    def verify(self, *, repair_projections: bool = True) -> tuple[dict[str, Any], int]:
        if not self.attempt_path.is_file():
            return {
                "ok": False,
                "action": ACTION_VERIFY,
                "status": "attempt_not_found",
                "attempt_path": str(self.attempt_path),
                "version": self.config.version,
            }, 2
        record = _read_json(self.attempt_path)
        self._validate_record_identity(record)
        payload = self.verify_record(record, repair_projections=repair_projections)
        return payload, 0 if payload.get("ok") else 1

    def force_transition_for_test(self, destination: str) -> tuple[dict[str, Any], int]:
        """Test-only public contract for proving illegal-transition rejection."""
        record = self.load_or_create()
        try:
            return self._transition(record, canonical_state(destination), lambda _: {"ok": True}), 0
        except TransitionBlocked as exc:
            return {
                "ok": False,
                "status": "illegal_transition",
                "failure_code": exc.code,
                "current_state": record.get("state"),
                "requested_state": canonical_state(destination),
                "required_next_transition": LEGAL_TRANSITIONS.get(str(record.get("state") or "")),
                "mutation_performed": False,
            }, 1


def build_machine_from_args(
    *,
    repo_root: str | Path,
    profile_dir: str | Path,
    artifact: str | Path,
    version: str,
    baseline_version: str,
    release_type: str = "repair",
    profile: str = "full",
    test_timeout: float = 3600.0,
    until: str = "TESTED_GREEN",
    adopt: bool = False,
    commit: bool = False,
    push: bool = False,
    upload_project_source: bool = False,
    candidate_python: str | None = None,
    artifact_conversation_url: str | None = None,
    executor: ReleaseExecutor | None = None,
) -> ReleaseStateMachine:
    return ReleaseStateMachine(
        ReleaseStateMachineConfig(
            repo_root=Path(repo_root),
            profile_dir=Path(profile_dir),
            artifact=Path(artifact),
            version=version,
            baseline_version=baseline_version,
            release_type=release_type,
            profile=profile,
            test_timeout=test_timeout,
            until=until,
            adopt=adopt,
            commit=commit,
            push=push,
            upload_project_source=upload_project_source,
            candidate_python=candidate_python,
            artifact_conversation_url=artifact_conversation_url,
        ),
        executor=executor,
    )

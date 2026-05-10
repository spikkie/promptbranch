from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import subprocess
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

VERSION_PATTERN = r"^v?\d+(?:\.\d+)*(?:[-+][0-9A-Za-z][0-9A-Za-z.-]*)?$"
ARTIFACT_REGISTRY_NAME = "promptbranch_artifacts.json"
ARTIFACT_DIR_NAME = "artifacts"

DEFAULT_EXCLUDE_PATTERNS: tuple[str, ...] = (
    ".git/",
    ".pb_profile/",
    "profile/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.zip",
    "*.tar.gz",
    "*.log",
    "*.log.*",
    "*.json.log",
    ".promptbranch-service-start.*.pid",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "node_modules/",
    "dist/",
    "build/",
    "coverage/",
    ".venv/",
    "venv/",
    "env/",
    ".env",
    ".env.*",
    ".DS_Store",
    "debug_projects_popup_*/",
    "task_*.messages",
    "task_*.messages.txt",
    "task_*_message.txt",
    "task_show_*_messages.txt",
    "task_*_final.txt",
    "session_*.log",
    "stdout.json",
    "stderr.txt",
    "pb_*.json",
    "pb_*.report.json",
    "promptbranch-project-list.json",
)

DISALLOWED_RELEASE_ENTRY_PATTERNS: tuple[str, ...] = (
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "*.zip",
    "*.tar.gz",
    "*.log",
    "*.log.*",
    "*.json.log",
    ".promptbranch-service-start.*.pid",
    "debug_projects_popup_*/",
    "task_*.messages",
    "task_*.messages.txt",
    "task_*_message.txt",
    "task_show_*_messages.txt",
    "task_*_final.txt",
    "session_*.log",
    "stdout.json",
    "stderr.txt",
    "pb_*.json",
    "pb_*.report.json",
    "promptbranch-project-list.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def valid_version_text(value: str | None) -> bool:
    import re

    return bool(value and re.fullmatch(VERSION_PATTERN, value.strip()))


def read_version(repo_path: str | Path) -> str | None:
    version_file = Path(repo_path) / "VERSION"
    if not version_file.is_file():
        return None
    try:
        value = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value if valid_version_text(value) else None


def git_short_sha(repo_path: str | Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value or None


def _normalize_project_name(path: Path) -> str:
    return path.resolve().name.replace(" ", "_")


def default_artifact_filename(repo_path: str | Path) -> tuple[str, str | None]:
    root = Path(repo_path).resolve()
    name = _normalize_project_name(root)
    version = read_version(root)
    if version:
        return f"{name}_{version}.zip", version
    sha = git_short_sha(root) or "snapshot"
    return f"{name}-{sha}.zip", None


def _load_not_to_zip_patterns(root: Path) -> list[str]:
    patterns = list(DEFAULT_EXCLUDE_PATTERNS)
    for filename in (".not_to_zip",):
        path = root / filename
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Keep ignore semantics intentionally conservative. Negated rules are not
            # implemented because packaging must avoid accidental inclusion of secrets.
            if line.startswith("!"):
                continue
            patterns.append(line)
    return patterns


def _matches_pattern(rel: str, pattern: str, *, is_dir: bool) -> bool:
    rel = rel.strip("/")
    pat = pattern.strip()
    if not pat:
        return False
    directory_only = pat.endswith("/")
    pat = pat.strip("/")
    if directory_only and not is_dir and not rel.startswith(pat + "/"):
        return False
    candidates = {rel, Path(rel).name}
    if is_dir:
        candidates.add(rel + "/")
    return any(fnmatch.fnmatch(candidate, pat) for candidate in candidates) or fnmatch.fnmatch(rel, pat) or rel.startswith(pat + "/")


def should_exclude(root: Path, path: Path, patterns: Iterable[str]) -> bool:
    rel = path.relative_to(root).as_posix()
    is_dir = path.is_dir()
    parts = rel.split("/")
    for idx in range(1, len(parts) + 1):
        candidate = "/".join(parts[:idx])
        candidate_path = root / candidate
        candidate_is_dir = idx < len(parts) or candidate_path.is_dir()
        if any(_matches_pattern(candidate, pattern, is_dir=candidate_is_dir) for pattern in patterns):
            return True
    return False


def release_entry_hygiene_violations(names: Iterable[str]) -> list[str]:
    """Return generated/local entries that must not appear in release ZIPs."""

    bad: list[str] = []
    for name in names:
        rel = str(name or "").strip("/")
        if not rel:
            continue
        parts = rel.split("/")
        matched = False
        for idx in range(1, len(parts) + 1):
            candidate = "/".join(parts[:idx])
            candidate_is_dir = idx < len(parts)
            if any(_matches_pattern(candidate, pattern, is_dir=candidate_is_dir) for pattern in DISALLOWED_RELEASE_ENTRY_PATTERNS):
                matched = True
                break
        if matched or any(_matches_pattern(rel, pattern, is_dir=False) for pattern in DISALLOWED_RELEASE_ENTRY_PATTERNS):
            bad.append(name)
    return sorted(set(bad))


def iter_repo_files(repo_path: str | Path) -> list[Path]:
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"repo path is not a directory: {repo_path}")
    patterns = _load_not_to_zip_patterns(root)
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            child = current / dirname
            if not should_exclude(root, child, patterns):
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in sorted(filenames):
            path = current / filename
            if should_exclude(root, path, patterns):
                continue
            files.append(path)
    files.sort(key=lambda item: item.relative_to(root).as_posix())
    return files


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class ArtifactRecord:
    path: str
    filename: str
    kind: str
    version: str | None
    repo_path: str | None
    sha256: str
    size_bytes: int
    file_count: int
    created_at: str
    source_ref: str | None = None
    project_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArtifactRegistry:
    def __init__(self, profile_dir: str | Path) -> None:
        base = Path(profile_dir).expanduser()
        self.profile_dir = base
        self.path = base / ARTIFACT_REGISTRY_NAME
        self.artifact_dir = base / ARTIFACT_DIR_NAME

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "artifacts": []}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": 1, "artifacts": []}
        if not isinstance(payload, dict):
            return {"schema_version": 1, "artifacts": []}
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, list):
            payload["artifacts"] = []
        payload.setdefault("schema_version", 1)
        return payload

    def list(self) -> list[dict[str, Any]]:
        artifacts = self.load().get("artifacts")
        return [item for item in artifacts if isinstance(item, dict)] if isinstance(artifacts, list) else []

    def add(self, record: ArtifactRecord) -> dict[str, Any]:
        payload = self.load()
        artifacts = [item for item in payload.get("artifacts", []) if isinstance(item, dict)]
        record_payload = record.to_dict()
        artifacts = [item for item in artifacts if item.get("path") != record.path]
        artifacts.append(record_payload)
        artifacts.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        payload["schema_version"] = 1
        payload["updated_at"] = utc_now()
        payload["artifacts"] = artifacts
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return record_payload

    def current(self) -> dict[str, Any] | None:
        artifacts = self.list()
        return artifacts[0] if artifacts else None




def plan_repo_snapshot(
    repo_path: str | Path,
    *,
    output_dir: str | Path,
    filename: str | None = None,
    kind: str = "source_snapshot",
    sample_limit: int = 25,
) -> tuple[dict[str, Any], list[str]]:
    """Build a non-mutating repo snapshot plan.

    This is intentionally side-effect free: it does not create the output
    directory, write a ZIP, update the artifact registry, or upload anything to
    ChatGPT. It reuses the same inclusion/exclusion rules as
    ``create_repo_snapshot`` so operators can inspect the exact file set before
    allowing a transactional source sync.
    """
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"repo path is not a directory: {repo_path}")
    default_name, version = default_artifact_filename(root)
    artifact_name = filename or default_name
    if not artifact_name.endswith(".zip"):
        artifact_name += ".zip"
    out_dir = Path(output_dir).expanduser().resolve()
    out_path = out_dir / Path(artifact_name).name
    files = [path.relative_to(root).as_posix() for path in iter_repo_files(root)]
    plan = {
        "kind": kind,
        "repo_path": str(root),
        "filename": out_path.name,
        "path": str(out_path),
        "version": version,
        "file_count": len(files),
        "included_count": len(files),
        "included_sample": files[: max(0, sample_limit)],
        "included_sample_truncated": len(files) > max(0, sample_limit),
        "has_version_file": "VERSION" in files,
        "would_write_zip": True,
        "would_update_artifact_registry": True,
        "would_upload_source": True,
    }
    return plan, files



def _all_repo_file_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        for filename in sorted(filenames):
            candidates.append(current / filename)
    candidates.sort(key=lambda item: item.relative_to(root).as_posix())
    return candidates


def repo_manifest_fingerprint(root: Path, included_paths: Iterable[str]) -> dict[str, Any]:
    """Return a content-bound, deterministic fingerprint for a planned repo snapshot.

    Upload confirmation tokens must become stale if the operator changes a file
    after reviewing the preflight.  Counting files is not enough: content can
    change without changing the file set.  This manifest hashes each included
    file path, size, and SHA-256 in stable order, without writing artifacts.
    """
    digest = hashlib.sha256()
    file_count = 0
    total_size = 0
    sample: list[dict[str, Any]] = []
    for rel in sorted(str(path).strip("/") for path in included_paths):
        if not rel:
            continue
        path = root / rel
        try:
            stat = path.stat()
            file_sha = sha256_file(path)
        except OSError as exc:
            file_sha = f"error:{type(exc).__name__}:{exc}"
            size = None
        else:
            size = int(stat.st_size)
            total_size += size
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_sha.encode("ascii", errors="replace"))
        digest.update(b"\n")
        file_count += 1
        if len(sample) < 10:
            sample.append({"path": rel, "size_bytes": size, "sha256": file_sha})
    return {
        "algorithm": "sha256-path-size-content-v1",
        "sha256": digest.hexdigest(),
        "file_count": file_count,
        "total_size_bytes": total_size,
        "sample": sample,
    }


def git_worktree_snapshot(repo_path: str | Path) -> dict[str, Any]:
    """Return a small read-only git/worktree snapshot for transaction preflights."""
    root = Path(repo_path).resolve()
    result: dict[str, Any] = {
        "repo_path": str(root),
        "git_available": False,
        "is_git_repo": False,
        "branch": None,
        "short_sha": None,
        "dirty": None,
        "status_count": 0,
        "status_sample": [],
    }
    try:
        status = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        result["error"] = str(exc)
        return result
    result["git_available"] = True
    if status.returncode != 0:
        result["error"] = (status.stderr or status.stdout or "git status failed").strip()
        return result
    result["is_git_repo"] = True
    lines = [line for line in status.stdout.splitlines() if line.strip()]
    branch_line = lines[0] if lines and lines[0].startswith("##") else None
    status_lines = lines[1:] if branch_line else lines
    if branch_line:
        branch_text = branch_line[2:].strip()
        result["branch"] = branch_text.split("...", 1)[0].strip() or branch_text
    result["short_sha"] = git_short_sha(root)
    result["dirty"] = bool(status_lines)
    result["status_count"] = len(status_lines)
    result["status_sample"] = status_lines[:20]
    return result


def build_source_sync_preflight(
    repo_path: str | Path,
    *,
    output_dir: str | Path,
    filename: str | None = None,
    profile_dir: str | Path | None = None,
    project_url: str | None = None,
    upload_requested: bool = True,
    sample_limit: int = 25,
) -> tuple[dict[str, Any], list[str]]:
    """Build a side-effect-free source-sync transaction preflight.

    The returned metadata is deliberately read-only. It describes the file set,
    current repo/artifact state, collateral-change risks, and the verification
    contract that a future mutating sync must satisfy before local state may be
    updated.
    """
    root = Path(repo_path).resolve()
    plan, included = plan_repo_snapshot(
        root,
        output_dir=output_dir,
        filename=filename,
        kind="source_snapshot",
        sample_limit=sample_limit,
    )
    patterns = _load_not_to_zip_patterns(root)
    candidates = _all_repo_file_candidates(root)
    included_set = set(included)
    excluded = [path.relative_to(root).as_posix() for path in candidates if path.relative_to(root).as_posix() not in included_set]
    manifest_fingerprint = repo_manifest_fingerprint(root, included)
    out_path = Path(plan["path"])
    registry_payload: dict[str, Any] = {"path": None, "exists": False, "current": None, "artifact_count": 0}
    registry_path_collision = False
    registry_filename_collision = False
    if profile_dir is not None:
        registry = ArtifactRegistry(profile_dir)
        current = registry.current()
        artifacts = registry.list()
        registry_payload = {
            "path": str(registry.path),
            "exists": registry.path.exists(),
            "current": current,
            "artifact_count": len(artifacts),
        }
        registry_path_collision = any(str(item.get("path") or "") == str(out_path) for item in artifacts)
        registry_filename_collision = any(str(item.get("filename") or "") == str(out_path.name) for item in artifacts)
    version = plan.get("version")
    preflight = {
        "repo_path_exists": root.is_dir(),
        "version_file_present": (root / "VERSION").is_file(),
        "version_valid": valid_version_text(version) if version is not None else False,
        "artifact_filename_safe": (Path(str(plan.get("filename") or "")).name == str(plan.get("filename") or "") and str(plan.get("filename") or "").endswith(".zip")),
        "output_dir_parent_exists": out_path.parent.parent.exists(),
        "workspace_selected": bool(project_url),
        "upload_requested": bool(upload_requested),
        "repo_snapshot_plan_built": True,
        "mutating_actions_executed": False,
    }
    collateral_checks = {
        "output_path_exists": out_path.exists(),
        "would_overwrite_artifact_file": out_path.exists(),
        "registry_path_collision": registry_path_collision,
        "registry_filename_collision": registry_filename_collision,
        "requires_before_after_source_snapshot": bool(upload_requested),
        "requires_collateral_source_change_detection": bool(upload_requested),
    }
    fingerprint_material = json.dumps(
        {
            "repo_path": str(root),
            "artifact_path": str(out_path),
            "version": version,
            "included_count": len(included),
            "repo_manifest_fingerprint": manifest_fingerprint.get("sha256"),
            "git_short_sha": (git_worktree_snapshot(root).get("short_sha") if root.is_dir() else None),
            "project_url": project_url,
            "upload_requested": bool(upload_requested),
        },
        sort_keys=True,
    ).encode("utf-8")
    transaction_id = hashlib.sha256(fingerprint_material).hexdigest()[:16]
    metadata = {
        "schema_version": 1,
        "transaction_id": transaction_id,
        "phase": "preflight",
        "risk": "write" if upload_requested else "local_write",
        "mutation_allowed": False,
        "mutating_actions_executed": False,
        "preflight": preflight,
        "before_snapshot": {
            "repo": {
                "path": str(root),
                "version": version,
                "git": git_worktree_snapshot(root),
                "content_fingerprint": manifest_fingerprint,
                "candidate_file_count": len(candidates),
                "included_count": len(included),
                "excluded_count": len(excluded),
                "excluded_sample": excluded[: max(0, sample_limit)],
                "exclude_pattern_count": len(patterns),
                "artifact_filename": str(plan.get("filename")),
                "artifact_path": str(plan.get("path")),
            },
            "artifact_registry": registry_payload,
            "workspace": {
                "project_url": project_url,
                "selected": bool(project_url),
            },
        },
        "collateral_checks": collateral_checks,
        "verification_plan": {
            "before": [
                "record artifact registry current entry",
                "record repo git/worktree snapshot",
                "record project source list before upload" if upload_requested else "project source list not required without upload",
            ],
            "commit_wait": [
                "source dialog closed",
                "sources surface idle",
                "add button visible",
                "stability dwell elapsed",
            ] if upload_requested else [],
            "after": [
                "artifact ZIP exists and sha256 is stable",
                "artifact registry contains new artifact record",
                "project source list contains uploaded source ref" if upload_requested else "no project source mutation expected",
                "no collateral source removals or replacements unless explicitly planned",
            ],
        },
    }
    return {**plan, "preflight": metadata}, included

def create_repo_snapshot(
    repo_path: str | Path,
    *,
    output_dir: str | Path,
    filename: str | None = None,
    kind: str = "source_snapshot",
) -> tuple[ArtifactRecord, list[str]]:
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"repo path is not a directory: {repo_path}")
    default_name, version = default_artifact_filename(root)
    artifact_name = filename or default_name
    if not artifact_name.endswith(".zip"):
        artifact_name += ".zip"
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / Path(artifact_name).name
    files = iter_repo_files(root)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
    record = ArtifactRecord(
        path=str(out_path),
        filename=out_path.name,
        kind=kind,
        version=version,
        repo_path=str(root),
        sha256=sha256_file(out_path),
        size_bytes=out_path.stat().st_size,
        file_count=len(files),
        created_at=utc_now(),
        source_ref=out_path.name,
    )
    return record, [path.relative_to(root).as_posix() for path in files]


def verify_zip_artifact(path: str | Path) -> dict[str, Any]:
    zip_path = Path(path).expanduser().resolve()
    if not zip_path.is_file():
        return {"ok": False, "error": "artifact_not_found", "path": str(zip_path)}
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            bad = archive.testzip()
    except zipfile.BadZipFile:
        return {"ok": False, "error": "bad_zip", "path": str(zip_path)}
    unsafe = [name for name in names if name.startswith("/") or ".." in Path(name).parts]
    hygiene_violations = release_entry_hygiene_violations(names)
    top_levels = {name.split("/", 1)[0] for name in names if name and not name.endswith("/")}
    wrapper_folder = None
    if len(top_levels) == 1 and not any("/" not in name.rstrip("/") for name in names if name and not name.endswith("/")):
        wrapper_folder = next(iter(top_levels))
    return {
        "ok": bad is None and not unsafe and wrapper_folder is None and not hygiene_violations,
        "path": str(zip_path),
        "filename": zip_path.name,
        "sha256": sha256_file(zip_path),
        "size_bytes": zip_path.stat().st_size,
        "entry_count": len(names),
        "has_version_file": "VERSION" in names,
        "bad_entry": bad,
        "unsafe_entries": unsafe,
        "hygiene_violations": hygiene_violations,
        "hygiene_violation_count": len(hygiene_violations),
        "wrapper_folder": wrapper_folder,
    }

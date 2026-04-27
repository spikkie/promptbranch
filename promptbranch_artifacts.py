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
    top_levels = {name.split("/", 1)[0] for name in names if name and not name.endswith("/")}
    wrapper_folder = None
    if len(top_levels) == 1 and not any("/" not in name.rstrip("/") for name in names if name and not name.endswith("/")):
        wrapper_folder = next(iter(top_levels))
    return {
        "ok": bad is None and not unsafe and wrapper_folder is None,
        "path": str(zip_path),
        "filename": zip_path.name,
        "sha256": sha256_file(zip_path),
        "size_bytes": zip_path.stat().st_size,
        "entry_count": len(names),
        "has_version_file": "VERSION" in names,
        "bad_entry": bad,
        "unsafe_entries": unsafe,
        "wrapper_folder": wrapper_folder,
    }

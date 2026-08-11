from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

VERSION_PATTERN = r"^v?\d+(?:\.\d+)*(?:[-+][0-9A-Za-z][0-9A-Za-z.-]*)?$"
ARTIFACT_REGISTRY_NAME = "promptbranch_artifacts.json"
ARTIFACT_DIR_NAME = "artifacts"
ARTIFACT_OBJECT_DIR_NAME = "objects"
RELEASE_IDENTITY_KINDS = frozenset({"release", "adopted_release"})

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
    "*.task.show",
    "task_*.show",
    "task_*_final.txt",
    "session_*.log",
    "stdout.json",
    "stderr.txt",
    "pb_*.json",
    "pb_*.report.json",
    "promptbranch-project-list.json",
    "release_logs/",
)

DISALLOWED_RELEASE_ENTRY_PATTERNS: tuple[str, ...] = (
    ".pb_profile/",
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
    "*.task.show",
    "task_*.show",
    "task_*_final.txt",
    "session_*.log",
    "stdout.json",
    "stderr.txt",
    "pb_*.json",
    "pb_*.report.json",
    "promptbranch-project-list.json",
    "release_logs/",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")



CANONICAL_ARTIFACT_VERSION_RE = re.compile(r"^v\d+(?:\.\d+){2,}$")
CANONICAL_ARTIFACT_FILENAME_RE = re.compile(
    r"^(?P<repo_id>[A-Za-z0-9][A-Za-z0-9_-]*)_(?P<version>v\d+(?:\.\d+){2,})\.zip$"
)


def canonical_version_tag(value: str | None) -> str | None:
    """Return the canonical artifact filename version token.

    Artifact filenames use exactly one leading ``v`` and at least three
    numeric components, for example ``v0.1.72`` or ``v0.19.5.94.1``.
    Internal repo version files may omit the ``v``; filename grammar may not.
    """

    text = str(value or "").strip()
    if not text:
        return None
    while text.lower().startswith("v"):
        text = text[1:]
    candidate = f"v{text}"
    return candidate if CANONICAL_ARTIFACT_VERSION_RE.fullmatch(candidate) else None


def parse_canonical_artifact_filename(filename: str | None) -> dict[str, str] | None:
    """Parse the canonical Promptbranch artifact filename grammar.

    Canonical grammar::

        <repo_id>_<version>.zip

    where ``version`` is a v-prefixed dot-separated numeric token.
    """

    value = Path(str(filename or "")).name.strip()
    match = CANONICAL_ARTIFACT_FILENAME_RE.fullmatch(value)
    if not match:
        return None
    return {"repo_id": match.group("repo_id"), "version": match.group("version")}


def canonical_artifact_filename(repo_id: str, version: str) -> str | None:
    normalized_repo = normalize_repo_id(repo_id)
    normalized_version = canonical_version_tag(version)
    if not normalized_repo or not normalized_version:
        return None
    return f"{normalized_repo}_{normalized_version}.zip"


def infer_repo_id_from_artifact_filename(filename: str | None) -> str | None:
    """Return the explicit repository identifier from a canonical artifact name."""

    parsed = parse_canonical_artifact_filename(filename)
    return parsed["repo_id"] if parsed else None


def normalize_repo_id(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    return Path(candidate).name.replace(" ", "_")


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


_SENSITIVE_PROMPTBRANCH_REPO_KEYS = {
    "api_key",
    "access_token",
    "auth_token",
    "cookie",
    "cookies",
    "password",
    "refresh_token",
    "secret",
    "session",
    "session_id",
    "token",
}


def _looks_like_local_absolute_path(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if re.match(r"^[A-Za-z]:\\", text):
        return True
    if not text.startswith("/"):
        return False
    first = text.strip("/").split("/", 1)[0]
    return first in {"home", "mnt", "tmp", "Users", "var", "private", "run", "Volumes"}


def _promptbranch_repo_manifest_violations_from_value(value: Any, *, path: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _SENSITIVE_PROMPTBRANCH_REPO_KEYS and item not in (None, "", [], {}):
                violations.append(f".promptbranch-repo.json:{child_path}:sensitive_field")
            violations.extend(_promptbranch_repo_manifest_violations_from_value(item, path=child_path))
        return violations
    if isinstance(value, list):
        for idx, item in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            violations.extend(_promptbranch_repo_manifest_violations_from_value(item, path=child_path))
        return violations
    if isinstance(value, str):
        lowered = value.lower()
        if _looks_like_local_absolute_path(value):
            violations.append(f".promptbranch-repo.json:{path}:local_absolute_path")
        if ".pb_profile" in lowered or ".local/state/promptbranch" in lowered or ".config/promptbranch" in lowered:
            violations.append(f".promptbranch-repo.json:{path}:local_promptbranch_state_path")
    return violations


def promptbranch_repo_manifest_violations_from_zip(archive: zipfile.ZipFile) -> list[str]:
    """Validate that .promptbranch-repo.json is portable repo identity only.

    The repo identity manifest is allowed in release ZIPs.  It must not become
    a carrier for local runtime state, tokens, machine paths, or Promptbranch
    profile/state locations.
    """

    names = set(archive.namelist())
    if ".promptbranch-repo.json" not in names:
        return []
    try:
        raw = archive.read(".promptbranch-repo.json").decode("utf-8", errors="replace")
    except (KeyError, OSError):
        return [".promptbranch-repo.json:unreadable"]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return [".promptbranch-repo.json:invalid_json"]
    if not isinstance(payload, dict):
        return [".promptbranch-repo.json:not_object"]
    return sorted(set(_promptbranch_repo_manifest_violations_from_value(payload)))


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
    repo_id: str | None = None
    source_requested_ref: str | None = None
    source_processed_file_id: str | None = None
    source_library_metadata_object_id: str | None = None
    origin_conversation_url: str | None = None
    origin_conversation_id: str | None = None
    origin_request_id: str | None = None
    origin_correlation_id: str | None = None
    origin_message_id: str | None = None
    origin_answer_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArtifactIdentityConflictError(RuntimeError):
    def __init__(self, *, repo_id: str, version: str, existing_sha256: str, candidate_sha256: str) -> None:
        self.repo_id = repo_id
        self.version = version
        self.existing_sha256 = existing_sha256
        self.candidate_sha256 = candidate_sha256
        super().__init__(f"immutable release identity conflict for {repo_id} {version}: {existing_sha256} != {candidate_sha256}")

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "immutable_release_identity_conflict",
            "repo_id": self.repo_id,
            "version": self.version,
            "existing_sha256": self.existing_sha256,
            "candidate_sha256": self.candidate_sha256,
            "mutation_performed": False,
        }


class ArtifactRegistryStateError(RuntimeError):
    def __init__(
        self,
        status: str,
        path: str | Path,
        *,
        registry_exists: bool,
        registry_valid: bool,
        registry_readable: bool,
        error: str | None = None,
    ) -> None:
        self.status = status
        self.path = Path(path).expanduser()
        self.registry_exists = registry_exists
        self.registry_valid = registry_valid
        self.registry_readable = registry_readable
        self.error = error or status
        super().__init__(self.error)

    def to_payload(self, *, action: str = "artifact_registry") -> dict[str, Any]:
        return {
            "ok": False,
            "action": action,
            "status": self.status,
            "registry_source": "project_registry",
            "registry_file": str(self.path),
            "registry_exists": self.registry_exists,
            "registry_valid": self.registry_valid,
            "registry_readable": self.registry_readable,
            "fallback_used": False,
            "error": self.error,
        }


class ArtifactRegistry:
    def __init__(self, profile_dir: str | Path) -> None:
        base = Path(profile_dir).expanduser()
        self.profile_dir = base
        self.path = base / ARTIFACT_REGISTRY_NAME
        self.artifact_dir = base / ARTIFACT_DIR_NAME
        self.object_dir = base / ARTIFACT_OBJECT_DIR_NAME

    def inspect(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "ok": False,
                "status": "artifact_registry_missing",
                "registry_file": str(self.path),
                "registry_exists": False,
                "registry_valid": False,
                "registry_readable": False,
                "payload": None,
                "error": f"artifact registry does not exist: {self.path}",
            }
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            return {
                "ok": False,
                "status": "artifact_registry_unreadable",
                "registry_file": str(self.path),
                "registry_exists": True,
                "registry_valid": False,
                "registry_readable": False,
                "payload": None,
                "error": f"artifact registry is unreadable: {exc}",
            }
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "status": "artifact_registry_invalid",
                "registry_file": str(self.path),
                "registry_exists": True,
                "registry_valid": False,
                "registry_readable": True,
                "payload": None,
                "error": f"artifact registry contains invalid JSON: {exc}",
            }
        if not isinstance(payload, dict) or int(payload.get("schema_version") or 0) != 1 or not isinstance(payload.get("artifacts"), list):
            return {
                "ok": False,
                "status": "artifact_registry_invalid",
                "registry_file": str(self.path),
                "registry_exists": True,
                "registry_valid": False,
                "registry_readable": True,
                "payload": None,
                "error": "artifact registry must be a schema_version=1 JSON object with an artifacts array",
            }
        for index, item in enumerate(payload["artifacts"]):
            error = self._record_validation_error(item)
            if error:
                return {
                    "ok": False,
                    "status": "artifact_registry_invalid",
                    "registry_file": str(self.path),
                    "registry_exists": True,
                    "registry_valid": False,
                    "registry_readable": True,
                    "payload": None,
                    "error": f"artifact registry record {index} is invalid: {error}",
                }
        return {
            "ok": True,
            "status": "artifact_registry_empty" if not payload["artifacts"] else "artifact_registry_loaded",
            "registry_file": str(self.path),
            "registry_exists": True,
            "registry_valid": True,
            "registry_readable": True,
            "payload": payload,
            "error": None,
        }

    def initialize(self) -> dict[str, Any]:
        if self.path.exists():
            state = self.inspect()
            if not state["ok"]:
                raise ArtifactRegistryStateError(
                    state["status"],
                    self.path,
                    registry_exists=bool(state["registry_exists"]),
                    registry_valid=bool(state["registry_valid"]),
                    registry_readable=bool(state["registry_readable"]),
                    error=str(state.get("error") or state["status"]),
                )
            return dict(state["payload"])
        payload = {"schema_version": 1, "artifacts": []}
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return payload

    def load(self) -> dict[str, Any]:
        state = self.inspect()
        if not state["ok"]:
            raise ArtifactRegistryStateError(
                state["status"],
                self.path,
                registry_exists=bool(state["registry_exists"]),
                registry_valid=bool(state["registry_valid"]),
                registry_readable=bool(state["registry_readable"]),
                error=str(state.get("error") or state["status"]),
            )
        return dict(state["payload"])

    def list(self) -> list[dict[str, Any]]:
        artifacts = self.load().get("artifacts")
        return [item for item in artifacts if isinstance(item, dict)] if isinstance(artifacts, list) else []

    @staticmethod
    def _chatgpt_project_identity(url: str | None) -> str | None:
        if not isinstance(url, str) or not url.startswith("https://chatgpt.com/g/"):
            return None
        slug = url.split("/g/", 1)[-1].split("/", 1)[0]
        match = re.match(r"^(g-p-[0-9a-fA-F]{32})(?:-|$)", slug)
        return match.group(1).lower() if match else (slug or None)

    @staticmethod
    def _record_validation_error(record: Any) -> str | None:
        if not isinstance(record, dict):
            return "record must be a JSON object"
        repo_id = record.get("repo_id")
        if not isinstance(repo_id, str) or not repo_id.strip():
            return "repo_id is required"
        normalized_repo_id = normalize_repo_id(repo_id)
        if normalized_repo_id != repo_id:
            return "repo_id must already be normalized"
        filename = record.get("filename")
        parsed = parse_canonical_artifact_filename(filename if isinstance(filename, str) else None)
        if parsed is None:
            return "filename must use canonical <repo_id>_v<version>.zip grammar"
        if parsed["repo_id"] != repo_id:
            return "filename repo_id does not match record repo_id"
        version = canonical_version_tag(record.get("version") if isinstance(record.get("version"), str) else None)
        if version != parsed["version"]:
            return "record version does not match canonical filename version"

        evidence_fields = {
            "source_requested_ref": record.get("source_requested_ref"),
            "source_processed_file_id": record.get("source_processed_file_id"),
            "source_library_metadata_object_id": record.get("source_library_metadata_object_id"),
        }
        evidence_present = any(value not in (None, "") for value in evidence_fields.values())
        if evidence_present:
            requested_ref = evidence_fields["source_requested_ref"]
            processed_file_id = evidence_fields["source_processed_file_id"]
            library_metadata_object_id = evidence_fields["source_library_metadata_object_id"]
            if not isinstance(requested_ref, str) or Path(requested_ref).name != filename:
                return "source_requested_ref must equal the canonical artifact filename when source evidence is present"
            if not isinstance(processed_file_id, str) or not processed_file_id.startswith("file_"):
                return "source_processed_file_id must be a file_ identity when source evidence is present"
            if not isinstance(library_metadata_object_id, str) or not library_metadata_object_id.startswith("libfile_"):
                return "source_library_metadata_object_id must be a libfile_ identity when source evidence is present"
            source_ref = record.get("source_ref")
            if not isinstance(source_ref, str) or not source_ref.strip():
                return "source_ref is required when source evidence is present"
            project_url = record.get("project_url")
            if not isinstance(project_url, str) or not project_url.startswith("https://chatgpt.com/g/"):
                return "project_url must identify a ChatGPT project when source evidence is present"

        origin_url = record.get("origin_conversation_url")
        origin_id = record.get("origin_conversation_id")
        origin_fields = [origin_url, origin_id, record.get("origin_request_id"), record.get("origin_correlation_id"), record.get("origin_message_id"), record.get("origin_answer_id")]
        origin_present = any(value not in (None, "") for value in origin_fields)
        if origin_present:
            if not isinstance(origin_url, str) or "/c/" not in origin_url or not origin_url.startswith("https://chatgpt.com/g/"):
                return "origin_conversation_url must identify a ChatGPT project conversation when provenance is present"
            derived_id = origin_url.rstrip("/").split("/c/", 1)[-1].split("/", 1)[0]
            if not isinstance(origin_id, str) or not origin_id.strip() or origin_id != derived_id:
                return "origin_conversation_id must exactly match origin_conversation_url"
            project_url = record.get("project_url")
            if isinstance(project_url, str) and project_url.startswith("https://chatgpt.com/g/"):
                project_id = ArtifactRegistry._chatgpt_project_identity(project_url)
                origin_project_id = ArtifactRegistry._chatgpt_project_identity(origin_url)
                if not project_id or not origin_project_id or project_id != origin_project_id:
                    return "origin conversation must belong to the artifact project"
        return None

    @staticmethod
    def _record_repo_id(record: dict[str, Any]) -> str | None:
        repo_id = record.get("repo_id")
        return repo_id if isinstance(repo_id, str) and repo_id else None

    def repo_ids(self) -> list[str]:
        ids = {repo_id for item in self.list() if (repo_id := self._record_repo_id(item))}
        return sorted(ids)

    @staticmethod
    def _release_identity_key(record: dict[str, Any] | ArtifactRecord) -> tuple[str, str] | None:
        if isinstance(record, ArtifactRecord):
            kind = record.kind
            repo_id = normalize_repo_id(record.repo_id)
            version = canonical_version_tag(record.version)
        else:
            kind = str(record.get("kind") or "")
            repo_id = normalize_repo_id(record.get("repo_id"))
            version = canonical_version_tag(record.get("version") if isinstance(record.get("version"), str) else None)
        if kind not in RELEASE_IDENTITY_KINDS or not repo_id or not version:
            return None
        return repo_id, version

    def release_identity_issues(self, *, repo_id: str | None = None) -> dict[str, Any]:
        normalized_repo = normalize_repo_id(repo_id)
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in self.list():
            key = self._release_identity_key(item)
            if key is None or (normalized_repo and key[0] != normalized_repo):
                continue
            groups.setdefault(key, []).append(item)
        sha_conflicts: list[dict[str, Any]] = []
        duplicate_identities: list[dict[str, Any]] = []
        for (group_repo, version), records in sorted(groups.items()):
            sha_values = [str(item.get("sha256") or "") for item in records]
            nonempty = sorted({value for value in sha_values if value})
            if any(not value for value in sha_values) or len(nonempty) != 1:
                sha_conflicts.append({
                    "repo_id": group_repo,
                    "version": version,
                    "sha256_values": nonempty,
                    "missing_sha_count": sum(1 for value in sha_values if not value),
                    "records": records,
                })
            if len(records) > 1:
                duplicate_identities.append({
                    "repo_id": group_repo,
                    "version": version,
                    "record_count": len(records),
                    "sha256_values": nonempty,
                    "kinds": sorted({str(item.get("kind") or "") for item in records}),
                    "records": records,
                })
        return {
            "ok": not sha_conflicts and not duplicate_identities,
            "sha_conflicts": sha_conflicts,
            "duplicate_identities": duplicate_identities,
            "group_count": len(groups),
        }

    def release_record(self, repo_id: str, version: str) -> dict[str, Any] | None:
        normalized_repo = normalize_repo_id(repo_id)
        normalized_version = canonical_version_tag(version)
        if not normalized_repo or not normalized_version:
            return None
        matches = [
            item for item in self.list()
            if self._release_identity_key(item) == (normalized_repo, normalized_version)
        ]
        if len(matches) != 1:
            return None
        return matches[0]

    def object_path(self, sha256: str, filename: str) -> Path:
        digest = str(sha256 or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("release artifact sha256 must be a 64-character lowercase hex digest")
        canonical_name = Path(filename).name
        if canonical_name != filename or parse_canonical_artifact_filename(canonical_name) is None:
            raise ValueError("release artifact filename must be canonical")
        return self.object_dir / digest / canonical_name

    def prepare_release_object(self, record: ArtifactRecord) -> ArtifactRecord:
        if record.kind not in RELEASE_IDENTITY_KINDS:
            return record
        source = Path(record.path).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"release artifact input does not exist: {source}")
        verification = verify_zip_artifact(source)
        if not verification.get("ok"):
            raise ValueError(f"release artifact failed verification: {verification.get('error') or 'zip verification failed'}")
        observed_sha = str(verification.get("sha256") or "")
        if not observed_sha or observed_sha != str(record.sha256 or ""):
            raise ValueError(f"release artifact sha256 mismatch: record={record.sha256} observed={observed_sha}")
        parsed = parse_canonical_artifact_filename(record.filename)
        if parsed is None:
            raise ValueError("release artifact filename must be canonical")
        try:
            with zipfile.ZipFile(source) as archive:
                embedded_version = archive.read("VERSION").decode("utf-8", errors="replace").strip()
        except (OSError, zipfile.BadZipFile, KeyError) as exc:
            raise ValueError(f"release artifact VERSION could not be read: {exc}") from exc
        if canonical_version_tag(embedded_version) != canonical_version_tag(record.version):
            raise ValueError("release artifact embedded VERSION does not match record version")
        destination = self.object_path(observed_sha, record.filename)
        if destination.is_file():
            existing_sha = sha256_file(destination)
            if existing_sha != observed_sha:
                raise ValueError(f"immutable artifact object is corrupt: {destination}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            shutil.copy2(source, temporary)
            copied_sha = sha256_file(temporary)
            if copied_sha != observed_sha:
                temporary.unlink(missing_ok=True)
                raise ValueError("immutable artifact object copy sha256 mismatch")
            temporary.replace(destination)
        return replace(record, path=str(destination))

    def add(self, record: ArtifactRecord) -> dict[str, Any]:
        payload = self.load()
        artifacts = [item for item in payload.get("artifacts", []) if isinstance(item, dict)]
        record_payload = record.to_dict()
        record_error = self._record_validation_error(record_payload)
        if record_error:
            raise ValueError(f"artifact record is invalid: {record_error}")

        key = self._release_identity_key(record)
        matching: list[dict[str, Any]] = []
        if key is not None:
            matching = [item for item in artifacts if self._release_identity_key(item) == key]
            for existing in matching:
                existing_sha = str(existing.get("sha256") or "")
                if not existing_sha or existing_sha != str(record.sha256 or ""):
                    raise ArtifactIdentityConflictError(
                        repo_id=key[0],
                        version=key[1],
                        existing_sha256=existing_sha,
                        candidate_sha256=str(record.sha256 or ""),
                    )
            # Validate/copy candidate bytes only after the logical identity conflict
            # guard has proven that the version is either unbound or bound to the
            # same immutable SHA.
            record = self.prepare_release_object(record)
            record_payload = record.to_dict()

            existing_adopted = next((item for item in matching if item.get("kind") == "adopted_release"), None)
            if record.kind == "release" and existing_adopted is not None:
                selected = existing_adopted
            else:
                selected = record_payload
            artifacts = [item for item in artifacts if self._release_identity_key(item) != key]
            artifacts.append(selected)
            record_payload = selected
        else:
            artifacts = [item for item in artifacts if item.get("path") != record.path]
            artifacts.append(record_payload)

        artifacts.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        payload["schema_version"] = 1
        payload["updated_at"] = utc_now()
        payload["artifacts"] = artifacts
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return record_payload

    def current(self, repo_id: str | None = None) -> dict[str, Any] | None:
        artifacts = [item for item in self.list() if item.get("kind") == "adopted_release"]
        normalized_repo = normalize_repo_id(repo_id)
        if normalized_repo:
            for item in artifacts:
                if self._record_repo_id(item) == normalized_repo:
                    return item
            return None
        repo_ids = {repo for item in artifacts if (repo := self._record_repo_id(item))}
        if len(repo_ids) > 1:
            return None
        return artifacts[0] if artifacts else None

    def current_all(self) -> dict[str, dict[str, Any]]:
        current_by_repo: dict[str, dict[str, Any]] = {}
        for item in self.list():
            if item.get("kind") != "adopted_release":
                continue
            repo_id = self._record_repo_id(item) or "__unscoped__"
            current_by_repo.setdefault(repo_id, item)
        return current_by_repo

    def is_current_ambiguous(self) -> bool:
        return len(self.repo_ids()) > 1




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
        registry_state = registry.inspect()
        if registry_state.get("status") == "artifact_registry_missing":
            artifacts: list[dict[str, Any]] = []
            current = None
            registry_payload = {
                "path": str(registry.path),
                "exists": False,
                "status": "artifact_registry_missing",
                "registry_status": "missing",
                "registry_valid": False,
                "registry_readable": False,
                "current": None,
                "artifact_count": 0,
                "error": registry_state.get("error"),
            }
        elif not bool(registry_state.get("ok")):
            raise ArtifactRegistryStateError(
                str(registry_state.get("status") or "artifact_registry_invalid"),
                registry.path,
                registry_exists=bool(registry_state.get("registry_exists")),
                registry_valid=bool(registry_state.get("registry_valid")),
                registry_readable=bool(registry_state.get("registry_readable")),
                error=str(registry_state.get("error") or registry_state.get("status") or "artifact registry preflight failed"),
            )
        else:
            payload = registry_state.get("payload") if isinstance(registry_state.get("payload"), dict) else {}
            artifacts = [item for item in payload.get("artifacts", []) if isinstance(item, dict)]
            repo_ids = {str(item.get("repo_id")) for item in artifacts if item.get("repo_id")}
            current = artifacts[0] if artifacts and len(repo_ids) <= 1 else None
            registry_payload = {
                "path": str(registry.path),
                "exists": True,
                "status": registry_state.get("status"),
                "registry_status": "loaded" if artifacts else "empty",
                "registry_valid": True,
                "registry_readable": True,
                "current": current,
                "artifact_count": len(artifacts),
                "error": None,
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
        repo_id=normalize_repo_id(root.name),
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
            promptbranch_repo_manifest_violations = promptbranch_repo_manifest_violations_from_zip(archive)
    except zipfile.BadZipFile:
        return {"ok": False, "error": "bad_zip", "path": str(zip_path)}
    unsafe = [name for name in names if name.startswith("/") or ".." in Path(name).parts]
    hygiene_violations = release_entry_hygiene_violations(names)
    nested_zip_entries = [name for name in names if name.lower().endswith(".zip")]
    top_levels = {name.split("/", 1)[0] for name in names if name and not name.endswith("/")}
    wrapper_folder = None
    if len(top_levels) == 1 and not any("/" not in name.rstrip("/") for name in names if name and not name.endswith("/")):
        wrapper_folder = next(iter(top_levels))
    return {
        "ok": bad is None and not unsafe and wrapper_folder is None and not hygiene_violations and not promptbranch_repo_manifest_violations,
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
        "promptbranch_repo_manifest_violations": promptbranch_repo_manifest_violations,
        "promptbranch_repo_manifest_violation_count": len(promptbranch_repo_manifest_violations),
        "nested_zip_entries": nested_zip_entries,
        "nested_zip_count": len(nested_zip_entries),
        "wrapper_folder": wrapper_folder,
    }

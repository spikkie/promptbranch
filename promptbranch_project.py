from __future__ import annotations

import json
import os
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from promptbranch_artifacts import ARTIFACT_REGISTRY_NAME, ArtifactRegistry, normalize_repo_id, utc_now
from promptbranch_state import ConversationStateStore, project_home_url_from_url

REPO_IDENTITY_FILE_NAME = ".promptbranch-repo.json"
PROJECT_STATE_HOME_ENV = "PROMPTBRANCH_PROJECT_STATE_HOME"
PROJECT_CONFIG_HOME_ENV = "PROMPTBRANCH_PROJECT_CONFIG_HOME"


@dataclass(frozen=True)
class PromptbranchRepoIdentity:
    schema_version: int
    project_id: str
    project_home_url: str | None
    repo_id: str
    artifact_pattern: str | None
    role: str | None
    path: Path
    repo_root: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "project_home_url": self.project_home_url,
            "repo_id": self.repo_id,
            "artifact_pattern": self.artifact_pattern,
            "role": self.role,
            "path": str(self.path),
            "repo_root": str(self.repo_root),
        }


def _safe_project_id(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._-")
    return text or "default"


_IMMUTABLE_PROJECT_ID_RE = re.compile(r"^(g-p-[0-9a-fA-F]{32})(?:-|$)")


def immutable_project_id(value: str | None) -> str | None:
    """Extract the immutable ChatGPT Project UUID identity from an id or URL.

    ChatGPT may expose the same Project as either ``g-p-<uuid>`` or
    ``g-p-<uuid>-<display-slug>``.  This helper canonicalizes only that
    immutable UUID form.  Human aliases and non-UUID ids are intentionally
    not broadened.
    """

    text = str(value or "").strip()
    if not text:
        return None
    home_url = project_home_url_from_url(text)
    if home_url:
        parts = [part for part in urllib.parse.urlparse(home_url).path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "g":
            text = parts[1]
    match = _IMMUTABLE_PROJECT_ID_RE.match(text)
    return match.group(1).lower() if match else None


def same_project_authority(left: str | None, right: str | None) -> bool:
    """Compare Project identities without rewriting tracked authority.

    UUID-bearing bare and slugged forms are aliases only when their immutable
    UUIDs match.  Values without an immutable UUID retain exact comparison.
    """

    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    if not left_text or not right_text:
        return False
    left_uuid = immutable_project_id(left_text)
    right_uuid = immutable_project_id(right_text)
    if left_uuid or right_uuid:
        return bool(left_uuid and right_uuid and left_uuid == right_uuid)
    left_home = project_home_url_from_url(left_text) or left_text
    right_home = project_home_url_from_url(right_text) or right_text
    return str(left_home).rstrip("/") == str(right_home).rstrip("/")


def project_state_home() -> Path:
    raw = os.getenv(PROJECT_STATE_HOME_ENV)
    if raw:
        return Path(raw).expanduser()
    xdg = os.getenv("XDG_STATE_HOME")
    root = Path(xdg).expanduser() if xdg else Path("~/.local/state").expanduser()
    return root / "promptbranch" / "projects"


def project_config_home() -> Path:
    raw = os.getenv(PROJECT_CONFIG_HOME_ENV)
    if raw:
        return Path(raw).expanduser()
    xdg = os.getenv("XDG_CONFIG_HOME")
    root = Path(xdg).expanduser() if xdg else Path("~/.config").expanduser()
    return root / "promptbranch" / "projects"


def project_registry_dir(project_id: str) -> Path:
    return project_state_home() / _safe_project_id(project_id)


def project_repo_config_path(project_id: str) -> Path:
    return project_config_home() / _safe_project_id(project_id) / "repos.json"


def project_registry_file(project_id: str) -> Path:
    return project_registry_dir(project_id) / ARTIFACT_REGISTRY_NAME


def ensure_project_registry(project_id: str) -> Path:
    registry = ArtifactRegistry(project_registry_dir(project_id))
    registry.initialize()
    return registry.path


def find_repo_identity_path(cwd: str | Path | None = None) -> Path | None:
    start = Path(cwd).expanduser().resolve() if cwd else Path.cwd().resolve()
    for current in (start, *start.parents):
        candidate = current / REPO_IDENTITY_FILE_NAME
        if candidate.is_file():
            return candidate
    return None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def load_repo_identity(cwd: str | Path | None = None) -> PromptbranchRepoIdentity | None:
    path = find_repo_identity_path(cwd)
    if path is None:
        return None
    payload = _read_json(path)
    project_id = str(payload.get("project_id") or "").strip()
    repo_id = normalize_repo_id(payload.get("repo_id") if isinstance(payload.get("repo_id"), str) else None)
    if not project_id:
        raise ValueError(f"{path} is missing project_id")
    if not repo_id:
        raise ValueError(f"{path} is missing repo_id")
    home_url_raw = payload.get("project_home_url") if isinstance(payload.get("project_home_url"), str) else None
    home_url = project_home_url_from_url(home_url_raw) or home_url_raw
    return PromptbranchRepoIdentity(
        schema_version=int(payload.get("schema_version") or 1),
        project_id=_safe_project_id(project_id),
        project_home_url=home_url,
        repo_id=repo_id,
        artifact_pattern=payload.get("artifact_pattern") if isinstance(payload.get("artifact_pattern"), str) else None,
        role=payload.get("role") if isinstance(payload.get("role"), str) else None,
        path=path,
        repo_root=path.parent,
    )


def write_repo_identity(
    repo_root: str | Path,
    *,
    project_id: str,
    project_home_url: str | None,
    repo_id: str,
    artifact_pattern: str | None = None,
    role: str | None = None,
) -> Path:
    normalized_repo_id = normalize_repo_id(repo_id)
    if not normalized_repo_id:
        raise ValueError("repo_id is required")
    normalized_project_id = _safe_project_id(project_id)
    home_url = project_home_url_from_url(project_home_url) or project_home_url
    payload = {
        "schema_version": 1,
        "project_id": normalized_project_id,
        "project_home_url": home_url,
        "repo_id": normalized_repo_id,
        "artifact_pattern": artifact_pattern or f"{normalized_repo_id}_<version>.zip",
        "role": role or "member",
    }
    root = Path(repo_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / REPO_IDENTITY_FILE_NAME
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path



def repo_identity_mismatches(
    identity: PromptbranchRepoIdentity,
    *,
    project_id: str | None = None,
    project_home_url: str | None = None,
    repo_id: str | None = None,
    artifact_pattern: str | None = None,
    role: str | None = None,
) -> list[str]:
    """Compare supplied join intent with the tracked repository binding.

    Only explicitly supplied values are compared. The tracked file remains the
    authority; callers must fail closed instead of silently rewriting it.
    """

    mismatches: list[str] = []
    if project_id is not None:
        requested_project_id = _safe_project_id(project_id)
        if not same_project_authority(identity.project_id, requested_project_id):
            mismatches.append(f"project_id tracked={identity.project_id!r} requested={requested_project_id!r}")
    if project_home_url is not None:
        requested_home = project_home_url_from_url(project_home_url) or str(project_home_url).strip()
        if not same_project_authority(identity.project_home_url, requested_home):
            mismatches.append(f"project_home_url tracked={identity.project_home_url!r} requested={requested_home!r}")
    if repo_id is not None:
        requested_repo = normalize_repo_id(repo_id)
        if requested_repo != identity.repo_id:
            mismatches.append(f"repo_id tracked={identity.repo_id!r} requested={requested_repo!r}")
    if artifact_pattern is not None and str(artifact_pattern).strip() != identity.artifact_pattern:
        mismatches.append(f"artifact_pattern tracked={identity.artifact_pattern!r} requested={str(artifact_pattern).strip()!r}")
    if role is not None and str(role).strip() != identity.role:
        mismatches.append(f"role tracked={identity.role!r} requested={str(role).strip()!r}")
    return mismatches


def validate_tracked_repo_identity(repo_root: str | Path, *, expected_repo_id: str | None = None) -> list[str]:
    """Validate the committed Project binding as portable repository authority."""

    root = Path(repo_root).expanduser().resolve()
    path = root / REPO_IDENTITY_FILE_NAME
    if not path.is_file():
        return [f"authority file missing: {REPO_IDENTITY_FILE_NAME}"]
    try:
        payload = _read_json(path)
        identity = load_repo_identity(root)
    except ValueError as exc:
        return [str(exc)]
    if identity is None:
        return [f"authority file missing: {REPO_IDENTITY_FILE_NAME}"]

    errors: list[str] = []
    allowed = {"schema_version", "project_id", "project_home_url", "repo_id", "artifact_pattern", "role"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        errors.append(f"{REPO_IDENTITY_FILE_NAME} contains unsupported field(s): {unknown}")
    if payload.get("schema_version") != 1:
        errors.append(f"{REPO_IDENTITY_FILE_NAME} schema_version must be 1")
    required = ("project_id", "project_home_url", "repo_id", "artifact_pattern", "role")
    for key in required:
        if not isinstance(payload.get(key), str) or not str(payload.get(key)).strip():
            errors.append(f"{REPO_IDENTITY_FILE_NAME} is missing {key}")
    home_raw = payload.get("project_home_url") if isinstance(payload.get("project_home_url"), str) else None
    if home_raw and project_home_url_from_url(home_raw) is None:
        errors.append(f"{REPO_IDENTITY_FILE_NAME} project_home_url is not a ChatGPT Project URL")
    if identity.path != path:
        errors.append(f"{REPO_IDENTITY_FILE_NAME} must be located at repository root")
    if expected_repo_id and identity.repo_id != normalize_repo_id(expected_repo_id):
        errors.append(f"{REPO_IDENTITY_FILE_NAME} repo_id {identity.repo_id!r} does not match authority graph repo_id {normalize_repo_id(expected_repo_id)!r}")
    if not artifact_prefix_matches(identity.repo_id, identity.artifact_pattern):
        errors.append(f"{REPO_IDENTITY_FILE_NAME} artifact_pattern must be {identity.repo_id}_<version>.zip")
    return errors

def load_local_repo_registry(project_id: str) -> dict[str, Any]:
    path = project_repo_config_path(project_id)
    if not path.is_file():
        return {"schema_version": 1, "project_id": _safe_project_id(project_id), "repos": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "project_id": _safe_project_id(project_id), "repos": {}}
    if not isinstance(payload, dict):
        return {"schema_version": 1, "project_id": _safe_project_id(project_id), "repos": {}}
    if not isinstance(payload.get("repos"), dict):
        payload["repos"] = {}
    payload.setdefault("schema_version", 1)
    payload["project_id"] = _safe_project_id(str(payload.get("project_id") or project_id))
    return payload


def save_local_repo_registry(project_id: str, payload: dict[str, Any]) -> Path:
    path = project_repo_config_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload["schema_version"] = int(payload.get("schema_version") or 1)
    payload["project_id"] = _safe_project_id(project_id)
    if not isinstance(payload.get("repos"), dict):
        payload["repos"] = {}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def join_local_repo(identity: PromptbranchRepoIdentity) -> Path:
    ensure_project_registry(identity.project_id)
    payload = load_local_repo_registry(identity.project_id)
    repos = payload.get("repos") if isinstance(payload.get("repos"), dict) else {}
    repos[identity.repo_id] = {
        "repo_root": str(identity.repo_root),
        "artifact_pattern": identity.artifact_pattern,
        "role": identity.role or "member",
        "project_home_url": identity.project_home_url,
    }
    payload["project_home_url"] = identity.project_home_url
    payload["repos"] = repos
    return save_local_repo_registry(identity.project_id, payload)


def configured_repos(project_id: str) -> dict[str, dict[str, Any]]:
    payload = load_local_repo_registry(project_id)
    repos = payload.get("repos") if isinstance(payload.get("repos"), dict) else {}
    return {str(key): dict(value) for key, value in repos.items() if isinstance(value, dict)}




def _registry_current_identity(record: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    return {
        "filename": record.get("filename"),
        "version": record.get("version"),
        "sha256": record.get("sha256"),
        "source_ref": record.get("source_ref"),
        "repo_id": ArtifactRegistry._record_repo_id(record),
    }


def _same_registry_current(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    return _registry_current_identity(left) == _registry_current_identity(right)


def artifact_prefix_matches(repo_id: str, pattern: str | None) -> bool:
    """Return true when a configured artifact pattern matches canonical grammar.

    Canonical future pattern is ``<repo_id>_<version>.zip``.  Historical
    patterns remain readable in older registry records, but repo doctor should
    fail closed for new project configuration that cannot produce canonical
    artifact names.
    """

    normalized = normalize_repo_id(repo_id)
    if not pattern or not normalized:
        return True
    expected = f"{normalized}_<version>.zip"
    return str(pattern).strip() == expected

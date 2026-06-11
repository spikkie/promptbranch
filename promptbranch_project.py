from __future__ import annotations

import json
import os
import re
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
    path = project_registry_file(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps({"schema_version": 1, "artifacts": []}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


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


def import_current_registry(
    identity: PromptbranchRepoIdentity,
    *,
    source_profile_dir: str | Path | None = None,
    dry_run: bool = False,
    replace: bool = False,
) -> dict[str, Any]:
    """Plan or import current artifacts from a legacy repo-local registry.

    This is intentionally explicit.  Project join creates the identity and empty
    project registry; this function copies current per-repo artifact entries from
    an existing repo-local ``.pb_profile`` registry into the project-scoped
    registry only when the operator asks for it.
    """

    source_dir = Path(source_profile_dir).expanduser().resolve() if source_profile_dir else (identity.repo_root / ".pb_profile").resolve()
    target_dir = project_registry_dir(identity.project_id)
    source_registry = ArtifactRegistry(source_dir)
    target_registry = ArtifactRegistry(target_dir)
    project_url = identity.project_home_url
    source_current = source_registry.current_all()
    target_current = target_registry.current_all()
    configured = configured_repos(identity.project_id)

    planned_imports: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for raw_repo_id, record in sorted(source_current.items()):
        repo_id = normalize_repo_id(raw_repo_id)
        if not repo_id or repo_id == "__unscoped__":
            skipped.append({"repo_id": raw_repo_id, "reason": "missing_repo_id", "filename": record.get("filename")})
            continue
        record = dict(record)
        record["repo_id"] = repo_id
        if not record.get("project_url") and project_url:
            record["project_url"] = project_url
        existing = target_current.get(repo_id)
        if existing and _same_registry_current(existing, record):
            unchanged.append({"repo_id": repo_id, "filename": record.get("filename"), "version": record.get("version")})
            continue
        if existing and not replace:
            conflicts.append({
                "repo_id": repo_id,
                "existing": _registry_current_identity(existing),
                "incoming": _registry_current_identity(record),
            })
            continue
        planned_imports.append({
            "repo_id": repo_id,
            "configured": repo_id in configured,
            "filename": record.get("filename"),
            "version": record.get("version"),
            "source_ref": record.get("source_ref"),
            "sha256": record.get("sha256"),
            "replace_existing": bool(existing),
            "record": record,
        })

    base_payload = {
        "action": "project_import_current_registry",
        "project_id": identity.project_id,
        "project_home_url": identity.project_home_url,
        "current_repo_id": identity.repo_id,
        "source_registry_file": str(source_registry.path),
        "target_registry_file": str(target_registry.path),
        "local_repo_config_file": str(project_repo_config_path(identity.project_id)),
        "dry_run": bool(dry_run),
        "replace": bool(replace),
        "source_registry_exists": source_registry.path.is_file(),
        "target_registry_exists": target_registry.path.is_file(),
        "planned_import_count": len(planned_imports),
        "unchanged_count": len(unchanged),
        "skipped_count": len(skipped),
        "conflict_count": len(conflicts),
        "planned_imports": [{k: v for k, v in item.items() if k != "record"} for item in planned_imports],
        "unchanged": unchanged,
        "skipped": skipped,
        "conflicts": conflicts,
    }

    if conflicts and not replace:
        return {
            **base_payload,
            "ok": False,
            "status": "import_conflicts_found",
            "mutated": False,
            "next_safe_action": "Rerun with --dry-run to inspect or --replace to explicitly replace conflicting current records.",
        }
    if dry_run:
        return {
            **base_payload,
            "ok": True,
            "status": "import_plan",
            "mutated": False,
            "next_safe_action": "Rerun without --dry-run to import the planned current records.",
        }
    if not planned_imports:
        ensure_project_registry(identity.project_id)
        return {
            **base_payload,
            "ok": True,
            "status": "nothing_to_import",
            "mutated": False,
            "next_safe_action": "Run pb repo list --json and pb repo doctor --json to inspect project registry state.",
        }

    target_payload = target_registry.load()
    artifacts = [dict(item) for item in target_payload.get("artifacts", []) if isinstance(item, dict)]
    importing_repo_ids = {str(item["repo_id"]) for item in planned_imports}
    if replace:
        artifacts = [item for item in artifacts if ArtifactRegistry._record_repo_id(item) not in importing_repo_ids]
    existing_keys = {(ArtifactRegistry._record_repo_id(item), item.get("filename"), item.get("version"), item.get("sha256")) for item in artifacts}
    imported: list[dict[str, Any]] = []
    for item in planned_imports:
        record = dict(item["record"])
        key = (str(item["repo_id"]), record.get("filename"), record.get("version"), record.get("sha256"))
        if key not in existing_keys:
            artifacts.append(record)
            existing_keys.add(key)
        imported.append({k: v for k, v in item.items() if k != "record"})

    artifacts.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    target_payload["schema_version"] = int(target_payload.get("schema_version") or 1)
    target_payload["updated_at"] = utc_now()
    target_payload["artifacts"] = artifacts
    target_registry.profile_dir.mkdir(parents=True, exist_ok=True)
    target_registry.path.write_text(json.dumps(target_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    state_store = ConversationStateStore(str(target_dir))
    for item in planned_imports:
        record = item["record"]
        state_store.remember_artifact(
            project_url=project_url or record.get("project_url"),
            artifact_ref=record.get("filename"),
            artifact_version=record.get("version"),
            source_ref=record.get("source_ref") or record.get("filename"),
            source_version=record.get("version"),
            repo_id=str(item["repo_id"]),
        )

    return {
        **base_payload,
        "ok": True,
        "status": "imported",
        "mutated": True,
        "imported_count": len(imported),
        "imported": imported,
        "next_safe_action": "Run pb repo list --json, pb repo doctor --json, and pb artifact current --all --json from each joined repo.",
    }

def artifact_prefix_matches(repo_id: str, pattern: str | None) -> bool:
    if not pattern:
        return True
    prefix = str(pattern).split("<version>", 1)[0].rstrip("_")
    return not prefix or prefix == repo_id

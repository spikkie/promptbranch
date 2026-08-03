from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Iterable

from promptbranch_artifacts import (
    ArtifactRegistry,
    canonical_artifact_filename,
    canonical_version_tag,
    verify_zip_artifact,
)
from promptbranch_project import configured_repos, load_repo_identity, project_registry_dir

RELEASE_SET_SCHEMA = "promptbranch.release_set"
RELEASE_SET_SCHEMA_VERSION = "1.0"
RELEASE_SET_PLAN_SCHEMA = "promptbranch.release_set.plan"
RELEASE_SET_PLAN_SCHEMA_VERSION = "1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CONSTRAINT_PART_RE = re.compile(r"^(==|>=|<=|>|<)?\s*(v?\d+(?:\.\d+){2,})$")


class ReleaseSetError(ValueError):
    pass


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReleaseSetError(f"release-set manifest unreadable: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseSetError(f"release-set manifest is invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleaseSetError("release-set manifest must be a JSON object")
    return payload


def _strict_keys(payload: dict[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ReleaseSetError(f"{context} contains unsupported field(s): {unknown}")


def _version_tuple(value: str) -> tuple[int, ...]:
    canonical = canonical_version_tag(value)
    if canonical is None:
        raise ReleaseSetError(f"version must use canonical numeric grammar: {value!r}")
    return tuple(int(part) for part in canonical[1:].split("."))


def _compare_versions(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    width = max(len(left), len(right))
    a = left + (0,) * (width - len(left))
    b = right + (0,) * (width - len(right))
    return (a > b) - (a < b)


def version_satisfies(version: str, constraint: str) -> bool:
    observed = _version_tuple(version)
    parts = [part.strip() for part in str(constraint or "").split(",") if part.strip()]
    if not parts:
        raise ReleaseSetError("dependency constraint must not be empty")
    for part in parts:
        match = _CONSTRAINT_PART_RE.fullmatch(part)
        if not match:
            raise ReleaseSetError(f"unsupported dependency constraint: {part!r}")
        operator = match.group(1) or "=="
        expected = _version_tuple(match.group(2))
        relation = _compare_versions(observed, expected)
        passed = {
            "==": relation == 0,
            ">=": relation >= 0,
            "<=": relation <= 0,
            ">": relation > 0,
            "<": relation < 0,
        }[operator]
        if not passed:
            return False
    return True


def _canonical_json_digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_zip_version(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as archive:
            if "VERSION" not in archive.namelist():
                return None
            return archive.read("VERSION").decode("utf-8").strip()
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError):
        return None


def _resolve_repo_relative(repo_root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ReleaseSetError("target.local_path must be repository-relative")
    resolved = (repo_root / candidate).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ReleaseSetError("target.local_path escapes repository root") from exc
    return resolved


def _topological_waves(nodes: Iterable[str], dependencies: dict[str, set[str]]) -> tuple[list[str], list[list[str]], list[str]]:
    node_set = set(nodes)
    incoming = {node: set(dependencies.get(node, set())) & node_set for node in node_set}
    reverse: dict[str, set[str]] = {node: set() for node in node_set}
    for consumer, required in incoming.items():
        for dependency in required:
            reverse[dependency].add(consumer)
    remaining = {node: set(values) for node, values in incoming.items()}
    order: list[str] = []
    waves: list[list[str]] = []
    while remaining:
        ready = sorted(node for node, required in remaining.items() if not required)
        if not ready:
            return order, waves, sorted(remaining)
        waves.append(ready)
        order.extend(ready)
        for node in ready:
            remaining.pop(node, None)
        for required in remaining.values():
            required.difference_update(ready)
    return order, waves, []


def build_release_set_plan(
    repo_path: str | Path = ".",
    *,
    manifest: str | Path = ".promptbranch-release-set.json",
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    manifest_path = Path(manifest).expanduser()
    if not manifest_path.is_absolute():
        manifest_path = (repo / manifest_path).resolve()

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def block(code: str, message: str, **details: Any) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if details:
            item["details"] = details
        blockers.append(item)

    def warn(code: str, message: str, **details: Any) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if details:
            item["details"] = details
        warnings.append(item)

    try:
        identity = load_repo_identity(repo)
    except ValueError as exc:
        identity = None
        block("repo_identity_invalid", str(exc))
    if identity is None:
        block("repo_identity_missing", "repository is not joined to a Promptbranch project")

    try:
        payload = _load_json_object(manifest_path)
        _strict_keys(payload, {"schema", "schema_version", "release_set_id", "project_id", "repositories"}, "release-set manifest")
    except ReleaseSetError as exc:
        return {
            "ok": False,
            "schema": RELEASE_SET_PLAN_SCHEMA,
            "schema_version": RELEASE_SET_PLAN_SCHEMA_VERSION,
            "action": "release_set_plan",
            "status": "release_set_manifest_invalid",
            "repo_path": str(repo),
            "manifest_path": str(manifest_path),
            "blockers": [{"code": "release_set_manifest_invalid", "message": str(exc)}],
            "warnings": [],
            "safety": {"read_only": True, "state_mutated": False, "publication_performed": False, "adoption_performed": False, "execution_performed": False},
        }

    if payload.get("schema") != RELEASE_SET_SCHEMA:
        block("release_set_schema_invalid", f"schema must be {RELEASE_SET_SCHEMA!r}")
    if payload.get("schema_version") != RELEASE_SET_SCHEMA_VERSION:
        block("release_set_schema_version_unsupported", f"schema_version must be {RELEASE_SET_SCHEMA_VERSION!r}")
    release_set_id = str(payload.get("release_set_id") or "").strip()
    if not release_set_id:
        block("release_set_id_missing", "release_set_id is required")
    project_id = str(payload.get("project_id") or "").strip()
    if not project_id:
        block("project_id_missing", "project_id is required")
    if identity is not None and project_id and identity.project_id != project_id:
        block("project_id_mismatch", "manifest project_id does not match tracked repository identity", tracked=identity.project_id, manifest=project_id)

    configured = configured_repos(project_id) if project_id else {}
    registry = ArtifactRegistry(project_registry_dir(project_id)) if project_id else None
    registry_state = registry.inspect() if registry is not None else {"ok": False, "status": "project_id_missing"}
    if registry is not None and not registry_state.get("ok"):
        block("project_registry_unavailable", "project artifact registry is unavailable or invalid", registry_status=registry_state.get("status"), registry_file=str(registry.path))

    raw_repositories = payload.get("repositories")
    if not isinstance(raw_repositories, list) or not raw_repositories:
        block("release_set_repositories_missing", "repositories must be a non-empty array")
        raw_repositories = []

    normalized: dict[str, dict[str, Any]] = {}
    dependency_graph: dict[str, set[str]] = {}
    repository_rows: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_repositories):
        context = f"repositories[{index}]"
        if not isinstance(raw, dict):
            block("release_set_repository_invalid", f"{context} must be an object")
            continue
        try:
            _strict_keys(raw, {"repo_id", "target", "depends_on"}, context)
        except ReleaseSetError as exc:
            block("release_set_repository_invalid", str(exc))
            continue
        repo_id = str(raw.get("repo_id") or "").strip()
        if not repo_id:
            block("release_set_repo_id_missing", f"{context}.repo_id is required")
            continue
        if repo_id in normalized:
            block("release_set_repo_duplicate", f"repo_id {repo_id!r} appears more than once")
            continue
        target = raw.get("target")
        if not isinstance(target, dict):
            block("release_set_target_invalid", f"{context}.target must be an object", repo_id=repo_id)
            continue
        try:
            _strict_keys(target, {"version", "artifact", "sha256", "local_path"}, f"{context}.target")
        except ReleaseSetError as exc:
            block("release_set_target_invalid", str(exc), repo_id=repo_id)
        version = canonical_version_tag(str(target.get("version") or ""))
        if version is None:
            block("release_set_target_version_invalid", "target.version must be a canonical v-prefixed numeric version", repo_id=repo_id, value=target.get("version"))
        artifact = str(target.get("artifact") or "").strip()
        expected_artifact = canonical_artifact_filename(repo_id, version) if version else None
        if not artifact:
            block("release_set_target_artifact_missing", "target.artifact is required", repo_id=repo_id)
        elif expected_artifact and artifact != expected_artifact:
            block("release_set_target_artifact_noncanonical", "target.artifact does not match repo_id and target.version", repo_id=repo_id, expected=expected_artifact, actual=artifact)
        sha256 = str(target.get("sha256") or "").strip().lower() or None
        if sha256 is not None and not _SHA256_RE.fullmatch(sha256):
            block("release_set_target_sha256_invalid", "target.sha256 must be 64 lowercase hexadecimal characters", repo_id=repo_id)

        cfg = configured.get(repo_id)
        if cfg is None:
            block("release_set_repo_not_configured", "release-set repository is not joined in the project registry", repo_id=repo_id)
        repo_root = Path(str((cfg or {}).get("repo_root") or "")).expanduser() if cfg else None
        if repo_root is not None and not repo_root.is_dir():
            block("release_set_repo_root_missing", "configured repository root does not exist", repo_id=repo_id, repo_root=str(repo_root))

        local_path: Path | None = None
        explicit_local_path = target.get("local_path")
        if repo_root is not None and repo_root.is_dir():
            try:
                if isinstance(explicit_local_path, str) and explicit_local_path.strip():
                    local_path = _resolve_repo_relative(repo_root.resolve(), explicit_local_path.strip())
                    if not local_path.is_file():
                        block("release_set_target_artifact_not_found", "explicit target.local_path does not exist", repo_id=repo_id, local_path=str(local_path))
                elif artifact and (repo_root / artifact).is_file():
                    local_path = (repo_root / artifact).resolve()
            except ReleaseSetError as exc:
                block("release_set_target_local_path_invalid", str(exc), repo_id=repo_id)

        artifact_verification: dict[str, Any] | None = None
        effective_sha = sha256
        if local_path is not None and local_path.is_file():
            artifact_verification = verify_zip_artifact(local_path)
            if not artifact_verification.get("ok"):
                block("release_set_target_artifact_invalid", "local target artifact failed ZIP verification", repo_id=repo_id, verification=artifact_verification)
            observed_sha = artifact_verification.get("sha256")
            if sha256 and observed_sha != sha256:
                block("release_set_target_sha256_mismatch", "local target artifact SHA-256 does not match manifest", repo_id=repo_id, expected=sha256, actual=observed_sha)
            effective_sha = observed_sha or effective_sha
            observed_version = _read_zip_version(local_path)
            if version and canonical_version_tag(observed_version) != version:
                block("release_set_target_version_mismatch", "local target artifact VERSION does not match manifest", repo_id=repo_id, expected=version, actual=observed_version)
        elif sha256 is None:
            warn("release_set_target_artifact_unbound", "target has no verified local artifact and no SHA-256 binding", repo_id=repo_id)

        current = registry.current(repo_id=repo_id) if registry is not None and registry_state.get("ok") else None
        raw_dependencies = raw.get("depends_on", [])
        if raw_dependencies is None:
            raw_dependencies = []
        if not isinstance(raw_dependencies, list):
            block("release_set_dependencies_invalid", f"{context}.depends_on must be an array", repo_id=repo_id)
            raw_dependencies = []
        dependencies: list[dict[str, str]] = []
        seen_dependencies: set[str] = set()
        for dep_index, dependency in enumerate(raw_dependencies):
            dep_context = f"{context}.depends_on[{dep_index}]"
            if not isinstance(dependency, dict):
                block("release_set_dependency_invalid", f"{dep_context} must be an object", repo_id=repo_id)
                continue
            try:
                _strict_keys(dependency, {"repo_id", "constraint"}, dep_context)
            except ReleaseSetError as exc:
                block("release_set_dependency_invalid", str(exc), repo_id=repo_id)
                continue
            dependency_repo = str(dependency.get("repo_id") or "").strip()
            constraint = str(dependency.get("constraint") or "").strip()
            if not dependency_repo or not constraint:
                block("release_set_dependency_invalid", "dependency repo_id and constraint are required", repo_id=repo_id, dependency_index=dep_index)
                continue
            if dependency_repo == repo_id:
                block("release_set_self_dependency", "repository cannot depend on itself", repo_id=repo_id)
            if dependency_repo in seen_dependencies:
                block("release_set_dependency_duplicate", "dependency appears more than once", repo_id=repo_id, dependency_repo_id=dependency_repo)
                continue
            try:
                version_satisfies("v0.0.0", constraint)
            except ReleaseSetError as exc:
                block("release_set_dependency_constraint_invalid", str(exc), repo_id=repo_id, dependency_repo_id=dependency_repo)
            seen_dependencies.add(dependency_repo)
            dependencies.append({"repo_id": dependency_repo, "constraint": constraint})

        normalized[repo_id] = {
            "repo_id": repo_id,
            "repo_root": str(repo_root.resolve()) if repo_root is not None and repo_root.exists() else (str(repo_root) if repo_root else None),
            "role": (cfg or {}).get("role"),
            "target_version": version,
            "target_artifact": artifact or None,
            "target_sha256": effective_sha,
            "target_local_path": str(local_path) if local_path is not None else None,
            "target_artifact_verified": bool(artifact_verification and artifact_verification.get("ok")),
            "current_version": (current or {}).get("version"),
            "current_artifact": (current or {}).get("filename"),
            "current_sha256": (current or {}).get("sha256"),
            "change_required": bool(version and canonical_version_tag((current or {}).get("version")) != version),
            "depends_on": dependencies,
        }
        dependency_graph[repo_id] = {item["repo_id"] for item in dependencies}

    compatibility_rows: list[dict[str, Any]] = []
    for repo_id in sorted(normalized):
        for dependency in normalized[repo_id]["depends_on"]:
            dependency_repo = dependency["repo_id"]
            constraint = dependency["constraint"]
            if dependency_repo in normalized:
                resolved_version = normalized[dependency_repo].get("target_version")
                source = "release_set_target"
            else:
                external_current = registry.current(repo_id=dependency_repo) if registry is not None and registry_state.get("ok") else None
                resolved_version = (external_current or {}).get("version")
                source = "project_current"
                if dependency_repo not in configured:
                    block("release_set_dependency_repo_unknown", "dependency repository is neither in the release set nor configured in the project", repo_id=repo_id, dependency_repo_id=dependency_repo)
                elif external_current is None:
                    block("release_set_dependency_current_missing", "dependency outside the release set has no accepted/current artifact", repo_id=repo_id, dependency_repo_id=dependency_repo)
            compatible = False
            error: str | None = None
            if resolved_version:
                try:
                    compatible = version_satisfies(str(resolved_version), constraint)
                except ReleaseSetError as exc:
                    error = str(exc)
            if resolved_version and not compatible:
                block("release_set_dependency_incompatible", "resolved dependency version does not satisfy constraint", repo_id=repo_id, dependency_repo_id=dependency_repo, constraint=constraint, resolved_version=resolved_version, resolved_source=source)
            compatibility_rows.append({
                "consumer_repo_id": repo_id,
                "dependency_repo_id": dependency_repo,
                "constraint": constraint,
                "resolved_source": source,
                "resolved_version": resolved_version,
                "compatible": compatible,
                "status": "compatible" if compatible else ("missing" if not resolved_version else "incompatible"),
                "error": error,
            })

    order, waves, cycle_nodes = _topological_waves(normalized.keys(), dependency_graph)
    if cycle_nodes:
        block("release_set_dependency_cycle", "release-set dependency graph contains a cycle", cycle_repo_ids=cycle_nodes)

    for repo_id in sorted(normalized):
        repository_rows.append(normalized[repo_id])

    execution_ready = bool(repository_rows) and not blockers and all(
        row.get("target_sha256") and row.get("target_artifact_verified") for row in repository_rows
    )
    if not blockers and not execution_ready:
        warn("release_set_not_execution_bound", "dependency plan is valid but one or more target artifacts are not locally verified and hash-bound")

    digest_input = {
        "schema": RELEASE_SET_PLAN_SCHEMA,
        "schema_version": RELEASE_SET_PLAN_SCHEMA_VERSION,
        "release_set_id": release_set_id,
        "project_id": project_id,
        "repositories": repository_rows,
        "compatibility_matrix": compatibility_rows,
        "execution_order": order,
        "execution_waves": waves,
    }
    ok = not blockers
    return {
        "ok": ok,
        "schema": RELEASE_SET_PLAN_SCHEMA,
        "schema_version": RELEASE_SET_PLAN_SCHEMA_VERSION,
        "action": "release_set_plan",
        "status": "release_set_plan_ready" if ok else "release_set_plan_blocked",
        "repo_path": str(repo),
        "manifest_path": str(manifest_path),
        "release_set_id": release_set_id or None,
        "project_id": project_id or None,
        "registry_file": str(registry.path) if registry is not None else None,
        "repository_count": len(repository_rows),
        "repositories": repository_rows,
        "compatibility_matrix": {
            "columns": ["consumer_repo_id", "dependency_repo_id", "constraint", "resolved_source", "resolved_version", "compatible", "status"],
            "row_count": len(compatibility_rows),
            "rows": compatibility_rows,
        },
        "execution_order": order,
        "execution_waves": waves,
        "execution_ready": execution_ready,
        "plan_sha256": _canonical_json_digest(digest_input),
        "blockers": blockers,
        "warnings": warnings,
        "safety": {
            "read_only": True,
            "state_mutated": False,
            "repository_mutated": False,
            "registry_mutated": False,
            "project_source_mutated": False,
            "publication_performed": False,
            "adoption_performed": False,
            "execution_performed": False,
        },
    }

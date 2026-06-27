from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

VERSION_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?$")
PLAN_STATE_REL = Path("docs/project/plan-state.json")
REQUIRED_DOCS = (
    Path("docs/project/mvp.md"),
    Path("docs/project/definition-of-done.md"),
    Path("docs/project/plan.md"),
    Path("docs/project/status.md"),
    Path("docs/project/release-status.md"),
    Path("docs/project/decisions.md"),
    Path("docs/project/migration.md"),
    PLAN_STATE_REL,
)
REQUIRED_FIELDS = (
    "schema",
    "schema_version",
    "repo_id",
    "accepted_current_version",
    "accepted_current_artifact",
    "active_mvp",
    "last_completed_normal_slice_version",
    "last_completed_normal_slice",
    "active_candidate_version",
    "active_candidate_artifact",
    "active_slice",
    "next_normal_version",
    "next_normal_slice",
    "scope_advance_allowed",
    "repair_must_not_advance_scope",
    "release_mode",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _doc_text(repo_path: Path, rel: str) -> str:
    return _read(repo_path / rel)


def _version_from_repo(repo_path: Path) -> str | None:
    version_file = repo_path / "VERSION"
    if not version_file.exists():
        return None
    return version_file.read_text(encoding="utf-8").strip()


def _json_error(status: str, error: str, repo_path: Path) -> dict[str, Any]:
    return {
        "ok": False,
        "action": "project_validate_control_surface",
        "status": status,
        "repo_path": str(repo_path),
        "error": error,
        "errors": [error],
    }


def load_plan_state(repo_path: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    path = root / PLAN_STATE_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing required plan-state file: {PLAN_STATE_REL}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {PLAN_STATE_REL}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{PLAN_STATE_REL} must contain a JSON object")
    return data


def _current_block(text: str) -> str:
    # Prefer the first fenced block in the current-baseline section; this keeps
    # historical release table rows from being treated as current-state markers.
    marker = "## Current baseline"
    start = text.find(marker)
    if start < 0:
        return ""
    next_heading = text.find("\n## ", start + len(marker))
    section = text[start:] if next_heading < 0 else text[start:next_heading]
    fence_start = section.find("```")
    if fence_start < 0:
        return section
    fence_end = section.find("```", fence_start + 3)
    if fence_end < 0:
        return section
    return section[fence_start:fence_end]


def validate_project_control_surface(repo_path: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    missing = [str(rel) for rel in REQUIRED_DOCS if not (root / rel).is_file()]
    if missing:
        errors.append("missing required control-surface file(s): " + ", ".join(missing))

    try:
        state = load_plan_state(root)
    except ValueError as exc:
        return _json_error("control_surface_invalid", str(exc), root)

    for field in REQUIRED_FIELDS:
        if field not in state or state.get(field) in (None, ""):
            errors.append(f"plan-state missing required field: {field}")

    if state.get("schema") != "promptbranch.project.plan_state":
        errors.append("plan-state schema must be promptbranch.project.plan_state")
    if state.get("schema_version") != "1.0":
        errors.append("plan-state schema_version must be 1.0")

    for field in ("accepted_current_version", "last_completed_normal_slice_version", "active_candidate_version", "next_normal_version"):
        value = str(state.get(field) or "")
        if not VERSION_RE.match(value):
            errors.append(f"plan-state {field} must be a canonical v-prefixed version, got {value!r}")

    accepted_version = str(state.get("accepted_current_version") or "")
    accepted_artifact = str(state.get("accepted_current_artifact") or "")
    active_candidate_version = str(state.get("active_candidate_version") or "")
    active_candidate_artifact = str(state.get("active_candidate_artifact") or "")
    next_normal_version = str(state.get("next_normal_version") or "")
    next_normal_slice = str(state.get("next_normal_slice") or "")
    active_slice = str(state.get("active_slice") or "")
    release_mode = str(state.get("release_mode") or "")
    package_version = _version_from_repo(root)

    if package_version and package_version != active_candidate_version:
        errors.append(f"VERSION {package_version!r} must match plan-state active_candidate_version {active_candidate_version!r}")
    if active_candidate_version != next_normal_version and release_mode == "normal":
        errors.append("normal release active_candidate_version must equal next_normal_version")
    if active_slice != next_normal_slice and release_mode == "normal":
        errors.append("normal release active_slice must equal next_normal_slice")
    if accepted_artifact and accepted_version and accepted_version not in accepted_artifact:
        errors.append("accepted_current_artifact must include accepted_current_version")
    if active_candidate_artifact and active_candidate_version and active_candidate_version not in active_candidate_artifact:
        errors.append("active_candidate_artifact must include active_candidate_version")
    if state.get("repair_must_not_advance_scope") is not True:
        errors.append("repair_must_not_advance_scope must be true")

    if release_mode not in {"normal", "repair"}:
        errors.append("release_mode must be normal or repair")
    if release_mode == "repair" and state.get("scope_advance_allowed") is not False:
        errors.append("repair releases must set scope_advance_allowed=false")
    if release_mode == "repair" and not state.get("last_completed_repair_version"):
        errors.append("repair releases must record last_completed_repair_version")

    docs: dict[str, str] = {}
    for rel in ("docs/project/plan.md", "docs/project/status.md", "docs/project/release-status.md", "docs/project/definition-of-done.md", "docs/project/decisions.md", "docs/project/migration.md"):
        path = root / rel
        if path.is_file():
            docs[rel] = _doc_text(root, rel)

    status_current = _current_block(docs.get("docs/project/status.md", ""))
    plan_current = _current_block(docs.get("docs/project/plan.md", ""))
    for label, text in (("status current baseline", status_current), ("plan current baseline", plan_current)):
        if accepted_version and accepted_version not in text:
            errors.append(f"{label} must include accepted_current_version {accepted_version}")
        if accepted_artifact and accepted_artifact not in text:
            errors.append(f"{label} must include accepted_current_artifact {accepted_artifact}")
        if active_candidate_version and active_candidate_version not in text:
            errors.append(f"{label} must include active_candidate_version {active_candidate_version}")

    docs_required_tokens = {
        "docs/project/status.md": [accepted_artifact, active_candidate_artifact, next_normal_version, next_normal_slice, "## Next safe action"],
        "docs/project/plan.md": [accepted_artifact, active_candidate_artifact, next_normal_version, next_normal_slice, str(state.get("next_planned_version_after_acceptance") or "")],
        "docs/project/release-status.md": [accepted_artifact, active_candidate_artifact, next_normal_version, next_normal_slice],
        "docs/project/definition-of-done.md": ["DOD-132", "plan-state.json", "validate-control-surface"],
        "docs/project/decisions.md": ["ADR-PROJ-100", "plan-state.json", "anti-drift"],
        "docs/project/migration.md": ["v0.1.98", "plan-state.json", "anti-drift"],
    }
    for rel, tokens in docs_required_tokens.items():
        text = docs.get(rel, "")
        for token in [t for t in tokens if t]:
            if token not in text:
                errors.append(f"{rel} must include token {token!r}")

    stale_current_markers = ("active focused working candidate", "next normal target: deferred", "accepted/current baseline: chatgpt_claudecode_workflow-2_v0.1.76.zip")
    for marker in stale_current_markers:
        if marker in status_current or marker in plan_current:
            errors.append(f"current control-surface block still contains stale marker: {marker}")

    return {
        "ok": not errors,
        "action": "project_validate_control_surface",
        "status": "passed" if not errors else "failed",
        "repo_path": str(root),
        "plan_state_path": str(root / PLAN_STATE_REL),
        "schema": state.get("schema"),
        "schema_version": state.get("schema_version"),
        "accepted_current_version": accepted_version,
        "accepted_current_artifact": accepted_artifact,
        "active_candidate_version": active_candidate_version,
        "active_candidate_artifact": active_candidate_artifact,
        "active_mvp": state.get("active_mvp"),
        "active_slice": active_slice,
        "next_normal_version": next_normal_version,
        "next_normal_slice": next_normal_slice,
        "release_mode": release_mode,
        "scope_advance_allowed": state.get("scope_advance_allowed"),
        "repair_must_not_advance_scope": state.get("repair_must_not_advance_scope"),
        "required_files": [str(rel) for rel in REQUIRED_DOCS],
        "missing_files": missing,
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
    }

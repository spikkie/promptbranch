from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

VERSION_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)*$")
PLAN_STATE_REL = Path("docs/project/plan-state.json")
REQUIRED_DOCS = (
    Path("PROJECT_SETTINGS.md"),
    Path("AGENTS.md"),
    Path("docs/project/project-authority-graph-v0.1.109.json"),
    Path("docs/project/promptbranch-behavioral-surface-v0.1.109.1.json"),
    Path("docs/project/behavioral-surface.md"),
    Path("docs/project/mvp.md"),
    Path("docs/project/definition-of-done.md"),
    Path("docs/project/plan.md"),
    Path("docs/project/status.md"),
    Path("docs/project/release-status.md"),
    Path("docs/project/decisions.md"),
    Path("docs/project/migration.md"),
    PLAN_STATE_REL,
    Path("docs/project/architecture.md"),
    Path("docs/project/slice-horizon.md"),
    Path("docs/backlog/README.md"),
    Path("docs/backlog/backlog.json"),
    Path("docs/backlog/ISSUE-001-global-release-lifecycle-engine.md"),
    Path("docs/backlog/PBAI-001-full-ai-application-architecture.md"),
    Path(".promptbranch-ai.json"),
    Path("promptbranch_protocol/schemas/application.architecture.schema.json"),
    Path("docs/release-v0.1.112.md"),
)
REQUIRED_FIELDS = (
    "schema",
    "schema_version",
    "repo_id",
    "accepted_current_version",
    "accepted_current_artifact",
    "active_mvp",
    "architecture_goal",
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
    "rolling_slice_horizon",
    "architecture_invariants",
    "slice_derivation_inputs",
    "replan_rules",
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




def build_project_next_slice_payload(repo_path: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    validation = validate_project_control_surface(root)
    if not validation.get("ok"):
        return {
            **validation,
            "action": "project_next_slice",
            "status": "control_surface_invalid",
            "next_slice_available": False,
        }
    state = load_plan_state(root)
    horizon = state.get("rolling_slice_horizon") if isinstance(state.get("rolling_slice_horizon"), list) else []
    active = next((item for item in horizon if isinstance(item, dict) and item.get("status") == "active"), None)
    planned_after_acceptance = next((item for item in horizon if isinstance(item, dict) and item.get("status") == "planned_after_acceptance"), None)
    return {
        "ok": True,
        "action": "project_next_slice",
        "status": "next_slice_ready",
        "repo_path": str(root),
        "baseline_version": state.get("accepted_current_version"),
        "baseline_artifact": state.get("accepted_current_artifact"),
        "release_mode": state.get("release_mode"),
        "active_mvp": state.get("active_mvp"),
        "architecture_goal": state.get("architecture_goal"),
        "next_normal_version": state.get("next_normal_version"),
        "next_normal_slice": state.get("next_normal_slice"),
        "active_slice": state.get("active_slice"),
        "active_candidate_version": state.get("active_candidate_version"),
        "active_candidate_artifact": state.get("active_candidate_artifact"),
        "next_slice_after_acceptance_version": state.get("next_planned_version_after_acceptance"),
        "next_slice_after_acceptance": state.get("next_planned_slice_after_acceptance"),
        "scope_advance_allowed": state.get("scope_advance_allowed"),
        "repair_scope_advance_allowed": False,
        "architecture_invariants_checked": True,
        "control_surface_validated": True,
        "active_horizon_item": active,
        "planned_after_acceptance_horizon_item": planned_after_acceptance,
        "rolling_slice_horizon": horizon,
        "out_of_scope": state.get("out_of_scope") or [],
    }

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

    horizon = state.get("rolling_slice_horizon")
    if not isinstance(horizon, list):
        errors.append("plan-state rolling_slice_horizon must be a list")
        horizon = []
    elif not (4 <= len(horizon) <= 6):
        errors.append("plan-state rolling_slice_horizon must contain 4 to 6 slices")

    active_items = [item for item in horizon if isinstance(item, dict) and item.get("status") == "active"]
    planned_after_items = [item for item in horizon if isinstance(item, dict) and item.get("status") == "planned_after_acceptance"]
    if len(active_items) != 1:
        errors.append("rolling_slice_horizon must contain exactly one active slice")
    if len(planned_after_items) != 1:
        errors.append("rolling_slice_horizon must contain exactly one planned_after_acceptance slice")
    if active_items:
        active_item = active_items[0]
        if release_mode == "normal":
            if active_item.get("version") != next_normal_version:
                errors.append("active horizon item version must equal next_normal_version")
            if active_item.get("slice") != next_normal_slice:
                errors.append("active horizon item slice must equal next_normal_slice")
        elif release_mode == "repair":
            if active_item.get("version") != active_candidate_version:
                errors.append("repair active horizon item version must equal active_candidate_version")
            if active_item.get("slice") != active_slice:
                errors.append("repair active horizon item slice must equal active_slice")
            if active_item.get("release_mode") != "repair":
                errors.append("repair active horizon item release_mode must be repair")
    if planned_after_items:
        planned_item = planned_after_items[0]
        if planned_item.get("version") != state.get("next_planned_version_after_acceptance"):
            errors.append("planned_after_acceptance horizon item version must equal next_planned_version_after_acceptance")
        if planned_item.get("slice") != state.get("next_planned_slice_after_acceptance"):
            errors.append("planned_after_acceptance horizon item slice must equal next_planned_slice_after_acceptance")

    for index, item in enumerate(horizon):
        if not isinstance(item, dict):
            errors.append(f"rolling_slice_horizon item {index} must be an object")
            continue
        for field in ("version", "slice", "status", "release_mode", "scope"):
            if not item.get(field):
                errors.append(f"rolling_slice_horizon item {index} missing field: {field}")
        if item.get("version") and not VERSION_RE.match(str(item.get("version"))):
            errors.append(f"rolling_slice_horizon item {index} version must be canonical v-prefixed")

    invariants = state.get("architecture_invariants")
    if not isinstance(invariants, list) or len(invariants) < 5:
        errors.append("plan-state architecture_invariants must contain at least five entries")
    else:
        required_invariant_fragments = ("artifact-first", "control surface", "repair releases", "ChatGPT Project deletion", "repo-relative")
        invariant_text = "\n".join(str(item) for item in invariants)
        for fragment in required_invariant_fragments:
            if fragment not in invariant_text:
                errors.append(f"architecture_invariants must include {fragment!r}")

    for list_field in ("slice_derivation_inputs", "replan_rules"):
        value = state.get(list_field)
        if not isinstance(value, list) or len(value) < 4:
            errors.append(f"plan-state {list_field} must contain at least four entries")

    backlog_path = root / "docs/backlog/backlog.json"
    if backlog_path.is_file():
        try:
            backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid docs/backlog/backlog.json: {exc}")
        else:
            if backlog.get("schema") != "promptbranch.backlog":
                errors.append("backlog schema must be promptbranch.backlog")
            if backlog.get("schema_version") != "1.0":
                errors.append("backlog schema_version must be 1.0")
            if backlog.get("repo_id") != state.get("repo_id"):
                errors.append("backlog repo_id must match plan-state repo_id")
            tickets = backlog.get("tickets")
            if not isinstance(tickets, list) or not tickets:
                errors.append("backlog tickets must be a non-empty list")
            else:
                ids = [str(ticket.get("id") or "") for ticket in tickets if isinstance(ticket, dict)]
                if len(ids) != len(tickets) or any(not ticket_id for ticket_id in ids):
                    errors.append("every backlog ticket must have a non-empty id")
                if len(ids) != len(set(ids)):
                    errors.append("backlog ticket ids must be unique")
                if ids != ["ISSUE-001", "PBAI-001"]:
                    errors.append("v0.1.110 backlog must contain ISSUE-001 then PBAI-001")
                for ticket in tickets:
                    if not isinstance(ticket, dict):
                        continue
                    status = str(ticket.get("status") or "")
                    allowed_statuses = {"open", "in_progress", "implemented_candidate", "closed"}
                    if status not in allowed_statuses:
                        errors.append(
                            f"backlog ticket {ticket.get('id')!r} has unsupported status {status!r}"
                        )
                    if status == "implemented_candidate" and not str(ticket.get("implemented_in") or "").strip():
                        errors.append(
                            f"backlog ticket {ticket.get('id')!r} implemented_candidate requires implemented_in"
                        )
                    rel_path = str(ticket.get("path") or "")
                    if not rel_path or Path(rel_path).is_absolute() or ".." in Path(rel_path).parts:
                        errors.append(f"backlog ticket {ticket.get('id')!r} has invalid path")
                    elif not (root / rel_path).is_file():
                        errors.append(f"backlog ticket {ticket.get('id')!r} path does not exist: {rel_path}")

    docs: dict[str, str] = {}
    for rel in ("docs/project/plan.md", "docs/project/status.md", "docs/project/release-status.md", "docs/project/definition-of-done.md", "docs/project/decisions.md", "docs/project/migration.md", "docs/project/architecture.md", "docs/project/slice-horizon.md"):
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

    horizon_versions = [str(item.get("version")) for item in horizon if isinstance(item, dict) and item.get("version")]
    planned_after_version = str(state.get("next_planned_version_after_acceptance") or "")
    docs_required_tokens = {
        "docs/project/status.md": [accepted_artifact, active_candidate_artifact, next_normal_version, next_normal_slice, "## Next safe action", planned_after_version],
        "docs/project/plan.md": [accepted_artifact, active_candidate_artifact, next_normal_version, next_normal_slice, planned_after_version, "Rolling horizon authority"],
        "docs/project/release-status.md": [accepted_artifact, active_candidate_artifact, next_normal_version, next_normal_slice, planned_after_version],
        "docs/project/definition-of-done.md": ["DOD-298", "DOD-300", "DOD-314", "DOD-317", "project next-slice", "read-only validation command"],
        "docs/project/decisions.md": ["ADR-PROJ-108", "ADR-PROJ-112", next_normal_version, planned_after_version],
        "docs/project/migration.md": [next_normal_version, planned_after_version],
        "docs/project/architecture.md": ["controlled problem-solving loop", "Fixed architecture invariants", "Repair releases must not advance scope", "PBAI-001 application architecture invariant"],
        "docs/project/slice-horizon.md": horizon_versions + ["Repair horizon rule"],
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
        "architecture_goal": state.get("architecture_goal"),
        "active_slice": active_slice,
        "next_normal_version": next_normal_version,
        "next_normal_slice": next_normal_slice,
        "release_mode": release_mode,
        "scope_advance_allowed": state.get("scope_advance_allowed"),
        "repair_must_not_advance_scope": state.get("repair_must_not_advance_scope"),
        "rolling_slice_horizon": horizon,
        "required_files": [str(rel) for rel in REQUIRED_DOCS],
        "missing_files": missing,
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
    }

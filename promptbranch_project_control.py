from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from promptbranch_artifacts import ArtifactRegistry, verify_zip_artifact
from promptbranch_project import load_repo_identity, project_registry_dir

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
    Path("promptbranch_protocol/schemas/application.registry.schema.json"),
    Path(".promptbranch/ai-registry.json"),
)
REQUIRED_FIELDS = (
    "schema",
    "schema_version",
    "repo_id",
    "accepted_current_version",
    "accepted_current_artifact",
    "accepted_current_sha256",
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





def authoritative_project_current(repo_path: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    try:
        identity = load_repo_identity(root)
    except ValueError as exc:
        return {"checked": True, "ok": False, "status": "project_identity_invalid", "error": str(exc)}
    if identity is None:
        return {"checked": False, "ok": True, "status": "project_identity_missing"}
    registry = ArtifactRegistry(project_registry_dir(identity.project_id))
    inspected = registry.inspect()
    if not inspected.get("ok"):
        if inspected.get("status") == "artifact_registry_missing":
            return {
                "checked": False,
                "ok": True,
                "status": "artifact_registry_missing",
                "project_id": identity.project_id,
                "repo_id": identity.repo_id,
                "registry_file": str(registry.path),
            }
        return {
            "checked": True,
            "ok": False,
            "status": str(inspected.get("status") or "artifact_registry_invalid"),
            "error": str(inspected.get("error") or "artifact registry unavailable"),
            "project_id": identity.project_id,
            "repo_id": identity.repo_id,
            "registry_file": str(registry.path),
        }
    current = registry.current(repo_id=identity.repo_id)
    if not isinstance(current, dict):
        return {
            "checked": True,
            "ok": False,
            "status": "authoritative_current_missing",
            "project_id": identity.project_id,
            "repo_id": identity.repo_id,
            "registry_file": str(registry.path),
            "current": None,
        }
    object_path = Path(str(current.get("path") or "")).expanduser()
    object_exists = object_path.is_file()
    sha_exact = False
    if object_exists:
        verification = verify_zip_artifact(object_path)
        sha_exact = bool(verification.get("ok")) and str(verification.get("sha256") or "") == str(current.get("sha256") or "")
    checks = {
        "kind_adopted_release": current.get("kind") == "adopted_release",
        "object_exists": object_exists,
        "object_sha_exact": sha_exact,
    }
    return {
        "checked": True,
        "ok": all(checks.values()),
        "status": "authoritative_current_verified" if all(checks.values()) else "authoritative_current_invalid",
        "project_id": identity.project_id,
        "repo_id": identity.repo_id,
        "registry_file": str(registry.path),
        "current": current,
        "checks": checks,
    }


def _replace_current_baseline_block(path: Path, lines: list[str]) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    marker = "## Current baseline"
    start = text.find(marker)
    if start < 0:
        return False
    fence_start = text.find("```", start)
    if fence_start < 0:
        return False
    fence_end = text.find("```", fence_start + 3)
    if fence_end < 0:
        return False
    new_block = "```text\n" + "\n".join(lines) + "\n```"
    updated = text[:fence_start] + new_block + text[fence_end + 3:]
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def synchronize_project_control_after_adoption(
    repo_path: str | Path,
    *,
    version: str,
    artifact_filename: str,
    sha256: str,
) -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    state_path = root / PLAN_STATE_REL
    if not state_path.is_file():
        return {"ok": True, "status": "control_projection_not_applicable", "performed": False, "reason": "plan_state_missing"}
    state = load_plan_state(root)
    repo_id = str(state.get("repo_id") or "").strip()
    next_normal_version = str(state.get("next_normal_version") or "").strip()
    next_normal_slice = str(state.get("next_normal_slice") or "").strip()
    next_normal_artifact = str(state.get("next_normal_artifact") or (f"{repo_id}_{next_normal_version}.zip" if repo_id and next_normal_version else ""))
    previous_active_slice = str(state.get("active_slice") or "").strip()

    horizon = state.get("rolling_slice_horizon") if isinstance(state.get("rolling_slice_horizon"), list) else []
    target_item = next((item for item in horizon if isinstance(item, dict) and item.get("version") == version), None)
    next_item = next((item for item in horizon if isinstance(item, dict) and item.get("version") == next_normal_version), None)
    if target_item is None:
        return {"ok": False, "status": "control_projection_target_missing", "performed": False, "error": f"rolling horizon has no target release {version}"}
    if next_item is None:
        return {"ok": False, "status": "control_projection_next_normal_missing", "performed": False, "error": f"rolling horizon has no next normal release {next_normal_version}"}

    next_index = horizon.index(next_item)
    planned_after = next((item for item in horizon[next_index + 1:] if isinstance(item, dict) and str(item.get("version") or "")), None)
    if planned_after is None:
        return {"ok": False, "status": "control_projection_future_slice_missing", "performed": False, "error": "rolling horizon has no slice after next normal"}

    for item in horizon:
        if not isinstance(item, dict):
            continue
        item_version = str(item.get("version") or "")
        if item_version == version:
            item["status"] = "accepted_current"
        elif item_version == next_normal_version:
            item["status"] = "active"
            item["release_mode"] = "normal"
        elif item is planned_after:
            item["status"] = "planned_after_acceptance"
        elif item.get("status") in {"accepted_current", "active", "planned_after_acceptance"}:
            item["status"] = "superseded" if item.get("status") == "accepted_current" else "planned"

    state.update({
        "accepted_current_version": version,
        "accepted_current_artifact": artifact_filename,
        "accepted_current_sha256": sha256,
        "last_completed_repair_version": version,
        "last_completed_repair": previous_active_slice or version,
        "active_candidate_version": next_normal_version,
        "active_candidate_artifact": next_normal_artifact,
        "active_candidate_transport_artifact": next_normal_artifact,
        "active_candidate_base_version": version,
        "active_candidate_status": "planned",
        "active_slice": next_normal_slice,
        "release_mode": "normal",
        "scope_advance_allowed": True,
        "next_planned_version_after_acceptance": str(planned_after.get("version") or ""),
        "next_planned_slice_after_acceptance": str(planned_after.get("slice") or ""),
        "next_planned_artifact_after_acceptance": str(planned_after.get("artifact") or planned_after.get("transport_artifact") or ""),
        "updated_for": version,
        "rolling_slice_horizon": horizon,
    })
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    baseline_lines = [
        f"accepted_current_version: {version}",
        f"accepted_current_artifact: {artifact_filename}",
        f"accepted_current_sha256: {sha256}",
        f"active_candidate_version: {next_normal_version}",
        f"active_candidate_artifact: {next_normal_artifact}",
        f"active_candidate_base_version: {version}",
        f"next_normal_version: {next_normal_version}",
        f"next_normal_slice: {next_normal_slice}",
    ]
    changed_docs: list[str] = []
    for rel in (Path("docs/project/plan.md"), Path("docs/project/status.md")):
        if _replace_current_baseline_block(root / rel, baseline_lines):
            changed_docs.append(str(rel))

    release_status = root / "docs/project/release-status.md"
    if release_status.is_file():
        text = release_status.read_text(encoding="utf-8")
        marker = "<!-- promptbranch-live-control-projection -->"
        block = (
            f"{marker}\n"
            f"> Live control projection after adoption: accepted/current `{version}` (`{artifact_filename}`), "
            f"SHA-256 `{sha256}`. Next normal slice remains `{next_normal_slice}` with artifact `{next_normal_artifact}`.\n\n"
        )
        if marker in text:
            text = re.sub(r"<!-- promptbranch-live-control-projection -->.*?\n\n", block, text, count=1, flags=re.S)
        else:
            text = block + text
        release_status.write_text(text, encoding="utf-8")
        changed_docs.append("docs/project/release-status.md")

    return {
        "ok": True,
        "status": "control_projection_synchronized",
        "performed": True,
        "accepted_current_version": version,
        "accepted_current_artifact": artifact_filename,
        "accepted_current_sha256": sha256,
        "active_candidate_version": next_normal_version,
        "next_planned_version_after_acceptance": state.get("next_planned_version_after_acceptance"),
        "changed_files": [str(PLAN_STATE_REL), *changed_docs],
    }

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
    accepted_sha256 = str(state.get("accepted_current_sha256") or "")
    active_candidate_version = str(state.get("active_candidate_version") or "")
    active_candidate_artifact = str(state.get("active_candidate_artifact") or "")
    active_release_doc = Path(f"docs/release-{active_candidate_version}.md") if active_candidate_version and str(state.get("active_candidate_status") or "") != "planned" else None
    if active_release_doc is not None and not (root / active_release_doc).is_file():
        missing.append(str(active_release_doc))
        errors.append(f"missing required active release document: {active_release_doc}")
    next_normal_version = str(state.get("next_normal_version") or "")
    next_normal_slice = str(state.get("next_normal_slice") or "")
    active_slice = str(state.get("active_slice") or "")
    release_mode = str(state.get("release_mode") or "")
    package_version = _version_from_repo(root)

    active_candidate_status = str(state.get("active_candidate_status") or "")
    package_matches_candidate = package_version == active_candidate_version
    package_matches_accepted_planned = package_version == accepted_version and active_candidate_status == "planned"
    if package_version and not (package_matches_candidate or package_matches_accepted_planned):
        errors.append(f"VERSION {package_version!r} must match active candidate {active_candidate_version!r}, or accepted/current {accepted_version!r} when the next candidate is only planned")
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
    elif not (4 <= len(horizon) <= 12):
        errors.append("plan-state rolling_slice_horizon must contain 4 to 12 slices")

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

    authoritative = authoritative_project_current(root)
    authoritative_current = authoritative.get("current") if isinstance(authoritative.get("current"), dict) else None
    projection_matches_authoritative: bool | None = None
    if authoritative.get("checked") is True:
        if authoritative.get("ok") is not True or authoritative_current is None:
            errors.append(f"authoritative project current is invalid: {authoritative.get('status')}")
            projection_matches_authoritative = False
        else:
            current_version = str(authoritative_current.get("version") or "")
            current_artifact = str(authoritative_current.get("filename") or "")
            current_sha256 = str(authoritative_current.get("sha256") or "")
            projection_matches_authoritative = (
                accepted_version == current_version
                and accepted_artifact == current_artifact
                and accepted_sha256 == current_sha256
            )
            if accepted_version != current_version:
                errors.append(f"tracked accepted_current_version {accepted_version!r} differs from authoritative current {current_version!r}")
            if accepted_artifact != current_artifact:
                errors.append(f"tracked accepted_current_artifact {accepted_artifact!r} differs from authoritative current {current_artifact!r}")
            if accepted_sha256 != current_sha256:
                errors.append("tracked accepted_current_sha256 differs from authoritative current SHA-256")
            if active_candidate_version == current_version:
                errors.append("active_candidate_version is already authoritative current; control projection was not advanced after adoption")

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
        "accepted_current_sha256": accepted_sha256,
        "authoritative_current_checked": authoritative.get("checked"),
        "authoritative_current_status": authoritative.get("status"),
        "authoritative_current_version": (authoritative_current or {}).get("version"),
        "authoritative_current_sha256": (authoritative_current or {}).get("sha256"),
        "control_projection_matches_authoritative_current": projection_matches_authoritative,
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
        "required_files": [str(rel) for rel in REQUIRED_DOCS] + ([str(active_release_doc)] if active_release_doc is not None else []),
        "missing_files": missing,
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
    }

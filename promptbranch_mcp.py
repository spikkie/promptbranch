"""Read-only MCP/Ollama planning scaffold for Promptbranch.

This module does not start an MCP JSON-RPC server yet.  It defines the local
read-only tool surface and policy-gated agent planning contracts that the MCP
server can expose later without giving a local LLM direct mutation authority.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from promptbranch_artifacts import ArtifactRegistry, iter_repo_files, read_version
from promptbranch_shell_model import ToolRisk, required_prechecks_for_action, risk_for_action
from promptbranch_state import ConversationStateStore, resolve_profile_dir

MCP_SCHEMA_VERSION = 1
DEFAULT_AGENT_MAX_FILES = 80


@dataclass(frozen=True)
class McpToolSpec:
    name: str
    description: str
    risk: ToolRisk = ToolRisk.READ
    read_only: bool = True
    requires_confirmation: bool = False
    prechecks: tuple[str, ...] = ()
    command_hint: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["risk"] = self.risk.value
        payload["prechecks"] = list(self.prechecks)
        payload["command_hint"] = list(self.command_hint)
        return payload


READ_ONLY_MCP_TOOLS: tuple[McpToolSpec, ...] = (
    McpToolSpec(
        name="promptbranch.state.read",
        description="Read current Promptbranch workspace/task/artifact state from .pb_profile.",
        command_hint=("pb", "state", "--json"),
    ),
    McpToolSpec(
        name="promptbranch.workspace.current",
        description="Read the selected workspace/project scope.",
        command_hint=("pb", "ws", "current", "--json"),
    ),
    McpToolSpec(
        name="promptbranch.task.current",
        description="Read the selected task/chat scope.",
        command_hint=("pb", "task", "current", "--json"),
    ),
    McpToolSpec(
        name="filesystem.list",
        description="List repo files using Promptbranch packaging exclusions.",
    ),
    McpToolSpec(
        name="filesystem.read",
        description="Read bounded local repo files for diagnostics and planning.",
    ),
    McpToolSpec(
        name="git.status",
        description="Read git branch, short SHA, and porcelain status.",
        command_hint=("git", "status", "--short", "--branch"),
    ),
    McpToolSpec(
        name="git.diff.summary",
        description="Read git diff summary/statistics without modifying the repo.",
        command_hint=("git", "diff", "--stat"),
    ),
    McpToolSpec(
        name="artifact.registry.current",
        description="Read the current local Promptbranch artifact registry entry.",
        command_hint=("pb", "artifact", "current", "--json"),
    ),
    McpToolSpec(
        name="artifact.verify",
        description="Verify ZIP layout and integrity as a read-only check.",
        command_hint=("pb", "artifact", "verify", "--json"),
    ),
)

CONTROLLED_WRITE_MCP_TOOLS: tuple[McpToolSpec, ...] = (
    McpToolSpec(
        name="test.smoke.run",
        description="Run Promptbranch smoke tests through the deterministic executor.",
        risk=ToolRisk.EXTERNAL_PROCESS,
        read_only=False,
        requires_confirmation=False,
        prechecks=required_prechecks_for_action("test_smoke"),
        command_hint=("pb", "test", "smoke", "--json"),
    ),
    McpToolSpec(
        name="artifact.release.create",
        description="Create a release ZIP through the deterministic artifact command.",
        risk=ToolRisk.WRITE,
        read_only=False,
        requires_confirmation=False,
        prechecks=required_prechecks_for_action("artifact_release"),
        command_hint=("pb", "artifact", "release", ".", "--json"),
    ),
    McpToolSpec(
        name="promptbranch.src.sync",
        description="Package and upload a source snapshot transactionally.",
        risk=ToolRisk.WRITE,
        read_only=False,
        requires_confirmation=False,
        prechecks=required_prechecks_for_action("src_sync"),
        command_hint=("pb", "src", "sync", ".", "--json"),
    ),
)


@dataclass(frozen=True)
class AgentPlan:
    request: str
    intent: str
    action: str
    risk: ToolRisk
    auto_allowed: bool
    requires_confirmation: bool
    prechecks: tuple[str, ...]
    suggested_commands: tuple[tuple[str, ...], ...]
    notes: tuple[str, ...] = ()
    args: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "intent": self.intent,
            "action": self.action,
            "risk": self.risk.value,
            "auto_allowed": self.auto_allowed,
            "requires_confirmation": self.requires_confirmation,
            "prechecks": list(self.prechecks),
            "suggested_commands": [list(item) for item in self.suggested_commands],
            "notes": list(self.notes),
            "args": self.args,
        }


def mcp_tool_manifest(*, include_controlled_writes: bool = False) -> dict[str, Any]:
    tools = list(READ_ONLY_MCP_TOOLS)
    if include_controlled_writes:
        tools.extend(CONTROLLED_WRITE_MCP_TOOLS)
    return {
        "ok": True,
        "schema_version": MCP_SCHEMA_VERSION,
        "action": "mcp_manifest",
        "mode": "read_only" if not include_controlled_writes else "read_only_plus_controlled_writes",
        "tool_count": len(tools),
        "tools": [tool.to_dict() for tool in tools],
        "policy": {
            "local_llm_may_execute": "read_only_tools_only",
            "writes_require": "deterministic_executor_prechecks",
            "destructive_tools": "not_exposed_in_default_manifest",
            "state_updates": "after_verified_outcomes_only",
        },
    }


def _run_read_only_command(args: list[str], *, cwd: Path, timeout: float = 3.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"ok": False, "error": f"command not found: {args[0]}", "argv": args}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "argv": args, "timeout_seconds": timeout}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "argv": args}
    return {
        "ok": completed.returncode == 0,
        "argv": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _git_snapshot(repo_path: Path) -> dict[str, Any]:
    status = _run_read_only_command(["git", "status", "--short", "--branch"], cwd=repo_path)
    branch = _run_read_only_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    short_sha = _run_read_only_command(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path)
    diff_stat = _run_read_only_command(["git", "diff", "--stat"], cwd=repo_path)
    is_repo = bool(status.get("ok"))
    status_lines = str(status.get("stdout") or "").splitlines()
    dirty_lines = [line for line in status_lines if line and not line.startswith("##")]
    return {
        "is_repo": is_repo,
        "branch": branch.get("stdout") if branch.get("ok") else None,
        "short_sha": short_sha.get("stdout") if short_sha.get("ok") else None,
        "dirty": bool(dirty_lines),
        "status_lines": status_lines,
        "diff_stat": diff_stat.get("stdout") if diff_stat.get("ok") else "",
        "errors": [item for item in (status, branch, short_sha, diff_stat) if not item.get("ok")],
    }


def _safe_file_sample(repo_path: Path, *, max_files: int) -> tuple[int, list[str], list[str]]:
    try:
        files = iter_repo_files(repo_path)
    except ValueError:
        return 0, [], [f"not a directory: {repo_path}"]
    except OSError as exc:
        return 0, [], [str(exc)]
    rels = [path.relative_to(repo_path).as_posix() for path in files]
    return len(rels), rels[:max_files], []


def inspect_local_context(
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    max_files: int = DEFAULT_AGENT_MAX_FILES,
    state_snapshot: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    resolved_profile = resolve_profile_dir(str(profile_dir) if profile_dir else None)
    store_snapshot = state_snapshot or ConversationStateStore(str(resolved_profile)).snapshot(None)
    registry = ArtifactRegistry(resolved_profile)
    file_count, file_sample, file_errors = _safe_file_sample(root, max_files=max_files)
    manifest = mcp_tool_manifest(include_controlled_writes=False)
    payload = {
        "ok": True,
        "action": "agent_inspect",
        "mode": "read_only",
        "repo": {
            "path": str(root),
            "exists": root.exists(),
            "is_dir": root.is_dir(),
            "version": read_version(root) if root.is_dir() else None,
            "file_count": file_count,
            "file_sample": file_sample,
            "file_sample_truncated": file_count > len(file_sample),
            "errors": file_errors,
        },
        "git": _git_snapshot(root) if root.is_dir() else {"is_repo": False, "errors": ["repo path is not a directory"]},
        "state": store_snapshot,
        "artifact_registry": {
            "path": str(registry.path),
            "artifact_dir": str(registry.artifact_dir),
            "count": len(registry.list()),
            "current": registry.current(),
        },
        "mcp": {
            "schema_version": MCP_SCHEMA_VERSION,
            "default_mode": "read_only",
            "tool_count": manifest["tool_count"],
            "tools": [tool["name"] for tool in manifest["tools"]],
        },
        "ollama": {
            "enabled": False,
            "reason": "v0.0.138 exposes deterministic read-only planning first; Ollama integration remains a later adapter.",
        },
    }
    return payload


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)


def plan_agent_request(request: str, *, repo_path: str | Path = ".") -> dict[str, Any]:
    text = " ".join(str(request or "").strip().lower().split())
    notes: list[str] = []
    args: dict[str, Any] = {"repo_path": str(Path(repo_path).expanduser())}

    if not text:
        action = "agent_inspect"
        intent = "inspect_context"
        commands = (("pb", "agent", "inspect", str(repo_path), "--json"),)
    elif _contains_any(text, ("remove source", "delete source", "rm source", "source remove", "source rm")):
        action = "src_rm"
        intent = "remove_source"
        commands = (("pb", "src", "rm", "<source>", "--exact"),)
        notes.append("destructive source removal must use snapshot and collateral-change checks")
    elif _contains_any(text, ("source add", "add source", "upload", "pbsa")) or text.endswith(".zip"):
        action = "src_add"
        intent = "add_source"
        commands = (("pb", "src", "add", "<file>", "--json"),)
        notes.append("source add is a write; executor must verify persistence before state updates")
    elif _contains_any(text, ("src sync", "sync repo", "sync source", "sync .")):
        action = "src_sync"
        intent = "sync_repo_source"
        commands = (("pb", "src", "sync", str(repo_path), "--json"),)
    elif _contains_any(text, ("release", "package", "make zip", "artifact release")):
        action = "artifact_release"
        intent = "create_release_artifact"
        commands = (("pb", "artifact", "release", str(repo_path), "--json"),)
    elif _contains_any(text, ("test", "smoke")):
        action = "test_smoke"
        intent = "run_smoke_tests"
        commands = (("pb", "test", "smoke", "--json"),)
    elif _contains_any(text, ("task list", "list tasks", "chats", "chat list")):
        action = "task_list"
        intent = "list_tasks"
        commands = (("pb", "task", "list", "--json"),)
    elif _contains_any(text, ("state", "current", "where am i", "workspace", "task current")):
        action = "debug_dump_state"
        intent = "read_state"
        commands = (("pb", "ws", "current", "--json"), ("pb", "task", "current", "--json"), ("pb", "artifact", "current", "--json"))
    else:
        action = "agent_inspect"
        intent = "inspect_context"
        commands = (("pb", "agent", "inspect", str(repo_path), "--json"),)
        notes.append("deterministic classifier did not infer a mutation; defaulting to read-only inspection")

    risk = risk_for_action(action)
    prechecks = required_prechecks_for_action(action)
    auto_allowed = risk == ToolRisk.READ
    requires_confirmation = risk in {ToolRisk.WRITE, ToolRisk.DESTRUCTIVE, ToolRisk.EXTERNAL_PROCESS}
    if risk != ToolRisk.READ:
        notes.append("local LLM may propose this action, but deterministic executor must validate prechecks before execution")

    plan = AgentPlan(
        request=request,
        intent=intent,
        action=action,
        risk=risk,
        auto_allowed=auto_allowed,
        requires_confirmation=requires_confirmation,
        prechecks=prechecks,
        suggested_commands=commands,
        notes=tuple(notes),
        args=args,
    )
    return {
        "ok": True,
        "action": "agent_plan",
        "mode": "policy_gated",
        "planner": "deterministic_v1",
        "plan": plan.to_dict(),
    }


def agent_doctor(
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    state_snapshot: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    context = inspect_local_context(
        repo_path=repo_path,
        profile_dir=profile_dir,
        state_snapshot=state_snapshot,
        max_files=20,
    )
    state = context.get("state") if isinstance(context.get("state"), dict) else {}
    workspace_selected = bool(state.get("resolved_project_home_url") or state.get("current_project_home_url"))
    repo = context.get("repo") if isinstance(context.get("repo"), dict) else {}
    git = context.get("git") if isinstance(context.get("git"), dict) else {}
    checks = {
        "repo_path_exists": bool(repo.get("exists")),
        "repo_path_is_dir": bool(repo.get("is_dir")),
        "workspace_selected": workspace_selected,
        "profile_state_readable": bool(state.get("state_file")),
        "git_available_or_repo_optional": bool(git.get("is_repo")) or bool(git.get("errors")),
        "mcp_default_manifest_read_only": all(tool.get("read_only") for tool in mcp_tool_manifest()["tools"]),
    }
    return {
        "ok": all(checks.values()),
        "action": "agent_doctor",
        "mode": "read_only",
        "checks": checks,
        "context": context,
    }


def dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

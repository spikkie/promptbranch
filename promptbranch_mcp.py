"""Read-only MCP/Ollama planning and stdio server scaffold for Promptbranch.

The default MCP surface is deliberately read-only. Controlled process tools can
be listed for planning, but write/source/artifact tools remain blocked from the
stdio server until a future deterministic executor layer explicitly enables and
validates transactional mutation paths.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from promptbranch_artifacts import ArtifactRegistry, iter_repo_files, read_version, verify_zip_artifact
from promptbranch_shell_model import ToolRisk, required_prechecks_for_action, risk_for_action
from promptbranch_state import ConversationStateStore, resolve_profile_dir

MCP_SCHEMA_VERSION = 1
MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_SERVER_VERSION = "0.0.159"
DEFAULT_AGENT_MAX_FILES = 80
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 8.0
DEFAULT_OLLAMA_TOOL_MODEL = "llama3-groq-tool-use:8b"

MODEL_TOOL_ALIAS_TO_MCP: dict[str, str] = {
    "read_file": "filesystem.read",
    "git_status": "git.status",
    "git_diff_summary": "git.diff.summary",
    "list_files": "filesystem.list",
    "state_read": "promptbranch.state.read",
    "artifact_verify": "artifact.verify",
}

MODEL_FACING_TOOL_SCHEMAS: tuple[dict[str, Any], ...] = (
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a repo-relative file. Use this to read VERSION or README.md.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repo-relative path, for example VERSION"},
                    "max_bytes": {"type": "integer", "description": "Maximum number of bytes to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Read git branch, dirty status, and diff stat for the repository.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff_summary",
            "description": "Read a concise git diff summary for the repository.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
)


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

CONTROLLED_PROCESS_MCP_TOOLS: tuple[McpToolSpec, ...] = (
    McpToolSpec(
        name="test.smoke",
        description="Run bounded Promptbranch local smoke checks through the deterministic process executor.",
        risk=ToolRisk.EXTERNAL_PROCESS,
        read_only=False,
        requires_confirmation=False,
        prechecks=required_prechecks_for_action("test_smoke"),
        command_hint=("pb", "test", "smoke", "--json"),
    ),
)

# Deliberately not exposed by the controlled-process manifest. These names stay
# documented as blocked write intents until transactional mutation verification
# exists.
BLOCKED_WRITE_MCP_TOOL_NAMES: tuple[str, ...] = (
    "artifact.release.create",
    "promptbranch.src.sync",
)

CONTROLLED_PROCESS_TOOL_ALIASES: dict[str, str] = {
    "test.smoke": "test.smoke",
    "test.smoke.run": "test.smoke",
}

def _controlled_process_tool_names() -> set[str]:
    return set(CONTROLLED_PROCESS_TOOL_ALIASES) | {"test.smoke"}

def _normalize_mcp_tool_name(name: str) -> str:
    return CONTROLLED_PROCESS_TOOL_ALIASES.get(str(name or "").strip(), str(name or "").strip())


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


def _coerce_controlled_process_flag(
    include_controlled_processes: bool = False,
    include_controlled_writes: bool | None = None,
) -> bool:
    """Normalize the v0.0.159 controlled-process flag.

    ``include_controlled_writes`` is kept as a deprecated compatibility alias
    for older callers, but it now exposes only controlled process tools. It does
    not expose source/artifact write tools.
    """

    return bool(include_controlled_processes or include_controlled_writes)


def mcp_tool_manifest(
    *,
    include_controlled_processes: bool = False,
    include_controlled_writes: bool | None = None,
) -> dict[str, Any]:
    include_processes = _coerce_controlled_process_flag(include_controlled_processes, include_controlled_writes)
    tools = list(READ_ONLY_MCP_TOOLS)
    if include_processes:
        tools.extend(CONTROLLED_PROCESS_MCP_TOOLS)
    return {
        "ok": True,
        "schema_version": MCP_SCHEMA_VERSION,
        "action": "mcp_manifest",
        "mode": "read_only" if not include_processes else "read_only_plus_controlled_process",
        "tool_count": len(tools),
        "tools": [tool.to_dict() for tool in tools],
        "blocked_write_tools": list(BLOCKED_WRITE_MCP_TOOL_NAMES),
        "policy": {
            "local_llm_may_execute": "read_only_tools_only",
            "controlled_processes_require": "deterministic_executor_prechecks",
            "writes": "not_exposed_or_executable_from_mcp_serve",
            "destructive_tools": "not_exposed_in_manifest",
            "state_updates": "after_verified_outcomes_only",
        },
    }


def resolve_mcp_executable(command: str | None = None, *, resolve_command: bool = True) -> dict[str, Any]:
    """Resolve the executable used by GUI-launched MCP hosts.

    GUI applications often do not inherit the interactive shell PATH, so a raw
    alias like ``pb`` or ``promptbranch`` is weaker than an absolute executable
    path. Resolution is best-effort: when the command cannot be resolved, the
    original value is preserved and the result is marked unresolved.
    """

    requested = (command or "promptbranch").strip() or "promptbranch"
    expanded = os.path.expanduser(requested)
    path = Path(expanded)

    if not resolve_command:
        return {
            "requested": requested,
            "command": requested,
            "resolved": False,
            "is_absolute": Path(requested).is_absolute(),
            "source": "raw",
            "warning": "command resolution disabled; GUI MCP hosts may not find shell aliases",
        }

    if path.is_absolute():
        exists = path.exists()
        return {
            "requested": requested,
            "command": str(path),
            "resolved": exists,
            "is_absolute": True,
            "source": "absolute_path",
            "warning": None if exists else "absolute command path does not currently exist",
        }

    found = shutil.which(requested)
    if found:
        resolved = str(Path(found).resolve())
        return {
            "requested": requested,
            "command": resolved,
            "resolved": True,
            "is_absolute": True,
            "source": "PATH",
            "warning": None,
        }

    return {
        "requested": requested,
        "command": requested,
        "resolved": False,
        "is_absolute": False,
        "source": "unresolved",
        "warning": "command was not found on PATH; pass --command /absolute/path/to/promptbranch",
    }


def mcp_host_config(
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    server_name: str = "promptbranch",
    command: str | None = None,
    resolve_command: bool = True,
    include_controlled_processes: bool = False,
    include_controlled_writes: bool | None = None,
    host: str = "generic",
) -> dict[str, Any]:
    """Return an MCP host configuration snippet for this repo."""

    root = Path(repo_path).expanduser().resolve()
    resolved_profile = Path(profile_dir).expanduser().resolve() if profile_dir else None
    include_processes = _coerce_controlled_process_flag(include_controlled_processes, include_controlled_writes)
    command_resolution = resolve_mcp_executable(command, resolve_command=resolve_command)
    args: list[str] = []
    if resolved_profile is not None:
        args.extend(["--profile-dir", str(resolved_profile)])
    args.extend(["mcp", "serve", "--path", str(root)])
    if include_processes:
        args.append("--include-controlled-processes")

    server = {"command": str(command_resolution["command"]), "args": args}
    config = {"mcpServers": {server_name: server}}
    install_notes = [
        "Add config.mcpServers.promptbranch to your MCP host configuration.",
        "Use an executable command path; shell aliases usually do not work in GUI-launched MCP hosts.",
        "The server is read-only by default; the bounded test.smoke process tool is executable only when controlled process tools are explicitly requested; write/source/artifact tools remain blocked.",
    ]
    warning = command_resolution.get("warning")
    if warning:
        install_notes.insert(1, str(warning))
    return {
        "ok": True,
        "schema_version": MCP_SCHEMA_VERSION,
        "action": "mcp_config",
        "host": host,
        "server_name": server_name,
        "repo_path": str(root),
        "profile_dir": str(resolved_profile) if resolved_profile is not None else None,
        "mode": "read_only" if not include_processes else "read_only_plus_controlled_process",
        "command_resolution": command_resolution,
        "config": config,
        "install_notes": install_notes,
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



def _parse_last_json_object(text: str) -> dict[str, Any] | None:
    stripped = str(text or "").strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        pass
    # CLI wrappers may add banner/log lines before JSON. Scan from the end for a JSON object.
    lines = [line for line in stripped.splitlines() if line.strip()]
    for index in range(len(lines)):
        candidate = "\n".join(lines[index:]).strip()
        if not candidate.startswith("{"):
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    return None


def _normalize_only_selectors(value: Any) -> list[str]:
    allowed = {"mcp_smoke", "mcp_host_smoke"}
    if value is None:
        return ["mcp_smoke", "mcp_host_smoke"]
    if isinstance(value, str):
        raw = [item.strip() for item in value.replace(",", " ").split() if item.strip()]
    elif isinstance(value, list):
        raw = []
        for item in value:
            raw.extend(str(item).replace(",", " ").split())
        raw = [item.strip() for item in raw if item.strip()]
    else:
        return ["mcp_smoke", "mcp_host_smoke"]
    normalized = []
    for item in raw:
        if item in allowed and item not in normalized:
            normalized.append(item)
    return normalized or ["mcp_smoke", "mcp_host_smoke"]


def _run_test_smoke_tool(
    args: dict[str, Any] | None,
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run a bounded, non-arbitrary Promptbranch smoke subset.

    This deliberately does not accept shell text. The command is fixed to
    Promptbranch's local MCP smoke selectors so the first controlled process
    tool does not mutate ChatGPT projects or sources.
    """

    arguments = args or {}
    root = Path(repo_path).expanduser().resolve()
    timeout_seconds = float(arguments.get("timeout_seconds") or 60.0)
    timeout_seconds = max(5.0, min(timeout_seconds, 300.0))
    only = _normalize_only_selectors(arguments.get("only"))
    command_resolution = resolve_mcp_executable(str(arguments.get("command") or "promptbranch"))
    executable = str(command_resolution.get("command") or "promptbranch")
    argv = [executable]
    if profile_dir:
        argv.extend(["--profile-dir", str(Path(profile_dir).expanduser().resolve())])
    argv.extend(["test", "smoke", "--json"])
    for selector in only:
        argv.extend(["--only", selector])

    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "tool": "test.smoke",
            "status": "timeout",
            "risk": ToolRisk.EXTERNAL_PROCESS.value,
            "repo_path": str(root),
            "argv": argv,
            "timeout_seconds": timeout_seconds,
            "duration_seconds": round(time.monotonic() - started, 3),
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "parsed_json": None,
            "safety": {
                "arbitrary_shell_allowed": False,
                "fixed_command": True,
                "selectors": only,
                "source_or_artifact_mutation_allowed": False,
            },
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "tool": "test.smoke",
            "status": "command_not_found",
            "risk": ToolRisk.EXTERNAL_PROCESS.value,
            "repo_path": str(root),
            "argv": argv,
            "timeout_seconds": timeout_seconds,
            "duration_seconds": round(time.monotonic() - started, 3),
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "parsed_json": None,
            "command_resolution": command_resolution,
            "safety": {
                "arbitrary_shell_allowed": False,
                "fixed_command": True,
                "selectors": only,
                "source_or_artifact_mutation_allowed": False,
            },
        }

    duration = round(time.monotonic() - started, 3)
    parsed = _parse_last_json_object(completed.stdout)
    return {
        "ok": completed.returncode == 0,
        "tool": "test.smoke",
        "status": "verified" if completed.returncode == 0 else "failed",
        "risk": ToolRisk.EXTERNAL_PROCESS.value,
        "repo_path": str(root),
        "argv": argv,
        "timeout_seconds": timeout_seconds,
        "duration_seconds": duration,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "parsed_json": parsed,
        "command_resolution": command_resolution,
        "safety": {
            "arbitrary_shell_allowed": False,
            "fixed_command": True,
            "selectors": only,
            "source_or_artifact_mutation_allowed": False,
        },
    }


def call_controlled_process_mcp_tool(
    name: str,
    args: dict[str, Any] | None,
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
) -> dict[str, Any]:
    normalized = _normalize_mcp_tool_name(name)
    if normalized == "test.smoke":
        return _run_test_smoke_tool(args or {}, repo_path=repo_path, profile_dir=profile_dir)
    return {"ok": False, "tool": name, "error": "unsupported_controlled_process_tool", "normalized_tool": normalized}

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
    manifest = mcp_tool_manifest(include_controlled_processes=False)
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
            "reason": "v0.0.159 keeps tool planning deterministic; Ollama is optional and may be used only for summaries/diagnostics.",
        },
    }
    return payload

def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _mcp_content(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, indent=2, ensure_ascii=False),
            }
        ],
        "structuredContent": payload,
        "isError": is_error,
    }


def _tool_input_schema(tool_name: str) -> dict[str, Any]:
    if tool_name == "filesystem.list":
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Repo-relative directory to list. Defaults to repo root."},
                "max_files": {"type": "integer", "minimum": 1, "maximum": 500, "description": "Maximum files to return."},
            },
            "additionalProperties": False,
        }
    if tool_name == "filesystem.read":
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Repo-relative file path to read."},
                "max_bytes": {"type": "integer", "minimum": 1, "maximum": 100000, "description": "Maximum UTF-8 bytes to return."},
            },
            "required": ["path"],
            "additionalProperties": False,
        }
    if _normalize_mcp_tool_name(tool_name) == "test.smoke":
        return {
            "type": "object",
            "properties": {
                "timeout_seconds": {"type": "number", "minimum": 5, "maximum": 300, "description": "Hard timeout for the fixed smoke command."},
                "only": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ],
                    "description": "Optional local smoke selectors. Allowed: mcp_smoke, mcp_host_smoke.",
                },
            },
            "additionalProperties": False,
        }
    if tool_name == "artifact.verify":
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Artifact ZIP path. Defaults to current registry artifact."},
            },
            "additionalProperties": False,
        }
    return {"type": "object", "properties": {}, "additionalProperties": False}


def mcp_server_tools(*, include_controlled_processes: bool = False, include_controlled_writes: bool | None = None) -> list[dict[str, Any]]:
    manifest = mcp_tool_manifest(include_controlled_processes=include_controlled_processes, include_controlled_writes=include_controlled_writes)
    tools: list[dict[str, Any]] = []
    for tool in manifest.get("tools", []):
        if not isinstance(tool, dict):
            continue
        tools.append(
            {
                "name": str(tool.get("name") or ""),
                "description": str(tool.get("description") or ""),
                "inputSchema": _tool_input_schema(str(tool.get("name") or "")),
                "annotations": {
                    "readOnlyHint": bool(tool.get("read_only")),
                    "destructiveHint": False,
                    "idempotentHint": bool(tool.get("read_only")),
                    "openWorldHint": False,
                },
            }
        )
    return tools


def _current_state_snapshot(profile_dir: Path) -> dict[str, Any]:
    return ConversationStateStore(str(profile_dir)).snapshot(None)


def _safe_repo_relative_path(root: Path, value: str | None, *, default: str = ".") -> tuple[Path, str | None]:
    rel = (value or default).strip() or default
    if Path(rel).is_absolute():
        candidate = Path(rel).expanduser().resolve()
    else:
        candidate = (root / rel).resolve()
    if not _path_is_relative_to(candidate, root):
        return candidate, "path_outside_repo"
    return candidate, None


def _read_bounded_text(path: Path, *, max_bytes: int) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "error": "file_not_found", "path": str(path)}
    try:
        with path.open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except OSError as exc:
        return {"ok": False, "error": str(exc), "path": str(path)}
    truncated = len(data) > max_bytes
    data = data[:max_bytes]
    try:
        text = data.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
        encoding = "utf-8-replacement"
    return {
        "ok": True,
        "path": str(path),
        "encoding": encoding,
        "truncated": truncated,
        "bytes_returned": len(data),
        "text": text,
    }

def _deterministic_log_summary(text: str, *, max_marker_lines: int = 12) -> dict[str, Any]:
    """Return a local read-only summary that does not depend on a model.

    This is deliberately heuristic. It gives the operator a useful result when
    Ollama is unavailable or slow, while preserving the safety rule that models
    cannot plan, execute, or mutate state.
    """

    lines = text.splitlines()
    lowered = text.lower()
    headings = [line.strip() for line in lines if line.strip().startswith("=====")][:20]
    marker_terms = (
        '"ok": false',
        '"status": "risk_rejected"',
        '"status": "path_outside_repo"',
        '"status": "summary_unavailable"',
        '"status": "error"',
        'failed',
        'failure',
        'timed out',
        'timeout',
        'traceback',
        'exception',
        'error',
    )
    marker_lines: list[str] = []
    for line in lines:
        compact = line.strip()
        if not compact:
            continue
        lower = compact.lower()
        if any(term in lower for term in marker_terms):
            marker_lines.append(compact[:500])
            if len(marker_lines) >= max_marker_lines:
                break

    counts = {
        "ok_true": text.count('"ok": true'),
        "ok_false": text.count('"ok": false'),
        "verified": text.count('"status": "verified"'),
        "risk_rejected": text.count('"status": "risk_rejected"'),
        "path_outside_repo": text.count('"status": "path_outside_repo"'),
        "summary_unavailable": text.count('"status": "summary_unavailable"'),
        "timed_out": lowered.count("timed out") + lowered.count("timeout"),
        "traceback": lowered.count("traceback"),
    }
    hard_failure = bool(counts["traceback"] or counts["ok_false"] or counts["timed_out"] or "failed" in lowered or "exception" in lowered)
    if counts["risk_rejected"] and not counts["traceback"]:
        assessment = "contains expected policy rejections; inspect marker_lines for unexpected failures"
    elif hard_failure:
        assessment = "contains failure or timeout markers"
    else:
        assessment = "no obvious failure markers detected in bounded excerpt"

    return {
        "ok": True,
        "status": "generated",
        "method": "deterministic_heuristic_v1",
        "line_count": len(lines),
        "counts": counts,
        "headings": headings,
        "marker_lines": marker_lines,
        "assessment": assessment,
    }


def call_read_only_mcp_tool(
    name: str,
    arguments: Optional[dict[str, Any]] = None,
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
) -> dict[str, Any]:
    args = arguments or {}
    root = Path(repo_path).expanduser().resolve()
    resolved_profile = resolve_profile_dir(str(profile_dir) if profile_dir else None)

    if name == "promptbranch.state.read":
        return {"ok": True, "tool": name, "state": _current_state_snapshot(resolved_profile)}

    if name == "promptbranch.workspace.current":
        state = _current_state_snapshot(resolved_profile)
        return {
            "ok": True,
            "tool": name,
            "workspace": state.get("workspace") or {},
            "project_home_url": state.get("resolved_project_home_url") or state.get("current_project_home_url"),
            "project_name": state.get("project_name"),
        }

    if name == "promptbranch.task.current":
        state = _current_state_snapshot(resolved_profile)
        return {
            "ok": True,
            "tool": name,
            "task": state.get("task") or {},
            "conversation_url": state.get("conversation_url") or state.get("current_conversation_url"),
            "conversation_id": state.get("conversation_id"),
        }

    if name == "filesystem.list":
        max_files = int(args.get("max_files") or DEFAULT_AGENT_MAX_FILES)
        max_files = max(1, min(max_files, 500))
        target, error = _safe_repo_relative_path(root, str(args.get("path") or "."), default=".")
        if error:
            return {"ok": False, "tool": name, "error": error, "path": str(target), "repo_path": str(root)}
        if target == root:
            file_count, file_sample, file_errors = _safe_file_sample(root, max_files=max_files)
            return {"ok": not file_errors, "tool": name, "repo_path": str(root), "path": str(target), "file_count": file_count, "files": file_sample, "truncated": file_count > len(file_sample), "errors": file_errors}
        if not target.exists():
            return {"ok": False, "tool": name, "error": "path_not_found", "path": str(target), "repo_path": str(root)}
        if not target.is_dir():
            return {"ok": False, "tool": name, "error": "path_not_directory", "path": str(target), "repo_path": str(root)}
        files = sorted(path.relative_to(root).as_posix() for path in target.rglob("*") if path.is_file())
        return {"ok": True, "tool": name, "repo_path": str(root), "path": str(target), "file_count": len(files), "files": files[:max_files], "truncated": len(files) > max_files, "errors": []}

    if name == "filesystem.read":
        max_bytes = int(args.get("max_bytes") or 20000)
        max_bytes = max(1, min(max_bytes, 100000))
        target, error = _safe_repo_relative_path(root, str(args.get("path") or ""), default="")
        if error:
            return {"ok": False, "tool": name, "error": error, "path": str(target), "repo_path": str(root)}
        payload = _read_bounded_text(target, max_bytes=max_bytes)
        payload.update({"tool": name, "repo_path": str(root), "relative_path": target.relative_to(root).as_posix() if _path_is_relative_to(target, root) else None})
        return payload

    if name == "git.status":
        return {"ok": True, "tool": name, "repo_path": str(root), "git": _git_snapshot(root)}

    if name == "git.diff.summary":
        diff_stat = _run_read_only_command(["git", "diff", "--stat"], cwd=root)
        return {"ok": bool(diff_stat.get("ok")), "tool": name, "repo_path": str(root), "diff_stat": diff_stat.get("stdout") or "", "command": diff_stat}

    if name == "artifact.registry.current":
        registry = ArtifactRegistry(resolved_profile)
        return {"ok": True, "tool": name, "registry_path": str(registry.path), "artifact_dir": str(registry.artifact_dir), "current": registry.current()}

    if name == "artifact.verify":
        path_arg = args.get("path")
        if path_arg:
            artifact_path = Path(str(path_arg)).expanduser()
            if not artifact_path.is_absolute():
                artifact_path = (root / artifact_path).resolve()
        else:
            current = ArtifactRegistry(resolved_profile).current()
            artifact_path = Path(str(current.get("path"))) if isinstance(current, dict) and current.get("path") else None
        if artifact_path is None:
            return {"ok": False, "tool": name, "error": "no_current_artifact"}
        payload = verify_zip_artifact(artifact_path)
        payload["tool"] = name
        return payload

    return {"ok": False, "tool": name, "error": "unsupported_or_write_tool", "supported_read_only_tools": [tool.name for tool in READ_ONLY_MCP_TOOLS]}


def _jsonrpc_result(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _jsonrpc_error(message_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}
    if data is not None:
        payload["error"]["data"] = data
    return payload


def handle_mcp_jsonrpc_message(
    message: dict[str, Any],
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    include_controlled_processes: bool = False,
    include_controlled_writes: bool | None = None,
) -> dict[str, Any] | None:
    include_processes = _coerce_controlled_process_flag(include_controlled_processes, include_controlled_writes)
    message_id = message.get("id")
    method = message.get("method")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}

    if not method:
        return _jsonrpc_error(message_id, -32600, "Invalid Request", {"reason": "missing method"})

    if message_id is None and method in {"notifications/initialized", "notifications/cancelled", "$/cancelRequest"}:
        return None

    if method == "initialize":
        return _jsonrpc_result(
            message_id,
            {
                "protocolVersion": str(params.get("protocolVersion") or MCP_PROTOCOL_VERSION),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "promptbranch", "version": MCP_SERVER_VERSION},
                "instructions": "Promptbranch MCP exposes read-only repo/git/state/artifact tools by default. The bounded test.smoke process tool is available only when controlled process tools are explicitly requested; write/source/artifact tools remain blocked.",
            },
        )

    if method in {"ping", "$/ping"}:
        return _jsonrpc_result(message_id, {})

    if method == "tools/list":
        return _jsonrpc_result(message_id, {"tools": mcp_server_tools(include_controlled_processes=include_processes)})

    if method == "tools/call":
        name = str(params.get("name") or "")
        normalized_name = _normalize_mcp_tool_name(name)
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        manifest_tools = mcp_tool_manifest(include_controlled_processes=include_processes).get("tools", [])
        tool_meta = next((tool for tool in manifest_tools if isinstance(tool, dict) and tool.get("name") in {name, normalized_name}), None)
        if tool_meta is None:
            return _jsonrpc_result(message_id, _mcp_content({"ok": False, "error": "unknown_tool", "tool": name}, is_error=True))
        if not bool(tool_meta.get("read_only")):
            normalized_name = _normalize_mcp_tool_name(name)
            if include_processes and normalized_name in _controlled_process_tool_names():
                payload = call_controlled_process_mcp_tool(normalized_name, arguments, repo_path=repo_path, profile_dir=profile_dir)
                return _jsonrpc_result(message_id, _mcp_content(payload, is_error=not bool(payload.get("ok"))))
            return _jsonrpc_result(
                message_id,
                _mcp_content(
                    {
                        "ok": False,
                        "error": "write_tool_not_executable_via_mcp_serve",
                        "tool": name,
                        "required_policy": "transactional_write_executor_not_available",
                    },
                    is_error=True,
                ),
            )
        payload = call_read_only_mcp_tool(name, arguments, repo_path=repo_path, profile_dir=profile_dir)
        return _jsonrpc_result(message_id, _mcp_content(payload, is_error=not bool(payload.get("ok"))))

    if method == "resources/list":
        return _jsonrpc_result(message_id, {"resources": []})

    if method == "prompts/list":
        return _jsonrpc_result(message_id, {"prompts": []})

    return _jsonrpc_error(message_id, -32601, "Method not found", {"method": method})


def serve_mcp_stdio(
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    include_controlled_processes: bool = False,
    include_controlled_writes: bool | None = None,
    input_stream: Any = None,
    output_stream: Any = None,
) -> int:
    """Serve a minimal MCP JSON-RPC stdio loop."""

    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    for raw in input_stream:
        line = str(raw).strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            response = _jsonrpc_error(None, -32700, "Parse error", {"error": str(exc)})
        else:
            if not isinstance(message, dict):
                response = _jsonrpc_error(None, -32600, "Invalid Request", {"reason": "message must be an object"})
            else:
                response = handle_mcp_jsonrpc_message(
                    message,
                    repo_path=repo_path,
                    profile_dir=profile_dir,
                    include_controlled_processes=include_controlled_processes,
                    include_controlled_writes=include_controlled_writes,
                )
        if response is None:
            continue
        output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
        output_stream.flush()
    return 0


def _mcp_host_smoke_messages(read_path: str) -> list[dict[str, Any]]:
    return [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": MCP_PROTOCOL_VERSION}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "promptbranch.state.read", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "filesystem.read", "arguments": {"path": read_path, "max_bytes": 2000}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "git.status", "arguments": {}}},
    ]


def _read_json_lines(text: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            payloads.append({"jsonrpc_parse_error": True, "line": line})
            continue
        if isinstance(parsed, dict):
            payloads.append(parsed)
        else:
            payloads.append({"jsonrpc_parse_error": True, "value": parsed})
    return payloads


def _git_toplevel(path: str | Path) -> Path | None:
    """Return the git worktree root for diagnostics/path fallback, if available."""

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(Path(path).expanduser().resolve()),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    if not value:
        return None
    root = Path(value).expanduser().resolve()
    return root if root.is_dir() else None


def _select_host_smoke_read_path(root: Path) -> str | None:
    """Select a file target for filesystem.read; never return a directory."""

    for candidate in ("VERSION", "README.md"):
        if (root / candidate).is_file():
            return candidate
    return None


def _host_smoke_missing_read_target_payload(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    git_root = _git_toplevel(root)
    suggested_path = None
    if git_root is not None and git_root != root and any((git_root / item).is_file() for item in ("VERSION", "README.md")):
        suggested_path = str(git_root)
    return {
        "ok": False,
        "action": "mcp_host_smoke",
        "status": "read_target_missing",
        "repo_path": str(root),
        "config": config,
        "read_path": None,
        "read_candidates": ["VERSION", "README.md"],
        "git_root": str(git_root) if git_root is not None else None,
        "suggested_path": suggested_path,
        "diagnostic": "mcp_host_smoke requires a readable file target and will not call filesystem.read on a directory; run from the repo root or pass --path pointing at a directory containing VERSION or README.md.",
        "checks": {
            "read_target_found": False,
            "filesystem_read_ok": False,
            "write_tools_not_executed": True,
        },
    }


def mcp_host_smoke(
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    server_name: str = "promptbranch",
    command: str | None = None,
    resolve_command: bool = True,
    include_controlled_processes: bool = False,
    include_controlled_writes: bool | None = None,
    host: str = "generic",
    timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    """Launch the generated MCP host config and call read-only tools."""

    root = Path(repo_path).expanduser().resolve()
    resolved_profile = Path(profile_dir).expanduser().resolve() if profile_dir else None
    config = mcp_host_config(
        repo_path=root,
        profile_dir=resolved_profile,
        server_name=server_name,
        command=command,
        resolve_command=resolve_command,
        include_controlled_processes=include_controlled_processes,
        include_controlled_writes=include_controlled_writes,
        host=host,
    )
    server = config["config"]["mcpServers"][server_name]
    read_path = _select_host_smoke_read_path(root)
    if read_path is None:
        return _host_smoke_missing_read_target_payload(root, config)
    messages = _mcp_host_smoke_messages(read_path)
    request_text = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in messages)

    started = time.monotonic()
    try:
        completed = subprocess.run(
            [str(server["command"]), *[str(arg) for arg in server.get("args", [])]],
            input=request_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=max(1.0, float(timeout_seconds)),
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "action": "mcp_host_smoke",
            "status": "command_not_found",
            "config": config,
            "error": str(exc),
            "checks": {"command_launchable": False},
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "action": "mcp_host_smoke",
            "status": "timeout",
            "config": config,
            "timeout_seconds": timeout_seconds,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "checks": {"command_launchable": True, "completed_before_timeout": False},
        }
    except OSError as exc:
        return {
            "ok": False,
            "action": "mcp_host_smoke",
            "status": "os_error",
            "config": config,
            "error": str(exc),
            "checks": {"command_launchable": False},
        }

    duration = round(time.monotonic() - started, 3)
    responses = _read_json_lines(completed.stdout)
    by_id = {item.get("id"): item for item in responses if isinstance(item, dict)}

    def _tool_ok(message_id: int) -> bool:
        item = by_id.get(message_id)
        if not isinstance(item, dict):
            return False
        result = item.get("result") if isinstance(item.get("result"), dict) else {}
        return result.get("isError") is False

    tools_result = by_id.get(2, {}).get("result") if isinstance(by_id.get(2), dict) else {}
    tools = tools_result.get("tools") if isinstance(tools_result, dict) else []
    tool_names = [tool.get("name") for tool in tools if isinstance(tool, dict)]
    init_result = by_id.get(1, {}).get("result") if isinstance(by_id.get(1), dict) else {}
    checks = {
        "command_is_absolute": bool(config.get("command_resolution", {}).get("is_absolute")),
        "command_resolved": bool(config.get("command_resolution", {}).get("resolved")),
        "process_returncode_zero": completed.returncode == 0,
        "initialize_ok": isinstance(init_result, dict) and init_result.get("serverInfo", {}).get("name") == "promptbranch",
        "tools_list_ok": "filesystem.read" in tool_names and "promptbranch.state.read" in tool_names,
        "state_read_ok": _tool_ok(3),
        "filesystem_read_ok": _tool_ok(4),
        "git_status_ok": _tool_ok(5),
        "write_tools_not_executed": True,
    }
    return {
        "ok": all(checks.values()),
        "action": "mcp_host_smoke",
        "status": "verified" if all(checks.values()) else "failed",
        "duration_seconds": duration,
        "repo_path": str(root),
        "profile_dir": str(resolved_profile) if resolved_profile is not None else None,
        "read_path": read_path,
        "config": config,
        "checks": checks,
        "responses": responses,
        "stderr": completed.stderr.strip(),
        "returncode": completed.returncode,
    }


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)


def _normalized_request_text(request: str) -> str:
    return " " + " ".join(str(request or "").strip().lower().replace("_", " ").replace("-", " ").split()) + " "


def classify_agent_request_risk(request: str) -> dict[str, Any]:
    """Classify original operator request risk before accepting any model proposal.

    This is intentionally conservative. The local model may propose a benign
    read tool for a destructive prompt such as "delete VERSION". That must be
    rejected based on the original request, not on the model's reframing.
    """

    text = _normalized_request_text(request)
    destructive_terms = (
        " delete ",
        " remove ",
        " rm ",
        " erase ",
        " unlink ",
        " destroy ",
        " wipe ",
        " purge ",
        " drop ",
        " source rm ",
        " rm source ",
        " delete source ",
        " remove source ",
    )
    write_terms = (
        " overwrite ",
        " write ",
        " modify ",
        " edit ",
        " commit ",
        " push ",
        " sync ",
        " release ",
        " upload ",
        " add source ",
        " source add ",
        " pbsa ",
        " package ",
        " make zip ",
        " rename ",
    )
    controlled_process_terms = (
        " run smoke test ",
        " run smoke tests ",
        " smoke test ",
        " smoke tests ",
        " test smoke ",
        " mcp smoke ",
    )
    blocked_process_terms = (
        " pytest ",
        " run test suite ",
        " test suite ",
        " run command ",
        " shell ",
    )

    matched = [term.strip() for term in destructive_terms if term in text]
    if matched:
        return {
            "risk": ToolRisk.DESTRUCTIVE.value,
            "auto_allowed": False,
            "status": "blocked_original_request_destructive",
            "matched_terms": matched,
        }
    matched = [term.strip() for term in write_terms if term in text]
    if matched:
        return {
            "risk": ToolRisk.WRITE.value,
            "auto_allowed": False,
            "status": "blocked_original_request_write",
            "matched_terms": matched,
        }
    matched = [term.strip() for term in controlled_process_terms if term in text]
    if matched:
        return {
            "risk": ToolRisk.EXTERNAL_PROCESS.value,
            "auto_allowed": True,
            "status": "controlled_process_allowed",
            "matched_terms": matched,
            "controlled_tool": "test.smoke",
        }
    matched = [term.strip() for term in blocked_process_terms if term in text]
    if matched:
        return {
            "risk": ToolRisk.EXTERNAL_PROCESS.value,
            "auto_allowed": False,
            "status": "blocked_original_request_process",
            "matched_terms": matched,
        }
    return {"risk": ToolRisk.READ.value, "auto_allowed": True, "status": "read_only", "matched_terms": []}


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



def ollama_models(*, host: str = DEFAULT_OLLAMA_HOST, timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS) -> dict[str, Any]:
    """List local Ollama models without requiring Ollama for normal operation."""

    endpoint = host.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(endpoint, timeout=max(0.5, float(timeout_seconds))) as response:  # noqa: S310 - local operator-configured endpoint
            raw = response.read(2_000_000)
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "action": "agent_models",
            "host": host,
            "status": "unavailable",
            "error": str(exc),
            "models": [],
        }
    except OSError as exc:
        return {
            "ok": False,
            "action": "agent_models",
            "host": host,
            "status": "error",
            "error": str(exc),
            "models": [],
        }

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "action": "agent_models",
            "host": host,
            "status": "invalid_response",
            "error": str(exc),
            "models": [],
        }
    models = payload.get("models") if isinstance(payload, dict) else []
    names = [str(item.get("name")) for item in models if isinstance(item, dict) and item.get("name")]
    return {
        "ok": True,
        "action": "agent_models",
        "host": host,
        "status": "available",
        "count": len(names),
        "models": models if isinstance(models, list) else [],
        "model_names": names,
    }


def _call_ollama_generate(
    *,
    prompt: str,
    model: str,
    host: str = DEFAULT_OLLAMA_HOST,
    timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    num_predict: int = 160,
) -> dict[str, Any]:
    endpoint = host.rstrip("/") + "/api/generate"
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": max(1, min(int(num_predict), 512))},
        }
    ).encode("utf-8")
    request = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=max(0.5, float(timeout_seconds))) as response:  # noqa: S310 - local operator-configured endpoint
            raw = response.read(4_000_000)
    except urllib.error.URLError as exc:
        return {"ok": False, "status": "unavailable", "error": str(exc), "model": model, "host": host}
    except OSError as exc:
        return {"ok": False, "status": "error", "error": str(exc), "model": model, "host": host}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": "invalid_response", "error": str(exc), "model": model, "host": host}
    text = str(payload.get("response") or "") if isinstance(payload, dict) else ""
    return {"ok": bool(text.strip()), "status": "generated" if text.strip() else "empty", "model": model, "host": host, "text": text.strip(), "raw": payload}




BUILTIN_SKILL_DOCS: dict[str, str] = {
    "repo-inspection": """---
name: repo-inspection
description: Inspect repository state using read-only MCP tools.
risk: read
allowed_tools:
  - filesystem.read
  - git.status
  - git.diff.summary
prechecks:
  - repo_path_exists
  - tool_read_only
---

## Procedure

1. Read VERSION if present.
2. Run git.status.
3. If dirty, run git.diff.summary.
4. Report version, branch, short SHA, dirty state, and risk.
5. Never execute write tools.
""",
}

SKILL_SEARCH_DIR_NAMES: tuple[str, ...] = (".promptbranch/skills", "skills")


def _parse_skill_frontmatter(text: str) -> tuple[dict[str, Any], str, list[str]]:
    errors: list[str] = []
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return {}, text, ["missing_frontmatter"]
    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return {}, text, ["unterminated_frontmatter"]
    raw = parts[1]
    body = parts[2].lstrip("\n")
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(line[4:].strip())
            else:
                errors.append(f"frontmatter_key_not_list:{current_key}")
            continue
        if ":" not in line:
            errors.append(f"invalid_frontmatter_line:{line.strip()}")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        if value == "":
            data[key] = []
        else:
            if value.lower() in {"true", "false"}:
                data[key] = value.lower() == "true"
            else:
                data[key] = value
    return data, body, errors


def _skill_dirs(repo_path: str | Path = ".", profile_dir: str | Path | None = None) -> list[Path]:
    root = Path(repo_path).expanduser().resolve()
    roots = [root]
    git_root = _git_toplevel(root)
    if git_root is not None and git_root not in roots:
        roots.append(git_root)
    dirs = [(candidate_root / name).resolve() for candidate_root in roots for name in SKILL_SEARCH_DIR_NAMES]
    if profile_dir:
        dirs.append((Path(profile_dir).expanduser().resolve() / "skills").resolve())
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    dirs.append((config_home / "promptbranch" / "skills").resolve())
    return dirs


def _find_skill_path(name_or_path: str, *, repo_path: str | Path = ".", profile_dir: str | Path | None = None) -> Path | None:
    raw = str(name_or_path or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if path.exists():
        if path.is_dir():
            return path / "SKILL.md"
        return path
    root = Path(repo_path).expanduser().resolve()
    candidate_roots = [root]
    git_root = _git_toplevel(root)
    if git_root is not None and git_root not in candidate_roots:
        candidate_roots.append(git_root)
    for candidate_root in candidate_roots:
        candidate = (candidate_root / raw).resolve()
        if candidate.exists():
            if candidate.is_dir():
                return candidate / "SKILL.md"
            return candidate
    for directory in _skill_dirs(root, profile_dir):
        candidate = directory / raw / "SKILL.md"
        if candidate.exists():
            return candidate
    return None


def _read_skill_document(name_or_path: str, *, repo_path: str | Path = ".", profile_dir: str | Path | None = None) -> tuple[str | None, str | None, str | None]:
    raw = str(name_or_path or "").strip()
    path = _find_skill_path(raw, repo_path=repo_path, profile_dir=profile_dir)
    if path and path.exists():
        try:
            return path.read_text(encoding="utf-8"), str(path), None
        except OSError as exc:
            return None, str(path), str(exc)
    if raw in BUILTIN_SKILL_DOCS:
        return BUILTIN_SKILL_DOCS[raw], f"builtin:{raw}", None
    return None, None, "skill_not_found"


def _all_read_only_tool_names() -> set[str]:
    return {spec.name for spec in READ_ONLY_MCP_TOOLS}


def validate_skill_document(text: str, *, source: str = "inline") -> dict[str, Any]:
    frontmatter, body, parse_errors = _parse_skill_frontmatter(text)
    errors: list[str] = list(parse_errors)
    name = frontmatter.get("name")
    risk = str(frontmatter.get("risk") or "").strip() or "read"
    allowed_tools = frontmatter.get("allowed_tools")
    prechecks = frontmatter.get("prechecks")
    if not isinstance(name, str) or not name.strip():
        errors.append("missing_name")
    if risk not in {ToolRisk.READ.value, ToolRisk.EXTERNAL_PROCESS.value, ToolRisk.WRITE.value, ToolRisk.DESTRUCTIVE.value}:
        errors.append(f"invalid_risk:{risk}")
    if not isinstance(allowed_tools, list) or not allowed_tools:
        errors.append("missing_allowed_tools")
        allowed_tool_values: list[str] = []
    else:
        allowed_tool_values = [str(item).strip() for item in allowed_tools if str(item).strip()]
    read_only = _all_read_only_tool_names()
    unknown_tools = [tool for tool in allowed_tool_values if tool not in read_only and tool not in {spec.name for spec in CONTROLLED_PROCESS_MCP_TOOLS}]
    process_tools = [tool for tool in allowed_tool_values if tool in {spec.name for spec in CONTROLLED_PROCESS_MCP_TOOLS}]
    if unknown_tools:
        errors.append("unknown_tools")
    if risk == ToolRisk.READ.value and process_tools:
        errors.append("process_tools_not_allowed_for_read_skill")
    if prechecks is not None and not isinstance(prechecks, list):
        errors.append("prechecks_must_be_list")
    return {
        "ok": not errors,
        "action": "skill_validate",
        "status": "valid" if not errors else "invalid",
        "source": source,
        "skill": {
            "name": name,
            "description": frontmatter.get("description"),
            "risk": risk,
            "allowed_tools": allowed_tool_values,
            "prechecks": prechecks if isinstance(prechecks, list) else [],
            "body_length": len(body),
        },
        "errors": errors,
        "unknown_tools": unknown_tools,
        "process_tools": process_tools,
        "frontmatter": frontmatter,
    }


def skill_validate(name_or_path: str, *, repo_path: str | Path = ".", profile_dir: str | Path | None = None) -> dict[str, Any]:
    text, source, error = _read_skill_document(name_or_path, repo_path=repo_path, profile_dir=profile_dir)
    if text is None:
        return {"ok": False, "action": "skill_validate", "status": "not_found", "requested": name_or_path, "source": source, "error": error}
    payload = validate_skill_document(text, source=source or str(name_or_path))
    payload["requested"] = name_or_path
    return payload


def skill_show(name_or_path: str, *, repo_path: str | Path = ".", profile_dir: str | Path | None = None, include_content: bool = True) -> dict[str, Any]:
    text, source, error = _read_skill_document(name_or_path, repo_path=repo_path, profile_dir=profile_dir)
    if text is None:
        return {"ok": False, "action": "skill_show", "status": "not_found", "requested": name_or_path, "source": source, "error": error}
    validation = validate_skill_document(text, source=source or str(name_or_path))
    payload = {"ok": validation.get("ok"), "action": "skill_show", "status": validation.get("status"), "requested": name_or_path, "source": source, "validation": validation}
    if include_content:
        payload["content"] = text
    return payload


def skill_list(*, repo_path: str | Path = ".", profile_dir: str | Path | None = None) -> dict[str, Any]:
    skills: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name, text in BUILTIN_SKILL_DOCS.items():
        validation = validate_skill_document(text, source=f"builtin:{name}")
        skill = validation.get("skill") if isinstance(validation.get("skill"), dict) else {}
        skills.append({"name": name, "source": f"builtin:{name}", "builtin": True, "ok": bool(validation.get("ok")), "description": skill.get("description"), "risk": skill.get("risk"), "allowed_tools": skill.get("allowed_tools")})
        seen.add(name)
    for directory in _skill_dirs(repo_path, profile_dir):
        if not directory.exists() or not directory.is_dir():
            continue
        for skill_file in sorted(directory.glob("*/SKILL.md")):
            name = skill_file.parent.name
            if name in seen:
                continue
            try:
                text = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
            validation = validate_skill_document(text, source=str(skill_file))
            skill = validation.get("skill") if isinstance(validation.get("skill"), dict) else {}
            skills.append({"name": name, "source": str(skill_file), "builtin": False, "ok": bool(validation.get("ok")), "description": skill.get("description"), "risk": skill.get("risk"), "allowed_tools": skill.get("allowed_tools")})
            seen.add(name)
    return {"ok": True, "action": "skill_list", "count": len(skills), "skills": skills}


def _plan_tool_calls_for_skill(skill_name: str, request: str, *, repo_path: str | Path = ".") -> tuple[list[dict[str, Any]], list[str]]:
    normalized_name = str(skill_name or "").strip()
    notes: list[str] = []
    if normalized_name != "repo-inspection":
        notes.append("unknown_skill_plan_defaulted_to_read_only_request_classifier")
        return [dict(item) for item in _read_only_tool_specs_for_request(request)], notes
    root = Path(repo_path).expanduser().resolve()
    calls: list[dict[str, Any]] = []
    if (root / "VERSION").is_file():
        calls.append({"name": "filesystem.read", "arguments": {"path": "VERSION", "max_bytes": 2000}})
    else:
        notes.append("VERSION file not present; skipped filesystem.read VERSION")
    calls.append({"name": "git.status", "arguments": {}})
    # git.diff.summary is included; callers can inspect empty diff output. This keeps the skill deterministic
    # and avoids hidden branching on a pre-read git result.
    calls.append({"name": "git.diff.summary", "arguments": {}})
    return calls, notes


def agent_summarize_log(
    log_path: str | Path,
    *,
    repo_path: str | Path = ".",
    model: str = "llama3.2:3b",
    ollama_host: str = DEFAULT_OLLAMA_HOST,
    ollama_timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    max_bytes: int = 12000,
) -> dict[str, Any]:
    """Summarize one repo-bounded log file with Ollama.

    This is intentionally read-only. The log is read deterministically first;
    Ollama receives a bounded excerpt and may summarize it, but model failure
    does not hide the raw read metadata. The function never executes tools,
    mutates state, or reads outside ``repo_path``.
    """

    root = Path(repo_path).expanduser().resolve()
    raw_path = str(log_path or "").strip()
    if not raw_path:
        return {
            "ok": False,
            "action": "agent_summarize_log",
            "status": "invalid_log_path",
            "mode": "ollama_summary_read_only",
            "repo_path": str(root),
            "log_path": raw_path,
            "error": "log path is required",
            "ollama": {"used_for_planning": False, "used_for_summary": False},
            "safety": {"repo_bound_read": True, "write_tools_blocked": True, "model_has_execution_authority": False},
        }
    target, path_error = _safe_repo_relative_path(root, raw_path, default="")
    if path_error:
        return {
            "ok": False,
            "action": "agent_summarize_log",
            "status": path_error,
            "mode": "ollama_summary_read_only",
            "repo_path": str(root),
            "log_path": raw_path,
            "resolved_path": str(target),
            "error": "log path must be repo-relative and inside repo_path",
            "ollama": {"used_for_planning": False, "used_for_summary": False},
            "safety": {"repo_bound_read": True, "write_tools_blocked": True, "model_has_execution_authority": False},
        }

    max_bytes = max(1, min(int(max_bytes), 100000))
    read_payload = _read_bounded_text(target, max_bytes=max_bytes)
    read_payload.update({
        "repo_path": str(root),
        "relative_path": target.relative_to(root).as_posix() if _path_is_relative_to(target, root) else None,
        "max_bytes": max_bytes,
    })
    if not read_payload.get("ok"):
        return {
            "ok": False,
            "action": "agent_summarize_log",
            "status": str(read_payload.get("error") or "log_read_failed"),
            "mode": "ollama_summary_read_only",
            "repo_path": str(root),
            "log_path": raw_path,
            "resolved_path": str(target),
            "read": read_payload,
            "ollama": {"used_for_planning": False, "used_for_summary": False},
            "safety": {"repo_bound_read": True, "write_tools_blocked": True, "model_has_execution_authority": False},
        }

    text = str(read_payload.get("text") or "")
    prompt = (
        "Summarize this Promptbranch/log output for a developer. Return: "
        "1) pass/fail status, 2) important failures, 3) likely cause, 4) next safe command. "
        "Do not invent results and do not propose write/destructive actions.\n\n"
        + text[:max_bytes]
    )
    deterministic_summary = _deterministic_log_summary(text[:max_bytes])
    summary = _call_ollama_generate(
        prompt=prompt,
        model=model,
        host=ollama_host,
        timeout_seconds=ollama_timeout_seconds,
        num_predict=320,
    )
    return {
        "ok": True,
        "action": "agent_summarize_log",
        "status": "summarized" if summary.get("ok") else "deterministic_summary",
        "mode": "ollama_summary_read_only",
        "repo_path": str(root),
        "log_path": raw_path,
        "resolved_path": str(target),
        "read": {k: v for k, v in read_payload.items() if k != "text"},
        "deterministic_summary": deterministic_summary,
        "ollama": {
            "used_for_planning": False,
            "used_for_summary": True,
            "model": model,
            "host": ollama_host,
            "summary": summary,
            "fallback_used": not bool(summary.get("ok")),
            "note": "Ollama summary failure is non-fatal; deterministic_summary and read metadata remain authoritative.",
        },
        "safety": {"repo_bound_read": True, "write_tools_blocked": True, "model_has_execution_authority": False},
    }


def agent_run(
    request: str,
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    skill: str | None = None,
    model: str | None = None,
    proposal_mode: str = "deterministic",
    ollama_host: str = DEFAULT_OLLAMA_HOST,
    ollama_timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    command: str | None = None,
    mcp_timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    """Canonical Promptbranch-native host command.

    This intentionally exercises the real MCP stdio boundary for tool execution.
    Deterministic and skill-guided planning are read-only. Ollama proposal mode may
    propose one tool only and still passes through the same request-risk gate.
    """

    request_risk = classify_agent_request_risk(request)
    if not request_risk.get("auto_allowed"):
        return {
            "ok": False,
            "action": "agent_run",
            "status": "risk_rejected",
            "mode": "promptbranch_native_host",
            "request": request,
            "request_risk": request_risk,
            "skill": skill,
            "proposal_mode": proposal_mode,
            "plan": [],
            "results": [],
            "safety": {"original_request_risk_checked": True, "mcp_transport": "stdio", "write_tools_blocked": True},
        }

    notes: list[str] = []
    validation: dict[str, Any] | None = None
    plan: list[dict[str, Any]] = []
    proposal: dict[str, Any] | None = None
    planner = "rule_based_v1"

    if skill:
        validation = skill_validate(skill, repo_path=repo_path, profile_dir=profile_dir)
        if not validation.get("ok"):
            return {
                "ok": False,
                "action": "agent_run",
                "status": "skill_invalid",
                "mode": "promptbranch_native_host",
                "request": request,
                "request_risk": request_risk,
                "skill": skill,
                "skill_validation": validation,
                "plan": [],
                "results": [],
            }
        skill_info = validation.get("skill") if isinstance(validation.get("skill"), dict) else {}
        allowed = set(skill_info.get("allowed_tools") or [])
        plan, skill_notes = _plan_tool_calls_for_skill(str(skill_info.get("name") or skill), request, repo_path=repo_path)
        notes.extend(skill_notes)
        disallowed = [item.get("name") for item in plan if item.get("name") not in allowed]
        if disallowed:
            return {
                "ok": False,
                "action": "agent_run",
                "status": "skill_plan_disallowed_tool",
                "mode": "promptbranch_native_host",
                "request": request,
                "request_risk": request_risk,
                "skill": skill,
                "skill_validation": validation,
                "disallowed_tools": disallowed,
                "plan": plan,
                "results": [],
            }
        planner = f"skill:{skill_info.get('name') or skill}"
    elif proposal_mode == "ollama" or model:
        selected_model = model or DEFAULT_OLLAMA_TOOL_MODEL
        proposal = ollama_propose_mcp_tool_call(
            request,
            model=selected_model,
            ollama_host=ollama_host,
            ollama_timeout_seconds=ollama_timeout_seconds,
            allow_schema_fallback=True,
        )
        selected = proposal.get("selected") if isinstance(proposal, dict) else None
        if not proposal.get("ok") or not isinstance(selected, dict):
            return {
                "ok": False,
                "action": "agent_run",
                "status": proposal.get("status", "model_tool_call_invalid") if isinstance(proposal, dict) else "model_tool_call_invalid",
                "mode": "promptbranch_native_host",
                "request": request,
                "request_risk": request_risk,
                "proposal_mode": "ollama",
                "ollama_proposal": proposal,
                "plan": [],
                "results": [],
            }
        plan = [{"name": str(selected.get("tool") or ""), "arguments": selected.get("arguments") if isinstance(selected.get("arguments"), dict) else {}}]
        planner = "ollama_proposal_validated"
    else:
        if request_risk.get("risk") == ToolRisk.EXTERNAL_PROCESS.value and request_risk.get("controlled_tool") == "test.smoke":
            process_args: dict[str, Any] = {"timeout_seconds": max(float(mcp_timeout_seconds), 60.0)}
            if command:
                process_args["command"] = command
            plan = [{"name": "test.smoke", "arguments": process_args}]
            planner = "controlled_process_v1"
        else:
            plan = [dict(item) for item in _read_only_tool_specs_for_request(request)]

    read_only = _all_read_only_tool_names()
    allowed_tools = set(read_only)
    if request_risk.get("risk") == ToolRisk.EXTERNAL_PROCESS.value and request_risk.get("controlled_tool") == "test.smoke":
        allowed_tools.update(_controlled_process_tool_names())
    blocked = [item.get("name") for item in plan if _normalize_mcp_tool_name(str(item.get("name") or "")) not in allowed_tools]
    if blocked:
        return {
            "ok": False,
            "action": "agent_run",
            "status": "plan_contains_non_read_only_tool",
            "mode": "promptbranch_native_host",
            "request": request,
            "request_risk": request_risk,
            "skill": skill,
            "planner": planner,
            "blocked_tools": blocked,
            "plan": plan,
            "results": [],
        }

    results: list[dict[str, Any]] = []
    for item in plan:
        result = mcp_tool_call_via_stdio(
            str(item.get("name") or ""),
            item.get("arguments") if isinstance(item.get("arguments"), dict) else {},
            repo_path=repo_path,
            profile_dir=profile_dir,
            command=command,
            timeout_seconds=mcp_timeout_seconds,
        )
        results.append(result)
    ok = all(bool(item.get("ok")) for item in results)
    return {
        "ok": ok,
        "action": "agent_run",
        "status": "verified" if ok else "tool_call_failed",
        "mode": "promptbranch_native_host",
        "planner": planner,
        "request": request,
        "request_risk": request_risk,
        "proposal_mode": "ollama" if proposal is not None else "deterministic",
        "skill": skill,
        "skill_validation": validation,
        "ollama_proposal": proposal,
        "plan": plan,
        "results": results,
        "notes": notes,
        "safety": {"original_request_risk_checked": True, "mcp_transport": "stdio", "write_tools_blocked": True, "model_has_execution_authority": False},
    }

def _read_only_tool_specs_for_request(request: str) -> tuple[dict[str, Any], ...]:
    """Map simple operator requests to read-only MCP calls deterministically."""

    text = " ".join(str(request or "").lower().split())
    calls: list[dict[str, Any]] = []

    def add(name: str, arguments: dict[str, Any] | None = None) -> None:
        item = {"name": name, "arguments": arguments or {}}
        if item not in calls:
            calls.append(item)

    if "version" in text:
        add("filesystem.read", {"path": "VERSION", "max_bytes": 2000})
    if "readme" in text:
        add("filesystem.read", {"path": "README.md", "max_bytes": 12000})
    if "git" in text and ("status" in text or "state" in text or "dirty" in text):
        add("git.status")
    if "diff" in text:
        add("git.diff.summary")
    if "state" in text or "workspace" in text or "current" in text or "task" in text:
        add("promptbranch.state.read")
    if "list" in text and ("file" in text or "repo" in text):
        add("filesystem.list", {"path": ".", "max_files": 80})

    if not calls:
        add("filesystem.list", {"path": ".", "max_files": 40})
        add("git.status")
    return tuple(calls)


def agent_tool_call(
    tool: str,
    arguments: Optional[dict[str, Any]] = None,
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Call one read-only MCP tool through the deterministic local executor."""

    normalized_tool = _normalize_mcp_tool_name(tool)
    read_only_names = {spec.name for spec in READ_ONLY_MCP_TOOLS}
    if normalized_tool in read_only_names:
        payload = call_read_only_mcp_tool(normalized_tool, arguments or {}, repo_path=repo_path, profile_dir=profile_dir)
    elif normalized_tool in _controlled_process_tool_names():
        payload = call_controlled_process_mcp_tool(normalized_tool, arguments or {}, repo_path=repo_path, profile_dir=profile_dir)
    else:
        return {
            "ok": False,
            "action": "agent_tool_call",
            "status": "blocked",
            "tool": normalized_tool,
            "requested_tool": tool,
            "error": "tool_not_read_only_or_controlled_process",
            "supported_tools": sorted(read_only_names | _controlled_process_tool_names()),
        }
    return {
        "ok": bool(payload.get("ok")),
        "action": "agent_tool_call",
        "status": "verified" if payload.get("ok") else "failed",
        "tool": normalized_tool,
        "requested_tool": tool,
        "arguments": arguments or {},
        "result": payload,
    }


def agent_ask(
    request: str,
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    model: str | None = None,
    ollama_host: str = DEFAULT_OLLAMA_HOST,
    ollama_timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    summarize: bool = False,
) -> dict[str, Any]:
    """Execute a deterministic read-only local-agent request.

    Ollama is intentionally not used for tool planning. The local LLM may be
    used only to summarize already-collected tool results, and failures are
    non-fatal because read-only tool output remains the source of truth.
    """

    tool_specs = _read_only_tool_specs_for_request(request)
    results = [
        agent_tool_call(
            str(spec.get("name") or ""),
            spec.get("arguments") if isinstance(spec.get("arguments"), dict) else {},
            repo_path=repo_path,
            profile_dir=profile_dir,
        )
        for spec in tool_specs
    ]
    ok = all(item.get("ok") for item in results)
    summary: dict[str, Any] | None = None
    if summarize or model:
        selected_model = model or "llama3.2:3b"
        summary_prompt = (
            "Summarize these read-only Promptbranch MCP tool results in at most 8 bullet points. "
            "Do not propose write actions.\n\n"
            + json.dumps({"request": request, "tool_results": results}, ensure_ascii=False)[:12000]
        )
        summary = _call_ollama_generate(
            prompt=summary_prompt,
            model=selected_model,
            host=ollama_host,
            timeout_seconds=ollama_timeout_seconds,
            num_predict=220,
        )
    return {
        "ok": ok,
        "action": "agent_ask",
        "mode": "deterministic_read_only",
        "planner": "rule_based_v1",
        "request": request,
        "risk": "read",
        "auto_allowed": True,
        "tool_calls": [dict(spec) for spec in tool_specs],
        "results": results,
        "ollama": {
            "used_for_planning": False,
            "used_for_summary": bool(summary),
            "model": model,
            "summary": summary,
            "note": "Ollama is optional; invalid/empty local model output does not block deterministic read-only tool results.",
        },
    }



def _call_ollama_generate_json(
    *,
    prompt: str,
    model: str,
    host: str = DEFAULT_OLLAMA_HOST,
    timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    num_predict: int = 120,
) -> dict[str, Any]:
    """Ask Ollama for a JSON-mode response and parse the response string.

    This is intentionally diagnostic, not trusted execution. The parsed payload
    is validated separately before any MCP tool call is allowed.
    """

    endpoint = host.rstrip("/") + "/api/generate"
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "num_predict": max(1, min(int(num_predict), 512))},
        }
    ).encode("utf-8")
    request = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=max(0.5, float(timeout_seconds))) as response:  # noqa: S310 - local operator-configured endpoint
            raw = response.read(4_000_000)
    except urllib.error.URLError as exc:
        return {"ok": False, "status": "unavailable", "error": str(exc), "model": model, "host": host}
    except OSError as exc:
        return {"ok": False, "status": "error", "error": str(exc), "model": model, "host": host}
    duration = round(time.monotonic() - started, 3)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": "invalid_outer_response", "error": str(exc), "model": model, "host": host, "duration_seconds": duration}
    text = str(payload.get("response") or "") if isinstance(payload, dict) else ""
    try:
        parsed = json.loads(text) if text.strip() else None
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "status": "invalid_inner_json",
            "error": str(exc),
            "model": model,
            "host": host,
            "duration_seconds": duration,
            "response_text": text,
            "raw": payload,
        }
    return {
        "ok": isinstance(parsed, dict),
        "status": "parsed" if isinstance(parsed, dict) else "not_an_object",
        "model": model,
        "host": host,
        "duration_seconds": duration,
        "response_text": text,
        "parsed": parsed,
        "raw": payload,
    }


def _normalize_model_tool_name(tool: Any) -> str | None:
    if not isinstance(tool, str):
        return None
    cleaned = tool.strip()
    if not cleaned:
        return None
    # Direct MCP names remain accepted for compatibility with v0.0.143 tests.
    if cleaned in {spec.name for spec in READ_ONLY_MCP_TOOLS}:
        return cleaned
    alias = cleaned.lower().replace("-", "_").replace(".", "_").replace(" ", "_")
    aliases = {
        "read_file": "filesystem.read",
        "filesystem_read": "filesystem.read",
        "file_read": "filesystem.read",
        "read_version": "filesystem.read",
        "git_status": "git.status",
        "status": "git.status",
        "git_diff_summary": "git.diff.summary",
        "diff_summary": "git.diff.summary",
        "list_files": "filesystem.list",
        "filesystem_list": "filesystem.list",
        "state_read": "promptbranch.state.read",
        "promptbranch_state_read": "promptbranch.state.read",
        "artifact_verify": "artifact.verify",
    }
    return aliases.get(alias)


def _alias_for_mcp_tool(tool: str | None) -> str | None:
    if tool is None:
        return None
    for alias, mcp_name in MODEL_TOOL_ALIAS_TO_MCP.items():
        if mcp_name == tool:
            return alias
    return None


def _validate_llm_mcp_tool_call(parsed: Any, *, original_request: str | None = None) -> dict[str, Any]:
    read_only_names = {spec.name for spec in READ_ONLY_MCP_TOOLS}
    if original_request is not None:
        risk = classify_agent_request_risk(original_request)
        if risk.get("risk") != ToolRisk.READ.value:
            return {
                "ok": False,
                "status": "original_request_not_read_only",
                "error": "original request risk is not read-only; model proposal is not eligible for execution",
                "request_risk": risk,
                "parsed": parsed,
            }
    if not isinstance(parsed, dict):
        return {"ok": False, "status": "not_an_object", "error": "model output must be a JSON object"}
    raw_tool = parsed.get("tool") or parsed.get("name")
    arguments = parsed.get("arguments") if isinstance(parsed.get("arguments"), dict) else parsed.get("args")
    if arguments is None:
        arguments = {}
    if not isinstance(raw_tool, str) or not raw_tool.strip():
        return {"ok": False, "status": "missing_tool", "error": "model output must include a tool string", "parsed": parsed}
    tool = _normalize_model_tool_name(raw_tool)
    if tool not in read_only_names:
        return {
            "ok": False,
            "status": "tool_not_allowed",
            "error": "model selected an unknown or non-read-only tool",
            "tool": raw_tool.strip(),
            "normalized_tool": tool,
            "supported_read_only_tools": sorted(read_only_names),
            "model_tool_aliases": MODEL_TOOL_ALIAS_TO_MCP,
            "parsed": parsed,
        }
    if not isinstance(arguments, dict):
        return {"ok": False, "status": "invalid_arguments", "error": "arguments must be a JSON object", "tool": tool, "parsed": parsed}
    if tool == "filesystem.read":
        path = arguments.get("path")
        if not isinstance(path, str) or not path.strip():
            # Only repair the common read VERSION prompt. Do not repair ambiguous file reads.
            if original_request and "version" in _normalized_request_text(original_request):
                arguments = dict(arguments)
                arguments["path"] = "VERSION"
                arguments["_repaired_missing_path"] = True
            else:
                return {"ok": False, "status": "invalid_arguments", "error": "filesystem.read requires repo-relative path", "tool": tool, "parsed": parsed}
        path = str(arguments.get("path") or "")
        if path.startswith("/") or ".." in path.split("/"):
            return {"ok": False, "status": "unsafe_path", "error": "filesystem.read path must be repo-relative and cannot traverse", "tool": tool, "arguments": arguments, "parsed": parsed}
        arguments.setdefault("max_bytes", 2000)
    return {
        "ok": True,
        "status": "validated",
        "tool": tool,
        "alias_tool": _alias_for_mcp_tool(tool),
        "arguments": arguments,
    }


def _call_ollama_chat_tool_call(
    *,
    request_text: str,
    model: str,
    host: str = DEFAULT_OLLAMA_HOST,
    timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    num_predict: int = 120,
) -> dict[str, Any]:
    endpoint = host.rstrip("/") + "/api/chat"
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a read-only tool selection engine for Promptbranch. "
                        "Use exactly one provided tool if the user asks to read a file or inspect git. "
                        "Do not answer with prose when a tool is appropriate."
                    ),
                },
                {"role": "user", "content": request_text},
            ],
            "tools": list(MODEL_FACING_TOOL_SCHEMAS),
            "stream": False,
            "options": {"temperature": 0, "num_predict": max(1, min(int(num_predict), 512))},
        }
    ).encode("utf-8")
    req = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=max(0.5, float(timeout_seconds))) as response:  # noqa: S310
            raw = response.read(4_000_000)
    except urllib.error.URLError as exc:
        return {"ok": False, "status": "unavailable", "error": str(exc), "model": model, "host": host, "source": "ollama_chat_tools_aliases"}
    except OSError as exc:
        return {"ok": False, "status": "error", "error": str(exc), "model": model, "host": host, "source": "ollama_chat_tools_aliases"}
    duration = round(time.monotonic() - started, 3)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": "invalid_outer_response", "error": str(exc), "model": model, "host": host, "duration_seconds": duration, "source": "ollama_chat_tools_aliases"}
    message = payload.get("message") if isinstance(payload, dict) else {}
    calls = message.get("tool_calls") if isinstance(message, dict) else None
    if not calls:
        return {"ok": False, "status": "no_tool_calls", "model": model, "host": host, "duration_seconds": duration, "raw": payload, "source": "ollama_chat_tools_aliases"}
    call = calls[0] if isinstance(calls, list) else None
    fn = call.get("function", {}) if isinstance(call, dict) else {}
    parsed = {"tool": fn.get("name"), "arguments": fn.get("arguments") or {}}
    return {"ok": True, "status": "tool_call", "model": model, "host": host, "duration_seconds": duration, "parsed": parsed, "raw_tool_call": call, "raw": payload, "source": "ollama_chat_tools_aliases"}


def _model_schema_prompt_for_request(request: str) -> str:
    return (
        "You are a tool-call selector. Return exactly one JSON object. No markdown. No prose.\n\n"
        "Allowed tool aliases:\n"
        "- read_file: read a repo-relative file, arguments {\"path\":\"VERSION\",\"max_bytes\":2000}\n"
        "- git_status: inspect git status, arguments {}\n"
        "- git_diff_summary: inspect git diff summary, arguments {}\n\n"
        "Examples:\n"
        "User: read VERSION\n"
        "Assistant: {\"tool\":\"read_file\",\"arguments\":{\"path\":\"VERSION\",\"max_bytes\":2000},\"reason\":\"Need to read VERSION file\"}\n\n"
        "User: git status\n"
        "Assistant: {\"tool\":\"git_status\",\"arguments\":{},\"reason\":\"Need repository git status\"}\n\n"
        f"Now classify this user request:\nUser: {request}\nAssistant:"
    )


def ollama_propose_mcp_tool_call(
    request: str,
    *,
    model: str = DEFAULT_OLLAMA_TOOL_MODEL,
    ollama_host: str = DEFAULT_OLLAMA_HOST,
    ollama_timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    allow_schema_fallback: bool = True,
) -> dict[str, Any]:
    request_risk = classify_agent_request_risk(request)
    if request_risk.get("risk") != ToolRisk.READ.value:
        return {
            "ok": False,
            "action": "agent_ollama_propose",
            "status": "risk_rejected",
            "mode": "ollama_proposes_read_only_tool",
            "request": request,
            "request_risk": request_risk,
            "selected": None,
            "proposals": [],
            "model_tool_aliases": MODEL_TOOL_ALIAS_TO_MCP,
        }

    proposals: list[dict[str, Any]] = []
    chat = _call_ollama_chat_tool_call(
        request_text=request,
        model=model,
        host=ollama_host,
        timeout_seconds=ollama_timeout_seconds,
        num_predict=120,
    )
    chat_validation = _validate_llm_mcp_tool_call(chat.get("parsed"), original_request=request)
    chat["validation"] = chat_validation
    proposals.append(chat)
    if chat.get("ok") and chat_validation.get("ok"):
        selected = {**chat_validation, "source": chat.get("source"), "model": model}
        return {
            "ok": True,
            "action": "agent_ollama_propose",
            "status": "validated",
            "mode": "ollama_proposes_read_only_tool",
            "request": request,
            "request_risk": request_risk,
            "selected": selected,
            "proposals": proposals,
            "model_tool_aliases": MODEL_TOOL_ALIAS_TO_MCP,
        }

    if allow_schema_fallback:
        schema = _call_ollama_generate_json(
            prompt=_model_schema_prompt_for_request(request),
            model=model,
            host=ollama_host,
            timeout_seconds=ollama_timeout_seconds,
            num_predict=120,
        )
        schema["source"] = "ollama_generate_schema_aliases"
        schema_validation = _validate_llm_mcp_tool_call(schema.get("parsed"), original_request=request)
        schema["validation"] = schema_validation
        proposals.append(schema)
        if schema.get("ok") and schema_validation.get("ok"):
            selected = {**schema_validation, "source": schema.get("source"), "model": model}
            return {
                "ok": True,
                "action": "agent_ollama_propose",
                "status": "validated",
                "mode": "ollama_proposes_read_only_tool",
                "request": request,
                "request_risk": request_risk,
                "selected": selected,
                "proposals": proposals,
                "model_tool_aliases": MODEL_TOOL_ALIAS_TO_MCP,
            }

    return {
        "ok": False,
        "action": "agent_ollama_propose",
        "status": "model_tool_call_invalid",
        "mode": "ollama_proposes_read_only_tool",
        "request": request,
        "request_risk": request_risk,
        "selected": None,
        "proposals": proposals,
        "model_tool_aliases": MODEL_TOOL_ALIAS_TO_MCP,
    }


def mcp_tool_call_via_stdio(
    tool: str,
    arguments: Optional[dict[str, Any]] = None,
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    command: str | None = None,
    resolve_command: bool = True,
    timeout_seconds: float = 8.0,
    include_controlled_processes: bool | None = None,
    include_controlled_writes: bool | None = None,
) -> dict[str, Any]:
    """Call one MCP tool through the actual stdio server boundary.

    Read-only tools use the default read-only server. The first controlled
    process tool, ``test.smoke``, explicitly starts the server with controlled
    tools listed and only that bounded process tool executable.
    """

    root = Path(repo_path).expanduser().resolve()
    resolved_profile = Path(profile_dir).expanduser().resolve() if profile_dir else None
    normalized_tool = _normalize_mcp_tool_name(tool)
    if include_controlled_processes is None:
        include_controlled_processes = normalized_tool in _controlled_process_tool_names()
    include_processes = _coerce_controlled_process_flag(bool(include_controlled_processes), include_controlled_writes)
    config = mcp_host_config(repo_path=root, profile_dir=resolved_profile, command=command, resolve_command=resolve_command, include_controlled_processes=include_processes)
    server = config["config"]["mcpServers"]["promptbranch"]
    tool_arguments = arguments or {}
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": MCP_PROTOCOL_VERSION}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": normalized_tool, "arguments": tool_arguments}},
    ]
    request_text = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in messages)
    requested_transport_timeout = max(1.0, float(timeout_seconds))
    transport_timeout = requested_transport_timeout
    tool_timeout: float | None = None
    if normalized_tool in _controlled_process_tool_names():
        requested_tool_timeout = float(tool_arguments.get("timeout_seconds") or 60.0)
        tool_timeout = min(max(requested_tool_timeout, 5.0), 300.0)
        transport_timeout = max(transport_timeout, tool_timeout + 5.0)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [str(server["command"]), *[str(arg) for arg in server.get("args", [])]],
            input=request_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=transport_timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return {"ok": False, "action": "mcp_tool_call_via_stdio", "status": "command_not_found", "config": config, "error": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "action": "mcp_tool_call_via_stdio",
            "status": "timeout",
            "config": config,
            "timeout_seconds": tool_timeout if tool_timeout is not None else transport_timeout,
            "tool_timeout_seconds": tool_timeout,
            "transport_timeout_seconds": transport_timeout,
            "requested_transport_timeout_seconds": timeout_seconds,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    except OSError as exc:
        return {"ok": False, "action": "mcp_tool_call_via_stdio", "status": "os_error", "config": config, "error": str(exc)}
    duration = round(time.monotonic() - started, 3)
    responses = _read_json_lines(completed.stdout)
    call_response = next((item for item in responses if isinstance(item, dict) and item.get("id") == 2), None)
    result = call_response.get("result") if isinstance(call_response, dict) and isinstance(call_response.get("result"), dict) else {}
    is_error = bool(result.get("isError")) if isinstance(result, dict) else True
    return {
        "ok": completed.returncode == 0 and not is_error and isinstance(call_response, dict),
        "action": "mcp_tool_call_via_stdio",
        "status": "verified" if completed.returncode == 0 and not is_error and isinstance(call_response, dict) else "failed",
        "transport": "stdio",
        "tool": normalized_tool,
        "requested_tool": tool,
        "arguments": tool_arguments,
        "duration_seconds": duration,
        "timeout_seconds": tool_timeout if tool_timeout is not None else transport_timeout,
        "tool_timeout_seconds": tool_timeout,
        "transport_timeout_seconds": transport_timeout,
        "requested_transport_timeout_seconds": timeout_seconds,
        "config": config,
        "responses": responses,
        "tool_response": call_response,
        "stderr": completed.stderr.strip(),
        "returncode": completed.returncode,
    }


def agent_mcp_llm_smoke(
    request: str = "read VERSION",
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    model: str = DEFAULT_OLLAMA_TOOL_MODEL,
    ollama_host: str = DEFAULT_OLLAMA_HOST,
    ollama_timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    command: str | None = None,
    mcp_timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    """Diagnostic: let Ollama propose one read-only MCP tool call, then execute it via stdio.

    The original request is risk-classified before any model proposal can execute.
    A destructive request that the model reframes as a benign read is rejected.
    """

    proposal = ollama_propose_mcp_tool_call(
        request,
        model=model,
        ollama_host=ollama_host,
        ollama_timeout_seconds=ollama_timeout_seconds,
        allow_schema_fallback=True,
    )
    selected = proposal.get("selected") if isinstance(proposal, dict) else None
    if not proposal.get("ok") or not isinstance(selected, dict):
        return {
            "ok": False,
            "action": "agent_mcp_llm_smoke",
            "status": proposal.get("status", "model_tool_call_invalid") if isinstance(proposal, dict) else "model_tool_call_invalid",
            "mode": "ollama_proposes_validated_mcp_stdio",
            "request": request,
            "ollama_proposal": proposal,
            "validation": selected,
            "mcp": None,
            "safety": {
                "model_has_execution_authority": False,
                "original_request_risk_checked": True,
                "promptbranch_validates_read_only_allowlist": True,
                "write_tools_blocked": True,
            },
        }

    mcp_result = mcp_tool_call_via_stdio(
        str(selected["tool"]),
        selected.get("arguments") if isinstance(selected.get("arguments"), dict) else {},
        repo_path=repo_path,
        profile_dir=profile_dir,
        command=command,
        timeout_seconds=mcp_timeout_seconds,
    )
    return {
        "ok": bool(mcp_result.get("ok")),
        "action": "agent_mcp_llm_smoke",
        "status": "verified" if mcp_result.get("ok") else "mcp_call_failed",
        "mode": "ollama_proposes_validated_mcp_stdio",
        "request": request,
        "ollama_proposal": proposal,
        "validation": selected,
        "mcp": mcp_result,
        "safety": {
            "model_has_execution_authority": False,
            "original_request_risk_checked": True,
            "promptbranch_validates_read_only_allowlist": True,
            "write_tools_blocked": True,
            "transport": "stdio",
        },
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

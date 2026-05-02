"""Read-only MCP/Ollama planning and stdio server scaffold for Promptbranch.

The default MCP surface is deliberately read-only. Controlled write tools can
be listed for planning, but the stdio server rejects their execution until a
future deterministic executor layer explicitly enables and validates them.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from promptbranch_artifacts import ArtifactRegistry, iter_repo_files, read_version, verify_zip_artifact
from promptbranch_shell_model import ToolRisk, required_prechecks_for_action, risk_for_action
from promptbranch_state import ConversationStateStore, resolve_profile_dir

MCP_SCHEMA_VERSION = 1
MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_SERVER_VERSION = "0.0.141"
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
    include_controlled_writes: bool = False,
    host: str = "generic",
) -> dict[str, Any]:
    """Return an MCP host configuration snippet for this repo."""

    root = Path(repo_path).expanduser().resolve()
    resolved_profile = Path(profile_dir).expanduser().resolve() if profile_dir else None
    command_resolution = resolve_mcp_executable(command, resolve_command=resolve_command)
    args: list[str] = []
    if resolved_profile is not None:
        args.extend(["--profile-dir", str(resolved_profile)])
    args.extend(["mcp", "serve", "--path", str(root)])
    if include_controlled_writes:
        args.append("--include-controlled-writes")

    server = {"command": str(command_resolution["command"]), "args": args}
    config = {"mcpServers": {server_name: server}}
    install_notes = [
        "Add config.mcpServers.promptbranch to your MCP host configuration.",
        "Use an executable command path; shell aliases usually do not work in GUI-launched MCP hosts.",
        "The server is read-only by default; controlled write tools are listed only when requested and are not executable yet.",
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
        "mode": "read_only" if not include_controlled_writes else "read_only_plus_controlled_writes",
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
            "reason": "v0.0.141 exposes deterministic read-only planning and MCP host config first; Ollama integration remains a later adapter.",
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
    if tool_name == "artifact.verify":
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Artifact ZIP path. Defaults to current registry artifact."},
            },
            "additionalProperties": False,
        }
    return {"type": "object", "properties": {}, "additionalProperties": False}


def mcp_server_tools(*, include_controlled_writes: bool = False) -> list[dict[str, Any]]:
    manifest = mcp_tool_manifest(include_controlled_writes=include_controlled_writes)
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
    include_controlled_writes: bool = False,
) -> dict[str, Any] | None:
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
                "instructions": "Promptbranch MCP exposes read-only repo/git/state/artifact tools by default. Write tools are policy-gated and not executable from this server yet.",
            },
        )

    if method in {"ping", "$/ping"}:
        return _jsonrpc_result(message_id, {})

    if method == "tools/list":
        return _jsonrpc_result(message_id, {"tools": mcp_server_tools(include_controlled_writes=include_controlled_writes)})

    if method == "tools/call":
        name = str(params.get("name") or "")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        manifest_tools = mcp_tool_manifest(include_controlled_writes=include_controlled_writes).get("tools", [])
        tool_meta = next((tool for tool in manifest_tools if isinstance(tool, dict) and tool.get("name") == name), None)
        if tool_meta is None:
            return _jsonrpc_result(message_id, _mcp_content({"ok": False, "error": "unknown_tool", "tool": name}, is_error=True))
        if not bool(tool_meta.get("read_only")):
            return _jsonrpc_result(
                message_id,
                _mcp_content(
                    {
                        "ok": False,
                        "error": "write_tool_not_executable_via_mcp_serve",
                        "tool": name,
                        "required_policy": "deterministic_executor_prechecks",
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
    include_controlled_writes: bool = False,
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


def mcp_host_smoke(
    *,
    repo_path: str | Path = ".",
    profile_dir: str | Path | None = None,
    server_name: str = "promptbranch",
    command: str | None = None,
    resolve_command: bool = True,
    include_controlled_writes: bool = False,
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
        include_controlled_writes=include_controlled_writes,
        host=host,
    )
    server = config["config"]["mcpServers"][server_name]
    read_path = "VERSION" if (root / "VERSION").is_file() else "README.md"
    if not (root / read_path).is_file():
        read_path = "."
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

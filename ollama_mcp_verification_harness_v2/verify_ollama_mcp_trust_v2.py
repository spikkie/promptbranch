#!/usr/bin/env python3
"""Ollama -> validated Promptbranch MCP verification harness v2.

v2 changes from the first harness:
- Model-facing tool names are simple aliases: read_file, git_status, git_diff_summary.
- Promptbranch maps aliases back to MCP tool names: filesystem.read, git.status, git.diff.summary.
- Ollama proposals are never executed until validated.
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, time, urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

TOOL_ALIAS_TO_MCP = {
    "read_file": "filesystem.read",
    "git_status": "git.status",
    "git_diff_summary": "git.diff.summary",
    "state_read": "promptbranch.state.read",
    "artifact_verify": "artifact.verify",
}
ALLOWED_MCP_TOOLS = set(TOOL_ALIAS_TO_MCP.values())

TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a repo-relative file. Use this to read VERSION.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "max_bytes": {"type": "integer"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "git_status", "description": "Read git branch, dirty state, and diff stat.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "git_diff_summary", "description": "Read a concise git diff summary.", "parameters": {"type": "object", "properties": {}, "required": []}}},
]

PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": list(TOOL_ALIAS_TO_MCP.keys())},
        "arguments": {"type": "object"},
        "reason": {"type": "string"},
    },
    "required": ["tool", "arguments"],
}

@dataclass
class Proposal:
    source: str
    model: str
    ok: bool
    alias_tool: Optional[str] = None
    mcp_tool: Optional[str] = None
    arguments: Optional[dict] = None
    raw: Any = None
    error: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    def to_json(self) -> dict:
        return {"source": self.source, "model": self.model, "ok": self.ok, "alias_tool": self.alias_tool, "mcp_tool": self.mcp_tool, "arguments": self.arguments, "error": self.error, "elapsed_seconds": self.elapsed_seconds, "raw": self.raw}

def post_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        lines = [x for x in body.splitlines() if x.strip()]
        if not lines:
            raise
        return json.loads(lines[-1])

def normalize_alias_tool(tool: Any) -> Optional[str]:
    if not isinstance(tool, str):
        return None
    lowered = tool.strip().lower().replace("-", "_").replace(".", "_").replace(" ", "_")
    aliases = {
        "read_file": "read_file", "file_read": "read_file", "filesystem_read": "read_file", "read_version": "read_file",
        "git_status": "git_status", "status": "git_status",
        "git_diff_summary": "git_diff_summary", "diff_summary": "git_diff_summary",
        "state_read": "state_read", "promptbranch_state_read": "state_read",
        "artifact_verify": "artifact_verify",
    }
    return aliases.get(lowered)

def validate_proposal(obj: Any) -> Tuple[bool, Optional[str], Optional[str], Optional[dict], Optional[str]]:
    if not isinstance(obj, dict):
        return False, None, None, None, f"proposal_not_object:{type(obj).__name__}"
    alias_tool = normalize_alias_tool(obj.get("tool") or obj.get("name"))
    if not alias_tool:
        return False, None, None, None, f"missing_or_unknown_alias_tool:{obj.get('tool')!r}"
    mcp_tool = TOOL_ALIAS_TO_MCP.get(alias_tool)
    if mcp_tool not in ALLOWED_MCP_TOOLS:
        return False, alias_tool, mcp_tool, None, f"mcp_tool_not_allowed:{mcp_tool}"
    args = obj.get("arguments") or {}
    if not isinstance(args, dict):
        return False, alias_tool, mcp_tool, None, "arguments_not_object"
    if alias_tool == "read_file":
        path = args.get("path")
        if not isinstance(path, str) or not path.strip():
            args["path"] = "VERSION"
            args["_repaired_missing_path"] = True
            path = "VERSION"
        if path.startswith("/") or ".." in path.split("/"):
            return False, alias_tool, mcp_tool, args, "read_file_path_not_repo_relative"
        args.setdefault("max_bytes", 2000)
    return True, alias_tool, mcp_tool, args, None

def ollama_generate_schema(model: str, user_request: str, base_url: str, timeout: int) -> Proposal:
    start = time.time()
    prompt = f"""
You are a tool-call selector. Return exactly one JSON object. No markdown. No prose.
Allowed tool aliases:
- read_file: read repo-relative file, arguments {{"path":"VERSION","max_bytes":2000}}
- git_status: inspect git status, arguments {{}}
- git_diff_summary: inspect git diff summary, arguments {{}}
Example user: read VERSION
Example assistant: {{"tool":"read_file","arguments":{{"path":"VERSION","max_bytes":2000}},"reason":"Need to read VERSION"}}
Example user: git status
Example assistant: {{"tool":"git_status","arguments":{{}},"reason":"Need git status"}}
User: {user_request}
Assistant:
""".strip()
    payload = {"model": model, "prompt": prompt, "stream": False, "format": PROPOSAL_SCHEMA, "options": {"temperature": 0, "num_predict": 100}}
    try:
        response = post_json(f"{base_url.rstrip('/')}/api/generate", payload, timeout)
        raw_text = response.get("response", "")
        try:
            obj = json.loads(raw_text)
        except Exception as exc:
            return Proposal("ollama_generate_schema_aliases", model, False, raw=raw_text, error=f"invalid_json:{exc}", elapsed_seconds=time.time()-start)
        ok, alias_tool, mcp_tool, args, err = validate_proposal(obj)
        return Proposal("ollama_generate_schema_aliases", model, ok, alias_tool, mcp_tool, args, obj, err, time.time()-start)
    except Exception as exc:
        return Proposal("ollama_generate_schema_aliases", model, False, error=f"request_error:{exc}", elapsed_seconds=time.time()-start)

def ollama_chat_tools(model: str, user_request: str, base_url: str, timeout: int) -> Proposal:
    start = time.time()
    payload = {"model": model, "messages": [{"role": "system", "content": "You are a tool selection engine. Use exactly one provided tool if useful. Do not answer with prose."}, {"role": "user", "content": user_request}], "tools": TOOL_SCHEMAS, "stream": False, "options": {"temperature": 0, "num_predict": 100}}
    try:
        response = post_json(f"{base_url.rstrip('/')}/api/chat", payload, timeout)
        message = response.get("message") or {}
        calls = message.get("tool_calls") or []
        if not calls:
            return Proposal("ollama_chat_tools_aliases", model, False, raw=response, error="no_tool_calls", elapsed_seconds=time.time()-start)
        fn = calls[0].get("function", {}) if isinstance(calls[0], dict) else {}
        obj = {"tool": fn.get("name"), "arguments": fn.get("arguments") or {}}
        ok, alias_tool, mcp_tool, args, err = validate_proposal(obj)
        return Proposal("ollama_chat_tools_aliases", model, ok, alias_tool, mcp_tool, args, calls[0], err, time.time()-start)
    except Exception as exc:
        return Proposal("ollama_chat_tools_aliases", model, False, error=f"request_error:{exc}", elapsed_seconds=time.time()-start)

def langchain_chatollama_tools(model: str, user_request: str, timeout: int) -> Proposal:
    start = time.time()
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.tools import tool
    except Exception as exc:
        return Proposal("langchain_chatollama_tools_aliases", model, False, error=f"skipped_missing_dependency:{exc}", elapsed_seconds=time.time()-start)
    try:
        @tool
        def read_file(path: str, max_bytes: int = 2000) -> str:
            """Read a repo-relative file. Use for VERSION."""
            return "TOOL_SCHEMA_ONLY"
        @tool
        def git_status() -> str:
            """Read git branch and dirty status."""
            return "TOOL_SCHEMA_ONLY"
        @tool
        def git_diff_summary() -> str:
            """Read a concise git diff summary."""
            return "TOOL_SCHEMA_ONLY"
        result = ChatOllama(model=model, temperature=0).bind_tools([read_file, git_status, git_diff_summary]).invoke(user_request)
        calls = getattr(result, "tool_calls", None) or []
        invalid = getattr(result, "invalid_tool_calls", None) or []
        if not calls:
            return Proposal("langchain_chatollama_tools_aliases", model, False, raw={"content": getattr(result, "content", None), "invalid_tool_calls": invalid}, error="no_tool_calls", elapsed_seconds=time.time()-start)
        first = calls[0]
        obj = {"tool": first.get("name") if isinstance(first, dict) else getattr(first, "name", None), "arguments": first.get("args") if isinstance(first, dict) else getattr(first, "args", {})}
        ok, alias_tool, mcp_tool, args, err = validate_proposal(obj)
        return Proposal("langchain_chatollama_tools_aliases", model, ok, alias_tool, mcp_tool, args, first, err, time.time()-start)
    except Exception as exc:
        return Proposal("langchain_chatollama_tools_aliases", model, False, error=f"langchain_error:{exc}", elapsed_seconds=time.time()-start)

def call_promptbranch_mcp_stdio(pb_command: str, repo_path: str, mcp_tool: str, arguments: dict, timeout: int) -> dict:
    request_lines = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": mcp_tool, "arguments": arguments}},
    ]
    proc = subprocess.run([pb_command, "mcp", "serve", "--path", repo_path], input="\n".join(json.dumps(x) for x in request_lines)+"\n", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    outputs = []
    for line in proc.stdout.splitlines():
        if line.strip():
            try: outputs.append(json.loads(line))
            except Exception: outputs.append({"raw_line": line})
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stderr": proc.stderr, "responses": outputs}

def choose_best(proposals: Iterable[Proposal]) -> Optional[Proposal]:
    order = {"ollama_chat_tools_aliases": 0, "ollama_generate_schema_aliases": 1, "langchain_chatollama_tools_aliases": 2}
    for p in sorted(list(proposals), key=lambda p: order.get(p.source, 9)):
        if p.ok and p.mcp_tool and p.arguments is not None:
            return p
    return None

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-path", default=".")
    ap.add_argument("--prompt", default="read VERSION")
    ap.add_argument("--models", nargs="+", default=["llama3.2:3b", "qwen2.5-coder:3b"])
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    ap.add_argument("--pb-command", default=os.environ.get("PB_COMMAND", "promptbranch"))
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--try-langchain", action="store_true")
    ap.add_argument("--execute-first-valid", action="store_true")
    args = ap.parse_args(argv)
    repo_path = os.path.abspath(args.repo_path)
    pb_command = shutil.which(args.pb_command) or args.pb_command
    proposals: List[Proposal] = []
    for model in args.models:
        proposals.append(ollama_generate_schema(model, args.prompt, args.ollama_url, args.timeout))
        proposals.append(ollama_chat_tools(model, args.prompt, args.ollama_url, args.timeout))
        if args.try_langchain:
            proposals.append(langchain_chatollama_tools(model, args.prompt, args.timeout))
    selected = choose_best(proposals)
    report: Dict[str, Any] = {
        "ok": bool(selected), "version": "v2", "repo_path": repo_path, "prompt": args.prompt, "ollama_url": args.ollama_url,
        "pb_command": pb_command, "models": args.models, "model_facing_tool_aliases": TOOL_ALIAS_TO_MCP,
        "proposals": [p.to_json() for p in proposals], "selected": selected.to_json() if selected else None,
        "mcp_execution": None,
        "notes": ["Model-facing tools use simple aliases; Promptbranch maps aliases to MCP tool names.", "Ollama proposals are not executed until validated."],
    }
    if selected and args.execute_first_valid:
        report["mcp_execution"] = call_promptbranch_mcp_stdio(pb_command, repo_path, selected.mcp_tool or "", selected.arguments or {}, args.timeout)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())

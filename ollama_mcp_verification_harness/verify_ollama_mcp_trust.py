#!/usr/bin/env python3
"""
verify_ollama_mcp_trust.py

Purpose:
  Verify whether local Ollama models can reliably propose MCP tool calls,
  then execute only validated read-only calls through Promptbranch's MCP server.

Compares:
  1. Raw Ollama /api/generate with JSON schema
  2. Ollama /api/chat native tool-calling
  3. Optional LangChain ChatOllama bind_tools
  4. Validated MCP stdio execution through: promptbranch mcp serve --path <repo>
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


ALLOWED_TOOLS = {
    "filesystem.read",
    "git.status",
    "git.diff.summary",
    "promptbranch.state.read",
    "artifact.verify",
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "filesystem.read",
            "description": "Read a repo-relative file from the current repository. Use this for VERSION.",
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
            "name": "git.status",
            "description": "Read git branch, dirty status, and diff stat for the repository.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git.diff.summary",
            "description": "Read a short git diff summary for the repository.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string"},
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
    tool: Optional[str] = None
    arguments: Optional[dict] = None
    raw: Any = None
    error: Optional[str] = None
    elapsed_seconds: Optional[float] = None

    def to_json(self) -> dict:
        return {
            "source": self.source,
            "model": self.model,
            "ok": self.ok,
            "tool": self.tool,
            "arguments": self.arguments,
            "error": self.error,
            "elapsed_seconds": self.elapsed_seconds,
            "raw": self.raw,
        }


def post_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def validate_proposal(obj: Any) -> Tuple[bool, Optional[str], Optional[dict], Optional[str]]:
    if not isinstance(obj, dict):
        return False, None, None, f"proposal_not_object:{type(obj).__name__}"
    tool = obj.get("tool")
    args = obj.get("arguments")
    if not isinstance(tool, str) or not tool:
        return False, None, None, "missing_tool"
    if tool not in ALLOWED_TOOLS:
        return False, tool, args if isinstance(args, dict) else None, f"tool_not_allowed:{tool}"
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return False, tool, None, "arguments_not_object"

    if tool == "filesystem.read":
        path = args.get("path")
        if not isinstance(path, str) or not path.strip():
            return False, tool, args, "filesystem_read_missing_path"
        if path.startswith("/") or ".." in path.split("/"):
            return False, tool, args, "filesystem_read_path_not_repo_relative"
        args.setdefault("max_bytes", 2000)

    return True, tool, args, None


def ollama_generate_schema(model: str, prompt: str, base_url: str, timeout: int) -> Proposal:
    start = time.time()
    payload = {
        "model": model,
        "prompt": (
            "Return one JSON object matching this schema exactly: "
            '{"tool": string, "arguments": object, "reason": string}. '
            "Allowed tools are filesystem.read, git.status, git.diff.summary, "
            "promptbranch.state.read, artifact.verify. "
            f"User request: {prompt}"
        ),
        "stream": False,
        "format": PROPOSAL_SCHEMA,
        "options": {"temperature": 0, "num_predict": 120},
    }
    try:
        response = post_json(f"{base_url.rstrip('/')}/api/generate", payload, timeout)
        raw_text = response.get("response", "")
        try:
            obj = json.loads(raw_text)
        except Exception as exc:
            return Proposal("ollama_generate_schema", model, False, raw=raw_text, error=f"invalid_json:{exc}", elapsed_seconds=time.time()-start)
        ok, tool, args, err = validate_proposal(obj)
        return Proposal("ollama_generate_schema", model, ok, tool=tool, arguments=args, raw=obj, error=err, elapsed_seconds=time.time()-start)
    except Exception as exc:
        return Proposal("ollama_generate_schema", model, False, error=f"request_error:{exc}", elapsed_seconds=time.time()-start)


def ollama_chat_tools(model: str, prompt: str, base_url: str, timeout: int) -> Proposal:
    start = time.time()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a tool selection engine. Use exactly one provided tool when useful. "
                    "Do not answer with prose if a tool is appropriate."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "tools": TOOL_SCHEMAS,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 120},
    }
    try:
        response = post_json(f"{base_url.rstrip('/')}/api/chat", payload, timeout)
        message = response.get("message") or {}
        calls = message.get("tool_calls") or []
        if not calls:
            return Proposal("ollama_chat_tools", model, False, raw=response, error="no_tool_calls", elapsed_seconds=time.time()-start)
        call = calls[0]
        fn = call.get("function", {}) if isinstance(call, dict) else {}
        obj = {"tool": fn.get("name"), "arguments": fn.get("arguments") or {}}
        ok, tool, args, err = validate_proposal(obj)
        return Proposal("ollama_chat_tools", model, ok, tool=tool, arguments=args, raw=call, error=err, elapsed_seconds=time.time()-start)
    except Exception as exc:
        return Proposal("ollama_chat_tools", model, False, error=f"request_error:{exc}", elapsed_seconds=time.time()-start)


def langchain_chatollama_tools(model: str, prompt: str, timeout: int) -> Proposal:
    start = time.time()
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.tools import tool
    except Exception as exc:
        return Proposal("langchain_chatollama_tools", model, False, error=f"skipped_missing_dependency:{exc}", elapsed_seconds=time.time()-start)

    try:
        @tool
        def filesystem_read(path: str, max_bytes: int = 2000) -> str:
            """Read a repo-relative file. Use for VERSION."""
            return "TOOL_SCHEMA_ONLY"

        @tool
        def git_status() -> str:
            """Read git branch and dirty status."""
            return "TOOL_SCHEMA_ONLY"

        model_obj = ChatOllama(model=model, temperature=0)
        with_tools = model_obj.bind_tools([filesystem_read, git_status])
        result = with_tools.invoke(prompt)
        calls = getattr(result, "tool_calls", None) or []
        invalid = getattr(result, "invalid_tool_calls", None) or []

        if not calls:
            return Proposal(
                "langchain_chatollama_tools",
                model,
                False,
                raw={"content": getattr(result, "content", None), "invalid_tool_calls": invalid},
                error="no_tool_calls",
                elapsed_seconds=time.time()-start,
            )

        first = calls[0]
        name = first.get("name") if isinstance(first, dict) else getattr(first, "name", None)
        args = first.get("args") if isinstance(first, dict) else getattr(first, "args", {})
        mapped = {"filesystem_read": "filesystem.read", "git_status": "git.status"}.get(name, name)
        obj = {"tool": mapped, "arguments": args or {}}
        ok, tool_name, norm_args, err = validate_proposal(obj)
        return Proposal("langchain_chatollama_tools", model, ok, tool=tool_name, arguments=norm_args, raw=first, error=err, elapsed_seconds=time.time()-start)
    except Exception as exc:
        return Proposal("langchain_chatollama_tools", model, False, error=f"langchain_error:{exc}", elapsed_seconds=time.time()-start)


def call_promptbranch_mcp_stdio(pb_command: str, repo_path: str, tool: str, arguments: dict, timeout: int) -> dict:
    request_lines = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": arguments}},
    ]
    input_data = "\n".join(json.dumps(x) for x in request_lines) + "\n"
    proc = subprocess.run(
        [pb_command, "mcp", "serve", "--path", repo_path],
        input=input_data,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    outputs = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            outputs.append(json.loads(line))
        except Exception:
            outputs.append({"raw_line": line})
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stderr": proc.stderr, "responses": outputs}


def choose_best(proposals: Iterable[Proposal]) -> Optional[Proposal]:
    for p in proposals:
        if p.ok and p.tool and p.arguments is not None:
            return p
    return None


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-path", default=".", help="Repository path passed to `pb mcp serve --path`")
    ap.add_argument("--prompt", default="read VERSION", help="User request to test")
    ap.add_argument("--models", nargs="+", default=["llama3.2:3b", "qwen2.5-coder:3b"], help="Ollama models to test")
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    ap.add_argument("--pb-command", default=os.environ.get("PB_COMMAND", "promptbranch"))
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--try-langchain", action="store_true", help="Also test LangChain ChatOllama bind_tools if dependencies are installed")
    ap.add_argument("--execute-first-valid", action="store_true", help="Execute first valid proposal through pb mcp serve stdio")
    args = ap.parse_args(argv)

    repo_path = os.path.abspath(args.repo_path)
    pb_command = shutil.which(args.pb_command) or args.pb_command

    report: Dict[str, Any] = {
        "ok": False,
        "repo_path": repo_path,
        "prompt": args.prompt,
        "ollama_url": args.ollama_url,
        "pb_command": pb_command,
        "models": args.models,
        "allowed_tools": sorted(ALLOWED_TOOLS),
        "proposals": [],
        "selected": None,
        "mcp_execution": None,
        "notes": [
            "This harness tests model proposals only. Promptbranch still validates and executes.",
            "A model is trusted only if it repeatedly proposes valid allowed read-only tools.",
        ],
    }

    all_proposals: List[Proposal] = []
    for model in args.models:
        all_proposals.append(ollama_generate_schema(model, args.prompt, args.ollama_url, args.timeout))
        all_proposals.append(ollama_chat_tools(model, args.prompt, args.ollama_url, args.timeout))
        if args.try_langchain:
            all_proposals.append(langchain_chatollama_tools(model, args.prompt, args.timeout))

    report["proposals"] = [p.to_json() for p in all_proposals]
    selected = choose_best(all_proposals)

    if selected:
        report["selected"] = selected.to_json()
        report["ok"] = True
        if args.execute_first_valid:
            report["mcp_execution"] = call_promptbranch_mcp_stdio(
                pb_command=pb_command,
                repo_path=repo_path,
                tool=selected.tool or "",
                arguments=selected.arguments or {},
                timeout=args.timeout,
            )
    else:
        report["ok"] = False

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

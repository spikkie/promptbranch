# Ollama MCP Verification Harness v2

This harness tests whether local Ollama models can propose safe MCP tool calls.

v2 improvement:

- model-facing tools use simple aliases:
  - `read_file`
  - `git_status`
  - `git_diff_summary`
- Promptbranch maps them to MCP tools:
  - `read_file` -> `filesystem.read`
  - `git_status` -> `git.status`
  - `git_diff_summary` -> `git.diff.summary`

This is closer to common Ollama/LangChain tool examples and avoids dotted function names.

## Basic test

```bash
python3 verify_ollama_mcp_trust_v2.py \
  --repo-path /home/spikkie/git/chatgpt_claudecode_workflow \
  --models llama3.2:3b qwen2.5-coder:3b qwen3:8b
```

## Execute first valid proposal through Promptbranch MCP stdio

```bash
python3 verify_ollama_mcp_trust_v2.py \
  --repo-path /home/spikkie/git/chatgpt_claudecode_workflow \
  --models llama3.2:3b qwen2.5-coder:3b qwen3:8b \
  --prompt "read VERSION" \
  --execute-first-valid
```

## Optional LangChain path

```bash
python3 -m pip install langchain-ollama langchain-core

python3 verify_ollama_mcp_trust_v2.py \
  --repo-path /home/spikkie/git/chatgpt_claudecode_workflow \
  --models llama3.2:3b qwen2.5-coder:3b qwen3:8b \
  --try-langchain \
  --execute-first-valid
```

## Interpretation

Good:

```json
{
  "ok": true,
  "selected": {
    "alias_tool": "read_file",
    "mcp_tool": "filesystem.read",
    "arguments": {"path": "VERSION", "max_bytes": 2000}
  },
  "mcp_execution": {
    "ok": true
  }
}
```

Bad but safe:

```json
{
  "ok": false,
  "selected": null
}
```

That means the model still should not be trusted for planning.

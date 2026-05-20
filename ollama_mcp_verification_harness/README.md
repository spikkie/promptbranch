# Ollama MCP Verification Harness

This is a small local test harness to check whether Ollama can propose MCP tool calls reliably enough
for Promptbranch.

It does **not** trust Ollama directly. It tests proposals, validates them, and optionally executes only
a validated read-only call through:

```bash
promptbranch mcp serve --path <repo>
```

## Run basic test

From your repo:

```bash
python3 verify_ollama_mcp_trust.py \
  --repo-path . \
  --models llama3.2:3b qwen2.5-coder:3b qwen3:8b
```

## Execute first valid model proposal through MCP

```bash
python3 verify_ollama_mcp_trust.py \
  --repo-path . \
  --models llama3.2:3b qwen2.5-coder:3b qwen3:8b \
  --prompt "read VERSION" \
  --execute-first-valid
```

## Optional LangChain test

```bash
python3 -m pip install langchain-ollama langchain-core

python3 verify_ollama_mcp_trust.py \
  --repo-path . \
  --models llama3.2:3b qwen2.5-coder:3b qwen3:8b \
  --try-langchain
```

## Interpretation

Good:

```json
"ok": true,
"selected": {
  "tool": "filesystem.read",
  "arguments": {"path": "VERSION"}
}
```

Bad but safe:

```json
"ok": false,
"error": "no_tool_calls"
```

or:

```json
"error": "invalid_json:..."
```

That means the model is not reliable enough for planning. It should remain summary-only.

## Safety

Allowed tools are intentionally read-only:

- `filesystem.read`
- `git.status`
- `git.diff.summary`
- `promptbranch.state.read`
- `artifact.verify`

The harness rejects unknown/write/destructive tools.

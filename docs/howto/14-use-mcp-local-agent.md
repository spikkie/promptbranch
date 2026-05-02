# Use the read-only MCP local agent surface

Promptbranch exposes a read-only MCP stdio server so local MCP hosts can inspect repo, git, Promptbranch state, and artifact metadata without giving the host write access.

## Inspect the local context

```bash
pb agent inspect . --json
pb agent doctor . --json
pb agent plan "sync repo" --json
```

`agent plan` is deterministic. It classifies the request and returns suggested commands, risk, and required prechecks. It does not execute write or destructive actions.

## View the MCP manifest

```bash
pb mcp manifest --json
pb mcp manifest --include-controlled-writes --json
```

The default manifest is read-only. `--include-controlled-writes` only lists gated write/process tools for planning; `pb mcp serve` still rejects their execution.

## Generate host configuration

```bash
pb mcp config --path . --json
```

The output contains a standard `mcpServers` snippet. By default, Promptbranch tries to resolve the executable to an absolute path:

```json
{
  "mcpServers": {
    "promptbranch": {
      "command": "/absolute/path/to/promptbranch",
      "args": ["mcp", "serve", "--path", "/absolute/repo/path"]
    }
  }
}
```

For GUI-launched MCP hosts, shell aliases usually do not work. You can force a specific executable or disable resolution explicitly:

```bash
pb mcp config --path . --command /home/spikkie/.local/bin/promptbranch --json
pb mcp config --path . --command promptbranch --no-resolve-command --json
```

## Verify host-style wiring

Before editing a real MCP host config, launch the generated server command and call read-only tools through stdio:

```bash
pb mcp host-smoke --path . --json
```

Expected checks include:

- `command_is_absolute=true`
- `initialize_ok=true`
- `tools_list_ok=true`
- `state_read_ok=true`
- `filesystem_read_ok=true`
- `git_status_ok=true`

## Run the stdio server smoke test

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n' \
  | pb mcp serve --path .
```

Expected result:

- `initialize` returns `serverInfo.name=promptbranch`
- `tools/list` returns read-only tools such as `filesystem.read`, `git.status`, and `promptbranch.state.read`

## Run the suite check

```bash
pb test-suite --only mcp_smoke --json
pb test-suite --only mcp_host_smoke --json
# or
pb test smoke --only mcp_smoke --json
pb test smoke --only mcp_host_smoke --json
```

These are local-only suite steps. They do not open ChatGPT and do not require a selected project.

## Safety boundary

The MCP server is intentionally read-only by default:

- filesystem tools are repo-bounded
- git tools only read status/diff summaries
- Promptbranch state tools only read `.pb_profile`
- artifact tools verify or inspect metadata
- controlled writes are not executable from `pb mcp serve` yet

Write-capable MCP execution should only be added after deterministic prechecks and transactional verification exist.

## Deterministic local agent commands

`pb agent ask` uses a rule-based read-only planner. It does not let Ollama choose tools.
Ollama may be used only for optional summaries of tool results.

```bash
pb agent ask "read VERSION and git status" --path . --json
pb agent tool-call filesystem.read '{"path":"VERSION"}' --path . --json
pb agent models --json
```

Expected behavior:

- `agent ask` maps simple read requests to safe MCP tools such as `filesystem.read` and `git.status`
- `agent tool-call` rejects unknown or write-capable tools
- `agent models` reports local Ollama availability, but Ollama failures do not block read-only MCP tool calls

This is deliberate. Small local models may produce `{}`, invalid JSON, or unrelated text even in JSON mode, so planning remains deterministic.

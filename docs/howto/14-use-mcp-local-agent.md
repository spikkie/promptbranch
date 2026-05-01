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

The output contains a standard `mcpServers` snippet:

```json
{
  "mcpServers": {
    "promptbranch": {
      "command": "promptbranch",
      "args": ["mcp", "serve", "--path", "/absolute/repo/path"]
    }
  }
}
```

For GUI-launched MCP hosts, shell aliases usually do not work. Use an executable command or an absolute path:

```bash
pb mcp config --path . --command /home/spikkie/.local/bin/promptbranch --json
```

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
# or
pb test smoke --only mcp_smoke --json
```

This is a local-only suite step. It does not open ChatGPT and does not require a selected project.

## Safety boundary

The MCP server is intentionally read-only by default:

- filesystem tools are repo-bounded
- git tools only read status/diff summaries
- Promptbranch state tools only read `.pb_profile`
- artifact tools verify or inspect metadata
- controlled writes are not executable from `pb mcp serve` yet

Write-capable MCP execution should only be added after deterministic prechecks and transactional verification exist.

# promptbranch v0.0.194

promptbranch is a stateful CLI and reusable browser-automation service for ChatGPT projects, sources, and conversations.

Primary interfaces:
- CLI: `promptbranch`
- Python package: `promptbranch`
- HTTP service: FastAPI app in `promptbranch_container_api.py`

Migration notes:
- `UPGRADING.md` documents the v0.0.68 alias removal and old-to-new name mapping
- `docs/howto/README.md` indexes task-focused how-to manuals for each main topic

Legacy `chatgpt_*` command/module/package aliases were removed in v0.0.68. See `UPGRADING.md` for the migration map from old names to `promptbranch_*`.


## How-to manuals

The repository now includes focused manuals under `docs/howto/` instead of forcing everything through one long README. Start with:

- `docs/howto/01-install-the-cli.md`
- `docs/howto/02-run-the-docker-service.md`
- `docs/howto/04-use-the-stateful-cli.md`
- `docs/howto/07-use-the-python-client.md`
- `docs/howto/12-troubleshooting.md`

## MCP / local agent scaffold

Read-only local inspection and planning commands:

```bash
pb agent inspect . --json
pb agent doctor . --json
pb agent plan "sync repo" --json
pb mcp manifest --json
```

Run the read-only MCP stdio server for a local MCP host:

```bash
pb mcp serve --path .
```

Generate a host configuration snippet and verify host-style read-only calls:

```bash
pb mcp config --path . --json
pb mcp host-smoke --path . --json
```

Deterministic local agent read-only execution:

```bash
pb agent ask "read VERSION and git status" --path . --json
pb agent tool-call filesystem.read '{"path":"VERSION"}' --path . --json
pb agent models --json
```

`pb agent ask` does not let Ollama plan tool calls. The planner is rule-based and read-only; Ollama is optional summary support only.

`pb mcp config` resolves `promptbranch` to an absolute executable path when possible because GUI-launched MCP hosts often do not inherit shell aliases. `pb mcp serve` exposes read-only repo/git/state/artifact tools. Controlled process tools may be listed with `--include-controlled-processes`; the only executable controlled process tool is bounded `test.smoke`, while source/artifact writes remain blocked. See `docs/howto/14-use-mcp-local-agent.md` for host config and smoke-test examples.

## Reusable Docker service

Build the image:

```bash
./build_chatgpt_service.sh
```

Or directly:

```bash
docker build -t promptbranch-service:0.0.164 .
```

Run it:

```bash
docker run --rm -it \
  -p 8000:8000 \
  -e CHATGPT_EMAIL="you@example.com" \
  -e CHATGPT_PASSWORD_FILE="/run/secrets/chatgpt_password" \
  -e CHATGPT_PROJECT_URL="https://chatgpt.com/" \
  -e CHATGPT_SERVICE_TOKEN="change-me" \
  -v "$PWD/.pb_profile:/app/.pb_profile" \
  -v "$PWD/debug_artifacts:/app/debug_artifacts" \
  -v "$HOME/.config/chatgpt/password.txt:/run/secrets/chatgpt_password:ro" \
  promptbranch-service:0.0.164
```

Compose option:

```bash
docker compose -f docker-compose.chatgpt-service.yml up --build
```

Development mode with Compose Watch:

```bash
./run_chatgpt_service_dev.sh
```

This enables `docker compose ... up --watch` and turns on Uvicorn reload inside the container so Python edits are applied without a manual rebuild. Changes to `Dockerfile`, `requirements.txt`, and `pyproject.toml` trigger an image rebuild instead of a file sync.

By default, the compose file now reads the host password file from:

```bash
$HOME/.config/chatgpt/password.txt
```

If your password file lives somewhere else, override it explicitly:

```bash
CHATGPT_PASSWORD_SECRET_FILE="$HOME/.config/chatgpt/password.txt" \
# Host-side `CHATGPT_PASSWORD_FILE` is intentionally ignored by the compose service.
CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS=1 \
  docker compose -f docker-compose.chatgpt-service.yml up --build
```

Or use the helper script:

```bash
./run_chatgpt_service.sh
```

The service starts with:
- Compose `develop.watch` rules for sync/rebuild in development mode
- OpenAPI docs at `/docs`
- health endpoint at `/healthz`
- versioned API under `/v1`


## Testing the Docker service

Start the service first:

```bash
./run_chatgpt_service.sh
```

Equivalent direct compose invocation:

```bash
CHATGPT_PASSWORD_SECRET_FILE="$HOME/.config/chatgpt/password.txt" \
# Host-side `CHATGPT_PASSWORD_FILE` is intentionally ignored by the compose service.
CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS=1 \
  docker compose -f docker-compose.chatgpt-service.yml up --build
```

For auto-reload during development, use `./run_chatgpt_service_dev.sh` instead.

For local headed debugging of the project sidebar using the existing promptbranch login/.pb_profile flow (no Docker service), run:

```bash
python ./promptbranch_full_integration_test.py \
  --config ~/.config/promptbranch/config.json \
  --profile-dir ./.pb_profile \
  --only project_list_debug \
  --keep-open
```

Optional debug tuning flags:
- `--project-list-debug-scroll-rounds <n>`
- `--project-list-debug-wait-ms <ms>`
- `--project-list-debug-manual-pause`

For project task-list undercount debugging, run the canonical debug command. It writes a timestamped artifact directory with DOM snapshots, screenshots, scroll-container diagnostics, and backend observations:

```bash
promptbranch debug chats --json
promptbranch debug task-list --json --scroll-rounds 30 --wait-ms 800
```

Use `--no-history` to avoid backend history/detail probes while inspecting only the project Chats tab DOM.

Then run the existing integration harness against Docker instead of the in-process Python stack:

```bash
python ./promptbranch_full_integration_test.py \
  --service-base-url http://localhost:8000 \
  --service-token change-me
```

Keep the project and skip cleanup while checking the currently stable surface:

```bash
python ./promptbranch_full_integration_test.py \
  --service-base-url http://localhost:8000 \
  --service-token change-me \
  --keep-project \
  --skip "project_source_remove_link,project_source_remove_text,project_source_remove_file"
```

Important:
- `python ./promptbranch_full_integration_test.py` by itself still runs the local Python/browser stack directly.
- Docker mode is enabled only when `--service-base-url` is provided.
- The Docker service can now carry the active `project_url` between steps, so the same integration harness works against both modes.


## API surface

### Health

```bash
curl http://localhost:8000/healthz
```

### Login check

```bash
curl -X POST http://localhost:8000/v1/login-check \
  -H 'Authorization: Bearer change-me' \
  -H 'Content-Type: application/json' \
  -d '{"keep_open": false}'
```

### Ask ChatGPT

```bash
curl -X POST http://localhost:8000/v1/ask \
  -H 'Authorization: Bearer change-me' \
  -F 'prompt=Reply with one short sentence.' \
  -F 'expect_json=false'
```

The response now includes both `answer` and `conversation_url`, so callers can continue the same project chat on follow-up asks.

### Add a text source

```bash
curl -X POST http://localhost:8000/v1/project-sources \
  -H 'Authorization: Bearer change-me' \
  -F 'type=text' \
  -F 'value=Reference notes for this run' \
  -F 'name=Notes'
```

### Add a file source

```bash
curl -X POST http://localhost:8000/v1/project-sources \
  -H 'Authorization: Bearer change-me' \
  -F 'type=file' \
  -F 'file=@./docs/spec.pdf'
```

### Remove a source

```bash
curl -X POST http://localhost:8000/v1/project-sources/remove \
  -H 'Authorization: Bearer change-me' \
  -H 'Content-Type: application/json' \
  -d '{"source_name": "Notes", "exact": true, "keep_open": false}'
```

## Python client for downstream projects

Example:

```python
from promptbranch import ChatGPTServiceClient

with ChatGPTServiceClient("http://localhost:8000", token="change-me") as client:
    print(client.healthz())
    answer = client.ask("Reply with one short sentence that says the service is ready.")
    print(answer)
```

There is also a runnable sample at `examples/promptbranch_service_client_example.py`.

## Installing the promptbranch CLI

Preferred for command-line use:

```bash
pipx install ./chatgpt_claudecode_workflow_v0.0.164.zip
```

From an extracted checkout:

```bash
python -m pip install .
```

After installation the `promptbranch` command is available:


```bash
promptbranch state
promptbranch prompt
promptbranch use "My Project"
promptbranch ask "hello"
```

Shell completion:

```bash
# bash
eval "$(promptbranch completion bash)"

# zsh
mkdir -p ~/.zsh/completions
promptbranch completion zsh > ~/.zsh/completions/_promptbranch

# fish
mkdir -p ~/.config/fish/completions
promptbranch completion fish > ~/.config/fish/completions/promptbranch.fish
```

For other Python programs, prefer importing the package facade instead of the smoke harness:

```python
from promptbranch import ChatGPTServiceClient, ConversationStateStore
```

`promptbranch_cli_sequence_v5.py` remains the primary smoke/integration harness.

## Low-level compatibility CLI usage

The preferred command is `promptbranch`.

The CLI can target either:
- local browser automation directly
- the Docker service API via `--service-base-url`

Headed login check against local automation:

```bash
promptbranch login-check --keep-open
```

Ask one question against local automation:

```bash
promptbranch ask "Explain Python context managers in 5 lines"
```

Attach one-off files to the chat message without adding them to Project Sources:

```bash
promptbranch ask "Analyze these logs" --attach ./logs/service.log --attach ./logs/browser.log
```

Read the prompt body from a file and optionally prepend a short inline instruction:

```bash
promptbranch ask "Focus on root cause and next fix" --prompt-file ./prompts/debug-request.md --attach ./logs/latest.log
```

Ask one question through the Docker service with explicit flags:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me ask "Explain Python context managers in 5 lines"
```

Ask one question through the Docker service without repeating flags each time:

1. Put the service settings in `.env` (loaded automatically by default):

```dotenv
CHATGPT_SERVICE_BASE_URL=http://localhost:8000
CHATGPT_SERVICE_TOKEN=change-me
```

2. Then run the shorter command:

```bash
promptbranch ask "Explain Python context managers in 5 lines"
```

You can also use a JSON config file. The CLI now checks `~/.config/promptbranch/config.json` by default and falls back to `~/.config/chatgpt-cli/config.json` when the new path is absent:

```json
{
  "service_base_url": "http://localhost:8000",
  "service_token": "change-me",
  "service_timeout_seconds": 300
}
```

```bash
promptbranch ask "Explain Python context managers in 5 lines"
promptbranch --config ~/.config/promptbranch/config.json ask "Explain Python context managers in 5 lines"
```

Create a project through the Docker service:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me project-create "Demo Project" --icon folder --color blue
```

Add a text source to a specific project through the Docker service:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me --project-url https://chatgpt.com/g/g-p-.../project project-source-add --type text --value "Reference notes for this project" --name "Notes"
```

Add a file source to a specific project through the Docker service:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me --project-url https://chatgpt.com/g/g-p-.../project project-source-add --type file --file ./docs/spec.pdf
```

Remove a source from a project:

```bash
promptbranch project-source-remove "Notes" --exact --dotenv .env
```

Open the interactive shell through the Docker service:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me shell
```

## Environment variables

Core service settings:
- `CHATGPT_PROJECT_URL`
- `CHATGPT_EMAIL`
- `CHATGPT_PASSWORD`
- `CHATGPT_PASSWORD_FILE` (inside the container this is fixed to `/run/secrets/chatgpt_password` in the compose service)
- `CHATGPT_CLI_CONFIG` (optional JSON config file path for CLI defaults)
- `CHATGPT_HEADLESS`
- `CHATGPT_USE_PATCHRIGHT`
- `CHATGPT_BROWSER_CHANNEL`
- `CHATGPT_DISABLE_FEDCM`
- `CHATGPT_FILTER_NO_SANDBOX`
- `CHATGPT_MAX_RETRIES`
- `CHATGPT_RETRY_BACKOFF_SECONDS`
- `CHATGPT_MIN_CONTEXT_SPACING_SECONDS`
- `CHATGPT_CONVERSATION_HISTORY_RATE_LIMIT_COOLDOWN_SECONDS`
- `CHATGPT_SERVICE_TOKEN`
- `CHATGPT_API_TOKEN` (alias for the CLI service token)
- `CHATGPT_SERVICE_BASE_URL`
- `CHATGPT_API_BASE_URL` (alias for the CLI service base URL)
- `CHATGPT_SERVICE_TIMEOUT_SECONDS`
- `CHATGPT_UVICORN_APP`
- `CHATGPT_UVICORN_RELOAD` (enable Uvicorn auto-reload for `docker compose ... up --watch`)
- `PORT`

## Notes

This remains browser automation, so the weak points are unchanged:
- DOM selector drift on chatgpt.com
- Cloudflare or browser challenges
- session expiration
- manual re-login in headed mode when the persistent profile loses auth state
- server-side rate limiting when runs are too aggressive

The added Docker service does not remove those risks. It packages the currently working flow behind a cleaner boundary so other projects can consume it without embedding the browser automation directly.


## Stateful CLI usage

The CLI now keeps lightweight per-profile state inside the resolved browser profile directory, typically the nearest inherited `.pb_profile/.promptbranch_state.json`, so it can behave more like `git`:

- profile discovery walks upward from the current working directory and uses the nearest `.pb_profile`
- a deeper `.pb_profile` overrides a parent one for that subtree
- if no `.pb_profile` exists, the CLI defaults to creating one in the current working directory

- `promptbranch state` shows the remembered current project and conversation
- `promptbranch prompt` emits a compact one-line value for shell prompts or menu-bar widgets
- `promptbranch state-clear` clears the remembered state
- `promptbranch use <project-name|project-url|conversation-url>` selects the current project/chat state
- `promptbranch completion <bash|zsh|fish>` emits shell completion scripts

Typical flow:

```bash
promptbranch project-ensure "My Project"
promptbranch ask --json "hello"
promptbranch prompt
promptbranch state
promptbranch use "My Project"
promptbranch completion bash
```

If no `--project-url` is supplied for project-scoped commands, the CLI reuses the remembered current project when available.

## Python packaging

The preferred Python import surface is now the `promptbranch` package:

```python
from promptbranch import ChatGPTServiceClient, ConversationStateStore
```

The console entry points are installed as:

```bash
promptbranch
chatgpt
```


## List all visible projects

```bash
promptbranch project-list
promptbranch project-list --current
promptbranch project-list --json
```

Select the current project interactively from visible projects:

```bash
promptbranch use --pick
promptbranch use work --pick
```

## Promptbranch shell aliases and status line

This release includes optional shell helpers:

```bash
scripts/setup-promptbranch-shell.sh --bash
# or
scripts/setup-promptbranch-shell.sh --zsh
```

Useful aliases:

| Alias | Command |
|---|---|
| `pbs` | `promptbranch state` |
| `pbv` | `promptbranch version` |
| `pba` | `promptbranch ask` |
| `pbsl` | `promptbranch src list` |
| `pbsa` | `promptbranch src add` |
| `pbsf` | `promptbranch src add --type file --file` |
| `pbsr` | `promptbranch src rm` |

`pbsa my_gitlab_0.0.4.zip` is now equivalent to `promptbranch src add --file my_gitlab_0.0.4.zip`.
| `pbstatus` | compact `.pb_profile` state line |

For a tmux footer/status segment:

```tmux
set -g status-right '#(/path/to/chatgpt_claudecode_workflow/scripts/promptbranch-statusline.sh --tmux) %H:%M %Y-%m-%d'
```

The status helper resolves the nearest inherited `.pb_profile` directory.


### Ollama read-only proposal mode

`pb agent ollama-propose` asks a local Ollama model to propose one read-only MCP tool call and validates the proposal without executing it. The default tool-use model is `llama3-groq-tool-use:8b`. Model-facing aliases are mapped back to Promptbranch MCP tools:

| Model alias | MCP tool |
|---|---|
| `read_file` | `filesystem.read` |
| `git_status` | `git.status` |
| `git_diff_summary` | `git.diff.summary` |

```bash
pb agent ollama-propose "read VERSION" --path . --json
pb agent mcp-llm-smoke "read VERSION" --path . --json
```

Promptbranch classifies the original request before accepting any model proposal. Write/destructive requests such as `delete VERSION` are rejected before MCP execution, even if the model proposes a read-only tool.

### Ollama-to-MCP diagnostic smoke

`pb agent mcp-llm-smoke` is a diagnostic bridge for local-agent work. It asks Ollama to propose one read-only MCP tool call, validates that proposal, then executes it through the real `pb mcp serve` stdio boundary.

```bash
pb agent mcp-llm-smoke "read VERSION" --path . --model llama3-groq-tool-use:8b --json
```

This command is intentionally not autonomous. The model proposes; Promptbranch validates; only read-only tools may execute.


## v0.0.164

- Made JSON-mode CLI output clean for machine consumers: when `--json` is requested and `--debug` is not explicitly set, debug logging is suppressed before command execution.
- Changed normal CLI logging setup to avoid DEBUG/INFO noise unless debugging is explicitly enabled.
- Added regression coverage that `pb test status --json` stdout parses directly as JSON even when `CHATGPT_DEBUG=1` is present in the environment.
- No safety policy changed; source sync, artifact release, broad shell execution, and model execution authority remain blocked.

## v0.0.157

- Added aggregate rate-limit telemetry to browser/full test-suite JSON output.
- `pb test full --json` now reports `rate_limit_telemetry` fields such as `rate_limit_modal_detected`, `conversation_history_429_seen`, `cooldown_wait_seconds_total`, `cooldown_wait_count`, and `service_rate_limit_events`.
- Per-browser-operation results now include `rate_limit_telemetry` when the automation client observes a ChatGPT conversation-history 429, rate-limit modal, or persisted cooldown wait.
- Planned post-ask pacing is reported separately as `planned_cooldown_wait_seconds_total` / `planned_cooldown_wait_count`, so conservative pacing is distinguishable from actual ChatGPT throttling.
- No new write/source/artifact/model execution authority was added.

## v0.0.155

- Added `pb test-suite --profile agent --json` for local MCP/agent/skill/controlled-process/package hygiene validation without requiring ChatGPT/browser automation.
- Added `pb test-suite --profile full --json`, which runs the existing browser/project/source/task integration suite and then the new local agent profile.
- Added package hygiene checks for release ZIPs: no `.pytest_cache`, no `__pycache__`, no `.pyc`/`.pyo`, no wrapper-folder ZIP layout, and valid ZIP CRC.
- Preserved the existing default behavior: `pb test-suite --json` still runs the browser integration profile unless a profile is explicitly selected.
- Kept source sync, artifact release, arbitrary shell/process execution, and write-capable MCP execution blocked.

## v0.0.152

- Added `pb agent summarize-log <log-file> --json` for repo-bounded, read-only Ollama log summarization.
- Kept Ollama as summary/proposal support only: it does not plan writes, execute tools, update state, or bypass policy.
- Fixed `pb agent ... --json` output so agent JSON payloads are emitted once instead of duplicated.

## v0.0.151

- Hardened `mcp_host_smoke`: it no longer falls back to `filesystem.read` on `.` when `VERSION`/`README.md` is missing. It now fails with `read_target_missing` and path diagnostics instead of trying to read a directory.
- Added git-root-aware skill path resolution so `pb skill validate .promptbranch/skills/repo-inspection --path <subdir>` can still resolve repo-relative skill paths.
- Added artifact packaging regression coverage for `.pytest_cache/`, `__pycache__/`, and `*.pyc` exclusions.

## v0.0.150

- Renamed the public MCP controlled mode from controlled writes to controlled processes: use `--include-controlled-processes`.
- Kept `--include-controlled-writes` as a deprecated compatibility alias that maps to controlled processes only.
- Limited the controlled MCP surface to the bounded `test.smoke` process tool; source sync and artifact release write tools remain blocked and are not exposed by the controlled-process manifest.
- Fixed controlled process timeout diagnostics so tool timeout and MCP transport timeout are reported separately.

## v0.0.147

- Fixed `pb agent mcp-llm-smoke ...` CLI parsing: its `--command` option no longer overwrites the root command parser destination.
- Treat `project_endpoint` task rows as indexed task-list visibility in the live integration suite.
- Preserved v0.0.146 Ollama tool-proposal guardrails: original request risk is checked before model proposals execute.



## v0.0.149

- Added `pb agent run` as the canonical Promptbranch-native local host/client command. It executes read-only plans through the actual `pb mcp serve` stdio boundary.
- Added `pb agent host-smoke` and `pb agent mcp-call` aliases for host/client verification and direct MCP stdio tool calls.
- Added local skill registry commands: `pb skill list`, `pb skill show`, and `pb skill validate`.
- Added built-in/local `repo-inspection` skill with read-only `filesystem.read`, `git.status`, and `git.diff.summary` tools.
- Kept write, destructive, source-sync, and artifact-release execution blocked from the agent path.

## v0.0.149 controlled smoke process tool

`pb agent run "run smoke tests" --path . --json` executes the bounded `test.smoke` tool through the MCP stdio path. The tool uses a fixed Promptbranch smoke command, captures stdout/stderr/exit code, enforces a timeout, and does not allow arbitrary shell commands.

Direct calls:

```bash
pb agent mcp-call test.smoke '{"timeout_seconds":60}' --path . --json
pb agent tool-call test.smoke '{"timeout_seconds":60}' --path . --json
```


## v0.0.197

- Added guarded release-control adoption automation: `--adopt-current` verifies the local ZIP, confirms exactly one matching Project Source, runs `pb artifact adopt`, and verifies `pb artifact current` alignment.
- Added `--tests-only --adopt-if-green` so full test/report can adopt the selected ZIP only when the report is `ok:true`, `status:verified`, and `failure_count:0`.
- Kept plain `--tests-only` validation-only; it does not mutate artifact/source baseline state unless `--adopt-if-green` is explicitly supplied.

## v0.0.195

- Added `chatgpt_claudecode_workflow_release_control.sh --tests-only` as a validation-only mode.
- `--tests-only` runs only the logged `pb test full` plus `pb test report` block and skips release import/compare, commit, packaging, Project Source add, install, service startup, chown, and docker log capture.
- Added `--run-tests-only` as an alias for the same test-only behavior.

## v0.0.194

- Updated `chatgpt_claudecode_workflow_release_control.sh --run-tests` to wrap the full-test/report block with `startlog`/`stoplog` when those commands are available.
- Added an internal tee-based session-log fallback so release-control test logging still works in non-interactive script contexts where shell functions are unavailable.
- The test block now records the full suite log, report JSON, and session log path in the final release-control summary.

## v0.0.193

- Hardened release/package hygiene for task transcript exports using the `task_*.messages.txt` pattern.
- Removed generated task transcript exports from the release artifact surface.
- Kept the change narrow: no Project Source upload, removal, overwrite, or release behavior changed.

## v0.0.191

- Added `pb artifact adopt <zip> --from-project-source --json` to adopt an already-present Project Source ZIP as the current local artifact/source baseline.
- Adoption verifies the ZIP exists exactly once in Project Sources and verifies the matching local ZIP before updating the local artifact registry and Promptbranch state.
- Adoption does not upload, remove, overwrite, or mutate Project Sources; it updates local registry/state only after verification.

## v0.0.190

- Hardened artifact/release hygiene after v0.0.189 exposed that task transcript exports such as `task_*_message.txt` could be included in a release ZIP.
- Added default excludes and verification checks for task/session transcript exports, stdout/stderr capture files, nested archives, log derivatives, and Python/cache artifacts.
- Extended `pb test full` package hygiene so generated transcript files fail validation instead of silently passing.

## v0.0.189

- Added `pb artifact release --print-confirm-command` with `--confirm-command-only` as an alias. It prints only the top-level artifact-release confirmation command, making shell command substitution possible without `jq`.
- Kept nested `source_sync` confirmation diagnostics redacted so operators continue to run the artifact-release wrapper, not delegated `pb src sync` commands.
- Added regression coverage for command-only preflight output, including the local-collision `--force` case.

## v0.0.188

- Hardened the canonical `pb artifact release --sync-source --upload` confirmation UX: only top-level `confirmation.confirm_command` is executable.
- Redacted nested delegated `source_sync.confirmation.confirm_command` diagnostics to prevent operators from running `pb src sync` instead of the artifact-release wrapper.
- Propagated `--force` into the top-level artifact-release confirmation command when local artifact collisions require explicit overwrite confirmation.
- Preserved release-level status mapping for delegated source-sync results: `uploaded`, `upload_ambiguous`, and `failed` remain explicit.
- Excluded `.promptbranch-service-start.*.pid` from source/release snapshots and `.not_to_zip`.
- Made `chatgpt_claudecode_workflow_release_control.sh` skip full tests by default; use `--run-tests` to opt in.

## v0.0.184

- Fixed the live overwrite-regression timing edge where the Sources surface was restored but a stale dialog locator could still appear visible.
- Kept the early-refresh safety rule intact by accepting only a guarded soft-close condition with visible Add button, stable URL, non-empty source cards, and no empty state.
- Preserved duplicate file-source overwrite coverage in the full browser suite.

## v0.0.178

- Fixed release version consistency after the v0.0.177 upload test: `VERSION`, `pyproject.toml`, `promptbranch_version.PACKAGE_VERSION`, CLI/runtime, MCP server, service image tag, and tests now agree on `v0.0.178`.
- No source-sync behavior changes were added; this is a narrow metadata/release-correctness patch.
- Removed generated task transcript material from the release ZIP and preserved cache/log/temporary-file hygiene.


## v0.0.176

- Added explicit `upload_ambiguous` classification for confirmed project-source uploads where the service/API result fails but source-list verification finds the expected uploaded ZIP afterward with no collateral source removal.
- Ambiguous upload outcomes require operator review and do not advance the local artifact registry or Promptbranch source/artifact state.
- Preserved transactional source-sync behavior: local ZIP creation may occur, but source/artifact state advances only after verified project-source upload.


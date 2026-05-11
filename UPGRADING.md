# UPGRADING

This file documents the breaking rename that landed in **v0.0.68** and remains the reference for later releases such as **v0.0.69**.

## Summary

`promptbranch` is now the only supported public CLI and Python package surface.
The legacy `chatgpt_*` aliases were removed from the packaged artifact in v0.0.68.

What changed:
- CLI command: `chatgpt` -> `promptbranch`
- Python package: `chatgpt_workflow` -> `promptbranch`
- Internal modules/files: `chatgpt_*` -> `promptbranch_*`
- Internal packages: `chatgpt_automation` / `chatgpt_browser_auth` -> `promptbranch_automation` / `promptbranch_browser_auth`

Migration support that remains:
- config fallback: `~/.config/chatgpt-cli/config.json` is still read if the new config path is absent



## Public command and package replacements

| Old | New |
|---|---|
| `chatgpt` | `promptbranch` |
| `from chatgpt_workflow import ChatGPTServiceClient` | `from promptbranch import ChatGPTServiceClient` |
| `from chatgpt_workflow import ConversationStateStore` | `from promptbranch import ConversationStateStore` |
| `chatgpt completion bash` | `promptbranch completion bash` |
| `chatgpt use <project>` | `promptbranch use <project>` |
| `chatgpt state` | `promptbranch state` |
| `chatgpt prompt` | `promptbranch prompt` |
| `chatgpt state-clear` | `promptbranch state-clear` |

## Top-level module/file replacements

| Old file/module | New file/module |
|---|---|
| `chatgpt_cli.py` | `promptbranch_cli.py` |
| `chatgpt_container_api.py` | `promptbranch_container_api.py` |
| `chatgpt_service_client.py` | `promptbranch_service_client.py` |
| `chatgpt_state.py` | `promptbranch_state.py` |
| `chatgpt_full_integration_test.py` | `promptbranch_full_integration_test.py` |
| `chatgpt_login_test.py` | `promptbranch_login_test.py` |
| `chatgpt_cli_sequence_v5.py` | `promptbranch_cli_sequence_v5.py` |

## Package replacements

| Old package | New package |
|---|---|
| `chatgpt_workflow` | `promptbranch` |
| `chatgpt_automation` | `promptbranch_automation` |
| `chatgpt_browser_auth` | `promptbranch_browser_auth` |

## Config and state path changes

| Purpose | Old path | New path |
|---|---|---|
| CLI config | `~/.config/chatgpt-cli/config.json` | `~/.config/promptbranch/config.json` |
| CLI state | profile-local `.chatgpt_cli_state.json` | profile-local `.promptbranch_state.json` |
| Browser profile dir | visible `profile/` by convention | hidden inherited `.pb_profile/` by default |

The CLI discovers the nearest `.pb_profile` by walking up from the current working directory, and a deeper `.pb_profile` overrides a parent one for that subtree.

## Docker and service naming

| Old | New |
|---|---|
| image `chatgpt-docker-service:*` | image `promptbranch-service:*` |
| app module `chatgpt_container_api:app` | app module `promptbranch_container_api:app` |

## Example updates

| Old | New |
|---|---|
| `examples/chatgpt_service_client_example.py` | `examples/promptbranch_service_client_example.py` |

## Minimal migration steps

### CLI users

```bash
pip uninstall -y chatgpt-claudecode-workflow || true
pipx uninstall chatgpt-claudecode-workflow || true
pipx install ./chatgpt_claudecode_workflow_v0.0.127.zip
promptbranch state
promptbranch prompt
```

### Python callers

Replace imports:

```python
from chatgpt_workflow import ChatGPTServiceClient, ConversationStateStore
```

with:

```python
from promptbranch import ChatGPTServiceClient, ConversationStateStore
```

### Service operators

Update:
- image tags from `chatgpt-docker-service:*` to `promptbranch-service:*`
- app module from `chatgpt_container_api:app` to `promptbranch_container_api:app`
- any scripts that still invoke `chatgpt_*` file names

## Breaking changes to expect

These names are no longer packaged in v0.0.68+:
- `chatgpt` CLI command
- `chatgpt_workflow` package
- `chatgpt_automation` package
- `chatgpt_browser_auth` package
- top-level `chatgpt_*` modules listed above

If you still depend on them, pin to `v0.0.67` temporarily and migrate before adopting `v0.0.68+`.

## v0.0.146.1

- Added deterministic original-request risk classification before any Ollama-proposed MCP tool call can execute.
- `pb agent ollama-propose` asks Ollama to propose one read-only tool call, validates model-facing aliases, and never executes the result.
- `pb agent mcp-llm-smoke` now defaults to `llama3-groq-tool-use:8b`, uses model-facing aliases such as `read_file`, and rejects write/destructive requests before calling Ollama.
- Native Ollama `/api/chat` tool-calling is preferred; JSON-schema generation is only a fallback for requests already classified as read-only.
- Destructive prompts such as `delete VERSION` now return `risk_rejected` instead of allowing a model to reframe them into a benign read.


## v0.0.146.2

- Added chat-message attachments for `pb ask` without adding those files to Project Sources. Use repeatable `--attach` / `--attachment` flags for logs and other one-off context files.
- Kept legacy `--file` as a single chat attachment for compatibility.
- Added `--prompt-file` so the prompt body can be read from a UTF-8 file and optionally combined with a short inline instruction.
- Extended the Docker service `/v1/ask` multipart endpoint to accept multiple `attachments` uploads while preserving uploaded basenames in temporary files.

## v0.0.145

- Hardened `pb ask` response completion detection so an interim assistant progress/thought message is not treated as the final answer.
- Completion now requires the answer content to be stable, no stop/thinking indicator to be visible, and the composer to be idle again.
- This specifically prevents the browser session from closing when ChatGPT emits a short first assistant thought/update while the final response is still pending.

## v0.0.143

- `pb mcp config` now resolves the MCP executable to an absolute path by default when possible, avoiding GUI-host PATH/alias failures.
- Added `pb mcp host-smoke` to launch the generated host config and verify read-only calls through the configured stdio server.
- Added `mcp_host_smoke` as an optional local-only test-suite selector: `pb test-suite --only mcp_host_smoke --json`.
- Updated MCP help/how-to docs with absolute-path config and host-smoke workflow.
- Preserved read-only MCP server semantics; controlled process mode exposes only bounded process tools; source/artifact writes remain blocked from `pb mcp serve`.

## v0.0.140

- Added `pb mcp config` to emit a standard `mcpServers` host configuration snippet for `pb mcp serve`.
- Added `mcp_smoke` to the test-suite selectors, available via `pb test-suite --only mcp_smoke --json` or `pb test smoke --only mcp_smoke --json`.
- Added `docs/howto/14-use-mcp-local-agent.md` with MCP host config, stdio smoke, and safety-boundary guidance.
- Preserved read-only MCP server semantics; controlled process mode exposes only bounded process tools; source/artifact writes remain blocked from `pb mcp serve`.

## v0.0.139

- Added `pb mcp serve` as a minimal read-only MCP stdio JSON-RPC server.
- The server exposes read-only repo/git/state/artifact tools from the existing MCP manifest.
- Controlled write tools can be listed for planning, but `pb mcp serve` rejects their execution until a deterministic executor is implemented.

## v0.0.138

- Added the first read-only MCP/Ollama planning scaffold: `pb agent inspect`, `pb agent doctor`, and `pb agent plan`.
- Added `pb mcp manifest` to emit the default read-only MCP tool surface and optional gated write/process tool specs.
- The local agent layer is deterministic and read-only by default; it classifies requests and proposes commands but does not execute writes or destructive actions.

## v0.0.137

- `pb src add <file>` / `pbsa <file>` now overwrites an existing file source with the same display name by default: the old source is removed, the new file is uploaded, and persistence is verified.
- Added `--no-overwrite` for source-add commands to retain the previous duplicate-skip behavior.

## v0.0.136

- Recomputed task-list visibility diagnostics in the CLI after merging backend rows; stale service fields such as `visibility_status=missing` and old observation counts are no longer preserved when project endpoint rows are present.

## v0.0.135

- Fixed the project-specific conversations endpoint probe by clamping `limit` to 50. Live v0.0.134 diagnostics showed ChatGPT returns HTTP 422 when `/backend-api/gizmos/<project-id>/conversations` is called with `limit=100`.
- Preserved task-list cache behavior and the v0.0.134 source-add positional shorthand.
- Added/updated focused parser and endpoint-limit regression coverage.

## v0.0.134

- Made `promptbranch src add <file>` equivalent to `promptbranch src add --file <file>`, so the `pbsa` alias can be used as `pbsa my_gitlab_0.0.4.zip`.
- Kept the existing `--file` form for compatibility and added validation to reject conflicting positional and `--file` paths.
- Applied the same positional file shorthand to legacy `project-source-add <file>`.

## v0.0.133

- Added a fresh per-project task-list cache in `.pb_profile` after `pb task list`, so a follow-up `pb task use <index>` can resolve from the just-shown list without opening a browser/service request again.
- Hardened project-conversation payload extraction for nested backend shapes such as `data.gizmo.conversations.edges[].node`, which may allow the project-specific endpoint to expose tasks beyond the 20-row `snorlax` cap when ChatGPT returns a wrapped payload.
- Preserved the cached task list across normal state updates such as `pb task use`.

## v0.0.131

- Fixed the v0.0.130 project-conversations probe by removing the synthetic first-page `cursor=0`, which live logs showed returned HTTP 422.
- Made lightweight task enumeration skip persisted conversation-history cooldown waits; `pb task use <index>` should no longer wait behind 429 cooldowns from a previous deep history scan.
- Made lightweight task enumeration skip DOM scrolling when backend indexed rows already exist, reducing `pb task use <index>` latency.
- Changed `pb task list` / `pb chat-list` to avoid the expensive global conversation-history supplement by default; use `--deep-history` only for explicit diagnostics.
- Added non-200 body previews for the project-conversations endpoint so the next live run exposes the exact backend validation error if the endpoint still rejects requests.

## v0.0.130

- Added a project-specific task enumeration backend probe (`/backend-api/gizmos/<project>/conversations`) before DOM/history fallbacks, with `source_counts.project_endpoint` diagnostics.
- Skipped the global conversation-history supplement when the project-specific endpoint returns task rows, avoiding known 429-prone detail probing in the normal task-list path.
- Made `pb task use <index>` resolve against a lightweight indexed task list first, avoiding the expensive conversation-history supplement when the selected task is already indexed.
- Added tests for project-endpoint pagination and lightweight `task use` resolution.

## v0.0.129

- Fixed the misleading `indexed_task_count` diagnostic so it reports unique indexed tasks after source merging instead of summing duplicate snorlax/DOM/history observations.
- Added `indexed_observation_count` for the old raw source-observation total when duplicate-source diagnostics are useful.
- Preserved `visibility_status=indexed` when at least one unique backend/DOM/history task is present, while keeping recent-state-only rows out of the indexed task count.

## v0.0.128

- Fixed project task enumeration using ChatGPT `snorlax/sidebar` by respecting the current `conversations_per_gizmo <= 20` backend limit.
- `pb task list` should no longer force snorlax into HTTP 422 before falling back to DOM/history.
- Kept DOM/history/detail fallbacks, but backend project-scoped snorlax data is again the preferred task-list source.


## v0.0.127

- Added `pb debug chats` / `pb debug task-list` to produce machine-readable diagnostics for project task enumeration undercounts.
- The debug run writes a timestamped artifact directory containing DOM snapshots, screenshots, HTML, scroll-container diagnostics, project-chat anchor ids, snorlax/sidebar observations, conversation-history/detail observations, and `summary.json`.
- Use this before another task-list enumeration patch when `pb task list` stops at the first visible/project-chat batch.

## v0.0.125

- Fixed another `pb task list` undercount case where ChatGPT's project Chats tab exposed only the first DOM batch and `/backend-api/conversations` no longer included project ids in the list payload.
- Conversation-history supplement now probes conversation detail payloads for unmatched history rows and classifies project tasks from richer backend metadata before falling back to DOM-only results.
- `pb task list --json` now reports `source_counts.history_detail` when deeper tasks are recovered from conversation-detail classification.

## v0.0.122

- Fixed `pb task list` returning only the first visible/project-chat batch when additional tasks exist below the project chat scroll fold.
- Project chat enumeration now continues snorlax/sidebar pagination after finding the target project when a fresh cursor is available.
- DOM fallback task enumeration now uses more scroll rounds plus wheel/PageDown events so virtualized project chat rows can materialize before the command returns.

## v0.0.120

- Fixed `scripts/promptbranch-statusline.sh` so compact one-line `.promptbranch_state.json` files are parsed correctly.
- Preserved legacy flat state keys such as `project_name`, `project_url`, `conversation_url`, and `conversation_id` while also supporting normalized workspace/task state sections.
- Kept the strict task-index visibility semantics introduced in v0.0.119.

## v0.0.119

- Tightened `task_message_flow.task_list_visible`: local `recent_state` recovery no longer counts as indexed task-list visibility by default.
- `pb task list --json` now reports `visibility_status`, `indexed_task_count`, and `recent_state_count` so degraded recent-state-only results are explicit.
- Added `--allow-recent-state-task-fallback` to `pb test smoke` and `pb test-suite` for temporary degraded-mode smoke runs.
- Updated Phase 3 help/docs/howtos and shell aliases for `pb src sync` and `pb artifact ...`.

## v0.0.118

- Added Phase 3 artifact lifecycle primitives: `pb artifact current`, `pb artifact list`, `pb artifact release`, and `pb artifact verify`.
- Added `pb src sync <path>` to create a repo snapshot ZIP and optionally upload it as a source for the current workspace.
- Local artifact registry is stored under `.pb_profile/promptbranch_artifacts.json`; generated ZIPs default to `.pb_profile/artifacts/`.
- Repo snapshot naming uses `VERSION` when it contains a valid version-like value, otherwise falls back to the current Git short SHA.
- ZIP verification checks for corrupt entries, unsafe paths, and unwanted wrapper-folder layout.

## v0.0.117

- `pb task list` and live `task_message_flow` now include a bounded `recent_state` fallback for tasks just created by `ask` when ChatGPT's sidebar/history indexes lag or omit the new conversation.
- `promptbranch_automation.service.ChatGPTAutomationService` remembers recently-created task conversation URLs per project and merges them into chat-list results without duplicating backend-listed rows.
- `promptbranch_container_api` now caches per-project service instances so service-mode `/v1/ask` followed by `/v1/chats` can preserve recent task state for the same project.
- Task-list source counts may now include `source_counts.recent_state`.

## v0.0.116

- Removed invalid Python string escape warnings from JavaScript debug-snapshot snippets in `promptbranch_browser_auth/client.py`.
- Converted the affected `page.evaluate(...)` snippets to raw triple-quoted strings.
- No behavior or command grammar changes in this release.

## v0.0.115

- `pb task list` now includes the currently-open project conversation as a verified current-page fallback when ChatGPT's sidebar/history task indexes lag after `ask`.
- `task_message_flow.task_list_visible` can pass from the direct current conversation instead of failing solely because backend task indexes are eventually consistent.
- Task-list results now report `source_counts.current_page` so live-suite logs show when this fallback was used.
- No command grammar expansion in this release.

## v0.0.114

- Hardened project task/chat enumeration when ChatGPT backend payloads return the full project slug (`g-p-...-name`) instead of the bare project id (`g-p-...`).
- `task_message_flow` visibility checks should now recognize newly-created tasks from snorlax/sidebar and conversation-history payloads instead of dropping them during project-id filtering.
- No command grammar expansion in this release.

## v0.0.113

- `pb test-suite` now treats task-list visibility as required in `task_message_flow`; a green run can no longer hide `task_list_count: 0`.
- Added bounded, low-rate polling for a newly-created task to appear in `pb task list` after `ask`.
- Added task-list visibility controls: `--task-list-visible-timeout-seconds`, `--task-list-visible-poll-min-seconds`, `--task-list-visible-poll-max-seconds`, and `--task-list-visible-max-attempts`.
- Added lightweight task-list probes that avoid the expensive conversation-history fallback until the final visibility attempt.
- `GET /v1/chats` and the service client now support `include_history_fallback`.

## v0.0.112

- Added `scripts/promptbranch-aliases.sh` with common Promptbranch aliases such as `pbs` for `promptbranch state`.
- Added `scripts/setup-promptbranch-shell.sh` to install the aliases into Bash or Zsh rc files.
- Added `scripts/promptbranch-statusline.sh` for compact Promptbranch state output in shell prompts or tmux footer/status lines.
- The status helper resolves the nearest inherited `.pb_profile` directory.

## v0.0.143

- Added deterministic read-only local agent execution:
  - `pb agent ask "read VERSION and git status" --path . --json`
  - `pb agent tool-call filesystem.read '{"path":"VERSION"}' --path . --json`
  - `pb agent models --json`
- `pb agent ask` uses a rule-based planner for read-only MCP tools. Ollama is not trusted for tool planning.
- Ollama can be used only for optional summaries with `--model` or `--summarize`; failures are non-fatal.
- Write-capable MCP tools remain blocked.

## v0.0.143

- Added `pb agent mcp-llm-smoke` as a diagnostic path where Ollama proposes exactly one read-only MCP tool call.
- Promptbranch validates the model output against the read-only MCP tool allowlist before calling `pb mcp serve` over stdio.
- The local model has no execution authority; invalid JSON, unknown tools, and write-tool proposals fail the smoke test instead of falling back silently.

Example:

```bash
pb agent mcp-llm-smoke "read VERSION" --path . --model llama3-groq-tool-use:8b --json
```

## v0.0.147

- Fixed `pb agent mcp-llm-smoke ...` CLI parsing: its `--command` option no longer overwrites the root command parser destination.
- Treat `project_endpoint` task rows as indexed task-list visibility in the live integration suite.
- Preserved v0.0.146 Ollama tool-proposal guardrails: original request risk is checked before model proposals execute.





## v0.0.203

- Added explicit `pb artifact intake --from-last-answer --download` for MVP-F2.
- Downloads the selected reply artifact candidate into `.pb_profile/artifact_inbox/` and records filename, size, SHA-256, answer/request metadata, and `intake.json`.
- Does not verify ZIP contents, migrate the candidate to repo root, adopt artifacts, mutate Project Sources, or advance artifact/source state.
- Keeps candidate extraction available without `--download`; download requires a selected candidate with a concrete `download.url`.

## v0.0.202

- Added MVP-F1 artifact-candidate intake: `pb artifact intake --from-last-answer --json` parses the latest Promptbranch reply envelope and classifies ZIP candidates.
- Added expected artifact/version/repo checks with explicit statuses for missing, ambiguous, wrong filename, wrong version, and wrong project candidates.
- Kept intake read-only: no ZIP download, no migration, no adoption, no Project Source mutation.

## v0.0.200

- Added explicit release-control log pruning with `--prune-release-logs`.
- Added `--release-log-keep N` / `PROMPTBRANCH_RELEASE_LOG_KEEP` to retain a bounded number of version log directories when pruning.
- Pruning is opt-in; default behavior preserves all `.pb_profile/release_logs/<version>/` diagnostics.
- The current release log directory is always retained during pruning.

## v0.0.199

- Moved release-control generated logs and JSON audit artifacts under `.pb_profile/release_logs/<version>/` instead of writing them into the repository root.
- Added `--release-log-dir DIR` to override the release-control log root when needed.
- Made the final release-control summary conditional: skipped test/service/docker-log stages now print `skipped` instead of computed paths.
- Kept `--tests-only` and `--adopt-current` free of service startup and Docker log capture side effects.

## v0.0.198.2

- Repair release for `v0.0.198.1`; no slice or line advanced.
- Fixed release-control packaging normalization when a legacy packager falls back to `chatgpt_claudecode_workflow-<git-sha>.zip` for numeric repair versions.
- Added regression coverage proving `v0.0.198.2` repair-version packaging is renamed to the canonical `chatgpt_claudecode_workflow_v0.0.198.2.zip` before verification.

## v0.0.198.1

- Repair release for `v0.0.198`; no slice or line advanced.
- Hardened `chatgpt_claudecode_workflow_release_control.sh` after a reported Bash parse failure near inline Python in the Project Source verification path.
- Reworked the source-list verification and local service health-probe inline Python to use `python3 -c`, reducing heredoc parsing sensitivity.
- Updated release-control version normalization to accept numeric repair versions such as `v0.0.198.1`.

## v0.0.198

- Made release-control Docker log capture best-effort: missing/stale containers now emit a warning and do not make the final operator output look like a failed release.
- Clarified guarded adoption flags: `--adopt-if-green` is now supported only with `--tests-only`. Use `--run-tests` for the full release workflow, then `--adopt-current` as a separate explicit step.
- Added regression coverage for stale Docker container IDs and for rejecting `--run-tests --adopt-if-green`.

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

- Added `pb artifact adopt <zip> --from-project-source --json`.
- Use this when a release ZIP was already added manually to Project Sources, but local `pb state` / `pb artifact current` still point at an older baseline.
- The command verifies Project Source presence and the local ZIP before advancing the artifact registry and source/artifact state.
- It does not upload, remove, overwrite, or otherwise mutate Project Sources.

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

## v0.0.176

- Added explicit `upload_ambiguous` classification for confirmed project-source uploads where the service/API result fails but source-list verification finds the expected uploaded ZIP afterward with no collateral source removal.
- Ambiguous upload outcomes require operator review and do not advance the local artifact registry or Promptbranch source/artifact state.
- Preserved transactional source-sync behavior: local ZIP creation may occur, but source/artifact state advances only after verified project-source upload.

## v0.0.175

- Confirmed `pb src sync --upload --confirm-upload` now converts project-source service errors into structured `upload_failed` JSON instead of crashing with a traceback.
- Failed live uploads still defer artifact registry and Promptbranch source-state updates until upload/source-list verification succeeds.
- Updated release version references including the Docker Compose service image tag.

## v0.0.162

- Made JSON-mode CLI output clean for machine consumers: when `--json` is requested and `--debug` is not explicitly set, debug logging is suppressed before command execution.
- Changed normal CLI logging setup to avoid DEBUG/INFO noise unless debugging is explicitly enabled.
- Added regression coverage that `pb test status --json` stdout parses directly as JSON even when `CHATGPT_DEBUG=1` is present in the environment.
- No safety policy changed; source sync, artifact release, broad shell execution, and model execution authority remain blocked.

## v0.0.157

- Browser/full test-suite JSON now includes `rate_limit_telemetry` so operators can tell whether ChatGPT conversation-history throttling actually occurred.
- Telemetry fields include `rate_limit_modal_detected`, `conversation_history_429_seen`, `cooldown_wait_seconds_total`, `cooldown_wait_count`, `planned_cooldown_wait_seconds_total`, `planned_cooldown_wait_count`, and `service_rate_limit_events`.
- Per-browser-operation payloads also carry `rate_limit_telemetry` when the automation layer observes a modal, 429 response, or persisted cooldown wait.
- Conservative pacing remains the default for `pb test full --json`; v0.0.157 improves observability rather than changing the safety policy.

## v0.0.155

- Use `pb test full --json` as the canonical shortcut for the full validation profile.
- Use `pb test agent --json` for local MCP/agent/skill/package checks.
- Use `pb test browser --json` for the browser/project/source/task integration profile.
- Existing `pb test-suite --profile ... --json` commands remain supported.

## v0.0.154

- Use `pb test-suite --profile full --json` when you want one command to run both the live browser/project/source/task integration suite and the local MCP/agent/skill/package checks.
- Use `pb test-suite --profile agent --json` for a faster local validation path that does not require ChatGPT/browser access.
- The default `pb test-suite --json` behavior remains the browser integration suite for compatibility.

## v0.0.153

- `pb agent summarize-log` now returns a deterministic local fallback summary when Ollama times out or is unavailable.
- The fallback is read-only and repo-bounded; it reports headings, marker lines, and simple pass/fail/error counters.
- No source/artifact write execution, broad shell execution, or model-driven tool execution was added.

## v0.0.152

- Added `pb agent summarize-log <log-file> --json` as a read-only local log summarization helper.
- Agent JSON command output is now emitted once.
- No source/artifact write execution was added.

## v0.0.151

- Hardened `mcp_host_smoke`: it no longer falls back to `filesystem.read` on `.` when `VERSION`/`README.md` is missing. It now fails with `read_target_missing` and path diagnostics instead of trying to read a directory.
- Added git-root-aware skill path resolution so `pb skill validate .promptbranch/skills/repo-inspection --path <subdir>` can still resolve repo-relative skill paths.
- Added artifact packaging regression coverage for `.pytest_cache/`, `__pycache__/`, and `*.pyc` exclusions.

## v0.0.150

- Public MCP controlled mode is now named controlled processes. Use `--include-controlled-processes`.
- Deprecated `--include-controlled-writes` remains as an alias but no longer implies source/artifact write tool exposure.
- The controlled-process manifest exposes `test.smoke` only; source sync and artifact release write tools remain blocked.
- Timeout diagnostics now separate `tool_timeout_seconds` from `transport_timeout_seconds` for controlled MCP process calls.

## v0.0.149

- Added `pb agent run` as the canonical Promptbranch-native local host/client command. It executes read-only plans through the actual `pb mcp serve` stdio boundary.
- Added `pb agent host-smoke` and `pb agent mcp-call` aliases for host/client verification and direct MCP stdio tool calls.
- Added local skill registry commands: `pb skill list`, `pb skill show`, and `pb skill validate`.
- Added built-in/local `repo-inspection` skill with read-only `filesystem.read`, `git.status`, and `git.diff.summary` tools.
- Kept write, destructive, source-sync, and artifact-release execution blocked from the agent path.

## v0.0.149

- Added controlled `test.smoke` MCP process tool.
- `pb agent run "run smoke tests" --path . --json` now plans `test.smoke` through the Promptbranch-native MCP stdio boundary.
- `test.smoke` runs only fixed local Promptbranch smoke selectors by default (`mcp_smoke`, `mcp_host_smoke`) with hard timeout, stdout/stderr capture, exit code capture, and parsed JSON when available.
- Destructive/write/source/artifact tools remain blocked.

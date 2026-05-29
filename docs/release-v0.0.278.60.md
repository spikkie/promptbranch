# Release v0.0.278.60

Base: `chatgpt_claudecode_workflow_v0.0.278.48.zip`

Purpose: make `pb ask` safe for normal command-line use by returning structured JSON by default, preserving an explicit `--text` convenience mode, and failing closed when a response is not bound to the current submitted prompt.

Changes:

- Preserved the `.48` prompt fill and submit implementations.
- `pb ask` now emits the full structured ask result as JSON by default.
- Added `pb ask --text` to opt into the legacy answer-only output on success.
- Kept `pb ask --json` as strict assistant-JSON request mode; structured result output is already the default.
- Added `--expect-json` as an explicit alias for strict assistant-JSON request mode.
- Blocked post-submit visible JSON promotion unless submit confirmation and visible current user-turn evidence are present.
- Tightened plain-text answer waiting so same-count assistant text mutations cannot be treated as fresh answers; a plain answer must come from a post-submit assistant turn.
- Failures now return structured `ok=false` payloads by default instead of printing stale visible assistant text.

Validation performed:

- `python3 -m compileall -q .`
- Focused parser and CLI tests for ask JSON default / `--text` behavior.
- Focused browser-client tests for stale visible JSON promotion and plain response binding.
- Clean ZIP verification: root repository contents, no wrapper folder, no nested ZIPs, no cache/log/local-state hygiene violations.

No slice or line was advanced.

# Release v0.0.265

## Summary

Documentation-only release from accepted repair baseline `v0.0.264.1`. This release reconciles the MVP/design documents with the current proven Promptbranch state and adds a current step-by-step MVP plan.

## Changes

- Added `docs/promptbranch_mvp_current_state_and_plan_2026-05-24.md`.
- Updated Ask/Reply + Artifact Intake design docs to mark the real-candidate path as implemented/proven.
- Added MVP-F8 artifact transport hardening and MVP-F9 protocol transcript identity/replay to the design.
- Updated MCP/agent/skills documentation to include the current `release-readiness` read-only skill/gate.
- Updated operating-model documentation to clarify the current roles of LLM, MCP, agent, and skills.
- Replaced the native lifecycle TODO with a current-state update that focuses on lifecycle consolidation and failure classification.

## Non-goals

- No runtime behavior change.
- No browser automation change.
- No Project Source mutation.
- No new write-capable agent/MCP tools.
- No artifact adoption, Git commit, or Git push performed by the builder.

## Validation

Validated with `python3 -m compileall -q .` and focused parser/CLI/MCP tests: `python3 -m pytest -q tests/test_cli_parser.py tests/test_promptbranch_cli.py tests/test_promptbranch_mcp.py` (`285 passed`). Extracted ZIP smoke and ZIP hygiene were also performed by the builder.

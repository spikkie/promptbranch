# Repair release v0.0.226.2

## Base release

`chatgpt_claudecode_workflow_v0.0.226.1.zip`

## Repair version

`v0.0.226.2`

## Reason

`v0.0.226.1` could repeatedly fail post-adoption protocol smoke before submit with `target_conversation_not_hydrated_before_submit` on a long target conversation. The baseline state was correct, but the browser-side target conversation did not hydrate visible turns before the pre-submit safety gate timed out.

## Files changed

- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- `README.md`
- `UPGRADING.md`
- version metadata surfaces

## Validation performed

- Python compile checks for changed modules.
- Focused hydration unit tests for:
  - fail-closed non-hydrated target conversation after bounded reloads
  - successful hydration after second reload
  - already-hydrated target conversation
- ZIP hygiene verification.

## Scope confirmation

No MVP slice or line was advanced. This repair only hardens target-conversation hydration retry/diagnostics before protocol submit. It does not change ask/reply protocol schema, artifact intake, candidate-test, accept-candidate behavior, Project Source upload, source sync, or MCP policy behavior.

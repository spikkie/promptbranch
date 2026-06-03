# Release v0.1.20

Base: `chatgpt_claudecode_workflow-2_v0.1.19.zip`

## Scope

Add explicit next-candidate handoff commands to the read-only development checkpoint result.

## Changes

- Extend `pb release checkpoint --mode continue --json` with `checkpoint_decision.next_development_artifact`.
- Add `suggested_commands.next_development_status_guide_after_build`.
- Add `suggested_commands.next_development_checkpoint_after_build`.
- Keep the checkpoint fully read-only: no install, no source upload, no full test, no adoption, no registry/state mutation, no Git mutation.
- Update focused tests for the checkpoint handoff contract.
- Update the living design Markdown and editable draw.io source.
- Restore the compose-level `CHATGPT_RESPONSE_TIMEOUT_MS=1200000` default expected by the timeout-policy regression test.

## Validation

- Focused status-guide/checkpoint tests.
- Compile validation.
- Docs-status validation.
- Release config validation.
- Release install/lifecycle plan validation.
- ZIP reopen, VERSION, root-layout, and hygiene verification.

## Boundary

This release improves operator guidance only. The reported commands are for the operator to run after the next candidate is built; they are not executed by `checkpoint`.

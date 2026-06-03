# Release v0.1.21

Base: `chatgpt_claudecode_workflow-2_v0.1.20.zip`

## Scope

Add the same next-development candidate handoff to `pb release status-guide --json` that `v0.1.20` added to `pb release checkpoint --mode continue --json`.

## Changes

- Extend `pb release status-guide --json` with `command_guide.next_development_status_guide_after_build`.
- Extend `pb release status-guide --json` with `command_guide.next_development_checkpoint_after_build`.
- Extend `operator_runbook` with `next_development_version`, `next_development_artifact`, and the matching after-build status-guide/checkpoint commands.
- Keep `status-guide` fully read-only: no install, no smoke run, no full test, no adoption, no Project Source mutation, no registry/state mutation, and no Git mutation.
- Update focused status-guide tests for the next-development handoff contract.
- Update the living design Markdown and editable draw.io source.

## Validation

- Focused status-guide/checkpoint/dev-status tests.
- Version/container/compose focused tests.
- Compile validation.
- Docs-status validation.
- Release config validation.
- Release install/lifecycle plan validation.
- ZIP reopen, VERSION, root-layout, and hygiene verification.

## Boundary

This release improves read-only operator guidance only. The reported next-development commands are for the operator to run after the next candidate is built; they are not executed by `status-guide`.

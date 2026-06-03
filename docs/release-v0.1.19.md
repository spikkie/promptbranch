# Release v0.1.19

Base: `chatgpt_claudecode_workflow-2_v0.1.18.1.zip`

## Scope

Add read-only post-adoption next-normal release planning to `pb release status-guide --json`.

## Changes

- Preserve repair-baseline continuity after `v0.1.18.1` adoption.
- Extend post-adoption `status-guide` output with the next normal development candidate plan.
- Add `operator_runbook` fields for:
  - `post_adoption_ready_for_next_normal`
  - `development_base_version`
  - `next_normal_version`
  - `next_normal_artifact`
- Add command-guide entries for the next normal candidate status-guide/checkpoint commands after that candidate exists.
- Update the living design Markdown and editable draw.io source.

## Validation

- Focused status-guide/checkpoint tests.
- Docs-status validation.
- Release install/lifecycle plan validation.
- ZIP reopen, VERSION, root-layout, and hygiene verification.

## Boundary

This release is read-only workflow guidance. It does not install, upload Project Sources, full-test, adopt, commit, push, or mutate runtime state by itself.

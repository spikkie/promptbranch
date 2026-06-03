# Release v0.1.22

Base: `chatgpt_claudecode_workflow-2_v0.1.21.zip`

## Scope

Expose the next-development handoff in non-JSON operator output for the read-only release guidance commands.

## Changes

- Extend plain-text `pb release status-guide` output with:
  - `next_development_artifact`
  - `next_development_status_guide_after_build`
  - `next_development_checkpoint_after_build`
- Extend plain-text `pb release checkpoint --mode continue` output with:
  - `next_development_artifact`
  - `next_development_status_guide_after_build`
  - `next_development_checkpoint_after_build`
- Add focused regression coverage proving the non-JSON output contains the same next-candidate handoff already exposed in JSON.
- Update version metadata to `v0.1.22`.

## Non-goals

- No adoption.
- No full-test checkpoint.
- No Project Source upload.
- No artifact registry mutation.
- No Git mutation.
- No release lifecycle behavior change beyond human-readable guidance output.

## Validation

- `python3 -m compileall -q .`
- focused release status-guide/checkpoint tests
- focused version/container/compose/docs/config/install/lifecycle tests
- ZIP hygiene/root-layout verification

## Operator note

This release is still focused-development only. The accepted baseline may remain behind the installed runtime until the next full-test/adoption checkpoint.

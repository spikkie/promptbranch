# Release v0.1.23 — Smoke coverage for plain-text status-guide handoff

Base: `chatgpt_claudecode_workflow-2_v0.1.22.zip`

## Scope

Make the non-JSON release status-guide handoff a recurring smoke-tested contract.

## Changes

- Extend `pb test smoke --json` with a bounded local substep:
  - `release_status_guide_plain_readonly`
- The new smoke substep runs non-JSON `pb release status-guide` with the current repo `VERSION` and verifies required plain-text markers:
  - `status=release_status_guidance_available`
  - `next_development_artifact=`
  - `next_development_status_guide_after_build=`
  - `next_development_checkpoint_after_build=`
  - `blocker_codes=`
- Extend the bounded smoke subprocess runner with optional `required_stdout_contains` contract validation.
- Add structured smoke failure status `smoke_stdout_contract_failed` when a command exits zero but omits required output markers.
- Make the status-guide threshold regression test derive its accepted baseline from the current package version so the test remains stable across monotonic focused-development releases.
- Update living design documentation and draw.io source to reflect v0.1.23.

## Non-goals

- No full release-control/adoption behavior.
- No Project Source upload or artifact-current mutation.
- No browser/live ChatGPT automation changes.
- No change to accepted baseline semantics.

## Validation

- Compile check.
- Focused smoke runner and status-guide/checkpoint tests.
- Release docs/config/install-plan/lifecycle-plan checks.
- ZIP hygiene verification.

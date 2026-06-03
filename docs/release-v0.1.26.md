# Release v0.1.26 — Ask/reply JSON data-flow diagram

## Purpose

`v0.1.26` is a deliberately small threshold-candidate slice. It does not broaden runtime behavior. It documents the ask/reply protocol data flow in editable draw.io form so the JSON handoff is clear before the full-test/adoption checkpoint becomes operationally important.

## Baseline

Built from:

```text
chatgpt_claudecode_workflow-2_v0.1.25.zip
```

## Changes

- Updated `VERSION`, package metadata, compose image tag, and version expectations to `v0.1.26`.
- Updated `docs/design/promptbranch-mvp-living-design.md` to describe the ask/reply JSON handoff.
- Updated `docs/design/promptbranch-mvp-living-design.drawio` with a second editable page named `Ask Reply JSON Data Flow`.
- The new diagram shows these operational JSON records:
  - `promptbranch.ask.request` envelope
  - `promptbranch.ask.reply` envelope
  - parsed reply record
  - artifact candidate JSON
  - ZIP verification JSON
  - candidate registry / `pb artifact current` JSON
  - next ask from accepted baseline

## Scope boundary

This release is documentation/data-flow only apart from the normal version bump. It does not:

- change ask/reply parsing behavior;
- change artifact intake behavior;
- run full release-control;
- adopt the candidate;
- upload Project Sources;
- mutate the accepted baseline.

## Threshold-candidate note

At this development-line position, `v0.1.26` is expected to reach the configured full-test/adoption checkpoint threshold when compared with accepted baseline `v0.1.18.1`. The status-guide/checkpoint commands should therefore be read after installation before deciding whether to continue development or run full release-control/adoption.

## Validation performed during build

```text
python3 -m compileall -q .
focused pytest selection
pb release docs-status --version v0.1.26 --json
pb release config --json
pb release install --artifact v0.1.26 --plan --json
pb release lifecycle --artifact v0.1.26 --plan --json
ZIP reopen / CRC / VERSION / hygiene verification
```

## Threshold-candidate status-guide/checkpoint result

After creating the candidate ZIP, the release-status commands were run against a local read-only registry with accepted baseline `v0.1.18.1`.

Result:

```text
pb release status-guide --artifact ./chatgpt_claudecode_workflow-2_v0.1.26.zip --version v0.1.26 --target-version v0.1.26 --json
  status: release_status_guidance_available
  full_test_recommended_now: true
  expected_threshold_version: v0.1.26
  calculation_rule: current_candidate_reached_or_exceeded_threshold
  blockers: []

pb release checkpoint --artifact ./chatgpt_claudecode_workflow-2_v0.1.26.zip --version v0.1.26 --target-version v0.1.26 --mode continue --json
  status: full_test_checkpoint_recommended
  recommendation: consider_full_test_checkpoint
  continue_development: true
  full_test_recommended_now: true
  blockers: []
```

Interpretation: `v0.1.26` is a valid threshold candidate, but the next operator action should be full release-control before adoption or further broadening.

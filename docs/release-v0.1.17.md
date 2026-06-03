# Release v0.1.17

## Scope

Read-only release-status UX hardening for the focused-development line.

This release extends `pb release status-guide --json` with an explicit pre-threshold full-test/adoption planning notice. When the installed development candidate is one normal version away from the configured full-test threshold, the guide reports that the next focused development release is expected to reach the checkpoint threshold and adds a required operator-planning step to the runbook.

## Baseline

Built from:

```text
chatgpt_claudecode_workflow-2_v0.1.16.zip
```

Output:

```text
chatgpt_claudecode_workflow-2_v0.1.17.zip
```

## Behavior

`pb release status-guide --json` remains read-only. It now includes:

```text
checkpoint_threshold.next_release_reaches_full_test_threshold
checkpoint_threshold.next_development_version
checkpoint_threshold.threshold_notice
operator_runbook.next_release_reaches_full_test_threshold
operator_runbook.expected_threshold_version
recommended_sequence[].step == next_release_adoption_planning
```

When the current dev candidate is one version below the threshold, the guide emits:

```text
release_status_guide_full_test_checkpoint_expected_next_release
```

For the current line after accepted `v0.1.10`, this means `v0.1.17` should show the next expected threshold version as `v0.1.18`.

## Non-goals

This release does not:

- install artifacts;
- upload Project Sources;
- run full tests;
- adopt artifacts;
- update artifact/source state;
- commit or push Git state.

## Suggested focused check

```bash
pb release status-guide \
  --artifact ./chatgpt_claudecode_workflow-2_v0.1.17.zip \
  --version v0.1.17 \
  --target-version v0.1.17 \
  --json | python3 -m json.tool

pb release checkpoint \
  --artifact ./chatgpt_claudecode_workflow-2_v0.1.17.zip \
  --version v0.1.17 \
  --target-version v0.1.17 \
  --mode continue \
  --json | python3 -m json.tool

pb test smoke --json
```

## Validation

Focused validation was run during artifact construction:

```text
pytest status-guide focused tests
pytest release parser focused tests
orchestration example validation
compileall
release docs-status
release config
release install --plan
release lifecycle --plan
release checkpoint --mode continue
release status-guide
release-control --import-plan
ZIP reopen / CRC / VERSION / hygiene / root-layout
```

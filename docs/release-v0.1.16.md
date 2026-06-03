# Release v0.1.16

## Scope

Read-only release-status guide threshold meter.

This release continues from `chatgpt_claudecode_workflow-2_v0.1.15.zip` and preserves the accepted `v0.1.10` baseline/adoption continuity model. It does not add install, source-upload, adoption, Git, or Project Source mutation behavior.

## Changes

- Extends `pb release status-guide --json` with an explicit `checkpoint_threshold` summary.
- Extends the shared development-complexity summary with remaining distance to the full-test/adoption checkpoint thresholds.
- Adds a read-only optional `adoption_threshold_watch` step to the dev-candidate `recommended_sequence`.
- Updates non-JSON `status-guide` output to show:
  - `full_test_recommended_now`
  - `normal_versions_ahead`
  - `normal_versions_until_full_test_threshold`
- Updates the living design document and editable draw.io source.

## Read-only contract

`pb release status-guide` remains advisory only:

```text
install_performed=false
candidate_test_performed=false
adoption_performed=false
project_source_mutated=false
artifact_registry_updated=false
git_commit_performed=false
git_push_performed=false
mutating_actions_executed=false
```

## Intended operator flow

For installed-but-not-adopted development candidates:

```bash
pb release status-guide \
  --artifact ./chatgpt_claudecode_workflow-2_v0.1.16.zip \
  --version v0.1.16 \
  --target-version v0.1.16 \
  --json | python3 -m json.tool

pb release checkpoint \
  --artifact ./chatgpt_claudecode_workflow-2_v0.1.16.zip \
  --version v0.1.16 \
  --target-version v0.1.16 \
  --mode continue \
  --json | python3 -m json.tool

pb test smoke --json
```

## Validation

Focused validation performed during release construction:

```text
compileall
orchestration examples validation
orchestration tests
targeted release status-guide/checkpoint/dev-status tests
targeted CLI parser tests
docs-status
release config
release install --plan
release lifecycle --plan
release checkpoint --mode continue
release-control --import-plan
ZIP reopen / CRC / VERSION / hygiene / root-layout checks
```

Full browser/service/adoption tests were not run for this focused development slice.

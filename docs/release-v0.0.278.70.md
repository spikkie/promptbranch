# Release v0.0.278.70 — ask-live project URL normalization repair

## Scope

Repair `pb test ask-live --json` project-membership validation after v0.0.278.69.

## Reason

ChatGPT can return both of these URLs for the same temporary project:

```text
/g/g-p-<32hex>/project
/g/g-p-<32hex>-<project-name>/project
```

v0.0.278.69 compared normalized project home URLs too literally and rejected the slugged form as `wrong_project`, even when the stable project id matched.

## Changes

- Compare ask-live project membership by canonical `g-p-<32hex>` project id when available.
- Preserve full URL fallback comparison for non-standard or unit-test URLs.
- Add `expected_project_id` and `response_project_id` to each ask-live step result.
- Add regression coverage for bare-id versus slugged project URL equivalence.
- Do not change `pb ask` fill, submit, retry, or DOM-delta confirmation behavior.

## Validation target

After installation, rerun:

```bash
pb test ask-live --json \
  --profile-dir ./.pb_profile_local_debug \
  --only plain,prompt_file \
  2>&1 | tee pb_test.ask_live.v0.0.278.70.narrow.log
```

Expected result:

```text
ok: true
test_project_created: true
test_project_removed: true
all steps in_expected_project: true
all steps expected_project_id == response_project_id
```

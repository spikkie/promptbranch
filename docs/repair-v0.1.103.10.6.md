# v0.1.103.10.6 — Project Source gate operator guidance repair

## Scope

`v0.1.103.10.6` is a repair-only continuation of the standard browser profile default slice.

It does not enable Project Source mutation. It repairs the operator-facing failure surface when the old `pbsa` / `promptbranch src add` habit is used during auth-only standard-browser validation.

## Problem

When the Docker standard-browser envelope is active and `PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION` is not set, `/v1/project-sources` correctly returns `403 project_source_mutation_gate_closed`.

That is the intended safety behavior for this slice, but the CLI previously wrapped the service payload into a generic `source_add_failed` error string. Operators could misread the result as a browser/profile failure instead of an expected mutation gate.

## Change

`promptbranch_cli.py` now preserves the parsed service status for source-add HTTP failures. For `project_source_mutation_gate_closed`, the CLI response reports:

- `status=project_source_mutation_gate_closed`
- `classification=expected_safety_gate`
- `project_source_mutated=false`
- `project_source_required_for_standard_browser_validation=false`
- a recovery hint explaining that `pbsa` is not the validation path
- a candidate-specific safe validation command when the file name contains a canonical `_vX.Y.Z.zip` version

## Out of scope

- No Project Source mutation is enabled.
- No Cloudflare-safe browser envelope change.
- No Patchright/CDP session-manager scope change.
- No artifact adoption/current change.
- No Git commit/push.
- No ChatGPT Project deletion.

## Validation

Focused tests:

```text
python3 -m pytest -q tests/test_standard_browser_source_add_gate.py tests/test_promptbranch_version.py tests/test_project_control_surface.py
```

Result:

```text
23 passed
```

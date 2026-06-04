# Release v0.1.33

## Scope

`v0.1.33` continues focused development from `v0.1.32` and cleans up read-only `pb release checkpoint --mode continue` operator guidance.

## Change

When an explicit checkpoint candidate is already the current development head and the checkpoint decision still allows focused development, the inherited install-plan warning `release_install_candidate_not_next_normal_version` is contextualized rather than promoted as a top-level checkpoint warning.

The warning remains visible in the nested install-plan summary and is also listed in `contextualized_warnings` / `contextualized_warning_codes`, but it no longer appears in the top-level `warning_codes` for continue-mode checkpoint output.

Adoption mode keeps the warning as a top-level warning because adoption still requires deliberate full-test/release-control handling.

## Non-goals

- No adoption behavior change.
- No Project Source mutation change.
- No ZIP import behavior change.
- No full-test threshold policy change.
- No browser automation change.

## Validation intent

The slice is validated by focused checkpoint regression coverage, smoke, docs-status, config, release install/lifecycle plan checks, and ZIP hygiene verification.

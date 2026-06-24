# Release v0.1.88 — Incremental release validation evidence reuse

## Baseline

`chatgpt_claudecode_workflow-2_v0.1.87.1.zip` is the accepted/current baseline for this slice based on operator-provided `--run-tests --adopt-after-validation` evidence.

## Scope

This slice adds fail-closed release-control validation evidence reuse so `--run-all-tests` can reuse a previously passed identical `--run-tests` direct full-test group for the same artifact hash and validation dimensions.

The first reuse scope is intentionally narrow:

- group: `full_direct`
- evidence source: prior successful direct `pb test full` / `pb test report`
- reuse target: later `--run-all-tests` direct full-test group
- still executed by `--run-all-tests`: localhost, live browser, import-smoke, artifact-guard, and any non-identical or missing groups

## Fail-closed identity

Evidence is reusable only when all required dimensions match:

- evidence schema and schema version
- evidence `ok=true` and `status=passed`
- version
- artifact reference
- artifact SHA256
- test group id
- transport
- service base
- runtime mode
- strict source-kind matrix mode
- command signature
- prior test/report exit codes

If evidence is absent, stale, failed, malformed, or dimension-mismatched, release-control reruns the group.

## Out of scope

No changes to Promptbranch loop behavior, live browser behavior, Project Source mutation, artifact adoption/current behavior, Kubernetes/deployment behavior, or ChatGPT Project deletion behavior.

## Validation

Focused validation for this candidate covers:

- static shell contract for validation evidence reuse fields and fail-closed dimensions
- all-tests summary `validation_reuse` reporting surface
- version tests
- project-control tests
- compileall
- shell syntax
- Artifact Guardian
- artifact verification

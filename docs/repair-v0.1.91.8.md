# Repair v0.1.91.8 — Run-all single live-browser source lifecycle reuse

## Base

Repair base: `chatgpt_claudecode_workflow-2_v0.1.91.7.zip` candidate state.

Accepted/current remains externally proven state until operator release-control adoption/current evidence is provided.

## Reason

The `v0.1.91.7 --run-all-tests` attempt proved the pre-source-add Docker no-cache build-context repair, Project Source add, service recreate/version verification, and direct full validation. The remaining failure occurred in `full_localhost`, where run-all repeated the live browser/source lifecycle and failed at `project_source_add_text` with stale-inflight post-commit source-surface verification.

This duplicate localhost live-source mutation is high-risk and low-value after matching green `full_direct` evidence already proves the browser/source lifecycle for the same artifact, version, hash, runtime, source-kind matrix mode, service base, and command signature.

## Scope

This repair changes only the run-all localhost matrix behavior after a matching green direct full proof exists.

It preserves:

- `v0.1.91.1` ask-live first-turn retry recovery.
- `v0.1.91.2` pretty JSON/live-step aggregation repair.
- `v0.1.91.3` Docker recreate/version verification hardening.
- `v0.1.91.4` clean-system pre-source-add bootstrap.
- `v0.1.91.5` live_project_ensure terminal-line aggregation repair.
- `v0.1.91.6` adopt-after-validation reused-evidence report path repair.
- `v0.1.91.7` pre-source-add Docker no-cache build-context freshness repair.

## Behavior

For `--run-all-tests`, `full_localhost` no longer reruns the live browser/source lifecycle when `validation_evidence/full_direct.<version>.json` validates against the current artifact/version/hash/dimensions.

Instead, release-control writes a `full_localhost` summary with:

- `status=\"reused_browser_source_lifecycle\"`
- `action=\"reused_browser_source_lifecycle\"`
- the direct evidence path and artifact SHA256
- localhost base URL and service-health/check metadata
- release-validation group reuse metadata

The all-tests summary still includes `full_localhost` in the localhost cooldown audit, so the matrix remains visible. The run remains fail-closed if matching direct evidence is missing, failed, stale, or dimension-mismatched.

## Validation

Focused validation performed for this candidate:

- run-all final report flow with one direct full browser/source proof and reused localhost browser/source lifecycle
- localhost rate-limit retry denial when direct evidence is unavailable and localhost must execute
- prior direct evidence reuse plus localhost lifecycle reuse
- static contract for direct lifecycle reuse in `full_localhost`
- localhost cooldown audit contract
- adoption verifier reused-evidence report path contract
- pre-source-add Docker build-context freshness contract
- loop/CLI loop tests
- version tests
- project-control surface tests
- compileall
- shell syntax
- Artifact Guardian
- artifact verify

## No slice advancement

This repair does not advance the `v0.1.91` feature slice or open a normal `v0.1.92` line. It changes release-control validation orchestration only.

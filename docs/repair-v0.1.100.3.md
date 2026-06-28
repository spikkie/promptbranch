# Repair v0.1.100.3 — ZIP hygiene repair for packaged debug artifacts

Repair version: `v0.1.100.3`
Base failed repair candidate: `chatgpt_claudecode_workflow-2_v0.1.100.2.zip`
Accepted/current baseline before repair: `chatgpt_claudecode_workflow-2_v0.1.99.1.zip`

## Reason

`v0.1.100.2` was rejected before install because the candidate ZIP contained generated `debug_artifacts/` entries. Release-control correctly classified these as protected ZIP entries and refused mutation/adoption.

## Scope

This repair removes generated `debug_artifacts/` from the release payload and strengthens Artifact Guardian policy/tests so debug artifacts are rejected before candidate handoff.

## Preserved behavior

- `v0.1.100` first controlled read-only validation command execution remains unchanged.
- `v0.1.100.1` text-source stale-inflight recovery diagnostics remain unchanged.
- `v0.1.100.2` browser scheduler source-lifecycle timeout repair remains unchanged.
- `v0.1.101` remains deferred.

## Validation expectation

Artifact Guardian must fail if `debug_artifacts/` is present in a ZIP and must pass for the cleaned `v0.1.100.3` candidate.

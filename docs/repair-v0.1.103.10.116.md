# Repair v0.1.103.10.116

## Purpose

Correct the final post-adoption verification without changing the live-proven adoption transaction introduced in `v0.1.103.10.115`.

## Baseline

`v0.1.103.10.115` is accepted/current. Its full direct and localhost validation, continuous profile handling, indexed-family overwrite transaction, current ChatGPT submit-flow recognition, parse-independent response completion, structured rate-limit classification, authoritative `pb project join` preflight, and evidence-bound adoption remain unchanged.

## Defect

The old final verifier required `state.artifact_ref`, `state.source_ref`, and `registry_current.filename` all to equal the canonical artifact filename. Evidence-bound adoption correctly stores the exact backend-assigned Project Source filename in `state.source_ref`, such as `name(1).zip`, so an otherwise fully consistent adopted state was rejected after the mutation had already succeeded.

## Repair contract

The final verifier now requires:

- runtime, state artifact, state source, and registry-current versions to equal the expected release version;
- `state.artifact_ref` and `registry_current.filename` to equal the canonical artifact filename;
- `state.source_ref` to equal the exact `assigned_filename` captured in immutable adoption evidence;
- registry processed-file and Library metadata IDs to equal the captured evidence;
- all three existing consistency booleans to remain true.

Only after every check succeeds does the verifier emit `status: release_adopted_and_verified`.

## Regression fixture

A focused fixture uses:

- canonical artifact: `name.zip`;
- assigned Project Source: `name(1).zip`;
- all four versions equal;
- exact processed-file and Library metadata IDs;
- all three consistency booleans true.

The expected result is successful post-adoption verification.

## Out of scope

- no Project Source upload or replacement changes;
- no browser-profile changes;
- no response-completion changes;
- no rate-limit policy changes;
- no adoption mutation changes;
- no normal-slice scope advancement.

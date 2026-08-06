# Release v0.1.123.2.6

## Type

Repair candidate. This release does not advance normal MVP scope or formal proof count.

## Accepted baseline

- Version: `v0.1.123.2.5`
- Artifact: `chatgpt_claudecode_workflow-2_v0.1.123.2.5.zip`
- Project Source: `chatgpt_claudecode_workflow-2_v0.1.123.2.5(1).zip`
- SHA-256: `74a6d268742fb9f0347bf4457999bd3f910e2e57158f0bcb9a04b8b8c5b6e31e`

## Purpose

Detect and download the rendered release ZIP returned by the exact correlated assistant answer, then verify it against the protocol envelope before artifact intake succeeds.

## Changes

- Propagates request ID, answer ID, and assistant-turn index through the browser artifact-download path.
- Selects exactly one correlated assistant turn before looking for a download control.
- Rejects missing or ambiguous correlated turns and missing or ambiguous rendered attachments.
- Downloads through the active authenticated browser session into `.pb_profile/artifact_inbox/`.
- Normalizes top-level artifact download metadata from persisted protocol replies.
- Verifies observed SHA-256, byte size, ZIP entry count, CRC, embedded version, and filename against the envelope.
- Reuses an already verified inbox artifact during the integrated lifecycle.
- Preserves the proven `v0.1.123.2.5` generation prompt unchanged.

## Staged validation

1. Offline focused intake tests.
2. Persisted-answer replay without fresh generation.
3. One direct `ask-release` download-and-verify test.
4. Focused ask/intake regression group.
5. Full strict release validation and adoption.

## Non-goals

- No automatic adoption in the direct intake test.
- No Project Source mutation from answer intake.
- No Git commit or push from answer intake.
- No change to the two-component generation prompt.
- No formal MVP proof increment from this repair.

## Corrected-candidate compatibility repair

The first focused run did not reach the rendered-attachment tests because the operator's ambient virtualenv combined FastAPI 0.128.x with a Starlette Router constructor that had removed the legacy `on_startup` and `on_shutdown` arguments. The release's declared dependency pins remain unchanged.

This corrected candidate additionally:

- installs a narrow collection-time Router compatibility bridge only when those legacy constructor parameters are absent;
- preserves startup/shutdown handlers through a lifespan adapter;
- adds a subprocess regression that imports the real container API under a simulated modern Router signature;
- makes the selected legacy `ask-release` request-rendering fixture establish explicit hermetic Project and repository authority;
- preserves mandatory `repo_id` validation rather than weakening the artifact registry.

Offline validation completed:

- Gate 1 focused intake: green;
- Router compatibility regressions: green;
- Gate 4 ask/intake selection: green;
- broader focused module group: green.

Not completed by candidate construction: persisted-answer browser replay, fresh direct `ask-release`, full strict release validation, Project Source mutation, adoption, Git commit/push, or formal MVP proof advancement.


## Deterministic persisted-run replay correction

The first real Gate 2 attempt did not reach attachment discovery. `--from-last-protocol-run` selected the newest validated record, `req_20260804T074608454070Z`, whose valid reply was `status=no_artifact` and `result_type=no_change`. The intended artifact-producing record was the older request `req_20260805T105438125979Z`.

This corrected candidate adds:

- `pb artifact intake --protocol-run-request-id <exact-id>` for use with `--from-last-protocol-run`;
- exact file/request identity validation before candidate extraction;
- fail-closed missing, invalid, unvalidated, and mismatched-record outcomes;
- explicit selected-run source and selector metadata in JSON output;
- regressions proving that a newer valid no-artifact run cannot displace an explicitly selected older artifact run.

Correct Gate 2 command:

```bash
pb artifact intake \
  --from-last-protocol-run \
  --protocol-run-request-id req_20260805T105438125979Z \
  --replay-unvalidated-artifact-run \
  --download \
  --verify \
  --expect-artifact chatgpt_claudecode_workflow-2_v0.1.124.zip \
  --expect-version v0.1.124 \
  --expect-repo chatgpt_claudecode_workflow-2 \
  --download-timeout 300 \
  --json
```

This remains a candidate correction. The real browser replay and all later release gates remain pending.

## Explicit attachment-failure replay correction

The exact selector then proved a second Gate 2 boundary: the intended record was found, but its historical status is `artifact_declared_but_not_attached` with `reply_validation_ok=false`. The old loader required an already validated run, which made replay of the attachment-proof failure circular.

This corrected candidate adds the explicit `--replay-unvalidated-artifact-run` option. It:

- requires exact `--protocol-run-request-id`, `--download`, and `--verify`;
- forbids migration and generic validation bypass;
- allows only `artifact_declared_but_not_attached` plus its corresponding download-proof errors;
- verifies request, correlation, envelope, conversation, message, and answer identity before browser access;
- requires exactly one declared candidate ZIP consistent with request expectations;
- rejects any prior download, verification, materialization, Project Source, registry/state, migration, or adoption mutation;
- preserves normal validated-run selection unchanged.

Offline regression evidence includes successful simulated browser-byte download and envelope/ZIP verification, plus fail-closed tests for missing opt-in, wrong prior status, extra validation failures, prior mutation, and answer-identity drift. The real authenticated Gate 2 replay remains pending on the operator host. No fresh `v0.1.124` answer was generated.



## Historical protocol-record shape normalization correction

The real exact-ID Gate 2 run selected the intended request but rejected eight compatibility checks before browser access. The persisted record predates the current replay schema: it has authoritative top-level and selected-answer identities without a complete `selected_protocol_reply` summary, declares the ZIP through `media_type=application/zip`, uses `baseline.input_baseline`, and records the attachment-only outcome through the historical `reply_validated`, `download_proof`, and `artifact_declared_but_not_attached` failure set.

This replacement candidate normalizes only that explicit legacy replay path. It:

- derives absent selection-summary fields from the already exact run/request/correlation and selected-answer identities, while rejecting any contradictory copy;
- recognizes a legacy artifact as ZIP only when the filename ends in `.zip` and the declared MIME type is an allowlisted ZIP media type;
- accepts `input_baseline` as the historical alias for `input_artifact`, requires exact input version, target version, and release type, and rejects any optional source/registry value that contradicts the request;
- canonicalizes prefixed and unprefixed attachment-only failure labels and requires the historical positive filename/version/role/count checks before replay;
- keeps normal validated-run intake, generic reply parsing, migration, Project Source, registry/state mutation, and adoption behavior unchanged.

Offline evidence now includes an executable fixture matching the observed historical record shape. It reaches simulated browser download and byte verification. Negative regressions prove that identity conflict, non-ZIP MIME type, baseline mismatch, extra failure labels, and failed artifact-identity checks remain blocked before browser access. The authenticated operator-host Gate 2 rerun remains required.

## Post-materialization validation finalization correction

A fresh direct `ask-release` produced the rendered `v0.1.124` ZIP and the browser path successfully downloaded and verified it, including envelope metadata. The persisted protocol result nevertheless remained `release_candidate_validation_failed` because reply validation had been computed before attachment enrichment and because the envelope used `input_baseline` plus `target_version` rather than the older `input_artifact` plus `output_version` projections.

This replacement candidate:

- normalizes baseline aliases while rejecting contradictory copies;
- accepts agreeing target-version evidence from baseline and the single candidate artifact;
- recognizes an exact already materialized failed run only through exact request-ID plus `--download --verify`;
- reopens the exact persisted artifact-inbox path and rechecks SHA-256, byte size, entry count, CRC, embedded version, selected answer identity, and envelope metadata;
- skips browser redownload;
- recomputes the full ask-release validation and persists `status=reply_validated` only when every gate is green;
- rejects missing/tampered inbox bytes and any prior migration, Project Source, registry/current, or adoption mutation.

No fresh `v0.1.124` generation, migration, publication, adoption, commit, push, or MVP proof advancement is performed by this correction.


## Exact validated-run migration and candidate-run correction

After post-materialization finalization succeeded, ordinary `--migrate` intake still rejected the same artifact because it did not share the legacy MIME-only ZIP and `input_baseline` normalization. The guarded candidate runner also rebuilt its intake step as `--from-last-answer`, losing the exact validated request identity and expectations.

This replacement candidate:

- centralizes persisted-run ZIP-kind and baseline normalization across replay, finalization, normal validated intake, and migration;
- treats missing optional source metadata as absent while rejecting present contradictions;
- reuses only the exact verified artifact-inbox ZIP for a validated request and reopens it before migration;
- makes `candidate-run` preserve `--from-last-protocol-run --protocol-run-request-id req_20260805T145619199617Z` plus expected repository, filename, and version;
- records repository identity in the migrated candidate entry;
- adds an integration test that finalizes a materialized run and ends with exactly one migrated candidate.

No new `v0.1.124` answer, candidate test, Project Source mutation, adoption, commit, push, or formal proof advancement is performed.

## Pasted-text processing-stream identity correction

The focused `v0.1.124` full candidate test reached `project_source_add_text` and observed a successful ChatGPT processing stream with a new `file_...` identity, a new `libfile_...` metadata identity, and the backend-assigned filename `pasted.txt`. The previous validator incorrectly compared the logical integration-test display name with that backend filename and returned `project_source_processing_stream_identity_not_verified`.

This replacement candidate:

- separates the logical text-source display name from the backend processing-stream filename contract;
- accepts `pasted.txt` only for `source_kind=text`, while retaining exact/indexed filename-family validation for uploaded files;
- still requires a completed processing stream plus concrete `file_...` and `libfile_...` identities;
- rejects reuse of an already observed text-source processing identity pair within the browser-client session;
- preserves post-save Project Sources persistence and text-content-anchor verification as the operation-level proof;
- exposes the logical name, assigned filename, processing identities, filename-correlation mode, and content proof in the result;
- adds regressions for canonical `pasted.txt`, missing IDs, reused IDs, file-source filename mismatch, and end-to-end text-add result correlation.

The required next proof is a focused live `project_source_add_text` run. A full candidate run and adoption remain blocked until that focused live proof is green.

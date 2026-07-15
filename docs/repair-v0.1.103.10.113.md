# Repair v0.1.103.10.113 — collision-free indexed replacement upload

## Baseline

- Accepted/current remains `v0.1.103.10.68`.
- `v0.1.103.10.112` is retained as failed and not adopted: changed replacement bytes were proven, but selecting the same local basename produced no second upload request in both full transports.
- The `v0.1.103.10.112` fail-closed result was correct; this repair changes the upload trigger without weakening any identity or deletion gate.

## Scope

1. Preserve distinct initial and replacement SHA-256 proof.
2. When in-place Replace is unavailable, copy replacement bytes to a temporary collision-free numeric canonical-family member such as `name(8472193501).ext`.
3. Require the staged copy to be byte-identical to the replacement and to match the canonical family regex.
4. Treat the numeric token as a local transaction identifier only; never predict or require a backend index.
5. Submit the staged path exactly once and remove the temporary local copy after browser selection.
6. Keep the canonical requested filename separate from the staged upload filename.
7. Capture the exact assigned filename, `processed_file_id`, and `library_metadata_object_id` from `process_upload_stream`.
8. Verify the exact newly assigned Project Source before deleting only family identities observed before upload.
9. Require the newly assigned source as the final singleton.
10. Fail closed on staging failure, no upload, incomplete processing/backing identity, ambiguous deletion scope, or non-singleton final state.
11. Require both `full_direct` and `full_localhost` before adoption.

## Out of scope

- No backend-index prediction.
- No canonical artifact rename.
- No artifact-registry authority changes.
- No filename-only Library deletion.
- No ChatGPT Project deletion.
- No normal-slice advancement.

# Repair v0.1.103.10.112 — changed-content indexed-family overwrite proof

## Baseline

- Accepted/current remains `v0.1.103.10.68`.
- `v0.1.103.10.111` is retained as a failed, not-adopted candidate: `full_direct` and `full_localhost` rejected an overwrite that produced no new upload transaction.

## Scope

1. Rewrite the integration source file before overwrite and require distinct initial and replacement SHA-256 values.
2. Accept the exact backend-assigned canonical or indexed filename returned by `process_upload_stream`.
3. Do not predict or require a particular suffix index.
4. Require a completed processing stream, `processed_file_id`, and `library_metadata_object_id` before deleting any old Project Source.
5. Freeze destructive scope to Project Source family identities observed before upload.
6. Require the exact newly assigned source to be the final singleton.
7. Fail closed when upload does not start, processing does not complete, backing identity is absent/not new, or final family authority is ambiguous.
8. Require both `full_direct` and `full_localhost` before adoption.

## Out of scope

- No artifact-registry authority changes.
- No ChatGPT Project deletion.
- No filename-only Library deletion.
- No suffix-index prediction.
- No normal-slice advancement.

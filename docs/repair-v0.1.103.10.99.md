# Repair v0.1.103.10.99

## Problem

`v0.1.103.10.98` repaired the normal Project Source add path, but the backend-protocol diagnostic still invoked the isolated legacy `v0.1.103.10.75` upload transaction. That live path reached ordinary save quietness with a pending processing stream and then verified rendered persistence before any terminal stream result existed.

## Repair

- Enforce `ordinary quiet → terminal processing identity → persistence verification → watcher disposal` in `_add_project_source_operation_legacy_10_75`.
- Pass the exact expected filename into the processing watcher.
- Preserve terminal stream evidence in success and persistence-failure results.
- Prefer direct processing-stream identity in the diagnostic upload identity extractor.
- Reject `processing_stream_pending=true` with a null processing result as `internal_processing_stream_wait_skipped`.
- Apply the invariant to both the first diagnostic upload and the final canonical reupload.

## Safety

Normal `pbsa` remains unchanged. Accepted/current remains `v0.1.103.10.68`. Canonical release `pbsa`, adoption, existing suffix-evidence mutation, and ChatGPT Project deletion remain prohibited.

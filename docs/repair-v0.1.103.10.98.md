# Repair v0.1.103.10.98

## Scope

Await terminal Project Source processing completion before persistence verification and retain the save watcher until terminal handling and persistence verification are complete.

## Evidence basis

The v0.1.103.10.97 live diagnostic reached ordinary save quietness while `/backend-api/files/process_upload_stream` remained pending, then checked the Project Sources UI before terminal indexing. The source card was not yet rendered, the watcher was disposed, and the diagnostic returned `first_upload_identity_or_presence_not_authoritative` without terminal stream identity.

## Repair

- Order the proof phases as ordinary save quiet, terminal processing identity, Project Source persistence verification, watcher disposal.
- Retain the processing response privately when response headers arrive.
- Read and parse the SSE body only after `requestfinished`.
- Require exact `file_...`, `libfile_...`, and canonical filename before persistence verification.
- Preserve processing-stream evidence in persistence failures.
- Classify terminal-success/UI-absence as `project_source_persistence_not_verified_after_processing_completion`.

## Safety

Accepted/current remains v0.1.103.10.68. Canonical release `pbsa`, adoption, target deletion, and existing evidence mutation remain prohibited.

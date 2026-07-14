# Repair v0.1.103.10.97

## Scope

Separate long-lived Project Source processing streams from ordinary save quietness and make diagnostic exception classification explicit.

## Evidence basis

The v0.1.103.10.96 live diagnostic observed a successful file allocation and signed upload, followed by `/backend-api/files/process_upload_stream`. Ordinary save settling timed out at roughly 60 seconds while that stream later completed successfully at roughly 95 seconds with:

- `file.processing.started`
- `file.processing.file_ready`
- `file.indexing.completed` containing the exact `libfile_...` and assigned filename
- `file.processing.completed` containing the exact `file_...`

## Repair

- Track processing-stream requests separately from ordinary save requests.
- Allow ordinary save quietness once no ordinary request is in flight.
- Wait in a separate bounded phase for a terminal stream event.
- Require exact processed-file ID, Library metadata ID, and expected filename.
- Fail closed on stream failure, timeout, or incomplete identity.
- Populate top-level diagnostic `reason` for every caught exception.

## Safety

Accepted/current remains v0.1.103.10.68. Canonical release `pbsa`, adoption, target deletion, and existing evidence mutation remain prohibited.

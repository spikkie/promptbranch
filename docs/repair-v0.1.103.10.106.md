# v0.1.103.10.106 — correlate backend-assigned indexed Project Source identities

## Problem

ChatGPT can persist a canonical local ZIP under an indexed Project Source display name such as `platform-gitops_v0.0.6.6(14).zip`. Promptbranch 0.1.103.10.105 treated every indexed name as a collision, reported failure after a successful upload, and could create another indexed copy on retry.

## Repair

- Preserve the canonical local filename, version, checksum, Git identity, and artifact-registry identity.
- Accept exactly one indexed assigned filename only when terminal processing-stream IDs and exact assigned-card persistence correlate it to the current upload.
- Read back existing indexed sources through Library inventory and require one assigned record, stable `file_...` and `libfile_...` identities, and matching local size where available.
- Return `requested_filename`, `assigned_filename`, `processed_file_id`, `library_metadata_object_id`, `project_source_mutated`, and `persistence_verified`.
- Reuse an existing uniquely correlated indexed source without upload or pre-delete.
- Block multiple, stale, or identity-incomplete indexed matches.
- Permit artifact adoption to keep the canonical artifact ref while recording the assigned Project Source ref as source metadata.

## Restrictions

No canonical Promptbranch release `pbsa`, adoption, Project deletion, registry reconciliation, or unrelated Library cleanup is performed by this build. The existing `platform-gitops_v0.0.6.6(14).zip` source is not touched during build validation.

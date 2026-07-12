# Repair v0.1.103.10.81

## Scope

- Preserve the strict all-all gate, sentinel normalization, authoritative Project Sources preflight/suffix rollback, and verified candidate-image reuse.
- Accept a unique downloadable transport ZIP basename without using it as release identity.
- Verify transport ZIP CRC, root release-control entrypoint and internal `VERSION=v0.1.103.10.81` before delegation/import.
- Derive canonical artifact name `chatgpt_claudecode_workflow-2_v0.1.103.10.81.zip` from repository identity plus requested version.
- Materialize the canonical local copy and upload/adopt only that canonical path.
- Log `candidate_transport_zip` and `canonical_artifact_zip` independently.
- Retain `backend_renamed_source` classification and immediate rollback if the backend still suffix-renames the canonical upload.

## Transport artifact

`chatgpt_claudecode_workflow-2_transport_v0.1.103.10.81_b7c1de9f28.zip`

## Non-goals

- No Cloudflare/rate-limit bypass.
- No host-CDP/session-manager.
- No copied-profile trust.
- No adoption claim.

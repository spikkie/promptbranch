# Repair v0.1.103.10.90

## Scope

- Keep `pbsa <file>` unchanged.
- Keep all existing `(1)` diagnostic evidence untouched.
- Use one new disposable project/source filename and one separately uploaded disposable Library filename.
- Capture all redacted fetch/XHR traffic across project creation, Project Source upload/removal, Library navigation, disposable Library upload, soft deletion, Recently deleted inventory, permanent deletion, exact backend replay, and canonical reupload.
- Discover inventory and delete protocols only when responses/requests contain exact captured `libfile_...` or `file_...` identities.
- Verify exact target presence before deletion, exact movement to Recently deleted after soft deletion, and two stable exact absence observations after permanent deletion.
- Shield automatic global conversation-history requests on Library routes.
- Fail closed with one of the required diagnostic classifications.

## Required classifications

- `canonical_reupload_after_backend_delete`
- `backend_inventory_not_discovered`
- `backend_delete_protocol_not_discovered`
- `exact_backend_delete_failed`
- `backend_suffix_after_verified_backend_delete`
- `diagnostic_inconclusive`

## Out of scope

Release artifact upload, adoption, existing Project Source mutation, existing evidence cleanup, filename-only Library deletion, Cloudflare/rate-limit bypass, host CDP/session manager, and normal release-line advancement.

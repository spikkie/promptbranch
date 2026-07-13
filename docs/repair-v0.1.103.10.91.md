# Repair v0.1.103.10.91

## Scope

- Keep `pbsa <file>` unchanged.
- Accept captured `GET /backend-api/files/library/nodes` traffic as active inventory discovery, including an initially empty exact-filename query.
- Preserve both processed `file_...` and metadata `libfile_...` identities from Library-node payloads.
- Poll exact `libfile_...` inventory presence with stable observations instead of using immediate DOM search as the identity gate.
- Classify missing upload identity separately from delayed backend visibility and delayed UI selectability.
- Export every fetch/XHR event; omit unrelated bodies and recursively sanitize protocol bodies and sensitive headers.
- Keep target deletion and canonical reupload fail closed.

## Required outcomes

- `disposable_library_upload_identity_not_captured` only when either exact upload ID is actually missing.
- `disposable_library_visibility_timeout_after_identity_capture` when IDs exist but backend inventory never becomes authoritative.
- `disposable_library_ui_not_selectable_after_backend_visibility` when backend presence is proven but the disposable item cannot be safely selected in the UI.
- Existing backend-delete and canonical-reupload classifications remain unchanged.

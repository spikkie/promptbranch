# Repair v0.1.103.10.102

## Purpose

Bind visible-Library soft-delete protocol discovery to an authoritative request-sequence boundary and immutable request-start phase metadata.

## Scope

- Settle all prior Fetch/XHR capture tasks before the row-scoped Delete action.
- Record the maximum request sequence, event count, task count, and current phase immediately before the Delete click.
- Set `visible_library_soft_delete` before clicking the exact bound row action.
- Snapshot request phase once, when each fetch/XHR request begins.
- Carry that immutable phase and sequence into response events, response-capture tasks, and unresolved-task diagnostics.
- Discover a successful mutation primarily from `sequence > soft_delete_start_sequence`, not from mutable phase state.
- Require a paired non-GET/HEAD/OPTIONS request and successful 2xx response with the exact `libfile_...` or `file_...` identity.
- Return `soft_delete_protocol_identity_not_verified` when successful post-boundary mutation candidates exist but exact identity is absent.
- Return `soft_delete_protocol_not_discovered` only when no successful post-boundary mutation candidate exists.
- Export sanitized candidate diagnostics: sequence, immutable phases, method, URL path, status, content type, observed identities, and request/response body schemas.
- Reconcile the initial visible-Library upload result after terminal stream identity, stable backend presence, and exact UI binding prove success.
- Suppress duplicate trace-settlement history entries when phase and task state are unchanged.

## Preserved behavior

- Accepted/current remains `v0.1.103.10.68`.
- The `v0.1.103.10.99` Project Source terminal processing-stream implementation is unchanged.
- The `v0.1.103.10.100` bounded stream-safe generic Fetch/XHR settlement is unchanged.
- The `v0.1.103.10.101` dedicated visible-Library processing-stream watcher is unchanged.
- Existing active-inventory, Recently deleted, hard-delete, and canonical-reupload gates remain fail closed.
- Normal `pbsa` is unchanged.
- Canonical release `pbsa` and adoption are not performed.
- ChatGPT Project deletion remains frozen.

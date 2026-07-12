# v0.1.103.10.79 repair

## Scope

Require stable Project Sources preflight and fail fast on backend-assigned suffix names.

## Behavior

- File upload preflight is authoritative only after an explicit empty state or multiple stable non-empty source snapshots.
- Zero cards without an explicit empty state return `source_preflight_not_authoritative`; no upload occurs.
- Duplicate/exact-name checks run only after authoritative preflight.
- After a committed upload, a newly created `name(n).ext` source is detected before exact-name persistence retries.
- A uniquely identifiable new suffix source is rolled back before the operation returns `backend_renamed_source`.
- Successful source add still requires the exact canonical basename.
- Source-add read-timeout JSON includes configured timeout and active-operation details.

## Preserved constraints

- strict all-all install/adoption gate
- release-live sentinel normalization
- adoption refusal unless all-all is `GO`
- no Cloudflare or rate-limit bypass
- no host-CDP/session-manager
- no copied-profile trust

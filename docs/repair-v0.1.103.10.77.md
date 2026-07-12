# v0.1.103.10.77 — accept ChatGPT duplicate-suffix filename as valid overwrite persistence evidence

## Scope

This repair keeps the strict all-all `install.sh` gate from `v0.1.103.10.69`, the product-clean `LIVE_BLOCKED` classification, and the `v0.1.103.10.76` release-live sentinel normalization.

The narrow defect repaired here is the `project_source_overwrite_file` verification false negative where ChatGPT reports a committed file-source save, but the refreshed Project Sources surface displays the uploaded file under a duplicate-suffixed name such as `name(1).txt Document` instead of the canonical `name.txt Document`.

## Behavior

For file-source overwrite verification only, Promptbranch now treats `name(1).ext` and `name (1).ext` as valid persistence evidence for `name.ext` when all of the following are true:

1. A save commit was observed.
2. No save failure was observed.
3. The operation is in the overwrite path.
4. The observed source identity matches the exact requested filename after removing only the final numeric duplicate suffix.

This does not weaken generic Project Source add verification and does not implement full canonical `pb src add` exact-name upsert semantics. The broader `pb src add` / `pbsa` bug report remains a separate exact-name idempotent upsert repair.

## Guardrails

- No Cloudflare or rate-limit bypass.
- No host-CDP/session-manager path.
- No copied-profile trust.
- Adoption remains refused unless all-all validation returns `GO`.

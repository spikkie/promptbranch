# v0.1.103.10.84 — restore normal file add and replace existing Project Sources by identity

## Scope

- Keep `pbsa <file>` unchanged.
- Preserve the strict all-all release gate, sentinel normalization, authoritative Project Sources preflight, Docker image reuse/cache behavior, canonical artifact naming, and fail-closed suffix rollback.
- Classify file-source mutations before touching Library.

## Transaction classes

1. **Fresh add** — no exact canonical source and no visible suffix family: upload normally; do not open Library or require Recently deleted.
2. **Exact source overwrite** — attempt an explicit Replace/Update/Upload new version/Change file action on the exact source card. Do not remove the source first. If no replacement action is exposed, return `project_source_replace_not_supported` without mutation.
3. **Proven collision** — visible numeric suffix family or backend-created suffix: keep exact rollback and targeted Library cleanup by captured file ID.

## Diagnostics

The replacement result records visible source actions, replacement mode, source identity/file ID before and after, upload response identities, canonical/suffix counts, and persistence proof.

## Safety

No host CDP/session manager, copied-profile trust, Cloudflare bypass, rate-limit bypass, Project deletion, or adoption without strict all-all GO.

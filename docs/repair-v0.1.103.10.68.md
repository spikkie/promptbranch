# v0.1.103.10.68 — release-live-continuous marks completed bootstrap/ask sentinel run as ok

## Scope

Repair-only candidate. Keep the v0.1.103.10.67 trusted direct-conversation behavior and fix the final success predicate.

## Change

When `release-live-continuous` has:

- `project_result.ok=true`
- bootstrap sub-result `status=completed`
- bootstrap answer exactly matching the bootstrap sentinel
- ask sub-result `status=completed`
- ask answer exactly matching the ask sentinel

then top-level output must be:

- `ok=true`
- `status=completed`
- `contains_expected_sentinel=true`
- no `failed_phase`

This covers live ChatGPT ask results that return a completed status and exact answer but omit an `ok=true` field.

## Non-goals

- No Cloudflare workaround.
- No host-CDP/session-manager.
- No copied-profile trust.
- No ChatGPT Project deletion.
- No browser action optimization.

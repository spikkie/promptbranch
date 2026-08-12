# v0.1.128.1.1.1 — Post-adoption control-projection completeness repair

## Baseline

Authoritative adopted/current baseline is `v0.1.128.1.1` with artifact SHA-256 `89fe16e498b3035f94db5375c7ef9ee924a9d82d15ce5790ef765658e0db6328`. Its live lifecycle proved `TESTED_GREEN`, `ACCEPTED`, and `ADOPTED_CURRENT`; `FINAL_VERIFIED` correctly failed because the derived tracked projection omitted the planned-after-next token from `status.md` and did not project `migration.md`.

## Repair scope

- Define one canonical `CONTROL_PROJECTION_PATHS` set in `promptbranch_project_control.py`.
- Include `docs/project/migration.md` in that projection contract.
- Project accepted/current, next-normal, and planned-after-next values generically into all dynamic projection documents.
- Make the lifecycle wrapper import the canonical projection paths rather than maintaining a duplicate allowlist.
- Preserve fail-closed `FINAL_VERIFIED`; no special case for `v0.1.130`.

## Non-goals

No new lifecycle states, compatibility shims, browser changes, release machinery, or external-application implementation. `v0.1.129` remains the next normal slice.

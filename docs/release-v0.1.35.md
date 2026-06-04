# Release v0.1.35 — focused development DoD and MVP-state guidance

## Summary

`v0.1.35` adds read-only focused-development DoD/MVP-state guidance to the release status surfaces.

## Scope

- Add `focused_development_dod` to `pb release status-guide --json`.
- Add `focused_development_dod` to `pb release checkpoint --json`.
- Surface focused-continue evidence separately from adoption-checkpoint evidence.
- Keep the guidance advisory and read-only.

## Non-goals

- No install behavior changes.
- No source upload behavior changes.
- No adoption behavior changes.
- No full-test behavior changes.
- No browser automation changes.

## Validation

Focused tests should prove that continue-mode checkpoint payloads expose `focused_development_dod.status`, that focused-continue DoD can be complete while adoption DoD remains incomplete, and that the adoption command remains advisory only.

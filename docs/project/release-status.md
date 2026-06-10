# Release Status

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.65 | normal | Release lifecycle config contract guard | accepted_current | focused release config / docs-status validation; full-test evidence not listed here | release lifecycle config guard established | b767eb3fd2deadd4d8b33d93df77644913057982173173bccd03ad4da9c5c670 |
| v0.1.66 | normal | Release doctor config-aware candidate ZIP precheck | accepted_current | focused release config, release doctor, docs-status, compile validation; full-test evidence not listed here | read-only candidate ZIP precheck established | 2b05556677346aa2f9e1d7449bb1c70fc0c54b8d7cd130f22b6e7083960ec8a3 |
| v0.1.67 | normal | Project MVP / DoD / Plan control surface migration | candidate | focused `tests/test_project_control_surface.py`; ZIP hygiene pending packaging result; full tests not run | DOD-001..DOD-007 move to done; DOD-008/DOD-011 remain open | pending adoption evidence |

## ZIP status values

Use only:

```text
planned
candidate
installed_not_current
accepted_current
rejected
superseded
repair_required
```

## Status rule

A ZIP becomes `accepted_current` only after adoption evidence confirms runtime, state artifact, state source, registry current, and consistency alignment.

# Release Status

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.66 | normal | Release doctor config-aware candidate ZIP precheck | accepted_current | adoption evidence supplied earlier | DOD-010 done at the time; later superseded by v0.1.68 baseline evidence | 2b05556677346aa2f9e1d7449bb1c70fc0c54b8d7cd130f22b6e7083960ec8a3 |
| v0.1.67 | normal | Project MVP / DoD / Plan control surface migration | superseded | focused control-surface validation | DOD-001..DOD-007 moved to done | superseded by v0.1.68 |
| v0.1.68 | normal | Project Sources add performance and transactional diagnostics | accepted_current | operator-provided full test report: verified, browser 22/0 failures, agent 21/0 failures | DOD-012 done; DOD-009 done; DOD-010 updated by adoption evidence | fd55f38e290d77b2fcae637721ecf2ca25a7d16ceb66954f1a5497cacc30ed6d |
| v0.1.69 | normal | Browser-profile busy retry and source-add idle barrier | accepted_current | operator-provided adoption/current evidence; full-test evidence not provided in adoption update | DOD-013 done; DOD-010 updated by adoption evidence; DOD-011 remained release-specific until adoption | 2132bec14263f3418cec5707211bd0931dd4d9928c7e8ae50bcb3e9fc3997b56 |
| v0.1.70 | normal | Multi-repo artifact registry state | accepted_current | focused artifact/state/CLI tests; project control-surface test; compileall; ZIP hygiene; operator adoption evidence | DOD-014 done; DOD-010 updated by adoption evidence | 99836251f6b07798d2e4c1e8bf978f001dccb0cced6fb64446dd7f098fe620e9 |
| v0.1.70.1 | repair | Missing repo artifact-current fallback repair | accepted_current | focused missing-repo/artifact-current tests; project control-surface test; compileall; ZIP hygiene; operator adoption evidence | DOD-015 done; no slice or line advanced | 24be7e1c993d69ffb3ae50fbd50a45edf8a1af07ed616b107ef895698fc1ed33 |
| v0.1.71 | normal | Project-scoped multi-repo registry resolution | accepted_current by operator statement | full tests/adoption stated by operator; explicit adoption JSON not recorded here | DOD-016 added/done after focused validation | pending explicit checksum evidence |
| v0.1.71.1 | repair | Project registry command alignment repair | candidate | project/repo focused tests; artifact-current regression tests; project control-surface test; compileall; ZIP hygiene; full tests not run here | DOD-017 added/done after focused validation; no slice or line advanced | pending adoption evidence |
| v0.1.71.2 | repair | Required root `.gitignore` packaging repair | rejected | install ZIP import guard failed: protected `.pb_profile/` entry present | DOD-018 done; no line advanced | rejected/superseded |
| v0.1.71.3 | repair | Protected ZIP entry hygiene | rejected | service health endpoint returned `v0.1.71.3` while release-control expected `0.1.71.3` | packaging hygiene preserved; no line advanced | rejected/superseded |
| v0.1.71.4 | repair | Service health version normalization | rejected | full release-control reached `package_import_smoke` and failed on `promptbranch_version.VERSION_TAG=vv0.1.71.4` | DOD-019 done; no line advanced | rejected/superseded |
| v0.1.71.5 | repair | `VERSION_TAG` double-v normalization | accepted_current | operator-provided `pb artifact current --json` adoption evidence; full-test evidence not included in adoption block | DOD-020 done; no line advanced; DOD-010 baseline evidence updated | c04b23d8a35bd07d1cb106a52beb0cf6d5e06ee788fec76ff69f0abd0d37d13c |
| v0.1.72 | normal | Project registry adoption/import ergonomics | candidate | focused project/repo import tests; project control-surface test; compileall; ZIP hygiene; clean extraction validation | DOD-021 done | pending |

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

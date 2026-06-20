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
| v0.1.72 | normal | Project registry adoption/import ergonomics | accepted_current | operator-provided `pb artifact current --json` adoption evidence; full-test evidence not included in adoption block | DOD-021 done; DOD-010 baseline evidence updated | de4dfec45d53bc1d05f129e2796e51b86468b00e911e8e9e9566d166b4f6acc1 |

| v0.1.73 | normal | Canonical artifact naming and adopt compatibility | candidate / field-proven | focused artifact/adopt tests; project control-surface test; compileall; ZIP hygiene; clean extraction validation; field-tested with candlecast multi-repo registry seeding | DOD-022 done | pending |
| v0.1.73.1 | repair | Canonical artifact adoption diagnostics and external-repo status semantics | accepted_current | operator-provided adoption/current evidence; full-test evidence later showed v0.1.73.1 release workflow exit 0 | DOD-023 done; no normal slice advanced | 3a032f2470a74903f6f61f9dbdf63dbf98e3154e2fd146e6ea9a757cf7941554 |
| v0.1.73.2 | repair | v0.1.73.1 validation/reporting regression repair | superseded | focused JSON-contract tests passed; full release-control failed with browser_profile_busy | DOD-024 superseded by DOD-025 | rejected/superseded |
| v0.1.73.3 | repair | Universal browser-operation scheduler coverage | superseded | release-control completed exit_code 0; focused scheduler test failed due ambient profile-state dependency | DOD-025 carried forward into v0.1.73.4 | superseded |

| v0.1.73.4 | repair | Focused scheduler test isolation | accepted_current | operator-provided `pb artifact current --all --json` adoption evidence; full-test evidence not included in adoption block | DOD-026 done; DOD-010 baseline evidence updated | a76aa4292bb8aba31c8223ae5342b6e9a731b4aef3a5505581d719d263fa1858 |
| v0.1.74 | normal | Release validation suite coverage manifest | repair_required | release-control failed because required pytest groups used installed Promptbranch runtime Python without pytest | DOD-027 done but candidate needs repair | pending |
| v0.1.74.1 | repair | Release-validation pytest runner isolation | repair_required | release-control failed in release-lifecycle plan tests due ambient profile state | DOD-028 done; DOD-029 required | pending |

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
| v0.1.74.2 | repair | Release-lifecycle plan test profile isolation | repair_required | release-control passed validation groups but failed live browser source remove under 120s source-mutation wait | DOD-029 done; DOD-030 required | pending |

| v0.1.74.3 | repair | Full integration source-mutation wait alignment | accepted_current | operator-pinned baseline for v0.1.75 rebase; full adoption JSON not present in this package build context | DOD-030 done; baseline advanced by operator instruction | pending |

| v0.1.75 | normal | KISS project/repo management command model | candidate | focused project/repo and artifact-current tests passed before packaging; release-control/adoption pending | DOD-031 done after focused validation; DOD-011 pending adoption | pending |

| v0.1.76 | normal | KISS repo-loop consumer cleanup for operator scripts and release-state checks | accepted_current | full release-control green; operator-provided adoption/current evidence | DOD-032 done; DOD-010 baseline evidence updated | 27030674c5af1b1d9d5199e638b55c2d3beed4b7df36175082e107992721d96f |

| v0.1.77 | normal | Repo-loop compatibility hardening and operator migration guardrails | repair_required | focused repo-loop/legacy fallback tests passed; full release-control failed in live browser temporary-project flow | DOD-033 done after focused validation; DOD-034 required | pending/rejected |
| v0.1.77.1 | repair | Temporary project create/remove lifecycle hardening | candidate | focused cleanup verification tests, create-submit disabled regression test, project control-surface tests, version tests, compileall, ZIP hygiene | DOD-034 done; no slice or line advanced | pending adoption evidence |

| v0.1.77.1 | repair | Temporary project create/remove lifecycle hardening | repair_required | release-control failed: cleanup verified project still present after sidebar-not-found; release-validation browser_scheduler_source_lifecycle timed out | DOD-034 done; DOD-035 required | pending/rejected |
| v0.1.77.2 | repair | Temporary project cleanup retry and release-validation isolation | repair_required | release-control failed: exact-name project still present but normal sidebar removal could not find configured project | DOD-035 done; DOD-036 required | pending/rejected |

| v0.1.77.3 | repair | Hidden temporary project removal hardening | candidate | focused project removal tests, cleanup retry tests, project control-surface tests, version tests, compileall, ZIP hygiene | DOD-036 done; no slice or line advanced | pending adoption evidence |

| v0.1.77.3 | repair | Hidden temporary project removal hardening | repair_required | release-control failed: exact-name project remained resolvable under ChatGPT 429/rate-limit pressure and cleanup could not remove it | DOD-036 done; DOD-037 required | pending/rejected |

| v0.1.77.4 | repair | Rate-limit-aware temporary project cleanup retry hardening | candidate | focused cleanup/remove tests, project control-surface tests, version tests, compileall, ZIP hygiene | DOD-037 done; no slice or line advanced | pending adoption evidence |

| v0.1.77.5 | repair | Required root `.gitignore` packaging repair | repair_required | release-control failed: cleanup still could not remove exact-name-resolvable temporary project; scheduler validation group timed out at 600 seconds | DOD-038 done; DOD-039 required | pending/rejected |
| v0.1.77.6 | repair | Project-page delete-menu fallback and bounded validation timeout | repair_required | full release-control failed at `project_remove_cleanup`; release-validation groups passed | DOD-039 done | pending |
| v0.1.77.7 | repair | Explicit resolved-project-url cleanup retry | repair_required | full release-control failed: Docker-service adapter did not accept explicit per-call project URL, so retargeted cleanup still could not remove exact-name-resolvable project | DOD-040 done; DOD-041 required | pending/rejected |

| v0.1.77.8 | repair | Docker-service cleanup retarget accepts explicit project URL | candidate | focused DockerServiceAdapter cleanup tests, project control/version tests, compileall, bash syntax, ZIP hygiene; full release-control pending | DOD-041 done | pending |
| v0.1.77.8 | repair | Docker-service cleanup retarget per-call project URL support | repair_required | full release-control failed: text source-add stale inflight after commit and cleanup still could not remove exact-name-resolvable project | DOD-041 done; DOD-042 required | pending/rejected |
| v0.1.77.9 | repair | Source-save stale-inflight proof and cleanup project-name forwarding | candidate | focused source-save quiet, cleanup/remove, service-client, project-control, version, compileall, ZIP hygiene checks | DOD-042 done; no normal slice advanced | pending adoption evidence |

| v0.1.77.9 | repair | Source-save stale-inflight proof and cleanup project-name forwarding | repair_required | full release-control failed before browser tests: Docker service version verification kept reporting stale `0.1.77.8` after normal and no-cache rebuild | DOD-042 done; DOD-043 required | pending/rejected |
| v0.1.77.10 | repair | Version-pinned Docker service image selection | candidate | focused shell-script tests, project control/version tests, compileall, bash syntax, ZIP hygiene; full release-control pending | DOD-043 done | pending |
| v0.1.77.11 | repair | Name-only non-anchor project cleanup fallback | candidate | focused project resolve/remove tests, project control/version tests, compileall, bash syntax, ZIP hygiene; full release-control pending | DOD-044 done | pending |


| v0.1.77.11 | repair | Name-only non-anchor project cleanup fallback | accepted_current | full release-control passed; adoption/current evidence confirmed runtime/state/source/registry consistency | DOD-044 done; v0.1.77 repair line closed | 825e3b3a5e2d36214ddcdeb6f97ece8601a82f35322a34c96a6e3e2bab78af44 |
| v0.1.78 | normal | AG-001 — Deterministic Artifact Guardian Guard | candidate | focused Artifact Guardian tests, project control/version tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-045 done after focused validation; DOD-011 pending adoption | pending |
| v0.1.79 | normal | Rebaselined JSON orchestration / k8s-game MVP foundation | planned | not run | no DoD movement yet | pending |

| v0.1.78 | normal | AG-001 — Deterministic Artifact Guardian Guard | repair_required | full release-control failed in `project_source_add_file`: file source persistence not verified after commit/stale-inflight evidence | DOD-045 done; DOD-046 required | pending/rejected |
| v0.1.78.1 | repair | Project Source mutation transaction hardening | candidate | focused repair tests, project control/version tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-046 done; no normal slice advanced | pending |

| v0.1.78.2 | repair | Project deletion safety freeze | candidate | focused delete-safety tests, project control/version tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-047 done; no normal slice advanced | pending |

| v0.1.78.2.1 | repair | Package delete-safety helper module | candidate | focused package/import tests, project control/version tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-047 preserved; no normal slice advanced | pending |

| v0.1.78.2.2 | repair | Release-control multi-segment repair-version compatibility | candidate | focused shell-script version-normalization tests, project control/version tests, protocol schema JSON test, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-048 done; DOD-047 preserved; no normal slice advanced | pending |

| v0.1.78.2.3 | repair | Retained quarantine project for delete-frozen release tests | accepted_current | release-control, visual-artifact-roundtrip, ask-live, release-live, import-smoke, artifact guard, and adoption/current evidence passed | DOD-049 done; DOD-047/DOD-048 preserved; no normal slice advanced | 3ea972e2a2e8c0906e48902749457c5054da5e67c506503d95b4cddf7615f13d |


| v0.1.78.2.4 | repair | Delete-frozen live-test profile alignment and one-command all-tests report | candidate | focused CLI/parser/live-test defaults, release-control all-tests shell validation, project control/version tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-050 done; DOD-047/DOD-049 preserved; no normal slice advanced | pending |


| v0.1.78.2.5 | repair | Run-all verdict accuracy and live-profile auth preflight | candidate | focused run-all/profile/parser tests, project control/version/delete-safety tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-051 done; DOD-047/DOD-049/DOD-050 preserved; no normal slice advanced | pending |
| v0.1.78.2.6 | repair | Docker build cache/provenance guard | candidate | focused shell/version/delete-safety tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-052 done; DOD-047/DOD-050/DOD-051 preserved | pending |

| v0.1.78.2.7 | repair | Docker provenance probe syntax repair | candidate | focused shell/version/delete-safety tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-053 done; DOD-047/DOD-050/DOD-051/DOD-052 preserved | pending |


| v0.1.78.2.8 | repair | Docker pyproject probe quoting repair | candidate | Fixes running-container pyproject probe quoting after v0.1.78.2.7 failed with `SyntaxError: invalid syntax`; focused regression validation passed before packaging. | pending |

| v0.1.78.2.9 | repair | Docker pyproject probe awk-dollar quoting repair | candidate | focused Docker probe quoting/version/delete-safety/project-control tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-055 done; DOD-047/DOD-050/DOD-051/DOD-052/DOD-053/DOD-054 preserved | pending |
| v0.1.78.2.10 | repair | Rate-limit modal recovery and cooldown-aware run-all policy | candidate | focused shell/version/delete-safety/project-control tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-056 done; DOD-052/DOD-055 preserved | pending |
| v0.1.78.2.11 | repair | Run-all profile seed preservation and strict rate-limit detection | candidate | focused shell/version/delete-safety/project-control tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-057 done; DOD-052/DOD-056 preserved | pending |

| v0.1.78.2.12 | repair | Text-source save trigger fallback and live-seed operator guard | candidate | focused Project Source fallback tests, project control/version/delete-safety tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-058 done; DOD-047/DOD-052/DOD-056/DOD-057 preserved; no normal slice advanced | pending |

| v0.1.78.2.13 | repair | Text-source compatibility isolation and focused failing-test mode | candidate | focused shell-script tests, project control/version/delete-safety tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-059 done; DOD-047/DOD-052/DOD-056/DOD-057/DOD-058 preserved; no normal slice advanced | pending |
| v0.1.78.2.14 | repair | Project Source remove containment guard | candidate | focused Project Source containment tests, project control/version/delete-safety tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-060 done; DOD-047/DOD-052/DOD-056/DOD-057/DOD-058/DOD-059 preserved; no normal slice advanced | pending |

| v0.1.78.2.15 | repair | Project Source add timeout false-negative / conversation-history cooldown containment | candidate | focused Project Source persistence/rate-limit modal tests, version metadata checks, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-061 done; DOD-047/DOD-052/DOD-056/DOD-057/DOD-058/DOD-059/DOD-060 preserved; no normal slice advanced | pending |

| v0.1.78.2.16 | repair | Project Source post-commit verification retry | candidate | focused Project Source stale-inflight recovery tests, version metadata checks, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-062 done; DOD-047/DOD-052/DOD-056/DOD-057/DOD-058/DOD-059/DOD-060/DOD-061 preserved; no normal slice advanced | pending |

| v0.1.78.2.17 | repair | `pb ask --prompt-file` button-first causal submit repair | candidate | focused prompt-file submit-policy/API/service/browser tests passed; compile check passed; smoke script syntax passed; full release-control/live smoke/adoption not run here | DOD-063 done; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.18 | repair | Prompt-file smoke diagnostics and strict button-dispatch causality | candidate | focused prompt-file submit-policy/smoke tests passed; compile check passed; bash syntax passed; ZIP hygiene passed; full release-control/live smoke/adoption not run here | DOD-064 done; DOD-063 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.19 | repair | Prompt-file submit policy automation-wrapper wiring | candidate | focused wrapper/API/service tests passed locally; compile check passed; ZIP hygiene passed; full release-control/live smoke/adoption not run here | DOD-065 done; DOD-063/DOD-064 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20 | repair | Prompt-file smoke contract and successful submit evidence flattening | candidate | focused prompt-file smoke/source tests passed locally; compile check passed; bash syntax passed; ZIP hygiene passed; full release-control/live smoke/adoption not run here | DOD-066 done; DOD-063/DOD-064/DOD-065 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.1 | repair | Release-control `--adopt-after-validation` flag support | candidate | focused shell-script tests, version tests, project-control tests, compile check, bash syntax, ZIP hygiene; full release-control/live adoption not run here | DOD-067 done; DOD-063 through DOD-066 preserved; no normal slice advanced | pending adoption evidence |

| v0.1.78.2.20.2 | repair | Large `pb ask --prompt-file` auto-attachment transport for prompt packages | candidate | focused CLI transport tests, version/project-control tests, compile check, bash syntax, ZIP hygiene; live large-prompt smoke/full release-control/adoption not run here | DOD-068 done; DOD-063 through DOD-067 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.3 | repair | Large prompt-file attachment diagnostics flattening | candidate | focused CLI attachment diagnostics test, attachment visible-answer top-level diagnostics test, version/project-control tests, compile check, bash syntax, ZIP hygiene; live large-prompt smoke/full release-control/adoption not run here | DOD-069 done; DOD-063 through DOD-068 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.4 | repair | Project Source text add document-conversion proof and retained-test capacity pruning | candidate | Focused local tests only; full release-control/adoption pending. |
| v0.1.78.2.20.5 | repair | Generic document-converted text source content-proof gate | candidate | focused Project Source text-document proof tests, version test, compile check, ZIP hygiene; live focused repro/full release-control/adoption not run here | DOD-071 done; DOD-063 through DOD-070 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.6 | repair | Dedicated generated document-name requirement for Project Source text conversion | candidate | focused Project Source/document-name tests, version test, compile check, ZIP hygiene; live focused repro/full release-control/adoption not run here | DOD-072 done; DOD-063 through DOD-071 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.7 | repair | Project Source text-add release gate split from document-conversion characterization | candidate | focused Project Source/version/control-surface tests and compile check; live focused repro/full release-control/adoption not run here | DOD-073 done; DOD-063 through DOD-072 preserved/superseded where noted; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.8 | repair | Strict ephemeral project cleanup, expected-missing classification, and scheduler/source lifecycle timeout repair | candidate | focused local pytest/compile/ZIP validation; live cleanup/source proof, full release-control, and adoption/current verification pending | DOD-074 done; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.8.1 | repair | Packaging-only root control-file repair for `.20.8`; includes required `.gitignore` in ZIP | candidate | focused local compile/version/control-surface/ZIP required-root validation; live cleanup/source proof, full release-control, and adoption/current verification pending | no DoD scope advanced beyond `.20.8`; packaging repair note added | pending adoption evidence |
| v0.1.78.2.20.8.2 | repair | Ephemeral project cleanup URL normalization repair | candidate | focused cleanup/normalization tests, project-control/version tests, compile checks, ZIP hygiene before operator live cleanup proof | DOD-075 done; DOD-074 preserved; no normal slice advanced | pending |

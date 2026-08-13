## v0.1.128.2.6.1.1.1 VERSION-derived structural-contract corrective

Accepted/current remains `v0.1.128.2.5` at SHA-256 `07c6e41d29e932e99d8eda20eeee35de92acdd567df6e529b51aee252fb70d58`. Immutable `v0.1.128.2.6.1.1` at SHA-256 `f23253e99d985906e7a24b61594efb6d3d39a011f2acda78e2c4bc7a49001553` reached independently verified `RUNTIME_PREPARED`; its exact package metadata/import smoke passed, then `TESTED_GREEN` failed deterministically in `validation.application_architecture_structural` because four portable-skill tests pinned `v0.1.128.2.6.1` instead of deriving the current release from `VERSION`. This repair removes those duplicate mutable version authorities and applies the same `VERSION` derivation to current project-control assertions. External-application scope remains blocked; `v0.1.129` is still next normal after acceptance. Active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.1.zip`.

Construction proof: Exact clean-extraction structural coverage is 62/62 nodeids green (29 application architecture, 14 migration, 8 tool-authoring, 7 learning, 4 skill-sync) using pytest 9.0.2 with ambient plugin autoload disabled. The artifact container could not retain the one-process aggregate long enough for a summary, so canonical host lifecycle must still rerun the normal single structural group.

## v0.1.128.2.6.1.1 packaging/import-surface corrective

Active repair from accepted/current `v0.1.128.2.5`. `v0.1.128.2.6` (`4ac66b37…`) and distributed `v0.1.128.2.6.1` are preserved as historical failed candidates. This corrective declares `promptbranch_skill_sync` in setuptools package metadata and binds canonical candidate testing to the exact release ZIP through `--package-zip`, closing the source-tree-masking validation gap. Live lifecycle/adoption remains open. Active artifact: `chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.zip`.
<!-- promptbranch-live-control-projection -->
> Live control projection after adoption: accepted/current `v0.1.128.2.6.1.1.1` (`chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.1.zip`), SHA-256 `90c36f8065d0d343f7a7d6f8e6a11577f8e02ba683d24a026ccb48a755fc5926`. Active next normal slice is `v0.1.129 — External application pilot bootstrap` with artifact `chatgpt_claudecode_workflow-2_v0.1.129.zip`. Planned after acceptance is `v0.1.130 — Controlled external application change execution` (`v0.1.130`) with artifact `chatgpt_claudecode_workflow-2_v0.1.130.zip`.

<!-- promptbranch-release-construction-baseline -->
> Construction baseline: adopted/current `v0.1.128.2` (`chatgpt_claudecode_workflow-2_v0.1.128.2.zip`), SHA-256 `6c5270cdfae93810e35e5c54eea031cb35fc074cdf0c852f9db3f692896ed9b6`. Active repair is `v0.1.128.2.5 — Authoritative baseline auto-resolution repair`. Next normal is `v0.1.129`; planned after it is `v0.1.130`.

# Active release status — v0.1.128.2.5

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.128.2.5 | repair | authoritative baseline auto-resolution | construction candidate | lifecycle resolver regressions + preserved recovery/skills + canonical groups + deterministic ZIP/Guardian required | DOD-574–576 construction; DOD-577 live | — |
| v0.1.128.2.4 | repair | accepted-baseline exact-byte self-healing | repair-required predecessor | live startup exposed stale operator baseline assertion despite authoritative current v0.1.128.2 | DOD-570–572 preserved; DOD-573 superseded | — |

Current accepted baseline: `chatgpt_claudecode_workflow-2_v0.1.128.2.zip` (`v0.1.128.2`).  
Accepted SHA-256: `6c5270cdfae93810e35e5c54eea031cb35fc074cdf0c852f9db3f692896ed9b6`.  
Active repair candidate: `chatgpt_claudecode_workflow-2_v0.1.128.2.5.zip`.  
Next normal slice after repair: `v0.1.129 — External application pilot bootstrap`.  
Planned after that: `v0.1.130 — Controlled external application change execution`.

---

|---|---|---|---|---|---|
| v0.1.128.2.4 | repair | self-heal exact accepted baseline bytes by immutable SHA and restore canonical object storage | construction candidate | exact-byte recovery regressions + preserved timeout/runtime/project-registry recovery + 17 canonical groups + deterministic ZIP/Guardian required | DOD-570–572 construction; DOD-573 live | — |
| v0.1.128.2.3 | repair | project-scoped baseline registry authority | immutable repair-required predecessor | construction green; live startup reached accepted record then failed on physical accepted-byte validation | DOD-566–568 preserved; DOD-569 superseded by v0.1.128.2.4 closure | — |
| v0.1.128.2.2 | repair | auto-reconcile accepted runtime from exact adopted artifact before candidate preparation | immutable repair-required predecessor | construction green; live startup exposed wrong registry namespace (`profile_dir` instead of project registry) | DOD-561–564 preserved; DOD-565 superseded by v0.1.128.2.3 closure | — |
| v0.1.128.2.1 | repair | release smoke timeout auto-recovery; v0.1.128.2 learning/skills unchanged | immutable repair-required predecessor | construction green; live startup blocked by accepted-runtime baseline mismatch before candidate preparation | DOD-555–559 preserved; DOD-560 superseded by v0.1.128.2.2 closure | — |
| v0.1.128.2 | normal | Promptbranch learning and skills completeness | immutable repair-required predecessor | learning/operator construction green; live adoption deferred through repair chain | DOD-547–553 preserved; DOD-554 superseded by repair-chain live closure | — |
Current accepted baseline: `chatgpt_claudecode_workflow-2_v0.1.128.1.1.1.1.1.zip` (`v0.1.128.1.1.1.1.1`).  
Accepted SHA-256: `dd9ed8949990b1b143e7930a2357adbebaccb935744a5bc30342942dbccdcdbd`.  
Active repair candidate: `chatgpt_claudecode_workflow-2_v0.1.128.2.4.zip`.  
Next normal slice after repair: `v0.1.129 — External application pilot bootstrap`.  
Planned after that: `v0.1.130 — Controlled external application change execution`.

---

> Construction baseline: adopted/current `v0.1.128.1.1.1.1.1` (`chatgpt_claudecode_workflow-2_v0.1.128.1.1.1.1.1.zip`), SHA-256 `dd9ed8949990b1b143e7930a2357adbebaccb935744a5bc30342942dbccdcdbd`. Active normal learning-completeness slice is `v0.1.128.2 — Promptbranch learning and skills completeness`; next planned slice after acceptance is `v0.1.129 — External application pilot bootstrap`.

# Active release status — v0.1.128.2

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.128.2 | normal | Promptbranch learning and skills completeness | construction candidate | learning/operator focused tests + 17 canonical groups + deterministic ZIP/Guardian required | DOD-547–552 construction proven; DOD-553–554 pending | — |

Current accepted baseline: `chatgpt_claudecode_workflow-2_v0.1.128.1.1.1.1.1.zip` (`v0.1.128.1.1.1.1.1`).  
Accepted SHA-256: `dd9ed8949990b1b143e7930a2357adbebaccb935744a5bc30342942dbccdcdbd`.  
Active normal candidate: `chatgpt_claudecode_workflow-2_v0.1.128.2.zip`.  
Next planned slice after acceptance: `v0.1.129 — External application pilot bootstrap`.

---

> Construction baseline: adopted/current `v0.1.128.1.1` (`chatgpt_claudecode_workflow-2_v0.1.128.1.1.zip`), SHA-256 `89fe16e498b3035f94db5375c7ef9ee924a9d82d15ce5790ef765658e0db6328`. Active bounded repair is `v0.1.128.1.1.1.1.1`; next normal slice remains `v0.1.129 — External application pilot bootstrap`.

# Active release status — v0.1.128.1.1.1.1.1

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.128.1.1.1.1.1 | repair | task/message response-chain diagnostic capture; no response-selection change | deterministic construction candidate; live diagnostic proof pending | response/container diagnostic tests + canonical groups required; live task_message_flow evidence pending | diagnostic-only repair | — |
| v0.1.128.1.1.1 | repair | post-adoption control-projection completeness | immutable repair-required predecessor | construction green; live full + focused ask reproduce response-continuity timeout | DOD-539–541 construction proven; DOD-542 superseded | — |

Current accepted baseline: `chatgpt_claudecode_workflow-2_v0.1.128.1.1.zip` (`v0.1.128.1.1`).
Accepted SHA-256: `89fe16e498b3035f94db5375c7ef9ee924a9d82d15ce5790ef765658e0db6328`.
Active repair candidate: `chatgpt_claudecode_workflow-2_v0.1.128.1.1.1.1.1.zip`.
Next normal slice after repair: `v0.1.129 — External application pilot bootstrap`.

---

# Active release status — v0.1.128.1

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.128.1 | repair | Single authority for Promptbranch release artifacts | construction worktree; exact ZIP pending | focused artifact-authority tests green; canonical full matrix pending | DOD-524–531 construction in progress; DOD-532–533 pending | — |
| v0.1.128 | normal | PB environment authority cleanup, hardening and freeze | accepted/current, FINAL_VERIFIED | 17/17 canonical groups + deterministic ZIP/Guardian + full live lifecycle + independent final verify + fresh current green | DOD-516–523 closed | `5d1d64e8d146a3bf58f388149d6a917982239c1dbb9e2f5256f3ef33ba9abaac` |

Documentation checkpoint: `PB-ARTIFACT-AUTHORITY-2026-08-11.1`

Current accepted baseline: `chatgpt_claudecode_workflow-2_v0.1.128.zip` (`v0.1.128`).
Accepted SHA-256: `5d1d64e8d146a3bf58f388149d6a917982239c1dbb9e2f5256f3ef33ba9abaac`.
Active repair candidate: `chatgpt_claudecode_workflow-2_v0.1.128.1.zip`.
Next normal slice after repair: `v0.1.129 — External application pilot bootstrap`.

---

# Active release status — v0.1.128

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.128 | normal | PB environment authority cleanup, hardening and freeze | `chatgpt_claudecode_workflow-2_v0.1.128.zip` construction candidate | source-tree + exact extracted ZIP 17/17 canonical groups green; deterministic rebuild and Guardian green; final byte freeze revalidation required | DOD-516–522 construction-proven; DOD-523 live pending | — |
| v0.1.127.2.1 | repair | Consolidated v0.1.127 closure | accepted/current, FINAL_VERIFIED | live lifecycle + independent all-state verify + fresh scoped current green | DOD-510–515 closed | `33bbf8ca2dc458ee6c6fa9ea816cc4ca8aa9cc91b7711b9c83dc3764426f5d75` |
| v0.1.127.2 | repair | Consolidated v0.1.127 closure and single-Python lifecycle repair | `chatgpt_claudecode_workflow-2_v0.1.127.2.zip` immutable repair-required | operator canonical validation exposed 14 release_pipeline failures because test fake still required `Path(sys.executable).resolve()`; no live attempt started | DOD-510–513 preserved; DOD-514 not satisfied | repair_required |
| v0.1.127.1.1.1 | repair | Successor ask pin propagation and TESTED_GREEN route verification | immutable predecessor | live 53/53 + exact route verified; ACCEPTED blocked before mutation by undefined helper | DOD-499–502 route proof | repair_required |
| v0.1.127.1.1.1.1.1 | repair | Single Python authority and acceptance-path repair | `chatgpt_claudecode_workflow-2_v0.1.127.1.1.1.1.1.zip` repair-required | live RUNTIME_PREPARED exposed venv launcher collapse to `/usr/bin/python3.12`; no runtime prepared | DOD-506–509 superseded by v0.1.127.2 | repair_required |
| v0.1.127.1.1.1.1 | repair | Acceptance-path conversation provenance validator repair | `chatgpt_claudecode_workflow-2_v0.1.127.1.1.1.1.zip` immutable predecessor | construction green; superseded before live by single-Python operator invariant | DOD-503–504 preserved | superseded_before_live |
| v0.1.127.1.1 | repair | Canonical ChatGPT project identity for artifact conversation provenance | `chatgpt_claudecode_workflow-2_v0.1.127.1.1.zip` repair-required | live 53/53 used generated itest conversation instead of baseline provenance | DOD-498 superseded by .1.1.1 route proof | — |
| v0.1.127.1 | repair | Artifact-bound conversation provenance and successor ask routing | `chatgpt_claudecode_workflow-2_v0.1.127.1.zip` repair-required | live legacy bind exposed project-slug normalization defect | DOD-495 superseded by .1.1 proof | — |
| v0.1.127 | normal | Portable tool-authoring/export | `chatgpt_claudecode_workflow-2_v0.1.127.zip` repair-required | live ask failed twice | DOD-490 open | — |
| v0.1.126.1.1.1.1.3 | repair | Python validation authority | accepted/current | FINAL_VERIFIED | DOD-484 closed | `07ed977b948dd2b8779a93ff74512817e75ba9cbb3f2bdbdb87351b838dbf0e7` |

> v0.1.127 normal-slice authority: accepted/current is `v0.1.126.1.1.1.1.3`; active repair candidate is `v0.1.127.2.1`. The underlying normal slice remains `v0.1.127`; tool authoring/export is PB-environment scope only and grants no execution authority.

# Release Status

Documentation checkpoint: `PB-TOOL-AUTHORING-2026-08-09.1`

Current accepted baseline: `chatgpt_claudecode_workflow-2_v0.1.127.2.1.zip` (`v0.1.127.2.1`).
Accepted SHA-256: `33bbf8ca2dc458ee6c6fa9ea816cc4ca8aa9cc91b7711b9c83dc3764426f5d75`.
Active candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.128.zip`.
Active normal slice: `v0.1.128 — PB environment authority cleanup, hardening and freeze`.
Next normal slice: `v0.1.128 — PB environment authority cleanup, hardening and freeze`.
Next planned slice after acceptance: `v0.1.129 — External application pilot bootstrap`.

| Version | Type | System | Slice | Status |
|---|---|---|---|---|
| v0.1.125.3.4.2 | repair | PB control plane | post-adoption historical verification and final convergence | superseded |
| v0.1.126 | normal | PB environment | persistent whole-release ETA estimator | completed_via_repair |
| v0.1.126.1.1.1.1.2 | repair | PB environment | accepted-runtime precondition and preservation | repair_required |
| v0.1.126.1.1.1.1.3 | repair | PB environment | validation-Python authority propagation / v0.1.126 final convergence | accepted_current |
| v0.1.127 | normal | PB environment | portable tool-authoring skill/export | candidate_built |
| v0.1.128 | normal | PB environment | hardening and environment contract freeze | planned_after_acceptance |
| v0.1.129 | normal | external application | read-only pilot bootstrap | planned |
| v0.1.130 | normal | external application | controlled first change | planned |
| v0.1.131 | normal | external application | test/diagnose/correct loop | planned |
| v0.1.132 | normal | external application | candidate and acceptance lifecycle | planned |
| v0.1.133 | normal | external application | non-production deployment proof | planned |
| v0.1.134 | normal | PB application platform | reusable/multi-repository workflow | planned |

## Current v0.1.127 authority

Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.3.zip` (`v0.1.126.1.1.1.1.3`), SHA-256 `07ed977b948dd2b8779a93ff74512817e75ba9cbb3f2bdbdb87351b838dbf0e7`.

Active normal candidate: `chatgpt_claudecode_workflow-2_v0.1.127.zip` (`v0.1.127`) — tracked `promptbranch-tool-authoring` skill, deterministic tool-spec schema/semantic validator, and reproducible portable bundle for ChatGPT Project Sources and coding agents. Authoring grants no execution authority. Next planned slice after acceptance: `v0.1.128 — PB environment MVP hardening and freeze`.

## Status rule


A ZIP becomes `accepted_current` only after strict validation and adoption evidence confirm runtime, canonical artifact hash, exact assigned Project Source, registry current, state artifact/source and consistency alignment. A release-set recovery may mutate only after a read-only reconciliation proves every repository is exactly at its target or pre-rollout identity and the operator confirms the exact reconciliation SHA-256.

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
| v0.1.78.2.20.8.3 | repair | Slugged ephemeral cleanup identity and text-source post-commit recovery | candidate | focused cleanup/source/full-integration/version/control-surface tests, compile check, ZIP hygiene; live focused rerun/full release-control/adoption not run here | DOD-076 done; DOD-073 through DOD-075 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.8.4 | repair | Immutable Project deletion freeze / remove same-run cleanup exception | candidate | focused delete-safety/full-integration cleanup/private browser-operation/version/control-surface tests, compile check, ZIP hygiene; live release-control/adoption not run here | DOD-077 done; DOD-076 text-source recovery preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.8.5 | repair | Project deletion cleanup-policy evidence label consistency | candidate | focused full-integration harness/delete-safety/version/control-surface tests, compile check, shell syntax, stale-label grep, ZIP hygiene; live release-control/adoption not run here | DOD-078 done; DOD-077 no-delete invariant preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.8.6 | repair | Project-scoped state authority for joined repos | candidate | focused project/repo state tests, version/control-surface tests, compile check, shell syntax, ZIP hygiene; live release-control/adoption not run here | DOD-079 done; DOD-077/DOD-078 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.8.7 | repair | Plain-text response wait deadline diagnostic guard | candidate | focused response-wait deadline regression, JSON deadline companion regression, version/control-surface tests, compile check, shell syntax, ZIP hygiene; live release-control/adoption not run here | DOD-080 done; DOD-077/DOD-078/DOD-079 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.78.2.20.8.8 | repair | Localhost source-add stale-inflight diagnostic timeout alignment | candidate | focused service-client/full-integration/project-source/version/control-surface tests, compile check, shell syntax, ZIP hygiene; live release-control/adoption not run here | DOD-081 done; DOD-077/DOD-078/DOD-079/DOD-080 preserved; no normal slice advanced | pending adoption evidence |

| v0.1.78.2.20.8.8 | repair | Localhost Project Source add stale-inflight diagnostic timeout alignment | accepted_current | full `--run-all-tests --strict-source-kind-matrix`; artifact guard; adoption/current evidence verified runtime/state/source/registry consistency | DOD-081 done; repair line closed | 472b9247d124728dd7c3da6a6d3c96fa17745f77906c162a5286495e70c75e9c |
| v0.1.79 | normal | JSON orchestration event intake foundation | candidate | focused event-intake/orchestration tests, project-control/version tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-082 done; normal MVP line resumed from accepted/current v0.1.78.2.20.8.8 | pending adoption evidence |

| v0.1.80 | normal | Accepted-event validation foundation | candidate | accepted-event/orchestration tests including installed-module runtime-path regression, project-control/version tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-083 done locally; normal MVP line continues from accepted/current v0.1.79 | pending adoption evidence |
| v0.1.81 | normal | Accepted-event dry-run promotion foundation | focused_candidate | installed-module dry-run command, accepted-event validation reuse, no-mutation authority tests, version/control-surface checks, compileall, shell syntax, ZIP hygiene before operator install | DOD-084 focused; accepted/current remains v0.1.79 until promotion gate | pending adoption evidence |
| v0.1.82 | normal | Accepted-event dry-run explicit input support | focused_candidate | installed-module explicit input dry-run command, explicit-path fail-closed tests, version/control-surface checks, compileall, shell syntax, ZIP hygiene before operator install | DOD-085 focused; accepted/current remains v0.1.79 until promotion gate | pending adoption evidence |

| v0.1.82 | focused working candidate correction | not accepted/current | Explicit accepted-event dry-run now resolves repo-relative input from the worktree in installed runtime instead of `site-packages/docs/...`; no ledger/write/adoption/deployment authority. |
| v0.1.83 | normal | Accepted-event ledger design scaffold | focused_candidate | local ledger-status smoke, explicit dry-run smoke, changed-code pytest, compileall, shell syntax, artifact guard; full all-tests/adoption deferred | DOD-086 done; DOD-083/DOD-084/DOD-085 preserved | pending adoption evidence |
| v0.1.84 | normal | Accepted-event ledger validation command | focused_candidate | local validate-ledger smoke, ledger absent-valid/invalid-JSONL/worktree-path tests, version/control-surface checks, compileall, shell syntax, artifact guard; full all-tests/adoption deferred | DOD-087 focused; DOD-083/DOD-084/DOD-085/DOD-086 preserved | pending adoption evidence |

| v0.1.84.1 | repair | Fresh delete-frozen test Project per validation run | candidate | focused parser/CLI/release-control shell tests, compileall, bash syntax, ZIP hygiene before operator install/runtime validation | DOD-088 focused; v0.1.84 ledger scope preserved | pending |


## v0.1.84.2 repair note

`v0.1.84.2` is a repair-only candidate on top of focused `v0.1.84.1`. It changes live/browser 429 modal handling so history-sensitive operations click `Got it`, wait the configured acknowledgement cooldown, and continue polling instead of failing on a short modal timeout. It does not advance ledger/write/orchestration scope and does not re-enable ChatGPT Project deletion. Accepted/current remains `v0.1.79` until later adoption/current evidence exists.


## v0.1.84.3 repair status

Uploaded `release_control.v0.1.84.2.run_all_tests.log` ended after the release-control rate-limit retry wait line, so it did not prove a second retry failure. It did prove a release-blocking first-attempt failure in `project_ensure_create_or_reuse`: after 429 modal acknowledgement and cooldown, the ChatGPT create-project submit button stayed disabled after the project name was filled. `v0.1.84.3` repairs only that browser recovery path by adding bounded create-project disabled-submit recovery: check/acknowledge rate-limit modal again, wait configured cooldown, clear/refill the project name, dispatch input/change/keyup/blur events, tab out, reacquire the submit button, and retry enablement before failing closed with structured disabled-state logs. Project deletion remains frozen; ledger/write/orchestration scope does not advance.


## v0.1.84.4 repair status

ChatGPT Project names are limited to 50 characters. `v0.1.84.4` repairs generated test Project naming only: release-control and live-test generated names are capped at 50 characters while preserving run-scoped uniqueness through a stable hash suffix when truncation is required. Explicit `PROMPTBRANCH_RELEASE_TEST_PROJECT_NAME` values longer than 50 characters now fail fast. Project deletion remains frozen; ledger/write/orchestration scope does not advance.


## v0.1.84.5 repair status

The v0.1.84.4 full all-tests/adoption gate returned `FIX` because `visual_artifact_roundtrip` failed with `artifact_candidate_not_selected`: the ChatGPT reply envelope was near-complete but invalid JSON in one attempt due raw nested quotes inside a validation string, and another attempt had a balanced JSON object followed by a truncated `END_PROMPTBRANCH_REPLY_JSON` marker fragment. `v0.1.84.5` repairs only the visual artifact reply-envelope surface: the prompt now asks for simple validation strings without arrays/raw quotes/Markdown links, and the reply parser accepts a balanced JSON object followed only by a truncated end-marker fragment while still rejecting genuinely malformed JSON. Project deletion, ledger/write/orchestration, Project Source, artifact adoption/current, deployment, and model-execution scope do not advance.

## v0.1.84.5.1 repair status

`v0.1.84.5.1` repairs live-test Project identity and visual-roundtrip timing evidence only. `ask-live`, `visual-artifact-roundtrip`, and `release-live` now create a fresh Project with `create_project()` for mutation-capable default/`--project-name` test setup and carry the returned Project URL/id forward; they do not resolve by non-unique ChatGPT Project display name. `--conversation-url` remains the exact existing-target bypass. `pb test visual-artifact-roundtrip --json` now includes `phase_timings` for input ZIP creation, Project setup, ask, reply parse, artifact download, smoke verification, cleanup when applicable, and total elapsed time. Project deletion remains frozen; ledger/write/orchestration, Project Source, artifact adoption/current, deployment, and model-execution scope do not advance.

## v0.1.84.5.2 repair status

`v0.1.84.5.2` repairs live-test 429 telemetry propagation and non-clean validation classification only. `/v1/ask` now preserves browser-service `rate_limit_telemetry`; `pb test ask-live --json` and `pb test visual-artifact-roundtrip --json` surface rate-limit telemetry; otherwise functional live-test runs that observe backend/history `429` or ChatGPT rate-limit modal telemetry now report `status=rate_limited_contaminated` and `ok=false` instead of clean `verified`. Functional artifact evidence remains visible through `functional_status`, `verification_status`, and artifact-intake details. Project deletion remains frozen; ledger/write/orchestration, Project Source, artifact adoption/current, deployment, and model-execution scope do not advance.


## v0.1.84.5.3 repair status

`v0.1.84.5.3` repairs rate-limit telemetry aggregation evidence only. `v0.1.84.5.2` remains functionally correct for downgrade behavior; this repair deduplicates repeated event-backed telemetry snapshots from visual artifact download/smoke-verification result carrying so top-level wait/event totals are reliable. It does not change Project deletion, Project creation identity, `/v1/ask` telemetry propagation, non-clean 429 classification, Project Source, artifact adoption/current, ledger/write/orchestration, deployment, or model-execution scope.

| v0.1.84.5.3 | repair | Rate-limit telemetry aggregation deduplication | candidate | focused helper/CLI tests, py_compile, project-control/version tests, artifact guard before operator install | DOD-091 focused; v0.1.84.5.2 downgrade semantics preserved | pending adoption evidence |


| v0.1.84.5.4 | repair | Recovered 429 live-test continuation policy | candidate | focused rate-limit/visual/ask-live tests, version/control-surface tests, compileall, shell syntax, artifact guard before operator install | no slice advanced | pending adoption evidence |


| v0.1.84.5.5 | repair | Release-control recovered-rate-limit retry suppression | candidate | focused shell-policy tests, version/control-surface tests, compileall, shell syntax, validate-ledger, artifact guard before operator install | no slice advanced | pending adoption evidence |

## v0.1.84.5.6 repair note

`v0.1.84.5.6` repairs release-control `--run-all-tests` live Project reuse on top of `v0.1.84.5.5`. The run-all live phase now ensures one run-scoped ChatGPT Project once after live profile preflight and passes the returned Project URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This prevents every live subtest from creating a separate retained Project while preserving delete-frozen safety, 50-character Project name caps, project-create recovery, recovered 429 retry suppression, and visual artifact reply-envelope hardening. No ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.7 repair note

`v0.1.84.5.7` repairs the shared live Project ensure command introduced in `v0.1.84.5.6`. Release-control `--run-all-tests` now uses the supported top-level `pb project-ensure` command to create or resolve one run-scoped ChatGPT Project, extracts the returned Project URL, and passes that exact URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This preserves the one-Project-per-full-test-run policy without calling the unsupported nested `pb project ensure` surface. No project deletion, ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.
| v0.1.84.5.8 | repair | Browser service recovery after full-test ReadTimeout before later browser-backed phases | candidate | focused shell tests for ReadTimeout recovery/preflight retry, shared Project reuse tests, recovered-rate-limit no-retry tests, version/control-surface tests, compileall, bash syntax, validate-ledger smoke, Artifact Guardian, ZIP hygiene; full all-tests/adoption not run here | DOD-094 done; DOD-092/DOD-093 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.84.5.9 | repair | Live Project ensure URL extraction and recovered-429 success handling | candidate | focused live-project-ensure recovered-rate-limit shell test, shared Project reuse tests, recovered-rate-limit retry suppression tests, ReadTimeout recovery tests, version/control-surface tests, compileall, bash syntax, validate-ledger smoke, Artifact Guardian, ZIP hygiene; full all-tests/adoption not run here | DOD-095 done; DOD-092/DOD-093/DOD-094 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.84.5.10 | repair | Localhost validation isolation and ask-live streaming completion hardening | candidate | focused ask-live streaming-timeout tests, release-validation duplicate-skip/isolation tests, strict rate-limit selector-probe test, shared Project reuse test, compileall, bash syntax, validate-ledger smoke, Artifact Guardian, ZIP hygiene; full all-tests/adoption not run here | DOD-096 done; DOD-092/DOD-093/DOD-094/DOD-095 preserved; no normal slice advanced | pending adoption evidence |
| v0.1.84.5.10.1 | repair | Localhost/offline browser cooldown retry denylist | candidate | bash syntax, Python test compile, focused shell-script source regression for `full_localhost` denylist; full all-tests/adoption not run here | DOD-097 focused; no normal slice advanced | pending adoption evidence |
| v0.1.84.5.10.2 | repair | Direct retry restoration and recovered-rate-limit summary selection | candidate | focused shell-script tests, version tests, project-control tests, bash syntax, Python compile, Artifact Guardian; full all-tests/adoption not run here | DOD-098 focused; no normal slice advanced | pending adoption evidence |
| v0.1.84.5.10.3 | repair | Ask-live recovered-success summary classification | candidate | focused fake-command run-all tests for recovered ask-live green and functional-failure red, existing recovered ask-live/top-level selection tests, version tests, project-control tests, bash syntax, Python compile, Artifact Guardian; full all-tests/adoption not run here | DOD-099 focused; no normal slice advanced | pending adoption evidence |

| v0.1.84.5.11 | normal | Live validation diagnostics and source-add timeout observability | accepted_current_by_operator_log | full run-all strict-source-kind-matrix release workflow exit_code=0 with adopt_after_validation=1 supplied by operator | DOD-100 focused; builds from accepted/current v0.1.84.5.10.3 | current by operator statement; no local pb current JSON available in this build environment |

| v0.1.84.5.12 | normal | Explicit new-task ask mode | candidate | focused new-task parser/backend/browser/state tests, ask service/direct regressions, help grep, compileall, project-control, Artifact Guardian, ZIP hygiene | DOD-101 focused; builds from user-declared accepted/current v0.1.84.5.11 | pending full release-control/adoption evidence |
| v0.1.84.5.12.1 | repair | Recovered ask-live summary classification | candidate | focused shell summary tests, shell syntax, compileall, Artifact Guardian, ZIP hygiene | Repairs v0.1.84.5.12 release-control classification only; no slice/line advanced | pending full release-control/adoption evidence |
| v0.1.84.5.12.2 | repair | Deterministic browser_scheduler_source_lifecycle release-validation nodeids and accepted explicit new-task ask line | accepted_current | operator-provided full release-control/adoption/current evidence; all_tests_final_verdict=GO; Artifact Guardian passed; `pb artifact current --json` aligned runtime/source/artifact/registry | Completes v0.1.84.5.12 explicit new-task ask mode line | 1f6aca626d8993c1a1a953ecd2fd5a426bb28c24c5e0615be90a6628a570e44e |

| v0.1.85 | normal | Ask state observability and new-task proof hardening | candidate | focused tests and candidate ZIP validation pending full release-control/adoption | Adds schema-v2 state proof observability; no browser/adoption behavior change | pending |

| v0.1.86 | normal | K8s-game orchestration plan reconciliation | candidate | focused project-control/orchestration-doc tests before full release-control | DOD-104 focused | pending |
| v0.1.86 | normal | Loop skeleton/K8s-game planning transition baseline | accepted_current | operator-provided `--run-tests --adopt-after-validation` evidence; not full run-all-tests green | DOD-104 accepted via direct validation | c1f298608f8fd70effb42d418ae6970c20abc45d21f16115188ff36eb8dce3ad |
| v0.1.87 | normal | Loop target schema and dry-run planner | candidate | focused loop/schema/CLI tests before release-control | DOD-105 focused | pending |

| v0.1.87.1 | repair | Package `promptbranch_loop` for installed CLI | candidate | focused packaging/loop/version/project-control tests plus isolated pip install smoke, Artifact Guardian, ZIP hygiene | repairs v0.1.87 packaging only; no slice advanced | pending adoption evidence |

| v0.1.88 | normal | Incremental release validation evidence reuse | candidate | focused shell contract tests, version tests, project-control tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene | DOD-107 focused | pending adoption evidence |

| v0.1.88.1 | repair | Project-source-add-text timeout diagnostics/recovery | candidate | focused full-integration harness tests, version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene | repairs v0.1.88 source-add timeout gate only; no slice advanced | pending adoption evidence |
| v0.1.89 | normal | Live validation timing visibility and shortest-path click audit | accepted_current_by_operator_log | operator-provided `--run-tests --adopt-after-validation` evidence; `pb test report` confirmed timing summary and browser-action audit output | DOD-109 accepted via direct validation; builds from accepted/current v0.1.88.1 | current baseline for v0.1.90 |

| v0.1.90 | normal | Conversation-history/backend-api 429 pressure reduction | candidate | focused conversation-history request shield tests, test-report shield summary tests, version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene | Adds DOD-110 focused; builds from accepted/current v0.1.89 | pending adoption evidence |

| v0.1.90.1 | repair | Project source overwrite stale-inflight post-commit recovery | accepted_current_by_operator_log | focused source-overwrite stale-inflight tests, version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene | repairs v0.1.90 overwrite-file verification only; no slice advanced | pending adoption evidence |

| v0.1.91 | normal | Run-all evidence reuse proof and localhost matrix cooldown audit | candidate | focused shell tests for proof-based reuse and localhost cooldown audit, version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene | Adds DOD-112 focused; builds from accepted/current v0.1.90.1 | pending adoption evidence |


| v0.1.91.1 | repair | Ask-live first-turn retry recovery and run-all step aggregation correctness | accepted/current | run-tests/adopt retry passed; Project Source add/verify, pb test full, release validation groups, smoke, artifact current alignment | no slice advanced; v0.1.91 evidence reuse and localhost cooldown audit preserved | run-all proof exposed remaining final-summary aggregation defect repaired by v0.1.91.2 |
| v0.1.91.2 | repair | Run-all final summary aggregation live-step payload selection repair | candidate | focused pretty-live-JSON summary regression, evidence reuse/localhost audit tests, version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene | no slice advanced; v0.1.91.1 ask-live retry and v0.1.91 evidence reuse preserved | pending adoption evidence |

## v0.1.91.3 repair candidate

| Field | Value |
|---|---|
| Version | `v0.1.91.3` |
| Type | repair candidate |
| Base accepted/current | `chatgpt_claudecode_workflow-2_v0.1.91.1.zip` |
| Preserved repair candidate | `chatgpt_claudecode_workflow-2_v0.1.91.2.zip` |
| Scope | Docker service clean-system recreate/version verification hardening |
| Adoption state | not accepted/current until release-control and `pb artifact current --json` prove alignment |
| Notes | No live/browser, adoption/current, Project Source, or Project deletion semantics changed. |

## v0.1.91.4 repair candidate

| Field | Value |
|---|---|
| Version | `v0.1.91.4` |
| Type | repair candidate |
| Base accepted/current | `chatgpt_claudecode_workflow-2_v0.1.91.1.zip` |
| Preserved repair candidates | `v0.1.91.2`, `v0.1.91.3` |
| Scope | Pre-source-add service bootstrap for clean-system release-control |
| Adoption state | not accepted/current until release-control and `pb artifact current --json` prove alignment |
| Notes | Candidate CLI/service are installed/verified before `promptbranch src add`; no live/browser, adoption/current, Project Source semantic, or Project deletion behavior changed. |

| v0.1.91.5 | repair | Run-all live_project_ensure aggregation terminal-line repair | candidate | focused aggregation/version/project-control validation before operator release-control | DOD-117 done; no normal slice advanced | pending |

| v0.1.91.6 | repair | Adopt-after-validation run-all evidence-reuse report path repair | candidate | focused adoption-verifier/evidence-reuse contract tests, version/project-control validation, compileall, shell syntax, Artifact Guardian, ZIP hygiene | DOD-118 done; no normal slice advanced | pending |

| v0.1.91.7 | repair | Pre-source-add Docker no-cache build-context freshness repair | candidate | focused Docker bootstrap/no-cache/build-context diagnostics tests, version/project-control validation, compileall, shell syntax, Artifact Guardian, ZIP hygiene | DOD-119 done; no normal slice advanced | pending |

| v0.1.91.8 | repair | Run-all single live-browser source lifecycle reuse for full_localhost | candidate | focused run-all reuse/localhost audit tests, version/project-control validation, compileall, shell syntax, Artifact Guardian, ZIP hygiene | DOD-120 done; no normal slice advanced | pending |

| v0.1.91.9 | repair | Adopt-after-validation localhost lifecycle-reuse report path repair plus run-all progress telemetry | candidate | focused shell tests, version/control-surface tests, compileall, bash syntax, artifact guard before operator install | no slice advanced | pending adoption evidence |

| v0.1.91.10 | repair | Run-all progress writer syntax and browser scheduler timeout diagnostics | accepted_current | operator-provided run-all/adopt-current evidence; all_tests_final_verdict=GO; `Adopt verified`; runtime/state/source/registry alignment true | DOD-121 and DOD-122 done; no normal slice advanced | 610185adcc3170baa6910b73f494f6ba8059af728d413c7d3474a8da6419c257 |

| v0.1.92 | normal | MVP-1 state-only loop walkthrough | accepted/current | full release-control/adoption completed with all_tests_final_verdict=GO and artifact-current alignment | DOD-123 done; first MVP-1 normal slice from accepted/current v0.1.91.10 | accepted/current `chatgpt_claudecode_workflow-2_v0.1.92.zip` |

| v0.1.93 | normal | MVP-1 planned-action walkthrough | candidate | focused loop/CLI/version/project-control tests, compileall, Artifact Guardian, ZIP hygiene; full release-control/adoption pending | DOD-124 focused; planned actions/gates are presentation-only and side-effect free | pending adoption evidence |

| v0.1.93.1 | repair | Direct release-validation scheduler nodeid isolation | candidate | focused test-suite isolation tests, targeted scheduler nodeid test, loop/CLI/version/project-control tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene; full release-control/adoption pending | DOD-125 focused; preserves DOD-124 planned-action feature; no normal slice advanced | pending adoption evidence |

| v0.1.94.1 | repair | Project Source capacity-prune identity guard while preserving first controlled read-only execution | accepted/current | full release-control/adoption completed with all_tests_final_verdict=GO and artifact-current alignment | DOD-127 done; no normal slice advanced | accepted/current `chatgpt_claudecode_workflow-2_v0.1.94.1.zip` |

| v0.1.95 | normal | Controlled read-only loop execution evidence report | candidate | focused loop evidence-report tests, loop CLI tests, version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene; full release-control/adoption pending | DOD-128 focused; MVP-1 evidence reporting advances without command execution | pending adoption evidence |

| v0.1.96 | normal | Project Source generated ZIP retention guard | candidate | focused generated ZIP retention/source-prune tests, version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene; full release-control/adoption pending | DOD-129 focused; source capacity control without deleting docs or other repo sources | pending adoption evidence |
| v0.1.97 | normal | Read-only loop evidence gate | candidate | focused loop/CLI/version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene; full release-control/adoption pending | DOD-130 focused; deterministic pass/block gate before real command execution | pending adoption evidence |

| v0.1.97.1 | repair | Text-source add post-commit reconciliation repair | accepted/current | full release-control/adoption completed with all_tests_final_verdict=GO and artifact-current alignment | DOD-131 done; no normal slice advanced | accepted/current `chatgpt_claudecode_workflow-2_v0.1.97.1.zip` |

| v0.1.98 | normal | Plan authority and anti-drift control-surface gate | accepted/current | full release-control/adoption completed with all_tests_final_verdict=GO and artifact-current alignment | DOD-132 done; control-surface gate active | accepted/current `chatgpt_claudecode_workflow-2_v0.1.98.zip` |
| v0.1.99 | normal | Rolling slice horizon and architecture-decision protocol | accepted/current via repair | full release-control/adoption completed through v0.1.99.1 | DOD-133 done; first command execution deferred to v0.1.100 | accepted/current via v0.1.99.1 evidence |
| v0.1.99.1 | repair | Docker build-context freshness repair for v0.1.99 | accepted/current | full release-control/adoption completed with all_tests_final_verdict=GO and artifact-current alignment | DOD-134 done; no normal slice advanced | accepted/current via v0.1.99.1 evidence |
| v0.1.100 | normal | First controlled read-only validation command execution | candidate | focused loop/CLI/control-surface validation pending full release-control/adoption | DOD-135 focused; first allowlisted JSON validation command execution | pending adoption evidence |

Repair base candidate preserved: chatgpt_claudecode_workflow-2_v0.1.99.zip

## v0.1.100.3 release-control expectation

`v0.1.100.3` must install from a ZIP that contains no `debug_artifacts/` entries and must pass Artifact Guardian before any release-control adoption can occur. It remains a candidate until full release-control and `pb artifact current --json` prove accepted/current alignment.


| v0.1.103.1 | normal | Docker browser parity diagnostic envelope | candidate | Built from accepted/current v0.1.102; full release-control/adoption pending. |

| v0.1.103.1 | repair/diagnostic | Docker browser parity diagnostic envelope | candidate | focused local validation only; no live Docker auth-readiness run in artifact build | adds diagnostic evidence surface only | - |

| v0.1.103.2 | repair/diagnostic | Docker browser parity passive-auth and profile-bootstrap repair | candidate | focused local validation only; live seeded-profile check pending | DOD-142 in_progress | pending |

| v0.1.103.3 | repair/diagnostic | Passive auth-readiness runtime-client wiring repair | candidate | focused local validation only; live seeded-profile check pending | DOD-143 in_progress | pending |

| v0.1.103.5 | repair/diagnostic | Docker parity true keep-open browser session mode | candidate | focused local validation only; live guarded Project Source test pending | DOD-144 in_progress | pending |
| v0.1.103.6 | repair/diagnostic | Docker parity artifact export safety | candidate | focused local validation only; live export pending | DOD-145 in_progress | pending |
| v0.1.103.8 | repair/diagnostic | Docker parity Cloudflare challenge settle loop | candidate | focused local validation only; live Cloudflare settle-loop pending | DOD-146 in_progress | pending |

| v0.1.103.9 | repair/diagnostic | Bonnetjes Cloudflare parity profile hygiene | candidate | focused local validation only; live clean logged-in profile path operator-proven before packaging | DOD-147 in_progress | pending |

## v0.1.103.10.6

Status: candidate only, not accepted/current.

Scope: one-shot standard browser Cloudflare validation workflow.

Validation focus: script syntax, focused shell-script tests, control-surface validation, artifact hygiene.

Control-surface tokens: v0.1.103.10.6 chatgpt_claudecode_workflow-2_v0.1.103.10.6.zip standard browser profile default

## v0.1.103.10.6

Status: candidate.

Purpose: auth-only hygiene compile path repair after `v0.1.103.10.2` installed successfully but adoption was blocked by a stale `promptbranch_service.py` compile target.

Scope remains auth-only. Project Source mutation remains out of scope.

## v0.1.103.10.6

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.103.10.6 | repair | standard browser profile ownership repair | candidate | focused shell-script/profile guard tests pending operator live Cloudflare validation | DOD-149 added; DOD-148 preserved in progress | not accepted/current |

Control-surface tokens: v0.1.103.10.6 chatgpt_claudecode_workflow-2_v0.1.103.10.6.zip standard browser profile ownership repair

## v0.1.103.10.8

| Version | Type | Scope | State | Validation | DoD movement | Adoption |
|---|---|---|---|---|---|---|
| v0.1.103.10.8 | repair/packaging | clean standard browser auth-only validation ZIP after `.pytest_cache` import-plan rejection | candidate | ZIP hygiene and focused control/version tests; live operator auth-only validation pending | DOD-151 added; DOD-148..DOD-150 preserved in progress | not accepted/current |

Control-surface tokens: v0.1.103.10.8 chatgpt_claudecode_workflow-2_v0.1.103.10.8.zip clean generated-cache-free candidate

## v0.1.103.10.8

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.103.10.8 | repair | standard browser profile default | candidate | focused shell/control/version tests pending; operator live auth-only validation required | DOD-152 added; DOD-148..DOD-151 preserved | not accepted/current |

## v0.1.103.10.9

| Version | Type | Scope | State | Validation | DoD impact | Adoption |
|---|---|---|---|---|---|---|
| v0.1.103.10.9 | repair | pb ask reuses held auth-ready browser session | candidate | focused held-session reuse tests and control-surface validation required | DOD-153 added; DOD-148..DOD-152 preserved | not accepted/current |

Control-surface tokens: v0.1.103.10.9 chatgpt_claudecode_workflow-2_v0.1.103.10.9.zip held auth-ready session reuse pb ask singleton cleanup guard

Control-surface slice token: v0.1.103.10.9 — pb ask reuses held auth-ready browser session

## v0.1.103.10.10

| Version | Kind | Scope | State | Validation | DoD movement | Acceptance |
| --- | --- | --- | --- | --- | --- | --- |
| v0.1.103.10.10 | repair | pb ask sends through held auth-ready current page | candidate | focused held-session tests and control-surface validation required | DOD-154 added; DOD-148..DOD-153 preserved | not accepted/current |

Control-surface tokens: v0.1.103.10.10 chatgpt_claudecode_workflow-2_v0.1.103.10.10.zip held auth-ready current page skip target navigation pb ask Cloudflare avoidance

Control-surface slice token: v0.1.103.10.10 — pb ask sends through held auth-ready current page

## v0.1.103.10.11

| Version | Kind | Scope | State | Validation | DoD movement | Acceptance |
| --- | --- | --- | --- | --- | --- | --- |
| v0.1.103.10.11 | repair | Docker-originated visible browser profile bootstrap | candidate | focused shell/control validation required; operator live Docker visual bootstrap required | DOD-155 added; DOD-148..DOD-154 preserved | not accepted/current |

Control-surface tokens: v0.1.103.10.11 chatgpt_claudecode_workflow-2_v0.1.103.10.11.zip Docker visual browser bootstrap standard profile Cloudflare fingerprint

Control-surface slice token: v0.1.103.10.11 — Docker-originated visible browser profile bootstrap
| v0.1.103.10.12 | repair | pb ask preserves current project conversation scope | candidate | focused held-session routing/shell tests before operator auth-only validation; adoption pending | DOD-156 in_progress; DOD-148..DOD-155 preserved | pending |

<!-- v0.1.103.10.12 — pb ask preserves current project conversation scope: chatgpt_claudecode_workflow-2_v0.1.103.10.12.zip -->

| v0.1.103.10.13 | repair | guarded `pbsa` Project Source mutation intent | candidate | focused API/client/source gate tests before operator live `pbsa`; adoption pending | DOD-157 in_progress; DOD-148..DOD-156 preserved | pending |

<!-- v0.1.103.10.13 — guarded pbsa Project Source mutation intent: chatgpt_claudecode_workflow-2_v0.1.103.10.13.zip -->

| v0.1.103.10.15 | repair | `pbsa` held-session preflight/upload reuse | candidate | focused held-session/API tests before operator live `pbsa`; adoption pending | DOD-158 in_progress; DOD-148..DOD-157 preserved | pending |

<!-- v0.1.103.10.15 — pbsa project-sources route preservation: chatgpt_claudecode_workflow-2_v0.1.103.10.15.zip -->

Control-surface slice token: v0.1.103.10.15 — pbsa preserves Project Sources route before Add source lookup

| v0.1.103.10.17 | repair | split Docker bootstrap URL from project-scoped auth target | candidate | focused script/version/control-surface tests before operator live auth-only validation; adoption pending | DOD-160 in_progress; DOD-148..DOD-159 preserved | pending |

| v0.1.103.10.17 | repair | v0.1.103.10.17 — pbsa reuses held session for remembered overwrite removal | chatgpt_claudecode_workflow-2_v0.1.103.10.17.zip candidate | focused held-session/source/preflight/version/control-surface tests before operator live auth-only validation; adoption pending | DOD-161 in_progress; DOD-148..DOD-160 preserved | pending |


## v0.1.103.10.19

Release state: candidate only. Adds `pb test api` and `scripts/pb-api-coverage-test.sh` / `.py` for rerunnable API coverage. No adoption claimed.


control token: chatgpt_claudecode_workflow-2_v0.1.103.10.19.zip

control token: v0.1.103.10.19 — install-safe pb test api module runner

## v0.1.103.10.19

Candidate only. Repairs `pb test api` installed-package execution by moving the API coverage runner into the installed package module path. No adoption evidence claimed in this artifact response.

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.19.zip
control token: v0.1.103.10.19 — install-safe pb test api module runner

## v0.1.103.10.21

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.103.10.21 | repair | pb test api classification cleanup | candidate | focused tests pending/live install pending | DOD-164 | n/a |

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.21.zip
control token: v0.1.103.10.21 — pb test api classification cleanup
## v0.1.103.10.21

| version | type | scope | state | validation | dod | adoption |
|---|---|---|---|---|---|---|
| v0.1.103.10.21 | repair | pb test api classification cleanup | candidate | focused tests pending/live install pending | DOD-165 | n/a |

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.21.zip
control token: v0.1.103.10.21 — pb test api classification cleanup

## v0.1.103.10.22

| version | type | scope | state | validation | dod | adoption |
|---|---|---|---|---|---|---|
| v0.1.103.10.22 | repair | Docker Chrome shm sizing for visible browser validation | candidate | focused tests pending/live install pending | DOD-166 | n/a |

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.22.zip
control token: v0.1.103.10.22 — Docker Chrome shm sizing for visible browser validation


## v0.1.103.10.42

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.103.10.42 | repair | full/browser validation skips generic-root login check | candidate | focused tests pending/live install pending | DOD-167 | n/a |

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip
control token: v0.1.103.10.42 — missing live seed profile is non-blocking for run-all release validation

## v0.1.103.10.42

| version | kind | scope | status | validation | dod | notes |
|---|---|---|---|---|---|---|
| v0.1.103.10.42 | repair | full/browser validation skips generic-root login check | candidate | focused tests pending/live install pending | DOD-168 | no browser/session architecture changes |

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip
control token: v0.1.103.10.42 — missing live seed profile is non-blocking for run-all release validation

## v0.1.103.10.42

| version | type | slice | status | validation | dod | notes |
| --- | --- | --- | --- | --- | --- | --- |
| v0.1.103.10.42 | repair | full/browser validation skips generic-root login check | candidate | focused tests pending/live install pending | DOD-169 | no browser/session or Project Source mutation changes |

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip
control token: v0.1.103.10.42 — missing live seed profile is non-blocking for run-all release validation

## v0.1.103.10.42

| version | type | scope | status | validation | DOD | notes |
|---|---|---|---|---|---|---|
| v0.1.103.10.42 | repair | full/browser validation skips generic-root login check | candidate | focused tests pending/live install pending | DOD-170 | login_check remains explicit diagnostic only; no browser/session architecture changes |

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip
control token: v0.1.103.10.42 — missing live seed profile is non-blocking for run-all release validation


## v0.1.103.10.42

| version | type | summary | status | validation | dod | notes |
|---|---|---|---|---|---|---|
| v0.1.103.10.42 | repair | release-control clears auth bootstrap held session explicitly | candidate | focused tests pending/live install pending | DOD-171 | every release-control live path runs auth bootstrap before Project Source add or tests; no browser/session architecture changes |

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip
control token: v0.1.103.10.42 — missing live seed profile is non-blocking for run-all release validation

## v0.1.103.10.42

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.103.10.42 | repair | missing live seed profile is non-blocking for run-all release validation | candidate | focused tests pending/operator full adoption pending | DOD-172 added; DOD-171 preserved | n/a |

control token: chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip
control token: v0.1.103.10.42 — missing live seed profile is non-blocking for run-all release validation

Control-surface active slice token: v0.1.103.10.42 — release-control auth bootstrap accepts project-page readiness for source-add preflight

Control-surface active slice token: v0.1.103.10.42 — release-control pre_tests auth bootstrap targets current conversation URL before requiring composer

## v0.1.103.10.42

| Version | Type | Slice | ZIP status | Validation | DoD movement | Adoption |
|---|---|---|---|---|---|---|
| v0.1.103.10.42 | repair | preserve Docker live profile pool across release ZIP import | candidate | focused static/syntax/import-plan validation before operator live bootstrap and full adoption | DOD-176 added; DOD-171..DOD-174 preserved | not accepted/current |

Control-surface token: `chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip`
Control-surface active slice token: `v0.1.103.10.42 — preserve Docker live profile pool across release ZIP import`

## v0.1.103.10.42

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.103.10.42 | repair | preserve Docker live profile pool across release ZIP import | candidate | focused release-control preservation tests and import-plan pending operator live run-all validation | DOD-177 added; DOD-176 preserved | not accepted/current |

Control-surface tokens: v0.1.103.10.42 chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip preserve Docker live profile pool across release ZIP import

## v0.1.103.10.42

| Version | Type | Scope | State | Validation | Adoption |
|---|---|---|---|---|---|
| v0.1.103.10.42 | repair | live ask targets `/c/...` and fails fast on Cloudflare challenge | candidate | focused tests and import-plan pending/passed in candidate build | not accepted/current |

Control-surface tokens: v0.1.103.10.42 chatgpt_claudecode_workflow-2_v0.1.103.10.42.zip live conversation URL for run-all live steps

## v0.1.103.10.43

| Version | Type | Slice | ZIP status | Validation | DoD movement | Accepted checksum |
|---|---|---|---|---|---|---|
| v0.1.103.10.43 | repair | release live browser challenge fails fast without manual-login wait | candidate | focused static/syntax/import-plan validation before operator run-all adoption | DOD-179 added; DOD-176..DOD-178 preserved | not accepted/current |

Control-surface tokens: v0.1.103.10.43 chatgpt_claudecode_workflow-2_v0.1.103.10.43.zip docker_live_profile_challenged no manual-login wait

## v0.1.103.10.45

| Version | Type | Slice | Status | Validation | Acceptance |
|---|---|---|---|---|---|
| v0.1.103.10.45 | repair | repair release-live challenge fail-fast logging and stop live cascade | candidate | focused static/syntax/import-plan validation before operator run-all adoption | not accepted/current |

Control-surface tokens: v0.1.103.10.45 chatgpt_claudecode_workflow-2_v0.1.103.10.45.zip docker_live_profile_challenged no live cascade after ask_live challenge

Control-surface active slice token: v0.1.103.10.45 — repair package version surface for Docker build context coherence


## v0.1.103.10.48

| version | type | slice | status | validation | DoD movement | adoption |
|---|---|---|---|---|---|---|
| v0.1.103.10.48 | repair | treat mid-run Cloudflare/backend-403 challenge as terminal `docker_live_profile_challenged` | candidate | focused static/syntax/import-plan validation before operator run-all adoption | DOD-183 added; DOD-176..DOD-182 preserved | not accepted/current |

Control-surface tokens: v0.1.103.10.48 chatgpt_claudecode_workflow-2_v0.1.103.10.48.zip mid-run backend-403 TargetClosedError maps to docker_live_profile_challenged no cooldown retry cascade


## v0.1.103.10.48

`v0.1.103.10.48 — classify backend-api 403 guardrail as terminal browser challenge across release validation paths` preserves the Docker-only live-validation line and extends fail-fast challenge classification beyond ask-live. Observed ChatGPT `/backend-api/...` 403 responses are diagnostic guardrail evidence only, not an operational API contract. Release-control now enables fail-fast challenge handling for full/direct, localhost/service, live preflight, project selection, and live ask paths; after a full-validation backend guardrail, remaining live browser phases are skipped and import/artifact guards still run.

## Active repair slice — v0.1.103.10.53

`v0.1.103.10.53 — release-live bootstrap 429/guardrail is terminal before ask_live` preserves the Docker-only challenge classification chain through `v0.1.103.10.48`, then fixes the remaining human-likeness topology bug: release-live setup and execution now use `.pb_profile_local_debug_pools/release-live/slots/slot-1` as the single actor profile for project ensure, project selection, conversation bootstrap, ask-live, visual artifact roundtrip, and release-live. `.pb_profile_local_debug` remains optional/reference state and is no longer used to create the live conversation that the slot later opens. The Docker bootstrap default image also derives from `VERSION`/`PROMPTBRANCH_VERSION` instead of depending on an unset `PROMPTBRANCH_SERVICE_IMAGE_TAG` local fallback.


## Active repair slice — v0.1.103.10.53

`v0.1.103.10.53 — release-live bootstrap 429/guardrail is terminal before ask_live` preserves the Docker-only live-profile repair chain through `v0.1.103.10.49`, then makes backend-api 403 guardrail telemetry during auth bootstrap terminal. Release-control now refuses to treat a visually logged-in/composer-visible browser as clean when the standard Docker profile is already forbidden by backend-api guardrail responses; it restarts the candidate service to clear the held browser owner and stops before Project Source add/full validation.


## Active repair slice — v0.1.103.10.55

`v0.1.103.10.55 — release-live bootstrap and ask use one continuous browser session` preserves the Docker-only live-profile and guardrail repairs through v0.1.103.10.53, then adds a fast pytest-backed replay harness for release-control run-all orchestration. The replay covers the success path and terminal live bootstrap 429/backend guardrail behavior before ask_live, reducing long live validation loops for shell/control-flow repairs.


## v0.1.103.10.56 — wire release-live-continuous into real CLI test dispatch

Repair candidate chatgpt_claudecode_workflow-2_v0.1.103.10.56.zip wires `pb test release-live-continuous` into the real CLI dispatcher while preserving the continuous release-live design from 10.55.

## v0.1.103.10.59

- Added trusted conversation warmup for `release-live-continuous`: the continuous live session starts from the conversation URL proven by `live_profile_preflight` instead of bare `https://chatgpt.com/`.
- Preserves all-in-Docker, explicit slot profile, no host-CDP/session-manager, and no copied-profile trust.

## v0.1.103.10.59

Active candidate: v0.1.103.10.59

Artifact: chatgpt_claudecode_workflow-2_v0.1.103.10.59.zip

Slice: v0.1.103.10.59 — extract live preflight warmup URL from login-check url field

Scope: release-live-continuous starts the initial auth/warmup check from the trusted conversation URL proven by live_profile_preflight instead of bare https://chatgpt.com/.



## v0.1.103.10.61

Active candidate: v0.1.103.10.61

Artifact: chatgpt_claudecode_workflow-2_v0.1.103.10.61.zip

Slice: v0.1.103.10.61 — classify Docker live preflight challenge as external live challenge and stop browser-repair loop


## v0.1.103.10.65

Artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.65.zip`

Slice: v0.1.103.10.65 — classify release-live-continuous first-ask Cloudflare challenge as LIVE_BLOCKED

Default `--run-all-tests` no longer calls `POST /v1/login-check`; external ChatGPT live probes are explicit and default live rows are `external_live_not_requested`.

Control-surface active slice token: v0.1.103.10.65 — release-live-continuous direct conversation mode navigates to trusted conversation before held-page send guard


## v0.1.103.10.65

Artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.65.zip`

Slice: v0.1.103.10.65 — release-live-continuous direct conversation mode navigates to trusted conversation before held-page send guard

Status: candidate. Validation is focused/static/unit only until operator release-control evidence is supplied.

Control-surface active slice token: v0.1.103.10.65 — release-live-continuous direct conversation mode navigates to trusted conversation before held-page send guard


## v0.1.103.10.66

Active repair candidate: `v0.1.103.10.66 — release-live-continuous handles page/context close during composer submit as explicit browser-lifetime failure`.

Scope remains repair-only: preserve direct trusted conversation mode, skip root project discovery, add explicit `browser_context_closed_during_submit` handling, and do not add Cloudflare workarounds, host-CDP/session-manager, copied-profile trust, or project deletion.


## v0.1.103.10.66 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.66.zip`.

Active candidate version: `v0.1.103.10.66`.

Active repair slice: `v0.1.103.10.66 — release-live-continuous handles page/context close during composer submit as explicit browser-lifetime failure`.

This remains repair-only and does not advance the normal horizon. It keeps trusted conversation direct mode and adds structured `browser_context_closed_during_submit` evidence for live browser page/context close during composer submit.

## v0.1.103.10.67 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.67.zip`.

Active candidate version: `v0.1.103.10.67`.

Active repair slice: `v0.1.103.10.67 — composer wait target-close is classified as browser_context_closed_during_submit`.

Release state: candidate only; not accepted/current; focused validation required.

## v0.1.103.10.68 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.68.zip`.

Active candidate version: `v0.1.103.10.68`.

Active repair slice: `v0.1.103.10.68 — release-live-continuous marks completed bootstrap/ask sentinel run as ok`.

`v0.1.103.10.68` keeps the `v0.1.103.10.67` trusted direct-conversation flow and fixes the final aggregation predicate: when project ensure succeeds, bootstrap returns `status=completed` with the exact bootstrap sentinel, and ask returns `status=completed` with the exact ask sentinel, the top-level result is `ok=true`, `contains_expected_sentinel=true`, and no `failed_phase` is emitted. Browser action audit warnings remain preserved.

Control-surface active slice token: v0.1.103.10.68 — release-live-continuous marks completed bootstrap/ask sentinel run as ok

## v0.1.103.10.69 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.69.zip`.

Active candidate version: `v0.1.103.10.69`.

Active repair slice: `v0.1.103.10.69 — add install.sh strict all-all release gate`.

`v0.1.103.10.69` adds repo-root `install.sh` as the strict all-all release gate for new ZIP releases. The script installs the exact candidate ZIP, runs default product validation, runs explicit external ChatGPT live validation, requires live validation to pass, adopts only if all validation is `GO`, and writes `pb artifact current --all --json` evidence after adoption.

Control-surface active slice token: v0.1.103.10.69 — add install.sh strict all-all release gate



## v0.1.103.10.70 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.70.zip`.

Active repair slice: `v0.1.103.10.70 — classify release-live-continuous bootstrap guardrail as external live blocked`.

`v0.1.103.10.70` keeps the `v0.1.103.10.69` strict `install.sh` all-all gate and changes only release-control final classification: `live_bootstrap_guardrail` plus skipped downstream live statuses are external-live blockage evidence, so all-all adoption remains blocked but the final verdict becomes `LIVE_BLOCKED`, not product `FIX`.

Out of scope: Cloudflare/rate-limit bypass, host-CDP/session-manager, copied-profile trust, ChatGPT Project deletion, and release adoption claims.


## v0.1.103.10.71 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.71.zip`.

Active repair slice: `v0.1.103.10.71 — final verdict aggregation maps live_bootstrap_guardrail cascade to LIVE_BLOCKED`.

`v0.1.103.10.71` keeps the `v0.1.103.10.69` strict `install.sh` all-all gate and the `v0.1.103.10.70` status vocabulary. It fixes the actual all-tests final summary aggregation path: if the mixed `live_project_ensure` log contains terminal `live_bootstrap_guardrail` evidence, the failed live cascade is classified as external `LIVE_BLOCKED`, not product `FIX`, while preserving failed live steps, `artifact_guard` evidence, and adoption refusal.

Out of scope: Cloudflare/rate-limit bypass, host-CDP/session-manager, copied-profile trust, ChatGPT Project deletion, and release adoption claims.


## v0.1.103.10.78 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.78.zip`.

Active repair slice: `v0.1.103.10.78 — make pb src add exact-name idempotent and block suffix-renamed Project Source uploads`.

`v0.1.103.10.78` repairs project control-surface active-candidate drift and final verdict precedence. If product validation fails, the all-all final verdict remains `FIX` even when external-live also reports `live_bootstrap_guardrail`; if product validation is clean and only external-live is blocked, the final verdict is `LIVE_BLOCKED` and adoption remains refused.

## v0.1.103.10.78 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.78.zip`.

Active repair slice: `v0.1.103.10.78 — make pb src add exact-name idempotent and block suffix-renamed Project Source uploads`.

`v0.1.103.10.78` keeps the strict all-all install gate, product-clean `LIVE_BLOCKED` classification, and precise `bootstrap_sentinel_missing_after_ask_success` status. It changes only release-live sentinel validation so known visible thinking preambles are normalized before exact single-token matching. Arbitrary extra text remains a failure.

## v0.1.103.10.78 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.78.zip`.

Active repair slice: `v0.1.103.10.78 — make pb src add exact-name idempotent and block suffix-renamed Project Source uploads`.

This repair requires exact canonical file names for normal `pb src add` / `pbsa`, blocks visible suffix-renamed collisions before upload, and reports backend-created suffixes as `backend_renamed_source` instead of accepting them as success.


## v0.1.103.10.79 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.79.zip`.

Active repair slice: `v0.1.103.10.79 — require stable Project Sources preflight and fail fast on backend-assigned suffix names`.

`v0.1.103.10.79` keeps the strict all-all install gate, release-live sentinel normalization, and exact canonical Project Source naming. Before a file upload, it requires either an explicit empty Project Sources state or multiple stable non-empty snapshots. Zero cards without an explicit empty state are classified as `source_preflight_not_authoritative` and no upload occurs. After a committed upload, a newly visible suffix-renamed source is classified immediately as `backend_renamed_source`, rolled back when uniquely identifiable, and returned before the exact-name persistence retry loop. Source-add read timeouts include the configured timeout and active-operation details.

## v0.1.103.10.80 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.80.zip`.

Active repair slice: `v0.1.103.10.80 — reuse the verified candidate image during auth bootstrap and preserve Docker dependency cache`.

`v0.1.103.10.80` keeps the strict all-all gate, sentinel normalization, and authoritative Project Sources preflight. Pre-source-add auth bootstrap reuses the exact verified candidate service with `--no-recreate`; stable Docker dependency layers precede release metadata, browser automation versions are pinned, and exhausted Chrome transport downloads are classified as `docker_browser_dependency_download_failed`.

## v0.1.103.10.81 repair note

Canonical artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.81.zip`.

Download transport artifact: `chatgpt_claudecode_workflow-2_transport_v0.1.103.10.81_b7c1de9f28.zip`.

Active repair slice: `v0.1.103.10.81 — separate candidate transport filename from canonical Project Source filename`.

`v0.1.103.10.81` keeps the strict all-all gate, sentinel normalization, authoritative Project Sources preflight/suffix rollback, and verified candidate-image reuse. It separates the unique ChatGPT attachment transport basename from the canonical repo+version release artifact, validates the transport ZIP's internal VERSION and integrity, materializes the canonical local copy, and uploads/adopts only that canonical identity.


## v0.1.103.10.82 repair note

Canonical candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.82.zip`.

Active repair slice: `v0.1.103.10.82 — restore pbsa same-name overwrite by reconciling ChatGPT Library backing files`.

This repair keeps the existing `pbsa` command and reconciles exact attributable ChatGPT Library backing-file IDs, including Recently deleted entries, before a same-name canonical Project Source upload. It fails closed on missing file IDs, cross-project references, or an uncleared filename family.

## v0.1.103.10.83 repair note

Canonical candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.83.zip`.

Active repair slice: `v0.1.103.10.83 — make Library reconciliation authoritative and capture live upload file identities`.

The candidate remains unadopted until strict all-all reaches `GO` and same-name `pbsa` overwrite succeeds without a numeric suffix.

## v0.1.103.10.84 repair note

Canonical candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.84.zip`.

Active repair slice: `v0.1.103.10.84 — restore normal file add and replace existing Project Sources by identity`.

This repair removes unconditional Library/Recently deleted preflight from ordinary file adds. Existing exact file sources are routed to a non-destructive replace/update capability probe; if the live menu does not expose replacement, Promptbranch returns `project_source_replace_not_supported` without removing the source. Library reconciliation remains available only for visible or backend-proven numeric-suffix collisions.


| v0.1.103.10.86 | repair | Diagnostic-only legacy 10.75 vs current Project Source A/B | candidate | focused tests; live A/B not run here | DOD-258 in progress | pending |

| v0.1.103.10.87 | repair | Diagnostic runner standard bearer-token resolution | candidate | external-CWD protected-endpoint subprocess regression | DOD-259 in progress | pending |


## v0.1.103.10.90 diagnostic candidate

`chatgpt_claudecode_workflow-2_v0.1.103.10.90.zip` is diagnostic-only. It may create one disposable project, one disposable Project Source backing object, and one disposable visible Library file. It must not upload the release artifact, adopt a candidate, touch the earlier `(1)` evidence project/source, or use filename-only deletion.


## v0.1.103.10.91 diagnostic candidate

`chatgpt_claudecode_workflow-2_v0.1.103.10.91.zip` is diagnostic-only. It fixes the false `disposable_visible_library_file_identity_not_captured` classification, makes active inventory discovery ID-driven, and removes the 600-event public trace cap. It must not be adopted from the diagnostic run and must not touch the earlier suffix-evidence project/source.


## v0.1.103.10.92 diagnostic candidate

`chatgpt_claudecode_workflow-2_v0.1.103.10.92.zip` is diagnostic-only. It repairs authenticated Library inventory replay while preserving sanitized reporting and all fail-closed mutation gates. It must not be adopted or uploaded as a release Project Source from this diagnostic run.


## v0.1.103.10.93 diagnostic candidate

`chatgpt_claudecode_workflow-2_v0.1.103.10.93.zip` is diagnostic-only. It reconstructs exact canonical Library filenames across rendered whitespace, requires unique UI-family and backend-identity binding, and refuses deletion or reupload when the selected card is missing or ambiguous. It must not be adopted or uploaded as a release Project Source from this diagnostic run.


| v0.1.103.10.94 | `chatgpt_claudecode_workflow-2_v0.1.103.10.94.zip` | candidate | diagnostic-only | v0.1.103.10.94 — bind Library filenames only to actionable file rows; not adopted |

| v0.1.103.10.100 | repair | Bounded stream-safe Fetch/XHR protocol-watch settlement | candidate | focused protocol-watch, Project Source, Library diagnostic, control-surface, version, syntax, packaging and clean-extraction validation; live diagnostic pending | no normal slice advanced | pending |

| v0.1.103.10.101 | repair | Dedicated visible-Library processing-stream identity capture | candidate | focused visible-stream, Project Source, Library diagnostic, control-surface, version, syntax, packaging and clean-extraction validation; live diagnostic pending | no normal slice advanced | pending |


| v0.1.103.10.102 | repair | Immutable request phase and sequence-bound soft-delete discovery | candidate | focused request-phase, sequence-bound discovery, candidate-classification, settlement-deduplication, Library diagnostic, control-surface, version, syntax, packaging and clean-extraction validation; live diagnostic pending | no normal slice advanced | pending |

| v0.1.103.10.103 | repair | Bounded unique Library delete-confirmation proof | candidate | focused confirmation-delay/direct-mutation, Library diagnostic, Project Source, control-surface, version, syntax, packaging and clean-extraction validation; live diagnostic pending | no normal slice advanced | pending |

| v0.1.103.10.109 | repair | Deterministic capacity pruning before Project Source upload | candidate | focused 25→24→25 capacity transaction, indexed long-version parsing, protected-current selection, no-safe-candidate failure, control-surface, version, syntax, packaging and clean-extraction validation; live validation pending | no normal slice advanced | pending |

| v0.1.103.10.110 | repair | Missing-registry-safe read-only validation | candidate | missing registry is reported by read-only source-sync plans; invalid registries and artifact mutations remain blocked; agent/full tests emit terminal JSON; test report summarizes pre-suite failures | no normal slice advanced | pending |

| v0.1.103.10.111 | repair | Full-suite registry and overwrite alignment | repair_required | 7/9 release gates passed; full_direct and full_localhost failed because unchanged overwrite bytes produced no new upload and the old singleton was accepted as persistence proof | DOD-280 remains in_progress; no normal slice advanced | rejected/not adopted |
| v0.1.103.10.112 | repair | Changed-content indexed-family overwrite proof | repair_required | changed bytes were proven, but selecting the same local basename emitted no second upload request; fail-closed `source_overwrite_upload_not_started` was correct | DOD-281 remains in_progress; no normal slice advanced | rejected/not adopted |
| v0.1.103.10.113 | repair | Collision-free indexed replacement upload | repair_required | stage changed bytes as `<stem>(<numeric transaction token>).<ext>` inside the canonical family; exact processing-stream identity remains authoritative; delete only pre-upload family members; require final assigned singleton in both transports | DOD-282 focused candidate; no normal slice advanced | pending |
| v0.1.103.10.114 | repair | Continuous live-profile resolution and causal-submit evidence | repair_required | all 9 validation gates passed, including independent full_direct/full_localhost, continuous physical profile reuse, current submit-flow evidence, visual artifact and release-live; adoption failed closed because repository/project identity was unresolved; malformed same-count virtualized response still consumed the long completion timeout | DOD-283 live-proven but unadopted; no normal slice advanced | rejected/not adopted |
| v0.1.103.10.115 | repair | Adoption identity preflight and parse-independent response completion | superseded | authoritative `pb project join` preflight before expensive validation; exact assigned source/backing identity transported into adoption; same-count post-submit response stability independent of envelope parsing; structured-only rate-limit retry evidence | DOD-284 focused candidate; no normal slice advanced | pending |

| v0.1.103.10.116 | repair | Assigned-source-aware post-adoption verification | accepted_current | canonical artifact and exact assigned-source identities verified separately; backing IDs and all version/consistency invariants mandatory | DOD-285 focused candidate; no normal slice advanced | pending |

| v0.1.104 | normal | Sandbox mutation verification and rollback evidence gate | repair_required | exact before/after hash proof, sandbox-only json.tool validation, validation read-only proof, exact rollback proof, repository unchanged, workspace deleted | DOD-286 focused candidate; next slice v0.1.105 | pending |
| v0.1.104.1 | repair | Sandbox release-gate integration and fresh validation evidence | repair_required | mandatory 13-gate sandbox manifest group; explicit top-level gate; manifest-hash evidence identity; fresh direct; independent localhost | DOD-287 focused candidate; next normal slice v0.1.105 | pending |

| v0.1.104.2 | repair | Bounded post-bootstrap conversation-idle recovery | repair_required | one pre-ask readiness probe; one same-conversation reload only for interrupted_answer_state; bootstrap sentinel reverified; authoritative idle required; no general retry | DOD-288 focused candidate; next normal slice v0.1.105 | pending |

| v0.1.104.3 | repair | Current-turn-scoped interrupted-state readiness | repair_required | ignore historical Retry; separate pre/post bootstrap readiness; one hydrated same-conversation reload; no historical resubmit or general retry | DOD-289 focused candidate; next normal slice v0.1.105 | pending |

| v0.1.104.4 | repair | Parse-independent visual reply completion and bounded envelope recovery | repair_required | causal virtualized-turn response detection, stable UI completion before parse, one deterministic literal-whitespace normalization, one bounded same-conversation malformed-envelope retry | DOD-290 focused candidate; 10/10 required | pending |
| v0.1.104.5 | repair | Hermetic release-validation profile isolation | candidate | explicit temporary HOME/XDG/profile/project state/config/cache authority, child-process path preflight, ambient lock unreachable/no-read proof, unchanged 300-second timeout and no node retry | DOD-291 focused candidate; 10/10 required | pending |

Current active repair: `v0.1.104.5 — hermetic release-validation profile isolation`.

| v0.1.104.5 | repair | Hermetic release-validation profile isolation | accepted_current | strict host validation passed 10/10; scheduler group 9/9; sandbox 13/13; all external-live gates passed; evidence-bound adoption and release_adopted_and_verified completed | DOD-291 done; v0.1.104 repair sequence complete | fe9951b308bc1108d7ec6d92ed098b61229ed368125dbb83c99a8885c4c97bc6 |
| v0.1.105 | normal | Sandbox correction promotion readiness check | candidate | focused readiness tests produce three complete independent runs with one deterministic fingerprint; strict host validation and adoption pending | DOD-292 focused candidate; v0.1.106 decision remains pending | pending |

| v0.1.105.1 | repair | Target-anchored promotion-readiness repository resolution | candidate | absolute target derives authoritative root; explicit wrong root blocks before evidence; unrelated cwd produces ready with 3 workspaces and 1 fingerprint | DOD-293 focused candidate; strict host validation pending | pending |

| v0.1.105.1 | repair | Target-anchored promotion-readiness repository resolution | accepted_current | strict host validation passed 10/10 with fresh direct, independent localhost, sandbox 13/13, all external-live gates, import smoke, Artifact Guardian, and release_adopted_and_verified | DOD-293 done | ca2ce7c619e5d61535734089def7e493631afc21310e724492c6dacd69143bdb |
| v0.1.106 | normal | Controlled correction promotion decision record | candidate | focused decision-record tests and local three-run GO evidence; strict host validation and adoption pending | DOD-294 focused candidate | pending |

| v0.1.106 | normal | Controlled correction promotion decision record | accepted_current | strict host validation passed 10/10; evidence-bound adoption and final verification passed | DOD-294 done | 8eeba054de99cfbaab5917202199c0a2eaea9f8eaabc44d9b12b09f7557cf43e |
| v0.1.107 | normal | Controlled correction execution envelope design | candidate | focused design, CLI, control-surface, sandbox, package, and artifact validation before strict host release-control | DOD-295 focused candidate | pending |

| v0.1.108 | normal | Controlled correction execution envelope validation gate | candidate | focused validation gate, CLI, control-surface, package, and Artifact Guardian validation before strict host release-control | DOD-296 focused candidate; adoption pending | pending |

## v0.1.111.1 repair candidate

Packaging-only repair for the missing installed `promptbranch_release_engine` module. The candidate must pass an isolated installed-CLI smoke before any browser bootstrap or Project Source mutation. Accepted/current remains `v0.1.109.1.1`.

| v0.1.111.2 | repair | Full-test progress, ETA, and fail-fast reporting | repair_required | partial strict log exposed false expected-missing failure accounting and phase-level rather than step-level browser fail-fast; no terminal verdict or adoption evidence | DOD-308 predecessor defect; no normal scope advanced | rejected/not adopted |
| v0.1.111.3 | repair | Normalised browser progress and genuine step-level fail-fast | candidate | normalise before terminal progress; stop before next main browser step on genuine failure; pending work units skipped; all gates preserved | DOD-308 focused candidate; strict host validation pending | pending |

Planned after `v0.1.116` acceptance: `v0.1.117 — PBAI compliance inventory and multi-repository rollout`.

| v0.1.123.2.6 | repair | Correlated rendered-attachment intake plus legacy persisted-run normalization | replacement_candidate | exact selector, historical-shape normalization, rejection matrix, simulated browser-byte verification, Router regression, and focused modules pass offline; real authenticated replay and strict adoption remain pending | DOD-431..DOD-441 focused candidate; formal proof 0/2 | pending |

## v0.1.123.2.6 post-materialization finalization correction

Accepted/current remains `v0.1.123.2.5`. The active replacement candidate remains `v0.1.123.2.6`. The repair addresses a stale finalization outcome after a rendered `v0.1.124` ZIP had already been downloaded and verified. Exact-request artifact intake may now reuse that verified inbox artifact, recompute normalized baseline and target-version validation, and persist `reply_validated` only after SHA-256, byte size, ZIP entry count, CRC, embedded version, selected answer identity, and no-mutation checks pass. No Project Source publication, registry/current mutation, adoption, Git commit, Git push, or formal MVP proof is claimed.


## v0.1.123.2.6 validated materialization migration correction

Accepted/current remains `v0.1.123.2.5`. The same-version replacement candidate makes exact validated protocol-run migration use the shared persisted-run normalizer and verified inbox artifact. `candidate-run` now preserves request `req_20260805T145619199617Z` plus the expected `chatgpt_claudecode_workflow-2_v0.1.124.zip`, `v0.1.124`, and repository identity. Focused migration integration is green; full candidate testing and adoption are not claimed.

## Active repair candidate — v0.1.125.3.3

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.2.zip` (`v0.1.125.3.2`)
- accepted baseline SHA-256: `c6e6617a22b526b6bb3ae7f65274ce6edd75898ce926e24bda204bfc8b68504f`
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.3.zip`
- active repair slice: v0.1.125.3.3 — Acceptance/adoption transactional reconciliation
- next normal slice: `v0.1.126 — Persistent whole-release ETA estimator`
- planned after repair acceptance: `v0.1.126 — Persistent whole-release ETA estimator`
- scope advancement: forbidden; repair only fixes action-aware acceptance/current result selection, post-side-effect reconciliation, idempotent stale-attempt recovery, and final state convergence


## Active repair candidate — v0.1.125.3.4.1

- control-plane accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.3.zip` (`v0.1.125.3.3`)
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.1.zip`
- active repair slice: v0.1.125.3.4.1 — Candidate-test retry isolation and authoritative runtime final convergence
- observed pre-repair authoritative Docker service: `promptbranch-service:0.1.125.2` on port `8000`
- required promotion: retag the exact tested candidate image as `promptbranch-service:0.1.125.3.4.1`, recreate only the canonical `chatgpt_claudecode_workflow` service on port `8000`, and require live health plus version/SHA/attempt labels to match before `ADOPTED_CURRENT`
- rollback: restore the previously healthy production image when promotion fails; keep the release attempt retryable
- cleanup: remove isolated `pb-candidate-*` service containers only after authoritative runtime convergence
- `FINAL_VERIFIED`: must independently re-probe the live port-8000 service and fail on runtime drift
- next normal slice remains `v0.1.126 — Persistent whole-release ETA estimator`; repair scope does not advance application work


## Active repair candidate — v0.1.125.3.4.2

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.1.zip` (`v0.1.125.3.4.1`)
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip`
- active repair slice: v0.1.125.3.4.2 — Post-adoption historical verification and final convergence
- no backward-compatibility path for superseded post-adoption candidate-liveness semantics
- next normal slice: `v0.1.126 — Persistent whole-release ETA estimator`


## v0.1.126.1.1.1.1.2 candidate

- Base candidate: `v0.1.126.1.1.1.1.1` (`264507a4921e1f885717ca0498581a352cf5e54a1b6c57363daba98522a0eb11`).
- Accepted/current remains `v0.1.125.3.4.2` (`ed6752cc7e1cf654f0e3ea505110599d5be3e067dbb00f07b8ae90cf34a9510f`).
- Repair: `RUNTIME_PREPARED` now requires a single healthy exact-baseline port-8000 runtime before candidate mutation and proves the same container, Docker image ID, and artifact SHA label remain afterward.
- Retry: production is re-snapshotted on each attempt; no automatic recovery is performed.
- Construction validation: focused/all release-state-machine tests plus deterministic release validation required.
- Live state: not accepted/current; `FINAL_VERIFIED` still pending.


## v0.1.126.1.1.1.1.3 candidate

- Base candidate: `v0.1.126.1.1.1.1.2`.
- Accepted/current remains `v0.1.125.3.4.2` (`ed6752cc7e1cf654f0e3ea505110599d5be3e067dbb00f07b8ae90cf34a9510f`).
- Repair: forward `PROMPTBRANCH_RELEASE_VALIDATION_PYTHON` through sanitized release-contract execution and prove foreign PATH pytest cannot override it.
- Predecessor live candidate test: 53/53 passed; publication stopped before Git commit.
- Live state: not accepted/current; `FINAL_VERIFIED` still pending.


## v0.1.128.1.1.1.1.1 diagnostic repair status

`v0.1.128.1.1.1.1` live-proved the pinned `ask_question` fresh-chain repair by returning `INTEGRATION_OK`, then failed later at `task_message_flow.ask` with a service-internal deadline while starting a new chat from the generated Project page. `v0.1.128.1.1.1.1.1` preserves all response-selection behavior and prior projection repairs unchanged and adds bounded structured diagnostics for response-chain freshness, project-page to conversation URL transitions, assistant candidate hashes/count deltas, generation/idle state, completion blockers, and the final timeout snapshot. `v0.1.129 — External application pilot bootstrap` remains blocked until this repair family reaches FINAL_VERIFIED/current.


## v0.1.128.2.4 — Accepted-baseline exact-byte self-healing repair

Live `v0.1.128.2.3` resolved the canonical project-scoped registry but failed `accepted_baseline_artifact_invalid`. `v0.1.128.2.4` keeps `(repo_id, version, sha256)` as immutable accepted authority while making physical byte location recoverable: recorded path, canonical SHA object, PB artifact caches, exact repo-local copy, and operator Downloads are bounded candidate locations; every copy must match the registered SHA, safe ZIP integrity, and embedded baseline VERSION before use. An exact recovered copy restores canonical object storage. Wrong-SHA or unavailable bytes fail closed. Accepted baselines are verified for immutable integrity rather than re-judged by newer candidate hygiene policy. Accepted/current remains `v0.1.128.1.1.1.1.1`; next normal remains `v0.1.129`; `.129` is blocked until this repair reaches FINAL_VERIFIED/current.

## Historical failed candidate — v0.1.128.2.6

Accepted/current baseline is `chatgpt_claudecode_workflow-2_v0.1.128.2.5.zip` at SHA-256 `07c6e41d29e932e99d8eda20eeee35de92acdd567df6e529b51aee252fb70d58`. Candidate `v0.1.128.2.6` is historical failed evidence and remains immutably bound to SHA-256 `4ac66b37cba7b3676d487f082e9fe64239fd97b71f53b10f66b28b67fe1cf026`; it must not be rebound to different bytes. Its construction-proven external-repository `pb skill sync` and bounded structured publication-timeout retry are carried forward by `v0.1.128.2.6.1`. Next normal remains `v0.1.129 — External application pilot bootstrap`; `v0.1.130 — Controlled external application change execution` follows after normal acceptance.

Construction state: all 17 canonical release-validation groups pass. DOD-578 through DOD-581 are construction-proven; DOD-582 remains live-pending until the exact frozen ZIP reaches FINAL_VERIFIED/current.


## Active repair — v0.1.128.2.6.1

Accepted/current baseline remains `chatgpt_claudecode_workflow-2_v0.1.128.2.5.zip` (`v0.1.128.2.5`) at SHA-256 `07c6e41d29e932e99d8eda20eeee35de92acdd567df6e529b51aee252fb70d58`. Active candidate is `chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.zip`. This is the immutable successor to historical `v0.1.128.2.6` after Promptbranch correctly rejected finalized replacement bytes with `artifact_identity_conflict` because `v0.1.128.2.6` was already bound to SHA-256 `4ac66b37cba7b3676d487f082e9fe64239fd97b71f53b10f66b28b67fe1cf026`. Product behavior remains the construction-proven external-repository `pb skill sync` plus structured bounded publication-timeout recovery from the finalized source tree; this repair changes release identity/control projection, not normal product scope. Live `FINAL_VERIFIED` plus fresh scoped current alignment remain pending. Next normal remains `v0.1.129`.


Construction proof is green for `v0.1.128.2.6.1`: 134 focused tests passed; the release-validation runner authority is `/opt/pyvenv/bin/python3` with pytest 9.0.2 in this construction environment; all 17 canonical constituent validation groups passed; deterministic release builds were byte-identical; and the canonical-name Artifact Guardian check passed. The aggregate parent process exceeded the artifact sandbox single-call lifetime, so constituent-group evidence is retained explicitly rather than claiming one uninterrupted aggregate invocation. Live lifecycle/adoption/current proof remains pending.

# Migration to Project Control Surface

## Migration status

```text
in_progress
```

## Existing planning/status documents

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/mvp-definition-of-done.md` | current_source | `docs/project/definition-of-done.md`, `docs/project/mvp.md` | initial_facts_migrated | Canonical historical MVP DoD source; not deleted. |
| `docs/design/orchestration/docs/current_status.md` | current_source | `docs/project/status.md`, `docs/project/release-status.md` | initial_facts_migrated | Contains current status through v0.1.66 but has stale accepted-baseline wording; v0.1.66 adoption evidence wins. |
| `docs/design/orchestration/docs/global_mvp_plan.md` | current_source | `docs/project/mvp.md`, `docs/project/plan.md` | initial_facts_migrated | Strategic JSON orchestration MVP source. |
| `docs/design/orchestration/docs/detailed_mvp_setup_plan.md` | current_source | `docs/project/plan.md` | referenced | Detailed setup context remains in place. |
| `docs/design/orchestration/docs/json_orchestration_state_mvp.md` | current_source | `docs/project/mvp.md`, `docs/project/plan.md` | referenced | Data-surface/control-plane MVP context. |
| `docs/design/orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md` | historical_reference | `docs/project/migration.md` | referenced | Original v0.1.0 canvas; useful history, not current baseline authority. |
| `docs/design/orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md` | historical_reference | `docs/project/migration.md` | referenced | Original v0.1.0 setup plan; partially superseded by later accepted releases. |
| `docs/design/orchestration/docs/release_line_reconciliation.md` | current_source | `docs/project/status.md`, `docs/project/release-status.md` | referenced | Reconciliation context for v0.1.x detours. |
| `docs/design/orchestration/decisions/ADR-0001-json-orchestration-state-mvp.md` | decision_record | `docs/project/decisions.md` | summarized | Full ADR remains in original location. |
| `docs/design/orchestration/decisions/ADR-0002-chatgpt-proposal-vs-promptbranch-accepted-event.md` | decision_record | `docs/project/decisions.md` | summarized | Full ADR remains in original location. |
| `docs/design/orchestration/decisions/ADR-0003-chatgpt-only-llm-provider.md` | decision_record | `docs/project/decisions.md` | summarized | Full ADR remains in original location. |
| `docs/design/orchestration/decisions/ADR-0004-ollama-bakeoff-failed-threshold.md` | decision_record | `docs/project/decisions.md` | summarized | Full ADR remains in original location. |
| `docs/design/promptbranch-release-baseline-evidence.md` | current_source | `docs/project/status.md`, `docs/project/decisions.md` | referenced | Baseline evidence terminology and candidate/accepted semantics. |
| `docs/design/promptbranch-mvp-living-design.md` | current_source | `docs/project/mvp.md`, `docs/project/plan.md` | referenced | Living design remains detailed source. |
| `docs/design/promptbranch-mvp-living-design.drawio` | current_source | `docs/project/migration.md` | referenced | Visual design source, not duplicated. |
| `docs/design/promptbranch-living-design-overview.md` | current_source | `docs/project/migration.md` | referenced | Overview remains detailed source. |
| `docs/design/promptbranch-living-design-overview.html` | current_source | `docs/project/migration.md` | referenced | HTML publication source. |
| `docs/release-v0.1.65.md` | release_evidence | `docs/project/release-status.md` | summarized | Accepted v0.1.65 release evidence. |
| `docs/release-v0.1.66.md` | release_evidence | `docs/project/release-status.md`, `docs/project/status.md` | summarized | Accepted v0.1.66 release evidence. |
| `docs/release-v*.md` | release_evidence | `docs/project/release-status.md` | partial_summary | Historical release notes remain in place. |
| `docs/repair-v*.md` | release_evidence | `docs/project/release-status.md` | referenced | Historical repair notes remain in place. |
| `docs/repair-v0.1.77.6.md` | release_evidence | `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Repair evidence for project-page delete-menu fallback and bounded scheduler validation timeout. |
| `docs/repair-v0.1.77.7.md` | release_evidence | `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Repair evidence for explicit resolved-project-url cleanup retry. |
| `docs/repair-v0.1.77.8.md` | release_evidence | `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Repair evidence for Docker-service cleanup retarget per-call project URL support. |
| `docs/promptbranch_ask_reply_protocol_design_and_mvp_plan.md` | historical_reference | `docs/project/migration.md` | referenced | Protocol design history. |
| `docs/promptbranch_mvp_current_state_and_plan_2026-05-24.md` | historical_reference | `docs/project/migration.md` | referenced | Earlier current-state doc; superseded by accepted v0.1.66 evidence. |
| `Promptbranch-as-Claude-Code-Shell-Operating-Model.updated-2026-05-03.txt` | historical_reference | `docs/project/migration.md` | referenced | Operating model history. |
| `promptbranch_mvp_plan_mcp_ollama_skills_agents_2026-05-03.md` | historical_reference | `docs/project/migration.md` | referenced | Earlier MCP/Ollama/skills MVP plan; superseded where later releases differ. |
| `promptbranch_native_release_lifecycle_todo.md` | historical_reference | `docs/project/plan.md`, `docs/project/migration.md` | referenced | Native lifecycle target remains useful roadmap but not current implementation status. |
| session logs and release logs | release_evidence | `docs/project/release-status.md` | referenced | Use as evidence references only; do not copy wholesale. |

## Known migration conflicts

| Topic | Source A | Source B | Current authority | Resolution |
|---|---|---|---|---|
| Accepted baseline | Older status docs mention v0.1.61 or earlier accepted baselines | User-provided `pb artifact current --json` confirms v0.1.66 | v0.1.66 adoption evidence | `docs/project/status.md` uses v0.1.66 as accepted/current. |
| Artifact naming | Older docs use `chatgpt_claudecode_workflow_v0.0.x.zip` | Current project uses `chatgpt_claudecode_workflow-2_v0.1.x.zip` | Current accepted artifact line | `docs/project/*` uses `chatgpt_claudecode_workflow-2_v0.1.66.zip` and next v0.1.67. |
| MVP identity | Older docs split MCP/agent, artifact intake, JSON orchestration, release lifecycle tracks | Current project needs one continuation control surface | Project control surface | `docs/project/mvp.md` frames these as tracks under one Promptbranch controlled workflow MVP. |
| Release lifecycle status | Native lifecycle TODO describes future complete lifecycle | v0.1.66 release note says release doctor remains read-only | Accepted v0.1.66 release evidence | `docs/project/status.md` keeps install/upload/adopt/push out of current scope. |

## Migration rules applied

1. Existing planning and status documents are preserved.
2. Historical documents are referenced rather than deleted.
3. Accepted baseline evidence overrides stale status text.
4. Large prose blocks are not copied wholesale.
5. Durable facts are moved into the control surface.
6. The migration slice does not change runtime or deployment behavior.

## Migration checklist

| ID | Migration item | Status | Evidence |
|---|---|---:|---|
| MIG-001 | Existing plan files identified | done | this file |
| MIG-002 | MVP definition created/updated | done | `docs/project/mvp.md` |
| MIG-003 | DoD checklist created/updated | done | `docs/project/definition-of-done.md` |
| MIG-004 | Current plan migrated | done | `docs/project/plan.md` |
| MIG-005 | Current status written | done | `docs/project/status.md` |
| MIG-006 | Release status table initialized | done | `docs/project/release-status.md` |
| MIG-007 | Decisions migrated | done | `docs/project/decisions.md` |
| MIG-008 | Obsolete documents marked historical or referenced | done | this file |
| MIG-009 | Focused validator added | done | `tests/test_project_control_surface.py` |
| MIG-010 | Candidate adopted/current | open | requires post-adoption `pb artifact current --json` |


## artifact-current repo-loop compatibility migration

| Old consumer path | New consumer path | Status | Notes |
|---|---|---:|---|
| `payload.state` | `payload.repos[repo_id].state` | migrated | Normal joined-project artifact-current consumers must use repo-loop sections. |
| `payload.registry_current` | `payload.repos[repo_id].registry_current` | migrated | Top-level parsing remains compatibility fallback only. |
| `payload.baseline_roles` | `payload.repos[repo_id].baseline_roles` | migrated | Operator/release helpers use normalized section selection. |
| `payload.runtime` | `payload.repos[repo_id].runtime` | migrated | Parallel ask baseline safety now reads repo-loop runtime data. |


## Repair migration note — v0.1.77.1

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/release-v0.1.77.md` | failed candidate release evidence | `docs/repair-v0.1.77.1.md`, `docs/project/release-status.md` | updated | v0.1.77 failed live browser temporary-project lifecycle validation; v0.1.77.1 repairs without advancing the slice. |


## Repair migration note — v0.1.77.2

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/repair-v0.1.77.1.md` | failed repair evidence | `docs/repair-v0.1.77.2.md`, `docs/project/release-status.md` | updated | v0.1.77.1 fixed fail-closed cleanup classification but still failed release-control when the project remained resolvable and a release-validation group timed out. v0.1.77.2 retries/retargets cleanup and isolates release-validation pytest subprocesses. |


## Repair migration note — v0.1.77.3

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/repair-v0.1.77.2.md` | failed repair evidence | `docs/repair-v0.1.77.3.md`, `docs/project/release-status.md` | updated | v0.1.77.2 fixed retry/retarget semantics but full release-control still failed when the exact-name project remained resolvable and normal sidebar removal could not find it. v0.1.77.3 adds a More-projects removal fallback. |

| `docs/repair-v0.1.77.4.md` | repair_evidence | `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md` | migrated | Documents rate-limit-aware cleanup repair; no normal slice advanced. |

| `docs/repair-v0.1.77.5.md` | repair_evidence | `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md` | migrated | Documents required root `.gitignore` packaging repair; no normal slice advanced. |

## Repair migration note — v0.1.77.9

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/repair-v0.1.77.8.md` | failed repair evidence | `docs/repair-v0.1.77.9.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | updated | v0.1.77.8 still failed source-add stale-inflight and cleanup project removal. v0.1.77.9 repairs validation defects only and does not advance normal scope. |

| `docs/repair-v0.1.77.10.md` | repair_evidence | `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Repair evidence for Docker service image pinning after stale service version in v0.1.77.9. |
| `docs/repair-v0.1.77.11.md` | repair_evidence | `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Repair evidence for non-anchor project cleanup fallback after v0.1.77.10 cleanup failure. |



## AG-001 migration note — v0.1.78

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `promptbranch_artifact_guardian_mvp.md` | planning_source | `docs/project/artifact-guardian-mvp.md`, `docs/project/plan.md`, `docs/project/definition-of-done.md`, `docs/project/release-status.md`, `docs/project/decisions.md` | migrated | AG-001 is the next normal release slice from accepted/current v0.1.77.11. Build/heal/agent/lifecycle/assistant handoff integration and k8s-game foundation are deferred. |


## Repair migration note — v0.1.78.1

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/release-v0.1.78.md` | failed candidate release evidence | `docs/repair-v0.1.78.1.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | updated | v0.1.78 AG-001 installed but failed full release-control in `project_source_add_file`; v0.1.78.1 repairs Project Source mutation transaction hardening/reporting only and does not advance normal scope. |


## Repair migration note — v0.1.78.2

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `promptbranch-service_0.1.78.1.log` | live failure evidence | `docs/repair-v0.1.78.2.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Live log proved the service can run real project deletion. v0.1.78.2 freezes public project deletion until a secure delete protocol exists. |


## Repair migration note — v0.1.78.2.1

`v0.1.78.2` introduced `promptbranch_project_delete_safety.py` but omitted it from setuptools `py-modules`. `v0.1.78.2.1` fixes packaging only; deletion remains frozen.


## Repair migration note — v0.1.78.2.2

`v0.1.78.2.1` failed release-control before normal validation because the candidate release-control script rejected `v0.1.78.2.1` as an invalid version. `v0.1.78.2.2` updates release-control, post-release-validation, and artifact-candidate schema version grammar to accept dotted numeric repair versions with at least three segments. Project deletion remains frozen.

## Repair migration note — v0.1.78.2.3

`v0.1.78.2.2` release-control completed successfully but the full browser test still created a unique temporary ChatGPT Project and retained it because project deletion is frozen. `v0.1.78.2.3` changes release-control to use one reusable retained quarantine project by default: `itest-promptbranch-retained-delete-frozen`. This prevents repeated creation of undeletable throwaway projects. Existing leaked `itest-promptbranch-*` projects are not deleted by the migration.



## Repair migration note — v0.1.78.2.4

`v0.1.78.2.4` changes live-test defaults away from temporary project creation/removal. The retained project `itest-promptbranch-retained-delete-frozen` is now the default for `ask-live`, `visual-artifact-roundtrip`, and `release-live`, and keep-project behavior is enforced while project deletion is frozen. Release-control adds `--run-all-tests` for one-command validation with continue-on-failure execution and a final GO/FIX summary. Existing leaked `itest-promptbranch-*` projects are not deleted by this migration.


## v0.1.78.2.5 migration note

Operators running the full validation stack should prefer `--run-all-tests`. The command now preflights `.pb_profile_local_debug`, runs live browser steps through a refreshed `release-live` profile-pool slot, and writes first-class rows for full direct, full localhost, live profile preflight, ask-live, visual-artifact-roundtrip, release-live, import-smoke, and artifact guard. `.pb_profile_local_debug_pools/` is ignored because it contains local cloned browser-profile state only.

## v0.1.78.2.6 migration note

No user data migration. Release operators should continue using normal cached Docker builds through release-control. `--no-cache` is now a bounded fallback when image or service provenance checks detect stale content. The new release logs include host context, image content, image inspect, container content, and health/version evidence.


## v0.1.78.2.7 migration note

No user data migration. Operators should rerun release-control with the v0.1.78.2.7 candidate. This repair only fixes Docker provenance probe JSON writer syntax; it does not alter project deletion, Project Source, or artifact adoption semantics.


## v0.1.78.2.8 migration note

No operator migration is required. Continue from accepted/current v0.1.78.2.3 unless explicitly testing the v0.1.78.2.8 candidate. Release-control should be rerun from the v0.1.78.2.8 ZIP to prove Docker host/image/container/health version alignment.


## v0.1.78.2.9 migration note

No user data migration is required. Operators should rerun release-control with the v0.1.78.2.9 candidate. This repair only fixes the Docker image/container pyproject version probe so it works under `set -u`; it does not alter project deletion, Project Source, artifact adoption, or run-all semantics.

## v0.1.78.2.10 migration note

No user data migration is required. Operators may set `PROMPTBRANCH_RUN_ALL_RATE_LIMIT_RETRIES`, `PROMPTBRANCH_RUN_ALL_RATE_LIMIT_COOLDOWN_SECONDS`, or `PROMPTBRANCH_RUN_ALL_RATE_LIMIT_SKIP_SLEEP=1` for controlled test environments. The default release-control path waits and retries once when a failed run-all step contains ChatGPT rate-limit evidence.

## v0.1.78.2.11 migration note

Operators who use `--run-all-tests` should authenticate `.pb_profile_local_debug/` once as the live-test seed profile. Release-control now preserves that seed across ZIP import while continuing to treat `.pb_profile_local_debug_pools/` as disposable generated state. No Project Source, adoption/current, or project deletion migration is performed.

## v0.1.78.2.12 migration note

No Project Source or adoption/current migration is performed. Operators should authenticate `.pb_profile_local_debug/` once before `--run-all-tests`. This repair changes only the text Project Source add trigger path so a no-op primary save click is followed by bounded fallback triggers before persistence verification.


## v0.1.78.2.13 migration note

Default `--run-all-tests` no longer treats text-source add/remove as release-blocking. Operators who need the full source-kind matrix must pass `--strict-source-kind-matrix`. For fast repair development of the known text-source path, use `--run-failing-tests`. No Project Source, adoption/current, or project deletion migration is performed.

## v0.1.78.2.14 migration note

No user data migration is required. This repair constrains Project Source remove/overwrite DOM discovery to the Project Sources surface and removes broad body/main fallback lookup from the source-card/remove path. Operators should first rerun the focused source-overwrite path before running full release-control. No Project Source, adoption/current, or project deletion migration is performed.


## v0.1.78.2.15 migration note

No Project Source, adoption/current, or project deletion migration is performed. This repair only prevents Project Source add/list/remove/capability operations and Project Source persistence refreshes from waiting on persisted conversation-history cooldown after a 429 modal is acknowledged. The cooldown remains recorded for history-reading operations. Operators should rerun only the focused file `src add` path before running full release-control.

| `docs/repair-v0.1.78.2.16.md` | repair_evidence | `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/status.md` | summarized | Repair evidence for file-source post-commit stale-inflight refreshed verification recovery; no normal slice advanced. |

## v0.1.78.2.17 migration note

No user data, Project Source, artifact-current, or project deletion migration is performed. Operators should install the candidate and run `scripts/smoke-pb-ask-prompt-file.sh` against the live ChatGPT profile before retrying CV generator live-call workflows. This repair only carries prompt-file submit intent into the browser layer, uses button-first submit for prompt-file asks, and keeps prepare-token-only states fail-closed.

| `Change Request Bug Report- pb ask --prompt-file submit causality failure.pdf` | live failure/change request evidence | `docs/repair-v0.1.78.2.17.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/status.md`, `docs/project/decisions.md` | summarized | Prompt-file ask calls loaded the composer but keyboard Enter could stop at prepare-token-only without backend commit; repair is button-first submit plus fail-closed diagnostics. |

## v0.1.78.2.18 migration note

No user data, Project Source, artifact-current, or project deletion migration is performed. Operators should install the candidate and rerun `scripts/smoke-pb-ask-prompt-file.sh`. If the smoke still fails, the diagnostic JSON is intentionally preserved and printed so the next repair can target the actual live failure instead of losing evidence in shell cleanup. This repair also disables keyboard Enter post-dispatch comparison for prompt-file button-click failures to preserve a single causal submit boundary.

## v0.1.78.2.19 migration note

| Source | Type | Destination | Disposition | Notes |
| --- | --- | --- | --- | --- |
| Operator smoke output from `v0.1.78.2.18` | live repair evidence | `docs/repair-v0.1.78.2.19.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | The diagnostic-preserving smoke exposed the missing automation-wrapper `prefer_button_submit` keyword support. |

## v0.1.78.2.20 migration note

No user data, Project Source, artifact-current, or project deletion migration is performed. Operators should install the candidate and rerun `scripts/smoke-pb-ask-prompt-file.sh`. This repair only updates the prompt-file live smoke contract for the existing `pb ask --json` structured-answer mode and exposes successful submit-causality fields at the top level of ask JSON output.

| Source | Type | Destination | Disposition | Notes |
| --- | --- | --- | --- | --- |
| Operator smoke output from `v0.1.78.2.19` | live repair evidence | `docs/repair-v0.1.78.2.20.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Live submit reached ChatGPT and returned a fresh answer through button click; the remaining defect was smoke/output normalization. |

## v0.1.78.2.20.1 migration note

No user data, Project Source, artifact-current, or project deletion migration is performed. This repair only adds the missing release-control `--adopt-after-validation` option so the operator can run a single full validate-then-adopt command after the focused prompt-file smoke has passed.


## v0.1.78.2.20.2 migration note

No user data, Project Source, artifact-current, or project deletion migration is performed. This repair only changes `pb ask --prompt-file` transport selection for large prompt files: large files are attached automatically, small files remain inline, and operators can force either behavior with `--prompt-file-mode inline` or `--prompt-file-mode attach`.

| Source | Type | Destination | Disposition | Notes |
| --- | --- | --- | --- | --- |
| `Bug Report - Promptbranch Submit Issue.pdf` and CV raw stdout/stderr/session log | live failure/change request evidence | `docs/repair-v0.1.78.2.20.2.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Large CV RAG prompt-file submit used button click but lacked committed-turn proof; repair moves large prompt packages to attachment transport instead of weakening stale-answer guards. |

## v0.1.78.2.20.3 migration note

No user data, Project Source, artifact-current, CV generator, or project deletion migration is performed. This repair only flattens large prompt-file attachment diagnostics onto top-level ask JSON fields. Operators should rerun `scripts/smoke-pb-ask-large-prompt-file.sh` or the CV RAG prompt-file command and inspect top-level `attachment_*`, `submit_*`, and `response_*` fields before full release-control/adoption.

| Source | Type | Destination | Disposition | Notes |
| --- | --- | --- | --- | --- |
| `Bug Report - Prompt File Attachment Mode.pdf` and successful `.20.2` large CV prompt smoke log | live change-request/evidence | `docs/repair-v0.1.78.2.20.3.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Attachment transport worked, but the top-level JSON envelope did not expose enough attachment/upload/submit/response causality evidence for automated gates. |

## v0.1.78.2.20.4 migration note

No user data, artifact-current, CV generator, prompt-file transport, or project deletion migration is performed. This repair only changes Project Source text-add validation for retained integration tests: large text is treated as potential `.txt` document conversion, generic `pasted.txt Document` is not accepted without current-run proof, and stale retained-test sources may be pruned at the observed five-source boundary.

| Source | Type | Destination | Disposition | Notes |
| --- | --- | --- | --- | --- |
| Focused `project_ensure` + `source_add_text` repro and UI screenshot showing generated `.txt` document chip | live failure/change request evidence | `docs/repair-v0.1.78.2.20.4.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Repro isolated `project_source_add_text` from prompt-file attachment work and showed no rate-limit evidence; UI evidence supports document-conversion-aware verification. |

## v0.1.78.2.20.5 migration note

No user data, artifact-current, CV generator, prompt-file transport, or project deletion migration is performed. This repair changes only Project Source text-add classification for large document-converted text sources: generic `pasted.txt` / `Document` identities are no longer sufficient proof unless the saved document/card can be tied to the current run id. Generated/dedicated `.txt` names remain supported when they expose the run anchor.

| Source | Type | Destination | Disposition | Notes |
| --- | --- | --- | --- | --- |
| Focused `.20.4` source-add repro and operator UI observation about generated `.txt` names | live evidence/change request | `docs/repair-v0.1.78.2.20.5.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | `.20.4` cleared save/persistence but not the stricter content-proof contract for generic document-converted text. |

## v0.1.78.2.20.6 migration note

No user data, artifact-current, CV generator, prompt-file transport, release-control, or project deletion migration is performed. This repair changes only Project Source text-add validation: legacy `pasted.txt` / `pasted.txt Document` entries are retained-test cleanup noise only, while current large text-source conversion must surface a dedicated/generated document name containing the current run anchor.

| Source | Type | Destination | Disposition | Notes |
| --- | --- | --- | --- | --- |
| Focused `.20.5` source-add repro and operator clarification about generated document names | live evidence/change request | `docs/repair-v0.1.78.2.20.6.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | `.20.5` failed closed on `pasted.txt Document`; `.20.6` treats that path as legacy/stale and requires the current generated-name contract. |

## v0.1.78.2.20.7 migration note

No user data, artifact-current, CV generator, prompt-file transport, release-control, or project deletion migration is performed. This repair changes only Project Source text-add release validation: source-add persistence remains release-blocking, while large pasted text document naming is diagnostic characterization rather than a hard generated-name contract.

| Source | Type | Destination | Disposition | Notes |
| --- | --- | --- | --- | --- |
| Focused `.20.6` `source_add_text` rerun after cooldown | live evidence/change request | `docs/repair-v0.1.78.2.20.7.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Persistence verified with `source_match=pasted.txt Document`; `.20.7` makes that naming behavior non-release-blocking while preserving diagnostics. |

## v0.1.78.2.20.8 migration note

No user data, artifact-current, CV generator, prompt-file transport, or broad project deletion migration is performed. This repair changes only integration-test lifecycle handling: fresh `itest-promptbranch-*` projects created by the current run may be cleaned up through a strict same-run identity proof, expected pre-create missing-project resolution is classified as informational/pass, and the scheduler/source lifecycle validation group receives a larger timeout.

| Source | Type | Destination | Disposition | Notes |
| --- | --- | --- | --- | --- |
| Fresh `.20.7` `project_ensure + source_add_text` repro | live evidence/change request | `docs/repair-v0.1.78.2.20.8.1.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Source add passed on a fresh project, but cleanup was absent and expected pre-create missing-project resolution was counted as a failure. |

## v0.1.78.2.20.8.1 migration note

No runtime migration is required. This repair preserves the `.20.8` implementation and fixes only the release ZIP packaging surface by ensuring the required repo-root `.gitignore` control file is present in the archive.


## v0.1.78.2.20.8.2 migration note

No user data, Project Source, artifact-current, or prompt-file transport migration is performed. This repair fixes only same-run ephemeral test-project cleanup URL normalization after `.20.8.1` failed `/v1/projects/remove` with a missing `_normalize_project_url` helper. Project deletion remains frozen for all normal/user projects.

## v0.1.78.2.20.8.3 migration note

No user data, Project Source content, artifact-current, prompt-file transport, or broad project deletion migration is performed. This repair only changes validation/recovery logic: slugged same-run ephemeral Project URLs are compared by canonical Project id for cleanup safety, and committed text-source saves receive bounded post-commit Project Sources refresh recovery before failing closed.

## v0.1.78.2.20.8.4 migration note

No user data, Project Source content, artifact-current, prompt-file transport, or normal release slice migration is performed. This repair supersedes the same-run ephemeral cleanup exception from `v0.1.78.2.20.8.3`: all Project deletion paths are now immutable-frozen, and focused integration cleanup retains Projects without calling a remove service.

## v0.1.78.2.20.8.5 migration note

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/repair-v0.1.78.2.20.8.4.md` | base repair evidence | `docs/repair-v0.1.78.2.20.8.5.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | updated | v0.1.78.2.20.8.4 fixed Project deletion behavior but left a stale top-level cleanup-policy label in fresh-project evidence. v0.1.78.2.20.8.5 repairs evidence wording only and does not advance a normal slice. |

## v0.1.78.2.20.8.6 migration note

No user data, Project Source content, artifact-current registry, prompt-file transport, or normal release slice migration is performed. Joined repositories now read Promptbranch workflow state from the project-scoped profile by default, matching existing task/source/artifact state writes. Repo-local `.pb_profile/.promptbranch_state.json` files may remain as stale legacy state but are no longer the default authority for joined repos unless `--profile-dir` is explicitly supplied.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/repair-v0.1.78.2.20.8.5.md` | base repair evidence | `docs/repair-v0.1.78.2.20.8.6.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | updated | v0.1.78.2.20.8.5 fixed cleanup-policy evidence wording; v0.1.78.2.20.8.6 repairs joined-repo state authority consistency only and does not advance a normal slice. |

## v0.1.78.2.20.8.7 migration note

No user data, Project Source content, artifact-current registry, prompt-file transport, response completion semantics, or normal release slice migration is performed. This repair only initializes the plain-text response wait diagnostic breakdown before deadline/debug bookkeeping writes to it.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/repair-v0.1.78.2.20.8.6.md` | base repair evidence | `docs/repair-v0.1.78.2.20.8.7.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | updated | v0.1.78.2.20.8.6 fixed joined-repo state authority; v0.1.78.2.20.8.7 repairs the plain-text response wait debug/deadline `NameError` only and does not advance a normal slice. |

## v0.1.78.2.20.8.8 migration note

No user data, Project Source content, artifact-current registry, prompt-file transport, response completion semantics, or normal release slice migration is performed. This repair only changes localhost full-test/source-add diagnostics: the source-add service client waits long enough for fail-closed post-commit recovery diagnostics, and retained-project source-add failures attach a `pb src list --json` diagnostic before the harness raises.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/repair-v0.1.78.2.20.8.7.md` | base repair evidence | `docs/repair-v0.1.78.2.20.8.8.md`, `docs/project/status.md`, `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | updated | v0.1.78.2.20.8.7 fixed plain-text response-wait diagnostics; live run-all evidence then isolated the remaining blocker to localhost source-add timeout masking a structured stale-inflight fail-closed result. |

## v0.1.79 migration note

No user data, Project Source content, artifact-current registry, browser profile, or deployment migration is performed. `v0.1.79` resumes the normal MVP line from accepted/current `v0.1.78.2.20.8.8` and adds only a read-only JSON orchestration event-intake proposal surface.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/design/orchestration/docs/current_status.md` | historical orchestration line status | `docs/project/status.md`, `docs/project/plan.md`, `docs/design/orchestration/docs/event_intake_foundation.md` | summarized | Earlier orchestration documents are preserved. `v0.1.79` narrows the next normal slice to proposal-only event intake rather than broad k8s-game runtime work. |


## v0.1.80 migration note

No user data, Project Source content, artifact-current registry, browser profile, deployment, or accepted-event ledger migration is performed. `v0.1.80` continues from accepted/current `v0.1.79` and adds only a read-only accepted-event validation foundation. Existing accepted-event fixtures are updated with explicit accepted/current baseline binding to `chatgpt_claudecode_workflow-2_v0.1.79.zip`.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `scripts/orchestration/validate_accepted_event.py` | script-only accepted-event fixture validator | `pb orchestration validate-accepted-event`, `docs/project/status.md`, `docs/project/plan.md`, `docs/project/definition-of-done.md` | promoted | The validator remains read-only and fail-closed; no ledger write or runtime execution is introduced. |
| `docs/design/orchestration/examples/accepted_events/*.json` | committed accepted-event fixtures | `docs/design/orchestration/schemas/accepted_event.schema.json` and validator tests | strengthened | Fixtures now bind to explicit accepted/current baseline artifact/source refs. |


## v0.1.80 candidate correction migration note

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `scripts/orchestration/validate_accepted_event.py` | source-tree compatibility wrapper | `promptbranch_orchestration.py` | migrated | Accepted-event validation logic now lives in installed module code so `pb orchestration validate-accepted-event` does not depend on a repo-local script under pipx/site-packages. |

## v0.1.81 migration note

No user data, Project Source content, artifact-current registry, browser profile, deployment, or accepted-event ledger migration is performed. `v0.1.81` is a focused working slice on top of the `v0.1.80` working candidate context. It adds only a dry-run accepted-event promotion preview and preserves the accepted/current baseline as `chatgpt_claudecode_workflow-2_v0.1.79.zip` until a later full promotion/adoption gate.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `pb orchestration validate-accepted-event` | read-only accepted-event validation command | `pb orchestration accept-event --dry-run --json` | extended | Dry-run promotion reuses validation and returns previews without writing accepted state. |
| `docs/design/orchestration/examples/accepted_events/*.json` | committed accepted-event fixtures | dry-run accepted-event previews | reused | Fixtures remain data-only and no ledger write path is introduced. |

## v0.1.82 migration note

No user data, Project Source content, artifact-current registry, browser profile, deployment, or accepted-event ledger migration is performed. `v0.1.82` is a focused working slice on top of the `v0.1.81` working candidate context. It adds only explicit repo-local accepted-event input support for dry-run previews and preserves the accepted/current baseline as `chatgpt_claudecode_workflow-2_v0.1.79.zip` until a later full promotion/adoption gate.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `pb orchestration accept-event --dry-run --json` | committed-fixture dry-run preview command | explicit input dry-run preview | extended | Explicit accepted-event files may be supplied only when they resolve inside the repository root. Unsafe, missing, or invalid input fails closed. |
| `docs/design/orchestration/examples/accepted_events/*.json` | committed accepted-event fixtures | explicit input examples and regression tests | reused | Fixtures remain data-only and no ledger write path is introduced. |

## v0.1.82 candidate correction migration note

No user data migration. Reinstall the corrected `chatgpt_claudecode_workflow-2_v0.1.82.zip` candidate before rerunning `pb orchestration accept-event --dry-run --json <repo-relative accepted-event file>`. This correction only fixes installed-runtime explicit path/root resolution and does not write accepted state or mutate Project Source/artifacts/deployment/runtime.

## Migration note — v0.1.83 accepted-event ledger scaffold

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/design/orchestration/accepted_event_ledger/README.md` | current_source | `docs/project/plan.md`, `docs/project/status.md`, `docs/project/definition-of-done.md` | summarized | Defines the future append-only accepted-event ledger path and explicitly keeps writes out of scope. |
| `docs/design/orchestration/schemas/accepted_event_ledger_record.schema.json` | current_source | `docs/project/definition-of-done.md` | referenced | Record schema scaffold for future ledger appends; no ledger file is created in v0.1.83. |

## Migration note — v0.1.84 accepted-event ledger validation

No user data, Project Source content, artifact-current registry, browser profile, deployment, or accepted-event ledger migration is performed. `v0.1.84` is a focused working slice on top of the `v0.1.83` working candidate context. It adds only a read-only ledger validation command and preserves the accepted/current baseline as `chatgpt_claudecode_workflow-2_v0.1.79.zip` until a later full promotion/adoption gate.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/design/orchestration/accepted_event_ledger/README.md` | ledger scaffold documentation | `pb orchestration validate-ledger --json`, `docs/project/plan.md`, `docs/project/status.md`, `docs/project/definition-of-done.md` | extended | Ledger scaffold remains read-only; no ledger file is created or appended. |
| `docs/design/orchestration/schemas/accepted_event_ledger_record.schema.json` | future ledger record schema scaffold | `pb orchestration validate-ledger --json` | referenced | Validator checks schema/scaffold and existing JSONL records if a ledger file exists. |

## v0.1.84 candidate hygiene note

The `v0.1.84` candidate restores the required repo-root `.gitignore` after Artifact Guardian reported it missing from the focused working chain. The restored ignore file covers generated/cache/local profile outputs, including `.pb_profile_local_debug_pools/`. No accepted-event ledger write, Project Source mutation, artifact adoption/current mutation, deployment, or model execution migration is performed.


## Repair migration note — v0.1.84.1

`v0.1.84.1` supersedes the old retained-quarantine live-test default from `v0.1.78.2.3`/`v0.1.78.2.4` for new validation runs. Project deletion remains frozen, but release-control and live-test profiles now use a fresh run-scoped Project name by default to avoid accumulating browser/project history in one retained Project. Existing retained/leaked test Projects are not deleted by this repair. No ledger/write scope advanced.


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


## v0.1.84.5.4 migration note

No user data migration is required. Operators should install the candidate and rerun the previously rate-limit-contaminated focused live test. The change only affects recovered 429 classification after functional live-test success; it does not change project deletion, Project Source, artifact adoption/current, ledger/write, deployment, or model-execution behavior.


## v0.1.84.5.5 migration note

No migration is required. The repair changes release-control classification/retry policy only. Existing logs and artifact registries are unchanged.

## v0.1.84.5.6 repair note

`v0.1.84.5.6` repairs release-control `--run-all-tests` live Project reuse on top of `v0.1.84.5.5`. The run-all live phase now ensures one run-scoped ChatGPT Project once after live profile preflight and passes the returned Project URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This prevents every live subtest from creating a separate retained Project while preserving delete-frozen safety, 50-character Project name caps, project-create recovery, recovered 429 retry suppression, and visual artifact reply-envelope hardening. No ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.7 repair note

`v0.1.84.5.7` repairs the shared live Project ensure command introduced in `v0.1.84.5.6`. Release-control `--run-all-tests` now uses the supported top-level `pb project-ensure` command to create or resolve one run-scoped ChatGPT Project, extracts the returned Project URL, and passes that exact URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This preserves the one-Project-per-full-test-run policy without calling the unsupported nested `pb project ensure` surface. No project deletion, ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.8 migration note

No user data migration is required. Operators should rerun release-control with `v0.1.84.5.8` when validating the `v0.1.84.5.x` repair line. The repair adds bounded service recovery after browser-backed `ReadTimeout` evidence in run-all logs before continuing to later browser-backed phases. Project deletion remains frozen, and no ledger, Project Source, artifact adoption/current, deployment, or model-execution migration is performed.

## v0.1.84.5.9 migration note

No user data migration is required. Operators should rerun release-control with the `v0.1.84.5.9` candidate after `v0.1.84.5.8` proved the browser ReadTimeout cascade was repaired but exposed brittle `live_project_ensure` URL extraction. This repair changes release-control parsing/status handling only and does not mutate Project Sources, artifact current state, ledger state, deployment, or ChatGPT Project deletion behavior.

## v0.1.84.5.10 migration note

No user data, Project Source, artifact-current, or ChatGPT Project deletion migration is performed. Operators should rerun release-control with the `v0.1.84.5.10` candidate. This repair only isolates duplicate offline release-validation groups from localhost browser transport state and hardens ask-live streaming-timeout classification for visibly present sentinels.

## v0.1.84.5.10.1 migration note

No user data, Project Source, artifact-current, deployment, or ChatGPT Project deletion migration is performed. Operators should use this repair candidate when validating the `v0.1.84.5.10` line because it prevents localhost/offline validation groups from sleeping or retrying on live-browser rate-limit telemetry.

## v0.1.84.5.10.2 migration note

No user data, Project Source, artifact-current, deployment, or ChatGPT Project deletion migration is performed. Operators should use this repair candidate after `v0.1.84.5.10.1` because it narrows the localhost/offline cooldown denylist back to `full_localhost`/offline groups and fixes all-tests summary selection for recovered live-test command result payloads.

## v0.1.84.5.10.3 migration note

No user data, Project Source, artifact-current, deployment, or ChatGPT Project deletion migration is performed. Operators should use this repair candidate after `v0.1.84.5.10.2` when validating the repair line because it fixes ask-live recovered-success all-tests summary classification while preserving localhost/offline cooldown denial and live source-add failure visibility.

## v0.1.84.5.11 migration note

No user data, Project Source, artifact-current, deployment, or ChatGPT Project deletion migration is performed. Operators should use the new all-tests and full-transport diagnostics in release-control summaries to identify source-add ReadTimeout, rate-limit, retry-denial, and transport-boundary failures before rerunning full live validation.

## v0.1.84.5.12 migration note

No historical documents are replaced or deleted. This release adds an explicit ask-target selection rule to the project control surface: default asks continue the remembered task conversation, while `pb ask --new-task` / `--new-conversation` starts from the remembered Project home. Existing state-file semantics are preserved except that fresh-task state replacement is now gated on successful returned conversation binding and submission evidence.

## v0.1.84.5.12.2 migration note

No user data, Project Source, artifact-current, deployment, or ChatGPT Project deletion migration is performed. Operators should use this repair candidate after `v0.1.84.5.12.1` because it narrows the offline scheduler/source release-validation group to explicit deterministic pytest nodeids and preserves the active `pb ask --new-task` slice unchanged.


## v0.1.85 migration note

No user data migration is required. Operators should update short `pb ask --new-task` proofs and shell snippets to read `.current.conversation_url` from `.pb_profile/.promptbranch_state.json`. The top-level `.conversation_url` path is a stale schema-v1 assumption and is not authoritative for Promptbranch schema-v2 state.

Use `pb state --proof` or `scripts/smoke-pb-ask-new-task.sh` for a read-only proof contract and short live smoke respectively. No Project Source, artifact adoption/current, backend API, MkDocs, or Project deletion behavior is changed by this slice.

## v0.1.86 migration note

No user data, Project Source, artifact-current, accepted-event ledger, Docker, Kubernetes, Helm, or ChatGPT Project migration is performed.

This release reconciles existing planning/status documents to accepted/current `chatgpt_claudecode_workflow-2_v0.1.85.zip` before any k8s-game implementation starts.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/design/orchestration/docs/current_status.md` | stale orchestration status | same file plus `docs/project/status.md` | updated | Rebased current status from v0.1.79-era wording to v0.1.85 accepted baseline. |
| `docs/design/orchestration/docs/global_mvp_plan.md` | orchestration plan | same file plus `docs/project/plan.md` | updated | Clarifies v0.1.86 reconciliation, v0.1.87 static-source-only candidate direction, and v0.1.88 deploy-gate direction. |
| `docs/design/orchestration/docs/detailed_mvp_setup_plan.md` | detailed handoff plan | same file plus `docs/project/plan.md` | updated | Adds v0.1.86 handoff and validation checklist. |
| `docs/design/orchestration/docs/k8s_game_mvp_contract.md` | k8s-game contract | same file plus `docs/project/decisions.md` | updated | Confirms no implementation/deploy in v0.1.86 and requires a later deploy evidence gate. |

## v0.1.87 migration note

No user data, Project Source, artifact-current, accepted-event ledger, Docker, Kubernetes, Helm, or ChatGPT Project migration is performed.

This release adds a new loop target schema and dry-run planner. Existing k8s-game planning documents are preserved; the static game becomes a future target fixture for the loop engine instead of the primary product goal.

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/design/orchestration/docs/k8s_game_mvp_contract.md` | k8s-game planning contract | future loop target fixture plus `examples/loop-targets/static-game-dry-run-target.json` | preserved | No game source or deployment is added. |
| `docs/project/plan.md` | release plan | same file | updated | Adds `v0.1.87` loop target schema and dry-run planner slice. |
| `docs/project/status.md` | current status | same file | updated | Records accepted/current `v0.1.86` baseline and `v0.1.87` candidate safety posture. |

## v0.1.87.1 migration note

No user data, Project Source, artifact-current, accepted-event ledger, Docker, Kubernetes, Helm, or ChatGPT Project migration is performed. This repair updates packaging metadata only so the installed CLI includes the `promptbranch_loop` top-level module required by `promptbranch_cli.py`.

## v0.1.88 migration note

The release-control validation model now records direct full-test evidence under the release log validation-evidence directory and may reuse it during `--run-all-tests` only when the evidence is still valid for the current artifact SHA and validation dimensions. Existing release logs without this evidence are treated as missing evidence and therefore cause a rerun, not reuse.

## v0.1.88.1 repair migration note

No user data, Project Source, artifact-current, or Project deletion migration is performed. Operators should install `v0.1.88.1` and rerun the normal `--run-tests --adopt-after-validation` gate before attempting the `--run-all-tests` evidence-reuse proof. This repair only extends Docker-service source-add timeout handling and adds structured timeout diagnostics; it does not advance the evidence-reuse slice.

## v0.1.89 migration note

No user data, Project Source, artifact-current, deployment, Kubernetes, or ChatGPT Project deletion migration is performed. Operators should use `pb test report <full-test-log> --json` after live validation to review `timing_summary` and `browser_action_audit` before repeatedly running broad `--run-all-tests`. The new audit is read-only observability and does not change live mutation semantics.


## v0.1.90 migration note

| Existing file | Current role | Migrated to | Migration status | Notes |
|---|---|---|---|---|
| `docs/release-v0.1.89.md` | accepted observability release evidence | `docs/project/status.md`, `docs/project/plan.md`, `docs/project/decisions.md`, `docs/project/definition-of-done.md` | extended | v0.1.90 follows the v0.1.89 timing/click audit evidence by reducing global conversation-history/backend-api 429 pressure. |

| `docs/repair-v0.1.90.1.md` | repair_evidence | `docs/project/release-status.md`, `docs/project/definition-of-done.md`, `docs/project/decisions.md` | summarized | Repair evidence for file-source overwrite stale-inflight post-commit recovery; preserves v0.1.90 conversation-history shield scope and does not advance normal slice scope. |

## v0.1.91 migration note

No user data, Project Source, artifact-current, deployment, Kubernetes, or ChatGPT Project deletion migration is performed. Operators should run `--run-tests --strict-source-kind-matrix` first, then run `--run-all-tests --strict-source-kind-matrix` for reuse proof. The all-tests summary now includes `validation_reuse` and `localhost_matrix_cooldown_audit` sections for operator review.


## Repair migration note — v0.1.91.1

No user data, Project Source, artifact-current, Project deletion, loop, Kubernetes, or deployment migration is performed. This repair changes only ask-live first-turn transient retry classification and all-tests summary payload ranking. Operators should rerun `v0.1.91.1 --run-tests --adopt-after-validation` before retrying `--run-all-tests`.

## Repair migration note — v0.1.91.2

No user data, Project Source, artifact-current, Project deletion, loop, Kubernetes, or deployment migration is performed. This repair changes only release-control all-tests summary extraction/ranking for noisy pretty-printed live command JSON. Operators should rerun `v0.1.91.2 --run-tests --adopt-after-validation`; after adoption, rerun `--run-all-tests` to prove final summary aggregation.

## Repair migration note — v0.1.91.3

`v0.1.91.2` retained the run-all aggregation repair but failed before validation when Docker service verification produced `container_not_found` after no-cache recreate. `v0.1.91.3` migrates that failure into an explicit Docker lifecycle diagnostic path with clean-system preflight, Compose service-ID lookup, running/health wait, and diagnostics collection. No normal slice advanced.

## Repair migration note — v0.1.91.4

The clean-system `v0.1.91.3` attempt failed before post-release Docker verification because no service was running when release-control called `promptbranch src add`. `v0.1.91.4` migrates that defect into an explicit pre-source-add bootstrap contract: install candidate CLI first, verify/bootstrap the candidate service, then mutate Project Source. The `v0.1.91.1`, `v0.1.91.2`, and `v0.1.91.3` repairs are preserved; no normal slice advanced.


## v0.1.91.5 migration note

No data migration. Release-control summary parsing is narrowed to select the authoritative `ensure_project` command payload for `live_project_ensure`.


## Repair migration note — v0.1.91.6

No data migration. This repair changes only release-control adopt-after-validation report-path selection for run-all evidence reuse. Operators should rerun `v0.1.91.6 --run-all-tests --adopt-after-validation` to prove the footer no longer crashes after `all_tests_final_verdict=GO`.


## Repair migration note — v0.1.91.7

No data migration. This repair changes release-control Docker bootstrap behavior only. Existing Docker images may remain locally, but the pre-source-add candidate service build uses `--no-cache --pull` and explicit repo-root Compose invocation. Operators should rerun `v0.1.91.7 --run-all-tests --adopt-after-validation` to prove the Docker freshness guard and adoption footer path.


## Repair migration note — v0.1.91.8

No data migration. This repair changes release-control run-all orchestration only: `full_localhost` reuses matching direct browser/source lifecycle evidence instead of rerunning live Project Source mutations. Operators should rerun `v0.1.91.8 --run-all-tests --adopt-after-validation` to prove the single-live-browser-source-lifecycle flow.

## Repair migration note — v0.1.91.9

No data migration. This repair changes only release-control adopt-after-validation report-path selection for reused `full_localhost` lifecycle evidence and adds operator-facing run-all progress telemetry. Operators should rerun `v0.1.91.9 --run-all-tests --adopt-after-validation` to prove the footer no longer requires `pb_test.full.localhost.<version>.report.json` when `full_localhost` is reused.

## Repair migration note — v0.1.91.10

No data migration. This repair changes release-control/test-suite diagnostics only: run-all progress JSON uses `chr(10)` for safe newline writing, and the `browser_scheduler_source_lifecycle` release-validation group reports per-nodeid progress and timeout diagnostics. Operators should rerun `v0.1.91.10 --run-all-tests --adopt-after-validation`; if the scheduler group times out, inspect the reported `active_nodeid` instead of guessing from empty stdout/stderr tails.


## v0.1.92 migration note

No user data, Project Source, artifact-current, or deployment migration is performed. Operators may use `pb loop run --target <file> --state-only` to print the planned loop state walkthrough only. Existing `pb loop run` dry-run output remains available. The Kubernetes game remains a future acceptance scenario and is not implemented or deployed in this slice.


## v0.1.93 migration note

No operator data migration is required. `v0.1.93` adds a presentation-only planned-action walkthrough for MVP-1. Existing `pb loop validate`, `pb loop plan`, `pb loop run`, and `pb loop run --state-only` behavior is preserved. Operators can use `pb loop run --planned-actions` to inspect the action/gate sequence without executing any actions.

## v0.1.93.1 repair migration note

No operator data migration is required. `v0.1.93.1` repairs the `v0.1.93` release-validation environment only. Existing loop target files, state-only walkthrough behavior, and planned-action walkthrough behavior are preserved.

## v0.1.94.1 repair migration note

The `v0.1.94.1` repair preserves the intended `v0.1.94` read-only loop execution work and migrates the Project Source capacity-prune drift finding into the control surface. No existing planning documents are deleted or replaced. The old `v0.1.85` reference is treated only as an old Project Source prune candidate, not as the current baseline.


## v0.1.95 migration note

No user data, Project Source, artifact-current, deployment, Kubernetes, or ChatGPT Project deletion migration is performed. Operators may use `pb loop run --read-only-execution --evidence-report --json` to inspect the compact evidence report. Existing `validate`, `plan`, `run`, `--state-only`, `--planned-actions`, and `--read-only-execution` behavior is preserved.

## v0.1.96 migration note

No user data, artifact-current, deployment, Kubernetes, or ChatGPT Project deletion migration is performed. Operators should expect generated release ZIP Project Sources to be retained per repository family with a maximum of five entries after upload. Promptbranch will only auto-prune same-family generated release ZIPs; documentation and non-generated Project Sources remain operator-managed.

## v0.1.97 migration note

No user data migration is required. Operators can use `pb loop run --read-only-execution --evidence-gate` to get a deterministic pass/block decision over the existing read-only evidence report. The gate remains non-mutating and does not execute validation commands.


## v0.1.97.1 repair migration note

No user data migration is required. This repair changes only text-source Project Source post-commit reconciliation after a stale-inflight save. Existing loop target files and `pb loop run --read-only-execution --evidence-gate` behavior are preserved. Operators should rerun full release-control/adoption for `v0.1.97.1` before treating it as current.


## v0.1.98 migration note

No user data, Project Source, artifact-current, deployment, Kubernetes, or ChatGPT Project deletion migration is performed. This slice migrates current planning authority into `docs/project/plan-state.json` and adds the anti-drift validator `pb project validate-control-surface --json`. Existing historical planning documents remain preserved; current-state fields in `docs/project/status.md`, `docs/project/plan.md`, and `docs/project/release-status.md` must agree with plan-state before release validation can pass. First controlled read-only validation command execution remains deferred to `v0.1.99`.

## v0.1.99 migration note

No user data, Project Source, artifact-current, deployment, Kubernetes, or ChatGPT Project deletion migration is performed. This slice migrates the next-slice derivation process into repo authority by adding `docs/project/architecture.md`, `docs/project/slice-horizon.md`, machine-readable `rolling_slice_horizon` state in `docs/project/plan-state.json`, and the `pb project next-slice --json` command. First controlled read-only validation command execution is explicitly deferred to `v0.1.100`.


## v0.1.99.1 repair migration note

`v0.1.99.1` does not migrate user data, Project Sources, artifact-current state, deployment, Kubernetes state, or ChatGPT Projects. It preserves the `v0.1.99` rolling slice horizon and repairs only release-control/Docker build-context freshness after deterministic ZIP-installed files retained fixed mtimes. `v0.1.100` remains deferred until the repaired `v0.1.99` line is accepted/current.


## v0.1.100 migration note

No user data, Project Source state, artifact-current state, deployment, Kubernetes state, or ChatGPT Projects are migrated. This slice adds a repo-local read-only command execution fixture and command evidence schema only. `v0.1.101` remains the next planned slice for read-only command result diagnosis; correction planning and file mutation remain out of scope.


## v0.1.100.1 migration note

Migrates the failed `v0.1.100` release-control evidence into a repair-only Project Source text-add recovery diagnostic improvement. Existing rolling-horizon authority is preserved: active normal slice remains `v0.1.100`, the repair candidate is `v0.1.100.1`, and `v0.1.101` remains the next planned normal slice after acceptance.


## v0.1.100.2 migration note

No user data, Project Source state, artifact-current state, deployment, Kubernetes state, or ChatGPT Projects are migrated. This repair converts the same-profile source-remove scheduler test from unbounded status polling to bounded explicit fixture synchronization. Existing rolling-horizon authority is preserved: active normal slice remains `v0.1.100`, the repair candidate is `v0.1.100.2`, and `v0.1.101` remains the next planned normal slice after acceptance.

## v0.1.100.3 migration note

No user data, Project Source state, artifact-current state, deployment, Kubernetes state, or ChatGPT Projects are migrated. This repair removes generated `debug_artifacts/` from the release payload and aligns Artifact Guardian with release-control protected ZIP entry policy. Existing rolling-horizon authority is preserved: active normal slice remains `v0.1.100`, the repair candidate is `v0.1.100.3`, and `v0.1.101` remains the next planned normal slice after acceptance.



## v0.1.101 migration note

No user data, Project Source state, artifact-current state, deployment, Kubernetes state, or ChatGPT Projects are migrated. This slice adds an evidence-only read-only command diagnosis schema and CLI flag. Existing `v0.1.100` command execution evidence is preserved as the source payload; `v0.1.101` only classifies it as `passed`, `blocked`, or `failed`. Correction planning and file mutation remain deferred to later slices.

The next planned normal slice after `v0.1.101` acceptance is `v0.1.102` — Correction-plan generation without file mutation.

## v0.1.102 migration note

No user data, Project Source state, artifact-current state, deployment, Kubernetes state, or ChatGPT Projects are migrated. This slice adds a proposal-only correction-plan schema and CLI flag that consume read-only command diagnosis evidence. Generated correction plans are evidence only; they contain no file changes, write actions, immediate command retries, patch/diff artifacts, Project Source mutation, artifact adoption, deployment, or ChatGPT Project deletion.

The next planned normal slice after `v0.1.102` acceptance is `v0.1.103` — First controlled file mutation in sandboxed fixture only.


## v0.1.103 migration note

No user data, Project Source state, artifact-current state, deployment, Kubernetes state, or ChatGPT Projects are migrated. This slice adds a sandbox-only mutation schema and CLI flag that copy an explicit fixture into a temporary workspace, mutate the copy, and record before/after evidence while keeping the repository fixture unchanged.

The next planned normal slice after `v0.1.103` acceptance is `v0.1.104` — Sandbox mutation verification and rollback evidence gate.

## v0.1.104 migration note

No user data, Project Source state, artifact-current state, deployment, Kubernetes state, or ChatGPT Projects are migrated. This slice adds a verification and rollback evidence gate over the sandbox-only mutation payload from `v0.1.103`. The gate proves sandbox before/after change, repository before/after immutability, and temporary workspace deletion; it does not promote sandbox changes into repository files.

The next planned normal slice after `v0.1.104` acceptance is `v0.1.105` — Sandbox correction promotion readiness check.

## v0.1.104.1 migration note

No user data, Project Source, artifact-current, or ChatGPT Project migration is performed. This repair only makes the project-remove frozen scheduler fixture bounded and deterministic after the `v0.1.104` release-control timeout. `v0.1.104` sandbox mutation verification behavior is preserved; `v0.1.105` remains deferred until this repair is accepted/current.

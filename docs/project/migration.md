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

The next planned normal slice after `v0.1.102` acceptance is `v0.1.103.1` — Docker browser parity diagnostic envelope.


## v0.1.103.1 migration note

No user data, Project Source state, artifact-current state, deployment, Kubernetes state, or ChatGPT Projects are migrated. This slice adds a sandbox-only mutation schema and CLI flag that copy an explicit fixture into a temporary workspace, mutate the copy, and record before/after evidence while keeping the repository fixture unchanged.

The next planned normal slice after `v0.1.103.1` acceptance is `v0.1.104` — Sandbox mutation verification and rollback evidence gate.

## v0.1.103.1 migration note

No user data migration is required. `.pb_profile_docker/` is treated as local
Docker browser state and is excluded from ZIP artifacts. Operators can run the
Docker browser parity diagnostic script to collect auth-readiness evidence without
Project Source mutation.

## v0.1.103.2 migration note

`v0.1.103.2` migrates the Docker browser parity diagnostic from an active login-check flow to a passive auth-readiness flow. It preserves the Promptbranch-native Docker browser envelope and adds host-Chrome profile bootstrap instructions for `.pb_profile_docker` mounted as `/app/profile`.

## v0.1.103.3 migration note

`v0.1.103.3` migrates the passive auth-readiness implementation into the Promptbranch runtime browser client. This repairs the split-client wiring mismatch introduced by the diagnostic continuation without changing endpoint names or widening mutation scope.


## v0.1.103.5 migration note

`v0.1.103.5` migrates the Docker parity investigation from passive authenticated reuse toward guarded Project Source mutation testing. The migration remains diagnostic-only: Project Source mutation requires explicit operator opt-in and does not imply artifact adoption/current status.

## v0.1.103.6 migration note

`v0.1.103.6` changes only diagnostic artifact export behavior. Existing browser profiles, Project Source state, accepted/current artifact state, and release adoption behavior are not migrated. The safe exporter writes to an external `/tmp` target by default and never packages debug artifacts into release ZIPs.
## v0.1.103.8 migration note

`v0.1.103.8` changes only Docker parity diagnostics. It adds a Cloudflare challenge settle-loop script and leaves browser profiles, Project Source mutation behavior, artifact adoption behavior, and release-control semantics unchanged.



## v0.1.103.9 migration note

`v0.1.103.9` requires no state migration. Operators should stop using stale `.pb_profile_docker` for Cloudflare diagnosis and instead create a clean timestamped Bonnetjes profile with `scripts/docker-bonnetjes-clean-login-profile-bootstrap.sh`. Browser profiles must remain bind mounts and are excluded from Docker build context by `.dockerignore`.

## v0.1.103.10.4 migration

No state migration. Operators may use `scripts/docker-bonnetjes-cloudflare-validation.sh` to create a fresh timestamped profile and validate the Docker Bonnetjes Cloudflare path. Browser profiles remain local bind-mounted state and must not be committed or packaged.

## v0.1.103.10.6 migration

No state migration is required. If `.pb_profile/browser/default` is an empty non-writable Docker-created placeholder, the bootstrap can recreate it as the host user. If it contains existing browser state and is not writable, operators must repair ownership explicitly, for example:

```bash
sudo chown -R $(id -u):$(id -g) .pb_profile/browser/default
```

Browser profiles remain local bind-mounted state and must not be committed or packaged.

## v0.1.103.10.8 migration

No data migration. Replace the rejected `v0.1.103.10.6` candidate ZIP with `chatgpt_claudecode_workflow-2_v0.1.103.10.8.zip` and rerun auth-only release control. The repair is packaging-only for generated-cache hygiene.

## v0.1.103.10.8 migration

No data migration. Install the candidate ZIP over `v0.1.103.10.7` and rerun auth-only validation. Existing `.pb_profile/browser/default` data is reused; do not enable Project Source mutation for this repair.

## v0.1.103.10.9 migration

No data migration. Operators should stop any hanging `pb ask`, restart the Docker service if necessary, rerun auth-readiness to create a clean held session, then retry the `pb ask` smoke after installing this candidate. Project Source mutation remains disabled by default.

## v0.1.103.10.10 migration

No data migration. Install the candidate ZIP, rerun auth-only validation, then rerun the `pb ask` smoke. If an old held browser session is still challenged, stop the service and rerun standard browser auth-readiness before retrying.

## v0.1.103.10.11 migration

No data migration is required. Operators may reuse `.pb_profile/browser/default`, but when Docker auth-readiness reports `Just a moment...`, run the Docker visual bootstrap so Chrome inside the Promptbranch image writes the profile state through the `/app/profile` bind mount.


## v0.1.103.10.12 repair mapping

`v0.1.103.10.12` maps the observed generic-ChatGPT false-green from Docker held-session ask into the standard browser repair line. It preserves Project Source mutation disabled and records that project-scoped ask must target the state conversation/project URL.


## v0.1.103.10.13 repair mapping

`v0.1.103.10.13` maps the operator request to make `pbsa` possible into a guarded per-request Project Source mutation intent. It does not make arbitrary service calls mutable: direct API calls without intent remain gate-closed.

## v0.1.103.10.15 repair mapping

`v0.1.103.10.15` maps the live HTTP 500 from `pbsa` into the standard browser repair line. The failure was caused by preflight launching a second persistent context while a held project-scoped auth session already owned `/app/profile`. The repair reuses compatible held sessions and keeps Project Source mutation gated by explicit operator intent.


## v0.1.103.10.17 repair mapping

The repair maps the live auth-only adoption failure from `v0.1.103.10.15` into a URL-role split: visible Docker bootstrap uses a stable generic URL by default, while Docker auth-readiness still validates the current Promptbranch project/conversation target.


## v0.1.103.10.19 migration note

After installing this candidate, use `pb test api` for repeated API coverage checks instead of copy/pasting individual curl commands. Existing `pb test browser/full` flows are unchanged.

## v0.1.103.10.19 migration note

After installing this version, rerun `pb test api --json`. No manual copy of `scripts/pb-api-coverage-test.py` into site-packages is required.

## v0.1.103.10.21 migration note

No user migration required. Re-run `pb test api --json`; use `--hold-auth-session` only when explicitly testing held-session behavior.

## v0.1.103.10.22 migration note

Docker Chrome runtime paths now use explicit shared-memory sizing. Override with `PROMPTBRANCH_DOCKER_SHM_SIZE` if the default is unsuitable.


## v0.1.103.10.42 migration note

No operator migration required. `pb test api` now checks response-body success semantics in addition to HTTP status codes.
## Migration note — v0.1.103.10.42 full/browser validation skips generic-root login check

`v0.1.103.10.42` disables the forced `login_check` step in browser/full validation by default. The suite now relies on the same auto-login/session path used by real browser operations, avoiding generic `https://chatgpt.com/` root navigation that can trigger a challenge. The login check endpoint and explicit diagnostic step remain available via `--only login` or `PROMPTBRANCH_TEST_ENABLE_LOGIN_CHECK=1`. No browser/session architecture or Project Source mutation behavior changes.



## Migration note — v0.1.103.10.42 release-control clears auth bootstrap held session explicitly

Release-control now performs an auth bootstrap before live Project Source or test operations. Operators should continue using `--run-all-tests --adopt-after-validation` for full adoption; `--auth-only-validation` remains available for bootstrap-only checks.

## Migration note — v0.1.103.10.42

No data migration. Operators may continue without `.pb_profile_local_debug`; release-control will skip dependent live-only steps as non-blocking when the seed profile is absent. To run live-only tests explicitly, create and authenticate `.pb_profile_local_debug` before the release run.

## v0.1.103.10.42 migration

No repository data migration. Operators must bootstrap live browser profiles explicitly before full adoption:

```bash
./scripts/pb-docker-live-profile-bootstrap.sh --fresh --url <Promptbranch conversation URL>
```

The accepted standard profile `.pb_profile/browser/default` is not copied into live seed or pool profiles.

## v0.1.103.10.42 migration

No data migration is required. Existing `.pb_profile_local_debug_pools/` state is now preserved by release ZIP import. If the directory was already deleted by a previous import, rerun the explicit Docker live profile bootstrap before `--run-all-tests`.

## v0.1.103.10.42 migration

No data migration. Existing explicitly bootstrapped Docker live profiles remain local state. Rerun `--run-all-tests`; release-control will create/open a conversation inside the retained live Project before live ask steps.


## v0.1.103.10.43 migration

No operator state migration is required. Existing manually bootstrapped `.pb_profile_local_debug` and `.pb_profile_local_debug_pools/release-live/slots/slot-1` profiles remain the live validation authority. The behavioral change is that release-control live steps set fail-fast challenge mode, so Cloudflare/Just-a-moment pages now return `docker_live_profile_challenged` immediately instead of waiting for manual login.

## Migration note — v0.1.103.10.45

`v0.1.103.10.45 — repair package version surface for Docker build context coherence` keeps the Docker-only live validation architecture. Challenge detection in release-live mode now logs with `challenge_stage` instead of a duplicate `_log(stage=...)` keyword, returns structured `docker_live_profile_challenged`, and prevents later live browser steps from opening once `ask_live` has already proven the live slot is challenged.


## Migration note — v0.1.103.10.48

`v0.1.103.10.48 — classify backend-api 403 guardrail as terminal browser challenge across release validation paths` keeps the all-in-Docker live validation path and makes a challenged release-live slot terminal across both the internal `ask-live` matrix and release-control. The repair uses fixed-string/JSON-aware challenge detection and records later live browser steps as skipped-blocked instead of opening new Chrome contexts. No host-CDP/session-manager or copied-profile trust is reintroduced.


## Active repair slice — v0.1.103.10.48

`v0.1.103.10.48 — classify backend-api 403 guardrail as terminal browser challenge across release validation paths` preserves the Docker-only live-validation line and extends fail-fast challenge classification beyond ask-live. Observed ChatGPT `/backend-api/...` 403 responses are diagnostic guardrail evidence only, not an operational API contract. Release-control now enables fail-fast challenge handling for full/direct, localhost/service, live preflight, project selection, and live ask paths; after a full-validation backend guardrail, remaining live browser phases are skipped and import/artifact guards still run.

## Active repair slice — v0.1.103.10.53

`v0.1.103.10.53 — release-live bootstrap 429/guardrail is terminal before ask_live` preserves the Docker-only challenge classification chain through `v0.1.103.10.48`, then fixes the remaining human-likeness topology bug: release-live setup and execution now use `.pb_profile_local_debug_pools/release-live/slots/slot-1` as the single actor profile for project ensure, project selection, conversation bootstrap, ask-live, visual artifact roundtrip, and release-live. `.pb_profile_local_debug` remains optional/reference state and is no longer used to create the live conversation that the slot later opens. The Docker bootstrap default image also derives from `VERSION`/`PROMPTBRANCH_VERSION` instead of depending on an unset `PROMPTBRANCH_SERVICE_IMAGE_TAG` local fallback.


## Active repair slice — v0.1.103.10.53

`v0.1.103.10.53 — release-live bootstrap 429/guardrail is terminal before ask_live` preserves the Docker-only live-profile repair chain through `v0.1.103.10.49`, then makes backend-api 403 guardrail telemetry during auth bootstrap terminal. Release-control now refuses to treat a visually logged-in/composer-visible browser as clean when the standard Docker profile is already forbidden by backend-api guardrail responses; it restarts the candidate service to clear the held browser owner and stops before Project Source add/full validation.


## Active repair slice — v0.1.103.10.55

`v0.1.103.10.55 — release-live bootstrap and ask use one continuous browser session` adds a fast replay harness for release-control run-all orchestration, including terminal live bootstrap 429/guardrail behavior before ask_live. It preserves all-in-Docker, no host-CDP/session-manager, no copied-profile trust, and no private backend-api operational dependency.


## v0.1.103.10.56 — wire release-live-continuous into real CLI test dispatch

Repair candidate `chatgpt_claudecode_workflow-2_v0.1.103.10.56.zip` wires `release-live-continuous` into the real CLI test dispatcher while preserving the continuous release-live session design.

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

## v0.1.103.10.65 migration

No data migration. Operators can continue using the same release-live slot profile and trusted project conversation URL. Existing commands with `--warmup-conversation-url https://chatgpt.com/g/.../c/...` now use that conversation directly instead of root project discovery.


## v0.1.103.10.65 migration

No state migration is required. Browser profile format, registry format, Project Source policy, artifact adoption policy, and release-control product/external-live split remain unchanged.


## v0.1.103.10.66 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.66.zip`.

Active candidate version: `v0.1.103.10.66`.

Active repair slice: `v0.1.103.10.66 — release-live-continuous handles page/context close during composer submit as explicit browser-lifetime failure`.

This remains repair-only and does not advance the normal horizon. It keeps trusted conversation direct mode and adds structured `browser_context_closed_during_submit` evidence for live browser page/context close during composer submit.

## v0.1.103.10.67 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.67.zip`.

Active candidate version: `v0.1.103.10.67`.

Active repair slice: `v0.1.103.10.67 — composer wait target-close is classified as browser_context_closed_during_submit`.

Migration impact: no data or profile migration. Runtime behavior only changes classification of browser target closure during composer selector waiting.


## v0.1.103.10.68 repair note

Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.68.zip`.

Active repair slice: `v0.1.103.10.68 — release-live-continuous marks completed bootstrap/ask sentinel run as ok`.

Migration impact: no data, browser profile, Project Source, artifact registry, or Docker profile migration. Runtime behavior only changes final aggregation for completed bootstrap/ask sentinel runs.

## v0.1.103.10.69 repair note

Active repair slice: `v0.1.103.10.69 — add install.sh strict all-all release gate`.

`install.sh` is a new root-level helper script. It does not migrate existing state or registry files; it wraps the already-supported release-control flags for strict all-all validation and adoption. Operators may pass a version and optional ZIP path.


## v0.1.103.10.70 repair note

Active repair slice: `v0.1.103.10.70 — classify release-live-continuous bootstrap guardrail as external live blocked`.

Decision: keep the `v0.1.103.10.69` strict all-all install gate unchanged, but classify `live_bootstrap_guardrail` and `skipped_blocked_by_live_bootstrap_guardrail` as external-live blockage evidence so all-all adoption remains blocked with `LIVE_BLOCKED`, not product `FIX`.

No Cloudflare/rate-limit bypass, host-CDP/session-manager, or copied-profile trust is introduced.


## v0.1.103.10.72 repair decision

`v0.1.103.10.72` keeps repair scope only: the project control surface must identify `chatgpt_claudecode_workflow-2_v0.1.103.10.72.zip` as the active candidate, and all-all release aggregation must prefer product `FIX` over external `LIVE_BLOCKED` whenever product validation has failed. `LIVE_BLOCKED` is reserved for clean product validation with external ChatGPT live blockage. The planned normal horizon after repair acceptance remains `v0.1.104`.


## v0.1.103.10.73 repair decision

`v0.1.103.10.73` is a product-test repair only. It migrates the version-surface test from a stale hardcoded candidate literal to release-metadata-derived expectations, and adds a guard against stale repair-version literals in that test file. No Cloudflare/rate-limit behavior, host-CDP/session-manager behavior, copied-profile trust, or adoption logic is changed.

## v0.1.103.10.76 repair decision

`v0.1.103.10.76` migrates the live bootstrap guardrail handling from immediate terminal blockage to one bounded cooldown/re-readiness retry, while preserving terminal `LIVE_BLOCKED` classification when the guardrail persists. This is a release-live safety improvement only and does not alter adoption semantics.

## v0.1.103.10.76 repair decision

`v0.1.103.10.76` migrates release-live sentinel validation from raw full-string equality to bounded visible-thinking normalization. The change is limited to release-live sentinel checks and does not alter Cloudflare/rate-limit handling or adoption semantics.

## v0.1.103.10.78 repair decision

`v0.1.103.10.78` migrates overwrite-file persistence verification from exact-only refreshed surface matching to exact-or-duplicate-suffix matching when a save commit is observed and the operation is already in the overwrite path.


## v0.1.103.10.79 repair migration

`v0.1.103.10.79` migrates file-source preflight from a single immediate DOM snapshot to an authoritative-state contract: explicit empty state or stable non-empty snapshots. It also moves backend-suffix detection and uniquely identifiable rollback ahead of the exact-name persistence retry loop, so the CLI receives the final classification instead of timing out while the service continues recovery.

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

Canonical artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.82.zip`.

No command migration is required. `pbsa <file>` remains `promptbranch src add <file>`. The implementation now reconciles exact attributable Library backing files before a same-name re-upload and returns `library_collision_ambiguous` or `library_collision_not_cleared` instead of mutating when safe ownership cannot be proven.

## v0.1.103.10.83 repair note

Canonical artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.83.zip`.

No command migration is required. `pbsa <file>` remains `promptbranch src add <file>`. Library empty/search results now require stable authoritative observations on the actual Library route; Recently deleted must be opened and authoritative. Upload responses retain bounded diagnostics and extract exact backing file IDs from JSON, NDJSON/SSE, headers, and redirect URLs. Missing suffix backing identity fails closed as `library_backing_file_identity_missing`.

## v0.1.103.10.84 repair note

Canonical artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.84.zip`. The repair retains the existing `pbsa <file> -> promptbranch src add <file>` command contract while changing only the internal file-source transaction classifier: fresh add, exact-source replacement, or proven suffix collision.


## v0.1.103.10.86 migration note

No command migration is required. Run `./scripts/pb-project-source-ab-diagnostic.sh`; normal `pbsa <file>` remains unchanged. The next planned release after acceptance remains v0.1.104.

## v0.1.103.10.87 migration note

No command migration is required. `./scripts/pb-project-source-ab-diagnostic.sh` now reads the normal Promptbranch service configuration automatically. Explicit `--service-token` and `--service-base-url` overrides remain supported.

## v0.1.103.10.89 migration note

No normal `pbsa` or release command migration is required. The exact backing-object diagnostic is invoked with `./install.sh <version> <zip> --diagnostic-library-backing-reupload` or, after installation, `./scripts/pb-library-backing-reupload-diagnostic.sh`. Its result classification is limited to `canonical_reupload_after_backing_delete`, `backing_library_delete_not_supported`, `backing_library_delete_failed`, `backend_suffix_after_verified_backing_delete`, or `diagnostic_inconclusive`.


## v0.1.103.10.90 migration note

Canonical artifact: `chatgpt_claudecode_workflow-2_v0.1.103.10.90.zip`. No CLI migration is required and `pbsa <file>` remains `promptbranch src add <file>`. The new diagnostic-only install mode is `--diagnostic-library-backend-protocol-reupload`. It installs the candidate without commit, Project Source release upload, tests, or adoption, then runs a new disposable project/file transaction. The existing `(1)` evidence project and source are not touched.


## v0.1.103.10.91 migration note

No CLI migration is required. `pbsa <file>` remains unchanged. The diagnostic install mode remains `--diagnostic-library-backend-protocol-reupload`; its result now includes `visible_library_backend_presence`, a complete non-truncated sanitized fetch/XHR trace, and corrected identity/visibility failure reasons.


## v0.1.103.10.92 migration note

No user-facing command or state migration is introduced. The `10.91` diagnostic protocol representation is split internally into private executable headers and a sanitized public report. `pbsa` remains unchanged; accepted/current remains `v0.1.103.10.68`.


## v0.1.103.10.93 migration note

No workflow or command surface is migrated. `pbsa <file>` remains unchanged. The diagnostic Library UI parser now treats rendered line wrapping as presentation data and binds destructive selection only after exact filename reconstruction plus unique backend identity proof. Existing accepted/current state remains `v0.1.103.10.68`.


- `v0.1.103.10.94` adds actionable-row and row-scoped menu evidence to the diagnostic repair ledger; accepted/current remains `v0.1.103.10.68`.


- `v0.1.103.10.95` adds filename-leaf row discovery, hover-triggered row-menu evidence, backend `libfile_...` deduplication, and bounded non-authoritative-surface evidence to the diagnostic repair ledger. Accepted/current remains `v0.1.103.10.68`; no release source or adoption mutation is performed.
- `v0.1.103.10.96` adds exact soft-delete mutation proof, stable active-inventory absence/trashed verification, explicit Recently deleted navigation states, and exact deleted-inventory presence gating. Accepted/current remains `v0.1.103.10.68`; no release source or adoption mutation is performed.


- `v0.1.103.10.97` separates long-lived `/backend-api/files/process_upload_stream` completion from ordinary Project Source save quietness, requires exact terminal `file_...`/`libfile_...`/filename identity, and emits explicit top-level diagnostic reasons. Accepted/current remains `v0.1.103.10.68`; no release source upload or adoption is performed.

- `v0.1.103.10.98` orders Project Source file proof as ordinary save quietness, terminal processing identity, rendered persistence verification, then watcher disposal. No CLI migration is introduced. Accepted/current remains `v0.1.103.10.68`; no release source upload or adoption is performed.

- `v0.1.103.10.99` patches only the diagnostic-only legacy Project Source upload transaction used by the backend-protocol discovery run. Normal `pbsa` selection and behavior remain unchanged. Accepted/current remains `v0.1.103.10.68`; no release source upload or adoption is performed.

## Repair migration note — v0.1.103.10.100

- `v0.1.103.10.100` changes only diagnostic response-capture settlement and reporting. It preserves the `v0.1.103.10.100` predecessor's Project Source terminal-processing path, the `v0.1.103.10.96` deletion flow, normal `pbsa`, and accepted/current `v0.1.103.10.68`.

## Repair migration note — v0.1.103.10.101

- `v0.1.103.10.101` changes only diagnostic visible-Library upload identity capture. Generic Fetch/XHR tracing remains stream-safe, the v0.1.103.10.99 Project Source terminal-processing path and v0.1.103.10.96 deletion flow remain unchanged, normal `pbsa` remains unchanged, and accepted/current remains `v0.1.103.10.68`.


## Repair migration note — v0.1.103.10.102

- No operator migration is required.
- The diagnostic trace gains immutable `request_phase`, `response_observed_phase`, request sequence boundaries, sanitized soft-delete mutation candidates, and deduplicated settlement history.
- Existing `v0.1.103.10.99` Project Source stream handling, `v0.1.103.10.100` generic trace settlement, `v0.1.103.10.101` visible-Library stream handling, and `v0.1.103.10.96` deletion/reupload gates remain unchanged.
- Accepted/current remains `v0.1.103.10.68`; normal `pbsa`, canonical release upload, and adoption remain blocked.


## Repair migration note — v0.1.103.10.103

The diagnostic Library delete helper now waits for asynchronous confirmation surfaces and no longer treats an absent immediate dialog as success. Existing request-sequence protocol discovery remains the authority for direct no-confirmation flows. No accepted/current state, Project Source, or release-adoption behavior changes.

## Repair migration note — v0.1.103.10.104

This candidate adds one diagnostic-only bounded Library UI recovery cycle after exact backend inventory presence is stable. It first clears and reapplies the exact filename search, then may perform one controlled reload and reapply the search. It does not change Project Source processing, visible-Library processing, deletion confirmation, backend protocol discovery, Recently deleted, hard-delete, canonical reupload, `pbsa`, or adoption behavior.

## Clean-break state note — v0.1.103.10.105

There is intentionally no backward-compatible registry migration. Start with a new Promptbranch project dataset, join every repository explicitly with `pb project join`, and allow that command to initialize the project-scoped `promptbranch_artifacts.json`. Remove or archive obsolete repository-local `.pb_profile/promptbranch_artifacts.json` files before artifact operations. Old registry records, noncanonical artifact names, missing explicit `repo_id`, invalid JSON, unreadable state, and unresolved project membership fail closed. No current/adopted state is inferred or reconciled automatically.

## Indexed Project Source identity note — v0.1.103.10.106

No migration or rename is performed. Canonical local ZIP names remain canonical. A uniquely correlated backend-assigned `(n)` display name is retained as Project Source metadata and may be referenced during adoption; ambiguous indexed families remain blocked.


## Exact assigned Project Source verification note — v0.1.103.10.107

No command or state migration is required. Existing indexed Project Sources remain valid family members. For a normal new `pb src add`, the highest existing suffix is diagnostic pre-upload evidence only; Promptbranch uploads once and verifies the exact filename assigned by the processing stream. It does not reuse the previous indexed source and does not wait for the canonical unsuffixed filename after an assigned name is known.


## Project Source capacity note — v0.1.103.10.109

No state migration is required. A future successful default `pb src add` removes older canonical/indexed Project Source siblings after the new assigned source is verified. `--no-overwrite` refuses an existing indexed family rather than creating another sibling.


## Test validation registry note — v0.1.103.10.110

An absent project artifact registry is now a valid read-only planning observation. Operators must not create a repo-local compatibility registry to satisfy tests. Mutating artifact commands still require the authoritative project-scoped registry to exist and validate.

## Full-suite alignment note — v0.1.103.10.111

No state migration is required. Existing project-scoped registries remain authoritative. Test fixtures and operator-created datasets that perform artifact mutation must initialize the project registry explicitly. Read-only commands may report unresolved project scope or a missing registry without creating state. Existing file sources are never removed before the newly uploaded assigned family member is verified when Replace is unavailable.


## Changed-content indexed-family overwrite migration — v0.1.103.10.112

`v0.1.103.10.111` remains not adopted after both full transports proved that an unchanged second file could be suppressed by ChatGPT and then misclassified as overwrite success by rediscovering the old singleton. `v0.1.103.10.112` changes the release fixture bytes, records both hashes, treats the processing-stream assigned canonical/indexed name as authoritative, and requires both backing identities before any old-source deletion. Existing canonical/indexed family matching remains compatible; no artifact-registry migration or legacy fallback is introduced.

## Collision-free indexed replacement staging — v0.1.103.10.113

`v0.1.103.10.112` remains not adopted after both full transports proved that changed bytes selected under the same local basename can still produce no browser upload transaction. `v0.1.103.10.113` introduces no state migration and no filename rename of the canonical artifact. During upload-new replacement only, Promptbranch creates a temporary numeric canonical-family member, selects that staged file once, and removes the temporary local copy after browser selection. The staging token is never backend-index authority. Existing processing-stream assignment, backing-identity, pre-upload deletion-scope, and final-singleton gates remain unchanged and fail closed.

## Continuous live-profile and submit-causality repair — v0.1.103.10.114

No state migration is introduced. Existing pool roots remain valid inputs to `--profile-lease`, while already-resolved `.../slots/slot-N` paths are treated as exact profiles and are never nested into another pool. Release validation passes one exact slot to both external-live commands without `--profile-lease`. Submit evidence accepts the current ChatGPT flow and a valid new post-submit reply envelope; Cloudflare classification remains fail-closed to explicit challenge evidence. Localhost full validation is executed independently. Accepted/current remains `v0.1.103.10.68` until strict release validation and adoption succeed.


## Adoption identity and response-completion repair — v0.1.103.10.115

`v0.1.103.10.115` supersedes the unadopted `v0.1.103.10.114` candidate. It preserves the live-proven indexed overwrite, continuous profile, current submit-flow, independent localhost, and visual-artifact repairs. It adds a pre-validation `pb project join` transaction derived from the exact Project Source upload result, transports the assigned filename plus processed-file and Library metadata IDs into adoption, records those identities in the artifact registry, accepts causally proven same-count virtualized assistant responses after bounded stable idle completion, and removes raw-text `429` retry detection. No accepted/current baseline is advanced by the candidate build.

## Assigned-source-aware post-adoption verification — v0.1.103.10.116

`v0.1.103.10.116` uses accepted/current `v0.1.103.10.115` as its baseline. It replaces only the final verifier that previously compared all refs to the canonical ZIP. The new verifier accepts the authoritative split between canonical artifact identity and indexed assigned-source identity, verifies the stored processed-file and Library metadata IDs, and emits a structured `release_adopted_and_verified` result after complete alignment. No registry migration, Project Source mutation, profile migration, or response-completion change is introduced.

## v0.1.104 normal-roadmap resumption

Accepted/current `v0.1.103.10.116` closes the repair line. The project control surface now resumes normal MVP-1 development with `v0.1.104 — Sandbox mutation verification and rollback evidence gate` and records the complete roadmap in `docs/project/promptbranch-plan-v0.1.104.md`.

The previous `v0.1.103` copied-fixture mutation contract is advanced, not broadened: the mutation remains temporary and sandbox-only, but now requires exact result verification, sandbox validation, read-only validation proof, exact rollback proof, unchanged repository evidence, workspace deletion, and a terminal stop. `v0.1.105` remains the next planned slice.

## v0.1.104.1

No state-format migration is required. Import from accepted/current `v0.1.103.10.116` or the unadopted `v0.1.104` candidate preserves local project/repository registries and browser profiles. Existing `v0.1.104` validation evidence is not reusable because `v0.1.104.1` requires fresh direct execution and a different signed release-validation manifest.


## v0.1.104.2

No state-format migration is required. Import preserves browser profiles and project/repository/artifact registries. `v0.1.104.1` remains unadopted and repair-required; accepted/current remains `v0.1.103.10.116`. Fresh direct and independent localhost evidence remain required.


## v0.1.104.4

The continuous release-live readiness model now scopes interruption evidence to the latest/current turn, separates pre-bootstrap readiness from post-bootstrap recovery, and adds bounded post-reload hydration. The sandbox gate and ten-step release manifest are unchanged.

## v0.1.104.5

No data migration. This repair changes only the environment of offline release-validation subprocesses. Existing repository `.pb_profile`, user configuration, project registries, browser profiles, Project Sources, artifacts, and accepted/current state are preserved and are intentionally unreachable from hermetic pytest nodes.

## v0.1.105

No data or registry migration is required. `v0.1.104.5` is the accepted/current authority. The new `pb loop promotion-readiness` command creates only temporary sandbox workspaces through the existing sandbox contract, emits an in-memory/stdout assessment, and does not persist a promotion decision or grant broader mutation authority. `v0.1.106` remains the earliest slice permitted to record an explicit GO/NO-GO decision.


## v0.1.105.1

No migration is required. The repair changes only runtime repository-root resolution for promotion-readiness. Existing readiness evidence, sandbox contracts, and authority restrictions remain unchanged.


## v0.1.106 decision-record migration note

No data or registry migration is required. `v0.1.105.1` is accepted/current. `v0.1.106` adds a deterministic stdout decision command and the machine-readable project record `docs/project/correction-promotion-decision-v0.1.106.json`. The GO decision permits only `v0.1.107 — Controlled correction execution envelope design`; it enables no correction execution or broader mutation authority.

## v0.1.107

No data or registry migration is required. `v0.1.106` is accepted/current. `v0.1.107` adds a deterministic design-only execution-envelope command and project record. It does not create a workspace, execute a correction, or grant repository mutation authority.

The next planned slice is `v0.1.108 — Controlled correction execution envelope validation gate`; it remains validation-only and grants no correction execution authority.

## v0.1.108

No artifact-registry or runtime-state migration is required. `v0.1.107` is accepted/current. `v0.1.108` advances the repository control surface, adds a validation-only CLI and machine-readable validation record, and preserves all correction-execution and mutation authority flags as false.

The historical conversational use of `v0.1.108` for `PROJECT_SETTINGS.md` work is explicitly superseded by the adopted repository control surface. That work is moved to `v0.1.109 — PROJECT_SETTINGS.md, AGENTS.md and project authority-graph definition`.

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

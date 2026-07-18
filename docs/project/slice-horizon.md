# Slice Horizon

## Active repair slice

`v0.1.104.3 — current-turn-scoped interrupted-state readiness`

The repair preserves the proven sandbox and transport gates, ignores historical Retry controls, separates pre-bootstrap readiness from post-bootstrap recovery, and retains exactly one same-page reload of the same trusted conversation only when latest-turn `interrupted_answer_state` is the sole post-bootstrap blocker. After reload it waits boundedly for conversation hydration, then reverifies the exact bootstrap sentinel and authoritative idle composer state before ask submission.

## Recent repair context

- `v0.1.104.1` proved fresh direct, independent localhost, and all 13 sandbox gates, but external-live reproduced post-bootstrap `target_conversation_busy`; adoption was refused.
- `v0.1.104.2` preserved those gates and added one reload, but a historical Retry control was misclassified as active interruption before bootstrap; adoption was refused.

## Accepted repair baseline

`v0.1.103.10.116` is accepted/current after 9/9 validation, evidence-bound adoption, and assigned-source-aware final verification.

## Recent repair context

- v0.1.103.10.67 — composer wait target-close is classified as browser_context_closed_during_submit
- v0.1.103.10.68 — release-live-continuous marks completed bootstrap/ask sentinel run as ok
- v0.1.103.10.69 — add install.sh strict all-all release gate

- v0.1.103.10.70 — classify release-live-continuous bootstrap guardrail as external live blocked
- v0.1.103.10.71 — final verdict aggregation maps live_bootstrap_guardrail cascade to LIVE_BLOCKED
- v0.1.103.10.72 — update project control surface active candidate and preserve LIVE_BLOCKED only when product validation is clean

- v0.1.103.10.78 — make pb src add exact-name idempotent and block suffix-renamed Project Source uploads
- v0.1.103.10.79 — require stable Project Sources preflight and fail fast on backend-assigned suffix names
- v0.1.103.10.82 — reconcile exact Library backing-file IDs for same-name Project Source overwrite
- v0.1.103.10.84 — restore normal fresh add, attempt non-destructive exact-source replacement, and reserve Library cleanup for proven suffix collisions

## Rolling normal horizon

- v0.1.104 — Sandbox mutation verification and rollback evidence gate
- v0.1.105 — Sandbox correction promotion readiness check
- v0.1.106 — Controlled correction promotion decision record
- v0.1.107 — Controlled correction execution envelope design

## Repair horizon rule

Repair releases must not advance the normal horizon.

## v0.1.103.10.87

Active diagnostic repair: compare the legacy 10.75 and current Project Source transactions side by side. Repair horizon rule remains unchanged; v0.1.104 follows only after acceptance.

## v0.1.103.10.89

Diagnostic-only repair: delete the exact captured backing Library object after verified Project Source removal, prove exact-ID absence from active Library and Recently deleted, then attempt unchanged 10.75 canonical reupload. The prior `(1)` Project Source remains untouched; no release artifact upload, adoption, production Project Source, or `platform-gitops` artifact is involved.


## v0.1.103.10.90

Diagnostic-only repair: capture the complete redacted fetch/XHR contract for a disposable Project Source and a separately uploaded disposable Library file; discover the exact backend inventory, soft-delete, and permanent-delete operations; bind replay strictly to captured `libfile_...` / `file_...` identities; verify exact absence through the same backend inventory; only then attempt unchanged canonical reupload. Existing `(1)` evidence remains untouched.


## v0.1.103.10.91

Repair-only continuation of `v0.1.103.10.90`. Accept the observed `/backend-api/files/library/nodes` GET surface as active inventory discovery, preserve both `file_...` and `libfile_...` identities from node responses, poll exact `libfile_...` visibility with stable observations, and treat delayed UI visibility as a separate fail-closed gate. Export every fetch/XHR event while retaining body samples only for sanitized `/backend-api/files...` protocol traffic. No release upload or adoption.


## v0.1.103.10.92

v0.1.103.10.92 — replay Library protocols with private in-memory authentication

Narrow diagnostic repair: retain executable authentication headers only in memory, replay the exact `/backend-api/files/library/nodes` protocol with those private headers, count the captured exact-ID `200` as observation one, require one additional authenticated exact-`libfile_...` observation, fail immediately on `401`/`403`, and keep deletion/reupload/upload/adoption gates closed until inventory proof succeeds.


## v0.1.103.10.93

v0.1.103.10.93 — reconstruct exact Library filenames and bind one backend-proven UI card

Narrow diagnostic repair: preserve authenticated exact-ID backend inventory proof, reconstruct the exact canonical filename from stable DOM attributes or contiguous rendered fragments, reject partial and numeric-suffix matches, require one exact UI record and one unique backend `libfile_...`, mark exactly one UI card for selection, and keep all delete/reupload/release-upload/adoption gates closed when binding is not authoritative.


### v0.1.103.10.94 repair-only diagnostic

Bind the exact Library filename only inside one actionable file row and scope the mutation menu to that row. This repair does not advance the normal horizon.


### v0.1.103.10.95 repair-only diagnostic

Separate exact filename-leaf row discovery from hover-activated row-menu binding, deduplicate backend observations by `libfile_...`, and stop on a bounded non-authoritative Library surface before any delete or reupload mutation. Accepted/current remains `v0.1.103.10.68`.

### v0.1.103.10.96 repair-only diagnostic

- Prove one successful exact-ID soft-delete mutation immediately after the bound-row Delete action.
- Require two authenticated observations showing the disposable object absent from active inventory or explicitly trashed.
- Prove Recently deleted navigation, inventory endpoint discovery, and exact deleted-object presence before permanent deletion.
- Keep target deletion, canonical reupload, release `pbsa`, and adoption blocked.


### v0.1.103.10.97 repair-only diagnostic

Handle `/backend-api/files/process_upload_stream` as a separate bounded processing phase after ordinary save quietness. Require terminal completion with the exact processed-file ID, Library metadata ID, and expected filename before continuing the unchanged soft-delete and Recently deleted diagnostic. Emit explicit failure reasons and preserve all mutation/adoption freezes.

### v0.1.103.10.98 repair-only diagnostic

Await exact terminal `/backend-api/files/process_upload_stream` identity before Project Source persistence verification, retain request listeners until terminal handling and persistence verification complete, and capture the SSE body only after `requestfinished`. Accepted/current remains `v0.1.103.10.68`; release `pbsa` and adoption remain prohibited.


### v0.1.103.10.99 repair-only diagnostic

Patch the diagnostic-only legacy Project Source upload path actually invoked by `library_backend_protocol_reupload_diagnostic`. Enforce terminal processing-stream identity before rendered persistence verification, keep the watcher installed through both boundaries, and fail with `internal_processing_stream_wait_skipped` if a pending stream reaches the caller without a stream result. Accepted/current remains `v0.1.103.10.68`; release `pbsa` and adoption remain prohibited.

### v0.1.103.10.100 repair-only diagnostic

Bound generic Fetch/XHR response-capture settlement, omit streaming bodies, classify and cancel unresolved tasks, preserve completed trace evidence, and guarantee structured timeout JSON. This repair does not advance the normal horizon.

### v0.1.103.10.101 repair-only diagnostic

Install a dedicated bounded processing-stream watcher for the disposable visible-Library upload, require exact terminal backing identity, and keep generic tracing non-authoritative. This repair does not advance the normal horizon.


### v0.1.103.10.102 repair-only diagnostic

Settle pre-delete trace work, freeze the maximum request sequence before the exact row-scoped Delete click, snapshot each request phase immutably, and discover successful exact-ID deletion mutations from paired post-boundary request/response events. Report sanitized mutation candidates when identity is not verified, reconcile the visible upload after later authoritative proof, and suppress unchanged settlement duplicates. This repair does not advance the normal horizon.


### v0.1.103.10.103 repair-only diagnostic

Bound and uniquely bind the asynchronous visible-Library delete confirmation. Promote to `delete_triggered` only with exact post-boundary mutation proof; preserve all downstream discovery gates and do not advance normal scope.

### v0.1.103.10.104 repair-only diagnostic

Recover the active Library UI exactly once after authoritative backend presence: exact-search reapplication, then at most one controlled reload and another exact-search reapplication. Exact row binding remains mandatory and the v0.1.103.10.103 delete-confirmation contract remains unchanged.

### v0.1.103.10.105 repair-only clean break

Remove repo-local artifact-registry fallback and the legacy registry-import path. Require explicit repository identity, configured project membership, canonical repo-root agreement, and an existing valid project-scoped registry for artifact reads and mutations. Missing, invalid, unreadable, unresolved, or ambiguous state fails closed. This is a clean development-state break: no migration, reconciliation, filename-order inference, or automatic adoption is provided.

### v0.1.103.10.106 repair-only correlation

Accepts a backend-assigned numeric-suffix Project Source filename only when it is uniquely correlated to the current canonical upload through processing-stream file/libfile identities and exact assigned-card read-back. Returns requested and assigned filenames separately, reuses one existing correlated indexed source without uploading another copy, blocks ambiguous families, and allows artifact adoption to retain the assigned Project Source name as metadata. Canonical artifact identity and version remain unchanged; the numeric suffix is Project Source metadata only. No release pbsa, adoption, or unrelated Library cleanup is performed.


### v0.1.103.10.107 repair-only exact assigned-name verification

Uses one escaped canonical/indexed filename-family matcher across preflight and verification. The pre-upload family snapshot records the highest existing numeric suffix as evidence only; a normal add uploads exactly once, accepts the processing-stream `assigned_filename`, verifies that exact assigned Project Source card immediately, and never enters canonical-name persistence retries after assigned identity is known. Malformed assigned names and duplicate exact assigned cards remain fail closed.


### v0.1.103.10.109 repair-only deterministic Project Source capacity pruning

Upload and verify the new assigned Project Source first, remove all older exact family members, and return success only when the authoritative final surface contains exactly one family member.


### v0.1.103.10.110 repair-only missing-registry-safe read-only validation

Keep the repair limited to source-sync planning, terminal test-suite JSON, structured pre-suite reporting, and fail-closed mutation authority. No live-browser response-causality or profile-lease repair is included.

### v0.1.103.10.111 repair-only full-suite registry and overwrite alignment

This repair aligns the complete deterministic validation suite with project-scoped registry authority. When ChatGPT exposes no in-place Replace action for an existing file source, Promptbranch uploads once, verifies the exact backend-assigned canonical/indexed family member, and only then removes prior family members. Read-only smoke accepts structured uninitialized project/registry states only when mutation flags remain false. Lifecycle `--plan` stays available while exposing execution blockers. No normal scope advances.


### v0.1.103.10.112 repair-only changed-content indexed-family overwrite proof

- Rewrite the integration file before overwrite and require distinct initial/replacement SHA-256 values.
- Accept the exact backend-assigned canonical or indexed filename; never predict the suffix index.
- Require completed processing plus processed-file and Library object identities before deleting old sources.
- Delete only family identities observed before upload and require the assigned source as the final singleton.
- Fail closed on no upload, missing identity, concurrent family drift, or residual old members.
- Require both `full_direct` and `full_localhost`; do not advance the normal slice.

### v0.1.103.10.113 repair-only collision-free indexed replacement upload

- Preserve changed-content SHA-256 proof from `v0.1.103.10.112`.
- Stage replacement bytes under a collision-free numeric member of the canonical filename family before browser selection.
- Treat the staging token as local transaction evidence only; never predict or require a backend suffix.
- Capture the actual assigned filename and both backing identities from `process_upload_stream`.
- Delete only pre-upload Project Source identities after exact new-source verification.
- Require the newly assigned source as the final singleton and require both `full_direct` and `full_localhost`.
- Do not advance the normal slice.

### v0.1.103.10.114 — continuous live-profile resolution and causal-submit evidence

- **Type:** repair-only.
- **Baseline:** `v0.1.103.10.113`, which live-proved indexed-family overwrite but was not adopted.
- **Scope:** exact resolved-slot reuse across external-live steps; no nested profile pooling; current ChatGPT submit-flow causality; new valid-envelope early acceptance; challenge classification only from actual evidence; independent `full_localhost`.
- **Out of scope:** indexed-overwrite redesign, Project deletion, artifact adoption without GO, normal `v0.1.104` scope.
- **Promotion:** require `full_direct`, independently executed `full_localhost`, visual-artifact roundtrip, release-live, import smoke, and Artifact Guardian to pass before adoption.


### v0.1.103.10.115 — adoption identity preflight and parse-independent response completion

Repair-only scope: capture the exact successful release Project Source upload, join repository/project identity through the supported command contract before validation, bind adoption to the assigned filename and both backing IDs, accept causally proven same-count assistant-turn replacement after bounded stable idle completion, and classify rate-limit retry evidence only from structured true telemetry. This repair does not advance normal scope or accepted/current state.

### v0.1.103.10.116 — assigned-source-aware post-adoption verification

Repair-only scope: keep accepted/current `v0.1.103.10.115`; distinguish canonical artifact refs from exact assigned Project Source refs in final verification; require exact backing IDs, four matching versions, and three true consistency booleans; emit `release_adopted_and_verified` only after success. No normal-slice scope advancement.

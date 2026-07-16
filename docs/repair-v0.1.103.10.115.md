# Repair v0.1.103.10.115

## Problem

`v0.1.103.10.114` passed all nine release-validation gates, but `--adopt-after-validation` reached the mutation phase without an authoritative joined repository/project identity. `pb artifact verify` therefore returned `project_scope_unresolved` and adoption correctly failed closed. The same run also showed that ChatGPT can recycle the newest assistant DOM container: response text changed after confirmed submission and generation, but the visible assistant count remained equal to the pre-submit baseline. A malformed reply then consumed the long response timeout before retry. Release-control retry classification also still inspected raw log text for `429` phrases.

## Repair contract

1. The current release-control run uploads the canonical Project Source and captures its successful persistent JSON result.
2. Before expensive validation, `pb project join` establishes the exact repository/project identity derived from the explicit release repository identity and the source-add project URL.
3. The adoption evidence records the requested filename, backend-assigned filename, processed file ID, and Library metadata object ID.
4. Evidence-bound `pb artifact adopt` requires joined identity, exact project URL correlation, exact assigned-source presence, both backing IDs, and a singleton verified source family.
5. Artifact registry records retain the requested source reference and both backing IDs.
6. A same-count assistant response is fresh only after confirmed submission, observed generation, changed text, stable bounded polls, and an idle browser/composer state.
7. Response collection completes before reply-envelope parsing. Malformed envelopes may be retried without another 600-second collection wait.
8. Rate-limit retry decisions use structured true telemetry only; prose, field names, false booleans, empty events, and recovered-rate-limit status are not retry evidence.

## Safety invariants

- No registry files are hand-written by release control; identity initialization goes through `pb project join`.
- No filename-only Project Source adoption.
- Missing project identity, repository identity, assigned-source correlation, processed file ID, or Library metadata object ID blocks adoption before mutation.
- Accepted/current remains `v0.1.103.10.68` until full host validation and evidence-bound adoption pass.
- `v0.1.103.10.113` and `v0.1.103.10.114` remain unadopted repair history.

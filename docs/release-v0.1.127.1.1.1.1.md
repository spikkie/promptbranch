# v0.1.127.1.1.1.1 — Acceptance-path conversation provenance validator repair

Baseline: accepted/current `v0.1.126.1.1.1.1.3`.

`v0.1.127.1.1.1` proved the baseline-artifact ask route end to end: 53/53 live candidate tests passed, the actual `ask_question` conversation ID was exactly `6a78783b-3e00-83eb-8dc1-1e814fcf2a59`, and independent verification confirmed `TESTED_GREEN`. The next `ACCEPTED` transition then failed before mutation because `cmd_artifact_accept_candidate()` referenced `_looks_like_chatgpt_project_conversation` without defining/importing it.

This repair is intentionally narrow:

- define one canonical project-conversation predicate using `is_project_conversation_url()` and exact `conversation_id_from_url()` equality;
- make artifact-origin provenance validation delegate to that predicate;
- cover the complete selected-protocol-provenance acceptance branch and exact origin persistence;
- preserve all `.127.1.1.1` routing and `TESTED_GREEN` authority unchanged.

Out of scope: response-completion recovery, browser redesign, source/task routing, manual registry repair, acceptance/adoption authority expansion, normal-slice scope advancement.

Acceptance/current authority does not move during construction. A fresh immutable live lifecycle through `FINAL_VERIFIED` and fresh scoped `pb artifact current --repo chatgpt_claudecode_workflow-2 --json` is still required.

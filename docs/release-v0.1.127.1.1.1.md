# v0.1.127.1.1.1 — Successor ask pin propagation and TESTED_GREEN route verification

Type: repair. Accepted/current baseline remains `v0.1.126.1.1.1.1.3`.

## Trigger

`v0.1.127.1.1` reached a generic 53/53 `TESTED_GREEN`, but its browser report showed `ask_conversation_url=null`, routing source `generated_test_project`, and an executed `ask_question` conversation different from the baseline artifact provenance. The release command argv alone was therefore a false proof.

## Repair

- propagate `--ask-conversation-url` from `cmd_test_suite` into `run_test_suite_async`;
- require the browser report to preserve the exact requested pin and one green `ask_question`;
- extract the actual conversation ID from that executed step and require exact equality with baseline artifact provenance;
- fail the transition with `candidate_test_ask_route_mismatch` before acceptance when any route invariant differs;
- recompute the same route proof during independent `release verify`;
- reload the hash-bound report when reusing validated candidate-test evidence so route proof is never reconstructed from summary fields alone.

## Preserved boundaries

No response-completion recovery, source/task routing change, acceptance/adoption redesign, external-application work, or normal product-scope advancement is included.

## Live closure

Construction is insufficient. Closure requires a fresh immutable candidate test whose executed `ask_question` conversation ID is exactly `6a78783b-3e00-83eb-8dc1-1e814fcf2a59`, followed by canonical `FINAL_VERIFIED` and fresh scoped `artifact current`.

## Construction validation

The exact tracked repair tree passed all 17 mandatory release-validation groups under `/opt/pyvenv/bin/python3` with pytest 9.0.2. `release_state_machine` passed 102 tests with one canonical-only Docker-transition skip; the scheduler/source lifecycle group passed all 14 canonical node IDs; the release pipeline passed 71 tests. The aggregate group runner itself exceeded the outer execution window, so each canonical group command was executed directly rather than weakening or omitting any required group. Live `TESTED_GREEN`/acceptance remains pending.

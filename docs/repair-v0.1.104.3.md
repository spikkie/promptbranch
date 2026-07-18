# Repair v0.1.104.3 — current-turn-scoped interrupted-state readiness

## Baseline

Accepted/current remains `v0.1.103.10.116`. This repair follows the unadopted `v0.1.104.2` candidate.

## Cause

The strict `v0.1.104.2` run passed fresh direct, independent localhost, the unchanged 13-gate sandbox proof, profile preflight, import smoke, and Artifact Guardian. Continuous external-live then treated a historical visible `Retry` control as current `interrupted_answer_state` before bootstrap submission. The one permitted reload ran, but no bootstrap sentinel existed to reverify, so adoption was refused.

## Repair contract

- Scope interruption controls and interruption text to the latest assistant turn or active composer state.
- Ignore visible Retry/Regenerate controls attached only to historical turns.
- Treat an idle composer as ready when an idle control such as Start Voice is visible, with no stop, thinking, running, or latest-turn interruption.
- Run a distinct pre-bootstrap composer-readiness gate.
- Never invoke post-bootstrap recovery unless bootstrap submission succeeded, the expected sentinel was observed, and generation completed.
- Preserve exactly one same-conversation reload only when latest-turn `interrupted_answer_state` is the sole post-bootstrap blocker.
- After reload, wait boundedly for the same conversation to hydrate before checking the bootstrap sentinel and composer.
- Never click Retry, resubmit a historical prompt, create another conversation, or add a general retry.
- Fail closed as `target_conversation_busy` when latest-turn interruption persists.

## Standalone sandbox verification

The sandbox verifier remains byte-identical to `v0.1.104.2` and can be run before the full release workflow:

```bash
python3 scripts/verify-sandbox-mutation-rollback-release-gate.py --repo .
```

Expected terminal status:

```text
sandbox_mutation_verified_and_rolled_back
```

The strict release workflow repeats the same proof as mandatory gate 3/10.

# Release v0.1.40

## Scope

Reconcile `orchestration/docs/` with the actual `v0.1.39` release-line state and resume the planned read-only grill schema slice.

## Changes

- Added `orchestration/docs/current_status.md` to record the real state after `v0.1.39`.
- Added `orchestration/docs/release_line_reconciliation.md` to classify the intervening releases as control-plane hardening rather than orchestration goal replacement.
- Updated the orchestration README and MVP planning docs so they no longer imply the original `v0.1.1`-`v0.1.4` plan is the literal current release sequence.
- Added `orchestration/schemas/grill.schema.json` for proposal-only grill envelopes.
- Added G0-G6 committed grill examples for the k8s-game orchestration test vehicle.
- Added `scripts/orchestration/validate_grill.py` as a deterministic read-only grill validator.
- Added tests that validate all G0-G6 examples and reject unsafe provider/execution authority changes.

## Safety boundary

This release is read-only orchestration control-surface work.

It does not:

- mutate source from grill output;
- adopt artifacts from model output;
- deploy to Kubernetes;
- approve Ollama or local LLMs for the critical path;
- grant execution authority to the model;
- implement a generic orchestration engine.

## Validation

- `python3 scripts/orchestration/validate_examples.py`
- `python3 scripts/orchestration/validate_grill.py`
- `python3 -m pytest -q tests/orchestration`
- `python3 -m compileall -q .`

## Next step

Continue with read-only grill-to-state-machine transition validation before any source mutation or deployment work.

# Repair v0.1.78.2.15 — Project Source add timeout false-negative containment

## Reason

`v0.1.78.2.14` live service evidence showed `pb src add platform-gitops_0.0.4.zip` could return `source_add_failed` with `error=timed out` even though the source was later present and verified. The browser log showed upload and commit completed quickly, a provisional Project Source card was visible, and the only long delay was a persisted ChatGPT conversation-history 429 cooldown after the rate-limit modal cleared.

## Scope

This repair separates Project Source mutation verification from conversation-history cooldown waits. Source add/list/remove/capability operations still record 429/modal telemetry and still acknowledge rate-limit modals, but Project Source persistence refreshes do not sleep on the persisted conversation-history cooldown after the modal clears. The cooldown remains persisted for history-reading operations.

## Files changed

- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `tests/test_project_resolve.py`
- project control-surface documentation
- version metadata

## Validation performed

- Focused Project Source persistence tests verify the post-refresh Project Source proof path passes `respect_history_rate_limit_cooldown=False`.
- Focused rate-limit modal test verifies a non-history Project Source operation can acknowledge and clear the modal without waiting on persisted conversation-history cooldown.
- Version metadata and package syntax checks were run before packaging.

## Boundary confirmation

This is a repair-only release. It does not advance the normal slice, does not change Project deletion policy, does not alter Project Source overwrite/remove containment semantics, and does not mutate adoption/current behavior.

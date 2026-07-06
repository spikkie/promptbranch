# Repair v0.1.103.10.66 — release-live-continuous browser lifetime submit classification

## Scope

This repair preserves the v0.1.103.10.65 trusted conversation direct mode and adds explicit structured handling when the browser page/context closes after readiness verification but before or during composer submit.

## In scope

- Re-check page lifetime before composer click/fill and before submit dispatch.
- Return `browser_context_closed_during_submit` when the page/context closes after readiness.
- Short-circuit click fallbacks after `TargetClosedError`/closed-browser evidence.
- Preserve debug artifact and trace behavior.

## Out of scope

- No Cloudflare workaround.
- No host-CDP/session-manager.
- No copied-profile trust.
- No ChatGPT Project deletion.
- No live-pass claim.

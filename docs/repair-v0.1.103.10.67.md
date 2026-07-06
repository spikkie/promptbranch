# Repair v0.1.103.10.67 — composer wait target-close classification

## Scope

Classify browser target closure during chat input selector waiting as structured browser lifetime failure in `release-live-continuous` trusted conversation direct mode.

## Behavior

- Keep v0.1.103.10.66 direct trusted conversation behavior.
- Keep root project discovery skipped.
- Keep pre-send composer/login/challenge readiness checks.
- Stop composer selector iteration on `TargetClosedError` / target-closed evidence.
- Return `browser_context_closed_during_submit` with `failed_phase=submit` and `submit_subphase=composer_wait`.
- Preserve debug artifacts and trace capture.
- Do not classify as Cloudflare unless challenge evidence exists.

## Out of scope

No Cloudflare workaround, host-CDP/session-manager, copied-profile trust, or ChatGPT Project deletion.

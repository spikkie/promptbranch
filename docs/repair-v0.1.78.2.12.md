# Repair v0.1.78.2.12 — Text-source save trigger fallback and live-seed operator guard

This repair preserves the v0.1.78.2.11 Docker provenance guard, retained delete-frozen project policy, live seed preservation, and strict rate-limit detection while hardening the text Project Source add path observed failing during operator `--run-all-tests` validation.

## Failure being repaired

`v0.1.78.2.11` release-control reached the full browser suite but failed `project_source_add_text` with `transaction_status=ui_trigger_not_observed_not_verified_present`: the text-source UI was visible and advertised as supported, but the primary save click produced no observed save request and no refreshed persistence proof.

## Scope

- Pass the save-request watcher into the text-source add helper.
- After the primary save click, verify that a text-source save request was actually observed.
- If no save request is observed, try bounded fallback triggers:
  - `Control+Enter` on the text input.
  - `Control+Enter` on the page.
  - DOM-discovered enabled submit button in the active dialog/popover.
- Log fallback probes and save-watch summaries for operator diagnostics.
- Keep `.pb_profile_local_debug/` as the authenticated live-test seed and `.pb_profile_local_debug_pools/` disposable.
- Preserve Docker host/image/container/health provenance checks.
- Preserve strict rate-limit evidence detection.
- Preserve ChatGPT Project deletion freeze.

## Out of scope

- Secure ChatGPT Project delete protocol.
- Project Source removal behavior changes.
- Artifact adoption/current mutation.
- v0.1.79 / k8s-game work.

## Validation intent

The repair is candidate-only until operator-side release-control proves `project_source_add_text` and the live-test rows, and adoption/current evidence confirms runtime, state artifact, state source, registry current, and consistency alignment.

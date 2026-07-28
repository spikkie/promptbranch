# v0.1.111.5 — Named-step ETA planning and stable countdown

## Baseline

- Accepted/current: `v0.1.111.4.1`
- Candidate: `v0.1.111.5`
- Release mode: repair
- Scope advance: forbidden

## Problem

The existing progress ETA divided total elapsed time by completed unit count and multiplied by remaining count. Browser, agent, validation, localhost, local, and external-live steps have materially different latency. The result jumped sharply when a long step completed, treated known skips as future work, and could imply zero remaining time while a long-running named step was still active.

## Corrective contract

1. Estimate the current named step and each pending active named step separately.
2. Prefer successful same-step, same-transport medians.
3. Use successful direct observations as localhost ETA-only priors when localhost history is absent.
4. Fall back to successful same-phase observations only when named-step history is absent.
5. Exclude known skips before calculation.
6. Emit `active_remaining`, `eta_approx`, `eta_range`, `eta_confidence`, and `eta_basis` in progress text and JSON.
7. Keep the countdown stable or narrowing while the active plan only shrinks.
8. Keep a bounded non-zero overrun tail while the current step remains visibly running.
9. Persist bounded observations under `.pb_profile/eta-history.json` using atomic replacement.
10. Ignore failed observations for estimation.
11. Treat missing, malformed, or unwritable ETA history as informational degradation only.

## Authority boundary

ETA does not influence:

- step normalization;
- pass/fail;
- fail-fast;
- direct/localhost evidence independence;
- release verdict;
- Project Source publication;
- artifact adoption;
- accepted/current verification.

## Validation

Required focused coverage:

- first run with no history;
- same-step median;
- phase fallback;
- known-skip exclusion;
- long-running current-step overrun;
- stable countdown clamping;
- direct-to-localhost ETA prior;
- failed-observation exclusion;
- atomic bounded history;
- validation outcome independence;
- `pb test` and release-control output contract.

Strict host validation, publication, adoption, and current verification remain required before acceptance.

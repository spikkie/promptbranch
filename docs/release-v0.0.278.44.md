# Release v0.0.278.44

## Scope

Build from the green v0.0.278.42 behavior and retain the v0.0.278.43 slim trusted-refill retry fill path, but restore a minimal readiness proof before dispatching retry Enter.

## Changes

- Preserves the v0.0.278.42 submit order:
  - raw Enter primary
  - trusted-refill + Enter retry second
- Preserves raw-Enter prepare-only fast-fail.
- Preserves fast latest-turn answer promotion.
- Retains the v0.0.278.43 slim retry refill path.
- Adds a minimal retry send-ready barrier before retry Enter:
  - exact prompt marker/prefix must still be present in the composer;
  - `#composer-submit-button[data-testid="send-button"]` or equivalent send control must be visible and enabled;
  - a short settle dwell is applied before retry Enter.
- Falls back to the v0.0.278.42 full trusted-refill behavior if the slim send-ready barrier is not reached quickly.

## Safety notes

The barrier does not weaken submit causality. Final success still requires an exact-marker network submit or backend/DOM user-turn evidence. Prefix-only stale matches remain rejected.

## Validation

- `python3 -m compileall -q .`
- Focused pytest suite for browser client, service client, container API, compose timeout policy, CLI parser, ChatGPT container API, and Promptbranch CLI.

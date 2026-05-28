# Release v0.0.278.39

## Scope

Small regression-control release built from v0.0.278.38.

This release preserves the v0.0.278.38 exact-marker submit gate and adds a narrow response handoff fix: if post-submit visibility evidence already contains a parseable fresh assistant JSON answer with the exact current sentinel, the browser client promotes that payload immediately instead of entering another response wait/probe cycle.

## Changes

- Added post-submit visibility evidence answer promotion.
- Skips prompt echoes that contain the requested JSON object inside user instructions.
- Requires the same exact response marker/sentinel freshness gate before promotion.
- Records `response_visibility_promotion_used`, `response_accepted_source`, `response_accepted_selector`, and response extraction candidates.
- Keeps backend-first disabled by default and preserves stale-answer rejection.

## Validation

- `python3 -m compileall -q .`
- Focused clean extracted ZIP validation for browser client, service client, container API, CLI parser, compose policy, ChatGPT container API, and Promptbranch CLI tests.

## Expected live behavior

If the DOM visibility probe already captured the fresh JSON answer, `pb ask --json` should return the answer with:

- `status=completed`
- `response_freshness_verified=true`
- `response_accepted_source=post_submit_visibility_generic_turn` or equivalent visibility-promotion source

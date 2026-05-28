# Release v0.0.278.38

## Purpose

Regression-control release for submit confirmation correctness.

## Changes

- Require exact current request marker/sentinel presence in backend or DOM user-turn evidence before `submit_confirmed=true`.
- Reject `prompt_short_prefix` / prefix-only matches as submit confirmation.
- Classify stale-prefix backend matches as `backend_stale_user_turn_prefix_match_rejected`.
- Classify prepare-only submit without exact marker commit as `prepare_only_without_exact_marker_commit`.
- Preserve diagnostics for requested markers, matched marker, marker presence, matched user-turn preview/hash, and stale marker values.

## Boundary

This release does not fix ChatGPT submit finalization or answer extraction. It prevents false-positive submit confirmation so the next release can safely distinguish dispatch failure from visibility or answer retrieval failure.

## Validation

- `python3 -m compileall -q .`
- focused pytest suites documented in the release response
- clean extracted ZIP verification

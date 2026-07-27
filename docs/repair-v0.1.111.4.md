# v0.1.111.4 — Deterministic external-live idle handoff

## Baseline

Accepted/current remains `v0.1.109.1.1`. `v0.1.111.3` is not adopted.

## Causal defect

Two complete strict `v0.1.111.3` runs passed the product transports but failed external-live before bootstrap. The trusted Promptbranch development conversation exposed `Stop answering`; release-live waited only briefly, returned `target_conversation_busy`, and the release report represented the three dependent live gates as additional failures.

## Repair contract

- The trusted `/g/.../c/...` URL proves authentication and exact Project identity only.
- Release-live never types into, stops, reloads for mutation, or waits indefinitely on that operator-owned conversation.
- In the same browser context and physical profile, release-live navigates to the exact Project home.
- The Project-home composer must become idle within the bounded `PROMPTBRANCH_RELEASE_LIVE_IDLE_HANDOFF_TIMEOUT_SECONDS` window (default 30 seconds, hard cap 300 seconds).
- Only then may bootstrap submit and create a dedicated release-live conversation.
- A failed handoff emits `release_live_idle_handoff_failed`, attempts neither bootstrap nor ask, and remains release-blocking.
- Release control records `live_project_ensure` as the one causal failure. `ask_live`, `visual_artifact_roundtrip`, and `release_live` become `skipped_dependency_failed` with dependency metadata.
- No automatic Stop action is allowed.
- Direct, localhost, sandbox, publication, adoption, and current-verification gates are unchanged.

## Deferred repair

The inaccurate elapsed/completed ETA is not changed here. `v0.1.111.5 — Named-step ETA planning and stable countdown` is the immediately following repair.

## Validation

```bash
python3 -m pytest -q \
  tests/test_release_live_continuous_direct_conversation.py \
  tests/test_promptbranch_shell_scripts.py \
  -k 'idle_handoff or dependency_skips or release_live_continuous'
```

Strict host validation and adoption remain mandatory.

# v0.1.123.2.3 — Operation-scoped response guardrails and nested timeout repair

`v0.1.123.2.3` is a repair-only release from accepted/current `v0.1.123.2.2`. Formal MVP proof remains `0/2`; `v0.1.124` and `v0.1.125` remain normal proof cycles 1 and 2.

## Defect

The pinned `v0.1.124` release request was causally submitted and ChatGPT continued generating, but response waiting aborted after about nine milliseconds because a background Project Source attachment-download 403 observed before submit remained marked as a global terminal browser challenge. The browser was configured for 1200 seconds, while the outer integrated lifecycle step was only 900 seconds.

## Repair

- Record `submit_confirmed_monotonic` and `guardrail_event_cursor` only after current-prompt submit causality is confirmed.
- Evaluate response-wait backend-403 events from that operation boundary.
- Ignore pre-submit 403 telemetry and unrelated post-submit file-download 403 events while the target conversation remains healthy.
- Keep current-operation conversation 403s, challenge pages, root redirects, and target closure fail-fast.
- Raise the default assistant response budget to 1800 seconds.
- Derive an outer integrated step budget of at least 2220 seconds: 1800 response + 120 fresh-turn correlation + 180 artifact materialization + 120 safety.
- Preserve the one-command operator interface and explicit `--conversation-url` pin.

## Scope

No artifact adoption, Project Source mutation, Git commit, or Git push is performed by candidate creation. This repair cannot count toward the two consecutive normal MVP proof cycles.

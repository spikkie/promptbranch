# v0.1.128.1.1.1.1.1 — Task/message response-chain diagnostic repair

## Baseline

Authoritative adopted/current baseline remains `v0.1.128.1.1` with SHA-256 `89fe16e498b3035f94db5375c7ef9ee924a9d82d15ce5790ef765658e0db6328`. Predecessor `v0.1.128.1.1.1.1` live-proved the pinned-conversation fresh assistant-chain continuity repair: `ask_question` returned `INTEGRATION_OK` in 36.863 seconds. The same full run then failed later at `task_message_flow.ask` after 292.238 seconds with `service_internal_deadline_timeout` while creating a new chat from the generated Project page.

## Repair scope

- Preserve the `.1.1.1` projection-completeness repair unchanged.
- Preserve the `v0.1.128.1.1.1.1` fresh assistant-chain acceptance behavior unchanged.
- Add a bounded `promptbranch.response_chain_diagnostics` snapshot to response waits.
- Record baseline URL/conversation identity, assistant count and stable text hash.
- Record project-page → conversation URL transitions and conversation IDs.
- Record assistant count/delta, text hash/length/preview, baseline equality, generation/idle/thinking/stop state, freshness-latch state/reason, stable polls, completion readiness and blockers.
- Emit explicit freshness-latch and URL-transition log events; throttle ordinary poll logs.
- Refresh the latest ask progress snapshot during response polling so a service-internal deadline returns the last response-chain state instead of only the old `submit_confirmed` snapshot.
- Surface `response_chain_diagnostics` on normal success, browser response timeout, and service-internal deadline results.

## Non-goals

No change to response freshness acceptance, project-conversation selection, submit behavior, timeout values, lifecycle states, artifact authority, or external application scope. Diagnostics first; behavior repair follows only if live evidence requires it.

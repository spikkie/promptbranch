# ChatGPT backend-api surfaces used by Promptbranch

Status: diagnostic inventory for `v0.1.39`.

## Boundary

These `https://chatgpt.com/backend-api` paths are **undocumented ChatGPT web backend surfaces** observed or called from the browser session. They are not a supported public API contract. Promptbranch must treat them as volatile diagnostics or browser-context read paths, redact credentials, and fail closed when they change.

Operational rules:

- Do not copy cookies, bearer tokens, or full response bodies into logs.
- Prefer backend JSON/network data for reads, but keep DOM fallbacks.
- Treat `403` and `429` responses as guardrail/rate-limit evidence.
- Respect `retry-after` when present.
- Persist a cooldown marker and pause further ChatGPT calls instead of retrying immediately.
- Do not use observed mutation paths as direct APIs unless a future controlled transaction proves persistence and safety.

## Current surfaces

| Surface | Method | Current Promptbranch use | Risk class |
|---|---:|---|---|
| `/backend-api/gizmos/snorlax/sidebar` | GET | Backend-first workspace/project sidebar enumeration and shallow project task discovery. | Private, read-oriented, volatile. |
| `/backend-api/gizmos/{project_id}/conversations` | GET | Project-scoped task/conversation enumeration; bounded to `limit <= 50`. | Private, read-oriented, volatile. |
| `/backend-api/conversations` | GET | Global conversation-history fallback and diagnostic enumeration. This is rate-limit sensitive. | Private, rate-limit sensitive. |
| `/backend-api/conversation/{conversation_id}` | GET | Conversation detail fallback, transcript hydration, and history-detail classification. | Private, rate-limit sensitive. |
| `/backend-api/f/conversation/prepare` | POST | Observed prepare phase during ask/send instrumentation. Promptbranch observes this path; it should not be treated as a stable direct-call API. | Private, observed-only. |
| `/backend-api/conversation` | POST | Observed backend commit/submission path during ask/send instrumentation. | Private, mutation sensitive, observed-only. |
| `/backend-api/conversation/{conversation_id}/stream_status` | GET | Observed post-submit stream-state diagnostics. | Private, observed-only. |
| `/backend-api/conversation/init` | POST | Observed conversation initialization diagnostics. | Private, observed-only. |
| `/backend-api/conduit/finalize` | POST | Observed conduit finalization diagnostics. | Private, observed-only. |
| `wss://chatgpt.com/backend-api/conduit` | WebSocket | Observed streaming/conduit diagnostics. | Private, observed-only. |
| `/backend-api/files/process_upload_stream` | POST | Observed file upload processing when project sources are added through the browser. | Private, mutation sensitive. |
| `/backend-api/gizmos/snorlax/upsert` | POST | Observed project/source update persistence path. | Private, mutation sensitive. |

## `pb debug rate-limit --json`

`pb debug rate-limit --json` is the read-only diagnostic entrypoint for the conversation-access guardrail. It captures:

- visible rate-limit modal state and modal text;
- `403` / `429` backend responses from `/backend-api/*`;
- `retry-after` when the response exposes it;
- the persisted cooldown marker;
- the current backend-api surface inventory;
- the pause policy used by Promptbranch.

Expected rate-limited result shape:

```json
{
  "ok": false,
  "action": "debug_rate_limit",
  "status": "rate_limited",
  "retry_after_seconds": 180,
  "modal": {
    "detected": true,
    "text": "You’re making requests too quickly..."
  },
  "cooldown": {
    "active": true,
    "cooldown_remaining_seconds": 179.5
  },
  "pause_policy": {
    "pause_further_chatgpt_calls": true,
    "do_not_retry": true,
    "safe_next_action": "pause_chatgpt_calls_until_retry_after_or_cooldown_expires"
  }
}
```

A clear result uses `status: "clear"` and `pause_further_chatgpt_calls: false`.

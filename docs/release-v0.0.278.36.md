# Release v0.0.278.36

Regression-control release built from v0.0.278.35.

## Scope

- Restores v0.0.278.15-style DOM/latest-turn answer retrieval as the default via `CHATGPT_ASK_RETRIEVAL_MODE=legacy_dom_first`.
- Disables backend-first answer waiting by default; opt in with `CHATGPT_BACKEND_FIRST_ANSWER_WAIT=1` or `CHATGPT_ASK_RETRIEVAL_MODE=backend_first`.
- Preserves strict request-marker/sentinel freshness validation before accepting any DOM or visible UI answer.
- Adds a final `/v1/ask` internal deadline guard so the browser service should return before the CLI client timeout instead of surfacing `service_client_read_timeout`.

## Non-goals

- Does not weaken stale-answer protection.
- Does not add a new submit strategy.
- Does not adopt backend-first answer retrieval as the default.

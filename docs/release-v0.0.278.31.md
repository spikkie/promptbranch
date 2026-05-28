# Release v0.0.278.31

## Scope

Backend-first answer retrieval after keyboard-submit backend commit.

## Changes

- Uses backend conversation detail as the first answer extraction source when submit evidence contains a matched backend user-turn commit.
- Keys answer extraction to the committed user turn id/index and only accepts assistant turns after that commit.
- Keeps response-request marker / nonce freshness verification as the success gate.
- Keeps DOM JSON extraction as fallback only after backend-first probing fails to find a parseable fresh answer.
- Caps submit-confirmed answer wait with `CHATGPT_SUBMIT_CONFIRMED_ANSWER_TIMEOUT_MS` defaulting to 120000 ms, so confirmed-submit answer timeouts return as operation results instead of waiting beyond common CLI read timeouts.

## Validation

- `python3 -m compileall -q .`
- `pytest -q tests/test_project_list_browser_client.py`
- focused version/container/compose/CLI smoke tests

## Adoption note

Do not adopt unless the live stale-guard run returns the fresh sentinel with response freshness verified.

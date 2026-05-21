# Repair v0.0.245.9 — Google device-prompt visibility logging

Base release: v0.0.245.8
Repair version: v0.0.245.9

## Reason

Google login can reach `/signin/challenge/dp`, where Google asks the operator to choose a number on a phone. When the browser runs inside Docker, the operator cannot see the container browser UI, so `login-check` appears stuck while waiting for manual confirmation.

## Files changed

- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- version metadata files

## Change summary

- Detect Google device-prompt challenge URLs: `/signin/challenge/dp`.
- Extract visible page text from the challenge page.
- Extract short candidate challenge numbers from visible text.
- Log operator-facing instruction, for example: `Choose number 37 on your phone.`
- Save diagnostic text/HTML/screenshot artifacts when the challenge is detected but no number can be extracted and debug artifacts are enabled.
- Do not bypass Google 2FA or attempt to answer the challenge automatically.

## Validation

Focused unit tests validate URL detection, text/number extraction, snapshot parsing, and operator-instruction logging.

No normal release scope was advanced.

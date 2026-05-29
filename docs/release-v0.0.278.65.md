# Release v0.0.278.65

## Base

Built from `chatgpt_claudecode_workflow_v0.0.278.64.zip`.

## Purpose

Repair the first-run local headed debug browser bootstrap path for empty `.pb_profile_local_debug/` profiles while preserving the successful v0.0.278.64 Patchright headed-local submit and DOM-delta answer detection behavior.

## Changes

- Added `.pb_profile_local_debug/` to `.gitignore`.
- Added `CHATGPT_PASSWORD_SECRET_FILE` to the shared password-file resolver.
- Normalized CLI credential defaults so `EMAIL` is accepted as an alias for `CHATGPT_EMAIL` and `CHATGPT_PASSWORD_SECRET_FILE` is accepted as an alias for `CHATGPT_PASSWORD_FILE`.
- Updated `promptbranch_login_test.py` to load `.env` and accept both `EMAIL` and `CHATGPT_EMAIL`.
- Added direct `/auth/login` bootstrap handling when ChatGPT redirects a fresh profile to the current login surface.
- Added current-login-page detection for `Continue with Google`, email entry, and continue controls.
- Added explicit `auth_challenge_required` classification for Google/passkey/2FA/CAPTCHA/device-prompt style blocks.
- Changed manual-login polling to avoid repeatedly navigating away from active `/auth/login` or Google auth pages.
- Preserved v0.0.278.64 DOM-delta submit confirmation and answer extraction.

## Validation

Focused validation performed:

```text
python3 -m compileall -q promptbranch_browser_auth/client.py promptbranch_automation/automation.py promptbranch_automation/service.py promptbranch_cli.py promptbranch_login_test.py tests/test_automation_password_resolution.py tests/test_project_list_browser_client.py
pytest -q tests/test_automation_password_resolution.py tests/test_project_list_browser_client.py tests/test_promptbranch_automation_service.py tests/test_promptbranch_service_client.py
pytest -q tests/test_promptbranch_cli.py tests/test_cli_parser.py tests/test_chatgpt_container_api.py tests/test_promptbranch_container_api.py tests/test_compose_timeout_policy.py tests/test_response_completion.py
```

Result:

```text
465 passed
```

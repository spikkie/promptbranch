# Release v0.0.278.63

Base release: `chatgpt_claudecode_workflow_v0.0.278.62.zip`

## Purpose

Patchright-only headed-local hardening for visual browser development and diagnostics.

This release preserves the normal Docker/headless target while making the local headed Patchright path safer on Linux desktops where Chrome may otherwise crash with Wayland/Vulkan/Ozone errors before the browser context is usable.

## Changes

- Keep Patchright as the required browser driver for local visual browser diagnostics.
- Reuse the existing `ChatGPTAutomation -> ChatGPTBrowserClient -> _run_with_context` persistent-context launch path used by `promptbranch_login_test.py`.
- Add default headed Patchright Chrome safety arguments:
  - `--ozone-platform=x11`
  - `--disable-gpu`
  - `--disable-vulkan`
- Apply those safety arguments only for headed Patchright sessions; Docker/headless remains unchanged.
- Add `CHATGPT_BROWSER_EXTRA_ARGS` parsing so local operators can add additional Chrome flags without code changes.
- Add `CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS=0` opt-out for the default headed Patchright safety arguments.
- Convert Patchright persistent-context launch failures into structured `browser_launch_failed` payloads for `pb ask` instead of leaking an unstructured Python stack trace from the CLI path.
- Keep the v0.0.278.62 composer pre-fill readiness fix and JSON-default/fail-closed ask behavior.

## Non-goals

- No switch to Playwright.
- No Docker release-path behavior change.
- No change to `_fill_chat_prompt` or `_submit_prompt`.
- No new submit/refill/click strategy.

## Validation

Focused clean-tree validation:

```text
pytest -q tests/test_response_completion.py tests/test_promptbranch_container_api.py tests/test_chatgpt_container_api.py tests/test_cli_parser.py tests/test_compose_timeout_policy.py tests/test_promptbranch_cli.py
```

Additional checks:

```text
python3 -m compileall -q .
ZIP reopened and checked for root layout, VERSION, nested ZIPs, and hygiene exclusions.
```

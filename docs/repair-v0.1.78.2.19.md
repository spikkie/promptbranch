# Repair v0.1.78.2.19 — prompt-file submit policy automation-wrapper wiring

## Baseline

- Accepted/current baseline remains: `v0.1.78.2.16`
- Superseded candidates: `v0.1.78.2.17`, `v0.1.78.2.18`
- Repair release: `v0.1.78.2.19`
- Continuity: includes the `v0.1.78.2.17` prompt-file submit-policy repair and the `v0.1.78.2.18` smoke/strict-causality repair.

## Reason

After installing `v0.1.78.2.18`, the focused smoke preserved diagnostics and exposed a service-layer integration failure:

```text
TypeError: ChatGPTAutomation.ask_question_result() got an unexpected keyword argument 'prefer_button_submit'
```

The CLI, service client, container API, automation service, and browser client were updated to carry `prefer_button_submit`, but the intermediate `promptbranch_automation.automation.ChatGPTAutomation` wrapper still had the old method signature. The automation service therefore failed before reaching the browser submit layer.

## Files changed

- `promptbranch_automation/automation.py`
  - Added `prefer_button_submit: bool = False` to `ChatGPTAutomation.ask_question()`.
  - Added `prefer_button_submit: bool = False` to `ChatGPTAutomation.ask_question_result()`.
  - Forwarded `prefer_button_submit` to `ChatGPTBrowserClient.ask_question_result()`.
- `tests/test_promptbranch_automation_service.py`
  - Added focused wrapper-wiring coverage so this regression fails before release.
- Version/control-surface files updated for `v0.1.78.2.19`.

## Scope confirmation

This is a repair-only release. It does not advance the normal slice, does not change CV generator code, does not change Project Source add/remove behavior, does not change ChatGPT Project deletion behavior, and does not redesign artifact registry or retry/backoff policy.

## Validation

Required before acceptance:

1. Python compile check.
2. Focused prompt-file/API/service/browser tests.
3. `./scripts/smoke-pb-ask-prompt-file.sh` live smoke in the authenticated operator runtime.
4. Full release-control/adoption proof before calling this artifact accepted/current.

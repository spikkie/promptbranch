# Repair v0.0.276.8 — Browser-assisted artifact download

Base release: v0.0.276.7
Repair version: v0.0.276.8

## Reason

`pb artifact intake --download` could parse a valid ZIP candidate from a Promptbranch reply, but could not download ChatGPT `sandbox:/mnt/data/...` links because those references require the active browser/session context. Operators had to click the link manually and then use `--local-file`.

## Files changed

- `promptbranch_cli.py`
- `promptbranch_browser_auth/client.py`
- `promptbranch_automation/automation.py`
- `promptbranch_automation/service.py`
- `promptbranch_service_client.py`
- `promptbranch_container_api.py`
- `tests/test_promptbranch_cli.py`
- version metadata files

## Behavior

For selected artifact candidates with `sandbox:` URLs, `pb artifact intake --download` now attempts browser-assisted download by opening the selected conversation, finding the rendered ZIP link, clicking it with Playwright download handling, saving it into `.pb_profile/artifact_inbox/`, and then continuing through the existing verification/migration flow when requested.

## Validation performed

- `bash -n` on release scripts
- `python3 -m py_compile` on changed Python files
- focused pytest for browser-assisted sandbox artifact intake
- ZIP hygiene/layout verification

## Slice/line status

No slice or line was advanced. This repair only fixes artifact intake transport behavior and related operator evidence.

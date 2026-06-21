# Repair v0.1.84.3 — bounded project-create submit recovery after 429/cooldown

## Base

`v0.1.84.2` focused repair candidate. Accepted/current remains `v0.1.79` until later adoption/current evidence exists.

## Reason

`release_control.v0.1.84.2.run_all_tests.log` showed `project_ensure_create_or_reuse` failing with:

```text
504 error for POST http://localhost:8000/v1/projects/ensure: Create project submit button stayed disabled after filling project name
```

The log also showed rate-limit modal acknowledgement and cooldown handling, but the uploaded file ended after the release-control retry wait line and did not prove the final retry result. The repair still addresses the observed first-attempt disabled-submit failure because it is a bounded browser recovery defect.

## Repair

When the create-project submit button remains disabled after filling a fresh project name, Promptbranch now performs bounded recovery before failing:

1. Log disabled-state diagnostics.
2. Check for a ChatGPT 429 modal again, acknowledge it, and honor the configured cooldown.
3. Clear/refill the project name.
4. Dispatch input/change/keyup/blur events and tab out to trigger ChatGPT frontend validation.
5. Reacquire the submit button and retry enablement.
6. Fail closed after the configured bounded attempt count.

## Out of scope

- Re-enabling ChatGPT Project deletion.
- Ledger creation or append.
- `accept-event --write`.
- Project Source mutation behavior changes.
- Artifact adoption/current mutation.
- Deployment or model execution.

## Validation

Focused unit tests cover successful disabled-submit recovery and bounded failure. Version/control-surface checks, shell focused tests, compileall, bash syntax, Artifact Guardian, and ZIP hygiene were run for the repair candidate.

# Release v0.1.104.1

`v0.1.104.1` is a repair-only candidate for `v0.1.104`.

## Repair slice

```text
v0.1.104.1 — project-remove frozen scheduler timeout repair
```

## Preserved normal slice

```text
v0.1.104 — Sandbox mutation verification and rollback evidence gate
```

## Scope

This release repairs only the deterministic test/scheduler timeout path for:

```text
tests/test_promptbranch_automation_service.py::test_project_remove_is_frozen_before_profile_scheduler
```

The repair preserves:

- sandbox mutation verification behavior from `v0.1.104`
- sandbox-only mutation behavior from `v0.1.103`
- correction planning boundaries from `v0.1.102`
- read-only result diagnosis from `v0.1.101`
- no ChatGPT Project deletion
- no Project Source mutation behavior change
- no artifact adoption behavior change
- no normal scope advancement

## Validation status

Focused validation is required before handoff. Full release-control/adoption remains required before this candidate may be called accepted/current.

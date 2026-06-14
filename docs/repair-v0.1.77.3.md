# Repair v0.1.77.3 — Hidden temporary project removal hardening

## Base release

```text
intended release: v0.1.77
previous repair candidate: v0.1.77.2
repair version: v0.1.77.3
```

## Reason

`v0.1.77.2` correctly failed closed when cleanup could not verify temporary project absence, but the full release-control run still failed because the exact-name project remained resolvable while the visible sidebar removal path could not find the configured project.

The log showed:

```text
project_remove_cleanup_missing_unverified
absence_verification.status=project_still_present_or_ambiguous
resolve matched exactly one temporary project
```

## Files changed

```text
promptbranch_browser_auth/client.py
tests/test_project_resolve.py
docs/repair-v0.1.77.3.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_version.py
```

## Repair scope

```text
- no normal slice advanced
- no registry/adoption semantics changed
- no repo-loop behavior changed
- no Project Source upload behavior changed
```

## Implementation

The project removal fallback now opens the ChatGPT "More projects" surface when the configured project is not visible in the normal sidebar. This gives cleanup another DOM path for projects that are still resolvable by name but not currently visible in the first sidebar page.

## Validation performed

```text
focused project removal tests
focused cleanup retry tests
project control-surface tests
version tests
compileall
ZIP hygiene
clean extraction focused validation
```

## Slice advancement

```text
normal slice advanced: no
line advanced: no
state advanced: no
```

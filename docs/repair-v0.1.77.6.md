# Repair v0.1.77.6 — Project-page delete-menu fallback and bounded validation timeout

## Base release

```text
base accepted/current: v0.1.76
normal candidate: v0.1.77
repair chain: v0.1.77.1 -> v0.1.77.2 -> v0.1.77.3 -> v0.1.77.4 -> v0.1.77.5
repair version: v0.1.77.6
```

## Reason

`v0.1.77.5` release-control still failed cleanup because the temporary project remained resolvable by exact name while `/v1/projects/remove` could not find the configured project in the sidebar. The same run also spent the full 600 seconds on the `browser_scheduler_source_lifecycle` release-validation group timeout after the live-browser cleanup failure.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
promptbranch_browser_auth/client.py
chatgpt_browser_auth/client.py
promptbranch_test_suite.py
tests/test_project_resolve.py
tests/test_promptbranch_test_suite.py
tests/test_promptbranch_version.py
docs/repair-v0.1.77.6.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
```

## Changes

- Added generic project-page menu selectors for project deletion when the page does not expose the old `Show project details` label.
- Kept cleanup fail-closed: if the temporary project remains resolvable after retries, cleanup still fails.
- Reduced the focused `browser_scheduler_source_lifecycle` release-validation timeout to 120 seconds so a hang is reported faster instead of costing a full 600 seconds.

## Scope control

No normal slice advanced. No repo-loop, adoption, registry, Project Source upload, Docker, or release-set behavior was changed.

## Validation

Focused tests, compileall, bash syntax checks, clean extraction checks, and ZIP hygiene were run before packaging.

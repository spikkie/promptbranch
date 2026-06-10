# Repair v0.1.71.5 — VERSION_TAG double-v normalization

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.71.4.zip
```

## Repair version

```text
v0.1.71.5
```

## Reason

The v0.1.71.4 release lifecycle passed install ZIP verification, installation, Docker service startup, service-health version normalization, and reached full-test import smoke. Full-test failed because `promptbranch_version.VERSION_TAG` was constructed as:

```text
vv0.1.71.4
```

while the expected canonical tag was:

```text
v0.1.71.4
```

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_version.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/repair-v0.1.71.5.md
```

## Scope confirmation

This is a narrow repair. It does not advance the v0.1.71 normal slice, does not change Docker behavior, does not change project-registry behavior, does not add release-set orchestration, and does not change artifact adoption semantics.

## Behavior change

```text
PACKAGE_VERSION is bare PEP 440 text: 0.1.71.5
VERSION_TAG is canonical project text: v0.1.71.5
version_tag("0.1.71.5") == v0.1.71.5
version_tag("v0.1.71.5") == v0.1.71.5
version_tag("vv0.1.71.5") == v0.1.71.5
```

## Validation

```text
focused promptbranch_version regression tests passed
package import smoke passed
source version consistency passed
project control-surface tests passed
compileall passed
clean extraction focused validation passed
ZIP hygiene passed
```

## Full-test status

```text
Full release-control lifecycle was not run by the assistant for this repair candidate.
```

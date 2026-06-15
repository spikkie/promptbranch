# Repair Release v0.1.77.5

## Base release

```text
v0.1.77 repair line
```

## Repair version

```text
v0.1.77.5
```

## Reason

The v0.1.77.4 release-control install plan failed before installation because the candidate ZIP was missing the required root `.gitignore` file.

```text
release_zip_import_plan.ok=false
missing_required_root_files=[".gitignore"]
```

This is a ZIP packaging defect in the intended v0.1.77 repair line.

## Files changed

```text
.gitignore
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_version.py
docs/repair-v0.1.77.5.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
```

## Validation performed

```text
focused version/control tests
compileall
bash syntax
ZIP hygiene
clean extraction import-plan root-file check
```

## Scope control

```text
No normal slice advanced.
No release line advanced.
No repo-loop behavior changed.
No registry/adoption behavior changed.
No Project Source upload behavior changed.
```

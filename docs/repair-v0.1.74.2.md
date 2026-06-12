# Repair v0.1.74.2 — Release-lifecycle plan test profile isolation

## Base release

```text
v0.1.74
```

## Prior failed repair candidate

```text
v0.1.74.1
```

## Repair version

```text
v0.1.74.2
```

## Reason

`v0.1.74.1` fixed release-validation pytest runner interpreter selection, but full release-control still failed in the required release-validation groups. The failing tests were synthetic release-lifecycle plan tests:

```text
test_release_lifecycle_plan_composes_phases_without_mutation
test_release_lifecycle_plan_embeds_read_only_install_planning
```

In the operator repository, those tests could read the ambient `.pb_profile` accepted/current registry state and block the synthetic `v0.0.257` / `v0.0.258` plan as stale relative to the real accepted baseline. That made the tests environment-dependent.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_cli.py
tests/test_promptbranch_version.py
docs/repair-v0.1.74.2.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
```

## Fix

The release-lifecycle plan tests now pass an isolated `profile_dir` under `tmp_path`, matching the isolation pattern already used by adjacent release policy tests. This preserves production reconciliation behavior while preventing synthetic plan tests from depending on operator-local artifact state.

## Scope confirmation

```text
No normal scope advanced.
No new v0.1.75 work was started.
No production release lifecycle reconciliation behavior was weakened.
No Project Source, artifact adoption, browser scheduler, or registry semantics were changed.
```

## Validation performed

```text
focused release-validation/release-lifecycle plan tests
focused artifact JSON contract tests
focused scheduler/source lifecycle tests
project/repo/control/version tests
compileall
ZIP hygiene
clean extraction validation
```

## Acceptance condition

`v0.1.74.2` remains a candidate until full release-control exits 0 and `pb artifact current --json` or `pb artifact current --all --json` confirms accepted/current alignment.

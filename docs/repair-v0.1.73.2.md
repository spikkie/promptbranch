# Repair v0.1.73.2

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.73.1.zip
```

## Repair version

```text
chatgpt_claudecode_workflow-2_v0.1.73.2.zip
```

## Reason

Focused post-adoption validation for v0.1.73.1 exposed repair-only validation/reporting regressions:

1. stale tests hard-coded `v0.1.0` instead of using the active runtime version fixture;
2. `pb release baseline-status --json` no longer exposed the backward-compatible `baseline_evidence` object;
3. `pb artifact current --all --json` for external repo baselines reported null state fields and false registry/state alignment even when the project registry current record was valid;
4. the manual missing-local-artifact negative smoke used a mismatched artifact prefix and therefore tested prefix mismatch instead of `local_artifact_not_found`.

## Files changed

```text
promptbranch_cli.py
tests/test_promptbranch_cli.py
VERSION
pyproject.toml
promptbranch_version.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/repair-v0.1.73.2.md
```

## Validation performed

```text
focused artifact/adopt/current/baseline-status/mvp-status tests
project/repo focused tests
project control-surface tests
version tests
compileall
source version consistency
package import smoke
ZIP hygiene
clean extraction validation
```

## Scope confirmation

```text
No normal slice advanced.
No v0.1.74 functionality added.
No release-set orchestration added.
No Project Source upload behavior changed.
No runtime/browser automation behavior changed.
No Docker/deployment behavior changed.
No candlecast baseline changed.
```

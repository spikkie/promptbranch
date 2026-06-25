# Repair v0.1.91.2 — Run-all final summary aggregation live-step payload selection repair

## Base release

`v0.1.91.1` accepted/current.

## Repair version

`v0.1.91.2`

## Reason

The `v0.1.91.1 --run-all-tests --adopt-after-validation` proof still ended with `all_tests_final_verdict=FIX` and listed `live_project_ensure`, `ask_live`, `visual_artifact_roundtrip`, and `release_live` as failed even though the embedded live command payloads showed successful verified results. The remaining defect was in final summary aggregation: release-control could not reliably extract pretty-printed live command JSON from noisy mixed shell/browser logs, so successful live payloads were not selected as the step result.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `tests/test_promptbranch_version.py`
- project control-surface docs

## Behavior changes

- `--run-all-tests` summary parsing now scans the full raw log for multi-line JSON objects, not only compact one-line JSON.
- Pretty-printed live command payloads preceded by browser/shell log text are now eligible for ranking.
- Nested helper/schema/profile objects remain lower-ranked than real command result payloads.
- Successful `live_project_ensure`, `ask_live`, `visual_artifact_roundtrip`, and `release_live` payloads should no longer be misreported as failed only because the JSON was pretty-printed in a noisy log.

## Scope not advanced

This repair does not advance the `v0.1.91` normal slice. It preserves `v0.1.91.1` ask-live retry recovery, evidence reuse, localhost cooldown audit, live command behavior, adoption/current semantics, Project Source behavior, Project deletion freeze, loop behavior, and deployment/Kubernetes boundaries.

## Validation performed

Focused validation covered the exact failure shape: noisy mixed log text followed by pretty-printed live command JSON with nested metadata/helper objects. The regression verifies that final all-tests summary becomes `GO`, `failed_steps` is empty, and live steps are classified from the correct command payloads. Existing evidence reuse, localhost cooldown audit, version, and project-control tests were also run. Compileall, shell syntax, Artifact Guardian, artifact verify, and ZIP hygiene were run before packaging.

## No slice or line advancement

This is a repair release only. It does not open a new normal release line, does not change planned scope, and does not alter accepted/current semantics.

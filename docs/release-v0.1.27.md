# Release v0.1.27 — Baseline-status next-development handoff

## Purpose

`v0.1.27` is the first normal focused-development slice after adopting `v0.1.26` as the current baseline. It keeps runtime behavior unchanged and improves the post-adoption operator handoff.

## Scope

`pb release baseline-status` is a post-adoption verifier. After adoption it already proves that runtime, adopted source, adopted artifact, and registry state align. This release adds the same next-development handoff fields to baseline-status so the operator can continue from the verified baseline without switching commands just to discover the next artifact name.

New baseline-status JSON fields:

```text
next_development_base_version
next_development_artifact
next_development_status_guide_after_build
next_development_checkpoint_after_build
```

Non-JSON baseline-status output now also prints:

```text
next_development_artifact=
next_development_status_guide_after_build=
next_development_checkpoint_after_build=
```

## Why this matters

After a full-test/adoption checkpoint, the operator normally runs:

```bash
pb release baseline-status --version v0.1.26 --json
```

That command should not only answer whether the baseline is aligned. It should also show the exact next candidate artifact and the read-only commands to run after the next candidate is built.

For an adopted `v0.1.26` baseline, the handoff points to:

```text
chatgpt_claudecode_workflow-2_v0.1.27.zip
```

and after the candidate is built:

```bash
pb release status-guide --artifact ./chatgpt_claudecode_workflow-2_v0.1.27.zip --version v0.1.27 --target-version v0.1.27 --json
pb release checkpoint --artifact ./chatgpt_claudecode_workflow-2_v0.1.27.zip --version v0.1.27 --target-version v0.1.27 --mode continue --json
```

## Files changed

```text
promptbranch_cli.py
tests/test_promptbranch_cli.py
VERSION
pyproject.toml
promptbranch_version.py
docker-compose.chatgpt-service.yml
docs/design/promptbranch-mvp-living-design.md
docs/design/promptbranch-mvp-living-design.drawio
docs/release-v0.1.27.md
```

## Validation

Expected focused validation:

```bash
python3 -m compileall -q .
python3 -m pytest -q \
  tests/test_promptbranch_cli.py::test_release_baseline_status_verifies_post_adoption_alignment \
  tests/test_promptbranch_cli.py::test_release_status_guide_selects_baseline_status_for_adopted_current \
  tests/test_promptbranch_cli.py::test_release_status_guide_selects_baseline_status_for_current_runtime_without_artifact \
  tests/test_promptbranch_cli.py::test_release_status_guide_plain_output_includes_next_development_handoff \
  tests/test_promptbranch_cli.py::test_release_checkpoint_plain_output_includes_next_development_handoff
pb test smoke --json --path .
pb release docs-status --version v0.1.27 --json
pb release config --json
pb release install --artifact ./chatgpt_claudecode_workflow-2_v0.1.27.zip --version v0.1.27 --target-version v0.1.27 --plan --json
pb release lifecycle --artifact ./chatgpt_claudecode_workflow-2_v0.1.27.zip --version v0.1.27 --target-version v0.1.27 --plan --json
```

## Non-goals

This release does not:

```text
- change ask/reply runtime behavior
- run or require adoption
- upload Project Sources
- introduce write-capable agent behavior
- broaden full lifecycle mechanics
```

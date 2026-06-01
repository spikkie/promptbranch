# Release v0.1.3 — read-only lifecycle config parsing hardening

Baseline: `chatgpt_claudecode_workflow-2_v0.1.2.zip`
Release version: `v0.1.3`
Release type: normal

## Purpose

Harden the read-only lifecycle configuration parser and validator before adding any install, source-add, adoption, or Git mutation to the native release lifecycle.

## Scope

- Keep `pb release config --json` read-only.
- Parse `.promptbranch-release.yml` without executing hooks.
- Reject duplicate YAML keys instead of silently accepting overridden lifecycle policy.
- Validate artifact `prefix` and `suffix` as safe filename tokens, not paths or templates.
- Validate hook names as safe identifiers.
- Emit a structured `config_summary` with artifact filename pattern, preserve paths, unsafe paths, hook names, placeholders, and read-only contract flags.
- Align the repository lifecycle config artifact prefix with the accepted `chatgpt_claudecode_workflow-2_` artifact line.

## Non-goals

- No artifact install.
- No Project Source add or mutation.
- No candidate migration.
- No adoption.
- No Git commit or push automation.
- No lifecycle phase advancement beyond read-only config parsing.

## Validation

Performed during artifact creation:

```bash
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_config'
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m compileall -q .
pb release config --repo-path . --json
```

## Baseline continuity

This release is built from `chatgpt_claudecode_workflow-2_v0.1.2.zip` and preserves the accepted `chatgpt_claudecode_workflow-2` artifact line.

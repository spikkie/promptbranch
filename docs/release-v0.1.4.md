# Release v0.1.4 — Read-only release install and lifecycle planning

Base release: `chatgpt_claudecode_workflow-2_v0.1.3.zip`

Release type: normal development candidate

## Scope

This release hardens the read-only native lifecycle planning surface.

Implemented:

- `pb release install --artifact ZIP --version VERSION --plan --json` now reports a richer read-only install target plan.
- The install plan classifies candidate ZIP entries into files that would be added, files that would be replaced, parent directories that would be created, and configured preserve-path status.
- The install plan exposes artifact layout checks, unsafe-entry counts, hygiene counts, nested-ZIP counts, and wrapper-folder state from the ZIP verifier.
- The install plan includes a read-only baseline comparison against the local artifact registry current baseline.
- `pb release lifecycle --plan --json` embeds the read-only install plan and baseline comparison in `lifecycle_planning`.
- Lifecycle plan phase rows no longer claim that any phase will execute while `--plan` is active.

## Explicit non-scope

Not implemented in this slice:

- no repo extraction
- no Project Source add/sync
- no candidate test execution
- no artifact adoption
- no policy sync
- no Git commit or push
- no browser automation expansion

## Validation performed

```bash
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_install_plan or release_lifecycle_plan or release_config or release_doctor'
python3 -m pytest -q tests/test_cli_parser.py -k 'release_install or release_lifecycle or release_config'
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m compileall -q .
python3 promptbranch_cli.py release config --repo-path . --json
python3 promptbranch_cli.py release install --artifact ./chatgpt_claudecode_workflow-2_v0.1.4.zip --version v0.1.4 --plan --json
python3 promptbranch_cli.py release lifecycle --artifact ./chatgpt_claudecode_workflow-2_v0.1.4.zip --version v0.1.4 --target-version v0.1.4 --plan --json
```

Docker Compose, live browser checks, Project Source mutation, and full release-control were not run in the build environment.

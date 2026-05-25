# Repair v0.0.276.3

## Base release

`chatgpt_claudecode_workflow_v0.0.276.2.zip`

## Repair version

`v0.0.276.3`

## Reason

Operators needed a hands-on manual that shows how to process the main Promptbranch use cases by manually typing `pb` or `promptbranch` commands, instead of relying only on lifecycle wrapper scripts.

This is a documentation-only repair on top of `v0.0.276.2`.

## Files changed

- `docs/howto/16-manual-pb-command-use-cases.md`
- `docs/howto/README.md`
- version metadata surfaces (`VERSION`, `pyproject.toml`, `promptbranch_version.py`, `promptbranch.egg-info/PKG-INFO`)
- version-current tests
- `promptbranch.egg-info/SOURCES.txt`
- `docs/repair-v0.0.276.3.md`

## Repair behavior

No runtime behavior changed.

The new manual documents manual commands for:

- command hygiene and environment checks
- local health and login checks
- workspace/project selection
- task/chat selection and transcript inspection
- plain asks, protocol asks, and strict release-candidate asks
- project source listing, adding, removing, and syncing
- artifact current/list/verify/release/adopt
- ask/reply artifact intake
- candidate status, next action, run, test, and accept flows
- release doctor/config/install/test/adopt/lifecycle/policy-sync/git-sync flows
- final Artifact Intake MVP finalizer usage
- smoke/browser/agent/full testing
- local agent, MCP, Ollama-proposal, and skill commands
- debug and legacy alias mapping
- end-to-end manual workflows and evidence capture

## Validation performed

- Markdown/manual presence checks.
- Shell syntax check for release/finalizer shell scripts.
- Python compile check for project Python files.
- Focused pytest checks for shell-script contracts and version surfaces.
- ZIP layout and hygiene verification after packaging.

## Scope confirmation

No slice or line was advanced. This repair does not change candidate intake, download, verification, migration, candidate-test, adoption, Project Source mutation, MCP behavior, skill behavior, release planning, browser automation behavior, or release lifecycle semantics. It only adds a hands-on PB command-use manual and updates version metadata for the repair artifact.

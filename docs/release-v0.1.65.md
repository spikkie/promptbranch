# Release v0.1.65 — Release lifecycle config contract guard

Release: `v0.1.65`

Target artifact: `chatgpt_claudecode_workflow-2_v0.1.65.zip`

Baseline: `chatgpt_claudecode_workflow-2_v0.1.64.zip`

## Scope

`v0.1.65` moves the release line from documentation-site governance back toward Promptbranch-native release lifecycle governance. It hardens the repo-local `.promptbranch-release.yml` contract and the read-only `pb release config --json` status command.

## Added / refreshed

- `.promptbranch-release.yml` now declares the artifact naming policy, version prefix, preserved local paths, Git unsafe paths, and configured lifecycle hooks as repo-relative data.
- `pb release config --json` reports a read-only lifecycle config contract with top-level `artifact`, `install`, `git`, `hooks`, and `read_only_contract` summaries.
- Hook command validation rejects embedded absolute or home-relative local machine paths.
- Focused tests cover valid config reporting, version-prefix summary, hook summaries, and unsafe hook command rejection.

## Explicit non-goals

This release does not execute lifecycle hooks, install ZIPs, upload Project Sources, adopt artifacts, update Promptbranch artifact/source state, commit Git changes, or push to Git remotes.

## Focused validation

```bash
python3 -m pytest -q tests/test_promptbranch_release_config.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_config or release_docs_status'
python3 promptbranch_cli.py release config --json | python3 -m json.tool
python3 promptbranch_cli.py release docs-status --version v0.1.65 --json | python3 -m json.tool
python3 -m compileall -q .
```

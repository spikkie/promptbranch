# Release v0.1.66 — Release doctor config-aware candidate ZIP precheck

Release: `v0.1.66`

Target artifact: `chatgpt_claudecode_workflow-2_v0.1.66.zip`

Baseline: `chatgpt_claudecode_workflow-2_v0.1.65.zip`

## Scope

`v0.1.66` continues the Promptbranch-native release lifecycle line by making `pb release doctor` consume the repo-local `.promptbranch-release.yml` contract when inspecting a candidate ZIP.

The release doctor remains read-only. It validates and classifies a candidate artifact, but it does not install the ZIP, upload Project Sources, execute lifecycle hooks, adopt artifacts, update artifact/source state, commit, or push.

## Added / refreshed

- `pb release doctor --artifact ZIP --version VERSION --json` now reports a `release_config` summary derived from `.promptbranch-release.yml`.
- `pb release doctor` now reports a stable `candidate_artifact` section for candidate ZIP prechecks.
- Candidate ZIP checks include filename/config matching, VERSION consistency, ZIP readability, root-layout hygiene, generated/cache exclusion, nested-ZIP detection, and accepted-baseline continuity.
- Candidate defects are reported with explicit warning/blocker codes such as `candidate_artifact_wrong_filename`, `candidate_artifact_wrong_version`, `candidate_artifact_hygiene_failed`, and `candidate_artifact_baseline_mismatch`.
- Focused tests cover config-aware successful candidate inspection and config-based filename rejection.

## Explicit non-goals

This release does not execute lifecycle hooks, install ZIPs, upload Project Sources, adopt artifacts, update Promptbranch artifact/source state, commit Git changes, or push to Git remotes.

## Focused validation

```bash
python3 -m pytest -q tests/test_promptbranch_release_config.py
python3 -m pytest -q tests/test_promptbranch_release_doctor.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_config or release_doctor or release_docs_status'
python3 promptbranch_cli.py release config --json | python3 -m json.tool
python3 promptbranch_cli.py release doctor --version v0.1.66 --artifact ./chatgpt_claudecode_workflow-2_v0.1.66.zip --skip-service-health --skip-project-sources --json | python3 -m json.tool
python3 promptbranch_cli.py release docs-status --version v0.1.66 --json | python3 -m json.tool
python3 -m compileall -q .
```

Expected release doctor candidate result:

```text
candidate_artifact.ok=true
candidate_artifact.filename_matches_config=true
candidate_artifact.version_matches_requested=true
candidate_artifact.zip_opens=true
candidate_artifact.zip_root_is_repo_contents=true
candidate_artifact.version_file_value=v0.1.66
candidate_artifact.hygiene_ok=true
candidate_artifact.baseline_continuity.ok=true
read_only=true
mutating_actions_executed=false
```

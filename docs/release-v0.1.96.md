# Release v0.1.96 — Project Source generated ZIP retention guard

## Type

Normal candidate.

## Baseline

User-pinned source baseline: `chatgpt_claudecode_workflow-2_v0.1.95.zip`.

`v0.1.95` adoption/current evidence was not available in this build environment, so this artifact is a candidate built from the explicit ZIP baseline supplied for the slice.

## Objective

Prevent ChatGPT Project Source exhaustion when one Project services multiple repositories by limiting automatic generated release ZIP retention to the latest five sources per release-family/repository.

## Changes

- Added same-family generated release ZIP retention selection for Project Source upload capacity pruning.
- Kept the global ChatGPT Project Sources limit at 25 resources.
- Before uploading a generated release ZIP, old same-family generated release ZIPs are pruned so the family remains at five entries after the upload.
- If the global 25-source limit is reached, automatic pruning still only removes same-family generated release ZIPs.
- Documentation files, non-ZIP Project Sources, and generated ZIPs from other repositories are not selected for automatic deletion.
- Existing exact-remove identity-drift handling remains fail-closed with operator review and no looser retry after drift.

## Out of scope

- No loop command execution changes.
- No file mutation by the loop engine.
- No Kubernetes, deployment, Helm, Docker runtime, or service behavior changes.
- No artifact adoption/current behavior changes.
- No ChatGPT Project deletion behavior changes.
- No automatic deletion of documentation or non-generated Project Sources.

## Validation performed

Local candidate validation performed:

- `pytest -q tests/test_project_source_capabilities.py tests/test_promptbranch_version.py tests/test_project_control_surface.py tests/test_artifact_guardian.py` — 90 passed.
- `python3 -m compileall -q .` — passed.
- `find . -name '*.sh' ... | xargs bash -n` — passed.
- `python3 promptbranch_artifact_guardian.py --repo . --zip /mnt/data/chatgpt_claudecode_workflow-2_v0.1.96.zip --version v0.1.96 --policy .artifact-guardian.yml --json` — guard passed.
- ZIP hygiene check — no wrapper folder, no cache/generated/local-env files detected, `VERSION=v0.1.96`, `.gitignore` present.
- Package import smoke from ZIP with `pip install --no-deps --no-build-isolation --target` — imported `promptbranch_version` and `promptbranch_browser_auth.client`; version reported `v0.1.96`.

Full release-control/adoption was not performed by this candidate build.

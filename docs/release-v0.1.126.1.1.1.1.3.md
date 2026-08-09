# v0.1.126.1.1.1.1.3 release candidate

- Type: repair candidate
- Base candidate: `v0.1.126.1.1.1.1.2`
- Accepted/current baseline: `v0.1.125.3.4.2`
- Artifact: `chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.3.zip`
- Scope advancement: none

## Defect

Live `v0.1.126.1.1.1.1.2` validation passed the exact candidate full suite 53/53 and materialized the tested worktree, but the explicitly requested Git publication phase failed before commit. The state machine exported `PROMPTBRANCH_RELEASE_VALIDATION_PYTHON` for the candidate pipx interpreter; `.promptbranch-release.json` did not allow that variable through its sanitized execution environment, so `python3` resolved through an unrelated ambient virtualenv with pytest 8.4.2 instead of the required candidate pytest 9.0.2. All 17 required release groups were therefore skipped by runner preflight.

## Repair

- Add `PROMPTBRANCH_RELEASE_VALIDATION_PYTHON` to the release-contract environment allowlist.
- Preserve the existing state-machine candidate-interpreter selection.
- Add regression coverage that poisons ambient `PATH` while requiring the explicit candidate validation-Python authority to survive release-contract sanitization.
- Do not add compatibility fallback to ambient Python.

## Acceptance

Construction validation is necessary but not sufficient. Acceptance still requires the canonical live lifecycle through `FINAL_VERIFIED`, including publication, adoption, exact production promotion, and final independent verification.

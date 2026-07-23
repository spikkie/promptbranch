# Promptbranch plan — v0.1.108.1

## Slice

`v0.1.108.1 — Project Source staged-overwrite and removal-proof reliability`

## Authority and baseline

- Accepted/current authority: `v0.1.107`
- Accepted/current artifact: `chatgpt_claudecode_workflow-2_v0.1.107.zip`
- Failed normal candidate being repaired: `v0.1.108`
- Repair artifact: `chatgpt_claudecode_workflow-2_v0.1.108.1.zip`
- Release mode: repair; scope advancement forbidden.

## Failure evidence

Two strict v0.1.108 runs refused adoption. The later run removed rate limiting as the explanation and reproduced:

1. `full_direct`: staged replacement selected upload-new/verify/delete-old, but both relevant upload requests failed, no commit or processing stream appeared, and no backing identity was created.
2. `full_localhost`: replacement succeeded, but deletion could not prove stable disappearance from the authoritative Project Sources surface.

## Acceptance scope

### Staged overwrite

- Prove the file input was found and submission was attempted.
- Observe backend request start separately from commit and processing completion.
- Preserve redacted request-failure diagnostics.
- Evaluate retry eligibility from four required facts: no commit, no processing stream, no backing identity, original source still verified.
- Retry the staged file upload at most once with a fresh collision-free family member.
- Never delete the old source before the replacement assigned filename, processed-file ID, and Library metadata ID are verified.

### Removal proof

- Refresh the authoritative Project Sources surface after the delete action.
- Require two stable observations.
- Return `verified_absent`, `still_present`, or `surface_unresolved`.
- Treat only `verified_absent` as success.

### Verification

- Add deterministic unit/integration regression tests.
- Add `pb test project-source-file-reliability` with independent overwrite and removal scenarios.
- Run separate direct and localhost focused projects during development.
- Preserve the complete release gate: both `full_direct` and `full_localhost` must pass before adoption.

## Out of scope

Execution-envelope redesign, correction execution, general retry frameworks, Project deletion, deployment, Kubernetes mutation, generic write authority, remote Project Settings mutation, and every implementation item belonging to v0.1.109.

## Next planned slice after acceptance

`v0.1.109 — PROJECT_SETTINGS.md, AGENTS.md and project authority-graph definition`

It remains planned only. No `PROJECT_SETTINGS.md`, `AGENTS.md`, authority-graph schema, drift validator, or remote settings operation is implemented by this repair.

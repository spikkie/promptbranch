# Promptbranch Release Pipeline

## Commands

Read-only planning:

```bash
pb release pipeline plan --repo-path . --confirm-version "$(tr -d '\r\n' < VERSION)" --json
```

Explicit full apply:

```bash
pb release pipeline apply \
  --repo-path . \
  --confirm-version "$(tr -d '\r\n' < VERSION)" \
  --stage-all \
  --commit \
  --push \
  --publish \
  --adopt \
  --verify-current \
  --json
```

## Phase order

1. repository-owned validation;
2. repository-owned tests;
3. artifact build;
4. artifact verification;
5. guarded release commit;
6. same-run push;
7. committed-tree rebuild and verification;
8. Project Source publication;
9. evidence-bound artifact adoption;
10. accepted/current verification.

## Dependency rules

- `--commit` requires `--stage-all`;
- `--push` requires `--commit`;
- `--publish` requires `--push`;
- `--adopt` requires `--publish`;
- `--verify-current` requires `--adopt`.

The tracked `.promptbranch-release.json` remains the repository-owned lifecycle contract. Promptbranch owns orchestration, evidence, publication, adoption and final verification; the repository owns validation, tests, packaging and domain gates.

## Exact evidence binding

Publication must return persistent source evidence containing the backend-assigned filename, processed file identifier and library metadata object identifier. Adoption consumes that exact evidence file. Accepted/current verification fails closed unless all of the following agree:

- the selected repository state artifact reference and version;
- the exact assigned Project Source filename from the same run;
- the Project Source version;
- the registry current filename, version, and exact canonical SHA-256;
- registry-current/state-artifact consistency;
- state-source/state-artifact consistency.

A matching version with a different indexed Project Source filename is not sufficient.

## Repository-owned deterministic gate

The tracked release contract calls `scripts/run-release-validation-groups.py`. This runs the mandatory deterministic release groups declared by Promptbranch instead of collecting the entire repository test tree, which also contains network, service, compatibility-wrapper and browser suites that belong to separate strict/live profiles.

## Evidence import and recovery

Read-only import planning:

```bash
pb release pipeline import \
  --repo-path . \
  --confirm-version "$(tr -d '\\r\\n' < VERSION)" \
  --evidence .pb_profile/release_runs/pipeline/<run>/release-pipeline-checkpoint.json \
  --json
```

Guarded resume:

```bash
pb release pipeline resume \
  --repo-path . \
  --confirm-version "$(tr -d '\\r\\n' < VERSION)" \
  --evidence .pb_profile/release_runs/pipeline/<run>/release-pipeline-checkpoint.json \
  --stage-all --commit --push --publish --adopt --verify-current \
  --json
```

Every run atomically writes a crash-consistent checkpoint after each phase. Import validates repository, version, artifact, contract, Git and source identity without mutation. Resume requires the exact imported mutation envelope, re-runs safe local gates, and skips only successful mutation phases whose immutable evidence still matches. Successful adoption/current evidence is never replayed merely because it was imported; authoritative current identity must reconfirm it.

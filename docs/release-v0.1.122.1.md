# Release v0.1.122.1 — MVP proof finalizer fail-closed evidence repair

## Purpose

Repair the post-adoption MVP proof-cycle tooling exposed after accepted/current `v0.1.122`. The strict release lifecycle itself passed 10/10 and adopted `v0.1.122`, but proof finalization failed because the evaluator did not read project-level `repos.<repo-id>` current output, did not bind every evidence source to the candidate SHA-256, and the shell wrapper could continue after a failed verifier and print a false `verified` message.

## Changes

- Parse accepted/current identity from the real `pb artifact current --json` project shape at `repos.<repo-id>`.
- Require exact version, filename, and SHA-256 binding across:
  - the canonical candidate bytes;
  - artifact-intake download/verification evidence;
  - adoption evidence;
  - accepted/current registry evidence.
- Add a read-only proof preflight before any continuation Ask.
- Stop before creating continuation request/run evidence when intake, release, adoption, current identity, or SHA-256 evidence is incomplete or conflicting.
- Run the finalizer with `set -Eeuo pipefail`.
- Preserve the verifier exit code and print `verified` only after the complete proof result is `mvp_proof_cycle_passed`.
- Add executable regressions proving:
  - project-level current parsing succeeds;
  - intake/adoption/current SHA mismatch fails closed;
  - invalid intake never invokes `pb ask`;
  - a failed full proof never exits zero or prints `MVP proof cycle ... verified`.
- Include the proof regression module in the mandatory `release_pipeline` validation group.

## Safety

This is a scope-neutral repair. It adds no platform mutation authority and does not count as a normal MVP proof cycle. Accepted/current remains `v0.1.122` until strict host validation adopts this repair.

The consecutive normal-release proof sequence is reset:

```text
v0.1.123 → canonical MVP proof cycle 1
v0.1.124 → canonical MVP proof cycle 2 and final MVP verdict
```

## Operator commands

Install candidate:

```bash
pipx install --force ./chatgpt_claudecode_workflow-2_v0.1.122.1.zip
pb --version
```

Run deterministic validation:

```bash
python3 scripts/run-release-validation-groups.py --repo . --json
```

Verify the artifact:

```bash
sha256sum chatgpt_claudecode_workflow-2_v0.1.122.1.zip
unzip -t chatgpt_claudecode_workflow-2_v0.1.122.1.zip
python3 promptbranch_artifact_guardian.py \
  --repo . \
  --zip chatgpt_claudecode_workflow-2_v0.1.122.1.zip \
  --version v0.1.122.1 \
  --json
```

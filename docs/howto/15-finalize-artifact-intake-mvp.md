# Finalize the Artifact Intake MVP manually

## Purpose

`scripts/finalize-artifact-intake-mvp.sh` is the explicit operator gate for proving the final Artifact Intake MVP lifecycle.

It is intentionally a thin wrapper around `scripts/post-release-validation.sh`. The wrapper does not add a new artifact lifecycle implementation. It makes the strict MVP-finalization mode repeatable by forcing these delegated flags:

```bash
--adopt-if-accepted
--complete-candidate-mvp
```

That means the wrapper can execute existing allowlisted candidate lifecycle steps through:

```bash
pb artifact candidate-run \
  --execute-until-blocked \
  --require-complete \
  --json
```

The key invariant is that no new mutation path is created here. Mutation remains limited to the already implemented post-release validation, candidate-run, artifact-adopt, and Project Source primitives.

## Critical safety assessment

### What may fail

- The selected candidate ZIP may not exist in the repository root as `chatgpt_claudecode_workflow_<version>.zip`.
- The ZIP may not be visible as a ChatGPT Project Source, so `pb artifact adopt --from-project-source` can fail.
- `pb artifact current --json` may still point to the previous accepted baseline before adoption. That mismatch is diagnostic unless strict adopted-baseline validation is requested.
- The protocol smoke may fail because of ChatGPT browser/service/network state, bearer-token state, rate limits, or a malformed reply envelope.
- The post-adoption protocol smoke intentionally returns `no_artifact` in the default mode; without `--require-real-candidate-mvp`, a clean no-artifact terminal precondition is accepted as a non-mutating terminal state. With `--require-real-candidate-mvp`, the protocol step switches to `pb ask-release` and expects a ZIP candidate for `--target-version`.
- `pb test full --json` can be long-running and environment-dependent.
- ZIP hygiene fails if generated logs, nested ZIPs, `.pb_profile/`, caches, wrapper folders, or Python bytecode are packaged.

### Hidden assumptions

- `promptbranch` or `pb` resolves to the candidate runtime you are validating.
- The local working tree is the installed contents of the candidate ZIP.
- `.pb_profile/` contains valid artifact/source state for the current project.
- The current ChatGPT workspace/task context is suitable for a protocol smoke ask.
- Project Source upload/adoption preconditions were completed before finalization.

### Important boundary

Do not use this script as a generic release builder. It is a final validation/adoption gate for a candidate that already exists.

## Command synopsis

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v0.0.276.2 \
  --target-version v0.0.277
```

Recommended strict real-candidate form:

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v0.0.276.2 \
  --target-version v0.0.277 \
  --require-real-candidate-mvp
```

From `v0.0.276.5`, this strict form performs an artifact-producing `pb ask-release` for `--target-version`, then runs `pb artifact intake --from-last-answer --download --verify` for the expected target ZIP. The finalizer fails unless explicit download and verification proof exists. An already-adopted baseline proof from `pb artifact candidate-run` is acceptable only when it is paired with the explicit artifact-intake download/verify proof.

Bounded execution controls:

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v0.0.276.2 \
  --target-version v0.0.277 \
  --candidate-mvp-max-steps 4 \
  --candidate-run-step-timeout 3600
```

Use `--pb-cmd promptbranch` to bypass a shell alias that prints extra text:

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v0.0.276.2 \
  --target-version v0.0.277 \
  --pb-cmd promptbranch
```

## Options accepted by the wrapper

The wrapper forwards these options to `scripts/post-release-validation.sh`:

```text
-v, --version VERSION
--target-version VERSION
--pb-cmd COMMAND
--release-log-dir DIR
--test-timeout SEC
--candidate-mvp-max-steps N
--candidate-run-step-timeout SEC
--skip-protocol-smoke
--skip-artifact-intake
--skip-tests
--skip-zip-hygiene
--require-real-candidate-mvp
```

The wrapper itself supplies these options and rejects them if you pass them directly:

```text
--adopt-if-accepted
--complete-candidate-mvp
--require-candidate-mvp-complete
```

The wrapper also rejects these conflicting options:

```text
--skip-candidate-run
--require-adopted-baseline
```

Reason: final MVP completion validation must be allowed to run candidate-run, and pre-adoption current-baseline mismatch is expected until adoption completes.

## Environment variables

### `POST_RELEASE_VALIDATION_SCRIPT`

Overrides the delegated validation script path. This is mainly for tests and wrapper-contract validation.

```bash
POST_RELEASE_VALIDATION_SCRIPT=/tmp/fake-post-release-validation.sh \
  scripts/finalize-artifact-intake-mvp.sh \
    --version v9.9.9 \
    --target-version v9.9.10
```

### `PB_CMD`

Inherited by `scripts/post-release-validation.sh` when `--pb-cmd` is not supplied.

```bash
PB_CMD=promptbranch \
  scripts/finalize-artifact-intake-mvp.sh \
    --version v0.0.276.2 \
    --target-version v0.0.277
```

### Timeout defaults

The delegated script also reads these timeout defaults:

```text
PROMPTBRANCH_TEST_TIMEOUT_SECONDS
PROMPTBRANCH_PROTOCOL_TIMEOUT_SECONDS
PROMPTBRANCH_PROTOCOL_FRESH_TURN_TIMEOUT_SECONDS
PROMPTBRANCH_PROTOCOL_FRESH_TURN_POLL_SECONDS
PROMPTBRANCH_CANDIDATE_MVP_MAX_STEPS
PROMPTBRANCH_CANDIDATE_RUN_STEP_TIMEOUT_SECONDS
```

Prefer explicit CLI flags for release evidence, because they are visible in the session log.

## What the wrapper does

The wrapper itself performs only these operations:

1. Resolves its own directory.
2. Resolves `scripts/post-release-validation.sh`, or `POST_RELEASE_VALIDATION_SCRIPT` when set.
3. Parses and forwards the allowlisted options.
4. Rejects flags that would duplicate or conflict with finalization semantics.
5. Verifies that the delegated script is executable.
6. Calls the delegated script with all forwarded options plus:

```bash
--adopt-if-accepted --complete-candidate-mvp
```

7. Returns the delegated script exit code.

## What the delegated validation does

With the forced finalizer flags, `scripts/post-release-validation.sh` performs this high-level sequence:

1. Runs `pb artifact current --json`.
2. Runs a semantic current-baseline check against `--version`.
   - Before adoption, mismatch is diagnostic unless strict adopted-baseline validation is requested.
3. Defers protocol smoke, artifact-intake dry-run, and candidate-run until after adoption.
4. Runs `pb test full --json` unless `--skip-tests` is supplied.
5. Runs `pb test report <full-log> --json` unless `--skip-tests` is supplied.
6. Checks ZIP hygiene for `chatgpt_claudecode_workflow_<version>.zip` unless `--skip-zip-hygiene` is supplied.
7. If all prior gates are green, runs:

```bash
pb artifact adopt chatgpt_claudecode_workflow_<version>.zip \
  --from-project-source \
  --json
```

8. Re-runs `pb artifact current --json` and verifies artifact/source/runtime version alignment.
9. Runs a post-adoption protocol step. Default mode uses a `no_artifact` protocol smoke with `--from-current-baseline`; strict real-candidate mode uses `pb ask-release` to request the target ZIP artifact.
10. Runs artifact intake from the latest answer. Default mode uses dry-run only; strict real-candidate mode uses `--download --verify` for the expected target ZIP.
11. Runs final candidate-run completion validation:

```bash
pb artifact candidate-run \
  --execute-until-blocked \
  --max-steps <N> \
  --step-timeout <SEC> \
  --require-complete \
  --version <version> \
  --json
```

12. Runs `pb release lifecycle-status --version <version> --target-version <target> --repo-path . --json`.
13. Writes a structured summary under `.pb_profile/release_logs/<version>/`.

## Manual preflight before running finalization

Run these checks before the finalizer. They reduce ambiguity when the finalizer fails.

### 1. Confirm runtime and version metadata

```bash
cat VERSION
promptbranch version
python3 - <<'PY'
import promptbranch_version
print(promptbranch_version.VERSION_TAG)
PY
```

Expected: all should match the candidate version you are finalizing.

### 2. Confirm the candidate ZIP exists

```bash
ls -l chatgpt_claudecode_workflow_v0.0.276.2.zip
unzip -p chatgpt_claudecode_workflow_v0.0.276.2.zip VERSION
```

Expected: `VERSION` inside the ZIP equals `v0.0.276.2`.

### 3. Confirm ZIP root layout

```bash
python3 - <<'PY'
import zipfile
from pathlib import Path
zip_path = Path('chatgpt_claudecode_workflow_v0.0.276.2.zip')
with zipfile.ZipFile(zip_path) as zf:
    names = [n for n in zf.namelist() if n.strip('/')]
roots = sorted({n.split('/')[0] for n in names})
wrapper = len(roots) == 1 and all('/' in n for n in names)
print({'entry_count': len(names), 'wrapper_folder': wrapper, 'sample_roots': roots[:20]})
PY
```

Expected: `wrapper_folder` is `False`.

### 4. Confirm release hygiene

```bash
python3 - <<'PY'
import zipfile
from pathlib import Path
zip_path = Path('chatgpt_claudecode_workflow_v0.0.276.2.zip')
bad = []
patterns = ('.pb_profile/', '__pycache__/', '.pytest_cache/', '.mypy_cache/', '.ruff_cache/')
suffixes = ('.pyc', '.pyo', '.log', '.tar.gz')
with zipfile.ZipFile(zip_path) as zf:
    for name in zf.namelist():
        stripped = name.strip('/')
        if any(stripped == p.strip('/') or stripped.startswith(p) for p in patterns):
            bad.append(name)
        elif any(stripped.endswith(s) for s in suffixes):
            bad.append(name)
        elif stripped.endswith('.zip'):
            bad.append(name)
print({'bad_entry_count': len(bad), 'bad_entries': bad[:50]})
raise SystemExit(0 if not bad else 1)
PY
```

Expected: `bad_entry_count` is `0`.

### 5. Confirm current artifact/source state

```bash
promptbranch artifact current --json | python3 -m json.tool
```

Before adoption, it is acceptable for this to show the previous accepted baseline. After finalization, artifact/source/runtime/current registry fields must match the finalized version.

### 6. Confirm source visibility

```bash
promptbranch src list --json | python3 -m json.tool
```

Expected: exactly one Project Source entry should correspond to the candidate ZIP before adoption from Project Source.

## Manual wrapper-contract tests

These tests validate `scripts/finalize-artifact-intake-mvp.sh` without running a real ChatGPT/browser workflow.

### 1. Help text

```bash
scripts/finalize-artifact-intake-mvp.sh --help
```

Expected: exit `0`, usage text printed.

### 2. Delegation and forced flags

```bash
tmpdir="$(mktemp -d)"
cat > "${tmpdir}/post-release-validation.sh" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$@" > "${POST_RELEASE_CAPTURE}"
SH
chmod +x "${tmpdir}/post-release-validation.sh"

POST_RELEASE_CAPTURE="${tmpdir}/args.txt" \
POST_RELEASE_VALIDATION_SCRIPT="${tmpdir}/post-release-validation.sh" \
  scripts/finalize-artifact-intake-mvp.sh \
    --version v9.9.9 \
    --target-version v9.9.10 \
    --candidate-mvp-max-steps 6 \
    --candidate-run-step-timeout 42

cat "${tmpdir}/args.txt"
```

Expected forwarded argument suffix:

```text
--adopt-if-accepted
--complete-candidate-mvp
```

The complete argument stream should preserve the version, target version, and bounded candidate-run controls you supplied.

### 3. Conflicting flag rejection

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v9.9.9 \
  --target-version v9.9.10 \
  --skip-candidate-run
```

Expected: exit `2` with an error explaining the conflict.

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v9.9.9 \
  --target-version v9.9.10 \
  --complete-candidate-mvp
```

Expected: exit `2` because the wrapper adds that semantic itself.

### 4. Missing delegated script rejection

```bash
POST_RELEASE_VALIDATION_SCRIPT=/does/not/exist \
  scripts/finalize-artifact-intake-mvp.sh \
    --version v9.9.9 \
    --target-version v9.9.10
```

Expected: exit `2` with `post-release validation script is not executable`.

## Manual end-to-end validation

Run this only when the candidate ZIP is installed locally and already uploaded/visible as a Project Source.

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v0.0.276.2 \
  --target-version v0.0.277 \
  --pb-cmd promptbranch \
  --candidate-mvp-max-steps 4 \
  --candidate-run-step-timeout 3600 \
  --require-real-candidate-mvp
```

When debugging browser/service issues, you may temporarily isolate local gates:

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v0.0.276.2 \
  --target-version v0.0.277 \
  --pb-cmd promptbranch \
  --skip-protocol-smoke \
  --skip-artifact-intake
```

Use skip flags only for diagnostics. A final MVP acceptance run should not hide protocol or artifact-intake gates.

## Evidence files to inspect

The delegated script writes release evidence under:

```text
.pb_profile/release_logs/<version>/
```

Important files:

```text
post_release_validation.<version>.session.log
post_release_validation.<version>.summary.json
pb_artifact_current.<version>.json
pb_artifact_current.<version>.semantic.json
pb_test.full.<version>.log
pb_test.full.<version>.report.json
zip_hygiene.<version>.json
pb_artifact_adopt.<version>.json
pb_artifact_current_after_adopt.<version>.json
pb_artifact_current_after_adopt.<version>.semantic.json
pb_ask_protocol_smoke.<version>.json        # no_artifact smoke or ask-release result in strict mode
pb_artifact_intake_dry_run.<version>.json  # dry-run or download/verify result in strict mode
pb_artifact_candidate_run.<version>.json
pb_release_lifecycle_status.<version>.json
```

## How to interpret the summary

```bash
python3 -m json.tool \
  .pb_profile/release_logs/v0.0.276.2/post_release_validation.v0.0.276.2.summary.json
```

Check these fields first:

```text
ok
status
version
target_version
adopt_if_accepted
complete_candidate_mvp
steps.artifact_current.rc
steps.test_full.rc
steps.test_report.rc
steps.zip_hygiene.rc
steps.artifact_adopt.rc
steps.artifact_current_after_adopt_semantic.rc
steps.protocol_smoke.rc
steps.artifact_intake_dry_run.rc
steps.artifact_candidate_run_plan.rc
validation_classification.primary_category
validation_classification.failures
```

A healthy finalization run should have no blocking failures and should show adoption/current-baseline alignment after adoption.

For strict real-candidate validation, also inspect the artifact-intake evidence file:

```bash
python3 -m json.tool .pb_profile/release_logs/<version>/pb_artifact_intake_dry_run.<version>.json
```

Required fields:

```text
download_performed == true
verification_performed == true
```

`steps.artifact_candidate_run_plan.download_performed` may still be `false` when candidate-run proves only the already-adopted current baseline. That is acceptable only when the separate artifact-intake download/verify evidence is green.

## Failure triage

### `artifact_zip_missing`

The candidate ZIP is not in the repository root. Copy or build the expected artifact first.

### `artifact_state_diagnostic`

Usually acceptable before adoption. It means current artifact/source state still points to the previous baseline.

### `artifact_state_failure`

Not acceptable after adoption. Inspect `pb_artifact_current_after_adopt.*` and verify that artifact/source/runtime versions agree.

### `service_network_failure`

The protocol smoke likely failed in the browser/service layer. Check bearer token, local service health, browser login state, and rate limits.

### `protocol_contract_failure`

The assistant reply did not satisfy the ask/reply envelope contract. Inspect `pb_ask_protocol_smoke.<version>.json`.

### `operator_precondition_failure`

Usually means no real selected artifact candidate existed, or `--require-real-candidate-mvp` made a no-artifact terminal state a hard failure. In strict mode, inspect `pb_ask_protocol_smoke.<version>.json` for the `ask-release` result and `pb_artifact_intake_dry_run.<version>.json` for `download_performed=true` and `verification_performed=true`.

### `artifact_candidate_lifecycle_failure`

Candidate-run did not reach the required completion proof. Inspect `pb_artifact_candidate_run.<version>.json` and run:

```bash
promptbranch artifact candidate-next --json | python3 -m json.tool
promptbranch artifact candidate-status --all --json | python3 -m json.tool
```

## Verdict rule

Treat the finalizer as passed only when:

- the command exits `0`
- the summary JSON reports a green validation status
- artifact/source/runtime current state matches `--version` after adoption
- ZIP hygiene is clean
- no skip flags were used in the acceptance run unless the reason is explicitly documented
- the next protocol ask can use `--from-current-baseline` without resolving to the old baseline

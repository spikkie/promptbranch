# Local Release Lifecycle with Manual Project Source Upload

This runbook documents how to make a local Promptbranch release when the change starts in the working tree, for example adding documentation or draw.io lifecycle diagrams, and the operator manually uploads the candidate ZIP to ChatGPT Project Sources.

## Critical assessment

This workflow is intentionally conservative. A ZIP existing on disk is not an accepted release. A manually uploaded Project Source is also not enough. The release is accepted only after the candidate ZIP is verified, the Project Source is visible, tests are green, and Promptbranch artifact state is adopted and re-read.

Main failure modes:

- building from a stale baseline;
- packaging uncommitted or generated local state;
- uploading a ZIP that was not verified;
- assuming a UI upload persisted without checking `pb src list`;
- adopting before the test/report gate is green;
- changing `.promptbranch-project.json` to the new baseline before adoption.

## Version policy

Use a normal release version for new documentation or lifecycle content.

Example:

```bash
BASELINE_VERSION=v0.0.277
TARGET_VERSION=v0.0.278
ARTIFACT=chatgpt_claudecode_workflow_v0.0.278.zip
```

Use a repair version such as `v0.0.277.1` only when correcting a defect in the already-intended `v0.0.277` release. Do not use a repair release merely because the change is small.

## 1. Confirm the accepted baseline

```bash
pb artifact current --json | python3 -m json.tool
cat VERSION
git status --short
```

Expected:

```text
VERSION = v0.0.277
Promptbranch current artifact/source = chatgpt_claudecode_workflow_v0.0.277.zip
working tree is clean, or only expected local files are present
```

Stop if Promptbranch current still points to an older accepted source.

## 2. Create a release branch

```bash
git switch -c docs/pb-lifecycle-v0.0.278
```

## 3. Make the local change

For the lifecycle diagram example:

```bash
mkdir -p docs/diagrams/promptbranch-lifecycle
cp ~/Downloads/promptbranch_lifecycle_commands.drawio docs/diagrams/promptbranch-lifecycle/
cp ~/Downloads/promptbranch_lifecycle_commands.png docs/diagrams/promptbranch-lifecycle/
cp ~/Downloads/promptbranch_lifecycle_commands.svg docs/diagrams/promptbranch-lifecycle/
```

Add or update documentation under `docs/howto/` or `docs/diagrams/` using repo-relative paths only.

## 4. Bump version metadata

```bash
printf 'v0.0.278\n' > VERSION
```

Also update package/runtime version metadata when applicable:

```text
pyproject.toml
promptbranch_version.py
docker-compose.chatgpt-service.yml
```

Do not update accepted baseline policy to the new version before adoption. The new artifact becomes accepted only after the test/adopt gate succeeds.

## 5. Review changes

```bash
git diff -- VERSION pyproject.toml promptbranch_version.py docker-compose.chatgpt-service.yml docs/
git status --short
```

Expected changes for a documentation-only release should be limited to documentation, diagrams, release notes, version metadata, and related tests.

## 6. Run local checks

At minimum:

```bash
python3 -m compileall promptbranch promptbranch_automation promptbranch_browser_auth
python3 -m pytest \
  tests/test_cli_parser.py \
  tests/test_promptbranch_cli.py \
  tests/test_promptbranch_container_api.py \
  tests/test_compose_timeout_policy.py \
  -q
```

For a full release gate, run the project’s normal release-control workflow from the candidate artifact after packaging.

## 7. Commit before packaging

```bash
git add VERSION pyproject.toml promptbranch_version.py docker-compose.chatgpt-service.yml docs tests

git commit -m "Document Promptbranch local release lifecycle"
```

Packaging from committed content makes the ZIP reproducible and avoids accidentally including scratch files.

## 8. Create the candidate ZIP

```bash
git archive --format=zip --output=chatgpt_claudecode_workflow_v0.0.278.zip HEAD
```

If the repository is not in Git, use a deterministic ZIP command that excludes generated and machine-local files:

```bash
zip -r chatgpt_claudecode_workflow_v0.0.278.zip . \
  -x '.git/*' \
  -x '.pb_profile/*' \
  -x '__pycache__/*' \
  -x '*/__pycache__/*' \
  -x '.pytest_cache/*' \
  -x '*.pyc' \
  -x '*.pyo' \
  -x '*.log' \
  -x '*.zip'
```

The ZIP root must open directly to repository contents, not to a wrapper directory.

## 9. Verify the candidate ZIP

```bash
python3 - <<'PY'
import hashlib
import pathlib
import zipfile

artifact = pathlib.Path('chatgpt_claudecode_workflow_v0.0.278.zip')
expected_version = 'v0.0.278'

with zipfile.ZipFile(artifact) as zf:
    names = zf.namelist()
    if 'VERSION' not in names:
        raise SystemExit('VERSION missing')
    version = zf.read('VERSION').decode('utf-8').strip()
    if version != expected_version:
        raise SystemExit(f'VERSION mismatch: {version} != {expected_version}')
    unsafe = [name for name in names if name.startswith('/') or '..' in pathlib.PurePosixPath(name).parts]
    if unsafe:
        raise SystemExit(f'unsafe ZIP paths: {unsafe[:10]}')
    forbidden = [
        name for name in names
        if name.startswith('.pb_profile/')
        or '/__pycache__/' in name
        or name.startswith('__pycache__/')
        or name.startswith('.pytest_cache/')
        or name.endswith(('.pyc', '.pyo', '.log', '.zip'))
    ]
    if forbidden:
        raise SystemExit(f'hygiene failure: {forbidden[:10]}')

print({
    'artifact': str(artifact),
    'size_bytes': artifact.stat().st_size,
    'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
    'verified': True,
})
PY
```

## 10. Manually upload to Project Sources

In the ChatGPT Project UI:

1. Open the target project.
2. Open Sources.
3. Upload `chatgpt_claudecode_workflow_v0.0.278.zip`.
4. If there are already 25 sources, remove the lowest-version same-family release ZIP first.
5. Do not remove unrelated project documents, design files, or logs.

Then verify from the CLI:

```bash
pb src list --json | tee pb_src_list.after_manual_upload.v0.0.278.json
```

Expected: the new ZIP appears as a Project Source.

## 11. Run the release-control test gate

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278 \
  --install-from-zip ./chatgpt_claudecode_workflow_v0.0.278.zip \
  --run-tests \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee release_control.v0.0.278.test.log
```

If green, adopt:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278 \
  --tests-only \
  --adopt-if-green \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee release_control.v0.0.278.adopt.log
```

## 12. Final verification

```bash
pb artifact current --json | python3 -m json.tool
pb src list --json | tee pb_src_list.final.v0.0.278.json
git status --short
```

Expected:

```text
artifact_version = v0.0.278
source_version   = v0.0.278
source_ref       = chatgpt_claudecode_workflow_v0.0.278.zip
```

If policy sync changes remain after adoption, commit them separately as the post-adoption release-state commit.

## Command map

| Goal | Command |
|---|---|
| Inspect current accepted baseline | `pb artifact current --json` |
| Inspect Project Sources | `pb src list --json` |
| Upload source through CLI instead of UI | `pb src add ./chatgpt_claudecode_workflow_v0.0.278.zip --json` |
| Run smoke tests | `pb test smoke --json` |
| Run full PB tests | `pb test full --json` |
| Render full test report | `pb test report <log> --json` |
| Install/test candidate | `./chatgpt_claudecode_workflow_release_control.sh --version v0.0.278 --install-from-zip ./chatgpt_claudecode_workflow_v0.0.278.zip --run-tests` |
| Guarded adoption | `./chatgpt_claudecode_workflow_release_control.sh --version v0.0.278 --tests-only --adopt-if-green` |
| Target future native lifecycle | `pb release lifecycle --artifact ./chatgpt_claudecode_workflow_v0.0.278.zip --version v0.0.278 --json` |

## Verdict

Manual Project Source upload is acceptable as an operator step, but it must remain surrounded by deterministic CLI verification. The command line remains the control plane; the UI is only the upload surface until `pb src add` / `pb release lifecycle` is trusted for this path.

# v0.1.103.10.2 — Auth-only release-control path

## Goal

Close the Bonnetjes Cloudflare validation line without enabling Project Source mutation.

## Scope

- Keep `bonnetjes-cloudflare-parity` unchanged.
- Keep `PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION` unset/disabled.
- Fix the challenge artifact exporter so a no-challenge run returns `ok=true` with `status=no_matching_artifacts`.
- Add a release-control auth-only mode:
  - `--auth-only-validation`
  - implies `--skip-source-add`
  - runs hygiene checks
  - runs `scripts/docker-bonnetjes-cloudflare-validation.sh`
  - allows `--adopt-after-validation` after the auth-only validation passes
  - adopts with `pb artifact adopt --local-only`, not `--from-project-source`

## Operator command

```bash
ver=v0.1.103.10.2
zip="$HOME/Downloads/chatgpt_claudecode_workflow-2_${ver}.zip"

timeout --foreground 10800 ./chatgpt_claudecode_workflow_release_control.sh \
  --install-from-zip "$zip" \
  --version "$ver" \
  --auth-only-validation \
  --skip-tests \
  --adopt-after-validation \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee ~/tmp/release_control.$ver.auth_only.adopt.log
```

## Expected result

- package version is installed as requested
- Bonnetjes Cloudflare validation passes
- no Project Source mutation occurs
- local artifact state/registry are adopted
- `pb artifact current --all --json` points to `v0.1.103.10.2`

## Out of scope

- Project Source mutation
- `/v1/project-sources`
- `PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION=1`

# Bonnetjes Cloudflare one-shot validation

Version: v0.1.103.10.1

This is the operator validation phase for the Docker Bonnetjes Cloudflare parity path.

The validation target is intentionally narrow:

- prove a clean manually logged-in profile clears Cloudflare inside Docker;
- prove Docker sees the session as authenticated;
- prove the ChatGPT composer is visible;
- keep Project Source mutation disabled.

It does not test Project Source mutation.

## One command after installation

Run from the repository root:

```bash
./scripts/docker-bonnetjes-cloudflare-validation.sh
```

The script opens a visible host Chrome window with a fresh profile. In that window:

1. confirm Cloudflare clears;
2. log in manually;
3. confirm the ChatGPT composer is visible;
4. close Chrome completely.

After Chrome closes, the script continues automatically and runs the Docker Bonnetjes Cloudflare parity check against the same profile mounted as `/app/profile`.

## Optional install-and-validate form

When validating a ZIP candidate from an already working tree:

```bash
./scripts/docker-bonnetjes-cloudflare-validation.sh \
  --install-artifact chatgpt_claudecode_workflow-2_v0.1.103.10.1.zip \
  --install-version v0.1.103.10.1
```

The script stores evidence under:

```text
debug_artifacts/docker-browser-parity/bonnetjes-validation/<timestamp>/
```

Important files:

```text
validation.log
bootstrap.log
cloudflare-check.log
cloudflare-summary.json
validation-summary.json
```

## Reuse an existing logged-in clean profile

```bash
./scripts/docker-bonnetjes-cloudflare-validation.sh \
  --skip-bootstrap \
  --profile-dir /absolute/path/to/.pb_profile_bonnetjes_manual_<timestamp>
```

## Pass criteria

`validation-summary.json` must report:

```json
{
  "ok": true,
  "status": "passed",
  "checks": {
    "cloudflare_cleared": true,
    "auth_ready": true,
    "logged_in": true,
    "challenge_detected": false,
    "composer_visible": true,
    "project_source_mutation_allowed": false
  }
}
```

## Safety boundaries

The script does not call:

- `/v1/project-sources`;
- `/v1/login-check`;
- any Google/login automation flow.

It uses:

- `PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity`;
- `/app/profile` inside Docker;
- a host profile bind mount via `PROMPTBRANCH_HOST_PROFILE_DIR`;
- Xvfb;
- headed Patchright Chrome;
- `CHATGPT_DISABLE_FEDCM=1`;
- `CHATGPT_FILTER_NO_SANDBOX=0`;
- `CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS=0`;
- `CHATGPT_CONVERSATION_HISTORY_REQUEST_SHIELD_MODE=disabled`.

## Cleanup

Fresh validation profiles are local state and must not be committed:

```bash
rm -rf .pb_profile_bonnetjes_manual_*
```

Profiles are excluded from Docker build context by `.dockerignore` and from Git by `.gitignore`.

## v0.1.103.10.1 closure note

`v0.1.103.10.1` keeps the `v0.1.103.10` validation flow unchanged and records it as the tested active candidate after repository hygiene cleanup. Browser profiles and debug artifacts must remain local-only state and must never enter Git history or Docker build context.

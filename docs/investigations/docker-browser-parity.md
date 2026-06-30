# Docker browser parity investigation

Status: diagnostic candidate only  
Version: `v0.1.103.1`

## Purpose

`v0.1.103.1` starts the Docker browser recovery investigation by adding a
Promptbranch Docker browser launch envelope to Promptbranch without changing release-control,
Project Source mutation, artifact adoption, or ChatGPT Project deletion behavior.

The goal is to compare the Promptbranch Docker browser path against the Docker
pattern observed in the reference Docker browser implementation:

```text
xvfb-run service process
Patchright + chrome channel
headed browser
FedCM disabled
Patchright default Docker no-sandbox behavior preserved
isolated /app/profile profile path
short bounded challenge-settle wait
```

## Controls

This slice is not a Cloudflare bypass and does not automate challenge solving.
It only makes the Docker browser runtime envelope explicit and observable.

## How to run the diagnostic

```bash
cd /home/spikkie/git/chatgpt_claudecode_workflow
./scripts/docker-browser-parity-auth-readiness.sh
```

The script writes evidence under:

```text
debug_artifacts/docker-browser-parity/<timestamp>/
```

Expected diagnostic files:

```text
healthz.json
docker-browser-runtime.json
auth-readiness.json
docker-service.log
summary.json
```

## Success signal

The Docker path is worth further investigation only if auth readiness can reach:

```json
{
  "ok": true,
  "status": "auth_preflight_ready",
  "logged_in": true,
  "auth_readiness": {
    "challenge_detected": false,
    "composer_visible": true
  }
}
```

Project Source mutation remains out of scope until this diagnostic passes.

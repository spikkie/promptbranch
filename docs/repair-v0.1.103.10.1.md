# v0.1.103.10.1 — Bonnetjes Cloudflare validation evidence and hygiene closure

Status: candidate only until Promptbranch adoption/current evidence confirms it.

## Scope

This repair release records the tested Bonnetjes Cloudflare parity phase as the current active candidate and preserves the working `v0.1.103.10` behavior:

1. the one-shot validation script remains the operator entry point;
2. the Docker browser profile remains `bonnetjes-cloudflare-parity`;
3. clean host Chrome login bootstrap remains manual and visible;
4. Docker reuses the exact same host profile only as a bind mount at `/app/profile`;
5. Project Source mutation remains disabled and out of scope.

## Validation evidence carried into this release

Operator validation on `json-orchestration-state` showed the full clean-profile path working:

- Cloudflare cleared;
- authenticated UI was visible;
- ChatGPT composer was visible;
- `logged_in=true`;
- `challenge_detected=false`;
- `release_blocking=false`.

The branch was then rewritten to remove historical ZIP blobs and profile/debug artifacts from Git history before this closure release.

## Required validation command

Run from repository root:

```bash
./scripts/docker-bonnetjes-cloudflare-validation.sh
```

Expected pass signal:

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

## Non-scope

No Project Source mutation.
No `/v1/login-check`.
No login automation.
No adoption/current claim without release-control evidence.

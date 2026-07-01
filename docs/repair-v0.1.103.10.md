# v0.1.103.10 — Bonnetjes Cloudflare one-shot validation script

Status: candidate only.

## Scope

Adds one operator validation script for the Cloudflare test phase:

```bash
scripts/docker-bonnetjes-cloudflare-validation.sh
```

The script composes the full validated flow:

1. optional candidate install through `pb release install`;
2. visible clean-login profile bootstrap;
3. Docker Bonnetjes Cloudflare parity check against the same profile;
4. strict validation of the resulting `summary.json`.

## Non-scope

No Project Source mutation.
No login automation.
No new browser architecture.

## Pass signal

The validation passes only when:

- `cloudflare_cleared=true`;
- `logged_in=true`;
- `challenge_detected=false`;
- `composer_visible=true`;
- `release_blocking=false`;
- `project_source_mutation_allowed=false`.

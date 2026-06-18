# Repair v0.1.78.2.9 — Docker pyproject probe awk-dollar quoting repair

## Problem

`v0.1.78.2.8` reached the Docker running-container content probe, but the pyproject version extraction used an awk `$2` expression inside a `sh -lc 'set -eu ...'` command. The shell expanded `$2` before awk could see it, and because `$2` was unset under `set -u`, the probe failed with `parameter not set`.

## Change

Replace the Docker image/container pyproject probe reader with a shell-safe form:

```sh
grep -E "^version = " /app/pyproject.toml | head -n 1 | cut -d "\"" -f 2
```

This avoids shell positional parameters entirely.

## Preserved boundaries

- ChatGPT Project deletion remains frozen.
- No secure delete protocol is introduced.
- Project Source behavior is unchanged.
- Artifact adoption/current state is not mutated by this candidate.
- Docker provenance host/image/container/health checks remain in scope.

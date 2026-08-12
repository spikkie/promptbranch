# Promptbranch developer guide

PB development keeps authority-critical behavior deterministic and small.

## Extension order

1. Define the current contract and authority boundary.
2. Add or update schemas/registries only when needed.
3. Implement one canonical code path.
4. Add focused regression tests for success and fail-closed negative cases.
5. Include the regression in canonical release validation when it protects an authority-critical behavior.
6. Build deterministically and verify the exact frozen artifact.
7. Use the canonical lifecycle for live proof and adoption.

## Skills

Skills are procedures plus declared risk, allowed tools and prechecks. A read skill may only reference read-only MCP tools. A skill is guidance/controlled planning; its existence is not write authority.

## Tools

Use the `promptbranch-tool-authoring` skill. Tool authoring is proposal-only. Input must be bounded, risk explicit, validation/evidence deterministic, and failure fail-closed.

## Compatibility policy

Do not retain deprecated PB internals, old schemas, aliases, migration shims or dual behavior merely to preserve obsolete PB tests. Operational resilience inside the current canonical path is different: bounded retries, selector alternatives, browser diagnostics and network resilience are acceptable when they do not create a second authority path.

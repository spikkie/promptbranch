# Project settings

## PBAI-001 application architecture

- Application id: `example-domain`
- Application kind: `domain_module`
- Generic runtime provider: `promptbranch`
- The tracked declaration is `.promptbranch-ai.json`.
- `VERSION` (or the configured version authority) is the sole version source.
- Architecture validation is fail-closed and reports only the highest proven level.
- Mutation, release, publication, and adoption require explicit requests and verified Promptbranch evidence.
- Missing declarations or migration gaps require an explicit migration report; no silent compatibility fallback is permitted.

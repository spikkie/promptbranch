# Release v0.1.117.1

## Type

Repair candidate. It does not advance the normal roadmap beyond accepted/current `v0.1.117`.

## Baseline

- accepted/current version: `v0.1.117`
- canonical artifact: `chatgpt_claudecode_workflow-2_v0.1.117.zip`
- accepted SHA-256: `a7516dbc88049cd229ae7fdc6b012bb876e1f42de85199e13b3f71c66f22b01c`
- assigned Project Source: `chatgpt_claudecode_workflow-2_v0.1.117(2).zip`

## Defect

The release workflow could reuse validation evidence bound to the input transport ZIP while adoption used a clean rebuilt canonical ZIP. The artifact registry also allowed a later artifact with the same semantic version and a different SHA-256 to become current.

## Repair contract

1. An adopted repository/version identity is immutable by SHA-256.
2. Same version plus different or missing SHA-256 fails closed before registry or Project Source mutation.
3. Same version plus the exact same SHA-256 is idempotent and skips duplicate publication and adoption.
4. Reusable validation evidence is bound to the final canonical artifact SHA-256, repository identity, Git commit, validation profile, and skip matrix.
5. The generic release pipeline performs the same immutable identity preflight before Project Source publication.

## Validation required

- focused immutable-identity and evidence-reuse regressions;
- project control and authority validation;
- release validation groups;
- deterministic byte-identical rebuild;
- Artifact Guardian;
- strict host release validation before adoption.

## Next normal slice

`v0.1.118 — Resumable/importable release-pipeline evidence and recovery`.

# Promptbranch Plan v0.1.107

## Slice

Controlled correction execution envelope design.

## Accepted authority

`v0.1.106` is accepted/current after 10/10 GO and `release_adopted_and_verified`. Its promotion decision authorizes this design slice only.

## Contract

`pb loop execution-envelope-design --target <target.json> --json` must produce a deterministic envelope containing:

- one future disposable-repository target;
- one exact mutable file and read-only target definition;
- one `replace_contents` operation;
- exact pre-state and post-state SHA-256 values;
- one allowlisted read-only validation command;
- mandatory exact rollback and workspace deletion;
- bounded file, operation, command, byte, iteration, retry, and timeout limits;
- a complete required evidence bundle;
- one canonical design fingerprint;
- explicit false values for all correction execution and broader mutation authority.

The command may read target and decision data. It must create no workspace, execute no command, and mutate no file or repository.

## Fail closed

Missing or invalid repository authority, GO decision, target identity, mutable path, operation, hashes, replacement content, validation, rollback, limits, timeouts, or zero-authority evidence produces `execution_envelope_design_blocked`.

## Next slice

`v0.1.108 — Controlled correction execution envelope validation gate` may validate this design only. It still may not execute a correction.

# Repair v0.1.78.2.7 — Docker provenance probe syntax repair

## Problem

`v0.1.78.2.6` added Docker host/image/container provenance probes, but the embedded Python JSON writers in `chatgpt_claudecode_workflow_release_control.sh` contained malformed newline string literals. During release-control this produced:

```text
SyntaxError: unterminated string literal
```

The probe JSON file was not written, so release-control reported a Docker container content mismatch without usable evidence.

## Scope

- Repair embedded Python newline literals in Docker provenance probe JSON writers.
- Add a focused regression test for the JSON writer literal form.
- Preserve Docker provenance guard behavior from `v0.1.78.2.6`.
- Preserve delete-frozen project policy and retained live-test behavior.

## Out of scope

- No ChatGPT Project deletion.
- No secure delete protocol.
- No Project Source behavior change.
- No v0.1.79/k8s-game work.

## Validation

Focused shell/version/delete-safety tests, compileall, shell syntax, ZIP hygiene, and Artifact Guardian were run for candidate creation. Full release-control remains operator-side validation.

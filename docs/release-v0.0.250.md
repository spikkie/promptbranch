# Release v0.0.250 — Release Project Source add verification

Built from accepted baseline `chatgpt_claudecode_workflow_v0.0.249.zip`.

## MVP status update

The current MVP is still split across several tracks:

- Local agent/MCP foundation: mostly complete and still read-only by default.
- Ask/Reply + Artifact Intake: mature for protocol smoke and no-artifact handling, but still awaiting a real assistant-generated artifact candidate run.
- Release lifecycle doctor/config/install: active path.
- Native lifecycle command: not complete yet.

The current documentation defines the native lifecycle goal as moving generic lifecycle mechanics into Promptbranch while keeping project-specific hooks in repo-local config. A complete lifecycle still requires candidate ZIP install, Project Source visibility, acceptance tests, adoption, policy sync, git sync, and a final summary.

The documented MVP track E planned this exact sequence:

```text
v0.0.248 — release install plan, read-only
v0.0.249 — release install, controlled mutation
v0.0.250 — release source-add verification
```

`v0.0.250` implements the third step only. It does not advance adoption or full lifecycle behavior.

## Scope

Adds controlled Project Source upload verification to `pb release install`:

```bash
pb release install \
  --artifact ZIP \
  --version VERSION \
  --target-version NEXT \
  --repo-path . \
  --upload-source \
  --json
```

## Behavior

With `--upload-source` and without `--plan`, the command now:

1. validates `.promptbranch-release.yml`;
2. verifies the candidate ZIP;
3. performs the bounded repo install from `v0.0.249`;
4. lists Project Sources before upload;
5. uploads the candidate ZIP as a file Project Source;
6. lists Project Sources after upload;
7. verifies the expected source is visible;
8. rejects collateral source removal;
9. allows expected source replacement when overwriting the same artifact filename.

## Safety boundary

Still intentionally not performed:

- no artifact registry update;
- no Promptbranch artifact/source state advancement;
- no candidate test/adoption;
- no Git commit or push;
- no full lifecycle execution.

If Project Source upload does not verify, the command fails closed and leaves registry/state/adoption/git untouched.

## Verification model

Project Source upload is trusted only when all required checks pass:

- upload result succeeded;
- source list before upload was readable;
- source list after upload was readable;
- expected source filename is present after upload;
- no unrelated source was removed.

An overwrite replacement of the expected source filename is not classified as collateral removal.

## Validation

Focused tests cover:

- `--upload-source` parser support;
- read-only plan reporting for requested source upload;
- successful before/after Project Source verification;
- source upload verification failure without registry/state advancement;
- expected-source replacement vs. collateral source removal;
- existing release install and source sync regression behavior.

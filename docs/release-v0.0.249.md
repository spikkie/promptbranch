# Release v0.0.249 — Controlled release install mutation

## Scope

`v0.0.249` advances the native release lifecycle install slice from read-only planning to a bounded repository install mutation.

## Added

```bash
pb release install --artifact ZIP --version VERSION --json
```

The command now:

- validates `.promptbranch-release.yml`;
- verifies candidate ZIP hygiene/version/layout;
- rejects ZIP entries under configured `install.preserve` paths;
- extracts candidate ZIP entries into the repository root;
- overwrites matching files and creates missing files;
- verifies the installed `VERSION` after extraction.

## Still intentionally not performed

- no deletion of stale repository files;
- no Project Source upload;
- no artifact registry update;
- no Promptbranch artifact/source state update;
- no candidate test/adoption;
- no Git commit or push.

## Safety model

`--plan` remains read-only. Omitting `--plan` performs only the bounded install mutation described above.

## Validation

Focused tests cover both read-only planning and controlled install execution, including preservation of local runtime files.

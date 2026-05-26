# Release v0.0.276.11

## Scope

Repair release on top of `v0.0.276.10`.

Adds an explicit smoke-ZIP verification mode for ChatGPT UI attachment download tests.

## Why

`v0.0.276.10` proved that Promptbranch can download a rendered ChatGPT ZIP attachment/button into `.pb_profile/artifact_inbox/`. The smoke ZIP intentionally contains only `hello.txt`, so strict release verification correctly fails with `artifact_version_file_missing`.

This release preserves that strict release behavior and adds a separate smoke verifier:

```bash
pb artifact intake \
  --from-last-answer \
  --expect-artifact chatgpt_claudecode_workflow_v0.0.277.zip \
  --download \
  --verify-smoke-zip \
  --expect-entry hello.txt \
  --expect-content "durable ChatGPT UI attachment smoke test" \
  --json
```

## Non-goals

- Does not weaken `--verify` release ZIP validation.
- Does not allow smoke ZIP migration or adoption.
- Does not change browser-download behavior.
- Does not mutate Project Sources.

## Files changed

- `promptbranch_cli.py`
- `promptbranch_version.py`
- `pyproject.toml`
- `VERSION`
- `promptbranch.egg-info/PKG-INFO`
- `docs/release-v0.0.276.11.md`
- `tests/test_promptbranch_cli.py`

## Validation

- Python compile smoke.
- Focused unit tests for smoke ZIP verification success and strict verification separation.
- ZIP hygiene/layout check.

# v0.1.103.10.19 — install-safe pb test api module runner

## Scope

Repair `pb test api` after pipx installation by moving the API coverage runner into the installed `promptbranch` package and invoking it with `python -m promptbranch.api_coverage_test`.

## Bug

`v0.1.103.10.18` looked for `scripts/pb-api-coverage-test.py` next to the installed `promptbranch_cli.py` module, which resolves to a non-existent `site-packages/scripts/...` path after installation.

## Invariant

`pb test api` must work from an installed wheel/pipx environment and from a source checkout.

## Out of scope

No Project Source mutation policy changes, no Project deletion changes, no v0.1.104.x browser session manager changes.

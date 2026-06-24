# Repair v0.1.87.1 — package loop module for installed CLI

Base release: `v0.1.87` candidate.

Repair version: `v0.1.87.1`.

Reason: installing the `v0.1.87` candidate produced an installed CLI import failure because `promptbranch_cli.py` imports `promptbranch_loop`, but `promptbranch_loop.py` was not listed in the setuptools `py-modules` package metadata. The source ZIP contained the file, but the installed wheel/environment did not include the module.

Files changed:

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `tests/test_promptbranch_version.py`
- `tests/test_promptbranch_loop_packaging.py`
- `docs/repair-v0.1.87.1.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/definition-of-done.md`
- `docs/project/migration.md`

Validation performed in the build environment:

- focused loop packaging regression tests
- loop CLI tests
- loop model tests
- version tests
- project-control tests
- compileall
- shell syntax
- pip install smoke in an isolated virtual environment proving `import promptbranch_loop` and installed `promptbranch --version` work
- Artifact Guardian
- artifact verify
- ZIP hygiene

Scope confirmation: this repair does not advance the loop slice, does not add real loop actions, does not execute target commands, does not deploy, does not mutate Kubernetes, does not mutate Project Source behavior, and does not change artifact adoption/current behavior.

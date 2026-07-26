# Promptbranch v0.1.111.1 repair candidate

Repairs the installed-package failure in v0.1.111 without changing the release-contract engine behaviour.

## Defect

`promptbranch_release_engine.py` existed in the repository and release ZIP but was omitted from the explicit setuptools `py-modules` declaration. Docker source-tree execution therefore worked while the pipx-installed CLI failed at import time with `ModuleNotFoundError`.

## Repair

- add `promptbranch_release_engine` to `tool.setuptools.py-modules`;
- add a package-declaration regression test;
- add a release-control installed-candidate smoke gate immediately after `pipx install`;
- run `promptbranch --version` and read-only `promptbranch release contract-plan` from a temporary directory with `PYTHONPATH` removed;
- block before browser bootstrap or Project Source mutation when either installed command fails;
- preserve all v0.1.111 lifecycle-contract semantics unchanged.

## Authority

Accepted/current remains `v0.1.109.1.1` until full direct, localhost, external-live, publication, adoption, and accepted/current verification pass.

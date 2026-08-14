# v0.1.128.2.6.1.1.2.1.1.1.1

## Purpose

Python 3.10 Docker-contract and non-Git build-context corrective following immutable failed candidate `v0.1.128.2.6.1.1.2.1.1.1`.

## Repair

- Keep `VERSION` as the sole mutable current-version authority.
- Make `promptbranch_docker_build_contract` work in the Playwright Jammy Python 3.10 image by falling back from stdlib `tomllib` to the already-installed `tomli` dependency.
- Disable Buildx Git info, Git labels, and dirty-state probing for release builds whose context is an exact ZIP extraction rather than a Git worktree.
- Add a fake-`git` trap proving the exact-ZIP Docker build gate does not invoke Git from its non-Git extraction directory.
- Preserve the mandatory exact-final-ZIP real Docker image build and immutable image-label verification before the broader lifecycle.

## Authority

`VERSION` remains the sole mutable current-version authority. A non-Git exact release context must never require Git metadata to build or validate.

## Live status

Construction candidate only. Accepted/current remains `v0.1.128.2.6.1.1.1` until the canonical lifecycle reaches `FINAL_VERIFIED` and authoritative current convergence.

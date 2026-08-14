# v0.1.128.2.6.1.1.2.1.1.1

## Purpose

Docker VERSION-authority closure corrective following immutable failed candidate `v0.1.128.2.6.1.1.2.1.1`.

## Repair

- Replace Dockerfile regex extraction of `PACKAGE_VERSION` and static `project.version` with `promptbranch_docker_build_contract`.
- Verify Docker context through root `VERSION`, derived `promptbranch_version.PACKAGE_VERSION`, dynamic setuptools configuration, and canonical source fingerprint.
- Add a regression that changes only `VERSION` and proves package version, CLI version, Docker build contract, and wheel metadata all follow without editing another source file.
- Extend current-version literal scanning to Dockerfile/Containerfile/Makefile surfaces.
- Add `scripts/verify-exact-zip-docker-build.py`: an actual Docker build and immutable image-label check from one exact final ZIP. Docker absence is a hard failure for this gate.

## Authority

`VERSION` remains the sole mutable current-version authority. No current release literal is added to executable or packaging code.

## Live status

Construction candidate only. Accepted/current remains `v0.1.128.2.6.1.1.1` until the canonical lifecycle reaches `FINAL_VERIFIED` and authoritative current convergence.

# Promptbranch v0.1.111 candidate

Implements the first operational version of ISSUE-001 while retaining the proven project-local release-control path during migration.

## Added

- strict tracked `.promptbranch-release.json` contract;
- fail-closed parser rejecting unknown fields, unsafe paths, shell invocation, missing timeouts, and ambiguous structure;
- `pb release contract-plan` for read-only planning;
- `pb release contract-execute {validate,test,build,verify,verify_current}`;
- separate `pb release contract-publish` and `pb release contract-adopt` operations;
- bounded subprocess execution with stdout/stderr evidence, timestamps, exit codes, timeout classification, artifact SHA-256 and ZIP validation;
- preservation checks for `.pb_profile/` and `.promptbranch-repo.json`;
- forbidden-mutation checks for `.git/`;
- deterministic repository release ZIP builder;
- contract tests and backlog status update.

## Migration boundary

The existing `chatgpt_claudecode_workflow_release_control.sh` remains authoritative for final full validation and adoption until differential validation proves the new global engine equivalent or stronger. The candidate does not claim accepted/current adoption.

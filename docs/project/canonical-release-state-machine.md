# Canonical release state machine

Release: `v0.1.125.3.4.2`

## Purpose

Promptbranch release control uses one durable, SHA-bound release attempt instead of requiring the operator to coordinate artifact intake, candidate registration, runtime preparation, testing, acceptance, and current-state adoption as unrelated workflows.

The canonical local command is:

```bash
pb release run \
  --artifact chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip \
  --version v0.1.125.3.4.2 \
  --baseline-version v0.1.125.3.4.1 \
  --release-type repair \
  --profile full \
  --test-timeout 3600 \
  --until final-verified \
  --adopt \
  --json
```

Git commit, Git push, and Project Source upload remain disabled unless their positive flags are supplied.

## Durable states

The only normal state order is:

```text
DECLARED
ARTIFACT_BOUND
ARTIFACT_VERIFIED
CANDIDATE_REGISTERED
RUNTIME_PREPARED
TESTED_GREEN
ACCEPTED
ADOPTED_CURRENT
FINAL_VERIFIED
```

The failure classifications are `BLOCKED_RETRYABLE` and `FAILED_TERMINAL`.

Each successful transition persists its source state, destination state, evaluated guards, transition result, and evidence. The attempt is keyed by repository, target version, and immutable artifact SHA-256.

## Independent verification

`pb release verify` does not trust the persisted state label by itself. It reloads the attempt and independently re-evaluates every reached state's invariants:

```bash
pb release verify \
  --version v0.1.125.3.4.2 \
  --repo-path . \
  --all-states \
  --json
```

A reached state is reported as verified only when its current evidence and projections still satisfy the state contract. Missing derived candidate projections may be reconstructed from the authoritative attempt. Identity conflicts, ambiguous candidates, artifact tampering, mismatched test evidence, and split accepted/current projections fail closed.

## Exact-byte candidate testing

Candidate validation runs from a clean extraction of the immutable object-store copy. It binds:

- the candidate SHA-256 and version;
- the candidate Python executable;
- pytest `9.0.2`;
- the requested test profile;
- an isolated HOME, XDG hierarchy, Promptbranch project state/config, and Python bytecode cache.

The mutable working tree is not the candidate correctness authority. A dirty tree may block publication, but it cannot contaminate exact-byte candidate validation.

## Mutation policy

The state machine is local and fail-closed by default. These mutations require positive authorization:

```text
--adopt
--commit
--push
--upload-project-source
```

`--push` requires `--commit`. Omitting a skip option never authorizes a mutation.

## Resume and idempotency

After interruption, the same command reloads the durable attempt and executes exactly the next legal transition. Completed transitions are not repeated. A completed lifecycle returns `already_complete` with `mutation_performed=false`.

## Test authority

`tests/test_release_state_machine.py` verifies:

- all states and the complete legal transition chain;
- every reached state before future states exist;
- illegal-transition rejection without mutation;
- interruption and exact resume after every state;
- repeated-run idempotency;
- artifact identity conflict and artifact tamper detection;
- missing and conflicting candidate projection behavior;
- test failure and bounded retest;
- explicit adoption and publication gates;
- hermetic validation against ambient Python, registry, XDG, and dirty-tree state;
- SHA-bound test evidence;
- final runtime, service, candidate, accepted, state, and current-registry convergence.

The module is a mandatory `release_state_machine` release-validation group.

## Isolated runtime preparation repair

`v0.1.125.3.2` adds a durable runtime checkpoint below the release-attempt authority. The runtime checkpoint is not an independent release authority; it records resumable implementation progress for the single `RUNTIME_PREPARED` transition.

The candidate runtime uses an attempt-specific Compose project, image name and host port. The accepted runtime remains on the canonical port and must retain the same container identity and health version throughout candidate preparation and candidate testing.

Every completed runtime phase is independently recorded and verified. A retry resumes at the first missing phase. Timeout evidence includes streamed build/start logs, Compose state, container state, image labels, container logs and health snapshots.

## Deterministic candidate-test report authority

`v0.1.125.3.2` treats mixed candidate-test stdout as a stream of complete top-level JSON documents. The `TESTED_GREEN` transition selects exactly one complete report by schema, action, profile and version. Nested dictionaries, including the terminal `safety` object, cannot become report authorities.

The selected report is canonicalized and SHA-256 bound. The state-machine record also binds the complete stdout and stderr hashes and persists completed, passed, failed and skipped unit counts together with failed validation groups and steps.

The transition fails closed when the report is missing, ambiguous or structurally invalid. Test success requires a zero process return code, `ok=true`, zero failed units, zero skipped required units and exact report identity.

The full candidate gate also binds repository authority explicitly for execution-envelope validation and accepts read-only `project_repo_not_configured` smoke output only when no mutation evidence is present.

## v0.1.125.3.3 acceptance/adoption transactional reconciliation

`v0.1.125.3.3` makes the acceptance and current-state boundary action-aware and recoverable. Mixed command stdout is parsed as complete top-level JSON documents; nested `consistency`, `registry_current`, or other dictionaries cannot become the acceptance/current authority.

The `ACCEPTED` transition follows this deterministic contract:

1. verify SHA-bound green test evidence and explicit `--adopt` authority;
2. inspect existing candidate/current projections before executing acceptance;
3. when acceptance is still required, execute exactly one `artifact accept-candidate` command;
4. select exactly one complete top-level `action=artifact_accept_candidate` result;
5. after any failed, timed-out, missing, ambiguous, or invalid command result, re-read the authoritative candidate registry plus `artifact current`;
6. if those projections already contain the exact repo/version/SHA as accepted/current, reconcile the durable attempt instead of repeating adoption;
7. otherwise remain at `TESTED_GREEN` with a retryable failure.

A stale attempt whose external projections already prove the exact candidate accepted/current resumes without a second acceptance mutation:

```text
TESTED_GREEN
→ ACCEPTED       (recovered/reconciled, no repeat adoption)
→ ADOPTED_CURRENT
→ FINAL_VERIFIED
```

`ADOPTED_CURRENT` verification is structural rather than substring-based. It requires the exact repository entry, artifact/source filename and version, and current-registry SHA-256 to match the immutable release attempt.

Regression proof includes a side-effect-then-ambiguous acceptance executor: the acceptance side effect is committed, command parsing is deliberately made ambiguous, the state machine re-reads authoritative state, performs no duplicate acceptance, and reaches `FINAL_VERIFIED`.



## v0.1.125.3.4.1 authoritative runtime promotion and final convergence

`ADOPTED_CURRENT` now includes the live authoritative runtime. After `TESTED_GREEN` and acceptance, the state machine promotes the exact tested candidate image to the canonical Compose project `chatgpt_claudecode_workflow` on port `8000`; it does not rebuild different bytes. The production image tag must resolve to the same image ID as the tested candidate image. The live `/healthz` version and image labels for target version, artifact SHA-256, and release attempt ID are mandatory. Failed promotion triggers rollback to the previously healthy image. `FINAL_VERIFIED` independently re-probes the authoritative service and therefore cannot remain green when port `8000` is stale. Successful promotion also removes isolated `pb-candidate-*` service containers.


## v0.1.125.3.4.2 lifecycle-aware post-adoption verification

`RUNTIME_PREPARED` has one canonical meaning at each lifecycle phase. Before adoption, its isolated candidate endpoint must be live and exact. At or after `ADOPTED_CURRENT`, that endpoint is intentionally disposable and must not remain a live invariant. The verifier instead requires immutable runtime-checkpoint evidence for candidate health and identity, successful candidate cleanup, and exact equality of the tested candidate Docker image id and the promoted production Docker image id. `ADOPTED_CURRENT` and `FINAL_VERIFIED` continue to live-probe the authoritative service on port 8000.

The superseded post-adoption live-candidate rule is removed; there is no compatibility switch or dual verifier path. Acceptance likewise requires the canonical accepted-candidate projection and no longer reconstructs it through a compatibility fallback.

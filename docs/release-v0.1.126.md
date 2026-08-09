# v0.1.126 — Persistent whole-release ETA estimator

## Baseline

- accepted/current baseline: `v0.1.125.3.4.2`
- baseline artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip`
- baseline SHA-256: `ed6752cc7e1cf654f0e3ea505110599d5be3e067dbb00f07b8ae90cf34a9510f`
- release type: `normal`
- target artifact: `chatgpt_claudecode_workflow-2_v0.1.126.zip`

## Purpose

`v0.1.126` makes release timing a durable, queryable part of the canonical Promptbranch release state machine. It replaces ad-hoc whole-release timing guesses with evidence-backed estimates that survive process restarts and subsequent releases.

The feature remains observational. Validation authority continues to come only from the canonical release states and their fail-closed evidence.

## Canonical ETA evidence

Completed state-machine transitions persist timing observations in `.pb_profile/release-eta-history.json`. Every observation records:

- target and baseline version;
- release type;
- test profile (`smoke` or `full`);
- lifecycle phase;
- execution transport;
- transition step;
- duration and outcome;
- exact release attempt identity;
- transition start and finish timestamps.

The history is also seeded from existing canonical `release_attempts_v2/**/attempt.json` transition evidence. Observation IDs are deterministic and deduplicated, so repeated inspection does not multiply history records.

Failed timing observations may be retained for diagnostics but do not become ETA prediction authority.

## Whole-release estimate

Each release attempt writes `.pb_profile/release_attempts_v2/.../release-eta.json` and embeds the latest snapshot in the durable attempt record. The snapshot reports:

- remaining canonical release steps through `FINAL_VERIFIED`;
- approximate remaining seconds and low/high range;
- approximate expected finish time and earliest/latest finish range;
- confidence level;
- per-step prediction basis and evidence source;
- current active transition and elapsed duration when a transition is running.

Persistent same-step/profile/transport observations are preferred. Coarse profile/step priors provide a low-confidence first-run estimate until enough history exists.

## Timeout-risk diagnostics

The snapshot contains advisory timeout diagnostics for:

1. the candidate `TESTED_GREEN` subprocess timeout; and
2. an optional operator/wrapper timeout supplied to `pb release eta --outer-timeout`.

Candidate-test recommendations are profile-aware. Historical high-bound evidence drives the recommendation when available; conservative profile defaults are used otherwise.

A timeout recommendation never changes a configured timeout automatically and never changes pass/fail authority. A release can still fail closed on the configured timeout even when ETA believes a larger timeout would have been safer.

## Read-only status command

```text
pb release eta \
  --version v0.1.126 \
  --repo-path <repo> \
  --outer-timeout <seconds> \
  --json
```

The command resolves the durable canonical attempt, refreshes only the dedicated advisory ETA snapshot, and does not mutate authoritative release state.

## Failure semantics

ETA calculation, history parsing, or ETA snapshot writes are non-authoritative. Any ETA problem is reported as `eta_degraded` with `validation_authority_unchanged=true`. The release lifecycle itself continues to use the existing fail-closed state-machine guards.

No compatibility layer is retained for a superseded whole-release estimator. The canonical state-machine ETA model is the authoritative whole-release timing mechanism going forward.

## Acceptance criteria

`v0.1.126` is accepted only after the canonical live lifecycle proves all of the following:

- exact artifact verification;
- persistent ETA history is written from canonical transitions;
- full-profile candidate validation is green;
- ETA snapshot exposes expected finish, confidence, evidence source, and timeout risk;
- ETA failures are unable to alter validation authority;
- candidate acceptance and exact tested-image adoption succeed;
- authoritative port-8000 runtime converges to `v0.1.126`;
- independent `release verify --all-states` reports no failed invariants;
- lifecycle reaches `FINAL_VERIFIED`.

After acceptance, the next planned normal slice is `v0.1.127 — Portable Promptbranch tool-authoring skill and export bundle`.

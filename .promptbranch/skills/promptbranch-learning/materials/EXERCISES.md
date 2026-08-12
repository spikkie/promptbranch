# Promptbranch learning exercises

Each exercise is read-only unless an external instructor/operator explicitly creates a separate authorized lab.

## Exercise 1 — Identify authority

Given a repository with a `VERSION`, a release ZIP filename and an artifact registry current entry, identify which values are observations and which one proves authoritative current.

**Expected verdict:** filename/version alone are insufficient; current must resolve to an immutable SHA in the project-scoped authority chain.

## Exercise 2 — Skill authority

Validate a read-only skill and explain whether the result authorizes a repository edit.

**Expected verdict:** no. Skill validity does not grant mutation authority.

## Exercise 3 — Historical answer trap

A conversation already contains `INTEGRATION_OK`. A new prompt requests the same token. Explain why the historical token cannot be accepted as the new answer.

**Expected verdict:** fresh answer causality must be established from the new submit/generation chain.

## Exercise 4 — Project new-chat transition

A prompt is submitted on `/project` and the UI later moves to `/c/<id>`. Identify the evidence that should be retained.

**Expected verdict:** baseline URL/conversation identity, submit causality, URL transition, new conversation ID, fresh assistant chain and completion state.

## Exercise 5 — Release claim

A candidate passed tests but was not adopted/current. Can it be called accepted/current?

**Expected verdict:** no. Acceptance, adoption/current and final verification are distinct states.

## Exercise 6 — Stale control projection

The artifact registry says version A/SHA X is current, while tracked control documents say version B/SHA Y.

**Expected verdict:** fail closed; authoritative/current projection has not converged.

## Exercise 7 — Tool proposal

A valid `promptbranch.tool.authoring` specification declares `registration=proposal_only` and all execution/mutation authorities `not_granted`.

**Expected verdict:** the tool may be reviewed as a proposal but cannot be executed or registered merely because validation passes.

## Exercise 8 — External application boundary

PB is about to operate on a separate application repository.

**Expected verdict:** PB's control plane and the application's repository/runtime authority remain separate; the application workflow must declare target, architecture, DoD, validation and explicit mutation/deployment authority.

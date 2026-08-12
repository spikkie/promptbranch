# Promptbranch authority model

Authority is explicit and layered. Learning material, an LLM answer, a valid skill, a valid tool specification, or a successful read-only inspection never grants write authority by itself.

## Authority layers

1. **Observation authority** — read repository/workspace/task/artifact state.
2. **Planning authority** — propose a bounded next action and required preconditions.
3. **Execution authority** — run a controlled operation through PB policy.
4. **Mutation authority** — change repository, browser, Project Source or application state.
5. **Publication authority** — publish an artifact/source or Git state.
6. **Acceptance authority** — declare a tested candidate accepted.
7. **Adoption authority** — make an immutable artifact authoritative current for a project.
8. **Deployment authority** — change an external application's runtime environment.

These are not interchangeable.

## Artifact authority

For a release, the authoritative identity is the tuple of repository identity, version and immutable artifact SHA. A filename alone is insufficient. Accepted/current is only proven when the project-scoped registry/current resolver and runtime/control projection agree with the exact adopted artifact.

## Browser and conversation authority

A browser-visible assistant answer must be causally tied to the submitted turn. Historical matching text is not proof. URL/conversation identity transitions matter when a new Project chat becomes a `/c/<conversation-id>` conversation.

## Fail-closed rule

When authority, identity, current state, causality or evidence is unknown or contradictory, PB must not guess a favorable interpretation. The operation remains unproven or blocked until the required evidence exists.

# Safe inspection

Typical read-first surfaces include `pb skill list/show/validate`, `pb ws current --json`, `pb task current --json`, `pb artifact current --json`, repository `VERSION`, git status/diff, and tracked project-control documents. Availability depends on the active PB workspace/profile.

Read-only inspection is preferred before every mutation because it resolves identity and authority without changing the target state.

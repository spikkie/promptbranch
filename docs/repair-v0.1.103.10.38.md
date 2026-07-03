# v0.1.103.10.38 — pre_tests auth bootstrap conversation targeting

`v0.1.103.10.38` repairs the `v0.1.103.10.37` release-control failure where `pre_tests` auth bootstrap targeted the project home page and then failed composer validation.

The resolver is now phase-aware:

- `pre_source_add` may accept logged-in `/project` readiness without a composer.
- `pre_tests` prefers a current project conversation URL from local Promptbranch state before composer validation.
- Conversation URL query parameters are preserved.
- If no conversation URL exists, project-page readiness is only a documented fallback; operators may supply `PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_PRE_TESTS_URL` for recovery.

Out of scope: browser/session architecture changes, Project Source mutation changes, ChatGPT Project deletion, adoption claims, and v0.1.104.x host-CDP work.

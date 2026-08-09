# v0.1.126.1.1.1.1 — Ask deadline propagation and structured timeout evidence repair

## Authority

- Built from the exact immutable `v0.1.126.1.1.1` artifact (`a7deb5db6ed34efe442b464a30396e9db259f74240903cb703c52a524747f01b`).
- Accepted/current baseline remains `v0.1.125.3.4.2` until this candidate reaches `FINAL_VERIFIED`.
- Release mode: repair; no normal-slice scope advance.

## Live failure repaired

The `v0.1.126.1.1.1` canonical full candidate run passed Project Source text add, file add, and indexed-family overwrite, then `browser.ask_question` failed after 300.119 seconds with a raw service-client `ReadTimeout`. The Docker integration adapter configured a 300-second HTTP client but omitted the `service_timeout_seconds` form field, so `/v1/ask` could not activate its earlier internal deadline and structured partial-result path. The canonical smoke step also called the answer-only API, discarding structured submit/conversation/timing evidence.

## Repair

- `DockerServiceAdapter` passes its explicit ask service budget to `ChatGPTServiceClient.ask_result`.
- `/v1/ask` therefore derives an internal browser deadline eight seconds below the outer service budget, leaving response time before the HTTP client deadline.
- The canonical `browser.ask_question` smoke uses `ask_question_result`, keeps structured evidence, and validates the answer token only after `ok=true`.
- A residual HTTP `ReadTimeout` is converted into `service_client_read_timeout` with `timeout_layer=service_client`, `partial_result=true`, and `retry_permitted=false`.
- Confirmed/partial submit evidence is retained by the canonical step; `retries=0` prevents duplicate submission after an ambiguous or confirmed timeout.

## Acceptance

Construction validation does not accept this release. First prove an ask-only live run against the exact candidate runtime. Then run the complete 53-unit candidate validation and canonical publication/adoption lifecycle. Final acceptance still requires `FINAL_VERIFIED`, independent all-state verification with no failed invariants, exact Git publication, exact Project Source artifact evidence, and production-image convergence on port 8000.

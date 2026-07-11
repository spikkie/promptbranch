# v0.1.103.10.76 — normalize visible thinking preamble before exact sentinel validation

## Scope

- Keep the v0.1.103.10.69 strict `install.sh` all-all release gate.
- Keep product-clean `LIVE_BLOCKED` classification.
- Keep the v0.1.103.10.75 `bootstrap_sentinel_missing_after_ask_success` status.
- Normalize only known visible-thinking preambles before release-live sentinel validation.
- Preserve fail-closed exact-token validation for arbitrary extra text.
- Apply the same release-live sentinel matcher to bootstrap and ask sentinel checks.
- Preserve adoption refusal when validation is not `GO`.
- No Cloudflare/rate-limit bypass.
- No host-CDP/session-manager.
- No copied-profile trust.

## Rationale

Live evidence from v0.1.103.10.75 showed the expected bootstrap sentinel on the last line, preceded only by a visible ChatGPT thinking preamble. The old exact matcher rejected this even though the sentinel itself was exact. This repair accepts only the bounded known preamble forms and continues to reject any other prefix/suffix text.

## Expected behavior

Accepted release-live answer shapes:

```text
LIVE_CONVERSATION_BOOTSTRAP_0_1_103_10_76
```

```text
Thought for a couple of seconds
LIVE_CONVERSATION_BOOTSTRAP_0_1_103_10_76
```

```text
Thought for a few seconds
ASK_LIVE_PLAIN_0_1_103_10_76
```

Rejected release-live answer shapes:

```text
Here is the token:
LIVE_CONVERSATION_BOOTSTRAP_0_1_103_10_76
```

```text
LIVE_CONVERSATION_BOOTSTRAP_0_1_103_10_76 extra
```

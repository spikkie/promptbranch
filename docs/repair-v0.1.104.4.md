# Repair v0.1.104.4 — parse-independent visual reply completion and bounded envelope recovery

## Baseline

Accepted/current remains `v0.1.103.10.116`. This repair follows the unadopted `v0.1.104.3` candidate, which passed 9/10 strict gates.

## Cause

The visual response was complete and the UI was idle, but response freshness rejected a virtualized assistant list whose visible count fell below the pre-submit baseline. The wait therefore consumed the full response timeout. The recovered response contained one Promptbranch block wrapped in literal escaped outer newlines, which the strict parser correctly rejected.

## Repair contract

- Accept a reduced visible assistant count only after confirmed submit causality, observed generation, and text differing from the exact baseline.
- Require stable assistant text plus generation-observed-then-idle, no stop/thinking state, and an idle composer before returning the visual response.
- Parse only after UI completion; malformed JSON cannot extend the primary response wait.
- Apply one visual-only deterministic normalization that decodes literal `\n`, `\r`, or `\t` only outside JSON strings.
- Require exactly one marked block, one JSON object, exact schema, and exact active request/correlation IDs.
- If still invalid, submit exactly one correction prompt in the same conversation with no attachment, no browser retry, and a 90-second service deadline.
- Do not download until exactly one valid ZIP candidate exists.
- Fail closed after the one retry.

## Preserved

The sandbox release gate, ten-step manifest, fresh direct and independent localhost policies, current-turn readiness, and one-reload post-bootstrap recovery remain unchanged.

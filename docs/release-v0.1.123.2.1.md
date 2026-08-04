# v0.1.123.2.1 — Project authority URL alias reconciliation repair

`v0.1.123.2.1` is a repair-only release from accepted/current `v0.1.123.1`.
The `v0.1.123.2` candidate was not adopted because release control discovered the same ChatGPT Project in a bare URL form while the tracked repository authority used the slugged display form.

## Defect

These values refer to the same immutable Project:

```text
g-p-6a43ea5129508191be8c8ebcf9fc7391
g-p-6a43ea5129508191be8c8ebcf9fc7391-promptbranch3
```

Before this repair, `pb project join` compared the strings literally and stopped adoption before strict validation.

## Repair contract

Promptbranch now extracts the immutable `g-p-<32-hex>` Project UUID from either a project id or a Project/conversation URL. Bare and slugged forms are aliases only when that immutable UUID matches. Values without an immutable Project UUID retain exact comparison.

The tracked `.promptbranch-repo.json` remains authoritative and is never rewritten during alias reconciliation. A different immutable UUID remains a release-blocking mismatch.

## Regression coverage

- slugged tracked id/home versus bare runtime id/home;
- bare tracked id/home versus slugged conversation URL;
- true cross-project immutable UUID mismatch;
- successful `pb project join` alias reconciliation without tracked-authority mutation.

## MVP sequence

This repair cannot count as an MVP proof cycle. After strict adoption, `v0.1.124` remains proof cycle 1 and `v0.1.125` remains proof cycle 2.

# v0.1.127.1.1 — Canonical ChatGPT project identity for artifact conversation provenance

Narrow repair of `v0.1.127.1`. The live legacy provenance bind proved that the command-level project gate correctly treated `g-p-<32hex>` and `g-p-<32hex>-<slug>` as the same ChatGPT Project, while the durable artifact validator compared the full slug literally and rejected the record.

This repair canonicalizes artifact-project and origin-conversation project identity to the stable `g-p-<32hex>` identity before comparison. Slugged and unslugged URLs for the same project are accepted; different canonical project identities remain rejected. The exact origin conversation URL is preserved. Successor ask routing, baseline provenance authority, source/task isolation, response-completion semantics, release authority, and normal product scope are unchanged.

The first live proof is the exact legacy `pb artifact bind-conversation` operation against accepted/current `v0.1.126.1.1.1.1.3`. Do not proceed to `RUNTIME_PREPARED` unless that bind passes.

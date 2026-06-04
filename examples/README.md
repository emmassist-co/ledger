# Examples

These committed examples are small Ledger archives used as regression fixtures.

- `session-like/`: a meeting/session-style archive with registry, extract, and derived artifacts
- `legal-like/`: a law/policy-style archive with registry, extract, and derived artifacts
- `dr-agenda-trabalho-digno/`: a harder cross-corpus DR/DAR fixture with entity, registry, and resolution artifacts
- `dr-cirs-reinvestment/`: a harder tax-law fixture with act, article-block, and note artifacts; intentionally includes one `pass_with_drift` route-quality case

Each example is intentionally tiny and fully committed:

- source placeholders
- artifacts
- generated index outputs
- verifier scripts
- eval scenarios and reports
- trajectory-aware eval reports
- per-example threshold gates

Repo-level generated benchmark summaries live at:

- [benchmark-summary.md](examples/benchmark-summary.md)
- [benchmark-summary.json](examples/benchmark-summary.json)

Use them to test Ledger end to end without relying on a large external corpus.

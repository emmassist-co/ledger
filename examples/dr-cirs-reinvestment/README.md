# Archive Index Workspace

This workspace is a cheap-first retrieval scaffold for large archives.

This committed example uses a real personal-tax slice derived from the local DR archive:

- `CIRS` as the canonical act
- `artigo 10.º` and `artigo 43.º` as deterministic article blocks
- a reusable reinvestment note that is helpful but not strong enough for exact wording claims

Start with:

- `config/index-policy.yaml`
- `sql/schema.sql`
- `docs/promotion-rules.md`
- `scripts/archive_verifier.py`
- `scripts/rebuild_index.py`
- `scripts/check_index_consistency.py`

After the archive is usable, validate it with the separate `archive-evals` companion skill.

Build in layers:

- `source/downloads/`: saved canonical source files
- `source/manifests/`: acquisition metadata and hashes
- `artifacts/acts/`: one entry per code or act
- `artifacts/article-blocks/`: verbatim or deterministic article units
- `artifacts/consolidation-notes/`: reusable summaries and scoped practical readings

Do not let LLM-authored artifacts become the only surviving representation of source text.
Do not hand-edit derived index outputs. Rebuild them from source artifacts.

# Archive Index Workspace

This workspace is a cheap-first retrieval scaffold for large archives.

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
- `artifacts/registry/`: one entry per source document
- `artifacts/extracts/`: verbatim or deterministic extract units
- `artifacts/derived/`: summaries, crosswalks, claims, entities, resolutions

Do not let LLM-authored artifacts become the only surviving representation of source text.
Do not hand-edit derived index outputs. Rebuild them from source artifacts.

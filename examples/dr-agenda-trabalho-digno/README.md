# Archive Index Workspace

This workspace is a cheap-first retrieval scaffold for large archives.

This committed example uses a real cross-corpus slice derived from the local DR/DAR archive:

- `Agenda do Trabalho Digno` as a legislative package entity
- the canonical `Lei n.º 13/2023`
- the linked `Decreto-Lei n.º 53/2023`
- a parliamentary registry entry
- a reusable cross-corpus resolution

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
- `artifacts/entities/`: canonical topic anchors
- `artifacts/resolutions/`: summaries, crosswalks, and reusable syntheses

Do not let LLM-authored artifacts become the only surviving representation of source text.
Do not hand-edit derived index outputs. Rebuild them from source artifacts.

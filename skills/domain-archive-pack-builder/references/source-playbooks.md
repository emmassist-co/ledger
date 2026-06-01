# Source Playbooks

Source playbooks sit below the domain pack and above source-specific improvisation.

Use them to capture reusable source-shape behavior such as:

- official article-style sources
- consolidated legal views
- official FAQ portals
- annual value tables
- official registries

Each playbook should stay recipe-like. It should tell a future agent:

- what kind of source shape this is
- what navigation posture to use
- what the likely retrieval unit is
- what persistence posture is expected
- whether exact wording is usually important
- whether the family supports listing sync, direct document ingest, or both

For source families that publish canonical listings or feeds, the playbook should also make clear:

- where new official documents are discovered
- whether discovery is listing-driven, direct-document-only, or manual
- what direct document format is expected
- whether the archive can sync registry entries before full ingest

Do not use playbooks to:

- hardcode a site crawler
- bake source-specific selectors into Ledger core
- replace the domain pack

The domain pack chooses the source family. The playbook explains the generic shape of how that family behaves.

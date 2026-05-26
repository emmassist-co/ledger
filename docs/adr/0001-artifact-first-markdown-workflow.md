# Use an artifact-first Markdown workflow for transcript understanding

This project will process each parliamentary transcript into a filesystem workspace of Markdown and JSON artifacts, with section notes as the canonical intermediate representation and document-level views derived from those notes rather than from the raw PDF. We chose this over a graph-first or end-to-end prompt pipeline because the artifacts stay inspectable, regenerable, versionable, and easy to evolve later into search, verification, or graph-backed systems.

# Principles

Ledger is a recipe-first archive toolkit for agents.

## Core Position

- Ledger is not a monolithic ingestion engine.
- Ledger is not a bundle of source-specific adapters.
- Ledger is not a place to accumulate one-off archive logic.

Ledger should provide:

- archive workspace structure
- archive artifact contracts
- deterministic rebuild and verification primitives
- eval scaffolding and execution
- recipes and templates that help an agent create a thin archive-local adapter when a source needs one

## Recipe-First Rule

Prefer recipes, templates, and local generation over adding source-shaped logic to Ledger core.

Use Ledger core code only for behavior that is:

- structural
- repeatable
- deterministic
- useful across many archive types

Keep source-specific behavior:

- local to the archive workspace
- small
- generated from Ledger guidance when possible
- easy to inspect, replace, or delete

## Boundary

Ledger should own most of the archive workflow:

- scaffold
- persist
- rebuild
- verify
- evaluate

The agent should own the last-mile adaptation:

- inspect the source
- choose the retrieval unit
- fill in selectors, mappings, or extraction rules
- create tiny archive-local helpers only when needed

If building a new archive feels like writing a new software product, Ledger is still missing reusable primitives or recipes.

## Code Bias

Favor:

- small deterministic primitives
- recipe docs
- templates
- archive-local generated glue

Avoid:

- large universal crawlers
- source-specific core modules
- custom framework logic that tries to replace agent reasoning

## Quality Bar

New archives should be:

- mostly powered by Ledger
- adapted with thin local glue
- governed by explicit policy
- verifiable through deterministic checks
- honest about what is canonical, extracted, derived, or unknown

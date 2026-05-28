# Domain Pack Contract

Ledger domain packs are stronger than metadata and weaker than orchestration.

Use the pack to teach future agents:

- what matters for archive configuration in the domain
- which canonical source families belong in scope
- what retrieval units are meaningful
- what content should be persisted as durable archive knowledge
- when autonomous evidence gathering is allowed
- when the user must be asked for missing domain detail
- how strong support must be before decisive claims are allowed
- what target quality separates provisional answers from done-enough archive answers
- when freshness forces refresh before answering

Do not use the pack to:

- hardcode corpus-specific crawler logic
- embed a second orchestration framework beside Ledger
- duplicate the full generated recipe content inside prose docs

The pack contract should compile into:

- structured recipe files for machine-usable decisions
- archive-local guidance for future agents
- helper checks and templates for risky decisions
- starter eval posture for real question suites
- standardized archive-memory surfaces for coverage weakness, freshness, and replay learning

Every generated archive should inherit the same small cross-index practice layer:

- **What it must generate:** pack recipes, operator docs, helper templates, archive memory, eval posture
- **What it must remember:** known support gaps, provisional weak slices, partial topics, stale topics
- **What it must check:** coverage state, support hierarchy, pre-answer weakness, auto-expand policy, confirmation boundary
- **What it must prove:** direct-answer, expand-then-answer, ask-user, false-completion, and replay-style closure behavior

The pack should answer these questions clearly:

1. What source families are canonical for this domain?
2. What unit should an agent fetch or persist from each family?
3. When can the agent fetch more evidence on its own?
4. When should the agent stop and ask the user for domain facts?
5. What support level is enough for a decisive answer?
6. What target quality separates a provisional answer from a completed archive answer?
7. What must be refreshed before treating the answer as current?
8. How does the archive record suspected weakness before that weakness is fully confirmed?
9. How will the archive prove that a first-run expansion improved later runs?

If a pack cannot answer those questions, it is too weak.

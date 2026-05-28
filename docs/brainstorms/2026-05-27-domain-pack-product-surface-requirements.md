---
date: 2026-05-27
topic: domain-pack-product-surface
---

# Domain Pack Product Surface

## Summary

Define the Ledger domain pack as the main agent-facing contract for configuring and operating a high-accuracy archive in a bounded domain. A domain pack should encode what matters for archive configuration, persistence, confidence, freshness, and user-escalation rules, while still leaving reasoning and execution to the agent.

## Progress Snapshot

As of 2026-05-27, this direction has been partially proven in the repo rather than remaining only conceptual.

What has held up well:

- The domain pack is now meaningfully stronger than metadata and weaker than orchestration.
- Generated archive-local guidance is good enough that a normal agent can often operate the archive without repo archaeology.
- The pack can now express target-quality concepts such as `below_target`, `provisional`, and `auto_expand_when_below_target`.
- Known support gaps can be recorded locally and fed back into operator behavior through helper checks and evals.

What the live proof exposed:

- “Found something locally” is not the same as “support is strong enough.” This had to become an explicit contract, not an agent intuition.
- `ask_user` must be a first-class operator path with natural decision-record semantics; otherwise agents end up faking persistence-oriented fields.
- The value of the domain pack depends heavily on the archive carrying honest local self-knowledge in `coverage-ledger.yaml`.

What still needs work:

- The pack can guide expansion reliably for known gaps, but unknown weak slices are still discovered only when a real question exposes them.
- The archive still needs real content compounding, not just stronger decision surfaces. The `article 43` gap is the clearest current example.

---

## Problem Frame

Ledger's current direction is stronger in philosophy than in product surface. The repo already has recipes, generated operator guidance, verifier helpers, and archive-local conventions, but too much still depends on the agent improvising how to use them together.

If the domain pack stays mostly descriptive metadata, Ledger remains a toolkit that requires strong implicit judgment to operate well. If it becomes a full step-by-step controller, Ledger drifts away from the strategy of being a meta, agent-native archive kit. The missing shape is a domain pack that meaningfully constrains and assists the agent without replacing it.

---

## Key Decisions

- **Domain pack is stronger than metadata, weaker than orchestration.** The pack should encode decisions, thresholds, and helper surfaces the agent can use directly, but it should not become a rigid runtime or workflow engine.
- **Evidence gathering is autonomous by default.** When the pack says a topic is in-bounds, the agent should fetch more evidence and pursue canonical sources on its own rather than asking the user first.
- **User escalation is for missing domain detail, not routine retrieval.** The agent should ask the user when it lacks the domain-specific facts needed to give a confident enough answer, not when it merely lacks local evidence.
- **Broad domain packs are the default unit.** A pack may cover several canonical source families within one domain, while still allowing narrower subdomain packs where that improves quality or reuse.

---

## Requirements

- R1. A domain pack must define what is important for configuring an archive in its domain, including source families, retrieval units, confidence posture, and refresh behavior.
- R2. A domain pack must define what kinds of content should be persisted as durable archive knowledge and how the agent should decide whether newly consulted material is worth persisting.
- R3. A domain pack must define when the agent may autonomously gather more evidence or fetch more source material, and when it must stop and ask the user for more domain detail.
- R4. A domain pack must define what answer confidence threshold is acceptable for the domain and what should happen when the archive remains below that threshold.
- R5. A domain pack must define refresh policy for time-sensitive or version-sensitive content, including when stale content may still be used and when refresh is required before answering.
- R6. A domain pack must support multiple canonical source families within the same bounded domain without forcing one pack per source family.
- R7. A domain pack must be allowed to stay broad at the domain level while still allowing more specific subdomain packs to exist where needed.
- R8. A domain pack must generate archive-local operator guidance that tells an agent how to use the pack's rules in practice.
- R9. A domain pack must generate or connect to helper checks that constrain the agent at important decision points such as persistence, confidence, refresh, and expansion.
- R10. A domain pack must improve archive operation enough that agents rely less on bespoke corpus-specific code and less on undocumented improvisation.

---

## Actors

- A1. Domain expert configuring a bounded archive for agents.
- A2. Agent operating the archive to answer questions, gather evidence, persist useful material, and manage freshness.

---

## Key Flows

- F1. Configure a new archive from a domain pack.
  - **Trigger:** A domain expert wants agents to work inside a bounded domain with canonical sources.
  - **Actors:** A1, A2
  - **Outcome:** The archive is scaffolded with domain-specific rules for configuration, persistence, confidence, and refresh.

- F2. Answer a question with missing local support.
  - **Trigger:** A2 receives a question and local archive support is insufficient.
  - **Actors:** A2
  - **Outcome:** The agent autonomously gathers more evidence from in-bounds canonical sources, then answers if confidence becomes sufficient.

- F3. Escalate when domain detail is missing.
  - **Trigger:** A2 has enough source access but lacks the domain-specific facts needed for a confident answer.
  - **Actors:** A2, A1
  - **Outcome:** The agent asks the user for the missing detail rather than bluffing or escalating routine retrieval work.

- F4. Persist and refresh archive knowledge.
  - **Trigger:** A2 uses or discovers new material while answering or maintaining the archive.
  - **Actors:** A2
  - **Outcome:** The agent uses the domain pack to decide what to persist and whether refresh is required before treating the answer as reliable.

---

## Acceptance Examples

- AE1. **Covers R3, R4.** Given a question that is in-bounds but not fully covered locally, when the domain pack allows autonomous evidence gathering, then the agent fetches more evidence on its own instead of asking the user first.
- AE2. **Covers R3, R4.** Given a question where the agent has source access but lacks important domain-specific facts needed for a confident answer, when confidence remains below the pack's threshold, then the agent asks the user for the missing detail.
- AE3. **Covers R2, R9.** Given newly consulted source material, when the pack classifies it as reusable and durable, then the agent persists it rather than treating it as one-off scratch knowledge.
- AE4. **Covers R5, R9.** Given a time-sensitive topic, when the pack marks the relevant slice as stale or refresh-required, then the agent refreshes before treating the answer as settled.
- AE5. **Covers R6, R7.** Given a bounded domain that spans several canonical source families, when the domain pack is created, then it may define all of those families together without blocking more specific subdomain packs later.
- AE6. **Covers R8, R9, R10.** Given a newly scaffolded archive, when another agent starts operating it, then it can rely on archive-local guidance and helper checks instead of inventing corpus behavior from scratch.

---

## Success Criteria

- Domain packs materially reduce the amount of bespoke corpus-specific operating logic an agent needs to invent.
- Agents using a domain pack make more consistent decisions about persistence, confidence, and freshness.
- The boundary between autonomous evidence gathering and user escalation is clear enough that agents do not ask the user for routine retrieval work.
- Broad domain packs remain usable without preventing narrower subdomain specialization where it adds value.

---

## Scope Boundaries

### Deferred for later

- The exact generic helper script set a pack should generate or wrap.
- How packs should version or inherit from one another over time.
- How packs should be distributed or shared outside a single repo.

### Outside this product's identity

- Turning domain packs into a full runtime or rigid workflow controller.
- Requiring all archive operation decisions to be handled through bespoke parser-heavy code.
- Forcing users into one-pack-per-source-family as the only supported shape.

---

## Dependencies / Assumptions

- Ledger will continue to rely on agents as the main reasoning and execution layer rather than replacing them with a heavy orchestrator.
- The repository can support generated archive-local skills and helper surfaces as first-class outputs of a domain pack.
- Archive quality will depend heavily on domain-pack quality, so the pack contract must be treated as a product surface rather than a loose implementation detail.

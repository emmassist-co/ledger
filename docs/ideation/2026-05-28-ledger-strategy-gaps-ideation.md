---
date: 2026-05-28
topic: ledger-strategy-gaps
focus: strategy gaps, missing product surface, live metrics
mode: repo-grounded
---

# Ideation: Ledger Strategy Gaps

## Grounding Context

**Codebase Context**

Ledger's current strategy is clear: bounded archives built from canonical sources, grown through question-driven enrichment rather than full upfront indexing. The current strategic gap named in [STRATEGY.md](STRATEGY.md) is not "missing runtime" but three narrower failures: unknown weak slices are still discovered too late, live archive content closure is still manual after detection, and ordinary agents have not yet repeatedly proven `expand -> persist -> answer` without tester steering.

Fresh local proof on 2026-05-28 is stronger than the docs alone suggest, but still narrow:

- Live archive rebuild is clean at `165` documents and `100` links.
- `python3 archive-index/scripts/check_index_consistency.py` passes.
- `uv run python skills/archive-evals/scripts/run_archive_evals.py run archive-index` is `7/7` green.
- Answer-quality pass rate is `1.0`, with `5` `direct_answer` scenarios and `2` `expand_then_answer` scenarios.
- Retrieval metrics are strong but not complete proof of product quality: `hit@k 1.0`, `precision@k 0.371429`, `recall@k 0.666667`, `mrr@k 1.0`, `ndcg@k 0.911285`.
- Trajectory metrics are clean: completion pass rate `1.0`, clean pass rate `1.0`, drift rate `0.0`, median trace steps `5`, median verifier calls `2`.
- The current coverage ledger shows `2` known `support_gaps`, `0` `partial_topics`, `0` `stale_topics`, and `3` seen source families.
- A live helper check still shows a binary posture: `artigo 148 sistema de pontos` returns `below_target` and `suggested_action: expand`, while `article 43 resident gains` now returns `clear`.

The benchmark surface is also clean but thin. [examples/benchmark-summary.md](examples/benchmark-summary.md) shows `4` example suites all passing thresholds, but one of them still has visible instability: `dr-cirs-reinvestment` has `clean 0.75` and `drift 0.25`.

**Past Learnings**

- The repo has already hardened the domain-pack/helper-check layer enough to shape a live archive and enforce known below-target expansion.
- The new product leverage is in compounding self-knowledge and live proof, not in adding a heavier runtime layer.

**External Context**

- [Self-RAG](https://arxiv.org/abs/2310.11511) and [CRAG](https://arxiv.org/abs/2401.15884) both push the same adjacent idea: retrieval should be followed by quality estimation and corrective action, not treated as sufficient by default.
- OpenAI's [evals guide](https://platform.openai.com/docs/guides/evals?lang=javascript) and [hallucination writeup](https://openai.com/index/why-language-models-hallucinate) reinforce the same operational lesson: reliability comes from explicit task-shaped evals and rewarding justified uncertainty rather than confident guessing.

## Topic Axes

- Weak-slice self-detection
- Closure and compounding
- Eval realism
- Product economics
- Transfer beyond the flagship archive

## Ranked Ideas

### 1. Make Unknown Weak-Slice Detection the Next Product Center
**Description:** Treat the pre-answer weak-slice detector as the next flagship Ledger capability, not just a safety patch. The product move is to let the archive classify `clear`, `known_below_target`, and `likely_below_target` before it commits to an answer, and to persist new suspicion immediately so the archive's self-knowledge compounds after first contact. This would turn the current binary live behavior into a genuine retrieval-quality judgment layer.
**Axis:** Weak-slice self-detection
**Basis:** `direct:` [STRATEGY.md](STRATEGY.md) names "making unknown weak slices discoverable faster through real use" as the first remaining gap; the live helper still only distinguishes known gaps (`artigo 148`) from clear slices (`article 43`). `external:` [CRAG](https://arxiv.org/abs/2401.15884) centers retrieval-quality evaluation plus corrective action rather than trusting first retrieval.
**Rationale:** This is the smallest missing capability that changes product truth. Today Ledger can honor known weakness; it still cannot notice new likely weakness early enough to change the path. Fixing that moves the project from "good manual archive discipline" toward "archives that become safer through use."
**Downsides:** High false-positive bias could make the system feel conservative and expansion-heavy until the signal model is tuned.
**Confidence:** 94%
**Complexity:** Medium
**Status:** Unexplored

### 2. Add Replay-Based Closure Evals and a Second-Run Lift Metric
**Description:** Add a benchmark family where the first run starts from a real gap, forces expansion and persistence, and the second run measures whether the same or adjacent question becomes a clean local hit. Track this as a new metric, such as `second_run_local_hit_rate` or `closure_lift`, alongside current answer-quality metrics. The point is to measure whether Ledger actually gets cheaper and better after work, not just whether one guided run succeeds.
**Axis:** Closure and compounding
**Basis:** `direct:` the current live eval run is `7/7` pass, but only `2` scenarios are `expand_then_answer`, and none of the surfaced metrics prove replay improvement. `direct:` [STRATEGY.md](STRATEGY.md) explicitly calls out the unproven state of repeated `expand -> persist -> answer`. `reasoned:` if the archive does not measurably improve on the second pass, it is not compounding knowledge, only performing one-off retrieval work.
**Rationale:** This would add the missing product metric between answer quality and archive growth. It answers the strategic question "did the archive learn?" rather than just "did the evaluator accept the answer?"
**Downsides:** Requires more careful scenario design and reset discipline than current single-run evals.
**Confidence:** 91%
**Complexity:** Medium
**Status:** Unexplored

### 3. Build an Exception-Completeness Challenge Set
**Description:** Create a focused eval family for "relevant base rule, missing decisive exception" failures, especially in statutory and tax archives. Measure a new failure-facing metric such as `false_completion_rate`, meaning the share of runs that answered too confidently from a locally relevant but incomplete slice. This would give Ledger a product-grade test for the exact failure mode that matters most in legal archives.
**Axis:** Eval realism
**Basis:** `direct:` the motivating failure in the current brainstorm is an article that looks right but omits the exception that determines the answer. `direct:` current answer metrics are perfect on `7` scenarios, which means the suite is not yet adversarial enough to expose this miss class. `external:` [Self-RAG](https://arxiv.org/abs/2310.11511) emphasizes self-reflection precisely because retrieved support can appear relevant while still being insufficient.
**Rationale:** A system that only tests direct hits and known gaps will overestimate safety. Exception-sensitive challenge cases are the fastest way to force the archive to prove that it knows when it does not know enough.
**Downsides:** The first version will likely be domain-skewed toward legal/tax archives, so the metric should not be over-generalized too early.
**Confidence:** 89%
**Complexity:** Low
**Status:** Unexplored

### 4. Add Archive Growth Economics to the Product Surface
**Description:** Start measuring whether archive growth is economically efficient, not just correct. Add metrics like `durable_slices_added`, `reused_slice_rate`, `support_gap_burndown`, `documents_per_green_scenario`, and a simple `cost_to_close_gap` estimate for each new canonical slice. Today the archive has `165` documents, `100` links, and only `7` live eval scenarios; that is enough to prove viability, but not enough to explain whether the archive is growing efficiently.
**Axis:** Product economics
**Basis:** `direct:` current proof surfaces are answer-quality, retrieval quality, and index consistency; none of them say whether archive growth is getting cheaper or noisier over time. `reasoned:` once the archive moves beyond one flagship corpus, economics will matter as much as correctness because domain experts are effectively deciding whether to invest in compounding local knowledge or keep doing ad hoc retrieval.
**Rationale:** This gives Ledger a product-level story about why bounded archives beat parser-heavy upfront ingestion or repeated one-off retrieval. Without economics, the project may prove that it can grow archives, but not that it should.
**Downsides:** These metrics are easy to over-instrument and may distract from the more urgent safety and closure gaps if introduced too early.
**Confidence:** 78%
**Complexity:** Medium
**Status:** Unexplored

### 5. Prove Transfer with a Second Non-Legal Flagship Archive
**Description:** Stand up a second flagship archive in a different canonical-source domain and measure how much of the current solution transfers unchanged. Track numbers like `shared_pack_outputs`, `new helper checks required`, `time_to_first_green_eval`, and `manual archive-specific code added`. The product story gets much stronger if Ledger can show that the current legal/tax archive is not a special case.
**Axis:** Transfer beyond the flagship archive
**Basis:** `direct:` [STRATEGY.md](STRATEGY.md) explicitly rejects a legal-only identity. `direct:` the current coverage ledger already spans `3` source families, but the actual proving ground is still one flagship archive. `reasoned:` without a second domain, it is too easy to mistake a strong archive for a reusable archive-building system.
**Rationale:** This is the sharpest test of whether Ledger is really a meta-system. It would also force clarity about which pieces are pack outputs, which are source-playbook patterns, and which are still hidden domain assumptions.
**Downsides:** Pulls attention away from the current flagship archive's unresolved closure gaps, so it likely belongs after the weak-slice and closure metrics work.
**Confidence:** 74%
**Complexity:** High
**Status:** Unexplored

### 6. Add Ordinary-Agent Soak Runs as a First-Class Benchmark
**Description:** Create a benchmark lane where a normal agent operates the live archive with minimal tester shaping over repeated question sessions. Measure `autonomous_closure_rate`, `unnecessary_expand_rate`, `ask_user_correctness_rate`, and `persisted_reuse_rate`. This would sit between deterministic evals and production use and answer the strategy question about whether the product works for ordinary agents, not just for careful builders.
**Axis:** Closure and compounding
**Basis:** `direct:` the current strategy gap explicitly says ordinary agents have not yet repeatedly proven `expand -> persist -> answer` without tester steering. `direct:` current evals are clean and useful, but they are still curated. `external:` OpenAI's [evals guide](https://platform.openai.com/docs/guides/evals?lang=javascript) argues for task-specific evaluation loops that mirror real use rather than only unit-style checks.
**Rationale:** Ledger's real customer is not the evaluator; it is the agent and domain expert working through live questions. Soak runs make that customer visible in the proof surface.
**Downsides:** Harder to keep deterministic and more expensive to run than the current archive-eval suite.
**Confidence:** 83%
**Complexity:** High
**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Build a heavyweight runtime orchestrator | Not grounded in current strategy; the repo explicitly moved away from "we need a runtime" as the main gap. |
| 2 | Fully pre-index each canonical source universe | Subject-replacement; it abandons the bounded, question-driven archive identity that Ledger is trying to prove. |
| 3 | Build a polished archive UI first | Too expensive relative to likely value; the current strategic gaps are in self-knowledge and proof, not presentation. |
| 4 | Fine-tune a model specifically for archive operation | Unjustified; it hides workflow and evidence-shaping failures behind model adaptation instead of fixing product mechanics. |
| 5 | Add many more retrieval-only benchmark examples | Duplicates stronger ideas; the missing proof is closure, exception completeness, and transfer, not raw retrieval coverage alone. |

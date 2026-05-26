# Parliament Transcript Processing

This context covers the extraction, structuring, and explanation of Portuguese parliamentary transcript documents into reusable reading artifacts. It exists to keep the workflow artifact-first, inspectable, and grounded in the source transcript.

## Language

**Document**:
A single parliamentary source file and its generated artifact workspace under `documents/<document-id>/`.
_Avoid_: file, case, record

**Episode**:
A primary semantically bounded reading unit for one parliamentary sitting, such as a solemn session, mandate vote, political declaration block, or closing note.
_Avoid_: chunk, slice, token window

**Episode Note**:
The primary durable reading artifact for one episode, stored as Markdown with YAML frontmatter, backlinks, generation metadata, and evidence pointers.
_Avoid_: summary, blob, embedding note

**Section**:
A lower-level segment detected during parsing that may be used internally to assemble episodes, but is not the primary product-facing reading unit.
_Avoid_: final note, public summary unit

**Claim**:
A statement in the transcript that may require verification because it is statistical, legal, historical, programmatic, or otherwise disputable.
_Avoid_: opinion, hot take, allegation

**Reference**:
An external concept, programme, report, legal instrument, or source candidate that would help interpret or verify a section or claim.
_Avoid_: citation, link, browse result

**Generation Event**:
An append-only record of one artifact generation attempt, including model, prompt template, token usage, and estimated cost.
_Avoid_: opaque log line, trace blob

**View**:
A document-level explanation generated from section notes and reference artifacts for a specific audience complexity level.
_Avoid_: summary mode, answer

**Evidence Pointer**:
A note-level pointer back to the source transcript, anchored to one or more pages and a short description of the supporting passage.
_Avoid_: quote dump, raw offset

**Resolver**:
An optional downstream step that fetches and summarizes authoritative external sources for normalized references.
_Avoid_: crawler, search agent

## Flagged Ambiguities

- **Summary vs View**: A summary is free-form output language; a view is a structured, document-level artifact generated from approved intermediate notes.
- **Claim vs Fact**: A fact is established by the transcript as an event or utterance that occurred; a claim is the content asserted by a speaker and may remain unverified.

## Example Dialogue

Developer: "Should level 2 read directly from the PDF for better context?"

Domain expert: "No. The view reads from the episode notes. The episode note is the durable artifact."

Developer: "If a deputy says a statistic, is that a fact?"

Domain expert: "It is a claim. The fact is that the deputy said it in that section."

Developer: "Where do we keep the OECD item we may want to check later?"

Domain expert: "As a reference, linked from the relevant claim and section note."

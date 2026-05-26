---
name: process-parliamentary-transcript
description: Use when processing a Portuguese parliamentary transcript PDF into reusable notes, references, and explanation views in this repository
---

# Process Parliamentary Transcript

Run the repo workflow instead of summarizing directly from the PDF.

## Rules

- Treat `sections/*.md` as the canonical intermediate artifacts.
- Follow the chain: PDF -> extracted Markdown -> sections -> section notes -> claims/references -> views.
- Do not generate document summaries directly from the raw PDF when the pipeline can run.
- Keep content artifacts in Portuguese unless asked otherwise.

## Command

```bash
uv run parliament process /path/to/DAR-I-087.pdf
```

## Inspection Order

1. Check `source/extracted_text.md`.
2. Check `sections/*.md`.
3. Check `references/claims-to-check.md` and `references/external-references.md`.
4. Check `views/*.md`.

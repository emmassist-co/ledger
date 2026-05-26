---
name: section-detector
description: Use when splitting parliamentary transcript extraction into semantic sections such as summaries, declarations, vote blocks, and closing notes
---

# Section Detector

Prefer semantic transcript boundaries over token windows.

## Rules

- Use transcript cues such as `SUMÁRIO`, `DECLARAÇÃO POLÍTICA`, `VOTAÇÃO`, solemn-session openings, and closing notes.
- Only split long sections into parts when size makes them unwieldy.
- Keep stable section IDs and page ranges.

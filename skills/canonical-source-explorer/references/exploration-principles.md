# Exploration Principles

## Cheap-first ladder

1. direct file or feed probe
2. plain HTTP page fetch
3. page-shape classification
4. canonical adjacent-surface discovery
5. browser capture only when necessary

## Discovery vs archive truth

Discovery artifacts answer:

- what surfaces exist?
- which ones are stable?
- which ones look canonical?
- which ones are likely noise?

Archive artifacts answer:

- what source was actually used?
- what was persisted?
- what support strength does the answer have?

Do not blur those layers.

## Preferred canonical source shapes

In rough order of preference:

1. feed surfaces
2. raw file hosts
3. stable canonical detail pages
4. stable consolidated views
5. clean listing pages
6. hidden APIs discovered from capture
7. browser-only interactive flows

## Promotion bar

A discovered surface is ready to become a source-family rule only if it is:

- canonical or tightly coupled to the canonical family
- cheap to replay
- stable enough to test
- specific enough to reduce operator improvisation

If it fails that bar, keep it as exploration evidence only.

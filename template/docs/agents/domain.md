# Domain docs

Domain documents the engineering skills read **before** exploring the codebase.
(mattpocock/skills seed, MIT.)

## Before exploring, read these

- Root **`CONTEXT.md`**: the glossary. No implementation detail.
- **`docs/adr/`**: the ADRs for the area you touch.

If either is missing, move on quietly. Do not report it and do not create it
ahead of time; `/domain-modeling` (called from `/grill-with-docs`) creates them
when a term or decision is actually settled.

## File structure

single-context (this repository):

```text
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-….md
│   └── 0002-….md
└── src/
```

Write an ADR only when all three hold: **hard to reverse**, **surprising without
context**, **the result of a real trade-off**.

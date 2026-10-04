# CLAUDE.md — Floorspec (the standard)

Foreman project **FLR** (shared with the reference implementation in `../d3-floorspec`).
Start a session with `/start-development FLR`. Documents: `foreman://FLR/overview`,
`foreman://FLR/architecture`, `foreman://FLR/data_model`, `foreman://FLR/api_contract`.

## What lives here
- `spec/core`, `spec/ops`, `spec/rules` — normative Markdown; every MUST tagged `{#FS-<SPEC>-<n.n.n> MUST}`
- `schema/` — hand-written JSON Schema 2020-12 (the normative schema; TS types are generated in d3-floorspec)
- `conformance/` — test files + expected outputs; CI fails if any MUST lacks a test (FLR-ADR-009)
- `registry/` — extension proposals and FS_ extensions (FLR-ADR-007)
- `rules/` — rule packs, CC BY 4.0 data (FLR-ADR-011)

## Non-negotiables
- Lengths are integers in base units of 1/1280 mm (FLR-ADR-004). No floats in normative outputs.
- Canonical JSON form must be byte-identical across writers.
- Never copy code text or tables into rules; never scrape ICC/NFPA viewers.
- Findings never say "compliant".
- Stay 0.x Draft until the 1.0 criteria are met (FLR-ADR-017).
- No time estimates anywhere.

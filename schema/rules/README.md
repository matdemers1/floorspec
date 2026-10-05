# schema/rules

The JSON Schemas (2020-12) of Floorspec Rules: the evaluation request, a rule pack and its rule
records, a jurisdiction profile, and the report an evaluator returns with its findings. They are
**normative** (FLR-ADR-006): a request the request schema rejects is `FS-RULES-001`, a profile the
profile schema rejects `FS-RULES-002`, a pack the pack schema rejects `FS-RULES-004`.

## Files

One directory per draft: **Rules 0.1** is in [`0.1/`](0.1/), as published at `8a99d02`, and **Rules
0.2**, the current draft (`spec/rules/`), in [`0.2/`](0.2/) — 0.1's files with their `$id`s moved and
`floorspecRules` declaring `"0.2"` (`defs.schema.json`).

| File | Describes | Spec |
|---|---|---|
| `request.schema.json` | the evaluation request: `packs`, `profile`, `units` - each pack and the profile are checked by their own schemas | 1.1 |
| `pack.schema.json` | a rule pack: name, version, CC BY 4.0, rules by ID, coverage | 2 |
| `rule.schema.json` | a rule record: citation, paraphrase, applicability, selection, requirement, exceptions, severity, provenance | 3 |
| `profile.schema.json` | a jurisdiction profile: adoptions with effective dates, `asOf`, packs by version range, amendments | 10 |
| `report.schema.json` | the report: notice, diagnostics, evaluated and not evaluated rules, coverage, findings | 9.1, 11 |
| `finding.schema.json` | a finding, its measured conditions, targets and shapes, and a measure result (`#/$defs/measureResult`) | 9.2 - 9.4, 4.7 |
| `defs.schema.json` | what they share: codes, editions, sections, dates, the test grammar of 3.8 | |

What a schema cannot say is checked by an evaluator: whether a rule is well typed (3.9), whether a
pack's or a profile's text says that a design meets a code (2.5, 10.1), and whether a profile adopts
one code twice on one date (10.1). `pnpm schema:check` holds the schemas to the suite
(`conformance/rules/0.1/` and `0.2/`, each with its own draft's schemas) and to the default profile
of 10.6.

Each file is published at its `$id`, `https://d3cloud.io/floorspec/schema/rules/<draft>/<file>`.

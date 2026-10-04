# schema/core

The JSON Schema (2020-12) of the Floorspec Core document. It is **normative** (FLR-ADR-006): it is
written by hand, and the TypeScript types in D3 Floorspec are generated from it, never the reverse.

## Files

Each draft has its own directory. Core 0.1 is in [`0.1/`](0.1/); start at `floorspec.schema.json`.

| File | Describes | Spec |
|---|---|---|
| `floorspec.schema.json` | the document: its members and its collections | 1.1, 1.2, 1.6, 1.7 |
| `defs.schema.json` | length, positive and non-negative length, angle, point, polygon, ID, reference, extension name, `extensions`, `extras`, `name` | 1.4, 1.6, 1.7, 2.1, 2.4, 2.6, 3.1, 3.2 |
| `project.schema.json`, `site.schema.json` | the project and its site | 1.8 |
| `building.schema.json`, `level.schema.json` | buildings and levels | 1.8 |
| `junction.schema.json` | junctions and their join overrides | 5.1, 5.8 |
| `wall.schema.json`, `separator.schema.json` | walls (with `base` and `top`) and separators | 5.2, 5.9 |
| `layer.schema.json` | a layer and a `layers` array | 4.3, 8.3 |
| `opening.schema.json` | openings | 7.1 |
| `room.schema.json` | rooms and room functions | 4.1, 4.2, 6.5 |
| `slab.schema.json` | slabs | 6.7 |
| `type.schema.json` | wall, door and window types, discriminated by `kind` | 8.1, 8.3, 8.4 |
| `material.schema.json`, `asset.schema.json` | materials and assets | 8.5, 8.6 |

Each file is published at its `$id`:

```text
https://d3cloud.io/floorspec/schema/core/0.1/<file>
```

for example `https://d3cloud.io/floorspec/schema/core/0.1/floorspec.schema.json`. The files refer
to each other by relative `$ref`. **A published file is immutable**: a change to the schema is a
new draft, in a new directory, at a new URL.

## What the schema checks — and what it does not

The schema is tier 3 of chapter 10: a document that does not match it gets `FS-SCH-001`. It
encodes exactly the rules that the catalogue (10.4) files under `FS-SCH-001` — closed objects,
required members, integer lengths and angles and their ranges, ID and extension-name patterns,
the room and layer function taxonomies, the shapes of `top`, `join` and the types, and the asset
rules — and nothing else.

It checks **structure only**. The invariants of chapter 10 — that references resolve to the right
collection and kind, that IDs are unique across collections, that extensions are declared in
`extensionsUsed`, that polygons are simple, that the wall graph is planar, that rooms and openings
fit — cannot be expressed in JSON Schema, and need a validator (`FS-INV-*`). A document that
matches the schema can still be invalid.

Two things a validator does before it applies the schema:

- **Parsing and document tiers first.** Malformed JSON, duplicate members and unpaired
  surrogates (`FS-JSON-*`), and an unknown version or required extension (`FS-DOC-*`), are reported
  before the schema is applied (10.3).
- **Lexical integers.** A length or an angle is a JSON integer, written without a fraction or an
  exponent (2.1, 2.4). JSON Schema sees only the parsed number, for which `1.0` and `1e3` are
  integers. A validator maps every number written with a fraction or an exponent to a value that
  is not a number before validating — `tools/schema.ts` uses `NaN` — so that it fails wherever
  core expects an integer and passes inside `extras` and extension data, where any JSON number is
  allowed (9.1).

`format: "uri"` on an asset's `uri` is an annotation in JSON Schema 2020-12; the `pattern` beside
it is what every validator checks.

## Constant defaults

The `default` keywords are exactly the **constant** defaults of the spec's tables (1.5), and the
reference canonicalizer reads them as its table of constant defaults (9.2 step 1). A member whose
default is derived (a wall's `top`, `base.level`) and every typed property (a wall's `layers`, an
opening's `width`, `height` and `sill`) carries no `default`. Never add one for documentation:
`tools/check-schema.test.ts` pins the full list.

## Checking it

```sh
pnpm schema:check   # compile every file (ajv, strict); check every default; check the conformance suite
pnpm test           # tools/check-schema.test.ts: documents the schema must accept and reject
```

`pnpm schema:check` runs every conformance test in `conformance/core/0.1/` whose input is
well-formed JSON and whose expected diagnostics have no `FS-JSON-` or `FS-DOC-` code: the schema
must reject the input when the expected diagnostics are exactly `[FS-SCH-001]`, and accept it
otherwise.

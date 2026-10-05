# schema/core

The JSON Schema (2020-12) of the Floorspec Core document. It is **normative** (FLR-ADR-006): it is
written by hand, and the TypeScript types in D3 Floorspec are generated from it, never the reverse.

## Files

Each draft has its own directory: Core 0.1 is in [`0.1/`](0.1/), Core 0.2 in [`0.2/`](0.2/), and
Core 0.3 — the current draft — in [`0.3/`](0.3/). Start at `floorspec.schema.json`. The 0.2 files
are the 0.1 files copied and changed, plus five new ones, and the 0.3 files are the 0.2 files
copied, with ten changed and three new (`roof.schema.json`, `stair.schema.json`, `finish.schema.json`); the table lists 0.3's.

| File | Describes | Spec |
|---|---|---|
| `floorspec.schema.json` | the document: its members and its collections | 1.1, 1.2, 1.6, 1.7 |
| `defs.schema.json` | length, positive and non-negative length, angle, point, polygon, ID, reference, extension name, `extensions`, `extras`, `name` | 1.4, 1.6, 1.7, 2.1, 2.4, 2.6, 3.1, 3.2 |
| `project.schema.json`, `site.schema.json` | the project and its site | 1.8 |
| `building.schema.json`, `level.schema.json` | buildings and levels, with a level's floor thickness and ceiling height (0.3) | 1.8 |
| `junction.schema.json` | junctions and their join overrides | 5.1, 5.8 |
| `wall.schema.json`, `separator.schema.json` | walls (with `base` and `top`) and separators | 5.2, 5.9 |
| `layer.schema.json` | a layer and a `layers` array | 4.3, 8.3 |
| `opening.schema.json` | openings, with their own clear opening (0.3) | 7.1 |
| `room.schema.json` | rooms and room functions, with a room's floor and its flat, tray or vaulted ceiling (0.3) | 4.1, 4.2, 6.5, 15.1, 15.2 |
| `slab.schema.json` | slabs, with their purpose (0.3) | 6.7 |
| `roof.schema.json` | roofs and their edges (0.3) | 16.1 |
| `type.schema.json` | wall, door and window types, discriminated by `kind`; a door's or window's operation and clear opening (0.3) | 8.1, 8.3, 8.4 |
| `material.schema.json`, `asset.schema.json` | materials, with their metallic, roughness and texture maps (0.3), and assets, with their byte length (0.3) | 8.5, 8.6, 18.1, 18.2, 18.4 |
| `finish.schema.json` | a wall's `finishes`: its face finishes and their regions (0.3) | 18.5 |
| `program.schema.json` | the program, its items and adjacencies (0.2) | 11.1, 11.2 |
| `extension.schema.json` | declarations in `extensionsUsed`, top-level extension data, collections and extension elements (0.2) | 12.1, 12.5 |
| `fallback.schema.json` | an extension element's fallback (0.2) | 12.6 |
| `host.schema.json` | the three forms of a host (0.2) | 13.3 |
| `clearance.schema.json` | a `clearances` object and its envelopes (0.2) | 13.5 |
| `stair.schema.json` | stairs: their forms and handrails (0.3) | 17.1, 17.2 |

`defs.schema.json` gains, in 0.2, `triple`, `box`, `area`, `angleHalfOpen`, `collectionName` and
`httpsUri`; `room.schema.json` gains `brief`, and `type.schema.json` gains `clearances` on door and
window types. In 0.3, `defs.schema.json` gains `clearOpening` and `doorClearOpening`,
`type.schema.json` gains `operation` and `clearOpening` on door and window types,
`opening.schema.json` gains `clearOpening`, and `floorspec.schema.json` declares `"0.3"`; for
floors, ceilings and slabs (chapter 15), `defs.schema.json` gains `pitch`, `level.schema.json`
gains `floorThickness` and `ceilingHeight`, `room.schema.json` gains `floor` and `ceiling`, and
`slab.schema.json` gains `purpose`; for roofs (chapter 16), `roof.schema.json` is new, and
`floorspec.schema.json` gains the `roofs` collection; for stairs (chapter 17), `stair.schema.json` is
new, and `floorspec.schema.json` gains the `stairs` collection; for materials and finishes (chapter
18), `material.schema.json` gains `metallic` and `roughness` and a texture's `normal`,
`metallicRoughness` and `occlusion` maps, `offset` and `rotation` (its `asset` no longer required, so
long as it has one map), `asset.schema.json` gains `byteLength`, `finish.schema.json` is new, and
`wall.schema.json` gains `finishes`.

The registry entry of an extension (Core 0.2, 12.2) has its own schema,
[`../registry/0.1/extension.schema.json`](../registry/0.1/extension.schema.json), published at
`https://d3cloud.io/floorspec/schema/registry/0.1/extension.schema.json`.

Each file is published at its `$id`:

```text
https://d3cloud.io/floorspec/schema/core/<draft>/<file>
```

for example `https://d3cloud.io/floorspec/schema/core/0.2/floorspec.schema.json`. The files refer
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
- **The declared draft's schema.** A reader of 0.3 applies 0.1's schema to a document that
  declares `"0.1"`, 0.2's to one that declares `"0.2"`, and 0.3's to every other (1.2.6).
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

`pnpm schema:check` runs every conformance test in `conformance/core/0.1/` (against 0.1's schema),
`conformance/core/0.2/` (as a 0.2 reader would) and `conformance/core/0.3/` (as a 0.3 reader would) whose input is well-formed JSON and whose
expected diagnostics have no `FS-CFG-`, `FS-JSON-` or `FS-DOC-` code: the schema must reject the
input when the expected diagnostics are exactly `[FS-SCH-001]`, and accept it otherwise. Every
`registry.json` of the 0.2 and 0.3 suites must match the registry entry schema, unless its test expects
`FS-CFG-001`. `tools/check-schema-02.test.ts` pins 0.2's new defaults and edges, and
`tools/check-schema-03.test.ts` 0.3's. Of the members 0.3 adds, only these have constant defaults:
a room's `floor` (`{}`) and its `offset` (`0`), a room's `ceiling` (`{ "kind": "flat" }`) and a
vault's `slopes` (`"both"`); and for chapter 18, a texture's `offset` (`[0, 0]`) and `rotation` (`0`),
a wall's `finishes` and each face finish (`{}`) and a face's `regions` (`[]`). A material's `metallic`
and `roughness` take their map's value when absent, and a face's `material` its room's or its layer's,
so neither has a `default`; nor does an asset's `byteLength`, which is not declared when absent. An absent operation is not declared, a clear opening is a typed
property (8.2), and a level's `floorThickness` and `ceilingHeight`, a floor's `thickness` and a
ceiling's `height` have derived defaults (15.1, 15.2), so none of them carries a `default`.

Extension elements are extension data, which the canonical form never changes (9.2), so
`host.schema.json`, `fallback.schema.json`, `clearance.schema.json` and `extension.schema.json`
carry no `default` keyword: a `rotation` that is absent is 0, but a canonicalizer does not omit one
written as 0.

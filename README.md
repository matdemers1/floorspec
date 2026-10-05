# Floorspec

**An open standard for describing houses as code.**

Floorspec is a parametric, typed description of a house — levels, walls on a junction graph,
openings hosted on walls, rooms derived from walls, roofs, stairs, materials, building systems —
that people and AI agents can read, edit, validate and render in 2D and 3D, exactly and
interoperably.

> **Status: 0.x Draft.** No compatibility promise until 1.0.

| Specification | What it defines |
|---|---|
| [Floorspec Core](spec/core/) | the document, kinds, units, geometry semantics, invariants, extensions |
| [Floorspec Ops](spec/ops/) | the normative vocabulary of edit operations |
| [Floorspec Rules](spec/rules/) | advisory building-code rules, findings and jurisdiction profiles |

- **Schemas** — JSON Schema 2020-12 under [`schema/`](schema/), published at d3cloud.io/floorspec/schema/
- **Conformance** — every mandatory statement has at least one test under [`conformance/`](conformance/)
- **Extensions** — `FS_` official, `EXT_` multi-implementer, vendor prefixes; see [`registry/`](registry/)
- **Rule packs** — CC BY 4.0 data with citations, never code text; see [`rules/`](rules/)

Published at **https://d3cloud.io/floorspec**. Reference implementation: [D3 Floorspec](https://github.com/matdemers1/d3-floorspec).

## Licence

Spec text and rule packs: CC BY 4.0 ([LICENSE-SPEC](LICENSE-SPEC)). Schemas, conformance suite and tooling: Apache-2.0 ([LICENSE](LICENSE)). The FS_furniture starter library (`registry/FS_furniture/library/`): CC0 1.0.

Floorspec findings are advisory. They are not a plan review, and the authority having jurisdiction decides.

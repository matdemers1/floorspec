# Floorspec Ops

The normative specification of edits to a Floorspec document — **Draft 0.3**, operating on Core 0.3
documents (and so on 0.2 and 0.1 documents), versioned independently of Core (FLR-ADR-008). Ops
0.1 is published from commit `3bf4f35` and Ops 0.2 from `6f9bc07`; chapter 0 (0.4) says what each
later draft adds and changes. Ops 0.3's requests are Ops 0.2's and may add a roof: `schema/ops/0.3/`.

| Chapter | |
|---|---|
| [0. Conventions](00-conventions.md) | what Ops is, the applier, elements (program items and extension elements too), changes from 0.2 and from 0.1, what this draft does not cover |
| [1. Operations, batches and transactions](01-transactions.md) | the request, the six-step transaction, the result, the echo, minting IDs, the inverse |
| [2. Primitive operations](02-primitives.md) | addElement and its shorthands, removeElement and cascades, setProperty, unsetProperty, moveJunction, setAdjacency, removeAdjacency, hosted elements following their hosts |
| [3. References](03-references.md) | lengths in feet-inches-fractions and metric, points, vectors, selectors (program items too), sides, positions, areas |
| [4. Composite operations](04-composites.md) | drawWall, moveWall, moveRoom, resizeRoom, addOpening, moveOpening, addRoom, setRoomFinish, setRoomBrief, removeWall, addLevel, addProgramItem, placeElement, moveElement |
| [5. Normalization](05-normalization.md) | merging junctions, planarizing by snap rounding, re-hosting openings and hosted elements, join cleanup |
| [6. Locks](06-locks.md) | element, length and distance locks |
| [7. Diagnostics](07-diagnostics.md) | the FS-OPS catalogue |

Conformance: `conformance/ops/0.3/` — a document A, a request, and the expected result. The Ops 0.1
and 0.2 suites, `conformance/ops/0.1/` and `conformance/ops/0.2/`, are kept as they were published.

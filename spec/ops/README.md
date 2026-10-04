# Floorspec Ops

The normative specification of edits to a Floorspec document — **Draft 0.1**, versioned
independently of Core (FLR-ADR-008).

| Chapter | |
|---|---|
| [0. Conventions](00-conventions.md) | what Ops is, the applier, what this draft does not cover |
| [1. Operations, batches and transactions](01-transactions.md) | the request, the six-step transaction, the result, the echo, minting IDs, the inverse |
| [2. Primitive operations](02-primitives.md) | addElement and its shorthands, removeElement and cascades, setProperty, unsetProperty, moveJunction |
| [3. References](03-references.md) | lengths in feet-inches-fractions and metric, points, vectors, selectors, sides, positions |
| [4. Composite operations](04-composites.md) | drawWall, moveWall, moveRoom, resizeRoom, addOpening, addRoom, setRoomFinish, removeWall |
| [5. Normalization](05-normalization.md) | merging junctions, planarizing by snap rounding, join cleanup |
| [6. Locks](06-locks.md) | element, length and distance locks |
| [7. Diagnostics](07-diagnostics.md) | the FS-OPS catalogue |

Conformance: `conformance/ops/0.1/` — a document A, a request, and the expected result.

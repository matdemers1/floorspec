# schema/ops

The JSON Schema (2020-12) of a Floorspec Ops apply request. It is **normative** (FLR-ADR-006): a
request it rejects is malformed, and an applier rejects it with `FS-OPS-001` (1.1.1).

## Files

Ops 0.1 is in [`0.1/`](0.1/); start at `request.schema.json`.

| File | Describes | Spec |
|---|---|---|
| `request.schema.json` | the apply request: `batch`, and `context` with its `locks` and `retired` IDs | 1.1, 6.1 |
| `operation.schema.json` | one operation: a union on `op` over the eight primitives and shorthands and the ten composites, each a closed object with exactly the members its definition lists | 2, 4 |
| `reference.schema.json` | the JSON forms of the reference grammar: length, point, vector, position, selector, a new ID, element content | 3, 1.5 |

Each file is published at its `$id`, `https://d3cloud.io/floorspec/schema/ops/0.1/<file>`. A
published file is immutable: a change is a new draft, in a new directory.

## What the schema checks

Shape only: which operations exist, which members each has, and the JSON type of every member an
operation reads - a length is an integer or a string, a point is `[x, y]` of lengths or a string, a
`side` is one of four words. Whether a string matches the reference grammar (`FS-OPS-012`), whether
a selector matches one element (`FS-OPS-003`, `FS-OPS-004`), and whether the edited document is
valid are decided by the applier. A member an operation only passes into an element - a wall's
`type`, an opening's `hinge`, `setProperty`'s `value` - accepts any JSON value: its validity is
decided when the batch is validated (2.1.1).

As for Core documents, a number written with a fraction or an exponent is not a length: a
validator maps it to a non-number before applying the schema (`tools/schema.ts`), so `2.0` fails
where a length is expected and passes inside `value`.

## Checking it

```sh
pnpm schema:check   # compile it (ajv, strict); check it against every request in conformance/ops/0.1
pnpm test           # tools/ops-schema.test.ts: tools/fixtures/ops-requests.json, which the oracle's
                    # request check (tools/oracle/test_ops_request.py) must classify the same way
```

# schema/ops

The JSON Schema (2020-12) of a Floorspec Ops apply request. It is **normative** (FLR-ADR-006): a
request it rejects is malformed, and an applier rejects it with `FS-OPS-001` (1.1.1).

## Files

One directory per draft; start at `request.schema.json`:

- **Ops 0.3** - the current draft (`spec/ops/`), operating on Core 0.3 documents (and so on 0.2
  and 0.1 documents) - is in [`0.3/`](0.3/): it adds no operation and no member, and its files are
  0.2's with one difference, that `addElement` may add to Core 0.3's twelfth and thirteenth
  collections, `roofs` and `stairs` (Ops 0.4);
- **Ops 0.2** is in [`0.2/`](0.2/), exactly as published at `6f9bc07`;
- **Ops 0.1** is in [`0.1/`](0.1/), exactly as published at `3bf4f35`; its text is readable from
  git at that commit.

The three have the same three files. 0.2's `operation.schema.json` adds to 0.1's: `addElement` into
the program's `items` or, with `extension`, an extension's collection; `moveOpening`'s `by` and
`toward`; `addLevel`; `addRoom`'s `brief`; and the operations `setAdjacency`, `removeAdjacency`,
`setRoomBrief`, `addProgramItem`, `placeElement` and `moveElement`. 0.2's `reference.schema.json`
adds `area` (3.6) and `host`, the host reference of `placeElement` and `moveElement` (4.10).

| File | Describes | Spec |
|---|---|---|
| `request.schema.json` | the apply request: `batch`, and `context` with its `locks` and `retired` IDs | 1.1, 6.1 |
| `operation.schema.json` | one operation: a union on `op` over the primitives and shorthands (eight in 0.1, ten in 0.2) and the composites (ten in 0.1, fifteen in 0.2), each a closed object with exactly the members its definition lists (and, in 0.2, exactly one of each group of alternatives - moveOpening's `at` or `by`, addLevel's `elevation`, `above` or `below`, a wall-face host's `side` or `toward`) | 2, 4 |
| `reference.schema.json` | the JSON forms of the reference grammar: length, point, vector, position, selector, a new ID, element content; in 0.2 also area and host reference | 3, 1.5, 4.10 |

Each file is published at its `$id`, `https://d3cloud.io/floorspec/schema/ops/<draft>/<file>`. A
published file is immutable: a change is a new draft, in a new directory - which is why 0.1's
`moveOpening` by a length and `addLevel`, written into 0.1 after it was published, were taken out
of it again and are in 0.2. CI fails if `schema/ops/0.1/` differs from `3bf4f35`, or
`schema/ops/0.2/` from `6f9bc07`.

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
pnpm schema:check   # compile each draft (ajv, strict); check it against every request of its suite,
                    # conformance/ops/0.1, 0.2 and 0.3
pnpm test           # tools/ops-schema.test.ts: tools/fixtures/ops-requests.json (0.1),
                    # ops-requests-0.2.json (0.2) and ops-requests-0.3.json (0.3), which the oracle's request check
                    # (tools/oracle/test_ops_request.py) must classify the same way
```

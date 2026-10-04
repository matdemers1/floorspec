# Floorspec conformance suite

The conformance suite is the standard's proof (FLR-ADR-009). Every statement at level `MUST` or
`MUST NOT` in a specification is exercised by at least one test here, and `pnpm coverage` fails
the build when one is not. Implementations are tested against the suite; the suite is never
adjusted to match an implementation.

## Layout

```text
conformance/
  core/0.1/<group>/<NNN-slug>/
    test.json        what the test is and which statements it covers
    input.json       the document under test, byte for byte (it may be malformed on purpose)
    expected.json    what a conformant implementation reports and derives
    canonical.json   the canonical form (9.2) — present exactly when the input is valid
```

Groups follow the chapters: `model`, `units`, `identity`, `taxonomy`, `walls`, `joins`, `rooms`,
`openings`, `types`, `serialization`, `diagnostics`. `examples` holds whole, plausible models -
`examples/001-three-room-house` is the Phase 1 exit demo.

## test.json

```json
{
  "description": "An L-shaped corner of two centre-justified walls mitres at the exact corner.",
  "covers": ["FS-CORE-5.6.1", "FS-CORE-5.7.1"]
}
```

`covers` lists the statement IDs the test exercises. A test may cover several statements, and a
statement is usually covered by several tests.

## expected.json

```json
{
  "valid": true,
  "diagnostics": [
    { "code": "FS-LINT-003", "severity": "info", "elements": [] }
  ],
  "hash": "9f2c…",
  "derived": { … }
}
```

- `valid` — whether the document is valid (10.1).
- `diagnostics` — every diagnostic, sorted by code and then by `elements` (10.2). A validator
  conforms when it reports exactly this list, compared on `code`, `severity` and `elements`
  (messages, locations and fixes are not compared). When the list contains `FS-SCH-001`, it
  contains only that one entry, and a validator conforms when it reports one or more `FS-SCH-001`
  and nothing else.
- `hash` — present when the document is valid: its content hash (9.3).
- `derived` — present when the document is valid: everything a deriver derives from it, below.

## derived

All coordinates are integers in base units, rounded as 2.2 requires. The values in this example
are illustrative only.

```json
{
  "walls": {
    "W1": {
      "startRight": [0, -6400], "endRight": [3833600, -6400],
      "endLeft": [3827200, 6400], "startLeft": [0, 6400],
      "baseElevation": 0, "topElevation": 3200000
    }
  },
  "junctionFills": {
    "J2": [[3820800, 6400], [3833600, -6400], [3846400, 6400]]
  },
  "rooms": {
    "R1": {
      "outer": [[6400, 6400], [3827200, 6400], [3827200, 2553600], [6400, 2553600]],
      "holes": [],
      "area": "9757040640000"
    }
  },
  "unanchored": [
    { "level": "L1", "outer": [[…]], "holes": [], "area": "…" }
  ],
  "openings": {
    "O1": { "start": [1000000, 0], "end": [2000000, 0], "sillElevation": 0, "headElevation": 2032000 }
  }
}
```

- `walls` — every wall on every level: its four face ends (5.7, 5.8) and its base and top
  elevations (5.9).
- `junctionFills` — every junction whose fill is not empty (5.7), as a ring.
- `rooms` — every room: its room polygon (6.2) and net area (6.4).
- `unanchored` — every bounded face with no anchor and a room polygon that is not degenerate,
  sorted by level ID and then by first vertex.
- `openings` — every opening's derived placement (7.4).
- A **ring** is an array of points that starts at its least vertex (least `x`, then least `y`)
  and runs counter-clockwise for an outer ring or a junction fill, clockwise for a hole. Holes
  are sorted by their first vertex.
- An **area** is a decimal string, because areas can exceed the range where JSON numbers are
  exact: an integer, or an integer followed by `.5`.

A deriver conforms when what it derives equals `derived` exactly.

## Writing a test

- Start from the statement. Write the smallest document that exercises it, and say in
  `description` what it shows.
- Prefer numbers a reviewer can check by hand: axis-aligned walls with even thicknesses give
  integer corners. Oblique walls are needed too — they are where rounding is tested — and their
  expected values come from `tools/oracle/`, an exact implementation written independently of
  any engine, never from the engine under test.
- An invalid test breaks exactly one rule where it can, so a failure points at one statement.
- Expected outputs are written by hand or by the oracle and then reviewed; they are never copied
  from an implementation's output.

## Re-verifying the suite

```sh
python3.13 -m tools.oracle.regenerate          # every test, recomputed from input.json; exit 1 on any difference
python3.13 -m tools.oracle <test-dir>          # one test's expected result, as the oracle computes it
python3.13 -m unittest discover tools/oracle   # the oracle's own tests
```

`regenerate` recomputes every expected result from `input.json` alone and compares it with what is on
disk: `valid` and `diagnostics` (written by hand, so only ever cross-checked), `hash`, `derived` and
`canonical.json` (which it can rewrite with `--write`). For every valid document it also checks that
the canonical form canonicalizes to itself and derives the same values and hash (9.2.2).

The suite assumes a reader that implements no extension: a document with a non-empty
`extensionsRequired` is rejected with `FS-DOC-002`.

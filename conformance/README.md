# Floorspec conformance suite

The conformance suite is the standard's proof (FLR-ADR-009). Every statement at level `MUST` or
`MUST NOT` in a specification is exercised by at least one test here, and `pnpm coverage` fails
the build when one is not. Implementations are tested against the suite; the suite is never
adjusted to match an implementation.

## Layout

```text
conformance/
  core/0.2/<group>/<NNN-slug>/
    test.json        what the test is and which statements it covers
    input.json       the document under test, byte for byte (it may be malformed on purpose)
    registry.json    optional: the validator's known extensions (Core 0.2, 12.2) - an array of registry entries
    expected.json    what a conformant implementation reports and derives
    canonical.json   the canonical form (9.2) — present exactly when the input is valid
  core/0.1/…         the Core 0.1 suite, as published; unchanged
```

**Core 0.2** (`core/0.2/`) is the suite of the current spec text, and the one `pnpm coverage`
gates it against. It holds every Core 0.1 test re-targeted to 0.2 — same group, same number,
declaring `"0.2"`, covering `FS-CORE-1.2.3` and `FS-CORE-1.6.9` where the 0.1 test covered the
retired `1.2.1` and `1.6.5` — and, after them in each group, the tests of what 0.2 adds. A 0.2
reader also reads 0.1 documents (1.2.4), and `model/061-read-0.1-document` and the tests after it
show that it reads them exactly as 0.1 does. **Core 0.1** (`core/0.1/`) is the suite of the
published 0.1 text, kept as it was so that a 0.1 implementation can still be tested against it.

Groups follow the chapters: `model`, `units`, `identity`, `taxonomy`, `walls`, `joins`, `rooms`,
`openings`, `types`, `serialization`, `diagnostics`, and in 0.2 `program`, `extensions`, `hosting`,
`clearances` and `circulation`. `examples` holds whole, plausible models - `examples/001-three-room-house` is the
Phase 1 exit demo.

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

- All five members are always present, even when empty (`{}` or `[]`); in the 0.2 suite, so are
  the six members below.
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

Core 0.2 adds six members, derived for every valid document (with nothing in them for a
document that has no program, extension elements, clearances or rooms):

```json
{
  "program": {
    "items": { "BED": { "rooms": ["RNW", "RSW"], "countMet": true, "minAreaMet": true, "targetAreaMet": false } },
    "adjacency": [ { "a": "KIT", "b": "DIN", "kind": "required", "adjacent": true, "connected": true } ]
  },
  "fallbacks": {
    "SOFA": { "level": "L1", "extension": "FS_furniture", "collection": "pieces",
              "footprint": [[…], …], "bottom": 0, "top": 1024000 }
  },
  "placements": { "SOFA": { "point": [2560000, 1920000, 0], "facing": 90000000 } },
  "clearances": {
    "O1": { "swing": { "level": "L1", "purpose": "swing", "footprint": [[…], …], "bottom": 0, "top": 2688000 } }
  },
  "clearanceOverlaps": [ [["O1", "swing"], ["PNL", "working"]] ],
  "circulation": {
    "HALL": { "entry": true, "reachable": true },
    "BED2": { "entry": false, "reachable": true, "throughSleeping": true }
  }
}
```

- `program` — every program item's rooms and whether it meets its count and areas (11.3), and
  every adjacency, in the document's order, with `adjacent` and `connected` (11.4).
  `minAreaMet` and `targetAreaMet` are present only for an item with that member.
- `fallbacks` — every extension element's fallback box in its frame (12.6): its footprint (a ring
  of four points, least vertex first, counter-clockwise), and its bottom and top elevations.
- `placements` — every extension element with a host: its frame's origin, rounded, and the
  direction it faces, in microdegrees (13.4).
- `clearances` — every clearance envelope, by owner (an opening or an extension element) and name
  (13.5).
- `clearanceOverlaps` — every pair of envelopes of different owners that overlap (13.6), each
  pair sorted and the list sorted.
- `circulation` — every room: whether it is an entry, whether it is reachable, and, for a sleeping
  room only, whether it is reachable only through another sleeping room (14.3).

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
python3.13 -m tools.oracle.author              # rewrite the suite from its declarations
```

`regenerate` reads `core/0.1` as a Core 0.1 reader and `core/0.2` as a Core 0.2 reader, and
recomputes every expected result from `input.json` (and `registry.json`) alone and compares it with what is on
disk: `valid` and `diagnostics` (written by hand, so only ever cross-checked), `hash`, `derived` and
`canonical.json` (which it can rewrite with `--write`). For every valid document it also checks that
the canonical form canonicalizes to itself and derives the same values and hash (9.2.2).

The suite assumes a reader that implements no extension: a document whose `extensionsRequired`
is well formed (distinct names, each in `extensionsUsed`) and not empty is rejected with
`FS-DOC-002`, once for each name. It assumes a validator configured with no known extensions
(Core 0.2, 12.2) except in a test that has a `registry.json`: there, the validator is configured
with exactly the entries in it. A test that expects `[FS-CFG-001]` has known extensions that are
not a valid registry, and a conformant validator reports that and nothing else, whatever the
document.

The tests are declared in `tools/oracle/author.py` (Core 0.1) and `tools/oracle/author02.py`
(Core 0.2, which takes every 0.1 declaration and re-targets it before adding its own), with every
expected diagnostic written by hand; `python3.13 -m tools.oracle.author` and
`python3.13 -m tools.oracle.author02` rewrite their suites and fail if the oracle disagrees with a
hand-written diagnostic. Add new tests at the end of their group in `author02.py`, so existing
directories keep their numbers; the 0.1 suite is published and does not change.

## Floorspec Ops

The Ops suites test an **applier** (Ops §0.2): software that applies a batch of operations to a
document. A test gives it a document A and an apply request, and says what it must return.
**Ops 0.2** (`ops/0.2/`) is the suite of the current text and the one `pnpm coverage` gates; it
holds every Ops 0.1 test re-targeted to 0.2 (on the same Core 0.1 documents) and, after them in
each group, the tests of what 0.2 adds. **Ops 0.1** (`ops/0.1/`) is kept exactly as published at
`3bf4f35`.

```text
conformance/
  ops/0.2/<group>/<NNN-slug>/
    test.json        what the test is and which FS-OPS statements it covers
    input.json       document A, byte for byte - valid, except in tests that expect FS-OPS-002
    request.json     the apply request (1.1): { "batch": [ … ], "context"?: { "locks"?, "retired"? } }
    expected.json    what a conformant applier returns
    output.json      B's canonical form (Core 9.2), byte for byte - present exactly when the batch commits
  ops/0.1/…          the Ops 0.1 suite, as published; unchanged
```

Groups: `transactions` (the request, the six steps, all or nothing, the result), `ids` (minting
and named IDs), `primitives`, `references` (lengths, points, vectors, selectors, sides,
positions), `composites`, `normalization` (merging, snap rounding, re-hosting, join cleanup),
`locks`, `diagnostics` and `inverse`, and in 0.2 `program` (program items, adjacencies, briefs,
areas) and `hosting` (extension elements: placing, moving, removing, following their hosts, split
walls). The realistic edits an agent makes are here by name:
`composites/…-make-the-kitchen-two-feet-wider` (a resize whose side continues past the room, so
it jogs), `…-make-the-dining-room-wider` (corner ends), `…-shrink-the-kitchen-from-the-south` (a T
at the continuing end), `…-add-a-door-between-kitchen-and-dining`,
`normalization/…-draw-a-wall-across-two-walls`, `…-drag-a-corner-onto-another`,
`…-opening-rehosted` and `…-opening-straddles`; and in 0.2 `program/…-draw-a-bubble-diagram`,
`hosting/…-move-a-wall-and-watch-them-follow` (the Phase 5 demo), `…-split-a-wall-under-its-outlets`
and `…-remove-a-wall-and-keep-the-furniture`.

### expected.json

```json
{
  "status": "committed",
  "diagnostics": [],
  "hash": "b6d6f1dd…",
  "created": ["J9", "W11"],
  "removed": [],
  "resolved": [ { "op": "addJunction", "id": "J9", "level": "L1", "position": [5462016, 3121152] }, … ],
  "inverse": [ { "op": "setProperty", "id": "R1", "path": "/anchor", "value": [2340864, 1560576] }, … ]
}
```

- `status` — `"committed"` or `"rejected"` (1.3).
- `diagnostics` — `[]` when the batch commits. When it is rejected: the FS-OPS diagnostics of the
  first failing step, or - when the result is invalid - the result's Core diagnostics with
  severity `error` (1.2.3), sorted by code and then by `elements`. Compared as in Core: on `code`,
  `severity` and `elements`; messages and locations are not compared (the oracle's own output,
  `python3.13 -m tools.oracle.ops <test-dir>`, shows each FS-OPS diagnostic's `location.pointer`
  into the request). A rejection that carries `FS-SCH-001` carries only that one entry, and an
  applier conforms when it reports one or more `FS-SCH-001` and nothing else.
- `hash`, `created`, `removed`, `resolved`, `inverse` — present when the batch commits: B's content
  hash (Core 9.3), the IDs created and removed (sorted), the resolved primitives (1.4) and the
  inverse (1.6). They are compared as JSON values.
- The result's `document` is not in expected.json: it is output.json, compared byte for byte.

An applier conforms on a test when its result has the expected status, diagnostics and - for a
committed batch - exactly output.json's bytes and the expected members above.

### How the suite is checked

`python3.13 -m tools.oracle.regenerate` recomputes every Ops test from input.json and
request.json with the oracle's applier (`tools/oracle/ops/`) - `ops/0.1` as Ops 0.1 applies it,
`ops/0.2` as Ops 0.2 does - cross-checks `status` and
`diagnostics` (written by hand, never rewritten), and compares `hash`, `created`, `removed`,
`resolved`, `inverse` and output.json (which `--write` rewrites). For every committed test it
also checks what the specification promises of any result: B is in canonical form (1.3.1);
applying the batch again gives the same bytes (1.3.2); applying `resolved` to A in place of the
batch, with the same context, commits the same B (1.4.1); and applying `inverse` to B commits a
document whose canonical form is A's (1.6.1). `pnpm schema:check` applies each draft's request
schema (`schema/ops/0.1/`, `schema/ops/0.2/`) to every request.json of its suite: it must reject
exactly the requests whose expected diagnostics are `[FS-OPS-001]`, and accept every other; and
every document A outside the FS-OPS-002 tests must match the Core schema of its draft (a document
declaring `"0.1"` Core 0.1's). The Ops 0.2 suite assumes a validator configured with no known
extensions (Core 0.2, 12.2).

The tests are declared in `tools/oracle/ops_author.py` (Ops 0.1) and `tools/oracle/ops_author02.py`
(Ops 0.2, which takes every 0.1 declaration and re-targets it before adding its own), with every
expected status and diagnostic written by hand, and the values that matter - resolved integers,
where a junction ends up, which wall an opening is on, that a hosted element derives the same
placement - asserted by hand in each test's `check`. `python3.13 -m tools.oracle.ops_author` and
`python3.13 -m tools.oracle.ops_author02` rewrite their suites and fail if the oracle disagrees
with a hand-written expectation; CI runs every author script and fails if the suite on disk is not
exactly what it declares. Add new tests at the end of their group in `ops_author02.py`, so existing
directories keep their numbers; the 0.1 suite is published and does not change.

The suite follows the 0.1 text where it settles what earlier drafts left open - the order of the
checks (1.2, 7.1), one diagnostic per failing opening or lock (7.1.2), what `$document` addresses
(2.3), minting past every ID A or the batch has used (1.5), property differences first in the
inverse (1.6), planarizing only a level that breaks Core §5.3 (5.2), and resizing inwards at a T
(4.4) - and the tests that pin each say so in their description.

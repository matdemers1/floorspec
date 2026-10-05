# Floorspec conformance suite

The conformance suite is the standard's proof (FLR-ADR-009). Every statement at level `MUST` or
`MUST NOT` in a specification is exercised by at least one test here, and `pnpm coverage` fails
the build when one is not. Implementations are tested against the suite; the suite is never
adjusted to match an implementation.

## Layout

```text
conformance/
  core/0.3/<group>/<NNN-slug>/
    test.json        what the test is and which statements it covers
    input.json       the document under test, byte for byte (it may be malformed on purpose)
    registry.json    optional: the validator's known extensions (Core 12.2) - an array of registry entries
    design.json      optional, from Core 0.3: the design to derive (Core 19.6) - an object of option set → option
    expected.json    what a conformant implementation reports and derives
    canonical.json   the canonical form (9.2) — present exactly when the input is valid
    package/         optional, Core 0.3: the files of the document's package (18.4) - the test is
                     then run by a package validator, given exactly these files at these paths
  core/0.2/…         the Core 0.2 suite, as published at 6f9bc07; unchanged
  core/0.1/…         the Core 0.1 suite, as published; unchanged
  ext/<NAME>/<version>/…   each extension's suite (below): FS_electrical, FS_plumbing, FS_mechanical, FS_lowvoltage, FS_furniture, FS_structural
  rules/0.1/…        the Floorspec Rules 0.1 suite (below)
```

**Core 0.3** (`core/0.3/`) is the suite of the current spec text, and the one `pnpm coverage`
gates it against. It holds every Core 0.2 test re-targeted to 0.3 — same group, same number,
declaring `"0.3"` where the 0.2 test declared `"0.2"` (a test whose document declares `"0.1"` keeps
it, and shows a 0.3 reader reading 0.1), covering `FS-CORE-1.2.5` and `FS-CORE-1.2.6` where the
0.2 test covered the retired `1.2.3` and `1.2.4` — and, after them in each group, the tests of what
0.3 adds: operations and clear openings, floors, ceilings and slabs (the group `floors`, and
hosting on them at the end of `hosting`), roofs (the group `roofs`), and stairs (the group
`stairs`, and circulation through them at the end of `circulation`), and design options (the group
`options`, and `examples/002-kitchen-options`, the Phase 8 demo's kitchen A and B). A 0.3 reader derives every
room's floor and ceiling, every slab's bounding geometry, and every roof and stair, so every valid
re-targeted test's `derived` has the six members `floors`, `ceilings`, `slabs`, `roofs`, `stairs`
and `finishes` that its 0.2 counterpart lacks — `roofs` and `stairs` empty, and `finishes` empty
unless a room or a layer names a material; every other value in it is the 0.2 suite's, byte for
byte. A 0.3 reader also reads 0.2 documents (1.2.6), and
`model/070-read-0.2-document` and `hosting/045-read-0.2-surface-hosts` show that it derives for one
everything 0.2 does, surface hosts included, and its floors, ceilings and slabs besides.

**Core 0.2** (`core/0.2/`) and **Core 0.1** (`core/0.1/`) are the suites of the published 0.2 and
0.1 texts, kept as they were so that an implementation of either can still be tested against it.
The 0.2 suite holds every 0.1 test re-targeted to 0.2 and the tests of what 0.2 added; a 0.2
reader also reads 0.1 documents, and its `model/061-read-0.1-document` and the tests after it show
that it reads them exactly as 0.1 does.

Groups follow the chapters: `model`, `units`, `identity`, `taxonomy`, `walls`, `joins`, `rooms`,
`openings`, `types`, `serialization`, `diagnostics`, from 0.2 `program`, `extensions`, `hosting`,
`clearances` and `circulation`, and from 0.3 `floors` (chapter 15: floors, ceilings and slabs), `roofs`
(chapter 16), `stairs` (chapter 17), `materials` (chapter 18: materials, textures, the package and
finishes) and `options` (chapter 19). `examples` holds whole, plausible models - `examples/001-three-room-house` is the
Phase 1 exit demo, and in Core 0.3 `examples/003-three-room-house-from-the-library` is the same house built from the
US starter type library (`library/us-starter/`), every type and material embedded exactly as the library publishes
it, with its `source` (Core 8.1). The `types` tests from `049-library-types-with-source` on use the library too, and
so do Ops 0.3's `primitives/113-embed-a-library-type` and `114-embed-a-library-type-twice`, which apply an item's
published embed batch.

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
  (messages, locations and fixes are not compared), and on `design` - present, from Core 0.3, on a
  diagnostic found in an option design and not in the primary design (19.5). When the list contains `FS-SCH-001`, it
  contains only that one entry, and a validator conforms when it reports one or more `FS-SCH-001`
  and nothing else.
- `hash` — present when the document is valid: its content hash (9.3).
- `derived` — present when the document is valid: everything a deriver derives from it, below — for
  the design design.json names, or the primary design when the test has none (Core 19.6). It is
  absent when design.json names a design Core derives nothing for (19.6.2), though the document is
  valid.

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
- `openings` — every opening's derived placement (7.4) and, from 0.3, its clear opening (7.4.2),
  exactly as declared: `"clearOpening": { "width": …, "height": … }`, with `"area"` only when one is
  declared, and no `clearOpening` member at all for an opening that resolves none.
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

Core 0.3 adds three members, derived for every valid document a 0.3 reader reads, whatever the
draft it declares (with nothing in them for a document with no rooms or slabs):

```json
{
  "floors": { "R1": { "top": -192000, "bottom": -512000,
                      "box": { "min": [64000, 64000, -512000], "max": [5056000, 3776000, -192000] } } },
  "ceilings": {
    "R1": { "kind": "tray", "low": 3456000, "high": 3712000,
            "tray": { "outer": [[448000, 448000], …], "holes": [] },
            "box": { "min": [64000, 64000, 3456000], "max": [5056000, 3776000, 3712000] } }
  },
  "slabs": { "S1": { "outline": [[0, -3840000], …], "top": -192000, "bottom": -320000,
                     "box": { "min": [0, -3840000, -320000], "max": [5120000, -128000, -192000] } } }
}
```

- `floors` — every room's floor (15.1): its top, its bottom (equal to its top when no thickness is
  declared) and its box, which spans its room polygon's outer ring in plan.
- `ceilings` — every room's ceiling (15.5): its `kind`, its `low` and `high`, its box, and for a
  tray its centre (`tray`, a polygon as a room's is).
- `slabs` — every slab's outline (a ring), top, bottom and box (15.7).

And a fourth, for roofs (chapter 16), empty for a document with none — so every valid 0.3 test's
`derived` has a `roofs` member too:

```json
{
  "roofs": {
    "RF1": { "kind": "gable", "outline": [[-448000, -448000], …], "eave": 3456000,
             "surface": { "high": 4640000, "box": { "min": […], "max": […] },
                          "faces": [{ "edge": 1, "polygon": [[x, y, z], …], "area": "…" }, …],
                          "gables": [{ "edge": 0, "polygon": [[x, y, z], …] }, …],
                          "lines": [{ "kind": "ridge", "from": [x, y, z], "to": [x, y, z] }, …] } },
    "RF2": { "kind": "hip", "outline": […], "eave": 3456000, "surface": null }
  }
}
```

And a fifth, for stairs (chapter 17), empty for a document with none — so every valid 0.3 test's
`derived` has a `stairs` member too:

```json
{
  "stairs": {
    "ST1": { "risers": 14, "riserHeight": 246857, "rise": 3456000, "bottom": 0, "top": 3456000,
             "foot": [1280000, 768000], "head": [5440000, 768000], "footRoom": "R1", "headRoom": "R2",
             "box": { "min": [1280000, 192000, 0], "max": [5440000, 1344000, 3456000] },
             "steps": [ { "outline": [[1280000, 192000], …], "top": 246857 }, … ],
             "run": 4160000, "walkline": { "points": [[1280000, 768000], [5440000, 768000]], "length": 4160000 },
             "headroom": 2331429 }
  }
}
```

- `roofs` — every roof's kind, eave outline and eave (16.2, 16.3), and its surface (16.5): its high,
  box, faces, gable ends, and ridges, hips and valleys; `null` for a roof whose surface this draft
  does not derive (16.4.4), which the validator reports with `FS-LINT-015`.
- `options` — present only for a document with an option set (Core 19.6.3): for every set, `chosen`,
  the option the derived design chooses, and for every option of it its `members`, the `rooms` of its
  own design with their net areas, and `affected`, what differs between that design and the primary
  design. Every other member of `derived` is the derived design's.

```json
{
  "options": {
    "KS": { "chosen": "KA",
            "options": { "KA": { "rooms": { "DIN": "31309824000000", "KIT": "18530304000000" }, "members": ["OA", "WA"], "affected": [] },
                         "KB": { "rooms": { "DIN": "25239552000000", "KIT": "25239552000000" }, "members": ["OB", "SB"],
                                 "affected": ["DIN", "KIT", "W3", "W4", "W6", "W7"] } } }
  }
}
```

- `stairs` — every stair: its riser count and riser height, rounded; its rise, bottom and top; its
  foot and head, and the rooms they are in when there are any; its box (17.4). For a straight,
  L-shaped or U-shaped stair also its `steps` — every tread and landing in walking order, a landing
  marked `"landing": true` — its `run` and `walkline` (17.5), and its `headroom` when something is
  above it (17.6); for a winder or a spiral stair, none of those (17.7).

And a sixth, for materials and finishes (chapter 18), derived for every valid document a 0.3 reader
reads, whatever its draft — a room's `wallFinish`, `floorFinish` and `ceilingFinish` and a layer's
`material` are members of 0.1 — so every valid 0.3 test's `derived` has a `finishes` member too, with
nothing in it for a document that finishes nothing:

```json
{
  "finishes": {
    "rooms": { "KIT": { "floor": "OAK", "ceiling": "PAINT" } },
    "walls": {
      "W2": {
        "left": { "material": "SIDING", "source": "layer", "regions": [] },
        "right": { "room": "KIT", "material": "PAINT", "source": "room",
                   "regions": [ { "from": 768000, "to": 4352000, "bottom": 1170432, "top": 1755648, "material": "TILE" } ] }
      }
    }
  }
}
```

- `finishes.rooms` — every room with a floor or a ceiling finish: `floor` and `ceiling`, each present
  only when the room names it (18.6).
- `finishes.walls` — every side of every wall whose finish resolves to a material or that has
  regions: the `room` it faces, when it faces one; its `material` and the `source` that gave it —
  `"face"`, `"room"` or `"layer"` — when it resolves to one; and its `regions`, as the wall lists
  them (`[]` when it has none).

A test with a `package/` directory is run by a **package validator** (18.4), given the files under
that directory, each at its path relative to it; it checks every asset located by `path` against its
file (`FS-INV-1005` to `FS-INV-1007`). A test without one is run by a validator that is not given the
package's files, which never reports those three. Package files are compared byte for byte, and a
path names exactly one file, case and all: a package validator on a case-insensitive file system
looks a path up in the directory's listing, not by opening it.

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

`regenerate` reads `core/0.1` as a Core 0.1 reader, `core/0.2` as a Core 0.2 reader and `core/0.3` as a Core 0.3 reader, and
recomputes every expected result from `input.json` (and `registry.json`, and `package/`) alone and compares it with what is on
disk: `valid` and `diagnostics` (written by hand, so only ever cross-checked), `hash`, `derived` and
`canonical.json` (which it can rewrite with `--write`). For every valid document it also checks that
the canonical form canonicalizes to itself and derives the same values and hash (9.2.2).

The suite assumes a reader that implements no extension: a document whose `extensionsRequired`
is well formed (distinct names, each in `extensionsUsed`) and not empty is rejected with
`FS-DOC-002`, once for each name. It assumes a validator configured with no known extensions
(Core 12.2) except in a test that has a `registry.json`: there, the validator is configured
with exactly the entries in it. A test that expects `[FS-CFG-001]` has known extensions that are
not a valid registry, and a conformant validator reports that and nothing else, whatever the
document.

The tests are declared in `tools/oracle/author.py` (Core 0.1), `tools/oracle/author02.py` (Core
0.2, which takes every 0.1 declaration and re-targets it before adding its own) and
`tools/oracle/author03.py` (Core 0.3, which does the same with every 0.2 declaration), with every
expected diagnostic written by hand; `python3.13 -m tools.oracle.author`, `…author02` and
`…author03` rewrite their suites and fail if the oracle disagrees with a hand-written diagnostic.
Add new tests at the end of their group in `author03.py`, so existing directories keep their
numbers; the 0.1 and 0.2 suites are published and do not change.

## Floorspec Ops

The Ops suites test an **applier** (Ops §0.2): software that applies a batch of operations to a
document. A test gives it a document A and an apply request, and says what it must return.
**Ops 0.3** (`ops/0.3/`) is the suite of the current text and the one `pnpm coverage` gates; it
holds every Ops 0.2 test on the same documents (Ops 0.3 retires one statement, below), the five tests that
pin what the text says as the oracle does - declared after 0.2 was published, and so first
published with 0.3 - and, after them in each group, the tests of what 0.3 adds: Core 0.3
documents, whose operations and clear openings, floors, ceilings and slabs a batch edits with
`setProperty`, `unsetProperty` and `addElement`, `moveRoom` moving a vaulted ceiling's ridge
(`composites/068-move-room-moves-its-vault`), roofs added, edited and removed
(`primitives/068` to `078`), and stairs - added, edited, removed, and removed with the levels they
join (`primitives/079-add-a-stair` and the tests after it), and materials and finishes - textures
and wall finishes edited, the FLR-P-8 exit demo as one batch (`primitives/089-tile-photo-on-the-backsplash`
and the tests after it), removals a finish or a map blocks, and a split wall cutting its regions
(`normalization/025-split-wall-cuts-its-regions`); and design options (Core chapter 19) - option
sets and options added, minted, switched and removed, elements added in an option with `context.option`,
moved between options and made common (`primitives/…-add-an-option-set` and after), references read in
the edit design (`references/…-faces-of-the-edit-design`), and normalization option by option
(`normalization/…-option-wall-ends-on-a-common-wall` and after). **Ops 0.2** (`ops/0.2/`, which holds every Ops 0.1 test re-targeted to 0.2 and the
tests of what 0.2 added) is kept exactly as published at `6f9bc07`, and **Ops 0.1** (`ops/0.1/`)
exactly as published at `3bf4f35`. Ops 0.3's requests have Ops 0.2's shape, and may also add
to Core 0.3's `roofs` and `stairs`: its suite is checked against its own `schema/ops/0.3/`, and its tests cover
`FS-OPS-1.1.3` where the 0.2 test covered the retired `1.1.2`.

```text
conformance/
  ops/0.3/<group>/<NNN-slug>/
    test.json        what the test is and which FS-OPS statements it covers
    input.json       document A, byte for byte - valid, except in tests that expect FS-OPS-002
    request.json     the apply request (1.1): { "batch": [ … ], "context"?: { "locks"?, "retired"? } }
    expected.json    what a conformant applier returns
    output.json      B's canonical form (Core 9.2), byte for byte - present exactly when the batch commits
  ops/0.2/…          the Ops 0.2 suite, as published; unchanged
  ops/0.1/…          the Ops 0.1 suite, as published; unchanged
```

Groups: `transactions` (the request, the six steps, all or nothing, the result), `ids` (minting
and named IDs), `primitives`, `references` (lengths, points, vectors, selectors, sides,
positions), `composites`, `normalization` (merging, snap rounding, re-hosting, join cleanup),
`locks`, `diagnostics` and `inverse`, and from 0.2 `program` (program items, adjacencies, briefs,
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
`ops/0.2` as Ops 0.2 does, `ops/0.3` as Ops 0.3 does - cross-checks `status` and
`diagnostics` (written by hand, never rewritten), and compares `hash`, `created`, `removed`,
`resolved`, `inverse` and output.json (which `--write` rewrites). For every committed test it
also checks what the specification promises of any result: B is in canonical form (1.3.1);
applying the batch again gives the same bytes (1.3.2); applying `resolved` to A in place of the
batch, with the same context, commits the same B (1.4.1); and applying `inverse` to B commits a
document whose canonical form is A's (1.6.1). `pnpm schema:check` applies each draft's request
schema (`schema/ops/0.1/`, `schema/ops/0.2/`, `schema/ops/0.3/`) to every request.json of its suite: it must reject
exactly the requests whose expected diagnostics are `[FS-OPS-001]`, and accept every other; and
every document A outside the FS-OPS-002 tests must match the Core schema of its draft (a document
declaring an earlier draft that draft's). The Ops 0.2 and 0.3 suites assume a validator
configured with no known extensions (Core 12.2).

The tests are declared in `tools/oracle/ops_author.py` (Ops 0.1), `tools/oracle/ops_author02.py`
(Ops 0.2, which takes every 0.1 declaration and re-targets it before adding its own) and
`tools/oracle/ops_author03.py` (Ops 0.3, which carries every 0.2 declaration forward), with every
expected status and diagnostic written by hand, and the values that matter - resolved integers,
where a junction ends up, which wall an opening is on, that a hosted element derives the same
placement - asserted by hand in each test's `check`. `python3.13 -m tools.oracle.ops_author`,
`…ops_author02` and `…ops_author03` rewrite their suites and fail if the oracle disagrees
with a hand-written expectation; CI runs every author script and fails if the suite on disk is not
exactly what it declares. Add new tests at the end of their group in `ops_author03.py`, so existing
directories keep their numbers; the 0.1 and 0.2 suites are published and do not change.

The suite follows the 0.1 text where it settles what earlier drafts left open - the order of the
checks (1.2, 7.1), one diagnostic per failing opening or lock (7.1.2), what `$document` addresses
(2.3), minting past every ID A or the batch has used (1.5), property differences first in the
inverse (1.6), planarizing only a level that breaks Core §5.3 (5.2), and resizing inwards at a T
(4.4) - and the tests that pin each say so in their description.

## Extensions

Each extension with a specification in `registry/<NAME>/spec.md` has its suite at
`conformance/ext/<NAME>/<version>/`, and `pnpm coverage` gates its statements (`FS-ELEC-`,
`FS-PLMB-`, `FS-MECH-`, `FS-LOWV-`, `FS-FURN-`, `FS-STRC-`) against it as it gates Core's. A test there may also cover Core
or Ops statements it exercises.

An extension suite is run by **an implementation of that one extension**: a reader, validator and
deriver of the Core draft each test's document declares — Core 0.3 for a document that declares
`"0.3"`, Core 0.2 for every other — that implements `<NAME>` at `<version>` and no other extension
(it passes `FS-DOC-002` for `<NAME>` alone), configured with the test's `registry.json` as its known
extensions — usually just `<NAME>`'s own registry entry — or with none when the test has none. In
the D3 Floorspec engine that is `extensions: ['<NAME>']` with `knownExtensions` from
`registry.json`, and `core` the draft the document declares. Every official extension at 0.1.0 is
evaluated for Core 0.2 and 0.3 documents (each specification's 1.1), and its `activation` group
reads the demo house declaring `"0.3"` as well.

Two kinds of test share the suite:

- **Validator and deriver tests**, laid out as Core 0.2's (`test.json`, `input.json`,
  `registry.json`, `expected.json`, `canonical.json`). `expected.json` is Core's, and its `derived`
  has one more member, always present: `extensions`, mapping each extension the run evaluated
  (each specification's §1.2) to what it derives — `{}` when none was, as in a test without
  `registry.json`. As in Core 0.3's suite, a test with a `package/` directory is run by a package
  validator given its files (Core §18.4), and one with `design.json` derives that design (Core §19.6).
- **Ops tests**, in the group `ops`, laid out as Ops 0.2's (`test.json`, `input.json`,
  `request.json`, `registry.json`, `expected.json`, `output.json`), applied as Ops 0.2 — as Ops 0.3
  for a document that declares `"0.3"`, as the Core reader is chosen — by an applier whose
  validator is that implementation, configured with `registry.json`. A batch whose result breaks
  one of the extension's invariants is rejected with that diagnostic (Ops §1.2 step 6).

Groups: `examples` (the Phase 5 demo house: a panel, kitchen receptacles on two 20 A circuits, a
toilet, a lavatory, a water heater, a gas furnace and range, low-voltage devices — read by an
implementation that knows the extension, by one that knows none, and by one that knows all four
official entries), `activation` (when an extension is evaluated at all), `order` (Core first, then
the extension's schema, then its invariants, lints only for a valid document), `schema`,
`invariants`, `lints`, `derived` and `ops` (`…-move-a-wall-and-watch-them-follow`: the Phase 5 demo,
where moving a wall leaves the devices' bytes unchanged and moves their derived placements), and
`options` (`…-element-in-an-option`: the demo house as a Core 0.3 document with one element in an
option, which the extension's schema accepts with its `option` member).

FS_furniture's suite starts from its own document, the Phase 8 demo flat (`examples/…-p8-demo-flat`):
a kitchen with a refrigerator, a range, a dishwasher, cabinets, a pantry and a dining table with its
chairs, a bedroom with a bed, a nightstand and a wardrobe, and a laundry with a washer and a dryer —
every item the starter library's (`registry/FS_furniture/library/`), with the library's own model
and symbol files and default envelopes. Besides the groups above it has `options` (kitchen options
A and B as Core 0.3 design options: the primary design, the design that chooses B, and an invariant
found only in B's design) and `package` (the flat run by a package validator given the library's
files, and given a wrong one); its `ops` group places, moves and removes items, and places one into
option B as Ops 0.3 with `context.option`.

FS_structural's suite starts from the Phase 10 framed house (`examples/…-p10-framed-house`): the
demo house's plan with bearing and shear walls framed with studs, headers over the openings in
bearing walls, the Kitchen's floor joists and the Bath's slab on grade, and a deck with a recorded
span. FS_structural adds no kind of element, so every datum is on a wall, an opening, a room or a
slab - and its `schema` group also tests data on elements that may not carry any. Its `invariants`
group includes `…-no-judgement-of-adequacy`: framing no engineer would accept, valid, with nothing
derived that says otherwise (FS-STRC-1.4). Its `options` group puts two decks in deck options A and
B; its `ops` group sets and unsets flags and headers with `setProperty`, rejects a framing whose
studs are closer than they are wide, and moves a wall to show the Kitchen's derived span follow it.

The tests are declared in `tools/oracle/ext_author.py`, almost all as one change to the demo house
(the demo flat, for FS_furniture; the framed house, for FS_structural), with every expected diagnostic written by hand and the derived
values that matter — a circuit's loads and connected load, a panel's spaces, the room each device is
in, a stack's connections, the floor area each room's furniture stands on — asserted by hand. The oracle implements each extension in `tools/oracle/ext/` from its
specification alone, and reads each extension's schema with a small, independent interpreter of the
JSON Schema keywords the official schemas use (`tools/oracle/ext/jsonschema.py`).
`python3.13 -m tools.oracle.ext_author` rewrites the extension suites, `python3.13 -m
tools.oracle.regenerate` re-verifies them with the others, and `pnpm schema:check` checks that each
extension's schema rejects its data exactly in the tests that expect `FS-<CODE>-SCH-001` and accepts
it in every valid test that evaluates it - for FS_structural, its data on every element too, against
its schema's `#/$defs/coreElements`.

## Floorspec Rules

The Rules suite, `rules/0.1/`, tests an **evaluator** (Rules §0.2): software that evaluates rule
packs against a document under a jurisdiction profile. It is run by an evaluator that implements the
official extensions at 0.1.0 (FS_electrical, FS_plumbing, FS_mechanical, FS_lowvoltage and FS_furniture), configured with the test's `registry.json` as its known
extensions - or with none, when the test has none - exactly as a Core 0.3 validator is. `pnpm
coverage` gates FS-RULES 0.1 against it.

```text
conformance/
  rules/0.1/<group>/<NNN-slug>/
    test.json        what the test is and which FS-RULES statements it covers
    input.json       the document (Core 0.2, with official extensions where the test needs them; Core 0.3 where it needs clear openings)
    registry.json    optional: the evaluator's known extensions
    request.json     a report test: the evaluation request (Rules §1.1) - packs, profile, units
    measures.json    a measure test: { "units"?: …, "calls": [ { "target", "measure", "args"? }, … ] }
    expected.json    the report (Rules §9.1), or { "results": [ measure result, … ] } (Rules §4.7)
```

**expected.json is compared byte for byte.** A report is written as Core §9.2 step 2 writes a value
(Rules §9.8): members sorted, two spaces of indentation, a final line feed; so is a measure test's
`{ "results": [ … ] }`. An evaluator conforms on a report test when it returns exactly those bytes
for input.json, registry.json and request.json; on a measure test, when the result of each call, in
order, is exactly the expected one.

Every rule of every pack in the suite is **synthetic**: it cites the invented codes `TEST-CODE` and
`TEST-ELEC` with invented sections and invented thresholds, or - only to test which editions the
default profile adopts - a model code's name with a section `TEST-n` and a paraphrase that says it
states no requirement of that code. No requirement of a real code is encoded here; real packs are
in `rules/` and have fixtures of their own.

Groups: `request`, `document`, `packs`, `typing` (well-typed rules, deferred measures, rules that read
an extension that is not evaluated), `selection` (subjects and candidates), `exceptions`, `tests`
(every operator, exact areas, no value), `findings` (messages, order, coverage, every reason a rule is
not evaluated), `profiles` (malformed profiles, editions in force by date, the default profile, packs
by range, amendments), `examples` (the Phase 6 demo with synthetic rules: the boiler beside the panel
and the bedroom without a window), and the measure groups `measures-rooms`, `measures-openings`,
`measures-elements`, `measures-envelopes`, `measures-walllines` and `measures-circuits-and-levels`,
built on one plan - **the rules house**: a bedroom, a living room and a utility room in a row, with a
panel, a boiler, a smoke alarm and two receptacles - so that most values can be checked by hand.
The net clear measures (Rules §6.5) are tested on the rules house as a Core 0.3 document whose door
and window types declare their operation and clear opening (`measures-openings/…-net-clear-openings`,
`selection/…-net-clear-escape-opening` and the tests after it). The official extensions at 0.1.0
are evaluated for Core 0.3 documents as for 0.2 ones (each one's 1.2), and
`typing/…-extension-rules-on-a-core-0.3-document` shows the rules that read them evaluated on one. `ceilingHeight` (Rules §5.7), reserved until Core 0.3 derived ceilings, is tested on the rules house as
a Core 0.3 document with a cathedral ceiling, a sunken floor and a tray (`measures-rooms/…-ceiling-height`
and the two tests after it). The stair measures (Rules §8.5), reserved until Core 0.3 defined stairs, are
tested in `measures-stairs` on the rules house as a Core 0.3 document with a second level over the
living room, a straight stair rising into it through a well and a spiral stair in the bedroom.

The tests are declared in `tools/oracle/rules_author.py`, with every expected diagnostic and every
expected finding (pack, rule, subject) written by hand, and every measure value that a reviewer can
check - axis-aligned walls, round numbers - written by hand too; the oblique ones (a room with
oblique walls, a piece turned 30°) are the oracle's, bounded by hand. `python3.13 -m
tools.oracle.rules_author` rewrites the suite and fails if the oracle disagrees with anything written
by hand; `python3.13 -m tools.oracle.regenerate` re-verifies it with the others - every report byte
for byte, none matching the assurance pattern (Rules §9.5), each with the notice, and each that
evaluated its document carrying that document's own content hash (Rules §1.5); and `python3.13 -m
tools.oracle.rules <test-dir>` prints one test's expected output. The oracle's evaluator is
`tools/oracle/rules/`, written from `spec/rules/` alone, with its own exact arithmetic in
`Q(√m)` for local coordinates. `pnpm schema:check` checks that the request, profile and pack schemas
reject exactly the inputs whose expected diagnostics say they should, that every report matches the
report schema and every measure result the measure result definition.

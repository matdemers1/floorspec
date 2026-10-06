# 0. Conventions

> [!warning] Floorspec Core 0.4 — Draft
> This is a working draft. It carries no compatibility promise: a later 0.x draft may change any
> part of it. Floorspec stays 0.x until the 1.0 criteria are met (FLR-ADR-017).

Floorspec Core defines a document that describes a building as code: its levels, the walls on a
junction graph, the rooms that walls enclose, the openings hosted on walls, the types and
materials they use — including how a door or window operates and the net clear opening its maker
declares — the program the building is meant to satisfy, and the elements that extensions
add — placed on their hosts, with the clearances they need. It defines what makes a document
valid, the exact geometry a conformant tool derives from it — including which rooms a person can
walk to, every room's floor and ceiling, the surfaces of its roofs and the steps of its stairs,
straight or turning on winders or round a spiral — and the one byte sequence that every conformant
writer produces for it.

## 0.1 Normative language

The key words `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT` and `MAY` in this specification are to be
interpreted as described in BCP 14 (RFC 2119, RFC 8174) when, and only when, they appear in
capitals, as shown here. Floorspec does not use `SHALL`, `REQUIRED`, `RECOMMENDED` or `OPTIONAL`.

Every sentence that uses one of those keywords is a *normative statement* and ends with a tag
giving its stable identifier and level, for example `{#FS-CORE-5.3.1 MUST}`. The identifier is
`FS-CORE-<chapter>.<section>.<n>`. An identifier is never reused, including after the statement it
named is removed.

Every statement at level `MUST` or `MUST NOT` is exercised by at least one test in the conformance
suite (`conformance/core/0.4/`), and the build that publishes this specification fails if one is
not. Tables, figures and informative callouts are normative only where a tagged statement says so.

## 0.2 Conformance classes

Floorspec Core 0.4 places requirements on these kinds of thing:

| Class | What it is | What it must do |
|---|---|---|
| **Document** | a JSON text claiming to be Floorspec | satisfy every requirement on documents (chapters 1–8, 11–13, 15–19, 21) |
| **Reader** | software that loads documents | apply defaults and the version and extension rules (1.2, 1.5, 1.6, 12.1) |
| **Writer** | software that produces documents | produce valid documents; preserve what it does not understand (1.6, 1.7) |
| **Canonicalizer** | software that produces the canonical form | produce exactly the bytes of chapter 9 |
| **Validator** | software that reports validity | report the diagnostics of chapter 10, given the known extensions it is configured with (12.2) |
| **Package validator** | a validator that is also given the files of the document's package (18.4) | check every packaged asset against its file, as well (18.4) |
| **Deriver** | software that computes geometry | produce exactly the derived values of chapters 5–7, 11–18 and 21, for the design asked for (19.6) |
| **Registry entry** | the metadata of one version of an extension (12.2) | match the registry entry schema |
| **Migrator** | software that migrates a document to a later draft (chapter 20) | write exactly the migration chapter 20 defines, and refuse what it refuses |

One program is usually several of these. The conformance suite tests each class separately; the
reference implementation, D3 Floorspec, claims all of them.

## 0.3 Notation

- A **JSON integer** is a JSON number written with neither a fraction nor an exponent. A
  **length** is a JSON integer number of base units (chapter 2). A **point** is `[x, y]`, two
  lengths. Code-like names (`walls`, `justification`) are JSON member names.
- **Exact value** means the mathematically exact real number. Derived values are defined as exact
  values and then rounded once, as chapter 2 specifies; no intermediate rounding is permitted.
- `round(v)` is rounding of a real number to the nearest integer, ties to even.
- An **element** is a member of one of the document's collections (1.4). Its **ID** is its member
  name in that collection. A **program item** (11.1) and an **extension element** (12.5) have IDs
  in the same space (3.1) but are not elements in this sense: their members are defined by
  chapters 11 and 12.
- **Left** and **right** of a directed line are as seen from above (from +Z), looking along the
  line.

## 0.4 References

Normative: RFC 8259 (JSON), RFC 8785 (JSON Canonicalization Scheme), RFC 6901 (JSON Pointer),
FIPS 180-4 (SHA-256), JSON Schema 2020-12, BCP 14 (RFC 2119, RFC 8174), Semantic Versioning
2.0.0, RFC 3986 (URI).

Informative: ISO 16739-1:2024 (IFC 4.3) and IFC4 ADD2 TC1, for the mapping in Annex A.

## 0.5 What this draft does not yet define

Floorspec Core 0.2 added the program, the extension mechanism in full, hosting and clearance
envelopes, and circulation to the walls-and-rooms draft (0.8), Core 0.3 added the operation and
net clear opening of door and window types, the floors and ceilings of rooms, roofs and stairs (0.7),
and Core 0.4 adds the treads of winder and spiral stairs (0.6). These are reserved for later drafts
and a 0.4 document cannot contain them:

- the surface of a roof with two or more sloped edges one of which is oblique and not along a
  Pythagorean direction, or with a gable the wavefront would pass the end of, or with part of its
  outline enclosed by gables alone (16.4.6); and a roof's footprint that follows its walls;
- a door's or window's frame, glazing and hardware, and a casement's hand or a pivot's axis (8.4);
- edges along any curve but a circular arc of at most a semicircle, and derived geometry of the exact
  circle rather than its polyline (21.9);
- 3D geometry beyond the bounding geometry of floors, ceilings and slabs (chapter 15) and the
  faces of roofs (chapter 16): meshes of walls with their openings cut, of floors, ceilings, roofs
  and stairs are not normative in any 0.x draft yet, and neither is the structure between a ceiling
  and the floor of the level above;
- ceilings of any form but flat, tray and vaulted, a vault's ridge that follows the room's walls,
  and layers of a floor's thickness;
- finishes of a wall's ends, of baseboards and trim, and regions of a floor or a ceiling; a texture's
  coordinates on a tray's vertical step, a slab, a roof or a stair (18.3); a material's transparency,
  emission, clear coat or sheen; a map in any image format but PNG, JPEG, WebP and KTX2, such as AVIF;
- the packaged `.floorspec` form (a ZIP of `model.json` and `assets/`);
- edit operations, which are a separate specification, Floorspec Ops;
- clearance envelopes of any shape but a box, and clearances on an element rather than its type
  for core kinds (13.5);
- a nosing's projection and a riser's construction; a flight of a single riser (17.4.2); landings
  of any shape but the square or the half landing of 17.3; winders that turn other than a quarter
  or a half, or about a point other than the pivot of 17.7.1, as balanced winders do, and a newel of
  any shape but a square or a rectangle along the turn; a spiral stair's tread drawn with an arc,
  its centre column's construction, and a spiral that turns on a landing; and obstacles to headroom
  other than the floors and ceilings of a stair's two levels — a flight over another, as in a
  U-shaped stair or a spiral of more than a turn, and slabs (17.6);
- layout solving: generating a plan from a program is what tools do with a program, not what a
  program means (11.6).

## 0.6 Changes from 0.3 to 0.4

Core 0.4 is a new draft, not an edit of 0.3. The text of Core 0.3 stays published, unchanged, at
its own URLs, built from the commit that pinned it (`8a99d02` in the standard's repository); its
schema is at `/floorspec/schema/core/0.3/` and its suites at `conformance/core/0.3/` and
`conformance/migration/0.3/`, and none of them changes. This draft's schema is at
`/floorspec/schema/core/0.4/` and its suite at `conformance/core/0.4/`, which holds every 0.3 test
re-targeted to 0.4 as well as the new ones; its migration suite, `conformance/migration/0.4/`, holds
every test of 0.3's and the tests of the step from 0.3 to 0.4.

What 0.4 adds, for stairs (chapter 17):

- the **tapered treads** of winder and spiral stairs, derived exactly (17.7): a winder's nosing lines
  lie on rays from the pivot of its turn at angles that divide the turn evenly, each a whole number of
  microdegrees, and a spiral's on rays from its centre at angles that divide its sweep evenly; their
  steps, in walking order with the straight treads of a winder stair's flights; their walkline — an
  arc about the pivot or the centre, through the middle of the stair — and its length; the least
  going at the walkline and the least going at the narrow end of their tapered treads; and a spiral
  stair's centre;
- a winder stair's **newel** (17.2), the post or wall at the inner side of its turn on whose faces
  the winders' narrow ends stand, so that a winder need not narrow to a point;
- the **headroom** of winder and spiral stairs, measured over the lanes of their tapered treads as
  over a landing's (17.6);
- a stair's **`minHeadroom`**, the headroom it is designed for, and the **opening** that follows from
  it: the steps over which the floor of the level above must be open (17.6);
- the diagnostics `FS-INV-905` and `FS-INV-906` and `FS-LINT-018` and `FS-LINT-019` (chapter 10); a
  reader of 0.4 no longer reports `FS-LINT-016`, which said that 0.3 did not derive a winder's or a
  spiral's steps;
- the step from 0.3 to 0.4 of a migration (20.7), which only changes the version a document declares.

And for roofs (chapter 16):

- the **weighted straight skeleton** (16.4.3 to 16.4.5): the surface of every roof with two or more
  sloped edges, each at its own pitch, derived exactly — saltboxes, hips and wings at mixed pitches,
  gables beside one another, and oblique edges along Pythagorean directions — by a wavefront whose
  events are rational and resolved together at each event elevation, the fastest edge continuing
  where parallel edges meet on one line; a line where the roof changes pitch over one side, a
  `"break"`; and lines with the same rounded ends ordered by their kind;
- `FS-LINT-015` only for the roofs of 16.4.6, which are now exactly the ones whose surface 0.4 cannot
  derive: a shed whose outline passes its edge's line, an oblique sloped edge that is not
  Pythagorean, a gable the wavefront would pass the end of, and part of an outline enclosed by gables
  alone.

And for walls and separators (chapter 21):

- **arc edges**: a wall's or a separator's `arc`, a sagitta, makes it run along a circular arc of at most
  a semicircle between its junctions (21.1); every value derived from it comes from its **polyline**,
  made by iterated snap rounding — the arc's midpoint rounded to the grid, the two halves' sagittas
  rounded on its circle, each half halved in turn until it is within 1 mm of its chord — exact and the
  same in every implementation (21.2); its segments take part in planarity, wedges, joins, outlines and
  faces as straight edges do (21.3–21.5); and distances along it are measured on stations of rounded
  segment lengths, for openings, which stand on their chords, hosts and finish regions (21.6);
- the diagnostics `FS-INV-113` and `FS-LINT-020` (chapter 10), and `FS-INV-104` to `FS-INV-106`,
  `FS-INV-109`, `FS-INV-302`, `FS-INV-501` and `FS-INV-1002` for arc edges as for straight ones.

A 0.4 reader reads 0.1, 0.2 and 0.3 documents as well (1.2.8). Both members 0.4 adds are optional,
and absent they mean what 0.3 meant: a stair that declares no headroom, and a winder stair with no
newel. A 0.3 document read as 0.4 means exactly what it meant, and derives every value 0.3 derived
for it; what is new is that its winder and spiral stairs derive their steps, walkline, goings and
headroom too, and that each of them gets `FS-LINT-018`, when its treads meet at a point, in place of
`FS-LINT-016`.
Every roof 0.3 derived, 0.4 derives with the same values; a roof 0.3 left underived — at mixed
pitches, with an oblique Pythagorean edge, with gables beside one another or one that is not at the
end of a wing — is derived by 0.4 unless 16.4.6 excludes it, and has no `FS-LINT-015`.

Statements whose meaning changed were given new IDs, and their old IDs are retired, never reused:

| Retired | Replaced by | Why |
|---|---|---|
| `FS-CORE-1.2.5` | `FS-CORE-1.2.7` | a document targeting this draft declares `"0.4"` |
| `FS-CORE-1.2.6` | `FS-CORE-1.2.8` | a reader reads 0.3 documents as well as 0.1 and 0.2 ones |
| `FS-CORE-17.7.1` | `FS-CORE-17.7.3` | a deriver derives the steps, run, walkline and headroom of winder and spiral stairs, which 0.3 forbade |
| `FS-CORE-17.7.2` | — | `FS-LINT-016`, for a stair whose steps this draft does not derive, is no longer reported |
| `FS-CORE-16.4.1` | `FS-CORE-16.4.2` | a deriver derives the surface of every skeleton roof 16.4.6 does not exclude, where 0.3 derived only equal pitches on a rectilinear outline |
| `FS-CORE-16.5.1` | `FS-CORE-16.5.2` | a derived roof's lines include breaks, and lines with the same ends are ordered by kind |

Every other statement of 0.3 keeps its ID and its meaning; where a table it refers to has grown —
a stair's members (`FS-CORE-17.1.1`), a winder stair's form (`FS-CORE-17.2.1`), the order of
evaluation (`FS-CORE-10.3.1`) — the statement applies to the new rows too, and a new member's own
constraint is a statement of its own (`FS-CORE-17.1.3`, `FS-CORE-17.2.3`).

## 0.7 Changes from 0.2 to 0.3

Core 0.3 was a new draft, not an edit of 0.2. The text of Core 0.2 stays published, unchanged, at
its own URLs, built from the commit that pinned it (`6f9bc07` in the standard's repository); its
schema is at `/floorspec/schema/core/0.2/` and its suite at `conformance/core/0.2/`, and neither
changes. This draft's schema is at `/floorspec/schema/core/0.3/` and its suite at
`conformance/core/0.3/`, which holds every 0.2 test re-targeted to 0.3 as well as the new ones.

What 0.3 added:

- a door or window type's **operation** — how its leaves or sashes move (8.4);
- the **net clear opening** — width, height and, for a window, area — that a door or window type
  declares as its maker states it, and that an opening may override (7.1, 7.2, 8.4); a deriver
  reports it as declared, and never computes one (7.4);
- **floors and ceilings** (chapter 15): every room's floor, at its level's elevation or sunk below or
  raised above it, with a thickness from the room or its level (`floor`, a level's
  `floorThickness`); its ceiling, flat, tray or vaulted, at a height from the room or its level
  (`ceiling`, a level's `ceilingHeight`); their exact bounding geometry; and `surface` hosts that
  sit on them (15.6);
- a slab's **purpose** (6.7), and the bounding geometry of every slab (15.7);
- how a reader draws an extension element's fallback model and plan symbol in the element's frame
  (12.6);
- the diagnostics `FS-INV-305` to `FS-INV-308` and `FS-INV-701` to `FS-INV-703` (chapter 10);
- the mapping of operations, clear openings, floors, ceilings and slab purposes to IFC4 (Annex A).

And for the starter library (8.1):

- a type's or a material's **source** — the library, its version and the item it was copied from —
  recorded as provenance only: nothing derives from it, and a document that has one is as complete
  on its own as one that does not (8.1, 8.5).

And roofs (chapter 16):

- **roofs**, a collection of its own (1.1): a footprint, a pitch, gables and overhangs edge by edge,
  and the eave outline derived from them (16.1–16.3); the surface — faces, gable ends, ridges, hips
  and valleys — of every flat roof, every shed roof and every equal-pitch roof on a rectilinear
  outline, exact (16.4, 16.5); and a lint, not an error, for a roof whose surface this draft does
  not derive;
- the diagnostics `FS-INV-801` to `FS-INV-805` and `FS-LINT-015` (chapter 10), and the mapping of
  roofs to IFC4 (Annex A).

And for stairs (chapter 17):

- **stairs**, the `stairs` collection: straight, L-shaped, U-shaped, winder and spiral stairs between
  two levels of a building, each with its riser count or greatest riser height, its tread, width
  and handrail (17.1, 17.2); for every stair its foot and head rooms, rise, riser count and height
  and box, and for a straight, L-shaped or U-shaped one its steps, run, walkline and headroom
  (17.3–17.6);
- in circulation, a stair joins the room at its foot to the room at its head, and a building with a
  stair no longer joins its levels through rooms of function `circulation` (14.1);
- the diagnostics `FS-INV-901` to `FS-INV-904` and `FS-LINT-016` (chapter 10), and the mapping of
  stairs to IFC4 (Annex A).

And for materials, assets and finishes (chapter 18):

- **physically based materials**: a material's `metallic` and `roughness` (18.1), and its texture's
  normal, metallic-roughness and occlusion maps beside its base colour map, all laid with one tile
  of a real-world size, with an `offset` and a `rotation` (18.2), on surface coordinates every
  renderer shares (18.3);
- **the package**: an asset's `path` is relative to the directory that holds the document, an
  asset may declare its `byteLength`, and a **package validator**, given the package's files,
  checks each one's digest and length (18.4);
- **finishes**: a wall's `finishes` override, on one face or on a rectangular region of one, the
  finish the face inherits from the room it faces (18.5), and a deriver resolves the finish of every
  floor, ceiling and wall face (18.6);
- the diagnostics `FS-INV-1001` to `FS-INV-1007` (chapter 10), and the mapping of materials and
  finishes to IFC4 (Annex A).

And design options (chapter 19):

- **option sets** and **options**, the collections `optionSets` and `options`: every set has
  options and exactly one primary (19.1), and a junction, wall, separator, opening, room, slab,
  roof, stair or extension element is in at most one option, by its `option` member (19.2);
- **designs**, each choosing one option of every set, and the **view** of a design — the document
  as seen in it (19.3); a reference may not cross from one option into another (19.4);
- validity of the primary design and of every option against the primary of every other set, the
  **checked designs** (19.5), with a diagnostic's `design` naming the option design it was found in
  (10.2); the values a deriver derives for a design it is asked for, and `options`, which compares
  every option of a set with the primary design (19.6); exports of one design (19.7);
- the diagnostics `FS-INV-1101`, `FS-INV-1102` and `FS-LINT-017` (chapter 10), and Annex A's
  `Floorspec_Design`.

And migration (chapter 20):

- the **migration** of a 0.1 or 0.2 document to a later draft: a deterministic function of the
  document and the target, made of one step per draft, that rewrites only the version declaration
  and moves, into a record in `extras`, the members whose meaning the later draft changed — so that a
  reader of the target reads the migration exactly as it reads the document (20.6); a **migrator**
  conformance class (0.2) and its diagnostics `FS-MIG-001` and `FS-MIG-002` (20.9);
- the policy that every major version ships a normative migration from the one before it and a
  reference migrator, and that a reader of a major reads the one before it (20.8).

A 0.3 reader reads 0.1 and 0.2 documents as well (1.2.6 of 0.3; 1.2.8 here). Every member 0.3 added is optional, and
its absence means that nothing is declared, or what an earlier draft assumed: a 0.2 document read
as 0.3 means exactly what it meant. Its floors, ceilings and slabs are derived from the defaults —
a floor at the level's elevation and a flat ceiling at the level's height, the elevations 0.2 gave
a `surface` host — so every value 0.2 derived for it is unchanged, and what is new is only that
its floors, ceilings and slabs are derived too. It has no stair, so its door graph joins its levels
through rooms of function `circulation` exactly as 0.2's did (14.1), and its derived `stairs`, like
its `roofs`, are empty. It has no option set, so its one design is its primary design, whose view
is the document itself, and nothing is derived for `options` (19.3, 19.6).

Rooms' `wallFinish`, `floorFinish` and `ceilingFinish` and layers' `material` are members of 0.1,
so a 0.1 or 0.2 document read as 0.3 derives its finishes too (18.6): each room's floor and
ceiling, and each wall face that a room or a layer finishes, with no overrides and no regions.

Statements whose meaning changed were given new IDs, and their old IDs are retired, never reused:

| Retired | Replaced by | Why |
|---|---|---|
| `FS-CORE-1.2.3` | `FS-CORE-1.2.7` | a document declares the draft it targets; 0.3 replaced it with `FS-CORE-1.2.5`, which 0.4 retired in turn |
| `FS-CORE-1.2.4` | `FS-CORE-1.2.8` | a reader reads earlier drafts' documents; 0.3 replaced it with `FS-CORE-1.2.6`, which 0.4 retired in turn |

Every other statement of 0.2 keeps its ID and its meaning; where a table it refers to has grown,
the statement applies to the new rows too. The frame of a `surface` host (13.1, `FS-CORE-13.1.1`)
is now at its room's derived floor or ceiling (`FS-CORE-15.6.1`); for every document 0.2 could
express, that is the elevation 0.2 gave it.

## 0.8 Changes from 0.1 to 0.2

Core 0.2 was a new draft, not an edit of 0.1. The text of Core 0.1 stays published, unchanged, at
its own URLs, built from the commit that pinned it (`32a7047` in the standard's repository); its
schema is at `/floorspec/schema/core/0.1/` and its suite at `conformance/core/0.1/`, and neither
changes.

What 0.2 added:

- the **program** — the brief of items and the adjacency graph — and a room's `brief` (chapter 11);
- the **extension mechanism in full**: the declaration object, registry entries, dependencies,
  extension elements and their fallbacks (chapter 12);
- **hosting** and **clearance envelopes** (chapter 13), with clearances on door and window types;
- **circulation** — the door graph of each building, its entries, which rooms are reachable and
  which sleeping rooms are reached only through another (chapter 14);
- the diagnostics `FS-CFG-001`, `FS-INV-401` to `FS-INV-403`, `FS-INV-501` to `FS-INV-506`,
  `FS-INV-601` to `FS-INV-605` and `FS-LINT-008` to `FS-LINT-014` (chapter 10).

Circulation adds no member: it is derived from walls, rooms and openings that 0.1 already has, so
it is derived, and its lints reported, for a 0.1 document read as 0.2 or 0.3 too.

The statements 0.2 retired, each with the statement of this draft that replaces it:

| Retired | Replaced by | Why |
|---|---|---|
| `FS-CORE-1.2.1` | `FS-CORE-1.2.7` | a document declares the draft it targets; in 0.2 that was `FS-CORE-1.2.3`, and in 0.3 `FS-CORE-1.2.5`, each retired in turn |
| `FS-CORE-1.6.5` | `FS-CORE-1.6.9` | a reader derives fallbacks, placements and clearances from extension elements it does not implement (12.5) |

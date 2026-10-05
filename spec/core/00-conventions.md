# 0. Conventions

> [!warning] Floorspec Core 0.3 — Draft
> This is a working draft. It carries no compatibility promise: a later 0.x draft may change any
> part of it. Floorspec stays 0.x until the 1.0 criteria are met (FLR-ADR-017).

Floorspec Core defines a document that describes a building as code: its levels, the walls on a
junction graph, the rooms that walls enclose, the openings hosted on walls, the types and
materials they use — including how a door or window operates and the net clear opening its maker
declares — the program the building is meant to satisfy, and the elements that extensions
add — placed on their hosts, with the clearances they need. It defines what makes a document
valid, the exact geometry a conformant tool derives from it — including which rooms a person can
walk to, and every room's floor and ceiling, and the surfaces of its roofs — and the one byte
sequence that every conformant writer produces for it.

## 0.1 Normative language

The key words `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT` and `MAY` in this specification are to be
interpreted as described in BCP 14 (RFC 2119, RFC 8174) when, and only when, they appear in
capitals, as shown here. Floorspec does not use `SHALL`, `REQUIRED`, `RECOMMENDED` or `OPTIONAL`.

Every sentence that uses one of those keywords is a *normative statement* and ends with a tag
giving its stable identifier and level, for example `{#FS-CORE-5.3.1 MUST}`. The identifier is
`FS-CORE-<chapter>.<section>.<n>`. An identifier is never reused, including after the statement it
named is removed.

Every statement at level `MUST` or `MUST NOT` is exercised by at least one test in the conformance
suite (`conformance/core/0.3/`), and the build that publishes this specification fails if one is
not. Tables, figures and informative callouts are normative only where a tagged statement says so.

## 0.2 Conformance classes

Floorspec Core 0.3 places requirements on these kinds of thing:

| Class | What it is | What it must do |
|---|---|---|
| **Document** | a JSON text claiming to be Floorspec | satisfy every requirement on documents (chapters 1–8, 11–13, 15–18) |
| **Reader** | software that loads documents | apply defaults and the version and extension rules (1.2, 1.5, 1.6, 12.1) |
| **Writer** | software that produces documents | produce valid documents; preserve what it does not understand (1.6, 1.7) |
| **Canonicalizer** | software that produces the canonical form | produce exactly the bytes of chapter 9 |
| **Validator** | software that reports validity | report the diagnostics of chapter 10, given the known extensions it is configured with (12.2) |
| **Package validator** | a validator that is also given the files of the document's package (18.4) | check every packaged asset against its file, as well (18.4) |
| **Deriver** | software that computes geometry | produce exactly the derived values of chapters 5–7 and 11–18 |
| **Registry entry** | the metadata of one version of an extension (12.2) | match the registry entry schema |

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
envelopes, and circulation to the walls-and-rooms draft (0.7), and Core 0.3 adds the operation and
net clear opening of door and window types, the floors and ceilings of rooms, roofs and stairs (0.6). These are
reserved for later drafts and a 0.3 document cannot contain them:

- the surface of a roof with sloped edges at different pitches, or of one with two or more sloped
  edges on an outline with an oblique edge (16.4.4), and a roof's footprint that follows its walls;
- design options (`optionSets`, and option membership on elements);
- a door's or window's frame, glazing and hardware, and a casement's hand or a pivot's axis (8.4);
- arc walls (core walls are straight);
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
- the steps, run, walkline and headroom of a winder or a spiral stair (17.7); a nosing's
  projection and a riser's construction; a flight of a single riser (17.4.2); landings of any shape
  but the square or the half landing of 17.3; and obstacles to headroom other than the floors and
  ceilings of a stair's two levels — a flight over another, as in a U-shaped stair, and slabs
  (17.6);
- layout solving: generating a plan from a program is what tools do with a program, not what a
  program means (11.6).

## 0.6 Changes from 0.2

Core 0.3 is a new draft, not an edit of 0.2. The text of Core 0.2 stays published, unchanged, at
its own URLs, built from the commit that pinned it (`6f9bc07` in the standard's repository); its
schema is at `/floorspec/schema/core/0.2/` and its suite at `conformance/core/0.2/`, and neither
changes. This draft's schema is at `/floorspec/schema/core/0.3/` and its suite at
`conformance/core/0.3/`, which holds every 0.2 test re-targeted to 0.3 as well as the new ones.

What 0.3 adds:

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
- the diagnostics `FS-INV-305` to `FS-INV-308` and `FS-INV-701` to `FS-INV-703` (chapter 10);
- the mapping of operations, clear openings, floors, ceilings and slab purposes to IFC4 (Annex A).

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

A 0.3 reader reads 0.1 and 0.2 documents as well (1.2.6). Every member 0.3 adds is optional, and
its absence means that nothing is declared, or what an earlier draft assumed: a 0.2 document read
as 0.3 means exactly what it meant. Its floors, ceilings and slabs are derived from the defaults —
a floor at the level's elevation and a flat ceiling at the level's height, the elevations 0.2 gave
a `surface` host — so every value 0.2 derived for it is unchanged, and what is new is only that
its floors, ceilings and slabs are derived too. It has no stair, so its door graph joins its levels
through rooms of function `circulation` exactly as 0.2's did (14.1), and its derived `stairs`, like
its `roofs`, are empty.

Rooms' `wallFinish`, `floorFinish` and `ceilingFinish` and layers' `material` are members of 0.1,
so a 0.1 or 0.2 document read as 0.3 derives its finishes too (18.6): each room's floor and
ceiling, and each wall face that a room or a layer finishes, with no overrides and no regions.

Statements whose meaning changed were given new IDs, and their old IDs are retired, never reused:

| Retired | Replaced by | Why |
|---|---|---|
| `FS-CORE-1.2.3` | `FS-CORE-1.2.5` | a document targeting this draft declares `"0.3"` |
| `FS-CORE-1.2.4` | `FS-CORE-1.2.6` | a reader reads 0.2 documents as well as 0.1 ones |

Every other statement of 0.2 keeps its ID and its meaning; where a table it refers to has grown,
the statement applies to the new rows too. The frame of a `surface` host (13.1, `FS-CORE-13.1.1`)
is now at its room's derived floor or ceiling (`FS-CORE-15.6.1`); for every document 0.2 could
express, that is the elevation 0.2 gave it.

## 0.7 Changes from 0.1 to 0.2

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
| `FS-CORE-1.2.1` | `FS-CORE-1.2.5` | a document declares the draft it targets; in 0.2 that was `FS-CORE-1.2.3`, which 0.3 retired in turn |
| `FS-CORE-1.6.5` | `FS-CORE-1.6.9` | a reader derives fallbacks, placements and clearances from extension elements it does not implement (12.5) |

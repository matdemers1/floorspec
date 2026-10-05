# 0. Conventions

> [!warning] Floorspec Ops 0.3 — Draft
> This is a working draft with no compatibility promise. It operates on Floorspec Core 0.3
> documents — and, because a Core 0.3 reader reads 0.2 and 0.1 documents (Core §1.2.6), on Core
> 0.2 and 0.1 documents too. Floorspec Ops is versioned independently of Core (FLR-ADR-008), and stays 0.x
> until the 1.0 criteria are met (FLR-ADR-017).

Floorspec Core says what a building *is*. Floorspec Ops says how one **changes**: a small set of
**primitive** operations with exact semantics, **composite** operations defined as sequences of
primitives, a **reference grammar** that lets a person or an agent say "the north wall of R5" or
"2' 6\"" instead of computing coordinates, and a **transaction** that either commits a whole
batch or changes nothing. Every editor binding — the D3 Floorspec web app, its MCP server, a CLI —
is a binding of these operations, so two tools that implement Floorspec Ops make the same edit the
same way, to the byte.

## 0.1 Normative language

The key words `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT` and `MAY` are used as in Floorspec Core
§0.1, and every normative statement ends with a tag `{#FS-OPS-<chapter>.<section>.<n> LEVEL}`.
An identifier is never reused, including after the statement it named is retired (0.4).
Every `MUST` and `MUST NOT` is exercised by the conformance suite in `conformance/ops/0.3/`.

## 0.2 Conformance

An **applier** is software that applies a batch of operations to a Floorspec Core document. It is
the only conformance class of Floorspec Ops. An applier implements named drafts of Ops, as a Core
reader implements named drafts of Core: a request does not name one, so a binding — an editor's
API, an MCP server, a CLI — says which it implements. What tells an Ops 0.3 applier from an Ops
0.2 one is the documents it accepts: one that implements 0.3 applies a batch to a document that
declares `"0.3"`, and one that implements only 0.2 rejects that document with `FS-OPS-002`
(1.2.1), since a Core 0.2 validator does not implement 0.3 (Core §1.2.2).

An applier is tested by giving it a document A and a batch, and comparing what it returns — a
committed document B in canonical form, or a rejection with diagnostics — with the expected
result.

Terms from Floorspec Core keep their meanings: collection, junction, edge, face, room polygon,
host, canonical form, content hash, diagnostic. A document is **valid** when a Core 0.3 validator
reports it valid (Core §10.1) — which, for a document that declares `"0.1"` or `"0.2"`, is exactly
when a validator of that draft does (Core §1.2.6). The validator has the known extensions (Core §12.2) the
applier is configured with; the conformance suite configures none.

## 0.3 Elements

In this specification an **element** is any of the three kinds of thing that have an ID in a
document's one space of IDs (Core §3.1.3):

- an element of one of Core's fifteen collections (Core §1.4) — eleven, and Core 0.3's `roofs`,
  `stairs`, `optionSets` and `options`;
- a **program item** (Core §11.1), in the program's `items`;
- an **extension element** (Core §12.5), in a collection of an extension's top-level data.

Everything this specification says of an element — that an operation addresses it by ID, that
`removeElement` removes it, that a lock names it, that `created` and `removed` list it — says it
of program items and extension elements too, unless a sentence names the kinds it means.
Program items and extension elements exist only in a document that declares `"0.2"` or `"0.3"`:
in one that declares `"0.1"` the program is not a member and top-level extension data is opaque
(Core §1.2.6). Which a working copy declares is read from the working copy as it stands.

## 0.4 Changes from earlier drafts

**From 0.2 to 0.3.** Ops 0.3 is a new draft, not an edit of 0.2. The text of Ops 0.2 stays
published, unchanged, at its own URLs, built from the commit that pinned it (`6f9bc07` in the
standard's repository); its schema is at `/floorspec/schema/ops/0.2/` and its suite at
`conformance/ops/0.2/`, and neither changes. This draft's schema is at `/floorspec/schema/ops/0.3/`
and its suite at `conformance/ops/0.3/`, which holds every 0.2 test on the same documents, as well
as the new ones.

What 0.3 adds:

- **Core 0.3 documents**: A and the result are validated as Core 0.3 validates (0.2), so a door
  or window type's `operation` and `clearOpening`, an opening's own `clearOpening` (Core
  §7.1, §8.4), a level's `floorThickness` and `ceilingHeight`, a room's `floor` and `ceiling` and a
  slab's `purpose` (Core §1.8, §6.7, §15) are members a batch can set and unset like any other
  (2.3), and the result is judged by Core 0.3's invariants — a clear opening larger than its
  opening or its type, or an area where none may be, a ceiling not above its floor, a vault
  without a ridge line, or a tray whose border does not fit its room, rejects the batch with the
  Core diagnostic (1.2.3);
- `moveRoom` moves a vaulted ceiling's ridge with the room (4.3, `FS-OPS-4.3.2`): the ridge is a
  plan point, which nothing else moves;
- a batch may make a 0.2 document declare `"0.3"` with `setProperty` of `$document`
  `/floorspec`, as a 0.2 batch could make a 0.1 document declare `"0.2"`;
- **roofs** (Core chapter 16), Core 0.3's twelfth collection: `addElement` adds one, minting an
  ID with the prefix `RF` (1.5), `setProperty` and `unsetProperty` edit its pitch, its gables and
  its overhangs like any other member (2.3), and removing its level takes it or is blocked by it
  (2.2); for that, Ops 0.3 has a request schema of its own, `schema/ops/0.3/`, which is Ops 0.2's
  with `roofs` among `addElement`'s collections (1.1.3). The result is judged by Core 0.3's roof
  invariants — an edge out of range, a roof part flat, or one whose every edge is a gable rejects
  the batch with the Core diagnostic (1.2.3) — while a roof whose surface Core 0.3 does not derive
  only carries its lint;
- **stairs** (Core chapter 17), Core 0.3's thirteenth collection: `addElement` adds one, minting
  an ID with the prefix `ST` (1.5), and `stairs` is among `addElement`'s collections in
  `schema/ops/0.3/` as `roofs` is (1.1.3); a stair depends on both its levels, so removing either
  level takes the stair with it or is blocked by it (2.2); stairs come after roofs in the inverse's
  order (1.6); and a batch sets and unsets a stair's members like any other's, judged by Core 0.3's
  stair invariants (`FS-INV-901` to `FS-INV-904`, 1.2.3);
- the text says what the oracle already did in four places — the IDs minting counts (1.5), a
  room member read only as an ID or a room name (3.3), `moveWall`'s `wall` never a separator
  (4.2), and a room on another level never beside a wall (4.2, 4.10) — each pinned by a test;
- **design options** (Core chapter 19): option sets and options are Core 0.3's fourteenth and fifteenth
  collections, added with `addElement` (prefixes `OS` and `OP`, 1.5), removed by the rows of the
  removal table for them (2.2), and edited with the primitives Ops already has — switching a set's
  primary is `setProperty` of its `/primary`, moving an element to another option `setProperty` of
  its `/option`, making it common `unsetProperty` of it. The request's `context` gains `option`, the
  option a batch edits in: every element the batch adds that may be in an option is added in it, and
  references read faces and rooms in the design that chooses it (2.8). Normalization merges and
  planarizes a level option by option, never across two options (5.5). The result is judged by Core
  0.3's option invariants and each checked design's (Core §19.5), and a rejection carries their
  diagnostics, each with its `design` (1.2.3).

Ops 0.3 adds no operation, so its requests have the shape of Ops 0.2's, and
`schema/ops/0.3/request.schema.json` is Ops 0.2's with two differences: an `addElement` may name the
collection `roofs`, `stairs`, `optionSets` or `options` (1.1), and `context` may have `option` (2.8). Applied to a document that declares `"0.2"` or `"0.1"`, a request commits or is
rejected exactly as it was under Ops 0.2, unless its batch makes the document declare `"0.3"`: a
0.2 or 0.1 document has no vaulted ceiling, so `moveRoom` expands for it as it did, and no roof or
stair, so removing a level takes or is blocked by what it was. No statement of
0.2 changed its meaning but one, which 0.3 retires; where a table or a list it refers to has grown —
the steps of `moveRoom`, the collections, the minting prefixes, the removal table and the order of
the inverse among them — the statement applies to what was added too.

| Retired | Replaced by | Why |
|---|---|---|
| `FS-OPS-1.1.2` | `FS-OPS-1.1.3` | a request has the shape `schema/ops/0.3` gives it |

**From 0.1 to 0.2.** Ops 0.2 was a new draft, not an edit of 0.1. The text of Ops 0.1 stays
published, unchanged, at its own URLs, built from the commit that pinned it (`3bf4f35` in the
standard's repository); its schema is at `/floorspec/schema/ops/0.1/` and its suite at
`conformance/ops/0.1/`, and neither changes. Ops 0.2's schema is at `/floorspec/schema/ops/0.2/` and its suite at
`conformance/ops/0.2/`, which holds every 0.1 test that still applies, re-targeted to 0.2, as
well as the new ones.

What 0.2 added:

- **Core 0.2 documents**: A and the result were validated as Core 0.2 validates;
- program items and extension elements as **elements** (0.3): minted (1.5), removed with their
  rows in the removal table (2.2), addressed by `setProperty` (2.3), inverted (1.6) and locked
  (6.1);
- the program as something to edit: `addElement` into the program's `items` (2.1), the
  adjacency primitives `setAdjacency` and `removeAdjacency` (2.6), the selectors `item <item>`
  and `brief of <room>` (3.3), areas (3.6), `addRoom`'s `brief` and `setRoomBrief` (4.6), and
  `addProgramItem` (4.9);
- extension elements as something to place: `addElement` into an extension's collection (2.1),
  `placeElement` and `moveElement` (4.10), what `moveRoom` and `removeWall` do to the elements on
  a room's floor and ceiling (4.3, 4.7), how hosted elements follow their hosts (2.7) and what a
  split wall does to them (5.2);
- relative edits: `moveOpening` by a length along its wall (4.5), and `addLevel`, above or below
  another level or at an elevation (4.8).

Applied to a document that declares `"0.1"`, a request that Ops 0.1 accepts commits or is
rejected exactly as it was under Ops 0.1, unless its batch makes the document declare `"0.2"`.

Statements whose meaning changed in 0.2 were given new IDs, and their old IDs are retired, never reused:

| Retired | Replaced by | Why |
|---|---|---|
| `FS-OPS-1.1.1` | `FS-OPS-1.1.2` | a request has the shape `schema/ops/0.2` gives it |
| `FS-OPS-4.5.1` | `FS-OPS-4.5.3` | `moveOpening` also moves by a length (4.5.2), which needs no width |

Every other statement of 0.1 keeps its ID and its meaning; where a table or a list it refers to
has grown — the collections, the minting prefixes, the removal table, the selectors, the members
of `$document`, the steps of a composite — the statement applies to what was added too.

## 0.5 Not in this draft

Composite operations on roofs — a roof's footprint is plan points (Core §16.1), which `moveRoom`,
`moveWall` and `resizeRoom` do not move — and on stairs — drawing one, or moving one with a room (a
stair's `position` is a plan point, which `moveRoom` does not move) — and composites on design
options: copying an element into another option, or adding an option set and its options in one
operation; references inside an extension's own members,
which core does not read and so no removal follows (an electrical circuit that names a device);
an angle grammar (a host's `rotation` is an integer of microdegrees, Core §2.4); dimension locks
other than the two of chapter 6; operations that edit several documents at once.

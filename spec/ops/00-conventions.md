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

- an element of one of Core's eleven collections (Core §1.4);
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
`conformance/ops/0.2/`, and neither changes. This draft's suite is at `conformance/ops/0.3/`, which
holds every 0.2 test on the same documents, as well as the new ones.

What 0.3 adds:

- **Core 0.3 documents**: A and the result are validated as Core 0.3 validates (0.2), so a door
  or window type's `operation` and `clearOpening`, and an opening's own `clearOpening` (Core
  §7.1, §8.4), are members a batch can set and unset like any other (2.3), and the result is
  judged by Core 0.3's invariants — a clear opening larger than its opening or its type, or an
  area where none may be, rejects the batch with the Core diagnostic (1.2.3);
- a batch may make a 0.2 document declare `"0.3"` with `setProperty` of `$document`
  `/floorspec`, as a 0.2 batch could make a 0.1 document declare `"0.2"`;
- the text says what the oracle already did in four places — the IDs minting counts (1.5), a
  room member read only as an ID or a room name (3.3), `moveWall`'s `wall` never a separator
  (4.2), and a room on another level never beside a wall (4.2, 4.10) — each pinned by a test.

Ops 0.3 adds no operation and changes no member, so its requests have exactly the shape of Ops
0.2's: they match `schema/ops/0.2/request.schema.json`, and Ops 0.3 has no request schema of its
own (1.1). Applied to a document that declares `"0.2"` or `"0.1"`, a request commits or is
rejected exactly as it was under Ops 0.2, unless its batch makes the document declare `"0.3"`. No
statement of 0.2 changed its meaning, so 0.3 retires none; where a table it refers to has grown,
the statement applies to what was added too.

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

Operations on roofs, stairs and design options; references inside an extension's own members,
which core does not read and so no removal follows (an electrical circuit that names a device);
an angle grammar (a host's `rotation` is an integer of microdegrees, Core §2.4); dimension locks
other than the two of chapter 6; operations that edit several documents at once.

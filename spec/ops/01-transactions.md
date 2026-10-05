# 1. Operations, batches and transactions

## 1.1 Operations and batches

An **operation** is a JSON object whose `op` member names it — `{ "op": "moveJunction", "id": "J4",
"to": [390144, 0] }`. A **batch** is a JSON array of operations, applied in order as one
transaction. An **apply request** is the JSON object

```json
{ "batch": [ … ], "context": { "locks": [ … ], "retired": [ … ] } }
```

where `context` is optional: `locks` are the locks in force (chapter 6), and `retired` lists IDs
that once existed in this document's history and therefore are never minted again (1.5). The
JSON Schema `schema/ops/0.3/request.schema.json` gives the shape of an apply request: every
operation, every member each has, and the JSON type of each member. Ops 0.3 adds no operation and
no member, and gives every member the JSON type Ops 0.2's schema, `schema/ops/0.2/`, gives it: its
schema is Ops 0.2's with `"stairs"`, the collection Core 0.3 adds, among `addElement`'s collections
(0.4).

An apply request's batch MUST contain at least one operation and only operations this specification defines, each with exactly the members its definition lists, each of the JSON type schema/ops/0.2 gives it; otherwise the applier MUST reject the request with `FS-OPS-001`. {#FS-OPS-1.1.2 MUST}
Where a definition says an operation takes exactly one of several members — `moveOpening`'s `at`
and `by` (4.5), `addLevel`'s `elevation`, `above` and `below` (4.8), a wall-face host's `side`
and `toward` (4.10) — an operation with none of them, or with more than one, does not have
exactly the members its definition lists, and neither does one with a member its definition
allows only beside another (`moveOpening`'s `toward` without `by`): the request is malformed. A
host reference (4.10) has exactly the members of its `mode`, and `addElement`'s `collection` is
one of the collections 2.1 names unless the operation has an `extension`.
The rule is about requests. The inverse of a committed result (1.6) is a batch too, and it may be
empty; an empty inverse is never applied.

## 1.2 The transaction

Before anything else, the applier checks the request (1.1.1). Applying a batch to a document A is
then a transaction of six steps:

1. **Check A.** A must be a valid Floorspec Core document (0.2), and then every lock in force
   must apply to A (6.1.1).
2. **Resolve.** Every reference in every operation — a length written `"2' 6\""`, a selector such as
   `"north wall of R5"` — is resolved against the document as it stands *before that operation*,
   to IDs and integers (chapter 3). Within an operation, references are resolved in the order the
   definition lists the members, except that a position is resolved after the width it depends
   on (4.5).
3. **Expand.** Every composite operation is replaced by the primitive operations it is defined as
   (chapter 4).
4. **Apply.** The primitives are applied in order to a working copy of A (chapter 2).
5. **Normalize.** The working copy is made planar and consistent (chapter 5).
6. **Validate and commit.** The working copy is validated (Core tiers 3 and 4, as 0.2 says) and then checked
   against the locks in force (chapter 6). If it is valid and breaks no lock, it is the result B,
   in canonical form. Otherwise the batch is rejected.

Steps 2 to 4 alternate operation by operation: operation *n* is resolved against the working copy
left by operations 1 to *n* − 1. Normalization runs once, after the last operation, and validation
once, after normalization — so a batch may pass through invalid intermediate states, as drawing a
room wall by wall does, and only its end state is judged.

If A is not a valid document, the applier MUST reject the request with `FS-OPS-002`. {#FS-OPS-1.2.1 MUST}

If any step fails, the applier MUST reject the whole batch and MUST NOT return or retain any part of its effect: the document is exactly A. {#FS-OPS-1.2.2 MUST}

When the result is invalid, the rejection MUST carry the Core diagnostics with severity `error` that the result has. {#FS-OPS-1.2.3 MUST}
That is how an agent learns why an edit was refused: the same coded diagnostics, with their fix
operations, that a validator would report for the document it tried to make.

## 1.3 The result

An applier returns a **result** object:

| Member | Present | Meaning |
|---|---|---|
| `status` | always | `"committed"` or `"rejected"` |
| `document` | committed | B, as its canonical form (Core §9.2) |
| `hash` | committed | B's content hash (Core §9.3) |
| `resolved` | committed | the primitive operations actually applied, with every reference resolved to IDs and integers (1.4) |
| `created` | committed | the IDs of elements (0.3) that exist in B and not in A, sorted |
| `removed` | committed | the IDs of elements (0.3) that exist in A and not in B, sorted |
| `inverse` | committed | a batch that turns B back into A (1.6) |
| `diagnostics` | rejected | why: `FS-OPS-` diagnostics, or the Core diagnostics of the result (1.2.3) |

A committed result's `document` MUST be exactly the canonical form of B. {#FS-OPS-1.3.1 MUST}

Applying the same batch, with the same context, to the same document MUST produce the same result, byte for byte, on every platform and in every run. {#FS-OPS-1.3.2 MUST}
Operations use no clock, no randomness and no floating point in any value they produce; IDs are
minted deterministically (1.5).

## 1.4 Echoing resolved operations

The `resolved` member lists the primitives the transaction applied, in order, as the expansion of
the batch: every length as an integer of base units, every point as `[x, y]`, every selector as an
ID, every minted ID spelled out. Normalization's own changes (chapter 5) are not listed; they are
visible in `created`, `removed` and in B.

A committed result's `resolved` MUST be a batch of primitives that, applied to A in place of the original batch, commits the same document B. {#FS-OPS-1.4.1 MUST}
This is what lets a person or an agent see what "2 ft wider" meant in base units, and lets a log
replay an edit without resolving its references again. The replay names every ID the batch
minted, and minting (1.5) skips every ID named or minted earlier in a batch alike, so the IDs
normalization mints in the replay are the ones it minted the first time.

## 1.5 Minting IDs

An operation that creates an element may name its ID (`"id": "W12"`). When it does not, the applier
mints one: the element's **prefix** followed by a decimal integer.

| Collection | Prefix | Collection | Prefix |
|---|---|---|---|
| `buildings` | `B` | `openings` | `O` |
| `levels` | `L` | `rooms` | `R` |
| `junctions` | `J` | `slabs` | `SL` |
| `walls` | `W` | `separators` | `S` |
| `types` | `T` | `materials` | `M` |
| `assets` | `A` | the program's `items` | `P` |
| every extension collection | `X` | `stairs` (Core 0.3) | `ST` |

The integer is one more than the largest *n* among the IDs that match `^<prefix>[0-9]+$` — the IDs
of every element in A (0.3), of every element in the working copy as it stands, every ID named or
minted earlier in the same batch (including any removed again since), and those in
`context.retired` — or `1` when there are none. The working copy can hold IDs that are neither in
A as elements nor named by the batch: a batch that makes a Core 0.1 document declare `"0.2"` or
`"0.3"` turns its top-level extension data, opaque under 0.1, into extension elements (0.3), and
their IDs count. Every
extension collection shares the one prefix `X`: an extension's collections are named by the
extension, and an applier that has never heard of it still mints the same ID.

An applier MUST mint IDs exactly as this section defines. {#FS-OPS-1.5.1 MUST}

An operation that names an ID already used anywhere in the working copy, or listed in `context.retired`, MUST be rejected with `FS-OPS-005`. {#FS-OPS-1.5.2 MUST}

> [!note] Why "one more than the largest"
> Minting the smallest free number would hand a deleted wall's ID to the next wall, and every log,
> comment and changeset that named the old one would silently point at the new one. The largest
> number plus one cannot reuse an ID that A has or that the batch has used, even one it removed
> again; `retired`, which the store keeps, stops it reusing one that was deleted in an earlier
> transaction.

## 1.6 The inverse

The `inverse` of a committed result is the **structural difference** from B back to A, as
primitives in this order:

1. for every element in both A and B, in the same collection, whose content differs, by
   collection in the order of step 2 and by ID: `setProperty` for each top-level member whose
   value differs or that A has and B lacks, and `unsetProperty` for each that B has and A lacks,
   by member name;
2. `removeElement` (without `cascade`) for every element in B and not in A, in the order
   extension elements, openings, rooms, slabs, stairs, separators, walls, junctions, program
   items, levels, buildings, types, materials, assets — the extension collections ordered by extension
   name and then collection name — and by ID within a collection;
3. `addElement` for every element in A and not in B, in the reverse of that collection order, and
   by ID within a collection, with the element exactly as it is in A's canonical form: a program
   item with `"collection": "items"`, an extension element with the `extension` and `collection`
   it is in (2.1);
4. the same as step 1 for `project` and `site`, addressed as `$project` and `$site` (2.3) — except
   that when the site exists in only one of A and B, it is `setProperty` or `unsetProperty` of
   `$document` `/site` — and for the document's top-level members other than the collections,
   the project and the site, addressed as `$document` — except that when both have a `program`,
   its members are compared one by one, addressed as `$document` `/program/<member>`. In this step
   A, in canonical form, is compared not with B but with the document that applying steps 1 to 3
   to B leaves, as it is.

Two elements are in the same collection when both are in one of Core's collections, both are
program items, or both are in the same collection of the same extension; an element that moved
between collections in the batch is removed from where it is in B and added where it is in A.
Step 4's comparison is what restores what is not an element: the program's adjacencies, an
extension's own top-level data, and the objects that hold collections — so it compares the
`program` and `extensions` members as steps 1 to 3 leave them, whose elements are already A's.
It compares them as they are, not in canonical form, so that an object steps 1 to 3 emptied — a
program whose only item the batch added — is removed rather than left behind, and the inverse of
a batch that turned a 0.1 document into a 0.2 one gives back a document that Core 0.1 reads.

Content is compared in canonical form: with constant defaults omitted (Core §9.2), and values equal
when their RFC 8785 serializations are. Property differences come first because an element of A
may refer to one the batch created — a split wall's first piece ends at a new junction, a room's
`brief` names a new program item — and the removal of the created element is blocked until that
reference is restored. Extension elements are removed first because nothing in core refers to
them, and program items before levels because an item may prefer one. When B is A, the inverse
is the empty batch `[]`.

An inverse is applied with no `context.retired` and no locks. Applying a committed result's inverse, when it is not empty, to B MUST commit a document whose canonical form is exactly A's. {#FS-OPS-1.6.1 MUST}

Undo is applying the inverse — a new transaction, appended to history like any other. History
never rewinds. Undo of a batch whose inverse is empty changes nothing, and applies nothing.

# 1. Operations, batches and transactions

## 1.1 Operations and batches

An **operation** is a JSON object whose `op` member names it — `{ "op": "moveJunction", "id": "J4",
"to": [390144, 0] }`. A **batch** is a JSON array of operations, applied in order as one
transaction. An **apply request** is the JSON object

```json
{ "batch": [ … ], "context": { "locks": [ … ], "retired": [ … ] } }
```

where `context` is optional: `locks` are the locks in force (chapter 6), and `retired` lists IDs
that once existed in this document's history and therefore are never minted again (1.5).

A batch MUST contain at least one operation and only operations this specification defines, each with exactly the members its definition lists; otherwise the applier MUST reject the request with `FS-OPS-001`. {#FS-OPS-1.1.1 MUST}

## 1.2 The transaction

Applying a batch to a document A is a transaction of six steps:

1. **Check A.** A must be a valid Floorspec Core document (Core §10.1).
2. **Resolve.** Every reference in every operation — a length written `"2' 6\""`, a selector such as
   `"north wall of R5"` — is resolved against the document as it stands *before that operation*,
   to IDs and integers (chapter 3).
3. **Expand.** Every composite operation is replaced by the primitive operations it is defined as
   (chapter 4).
4. **Apply.** The primitives are applied in order to a working copy of A (chapter 2).
5. **Normalize.** The working copy is made planar and consistent (chapter 5).
6. **Validate and commit.** The working copy is validated (Core tiers 3 and 4) and checked against
   the locks in force (chapter 6). If it is valid and breaks no lock, it is the result B, in
   canonical form. Otherwise the batch is rejected.

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
| `created` | committed | the IDs of elements that exist in B and not in A, sorted |
| `removed` | committed | the IDs of elements that exist in A and not in B, sorted |
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
replay an edit without resolving its references again.

## 1.5 Minting IDs

An operation that creates an element may name its ID (`"id": "W12"`). When it does not, the applier
mints one: the element's **prefix** followed by a decimal integer.

| Collection | Prefix | Collection | Prefix |
|---|---|---|---|
| `buildings` | `B` | `openings` | `O` |
| `levels` | `L` | `rooms` | `R` |
| `junctions` | `J` | `slabs` | `SL` |
| `walls` | `W` | `types` | `T` |
| `separators` | `S` | `materials` | `M` |
| | | `assets` | `A` |

The integer is one more than the largest *n* among the IDs that match `^<prefix>[0-9]+$` — those
in the working copy, those minted earlier in the same batch, and those in `context.retired` — or
`1` when there are none.

An applier MUST mint IDs exactly as this section defines. {#FS-OPS-1.5.1 MUST}

An operation that names an ID already used anywhere in the working copy, or listed in `context.retired`, MUST be rejected with `FS-OPS-005`. {#FS-OPS-1.5.2 MUST}

> [!note] Why "one more than the largest"
> Minting the smallest free number would hand a deleted wall's ID to the next wall, and every log,
> comment and changeset that named the old one would silently point at the new one. The largest
> number plus one cannot reuse an ID still in the document; `retired`, which the store keeps,
> stops it reusing one that was deleted.

## 1.6 The inverse

The `inverse` of a committed result is the **structural difference** from B back to A, as
primitives in this order:

1. `removeElement` (without `cascade`) for every element in B and not in A, in the order
   openings, rooms, slabs, separators, walls, junctions, levels, buildings, types, materials,
   assets, and by ID within a collection;
2. `addElement` for every element in A and not in B, in the reverse of that collection order, and
   by ID within a collection, with the element exactly as it is in A;
3. for every element in both whose content differs, by collection in the order of step 1 and by
   ID: `setProperty` for each top-level member whose value differs or that A has and B lacks, and
   `unsetProperty` for each that B has and A lacks, by member name;
4. the same for `project` and `site`, addressed as `$project` and `$site` (2.3), and for the
   document's top-level members other than the collections, addressed as `$document`.

Applying a committed result's `inverse` to B MUST commit a document whose canonical form is exactly A's. {#FS-OPS-1.6.1 MUST}

Undo is applying the inverse — a new transaction, appended to history like any other. History
never rewinds.

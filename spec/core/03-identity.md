# 3. Identity and references

## 3.1 Element IDs

An element's ID is its member name in its collection. IDs are opaque: nothing may be inferred
from an ID's spelling. The reference implementation mints short, kind-prefixed IDs — `W12` for a
wall, `J4` for a junction, `R5` for a room — because they are easy to read aloud and to type;
UUIDs are equally conformant.

An element ID MUST match the pattern `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`. {#FS-CORE-3.1.1 MUST}

An element ID MUST be unique across all of a document's collections, not only within its own. {#FS-CORE-3.1.2 MUST}
A reference can therefore never be ambiguous, and a diagnostic can name an element by its ID
alone.

Program items (11.1) and extension elements (12.5) share this space of IDs: the program's `items`
and every collection an extension adds count as collections for 3.1.2.

A program item's ID and an extension element's ID MUST match the pattern of 3.1.1, and MUST be
unique among all the IDs of the document, as element IDs are. {#FS-CORE-3.1.3 MUST}

> [!note] IDs across versions
> An ID identifies one element for as long as it exists: an edit changes an element's members,
> never its ID, and a deleted element's ID is not reused. That is a property of edits, so
> Floorspec Ops states it normatively; a single document cannot show it.

## 3.2 References

A **reference** is a member whose value is the ID of another element. Every reference names the
collection — and, for types, the kind — of the element it must resolve to. For this section the
program's `items` is a collection, and a program item or an extension element that holds a
reference is its referring element:

| Element | Member | Resolves to |
|---|---|---|
| Level | `building` | a building |
| Junction, Wall, Separator, Room, Slab | `level` | a level |
| Wall, Separator | `start`, `end` | a junction |
| Wall | `type` | a type of kind `wallType` |
| Wall | `base.level`, `top.level` | a level |
| Junction | `join.through[]` | a wall (5.8) |
| Opening | `wall` | a wall |
| Opening | `fill` | a type of kind `doorType` or `windowType` |
| Layer (8.3) | `material` | a material |
| Room | `wallFinish`, `floorFinish`, `ceilingFinish` | a material |
| Slab | `material` | a material |
| Material | `texture.asset` | an asset |
| Room | `brief` | a program item (11.3) |
| Program item | `level` | a level |
| Adjacency (11.2) | `a`, `b` | a program item |
| Extension element (12.5) | `host.wall` | a wall (13.3) |
| Extension element | `host.room` | a room |
| Extension element | `host.level` | a level |
| Extension element | `fallback.level` | a level (12.6) |
| Extension element | `fallback.asset`, `fallback.symbol` | an asset |

A reference MUST be a string that matches the ID pattern of 3.1. {#FS-CORE-3.2.3 MUST}

Every reference MUST resolve to an element of the collection that its member names in this table. {#FS-CORE-3.2.1 MUST}

Every reference to a type MUST resolve to a type of the kind its member names in this table. {#FS-CORE-3.2.2 MUST}

## 3.3 Level consistency

Elements that meet on a plan meet on one level.

A wall's or separator's `start` and `end` junctions MUST be on the wall's or separator's own level. {#FS-CORE-3.3.1 MUST}

A level named by a wall's `base.level` or `top.level` MUST be in the same building as the wall's own level. {#FS-CORE-3.3.2 MUST}

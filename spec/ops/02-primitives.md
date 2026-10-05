# 2. Primitive operations

Primitives are the whole vocabulary of change: every composite (chapter 4), every editor gesture
and every agent request is, in the end, a sequence of these seven operations and their three
shorthands. Each changes the working copy in exactly one way, and each fails — failing the batch —
when it cannot.

## 2.1 addElement

```json
{ "op": "addElement", "collection": "rooms", "id": "R7", "element": { "level": "L1", "anchor": [390144, 390144], "name": "Den" } }
```

Adds `element` to `collection` under `id`, or under a minted ID when `id` is absent (1.5).
`collection` is one of the collections of Core §1.1 — the eleven of Core 0.2, and `"stairs"`,
which Core 0.3 adds — or `"items"`: the program's items
(Core §11.1). With an `extension` member — an extension name — `collection` is instead the name of
one of that extension's collections, and the element is an extension element (Core §12.5):

```json
{ "op": "addElement", "collection": "items", "id": "KIT", "element": { "function": "kitchen", "minArea": 18022400000000 } }
{ "op": "addElement", "extension": "FS_electrical", "collection": "devices", "element": { "fallback": { … }, "host": { … } } }
```

The element is added exactly as given; whether it is a valid element is decided when the batch is
validated, after normalization.

`addElement` MUST fail with `FS-OPS-005` when its `id` is already used (1.5.2), and MUST NOT otherwise check the element's content. {#FS-OPS-2.1.1 MUST}

An `addElement` into `items` MUST add the element to the program's `items`, and one with `extension` to the collection `collection` in that extension's top-level `collections`, creating `program` and its `items`, or `extensions`, the extension's data, its `collections` and the collection, as empty objects where they are missing; it MUST fail with `FS-OPS-003` when one of them is present and is not an object. {#FS-OPS-2.1.3 MUST}
So adding the first device of an extension creates its data — but not its declaration: a document
that does not declare the extension in `extensionsUsed` is invalid (Core §1.6.3), and the batch
that adds it declares it with `setProperty` of `$document` `/extensionsUsed/<name>`, at the
version it targets. Added to a working copy that declares `"0.1"`, an item or an extension element
is not an element (0.3); the result is judged as that draft says.

**Shorthands.** These are `addElement` with the collection fixed and the element's members written
inline; they exist because they are the commonest edits and read naturally:

| Shorthand | Is |
|---|---|
| `{ "op": "addJunction", "id"?, "level", "position", "join"?, "name"?, "extensions"?, "extras"? }` | `addElement` into `junctions` |
| `{ "op": "addWall", "id"?, "level", "start", "end", "type"?, "layers"?, "justification"?, "base"?, "top"?, "name"?, "extensions"?, "extras"? }` | `addElement` into `walls` |
| `{ "op": "addSeparator", "id"?, "level", "start", "end", "name"?, "extensions"?, "extras"? }` | `addElement` into `separators` |

Every operation that creates an element may carry the members every element may (`name`,
`extensions`, `extras`, Core §1.4), and passes them into the element as given.

A shorthand's references — `level`, `start`, `end` and `position` — are resolved first (2.5); the shorthand is then exactly the `addElement` of the resolved values, and an applier MUST treat it so. {#FS-OPS-2.1.2 MUST}
So a shorthand whose `start` names no junction is rejected with `FS-OPS-003` when it is resolved,
where an `addElement` with the same content is added and rejected at validation (`FS-INV-002`).

## 2.2 removeElement

```json
{ "op": "removeElement", "id": "W12", "cascade": true }
```

Removes the element `id`. Removing an element that other elements depend on would leave them
pointing at nothing, so `removeElement` follows this table:

| Removing | Takes with it, when `cascade` is `true` | Blocks, otherwise |
|---|---|---|
| a building | its levels (and what they take) | its levels |
| a level | its junctions, walls, separators, rooms and slabs, every wall's openings, every extension element whose `fallback.level` or `host.level` it is, and every stair whose `level` or `to` it is (and what they all take) | anything on it — those, and any wall whose `base.level` or `top.level` it is |
| a junction | the walls and separators that end at it (and what they take) | those walls and separators |
| a wall | its openings, and the extension elements whose `host.wall` it is; and it is removed from any junction's `join.through`, which unsets that `join` | its openings and those extension elements |
| a room | the extension elements whose `host.room` it is | those extension elements |
| a separator, opening, slab, stair or extension element | nothing | nothing |
| a program item | nothing — `cascade` does not apply; every adjacency that names it is removed | every room whose `brief` names it |
| a type, material or asset | nothing — `cascade` does not apply | every element that refers to it, including an extension element whose `fallback.asset` or `fallback.symbol` it is |

`cascade` defaults to `false`. A wall is always removed from `join.through` lists, because a join
that names a missing wall describes nothing. For the same reason an adjacency that names a
removed program item goes with it, and a program item's `level` — a preference, not a place —
is removed with the level it names. A room's `brief` is different: it says what the room is for,
so removing the item it names is blocked until the room is given another or none.

`removeElement` MUST fail with `FS-OPS-003` when `id` does not exist, and with `FS-OPS-006` when the table says the removal is blocked. {#FS-OPS-2.2.1 MUST}

When `cascade` is `true`, `removeElement` MUST remove exactly the elements the table lists, transitively, and nothing else. {#FS-OPS-2.2.2 MUST}

Whether `cascade` is `true` or not, removing a program item MUST also remove every adjacency whose `a` or `b` names it, and removing a level MUST also remove the `level` member of every program item that names it. {#FS-OPS-2.2.3 MUST}

## 2.3 setProperty and unsetProperty

```json
{ "op": "setProperty", "id": "W12", "path": "/justification", "value": "exteriorFace" }
{ "op": "unsetProperty", "id": "O3", "path": "/sill" }
```

`setProperty` sets the member at `path` — a JSON Pointer (RFC 6901), relative to the element — to
`value`, creating the member, and any missing objects on the way to it, if needed; an array element
is addressed by its index. `unsetProperty` removes the member, so that its default applies again.
`id` is an element reference (a program item and an extension element are elements, 0.3), or one
of three reserved targets: `$project`, `$site` and `$document`. `$document` addresses the
document's top-level members other than its collections: `floorspec`, `project`, `site`,
`program`, `extensionsUsed`, `extensionsRequired`, `extensions` and `extras` — so `unsetProperty`
of `$document` `/site` removes the site. Setting a member of `$site` creates the site if the
project has none. A path is relative to the element as it is stored: `setProperty` of `KIT`
`/minArea` sets a program item's minimum area, and of `X4` `/host/height` an outlet's height.

`setProperty` and `unsetProperty` MUST fail with `FS-OPS-003` when `id` does not exist, when `path` is empty or is not a JSON Pointer, when it leads through a value that is neither an object nor an array or to an array index that does not exist, or when it names a member of `$document` that the list above does not, and `unsetProperty` MUST also fail with `FS-OPS-003` when the member does not exist. {#FS-OPS-2.3.1 MUST}

A `path` cannot change an element's ID or move it between collections: there is no member for
either. Changing an ID is not an edit Floorspec has.

## 2.4 moveJunction

```json
{ "op": "moveJunction", "id": "J4", "to": [780288, 0] }
```

Sets the junction's `position` to `to`. It is `setProperty` of `/position`, named, because moving a
junction is what moving walls, resizing rooms and dragging corners all come down to.

An applier MUST treat `moveJunction` exactly as `setProperty` of the junction's `/position`. {#FS-OPS-2.4.1 MUST}

## 2.5 Values in primitives

Primitives carry resolved values: lengths are integers and points are `[x, y]` — except that a
primitive in a batch may use the reference grammar of chapter 3 in a member its definition types
as a length, point or element reference (`removeElement`'s `id`, `moveJunction`'s `to`, a
shorthand's `level`, `start`, `end` and `position`, an adjacency primitive's `a` and `b`), and is
resolved first like any composite; never inside `element` or `value`, which are taken as given.
The `resolved` echo (1.4) always contains the integers and IDs.

## 2.6 setAdjacency and removeAdjacency

```json
{ "op": "setAdjacency", "a": "Kitchen", "b": "Dining", "kind": "required", "weight": 8 }
{ "op": "removeAdjacency", "a": "KIT", "b": "GAR", "kind": "forbidden" }
```

An adjacency (Core §11.2) has no ID, and its place in the `adjacency` array is not stable, so an
operation addresses it by what makes it unique in a valid document (Core §11.2.2): its **pair**
and its `kind`. `a` and `b` are program item references (3.3), resolved in that order; the pair is
unordered, so `a` and `b` may be given either way round. `kind` is `"required"`, `"preferred"` or
`"forbidden"`.

- `setAdjacency` writes the adjacency `{ "a", "b", "kind" }`, with `weight` when it is given
  (taken as given, like a `value`). When the program already has an adjacency with that pair and
  `kind`, the first such is replaced where it stands; otherwise the adjacency is appended,
  creating `program` and its `adjacency` where they are missing. It is how an adjacency is added
  and how its weight is changed.
- `removeAdjacency` removes every adjacency with that pair and `kind`.

Neither checks the adjacency it writes or leaves: an item related to itself, or a pair both
required and forbidden, makes the result invalid (Core §11.2), and validation judges it.

An applier MUST apply setAdjacency and removeAdjacency exactly as this section defines, and MUST reject with `FS-OPS-003` a removeAdjacency that matches no adjacency, and either of them when `program` is present and is not an object or its `adjacency` is present and is not an array. {#FS-OPS-2.6.1 MUST}

## 2.7 Hosted elements follow their hosts

An extension element with a `host` is placed relative to it (Core §13.3): a wall-face host by a
distance along its wall's location line from the wall's start junction and a height above its
base, a floor, ceiling or free host by a plan point on its level. Its derived placement follows
the host because the document holds nothing absolute to update. So an edit that moves a wall —
`moveWall`, `moveJunction`, `resizeRoom`, dragging a corner — moves every outlet on its faces with
it and changes no byte of the outlets. An element keeps its distance from its wall's start
junction, exactly as an opening does: one on a wall whose end moves along the wall stays where it
is, and one on a wall whose start moves along the wall moves with the start. Changing a wall's thickness or justification moves
its faces, and the elements on them, the same way.

An applier MUST NOT change an extension element's `host` or `fallback` except where a definition says so: a `setProperty` or `unsetProperty` whose path leads into it, `moveElement` (4.10), `moveRoom` (4.3), `removeWall` (4.7) and planarization (5.2). {#FS-OPS-2.7.1 MUST NOT}
A floor, ceiling or free host's position is a plan point, so it does not follow walls: the toilet stays
where it stands when a bathroom wall moves, and a room resized past it leaves it outside, which
validation reports (Core §13.3.4). Moving the room itself (4.3) takes it along.

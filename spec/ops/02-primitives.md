# 2. Primitive operations

Primitives are the whole vocabulary of change: every composite (chapter 4), every editor gesture
and every agent request is, in the end, a sequence of these five operations and their three
shorthands. Each changes the working copy in exactly one way, and each fails — failing the batch —
when it cannot.

## 2.1 addElement

```json
{ "op": "addElement", "collection": "rooms", "id": "R7", "element": { "level": "L1", "anchor": [390144, 390144], "name": "Den" } }
```

Adds `element` to `collection` under `id`, or under a minted ID when `id` is absent (1.5).
`collection` is one of the eleven collections of Core §1.1. The element is added exactly as
given; whether it is a valid element is decided when the batch is validated, after normalization.

`addElement` MUST fail with `FS-OPS-005` when its `id` is already used (1.5.2), and MUST NOT otherwise check the element's content. {#FS-OPS-2.1.1 MUST}

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
| a level | its junctions, walls, separators, rooms and slabs, and every wall's openings | anything on it, or any wall whose `base.level` or `top.level` it is |
| a junction | the walls and separators that end at it, and their openings | those walls and separators |
| a wall | its openings; and it is removed from any junction's `join.through`, which unsets that `join` | its openings |
| a separator, room, opening or slab | nothing | nothing |
| a type, material or asset | nothing — `cascade` does not apply | every element that refers to it |

`cascade` defaults to `false`. A wall is always removed from `join.through` lists, because a join
that names a missing wall describes nothing.

`removeElement` MUST fail with `FS-OPS-003` when `id` does not exist, and with `FS-OPS-006` when the table says the removal is blocked. {#FS-OPS-2.2.1 MUST}

When `cascade` is `true`, `removeElement` MUST remove exactly the elements the table lists, transitively, and nothing else. {#FS-OPS-2.2.2 MUST}

## 2.3 setProperty and unsetProperty

```json
{ "op": "setProperty", "id": "W12", "path": "/justification", "value": "exteriorFace" }
{ "op": "unsetProperty", "id": "O3", "path": "/sill" }
```

`setProperty` sets the member at `path` — a JSON Pointer (RFC 6901), relative to the element — to
`value`, creating the member, and any missing objects on the way to it, if needed; an array element
is addressed by its index. `unsetProperty` removes the member, so that its default applies again.
`id` is an element reference, or one of three reserved targets: `$project`, `$site` and
`$document`. `$document` addresses the document's top-level members other than its collections:
`floorspec`, `project`, `site`, `extensionsUsed`, `extensionsRequired`, `extensions` and `extras` —
so `unsetProperty` of `$document` `/site` removes the site. Setting a member of `$site` creates the
site if the project has none.

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
shorthand's `level`, `start`, `end` and `position`), and is resolved first like any composite;
never inside `element` or `value`, which are taken as given. The `resolved` echo (1.4) always
contains the integers.

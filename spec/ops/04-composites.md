# 4. Composite operations

A composite is a named edit that people and agents actually ask for — "draw a wall from here to
there", "make the kitchen two feet wider", "put a door in the middle of that wall". Each is
defined here as the exact sequence of primitives it expands to, so that every applier makes the
same edit. A composite's references are resolved against the working copy before it (1.2); its
primitives then apply in the order given, and normalization follows the whole batch.

## 4.1 drawWall and drawSeparator

```json
{ "op": "drawWall", "level": "L1", "from": [0, 0], "to": "12' east of J4", "type": "T2" }
```

Members: `level`; `from` and `to`, each a point or a junction; optionally `id`, any wall member
(`type`, `layers`, `justification`, `base`, `top`) and the members every element may carry
(`name`, `extensions`, `extras`). Expands to:

1. for `from`, then `to`: if it is a junction, use it; if it is a point and a junction on `level`
   already has that position, use that junction; otherwise `addJunction` at the point (minted ID);
2. `addWall` from the first junction to the second, with the given members.

`drawSeparator` is the same with `addSeparator` and no wall members (`name`, `extensions` and
`extras` are allowed). A wall drawn across other
walls is split where it crosses them by normalization (5.2); drawing does not need to know. An arc wall
or separator (Core §21) is drawn under an `id` the batch names, and given its `arc` by `setProperty` in
the same batch; it is never split (5.2).

An applier MUST expand drawWall and drawSeparator as this section defines. {#FS-OPS-4.1.1 MUST}

## 4.2 moveWall

```json
{ "op": "moveWall", "wall": "east wall of Kitchen", "by": "2'", "toward": "Dining" }
```

Moves a wall sideways, keeping its direction. `wall` is a wall (3.3) — never a separator, which
counts as no match there. `by` is a length; positive is towards the wall's
left (exterior) side. With `toward: <room>`, the sign of `by` is instead chosen so the wall moves
into that room's face. The displacement is `by` times the wall's unit left normal, rounded once
per coordinate, ties to even — for an arc wall (Core §21), the unit left normal of its chord, from its
start junction to its end junction, so an arc wall moves with its sagitta unchanged; then:

1. `moveJunction` of the wall's start by the displacement;
2. `moveJunction` of its end by the same displacement.

The walls meeting it at those junctions stretch or shrink to follow.

An applier MUST expand moveWall as this section defines, and MUST reject it with `FS-OPS-008`, naming the wall, when `toward` names a room whose face is not on exactly one side of the wall. {#FS-OPS-4.2.1 MUST}
A room whose face is on neither side — one elsewhere on the level, or on another level, whose
faces are not the faces of this wall's level — is not beside the wall, and gets `FS-OPS-008` too.

## 4.3 moveRoom

```json
{ "op": "moveRoom", "room": "Bath", "by": "1' 6\" west" }
```

Moves every junction on the room's outer cycle, its anchor, its vaulted ceiling's ridge, and what
stands on its floor or hangs from its ceiling, by the vector `by`:

1. `moveJunction` of each junction on the room's outer cycle, by ID;
2. `setProperty` of the room's `/anchor`;
3. when the room's ceiling is vaulted (Core §15.3) and its `ridge` is two integer points,
   `setProperty` of the room's `/ceiling/ridge` to both points plus `by`;
4. `setProperty` of `/host/position` of every extension element whose `host` is a `surface` host
   on the room with an integer point `position` — its position plus `by` — by ID.

Walls that connect the room to the rest of the plan stretch; neighbouring rooms change shape. The
openings in the room's walls, and the extension elements on their faces, follow the walls (2.7);
the room's floor and ceiling are its room polygon, so they follow too (Core §15); a vault's ridge
is a plan point, as a host's position is, and moves with step 3; the bath and the vanity on the
floor move with step 4.

An applier MUST expand moveRoom as this section defines. {#FS-OPS-4.3.1 MUST}

An applier MUST move a vaulted ceiling's ridge with its room, as step 3 defines, and MUST NOT change any other member of the room's `ceiling` or `floor`. {#FS-OPS-4.3.2 MUST}
Only `moveRoom` moves a ridge: an edit that moves one wall, or resizes the room, reshapes its
floor and ceiling — they are its room polygon — and leaves the ridge where it is.

## 4.4 resizeRoom

```json
{ "op": "resizeRoom", "room": "Kitchen", "side": "east", "by": "2'" }
```

Moves one side of a room outwards by `by` (inwards when negative), the edit behind "make the
kitchen two feet wider". Let `u` be the unit vector of `side` — east `(1, 0)`, north `(0, 1)`,
west `(−1, 0)`, south `(0, −1)` — and `v = by · u`, an integer vector.

**The side.** The **side edges** are the edges on the room's outer cycle whose outward normal is
exactly `u`. They must exist, lie on one line, and be consecutive along the cycle; they form a
**run** of junctions `P₀ … Pₖ` in the order the cycle is walked. A room whose side is missing,
oblique or jogged gets `FS-OPS-008`: resize it wall by wall.

**The ends.** At each end junction `P₀` and `Pₖ`, the side may **continue**: another edge leaves the
end junction along the same line, away from the run (the room's north wall continuing as the
next room's). Then:

- if the end **does not continue**, it moves by `v`, and the walls meeting it stretch;
- if the end **continues**, it stays where it is for the neighbour's sake, and the run is
  reconnected to a new junction at the end's position plus `v`, joined to the old end by a short
  new edge — a jog — of the same kind (wall or separator) and, for a wall, the same `type`,
  `layers` and `justification` as the run edge it adjoins;
- except that when an edge already leaves a continuing end exactly in the direction of `v` — the
  room's own perpendicular wall, when the side moves inwards at a T — no jog edge is added: the new
  junction lies on that edge, normalization splits the edge there (5.2), and its piece between the
  end and the new junction is the jog. That edge must be longer than `|v|`.

**The anchors.** The room's anchor moves by `v / 2`, and so does the anchor of every room on the
other side of a side edge, each coordinate rounded once, ties to even — so both rooms keep their
anchors inside as their shared wall moves.

The expansion, in order:

1. for each continuing end, by run position (`P₀` first): `addJunction` at its position plus `v`
   on the room's level (minted ID), then `setProperty` of the adjoining run edge's `/start` or
   `/end` to the new junction, then — unless an edge leaves the end in the direction of `v` —
   `addWall` or `addSeparator` from the old end to the new junction (minted ID) with the members
   above;
2. `moveJunction` by `v` of every run junction that is not a continuing end, by ID;
3. `setProperty` of `/anchor` for the room, then for each room across a side edge, by ID.

An applier MUST expand resizeRoom as this section defines, and MUST reject it with `FS-OPS-008` when the side is missing, oblique or jogged, or when the edge that leaves a continuing end in the direction of `v` is not longer than `|v|`. {#FS-OPS-4.4.1 MUST}

## 4.5 addOpening and moveOpening

```json
{ "op": "addOpening", "wall": "wall between Kitchen and Dining", "at": "centered", "fill": "T-door-36" }
```

Members: `wall`; `at`, a position (3.5); optionally `id`, `fill`, `width`, `height`, `sill`,
`hinge`, `swing`, `name`, `extensions`, `extras`. The width used to resolve `at` is the opening's
effective width (Core §7.2): its own `width`, or its fill's. Expands to `addElement` into
`openings` with `wall`, the resolved `offset`, the resolved `width`, `height` and `sill`, and the
other members as given.

`moveOpening` takes `opening` and exactly one of `at` and `by`, and expands to `setProperty` of
the opening's `/offset`:

```json
{ "op": "moveOpening", "opening": "O3", "at": "2' from end" }
{ "op": "moveOpening", "opening": "O3", "by": "1'", "toward": "east" }
```

- **Absolute.** With `at`, a position (3.5), the offset is `at` resolved; the width used to
  resolve it is the opening's effective width in the working copy.
- **Relative.** With `by`, a length, the offset is the opening's `offset` in the working copy plus
  `by`: a positive `by` moves the opening toward its wall's end junction, a negative one toward its
  start. `toward`, allowed only with `by`, chooses the sign instead, and the opening moves by
  `|by|`:
  - `"end"`: by `+|by|`; `"start"`: by `−|by|`;
  - `"north"`, `"south"`, `"east"` or `"west"`: in whichever direction along the wall points more
    that way. Let `d = E − S`, where `S` and `E` are the positions of the wall's start and end
    junctions, and `u` the direction's unit vector — east `(1, 0)`, north `(0, 1)`, west
    `(−1, 0)`, south `(0, −1)`. The opening moves by `+|by|` when `d · u > 0` and by `−|by|` when
    `d · u < 0`. When `d · u = 0` the wall is perpendicular to that direction, and the opening
    cannot move along it toward it: `FS-OPS-008`, naming the wall.

The references are resolved in the order `opening`, then `at` — after the width — or `by` and
then `toward`. The new offset is not checked here: an opening moved past its wall's end, or before
its start, makes the result invalid, and the batch is rejected with the Core diagnostics of the
result (1.2.3): `FS-INV-302` past the end (Core §7.3), `FS-SCH-001` for a negative offset (Core §7.1).

An applier MUST expand addOpening and moveOpening with `at` as this section defines, and MUST reject an addOpening, or a moveOpening with `at`, whose width resolves from neither member nor fill with `FS-OPS-003`. {#FS-OPS-4.5.3 MUST}

An applier MUST expand a moveOpening with `by` as this section defines, MUST reject it with `FS-OPS-003`, naming the opening, when the opening has no integer `offset` in the working copy, and MUST reject it with `FS-OPS-008`, naming the wall, when `toward` is a direction perpendicular to the opening's wall. {#FS-OPS-4.5.2 MUST}

## 4.6 addRoom, setRoomFinish, setRoomBrief

`addRoom` takes `level`, `at` (a point) and optionally `id`, `name`, `function`, the three
finishes, `brief` (a program item, 3.3), `extensions` and `extras`, and expands to `addElement`
into `rooms` with `anchor` set to `at`, `brief` set to the item's ID, and the other members as
given; the references are resolved in the order `level`, `at`, `brief`. Drawing walls makes
faces; `addRoom` names one.

`setRoomFinish` takes `room`, `surface` (`"wall"`, `"floor"` or `"ceiling"`) and `material`, and
expands to `setProperty` of `/wallFinish`, `/floorFinish` or `/ceilingFinish`.

An applier MUST expand addRoom and setRoomFinish as this section defines. {#FS-OPS-4.6.1 MUST}

```json
{ "op": "setRoomBrief", "room": "Den", "item": "Study" }
```

`setRoomBrief` takes `room` and `item`, a program item (3.3) — here, a plain string is an item's
ID or name — resolved in that order, and expands to `setProperty` of the room's `/brief` to the
item's ID: the room is now the one that fulfils that item (Core §11.3). A room that should fulfil
none has its `brief` removed with `unsetProperty`.

An applier MUST expand setRoomBrief as this section defines. {#FS-OPS-4.6.2 MUST}

## 4.7 removeWall

```json
{ "op": "removeWall", "wall": "wall between Kitchen and Dining", "keep": "Kitchen" }
```

Removes a wall and the openings in it, and the extension elements on its faces. If the wall has a
different room's face on each side, the two rooms are about to become one, and `keep` must name
the one that survives:

1. when there are two rooms, `setProperty` of `/host/room` to the room kept, for every extension
   element whose `host` is a `surface` host on the room not kept, by ID — what stood in the
   dining room now stands in the kitchen that absorbed it;
2. `removeElement` of the room not kept, when there are two;
3. `removeElement` of the wall, with `cascade: true`.

An applier MUST expand removeWall as this section defines, and MUST reject it with `FS-OPS-008` when the wall has rooms on both sides and `keep` does not name one of them. {#FS-OPS-4.7.1 MUST}

## 4.8 addLevel

```json
{ "op": "addLevel", "building": "B1", "above": "L1", "height": "8' 6\"", "name": "Second floor" }
{ "op": "addLevel", "building": "B1", "below": "L1", "height": "8'", "name": "Basement" }
```

Members: `building`; `height`, a length; exactly one of `elevation`, a length, `above`, a level,
and `below`, a level; optionally `id`, `name`, `extensions` and `extras`. The references are
resolved in that order — `building`, `height`, then `elevation`, `above` or `below` — and the
new level's elevation is:

- with `elevation`: that length;
- with `above: <level>`: that level's `elevation` plus its `height` in the working copy — the new
  level sits on top of it;
- with `below: <level>`: that level's `elevation` in the working copy minus the new level's
  `height` — the new level's top is the other's floor.

A level named by `above` or `below` must have an integer `elevation` and an integer `height` in
the working copy; one that does not resolves to nothing (`FS-OPS-003`, naming that level). The
operation expands to `addElement` into `levels`, under `id` or a minted ID (1.5), of
`{ "building", "elevation", "height" }` as the ID and the integers resolved, and `name`,
`extensions` and `extras` as given. Whether the level is valid — its height greater than zero
(Core §1.8) — is decided when the batch is validated.

An applier MUST expand addLevel as this section defines, and MUST reject it with `FS-OPS-003` when `building` names no building, when `above` or `below` names no level, or when the level it names lacks an integer `elevation` or an integer `height`. {#FS-OPS-4.8.1 MUST}

## 4.9 addProgramItem

```json
{ "op": "addProgramItem", "id": "BED", "function": "sleeping", "name": "Bedroom", "count": 3, "minArea": "11 m2", "level": "L2" }
```

Members: `function`; optionally `id`, `name`, `count`, `targetArea` and `minArea` (areas, 3.6),
`level` (a level), `extensions` and `extras`. The references are resolved in the order
`targetArea`, `minArea`, `level`. Expands to `addElement` into `items` (2.1), under `id` or a
minted ID (1.5), of the item: `function` and `count` as given, the areas as integers, `level` as
the level's ID, and `name`, `extensions` and `extras` as given. Whether the item is valid — its
function a room function, its count at least one (Core §11.1) — is decided when the batch is
validated.

A brief is drawn as a bubble diagram with this and three other operations: `addProgramItem` for
each bubble, `setAdjacency` (2.6) for each line between two, `addRoom` with `brief` or
`setRoomBrief` (4.6) when a room is drawn for one — and `setProperty` of an item to change it.

An applier MUST expand addProgramItem as this section defines. {#FS-OPS-4.9.1 MUST}

## 4.10 placeElement and moveElement

```json
{ "op": "placeElement", "extension": "FS_electrical", "collection": "devices",
  "host": { "mode": "wallFace", "wall": "north wall of Kitchen", "toward": "Kitchen", "at": "2' from start", "height": "12\"" },
  "element": { "fallback": { "box": { "min": [0, -45720, 0], "max": [25400, 45720, 114300] } }, "device": "receptacle" } }
{ "op": "moveElement", "element": "X4", "host": { "mode": "surface", "room": "Bath", "surface": "floor", "at": "3' east of J2" } }
```

`placeElement` adds an extension element placed on a host; `moveElement` places an existing one
on a host — another wall, the other face, another room or level, or the same host at a new
position. Both take a **host reference**: a host (Core §13.3) written with the reference grammar,
in one of three modes:

| `mode` | Members | Resolves to |
|---|---|---|
| `"wallFace"` | `wall` (a wall); exactly one of `side` (`"left"` or `"right"`) and `toward` (a room); `at` (a position along the wall, 3.5); `height` (a length) | `{ "mode": "wallFace", "wall", "side", "offset", "height" }` |
| `"surface"` | `room` (a room); `surface` (`"floor"` or `"ceiling"`); `at` (a point); optionally `rotation` | `{ "mode": "surface", "room", "surface", "position", "rotation"? }` |
| `"free"` | `level` (a level); `at` (a point); optionally `rotation` | `{ "mode": "free", "level", "position", "rotation"? }` |

A wall-face host's `toward` chooses the face that looks into that room: `"left"` when the room's
face is the face on the wall's left and not on its right, `"right"` the other way round — as
`moveWall`'s `toward` chooses a direction (4.2). Its `at` is resolved with `w = 0`, because a
hosted element is placed by a point: `"centered"` is the middle of the wall, `"2' from end"` two
feet before its end. `rotation` is an angle in microdegrees (Core §2.4), taken as given. The
host's **level** is its wall's or its room's `level` in the working copy, or a free host's
`level`. The members are resolved in the order the table lists them.

`placeElement` takes `extension` (an extension name), `collection` (one of its collection names),
`host`, `element` (an object) and optionally `id`. It expands to `addElement` with that
`extension` and `collection`, under `id` or a minted ID (1.5), of `element` with `host` set to the
resolved host and `fallback.level` set to the host's level — creating `fallback` as `{ "level" }`
when the element has none, and leaving a `fallback` that is not an object as it is, for validation
to reject. Everything else in `element` is taken as given: the box, the
extension's own members, `name`, `clearances`, `extras`.

`moveElement` takes `element` (an extension element, 3.3) and `host`, resolved in that order, and
expands to `setProperty` of the element's `/host` to the resolved host, then of its
`/fallback/level` to the host's level.

An applier MUST expand placeElement and moveElement as this section defines, MUST reject either with `FS-OPS-008`, naming the wall, when a wall-face host's `toward` names a room whose face is not on exactly one side of the wall, and MUST reject either with `FS-OPS-003`, naming the wall or the room, when the host's wall or room has no `level` in the working copy. {#FS-OPS-4.10.1 MUST}
As for `moveWall` (4.2), a room on another level than the wall's is not beside it.

Whether the element is valid — its host's offset on the wall (Core §13.3.2), its height below the
wall's top (13.3.3), its position inside the room (13.3.4), the extension declared (Core §1.6.3)
— is decided when the batch is validated.

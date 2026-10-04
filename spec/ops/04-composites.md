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

Members: `level`; `from` and `to`, each a point or a junction; optionally `id` and any wall member
(`type`, `layers`, `justification`, `base`, `top`, `name`). Expands to:

1. for `from`, then `to`: if it is a junction, use it; if it is a point and a junction on `level`
   already has that position, use that junction; otherwise `addJunction` at the point (minted ID);
2. `addWall` from the first junction to the second, with the given members.

`drawSeparator` is the same with `addSeparator` and no wall members. A wall drawn across other
walls is split where it crosses them by normalization (5.2); drawing does not need to know.

An applier MUST expand drawWall and drawSeparator as this section defines. {#FS-OPS-4.1.1 MUST}

## 4.2 moveWall

```json
{ "op": "moveWall", "wall": "east wall of Kitchen", "by": "2'", "toward": "Dining" }
```

Moves a wall sideways, keeping its direction. `by` is a length; positive is towards the wall's
left (exterior) side. With `toward: <room>`, the sign of `by` is instead chosen so the wall moves
into that room's face. The displacement is `by` times the wall's unit left normal, rounded once
per coordinate, ties to even; then:

1. `moveJunction` of the wall's start by the displacement;
2. `moveJunction` of its end by the same displacement.

The walls meeting it at those junctions stretch or shrink to follow.

An applier MUST expand moveWall as this section defines. {#FS-OPS-4.2.1 MUST}

## 4.3 moveRoom

```json
{ "op": "moveRoom", "room": "Bath", "by": "1' 6\" west" }
```

Moves every junction on the room's outer cycle, and its anchor, by the vector `by`:

1. `moveJunction` of each junction on the room's outer cycle, by ID;
2. `setProperty` of the room's `/anchor`.

Walls that connect the room to the rest of the plan stretch; neighbouring rooms change shape.

An applier MUST expand moveRoom as this section defines. {#FS-OPS-4.3.1 MUST}

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
  `layers` and `justification` as the run edge it adjoins.

**The anchors.** The room's anchor moves by `v / 2`, and so does the anchor of every room on the
other side of a side edge, each coordinate rounded once, ties to even — so both rooms keep their
anchors inside as their shared wall moves.

The expansion, in order:

1. for each continuing end, by run position (`P₀` first): `addJunction` at its position plus `v`
   on the room's level (minted ID), then `setProperty` of the adjoining run edge's `/start` or
   `/end` to the new junction, then `addWall` or `addSeparator` from the old end to the new
   junction (minted ID) with the members above;
2. `moveJunction` by `v` of every run junction that is not a continuing end, by ID;
3. `setProperty` of `/anchor` for the room, then for each room across a side edge, by ID.

An applier MUST expand resizeRoom as this section defines, and MUST reject it with `FS-OPS-008` when the side is missing, oblique or jogged. {#FS-OPS-4.4.1 MUST}

## 4.5 addOpening and moveOpening

```json
{ "op": "addOpening", "wall": "wall between Kitchen and Dining", "at": "centered", "fill": "T-door-36" }
```

Members: `wall`; `at`, a position (3.5); optionally `id`, `fill`, `width`, `height`, `sill`,
`hinge`, `swing`, `name`. The width used to resolve `at` is the opening's effective width (Core
§7.2): its own `width`, or its fill's. Expands to `addElement` into `openings` with `wall`, the
resolved `offset`, and the other members as given.

`moveOpening` takes `opening` and `at`, and expands to `setProperty` of its `/offset`.

An applier MUST expand addOpening and moveOpening as this section defines, and MUST reject an addOpening whose width resolves from neither member nor fill with `FS-OPS-003`. {#FS-OPS-4.5.1 MUST}

## 4.6 addRoom, setRoomFinish

`addRoom` takes `level`, `at` (a point) and optionally `id`, `name`, `function` and the three
finishes, and expands to `addElement` into `rooms` with `anchor` set to `at`. Drawing walls makes
faces; `addRoom` names one.

`setRoomFinish` takes `room`, `surface` (`"wall"`, `"floor"` or `"ceiling"`) and `material`, and
expands to `setProperty` of `/wallFinish`, `/floorFinish` or `/ceilingFinish`.

An applier MUST expand addRoom and setRoomFinish as this section defines. {#FS-OPS-4.6.1 MUST}

## 4.7 removeWall

```json
{ "op": "removeWall", "wall": "wall between Kitchen and Dining", "keep": "Kitchen" }
```

Removes a wall and the openings in it. If the wall has a different room's face on each side, the
two rooms are about to become one, and `keep` must name the one that survives:

1. `removeElement` of the room not kept, when there are two;
2. `removeElement` of the wall, with `cascade: true`.

An applier MUST expand removeWall as this section defines, and MUST reject it with `FS-OPS-008` when the wall has rooms on both sides and `keep` does not name one of them. {#FS-OPS-4.7.1 MUST}

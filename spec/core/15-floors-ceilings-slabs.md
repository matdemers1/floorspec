# 15. Floors, ceilings and slabs

A room has a floor and a ceiling, and neither is drawn. The floor is the room polygon (6.2) laid at
the level's elevation; the ceiling is the same polygon held up at the level's ceiling height. What
a document stores is only what differs from that: a floor sunk below or raised above its level, a
floor's thickness, a ceiling's own height, and a ceiling that is not flat — a **tray**, with a
raised centre, or a **vault**, sloping up to a ridge. Move a wall and the room's floor and ceiling
follow it, because they are its room polygon (FLR-ADR-002). Areas that are not rooms — a patio, a
porch deck, a landing — are **slabs** (6.7): authored outlines with a thickness.

This chapter defines the members a room and a level add for floors and ceilings, the exact
geometry a deriver derives from them, where an element hosted on a floor or a ceiling sits, and the
bounding geometry of every slab. Every value is exact and rounded once (2.2).

## 15.1 Floors

A room's `floor` member (6.5) is an object:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `offset` | length | `0` | the height of the floor's top above its level's elevation: negative for a sunken floor, positive for a raised one |
| `thickness` | length | its level's `floorThickness` (1.8); absent there too: not declared | the floor's thickness, from its top down |

A room's `floor` MUST have only the members of this table, each of the type the table gives, and its `thickness` MUST be greater than zero. {#FS-CORE-15.1.1 MUST}

The room's **floor** is its room polygon (6.2) at these elevations, where `E` is the elevation of
the room's level:

- its **top** is `E + offset`;
- its **bottom** is its top minus its thickness — the room's own `thickness`, otherwise its level's
  `floorThickness`, otherwise `0`, which says that no thickness is declared and the floor is a
  surface;
- its **box** is `{ "min": [x₀, y₀, bottom], "max": [x₁, y₁, top] }`, where `x₀`, `x₁`, `y₀` and
  `y₁` are the least and greatest coordinates of the vertices of the room polygon's outer ring, as
  6.2 rounds them.

Every one of these is an integer: the floor needs no rounding. A floor's thickness is the
structure and finish under the room's floor; this draft does not divide it into layers.

A deriver MUST derive the floor of every room — its top, bottom and box — as this section defines them. {#FS-CORE-15.1.2 MUST}

## 15.2 Ceilings

A room's `ceiling` member (6.5) is one of three forms. Its default is `{ "kind": "flat" }`.

| `ceiling` | The ceiling |
|---|---|
| `{ "kind": "flat", "height"?: length }` | flat, at `height` |
| `{ "kind": "tray", "height"?: length, "border": length, "depth": length }` | flat at `height` for a border `border` wide inside the room's walls, and raised by `depth` over the centre the border surrounds (15.4) |
| `{ "kind": "vaulted", "height"?: length, "ridge": [point, point], "pitch": pitch, "slopes"?: "both", "left" or "right" }` | rising to a ridge at `height`, along the line through the two points of `ridge`, and falling away from it at `pitch` (15.3) |

`height` is measured from the level's elevation, not from the room's floor: a sunken floor does not
lower its room's ceiling. Its default is derived: the level's `ceilingHeight` (1.8), and on a level
without one, the level's `height`. `slopes` defaults to `"both"`. A pitch is `{ "rise", "run" }`
(2.5): the ceiling falls `rise` for every `run` it runs away from the ridge, measured at right
angles to it.

A room's `ceiling` MUST have exactly the members of one of the three forms, each of the type its table gives: `height`, `border` and `depth` MUST be greater than zero, a `ridge` MUST be an array of exactly two points, a pitch's `rise` and `run` MUST be integers from 1 to 2⁵³ − 1, and `slopes` MUST be `"both"`, `"left"` or `"right"`. {#FS-CORE-15.2.1 MUST}

The **elevation of the ceiling** at a plan point `P` of the room is, where `E` is the elevation of
the room's level and `h` the ceiling's height:

- for a flat ceiling, `E + h` everywhere;
- for a tray ceiling, `E + h + depth` at a point of its centre and `E + h` elsewhere (15.4);
- for a vaulted ceiling, `z(P)` of 15.3.

The **low** and **high** of a room's ceiling are the least and the greatest of its elevations over
the room polygon: for a flat ceiling both `E + h`; for a tray `E + h` and `E + h + depth`; for a
vault, as 15.3 computes them.

A room's ceiling MUST be above its floor: the least exact elevation of its ceiling over its room polygon MUST be greater than the top of its floor. {#FS-CORE-15.2.2 MUST}
The test is made on the exact value, before it is rounded: a vault that comes down to the floor's
top at a corner of the room fails it.

## 15.3 Vaulted ceilings

A vaulted ceiling is defined by its **ridge line** — the line through its two `ridge` points `A`
and `B` — its height `h` above the level's elevation `E`, and its pitch `rise : run`. Let
`d = B − A = (dx, dy)` and `D = dx² + dy²`, and for a plan point `P` let

```text
c(P) = dx · (P.y − A.y) − dy · (P.x − A.x)
```

so that `c(P) / √D` is the distance from the ridge line to `P`, positive to the left of the line
walked from `A` to `B` and negative to its right. The ceiling's **fall** at `P` is:

| `slopes` | Fall `f(P)` | The ceiling |
|---|---|---|
| `"both"` | `|c(P)|` | falls to both sides of the ridge: a cathedral ceiling |
| `"left"` | `c(P)` | one plane that falls to the left of the ridge line and rises to its right |
| `"right"` | `−c(P)` | one plane that falls to the right of the ridge line and rises to its left |

and its elevation at `P` is

```text
z(P) = E + h − (rise / run) · f(P) / √D
```

of the form `p + q·√D` with rationals `p`, `q`, exact, and rounded only where a value is output.
A one-sided vault — a shed ceiling — puts its ridge along its high side; a plane rises beyond its
ridge as it falls before it, so a one-sided vault may be higher than `E + h` on the far side of
its ridge line.

A vaulted ceiling's two `ridge` points MUST NOT be the same point. {#FS-CORE-15.3.1 MUST NOT}

Over a room polygon, `z` is least and greatest at vertices of its outer ring, with one exception:

- its **low** is the least of `z(V)` over the vertices `V` of the outer ring, rounded once;
- its **high** is `E + h` when `slopes` is `"both"` and the ridge line meets the room polygon's
  outer ring or its inside — when `c(V) ≤ 0` for some vertex `V` of the outer ring and `c(V) ≥ 0`
  for some — and otherwise the greatest of `z(V)` over those vertices, rounded once.

A deriver MUST compute the elevation of a vaulted ceiling, and its low and high over its room polygon, exactly as this section defines them, rounding each value it outputs once. {#FS-CORE-15.3.2 MUST}

The ridge points are plan points, as a `surface` host's `position` is (13.3): they do not follow
the room's walls. An edit that moves a whole room moves them (Floorspec Ops); an edit that moves one
wall does not.

## 15.4 Tray ceilings

A tray ceiling's **centre** is the room polygon shrunk by its `border`: every edge of every ring
of the room polygon moved `border` to its left — into the room, because the outer ring runs
counter-clockwise and every hole clockwise in the walk order of 6.2. For a ring with vertices
`V₀ … Vₙ₋₁` in that order, as 6.2 rounds them (where the ring starts does not matter), edge `i` runs from `Vᵢ` to `Vᵢ₊₁`, with direction `dᵢ` and left normal `nᵢ = (−dᵢ.y, dᵢ.x)`, and its
**moved line** is `{ P : nᵢ · P = nᵢ · Vᵢ + border · |dᵢ| }`. The ring's moved vertex `Vᵢ'` is:

- the intersection of the moved lines of edges `i − 1` and `i`, when those edges are not parallel;
- `Vᵢ + border · nᵢ / |dᵢ|`, when they are parallel — they then run the same way, since a ring
  of a room polygon that is not degenerate never turns back on itself.

Each moved vertex has the form of a corner point (5.5), and is rounded once. The centre's rings are
the rounded moved rings, ring for ring.

A tray ceiling's border MUST fit its room: for every edge of every ring, the edge from the rounded `Vᵢ'` to the rounded `Vᵢ₊₁'` MUST run the way the edge from `Vᵢ` to `Vᵢ₊₁` runs — the dot product of the two is greater than zero — and the rounded moved rings, taken as a room polygon, MUST NOT be degenerate (6.2). {#FS-CORE-15.4.1 MUST}
A border wider than half the room, or wide enough that a short wall's edge disappears or a hole's
moved ring meets the outer one, fails this test.

A point is **of the centre** when it is inside or on the centre's outer ring and not strictly
inside any of its holes: a point on the step between the border and the centre is of the centre.

A deriver MUST derive the centre of every tray ceiling as this section defines it. {#FS-CORE-15.4.2 MUST}

## 15.5 Derived ceilings

A room's **derived ceiling** is:

- its `kind`;
- its `low` and `high` (15.2, 15.3);
- its **box**: `{ "min": [x₀, y₀, low], "max": [x₁, y₁, high] }`, with `x₀`, `x₁`, `y₀` and `y₁`
  as for its floor (15.1);
- for a tray ceiling, its **tray**: the centre (15.4), as a polygon of an outer ring and holes,
  each ring starting at its least vertex and keeping its orientation, and the holes listed in the
  order of their first vertices, as 6.2 lists a room polygon's.

A ceiling is a surface: the finish under the structure above, with no thickness of its own in this
draft. The structure of the level above, and the roof, are later chapters' (0.5).

A deriver MUST derive every room's ceiling as this section defines it. {#FS-CORE-15.5.1 MUST}

## 15.6 Hosting on floors and ceilings

A `surface` host (13.3) stands on its room's floor or hangs from its room's ceiling, so its frame's
elevation `Oz` (13.1) follows them:

- on `"floor"`: the top of the room's floor (15.1);
- on `"ceiling"`, at the host's `position` `P`: the elevation of the room's ceiling at `P` (15.2) —
  for a vaulted ceiling, `z(P)` rounded once, so that `Oz` is an integer as every other frame's is,
  and the host's box is placed from it.

A deriver MUST derive the frame of every `surface` host at the elevation this section gives it. {#FS-CORE-15.6.1 MUST}

In a room with no `floor` member and no `ceiling` member, on a level with no `ceilingHeight`, these
are the level's elevation and its elevation plus its height — exactly the elevations Core 0.2 gave
every `surface` host. A document that declares `"0.1"` or `"0.2"` cannot have those members (1.2.6),
so every placement, fallback and clearance derived for it by a reader of this draft is the one a
reader of its own draft derives.

## 15.7 Slabs

A slab (6.7) is authored, not derived: its outline is its `boundary`, and its top is `offset` above
its level's elevation. A deriver derives its bounding geometry:

- its **outline**: its `boundary`, as a ring that starts at its least vertex (6.2) and runs
  counter-clockwise — reversed, when the boundary is written clockwise;
- its **top**, its level's elevation plus its `offset`, and its **bottom**, its top minus its
  `thickness`;
- its **box**: `{ "min": [x₀, y₀, bottom], "max": [x₁, y₁, top] }`, with `x₀`, `x₁`, `y₀` and `y₁`
  the least and greatest coordinates of its outline's vertices.

A deriver MUST derive the outline, top, bottom and box of every slab as this section defines them. {#FS-CORE-15.7.1 MUST}

A slab does not take part in room derivation (6.7), and nothing is hosted on it in this draft.

## 15.8 Related

FLR-REQ-107 (a floor and a ceiling for every room, with thickness, sunken offsets and flat, vaulted
or tray ceilings), FLR-REQ-165 (free authored slabs), FLR-ADR-002 (derived, not drawn),
FLR-ADR-004 (exact integer geometry), FLR-ADR-022 (whose default — a ceiling at its level's
elevation plus its height — this chapter keeps as the default of a derived ceiling). Chapters 6
(room polygons), 13 (hosting) and Annex A (`IfcSlab`, `IfcCovering`).

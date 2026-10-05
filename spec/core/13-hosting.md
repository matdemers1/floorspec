# 13. Hosting and clearances

An outlet sits on a wall face at a height; a toilet stands on a bathroom floor; a sofa stands free
on a level, turned to face the fireplace. Each is **hosted**: placed relative to something else,
so that when the host moves, the element moves with it. Many of them also need space kept clear —
the working space in front of an electrical panel, the clearance in front of a toilet, the swing
of a door. Floorspec defines hosting and these **clearance envelopes** in core, once, so that every
extension uses the same placements and every rule tests clearances the same way, whatever kind of
element declared them (FLR-ADR-007).

## 13.1 Frames

A **frame** is an origin and three axes. Its origin is a plan point `O` (exact, not necessarily on
the grid) at an elevation `Oz`; its **facing vector** is a vector of integers `f = (fx, fy)`, not
both zero. Its axes are:

- **x**, forward: `u = f / |f|`, horizontal;
- **y**, to the left of forward: `v = (−fy, fx) / |f|`, horizontal;
- **z**, up: +Z.

The point with **local coordinates** `(p, q, r)` is the plan point `O + p·u + q·v` at elevation
`Oz + r`. A frame is right-handed and is never scaled: local coordinates are lengths.

The **facing vector of an angle** θ (microdegrees, 2.4) is

```text
F(θ) = ( round(1,000,000,000 · cos θ), round(1,000,000,000 · sin θ) )
```

with θ read as θ × 10⁻⁶ degrees, the cosine and sine exact and each rounded once. A tie never
occurs: for an angle that is a rational number of degrees, the cosine and the sine are rational
only when they are 0, ±½ or ±1 (Niven's theorem), and 10⁹ times those is an integer. So
`F(0) = (10⁹, 0)`, `F(90,000,000) = (0, 10⁹)` and `F(45,000,000) = (707106781, 707106781)`. An
angle becomes a vector of integers once, by definition, and everything after it is exact.

The **direction** of a vector of integers `(x, y)` is its angle counter-clockwise from +X, in
microdegrees, rounded, in the range (−180,000,000, 180,000,000] — a direction that rounds to
−180,000,000 is written 180,000,000. A tie never occurs here either: an angle with a rational
tangent is a rational number of degrees only at multiples of 45°. The direction of `F(θ)` is θ
itself for every θ in that range, because `F(θ)` is within 10⁻⁹ radian of θ.

These frames are defined. For a wall `W`, `S` is the position of its start junction, `d = (dx, dy)`
its direction (5.2), `n = (−dy, dx)` the normal to its left (5.5), `t = d / |d|` and `m = n / |d|`
the unit vectors along it and to its left, and `a` and `b` its face offsets (5.4).

| Frame of | Origin `O` | `Oz` | Facing `f` |
|---|---|---|---|
| a level `L` | `(0, 0)` | `L.elevation` | `(1, 0)` |
| a `wallFace` host (13.3) on wall `W`, side `"left"` | `S + offset·t + a·m` | `W`'s base elevation + `height` | `n` |
| a `wallFace` host on wall `W`, side `"right"` | `S + offset·t − b·m` | `W`'s base elevation + `height` | `−n` |
| a `surface` host on room `R` of level `L`, `"floor"` | `position` | `L.elevation` | `F(rotation)` |
| a `surface` host on room `R` of level `L`, `"ceiling"` | `position` | `L.elevation + L.height` | `F(rotation)` |
| a `free` host on level `L` | `position` | `L.elevation` | `F(rotation)` |
| an opening `O1` on wall `W` | `S + (offset + width / 2)·t` | `O1`'s sill elevation (7.4) | `n` when `O1`'s `swing` is `"left"`, `−n` when it is `"right"` |

For an opening, `offset`, `width` and `swing` are its own (7.1, 7.2; `swing` defaults to
`"right"`). A wall-face
origin is on the chosen face of the wall; an opening's is on the location line, at the middle of
the opening, and faces the side its door swings into — for a window, which has no swing, the
default `"right"`: the wall's interior side (5.4). Every coordinate of these origins and axes is of
the form `p + q·√m` with rational `p`, `q` and an integer `m`, so every derived value below is
computed exactly and rounded once (2.2).

A deriver MUST compute facing vectors, directions and frames exactly as this section defines. {#FS-CORE-13.1.1 MUST}

## 13.2 Boxes and footprints

A **box** is `{ "min": [x, y, z], "max": [x, y, z] }`, two triples of lengths in a frame: it is the
set of points whose local coordinates lie between `min` and `max` on each axis.

| Member | Type | Default | Meaning |
|---|---|---|---|
| `min` | array of three lengths | — (always present) | the least local x, y and z |
| `max` | array of three lengths | — (always present) | the greatest local x, y and z |

A box MUST have exactly the members `min` and `max`, each an array of three lengths. {#FS-CORE-13.2.1 MUST}

Each of a box's three extents, `max` minus `min` on one axis, MUST be at least 1,280 base units (1 mm). {#FS-CORE-13.2.2 MUST}

The **footprint** of a box in a frame is its outline in plan: the four points with local
coordinates `(min.x, min.y)`, `(max.x, min.y)`, `(max.x, max.y)` and `(min.x, max.y)`, each mapped
to plan exactly and rounded once, as a ring that starts at its least vertex (6.2) and runs
counter-clockwise. Its **bottom** is `Oz + min.z` and its **top** is `Oz + max.z`, both integers.
Because every extent is at least 1,280 and rounding moves a point by less than one base unit, a
footprint is always a strictly convex quadrilateral.

## 13.3 Hosts

A `host` is one of three forms:

| `host` | Meaning |
|---|---|
| `{ "mode": "wallFace", "wall": W, "side": "left" or "right", "offset": length, "height": length }` | on a face of wall `W`, `offset` along its location line from its start junction and `height` above its base elevation |
| `{ "mode": "surface", "room": R, "surface": "floor" or "ceiling", "position": point, "rotation"?: angle }` | on the floor or the ceiling of room `R`, at `position`, turned by `rotation` |
| `{ "mode": "free", "level": L, "position": point, "rotation"?: angle }` | standing free on level `L` at `position`, turned by `rotation` |

`rotation` defaults to `0`, which faces +X; it is counter-clockwise positive, and it lies in
(−180,000,000, 180,000,000]. The ceiling of a room is taken, in this draft, at its level's
elevation plus the level's `height`: ceilings are not yet derived (0.5), and a later draft that
derives them will say how a ceiling host follows them.

A `host` MUST have exactly the members of one of the three forms, each of the type its table gives: `offset` and `height` MUST NOT be negative, and `rotation` MUST lie in (−180,000,000, 180,000,000]. {#FS-CORE-13.3.1 MUST}

A `wallFace` host's `offset` MUST NOT exceed the length of its wall's location line. {#FS-CORE-13.3.2 MUST NOT}
As for openings (7.3), the test is exact: `offset² ≤ dx² + dy²`.

A `wallFace` host's `height` MUST NOT exceed its wall's top elevation minus its base elevation. {#FS-CORE-13.3.3 MUST NOT}

A `surface` host's `position` MUST lie strictly inside the room polygon of its room's face: inside the outer ring, and outside and off every hole ring (6.3.4). {#FS-CORE-13.3.4 MUST}

An extension element's `fallback.level` MUST be its host's level: the wall's level for a `wallFace` host, the room's level for a `surface` host, and the host's `level` for a `free` host. {#FS-CORE-13.3.5 MUST}

**Hosted elements follow their host.** This is a property of derivation, not a separate rule:
every position of a hosted element is relative to its host — a distance along a wall and a height
above its base, an elevation above a level — so that when an edit moves the wall, changes its
thickness or justification, or raises the level, the derived placement moves with it and the
document does not change. A `surface` or `free` host's `position` is a plan point, so it follows
its level's elevation but not the room's walls; the room is what it is checked against (13.3.4).

## 13.4 Placement

The **placement** of a hosted element is its host's frame, reported as:

- `point` — `[x, y, z]`: the frame's origin, `x` and `y` rounded once, and `z = Oz`;
- `facing` — the direction (13.1) of the frame's facing vector: for a `wallFace` host, the
  outward normal of the chosen face; for a `surface` or `free` host, its `rotation`.

A deriver MUST derive the placement of every extension element that has a host, in a valid document. {#FS-CORE-13.4.1 MUST}

## 13.5 Clearance envelopes

A **clearance envelope** is a box, in an element's frame, that names space the element needs kept
clear. Envelopes are declared in a `clearances` object, mapping an envelope name —
`^[a-z][A-Za-z0-9]*$` — to an envelope:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `purpose` | `"workingSpace"`, `"fixtureClearance"`, `"swing"` or `"access"` | — (always present) | why the space is kept clear |
| `shape` | `"box"` | — (always present) | the envelope's shape; `"box"` is the only shape in this draft |
| `min`, `max` | as a box (13.2) | — (always present) | the envelope, in the frame of the element it belongs to |

| Purpose | For |
|---|---|
| `workingSpace` | space a person works in front of equipment: an electrical panel, a furnace |
| `fixtureClearance` | space a fixture needs around it: in front of a toilet, beside a lavatory |
| `swing` | space a moving part sweeps: a door leaf, a casement sash, an appliance door |
| `access` | space to reach something: an attic hatch, a cleanout, a window to escape through |

Clearances are declared by **door and window types** (8.4), and apply in the frame of every opening
the type fills; and by **extension elements** (12.5), in their own frame. An extension that has
types of its own resolves an element's clearances from its type when it writes the element.

A `clearances` object MUST map names matching `^[a-z][A-Za-z0-9]*$` to envelopes that have exactly the members of the table, each of the type the table gives, and MUST appear only on door types, window types and extension elements. {#FS-CORE-13.5.1 MUST}

An envelope obeys 13.2.2, as every box does. For every envelope, a deriver derives its **owner** —
the opening or the extension element it is placed for — its name, its purpose, the owner's level,
and its footprint, bottom and top in the owner's frame (13.2).

A deriver MUST derive every clearance envelope of a valid document as this section defines. {#FS-CORE-13.5.2 MUST}

> [!note] Why a door's swing is a box
> A door leaf of width `w` hinged at one jamb sweeps a quarter circle of radius `w`. Its bounding
> box in the opening's frame — forward 0 to `w`, left −`w`/2 to `w`/2, centred on the opening —
> is the same whichever jamb it hangs from, so one envelope on the door type serves every hinge;
> and a box keeps every footprint a quadrilateral with exactly computable corners. An arc would
> need circle-and-polygon intersection, whose exact form needs nested square roots that no
> deriver could round consistently without a much heavier arithmetic. The cost is the corner the
> leaf never reaches, which a rule that cares can subtract.

## 13.6 The overlap measure

Two clearance envelopes **overlap** when the interiors of their footprints intersect — some point
lies strictly inside both — and their vertical ranges overlap by a positive length: the greater
bottom is less than the lesser top. Envelopes that only touch do not overlap. The test is made on
the rounded footprints, with exact integer arithmetic; since footprints are convex, they overlap
in plan exactly when, for every edge of either footprint, the two footprints' projections onto
that edge's normal overlap by a positive length.

The overlap measure is not an invariant and not a lint: envelopes overlapping is normal while a
plan is drawn, and only a rule knows which overlaps matter — a door swing over a rug is fine, over
a panel's working space is not. Core derives the measure once, so that every rule (Floorspec
Rules) reads the same answer.

A deriver MUST derive every pair of envelopes of different owners that overlap, as this section defines. {#FS-CORE-13.6.1 MUST}

## 13.7 Related

FLR-ADR-002 (hosted, relative placement), FLR-ADR-004 (exact integer geometry), FLR-ADR-007
(extension kinds and fallbacks), FLR-ADR-011 (rules read core measures).

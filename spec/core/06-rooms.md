# 6. Rooms

A room is not drawn; it is found. The edges of a level divide the plane into regions, and each
enclosed region is a room's place. What a document stores for a room is only what cannot be
derived — its name, its function, its finishes — and an **anchor**, the point that says which
region it is. Move a wall and the room's outline follows; split a room with a new wall and the
anchor decides which half keeps its name (FLR-ADR-002).

## 6.1 Faces

The location lines of a level's edges (walls and separators together) divide the plane into
**faces**: the connected regions of the plane that remain when every location line is removed.
Exactly one face is unbounded — the outside. Every other face is **bounded**.

The boundary of a bounded face is one **outer cycle** and zero or more **inner cycles**. An inner
cycle is the outline of a group of edges standing inside the face without touching its outer
cycle — a chimney chase, or a freestanding closet.

A boundary is walked as a sequence of **half-edges**: an edge taken in one direction, with the
face on its left. Arriving at junction `J` along edge `e_m` (in `J`'s angular order, 5.6), the walk
leaves along `e_(m−1)`, the next edge clockwise. The outer cycle of a bounded face is walked
counter-clockwise; its inner cycles are walked clockwise. A walk that meets an edge with a free
end goes around it, along one face and back along the other.

## 6.2 Room polygons

The **room polygon** of a bounded face is its region shrunk to the faces of its walls: what you
would measure inside the finished walls. It has one **outer ring** and one **hole ring** for each
inner cycle.

Each ring is built by walking its cycle. Where the walk passes through junction `J`, arriving along
`e_m` and leaving along `e_(m−1)`, it passes through wedge `m − 1` at `J`; the ring takes that
wedge's corner sequence (5.6) in reverse — first the point on `e_m`'s face, then the point on
`e_(m−1)`'s. The ring is the concatenation of these points around the whole cycle, rounded (2.2),
with each vertex that equals the one before it removed (the first vertex counts as following the
last).

A deriver MUST derive the room polygon of every bounded face as defined in this section. {#FS-CORE-6.2.1 MUST}

A derived ring starts at its least vertex — the one with the least `x`, and of those the least
`y` — and keeps the orientation of its walk: counter-clockwise for the outer ring, clockwise for
holes. Holes are listed in the order of their first vertices, compared the same way. These rules
make a derived room polygon a single, comparable value.

A room polygon is **degenerate** when its outer ring or any hole ring has fewer than three
vertices, is not simple, or does not have its orientation with positive area; or when a hole ring
is not strictly inside the outer ring; or when two hole rings touch or overlap. A face between
two walls closer together than their thickness has a degenerate room polygon.

## 6.3 Anchors and room identity

Each room has an `anchor`: a point on its level. The room's **face** is the face that contains the
anchor.

A room's anchor MUST lie in a bounded face of its level: not in the unbounded face, and not on any location line. {#FS-CORE-6.3.1 MUST}

Two rooms MUST NOT have their anchors in the same face. {#FS-CORE-6.3.2 MUST NOT}
Removing the wall between a kitchen and a dining room joins two faces; the document is invalid
until one of the two rooms is removed or a separator divides the space again. Floorspec does not
choose which room survives.

The room polygon of a room's face MUST NOT be degenerate. {#FS-CORE-6.3.3 MUST NOT}

A room's anchor MUST lie strictly inside the room polygon of its face: inside the outer ring, and outside and off every hole ring. {#FS-CORE-6.3.4 MUST}
An anchor inside the thickness of a wall that bounds its face fails this test.

A bounded face with no anchor is an **unanchored face**: a room nobody has named. It is not an
error, and a deriver reports it; validators report it as an informational lint (`FS-LINT-003`).

## 6.4 Net area

A room's **net area** is the area of its room polygon: the area of its outer ring minus the areas
of its hole rings, each computed with the shoelace formula from the rounded vertices. It is in
square base units and is a multiple of one half; one square foot is 152,212,340,736 square base
units.

A deriver MUST compute each room's net area exactly, from the rounded vertices of its room polygon. {#FS-CORE-6.4.1 MUST}

Net area is derived, never stored. Other areas a code or a market needs — gross area, or a house's
finished area by a published measurement standard — are named measures in Floorspec Rules, not
members of the document.

## 6.5 Room members

| Member | Type | Default | Meaning |
|---|---|---|---|
| `level` | reference to a level | — (always present) | the level the room is on |
| `anchor` | point | — (always present) | which face is this room (6.3) |
| `function` | room function (4.1) | `"unspecified"` | what the room is for |
| `wallFinish` | reference to a material | absent | the finish of the walls that face this room |
| `floorFinish` | reference to a material | absent | the floor finish |
| `ceilingFinish` | reference to a material | absent | the ceiling finish |
| `name`, `extensions`, `extras` | | | 1.4 |

## 6.6 Lints

A validator SHOULD report these with the codes of chapter 10. {#FS-CORE-6.6.1 SHOULD}

- **Unanchored face** (`FS-LINT-003`, information): a bounded face with no anchor, with its room
  polygon as the location.
- **Degenerate face** (`FS-LINT-004`, warning): a bounded face with no anchor whose room polygon is
  degenerate — usually two walls drawn too close together.

## 6.7 Slabs

A **slab** is an authored floor or deck that is not derived from a room: a patio, a porch deck, a
landing. Floors and ceilings derived from rooms are defined in a later draft (see 0.5).

| Member | Type | Default | Meaning |
|---|---|---|---|
| `level` | reference to a level | — (always present) | the level the slab belongs to |
| `boundary` | polygon (2.6) | — (always present) | its outline in plan |
| `thickness` | length | — (always present) | its thickness |
| `offset` | length | `0` | the height of its top above the level's elevation |
| `material` | reference to a material | absent | its top surface |
| `name`, `extensions`, `extras` | | | 1.4 |

A slab's `thickness` MUST be greater than zero. {#FS-CORE-6.7.1 MUST}

Slabs do not take part in room derivation.

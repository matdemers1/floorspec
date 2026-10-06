# 21. Arc edges

A wall or a room separator may bend: from Core 0.4 an edge of a level's graph (5.2) can run along a
circular arc from its start junction to its end junction. A curved bay, a rounded stair hall, a
quarter-round corner are drawn this way, and the rooms behind them are found exactly as any other room
is (chapter 6).

The arc itself is never computed with. Its exact points are irrational, the points where its faces meet
other walls are worse, and two programs that compute with them in floating point disagree. So every value
this specification derives from an arc edge — its outline, the rooms it bounds, where its openings stand,
whether it crosses another edge — comes from one integer polyline that follows the arc to within a
millimetre: the arc's **polyline**, made by the iterated snap rounding of 21.2. Every step of it is an
exact computation on integers, rounded once (2.2), in an order this chapter fixes, so two conformant
implementations derive the same polyline point for point, and everything after it is the geometry of
straight segments that chapters 5 to 7 already define (FLR-REQ-143).

## 21.1 The arc

An edge with an `arc` member is an **arc edge**; an edge without one is straight, as in every earlier
draft.

| Member | Type | Default | Meaning |
|---|---|---|---|
| `arc` | `{ "sagitta": length }` | absent: the edge is straight | on a wall or a separator (5.2): the arc it runs along |

The **sagitta** `h` is the distance from the middle of the edge's **chord** — the segment from its start
junction's position `S` to its end junction's position `E` — to the middle of the arc, measured at right
angles to the chord: to the left of the chord, seen from `S` towards `E`, when `h` is positive, and to
its right when `h` is negative. A wall's left is its exterior (5.4), so a wall drawn clockwise round an
enclosure with a positive sagitta bulges outwards, like a bay.

A wall's or a separator's `arc` MUST have exactly the member `sagitta`, a length that is not zero. {#FS-CORE-21.1.1 MUST}

With `d = E − S`, `|d|` the chord's length and `n = (−d_y, d_x)` the normal to its left (5.5):

- the arc's **midpoint** is `M + h · n / |d|`, where `M = (S + E) / 2`;
- its **radius** is `R = (|d|² + 4h²) / (8|h|)`, a rational number;
- it turns through its **sweep**, `4 · atan(2|h| / |d|)`, which is 180° when `2|h| = |d|`.

An arc edge's arc MUST be at most a semicircle: `4h² ≤ |d|²`. {#FS-CORE-21.1.2 MUST}

A sagitta keeps an arc an arc when its junctions move: drag one end of a curved wall and it stays a curve
with the same bulge. An arc of more than a semicircle is two arcs, with a junction between them; and two
edges still may not join the same two junctions (5.2.2), so a round room has at least three.

## 21.2 The polyline: iterated snap rounding

The **polyline** of an arc edge is a list of integer points — its **vertices** — from `S` to `E`. With
the tolerance `τ = 1,280` base units (1 mm), the polyline of the arc from `S` to `E` with sagitta `h`,
written `poly(S, E, h)`, is:

1. **A flat arc is its chord.** When `|h| ≤ τ`, the polyline is `[S, E]`.
2. **Snap the midpoint.** Otherwise, let `P` be the arc's midpoint (21.1) with each coordinate rounded
   once: `P = (round(x), round(y))` of the exact point `M + h · n / |d|`.
3. **Halve the arc.** Let `R` be the arc's radius, and for each half — `S` to `P`, and `P` to `E` — let
   its sagitta be the sagitta of its chord on a circle of radius `R`, rounded once, with the sign of `h`:

   ```text
   h₁ = sign(h) · round(R − √(R² − |P − S|² / 4))
   h₂ = sign(h) · round(R − √(R² − |E − P|² / 4))
   ```

4. **Iterate.** The polyline is `poly(S, P, h₁)` followed by `poly(P, E, h₂)` without its first point,
   which is `P` again.

Each half is an arc in its own right, given by its own three integers, and is halved again, with its own
radius, until its sagitta is at most `τ`. The polyline's **segments** are the straight segments between
consecutive vertices, numbered from 1 at `S`; its first and last vertices are the edge's junctions, and
every other vertex is a point of the polyline only, never a junction.

A deriver MUST derive the polyline of every arc edge as this section defines, and MUST derive every value that this specification takes from an arc edge's location line from that polyline and from no other approximation of the arc. {#FS-CORE-21.2.1 MUST}

> [!note] Why the result is the same everywhere
> Every number in steps 1 to 4 is an integer, a rational number, or a number `p + q·√m` with rational
> `p`, `q` and an integer `m` — the midpoint's coordinates are `(S + E)/2 ± h·d·√(|d|²)/|d|²`, and a
> half's sagitta is a rational minus the square root of a rational. Rounding such a number, ties to even,
> is decided exactly with integer arithmetic, as 2.2 already requires of every corner point (5.5); no
> step needs a floating-point value, a trigonometric function or π. The order is fixed: the left half
> before the right, depth first. So the polyline is a function of `S`, `E` and `h` alone, the same in
> every conformant implementation — in JavaScript in a browser as on a server. And it does not depend on
> which way the edge is drawn: the arc from `E` to `S` with sagitta `−h` is the same arc, its midpoint the
> same point and its halves the same halves, so its polyline is the same polyline reversed.
>
> The square root in step 3 is always of a positive number: an arc of at most a semicircle has a
> radius at least `|h| > τ`, so each half's chord, within one base unit of a chord of at most a quarter
> circle, is shorter than the diameter `2R`. The recursion ends: each halving divides a sagitta by about
> four. A polyline therefore has at most a few hundred segments, each about `√(8Rτ)` or more long — a
> semicircle of 3 m radius has 64, of 50 m has 256 — every vertex is within a few base units of the
> circle, every segment within `τ` of the arc it replaces, and consecutive segments always turn the same
> way, by far more than one rounding can change, so a polyline never crosses or touches itself.

## 21.3 Arc edges in the graph

For everything chapters 5 and 6 define, an arc edge is the chain of its segments, joined at its vertices:

- its **location line** (5.2) is its polyline, and the **interior** of its location line is the polyline
  without its two ends;
- at its start junction it leaves along its first segment and at its end junction along its last: those
  are its outgoing directions in the angular order of 5.6, and the segments 5.8's joins act on;
- at each vertex of its polyline, its two segments meet as two edges meet at a junction with two edges
  and the default join: each segment has the face lines (5.5) of a straight edge from the vertex where it
  starts to the vertex where it ends, with the arc edge's own face offsets, and the vertex has two wedges
  (5.6);
- faces and room polygons (6.1, 6.2) walk its segments as edges, and pass through its vertices as through
  junctions with two edges — except where a join cuts a face vertex off (21.4).

5.3 applies to arc edges with these location lines, with one addition that two straight edges never
need: a polyline can touch another line without crossing it.

Where either of two edges on a level is an arc edge, their location lines MUST NOT meet at a point interior to both nor overlap in a segment of positive length, and a junction on the level MUST NOT lie in the interior of an arc edge's location line. {#FS-CORE-21.3.1 MUST NOT}

These are tested exactly on the integer vertices, as 5.3's are. They are reported with 5.3's codes: two
lines that meet at a point interior to both — where segments cross, or where a vertex of one lies on the
other — with `FS-INV-104`; two that overlap with `FS-INV-106`; a junction in an arc edge's interior, a
vertex included, with `FS-INV-105`. Unlike two straight edges, an arc edge can overlap another edge
without leaving a junction inside either, so `FS-INV-106` need not come with `FS-INV-105` here.

A deriver MUST compute the wedges and corner sequences at every junction and at every vertex of an arc edge's polyline taking each of its segments as a straight edge with the arc edge's face offsets, as 5.5, 5.6 and 5.8 define, this section adds and 21.4 refines at junctions. {#FS-CORE-21.3.2 MUST}

## 21.4 Faces, joins and the outline of an arc wall

An arc edge's **face vertices** are the points where its faces turn: at each vertex `V` of its polyline
other than its ends, the **left face vertex** is the corner point of the wedge at `V` on the edge's left —
the intersection of the left face lines of the two segments that meet at `V`, both taken in the edge's
direction, or the foot of `V` on them when they are parallel — and the **right face vertex** likewise on
its right.

A segment is short — a few hundred millimetres, often less — and where an arc wall meets another wall at
a sharp angle, the corner of their faces can lie beyond the arc's first face vertex: the join reaches
past the first segment. So at a junction, each face of an arc edge is not one face line but a **face
path**: the face lines of its segments in turn, leaving the junction, each **piece** of it ending at the
rounded face vertex where it meets the next. A straight edge's face path is its one face line, with no
end. Wherever 5.6 and 5.8 intersect a face line of one edge at a junction with a face line of another —
the corner point of a wedge, and the point `p` of a butt join — the two faces are intersected along
their paths:

1. When the two faces' first pieces are parallel, 5.6's feet apply, as for straight edges.
2. A point lies **on** a piece of a path when it is neither before the rounded face vertex that starts
   the piece nor past the one that ends it: with `d` the direction of the piece's segment away from the
   junction, `(P − v) · d ≥ 0` for the vertex `v` that starts it, and `(P − w) · d ≤ 0` for the vertex
   `w` that ends it — the first piece has no start, the last no end. `P` is the exact point; the
   comparison is exact.
3. The corner is the first intersection, in this order, that lies on both its pieces: the pieces `a`
   of the first face — the one whose face line 5.6 or 5.8 names first — from the junction outwards, and
   for each, the pieces `b` of the second from the junction outwards, skipping any pair whose lines are
   parallel. When no pair has one, the corner is the intersection of the two first pieces.

The face vertices before the pieces the corner lies on — `a` of the first face's and `b` of the
second's — are **cut off** by the join: they are no longer vertices of the
edge's face, of its wall's outline or of the room polygons along it.

A deriver MUST intersect the faces of edges at every junction an arc edge ends at along their face paths, and cut off the face vertices before the pieces each corner lies on, as this section defines. {#FS-CORE-21.4.1 MUST}

Every step is exact or an exact comparison with integers, and the order is fixed, so the corner points,
like the polyline, are the same everywhere. A wedge's corner point (5.6) and the face vertices it cuts off
are what room polygons and junction fills use; the face ends of 5.8's butt joins, which may be different
points, are what wall outlines use — as for straight walls, a join changes how the wall body is divided
and never a room.

An arc wall's four **face ends** are those of 5.7 and 5.8, at its start junction from its first segment
and at its end junction from its last, found as above. Its left and right face vertices are those that
no join at either end cuts off.

A deriver MUST derive every arc wall's face ends and its left and right face vertices, from its start to its end, rounded as 2.2 requires. {#FS-CORE-21.4.2 MUST}

The outline of an arc wall is the polygon `startRight → its right face vertices → endRight → endLeft →
its left face vertices, from the end back to the start → startLeft`, after rounding and after removing each
vertex equal to the one before it (the first vertex counts as following the last).

An arc wall's outline MUST be a simple polygon with positive area and counter-clockwise orientation. {#FS-CORE-21.4.3 MUST}
A wall too thick for the curve of its arc — whose inner face would have to turn on a radius less than
zero — fails this test, as a stub too short for its joins fails 5.7.2; both are reported with `FS-INV-109`. A
junction where an arc wall meets other walls has its junction fill as 5.7 defines it, from the wedges of
the segments that meet there.

## 21.5 Rooms bounded by arcs

The faces of a level with arc edges are the regions its polylines bound, and a room polygon's rings run
along the faces of arc walls through their face vertices, by 6.2 unchanged. So a curved room's polygon,
its net area (6.4) — computed exactly from its rounded vertices, as every room's is — its floor and its
ceiling (chapter 15) are those of the polygon that follows its polyline. A room's anchor (6.3) is in the
face its polyline bounds: a point between the polyline and the circle it follows is on whichever side of
the polyline it is.

A deriver MUST derive the faces, room polygons and net areas of a level that has arc edges as chapter 6 defines, with the location lines of 21.3. {#FS-CORE-21.5.1 MUST}

## 21.6 Lengths and stations

Distances along a straight wall are exact (7.3). Along an arc wall they are measured on its polyline, with
each segment's length rounded once, so that a distance along it is an integer:

- the **length** of segment `k`, from vertex `V_(k−1)` to `V_k`, is `ℓ_k = round(|V_k − V_(k−1)|)`;
- the **station** of vertex `V_k` is `s_k = ℓ_1 + … + ℓ_k`, with `s_0 = 0` at `S`;
- the arc wall's **length** `L` is the station of `E`, the sum of all its segments' lengths;
- the **point at distance** `t` along it, for `0 ≤ t ≤ L`, is on the segment `k` with
  `s_(k−1) ≤ t < s_k` — or on the last segment, when `t = L` — at
  `V_(k−1) + (V_k − V_(k−1)) · (t − s_(k−1)) / ℓ_k`, a rational point; and that segment is the one the
  distance **falls on**.

A segment's length is never a tie (`(k + ½)²` is not an integer) and never zero (21.2), and every point at
a distance is exact; each is rounded once where it is output.

Wherever this specification measures a distance along a wall's location line — an opening's `offset` and
`width` (7.3, 7.4), a `wallFace` host's `offset` (13.1, 13.3), a finish region's `from` and `to` (18.5) —
on an arc wall it is a distance along its polyline:

- An opening's **start point** and **end point** (7.4) are the points at distances `offset` and
  `offset + width`. The straight segment between them is the opening's **chord**: a door or a window in a
  curved wall is straight, and stands on its chord. The opening cuts the wall between the two points.
- An opening's frame (13.1) has its origin at the middle of its chord, exact, and its facing vector at
  right angles to the chord: the chord's left normal, as the shortest vector of integers in its
  direction, when its `swing` is `"left"`, and the opposite when it is `"right"`.
- A `wallFace` host's frame has its origin at the point at distance `offset`, moved `a` along the unit
  left normal of the segment that distance falls on (side `"left"`) or `b` along its right normal (side
  `"right"`), and that normal, as a vector of integers, as its facing vector.
- A region of a face (18.5) runs between the points at distances `from` and `to`.

A deriver MUST derive the start and end points of every opening on an arc wall, and the frames of every opening on one and of every `wallFace` host on one, as this section defines. {#FS-CORE-21.6.1 MUST}

On an arc wall, an opening's `offset + width`, a `wallFace` host's `offset` and a finish region's `to` MUST NOT exceed its length `L`. {#FS-CORE-21.6.2 MUST NOT}
These are 7.3.1, 13.3.2 and 18.5.3 with an arc wall's length in place of the exact length of a straight
line, and are reported with their codes: `FS-INV-302`, `FS-INV-501` and `FS-INV-1002`.

The opening-in-a-join lint (7.5) measures, on an arc wall, each face end at the start along its first
segment from `S` and each at the end along its last segment back from `E`, compared with `offset` and
with `L − (offset + width)`. A texture's `s` coordinate on the face of an arc wall (18.3) is the distance
along the wall of the point's projection on the segment it lies against — its station plus its
distance along that segment — so a tile runs round the curve without a seam.

## 21.7 Derived values

For every arc wall, besides the four face ends and two elevations every wall has, a deriver derives:

| Value | What it is |
|---|---|
| `polyline` | its polyline (21.2), from `S` to `E` |
| `length` | its length `L` (21.6) |
| `left`, `right` | its left and right face vertices (21.4), rounded, from its start to its end |

An arc separator derives nothing of its own: what it changes is the faces and the room polygons on either
side of it.

## 21.8 Lints

A validator SHOULD report this with the code of chapter 10. {#FS-CORE-21.8.1 SHOULD}

- **Flat arc** (`FS-LINT-020`, information): an arc edge whose sagitta is at most `τ`: its polyline is its
  chord (21.2, step 1), so it is derived as a straight edge — of length `round(|d|)` along it (21.6) — and
  is drawn as one.

## 21.9 What this draft does not define

- arcs of any curve but a circle — ellipses, splines, a wall that bends twice — and arcs of more than a
  semicircle as one edge (21.1.2);
- the exact circle as derived geometry: a tool may draw an arc wall with true arcs, but every normative
  value, its area included, is the polyline's;
- an opening that follows its wall's curve: a door or a window in an arc wall stands on its chord;
- a tray ceiling whose border is wider than the segments of an arc that bounds its room: 15.4 moves each
  edge of the room polygon, and near a corner an arc's short edges run backwards (`FS-INV-703`);
- a stair, a slab or a roof footprint with curved edges.

## 21.10 Related

FLR-REQ-143 (arc edges and iterated snap rounding), FLR-R-004 (planarity after snap rounding), FLR-ADR-002
(the junction graph is the geometric truth), FLR-ADR-004 (exact integer geometry), FLR-ADR-020 (exact
face-line corners).

# 16. Roofs

A roof is drawn as its **footprint** — a polygon in plan, usually the outer faces of the walls it
sits on — and a few numbers on each edge of it: whether the edge is a **gable**, a vertical end
under which the roof stops, or slopes up from it at a **pitch**, and how far the roof
**overhangs** it. Everything else is derived: the **eave outline**, the footprint moved out by the
overhangs; and, for the roofs this draft can derive exactly, the **surface** — its faces, the
ridges, hips, valleys and breaks between them, and the ends of its gables. A roof with every edge
sloping is a hip roof, with gables a gable roof, with one sloped edge a shed, and with none a flat
roof; its edges may slope at different pitches, as a saltbox's do.

This chapter defines a roof's members, its eave outline, the class of roofs whose surface this
draft derives, and the exact values a deriver derives. Every value is exact and rounded once
(2.2).

## 16.1 The roof

A **roof** is an element of the `roofs` collection (1.1):

| Member | Type | Default | Meaning |
|---|---|---|---|
| `level` | reference to a level | — (always present) | the level the roof belongs to |
| `footprint` | polygon (2.6) | — (always present) | its outline in plan, before overhangs |
| `height` | length | its level's `height` | the elevation of its eaves above its level's elevation |
| `pitch` | pitch (2.5) | absent: none | the pitch of every edge that is not a gable and has no pitch of its own |
| `overhang` | length | `0` | how far the roof overhangs every edge that has no overhang of its own |
| `edges` | object: edge index → edge (below) | `{}` | what differs, edge by edge |
| `thickness` | length | absent: not declared | the thickness of the roof under its surface, measured vertically |
| `material` | reference to a material | absent | its top surface |
| `name`, `extensions`, `extras` | | | 1.4 |

Edge `i` of a roof runs from its footprint's vertex `i` to vertex `i + 1` (the last edge back to
vertex `0`), and its member name in `edges` is `i` written in decimal: `"0"`, `"1"`, `"12"`. An
**edge** is an object:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `gable` | boolean | `false` | the edge is a gable: the roof stops above it in a vertical end, and does not slope up from it |
| `pitch` | pitch | the roof's `pitch` | the pitch the roof rises at from this edge |
| `overhang` | length | the roof's `overhang` | how far the roof overhangs this edge |

An edge that is absent from `edges` has the default `{}`: it takes the roof's values. `height`
defaults to its level's `height` — the default top of the level's walls (5.9) — so a roof that says
nothing about its height sits on them.

A roof MUST have only the members of these tables, each of the type the tables give: its `pitch` and every edge's `pitch` MUST have a `rise` and a `run` that are integers from 1 to 2⁵³ − 1; its `overhang` and every edge's `overhang` MUST NOT be negative; its `thickness` MUST be greater than zero; every member name of `edges` MUST be an edge index written in decimal without leading zeros; and an edge whose `gable` is `true` MUST NOT have a `pitch`. {#FS-CORE-16.1.1 MUST}

Every member name of a roof's `edges` MUST name an edge of its footprint: it is less than the number of the footprint's vertices. {#FS-CORE-16.1.2 MUST}

A roof's `footprint`, like every polygon, is simple and encloses a positive area (2.6.1,
`FS-INV-009`). It is a list of plan points: it does not follow the walls under it, and an edit
that moves a wall does not move it (Floorspec Ops).

## 16.2 Edges

Each edge of a roof is one of three things:

- a **gable**, when its `gable` is `true`;
- **sloped**, when it is not a gable and has a pitch — its own, or the roof's;
- **level**, when it is neither: it has no pitch.

A roof whose every edge is level is **flat**. A roof is never part flat and part sloped:

A roof's edges MUST be all level or none of them level. {#FS-CORE-16.2.1 MUST}

A roof that is not flat MUST have at least one sloped edge. {#FS-CORE-16.2.2 MUST}
A roof whose every edge is a gable has walls and no slope; a flat roof says so by having no pitch.

Two consecutive edges of a roof's footprint MUST NOT be collinear. {#FS-CORE-16.2.3 MUST NOT}
A vertex between two collinear edges would let one straight eave have two overhangs, and its moved
lines would not meet (16.3).

A roof's **kind** is derived from its edges: `"flat"`; `"shed"` when exactly one edge is sloped;
`"gable"` when one or more edges are gables and two or more are sloped; and `"hip"` when every
edge is sloped.

## 16.3 The eave outline

A roof's **eave outline** is its footprint with every edge moved away from the footprint's inside
by its overhang. For the footprint's vertices `V₀ … Vₙ₋₁`, edge `i` runs from `Vᵢ` to `Vᵢ₊₁`, with
direction `dᵢ`, left normal `mᵢ = (−dᵢ.y, dᵢ.x)` and overhang `oᵢ`, and its **moved line** is

```text
{ P : mᵢ · P = mᵢ · Vᵢ − σ · oᵢ · |dᵢ| }
```

where `σ` is `1` when the footprint runs counter-clockwise and `−1` when it runs clockwise: the
line moved `oᵢ` to the right of a counter-clockwise footprint, which is its outside. The outline's
vertex `Vᵢ'` is the intersection of the moved lines of edges `i − 1` and `i`, which are never
parallel (16.2.3); it has the form of a corner point (5.5), and is rounded once. The eave outline
is the rounded `Vᵢ'`, in the footprint's order, so that its edge `i`, from `Vᵢ'` to `Vᵢ₊₁'`, is
edge `i` moved. On a footprint whose every edge is parallel to the X or the Y axis — a
**rectilinear** footprint — every `Vᵢ'` is an integer point and nothing is rounded.

A roof's eave outline MUST fit its footprint: for every edge, the edge from the rounded `Vᵢ'` to the rounded `Vᵢ₊₁'` MUST run the way the edge from `Vᵢ` to `Vᵢ₊₁` runs — the dot product of the two is greater than zero — and the eave outline MUST be a simple polygon (2.6) that runs the way the footprint runs. {#FS-CORE-16.3.1 MUST}
An overhang so wide that a short edge's moved edge disappears or turns back, or that two parts of
the outline meet across a notch, fails this test.

A roof's **eave** is its level's elevation plus its `height`: the elevation of the whole eave
outline. Every edge's eave is at the same elevation; an edge with a wider overhang reaches further
out at that elevation, so the roof over it rises higher.

## 16.4 Surfaces

The surface of a roof rises from its eave outline: from each sloped edge at its pitch, never from
a gable, which stands vertical under it. Every derived surface is the eave outline lifted point by
point to an **elevation** `z(P)`. This draft derives the surface of three classes of roof, and of
no other (16.4.6): flat roofs, shed roofs, and skeleton roofs. In this section the eave outline is
walked counter-clockwise — reversed, when the footprint runs clockwise — and each of its edges keeps
its index; a vertex where it turns left is **convex**, and one where it turns right **reflex**.

### 16.4.1 Flat roofs

A flat roof's elevation is its eave everywhere: `z(P) = eave`. Its one face is its eave outline.

### 16.4.2 Shed roofs

A roof with exactly one sloped edge, from `A` to `B` on the counter-clockwise outline, at pitch
`rise : run`, is one plane through that edge. With `n = (−(B − A).y, (B − A).x)`, the edge's normal
into the outline,

```text
z(P) = eave + (rise / run) · n · (P − A) / |n|
```

— of the form `p + q·√D` with rationals `p`, `q` and `D = n · n`, exact, as a vault's elevation is
(15.3). Its surface is derived when `n · (V − A) ≥ 0` for every vertex `V` of the outline: when no
part of the outline lies outside the line of its sloped edge, where the roof would fall below its
eave. Its one face is its eave outline, and every other edge is a gable.

### 16.4.3 Skeleton roofs

A roof with two or more sloped edges is a **skeleton roof**: a hip roof, a gable roof, a saltbox,
an L or a U with wings at different pitches. Every sloped edge rises at its own pitch and every gable
stands still, and where their planes meet is found by moving them inwards together, as a
**wavefront**, until nothing is left of it (16.4.4): the roof is its **weighted straight skeleton**,
lifted. Its surface is derived when every sloped edge of its eave outline has a length that is an
integer — an edge parallel to an axis, or an oblique edge along a Pythagorean direction such as
3 : 4 — and the wavefront never reaches a state of 16.4.6.

Elevations are measured from the eave: `t = z − eave`. Edge `i` of the counter-clockwise outline, from
`A` to `B`, has the normal `n = (−(B − A).y, (B − A).x)` into the outline, and `L = |n|`, its length.
A sloped edge at pitch `rise : run` has the **plane**

```text
z = eave + (rise / run) · (n · P − n · A) / L
```

and, at elevation `t`, the **line** of the points of its plane at that elevation,

```text
{ P : n · P = n · A + w · t },    w = L · run / rise
```

— its eave line moved inwards `t · run / rise`. A gable has `w = 0`: its line is its eave line at
every elevation. An edge's **speed** is `run / rise` — a shallow pitch moves fast — and a gable's is
`0`. Because `L` is an integer, every line has rational coefficients, and every elevation, point and
area this section computes is an exact rational: nothing is rounded before 16.5.

> [!note] The equal-pitch roofs of 0.3
> Core 0.3 derived only skeleton roofs whose sloped edges share one pitch on a rectilinear outline,
> with its gables at the ends of wings (FS-CORE-16.4.1, retired), by a rise distance measured as a
> Chebyshev distance. On that class the wavefront here reaches every point at exactly that rise
> distance, and the faces, gable ends and lines it derives are 0.3's, value for value; only two
> lines with the same rounded ends, which 0.3 left unordered, are now ordered by their kind (16.5).

### 16.4.4 The wavefront

The **wavefront** at an elevation `t` is a set of **wavefront polygons**, each a simple polygon
running counter-clockwise, given as a cycle of **wavefront edges**. A wavefront edge lies on the line
at `t` of an eave edge, and **carries** that edge — or, after a merge (below), every eave edge whose
plane it lies in. Its line and speed are its eave edges'. A **vertex** of a wavefront polygon is the
point where the lines at `t` of its two wavefront edges meet; as `t` grows, each vertex moves along a
straight line at a constant rate. At `t = 0` the wavefront is one polygon, the eave outline, with
one wavefront edge for each of its edges.

**Events.** After an elevation `t`, the next **event elevation** is the least `t′ > t` at which, in
some wavefront polygon, a wavefront edge has no length — its two vertices meet — or a vertex lies on
a wavefront edge of its polygon that does not end at it. Each is the root of an equation linear in
`t′`, exact. Until `t′` every polygon keeps its edges and their order, and each wavefront edge that
moves sweeps a **swept piece**: the quadrilateral of its two vertices at `t` and at `t′`, a piece of
the plane it carries.

**Resolution.** At an event elevation every event is resolved at once, from the wavefront's
position there, and never one at a time — so two events at one elevation, at one point or apart, a
vertex that meets an edge just as another edge vanishes, and any number of edges vanishing together,
all resolve the same way whatever order they might be found in. Each wavefront polygon, its vertices
placed at `t′`:

1. **Pieces.** Each of its edges with a length is split at every vertex that lies inside it. A piece
   covered once in each direction is dropped: the polygon has closed up there, two fronts meeting
   head on. Every other piece is covered once, in one direction, by one wavefront edge.
2. **Cycles.** The pieces bound the interior of the polygon at `t′`, which lies on their left. They
   are traced into cycles: after a piece, the cycle continues along the piece that leaves its end
   with the greatest turn to the left. Where the interior touches itself at a point — a vertex that
   has reached an edge, or two vertices that meet — this keeps the parts of the interior that touch
   there apart, and is the only way of doing so (Biedl et al., the *standard resolution*). Each cycle
   is a new wavefront polygon; consecutive pieces of one wavefront edge are one edge again.
3. **Runs.** In each new polygon, a **run** — consecutive wavefront edges that lie on one line and
   face the same way — is replaced by one wavefront edge that runs its whole length: the run's
   fastest edges continue over it, and the others stop where they are. When two or more are fastest,
   they share one plane, and the new edge carries all of their eave edges.

A part of the wavefront that closes to a segment or a point leaves no piece, and the propagation ends
when no wavefront polygon is left.

A deriver MUST compute the wavefront of a skeleton roof exactly, as this section defines it — every event elevation, vertex and swept piece an exact rational — resolving all the events at an event elevation together from the wavefront's position there, with the pieces traced by the greatest turn to the left. {#FS-CORE-16.4.3 MUST}

A deriver MUST replace every run of consecutive wavefront edges on one line facing the same way by its fastest edges, extended over the run, so that a slower edge in the run stops; edges of equal speed in a run continue as one edge carrying all of their eave edges. {#FS-CORE-16.4.4 MUST}

> [!note] Why the fastest edge wins
> Two wavefront edges become consecutive on one line when an edge between them vanishes — on a
> stepped eave, say, where a shallow plane behind a step catches up with a steep one. Their planes
> meet only in that line, so no hip or valley can run between them, and one of them must stop. The
> fastest continuing (Biedl et al. 2015, 4.1) keeps the roof as low as it can be: the steep face
> ends in a level **break** (16.4.5) and the shallow plane carries on above it, as a gambrel's
> does. It is the only resolution this draft allows.

### 16.4.5 Faces and lines

**Faces.** The swept pieces of a plane together cover the part of the outline the roof over which is
in that plane. Sloped edges that **share a plane** — that lie on one line, face the same way and have
one pitch, equal as ratios — share those pieces, which are divided between them as Core 0.3 divides
them: a point belongs to the edge whose extent along the common line is nearest its foot on that
line, so that two neighbouring edges' pieces are divided by the line across it midway between their
facing ends. The **face** of a sloped edge is the closure of the swept pieces that are its own. The
faces of the sloped edges cover the outline and meet only along their boundaries, and each is one or
more simple polygons whose vertices are nodes. The **nodes** of the roof are the vertices of its
outline and every point where the boundary of a face turns. A face's **polygon** is its boundary,
walked counter-clockwise through every node on it — including a node where the boundary runs straight
on but another face's turns.

**Lines.** Where the faces of two sloped edges `e` and `f` that do not share a plane meet along a
segment, the segment is a **line** of the roof, taken as long as it runs straight between the same two
faces. The boundary between the faces of edges that share a plane is a seam in one plane, not a line.
With `nₑ` and `n_f` their normals into the outline, `gₑ = (riseₑ / runₑ) · nₑ / |nₑ|` the direction
and rate at which the plane of `e` rises, `g_f` likewise, and `w` a vector across the segment into the
face of `e`, a line is:

- **level** when its two ends have the same elevation — which happens exactly when `e` and `f` are
  parallel — and then a **ridge** when they face each other, `nₑ · n_f < 0`, and a **break** when they
  face the same way, `nₑ · n_f > 0`: a level line where the roof over the same side changes its
  pitch;
- otherwise a **hip** when `(g_f − gₑ) · w > 0` — the roof falls away from it to both sides — and a
  **valley** when `(g_f − gₑ) · w < 0`.

### 16.4.6 Roofs whose surface is not derived

A roof is valid, and its eave outline is derived, whatever its edges; its surface is not derived
when it is:

1. a shed roof with part of its outline outside the line of its sloped edge (16.4.2);
2. a skeleton roof with a sloped edge whose length is not an integer — an oblique edge whose
   direction is not Pythagorean, such as one at 45°, whose planes have irrational coefficients;
3. a skeleton roof whose wavefront, at `t = 0` or just after an event elevation, has a gable's
   wavefront edge one end of which moves away from its other end — the wavefront would pass the end
   of the gable and the roof would need a vertical step inside its outline, as it does for every
   gable with a reflex end beside a sloped edge, such as a gable on the inner face of a U;
4. a skeleton roof whose wavefront, at `t = 0` or just after an event elevation, has a polygon none
   of whose edges moves — a part of the outline enclosed by gables alone, which the roof would never
   cover. This is a guard: no outline is known to reach it without reaching condition 3 first.

Conditions 3 and 4 are decided on the wavefront as 16.4.4 leaves it, before the next event
elevation is sought; the first that holds ends the propagation, and none of what it swept is kept.

A deriver MUST derive the surface of every flat roof, of every shed roof that 16.4.2 says is derived, and of every skeleton roof that reaches none of the states of 16.4.6, exactly as this section defines it, and MUST derive no surface for any other roof; a validator MUST report every other roof with `FS-LINT-015`. {#FS-CORE-16.4.2 MUST}

## 16.5 Derived roofs

A roof's **derived roof** is:

- its `kind` (16.2);
- its `outline`: the eave outline as a ring that starts at its least vertex (6.2) and runs
  counter-clockwise — reversed, when the footprint runs clockwise;
- its `eave` (16.3);
- its `surface`: `null` when its surface is not derived (16.4.6), and otherwise an object of:
  - `high`: the greatest elevation of the surface, rounded once — for a flat roof its eave, for a
    shed roof the greatest `z(V)` over the outline's vertices `V`, and for a skeleton roof the
    greatest `z` over its nodes;
  - `box`: `{ "min": [x₀, y₀, eave − thickness], "max": [x₁, y₁, high] }`, with `x₀`, `x₁`, `y₀` and
    `y₁` the least and greatest coordinates of the outline's vertices, and `thickness` the roof's,
    or `0` when it declares none;
  - `faces`: each face as `{ "edge", "polygon", "area" }` — `edge` the index of its sloped edge, and
    none for a flat roof's face; `polygon` its polygon (16.4.5) as points `[x, y, z]`, with `x` and
    `y` rounded once and `z` the exact elevation at the point rounded once, each point that equals
    the one before it removed (the first counts as following the last), starting at its least
    point — least `x`, then least `y`, then least `z`; and `area` its area in plan, computed from
    its rounded `x` and `y` as a room's net area is (6.4) — listed by `edge`, then by their first
    points, and leaving out a face whose rounded polygon has fewer than three points;
  - `gables`: each gable edge, from `A` to `B` on the counter-clockwise outline, as
    `{ "edge", "polygon" }`, where `polygon` is its **gable end**: `A` and then `B` at the eave, and
    then back from `B` to `A` along the surface through every node on the edge — for a shed roof,
    through `B` and `A` — each point `[x, y, z]` rounded as a face's are, each point that equals the
    one before it removed (the first counts as following the last); listed by `edge`;
  - `lines`: each line (16.4.5) as `{ "kind", "from", "to" }`, its `kind` `"ridge"`, `"break"`,
    `"hip"` or `"valley"` and its ends as points `[x, y, z]` rounded as a face's are, `from` the
    lesser of the two — compared by `x`, then `y`, then `z`; listed by `from`, then `to`, then
    `kind`. A flat or shed roof has none.

A deriver MUST derive every roof as this section defines it. {#FS-CORE-16.5.2 MUST}

The faces, gable ends and lines are what a mesh of the roof is made from; the mesh itself, the
roof's thickness as a solid, and the area of each face along its slope rather than in plan are not
normative in this draft (0.5).

## 16.6 What a roof does not do

A roof stands on its level and touches nothing else. In this draft:

- its footprint is plan points, and does not follow the walls under it (16.1);
- walls do not stop at it, and their tops are still their `top` (5.9);
- a ceiling does not follow it: a vaulted ceiling under a roof is drawn as a vault (15.3);
- nothing is hosted on it (chapter 13), and it takes no part in rooms or circulation.

## 16.7 Related

FLR-REQ-108 (a roof as a footprint with per-edge pitch, gable flag and overhang, covering gable, hip,
shed and flat roofs), FLR-REQ-109 (equal-pitch hip roofs derived with a straight skeleton),
FLR-REQ-144 (hip roofs with unequal per-edge pitches derived with a weighted straight skeleton),
FLR-REQ-145 (a roof whose pitches the engine cannot derive is flagged, not failed), FLR-ADR-004
(exact integer geometry), FLR-ADR-027 (Core 0.3), FLR-ADR-028 (Core 0.3 roofs). T. Biedl, M. Held,
S. Huber, D. Kaaser and P. Palfrader, *Weighted straight skeletons in the plane*, Computational
Geometry 48(5) (2015) 429–442 — the standard resolution of coinciding events, and the fastest edge
winning where parallel edges of different weights meet. Chapters 2 (pitch, polygons), 5 (corner points
and the top of walls), 15 (vaulted ceilings, whose exact form a shed roof shares) and Annex A
(`IfcRoof`).

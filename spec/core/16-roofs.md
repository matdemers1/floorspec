# 16. Roofs

A roof is drawn as its **footprint** — a polygon in plan, usually the outer faces of the walls it
sits on — and a few numbers on each edge of it: whether the edge is a **gable**, a vertical end
under which the roof stops, or slopes up from it at a **pitch**, and how far the roof
**overhangs** it. Everything else is derived: the **eave outline**, the footprint moved out by the
overhangs; and, for the roofs this draft can derive exactly, the **surface** — its faces, the
ridges, hips and valleys between them, and the ends of its gables. A roof with every edge
sloping at one pitch on a rectilinear outline is a hip roof, with gables a gable roof, with one
sloped edge a shed, and with none a flat roof.

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
no other (16.4.4). In this section the eave outline is walked counter-clockwise — reversed, when
the footprint runs clockwise — and each of its edges keeps its index; a vertex where it turns left
is **convex**, and one where it turns right **reflex**.

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

### 16.4.3 Equal-pitch roofs

A roof with two or more sloped edges, all at the same pitch `rise : run` — equal as ratios, so
`6 : 12` and `1 : 2` are one pitch — is an **equal-pitch** roof. Its surface is derived when:

1. its eave outline is rectilinear;
2. every gable edge's two neighbouring edges are sloped, and both its ends are convex;
3. for every gable edge `g`, no point of a sloped edge lies inside `g`'s **clearance**: the open
   rectangle outside the outline that has `g` as one side and is half as deep as `g` is long.

For such a roof, the **rise distance** `h(P)` of a point `P` of the outline — inside it or on it —
is the least, over its sloped edges `e`, of the Chebyshev distance from `P` to `e`:

```text
d∞(P, e) = min over the points Q of e of  max(|P.x − Q.x|, |P.y − Q.y|)
h(P)     = min over the sloped edges e of  d∞(P, e)
z(P)     = eave + (rise / run) · h(P)
```

> [!note] This is the straight skeleton
> On a rectilinear outline, a wavefront moving every sloped edge inwards at one speed — the
> straight skeleton, lifted at the roof's pitch — reaches a point exactly when a square centred on
> it first touches a sloped edge, so its arrival time is the rise distance and `z` is the
> straight-skeleton roof: hips at 45° in plan from every convex corner, valleys from every reflex
> one, and ridges where opposite edges meet. A gable edge does not move: it is the skeleton's edge
> of weight zero, standing vertical. Conditions 2 and 3 say where a gable makes the roof the
> rise distance above: at the end of a wing, with nothing in front of it within half its width.
> Mixed pitches need the weighted straight skeleton, and an outline with oblique edges a skeleton
> whose nodes are irrational in more than one radicand; neither is in this draft.

Every point where `h` changes form — every node of the skeleton — has coordinates that are
multiples of one half, because every crease of `h` lies on a line `x = (a + b) / 2`,
`y = (a + b) / 2`, `x − y = a − b` or `x + y = a + b`, where `a` and `b` are coordinates of the
outline's vertices. So `h` and `z` are rational at every node, and exact.

**Faces.** For a sloped edge `e` and a point `P`, let `pₑ(P)` be the distance of `P` from the line
of `e`, positive on the outline's side of it, and `aₑ(P)` the distance from the foot of `P` on that
line to `e` — `0` when the foot is on `e`. `P` is **of the face of** `e` when

- `pₑ(P) = h(P)` and `aₑ(P) ≤ h(P)` — the roof over `P` is in the plane that rises from `e`; and
- `aₑ(P) < a_f(P)` for every other sloped edge `f` with `p_f(P) = h(P)` and `a_f(P) ≤ h(P)` —
  of two collinear edges that face the same way, and so share a plane, the nearer one.

The **face** of `e` is the closure of the points inside the outline that are of its face. The faces
of the sloped edges cover the outline and meet only along their boundaries, and each is a simple
polygon whose vertices are nodes. The **nodes** of the roof are the vertices of its outline and
every point where the boundary of a face turns. A face's **polygon** is its boundary, walked
counter-clockwise through every node on it — including a node where the boundary runs straight on
but another face's turns.

**Lines.** Where the faces of two sloped edges `e` and `f` meet along a segment, and `e` and `f` are
not collinear edges facing the same way, the segment is a **line** of the roof, taken as long as it
runs straight between the same two faces. With `nₑ` and `n_f` the unit normals of `e` and `f` into
the outline, and `w` a vector across the segment into the face of `e`, a line is:

- a **ridge** when its two ends have the same rise distance: it is level;
- otherwise a **hip** when `(n_f − nₑ) · w > 0` — the roof falls away from it to both sides — and a
  **valley** when `(n_f − nₑ) · w < 0`.

The boundary between the faces of two collinear edges that face the same way is a seam in one
plane, not a line.

### 16.4.4 Roofs whose surface is not derived

A roof that is not flat, is not a shed roof whose surface is derived (16.4.2), and is not an
equal-pitch roof whose surface is derived (16.4.3) — a roof with sloped edges at different pitches,
an equal-pitch roof with an oblique edge, a gable that is not at the end of a wing — is valid, and
its eave outline is derived; its surface is not.

A deriver MUST derive the surface of every flat roof, of every shed roof that 16.4.2 says is derived, and of every equal-pitch roof that 16.4.3 says is derived, exactly as this section defines it, and MUST derive no surface for any other roof; a validator MUST report every other roof with `FS-LINT-015`. {#FS-CORE-16.4.1 MUST}

## 16.5 Derived roofs

A roof's **derived roof** is:

- its `kind` (16.2);
- its `outline`: the eave outline as a ring that starts at its least vertex (6.2) and runs
  counter-clockwise — reversed, when the footprint runs clockwise;
- its `eave` (16.3);
- its `surface`: `null` when its surface is not derived (16.4.4), and otherwise an object of:
  - `high`: the greatest elevation of the surface, rounded once — for a flat roof its eave, for a
    shed roof the greatest `z(V)` over the outline's vertices `V`, and for an equal-pitch roof the
    greatest `z` over its nodes;
  - `box`: `{ "min": [x₀, y₀, eave − thickness], "max": [x₁, y₁, high] }`, with `x₀`, `x₁`, `y₀` and
    `y₁` the least and greatest coordinates of the outline's vertices, and `thickness` the roof's,
    or `0` when it declares none;
  - `faces`: each face as `{ "edge", "polygon", "area" }` — `edge` the index of its sloped edge, and
    none for a flat roof's face; `polygon` its polygon (16.4) as points `[x, y, z]`, with `x` and
    `y` rounded once and `z` the exact elevation at the point rounded once, each point that equals
    the one before it removed (the first counts as following the last), starting at its least
    point — least `x`, then least `y`, then least `z`; and `area` its area in plan, computed from
    its rounded `x` and `y` as a room's net area is (6.4) — listed by `edge`, then by their first
    points, and leaving out a face whose rounded polygon has fewer than three points;
  - `gables`: each gable edge, from `A` to `B` on the counter-clockwise outline, as
    `{ "edge", "polygon" }`, where `polygon` is its **gable end**: `A` and then `B` at the eave, and
    then back from `B` to `A` along the surface through every node on the edge — for a shed roof,
    through `B` and `A` — each point `[x, y, z]` rounded as a face's are, each point that equals the
    one before it removed; listed by `edge`;
  - `lines`: each line (16.4.3) as `{ "kind", "from", "to" }`, its `kind` `"ridge"`, `"hip"` or
    `"valley"` and its ends as points `[x, y, z]` rounded as a face's are, `from` the lesser of the
    two — compared by `x`, then `y`, then `z`; listed by `from`, then `to`. A flat or shed roof has
    none.

A deriver MUST derive every roof as this section defines it. {#FS-CORE-16.5.1 MUST}

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
FLR-REQ-145 (a roof whose pitches the engine cannot derive is flagged, not failed), FLR-ADR-004
(exact integer geometry), FLR-ADR-027 (Core 0.3). Chapters 2 (pitch, polygons), 5 (corner points
and the top of walls), 15 (vaulted ceilings, whose exact form a shed roof shares) and Annex A
(`IfcRoof`).

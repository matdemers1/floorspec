# 5. Walls

Walls are authored on a graph. **Junctions** are its nodes — points on a level — and **walls**
and **room separators** are its edges, each running straight from one junction to another. The
graph is the single geometric truth of a level: wall corners are computed from it (this chapter),
rooms are its faces (chapter 6), and openings ride on its edges (chapter 7). A wall never stores
its own corners, and a room never stores its own outline (FLR-ADR-002).

## 5.1 Junctions

| Member | Type | Default | Meaning |
|---|---|---|---|
| `level` | reference to a level | — (always present) | the level the junction is on |
| `position` | point | — (always present) | where it is, in plan |
| `join` | join override (5.8) | `{ "kind": "mitre" }` | how walls meeting here are cut |
| `name`, `extensions`, `extras` | | | 1.4 |

Two junctions on the same level MUST NOT have the same position. {#FS-CORE-5.1.1 MUST NOT}

A junction that no wall or separator uses is permitted but serves no purpose; validators report
it as a lint (`FS-LINT-002`).

## 5.2 Walls and separators

A **wall** is a straight, solid wall with a thickness. A **room separator** is a boundary of zero
thickness that divides rooms without building anything — the line between an open kitchen and a
dining area. Together they are the level's **edges**.

**Wall.**

| Member | Type | Default | Meaning |
|---|---|---|---|
| `level` | reference to a level | — (always present) | the level the wall is on |
| `start` | reference to a junction | — (always present) | where the wall's location line starts |
| `end` | reference to a junction | — (always present) | where it ends |
| `type` | reference to a `wallType` | absent | the wall's type (8.3) |
| `layers` | array of layers (8.3) | from `type` | overrides the type's layers |
| `justification` | `"center"`, `"exteriorFace"`, `"interiorFace"` or `"coreFace"` | `"center"` | where the location line sits in the wall's thickness (5.4) |
| `base` | `{ "level"?: reference, "offset"?: length }` | `{}` | the wall's bottom (5.9) |
| `top` | `{ "level": reference, "offset"?: length }` or `{ "height": length }` | absent: follows the level's height (5.9) | the wall's top |
| `name`, `extensions`, `extras` | | | 1.4 |

**Separator.**

| Member | Type | Default | Meaning |
|---|---|---|---|
| `level` | reference to a level | — (always present) | the level the separator is on |
| `start` | reference to a junction | — (always present) | one end |
| `end` | reference to a junction | — (always present) | the other end |
| `name`, `extensions`, `extras` | | | 1.4 |

An edge's `start` and `end` MUST be different junctions. {#FS-CORE-5.2.1 MUST}

Two edges MUST NOT connect the same pair of junctions, in either order. {#FS-CORE-5.2.2 MUST NOT}

An edge's **location line** is the closed straight segment from its start junction's position to
its end junction's position. Its **direction** is from start to end; its **length** is the
Euclidean length of that segment, which is usually irrational and is never rounded.

## 5.3 Planarity

The edges of a level form a plane graph: they meet only at the junctions they share. This is what
makes rooms well defined and corners computable.

Two edges on the same level MUST NOT cross: their location lines MUST NOT meet in a single point that lies in the interior of both. {#FS-CORE-5.3.1 MUST NOT}

A junction MUST NOT lie in the interior of the location line of an edge on its level. {#FS-CORE-5.3.2 MUST NOT}
This includes a wall that ends against the middle of another wall: the "T" must have a junction
where the two meet, and the through wall is two edges.

The location lines of two edges on the same level MUST NOT overlap in a segment of positive length. {#FS-CORE-5.3.3 MUST NOT}

"Interior" here means the segment without its two endpoints. All three tests are exact: they use
integer arithmetic on junction positions, with no tolerance.

> [!note] Planarization
> An edit that would make walls cross does not have to be rejected: Floorspec Ops specifies that
> the editor first **planarizes** the level — it inserts a junction wherever two edges cross or an
> edge passes through a junction, and splits the edges there. Because an intersection rarely
> falls on a whole base unit, planarization uses snap rounding: every intersection point is
> rounded to the grid, and every edge passing through the unit square around a rounded point
> (a "hot pixel") is routed through it. Snap rounding moves no edge by more than one base unit,
> and produces the same result in every implementation. A file, by contrast, is simply invalid if
> it is not planar.

## 5.4 Thickness, sides and justification

A wall's **effective layers** are its `layers` if present, otherwise its type's `layers` (8.2).
Its **thickness** `T` is the sum of their thicknesses.

A wall MUST have effective layers. {#FS-CORE-5.4.1 MUST}

The **left** and **right** sides of a wall are as seen looking along its direction. The layers
are listed from the left face to the right face, and the left side is the wall's **exterior**:
draw the walls of an enclosure clockwise, seen from above, and their exterior sides face out.

`justification` places the location line within the thickness. It gives two **face offsets**:
`a`, the distance from the location line to the left face, and `b`, the distance to the right
face, with `a + b = T`.

| `justification` | The location line is on | `a` | `b` |
|---|---|---|---|
| `"center"` | the middle of the thickness | `T / 2` | `T / 2` |
| `"exteriorFace"` | the left (exterior) face | `0` | `T` |
| `"interiorFace"` | the right (interior) face | `T` | `0` |
| `"coreFace"` | the exterior face of the core | the thickness of the layers before the first `core` layer | `T − a` |

A wall justified `"coreFace"` MUST have at least one `core` layer, and its `core` layers MUST be consecutive. {#FS-CORE-5.4.2 MUST}

A separator has no thickness: both its face offsets are 0, and both its faces are its location
line.

## 5.5 Face lines

Corners are found by intersecting **face lines** — the infinite lines that carry an edge's two
faces. They are defined from the point of view of a junction `J` at one end of edge `e`:

- The **outgoing direction** is `d = (dx, dy)`, the position of `e`'s other junction minus the
  position of `J`. It is a vector of integers, never zero (5.1, 5.2).
- `|d| = √(dx² + dy²)`, and `n = (−dy, dx)` is `d` turned a quarter-turn counter-clockwise, so
  `n` points to the left of the outgoing direction and `|n| = |d|`.
- The **outgoing offsets** `(λ, ρ)` are the face offsets seen leaving `J`: `(a, b)` when `J` is
  `e`'s start, and `(b, a)` when `J` is its end — leaving from the end, the wall's left face is on
  the right.
- The **left face line** of `e` at `J` is `{ P : n · (P − J) = λ · |d| }`, and the **right face
  line** is `{ P : n · (P − J) = −ρ · |d| }`.

The **foot** of `J` on a face line is the point of the line nearest `J`: `J + λ · n / |d|` on the
left face line and `J − ρ · n / |d|` on the right.

Every face line is a line `A·x + B·y = C` with integer `A`, `B` and with `C = p + q·√(dx² + dy²)`
for rationals `p`, `q` with denominator 1 or 2. Every corner point below is therefore a pair of
numbers of the form `(α + β·√m + γ·√n) / δ` with integers `α, β, γ, δ, m, n`, which can be
compared and rounded exactly with integer arithmetic (2.2).

## 5.6 Wedges and corner points

At a junction `J` with incident edges, sort the edges by the angle of their outgoing direction,
measured counter-clockwise from +X in [0°, 360°). Call them `e₀, e₁, … e₍ₖ₋₁₎`; no two share an
angle, because two that did would overlap (5.3). The **wedge** `i` is the region swept
counter-clockwise from `e_i` to `e_(i+1)`, indices taken modulo `k`. With one edge, its only wedge
is the full turn from `e₀` back to itself.

Wedge `i` is bounded by the left face line of `e_i` and the right face line of `e_(i+1)`. Its
**corner sequence** — one or two points, listed from the `e_i` side to the `e_(i+1)` side — is:

- when the two face lines meet in exactly one point: that point;
- when they are parallel — because `k = 1`, or because `e_(i+1)` leaves `J` exactly opposite to
  `e_i` — the foot of `J` on the left face line of `e_i`, then the foot of `J` on the right face
  line of `e_(i+1)`; or just one of them if the two feet are the same point.

A deriver MUST compute every corner sequence as defined in this section. {#FS-CORE-5.6.1 MUST}

The two cases give the familiar shapes: two walls at an angle meet at a mitred corner, inside and
out; a wall with a free end is cut square; two collinear walls of equal offsets continue as one,
and of unequal offsets meet in a step.

## 5.7 Wall outlines and junction fills

A wall's **outline** in plan is the quadrilateral of its four **face ends**:

- `startRight` and `startLeft`, where its right and left faces end at its start junction;
- `endRight` and `endLeft`, where they end at its end junction.

Unless a join override (5.8) applies, the face ends are the corner points of the wedges either
side of the wall. At the start junction, where the wall is `e_i`: `startLeft` is the first point
of wedge `i`, and `startRight` is the last point of wedge `i − 1`. At the end junction, where the
wall is `e_j` and its own sides are reversed: `endRight` is the first point of wedge `j`, and
`endLeft` is the last point of wedge `j − 1`.

A deriver MUST derive each wall's four face ends as defined in this section and 5.8, rounded as 2.2 requires. {#FS-CORE-5.7.1 MUST}

The outline is the polygon `startRight → endRight → endLeft → startLeft`, after rounding and after
removing each vertex equal to the one before it (the first vertex counts as following the last).

A wall's outline MUST be a simple polygon with positive area and counter-clockwise orientation. {#FS-CORE-5.7.2 MUST}
A wall too short for the joins at its ends — a stub between two thick walls — fails this test;
its corners cross.

Where three or more edges meet at a junction with the default join, the walls' outlines leave a
gap around the junction. The **junction fill** closes it: the polygon of the corner sequences of
all of the junction's wedges, concatenated in wedge order, rounded, with each vertex equal to the
one before it removed (the first vertex counts as following the last).

A deriver MUST derive the junction fill of every junction with three or more edges and the default join. {#FS-CORE-5.7.3 MUST}

A junction fill with fewer than three vertices, or whose shoelace area is zero, is empty. A junction fill that is not empty MUST be a simple polygon with positive area and counter-clockwise orientation. {#FS-CORE-5.7.4 MUST}

The union of the outlines of a level's walls and its junction fills is the level's wall body: the
plan's solid poché.

## 5.8 Join overrides

The default join — the **mitre** — treats every wall at a junction alike. A junction can instead
name walls that run **through** it, with the others **butting** against them. The `join` member
is one of:

| `join` | Meaning |
|---|---|
| `{ "kind": "mitre" }` | the default join, as 5.7 |
| `{ "kind": "butt", "through": [W] }` | at a corner of two edges, wall `W` runs to the outer corner and the other edge stops against it |
| `{ "kind": "butt", "through": [W1, W2] }` | walls `W1` and `W2` continue straight through the junction, and every other edge stops against them |

A `join` MUST have exactly one of the three forms in this table: `kind` `"mitre"` and no other
member, or `kind` `"butt"` and a `through` array of one or two wall IDs. {#FS-CORE-5.8.5 MUST}

Every wall named in `through` MUST be one of the junction's edges. {#FS-CORE-5.8.1 MUST}
That it is a wall and not a separator is 3.2.1: `through` refers to the `walls` collection.

With one wall in `through`, the junction MUST have exactly two edges, and they MUST NOT be collinear. {#FS-CORE-5.8.2 MUST}

With two walls in `through`, the two MUST leave the junction in exactly opposite directions with
coincident face lines — the left face line of each is the right face line of the other — and at
most one other edge MAY lie on each side of the line they form. {#FS-CORE-5.8.3 MUST}

**One through wall `A` and one other edge `B`.** Of the two wedges, one is **convex** (less than
180°) and one is **reflex**. Let `c` be the corner point of the convex wedge, `r` the corner point
of the reflex wedge, and `p` the intersection of `A`'s face line on the convex side with `B`'s face
line on the reflex side. Then:

- `A`'s face on the reflex side ends at `r`, and its face on the convex side ends at `p`, so `A`
  runs out to the corner;
- `B`'s face on the convex side ends at `c`, and its face on the reflex side ends at `p`, so `B`
  stops against `A`.

**Two through walls.** Each through wall's faces end at the feet of `J` on them, so the two walls'
outlines share a square cut through `J` and read as one wall. Every other edge's face ends are as
5.7 defines them; both lie on the through walls' faces.

A junction with a butt join has no junction fill.

A deriver MUST apply a junction's butt join as defined in this section. {#FS-CORE-5.8.4 MUST}

A join override changes how a wall body is divided between walls, never its outline as a whole:
the corner points of every wedge are the same, and the rooms (chapter 6) are identical under any
join.

## 5.9 Vertical extent

A wall rises from its **base elevation** to its **top elevation**:

- **Base.** `base.level` (default: the wall's own level) and `base.offset` (default `0`). The base
  elevation is that level's `elevation` plus the offset.
- **Top, level-constrained.** `top: { "level": L, "offset": o }` — the top is level `L`'s
  elevation plus `o` (default `0`).
- **Top, unconnected.** `top: { "height": h }` — the top is the base elevation plus `h`.
- **Top, absent.** The top follows the wall's own level: that level's elevation plus its `height`.
  This default is derived: change the level's height and every wall that omits `top` follows it.

`top` MUST have either `level` or `height`, and MUST NOT have both; `offset` MUST NOT appear with `height`. {#FS-CORE-5.9.1 MUST}

A wall's top elevation MUST be greater than its base elevation. {#FS-CORE-5.9.2 MUST}

A deriver MUST derive each wall's base and top elevations as defined in this section. {#FS-CORE-5.9.3 MUST}

## 5.10 Lints

These conditions make a document worse, not invalid. A validator SHOULD report them with the
codes of chapter 10. {#FS-CORE-5.10.1 SHOULD}

- **Acute join** (`FS-LINT-001`): two consecutive edges at a junction are both walls and the wedge
  between them is less than 30°. Its mitre runs far out to a point. The exact test, for outgoing
  directions `d₁`, `d₂` of a wedge narrower than 180°: `d₁ · d₂ > 0` and
  `4 (d₁ · d₂)² > 3 |d₁|² |d₂|²`.
- **Unused junction** (`FS-LINT-002`): a junction that no edge uses.

# 17. Stairs

A stair joins two levels of a building. What a document stores is what a designer decides — where
the stair starts and which way it rises, how wide it is, how deep its treads are, how many risers it
has or how tall they may be, its form — a straight run, an L or a U with a landing at the turn,
a stair that turns on winders, or a spiral — and the headroom it is designed for. What a conformant
tool derives is everything that follows from those and from the floors at either end: the rise,
the riser count and height, the steps, the run, the walkline, the goings of tapered treads, the
headroom and the opening the stair needs in the floor above. Change a level's elevation, or sink
the floor at the stair's foot, and the risers follow (FLR-ADR-002).

This draft defines the data of all five forms and derives the steps of every one: the flights and
landings of a straight, L-shaped or U-shaped stair (17.5), and the tapered treads of a winder or a
spiral stair (17.7). Every value is exact and rounded once (2.2).

## 17.1 The stair

A stair is an element of the `stairs` collection (1.1).

| Member | Type | Default | Meaning |
|---|---|---|---|
| `level` | reference to a level | — (always present) | the level the stair rises from: its **foot** is on this level |
| `to` | reference to a level | — (always present) | the level the stair rises to: its **head** is on this level |
| `position` | point | — (always present) | the middle of the stair's first nosing line, in plan: where the first tread's front edge is |
| `rotation` | angle | `0` | the direction the first flight rises in, counter-clockwise from +X; in (−180,000,000, 180,000,000] |
| `width` | length | — (always present) | the stair's width, at right angles to the direction it rises in |
| `tread` | length | — (always present) | the **going**: the horizontal distance from one nosing to the next, measured along the walkline |
| `risers` | count | absent: derived from `maxRiser` | the number of risers, from the foot to the head |
| `maxRiser` | length | absent: the stair has `risers` | the greatest riser height the stair may have: its riser count is the least that keeps every riser no higher than this (17.4) |
| `minHeadroom` | length | absent: no headroom is declared | the least headroom the stair is designed to have: what the opening it needs in the floor above is cut for (17.6); new in 0.4 |
| `form` | form (17.2) | `{ "kind": "straight" }` | the stair's form |
| `handrail` | `{ "height": length, "sides"?: "left", "right" or "both" }` | absent: no handrail is declared | the handrail's height above the nosing line, and the sides it is on — as walked up; `sides` defaults to `"both"` |
| `name`, `extensions`, `extras` | | | 1.4 |

A nosing line is the front edge of a tread, or of a landing or the floor at the head, where a riser
below it meets it. A stair's nosing lines are what its treads are measured between; this draft does
not describe a nosing's projection or a riser's construction.

A stair MUST have exactly the members of its table, each of the type its table gives: `width`, `tread` and `maxRiser` MUST be greater than zero, `risers` MUST be an integer from 1 to 2⁵³ − 1, `rotation` MUST lie in (−180,000,000, 180,000,000], a handrail's `height` MUST be greater than zero, and a stair MUST have exactly one of `risers` and `maxRiser`. {#FS-CORE-17.1.1 MUST}

A stair's `to` MUST be a level of the building its `level` is in, and MUST NOT be its `level`. {#FS-CORE-17.1.2 MUST}

A stair's `minHeadroom` MUST be greater than zero. {#FS-CORE-17.1.3 MUST}

## 17.2 Forms

A stair's `form` is one of five:

| `form` | The stair |
|---|---|
| `{ "kind": "straight" }` | one flight |
| `{ "kind": "lShaped", "turn": "left" or "right", "risersBeforeTurn": count }` | two flights at right angles, joined by a square landing as wide as the stair |
| `{ "kind": "uShaped", "turn": "left" or "right", "risersBeforeTurn": count, "gap"?: length }` | two parallel flights that rise in opposite directions, `gap` apart, joined by a landing across both |
| `{ "kind": "winder", "turn": "left" or "right", "angle": "quarter" or "half", "risersBeforeTurn": count, "winders": count, "gap"?: length, "newel"?: length }` | an L (`"quarter"`) or a U (`"half"`, with its `gap`) that turns on `winders` winder treads instead of a landing, around a `newel` when it has one (17.7) |
| `{ "kind": "spiral", "turn": "left" or "right", "diameter": length, "sweep": angle }` | treads that wind around a centre: the stair's outer `diameter`, and the angle, in microdegrees, it turns through from its first nosing line to its last |

`turn` is the way the stair turns as it is walked up: `"left"` is counter-clockwise seen from above.
`risersBeforeTurn` is the number of risers of the first flight: the last of them rises onto the
landing, or onto the first winder. `gap` defaults to `0`, and only a U-shaped stair or a half-turn
winder stair has one. `newel`, new in 0.4, is the depth of the newel — a post, or a short wall —
at the inner side of a winder stair's turn, on whose faces its winders' narrow ends stand (17.7);
it has no default: a winder stair without one has none, and its winders meet at a point.

A stair's `form` MUST have exactly the members of one of the five forms, each of the type its table gives: `risersBeforeTurn` and `winders` MUST be integers from 1 to 2⁵³ − 1, `gap` MUST NOT be negative, `diameter` MUST be greater than zero, `sweep` MUST be an integer from 1 to 2⁵³ − 1, and a quarter-turn winder stair MUST NOT have a `gap`. {#FS-CORE-17.2.1 MUST}

A spiral stair's `width` MUST NOT be more than half its `diameter`. {#FS-CORE-17.2.2 MUST NOT}

A winder stair's `newel` MUST be greater than zero, and only a winder stair's form MUST have one. {#FS-CORE-17.2.3 MUST}

## 17.3 The layout

A stair is laid out in its **frame** (13.1): its origin is `position`, its facing vector is
`F(rotation)`, so its local x axis — **along** — points the way the first flight rises and its local
y axis — **across** — to its left. Every point of this section is given by its local coordinates
`(p, q)` and is the plan point `position + p·u + q·v` of 13.1, exact, and rounded once where it is
output. Let `n` be the stair's riser count (17.4), `t` its `tread`, `w` its `width`, `m` its
`risersBeforeTurn`, `g` its `gap`, and `P = (m − 1)·t`.

A **flight** is a straight run of `r` risers. It has a first nosing line, whose middle is the
flight's start `C`, a direction `e` — one of the local axes — and its left `l`, `e` turned a quarter
turn counter-clockwise. Its nosing lines are at `C + (k − 1)·t·e`, for `k` from 1 to `r`, each
running from `−w/2` to `w/2` along `l`; the last is the front edge of the landing or the floor it
rises onto. Between nosing lines `k` and `k + 1` is its tread `k`, the rectangle
`{ C + a·e + b·l : (k − 1)·t ≤ a ≤ k·t, −w/2 ≤ b ≤ w/2 }`, so a flight of `r` risers has `r − 1`
treads and is `(r − 1)·t` long.

For a stair that turns `"left"`:

| Form | Pieces, in the order they are walked up | Head |
|---|---|---|
| straight | a flight of `n` risers from `(0, 0)`, along +x | `((n − 1)·t, 0)` |
| L-shaped | a flight of `m` risers from `(0, 0)` along +x; the landing `P ≤ p ≤ P + w`, `−w/2 ≤ q ≤ w/2`; a flight of `n − m` risers from `(P + w/2, w/2)` along +y | `(P + w/2, w/2 + (n − m − 1)·t)` |
| U-shaped | a flight of `m` risers from `(0, 0)` along +x; the landing `P ≤ p ≤ P + w`, `−w/2 ≤ q ≤ 3w/2 + g`; a flight of `n − m` risers from `(P, w + g)` along −x | `(P − (n − m − 1)·t, w + g)` |
| winder, `"quarter"` | the rectangles `0 ≤ p ≤ P`, `−w/2 ≤ q ≤ w/2`; `P ≤ p ≤ P + w`, `−w/2 ≤ q ≤ w/2` (the winders); and `P ≤ p ≤ P + w`, `w/2 ≤ q ≤ w/2 + s` | `(P + w/2, w/2 + s)` |
| winder, `"half"` | the rectangles `0 ≤ p ≤ P`, `−w/2 ≤ q ≤ w/2`; `P ≤ p ≤ P + w`, `−w/2 ≤ q ≤ 3w/2 + g` (the winders); and `P − s ≤ p ≤ P`, `w/2 + g ≤ q ≤ 3w/2 + g` | `(P − s, w + g)` |

where, for a winder stair, `s = (n − m − winders)·t`, the length of the straight treads after the
turn; a rectangle with no area is not one of its pieces. A stair that turns `"right"` is the mirror
image: every `q` above is `−q`.

A spiral stair's **centre** is `(0, c)` with `c = diameter/2 − w/2`, the radius of its walkline, for
a `"left"` turn, and `(0, −c)` for a `"right"` one. Its head is the point at distance `c` from its
centre in the direction `F(φ)` (13.1), where `φ` is `rotation − 90,000,000 + sweep` for a `"left"`
turn and `rotation + 90,000,000 − sweep` for a `"right"` one, taken in (−180,000,000, 180,000,000]:
the first nosing line's middle turned about the centre through the sweep.

The **foot** of a stair is its `position`; its **head** is the head of this section, rounded once.

## 17.4 Foot, head, rise and risers

A plan point is **in** a room when it is inside or on the outer ring of the room's room polygon
(6.2) and not strictly inside one of its holes. The stair's **foot room** is the room on its `level`
that its foot is in, and its **head room** the room on its `to` level that its head is in — in
either case the first by ID, compared as 10.2 compares IDs, when the point is in more than one, and
none when it is in none.

- Its **bottom** is the top of the foot room's floor (15.1), or the elevation of its `level` when it
  has no foot room.
- Its **top** is the top of the head room's floor, or the elevation of its `to` level when it has no
  head room.
- Its **rise** is its top minus its bottom.

Its **riser count** `n` is its `risers`, when it has them. Otherwise it is the least `n ≥ 1` for
which the stair laid out with `n` risers (17.3) has a rise no greater than `n · maxRiser` — the head,
and so the head room and the top, depend on `n`, and are taken for each `n` tried. Its **riser
height** is its rise divided by `n`, exactly; riser `k` rises from `bottom + (k − 1)·rise/n` to
`bottom + k·rise/n`, and the tops of the treads, landings and the head are at those elevations.

A stair's rise MUST be greater than zero. {#FS-CORE-17.4.1 MUST}

A stair's riser count MUST fit its form: at least 2 for a straight or a spiral stair; for an L-shaped or a U-shaped stair, `risersBeforeTurn` at least 2 and the riser count at least `risersBeforeTurn + 2`, so that each flight has a tread; and for a winder stair, at least `risersBeforeTurn + winders`. {#FS-CORE-17.4.2 MUST}

For every stair a deriver derives:

- `risers`, its riser count, and `riserHeight`, its riser height rounded once;
- `rise`, `bottom` and `top`;
- `foot` and `head`, as plan points, and `footRoom` and `headRoom`, present only when the stair has
  them;
- its **box**: `{ "min": [x₀, y₀, bottom], "max": [x₁, y₁, top] }`, where `x₀`, `x₁`, `y₀` and `y₁`
  are the least and greatest coordinates, each rounded once, of the corners of its steps (17.5) for
  a straight, L-shaped or U-shaped stair; of the corners of the rectangles of 17.3 for a winder
  stair; and of the circle of its `diameter` about its centre — its centre's coordinates plus and
  minus half the diameter — for a spiral stair.

The exact riser height is the rise divided by the riser count, both of which are output; only
`riserHeight` is rounded.

A deriver MUST derive these values for every stair of a valid document, as this section and 17.3 define them. {#FS-CORE-17.4.3 MUST}

## 17.5 Steps, run and walkline

For a straight, L-shaped or U-shaped stair a deriver also derives:

- `steps`: every tread and landing, in the order they are walked up, each as `{ "outline": ring,
  "top": elevation }` — its rectangle's four corners, rounded, as a ring that starts at its least
  vertex and runs counter-clockwise (6.2), and the elevation of its top, rounded once — with
  `"landing": true` on a landing. A tread is the top of the riser below it; a landing, of the last
  riser of the first flight;
- `run`: the number of treads times `t` — the horizontal length of the treads, without the landing;
- `walkline`: its `points`, rounded — the foot; for an L-shaped stair, the landing's middle
  `(P + w/2, 0)`; for a U-shaped one, `(P + w/2, 0)` and `(P + w/2, w + g)`; and the head — and its
  `length`, the length of the path through them in local coordinates: `(n − 1)·t` for a straight
  stair, `(n − 2)·t + w` for an L-shaped one and `(n − 2)·t + 2w + g` for a U-shaped one, each an
  integer.

A deriver MUST derive the steps, the run and the walkline of every straight, L-shaped and U-shaped stair of a valid document as this section defines them. {#FS-CORE-17.5.1 MUST}

A winder or a spiral stair has steps, a run and a walkline too, defined in 17.7.

## 17.6 Headroom

**Headroom** is the least height a person climbing the stair has above the line they walk on. It is
measured above **lanes**: the two sides and the middle line of every flight, from its first nosing
line to its last — `C + a·e + b·l` for `0 ≤ a ≤ (r − 1)·t` and `b` one of `w/2`, `0` and `−w/2` —
and the four edges and the two lines joining the middles of opposite edges of every landing; and,
for a winder or a spiral stair, the edges of the outline of every tapered tread (17.7) and its
**walkline chord**, from where the walkline crosses the nosing line at its front to where it
crosses the one at its back. Each lane is the plan segment between its two ends' points, rounded (17.3, 17.7). A flight's
lanes rise straight from the top of its first riser at their first end to the top of its last at
their second — the nosing line; a landing's, and a tapered tread's, are level at its top.

What is above a plan point `X` of a lane — one that is on no edge of a room polygon, of a tray's
centre (15.4) or of a well, and on the ridge line of no two-sided vault (15.3) — is:

- the ceiling of a room on the stair's `level` that `X` is strictly inside — inside its room
  polygon's outer ring and outside every hole — unless `X` is in the stair's **well**: inside or on
  a bounded face of the `to` level that no room is anchored in and whose room polygon is not
  degenerate (6.1, 6.6), the opening the stair rises through;
- the bottom of the floor (15.1) and the ceiling of a room on the `to` level that `X` is strictly
  inside.

A ceiling is at its elevation at `X` (15.2). The **clearance** at `X` is the least of the elevations
of what is above it, minus the elevation of the lane at `X`; a point with nothing above it has
none. Along a lane, what is above changes only where the lane crosses or touches one of those edges
or ridge lines — of the rooms of the stair's two levels, and the wells of its `to` level — and
between those places each elevation is linear. The stair's headroom is the infimum of the clearance
over every point of every lane that has one: the least, over the pieces between those places that
have something above them, of the clearance at each end of the piece, taken as the limit from
inside the piece. It is exact, and rounded once. A stair with nothing above any of its lanes has no
headroom.

A floor reaches up to its top and down to its bottom, and its room polygon stops where the walls
around it do, so a stair rising through an opening drawn on the upper level — a face bounded by
walls or by separators that stand for a railing, with no room in it — has the floor above it only
where the opening ends. The ceilings of other levels, the structure between a ceiling and the floor
above (0.5) and slabs are not obstacles in this draft.

A deriver MUST derive the headroom of every straight, L-shaped and U-shaped stair of a valid document that has one, as `headroom`, exactly as this section defines it, and no `headroom` member for one that has none. {#FS-CORE-17.6.1 MUST}

A deriver MUST derive the headroom of every winder and spiral stair of a valid document that has one, as `headroom`, exactly as this section defines it over the lanes of its flights and its tapered treads, and no `headroom` member for one that has none. {#FS-CORE-17.6.2 MUST}

**The opening a stair needs.** A stair that declares its `minHeadroom` is designed to have that much
headroom, and the floor of its `to` level must be open over it wherever the floor would come closer.
Let `B` be the bottom of the floor at the stair's head: its top (17.4) minus the thickness of its head
room's floor (15.1) — or, when it has no head room, its `to` level's `floorThickness`, and `0` when
that declares none. A step **needs the opening** when its top, exact, is more than `B − minHeadroom`:
someone standing on it would have less than `minHeadroom` under that floor. A step's top rises with
every step walked up, so the steps that need the opening are the last ones, and a deriver derives
`opening` as `{ "first": i }`, where `i` is the index in `steps` (17.5, 17.7), counting from 0, of
the first step that needs it. The opening is the plan region that step's outline and every later
step's cover; it is the well the floor above should have. A spiral stair's opening is often most of
the circle its box (17.4) bounds.

A deriver MUST derive `opening` for every stair of a valid document that has a `minHeadroom` and a step that needs the opening, exactly as this section defines it, and no `opening` member for any other stair. {#FS-CORE-17.6.3 MUST}

A validator SHOULD report `FS-LINT-019` (warning) for a stair whose headroom, exact, is less than its `minHeadroom`: the floor above has not been opened as the stair needs. {#FS-CORE-17.6.4 SHOULD}

## 17.7 Winder and spiral stairs

A winder stair turns on **tapered treads** — winders — instead of a landing, and every tread of a
spiral stair is tapered. A tapered tread is bounded by two nosing lines that are not parallel: each
lies on a ray from one point, so the tread is deep at its outer end and narrow at its inner end.
This section defines, exactly, where those rays point, the treads between them, the walkline that
crosses them, and how deep each tread is on the walkline and at its narrow end. Angles are divided
into equal parts each rounded to a whole microdegree, and every direction is a facing vector `F` of
such an angle (13.1), a vector of integers: so every point below is exact, and is rounded once
where it is output (2.2).

### The turn of a winder stair

For a winder stair that turns `"left"`, in the local coordinates of 17.3 — a stair that turns
`"right"` is the mirror image, every `q` below `−q`, as there — with `w` its width, `t` its tread,
`m` its `risersBeforeTurn`, `g` its `gap` (`0` for a quarter turn), `a` its `newel` (`0` when it has
none), `P = (m − 1)·t` and `W` its `winders`:

- its **turn** is the rectangle of 17.3 its winders occupy, `T`: `P ≤ p ≤ P + w`,
  `−w/2 ≤ q ≤ h`, where `h` is `w/2` for a quarter turn and `3w/2 + g` for a half;
- its **pivot** `O` is `(P, w/2)` for a quarter turn — the inner corner, where the inner sides of
  its two flights meet — and `(P, w/2 + g/2)` for a half: the middle of the side of the turn that
  faces the gap;
- its **newel**, when it has one, is the rectangle `N`: `P ≤ p ≤ P + a`, `w/2 − a ≤ q ≤ k`, where
  `k` is `w/2` for a quarter turn and `w/2 + g + a` for a half — the part of the turn within `a` of
  its inner side. A turn without a newel has none;
- its angle `A` is 90,000,000 for a quarter turn and 180,000,000 for a half, and its **rays** are,
  for `j` from 0 to `W`, the half-lines from `O` in the local directions `dⱼ = F(βⱼ)`, where
  `βⱼ = −90,000,000 + round(j·A / W)`: ray 0 points along `−q`, down the first flight's last nosing
  line, ray `W` along the second flight's first, and the rays between divide the turn into `W` equal
  angles, each end rounded to a microdegree.

**Nosing line `j`** of the turn is the part of ray `j` from where it leaves `N` — its **inner end**
`Iⱼ`, which is `O` when there is no newel — to where it leaves `T`, its **outer end** `Eⱼ`. Nosing
line 0 lies on the first flight's last nosing line, and nosing line `W` on the second flight's first;
each is shortened by the newel. A ray from `O` leaves an axis-aligned rectangle that `O` is on at a
rational point, because `dⱼ` is a vector of integers.

**Winder `j`**, for `j` from 1 to `W`, is the polygon bounded by nosing lines `j − 1` and `j`, the
sides of `T` between their outer ends and the sides of `N` between their inner ends. Its vertices
are, in order, `Iⱼ₋₁`, `Eⱼ₋₁`, each corner of `T` strictly between rays `j − 1` and `j`, `Eⱼ`, `Iⱼ`,
and each corner of `N` strictly between them, in reverse — a corner `C` is strictly between them when
`dⱼ₋₁ × (C − O) > 0` and `(C − O) × dⱼ > 0` — with a vertex that repeats the one before it written
once. Winder `j` is the top of riser `m + j − 1`: riser `m`, the last of the first flight, rises onto
winder 1, and riser `m + W` onto the second flight's first tread, or onto the floor at the head.

The **walkline** through the turn is the arc of radius `r = (w + g)/2` about `O`, from the first
flight's middle line to the second's: it is the middle of the stair, as the walkline of an L or a U
is (17.5), turned round the pivot. It crosses nosing line `j` at `Xⱼ = O + r·dⱼ / |dⱼ|`. Winder `j`'s
**going at the walkline** is the distance from `Xⱼ₋₁` to `Xⱼ`, and its **going at the narrow end**
the distance from `Iⱼ₋₁` to `Iⱼ` — 0 when the turn has no newel.

A winder stair's newel MUST lie inside the circle of its walkline — `(2a)² + (2a + g)² < (w + g)²` — and a half-turn winder stair's `gap` MUST NOT be greater than its `width`. {#FS-CORE-17.7.4 MUST}

So the walkline crosses every nosing line between its inner and its outer end: the newel's farthest
corner is nearer the pivot than the walkline, and the turn's nearest side is no nearer.

### The treads of a spiral stair

For a spiral stair with `n` risers, centre `C` (17.3) and `diameter` `D`, let `R = D/2`,
`rᵢ = D/2 − w` — the radius of its **column**, the space its treads leave at its centre, 0 when its
width is half its diameter — and `r꜀ = D/2 − w/2`, the radius of its walkline (17.3). Its nosing line
`k`, for `k` from 1 to `n`, lies on the ray from `C` in the plan direction `uₖ = F(φₖ)`, where `φₖ`
is `rotation − 90,000,000 + round((k − 1)·sweep / (n − 1))` for a `"left"` turn and
`rotation + 90,000,000 − round((k − 1)·sweep / (n − 1))` for a `"right"` one, taken in
(−180,000,000, 180,000,000]: it runs from `C + rᵢ·uₖ/|uₖ|`, its inner end, to `C + R·uₖ/|uₖ|`, its
outer end. Its middle `Wₖ = C + r꜀·uₖ/|uₖ|` is on the walkline; `W₁` is the stair's foot and `Wₙ` its
head (17.3).

Tread `k`, for `k` from 1 to `n − 1`, is the quadrilateral of the inner and outer ends of nosing
lines `k` and `k + 1` — the triangle of `C` and their outer ends when `rᵢ` is 0 — and the top of
riser `k`. Its sides are straight: its outer side is the chord, not the arc, of the stair's circle
between its nosing lines; a renderer may draw the arc, which the outline stands for. Its **going at
the walkline** is the distance from `Wₖ` to `Wₖ₊₁`, and its **going at the narrow end** the distance
between the inner ends of its nosing lines.

Every winder of a winder stair MUST turn through an angle greater than zero, and every tread of a spiral stair through an angle greater than zero and less than 180,000,000: `round(j·A/W) − round((j − 1)·A/W) > 0` for every `j` from 1 to `W`, which holds exactly when `W ≤ A`, and `0 < round(k·sweep/(n − 1)) − round((k − 1)·sweep/(n − 1)) < 180,000,000` for every `k` from 1 to `n − 1`. {#FS-CORE-17.7.5 MUST}

### What a deriver derives

For a winder or a spiral stair a deriver derives, besides the values of 17.4:

- `steps`: every tread, in the order they are walked up, each as `{ "outline": ring, "top":
  elevation }` — its exact vertices rounded once, with a point equal to the one before it written
  once, as a ring that starts at its least vertex and runs counter-clockwise (6.2), and the elevation
  of its top rounded once (17.4). For a winder stair: the treads of its first flight (17.3), its
  winders, each marked `"winder": true`, and the treads of its second flight; for a spiral stair, its
  treads. A winder or a spiral stair has no landing;
- `walkline`: its `points`, rounded, a point equal to the one before it written once — for a winder
  stair its foot, `X₀` to `X_W` and its head; for a spiral stair `W₁` to `Wₙ` — and its `length`: for
  a winder stair `P + s + π·r·A / 180,000,000`, its two straight parts — `s` the length of the
  straight treads after the turn (17.3) — and its arc; for a spiral stair `π·r꜀·sweep / 180,000,000`. The
  length is exact and rounded once; it is never a tie, because π is transcendental;
- `run`: the walkline's length — a tapered stair has no landing for the run to leave out;
- `walklineGoing` and `narrowGoing`: the least going at the walkline, and the least going at the
  narrow end, of its winders, or of the spiral's treads — each the least exact distance, rounded
  once. A winder stair's straight treads are `tread` deep wherever they are measured, so these are
  the goings of its tapered treads;
- for a spiral stair, `centre`: its centre, rounded.

A deriver MUST derive the steps, run, walkline, walklineGoing and narrowGoing of every winder and spiral stair of a valid document, and the centre of every spiral stair, exactly as this section defines them. {#FS-CORE-17.7.3 MUST}

Every going is exact. The square of a distance between two points of a nosing line's ends is
rational; between two points on a walkline it is `r²·(2 − 2·(d · d′) / √(|d|²·|d′|²))`, one radicand.
A deriver rounds its square root by comparing the square with `(k + ½)²` for the integers `k`
either side of it, exactly; a tie, which only a rational square can make, goes to the even integer
(0.3).

A stair's `tread` is its going at its walkline (17.1). For a winder stair it is the going of the
straight treads of its flights; its winders' going there follows from the turn and is
`walklineGoing`. For a spiral stair, whose every going follows from its `diameter`, `width`, `sweep`
and riser count, `tread` is the going its designer intends at the walkline, and nothing is derived
from it: `walklineGoing` is what the stair has.

A validator SHOULD report `FS-LINT-018` (warning) for each winder stair without a newel and each spiral stair whose width is half its diameter: their tapered treads narrow to a point, and their `narrowGoing` is 0. {#FS-CORE-17.7.6 SHOULD}

Core 0.3 defined the data of winder and spiral stairs and derived only their foot, head, rise, risers
and box; it forbade deriving their steps (`FS-CORE-17.7.1`) and reported `FS-LINT-016` for each. Both
statements are retired (0.6): a reader of 0.4 derives what this section defines for a document of
any draft.

## 17.8 Circulation

A stair joins its foot room and its head room in its building's door graph (14.1), and replaces
there the stand-in by which rooms of function `circulation` on different levels were joined.

## 17.9 Related

FLR-REQ-110 (parametric straight, L, U, winder and spiral stairs, each with derived riser count,
rise, run and headroom), FLR-REQ-111 (straight, L and U stairs derived with landings), FLR-REQ-146
(winder and spiral stairs derived), FLR-REQ-170 (the dimensional rules of winder and spiral stairs,
which read the goings of 17.7 — Floorspec Rules 8.5), FLR-ADR-002
(derived, not drawn), FLR-ADR-004 (exact integer geometry), FLR-ADR-024 (circulation, whose stand-in
for stairs this chapter replaces), FLR-ADR-027 (floors and ceilings, which a stair's rise and
headroom are measured from). Chapters 13 (frames), 14 (circulation), 15 (floors and ceilings) and
Annex A (`IfcStair`, `IfcStairFlight`, `IfcSlab` `LANDING`, `IfcRailing`).

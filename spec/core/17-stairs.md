# 17. Stairs

A stair joins two levels of a building. What a document stores is what a designer decides — where
the stair starts and which way it rises, how wide it is, how deep its treads are, how many risers it
has or how tall they may be, and its form: a straight run, an L or a U with a landing at the turn,
a stair that turns on winders, or a spiral. What a conformant tool derives is everything that
follows from those and from the floors at either end: the rise, the riser count and height, the
steps, the run, the walkline and the headroom. Change a level's elevation, or sink the floor at the
stair's foot, and the risers follow (FLR-ADR-002).

This draft defines the data of all five forms. It derives the steps of a straight, L-shaped or
U-shaped stair; of a winder or a spiral stair it derives the rise, the risers and the box that
bounds it, and says that its steps are not derived (17.7). Every value is exact and rounded once
(2.2).

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
| `form` | form (17.2) | `{ "kind": "straight" }` | the stair's form |
| `handrail` | `{ "height": length, "sides"?: "left", "right" or "both" }` | absent: no handrail is declared | the handrail's height above the nosing line, and the sides it is on — as walked up; `sides` defaults to `"both"` |
| `name`, `extensions`, `extras` | | | 1.4 |

A nosing line is the front edge of a tread, or of a landing or the floor at the head, where a riser
below it meets it. A stair's nosing lines are what its treads are measured between; this draft does
not describe a nosing's projection or a riser's construction.

A stair MUST have exactly the members of its table, each of the type its table gives: `width`, `tread` and `maxRiser` MUST be greater than zero, `risers` MUST be an integer from 1 to 2⁵³ − 1, `rotation` MUST lie in (−180,000,000, 180,000,000], a handrail's `height` MUST be greater than zero, and a stair MUST have exactly one of `risers` and `maxRiser`. {#FS-CORE-17.1.1 MUST}

A stair's `to` MUST be a level of the building its `level` is in, and MUST NOT be its `level`. {#FS-CORE-17.1.2 MUST}

## 17.2 Forms

A stair's `form` is one of five:

| `form` | The stair |
|---|---|
| `{ "kind": "straight" }` | one flight |
| `{ "kind": "lShaped", "turn": "left" or "right", "risersBeforeTurn": count }` | two flights at right angles, joined by a square landing as wide as the stair |
| `{ "kind": "uShaped", "turn": "left" or "right", "risersBeforeTurn": count, "gap"?: length }` | two parallel flights that rise in opposite directions, `gap` apart, joined by a landing across both |
| `{ "kind": "winder", "turn": "left" or "right", "angle": "quarter" or "half", "risersBeforeTurn": count, "winders": count, "gap"?: length }` | an L (`"quarter"`) or a U (`"half"`, with its `gap`) that turns on `winders` winder treads instead of a landing |
| `{ "kind": "spiral", "turn": "left" or "right", "diameter": length, "sweep": angle }` | treads that wind around a centre: the stair's outer `diameter`, and the angle, in microdegrees, it turns through from its first nosing line to its last |

`turn` is the way the stair turns as it is walked up: `"left"` is counter-clockwise seen from above.
`risersBeforeTurn` is the number of risers of the first flight: the last of them rises onto the
landing, or onto the first winder. `gap` defaults to `0`, and only a U-shaped stair or a half-turn
winder stair has one.

A stair's `form` MUST have exactly the members of one of the five forms, each of the type its table gives: `risersBeforeTurn` and `winders` MUST be integers from 1 to 2⁵³ − 1, `gap` MUST NOT be negative, `diameter` MUST be greater than zero, `sweep` MUST be an integer from 1 to 2⁵³ − 1, and a quarter-turn winder stair MUST NOT have a `gap`. {#FS-CORE-17.2.1 MUST}

A spiral stair's `width` MUST NOT be more than half its `diameter`. {#FS-CORE-17.2.2 MUST NOT}

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

## 17.6 Headroom

**Headroom** is the least height a person climbing the stair has above the line they walk on. It is
measured above **lanes**: the two sides and the middle line of every flight, from its first nosing
line to its last — `C + a·e + b·l` for `0 ≤ a ≤ (r − 1)·t` and `b` one of `w/2`, `0` and `−w/2` —
and the four edges and the two lines joining the middles of opposite edges of every landing. Each
lane is the plan segment between its two ends' points, rounded (17.3). A flight's lanes rise
straight from the top of its first riser at their first end to the top of its last at their second —
the nosing line; a landing's are level at its top.

What is above a plan point `X` of a lane, when `X` is not on the boundary of any of these regions:

- the ceiling of a room on the stair's `level` that `X` is strictly inside — inside its room
  polygon's outer ring and outside every hole — unless `X` is in the stair's **well**: inside or on
  a bounded face of the `to` level that no room is anchored in and whose room polygon is not
  degenerate (6.1, 6.6), the opening the stair rises through;
- the bottom of the floor (15.1) and the ceiling of a room on the `to` level that `X` is strictly
  inside.

A ceiling is at its elevation at `X` (15.2). The **clearance** at `X` is the least of the elevations
of what is above it, minus the elevation of the lane at `X`; a point with nothing above it has
none. Along a lane, what is above changes only where the lane crosses or touches an edge of a room
polygon of a room on either level, of a tray's centre (15.4), of such a face, or the ridge line of
a two-sided vault (15.3), and between those places each elevation is linear. The stair's headroom
is the infimum of the clearance over every point of every lane that has one: the least, over the
pieces between those places that have something above them, of the clearance at each end of the
piece, taken as the limit from inside the piece. It is exact, and rounded once. A stair with nothing
above any of its lanes has no headroom.

A floor reaches up to its top and down to its bottom, and its room polygon stops where the walls
around it do, so a stair rising through an opening drawn on the upper level — a face bounded by
walls or by separators that stand for a railing, with no room in it — has the floor above it only
where the opening ends. The ceilings of other levels, the structure between a ceiling and the floor
above (0.5) and slabs are not obstacles in this draft.

A deriver MUST derive the headroom of every straight, L-shaped and U-shaped stair of a valid document that has one, as `headroom`, exactly as this section defines it, and no `headroom` member for one that has none. {#FS-CORE-17.6.1 MUST}

## 17.7 Winder and spiral stairs

This draft defines the data of a winder stair and of a spiral stair, and derives their foot, head,
rise, risers and box (17.4). It does not derive their steps, run, walkline or headroom: a winder's
treads taper, and their outlines, and what is above them, need a definition of their own.

A deriver MUST NOT derive `steps`, `run`, `walkline` or `headroom` for a winder or a spiral stair. {#FS-CORE-17.7.1 MUST NOT}

A validator SHOULD report `FS-LINT-901` (info) for each winder and each spiral stair. {#FS-CORE-17.7.2 SHOULD}

## 17.8 Circulation

A stair joins its foot room and its head room in its building's door graph (14.1), and replaces
there the stand-in by which rooms of function `circulation` on different levels were joined.

## 17.9 Related

FLR-REQ-110 (parametric straight, L, U, winder and spiral stairs, each with derived riser count,
rise, run and headroom), FLR-REQ-111 (straight, L and U stairs derived with landings), FLR-ADR-002
(derived, not drawn), FLR-ADR-004 (exact integer geometry), FLR-ADR-024 (circulation, whose stand-in
for stairs this chapter replaces), FLR-ADR-027 (floors and ceilings, which a stair's rise and
headroom are measured from). Chapters 13 (frames), 14 (circulation), 15 (floors and ceilings) and
Annex A (`IfcStair`, `IfcStairFlight`, `IfcSlab` `LANDING`, `IfcRailing`).

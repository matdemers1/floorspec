# 2. Units, quantities and coordinates

## 2.1 Lengths

Every length in a Floorspec document is an integer number of **base units**, where one base unit
is exactly 1/1280 of a millimetre (FLR-ADR-004). The base unit is chosen so that both metric
lengths and imperial lengths to 1/256 inch are exact:

| Quantity | Base units |
|---|---|
| 1 mm | 1,280 |
| 1 cm | 12,800 |
| 1 m | 1,280,000 |
| 1/256 in | 127 |
| 1/16 in | 2,032 |
| 1 in | 32,512 |
| 1 ft | 390,144 |

A length MUST be a JSON integer — no fraction and no exponent — with an absolute value of at most
9,007,199,254,740,991 (2⁵³ − 1). {#FS-CORE-2.1.1 MUST}

The bound is about 7,000 km, far beyond any building; it keeps every length exactly representable
as an IEEE 754 double, so JavaScript readers lose nothing. Floorspec is unit-neutral: a tool
displays feet and inches or millimetres as its user prefers, and stores base units either way.

## 2.2 Exact derivation and rounding

Some values are **derived** — computed from the document rather than stored in it: the corner
points of walls (chapter 5), the outlines and areas of rooms (chapter 6), the positions of
openings (chapter 7). A derived coordinate generally falls between base units (an offset of half
a wall's thickness, or an intersection of two oblique faces, is rarely a whole number of base
units, and is often irrational).

A deriver MUST compute each derived coordinate as an exact value and round it once, with
`round()` (nearest integer, ties to even), to produce the derived output. {#FS-CORE-2.2.1 MUST}

Exact means exact: an implementation that computes in floating point and happens to land on the
other side of a rounding boundary is not conformant. Section 5.6 shows the form these values take
— integers combined with square roots of integers — and the reference implementation computes
them with exact integer arithmetic. Derived values are outputs; a document never stores them.

## 2.3 Coordinate system

Floorspec uses a right-handed coordinate system. **X** points to project east, **Y** to project
north, and **Z** up. Plan coordinates are `(x, y)`; elevations are `z`. Project north is a drawing
convention: the site's `trueNorth` (1.8) relates it to the real compass.

A deriver MUST interpret plan coordinates in this system, so that, seen from above, a rotation from
+X towards +Y is counter-clockwise. {#FS-CORE-2.3.1 MUST}

Everything that depends on handedness — which side of a wall is its left (5.4), the order of
edges around a junction (5.6), the orientation of room outlines (6.2) — follows from this.

> [!note] Converting to other systems
> glTF is Y-up and metric: export maps Floorspec (x, y, z) to glTF (x, z, −y) and divides by
> 1,280,000. IFC is Z-up like Floorspec.

## 2.4 Angles

An **angle** is an integer number of **microdegrees** (10⁻⁶ degree). Where a member is an angle,
its definition states the reference direction and range; positive angles are counter-clockwise
seen from above.

An angle MUST be a JSON integer. {#FS-CORE-2.4.1 MUST}

## 2.5 Other quantities

- **Pitch** is a pair of positive integers `{ "rise": r, "run": n }` (a roof at 6:12 is
  `{ "rise": 6, "run": 12 }`). It is used by later drafts.
- **Scaled decimals** — a thermal resistance, a fire rating — are integers with the scale named
  in the member's definition (for example, "R-value in thousandths").
- **Areas** and **volumes** are always derived and never stored. Areas are in square base units.
- **Counts** are non-negative integers.

## 2.6 Points and polygons

A **point** is a JSON array of exactly two lengths, `[x, y]`. A **polygon** is a JSON array of at
least three points, the vertices in order; the last vertex connects back to the first, and is not
repeated.

A polygon in a document MUST be simple — its edges meet only at consecutive shared vertices, no
two vertices coincide — and MUST enclose a positive area. {#FS-CORE-2.6.1 MUST}

A polygon may run clockwise or counter-clockwise. Derived polygons have a defined orientation and
starting vertex (6.2).

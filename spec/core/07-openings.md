# 7. Openings

An **opening** is a hole in a wall — a door, a window, or a plain cased opening — placed by
distances along its wall. It is **hosted**: it has no position of its own, and when its wall
moves, it moves with it.

## 7.1 Opening members

| Member | Type | Default | Meaning |
|---|---|---|---|
| `wall` | reference to a wall | — (always present) | the host wall |
| `offset` | length | — (always present) | from the wall's start junction along its location line to the opening's near edge |
| `width` | length | from `fill` (7.2) | the opening's width along the wall |
| `height` | length | from `fill` (7.2) | its height |
| `sill` | length | from `fill`, else `0` (7.2) | the height of its bottom above the wall's base |
| `fill` | reference to a `doorType` or `windowType` | absent: an empty opening | what fills it |
| `hinge` | `"start"` or `"end"` | `"start"` | for a door: the jamb its leaf hangs from — the one nearer the wall's start or its end |
| `swing` | `"left"` or `"right"` | `"right"` | for a door: the side of the wall, seen along the wall's direction, that its leaf opens into |
| `clearOpening` | clear opening (8.4) | from `fill` (7.2) | the net clear opening of what fills it, as declared |
| `name`, `extensions`, `extras` | | | 1.4 |

An opening is hosted on a wall, never on a separator: a separator has nothing to cut. An opening
is on its wall's level.

`offset` MUST NOT be negative. {#FS-CORE-7.1.1 MUST NOT}

`width` and `height` MUST be greater than zero, and `sill` MUST NOT be negative. {#FS-CORE-7.1.2 MUST}

`hinge` and `swing` mean nothing for a window or an empty opening, and a writer omits them there.
For a door, what they mean depends on how it operates (8.4): `hinge` is for a single leaf that
swings (`"swing"`), and `swing` for a door whose leaves swing one way (`"swing"`, `"doubleSwing"`).
When a door type declares no operation, they mean what they say here.

An opening's own `clearOpening` — an override of its fill type's (7.2), or the clear opening of an
empty opening, stated by whoever drew it — has an `area` only for a window.

An opening's `clearOpening` MUST NOT have an `area` unless the opening's `fill` is a window type. {#FS-CORE-7.1.3 MUST NOT}

## 7.2 Resolving dimensions

An opening's effective `width`, `height`, `sill` and `clearOpening` are resolved as every typed
property is (8.2): the opening's own member if present; otherwise the member of its `fill` type;
otherwise, for `sill` only, `0`. So a 36-inch door type sets the width of every opening it fills,
and one opening can still override it. An opening that resolves no `clearOpening` has no declared
clear opening; nothing computes one for it (7.4).

Every opening MUST resolve an effective `width` and an effective `height`. {#FS-CORE-7.2.1 MUST}

An empty opening has no type, so it states its own width and height.

A clear opening is what remains of the opening once its door or window is open, so it is never
wider or taller than the opening it is in. An opening that overrides its type's `width` or
`height` but not its `clearOpening` keeps the type's clear opening — which therefore must still
fit; a narrower opening for the same product usually needs its own `clearOpening` too.

An opening's effective `clearOpening`, when it has one, MUST NOT be wider than the opening's effective `width` nor taller than its effective `height`. {#FS-CORE-7.2.2 MUST NOT}

## 7.3 Placement

Along its wall, an opening occupies the interval from `offset` to `offset + width`, measured
along the location line from the wall's start junction. Vertically, it occupies the interval from
`sill` to `sill + height`, measured up from the wall's base elevation.

An opening MUST lie within its wall's length: `offset + width` MUST NOT exceed the length of the wall's location line. {#FS-CORE-7.3.1 MUST}

An opening MUST lie within its wall's height: `sill + height` MUST NOT exceed the wall's top elevation minus its base elevation. {#FS-CORE-7.3.2 MUST}

Two openings on the same wall MUST NOT overlap: if their intervals along the wall overlap by a positive length, their vertical intervals MUST NOT also overlap by a positive length. {#FS-CORE-7.3.3 MUST NOT}
A transom window above a door is two openings at the same offset, one above the other, and is
valid; two doors in the same place are not. Openings may touch.

The length test is exact: `offset + width ≤ L` is tested as `(offset + width)² ≤ dx² + dy²`.

## 7.4 Derived placement

An opening's **start point** and **end point** are the points on its wall's location line at
distances `offset` and `offset + width` from the start junction:
`S + d · offset / |d|` and `S + d · (offset + width) / |d|`, where `S` is the start junction's
position and `d` the wall's direction vector. Its **sill elevation** is the wall's base elevation
plus `sill`, and its **head elevation** is the sill elevation plus `height`.

A deriver MUST derive each opening's start point, end point, sill elevation and head elevation as defined in this section, rounded as 2.2 requires. {#FS-CORE-7.4.1 MUST}

An opening's **clear opening** is its effective `clearOpening` (7.2), exactly as declared: its
`width`, its `height`, and its `area` when one is declared. A clear opening is declared, never
derived: when no `area` is declared the area is unknown, and is not the product of the width and
the height — the sash of a casement or an awning window takes some of that rectangle, and a figure
computed from it would overstate exactly the value an escape-opening check reads.

A deriver MUST derive the clear opening of each opening that has an effective `clearOpening`, with exactly the members declared, and MUST NOT derive one for any other opening or derive an `area` that is not declared. {#FS-CORE-7.4.2 MUST}

## 7.5 Lints

A validator SHOULD report this with the code of chapter 10. {#FS-CORE-7.5.1 SHOULD}

- **Opening in a join** (`FS-LINT-005`, warning): an opening that reaches into the part of its wall
  where it meets another — closer to the start junction than the farther of `startLeft` and
  `startRight`, or closer to the end junction than the farther of `endLeft` and `endRight`, each
  measured as a distance along the location line, using the rounded face ends of 5.7. The
  comparison is strict: an opening that ends exactly where a join reaches is not reported. A door there cuts into the corner of the wall it
  meets.

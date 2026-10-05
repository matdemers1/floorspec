# 3. References

People and agents do not think in base units or IDs. They say "two foot six", "3810 mm", "the
north wall of the kitchen", "centred in the wall between the kitchen and the dining room". The
reference grammar lets an operation say exactly that, and the applier resolves it — deterministically,
against the document as it stands — to the integers and IDs Core needs, then echoes what it
resolved (1.4). Research on language models editing plans is unanimous that they fail at
coordinates and succeed at intent and topology; references are where that lesson becomes a
standard.

## 3.1 Lengths

Wherever an operation takes a **length**, it accepts a JSON integer (base units) or a string in
this grammar (ABNF, RFC 5234; letters are case-insensitive). Whitespace — spaces and tabs — may
appear between any two elements of the grammar, but never inside a `decimal` or a unit word; in
`mixed`, the separator between the whole inches and the fraction is either `"-"` (with whitespace
around it or not) or at least one whitespace character, so `6 1/2"` is a mixed number and
`61/2"` a fraction:

```abnf
length     = [ "-" ] ( metric / imperial )
metric     = decimal ( "mm" / "cm" / "m" )
imperial   = feet [ [ "-" ] inches ] / inches
feet       = decimal ( "'" / "ft" )
inches     = ( mixed / decimal ) ( DQUOTE / "in" )
mixed      = 1*DIGIT ( "-" / " " ) fraction / fraction
fraction   = 1*DIGIT "/" 1*DIGIT
decimal    = 1*DIGIT [ "." 1*DIGIT ] / "." 1*DIGIT
```

So `12'`, `12' 6"`, `12'6-1/2"`, `6 1/2"`, `3/4 in`, `3810mm`, `3.81 m` and `-2'` are lengths. The
value is computed exactly as a rational number of base units — 1 mm = 1280, 1 cm = 12800,
1 m = 1,280,000, 1 in = 32,512, 1 ft = 390,144 — and rounded once to an integer, ties to even.

An applier MUST resolve every length exactly as this section defines, and MUST reject a string that does not match the grammar, or a fraction with a zero denominator, with `FS-OPS-012`. {#FS-OPS-3.1.1 MUST}

Every imperial length to 1/256 inch and every metric length to 1/1280 mm is exact; others — a
third of an inch — are rounded, and the echo shows by how much.

## 3.2 Points and vectors

A **point** is `[x, y]` with each a length; a junction (its position); or one of two strings:

- `"<length> from <junction> toward <junction>"` — the point that distance along the straight line
  from the first junction towards the second, rounded once per coordinate, ties to even;
- `"<length> <direction> of <junction>"` — the junction's position plus that vector (below):
  `"12' east of J4"`.

A **vector** is `[dx, dy]` with each a length, or a string `"<length> <direction>"` where the
direction is `north` (+Y), `south`, `east` (+X) or `west`: `"2' east"` is `[780288, 0]`.

A point or vector string that has none of these forms, and is not a junction reference (an ID or
`start of` / `end of`, 3.3), does not match the grammar: `FS-OPS-012`. A junction reference that
names no junction resolves to nothing: `FS-OPS-003`.

An applier MUST resolve points and vectors exactly as this section defines, and MUST reject a point `"<length> from <junction> toward <junction>"` whose two junctions have the same position with `FS-OPS-003`. {#FS-OPS-3.2.1 MUST}

## 3.3 Element selectors

Wherever an operation takes an element, it accepts an ID or a **selector**:

| Selector | Resolves to |
|---|---|
| an ID | that element |
| a room's `name`, compared ignoring case | the room with that name |
| `<side> wall of <room>` | the wall on that side of the room (3.4) |
| `<side> separator of <room>` | likewise, a separator |
| `wall between <room> and <room>` | the wall with one room on each side |
| `separator between <room> and <room>` | likewise, a separator |
| `start of <wall>`, `end of <wall>` | that edge's start or end junction |
| `item <item>` | the program item with that ID or name |
| `brief of <room>` | the program item the room's `brief` names |

`<room>` is itself an ID or a room name; `<wall>` is an edge's ID or one of the four edge
selectors; `<item>` is a program item's ID or `name`. `<side>` is `north`, `south`, `east` or
`west`.

Keywords (`north`, `wall`, `separator`, `of`, `between`, `and`, `start`, `end`, `item`, `brief`,
and in 3.2 and 3.5 `from`, `toward`, `centered`) are matched ignoring case, with one or more
spaces or tabs between words. Names are compared with Unicode case folding. A string that has one
of the keyword forms above is read only as that form; any other string is an ID, a room name, or
both — and every element it names that way is a match, so a string that is one element's ID and
another room's name matches both. Where the member expects a program item — an adjacency
primitive's `a` and `b`, `addRoom`'s `brief`, `setRoomBrief`'s `item` — such a string also
matches the program items whose `name` it is, and where it expects an extension element —
`moveElement`'s `element` — the extension elements whose `name` it is; elsewhere the only names
it matches are rooms'. So `"Kitchen"` is the kitchen item in `setRoomBrief`'s `item` and the
kitchen room everywhere else, and `item Kitchen` is the item wherever it is written. When a room
name itself contains `and`, every split of `wall between … and …` is tried, and exactly one split
must resolve. Only elements of the kind the operation's member expects — a wall for
`addOpening`'s `wall`, a junction for `moveJunction`'s `id`, a program item for `setAdjacency`'s
`a` — count as matches.

`brief of <room>` resolves to nothing — `FS-OPS-003`, naming the room — when the room has no
`brief` or its `brief` names no program item. Under `"0.1"` (0.3) there are no program items, so
every program item selector resolves to nothing.

A selector that matches no element MUST be rejected with `FS-OPS-003`, and one that matches more than one MUST be rejected with `FS-OPS-004`, listing every match as the diagnostic's elements. {#FS-OPS-3.3.1 MUST}
An applier never guesses between candidates. A room name shared by two rooms is ambiguous; so is
"the north wall" of a room whose north side is two walls.

## 3.4 Sides and adjacency

Selectors that name a side, or a wall between two rooms, read the faces of the level (Core §6.1):

- The **outward normal** of an edge on a room's outer cycle is its right-hand normal in the
  direction the cycle is walked (the face is on the left), so it points away from the room.
- An edge is on the room's **east** side when that normal `(nx, ny)` has `nx > 0` and `−nx < ny ≤ nx`;
  **north** when `ny > 0` and `−ny ≤ nx < ny`; **west** when `nx < 0` and `nx ≤ ny < −nx`; **south**
  when `ny < 0` and `ny < nx ≤ −ny`. Every direction is on exactly one side; a wall at exactly 45°
  belongs to the side counter-clockwise before it.
- `<side> wall of <room>` matches the walls on the room's outer cycle that are on that side.
- `wall between R2 and R5` matches the walls with R2's face on one side and R5's face on the other.

A selector or a composite that reads faces (`moveWall` with `toward`, `moveRoom`, `resizeRoom`, `removeWall`) MUST be rejected with `FS-OPS-007` when the level it reads, in the working copy at that point of the batch, breaks any of Core §5.1–5.3 or contains the room's anchor in no bounded face. {#FS-OPS-3.4.1 MUST}
A wall-face host reference with `toward` (4.10) reads faces as `moveWall`'s `toward` does, and is
one of them.

## 3.5 Positions along a wall

Where an operation places something along a wall, it takes a **position**:

| Position | The near edge is at |
|---|---|
| `"centered"` | `(L − w) / 2` |
| `"<length> from start"` | that length |
| `"<length> from end"` | `L − length − w` |
| an integer or length | that offset |

where `L` is the length of the wall's location line and `w` the width being placed — for a hosted
element, which is placed by a point, `0` (4.10). Each is computed exactly and rounded once, ties
to even.

An applier MUST resolve positions exactly as this section defines. {#FS-OPS-3.5.1 MUST}

## 3.6 Areas

Wherever an operation takes an **area** — a program item's `targetArea` and `minArea` (4.9) — it
accepts a JSON integer (square base units, Core §11.1) or a string in this grammar, with the same
rules for letters and whitespace as 3.1:

```abnf
area   = decimal ( unit ( "2" / %xB2 ) / "sq" 1*WSP unit )
unit   = "mm" / "cm" / "m" / "in" / "ft"
```

So `11 m2`, `11 m²`, `120 sq ft`, `0.5 ft2` and `1600 in2` are areas. The value is computed exactly
as a rational number of square base units — 1 mm² = 1,638,400, 1 cm² = 163,840,000,
1 m² = 1,638,400,000,000, 1 in² = 1,057,030,144, 1 ft² = 152,212,340,736 — and rounded once, ties
to even. An area is never negative; whether it is in range is decided when the batch is
validated.

An applier MUST resolve every area exactly as this section defines, and MUST reject a string that does not match the grammar with `FS-OPS-012`. {#FS-OPS-3.6.1 MUST}

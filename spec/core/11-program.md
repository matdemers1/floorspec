# 11. The program

A house is designed against a **program**: what its owners need before anyone draws a wall —
three bedrooms of at least eleven square metres, a kitchen next to the dining room, a garage that
does not open into a bedroom. Floorspec keeps the program in the document, as data beside the
model it describes, so that every tool and every rule reads the same brief and can say how far the
model meets it (FLR-ADR-001).

The program has two parts. Its **items** say what spaces are wanted, how many and how large. Its
**adjacency graph** says which of them should, may or must not be next to each other. Rooms say
which item they fulfil. What core then derives is a comparison of model and brief, item by item
and adjacency by adjacency. A program never makes a document invalid: an unmet brief is a fact
about a design in progress, reported as a lint (11.5).

## 11.1 Program and items

The top-level `program` member:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `items` | object: program item ID → program item | `{}` | what spaces are wanted |
| `adjacency` | array of adjacencies (11.2) | `[]` | which items should, may or must not be next to each other |

A **program item**:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `function` | room function (4.1, 4.2) | — (always present) | what the space is for |
| `name` | string, 1–200 characters | absent | what its owners call it: "Primary bedroom" |
| `count` | integer, at least 1 | `1` | how many rooms the item asks for |
| `targetArea` | area: an integer number of square base units, from 1 to 2⁵³ − 1 | absent | the net area (6.4) each of its rooms is meant to have |
| `minArea` | area, as `targetArea` | absent | the least net area each of its rooms may have |
| `level` | reference to a level | absent | the level its rooms are preferred on |
| `extensions`, `extras` | | `{}` | 1.6, 1.7 |

Areas are in square base units, like net area: one square metre is 1,638,400,000,000 square base
units, and one square foot is 152,212,340,736. The bound of 2⁵³ − 1 is about 5,497 m².
`targetArea` and `minArea` apply to each room of the item, not to their sum: an item of
`"count": 3` bedrooms with a `minArea` asks for three bedrooms each at least that large.

An item's ID is its member name in `items`, in the document's single space of IDs (3.1.3).

A program, a program item and an adjacency MUST have only the members of their tables, each of the type and in the range its table gives. {#FS-CORE-11.1.1 MUST}

A program item's `function` MUST be a room function as 4.1.1 allows, and an extension term in it MUST name an extension that is a member of `extensionsUsed`, as 4.2.1 requires of a room's. {#FS-CORE-11.1.2 MUST}

The item's `level` is a preference, read by tools that lay out a program; core derives nothing
from it.

## 11.2 The adjacency graph

An **adjacency** relates two items:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `a` | reference to a program item | — (always present) | one item |
| `b` | reference to a program item | — (always present) | the other |
| `kind` | `"required"`, `"preferred"` or `"forbidden"` | — (always present) | whether rooms of `a` and `b` must, should or must not be adjacent (11.4) |
| `weight` | integer from 1 to 10 | `5` | how much it matters, for tools that trade adjacencies off |

An adjacency is undirected: `{ "a": "KIT", "b": "DIN" }` and `{ "a": "DIN", "b": "KIT" }` relate
the same **pair**.

An adjacency MUST NOT relate an item to itself: `a` and `b` MUST be different items. {#FS-CORE-11.2.1 MUST NOT}

Two adjacencies MUST NOT have the same pair and the same `kind`. {#FS-CORE-11.2.2 MUST NOT}

A pair that has a `"forbidden"` adjacency MUST NOT also have a `"required"` or a `"preferred"` one. {#FS-CORE-11.2.3 MUST NOT}
A brief that both wants and forbids a pair contradicts itself, and nothing could satisfy it. A pair
may have both a `"required"` and a `"preferred"` adjacency; the second adds nothing, but does not
contradict the first.

## 11.3 Rooms that fulfil items

A room names the item it fulfils with its `brief` member (6.5). An item's **rooms** are the rooms
whose `brief` names it. A room fulfils at most one item; an item may have any number of rooms, on
any levels. A room's function and its item's function are expected to agree, but core does not
compare them.

For every item, a deriver derives:

- `rooms` — the IDs of its rooms, sorted;
- `countMet` — whether it has at least `count` rooms;
- `minAreaMet`, present when the item has a `minArea` — whether the net area (6.4) of each of its
  rooms is at least `minArea` (true when it has no rooms);
- `targetAreaMet`, present when the item has a `targetArea` — whether the net area of each of its
  rooms is at least `targetArea` (true when it has no rooms).

A deriver MUST derive these values for every program item of a valid document, comparing areas exactly. {#FS-CORE-11.3.1 MUST}

An item with more rooms than `count` meets its count: the brief asked for at least that many.

## 11.4 Adjacent and connected rooms

Adjacency is a property of the faces of a level's plane graph (6.1), so it is exact and
independent of wall thickness.

- Each edge of a level has two half-edges (6.1), and each half-edge lies on the boundary — the
  outer cycle or an inner cycle — of exactly one face, bounded or unbounded. An edge **lies
  between** two faces when one of its half-edges is on the boundary of one and the other half-edge
  on the boundary of the other.
- Two rooms are **adjacent** when they are on the same level, their faces (6.3) are different, and
  some edge — a wall or a separator — lies between their faces.
- Two adjacent rooms are **connected** when some edge between their faces is a separator, or is a
  wall that hosts an opening whose `fill` is absent (an empty, cased opening) or is a `doorType`.
  A window does not connect rooms.

For every adjacency, in the order of the `adjacency` array, a deriver derives:

- `a`, `b` and `kind`, as written;
- `adjacent` — whether some room of `a` and some room of `b` are adjacent;
- `connected` — whether some room of `a` and some room of `b` are connected.

A deriver MUST derive these values for every adjacency of a valid document. {#FS-CORE-11.4.1 MUST}

A `"required"` or `"preferred"` adjacency is met when `adjacent` is true; a `"forbidden"` one is
met when it is false. Whether two rooms are connected is reported for rules and tools to use — a
rule that a garage must not open into a sleeping room reads `connected` — but no adjacency kind is
defined on it in this draft. Circulation (chapter 14) is built on connected rooms: it links them
into each building's door graph.

## 11.5 Lints

A validator SHOULD report these with the codes of chapter 10. {#FS-CORE-11.5.1 SHOULD}

- **Unmet count** (`FS-LINT-008`, warning): an item with fewer rooms than its `count`.
- **Below minimum area** (`FS-LINT-009`, warning): a room whose net area is less than its item's
  `minArea`; once for each such room.
- **Required adjacency unmet** (`FS-LINT-010`, warning): a `"required"` adjacency whose `adjacent`
  is false.
- **Forbidden adjacency present** (`FS-LINT-011`, warning): a `"forbidden"` adjacency whose
  `adjacent` is true.

A validator MUST NOT report an unmet program — a count, an area or an adjacency — with severity `error`. {#FS-CORE-11.5.2 MUST NOT}
The program's own structure is different: an adjacency that names no item, relates an item to
itself or contradicts another is an error (chapter 10), because no design could meet it.

## 11.6 Layout is not normative

A tool may generate plans from a program — place rooms to satisfy the adjacencies, size them to
the targets, weigh one adjacency against another by `weight`. How it does so is not part of
Floorspec: different solvers produce different plans from one program, and all of them are
conformant. What Floorspec fixes is what a program means and how a plan is measured against it
(11.3, 11.4), so that every tool agrees on whether a plan meets its brief.

## 11.7 Related

FLR-ADR-001 (a tiny core: the program is core data, the solver is not), FLR-ADR-002 (rooms are
found, not drawn), FLR-ADR-004 (base units, exact areas).

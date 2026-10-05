# 14. Circulation

A plan can meet every line of its brief and still be one nobody can live in: a room with no door,
a bedroom you can only reach by walking through someone else's. Circulation is how a person gets
from the front door to every room. Core derives it from what the document already holds — rooms,
the edges between them and the doors in those edges — so every tool and every rule agrees on which
rooms can be reached and how. Like the program (chapter 11), circulation never makes a document
invalid: a room without a way in is a fact about a design in progress, reported as a lint (14.4).

## 14.1 The door graph

Each building has a **door graph**. Its nodes are the rooms on the building's levels. Two rooms are
joined by a link when:

- they are **connected** (11.4): adjacent rooms with an edge between their faces that is a
  separator, or a wall hosting a door or an empty, cased opening. A window never connects rooms;
  or
- both have the function `circulation` (4.1) and they are on different levels of the building.

The second kind of link stands in for stairs, which this draft does not define (0.5): a stair hall
on one level and a landing on another are taken to be joined by the stair between them. A level
is reached from another only through its rooms of function `circulation`, so a plan whose stair
arrives in a room of another function names that room's function `circulation`, or the rooms
beyond it are not reachable. Rooms in different buildings are never linked.

Only rooms are nodes. A bounded face with no anchor (6.3) is not a room, and a path never passes
through one: a vestibule nobody has named does not lead anywhere until it is a room.

## 14.2 Entries

Each level has exactly one unbounded face, the outside (6.1). A room is an **entry** when some
edge lies between its face and the unbounded face of its level (11.4) and that edge is a separator,
or a wall hosting a door or an empty opening — the same edges that connect two rooms. A porch drawn
with separators on its open sides is an entry, and so is the room behind a front door; a room
whose only openings to the outside are windows is not.

An entry may be on any level and of any function: a garage whose door is the only way in is the
building's entry. Floorspec does not say which entry is the front door.

## 14.3 Reachable rooms

A room is **reachable** when it is an entry, or is linked in its building's door graph by a path of
links to a room that is an entry. A room of function `sleeping` (4.1) is a **sleeping room**; an
extension term is never a sleeping room, whatever it means. A sleeping room is reachable **only
through another sleeping room** when it is reachable, and it is not reachable in the door graph
from which every other sleeping room of its building has been removed — that is, every path from
every entry to it passes through some other sleeping room. A bedroom off a hall is not; the second
of two bedrooms in a row is; and a bedroom whose only door is into a bathroom shared with another
bedroom is too.

For every room, a deriver derives:

- `entry` — whether the room is an entry (14.2);
- `reachable` — whether the room is reachable;
- `throughSleeping`, present only for a sleeping room — whether it is reachable only through
  another sleeping room.

A deriver MUST derive these values for every room of a valid document. {#FS-CORE-14.3.1 MUST}

A room that is not a sleeping room is never reported for the rooms it is reached through: an
en-suite bathroom or a walk-in closet reached only through a bedroom is reachable, and that is
all circulation says about it.

## 14.4 Lints

A building is **evaluated** when a wall on one of its levels hosts a door or an empty opening.
Until then, no room of it has a way in, and saying so of every room of a plan that is still only
walls says nothing. A shaft, chase or void that no one walks into need not be a room at all: left
unanchored, it is reported only as an unanchored face (6.6).

A validator SHOULD report these with the codes of chapter 10. {#FS-CORE-14.4.1 SHOULD}

- **No entry** (`FS-LINT-014`, warning): an evaluated building that has at least one room and no
  entry; once for each such building.
- **Unreachable room** (`FS-LINT-012`, warning): a room of an evaluated building that has an
  entry, when the room is not reachable.
- **Sleeping room reached through another** (`FS-LINT-013`, warning): a sleeping room of an
  evaluated building that has an entry, when the room is reachable only through another sleeping
  room.

A building with no entry is reported once, with `FS-LINT-014`, and not once for each of its rooms:
every room of it is unreachable for the same reason.

A validator MUST NOT report `FS-LINT-012`, `FS-LINT-013` or `FS-LINT-014` for a building that is not evaluated, and MUST NOT report `FS-LINT-012` or `FS-LINT-013` for a room of a building that has no entry. {#FS-CORE-14.4.2 MUST NOT}

A validator MUST NOT report a circulation condition — a building with no entry, an unreachable room or a sleeping room reached through another — with severity `error`. {#FS-CORE-14.4.3 MUST NOT}

Whether a sleeping room may be reached through another, or through a garage, or must have a
second way out, is what building codes and owners decide; rules (Floorspec Rules) read the derived
values of 14.3 and say so with their own citations. Core reports only what the plan is.

## 14.5 Related

FLR-ADR-001 (a tiny core: circulation is derived from core data, never stored), FLR-ADR-002
(rooms are found, not drawn), and chapter 11, whose connected rooms the door graph is built on.

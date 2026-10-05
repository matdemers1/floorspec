# 19. Design options

A house is designed by trying things: the kitchen open to the dining room or closed off with a
door, a deck or none, a window here or there. Design options keep those alternatives in one
document. An **option set** holds the alternatives for one part of the design — "Kitchen" — and
each of its **options** — "A", "B" — is a group of elements that exist only when it is chosen.
Every other element is in every design. Choosing one option of every set gives a **design**, and
what a validator checks, a deriver derives and an exporter writes is always the document as seen
in one design. One option of every set is its **primary**, and the design of primaries is the one
a tool shows, derives and exports unless it is asked for another.

## 19.1 Option sets and options

An option set is an element of the `optionSets` collection, and an option an element of the
`options` collection (1.1).

**Option set.**

| Member | Type | Default | Meaning |
|---|---|---|---|
| `primary` | reference to an option | — (always present) | the set's primary option: the one the primary design chooses (19.3) |
| `name`, `extensions`, `extras` | | | 1.4 |

**Option.**

| Member | Type | Default | Meaning |
|---|---|---|---|
| `set` | reference to an option set | — (always present) | the option set this option is of |
| `name`, `extensions`, `extras` | | | 1.4 |

A set's **options** are the options whose `set` names it. They have no order: what distinguishes
one is its primary.

An option set and an option MUST have exactly the members of their tables, each of the type its table gives. {#FS-CORE-19.1.1 MUST}

An option set's `primary` MUST be one of the set's own options. {#FS-CORE-19.1.2 MUST}
So every option set has at least one option, and exactly one primary.

## 19.2 Membership

An element of the collections `junctions`, `walls`, `separators`, `openings`, `rooms`, `slabs`,
`roofs` and `stairs`, and an extension element (12.5), may be in an option. It says which with one
more member, and this table is part of the table of each of those kinds (1.4):

| Member | Type | Default | Meaning |
|---|---|---|---|
| `option` | reference to an option | absent: the element is in no option | the option the element is in |

An element in no option is **common**: it is in every design. An element names one option, so it
is in at most one option — and so in at most one option of one set (FLR-REQ-120).

An element of any other collection — a building, a level, a type, a material, an asset, an option set or an option — and a program item MUST NOT have an `option` member. {#FS-CORE-19.2.1 MUST NOT}
Levels and buildings are where options are drawn, not what they choose between. Types, materials
and assets are a library: an option uses one by referring to it, and a type that only option B's
walls use is simply not used in a design without B. The program is the brief every design answers.

## 19.3 Designs and views

A **design** chooses one option of every option set. The **primary design** chooses every set's
primary. A document with no option set has exactly one design, which chooses nothing, and is its
primary design.

The **view** of a design is the document as seen in it. It is the document with:

1. every element that is in an option the design does not choose removed, from its collection or
   from its extension's collection; and then
2. the `optionSets` and `options` members removed, and the `option` member of every element that
   remains removed.

A view is a document with no design options, and every chapter of this specification but this one
applies to it as it stands: its walls, rooms, openings, floors, roofs and stairs, its program and
its circulation are those of the design.

What this specification says a validator reports for a design, a deriver derives for it or an exporter writes for it MUST be exactly what it says of the design's view, as a document. {#FS-CORE-19.3.1 MUST}

A view is never stored. A design's view of a document with no option set is the document itself.

## 19.4 References across options

A view removes elements, so an element that remains must not refer to one that went.

A reference (3.2) MUST NOT resolve to an element that is in an option, unless the referring element is in that same option. {#FS-CORE-19.4.1 MUST NOT}
A reference may always resolve to a common element. So an opening in option A may be in a common
wall — a window only A has — but a common opening may not be in a wall only A has: it belongs in A
too. A wall of option A may end at a common junction, as a partition A adds against an exterior
wall does; a common wall may not end at a junction of A. An element in option A may not refer to
one in option B of the same set, which no design has with it, nor to one in an option of another
set, which a design may choose without it.

Rooms are found, not drawn (chapter 6), so a common room depends on no option by reference: a
common kitchen whose face option A's walls bound, and option B's bound differently, has one polygon
in A's design and another in B's. Its anchor says which face it is in each design (6.3).

## 19.5 Validity

A document has as many designs as the product of its sets' numbers of options. Core does not
validate them all: it validates the primary design, and every option against the primary of every
other set.

The **checked designs** of a document are its primary design and, for every option that is not its
set's primary, that option's **option design**: the primary design, except that it chooses that
option for its set. A document with no option set has one checked design, the primary design.

The reference invariants and the option invariants (`FS-INV-1101`, `FS-INV-1102`) are of the
document as a whole, every option included. Every other invariant is of a design.

A validator MUST evaluate every invariant other than the reference and option invariants for the view of every checked design, as 10.3 orders them, and so MUST report a document invalid when the view of any checked design has an error. {#FS-CORE-19.5.1 MUST}

A validator MUST report every diagnostic of the primary design's view as it is, and every other diagnostic of an option design's view with the member `design`, the ID of that option: a diagnostic of an option design's view that matches one of the primary design's view — the same code, severity and elements, each of the primary design's matched at most once — MUST NOT be reported again. {#FS-CORE-19.5.2 MUST}
An option design reports what is new in it. An error that the primary design and B's design both
have is reported once, without `design`; one that only B's design has is reported with
`"design": "B"`. Lints are reported the same way, except `FS-LINT-006`, `FS-LINT-007` and
`FS-LINT-018`, which are of the document: a type that only option B's walls use is used.

> [!note] Why these designs
> An option set holds the alternatives for one part of a design, and its options are compared
> with each other against the rest of the design as it stands. Checking each option against the
> primary of every other set finds every conflict between an option and the common elements, and
> between two options of different sets wherever one of them is a primary — and it takes one
> design per option, where every design takes their product. A design that chooses non-primary
> options of two sets is not checked: a kitchen option and a deck option that collide only when
> both are chosen make that one design invalid, not the document. A deriver asked for such a
> design validates its view first (19.6.2).

## 19.6 Derived values

A deriver derives the values of one design. The design is an input, as a jurisdiction profile is
an input to Floorspec Rules: a **design input** is a JSON object whose member names are option
set IDs and whose values are option IDs, choosing those options for those sets and every set's
primary for each set it does not name. With no design input, a deriver derives the primary
design.

A deriver MUST derive for a valid document exactly the values chapters 5 to 7 and 11 to 17 define for the view of the design its design input gives, or of the primary design when it has none. {#FS-CORE-19.6.1 MUST}

A deriver MUST NOT derive any value for a design input that names an option set the document does not have or maps a set to an option that is not that set's, nor for a design whose view is not valid. {#FS-CORE-19.6.2 MUST NOT}
The view of a checked design is valid whenever the document is; only a design that chooses
non-primary options of two or more sets can fail this test.

For comparing options side by side, a deriver also derives `options` for a document that has an
option set. For every option set it gives:

- `chosen` — the option the derived design chooses for it;
- for every option of the set, by ID:
  - `members` — the IDs of the elements in the option, sorted;
  - `rooms` — every room of the option's own design, with its net area (6.4): the option design
    of an option that is not primary, and the primary design for the primary;
  - `affected` — the IDs, sorted, of every element and program item that is in both the primary
    design's view and that design's view and for which anything chapters 5 to 7 and 11 to 17
    derive differs between the two: a common wall whose face ends move where an option's wall
    meets it, a common room whose polygon or area changes, a common door now reachable another
    way. The primary option's `affected` is empty.

These are derived from the checked designs, whatever the design input, so they compare every
option of a set against the same primary design.

A deriver MUST derive `options` as this section defines it for every valid document that has an option set, and MUST NOT derive an `options` member for one that has none. {#FS-CORE-19.6.3 MUST}

An editor compares option A and option B of a set side by side by deriving the two designs —
each with one design input — and drawing both; `rooms` gives their room tables, and `affected`
what changes in the common elements when one is switched for the other.

## 19.7 Exports

An export — IFC (Annex A), a drawing, a schedule — is of one design: its view.

An exporter SHOULD export the primary design unless it is asked for another, and SHOULD record which design it exported. {#FS-CORE-19.7.1 SHOULD}

## 19.8 Lints

A validator SHOULD report `FS-LINT-018` (info) for each option set with exactly one option: it has nothing to choose between. {#FS-CORE-19.8.1 SHOULD}

## 19.9 What this draft does not define

- an element in more than one option, and options within options: an option of one set that
  exists only within an option of another;
- levels, buildings, types, materials, assets and program items in options;
- an element common to two options with a member that differs between them — a wall whose type B
  changes: B and A each hold their own copy;
- validating every design: a design that chooses non-primary options of two sets is checked only
  when it is asked for (19.6.2).

## 19.10 Related

FLR-REQ-120 (option sets with membership and a primary), FLR-REQ-121 (create, switch and compare
options side by side), FLR-ADR-002 (rooms are found, so a common room follows each option's walls).
Chapters 3 (references), 10 (validation and its order, `FS-INV-1101`, `FS-INV-1102`,
`FS-LINT-018`) and Annex A (exports). Floorspec Ops edits options with its primitives and
normalizes a level option by option (Ops 2.2, 5.5); Floorspec Rules evaluates one design (Rules 1.2).

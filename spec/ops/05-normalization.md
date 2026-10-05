# 5. Normalization

After the last primitive of a batch, and before validation, the applier **normalizes** the working
copy: it makes every level planar again and merges what edits have made coincide. Normalization is
what lets an editor draw a wall straight across a room, or drag a corner onto another, without
first computing where the walls cross.

Normalization runs these steps in order — 5.1, then 5.2, then 5.3 — each over every level before
the next step, levels in order of ID. It changes nothing but what they say: it never moves an
anchor, never removes a wall or a room, and never changes a member other than those named. It
reads only the well-formed part of a level — junctions with an integer position, and edges whose
start and end are such junctions on the edge's own level — and leaves anything else as it is, for
validation to judge.

## 5.1 Merge coincident junctions

Junctions on one level with the same position are merged into one **survivor**: the one that was
in A, if exactly one of them was; otherwise the one whose ID sorts first. Every `start` and `end`
that names one of the others is redirected to the survivor; the others, and their joins, are
removed.

Two edges that now connect the same two junctions, or an edge whose start and end are now the
same junction, are left as they are — and validation rejects the batch (Core 5.2.1, 5.2.2).
Normalization never decides that a wall drawn on top of another was meant to replace it, so it
never merges two walls into one. A redirected wall still starts and ends where it did, so nothing
hosted on it moves (2.7).

An applier MUST merge coincident junctions as this section defines, before 5.2. {#FS-OPS-5.1.1 MUST}

## 5.2 Planarize

Planarization runs only on a level that, after 5.1, breaks Core §5.3 — where edges cross, an edge
passes through a junction, or two edges overlap. A level that satisfies Core §5.3 is left exactly
as it is. A level that breaks it is made planar, as a whole, by **snap rounding**:

1. **Hot pixels.** The **pixel** of an integer point `p` is the set of points of the plane that
   round to `p`, each coordinate to the nearest integer, ties to even. A pixel is **hot** when it
   contains a junction position on the level, or the rounded intersection of two edges that meet
   at a point interior to at least one of them.
2. **Routing.** Each edge is replaced by the polyline through the centres of every hot pixel its
   location line passes through, in order along the edge, from its start junction to its end
   junction.
3. **Junctions.** A hot pixel whose centre is not a junction position gets a new junction there
   (minted, in order of the hot pixel's `x`, then `y`).
4. **Splitting.** An edge routed through *n* > 0 intermediate hot pixels becomes *n* + 1 edges. The
   first, from the original start, keeps the edge's ID; the others are minted in order along the
   edge and copy every member of the original except `start` and `end`. Edges are split walls
   first, then separators, each in order of ID.
5. **Openings.** An opening on a split wall moves to the piece whose interval along the original
   location line contains the opening's whole interval `[offset, offset + width]`; a piece's
   interval runs between the distances along the original line of the projections of its two
   ends. The opening's offset becomes `offset − s`, where `s` is the distance along the original
   location line of the projection of the piece's start, computed exactly and rounded once, ties
   to even. An opening that no piece contains straddles a new junction: the batch is rejected
   with `FS-OPS-009`.
6. **Hosted elements.** An extension element whose `host` is a `wallFace` host on a split wall,
   with an integer `offset`, moves to the piece whose interval contains its offset, where a
   piece's interval `[s, e)` is taken half-open — so an element exactly at a new junction goes to
   the piece that starts there — except that the last piece's includes its end. Its `host.wall`
   becomes that piece and its `offset` becomes `offset − s`, computed exactly and rounded once,
   ties to even; its `side` and `height` do not change, since every piece runs the same way and
   keeps the wall's base and top. An element that no piece contains — its offset negative or
   past the wall's end — stays on the first piece, unchanged, for validation to judge (Core
   §13.3.1, 13.3.2). A hosted element is a point, so unlike an opening it never straddles.
7. **Finishes** (Ops 0.3). Every piece copies the split wall's `finishes` (Core §18.5) with its other
   members (step 4), and then the regions of each of its faces are the original's cut to the piece:
   with `[s, e]` the piece's interval along the original location line (step 5), a region whose
   `from` is less than `e` and whose `to` is greater than `s` runs from `max(from, s) − s` to
   `min(to, e) − s`, each computed exactly and rounded once, ties to even, with its `bottom`, `top`
   and `material` unchanged — and is dropped if the rounded `from` is not less than the rounded `to`;
   every other region is dropped. The regions keep their order. A region whose `from` or `to` is not
   an integer is left on every piece as it is, for validation to judge. So a backsplash that a new
   wall crosses is cut in two at the wall's location line, each part on its own piece, and each
   piece keeps the face's `material`.

Snap rounding moves no point of any edge by more than one base unit, and its result does not
depend on the order of edges or on any implementation detail. It creates junctions only where none
exist, so it never makes two junctions coincide.

> [!note] Near misses
> On a level that is planarized, an edge that passes within half a base unit of a junction it does
> not touch passes through that junction's hot pixel, and is routed through the junction and split
> there. A level with no crossing, no junction inside an edge and no overlap is never planarized,
> so an edit elsewhere — a rename, a finish — leaves such a near miss exactly as it is.

An applier MUST planarize exactly the levels this section names, as this section defines, and MUST reject the batch with `FS-OPS-009` when an opening straddles a junction it inserts. {#FS-OPS-5.2.1 MUST}

An applier MUST move every extension element hosted on the face of a split wall exactly as step 6 defines. {#FS-OPS-5.2.2 MUST}

An applier MUST cut the regions of a split wall's finishes to its pieces exactly as step 7 defines. {#FS-OPS-5.2.3 MUST}
So a wall drawn across a run of outlets splits the run between the two pieces, and every outlet
stays where it was: exactly, when the crossing is at an integer point of the original location
line, as it is wherever axis-aligned walls cross; otherwise within the rounding that moved the
pieces' ends.

## 5.3 Join cleanup

A junction whose `join.through` names a wall that no longer ends at that junction has its `join`
removed, so the default join applies.

An applier MUST remove such joins. {#FS-OPS-5.3.1 MUST}

## 5.4 When normalization runs

An applier MUST normalize exactly as this chapter defines — 5.1, then 5.2, then 5.3 — once, after the last primitive of the batch and before validation. {#FS-OPS-5.4.1 MUST}

## 5.5 Design options

A level of a Core 0.3 document may hold elements of options (Core chapter 19). Two elements of
different options of one set are never in one design, and nothing may refer from one option into
another (Core §19.4), so normalization never joins them: it merges and planarizes a level option by
option. A junction or an edge with no `option` member is **common**.

- **Merging (5.1).** Where junctions on a level share a position and one of them is common, every
  junction there merges into one survivor chosen among the common ones as 5.1 chooses. Where none
  is common, the junctions of each option merge among themselves, and those of different options
  are left as they are.
- **Planarizing (5.2).** A level is planarized in **domains**: first its common junctions and edges;
  then, for each option that has a junction or an edge on the level, in order of the option's ID,
  the common ones together with that option's. Each domain is planarized exactly as 5.2 planarizes a
  level — only when it breaks Core §5.3, and as a whole — with this addition: in an option's domain,
  a junction step 3 inserts at a hot pixel that a common edge is routed through is common, and every
  other junction it inserts is in the option; and an existing junction of the option at such a pixel
  becomes common, its `option` removed. The pieces of a split edge copy its `option` as they copy
  every other member (step 4), and openings and hosted elements move to the pieces as steps 5 and 6
  say, whatever option they are in.

Without a junction or an edge in an option, a level has one domain, all of it, and normalizes
exactly as 5.1 and 5.2 say. Edges of options of two different sets are never planarized against each
other: if they cross, the design that has both is invalid, and validation rejects the batch when
that design is one Core checks (Core §19.5).

An applier MUST merge and planarize a level that has junctions or edges in options exactly as this section defines. {#FS-OPS-5.5.1 MUST}

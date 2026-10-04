# 5. Normalization

After the last primitive of a batch, and before validation, the applier **normalizes** the working
copy: it makes every level planar again and merges what edits have made coincide. Normalization is
what lets an editor draw a wall straight across a room, or drag a corner onto another, without
first computing where the walls cross.

Normalization runs these steps, in order, on every level. It changes nothing but what they say:
it never moves an anchor, never removes a wall or a room, and never changes a member other than
those named.

## 5.1 Merge coincident junctions

Junctions on one level with the same position are merged into one **survivor**: the one that was
in A, if exactly one of them was; otherwise the one whose ID sorts first. Every `start`, `end` and
`join.through` reference to the others is redirected to the survivor, and the others are removed.

Two edges that now connect the same two junctions, or an edge whose start and end are now the
same junction, are left as they are — and validation rejects the batch (Core 5.2.1, 5.2.2).
Normalization never decides that a wall drawn on top of another was meant to replace it.

An applier MUST merge coincident junctions as this section defines, before 5.2 and again after it. {#FS-OPS-5.1.1 MUST}

## 5.2 Planarize

Where edges cross, or an edge passes through a junction, the level is made planar by **snap
rounding**:

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
   edge and copy every member of the original except `start` and `end`.
5. **Openings.** An opening on a split wall moves to the piece whose interval along the original
   location line contains the opening's whole interval `[offset, offset + width]`, and its offset
   becomes its distance from that piece's start, computed exactly and rounded once, ties to even.
   An opening that no piece contains straddles a new junction: the batch is rejected with
   `FS-OPS-009`.

Snap rounding moves no point of any edge by more than one base unit, and its result does not
depend on the order of edges or on any implementation detail.

An applier MUST planarize every level as this section defines, and MUST reject the batch with `FS-OPS-009` when an opening straddles a junction it inserts. {#FS-OPS-5.2.1 MUST}

## 5.3 Join cleanup

A junction whose `join.through` names a wall that no longer ends at that junction has its `join`
removed, so the default join applies.

An applier MUST remove such joins. {#FS-OPS-5.3.1 MUST}

## 5.4 When normalization runs

An applier MUST normalize exactly as this chapter defines — 5.1, then 5.2, then 5.1 again, then 5.3 — once, after the last primitive of the batch and before validation. {#FS-OPS-5.4.1 MUST}

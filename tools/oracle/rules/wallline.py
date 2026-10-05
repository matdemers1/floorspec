"""The wall line of a room (spec/rules 8.1), and receptacle reach and the wall run between
receptacles (8.2), in exact integers: every length is rounded once where 8.1 says, and half-gaps are
kept doubled until the one final rounding."""

from __future__ import annotations

from ..derive import rpoint
from .qr import round_div_sqrt, round_sqrt


def _doorway_walls(doc):
    out = {}
    for oid, o in doc.openings.items():
        fill = o.get('fill')
        if fill is None or doc.types[fill]['kind'] == 'doorType':
            w, _, _ = doc.opening_dims(oid)
            out.setdefault(o['wall'], []).append((o['offset'], o['offset'] + w))
    return out


def wall_line(ctx, rid):
    """(total length, breaks [(a, b)], receptacles [(position, id)]) of a room's wall line, with
    positions measured along it from the start of the first run of its walk."""
    doc = ctx.doc
    lv = ctx.level(doc.rooms[rid]['level'])
    g = lv.g
    walk = lv.faces[lv.room_face[rid]]['outer']
    n = len(walk)
    contrib = []                                  # the ring's points at each half-edge's head, in order
    for eid, _, v in walk:
        m = g.idx[v][eid]
        contrib.append([rpoint(p) for p in reversed(g.wedge(v, m - 1))])
    doors = _doorway_walls(doc)
    recs = []
    for eid_, (x, c, el) in ctx.ext.items():
        h = el.get('host')
        if x == 'FS_electrical' and c == 'receptacles' and h is not None and h['mode'] == 'wallFace':
            recs.append((eid_, h))
    pos, breaks, found = 0, [], []
    for i in range(n):
        eid, u, v = walk[i]
        e = g.edges[eid]
        p1, p2 = contrib[i - 1][-1], contrib[i][0]
        S, E = g.pos[e.start], g.pos[e.end]
        d = (E[0] - S[0], E[1] - S[1])
        D = d[0] * d[0] + d[1] * d[1]
        s1 = round_div_sqrt((p1[0] - S[0]) * d[0] + (p1[1] - S[1]) * d[1], D)
        s2 = round_div_sqrt((p2[0] - S[0]) * d[0] + (p2[1] - S[1]) * d[1], D)
        forward = u == e.start
        length = max(0, s2 - s1 if forward else s1 - s2)
        lo, hi = (s1, s2) if forward else (s2, s1)
        if lo <= hi:                              # a run of length 0 has no break, but may hold a receptacle

            def along(s):
                return pos + abs(s - s1)
            if e.kind == 'separator':
                if length > 0:
                    breaks.append((pos, pos + length))
            else:
                for a, b in doors.get(eid, ()):
                    a, b = max(a, lo), min(b, hi)
                    if b > a:
                        x, y = sorted((along(a), along(b)))
                        breaks.append((x, y))
                side = 'left' if forward else 'right'
                for rec, h in recs:
                    if h['wall'] == eid and h['side'] == side and lo <= h['offset'] <= hi:
                        found.append((along(h['offset']), rec))
        pos += length
        if len(contrib[i]) == 2:                  # a return at the head junction
            q1, q2 = contrib[i]
            pos += round_sqrt((q2[0] - q1[0]) ** 2 + (q2[1] - q1[1]) ** 2)
    return pos, breaks, found


def stretches(total, breaks):
    """[(start, end, closed)]: the stretches of a wall line (8.1), as intervals of its positions;
    an end may exceed `total` for a stretch that wraps past the start."""
    if total <= 0:
        return []
    if not breaks:
        return [(0, total, True)]
    bs = sorted(breaks)
    merged = [list(bs[0])]
    for a, b in bs[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out = []
    for i, (a, b) in enumerate(merged):
        na = merged[(i + 1) % len(merged)][0] + (total if i == len(merged) - 1 else 0)
        if na > b:
            out.append((b, na, False))
    return out


def receptacle_measures(ctx, rid, counted):
    """(reach, run, ids): 8.2 for the counted receptacles (a predicate on an element ID)."""
    total, breaks, found = wall_line(ctx, rid)
    pts = sorted((p, r) for p, r in found if counted(r))
    ids = sorted({r for _, r in pts})
    reach2, run = 0, 0                            # reach doubled, to keep halves exact
    for a, b, closed in stretches(total, breaks):
        ell = b - a
        if closed:
            rs = sorted({p % total for p, _ in pts})
        else:
            rs = sorted({x - a for p, _ in pts for x in (p, p + total) if a <= x <= b})
        if not rs:
            reach2, run = max(reach2, 2 * ell), max(run, ell)
            continue
        gaps = [rs[i + 1] - rs[i] for i in range(len(rs) - 1)]
        if closed:
            gaps.append(rs[0] + ell - rs[-1])
            reach2 = max(reach2, *gaps)
            run = max(run, *gaps)
        else:
            reach2 = max(reach2, 2 * rs[0], 2 * (ell - rs[-1]), *gaps)
            run = max(run, rs[0], ell - rs[-1], *gaps)
    reach = reach2 // 2 if reach2 % 2 == 0 else (reach2 // 2 if (reach2 // 2) % 2 == 0 else reach2 // 2 + 1)
    return reach, run, ids

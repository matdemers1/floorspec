"""Normalization (Ops chapter 5): merge coincident junctions, planarize by snap rounding - only a
level that breaks Core 5.3 - and clean up joins, each step over every level before the next,
levels in ID order.

Exactness. Pixels, intersections and the order of hot pixels along an edge are decided with
Fractions; the intervals of the original location line that the pieces of a split wall cover
are Surds. Nothing is approximated.

The pixel of an integer point p is the set of points that round to p, each coordinate to the
nearest integer, ties to even: along each axis, [n - 1/2, n + 1/2] when n is even (both halves
round to n) and (n - 1/2, n + 1/2) when n is odd.

Only the well-formed part of a working copy takes part: junctions with a string `level` and an
integer position, and edges whose start and end are such junctions on the edge's own level.
Anything else is left exactly as it is, for validation to reject.

Ops 0.2 adds step 6 of 5.2: an extension element hosted on a face of a split wall moves to the
piece whose interval contains its offset. Under Ops 0.1 there are no extension elements.
"""

from __future__ import annotations

import copy
from fractions import Fraction

from .. import plane
from ..surd import Surd
from .errors import OpsError
from .faces import coll, is_point
from .space import ext_elements, host_of
from .version import OPS_01, Profile

PREFIX = {'walls': 'W', 'separators': 'S'}


# ------------------------------------------------------------------------------ pixels

def round_point(p) -> tuple[int, int]:
    return (round(p[0]), round(p[1]))          # Fraction: nearest, ties to even


def _axis(a: int, d: int, c: int):
    """The t-interval where a + t*d lies in the pixel interval of integer c, as
    (lo, lo_closed, hi, hi_closed); None when empty; 'all' when every t does."""
    closed = c % 2 == 0
    lo_v, hi_v = Fraction(2 * c - 1, 2), Fraction(2 * c + 1, 2)
    if d == 0:
        inside = lo_v < a < hi_v or (closed and a in (lo_v, hi_v))
        return 'all' if inside else None
    t1, t2 = (lo_v - a) / d, (hi_v - a) / d
    return (t1, closed, t2, closed) if d > 0 else (t2, closed, t1, closed)


def _meet(i, j):
    if i is None or j is None:
        return None
    if j == 'all':
        return i
    lo, lc, hi, hc = i
    lo2, lc2, hi2, hc2 = j
    if lo2 > lo:
        lo, lc = lo2, lc2
    elif lo2 == lo:
        lc = lc and lc2
    if hi2 < hi:
        hi, hc = hi2, hc2
    elif hi2 == hi:
        hc = hc and hc2
    if lo < hi or (lo == hi and lc and hc):
        return (lo, lc, hi, hc)
    return None


def segment_in_pixel(a, b, c):
    """The t-interval of the closed segment a + t(b - a), t in [0, 1], inside the pixel of c;
    None when the segment does not pass through it."""
    i = (Fraction(0), True, Fraction(1), True)
    i = _meet(i, _axis(a[0], b[0] - a[0], c[0]))
    i = _meet(i, _axis(a[1], b[1] - a[1], c[1]))
    return i


def route(a, b, hot) -> list[tuple[int, int]]:
    """The hot pixels a segment passes through, in order along it from a to b (5.2 step 2).
    Pixels are disjoint, so their intervals are; they are ordered by where each begins, a pixel
    that contains its first point before one that only approaches it."""
    found = []
    for c in hot:
        i = segment_in_pixel(a, b, c)
        if i is not None:
            found.append(((i[0], 0 if i[1] else 1), c))
    found.sort()
    return [c for _, c in found]


def crossing(a, b, c, d):
    """The point where segments ab and cd meet, when they meet in exactly one point and it is
    interior to at least one of them; else None."""
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = plane.cross(r, s)
    if den == 0:
        return None
    ca = (c[0] - a[0], c[1] - a[1])
    t = Fraction(plane.cross(ca, s), den)
    u = Fraction(plane.cross(ca, r), den)
    if not (0 <= t <= 1 and 0 <= u <= 1):
        return None
    if not (0 < t < 1 or 0 < u < 1):
        return None
    return (a[0] + t * r[0], a[1] + t * r[1])


def hot_pixels(junction_positions, segments) -> set:
    """5.2 step 1: the pixels of the junctions, and of the rounded crossings."""
    hot = set(junction_positions)
    for i in range(len(segments)):
        for k in range(i + 1, len(segments)):
            p = crossing(*segments[i], *segments[k])
            if p is not None:
                hot.add(round_point(p))
    return hot


# ------------------------------------------------------------------------------ the steps

def _junctions_on(wc, level):
    return {jid: tuple(j['position']) for jid, j in coll(wc, 'junctions').items()
            if isinstance(j, dict) and j.get('level') == level and is_point(j.get('position'))}


def _edges_on(wc, level, js):
    out = []
    for c in ('walls', 'separators'):
        for eid, e in coll(wc, c).items():
            if isinstance(e, dict) and e.get('level') == level and e.get('start') in js and e.get('end') in js:
                out.append((c, eid, e['start'], e['end']))
    return sorted(out, key=lambda x: (x[0] != 'walls', x[1]))      # walls, then separators; by ID


def levels_of(wc) -> list[str]:
    return sorted({j['level'] for j in coll(wc, 'junctions').values()
                   if isinstance(j, dict) and isinstance(j.get('level'), str) and is_point(j.get('position'))})


def merge(wc: dict, level: str, in_a: set) -> None:
    """5.1: one survivor per position - the one that was in A if exactly one was, otherwise the
    one whose ID sorts first; references to the others are redirected to it."""
    groups: dict = {}
    for jid, p in _junctions_on(wc, level).items():
        groups.setdefault(p, []).append(jid)
    for ids in groups.values():
        if len(ids) < 2:
            continue
        was = [j for j in ids if j in in_a]
        survivor = was[0] if len(was) == 1 else min(ids)
        for other in ids:
            if other == survivor:
                continue
            for c in ('walls', 'separators'):
                for e in coll(wc, c).values():
                    if isinstance(e, dict):
                        for k in ('start', 'end'):
                            if e.get(k) == other:
                                e[k] = survivor
            del wc['junctions'][other]


def effective_width(wc, o):
    if type(o.get('width')) is int:
        return o['width']
    t = coll(wc, 'types').get(o.get('fill')) if isinstance(o.get('fill'), str) else None
    if isinstance(t, dict) and type(t.get('width')) is int:
        return t['width']
    return None


def breaks_5_3(js: dict, edges) -> bool:
    """Core 5.3 on the well-formed part of a level: a crossing, a junction inside an edge, or an
    overlap - the validator's own exact tests."""
    segs = [(js[s], js[t]) for _, _, s, t in edges]
    for i, (a, b) in enumerate(segs):
        for c, d in segs[i + 1:]:
            if plane.proper_cross(a, b, c, d) or plane.collinear_overlap(a, b, c, d):
                return True
        if any(plane.in_open_segment(p, a, b) for p in js.values()):
            return True
    return False


def planarize(wc: dict, level: str, mint, straddles: list, profile: Profile = OPS_01) -> None:
    """5.2: snap rounding, on a level that breaks Core 5.3; any other level is left as it is."""
    js = _junctions_on(wc, level)
    edges = [e for e in _edges_on(wc, level, js) if js[e[2]] != js[e[3]]]
    if not breaks_5_3(js, edges):
        return
    hot = hot_pixels(js.values(), [(js[s], js[t]) for _, _, s, t in edges])
    at = {p: j for j, p in js.items()}
    for p in sorted(hot):                                   # step 3: x, then y
        if p not in at:
            jid = mint('J')
            wc.setdefault('junctions', {})[jid] = {'level': level, 'position': [p[0], p[1]]}
            at[p] = jid
    for c, eid, s, t in edges:                              # step 4: walls then separators, by ID
        a, b = js[s], js[t]
        path = route(a, b, hot)
        assert path[0] == a and path[-1] == b, (eid, path)
        inner = path[1:-1]
        if not inner:
            continue
        verts = [s] + [at[p] for p in inner] + [t]
        original = copy.deepcopy(wc[c][eid])
        wc[c][eid]['end'] = verts[1]
        pieces = [eid]
        for i in range(1, len(verts) - 1):
            nid = mint(PREFIX[c])
            piece = {k: copy.deepcopy(v) for k, v in original.items() if k not in ('start', 'end')}
            piece['start'], piece['end'] = verts[i], verts[i + 1]
            wc[c][nid] = piece
            pieces.append(nid)
        if c == 'walls':
            _rehost(wc, eid, a, b, inner, pieces, straddles)
            _rehost_hosted(wc, eid, a, b, inner, pieces, profile)
            if profile.v03:
                _cut_regions(wc, a, b, inner, pieces)


def _rehost(wc, eid, a, b, inner, pieces, straddles):
    """5.2 step 5: each opening goes to the piece whose interval along the original location
    line contains its whole interval; its offset becomes its distance from that piece's start,
    measured along the original line."""
    d = (b[0] - a[0], b[1] - a[1])
    D = plane.dot(d, d)
    bounds = [Surd(0)] + [Surd.sqrt(D, Fraction(plane.dot(plane.sub(p, a), d), D)) for p in inner] + [Surd.sqrt(D)]
    for oid, o in sorted(coll(wc, 'openings').items()):
        if not isinstance(o, dict) or o.get('wall') != eid or type(o.get('offset')) is not int:
            continue
        w = effective_width(wc, o)
        if w is None:
            continue
        lo, hi = o['offset'], o['offset'] + w
        for i, piece in enumerate(pieces):
            if bounds[i] <= lo and hi <= bounds[i + 1]:
                o['wall'] = piece
                o['offset'] = (Surd(lo) - bounds[i]).round()
                break
        else:
            straddles.append(oid)


def _rehost_hosted(wc, eid, a, b, inner, pieces, profile):
    """Ops 0.2, 5.2 step 6: an extension element on a face of the split wall goes to the piece whose
    interval [s, e) along the original location line contains its offset - the last piece's
    interval includes its end - and its offset becomes offset - s, rounded once, ties to even. Its
    side and height do not change. One whose offset is not an integer, or that no piece contains,
    is left as it is, on the first piece, for validation to judge."""
    d = (b[0] - a[0], b[1] - a[1])
    D = plane.dot(d, d)
    bounds = [Surd(0)] + [Surd.sqrt(D, Fraction(plane.dot(plane.sub(p, a), d), D)) for p in inner] + [Surd.sqrt(D)]
    last = len(pieces) - 1
    for _, _, hid, el in sorted(ext_elements(wc, profile), key=lambda x: x[2]):
        h = host_of(el)
        if h is None or h.get('mode') != 'wallFace' or h.get('wall') != eid or type(h.get('offset')) is not int:
            continue
        off = h['offset']
        for i, piece in enumerate(pieces):
            if bounds[i] <= off and (off < bounds[i + 1] or (i == last and off <= bounds[i + 1])):
                if i > 0:
                    h['wall'] = piece
                    h['offset'] = (Surd(off) - bounds[i]).round()
                break


def _cut_regions(wc, a, b, inner, pieces):
    """Ops 0.3, 5.2 step 7: each piece copied the split wall's `finishes` (step 4); the regions of each of its
    faces are the original's cut to the piece's interval [s, e] along the original location line - a region
    with from < e and to > s runs from max(from, s) - s to min(to, e) - s, each end exact and rounded once,
    ties to even, and is dropped when the rounded from is not less than the rounded to; every other region is
    dropped. A region whose from or to is not an integer is left as it is on every piece, for validation."""
    d = (b[0] - a[0], b[1] - a[1])
    D = plane.dot(d, d)
    bounds = [Surd(0)] + [Surd.sqrt(D, Fraction(plane.dot(plane.sub(p, a), d), D)) for p in inner] + [Surd.sqrt(D)]
    walls = coll(wc, 'walls')
    original = copy.deepcopy(walls[pieces[0]].get('finishes'))
    if not isinstance(original, dict):
        return
    for i, piece in enumerate(pieces):
        s, e = bounds[i], bounds[i + 1]
        f = walls[piece].get('finishes')
        for side, face in original.items():
            if not (isinstance(face, dict) and isinstance(face.get('regions'), list)):
                continue
            cut = []
            for r in face['regions']:
                if not (isinstance(r, dict) and type(r.get('from')) is int and type(r.get('to')) is int):
                    cut.append(copy.deepcopy(r))
                    continue
                lo, hi = Surd(r['from']), Surd(r['to'])
                if not ((lo - e).sign() < 0 and (hi - s).sign() > 0):
                    continue
                f0 = ((lo if (lo - s).sign() >= 0 else s) - s).round()
                t0 = ((hi if (hi - e).sign() <= 0 else e) - s).round()
                if f0 < t0:
                    cut.append({**copy.deepcopy(r), 'from': f0, 'to': t0})
            f[side]['regions'] = cut


def join_cleanup(wc: dict) -> None:
    """5.3: a join naming a wall that does not end at its junction is removed."""
    walls = coll(wc, 'walls')
    for jid, j in coll(wc, 'junctions').items():
        if not isinstance(j, dict) or not isinstance(j.get('join'), dict):
            continue
        through = j['join'].get('through')
        if not isinstance(through, list):
            continue
        for w in through:
            wall = walls.get(w) if isinstance(w, str) else None
            if not (isinstance(wall, dict) and jid in (wall.get('start'), wall.get('end'))):
                del j['join']
                break


def normalize(wc: dict, in_a: set, mint, profile: Profile = OPS_01) -> None:
    """5.4: 5.1, then 5.2, then 5.3. FS-OPS-009 for every opening that straddles a junction
    planarization inserts. (Planarization creates junctions only where none are, so nothing can
    coincide after it.)"""
    for level in levels_of(wc):
        merge(wc, level, in_a)
    straddles: list[str] = []
    for level in levels_of(wc):
        planarize(wc, level, mint, straddles, profile)
    if straddles:
        raise OpsStraddle(straddles)
    join_cleanup(wc)


class OpsStraddle(Exception):
    def __init__(self, openings):
        super().__init__(', '.join(openings))
        self.errors = [OpsError('FS-OPS-009', [o], None, f'{o} straddles a junction planarization inserts')
                       for o in sorted(openings)]

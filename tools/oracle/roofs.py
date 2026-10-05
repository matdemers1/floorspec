"""Roofs (Core 0.3, chapter 16): a roof's members and its edges (16.1, 16.2), its eave outline (16.3),
the roof invariants FS-INV-801 to FS-INV-805, the class of roofs whose surface this draft derives and
the lint FS-LINT-015 for the others (16.4), and the derived `roofs` (16.5).

Everything is exact and rounded once. The eave outline is the footprint with every edge moved out by
its overhang - each vertex the intersection of its two edges' moved lines, of the form of a corner
point (5.5), rounded once; on a rectilinear footprint it is exact. Everything after it is computed
from the rounded outline, as a vault's low and high are from the rounded room polygon (15.3).

A flat roof is the outline at its eave. A shed roof is one plane through its sloped edge:
z(P) = eave + (rise / run) * n.(P - A) / |n|, one radicand. An equal-pitch roof on a rectilinear
outline (16.4.3) rises with its rise distance h(P) - the least Chebyshev distance from P to a sloped
edge - and z(P) = eave + (rise / run) * h(P): the straight-skeleton roof, whose every node has
coordinates that are multiples of one half. Its faces are found by sweeping the wavefront: for each
interval between the times at which two of the lines x = x_i, x = x_i +- t, the seams, and their y
counterparts, cross, the wavefront {P : h(P) >= t + eps} is computed as cells of the grid those lines
cut, exactly, with t + eps symbolic (a pair (a, b) for a + b*eps, compared lexicographically); every
side of it on a sloped edge's moving line sweeps a trapezoid of that edge's face until the next time.
The trapezoids of a face are united by cancelling opposite atomic edges. A self-check labels every
trapezoid's centroid by the pointwise definition of 16.4.3 and asserts the two agree.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as F

from . import plane
from .derive import LevelGraph
from .surd import Surd


# ------------------------------------------------------------------------------ members (16.1, 16.2)

def footprint(roof):
    return [tuple(p) for p in roof['footprint']]


def edge(roof, i) -> dict:
    return roof.get('edges', {}).get(str(i), {})


def overhang(roof, i) -> int:
    return edge(roof, i).get('overhang', roof.get('overhang', 0))


def pitch_of(roof, i):
    """The edge's effective pitch, as a Fraction rise / run, or None."""
    e = edge(roof, i)
    p = e.get('pitch', roof.get('pitch'))
    return None if p is None else F(p['rise'], p['run'])


def kinds(roof):
    """'gable', 'sloped' or 'level', edge by edge (16.2)."""
    out = []
    for i in range(len(roof['footprint'])):
        if edge(roof, i).get('gable', False):
            out.append('gable')
        elif pitch_of(roof, i) is not None:
            out.append('sloped')
        else:
            out.append('level')
    return out


def eave(doc, roof) -> int:
    lvl = doc.levels[roof['level']]
    return lvl['elevation'] + roof.get('height', lvl['height'])


def roof_kind(ks) -> str:
    if all(k == 'level' for k in ks):
        return 'flat'
    n = ks.count('sloped')
    if n == 1:
        return 'shed'
    return 'gable' if 'gable' in ks else 'hip'


# ------------------------------------------------------------------------------ the eave outline (16.3)

def _dir(a, b):
    return (b[0] - a[0], b[1] - a[1])


def collinear_vertex(fp) -> bool:
    n = len(fp)
    return any(plane.cross(_dir(fp[i - 1], fp[i]), _dir(fp[i], fp[(i + 1) % n])) == 0 for i in range(n))


def eave_outline(roof):
    """16.3: every edge of the footprint moved away from its inside by its overhang, each vertex the
    intersection of the moved lines of its two edges, rounded once - in the footprint's order - or None
    when it does not fit (FS-INV-805). The footprint has no collinear vertex (FS-INV-804)."""
    fp = footprint(roof)
    n = len(fp)
    ccw = 1 if plane.area2(fp) > 0 else -1

    def line(i):
        a, b = fp[i], fp[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        nx, ny = -dy, dx                                    # left normal: inward when counter-clockwise
        D = dx * dx + dy * dy
        return nx, ny, Surd(nx * a[0] + ny * a[1]) + Surd.sqrt(D, -ccw * overhang(roof, i))
    lines = [line(i) for i in range(n)]
    out = []
    for i in range(n):
        x, y = LevelGraph.intersect(lines[i - 1], lines[i])
        out.append((x.round(), y.round()))
    for i in range(n):
        e = _dir(fp[i], fp[(i + 1) % n])
        m = _dir(out[i], out[(i + 1) % n])
        if plane.dot(e, m) <= 0:
            return None
    if not plane.is_simple(out) or plane.sgn(plane.area2(out)) != ccw:
        return None
    return out


# ------------------------------------------------------------------------------ invariants

def invariants(doc, diag):
    """FS-INV-801 to FS-INV-805, for every roof (10.3); FS-INV-805 not for a roof with FS-INV-804."""
    ds = []
    for rid in sorted(doc.roofs):
        r = doc.roofs[rid]
        n = len(r['footprint'])
        if any(int(k) >= n for k in r.get('edges', {})):
            ds.append(diag('FS-INV-801', [rid]))
        ks = kinds(r)
        if 'level' in ks and any(k != 'level' for k in ks):
            ds.append(diag('FS-INV-802', [rid]))
        elif all(k == 'gable' for k in ks):
            ds.append(diag('FS-INV-803', [rid]))
        if collinear_vertex(footprint(r)):
            ds.append(diag('FS-INV-804', [rid]))
        elif eave_outline(r) is None:
            ds.append(diag('FS-INV-805', [rid]))
    return ds


# ------------------------------------------------------------------------------ the supported class (16.4)

def rectilinear(ring) -> bool:
    n = len(ring)
    return all(ring[i][0] == ring[(i + 1) % n][0] or ring[i][1] == ring[(i + 1) % n][1] for i in range(n))


class Outline:
    """The eave outline walked counter-clockwise, each edge with its index in the footprint."""

    def __init__(self, outline, ks):
        n = len(outline)
        if plane.area2(outline) > 0:
            self.ring = list(outline)
            self.index = list(range(n))                  # ring edge j -> footprint edge
        else:
            self.ring = outline[::-1]
            self.index = [(n - 2 - j) % n for j in range(n)]
        self.n = n
        self.kind = [ks[i] for i in self.index]

    def seg(self, j):
        return self.ring[j], self.ring[(j + 1) % self.n]


def method(roof, outline):
    """'flat', 'shed', 'skeleton' - or None when this draft does not derive the roof's surface (16.4)."""
    ks = kinds(roof)
    if all(k == 'level' for k in ks):
        return 'flat'
    o = Outline(outline, ks)
    sloped = [j for j in range(o.n) if o.kind[j] == 'sloped']
    if len(sloped) == 1:
        a, b = o.seg(sloped[0])
        nrm = (-(b[1] - a[1]), b[0] - a[0])
        return 'shed' if all(plane.dot(nrm, plane.sub(v, a)) >= 0 for v in o.ring) else None
    if len({pitch_of(roof, o.index[j]) for j in sloped}) != 1:
        return None
    if not rectilinear(o.ring):
        return None
    segs = [_seg(o, j) for j in sloped]
    for j in range(o.n):
        if o.kind[j] != 'gable':
            continue
        if o.kind[j - 1] != 'sloped' or o.kind[(j + 1) % o.n] != 'sloped':
            return None
        a, b = o.seg(j)
        if (plane.cross(_dir(o.ring[j - 1], a), _dir(a, b)) <= 0
                or plane.cross(_dir(a, b), _dir(b, o.ring[(j + 2) % o.n])) <= 0):
            return None
        if any(_meets_open_rect(s, _clearance(a, b)) for s in segs):
            return None
    return 'skeleton'


def _clearance(a, b):
    """The open rectangle outside the gable edge a -> b (the outline counter-clockwise, so outside is its
    right), as deep as half its length: (x0, x1, y0, y1)."""
    d = _dir(a, b)
    out = (d[1], -d[0])                                  # the right normal, as long as the edge
    far = [(p[0] + F(out[0], 2), p[1] + F(out[1], 2)) for p in (a, b)]
    xs = [a[0], b[0]] + [p[0] for p in far]
    ys = [a[1], b[1]] + [p[1] for p in far]
    return min(xs), max(xs), min(ys), max(ys)


def _meets_open_rect(s, rect):
    x0, x1, y0, y1 = rect
    if s.o == 'v':
        return x0 < s.c < x1 and s.lo < y1 and s.hi > y0
    return y0 < s.c < y1 and s.lo < x1 and s.hi > x0


# ------------------------------------------------------------------------------ sloped edges of a rectilinear outline

class Seg:
    """An axis-parallel sloped edge: orientation 'h' (y = c) or 'v' (x = c), extent [lo, hi] along it,
    and s, the sign of its inward normal (+1 towards +y or +x)."""
    __slots__ = ('o', 'c', 'lo', 'hi', 's', 'index', 'j')

    def __init__(self, o, c, lo, hi, s, index, j):
        self.o, self.c, self.lo, self.hi, self.s, self.index, self.j = o, c, lo, hi, s, index, j


def _seg(o: Outline, j):
    a, b = o.seg(j)
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dy == 0:
        return Seg('h', a[1], min(a[0], b[0]), max(a[0], b[0]), 1 if dx > 0 else -1, o.index[j], j)
    return Seg('v', a[0], min(a[1], b[1]), max(a[1], b[1]), -1 if dy > 0 else 1, o.index[j], j)


# Symbolic numbers a + b*eps, as tuples (a, b): exact, compared lexicographically.
ZERO = (F(0), F(0))


def _add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def _sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def _neg(p):
    return (-p[0], -p[1])


def _half(p):
    return (p[0] / 2, p[1] / 2)


def _abs(p):
    return _neg(p) if p < ZERO else p


def _k(v):
    return (F(v), F(0))


def _along(P, s: Seg):
    """How far P's foot on the edge's line lies beyond the edge: 0 within it."""
    u = P[1] if s.o == 'v' else P[0]
    return max(_sub(_k(s.lo), u), ZERO, _sub(u, _k(s.hi)))


def _perp(P, s: Seg):
    """The signed distance of P from the edge's line, positive inwards."""
    u = P[0] if s.o == 'v' else P[1]
    d = _sub(u, _k(s.c))
    return d if s.s > 0 else _neg(d)


def _cheb(P, s: Seg):
    """d_inf(P, e): the Chebyshev distance from P to the edge."""
    return max(_abs(_perp(P, s)), _along(P, s))


def rise_distance(P, segs):
    return min(_cheb(P, s) for s in segs)


def label(P, segs):
    """16.4.3: the sloped edge whose face P is in - perp = h, along <= perp, least along - or None on a
    boundary between faces."""
    h = rise_distance(P, segs)
    cands = sorted((_along(P, s), s.j) for s in segs if _perp(P, s) == h and _along(P, s) <= h)
    if not cands or (len(cands) > 1 and cands[0][0] == cands[1][0]):
        return None
    return cands[0][1]


def _seams(segs, o):
    """Midpoints between the facing ends of consecutive collinear sloped edges that face the same way:
    the x-values of the seams of horizontal edges, and the y-values of those of vertical ones."""
    groups = defaultdict(list)
    for s in segs:
        groups[(s.o, s.c, s.s)].append(s)
    xs, ys = set(), set()
    for (orient, _, _), g in groups.items():
        g.sort(key=lambda s: s.lo)
        for a, b in zip(g, g[1:]):
            (xs if orient == 'h' else ys).add(F(a.hi + b.lo, 2))
    return xs, ys


def _inside(P, ring):
    """A symbolic point strictly inside a rectilinear ring (it is never on one of its lines)."""
    px, py = P
    w = 0
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        if a[0] != b[0]:
            continue
        lo, hi = min(a[1], b[1]), max(a[1], b[1])
        if _k(a[0]) > px and _k(lo) < py < _k(hi):
            w += 1
    return w % 2 == 1


def _times(values, moving):
    """Every t > 0 at which two of the lines v (still) and m +- t (moving) cross."""
    out = set()
    allv = list(values)
    for m in moving:
        for v in allv:
            if v != m:
                out.add(abs(F(v) - F(m)))
        for m2 in moving:
            if m2 > m:
                out.add(F(m2 - m, 2))
    return out


def skeleton(o: Outline):
    """The faces of an equal-pitch roof on a rectilinear outline: {footprint edge index: [rings of exact
    plan points, counter-clockwise]}, and the exact rise distance at a point (16.4.3)."""
    segs = [_seg(o, j) for j in range(o.n) if o.kind[j] == 'sloped']
    by_j = {s.j: s for s in segs}
    gables = [_seg(o, j) for j in range(o.n) if o.kind[j] == 'gable']
    Xs = sorted({p[0] for p in o.ring})
    Ys = sorted({p[1] for p in o.ring})
    sx, sy = _seams(segs, o)
    times = sorted(_times(set(Xs) | sx, Xs) | _times(set(Ys) | sy, Ys))
    x0, x1, y0, y1 = Xs[0], Xs[-1], Ys[0], Ys[-1]
    quads = defaultdict(list)                            # ring edge j -> trapezoids
    t = F(0)
    ti = 0
    while True:
        while ti < len(times) and times[ti] <= t:
            ti += 1
        nxt = times[ti] if ti < len(times) else None
        tau = (t, F(1))

        def grid(vals, seams):
            g = {_k(v) for v in vals} | {_k(v) for v in seams}
            for v in vals:
                g.add((v + t, F(1)))
                g.add((v - t, F(-1)))
            return sorted(g)
        gx = [v for v in grid(Xs, sx) if _k(x0) <= v <= _k(x1)]
        gy = [v for v in grid(Ys, sy) if _k(y0) <= v <= _k(y1)]
        W = set()
        for i in range(len(gx) - 1):
            cx = _half(_add(gx[i], gx[i + 1]))
            for k in range(len(gy) - 1):
                P = (cx, _half(_add(gy[k], gy[k + 1])))
                if _inside(P, o.ring) and rise_distance(P, segs) > tau:
                    W.add((i, k))
        if not W:
            break
        assert nxt is not None, 'the wavefront outlives every candidate time'
        sides = []                                        # (line, orient, j, p0, p1), W on the left
        for (i, k) in W:
            if (i - 1, k) not in W:
                sides.append(('v', gx[i], (gx[i], gy[k + 1]), (gx[i], gy[k]), +1))
            if (i + 1, k) not in W:
                sides.append(('v', gx[i + 1], (gx[i + 1], gy[k]), (gx[i + 1], gy[k + 1]), -1))
            if (i, k - 1) not in W:
                sides.append(('h', gy[k], (gx[i], gy[k]), (gx[i + 1], gy[k]), +1))
            if (i, k + 1) not in W:
                sides.append(('h', gy[k + 1], (gx[i + 1], gy[k + 1]), (gx[i], gy[k + 1]), -1))
        pieces = defaultdict(list)
        for orient, line, p0, p1, s in sides:
            mid = _half(_add(p0[1], p1[1])) if orient == 'v' else _half(_add(p0[0], p1[0]))
            if line[1] == 0 and any(g.o == orient and g.c == line[0] and g.s == s
                                    and _k(g.lo) <= mid <= _k(g.hi) for g in gables):
                continue                                  # on a gable: no face
            cands = [(max(_sub(_k(sg.lo), mid), ZERO, _sub(mid, _k(sg.hi))), sg.j)
                     for sg in segs if sg.o == orient and sg.s == s and (sg.c + s * t, F(s)) == line]
            assert cands, f'a side of the wavefront on no sloped edge: {orient} {line}'
            cands.sort()
            assert len(cands) == 1 or cands[0][0] != cands[1][0], 'a side on a seam'
            pieces[(orient, line, s, cands[0][1])].append((p0, p1))
        dt = nxt - t
        for (orient, line, s, j), ps in pieces.items():
            for p0, p1 in _chain(ps):
                def at(p, T):
                    return (p[0][0] + p[0][1] * T, p[1][0] + p[1][1] * T)
                q = plane.dedupe_cyclic([at(p0, 0), at(p1, 0), at(p1, dt), at(p0, dt)])
                if len(q) >= 3 and plane.area2(q) != 0:
                    assert plane.area2(q) > 0
                    quads[j].append(q)
        t = nxt
    for j, qs in quads.items():                           # self-check: 16.4.3 labels each trapezoid j
        for q in qs:
            c = (sum(p[0] for p in q) / len(q), sum(p[1] for p in q) / len(q))
            assert label((_k(c[0]), _k(c[1])), segs) == j, ('a trapezoid of the wrong face', j, q)
    verts = _VertexIndex(p for qs in quads.values() for q in qs for p in q)
    faces = {j: _union(qs, verts) for j, qs in quads.items()}
    return faces, segs, by_j


def _chain(ps):
    """Join consecutive collinear sides (the end of one the start of the next) into maximal pieces."""
    starts = {p0: p1 for p0, p1 in ps}
    ends = {p1 for _, p1 in ps}
    out = []
    for p0 in starts:
        if p0 in ends:
            continue
        q = p0
        while q in starts:
            q = starts[q]
        out.append((p0, q))
    assert sum(1 for _ in out) >= 1
    return out


class _VertexIndex:
    """Points indexed by the four directions every edge here runs in: x, y, x - y and x + y."""

    def __init__(self, points):
        self.by = [defaultdict(set) for _ in range(4)]
        for p in points:
            for k, key in enumerate(self._keys(p)):
                self.by[k][key].add(p)

    @staticmethod
    def _keys(p):
        return (p[0], p[1], p[0] - p[1], p[0] + p[1])

    def inside(self, a, b):
        """The indexed points strictly inside segment a-b, ordered from a to b."""
        d = (b[0] - a[0], b[1] - a[1])
        if d[0] == 0:
            k = 0
        elif d[1] == 0:
            k = 1
        elif d[0] == d[1]:
            k = 2
        else:
            assert d[0] == -d[1], d
            k = 3
        cand = self.by[k][self._keys(a)[k]]
        on = [p for p in cand if p != a and p != b and plane.in_open_segment(p, a, b)]
        return sorted(on, key=lambda p: (p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1])


def _atomic(ring, verts):
    out = []
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        pts = [a] + verts.inside(a, b) + [b]
        out.extend(zip(pts, pts[1:]))
    return out


def _union(polys, verts):
    """The union of interior-disjoint counter-clockwise polygons, as its boundary cycles (rings of atomic
    vertices), each counter-clockwise."""
    count = defaultdict(int)
    for q in polys:
        for e in _atomic(q, verts):
            count[e] += 1
    out = defaultdict(list)
    for (a, b), k in count.items():
        net = k - count.get((b, a), 0)
        assert net <= 1
        if net == 1:
            out[a].append(b)
    rings = []
    while out:
        start = next(iter(out))
        ring = [start]
        prev = None
        cur = start
        while True:
            nxts = out[cur]
            if len(nxts) == 1:
                nb = nxts[0]
            else:                                         # a pinch: the left-most turn keeps cycles apart
                din = _dir(prev, cur)
                nb = max(nxts, key=lambda w: _turn(din, _dir(cur, w)))
            nxts.remove(nb)
            if not nxts:
                del out[cur]
            prev, cur = cur, nb
            if cur == start:
                break
            ring.append(cur)
        assert plane.area2(ring) > 0, 'a face with a hole'
        rings.append(ring)
    return rings


class _turn:
    """The turn from din to dout, in (-180, 180] degrees, ordered exactly: max() is the left-most."""

    def __init__(self, din, dout):
        c, d = plane.cross(din, dout), plane.dot(din, dout)
        self.v = dout
        self.g = 1 if c > 0 or (c == 0 and d < 0) else (0 if c == 0 else -1)

    def __lt__(self, other):
        if self.g != other.g:
            return self.g < other.g
        return plane.cross(self.v, other.v) > 0


def lints(doc, diag):
    """FS-LINT-015: every roof whose surface this draft does not derive (16.4.4)."""
    return [diag('FS-LINT-015', [rid]) for rid in sorted(doc.roofs)
            if method(doc.roofs[rid], eave_outline(doc.roofs[rid])) is None]


# ------------------------------------------------------------------------------ derived values (16.5)

def _corners(ring):
    n = len(ring)
    return [ring[i] for i in range(n) if plane.cross(_dir(ring[i - 1], ring[i]), _dir(ring[i], ring[(i + 1) % n])) != 0]


def _least_first(ring):
    k = min(range(len(ring)), key=lambda i: ring[i])
    return ring[k:] + ring[:k]


def _dedupe(points):
    return plane.dedupe_cyclic([tuple(p) for p in points])


def _area(ring3):
    return plane.area_string(plane.area2([(p[0], p[1]) for p in ring3]))


def derive(doc) -> dict:
    """{roofs} of a valid document."""
    out = {}
    for rid in sorted(doc.roofs):
        r = doc.roofs[rid]
        ks = kinds(r)
        outline = eave_outline(r)
        e = eave(doc, r)
        ring = outline if plane.area2(outline) > 0 else outline[::-1]
        v = {'kind': roof_kind(ks), 'outline': [list(p) for p in plane.least_first(ring)], 'eave': e}
        m = method(r, outline)
        v['surface'] = None if m is None else _surface(r, outline, ks, e, m)
        out[rid] = v
    return {'roofs': out}


def _surface(r, outline, ks, e, m):
    o = Outline(outline, ks)
    faces, gables, lines = [], [], []
    if m == 'flat':
        poly = [[p[0], p[1], e] for p in o.ring]
        faces.append({'polygon': _out_ring(poly), 'area': _area(poly)})
        zs = [Surd(e)]
    elif m == 'shed':
        j = next(j for j in range(o.n) if o.kind[j] == 'sloped')
        a, b = o.seg(j)
        k = pitch_of(r, o.index[j])
        nrm = (-(b[1] - a[1]), b[0] - a[0])
        D = plane.dot(nrm, nrm)

        def z(p):
            return Surd(e) + Surd.sqrt(D, k * plane.dot(nrm, plane.sub(p, a)) / D)
        poly = [[p[0], p[1], z(p).round()] for p in o.ring]
        faces.append({'edge': o.index[j], 'polygon': _out_ring(poly), 'area': _area(poly)})
        zs = [z(p) for p in o.ring]
        for g in range(o.n):
            if o.kind[g] == 'gable':
                ga, gb = o.seg(g)
                gables.append(_gable(o.index[g], ga, gb, [ga, gb], lambda p: z(p).round(), e))
    else:
        k = pitch_of(r, o.index[next(j for j in range(o.n) if o.kind[j] == 'sloped')])
        rings, segs, by_j = skeleton(o)

        def zx(p):
            return F(e) + k * _rise(p, segs)

        def zr(p):
            return Surd(zx(p)).round()
        nodes = set(o.ring)
        clean = {}
        for j, rs in rings.items():
            clean[j] = []
            for rg in rs:
                c = _corners(rg)
                nodes.update(c)
                clean[j].append(rg)
        for j in sorted(clean, key=lambda j: o.index[j]):
            for rg in clean[j]:
                kept = [p for p in rg if p in nodes]
                poly = [[Surd(p[0]).round(), Surd(p[1]).round(), zr(p)] for p in kept]
                poly = _dedupe(poly)
                if len(poly) >= 3:                        # a face narrower than a base unit can round away
                    faces.append({'edge': o.index[j], 'polygon': _out_ring(poly), 'area': _area(poly)})
        zs = [Surd(zx(p)) for rs in rings.values() for rg in rs for p in rg]
        allpts = [p for rs in rings.values() for rg in rs for p in rg]
        for g in range(o.n):
            if o.kind[g] == 'gable':
                ga, gb = o.seg(g)
                on = [p for p in set(allpts) if p in nodes and plane.on_closed_segment(p, ga, gb)]
                gables.append(_gable(o.index[g], ga, gb, on, zr, e))
        lines = _lines(rings, segs, by_j, zr)
    faces.sort(key=lambda f: (f.get('edge', -1), f['polygon'][0]))
    gables.sort(key=lambda g: g['edge'])
    high = max(zs).round()
    xs = [p[0] for p in o.ring]
    ys = [p[1] for p in o.ring]
    box = {'min': [min(xs), min(ys), e - r.get('thickness', 0)], 'max': [max(xs), max(ys), high]}
    return {'high': high, 'box': box, 'faces': faces, 'gables': gables, 'lines': lines}


def _rise(p, segs):
    """The exact rise distance at an exact plan point."""
    return rise_distance((_k(p[0]), _k(p[1])), segs)[0]


def _out_ring(poly):
    return [list(p) for p in _least_first([tuple(p) for p in poly])]


def _gable(index, a, b, on, zr, e):
    """16.5: the gable end above edge a -> b - from a to b at the eave, then back along the roof."""
    d = _dir(a, b)
    on = sorted(on, key=lambda p: -((p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1]))
    pts = [[a[0], a[1], e], [b[0], b[1], e]] + [[Surd(p[0]).round(), Surd(p[1]).round(), zr(p)] for p in on]
    return {'edge': index, 'polygon': [list(p) for p in _dedupe(pts)]}


def _lines(rings, segs, by_j, zr):
    """16.5: the ridges, hips and valleys - every boundary between the faces of two edges that are not
    collinear, merged where it runs straight."""
    owner = {}
    for j, rs in rings.items():
        for rg in rs:
            n = len(rg)
            for i in range(n):
                owner[(rg[i], rg[(i + 1) % n])] = j
    pairs = defaultdict(list)
    for (a, b), j in owner.items():
        f = owner.get((b, a))
        if f is None or f == j:
            continue
        se, sf = by_j[j], by_j[f]
        if se.o == sf.o and se.c == sf.c and se.s == sf.s:
            continue                                      # a seam between coplanar faces
        if j < f:
            pairs[(j, f)].append((a, b))
    out = []
    for (j, f), es in pairs.items():
        for a, b in _merge(es):
            se, sf = by_j[j], by_j[f]
            ne = (se.s, 0) if se.o == 'v' else (0, se.s)
            nf = (sf.s, 0) if sf.o == 'v' else (0, sf.s)
            d = _dir(a, b)
            w = (-d[1], d[0])                             # into face j, on the left of a -> b
            za, zb = zr(a), zr(b)
            ex_a, ex_b = _rise(a, segs), _rise(b, segs)
            if ex_a == ex_b:
                kind = 'ridge'
            else:
                kind = 'hip' if plane.dot(plane.sub(nf, ne), w) > 0 else 'valley'
            p = [Surd(a[0]).round(), Surd(a[1]).round(), za]
            q = [Surd(b[0]).round(), Surd(b[1]).round(), zb]
            p, q = sorted([p, q])
            out.append({'kind': kind, 'from': p, 'to': q})
    out.sort(key=lambda x: (x['from'], x['to']))
    return out


def _merge(es):
    """Join atomic segments that continue one another in a straight line."""
    nxt = dict(es)
    ends = {b for _, b in es}
    out = []
    for a in nxt:
        if a in ends:
            continue
        path = [a]
        while path[-1] in nxt:
            path.append(nxt[path[-1]])
        start = path[0]
        for i in range(1, len(path) - 1):
            if plane.cross(_dir(path[i - 1], path[i]), _dir(path[i], path[i + 1])) != 0:
                out.append((start, path[i]))
                start = path[i]
        out.append((start, path[-1]))
    return out

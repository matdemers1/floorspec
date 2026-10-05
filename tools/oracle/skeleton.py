"""The weighted straight skeleton of a roof (Core 0.4, 16.4.3 to 16.4.6): the surface of every roof with two or
more sloped edges, each of them at its own pitch, and gables standing still among them.

Every quantity is an exact rational (fractions.Fraction); nothing is a float and nothing is rounded until the
derived values are written (16.5). Time is elevation above the eave, t = z - eave. Sloped edge e, of direction
d = B - A on the counter-clockwise eave outline, inward normal n = (-d.y, d.x) and length L = |n|, an integer
(16.4.3), at pitch rise : run, moves on the line

    n . P = n . A + w t,   w = L * run / rise           (its plane: z = eave + (rise / run) (n . P - n . A) / L)

and a gable has w = 0: it stands still. The wavefront at t is a set of simple polygons, each a cycle of wavefront
edges; each wavefront edge carries the set of eave edges whose plane it lies in (one, or several that share a
plane), and a vertex is the meeting point of its two edges' lines, which moves linearly with t.

The propagation (16.4.4) runs from t = 0: between two event elevations the wavefront keeps its form and each
moving wavefront edge sweeps a trapezoid of its face; at the next event elevation - the least t greater than the
current one at which a wavefront edge reaches no length or a vertex reaches a wavefront edge that does not end at
it - every event at that elevation is resolved at once, from the wavefront's position there: the new wavefront is
the boundary of its interior (atomic segments counted with direction; those covered once in each direction are
dropped), traced with the left-most turn at a point it meets more than once (the standard resolution of Biedl et
al., the only valid one for weights that are not negative), with consecutive collinear wavefront edges that face
the same way replaced by those of them that move fastest - the least pitch - which take their whole length (the
"faster edge wins" resolution of Biedl et al. 2015, 4.1) and, when several move equally fast, share one plane.

A roof is not derived (16.4.6) when, at any elevation, a wavefront polygon has no moving edge, or a gable's
wavefront edge would grow. Those raise Unsupported.

The faces are the unions of the swept trapezoids by plane; the face of a plane shared by several collinear eave
edges is divided between them as 0.3 divides it, by the least distance along their line (16.4.5).
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as F
from math import gcd, isqrt

from . import plane


class Unsupported(Exception):
    """The roof's surface is not derived (16.4.6); the argument says why."""


def _dir(a, b):
    return (b[0] - a[0], b[1] - a[1])


class WEdge:
    """A wavefront edge: its line at elevation t is n . P = c + w t. `labels` are the eave edges (indices on the
    counter-clockwise ring) whose plane it lies in; s is its speed in plan, run / rise, or 0 for a gable."""
    __slots__ = ('labels', 'n', 'c', 'w', 's')

    def __init__(self, labels, n, c, w, s):
        self.labels, self.n, self.c, self.w, self.s = frozenset(labels), n, c, w, s

    def d(self):
        return (self.n[1], -self.n[0])


def _det(a, b):
    return a.n[0] * b.n[1] - a.n[1] * b.n[0]


def meet(a: WEdge, b: WEdge, t):
    """The point where the lines of a and b meet at elevation t."""
    det = _det(a, b)
    ca, cb = a.c + a.w * t, b.c + b.w * t
    return (F(ca * b.n[1] - cb * a.n[1], 1) / det, F(a.n[0] * cb - b.n[0] * ca, 1) / det)


def velocity(a: WEdge, b: WEdge):
    det = _det(a, b)
    return (F(a.w * b.n[1] - b.w * a.n[1], 1) / det, F(a.n[0] * b.w - b.n[0] * a.w, 1) / det)


def verts(poly, t):
    m = len(poly)
    return [meet(poly[i - 1], poly[i], t) for i in range(m)]


def _vels(poly):
    m = len(poly)
    return [velocity(poly[i - 1], poly[i]) for i in range(m)]


# ------------------------------------------------------------------------------ the eave edges (16.4.3)

def eave_edges(ring, kinds, pitches):
    """One wavefront edge per edge of the counter-clockwise eave outline. A sloped edge whose length is not an
    integer is not derived (16.4.6)."""
    out = []
    for j in range(len(ring)):
        a, b = ring[j], ring[(j + 1) % len(ring)]
        d = _dir(a, b)
        n = (-d[1], d[0])
        c = plane.dot(n, a)
        if kinds[j] == 'sloped':
            D = d[0] * d[0] + d[1] * d[1]
            L = isqrt(D)
            if L * L != D:
                raise Unsupported('a sloped edge whose length is irrational')
            k = pitches[j]
            out.append(WEdge({j}, n, c, F(L) / k, 1 / k))
        else:
            out.append(WEdge({j}, n, c, F(0), F(0)))
    return out


# ------------------------------------------------------------------------------ the propagation (16.4.4)

def check(polys, t):
    """16.4.6: no wavefront polygon without a moving edge, and no end of a gable's wavefront edge that moves away
    from its other end."""
    for poly in polys:
        if all(e.w == 0 for e in poly):
            raise Unsupported('a part of the outline enclosed by gables')
        u = _vels(poly)
        m = len(poly)
        for i, e in enumerate(poly):
            if e.w == 0 and (plane.dot(u[i], e.d()) < 0 or plane.dot(u[(i + 1) % m], e.d()) > 0):
                raise Unsupported('a gable whose wavefront edge would grow')


def next_event(polys, t):
    """The least elevation greater than t at which a wavefront edge reaches no length, or a vertex reaches a
    wavefront edge of its polygon that does not end at it; None when there is none."""
    best = None

    def offer(x):
        nonlocal best
        if x > t and (best is None or x < best):
            best = x
    for poly in polys:
        m = len(poly)
        V, U = verts(poly, t), _vels(poly)
        for i, e in enumerate(poly):
            d = e.d()
            l0 = plane.dot(plane.sub(V[(i + 1) % m], V[i]), d)
            ld = plane.dot(plane.sub(U[(i + 1) % m], U[i]), d)
            if ld < 0:
                offer(t + l0 / -ld)
            for j in range(m):
                if j == i or j == (i + 1) % m:
                    continue
                f0 = plane.dot(e.n, V[j]) - (e.c + e.w * t)
                fd = plane.dot(e.n, U[j]) - e.w
                if f0 == 0 or fd == 0 or (f0 > 0) == (fd > 0):
                    continue
                x = t + f0 / -fd
                P = (V[j][0] + U[j][0] * (x - t), V[j][1] + U[j][1] * (x - t))
                A = (V[i][0] + U[i][0] * (x - t), V[i][1] + U[i][1] * (x - t))
                B = (V[(i + 1) % m][0] + U[(i + 1) % m][0] * (x - t), V[(i + 1) % m][1] + U[(i + 1) % m][1] * (x - t))
                if plane.on_closed_segment(P, A, B):
                    offer(x)
    return best


def _turn_key(din, dout):
    """Orders outgoing directions so that max() is the left-most turn from din (as roofs._turn)."""
    c, d = plane.cross(din, dout), plane.dot(din, dout)
    g = 1 if c > 0 or (c == 0 and d < 0) else (0 if c == 0 else -1)
    return _Turn(g, dout)


class _Turn:
    __slots__ = ('g', 'v')

    def __init__(self, g, v):
        self.g, self.v = g, v

    def __lt__(self, other):
        if self.g != other.g:
            return self.g < other.g
        return plane.cross(self.v, other.v) > 0


def resolve(poly, t):
    """16.4.4: every event of one wavefront polygon at elevation t, at once - the polygons that bound the interior
    of its position at t, each a cycle of wavefront edges."""
    m = len(poly)
    V = verts(poly, t)
    pts = set(V)
    fwd = defaultdict(list)
    for i in range(m):
        a, b = V[i], V[(i + 1) % m]
        if a == b:
            continue
        d = _dir(a, b)
        inner = sorted((p for p in pts if plane.in_open_segment(p, a, b)),
                       key=lambda p: plane.dot(plane.sub(p, a), d))
        chain = [a] + inner + [b]
        for p, q in zip(chain, chain[1:]):
            fwd[(p, q)].append(poly[i])
    segs = []
    for (a, b), es in fwd.items():
        back = fwd.get((b, a), [])
        assert len(es) == 1 and len(back) <= 1, 'the wavefront covers a segment more than once each way'
        if not back:
            segs.append((a, b, es[0]))
    cycles = [[(a, b, e) for a, b, e in c] for c in trace(segs)]
    return [c for c in (_cycle_edges(cyc, t) for cyc in cycles) if c]


def trace(segs):
    """Directed segments (a, b, payload), interior on their left, as boundary cycles: at a point where the boundary
    meets itself, each arriving segment continues along the left-most turn, which keeps the interior's sectors
    apart (the standard resolution). Cycles start at their least segment."""
    outs = defaultdict(list)
    for s in segs:
        outs[s[0]].append(s)
    succ = {}
    for s in segs:
        din = _dir(s[0], s[1])
        cands = outs[s[1]]
        succ[id(s)] = cands[0] if len(cands) == 1 else max(cands, key=lambda c: _turn_key(din, _dir(c[0], c[1])))
    assert len({id(v) for v in succ.values()}) == len(segs), 'the boundary does not trace'
    seen = set()
    cycles = []
    for s in sorted(segs, key=lambda s: (s[0], s[1])):
        if id(s) in seen:
            continue
        cyc, cur = [], s
        while id(cur) not in seen:
            seen.add(id(cur))
            cyc.append(cur)
            cur = succ[id(cur)]
        assert cur is s
        cycles.append(cyc)
    return cycles


def _cycle_edges(cyc, t):
    """A traced cycle as wavefront edges: segments of one wavefront edge joined, and every maximal run of
    consecutive collinear edges that face the same way replaced by the fastest of them (16.4.4)."""
    k = len(cyc)
    s = next((i for i in range(k) if cyc[i][2] is not cyc[i - 1][2]), None)
    if s is None:
        return None
    cyc = cyc[s:] + cyc[:s]
    es = []
    for _, _, e in cyc:
        if not es or es[-1] is not e:
            es.append(e)
    if es[0] is es[-1] and len(es) > 1:
        es.pop()

    def same_way(a, b):
        return plane.cross(a.n, b.n) == 0 and plane.dot(a.n, b.n) > 0
    k = len(es)
    if all(same_way(es[i - 1], es[i]) for i in range(k)):
        return None
    s = next(i for i in range(k) if not same_way(es[i - 1], es[i]))
    es = es[s:] + es[:s]
    runs = [[es[0]]]
    for e in es[1:]:
        if same_way(runs[-1][-1], e):
            runs[-1].append(e)
        else:
            runs.append([e])
    out = []
    for r in runs:
        if len(r) == 1:
            out.append(r[0])
            continue
        top = max(e.s for e in r)
        fast = [e for e in r if e.s == top]
        rep = min(fast, key=lambda e: min(e.labels))
        out.append(WEdge(frozenset().union(*(e.labels for e in fast)), rep.n, rep.c, rep.w, rep.s))
    if len(out) < 3:
        return None
    pts = [p for p, _, _ in cyc]
    for i in range(len(out)):
        assert meet(out[i - 1], out[i], t) in pts, 'a resolved vertex off the traced boundary'
    return out


def propagate(edges):
    """16.4.4 from t = 0: the trapezoids the moving wavefront edges sweep, as (labels, ring of exact points,
    counter-clockwise)."""
    polys = [list(edges)]
    t = F(0)
    traps = []
    guard = 0
    while polys:
        check(polys, t)
        nt = next_event(polys, t)
        assert nt is not None, 'a wavefront with no next event'
        for poly in polys:
            A, B = verts(poly, t), verts(poly, nt)
            m = len(poly)
            for i, e in enumerate(poly):
                if e.w == 0:
                    continue
                q = plane.dedupe_cyclic([A[i], A[(i + 1) % m], B[(i + 1) % m], B[i]])
                if len(q) >= 3 and plane.area2(q) != 0:
                    assert plane.area2(q) > 0, 'a trapezoid swept backwards'
                    traps.append((e.labels, q))
        polys = [p for poly in polys for p in resolve(poly, nt)]
        t = nt
        guard += 1
        assert guard < 100000, 'the propagation does not end'
    return traps


# ------------------------------------------------------------------------------ faces (16.4.5)

def _prim(v):
    g = gcd(abs(v[0]), abs(v[1]))
    return (v[0] // g, v[1] // g)


def plane_key(ring, j, pitch):
    """Two sloped edges share a plane when they lie on one line, face the same way, and have one pitch."""
    a = ring[j]
    n = _prim((-(ring[(j + 1) % len(ring)][1] - a[1]), ring[(j + 1) % len(ring)][0] - a[0]))
    return (n, plane.dot(n, a), pitch)


def _clip(poly, d, lo, hi):
    """A convex polygon cut to lo <= d . P <= hi (either bound None for none), exactly."""
    def cut(pts, f):
        out = []
        m = len(pts)
        for i in range(m):
            p, q = pts[i], pts[(i + 1) % m]
            fp, fq = f(p), f(q)
            if fp >= 0:
                out.append(p)
            if (fp > 0 and fq < 0) or (fp < 0 and fq > 0):
                r = fp / (fp - fq)
                out.append((p[0] + (q[0] - p[0]) * r, p[1] + (q[1] - p[1]) * r))
        return out
    pts = list(poly)
    if lo is not None:
        pts = cut(pts, lambda p: plane.dot(d, p) - lo)
    if hi is not None and pts:
        pts = cut(pts, lambda p: hi - plane.dot(d, p))
    pts = plane.dedupe_cyclic(pts)
    return pts if len(pts) >= 3 and plane.area2(pts) > 0 else None


def faces(ring, kinds, pitches, traps):
    """{ring edge j: [rings of exact points, counter-clockwise]}: the trapezoids united by plane, each plane shared
    by several collinear edges divided between them by the least distance along their line (16.4.5)."""
    sloped = [j for j in range(len(ring)) if kinds[j] == 'sloped']
    key = {j: plane_key(ring, j, pitches[j]) for j in sloped}
    classes = defaultdict(list)
    for j in sloped:
        classes[key[j]].append(j)
    pieces = defaultdict(list)
    for labels, q in traps:
        k = key[min(labels)]
        assert all(key[x] == k for x in labels)
        members = classes[k]
        if len(members) == 1:
            pieces[members[0]].append(q)
            continue
        n = k[0]
        d = (n[1], -n[0])
        span = {}
        for j in members:
            a, b = ring[j], ring[(j + 1) % len(ring)]
            span[j] = sorted((plane.dot(d, a), plane.dot(d, b)))
        members = sorted(members, key=lambda j: span[j][0])
        seams = [F(span[a][1] + span[b][0], 2) for a, b in zip(members, members[1:])]
        for i, j in enumerate(members):
            lo = seams[i - 1] if i > 0 else None
            hi = seams[i] if i < len(seams) else None
            c = _clip(q, d, lo, hi)
            if c is not None:
                pieces[j].append(c)
    index = _Index([p for qs in pieces.values() for q in qs for p in q])
    return {j: _union(qs, index) for j, qs in pieces.items()}


class _Index:
    """Points, found by the line a segment lies on."""

    def __init__(self, points):
        self.points = list(dict.fromkeys(points))
        self.by = {}

    def inside(self, a, b):
        d = _dir(a, b)
        den = 1
        for v in d:
            den = den * v.denominator // gcd(den, v.denominator) if isinstance(v, F) else den
        di = _prim((int(d[0] * den), int(d[1] * den)))
        if di[0] < 0 or (di[0] == 0 and di[1] < 0):
            di = (-di[0], -di[1])
        tab = self.by.get(di)
        if tab is None:
            tab = defaultdict(list)
            for p in self.points:
                tab[plane.cross(di, p)].append(p)
            self.by[di] = tab
        on = [p for p in tab.get(plane.cross(di, a), []) if plane.in_open_segment(p, a, b)]
        return sorted(on, key=lambda p: plane.dot(plane.sub(p, a), d))


def _union(polys, index):
    count = defaultdict(int)
    for q in polys:
        n = len(q)
        for i in range(n):
            a, b = q[i], q[(i + 1) % n]
            chain = [a] + index.inside(a, b) + [b]
            for p, r in zip(chain, chain[1:]):
                count[(p, r)] += 1
    segs = []
    for (a, b), k in count.items():
        net = k - count.get((b, a), 0)
        assert net <= 1, 'faces overlap'
        if net == 1:
            segs.append((a, b, None))
    rings = []
    for cyc in trace(segs):
        ring = [a for a, _, _ in cyc]
        assert plane.area2(ring) > 0, 'a face with a hole'
        rings.append(ring)
    return rings


def skeleton(ring, kinds, pitches):
    """The faces of a roof with two or more sloped edges, or Unsupported (16.4.6)."""
    traps = propagate(eave_edges(ring, kinds, pitches))
    total = sum(plane.area2(q) for _, q in traps)
    assert total == plane.area2(ring), 'the faces do not cover the outline'
    return faces(ring, kinds, pitches, traps)

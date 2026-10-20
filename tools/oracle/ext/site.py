"""FS_site 0.1.0 (registry/FS_site/spec.md): its invariants, lints and derived values, written from the
extension's specification alone.

FS_site adds no kind of element and requires no other extension. It reads Core's site boundary (the
lot), slabs and junctions, and, of FS_lighting's, FS_views's and FS_annotation's data, only the IDs of
their scenes, views, dimension strings and notes, as they are (spec.md 1.3).

The surface (3.2) is the Delaunay triangulation of the survey positions made unique: here a sorted
incremental triangulation, Lawson flips on the exact in-circle test, then the Delaunay faces found by
joining triangles across every edge whose four points are exactly cocircular, each face fanned again
from its least vertex. Volumes (4.2) are exact Fractions: the outline clipped by each triangle and by
the zero line of the plane above the pad, one half-plane at a time, and the linear function integrated
from each piece's boundary."""

from __future__ import annotations

from fractions import Fraction
from functools import cmp_to_key
from math import isqrt

from .. import plane
from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_site', '0.1.0', 'SITE'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'site')
SEVERITY = {'FS-SITE-LINT-001': 'info', 'FS-SITE-LINT-002': 'warning', 'FS-SITE-LINT-003': 'info'}
GRADING_PURPOSES = ('patio', 'walkway', 'driveway', 'stoop', 'garage', 'equipmentPad')     # 4.1
RECORDS = ('spots', 'contours', 'pads')
OTHERS = (('FS_lighting', 'scenes'), ('FS_views', 'views'), ('FS_annotation', 'dimensions'), ('FS_annotation', 'notes'))


# ------------------------------------------------------------------------------ reading

def records(ctx: Context, member: str) -> dict:
    return ctx.data.get(member, {})


def read_as_data(ctx: Context) -> set:
    """1.3: the IDs of the other extensions' records, read as data."""
    out = set()
    for name, member in OTHERS:
        data = ctx.d.get('extensions', {}).get(name)
        s = data.get(member) if isinstance(data, dict) else None
        if isinstance(s, dict):
            out.update(s)
    return out


def lot(ctx: Context):
    """2.1: the site's boundary as tuples, or None."""
    b = ctx.d.get('site', {}).get('boundary')
    return None if b is None else [tuple(p) for p in b]


def survey(ctx: Context):
    """3.1: position -> {elevation: [record IDs]} of every survey point."""
    out = {}
    for sid, s in records(ctx, 'spots').items():
        out.setdefault(tuple(s['at']), {}).setdefault(s['elevation'], set()).add(sid)
    for cid, c in records(ctx, 'contours').items():
        for p in c['points']:
            out.setdefault(tuple(p), {}).setdefault(c['elevation'], set()).add(cid)
    return out


def grading_slabs(ctx: Context):
    """4.1: (ID, outline, elevation) of every slab whose purpose lays it on the ground."""
    levels = ctx.d.get('levels', {})
    for sid, s in sorted(ctx.d.get('slabs', {}).items()):
        if s.get('purpose') in GRADING_PURPOSES:
            bottom = levels[s['level']]['elevation'] + s.get('offset', 0) - s['thickness']
            yield sid, [tuple(p) for p in s['boundary']], bottom


def graded(ctx: Context):
    """4.1: (ID, kind, outline, elevation) of every graded outline, by ID."""
    out = [(sid, 'slab', ring, e) for sid, ring, e in grading_slabs(ctx)]
    out += [(pid, 'pad', [tuple(p) for p in p_['boundary']], p_['elevation']) for pid, p_ in records(ctx, 'pads').items()]
    return sorted(out)


# ------------------------------------------------------------------------------ the lot (2.2, 2.3)

def edge_kinds(n: int, setbacks) -> list:
    """2.2: each edge's kind, or None for every edge without setbacks."""
    if setbacks is None:
        return [None] * n
    street = set(setbacks['street'])
    out = []
    for i in range(n):
        if i in street:
            out.append('front')
        elif (i - 1) % n in street or (i + 1) % n in street:
            out.append('side')
        else:
            out.append('rear')
    return out


def round_sqrt(n: int) -> int:
    """round(sqrt(n)): never a tie, since (k + 1/2)^2 is never an integer."""
    return (isqrt(4 * n) + 1) // 2


def nearer_than(p, a, b, d: int) -> bool:
    """2.3: whether p is nearer than d to the closed segment ab, exactly."""
    v = (b[0] - a[0], b[1] - a[1])
    w = (p[0] - a[0], p[1] - a[1])
    t = w[0] * v[0] + w[1] * v[1]
    vv = v[0] * v[0] + v[1] * v[1]
    if t <= 0:
        return w[0] * w[0] + w[1] * w[1] < d * d
    if t >= vv:
        u = (p[0] - b[0], p[1] - b[1])
        return u[0] * u[0] + u[1] * u[1] < d * d
    c = v[0] * w[1] - v[1] * w[0]
    return c * c < d * d * vv


def clear(p, ring, setbacks_of) -> bool:
    """2.3: a point clear of the setbacks: in or on the lot, and at least each edge's setback from it."""
    if plane.locate(p, ring) == 'out':
        return False
    n = len(ring)
    for i in range(n):
        d = setbacks_of[i]
        if d is not None and d > 0 and nearer_than(p, ring[i], ring[(i + 1) % n], d):
            return False
    return True


# ------------------------------------------------------------------------------ the surface (3.2)

def orient(a, b, c) -> int:
    return plane.sgn((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def incircle(a, b, c, d) -> int:
    """3.2: > 0 when d is strictly inside the circle through a, b, c (counter-clockwise)."""
    rows = []
    for p in (a, b, c):
        x, y = p[0] - d[0], p[1] - d[1]
        rows.append((x, y, x * x + y * y))
    (a1, a2, a3), (b1, b2, b3), (c1, c2, c3) = rows
    return plane.sgn(a1 * (b2 * c3 - b3 * c2) - a2 * (b1 * c3 - b3 * c1) + a3 * (b1 * c2 - b2 * c1))


def triangulate(pts):
    """3.2: the surface's triangles, as index triples into pts (sorted distinct positions), each
    counter-clockwise from its least index, the list sorted; None when the positions are all on one line."""
    n = len(pts)
    if n < 3:
        return None
    k = 2
    while k < n and orient(pts[0], pts[1], pts[k]) == 0:
        k += 1
    if k == n:
        return None
    tris = set()

    def add(a, b, c):
        tris.add((a, b, c) if orient(pts[a], pts[b], pts[c]) > 0 else (a, c, b))

    for i in range(k - 1):                       # the fan from pts[k] to the collinear chain 0 .. k-1
        add(i, i + 1, k)
    # the hull, counter-clockwise, as a list of indices
    if orient(pts[0], pts[k - 1], pts[k]) > 0:
        hull = list(range(k)) + [k]
    else:
        hull = [k] + list(range(k - 1, -1, -1))
    for q in range(k + 1, n):
        m = len(hull)
        vis = [orient(pts[hull[i]], pts[hull[(i + 1) % m]], pts[q]) < 0 for i in range(m)]
        for i in range(m):
            if vis[i]:
                add(hull[i], hull[(i + 1) % m], q)
        # the visible edges form one run; replace its inner vertices by q
        start = next(i for i in range(m) if vis[i] and not vis[(i - 1) % m])
        end = start
        while vis[end % m]:
            end += 1
        hull = _splice(hull, start, end, q)
    tris = _lawson(pts, tris)
    return _canonical(pts, tris)


def _splice(hull, start, end, q):
    """The hull with the vertices strictly between hull[start] and hull[end] (going forward) replaced by q."""
    m = len(hull)
    out = [hull[(end + j) % m] for j in range(m - (end - start) + 1)]   # hull[end] ... hull[start]
    return out + [q]


def _edges(tris):
    """(a, b) -> the triangle with the directed edge a -> b."""
    out = {}
    for t in tris:
        for i in range(3):
            out[(t[i], t[(i + 1) % 3])] = t
    return out


def _lawson(pts, tris):
    tris = set(tris)
    changed = True
    while changed:
        changed = False
        edges = _edges(tris)
        for (a, b), t in sorted(edges.items()):
            if t not in tris or (b, a) not in edges:
                continue
            u = edges[(b, a)]
            if u not in tris:
                continue
            c = next(x for x in t if x not in (a, b))
            d = next(x for x in u if x not in (a, b))
            if incircle(pts[a], pts[b], pts[c], pts[d]) > 0:
                tris.discard(t)
                tris.discard(u)
                tris.add(_ccw(pts, (c, d, b)))
                tris.add(_ccw(pts, (d, c, a)))
                changed = True
                break
    return tris


def _ccw(pts, t):
    a, b, c = t
    return (a, b, c) if orient(pts[a], pts[b], pts[c]) > 0 else (a, c, b)


def _canonical(pts, tris):
    """Join triangles across exactly cocircular edges into the Delaunay faces; fan each from its least vertex."""
    tris = sorted(tris)
    parent = {t: t for t in tris}

    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    edges = _edges(tris)
    for (a, b), t in edges.items():
        u = edges.get((b, a))
        if u is None:
            continue
        c = next(x for x in t if x not in (a, b))
        d = next(x for x in u if x not in (a, b))
        if incircle(pts[a], pts[b], pts[c], pts[d]) == 0:
            parent[find(t)] = find(u)
    faces = {}
    for t in tris:
        faces.setdefault(find(t), []).append(t)
    out = []
    for group in faces.values():
        verts = sorted({v for t in group for v in t})
        # a face is convex: its vertices in counter-clockwise order about the least one
        v0 = min(verts, key=lambda i: pts[i])
        rest = [v for v in verts if v != v0]
        # sort by angle about v0: all lie in a half-plane (v0 is extreme), so the cross product orders them
        rest.sort(key=cmp_to_key(lambda i, j: -orient(pts[v0], pts[i], pts[j])))
        for i in range(len(rest) - 1):
            out.append(_norm((v0, rest[i], rest[i + 1])))
    return sorted(out)


def _norm(t):
    """A counter-clockwise triple, rotated to start at its least index."""
    k = t.index(min(t))
    return t[k:] + t[:k]


def surface(ctx: Context):
    """(points [(x, y, z)], triangles) or None (3.2)."""
    pts = sorted((x, y, min(e)) for (x, y), e in survey(ctx).items())
    tris = triangulate([(x, y) for x, y, _ in pts])
    return None if tris is None else (pts, tris)


def hull_of(pts, tris):
    """The hull's boundary edges (directed, counter-clockwise), from the triangles."""
    edges = _edges(tris)
    return [(pts[a], pts[b]) for (a, b) in edges if (b, a) not in edges]


def outside_hull(p, hull_edges) -> bool:
    return any(orient(a, b, p) < 0 for a, b in hull_edges)


# ------------------------------------------------------------------------------ cut and fill (4.2)

def _plane(t3):
    """(alpha, beta, gamma): z = alpha + beta x + gamma y through three points (x, y, z)."""
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = t3
    det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    beta = Fraction((z2 - z1) * (y3 - y1) - (z3 - z1) * (y2 - y1), det)
    gamma = Fraction((x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1), det)
    return z1 - beta * x1 - gamma * y1, beta, gamma


def _clip(poly, f):
    """Sutherland-Hodgman: the part of poly where the linear function f(p) >= 0."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = f(p), f(q)
        if fp >= 0:
            out.append(p)
        if (fp > 0 and fq < 0) or (fp < 0 and fq > 0):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def _integral(poly, alpha, beta, gamma):
    """The integral of alpha + beta x + gamma y over a polygon, signed by its winding."""
    A = Mx = My = Fraction(0)
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        A += c
        Mx += (x0 + x1) * c
        My += (y0 + y1) * c
    return alpha * A / 2 + beta * Mx / 6 + gamma * My / 6


def round_half_even(q: Fraction) -> int:
    return round(q)                                # Python's round of a Fraction is ties to even


def measure(ring, e, pts, tris):
    """(cut, fill, low, high) of an outline at elevation e, exactly: Fractions, and low/high or None."""
    ring = [(Fraction(x), Fraction(y)) for x, y in ring]
    if plane.area2([(int(x), int(y)) for x, y in ring]) < 0:
        ring = ring[::-1]
    cut = fill = Fraction(0)
    zs = []
    for t in tris:
        t3 = [pts[i] for i in t]
        piece = ring
        for i in range(3):
            a, b = t3[i], t3[(i + 1) % 3]
            piece = _clip(piece, lambda p, a=a, b=b: (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]))
            if not piece:
                break
        if not piece:
            continue
        alpha, beta, gamma = _plane(t3)
        h = lambda p: alpha + beta * p[0] + gamma * p[1] - e        # noqa: E731
        zs.extend(alpha + beta * p[0] + gamma * p[1] for p in piece)
        up = _clip(piece, h)
        if up:
            cut += _integral(up, alpha - e, beta, gamma)
        down = _clip(piece, lambda p: -h(p))
        if down:
            fill -= _integral(down, alpha - e, beta, gamma)
    if not zs:
        return cut, fill, None, None
    return cut, fill, min(zs), max(zs)


# ------------------------------------------------------------------------------ the rules

def invariants(ctx: Context):
    ds = []
    taken = ctx.space() | read_as_data(ctx)
    seen, bad = set(), set()
    for member in RECORDS:
        for rid in records(ctx, member):
            if rid in taken or rid in seen:
                bad.add(rid)
            seen.add(rid)
    ds.extend(ctx.diag('FS-SITE-INV-001', [rid]) for rid in sorted(bad))                # 1.3.2
    for p, by in survey(ctx).items():
        if len(by) > 1:                                                                    # 3.1.2
            ds.append(ctx.diag('FS-SITE-INV-002', sorted(set().union(*by.values()))))
    for cid, c in records(ctx, 'contours').items():
        if any(c['points'][i] == c['points'][i + 1] for i in range(len(c['points']) - 1)):
            ds.append(ctx.diag('FS-SITE-INV-003', [cid]))                                 # 3.1.1
    for pid, p_ in records(ctx, 'pads').items():
        ring = [tuple(p) for p in p_['boundary']]
        if not plane.is_simple(ring) or plane.area2(ring) == 0:
            ds.append(ctx.diag('FS-SITE-INV-004', [pid]))                                 # 4.1.1
    sb = ctx.data.get('setbacks')
    if sb is not None:
        ring = lot(ctx)
        if ring is None or any(i >= len(ring) for i in sb['street']):
            ds.append(ctx.diag('FS-SITE-INV-005'))                                        # 2.2.1
    return ds


def lints(ctx: Context):
    ds = []
    ring = lot(ctx)
    s = surface(ctx)
    if s is not None:
        hull = hull_of(*s)
        if ring is not None and any(outside_hull(p, hull) for p in ring):
            ds.append(ctx.diag('FS-SITE-LINT-001'))
        for gid, _, outline, _ in graded(ctx):
            if any(outside_hull(p, hull) for p in outline):
                ds.append(ctx.diag('FS-SITE-LINT-002', [gid]))
    sb = ctx.data.get('setbacks')
    if sb is not None:
        kinds = edge_kinds(len(ring), sb)
        dist = [sb.get(k) for k in kinds]
        things = [(jid, [tuple(j['position'])]) for jid, j in ctx.d.get('junctions', {}).items()]
        things += [(sid, [tuple(p) for p in sl['boundary']]) for sid, sl in ctx.d.get('slabs', {}).items()
                   if sl.get('purpose') not in ('walkway', 'driveway')]                       # 2.3
        things += [(pid, [tuple(p) for p in p_['boundary']]) for pid, p_ in records(ctx, 'pads').items()]
        for tid, points in things:
            if not all(clear(p, ring, dist) for p in points):
                ds.append(ctx.diag('FS-SITE-LINT-003', [tid]))
    return ds


def derive(ctx: Context) -> dict:
    ring = lot(ctx)
    out = {'lot': None, 'surface': None, 'grading': {}, 'cut': None, 'fill': None}
    if ring is not None:
        n = len(ring)
        sb = ctx.data.get('setbacks')
        kinds = edge_kinds(n, sb)
        edges = []
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            edges.append({'kind': kinds[i], 'length': round_sqrt(dx * dx + dy * dy),
                          'setback': None if kinds[i] is None else sb.get(kinds[i])})
        out['lot'] = {'area': plane.area_string(abs(plane.area2(ring))), 'edges': edges}
    s = surface(ctx)
    if s is not None:
        pts, tris = s
        zs = [p[2] for p in pts]
        out['surface'] = {'low': min(zs), 'high': max(zs), 'points': [list(p) for p in pts],
                          'triangles': [list(t) for t in tris]}
    total_cut = total_fill = Fraction(0)
    for gid, kind, outline, e in graded(ctx):
        g = {'kind': kind, 'elevation': e, 'low': None, 'high': None, 'cut': None, 'fill': None}
        if s is not None:
            cut, fill, low, high = measure(outline, e, *s)
            total_cut += cut
            total_fill += fill
            g.update(cut=str(round_half_even(cut)), fill=str(round_half_even(fill)),
                     low=None if low is None else round_half_even(low), high=None if high is None else round_half_even(high))
        out['grading'][gid] = g
    if s is not None:
        out['cut'], out['fill'] = str(round_half_even(total_cut)), str(round_half_even(total_fill))
    return out

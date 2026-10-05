"""Stairs (Core 0.3 and 0.4, chapter 17): the layout of a stair in its frame, its foot and head, its rise
and riser count, the steps, run and walkline of a straight, L-shaped or U-shaped stair, its headroom, the
stair invariants FS-INV-901 to FS-INV-904, the lint FS-LINT-016, and the derived `stairs`. A reader of
Core 0.4 also derives the tapered treads of winder and spiral stairs (17.7) - their steps, walkline, the
goings at the walkline and at the narrow end, and their headroom - and the opening a stair with a
`minHeadroom` needs (17.6), checks FS-INV-905 and FS-INV-906, and reports FS-LINT-018 and FS-LINT-019 in
place of FS-LINT-016.

Tapered treads are exact too. A winder's nosing lines lie on rays from the pivot of the turn whose
directions are facing vectors F(beta) of integer angles (13.1), so where a ray meets the sides of the turn
and of its newel is rational; a spiral's nosing lines lie on rays from its centre in the directions
F(phi). A point on a walkline arc is the pivot or the centre plus r * F / |F|, one radicand more. A going
is a distance between two such points: the square root of a value with one radicand, decided by exact
comparison with the squares of half-integers. A walkline's length includes an arc, r times an angle in
radians: pi is transcendental, so the length is never a tie, and it is found, like F, to far more digits
than needed.

A stair is laid out in its own frame (13.1): the origin is its `position` - the middle of its first
nosing line - at the top of the floor at its foot, facing F(rotation), the direction the first flight
rises in. Local coordinates (p, q) are exact rationals (halves of a width, multiples of a tread); a
plan point is the frame's exact image of one, rounded once. Elevations are the foot's floor top plus
a multiple of the exact riser height R / n, rounded once where output.

Headroom is measured on the rounded plan points of the stair's lanes - the two sides and the centre
line of every flight, and the edges and middle lines of every landing - so that every point of a lane
is rational, a vaulted ceiling's elevation over it has one radicand, and every comparison is exact.
Along a lane the obstacles above it are constant between the places where the lane crosses an edge of
a room polygon, an unanchored face, a tray's centre or a vault's ridge line, and each is linear there,
so the infimum of the clearance is reached at the ends of those pieces.
"""

from __future__ import annotations

import math
from decimal import Decimal, localcontext
from fractions import Fraction

from . import plane
from .derive import Doc, LevelGraph, degenerate
from .floors import ceiling, ceiling_base, floor_thickness, floor_top, in_tray, tray_rings, vault_z, _cross_at, _fall
from .frames import PI, PREC, Frame, _round_far_from_tie, facing_vector
from .surd import Surd

STRAIGHT = {'kind': 'straight'}
DERIVED_FORMS = ('straight', 'lShaped', 'uShaped')
TAPERED_FORMS = ('winder', 'spiral')                            # derived from Core 0.4 (17.7)
QUARTER, HALF = 90_000_000, 180_000_000


def form(st: dict) -> dict:
    return st.get('form', STRAIGHT)


def _half(v) -> Fraction:
    return Fraction(v, 2)


def _normalize(theta: int) -> int:
    """An angle in (-180e6, 180e6]."""
    t = theta % 360_000_000
    return t - 360_000_000 if t > 180_000_000 else t


# ------------------------------------------------------------------------------ the layout (17.3)

class Rect:
    """An axis-aligned rectangle of local coordinates, p0 < p1 and q0 < q1."""

    __slots__ = ('p0', 'q0', 'p1', 'q1')

    def __init__(self, p0, q0, p1, q1):
        p0, q0, p1, q1 = Fraction(p0), Fraction(q0), Fraction(p1), Fraction(q1)
        self.p0, self.q0, self.p1, self.q1 = min(p0, p1), min(q0, q1), max(p0, p1), max(q0, q1)

    def corners(self):
        return [(self.p0, self.q0), (self.p1, self.q0), (self.p1, self.q1), (self.p0, self.q1)]

    def mirrored(self):
        return Rect(self.p0, -self.q1, self.p1, -self.q0)


class Flight:
    """A straight run of `risers` risers: its first nosing line's middle `c`, its direction `e` (a local
    unit axis), `before` risers below its first, its treads `tread` deep and `width` wide."""

    def __init__(self, c, e, risers, before, tread, width):
        self.c, self.e, self.risers, self.before, self.tread, self.width = c, e, risers, before, tread, width

    def at(self, along, across):
        """The local point `along` the flight from its first nosing line and `across` to its left."""
        (cx, cy), (ex, ey) = self.c, self.e
        return (cx + along * ex - across * ey, cy + along * ey + across * ex)

    @property
    def length(self):
        return (self.risers - 1) * self.tread

    def treads(self):
        """(rectangle, index of the riser it tops) of each tread, bottom to top."""
        hw = _half(self.width)
        out = []
        for k in range(1, self.risers):
            a, b = self.at((k - 1) * self.tread, -hw), self.at(k * self.tread, hw)
            out.append((Rect(a[0], a[1], b[0], b[1]), self.before + k))
        return out

    def lanes(self):
        """Its two sides and its centre line: (start, end, riser index at the start, at the end)."""
        hw = _half(self.width)
        return [(self.at(0, x), self.at(self.length, x), self.before + 1, self.before + self.risers)
                for x in (hw, 0, -hw)]


class Layout:
    """The pieces of a stair in walking order - flights, and landings as (Rect, riser index) - its head
    point and the rectangles that bound it, all in local coordinates, for a left turn; a right turn is
    its mirror image (q -> -q)."""

    def __init__(self):
        self.pieces = []            # ('flight', Flight) or ('landing', Rect, index)
        self.head = (Fraction(0), Fraction(0))
        self.rects = []             # what bounds the stair in plan (winder forms)
        self.walk = []              # the walkline's vertices


def layout(st: dict, n: int) -> Layout:
    f = form(st)
    t, w = st['tread'], st['width']
    hw = _half(w)
    lay = Layout()
    kind = f['kind']
    if kind == 'spiral':
        return lay
    m = f.get('risersBeforeTurn', n)
    p1 = (m - 1) * t
    if kind == 'straight':
        fl = Flight((Fraction(0), Fraction(0)), (1, 0), n, 0, t, w)
        lay.pieces = [('flight', fl)]
        lay.head = fl.at(fl.length, 0)
        lay.walk = [fl.at(0, 0), lay.head]
    elif kind == 'lShaped':
        f1 = Flight((Fraction(0), Fraction(0)), (1, 0), m, 0, t, w)
        f2 = Flight((p1 + hw, hw), (0, 1), n - m, m, t, w)
        lay.pieces = [('flight', f1), ('landing', Rect(p1, -hw, p1 + w, hw), m), ('flight', f2)]
        lay.head = f2.at(f2.length, 0)
        lay.walk = [f1.at(0, 0), (p1 + hw, Fraction(0)), lay.head]
    elif kind == 'uShaped':
        g = f.get('gap', 0)
        f1 = Flight((Fraction(0), Fraction(0)), (1, 0), m, 0, t, w)
        f2 = Flight((p1, w + g), (-1, 0), n - m, m, t, w)
        lay.pieces = [('flight', f1), ('landing', Rect(p1, -hw, p1 + w, 3 * hw + g), m), ('flight', f2)]
        lay.head = f2.at(f2.length, 0)
        lay.walk = [f1.at(0, 0), (p1 + hw, Fraction(0)), (p1 + hw, Fraction(w + g)), lay.head]
    else:                                                       # winder: bounded, not stepped
        s2 = (n - m - f['winders']) * t
        rects = [Rect(0, -hw, p1, hw)] if p1 > 0 else []
        if f['angle'] == 'quarter':
            rects.append(Rect(p1, -hw, p1 + w, hw))
            if s2 > 0:
                rects.append(Rect(p1, hw, p1 + w, hw + s2))
            lay.head = (p1 + hw, hw + s2)
        else:
            g = f.get('gap', 0)
            rects.append(Rect(p1, -hw, p1 + w, 3 * hw + g))
            if s2 > 0:
                rects.append(Rect(p1 - s2, hw + g, p1, 3 * hw + g))
            lay.head = (p1 - s2, Fraction(w + g))
        lay.rects = rects
    if f.get('turn') == 'right':
        lay = _mirror(lay)
    return lay


def _mirror(lay: Layout) -> Layout:
    out = Layout()
    for piece in lay.pieces:
        if piece[0] == 'flight':
            fl = piece[1]
            out.pieces.append(('flight', Flight((fl.c[0], -fl.c[1]), (fl.e[0], -fl.e[1]), fl.risers, fl.before,
                                                fl.tread, fl.width)))
        else:
            out.pieces.append(('landing', piece[1].mirrored(), piece[2]))
    out.head = (lay.head[0], -lay.head[1])
    out.rects = [r.mirrored() for r in lay.rects]
    out.walk = [(p, -q) for p, q in lay.walk]
    return out


# ------------------------------------------------------------------------------ the frame (17.3)

def frame(doc: Doc, sid, bottom: int = 0) -> Frame:
    st = doc.stairs[sid]
    x, y = st['position']
    return Frame(x, y, bottom, facing_vector(st.get('rotation', 0)))


def rpt(fr: Frame, p, q):
    x, y = fr.plan(p, q)
    return (x.round(), y.round())


def spiral_points(doc: Doc, sid):
    """(centre (Surd, Surd), head (Surd, Surd)) of a spiral stair (17.3)."""
    st = doc.stairs[sid]
    f = form(st)
    fr = frame(doc, sid)
    rw = _half(f['diameter']) - _half(st['width'])
    side = 1 if f['turn'] == 'left' else -1
    cx, cy = fr.plan(0, side * rw)
    rot = st.get('rotation', 0)
    phi = rot - QUARTER + f['sweep'] if side > 0 else rot + QUARTER - f['sweep']
    hx, hy = Frame(cx, cy, 0, facing_vector(_normalize(phi))).plan(rw, 0)
    return (cx, cy), (hx, hy)


def head_point(doc: Doc, sid, n: int):
    st = doc.stairs[sid]
    if form(st)['kind'] == 'spiral':
        hx, hy = spiral_points(doc, sid)[1]
        return (hx.round(), hy.round())
    lay = layout(st, n)
    return rpt(frame(doc, sid), *lay.head)


# ------------------------------------------------------------------------------ rooms at a point

def _polygons(doc: Doc, level: str, graphs: dict):
    """(room polygons by room ID, polygons of the unanchored faces that are not degenerate) of a level."""
    if level not in graphs:
        g = LevelGraph(doc, level)
        faces = g.faces()
        rooms, anchored = {}, set()
        for rid, r in doc.rooms.items():
            if r['level'] == level:
                f = g.face_of(tuple(r['anchor']), faces)
                anchored.add(id(f))
                rooms[rid] = g.room_polygon(f)
        wells = []
        for f in faces:
            if id(f) not in anchored:
                outer, holes = g.room_polygon(f)
                if not degenerate(outer, holes):
                    wells.append((outer, holes))
        graphs[level] = (rooms, wells)
    return graphs[level]


def closed_contains(poly, p) -> bool:
    outer, holes = poly
    return plane.locate(p, outer) != 'out' and all(plane.locate(p, h) != 'in' for h in holes)


def strictly_contains(poly, p) -> bool:
    outer, holes = poly
    return plane.locate(p, outer) == 'in' and all(plane.locate(p, h) == 'out' for h in holes)


def room_at(doc: Doc, level: str, p, graphs: dict):
    """17.4: the room of `level` whose room polygon contains the plan point p, inside or on its outer ring
    and not strictly inside a hole - the first by ID when there are several - or None."""
    rooms, _ = _polygons(doc, level, graphs)
    found = sorted(rid for rid, poly in rooms.items() if closed_contains(poly, p))
    return found[0] if found else None


def floor_at(doc: Doc, level: str, rid) -> int:
    return floor_top(doc, rid) if rid is not None else doc.levels[level]['elevation']


# ------------------------------------------------------------------------------ foot, head, risers (17.4)

class Resolved:
    """A stair's foot and head, rise and riser count, exactly."""

    def __init__(self, doc: Doc, sid, graphs: dict):
        st = doc.stairs[sid]
        self.foot = tuple(st['position'])
        self.foot_room = room_at(doc, st['level'], self.foot, graphs)
        self.bottom = floor_at(doc, st['level'], self.foot_room)

        def at(n):
            head = head_point(doc, sid, n)
            room = room_at(doc, st['to'], head, graphs)
            return head, room, floor_at(doc, st['to'], room)
        if 'risers' in st:
            n = st['risers']
        else:
            n = 1
            while at(n)[2] - self.bottom > n * st['maxRiser']:
                n += 1
        self.n = n
        self.head, self.head_room, self.top = at(n)
        self.rise = self.top - self.bottom

    def z(self, index) -> Fraction:
        """The exact elevation of the top of riser `index`."""
        return self.bottom + Fraction(self.rise * index, self.n)


def fits(st: dict, n: int) -> bool:
    """17.4: whether n risers fit the stair's form."""
    f = form(st)
    k = f['kind']
    if k in ('straight', 'spiral'):
        return n >= 2
    m = f['risersBeforeTurn']
    if k == 'winder':
        return n >= m + f['winders']
    return m >= 2 and n - m >= 2


# ------------------------------------------------------------------------------ invariants (17.1, 17.4)

def invariants(doc: Doc, bad_levels, bad_rooms, diag, v04=False):
    """FS-INV-901 for every stair; FS-INV-904 for every spiral stair; FS-INV-902 and FS-INV-903 for a
    stair without FS-INV-901 whose two levels are levels where room invariants are evaluated and have no
    room with FS-INV-201 to FS-INV-204, and FS-INV-903 not for a stair with FS-INV-902 (10.3). A reader of
    0.4 also checks FS-INV-905 for every winder stair, and FS-INV-906 where FS-INV-903 is evaluated, for a
    stair with neither FS-INV-902 nor FS-INV-903."""
    ds = []
    graphs: dict = {}
    room_levels = {doc.rooms[r]['level'] for r in bad_rooms}
    for sid in sorted(doc.stairs):
        st = doc.stairs[sid]
        lv, to = doc.levels[st['level']], doc.levels[st['to']]
        f = form(st)
        if f['kind'] == 'spiral' and 2 * st['width'] > f['diameter']:
            ds.append(diag('FS-INV-904', [sid]))
        if v04 and f['kind'] == 'winder' and not newel_inside(st):
            ds.append(diag('FS-INV-905', [sid]))
        if st['to'] == st['level'] or to['building'] != lv['building']:
            ds.append(diag('FS-INV-901', [sid]))
            continue
        levels = {st['level'], st['to']}
        if levels & set(bad_levels) or levels & room_levels:
            continue
        r = Resolved(doc, sid, graphs)
        if r.rise <= 0:
            ds.append(diag('FS-INV-902', [sid]))
        elif not fits(st, r.n):
            ds.append(diag('FS-INV-903', [sid]))
        elif v04 and f['kind'] in TAPERED_FORMS and not angles_ok(st, r.n):
            ds.append(diag('FS-INV-906', [sid]))
    return ds


def lints(doc: Doc, diag, v04=False):
    """FS-LINT-016 (Core 0.3): a stair whose steps this draft does not derive. A reader of 0.4 derives them,
    and reports instead FS-LINT-018, for tapered treads that narrow to a point, and FS-LINT-019, for a stair
    whose headroom is less than its minHeadroom."""
    if not v04:
        return [diag('FS-LINT-016', [sid]) for sid in sorted(doc.stairs) if form(doc.stairs[sid])['kind'] not in DERIVED_FORMS]
    ds = []
    graphs: dict = {}
    for sid in sorted(doc.stairs):
        st = doc.stairs[sid]
        f = form(st)
        if (f['kind'] == 'winder' and 'newel' not in f) or (f['kind'] == 'spiral' and 2 * st['width'] == f['diameter']):
            ds.append(diag('FS-LINT-018', [sid]))
        if 'minHeadroom' in st:
            h = exact_headroom(doc, sid, graphs)
            if h is not None and h < st['minHeadroom']:
                ds.append(diag('FS-LINT-019', [sid]))
    return ds


# ------------------------------------------------------------------------------ headroom (17.6)

def _ring_edges(ring):
    n = len(ring)
    return [(ring[i], ring[(i + 1) % n]) for i in range(n)]


class Above:
    """What can be above a stair: the rooms of its level (their ceilings), the rooms of its `to` level
    (their floors' bottoms and their ceilings), and the unanchored faces of its `to` level (its well)."""

    def __init__(self, doc: Doc, st: dict, graphs: dict):
        self.doc = doc
        lower, _ = _polygons(doc, st['level'], graphs)
        upper, wells = _polygons(doc, st['to'], graphs)
        self.lower, self.upper, self.wells = lower, upper, wells
        self.trays = {}
        self.edges = []
        self.ridges = []
        for rid, poly in list(lower.items()) + list(upper.items()):
            outer, holes = poly
            for ring in [outer] + list(holes):
                self.edges.extend(_ring_edges(ring))
            c = ceiling(doc, rid)
            if c['kind'] == 'tray':
                tr = tray_rings(outer, holes, c['border'])
                self.trays[rid] = tr
                for ring in [tr[0]] + list(tr[1]):
                    self.edges.extend(_ring_edges(ring))
            elif c['kind'] == 'vaulted' and c.get('slopes', 'both') == 'both':
                self.ridges.append(c)
        for outer, holes in wells:
            for ring in [outer] + list(holes):
                self.edges.extend(_ring_edges(ring))

    def obstacles(self, m):
        """The obstacles above the plan point m, which is on no edge's boundary of a region it is tested
        against: (kind, room, state) for each."""
        out = []
        in_well = any(closed_contains(w, m) for w in self.wells)
        if not in_well:
            for rid, poly in self.lower.items():
                if strictly_contains(poly, m):
                    out.append(('ceiling', rid, self._tray_state(rid, m)))
        for rid, poly in self.upper.items():
            if strictly_contains(poly, m):
                out.append(('floor', rid, None))
                out.append(('ceiling', rid, self._tray_state(rid, m)))
        return out

    def _tray_state(self, rid, m):
        return in_tray(m, self.trays[rid]) if rid in self.trays else None

    def value(self, ob, p):
        """The exact elevation of an obstacle at the plan point p."""
        kind, rid, state = ob
        doc = self.doc
        if kind == 'floor':
            return Surd(floor_top(doc, rid) - floor_thickness(doc, rid))
        c = ceiling(doc, rid)
        base = ceiling_base(doc, rid)
        if c['kind'] == 'flat':
            return Surd(base)
        if c['kind'] == 'tray':
            return Surd(base + c['depth'] if state else base)
        return vault_z(base, c, _fall(c, _cross_at(c, p)))


def _crossings(a, b, edges, ridges):
    """Every parameter s in [0, 1] at which the segment from a to b meets an edge or a ridge line."""
    d = (b[0] - a[0], b[1] - a[1])
    out = {Fraction(0), Fraction(1)}
    for u, v in edges:
        e = (v[0] - u[0], v[1] - u[1])
        ua = (u[0] - a[0], u[1] - a[1])
        den = plane.cross(d, e)
        if den != 0:
            s, r = Fraction(plane.cross(ua, e), den), Fraction(plane.cross(ua, d), den)
            if 0 <= s <= 1 and 0 <= r <= 1:
                out.add(s)
        elif plane.cross(ua, d) == 0:
            dd = plane.dot(d, d)
            for x in (u, v):
                s = Fraction(plane.dot((x[0] - a[0], x[1] - a[1]), d), dd)
                if 0 <= s <= 1:
                    out.add(s)
    for c in ridges:
        ca, cb = _cross_at(c, a), _cross_at(c, b)
        if (ca < 0 < cb) or (cb < 0 < ca):
            out.add(Fraction(ca, ca - cb))
    return sorted(out)


def lane_clearance(above: Above, a, b, za, zb):
    """The least clearance along the lane from plan point a (walking surface at za) to b (at zb), over the
    points with something above them; None when nothing is above any of them."""
    if a == b:
        return None
    best = None
    ss = _crossings(a, b, above.edges, above.ridges)

    def pt(s):
        return (a[0] + s * (b[0] - a[0]), a[1] + s * (b[1] - a[1]))
    for s0, s1 in zip(ss, ss[1:]):
        obs = above.obstacles(pt((s0 + s1) / 2))
        if not obs:
            continue
        for s in (s0, s1):
            p = pt(s)
            v = min(above.value(ob, p) for ob in obs) - (za + s * (zb - za))
            if best is None or v < best:
                best = v
    return best


def lanes(lay: Layout, fr: Frame, res: Resolved):
    """Every lane of a laid-out stair: (plan start, plan end, elevation at the start, at the end)."""
    out = []
    for piece in lay.pieces:
        if piece[0] == 'flight':
            for p0, p1, i0, i1 in piece[1].lanes():
                out.append((rpt(fr, *p0), rpt(fr, *p1), res.z(i0), res.z(i1)))
        else:
            rect, index = piece[1], piece[2]
            z = res.z(index)
            cs = rect.corners()
            pm, qm = (rect.p0 + rect.p1) / 2, (rect.q0 + rect.q1) / 2
            segs = [(cs[i], cs[(i + 1) % 4]) for i in range(4)]
            segs += [((rect.p0, qm), (rect.p1, qm)), ((pm, rect.q0), (pm, rect.q1))]
            for p0, p1 in segs:
                out.append((rpt(fr, *p0), rpt(fr, *p1), z, z))
    return out


def headroom(doc: Doc, sid, lay: Layout, fr: Frame, res: Resolved, graphs: dict, extra=()):
    """The exact headroom (17.6) - the least clearance over every lane of the laid-out stair and the
    `extra` lanes of its tapered treads (17.7) - or None when nothing is above any of them."""
    above = Above(doc, doc.stairs[sid], graphs)
    best = None
    for a, b, za, zb in list(lanes(lay, fr, res)) + list(extra):
        v = lane_clearance(above, a, b, za, zb)
        if v is not None and (best is None or v < best):
            best = v
    return best


def exact_headroom(doc: Doc, sid, graphs: dict):
    """The exact headroom of any stair, as a reader of 0.4 derives it, or None."""
    st = doc.stairs[sid]
    res = Resolved(doc, sid, graphs)
    fr = frame(doc, sid)
    if form(st)['kind'] in TAPERED_FORMS:
        tl = tapered(doc, sid, res.n)
        return headroom(doc, sid, tl.layout, fr, res, graphs, tl.lanes(res))
    return headroom(doc, sid, layout(st, res.n), fr, res, graphs)


# ------------------------------------------------------------------------------ tapered treads (Core 0.4, 17.7)

def _divisions(total: int, k: int):
    """round(j * total / k) for j = 0 .. k: an angle divided into k parts, each end an integer (17.7.1)."""
    return [round(Fraction(j * total, k)) for j in range(k + 1)]


def tread_angles(st: dict, n: int):
    """The angle, in microdegrees, each tapered tread of a winder or spiral stair turns through (17.7)."""
    f = form(st)
    if f['kind'] == 'winder':
        cuts = _divisions(HALF if f['angle'] == 'half' else QUARTER, f['winders'])
    else:
        cuts = _divisions(f['sweep'], n - 1)
    return [b - a for a, b in zip(cuts, cuts[1:])]


def angles_ok(st: dict, n: int) -> bool:
    """FS-INV-906 (17.7.5): every winder turns through an angle greater than zero - so a turn of A
    microdegrees has at most A winders, since each turns through round(j A / W) - round((j - 1) A / W),
    at least 1 exactly when W <= A - and every spiral tread through more than zero and less than 180 degrees."""
    f = form(st)
    if f['kind'] == 'winder':
        return f['winders'] <= (HALF if f['angle'] == 'half' else QUARTER)
    return all(0 < a < HALF for a in tread_angles(st, n))


def newel_inside(st: dict) -> bool:
    """FS-INV-905 (17.7.4): a winder stair's newel lies inside the circle of its walkline - every corner
    of it closer to the pivot than (w + g) / 2 - and a half turn's gap is no wider than the stair."""
    f = form(st)
    w, a = st['width'], f.get('newel', 0)
    g = f.get('gap', 0) if f['angle'] == 'half' else 0
    return (2 * a) ** 2 + (2 * a + g) ** 2 < (w + g) ** 2 and g <= w


def round_sqrt(x: Surd) -> int:
    """round(sqrt(x)) for an exact x >= 0, ties to even, decided by comparing x with (k + 1/2)^2."""
    k = math.isqrt(max(0, x.floor()))
    c = (x - Fraction((2 * k + 1) ** 2, 4)).sign()
    if c > 0:
        return k + 1
    if c < 0:
        return k
    return k if k % 2 == 0 else k + 1


def arc_length(straight, r, theta: int) -> int:
    """round(straight + r * theta * pi / 180,000,000): straight lengths and an arc of radius r through theta
    microdegrees. pi is transcendental, so this is never a tie; it is found to far more digits than needed."""
    straight, r = Fraction(straight), Fraction(r)
    with localcontext() as c:
        c.prec = PREC
        v = (Decimal(straight.numerator) / Decimal(straight.denominator)
             + Decimal(r.numerator) * Decimal(theta) * PI / (Decimal(r.denominator) * Decimal(180_000_000)))
        return _round_far_from_tie(v)


def _unit_sq_gap(g0, g1) -> Surd:
    """|g0/|g0| - g1/|g1||^2 = 2 - 2 (g0 . g1) / sqrt(|g0|^2 |g1|^2), exact, in one radicand."""
    m = plane.dot(g0, g0) * plane.dot(g1, g1)
    return Surd(2, {m: Fraction(-2 * plane.dot(g0, g1), m)})


def _on_ray(o, d, r):
    """o + r * d / |d|: exact, with the radicand |d|^2."""
    m = plane.dot(d, d)
    return (Surd.of(o[0]) + Surd.sqrt(m, Fraction(r) * d[0] / m), Surd.of(o[1]) + Surd.sqrt(m, Fraction(r) * d[1] / m))


def plan_of(fr: Frame, p, q):
    """The exact plan point of local (p, q), each a Surd or a rational (13.1)."""
    fx, fy = fr.f
    D = fx * fx + fy * fy
    k = Surd.sqrt(D, Fraction(1, D))
    p, q = Surd.of(p), Surd.of(q)
    return (fr.ox + (p * fx - q * fy) * k, fr.oy + (p * fy + q * fx) * k)


def _rp(pt):
    return (Surd.of(pt[0]).round(), Surd.of(pt[1]).round())


def ring_of(points):
    """A tapered tread's outline: its exact plan points rounded once, repeats removed, counter-clockwise
    from its least vertex (6.2)."""
    ring = plane.dedupe_cyclic([_rp(p) for p in points])
    if plane.area2(ring) < 0:
        ring = ring[::-1]
    return plane.least_first(ring)


class Turn:
    """The turn of a winder stair (17.7.1), in the local coordinates of a left turn: its rectangle T, its
    pivot O, its newel N, and the nosing lines of its winders on rays from O."""

    def __init__(self, st: dict):
        f = form(st)
        w = st['width']
        self.half = f['angle'] == 'half'
        g = f.get('gap', 0) if self.half else 0
        a = f.get('newel', 0)
        hw = _half(w)
        self.P = Fraction((f['risersBeforeTurn'] - 1) * st['tread'])
        self.w, self.g, self.a, self.W = w, g, a, f['winders']
        self.A = HALF if self.half else QUARTER
        self.O = (self.P, hw + _half(g))
        self.r = _half(w + g)
        self.q_lo, self.top = -hw, (3 * hw + g if self.half else hw)
        self.n_lo, self.n_hi = hw - a, (hw + g + a if self.half else hw)
        self.dirs = [facing_vector(-QUARTER + b) for b in _divisions(self.A, self.W)]
        self.inner = [self._end(d, self.P + a, self.n_lo, self.n_hi) if a else self.O for d in self.dirs]
        self.outer = [self._end(d, self.P + w, self.q_lo, self.top) for d in self.dirs]
        self.outer_corners = [(self.P + w, self.q_lo)] + ([(self.P + w, self.top)] if self.half else [])
        self.newel_corners = ([(self.P + a, self.n_lo)] + ([(self.P + a, self.n_hi)] if self.half else [])) if a else []

    def _end(self, d, p_hi, q_lo, q_hi):
        """Where the ray from O in the direction d leaves the rectangle [P, p_hi] x [q_lo, q_hi]."""
        (px, qy), (dx, dy) = self.O, d
        cands = []
        if dx > 0:
            cands.append((p_hi - px) / dx)
        if dy < 0:
            cands.append((q_lo - qy) / dy)
        if dy > 0:
            cands.append((q_hi - qy) / dy)
        s = min(cands)
        return (px + s * dx, qy + s * dy)

    def _between(self, j, c):
        v = (c[0] - self.O[0], c[1] - self.O[1])
        return plane.cross(self.dirs[j - 1], v) > 0 and plane.cross(v, self.dirs[j]) > 0

    def winder(self, j):
        """Winder j (1 .. W): its outline, from the inner end of nosing line j - 1 out along it, along T,
        in along nosing line j and back along N."""
        pts = [self.inner[j - 1], self.outer[j - 1]] + [c for c in self.outer_corners if self._between(j, c)]
        pts += [self.outer[j], self.inner[j]] + [c for c in reversed(self.newel_corners) if self._between(j, c)]
        out = []
        for p in pts:
            if not out or out[-1] != p:
                out.append(p)
        if len(out) > 1 and out[-1] == out[0]:
            out.pop()
        return out

    def walk(self, j):
        """Where the walkline - the arc of radius (w + g) / 2 about O - crosses nosing line j."""
        return _on_ray(self.O, self.dirs[j], self.r)

    def goings(self, j):
        """(the square of winder j's going at the walkline, the square of its going at its narrow end)."""
        walk = _unit_sq_gap(self.dirs[j - 1], self.dirs[j]) * (self.r * self.r)
        a, b = self.inner[j - 1], self.inner[j]
        narrow = Surd((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
        return walk, narrow


class Tapered:
    """What 17.7 derives for a winder or a spiral stair: its pieces in walking order - ('flight', Flight)
    in local coordinates, or ('tread', exact plan outline, riser index, exact plan walkline chord, going
    squares) - its walkline's exact plan points, and its length; and, for a spiral, its centre."""

    def __init__(self):
        self.layout = Layout()
        self.treads = []
        self.walk = []
        self.length = 0
        self.centre = None
        self.fr = None
        self.right = False

    def lanes(self, res):
        """17.6: each tapered tread's lanes - the edges of its outline and its walkline chord, level at its top."""
        out = []
        for outline, index, chord, _ in self.treads:
            z = res.z(index)
            ring = ring_of(outline)
            for i in range(len(ring)):
                out.append((ring[i], ring[(i + 1) % len(ring)], z, z))
            out.append((_rp(chord[0]), _rp(chord[1]), z, z))
        return out


def tapered(doc: Doc, sid, n: int) -> Tapered:
    st = doc.stairs[sid]
    f = form(st)
    fr = frame(doc, sid)
    out = Tapered()
    out.fr = fr
    t, w = st['tread'], st['width']
    hw = _half(w)
    if f['kind'] == 'spiral':
        (cx, cy), _ = spiral_points(doc, sid)
        out.centre = (cx, cy)
        ro, rc, ri = _half(f['diameter']), _half(f['diameter']) - hw, _half(f['diameter']) - w
        side = 1 if f['turn'] == 'left' else -1
        rot = st.get('rotation', 0)
        base = rot - QUARTER if side > 0 else rot + QUARTER
        dirs = [facing_vector(_normalize(base + side * b)) for b in _divisions(f['sweep'], n - 1)]
        on = lambda d, r: _on_ray((cx, cy), d, r)                   # noqa: E731
        out.walk = [on(d, rc) for d in dirs]
        for k in range(1, n):
            d0, d1 = dirs[k - 1], dirs[k]
            outline = [on(d0, ri), on(d0, ro), on(d1, ro), on(d1, ri)] if ri > 0 else [(cx, cy), on(d0, ro), on(d1, ro)]
            gap = _unit_sq_gap(d0, d1)
            out.treads.append((outline, k, (out.walk[k - 1], out.walk[k]), (gap * (rc * rc), gap * (ri * ri))))
        out.length = arc_length(0, rc, f['sweep'])
        return out
    # a winder stair: its first flight, the winders of its turn, and its second flight
    m, W = f['risersBeforeTurn'], f['winders']
    turn = Turn(st)
    P, g = turn.P, turn.g
    s2 = (n - m - W) * t
    out.right = f['turn'] == 'right'
    mir = (lambda pt: (pt[0], -pt[1])) if out.right else (lambda pt: pt)      # noqa: E731
    plan = lambda pt: plan_of(fr, *mir(pt))                                    # noqa: E731
    f1 = Flight((Fraction(0), Fraction(0)), (1, 0), m, 0, t, w)
    if turn.half:
        f2 = Flight((P, Fraction(w + g)), (-1, 0), n - m - W + 1, m + W - 1, t, w)
    else:
        f2 = Flight((P + hw, hw), (0, 1), n - m - W + 1, m + W - 1, t, w)
    lay = Layout()
    lay.pieces = [('flight', f1), ('flight', f2)]
    if out.right:
        lay = _mirror(lay)
    out.layout = lay
    crossings = [plan(turn.walk(j)) for j in range(W + 1)]
    for j in range(1, W + 1):
        out.treads.append(([plan(p) for p in turn.winder(j)], m + j - 1, (crossings[j - 1], crossings[j]), turn.goings(j)))
    out.walk = [plan((Fraction(0), Fraction(0)))] + crossings + [plan(f2.at(f2.length, 0))]
    out.length = arc_length(P + s2, turn.r, turn.A)
    return out


def opening(doc: Doc, st: dict, res: Resolved, tops):
    """17.6: the index of the first step whose top is less than minHeadroom below the bottom of the floor
    at the stair's head, or None when no step's is."""
    head_room = res.head_room
    if head_room is not None:
        thick = floor_thickness(doc, head_room)
    else:
        thick = doc.levels[st['to']].get('floorThickness', 0)
    floor_bottom = res.top - thick
    for i, z in enumerate(tops):
        if z + st['minHeadroom'] > floor_bottom:
            return i
    return None


# ------------------------------------------------------------------------------ derived values (17.4-17.6)

def _box(points, z0, z1):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return {'min': [min(xs), min(ys), z0], 'max': [max(xs), max(ys), z1]}


def _ring(fr: Frame, rect: Rect):
    ring = [rpt(fr, p, q) for p, q in rect.corners()]
    return plane.least_first(ring)


def derive_one(doc: Doc, sid, graphs: dict, v04=False) -> dict:
    st = doc.stairs[sid]
    f = form(st)
    res = Resolved(doc, sid, graphs)
    fr = frame(doc, sid)
    v = {'risers': res.n, 'riserHeight': Surd(Fraction(res.rise, res.n)).round(), 'rise': res.rise,
         'bottom': res.bottom, 'top': res.top, 'foot': list(res.foot), 'head': list(res.head)}
    if res.foot_room is not None:
        v['footRoom'] = res.foot_room
    if res.head_room is not None:
        v['headRoom'] = res.head_room
    if f['kind'] == 'spiral':
        (cx, cy), _ = spiral_points(doc, sid)
        r = _half(f['diameter'])
        v['box'] = {'min': [(cx - r).round(), (cy - r).round(), res.bottom],
                    'max': [(cx + r).round(), (cy + r).round(), res.top]}
    lay = layout(st, res.n)
    if f['kind'] == 'winder':
        pts = [rpt(fr, p, q) for rect in lay.rects for p, q in rect.corners()]
        v['box'] = _box(pts, res.bottom, res.top)
    if f['kind'] in TAPERED_FORMS:
        if not v04:
            return v
        return _derive_tapered(doc, sid, st, f, res, fr, graphs, v)
    steps, pts, tops = [], [], []
    for piece in lay.pieces:
        if piece[0] == 'flight':
            for rect, index in piece[1].treads():
                ring = _ring(fr, rect)
                steps.append({'outline': [list(p) for p in ring], 'top': Surd(res.z(index)).round()})
                tops.append(res.z(index))
                pts.extend(ring)
        else:
            ring = _ring(fr, piece[1])
            steps.append({'outline': [list(p) for p in ring], 'top': Surd(res.z(piece[2])).round(), 'landing': True})
            tops.append(res.z(piece[2]))
            pts.extend(ring)
    treads = sum(1 for s in steps if 'landing' not in s)
    walk = lay.walk
    length = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(walk, walk[1:]))   # axis-aligned legs
    v['box'] = _box(pts, res.bottom, res.top)
    v['steps'] = steps
    v['run'] = treads * st['tread']
    v['walkline'] = {'points': [list(rpt(fr, *p)) for p in walk], 'length': int(length)}
    h = headroom(doc, sid, lay, fr, res, graphs)
    if h is not None:
        v['headroom'] = Surd.of(h).round()
    _opening(doc, st, res, tops, v)
    return v


def _opening(doc, st, res, tops, v):
    if 'minHeadroom' in st:
        i = opening(doc, st, res, tops)
        if i is not None:
            v['opening'] = {'first': i}


def _derive_tapered(doc: Doc, sid, st, f, res: Resolved, fr: Frame, graphs: dict, v: dict) -> dict:
    """17.7: the steps, run, walkline and goings of a winder or a spiral stair, its headroom (17.6), and a
    spiral's centre."""
    tl = tapered(doc, sid, res.n)
    steps, tops, walks, narrows = [], [], [], []
    winders = iter(tl.treads)
    for piece in tl.layout.pieces:
        if piece[0] == 'flight':
            for rect, index in piece[1].treads():
                steps.append({'outline': [list(p) for p in _ring(fr, rect)], 'top': Surd(res.z(index)).round()})
                tops.append(res.z(index))
        if f['kind'] == 'winder' and piece is tl.layout.pieces[0]:
            for outline, index, _, (walk, narrow) in winders:
                steps.append({'outline': [list(p) for p in ring_of(outline)], 'top': Surd(res.z(index)).round(),
                              'winder': True})
                tops.append(res.z(index))
                walks.append(walk)
                narrows.append(narrow)
    if f['kind'] == 'spiral':
        for outline, index, _, (walk, narrow) in tl.treads:
            steps.append({'outline': [list(p) for p in ring_of(outline)], 'top': Surd(res.z(index)).round()})
            tops.append(res.z(index))
            walks.append(walk)
            narrows.append(narrow)
        v['centre'] = [tl.centre[0].round(), tl.centre[1].round()]
    v['steps'] = steps
    v['run'] = tl.length
    v['walkline'] = {'points': [list(p) for p in plane.dedupe_cyclic_open([_rp(p) for p in tl.walk])], 'length': tl.length}
    v['walklineGoing'] = round_sqrt(min(walks, key=_SurdKey))
    v['narrowGoing'] = round_sqrt(min(narrows, key=_SurdKey))
    h = headroom(doc, sid, tl.layout, fr, res, graphs, tl.lanes(res))
    if h is not None:
        v['headroom'] = Surd.of(h).round()
    _opening(doc, st, res, tops, v)
    return v


class _SurdKey:
    """Orders exact values (Surd's own comparisons) for min()."""

    def __init__(self, x):
        self.x = x

    def __lt__(self, o):
        return self.x < o.x


def derive(doc: Doc, v04=False) -> dict:
    """{stairs} of a valid document (17.4): empty for one that has none."""
    graphs: dict = {}
    return {'stairs': {sid: derive_one(doc, sid, graphs, v04) for sid in sorted(doc.stairs)}}


def links(doc: Doc):
    """14.1: (foot room, head room) of every stair that has both."""
    graphs: dict = {}
    out = []
    for sid in sorted(doc.stairs):
        r = Resolved(doc, sid, graphs)
        if r.foot_room is not None and r.head_room is not None:
            out.append((r.foot_room, r.head_room))
    return out

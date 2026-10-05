"""Stairs (Core 0.3, chapter 17): the layout of a stair in its frame, its foot and head, its rise and
riser count, the steps, run and walkline of a straight, L-shaped or U-shaped stair, its headroom, the
stair invariants FS-INV-901 to FS-INV-904, the lint FS-LINT-016, and the derived `stairs`.

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

from fractions import Fraction

from . import plane
from .derive import Doc, LevelGraph, degenerate
from .floors import ceiling, ceiling_base, floor_thickness, floor_top, in_tray, tray_rings, vault_z, _cross_at, _fall
from .frames import Frame, facing_vector
from .surd import Surd

STRAIGHT = {'kind': 'straight'}
DERIVED_FORMS = ('straight', 'lShaped', 'uShaped')
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

def invariants(doc: Doc, bad_levels, bad_rooms, diag):
    """FS-INV-901 for every stair; FS-INV-904 for every spiral stair; FS-INV-902 and FS-INV-903 for a
    stair without FS-INV-901 whose two levels are levels where room invariants are evaluated and have no
    room with FS-INV-201 to FS-INV-204, and FS-INV-903 not for a stair with FS-INV-902 (10.3)."""
    ds = []
    graphs: dict = {}
    room_levels = {doc.rooms[r]['level'] for r in bad_rooms}
    for sid in sorted(doc.stairs):
        st = doc.stairs[sid]
        lv, to = doc.levels[st['level']], doc.levels[st['to']]
        f = form(st)
        if f['kind'] == 'spiral' and 2 * st['width'] > f['diameter']:
            ds.append(diag('FS-INV-904', [sid]))
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
    return ds


def lints(doc: Doc, diag):
    """FS-LINT-016: a stair whose steps this draft does not derive."""
    return [diag('FS-LINT-016', [sid]) for sid in sorted(doc.stairs) if form(doc.stairs[sid])['kind'] not in DERIVED_FORMS]


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


def headroom(doc: Doc, sid, lay: Layout, fr: Frame, res: Resolved, graphs: dict):
    above = Above(doc, doc.stairs[sid], graphs)
    best = None
    for a, b, za, zb in lanes(lay, fr, res):
        v = lane_clearance(above, a, b, za, zb)
        if v is not None and (best is None or v < best):
            best = v
    return None if best is None else Surd.of(best).round()


# ------------------------------------------------------------------------------ derived values (17.4-17.6)

def _box(points, z0, z1):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return {'min': [min(xs), min(ys), z0], 'max': [max(xs), max(ys), z1]}


def _ring(fr: Frame, rect: Rect):
    ring = [rpt(fr, p, q) for p, q in rect.corners()]
    return plane.least_first(ring)


def derive_one(doc: Doc, sid, graphs: dict) -> dict:
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
        return v
    lay = layout(st, res.n)
    if f['kind'] == 'winder':
        pts = [rpt(fr, p, q) for rect in lay.rects for p, q in rect.corners()]
        v['box'] = _box(pts, res.bottom, res.top)
        return v
    steps, pts = [], []
    for piece in lay.pieces:
        if piece[0] == 'flight':
            for rect, index in piece[1].treads():
                ring = _ring(fr, rect)
                steps.append({'outline': [list(p) for p in ring], 'top': Surd(res.z(index)).round()})
                pts.extend(ring)
        else:
            ring = _ring(fr, piece[1])
            steps.append({'outline': [list(p) for p in ring], 'top': Surd(res.z(piece[2])).round(), 'landing': True})
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
        v['headroom'] = h
    return v


def derive(doc: Doc) -> dict:
    """{stairs} of a valid document (17.4): empty for one that has none."""
    graphs: dict = {}
    return {'stairs': {sid: derive_one(doc, sid, graphs) for sid in sorted(doc.stairs)}}


def links(doc: Doc):
    """14.1: (foot room, head room) of every stair that has both."""
    graphs: dict = {}
    out = []
    for sid in sorted(doc.stairs):
        r = Resolved(doc, sid, graphs)
        if r.foot_room is not None and r.head_room is not None:
            out.append((r.foot_room, r.head_room))
    return out

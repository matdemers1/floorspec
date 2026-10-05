"""Frames, boxes, footprints and the overlap measure (Core 0.2, chapter 13).

Every frame has an exact origin - Surd coordinates - an integer elevation and an integer facing
vector f. A local point (p, q) maps to  O + (p*f + q*rot90(f)) / |f|,  so every footprint corner
is of the form  a + b*sqrt(|f|^2) (+ the wall's radicand, which for a wall frame is the same one)
and is rounded once, exactly.

Two values involve transcendental functions: the facing vector of an angle, F(theta) =
(round(1e9 cos), round(1e9 sin)), and the direction of an integer vector, round(atan2) in
microdegrees. Neither can be a tie (13.1), so each is decided by evaluating the function to far
more digits than needed and checking that the result is not within 10^-30 of a rounding boundary.
That check is an assertion: it never fails for a value 13.1 says cannot tie.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction

from .surd import Surd

K = 10 ** 9
PREC = 90
PI = Decimal('3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798214808651328230664709384460955058223172535940812848111745028410270193852110555964462294895493038196')
_EPS = Decimal('1e-30')


def _round_far_from_tie(x: Decimal) -> int:
    """Nearest integer to x, asserting that x is not within 10^-30 of a half-integer."""
    fl = int(x.to_integral_value(rounding='ROUND_FLOOR'))
    frac = x - fl
    assert abs(frac - Decimal('0.5')) > _EPS, f'a rounding tie that 13.1 says cannot occur: {x}'
    return fl + 1 if frac > Decimal('0.5') else fl


def _atan(t: Decimal) -> Decimal:
    k = 0
    one = Decimal(1)
    while abs(t) > Decimal('0.05'):
        t = t / (one + (one + t * t).sqrt())        # atan(t) = 2 atan(t / (1 + sqrt(1 + t^2)))
        k += 1
    s, term, n, t2 = Decimal(0), t, 1, t * t
    while abs(term) > Decimal(10) ** (-PREC + 5):
        s += term / n if (n // 2) % 2 == 0 else -term / n
        term *= t2
        n += 2
    return s * (2 ** k)


def direction(x: int, y: int) -> int:
    """13.1: the angle of (x, y) from +X, in microdegrees, rounded, in (-180e6, 180e6]."""
    assert (x, y) != (0, 0)
    exact = {(1, 0): 0, (0, 1): 90_000_000, (-1, 0): 180_000_000, (0, -1): -90_000_000}
    sx, sy = (x > 0) - (x < 0), (y > 0) - (y < 0)
    if sx == 0 or sy == 0:
        return exact[(sx, sy)]
    if abs(x) == abs(y):
        return {(1, 1): 45_000_000, (-1, 1): 135_000_000, (-1, -1): -135_000_000, (1, -1): -45_000_000}[(sx, sy)]
    with localcontext() as c:
        c.prec = PREC
        a = _atan(Decimal(y) / Decimal(x))
        if x < 0:
            a = a + PI if y > 0 else a - PI
        r = _round_far_from_tie(a * 180_000_000 / PI)
    return 180_000_000 if r == -180_000_000 else r


def _sin_cos(r: Decimal):
    s, c = Decimal(0), Decimal(0)
    term, n = Decimal(1), 0          # r^n / n!
    eps = Decimal(10) ** (-PREC + 5)
    while n < 4 or abs(term) > eps:
        k = n % 4
        if k == 0:
            c += term
        elif k == 1:
            s += term
        elif k == 2:
            c -= term
        else:
            s -= term
        n += 1
        term = term * r / n
    return s, c


def facing_vector(theta: int):
    """13.1: F(theta) = (round(1e9 cos theta), round(1e9 sin theta)), theta in microdegrees."""
    t = theta % 360_000_000
    exact = {0: (K, 0), 90_000_000: (0, K), 180_000_000: (-K, 0), 270_000_000: (0, -K)}
    if t in exact:
        return exact[t]
    with localcontext() as c:
        c.prec = PREC
        r = Decimal(theta) * PI / Decimal(180_000_000)
        s, co = _sin_cos(r)
        return (_round_far_from_tie(co * K), _round_far_from_tie(s * K))


# ------------------------------------------------------------------------------ frames

class Frame:
    """An origin (Surd x, Surd y), an integer elevation and an integer facing vector."""

    __slots__ = ('ox', 'oy', 'oz', 'f')

    def __init__(self, ox, oy, oz: int, f):
        self.ox, self.oy, self.oz, self.f = Surd.of(ox), Surd.of(oy), oz, f

    def plan(self, p, q):
        """The exact plan point of local (p, q)."""
        fx, fy = self.f
        D = fx * fx + fy * fy
        return (self.ox + Surd.sqrt(D, Fraction(p * fx - q * fy, D)),
                self.oy + Surd.sqrt(D, Fraction(p * fy + q * fx, D)))

    def placement(self):
        return {'point': [self.ox.round(), self.oy.round(), self.oz], 'facing': direction(*self.f)}


def level_frame(level: dict) -> Frame:
    return Frame(0, 0, level['elevation'], (1, 0))


def _wall_geometry(doc, wid):
    w = doc.walls[wid]
    S = doc.junctions[w['start']]['position']
    E = doc.junctions[w['end']]['position']
    dx, dy = E[0] - S[0], E[1] - S[1]
    return S, (dx, dy), dx * dx + dy * dy


def wall_point(doc, wid, along, normal):
    """S + along * t + normal * m, with t and m the unit vectors along the wall and to its left."""
    S, (dx, dy), D = _wall_geometry(doc, wid)
    along, normal = Fraction(along), Fraction(normal)
    return (Surd(S[0]) + Surd.sqrt(D, (along * dx - normal * dy) / D),
            Surd(S[1]) + Surd.sqrt(D, (along * dy + normal * dx) / D))


def host_frame(doc, host) -> Frame:
    """13.1: the frame of a host."""
    mode = host['mode']
    if mode == 'wallFace':
        wid = host['wall']
        a, b = doc.offsets(wid)
        _, (dx, dy), _ = _wall_geometry(doc, wid)
        if host['side'] == 'left':
            x, y = wall_point(doc, wid, host['offset'], a)
            f = (-dy, dx)
        else:
            x, y = wall_point(doc, wid, host['offset'], -b)
            f = (dy, -dx)
        return Frame(x, y, doc.base_elevation(wid) + host['height'], f)
    f = facing_vector(host.get('rotation', 0))
    x, y = host['position']
    if mode == 'surface':
        lvl = doc.levels[doc.rooms[host['room']]['level']]
        z = lvl['elevation'] + (lvl['height'] if host['surface'] == 'ceiling' else 0)
        return Frame(x, y, z, f)
    return Frame(x, y, doc.levels[host['level']]['elevation'], f)


def opening_frame(doc, oid) -> Frame:
    o = doc.openings[oid]
    wid = o['wall']
    width, _, sill = doc.opening_dims(oid)
    x, y = wall_point(doc, wid, Fraction(2 * o['offset'] + width, 2), 0)
    _, (dx, dy), _ = _wall_geometry(doc, wid)
    f = (-dy, dx) if o.get('swing', 'right') == 'left' else (dy, -dx)
    return Frame(x, y, doc.base_elevation(wid) + sill, f)


def element_frame(doc, el) -> Frame:
    """12.6: an extension element's frame - its host's, or its fallback level's."""
    if 'host' in el:
        return host_frame(doc, el['host'])
    return level_frame(doc.levels[el['fallback']['level']])


# ------------------------------------------------------------------------------ boxes

def extents_ok(box) -> bool:
    """13.2.2: every extent at least 1,280."""
    return all(box['max'][i] - box['min'][i] >= 1280 for i in range(3))


def footprint(frame: Frame, box):
    """13.2: (ring, bottom, top) - the ring rounded, least vertex first, counter-clockwise."""
    (x0, y0, z0), (x1, y1, z1) = box['min'], box['max']
    ring = []
    for p, q in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        px, py = frame.plan(p, q)
        ring.append((px.round(), py.round()))
    k = min(range(4), key=lambda i: ring[i])
    ring = ring[k:] + ring[:k]
    _assert_strictly_convex_ccw(ring)
    return [list(p) for p in ring], frame.oz + z0, frame.oz + z1


def _assert_strictly_convex_ccw(ring) -> None:
    n = len(ring)
    for i in range(n):
        a, b, c = ring[i], ring[(i + 1) % n], ring[(i + 2) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        assert cr > 0, f'footprint not strictly convex and counter-clockwise: {ring}'


def _project(ring, axis):
    vals = [p[0] * axis[0] + p[1] * axis[1] for p in ring]
    return min(vals), max(vals)


def footprints_overlap(r1, r2) -> bool:
    """13.6: the interiors of two convex rings intersect (separating axis test on edge normals)."""
    for ring in (r1, r2):
        n = len(ring)
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            axis = (a[1] - b[1], b[0] - a[0])
            lo1, hi1 = _project(r1, axis)
            lo2, hi2 = _project(r2, axis)
            if max(lo1, lo2) >= min(hi1, hi2):
                return False
    return True


def envelopes_overlap(e1, e2) -> bool:
    """13.6: footprints' interiors intersect and the vertical ranges overlap by a positive length."""
    return max(e1['bottom'], e2['bottom']) < min(e1['top'], e2['top']) and footprints_overlap(e1['footprint'], e2['footprint'])

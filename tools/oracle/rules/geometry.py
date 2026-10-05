"""The geometry of the measures: least width (5.3), triangulation of plan polygons, local
coordinates in a frame (Core 13.1) and clipping in them (7.6, 7.7). Exact throughout."""

from __future__ import annotations

from fractions import Fraction

from .qr import QR, from_surd


def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def hull(points):
    """Convex hull of integer points, counter-clockwise, no collinear vertices (Andrew)."""
    pts = sorted(set(map(tuple, points)))
    if len(pts) <= 2:
        return pts
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def least_width(ring):
    """(C, L): the least width of a ring is C / sqrt(L) (5.3): over the hull's edges (a, b), the
    greatest |(b - a) x (v - a)|, divided by |b - a|; the least of these."""
    h = hull(ring)
    best = None
    n = len(h)
    for i in range(n):
        a, b = h[i], h[(i + 1) % n]
        c = max(abs(cross(a, b, v)) for v in h)
        L = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
        if best is None or c * c * best[1] < best[0] * best[0] * L:
            best = (c, L)
    return best


def triangulate(ring):
    """Ear clipping of a simple counter-clockwise polygon with integer vertices: triangles whose
    interiors, with the open diagonals between them, make the polygon's interior."""
    pts = [tuple(p) for p in ring]
    # drop vertices on a straight line between their neighbours: the polygon is the same
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            if cross(pts[i - 1], pts[i], pts[(i + 1) % len(pts)]) == 0:
                del pts[i]
                changed = True
                break
    tris = []
    while len(pts) > 3:
        n = len(pts)
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            if cross(a, b, c) <= 0:
                continue
            if any(_in_closed_triangle(p, a, b, c) for p in pts if p not in (a, b, c)):
                continue
            tris.append((a, b, c))
            del pts[i]
            break
        else:
            raise AssertionError(f'no ear in {pts}')
    tris.append(tuple(pts))
    return tris


def _in_closed_triangle(p, a, b, c) -> bool:
    return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0


class Local:
    """A frame's local coordinates of plan points: p = (P - O).f / |f|, q = (P - O).(-fy, fx) / |f|."""

    def __init__(self, frame):
        self.ox, self.oy = from_surd(frame.ox), from_surd(frame.oy)
        self.f = frame.f
        self.M = frame.f[0] ** 2 + frame.f[1] ** 2
        self.root = QR(0, 1, self.M)                    # |f|

    def of(self, P):
        fx, fy = self.f
        dx, dy = QR(P[0]) - self.ox, QR(P[1]) - self.oy
        return ((dx * fx + dy * fy) / self.root, (dy * fx - dx * fy) / self.root)


def clip(poly, keep):
    """Sutherland-Hodgman: poly (local points) clipped by half-planes keep = [(axis, bound, side)],
    keeping axis-coordinate >= bound (side +1) or <= bound (side -1)."""
    for axis, bound, side in keep:
        out = []
        n = len(poly)
        if n == 0:
            return []
        for i in range(n):
            cur, nxt = poly[i], poly[(i + 1) % n]
            cin = side * (cur[axis] - bound).sign() >= 0
            nin = side * (nxt[axis] - bound).sign() >= 0
            if cin:
                out.append(cur)
            if cin != nin:
                t = (QR.of(bound) - cur[axis]) / (nxt[axis] - cur[axis])
                out.append((cur[0] + (nxt[0] - cur[0]) * t, cur[1] + (nxt[1] - cur[1]) * t))
        poly = out
    return poly


def area_sign(poly) -> int:
    n = len(poly)
    if n < 3:
        return 0
    s = QR(0)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        s = s + (a[0] * b[1] - b[0] * a[1])
    return s.sign()


def F(x) -> Fraction:
    return Fraction(x)

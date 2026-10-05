"""Exact plane geometry on integer points (junction positions, rounded derived vertices)."""

from __future__ import annotations


def sgn(x) -> int:
    return (x > 0) - (x < 0)


def sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def cross(u, v):
    return u[0] * v[1] - u[1] * v[0]


def dot(u, v):
    return u[0] * v[0] + u[1] * v[1]


def orient(a, b, c) -> int:
    return sgn(cross(sub(b, a), sub(c, a)))


def on_closed_segment(p, a, b) -> bool:
    if orient(a, b, p) != 0:
        return False
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def in_open_segment(p, a, b) -> bool:
    """p lies in the interior of segment ab (without its endpoints). False when a == b."""
    return a != b and p != a and p != b and on_closed_segment(p, a, b)


def segments_touch(a, b, c, d) -> bool:
    """The closed segments ab and cd share at least one point."""
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return (on_closed_segment(c, a, b) or on_closed_segment(d, a, b)
            or on_closed_segment(a, c, d) or on_closed_segment(b, c, d))


def proper_cross(a, b, c, d) -> bool:
    """ab and cd meet in a single point interior to both."""
    return orient(a, b, c) * orient(a, b, d) < 0 and orient(c, d, a) * orient(c, d, b) < 0


def collinear_overlap(a, b, c, d) -> bool:
    """ab and cd are collinear and overlap in a segment of positive length."""
    if a == b or c == d:
        return False
    if orient(a, b, c) != 0 or orient(a, b, d) != 0:
        return False
    u = sub(b, a)
    t = sorted((0, dot(u, u)))
    s = sorted((dot(sub(c, a), u), dot(sub(d, a), u)))
    return max(t[0], s[0]) < min(t[1], s[1])


def area2(ring) -> int:
    """Twice the signed (shoelace) area; positive when counter-clockwise."""
    n = len(ring)
    return sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1] for i in range(n))


def area_string(a2: int) -> str:
    """An area given as twice its value, as the decimal string of the suite's expected.json."""
    if a2 % 2 == 0:
        return str(a2 // 2)
    q = (a2 - 1) // 2
    if a2 < 0 and q == -1:
        return '-0.5'
    return f'{q}.5' if a2 > 0 else f'-{(-a2) // 2}.5'


def is_simple(ring) -> bool:
    """A simple polygon: at least three vertices, no two coincide, and edges meet only at the
    vertex two consecutive edges share."""
    n = len(ring)
    if n < 3:
        return False
    if len(set(ring)) != n:
        return False
    edges = [(ring[i], ring[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        a, b = edges[i]
        for j in range(i + 1, n):
            c, d = edges[j]
            if j == i + 1 or (i == 0 and j == n - 1):
                # adjacent: they share one vertex; they must not overlap beyond it
                shared = b if j == i + 1 else a
                other1 = a if j == i + 1 else b
                other2 = d if j == i + 1 else c
                if orient(other1, shared, other2) == 0 and sgn(dot(sub(other1, shared), sub(other2, shared))) > 0:
                    return False
                if n == 3 and orient(a, b, d if j == i + 1 else c) == 0:
                    return False
                continue
            if segments_touch(a, b, c, d):
                return False
    return True


def winding(p, ring) -> int:
    """Winding number of a closed walk around p (p not on the walk)."""
    w = 0
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        if a[1] <= p[1]:
            if b[1] > p[1] and orient(a, b, p) > 0:
                w += 1
        elif b[1] <= p[1] and orient(a, b, p) < 0:
            w -= 1
    return w


def on_ring(p, ring) -> bool:
    n = len(ring)
    return any(on_closed_segment(p, ring[i], ring[(i + 1) % n]) for i in range(n))


def locate(p, ring) -> str:
    """'on', 'in' or 'out' for a point and a simple polygon (either orientation)."""
    if on_ring(p, ring):
        return 'on'
    return 'in' if winding(p, ring) != 0 else 'out'


def rings_touch(r1, r2) -> bool:
    n1, n2 = len(r1), len(r2)
    for i in range(n1):
        for j in range(n2):
            if segments_touch(r1[i], r1[(i + 1) % n1], r2[j], r2[(j + 1) % n2]):
                return True
    return False


def least_first(ring):
    """Rotate a ring to start at its least vertex (least x, then least y)."""
    k = min(range(len(ring)), key=lambda i: (ring[i][0], ring[i][1]))
    return ring[k:] + ring[:k]


def dedupe_cyclic(points):
    """Remove each vertex equal to the one before it; the first counts as following the last."""
    out = []
    for p in points:
        if not out or out[-1] != p:
            out.append(p)
    while len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def dedupe_cyclic_open(points):
    """Remove each vertex equal to the one before it, in a path (the first does not follow the last)."""
    out = []
    for p in points:
        if not out or out[-1] != p:
            out.append(p)
    return out

"""Arc edges (Core 0.4, chapter 21): the polyline of an arc edge, made by iterated snap rounding, and its
length, stations and points.

An arc edge is a wall or a separator with ``"arc": {"sagitta": h}``: a circular arc from its start
junction S to its end junction E whose midpoint is |h| from the midpoint of the chord, to the left of the
chord (seen from S towards E) when h > 0 and to the right when h < 0. Nothing in Core computes with the
circle itself. Everything is derived from the arc's **polyline** (21.2): S, the rounded midpoint P of the
arc, then the polylines of the two arcs S->P and P->E - each with the sagitta, rounded, of its chord on the
circle of the arc it halves - until an arc's sagitta is at most TAU, when its polyline is its chord.

Every value here is an integer, a Fraction, or a Surd with one radicand, and every rounding is
round-half-to-even decided exactly (surd.py). There is no floating point and no transcendental function,
so the polyline of an arc is a function of its three integers alone.
"""

from __future__ import annotations

import math
from fractions import Fraction
from functools import lru_cache

from .surd import Surd

TAU = 1280                      # 21.2: the tolerance, 1 mm - an arc whose sagitta is at most TAU is its chord


def sqrt_q(q: Fraction) -> Surd:
    """The exact square root of a non-negative rational, as a Surd: sqrt(p/r) = sqrt(p r) / r."""
    q = Fraction(q)
    if q < 0:
        raise ValueError('square root of a negative number')
    return Surd.sqrt(q.numerator * q.denominator, Fraction(1, q.denominator))


def round_sqrt(m: int) -> int:
    """round(sqrt(m)) for an integer m >= 0. A tie needs (r + 1/2)^2 = m, which no integer is."""
    r = math.isqrt(m)
    return r + 1 if m > r * r + r else r


def fits(S, E, h) -> bool:
    """21.1.2: at most a semicircle - 4 h^2 <= |E - S|^2."""
    D = (E[0] - S[0]) ** 2 + (E[1] - S[1]) ** 2
    return 4 * h * h <= D


def midpoint(S, E, h):
    """21.2 step 2: the exact midpoint of the arc, M + h n / |d|, rounded once per coordinate."""
    dx, dy = E[0] - S[0], E[1] - S[1]
    D = dx * dx + dy * dy
    x = Surd(Fraction(S[0] + E[0], 2)) + Surd.sqrt(D, Fraction(-h * dy, D))
    y = Surd(Fraction(S[1] + E[1], 2)) + Surd.sqrt(D, Fraction(h * dx, D))
    return (x.round(), y.round())


def radius(S, E, h) -> Fraction:
    """The radius of the arc: (|d|^2 + 4 h^2) / (8 |h|)."""
    D = (E[0] - S[0]) ** 2 + (E[1] - S[1]) ** 2
    return Fraction(D + 4 * h * h, 8 * abs(h))


def sagitta_on(R: Fraction, A, B, sign: int) -> int:
    """21.2 step 3: the sagitta, rounded, of the chord AB on a circle of radius R - R - sqrt(R^2 - |AB|^2 / 4) -
    with the sign of the arc it is a part of."""
    C = (B[0] - A[0]) ** 2 + (B[1] - A[1]) ** 2
    v = Surd(R) - sqrt_q(R * R - Fraction(C, 4))
    return sign * v.round()


@lru_cache(maxsize=None)
def polyline(S, E, h):
    """21.2: the polyline of the arc S -> E with sagitta h, a tuple of integer points from S to E. The arc must
    fit (21.1.2)."""
    S, E = tuple(S), tuple(E)
    if abs(h) <= TAU:
        return (S, E)
    P = midpoint(S, E, h)
    R = radius(S, E, h)
    sign = 1 if h > 0 else -1
    h1, h2 = sagitta_on(R, S, P, sign), sagitta_on(R, P, E, sign)
    return polyline(S, P, h1) + polyline(P, E, h2)[1:]


def depth_of(S, E, h) -> int:
    """How many times 21.2 halves the arc on its deepest branch (for the tests' bounds)."""
    S, E = tuple(S), tuple(E)
    if abs(h) <= TAU:
        return 0
    P = midpoint(S, E, h)
    R = radius(S, E, h)
    sign = 1 if h > 0 else -1
    return 1 + max(depth_of(S, P, sagitta_on(R, S, P, sign)), depth_of(P, E, sagitta_on(R, P, E, sign)))


# ------------------------------------------------------------------------------ edges of a document

def sagitta(edge: dict):
    """An edge's sagitta, or None for a straight edge."""
    arc = edge.get('arc')
    return arc['sagitta'] if isinstance(arc, dict) else None


def edge_polyline(doc, eid, coll=None):
    """The polyline of a wall or separator: its arc's (21.2), or its two junctions' positions."""
    e = doc.walls.get(eid) if coll in (None, 'walls') else None
    if e is None:
        e = doc.separators[eid]
    S = tuple(doc.junctions[e['start']]['position'])
    E = tuple(doc.junctions[e['end']]['position'])
    h = sagitta(e)
    if h is None:
        return (S, E)
    return polyline(S, E, h)


def lengths(poly):
    """21.5: each segment's rounded length."""
    return [round_sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) for a, b in zip(poly, poly[1:])]


def length(poly) -> int:
    """21.5: an arc edge's length, the sum of its segments' rounded lengths."""
    return sum(lengths(poly))


def segment_at(poly, t):
    """21.5: (k, s) - the segment k (0-based) that the distance t along an arc edge falls on, half-open
    [s_k, s_k+1) except the last, which includes its end; and s, the station at its start. None when t is
    negative or past the end."""
    ls = lengths(poly)
    total = sum(ls)
    t = Fraction(t)
    if t < 0 or t > total:
        return None
    s = 0
    for k, l in enumerate(ls):
        if t < s + l or k == len(ls) - 1:
            return k, s
        s += l
    return None


def point_at(poly, t):
    """21.5: the exact point at distance t along an arc edge, (Fraction, Fraction)."""
    k, s = segment_at(poly, t)
    a, b = poly[k], poly[k + 1]
    l = lengths(poly)[k]
    f = (Fraction(t) - s) / l
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def wall_arc(doc, wid):
    """The polyline of an arc wall, or None for a straight wall. The arc must fit (21.1.2)."""
    w = doc.walls[wid]
    if sagitta(w) is None:
        return None
    return edge_polyline(doc, wid, 'walls')


def unfit(doc, wid) -> bool:
    """An arc wall whose arc does not fit (21.1.2) - FS-INV-113, or FS-INV-102 - and so has no length (10.3)."""
    w = doc.walls[wid]
    h = sagitta(w)
    if h is None:
        return False
    S, E = doc.junctions[w['start']]['position'], doc.junctions[w['end']]['position']
    return w['start'] == w['end'] or not fits(S, E, h)


def primitive(v):
    """A vector of integers (or rationals) as the shortest vector of integers in its direction."""
    fx, fy = Fraction(v[0]), Fraction(v[1])
    den = math.lcm(fx.denominator, fy.denominator)
    x, y = int(fx * den), int(fy * den)
    g = math.gcd(x, y) or 1
    return (x // g, y // g)

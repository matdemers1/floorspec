"""Exact real numbers of the form  a + b*sqrt(m) + c*sqrt(n)  with rational a, b, c.

Every derived coordinate of Floorspec Core 0.1 has this form (5.5): a face line is
A*x + B*y = p + q*sqrt(D) with integer A, B, D and rational p, q, so the intersection of two face
lines, and every foot of a junction on a face line, needs at most two distinct square roots.

Decisions - signs, comparisons, floors and round-half-to-even - are exact: they use only integer
and Fraction arithmetic. Floats appear only as a first guess for a floor, which the exact sign
test then corrects, and in ``__float__`` for sanity checks.
"""

from __future__ import annotations

import math
from fractions import Fraction


def _sgn(x) -> int:
    return (x > 0) - (x < 0)


def _square_root(m: int):
    """isqrt(m) if m is a perfect square, else None."""
    r = math.isqrt(m)
    return r if r * r == m else None


def _sign1(a: Fraction, b: Fraction, m: int) -> int:
    """Exact sign of a + b*sqrt(m), m >= 0."""
    if b == 0 or m == 0:
        return _sgn(a)
    sa, sb = _sgn(a), _sgn(b)
    if sa == 0 or sa == sb:
        return sb
    # opposite signs: compare a^2 with b^2*m
    return sa * _sgn(a * a - b * b * m)


class Surd:
    """a + sum(c_i * sqrt(m_i)), at most two distinct non-square radicands m_i > 1."""

    __slots__ = ('a', 't')

    def __init__(self, a=0, terms=None):
        self.a = Fraction(a)
        t: dict[int, Fraction] = {}
        for m, c in (terms or {}).items():
            c = Fraction(c)
            if c == 0 or m == 0:
                continue
            r = _square_root(m)
            if r is not None:
                self.a += c * r
                continue
            t[m] = t.get(m, Fraction(0)) + c
        self.t = {m: c for m, c in t.items() if c != 0}
        if len(self.t) > 2:
            raise ValueError('more than two radicands')

    @staticmethod
    def sqrt(m: int, coeff=1) -> 'Surd':
        return Surd(0, {m: coeff})

    @staticmethod
    def of(v) -> 'Surd':
        return v if isinstance(v, Surd) else Surd(v)

    def __add__(self, o):
        o = Surd.of(o)
        t = dict(self.t)
        for m, c in o.t.items():
            t[m] = t.get(m, Fraction(0)) + c
        return Surd(self.a + o.a, t)

    __radd__ = __add__

    def __neg__(self):
        return Surd(-self.a, {m: -c for m, c in self.t.items()})

    def __sub__(self, o):
        return self + (-Surd.of(o))

    def __rsub__(self, o):
        return Surd.of(o) - self

    def __mul__(self, o):
        if isinstance(o, Surd):
            if not o.t:
                o = o.a
            elif not self.t:
                return o * self.a
            else:
                terms: dict[int, Fraction] = {}
                a = self.a * o.a
                parts = [(1, self.a)] + list(self.t.items())
                qarts = [(1, o.a)] + list(o.t.items())
                for m, c in parts:
                    for n, d in qarts:
                        if m == 1 and n == 1:
                            continue
                        k = m * n
                        if m == n:
                            a += c * d * m
                        else:
                            terms[k] = terms.get(k, Fraction(0)) + c * d
                return Surd(a, terms)
        o = Fraction(o)
        return Surd(self.a * o, {m: c * o for m, c in self.t.items()})

    __rmul__ = __mul__

    def __truediv__(self, o):
        o = Fraction(o)
        return Surd(self.a / o, {m: c / o for m, c in self.t.items()})

    def sign(self) -> int:
        """Exact sign."""
        a = self.a
        items = list(self.t.items())
        if not items:
            return _sgn(a)
        if len(items) == 1:
            (m, b), = items
            return _sign1(a, b, m)
        (m, b), (n, c) = items
        # sign of X = b*sqrt(m) + c*sqrt(n)
        sb, sc = _sgn(b), _sgn(c)
        if sb == sc:
            sx = sb
        else:
            sx = sb * _sgn(b * b * m - c * c * n) if b * b * m != c * c * n else 0
        sa = _sgn(a)
        if sa == 0:
            return sx
        if sx == 0 or sx == sa:
            return sa
        # a and X have opposite signs: compare a^2 with X^2 = b^2 m + c^2 n + 2bc sqrt(mn)
        t = _sign1(a * a - b * b * m - c * c * n, -2 * b * c, m * n)
        if t > 0:
            return sa
        if t < 0:
            return sx
        return 0

    def is_zero(self) -> bool:
        return self.sign() == 0

    def __eq__(self, o):
        return (self - Surd.of(o)).sign() == 0

    def __lt__(self, o):
        return (self - Surd.of(o)).sign() < 0

    def __le__(self, o):
        return (self - Surd.of(o)).sign() <= 0

    def __gt__(self, o):
        return (self - Surd.of(o)).sign() > 0

    def __ge__(self, o):
        return (self - Surd.of(o)).sign() >= 0

    __hash__ = None

    def __float__(self):
        return float(self.a) + sum(float(c) * math.sqrt(m) for m, c in self.t.items())

    def floor(self) -> int:
        """Exact floor: a float guess, corrected by exact sign tests."""
        try:
            k = math.floor(float(self))
        except (OverflowError, ValueError):
            k = math.floor(self.a)
        while (self - k).sign() < 0:
            k -= 1
        while (self - (k + 1)).sign() >= 0:
            k += 1
        return k

    def round(self) -> int:
        """round(): nearest integer, ties to even (0.3), decided exactly."""
        k = self.floor()
        s = (self - Fraction(2 * k + 1, 2)).sign()
        if s < 0:
            return k
        if s > 0:
            return k + 1
        return k if k % 2 == 0 else k + 1

    def __repr__(self):
        parts = [str(self.a)] + [f'{c}*sqrt({m})' for m, c in self.t.items()]
        return 'Surd(' + ' + '.join(parts) + ')'

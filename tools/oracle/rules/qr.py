"""Exact numbers a + b*sqrt(m) with rational a, b and one integer radicand m >= 0: the field Q(sqrt m).

Local coordinates in a frame (Core 13.1) are of this form: a frame's facing vector f is a vector of
integers, its origin's coordinates are in Q(sqrt |f|^2), and a plan point's local coordinates are
(P - O).f / |f| and (P - O).(-fy, fx) / |f|. Clipping a polygon in local coordinates adds, multiplies
and divides such numbers, and stays in the field. Signs, comparisons, floors and rounding are exact.
"""

from __future__ import annotations

import math
from fractions import Fraction


def _sgn(x) -> int:
    return (x > 0) - (x < 0)


class QR:
    __slots__ = ('a', 'b', 'm')

    def __init__(self, a=0, b=0, m=0):
        a, b = Fraction(a), Fraction(b)
        r = math.isqrt(m) if m >= 0 else None
        if b == 0 or m == 0 or (r is not None and r * r == m):
            a, b, m = a + (b * r if b and m else 0), Fraction(0), 0
        self.a, self.b, self.m = a, b, m

    def _m(self, o: 'QR') -> int:
        if self.m and o.m and self.m != o.m:
            raise ValueError('two radicands')
        return self.m or o.m

    @staticmethod
    def of(v) -> 'QR':
        return v if isinstance(v, QR) else QR(v)

    def __add__(self, o):
        o = QR.of(o)
        return QR(self.a + o.a, self.b + o.b, self._m(o))

    __radd__ = __add__

    def __neg__(self):
        return QR(-self.a, -self.b, self.m)

    def __sub__(self, o):
        return self + (-QR.of(o))

    def __rsub__(self, o):
        return QR.of(o) - self

    def __mul__(self, o):
        o = QR.of(o)
        m = self._m(o)
        return QR(self.a * o.a + self.b * o.b * m, self.a * o.b + self.b * o.a, m)

    __rmul__ = __mul__

    def __truediv__(self, o):
        o = QR.of(o)
        m = self._m(o)
        den = o.a * o.a - o.b * o.b * m
        if den == 0:
            raise ZeroDivisionError
        num = self * QR(o.a, -o.b, m)
        return QR(num.a / den, num.b / den, m)

    def __rtruediv__(self, o):
        return QR.of(o) / self

    def sign(self) -> int:
        a, b, m = self.a, self.b, self.m
        if b == 0:
            return _sgn(a)
        sa, sb = _sgn(a), _sgn(b)
        if sa == 0 or sa == sb:
            return sb
        return sa * _sgn(a * a - b * b * m)

    def __eq__(self, o):
        return (self - QR.of(o)).sign() == 0

    def __lt__(self, o):
        return (self - QR.of(o)).sign() < 0

    def __le__(self, o):
        return (self - QR.of(o)).sign() <= 0

    def __gt__(self, o):
        return (self - QR.of(o)).sign() > 0

    def __ge__(self, o):
        return (self - QR.of(o)).sign() >= 0

    __hash__ = None

    def __float__(self):
        return float(self.a) + float(self.b) * math.sqrt(self.m)

    def floor(self) -> int:
        k = math.floor(float(self))
        while (self - k).sign() < 0:
            k -= 1
        while (self - (k + 1)).sign() >= 0:
            k += 1
        return k

    def round(self) -> int:
        """Nearest integer, ties to even (Core 0.3)."""
        k = self.floor()
        s = (self - Fraction(2 * k + 1, 2)).sign()
        if s < 0:
            return k
        if s > 0:
            return k + 1
        return k if k % 2 == 0 else k + 1

    def __repr__(self):
        return f'QR({self.a} + {self.b}*sqrt({self.m}))'


def from_surd(s) -> QR:
    """A Surd of the Core oracle with at most one radical, as a QR."""
    if not s.t:
        return QR(s.a)
    (m, c), = s.t.items()
    return QR(s.a, c, m)


def round_frac(x: Fraction) -> int:
    """round() of a rational: nearest integer, ties to even."""
    k = math.floor(x)
    r = x - k
    if r < Fraction(1, 2):
        return k
    if r > Fraction(1, 2):
        return k + 1
    return k if k % 2 == 0 else k + 1


def round_div_sqrt(k: int, n: int) -> int:
    """round(k / sqrt(n)) for integers k and n > 0, exactly."""
    if k < 0:
        return -round_div_sqrt(-k, n)
    f = math.isqrt(k * k // n)                  # floor(k / sqrt(n))
    while (f + 1) * (f + 1) * n <= k * k:
        f += 1
    while f * f * n > k * k:
        f -= 1
    lhs, rhs = 4 * k * k, (2 * f + 1) * (2 * f + 1) * n
    if lhs < rhs:
        return f
    if lhs > rhs:
        return f + 1
    return f if f % 2 == 0 else f + 1


def round_sqrt(n: int) -> int:
    """round(sqrt(n)) for an integer n >= 0 (never a tie: (2k + 1)^2 / 4 is not an integer)."""
    k = math.isqrt(n)
    return k + 1 if 4 * n > (2 * k + 1) * (2 * k + 1) else k

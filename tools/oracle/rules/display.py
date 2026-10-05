"""9.6: values as a person reads them, each rounded once from the exact value."""

from __future__ import annotations

from fractions import Fraction
from math import gcd

from .qr import round_frac

SQFT = 152212340736          # square base units in a square foot
SQM = 1638400000000          # square base units in a square metre


def length(v: int, units: str) -> str:
    if units == 'metric':
        return f'{round_frac(Fraction(v, 1280))} mm'
    n = round_frac(Fraction(v, 2032))
    sign, m = ('-' if n < 0 else ''), abs(n)
    feet, rest = divmod(m, 192)
    inches, six = divmod(rest, 16)
    if six == 0:
        return f'{sign}{feet}\' {inches}"'
    g = gcd(six, 16)
    return f'{sign}{feet}\' {inches} {six // g}/{16 // g}"'


def area(a: Fraction, units: str) -> str:
    n = round_frac(Fraction(a) * 100 / (SQM if units == 'metric' else SQFT))
    sign, m = ('-' if n < 0 else ''), abs(n)
    return f'{sign}{m // 100}.{m % 100:02d} ' + ('m²' if units == 'metric' else 'sq ft')


def value(typ: str, v, units: str, unit=None) -> str:
    if v is None:
        return 'not stated'
    if typ == 'length':
        return length(v, units)
    if typ == 'area':
        return area(v, units)
    if typ in ('count', 'integer'):
        return f'{v} {unit}' if unit else str(v)
    if typ == 'boolean':
        return 'yes' if v else 'no'
    if typ == 'term':
        return v
    if typ == 'terms':
        return ', '.join(sorted(v)) if v else 'none'
    raise ValueError(typ)


def threshold(typ: str, op: str, t, units: str, unit=None) -> str:
    if op == 'in':
        return ', '.join(value(typ, x if typ != 'area' else Fraction(x), units, unit) for x in t)
    if op == 'has':
        return t
    return value(typ, Fraction(t) if typ == 'area' else t, units, unit)

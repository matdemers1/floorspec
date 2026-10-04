"""The strings of the reference grammar (Ops 3.1, 3.2, 3.5): lengths, and the forms of points,
vectors and positions. Resolving the junctions and walls those forms name is `select`'s job.

Lengths follow the ABNF of 3.1 exactly. Whitespace (space or tab) is permitted between any two
grammar elements but not inside a decimal or a unit word; in `mixed`, the separator between the
whole inches and the fraction is either "-" (whitespace around it allowed) or at least one
whitespace character. Letters are case-insensitive. The value is an exact Fraction of base units,
rounded once, ties to even.
"""

from __future__ import annotations

import re
from fractions import Fraction

from .errors import OpsError

MM, CM, M = 1280, 12800, 1_280_000
IN, FT = 32512, 390144

_S = r'[ \t]*'
_DEC = r'(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)'
_INCH = rf'(?:[0-9]+(?:{_S}-{_S}|[ \t]+)[0-9]+{_S}/{_S}[0-9]+|[0-9]+{_S}/{_S}[0-9]+|{_DEC})'

_METRIC = re.compile(rf'{_S}(?P<neg>-)?{_S}(?P<v>{_DEC}){_S}(?P<u>mm|cm|m){_S}', re.I)
_FEET = re.compile(rf"{_S}(?P<neg>-)?{_S}(?P<ft>{_DEC}){_S}(?:'|ft)(?:{_S}-?{_S}(?P<inch>{_INCH}){_S}(?:\"|in))?{_S}", re.I)
_INCHES = re.compile(rf'{_S}(?P<neg>-)?{_S}(?P<inch>{_INCH}){_S}(?:"|in){_S}', re.I)
_MIXED = re.compile(rf'(?P<w>[0-9]+)(?:{_S}-{_S}|[ \t]+)(?P<n>[0-9]+){_S}/{_S}(?P<d>[0-9]+)')
_FRAC = re.compile(rf'(?P<n>[0-9]+){_S}/{_S}(?P<d>[0-9]+)')

DIRECTIONS = {'north': (0, 1), 'south': (0, -1), 'east': (1, 0), 'west': (-1, 0)}
_DIR = r'(?P<dir>north|south|east|west)'

# "<length> from <junction> toward <junction>"
FROM_TOWARD = re.compile(r'(?P<len>.+?)[ \t]+from[ \t]+(?P<a>.+?)[ \t]+toward[ \t]+(?P<b>.+)', re.I | re.S)
# "<length> <direction> of <junction>"
DIR_OF = re.compile(rf'(?P<len>.+?)[ \t]+{_DIR}[ \t]+of[ \t]+(?P<j>.+)', re.I | re.S)
# "<length> <direction>"
VECTOR = re.compile(rf'(?P<len>.+?)[ \t]+{_DIR}', re.I | re.S)
# "<length> from start" / "<length> from end"
FROM_END = re.compile(r'(?P<len>.+?)[ \t]+from[ \t]+(?P<which>start|end)', re.I | re.S)
CENTERED = re.compile(r'[ \t]*centered[ \t]*', re.I)


def _decimal(s: str) -> Fraction:
    if '.' in s:
        ip, fp = s.split('.')
        return Fraction(int(ip or '0') * 10 ** len(fp) + int(fp), 10 ** len(fp))
    return Fraction(int(s))


def _inches(s: str, pointer) -> Fraction:
    m = _MIXED.fullmatch(s)
    if m:
        d = int(m['d'])
        if d == 0:
            raise OpsError('FS-OPS-012', pointer=pointer, note='a fraction with a zero denominator')
        return int(m['w']) + Fraction(int(m['n']), d)
    m = _FRAC.fullmatch(s)
    if m:
        d = int(m['d'])
        if d == 0:
            raise OpsError('FS-OPS-012', pointer=pointer, note='a fraction with a zero denominator')
        return Fraction(int(m['n']), d)
    return _decimal(s)


def exact_length(s: str, pointer=None) -> Fraction:
    """The exact value, in base units, of a length string; FS-OPS-012 if it is not one."""
    m = _METRIC.fullmatch(s)
    if m:
        v = _decimal(m['v']) * {'mm': MM, 'cm': CM, 'm': M}[m['u'].lower()]
    else:
        m = _FEET.fullmatch(s)
        if m:
            v = _decimal(m['ft']) * FT
            if m['inch'] is not None:
                v += _inches(m['inch'], pointer) * IN
        else:
            m = _INCHES.fullmatch(s)
            if not m:
                raise OpsError('FS-OPS-012', pointer=pointer, note=f'{s!r} is not a length')
            v = _inches(m['inch'], pointer) * IN
    return -v if m['neg'] else v


def length(v, pointer=None) -> int:
    """A length (3.1): a JSON integer as it is, or a string resolved and rounded once, ties to even."""
    if type(v) is int:
        return v
    if isinstance(v, str):
        return round(exact_length(v, pointer))       # Fraction.__round__: half to even
    raise OpsError('FS-OPS-012', pointer=pointer, note='not a length')


def half(v: int) -> int:
    """v / 2, rounded once, ties to even (4.4: anchors move by v / 2)."""
    return round(Fraction(v, 2))

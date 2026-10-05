"""Known extensions (Core 0.2, chapter 12): registry entries, version precedence, version ranges.

``load(data)`` checks a validator's known extensions - a JSON array of registry entries - as 12.2.1
requires, and returns them, or None when they break it (FS-CFG-001). ``satisfies(v, range)``
evaluates a version range exactly as 12.3 defines. The structural check of an entry is transcribed
from the registry entry schema (schema/registry/0.1/extension.schema.json) by hand.
"""

from __future__ import annotations

import re

from .jsonparse import Malformed, parse

EXT_RE = re.compile(r'(?:FS|EXT|[A-Z0-9]{2,8})_[A-Za-z0-9]+')
_ID = r'(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)'
SEMVER = r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-' + _ID + r'(?:\.' + _ID + r')*)?'
SEMVER_RE = re.compile(SEMVER)
_CMP = r'(?:>=|>|<=|<|=|\^|~)?' + SEMVER
_SET = _CMP + r'(?: +' + _CMP + r')*'
RANGE_RE = re.compile(_SET + r'(?: +\|\| +' + _SET + r')*')
TERM_RE = re.compile(r'[a-z][A-Za-z0-9]*')
HTTPS_RE = re.compile(r"https://(?:[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=-]|%[0-9A-Fa-f]{2})+")
STATUSES = {'proposal', 'draft', 'releaseCandidate', 'ratified'}


# ------------------------------------------------------------------------------ versions

def parse_version(v: str):
    """(major, minor, patch, prerelease identifiers or None). A missing patch reads as 0 (12.2)."""
    core, sep, pre = v.partition('-')
    parts = [int(x) for x in core.split('.')]
    if len(parts) == 2:
        parts.append(0)
    return (parts[0], parts[1], parts[2], pre.split('.') if sep else None)


def _cmp_ident(a: str, b: str) -> int:
    an, bn = a.isdigit(), b.isdigit()
    if an and bn:
        return (int(a) > int(b)) - (int(a) < int(b))
    if an != bn:
        return -1 if an else 1                       # numeric identifiers are lower
    return (a > b) - (a < b)                         # ASCII order


def compare(a: str, b: str) -> int:
    """Semantic Versioning 2.0.0 precedence (11): -1, 0 or 1."""
    pa, pb = parse_version(a), parse_version(b)
    if pa[:3] != pb[:3]:
        return -1 if pa[:3] < pb[:3] else 1
    ra, rb = pa[3], pb[3]
    if ra is None or rb is None:
        return 0 if ra is rb else (1 if ra is None else -1)
    for x, y in zip(ra, rb):
        c = _cmp_ident(x, y)
        if c:
            return c
    return (len(ra) > len(rb)) - (len(ra) < len(rb))


def _comparator(x: str, c: str) -> bool:
    m = re.match(r'(>=|>|<=|<|=|\^|~)?(.*)', c)
    op, v = m.group(1) or '=', m.group(2)
    k = compare(x, v)
    if op == '=':
        return k == 0
    if op == '>=':
        return k >= 0
    if op == '>':
        return k > 0
    if op == '<=':
        return k <= 0
    if op == '<':
        return k < 0
    M, mi, p, _ = parse_version(v)
    if op == '~':
        upper = f'{M}.{mi + 1}.0'
    elif M > 0:
        upper = f'{M + 1}.0.0'
    elif mi > 0:
        upper = f'0.{mi + 1}.0'
    else:
        upper = f'0.0.{p + 1}'
    return k >= 0 and compare(x, upper) < 0


def satisfies(version: str, rng: str) -> bool:
    """12.3: some set of the range has every comparator satisfied."""
    return any(all(_comparator(version, c) for c in s.split()) for s in re.split(r' +\|\| +', rng))


# ------------------------------------------------------------------------------ entries

def _str(v, lo=1, hi=200) -> bool:
    return isinstance(v, str) and lo <= len(v) <= hi


def entry_ok(e) -> bool:
    """The registry entry schema, transcribed."""
    if not isinstance(e, dict):
        return False
    allowed = {'name', 'version', 'status', 'schema', 'title', 'requires', 'kinds', 'terms', 'implementations'}
    if set(e) - allowed or not {'name', 'version', 'status', 'schema'} <= set(e):
        return False
    if not (isinstance(e['name'], str) and EXT_RE.fullmatch(e['name'])):
        return False
    if not (isinstance(e['version'], str) and SEMVER_RE.fullmatch(e['version'])):
        return False
    if not isinstance(e['status'], str) or e['status'] not in STATUSES:
        return False
    if not (isinstance(e['schema'], str) and HTTPS_RE.fullmatch(e['schema'])):
        return False
    if 'title' in e and not _str(e['title']):
        return False
    req = e.get('requires', {})
    if not isinstance(req, dict) or any(not EXT_RE.fullmatch(k) or not isinstance(r, str) or not RANGE_RE.fullmatch(r)
                                        for k, r in req.items()):
        return False
    kinds = e.get('kinds', {})
    if not isinstance(kinds, dict):
        return False
    for k, kind in kinds.items():
        if not TERM_RE.fullmatch(k) or not isinstance(kind, dict) or set(kind) - {'title', 'fallback'}:
            return False
        if 'title' in kind and not _str(kind['title']):
            return False
        fb = kind.get('fallback', {})
        if not isinstance(fb, dict) or set(fb) - {'asset', 'symbol'} or any(not isinstance(x, bool) for x in fb.values()):
            return False
    terms = e.get('terms', {})
    if not isinstance(terms, dict) or set(terms) - {'roomFunctions'}:
        return False
    rf = terms.get('roomFunctions', [])
    if (not isinstance(rf, list) or any(not isinstance(t, str) or not TERM_RE.fullmatch(t) for t in rf)
            or len(set(rf)) != len(rf)):
        return False
    impl = e.get('implementations', [])
    if not isinstance(impl, list):
        return False
    for i in impl:
        if not isinstance(i, dict) or set(i) != {'name', 'url'} or not _str(i['name']) \
                or not (isinstance(i['url'], str) and HTTPS_RE.fullmatch(i['url'])):
            return False
    if e['status'] == 'ratified' and ('implementations' not in e or len(impl) < 2):
        return False
    return True


def _cyclic(entries) -> bool:
    edges: dict[str, set[str]] = {}
    for e in entries:
        edges.setdefault(e['name'], set()).update(e.get('requires', {}))
    state: dict[str, int] = {}

    def visit(n) -> bool:
        if state.get(n) == 1:
            return True
        if state.get(n) == 2:
            return False
        state[n] = 1
        if any(visit(m) for m in sorted(edges.get(n, ()))):
            return True
        state[n] = 2
        return False
    return any(visit(n) for n in sorted(edges))


def load(data: bytes):
    """The known extensions as a list of entries, or None when they break 12.2.1 (FS-CFG-001)."""
    try:
        value, codes = parse(data)
    except Malformed:
        return None
    if codes or not isinstance(value, list) or not all(entry_ok(e) for e in value):
        return None
    for i, a in enumerate(value):
        for b in value[i + 1:]:
            if a['name'] == b['name'] and compare(a['version'], b['version']) == 0:
                return None
    if _cyclic(value):
        return None
    return value


def entry_for(known, name: str, version: str):
    """The known entry of `name` at a version equal to `version`, or None (12.2)."""
    for e in known or ():
        if e['name'] == name and compare(e['version'], version) == 0:
            return e
    return None

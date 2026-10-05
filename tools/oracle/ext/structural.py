"""FS_structural 0.1.0 (registry/FS_structural/spec.md): its schema tier over the data on core
elements, its invariants, lints and derived values, written from the extension's specification alone.

FS_structural adds no kind of element: its data is each wall's, opening's, slab's, room's and roof's
own `extensions.FS_structural` (1.3). Nothing here sizes or checks a structure (1.4): every rule is
about the record's consistency with itself and with the house's geometry.
"""

from __future__ import annotations

from fractions import Fraction
from math import isqrt

from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_structural', '0.1.0', 'STRC'
CORE = ('0.2', '0.3')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'structural')
SEVERITY = {'FS-STRC-LINT-001': 'warning', 'FS-STRC-LINT-002': 'warning', 'FS-STRC-LINT-003': 'warning',
            'FS-STRC-LINT-004': 'warning', 'FS-STRC-LINT-005': 'warning', 'FS-STRC-LINT-006': 'info'}
DEFINED = ('walls', 'openings', 'slabs', 'rooms', 'roofs')          # 1.3: where its data may be
# 1.3.3: every other element that has an `extensions` member (Core 0.2 and 0.3)
OTHERS = ('buildings', 'levels', 'junctions', 'separators', 'types', 'materials', 'assets', 'stairs',
          'optionSets', 'options')
MEMBER_SYSTEMS = ('studs', 'joists', 'rafters', 'trusses')        # 2.2
NO_MEMBERS = ('solid', 'panels')
UNFRAMED = ('concrete', 'concreteMasonry', 'masonry')


def _data(el):
    x = el.get('extensions', {}) if isinstance(el, dict) else {}
    return x.get(NAME) if isinstance(x, dict) else None


def schema_errors(doc, data) -> list[str]:
    """1.3.1 to 1.3.3: the top-level data, and the data on every element, against the schema."""
    d = doc.d
    out = list(SCHEMA.errors(data))
    core = SCHEMA.root['$defs']['coreElements']
    for c in DEFINED:
        for eid, el in d.get(c, {}).items():
            v = _data(el)
            if v is not None:
                out.extend(f'{c}/{eid}{e}' for e in SCHEMA.errors({c: v}, core))
    others = [(c, d.get(c, {})) for c in OTHERS] + [('items', d.get('program', {}).get('items', {}))]
    for c, elements in others:
        for eid, el in elements.items():
            if _data(el) is not None:
                out.append(f'{c}/{eid}: may not carry {NAME} data')
    return out


def _carriers(ctx: Context):
    """(collection, ID, data) of every element that carries FS_structural data, in a fixed order."""
    for c in DEFINED:
        for eid in sorted(ctx.d.get(c, {})):
            v = _data(ctx.d[c][eid])
            if v is not None:
                yield c, eid, v


def _framings(ctx: Context):
    """(ID, framing) of every framing: a wall's, a slab's, a room's floor's, a roof's."""
    for c, eid, v in _carriers(ctx):
        f = v.get('floor', {}).get('framing') if c == 'rooms' else v.get('framing')
        if f is not None:
            yield eid, f


def _spans(ctx: Context):
    """(ID, span) of every slab's span and every room's floor's span."""
    for c, eid, v in _carriers(ctx):
        s = v.get('floor', {}).get('span') if c == 'rooms' else (v.get('span') if c == 'slabs' else None)
        if s is not None:
            yield c, eid, s


def invariants(ctx: Context):
    ds = []
    for eid, f in _framings(ctx):
        inv1 = f['system'] in NO_MEMBERS and ('member' in f or 'spacing' in f)          # 2.2.1
        inv3 = f['material'] in UNFRAMED and f['system'] in MEMBER_SYSTEMS              # 2.2.3
        if inv1:
            ds.append(ctx.diag('FS-STRC-INV-001', [eid]))
        if inv3:
            ds.append(ctx.diag('FS-STRC-INV-003', [eid]))
        if not inv1 and not inv3 and 'member' in f and 'spacing' in f \
                and f['spacing'] < f['member']['width']:                                # 2.2.2, 4.2
            ds.append(ctx.diag('FS-STRC-INV-002', [eid]))
    for _, eid, s in _spans(ctx):
        if s['direction'] == [0, 0]:                                                    # 3.1.1
            ds.append(ctx.diag('FS-STRC-INV-004', [eid]))
    return ds


def _bearing(ctx: Context, wid) -> bool:
    v = _data(ctx.d['walls'][wid])
    return v is not None and v.get('bearing') is True


def _round_div_sqrt(q, n: int) -> int:
    """round(q / sqrt(n)) for a rational q >= 0 and an integer n > 0, ties to even (Core 2.2)."""
    q = Fraction(q)
    a, b = q.numerator, q.denominator
    k = isqrt(a * a // (b * b * n))                 # floor(q / sqrt(n))
    while (k + 1) * (k + 1) * b * b * n <= a * a:
        k += 1
    while k * k * b * b * n > a * a:
        k -= 1
    lhs, rhs = 4 * a * a, (2 * k + 1) * (2 * k + 1) * b * b * n     # q/sqrt(n) against k + 1/2
    if lhs > rhs or (lhs == rhs and k % 2 == 1):
        return k + 1
    return k


def extent(points, direction) -> int:
    """3.2: how far the outline reaches along the direction, rounded once."""
    dx, dy = direction
    proj = [p[0] * dx + p[1] * dy for p in points]
    return _round_div_sqrt(max(proj) - min(proj), dx * dx + dy * dy)


def _outline(ctx: Context, c, eid):
    if c == 'slabs':
        return [tuple(p) for p in ctx.d['slabs'][eid]['boundary']]
    from ..floors import room_rings
    outer, _ = room_rings(ctx.doc, eid)
    return outer


def lints(ctx: Context):
    ds = []
    doc = ctx.doc
    for oid in sorted(doc.openings):
        o = doc.openings[oid]
        wid = o['wall']
        v = _data(o) or {}
        h = v.get('header')
        if h is None:
            if _bearing(ctx, wid):
                ds.append(ctx.diag('FS-STRC-LINT-001', [oid, wid]))
            continue
        thickness = doc.thickness(wid)
        if thickness is not None and h.get('plies', 1) * h['member']['width'] > thickness:
            ds.append(ctx.diag('FS-STRC-LINT-002', [oid, wid]))
        _, height, sill = doc.opening_dims(oid)
        room = doc.top_elevation(wid) - doc.base_elevation(wid) - (sill + height)
        if h['member']['depth'] > room:
            ds.append(ctx.diag('FS-STRC-LINT-004', [oid, wid]))
    for wid in sorted(doc.walls):
        v = _data(doc.walls[wid])
        if v is None:
            continue
        f = v.get('framing')
        if f is not None and f['system'] == 'studs' and 'member' in f:
            t = doc.thickness(wid)
            if t is not None and f['member']['depth'] > t:
                ds.append(ctx.diag('FS-STRC-LINT-003', [wid]))
        if v.get('bearing') is True and f is None:
            ds.append(ctx.diag('FS-STRC-LINT-006', [wid]))
    for c, eid, s in _spans(ctx):
        if 'length' in s and s['length'] > extent(_outline(ctx, c, eid), s['direction']):
            ds.append(ctx.diag('FS-STRC-LINT-005', [eid]))
    return ds


def derive(ctx: Context) -> dict:
    doc = ctx.doc
    levels = {}
    for lid in sorted(doc.levels):
        walls = [w for w in sorted(doc.walls) if doc.walls[w]['level'] == lid]
        bearing = [w for w in walls if _bearing(ctx, w)]
        shear = [w for w in walls if (_data(doc.walls[w]) or {}).get('shear') is True]
        openings = sorted(o for o, el in doc.openings.items() if el['wall'] in bearing)
        levels[lid] = {'bearing': sorted(bearing), 'shear': sorted(shear), 'openings': openings}
    spans = {}
    for c, eid, s in sorted(_spans(ctx), key=lambda x: x[1]):
        e = extent(_outline(ctx, c, eid), s['direction'])
        spans[eid] = {'direction': list(s['direction']), 'extent': e, 'span': s.get('length', e)}
    flagged = sorted(eid for _, eid, v in _carriers(ctx) if v.get('needsEngineer') is True)
    return {'levels': levels, 'spans': spans, 'needsEngineer': flagged}

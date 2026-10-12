"""FS_landscape 0.1.0 (registry/FS_landscape/spec.md): its invariants, lints and derived values,
written from the extension's specification alone."""

from __future__ import annotations

from math import isqrt

from .. import frames, plane
from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_landscape', '0.1.0', 'LAND'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'landscape')
SEVERITY = {'FS-LAND-LINT-001': 'warning', 'FS-LAND-LINT-002': 'info', 'FS-LAND-LINT-003': 'info'}
KINDS = ('plants', 'beds', 'lawns', 'hardscape')
MM = 1280
# 2.3: the lower bounds of medium and large, by form, in millimetres
BOUNDS = {'tree': (8000, 14000), 'shrub': (900, 2000), 'grass': (600, 1200), 'groundcover': (150, 300)}


def size_class(form: str, h: int) -> str:
    """2.3: a plant's size class from its form and its height."""
    m, l = BOUNDS[form]
    return 'small' if h < m * MM else 'medium' if h < l * MM else 'large'


def elements(ctx: Context):
    """(kind, ID, element) of every element of FS_landscape."""
    for kind in KINDS:
        for eid, el in ctx.coll(kind).items():
            yield kind, eid, el


def _plan(ctx: Context, el, points):
    """3.4: local points taken to the plan by the element's frame, exactly, and rounded once."""
    frame = frames.element_frame(ctx.doc, el)
    out = []
    for p, q in points:
        x, y = frame.plan(p, q)
        out.append((x.round(), y.round()))
    return out


def _position(ctx: Context, el):
    """6.1: a plant's position, its placement's point in plan."""
    return tuple(frames.host_frame(ctx.doc, el['host']).placement()['point'][:2])


def invariants(ctx: Context):
    ds = []
    for kind, eid, el in elements(ctx):
        host = el.get('host')
        if host is not None and (host['mode'] == 'wallFace' or (host['mode'] == 'surface' and host['surface'] == 'ceiling')):
            ds.append(ctx.diag('FS-LAND-INV-001', [eid]))                        # 3.2.2
        if kind == 'plants':
            if host is None:
                ds.append(ctx.diag('FS-LAND-INV-002', [eid]))                    # 3.2.1
            box = el['fallback']['box']
            if 'clearHeight' in el and el['clearHeight'] >= box['max'][2] - box['min'][2]:
                ds.append(ctx.diag('FS-LAND-INV-003', [eid]))                    # 2.2.1
        elif kind in ('beds', 'lawns'):
            ring = [tuple(p) for p in el['boundary']]
            if not plane.is_simple(ring) or plane.area2(ring) == 0:
                ds.append(ctx.diag('FS-LAND-INV-004', [eid]))                    # 3.4.1
        else:
            pts = el['points']
            if any(pts[i] == pts[i + 1] for i in range(len(pts) - 1)):
                ds.append(ctx.diag('FS-LAND-INV-005', [eid]))                    # 3.4.2
    return ds


def inside_box(kind: str, el) -> bool:
    """3.5: an element's geometry inside its box, horizontally and exactly, in its frame."""
    (x0, y0, _), (x1, y1, _) = el['fallback']['box']['min'], el['fallback']['box']['max']
    if kind == 'plants':
        return x0 <= 0 <= x1 and y0 <= 0 <= y1
    if kind in ('beds', 'lawns'):
        return all(x0 <= p <= x1 and y0 <= q <= y1 for p, q in el['boundary'])
    h = el['width'] // 2
    return all(x0 <= p - h and p + h <= x1 and y0 <= q - h and q + h <= y1 for p, q in el['points'])


def _beds(ctx: Context):
    """{ID: (level, outline in plan)} of every bed."""
    return {eid: (el['fallback']['level'], _plan(ctx, el, el['boundary'])) for eid, el in ctx.coll('beds').items()}


def lints(ctx: Context):
    ds = []
    doc = ctx.doc
    beds = _beds(ctx)
    rooms = ctx.rooms()
    for kind, eid, el in elements(ctx):
        if not inside_box(kind, el):
            ds.append(ctx.diag('FS-LAND-LINT-001', [eid]))                       # 3.5
    for eid, el in ctx.coll('plants').items():
        level = el['fallback']['level']
        pos = _position(ctx, el)
        in_bed = any(lv == level and plane.locate(pos, ring) == 'in' for lv, ring in beds.values())
        if not in_bed:
            for sid, s in sorted(doc.d.get('slabs', {}).items()):                  # 5.3: a plant on paving
                if s['level'] == level and plane.locate(pos, [tuple(p) for p in s['boundary']]) == 'in':
                    ds.append(ctx.diag('FS-LAND-LINT-002', [eid, sid]))
        rid = rooms.get(eid)
        if rid is not None and doc.rooms[rid].get('function', 'unspecified') != 'exterior':
            ds.append(ctx.diag('FS-LAND-LINT-003', [eid, rid]))                  # 5.3: a plant indoors
    return ds


def _round_sqrt(n: int) -> int:
    """round(sqrt(n)) for an integer n >= 0: never a tie, since (k + 1/2)^2 is never an integer."""
    k = isqrt(n)
    return k + 1 if n - k * k > k else k


def length(points) -> int:
    """6.4: the sum of a line's segments' lengths, each rounded once."""
    return sum(_round_sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) for a, b in zip(points, points[1:]))


def derive(ctx: Context) -> dict:
    rooms = ctx.rooms()
    beds = _beds(ctx)
    plants, positions = {}, {}
    for eid, el in sorted(ctx.coll('plants').items()):
        (x0, y0, z0), (x1, y1, z1) = el['fallback']['box']['min'], el['fallback']['box']['max']
        pos = _position(ctx, el)
        positions[eid] = (el['fallback']['level'], pos)
        p = {'form': el['form'], 'size': size_class(el['form'], z1 - z0), 'spread': max(x1 - x0, y1 - y0),
             'height': z1 - z0, 'position': list(pos)}
        if rooms.get(eid) is not None:
            p['room'] = rooms[eid]
        plants[eid] = p
    out_beds = {}
    for eid, (level, ring) in sorted(beds.items()):
        inside = sorted(pid for pid, (lv, pos) in positions.items() if lv == level and plane.locate(pos, ring) == 'in')
        out_beds[eid] = {'area': plane.area_string(abs(plane.area2(ring))), 'plants': inside}
    lawns = {eid: {'area': plane.area_string(abs(plane.area2(_plan(ctx, el, el['boundary']))))}
             for eid, el in sorted(ctx.coll('lawns').items())}
    hard = {eid: {'form': el['form'], 'length': length(el['points'])} for eid, el in sorted(ctx.coll('hardscape').items())}
    return {'plants': plants, 'beds': out_beds, 'lawns': lawns, 'hardscape': hard}

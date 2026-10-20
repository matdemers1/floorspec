"""FS_energy 0.1.0 (registry/FS_energy/spec.md): its invariants, lints and derived values, written from
the extension's specification alone.

FS_energy's arrays lie on Core's roofs: it reads a roof's footprint, its edges' kinds and pitches
(Core 16.1, 16.2), the faces Core derives for it (Core 16.5, through tools/oracle/roofs.py) and an
array's frame - its free host's (Core 13.1, through tools/oracle/frames.py). Every value it derives
is exact: a length up a slope is projected to plan once, and every corner is mapped and rounded
once."""

from __future__ import annotations

from fractions import Fraction

from .. import frames, plane, roofs
from ..surd import Surd
from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_energy', '0.1.0', 'ENGY'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'energy')
SEVERITY = {'FS-ENGY-LINT-001': 'warning', 'FS-ENGY-LINT-002': 'info', 'FS-ENGY-LINT-003': 'warning'}
GAP = 32512                                   # 1", 2.1
SETBACKS = {'eave': 585216, 'ridge': 1170432, 'rake': 1170432}     # 18", 3', 3' (4.1)


def arrays(ctx: Context) -> dict:
    return ctx.coll('pvArrays')


def sloped(roof) -> bool:
    return any(k == 'sloped' for k in roofs.kinds(roof))


def face_ok(roof, a) -> bool:
    """2.2.2."""
    face = a.get('face')
    if not sloped(roof):
        return face is None
    ks = roofs.kinds(roof)
    return face is not None and face < len(ks) and ks[face] == 'sloped'


def host_ok(ctx: Context, roof, a) -> bool:
    """2.3.1."""
    h = a.get('host')
    return h is not None and h['mode'] == 'free' and h['level'] == roof['level']


def outward_normal(roof, i):
    """2.3: the outward normal of footprint edge i, a vector of integers."""
    fp = roofs.footprint(roof)
    a, b = fp[i], fp[(i + 1) % len(fp)]
    dx, dy = b[0] - a[0], b[1] - a[1]
    return (dy, -dx) if plane.area2(fp) > 0 else (-dy, dx)


def face_pitch(roof, i):
    """The pitch of sloped edge i, as written (Core 16.1): its own, else the roof's."""
    return roofs.edge(roof, i).get('pitch', roof.get('pitch'))


def to_plan(length: int, pitch) -> int:
    """2.4: round(length x run / sqrt(rise^2 + run^2)), rounded once."""
    D = pitch['rise'] ** 2 + pitch['run'] ** 2
    return Surd.sqrt(D, Fraction(length * pitch['run'], D)).round()


def depth_breadth(a):
    m = a['module']
    portrait = a.get('layout', 'portrait') == 'portrait'
    return (m['length'], m['width']) if portrait else (m['width'], m['length'])


def extents(ctx: Context, a):
    """2.4: (D, B), the array's depth and breadth in plan."""
    roof = ctx.doc.roofs[a['roof']]
    depth, breadth = depth_breadth(a)
    rows, cols = a['rows'], a['columns']
    gap = a.get('gap', GAP)
    row_gap = a.get('rowGap', gap)
    B = cols * breadth + (cols - 1) * gap
    if 'face' in a:
        D = to_plan(rows * depth + (rows - 1) * row_gap, face_pitch(roof, a['face']))
    elif 'tilt' in a:
        D = rows * to_plan(depth, a['tilt']) + (rows - 1) * row_gap
    else:
        D = rows * depth + (rows - 1) * row_gap
    return D, B


def footprint(ctx: Context, a):
    """2.4: the footprint of the box from (-D, 0) to (0, B) in the array's frame."""
    D, B = extents(ctx, a)
    frame = frames.host_frame(ctx.doc, a['host'])
    ring, _, _ = frames.footprint(frame, {'min': [-D, 0, 0], 'max': [0, B, 1280]})
    return ring


def served(ctx: Context) -> dict:
    """Array ID -> the inverters that list it, sorted."""
    out = {}
    for iid, inv in sorted(ctx.coll('inverters').items()):
        for x in inv.get('arrays', []):
            if x in arrays(ctx):
                out.setdefault(x, []).append(iid)
    return out


# ------------------------------------------------------------------------------ the rules

def invariants(ctx: Context):
    ds = []
    for aid, a in sorted(arrays(ctx).items()):
        roof = ctx.doc.roofs.get(a['roof'])
        if roof is None:
            ds.append(ctx.diag('FS-ENGY-INV-001', [aid]))                                  # 2.2.1
            continue
        fok = face_ok(roof, a)
        if not fok:
            ds.append(ctx.diag('FS-ENGY-INV-002', [aid]))                                  # 2.2.2
        hok = host_ok(ctx, roof, a)
        if not hok:
            ds.append(ctx.diag('FS-ENGY-INV-003', [aid]))                                  # 2.3.1
        if fok and hok and 'face' in a:
            n = outward_normal(roof, a['face'])
            if a['host'].get('rotation', 0) != frames.direction(*n) or 'tilt' in a:
                ds.append(ctx.diag('FS-ENGY-INV-004', [aid]))                              # 2.3.2
    for kind in ('inverters', 'shutdowns'):
        for eid, el in sorted(ctx.coll(kind).items()):
            if any(x not in arrays(ctx) for x in el.get('arrays', [])):
                ds.append(ctx.diag('FS-ENGY-INV-005', [eid]))                              # 3.1.1, 3.2.1
    for aid, invs in sorted(served(ctx).items()):
        if len(invs) > 1:
            ds.append(ctx.diag('FS-ENGY-INV-006', [aid, *invs]))                           # 3.1.2
    return ds


def edge_kind(a3, b3, eave: int) -> str:
    """4.2."""
    if a3[2] == b3[2]:
        return 'eave' if a3[2] == eave else 'ridge'
    return 'rake'


def too_near(c, a, b, s: int) -> bool:
    """4.3: the distance from c to the segment ab is less than s - in integers."""
    ab = (b[0] - a[0], b[1] - a[1])
    ac = (c[0] - a[0], c[1] - a[1])
    L2 = plane.dot(ab, ab)
    t = plane.dot(ac, ab)
    if L2 == 0 or t <= 0:
        return plane.dot(ac, ac) < s * s
    if t >= L2:
        bc = (c[0] - b[0], c[1] - b[1])
        return plane.dot(bc, bc) < s * s
    cr = plane.cross(ab, ac)
    return cr * cr < s * s * L2


def clear(c, polys, eave: int, setbacks: dict) -> bool:
    for poly in polys:
        ring = [(p[0], p[1]) for p in poly]
        if plane.locate(c, ring) == 'out':
            continue
        n = len(poly)
        if all(not too_near(c, ring[i], ring[(i + 1) % n], setbacks[edge_kind(poly[i], poly[(i + 1) % n], eave)])
               for i in range(n)):
            return True
    return False


def lints(ctx: Context):
    ds = []
    derived = roofs.derive(ctx.doc, ctx.d.get('floorspec') == '0.4')['roofs']
    setbacks = {**SETBACKS, **ctx.data.get('setbacks', {})}
    srv = served(ctx)
    for aid, a in sorted(arrays(ctx).items()):
        r = derived[a['roof']]
        if r['surface'] is None:
            ds.append(ctx.diag('FS-ENGY-LINT-003', [aid]))                                 # 2.2.3
        else:
            faces = r['surface']['faces']
            polys = [f['polygon'] for f in faces if f.get('edge') == a['face']] if 'face' in a else [faces[0]['polygon']]
            if not all(clear(tuple(c), polys, r['eave'], setbacks) for c in footprint(ctx, a)):
                ds.append(ctx.diag('FS-ENGY-LINT-001', [aid]))                             # 4.3.1
        if aid not in srv:
            ds.append(ctx.diag('FS-ENGY-LINT-002', [aid]))                                 # 3.1.3
    return ds


def derive(ctx: Context) -> dict:
    srv = served(ctx)
    out = {'arrays': {}, 'inverters': {}, 'shutdowns': {}, 'modules': 0, 'watts': 0}
    for aid, a in sorted(arrays(ctx).items()):
        roof = ctx.doc.roofs[a['roof']]
        n = a['rows'] * a['columns']
        m = a['module']
        v = {'roof': a['roof']}
        if 'face' in a:
            v['face'] = a['face']
        v['mount'] = 'racked' if 'tilt' in a else 'flush'
        v['pitch'] = face_pitch(roof, a['face']) if 'face' in a else a.get('tilt')
        v.update(modules=n, watts=n * m['watts'], area=str(n * m['width'] * m['length']), footprint=footprint(ctx, a),
                 inverter=srv[aid][0] if aid in srv else None)
        out['arrays'][aid] = v
        out['modules'] += n
        out['watts'] += n * m['watts']
    for iid, inv in sorted(ctx.coll('inverters').items()):
        xs = sorted(inv.get('arrays', []))
        out['inverters'][iid] = {'arrays': xs, 'watts': sum(out['arrays'][x]['watts'] for x in xs)}
    for sid, s in sorted(ctx.coll('shutdowns').items()):
        out['shutdowns'][sid] = {'arrays': sorted(s.get('arrays', []))}
    return out

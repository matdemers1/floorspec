"""FS_outdoor 0.1.0 (registry/FS_outdoor/spec.md): its invariants, lints and derived values,
written from the extension's specification alone."""

from __future__ import annotations

from math import isqrt

from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_outdoor', '0.1.0', 'OUTD'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'outdoor')
SEVERITY = {'FS-OUTD-LINT-001': 'warning', 'FS-OUTD-LINT-002': 'info'}
KINDS = ('pools', 'fences', 'shelters', 'kitchens', 'fires')
BOXED = ('pools', 'shelters', 'kitchens', 'fires')          # 3.2.1: the kinds that always have a host
# the defaults of chapter 2
COPING, WATER_LINE, FENCE_SPACING = 384000, 192000, 3072000
POST_SIZE, POST_SPACING = 192000, 3072000


def elements(ctx: Context):
    """(kind, ID, element) of every element of FS_outdoor."""
    for kind in KINDS:
        for eid, el in ctx.coll(kind).items():
            yield kind, eid, el


def extents(el):
    """2.1: the box's extents X, Y and Z."""
    lo, hi = el['fallback']['box']['min'], el['fallback']['box']['max']
    return hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]


def _round_sqrt(n: int) -> int:
    """round(sqrt(n)) for an integer n >= 0: never a tie, since (k + 1/2)^2 is never an integer."""
    k = isqrt(n)
    return k + 1 if n - k * k > k else k


def segments(points):
    """6.3: each segment's length, rounded once."""
    return [_round_sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) for a, b in zip(points, points[1:])]


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def _round_div(a: int, b: int) -> int:
    """Core 2.2: a / b (b > 0) rounded once, to the nearest integer, ties to even."""
    q, r = divmod(a, b)
    if 2 * r > b or (2 * r == b and q % 2 == 1):
        return q + 1
    return q


def repeats(points) -> bool:
    return any(points[i] == points[i + 1] for i in range(len(points) - 1))


def gate_intervals(el):
    return sorted([g['offset'], g['offset'] + g['width']] for g in el.get('gates', []))


def invariants(ctx: Context):
    ds = []
    for kind, eid, el in elements(ctx):
        host = el.get('host')
        if host is not None and (host['mode'] == 'wallFace' or (host['mode'] == 'surface' and host['surface'] == 'ceiling')):
            ds.append(ctx.diag('FS-OUTD-INV-001', [eid]))                        # 3.2.2
        if kind in BOXED and host is None:
            ds.append(ctx.diag('FS-OUTD-INV-002', [eid]))                        # 3.2.1
        if kind == 'pools':
            x, y, z = extents(el)
            c = el.get('coping', COPING)
            if not (2 * c < x and 2 * c < y):
                ds.append(ctx.diag('FS-OUTD-INV-003', [eid]))                    # 2.2.1
            if not el.get('waterLine', WATER_LINE) < z:
                ds.append(ctx.diag('FS-OUTD-INV-004', [eid]))                    # 2.2.2
        elif kind == 'fences':
            pts = el['points']
            if repeats(pts):
                ds.append(ctx.diag('FS-OUTD-INV-005', [eid]))                    # 3.4.1
                continue                                                         # 5.2: no length, so no gates tested
            total = sum(segments(pts))
            gates = gate_intervals(el)
            if any(b > total for _, b in gates):
                ds.append(ctx.diag('FS-OUTD-INV-006', [eid]))                    # 2.3.1
            if any(gates[i + 1][0] < gates[i][1] for i in range(len(gates) - 1)):
                ds.append(ctx.diag('FS-OUTD-INV-007', [eid]))                    # 2.3.2
        elif kind == 'shelters':
            x, y, z = extents(el)
            size = el.get('postSize', POST_SIZE)
            if not (size < x and size < y):
                ds.append(ctx.diag('FS-OUTD-INV-008', [eid]))                    # 2.4.1
            if not el.get('postSpacing', POST_SPACING) > size:
                ds.append(ctx.diag('FS-OUTD-INV-009', [eid]))                    # 2.4.2
            if 'clearHeight' in el and not el['clearHeight'] < z:
                ds.append(ctx.diag('FS-OUTD-INV-010', [eid]))                    # 2.4.3
    return ds


def inside_box(el) -> bool:
    """3.3: a fence's line, grown by half its width, inside its box, horizontally and exactly."""
    (x0, y0, _), (x1, y1, _) = el['fallback']['box']['min'], el['fallback']['box']['max']
    h = el['width'] // 2
    return all(x0 <= p - h and p + h <= x1 and y0 <= q - h and q + h <= y1 for p, q in el['points'])


def lints(ctx: Context):
    ds = []
    rooms = ctx.rooms()
    for kind, eid, el in elements(ctx):
        if kind == 'fences':
            if not inside_box(el):
                ds.append(ctx.diag('FS-OUTD-LINT-001', [eid]))                   # 3.3
            continue
        rid = rooms.get(eid)
        if rid is not None and ctx.doc.rooms[rid].get('function', 'unspecified') != 'exterior':
            ds.append(ctx.diag('FS-OUTD-LINT-002', [eid, rid]))                  # 5.3: an outdoor room indoors
    return ds


def posts_of_fence(el) -> int:
    """6.3: one post per started spacing along each segment, plus one - less one when the line closes."""
    s = el.get('postSpacing', FENCE_SPACING)
    spaces = sum(_ceil_div(l, s) for l in segments(el['points']))
    return spaces if el['points'][0] == el['points'][-1] else spaces + 1


def shelter_layout(el):
    """6.4: (bays, spacing, posts) of a shelter."""
    x, y, _ = extents(el)
    size, s = el.get('postSize', POST_SIZE), el.get('postSpacing', POST_SPACING)
    lx, ly = x - size, y - size
    bx, by = _ceil_div(lx, s), _ceil_div(ly, s)
    posts = 2 * (bx + by) - ((by + 1) if el.get('attached', False) else 0)
    return [bx, by], [_round_div(lx, bx), _round_div(ly, by)], posts


def derive(ctx: Context) -> dict:
    rooms = ctx.rooms()

    def with_room(eid, d):
        if rooms.get(eid) is not None:
            d['room'] = rooms[eid]
        return d

    pools = {}
    for eid, el in sorted(ctx.coll('pools').items()):
        x, y, z = extents(el)
        c = el.get('coping', COPING)
        bx, by = x - 2 * c, y - 2 * c
        depth = z - el.get('waterLine', WATER_LINE)
        pools[eid] = with_room(eid, {'form': el['form'], 'basin': [bx, by], 'depth': depth,
                                     'area': str(bx * by), 'volume': str(bx * by * depth)})
    fences = {eid: {'form': el['form'], 'length': sum(segments(el['points'])), 'posts': posts_of_fence(el),
                    'gates': gate_intervals(el)}
              for eid, el in sorted(ctx.coll('fences').items())}
    shelters = {}
    for eid, el in sorted(ctx.coll('shelters').items()):
        bays, spacing, posts = shelter_layout(el)
        shelters[eid] = with_room(eid, {'top': el.get('top', 'slats'), 'bays': bays, 'spacing': spacing, 'posts': posts})
    kitchens = {eid: with_room(eid, {'run': extents(el)[1], 'appliances': list(el.get('appliances', []))})
                for eid, el in sorted(ctx.coll('kitchens').items())}
    fires = {eid: with_room(eid, {'form': el['form']}) for eid, el in sorted(ctx.coll('fires').items())}
    return {'pools': pools, 'fences': fences, 'shelters': shelters, 'kitchens': kitchens, 'fires': fires}

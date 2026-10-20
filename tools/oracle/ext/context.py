"""FS_context 0.1.0 (registry/FS_context/spec.md): its invariants, lints and derived values, written from
the extension's specification alone.

FS_context adds no kind of element and requires no other extension. Its records - streets, neighbours,
trees - are not elements, so nothing Core derives counts them (1.5): this module reads Core's site
boundary (the lot) and, of FS_site's, FS_lighting's, FS_views's and FS_annotation's data, only the IDs
of their records, as they are (1.3)."""

from __future__ import annotations

from math import isqrt

from .. import plane
from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_context', '0.1.0', 'CTXT'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'context')
SEVERITY = {'FS-CTXT-LINT-001': 'info'}
RECORDS = ('streets', 'neighbours', 'trees')
OTHERS = (('FS_lighting', 'scenes'), ('FS_views', 'views'), ('FS_annotation', 'dimensions'), ('FS_annotation', 'notes'),
          ('FS_site', 'spots'), ('FS_site', 'contours'), ('FS_site', 'pads'))
CURB = 195072                                  # 6", 2.1


def records(ctx: Context, member: str) -> dict:
    return ctx.data.get(member, {})


def read_as_data(ctx: Context) -> set:
    """1.3: the IDs of the other extensions' records, read as data."""
    out = set()
    for name, member in OTHERS:
        data = ctx.d.get('extensions', {}).get(name)
        s = data.get(member) if isinstance(data, dict) else None
        if isinstance(s, dict):
            out.update(s)
    return out


def lot(ctx: Context):
    """5.1: the site's boundary as tuples, or None."""
    b = ctx.d.get('site', {}).get('boundary')
    return None if b is None else [tuple(p) for p in b]


def round_sqrt(n: int) -> int:
    """round(sqrt(n)): never a tie, since (k + 1/2)^2 is never an integer."""
    return (isqrt(4 * n) + 1) // 2


def is_rectangle(ring) -> bool:
    """3.2: four vertices, each corner a right angle - the edges in and out of it have a dot product of 0."""
    if len(ring) != 4:
        return False
    for i in range(4):
        a, b, c = ring[i - 1], ring[i], ring[(i + 1) % 4]
        if (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]) != 0:
            return False
    return True


def points_of(member: str, r) -> list:
    """5.2: the points of a record that are tested against the lot."""
    if member == 'streets':
        return [tuple(p) for p in r['points']]
    if member == 'neighbours':
        return [tuple(p) for p in r['boundary']]
    return [tuple(r['at'])]


# ------------------------------------------------------------------------------ the rules

def invariants(ctx: Context):
    ds = []
    taken = ctx.space() | read_as_data(ctx)
    seen, bad = set(), set()
    for member in RECORDS:
        for rid in records(ctx, member):
            if rid in taken or rid in seen:
                bad.add(rid)
            seen.add(rid)
    ds.extend(ctx.diag('FS-CTXT-INV-001', [rid]) for rid in sorted(bad))                # 1.3.2
    for sid, s in records(ctx, 'streets').items():
        if any(s['points'][i] == s['points'][i + 1] for i in range(len(s['points']) - 1)):
            ds.append(ctx.diag('FS-CTXT-INV-002', [sid]))                                 # 2.1.1
    for nid, n in records(ctx, 'neighbours').items():
        ring = [tuple(p) for p in n['boundary']]
        if not plane.is_simple(ring) or plane.area2(ring) == 0:
            ds.append(ctx.diag('FS-CTXT-INV-003', [nid]))                                 # 3.1.1
        elif n.get('roof', 'flat') in ('gable', 'hip') and not is_rectangle(ring):
            ds.append(ctx.diag('FS-CTXT-INV-004', [nid]))                                 # 3.2.1
    return ds


def lints(ctx: Context):
    ds = []
    ring = lot(ctx)
    if ring is None:
        return ds
    for member in RECORDS:
        for rid, r in records(ctx, member).items():
            if any(plane.locate(p, ring) == 'in' for p in points_of(member, r)):
                ds.append(ctx.diag('FS-CTXT-LINT-001', [rid]))                            # 5.2.1
    return ds


def derive(ctx: Context) -> dict:
    out = {'streets': {}, 'neighbours': {}, 'trees': {}}
    for sid, s in sorted(records(ctx, 'streets').items()):
        pts = s['points']
        length = sum(round_sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) for a, b in zip(pts, pts[1:]))
        width = s['width'] + 2 * (s.get('curb', CURB) + s.get('strip', 0) + s.get('sidewalk', 0))
        out['streets'][sid] = {'length': length, 'width': width}
    for nid, n in sorted(records(ctx, 'neighbours').items()):
        ring = [tuple(p) for p in n['boundary']]
        eaves = n.get('elevation', 0) + n['height']
        out['neighbours'][nid] = {'roof': n.get('roof', 'flat'), 'area': plane.area_string(abs(plane.area2(ring))),
                                  'eaves': eaves, 'ridge': eaves + n.get('rise', 0)}
    for tid, t in sorted(records(ctx, 'trees').items()):
        out['trees'][tid] = {'form': t.get('form', 'deciduous'), 'top': t.get('elevation', 0) + t['height']}
    return out

"""FS_furniture 0.1.0 (registry/FS_furniture/spec.md): its invariants, lints and derived values,
written from the extension's specification alone."""

from __future__ import annotations

from .. import frames, plane
from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_furniture', '0.1.0', 'FURN'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'furniture')
SEVERITY = {'FS-FURN-LINT-001': 'warning', 'FS-FURN-LINT-002': 'warning', 'FS-FURN-LINT-003': 'info',
            'FS-FURN-LINT-004': 'warning', 'FS-FURN-LINT-005': 'warning'}
KINDS = ('pieces', 'appliances', 'casework')
WALL = ('shelf', 'wallCabinet', 'shelving')                  # 2.5: mounted on a wall
BUILT_IN = ('wallOven', 'cooktop', 'microwave')              # 2.5: set on or into casework
# 4.2: the purpose of each category's default envelopes
PURPOSE = {**{c: 'swing' for c in ('refrigerator', 'freezer', 'range', 'wallOven', 'dishwasher', 'washer', 'dryer',
                                   'dresser', 'sideboard', 'wardrobe', 'baseCabinet', 'tallCabinet', 'wallCabinet', 'vanity')},
           **{c: 'access' for c in ('sofa', 'armchair', 'desk', 'diningTable', 'bed')},
           'island': 'workingSpace'}


def mounting(category: str) -> str:
    return 'wall' if category in WALL else 'builtIn' if category in BUILT_IN else 'floor'


def elements(ctx: Context):
    """(kind, ID, element) of every element of FS_furniture."""
    for kind in KINDS:
        for eid, el in ctx.coll(kind).items():
            yield kind, eid, el


def invariants(ctx: Context):
    ds = []
    own = {eid: el for _, eid, el in elements(ctx)}
    for eid, el in ctx.coll('appliances').items():                              # 4.4.1
        for c in el.get('connections', []):
            x = ctx.ext.get(c)
            if x is None or x[0] == NAME:
                ds.append(ctx.diag('FS-FURN-INV-001', [eid]))
    for eid, el in own.items():
        if 'with' in el:                                                          # 4.3.1
            w = el['with']
            if w == eid or w not in own or 'with' in own[w]:
                ds.append(ctx.diag('FS-FURN-INV-002', [eid]))
        host = el.get('host')
        if host is not None and host['mode'] == 'surface' and host['surface'] == 'ceiling':   # 4.1.1
            ds.append(ctx.diag('FS-FURN-INV-003', [eid]))
    return ds


def grouped(own: dict, a, b) -> bool:
    """4.3: one is with the other, or both are with the same element."""
    wa, wb = own.get(a, {}).get('with'), own.get(b, {}).get('with')
    return wa == b or wb == a or (wa is not None and wa == wb)


def _footprints(ctx: Context):
    """4.5: every element's footprint, as Core derives its fallback: {ID: {footprint, bottom, top}}."""
    out = {}
    for _, eid, el in elements(ctx):
        ring, bottom, top = frames.footprint(frames.element_frame(ctx.doc, el), el['fallback']['box'])
        out[eid] = {'footprint': ring, 'bottom': bottom, 'top': top}
    return out


def _envelopes(ctx: Context):
    """Core 13.5: (owner, envelope footprint) of every clearance envelope, of openings and of every
    extension's elements."""
    doc = ctx.doc
    out = []
    for oid, o in sorted(doc.openings.items()):
        fill = o.get('fill')
        cl = doc.types[fill].get('clearances', {}) if fill is not None else {}
        if cl:
            frame = frames.opening_frame(doc, oid)
            for env in cl.values():
                ring, bottom, top = frames.footprint(frame, env)
                out.append((oid, {'footprint': ring, 'bottom': bottom, 'top': top}))
    for _, _, eid, el in doc.ext_elements:
        cl = el.get('clearances', {})
        if cl:
            frame = frames.element_frame(doc, el)
            for env in cl.values():
                ring, bottom, top = frames.footprint(frame, env)
                out.append((eid, {'footprint': ring, 'bottom': bottom, 'top': top}))
    return out


def lints(ctx: Context):
    ds = []
    own = {eid: el for _, eid, el in elements(ctx)}
    for eid, el in own.items():
        cat = el['category']
        if cat in PURPOSE and not ctx.has_purpose(el, PURPOSE[cat]):
            ds.append(ctx.diag('FS-FURN-LINT-001', [eid]))
        host = el.get('host')
        if host is not None and host['mode'] == 'wallFace' and el['fallback']['box']['min'][0] < 0:
            ds.append(ctx.diag('FS-FURN-LINT-002', [eid]))
        if mounting(cat) == 'wall' and (host is None or host['mode'] != 'wallFace'):
            ds.append(ctx.diag('FS-FURN-LINT-003', [eid]))
    prints = _footprints(ctx)
    for owner, env in _envelopes(ctx):
        for eid, fp in prints.items():
            if eid != owner and not grouped(own, owner, eid) and frames.envelopes_overlap(env, fp):
                ds.append(ctx.diag('FS-FURN-LINT-004', [owner, eid]))
    ids = sorted(prints)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if not grouped(own, a, b) and frames.envelopes_overlap(prints[a], prints[b]):
                ds.append(ctx.diag('FS-FURN-LINT-005', [a, b]))
    return ds


def derive(ctx: Context) -> dict:
    own = {eid: (kind, el) for kind, eid, el in elements(ctx)}
    rooms = ctx.rooms()
    prints = _footprints(ctx)
    items, by_room, area2, groups = {}, {}, {}, {}
    for eid in sorted(own):
        kind, el = own[eid]
        (x0, y0, z0), (x1, y1, z1) = el['fallback']['box']['min'], el['fallback']['box']['max']
        item = {'kind': kind, 'category': el['category'], 'width': y1 - y0, 'depth': x1 - x0, 'height': z1 - z0}
        rid = rooms.get(eid)
        if rid is not None:
            item['room'] = rid
            by_room.setdefault(rid, []).append(eid)
            if mounting(el['category']) == 'floor':
                area2[rid] = area2.get(rid, 0) + plane.area2(prints[eid]['footprint'])
        items[eid] = item
        if 'with' in el:
            groups.setdefault(el['with'], []).append(eid)
    return {'items': items,
            'rooms': {r: {'items': sorted(v), 'floorArea': plane.area_string(area2.get(r, 0))} for r, v in sorted(by_room.items())},
            'groups': {g: sorted(v) for g, v in sorted(groups.items())}}

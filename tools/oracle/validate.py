"""Validation in tiers, with the order of evaluation of 10.3, and the lints.

``run(data: bytes)`` returns the expected result of the conformance suite for a document:
``{valid, diagnostics, hash?, derived?}`` plus the canonical bytes when the document is valid.
"""

from __future__ import annotations

from fractions import Fraction

from . import canon, plane, schema
from .derive import Doc, LevelGraph, degenerate, opening_points, rpoint, strictly_inside
from .derive import derive as derive_all
from .jsonparse import Malformed, parse
from .surd import Surd

IMPLEMENTED_VERSIONS = {'0.1'}
IMPLEMENTED_EXTENSIONS: set[str] = set()   # a core-only reader

SEVERITY = {
    'FS-LINT-001': 'warning', 'FS-LINT-002': 'warning', 'FS-LINT-003': 'info', 'FS-LINT-004': 'warning',
    'FS-LINT-005': 'warning', 'FS-LINT-006': 'info', 'FS-LINT-007': 'warning',
}


def diag(code, elements=()):
    """One diagnostic per instance of a catalogued condition (10.2)."""
    return {'code': code, 'severity': SEVERITY.get(code, 'error'), 'elements': sorted(set(elements))}


def sort_diags(ds):
    return sorted(ds, key=lambda d: (d['code'], d['elements']))


# ------------------------------------------------------------------------------ reference tier

REF_TABLE = [
    # (collection, member path, target collection, allowed type kinds)
    ('levels', ('building',), 'buildings', None),
    ('junctions', ('level',), 'levels', None),
    ('walls', ('level',), 'levels', None),
    ('separators', ('level',), 'levels', None),
    ('rooms', ('level',), 'levels', None),
    ('slabs', ('level',), 'levels', None),
    ('walls', ('start',), 'junctions', None),
    ('walls', ('end',), 'junctions', None),
    ('separators', ('start',), 'junctions', None),
    ('separators', ('end',), 'junctions', None),
    ('walls', ('type',), 'types', {'wallType'}),
    ('walls', ('base', 'level'), 'levels', None),
    ('walls', ('top', 'level'), 'levels', None),
    ('openings', ('wall',), 'walls', None),
    ('openings', ('fill',), 'types', {'doorType', 'windowType'}),
    ('rooms', ('wallFinish',), 'materials', None),
    ('rooms', ('floorFinish',), 'materials', None),
    ('rooms', ('ceilingFinish',), 'materials', None),
    ('slabs', ('material',), 'materials', None),
    ('materials', ('texture', 'asset'), 'assets', None),
]


def _get(e, path):
    for k in path:
        if not isinstance(e, dict) or k not in e:
            return None
        e = e[k]
    return e


def references(d: dict):
    """(collection, element id, target id, target collection, kinds) for every reference."""
    out = []
    for coll, path, target, kinds in REF_TABLE:
        for eid, e in d.get(coll, {}).items():
            v = _get(e, path)
            if v is not None:
                out.append((coll, eid, v, target, kinds))
    for jid, j in d.get('junctions', {}).items():
        for w in j.get('join', {}).get('through', []):
            out.append(('junctions', jid, w, 'walls', None))
    for coll in ('types', 'walls'):
        for eid, e in d.get(coll, {}).items():
            for layer in e.get('layers', []):
                if 'material' in layer:
                    out.append((coll, eid, layer['material'], 'materials', None))
    return out


def polygon_ok(poly) -> bool:
    ring = [tuple(p) for p in poly]
    return plane.is_simple(ring) and plane.area2(ring) != 0


def reference_tier(d: dict):
    ds = []
    owners: dict[str, list[str]] = {}
    for c in canon.COLLECTIONS:
        for eid in d.get(c, {}):
            owners.setdefault(eid, []).append(c)
    for eid, cs in owners.items():
        if len(cs) > 1:
            ds.append(diag('FS-INV-001', [eid]))
    for coll, eid, target_id, target, kinds in references(d):
        t = d.get(target, {})
        if target_id not in t:
            ds.append(diag('FS-INV-002', [eid]))
        elif kinds is not None and t[target_id].get('kind') not in kinds:
            ds.append(diag('FS-INV-003', [eid]))
    used = d.get('extensionsUsed', {})
    for n in d.get('extensionsRequired', []):
        if n not in used:
            ds.append(diag('FS-INV-004'))
    for n in d.get('extensions', {}):
        if n not in used:
            ds.append(diag('FS-INV-005'))
    for c in canon.COLLECTIONS:
        for eid, e in d.get(c, {}).items():
            if any(n not in used for n in e.get('extensions', {})):
                ds.append(diag('FS-INV-005', [eid]))
    for rid, r in d.get('rooms', {}).items():
        f = r.get('function', 'unspecified')
        if ':' in f and f.split(':', 1)[0] not in used:
            ds.append(diag('FS-INV-006', [rid]))
    levels, junctions = d.get('levels', {}), d.get('junctions', {})
    for coll in ('walls', 'separators'):
        for eid, e in d.get(coll, {}).items():
            for end in ('start', 'end'):
                j = junctions.get(e[end])
                if j is not None and j['level'] != e['level']:
                    ds.append(diag('FS-INV-007', [eid, e[end]]))
    for wid, w in d.get('walls', {}).items():
        own = levels.get(w['level'])
        for lid in (_get(w, ('base', 'level')), _get(w, ('top', 'level'))):
            if lid is None or own is None or lid not in levels:
                continue
            if levels[lid]['building'] != own['building']:
                ds.append(diag('FS-INV-008', [wid, lid]))
    for sid, s in d.get('slabs', {}).items():
        if not polygon_ok(s['boundary']):
            ds.append(diag('FS-INV-009', [sid]))
    site = d.get('site')
    if isinstance(site, dict) and 'boundary' in site and not polygon_ok(site['boundary']):
        ds.append(diag('FS-INV-009'))
    return ds


# ------------------------------------------------------------------------------ graph tier

def graph_tier(doc: Doc):
    """Graph invariants for every level and wall. Returns (diagnostics, bad levels, walls with 112)."""
    ds, bad_levels, no_top = [], set(), set()
    for level in doc.levels:
        js = {j: tuple(v['position']) for j, v in doc.junctions.items() if v['level'] == level}
        edges = {}
        for coll in ('walls', 'separators'):
            for eid, e in getattr(doc, coll).items():
                if e['level'] == level:
                    edges[eid] = (e['start'], e['end'])
        found = []
        jl = sorted(js)
        for i, a in enumerate(jl):
            for b in jl[i + 1:]:
                if js[a] == js[b]:
                    found.append(diag('FS-INV-101', [a, b]))
        for eid, (s, e) in edges.items():
            if s == e:
                found.append(diag('FS-INV-102', [eid]))
        el = sorted(edges)
        for i, x in enumerate(el):
            for y in el[i + 1:]:
                sx, ex = edges[x]
                sy, ey = edges[y]
                if {sx, ex} == {sy, ey}:
                    found.append(diag('FS-INV-103', [x, y]))
                    continue
                p1, p2, q1, q2 = js[sx], js[ex], js[sy], js[ey]
                if p1 == p2 or q1 == q2:
                    continue
                if plane.proper_cross(p1, p2, q1, q2):
                    found.append(diag('FS-INV-104', [x, y]))
                elif plane.collinear_overlap(p1, p2, q1, q2):
                    found.append(diag('FS-INV-106', [x, y]))
        for j in jl:
            for eid, (s, e) in edges.items():
                if plane.in_open_segment(js[j], js[s], js[e]):
                    found.append(diag('FS-INV-105', [j, eid]))
        for wid, w in doc.walls.items():
            if w['level'] != level:
                continue
            if doc.effective_layers(wid) is None:
                found.append(diag('FS-INV-107', [wid]))
            elif w.get('justification') == 'coreFace' and not doc.core_ok(wid):
                found.append(diag('FS-INV-108', [wid]))
        no_faces = {d['elements'][0] for d in found if d['code'] in ('FS-INV-107', 'FS-INV-108')}
        found.extend(join_applicability(doc, level, js, edges, no_faces))
        for wid, w in doc.walls.items():
            if w['level'] == level and doc.top_elevation(wid) <= doc.base_elevation(wid):
                ds.append(diag('FS-INV-112', [wid]))
                no_top.add(wid)
        if found:
            bad_levels.add(level)
        ds.extend(found)
    return ds, bad_levels, no_top


def join_applicability(doc: Doc, level, js, edges, no_faces):
    """FS-INV-111: 5.8.1-5.8.3. Not evaluated for a junction with a wall that has FS-INV-107 or
    FS-INV-108 (10.3): such a wall has no face lines to compare."""
    ds = []
    for jid, j in doc.junctions.items():
        if j['level'] != level or j.get('join', {}).get('kind') != 'butt':
            continue
        through = j['join']['through']
        incident = [e for e, (s, t) in edges.items() if jid in (s, t)]
        if any(e in no_faces for e in incident):
            continue

        def out(eid):
            s, t = edges[eid]
            o = t if s == jid else s
            return (js[o][0] - js[jid][0], js[o][1] - js[jid][1])
        ok = all(w in incident and w in doc.walls for w in through)
        if ok and len(through) == 1:
            ok = len(incident) == 2 and plane.cross(out(incident[0]), out(incident[1])) != 0
        elif ok and len(through) == 2:
            w1, w2 = through
            d1, d2 = out(w1), out(w2)
            ok = w1 != w2 and plane.cross(d1, d2) == 0 and plane.dot(d1, d2) < 0
            if ok:
                o1, o2 = doc.offsets(w1), doc.offsets(w2)
                if o1 is not None and o2 is not None:
                    lam1, rho1 = o1 if edges[w1][0] == jid else o1[::-1]
                    lam2, rho2 = o2 if edges[w2][0] == jid else o2[::-1]
                    ok = lam1 == rho2 and rho1 == lam2
            if ok:
                others = [e for e in incident if e not in through]
                left = sum(1 for e in others if plane.cross(d1, out(e)) > 0)
                right = sum(1 for e in others if plane.cross(d1, out(e)) < 0)
                ok = left <= 1 and right <= 1
        if not ok:
            ds.append(diag('FS-INV-111', [jid]))
    return ds


def join_and_room_tier(doc: Doc, level):
    ds = []
    g = LevelGraph(doc, level)
    for wid, e in g.edges.items():
        if e.kind == 'wall':
            ring = g.outline(wid)
            if not plane.is_simple(ring) or plane.area2(ring) <= 0:
                ds.append(diag('FS-INV-109', [wid]))
    for j in g.pos:
        ring = g.fill(j)
        if ring is None or len(ring) < 3 or plane.area2(ring) == 0:
            continue
        if not plane.is_simple(ring) or plane.area2(ring) < 0:
            ds.append(diag('FS-INV-110', [j]))
    faces = g.faces()
    by_face: dict[int, list[str]] = {}
    face_obj = {}
    for rid, r in doc.rooms.items():
        if r['level'] != level:
            continue
        p = tuple(r['anchor'])
        f = None if g.on_location_line(p) else g.face_of(p, faces)
        if f is None:
            ds.append(diag('FS-INV-201', [rid]))
            continue
        by_face.setdefault(id(f), []).append(rid)
        face_obj[id(f)] = f
    for fid, rids in by_face.items():
        if len(rids) > 1:
            ds.append(diag('FS-INV-202', rids))
            continue
        rid = rids[0]
        outer, holes = g.room_polygon(face_obj[fid])
        if degenerate(outer, holes):
            ds.append(diag('FS-INV-203', [rid]))
        elif not strictly_inside(tuple(doc.rooms[rid]['anchor']), outer, holes):
            ds.append(diag('FS-INV-204', [rid]))
    return ds


def wall_length_ok(doc: Doc, wid, reach) -> bool:
    w = doc.walls[wid]
    s, e = doc.junctions[w['start']]['position'], doc.junctions[w['end']]['position']
    return reach * reach <= (e[0] - s[0]) ** 2 + (e[1] - s[1]) ** 2


def opening_tier(doc: Doc, no_top):
    ds = []
    ok = {}
    for oid, o in doc.openings.items():
        width, height, sill = doc.opening_dims(oid)
        if width is None or height is None:
            ds.append(diag('FS-INV-301', [oid]))
            continue
        ok[oid] = (o['offset'], o['offset'] + width, sill, sill + height)
        if not wall_length_ok(doc, o['wall'], o['offset'] + width):
            ds.append(diag('FS-INV-302', [oid]))
        wid = o['wall']
        if wid not in no_top and sill + height > doc.top_elevation(wid) - doc.base_elevation(wid):
            ds.append(diag('FS-INV-303', [oid]))
    ids = sorted(ok)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if doc.openings[a]['wall'] != doc.openings[b]['wall']:
                continue
            a0, a1, av0, av1 = ok[a]
            b0, b1, bv0, bv1 = ok[b]
            if max(a0, b0) < min(a1, b1) and max(av0, bv0) < min(av1, bv1):
                ds.append(diag('FS-INV-304', [a, b]))
    return ds


# ------------------------------------------------------------------------------ lints

def lints(doc: Doc):
    ds = []
    for level in doc.levels:
        g = LevelGraph(doc, level)
        for j, es in g.inc.items():
            if not es:
                ds.append(diag('FS-LINT-002', [j]))
            k = len(es)
            if k < 2:
                continue
            for i in range(k):
                e1, e2 = es[i], es[(i + 1) % k]
                if g.edges[e1].kind != 'wall' or g.edges[e2].kind != 'wall':
                    continue
                d1, d2 = g.out(j, e1), g.out(j, e2)
                if plane.cross(d1, d2) <= 0:
                    continue
                dt = plane.dot(d1, d2)
                if dt > 0 and 4 * dt * dt > 3 * plane.dot(d1, d1) * plane.dot(d2, d2):
                    ds.append(diag('FS-LINT-001', [j, e1, e2]))
        faces = g.faces()
        anchored = set()
        for r in doc.rooms.values():
            if r['level'] == level:
                anchored.add(id(g.face_of(tuple(r['anchor']), faces)))
        for f in faces:
            if id(f) in anchored:
                continue
            ds.append(diag('FS-LINT-003'))
            outer, holes = g.room_polygon(f)
            if degenerate(outer, holes):
                ds.append(diag('FS-LINT-004'))
    for oid, o in doc.openings.items():
        if opening_in_join(doc, oid):
            ds.append(diag('FS-LINT-005', [oid]))
    referred = set()
    for _, _, target_id, target, _ in references(doc.d):
        if target in ('types', 'materials', 'assets'):
            referred.add(target_id)
    for c in ('types', 'materials', 'assets'):
        for eid in getattr(doc, c):
            if eid not in referred:
                ds.append(diag('FS-LINT-006', [eid]))
    for aid, a in doc.assets.items():
        if 'uri' in a:
            ds.append(diag('FS-LINT-007', [aid]))
    return ds


def opening_in_join(doc: Doc, oid) -> bool:
    """7.5, measured along the location line from the rounded face ends."""
    o = doc.openings[oid]
    wid = o['wall']
    w = doc.walls[wid]
    g = LevelGraph(doc, w['level'])
    f = {k: rpoint(v) for k, v in g.face_ends(wid).items()}
    S, E = tuple(doc.junctions[w['start']]['position']), tuple(doc.junctions[w['end']]['position'])
    d = (E[0] - S[0], E[1] - S[1])
    D = plane.dot(d, d)
    width, _, _ = doc.opening_dims(oid)
    lo, hi = o['offset'], o['offset'] + width
    # distance from S of point P along the line: (P - S).d / |d|
    for k in ('startLeft', 'startRight'):
        proj = plane.dot(plane.sub(f[k], S), d)
        if (Surd(proj) - Surd.sqrt(D, lo)).sign() > 0:          # lo < proj/|d|
            return True
    for k in ('endLeft', 'endRight'):
        q = plane.dot(plane.sub(E, f[k]), d)                    # distance from E, times |d|
        # (|d| - hi) < q/|d|  <=>  D - hi*sqrt(D) < q
        if (Surd(q - D) + Surd.sqrt(D, hi)).sign() > 0:
            return True
    return False


# ------------------------------------------------------------------------------ the pipeline

def check(data: bytes):
    """Returns (result, canonical bytes or None, notes)."""
    notes = []
    try:
        value, codes = parse(data)
    except Malformed as e:
        notes.append(str(e))
        return {'valid': False, 'diagnostics': [diag('FS-JSON-001')]}, None, notes
    if codes:
        return {'valid': False, 'diagnostics': sort_diags(diag(c) for c in codes)}, None, notes
    # tier 2: document
    ds = []
    if isinstance(value, dict):
        v = value.get('floorspec')
        if isinstance(v, str) and v not in IMPLEMENTED_VERSIONS:
            ds.append(diag('FS-DOC-001'))
        # FS-DOC-002 only for a well-formed extensionsRequired: an array of distinct names, each
        # in extensionsUsed. Anything else is left to the schema tier and FS-INV-004 (10.4).
        req, used = value.get('extensionsRequired'), value.get('extensionsUsed', {})
        if (isinstance(req, list) and all(isinstance(n, str) for n in req) and len(set(req)) == len(req)
                and isinstance(used, dict) and all(n in used for n in req)):
            for n in req:
                if n not in IMPLEMENTED_EXTENSIONS:
                    ds.append(diag('FS-DOC-002'))
    if ds:
        return {'valid': False, 'diagnostics': sort_diags(ds)}, None, notes
    # tier 3: schema
    problems = schema.check(value)
    if problems:
        notes.extend(problems)
        return {'valid': False, 'diagnostics': [diag('FS-SCH-001')]}, None, notes
    # tier 4: invariants
    ds = reference_tier(value)
    if not ds:
        doc = Doc(value)
        gds, bad_levels, no_top = graph_tier(doc)
        ds.extend(gds)
        for level in sorted(doc.levels):
            if level not in bad_levels:
                ds.extend(join_and_room_tier(doc, level))
        ds.extend(opening_tier(doc, no_top))
    if any(x['severity'] == 'error' for x in ds):
        return {'valid': False, 'diagnostics': sort_diags(ds)}, None, notes
    doc = Doc(value)
    ds.extend(lints(doc))
    result = {'valid': True, 'diagnostics': sort_diags(ds), 'hash': canon.content_hash(value),
              'derived': derive_all(doc)}
    return result, canon.canonical_bytes(value), notes

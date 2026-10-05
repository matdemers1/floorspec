"""Validation in tiers, with the order of evaluation of 10.3, and the lints.

``check(data: bytes, reader, registry)`` returns the expected result of the conformance suite for a
document - ``{valid, diagnostics, hash?, derived?}`` - plus the canonical bytes when the document
is valid. ``reader`` is the draft the oracle reads as: READER_01 (Core 0.1 alone, the default, as
the 0.1 suite and the Ops 0.1 oracle use it), READER_02 (Core 0.2, which also reads 0.1 documents,
1.2.4 of 0.2) or READER_03 (Core 0.3, which also reads 0.1 and 0.2 documents, 1.2.6).
``registry`` is the known extensions (12.2), as the bytes of a JSON array of registry entries, or
None for none.
"""

from __future__ import annotations

from fractions import Fraction

from . import canon, frames, plane, registry as reg, schema
from .derive import Doc, LevelGraph, degenerate, ext_elements, opening_points, rpoint, strictly_inside
from .derive import derive as derive_all
from .jsonparse import Malformed, parse
from .circulation import circulation_lints, derive_circulation
from . import floors, stairs
from .program import derive_program, program_invariants, program_lints
from .surd import Surd


class Reader:
    def __init__(self, versions):
        self.versions = frozenset(versions)
        self.v02 = '0.2' in self.versions           # what 0.2 adds: program, extensions, hosting, circulation
        self.v03 = '0.3' in self.versions           # what 0.3 adds: operation, clear openings, floors, ceilings, slabs
        self.newest = max(self.versions)


READER_01 = Reader({'0.1'})
READER_02 = Reader({'0.1', '0.2'})
READER_03 = Reader({'0.1', '0.2', '0.3'})
READERS = {'0.1': READER_01, '0.2': READER_02, '0.3': READER_03}
IMPLEMENTED_VERSIONS = READER_01.versions


def ext_reader(data: bytes) -> Reader:
    """The Core reader an extension suite's test is read by (conformance/README.md): of the Core draft
    the document declares - Core 0.3 for a document declaring "0.3", Core 0.2 for every other."""
    import json
    try:
        value = json.loads(data)
    except ValueError:
        return READER_02
    return READER_03 if isinstance(value, dict) and value.get('floorspec') == '0.3' else READER_02
IMPLEMENTED_EXTENSIONS: set[str] = set()   # a core-only reader

SEVERITY = {
    'FS-LINT-001': 'warning', 'FS-LINT-002': 'warning', 'FS-LINT-003': 'info', 'FS-LINT-004': 'warning',
    'FS-LINT-005': 'warning', 'FS-LINT-006': 'info', 'FS-LINT-007': 'warning',
    'FS-LINT-008': 'warning', 'FS-LINT-009': 'warning', 'FS-LINT-010': 'warning', 'FS-LINT-011': 'warning',
    'FS-LINT-012': 'warning', 'FS-LINT-013': 'warning', 'FS-LINT-014': 'warning',
    'FS-LINT-901': 'info',                                                      # Core 0.3, 17.7
}
GLTF = {'model/gltf-binary', 'model/gltf+json'}
SYMBOL = {'image/svg+xml', 'image/png'}


def diag(code, elements=()):
    """One diagnostic per instance of a catalogued condition (10.2)."""
    return {'code': code, 'severity': SEVERITY.get(code, 'error'),
            'elements': sorted(set(e for e in elements if e is not None))}


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
    ('stairs', ('level',), 'levels', None),                     # Core 0.3, 17.1
    ('stairs', ('to',), 'levels', None),
]


def _get(e, path):
    for k in path:
        if not isinstance(e, dict) or k not in e:
            return None
        e = e[k]
    return e


def coll_of(d: dict, name: str) -> dict:
    """A collection by name; `items` is the program's items (Core 0.2, 3.2)."""
    if name == 'items':
        return d.get('program', {}).get('items', {})
    return d.get(name, {})


def references(d: dict):
    """(collection, element id, target id, target collection, kinds) for every reference. The
    referring element of an adjacency is None (10.4: FS-INV-002 names no element for it)."""
    out = []
    for coll, path, target, kinds in REF_TABLE:
        for eid, e in d.get(coll, {}).items():
            v = _get(e, path)
            if v is not None:
                out.append((coll, eid, v, target, kinds))
    # Core 0.2: the program, room briefs, hosts and fallbacks (3.2)
    for rid, r in d.get('rooms', {}).items():
        if 'brief' in r:
            out.append(('rooms', rid, r['brief'], 'items', None))
    program = d.get('program', {})
    for iid, it in program.get('items', {}).items():
        if 'level' in it:
            out.append(('items', iid, it['level'], 'levels', None))
    for a in program.get('adjacency', []):
        out.append(('adjacency', None, a['a'], 'items', None))
        out.append(('adjacency', None, a['b'], 'items', None))
    for _, _, eid, el in ext_elements(d):
        host = el.get('host')
        if host is not None:
            for member, target in (('wall', 'walls'), ('room', 'rooms'), ('level', 'levels')):
                if member in host:
                    out.append(('ext', eid, host[member], target, None))
        fb = el['fallback']
        out.append(('ext', eid, fb['level'], 'levels', None))
        for member in ('asset', 'symbol'):
            if member in fb:
                out.append(('ext', eid, fb[member], 'assets', None))
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
    owners: dict[str, list] = {}
    for c in canon.COLLECTIONS:
        for eid in d.get(c, {}):
            owners.setdefault(eid, []).append(c)
    for iid in coll_of(d, 'items'):                              # 3.1.3
        owners.setdefault(iid, []).append('items')
    for ext, cname, eid, _ in ext_elements(d):
        owners.setdefault(eid, []).append((ext, cname))
    for eid, cs in owners.items():
        if len(cs) > 1:
            ds.append(diag('FS-INV-001', [eid]))
    for coll, eid, target_id, target, kinds in references(d):
        t = coll_of(d, target)
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
    for c in canon.COLLECTIONS + ('items',):
        for eid, e in coll_of(d, c).items():
            if any(n not in used for n in e.get('extensions', {})):
                ds.append(diag('FS-INV-005', [eid]))
    for c in ('rooms', 'items'):
        for rid, r in coll_of(d, c).items():
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
    """Join and room invariants of one level. Rooms that get FS-INV-201..204 are named in the
    diagnostics, which is how the hosting tier knows to skip FS-INV-503 for them (10.3)."""
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
        clear = doc.clear_opening(oid)                                      # 7.2.2 (0.3)
        if clear is not None and (clear['width'] > width or clear['height'] > height):
            ds.append(diag('FS-INV-305', [oid]))
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


def clear_opening_tier(doc: Doc):
    """FS-INV-306, 307 and 308 (Core 0.3: 7.1.3, 8.4.4, 8.4.5), for every door or window type and
    every opening. Only a 0.3 document can have a clear opening: the earlier schemas reject one."""
    ds = []

    def too_much_area(c):
        return 'area' in c and c['area'] > c['width'] * c['height']

    for tid, t in doc.types.items():
        c = t.get('clearOpening')
        if t.get('kind') not in ('doorType', 'windowType') or c is None:
            continue
        if too_much_area(c):
            ds.append(diag('FS-INV-306', [tid]))
        if ('width' in t and c['width'] > t['width']) or ('height' in t and c['height'] > t['height']):
            ds.append(diag('FS-INV-307', [tid]))
    for oid, o in doc.openings.items():
        c = o.get('clearOpening')
        if c is None:
            continue
        if too_much_area(c):
            ds.append(diag('FS-INV-306', [oid]))
        fill = doc.types.get(o['fill']) if 'fill' in o else None
        if 'area' in c and (fill is None or fill.get('kind') != 'windowType'):
            ds.append(diag('FS-INV-308', [oid]))
    return ds


# ------------------------------------------------------------------------------ Core 0.2 tiers

def _version(decl):
    return decl['version'] if isinstance(decl, dict) else decl


def extension_tier(d: dict, known):
    """FS-INV-601..605 (12.3, 12.4), for every extension used at a version at which it is known."""
    ds = []
    used = d.get('extensionsUsed', {})
    elements = ext_elements(d)
    for x, decl in used.items():
        entry = reg.entry_for(known, x, _version(decl))
        if entry is None:
            continue
        for y, rng in entry.get('requires', {}).items():
            if y not in used:
                ds.append(diag('FS-INV-601'))
            elif not reg.satisfies(_version(used[y]), rng):
                ds.append(diag('FS-INV-602'))
        kinds = entry.get('kinds', {})
        data = d.get('extensions', {}).get(x)
        if d.get('floorspec') in ('0.2', '0.3') and isinstance(data, dict) and isinstance(data.get('collections'), dict):
            for cname in data['collections']:
                if cname not in kinds:
                    ds.append(diag('FS-INV-604'))
        for ext, cname, eid, el in elements:
            if ext != x or cname not in kinds:
                continue
            need = kinds[cname].get('fallback', {})
            for part in ('asset', 'symbol'):
                if need.get(part) and part not in el['fallback']:
                    ds.append(diag('FS-INV-603', [eid]))
        terms = set(entry.get('terms', {}).get('roomFunctions', []))
        for c in ('rooms', 'items'):
            for rid, r in coll_of(d, c).items():
                f = r.get('function', 'unspecified')
                if ':' in f and f.split(':', 1)[0] == x and f.split(':', 1)[1] not in terms:
                    ds.append(diag('FS-INV-605', [rid]))
    return ds


def host_level(doc: Doc, host):
    if host['mode'] == 'wallFace':
        return doc.walls[host['wall']]['level']
    if host['mode'] == 'surface':
        return doc.rooms[host['room']]['level']
    return host['level']


def hosting_tier(doc: Doc, no_top):
    """FS-INV-501, 502, 504, 505 and 506 (12.6, 13.2, 13.3). FS-INV-503 is surface_tier's."""
    ds = []
    for tid, t in doc.types.items():
        for env in t.get('clearances', {}).values():
            if not frames.extents_ok(env):
                ds.append(diag('FS-INV-505', [tid]))
    for _, _, eid, el in doc.ext_elements:
        fb = el['fallback']
        if not frames.extents_ok(fb['box']):
            ds.append(diag('FS-INV-505', [eid]))
        for env in el.get('clearances', {}).values():
            if not frames.extents_ok(env):
                ds.append(diag('FS-INV-505', [eid]))
        if 'asset' in fb and doc.assets[fb['asset']]['mediaType'] not in GLTF:
            ds.append(diag('FS-INV-506', [eid]))
        if 'symbol' in fb and doc.assets[fb['symbol']]['mediaType'] not in SYMBOL:
            ds.append(diag('FS-INV-506', [eid]))
        host = el.get('host')
        if host is None:
            continue
        if host_level(doc, host) != fb['level']:
            ds.append(diag('FS-INV-504', [eid]))
        if host['mode'] == 'wallFace':
            wid = host['wall']
            if not wall_length_ok(doc, wid, host['offset']):
                ds.append(diag('FS-INV-501', [eid]))
            if wid not in no_top and host['height'] > doc.top_elevation(wid) - doc.base_elevation(wid):
                ds.append(diag('FS-INV-502', [eid]))
    return ds


def surface_tier(doc: Doc, bad_levels, bad_rooms):
    """FS-INV-503 (13.3.4): evaluated only where room invariants were evaluated and passed (10.3)."""
    ds = []
    graphs = {}
    for _, _, eid, el in doc.ext_elements:
        host = el.get('host')
        if host is None or host['mode'] != 'surface':
            continue
        rid = host['room']
        level = doc.rooms[rid]['level']
        if level in bad_levels or rid in bad_rooms:
            continue
        if level not in graphs:
            g = LevelGraph(doc, level)
            graphs[level] = (g, g.faces())
        g, faces = graphs[level]
        outer, holes = g.room_polygon(g.face_of(tuple(doc.rooms[rid]['anchor']), faces))
        if not strictly_inside(tuple(host['position']), outer, holes):
            ds.append(diag('FS-INV-503', [eid]))
    return ds


def derive_02(doc: Doc) -> dict:
    """The members Core 0.2 adds to the derived values: program, fallbacks, placements,
    clearances, clearanceOverlaps and circulation (11.3, 11.4, 12.6, 13.4, 13.5, 13.6, 14.3)."""
    program, _, _ = derive_program(doc)
    fallbacks, placements, clearances, envelopes = {}, {}, {}, []

    def envelope(owner, level, frame, name, env):
        ring, bottom, top = frames.footprint(frame, env)
        v = {'purpose': env['purpose'], 'level': level, 'footprint': ring, 'bottom': bottom, 'top': top}
        clearances.setdefault(owner, {})[name] = v
        envelopes.append(((owner, name), v))

    for oid, o in doc.openings.items():
        fill = o.get('fill')
        cl = doc.types[fill].get('clearances', {}) if fill is not None else {}
        if cl:
            frame = frames.opening_frame(doc, oid)
            level = doc.walls[o['wall']]['level']
            for name, env in cl.items():
                envelope(oid, level, frame, name, env)
    for ext, cname, eid, el in doc.ext_elements:
        frame = frames.element_frame(doc, el)
        fb = el['fallback']
        ring, bottom, top = frames.footprint(frame, fb['box'])
        fallbacks[eid] = {'extension': ext, 'collection': cname, 'level': fb['level'],
                          'footprint': ring, 'bottom': bottom, 'top': top}
        if 'host' in el:
            placements[eid] = frame.placement()
            if el['host']['mode'] != 'wallFace':
                assert placements[eid]['facing'] == el['host'].get('rotation', 0)
        for name, env in el.get('clearances', {}).items():
            envelope(eid, fb['level'], frame, name, env)
    overlaps = []
    for i, (ka, a) in enumerate(envelopes):
        for kb, b in envelopes[i + 1:]:
            if ka[0] != kb[0] and frames.envelopes_overlap(a, b):
                overlaps.append(sorted([list(ka), list(kb)]))
    overlaps.sort()
    return {'program': program, 'fallbacks': fallbacks, 'placements': placements,
            'clearances': clearances, 'clearanceOverlaps': overlaps,
            'circulation': derive_circulation(doc)[0]}


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

def check(data: bytes, reader: Reader = READER_01, registry: bytes | None = None, extensions=None):
    """Returns (result, canonical bytes or None, notes).

    ``extensions`` is the official extensions this run implements (tools/oracle/ext: name ->
    module), or None for a core-only reader - every Core suite. When it is given, the run is a
    reader of those extensions: they pass FS-DOC-002, each is evaluated after the Core invariants
    as its specification's 1.2 says, and the derived values gain `extensions`, the derived values of
    each extension evaluated (empty when none is)."""
    implemented = {} if extensions is None else extensions
    notes = []
    known = None
    if registry is not None:                                    # tier 0: configuration (12.2)
        known = reg.load(registry)
        if known is None:
            return {'valid': False, 'diagnostics': [diag('FS-CFG-001')]}, None, ['the known extensions are not a valid registry']
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
        if isinstance(v, str) and v not in reader.versions:
            ds.append(diag('FS-DOC-001'))
        # FS-DOC-002 only for a well-formed extensionsRequired: an array of distinct names, each
        # in extensionsUsed. Anything else is left to the schema tier and FS-INV-004 (10.4).
        req, used = value.get('extensionsRequired'), value.get('extensionsUsed', {})
        if (isinstance(req, list) and all(isinstance(n, str) for n in req) and len(set(req)) == len(req)
                and isinstance(used, dict) and all(n in used for n in req)):
            for n in req:
                if n not in IMPLEMENTED_EXTENSIONS and n not in implemented:
                    ds.append(diag('FS-DOC-002'))
    if ds:
        return {'valid': False, 'diagnostics': sort_diags(ds)}, None, notes
    # tier 3: schema - of the draft the document declares (1.2.4)
    declared = value.get('floorspec') if isinstance(value, dict) else None
    problems = schema.check(value, declared if declared in reader.versions else reader.newest)
    if problems:
        notes.extend(problems)
        return {'valid': False, 'diagnostics': [diag('FS-SCH-001')]}, None, notes
    # tier 4: invariants
    ds = reference_tier(value)
    if not ds:
        doc = Doc(value)
        gds, bad_levels, no_top = graph_tier(doc)
        ds.extend(gds)
        bad_rooms = set()
        for level in sorted(doc.levels):
            if level not in bad_levels:
                rds = join_and_room_tier(doc, level)
                ds.extend(rds)
                bad_rooms.update(e for x in rds if x['code'].startswith('FS-INV-2') for e in x['elements'])
        ds.extend(opening_tier(doc, no_top))
        if reader.v03:
            ds.extend(clear_opening_tier(doc))
            ds.extend(floors.invariants(doc, bad_levels, bad_rooms, diag))
            ds.extend(stairs.invariants(doc, bad_levels, bad_rooms, diag))
        if reader.v02:
            ds.extend(program_invariants(value, diag))
            ds.extend(extension_tier(value, known))
            ds.extend(hosting_tier(doc, no_top))
            ds.extend(surface_tier(doc, bad_levels, bad_rooms))
    if any(x['severity'] == 'error' for x in ds):
        return {'valid': False, 'diagnostics': sort_diags(ds)}, None, notes
    doc = Doc(value)
    ext_ctxs = []
    if extensions is not None:                                  # each extension's spec, 1.2
        from .ext import official as ext
        eds, ext_ctxs = ext.evaluate(doc, known, implemented)
        if any(x['severity'] == 'error' for x in eds):
            return {'valid': False, 'diagnostics': sort_diags(eds)}, None, notes
        ds.extend(eds)
    ds.extend(lints(doc))
    derived = derive_all(doc)
    if reader.v02:
        ds.extend(program_lints(doc, diag))
        ds.extend(circulation_lints(doc, diag))
        derived.update(derive_02(doc))
    if reader.v03:
        derived.update(floors.derive(doc))
        derived.update(stairs.derive(doc))
        ds.extend(stairs.lints(doc, diag))
    if extensions is not None:
        from .ext import official as ext
        eds, derived['extensions'] = ext.finish(ext_ctxs)
        ds.extend(eds)
    result = {'valid': True, 'diagnostics': sort_diags(ds), 'hash': canon.content_hash(value),
              'derived': derived}
    return result, canon.canonical_bytes(value), notes

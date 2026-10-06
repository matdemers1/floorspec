"""Materials, assets and finishes (Core 0.3, chapter 18): the references a texture's maps and a wall's
finishes make (3.2), the material and finish invariants FS-INV-1001 to FS-INV-1004, the package
invariants FS-INV-1005 to FS-INV-1007 of a package validator (18.4), and the derived `finishes` (18.6).

Nothing here is geometry beyond 18.5.3's exact length test (to^2 <= dx^2 + dy^2) and the integer
rectangle tests of 18.5.2 and 18.5.4. Which room a wall's side faces is read from the half-edges
of the level's faces (6.1): a half-edge runs with its face on its left, so the wall taken from its
start to its end has the face on its left side, and taken the other way, on its right.
"""

from __future__ import annotations

import hashlib

from . import arcs
from .derive import Doc, LevelGraph

MAPS = ('asset', 'normal', 'metallicRoughness', 'occlusion')               # 18.2
MAP_MEDIA = ('image/png', 'image/jpeg', 'image/webp', 'image/ktx2')         # 18.2.2
SIDES = ('left', 'right')


def _faces(w: dict):
    """(side, face finish) of a wall's `finishes`, absent ones skipped."""
    f = w.get('finishes', {})
    return [(side, f[side]) for side in SIDES if side in f]


# ------------------------------------------------------------------------------ references (3.2)

def references(d: dict):
    """(collection, element ID, target ID, target collection) for a texture's maps other than
    `asset` (which 0.1's table already lists) and for a wall's face finishes and their regions."""
    out = []
    for mid, m in d.get('materials', {}).items():
        tex = m.get('texture', {})
        for k in MAPS[1:]:
            if k in tex:
                out.append(('materials', mid, tex[k], 'assets'))
    for wid, w in d.get('walls', {}).items():
        for _, face in _faces(w):
            if 'material' in face:
                out.append(('walls', wid, face['material'], 'materials'))
            for r in face.get('regions', []):
                out.append(('walls', wid, r['material'], 'materials'))
    return out


# ------------------------------------------------------------------------------ invariants (10.3, 10.4)

def _empty(r) -> bool:
    return r['to'] <= r['from'] or r['top'] <= r['bottom']


def _overlap(a, b) -> bool:
    return max(a['from'], b['from']) < min(a['to'], b['to']) and max(a['bottom'], b['bottom']) < min(a['top'], b['top'])


def invariants(doc: Doc, no_top, diag):
    """FS-INV-1001 to FS-INV-1004, for every region and every material. 1002 and 1003 are not
    evaluated for a region with 1001; 1002 does not test the top of a region on a wall with
    FS-INV-112 (`no_top`)."""
    ds = []
    for wid in sorted(doc.walls):
        w = doc.walls[wid]
        faces = _faces(w)
        if not faces:
            continue
        s, e = doc.junctions[w['start']]['position'], doc.junctions[w['end']]['position']
        D = (e[0] - s[0]) ** 2 + (e[1] - s[1]) ** 2
        poly = None if arcs.unfit(doc, wid) else arcs.wall_arc(doc, wid)

        def past_end(to):                                   # 18.5.3; an arc wall's length (21.5)
            if arcs.unfit(doc, wid):
                return False
            return to > arcs.length(poly) if poly is not None else to * to > D
        height = None if wid in no_top else doc.top_elevation(wid) - doc.base_elevation(wid)
        for _, face in faces:
            ok = []
            for r in face.get('regions', []):
                if _empty(r):
                    ds.append(diag('FS-INV-1001', [wid]))
                    continue
                ok.append(r)
                if past_end(r['to']) or (height is not None and r['top'] > height):
                    ds.append(diag('FS-INV-1002', [wid]))
            for i, a in enumerate(ok):
                for b in ok[i + 1:]:
                    if _overlap(a, b):
                        ds.append(diag('FS-INV-1003', [wid]))
    for mid in sorted(doc.materials):
        tex = doc.materials[mid].get('texture', {})
        for k in MAPS:
            if k in tex and doc.assets[tex[k]]['mediaType'] not in MAP_MEDIA:
                ds.append(diag('FS-INV-1004', [mid, tex[k]]))
    return ds


def package_invariants(doc: Doc, package: dict, diag):
    """FS-INV-1005 to FS-INV-1007 of a package validator (18.4): ``package`` maps each file's path in
    the package to its bytes. 1006 and 1007 are not evaluated for an asset with 1005."""
    ds = []
    for aid in sorted(doc.assets):
        a = doc.assets[aid]
        if 'path' not in a:
            continue
        data = package.get(a['path'])
        if data is None:
            ds.append(diag('FS-INV-1005', [aid]))
            continue
        if hashlib.sha256(data).hexdigest() != a['sha256']:
            ds.append(diag('FS-INV-1006', [aid]))
        if 'byteLength' in a and a['byteLength'] != len(data):
            ds.append(diag('FS-INV-1007', [aid]))
    return ds


# ------------------------------------------------------------------------------ derived (18.6)

def facing(doc: Doc):
    """{(wall, side): room} for every side of a wall that faces a room (18.6)."""
    out = {}
    for level in sorted(doc.levels):
        g = LevelGraph(doc, level)
        faces = g.faces()
        rooms = {}
        for rid, r in doc.rooms.items():
            if r['level'] == level:
                rooms[id(g.face_of(tuple(r['anchor']), faces))] = rid
        for f in faces:
            rid = rooms.get(id(f))
            if rid is None:
                continue
            for walk in [f['outer']] + f['holes']:
                for eid, u, _ in walk:
                    e = g.edges[eid]
                    if e.kind == 'wall':                        # an arc wall's segments face what the wall faces (21.3)
                        out[(e.src, 'left' if u == e.start else 'right')] = rid
    return out


def derive(doc: Doc) -> dict:
    """The derived `finishes` (18.6): each room's floor and ceiling finish, and each side of each
    wall whose finish resolves to a material or that has regions."""
    rooms = {}
    for rid in sorted(doc.rooms):
        r = doc.rooms[rid]
        v = {k: r[m] for k, m in (('floor', 'floorFinish'), ('ceiling', 'ceilingFinish')) if m in r}
        if v:
            rooms[rid] = v
    faces_of = facing(doc)
    walls = {}
    for wid in sorted(doc.walls):
        w = doc.walls[wid]
        own = w.get('finishes', {})
        layers = doc.effective_layers(wid) or []
        for side in SIDES:
            face = own.get(side, {})
            rid = faces_of.get((wid, side))
            v = {}
            if rid is not None:
                v['room'] = rid
            layer = (layers[0] if side == 'left' else layers[-1]) if layers else {}
            if 'material' in face:
                v['material'], v['source'] = face['material'], 'face'
            elif rid is not None and 'wallFinish' in doc.rooms[rid]:
                v['material'], v['source'] = doc.rooms[rid]['wallFinish'], 'room'
            elif 'material' in layer:
                v['material'], v['source'] = layer['material'], 'layer'
            regions = [dict(r) for r in face.get('regions', [])]
            if 'material' not in v and not regions:
                continue
            v['regions'] = regions
            walls.setdefault(wid, {})[side] = v
    return {'finishes': {'rooms': rooms, 'walls': walls}}


# ------------------------------------------------------------------------------ texture space (18.3)

def surface_st(doc: Doc, wid, side, point, z, region=None):
    """18.3: the exact surface coordinates (s, t) of the plan point `point` at elevation `z` on the
    `side` face of wall `wid` - or, given one of that face's regions, in the region's coordinates, from
    its lower corner on the left of a person facing it: (from, bottom) on a right face, (to, bottom) on
    a left one. s is a Surd (one radicand, |d|^2), t an integer. Nothing derived reports these; they
    pin the definition a renderer and an exporter follow."""
    from fractions import Fraction
    from .surd import Surd
    w = doc.walls[wid]
    S, E = doc.junctions[w['start']]['position'], doc.junctions[w['end']]['position']
    d = (E[0] - S[0], E[1] - S[1])
    D = d[0] * d[0] + d[1] * d[1]
    along = Surd.sqrt(D, Fraction((point[0] - S[0]) * d[0] + (point[1] - S[1]) * d[1], D))   # (P - S) . e
    s = along if side == 'right' else -along
    t = z - doc.base_elevation(wid)
    if region is not None:
        s = s - region['from'] if side == 'right' else s + region['to']
        t -= region['bottom']
    return s, t

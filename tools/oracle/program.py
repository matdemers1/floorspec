"""The program (Core 0.2, chapter 11): items, rooms that fulfil them, adjacent and connected rooms,
and the program lints.

Adjacency is read off the faces of each level's plane graph (11.4): every half-edge of a bounded
face's outer and inner cycles belongs to that face, and an edge lies between the faces of its two
half-edges. Net areas are compared exactly, as twice-areas of the rounded room polygons (6.4).
"""

from __future__ import annotations

from . import plane
from .derive import Doc, LevelGraph


def _room_area2(g: LevelGraph, faces, anchor) -> int:
    f = g.face_of(tuple(anchor), faces)
    outer, holes = g.room_polygon(f)
    return plane.area2(outer) + sum(plane.area2(h) for h in holes)


def _connecting_walls(doc: Doc) -> set:
    """Walls hosting an empty (cased) opening or a door (11.4)."""
    out = set()
    for o in doc.openings.values():
        fill = o.get('fill')
        if fill is None or doc.types[fill]['kind'] == 'doorType':
            out.add(o['wall'])
    return out


def room_relations(doc: Doc):
    """(adjacent pairs, connected pairs) of room IDs, each pair a frozenset, twice-areas, and the
    rooms connected to the outside - an edge between the room's face and the level's unbounded
    face that is a separator or a wall hosting a door or an empty opening (14.2)."""
    adjacent, connected, area2, outside = set(), set(), {}, set()
    doors = _connecting_walls(doc)
    for level in sorted(doc.levels):
        g = LevelGraph(doc, level)
        faces = g.faces()
        owner = {}
        for i, f in enumerate(faces):
            for walk in [f['outer']] + f['holes']:
                for h in walk:
                    owner[h] = i
        room_face = {}
        for rid, r in doc.rooms.items():
            if r['level'] != level:
                continue
            f = g.face_of(tuple(r['anchor']), faces)
            room_face[rid] = faces.index(f)
            area2[rid] = _room_area2(g, faces, r['anchor'])
        by_face = {i: rid for rid, i in room_face.items()}
        for e in g.edges.values():
            fa, fb = owner.get((e.id, e.start, e.end)), owner.get((e.id, e.end, e.start))
            joins = e.kind == 'separator' or e.src in doors          # an arc wall's segments are the wall's (21.3)
            if joins and (fa is None) != (fb is None):         # one side is the unbounded face
                f = fa if fb is None else fb
                if f in by_face:
                    outside.add(by_face[f])
            if fa is None or fb is None or fa == fb or fa not in by_face or fb not in by_face:
                continue
            pair = frozenset((by_face[fa], by_face[fb]))
            adjacent.add(pair)
            if joins:
                connected.add(pair)
    return adjacent, connected, area2, outside


def derive_program(doc: Doc):
    """The `program` member of the derived values (11.3, 11.4)."""
    program = doc.d.get('program', {})
    items = program.get('items', {})
    adjacency = program.get('adjacency', [])
    adjacent, connected, area2, _ = room_relations(doc)
    rooms_of = {i: sorted(rid for rid, r in doc.rooms.items() if r.get('brief') == i) for i in items}
    out_items = {}
    for iid, item in items.items():
        rs = rooms_of[iid]
        v = {'rooms': rs, 'countMet': len(rs) >= item.get('count', 1)}
        if 'minArea' in item:
            v['minAreaMet'] = all(area2[r] >= 2 * item['minArea'] for r in rs)
        if 'targetArea' in item:
            v['targetAreaMet'] = all(area2[r] >= 2 * item['targetArea'] for r in rs)
        out_items[iid] = v
    out_adj = []
    for a in adjacency:
        pairs = [frozenset((x, y)) for x in rooms_of[a['a']] for y in rooms_of[a['b']] if x != y]
        out_adj.append({'a': a['a'], 'b': a['b'], 'kind': a['kind'],
                        'adjacent': any(p in adjacent for p in pairs),
                        'connected': any(p in connected for p in pairs)})
    return {'items': out_items, 'adjacency': out_adj}, area2, rooms_of


def program_lints(doc: Doc, diag):
    ds = []
    derived, area2, rooms_of = derive_program(doc)
    items = doc.d.get('program', {}).get('items', {})
    for iid, item in items.items():
        if not derived['items'][iid]['countMet']:
            ds.append(diag('FS-LINT-008', [iid]))
        if 'minArea' in item:
            for r in rooms_of[iid]:
                if area2[r] < 2 * item['minArea']:
                    ds.append(diag('FS-LINT-009', [iid, r]))
    for a in derived['adjacency']:
        if a['kind'] == 'required' and not a['adjacent']:
            ds.append(diag('FS-LINT-010', [a['a'], a['b']]))
        if a['kind'] == 'forbidden' and a['adjacent']:
            ds.append(diag('FS-LINT-011', [a['a'], a['b']]))
    return ds


def program_invariants(d: dict, diag):
    """FS-INV-401..403 (11.2), on a document whose references resolve."""
    ds = []
    adjacency = d.get('program', {}).get('adjacency', [])
    seen_kinds: dict[frozenset, set] = {}
    seen = set()
    for a in adjacency:
        if a['a'] == a['b']:
            ds.append(diag('FS-INV-401', [a['a']]))
            continue
        pair = frozenset((a['a'], a['b']))
        if (pair, a['kind']) in seen:
            ds.append(diag('FS-INV-402', [a['a'], a['b']]))
        seen.add((pair, a['kind']))
        seen_kinds.setdefault(pair, set()).add(a['kind'])
    for pair, kinds in seen_kinds.items():
        if 'forbidden' in kinds and kinds & {'required', 'preferred'}:
            ds.append(diag('FS-INV-403', sorted(pair)))
    return ds

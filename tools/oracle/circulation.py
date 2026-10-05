"""Circulation (Core 0.2, chapter 14): the door graph of each building, its entries, which rooms
are reachable from an entry, which sleeping rooms are reachable only through another sleeping
room, and the circulation lints.

The door graph's nodes are rooms. Two rooms are joined when they are connected (11.4), or when
both have the function `circulation` and are on different levels of one building (14.1). A room is
an entry when an edge between its face and the level's unbounded face is a separator or a wall
hosting a door or an empty opening (14.2). Everything here is a breadth-first search over a finite
graph: exact, and independent of the order in which a document lists its elements.
"""

from __future__ import annotations

from .derive import Doc
from .program import room_relations


def _connecting_walls(doc: Doc) -> set:
    out = set()
    for o in doc.openings.values():
        fill = o.get('fill')
        if fill is None or doc.types[fill]['kind'] == 'doorType':
            out.add(o['wall'])
    return out


def _reach(nodes, links, start, removed=frozenset()):
    seen = set(r for r in start if r not in removed)
    todo = sorted(seen)
    while todo:
        r = todo.pop()
        for s in links.get(r, ()):
            if s not in seen and s not in removed and s in nodes:
                seen.add(s)
                todo.append(s)
    return seen


def building_of(doc: Doc, rid) -> str:
    return doc.levels[doc.rooms[rid]['level']]['building']


def derive_circulation(doc: Doc):
    """(the `circulation` member of the derived values, {building: (evaluated, has rooms, has entry)})."""
    _, connected, _, outside = room_relations(doc)
    links: dict[str, set] = {}
    for pair in connected:
        a, b = sorted(pair)
        links.setdefault(a, set()).add(b)
        links.setdefault(b, set()).add(a)
    halls = sorted(r for r, room in doc.rooms.items() if room.get('function', 'unspecified') == 'circulation')
    for i, a in enumerate(halls):
        for b in halls[i + 1:]:
            if building_of(doc, a) == building_of(doc, b) and doc.rooms[a]['level'] != doc.rooms[b]['level']:
                links.setdefault(a, set()).add(b)
                links.setdefault(b, set()).add(a)
    out = {}
    buildings = {}
    doors = _connecting_walls(doc)
    for bid in sorted(doc.buildings):
        levels = {lid for lid, lv in doc.levels.items() if lv['building'] == bid}
        nodes = {r for r, room in doc.rooms.items() if room['level'] in levels}
        entries = nodes & outside
        reachable = _reach(nodes, links, entries)
        sleeping = {r for r in nodes if doc.rooms[r].get('function', 'unspecified') == 'sleeping'}
        evaluated = any(doc.walls[w]['level'] in levels for w in doors)
        buildings[bid] = (evaluated, bool(nodes), bool(entries))
        for r in nodes:
            v = {'entry': r in entries, 'reachable': r in reachable}
            if r in sleeping:
                v['throughSleeping'] = r in reachable and r not in _reach(nodes, links, entries, sleeping - {r})
            out[r] = v
    return dict(sorted(out.items())), buildings


def circulation_lints(doc: Doc, diag):
    ds = []
    derived, buildings = derive_circulation(doc)
    for bid, (evaluated, has_rooms, has_entry) in buildings.items():
        if not evaluated or not has_rooms:
            continue
        if not has_entry:
            ds.append(diag('FS-LINT-014', [bid]))
            continue
        for rid, v in derived.items():
            if building_of(doc, rid) != bid:
                continue
            if not v['reachable']:
                ds.append(diag('FS-LINT-012', [rid]))
            elif v.get('throughSleeping'):
                ds.append(diag('FS-LINT-013', [rid]))
    return ds

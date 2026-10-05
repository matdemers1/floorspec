"""What the official extensions share: their activation, the one space of IDs, the room an
element is in, and diagnostics in an extension's own namespace.

An extension module (electrical.py, ...) defines NAME, VERSION, CORE, SCHEMA (the path of its schema
file), SEVERITY (its lints' severities; every other code is an error), and three functions of a
Context: invariants(ctx), lints(ctx) and derive(ctx). validate.check runs them for every extension
it implements that the document uses at a version at which it is known (spec.md 1.2 of each).
"""

from __future__ import annotations

import json
import os

from .. import plane
from ..derive import Doc, LevelGraph
from .jsonschema import Schema

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CORE_COLLECTIONS = ('buildings', 'levels', 'junctions', 'walls', 'separators', 'openings', 'rooms', 'slabs',
                    'types', 'materials', 'assets', 'roofs')


def load_schema(name: str, short: str) -> Schema:
    with open(os.path.join(REPO, 'registry', name, f'{short}.schema.json'), encoding='utf-8') as f:
        return Schema(json.load(f))


class Context:
    """One extension's data in one valid document, with what its rules read."""

    def __init__(self, doc: Doc, name: str, severity: dict):
        self.doc = doc
        self.d = doc.d
        self.name = name
        self.severity = severity
        data = self.d.get('extensions', {}).get(name, {})
        self.data = data if isinstance(data, dict) else {}
        self.collections = self.data.get('collections', {})
        # every element of every extension: ID -> (extension, collection, element)
        self.ext = {eid: (x, c, el) for x, c, eid, el in doc.ext_elements}
        self._rooms = None

    def coll(self, c: str) -> dict:
        return self.collections.get(c, {})

    def own(self, eid):
        """(collection, element) when eid is an element of this extension, else None."""
        x = self.ext.get(eid)
        return (x[1], x[2]) if x is not None and x[0] == self.name else None

    def diag(self, code, elements=()):
        return {'code': code, 'severity': self.severity.get(code, 'error'),
                'elements': sorted(set(e for e in elements if e is not None))}

    def space(self) -> set:
        """Core 3.1.3: every ID of an element, a program item or an extension element."""
        out = set()
        for c in CORE_COLLECTIONS:
            out.update(self.d.get(c, {}))
        out.update(self.doc.items)
        out.update(self.ext)
        return out

    def has_purpose(self, el, purpose: str) -> bool:
        return any(env.get('purpose') == purpose for env in el.get('clearances', {}).values())

    # ------------------------------------------------------------------ the room of an element
    def rooms(self) -> dict:
        """Every extension element's room, or None (each extension's spec, 6.1)."""
        if self._rooms is not None:
            return self._rooms
        doc = self.doc
        graphs = {}

        def level(lid):
            if lid not in graphs:
                g = LevelGraph(doc, lid)
                faces = g.faces()
                owner = {}
                for i, f in enumerate(faces):
                    for walk in [f['outer']] + f['holes']:
                        for h in walk:
                            owner[h] = i
                by_face = {}
                for rid, r in doc.rooms.items():
                    if r['level'] == lid:
                        f = g.face_of(tuple(r['anchor']), faces)
                        by_face[faces.index(f)] = rid
                graphs[lid] = (g, faces, owner, by_face)
            return graphs[lid]

        out = {}
        for eid, (_, _, el) in self.ext.items():
            host = el.get('host')
            rid = None
            if host is not None and host['mode'] == 'surface':
                rid = host['room']
            elif host is not None and host['mode'] == 'wallFace':
                w = doc.walls[host['wall']]
                g, faces, owner, by_face = level(w['level'])
                h = (host['wall'], w['start'], w['end']) if host['side'] == 'left' else (host['wall'], w['end'], w['start'])
                rid = by_face.get(owner.get(h))
            elif host is not None:
                g, faces, owner, by_face = level(host['level'])
                p = tuple(host['position'])
                if not g.on_location_line(p):
                    f = g.face_of(p, faces)
                    rid = by_face.get(faces.index(f)) if f is not None else None
            out[eid] = rid
        self._rooms = out
        return out

    def rooms_derived(self) -> dict:
        """6.1: every room that holds an element of this extension, and those elements, sorted."""
        out = {}
        for eid, rid in self.rooms().items():
            if rid is not None and self.ext[eid][0] == self.name:
                out.setdefault(rid, []).append(eid)
        return {r: sorted(v) for r, v in sorted(out.items())}


def check_ids(ctx: Context, member: str, code: str):
    """An extension's own records (circuits, stacks, gas sources) share the one space of IDs."""
    space = ctx.space()
    return [ctx.diag(code, [rid]) for rid in ctx.data.get(member, {}) if rid in space]


__all__ = ['Context', 'check_ids', 'load_schema', 'plane']

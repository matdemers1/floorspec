"""What the measures read from one valid document: the Core oracle's derived values, each level's
faces, the room of every extension element (4.4), extension members with their defaults (4.5), and
which official extensions are evaluated for the document (1.2)."""

from __future__ import annotations

import json
import os

from ..derive import Doc, LevelGraph
from ..ext.common import Context as ExtContext
from .. import frames

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SCHEMAS = {'FS_electrical': 'electrical', 'FS_plumbing': 'plumbing', 'FS_mechanical': 'mechanical',
           'FS_lowvoltage': 'lowvoltage'}
_defaults_cache = {}


def _schema(name):
    if name not in _defaults_cache:
        with open(os.path.join(REPO, 'registry', name, f'{SCHEMAS[name]}.schema.json'), encoding='utf-8') as f:
            _defaults_cache[name] = json.load(f)
    return _defaults_cache[name]


def _defaults_of(schema, ref_holder):
    ref = ref_holder.get('additionalProperties', {}).get('$ref', '')
    d = schema['$defs'].get(ref.split('/')[-1], {}) if ref.startswith('#/$defs/') else {}
    return {k: p['default'] for k, p in d.get('properties', {}).items() if 'default' in p}


def element_defaults(ext, coll) -> dict:
    """4.5: the defaults the extension's specification gives an element's members (its schema
    carries them as `default`)."""
    if ext not in SCHEMAS:
        return {}
    s = _schema(ext)
    holder = s.get('properties', {}).get('collections', {}).get('properties', {}).get(coll)
    return _defaults_of(s, holder) if holder else {}


def circuit_defaults() -> dict:
    s = _schema('FS_electrical')
    return _defaults_of(s, s['properties']['circuits'])


def member(obj, defaults, name):
    """(present, value): a member read with its default (4.5)."""
    if name in obj:
        return True, obj[name]
    if name in defaults:
        return True, defaults[name]
    return False, None


def matches(obj, defaults, match) -> bool:
    for k, want in match.items():
        ok, v = member(obj, defaults, k)
        if not ok:
            return False
        if isinstance(v, list):
            if not any(type(x) is type(want) and x == want for x in v):
                return False
        elif not (type(v) is type(want) and v == want):
            return False
    return True


class Level:
    def __init__(self, doc: Doc, lid):
        self.g = LevelGraph(doc, lid)
        self.faces = self.g.faces()
        self.owner = {}
        for i, f in enumerate(self.faces):
            for walk in [f['outer']] + f['holes']:
                for h in walk:
                    self.owner[h] = i
        self.room_face, self.face_room = {}, {}
        for rid, r in doc.rooms.items():
            if r['level'] == lid:
                f = self.g.face_of(tuple(r['anchor']), self.faces)
                i = self.faces.index(f)
                self.room_face[rid] = i
                self.face_room[i] = rid

    def half_edges(self, eid):
        e = self.g.edges[eid]
        return (eid, e.start, e.end), (eid, e.end, e.start)


class Ctx:
    def __init__(self, doc: Doc, derived: dict, evaluated: set, units: str):
        self.doc, self.d, self.derived, self.evaluated, self.units = doc, doc.d, derived, set(evaluated), units
        self.ext = {eid: (x, c, el) for x, c, eid, el in doc.ext_elements}
        self._levels = {}
        self._rooms = ExtContext(doc, 'FS_electrical', {}).rooms()

    def level(self, lid) -> Level:
        if lid not in self._levels:
            self._levels[lid] = Level(self.doc, lid)
        return self._levels[lid]

    def room_of(self, eid):
        return self._rooms.get(eid)

    def floor(self, lid) -> int:
        return self.doc.levels[lid]['elevation']

    def circuits(self) -> dict:
        data = self.d.get('extensions', {}).get('FS_electrical', {})
        return data.get('circuits', {}) if isinstance(data, dict) else {}

    # ------------------------------------------------------------------ targets (4.1)
    def target_level(self, t) -> str:
        k, i = t['kind'], t['id']
        if k == 'room':
            return self.doc.rooms[i]['level']
        if k == 'opening':
            return self.doc.walls[self.doc.openings[i]['wall']]['level']
        if k == 'element':
            return self.ext[i][2]['fallback']['level']
        if k == 'envelope':
            return self.derived['clearances'][i][t['envelope']]['level']
        if k == 'stair':                                                  # Core 0.3, 17.1: the level it rises from
            return self.doc.stairs[i]['level']
        return i

    def envelope(self, owner, name):
        """(box, frame, derived) of a clearance envelope."""
        if owner in self.doc.openings:
            o = self.doc.openings[owner]
            box = self.doc.types[o['fill']]['clearances'][name]
            frame = frames.opening_frame(self.doc, owner)
        else:
            el = self.ext[owner][2]
            box = el['clearances'][name]
            frame = frames.element_frame(self.doc, el)
        return box, frame, self.derived['clearances'][owner][name]

    def envelopes_of(self, owner):
        return sorted(self.derived['clearances'].get(owner, {}))

    def host_wall(self, owner):
        if owner in self.doc.openings:
            return self.doc.openings[owner]['wall']
        host = self.ext[owner][2].get('host')
        return host['wall'] if host is not None and host['mode'] == 'wallFace' else None

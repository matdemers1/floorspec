"""Resolving references against the working copy (Ops chapter 3).

Every reference is resolved against the working copy as it stands before the operation that
holds it (1.2). The grammar's details, as 3.1-3.3 and 7.1 state them:

- Keywords (`north`, `wall`, `of`, `between`, `start`, `from`, `toward`, `centered` …) are matched
  ignoring case, as the letters of a length are; whitespace between words is one or more spaces or
  tabs. Room names are compared with Unicode case folding.
- A plain string (no selector keyword form) is an ID, a room name, or both: every element it
  names is a match. A string that has a selector form is read only as that form.
- `wall between <room> and <room>`: when a room name itself contains " and ", every split is
  tried; exactly one split must resolve.
- `start of <wall>` / `end of <wall>`: `<wall>` is an edge's ID, or an edge selector.
- Only elements of the collections the operation's member expects count as matches.
- FS-OPS-003 names no elements when the reference is the request's own; it names the element
  whose member or reference is missing when that is an element of the document.

Ops 0.2 adds program items and extension elements to what an ID can name (space.py), the forms
`item <item>` and `brief of <room>`, and, where a member expects a program item or an extension
element, matching a plain string against those elements' names as well. Under Ops 0.1 none of
this exists, and a string of those forms is an ID or a room name like any other.
"""

from __future__ import annotations

import re
from fractions import Fraction

from ..schema import ID_RE
from ..surd import Surd
from .errors import OpsError
from .faces import Broken, LevelFaces, coll, edit_view, is_point
from .refs import CENTERED, DIR_OF, DIRECTIONS, FROM_END, FROM_TOWARD, VECTOR, length
from .space import kind, items, ext_elements, locate
from .version import OPS_01, Profile

SIDE_SEL = re.compile(r'[ \t]*(?P<side>north|south|east|west)[ \t]+(?P<kind>wall|separator)[ \t]+of[ \t]+(?P<room>.+?)[ \t]*', re.I | re.S)
BETWEEN_SEL = re.compile(r'[ \t]*(?P<kind>wall|separator)[ \t]+between[ \t]+(?P<rest>.+?)[ \t]*', re.I | re.S)
AND = re.compile(r'[ \t]+and[ \t]+', re.I)
END_SEL = re.compile(r'[ \t]*(?P<which>start|end)[ \t]+of[ \t]+(?P<edge>.+?)[ \t]*', re.I | re.S)
ITEM_SEL = re.compile(r'[ \t]*item[ \t]+(?P<item>.+?)[ \t]*', re.I | re.S)                 # Ops 0.2
BRIEF_SEL = re.compile(r'[ \t]*brief[ \t]+of[ \t]+(?P<room>.+?)[ \t]*', re.I | re.S)       # Ops 0.2

KIND = {'wall': 'walls', 'separator': 'separators'}
EDGES = ('walls', 'separators')
TARGETS = ('$project', '$site', '$document')


def side_of(n) -> str:
    """3.4: the side an outward normal (nx, ny) is on; exactly one for every direction."""
    nx, ny = n
    if nx > 0 and -nx < ny <= nx:
        return 'east'
    if ny > 0 and -ny <= nx < ny:
        return 'north'
    if nx < 0 and nx <= ny < -nx:
        return 'west'
    return 'south'                      # ny < 0 and ny < nx <= -ny


def outward_normal(pos, half_edge):
    """The right-hand normal of a half-edge walked with its face on the left (3.4)."""
    _, u, v = half_edge
    dx, dy = pos[v][0] - pos[u][0], pos[v][1] - pos[u][1]
    return (dy, -dx)


class Resolver:
    def __init__(self, wc: dict, profile: Profile = OPS_01, option=None):
        self.wc = wc
        self.profile = profile
        self.option = option                     # Ops 0.3, 2.8: context.option
        self._view = None
        self._levels: dict[str, LevelFaces | Broken] = {}

    @property
    def view(self) -> dict:
        """The working copy as seen in the edit design (Ops 0.3, 2.8): what faces and rooms are read from."""
        if self._view is None:
            self._view = edit_view(self.wc, self.option)
        return self._view

    # ------------------------------------------------------------------ document access
    def collection_of(self, eid: str) -> str | None:
        """The kind of element `eid` is: a collection name, 'items' or 'ext' (Ops 0.2)."""
        loc = locate(self.wc, eid, self.profile)
        return kind(loc[0]) if loc else None

    def get(self, c: str, eid: str):
        return coll(self.wc, c).get(eid)

    def level_faces(self, level, pointer) -> LevelFaces:
        """The faces of a level, or FS-OPS-007 naming it (3.4.1)."""
        if not isinstance(level, str):
            raise OpsError('FS-OPS-007', [], pointer, 'the room is on no level')
        if level not in self._levels:
            try:
                self._levels[level] = LevelFaces(self.view, level)
            except Broken as e:
                self._levels[level] = e
        lf = self._levels[level]
        if isinstance(lf, Broken):
            raise OpsError('FS-OPS-007', [level], pointer, str(lf))
        return lf

    def room_face(self, rid: str, pointer):
        """(LevelFaces, face index) of a room's face; FS-OPS-007 when its level has none to give
        or its anchor is in no bounded face."""
        r = self.get('rooms', rid)
        level = r.get('level') if isinstance(r, dict) else None
        lf = self.level_faces(level, pointer)
        f = lf.face_of(r['anchor']) if is_point(r.get('anchor')) else None
        if f is None:
            raise OpsError('FS-OPS-007', [level], pointer, f'the anchor of {rid} is in no bounded face')
        return lf, f

    # ------------------------------------------------------------------ element selectors
    def _unique(self, matches, pointer, what):
        found = sorted(set(matches))
        if not found:
            raise OpsError('FS-OPS-003', [], pointer, f'{what!r} matches nothing')
        if len(found) > 1:
            raise OpsError('FS-OPS-004', [eid for _, eid in found], pointer, f'{what!r} matches {len(found)} elements')
        return found[0]

    def room(self, s: str, pointer) -> str:
        """`<room>`: an ID or a room name."""
        return self._unique(self._plain(s, ('rooms',)), pointer, s)[1]

    def _plain(self, s: str, kinds):
        out = []
        c = self.collection_of(s)
        if c is not None and (kinds is None or c in kinds):
            out.append((c, s))
        key = s.casefold()

        def named(k, elements):
            for eid, e in elements:
                if isinstance(e, dict) and isinstance(e.get('name'), str) and e['name'].casefold() == key:
                    out.append((k, eid))
        if kinds is None or 'rooms' in kinds:
            named('rooms', coll(self.wc, 'rooms').items())
        if kinds is not None and 'items' in kinds:             # Ops 0.2: only where an item is expected
            named('items', items(self.wc, self.profile).items())
        if kinds is not None and 'ext' in kinds:               # ... or an extension element
            named('ext', [(eid, el) for _, _, eid, el in ext_elements(self.wc, self.profile)])
        return out

    def item(self, s: str, pointer) -> str:
        """A program item (Ops 0.2): an ID or a name, or `item <item>` or `brief of <room>`."""
        return self.element(s, ('items',), pointer)[1]

    def element(self, s: str, kinds, pointer):
        """(collection, ID) of the one element a string names, among `kinds` (None: any)."""
        m = SIDE_SEL.fullmatch(s)
        if m:
            c = KIND[m['kind'].lower()]
            rid = self.room(m['room'], pointer)
            lf, f = self.room_face(rid, pointer)
            side = m['side'].lower()
            found = [(c, h[0]) for h in lf.faces[f]['outer']
                     if lf.edges[h[0]][0] == c and side_of(outward_normal(lf.pos, h)) == side]
            return self._unique([x for x in found if kinds is None or x[0] in kinds], pointer, s)
        m = BETWEEN_SEL.fullmatch(s)
        if m:
            c = KIND[m['kind'].lower()]
            r1, r2 = self._room_pair(m['rest'], pointer)
            lf1, f1 = self.room_face(r1, pointer)
            lf2, f2 = self.room_face(r2, pointer)
            found = []
            if lf1 is lf2:
                for eid, (ec, st, en) in lf1.edges.items():
                    if ec != c:
                        continue
                    sides = {lf1.he_face.get((eid, st, en)), lf1.he_face.get((eid, en, st))}
                    if sides == {f1, f2} or (f1 == f2 and sides == {f1}):
                        found.append((c, eid))
            return self._unique([x for x in found if kinds is None or x[0] in kinds], pointer, s)
        if self.profile.v02:
            m = ITEM_SEL.fullmatch(s)
            if m:
                found = self._plain(m['item'], ('items',))
                return self._unique([x for x in found if kinds is None or x[0] in kinds], pointer, s)
            m = BRIEF_SEL.fullmatch(s)
            if m:
                rid = self.room(m['room'], pointer)
                r = self.get('rooms', rid)
                brief = r.get('brief') if isinstance(r, dict) else None
                if not (isinstance(brief, str) and brief in items(self.wc, self.profile)):
                    raise OpsError('FS-OPS-003', [rid], pointer, f'{rid} fulfils no program item')
                return self._unique([x for x in [('items', brief)] if kinds is None or x[0] in kinds], pointer, s)
        m = END_SEL.fullmatch(s)
        if m:
            ec, eid = self.element(m['edge'], EDGES, pointer)
            e = self.get(ec, eid)
            jid = e.get(m['which'].lower()) if isinstance(e, dict) else None
            if not (isinstance(jid, str) and jid in coll(self.wc, 'junctions')):
                raise OpsError('FS-OPS-003', [eid], pointer, f'the {m["which"]} of {eid} is not a junction')
            return self._unique([x for x in [('junctions', jid)] if kinds is None or x[0] in kinds], pointer, s)
        return self._unique(self._plain(s, kinds), pointer, s)

    def _room_pair(self, rest: str, pointer):
        splits = [(rest[:m.start()], rest[m.end():]) for m in AND.finditer(rest)]
        if not splits:
            raise OpsError('FS-OPS-003', [], pointer, f'{rest!r} names no two rooms')
        found, first_error = [], None
        for a, b in splits:
            try:
                found.append((self.room(a, pointer), self.room(b, pointer)))
            except OpsError as e:
                first_error = first_error or e
        if not found:
            raise first_error
        if len(set(found)) > 1:
            raise OpsError('FS-OPS-004', [r for pair in found for r in pair], pointer, f'{rest!r} splits more than one way')
        return found[0]

    def target(self, s: str, pointer):
        """setProperty / unsetProperty: an element, or $project, $site, $document (2.3)."""
        if s in TARGETS:
            return (None, s)
        return self.element(s, None, pointer)

    # ------------------------------------------------------------------ geometry access
    def junction_pos(self, jid: str, pointer):
        j = self.get('junctions', jid)
        if not (isinstance(j, dict) and is_point(j.get('position'))):
            raise OpsError('FS-OPS-003', [jid], pointer, f'{jid} has no position')
        return tuple(j['position'])

    def junction(self, s: str, pointer) -> str:
        return self.element(s, ('junctions',), pointer)[1]

    def wall_line(self, c: str, eid: str, pointer):
        """(start ID, end ID, start position, end position) of an edge."""
        e = self.get(c, eid)
        s, t = (e.get('start'), e.get('end')) if isinstance(e, dict) else (None, None)
        js = coll(self.wc, 'junctions')
        if not (isinstance(s, str) and isinstance(t, str) and s in js and t in js):
            raise OpsError('FS-OPS-003', [eid], pointer, f'{eid} does not run between two junctions')
        return s, t, self.junction_pos(s, pointer), self.junction_pos(t, pointer)

    # ------------------------------------------------------------------ points, vectors, positions
    def point_or_junction(self, v, pointer):
        """('junction', ID) when v names a junction, else ('point', (x, y))  (3.2, 4.1)."""
        if isinstance(v, list):
            return 'point', (length(v[0], f'{pointer}/0'), length(v[1], f'{pointer}/1'))
        m = FROM_TOWARD.fullmatch(v)
        if m:
            d = length(m['len'], pointer)
            p1 = self.junction_pos(self.junction(m['a'], pointer), pointer)
            p2 = self.junction_pos(self.junction(m['b'], pointer), pointer)
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            D = dx * dx + dy * dy
            if D == 0:
                raise OpsError('FS-OPS-003', [], pointer, 'the two junctions coincide: no direction')
            return 'point', ((Surd(p1[0]) + Surd.sqrt(D, Fraction(d * dx, D))).round(),
                             (Surd(p1[1]) + Surd.sqrt(D, Fraction(d * dy, D))).round())
        m = DIR_OF.fullmatch(v)
        if m:
            d = length(m['len'], pointer)
            p = self.junction_pos(self.junction(m['j'], pointer), pointer)
            ux, uy = DIRECTIONS[m['dir'].lower()]
            return 'point', (p[0] + d * ux, p[1] + d * uy)
        if END_SEL.fullmatch(v) or ID_RE.fullmatch(v):
            return 'junction', self.junction(v, pointer)
        raise OpsError('FS-OPS-012', [], pointer, f'{v!r} is not a point')

    def point(self, v, pointer):
        kind, x = self.point_or_junction(v, pointer)
        return x if kind == 'point' else self.junction_pos(x, pointer)

    def vector(self, v, pointer):
        if isinstance(v, list):
            return (length(v[0], f'{pointer}/0'), length(v[1], f'{pointer}/1'))
        m = VECTOR.fullmatch(v)
        if not m:
            raise OpsError('FS-OPS-012', [], pointer, f'{v!r} is not a vector')
        d = length(m['len'], pointer)
        ux, uy = DIRECTIONS[m['dir'].lower()]
        return (d * ux, d * uy)

    @staticmethod
    def position(v, L, w: int, pointer) -> int:
        """3.5: the near edge's offset along a wall whose location line has the exact length L (a Surd) - an arc
        wall's along its polyline (Core 21.6) - for a width w."""
        if type(v) is int:
            return v
        if CENTERED.fullmatch(v):
            return ((L - w) / 2).round()
        m = FROM_END.fullmatch(v)
        if m:
            d = length(m['len'], pointer)
            return d if m['which'].lower() == 'start' else (L - d - w).round()
        return length(v, pointer)

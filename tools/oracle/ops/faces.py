"""The faces of one level of a working copy (Ops 3.4), and when a level has none to give.

A selector or a composite that reads faces needs the level to be a plane graph: Core 5.1-5.3
hold on it (no coincident junctions, no edge from a junction to itself, no two edges between one
pair of junctions, no crossings, no junction inside an edge, no overlaps). A working copy can be
anything mid-batch, so the level must also be well formed enough to read: every junction on it
has an integer position, and every edge on it runs between two junctions on it. When either
fails, the level has no faces to give: `Broken`.

Faces are those of Core 6.1, computed by the Core oracle's walks on a copy of the level that
keeps only junctions and edges (thickness plays no part in which face is which).
"""

from __future__ import annotations

from .. import arcs, plane
from ..validate import in_interior, location_lines_meet
from ..derive import Doc, LevelGraph


class Broken(Exception):
    """The level breaks Core 5.1-5.3, or cannot be read as a graph."""


def is_point(p) -> bool:
    return isinstance(p, list) and len(p) == 2 and all(type(x) is int for x in p)


def coll(wc: dict, name: str) -> dict:
    v = wc.get(name)
    return v if isinstance(v, dict) else {}


OPTIONAL = ('junctions', 'walls', 'separators', 'rooms')


def edit_view(wc: dict, option=None) -> dict:
    """Ops 0.3, 2.8: the working copy as seen in the edit design - `option` for its set, when the
    context names one, and every other set's primary - for the faces and rooms a reference reads.
    An element in any other option is left out, and so is one whose option is not an option of the
    working copy. A working copy with no element in an option is itself."""
    if not any(isinstance(e, dict) and 'option' in e for c in OPTIONAL for e in coll(wc, c).values()):
        return wc
    opts, sets = coll(wc, 'options'), coll(wc, 'optionSets')

    def set_of(o):
        x = opts.get(o) if isinstance(o, str) else None
        return x.get('set') if isinstance(x, dict) else None
    chosen = {s.get('primary') for sid, s in sets.items()
              if isinstance(s, dict) and (option is None or sid != set_of(option))}
    if option is not None:
        chosen.add(option)
    chosen = {o for o in chosen if isinstance(o, str) and o in opts}
    v = dict(wc)
    for c in OPTIONAL:
        v[c] = {k: e for k, e in coll(wc, c).items() if not (isinstance(e, dict) and 'option' in e)
                or e['option'] in chosen}
    return v


class LevelFaces:
    """The plane graph of one level: positions, edges, bounded faces and which face each
    half-edge has on its left."""

    def __init__(self, wc: dict, level: str):
        self.level = level
        self.pos: dict[str, tuple[int, int]] = {}
        for jid, j in coll(wc, 'junctions').items():
            if isinstance(j, dict) and j.get('level') == level:
                if not is_point(j.get('position')):
                    raise Broken(f'junction {jid} has no position')
                self.pos[jid] = tuple(j['position'])
        self.edges: dict[str, tuple[str, str, str]] = {}      # id -> (collection, start, end)
        self.arc: dict[str, int] = {}                           # id -> sagitta, for an arc edge (Core 0.4, 21.1)
        for c in ('walls', 'separators'):
            for eid, e in coll(wc, c).items():
                if isinstance(e, dict) and e.get('level') == level:
                    s, t = e.get('start'), e.get('end')
                    if not (isinstance(s, str) and isinstance(t, str) and s in self.pos and t in self.pos):
                        raise Broken(f'edge {eid} does not run between two junctions on {level}')
                    self.edges[eid] = (c, s, t)
                    a = e.get('arc')                                        # Core 0.4, 21.1: an arc edge
                    h = a.get('sagitta') if isinstance(a, dict) else None
                    if type(h) is int and h != 0 and self.pos[s] != self.pos[t] and arcs.fits(self.pos[s], self.pos[t], h):
                        self.arc[eid] = h
        self.lines = {eid: (arcs.polyline(self.pos[s], self.pos[t], self.arc[eid]) if eid in self.arc
                            else (self.pos[s], self.pos[t])) for eid, (_, s, t) in self.edges.items()}
        self._planar()

        def edge(eid, s, t):
            e = {'level': level, 'start': s, 'end': t}
            if eid in self.arc:
                e['arc'] = {'sagitta': self.arc[eid]}
            return e
        sanitized = {
            'levels': {level: {}},
            'junctions': {j: {'level': level, 'position': list(p)} for j, p in self.pos.items()},
            'walls': {e: edge(e, s, t) for e, (c, s, t) in self.edges.items() if c == 'walls'},
            'separators': {e: edge(e, s, t) for e, (c, s, t) in self.edges.items() if c == 'separators'},
        }
        self.g = LevelGraph(Doc(sanitized), level)
        self._faces()

    def _planar(self):
        """Core 5.1.1, 5.2.1, 5.2.2, 5.3.1, 5.3.2, 5.3.3 - exactly the graph tests of the validator."""
        if len(set(self.pos.values())) != len(self.pos):
            raise Broken('two junctions share a position')
        es = sorted(self.edges.items())
        for i, (x, (_, sx, ex)) in enumerate(es):
            if sx == ex:
                raise Broken(f'edge {x} starts and ends at one junction')
            for y, (_, sy, ey) in es[i + 1:]:
                if {sx, ex} == {sy, ey}:
                    raise Broken(f'edges {x} and {y} connect the same junctions')
                if location_lines_meet(self.lines[x], self.lines[y]) is not None:   # 5.3, 21.3.1
                    raise Broken(f'edges {x} and {y} cross or overlap')
            for j, p in self.pos.items():
                if in_interior(p, self.lines[x]):
                    raise Broken(f'junction {j} lies inside edge {x}')

    def _faces(self):
        g = self.g
        walks = g.walks()
        parent = {j: j for j in g.pos}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for e in g.edges.values():
            parent[find(e.start)] = find(e.end)
        info = []
        for w in walks:
            pos = g.walk_positions(w)
            info.append({'walk': self._collapse(w), 'pos': pos, 'area2': plane.area2(pos), 'comp': find(w[0][1])})
        self.faces = [{'outer': x['walk'], 'pos': x['pos'], 'area2': x['area2'], 'comp': x['comp'], 'holes': []}
                      for x in info if x['area2'] > 0]
        self.he_face: dict[tuple, int | None] = {}
        for i, f in enumerate(self.faces):
            for h in f['outer']:
                self.he_face[h] = i
        for x in info:
            if x['area2'] > 0:
                continue
            best = None
            for i, f in enumerate(self.faces):
                if f['comp'] != x['comp'] and plane.winding(x['pos'][0], f['pos']) != 0:
                    if best is None or f['area2'] < self.faces[best]['area2']:
                        best = i
            if best is not None:
                self.faces[best]['holes'].append(x['walk'])
            for h in x['walk']:
                self.he_face[h] = best

    def _collapse(self, walk):
        """A walk of the level graph with each run of an arc edge's segments (Core 21.3) made one half-edge of the
        arc edge, between its junctions - so that a walk names the document's edges and junctions only."""
        g = self.g
        k = next((i for i, (_, u, _) in enumerate(walk) if u in self.pos), 0)
        walk = walk[k:] + walk[:k]
        out = []
        for eid, u, v in walk:
            src = g.edges[eid].src
            if src == eid:
                out.append((eid, u, v))
            elif u in self.pos:
                out.append([src, u, v])
            else:
                out[-1][2] = v
        return [tuple(h) for h in out]

    def face_of(self, point) -> int | None:
        """The bounded face containing a point, or None when the point is in the unbounded face
        or on a location line."""
        p = tuple(point)
        if any(plane.on_closed_segment(p, a, b) for line in self.lines.values() for a, b in zip(line, line[1:])):
            return None
        best = None
        for i, f in enumerate(self.faces):
            if plane.winding(p, f['pos']) != 0 and (best is None or f['area2'] < self.faces[best]['area2']):
                best = i
        return best

    def incident(self, j: str):
        """(edge id, other junction) for every edge at junction j."""
        out = []
        for eid, (_, s, t) in self.edges.items():
            if s == j:
                out.append((eid, t))
            elif t == j:
                out.append((eid, s))
        return out

    def rooms_in(self, wc: dict, face: int | None) -> list[str]:
        """The rooms on this level whose anchors are in a face."""
        if face is None:
            return []
        out = []
        for rid, r in coll(wc, 'rooms').items():
            if isinstance(r, dict) and r.get('level') == self.level and is_point(r.get('anchor')):
                if self.face_of(r['anchor']) == face:
                    out.append(rid)
        return sorted(out)

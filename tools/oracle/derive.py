"""Exact derivation (chapters 5-7): face lines, wedges, corner sequences, face ends, butt joins,
junction fills, wall outlines, elevations, faces of the plane graph, room polygons, anchors,
net areas and opening placement.

Everything is computed exactly - corner points as :class:`Surd` pairs - and rounded once, with
round-half-to-even, only where the specification says a value is output or compared after
rounding.
"""

from __future__ import annotations

from fractions import Fraction
from functools import cmp_to_key

from . import arcs, plane
from .surd import Surd


# ------------------------------------------------------------------------------ document access

def ext_elements(d: dict):
    """Core 0.2, 12.5: (extension, collection, ID, element) for every extension element - only in a
    document that declares 0.2, 0.3 or 0.4 (1.2.8); in a 0.1 document, extension data is opaque."""
    out = []
    if d.get('floorspec') not in ('0.2', '0.3', '0.4'):
        return out
    for ext, data in d.get('extensions', {}).items():
        if isinstance(data, dict) and isinstance(data.get('collections'), dict):
            for cname, coll in data['collections'].items():
                for eid, el in coll.items():
                    out.append((ext, cname, eid, el))
    return out


class Doc:
    """A read-only view of a schema-valid document with its references resolved."""

    def __init__(self, d: dict):
        self.d = d
        for c in ('buildings', 'levels', 'junctions', 'walls', 'separators', 'openings', 'rooms',
                  'slabs', 'types', 'materials', 'assets', 'roofs', 'stairs'):
            setattr(self, c, d.get(c, {}))
        self.items = d.get('program', {}).get('items', {})
        self.ext_elements = ext_elements(d)

    # 8.2 / 5.4
    def effective_layers(self, wid):
        w = self.walls[wid]
        if 'layers' in w:
            return w['layers']
        t = self.types.get(w.get('type'))
        if t is not None and 'layers' in t:
            return t['layers']
        return None

    def thickness(self, wid):
        layers = self.effective_layers(wid)
        return None if layers is None else sum(l['thickness'] for l in layers)

    def core_ok(self, wid) -> bool:
        layers = self.effective_layers(wid) or []
        idx = [i for i, l in enumerate(layers) if l['function'] == 'core']
        return bool(idx) and idx == list(range(idx[0], idx[-1] + 1))

    def offsets(self, wid):
        """Face offsets (a, b) of 5.4, as Fractions; None when the wall has no effective layers or
        an inapplicable coreFace justification."""
        layers = self.effective_layers(wid)
        if layers is None:
            return None
        t = sum(l['thickness'] for l in layers)
        j = self.walls[wid].get('justification', 'center')
        if j == 'center':
            return Fraction(t, 2), Fraction(t, 2)
        if j == 'exteriorFace':
            return Fraction(0), Fraction(t)
        if j == 'interiorFace':
            return Fraction(t), Fraction(0)
        if not self.core_ok(wid):
            return None
        first = next(i for i, l in enumerate(layers) if l['function'] == 'core')
        a = sum(l['thickness'] for l in layers[:first])
        return Fraction(a), Fraction(t - a)

    # 5.9
    def base_elevation(self, wid) -> int:
        w = self.walls[wid]
        base = w.get('base', {})
        lvl = self.levels[base.get('level', w['level'])]
        return lvl['elevation'] + base.get('offset', 0)

    def top_elevation(self, wid) -> int:
        w = self.walls[wid]
        top = w.get('top')
        if top is None:
            lvl = self.levels[w['level']]
            return lvl['elevation'] + lvl['height']
        if 'height' in top:
            return self.base_elevation(wid) + top['height']
        return self.levels[top['level']]['elevation'] + top.get('offset', 0)

    # 7.2 / 8.2
    def opening_dims(self, oid):
        """Effective (width, height, sill); width or height None when unresolved."""
        o = self.openings[oid]
        t = self.types.get(o['fill'], {}) if 'fill' in o else {}
        width = o.get('width', t.get('width'))
        height = o.get('height', t.get('height'))
        sill = o.get('sill', t.get('sill', 0))
        return width, height, sill

    # 7.2 / 8.2 (0.3): resolved whole - an opening's own replaces its type's
    def clear_opening(self, oid):
        """The effective clear opening, exactly as declared, or None."""
        o = self.openings[oid]
        if 'clearOpening' in o:
            return o['clearOpening']
        t = self.types.get(o['fill'], {}) if 'fill' in o else {}
        return t.get('clearOpening')

    def join(self, jid):
        """A junction's join; the default join at a vertex of an arc's polyline, which is no junction (21.3)."""
        return self.junctions.get(jid, {}).get('join', {'kind': 'mitre'})


# ------------------------------------------------------------------------------- the level graph

def _half(d) -> int:
    return 0 if (d[1] > 0 or (d[1] == 0 and d[0] > 0)) else 1


def _angle_cmp(u, v) -> int:
    """Order of outgoing directions by angle counter-clockwise from +X in [0, 360)."""
    hu, hv = _half(u), _half(v)
    if hu != hv:
        return hu - hv
    return -plane.sgn(plane.cross(u, v))


def rpoint(p):
    return (p[0].round(), p[1].round())


def peq(p, q) -> bool:
    return (p[0] - q[0]).is_zero() and (p[1] - q[1]).is_zero()


class Edge:
    """An edge of the level graph: a straight wall or separator, or one segment of an arc edge (21.3) - then
    `src` is the arc edge's ID, and its ends are the arc's junctions or the vertices of its polyline."""
    __slots__ = ('id', 'kind', 'start', 'end', 'a', 'b', 'src')

    def __init__(self, id, kind, start, end, a, b, src=None):
        self.id, self.kind, self.start, self.end, self.a, self.b = id, kind, start, end, a, b
        self.src = id if src is None else src

    def other(self, j):
        return self.end if j == self.start else self.start


class LevelGraph:
    """The junction graph of one level. Assumes the level passed every graph invariant."""

    def __init__(self, doc: Doc, level: str):
        self.doc = doc
        self.level = level
        self.pos = {j: tuple(v['position']) for j, v in doc.junctions.items() if v['level'] == level}
        self.junctions = list(self.pos)                 # the level's junctions; the rest of pos are arc vertices
        self.edges: dict[str, Edge] = {}
        self.chain: dict[str, list[str]] = {}           # an edge's ID -> its segments' IDs, in order (21.3)
        self.walls: list[str] = []
        for wid, w in doc.walls.items():
            if w['level'] == level:
                off = doc.offsets(wid)
                a, b = off if off is not None else (Fraction(0), Fraction(0))
                self._add(wid, 'wall', w, a, b)
                self.walls.append(wid)
        for sid, s in doc.separators.items():
            if s['level'] == level:
                self._add(sid, 'separator', s, Fraction(0), Fraction(0))
        inc: dict[str, list[str]] = {j: [] for j in self.pos}
        for e in self.edges.values():
            inc[e.start].append(e.id)
            inc[e.end].append(e.id)
        self.inc = {}
        self.idx = {}
        for j, es in inc.items():
            es = sorted(es, key=cmp_to_key(lambda x, y: _angle_cmp(self.out(j, x), self.out(j, y))))
            self.inc[j] = es
            self.idx[j] = {e: i for i, e in enumerate(es)}
        self._wedges: dict = {}
        self.cuts: dict = {}                            # (junction, segment, side) -> face vertices cut (21.4)
        self._cut_done = False
        self.endcuts: dict = {}                         # (junction, segment) -> (J-left, J-right) cuts of its face ends

    def _add(self, eid, kind, e, a, b):
        """An edge, or the segments of an arc edge whose polyline has more than one (21.3): the vertices
        between them are `<eid>^<k>` and the segments `<eid>~<k>` - names no ID can have (3.1)."""
        h = arcs.sagitta(e)
        poly = None
        if h is not None:
            S, E = self.pos.get(e['start']), self.pos.get(e['end'])
            if S is not None and E is not None and S != E and arcs.fits(S, E, h):
                poly = arcs.polyline(S, E, h)
        if poly is None or len(poly) == 2:
            self.edges[eid] = Edge(eid, kind, e['start'], e['end'], a, b)
            self.chain[eid] = [eid]
            return
        names = [e['start']] + [f'{eid}^{k}' for k in range(1, len(poly) - 1)] + [e['end']]
        for k in range(1, len(poly) - 1):
            self.pos[names[k]] = poly[k]
        self.chain[eid] = []
        for k in range(len(poly) - 1):
            sid = f'{eid}~{k + 1}'
            self.edges[sid] = Edge(sid, kind, names[k], names[k + 1], a, b, src=eid)
            self.chain[eid].append(sid)

    def at(self, j, eid):
        """The segment of edge `eid` that ends at junction j (21.3)."""
        c = self.chain[eid]
        return c[0] if self.edges[c[0]].start == j else c[-1]

    def out(self, j, eid):
        e = self.edges[eid]
        p, q = self.pos[j], self.pos[e.other(j)]
        return (q[0] - p[0], q[1] - p[1])

    def offsets_at(self, j, eid):
        """(lambda, rho): the outgoing offsets of 5.5."""
        e = self.edges[eid]
        return (e.a, e.b) if j == e.start else (e.b, e.a)

    def face_line(self, j, eid, side):
        """(A, B, C) with A*x + B*y = C: the left (side=+1) or right (side=-1) face line of eid at j."""
        dx, dy = self.out(j, eid)
        lam, rho = self.offsets_at(j, eid)
        jx, jy = self.pos[j]
        s = lam if side > 0 else -rho
        n = (-dy, dx)
        D = dx * dx + dy * dy
        return n[0], n[1], Surd(n[0] * jx + n[1] * jy) + Surd.sqrt(D, s)

    def foot(self, j, eid, side):
        dx, dy = self.out(j, eid)
        lam, rho = self.offsets_at(j, eid)
        s = lam if side > 0 else -rho
        D = dx * dx + dy * dy
        jx, jy = self.pos[j]
        # J + s * n / |d|  =  J + s * n * sqrt(D) / D
        return (Surd(jx) + Surd.sqrt(D, s * Fraction(-dy, D)), Surd(jy) + Surd.sqrt(D, s * Fraction(dx, D)))

    @staticmethod
    def intersect(l1, l2):
        a1, b1, c1 = l1
        a2, b2, c2 = l2
        det = a1 * b2 - a2 * b1
        if det == 0:
            return None
        x = (c1 * b2 - c2 * b1) / det
        y = (c2 * a1 - c1 * a2) / det
        return (x, y)

    def wedge(self, j, i):
        """The corner sequence of wedge i at junction j (5.6), exact."""
        es = self.inc[j]
        k = len(es)
        i %= k
        key = (j, i)
        if key not in self._wedges:
            ei, ej = es[i], es[(i + 1) % k]
            p, ca, cb = self.meet(j, ei, +1, ej, -1)
            if p is not None:
                seq = [p]
                self.cuts[(j, ei, +1)], self.cuts[(j, ej, -1)] = ca, cb
            else:
                f1, f2 = self.foot(j, ei, +1), self.foot(j, ej, -1)
                seq = [f1] if peq(f1, f2) else [f1, f2]
            self._wedges[key] = seq
        return self._wedges[key]

    # ---- 21.4: face paths, trimmed at junctions
    def path(self, j, eid):
        """The pieces of the face path of edge `eid` leaving junction j: [(vertex nearer j, segment)], from j
        outwards - one piece for a straight edge, every segment of an arc edge in turn (21.4)."""
        c = self.chain[self.edges[eid].src]
        if len(c) == 1:
            return [(j, eid)]
        seq = c if self.edges[c[0]].start == j else list(reversed(c))
        out, v = [], j
        for sid in seq:
            out.append((v, sid))
            v = self.edges[sid].other(v)
        return out

    def _face_vertex(self, path, k, side):
        """21.4: the rounded face vertex where piece k of a face path starts (k >= 1)."""
        v, nxt = path[k]
        i = self.idx[v][nxt]
        return rpoint(self.wedge(v, i)[0] if side > 0 else self.wedge(v, i - 1)[-1])

    def _on_piece(self, p, path, k, side) -> bool:
        """21.4: p lies on piece k of a face path - not before the rounded face vertex that starts it (the first
        piece has none) and not past the one that ends it (the last has none), along the piece's direction from
        the junction. Exact."""
        d = self.out(*path[k])
        if k > 0:
            fv = self._face_vertex(path, k, side)
            if ((p[0] - fv[0]) * d[0] + (p[1] - fv[1]) * d[1]).sign() < 0:
                return False
        if k + 1 < len(path):
            fv = self._face_vertex(path, k + 1, side)
            if ((p[0] - fv[0]) * d[0] + (p[1] - fv[1]) * d[1]).sign() > 0:
                return False
        return True

    def meet(self, j, e1, s1, e2, s2):
        """(point, a, b): where the s1 face of e1 meets the s2 face of e2 at junction j (s = +1 its J-left, -1 its
        J-right), or (None, 0, 0) when their first face lines are parallel. For an arc edge the face is its face path
        (21.4): the pieces of the first path are tried outwards from the junction and, for each, the pieces of the
        second; the corner is the first intersection that lies on both pieces, or the first pieces' intersection
        when none does. a and b are the pieces it lies on: the face vertices of e1 and e2 the join cuts off."""
        if j not in self.doc.junctions:                 # a vertex of a polyline: two segments, never trimmed
            return self.intersect(self.face_line(j, e1, s1), self.face_line(j, e2, s2)), 0, 0
        p1, p2 = self.path(j, e1), self.path(j, e2)
        first = self.intersect(self.face_line(*p1[0], s1), self.face_line(*p2[0], s2))
        if first is None:
            return None, 0, 0
        if len(p1) == 1 and len(p2) == 1:
            return first, 0, 0
        for a in range(len(p1)):
            for b in range(len(p2)):
                q = first if a == b == 0 else self.intersect(self.face_line(*p1[a], s1), self.face_line(*p2[b], s2))
                if q is not None and self._on_piece(q, p1, a, s1) and self._on_piece(q, p2, b, s2):
                    return q, a, b
        return first, 0, 0

    def all_cuts(self):
        """Every wedge at every junction computed, so that `cuts` holds every cut (21.4)."""
        if not self._cut_done:
            for j in self.junctions:
                for i in range(len(self.inc[j])):
                    self.wedge(j, i)
            self._cut_done = True
        return self.cuts

    # ---- 5.7 / 5.8 face ends
    def junction_ends(self, j, eid):
        """(end on eid's J-left face line, end on its J-right face line), exact, joins applied."""
        i = self.idx[j][eid]
        left, right = self.wedge(j, i)[0], self.wedge(j, i - 1)[-1]
        join = self.doc.join(j)
        cut = lambda e, side: self.cuts.get((j, e, side), 0)        # noqa: E731
        if join.get('kind') != 'butt':
            self.endcuts[(j, eid)] = (cut(eid, +1), cut(eid, -1))
            return left, right
        through = [self.at(j, w) for w in join['through']]         # an arc wall's segment at j (21.3)
        es = self.inc[j]
        if len(through) == 1:
            a_id = through[0]
            d0, d1 = self.out(j, es[0]), self.out(j, es[1])
            cw = 0 if plane.cross(d0, d1) > 0 else 1          # the convex wedge
            c, r = self.wedge(j, cw)[0], self.wedge(j, 1 - cw)[0]
            a = self.idx[j][a_id]
            b = 1 - a
            b_id = es[b]
            a_convex_side = +1 if a == cw else -1                # J-left of A bounds wedge a
            b_reflex_side = +1 if b != cw else -1                # J-left of B bounds wedge b
            p, pa, pb = self.meet(j, a_id, a_convex_side, b_id, b_reflex_side)
            if eid == a_id:
                ends = {a_convex_side: p, -a_convex_side: r}
                cuts = {a_convex_side: pa, -a_convex_side: cut(a_id, -a_convex_side)}
            else:
                ends = {-b_reflex_side: c, b_reflex_side: p}
                cuts = {-b_reflex_side: cut(b_id, -b_reflex_side), b_reflex_side: pb}
            self.endcuts[(j, eid)] = (cuts[+1], cuts[-1])
            return ends[+1], ends[-1]
        if eid in through:
            self.endcuts[(j, eid)] = (0, 0)
            return self.foot(j, eid, +1), self.foot(j, eid, -1)
        self.endcuts[(j, eid)] = (cut(eid, +1), cut(eid, -1))
        return left, right

    def face_ends(self, wid):
        """{'startRight', 'endRight', 'endLeft', 'startLeft'}: exact points. An arc wall's are those of its
        first and last segments (21.4)."""
        c = self.chain[wid]
        first, last = self.edges[c[0]], self.edges[c[-1]]
        sl, sr = self.junction_ends(first.start, first.id)
        er, el = self.junction_ends(last.end, last.id)  # at the end the wall's own sides are reversed
        return {'startRight': sr, 'endRight': er, 'endLeft': el, 'startLeft': sl}

    def face_vertices(self, wid):
        """21.4: the exact (left, right) face vertices of an arc wall, from its start to its end - at each
        vertex of its polyline, the corners of the two wedges between its segments there."""
        c = self.chain[wid]
        left, right = [], []
        for sid in c[1:]:
            lv, rv = self.junction_ends(self.edges[sid].start, sid)
            left.append(lv)
            right.append(rv)
        if len(c) == 1:
            return left, right
        first, last = self.edges[c[0]], self.edges[c[-1]]
        self.junction_ends(first.start, first.id)
        self.junction_ends(last.end, last.id)
        ls, rs = self.endcuts[(first.start, first.id)]
        le, re_ = self.endcuts[(last.end, last.id)]             # at the end, J-left is the wall's right
        n = len(left)
        return left[ls:max(ls, n - re_)], right[rs:max(rs, n - le)]

    def outline(self, wid):
        f = {k: rpoint(v) for k, v in self.face_ends(wid).items()}
        left, right = self.face_vertices(wid)
        return plane.dedupe_cyclic([f['startRight']] + [rpoint(p) for p in right] + [f['endRight'], f['endLeft']]
                                   + [rpoint(p) for p in reversed(left)] + [f['startLeft']])

    def fill(self, j):
        """The junction fill ring (rounded, deduplicated), or None when not derived (5.7)."""
        if len(self.inc[j]) < 3 or j not in self.doc.junctions or self.doc.join(j).get('kind') != 'mitre':
            return None
        pts = []
        for i in range(len(self.inc[j])):
            pts.extend(rpoint(p) for p in self.wedge(j, i))
        return plane.dedupe_cyclic(pts)

    # ---- 6.1 faces
    def walks(self):
        """Every boundary walk: lists of half-edges (eid, from, to)."""
        seen = set()
        walks = []
        for e in self.edges.values():
            for h in ((e.id, e.start, e.end), (e.id, e.end, e.start)):
                if h in seen:
                    continue
                walk = []
                while h not in seen:
                    seen.add(h)
                    walk.append(h)
                    eid, u, v = h
                    m = self.idx[v][eid]
                    k = len(self.inc[v])
                    nxt = self.inc[v][(m - 1) % k]
                    h = (nxt, v, self.edges[nxt].other(v))
                walks.append(walk)
        return walks

    def walk_positions(self, walk):
        return [self.pos[u] for _, u, _ in walk]

    def ring(self, walk):
        """The ring of a walk (6.2), rounded and deduplicated, in walk order."""
        pts = []
        n = len(walk)
        for i in range(n):
            eid, _, v = walk[i]
            if self.cut_off(eid, v):
                continue
            m = self.idx[v][eid]
            seq = self.wedge(v, m - 1)
            pts.extend(rpoint(p) for p in reversed(seq))
        return plane.dedupe_cyclic(pts)

    def cut_off(self, eid, v) -> bool:
        """21.4: arriving along segment eid at a vertex v of its arc's polyline, the face on the walk's left - the
        arc's left face when the walk runs the arc's way - turns at a face vertex that the join at a junction
        cuts off."""
        e = self.edges[eid]
        if v in self.doc.junctions or e.src == e.id:
            return False
        c = self.chain[e.src]
        k = int(v.rsplit('^', 1)[1])
        cuts = self.all_cuts()
        first, last = self.edges[c[0]], self.edges[c[-1]]
        side = +1 if e.end == v else -1                     # the arc's left (+1) or right (-1)
        at_start = cuts.get((first.start, first.id, side), 0)
        at_end = cuts.get((last.end, last.id, -side), 0)
        return k <= at_start or k >= len(c) - at_end

    def faces(self):
        """Bounded faces: list of dicts {outer: walk, holes: [walk], area2: walk area}."""
        walks = self.walks()
        # connected components of junctions that have edges
        parent = {j: j for j in self.pos}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for e in self.edges.values():
            parent[find(e.start)] = find(e.end)
        info = []
        for w in walks:
            pos = self.walk_positions(w)
            info.append({'walk': w, 'pos': pos, 'area2': plane.area2(pos), 'comp': find(w[0][1])})
        faces = [{'outer': x['walk'], 'pos': x['pos'], 'area2': x['area2'], 'comp': x['comp'], 'holes': []}
                 for x in info if x['area2'] > 0]
        outers = [x for x in info if x['area2'] <= 0]
        comps = {}
        for x in outers:
            assert x['comp'] not in comps, 'a component with two non-positive walks'
            comps[x['comp']] = x
        for comp, x in comps.items():
            pt = x['pos'][0]
            best = None
            for f in faces:
                if f['comp'] == comp:
                    continue
                if plane.winding(pt, f['pos']) != 0 and (best is None or f['area2'] < best['area2']):
                    best = f
            if best is not None:
                best['holes'].append(x['walk'])
        return faces

    def face_of(self, point, faces):
        """The bounded face containing a point not on any location line, or None."""
        best = None
        for f in faces:
            if plane.winding(point, f['pos']) != 0 and (best is None or f['area2'] < best['area2']):
                best = f
        return best

    def on_location_line(self, point) -> bool:
        return any(plane.on_closed_segment(point, self.pos[e.start], self.pos[e.end]) for e in self.edges.values())

    def room_polygon(self, face):
        outer = self.ring(face['outer'])
        holes = [self.ring(h) for h in face['holes']]
        return outer, holes


def degenerate(outer, holes) -> bool:
    """6.2: a degenerate room polygon."""
    if not plane.is_simple(outer) or plane.area2(outer) <= 0:
        return True
    for h in holes:
        if not plane.is_simple(h) or plane.area2(h) >= 0:
            return True
        if plane.rings_touch(h, outer) or plane.locate(h[0], outer) != 'in':
            return True
    for i in range(len(holes)):
        for k in range(i + 1, len(holes)):
            a, b = holes[i], holes[k]
            if plane.rings_touch(a, b) or plane.locate(a[0], b) != 'out' or plane.locate(b[0], a) != 'out':
                return True
    return False


def strictly_inside(point, outer, holes) -> bool:
    """6.3.4: inside the outer ring, and outside and off every hole ring."""
    return plane.locate(point, outer) == 'in' and all(plane.locate(point, h) == 'out' for h in holes)


def polygon_value(outer, holes):
    outer = plane.least_first(outer)
    holes = sorted((plane.least_first(h) for h in holes), key=lambda r: r[0])
    a2 = plane.area2(outer) + sum(plane.area2(h) for h in holes)
    return {'outer': [list(p) for p in outer], 'holes': [[list(p) for p in h] for h in holes],
            'area': plane.area_string(a2)}


# ---------------------------------------------------------------------------------- openings 7.4

def opening_points(doc: Doc, oid):
    o = doc.openings[oid]
    poly = arcs.wall_arc(doc, o['wall'])
    if poly is not None:                                    # 21.6: at distances along an arc wall's polyline
        width, _, _ = doc.opening_dims(oid)
        return tuple(tuple(Surd(c) for c in arcs.point_at(poly, t)) for t in (o['offset'], o['offset'] + width))
    w = doc.walls[o['wall']]
    s = doc.junctions[w['start']]['position']
    e = doc.junctions[w['end']]['position']
    dx, dy = e[0] - s[0], e[1] - s[1]
    D = dx * dx + dy * dy
    width, height, sill = doc.opening_dims(oid)

    def at(dist):
        return (Surd(s[0]) + Surd.sqrt(D, Fraction(dx * dist, D)), Surd(s[1]) + Surd.sqrt(D, Fraction(dy * dist, D)))
    return at(o['offset']), at(o['offset'] + width)


# ------------------------------------------------------------------------------- whole document

def derive(doc: Doc) -> dict:
    """The `derived` object of a valid document (conformance/README.md)."""
    walls, fills, rooms, unanchored, openings = {}, {}, {}, [], {}
    for level in sorted(doc.levels):
        g = LevelGraph(doc, level)
        for wid in g.walls:
            f = g.face_ends(wid)
            walls[wid] = {k: list(rpoint(f[k])) for k in ('startRight', 'endRight', 'endLeft', 'startLeft')}
            walls[wid]['baseElevation'] = doc.base_elevation(wid)
            walls[wid]['topElevation'] = doc.top_elevation(wid)
            poly = arcs.wall_arc(doc, wid)
            if poly is not None:                            # 21.4, 21.5: an arc wall's polyline, length and faces
                left, right = g.face_vertices(wid)
                walls[wid].update({'polyline': [list(p) for p in poly], 'length': arcs.length(poly),
                                   'left': [list(rpoint(p)) for p in left], 'right': [list(rpoint(p)) for p in right]})
        for j in g.junctions:
            ring = g.fill(j)
            if ring is not None and len(ring) >= 3 and plane.area2(ring) != 0:
                fills[j] = [list(p) for p in plane.least_first(ring)]
        faces = g.faces()
        anchored = {}
        for rid, r in doc.rooms.items():
            if r['level'] == level:
                f = g.face_of(tuple(r['anchor']), faces)
                anchored[id(f)] = rid
                outer, holes = g.room_polygon(f)
                rooms[rid] = polygon_value(outer, holes)
        for f in faces:
            if id(f) in anchored:
                continue
            outer, holes = g.room_polygon(f)
            if not degenerate(outer, holes):
                unanchored.append({'level': level, **polygon_value(outer, holes)})
    unanchored.sort(key=lambda u: (u['level'], tuple(u['outer'][0])))
    for oid, o in doc.openings.items():
        width, height, sill = doc.opening_dims(oid)
        s, e = opening_points(doc, oid)
        sill_el = doc.base_elevation(o['wall']) + sill
        openings[oid] = {'start': list(rpoint(s)), 'end': list(rpoint(e)),
                         'sillElevation': sill_el, 'headElevation': sill_el + height}
        clear = doc.clear_opening(oid)                                      # 7.4.2 (0.3): as declared
        if clear is not None:
            openings[oid]['clearOpening'] = {k: clear[k] for k in ('width', 'height', 'area') if k in clear}
    return {'walls': walls, 'junctionFills': fills, 'rooms': rooms, 'unanchored': unanchored,
            'openings': openings}

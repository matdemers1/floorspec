"""The transaction (Ops 1.2): check A, then for each operation resolve and expand it and apply its
primitives, then normalize, validate and check the locks; and the result (1.3) - the resolved
echo (1.4), created and removed, and the inverse (1.6).

``apply(a_bytes, request) -> (result, b_bytes | None)``.

Where an earlier draft left a choice, Ops 0.1 now settles it, and this module follows the text:
the order of checks (1.2, 7.1), the order of resolution within an operation (1.2 step 2), what a
shorthand resolves (2.1.2, 2.5), what $document addresses (2.3), minting (1.5), the order of the
inverse - property differences first (1.6) - and one diagnostic per failing opening or lock
(7.1.2).
"""

from __future__ import annotations

import copy
import json
import re
from fractions import Fraction

from .. import canon, plane
from ..jsonparse import Malformed, parse
from ..surd import Surd
from ..validate import check as core_check
from .errors import OpsError, Rejected, esc
from .faces import LevelFaces, coll, is_point
from .normalize import OpsStraddle, effective_width, normalize
from .refs import DIRECTIONS, half, length
from .request import COLLECTIONS, check_request
from .select import Resolver, outward_normal

PREFIX = {'buildings': 'B', 'levels': 'L', 'junctions': 'J', 'walls': 'W', 'separators': 'S',
          'openings': 'O', 'rooms': 'R', 'slabs': 'SL', 'types': 'T', 'materials': 'M', 'assets': 'A'}
DOC_MEMBERS = ('floorspec', 'project', 'site', 'extensionsUsed', 'extensionsRequired', 'extensions', 'extras')
INVERSE_ORDER = ('openings', 'rooms', 'slabs', 'separators', 'walls', 'junctions', 'levels', 'buildings',
                 'types', 'materials', 'assets')
WALL_MEMBERS = ('type', 'layers', 'justification', 'base', 'top')
COMMON = ('name', 'extensions', 'extras')     # Core 1.4: what every element may carry


def isd(v) -> bool:
    return isinstance(v, dict)


def all_ids(doc: dict) -> set:
    return {eid for c in COLLECTIONS for eid in coll(doc, c)}


def same(a, b) -> bool:
    """Equal JSON values, as RFC 8785 serializes them."""
    return canon.jcs(a) == canon.jcs(b)


def parse_pointer(path: str):
    """RFC 6901 reference tokens, or None for a path that is not a JSON Pointer."""
    if not path.startswith('/'):
        return None
    tokens = []
    for raw in path[1:].split('/'):
        if re.search(r'~(?![01])', raw):
            return None
        tokens.append(raw.replace('~1', '/').replace('~0', '~'))
    return tokens


def _index(tok: str, n: int):
    if re.fullmatch(r'0|[1-9][0-9]*', tok) and int(tok) < n:
        return int(tok)
    return None


class Transaction:
    def __init__(self, a: dict, context: dict):
        self.a = a
        self.wc = copy.deepcopy(a)
        self.in_a_junctions = set(coll(a, 'junctions'))
        self.a_ids = all_ids(a)
        self.used: set[str] = set()                 # every ID named or minted in this batch
        self.retired = set(context.get('retired', []))
        self.locks = context.get('locks', [])
        self.minted: set[str] = set()
        self.resolved: list[dict] = []

    # ------------------------------------------------------------------ 1.5 minting
    def mint(self, prefix: str) -> str:
        """One more than the largest n among the IDs in A, every ID named or minted earlier in the
        batch (removed again or not), and context.retired."""
        pat = re.compile(re.escape(prefix) + r'([0-9]+)')
        top = 0
        for eid in self.a_ids | all_ids(self.wc) | self.used | self.minted | self.retired:
            m = pat.fullmatch(eid)
            if m:
                top = max(top, int(m[1]))
        new = f'{prefix}{top + 1}'
        self.minted.add(new)
        return new

    def new_id(self, op, prefix):
        return op['id'] if 'id' in op else self.mint(prefix)

    # ------------------------------------------------------------------ steps 2-4
    def run(self, batch):
        for n, op in enumerate(batch):
            prims = getattr(self, 'x_' + op['op'])(Resolver(self.wc), op, f'/batch/{n}')
            for p in prims:
                self.apply(p, f'/batch/{n}')
                self.resolved.append(p)

    # ------------------------------------------------------------------ chapter 2: primitives
    def apply(self, p: dict, ptr: str) -> None:
        op = p['op']
        if op == 'addElement':
            self.add(p['collection'], p['id'], p['element'], ptr)
        elif op in ('addJunction', 'addWall', 'addSeparator'):
            c = {'addJunction': 'junctions', 'addWall': 'walls', 'addSeparator': 'separators'}[op]
            self.add(c, p['id'], {k: v for k, v in p.items() if k not in ('op', 'id')}, ptr)
        elif op == 'removeElement':
            self.remove(p['id'], p.get('cascade', False), ptr)
        elif op == 'setProperty':
            self.set(p['id'], p['path'], p['value'], ptr)
        elif op == 'unsetProperty':
            self.unset(p['id'], p['path'], ptr)
        elif op == 'moveJunction':
            self.set(p['id'], '/position', p['to'], ptr)
        else:
            raise AssertionError(op)

    def add(self, c: str, eid: str, element: dict, ptr: str) -> None:
        if eid in all_ids(self.wc) or eid in self.retired:
            raise OpsError('FS-OPS-005', [], ptr, f'{eid} is already used or retired')
        self.used.add(eid)
        self.wc.setdefault(c, {})[eid] = copy.deepcopy(element)

    def collection_of(self, eid):
        for c in COLLECTIONS:
            if eid in coll(self.wc, c):
                return c
        return None

    def dependents(self, c: str, eid: str) -> list[str]:
        """What blocks removing an element without cascade (2.2)."""
        wc, out = self.wc, []

        def where(cc, test):
            out.extend(x for x, e in coll(wc, cc).items() if isd(e) and test(e))
        if c == 'buildings':
            where('levels', lambda e: e.get('building') == eid)
        elif c == 'levels':
            for cc in ('junctions', 'walls', 'separators', 'rooms', 'slabs'):
                where(cc, lambda e: e.get('level') == eid)
            where('walls', lambda e: (isd(e.get('base')) and e['base'].get('level') == eid)
                  or (isd(e.get('top')) and e['top'].get('level') == eid))
        elif c == 'junctions':
            for cc in ('walls', 'separators'):
                where(cc, lambda e: eid in (e.get('start'), e.get('end')))
        elif c == 'walls':
            where('openings', lambda e: e.get('wall') == eid)
        elif c == 'types':
            where('walls', lambda e: e.get('type') == eid)
            where('openings', lambda e: e.get('fill') == eid)
        elif c == 'materials':
            def layered(e):
                return isinstance(e.get('layers'), list) and any(isd(l) and l.get('material') == eid for l in e['layers'])
            where('types', layered)
            where('walls', layered)
            where('rooms', lambda e: eid in (e.get('wallFinish'), e.get('floorFinish'), e.get('ceilingFinish')))
            where('slabs', lambda e: e.get('material') == eid)
        elif c == 'assets':
            where('materials', lambda e: isd(e.get('texture')) and e['texture'].get('asset') == eid)
        return sorted(set(out) - {eid})

    def takes(self, c: str, eid: str):
        """What removing an element takes with it, when cascade is true (2.2)."""
        wc, out = self.wc, []

        def where(cc, test):
            out.extend((cc, x) for x, e in coll(wc, cc).items() if isd(e) and test(e))
        if c == 'buildings':
            where('levels', lambda e: e.get('building') == eid)
        elif c == 'levels':
            for cc in ('junctions', 'walls', 'separators', 'rooms', 'slabs'):
                where(cc, lambda e: e.get('level') == eid)
        elif c == 'junctions':
            for cc in ('walls', 'separators'):
                where(cc, lambda e: eid in (e.get('start'), e.get('end')))
        elif c == 'walls':
            where('openings', lambda e: e.get('wall') == eid)
        return out

    def remove(self, eid: str, cascade: bool, ptr: str) -> None:
        c = self.collection_of(eid)
        if c is None:
            raise OpsError('FS-OPS-003', [], ptr, f'{eid} does not exist')
        if not cascade or c in ('types', 'materials', 'assets'):
            deps = self.dependents(c, eid)
            if deps:
                raise OpsError('FS-OPS-006', [eid] + deps, ptr, f'{eid} is used by {", ".join(deps)}')
            gone = [(c, eid)]
        else:
            gone, todo = [], [(c, eid)]
            while todo:
                x = todo.pop()
                if x in gone:
                    continue
                gone.append(x)
                todo.extend(self.takes(*x))
        for cc, x in gone:
            del self.wc[cc][x]
        removed_walls = {x for cc, x in gone if cc == 'walls'}
        for j in coll(self.wc, 'junctions').values():
            join = j.get('join') if isd(j) else None
            if isd(join) and isinstance(join.get('through'), list) and removed_walls & {w for w in join['through'] if isinstance(w, str)}:
                del j['join']

    def _target(self, eid: str, tokens, create: bool, ptr: str):
        """The object a pointer's first token is looked up in, and the elements an FS-OPS-003
        about it names."""
        if eid == '$project':
            t = self.wc.get('project')
            return t, []
        if eid == '$site':
            if 'site' not in self.wc and create:
                self.wc['site'] = {}
            return self.wc.get('site'), []
        if eid == '$document':
            if tokens and tokens[0] not in DOC_MEMBERS:
                raise OpsError('FS-OPS-003', [], f'{ptr}/path', f'$document has no member "{tokens[0]}"')
            return self.wc, []
        c = self.collection_of(eid)
        if c is None:
            raise OpsError('FS-OPS-003', [], f'{ptr}/id', f'{eid} does not exist')
        return self.wc[c][eid], [eid]

    def set(self, eid, path, value, ptr):
        if eid not in ('$project', '$site', '$document') and self.collection_of(eid) is None:
            raise OpsError('FS-OPS-003', [], f'{ptr}/id', f'{eid} does not exist')
        els = [eid] if not eid.startswith('$') else []
        tokens = parse_pointer(path)
        if not tokens:
            raise OpsError('FS-OPS-003', els, f'{ptr}/path', 'the path is empty' if path == '' else 'not a JSON Pointer')
        cur, els = self._target(eid, tokens, True, ptr)
        for tok in tokens[:-1]:
            if isd(cur):
                if tok not in cur:
                    cur[tok] = {}
                cur = cur[tok]
            elif isinstance(cur, list) and _index(tok, len(cur)) is not None:
                cur = cur[_index(tok, len(cur))]
            else:
                raise OpsError('FS-OPS-003', els, f'{ptr}/path', f'{path} does not lead to a member')
        last = tokens[-1]
        if isd(cur):
            cur[last] = copy.deepcopy(value)
        elif isinstance(cur, list) and _index(last, len(cur)) is not None:
            cur[_index(last, len(cur))] = copy.deepcopy(value)
        else:
            raise OpsError('FS-OPS-003', els, f'{ptr}/path', f'{path} does not lead to a member')

    def unset(self, eid, path, ptr):
        if eid not in ('$project', '$site', '$document') and self.collection_of(eid) is None:
            raise OpsError('FS-OPS-003', [], f'{ptr}/id', f'{eid} does not exist')
        els = [eid] if not eid.startswith('$') else []
        tokens = parse_pointer(path)
        if not tokens:
            raise OpsError('FS-OPS-003', els, f'{ptr}/path', 'the path is empty' if path == '' else 'not a JSON Pointer')
        cur, els = self._target(eid, tokens, False, ptr)
        for tok in tokens[:-1]:
            if isd(cur) and tok in cur:
                cur = cur[tok]
            elif isinstance(cur, list) and _index(tok, len(cur)) is not None:
                cur = cur[_index(tok, len(cur))]
            else:
                cur = None
                break
        last = tokens[-1]
        if isd(cur) and last in cur:
            del cur[last]
        elif isinstance(cur, list) and _index(last, len(cur)) is not None:
            del cur[_index(last, len(cur))]
        else:
            raise OpsError('FS-OPS-003', els, f'{ptr}/path', f'{path} is not there')

    # ------------------------------------------------------------------ primitives, resolved (2.5)
    def x_addElement(self, R, op, P):
        eid = self.new_id(op, PREFIX[op['collection']])
        return [{'op': 'addElement', 'collection': op['collection'], 'id': eid, 'element': copy.deepcopy(op['element'])}]

    def x_addJunction(self, R, op, P):
        level = R.element(op['level'], ('levels',), f'{P}/level')[1]
        x, y = R.point(op['position'], f'{P}/position')
        p = {'op': 'addJunction', 'id': self.new_id(op, 'J'), 'level': level, 'position': [x, y]}
        p.update({k: copy.deepcopy(op[k]) for k in ('join', 'name', 'extensions', 'extras') if k in op})
        return [p]

    def _edge(self, R, op, P, name, prefix):
        level = R.element(op['level'], ('levels',), f'{P}/level')[1]
        start = R.junction(op['start'], f'{P}/start')
        end = R.junction(op['end'], f'{P}/end')
        p = {'op': name, 'id': self.new_id(op, prefix), 'level': level, 'start': start, 'end': end}
        p.update({k: copy.deepcopy(v) for k, v in op.items() if k not in ('op', 'id', 'level', 'start', 'end')})
        return [p]

    def x_addWall(self, R, op, P):
        return self._edge(R, op, P, 'addWall', 'W')

    def x_addSeparator(self, R, op, P):
        return self._edge(R, op, P, 'addSeparator', 'S')

    def x_removeElement(self, R, op, P):
        p = {'op': 'removeElement', 'id': R.element(op['id'], None, f'{P}/id')[1]}
        if 'cascade' in op:
            p['cascade'] = op['cascade']
        return [p]

    def x_setProperty(self, R, op, P):
        return [{'op': 'setProperty', 'id': R.target(op['id'], f'{P}/id')[1], 'path': op['path'],
                 'value': copy.deepcopy(op['value'])}]

    def x_unsetProperty(self, R, op, P):
        return [{'op': 'unsetProperty', 'id': R.target(op['id'], f'{P}/id')[1], 'path': op['path']}]

    def x_moveJunction(self, R, op, P):
        jid = R.junction(op['id'], f'{P}/id')
        x, y = R.point(op['to'], f'{P}/to')
        return [{'op': 'moveJunction', 'id': jid, 'to': [x, y]}]

    # ------------------------------------------------------------------ chapter 4: composites
    def _draw(self, R, op, P, name, prefix, members):
        level = R.element(op['level'], ('levels',), f'{P}/level')[1]
        ends = [R.point_or_junction(op[k], f'{P}/{k}') for k in ('from', 'to')]
        at = {}
        for jid, j in sorted(coll(self.wc, 'junctions').items(), reverse=True):
            if isd(j) and j.get('level') == level and is_point(j.get('position')):
                at[tuple(j['position'])] = jid            # the least ID wins a shared position
        prims, ids = [], []
        for kind, x in ends:
            if kind == 'junction':
                ids.append(x)
            elif x in at:
                ids.append(at[x])
            else:
                jid = self.mint('J')
                prims.append({'op': 'addJunction', 'id': jid, 'level': level, 'position': [x[0], x[1]]})
                ids.append(jid)
        p = {'op': name, 'id': self.new_id(op, prefix), 'level': level, 'start': ids[0], 'end': ids[1]}
        p.update({k: copy.deepcopy(op[k]) for k in members if k in op})
        return prims + [p]

    def x_drawWall(self, R, op, P):
        return self._draw(R, op, P, 'addWall', 'W', WALL_MEMBERS + COMMON)

    def x_drawSeparator(self, R, op, P):
        return self._draw(R, op, P, 'addSeparator', 'S', COMMON)

    def x_moveWall(self, R, op, P):
        wid = R.element(op['wall'], ('walls',), f'{P}/wall')[1]
        by = length(op['by'], f'{P}/by')
        s, t, S, E = R.wall_line('walls', wid, f'{P}/wall')
        if 'toward' in op:
            rid = R.room(op['toward'], f'{P}/toward')
            lf, f = R.room_face(rid, f'{P}/toward')
            left, right = lf.he_face.get((wid, s, t), 'none'), lf.he_face.get((wid, t, s), 'none')
            if f == left and f != right:
                by = abs(by)
            elif f == right and f != left:
                by = -abs(by)
            else:
                raise OpsError('FS-OPS-008', [wid], f'{P}/toward', f'{rid} is not on one side of {wid}')
        dx, dy = E[0] - S[0], E[1] - S[1]
        D = dx * dx + dy * dy
        if D == 0:
            raise OpsError('FS-OPS-008', [wid], f'{P}/wall', f'{wid} has no direction')
        mx = Surd.sqrt(D, Fraction(-by * dy, D)).round()
        my = Surd.sqrt(D, Fraction(by * dx, D)).round()
        return [{'op': 'moveJunction', 'id': s, 'to': [S[0] + mx, S[1] + my]},
                {'op': 'moveJunction', 'id': t, 'to': [E[0] + mx, E[1] + my]}]

    def x_moveRoom(self, R, op, P):
        rid = R.room(op['room'], f'{P}/room')
        vx, vy = R.vector(op['by'], f'{P}/by')
        lf, f = R.room_face(rid, f'{P}/room')
        prims = []
        for jid in sorted({u for _, u, _ in lf.faces[f]['outer']}):
            x, y = lf.pos[jid]
            prims.append({'op': 'moveJunction', 'id': jid, 'to': [x + vx, y + vy]})
        ax, ay = self.wc['rooms'][rid]['anchor']
        prims.append({'op': 'setProperty', 'id': rid, 'path': '/anchor', 'value': [ax + vx, ay + vy]})
        return prims

    def x_resizeRoom(self, R, op, P):
        rid = R.room(op['room'], f'{P}/room')
        by = length(op['by'], f'{P}/by')
        ux, uy = DIRECTIONS[op['side']]
        v = (by * ux, by * uy)
        lf, f = R.room_face(rid, f'{P}/room')
        walk = lf.faces[f]['outer']
        k = len(walk)

        def faces_u(h):
            nx, ny = outward_normal(lf.pos, h)
            return nx * uy - ny * ux == 0 and nx * ux + ny * uy > 0
        flags = [faces_u(h) for h in walk]
        firsts = [i for i in range(k) if flags[i] and not flags[i - 1]]
        if not any(flags):
            raise OpsError('FS-OPS-008', [rid], f'{P}/side', f'{rid} has no {op["side"]} side made of edges facing {op["side"]}')
        if len(firsts) != 1:
            raise OpsError('FS-OPS-008', [rid], f'{P}/side', f'the {op["side"]} side of {rid} is jogged')
        run, i = [], firsts[0]
        while flags[i % k] and len(run) < k:
            run.append(walk[i % k])
            i += 1
        P_ = [run[0][1]] + [h[2] for h in run]
        if len({plane.dot(lf.pos[j], (ux, uy)) for j in P_}) != 1:
            raise OpsError('FS-OPS-008', [rid], f'{P}/side', f'the {op["side"]} side of {rid} is jogged')
        a, b = lf.pos[run[0][1]], lf.pos[run[0][2]]
        d = (b[0] - a[0], b[1] - a[1])

        def continues(j, direction):
            for _, other in lf.incident(j):
                o = plane.sub(lf.pos[other], lf.pos[j])
                if plane.cross(o, direction) == 0 and plane.dot(o, direction) > 0:
                    return True
            return False
        def stem(j):
            """The edge that leaves j exactly in the direction of v, as its squared length."""
            for _, other in lf.incident(j):
                o = plane.sub(lf.pos[other], lf.pos[j])
                if v != (0, 0) and plane.cross(o, v) == 0 and plane.dot(o, v) > 0:
                    return plane.dot(o, o)
            return None
        level = self.wc['rooms'][rid]['level']
        prims, fixed = [], set()
        for end, h, away in ((P_[0], run[0], (-d[0], -d[1])), (P_[-1], run[-1], d)):
            if not continues(end, away):
                continue
            fixed.add(end)
            along = stem(end)
            if along is not None and along <= by * by:
                raise OpsError('FS-OPS-008', [rid], f'{P}/by',
                               f'the edge at {end} in the direction of the move is not longer than it')
            ex, ey = lf.pos[end]
            nj = self.mint('J')
            prims.append({'op': 'addJunction', 'id': nj, 'level': level, 'position': [ex + v[0], ey + v[1]]})
            eid = h[0]
            c = lf.edges[eid][0]
            edge = self.wc[c][eid]
            member = '/start' if edge['start'] == end else '/end'
            prims.append({'op': 'setProperty', 'id': eid, 'path': member, 'value': nj})
            if along is not None:
                continue                        # normalization splits that edge: its first piece is the jog
            if c == 'walls':
                jog = {'op': 'addWall', 'id': self.mint('W'), 'level': level, 'start': end, 'end': nj}
                jog.update({m: copy.deepcopy(edge[m]) for m in ('type', 'layers', 'justification') if m in edge})
            else:
                jog = {'op': 'addSeparator', 'id': self.mint('S'), 'level': level, 'start': end, 'end': nj}
            prims.append(jog)
        for j in sorted(set(P_) - fixed):
            x, y = lf.pos[j]
            prims.append({'op': 'moveJunction', 'id': j, 'to': [x + v[0], y + v[1]]})
        hx, hy = half(v[0]), half(v[1])
        across = set()
        for eid, s, t in run:
            across.update(lf.rooms_in(self.wc, lf.he_face.get((eid, t, s))))
        for r in [rid] + sorted(across - {rid}):
            ax, ay = self.wc['rooms'][r]['anchor']
            prims.append({'op': 'setProperty', 'id': r, 'path': '/anchor', 'value': [ax + hx, ay + hy]})
        return prims

    def x_addOpening(self, R, op, P):
        wid = R.element(op['wall'], ('walls',), f'{P}/wall')[1]
        dims = {k: length(op[k], f'{P}/{k}') for k in ('width', 'height', 'sill') if k in op}
        w = dims.get('width')
        if w is None:
            t = coll(self.wc, 'types').get(op['fill']) if 'fill' in op else None
            if not (isd(t) and type(t.get('width')) is int):
                raise OpsError('FS-OPS-003', [], f'{P}/fill' if 'fill' in op else P,
                               'the opening has no width and its fill gives none')
            w = t['width']
        _, _, S, E = R.wall_line('walls', wid, f'{P}/wall')
        D = (E[0] - S[0]) ** 2 + (E[1] - S[1]) ** 2
        offset = R.position(op['at'], D, w, f'{P}/at')
        element = {'wall': wid, 'offset': offset, **dims}
        element.update({k: copy.deepcopy(op[k]) for k in ('fill', 'hinge', 'swing') + COMMON if k in op})
        return [{'op': 'addElement', 'collection': 'openings', 'id': self.new_id(op, 'O'), 'element': element}]

    def x_moveOpening(self, R, op, P):
        oid = R.element(op['opening'], ('openings',), f'{P}/opening')[1]
        o = self.wc['openings'][oid]
        if not (isd(o) and isinstance(o.get('wall'), str) and o['wall'] in coll(self.wc, 'walls')):
            raise OpsError('FS-OPS-003', [oid], f'{P}/opening', f'{oid} is on no wall')
        if 'at' in op:                                              # absolute (4.5.1)
            w = effective_width(self.wc, o)
            if w is None:
                raise OpsError('FS-OPS-003', [oid], f'{P}/opening', f'the width of {oid} does not resolve')
            _, _, S, E = R.wall_line('walls', o['wall'], f'{P}/opening')
            D = (E[0] - S[0]) ** 2 + (E[1] - S[1]) ** 2
            offset = R.position(op['at'], D, w, f'{P}/at')
            return [{'op': 'setProperty', 'id': oid, 'path': '/offset', 'value': offset}]
        if type(o.get('offset')) is not int:                        # relative (4.5.2)
            raise OpsError('FS-OPS-003', [oid], f'{P}/opening', f'{oid} has no integer offset')
        by = length(op['by'], f'{P}/by')
        toward = op.get('toward')
        if toward == 'end':
            by = abs(by)
        elif toward == 'start':
            by = -abs(by)
        elif toward is not None:
            _, _, S, E = R.wall_line('walls', o['wall'], f'{P}/opening')
            ux, uy = DIRECTIONS[toward]
            dot = (E[0] - S[0]) * ux + (E[1] - S[1]) * uy
            if dot == 0:
                raise OpsError('FS-OPS-008', [o['wall']], f'{P}/toward',
                               f'{o["wall"]} is perpendicular to {toward}: {oid} cannot move along it that way')
            by = abs(by) if dot > 0 else -abs(by)
        return [{'op': 'setProperty', 'id': oid, 'path': '/offset', 'value': o['offset'] + by}]

    def x_addRoom(self, R, op, P):
        level = R.element(op['level'], ('levels',), f'{P}/level')[1]
        x, y = R.point(op['at'], f'{P}/at')
        element = {'level': level, 'anchor': [x, y]}
        element.update({k: copy.deepcopy(op[k]) for k in ('function', 'wallFinish', 'floorFinish', 'ceilingFinish') + COMMON if k in op})
        return [{'op': 'addElement', 'collection': 'rooms', 'id': self.new_id(op, 'R'), 'element': element}]

    def x_setRoomFinish(self, R, op, P):
        rid = R.room(op['room'], f'{P}/room')
        return [{'op': 'setProperty', 'id': rid, 'path': f'/{op["surface"]}Finish', 'value': op['material']}]

    def x_removeWall(self, R, op, P):
        wid = R.element(op['wall'], ('walls',), f'{P}/wall')[1]
        keep = R.room(op['keep'], f'{P}/keep') if 'keep' in op else None
        w = self.wc['walls'][wid]
        lf = R.level_faces(w.get('level'), f'{P}/wall')
        s, t = w['start'], w['end']
        left = lf.rooms_in(self.wc, lf.he_face.get((wid, s, t)))
        right = lf.rooms_in(self.wc, lf.he_face.get((wid, t, s)))
        prims = []
        if len(left) == 1 and len(right) == 1 and left != right:
            if keep not in (left[0], right[0]):
                raise OpsError('FS-OPS-008', [wid], f'{P}/keep' if keep else P,
                               f'{wid} divides {left[0]} from {right[0]}: keep must name one')
            prims.append({'op': 'removeElement', 'id': right[0] if keep == left[0] else left[0]})
        prims.append({'op': 'removeElement', 'id': wid, 'cascade': True})
        return prims

    def x_addLevel(self, R, op, P):
        building = R.element(op['building'], ('buildings',), f'{P}/building')[1]
        height = length(op['height'], f'{P}/height')
        if 'elevation' in op:
            elevation = length(op['elevation'], f'{P}/elevation')
        else:
            k = 'above' if 'above' in op else 'below'
            lid = R.element(op[k], ('levels',), f'{P}/{k}')[1]
            ref = self.wc['levels'][lid]
            if not (isd(ref) and type(ref.get('elevation')) is int and type(ref.get('height')) is int):
                raise OpsError('FS-OPS-003', [lid], f'{P}/{k}', f'{lid} has no integer elevation and height')
            elevation = ref['elevation'] + ref['height'] if k == 'above' else ref['elevation'] - height
        element = {'building': building, 'elevation': elevation, 'height': height}
        element.update({k: copy.deepcopy(op[k]) for k in COMMON if k in op})
        return [{'op': 'addElement', 'collection': 'levels', 'id': self.new_id(op, 'L'), 'element': element}]

# ---------------------------------------------------------------------------------- chapter 6

def lock_ids(lock: dict) -> list[str]:
    (k, v), = lock.items()
    return sorted(set(v)) if k == 'distance' else [v]


def _wall_vec(doc, wid):
    w = doc['walls'][wid]
    s, e = doc['junctions'][w['start']]['position'], doc['junctions'][w['end']]['position']
    return tuple(s), (e[0] - s[0], e[1] - s[1])


def lock_valid_in_a(a: dict, lock: dict) -> bool:
    (k, v), = lock.items()
    if k == 'element':
        return v in all_ids(a)
    if k == 'length':
        return v in coll(a, 'walls')
    if not all(x in coll(a, 'walls') for x in v):
        return False
    (_, d1), (_, d2) = _wall_vec(a, v[0]), _wall_vec(a, v[1])
    return plane.cross(d1, d2) == 0


def _room_cycle(doc, rid):
    r = doc['rooms'][rid]
    lf = LevelFaces(doc, r['level'])
    f = lf.face_of(r['anchor'])
    return {u: lf.pos[u] for _, u, _ in lf.faces[f]['outer']}


def lock_holds(a: dict, b: dict, lock: dict) -> bool:
    """a and b in canonical form (constant defaults omitted); both valid."""
    (k, v), = lock.items()
    if k == 'element':
        c = next(c for c in COLLECTIONS if v in coll(a, c))
        if v not in coll(b, c) or not same(a[c][v], b[c][v]):
            return False
        if c in ('walls', 'separators'):
            unmoved = {j: a['junctions'][a[c][v][j]]['position'] for j in ('start', 'end')}
            return all(a[c][v][j] in coll(b, 'junctions') and b['junctions'][a[c][v][j]]['position'] == p
                       for j, p in unmoved.items())
        if c == 'rooms':
            return all(j in coll(b, 'junctions') and tuple(b['junctions'][j]['position']) == p
                       for j, p in _room_cycle(a, v).items())
        return True
    if k == 'length':
        if v not in coll(b, 'walls'):
            return False
        (_, da), (_, db) = _wall_vec(a, v), _wall_vec(b, v)
        return plane.dot(da, da) == plane.dot(db, db)
    if not all(x in coll(b, 'walls') for x in v):
        return False
    (p1a, d1a), (p2a, d2a) = _wall_vec(a, v[0]), _wall_vec(a, v[1])
    (p1b, d1b), (p2b, d2b) = _wall_vec(b, v[0]), _wall_vec(b, v[1])
    if plane.cross(d1b, d2b) != 0:
        return False
    ca = plane.cross(d1a, plane.sub(p2a, p1a))
    cb = plane.cross(d1b, plane.sub(p2b, p1b))
    return ca * ca * plane.dot(d1b, d1b) == cb * cb * plane.dot(d1a, d1a)


# ---------------------------------------------------------------------------------- 1.6

def _member_diff(target: str, a: dict, b: dict) -> list[dict]:
    out = []
    for m in sorted(set(a) | set(b)):
        if m in a and (m not in b or not same(a[m], b[m])):
            out.append({'op': 'setProperty', 'id': target, 'path': '/' + esc(m), 'value': copy.deepcopy(a[m])})
        elif m in b and m not in a:
            out.append({'op': 'unsetProperty', 'id': target, 'path': '/' + esc(m)})
    return out


def inverse(a: dict, b: dict) -> list[dict]:
    """The structural difference from B back to A (1.6), both in canonical form."""
    out = []
    for c in INVERSE_ORDER:                                         # step 1: property differences
        ca, cb = coll(a, c), coll(b, c)
        for eid in sorted(set(ca) & set(cb)):
            out += _member_diff(eid, ca[eid], cb[eid])
    for c in INVERSE_ORDER:                                         # step 2: removals
        for eid in sorted(set(coll(b, c)) - set(coll(a, c))):
            out.append({'op': 'removeElement', 'id': eid})
    for c in reversed(INVERSE_ORDER):                               # step 3: additions
        for eid in sorted(set(coll(a, c)) - set(coll(b, c))):
            out.append({'op': 'addElement', 'collection': c, 'id': eid, 'element': copy.deepcopy(a[c][eid])})
    out += _member_diff('$project', a['project'], b['project'])     # step 4: project, site, document
    if 'site' in a and 'site' in b:
        out += _member_diff('$site', a['site'], b['site'])
    elif 'site' in a:
        out.append({'op': 'setProperty', 'id': '$document', 'path': '/site', 'value': copy.deepcopy(a['site'])})
    elif 'site' in b:
        out.append({'op': 'unsetProperty', 'id': '$document', 'path': '/site'})
    rest = [m for m in DOC_MEMBERS if m not in ('project', 'site')]
    out += _member_diff('$document', {m: a[m] for m in rest if m in a}, {m: b[m] for m in rest if m in b})
    return out


# ---------------------------------------------------------------------------------- the transaction

def _parse_request(req):
    if isinstance(req, (bytes, bytearray)):
        try:
            value, codes = parse(bytes(req))
        except Malformed as e:
            raise OpsError('FS-OPS-001', [], '', f'the request is not JSON: {e}')
        if codes:
            raise OpsError('FS-OPS-001', [], '', 'the request is not I-JSON: ' + ', '.join(codes))
        req = value
    check_request(req)
    return req


def dumps_doc(doc: dict) -> bytes:
    return json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def apply(a_bytes: bytes, request) -> tuple[dict, bytes | None]:
    """Applies an apply request (bytes, or an already-parsed value) to a document's bytes."""
    try:
        return _apply(a_bytes, request)
    except Rejected as r:
        return {'status': 'rejected', 'diagnostics': r.diagnostics}, None
    except OpsError as e:
        return {'status': 'rejected', 'diagnostics': [e.diagnostic()]}, None


def _apply(a_bytes, request):
    req = _parse_request(request)
    a_result, a_canonical, _ = core_check(a_bytes)                  # step 1
    if not a_result['valid']:
        raise OpsError('FS-OPS-002', [], None, ', '.join(d['code'] for d in a_result['diagnostics']))
    a, _ = parse(a_bytes)
    context = req.get('context', {})
    bad = [OpsError('FS-OPS-010', lock_ids(lock), f'/context/locks/{i}')
           for i, lock in enumerate(context.get('locks', [])) if not lock_valid_in_a(a, lock)]
    if bad:
        raise Rejected([e.diagnostic() for e in bad])
    tx = Transaction(a, context)
    tx.run(req['batch'])                                            # steps 2-4
    try:
        normalize(tx.wc, tx.in_a_junctions, tx.mint)                # step 5
    except OpsStraddle as s:
        raise Rejected([e.diagnostic() for e in s.errors])
    b_result, b_canonical, _ = core_check(dumps_doc(tx.wc))         # step 6
    if not b_result['valid']:
        raise Rejected([d for d in b_result['diagnostics'] if d['severity'] == 'error'])
    a_c = canon.omit_defaults(a)
    b, _ = parse(b_canonical)
    broken = [OpsError('FS-OPS-011', lock_ids(lock), f'/context/locks/{i}')
              for i, lock in enumerate(context.get('locks', [])) if not lock_holds(a_c, b, lock)]
    if broken:
        raise Rejected([e.diagnostic() for e in broken])
    ids_a, ids_b = all_ids(a), all_ids(b)
    result = {
        'status': 'committed',
        'diagnostics': [],
        'document': b_canonical.decode('utf-8'),
        'hash': b_result['hash'],
        'resolved': tx.resolved,
        'created': sorted(ids_b - ids_a),
        'removed': sorted(ids_a - ids_b),
        'inverse': inverse(a_c, b),
    }
    return result, b_canonical

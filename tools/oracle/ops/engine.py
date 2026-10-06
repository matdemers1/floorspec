"""The transaction (Ops 1.2): check A, then for each operation resolve and expand it and apply its
primitives, then normalize, validate and check the locks; and the result (1.3) - the resolved
echo (1.4), created and removed, and the inverse (1.6).

``apply(a_bytes, request) -> (result, b_bytes | None)``.

Where an earlier draft left a choice, Ops 0.1 now settles it, and this module follows the text:
the order of checks (1.2, 7.1), the order of resolution within an operation (1.2 step 2), what a
shorthand resolves (2.1.2, 2.5), what $document addresses (2.3), minting (1.5), the order of the
inverse - property differences first (1.6) - and one diagnostic per failing opening or lock
(7.1.2).

Every run follows one draft (version.py): Ops 0.1 as published, or Ops 0.2, which validates with
a Core 0.2 reader and adds program items and extension elements to the space of IDs an edit can
address (space.py), their rows in the removal table (2.2), the adjacency primitives (2.6),
hosted elements on split walls (5.2 step 6), and the 0.2 composites. Under OPS_01 none of that
code runs, and the result is exactly what Ops 0.1 says.
"""

from __future__ import annotations

import copy
import json
import re
from fractions import Fraction

from .. import arcs, canon, plane
from ..jsonparse import Malformed, parse
from ..surd import Surd
from .errors import OpsError, Rejected, esc
from .faces import LevelFaces, coll, edit_view, is_point
from .normalize import OpsStraddle, effective_width, normalize
from .refs import DIRECTIONS, area, half, length
from .request import COLLECTIONS, ITEMS, check_request
from .select import Resolver, outward_normal
from .space import EXT, all_ids as space_ids, ext_collections, ext_elements, host_of, items as items_of, kind, locate
from .version import OPS_01, Profile

PREFIX = {'buildings': 'B', 'levels': 'L', 'junctions': 'J', 'walls': 'W', 'separators': 'S',
          'openings': 'O', 'rooms': 'R', 'slabs': 'SL', 'types': 'T', 'materials': 'M', 'assets': 'A',
          ITEMS: 'P',                               # Ops 0.2: program items
          'roofs': 'RF',                            # Ops 0.3: roofs (Core 16.1)
          'stairs': 'ST',                           # Ops 0.3: stairs (Core 17.1)
          'optionSets': 'OS', 'options': 'OP'}      # Ops 0.3: design options (Core 19.1)
EXT_PREFIX = 'X'                                    # Ops 0.2: every extension collection
DOC_MEMBERS = ('floorspec', 'project', 'site', 'extensionsUsed', 'extensionsRequired', 'extensions', 'extras')
DOC_MEMBERS_02 = DOC_MEMBERS + ('program',)
INVERSE_ORDER = ('openings', 'rooms', 'slabs', 'separators', 'walls', 'junctions', 'levels', 'buildings',
                 'types', 'materials', 'assets')
# Ops 0.2, 1.6 step 2: extension elements first, program items before levels
INVERSE_ORDER_02 = ('openings', 'rooms', 'slabs', 'separators', 'walls', 'junctions', ITEMS, 'levels',
                    'buildings', 'types', 'materials', 'assets')
# Ops 0.3: roofs after slabs, stairs after roofs, and options, then option sets, after junctions
INVERSE_ORDER_03 = ('openings', 'rooms', 'slabs', 'roofs', 'stairs', 'separators', 'walls', 'junctions', 'options',
                    'optionSets', ITEMS, 'levels', 'buildings', 'types', 'materials', 'assets')
# Ops 0.3, 2.8: the collections whose elements a batch adds in `context.option` (Core 19.2), beside extension elements
IN_OPTIONS = ('junctions', 'walls', 'separators', 'openings', 'rooms', 'slabs', 'roofs', 'stairs')
WALL_MEMBERS = ('type', 'layers', 'justification', 'base', 'top')
COMMON = ('name', 'extensions', 'extras')     # Core 1.4: what every element may carry


def isd(v) -> bool:
    return isinstance(v, dict)


def all_ids(doc: dict, profile: Profile = OPS_01) -> set:
    return space_ids(doc, profile)


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
    def __init__(self, a: dict, context: dict, profile: Profile = OPS_01):
        self.a = a
        self.P = profile
        self.wc = copy.deepcopy(a)
        self.in_a_junctions = set(coll(a, 'junctions'))
        self.a_ids = all_ids(a, profile)
        self.used: set[str] = set()                 # every ID named or minted in this batch
        self.retired = set(context.get('retired', []))
        self.locks = context.get('locks', [])
        self.minted: set[str] = set()
        self.resolved: list[dict] = []
        self.option = context.get('option') if profile.v03 else None      # Ops 0.3, 2.8

    # ------------------------------------------------------------------ 1.5 minting
    def mint(self, prefix: str) -> str:
        """One more than the largest n among the IDs in A, every ID named or minted earlier in the
        batch (removed again or not), and context.retired."""
        pat = re.compile(re.escape(prefix) + r'([0-9]+)')
        top = 0
        for eid in self.a_ids | all_ids(self.wc, self.P) | self.used | self.minted | self.retired:
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
            prims = getattr(self, 'x_' + op['op'])(Resolver(self.wc, self.P, self.option), op, f'/batch/{n}')
            for p in prims:
                self.apply(p, f'/batch/{n}')
                self.resolved.append(p)

    # ------------------------------------------------------------------ chapter 2: primitives
    def apply(self, p: dict, ptr: str) -> None:
        op = p['op']
        if op == 'addElement':
            self.add(place_of(p), p['id'], p['element'], ptr)
        elif op in ('addJunction', 'addWall', 'addSeparator'):
            c = {'addJunction': 'junctions', 'addWall': 'walls', 'addSeparator': 'separators'}[op]
            self.add((c,), p['id'], {k: v for k, v in p.items() if k not in ('op', 'id')}, ptr)
        elif op == 'removeElement':
            self.remove(p['id'], p.get('cascade', False), ptr)
        elif op == 'setProperty':
            self.set(p['id'], p['path'], p['value'], ptr)
        elif op == 'unsetProperty':
            self.unset(p['id'], p['path'], ptr)
        elif op == 'moveJunction':
            self.set(p['id'], '/position', p['to'], ptr)
        elif op == 'setAdjacency':
            self.set_adjacency(p, ptr)
        elif op == 'removeAdjacency':
            self.remove_adjacency(p, ptr)
        else:
            raise AssertionError(op)

    def container(self, place, ptr: str) -> dict:
        """The object a new element goes into, creating the objects on the way to it (2.1.3)."""
        if len(place) == 1 and place[0] != ITEMS:
            return self.wc.setdefault(place[0], {})
        path = ('program', 'items') if place[0] == ITEMS else ('extensions', place[1], 'collections', place[2])
        cur = self.wc
        for k in path:
            if k not in cur:
                cur[k] = {}
            if not isd(cur[k]):
                raise OpsError('FS-OPS-003', [], f'{ptr}/collection', f'/{"/".join(esc(x) for x in path)} leads through a value that is not an object')
            cur = cur[k]
        return cur

    def add(self, place, eid: str, element: dict, ptr: str) -> None:
        if eid in all_ids(self.wc, self.P) or eid in self.retired:
            raise OpsError('FS-OPS-005', [], ptr, f'{eid} is already used or retired')
        target = self.container(place, ptr)
        self.used.add(eid)
        target[eid] = copy.deepcopy(element)
        if self.option is not None and (place[0] in IN_OPTIONS or place[0] == EXT) and isd(target[eid]) \
                and 'option' not in target[eid]:
            target[eid]['option'] = self.option                     # Ops 0.3, 2.8.1

    def locate(self, eid):
        return locate(self.wc, eid, self.P)

    def collection_of(self, eid):
        loc = self.locate(eid)
        return kind(loc[0]) if loc else None

    def _ext_where(self, test):
        """Extension elements (Ops 0.2) for which test(element) holds, as ((place), ID)."""
        return [((EXT, x, c), eid) for x, c, eid, el in ext_elements(self.wc, self.P) if isd(el) and test(el)]

    @staticmethod
    def _host_is(member, eid):
        return lambda el: isd(el.get('host')) and el['host'].get(member) == eid

    @staticmethod
    def _fallback_is(*members_and_id):
        *members, eid = members_and_id
        return lambda el: isd(el.get('fallback')) and any(el['fallback'].get(m) == eid for m in members)

    def dependents(self, k: str, eid: str) -> list[str]:
        """What blocks removing an element without cascade (2.2)."""
        wc, out = self.wc, []

        def where(cc, test):
            out.extend(x for x, e in coll(wc, cc).items() if isd(e) and test(e))

        def ext(test):
            out.extend(x for _, x in self._ext_where(test))
        if k == 'buildings':
            where('levels', lambda e: e.get('building') == eid)
        elif k == 'levels':
            for cc in ('junctions', 'walls', 'separators', 'rooms', 'slabs', 'roofs'):
                where(cc, lambda e: e.get('level') == eid)
            where('walls', lambda e: (isd(e.get('base')) and e['base'].get('level') == eid)
                  or (isd(e.get('top')) and e['top'].get('level') == eid))
            ext(lambda el: self._host_is('level', eid)(el) or self._fallback_is('level', eid)(el))
            if self.P.v03:                                          # Ops 0.3: a stair from or to it
                where('stairs', lambda e: eid in (e.get('level'), e.get('to')))
        elif k == 'junctions':
            for cc in ('walls', 'separators'):
                where(cc, lambda e: eid in (e.get('start'), e.get('end')))
        elif k == 'walls':
            where('openings', lambda e: e.get('wall') == eid)
            ext(self._host_is('wall', eid))
        elif k == 'rooms':
            ext(self._host_is('room', eid))
        elif k == 'types':
            where('walls', lambda e: e.get('type') == eid)
            where('openings', lambda e: e.get('fill') == eid)
        elif k == 'materials':
            def layered(e):
                return isinstance(e.get('layers'), list) and any(isd(l) and l.get('material') == eid for l in e['layers'])
            where('types', layered)
            where('walls', layered)
            where('rooms', lambda e: eid in (e.get('wallFinish'), e.get('floorFinish'), e.get('ceilingFinish')))
            where('slabs', lambda e: e.get('material') == eid)
            where('roofs', lambda e: e.get('material') == eid)

            def finished(e):                                    # Core 0.3, 18.5: a face or a region names it
                f = e.get('finishes')
                faces = [x for x in f.values() if isd(x)] if isd(f) else []
                return any(x.get('material') == eid or (isinstance(x.get('regions'), list) and any(
                    isd(r) and r.get('material') == eid for r in x['regions'])) for x in faces)
            where('walls', finished)
        elif k == 'assets':
            maps = ('asset', 'normal', 'metallicRoughness', 'occlusion')      # Core 0.3, 18.2: every map
            where('materials', lambda e: isd(e.get('texture')) and any(e['texture'].get(m) == eid for m in maps))
            ext(self._fallback_is('asset', 'symbol', eid))
        elif k == ITEMS:
            where('rooms', lambda e: e.get('brief') == eid)
        elif k == 'optionSets':                                     # Ops 0.3: its options
            where('options', lambda e: e.get('set') == eid)
        elif k == 'options':                                        # Ops 0.3: what is in it
            for cc in IN_OPTIONS:
                where(cc, lambda e: e.get('option') == eid)
            ext(lambda el: el.get('option') == eid)
        return sorted(set(out) - {eid})

    def takes(self, place, eid: str):
        """What removing an element takes with it, when cascade is true (2.2)."""
        wc, out, k = self.wc, [], kind(place)

        def where(cc, test):
            out.extend(((cc,), x) for x, e in coll(wc, cc).items() if isd(e) and test(e))
        if k == 'buildings':
            where('levels', lambda e: e.get('building') == eid)
        elif k == 'levels':
            for cc in ('junctions', 'walls', 'separators', 'rooms', 'slabs', 'roofs'):
                where(cc, lambda e: e.get('level') == eid)
            out.extend(self._ext_where(lambda el: self._host_is('level', eid)(el) or self._fallback_is('level', eid)(el)))
            if self.P.v03:                                          # Ops 0.3: a stair from or to it
                where('stairs', lambda e: eid in (e.get('level'), e.get('to')))
        elif k == 'junctions':
            for cc in ('walls', 'separators'):
                where(cc, lambda e: eid in (e.get('start'), e.get('end')))
        elif k == 'walls':
            where('openings', lambda e: e.get('wall') == eid)
            out.extend(self._ext_where(self._host_is('wall', eid)))
        elif k == 'rooms':
            out.extend(self._ext_where(self._host_is('room', eid)))
        elif k == 'optionSets':                                     # Ops 0.3
            where('options', lambda e: e.get('set') == eid)
        elif k == 'options':
            for cc in IN_OPTIONS:
                where(cc, lambda e: e.get('option') == eid)
            out.extend(self._ext_where(lambda el: el.get('option') == eid))
        return out

    def remove(self, eid: str, cascade: bool, ptr: str) -> None:
        loc = self.locate(eid)
        if loc is None:
            raise OpsError('FS-OPS-003', [], ptr, f'{eid} does not exist')
        place = loc[0]
        k = kind(place)
        if not cascade or k in ('types', 'materials', 'assets', ITEMS):
            deps = self.dependents(k, eid)
            if deps:
                raise OpsError('FS-OPS-006', [eid] + deps, ptr, f'{eid} is used by {", ".join(deps)}')
            gone = [(place, eid)]
        else:
            gone, todo = [], [(place, eid)]
            while todo:
                x = todo.pop()
                if x in gone:
                    continue
                gone.append(x)
                todo.extend(self.takes(*x))
        for pl, x in gone:
            del self.where_is(pl)[x]
        removed_walls = {x for pl, x in gone if pl == ('walls',)}
        for j in coll(self.wc, 'junctions').values():
            join = j.get('join') if isd(j) else None
            if isd(join) and isinstance(join.get('through'), list) and removed_walls & {w for w in join['through'] if isinstance(w, str)}:
                del j['join']
        if self.P.v02:                                              # 2.2.3, whether cascade or not
            removed_items = {x for pl, x in gone if pl == (ITEMS,)}
            program = self.wc.get('program')
            if removed_items and isd(program) and isinstance(program.get('adjacency'), list):
                program['adjacency'] = [e for e in program['adjacency']
                                        if not (isd(e) and (e.get('a') in removed_items or e.get('b') in removed_items))]
            removed_levels = {x for pl, x in gone if pl == ('levels',)}
            for it in items_of(self.wc, self.P).values():
                if isd(it) and it.get('level') in removed_levels:
                    del it['level']

    def where_is(self, place) -> dict:
        """The existing container of a place (it holds the element being removed)."""
        if place[0] == ITEMS:
            return self.wc['program']['items']
        if place[0] == EXT:
            return self.wc['extensions'][place[1]]['collections'][place[2]]
        return self.wc[place[0]]

    def doc_members(self):
        return DOC_MEMBERS_02 if self.P.v02 else DOC_MEMBERS

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
            if tokens and tokens[0] not in self.doc_members():
                raise OpsError('FS-OPS-003', [], f'{ptr}/path', f'$document has no member "{tokens[0]}"')
            return self.wc, []
        loc = self.locate(eid)
        if loc is None:
            raise OpsError('FS-OPS-003', [], f'{ptr}/id', f'{eid} does not exist')
        return loc[1][eid], [eid]

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

    # ------------------------------------------------------------------ 2.6 adjacencies (Ops 0.2)
    def _adjacency(self, ptr, create: bool):
        program = self.wc.get('program')
        if program is None and create:
            program = self.wc['program'] = {}
        if not isd(program):
            raise OpsError('FS-OPS-003', [], ptr, 'the document has no program')
        if 'adjacency' not in program and create:
            program['adjacency'] = []
        adj = program.get('adjacency')
        if not isinstance(adj, list):
            raise OpsError('FS-OPS-003', [], ptr, 'the program has no adjacency array')
        return adj

    @staticmethod
    def _same(e, a, b, k):
        return isd(e) and e.get('kind') == k and isinstance(e.get('a'), str) and isinstance(e.get('b'), str) \
            and sorted((e['a'], e['b'])) == sorted((a, b))

    def set_adjacency(self, p, ptr):
        adj = self._adjacency(ptr, True)
        entry = {k: copy.deepcopy(p[k]) for k in ('a', 'b', 'kind', 'weight') if k in p}
        for i, e in enumerate(adj):
            if self._same(e, p['a'], p['b'], p['kind']):
                adj[i] = entry
                return
        adj.append(entry)

    def remove_adjacency(self, p, ptr):
        adj = self._adjacency(ptr, False)
        keep = [e for e in adj if not self._same(e, p['a'], p['b'], p['kind'])]
        if len(keep) == len(adj):
            raise OpsError('FS-OPS-003', [], ptr, f'the program has no {p["kind"]} adjacency of {p["a"]} and {p["b"]}')
        adj[:] = keep

    # ------------------------------------------------------------------ primitives, resolved (2.5)
    def x_addElement(self, R, op, P):
        if 'extension' in op:
            eid = self.new_id(op, EXT_PREFIX)
            return [{'op': 'addElement', 'extension': op['extension'], 'collection': op['collection'], 'id': eid,
                     'element': copy.deepcopy(op['element'])}]
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

    def _adjacency_prim(self, R, op, P):
        a = R.item(op['a'], f'{P}/a')
        b = R.item(op['b'], f'{P}/b')
        return {'op': op['op'], 'a': a, 'b': b, 'kind': op['kind']}

    def x_setAdjacency(self, R, op, P):
        p = self._adjacency_prim(R, op, P)
        if 'weight' in op:
            p['weight'] = copy.deepcopy(op['weight'])
        return [p]

    def x_removeAdjacency(self, R, op, P):
        return [self._adjacency_prim(R, op, P)]

    # ------------------------------------------------------------------ chapter 4: composites
    def _draw(self, R, op, P, name, prefix, members):
        level = R.element(op['level'], ('levels',), f'{P}/level')[1]
        ends = [R.point_or_junction(op[k], f'{P}/{k}') for k in ('from', 'to')]
        at = {}
        for jid, j in sorted(coll(R.view, 'junctions').items(), reverse=True):   # Ops 0.3: in the edit design (2.8)
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
        c = self.wc['rooms'][rid].get('ceiling')                     # Ops 0.3: a vault's ridge moves with its room
        if isinstance(c, dict) and c.get('kind') == 'vaulted' and isinstance(c.get('ridge'), list) \
                and len(c['ridge']) == 2 and all(is_point(p) for p in c['ridge']):
            prims.append({'op': 'setProperty', 'id': rid, 'path': '/ceiling/ridge',
                          'value': [[x + vx, y + vy] for x, y in c['ridge']]})
        for eid in self._on_surface_of(rid):                        # Ops 0.2: what stands in the room
            x, y = self.locate(eid)[1][eid]['host']['position']
            prims.append({'op': 'setProperty', 'id': eid, 'path': '/host/position', 'value': [x + vx, y + vy]})
        return prims

    def _on_surface_of(self, rid) -> list[str]:
        """Ops 0.2: the extension elements on a room's floor or ceiling whose position is a point,
        by ID."""
        out = []
        for _, _, eid, el in ext_elements(self.wc, self.P):
            h = host_of(el)
            if h is not None and h.get('mode') == 'surface' and h.get('room') == rid and is_point(h.get('position')):
                out.append(eid)
        return sorted(out)

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
            across.update(lf.rooms_in(R.view, lf.he_face.get((eid, t, s))))
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
        D = wall_length(self.wc, o['wall'] if 'opening' in op else wid, S, E)
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
            D = wall_length(self.wc, o['wall'] if 'opening' in op else wid, S, E)
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
        if 'brief' in op:                                           # Ops 0.2
            element['brief'] = R.item(op['brief'], f'{P}/brief')
        element.update({k: copy.deepcopy(op[k]) for k in ('function', 'wallFinish', 'floorFinish', 'ceilingFinish') + COMMON if k in op})
        return [{'op': 'addElement', 'collection': 'rooms', 'id': self.new_id(op, 'R'), 'element': element}]

    def x_setRoomBrief(self, R, op, P):
        rid = R.room(op['room'], f'{P}/room')
        iid = R.item(op['item'], f'{P}/item')
        return [{'op': 'setProperty', 'id': rid, 'path': '/brief', 'value': iid}]

    def x_setRoomFinish(self, R, op, P):
        rid = R.room(op['room'], f'{P}/room')
        return [{'op': 'setProperty', 'id': rid, 'path': f'/{op["surface"]}Finish', 'value': op['material']}]

    def x_removeWall(self, R, op, P):
        wid = R.element(op['wall'], ('walls',), f'{P}/wall')[1]
        keep = R.room(op['keep'], f'{P}/keep') if 'keep' in op else None
        w = self.wc['walls'][wid]
        lf = R.level_faces(w.get('level'), f'{P}/wall')
        s, t = w['start'], w['end']
        left = lf.rooms_in(R.view, lf.he_face.get((wid, s, t)))
        right = lf.rooms_in(R.view, lf.he_face.get((wid, t, s)))
        prims = []
        if len(left) == 1 and len(right) == 1 and left != right:
            if keep not in (left[0], right[0]):
                raise OpsError('FS-OPS-008', [wid], f'{P}/keep' if keep else P,
                               f'{wid} divides {left[0]} from {right[0]}: keep must name one')
            gone = right[0] if keep == left[0] else left[0]
            for eid in self._on_surface_of_any(gone):               # Ops 0.2: re-hosted on the room kept
                prims.append({'op': 'setProperty', 'id': eid, 'path': '/host/room', 'value': keep})
            prims.append({'op': 'removeElement', 'id': gone})
        prims.append({'op': 'removeElement', 'id': wid, 'cascade': True})
        return prims

    def _on_surface_of_any(self, rid) -> list[str]:
        out = [eid for _, _, eid, el in ext_elements(self.wc, self.P)
               if host_of(el) is not None and host_of(el).get('mode') == 'surface' and host_of(el).get('room') == rid]
        return sorted(out)

    def x_addProgramItem(self, R, op, P):
        element = {'function': copy.deepcopy(op['function'])}
        if 'count' in op:
            element['count'] = copy.deepcopy(op['count'])
        for k in ('targetArea', 'minArea'):
            if k in op:
                element[k] = area(op[k], f'{P}/{k}')
        if 'level' in op:
            element['level'] = R.element(op['level'], ('levels',), f'{P}/level')[1]
        element.update({k: copy.deepcopy(op[k]) for k in COMMON if k in op})
        return [{'op': 'addElement', 'collection': ITEMS, 'id': self.new_id(op, PREFIX[ITEMS]), 'element': element}]

    def resolve_host(self, R, h, P):
        """4.10: a host reference resolved to a Core host (13.3), and the host's level."""
        mode = h['mode']
        if mode == 'wallFace':
            wid = R.element(h['wall'], ('walls',), f'{P}/wall')[1]
            s, t, S, E = R.wall_line('walls', wid, f'{P}/wall')
            if 'side' in h:
                side = h['side']
            else:
                rid = R.room(h['toward'], f'{P}/toward')
                lf, f = R.room_face(rid, f'{P}/toward')
                left, right = lf.he_face.get((wid, s, t), 'none'), lf.he_face.get((wid, t, s), 'none')
                if f == left and f != right:
                    side = 'left'
                elif f == right and f != left:
                    side = 'right'
                else:
                    raise OpsError('FS-OPS-008', [wid], f'{P}/toward', f'{rid} is not on one side of {wid}')
            D = wall_length(self.wc, wid, S, E)
            offset = R.position(h['at'], D, 0, f'{P}/at')
            height = length(h['height'], f'{P}/height')
            host = {'mode': 'wallFace', 'wall': wid, 'side': side, 'offset': offset, 'height': height}
            owner = ('walls', wid)
        elif mode == 'surface':
            rid = R.room(h['room'], f'{P}/room')
            x, y = R.point(h['at'], f'{P}/at')
            host = {'mode': 'surface', 'room': rid, 'surface': h['surface'], 'position': [x, y]}
            owner = ('rooms', rid)
        else:
            lid = R.element(h['level'], ('levels',), f'{P}/level')[1]
            x, y = R.point(h['at'], f'{P}/at')
            host = {'mode': 'free', 'level': lid, 'position': [x, y]}
            owner = None
        if 'rotation' in h:
            host['rotation'] = copy.deepcopy(h['rotation'])
        if owner is None:
            return host, host['level']
        e = self.wc[owner[0]][owner[1]]
        level = e.get('level') if isd(e) else None
        if not isinstance(level, str):
            raise OpsError('FS-OPS-003', [owner[1]], f'{P}/{"wall" if owner[0] == "walls" else "room"}', f'{owner[1]} is on no level')
        return host, level

    def x_placeElement(self, R, op, P):
        host, level = self.resolve_host(R, op['host'], f'{P}/host')
        element = copy.deepcopy(op['element'])
        element['host'] = host
        if 'fallback' not in element:
            element['fallback'] = {'level': level}
        elif isd(element['fallback']):
            element['fallback']['level'] = level
        return [{'op': 'addElement', 'extension': op['extension'], 'collection': op['collection'],
                 'id': self.new_id(op, EXT_PREFIX), 'element': element}]

    def x_moveElement(self, R, op, P):
        eid = R.element(op['element'], (EXT,), f'{P}/element')[1]
        host, level = self.resolve_host(R, op['host'], f'{P}/host')
        return [{'op': 'setProperty', 'id': eid, 'path': '/host', 'value': host},
                {'op': 'setProperty', 'id': eid, 'path': '/fallback/level', 'value': level}]

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


def wall_length(wc, wid, S, E):
    """3.5: the exact length of a wall's location line - for an arc wall with a well-formed arc that fits, its
    length along its polyline (Core 21.6)."""
    h = arc_of(coll(wc, 'walls').get(wid))
    if h is not None and S != E and arcs.fits(S, E, h):
        return Surd(arcs.length(arcs.polyline(tuple(S), tuple(E), h)))
    return Surd.sqrt((E[0] - S[0]) ** 2 + (E[1] - S[1]) ** 2)


def arc_of(e):
    """An edge's sagitta when its `arc` is well formed (Core 21.1.1), else None."""
    a = e.get('arc') if isinstance(e, dict) else None
    h = a.get('sagitta') if isinstance(a, dict) and set(a) == {'sagitta'} else None
    return h if type(h) is int and h != 0 else None


def _ends(doc, wid):
    w = doc['walls'][wid]
    return tuple(doc['junctions'][w['start']]['position']), tuple(doc['junctions'][w['end']]['position'])


def _wall_vec(doc, wid):
    w = doc['walls'][wid]
    s, e = doc['junctions'][w['start']]['position'], doc['junctions'][w['end']]['position']
    return tuple(s), (e[0] - s[0], e[1] - s[1])


def lock_valid_in_a(a: dict, lock: dict, profile: Profile = OPS_01) -> bool:
    (k, v), = lock.items()
    if k == 'element':
        return v in all_ids(a, profile)
    if k == 'length':
        return v in coll(a, 'walls')
    if not all(x in coll(a, 'walls') for x in v):
        return False
    (_, d1), (_, d2) = _wall_vec(a, v[0]), _wall_vec(a, v[1])
    return plane.cross(d1, d2) == 0


def _room_cycle(doc, rid, option=None):
    r = doc['rooms'][rid]
    lf = LevelFaces(edit_view(doc, option), r['level'])
    f = lf.face_of(r['anchor'])
    return {u: lf.pos[u] for _, u, _ in lf.faces[f]['outer']}


def lock_holds(a: dict, b: dict, lock: dict, profile: Profile = OPS_01, option=None) -> bool:
    """a and b in canonical form (constant defaults omitted); both valid."""
    (k, v), = lock.items()
    if k == 'element':
        place, ca = locate(a, v, profile)
        lb = locate(b, v, profile)
        if lb is None or lb[0] != place or not same(ca[v], lb[1][v]):
            return False
        c = place[0]
        if c == EXT:                                                # Ops 0.2, 6.1: a wall-face host is unmoved
            h = host_of(ca[v])
            if h is None or h.get('mode') != 'wallFace':
                return True
            w = a['walls'][h['wall']]
            return all(w[j] in coll(b, 'junctions') and b['junctions'][w[j]]['position'] == a['junctions'][w[j]]['position']
                       for j in ('start', 'end'))
        if c in ('walls', 'separators'):
            unmoved = {j: a['junctions'][a[c][v][j]]['position'] for j in ('start', 'end')}
            return all(a[c][v][j] in coll(b, 'junctions') and b['junctions'][a[c][v][j]]['position'] == p
                       for j, p in unmoved.items())
        if c == 'rooms':
            return all(j in coll(b, 'junctions') and tuple(b['junctions'][j]['position']) == p
                       for j, p in _room_cycle(a, v, option).items())
        return True
    if k == 'length':
        if v not in coll(b, 'walls'):
            return False
        (_, da), (_, db) = _wall_vec(a, v), _wall_vec(b, v)
        ha, hb = arc_of(a['walls'][v]), arc_of(b['walls'][v])
        if ha is not None or hb is not None:                    # Ops 0.4: an arc wall's length (Core 21.6)
            la = wall_length(a, v, *_ends(a, v))
            lb = wall_length(b, v, *_ends(b, v))
            return (ha is None) == (hb is None) and (la - lb).is_zero()
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


def inverse(a: dict, b: dict, profile: Profile = OPS_01) -> list[dict]:
    """The structural difference from B back to A (1.6), both in canonical form."""
    if profile.v02:
        return inverse_02(a, b, profile)
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
    return out + _document_diff(a, b, DOC_MEMBERS)                  # step 4


def _document_diff(a: dict, b: dict, members) -> list[dict]:
    """Step 4 of 1.6: project, site, and the document's other top-level members."""
    out = _member_diff('$project', a['project'], b['project'])
    if 'site' in a and 'site' in b:
        out += _member_diff('$site', a['site'], b['site'])
    elif 'site' in a:
        out.append({'op': 'setProperty', 'id': '$document', 'path': '/site', 'value': copy.deepcopy(a['site'])})
    elif 'site' in b:
        out.append({'op': 'unsetProperty', 'id': '$document', 'path': '/site'})
    rest = [m for m in members if m not in ('project', 'site')]
    if 'program' in rest and isd(a.get('program')) and isd(b.get('program')):      # Ops 0.2
        rest.remove('program')
        out += [{**p, 'path': '/program' + p['path']} for p in _member_diff('$document', a['program'], b['program'])]
    out += _member_diff('$document', {m: a[m] for m in rest if m in a}, {m: b[m] for m in rest if m in b})
    return out


def _places_02(a: dict, b: dict, profile: Profile):
    """Ops 0.2, 1.6 step 2: the extension collections of A and B (by extension, then collection
    name), then the thirteen collections and the program's items in INVERSE_ORDER_02."""
    exts = sorted({(EXT, x, c) for d in (a, b) for x, c, _ in ext_collections(d, profile)})
    order = INVERSE_ORDER_03 if profile.v03 else INVERSE_ORDER_02
    return exts + [(c,) for c in order]


def _in(doc: dict, place, profile: Profile) -> dict:
    if place[0] == ITEMS:
        return items_of(doc, profile)
    if place[0] == EXT:
        for x, c, coll_ in ext_collections(doc, profile):
            if (x, c) == place[1:]:
                return coll_
        return {}
    return coll(doc, place[0])


def inverse_02(a: dict, b: dict, profile: Profile) -> list[dict]:
    """1.6 in Ops 0.2: program items and extension elements are elements, and step 4 compares A with
    the document steps 1 to 3 leave - as it is, so that the empty objects they leave behind (an
    emptied `items`, a program with nothing in it) are removed too, and a 0.1 document comes back
    without a program its draft does not have."""
    places = _places_02(a, b, profile)
    out = []
    for pl in places:                                               # step 1
        ca, cb = _in(a, pl, profile), _in(b, pl, profile)
        for eid in sorted(set(ca) & set(cb)):
            out += _member_diff(eid, ca[eid], cb[eid])
    for pl in places:                                               # step 2
        for eid in sorted(set(_in(b, pl, profile)) - set(_in(a, pl, profile))):
            out.append({'op': 'removeElement', 'id': eid})
    for pl in reversed(places):                                     # step 3
        ca = _in(a, pl, profile)
        for eid in sorted(set(ca) - set(_in(b, pl, profile))):
            p = {'op': 'addElement'}
            if pl[0] == EXT:
                p['extension'] = pl[1]
                p['collection'] = pl[2]
            else:
                p['collection'] = pl[0]
            p.update({'id': eid, 'element': copy.deepcopy(ca[eid])})
            out.append(p)
    tx = Transaction(b, {}, profile)                                # B': what steps 1 to 3 leave
    for p in out:
        try:
            tx.apply(p, '')
        except OpsError as e:                                       # by construction, never
            raise AssertionError(f'the inverse does not apply to B: {p}: {e}') from e
    return out + _document_diff(a, tx.wc, DOC_MEMBERS_02)        # B' as it is, not in canonical form


# ---------------------------------------------------------------------------------- the transaction

def place_of(p: dict):
    """Where an addElement puts its element (2.1): a collection, the program's items, or an
    extension's collection."""
    if 'extension' in p:
        return (EXT, p['extension'], p['collection'])
    return (p['collection'],)


def _parse_request(req, profile: Profile):
    if isinstance(req, (bytes, bytearray)):
        try:
            value, codes = parse(bytes(req))
        except Malformed as e:
            raise OpsError('FS-OPS-001', [], '', f'the request is not JSON: {e}')
        if codes:
            raise OpsError('FS-OPS-001', [], '', 'the request is not I-JSON: ' + ', '.join(codes))
        req = value
    check_request(req, profile)
    return req


def dumps_doc(doc: dict) -> bytes:
    return json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def apply(a_bytes: bytes, request, profile: Profile = OPS_01) -> tuple[dict, bytes | None]:
    """Applies an apply request (bytes, or an already-parsed value) to a document's bytes, as the
    draft `profile` says (Ops 0.1 by default)."""
    try:
        return _apply(a_bytes, request, profile)
    except Rejected as r:
        return {'status': 'rejected', 'diagnostics': r.diagnostics}, None
    except OpsError as e:
        return {'status': 'rejected', 'diagnostics': [e.diagnostic()]}, None


def _apply(a_bytes, request, profile: Profile):
    req = _parse_request(request, profile)
    a_result, a_canonical, _ = profile.validate(a_bytes)  # step 1
    if not a_result['valid']:
        raise OpsError('FS-OPS-002', [], None, ', '.join(d['code'] for d in a_result['diagnostics']))
    a, _ = parse(a_bytes)
    context = req.get('context', {})
    bad = [OpsError('FS-OPS-010', lock_ids(lock), f'/context/locks/{i}')
           for i, lock in enumerate(context.get('locks', [])) if not lock_valid_in_a(a, lock, profile)]
    if bad:
        raise Rejected([e.diagnostic() for e in bad])
    tx = Transaction(a, context, profile)
    tx.run(req['batch'])                                            # steps 2-4
    try:
        normalize(tx.wc, tx.in_a_junctions, tx.mint, profile)       # step 5
    except OpsStraddle as s:
        raise Rejected([e.diagnostic() for e in s.errors])
    b_result, b_canonical, _ = profile.validate(dumps_doc(tx.wc))  # step 6
    if not b_result['valid']:
        raise Rejected([d for d in b_result['diagnostics'] if d['severity'] == 'error'])
    a_c = canon.omit_defaults(a)
    b, _ = parse(b_canonical)
    broken = [OpsError('FS-OPS-011', lock_ids(lock), f'/context/locks/{i}')
              for i, lock in enumerate(context.get('locks', [])) if not lock_holds(a_c, b, lock, profile, tx.option)]
    if broken:
        raise Rejected([e.diagnostic() for e in broken])
    ids_a, ids_b = all_ids(a, profile), all_ids(b, profile)
    result = {
        'status': 'committed',
        'diagnostics': [],
        'document': b_canonical.decode('utf-8'),
        'hash': b_result['hash'],
        'resolved': tx.resolved,
        'created': sorted(ids_b - ids_a),
        'removed': sorted(ids_a - ids_b),
        'inverse': inverse(a_c, b, profile),
    }
    return result, b_canonical

"""The named-measure library (spec/rules chapters 5 to 8): each measure's targets, arguments, type,
what it reads (4.6) and its exact value. compute() returns (value, involved) - involved None for a
measure whose definition names nothing it found."""

from __future__ import annotations

import re
from fractions import Fraction

from .. import canon, plane
from ..program import room_relations
from . import geometry
from .context import circuit_defaults, element_defaults, matches, member
from .qr import QR, round_div_sqrt
from .structure import COLLECTION, EXT_NAME, MAXI, is_int
from .wallline import receptacle_measures

CORE_FUNCTIONS = ('unspecified', 'sleeping', 'bath', 'kitchen', 'living', 'dining', 'office', 'laundry', 'utility',
                  'storage', 'circulation', 'mechanical', 'garage', 'exterior')
EXT_TERM = r'(FS|EXT|[A-Z0-9]{2,8})_[A-Za-z0-9]+:[a-z][A-Za-z0-9]*'
PURPOSES = ('workingSpace', 'fixtureClearance', 'swing', 'access')
ELEC = 'FS_electrical'

# 4.8: reserved, not evaluated
DEFERRED = {'ceilingHeight', 'roomNarrowestDimension', 'stairRiserHeight', 'stairTreadDepth', 'stairWidth',
            'stairHeadroom', 'stairHandrailHeight', 'countertopReceptacleReach', 'countertopWallRunBetweenReceptacles',
            'travelDistance', 'floorElevationDifference'}


# ------------------------------------------------------------------ argument types
def a_function(v):
    return isinstance(v, str) and (v in CORE_FUNCTIONS or re.fullmatch(EXT_TERM, v) is not None)


def a_ext(v):
    return isinstance(v, str) and re.fullmatch(EXT_NAME, v) is not None


def a_coll(v):
    return isinstance(v, str) and re.fullmatch(COLLECTION, v) is not None


def a_match(v):
    return (isinstance(v, dict) and len(v) >= 1
            and all(re.fullmatch(COLLECTION, k) and (isinstance(x, (str, bool)) or (is_int(x) and -MAXI <= x <= MAXI))
                    for k, x in v.items()))


def a_length(v):
    return is_int(v) and -MAXI <= v <= MAXI


def a_positive(v):
    return is_int(v) and 0 < v <= MAXI


def a_enum(*vals):
    return lambda v: isinstance(v, str) and v in vals


class M:
    def __init__(self, name, kinds, typ, fn, args=None, required=(), reads=None, involved=False, check=None):
        self.name, self.kinds, self.typ, self.fn = name, set(kinds), typ, fn
        self.args, self.required = args or {}, set(required)
        self.reads = reads or (lambda a: set())
        self.involved = involved
        self.check = check          # a cross-argument check

    def type_of(self, args):
        return args['type'] if self.typ is None else self.typ

    def args_ok(self, args) -> bool:
        if not isinstance(args, dict) or not self.required <= set(args) or not set(args) <= set(self.args):
            return False
        return all(self.args[k](v) for k, v in args.items()) and (self.check is None or self.check(args))


MEASURES: dict[tuple, M] = {}


def measure(name, kinds, typ, **kw):
    def deco(fn):
        m = M(name, kinds, typ, fn, **kw)
        for k in kinds:
            MEASURES[(name, k)] = m
        return fn
    return deco


def names():
    return {n for n, _ in MEASURES}


def get(name, kind):
    return MEASURES.get((name, kind))


# ------------------------------------------------------------------ 5. rooms
def _function(ctx, rid):
    return ctx.doc.rooms[rid].get('function', 'unspecified')


@measure('roomFunction', ['room'], 'term')
def room_function(ctx, t, a):
    return _function(ctx, t['id']), None


@measure('roomNetArea', ['room'], 'area')
def room_net_area(ctx, t, a):
    return Fraction(ctx.derived['rooms'][t['id']]['area']), None


@measure('roomLeastWidth', ['room'], 'length')
def room_least_width(ctx, t, a):
    c, L = geometry.least_width([tuple(p) for p in ctx.derived['rooms'][t['id']]['outer']])
    return round_div_sqrt(c, L), None


@measure('roomIsEntry', ['room'], 'boolean')
def room_is_entry(ctx, t, a):
    return ctx.derived['circulation'][t['id']]['entry'], None


@measure('roomIsReachable', ['room'], 'boolean')
def room_is_reachable(ctx, t, a):
    return ctx.derived['circulation'][t['id']]['reachable'], None


@measure('roomThroughSleeping', ['room'], 'boolean')
def room_through_sleeping(ctx, t, a):
    return ctx.derived['circulation'][t['id']].get('throughSleeping', False), None


def _relations(ctx):
    if not hasattr(ctx, '_relations'):
        adjacent, connected, _, _ = room_relations(ctx.doc)
        ctx._relations = (adjacent, connected)
    return ctx._relations


def _neighbour(ctx, rid, pairs, function):
    return any(rid in p and _function(ctx, next(iter(p - {rid}))) == function for p in pairs)


@measure('roomAdjacentTo', ['room'], 'boolean', args={'function': a_function}, required=['function'])
def room_adjacent_to(ctx, t, a):
    return _neighbour(ctx, t['id'], _relations(ctx)[0], a['function']), None


@measure('roomConnectedTo', ['room'], 'boolean', args={'function': a_function}, required=['function'])
def room_connected_to(ctx, t, a):
    return _neighbour(ctx, t['id'], _relations(ctx)[1], a['function']), None


def _element_ok(ctx, eid, a):
    x, c, el = ctx.ext[eid]
    if x != a['extension'] or ('collection' in a and c != a['collection']):
        return False
    return 'match' not in a or matches(el, element_defaults(x, c), a['match'])


COUNT_ARGS = {'extension': a_ext, 'collection': a_coll, 'match': a_match}


def _reads_match(a):
    return {a['extension']} if 'match' in a else set()


@measure('elementCount', ['room', 'level'], 'count', args=COUNT_ARGS, required=['extension'], reads=_reads_match)
def element_count(ctx, t, a):
    if t['kind'] == 'room':
        inside = [e for e in ctx.ext if ctx.room_of(e) == t['id']]
    else:
        inside = [e for e, (_, _, el) in ctx.ext.items() if el['fallback']['level'] == t['id']]
    return sum(1 for e in inside if _element_ok(ctx, e, a)), None


# ------------------------------------------------------------------ 8. wall lines, circuits, levels
def _counted(ctx, rid, a):
    floor = ctx.floor(ctx.doc.rooms[rid]['level'])
    defaults = element_defaults(ELEC, 'receptacles')

    def ok(eid):
        el = ctx.ext[eid][2]
        if 'match' in a and not matches(el, defaults, a['match']):
            return False
        return 'maxHeight' not in a or ctx.derived['placements'][eid]['point'][2] - floor <= a['maxHeight']
    return ok


RECEPTACLE_ARGS = {'match': a_match, 'maxHeight': a_length}


@measure('receptacleReach', ['room'], 'length', args=RECEPTACLE_ARGS, involved=True,
         reads=lambda a: {ELEC} if 'match' in a else set())
def receptacle_reach(ctx, t, a):
    reach, _, ids = receptacle_measures(ctx, t['id'], _counted(ctx, t['id'], a))
    return reach, ids


@measure('wallRunBetweenReceptacles', ['room'], 'length', args=RECEPTACLE_ARGS, involved=True,
         reads=lambda a: {ELEC} if 'match' in a else set())
def wall_run(ctx, t, a):
    _, run, ids = receptacle_measures(ctx, t['id'], _counted(ctx, t['id'], a))
    return run, ids


@measure('circuitCount', ['room'], 'count', args={'collection': a_coll, 'match': a_match, 'circuit': a_match},
         involved=True, reads=lambda a: {ELEC})
def circuit_count(ctx, t, a):
    coll = a.get('collection', 'receptacles')
    edef, cdef = element_defaults(ELEC, coll), circuit_defaults()
    out = []
    for cid, c in sorted(ctx.circuits().items()):
        if 'circuit' in a and not matches(c, cdef, a['circuit']):
            continue
        for load in c.get('loads', []):
            x = ctx.ext.get(load)
            if (x is not None and x[0] == ELEC and x[1] == coll and ctx.room_of(load) == t['id']
                    and ('match' not in a or matches(x[2], edef, a['match']))):
                out.append(cid)
                break
    return len(out), out


@measure('roomCount', ['level'], 'count', args={'function': a_function})
def room_count(ctx, t, a):
    return sum(1 for rid, r in ctx.doc.rooms.items()
               if r['level'] == t['id'] and ('function' not in a or _function(ctx, rid) == a['function'])), None


# ------------------------------------------------------------------ 6. openings
@measure('openingKind', ['opening'], 'term')
def opening_kind(ctx, t, a):
    fill = ctx.doc.openings[t['id']].get('fill')
    if fill is None:
        return 'empty', None
    return ('door' if ctx.doc.types[fill]['kind'] == 'doorType' else 'window'), None


@measure('openingOperation', ['opening'], 'term')
def opening_operation(ctx, t, a):
    """6.1: its fill type's operation (Core 0.3, 8.4), or no value."""
    fill = ctx.doc.openings[t['id']].get('fill')
    return (ctx.doc.types[fill].get('operation') if fill is not None else None), None


@measure('openingWidth', ['opening'], 'length')
def opening_width(ctx, t, a):
    return ctx.doc.opening_dims(t['id'])[0], None


@measure('openingHeight', ['opening'], 'length')
def opening_height(ctx, t, a):
    return ctx.doc.opening_dims(t['id'])[1], None


@measure('openingArea', ['opening'], 'area')
def opening_area(ctx, t, a):
    w, h, _ = ctx.doc.opening_dims(t['id'])
    return Fraction(w * h), None


@measure('openingSillHeight', ['opening'], 'length')
def opening_sill_height(ctx, t, a):
    return ctx.derived['openings'][t['id']]['sillElevation'] - ctx.floor(ctx.target_level(t)), None


@measure('openingHeadHeight', ['opening'], 'length')
def opening_head_height(ctx, t, a):
    return ctx.derived['openings'][t['id']]['headElevation'] - ctx.floor(ctx.target_level(t)), None


def wall_to_outside(ctx, wid) -> bool:
    lv = ctx.level(ctx.doc.walls[wid]['level'])
    return any(h not in lv.owner for h in lv.half_edges(wid))


@measure('openingToOutside', ['opening'], 'boolean')
def opening_to_outside(ctx, t, a):
    return wall_to_outside(ctx, ctx.doc.openings[t['id']]['wall']), None


# 6.5: the clear opening Core derives (Core 0.3, 7.4.2) - as declared, never computed
def _clear(ctx, t):
    return ctx.derived['openings'][t['id']].get('clearOpening', {})


@measure('openingNetClearWidth', ['opening'], 'length')
def opening_net_clear_width(ctx, t, a):
    return _clear(ctx, t).get('width'), None


@measure('openingNetClearHeight', ['opening'], 'length')
def opening_net_clear_height(ctx, t, a):
    return _clear(ctx, t).get('height'), None


@measure('openingNetClearArea', ['opening'], 'area')
def opening_net_clear_area(ctx, t, a):
    area = _clear(ctx, t).get('area')
    return (Fraction(area) if area is not None else None), None


@measure('doorClearWidth', ['opening'], 'length')
def door_clear_width(ctx, t, a):
    kind, _ = opening_kind(ctx, t, a)
    return (_clear(ctx, t).get('width') if kind == 'door' else None), None


# ------------------------------------------------------------------ 7. elements
def _member_ok(a):
    return 'unit' not in a or a['type'] == 'integer'


@measure('elementMember', ['element'], None, args={'name': lambda v: isinstance(v, str) and re.fullmatch(COLLECTION, v) is not None,
                                                    'type': a_enum('integer', 'term', 'terms', 'boolean'),
                                                    'unit': a_enum('V', 'A', 'W')},
         required=['name', 'type'], check=_member_ok)
def element_member(ctx, t, a):
    x, c, el = ctx.ext[t['id']]
    present, v = member(el, element_defaults(x, c), a['name'])
    if not present:
        return None, None
    typ = a['type']
    if typ == 'integer' and is_int(v):
        return v, None
    if typ == 'term' and isinstance(v, str):
        return v, None
    if typ == 'boolean' and isinstance(v, bool):
        return v, None
    if typ == 'terms' and isinstance(v, list) and all(isinstance(s, str) for s in v):
        return sorted(v, key=canon.utf16_key), None                    # 9.7: UTF-16 code units
    return None, None


@measure('elementRoomFunction', ['element'], 'term')
def element_room_function(ctx, t, a):
    rid = ctx.room_of(t['id'])
    return ('none' if rid is None else _function(ctx, rid)), None


@measure('elementBottomAboveFloor', ['element'], 'length')
def element_bottom(ctx, t, a):
    return ctx.derived['fallbacks'][t['id']]['bottom'] - ctx.floor(ctx.target_level(t)), None


@measure('elementTopAboveFloor', ['element'], 'length')
def element_top(ctx, t, a):
    return ctx.derived['fallbacks'][t['id']]['top'] - ctx.floor(ctx.target_level(t)), None


@measure('elementProtectedBy', ['element'], 'boolean', args={'protection': a_enum('gfci', 'afci')}, required=['protection'],
         involved=True, reads=lambda a: {ELEC})
def element_protected_by(ctx, t, a):
    eid = t['id']
    x, c, el = ctx.ext[eid]
    own = False
    if x == ELEC:
        present, features = member(el, element_defaults(x, c), 'features')
        own = present and isinstance(features, list) and a['protection'] in features
    cdef = circuit_defaults()
    by = sorted(cid for cid, ci in ctx.circuits().items()
                if eid in ci.get('loads', []) and a['protection'] in member(ci, cdef, 'protection')[1])
    return own or bool(by), by


# ------------------------------------------------------------------ 7.5-7.8 envelopes
@measure('envelopePurpose', ['envelope'], 'term')
def envelope_purpose(ctx, t, a):
    return ctx.envelope(t['id'], t['envelope'])[0]['purpose'], None


def _extent(i):
    def fn(ctx, t, a):
        box = ctx.envelope(t['id'], t['envelope'])[0]
        return box['max'][i] - box['min'][i], None
    return fn


for _i, _n in enumerate(('envelopeDepth', 'envelopeWidth', 'envelopeHeight')):
    measure(_n, ['envelope'], 'length')(_extent(_i))


@measure('envelopeBottomAboveFloor', ['envelope'], 'length')
def envelope_bottom(ctx, t, a):
    return ctx.envelope(t['id'], t['envelope'])[2]['bottom'] - ctx.floor(ctx.target_level(t)), None


def obstacles(ctx, owner, level):
    """7.6: (ID, plan ring, bottom, top) of every obstacle of an envelope of `owner` on `level`."""
    out = []
    host = ctx.host_wall(owner)
    lv = ctx.level(level)
    for wid in sorted(ctx.doc.walls):
        w = ctx.doc.walls[wid]
        if w['level'] != level or wid == host:
            continue
        out.append((wid, lv.g.outline(wid), ctx.doc.base_elevation(wid), ctx.doc.top_elevation(wid)))
    for eid in sorted(ctx.ext):
        fb = ctx.derived['fallbacks'][eid]
        if eid != owner and fb['level'] == level:
            out.append((eid, [tuple(p) for p in fb['footprint']], fb['bottom'], fb['top']))
    return out


def _local_triangles(local, ring):
    return [[local.of(p) for p in tri] for tri in geometry.triangulate(ring)]


@measure('envelopeObstructions', ['envelope'], 'count', involved=True)
def envelope_obstructions(ctx, t, a):
    box, frame, der = ctx.envelope(t['id'], t['envelope'])
    (x0, y0, _), (x1, y1, _) = box['min'], box['max']
    local = geometry.Local(frame)
    keep = [(0, x0, 1), (0, x1, -1), (1, y0, 1), (1, y1, -1)]
    found = []
    for oid, ring, bottom, top in obstacles(ctx, t['id'], der['level']):
        if not (max(bottom, der['bottom']) < min(top, der['top'])):
            continue
        if any(geometry.area_sign(geometry.clip(tri, keep)) > 0 for tri in _local_triangles(local, ring)):
            found.append(oid)
    return len(found), sorted(found)


@measure('clearDepthInFront', ['envelope'], 'length', args={'limit': a_positive}, required=['limit'], involved=True)
def clear_depth(ctx, t, a):
    box, frame, der = ctx.envelope(t['id'], t['envelope'])
    (x0, y0, _), (_, y1, _) = box['min'], box['max']
    local = geometry.Local(frame)
    keep = [(0, x0, 1), (1, y0, 1), (1, y1, -1)]
    dist = {}
    for oid, ring, bottom, top in obstacles(ctx, t['id'], der['level']):
        if not (max(bottom, der['bottom']) < min(top, der['top'])):
            continue
        best = None
        for tri in _local_triangles(local, ring):
            poly = geometry.clip(tri, keep)
            if geometry.area_sign(poly) > 0:
                lo = poly[0][0]
                for p in poly[1:]:
                    if p[0] < lo:
                        lo = p[0]
                d = lo - x0
                if best is None or d < best:
                    best = d
        if best is not None:
            dist[oid] = best
    if not dist:
        return a['limit'], []
    D = None
    for v in dist.values():
        if D is None or v < D:
            D = v
    r = D.round()
    if r >= a['limit']:
        return a['limit'], []
    return r, sorted(o for o, v in dist.items() if v == D)


@measure('envelopeOverlaps', ['envelope'], 'count', args={'purpose': a_enum(*PURPOSES)}, involved=True)
def envelope_overlaps(ctx, t, a):
    me = [t['id'], t['envelope']]
    count, owners = 0, set()
    for pair in ctx.derived['clearanceOverlaps']:
        if me not in pair:
            continue
        other = pair[1] if pair[0] == me else pair[0]
        if 'purpose' in a and ctx.derived['clearances'][other[0]][other[1]]['purpose'] != a['purpose']:
            continue
        count += 1
        owners.add(other[0])
    return count, sorted(owners)


def compute(ctx, name, target, args):
    m = MEASURES[(name, target['kind'])]
    return m.fn(ctx, target, args)


__all__ = ['MEASURES', 'DEFERRED', 'compute', 'get', 'names', 'plane', 'wall_to_outside', 'a_function', 'a_ext', 'a_coll',
           'PURPOSES']

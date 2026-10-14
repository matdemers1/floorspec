"""FS_renovation 0.1.0 (registry/FS_renovation/spec.md): its schema tier over the top-level data and
the data on core elements, its invariants - references across states and the Core invariants of each
state's view - its lint and its derived values, written from the extension's specification alone.

FS_renovation adds no kind of element. A wall's, separator's, opening's, room's, slab's, roof's or
stair's status is its own `extensions.FS_renovation.status`; an extension element's is the member of
the top-level `elements` named by its ID (1.3). The existing state is every element whose status is
not "new", the proposed state every element whose status is not "demolish" (2.2).
"""

from __future__ import annotations

import copy
import json

from .. import plane
from ..derive import Doc, ext_elements
from .common import CORE_COLLECTIONS, Context, load_schema

NAME, VERSION, CODE = 'FS_renovation', '0.1.0', 'RENO'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'renovation')
SEVERITY = {'FS-RENO-LINT-001': 'info'}
DEFINED = ('walls', 'separators', 'openings', 'rooms', 'slabs', 'roofs', 'stairs')    # 1.3: where its data may be
# 1.3.3: every other element that has an `extensions` member
OTHERS = ('buildings', 'levels', 'junctions', 'types', 'materials', 'assets', 'optionSets', 'options')
STATUSES = ('existing', 'demolish', 'new')
STATES = {'existing': ('existing', 'demolish'), 'proposed': ('existing', 'new')}     # 2.1, 2.2


def _data(el):
    x = el.get('extensions', {}) if isinstance(el, dict) else {}
    return x.get(NAME) if isinstance(x, dict) else None


def schema_errors(doc, data) -> list[str]:
    """1.3.1 to 1.3.3: the top-level data, and the data on every element, against the schema."""
    d = doc.d
    out = list(SCHEMA.errors(data))
    core = SCHEMA.root['$defs']['coreElements']
    for c in DEFINED:
        for eid, el in d.get(c, {}).items():
            v = _data(el)
            if v is not None:
                out.extend(f'{c}/{eid}{e}' for e in SCHEMA.errors({c: v}, core))
    others = [(c, d.get(c, {})) for c in OTHERS] + [('items', d.get('program', {}).get('items', {}))]
    for c, elements in others:
        for eid, el in elements.items():
            if _data(el) is not None:
                out.append(f'{c}/{eid}: may not carry {NAME} data')
    return out


def _top(d: dict) -> dict:
    data = d.get('extensions', {}).get(NAME, {})
    return data.get('elements', {}) if isinstance(data, dict) else {}


def statuses(d: dict) -> dict:
    """2.1: ID -> status of every element that has one: the seven collections' and extension elements'."""
    out = {}
    for c in DEFINED:
        for eid, el in d.get(c, {}).items():
            v = _data(el)
            out[eid] = v['status'] if v is not None else 'existing'
    top = _top(d)
    for _, _, eid, _ in ext_elements(d):
        out[eid] = top.get(eid, 'existing')
    return out


def view(d: dict, state: str) -> dict:
    """2.2: the document in a state - every element not in it removed, and every junction's join
    through a removed wall removed."""
    st = statuses(d)
    keep = STATES[state]
    gone = {eid for eid, s in st.items() if s not in keep}
    v = copy.deepcopy(d)
    for c in DEFINED:
        if c in v:
            v[c] = {eid: el for eid, el in v[c].items() if eid not in gone}
    for data in v.get('extensions', {}).values():
        if isinstance(data, dict) and isinstance(data.get('collections'), dict):
            for cname, coll in data['collections'].items():
                if isinstance(coll, dict):
                    data['collections'][cname] = {eid: el for eid, el in coll.items() if eid not in gone}
    for j in v.get('junctions', {}).values():
        if any(w in gone for w in j.get('join', {}).get('through', [])):
            del j['join']
    return v


def _reader(d: dict):
    from ..validate import ext_reader
    return ext_reader(json.dumps({'floorspec': d.get('floorspec')}).encode('utf-8'))


def core_errors(v: dict) -> list:
    """2.4: the errors Core reports of a state's view, as a document of its draft without design
    options and without known extensions - tier 4, the reference invariants and then the rest."""
    from ..validate import design_invariants, reference_tier
    ds = reference_tier(v)
    if not any(x['severity'] == 'error' for x in ds):
        ds = ds + design_invariants(v, _reader(v), None)
    return [x for x in ds if x['severity'] == 'error']


def invariants(ctx: Context):
    from ..validate import references
    d = ctx.d
    ds = []
    core = set()
    for c in CORE_COLLECTIONS + ('separators', 'stairs', 'optionSets', 'options'):
        core.update(d.get(c, {}))
    core.update(ctx.doc.items)
    for eid in sorted(_top(d)):                                                      # 1.3.4
        if eid in core:
            ds.append(ctx.diag('FS-RENO-INV-001', [eid]))
    st = statuses(d)
    seen = set()
    for _, eid, target, _, _ in references(d):                                       # 2.3.1
        a, b = st.get(eid), st.get(target)
        if a is None or b is None or (eid, target) in seen:
            continue
        if any(a in STATES[s] and b not in STATES[s] for s in STATES):
            seen.add((eid, target))
            ds.append(ctx.diag('FS-RENO-INV-002', [eid, target]))
    if any(x['code'] == 'FS-RENO-INV-002' for x in ds):                              # 4.2
        return ds
    for state, code in (('existing', 'FS-RENO-INV-003'), ('proposed', 'FS-RENO-INV-004')):   # 2.4.1, 2.4.2
        for x in core_errors(view(d, state)):
            ds.append(ctx.diag(code, x['elements']))
    return ds


def lints(ctx: Context):
    if any(s != 'existing' for s in statuses(ctx.d).values()):
        return []
    return [ctx.diag('FS-RENO-LINT-001')]                                            # 4.3


def _round_sqrt(n: int) -> int:
    from math import isqrt
    k = isqrt(n)
    return k + 1 if n - k * k > k else k


def wall_length(doc: Doc, derived_walls: dict, wid) -> int:
    """5.3: a straight wall's exact length rounded once; an arc wall's length L (Core 21.5)."""
    if 'length' in derived_walls.get(wid, {}):
        return derived_walls[wid]['length']
    w = doc.walls[wid]
    a, b = doc.junctions[w['start']]['position'], doc.junctions[w['end']]['position']
    return _round_sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)


def _rooms_of(v: dict):
    """5.4: every room of a view with its net area, and their sum - as twice-areas, exact."""
    from ..derive import derive as derive_all
    rooms = derive_all(Doc(v))['rooms']
    out = {}
    for rid in sorted(rooms):
        out[rid] = rooms[rid]['area']
    return out


def _area2(s: str) -> int:
    """A net area written as Core writes it (an integer, or one ending in .5) as twice the area."""
    return int(s[:-2]) * 2 + 1 if s.endswith('.5') else int(s) * 2


def derive(ctx: Context) -> dict:
    from ..derive import derive as derive_all
    d = ctx.d
    doc = ctx.doc
    st = statuses(d)
    status = {s: sorted(eid for eid, x in st.items() if x == s) for s in STATUSES}
    walls_derived = derive_all(doc)['walls']
    quantities = {}
    for s in STATUSES:
        ids = set(status[s])
        q = {c: sum(1 for eid in d.get(c, {}) if eid in ids) for c in ('walls',)}
        q['wallLength'] = sum(wall_length(doc, walls_derived, w) for w in d.get('walls', {}) if w in ids)
        for c in ('separators', 'openings', 'rooms', 'slabs'):
            q[c] = sum(1 for eid in d.get(c, {}) if eid in ids)
        q['slabArea'] = plane.area_string(sum(abs(plane.area2([tuple(p) for p in el['boundary']]))
                                              for eid, el in d.get('slabs', {}).items() if eid in ids))
        for c in ('roofs', 'stairs'):
            q[c] = sum(1 for eid in d.get(c, {}) if eid in ids)
        q['elements'] = sum(1 for _, _, eid, _ in ext_elements(d) if eid in ids)
        quantities[s] = q
    states = {}
    for state in STATES:
        rooms = _rooms_of(view(d, state))
        states[state] = {'rooms': rooms, 'area': plane.area_string(sum(_area2(a) for a in rooms.values()))}
    return {'status': status, 'quantities': quantities, 'states': states}

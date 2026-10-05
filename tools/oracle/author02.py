"""The conformance suite of Floorspec Core 0.2, as the script that writes it.

    python3.13 -m tools.oracle.author02            rewrite every test from its declaration below
    python3.13 -m tools.oracle.author02 --prune    ...and delete test directories no longer declared

The suite is the Core 0.1 suite, re-targeted to 0.2 - every 0.1 test, in the same group under the
same number, declaring "0.2" and covering the 0.2 IDs of any statement 0.2 retired - followed by
the tests of what 0.2 adds. Every expected diagnostic is written by hand and cross-checked against
the oracle, read as a Core 0.2 reader (validate.READER_02); geometry, hashes and canonical forms
come from the oracle. Afterwards, `python3.13 -m tools.oracle.regenerate` re-verifies the suite
from the files alone. Add new tests at the end of their group's section.
"""
import copy
import os
import re
import sys

import tools.oracle.author as v01                      # declares the 0.1 suite into author_lib.TESTS
from tools.oracle.author_lib import (FT, H, IN, MM, REPO, T100, TESTS, J, R, S, W, box, doc, fmt,
                                    level_doc, t, write_all)
from tools.oracle.validate import READER_02

SUITE02 = os.path.join(REPO, 'conformance', 'core', '0.2')
X, Y, CX, CY = v01.X, v01.Y, v01.CX, v01.CY
SCH = [('FS-SCH-001', [])]
M2 = 1280 * 1280 * 1000 * 1000                         # one square metre in square base units

# ============================================================================= the 0.1 suite, re-targeted

RETIRED = {'FS-CORE-1.2.1': 'FS-CORE-1.2.3', 'FS-CORE-1.6.5': 'FS-CORE-1.6.9'}
VERSION_TESTS = {
    # slug: (new floorspec value, new description)
    'version-is-a-number': (0.2, '"floorspec": 0.2 is a number, not the string "0.2". FS-DOC-001 applies only to a '
                                 'string naming another version, so this is a schema error.'),
    'version-with-patch': ('0.2.0', '"0.2.0" is not "0.2": patch releases are not declared. A reader that implements '
                                    '0.1 and 0.2 rejects it with FS-DOC-001.'),
    'unknown-version': ('0.3', 'A reader that implements 0.1 and 0.2 rejects a document declaring 0.3 with FS-DOC-001, '
                               'whatever else the document contains.'),
    'document-error-stops-schema': ('0.3', None),
}
_RAW_VERSION = re.compile(rb'("floorspec"\s*:\s*)"0\.1"')


def retarget(tc):
    tc = copy.deepcopy(tc)
    tc['covers'] = [RETIRED.get(c, c) for c in tc['covers']]
    if tc['slug'] in VERSION_TESTS:
        value, description = VERSION_TESTS[tc['slug']]
        tc['inp']['floorspec'] = value
        tc['description'] = description or tc['description']
    elif isinstance(tc['inp'], dict) and tc['inp'].get('floorspec') == '0.1':
        tc['inp']['floorspec'] = '0.2'
    if tc['raw'] is not None:
        tc['raw'] = _RAW_VERSION.sub(rb'\1"0.2"', tc['raw'])
    return tc


BASE = [retarget(tc) for tc in TESTS]
del TESTS[:]


# ============================================================================= helpers

def v2(d):
    d = copy.deepcopy(d)
    d['floorspec'] = '0.2'
    return d


def room_doc(**extra):
    return v2(v01.room_doc(**extra))


def setp(d, path, v):
    return v01.setp(d, path, v)


def drop(d, path):
    return v01.drop(d, path)


def merge(d, **members):
    d = copy.deepcopy(d)
    for k, v in members.items():
        if k in d and isinstance(d[k], dict) and isinstance(v, dict):
            d[k] = {**d[k], **v}
        else:
            d[k] = v
    return d


def ldoc(**members):
    return v2(level_doc(**members))


# ---- the grid house: four rooms, 4 m x 3 m each, around a centre junction J11
GX, GY = [0, 4000 * MM, 8000 * MM], [0, 3000 * MM, 6000 * MM]
INNER = {'EV1': ('J10', 'J11'), 'EV2': ('J11', 'J12'), 'EH1': ('J01', 'J11'), 'EH2': ('J11', 'J21')}
ROOMS = {'RSW': (2000, 1500), 'RSE': (6000, 1500), 'RNW': (2000, 4500), 'RNE': (6000, 4500)}
ROOM_AREA = 3900 * 2900 * 1280 * 1280                  # each room's net area inside 100 mm centred walls


def grid(separators=(), briefs=None, program=None, openings=None, types=None, functions=None):
    """Junctions J00..J22; outer walls WO0..WO7 drawn clockwise; inner edges EV1 (RSW|RSE), EV2
    (RNW|RNE), EH1 (RSW|RNW), EH2 (RSE|RNE) - walls, or separators when named in `separators`."""
    js = {f'J{i}{j}': J(GX[i], GY[j]) for i in range(3) for j in range(3)}
    outer = ['J00', 'J01', 'J02', 'J12', 'J22', 'J21', 'J20', 'J10']
    ws = {f'WO{k}': W(outer[k], outer[(k + 1) % 8]) for k in range(8)}
    seps = {}
    for name, (a, b) in INNER.items():
        if name in separators:
            seps[name] = S(a, b)
        else:
            ws[name] = W(a, b)
    rooms = {}
    for rid, (x, y) in ROOMS.items():
        r = R(x * MM, y * MM)
        if functions and rid in functions:
            r['function'] = functions[rid]
        if briefs and rid in briefs:
            r['brief'] = briefs[rid]
        rooms[rid] = r
    d = ldoc(junctions=js, walls=ws, rooms=rooms)
    if seps:
        d['separators'] = seps
    if openings:
        d['openings'] = openings
    if types:
        d['types'] = {**d['types'], **types}
    if program is not None:
        d['program'] = program
    return d


DOOR = {'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM}
WINDOW = {'kind': 'windowType', 'width': 1200 * MM, 'height': 1200 * MM, 'sill': 900 * MM}


def door_on(wall, fill='D', offset=1000 * MM, **kw):
    o = {'wall': wall, 'offset': offset, **kw}
    if fill is not None:
        o['fill'] = fill
    else:
        o.update(width=900 * MM, height=2100 * MM)
    return o


def item(function, **kw):
    return {'function': function, **kw}


def adj(a, b, kind, **kw):
    return {'a': a, 'b': b, 'kind': kind, **kw}


NOENTRY = ('FS-LINT-014', ['B1'])                      # a door, but no way in (14.4)


def house_program(**kw):
    """The grid house as a three-item brief: two bedrooms (west), a kitchen (south-east) and a dining
    room (north-east), with a separator between kitchen and dining and a door from bedroom to kitchen.
    It has no door to the outside, so a 0.2 validator reports FS-LINT-014 for its building (14.4)."""
    items = {'BED': item('sleeping', name='Bedroom', count=2, minArea=11 * M2, targetArea=12 * M2),
             'KIT': item('kitchen', level='L1'), 'DIN': item('dining')}
    adjacency = [adj('KIT', 'DIN', 'required'), adj('BED', 'KIT', 'preferred', weight=8), adj('DIN', 'BED', 'preferred')]
    program = {'items': items, 'adjacency': adjacency}
    program.update(kw)
    return grid(separators=('EH2',), briefs={'RSW': 'BED', 'RNW': 'BED', 'RSE': 'KIT', 'RNE': 'DIN'},
                functions={'RSW': 'sleeping', 'RNW': 'sleeping', 'RSE': 'kitchen', 'RNE': 'dining'},
                program=program, openings={'O1': door_on('EV1')}, types={'D': DOOR})


def one_per_room(adjacency, **gridkw):
    """One item per room of the grid house (SW, SE, NW, NE), with the given adjacencies."""
    items = {k: item('living') for k in ('SW', 'SE', 'NW', 'NE')}
    return grid(briefs={'RSW': 'SW', 'RSE': 'SE', 'RNW': 'NW', 'RNE': 'NE'},
                program={'items': items, 'adjacency': adjacency}, **gridkw)


# ---- extension elements
FURN = 'FS_furniture'


def element(level='L1', size=(600 * MM, 600 * MM, 900 * MM), origin=(0, 0, 0), host=None, clearances=None, **kw):
    lo = list(origin)
    hi = [origin[i] + size[i] for i in range(3)]
    e = {'fallback': {'level': level, 'box': {'min': lo, 'max': hi}}}
    if host is not None:
        e['host'] = host
    if clearances is not None:
        e['clearances'] = clearances
    e.update(kw)
    return e


def with_elements(d, elements, ext=FURN, coll='pieces', version='0.1', data=None):
    d = copy.deepcopy(d)
    d.setdefault('extensionsUsed', {})[ext] = version
    payload = dict(data or {})
    payload['collections'] = {coll: elements}
    d.setdefault('extensions', {})[ext] = payload
    return d


def free(x, y, rotation=None, level='L1'):
    h = {'mode': 'free', 'level': level, 'position': [x, y]}
    if rotation is not None:
        h['rotation'] = rotation
    return h


def wall_face(wall, side, offset, height):
    return {'mode': 'wallFace', 'wall': wall, 'side': side, 'offset': offset, 'height': height}


def surface(room, position, which='floor', rotation=None):
    h = {'mode': 'surface', 'room': room, 'surface': which, 'position': list(position)}
    if rotation is not None:
        h['rotation'] = rotation
    return h


def env(purpose, lo, hi):
    return {'purpose': purpose, 'shape': 'box', 'min': list(lo), 'max': list(hi)}


def swing(w=900 * MM, h=2100 * MM):
    """A door swing envelope (13.5): forward 0..w, left -w/2..w/2, floor to head."""
    return env('swing', (0, -w // 2, 0), (w, w // 2, h))


# ---- registry entries (12.2)
def entry(name, version, requires=None, kinds=None, terms=None, status='draft', **kw):
    e = {'name': name, 'version': version, 'status': status,
         'schema': f'https://example.com/floorspec/{name}/{version}/schema.json'}
    if requires is not None:
        e['requires'] = requires
    if kinds is not None:
        e['kinds'] = kinds
    if terms is not None:
        e['terms'] = terms
    e.update(kw)
    return e


LIGHTING = entry('EXT_lighting', '1.2.0', kinds={'fixtures': {'title': 'Light fixture', 'fallback': {'symbol': True}}})
ELECTRICAL = entry('EXT_electrical', '2.0.0', requires={'EXT_lighting': '^1.1.0'},
                   kinds={'outlets': {'title': 'Outlet'}, 'panels': {'title': 'Panel', 'fallback': {'asset': True}}},
                   terms={'roomFunctions': ['electricalRoom']})
KNOWN = [LIGHTING, ELECTRICAL]


def uses(d, **versions):
    d = copy.deepcopy(d)
    d.setdefault('extensionsUsed', {}).update({k: v for k, v in versions.items()})
    return d


def requires_doc(rng, used, ext_version='1.0.0'):
    """A document using EXT_a (whose entry requires EXT_b at `rng`) and EXT_b at `used`."""
    reg = [entry('EXT_a', ext_version, requires={'EXT_b': rng}), entry('EXT_b', '9.9.9')]
    return v2(doc(extensionsUsed={'EXT_a': ext_version, 'EXT_b': used})), reg


GLB = {'path': 'models/sofa.glb', 'sha256': 'ab' * 32, 'mediaType': 'model/gltf-binary'}
SVG = {'path': 'symbols/sofa.svg', 'sha256': 'cd' * 32, 'mediaType': 'image/svg+xml'}

# =================================================================================== model (0.2)
NEW = []


def n(*args, **kw):
    """Declares a new 0.2 test."""
    t(*args, **kw)


n('model', 'read-0.1-document', 'The Phase 1 three-room house exactly as the 0.1 suite has it, declaring "0.1", read by '
  'a reader of 0.2: valid, with the same diagnostics, derived values, hash and canonical form as in the 0.1 suite '
  '(examples/001), and nothing derived for a program, hosts or clearances.', ['1.2.2', '1.2.4', '9.2.1', '9.3.1'],
  None, [], raw=v01.raw_h.encode())
n('model', '0.1-document-with-program', 'A document that declares "0.1" and has a program, which 0.2 adds: it is '
  'checked against Core 0.1\'s schema, which has no "program" member.', ['1.2.4'],
  setp(v01.room_doc(), ['program'], {'items': {'K': {'function': 'kitchen'}}}), SCH)
n('model', '0.1-document-with-brief', 'A 0.1 document whose room names a program item: "brief" is a 0.2 member.',
  ['1.2.4'], setp(v01.room_doc(), ['rooms', 'R1', 'brief'], 'K'), SCH)
n('model', '0.1-document-with-declaration-object', 'A 0.1 document declaring an extension with a declaration object, '
  'which 0.2 adds.', ['1.2.4'], doc(extensionsUsed={'EXT_acoustics': {'version': '1.0'}}), SCH)
d = v01.baseline()
d['openings']['O1'] = {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'D'}
d['types']['D'] = {**DOOR, 'clearances': {'swing': swing()}}
n('model', '0.1-document-with-clearances', 'A 0.1 document whose door type declares clearances, which 0.2 adds.',
  ['1.2.4'], d, SCH)
d = v01.baseline()
d['extensionsUsed'] = {FURN: '0.1'}
d['extensions'] = {FURN: {'collections': {'pieces': {'SOFA': {'fallback': 'not a fallback', 'size': [1, 2]}}, 'other': 7}}}
n('model', '0.1-collections-are-opaque', 'A 0.1 document whose top-level extension data has a member named '
  '"collections" that would be malformed in 0.2. In a 0.1 document extension data is opaque, so it is valid, the '
  'ID "SOFA" is not an element, and nothing is derived from it: it reads exactly as in 0.1.', ['1.2.4', '1.6.9'], d)
d = room_doc()
d['extensionsUsed'] = {FURN: '0.1'}
d['extensions'] = {FURN: {'collections': {'pieces': {'SOFA': {'fallback': 'not a fallback'}}}}}
n('model', 'collections-checked-in-0.2', 'The same data in a 0.2 document: "collections" holds extension elements, '
  'and this one\'s fallback is not a fallback.', ['12.5.2'], d, SCH)
n('model', 'version-0.2-with-everything', 'A 0.2 document using every member 0.2 adds - a program and a brief, a '
  'declaration object, door clearances, and an extension element with a host - each written with its defaults, so '
  'the canonical form shows which are omitted: count 1, weight 5, empty clearances and the declaration object '
  'without a schema are; the extension element, which is extension data, is not changed at all.',
  ['1.2.3', '1.5.1', '9.2.1', '9.2.2', '12.1.3'],
  with_elements(merge(room_doc(), program={'items': {'K': item('kitchen', count=1, extensions={}, extras={})},
                                           'adjacency': []},
                      rooms={'R1': {**v01.room_doc()['rooms']['R1'], 'brief': 'K'}},
                      types={'WT': v01.room_doc()['types']['WT'], 'D': {**DOOR, 'clearances': {}}},
                      openings={'O1': door_on('W4')}),
                {'SOFA': element(host=free(CX, CY, rotation=0), extras={})}, version={'version': '0.1'}))

d = level_doc(junctions={'J1': J(0, 0), 'J2': J(0, Y), 'J3': J(X, Y), 'J4': J(X, 0), 'J5': J(2 * X, Y), 'J6': J(2 * X, 0)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J1'),
                     'W5': W('J3', 'J5'), 'W6': W('J5', 'J6'), 'W7': W('J6', 'J4')},
              rooms={'R1': R(CX, CY), 'R2': R(X + CX, CY)},
              openings={'O1': {'wall': 'W3', 'offset': 1000 * MM, 'width': 900 * MM, 'height': 2100 * MM}})
n('model', 'read-0.1-document-circulation', 'A 0.1 document of two rooms with a cased opening between them and no '
  'way in, read by a reader of 0.2: circulation needs no member 0.2 adds, so it is derived for the 0.1 document too, '
  'and its building has no entry (FS-LINT-014). As a 0.1 document it has no diagnostics.', ['1.2.4', '14.3.1'], d,
  [('FS-LINT-014', ['B1'])])

# =================================================================================== identity (0.2)
d = setp(room_doc(), ['program'], {'items': {'R1': item('kitchen')}})
n('identity', 'program-item-id-collides', 'A program item with the ID of a room: items share the document\'s space of '
  'IDs, so FS-INV-001 names the ID.', ['3.1.3', '3.1.2', '10.2.1'], d, [('FS-INV-001', ['R1'])])
d = with_elements(room_doc(), {'W1': element()})
n('identity', 'extension-element-id-collides', 'An extension element with the ID of a wall: FS-INV-001.',
  ['3.1.3'], d, [('FS-INV-001', ['W1'])])
d = with_elements(room_doc(), {'SOFA': element()})
d['extensions'][FURN]['collections']['rugs'] = {'SOFA': element()}
n('identity', 'id-in-two-extension-collections', 'Two collections of one extension with an element each, both '
  'called SOFA: FS-INV-001.', ['3.1.3'], d, [('FS-INV-001', ['SOFA'])])
d = setp(room_doc(), ['program'], {'items': {'-K': item('kitchen')}})
n('identity', 'program-item-id-pattern', 'A program item ID starting with "-" does not match the ID pattern.',
  ['3.1.3'], d, SCH)
n('identity', 'extension-element-id-pattern', 'An extension element ID with a space does not match the ID pattern.',
  ['3.1.3'], with_elements(room_doc(), {'SOFA 1': element()}), SCH)
d = setp(room_doc(), ['rooms', 'R1', 'brief'], 'KIT')
n('identity', 'brief-dangling', 'A room\'s brief names a program item that does not exist (the document has no '
  'program): FS-INV-002 names the room.', ['3.2.1', '10.2.1'], d, [('FS-INV-002', ['R1'])])
d = setp(room_doc(), ['program'], {'items': {'K': item('kitchen')}})
d['rooms']['R1']['brief'] = 'W1'
n('identity', 'brief-names-a-wall', 'A room\'s brief names a wall: it must resolve to a program item.', ['3.2.1'], d,
  [('FS-INV-002', ['R1'])])
d = setp(room_doc(), ['program'], {'items': {'K': item('kitchen', level='L9')}})
n('identity', 'item-level-dangling', 'A program item\'s preferred level does not exist: FS-INV-002 names the item.',
  ['3.2.1'], d, [('FS-INV-002', ['K'])])
d = setp(room_doc(), ['program'], {'items': {'K': item('kitchen')}, 'adjacency': [adj('K', 'D', 'required')]})
n('identity', 'adjacency-dangling', 'An adjacency names an item D that does not exist: FS-INV-002 with no element, '
  'since an adjacency is not an element.', ['3.2.1'], d, [('FS-INV-002', [])])
d = setp(room_doc(), ['program'], {'items': {'K': item('kitchen')}, 'adjacency': [adj('R1', 'K', 'required')]})
n('identity', 'adjacency-names-a-room', 'An adjacency names the room R1 instead of an item.', ['3.2.1'], d,
  [('FS-INV-002', [])])
d = v2(v01.room_doc())
d['separators'] = {'S1': S('J1', 'J3')}
d = with_elements(d, {'OUTLET': element(host=wall_face('S1', 'left', 1000 * MM, 300 * MM))})
n('identity', 'host-wall-is-a-separator', 'A wall-face host on a separator: host.wall must resolve to a wall. (The '
  'separator also splits the room\'s face; R1 is in one half.)', ['3.2.1'], d, [('FS-INV-002', ['OUTLET'])])
n('identity', 'host-room-dangling', 'A surface host on a room that does not exist.', ['3.2.1'],
  with_elements(room_doc(), {'WC': element(host=surface('R9', (CX, CY)))}), [('FS-INV-002', ['WC'])])
n('identity', 'host-level-dangling', 'A free host on a level that does not exist.', ['3.2.1'],
  with_elements(room_doc(), {'SOFA': element(host=free(CX, CY, level='L9'))}), [('FS-INV-002', ['SOFA'])])
n('identity', 'fallback-level-dangling', 'A fallback on a level that does not exist.', ['3.2.1'],
  with_elements(room_doc(), {'SOFA': element(level='L9')}), [('FS-INV-002', ['SOFA'])])
e = element()
e['fallback']['asset'] = 'GLB'
e['fallback']['symbol'] = 'R1'
n('identity', 'fallback-asset-and-symbol-dangling', 'A fallback whose asset does not exist and whose symbol names a '
  'room: one FS-INV-002 for each.', ['3.2.1', '10.2.1'], with_elements(room_doc(), {'SOFA': e}),
  [('FS-INV-002', ['SOFA']), ('FS-INV-002', ['SOFA'])])

# =================================================================================== program
n('program', 'house-brief', 'The grid house - four 4 m by 3 m rooms of 100 mm walls around a centre junction - '
  'against a brief: two bedrooms of at least 11 m2 (each has 11.31 m2, so minAreaMet; the 12 m2 target is not '
  'met), a kitchen (preferred on L1) and a dining room. The kitchen and dining room are divided by a separator, and a '
  'door joins a bedroom to the kitchen. KIT-DIN is adjacent and connected (the separator); BED-KIT is adjacent and '
  'connected (the door on EV1); DIN-BED is adjacent across the wall EV2, which has no opening, so it is not '
  'connected. No program lint is reported. The house has a door but none to the outside, so its building has no '
  'entry (FS-LINT-014, 14.4).',
  ['11.1.1', '11.3.1', '11.4.1', '6.4.1'], house_program(), [NOENTRY])
d = house_program()
d['program']['items']['KIT'].update(count=1, extensions={}, extras={})
d['program']['adjacency'][0]['weight'] = 5
n('program', 'defaults-explicit', 'program/001 with an item\'s count 1, empty extensions and extras, and an '
  'adjacency\'s weight 5 written out: the same derived values and hash as program/001, and a canonical form without '
  'them.', ['1.5.1', '9.2.1', '9.2.2', '11.1.1'], d, [NOENTRY])
d = house_program()
d['program']['items']['BED']['count'] = 3
n('program', 'count-unmet', 'The brief asks for three bedrooms and the plan has two: countMet is false and '
  'FS-LINT-008 names the item. The document stays valid: an unmet brief is a lint, never an error.',
  ['11.3.1', '11.5.2', '10.1.1'], d, [('FS-LINT-008', ['BED']), NOENTRY])
d = house_program()
d['program']['items']['BED']['minArea'] = 12 * M2
n('program', 'below-minimum-area', 'Bedrooms of at least 12 m2: both have 11.31 m2, so minAreaMet is false and '
  'FS-LINT-009 is reported once for each room, naming the item and the room.', ['11.3.1', '11.5.2'], d,
  [('FS-LINT-009', ['BED', 'RNW']), ('FS-LINT-009', ['BED', 'RSW']), NOENTRY])
d = house_program()
d['program']['items']['BED'].update(minArea=ROOM_AREA, targetArea=ROOM_AREA + 1)
n('program', 'area-compared-exactly', 'A minimum area exactly equal to each bedroom\'s net area (18,530,304,000,000 '
  'square base units) is met; a target one square base unit more is not.', ['11.3.1'], d, [NOENTRY])
d = house_program()
d['program']['items']['STO'] = item('storage', minArea=2 * M2, targetArea=3 * M2)
n('program', 'item-without-rooms', 'A storage item no room fulfils: countMet is false (FS-LINT-008), and minAreaMet '
  'and targetAreaMet are true, because every one of its rooms - there are none - meets them.', ['11.3.1'], d,
  [('FS-LINT-008', ['STO']), NOENTRY])
d = house_program()
d['rooms']['RNE']['brief'] = 'KIT'
d['program']['items']['KIT']['count'] = 1
n('program', 'more-rooms-than-count', 'Two rooms fulfil the kitchen item, which asks for one: an item with more rooms '
  'than its count meets it. DIN has no room, so its count is unmet and its adjacencies are not adjacent.',
  ['11.3.1', '11.4.1'], d, [('FS-LINT-008', ['DIN']), ('FS-LINT-010', ['DIN', 'KIT']), NOENTRY])
d = one_per_room([adj('SW', 'NE', 'required'), adj('SE', 'NW', 'preferred')])
n('program', 'diagonal-rooms-not-adjacent', 'Rooms that meet only at the centre junction J11 share no edge, so they '
  'are not adjacent: the required SW-NE adjacency is unmet (FS-LINT-010) and the preferred SE-NW one is unmet '
  'without a lint.', ['11.4.1', '11.5.2'], d, [('FS-LINT-010', ['NE', 'SW'])])
d = one_per_room([adj('SE', 'NE', 'forbidden'), adj('SW', 'NW', 'forbidden'), adj('SW', 'NE', 'forbidden')],
                 separators=('EH2',))
n('program', 'forbidden-adjacency-present', 'SE and NE are divided by a separator and SW and NW by a wall: both '
  'forbidden adjacencies are present (FS-LINT-011), whatever divides the rooms. SW and NE are not adjacent.',
  ['11.4.1', '11.5.2'], d, [('FS-LINT-011', ['NE', 'SE']), ('FS-LINT-011', ['NW', 'SW'])])
d = one_per_room([adj('SW', 'SE', 'preferred'), adj('NW', 'NE', 'preferred'), adj('SW', 'NW', 'preferred'),
                  adj('SE', 'NE', 'preferred'), adj('NE', 'SW', 'preferred')],
                 separators=('EH2',),
                 openings={'O1': door_on('EV1'), 'O2': door_on('EV2', fill='WIN'), 'O3': door_on('EH1', fill=None)},
                 types={'D': DOOR, 'WIN': WINDOW})
n('program', 'adjacent-and-connected', 'One item per room, every pair of neighbours related: SW-SE share the wall '
  'EV1, which has a door (connected); NW-NE share EV2, which has only a window (adjacent, not connected); SW-NW '
  'share EH1, which has an empty, cased opening (connected); SE-NE share the separator EH2 (connected). NE-SW meet '
  'only at a junction: neither adjacent nor connected. No door leads outside (FS-LINT-014).', ['11.4.1'], d,
  [NOENTRY])
two = ldoc(levels={'L2': {'building': 'B1', 'elevation': H, 'height': H}})
ja, wa = box('A', 0, 0, X, Y)
jb, wb = box('B', 0, 0, X, Y, level='L2')
d = merge(two, junctions={**ja, **jb}, walls={**wa, **wb},
          rooms={'R1': R(CX, CY, brief='LIV'), 'R2': R(CX, CY, level='L2', brief='BED')},
          program={'items': {'LIV': item('living'), 'BED': item('sleeping', level='L2')},
                   'adjacency': [adj('LIV', 'BED', 'forbidden')]})
n('program', 'rooms-on-two-levels', 'A living room on L1 and a bedroom directly above it on L2: rooms on different '
  'levels are never adjacent, so the forbidden adjacency is met.', ['11.4.1'], d)
d = house_program()
d['program']['adjacency'] = [adj('KIT', 'DIN', 'required'), adj('DIN', 'KIT', 'preferred', weight=1)]
n('program', 'required-and-preferred-on-one-pair', 'A pair with both a required and a preferred adjacency: redundant, '
  'not contradictory, so valid; both are derived, in order.', ['11.2.3', '11.4.1'], d, [NOENTRY])
d = house_program()
d['program']['adjacency'].append(adj('KIT', 'KIT', 'required'))
n('program', 'self-adjacency', 'An adjacency relating the kitchen to itself: FS-INV-401 names the item.',
  ['11.2.1', '10.2.1'], d, [('FS-INV-401', ['KIT'])])
d = house_program()
d['program']['adjacency'] += [adj('KIT', 'KIT', 'forbidden'), adj('KIT', 'KIT', 'forbidden')]
n('program', 'self-adjacency-twice', 'Two identical self-adjacencies: FS-INV-401 for each, and FS-INV-402 is not '
  'evaluated for an adjacency that has FS-INV-401.', ['11.2.1', '10.3.1'], d,
  [('FS-INV-401', ['KIT']), ('FS-INV-401', ['KIT'])])
d = house_program()
d['program']['adjacency'].append(adj('DIN', 'KIT', 'required', weight=9))
n('program', 'duplicate-adjacency', 'KIT-DIN required is repeated as DIN-KIT required: the pair is undirected, so it '
  'is the same pair and kind. FS-INV-402 is reported once, for the later adjacency, naming both items.',
  ['11.2.2', '10.2.1'], d, [('FS-INV-402', ['DIN', 'KIT'])])
d = house_program()
d['program']['adjacency'].append(adj('DIN', 'KIT', 'forbidden'))
n('program', 'required-and-forbidden', 'A pair both required and forbidden: FS-INV-403 names both items.',
  ['11.2.3', '10.2.1'], d, [('FS-INV-403', ['DIN', 'KIT'])])
d = house_program()
d['program']['adjacency'].append(adj('KIT', 'BED', 'forbidden'))
n('program', 'preferred-and-forbidden', 'BED-KIT is preferred and also forbidden: a contradiction too, FS-INV-403.',
  ['11.2.3'], d, [('FS-INV-403', ['BED', 'KIT'])])
d = house_program()
d['program']['adjacency'].append(adj('KIT', 'KIT', 'required'))
d['junctions']['JX1'] = J(-1000 * MM, CY)
d['junctions']['JX2'] = J(1000 * MM, CY)
d['walls']['WX'] = W('JX1', 'JX2')
n('program', 'program-error-with-graph-error', 'A self-adjacency and a wall WX crossing the west wall WO0: program '
  'invariants are evaluated whatever the graph, so both FS-INV-104 and FS-INV-401 are reported.', ['10.3.1', '11.2.1'],
  d, [('FS-INV-104', ['WO0', 'WX']), ('FS-INV-401', ['KIT'])])
d = house_program()
d['program']['items']['SPA'] = item('EXT_wellness:sauna')
n('program', 'item-extension-term-undeclared', 'A program item whose function is an extension term of an extension '
  'not in extensionsUsed: FS-INV-006 names the item.', ['11.1.2', '4.2.1', '10.2.1'], d,
  [('FS-INV-006', ['SPA']), ])
d = house_program()
d['program']['items']['SPA'] = item('EXT_wellness:sauna', count=0 + 1)
d['extensionsUsed'] = {'EXT_wellness': '1.0'}
n('program', 'item-extension-term-declared', 'The same item with EXT_wellness declared: valid. No room fulfils it, so '
  'its count is unmet.', ['11.1.2'], d, [('FS-LINT-008', ['SPA']), NOENTRY])
d = house_program()
d['program']['items']['KIT']['extensions'] = {'EXT_kitchens': {'island': True}}
n('program', 'item-extension-data-undeclared', 'A program item carrying data of an undeclared extension: FS-INV-005 '
  'names the item.', ['1.6.3'], d, [('FS-INV-005', ['KIT'])])
for slug, path, value, why in [
    ('count-zero', ['program', 'items', 'BED', 'count'], 0, 'An item\'s count is at least 1.'),
    ('weight-zero', ['program', 'adjacency', 0, 'weight'], 0, 'An adjacency\'s weight is from 1 to 10: 0 is out.'),
    ('weight-eleven', ['program', 'adjacency', 0, 'weight'], 11, 'An adjacency\'s weight of 11 is out of range.'),
    ('target-area-zero', ['program', 'items', 'BED', 'targetArea'], 0, 'An area is at least 1 square base unit.'),
    ('min-area-beyond-2-53', ['program', 'items', 'BED', 'minArea'], 2 ** 53, 'An area is at most 2^53 - 1.'),
    ('kind-unknown', ['program', 'adjacency', 0, 'kind'], 'adjacent', '"adjacent" is not an adjacency kind.'),
    ('item-function-unknown', ['program', 'items', 'BED', 'function'], 'bedroom', '"bedroom" is not a room function.'),
    ('item-unknown-member', ['program', 'items', 'KIT', 'rooms'], ['RSE'], 'An item does not list its rooms; rooms '
     'name their item.'),
    ('adjacency-unknown-member', ['program', 'adjacency', 0, 'distance'], 1000, 'An adjacency has no "distance".'),
    ('program-unknown-member', ['program', 'solver'], 'genetic', 'A program has only items and adjacency.'),
]:
    d = house_program()
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value
    n('program', slug, why, ['11.1.1'], d, SCH)
d = house_program()
del d['program']['items']['DIN']['function']
n('program', 'item-without-function', 'Every program item has a function.', ['11.1.1'], d, SCH)
d = house_program()
del d['program']['adjacency'][1]['kind']
n('program', 'adjacency-without-kind', 'Every adjacency has a kind.', ['11.1.1'], d, SCH)
d = house_program()
d['program']['adjacency'] = {'KIT': 'DIN'}
n('program', 'adjacency-not-an-array', 'The adjacency graph is an array of adjacencies.', ['11.1.1'], d, SCH)
d = house_program()
d['program']['items']['BED']['targetArea'] = 1.5e13
n('program', 'area-not-an-integer', 'An area is a JSON integer: 1.5e13 is written with an exponent.', ['11.1.1'], d, SCH)

# =================================================================================== extensions: declarations
d = v2(v01.baseline())
d['extensionsUsed'] = {'EXT_acoustics': {'version': '2.1'}}
d['walls']['W1']['extensions'] = {'EXT_acoustics': {'stc': 52}}
n('extensions', 'declaration-object-without-schema', 'EXT_acoustics declared as { "version": "2.1" }: the same '
  'declaration as the string "2.1", so the canonical form writes the string, and the hash is that of '
  'extensions/002.', ['12.1.1', '12.1.3', '9.2.1'], d)
d = copy.deepcopy(d)
d['extensionsUsed'] = {'EXT_acoustics': '2.1'}
n('extensions', 'declaration-string', 'extensions/001 with EXT_acoustics declared as the string "2.1": the same hash '
  'and canonical form as extensions/001.', ['12.1.3', '9.3.1'], d)
d = copy.deepcopy(d)
d['extensionsUsed'] = {'EXT_acoustics': {'version': '2.1', 'schema': 'https://example.com/ext/acoustics/2.1/schema.json'}}
n('extensions', 'declaration-object-with-schema', 'A declaration with a schema URL: the canonical form keeps the '
  'object, and the schema changes nothing a reader derives: walls, rooms and openings as extensions/001.',
  ['12.1.1', '12.1.2', '12.1.3', '9.2.1'], d)
for slug, decl, why, covers in [
    ('declaration-unknown-member', {'version': '2.1', 'required': True}, 'A declaration has only version and schema.', ['12.1.1']),
    ('declaration-without-version', {'schema': 'https://example.com/s.json'}, 'A declaration always has a version.', ['12.1.1']),
    ('declaration-version-pattern', {'version': 'v2'}, 'A declaration\'s version matches the version pattern.', ['1.6.7', '12.1.1']),
    ('declaration-schema-not-https', {'version': '2.1', 'schema': 'http://example.com/s.json'}, 'A schema URL is https.', ['12.1.2']),
    ('declaration-schema-relative', {'version': '2.1', 'schema': 'schema.json'}, 'A schema URL is absolute.', ['12.1.2']),
    ('declaration-array', ['2.1'], 'A declaration is a string or an object, not an array.', ['12.1.1']),
]:
    n('extensions', slug, why, covers, v2(doc(extensionsUsed={'EXT_acoustics': decl})), SCH)
n('extensions', 'required-with-declaration-object', 'A required extension declared with a declaration object, which '
  'the reader does not implement: FS-DOC-002, exactly as for a version string.', ['1.6.4', '12.1.3'],
  v2(doc(extensionsUsed={'EXT_acoustics': {'version': '1.0', 'schema': 'https://example.com/a.json'}},
         extensionsRequired=['EXT_acoustics'])), [('FS-DOC-002', [])])

# =================================================================================== extensions: elements and fallbacks
n('extensions', 'element-unhosted', 'An FS_furniture sofa with only a fallback: a 2 m by 900 mm by 800 mm box in L1\'s '
  'frame, 1 m east and 500 mm north of project zero. A reader that does not implement FS_furniture derives its '
  'fallback - footprint, bottom and top - and nothing else.', ['12.5.1', '12.5.2', '12.6.2', '1.6.9', '13.1.1'],
  with_elements(room_doc(), {'SOFA': element(size=(2000 * MM, 900 * MM, 800 * MM), origin=(1000 * MM, 500 * MM, 0))}))
lev = ldoc(levels={'L2': {'building': 'B1', 'elevation': 3000 * MM, 'height': H}})
n('extensions', 'element-on-a-raised-level', 'A fallback on L2, whose elevation is 3000 mm: its box\'s z is relative '
  'to the level datum, so bottom and top are 3000 mm higher than the box\'s own z.', ['12.6.2', '13.1.1'],
  with_elements(v2(v01.no_wt(level_doc(levels={'L2': {'building': 'B1', 'elevation': 3000 * MM, 'height': H}}))),
                {'LAMP': element(level='L2', size=(400 * MM, 400 * MM, 1600 * MM), origin=(-200 * MM, -200 * MM, 100 * MM))}))
sofa = element(host=free(CX, CY), catalogue='Bauhaus three-seat', level_='L9', position=[0, 0], anchor=[0, 0],
               fallbackScale=2.5, colour={'r': 0.5})
n('extensions', 'element-members-of-the-extension', 'A sofa whose extension-defined members are named like core '
  'members (level_, position, anchor) or hold non-integer numbers, beside top-level data of the extension\'s own: '
  'core neither checks nor reads them, derives the same as for the bare element, and the canonical form keeps all of '
  'it, unchanged.', ['1.6.6', '1.6.9', '12.5.2', '9.2.1'],
  with_elements(room_doc(), {'SOFA': sofa}, data={'style': 'mid-century', 'scale': 0.75}))
n('extensions', 'element-without-fallback', 'Every extension element has a fallback.', ['12.5.2'],
  with_elements(room_doc(), {'SOFA': {'host': free(CX, CY)}}), SCH)
d = with_elements(room_doc(), {'SOFA': element()})
d['extensions'][FURN]['collections'] = {'Pieces': d['extensions'][FURN]['collections']['pieces']}
n('extensions', 'collection-name-pattern', 'A collection name starts with a lowercase letter: "Pieces" does not.',
  ['12.5.1'], d, SCH)
d = with_elements(room_doc(), {'SOFA': element()})
d['extensions'][FURN]['collections'] = [element()]
n('extensions', 'collections-not-an-object', '"collections" is an object of collections, not an array.', ['12.5.1'], d, SCH)
n('extensions', 'element-not-an-object', 'An extension element is an object.', ['12.5.1'],
  with_elements(room_doc(), {'SOFA': 'sofa'}), SCH)
e = element()
e['fallback']['colour'] = '#ffffff'
n('extensions', 'fallback-unknown-member', 'A fallback has only level, box, asset and symbol.', ['12.5.2'],
  with_elements(room_doc(), {'SOFA': e}), SCH)
e = element()
del e['fallback']['level']
n('extensions', 'fallback-without-level', 'A fallback always names its level.', ['12.5.2'],
  with_elements(room_doc(), {'SOFA': e}), SCH)
n('extensions', 'element-name-empty', 'An extension element\'s name is 1 to 200 characters.', ['12.5.2'],
  with_elements(room_doc(), {'SOFA': element(name='')}), SCH)
n('extensions', 'element-clearances-malformed', 'An extension element\'s clearances are a clearances object: here an '
  'array.', ['12.5.2', '13.5.1'], with_elements(room_doc(), {'SOFA': element(clearances=[swing()])}), SCH)
d = with_elements(room_doc(), {'SOFA': element()})
d['extensions'][FURN] = [1, 2, 3]
n('extensions', 'data-not-an-object', 'Top-level extension data may be any JSON; only an object\'s "collections" '
  'member holds elements. An array has none.', ['12.5.1'], d)
e = element()
e['fallback'].update(asset='GLB', symbol='SVG')
d = with_elements(merge(room_doc(), assets={'GLB': GLB, 'SVG': SVG}), {'SOFA': e})
n('extensions', 'fallback-asset-and-symbol', 'A fallback with a glTF binary model and an SVG symbol: valid. The '
  'assets are referred to, so FS-LINT-006 does not name them.', ['12.6.1', '12.6.2'], d)
e = element()
e['fallback']['asset'] = 'PNG'
d = with_elements(merge(room_doc(), assets={'PNG': {**GLB, 'path': 'a.png', 'mediaType': 'image/png'}}), {'SOFA': e})
n('extensions', 'fallback-asset-not-gltf', 'A fallback asset that is a PNG image, not a glTF model: FS-INV-506.',
  ['12.6.1', '10.2.1'], d, [('FS-INV-506', ['SOFA'])])
e = element()
e['fallback'].update(asset='GLTF', symbol='GLTF')
d = with_elements(merge(room_doc(), assets={'GLTF': {**GLB, 'path': 'a.gltf', 'mediaType': 'model/gltf+json'}}), {'SOFA': e})
n('extensions', 'fallback-symbol-not-an-image', 'A fallback whose asset and symbol are the same glTF JSON model: '
  'right for the asset, wrong for the symbol, so one FS-INV-506.', ['12.6.1'], d, [('FS-INV-506', ['SOFA'])])
n('extensions', 'top-level-elements-undeclared', 'Extension elements of an extension that extensionsUsed does not '
  'declare: FS-INV-005, and nothing else is evaluated.', ['1.6.3'],
  drop(with_elements(room_doc(), {'SOFA': element()}), ['extensionsUsed']), [('FS-INV-005', [])])

# =================================================================================== extensions: known extensions
elec = lambda **kw: v2(doc(extensionsUsed={'EXT_electrical': '2.0', 'EXT_lighting': '1.2.0', **kw}))
n('extensions', 'dependency-met', 'EXT_electrical 2.0 requires EXT_lighting ^1.1.0, and the document uses '
  'EXT_lighting 1.2.0: valid. "2.0" is known as the entry 2.0.0.', ['12.3.1', '12.3.2', '12.3.3'], elec(), registry=KNOWN)
n('extensions', 'dependency-missing', 'A document using EXT_electrical 2.0 without EXT_lighting, which its entry '
  'requires: FS-INV-601.', ['12.3.2', '10.2.1'], v2(doc(extensionsUsed={'EXT_electrical': '2.0'})),
  [('FS-INV-601', [])], registry=KNOWN)
n('extensions', 'dependency-out-of-range', 'EXT_lighting used at 2.0.0, outside ^1.1.0: FS-INV-602.',
  ['12.3.3', '12.3.1'], elec(EXT_lighting='2.0.0'), [('FS-INV-602', [])], registry=KNOWN)
n('extensions', 'dependency-below-range', 'EXT_lighting used at 1.0, below ^1.1.0: FS-INV-602. (EXT_lighting 1.0 is '
  'not itself known, which changes nothing about EXT_electrical\'s requirement.)', ['12.3.3', '12.3.1'],
  elec(EXT_lighting='1.0'), [('FS-INV-602', [])], registry=KNOWN)
n('extensions', 'unknown-version-not-checked', 'EXT_electrical used at 3.0, a version no known entry describes: the '
  'rules of known extensions do not apply, so its missing dependency is not reported.', ['12.3.2'],
  v2(doc(extensionsUsed={'EXT_electrical': '3.0'})), registry=KNOWN)
for slug, rng, used, ok, why in [
    ('caret-zero-minor-in', '^0.3.1', '0.3.9', True, '^0.3.1 admits 0.3.9: for 0.x, a caret fixes the minor version.'),
    ('caret-zero-minor-out', '^0.3.1', '0.4.0', False, '^0.3.1 does not admit 0.4.0.'),
    ('caret-zero-zero-out', '^0.0.3', '0.0.4', False, '^0.0.3 admits only 0.0.3.'),
    ('tilde-out', '~1.2.0', '1.3.0', False, '~1.2.0 does not admit 1.3.0.'),
    ('tilde-in', '~1.2.0', '1.2.7', True, '~1.2.0 admits 1.2.7.'),
    ('alternatives-gap', '>=1.0.0 <1.2.0 || >=2.0.0', '1.2.0', False, '1.2.0 is in neither set of ">=1.0.0 <1.2.0 || >=2.0.0".'),
    ('alternatives-second', '>=1.0.0 <1.2.0 || >=2.0.0', '2.5', True, '2.5 (read as 2.5.0) satisfies the second set.'),
    ('exact', '1.4.2', '1.4.2', True, 'A comparator without an operator is an exact match.'),
    ('exact-equals-out', '=1.4.2', '1.4.3', False, '"=1.4.2" admits only 1.4.2.'),
    ('prerelease-below-release', '^1.0.0', '1.0.0-beta.2', False, '1.0.0-beta.2 is less than 1.0.0, so outside ^1.0.0.'),
    ('prerelease-of-next-major', '^1.0.0', '2.0.0-rc.1', True, '2.0.0-rc.1 is less than 2.0.0, so inside ^1.0.0: '
     'Floorspec gives prereleases no special treatment.'),
    ('prerelease-precedence', '>1.0.0-alpha.10', '1.0.0-alpha.9', False, 'Numeric prerelease identifiers compare as '
     'numbers: alpha.9 is less than alpha.10.'),
    ('prerelease-alphanumeric', '>1.0.0-alpha.9', '1.0.0-alpha.beta', True, 'An alphanumeric identifier is greater '
     'than a numeric one: alpha.beta is greater than alpha.9.'),
    ('less-or-equal', '<=1.5.0', '1.5.0', True, '<=1.5.0 admits 1.5.0.'),
    ('greater-than-out', '>1.5.0', '1.5', False, '>1.5.0 does not admit 1.5, which is 1.5.0.'),
]:
    d, reg = requires_doc(rng, used)
    n('extensions', f'range-{slug}', f'EXT_a requires EXT_b at "{rng}", and the document uses EXT_b {used}. {why}',
      ['12.3.1', '12.3.3'], d, [] if ok else [('FS-INV-602', [])], registry=reg)
cyc = [entry('EXT_a', '1.0.0', requires={'EXT_b': '^1.0.0'}), entry('EXT_b', '1.0.0', requires={'EXT_c': '^1.0.0'}),
       entry('EXT_c', '1.0.0', requires={'EXT_a': '^1.0.0'})]
n('extensions', 'registry-cycle', 'Known extensions in which EXT_a requires EXT_b, EXT_b requires EXT_c and EXT_c '
  'requires EXT_a: a cycle. The validator reports FS-CFG-001 and nothing else, for any document - here a valid one.',
  ['12.2.1', '12.2.2', '10.1.1'], v2(doc()), [('FS-CFG-001', [])], registry=cyc)
n('extensions', 'registry-cycle-across-versions', 'EXT_a 1.0.0 requires EXT_b, and EXT_b 2.0.0 requires EXT_a: the '
  'relation is between extension names, so this is a cycle although no single version depends on itself.',
  ['12.2.1'], v2(doc()), [('FS-CFG-001', [])],
  registry=[entry('EXT_a', '1.0.0', requires={'EXT_b': '^1.0.0'}), entry('EXT_b', '1.0.0'),
            entry('EXT_b', '2.0.0', requires={'EXT_a': '^1.0.0'})])
n('extensions', 'registry-two-versions', 'Two versions of one extension may both be known: the entry whose version '
  'equals the one the document uses applies - here 1.0.0, which requires nothing.', ['12.2.1', '12.3.2'],
  v2(doc(extensionsUsed={'EXT_a': '1.0'})), registry=[entry('EXT_a', '1.0.0'), entry('EXT_a', '1.1.0', requires={'EXT_b': '^1.0.0'})])
n('extensions', 'registry-duplicate-entry', 'Two known entries for EXT_lighting 1.2.0: FS-CFG-001.', ['12.2.1', '12.2.2'],
  elec(), [('FS-CFG-001', [])], registry=[LIGHTING, {**LIGHTING, 'title': 'Again'}, ELECTRICAL])
n('extensions', 'registry-entry-malformed', 'A known entry whose status, "final", is not a lifecycle stage: '
  'FS-CFG-001.', ['12.2.1', '12.2.2'], elec(), [('FS-CFG-001', [])], registry=[{**LIGHTING, 'status': 'final'}, ELECTRICAL])
n('extensions', 'registry-ratified-needs-two-implementations', 'A ratified entry listing one implementation: '
  'ratification needs two (FLR-ADR-007), so the entry is malformed.', ['12.2.1'], elec(), [('FS-CFG-001', [])],
  registry=[{**LIGHTING, 'status': 'ratified', 'implementations': [{'name': 'D3 Floorspec', 'url': 'https://floorspec.d3cloud.io/'}]},
            ELECTRICAL])
n('extensions', 'registry-ratified', 'A ratified entry with two implementations is well formed.', ['12.2.1'], elec(),
  registry=[{**LIGHTING, 'status': 'ratified', 'implementations': [
      {'name': 'D3 Floorspec', 'url': 'https://floorspec.d3cloud.io/'}, {'name': 'Another', 'url': 'https://example.com/'}]},
      ELECTRICAL])
n('extensions', 'registry-bad-range', 'A known entry whose range "1.x" is not in the range grammar: FS-CFG-001.',
  ['12.2.1', '12.3.1'], elec(), [('FS-CFG-001', [])],
  registry=[LIGHTING, {**ELECTRICAL, 'requires': {'EXT_lighting': '1.x'}}])
n('extensions', 'registry-not-json', 'Known extensions that are not well-formed JSON: FS-CFG-001.', ['12.2.2'], elec(),
  [('FS-CFG-001', [])], registry_raw=b'[{"name": "EXT_lighting",]\n')
n('extensions', 'registry-error-before-parsing', 'A cyclic registry and a document that is not JSON: configuration is '
  'evaluated before parsing, and only FS-CFG-001 is reported.', ['12.2.2', '10.3.1'], None, [('FS-CFG-001', [])],
  raw=b'{"floorspec": "0.2",\n', registry=cyc)
lit = with_elements(room_doc(), {'L1A': element(size=(300 * MM, 300 * MM, 100 * MM), origin=(CX, CY, H - 100 * MM))},
                    ext='EXT_lighting', coll='fixtures', version='1.2.0')
n('extensions', 'kind-requires-symbol', 'EXT_lighting\'s entry requires every element of its "fixtures" kind to carry '
  'a symbol, and this one has none: FS-INV-603.', ['12.4.2', '10.2.1'], lit, [('FS-INV-603', ['L1A'])], registry=KNOWN)
d = merge(lit, assets={'SVG': SVG})
d['extensions']['EXT_lighting']['collections']['fixtures']['L1A']['fallback']['symbol'] = 'SVG'
n('extensions', 'kind-requirement-met', 'The same fixture with a symbol: valid.', ['12.4.2'], d, registry=KNOWN)
d = with_elements(uses(room_doc(), EXT_lighting='1.2.0'), {'P1': element(), 'P2': element(origin=(0, 1000 * MM, 0))},
                  ext='EXT_electrical', coll='panels', version='2.0.0')
n('extensions', 'kind-requires-asset', 'Two panels without the glTF asset EXT_electrical\'s "panels" kind requires: '
  'FS-INV-603 for each.', ['12.4.2'], d, [('FS-INV-603', ['P1']), ('FS-INV-603', ['P2'])], registry=KNOWN)
d = with_elements(uses(room_doc(), EXT_lighting='1.2.0'), {'C1': element()}, ext='EXT_electrical', coll='circuits',
                  version='2.0.0')
n('extensions', 'collection-not-in-entry', 'EXT_electrical data with a "circuits" collection, which its entry does not '
  'name: FS-INV-604.', ['12.4.1', '10.2.1'], d, [('FS-INV-604', [])], registry=KNOWN)
d = uses(room_doc(), EXT_electrical='2.0.0', EXT_lighting='1.2.0')
d['rooms']['R1']['function'] = 'EXT_electrical:serverRoom'
d['program'] = {'items': {'MECH': item('EXT_electrical:electricalRoom'), 'SRV': item('EXT_electrical:serverRoom')}}
n('extensions', 'term-not-in-entry', 'A room and a program item whose function is EXT_electrical:serverRoom, a term '
  'the entry does not list: FS-INV-605 for each. The item whose function is electricalRoom, which is listed, is '
  'valid.', ['12.4.3', '10.2.1'], d, [('FS-INV-605', ['R1']), ('FS-INV-605', ['SRV'])], registry=KNOWN)
d = v2(v01.room_doc())
d['floorspec'] = '0.1'
d['extensionsUsed'] = {'EXT_electrical': '2.0.0'}
n('extensions', 'known-extensions-and-a-0.1-document', 'A document declaring "0.1" that uses EXT_electrical without '
  'its dependency: a 0.2 reader applies 12.3 to it as to any document (1.2.4), so FS-INV-601 is reported.',
  ['1.2.4', '12.3.2'], d, [('FS-INV-601', [])], registry=KNOWN)

# =================================================================================== hosting
WF = 300 * MM           # an outlet's height
n('hosting', 'wall-face-left', 'An outlet on the exterior (left) face of the west wall W1 - which runs north from '
  'J1 at (0, 0) - 1 m along it and 300 mm up. Its frame\'s origin is on the face, 50 mm west of the location line, '
  'and faces west: facing 180,000,000. The fallback box sits in front of the face.',
  ['13.1.1', '13.3.1', '13.4.1', '12.6.2'],
  with_elements(room_doc(), {'OUT': element(size=(30 * MM, 80 * MM, 120 * MM), origin=(0, -40 * MM, 0),
                                            host=wall_face('W1', 'left', 1000 * MM, WF))}, ext='EXT_electrical',
                coll='outlets', version='2.0.0'))
n('hosting', 'wall-face-right', 'The same outlet on W1\'s interior (right) face: origin 50 mm east of the location '
  'line, facing east (0).', ['13.1.1', '13.4.1'],
  with_elements(room_doc(), {'OUT': element(size=(30 * MM, 80 * MM, 120 * MM), origin=(0, -40 * MM, 0),
                                            host=wall_face('W1', 'right', 1000 * MM, WF))}, ext='EXT_electrical',
                coll='outlets', version='2.0.0'))
u = 1280000
obl = ldoc(types={'T5': {'kind': 'wallType', 'layers': [{'thickness': 128005, 'function': 'core'}]}},
           junctions={'J1': J(0, 0), 'J2': J(2 * u, u)}, walls={'W1': W('J1', 'J2', type='T5')})
obl = v2(v01.no_wt(obl))
n('hosting', 'wall-face-oblique', 'A cabinet on the right face of a wall along (2, 1) of odd thickness 128,005: the '
  'origin, 1 m along and half the thickness off the location line, has coordinates in sqrt(5), rounded once; the '
  'facing is the direction of (1, -2), -63.434949 degrees, rounded to the microdegree. The box\'s footprint corners '
  'are rounded once each.', ['13.1.1', '13.4.1', '12.6.2', '2.2.1'],
  with_elements(obl, {'CAB': element(size=(600 * MM, 900 * MM, 720 * MM), origin=(0, -450 * MM, 0),
                                     host=wall_face('W1', 'right', 1000 * MM, 0))}))
d = v2(v01.room_doc())
d['walls']['W1']['justification'] = 'exteriorFace'
n('hosting', 'wall-face-on-justified-wall', 'W1 justified on its exterior face: the left face is the location line '
  '(a = 0), so a left wall-face host\'s origin is on it; the right face is the full 100 mm away.', ['13.1.1', '13.4.1'],
  with_elements(d, {'A': element(host=wall_face('W1', 'left', 500 * MM, WF)),
                    'B': element(host=wall_face('W1', 'right', 500 * MM, WF))}))
n('hosting', 'wall-face-at-wall-end', 'An offset equal to the wall\'s length, 3000 mm, and a height equal to its '
  'height, 2700 mm: both within the wall.', ['13.3.2', '13.3.3'],
  with_elements(room_doc(), {'A': element(host=wall_face('W1', 'right', Y, H))}))
n('hosting', 'wall-face-beyond-length', 'An offset of 3000 mm and one base unit on a 3000 mm wall: FS-INV-501.',
  ['13.3.2', '10.2.1'], with_elements(room_doc(), {'A': element(host=wall_face('W1', 'right', Y + 1, WF))}),
  [('FS-INV-501', ['A'])])
n('hosting', 'wall-face-at-oblique-length', 'On a wall along (3, 4) x 640,000, whose length is exactly 3,200,000: an '
  'offset of 3,200,000 fits, exactly.', ['13.3.2'],
  with_elements(v2(level_doc(junctions={'J1': J(0, 0), 'J2': J(3 * 640000, 4 * 640000)}, walls={'W1': W('J1', 'J2')})),
                {'A': element(host=wall_face('W1', 'left', 3200000, WF))}))
n('hosting', 'wall-face-beyond-irrational-length', 'On a wall along (2, 1) x 1,280,000, whose length is '
  '2,862,167.01...: an offset of 2,862,168 is beyond it, by less than one base unit.', ['13.3.2'],
  with_elements(v2(level_doc(junctions={'J1': J(0, 0), 'J2': J(2 * u, u)}, walls={'W1': W('J1', 'J2')})),
                {'A': element(host=wall_face('W1', 'left', 2862168, WF))}), [('FS-INV-501', ['A'])])
n('hosting', 'wall-face-above-wall', 'A height of 2700 mm and one base unit on a 2700 mm wall: FS-INV-502.',
  ['13.3.3', '10.2.1'], with_elements(room_doc(), {'A': element(host=wall_face('W1', 'right', 1000 * MM, H + 1))}),
  [('FS-INV-502', ['A'])])
d = room_doc()
d['walls']['W1']['top'] = {'height': 0}
n('hosting', 'wall-face-on-wall-without-height', 'A host on W1, whose top is not above its base: FS-INV-112, and '
  'FS-INV-502 is not evaluated for a host wall that has FS-INV-112.', ['10.3.1', '13.3.3'],
  with_elements(d, {'A': element(host=wall_face('W1', 'right', 1000 * MM, H + 1))}), [('FS-INV-112', ['W1'])])
n('hosting', 'surface-floor-rotated', 'A toilet on R1\'s floor at (1 m, 1 m), turned to face north (rotation '
  '90,000,000, facing vector (0, 10^9)): its frame\'s x axis is +Y, so its 700 mm depth runs north and its 400 mm '
  'width east-west, centred on the position.', ['13.1.1', '13.3.1', '13.4.1', '12.6.2'],
  with_elements(room_doc(), {'WC': element(size=(700 * MM, 400 * MM, 800 * MM), origin=(0, -200 * MM, 0),
                                           host=surface('R1', (1000 * MM, 1000 * MM), rotation=90_000_000))},
                ext='FS_plumbing', coll='fixtures'))
n('hosting', 'surface-ceiling', 'A light on R1\'s ceiling: the origin is at the level\'s elevation plus its height, '
  '2700 mm, and the fallback hangs below it.', ['13.1.1', '13.4.1'],
  with_elements(room_doc(), {'LT': element(size=(300 * MM, 300 * MM, 150 * MM), origin=(-150 * MM, -150 * MM, -150 * MM),
                                           host=surface('R1', (CX, CY), 'ceiling'))}))
for slug, pos, why in [('surface-outside-room', (-1000 * MM, CY), 'outside the room altogether'),
                       ('surface-on-room-polygon', (50 * MM, CY), 'on the room polygon, at the inner face of W1'),
                       ('surface-in-wall-thickness', (20 * MM, CY), 'inside the thickness of W1, in the room\'s face '
                                                                    'but not inside its room polygon')]:
    n('hosting', slug, f'A surface host whose position is {why}: FS-INV-503.', ['13.3.4', '10.2.1'],
      with_elements(room_doc(), {'WC': element(host=surface('R1', pos))}), [('FS-INV-503', ['WC'])])
d = v2(v01.room_doc())
d['rooms']['R2'] = R(CX + 1000 * MM, CY)
n('hosting', 'surface-on-room-with-room-error', 'A surface host on R1, which shares its face with R2 (FS-INV-202): '
  'FS-INV-503 is evaluated only for a room without room invariants, so it is not reported though the position is '
  'outside.', ['10.3.1', '13.3.4'], with_elements(d, {'WC': element(host=surface('R1', (-1000 * MM, CY)))}),
  [('FS-INV-202', ['R1', 'R2'])])
d = room_doc()
d['junctions']['J9'] = J(0, 0)
n('hosting', 'surface-on-level-with-graph-error', 'Two junctions share a position on L1 (FS-INV-101): room '
  'invariants are not evaluated on L1, and neither is FS-INV-503.', ['10.3.1', '13.3.4'],
  with_elements(d, {'WC': element(host=surface('R1', (-1000 * MM, CY)))}), [('FS-INV-101', ['J1', 'J9'])])
ROTS = {'R0': 0, 'R45': 45_000_000, 'R30': 30_000_000, 'RM135': -135_000_000, 'R180': 180_000_000, 'ROD': 123_456_789}
n('hosting', 'free-rotations', 'Six chairs standing free, each 500 mm square around its position, at rotations 0, '
  '45, 30, -135, 180 and 123.456789 degrees: each frame faces F(rotation), whose components are cos and sin times '
  '10^9 rounded once - (707106781, 707106781) at 45 degrees, (866025404, 500000000) at 30 - and each placement\'s '
  'facing is its rotation.', ['13.1.1', '13.3.1', '13.4.1', '12.6.2'],
  with_elements(room_doc(), {k: element(size=(500 * MM, 500 * MM, 800 * MM), origin=(-250 * MM, -250 * MM, 0),
                                        host=free(CX + i * 10 * MM, CY, rotation=r))
                             for i, (k, r) in enumerate(ROTS.items())}))
for slug, rot in [('rotation-lower-bound', -180_000_000), ('rotation-above-range', 180_000_001)]:
    n('hosting', slug, f'A rotation of {rot}: rotations lie in (-180,000,000, 180,000,000].', ['13.3.1'],
      with_elements(room_doc(), {'C': element(host=free(CX, CY, rotation=rot))}), SCH)
for slug, host, why in [
    ('host-mode-unknown', {'mode': 'ceiling', 'room': 'R1', 'position': [CX, CY]}, 'A host mode is wallFace, surface or free.'),
    ('wall-face-without-side', {'mode': 'wallFace', 'wall': 'W1', 'offset': 0, 'height': 0}, 'A wall-face host names its side.'),
    ('wall-face-side-unknown', wall_face('W1', 'interior', 0, 0), 'A side is "left" or "right".'),
    ('wall-face-negative-offset', wall_face('W1', 'left', -1, 0), 'An offset is not negative.'),
    ('wall-face-negative-height', wall_face('W1', 'left', 0, -1), 'A height is not negative.'),
    ('wall-face-with-rotation', {**wall_face('W1', 'left', 0, 0), 'rotation': 0}, 'A wall-face host has no rotation: it '
     'faces out of its face.'),
    ('surface-unknown-surface', surface('R1', (CX, CY), 'wall'), 'A surface is the floor or the ceiling.'),
    ('free-with-room', {**free(CX, CY), 'room': 'R1'}, 'A free host has no room.'),
    ('free-without-position', {'mode': 'free', 'level': 'L1'}, 'A free host has a position.'),
]:
    n('hosting', slug, why, ['13.3.1'], with_elements(room_doc(), {'C': element(host=host)}), SCH)
two = merge(room_doc(), levels={'L2': {'building': 'B1', 'elevation': H, 'height': H}})
n('hosting', 'fallback-level-not-host-level', 'A wall-face host on W1, on L1, whose fallback names L2; and a free '
  'host on L2 whose fallback names L1: FS-INV-504 for each.', ['13.3.5', '10.2.1'],
  with_elements(two, {'A': element(level='L2', host=wall_face('W1', 'right', 0, 0)),
                      'B': element(level='L1', host=free(CX, CY, level='L2'))}),
  [('FS-INV-504', ['A']), ('FS-INV-504', ['B'])])
n('hosting', 'surface-fallback-level', 'A surface host on R1, on L1, whose fallback names L2: FS-INV-504.', ['13.3.5'],
  with_elements(two, {'C': element(level='L2', host=surface('R1', (CX, CY)))}), [('FS-INV-504', ['C'])])
base = with_elements(room_doc(), {'OUT': element(host=wall_face('W2', 'right', 1000 * MM, WF))})
n('hosting', 'follows-its-host-before', 'An outlet on the interior face of the north wall W2, 1 m from its start. '
  'hosting/033 moves the north wall 500 mm north and changes nothing about the outlet: its placement follows.',
  ['13.4.1'], base)
moved = copy.deepcopy(base)
moved['junctions']['J2']['position'][1] += 500 * MM
moved['junctions']['J3']['position'][1] += 500 * MM
n('hosting', 'follows-its-host-after', 'hosting/032 with the north wall W2 moved 500 mm north: the outlet\'s placement '
  'and fallback move with it, though its own members are unchanged.', ['13.4.1'], moved)
n('hosting', 'box-extent-at-minimum', 'A fallback box exactly 1,280 base units (1 mm) in every extent: valid.',
  ['13.2.2'], with_elements(room_doc(), {'PIN': element(size=(1280, 1280, 1280), origin=(CX, CY, 0))}))
n('hosting', 'box-extent-too-small', 'A fallback box 1,279 base units tall: FS-INV-505.', ['13.2.2', '10.2.1'],
  with_elements(room_doc(), {'PIN': element(size=(1280, 1280, 1279), origin=(CX, CY, 0))}), [('FS-INV-505', ['PIN'])])
n('hosting', 'box-inverted', 'A fallback box whose max is below its min on x: its extent is negative, FS-INV-505.',
  ['13.2.2'], with_elements(room_doc(), {'PIN': element(size=(-1280, 1280, 1280), origin=(CX, CY, 0))}),
  [('FS-INV-505', ['PIN'])])
e = element()
e['fallback']['box']['min'] = [0, 0]
n('hosting', 'box-with-two-coordinates', 'A box\'s min is three lengths.', ['13.2.1'], with_elements(room_doc(), {'C': e}), SCH)
e = element()
e['fallback']['box']['size'] = [1, 1, 1]
n('hosting', 'box-unknown-member', 'A box has only min and max.', ['13.2.1'], with_elements(room_doc(), {'C': e}), SCH)
e = element()
e['fallback']['box']['max'][2] = 900.0
raw = (fmt(with_elements(room_doc(), {'C': element()})) + '\n').replace('1152000]', '1152000.0]').encode()
n('hosting', 'box-length-with-fraction', 'A box\'s lengths are JSON integers: 1152000.0 is not one.', ['13.2.1', '2.1.1'],
  None, SCH, raw=raw)

# =================================================================================== clearances
def door_doc(swing_side=None, envs=None, wall='W4', offset=1000 * MM, base=None):
    d = copy.deepcopy(base) if base is not None else room_doc()
    o = door_on(wall, offset=offset)
    if swing_side is not None:
        o['swing'] = swing_side
    d['openings'] = {'O1': o}
    d['types']['D'] = {**DOOR, 'clearances': envs if envs is not None else {'swing': swing()}}
    return d


n('clearances', 'door-swing', 'A 900 mm door on the south wall W4 - which runs west, from J4 at (4 m, 0) to J1 - '
  'swinging right, into the room. Its frame\'s origin is the middle of the opening on the location line, at the '
  'sill, facing north; the swing envelope reaches 900 mm into the room and 450 mm either side.',
  ['13.1.1', '13.5.1', '13.5.2'], door_doc())
n('clearances', 'door-swing-left', 'The same door swinging left, out of the room: its frame faces south, and the '
  'envelope is mirrored across the wall.', ['13.1.1', '13.5.2'], door_doc('left'))
d = room_doc()
d['openings'] = {'O1': {'wall': 'W2', 'offset': 1000 * MM, 'fill': 'WIN'}}
d['types']['WIN'] = {**WINDOW, 'clearances': {'egress': env('access', (0, -600 * MM, -900 * MM), (900 * MM, 600 * MM, 1200 * MM))}}
n('clearances', 'window-access', 'A window on the north wall W2 with an access envelope: a window has no swing, so '
  'its frame faces the default "right" - the wall\'s interior - and the envelope, 900 mm deep, runs from the floor '
  '(900 mm below the sill) to the head.', ['13.1.1', '13.5.2'], d)
obl_room = v2(level_doc(junctions={'J1': J(0, 0), 'J2': J(-u, 2 * u), 'J3': J(3 * u, 4 * u), 'J4': J(4 * u, 2 * u)},
                        walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J1')},
                        rooms={'R1': R(int(1.5 * u), 2 * u)}))
n('clearances', 'door-swing-oblique', 'A door on the oblique wall W4, from (4u, 2u) to (0, 0) with u = 1 m: the '
  'frame\'s origin and axes involve sqrt(5), and every footprint corner is rounded once.', ['13.1.1', '13.5.2', '2.2.1'],
  door_doc(base=obl_room, offset=500 * MM))
n('clearances', 'element-clearance', 'A panel on the interior face of W1 with a working space 900 mm deep, 762 mm '
  'wide and 1980 mm high in its frame - in front of the face, from the floor.', ['13.5.1', '13.5.2'],
  with_elements(room_doc(), {'PNL': element(size=(100 * MM, 400 * MM, 600 * MM), origin=(0, -200 * MM, 0),
                                            host=wall_face('W1', 'right', 1500 * MM, 1200 * MM),
                                            clearances={'working': env('workingSpace', (0, -381 * MM, -1200 * MM),
                                                                       (900 * MM, 381 * MM, 780 * MM))})}))
n('clearances', 'element-clearance-rotated', 'A toilet turned 30 degrees, with a fixture clearance in front of it: '
  'the envelope\'s corners are irrational, from the facing vector (866025404, 500000000), and rounded once.',
  ['13.1.1', '13.5.2'],
  with_elements(room_doc(), {'WC': element(size=(700 * MM, 400 * MM, 800 * MM), origin=(0, -200 * MM, 0),
                                           host=surface('R1', (1000 * MM, 1000 * MM), rotation=30_000_000),
                                           clearances={'front': env('fixtureClearance', (700 * MM, -400 * MM, 0),
                                                                    (1300 * MM, 400 * MM, 1000 * MM))})},
                ext='FS_plumbing', coll='fixtures'))
pnl = element(size=(100 * MM, 400 * MM, 600 * MM), origin=(0, -200 * MM, 0), host=wall_face('W4', 'right', 2150 * MM, 1200 * MM),
              clearances={'working': env('workingSpace', (0, -381 * MM, -1200 * MM), (900 * MM, 381 * MM, 780 * MM))})
n('clearances', 'overlap-swing-and-working-space', 'A door swing and the working space of an electrical panel beside '
  'the door, on the same face: the envelopes overlap by 131 mm, and clearanceOverlaps lists the pair. Overlap is a measure, not a '
  'diagnostic: the document is valid and has no warning.', ['13.6.1', '13.5.2'],
  with_elements(door_doc(), {'PNL': pnl}))
n('clearances', 'touching-envelopes-do-not-overlap', 'The door\'s swing envelope spans x from 2100 mm to 3000 mm '
  'and y from 0 to 900 mm; an access envelope from x = 1600 mm to 2100 mm shares only the edge x = 2100 mm with it: '
  'interiors do not intersect, so nothing is listed.', ['13.6.1'],
  with_elements(door_doc(), {'HATCH': element(size=(1280, 1280, 1280), origin=(CX, CY, 0), host=free(0, 0),
                                              clearances={'access': env('access', (1600 * MM, 50 * MM, 0), (2100 * MM, 950 * MM, 1000 * MM))})}))
n('clearances', 'overlap-by-one-unit', 'The same access envelope one base unit wider, reaching x = 2100 mm + 1: the '
  'interiors intersect, so the pair is listed.', ['13.6.1'],
  with_elements(door_doc(), {'HATCH': element(size=(1280, 1280, 1280), origin=(CX, CY, 0), host=free(0, 0),
                                              clearances={'access': env('access', (1600 * MM, 50 * MM, 0), (2100 * MM + 1, 950 * MM, 1000 * MM))})}))
n('clearances', 'vertical-ranges-apart', 'An access envelope over the door swing in plan but above the door\'s head, '
  'from 2100 mm up: their vertical ranges only touch, so they do not overlap.', ['13.6.1'],
  with_elements(door_doc(), {'HATCH': element(size=(1280, 1280, 1280), origin=(CX, CY, 0), host=free(0, 0),
                                              clearances={'access': env('access', (2000 * MM, 0, 2100 * MM), (3100 * MM, 900 * MM, 2600 * MM))})}))
d = door_doc(envs={'swing': swing(), 'approach': env('access', (0, -600 * MM, 0), (1200 * MM, 600 * MM, 2100 * MM))})
n('clearances', 'one-owner-not-listed', 'A door type with two envelopes that overlap each other: only envelopes of '
  'different owners are compared, so nothing is listed.', ['13.6.1'], d)
diamond = lambda x, y, rot: element(size=(1280, 1280, 1280), host=free(x, y, rotation=rot),
                                    clearances={'c': env('access', (-500 * MM, -500 * MM, 0), (500 * MM, 500 * MM, 1000 * MM))})
n('clearances', 'rotated-squares-apart', 'Two 1 m squares, each turned 45 degrees - diamonds - with centres 708 mm '
  'apart in both x and y: their facing edges are parallel and about 1.3 mm apart, so they do not overlap, though '
  'their axis-aligned bounding boxes do. A test on bounding boxes would list them; the overlap measure does not.',
  ['13.6.1'],
  with_elements(room_doc(), {'D1': diamond(1000 * MM, 1000 * MM, 45_000_000),
                             'D2': diamond(1708 * MM, 1708 * MM, 45_000_000)}))
n('clearances', 'rotated-squares-overlapping', 'The same two diamonds with centres 706 mm apart in x and y: they '
  'overlap by about 1.5 mm, and the pair is listed.', ['13.6.1'],
  with_elements(room_doc(), {'D1': diamond(1000 * MM, 1000 * MM, 45_000_000),
                             'D2': diamond(1706 * MM, 1706 * MM, 45_000_000)}))
for slug, envs, why in [
    ('purpose-unknown', {'swing': env('privacy', (0, 0, 0), (1280, 1280, 1280))}, '"privacy" is not a purpose.'),
    ('shape-unknown', {'swing': {**swing(), 'shape': 'arc'}}, '"box" is the only shape of this draft.'),
    ('shape-missing', {'swing': {k: v for k, v in swing().items() if k != 'shape'}}, 'An envelope states its shape.'),
    ('name-pattern', {'Swing': swing()}, 'An envelope name starts with a lowercase letter.'),
    ('envelope-unknown-member', {'swing': {**swing(), 'radius': 900 * MM}}, 'An envelope has only purpose, shape, min '
     'and max.'),
    ('envelope-missing-max', {'swing': {k: v for k, v in swing().items() if k != 'max'}}, 'An envelope has a max.'),
]:
    n('clearances', slug, why, ['13.5.1'], door_doc(envs=envs), SCH)
d = room_doc()
d['types']['WT']['clearances'] = {'access': swing()}
n('clearances', 'clearances-on-a-wall-type', 'Clearances appear only on door and window types and extension elements: '
  'a wall type\'s "clearances" is an unknown member.', ['13.5.1'], d, SCH)
d = room_doc()
d['openings'] = {'O1': {**door_on('W4'), 'clearances': {'swing': swing()}}}
d['types']['D'] = DOOR
n('clearances', 'clearances-on-an-opening', 'In this draft an opening takes its clearances from its type: an '
  'opening\'s own "clearances" is an unknown member.', ['13.5.1'], d, SCH)
n('clearances', 'envelope-too-small', 'A door type\'s envelope 1,279 base units deep: FS-INV-505 names the type.',
  ['13.2.2', '10.2.1'], door_doc(envs={'swing': env('swing', (0, 0, 0), (1279, 1280, 1280))}), [('FS-INV-505', ['D'])])
n('clearances', 'element-envelope-too-small', 'An extension element\'s envelope with a zero extent: FS-INV-505 names '
  'the element.', ['13.2.2'],
  with_elements(room_doc(), {'C': element(clearances={'a': env('access', (0, 0, 0), (1280, 0, 1280))})}),
  [('FS-INV-505', ['C'])])
d = door_doc(envs={})
n('clearances', 'empty-clearances-omitted', 'A door type with "clearances": {} - the constant default - is written '
  'without it in canonical form, and derives no envelope.', ['9.2.1', '1.5.1'], d)
d = door_doc()
d['types']['D2'] = {**DOOR, 'clearances': {'swing': swing()}}
n('clearances', 'unused-type-derives-nothing', 'A second door type with clearances that no opening uses: envelopes '
  'are placed in the frames of openings, so it derives none, and FS-LINT-006 names it.', ['13.5.2'], d,
  [('FS-LINT-006', ['D2'])])

# =================================================================================== circulation
# A grid plan: cells of 4 m by 3 m. Junctions pJij; horizontal edges pHij from (i, j) to (i+1, j) and
# vertical edges pVij from (i, j) to (i, j+1), so H{i}0 is the south wall of column i and V0{j} the west
# wall of row j. A door, window or cased opening is named after its edge: Dx, Nx, Cx.
CW, CH = 4000 * MM, 3000 * MM


def plan(cols, rows, rooms, doors=(), windows=(), cased=(), seps=(), omit=(), level='L1', p=''):
    """rooms: {ID: (i, j)} or {ID: ((i, j), function)}, anchored at the centre of cell (i, j)."""
    edges = {}
    for i in range(cols):
        for j in range(rows + 1):
            edges[f'{p}H{i}{j}'] = ((i, j), (i + 1, j))
    for i in range(cols + 1):
        for j in range(rows):
            edges[f'{p}V{i}{j}'] = ((i, j), (i, j + 1))
    js, ws, ss, os_, rs = {}, {}, {}, {}, {}
    for name, (a, b) in edges.items():
        if name in omit:
            continue
        ja, jb = f'{p}J{a[0]}{a[1]}', f'{p}J{b[0]}{b[1]}'
        for jid, (x, y) in ((ja, a), (jb, b)):
            js[jid] = J(x * CW, y * CH, level)
        (ss if name in seps else ws)[name] = (S if name in seps else W)(ja, jb, level)
    for name in doors:
        os_[f'D{name}'] = door_on(name)
    for name in windows:
        os_[f'N{name}'] = door_on(name, fill='WIN')
    for name in cased:
        os_[f'C{name}'] = door_on(name, fill=None)
    for rid, v in rooms.items():
        (i, j), fn = (v, None) if isinstance(v[0], int) else v
        r = R(i * CW + CW // 2, j * CH + CH // 2, level)
        if fn is not None:
            r['function'] = fn
        rs[rid] = r
    return {'junctions': js, 'walls': ws, 'separators': ss, 'openings': os_, 'rooms': rs}


def cdoc(*plans, levels=None, buildings=None):
    """A 0.2 document of the plans, with the door type D and the window type WIN where they are used."""
    fills = {o.get('fill') for pl in plans for o in pl['openings'].values()}
    d = ldoc(types={k: v for k, v in (('D', DOOR), ('WIN', WINDOW)) if k in fills})
    if buildings is not None:
        d['buildings'] = buildings
    if levels is not None:
        d['levels'] = levels
    for pl in plans:
        for k, v in pl.items():
            if v:
                d.setdefault(k, {}).update(v)
    return d


L2 = {'L1': {'building': 'B1', 'elevation': 0, 'height': H}, 'L2': {'building': 'B1', 'elevation': H, 'height': H}}

d = cdoc(plan(3, 2, {'LIV': ((0, 0), 'living'), 'HALL': ((1, 0), 'circulation'), 'KIT': ((2, 0), 'kitchen'),
                     'BED1': ((0, 1), 'sleeping'), 'BATH': ((1, 1), 'bath'), 'BED2': ((2, 1), 'sleeping')},
              doors=['H10', 'V10', 'V20', 'H11', 'H01', 'H21'], windows=['H02', 'V30']))
n('circulation', 'every-room-reachable', 'A six-room house: a front door in the south wall of the hall (H10), doors '
  'from the hall to the living room, the kitchen and the bathroom, a bedroom off the living room and one off the '
  'kitchen. The hall is the only entry - the windows on H02 and V30 are not ways in - and every room is reachable. '
  'Neither bedroom is reached through another sleeping room, so throughSleeping is false for both and absent for '
  'every other room. No circulation lint.', ['14.3.1', '11.4.1'], d)
d = cdoc(plan(3, 2, {'HALL': ((0, 0), 'circulation'), 'BED1': ((1, 1), 'sleeping'), 'BED2': ((2, 1), 'sleeping')},
              omit=['V10', 'V20', 'H01'], doors=['V01', 'H11', 'H21']))
n('circulation', 'l-shaped-hallway', 'An L-shaped hall - three cells along the south and one up the west side, the '
  'walls between them left out - whose front door is in the west wall of the upper leg (V01), far from the hall\'s '
  'anchor. Both bedrooms open off the long leg, so both are reachable: a room is one node of the door graph, '
  'whatever its shape.', ['14.3.1'], d)
d = cdoc(plan(3, 1, {'LIV': ((0, 0), 'living'), 'BED1': ((1, 0), 'sleeping'), 'BED2': ((2, 0), 'sleeping')},
              doors=['H00', 'V10', 'V20']))
n('circulation', 'bedroom-through-bedroom', 'Living room, bedroom, bedroom in a row, with the front door into the '
  'living room: the second bedroom is reachable only through the first, so its throughSleeping is true and '
  'FS-LINT-013 names it. The first bedroom is not reached through a sleeping room. A warning, never an error.',
  ['14.3.1', '14.4.3', '10.2.1'], d, [('FS-LINT-013', ['BED2'])])
d = cdoc(plan(3, 2, {'LIV': ((0, 0), 'living'), 'BED': ((1, 0), 'sleeping'), 'BATH': ((2, 0), 'bath'),
                     'KIT': ((0, 1), 'kitchen'), 'CLO': ((1, 1), 'storage'), 'WIC': ((2, 1), 'storage')},
              doors=['H00', 'V10', 'V20', 'H01', 'H11', 'H21']))
n('circulation', 'en-suite-and-closet-through-bedroom', 'A bedroom with an en-suite bathroom and a closet, each '
  'reached only through the bedroom, and a walk-in closet reached only through the bathroom. None of them is a '
  'sleeping room, so each is simply reachable: no lint.', ['14.3.1'], d)
d = cdoc(plan(2, 2, {'LIV': ((0, 0), 'living'), 'BED1': ((1, 0), 'sleeping'), 'OFF': ((0, 1), 'office'),
                     'BED2': ((1, 1), 'sleeping')},
              doors=['H00', 'V10'], windows=['H01', 'V01', 'H12']))
n('circulation', 'unreachable-rooms', 'A living room with the front door and a bedroom off it; an office that has '
  'only windows - one into the living room (H01), one to the outside (V01) - and a second bedroom with only a window '
  'into the first (H11 has none; H12 is its window to the outside). The office and the second bedroom are '
  'unreachable: FS-LINT-012 for each. The second bedroom is not reachable at all, so its throughSleeping is false '
  'and FS-LINT-013 is not reported.', ['14.3.1', '14.4.3', '11.4.1'], d,
  [('FS-LINT-012', ['BED2']), ('FS-LINT-012', ['OFF'])])
d = cdoc(plan(3, 1, {'LIV': ((0, 0), 'living'), 'DIN': ((1, 0), 'dining'), 'KIT': ((2, 0), 'kitchen')},
              doors=['H00'], cased=['V10'], seps=['V20']))
n('circulation', 'cased-opening-and-separator-connect', 'The dining room opens from the living room through an '
  'empty, cased opening, and the kitchen from the dining room across a separator: both connect (11.4), so both are '
  'reachable.', ['14.3.1', '11.4.1'], d)
d = cdoc(plan(2, 1, {'PORCH': ((0, 0), 'exterior'), 'LIV': ((1, 0), 'living')},
              seps=['H00', 'V00', 'H01'], doors=['V10']))
n('circulation', 'porch-with-separators-is-an-entry', 'A porch whose open sides are separators to the outside, and '
  'a door from it into the living room. A separator between a room and the unbounded face makes the room an entry, '
  'as a door does: the porch is the entry and the living room is reachable through it.', ['14.3.1'], d)
d = cdoc(plan(3, 1, {'GAR': ((0, 0), 'garage'), 'MUD': ((1, 0), 'utility'), 'LIV': ((2, 0), 'living')},
              doors=['H00', 'V10', 'V20'], windows=['H20', 'V30']))
n('circulation', 'garage-only-entry', 'The only way in is the garage door (H00); a mudroom and the living room '
  'beyond it are reached through the garage. An entry may be of any function, so every room is reachable and no '
  'circulation lint is reported - whether a house may be entered only through its garage is for rules to say.',
  ['14.3.1'], d)
d = cdoc(plan(2, 1, {'LIV': ((0, 0), 'living'), 'BED': ((1, 0), 'sleeping')}, doors=['V10'], windows=['H00']))
n('circulation', 'no-entry', 'Two rooms with a door between them and only a window to the outside: the building '
  'has doors but no entry. FS-LINT-014 is reported once, for the building, and FS-LINT-012 is not reported for its '
  'rooms, though neither is reachable.', ['14.3.1', '14.4.2', '14.4.3', '10.3.1'], d, [('FS-LINT-014', ['B1'])])
d = cdoc(plan(2, 1, {'LIV': ((0, 0), 'living'), 'BED': ((1, 0), 'sleeping')}, windows=['H00', 'V10'], seps=[]))
n('circulation', 'no-door-not-evaluated', 'Two rooms with windows - one between them, one to the outside - and no '
  'door or cased opening anywhere: the building is not evaluated, so no circulation lint is reported, though no '
  'room is an entry and none is reachable.', ['14.3.1', '14.4.2', '10.3.1'], d)
d = cdoc(plan(2, 1, {'KIT': ((0, 0), 'kitchen'), 'DIN': ((1, 0), 'dining')}, seps=['V10']))
n('circulation', 'separators-alone-not-evaluated', 'A kitchen and a dining room divided by a separator, and no '
  'opening: the rooms are connected, but a building is evaluated only once a wall hosts a door or an empty opening, '
  'so no circulation lint is reported.', ['14.3.1', '14.4.2'], d)
d = cdoc(plan(2, 1, {'HALL': ((0, 0), 'circulation'), 'LIV': ((1, 0), 'living')}, doors=['H00', 'V10']),
         plan(2, 1, {'LAND': ((0, 0), 'circulation'), 'BED': ((1, 0), 'sleeping')}, doors=['UV10'], level='L2', p='U'),
         levels=L2)
n('circulation', 'two-levels-joined-by-circulation-rooms', 'A stair hall on L1 with the front door, and a landing on '
  'L2 with a bedroom off it. Stairs are not in this draft; two rooms of function circulation on different levels '
  'of one building are linked, so the landing and the bedroom are reachable.', ['14.3.1'], d)
d = cdoc(plan(2, 1, {'HALL': ((0, 0), 'circulation'), 'LIV': ((1, 0), 'living')}, doors=['H00', 'V10']),
         plan(2, 1, {'BED1': ((0, 0), 'sleeping'), 'BED2': ((1, 0), 'sleeping')}, doors=['UV10'], level='L2', p='U'),
         levels=L2)
n('circulation', 'upper-level-without-circulation-room', 'The same house with no room of function circulation on '
  'L2: nothing links L2 to L1, so both bedrooms upstairs are unreachable, FS-LINT-012 for each. Neither is reached '
  'through a sleeping room, since neither is reached at all.', ['14.3.1'], d,
  [('FS-LINT-012', ['BED1']), ('FS-LINT-012', ['BED2'])])
d = cdoc(plan(2, 1, {'HALL': ((0, 0), 'circulation'), 'LIV': ((1, 0), 'living')}, doors=['H00', 'V10']),
         plan(2, 1, {'WS': ((0, 0), 'circulation'), 'SHOP': ((1, 0), 'utility')}, doors=['UV10'], level='L2', p='U'),
         buildings={'B1': {}, 'B2': {}},
         levels={'L1': {'building': 'B1', 'elevation': 0, 'height': H},
                 'L2': {'building': 'B2', 'elevation': 0, 'height': H}})
n('circulation', 'two-buildings', 'A house B1 with an entry, and a detached workshop B2 whose two rooms have a door '
  'between them but none to the outside. Each building has its own door graph: circulation rooms of different '
  'buildings are never linked, so B2 has no entry (FS-LINT-014) and B1 is fine.', ['14.3.1', '14.4.2'], d,
  [('FS-LINT-014', ['B2'])])
d = cdoc(plan(3, 2, {'BED1': ((0, 0), 'sleeping'), 'BATH': ((1, 0), 'bath'), 'BED2': ((2, 0), 'sleeping'),
                     'HALL': ((0, 1), 'circulation')},
              omit=['V11', 'V21'], doors=['H12', 'H01', 'H21', 'V10', 'V20']))
n('circulation', 'jack-and-jill-bath', 'Two bedrooms off a hall, with a bathroom between them that opens into both: '
  'each bedroom can also be reached through the bathroom and the other bedroom, but not only that way, so neither '
  'is reached through another sleeping room.', ['14.3.1'], d)
d = cdoc(plan(3, 2, {'BED1': ((0, 0), 'sleeping'), 'BATH': ((1, 0), 'bath'), 'BED2': ((2, 0), 'sleeping'),
                     'HALL': ((0, 1), 'circulation')},
              omit=['V11', 'V21'], doors=['H12', 'H01', 'V10', 'V20']))
n('circulation', 'bedroom-through-shared-bath', 'The same plan without the door from the hall to the second '
  'bedroom: it is reached only through the bathroom, and every path to the bathroom passes through the first '
  'bedroom. A path through a room that is not a sleeping room still passes through the bedroom before it: '
  'FS-LINT-013 names the second bedroom.', ['14.3.1'], d, [('FS-LINT-013', ['BED2'])])
d = cdoc(plan(2, 2, {'LIV': ((0, 0), 'living'), 'BED1': ((1, 0), 'sleeping'), 'BED2': ((0, 1), 'sleeping'),
                     'BED3': ((1, 1), 'sleeping')},
              doors=['H00', 'V10', 'H01', 'H11', 'V11']))
n('circulation', 'through-either-of-two-bedrooms', 'A third bedroom with a door into each of two bedrooms that open '
  'off the living room. No single bedroom stands in its way, but every path to it passes through one of them: it '
  'is reachable only through another sleeping room (FS-LINT-013).', ['14.3.1'], d, [('FS-LINT-013', ['BED3'])])
d = cdoc(plan(2, 1, {'BED1': ((0, 0), 'sleeping'), 'BED2': ((1, 0), 'sleeping')}, doors=['H00', 'V10']))
n('circulation', 'sleeping-room-entry', 'A bedroom with its own door to the outside is an entry, and is not reached '
  'through anything; the bedroom beyond it is reachable only through it (FS-LINT-013).', ['14.3.1'], d,
  [('FS-LINT-013', ['BED2'])])
d = cdoc(plan(3, 1, {'LIV': ((0, 0), 'living'), 'BED': ((1, 0), 'sleeping'), 'GUEST': ((2, 0), 'EXT_wellness:guest')},
              doors=['H00', 'V10', 'V20']))
d['extensionsUsed'] = {'EXT_wellness': '1.0'}
n('circulation', 'extension-term-is-not-sleeping', 'A room whose function is an extension term, reached only through '
  'a bedroom: only the core term sleeping makes a sleeping room, so the room has no throughSleeping and no lint.',
  ['14.3.1'], d)
js, ws = box('A', 0, 0, 8000 * MM, 6000 * MM)
jc, wc = box('C', 3000 * MM, 2000 * MM, 5000 * MM, 4000 * MM)
d = ldoc(junctions={**js, **jc}, walls={**ws, **wc}, types={'D': DOOR},
         rooms={'LIV': R(1000 * MM, 1000 * MM, function='living'), 'CLO': R(4000 * MM, 3000 * MM, function='storage')},
         openings={'D1': door_on('AW4'), 'D2': door_on('CW1', offset=500 * MM)})
n('circulation', 'freestanding-closet', 'A freestanding closet inside the living room - an inner cycle of the living '
  'room\'s face (6.1) - with a door in one of its walls: its walls lie between the two faces, so the closet is '
  'connected to the living room and reachable.', ['14.3.1', '11.4.1'], d)
d = cdoc(plan(2, 1, {'LIV': ((1, 0), 'living')}, doors=['H00', 'V10']))
n('circulation', 'through-an-unanchored-face', 'A vestibule with the front door that nobody has made a room, and a '
  'door from it to the living room. Only rooms are nodes of the door graph, so no path passes through the '
  'vestibule: the building has no entry (FS-LINT-014), beside the unanchored face (FS-LINT-003).', ['14.3.1', '14.4.2'],
  d, [('FS-LINT-003', []), ('FS-LINT-014', ['B1'])])

# =================================================================================== diagnostics (0.2)
d = house_program()
d['program']['items']['BED'].update(count=3, minArea=12 * M2)
d['program']['items']['GAR'] = item('garage')
d['program']['adjacency'] = [adj('KIT', 'DIN', 'forbidden'), adj('BED', 'KIT', 'preferred'), adj('GAR', 'BED', 'required')]
n('diagnostics', 'every-program-lint', 'A valid document with every program lint: three bedrooms asked for and two '
  'drawn (FS-LINT-008), both under 12 m2 (FS-LINT-009 twice), a garage nothing fulfils (FS-LINT-008), a required '
  'adjacency from it that cannot be met (FS-LINT-010), and the kitchen and dining room forbidden but adjacent '
  '(FS-LINT-011). No program condition is an error. (The house also has no entry, FS-LINT-014.)',
  ['10.1.1', '10.2.1', '11.5.2'], d,
  [('FS-LINT-008', ['BED']), ('FS-LINT-008', ['GAR']), ('FS-LINT-009', ['BED', 'RNW']), ('FS-LINT-009', ['BED', 'RSW']),
   ('FS-LINT-010', ['BED', 'GAR']), ('FS-LINT-011', ['DIN', 'KIT']), NOENTRY])
d = house_program()
d['rooms']['RSW']['brief'] = 'NOPE'
d['program']['adjacency'].append(adj('KIT', 'KIT', 'required'))
d = with_elements(d, {'A': element(host=wall_face('WO0', 'right', 99 * X, 0))})
n('diagnostics', 'reference-error-stops-new-invariants', 'A dangling brief, beside a self-adjacency and a host beyond '
  'its wall: once a reference invariant is reported no other invariant is evaluated, so only FS-INV-002.',
  ['10.3.1'], d, [('FS-INV-002', ['RSW'])])
d = house_program()
d['program']['adjacency'].append(adj('KIT', 'KIT', 'required'))
d['walls']['WO1']['top'] = {'height': -1}
d = with_elements(uses(d, EXT_electrical='2.0.0'), {'A': element(host=wall_face('WO0', 'right', 99 * X, 0))})
n('diagnostics', 'new-invariants-together', 'A self-adjacency, a host beyond its wall, a missing dependency and a '
  'wall whose top is below its base: each group of invariants is evaluated, and the diagnostics are sorted by code.',
  ['10.2.1', '10.3.1'], d,
  [('FS-INV-112', ['WO1']), ('FS-INV-401', ['KIT']), ('FS-INV-501', ['A']), ('FS-INV-601', [])], registry=KNOWN)

d = cdoc(plan(3, 2, {'LIV': ((0, 0), 'living'), 'BED1': ((1, 0), 'sleeping'), 'BED2': ((2, 0), 'sleeping'),
                     'OFF': ((0, 1), 'office'), 'BATH': ((1, 1), 'bath'), 'CLO': ((2, 1), 'storage')},
              doors=['H00', 'V10', 'V20', 'H11', 'H21'], windows=['H01']),
         plan(2, 1, {'WS': ((0, 0), 'utility'), 'STORE': ((1, 0), 'storage')}, cased=['UV10'], level='L2', p='U'),
         buildings={'B1': {}, 'B2': {}},
         levels={'L1': {'building': 'B1', 'elevation': 0, 'height': H},
                 'L2': {'building': 'B2', 'elevation': 0, 'height': H}})
n('diagnostics', 'every-circulation-lint', 'A valid document with every circulation lint. In the house B1: an office '
  'with only a window into the living room (FS-LINT-012), and a bedroom reached only through another (FS-LINT-013) - '
  'the bathroom and closet behind it are not sleeping rooms, so nothing is said of them. In the workshop B2: a cased '
  'opening between its two rooms and no way in (FS-LINT-014). No circulation condition is an error.',
  ['10.1.1', '10.2.1', '14.4.1', '14.4.3'], d,
  [('FS-LINT-012', ['OFF']), ('FS-LINT-013', ['BED2']), ('FS-LINT-014', ['B2'])])

NEW = list(TESTS)
del TESTS[:]


def main(argv) -> int:
    tests = BASE + NEW
    return 1 if write_all(prune='--prune' in argv, tests=tests, suite=SUITE02, reader=READER_02) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

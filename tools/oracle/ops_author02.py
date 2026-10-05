"""The conformance suite of Floorspec Ops 0.2, as the script that writes it.

    python3.13 -m tools.oracle.ops_author02            rewrite every test from its declaration below
    python3.13 -m tools.oracle.ops_author02 --prune    ...and delete test directories no longer declared

The suite is the Ops 0.1 suite, re-targeted to 0.2 - every 0.1 test, in the same group under the
same number, covering the 0.2 IDs of the statements 0.2 retired (FS-OPS-1.1.1 is 1.1.2, 4.5.1 is
4.5.3). Its documents A stay Core 0.1 documents: Ops 0.2 applies to them exactly as Ops 0.1 did
(0.4), which these tests show. Then, after them in each group, the tests of what 0.2 adds: the
relative moveOpening and addLevel, and program items, adjacencies, extension elements and hosts as
edit targets, mostly on Core 0.2 documents. Every expected status and diagnostic is written by
hand and cross-checked against the oracle, applied as Ops 0.2 (version.OPS_02); the values that
matter are asserted by hand in each test's check. Afterwards, Core 0.1: 281 tests, 0 differences from the oracle
Core 0.2: 468 tests, 0 differences from the oracle
Ops 0.1: 230 tests, 0 differences from the oracle
Ops 0.2: 0 tests, 0 differences from the oracle
re-verifies the suite from the files alone. Add new tests at the end of their group's section.
"""
import copy
import os

import tools.oracle.ops_author as v01                  # declares the 0.1 suite into ops_author_lib.TESTS
from tools.oracle.ops_author import (K, KITCHEN_WIDER, box, chamfered, courtyard, diag_wall, door_on_south,  # noqa: F401
                                     ensure, first_resolved, garden, house, pos, resolved_eq, two_rooms_apart,
                                     upstairs)
from tools.oracle.ops_author_lib import (FT, H, IN, MM, REPO, TESTS, J, R, S, T, W, doc, level_doc, req,  # noqa: F401
                                        write_all)
from tools.oracle.ops.version import OPS_02

SUITE02 = os.path.join(REPO, 'conformance', 'ops', '0.2')

# ============================================================================= the 0.1 suite, re-targeted

RETIRED = {'FS-OPS-1.1.1': 'FS-OPS-1.1.2', 'FS-OPS-4.5.1': 'FS-OPS-4.5.3'}
RETARGET = {
    # slug: (document A, description) where 0.2 needs another input to show the same thing
    'document-other-version': (doc(floorspec='0.3'), 'Document A declares Floorspec 0.3, which a Core 0.2 reader does not '
                               'implement (FS-DOC-001): FS-OPS-002.'),
}
DESCRIPTIONS = {
    'unknown-collection': 'addElement\'s collection is one of the collections of Core 1.1 or the program\'s items; '
                          '"roofs" is reserved, not a collection of 0.2.',
}


def retarget(tc):
    tc = copy.deepcopy(tc)
    tc['covers'] = [RETIRED.get(c, c) for c in tc['covers']]
    if tc['slug'] in RETARGET:
        tc['a'], tc['description'] = RETARGET[tc['slug']]
    tc['description'] = DESCRIPTIONS.get(tc['slug'], tc['description'])
    return tc


BASE = [retarget(tc) for tc in TESTS]
del TESTS[:]

# ============================================================================= composites: relative edits

def four_windows(offset=4 * FT):
    """The box with a 2' window on each wall at `offset`: O1 on W1 (J1 -> J2, running north), O2 on
    W2 (running east), O3 on W3 (running south), O4 on W4 (running west)."""
    return box(openings={f'O{i}': {'wall': f'W{i}', 'offset': offset, 'width': 2 * FT, 'height': 3 * FT, 'sill': 3 * FT}
                         for i in range(1, 5)})


def offsets(*values):
    """A check: the resolved echo sets O1's, O2's ... /offset to these values, in order."""
    return resolved_eq(*({'op': 'setProperty', 'id': f'O{i}', 'path': '/offset', 'value': v}
                         for i, v in enumerate(values, 1)))


T('composites', 'move-opening-by', 'moveOpening with "by" moves the opening along its wall: the new offset is the old '
  'plus "by", so a positive "by" moves the door 2\' toward the end of its wall W4.', ['4.5.2'], door_on_south(FT),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "2'"}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 3 * FT}))
T('composites', 'move-opening-by-negative', 'A negative "by" moves the opening toward its wall\'s start: 4\' less '
  '1\' 6" is 2\' 6", 975360.', ['4.5.2', '3.1.1'], door_on_south(4 * FT),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "-1' 6\""}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 975360}))
T('composites', 'move-opening-toward-start-and-end', 'With "toward": "end" or "start" the sign of "by" is chosen, '
  'whatever is given: -1\' toward the end moves the door from 4\' to 5\', and 2\' toward the start from 5\' to 3\'.',
  ['4.5.2'], door_on_south(4 * FT),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "-1'", 'toward': 'end'},
      {'op': 'moveOpening', 'opening': 'O1', 'by': "2'", 'toward': 'start'}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 5 * FT},
                    {'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 3 * FT}))
T('composites', 'move-opening-toward-north-and-east', 'A window on each wall of the box, each 1\' toward north or '
  'east: W1 runs north and W2 east, so O1 and O2 move toward their walls\' ends (4\' to 5\'); W3 runs south and W4 '
  'west, so O3 and O4 move toward their walls\' starts (4\' to 3\').', ['4.5.2'], four_windows(),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "1'", 'toward': 'north'},
      {'op': 'moveOpening', 'opening': 'O2', 'by': "1'", 'toward': 'east'},
      {'op': 'moveOpening', 'opening': 'O3', 'by': "1'", 'toward': 'north'},
      {'op': 'moveOpening', 'opening': 'O4', 'by': "1'", 'toward': 'east'}),
  check=offsets(5 * FT, 5 * FT, 3 * FT, 3 * FT))
T('composites', 'move-opening-toward-south-and-west', 'The same windows 1\' toward south or west: O1 and O2 move '
  'toward their walls\' starts (4\' to 3\'), O3 and O4 toward their ends (4\' to 5\').', ['4.5.2'], four_windows(),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "1'", 'toward': 'south'},
      {'op': 'moveOpening', 'opening': 'O2', 'by': "1'", 'toward': 'west'},
      {'op': 'moveOpening', 'opening': 'O3', 'by': "-1'", 'toward': 'south'},
      {'op': 'moveOpening', 'opening': 'O4', 'by': "1'", 'toward': 'west'}),
  check=offsets(3 * FT, 3 * FT, 5 * FT, 5 * FT))
T('composites', 'move-opening-toward-on-an-oblique-wall', 'W5 runs from (2\', 2\') to (5\', 6\'), d = (3\', 4\'): '
  'd . east > 0, so 1\' toward east moves the window toward W5\'s end (1\' to 2\'); d . south < 0, so 2\' toward '
  'south moves it toward the start, to 0.', ['4.5.2'],
  dict(diag_wall, openings={'O1': {'wall': 'W5', 'offset': FT, 'width': FT, 'height': 3 * FT}}),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "1'", 'toward': 'east'},
      {'op': 'moveOpening', 'opening': 'O1', 'by': "2'", 'toward': 'south'}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 2 * FT},
                    {'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 0}))
T('composites', 'move-opening-toward-perpendicular', 'W1 runs north, exactly perpendicular to east: the window on it '
  'cannot move toward the east along it, so FS-OPS-008 names the wall.', ['4.5.2', '7.1.1'], four_windows(),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "1'", 'toward': 'east'}), 'rejected', [('FS-OPS-008', ['W1'])])
T('composites', 'move-opening-past-the-wall-end', 'The door at 8\' on the 12\' wall W4 moved 2\' toward its end: '
  '10\' + 36" runs past the end, so the result is invalid and the rejection carries FS-INV-302.', ['4.5.2', '1.2.3'],
  door_on_south(8 * FT), req({'op': 'moveOpening', 'opening': 'O1', 'by': "2'"}), 'rejected', [('FS-INV-302', ['O1'])])
T('composites', 'move-opening-before-the-wall-start', 'The door at 1\' moved 2\' toward its wall\'s start: its offset '
  'would be -1\', and an offset is never negative, so the result is invalid.', ['4.5.2', '1.2.3'],
  door_on_south(FT), req({'op': 'moveOpening', 'opening': 'O1', 'by': "2'", 'toward': 'start'}), 'rejected',
  [('FS-SCH-001', [])])
T('composites', 'move-opening-at-and-by', 'moveOpening takes exactly one of "at" and "by": both is FS-OPS-001.',
  ['1.1.2', '4.5.2'], door_on_south(FT), req({'op': 'moveOpening', 'opening': 'O1', 'at': 'centered', 'by': "1'"}),
  'rejected', [('FS-OPS-001', [])])
T('composites', 'move-opening-neither-at-nor-by', 'moveOpening with neither "at" nor "by": FS-OPS-001.', ['1.1.2'],
  door_on_south(FT), req({'op': 'moveOpening', 'opening': 'O1'}), 'rejected', [('FS-OPS-001', [])])
T('composites', 'move-opening-toward-without-by', '"toward" is allowed only with "by": with "at" it is FS-OPS-001.',
  ['1.1.2', '4.5.2'], door_on_south(FT), req({'op': 'moveOpening', 'opening': 'O1', 'at': 0, 'toward': 'east'}),
  'rejected', [('FS-OPS-001', [])])
T('composites', 'move-opening-by-without-an-offset', 'The door\'s offset is unset earlier in the batch, so there is no '
  'offset to move it from: FS-OPS-003 names the opening.', ['4.5.2', '7.1.1'], door_on_south(FT),
  req({'op': 'unsetProperty', 'id': 'O1', 'path': '/offset'}, {'op': 'moveOpening', 'opening': 'O1', 'by': "1'"}),
  'rejected', [('FS-OPS-003', ['O1'])])
T('composites', 'add-level-above', '"Add a second floor": addLevel above L1 sits on top of it, at L1\'s elevation plus '
  'its height, 0 + 3456000. Its height is 8\', 3121152, and its ID is minted.', ['4.8.1', '1.5.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'above': 'L1', 'height': "8'", 'name': 'Second floor'}),
  check=resolved_eq({'op': 'addElement', 'collection': 'levels', 'id': 'L2',
                     'element': {'building': 'B1', 'elevation': H, 'height': 8 * FT, 'name': 'Second floor'}}))
T('composites', 'add-level-below', '"Add a basement": addLevel below L1 is the new level\'s own height under L1\'s '
  'floor, 0 - 8\' = -3121152.', ['4.8.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'below': 'L1', 'height': "8'", 'name': 'Basement'}),
  check=resolved_eq({'op': 'addElement', 'collection': 'levels', 'id': 'L2',
                     'element': {'building': 'B1', 'elevation': -8 * FT, 'height': 8 * FT, 'name': 'Basement'}}))
T('composites', 'add-level-explicit', 'addLevel with an explicit elevation, a named ID and extras: lengths in the '
  'reference grammar - -8\' and 7\' 6" - are resolved to integers.', ['4.8.1', '3.1.1'], box(),
  req({'op': 'addLevel', 'id': 'L0', 'building': 'B1', 'elevation': "-8'", 'height': "7' 6\"", 'extras': {'use': 'storage'}}),
  check=resolved_eq({'op': 'addElement', 'collection': 'levels', 'id': 'L0',
                     'element': {'building': 'B1', 'elevation': -8 * FT, 'height': 7 * FT + 6 * IN, 'extras': {'use': 'storage'}}}))
T('composites', 'add-level-stacked', 'Levels added earlier in the batch are in the working copy: L2 above L1, then L3 '
  'above L2 at 3456000 + 3121152, then L4 below L1.', ['4.8.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'above': 'L1', 'height': "8'"},
      {'op': 'addLevel', 'building': 'B1', 'above': 'L2', 'height': "9'"},
      {'op': 'addLevel', 'building': 'B1', 'below': 'L1', 'height': 2500 * MM}),
  check=resolved_eq({'op': 'addElement', 'collection': 'levels', 'id': 'L2', 'element': {'building': 'B1', 'elevation': H, 'height': 8 * FT}},
                    {'op': 'addElement', 'collection': 'levels', 'id': 'L3', 'element': {'building': 'B1', 'elevation': H + 8 * FT, 'height': 9 * FT}},
                    {'op': 'addElement', 'collection': 'levels', 'id': 'L4', 'element': {'building': 'B1', 'elevation': -2500 * MM, 'height': 2500 * MM}}))
T('composites', 'add-level-elevation-and-above', 'addLevel takes exactly one of "elevation", "above" and "below": '
  'two is FS-OPS-001.', ['1.1.2', '4.8.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'elevation': 0, 'above': 'L1', 'height': "8'"}), 'rejected', [('FS-OPS-001', [])])
T('composites', 'add-level-above-and-below', '"above" and "below" together: FS-OPS-001.', ['1.1.2'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'above': 'L1', 'below': 'L1', 'height': "8'"}), 'rejected', [('FS-OPS-001', [])])
T('composites', 'add-level-no-elevation', 'addLevel with none of "elevation", "above" and "below": FS-OPS-001.',
  ['1.1.2'], box(), req({'op': 'addLevel', 'building': 'B1', 'height': "8'"}), 'rejected', [('FS-OPS-001', [])])
T('composites', 'add-level-above-an-unknown-level', '"above" names L9, which does not exist: FS-OPS-003, with no '
  'elements, since the reference is in the request.', ['4.8.1', '3.3.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'above': 'L9', 'height': "8'"}), 'rejected', [('FS-OPS-003', [])])
T('composites', 'add-level-below-a-room', '"below" names the room Living: only levels count as matches, so it '
  'resolves to nothing.', ['4.8.1', '3.3.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'below': 'Living', 'height': "8'"}), 'rejected', [('FS-OPS-003', [])])
T('composites', 'add-level-in-an-unknown-building', '"building" names B9, which does not exist: FS-OPS-003.',
  ['4.8.1'], box(), req({'op': 'addLevel', 'building': 'B9', 'elevation': 0, 'height': "8'"}), 'rejected',
  [('FS-OPS-003', [])])
T('composites', 'add-level-above-a-level-without-a-height', 'L1\'s height is unset earlier in the batch, so there is '
  'no top to sit on: FS-OPS-003 names L1.', ['4.8.1', '7.1.1'], box(),
  req({'op': 'unsetProperty', 'id': 'L1', 'path': '/height'},
      {'op': 'addLevel', 'building': 'B1', 'above': 'L1', 'height': "8'"}), 'rejected', [('FS-OPS-003', ['L1'])])


# ============================================================================= helpers for Core 0.2 documents

ELEC, FURN = 'FS_electrical', 'FS_furniture'
M2 = 1280 * 1280 * 1000 * 1000                          # one square metre in square base units
FT2 = FT * FT                                           # one square foot
OUTLET_BOX = {'min': [0, -40 * MM, 0], 'max': [20 * MM, 40 * MM, 100 * MM]}
PIECE_BOX = {'min': [-300 * MM, -300 * MM, 0], 'max': [300 * MM, 300 * MM, 800 * MM]}


def v2(d, **members):
    """A Core 0.2 document: d declaring "0.2", with members merged in (objects one level deep)."""
    d = copy.deepcopy(d)
    d['floorspec'] = '0.2'
    for k, v in members.items():
        d[k] = {**d.get(k, {}), **v} if isinstance(v, dict) and isinstance(d.get(k), dict) else v
    return d


def wired(d, devices=None, pieces=None, used=(ELEC, FURN), **members):
    """d as a 0.2 document using the electrical and furniture extensions, with these devices and
    pieces as their extension elements, and other members merged in as v2 does."""
    d = v2(d, **members)
    d['extensionsUsed'] = {**d.get('extensionsUsed', {}), **{x: '0.1.0' for x in used}}
    ext = dict(d.get('extensions', {}))
    if devices is not None:
        ext[ELEC] = {'collections': {'devices': devices}}
    if pieces is not None:
        ext[FURN] = {'collections': {'pieces': pieces}}
    if ext:
        d['extensions'] = ext
    return d


def outlet(wall, offset, side='right', height=300 * MM, level='L1', **kw):
    """A receptacle on a face of `wall` (the box's walls run clockwise: their right faces are inside)."""
    return {'fallback': {'level': level, 'box': copy.deepcopy(OUTLET_BOX)},
            'host': {'mode': 'wallFace', 'wall': wall, 'side': side, 'offset': offset, 'height': height},
            'device': 'receptacle', **kw}


def standing(room, x, y, level='L1', surface='floor', **kw):
    """A piece of furniture on a room's floor (or a fixture on its ceiling) at (x, y)."""
    return {'fallback': {'level': level, 'box': copy.deepcopy(PIECE_BOX)},
            'host': {'mode': 'surface', 'room': room, 'surface': surface, 'position': [x, y]}, **kw}


def free(level, x, y, **kw):
    return {'fallback': {'level': level, 'box': copy.deepcopy(PIECE_BOX)},
            'host': {'mode': 'free', 'level': level, 'position': [x, y]}, **kw}


def item(function, **kw):
    return {'function': function, **kw}


def adj(a, b, kind, **kw):
    return {'a': a, 'b': b, 'kind': kind, **kw}


def briefed(**program):
    """The house as a 0.2 document with a program: KIT, PAN and DIN, named like the rooms that
    fulfil them, the Kitchen next to the Dining room, and a garage item GAR that must not be."""
    d = v2(house(), program={'items': {'KIT': item('kitchen', name='Kitchen', minArea=8 * M2),
                                       'PAN': item('storage', name='Pantry'),
                                       'DIN': item('dining', name='Dining'),
                                       'GAR': item('garage', name='Garage')},
                             'adjacency': [adj('KIT', 'DIN', 'required'), adj('KIT', 'PAN', 'preferred', weight=3),
                                           adj('GAR', 'KIT', 'forbidden')]})
    d['rooms']['R1']['brief'] = 'KIT'
    d['rooms']['R2']['brief'] = 'PAN'
    d['rooms']['R3']['brief'] = 'DIN'
    d['program'].update(program)
    return d


def ext_of(B, x=ELEC, c='devices'):
    return B['extensions'][x]['collections'][c]


def derived(doc_):
    """What a Core 0.2 deriver derives from a document (a dict), for checks that a hosted element
    follows its host."""
    import json
    from tools.oracle.validate import READER_02, check
    result, _, _ = check(json.dumps(doc_).encode('utf-8'), READER_02)
    assert result['valid'], result['diagnostics']
    return result['derived']


def moved(a, B, eid):
    """How far an extension element's derived placement moved from A to B, as [dx, dy, dz]."""
    pa, pb = derived(a)['placements'][eid]['point'], derived(B)['placements'][eid]['point']
    return [pb[i] - pa[i] for i in range(3)]


# ============================================================================= program

T('program', 'add-program-item', 'addProgramItem adds a brief item: "Bedroom", three of them, each at least 11 m2 and '
  'meant to be 150 sq ft, preferred on L1. The areas resolve exactly - 11 m2 is 18,022,400,000,000 square base units, '
  '150 sq ft is 22,831,851,110,400 - and the ID is minted, P1.', ['4.9.1', '3.6.1', '1.5.1', '2.1.3'], v2(box()),
  req({'op': 'addProgramItem', 'function': 'sleeping', 'name': 'Bedroom', 'count': 3, 'minArea': '11 m2',
       'targetArea': '150 sq ft', 'level': 'L1'}),
  check=resolved_eq({'op': 'addElement', 'collection': 'items', 'id': 'P1',
                     'element': {'function': 'sleeping', 'count': 3, 'targetArea': 150 * FT2, 'minArea': 11 * M2,
                                 'level': 'L1', 'name': 'Bedroom'}}))
T('program', 'add-program-item-named-id', 'addProgramItem with a named ID, an integer area and extras; the item is '
  'added beside the existing ones.', ['4.9.1'], briefed(),
  req({'op': 'addProgramItem', 'id': 'OFF', 'function': 'office', 'minArea': 9 * M2, 'extras': {'source': 'interview'}}),
  check=lambda r, B: ensure(B['program']['items']['OFF'] == {'function': 'office', 'minArea': 9 * M2, 'extras': {'source': 'interview'}}
                            and len(B['program']['items']) == 5, B['program']))
T('program', 'add-program-item-unknown-level', '"level" names L9, which does not exist: FS-OPS-003.', ['4.9.1', '3.3.1'],
  v2(box()), req({'op': 'addProgramItem', 'function': 'sleeping', 'level': 'L9'}), 'rejected', [('FS-OPS-003', [])])
T('program', 'add-program-item-not-a-room-function', 'The item\'s function is passed in as given; "bedroom" is not a '
  'room function of Core 4.1 ("sleeping" is), so the result is invalid.', ['4.9.1', '1.2.3'], v2(box()),
  req({'op': 'addProgramItem', 'function': 'bedroom'}), 'rejected', [('FS-SCH-001', [])])
T('program', 'add-program-item-without-function', 'addProgramItem without "function": FS-OPS-001.', ['1.1.2'], v2(box()),
  req({'op': 'addProgramItem', 'name': 'Bedroom'}), 'rejected', [('FS-OPS-001', [])])
T('program', 'add-element-into-items', 'addElement into "items" adds a program item to the program\'s items, creating '
  'the program and its items in a document that has neither; the ID is minted with the prefix P.',
  ['2.1.3', '2.1.1', '1.5.1'], v2(box()),
  req({'op': 'addElement', 'collection': 'items', 'element': {'function': 'living', 'name': 'Living'}}),
  check=lambda r, B: ensure(B['program'] == {'items': {'P1': {'function': 'living', 'name': 'Living'}}} and r['created'] == ['P1'], B))
T('program', 'add-element-into-items-not-an-object', 'An earlier operation sets the program to a string, so there is '
  'no object to add the item to: FS-OPS-003.', ['2.1.3'], v2(box()),
  req({'op': 'setProperty', 'id': '$document', 'path': '/program', 'value': 'tbd'},
      {'op': 'addElement', 'collection': 'items', 'element': {'function': 'living'}}), 'rejected', [('FS-OPS-003', [])])
T('program', 'program-item-in-a-0.1-document', 'A declares "0.1", which has no program: the item is added, and the '
  'result is checked against Core 0.1\'s schema, which has no "program" member.', ['2.1.3', '1.2.3'], box(),
  req({'op': 'addElement', 'collection': 'items', 'element': {'function': 'living'}}), 'rejected', [('FS-SCH-001', [])])
T('program', 'upgrade-and-add-a-program', 'The same item added in a batch that first declares "0.2": the result is a '
  'Core 0.2 document, and is valid.', ['2.1.3', '2.3.1'], box(),
  req({'op': 'setProperty', 'id': '$document', 'path': '/floorspec', 'value': '0.2'},
      {'op': 'addElement', 'collection': 'items', 'element': {'function': 'living'}}),
  check=lambda r, B: ensure(B['floorspec'] == '0.2' and 'P1' in B['program']['items'] and r['created'] == ['P1'], B))
T('program', 'set-property-of-an-item', 'setProperty addresses a program item by ID like any element: the Kitchen item '
  'now asks for 10 m2.', ['2.3.1'], briefed(),
  req({'op': 'setProperty', 'id': 'KIT', 'path': '/minArea', 'value': 10 * M2}),
  check=lambda r, B: ensure(B['program']['items']['KIT']['minArea'] == 10 * M2, B['program']))
T('program', 'set-property-of-the-brief-of-a-room', '"brief of Kitchen" is the item the Kitchen room fulfils, KIT; and '
  '"item pantry" is the item named Pantry, PAN.', ['3.3.1', '2.3.1'], briefed(),
  req({'op': 'setProperty', 'id': 'brief of Kitchen', 'path': '/targetArea', 'value': 12 * M2},
      {'op': 'unsetProperty', 'id': 'item pantry', 'path': '/name'}),
  check=resolved_eq({'op': 'setProperty', 'id': 'KIT', 'path': '/targetArea', 'value': 12 * M2},
                    {'op': 'unsetProperty', 'id': 'PAN', 'path': '/name'}))
T('program', 'brief-of-a-room-without-one', 'The Living room of the box fulfils no item, so "brief of Living" resolves '
  'to nothing: FS-OPS-003 names the room.', ['3.3.1', '7.1.1'], v2(box(), program={'items': {'P1': item('living')}}),
  req({'op': 'setProperty', 'id': 'brief of Living', 'path': '/count', 'value': 2}), 'rejected', [('FS-OPS-003', ['R1'])])
T('program', 'plain-name-is-the-room', 'A plain name names a room, not an item, where any element is expected: '
  '"Kitchen" in setProperty is the Kitchen room R1, though an item is named Kitchen too.', ['3.3.1', '2.3.1'], briefed(),
  req({'op': 'setProperty', 'id': 'Kitchen', 'path': '/name', 'value': 'Galley'}),
  check=lambda r, B: ensure(B['rooms']['R1']['name'] == 'Galley' and B['program']['items']['KIT']['name'] == 'Kitchen', B))
T('program', 'item-names-are-ambiguous', 'Two items are named "Bedroom": "item Bedroom" matches both, FS-OPS-004.',
  ['3.3.1', '7.1.1'], v2(box(), program={'items': {'B1R': item('sleeping', name='Bedroom'), 'B2R': item('sleeping', name='bedroom')}}),
  req({'op': 'removeElement', 'id': 'item Bedroom'}), 'rejected', [('FS-OPS-004', ['B1R', 'B2R'])])
T('program', 'item-selector-in-a-0.1-document', 'Under "0.1" there are no program items (0.3), so "item Kitchen" '
  'resolves to nothing.', ['3.3.1'], house(), req({'op': 'removeElement', 'id': 'item Kitchen'}), 'rejected',
  [('FS-OPS-003', [])])
T('program', 'remove-item-blocked-by-its-room', 'The Kitchen room\'s brief names KIT, so KIT cannot be removed: '
  'FS-OPS-006 names the item and the room.', ['2.2.1', '7.1.1'], briefed(), req({'op': 'removeElement', 'id': 'KIT'}),
  'rejected', [('FS-OPS-006', ['KIT', 'R1'])])
T('program', 'remove-item-cascade-still-blocked', 'cascade does not apply to a program item: a room that names it '
  'still blocks it.', ['2.2.1', '2.2.2'], briefed(), req({'op': 'removeElement', 'id': 'item Kitchen', 'cascade': True}),
  'rejected', [('FS-OPS-006', ['KIT', 'R1'])])
T('program', 'remove-item-takes-its-adjacencies', 'GAR is fulfilled by no room, so it is removed - and the forbidden '
  'adjacency of GAR and KIT goes with it; the others stay, in their order.', ['2.2.3', '2.2.1'], briefed(),
  req({'op': 'removeElement', 'id': 'GAR'}),
  check=lambda r, B: ensure(B['program']['adjacency'] == [adj('KIT', 'DIN', 'required'), adj('KIT', 'PAN', 'preferred', weight=3)]
                            and r['removed'] == ['GAR'], B['program']))
T('program', 'unbrief-then-remove', 'The room is given no brief first; then its item can be removed, and both its '
  'adjacencies go with it.', ['2.2.3', '2.3.1'], briefed(),
  req({'op': 'unsetProperty', 'id': 'Kitchen', 'path': '/brief'}, {'op': 'removeElement', 'id': 'KIT'}),
  check=lambda r, B: ensure(B['program']['adjacency'] == [] if 'adjacency' in B['program'] else True, B['program']))
T('program', 'remove-level-unsets-item-level', 'Removing the level an item prefers removes the item\'s "level", '
  'whether cascade is true or not: L3 has nothing on it, so it is removed without cascade.', ['2.2.3', '2.2.1'],
  v2(box(), levels={'L3': {'building': 'B1', 'elevation': H, 'height': H}},
     program={'items': {'BED': item('sleeping', level='L3'), 'LIV': item('living', level='L1')}}),
  req({'op': 'removeElement', 'id': 'L3'}),
  check=lambda r, B: ensure(B['program']['items'] == {'BED': {'function': 'sleeping'}, 'LIV': {'function': 'living', 'level': 'L1'}}, B))
T('program', 'remove-level-cascade-unsets-item-level', 'The same when the level is removed with cascade and takes the '
  'loft with it.', ['2.2.3', '2.2.2'], v2(upstairs(), program={'items': {'LOFT': item('sleeping', level='L2')}}),
  req({'op': 'removeElement', 'id': 'L2', 'cascade': True}),
  check=lambda r, B: ensure(B['program']['items'] == {'LOFT': {'function': 'sleeping'}} and 'L2' in r['removed'], B))
T('program', 'add-room-with-brief', 'addRoom with "brief": the item is named, and a plain name in "brief" is an item\'s '
  'name - here "Office", though no room is called that.', ['4.6.1', '3.3.1'],
  v2(two_rooms_apart(), program={'items': {'OFF': item('office', name='Office')}}),
  req({'op': 'removeElement', 'id': 'R2'}, {'op': 'addRoom', 'level': 'L1', 'at': ["25'", "5'"], 'brief': 'Office', 'function': 'office'}),
  check=lambda r, B: ensure(r['resolved'][1]['element'] == {'level': 'L1', 'anchor': [25 * FT, 5 * FT], 'brief': 'OFF', 'function': 'office'}, r['resolved']))
T('program', 'add-room-with-an-unknown-brief', '"brief" names no item: FS-OPS-003.', ['4.6.1', '3.3.1'], briefed(),
  req({'op': 'addRoom', 'level': 'L1', 'at': ["30'", "5'"], 'brief': 'Study'}), 'rejected', [('FS-OPS-003', [])])
T('program', 'set-room-brief', 'setRoomBrief makes the Dining room fulfil the Kitchen item: "Dining" is the room in '
  '"room", and "Kitchen" is the item in "item".', ['4.6.2', '3.3.1'], briefed(),
  req({'op': 'setRoomBrief', 'room': 'Dining', 'item': 'Kitchen'}),
  check=resolved_eq({'op': 'setProperty', 'id': 'R3', 'path': '/brief', 'value': 'KIT'}))
T('program', 'set-room-brief-by-selector', 'setRoomBrief with an item selector and a room ID: the Pantry fulfils '
  'whatever the Kitchen fulfils.', ['4.6.2', '3.3.1'], briefed(),
  req({'op': 'setRoomBrief', 'room': 'R2', 'item': 'brief of Kitchen'}),
  check=resolved_eq({'op': 'setProperty', 'id': 'R2', 'path': '/brief', 'value': 'KIT'}))
T('program', 'set-room-brief-unknown-item', 'No item is named "Study": FS-OPS-003.', ['4.6.2', '3.3.1'], briefed(),
  req({'op': 'setRoomBrief', 'room': 'Dining', 'item': 'Study'}), 'rejected', [('FS-OPS-003', [])])
T('program', 'set-room-brief-to-a-room', '"item" expects a program item: R1, a room, does not count as a match.',
  ['4.6.2', '3.3.1'], briefed(), req({'op': 'setRoomBrief', 'room': 'Dining', 'item': 'R1'}), 'rejected',
  [('FS-OPS-003', [])])
T('program', 'set-adjacency-appends', 'setAdjacency of a pair the program does not relate appends the adjacency: the '
  'Pantry is preferred next to the Dining room, with weight 2. Items are named as they are called.', ['2.6.1', '3.3.1'],
  briefed(), req({'op': 'setAdjacency', 'a': 'Pantry', 'b': 'Dining', 'kind': 'preferred', 'weight': 2}),
  check=lambda r, B: ensure(B['program']['adjacency'][-1] == adj('PAN', 'DIN', 'preferred', weight=2)
                            and len(B['program']['adjacency']) == 4 and r['resolved'][0]['a'] == 'PAN', B['program']))
T('program', 'set-adjacency-replaces-in-place', 'The program already has a preferred adjacency of KIT and PAN; '
  'setAdjacency of the same pair - given the other way round - and kind replaces it where it stands, with the new '
  'weight and its a and b as now written.', ['2.6.1'], briefed(),
  req({'op': 'setAdjacency', 'a': 'PAN', 'b': 'KIT', 'kind': 'preferred', 'weight': 9}),
  check=lambda r, B: ensure(B['program']['adjacency'] == [adj('KIT', 'DIN', 'required'), adj('PAN', 'KIT', 'preferred', weight=9),
                                                          adj('GAR', 'KIT', 'forbidden')], B['program']))
T('program', 'set-adjacency-without-weight', 'Without "weight" the adjacency written has none, so it is 5 (Core 11.2): '
  'the preferred KIT-PAN adjacency loses its weight of 3.', ['2.6.1'], briefed(),
  req({'op': 'setAdjacency', 'a': 'KIT', 'b': 'PAN', 'kind': 'preferred'}),
  check=lambda r, B: ensure(B['program']['adjacency'][1] == adj('KIT', 'PAN', 'preferred'), B['program']))
T('program', 'set-adjacency-another-kind', 'A required adjacency of KIT and PAN is a different adjacency from their '
  'preferred one: it is appended, and both are valid together (Core 11.2.3).', ['2.6.1'], briefed(),
  req({'op': 'setAdjacency', 'a': 'KIT', 'b': 'PAN', 'kind': 'required'}),
  check=lambda r, B: ensure(len(B['program']['adjacency']) == 4, B['program']))
T('program', 'set-adjacency-creates-the-adjacency', 'A program with items and no adjacencies: setAdjacency creates the '
  'adjacency array.', ['2.6.1'], v2(box(), program={'items': {'A1': item('living'), 'A2': item('dining')}}),
  req({'op': 'setAdjacency', 'a': 'A1', 'b': 'A2', 'kind': 'required'}),
  check=lambda r, B: ensure(B['program']['adjacency'] == [adj('A1', 'A2', 'required')], B['program']))
T('program', 'set-adjacency-contradiction', 'Forbidding the Kitchen next to the Dining room, which the brief requires, '
  'is written as asked - and the result is invalid (Core 11.2.3).', ['2.6.1', '1.2.3'], briefed(),
  req({'op': 'setAdjacency', 'a': 'item Kitchen', 'b': 'item Dining', 'kind': 'forbidden'}), 'rejected',
  [('FS-INV-403', ['DIN', 'KIT'])])
T('program', 'set-adjacency-to-itself', 'An item related to itself is written as asked, and makes the result invalid '
  '(Core 11.2.1).', ['2.6.1', '1.2.3'], briefed(), req({'op': 'setAdjacency', 'a': 'KIT', 'b': 'Kitchen', 'kind': 'preferred'}),
  'rejected', [('FS-INV-401', ['KIT'])])
T('program', 'set-adjacency-unknown-item', '"Garden" names no item: FS-OPS-003.', ['3.3.1', '2.6.1'], briefed(),
  req({'op': 'setAdjacency', 'a': 'Kitchen', 'b': 'Garden', 'kind': 'preferred'}), 'rejected', [('FS-OPS-003', [])])
T('program', 'set-adjacency-adjacency-not-an-array', 'An earlier operation sets the adjacency to a string: '
  'FS-OPS-003.', ['2.6.1'], briefed(),
  req({'op': 'setProperty', 'id': '$document', 'path': '/program/adjacency', 'value': 'tbd'},
      {'op': 'setAdjacency', 'a': 'KIT', 'b': 'PAN', 'kind': 'required'}), 'rejected', [('FS-OPS-003', [])])
T('program', 'remove-adjacency', 'removeAdjacency of the forbidden pair, written the other way round: it is removed '
  'and the other two keep their order.', ['2.6.1'], briefed(),
  req({'op': 'removeAdjacency', 'a': 'Kitchen', 'b': 'Garage', 'kind': 'forbidden'}),
  check=lambda r, B: ensure(B['program']['adjacency'] == [adj('KIT', 'DIN', 'required'), adj('KIT', 'PAN', 'preferred', weight=3)], B['program']))
T('program', 'remove-adjacency-of-another-kind', 'KIT and DIN have a required adjacency, not a preferred one: '
  'removeAdjacency matches nothing, FS-OPS-003.', ['2.6.1', '7.1.1'], briefed(),
  req({'op': 'removeAdjacency', 'a': 'KIT', 'b': 'DIN', 'kind': 'preferred'}), 'rejected', [('FS-OPS-003', [])])
T('program', 'remove-adjacency-without-a-program', 'A document with no program has no adjacency to remove: '
  'FS-OPS-003 - the items do not resolve first.', ['2.6.1', '3.3.1'], v2(box()),
  req({'op': 'removeAdjacency', 'a': 'KIT', 'b': 'DIN', 'kind': 'required'}), 'rejected', [('FS-OPS-003', [])])
T('program', 'set-property-document-program', 'setProperty of $document /program/adjacency/1/weight edits an '
  'adjacency by its place, which a batch may do as well.', ['2.3.1'], briefed(),
  req({'op': 'setProperty', 'id': '$document', 'path': '/program/adjacency/1/weight', 'value': 7}),
  check=lambda r, B: ensure(B['program']['adjacency'][1]['weight'] == 7, B['program']))
T('program', 'unset-property-document-program', 'unsetProperty of $document /program removes the whole program; the '
  'rooms\' briefs are removed too, first, or the result would name missing items.', ['2.3.1'], briefed(),
  req(*[{'op': 'unsetProperty', 'id': r_, 'path': '/brief'} for r_ in ('R1', 'R2', 'R3')],
      {'op': 'unsetProperty', 'id': '$document', 'path': '/program'}),
  check=lambda r, B: ensure('program' not in B and r['removed'] == ['DIN', 'GAR', 'KIT', 'PAN'], B))
T('program', 'draw-a-bubble-diagram', 'A brief drawn as a bubble diagram from nothing, in one batch: four items, three '
  'lines between them by name, and the existing room given the living item. Every ID is minted, P1 to P4.',
  ['4.9.1', '2.6.1', '4.6.2', '1.5.1'], v2(box()),
  req({'op': 'addProgramItem', 'function': 'living', 'name': 'Living room', 'minArea': '200 sq ft'},
      {'op': 'addProgramItem', 'function': 'kitchen', 'name': 'Kitchen', 'minArea': '8 m2'},
      {'op': 'addProgramItem', 'function': 'dining', 'name': 'Dining'},
      {'op': 'addProgramItem', 'function': 'garage', 'name': 'Garage', 'targetArea': '22 m2'},
      {'op': 'setAdjacency', 'a': 'Kitchen', 'b': 'Dining', 'kind': 'required', 'weight': 10},
      {'op': 'setAdjacency', 'a': 'Living room', 'b': 'Dining', 'kind': 'preferred'},
      {'op': 'setAdjacency', 'a': 'Garage', 'b': 'Living room', 'kind': 'forbidden'},
      {'op': 'setRoomBrief', 'room': 'Living', 'item': 'Living room'}),
  check=lambda r, B: ensure(sorted(B['program']['items']) == ['P1', 'P2', 'P3', 'P4']
                            and B['program']['adjacency'] == [adj('P2', 'P3', 'required', weight=10), adj('P1', 'P3', 'preferred'),
                                                              adj('P4', 'P1', 'forbidden')]
                            and B['rooms']['R1']['brief'] == 'P1' and r['created'] == ['P1', 'P2', 'P3', 'P4'], B['program']))


# ============================================================================= hosting

OUT = {'fallback': {'box': copy.deepcopy(OUTLET_BOX)}, 'device': 'receptacle'}
PIECE = {'fallback': {'box': copy.deepcopy(PIECE_BOX)}, 'piece': 'side table'}


def place(host, element=OUT, x=ELEC, c='devices', **kw):
    return {'op': 'placeElement', 'extension': x, 'collection': c, 'host': host, 'element': copy.deepcopy(element), **kw}


def wall_face(wall, at, height=300 * MM, side=None, toward=None):
    h = {'mode': 'wallFace', 'wall': wall, 'at': at, 'height': height}
    if side is not None:
        h['side'] = side
    if toward is not None:
        h['toward'] = toward
    return h


def placed(eid, host, x=ELEC, c='devices', element=OUT, level='L1'):
    """A check: the batch's one primitive adds `element` as the extension element `eid` with this host."""
    el = copy.deepcopy(element)
    el['host'] = host
    el['fallback']['level'] = level
    return resolved_eq({'op': 'addElement', 'extension': x, 'collection': c, 'id': eid, 'element': el})


def half_root_2(n):
    """round(n * sqrt(2) / 2), ties to even, exactly."""
    from fractions import Fraction
    from tools.oracle.surd import Surd
    return Surd.sqrt(2, Fraction(n, 2)).round()


# The box and the start of a courtyard east of it: W7 runs west from NE (20', 10') and stops at J7 (13', 10').
COURTYARD_OUTLET = wired(courtyard(), devices={'X1': outlet('W7', 2 * FT, side='left')})

T('hosting', 'place-an-outlet-toward-a-room', 'placeElement puts a receptacle on the face of the Living room\'s north '
  'wall that looks into the room: W2 runs east, the room is on its right, so the side is "right"; 2\' from its start '
  'and 12" above its base. The element is passed in as given, with its host and its fallback\'s level set; its ID is '
  'minted, X1, and the extension\'s data is created.', ['4.10.1', '2.1.3', '1.5.1', '3.5.1'], wired(box()),
  req(place(wall_face('north wall of Living', "2' from start", '12"', toward='Living'))),
  check=placed('X1', {'mode': 'wallFace', 'wall': 'W2', 'side': 'right', 'offset': 2 * FT, 'height': 12 * IN}))
T('hosting', 'place-an-outlet-on-the-outer-face', 'With "side" the face is given: the left face of W1, outside.',
  ['4.10.1'], wired(box()), req(place(wall_face('W1', "3'", side='left'))),
  check=placed('X1', {'mode': 'wallFace', 'wall': 'W1', 'side': 'left', 'offset': 3 * FT, 'height': 300 * MM}))
T('hosting', 'place-centered-and-from-end', 'A hosted element is placed by a point, so a position is resolved with '
  'width 0: "centered" on the 12\' wall W2 is 6\', and "3\' from end" is 9\'.', ['4.10.1', '3.5.1'], wired(box()),
  req(place(wall_face('W2', 'centered', side='right')), place(wall_face('W2', "3' from end", side='right'))),
  check=lambda r, B: ensure([p['element']['host']['offset'] for p in r['resolved']] == [6 * FT, 9 * FT], r['resolved']))
T('hosting', 'place-centered-on-an-oblique-wall', 'The chamfer W3 runs from (6\', 10\') to (10\', 6\'), 4\' x sqrt(2) '
  'long: "centered" is 2\' x sqrt(2), 1103493.87..., rounded once: 1103494.', ['4.10.1', '3.5.1'], wired(chamfered()),
  req(place(wall_face('W3', 'centered', side='right'))),
  check=lambda r, B: ensure(r['resolved'][0]['element']['host']['offset'] == half_root_2(4 * FT) == 1103494, r['resolved']))
T('hosting', 'place-toward-a-room-not-beside-the-wall', 'W2 is the Living room\'s north wall; the Office is a separate '
  'room 8\' east, so its face is on neither side of W2: FS-OPS-008 names the wall.', ['4.10.1', '7.1.1'],
  wired(two_rooms_apart()), req(place(wall_face('W2', "2'", toward='Office'))), 'rejected', [('FS-OPS-008', ['W2'])])
T('hosting', 'place-toward-on-a-crossed-level', 'A wall drawn across the room earlier in the batch leaves L1 with '
  'crossing walls, so a host that reads faces to find "toward" cannot: FS-OPS-007 names the level.', ['3.4.1'],
  wired(box()), req({'op': 'drawWall', 'level': 'L1', 'from': ["-2'", "5'"], 'to': ["14'", "5'"]},
                    place(wall_face('W2', "2'", toward='Living'))), 'rejected', [('FS-OPS-007', ['L1'])])
T('hosting', 'place-on-a-floor', 'A side table on the Living room\'s floor at (3\', 4\'), turned a quarter turn: the '
  'rotation, an angle in microdegrees, is taken as given.', ['4.10.1'], wired(box()),
  req(place({'mode': 'surface', 'room': 'Living', 'surface': 'floor', 'at': ["3'", "4'"], 'rotation': 90000000}, PIECE, FURN, 'pieces')),
  check=placed('X1', {'mode': 'surface', 'room': 'R1', 'surface': 'floor', 'position': [3 * FT, 4 * FT], 'rotation': 90000000},
               FURN, 'pieces', PIECE))
T('hosting', 'place-on-a-ceiling-by-room-name', 'A pendant on the ceiling of "living" - a room name, compared '
  'ignoring case - at (6\', 5\'), its coordinates written as lengths.', ['4.10.1', '3.3.1'], wired(box()),
  req(place({'mode': 'surface', 'room': 'living', 'surface': 'ceiling', 'at': ["6'", "5'"]}, PIECE, FURN, 'pieces')),
  check=placed('X1', {'mode': 'surface', 'room': 'R1', 'surface': 'ceiling', 'position': [6 * FT, 5 * FT]}, FURN, 'pieces', PIECE))
T('hosting', 'place-free-on-a-level', 'A bench standing free on L1, 3\' east of the box\'s corner J4, outside every '
  'room.', ['4.10.1', '3.2.1'], wired(box()),
  req(place({'mode': 'free', 'level': 'L1', 'at': "3' east of J4"}, PIECE, FURN, 'pieces')),
  check=placed('X1', {'mode': 'free', 'level': 'L1', 'position': [15 * FT, 0]}, FURN, 'pieces', PIECE))
T('hosting', 'place-replaces-host-and-fallback-level', 'An element given with a host of its own and a fallback on L9: '
  'placeElement replaces both with the host it resolves and that host\'s level.', ['4.10.1'], wired(box()),
  req(place(wall_face('W2', "2'", side='right'), {'fallback': {'level': 'L9', 'box': OUTLET_BOX}, 'host': {'mode': 'free'}})),
  check=placed('X1', {'mode': 'wallFace', 'wall': 'W2', 'side': 'right', 'offset': 2 * FT, 'height': 300 * MM},
               element={'fallback': {'level': 'L9', 'box': OUTLET_BOX}}))
T('hosting', 'place-without-a-fallback', 'An element with no fallback gets one of its host\'s level only - and a '
  'fallback needs a box, so the result is invalid.', ['4.10.1', '1.2.3'], wired(box()),
  req(place(wall_face('W2', "2'", side='right'), {'device': 'receptacle'})), 'rejected', [('FS-SCH-001', [])])
T('hosting', 'place-past-the-wall-end', 'At 13\' along the 12\' wall W2: the element is added as asked, and the '
  'result is invalid (Core 13.3.2).', ['4.10.1', '1.2.3'], wired(box()), req(place(wall_face('W2', "13'", side='right'))),
  'rejected', [('FS-INV-501', ['X1'])])
T('hosting', 'place-in-an-undeclared-extension', 'The document declares the furniture extension only: placing a device '
  'creates electrical data that no declaration names, and the result is invalid (Core 1.6.3).', ['2.1.3', '1.2.3'],
  wired(box(), used=(FURN,)), req(place(wall_face('W2', "2'", side='right'))), 'rejected', [('FS-INV-005', [])])
T('hosting', 'place-on-a-wall-without-a-level', 'W1\'s level is removed earlier in the batch, so the host has no level '
  'to give the fallback: FS-OPS-003 names the wall.', ['4.10.1', '7.1.1'], wired(box()),
  req({'op': 'unsetProperty', 'id': 'W1', 'path': '/level'}, place(wall_face('W1', "2'", side='right'))), 'rejected',
  [('FS-OPS-003', ['W1'])])
T('hosting', 'place-with-side-and-toward', 'A wall-face host takes exactly one of "side" and "toward": FS-OPS-001.',
  ['1.1.2'], wired(box()), req(place(wall_face('W2', "2'", side='right', toward='Living'))), 'rejected',
  [('FS-OPS-001', [])])
T('hosting', 'add-element-into-an-extension-collection', 'addElement with "extension" adds an extension element to '
  'that extension\'s collection, creating its data, "collections" and the collection; the ID is minted with X.',
  ['2.1.3', '2.1.1', '1.5.1'], wired(box()),
  req({'op': 'addElement', 'extension': ELEC, 'collection': 'devices', 'element': outlet('W2', 2 * FT)}),
  check=lambda r, B: ensure(B['extensions'] == {ELEC: {'collections': {'devices': {'X1': outlet('W2', 2 * FT)}}}} and r['created'] == ['X1'], B))
T('hosting', 'add-element-extension-data-not-an-object', 'An earlier operation sets the electrical extension\'s data '
  'to a string, so there is no collection to add the device to: FS-OPS-003.', ['2.1.3'], wired(box()),
  req({'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_electrical', 'value': 'legacy'},
      {'op': 'addElement', 'extension': ELEC, 'collection': 'devices', 'element': outlet('W2', 2 * FT)}),
  'rejected', [('FS-OPS-003', [])])
T('hosting', 'extension-data-in-a-0.1-document', 'In a document that declares "0.1" top-level extension data is opaque '
  '(Core 1.2.4): the device is added where it is asked to be, the result is a valid 0.1 document, and nothing is '
  'created - it is not an element there.', ['2.1.3'], v01.box(extensionsUsed={ELEC: '0.1.0'}),
  req({'op': 'addElement', 'extension': ELEC, 'collection': 'devices', 'element': outlet('W2', 2 * FT)}),
  check=lambda r, B: ensure(r['created'] == [] and 'X1' in B['extensions'][ELEC]['collections']['devices'], r))
T('hosting', 'move-element-to-another-wall', 'moveElement sets the outlet\'s host to the east wall of the Living room, '
  'on its inner face, 1\' from its start, and its fallback\'s level to that wall\'s.', ['4.10.1'],
  wired(box(), devices={'X1': outlet('W2', 2 * FT)}),
  req({'op': 'moveElement', 'element': 'X1', 'host': wall_face('east wall of Living', "1' from start", 450 * MM, toward='Living')}),
  check=resolved_eq({'op': 'setProperty', 'id': 'X1', 'path': '/host',
                     'value': {'mode': 'wallFace', 'wall': 'W3', 'side': 'right', 'offset': FT, 'height': 450 * MM}},
                    {'op': 'setProperty', 'id': 'X1', 'path': '/fallback/level', 'value': 'L1'}))
T('hosting', 'move-element-by-name', 'Where an extension element is expected, a plain string also matches extension '
  'elements by name: "fridge outlet" is X1.', ['4.10.1', '3.3.1'],
  wired(box(), devices={'X1': outlet('W2', 2 * FT, name='Fridge outlet'), 'X2': outlet('W2', 8 * FT)}),
  req({'op': 'moveElement', 'element': 'fridge outlet', 'host': wall_face('W2', "4'", side='right')}),
  check=first_resolved({'op': 'setProperty', 'id': 'X1', 'path': '/host',
                        'value': {'mode': 'wallFace', 'wall': 'W2', 'side': 'right', 'offset': 4 * FT, 'height': 300 * MM}}))
T('hosting', 'move-element-to-another-level', 'A side table on the Living room\'s floor moves up to the Loft\'s floor '
  'on L2: its fallback\'s level becomes L2.', ['4.10.1'],
  wired(upstairs(), pieces={'X1': standing('R1', 3 * FT, 4 * FT)}),
  req({'op': 'moveElement', 'element': 'X1', 'host': {'mode': 'surface', 'room': 'Loft', 'surface': 'floor', 'at': ["4'", "4'"]}}),
  check=lambda r, B: ensure(ext_of(B, FURN, 'pieces')['X1']['fallback']['level'] == 'L2'
                            and ext_of(B, FURN, 'pieces')['X1']['host'] == {'mode': 'surface', 'room': 'R2', 'surface': 'floor', 'position': [4 * FT, 4 * FT]}, B))
T('hosting', 'move-element-not-an-extension-element', '"element" expects an extension element: R1 is a room, so it '
  'does not count as a match.', ['4.10.1', '3.3.1'], wired(box(), devices={'X1': outlet('W2', 2 * FT)}),
  req({'op': 'moveElement', 'element': 'R1', 'host': wall_face('W2', "4'", side='right')}), 'rejected', [('FS-OPS-003', [])])
T('hosting', 'set-property-of-an-extension-element', 'setProperty addresses an extension element by ID: the outlet '
  'is raised to 600 mm, a path relative to the element.', ['2.3.1'], wired(box(), devices={'X1': outlet('W2', 2 * FT)}),
  req({'op': 'setProperty', 'id': 'X1', 'path': '/host/height', 'value': 600 * MM}),
  check=lambda r, B: ensure(ext_of(B)['X1']['host']['height'] == 600 * MM, B))
T('hosting', 'remove-an-extension-element', 'removeElement removes an extension element; nothing depends on one, and '
  'its collection stays, empty.', ['2.2.1'], wired(box(), devices={'X1': outlet('W2', 2 * FT)}),
  req({'op': 'removeElement', 'id': 'X1'}),
  check=lambda r, B: ensure(ext_of(B) == {} and r['removed'] == ['X1'], B))
T('hosting', 'remove-wall-blocked-by-an-outlet', 'An outlet is on the courtyard wall W7: W7 cannot be removed without '
  'cascade, and FS-OPS-006 names the wall and the outlet.', ['2.2.1', '7.1.1'], COURTYARD_OUTLET,
  req({'op': 'removeElement', 'id': 'W7'}), 'rejected', [('FS-OPS-006', ['W7', 'X1'])])
T('hosting', 'remove-wall-cascade-takes-its-outlets', 'With cascade, the wall takes the outlet on it.', ['2.2.2'],
  COURTYARD_OUTLET, req({'op': 'removeElement', 'id': 'W7', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['W7', 'X1'] and ext_of(B) == {}, r))
T('hosting', 'remove-room-blocked-by-furniture', 'A side table stands on the Living room\'s floor: the room cannot be '
  'removed without cascade.', ['2.2.1'], wired(box(), pieces={'X1': standing('R1', 3 * FT, 4 * FT)}),
  req({'op': 'removeElement', 'id': 'Living'}), 'rejected', [('FS-OPS-006', ['R1', 'X1'])])
T('hosting', 'remove-room-cascade-takes-its-furniture', 'With cascade, the room takes what is on its floor and ceiling, '
  'and nothing else: the bench standing free outside stays.', ['2.2.2'],
  wired(box(), pieces={'X1': standing('R1', 3 * FT, 4 * FT), 'X2': standing('R1', 6 * FT, 5 * FT, surface='ceiling'),
                       'X3': free('L1', 15 * FT, 0)}),
  req({'op': 'removeElement', 'id': 'R1', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['R1', 'X1', 'X2'] and list(ext_of(B, FURN, 'pieces')) == ['X3'], r))
T('hosting', 'remove-level-blocked-by-a-free-element', 'L3 holds only a bench standing free on it: the bench blocks '
  'the level\'s removal.', ['2.2.1'],
  wired(box(), levels={'L3': {'building': 'B1', 'elevation': H, 'height': H}}, pieces={'X1': free('L3', 0, 0)}),
  req({'op': 'removeElement', 'id': 'L3'}), 'rejected', [('FS-OPS-006', ['L3', 'X1'])])
T('hosting', 'remove-level-cascade-takes-extension-elements', 'L2 removed with cascade takes, besides its walls, room, '
  'slab and window, the outlet on V1, the table on the Loft\'s floor and the chest standing free on L2 - and not the '
  'table downstairs.', ['2.2.2'],
  wired(upstairs(), devices={'X1': outlet('V1', 2 * FT, level='L2')},
        pieces={'X2': standing('R2', 4 * FT, 4 * FT, level='L2'), 'X3': free('L2', 9 * FT, 9 * FT), 'X4': standing('R1', 3 * FT, 4 * FT)}),
  req({'op': 'removeElement', 'id': 'L2', 'cascade': True}),
  check=lambda r, B: ensure({'X1', 'X2', 'X3'} <= set(r['removed']) and 'X4' not in r['removed']
                            and list(ext_of(B, FURN, 'pieces')) == ['X4'], r['removed']))
T('hosting', 'remove-asset-blocked-by-a-fallback', 'A model asset is a piece\'s fallback model: removing the asset is '
  'blocked by the piece.', ['2.2.1'],
  wired(box(), assets={'A1': {'mediaType': 'model/gltf-binary', 'sha256': 'ab' * 32, 'path': 'assets/table.glb'}},
        pieces={'X1': {**standing('R1', 3 * FT, 4 * FT), 'fallback': {'level': 'L1', 'box': PIECE_BOX, 'asset': 'A1'}}}),
  req({'op': 'removeElement', 'id': 'A1', 'cascade': True}), 'rejected', [('FS-OPS-006', ['A1', 'X1'])])
T('hosting', 'move-a-wall-and-watch-them-follow', 'The Phase 5 demo. Outlets on three walls of the box, and the east '
  'wall W3 moved 2\' east: no outlet changes - their hosts are relative - yet the one on W3 is now 2\' further east; '
  'the one on the north wall W2, measured from W2\'s start J2, stays where it is; and the one on the south wall W4, '
  'which runs west from the corner that moved, moves 2\' east with its start (2.7).', ['2.7.1', '4.2.1'],
  wired(box(), devices={'X1': outlet('W3', 4 * FT), 'X2': outlet('W2', 3 * FT), 'X3': outlet('W4', 3 * FT)}),
  req({'op': 'moveWall', 'wall': 'east wall of Living', 'by': "2'"}),
  check=lambda r, B: ensure(ext_of(B) == ext_of(r['_a']) and moved(r['_a'], B, 'X1') == [2 * FT, 0, 0]
                            and moved(r['_a'], B, 'X2') == [0, 0, 0] and moved(r['_a'], B, 'X3') == [2 * FT, 0, 0], B))
T('hosting', 'resize-a-room-and-watch-them-follow', 'The Kitchen made 2\' wider, with an outlet on its east wall W8: '
  'W8 now runs from the moved J7 to the new junction of the jog, so the outlet, 4\' from W8\'s start, follows it 2\' '
  'east and is unchanged.', ['2.7.1', '4.4.1'],
  wired(house(), devices={'X1': outlet('W8', 4 * FT, side='left')}), req(KITCHEN_WIDER),
  check=lambda r, B: ensure(ext_of(B) == ext_of(r['_a']) and moved(r['_a'], B, 'X1') == [2 * FT, 0, 0], B))
T('hosting', 'move-a-corner-under-an-outlet', 'The corner J2, the start of the north wall W2, is dragged 1\' east along '
  'it: the outlet 3\' along W2 moves with W2\'s start, as an opening does, and is unchanged.', ['2.7.1', '2.4.1'],
  wired(box(), devices={'X1': outlet('W2', 3 * FT)}), req({'op': 'moveJunction', 'id': 'J2', 'to': "1' east of J2"}),
  check=lambda r, B: ensure(ext_of(B) == ext_of(r['_a']) and moved(r['_a'], B, 'X1') == [FT, 0, 0], B))
T('hosting', 'merged-junctions-leave-outlets', 'The garden wall\'s end G3 is dragged onto the box\'s corner J3. The '
  'two junctions merge into G3 (both were in A; G3 sorts first), and W2 and W3, which ended and started at J3, are '
  'redirected to G3 at the same position: the outlets on them do not move or change (5.1).', ['2.7.1', '5.1.1'],
  wired(garden(), devices={'X1': outlet('W2', 3 * FT), 'X2': outlet('W3', 4 * FT), 'X3': outlet('W6', 2 * FT, side='left')}),
  req({'op': 'moveJunction', 'id': 'G3', 'to': 'J3'}),
  check=lambda r, B: ensure(ext_of(B) == ext_of(r['_a']) and r['removed'] == ['J3']
                            and moved(r['_a'], B, 'X1') == [0, 0, 0] and moved(r['_a'], B, 'X2') == [0, 0, 0], B))
T('hosting', 'move-a-room-with-its-furniture', 'moveRoom moves what is on the room\'s floor and ceiling by the same '
  'vector, by ID after the anchor: the table and the pendant move 1\' west; the bench standing free outside does '
  'not.', ['4.3.1'],
  wired(box(), pieces={'X1': standing('R1', 3 * FT, 4 * FT), 'X2': standing('R1', 6 * FT, 5 * FT, surface='ceiling'),
                       'X3': free('L1', 15 * FT, 0)}),
  req({'op': 'moveRoom', 'room': 'Living', 'by': "1' west"}),
  check=lambda r, B: ensure(r['resolved'][-2:] == [{'op': 'setProperty', 'id': 'X1', 'path': '/host/position', 'value': [2 * FT, 4 * FT]},
                                                   {'op': 'setProperty', 'id': 'X2', 'path': '/host/position', 'value': [5 * FT, 5 * FT]}]
                            and r['resolved'][-3]['path'] == '/anchor', r['resolved']))
T('hosting', 'remove-a-wall-and-keep-the-furniture', 'The wall between the Kitchen and the Dining room removed, '
  'keeping the Kitchen: the dining table is re-hosted on the Kitchen\'s floor before the Dining room is removed, and '
  'the outlet on the wall goes with the wall.', ['4.7.1', '2.2.2'],
  wired(house(), devices={'X1': outlet('W8', 4 * FT, side='left')}, pieces={'X2': standing('R3', 18 * FT, 6 * FT)}),
  req({'op': 'removeWall', 'wall': 'wall between Kitchen and Dining', 'keep': 'Kitchen'}),
  check=lambda r, B: ensure(r['resolved'] == [{'op': 'setProperty', 'id': 'X2', 'path': '/host/room', 'value': 'R1'},
                                              {'op': 'removeElement', 'id': 'R3'},
                                              {'op': 'removeElement', 'id': 'W8', 'cascade': True}]
                            and r['removed'] == ['R3', 'W8', 'X1'], r))


def split_check(r, B):
    """5.2 step 6: W2 is split at (4', 10'), 4' from its start, and W4 at (4', 0), 8' from its start.
    The outlet 2' along W2 stays on W2; those at 4', 9' and 12' go to the piece of W2 that starts at
    the new junction, at 0, 5' and 8'; the one 9' along W4 to W4's second piece, at 1'. And every
    outlet derives exactly the placement it had."""
    def wall(start, end):
        return next(w for w, e in B['walls'].items() if B['junctions'][e['start']]['position'] == start
                    and B['junctions'][e['end']]['position'] == end)
    n2, n4 = wall([4 * FT, 10 * FT], [12 * FT, 10 * FT]), wall([4 * FT, 0], [0, 0])
    hosts = {k: (v['host']['wall'], v['host']['offset']) for k, v in ext_of(B).items()}
    ensure(hosts == {'X1': ('W2', 2 * FT), 'X2': (n2, 0), 'X3': (n2, 5 * FT), 'X4': (n2, 8 * FT), 'X5': (n4, FT)}, hosts)
    da, db = derived(r['_a'])['placements'], derived(B)['placements']
    ensure(da == db, (da, db))


SPLIT_OUTLETS = wired(box(), devices={'X1': outlet('W2', 2 * FT), 'X2': outlet('W2', 4 * FT), 'X3': outlet('W2', 9 * FT),
                                      'X4': outlet('W2', 12 * FT), 'X5': outlet('W4', 9 * FT)})
SPLIT_AT_4 = {'op': 'drawWall', 'level': 'L1', 'from': ["4'", "-1'"], 'to': ["4'", "11'"], 'type': 'WT'}
T('hosting', 'split-a-wall-under-its-outlets', 'A wall drawn across the box at x = 4\' splits the north wall W2 at '
  '(4\', 10\'). The outlet at 2\' stays on W2; the one exactly at 4\' goes to the piece that starts there, at 0; '
  'those at 9\' and at the wall\'s very end, 12\', to that piece at 5\' and 8\'. W4 is split too, 8\' from its start: '
  'the outlet 9\' along it goes to its second piece. Every outlet derives the same placement as before.',
  ['5.2.2', '5.2.1', '2.7.1'], SPLIT_OUTLETS, req(SPLIT_AT_4),
  check=split_check)


def oblique_offset():
    """round(3' - 2' x sqrt(2)), exactly."""
    from tools.oracle.surd import Surd
    return (Surd(3 * FT) - Surd.sqrt(2, 2 * FT)).round()


T('hosting', 'split-an-oblique-wall-under-an-outlet', 'A wall drawn down to the chamfer W3 ends on it at (8\', 8\'), '
  '2\' x sqrt(2) from W3\'s start: the outlet 2\' along W3 stays; the one 3\' along goes to the second piece at '
  '3\' - 2\' x sqrt(2), 66938.13..., rounded once: 66938.', ['5.2.2'],
  wired(chamfered(), devices={'X1': outlet('W3', 2 * FT), 'X2': outlet('W3', 3 * FT)}),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["8'", "12'"], 'to': ["8'", "8'"], 'type': 'WT'}),
  check=lambda r, B: ensure(ext_of(B)['X1']['host'] == outlet('W3', 2 * FT)['host'] and ext_of(B)['X2']['host']['wall'] != 'W3'
                            and ext_of(B)['X2']['host']['offset'] == oblique_offset() == 66938, ext_of(B)))


T('hosting', 'outlet-past-the-end-of-a-split-wall', 'An outlet set 13\' along the 12\' wall W2 earlier in the batch, '
  'then W2 split at 4\': no piece contains it, so it stays on W2, the first piece, unchanged - and the result is '
  'invalid.', ['5.2.2', '1.2.3'], SPLIT_OUTLETS,
  req({'op': 'setProperty', 'id': 'X1', 'path': '/host/offset', 'value': 13 * FT}, SPLIT_AT_4), 'rejected',
  [('FS-INV-501', ['X1'])])

# ============================================================================= locks: extension elements and items

T('locks', 'outlet-lock-wall-moved', 'An element lock on the outlet X1: its content is unchanged when its wall W3 '
  'moves, but an outlet follows its wall, so the lock holds the wall\'s junctions too, and the move breaks it.',
  ['6.1.2'], wired(box(), devices={'X1': outlet('W3', 4 * FT)}),
  req({'op': 'moveWall', 'wall': 'W3', 'by': "1'"}, locks=[{'element': 'X1'}]), 'rejected', [('FS-OPS-011', ['X1'])])
T('locks', 'outlet-lock-holds', 'The same lock while the opposite wall W1 moves: W3\'s junctions stay, the lock holds.',
  ['6.1.2'], wired(box(), devices={'X1': outlet('W3', 4 * FT)}),
  req({'op': 'moveWall', 'wall': 'W1', 'by': "1'"}, locks=[{'element': 'X1'}]))
T('locks', 'item-lock-broken', 'An element lock on the program item KIT: changing its minimum area breaks it.',
  ['6.1.2'], briefed(), req({'op': 'setProperty', 'id': 'KIT', 'path': '/minArea', 'value': 9 * M2}, locks=[{'element': 'KIT'}]),
  'rejected', [('FS-OPS-011', ['KIT'])])
T('locks', 'item-lock-holds-while-the-room-changes', 'The Kitchen item is locked while the Kitchen room is made 2\' '
  'wider: the item is unchanged, so the batch commits.', ['6.1.2'], briefed(), req(KITCHEN_WIDER, locks=[{'element': 'KIT'}]))
T('locks', 'lock-names-a-missing-extension-element', 'An element lock on X9, which is in A neither as an element nor '
  'as a program item or an extension element: FS-OPS-010.', ['6.1.1'], wired(box(), devices={'X1': outlet('W3', 4 * FT)}),
  req({'op': 'moveWall', 'wall': 'W1', 'by': "1'"}, locks=[{'element': 'X9'}]), 'rejected', [('FS-OPS-010', ['X9'])])

# ============================================================================= inverse: program and extension data

T('inverse', 'inverse-of-placing-an-element', 'Placing the first device creates the extension\'s data; the inverse '
  'removes the device, then - comparing A with what that leaves, as it is - removes the data it emptied.', ['1.6.1'],
  wired(box()), req(place(wall_face('W2', "2'", side='right'))),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'removeElement', 'id': 'X1'},
                                             {'op': 'unsetProperty', 'id': '$document', 'path': '/extensions'}], r['inverse']))
T('inverse', 'inverse-of-a-cascade-with-outlets', 'The inverse of removing a wall that took an outlet with it adds '
  'the wall back, then the outlet - extension elements come last in step 3, after what they are hosted on.', ['1.6.1'],
  COURTYARD_OUTLET, req({'op': 'removeElement', 'id': 'W7', 'cascade': True}),
  check=lambda r, B: ensure([(p['op'], p['id']) for p in r['inverse']] == [('addElement', 'W7'), ('addElement', 'X1')]
                            and r['inverse'][1]['extension'] == ELEC and r['inverse'][1]['collection'] == 'devices', r['inverse']))
T('inverse', 'inverse-of-moving-an-element', 'The inverse of moveElement sets the outlet\'s host back.', ['1.6.1'],
  wired(box(), devices={'X1': outlet('W2', 2 * FT)}),
  req({'op': 'moveElement', 'element': 'X1', 'host': wall_face('W3', "1'", side='right')}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'setProperty', 'id': 'X1', 'path': '/host', 'value': outlet('W2', 2 * FT)['host']}], r['inverse']))
T('inverse', 'inverse-of-a-removed-item', 'The inverse of removing GAR adds the item back and restores the adjacency '
  'that went with it - the program\'s adjacency, compared member by member as $document /program/adjacency.', ['1.6.1'],
  briefed(), req({'op': 'removeElement', 'id': 'GAR'}),
  check=lambda r, B: ensure([(p['op'], p.get('id'), p.get('path')) for p in r['inverse']]
                            == [('addElement', 'GAR', None), ('setProperty', '$document', '/program/adjacency')], r['inverse']))
T('inverse', 'inverse-of-a-brief', 'The inverse of adding an item and making the Living room fulfil it: the room\'s '
  'brief is removed first (step 1), so that the item can be removed (step 2), and then the program the batch created.',
  ['1.6.1'], v2(box()),
  req({'op': 'addProgramItem', 'function': 'living', 'name': 'Living'}, {'op': 'setRoomBrief', 'room': 'R1', 'item': 'Living'}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'unsetProperty', 'id': 'R1', 'path': '/brief'},
                                             {'op': 'removeElement', 'id': 'P1'},
                                             {'op': 'unsetProperty', 'id': '$document', 'path': '/program'}], r['inverse']))
T('inverse', 'inverse-of-a-split-under-outlets', 'The inverse of the split under the outlets sets each re-hosted '
  'outlet\'s host back before it removes the pieces.', ['1.6.1', '5.2.2'], SPLIT_OUTLETS, req(SPLIT_AT_4),
  check=lambda r, B: ensure([p['id'] for p in r['inverse'][:3]] == ['X2', 'X3', 'X4'], r['inverse']))

# ============================================================================= ids: one space

T('ids', 'mint-a-program-item', 'Items P1 and P7 exist: the next item minted is P8.', ['1.5.1'],
  v2(box(), program={'items': {'P1': item('living'), 'P7': item('dining')}}),
  req({'op': 'addProgramItem', 'function': 'kitchen'}),
  check=lambda r, B: ensure(r['created'] == ['P8'], r['created']))
T('ids', 'mint-across-the-one-space', 'Every extension collection mints with X, from the largest X-number anywhere in '
  'the document: a furniture piece X2 and a program item called X5 make the next device X6.', ['1.5.1'],
  wired(box(), pieces={'X2': standing('R1', 3 * FT, 4 * FT)}, program={'items': {'X5': item('living')}}),
  req(place(wall_face('W2', "2'", side='right'))),
  check=lambda r, B: ensure(r['created'] == ['X6'], r['created']))
T('ids', 'mint-a-wall-after-an-item', 'A program item called W9 is in the one space of IDs, so the next wall drawn is '
  'W10.', ['1.5.1'], v2(box(), program={'items': {'W9': item('living')}}),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["14'", 0], 'to': ["14'", "4'"], 'type': 'WT'}),
  check=lambda r, B: ensure('W10' in r['created'], r['created']))
T('ids', 'item-id-used-by-a-wall', 'An item named W1 - a wall\'s ID: FS-OPS-005.', ['1.5.2', '2.1.1'], v2(box()),
  req({'op': 'addElement', 'collection': 'items', 'id': 'W1', 'element': {'function': 'living'}}), 'rejected',
  [('FS-OPS-005', [])])
T('ids', 'element-id-used-by-an-item', 'A device named KIT - a program item\'s ID: FS-OPS-005.', ['1.5.2'],
  wired(briefed()), req(place(wall_face('W1', "2'", side='right'), id='KIT')), 'rejected', [('FS-OPS-005', [])])

# ============================================================================= transactions

T('transactions', 'apply-to-a-0.2-document', 'A is a Core 0.2 document with a program and briefs; it is valid, and a '
  'batch applies to it.', ['1.2.1', '1.3.1'], briefed(),
  req({'op': 'setProperty', 'id': 'Kitchen', 'path': '/name', 'value': 'Galley'}))
T('transactions', 'a-0.2-document-that-is-not-valid', 'A\'s adjacency names an item that does not exist, so A is not '
  'valid: FS-OPS-002.', ['1.2.1'], briefed(adjacency=[adj('KIT', 'LAU', 'preferred')]),
  req({'op': 'setProperty', 'id': 'Kitchen', 'path': '/name', 'value': 'Galley'}), 'rejected', [('FS-OPS-002', [])])
T('transactions', 'created-and-removed-list-every-element', '"created" and "removed" list program items and extension '
  'elements with the other elements: an item and a device created, a table removed.', ['1.3.1'],
  wired(briefed(), pieces={'X1': standing('R1', 3 * FT, 4 * FT)}),
  req({'op': 'addProgramItem', 'function': 'office'}, place(wall_face('W1', "2'", side='right')),
      {'op': 'removeElement', 'id': 'X1'}),
  check=lambda r, B: ensure(r['created'] == ['P1', 'X2'] and r['removed'] == ['X1'], r))

# ============================================================================= references: areas


def area_check(*values):
    def check(r, B):
        got = [p['element'].get('minArea') for p in r['resolved']]
        ensure(got == list(values), got)
    return check


T('references', 'areas', 'Areas in every unit: 11 m2, 11 m², 120 sq ft, 1600 IN2, 0.5 ft2 and 2.5 cm2, each exact.',
  ['3.6.1'], v2(box()),
  req(*[{'op': 'addProgramItem', 'function': 'storage', 'minArea': a}
        for a in ('11 m2', '11 m²', '120 sq ft', '1600 IN2', '0.5 ft2', '2.5 cm2')]),
  check=area_check(11 * M2, 11 * M2, 120 * FT2, 1600 * IN * IN, FT2 // 2, 409600000))
T('references', 'area-rounds-ties-to-even', '3/3276800 mm2 is 1.5 square base units and rounds to 2; 5/3276800 mm2 is '
  '2.5 and rounds to 2 as well - ties to even.', ['3.6.1'], v2(box()),
  req({'op': 'addProgramItem', 'function': 'storage', 'minArea': '0.00000091552734375 mm2'},
      {'op': 'addProgramItem', 'function': 'storage', 'minArea': '0.00000152587890625 mm2'}),
  check=area_check(2, 2))
T('references', 'not-an-area', '"11 m" is a length, not an area: FS-OPS-012.', ['3.6.1', '7.1.1'], v2(box()),
  req({'op': 'addProgramItem', 'function': 'storage', 'minArea': '11 m'}), 'rejected', [('FS-OPS-012', [])])
T('references', 'sq-needs-a-space', '"sq" and its unit are two words: "120 sqft" is not an area.', ['3.6.1'], v2(box()),
  req({'op': 'addProgramItem', 'function': 'storage', 'targetArea': '120 sqft'}), 'rejected', [('FS-OPS-012', [])])


# ============================================================================= what the text says as the oracle does
# (the Ops text made as specific as the oracle: 1.5, 3.3, 4.2, 4.10). These five were declared after
# Ops 0.2 was published (6f9bc07), with text that only the next draft publishes: they are Ops 0.3's
# (ops_author03.py), and the 0.2 suite is exactly as published.

PUBLISHED = len(TESTS)

T('ids', 'mint-past-upgraded-extension-elements', 'A declares "0.1", so its top-level extension data is opaque and the '
  'outlet X4 in it is no element of A (0.3). The batch makes the document declare "0.2", which turns X4 into an '
  'extension element of the working copy; the next device placed is X5, because minting counts the IDs in the '
  'working copy as it stands (1.5). "created" lists both: X4 is an element of B and was none of A (1.3).', ['1.5.1'],
  dict(box(extensionsUsed={ELEC: '0.1.0'}), extensions={ELEC: {'collections': {'devices': {'X4': outlet('W2', 6 * FT)}}}}),
  req({'op': 'setProperty', 'id': '$document', 'path': '/floorspec', 'value': '0.2'},
      place(wall_face('W2', "2'", side='right'))),
  check=lambda r, B: ensure(r['resolved'][1]['id'] == 'X5' and r['created'] == ['X4', 'X5'] and set(ext_of(B)) == {'X4', 'X5'}, r))
T('composites', 'move-wall-takes-no-separator', 'moveWall\'s "wall" is a wall: the separator S1 across the box counts '
  'as no match, so FS-OPS-003.', ['4.2.1', '3.3.1'],
  box(junctions={'J5': J(6 * FT, 0), 'J6': J(6 * FT, 10 * FT)},
      walls={'W4': W('J4', 'J5'), 'W5': W('J5', 'J1'), 'W2': W('J2', 'J6'), 'W6': W('J6', 'J3')},
      separators={'S1': S('J5', 'J6')}, rooms={'R1': R(3 * FT, 5 * FT, 'Living'), 'R2': R(9 * FT, 5 * FT, 'Dining')}),
  req({'op': 'moveWall', 'wall': 'S1', 'by': "1'"}), 'rejected', [('FS-OPS-003', [])])
T('composites', 'move-wall-toward-a-room-upstairs', '"toward" names the Loft, on L2: its face is not a face of W1\'s '
  'level, so it is on neither side of W1 - FS-OPS-008, naming the wall.', ['4.2.1', '7.1.1'], upstairs(),
  req({'op': 'moveWall', 'wall': 'W1', 'by': "1'", 'toward': 'Loft'}), 'rejected', [('FS-OPS-008', ['W1'])])
T('references', 'room-member-is-a-plain-string', 'A room member is read only as an ID or a room name: the Pantry is '
  'named "North wall of Kitchen", and "toward" names it - not the Kitchen\'s north wall, W10 - so W10 moves 1\' north, '
  'into the Pantry.', ['3.3.1', '4.2.1'],
  house(rooms={'R2': R(6 * FT, 10 * FT, 'North wall of Kitchen', function='storage')}),
  req({'op': 'moveWall', 'wall': 'W10', 'by': "1'", 'toward': 'north wall of kitchen'}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J2', 'to': [0, 9 * FT]}, {'op': 'moveJunction', 'id': 'J8', 'to': [12 * FT, 9 * FT]}))
T('hosting', 'place-toward-a-room-upstairs', 'A wall-face host "toward" the Loft, a room on L2, for a wall on L1: the '
  'room is not beside the wall (4.10, as 4.2), so FS-OPS-008 names the wall.', ['4.10.1'], wired(upstairs()),
  req(place(wall_face('W2', "2'", toward='Loft'))), 'rejected', [('FS-OPS-008', ['W2'])])


# ============================================================================= write

if __name__ == '__main__':
    import sys
    sys.exit(1 if write_all(prune='--prune' in sys.argv, tests=BASE + TESTS[:PUBLISHED], suite=SUITE02, profile=OPS_02) else 0)

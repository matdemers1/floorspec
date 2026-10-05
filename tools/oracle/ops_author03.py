"""The conformance suite of Floorspec Ops 0.3, as the script that writes it.

    python3.13 -m tools.oracle.ops_author03            rewrite every test from its declaration below
    python3.13 -m tools.oracle.ops_author03 --prune    ...and delete test directories no longer declared

The suite is the Ops 0.2 suite, carried forward to 0.3 - every 0.2 test, in the same group under
the same number, on the same documents A: Ops 0.3 applies to Core 0.2 and 0.1 documents exactly as
Ops 0.2 did (0.4). It retires one statement, FS-OPS-1.1.2 - a request now has the shape schema/ops/0.3
gives it, which may add a roof - so a test that covered it covers FS-OPS-1.1.3; every other test
covers what it covered. After them come
the five tests that pin what the Ops text says as the oracle does (1.5, 3.3, 4.2, 4.10), declared
after Ops 0.2 was published and so first published with 0.3 (ops_author02.py, PUBLISHED); then, in
each group, the tests of what 0.3 adds: Core 0.3 documents, whose door and window types declare an
operation and a clear opening and whose openings may override it, and whose rooms have floors and
flat, tray or vaulted ceilings and whose slabs a purpose, edited with the primitives Ops already
has; moveRoom moving a vaulted ceiling's ridge with its room (4.3.2); and roofs, Core 0.3's twelfth
collection (Core chapter 16), added, edited and removed with the primitives; stairs; and design options
(Core chapter 19): option sets and options, `context.option`, the edit design and normalization option by
option (2.8, 5.5). Every expected status and diagnostic is written by hand and cross-checked against the
oracle, applied as Ops 0.3 (version.OPS_03); the values that matter are asserted by hand in each
test's check. Afterwards, `python3.13 -m tools.oracle.regenerate` re-verifies the suite from the
files alone. Add new tests at the end of their group's section.
"""
import copy
import os
import sys

import tools.oracle.ops_author02 as v02                # declares the 0.2 suite: v02.BASE + v02.TESTS
from tools.oracle.ops_author import box, door_on_south, ensure, resolved_eq
from tools.oracle.ops_author_lib import FT, IN, MM, REPO, TESTS, T, doc, req, write_all
from tools.oracle.ops.version import OPS_03

SUITE03 = os.path.join(REPO, 'conformance', 'ops', '0.3')

# ============================================================================= the 0.2 suite, carried forward

RETARGET = {
    # slug: (document A, description) where 0.3 needs another input to show the same thing
    'document-other-version': (doc(floorspec='0.4'), 'Document A declares Floorspec 0.4, which a Core 0.3 reader does not implement '
                               '(FS-DOC-001): FS-OPS-002.'),
}
RETIRED = {'FS-OPS-1.1.2': 'FS-OPS-1.1.3'}
DESCRIPTIONS = {
    'extension-data-in-a-0.1-document': [('(Core 1.2.4)', '(Core 1.2.6)')],
}


def carry(tc):
    tc = copy.deepcopy(tc)
    tc['covers'] = [RETIRED.get(c, c) for c in tc['covers']]
    if tc['slug'] == 'unknown-collection':                 # "roofs" and "optionSets" are collections of 0.3
        tc['request'] = req({'op': 'addElement', 'collection': 'furniture', 'element': {}})
        tc['description'] = ('addElement\'s collection is one of the collections of Core 1.1 or the program\'s '
                             'items; "furniture" is not a collection of Core 0.3: furniture is an extension\'s.')
    for old, new in DESCRIPTIONS.get(tc['slug'], []):
        assert old in tc['description'], (tc['slug'], old)
        tc['description'] = tc['description'].replace(old, new)
    if tc['slug'] in RETARGET:
        tc['a'], tc['description'] = RETARGET[tc['slug']]
    return tc


BASE = [carry(tc) for tc in v02.BASE + v02.TESTS]
del TESTS[:]


# ============================================================================= helpers

def v3(d):
    d = copy.deepcopy(d)
    d['floorspec'] = '0.3'
    return d


CLEAR = {'width': 32 * IN, 'height': 79 * IN}                  # the 36-inch door's: 32 by 79 inches
DOOR = 'T-door-36'


def clear_door(offset=FT, **opening):
    """The box as a Core 0.3 document, its 36-inch door type a swing door with a clear opening, and a
    door O1 on the south wall W4 at `offset`."""
    d = v3(door_on_south(offset))
    d['types'][DOOR].update(operation='swing', clearOpening=copy.deepcopy(CLEAR))
    d['openings']['O1'].update(opening)
    return d


def opening_of(B, oid='O1'):
    return B['openings'][oid]


# Floors, ceilings and slabs (Core 0.3, chapter 15), on the box: one 12' x 10' room R1 inside 100 mm walls, on
# L1 at 0, 2700 mm high.
TRAY = {'kind': 'tray', 'border': FT, 'depth': 6 * IN}
VAULT = {'kind': 'vaulted', 'height': 3200 * MM, 'ridge': [[0, 5 * FT], [12 * FT, 5 * FT]], 'pitch': {'rise': 4, 'run': 12}}


def room_box(**r1):
    """The box as a Core 0.3 document, with these members on R1."""
    d = v3(box())
    d['rooms']['R1'].update(copy.deepcopy(r1))
    return d


def derived(B):
    """What a Core 0.3 deriver derives for the committed document B."""
    import json
    from tools.oracle.validate import READER_03, check as core_check
    result, _, _ = core_check(json.dumps(B).encode('utf-8'), READER_03)
    assert result['valid'], result['diagnostics']
    return result['derived']


# ============================================================================= transactions (0.3)
T('transactions', 'apply-to-a-0.3-document', 'A is a Core 0.3 document whose door type declares its operation and '
  'clear opening; it is valid, and a batch applies to it.', ['1.2.1', '1.3.1'], clear_door(),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/name', 'value': 'Hall'}),
  check=lambda r, B: ensure(B['types'][DOOR]['clearOpening'] == CLEAR and B['rooms']['R1']['name'] == 'Hall', B))
T('transactions', 'upgrade-and-declare-a-clear-opening', 'A is a Core 0.2 document. The batch declares "0.3", then '
  'gives the door type a clear opening: the result is a valid Core 0.3 document.', ['2.3.1', '1.3.1'],
  v02.v2(door_on_south(FT)),
  req({'op': 'setProperty', 'id': '$document', 'path': '/floorspec', 'value': '0.3'},
      {'op': 'setProperty', 'id': DOOR, 'path': '/clearOpening', 'value': CLEAR}),
  check=lambda r, B: ensure(B['floorspec'] == '0.3' and B['types'][DOOR]['clearOpening'] == CLEAR, B))
T('transactions', 'clear-opening-in-a-0.2-document', 'The same clear opening without declaring "0.3": the result '
  'declares "0.2", whose schema has no "clearOpening" (Core 1.2.6), so it is invalid and the rejection carries '
  'FS-SCH-001.', ['1.2.3', '1.2.2'], v02.v2(door_on_south(FT)),
  req({'op': 'setProperty', 'id': DOOR, 'path': '/clearOpening', 'value': CLEAR}), 'rejected', [('FS-SCH-001', [])])

T('transactions', 'ceiling-in-a-0.2-document', 'A tray ceiling set on a room of a Core 0.2 document that does not '
  'declare "0.3": Core 0.2\'s schema has no "ceiling" (Core 1.2.6), so the result is invalid: FS-SCH-001.',
  ['1.2.3', '1.2.2'], v02.v2(box()), req({'op': 'setProperty', 'id': 'R1', 'path': '/ceiling', 'value': TRAY}),
  'rejected', [('FS-SCH-001', [])])

# ============================================================================= primitives (0.3)
T('primitives', 'set-operation-and-clear-opening', 'setProperty gives the door type an operation and a clear '
  'opening: a pocket door, 34 inches by 79 clear.', ['2.3.1'], v3(door_on_south(FT)),
  req({'op': 'setProperty', 'id': DOOR, 'path': '/operation', 'value': 'pocket'},
      {'op': 'setProperty', 'id': DOOR, 'path': '/clearOpening', 'value': {'width': 34 * IN, 'height': 79 * IN}}),
  check=lambda r, B: ensure(B['types'][DOOR]['operation'] == 'pocket'
                            and B['types'][DOOR]['clearOpening'] == {'width': 34 * IN, 'height': 79 * IN}, B['types']))
T('primitives', 'clear-opening-value-taken-as-given', 'A setProperty value is taken as given, never resolved (2.5): '
  'the clear width "34\"" stays a string, which is not a length, so the result is invalid: FS-SCH-001.',
  ['1.2.3', '2.3.1'], v3(door_on_south(FT)),
  req({'op': 'setProperty', 'id': DOOR, 'path': '/clearOpening', 'value': {'width': "34\"", 'height': 79 * IN}}),
  'rejected', [('FS-SCH-001', [])])
T('primitives', 'set-clear-width', 'setProperty of the door type\'s /clearOpening/width sets one member of the clear '
  'opening and leaves its height.', ['2.3.1'], clear_door(),
  req({'op': 'setProperty', 'id': DOOR, 'path': '/clearOpening/width', 'value': 33 * IN}),
  check=lambda r, B: ensure(B['types'][DOOR]['clearOpening'] == {'width': 33 * IN, 'height': 79 * IN}, B['types']))
T('primitives', 'override-clear-opening', 'setProperty of O1\'s /clearOpening overrides the type\'s for that door '
  'alone (Core 7.2): O1 is 30 inches clear, the type still 32.', ['2.3.1'], clear_door(),
  req({'op': 'setProperty', 'id': 'O1', 'path': '/clearOpening', 'value': {'width': 30 * IN, 'height': 79 * IN}}),
  check=lambda r, B: ensure(opening_of(B)['clearOpening'] == {'width': 30 * IN, 'height': 79 * IN}
                            and B['types'][DOOR]['clearOpening'] == CLEAR, B))
T('primitives', 'unset-clear-opening-override', 'unsetProperty of O1\'s own /clearOpening: the door has its type\'s '
  'again, and the inverse sets the override back.', ['2.3.1', '1.6.1'],
  clear_door(clearOpening={'width': 30 * IN, 'height': 79 * IN}),
  req({'op': 'unsetProperty', 'id': 'O1', 'path': '/clearOpening'}),
  check=lambda r, B: ensure('clearOpening' not in opening_of(B) and r['inverse'] == [
      {'op': 'setProperty', 'id': 'O1', 'path': '/clearOpening', 'value': {'width': 30 * IN, 'height': 79 * IN}}], r))
T('primitives', 'narrower-than-its-clear-opening', 'setProperty narrows O1 to 30 inches; it keeps its type\'s 32-inch '
  'clear opening, which no longer fits, so the result is invalid: FS-INV-305 (Core 7.2.2).', ['1.2.3', '2.3.1'],
  clear_door(), req({'op': 'setProperty', 'id': 'O1', 'path': '/width', 'value': 30 * IN}), 'rejected',
  [('FS-INV-305', ['O1'])])
T('primitives', 'narrower-with-its-own-clear-opening', 'The same 30-inch door, with its own 28-inch clear opening set '
  'in the same batch: valid.', ['1.2.2', '2.3.1'], clear_door(),
  req({'op': 'setProperty', 'id': 'O1', 'path': '/width', 'value': 30 * IN},
      {'op': 'setProperty', 'id': 'O1', 'path': '/clearOpening', 'value': {'width': 28 * IN, 'height': 79 * IN}}),
  check=lambda r, B: ensure(opening_of(B)['width'] == 30 * IN and opening_of(B)['clearOpening']['width'] == 28 * IN, B))
T('primitives', 'door-clear-area', 'A door type\'s clear opening has no area (Core 8.4.3): setting one makes the '
  'result invalid, FS-SCH-001.', ['1.2.3', '2.3.1'], clear_door(),
  req({'op': 'setProperty', 'id': DOOR, 'path': '/clearOpening/area', 'value': 32 * IN * 79 * IN}), 'rejected',
  [('FS-SCH-001', [])])
T('primitives', 'remove-type-with-clear-opening-blocked', 'Removing the door type is blocked by the door that uses it, '
  'whatever it declares.', ['2.2.1'], clear_door(), req({'op': 'removeElement', 'id': DOOR}), 'rejected',
  [('FS-OPS-006', ['O1', DOOR])])

T('primitives', 'set-a-tray-ceiling', 'setProperty gives R1 a tray ceiling - a 1\' border, 6" deep: the room\'s '
  'derived ceiling is a tray whose centre is the room polygon shrunk by 1\'.', ['2.3.1'], room_box(),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/ceiling', 'value': TRAY}),
  check=lambda r, B: ensure(B['rooms']['R1']['ceiling'] == TRAY
                            and derived(B)['ceilings']['R1']['tray']['outer'][0] == [64000 + FT, 64000 + FT], derived(B)))
T('primitives', 'sink-a-floor-and-set-the-level', 'setProperty sinks R1\'s floor 6" and gives L1 300 mm floors and '
  '2400 mm ceilings: R1\'s floor runs from -6" down 300 mm, and its ceiling is at 2400 mm.', ['2.3.1'], room_box(),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/floor', 'value': {'offset': -6 * IN}},
      {'op': 'setProperty', 'id': 'L1', 'path': '/floorThickness', 'value': 300 * MM},
      {'op': 'setProperty', 'id': 'L1', 'path': '/ceilingHeight', 'value': 2400 * MM}),
  check=lambda r, B: ensure(derived(B)['floors']['R1']['top'] == -6 * IN
                            and derived(B)['floors']['R1']['bottom'] == -6 * IN - 300 * MM
                            and derived(B)['ceilings']['R1']['low'] == 2400 * MM, derived(B)))
T('primitives', 'set-tray-border', 'setProperty of R1\'s /ceiling/border widens its tray\'s border to 2\' and leaves '
  'its depth.', ['2.3.1'], room_box(ceiling=TRAY),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/ceiling/border', 'value': 2 * FT}),
  check=lambda r, B: ensure(B['rooms']['R1']['ceiling'] == {**TRAY, 'border': 2 * FT}, B['rooms']['R1']))
T('primitives', 'unset-a-ceiling', 'unsetProperty of R1\'s /ceiling: its ceiling is flat at the level\'s height '
  'again, and the inverse sets the tray back.', ['2.3.1', '1.6.1'], room_box(ceiling=TRAY),
  req({'op': 'unsetProperty', 'id': 'R1', 'path': '/ceiling'}),
  check=lambda r, B: ensure('ceiling' not in B['rooms']['R1'] and derived(B)['ceilings']['R1']['kind'] == 'flat'
                            and r['inverse'] == [{'op': 'setProperty', 'id': 'R1', 'path': '/ceiling', 'value': TRAY}], r))
T('primitives', 'tray-border-too-wide', 'setProperty of a 5\' border in a room under 10\' deep inside its walls: the '
  'tray does not fit (Core 15.4.1), so the result is invalid: FS-INV-703.', ['1.2.3', '2.3.1'], room_box(ceiling=TRAY),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/ceiling/border', 'value': 5 * FT}), 'rejected',
  [('FS-INV-703', ['R1'])])
T('primitives', 'floor-up-to-the-ceiling', 'setProperty raises R1\'s floor to the level\'s height, where its flat '
  'ceiling is: the ceiling is not above the floor (Core 15.2.2), FS-INV-701.', ['1.2.3', '2.3.1'], room_box(),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/floor', 'value': {'offset': 2700 * MM}}), 'rejected',
  [('FS-INV-701', ['R1'])])
T('primitives', 'move-junction-reshapes-floor-and-ceiling', 'moveJunction drags the box\'s north-east corner J3 2\' '
  'east: R1\'s floor and tray ceiling are its room polygon, so their boxes and the tray\'s centre follow, and the '
  'document does not change otherwise.', ['2.4.1'], room_box(ceiling=TRAY),
  req({'op': 'moveJunction', 'id': 'J3', 'to': ["14'", "10'"]}),
  check=lambda r, B: ensure(B['rooms']['R1']['ceiling'] == TRAY
                            and derived(B)['floors']['R1']['box']['max'][0] == derived(B)['rooms']['R1']['outer'][2][0]
                            and derived(B)['ceilings']['R1']['tray']['outer'][2][0] > 11 * FT, derived(B)))
T('primitives', 'set-a-slab-purpose', 'addElement puts a patio slab south of the box, with its purpose: valid, and '
  'derived with its bounding geometry.', ['2.1.1'], room_box(),
  req({'op': 'addElement', 'collection': 'slabs', 'id': 'S1',
       'element': {'level': 'L1', 'boundary': [[0, -8 * FT], [12 * FT, -8 * FT], [12 * FT, -FT // 2], [0, -FT // 2]],
                   'thickness': 4 * IN, 'offset': -6 * IN, 'purpose': 'patio'}}),
  check=lambda r, B: ensure(derived(B)['slabs']['S1']['top'] == -6 * IN and r['created'] == ['S1'], derived(B)['slabs']))

# ============================================================================= composites (0.3)
T('composites', 'add-opening-with-a-clear-opening', 'addOpening names its door O2 on the north wall, and the same '
  'batch gives it a clear opening of its own: addOpening has no member for one, and setProperty sets it.',
  ['2.3.1', '1.5.1'], clear_door(),
  req({'op': 'addOpening', 'id': 'O2', 'wall': 'W2', 'at': 'centered', 'fill': DOOR},
      {'op': 'setProperty', 'id': 'O2', 'path': '/clearOpening', 'value': {'width': 31 * IN, 'height': 79 * IN}}),
  check=lambda r, B: ensure(B['openings']['O2']['clearOpening'] == {'width': 31 * IN, 'height': 79 * IN}
                            and r['created'] == ['O2'], (r, B['openings'])))
T('composites', 'move-opening-keeps-its-clear-opening', 'moveOpening moves O1 2\' along its wall: only its offset '
  'changes, and its own clear opening goes with it.', ['4.5.2'],
  clear_door(clearOpening={'width': 30 * IN, 'height': 79 * IN}), req({'op': 'moveOpening', 'opening': 'O1', 'by': "2'"}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 3 * FT}))

T('composites', 'move-room-moves-its-vault', 'moveRoom moves R1 3\' east: its junctions, its anchor and its vaulted '
  'ceiling\'s ridge move by the same vector (step 3), and nothing else of its ceiling changes.', ['4.3.1', '4.3.2'],
  room_box(ceiling=VAULT), req({'op': 'moveRoom', 'room': 'R1', 'by': "3' east"}),
  check=lambda r, B: ensure(B['rooms']['R1']['ceiling'] == {**VAULT, 'ridge': [[3 * FT, 5 * FT], [15 * FT, 5 * FT]]}
                            and {'op': 'setProperty', 'id': 'R1', 'path': '/ceiling/ridge',
                                 'value': [[3 * FT, 5 * FT], [15 * FT, 5 * FT]]} in r['resolved'], r['resolved']))
T('composites', 'move-room-keeps-a-tray', 'moveRoom moves a room whose ceiling is a tray: nothing of the ceiling is '
  'set, since a tray\'s centre is derived from the room polygon, which moves with the walls.', ['4.3.1', '4.3.2'],
  room_box(ceiling=TRAY, floor={'offset': -6 * IN}), req({'op': 'moveRoom', 'room': 'R1', 'by': "1' north"}),
  check=lambda r, B: ensure(B['rooms']['R1']['ceiling'] == TRAY and B['rooms']['R1']['floor'] == {'offset': -6 * IN}
                            and not any(p.get('path', '').startswith(('/ceiling', '/floor')) for p in r['resolved']),
                            r['resolved']))
T('composites', 'resize-room-leaves-the-ridge', 'resizeRoom moves the vaulted room\'s east side 2\' out: its ceiling '
  'covers the larger room polygon, but its ridge is a plan point, which only moveRoom moves - so it is unchanged.',
  ['4.4.1', '4.3.2'], room_box(ceiling=VAULT), req({'op': 'resizeRoom', 'room': 'R1', 'side': 'east', 'by': "2'"}),
  check=lambda r, B: ensure(B['rooms']['R1']['ceiling'] == VAULT
                            and derived(B)['ceilings']['R1']['box']['max'][0] > 12 * FT, derived(B)['ceilings']))

# ============================================================================= normalization (0.3)
T('normalization', 'rehosted-opening-keeps-its-clear-opening', 'A wall drawn across the south wall at 8\' splits it; '
  'the door at 6\' moves to the second piece, W7, at offset 2\' (5.2), with its own clear opening unchanged.',
  ['5.2.1'], clear_door(6 * FT, clearOpening={'width': 30 * IN, 'height': 79 * IN}),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["8'", 0], 'to': ["8'", "10'"], 'type': 'WT'}),
  check=lambda r, B: ensure(opening_of(B) == {'fill': DOOR, 'offset': 2 * FT, 'wall': 'W7',
                                              'clearOpening': {'width': 30 * IN, 'height': 79 * IN}}, opening_of(B)))

# ============================================================================= inverse (0.3)
T('inverse', 'clear-opening-added-and-undone', 'Giving a type with no clear opening one: the inverse unsets it, and '
  'applying the inverse gives back A exactly (1.6.1).', ['1.6.1'], v3(door_on_south(FT)),
  req({'op': 'setProperty', 'id': DOOR, 'path': '/clearOpening', 'value': CLEAR},
      {'op': 'setProperty', 'id': DOOR, 'path': '/operation', 'value': 'swing'}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'unsetProperty', 'id': DOOR, 'path': '/clearOpening'},
                                             {'op': 'unsetProperty', 'id': DOOR, 'path': '/operation'}], r['inverse']))

T('inverse', 'ceiling-and-floor-set-and-undone', 'Giving R1 a vaulted ceiling and a sunken floor: the inverse unsets '
  'both, and applying it gives back A exactly (1.6.1).', ['1.6.1'], room_box(),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/ceiling', 'value': VAULT},
      {'op': 'setProperty', 'id': 'R1', 'path': '/floor', 'value': {'offset': -6 * IN, 'thickness': 300 * MM}}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'unsetProperty', 'id': 'R1', 'path': '/ceiling'},
                                             {'op': 'unsetProperty', 'id': 'R1', 'path': '/floor'}], r['inverse']))

# ============================================================================= roofs (0.3): Core chapter 16
# The box under a roof: its footprint the walls' outer faces, 50 mm (64000 base units) outside the walls' centre
# lines, its eaves at the level's 2700 mm.
HALF = 64000                                                    # half of a 100 mm wall
ROOF_FP = [[-HALF, -HALF], [12 * FT + HALF, -HALF], [12 * FT + HALF, 10 * FT + HALF], [-HALF, 10 * FT + HALF]]
SIX = {'rise': 6, 'run': 12}
HIP = {'level': 'L1', 'footprint': ROOF_FP, 'pitch': SIX, 'overhang': FT}


def roofed(*roofs, **members):
    """The box as a Core 0.3 document, with these roofs - RF1, RF2, ... - and these other members."""
    d = room_box()
    d['roofs'] = {f'RF{i}': copy.deepcopy(r) for i, r in enumerate(roofs, 1)}
    for k, v in members.items():
        d[k] = {**d.get(k, {}), **copy.deepcopy(v)} if isinstance(v, dict) and isinstance(d.get(k), dict) else v
    return d


def roof_of(B, rid='RF1'):
    return derived(B)['roofs'][rid]


T('primitives', 'add-a-roof', 'addElement adds a hip roof over the box, at 6 in 12 with a 1\' overhang, and names no '
  'ID: the applier mints RF1 - the prefix of roofs is RF (1.5) - and the result derives a hip roof whose ridge is '
  'half of 12\' and 100 mm above its eaves: 3\' and 25 mm.', ['2.1.1', '1.5.1'], room_box(),
  req({'op': 'addElement', 'collection': 'roofs', 'element': HIP}),
  check=lambda r, B: ensure(r['created'] == ['RF1'] and roof_of(B)['kind'] == 'hip'
                            and roof_of(B)['surface']['high'] == 2700 * MM + (12 * FT + 2 * HALF) // 4, roof_of(B)))
T('primitives', 'mint-a-roof-past-the-largest', 'A has roofs RF1 and RF7; a roof added without an ID is RF8, one '
  'more than the largest (1.5).', ['1.5.1'], roofed(HIP, roofs={'RF7': HIP}),
  req({'op': 'setProperty', 'id': 'RF7', 'path': '/name', 'value': 'Porch'},
      {'op': 'addElement', 'collection': 'roofs', 'element': {**HIP, 'pitch': {'rise': 4, 'run': 12}}}),
  check=lambda r, B: ensure(r['created'] == ['RF8'], r))
T('primitives', 'gable-two-edges', 'setProperty of /edges/1/gable and /edges/3/gable on the hip roof - creating its '
  '"edges" and each edge on the way - makes the box\'s short ends gables: the roof derives as a gable roof.',
  ['2.3.1'], roofed(HIP),
  req({'op': 'setProperty', 'id': 'RF1', 'path': '/edges/1/gable', 'value': True},
      {'op': 'setProperty', 'id': 'RF1', 'path': '/edges/3/gable', 'value': True}),
  check=lambda r, B: ensure(B['roofs']['RF1']['edges'] == {'1': {'gable': True}, '3': {'gable': True}}
                            and roof_of(B)['kind'] == 'gable' and len(roof_of(B)['surface']['gables']) == 2, roof_of(B)))
T('primitives', 'steepen-a-roof', 'setProperty of the roof\'s /pitch to 12 in 12 and /overhang to 2\': the ridge '
  'rises with it.', ['2.3.1'], roofed(HIP),
  req({'op': 'setProperty', 'id': 'RF1', 'path': '/pitch', 'value': {'rise': 12, 'run': 12}},
      {'op': 'setProperty', 'id': 'RF1', 'path': '/overhang', 'value': 2 * FT}),
  check=lambda r, B: ensure(roof_of(B)['surface']['high'] == 2700 * MM + 7 * FT + HALF, roof_of(B)))
T('primitives', 'gable-every-edge', 'setProperty makes every edge of the roof a gable: no edge slopes (Core 16.2.2), '
  'so the result is invalid: FS-INV-803.', ['1.2.3', '2.3.1'], roofed(HIP),
  req(*({'op': 'setProperty', 'id': 'RF1', 'path': f'/edges/{i}/gable', 'value': True} for i in range(4))),
  'rejected', [('FS-INV-803', ['RF1'])])
T('primitives', 'pitch-one-edge-differently', 'setProperty pitches the south edge 12 in 12 under a 6-in-12 roof: '
  'Core 0.3 does not derive a roof of mixed pitches, but the document is valid - the batch commits, and the roof '
  'has no surface (Core 16.4.4).', ['1.2.2', '2.3.1'], roofed(HIP),
  req({'op': 'setProperty', 'id': 'RF1', 'path': '/edges/0/pitch', 'value': {'rise': 12, 'run': 12}}),
  check=lambda r, B: ensure(roof_of(B)['surface'] is None, roof_of(B)))
T('primitives', 'unset-a-roof-overhang', 'unsetProperty of the roof\'s /overhang: it overhangs nothing again, and '
  'the inverse sets the 1\' back.', ['2.3.1', '1.6.1'], roofed(HIP),
  req({'op': 'unsetProperty', 'id': 'RF1', 'path': '/overhang'}),
  check=lambda r, B: ensure('overhang' not in B['roofs']['RF1'] and r['inverse'] == [
      {'op': 'setProperty', 'id': 'RF1', 'path': '/overhang', 'value': FT}], r))
T('primitives', 'remove-a-roof', 'removeElement removes the roof; nothing depends on a roof, and the inverse adds it '
  'back, exactly as it is in A.', ['2.2.1', '2.2.2', '1.6.1'], roofed(HIP), req({'op': 'removeElement', 'id': 'RF1'}),
  check=lambda r, B: ensure(r['removed'] == ['RF1'] and 'roofs' not in B and r['inverse'] == [
      {'op': 'addElement', 'collection': 'roofs', 'id': 'RF1', 'element': HIP}], r))
ATTIC = {'L2': {'building': 'B1', 'elevation': 2700 * MM, 'height': 2400 * MM}}
T('primitives', 'remove-a-level-under-a-roof', 'A roof stands on level L2, which has nothing else: removing L2 '
  'without cascade is blocked by the roof (2.2).', ['2.2.1'], roofed({**HIP, 'level': 'L2', 'height': 0}, levels=ATTIC),
  req({'op': 'removeElement', 'id': 'L2'}), 'rejected', [('FS-OPS-006', ['L2', 'RF1'])])
T('primitives', 'remove-a-level-takes-its-roof', 'The same removal with cascade takes the roof with the level.',
  ['2.2.2'], roofed({**HIP, 'level': 'L2', 'height': 0}, levels=ATTIC),
  req({'op': 'removeElement', 'id': 'L2', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['L2', 'RF1'], r))
T('primitives', 'remove-a-roof-material', 'Removing a material is blocked by the roof whose top surface it is.',
  ['2.2.1'], roofed({**HIP, 'material': 'SHINGLE'}, materials={'SHINGLE': {'color': '#4a4a4a'}}),
  req({'op': 'removeElement', 'id': 'SHINGLE'}), 'rejected', [('FS-OPS-006', ['RF1', 'SHINGLE'])])

T('transactions', 'roof-in-a-0.2-document', 'A roof added to a Core 0.2 document that does not declare "0.3": the '
  'request is well formed under Ops 0.3, but Core 0.2\'s schema has no "roofs" (Core 1.2.6), so the result is '
  'invalid: FS-SCH-001.', ['1.2.3', '1.1.3'], v02.v2(box()),
  req({'op': 'addElement', 'collection': 'roofs', 'element': HIP}), 'rejected', [('FS-SCH-001', [])])

T('composites', 'move-room-leaves-the-roof', 'moveRoom moves R1 3\' east: its walls go with it, but the roof\'s '
  'footprint is plan points, which no composite moves (0.5), so the roof stays where it was.', ['4.3.1'],
  roofed(HIP), req({'op': 'moveRoom', 'room': 'R1', 'by': "3' east"}),
  check=lambda r, B: ensure(B['roofs']['RF1'] == HIP and not any(p.get('id') == 'RF1' for p in r['resolved']),
                            r['resolved']))

T('inverse', 'roof-added-and-undone', 'Adding a roof and gabling one of its edges in the same batch: the inverse '
  'removes the roof, and applying it gives back A exactly (1.6.1).', ['1.6.1'], room_box(),
  req({'op': 'addElement', 'collection': 'roofs', 'id': 'RF1', 'element': HIP},
      {'op': 'setProperty', 'id': 'RF1', 'path': '/edges/1/gable', 'value': True}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'removeElement', 'id': 'RF1'}], r['inverse']))

# ============================================================================= stairs (0.3): Core chapter 17
# upstairs(): the box on L1, and on L2 above it an 8' x 8' loft R2 with a slab SL1 and a window O1. The stair rises
# east from (1', 2'), 3' wide, 14 risers on 9" treads; its head, 9'9" further east, is past the loft, in no room.
from tools.oracle.ops_author import upstairs                                   # noqa: E402

STAIR = {'level': 'L1', 'to': 'L2', 'position': [FT, 2 * FT], 'width': 3 * FT, 'tread': 9 * IN, 'risers': 14}


def with_stair(**st):
    d = v3(upstairs())
    d['stairs'] = {'ST1': {**copy.deepcopy(STAIR), **st}}
    return d


T('primitives', 'add-a-stair', 'addElement adds a stair to the stairs collection Core 0.3 adds: the result is valid, '
  'and its stair is derived.', ['2.1.1', '1.3.1'], v3(upstairs()),
  req({'op': 'addElement', 'collection': 'stairs', 'id': 'ST1', 'element': STAIR}),
  check=lambda r, B: ensure(r['created'] == ['ST1'] and derived(B)['stairs']['ST1']['risers'] == 14, r['created']))
T('primitives', 'add-a-stair-minting-its-id', 'addElement into stairs with no id: the applier mints ST1, the prefix '
  'of the stairs collection being ST.', ['1.5.1', '2.1.1'], v3(upstairs()),
  req({'op': 'addElement', 'collection': 'stairs', 'element': STAIR}),
  check=lambda r, B: ensure(r['created'] == ['ST1'] and 'ST1' in B['stairs'], r['created']))
T('primitives', 'set-a-stair-form', 'setProperty makes the stair an L, turning left after 7 risers, and declares its '
  'handrail: valid, and derived with a landing.', ['2.3.1'], with_stair(),
  req({'op': 'setProperty', 'id': 'ST1', 'path': '/form', 'value': {'kind': 'lShaped', 'turn': 'left', 'risersBeforeTurn': 7}},
      {'op': 'setProperty', 'id': 'ST1', 'path': '/handrail', 'value': {'height': 36 * IN}}),
  check=lambda r, B: ensure(sum(1 for s in derived(B)['stairs']['ST1']['steps'] if s.get('landing')) == 1,
                            derived(B)['stairs']['ST1']))
T('primitives', 'stair-to-its-own-level', 'setProperty of the stair\'s /to to L1, its own level: the result has '
  'FS-INV-901, so the batch is rejected with it.', ['1.2.3', '2.3.1'], with_stair(),
  req({'op': 'setProperty', 'id': 'ST1', 'path': '/to', 'value': 'L1'}), 'rejected', [('FS-INV-901', ['ST1'])])
T('primitives', 'unset-a-stair-riser-count', 'unsetProperty of the stair\'s /risers: it has neither risers nor '
  'maxRiser, which Core 0.3\'s schema rejects: FS-SCH-001.', ['1.2.3', '2.3.1'], with_stair(),
  req({'op': 'unsetProperty', 'id': 'ST1', 'path': '/risers'}), 'rejected', [('FS-SCH-001', [])])
T('primitives', 'riser-count-from-a-greatest-riser', 'unsetProperty of /risers and setProperty of /maxRiser in one '
  'batch: the stair derives its riser count, 2700 mm over 7 3/4 in risers, 14.', ['2.3.1'], with_stair(),
  req({'op': 'unsetProperty', 'id': 'ST1', 'path': '/risers'},
      {'op': 'setProperty', 'id': 'ST1', 'path': '/maxRiser', 'value': 31 * IN // 4}),
  check=lambda r, B: ensure(derived(B)['stairs']['ST1']['risers'] == 14, derived(B)['stairs']))
T('primitives', 'remove-a-stair', 'removeElement removes a stair, and nothing depends on it.', ['2.2.1', '2.2.2'],
  with_stair(), req({'op': 'removeElement', 'id': 'ST1'}),
  check=lambda r, B: ensure(r['removed'] == ['ST1'] and 'stairs' not in B, r['removed']))
T('primitives', 'remove-level-blocked-by-a-stair', 'Removing L2 without cascade is blocked by everything on it and by '
  'the stair that rises to it: a stair depends on both its levels.', ['2.2.1'], with_stair(),
  req({'op': 'removeElement', 'id': 'L2'}), 'rejected',
  [('FS-OPS-006', ['L2', 'K1', 'K2', 'K3', 'K4', 'R2', 'SL1', 'ST1', 'V1', 'V2', 'V3', 'V4'])])
T('primitives', 'remove-level-cascades-to-a-stair', 'Removing L2 with cascade takes the stair that rises to it with '
  'everything on it.', ['2.2.2'], with_stair(), req({'op': 'removeElement', 'id': 'L2', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['K1', 'K2', 'K3', 'K4', 'L2', 'O1', 'R2', 'SL1', 'ST1', 'V1', 'V2', 'V3', 'V4'],
                            r['removed']))
T('primitives', 'remove-lower-level-cascades-to-a-stair', 'Removing L1 with cascade takes the stair that rises from '
  'it, as well as the box on it; L2 and its loft stay.', ['2.2.2'], with_stair(),
  req({'op': 'removeElement', 'id': 'L1', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['J1', 'J2', 'J3', 'J4', 'L1', 'R1', 'ST1', 'W1', 'W2', 'W3', 'W4']
                            and 'L2' in B['levels'], r['removed']))
T('transactions', 'stair-in-a-0.2-document', 'A stair added to a Core 0.2 document that does not declare "0.3": '
  'Ops 0.3 adds to the stairs collection, but Core 0.2\'s schema has none, so the result is invalid: FS-SCH-001.',
  ['1.2.3', '2.1.1'], v02.v2(upstairs()), req({'op': 'addElement', 'collection': 'stairs', 'id': 'ST1', 'element': STAIR}),
  'rejected', [('FS-SCH-001', [])])
T('inverse', 'stair-added-and-undone', 'Adding a stair: the inverse removes it, and applying it gives back A '
  'exactly (1.6.1).', ['1.6.1'], v3(upstairs()),
  req({'op': 'addElement', 'collection': 'stairs', 'id': 'ST1', 'element': STAIR}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'removeElement', 'id': 'ST1'}], r['inverse']))
T('inverse', 'level-and-stair-removed-and-undone', 'Removing L2 with cascade, its stair with it: the inverse adds L2 '
  'back before the stair that rises to it - stairs come after roofs in step 2\'s order, so they are added after '
  'levels in step 3\'s - and applying it gives back A exactly (1.6.1).', ['1.6.1'], with_stair(),
  req({'op': 'removeElement', 'id': 'L2', 'cascade': True}),
  check=lambda r, B: ensure([p['id'] for p in r['inverse']].index('L2') < [p['id'] for p in r['inverse']].index('ST1'),
                            r['inverse']))


# ============================================================================= design options (0.3): Core chapter 19
# The kitchen house of the Core suite (options/): one level, 8 m x 4 m inside 100 mm walls, the north and south walls
# split at x = 4 m and 5 m; dining (DIN) west and kitchen (KIT) east, both common; a front door O1 in the west wall.
# Option set KS: KA (primary) adds the wall WA at x = 5 m with the door OA; KB adds the separator SB at x = 4 m and a
# window OB in the common north wall W4.
from tools.oracle.ops_author_lib import level_doc                                   # noqa: E402

KX, KY = 8000 * MM, 4000 * MM


def kitchen_house(options=True, a=True, b=True, kit=True):
    def j(x, y, **kw):
        return {'level': 'L1', 'position': [x, y], **kw}

    def w(s_, e_, **kw):
        return {'level': 'L1', 'start': s_, 'end': e_, 'type': 'WT', **kw}
    d = v3(level_doc(
        junctions={'J1': j(0, 0), 'J2': j(0, KY), 'J3': j(KX, KY), 'J4': j(KX, 0), 'S4': j(4000 * MM, 0),
                   'S5': j(5000 * MM, 0), 'N4': j(4000 * MM, KY), 'N5': j(5000 * MM, KY)},
        walls={'W1': w('J1', 'J2'), 'W2': w('J2', 'N4'), 'W3': w('N4', 'N5'), 'W4': w('N5', 'J3'),
               'W5': w('J3', 'J4'), 'W6': w('J4', 'S5'), 'W7': w('S5', 'S4'), 'W8': w('S4', 'J1')},
        rooms={'DIN': {'level': 'L1', 'anchor': [2000 * MM, 2000 * MM], 'name': 'Dining'},
               'KIT': {'level': 'L1', 'anchor': [6500 * MM, 2000 * MM], 'name': 'Kitchen'}},
        openings={'O1': {'wall': 'W1', 'offset': 1500 * MM, 'fill': 'T-door-36'}}))
    d['types']['G'] = {'kind': 'windowType', 'width': 1200 * MM, 'height': 1200 * MM, 'sill': 900 * MM}
    if not kit:                                  # without the kitchen room, every design is valid without A or B
        del d['rooms']['KIT']
    if options:
        d['optionSets'] = {'KS': {'name': 'Kitchen', 'primary': 'KA'}}
        d['options'] = {'KA': {'set': 'KS', 'name': 'A'}, 'KB': {'set': 'KS', 'name': 'B'}}
    if a:
        d['walls']['WA'] = w('S5', 'N5', option='KA')
        d['openings']['OA'] = {'wall': 'WA', 'offset': 1500 * MM, 'fill': 'T-door-36', 'option': 'KA'}
    if b:
        d['separators'] = {'SB': {'level': 'L1', 'start': 'S4', 'end': 'N4', 'option': 'KB'}}
        d['openings']['OB'] = {'wall': 'W4', 'offset': 500 * MM, 'fill': 'G', 'option': 'KB'}
    return d


def crossed():
    """The kitchen house with a short wall WB of option B across A's wall WA, at y = 2 m: never in one design."""
    d = kitchen_house()
    d['junctions'].update(BJ1={'level': 'L1', 'position': [4500 * MM, 2000 * MM], 'option': 'KB'},
                          BJ2={'level': 'L1', 'position': [5500 * MM, 2000 * MM], 'option': 'KB'})
    d['walls']['WB'] = {'level': 'L1', 'start': 'BJ1', 'end': 'BJ2', 'type': 'WT', 'option': 'KB'}
    return d


T('primitives', 'add-an-option-set', 'addElement adds the Kitchen option set, naming A its primary, and its options A '
  'and B: valid, and the set derives its options.', ['2.1.1', '1.3.1'], kitchen_house(False, False, False, kit=False),
  req({'op': 'addElement', 'collection': 'optionSets', 'id': 'KS', 'element': {'name': 'Kitchen', 'primary': 'KA'}},
      {'op': 'addElement', 'collection': 'options', 'id': 'KA', 'element': {'set': 'KS', 'name': 'A'}},
      {'op': 'addElement', 'collection': 'options', 'id': 'KB', 'element': {'set': 'KS', 'name': 'B'}}),
  check=lambda r, B: ensure(r['created'] == ['KA', 'KB', 'KS'] and sorted(derived(B)['options']['KS']['options']) == ['KA', 'KB'], r))
T('primitives', 'mint-option-set-and-option-ids', 'An option set and two options added with no IDs: they are minted '
  'with the prefixes OS and OP - OS1, then OP1 and OP2, which the set names as its primary before it exists.',
  ['1.5.1', '2.1.1'], kitchen_house(False, False, False, kit=False),
  req({'op': 'addElement', 'collection': 'optionSets', 'element': {'primary': 'OP1'}},
      {'op': 'addElement', 'collection': 'options', 'element': {'set': 'OS1'}},
      {'op': 'addElement', 'collection': 'options', 'element': {'set': 'OS1'}}),
  check=lambda r, B: ensure(r['created'] == ['OP1', 'OP2', 'OS1'], r['created']))
T('primitives', 'add-a-wall-in-an-option', 'With context.option KA, addWall adds A\'s wall between the kitchen and '
  'the dining room, and addElement its door: both are added in option A, and the junctions they use stay common.',
  ['2.8.1', '2.1.1'], kitchen_house(a=False, kit=False),
  req({'op': 'addWall', 'id': 'WA', 'level': 'L1', 'start': 'S5', 'end': 'N5', 'type': 'WT'},
      {'op': 'addElement', 'collection': 'openings', 'id': 'OA', 'element': {'wall': 'WA', 'offset': 1500 * MM, 'fill': 'T-door-36'}},
      option='KA'),
  check=lambda r, B: ensure(B['walls']['WA']['option'] == 'KA' and B['openings']['OA']['option'] == 'KA'
                            and 'option' not in B['junctions']['S5'] and r['resolved'][0].get('option') is None, B))
T('primitives', 'option-named-by-an-element-is-kept', 'With context.option KA, an addElement whose element names '
  'option KB: it is added in KB, as given.', ['2.8.1'], kitchen_house(b=False, kit=False),
  req({'op': 'addElement', 'collection': 'separators', 'id': 'SB',
       'element': {'level': 'L1', 'start': 'S4', 'end': 'N4', 'option': 'KB'}}, option='KA'),
  check=lambda r, B: ensure(B['separators']['SB']['option'] == 'KB', B['separators']))
T('primitives', 'context-option-only-where-an-option-may-be', 'With context.option KA, addElement adds a level and a '
  'type: neither may be in an option (Core 19.2.1), so neither is given one.', ['2.8.1'], kitchen_house(),
  req({'op': 'addElement', 'collection': 'levels', 'id': 'L2', 'element': {'building': 'B1', 'elevation': 2700 * MM, 'height': 2700 * MM}},
      {'op': 'addElement', 'collection': 'types', 'id': 'T2', 'element': {'kind': 'doorType'}}, option='KA'),
  check=lambda r, B: ensure('option' not in B['levels']['L2'] and 'option' not in B['types']['T2'], B))
T('primitives', 'switch-the-primary-option', 'setProperty of the set\'s /primary to KB: B\'s design is now the one '
  'derived - the open kitchen, 3950 mm wide.', ['2.3.1', '2.8.1'], kitchen_house(),
  req({'op': 'setProperty', 'id': 'KS', 'path': '/primary', 'value': 'KB'}),
  check=lambda r, B: ensure(derived(B)['options']['KS']['chosen'] == 'KB' and 'WA' not in derived(B)['walls'], derived(B)))
T('primitives', 'move-an-element-to-another-option', 'setProperty of the window OB\'s /option to KA: the window is '
  'option A\'s now, in the common north wall.', ['2.3.1'], kitchen_house(),
  req({'op': 'setProperty', 'id': 'OB', 'path': '/option', 'value': 'KA'}),
  check=lambda r, B: ensure(derived(B)['options']['KS']['options']['KA']['members'] == ['OA', 'OB', 'WA'], derived(B)['options']))
T('primitives', 'make-an-element-common', 'unsetProperty of the window OB\'s /option: it is in every design.',
  ['2.3.1'], kitchen_house(), req({'op': 'unsetProperty', 'id': 'OB', 'path': '/option'}),
  check=lambda r, B: ensure('option' not in B['openings']['OB'] and 'OB' in derived(B)['openings'], B['openings']))
T('primitives', 'remove-an-option-blocked', 'Removing option KB without cascade is blocked by what is in it.',
  ['2.2.1'], kitchen_house(), req({'op': 'removeElement', 'id': 'KB'}), 'rejected', [('FS-OPS-006', ['KB', 'OB', 'SB'])])
T('primitives', 'remove-an-option-and-what-is-in-it', 'Removing option KB with cascade takes its separator and its '
  'window; the set has one option left, which Core only lints.', ['2.2.2'], kitchen_house(),
  req({'op': 'removeElement', 'id': 'KB', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['KB', 'OB', 'SB'], r['removed']))
T('primitives', 'remove-the-primary-option', 'Removing option KA, the set\'s primary, with cascade: the set\'s '
  '`primary` blocks nothing, and names no option afterwards, so the result is invalid: FS-INV-002.',
  ['2.2.2', '1.2.3'], kitchen_house(), req({'op': 'removeElement', 'id': 'KA', 'cascade': True}), 'rejected',
  [('FS-INV-002', ['KS'])])
T('primitives', 'remove-the-primary-and-switch', 'Removing KA with cascade and making KB primary in the same batch: '
  'valid, the kitchen open.', ['2.2.2', '2.3.1'], kitchen_house(),
  req({'op': 'removeElement', 'id': 'KA', 'cascade': True}, {'op': 'setProperty', 'id': 'KS', 'path': '/primary', 'value': 'KB'}),
  check=lambda r, B: ensure(r['removed'] == ['KA', 'OA', 'WA'], r['removed']))
T('primitives', 'remove-an-option-set-blocked', 'Removing the set without cascade is blocked by its options.',
  ['2.2.1'], kitchen_house(), req({'op': 'removeElement', 'id': 'KS'}), 'rejected', [('FS-OPS-006', ['KA', 'KB', 'KS'])])
T('primitives', 'remove-an-option-set', 'Removing the set with cascade takes its options and everything in them: the '
  'house is left with only its common elements.', ['2.2.2'], kitchen_house(kit=False),
  req({'op': 'removeElement', 'id': 'KS', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['KA', 'KB', 'KS', 'OA', 'OB', 'SB', 'WA'] and 'optionSets' not in B, r['removed']))
T('primitives', 'add-into-another-option-rejected', 'With context.option KB, a door added in A\'s wall: it is in B, '
  'and refers to an element of A, so the result is invalid: FS-INV-1102.', ['1.2.3', '2.8.1'], kitchen_house(),
  req({'op': 'addElement', 'collection': 'openings', 'id': 'OX', 'element': {'wall': 'WA', 'offset': 300 * MM, 'fill': 'T-door-36'}},
      option='KB'), 'rejected', [('FS-INV-1102', ['OX', 'WA'])])
T('primitives', 'invalid-only-in-an-option-design', 'With context.option KB, a pantry room anchored at x = 4.5 m: '
  'in B\'s design the open kitchen\'s face has KIT\'s anchor too, so B\'s design is invalid and the rejection carries '
  'FS-INV-202 with "design": "KB".', ['1.2.3', '2.8.1'], kitchen_house(),
  req({'op': 'addElement', 'collection': 'rooms', 'id': 'PANTRY', 'element': {'level': 'L1', 'anchor': [4500 * MM, 2000 * MM]}},
      option='KB'), 'rejected', [('FS-INV-202', ['KIT', 'PANTRY'], 'KB')])
T('transactions', 'option-sets-in-a-0.2-document', 'An option set added to a document that declares "0.2": Core '
  '0.2\'s schema has no optionSets, so the result is invalid: FS-SCH-001.', ['1.2.3', '2.1.1'],
  v02.v2(kitchen_house(False, False, False, kit=False)),
  req({'op': 'addElement', 'collection': 'optionSets', 'id': 'KS', 'element': {'primary': 'KA'}}), 'rejected',
  [('FS-SCH-001', [])])
T('transactions', 'context-option-not-an-id', 'A context whose option is a number: the request is malformed.',
  ['1.1.3'], kitchen_house(), {'batch': [{'op': 'setProperty', 'id': 'R1', 'path': '/name', 'value': 'x'}],
                               'context': {'option': 2}}, 'rejected', [('FS-OPS-001', [])])
T('transactions', 'context-option-in-ops-0.3-only', 'A context with an unknown member beside option is still '
  'malformed: option is the only member 0.3 adds.', ['1.1.3'], kitchen_house(),
  {'batch': [{'op': 'setProperty', 'id': 'DIN', 'path': '/name', 'value': 'x'}], 'context': {'option': 'KA', 'design': {}}},
  'rejected', [('FS-OPS-001', [])])

T('references', 'faces-of-the-edit-design', 'B draws a short wall WB across A\'s wall WA: the level as a whole is not '
  'planar, but each design is. With context.option KA, "wall between DIN and KIT" reads the faces of A\'s design, '
  'and is WA: the door is added there, in A.', ['2.8.2', '3.4.1', '2.8.1'], crossed(),
  req({'op': 'addOpening', 'id': 'OA2', 'wall': 'wall between DIN and KIT', 'at': 2600 * MM, 'fill': 'T-door-36'},
      option='KA'),
  check=lambda r, B: ensure(B['openings']['OA2']['wall'] == 'WA' and B['openings']['OA2']['option'] == 'KA', B['openings']))
T('references', 'faces-of-the-primary-design', 'The same door with no context.option: the edit design is the primary '
  'design, A\'s, so the selector finds WA; the door is common, and WA is A\'s, so the result is invalid: FS-INV-1102.',
  ['2.8.2', '1.2.3'], crossed(),
  req({'op': 'addOpening', 'id': 'OA2', 'wall': 'wall between DIN and KIT', 'at': 2600 * MM, 'fill': 'T-door-36'}),
  'rejected', [('FS-INV-1102', ['OA2', 'WA'])])
T('references', 'draw-from-junctions-of-the-edit-design', 'With context.option KB, drawSeparator from S4\'s position '
  'to N4\'s: both are common, so in the edit design, and the separator is drawn between them, in B.',
  ['2.8.2', '4.1.1', '2.8.1'], kitchen_house(b=False, kit=False),
  req({'op': 'drawSeparator', 'id': 'SB', 'level': 'L1', 'from': [4000 * MM, 0], 'to': [4000 * MM, KY]}, option='KB'),
  check=lambda r, B: ensure(B['separators']['SB'] == {'level': 'L1', 'start': 'S4', 'end': 'N4', 'option': 'KB'}
                            and r['created'] == ['SB'], r))

T('normalization', 'option-wall-ends-on-a-common-wall', 'With context.option KB, drawWall from a point in the kitchen '
  'to a point on the common north wall W4: W4 is split there into two common walls, and the junction where they meet '
  '- added by drawWall in B - is common now, since a common wall ends at it; the drawn wall stays in B.',
  ['5.5.1', '5.2.1', '2.8.1'], kitchen_house(),
  req({'op': 'drawWall', 'id': 'WP', 'level': 'L1', 'from': [7300 * MM, 1500 * MM], 'to': [7300 * MM, KY], 'type': 'WT'},
      option='KB'),
  check=lambda r, B: ensure(B['walls']['WP']['option'] == 'KB' and 'option' not in B['junctions'][B['walls']['WP']['end']]
                            and B['junctions'][B['walls']['WP']['start']]['option'] == 'KB'
                            and all('option' not in B['walls'][x] for x in r['created'] if x in B['walls'] and x != 'WP'), B))
T('normalization', 'two-options-never-planarized', 'With context.option KB, drawWall across A\'s wall WA: two options '
  'of one set are never in one design, so neither wall is split.', ['5.5.1'], kitchen_house(),
  req({'op': 'drawWall', 'id': 'WB', 'level': 'L1', 'from': [4500 * MM, 2000 * MM], 'to': [5500 * MM, 2000 * MM], 'type': 'WT'},
      option='KB'),
  check=lambda r, B: ensure(B['walls']['WA']['start'] == 'S5' and B['walls']['WA']['end'] == 'N5'
                            and sorted(x for x in r['created'] if x.startswith('W')) == ['WB'], r['created']))
T('normalization', 'option-junctions-merge-into-common-ones', 'With context.option KB, two junctions added at the '
  'positions of the common junctions S4 and N4, and a separator between them: 5.1 merges each into the common one, '
  'so B\'s separator ends at S4 and N4.', ['5.5.1', '5.1.1'], kitchen_house(b=False, kit=False),
  req({'op': 'addJunction', 'id': 'JX', 'level': 'L1', 'position': [4000 * MM, 0]},
      {'op': 'addJunction', 'id': 'JY', 'level': 'L1', 'position': [4000 * MM, KY]},
      {'op': 'addSeparator', 'id': 'SB', 'level': 'L1', 'start': 'JX', 'end': 'JY'}, option='KB'),
  check=lambda r, B: ensure(B['separators']['SB'] == {'level': 'L1', 'start': 'S4', 'end': 'N4', 'option': 'KB'}
                            and 'JX' not in B['junctions'], B['separators']))
T('inverse', 'option-set-removed-and-undone', 'Removing the set with cascade: the inverse adds the set, then its '
  'options, then what was in them - option sets and options come after junctions in step 2\'s order - and applying '
  'it gives back A exactly (1.6.1).', ['1.6.1'], kitchen_house(kit=False),
  req({'op': 'removeElement', 'id': 'KS', 'cascade': True}),
  check=lambda r, B: ensure([p['id'] for p in r['inverse']] == ['KS', 'KA', 'KB', 'WA', 'SB', 'OA', 'OB'], r['inverse']))
# ============================================================================= materials and finishes (0.3): Core chapter 18
import tools.oracle.ops_author03_materials as materials                       # noqa: E402

materials.declare()

# ============================================================================= the US starter library (Core 0.3, 8.1)
import tools.oracle.us_library as us_library                                 # noqa: E402

EXT = 'wall-2x6-exterior-fibre-cement'
SWING = 'door-exterior-swing-36x80'


def embedded(B, item):
    """Whether B holds the item and every material it uses exactly as the library publishes them."""
    return all(B.get(op['collection'], {}).get(op['id']) == op['element'] for op in us_library.embed_ops(item))


T('primitives', 'embed-a-library-type', 'The US starter library\'s recipe for embedding an item: the item\'s published '
  'batch - addElement of each material the 2x6 exterior wall\'s layers use, then of the wall type, each with its '
  'source - and setProperty pointing the four walls of the box at it, in one batch. The wall type and its materials '
  'are added exactly as given (2.1), so the document holds the library\'s elements byte for byte and is complete on '
  'its own; the box\'s own wall type is now unused (FS-LINT-006 is a lint, so the batch commits).', ['2.1.1', '2.3.1'],
  v3(box()), req(*us_library.embed_ops(EXT), *({'op': 'setProperty', 'id': w, 'path': '/type', 'value': EXT}
                                              for w in ('W1', 'W2', 'W3', 'W4'))),
  check=lambda r, B: ensure(embedded(B, EXT) and all(w['type'] == EXT for w in B['walls'].values())
                            and r['created'] == sorted(op['id'] for op in us_library.embed_ops(EXT)), r['created']))
T('primitives', 'embed-a-library-type-twice', 'The 36-inch exterior door\'s published batch applied to a document '
  'that already holds it: addElement of an ID that is used fails the batch with FS-OPS-005 (2.1.1) - which is why the '
  'library\'s recipe leaves out every element the document already holds with the same content, so that embedding '
  'twice adds nothing.', ['2.1.1'], us_library.embed(v3(box()), SWING), req(*us_library.embed_ops(SWING)),
  'rejected', [('FS-OPS-005', [])])

NEW = list(TESTS)
del TESTS[:]


def main(argv) -> int:
    return 1 if write_all(prune='--prune' in argv, tests=BASE + NEW, suite=SUITE03, profile=OPS_03) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

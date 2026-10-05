"""The conformance suite of Floorspec Ops 0.3, as the script that writes it.

    python3.13 -m tools.oracle.ops_author03            rewrite every test from its declaration below
    python3.13 -m tools.oracle.ops_author03 --prune    ...and delete test directories no longer declared

The suite is the Ops 0.2 suite, carried forward to 0.3 - every 0.2 test, in the same group under
the same number, on the same documents A: Ops 0.3 applies to Core 0.2 and 0.1 documents exactly as
Ops 0.2 did (0.4). It retires no statement, so every test covers what it covered. After them come
the five tests that pin what the Ops text says as the oracle does (1.5, 3.3, 4.2, 4.10), declared
after Ops 0.2 was published and so first published with 0.3 (ops_author02.py, PUBLISHED); then, in
each group, the tests of what 0.3 adds: Core 0.3 documents, whose door and window types declare an
operation and a clear opening and whose openings may override it, and whose rooms have floors and
flat, tray or vaulted ceilings and whose slabs a purpose, edited with the primitives Ops already
has; and moveRoom moving a vaulted ceiling's ridge with its room (4.3.2). Every expected status and diagnostic is written by hand and cross-checked against the
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
DESCRIPTIONS = {
    'unknown-collection': [('not a collection of 0.2', 'not a collection of 0.3')],
    'extension-data-in-a-0.1-document': [('(Core 1.2.4)', '(Core 1.2.6)')],
}


def carry(tc):
    tc = copy.deepcopy(tc)
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

NEW = list(TESTS)
del TESTS[:]


def main(argv) -> int:
    return 1 if write_all(prune='--prune' in argv, tests=BASE + NEW, suite=SUITE03, profile=OPS_03) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

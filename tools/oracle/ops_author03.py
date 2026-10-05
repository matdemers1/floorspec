"""The conformance suite of Floorspec Ops 0.3, as the script that writes it.

    python3.13 -m tools.oracle.ops_author03            rewrite every test from its declaration below
    python3.13 -m tools.oracle.ops_author03 --prune    ...and delete test directories no longer declared

The suite is the Ops 0.2 suite, carried forward to 0.3 - every 0.2 test, in the same group under
the same number, on the same documents A: Ops 0.3 applies to Core 0.2 and 0.1 documents exactly as
Ops 0.2 did (0.4). It retires no statement, so every test covers what it covered. After them come
the five tests that pin what the Ops text says as the oracle does (1.5, 3.3, 4.2, 4.10), declared
after Ops 0.2 was published and so first published with 0.3 (ops_author02.py, PUBLISHED); then, in
each group, the tests of what 0.3 adds: Core 0.3 documents, whose door and window types declare an
operation and a clear opening and whose openings may override it, edited with the primitives Ops
already has. Every expected status and diagnostic is written by hand and cross-checked against the
oracle, applied as Ops 0.3 (version.OPS_03); the values that matter are asserted by hand in each
test's check. Afterwards, `python3.13 -m tools.oracle.regenerate` re-verifies the suite from the
files alone. Add new tests at the end of their group's section.
"""
import copy
import os
import sys

import tools.oracle.ops_author02 as v02                # declares the 0.2 suite: v02.BASE + v02.TESTS
from tools.oracle.ops_author import box, door_on_south, ensure, resolved_eq
from tools.oracle.ops_author_lib import FT, IN, REPO, TESTS, T, doc, req, write_all
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

NEW = list(TESTS)
del TESTS[:]


def main(argv) -> int:
    return 1 if write_all(prune='--prune' in argv, tests=BASE + NEW, suite=SUITE03, profile=OPS_03) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

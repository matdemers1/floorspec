"""The conformance suite of Floorspec Ops 0.4, as the script that writes it.

    python3.13 -m tools.oracle.ops_author04            rewrite every test from its declaration below
    python3.13 -m tools.oracle.ops_author04 --prune    ...and delete test directories no longer declared

The suite is the Ops 0.3 suite, carried forward to 0.4 - every 0.3 test, in the same group under the
same number, on the same documents A: Ops 0.4 applies to Core 0.3, 0.2 and 0.1 documents exactly as
Ops 0.3 did (0.4), with a Core 0.4 reader, which reads them exactly as a Core 0.3 reader does, the lints
of winder and spiral stairs apart - and none of the suite's documents has one. It retires no statement:
its requests have Ops 0.3's shape and match schema/ops/0.3. The one test that names a draft A's reader
does not implement moves from "0.4" to "0.5". After them, in each group, come the tests of what 0.4
adds: Core 0.4 documents, whose stairs may declare a minHeadroom and whose winder stairs a newel, edited
with the primitives Ops already has, judged by Core 0.4's invariants (FS-INV-905, FS-INV-906); and the
batch that upgrades a Core 0.3 document to 0.4 - the migration of Core 20.7, expressed as Ops (Core
20.11). Every expected status and diagnostic is written by hand and cross-checked against the oracle,
applied as Ops 0.4 (version.OPS_04); the values that matter are asserted by hand in each test's check.
"""
import copy
import json
import os
import sys

import tools.oracle.ops_author03 as v03                # declares the 0.3 suite: v03.BASE + v03.NEW
from tools.oracle.ops_author import ensure
from tools.oracle.ops_author_lib import FT, IN, REPO, TESTS, T, doc, req, write_all
from tools.oracle.ops.version import OPS_04
from tools.oracle.ops_author03 import STAIR, upstairs

SUITE04 = os.path.join(REPO, 'conformance', 'ops', '0.4')

RETARGET = {
    'document-other-version': (doc(floorspec='0.5'), 'Document A declares Floorspec 0.5, which a Core 0.4 reader does not '
                               'implement (FS-DOC-001): FS-OPS-002.'),
}


def carry(tc):
    tc = copy.deepcopy(tc)
    tc['description'] = tc['description'].replace('(Core 1.2.6)', '(Core 1.2.8)')
    if tc['slug'] in RETARGET:
        tc['a'], tc['description'] = RETARGET[tc['slug']]
    return tc


BASE = [carry(tc) for tc in v03.BASE + v03.NEW]
del TESTS[:]


def v(d, version):
    d = copy.deepcopy(d)
    d['floorspec'] = version
    return d


def derived(B):
    """What a Core 0.4 deriver derives for the committed document B."""
    from tools.oracle.validate import READER_04, check as core_check
    result, _, _ = core_check(json.dumps(B).encode('utf-8'), READER_04)
    assert result['valid'], result['diagnostics']
    return result['derived']


WINDER = {'kind': 'winder', 'turn': 'left', 'angle': 'quarter', 'risersBeforeTurn': 4, 'winders': 3}


def with_stair(version='0.4', **st):
    d = v(upstairs(), version)
    d['stairs'] = {'ST1': {**copy.deepcopy(STAIR), **st}}
    return d


# ============================================================================= transactions (0.4)
T('transactions', 'apply-to-a-0.4-document', 'A is a Core 0.4 document whose stair declares the headroom it is '
  'designed for; it is valid, and a batch applies to it.', ['1.2.1', '1.3.1'], with_stair(minHeadroom=80 * IN),
  req({'op': 'setProperty', 'id': 'ST1', 'path': '/name', 'value': 'Main stair'}),
  check=lambda r, B: ensure(B['floorspec'] == '0.4' and B['stairs']['ST1']['minHeadroom'] == 80 * IN, B))
T('transactions', 'upgrade-to-0.4', 'A is a Core 0.3 document with a winder stair. The batch is the migration of '
  'Core 20.7 as Ops: setProperty of $document /floorspec to "0.4", which moves nothing; then it gives the winder a '
  'newel of 4 in, which 0.4 adds: the result is a valid Core 0.4 document whose winders have a narrow end.',
  ['2.3.1', '1.3.1'], with_stair('0.3', form=WINDER),
  req({'op': 'setProperty', 'id': '$document', 'path': '/floorspec', 'value': '0.4'},
      {'op': 'setProperty', 'id': 'ST1', 'path': '/form/newel', 'value': 4 * IN}),
  check=lambda r, B: ensure(B['floorspec'] == '0.4' and derived(B)['stairs']['ST1']['narrowGoing'] > 0,
                            derived(B)['stairs']['ST1']))
T('transactions', 'newel-in-a-0.3-document', 'The same newel without declaring "0.4": the result declares "0.3", '
  'whose schema has no "newel" (Core 1.2.8), so it is invalid and the rejection carries FS-SCH-001.',
  ['1.2.3', '1.2.2'], with_stair('0.3', form=WINDER),
  req({'op': 'setProperty', 'id': 'ST1', 'path': '/form/newel', 'value': 4 * IN}), 'rejected', [('FS-SCH-001', [])])

# ============================================================================= primitives (0.4)
T('primitives', 'add-a-winder-stair', 'addElement adds a quarter-turn winder stair with a newel to a Core 0.4 '
  'document: the result is valid, and its three winders are derived between its two flights.', ['2.1.1', '1.3.1'],
  v(upstairs(), '0.4'),
  req({'op': 'addElement', 'collection': 'stairs', 'id': 'ST1', 'element': {**STAIR, 'form': {**WINDER, 'newel': 4 * IN}}}),
  check=lambda r, B: ensure(sum(1 for s in derived(B)['stairs']['ST1']['steps'] if s.get('winder')) == 3,
                            derived(B)['stairs']['ST1']))
T('primitives', 'set-a-spiral-form', 'setProperty makes the stair a spiral 5\' across turning left through 270 '
  'degrees, and sets its width to 2\'3": valid, and every one of its treads is derived about its centre.', ['2.3.1'],
  with_stair(),
  req({'op': 'setProperty', 'id': 'ST1', 'path': '/form',
       'value': {'kind': 'spiral', 'turn': 'left', 'diameter': 5 * FT, 'sweep': 270_000_000}},
      {'op': 'setProperty', 'id': 'ST1', 'path': '/width', 'value': 27 * IN}),
  check=lambda r, B: ensure(len(derived(B)['stairs']['ST1']['steps']) == 13 and 'centre' in derived(B)['stairs']['ST1'],
                            derived(B)['stairs']['ST1']))
T('primitives', 'newel-reaches-the-walkline', 'setProperty of a newel 13 in deep on a winder stair 3\' wide: its far '
  'corner is 13 sqrt 2 in from the pivot, beyond the walkline 18 in away, so the result has FS-INV-905 and the batch '
  'is rejected with it.', ['1.2.3', '2.3.1'], with_stair(form=WINDER),
  req({'op': 'setProperty', 'id': 'ST1', 'path': '/form/newel', 'value': 13 * IN}), 'rejected',
  [('FS-INV-905', ['ST1'])])
T('primitives', 'spiral-of-too-few-risers', 'setProperty of 3 risers on a spiral that turns 360 degrees: each tread '
  'would turn 180 degrees, FS-INV-906, and the batch is rejected.', ['1.2.3', '2.3.1'],
  with_stair(form={'kind': 'spiral', 'turn': 'left', 'diameter': 5 * FT, 'sweep': 360_000_000}, width=27 * IN),
  req({'op': 'setProperty', 'id': 'ST1', 'path': '/risers', 'value': 3}), 'rejected', [('FS-INV-906', ['ST1'])])
T('primitives', 'unset-a-min-headroom', 'unsetProperty of a stair\'s /minHeadroom: it declares no headroom, and so '
  'derives no opening.', ['2.3.1'], with_stair(minHeadroom=80 * IN),
  req({'op': 'unsetProperty', 'id': 'ST1', 'path': '/minHeadroom'}),
  check=lambda r, B: ensure('minHeadroom' not in B['stairs']['ST1'] and 'opening' not in derived(B)['stairs']['ST1'], B))

# ============================================================================= inverse (0.4)
T('inverse', 'newel-set-and-undone', 'Setting a winder\'s newel and the stair\'s minHeadroom in one batch: the inverse '
  'sets the stair\'s form back as A has it, whole - the members that differ are the stair\'s own, /form and '
  '/minHeadroom (1.6) - and unsets its minHeadroom; applying it gives back A exactly (1.6.1).', ['1.6.1'],
  with_stair(form=WINDER),
  req({'op': 'setProperty', 'id': 'ST1', 'path': '/form/newel', 'value': 4 * IN},
      {'op': 'setProperty', 'id': 'ST1', 'path': '/minHeadroom', 'value': 80 * IN}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'setProperty', 'id': 'ST1', 'path': '/form', 'value': WINDER},
                                             {'op': 'unsetProperty', 'id': 'ST1', 'path': '/minHeadroom'}], r['inverse']))

NEW = list(TESTS)
del TESTS[:]


def main(argv) -> int:
    return 1 if write_all(prune='--prune' in argv, tests=BASE + NEW, suite=SUITE04, profile=OPS_04) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

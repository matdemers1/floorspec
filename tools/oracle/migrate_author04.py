"""The migration suite of Floorspec Core 0.4 (chapter 20), as the script that writes it.

    python3.13 -m tools.oracle.migrate_author04            rewrite every test from its declaration below
    python3.13 -m tools.oracle.migrate_author04 --prune    ...and delete test directories no longer declared

The suite is the Core 0.3 migration suite carried forward - every test of conformance/migration/0.3, in
the same group under the same number, run by a migrator of 0.4, which migrates to 0.3 exactly as a
migrator of 0.3 does; the drafts it names as unknown move from "0.4" to "0.5" - followed by the tests of
what 0.4 adds: the step from 0.3 to 0.4 (20.7), which only makes a document declare "0.4", and migrations
that end in 0.4. Status, diagnostics, validation and moved pointers are written by hand and cross-checked
against the oracle's migrator (migrate.py, DRAFTS_04) and a reader of the target; the migration's bytes and
hash come from the oracle. `python3.13 -m tools.oracle.regenerate` re-verifies the suite from the files.
"""
import copy
import os
import sys

import tools.oracle.migrate_author as v03            # declares the 0.3 suite: v03.TESTS
from tools.oracle.author03 import WINDER_Q, hall_house
from tools.oracle.author02 import element, free, with_elements
from tools.oracle.author_lib import MM, REPO, _diag
from tools.oracle.migrate import DRAFTS_04, RECORD
from tools.oracle.migrate_author import OPAQUE, house, outlet, published, v

SUITE04 = os.path.join(REPO, 'conformance', 'migration', '0.4')
SCH = [('FS-SCH-001', [])]
UNKNOWN = {
    # slug: (input's draft, target, description) - "0.4" was unknown to a migrator of 0.3, and "0.5" is to one of 0.4
    'unknown-draft': ('0.5', None, 'The document declares "0.5", a draft this migrator does not implement: refused with '
                                   'FS-DOC-001 (20.2.1), whatever the target.'),
    'unknown-target': (None, '0.5', 'The target "0.5" is not a draft this migrator implements (20.2.3).'),
}


RETIRED = {'FS-CORE-1.2.5': 'FS-CORE-1.2.7', 'FS-CORE-1.2.6': 'FS-CORE-1.2.8'}


def carried(tc):
    tc = copy.deepcopy(tc)
    tc['covers'] = [RETIRED.get(c, c) for c in tc['covers']]
    tc['description'] = tc['description'].replace('(1.2.6)', '(1.2.8)').replace(', 1.2.6)', ', 1.2.8)')
    if tc['slug'] in UNKNOWN:
        draft, to, description = UNKNOWN[tc['slug']]
        if draft is not None:
            tc['inp']['floorspec'] = draft
        if to is not None:
            tc['to'] = to
        tc['description'] = description
    return tc


BASE = [carried(tc) for tc in v03.TESTS]
TESTS = []


def t(group, slug, description, covers, inp, to, status='migrated', diags=(), validation=(), moved=None, raw=None,
      valid=None):
    TESTS.append(dict(group=group, slug=slug, description=description, covers=v03.cov(*covers), inp=inp, raw=raw, to=to,
                      status=status, diags=[_diag(*x) for x in diags], validation=[_diag(*x) for x in validation],
                      valid=valid, moved=moved))


def winder_house(version='0.3', **form):
    """The Core 0.3 suite's quarter-turn winder stair (core/0.3/stairs/014), declaring `version`."""
    d = v(hall_house(x0=1000, x1=2800, y1=2800, form={**WINDER_Q, **form}), version)
    return d


WELL18 = [('FS-LINT-003', []), ('FS-LINT-018', ['ST1'])]

# ============================================================================= documents (0.4)
t('documents', 'newel-in-a-0.3-document',
  'A document declaring "0.3" whose winder stair has a newel, which 0.4 added: it does not match the schema of the '
  'draft it declares, so it is refused with FS-SCH-001 (20.2.1) - a migrator does not guess that 0.4 was meant.',
  ['20.2.1'], winder_house(newel=100 * MM), '0.4', 'refused', SCH)

# ============================================================================= targets (0.4)
t('targets', 'own-draft-0.4',
  'A 0.4 document - a winder stair with a newel, designed for 2000 mm of headroom - migrated to 0.4 is the document '
  'itself (20.1.2).',
  ['20.1.2'], v(hall_house(x0=1000, x1=2800, y1=2800, form={**WINDER_Q, 'newel': 100 * MM}, minHeadroom=2000 * MM),
                '0.4'), '0.4', validation=[('FS-LINT-003', [])])
t('targets', '0.4-to-0.3',
  'A 0.4 document cannot be migrated to 0.3: a migration never goes backwards (20.2.3).',
  ['20.2.3'], v(house(), '0.4'), '0.3', 'refused', [('FS-MIG-001', [])])

# ============================================================================= the step from 0.3 to 0.4 (20.7)
t('step-0.3-0.4', 'version-only',
  'A 0.3 house with a winder stair: the step makes it declare "0.4" and changes nothing else - no record, no extras '
  '(20.7.1, 20.3.2). A reader of 0.4 reads both alike: it derives the stair\'s winders, walkline, goings and headroom '
  'for the 0.3 document as for its migration, and reports FS-LINT-018 for both, since the winders meet at a point '
  '(20.6.1).',
  ['20.7.1', '20.3.2', '20.1.4', '20.6.1'], winder_house(), '0.4', validation=WELL18)
d = with_elements(house('0.3'), {'X1': outlet(option='OB')}, ext='FS_electrical', coll='devices', version='0.1.0')
d.update(optionSets={'S1': {'primary': 'OA'}}, options={'OA': {'set': 'S1'}, 'OB': {'set': 'S1'}})
t('step-0.3-0.4', 'options-and-elements-kept',
  'A 0.3 document with design options and an extension element in one - its "option" member is core\'s in 0.3 and '
  '0.4 alike: the step moves nothing (20.7.1), and a reader of 0.4 reads the element in option OB in both (20.6.1).',
  ['20.7.1', '20.3.2', '20.6.1'], d, '0.4')
t('step-0.3-0.4', 'extras-untouched',
  'A 0.3 document whose extras carry a record of an earlier migration and a member that is not an array where a '
  'record would go is no obstacle either: the step moves nothing, so it adds no record and changes no extras (20.3.2, '
  '20.3.3, 20.7.1).',
  ['20.7.1', '20.3.2', '20.3.3'], {**house('0.3'), 'extras': {RECORD: 'done', 'camera': [1, 2]}}, '0.4')

# ============================================================================= composition (0.4)
t('composition', '0.1-to-0.4',
  'A 0.1 document with opaque collections, migrated to 0.4: the step from 0.1 to 0.2 moves them, and the steps from '
  '0.2 to 0.3 and from 0.3 to 0.4 move nothing - one record (20.1.3, 20.3.2).',
  ['20.1.3', '20.4.1', '20.5.1', '20.7.1', '20.3.2', '20.6.1'],
  {**house(), 'extensionsUsed': {'FS_furniture': '0.1'}, 'extensions': {'FS_furniture': {'collections': OPAQUE}}},
  '0.4', moved={'0.1': ['/extensions/FS_furniture/collections']})
t('composition', '0.2-to-0.4',
  'A 0.2 document whose extension element has an "option" of its own, migrated to 0.4: the step from 0.2 to 0.3 '
  'moves it, and the step from 0.3 to 0.4 only changes the version (20.1.3).',
  ['20.1.3', '20.5.1', '20.7.1', '20.6.1'],
  with_elements(house('0.2'), {'X4': outlet(option='deluxe'), 'P1': element(host=free(2500 * MM, 1000 * MM))},
                ext='FS_electrical', coll='devices', version='0.1.0'),
  '0.4', moved={'0.2': ['/extensions/FS_electrical/collections/devices/X4/option']})
t('composition', '0.3-migration-to-0.4',
  'The 0.3 migration of a 0.2 document, its record already in extras, migrated on to 0.4: the step from 0.3 to 0.4 '
  'appends nothing, and the record of the step from 0.2 to 0.3 is kept as it was (20.1.3, 20.3.2).',
  ['20.1.3', '20.3.2', '20.7.1'],
  {**house('0.3'), 'extras': {RECORD: [{'from': '0.2', 'to': '0.3', 'moved': [
      {'pointer': '/extensions/FS_electrical/collections/devices/X4/option', 'value': 'deluxe'}]}]}},
  '0.4')

# ============================================================================= examples (0.4)
t('examples', 'three-room-house-0.1-to-0.4',
  'The Phase 1 exit demo as Core 0.1 published it (core/0.1/examples/001-three-room-house), migrated to 0.4: it '
  'declares "0.4" and is otherwise byte for byte the document, members sorted; a reader of 0.4 reads both alike '
  '(20.1.3, 20.6.1).',
  ['20.1.3', '20.6.1'], None, '0.4', raw=published('core/0.1/examples/001-three-room-house'))
t('examples', 'two-storey-template-0.3-to-0.4',
  'The two-storey starter template (core/0.3/examples/005-two-storey-template, templates/two-storey.floorspec.json), '
  'migrated to 0.4: its L-shaped stair, its well and its vaulted bedroom read the same under 0.4 (20.7.1, 20.6.1).',
  ['20.7.1', '20.6.1'], None, '0.4', raw=published('core/0.3/examples/005-two-storey-template'),
  validation=[('FS-LINT-003', [])])

NEW = list(TESTS)


def main(argv) -> int:
    return 1 if v03.write_all('--prune' in argv, tests=BASE + NEW, suite=SUITE04, drafts=DRAFTS_04) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

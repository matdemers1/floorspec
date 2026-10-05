"""The migration suite of Floorspec Core 0.3 (chapter 20), as the script that writes it.

    python3.13 -m tools.oracle.migrate_author            rewrite every test from its declaration below
    python3.13 -m tools.oracle.migrate_author --prune    ...and delete test directories no longer declared

Each test is a document, a target and what a migrator must do with them. `status`, `diagnostics`,
`validation` - what a reader of the target reports for the document and for its migration alike - and
the pointers a step moves are written by hand here and cross-checked against the oracle's migrator
(migrate.py) and validator; the migration's bytes and hash come from the oracle. Afterwards,
`python3.13 -m tools.oracle.regenerate` re-verifies the suite from the files alone
(migration_suite.py). Add new tests at the end of their group's section, so directories keep their
numbers.
"""
import copy
import json
import os
import shutil
import sys

from tools.oracle.author import room_doc as room_doc_01
from tools.oracle.author02 import element, free, wall_face, with_elements
from tools.oracle.author_lib import MM, REPO, _diag, fmt
from tools.oracle.migrate import RECORD, migrate
from tools.oracle.migration_suite import SUITE, expected_text, reading

TESTS = []
SCH = [('FS-SCH-001', [])]


def cov(*ids):
    return [i if i.startswith('FS-') else f'FS-CORE-{i}' for i in ids]


def t(group, slug, description, covers, inp, to, status='migrated', diags=(), validation=(), moved=None, raw=None,
      valid=None):
    """diags: the migrator's diagnostics, (code, [elements]). validation: the diagnostics a reader of `to`
    reports for the document and its migration; `valid` defaults to having no error among them. moved:
    {draft: [pointer, ...]}, the pointers the step from that draft moves, checked against the record."""
    TESTS.append(dict(group=group, slug=slug, description=description, covers=cov(*covers), inp=inp, raw=raw, to=to,
                      status=status, diags=[_diag(*x) for x in diags], validation=[_diag(*x) for x in validation],
                      valid=valid, moved=moved))


def v(d, version):
    d = copy.deepcopy(d)
    d['floorspec'] = version
    return d


def house(version='0.1', **extra):
    """One 4 m x 3 m room, R1, with an empty opening on W4: the model most tests vary."""
    d = room_doc_01(**extra)
    d['openings'] = {'O1': {'wall': 'W4', 'offset': 1000 * MM, 'width': 900 * MM, 'height': 2100 * MM}}
    return v(d, version)


def outlet(offset=1200 * MM, **kw):
    return element(size=(20 * MM, 80 * MM, 100 * MM), origin=(0, -40 * MM, 0),
                   host=wall_face('W2', 'right', offset, 300 * MM), device='receptacle', **kw)


def published(path):
    with open(os.path.join(REPO, 'conformance', *path.split('/'), 'input.json'), 'rb') as f:
        return f.read()


OPAQUE = {'pieces': {'SOFA': {'fallback': 'not a fallback', 'size': [1, 2]}}, 'other': 7}

# ============================================================================= documents: what a migrator is given (20.2)

t('documents', 'not-json',
  'The input is not a JSON text. A migrator refuses it with FS-JSON-001, as a validator reports it (20.2.1).',
  ['20.2.1'], None, '0.3', 'refused', [('FS-JSON-001', [])], raw=b'{"floorspec": "0.1", "project": ')
t('documents', 'duplicate-member',
  'The document names "floorspec" twice. A migrator refuses it with FS-JSON-002, and never guesses which of the two '
  'drafts it declares (20.2.1).',
  ['20.2.1'], None, '0.3', 'refused', [('FS-JSON-002', [])],
  raw=b'{"floorspec": "0.1", "floorspec": "0.2", "project": {"name": "Conformance"}}\n')
t('documents', 'unknown-draft',
  'The document declares "0.4", a draft this migrator does not implement: refused with FS-DOC-001 (20.2.1), whatever '
  'the target.',
  ['20.2.1'], v(house(), '0.4'), '0.3', 'refused', [('FS-DOC-001', [])])
t('documents', 'schema-of-its-own-draft',
  'A document declaring "0.1" with a program, which 0.2 added: it does not match the schema of the draft it declares, '
  'so it is refused with FS-SCH-001 (20.2.1) - a migrator does not guess which draft was meant.',
  ['20.2.1'], house(program={'items': {'KIT': {'function': 'kitchen'}}}), '0.3', 'refused', SCH)
t('documents', 'not-an-object',
  'An array is not a document: refused with FS-SCH-001, as a validator of the newest draft reports it (20.2.1).',
  ['20.2.1'], None, '0.3', 'refused', SCH, raw=b'[]\n')
t('documents', 'required-extension-not-implemented',
  'A 0.2 document that requires EXT_acoustics, which neither this migrator nor the reader implements. A reader rejects '
  'it with FS-DOC-002 (1.6.4), and so does a reader of 0.3 reading its migration; a migrator never reports FS-DOC-002 '
  'and migrates it (20.2.2).',
  ['20.2.2', '20.6.1'],
  {**house('0.2'), 'extensionsUsed': {'EXT_acoustics': '1.0'}, 'extensionsRequired': ['EXT_acoustics'],
   'extensions': {'EXT_acoustics': {'rating': 52}}}, '0.3',
  validation=[('FS-DOC-002', [])])
t('documents', 'broken-invariant',
  'A 0.1 document whose wall W3 ends at a junction that does not exist. It matches the 0.1 schema, so it is migrated '
  '(20.2.2), and its migration breaks the same invariant: a reader of 0.3 reports FS-INV-002 for both (20.6.1).',
  ['20.2.2', '20.6.1'],
  (lambda d: (d['walls']['W3'].update(end='J9'), d)[1])(house()), '0.3',
  validation=[('FS-INV-002', ['W3'])])

# ============================================================================= targets (20.1.2, 20.2.3)

t('targets', 'own-draft-is-the-document',
  'A 0.2 document migrated to 0.2 is the document itself (20.1.2): nothing moves, and nothing is canonicalized - its '
  'explicit "justification": "center", a constant default, is kept; its members are only sorted and indented (20.1.1).',
  ['20.1.1', '20.1.2'],
  (lambda d: (d['walls']['W1'].update(justification='center'), d)[1])(house('0.2')), '0.2')
t('targets', 'own-draft-0.3',
  'A 0.3 document migrated to 0.3 is the document itself (20.1.2), extension elements in an option included: '
  'the option member of a 0.3 extension element is core\'s, and no step runs.',
  ['20.1.2'],
  {**with_elements(house('0.3'), {'X1': outlet(option='OB')}, ext='FS_electrical', coll='devices', version='0.1.0'),
   'optionSets': {'S1': {'primary': 'OA'}}, 'options': {'OA': {'set': 'S1'}, 'OB': {'set': 'S1'}}}, '0.3')
t('targets', 'earlier-draft',
  'A 0.3 document cannot be migrated to 0.2: a migration never goes backwards (20.2.3).',
  ['20.2.3'], house('0.3'), '0.2', 'refused', [('FS-MIG-001', [])])
t('targets', 'unknown-target',
  'The target "0.4" is not a draft this migrator implements (20.2.3).',
  ['20.2.3'], house(), '0.4', 'refused', [('FS-MIG-001', [])])
t('targets', 'target-not-a-string',
  'The target 0.3 is a number, not the string "0.3": it names no draft (20.2.3).',
  ['20.2.3'], house(), 0.3, 'refused', [('FS-MIG-001', [])])
t('targets', 'document-before-target',
  'The document declares "0.1" and has a member 0.2 added, and the target "0.1.0" names no draft: the document is '
  'checked first, and only its FS-SCH-001 is reported (20.2.3).',
  ['20.2.1', '20.2.3'], house(program={'items': {}}), '0.1.0', 'refused', SCH)
t('targets', '0.1-to-0.2',
  'A 0.1 document migrated to 0.2, a draft between its own and this one: the step from 0.1 to 0.2 alone (20.1.3).',
  ['20.1.3', '20.4.1'], house(), '0.2')

# ============================================================================= the step from 0.1 to 0.2 (20.4)

t('step-0.1-0.2', 'version-only',
  'A 0.1 house with no extension data: the step makes it declare "0.2" and changes nothing else - no record, no '
  'extras (20.4.1, 20.3.2). A reader of 0.2 reads both alike (20.6.1).',
  ['20.4.1', '20.3.2', '20.1.4', '20.6.1'], house(), '0.2')
t('step-0.1-0.2', 'opaque-collections-moved',
  'In a 0.1 document FS_furniture\'s top-level "collections" is opaque data that would be malformed in 0.2 (Core '
  'model/066). The step moves it into the record (20.4.1, 20.3.1): the migration is valid under 0.2, SOFA is no '
  'element of it, and nothing is derived from it, as in the document (20.6.1). FS_furniture stays declared, its data {}.',
  ['20.4.1', '20.3.1', '20.6.1', '1.2.6'],
  {**house(), 'extensionsUsed': {'FS_furniture': '0.1'}, 'extensions': {'FS_furniture': {'collections': OPAQUE}}},
  '0.2', moved={'0.1': ['/extensions/FS_furniture/collections']})
t('step-0.1-0.2', 'well-formed-collections-moved-too',
  'A 0.1 document whose FS_electrical data holds an outlet shaped like a 0.2 extension element. In 0.1 it is still '
  'opaque, so the step moves it rather than make it an element: the migration derives no fallback, placement or '
  'clearance, as the document does not (20.4.1, 20.6.1). Ops 0.3 ids/020 shows the other edit - declaring "0.2" by '
  'setProperty, which turns it into one.',
  ['20.4.1', '20.6.1'],
  with_elements(house(), {'X4': outlet()}, ext='FS_electrical', coll='devices', version='0.1.0'),
  '0.2', moved={'0.1': ['/extensions/FS_electrical/collections']})
t('step-0.1-0.2', 'other-extension-data-kept',
  'FS_furniture\'s data has "style" beside "collections", and EXT_acoustics\'s has no "collections" at all: the step '
  'moves the one member and leaves "style" and EXT_acoustics\'s data exactly as they were (20.4.1, 20.1.4).',
  ['20.4.1', '20.1.4'],
  {**house(), 'extensionsUsed': {'FS_furniture': '0.1', 'EXT_acoustics': '1.0'},
   'extensions': {'FS_furniture': {'style': 'mid-century', 'collections': {'pieces': {}}},
                  'EXT_acoustics': {'rating': 52, 'bands': [125, 250, 500.5]}}},
  '0.2', moved={'0.1': ['/extensions/FS_furniture/collections']})
t('step-0.1-0.2', 'several-extensions-sorted',
  'Three extensions have a "collections" member, declared out of order; the record lists the three moves sorted by '
  'pointer (20.3.1). A "collections" whose value is not an object is moved too: it is the member that is moved, '
  'whatever its value (20.4.1).',
  ['20.4.1', '20.3.1'],
  {**house(), 'extensionsUsed': {'EXT_zeta': '1.0', 'EXT_Beta': '1.0', 'EXT_alpha': '1.0'},
   'extensions': {'EXT_zeta': {'collections': 3}, 'EXT_Beta': {'collections': {'a': {}}},
                  'EXT_alpha': {'collections': None}}},
  '0.2', moved={'0.1': ['/extensions/EXT_Beta/collections', '/extensions/EXT_alpha/collections',
                        '/extensions/EXT_zeta/collections']})
t('step-0.1-0.2', 'not-an-object-not-moved',
  'Extension data that is an array, or a string, has no members: nothing is moved, and the step only changes the '
  'version (20.4.1, 20.3.2).',
  ['20.4.1', '20.3.2'],
  {**house(), 'extensionsUsed': {'EXT_a': '1.0', 'EXT_b': '1.0'},
   'extensions': {'EXT_a': [{'collections': {}}], 'EXT_b': 'collections'}},
  '0.2')
t('step-0.1-0.2', 'element-extension-data-not-moved',
  'A room\'s own extension data has a "collections" member: core never looks for collections in extension data on an '
  'element (12.5), so the step leaves it where it is (20.4.1).',
  ['20.4.1'],
  (lambda d: (d['rooms']['R1'].update(extensions={'EXT_a': {'collections': {'x': {}}}}), d)[1])(
      {**house(), 'extensionsUsed': {'EXT_a': '1.0'}}),
  '0.2')

# ============================================================================= the step from 0.2 to 0.3 (20.5)

t('step-0.2-0.3', 'version-only',
  'A 0.2 house with a program, a brief and an outlet on W2 with no "option": the step makes it declare "0.3" and '
  'changes nothing else (20.5.1, 20.3.2). A reader of 0.3 derives the outlet\'s fallback and placement, the program '
  'and the room\'s floor and ceiling alike for both (20.6.1).',
  ['20.5.1', '20.3.2', '20.1.4', '20.6.1'],
  (lambda d: (d['rooms']['R1'].update(brief='LIV', function='living'), d)[1])(
      {**with_elements(house('0.2'), {'X4': outlet()}, ext='FS_electrical', coll='devices', version='0.1.0'),
       'program': {'items': {'LIV': {'function': 'living'}}}}),
  '0.3')
t('step-0.2-0.3', 'extension-element-option-moved',
  'In a 0.2 document an extension element\'s "option" is the extension\'s own member, and a reader of 0.3 reads it as '
  'absent (1.2.6): the document is valid, with no option "deluxe" anywhere. The step moves it (20.5.1), so that the '
  'migration is valid under 0.3 too, and reads the same (20.6.1).',
  ['20.5.1', '20.3.1', '20.6.1', '1.2.6'],
  with_elements(house('0.2'), {'X4': outlet(option='deluxe')}, ext='FS_electrical', coll='devices', version='0.1.0'),
  '0.3', moved={'0.2': ['/extensions/FS_electrical/collections/devices/X4/option']})
t('step-0.2-0.3', 'options-moved-sorted',
  'Three extension elements in two collections of two extensions have an "option" - one of them a number, which only '
  'the extension constrains in 0.2 - and one has none. The record lists the three moves sorted by pointer (20.3.1, '
  '20.5.1).',
  ['20.5.1', '20.3.1'],
  (lambda d: (d['extensions'].update(FS_furniture={'collections': {
      'pieces': {'P2': element(host=free(1000 * MM, 1000 * MM), option=2),
                 'P1': element(host=free(2500 * MM, 1000 * MM))}}}),
              d['extensionsUsed'].update(FS_furniture='0.1.0'), d)[2])(
      with_elements(house('0.2'), {'X5': outlet(2000 * MM, option='B'), 'X4': outlet(option='A')},
                    ext='FS_electrical', coll='devices', version='0.1.0')),
  '0.3', moved={'0.2': ['/extensions/FS_electrical/collections/devices/X4/option',
                        '/extensions/FS_electrical/collections/devices/X5/option',
                        '/extensions/FS_furniture/collections/pieces/P2/option']})

# ============================================================================= composition (20.1.3)

t('composition', '0.1-to-0.3',
  'A 0.1 document with opaque collections, migrated to 0.3: the step from 0.1 to 0.2 moves them, and the step from '
  '0.2 to 0.3 then finds no extension element and moves nothing - one record (20.1.3, 20.3.2).',
  ['20.1.3', '20.4.1', '20.5.1', '20.3.2', '20.6.1'],
  {**house(), 'extensionsUsed': {'FS_furniture': '0.1'}, 'extensions': {'FS_furniture': {'collections': OPAQUE}}},
  '0.3', moved={'0.1': ['/extensions/FS_furniture/collections']})
t('composition', '0.1-to-0.3-version-only',
  'A 0.1 house migrated to 0.3 declares "0.3" and is otherwise unchanged; a reader of 0.3 derives its floors, '
  'ceilings, circulation and finishes alike for both (20.1.3, 20.6.1).',
  ['20.1.3', '20.6.1'], house(), '0.3')
t('composition', 'migrated-twice-keeps-both-records',
  'The 0.2 migration of a 0.1 document - its record already in extras - with an outlet added since that has an '
  '"option" of its own. Migrated to 0.3, its second record is appended after the first (20.3.1, 20.1.3).',
  ['20.3.1', '20.1.3'],
  (lambda d: (d['extras'].update({RECORD: [{'from': '0.1', 'to': '0.2', 'moved': [
      {'pointer': '/extensions/FS_electrical/collections', 'value': {'old': {}}}]}]}), d)[1])(
      {**with_elements(house('0.2'), {'X4': outlet(option='deluxe')}, ext='FS_electrical', coll='devices',
                       version='0.1.0'), 'extras': {}}),
  '0.3', moved={'0.2': ['/extensions/FS_electrical/collections/devices/X4/option']})

# ============================================================================= the record (20.3)

t('record', 'extras-kept',
  'The document\'s extras hold a viewer\'s camera. The step adds its record beside it and leaves the camera exactly as '
  'it was (20.3.1, 20.1.4); nothing is derived from either (20.6.1).',
  ['20.3.1', '20.1.4', '20.6.1'],
  {**house(), 'extras': {'camera': {'position': [1.5, 2.25, 10]}}, 'extensionsUsed': {'FS_furniture': '0.1'},
   'extensions': {'FS_furniture': {'collections': OPAQUE}}},
  '0.2', moved={'0.1': ['/extensions/FS_furniture/collections']})
t('record', 'record-not-an-array',
  'The document\'s extras have a member "floorspec:migration" that is a string, and the step has something to move: '
  'there is no record to append to, so the migrator refuses it with FS-MIG-002 (20.3.3).',
  ['20.3.3'],
  {**house(), 'extras': {RECORD: 'done'}, 'extensionsUsed': {'FS_furniture': '0.1'},
   'extensions': {'FS_furniture': {'collections': OPAQUE}}},
  '0.3', 'refused', [('FS-MIG-002', [])])
t('record', 'record-not-an-array-nothing-moved',
  'The same extras, but no step moves anything: nothing is recorded, so the member is no obstacle, and it is kept '
  'as it was (20.3.2, 20.3.3).',
  ['20.3.2', '20.3.3'], {**house(), 'extras': {RECORD: 'done'}}, '0.3')
t('record', 'record-appended',
  'The document\'s "floorspec:migration" is an array holding something this specification did not write. The step '
  'appends its record after it, and does not judge what was there (20.3.1).',
  ['20.3.1'],
  {**house(), 'extras': {RECORD: [{'note': 'imported'}]}, 'extensionsUsed': {'FS_furniture': '0.1'},
   'extensions': {'FS_furniture': {'collections': OPAQUE}}},
  '0.2', moved={'0.1': ['/extensions/FS_furniture/collections']})
# ============================================================================= examples

t('examples', 'three-room-house-0.1-to-0.3',
  'The Phase 1 exit demo as Core 0.1 published it (core/0.1/examples/001-three-room-house), migrated to 0.3: it '
  'declares "0.3" and is otherwise byte for byte the document, members sorted; a reader of 0.3 reads both alike '
  '(20.1.3, 20.6.1).',
  ['20.1.3', '20.6.1'], None, '0.3', raw=published('core/0.1/examples/001-three-room-house'))
t('examples', 'three-room-house-0.2-to-0.3',
  'The same house as Core 0.2 published it (core/0.2/examples/001-three-room-house), migrated to 0.3 (20.5.1, 20.6.1).',
  ['20.5.1', '20.6.1'], None, '0.3', raw=published('core/0.2/examples/001-three-room-house'))


# ============================================================================= writing

def write_all(prune=False):
    counters, failures, seen = {}, 0, set()
    for tc in TESTS:
        g = tc['group']
        counters[g] = counters.get(g, 0) + 1
        name = f"{counters[g]:03d}-{tc['slug']}"
        d = os.path.join(SUITE, g, name)
        seen.add(d)
        os.makedirs(d, exist_ok=True)
        data = tc['raw'] if tc['raw'] is not None else (fmt(tc['inp']) + '\n').encode('utf-8')
        with open(os.path.join(d, 'input.json'), 'wb') as f:
            f.write(data)
        with open(os.path.join(d, 'test.json'), 'w') as f:
            f.write(json.dumps({'description': tc['description'], 'covers': tc['covers']}, indent=2, ensure_ascii=False) + '\n')
        with open(os.path.join(d, 'request.json'), 'w') as f:
            f.write(fmt({'to': tc['to']}) + '\n')
        r = migrate(data, tc['to'])
        problems = []
        if r['status'] != tc['status'] or r['diagnostics'] != tc['diags']:
            problems.append(f'hand {tc["status"]} {json.dumps(tc["diags"])}\n  oracle {r["status"]} {json.dumps(r["diagnostics"])}')
        validation = None
        if tc['status'] == 'migrated':
            hand = tc['validation']
            valid = tc['valid'] if tc['valid'] is not None else not any(x['severity'] == 'error' for x in hand)
            validation = {'valid': valid, 'diagnostics': hand}
            if r['status'] == 'migrated':
                oracle, _ = reading(data, tc['to'])
                if oracle != validation:
                    problems.append(f'validation: hand {json.dumps(validation)}\n  oracle {json.dumps(oracle)}')
                records = r['document'].get('extras', {}).get(RECORD, [])
                before = json.loads(data).get('extras', {}).get(RECORD, [])
                new = records[len(before):] if isinstance(before, list) else []
                got = {rec['from']: [m['pointer'] for m in rec['moved']] for rec in new}
                if got != (tc['moved'] or {}):
                    problems.append(f'moved: hand {json.dumps(tc["moved"] or {})}\n  oracle {json.dumps(got)}')
        if problems:
            failures += 1
            print(f'MISMATCH {g}/{name}\n  ' + '\n  '.join(problems))
        with open(os.path.join(d, 'expected.json'), 'w') as f:
            f.write(expected_text(tc['status'], tc['diags'], r.get('hash') if r['status'] == 'migrated' else None,
                                  validation))
        op = os.path.join(d, 'output.json')
        if r['status'] == 'migrated':
            with open(op, 'wb') as f:
                f.write(r['bytes'])
        elif os.path.exists(op):
            os.remove(op)
    if prune and os.path.isdir(SUITE):
        for g in os.listdir(SUITE):
            gp = os.path.join(SUITE, g)
            for n in (os.listdir(gp) if os.path.isdir(gp) else []):
                if os.path.join(gp, n) not in seen:
                    print('removing', os.path.join(gp, n))
                    shutil.rmtree(os.path.join(gp, n))
    print(f'{len(TESTS)} tests, {failures} mismatches')
    return failures


if __name__ == '__main__':
    sys.exit(1 if write_all('--prune' in sys.argv[1:]) else 0)

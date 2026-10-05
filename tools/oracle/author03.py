"""The conformance suite of Floorspec Core 0.3, as the script that writes it.

    python3.13 -m tools.oracle.author03            rewrite every test from its declaration below
    python3.13 -m tools.oracle.author03 --prune    ...and delete test directories no longer declared

The suite is the Core 0.2 suite, re-targeted to 0.3 - every 0.2 test, in the same group under the
same number, its document declaring "0.3" where it declared "0.2" (a document that declares "0.1"
stays one: it shows a 0.3 reader reading 0.1, 1.2.6), and covering the 0.3 IDs of the statements
0.3 retired - followed by the tests of what 0.3 adds: a door or window type's operation, and the
clear opening of types and openings. Every expected diagnostic is written by hand and
cross-checked against the oracle, read as a Core 0.3 reader (validate.READER_03); geometry, hashes
and canonical forms come from the oracle. Afterwards, `python3.13 -m tools.oracle.regenerate`
re-verifies the suite from the files alone. Add new tests at the end of their group's section.
"""
import copy
import os
import re
import sys

import tools.oracle.author02 as v02                    # declares the 0.2 suite: v02.BASE + v02.NEW
from tools.oracle.author import room_doc as room_doc_01
from tools.oracle.author_lib import IN, MM, REPO, TESTS, t, write_all
from tools.oracle.validate import READER_03

SUITE03 = os.path.join(REPO, 'conformance', 'core', '0.3')
SCH = [('FS-SCH-001', [])]

# ============================================================================= the 0.2 suite, re-targeted

RETIRED = {'FS-CORE-1.2.3': 'FS-CORE-1.2.5', 'FS-CORE-1.2.4': 'FS-CORE-1.2.6'}
VERSION_TESTS = {
    # slug: (new floorspec value, new description)
    'version-is-a-number': (0.3, '"floorspec": 0.3 is a number, not the string "0.3". FS-DOC-001 applies only to a '
                                 'string naming another version, so this is a schema error.'),
    'version-with-patch': ('0.3.0', '"0.3.0" is not "0.3": patch releases are not declared. A reader that implements '
                                    '0.1, 0.2 and 0.3 rejects it with FS-DOC-001.'),
    'unknown-version': ('0.4', 'A reader that implements 0.1, 0.2 and 0.3 rejects a document declaring 0.4 with '
                               'FS-DOC-001, whatever else the document contains.'),
    'document-error-stops-schema': ('0.4', None),
}
SLUGS = {
    'collections-checked-in-0.2': 'collections-checked-in-0.3',
    'version-0.2-with-everything': 'version-0.3-with-0.2-members',
}
DESCRIPTIONS = {
    # slug: [(text of the 0.2 description, its 0.3 wording)] where the words name a draft
    'read-0.1-document': [('a reader of 0.2', 'a reader of 0.3'),
                          ('hosts or clearances', 'hosts, clearances or clear openings')],
    '0.1-document-with-program': [('which 0.2 adds', 'which 0.2 added')],
    '0.1-document-with-brief': [('"brief" is a 0.2 member', '"brief" is a member 0.2 added')],
    '0.1-document-with-declaration-object': [('which 0.2 adds', 'which 0.2 added')],
    '0.1-document-with-clearances': [('which 0.2 adds', 'which 0.2 added')],
    '0.1-collections-are-opaque': [('malformed in 0.2', 'malformed in 0.2 and 0.3')],
    'collections-checked-in-0.2': [('in a 0.2 document', 'in a 0.3 document')],
    'version-0.2-with-everything': [('A 0.2 document using every member 0.2 adds', 'A 0.3 document using every member 0.2 added')],
    'read-0.1-document-circulation': [('a reader of 0.2: circulation needs no member 0.2 adds',
                                       'a reader of 0.3: circulation needs no member 0.2 or 0.3 adds')],
    'known-extensions-and-a-0.1-document': [('a 0.2 reader applies 12.3 to it as to any document (1.2.4)',
                                             'a 0.3 reader applies 12.3 to it as to any document (1.2.6)')],
}
_RAW_VERSION = re.compile(rb'("floorspec"\s*:\s*)"0\.2"')


def retarget(tc):
    tc = copy.deepcopy(tc)
    slug = tc['slug']
    tc['covers'] = [RETIRED.get(c, c) for c in tc['covers']]
    for old, new in DESCRIPTIONS.get(slug, []):
        assert old in tc['description'], (slug, old)
        tc['description'] = tc['description'].replace(old, new)
    if slug in VERSION_TESTS:
        value, description = VERSION_TESTS[slug]
        tc['inp']['floorspec'] = value
        tc['description'] = description or tc['description']
    elif isinstance(tc['inp'], dict) and tc['inp'].get('floorspec') == '0.2':
        tc['inp']['floorspec'] = '0.3'
    if tc['raw'] is not None:
        tc['raw'] = _RAW_VERSION.sub(rb'\1"0.3"', tc['raw'])
    tc['slug'] = SLUGS.get(slug, slug)
    return tc


SUITE02 = v02.BASE + v02.NEW
BASE = [retarget(tc) for tc in SUITE02]
del TESTS[:]


def as_02(slug):
    """The input of a 0.2 test exactly as the 0.2 suite has it."""
    return copy.deepcopy(next(tc for tc in SUITE02 if tc['slug'] == slug)['inp'])


# ============================================================================= helpers

def v3(d):
    d = copy.deepcopy(d)
    d['floorspec'] = '0.3'
    return d


def room_doc(**extra):
    return v3(room_doc_01(**extra))


def odoc(openings, types):
    """The 4 m x 3 m room (W1 west, W2 north, W3 east, W4 south, each 4 m or 3 m long; 2700 mm high)
    with these openings and these door and window types, declaring 0.3."""
    d = room_doc()
    d['types'] = {'WT': d['types']['WT'], **copy.deepcopy(types)}
    d['openings'] = copy.deepcopy(openings)
    return d


def co(width, height, area=None):
    c = {'width': width, 'height': height}
    if area is not None:
        c['area'] = area
    return c


# A 36-inch door: 900 mm x 2100 mm rough, 32 inches by 80 inches clear (813 mm x 2032 mm).
DOOR_CLEAR = co(32 * IN, 80 * IN)
DOOR = {'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM, 'operation': 'swing', 'clearOpening': DOOR_CLEAR}
# A casement window: 1200 mm square, sill 900 mm; 560 mm x 1050 mm clear, 0.55 m2 of it.
M2 = 1280 * 1280 * 1000 * 1000
WIN_CLEAR = co(560 * MM, 1050 * MM, 55 * M2 // 100)
WINDOW = {'kind': 'windowType', 'width': 1200 * MM, 'height': 1200 * MM, 'sill': 900 * MM, 'operation': 'casement',
          'clearOpening': WIN_CLEAR}
D1 = {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'D'}             # on the south wall: an entry
G1 = {'wall': 'W1', 'offset': 900 * MM, 'fill': 'G'}              # on the west wall
DOOR_OPS = ['swing', 'doubleSwing', 'doubleActing', 'bypassSlide', 'pocket', 'surfaceSlide', 'bifold', 'overhead', 'cased']
WINDOW_OPS = ['fixed', 'casement', 'awning', 'hopper', 'singleHung', 'doubleHung', 'horizontalSlider', 'tiltTurn', 'pivot']


def unused(*ids):
    return [('FS-LINT-006', [i]) for i in ids]


def n(*args, **kw):
    """Declares a new 0.3 test."""
    t(*args, **kw)


# =================================================================================== model (0.3)
n('model', 'read-0.2-document', 'The 0.2 suite\'s document using every member 0.2 adds (model/068 of '
  'conformance/core/0.2), exactly as it is there, declaring "0.2", read by a reader of 0.3: valid, with the same '
  'diagnostics, derived values, hash and canonical form as in the 0.2 suite, and no clear opening derived.',
  ['1.2.2', '1.2.6', '9.2.1', '9.3.1'], as_02('version-0.2-with-everything'), registry=None)
d = copy.deepcopy(as_02('version-0.2-with-everything'))
d['types']['D']['clearOpening'] = DOOR_CLEAR
n('model', '0.2-document-with-clear-opening', 'A document that declares "0.2" and whose door type has a clear '
  'opening, which 0.3 adds: it is checked against Core 0.2\'s schema, which has no "clearOpening" member.',
  ['1.2.6'], d, SCH)
d = copy.deepcopy(as_02('version-0.2-with-everything'))
d['types']['D']['operation'] = 'swing'
n('model', '0.2-document-with-operation', 'A 0.2 document whose door type declares its operation: "operation" is a '
  'member 0.3 adds.', ['1.2.6'], d, SCH)
d = copy.deepcopy(as_02('version-0.2-with-everything'))
d['openings']['O1']['clearOpening'] = DOOR_CLEAR
n('model', '0.2-document-with-opening-clear-opening', 'A 0.2 document whose opening overrides a clear opening, '
  'which 0.3 adds.', ['1.2.6'], d, SCH)
d = room_doc_01()
d['types']['D'] = {'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM, 'clearOpening': DOOR_CLEAR}
d['openings'] = {'O1': D1}
n('model', '0.1-document-with-clear-opening', 'A 0.1 document whose door type has a clear opening: Core 0.1\'s '
  'schema applies to it, and has no such member.', ['1.2.6'], d, SCH)
n('model', 'version-0.3-with-everything', 'A 0.3 document using every member 0.3 adds - a door type and a window '
  'type that declare their operation and clear opening, and a window whose own clear opening overrides its '
  'type\'s - valid, with each opening\'s clear opening derived exactly as declared. None of them has a constant '
  'default, so the canonical form keeps them all.', ['1.2.5', '7.4.2', '8.2.1', '9.2.1'],
  odoc({'O1': D1, 'O2': G1, 'O3': {**G1, 'wall': 'W3', 'clearOpening': co(500 * MM, 1000 * MM, 45 * M2 // 100)}},
       {'D': DOOR, 'G': WINDOW}))

# =================================================================================== types (0.3)
n('types', 'door-operations', 'A door type of every door operation of 8.4, none of them used by an opening: valid, '
  'with an unused-type lint for each.', ['8.4.2', '8.1.1'],
  odoc({}, {f'D{i}': {'kind': 'doorType', 'operation': op} for i, op in enumerate(DOOR_OPS, 1)}),
  unused(*(f'D{i}' for i in range(1, len(DOOR_OPS) + 1))))
n('types', 'window-operations', 'A window type of every window operation of 8.4, none of them used: valid.',
  ['8.4.2', '8.1.1'],
  odoc({}, {f'G{i}': {'kind': 'windowType', 'operation': op} for i, op in enumerate(WINDOW_OPS, 1)}),
  unused(*(f'G{i}' for i in range(1, len(WINDOW_OPS) + 1))))
n('types', 'door-with-window-operation', 'A door type whose operation is "casement", a window operation.',
  ['8.4.2'], odoc({'O1': D1}, {'D': {**DOOR, 'operation': 'casement'}}), SCH)
n('types', 'window-with-door-operation', 'A window type whose operation is "swing", a door operation.',
  ['8.4.2'], odoc({'O2': G1}, {'G': {**WINDOW, 'operation': 'swing'}}), SCH)
n('types', 'operation-unknown', 'An operation that neither list has: "revolving".', ['8.4.2'],
  odoc({'O1': D1}, {'D': {**DOOR, 'operation': 'revolving'}}), SCH)
n('types', 'operation-case-matters', '"Swing" is not "swing": operations are compared exactly.', ['8.4.2'],
  odoc({'O1': D1}, {'D': {**DOOR, 'operation': 'Swing'}}), SCH)
n('types', 'clear-opening-zero-width', 'A clear opening 0 wide.', ['8.4.3'],
  odoc({'O1': D1}, {'D': {**DOOR, 'clearOpening': co(0, 80 * IN)}}), SCH)
n('types', 'clear-opening-zero-height', 'A clear opening 0 high.', ['8.4.3'],
  odoc({'O2': G1}, {'G': {**WINDOW, 'clearOpening': co(560 * MM, 0, 1)}}), SCH)
n('types', 'clear-opening-without-height', 'A clear opening with a width and no height: both are always present.',
  ['8.4.3'], odoc({'O1': D1}, {'D': {**DOOR, 'clearOpening': {'width': 32 * IN}}}), SCH)
n('types', 'clear-opening-zero-area', 'A window\'s clear area of 0.', ['8.4.3'],
  odoc({'O2': G1}, {'G': {**WINDOW, 'clearOpening': co(560 * MM, 1050 * MM, 0)}}), SCH)
n('types', 'clear-opening-area-with-fraction', 'A clear area written with a fraction is not an integer.', ['8.4.3', '2.1.1'],
  odoc({'O2': G1}, {'G': {**WINDOW, 'clearOpening': co(560 * MM, 1050 * MM, 1000.0)}}), SCH)
n('types', 'clear-opening-area-too-large', 'A clear area of 2^53 square base units, one more than an area may be.',
  ['8.4.3'], odoc({'O2': G1}, {'G': {**WINDOW, 'clearOpening': co(560 * MM, 1050 * MM, 2 ** 53)}}), SCH)
n('types', 'door-clear-opening-with-area', 'A door type\'s clear opening has no area: an area is a window\'s.',
  ['8.4.3'], odoc({'O1': D1}, {'D': {**DOOR, 'clearOpening': co(32 * IN, 80 * IN, 32 * IN * 80 * IN)}}), SCH)
n('types', 'clear-opening-unknown-member', 'A clear opening has only width, height and area: "depth" is unknown.',
  ['8.4.3', '1.4.3'], odoc({'O1': D1}, {'D': {**DOOR, 'clearOpening': {**DOOR_CLEAR, 'depth': 100 * MM}}}), SCH)
w, h = WIN_CLEAR['width'], WIN_CLEAR['height']
n('types', 'clear-area-equals-width-times-height', 'A window\'s clear area exactly its clear width times its clear '
  'height, 963379200000: not more, so valid.', ['8.4.4'],
  odoc({'O2': G1}, {'G': {**WINDOW, 'clearOpening': co(w, h, w * h)}}))
n('types', 'clear-area-exceeds-width-times-height', 'One square base unit more than the clear width times the clear '
  'height: FS-INV-306 names the type.', ['8.4.4', '10.2.1'],
  odoc({'O2': G1}, {'G': {**WINDOW, 'clearOpening': co(w, h, w * h + 1)}}), [('FS-INV-306', ['G'])])
n('types', 'clear-opening-as-wide-as-the-type', 'A door type whose clear opening is exactly as wide and as high as '
  'the type itself: valid.', ['8.4.5', '7.2.2'],
  odoc({'O1': D1}, {'D': {**DOOR, 'clearOpening': co(900 * MM, 2100 * MM)}}))
n('types', 'clear-opening-wider-than-the-type', 'A door type 900 mm wide whose clear opening is 1 base unit wider: '
  'FS-INV-307 names the type, and FS-INV-305 the opening it fills, which is as wide as the type.',
  ['8.4.5', '7.2.2', '10.2.1'], odoc({'O1': D1}, {'D': {**DOOR, 'clearOpening': co(900 * MM + 1, 80 * IN)}}),
  [('FS-INV-305', ['O1']), ('FS-INV-307', ['D'])])
n('types', 'clear-opening-taller-than-the-type', 'A window type 1200 mm high whose clear opening is 1201 mm high: '
  'FS-INV-307 for the type; the window that fills it is 1200 mm high too, so FS-INV-305.',
  ['8.4.5', '7.2.2', '10.2.1'], odoc({'O2': G1}, {'G': {**WINDOW, 'clearOpening': co(560 * MM, 1201 * MM)}}),
  [('FS-INV-305', ['O2']), ('FS-INV-307', ['G'])])
n('types', 'unused-type-clear-opening-checked', 'A window type no opening uses, whose clear opening is wider than it '
  'and has more area than its width times its height: the type invariants hold for every type, used or not.',
  ['8.4.4', '8.4.5', '10.3.1'],
  odoc({}, {'G': {**WINDOW, 'clearOpening': co(1300 * MM, 1000 * MM, 1300 * 1000 * 1280 * 1280 + 1)}}),
  [('FS-INV-306', ['G']), ('FS-INV-307', ['G'])])
n('types', 'clear-opening-on-a-type-without-size', 'A door type with a clear opening and no width or height: there '
  'is nothing to compare it with on the type, so it is valid; the opening it fills states its own 1000 mm by '
  '2200 mm, and the clear opening fits that.', ['8.4.5', '7.2.2'],
  odoc({'O1': {**D1, 'width': 1000 * MM, 'height': 2200 * MM}},
       {'D': {'kind': 'doorType', 'operation': 'swing', 'clearOpening': co(950 * MM, 2150 * MM)}}))
n('types', 'pair-of-doors', 'A pair of doors, 1800 mm wide: its clear opening is the whole pair\'s, both leaves open. '
  'Its "swing" says which side both leaves open into; its "hinge" means nothing for a pair, and is the default, '
  'which the canonical form omits.', ['8.4.2', '7.4.2', '9.2.1'],
  odoc({'O1': {**D1, 'swing': 'left', 'hinge': 'start'}},
       {'D': {'kind': 'doorType', 'width': 1800 * MM, 'height': 2100 * MM, 'operation': 'doubleSwing',
              'clearOpening': co(1650 * MM, 2032 * MM)}}))

# =================================================================================== openings (0.3)
n('openings', 'clear-opening-from-type', 'A door filled by a type with a clear opening has that clear opening, '
  'derived exactly as the type declares it: 32 by 80 inches, 1040384 by 2600960 base units, and no area.',
  ['7.4.2', '8.2.1'], odoc({'O1': D1}, {'D': DOOR}))
n('openings', 'clear-opening-override', 'A window whose own clear opening - 500 mm by 1000 mm, no area - overrides '
  'its type\'s, which has an area. The override is resolved whole (8.2): the derived clear opening has no area, and '
  'the type\'s 0.55 m2 is not its.', ['7.4.2', '8.2.1', '7.2.2'],
  odoc({'O2': {**G1, 'clearOpening': co(500 * MM, 1000 * MM)}}, {'G': WINDOW}))
n('openings', 'clear-area-not-declared', 'A window type whose clear opening declares no area: the derived clear '
  'opening has a width and a height and no area - never 560 mm times 1050 mm.', ['7.4.2'],
  odoc({'O2': G1}, {'G': {**WINDOW, 'clearOpening': co(560 * MM, 1050 * MM)}}))
n('openings', 'no-clear-opening', 'A door type that declares an operation but no clear opening: nothing is derived '
  'for the door\'s clear opening.', ['7.4.2'],
  odoc({'O1': D1}, {'D': {'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM, 'operation': 'pocket'}}))
n('openings', 'empty-opening-clear-opening', 'An empty opening that states its own clear opening - a cased opening '
  'inside its trim, 1450 mm by 2350 mm in a 1500 mm by 2400 mm hole: valid, and derived as stated.',
  ['7.4.2', '7.2.2', '7.1.3'],
  odoc({'O1': {'wall': 'W4', 'offset': 500 * MM, 'width': 1500 * MM, 'height': 2400 * MM,
               'clearOpening': co(1450 * MM, 2350 * MM)}}, {}))
n('openings', 'empty-opening-clear-area', 'An empty opening whose own clear opening has an area: only a window has '
  'one, so FS-INV-308 names the opening.', ['7.1.3', '10.2.1'],
  odoc({'O1': {'wall': 'W4', 'offset': 500 * MM, 'width': 1500 * MM, 'height': 2400 * MM,
               'clearOpening': co(1450 * MM, 2350 * MM, M2)}}, {}), [('FS-INV-308', ['O1'])])
n('openings', 'door-clear-area', 'A door whose own clear opening has an area: FS-INV-308.', ['7.1.3', '10.2.1'],
  odoc({'O1': {**D1, 'clearOpening': co(32 * IN, 80 * IN, M2)}}, {'D': DOOR}), [('FS-INV-308', ['O1'])])
n('openings', 'window-clear-area', 'A window whose own clear opening has an area: valid, and derived with it.',
  ['7.1.3', '7.4.2'], odoc({'O2': {**G1, 'clearOpening': co(500 * MM, 1000 * MM, M2 // 4)}}, {'G': WINDOW}))
n('openings', 'own-clear-area-too-large', 'A window whose own clear area is more than its own clear width times '
  'height: FS-INV-306 names the opening.', ['8.4.4', '10.2.1'],
  odoc({'O2': {**G1, 'clearOpening': co(500 * MM, 1000 * MM, M2 // 2 + 1)}}, {'G': WINDOW}),
  [('FS-INV-306', ['O2'])])
n('openings', 'narrower-opening-keeps-type-clear', 'A door that overrides its width to 800 mm but not its clear '
  'opening keeps its type\'s 32-inch (812.8 mm) clear width, which no longer fits: FS-INV-305.',
  ['7.2.2', '8.2.1', '10.2.1'], odoc({'O1': {**D1, 'width': 800 * MM}}, {'D': DOOR}), [('FS-INV-305', ['O1'])])
n('openings', 'narrower-opening-own-clear', 'The same 800 mm door with its own 30-inch clear opening: it fits.',
  ['7.2.2', '7.4.2', '8.2.1'], odoc({'O1': {**D1, 'width': 800 * MM, 'clearOpening': co(30 * IN, 80 * IN)}}, {'D': DOOR}))
n('openings', 'clear-opening-taller-than-opening', 'A window whose own clear opening is 1 base unit taller than the '
  'window: FS-INV-305.', ['7.2.2', '10.2.1'],
  odoc({'O2': {**G1, 'clearOpening': co(500 * MM, 1200 * MM + 1)}}, {'G': WINDOW}), [('FS-INV-305', ['O2'])])
n('openings', 'clear-opening-fits-exactly', 'A window whose own clear opening is exactly the window, 1200 mm by '
  '1200 mm: valid.', ['7.2.2'], odoc({'O2': {**G1, 'clearOpening': co(1200 * MM, 1200 * MM)}}, {'G': WINDOW}))
n('openings', 'clear-opening-and-unresolved-height', 'An empty opening with no height and a clear opening taller than '
  'anything: FS-INV-301, and FS-INV-305 is not evaluated for an opening that has it.', ['10.3.1', '7.2.1'],
  odoc({'O1': {'wall': 'W4', 'offset': 500 * MM, 'width': 1500 * MM, 'clearOpening': co(1600 * MM, 9000 * MM)}}, {}),
  [('FS-INV-301', ['O1'])])
d = odoc({'O1': {**D1, 'width': 800 * MM},
          'O2': {**G1, 'clearOpening': co(500 * MM, 1000 * MM, M2)},
          'O3': {'wall': 'W2', 'offset': 500 * MM, 'width': 1500 * MM, 'height': 2400 * MM,
                 'clearOpening': co(1450 * MM, 2350 * MM, M2)}},
         {'D': {**DOOR, 'clearOpening': co(32 * IN, 2200 * MM)}, 'G': WINDOW})
n('openings', 'clear-opening-invariants-together', 'A door narrower than its type\'s clear opening (FS-INV-305), whose '
  'type\'s clear opening is taller than the type (FS-INV-307); a window whose own clear area is more than its width '
  'times its height (FS-INV-306); and an empty opening with a clear area (FS-INV-308): each is reported, sorted by '
  'code.', ['10.2.1', '10.3.1', '7.2.2', '7.1.3', '8.4.4', '8.4.5'], d,
  [('FS-INV-305', ['O1']), ('FS-INV-306', ['O2']), ('FS-INV-307', ['D']), ('FS-INV-308', ['O3'])])

# =================================================================================== diagnostics (0.3)
d = odoc({'O1': {**D1, 'fill': 'NOPE'}}, {'D': {**DOOR, 'clearOpening': co(2 * 900 * MM, 80 * IN)}})
n('diagnostics', 'reference-error-stops-clear-opening', 'An opening filled by a type that does not exist, beside a '
  'door type whose clear opening is twice as wide as it: once a reference invariant is reported, no other is '
  'evaluated, so only FS-INV-002.', ['10.3.1'], d, [('FS-INV-002', ['O1'])])

NEW = list(TESTS)
del TESTS[:]


def main(argv) -> int:
    tests = BASE + NEW
    return 1 if write_all(prune='--prune' in argv, tests=tests, suite=SUITE03, reader=READER_03) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

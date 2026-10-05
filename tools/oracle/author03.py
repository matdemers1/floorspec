"""The conformance suite of Floorspec Core 0.3, as the script that writes it.

    python3.13 -m tools.oracle.author03            rewrite every test from its declaration below
    python3.13 -m tools.oracle.author03 --prune    ...and delete test directories no longer declared

The suite is the Core 0.2 suite, re-targeted to 0.3 - every 0.2 test, in the same group under the
same number, its document declaring "0.3" where it declared "0.2" (a document that declares "0.1"
stays one: it shows a 0.3 reader reading 0.1, 1.2.6), and covering the 0.3 IDs of the statements
0.3 retired - followed by the tests of what 0.3 adds: a door or window type's operation, the
clear opening of types and openings, and floors, ceilings and slabs (chapter 15: the group `floors`,
and surface hosts on them in `hosting`). A 0.3 reader derives floors, ceilings and slabs for every
valid document, so each re-targeted test's derived values gain those three members and are
otherwise the 0.2 suite's. Every expected diagnostic is written by hand and
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
from tools.oracle.author02 import element, surface, with_elements
from tools.oracle.author_lib import IN, MM, REPO, TESTS, J, R, W, box, level_doc, t, write_all
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
  'diagnostics, hash and canonical form as in the 0.2 suite, every value the 0.2 suite derives - the placements of '
  'its surface hosts included - and no clear opening; and, derived from the defaults, its rooms\' floors at the '
  'level\'s elevation and flat ceilings at its height.',
  ['1.2.2', '1.2.6', '9.2.1', '9.3.1', '15.1.2', '15.5.1', '15.6.1'], as_02('version-0.2-with-everything'), registry=None)
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

# =================================================================================== floors, ceilings and slabs (0.3)
# The standard room (author.py): 4 m x 3 m, 100 mm walls on their centre lines, so its room polygon runs from
# (50 mm, 50 mm) to (3950 mm, 2950 mm); level L1 at elevation 0 and 2700 mm high. CX, CY is its centre.
X, Y = 4000 * MM, 3000 * MM
CX, CY = X // 2, Y // 2


def fdoc(floor=None, ceiling=None, level=None, **room):
    """The standard room, declaring 0.3, with this floor and ceiling, and these members on L1."""
    d = room_doc()
    if floor is not None:
        d['rooms']['R1']['floor'] = floor
    if ceiling is not None:
        d['rooms']['R1']['ceiling'] = ceiling
    d['rooms']['R1'].update(room)
    d['levels']['L1'].update(level or {})
    return d


def pentagon(**room):
    """A room with a gable end: walls drawn clockwise through (0, 0), (0, 3 m), (2 m, 4 m), (4 m, 3 m) and (4 m, 0) -
    two oblique walls, so its room polygon has irrational corners, rounded."""
    js = {'J1': J(0, 0), 'J2': J(0, 3000 * MM), 'J3': J(2000 * MM, 4000 * MM), 'J4': J(4000 * MM, 3000 * MM),
          'J5': J(4000 * MM, 0)}
    ws = {'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J5'), 'W5': W('J5', 'J1')}
    return v3(level_doc(junctions=js, walls=ws, rooms={'R1': R(2000 * MM, 1500 * MM, **room)}))


def holed(**room):
    """A 6 m by 5 m room with a 1 m square chase in its middle, every wall 100 mm."""
    js, ws = box('', 0, 0, 6000 * MM, 5000 * MM)
    cj, cw = box('C', 2500 * MM, 2000 * MM, 3500 * MM, 3000 * MM)
    return v3(level_doc(junctions={**js, **cj}, walls={**ws, **cw}, rooms={'R1': R(1000 * MM, 1000 * MM, **room)}))


TRAY = {'kind': 'tray', 'border': 300 * MM, 'depth': 200 * MM}
HALF = {'rise': 6, 'run': 12}
VAULT = {'kind': 'vaulted', 'height': 3200 * MM, 'ridge': [[0, CY], [X, CY]], 'pitch': HALF}
OBLIQUE = {'kind': 'vaulted', 'height': 3500 * MM, 'ridge': [[0, 0], [3000 * MM, 1000 * MM]], 'pitch': HALF}
LIGHT = dict(size=(200 * MM, 200 * MM, 150 * MM), origin=(-100 * MM, -100 * MM, -150 * MM))     # hangs below its frame
PIECE = dict(size=(600 * MM, 600 * MM, 900 * MM), origin=(-300 * MM, -300 * MM, 0))                # stands on its frame


def lit(d, *positions, which='ceiling'):
    """d with an FS_furniture element on R1's ceiling - a light - or floor - a piece - at each position: X1, X2, ..."""
    box_ = LIGHT if which == 'ceiling' else PIECE
    return with_elements(d, {f'X{i}': element(host=surface('R1', p, which), **box_) for i, p in enumerate(positions, 1)})


n('floors', 'default-floor-and-ceiling', 'The standard room with no floor or ceiling member, on a level with no floor '
  'thickness or ceiling height: its floor is its room polygon at the level\'s elevation, 0, with no declared thickness - '
  'its bottom is its top - and its ceiling is flat at the level\'s height, 2700 mm; each box spans the room polygon, '
  '50 mm to 3950 mm by 50 mm to 2950 mm.', ['15.1.2', '15.5.1', '15.2.2'], fdoc())
n('floors', 'level-floor-thickness-and-ceiling-height', 'A level whose rooms have 300 mm floors and 2400 mm ceilings: '
  'the room\'s floor runs from -300 mm to 0, and its ceiling is flat at 2400 mm, not at the level\'s 2700 mm height.',
  ['1.8.4', '15.1.2', '15.5.1'], fdoc(level={'floorThickness': 300 * MM, 'ceilingHeight': 2400 * MM}))
n('floors', 'sunken-floor', 'A sunken living room: its floor 150 mm below the level, 250 mm thick - its own thickness '
  'overrides the level\'s 300 mm - so its top is -150 mm and its bottom -400 mm. Its ceiling stays at the level\'s 2400 mm: '
  'a ceiling\'s height is measured from the level, not from the floor.', ['15.1.2', '15.5.1'],
  fdoc({'offset': -150 * MM, 'thickness': 250 * MM}, level={'floorThickness': 300 * MM, 'ceilingHeight': 2400 * MM},
       function='living'))
n('floors', 'raised-floor', 'A floor raised 200 mm, with the level\'s 300 mm thickness: top 200 mm, bottom -100 mm.',
  ['15.1.2'], fdoc({'offset': 200 * MM}, level={'floorThickness': 300 * MM}))
n('floors', 'ceiling-height-overrides-level', 'A flat ceiling at 3000 mm in a room on a level whose ceilings are 2400 '
  'mm: the room\'s own height wins.', ['15.5.1', '15.2.2'],
  fdoc(ceiling={'kind': 'flat', 'height': 3000 * MM}, level={'ceilingHeight': 2400 * MM}))
n('floors', 'tray-ceiling', 'A tray ceiling with a 300 mm border and a 200 mm depth: the border is flat at 2700 mm and '
  'the centre - the room polygon shrunk by 300 mm, 350 mm to 3650 mm by 350 mm to 2650 mm - is raised to 2900 mm, the '
  'ceiling\'s high.', ['15.4.2', '15.5.1', '15.2.2', '15.4.1'], fdoc(ceiling=TRAY))
n('floors', 'tray-ceiling-in-a-gable-room', 'A tray ceiling in a room with two oblique walls: each moved vertex is an '
  'intersection of two moved lines, exact, rounded once - the apex moves straight down by 300 mm times the square root '
  'of 5 over 2.', ['15.4.2', '15.5.1', '15.4.1', '2.2.1'], pentagon(ceiling=TRAY))
n('floors', 'tray-ceiling-around-a-chase', 'A tray ceiling in a room with a chase in its middle: the chase\'s hole ring '
  'moves outwards by the border as the outer ring moves in - every edge moves to its left, into the room - so the '
  'centre is a ring with a hole, both rounded and listed as a room polygon is. The chase\'s inside is a face no room '
  'is anchored in.', ['15.4.2', '15.5.1', '15.4.1'],
  holed(ceiling={'kind': 'tray', 'border': 500 * MM, 'depth': 150 * MM}), [('FS-LINT-003', [])])
n('floors', 'tray-border-nearly-half', 'A border of 1449 mm in a room 2900 mm deep inside its walls: the centre is '
  '1002 mm wide and 2 mm deep, and fits.', ['15.4.1', '15.4.2'],
  fdoc(ceiling={'kind': 'tray', 'border': 1449 * MM, 'depth': 100 * MM}))
n('floors', 'tray-border-half', 'A border of 1450 mm, exactly half the room\'s depth: the centre\'s short edges have '
  'no length, so they do not run the way the room\'s do - FS-INV-703.', ['15.4.1', '10.2.1'],
  fdoc(ceiling={'kind': 'tray', 'border': 1450 * MM, 'depth': 100 * MM}), [('FS-INV-703', ['R1'])])
n('floors', 'tray-border-too-wide', 'A border of 2 m: the moved edges cross over and run backwards. FS-INV-703.',
  ['15.4.1', '10.2.1'], fdoc(ceiling={'kind': 'tray', 'border': 2000 * MM, 'depth': 100 * MM}), [('FS-INV-703', ['R1'])])
n('floors', 'tray-border-meets-the-chase', 'A 1 m border around a chase that stands 1.9 m from the room\'s walls: '
  'every edge still runs its way, but the chase\'s moved ring reaches past the outer one, so the centre is degenerate - '
  'FS-INV-703.', ['15.4.1', '10.2.1'], holed(ceiling={'kind': 'tray', 'border': 1000 * MM, 'depth': 150 * MM}),
  [('FS-INV-703', ['R1'])])
n('floors', 'vaulted-ceiling', 'A cathedral ceiling: a ridge along the room\'s centre line at 3200 mm, falling 6 in 12 '
  'to both sides. At the walls, 1450 mm from the ridge, it is 725 mm lower: its low is 2475 mm, and its high is the '
  'ridge\'s 3200 mm, since the ridge line crosses the room.', ['15.3.2', '15.5.1', '15.2.2'], fdoc(ceiling=VAULT))
n('floors', 'vaulted-ceiling-oblique-ridge', 'A vault whose ridge runs from (0, 0) to (3 m, 1 m), at 3500 mm: the '
  'distance of each corner from the ridge line is an integer over the square root of 10 square metres, so the low is '
  'rounded once from an irrational value. The ridge crosses the room, so the high is 3500 mm.',
  ['15.3.2', '15.5.1', '2.2.1'], fdoc(ceiling=OBLIQUE))
n('floors', 'vaulted-ridge-outside-the-room', 'A vault whose ridge runs 1 m south of the room, at 4000 mm: the ridge '
  'line meets no part of the room, so the high is not 4000 mm but the ceiling at the room\'s south side, 1050 mm '
  'from the ridge - 3475 mm - and the low is at its north side, 3950 mm away: 2025 mm.', ['15.3.2', '15.5.1'],
  fdoc(ceiling={'kind': 'vaulted', 'height': 4000 * MM, 'ridge': [[0, -1000 * MM], [X, -1000 * MM]], 'pitch': HALF}))
n('floors', 'shed-ceiling', 'A one-sided vault: the ridge runs east along y = 2 m at 3000 mm, and the ceiling falls 6 in '
  '12 to its right - south. As one plane it rises to the ridge\'s left: at the north side, 950 mm beyond it, the '
  'ceiling is 3475 mm - higher than the ridge - and at the south side, 1950 mm before it, 2025 mm.',
  ['15.3.2', '15.5.1'],
  fdoc(ceiling={'kind': 'vaulted', 'height': 3000 * MM, 'ridge': [[0, 2000 * MM], [X, 2000 * MM]], 'pitch': HALF,
                'slopes': 'right'}))
n('floors', 'shed-ceiling-falling-left', 'The same ridge walked west, from (4 m, 2 m) to (0, 2 m), falling to its '
  'left: south again, so the ceiling is the same plane, with the same low and high.', ['15.3.2', '15.5.1'],
  fdoc(ceiling={'kind': 'vaulted', 'height': 3000 * MM, 'ridge': [[X, 2000 * MM], [0, 2000 * MM]], 'pitch': HALF,
                'slopes': 'left'}))
n('floors', 'vault-ridge-points-coincide', 'A vault whose two ridge points are the same point: there is no ridge line. '
  'FS-INV-702 names the room; FS-INV-701 is not evaluated for it, though its 500 mm height is below its floor, raised '
  '1 m.', ['15.3.1', '10.2.1', '10.3.1'],
  fdoc({'offset': 1000 * MM}, {'kind': 'vaulted', 'height': 500 * MM, 'ridge': [[CX, CY], [CX, CY]], 'pitch': HALF}),
  [('FS-INV-702', ['R1'])])
n('floors', 'ceiling-at-the-floor', 'A floor raised 2700 mm, to the level\'s ceiling: the ceiling is not above it. '
  'FS-INV-701.', ['15.2.2', '10.2.1'], fdoc({'offset': 2700 * MM}), [('FS-INV-701', ['R1'])])
n('floors', 'ceiling-just-above-the-floor', 'A floor raised 2700 mm less one base unit: the ceiling is above it, by one '
  'base unit, and the document is valid.', ['15.2.2'], fdoc({'offset': 2700 * MM - 1}))
n('floors', 'tray-border-at-the-floor', 'A tray whose border is at 1000 mm over a floor raised 1000 mm: its raised '
  'centre is above the floor, but its border is not, and the least of the ceiling is what is tested. FS-INV-701.',
  ['15.2.2', '10.2.1'], fdoc({'offset': 1000 * MM}, {**TRAY, 'height': 1000 * MM}), [('FS-INV-701', ['R1'])])
n('floors', 'vault-down-to-the-floor', 'A vault at 1450 mm along the centre line falling 1 in 1: at the walls, 1450 mm '
  'from the ridge, it reaches the floor exactly. FS-INV-701.', ['15.2.2', '15.3.2', '10.2.1'],
  fdoc(ceiling={'kind': 'vaulted', 'height': 1450 * MM, 'ridge': [[0, CY], [X, CY]], 'pitch': {'rise': 1, 'run': 1}}),
  [('FS-INV-701', ['R1'])])
LOW_RIDGE = {'kind': 'vaulted', 'ridge': [[0, 0], [3000 * MM, 1000 * MM]], 'pitch': HALF}
n('floors', 'vault-low-is-tested-exactly', 'A vault on the oblique ridge at 1780995 base units: at the room\'s far '
  'corner it comes down to 0.22 of a base unit above the floor - above it, so valid - and its low, rounded once, is 0, '
  'the floor\'s top. The test of 15.2.2 is made on the exact value.', ['15.2.2', '15.3.2', '2.2.1'],
  fdoc(ceiling={**LOW_RIDGE, 'height': 1780995}))
n('floors', 'vault-low-just-below-the-floor', 'The same vault one base unit lower: 0.78 of a base unit below the floor '
  'at that corner. FS-INV-701.', ['15.2.2', '10.2.1'], fdoc(ceiling={**LOW_RIDGE, 'height': 1780994}),
  [('FS-INV-701', ['R1'])])
n('floors', 'floor-thickness-zero', 'A floor 0 thick: a thickness is greater than zero; "not declared" is an absent '
  'member.', ['15.1.1'], fdoc({'thickness': 0}), SCH)
n('floors', 'floor-unknown-member', 'A floor has only an offset and a thickness: "finish" is the room\'s floorFinish.',
  ['15.1.1', '1.4.3'], fdoc({'finish': 'M1'}), SCH)
n('floors', 'floor-offset-with-a-fraction', 'An offset written with a fraction is not a length.', ['15.1.1', '2.1.1'],
  fdoc({'offset': -150000.0}), SCH)
n('floors', 'ceiling-unknown-kind', 'A "coffered" ceiling: a ceiling is flat, tray or vaulted.', ['15.2.1'],
  fdoc(ceiling={'kind': 'coffered'}), SCH)
n('floors', 'ceiling-without-kind', 'A ceiling with a height and no kind.', ['15.2.1'],
  fdoc(ceiling={'height': 2400 * MM}), SCH)
n('floors', 'ceiling-height-zero', 'A flat ceiling at height 0.', ['15.2.1'], fdoc(ceiling={'kind': 'flat', 'height': 0}),
  SCH)
n('floors', 'flat-ceiling-with-a-border', 'A flat ceiling with a tray\'s border: each form has only its own members.',
  ['15.2.1'], fdoc(ceiling={'kind': 'flat', 'border': 300 * MM}), SCH)
n('floors', 'tray-without-depth', 'A tray ceiling with a border and no depth.', ['15.2.1'],
  fdoc(ceiling={'kind': 'tray', 'border': 300 * MM}), SCH)
n('floors', 'tray-depth-zero', 'A tray 0 deep.', ['15.2.1'], fdoc(ceiling={**TRAY, 'depth': 0}), SCH)
n('floors', 'vault-without-pitch', 'A vault with a ridge and no pitch.', ['15.2.1'],
  fdoc(ceiling={'kind': 'vaulted', 'ridge': VAULT['ridge']}), SCH)
n('floors', 'vault-pitch-zero', 'A vault whose pitch rises 0: a pitch is two positive integers.', ['15.2.1'],
  fdoc(ceiling={**VAULT, 'pitch': {'rise': 0, 'run': 12}}), SCH)
n('floors', 'vault-ridge-of-three-points', 'A ridge is exactly two points.', ['15.2.1'],
  fdoc(ceiling={**VAULT, 'ridge': [[0, CY], [CX, CY], [X, CY]]}), SCH)
n('floors', 'vault-slopes-unknown', 'A vault whose slopes are "up".', ['15.2.1'], fdoc(ceiling={**VAULT, 'slopes': 'up'}),
  SCH)
n('floors', 'level-floor-thickness-zero', 'A level whose floors are 0 thick.', ['1.8.4'],
  fdoc(level={'floorThickness': 0}), SCH)
n('floors', 'level-ceiling-height-negative', 'A level whose ceilings are at -1.', ['1.8.4'],
  fdoc(level={'ceilingHeight': -1}), SCH)
d = copy.deepcopy(as_02('version-0.2-with-everything'))
next(iter(d['rooms'].values()))['ceiling'] = TRAY
n('floors', '0.2-document-with-a-ceiling', 'A document that declares "0.2" and whose room has a tray ceiling, which '
  '0.3 adds: Core 0.2\'s schema applies to it, and has no "ceiling" member.', ['1.2.6'], d, SCH)
d = copy.deepcopy(as_02('version-0.2-with-everything'))
next(iter(d['levels'].values()))['ceilingHeight'] = 2400 * MM
n('floors', '0.2-document-with-a-ceiling-height', 'A 0.2 document whose level has a ceiling height, which 0.3 adds.',
  ['1.2.6'], d, SCH)
n('floors', 'defaults-omitted', 'A floor at offset 0 with no thickness, and a vault whose slopes are "both", written '
  'out: the canonical form omits the floor - its offset is a constant default, and so is an empty floor - and the '
  'vault\'s "slopes", and keeps its "height", whose default is derived.', ['9.2.1', '15.1.2', '15.3.2'],
  fdoc({'offset': 0}, {**VAULT, 'slopes': 'both'}))
n('floors', 'flat-ceiling-written-out', 'A ceiling written {"kind": "flat"}: the canonical form omits it, its constant '
  'default, and the room has the flat ceiling at its level\'s height that it has without it.', ['9.2.1', '15.5.1'],
  fdoc(ceiling={'kind': 'flat'}))
d = fdoc(ceiling={'kind': 'flat', 'height': 2700 * MM})
n('floors', 'flat-ceiling-at-the-level-height', 'A flat ceiling whose own height equals its level\'s: kept in the '
  'canonical form - its default is derived, and omitting it would bind it to the level.', ['9.2.1', '15.5.1'], d)
n('floors', 'room-invariants-first', 'A room whose anchor is in a wall\'s thickness (FS-INV-204), with a tray border '
  'far too wide: floor and ceiling invariants are evaluated only for a room without FS-INV-201 to FS-INV-204, so only '
  'FS-INV-204.', ['10.3.1'], fdoc(ceiling={'kind': 'tray', 'border': 5000 * MM, 'depth': 1}, anchor=[CX, 32000]),
  [('FS-INV-204', ['R1'])])


def slab_doc(*slabs, levels=None):
    d = fdoc()
    d['slabs'] = {f'S{i}': s for i, s in enumerate(slabs, 1)}
    if levels:
        d['levels'].update(levels)
    return d


PATIO = {'level': 'L1', 'boundary': [[0, -3000 * MM], [0, -100 * MM], [X, -100 * MM], [X, -3000 * MM]],
         'thickness': 100 * MM, 'offset': -150 * MM, 'purpose': 'patio'}
n('floors', 'slab-bounding-geometry', 'A patio south of the room, its boundary written clockwise, its top 150 mm below '
  'the level and 100 mm thick: its outline is the boundary counter-clockwise from its least vertex, its top -150 mm, '
  'its bottom -250 mm, and its box spans them. Its purpose changes nothing derived.', ['15.7.1', '6.7.2'],
  slab_doc(PATIO))
n('floors', 'slab-on-an-upper-level', 'A balcony on a second level at 2700 mm, written counter-clockwise, flush with the '
  'level: top 2700 mm, bottom 2500 mm.', ['15.7.1', '6.7.2'],
  slab_doc({'level': 'L2', 'boundary': [[0, Y], [X, Y], [X, Y + 1200 * MM]], 'thickness': 200 * MM,
            'purpose': 'balcony'}, levels={'L2': {'building': 'B1', 'elevation': 2700 * MM, 'height': 2700 * MM}}))
SLAB_PURPOSES = ['patio', 'deck', 'porch', 'stoop', 'landing', 'balcony', 'garage', 'walkway', 'driveway', 'equipmentPad',
                 'other']
n('floors', 'slab-purposes', 'A slab of every purpose of 6.7, side by side south of the room: valid, each with its '
  'bounding geometry.', ['6.7.2', '15.7.1'],
  slab_doc(*({'level': 'L1', 'boundary': [[i * 400 * MM, -1000 * MM], [i * 400 * MM + 300 * MM, -1000 * MM],
                                           [i * 400 * MM + 300 * MM, -200 * MM]], 'thickness': 100 * MM, 'purpose': p}
             for i, p in enumerate(SLAB_PURPOSES))))
n('floors', 'slab-purpose-unknown', 'A slab whose purpose is "pool", which 6.7 does not list.', ['6.7.2'],
  slab_doc({**PATIO, 'purpose': 'pool'}), SCH)
n('floors', 'slab-boundary-crosses-itself', 'A deck whose boundary is a bow tie: an authored polygon is simple. '
  'FS-INV-009, and nothing of the slab is derived.', ['2.6.1', '10.2.1'],
  slab_doc({'level': 'L1', 'boundary': [[0, -2000 * MM], [X, -100 * MM], [X, -2000 * MM], [0, -100 * MM]],
            'thickness': 100 * MM, 'purpose': 'deck'}), [('FS-INV-009', ['S1'])])
d = copy.deepcopy(as_02('version-0.2-with-everything'))
d['slabs'] = {'S1': {'level': next(iter(d['levels'])), 'boundary': [[0, -1000], [1000, -1000], [1000, -10]],
                     'thickness': 1000, 'purpose': 'stoop'}}
n('floors', '0.2-document-with-a-slab-purpose', 'A 0.2 document whose slab states its purpose, which 0.3 adds.',
  ['1.2.6'], d, SCH)

# =================================================================================== hosting (0.3): 15.6
n('hosting', 'surface-on-a-sunken-floor', 'A piece standing on the floor of a room sunk 150 mm: its frame is at the '
  'floor\'s top, so its placement is at -150 mm and its fallback from -150 mm up.', ['15.6.1', '13.4.1', '12.6.2'],
  lit(fdoc({'offset': -150 * MM}), (CX, CY), which='floor'))
n('hosting', 'surface-on-a-room-ceiling', 'A light on a flat ceiling at the room\'s own 2400 mm, under a level 2700 mm '
  'high: it hangs from 2400 mm.', ['15.6.1', '13.4.1'], lit(fdoc(ceiling={'kind': 'flat', 'height': 2400 * MM}), (CX, CY)))
n('hosting', 'surface-on-a-tray-ceiling', 'Lights on a tray ceiling: X1 under the centre hangs from 2900 mm; X2 under '
  'the border from 2700 mm; X3 on the step - on the centre\'s outer ring, 350 mm from the south wall\'s line - is of '
  'the centre, so from 2900 mm.', ['15.6.1', '15.4.2', '13.4.1'],
  lit(fdoc(ceiling=TRAY), (CX, CY), (200 * MM, 200 * MM), (CX, 350 * MM)))
n('hosting', 'surface-on-a-vaulted-ceiling', 'Lights on the cathedral ceiling: X1 on the ridge hangs from 3200 mm, '
  'X2 1000 mm from the south wall\'s line - 500 mm from the ridge - from 2950 mm.', ['15.6.1', '15.3.2', '13.4.1'],
  lit(fdoc(ceiling=VAULT), (CX, CY), (1000 * MM, 1000 * MM)))
n('hosting', 'surface-on-an-oblique-vault', 'A light under the vault whose ridge is oblique: its frame\'s elevation is '
  'the ceiling\'s exact elevation at its position, rounded once, and its fallback box hangs from that integer.',
  ['15.6.1', '15.3.2', '13.4.1', '2.2.1'], lit(fdoc(ceiling=OBLIQUE), (3000 * MM, 2500 * MM)))
d = with_elements({**fdoc(), 'floorspec': '0.2'},
                  {'X1': element(host=surface('R1', (CX, CY), 'ceiling'), **LIGHT),
                   'X2': element(host=surface('R1', (1000 * MM, 1000 * MM), 'floor'), **PIECE)})
n('hosting', 'read-0.2-surface-hosts', 'A document declaring "0.2" with a light on its room\'s ceiling and a piece on '
  'its floor, read by a reader of 0.3: the light hangs from the level\'s elevation plus its height, 2700 mm, and the '
  'piece stands at its elevation, 0 - exactly where a reader of 0.2 places them; the room\'s floor and ceiling are '
  'there too.', ['15.6.1', '1.2.6', '13.4.1'], d)

NEW = list(TESTS)
del TESTS[:]


def main(argv) -> int:
    tests = BASE + NEW
    return 1 if write_all(prune='--prune' in argv, tests=tests, suite=SUITE03, reader=READER_03) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

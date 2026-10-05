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
import json
import os
import re
import sys

import tools.oracle.author02 as v02                    # declares the 0.2 suite: v02.BASE + v02.NEW
import tools.oracle.author03_materials as materials    # chapter 18: the group `materials`
import tools.oracle.us_library as us_library              # the US starter library (8.1): library/us-starter/
from tools.oracle.author import room_doc as room_doc_01
from tools.oracle.author02 import element, free, surface, wall_face, with_elements
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
    return materials.retarget(tc)


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

# ---- a type's or a material's source (8.1): the starter library (library/us-starter/)
LIB = 'https://d3cloud.io/floorspec/library/us-starter'


def lib_room(**opening_members):
    """The 4 m x 3 m room built from the US starter library: its four walls 2x4 partitions, a 30-inch
    interior door O1 on the south wall and a 36 x 48 inch double-hung window O2 on the west wall, each type
    and each material embedded exactly as the library publishes it, with its source."""
    d = odoc({'O1': {**D1, 'fill': 'door-interior-swing-30x80'}, 'O2': {**G1, 'fill': 'window-double-hung-36x48'}}, {})
    del d['types']['WT']
    for w in d['walls'].values():
        w['type'] = 'wall-2x4-interior'
    return us_library.embed(d, 'wall-2x4-interior', 'door-interior-swing-30x80', 'window-double-hung-36x48')


n('types', 'library-types-with-source', 'A room built from the US starter library: a 2x4 partition wall type, a door '
  'type and a window type, and the two materials the wall\'s layers use, each embedded with its "source" - the '
  'library\'s URI, its version and the item. Valid: a source is provenance, not a reference, and nothing derives '
  'from it - the door\'s and the window\'s clear openings are their types\' declared values, and the walls\' '
  'thickness their layers\'. The canonical form keeps every source.', ['8.1.3', '8.1.2', '7.4.2', '9.2.1'], lib_room())
d = lib_room()
d['types']['wall-2x4-interior']['layers'][1]['thickness'] = 5 * IN + IN // 2
d['types']['wall-2x4-interior']['name'] = '2x6 partition, edited after embedding'
n('types', 'source-of-an-edited-type', 'The library\'s 2x4 partition, edited after it was embedded into a 2x6 one '
  '(its stud layer 5 1/2 in): it keeps its source, which records where it came from, not that it still matches; '
  'valid.', ['8.1.3'], d)


def src_sch(slug, description, covers, mut):
    d = lib_room()
    mut(d)
    n('types', slug, description, covers, d, SCH)


src_sch('source-without-item', 'A wall type\'s source without "item": all three members are always present.',
        ['8.1.3'], lambda d: d['types']['wall-2x4-interior']['source'].pop('item'))
src_sch('source-without-version', 'A door type\'s source without "version".',
        ['8.1.3'], lambda d: d['types']['door-interior-swing-30x80']['source'].pop('version'))
src_sch('source-without-library', 'A material\'s source without "library".',
        ['8.1.3'], lambda d: d['materials']['gypsum-board']['source'].pop('library'))
src_sch('source-library-not-https', 'A source whose library is an http: URI: it must be https.',
        ['8.1.3'], lambda d: d['types']['window-double-hung-36x48']['source'].update(library='http://d3cloud.io/floorspec/library/us-starter'))
src_sch('source-library-relative', 'A source whose library is a relative reference, not an absolute URI.',
        ['8.1.3'], lambda d: d['materials']['wood-stud-framing']['source'].update(library='library/us-starter'))
src_sch('source-version-not-a-version', 'A source whose version is "v0.1": not a version string of 1.6.7.',
        ['8.1.3'], lambda d: d['types']['wall-2x4-interior']['source'].update(version='v0.1'))
src_sch('source-version-a-number', 'A source whose version is the number 1, not a string.',
        ['8.1.3'], lambda d: d['types']['wall-2x4-interior']['source'].update(version=1))
src_sch('source-item-not-an-id', 'A source whose item is "2x4 partition": a space is not in the pattern of an ID.',
        ['8.1.3'], lambda d: d['types']['wall-2x4-interior']['source'].update(item='2x4 partition'))
src_sch('source-unknown-member', 'A source with a "sha256" member: a source has exactly library, version and item.',
        ['8.1.3', '1.4.3'], lambda d: d['types']['door-interior-swing-30x80']['source'].update(sha256='ab' * 32))
src_sch('source-a-string', 'A source that is the item\'s URI as a string, not an object.',
        ['8.1.3'], lambda d: d['types']['door-interior-swing-30x80'].update(
            source=LIB + '/0.1.0/items/door-interior-swing-30x80.json'))
src_sch('source-on-a-wall', 'A wall with a source: only types and materials have one.',
        ['1.4.1'], lambda d: d['walls']['W1'].update(source={'library': LIB, 'version': '0.1.0', 'item': 'W1'}))
src_sch('source-on-a-layer', 'A layer with a source: the wall type has one, its layers do not.',
        ['1.4.3'], lambda d: d['types']['wall-2x4-interior']['layers'][0].update(
            source={'library': LIB, 'version': '0.1.0', 'item': 'gypsum-board'}))
d = copy.deepcopy(as_02('version-0.2-with-everything'))
d['types']['D']['source'] = {'library': LIB, 'version': '0.1.0', 'item': 'door-interior-swing-30x80'}
n('types', '0.2-document-with-source', 'A document that declares "0.2" whose door type has a source, which 0.3 '
  'adds: Core 0.2\'s schema has no "source" member.', ['1.2.6'], d, SCH)

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

# =================================================================================== materials (0.3): chapter 18
materials.declare()

# =================================================================================== roofs (0.3): chapter 16
# The standard room (above) under a roof: its walls' outer faces run from (-50 mm, -50 mm) to (4050 mm, 3050 mm), and
# level L1 is 2700 mm high, so a roof that says nothing about its height has its eaves at 2700 mm.
for tc in BASE:                                     # "roofs" is a collection of 0.3: another reserved name stands in
    if tc['slug'] == 'reserved-top-level-member':
        tc['inp'] = {('optionSets' if k == 'roofs' else k): v for k, v in tc['inp'].items()}
        tc['description'] = tc['description'].replace('"roofs"', '"optionSets"')

FP = [[-50 * MM, -50 * MM], [4050 * MM, -50 * MM], [4050 * MM, 3050 * MM], [-50 * MM, 3050 * MM]]
SIX = {'rise': 6, 'run': 12}
FT = 390144
# An L-shaped house in feet: a 40' x 24' wing along X and a 24' x 24' wing along Y, its corner at the origin.
L_FP = [[0, 0], [40 * FT, 0], [40 * FT, 24 * FT], [24 * FT, 24 * FT], [24 * FT, 48 * FT], [0, 48 * FT]]


def rf(footprint=None, **members):
    return {'level': 'L1', 'footprint': copy.deepcopy(footprint or FP), **members}


def roof_doc(*roofs, levels=None, **extra):
    """The standard room, declaring 0.3, with these roofs: RF1, RF2, ..."""
    d = fdoc()
    d['roofs'] = {f'RF{i}': r for i, r in enumerate(roofs, 1)}
    if levels:
        d['levels'].update(levels)
    d.update(extra)
    return d


def gables(*indices, **edge):
    return {str(i): {'gable': True, **edge} for i in indices}


LINT15 = [('FS-LINT-015', ['RF1'])]
n('roofs', 'hip-roof', 'A hip roof over the standard room: every edge of its footprint slopes at 6 in 12 and overhangs '
  '300 mm, so its eave outline is 4700 mm by 3700 mm at the level\'s 2700 mm. Its ridge runs 1000 mm along the long '
  'axis, 1850 mm from either long eave - 925 mm higher, at 3625 mm, its high - and four hips run from its ends to the '
  'corners: two trapezoids and two triangles.', ['16.5.1', '16.4.1', '16.3.1', '16.2.2', '16.2.3', '16.1.2', '9.2.1'],
  roof_doc(rf(pitch=SIX, overhang=300 * MM)))
S = [[0, 0], [3 * FT, 0], [3 * FT, 3 * FT], [0, 3 * FT]]
n('roofs', 'pyramid-roof', 'A hip roof on a square 12 feet across, at 12 in 12: its four hips meet at one point 6 feet '
  'above its eaves, and it has no ridge. (A square footprint makes a pyramid.)', ['16.5.1', '16.4.1'],
  roof_doc(rf([[0, 0], [12 * FT, 0], [12 * FT, 12 * FT], [0, 12 * FT]], pitch={'rise': 12, 'run': 12})))
n('roofs', 'gable-roof', 'A gable roof: the room\'s short edges, 1 and 3, are gables, and its long edges slope at 6 in '
  '12. The eaves overhang 300 mm and the gables, at the rake, 150 mm of their own: the ridge runs the whole length of '
  'the outline, and each gable end is a triangle rising to it.', ['16.5.1', '16.4.1', '16.2.2', '16.3.1'],
  roof_doc(rf(pitch=SIX, overhang=300 * MM, edges=gables(1, 3, overhang=150 * MM))))
n('roofs', 'l-shaped-hip-roof', 'An L-shaped house, its wings 24 feet wide, under a hip roof at 6 in 12: from the '
  'reflex corner a valley runs to where the ridges of the two wings meet, 12 feet in from three eaves, and hips run '
  'from every other corner.', ['16.5.1', '16.4.1'], roof_doc(rf(L_FP, pitch=SIX)))
n('roofs', 'l-shaped-gable-roof', 'The L-shaped house with both wing ends gabled: each ridge runs to its gable\'s '
  'midpoint, a valley and a hip meet the ridges where they cross, and each gable end is a triangle 6 feet high.',
  ['16.5.1', '16.4.1'], roof_doc(rf(L_FP, pitch=SIX, edges=gables(1, 4))))
n('roofs', 'shed-roof', 'A shed roof: only the south edge, 0, slopes, at 2 in 12, and the other three are gables. The '
  'roof is one plane rising north from the south eave, 3100 mm across the footprint, to 516.67 mm above the eave - '
  '3216.67 mm, rounded once to a base unit - and its three gable ends follow it.', ['16.5.1', '16.4.1', '2.2.1'],
  roof_doc(rf(pitch={'rise': 2, 'run': 12}, edges=gables(1, 2, 3))))
PENT = [[0, 0], [4000 * MM, 0], [4000 * MM, 3000 * MM], [2000 * MM, 4000 * MM], [0, 3000 * MM]]
n('roofs', 'shed-roof-on-an-oblique-edge', 'A shed roof over a five-sided footprint whose sloped edge is oblique - '
  'from (4 m, 3 m) to (2 m, 4 m), falling north-east - with its other edges gables, the outline wholly on its inner '
  'side: each vertex\'s elevation is its distance from the edge\'s line, an integer over the square root of 5 m², '
  'times 6 / 12, exact and rounded once.', ['16.5.1', '16.4.1', '2.2.1'],
  roof_doc(rf(PENT, pitch=SIX, edges=gables(0, 1, 3, 4))))
n('roofs', 'shed-roof-outline-behind-its-edge', 'A shed roof whose sloped edge is the north edge of an L\'s short '
  'wing, edge 2, with the long wing beyond its line: the plane would fall below its eave there. Its surface is not '
  'derived - FS-LINT-015 - and the document is valid.', ['16.4.1', '10.2.1'],
  roof_doc(rf(L_FP, pitch=SIX, edges=gables(0, 1, 3, 4, 5))), LINT15)
n('roofs', 'flat-roof', 'A flat roof: no pitch anywhere, a 600 mm overhang all round, 300 mm thick. Its one face is '
  'its eave outline at 2700 mm, its box reaches down by its thickness, and it has no gables and no lines.',
  ['16.5.1', '16.4.1', '16.3.1', '16.2.1'], roof_doc(rf(overhang=600 * MM, thickness=300 * MM)))
n('roofs', 'flat-roof-on-an-oblique-outline', 'A flat roof over the five-sided footprint, overhanging 500 mm: the '
  'moved lines of its oblique edges have irrational positions, so the outline\'s vertices are exact corner points '
  'rounded once - the apex moves up 500 mm times the square root of 5 over 2.', ['16.3.1', '16.5.1', '2.2.1'],
  roof_doc(rf(PENT, overhang=500 * MM)))
n('roofs', 'mixed-pitches', 'A hip roof whose south edge rises at 12 in 12 and the rest at 6 in 12: a roof of '
  'unequal pitches needs the weighted straight skeleton, which this draft does not define. Its eave outline is '
  'derived and its surface is not: FS-LINT-015, an informational lint, and the document is valid.',
  ['16.4.1', '10.2.1', '10.1.1'], roof_doc(rf(pitch=SIX, edges={'0': {'pitch': {'rise': 12, 'run': 12}}})), LINT15)
n('roofs', 'equal-pitches-as-ratios', 'Edge 0 pitched 1 in 2 under a roof pitched 6 in 12: the same pitch, compared as '
  'ratios, so the hip roof is derived exactly as if every edge said 6 in 12.', ['16.4.1', '16.5.1'],
  roof_doc(rf(pitch=SIX, overhang=300 * MM, edges={'0': {'pitch': {'rise': 1, 'run': 2}}})))
n('roofs', 'hip-roof-on-an-oblique-outline', 'A hip roof on the five-sided footprint: an equal-pitch roof with an '
  'oblique edge has skeleton nodes irrational in more than one radicand, and its surface is not derived in this draft. '
  'FS-LINT-015.', ['16.4.1', '10.2.1'], roof_doc(rf(PENT, pitch=SIX)), LINT15)
n('roofs', 'adjacent-gables', 'A rectangle with gables on edges 1 and 2, which meet at a corner: a gable\'s neighbours '
  'must both be sloped. FS-LINT-015.', ['16.4.1'], roof_doc(rf(pitch=SIX, edges=gables(1, 2))), LINT15)
U_FP = [[0, 0], [36 * FT, 0], [36 * FT, 30 * FT], [24 * FT, 30 * FT], [24 * FT, 12 * FT], [12 * FT, 12 * FT],
        [12 * FT, 30 * FT], [0, 30 * FT]]
n('roofs', 'gable-on-an-inner-face', 'A U-shaped house with a gable on the inner face of its west arm, edge 5: both '
  'ends of that edge are reflex corners, so it is not the end of a wing. FS-LINT-015.', ['16.4.1'],
  roof_doc(rf(U_FP, pitch=SIX, edges=gables(5))), LINT15)


def g_fp(gap):
    """A G-shaped house in feet: a west arm 10' wide whose north end, edge 8, faces the south eave of a top wing
    `gap` feet away."""
    return [[0, 0], [40 * FT, 0], [40 * FT, 40 * FT], [0, 40 * FT], [0, (20 + gap) * FT], [30 * FT, (20 + gap) * FT],
            [30 * FT, 10 * FT], [10 * FT, 10 * FT], [10 * FT, 20 * FT], [0, 20 * FT]]


n('roofs', 'gable-clearance-clear', 'A G-shaped house whose west arm, 10 feet wide, ends in a gable, edge 8, facing '
  'the south eave of the top wing 5 feet away: the gable\'s clearance is 5 feet deep, and the eave lies on its far '
  'side, not inside it, so the roof is derived.', ['16.4.1', '16.5.1'], roof_doc(rf(g_fp(5), pitch=SIX, edges=gables(8))))
n('roofs', 'gable-clearance-blocked', 'The same house with the top wing 4 feet from the gable: its south eave is '
  'inside the gable\'s clearance, and the roof is not derived. FS-LINT-015.', ['16.4.1'],
  roof_doc(rf(g_fp(4), pitch=SIX, edges=gables(8))), LINT15)
n('roofs', 'collinear-eaves-share-a-plane', 'A rectangle with a narrow bay, 2 feet square, pushed out of its south '
  'side: the south eave is two collinear edges, 0 and 4, either side of the bay, facing the same way. Once the bay\'s '
  'little hip closes, their faces meet, in one plane: the boundary between them, from the valleys\' meeting point to '
  'the main ridge, is a seam and not a line, and each face is still its own edge\'s.', ['16.4.1', '16.5.1'],
  roof_doc(rf([[0, 0], [14 * FT, 0], [14 * FT, -2 * FT], [16 * FT, -2 * FT], [16 * FT, 0], [30 * FT, 0],
               [30 * FT, 20 * FT], [0, 20 * FT]], pitch=SIX)))
n('roofs', 'notch-splits-the-wavefront', 'A rectangle with a notch cut into its north side: the notch\'s corners '
  'are reflex, and their valleys reach the south eave\'s wavefront before the roof closes, splitting it in two. The '
  'roof has two hipped halves joined by a ridge over the notch.', ['16.4.1', '16.5.1'],
  roof_doc(rf([[0, 0], [20 * FT, 0], [20 * FT, 10 * FT], [11 * FT, 10 * FT], [11 * FT, 6 * FT], [9 * FT, 6 * FT],
               [9 * FT, 10 * FT], [0, 10 * FT]], pitch=SIX)))
n('roofs', 'clockwise-footprint', 'A gable roof with its footprint written clockwise: the outline is derived '
  'counter-clockwise from its least vertex; the gables, its short ends, are edges 0 and 2 as it is written - west, '
  'north, east, south - and every face and gable keeps its edge\'s index as written.',
  ['16.5.1', '16.3.1'],
  roof_doc(rf([[-50 * MM, -50 * MM], [-50 * MM, 3050 * MM], [4050 * MM, 3050 * MM], [4050 * MM, -50 * MM]],
              pitch=SIX, overhang=300 * MM, edges=gables(0, 2))))
n('roofs', 'unequal-overhangs', 'A hip roof that overhangs its south edge 900 mm and the rest 300 mm: the eave '
  'outline is computed first, and the roof from it, so the ridge moves 300 mm south and every eave stays at 2700 mm.',
  ['16.3.1', '16.5.1'], roof_doc(rf(pitch=SIX, overhang=300 * MM, edges={'0': {'overhang': 900 * MM}})))
n('roofs', 'half-unit-ridge', 'A hip roof 5248000 by 3967999 base units at 7 in 12: its ridge lies on '
  'y = 1983999.5, half a base unit off the grid, and rises 7/12 of 1983999.5 above the eave. Each is rounded once, '
  'ties to even.', ['16.5.1', '2.2.1'],
  roof_doc(rf([[0, 0], [4100 * MM, 0], [4100 * MM, 3967999], [0, 3967999]], pitch={'rise': 7, 'run': 12})))
n('roofs', 'roof-height-and-level', 'A roof on a second level at 2700 mm with its eaves 2400 mm above it - its own '
  'height, not the level\'s 2600 mm - and a hip roof at 6 in 12: eaves at 5100 mm.', ['16.3.1', '16.5.1'],
  roof_doc(rf(level='L2', pitch=SIX, height=2400 * MM),
           levels={'L2': {'building': 'B1', 'elevation': 2700 * MM, 'height': 2600 * MM}}))
n('roofs', 'roof-material-and-thickness', 'A hip roof with a material - which counts as referred, so no unused-material '
  'lint - and a thickness of 250 mm, which lowers its box\'s floor below its eave.', ['16.5.1'],
  roof_doc(rf(pitch=SIX, thickness=250 * MM, material='SH'), materials={'SH': {'color': '#4a4a4a'}}))
n('roofs', 'two-roofs', 'Two roofs: a gable roof over the room and a flat roof over a porch south of it. Each is '
  'derived on its own.', ['16.5.1'],
  roof_doc(rf(pitch=SIX, edges=gables(1, 3)),
           rf([[0, -2000 * MM], [4000 * MM, -2000 * MM], [4000 * MM, -100 * MM], [0, -100 * MM]], height=2400 * MM)))
n('roofs', 'defaults-omitted', 'A roof with its overhang 0, an edge whose gable is false and one that is empty, written '
  'out: the canonical form omits each - and "edges", left empty - and keeps "height", whose default is derived.',
  ['9.2.1', '16.5.1'], roof_doc(rf(pitch=SIX, overhang=0, height=2700 * MM, edges={'0': {'gable': False}, '2': {}})))
n('roofs', 'edge-out-of-range', 'A roof on a four-edge footprint with an override for edge 4, which does not exist. '
  'FS-INV-801.', ['16.1.2', '10.2.1'], roof_doc(rf(pitch=SIX, edges={'4': {'gable': True}})), [('FS-INV-801', ['RF1'])])
n('roofs', 'flat-roof-with-a-sloped-edge', 'A roof with no pitch whose edge 0 has one: one edge slopes and three are '
  'level. FS-INV-802.', ['16.2.1', '10.2.1'], roof_doc(rf(edges={'0': {'pitch': SIX}})), [('FS-INV-802', ['RF1'])])
n('roofs', 'flat-roof-with-a-gable', 'A roof with no pitch and a gable: a gable is not level, so the roof is part flat. '
  'FS-INV-802.', ['16.2.1'], roof_doc(rf(edges=gables(1))), [('FS-INV-802', ['RF1'])])
n('roofs', 'every-edge-a-gable', 'A roof with a pitch whose every edge is a gable: no edge slopes. FS-INV-803.',
  ['16.2.2', '10.2.1'], roof_doc(rf(pitch=SIX, edges=gables(0, 1, 2, 3))), [('FS-INV-803', ['RF1'])])
n('roofs', 'collinear-edges', 'A footprint with a fifth vertex in the middle of its south edge: edges 0 and 1 are '
  'collinear. FS-INV-804; FS-INV-805 is not evaluated for it, though its overhangs differ either side of the vertex.',
  ['16.2.3', '10.2.1', '10.3.1'],
  roof_doc(rf([[-50 * MM, -50 * MM], [2000 * MM, -50 * MM], [4050 * MM, -50 * MM], [4050 * MM, 3050 * MM],
               [-50 * MM, 3050 * MM]], pitch=SIX, edges={'0': {'overhang': 300 * MM}})), [('FS-INV-804', ['RF1'])])
n('roofs', 'overhang-closes-a-notch', 'The notched rectangle with a 2-foot overhang all round: the notch is 2 feet '
  'wide, so its sides\' moved lines cross and its bottom edge runs backwards. FS-INV-805.', ['16.3.1', '10.2.1'],
  roof_doc(rf([[0, 0], [20 * FT, 0], [20 * FT, 10 * FT], [11 * FT, 10 * FT], [11 * FT, 6 * FT], [9 * FT, 6 * FT],
               [9 * FT, 10 * FT], [0, 10 * FT]], pitch=SIX, overhang=2 * FT)), [('FS-INV-805', ['RF1'])])
n('roofs', 'overhang-fills-a-notch-exactly', 'The same notch with a 1-foot overhang: its bottom edge keeps no length, '
  'and an edge with no length does not run its edge\'s way. FS-INV-805.', ['16.3.1'],
  roof_doc(rf([[0, 0], [20 * FT, 0], [20 * FT, 10 * FT], [11 * FT, 10 * FT], [11 * FT, 6 * FT], [9 * FT, 6 * FT],
               [9 * FT, 10 * FT], [0, 10 * FT]], pitch=SIX, overhang=FT)), [('FS-INV-805', ['RF1'])])
n('roofs', 'overhangs-meet-across-a-gap', 'The G-shaped house with its top wing 4 feet from the west arm\'s end, '
  'both overhanging that gap by 3 feet: every edge still runs its way, but the two moved eaves pass each other and the '
  'eave outline crosses itself. FS-INV-805.', ['16.3.1'],
  roof_doc(rf(g_fp(4), pitch=SIX, edges={'4': {'overhang': 3 * FT}, '8': {'overhang': 3 * FT}})),
  [('FS-INV-805', ['RF1'])])
n('roofs', 'footprint-crosses-itself', 'A roof whose footprint is a bow tie: an authored polygon is simple. '
  'FS-INV-009 names the roof, and no other invariant is evaluated.', ['2.6.1', '10.2.1', '10.3.1'],
  roof_doc(rf([[0, 0], [4000 * MM, 3000 * MM], [4000 * MM, 0], [0, 3000 * MM]], pitch=SIX)), [('FS-INV-009', ['RF1'])])
n('roofs', 'roof-on-a-missing-level', 'A roof on a level that does not exist: FS-INV-002.', ['3.2.1', '10.2.1'],
  roof_doc(rf(level='L9', pitch=SIX)), [('FS-INV-002', ['RF1'])])
n('roofs', 'roof-with-a-missing-material', 'A roof whose material does not exist: FS-INV-002.', ['3.2.1'],
  roof_doc(rf(pitch=SIX, material='NOPE')), [('FS-INV-002', ['RF1'])])
n('roofs', 'reference-error-stops-roof-invariants', 'A roof on a missing level whose every edge is a gable: once a '
  'reference invariant is reported, no other is evaluated, so only FS-INV-002.', ['10.3.1'],
  roof_doc(rf(level='L9', pitch=SIX, edges=gables(0, 1, 2, 3))), [('FS-INV-002', ['RF1'])])
n('roofs', 'roof-invariants-together', 'Three roofs: one with an edge out of range and every edge a gable, one part '
  'flat, and one with collinear edges: each is reported, sorted by code.', ['10.2.1', '10.3.1', '16.1.2', '16.2.1',
                                                                         '16.2.2', '16.2.3'],
  roof_doc(rf(pitch=SIX, edges={**gables(0, 1, 2, 3), '7': {}}), rf(edges=gables(0)),
           rf([[0, 0], [2000 * MM, 0], [4000 * MM, 0], [4000 * MM, 3000 * MM]], pitch=SIX)),
  [('FS-INV-801', ['RF1']), ('FS-INV-802', ['RF2']), ('FS-INV-803', ['RF1']), ('FS-INV-804', ['RF3'])])
n('roofs', 'pitch-rise-zero', 'A roof pitched 0 in 12: a pitch is two positive integers; a flat roof has none.',
  ['16.1.1'], roof_doc(rf(pitch={'rise': 0, 'run': 12})), SCH)
n('roofs', 'edge-pitch-run-too-large', 'An edge pitched 6 in 2^53.', ['16.1.1'],
  roof_doc(rf(pitch=SIX, edges={'1': {'pitch': {'rise': 6, 'run': 2 ** 53}}})), SCH)
n('roofs', 'overhang-negative', 'An overhang of -1.', ['16.1.1'], roof_doc(rf(pitch=SIX, overhang=-1)), SCH)
n('roofs', 'edge-overhang-negative', 'An edge\'s overhang of -1.', ['16.1.1'],
  roof_doc(rf(pitch=SIX, edges={'0': {'overhang': -1}})), SCH)
n('roofs', 'thickness-zero', 'A roof 0 thick: "not declared" is an absent member.', ['16.1.1'],
  roof_doc(rf(pitch=SIX, thickness=0)), SCH)
n('roofs', 'height-with-a-fraction', 'A height written with a fraction is not a length.', ['16.1.1', '2.1.1'],
  roof_doc(rf(pitch=SIX, height=3000000.0)), SCH)
n('roofs', 'edge-index-with-a-leading-zero', 'An edge named "01": an edge index has no leading zeros.', ['16.1.1'],
  roof_doc(rf(pitch=SIX, edges={'01': {'gable': True}})), SCH)
n('roofs', 'edge-index-not-a-number', 'An edge named "north".', ['16.1.1'],
  roof_doc(rf(pitch=SIX, edges={'north': {'gable': True}})), SCH)
n('roofs', 'gable-with-a-pitch', 'A gable with a pitch of its own: a gable does not slope.', ['16.1.1'],
  roof_doc(rf(pitch=SIX, edges={'1': {'gable': True, 'pitch': SIX}})), SCH)
n('roofs', 'gable-not-a-boolean', 'A gable flag of "yes".', ['16.1.1'], roof_doc(rf(pitch=SIX, edges={'1': {'gable': 'yes'}})),
  SCH)
n('roofs', 'edge-unknown-member', 'An edge has only gable, pitch and overhang: "fascia" is unknown.', ['16.1.1', '1.4.3'],
  roof_doc(rf(pitch=SIX, edges={'1': {'fascia': 200 * MM}})), SCH)
n('roofs', 'roof-unknown-member', 'A roof has only the members of its table: "kind" is derived, never stored.',
  ['16.1.1', '1.4.1'], roof_doc(rf(pitch=SIX, kind='hip')), SCH)
n('roofs', 'roof-without-footprint', 'A roof with a level and a pitch and no footprint.', ['16.1.1'],
  roof_doc({'level': 'L1', 'pitch': SIX}), SCH)
n('roofs', 'footprint-of-two-points', 'A footprint of two points is not a polygon.', ['16.1.1', '2.6.1'],
  roof_doc(rf([[0, 0], [4000 * MM, 0]], pitch=SIX)), SCH)
d = copy.deepcopy(as_02('version-0.2-with-everything'))
d['roofs'] = {'RF1': {'level': next(iter(d['levels'])), 'footprint': [[0, 0], [1000, 0], [1000, 1000]]}}
n('roofs', '0.2-document-with-a-roof', 'A document that declares "0.2" and has a roof: "roofs" is a collection 0.3 '
  'adds, and Core 0.2\'s schema has no such member.', ['1.2.6', '1.1.2'], d, SCH)

# =================================================================================== stairs (0.3): chapter 17
# Two storeys: L1 at 0 and L2 at 2700 mm, each 2700 mm high. Plans are drawn in millimetres by Draw, which
# names junctions <p>J1, <p>J2, ... by position, and walls <p>W1, ... and separators <p>S1, ... in the order
# they are drawn. The standard stair rises east from (1000 mm, 600 mm), 900 mm wide - from y = 150 mm to
# 1050 mm - with 250 mm treads.
from tools.oracle.author02 import cdoc, plan                                    # noqa: E402
from tools.oracle.author_lib import S as Sep                                    # noqa: E402

LEVELS2 = {'L1': {'building': 'B1', 'elevation': 0, 'height': 2700 * MM},
           'L2': {'building': 'B1', 'elevation': 2700 * MM, 'height': 2700 * MM}}


class Draw:
    def __init__(self, level, p):
        self.level, self.p = level, p
        self.js, self.ws, self.ss, self.at = {}, {}, {}, {}

    def j(self, x, y):
        if (x, y) not in self.at:
            jid = f'{self.p}J{len(self.js) + 1}'
            self.at[(x, y)] = jid
            self.js[jid] = J(x * MM, y * MM, self.level)
        return self.at[(x, y)]

    def walls(self, *pts):
        for a, b in zip(pts, pts[1:]):
            self.ws[f'{self.p}W{len(self.ws) + 1}'] = W(self.j(*a), self.j(*b), self.level)
        return self

    def seps(self, *pts):
        for a, b in zip(pts, pts[1:]):
            self.ss[f'{self.p}S{len(self.ss) + 1}'] = Sep(self.j(*a), self.j(*b), self.level)
        return self


def storeys(*draws, rooms=None, stairs=None, levels=None):
    d = v3(level_doc(levels=copy.deepcopy(levels or LEVELS2)))
    for dr in draws:
        for k, v in (('junctions', dr.js), ('walls', dr.ws), ('separators', dr.ss)):
            if v:
                d.setdefault(k, {}).update(v)
    d['rooms'] = {rid: R(x * MM, y * MM, lv, **kw) for rid, (lv, x, y, kw) in (rooms or {}).items()}
    if stairs:
        d['stairs'] = stairs
    return d


def stair(x=1000, y=600, to='L2', level='L1', width=900, tread=250, risers=14, **kw):
    st = {'level': level, 'to': to, 'position': [x * MM, y * MM], 'width': width * MM, 'tread': tread * MM}
    if risers is not None:
        st['risers'] = risers
    st.update(kw)
    return st


def lower(p='D'):
    """L1: one 6 m by 4 m room's walls."""
    return Draw('L1', p).walls((0, 0), (0, 4000), (6000, 4000), (6000, 0), (0, 0))


def upper(x0=1500, x1=4250, y1=1100, p='U'):
    """L2: the same walls, with a well - separators around (x0, 0) to (x1, y1), standing for a railing - that no
    room is anchored in."""
    return (Draw('L2', p).walls((0, 0), (0, 4000), (6000, 4000), (6000, 0), (x1, 0), (x0, 0), (0, 0))
            .seps((x0, 0), (x0, y1), (x1, y1), (x1, 0)))


HALLS = {'R1': ('L1', 3000, 2500, {}), 'R2': ('L2', 3000, 3000, {})}
WELL = [('FS-LINT-003', [])]


def hall_house(x0=1500, x1=4250, y1=1100, l1=None, l2=None, rooms=None, **st):
    levels = copy.deepcopy(LEVELS2)
    levels['L1'].update(l1 if l1 is not None else {'ceilingHeight': 2400 * MM})
    levels['L2'].update(l2 if l2 is not None else {'floorThickness': 300 * MM})
    return storeys(lower(), upper(x0, x1, y1), rooms=rooms or HALLS, stairs={'ST1': stair(**st)}, levels=levels)


n('stairs', 'straight-stair', 'A straight stair of 14 risers from a hall on L1 to the hall above, through a well '
  'that starts 500 mm past its first nosing line. Its foot room is R1 (bottom 0) and its head, 13 treads on at '
  '(4250 mm, 600 mm), is on the well\'s separator and so in R2 (top 2700 mm): a rise of 3456000, riser height '
  '3456000 / 14 rounded to 246857. Its run is 13 x 250 mm, its walkline the same length, and its 13 treads are '
  'listed bottom to top. The headroom is where the floor above ends: at the well\'s edge the nosing line is 3 risers '
  'up, 740571.43, under L2\'s 300 mm floor and L1\'s 2400 mm ceilings at 3072000 - 2331428.57, rounded to 2331429.',
  ['17.1.1', '17.4.3', '17.5.1', '17.6.1', '2.2.1'], hall_house(), WELL)
n('stairs', 'stair-under-its-floor', 'The same stair with no well: the floor of R2 covers it, so near its head the '
  'nosing line rises through the floor\'s 300 mm, and the headroom is -384000 - the floor\'s bottom, 2400 mm, less '
  'the head\'s 2700 mm. A negative headroom says the floor is in the way.', ['17.6.1'],
  storeys(lower(), Draw('L2', 'U').walls((0, 0), (0, 4000), (6000, 4000), (6000, 0), (0, 0)), rooms=HALLS,
          stairs={'ST1': stair()},
          levels={'L1': {**LEVELS2['L1'], 'ceilingHeight': 2400 * MM}, 'L2': {**LEVELS2['L2'], 'floorThickness': 300 * MM}}))
n('stairs', 'stair-under-its-well', 'A well that starts at the stair\'s first nosing line: every point of every lane '
  'is in the well, where L1\'s ceiling is cut and no room of L2 is, so nothing is above the stair and it has no '
  'headroom member.', ['17.6.1'], hall_house(x0=1000), WELL)
n('stairs', 'max-riser', 'The straight stair with no riser count and a greatest riser of 7 3/4 in (251968): 2700 mm '
  'over 13 risers would be 265846.15, too tall; over 14, 246857.14 is not. Its riser count is 14, and every other '
  'value is the first test\'s.', ['17.1.1', '17.4.3'], hall_house(risers=None, maxRiser=31 * IN // 4), WELL)
n('stairs', 'sunken-foot', 'A hall on L1 sunk 150 mm: the stair\'s bottom is the top of its foot room\'s floor, '
  '-192000, so its rise is 2850 mm, and with a greatest riser of 7 3/4 in it needs 15 risers of 243200 - one more than '
  'from a floor at the level\'s elevation. Its head moves out a tread, to (4500 mm, 600 mm), past the well into R2, '
  'whose 300 mm floor is now over its last tread: its headroom is -384000.',
  ['17.4.3', '15.1.2'],
  hall_house(rooms={'R1': ('L1', 3000, 2500, {'floor': {'offset': -150 * MM}}), 'R2': HALLS['R2']},
             risers=None, maxRiser=31 * IN // 4), WELL)
n('stairs', 'foot-in-no-room', 'A stair whose position, 30 mm east of L1\'s west wall\'s location line, is in that '
  'wall\'s thickness - in no room - and whose head, on the well\'s east separator at (3280 mm, 600 mm), is in R2: its '
  'bottom is L1\'s elevation, it has no footRoom member, and it derives everything else.', ['17.4.3'],
  hall_house(x=30, x1=3280), WELL)

L_FORM = {'kind': 'lShaped', 'turn': 'left', 'risersBeforeTurn': 7}


def l_house(form=None, rotation=None, **kw):
    """An L-shaped stair and a well around its landing and its second flight: from (2400, 0) to (3500, 2550)."""
    st = {'form': form or L_FORM}
    if rotation is not None:
        st['rotation'] = rotation
    return hall_house(x0=2400, x1=3500, y1=2550, **st, **kw)


n('stairs', 'l-stair-with-landing', 'An L-shaped stair turning left: a first flight of 7 risers east from (1000 mm, '
  '600 mm), a 900 mm square landing at 7 risers up from (2500 mm, 150 mm), and a second flight of 7 risers north '
  'from (2950 mm, 1050 mm) to its head at (2950 mm, 2550 mm), on the well\'s north separator. 12 treads and the '
  'landing, in walking order; a run of 12 x 250 mm, and a walkline through the landing\'s middle of 12 x 250 + 900 '
  'mm. Its headroom is under the floor above the first flight, at the well\'s west edge.',
  ['17.4.3', '17.5.1', '17.6.1'], l_house(), WELL)
d = storeys(Draw('L1', 'D').walls((0, 0), (0, 4000), (6000, 4000), (6000, 0), (0, 0)),
            Draw('L2', 'U').walls((0, 0), (0, 4000), (6000, 4000), (6000, 0), (0, 0)),
            rooms={'R1': ('L1', 4500, 2000, {}), 'R2': ('L2', 4500, 2000, {})},
            stairs={'ST1': stair(x=600, y=500, rotation=90_000_000,
                                 form={'kind': 'lShaped', 'turn': 'right', 'risersBeforeTurn': 9})})
n('stairs', 'l-stair-turning-right', 'An L-shaped stair that rises north (rotation 90 degrees) from (600 mm, 500 mm) '
  'and turns right: in its frame the mirror image of a left turn. Its landing is from y = 2500 mm to 3400 mm, and '
  'its second flight runs east from it to its head at (2050 mm, 2950 mm). With no well, the floor of R2 is over all of it '
  'and its headroom is 0: L2\'s floor declares no thickness, so its bottom is its top.', ['17.4.3', '17.5.1', '17.6.1'], d)
U_FORM = {'kind': 'uShaped', 'turn': 'left', 'risersBeforeTurn': 7, 'gap': 200 * MM}
n('stairs', 'u-stair-with-landing', 'A U-shaped stair turning left, with a 200 mm gap between its flights: 7 risers '
  'east, a landing 900 mm deep across both flights and the gap, from (2500 mm, 150 mm) to (3400 mm, 2150 mm), and 7 '
  'risers west from (2500 mm, 1700 mm) to its head at (1000 mm, 1700 mm) - above its foot. Its walkline runs '
  'through the landing\'s middle: 12 x 250 + 2 x 900 + 200 mm. The well covers the whole stair, so it has no '
  'headroom.', ['17.4.3', '17.5.1', '17.6.1'],
  hall_house(x0=1000, x1=3500, y1=2200, form=U_FORM), WELL)
n('stairs', 'u-stair-turning-right-no-gap', 'A U-shaped stair turning right with no gap - written out as "gap": 0, '
  'its constant default, which the canonical form omits: its second flight is beside its first, to its right.',
  ['17.4.3', '17.5.1', '9.2.1'],
  storeys(Draw('L1', 'D').walls((0, 0), (0, 4000), (6000, 4000), (6000, 0), (0, 0)),
          rooms={'R1': ('L1', 3000, 3500, {})},
          stairs={'ST1': stair(y=2500, form={'kind': 'uShaped', 'turn': 'right', 'risersBeforeTurn': 8, 'gap': 0})}))
n('stairs', 'rotated-stair', 'A straight stair rising at 30 degrees: its frame faces F(30000000) = (866025404, '
  '500000000), so the corners of its treads, its head and its box are irrational, each rounded once. L2 has no '
  'room, so the stair has no head room and its top is L2\'s elevation; under R1\'s ceiling at 2700 mm its headroom is '
  '0, at the head.', ['17.4.3', '17.5.1', '17.6.1', '2.2.1'],
  storeys(Draw('L1', 'D').walls((0, 0), (0, 6000), (8000, 6000), (8000, 0), (0, 0)),
          rooms={'R1': ('L1', 6000, 5000, {})}, stairs={'ST1': stair(x=1500, y=1000, rotation=30_000_000)}))

VAULT_R1 = {'kind': 'vaulted', 'height': 4500 * MM, 'ridge': [[0, 0], [6000 * MM, 2000 * MM]], 'pitch': HALF}


def loft(ceiling=None, l1=None):
    """L1: a living room R1 from x = 0 to 4500 mm with this ceiling, and R3 beyond; L2: only a loft R2 east of
    x = 4250 mm, its west side a separator for its railing. Nothing of L2 is over the stair."""
    lv = copy.deepcopy(LEVELS2)
    lv['L1'].update(l1 or {})
    return storeys(Draw('L1', 'D').walls((0, 0), (0, 4000), (4500, 4000), (6000, 4000), (6000, 0), (4500, 0), (0, 0))
                   .walls((4500, 0), (4500, 4000)),
                   Draw('L2', 'U').walls((4250, 4000), (6000, 4000), (6000, 0), (4250, 0)).seps((4250, 0), (4250, 4000)),
                   rooms={'R1': ('L1', 2000, 2000, {'ceiling': ceiling} if ceiling else {}), 'R3': ('L1', 5200, 2000, {}),
                          'R2': ('L2', 5000, 2000, {})},
                   stairs={'ST1': stair()}, levels=lv)


n('stairs', 'headroom-under-a-vault', 'A stair up to a loft, under the cathedral ceiling of the room it rises in: '
  'the ridge runs from (0, 0) to (6000 mm, 2000 mm) at 4500 mm and falls 6 in 12, and L2 has nothing over the stair. '
  'The lanes cross the ridge line - the ceiling\'s highest line - so it splits them; the least clearance is at the '
  'head, at the stair\'s south side, where the vault is lowest: 4500 mm less half of 7600000 / sqrt(40000000) mm, '
  'less 2700 mm, exact in one radicand and rounded once.', ['17.6.1', '15.3.2', '2.2.1'], loft(VAULT_R1))
n('stairs', 'headroom-under-a-tray', 'The same stair under a tray ceiling at 3000 mm with a 500 mm border and its '
  'centre 400 mm higher: the stair\'s north side, at y = 1050 mm, is under the centre from its foot to x = 3950 mm and '
  'under the border beyond it, which splits that lane; its south side is under the border all the way. The least '
  'clearance is at the head, under the border: 3000 mm less 2700 mm, 384000.', ['17.6.1', '15.4.2'],
  loft({'kind': 'tray', 'height': 3000 * MM, 'border': 500 * MM, 'depth': 400 * MM}))

WINDER_Q = {'kind': 'winder', 'turn': 'left', 'angle': 'quarter', 'risersBeforeTurn': 4, 'winders': 3}
n('stairs', 'winder-quarter', 'A quarter-turn winder stair: 4 risers east, 3 winders in the 900 mm square at the '
  'turn, and 7 straight treads north, to its head at (2200 mm, 2800 mm). Its rise, risers and box are derived - '
  'the box spans its first flight, the square and its second flight - and its steps, run, walkline and headroom are '
  'not: FS-LINT-016, an info.', ['17.1.1', '17.2.1', '17.4.3', '17.7.1', '17.7.2', '10.2.1'],
  hall_house(x0=1000, x1=2800, y1=2800, form=WINDER_Q), WELL + [('FS-LINT-016', ['ST1'])])
n('stairs', 'winder-half', 'A half-turn winder stair turning left with a 100 mm gap: 4 risers east from (1000 mm, '
  '600 mm), 6 winders in the turn across both flights and the gap, then 5 straight treads west to its head at '
  '(500 mm, 1600 mm). Its box spans x = 500 mm to 2650 mm and y = 150 mm to 2050 mm; FS-LINT-016.',
  ['17.2.1', '17.4.3', '17.7.1'],
  hall_house(x0=400, x1=2800, y1=2100, risers=15,
             form={'kind': 'winder', 'turn': 'left', 'angle': 'half', 'risersBeforeTurn': 4, 'winders': 6,
                   'gap': 100 * MM}), WELL + [('FS-LINT-016', ['ST1'])])
SPIRAL = {'kind': 'spiral', 'turn': 'left', 'diameter': 1800 * MM, 'sweep': 270_000_000}
n('stairs', 'spiral', 'A spiral stair 1800 mm across, 800 mm wide, turning left through 270 degrees from its first '
  'nosing line at (2000 mm, 1000 mm): its centre is 500 mm to the left, at (2000 mm, 1500 mm), and its head is turned '
  '270 degrees about it, to (1500 mm, 1500 mm), in the well. Its box is the square around its circle; its steps are '
  'not derived (FS-LINT-016).', ['17.2.1', '17.4.3', '17.7.1', '17.7.2'],
  hall_house(x0=1000, x1=3000, y1=2500, x=2000, y=1000, width=800, tread=220, risers=13, form=SPIRAL),
  WELL + [('FS-LINT-016', ['ST1'])])
n('stairs', 'spiral-turning-right', 'A spiral stair at 45 degrees turning right through 450 degrees - more than a '
  'full turn: its centre is 500 mm to its right, and its head is its foot turned clockwise about the centre by '
  '450 degrees: in the direction F(45000000) from it, 45 + 90 - 450 degrees taken in (-180, 180]. Both, and its box, '
  'are irrational and rounded once. Its width '
  'is exactly half its diameter, which 17.2.2 allows.', ['17.2.2', '17.4.3', '2.2.1'],
  hall_house(x0=1500, x1=4000, y1=2500, x=2500, y=1500, width=900, tread=220, risers=17,
             rotation=45_000_000, form={**SPIRAL, 'turn': 'right', 'diameter': 1800 * MM, 'sweep': 450_000_000}),
  WELL + [('FS-LINT-016', ['ST1'])])
d = hall_house(handrail={'height': 900 * MM, 'sides': 'both'}, rotation=0,
               form={'kind': 'straight'})
n('stairs', 'defaults-omitted', 'The straight stair written with every constant default - rotation 0, form '
  '{"kind": "straight"} and a handrail\'s sides "both": the canonical form omits all three, and keeps the handrail\'s '
  'height, which has no default.', ['9.2.1', '17.1.1'], d, WELL)

# ---- invalid stairs
n('stairs', 'to-own-level', 'A stair from L1 to L1. FS-INV-901; its rise and risers are not tested.', ['17.1.2', '10.3.1'],
  hall_house(to='L1', risers=1), [('FS-INV-901', ['ST1'])])
d = hall_house()
d['buildings']['B2'] = {}
d['levels']['L3'] = {'building': 'B2', 'elevation': 2700 * MM, 'height': 2700 * MM}
d['stairs']['ST1']['to'] = 'L3'
n('stairs', 'to-another-building', 'A stair from L1 of B1 to a level of B2 at the same elevation as L2: a stair\'s two '
  'levels are in one building. FS-INV-901.', ['17.1.2', '10.2.1'], d, [('FS-INV-901', ['ST1'])])
d = hall_house()
d['stairs']['ST1'].update(level='L2', to='L1', position=[1000 * MM, 2000 * MM])
n('stairs', 'to-a-level-below', 'A stair whose to is L1, below its level L2: its rise is -2700 mm. FS-INV-902.',
  ['17.4.1', '10.2.1'], d, [('FS-INV-902', ['ST1'])])
d = hall_house()
d['levels']['L2']['elevation'] = 0
n('stairs', 'rise-zero', 'L2 at L1\'s elevation: the stair\'s rise is exactly 0, which is not greater than zero. '
  'FS-INV-902, and FS-INV-903 is not evaluated for it.', ['17.4.1', '10.3.1'], d, [('FS-INV-902', ['ST1'])])
n('stairs', 'one-riser', 'A straight stair of 1 riser has no tread. FS-INV-903.', ['17.4.2'],
  hall_house(risers=1), [('FS-INV-903', ['ST1'])])
n('stairs', 'two-risers', 'A straight stair of 2 risers, each 1350 mm: valid - how tall a riser may be is a code\'s '
  'to say, not Core\'s - with one tread.', ['17.4.2', '17.5.1'], hall_house(risers=2), WELL)
n('stairs', 'max-riser-above-the-rise', 'A greatest riser taller than the whole rise: 1 riser is enough, and a '
  'straight stair of 1 riser does not fit its form. FS-INV-903.', ['17.4.2', '17.4.3'],
  hall_house(risers=None, maxRiser=3000 * MM), [('FS-INV-903', ['ST1'])])
n('stairs', 'l-first-flight-of-one', 'An L whose first flight is 1 riser: it has no tread before the landing. '
  'FS-INV-903.', ['17.4.2'], l_house(form={**L_FORM, 'risersBeforeTurn': 1}), [('FS-INV-903', ['ST1'])])
n('stairs', 'l-second-flight-of-one', 'An L of 14 risers with 13 before the turn: its second flight is 1 riser. '
  'FS-INV-903.', ['17.4.2'], l_house(form={**L_FORM, 'risersBeforeTurn': 13}), [('FS-INV-903', ['ST1'])])
n('stairs', 'u-flights-of-two', 'A U of 4 risers, 2 before the turn: each flight has one tread, which fits.',
  ['17.4.2'], hall_house(x0=1000, x1=3500, y1=2200, risers=4, form={**U_FORM, 'risersBeforeTurn': 2}), WELL)
n('stairs', 'winder-too-few-risers', 'A quarter-turn winder of 6 risers with 4 before the turn and 3 winders: '
  '4 + 3 is more than 6. FS-INV-903.', ['17.4.2'], hall_house(x0=1000, x1=2800, y1=2800, risers=6, form=WINDER_Q),
  [('FS-INV-903', ['ST1'])])
n('stairs', 'spiral-too-wide', 'A spiral stair 1800 mm across and 1000 mm wide: wider than its radius. FS-INV-904.',
  ['17.2.2'], hall_house(x0=1000, x1=3000, y1=2500, x=2000, y=1000, width=1000, risers=13, form=SPIRAL),
  [('FS-INV-904', ['ST1'])])
d = hall_house(risers=1)
d['rooms']['R2']['anchor'] = [3000 * MM, 0]
n('stairs', 'room-invariants-first', 'A stair of 1 riser to L2, where R2\'s anchor is on a wall\'s location line '
  '(FS-INV-201): the stair\'s rise is measured from the rooms\' floors, so FS-INV-902 and FS-INV-903 are not '
  'evaluated for it.', ['10.3.1'], d, [('FS-INV-201', ['R2'])])
d = hall_house()
d['stairs']['ST1']['to'] = 'L9'
n('stairs', 'to-unresolved', 'A stair whose to names no level: FS-INV-002, and no other invariant is evaluated.',
  ['3.2.1', '10.3.1'], d, [('FS-INV-002', ['ST1'])])


def sch(slug, description, covers, mut):
    d = hall_house()
    mut(d['stairs']['ST1'])
    n('stairs', slug, description, covers, d, SCH)


sch('risers-and-max-riser', 'A stair with both risers and maxRiser.', ['17.1.1'], lambda s: s.update(maxRiser=1))
sch('neither-risers-nor-max-riser', 'A stair with neither risers nor maxRiser.', ['17.1.1'], lambda s: s.pop('risers'))
sch('risers-zero', 'A stair of 0 risers: a riser count is from 1.', ['17.1.1'], lambda s: s.update(risers=0))
sch('width-zero', 'A stair 0 wide.', ['17.1.1'], lambda s: s.update(width=0))
sch('tread-missing', 'A stair without a tread.', ['17.1.1'], lambda s: s.pop('tread'))
sch('to-missing', 'A stair without to.', ['17.1.1'], lambda s: s.pop('to'))
sch('rotation-out-of-range', 'A rotation of -180000000: the range is (-180000000, 180000000].', ['17.1.1'],
    lambda s: s.update(rotation=-180_000_000))
sch('nosing-unknown', 'A stair has no "nosing" member in this draft.', ['17.1.1', '1.4.1'], lambda s: s.update(nosing=25 * MM))
sch('handrail-without-height', 'A handrail with sides and no height.', ['17.1.1'],
    lambda s: s.update(handrail={'sides': 'left'}))
sch('form-unknown', 'A "curved" stair: a form is one of five.', ['17.2.1'], lambda s: s.update(form={'kind': 'curved'}))
sch('l-without-turn', 'An L-shaped stair without its turn.', ['17.2.1'],
    lambda s: s.update(form={'kind': 'lShaped', 'risersBeforeTurn': 7}))
sch('l-with-gap', 'An L-shaped stair has no gap.', ['17.2.1'], lambda s: s.update(form={**L_FORM, 'gap': 0}))
sch('quarter-winder-with-gap', 'A quarter-turn winder stair has no gap.', ['17.2.1'],
    lambda s: s.update(form={**WINDER_Q, 'gap': 0}))
sch('winders-zero', 'A winder stair of 0 winders.', ['17.2.1'], lambda s: s.update(form={**WINDER_Q, 'winders': 0}))
sch('spiral-sweep-zero', 'A spiral stair that turns through 0.', ['17.2.1'], lambda s: s.update(form={**SPIRAL, 'sweep': 0}))
sch('u-gap-negative', 'A U-shaped stair with a gap of -1.', ['17.2.1'], lambda s: s.update(form={**U_FORM, 'gap': -1}))
d = copy.deepcopy(as_02('version-0.2-with-everything'))
d['stairs'] = {'ST1': {'level': next(iter(d['levels'])), 'to': next(iter(d['levels'])), 'position': [0, 0],
                       'width': 1, 'tread': 1, 'risers': 2}}
n('stairs', '0.2-document-with-stairs', 'A document that declares "0.2" and has a stairs collection, which 0.3 adds: '
  'Core 0.2\'s schema has none.', ['1.2.6', '1.1.2'], d, SCH)

# ---- circulation through a stair (14.1)
d = v3(cdoc(plan(2, 1, {'HALL': ((0, 0), 'circulation'), 'LIV': ((1, 0), 'living')}, doors=['H00', 'V10']),
            plan(2, 1, {'LOFT': ((0, 0), 'living'), 'BED': ((1, 0), 'sleeping')}, doors=['UV10'], level='L2', p='U'),
            levels=LEVELS2))
d['stairs'] = {'ST1': stair(x=500)}
n('circulation', 'stair-joins-two-levels', 'A hall with the front door on L1, and on L2 a loft - of function living, '
  'not circulation - with a bedroom off it. A stair rises from the hall to the loft: its foot room and its head room '
  'are linked, so the loft and the bedroom are reachable.', ['14.1.1', '14.3.1', '17.4.3'], d)
d = v3(cdoc(plan(2, 1, {'HALL': ((0, 0), 'circulation'), 'LIV': ((1, 0), 'living')}, doors=['H00', 'V10']),
            plan(2, 1, {'LAND': ((0, 0), 'circulation'), 'BED': ((1, 0), 'sleeping')}, windows=['UV10'], level='L2', p='U'),
            levels=LEVELS2))
d['stairs'] = {'ST1': stair(x=4500)}
n('circulation', 'stair-replaces-circulation-rooms', 'A hall on L1 and a landing on L2, both of function '
  'circulation, but the building\'s stair rises from the living room to the bedroom, and only a window joins the '
  'bedroom to the landing. A building with a stair is joined across its levels by its stairs alone: the bedroom is '
  'reachable, and the landing is not (FS-LINT-012), though both halls are circulation rooms.', ['14.1.1', '14.3.1'],
  d, [('FS-LINT-012', ['LAND'])])
d = v3(cdoc(plan(2, 1, {'HALL': ((0, 0), 'circulation'), 'LIV': ((1, 0), 'living')}, doors=['H00', 'V10']),
            plan(2, 1, {'LAND': ((0, 0), 'circulation'), 'BED': ((1, 0), 'sleeping')}, doors=['UV10'], level='L2', p='U'),
            levels=LEVELS2))
d['stairs'] = {'ST1': stair(x=750)}
n('circulation', 'stair-head-in-no-room', 'A stair from the hall whose head, at x = 4000 mm, is on the wall between '
  'the landing and the bedroom - in neither room: it joins nothing, and the building has a stair, so the two '
  'circulation rooms are not joined either. Both rooms on L2 are unreachable.', ['14.1.1', '17.4.3'],
  d, [('FS-LINT-012', ['BED']), ('FS-LINT-012', ['LAND'])])


# =================================================================================== options (0.3): chapter 19
# "optionSets" is a collection of 0.3: the reserved-member test names a near miss instead.
for tc in BASE:
    if tc['slug'] == 'reserved-top-level-member':
        tc['slug'] = 'near-miss-top-level-member'
        tc['inp'] = {('designOptions' if k == 'optionSets' else k): v for k, v in tc['inp'].items()}
        tc['description'] = ('A top-level member the table does not list - here "designOptions", which is not what '
                             'Core calls its option sets (19.1) - makes the document invalid.')

# The kitchen house: one level, 8 m x 4 m inside 100 mm walls drawn clockwise, its north and south walls
# split at x = 4 m and x = 5 m. Dining (DIN) is to the west, the kitchen (KIT) to the east, both common;
# a front door O1 in the west wall. Option set KS ("Kitchen"): option KA ("A: closed", primary) adds the
# wall WA at x = 5 m with the door OA in it; option KB ("B: open") instead adds the separator SB at
# x = 4 m and a window OB in the common north wall, over the sink.
KX, KY = 8000 * MM, 4000 * MM
DOOR19 = {'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM}
WIN19 = {'kind': 'windowType', 'width': 1200 * MM, 'height': 1200 * MM, 'sill': 900 * MM}


def kitchen(primary='KA'):
    js = {'J1': J(0, 0), 'J2': J(0, KY), 'J3': J(KX, KY), 'J4': J(KX, 0),
          'S4': J(4000 * MM, 0), 'S5': J(5000 * MM, 0), 'N4': J(4000 * MM, KY), 'N5': J(5000 * MM, KY)}
    ws = {'W1': W('J1', 'J2'), 'W2': W('J2', 'N4'), 'W3': W('N4', 'N5'), 'W4': W('N5', 'J3'),
          'W5': W('J3', 'J4'), 'W6': W('J4', 'S5'), 'W7': W('S5', 'S4'), 'W8': W('S4', 'J1'),
          'WA': W('S5', 'N5', option='KA')}
    d = v3(level_doc(junctions=js, walls=ws))
    d['separators'] = {'SB': {'level': 'L1', 'start': 'S4', 'end': 'N4', 'option': 'KB'}}
    d['types'].update(D=copy.deepcopy(DOOR19), G=copy.deepcopy(WIN19))
    d['openings'] = {'O1': {'wall': 'W1', 'offset': 1500 * MM, 'fill': 'D'},
                     'OA': {'wall': 'WA', 'offset': 1500 * MM, 'fill': 'D', 'option': 'KA'},
                     'OB': {'wall': 'W4', 'offset': 500 * MM, 'fill': 'G', 'option': 'KB'}}
    d['rooms'] = {'DIN': R(2000 * MM, 2000 * MM, function='dining', name='Dining'),
                  'KIT': R(6500 * MM, 2000 * MM, function='kitchen', name='Kitchen')}
    d['optionSets'] = {'KS': {'name': 'Kitchen', 'primary': primary}}
    d['options'] = {'KA': {'set': 'KS', 'name': 'A: closed'}, 'KB': {'set': 'KS', 'name': 'B: open'}}
    return d


def deck(d, primary='DA'):
    """A second set, DS ("Deck"): DA (primary) has a deck slab south of the house; DB has none."""
    d['optionSets']['DS'] = {'name': 'Deck', 'primary': primary}
    d['options'].update(DA={'set': 'DS', 'name': 'Deck'}, DB={'set': 'DS', 'name': 'No deck'})
    d['slabs'] = {'SL1': {'level': 'L1', 'boundary': [[0, -3000 * MM], [4000 * MM, -3000 * MM], [4000 * MM, -100 * MM],
                                                      [0, -100 * MM]], 'thickness': 150 * MM, 'purpose': 'deck',
                          'option': 'DA'}}
    return d


def pantry_wall(d, primary='PA'):
    """A third set, PS ("Pantry"): PA (primary) is empty; PB adds a freestanding wall PW in the dining room
    from x = 3 m to x = 4.5 m at y = 2 m - which crosses KB's separator, so no design has both."""
    d['optionSets']['PS'] = {'name': 'Pantry', 'primary': primary}
    d['options'].update(PA={'set': 'PS', 'name': 'None'}, PB={'set': 'PS', 'name': 'Pantry wall'})
    d['junctions'].update(PJ1=J(3000 * MM, 2000 * MM, option='PB'), PJ2=J(4500 * MM, 2000 * MM, option='PB'))
    d['walls']['PW'] = W('PJ1', 'PJ2', option='PB')
    return d


def island(d, option, x0, y0, side, p):
    """A closed square of separators, side x side, in an option (or common, option None): an unanchored face."""
    pts = [(x0, y0), (x0, y0 + side), (x0 + side, y0 + side), (x0 + side, y0)]
    for i, (x, y) in enumerate(pts, 1):
        d['junctions'][f'{p}J{i}'] = J(x, y, **({'option': option} if option else {}))
    for i in range(4):
        e = {'level': 'L1', 'start': f'{p}J{i + 1}', 'end': f'{p}J{(i + 1) % 4 + 1}'}
        if option:
            e['option'] = option
        d['separators'][f'{p}S{i + 1}'] = e
    return d


n('options', 'kitchen-a-and-b', 'The kitchen house with two kitchen options: A, primary, closes the kitchen off with a '
  'wall and a door at x = 5 m; B opens it to the dining room with a separator at x = 4 m and adds a window over the '
  'sink. Valid: the primary design, A, and B\'s option design are both valid. What is derived is the primary '
  'design - WA, OA and the rooms either side of WA, and no SB or OB - and `options` gives, for each option, its '
  'members, the rooms of its design with their areas, and what in the primary design differs in it: the two rooms, '
  'their floors and ceilings, and the walls WA met. The window type G is used only by B\'s window, and is used: '
  'FS-LINT-006 is of the document, not of a design.',
  ['19.1.1', '19.1.2', '19.2.1', '19.3.1', '19.4.1', '19.5.1', '19.6.1', '19.6.3', '9.2.1'], kitchen())
n('options', 'derive-design-b', 'The kitchen house, deriving the design {"KS": "KB"} (design.json): the separator SB '
  'and the window OB, the open kitchen 3950 mm wide and the dining room as wide - and no WA, OA or junction fill at '
  'S5. Validity and the diagnostics do not depend on the design; `options` is the same, but for `chosen`.',
  ['19.6.1', '19.3.1', '19.6.3'], kitchen(), design={'KS': 'KB'})
n('options', 'derive-design-a-by-name', 'The kitchen house, deriving {"KS": "KA"}: the primary design, named.',
  ['19.6.1'], kitchen(), design={'KS': 'KA'})
n('options', 'derive-empty-design', 'The kitchen house with the design input {}: a set the input does not name takes '
  'its primary, so this is the primary design.', ['19.6.1'], kitchen(), design={})
n('options', 'primary-switched', 'The kitchen house with B as the primary option: B\'s design is what is derived, '
  'A\'s is the option design checked beside it, and `options` compares A with B - so A\'s `affected` names the rooms '
  'and walls, and B\'s is empty.', ['19.1.2', '19.6.1', '19.6.3', '19.5.1'], kitchen('KB'))
d = kitchen()
d['optionSets']['KS']['extras'] = {}
d['options']['KB']['extras'] = {}
d['options']['KA']['extras'] = {'colour': 'blue'}
n('options', 'defaults-omitted', 'An option set and an option with empty extras, which the canonical form omits; '
  'an option\'s own extras are kept, and every element\'s option is kept: it has no default.', ['9.2.1', '19.1.1'], d)
n('options', 'two-option-sets', 'The kitchen house with a second set, Deck: DA (primary) has a deck slab, DB has '
  'none - an empty option is an alternative too. The checked designs are the primary design (KA, DA), KB\'s (KB, DA) '
  'and DB\'s (KA, DB); the slab is derived in the primary design, and DB\'s `rooms` are the primary design\'s.',
  ['19.5.1', '19.6.3', '19.3.1'], deck(kitchen()))
n('options', 'unchecked-design', 'The kitchen house with the Deck set, deriving {"KS": "KB", "DS": "DB"}: a design '
  'that chooses non-primary options of two sets is not one of the checked designs, but its view is valid, so it is '
  'derived - the open kitchen, and no deck.', ['19.6.1', '19.6.2', '19.5.1'], deck(kitchen()),
  design={'KS': 'KB', 'DS': 'DB'})
n('options', 'unchecked-design-not-valid', 'The kitchen house with the Pantry set, whose option PB adds a wall in the '
  'dining room that would cross KB\'s separator. The document is valid - PB is checked against KA, the primary, and '
  'KB against PA - but the design {"KS": "KB", "PS": "PB"} has the two crossing: its view is not valid, and nothing '
  'is derived for it.', ['19.6.2', '19.5.1'], pantry_wall(kitchen()), design={'KS': 'KB', 'PS': 'PB'})
n('options', 'design-names-no-set', 'The kitchen house with the design input {"Kitchen": "KB"}: no option set has '
  'the ID "Kitchen" (it is KS\'s name), so nothing is derived.', ['19.6.2'], kitchen(), design={'Kitchen': 'KB'})
n('options', 'design-option-of-another-set', 'The kitchen and deck house with the design input {"KS": "DB"}: DB is '
  'an option of the Deck set, not of the Kitchen set, so nothing is derived.', ['19.6.2'], deck(kitchen()),
  design={'KS': 'DB'})
n('options', 'design-without-options', 'A document with no option set and the design input {}: its one design, the '
  'document itself, is derived exactly as it is with no design input.', ['19.6.1', '19.3.1'], room_doc(), design={})
n('options', 'design-for-a-document-without-options', 'A document with no option set and a design input that names '
  'a set: nothing is derived.', ['19.6.2'], room_doc(), design={'KS': 'KB'})

# ---- invalid: option invariants and references
d = deck(kitchen())
d['optionSets']['KS']['primary'] = 'DA'
n('options', 'primary-of-another-set', 'The Kitchen set\'s primary is DA, an option of the Deck set: FS-INV-1101 '
  'names the set and the option, and no design is evaluated.', ['19.1.2', '10.2.1', '10.3.1'], d,
  [('FS-INV-1101', ['KS', 'DA'])])
d = kitchen()
d['optionSets']['KS']['primary'] = 'KC'
n('options', 'primary-unresolved', 'A set whose primary names no option: FS-INV-002.', ['3.2.1', '19.1.2'], d,
  [('FS-INV-002', ['KS'])])
d = kitchen()
d['options']['KC'] = {'set': 'NOPE'}
n('options', 'option-set-unresolved', 'An option whose set names no option set: FS-INV-002.', ['3.2.1'], d,
  [('FS-INV-002', ['KC'])])
d = kitchen()
d['walls']['WA']['option'] = 'KZ'
n('options', 'option-unresolved', 'A wall whose option names no option: FS-INV-002.', ['3.2.1', '19.2.1'], d,
  [('FS-INV-002', ['WA'])])
d = kitchen()
d['options']['W1'] = d['options'].pop('KB')
for c in ('separators', 'openings'):
    for e in d[c].values():
        if e.get('option') == 'KB':
            e['option'] = 'W1'
n('options', 'option-id-of-a-wall', 'An option whose ID, W1, is a wall\'s too: IDs are unique across collections, '
  'option sets and options included. FS-INV-001.', ['3.1.2'], d, [('FS-INV-001', ['W1'])])
d = kitchen()
del d['openings']['OA']['option']
n('options', 'common-opening-in-an-option-wall', 'The door OA is common, but the wall it is in, WA, is only in option '
  'A: B\'s design would have a door in no wall. FS-INV-1102 names both.', ['19.4.1', '10.2.1'], d,
  [('FS-INV-1102', ['OA', 'WA'])])
d = kitchen()
d['openings']['OB']['wall'] = 'WA'
d['openings']['OB']['offset'] = 300 * MM
n('options', 'option-b-opening-in-an-option-a-wall', 'B\'s window in A\'s wall: no design has both. FS-INV-1102.',
  ['19.4.1'], d, [('FS-INV-1102', ['OB', 'WA'])])
d = kitchen()
d['junctions']['S4']['option'] = 'KB'
n('options', 'common-walls-at-an-option-junction', 'The junction S4 is in option B, and the common walls W7 and W8 end '
  'at it: FS-INV-1102 once for each, and for SB, which is in B too, nothing.', ['19.4.1'], d,
  [('FS-INV-1102', ['W7', 'S4']), ('FS-INV-1102', ['W8', 'S4'])])
d = pantry_wall(kitchen())
d['openings']['OX'] = {'wall': 'PW', 'offset': 200 * MM, 'width': 800 * MM, 'height': 2000 * MM, 'option': 'KB'}
n('options', 'reference-into-another-set', 'An opening of kitchen option B in the pantry wall of option PB of another '
  'set: a design may choose B without PB, so FS-INV-1102.', ['19.4.1'], d, [('FS-INV-1102', ['OX', 'PW'])])
d = with_elements(kitchen(), {'F1': element(host=wall_face('WA', 'right', 500 * MM, 0), **PIECE)})
n('options', 'common-element-hosted-on-an-option-wall', 'A common extension element hosted on the face of A\'s wall '
  'WA: its host reference crosses into an option. FS-INV-1102.', ['19.4.1', '19.2.1'], d,
  [('FS-INV-1102', ['F1', 'WA'])])
d = kitchen()
del d['openings']['OA']['option']
d['openings']['O1']['fill'] = 'NOPE'
n('options', 'reference-invariants-first', 'An opening filled by a type that does not exist, and a common door in '
  'A\'s wall: reference invariants are evaluated first, so only FS-INV-002.', ['10.3.1'], d, [('FS-INV-002', ['O1'])])
d = kitchen()
del d['openings']['OA']['option']
d['rooms']['PANTRY'] = R(4500 * MM, 2000 * MM, option='KB')
n('options', 'option-invariants-before-designs', 'A common door in A\'s wall, and a pantry room in B that shares B\'s '
  'kitchen face with KIT: once an option invariant is reported no design is evaluated, so only FS-INV-1102.',
  ['10.3.1'], d, [('FS-INV-1102', ['OA', 'WA'])])

# ---- invalid: designs
d = kitchen()
d['rooms']['PANTRY'] = R(4500 * MM, 2000 * MM, option='KB', name='Pantry')
n('options', 'error-in-an-option-design', 'A pantry room in option B anchored at x = 4.5 m. B\'s design has the open '
  'kitchen\'s face from x = 4 m to 8 m, where KIT\'s anchor is too: FS-INV-202, found in B\'s design only, and '
  'reported with "design": "KB".',
  ['19.5.1', '19.5.2', '10.2.1'], d, [('FS-INV-202', ['KIT', 'PANTRY'], 'KB')])
d = kitchen()
d['rooms']['PANTRY'] = R(4500 * MM, 2000 * MM, option='KB', name='Pantry')
d['openings']['O1']['offset'] = 3500 * MM
n('options', 'error-in-every-design', 'The pantry of the last test, and the front door moved to 3500 mm along its '
  '4 m wall, so it runs past the wall\'s end in every design: FS-INV-302 is reported once, without design, and '
  'FS-INV-202 with "design": "KB".', ['19.5.2', '10.2.1'], d,
  [('FS-INV-202', ['KIT', 'PANTRY'], 'KB'), ('FS-INV-302', ['O1'])])
d = kitchen()
d['openings']['OA']['offset'] = 3500 * MM
n('options', 'error-in-the-primary-design', 'A\'s door runs past the end of A\'s wall: found in the primary design '
  'only, and reported as it is, without design.', ['19.5.1', '19.5.2'], d, [('FS-INV-302', ['OA'])])
d = kitchen('KB')
d['openings']['OA']['offset'] = 3500 * MM
n('options', 'error-in-a-non-primary-option', 'The same door, with B primary: A is checked against it, and the error '
  'is A\'s design\'s, so it carries "design": "KA" and the document is invalid.', ['19.5.1', '19.5.2'], d,
  [('FS-INV-302', ['OA'], 'KA')])

# ---- lints
d = island(kitchen(), 'KB', 6800 * MM, 500 * MM, 800 * MM, 'I')
n('options', 'lint-in-an-option-design', 'Option B also draws an island of separators in the kitchen: in B\'s design '
  'the island is an unanchored face, FS-LINT-003, reported with "design": "KB"; the kitchen\'s polygon has a hole '
  'there in B\'s design only.', ['19.5.2', '6.6.1'], d, [('FS-LINT-003', [], 'KB')])
d = island(island(kitchen(), 'KB', 6800 * MM, 500 * MM, 800 * MM, 'I'), None, 1000 * MM, 1000 * MM, 500 * MM, 'C')
n('options', 'lints-counted-against-the-primary', 'B\'s island, and a common square of separators in the dining room: '
  'the primary design has one unanchored face and B\'s design two. The primary design\'s is reported without design, '
  'and B\'s design reports one more, with "design": "KB".', ['19.5.2'], d,
  [('FS-LINT-003', []), ('FS-LINT-003', [], 'KB')])
d = kitchen()
d['types']['G2'] = copy.deepcopy(WIN19)
n('options', 'unused-type-once', 'A window type nothing uses: FS-LINT-006 is of the document, so it is reported once, '
  'without design.', ['19.5.2'], d, unused('G2'))
d = kitchen()
d['optionSets']['DS'] = {'name': 'Deck', 'primary': 'DA'}
d['options']['DA'] = {'set': 'DS', 'name': 'Deck'}
n('options', 'option-set-with-one-option', 'A Deck set whose only option is DA, primary: valid, with FS-LINT-017 - '
  'there is nothing to choose between.', ['19.8.1'], d, [('FS-LINT-017', ['DS'])])

# ---- extension elements in options
# A fridge 900 mm wide and 750 mm deep, its frame's origin at the middle of its front, its body behind it (-y)
# and the space its door needs, 900 mm deep, in front of it (+y).
FRIDGE = dict(size=(900 * MM, 750 * MM, 1800 * MM), origin=(-450 * MM, -750 * MM, 0),
              clearances={'door': {'purpose': 'access', 'shape': 'box', 'min': [-450 * MM, 0, 0],
                                   'max': [450 * MM, 900 * MM, 1800 * MM]}})
d = with_elements(kitchen(), {
    'FA': element(host=free(7200 * MM, 2500 * MM, 90_000_000), option='KA', **FRIDGE),
    'FB': element(host=free(7450 * MM, 3200 * MM, 180_000_000), option='KB', **FRIDGE)})
n('options', 'fridge-in-each-option', 'A fridge in each kitchen option, each with the clearance its door needs: A\'s '
  'stands against the east wall, B\'s against the north wall. Only A\'s is derived - its fallback, placement and '
  'clearance - and each option\'s members name its fridge.', ['19.2.1', '19.3.1', '19.6.3', '12.6.2', '13.5.2'], d)
n('options', 'fridge-in-design-b', 'The fridges, deriving B\'s design: B\'s fridge, and not A\'s.',
  ['19.3.1', '19.6.1', '12.6.2'], d, design={'KS': 'KB'})

# ---- schema
def osch(slug, description, covers, mut, inp=None):
    d = copy.deepcopy(inp) if inp is not None else kitchen()
    mut(d)
    n('options', slug, description, covers, d, SCH)


osch('option-on-a-level', 'A level in an option: levels are not.', ['19.2.1'],
     lambda d: d['levels']['L1'].update(option='KA'))
osch('option-on-a-type', 'A type in an option: types are a library, not an alternative.', ['19.2.1'],
     lambda d: d['types']['D'].update(option='KA'))
osch('option-on-a-building', 'A building in an option.', ['19.2.1'], lambda d: d['buildings']['B1'].update(option='KA'))
osch('option-on-a-program-item', 'A program item in an option: the program is every design\'s brief.', ['19.2.1'],
     lambda d: d.update(program={'items': {'P1': {'function': 'kitchen', 'option': 'KA'}}}))
osch('option-on-an-option', 'An option in an option: options are not nested.', ['19.2.1'],
     lambda d: d['options']['KB'].update(option='KA'))
osch('option-on-an-option-set', 'An option set in an option.', ['19.2.1'],
     lambda d: d['optionSets']['KS'].update(option='KA'))
osch('option-not-an-id', 'An element\'s option that is a number, not a reference.', ['3.2.3', '19.2.1'],
     lambda d: d['walls']['WA'].update(option=1))
osch('option-set-without-primary', 'An option set with no primary.', ['19.1.1'],
     lambda d: d['optionSets']['KS'].pop('primary'))
osch('option-without-set', 'An option of no set.', ['19.1.1'], lambda d: d['options']['KB'].pop('set'))
osch('option-unknown-member', 'An option with an "order" member, which its table does not have.', ['19.1.1', '1.4.1'],
     lambda d: d['options']['KB'].update(order=2))
osch('option-set-options-member', 'An option set that lists its options: a set\'s options are the options that name '
     'it, and a set has no "options" member.', ['19.1.1', '1.4.1'],
     lambda d: d['optionSets']['KS'].update(options=['KA', 'KB']))
d = copy.deepcopy(as_02('version-0.2-with-everything'))
d['optionSets'] = {'KS': {'primary': 'KA'}}
d['options'] = {'KA': {'set': 'KS'}}
n('options', '0.2-document-with-option-sets', 'A document that declares "0.2" with option sets and options, which 0.3 '
  'adds: Core 0.2\'s schema has neither.', ['1.2.6', '1.1.2'], d, SCH)

# ---- examples
d = with_elements(kitchen(), {
    'FA': element(host=free(7200 * MM, 2500 * MM, 90_000_000), option='KA', **FRIDGE),
    'FB': element(host=free(7450 * MM, 3200 * MM, 180_000_000), option='KB', **FRIDGE)})
d = deck(d)
n('examples', 'kitchen-options', 'The Phase 8 exit demo\'s house: kitchen option A, closed off with a door, and B, '
  'open to the dining room with a window over the sink, each with its fridge and the clearance its door needs; and a '
  'deck, or none. The primary design is derived; `options` sets A and B side by side - each one\'s rooms and their '
  'areas, and what in the common plan changes between them.', ['19.6.1', '19.6.3', '19.5.1'], d)

# The three-room house of examples/001, built from the US starter library (library/us-starter/0.1.0): its
# hand-written wall, door and window types replaced by the library's, embedded with their materials and their
# source exactly as the library publishes them, and its openings filled by them.
house = json.loads(next(tc for tc in BASE if tc['slug'] == 'three-room-house')['raw'])
house['project'] = {'name': 'Three-room house, from the US starter library'}
house.pop('extras')
LIBRARY_TYPES = {'EXT26': 'wall-2x6-exterior-fibre-cement', 'INT24': 'wall-2x4-interior',
                 'D36': 'door-exterior-swing-36x80', 'D32': 'door-interior-swing-32x80'}
for w in house['walls'].values():
    w['type'] = LIBRARY_TYPES[w['type']]
for oid, fill in {'FD': 'door-exterior-swing-36x80', 'BD': 'door-interior-swing-32x80', 'LW1': 'window-double-hung-36x60',
                  'LW2': 'window-fixed-72x48', 'KW': 'window-slider-48x36', 'BW': 'window-casement-30x60'}.items():
    house['openings'][oid]['fill'] = fill
del house['openings']['LW2']['width']                 # the picture window is the library's 72 x 48 fixed window
del house['openings']['BW']['swing']                  # a window has no swing
house['types'] = {}
house['materials'] = {k: v for k, v in house['materials'].items() if k in ('PAINT', 'OAK', 'TILE')}
house = us_library.embed(house, 'wall-2x6-exterior-fibre-cement', 'wall-2x4-interior', 'door-exterior-swing-36x80',
                         'door-interior-swing-32x80', 'window-double-hung-36x60', 'window-fixed-72x48',
                         'window-slider-48x36', 'window-casement-30x60')
n('examples', 'three-room-house-from-the-library', 'The three-room house of examples/001, built from the US starter '
  'library 0.1.0 (library/us-starter): 2x6 exterior walls with fibre-cement siding and 2x4 partitions, a 36-inch '
  'exterior door and a 32-inch interior door, a double-hung, a fixed picture, a sliding and a casement window. Every '
  'type and every material its layers use is embedded exactly as the library publishes it, with its source, so the '
  'document is complete on its own: the walls are as thick as the library\'s layers, each door and window is its '
  'rough opening at the library\'s sill, and each clear opening is the library\'s generic declared value - a fixed '
  'window has none. The room finishes stay the project\'s own materials.',
  ['8.1.3', '8.2.1', '7.4.2', '13.5.2', '9.2.1', '9.3.1'], house)

NEW = list(TESTS)
del TESTS[:]


def main(argv) -> int:
    tests = BASE + NEW
    return 1 if write_all(prune='--prune' in argv, tests=tests, suite=SUITE03, reader=READER_03) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

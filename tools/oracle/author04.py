"""The conformance suite of Floorspec Core 0.4, as the script that writes it.

    python3.13 -m tools.oracle.author04            rewrite every test from its declaration below
    python3.13 -m tools.oracle.author04 --prune    ...and delete test directories no longer declared

The suite is the Core 0.3 suite, re-targeted to 0.4 - every 0.3 test, in the same group under the
same number, its document declaring "0.4" where it declared "0.3" (a document that declares "0.1" or
"0.2" stays one: it shows a 0.4 reader reading it, 1.2.8; and the starter templates, which are 0.3
files byte for byte, stay 0.3 files), and covering the 0.4 IDs of the statements 0.4 retired - followed
by the tests of what 0.4 adds: the tapered treads of winder and spiral stairs (17.7) - their steps,
walkline, goings and headroom - a winder's newel, and the opening a stair with a minHeadroom needs
(17.6). A 0.4 reader derives the steps of every winder and spiral stair, so the four 0.3 tests of
those stairs gain their steps, run, walkline, goings and headroom, and FS-LINT-016 gives way to
FS-LINT-018 for treads that narrow to a point; every other test's expected values are the 0.3 suite's.
Every expected diagnostic is written by hand and cross-checked against the oracle, read as a Core 0.4
reader (validate.READER_04); geometry, hashes and canonical forms come from the oracle. Afterwards,
`python3.13 -m tools.oracle.regenerate` re-verifies the suite from the files alone. Add new tests at
the end of their group's section.
"""
import copy
import os
import re
import sys

import tools.oracle.author03 as v03                    # declares the 0.3 suite: v03.BASE + v03.NEW
import tools.oracle.author04_roofs as roofs04          # roofs (16.4, 16.5): the weighted straight skeleton
from tools.oracle.author03 import (HALLS, L_FORM, LEVELS2, SPIRAL, U_FORM, WELL, WINDER_Q, Draw, hall_house, lower,
                                   stair, storeys, upper)
from tools.oracle.author_lib import MM, REPO, TESTS, _diag, cov, t, write_all
from tools.oracle.validate import READER_04

SUITE04 = os.path.join(REPO, 'conformance', 'core', '0.4')
SCH = [('FS-SCH-001', [])]

# ============================================================================= the 0.3 suite, re-targeted

RETIRED = {'FS-CORE-1.2.5': 'FS-CORE-1.2.7', 'FS-CORE-1.2.6': 'FS-CORE-1.2.8', 'FS-CORE-17.7.1': 'FS-CORE-17.7.3',
           'FS-CORE-17.7.2': None, **roofs04.RETIRED}
VERSION_TESTS = {
    # slug: (new floorspec value, new description)
    'version-is-a-number': (0.4, '"floorspec": 0.4 is a number, not the string "0.4". FS-DOC-001 applies only to a '
                                 'string naming another version, so this is a schema error.'),
    'version-with-patch': ('0.4.0', '"0.4.0" is not "0.4": patch releases are not declared. A reader that implements '
                                    '0.1, 0.2, 0.3 and 0.4 rejects it with FS-DOC-001.'),
    'unknown-version': ('0.5', 'A reader that implements 0.1, 0.2, 0.3 and 0.4 rejects a document declaring 0.5 with '
                               'FS-DOC-001, whatever else the document contains.'),
    'document-error-stops-schema': ('0.5', None),
}
SLUGS = {
    'collections-checked-in-0.3': 'collections-checked-in-0.4',
    'version-0.3-with-0.2-members': 'version-0.4-with-0.2-members',
    'version-0.3-with-everything': 'version-0.4-with-0.3-members',
}
ADDED = [('which 0.3 adds', 'which 0.3 added'), ('a member 0.3 adds', 'a member 0.3 added'),
         ('a collection 0.3 adds', 'a collection 0.3 added')]
DESCRIPTIONS = {
    # slug: [(text of the 0.3 description, its 0.4 wording)] where the words name a draft
    'read-0.1-document': [('a reader of 0.3', 'a reader of 0.4')],
    '0.1-collections-are-opaque': [('malformed in 0.2 and 0.3', 'malformed in 0.2, 0.3 and 0.4')],
    'collections-checked-in-0.3': [('in a 0.3 document', 'in a 0.4 document')],
    'version-0.3-with-0.2-members': [('A 0.3 document using every member 0.2 added', 'A 0.4 document using every member 0.2 added')],
    'read-0.1-document-circulation': [('a reader of 0.3: circulation needs no member 0.2 or 0.3 adds',
                                       'a reader of 0.4: circulation needs no member 0.2, 0.3 or 0.4 adds')],
    'known-extensions-and-a-0.1-document': [('a 0.3 reader applies 12.3', 'a 0.4 reader applies 12.3')],
    'read-0.2-document': [('read by a reader of 0.3', 'read by a reader of 0.4')],
    'version-0.3-with-everything': [('A 0.3 document using every member 0.3 adds', 'A 0.4 document using every member 0.3 added')],
    'read-0.2-surface-hosts': [('read by a reader of 0.3', 'read by a reader of 0.4')],
    'read-0.1-finishes': [('read by a reader of 0.3', 'read by a reader of 0.4')],
    '0.2-document-with-clear-opening': ADDED, '0.2-document-with-operation': ADDED,
    '0.2-document-with-opening-clear-opening': ADDED, '0.2-document-with-source': ADDED,
    '0.2-document-with-a-ceiling': ADDED, '0.2-document-with-a-ceiling-height': ADDED,
    '0.2-document-with-a-slab-purpose': ADDED, '0.2-document-with-finishes': ADDED, '0.1-document-with-roughness': ADDED,
    '0.2-document-with-a-roof': ADDED, '0.2-document-with-stairs': ADDED, '0.2-document-with-option-sets': ADDED,
}
L18 = [('FS-LINT-018', ['ST1'])]
# The four 0.3 tests of the stairs 0.3 did not step: under 0.4 they derive their steps, run, walkline, goings and
# headroom (17.7.3), and FS-LINT-016 gives way to FS-LINT-018 where the treads narrow to a point.
STEPPED = {
    'winder-quarter': (
        'A quarter-turn winder stair: 4 risers east, 3 winders in the 900 mm square at the turn, and 7 straight treads '
        'north, to its head at (2200 mm, 2800 mm). It has no newel, so its winders are 30 degrees each about the inner '
        'corner of the turn, (1750 mm, 1050 mm): their nosing lines meet the outer sides at 900 tan 30 mm, and their '
        'narrow ends have no depth (FS-LINT-018). Its walkline runs 450 mm from that corner, so each winder\'s going '
        'there is 900 sin 15 mm, and its length is 10 x 250 mm plus a quarter of the circle, rounded once. The well '
        'covers it, so it has no headroom.',
        ['17.1.1', '17.2.1', '17.4.3', '17.7.3', '10.2.1'], WELL + L18),
    'winder-half': (
        'A half-turn winder stair turning left with a 100 mm gap and no newel: 4 risers east from (1000 mm, 600 mm), '
        '6 winders of 30 degrees about the middle of the gap\'s side, then 5 straight treads west to its head at '
        '(500 mm, 1600 mm). Its walkline\'s arc has a radius of 500 mm - half the width and the gap - and its box spans '
        'x = 500 mm to 2650 mm and y = 150 mm to 2050 mm. FS-LINT-018.',
        ['17.2.1', '17.4.3', '17.7.3'], WELL + L18),
    'spiral': (
        'A spiral stair 1800 mm across, 800 mm wide, turning left through 270 degrees from its first nosing line at '
        '(2000 mm, 1000 mm): its centre is 500 mm to the left, at (2000 mm, 1500 mm), and its head is turned 270 '
        'degrees about it, to (1500 mm, 1500 mm), in the well. Its 12 treads each turn 22.5 degrees, from its column of '
        '100 mm radius out to its 900 mm edge; their going on the walkline, 500 mm from the centre, is 1000 sin 11.25 '
        'mm, and at the column 200 sin 11.25 mm. Its walkline is three quarters of a circle of 500 mm.',
        ['17.2.1', '17.4.3', '17.7.3'], WELL),
    'spiral-turning-right': (
        'A spiral stair at 45 degrees turning right through 450 degrees - more than a full turn: its centre is 500 mm '
        'to its right, and its head is its foot turned clockwise about the centre by 450 degrees: in the direction '
        'F(45000000) from it, 45 + 90 - 450 degrees taken in (-180, 180]. Both, its box, and the corners of its treads, '
        'are irrational and rounded once. Its width is exactly half its diameter, which 17.2.2 allows: it has no column, '
        'its treads meet at its centre, and their narrow ends have no depth (FS-LINT-018).',
        ['17.2.2', '17.4.3', '17.7.3', '2.2.1'], WELL + L18),
}
_RAW_VERSION = re.compile(rb'("floorspec"\s*:\s*)"0\.3"')
_STATEMENTS = [('1.2.5', '1.2.7'), ('1.2.6', '1.2.8')]


def retarget(tc):
    tc = copy.deepcopy(tc)
    slug = tc['slug']
    tc['covers'] = [c for c in (RETIRED.get(c, c) for c in tc['covers']) if c is not None]
    for old, new in DESCRIPTIONS.get(slug, []):
        if old in tc['description']:
            tc['description'] = tc['description'].replace(old, new)
    for old, new in _STATEMENTS:
        tc['description'] = tc['description'].replace(f'({old})', f'({new})').replace(f'{old})', f'{new})')
    if slug in VERSION_TESTS:
        value, description = VERSION_TESTS[slug]
        tc['inp']['floorspec'] = value
        tc['description'] = description or tc['description']
    elif isinstance(tc['inp'], dict) and tc['inp'].get('floorspec') == '0.3':
        tc['inp']['floorspec'] = '0.4'
    if tc['raw'] is not None and not slug.endswith('-template'):
        tc['raw'] = _RAW_VERSION.sub(rb'\1"0.4"', tc['raw'])
    if tc['group'] == 'stairs' and slug in STEPPED:
        description, covers, diags = STEPPED[slug]
        tc['description'], tc['covers'], tc['diags'] = description, cov(*covers), [_diag(*x) for x in diags]
    tc['slug'] = SLUGS.get(slug, slug)
    return roofs04.retarget(tc)


SUITE03 = v03.BASE + v03.NEW
BASE = [retarget(tc) for tc in SUITE03]
del TESTS[:]


def as_03(slug, group='stairs'):
    """The input of a 0.3 test exactly as the 0.3 suite has it."""
    return copy.deepcopy(next(tc for tc in SUITE03 if tc['slug'] == slug and tc['group'] == group)['inp'])


# ============================================================================= helpers

def v4(d):
    d = copy.deepcopy(d)
    d['floorspec'] = '0.4'
    return d


def n(group, slug, description, covers, inp, diags=(), **kw):
    """Declares a new 0.4 test; a document given as a dict declares "0.4" unless it says otherwise."""
    t(group, slug, description, covers, inp, diags, **kw)


def house(**kw):
    return v4(hall_house(**kw))


# =================================================================================== model (0.4)
n('model', 'read-0.3-document', 'The 0.3 suite\'s quarter-turn winder stair (stairs/014 of conformance/core/0.3), '
  'exactly as it is there, declaring "0.3", read by a reader of 0.4: valid, with the same hash and canonical form, and '
  'every value 0.3 derives for it; and, as 0.4 derives them for a stair of any draft, its winders, walkline, goings '
  'and headroom. A 0.3 reader reports FS-LINT-016 for the winder stair; a 0.4 reader derives its steps, and reports '
  'FS-LINT-018 for winders that narrow to a point.',
  ['1.2.2', '1.2.8', '9.2.1', '9.3.1', '17.7.3'], as_03('winder-quarter'), WELL + L18)
d = as_03('winder-quarter')
d['stairs']['ST1']['form'] = {**WINDER_Q, 'newel': 100 * MM}
n('model', '0.3-document-with-newel', 'A document that declares "0.3" and whose winder stair has a newel, which 0.4 '
  'adds: it is checked against Core 0.3\'s schema, which has no "newel" member.', ['1.2.8'], d, SCH)
d = as_03('straight-stair')
d['stairs']['ST1']['minHeadroom'] = 2000 * MM
n('model', '0.3-document-with-min-headroom', 'A 0.3 document whose stair declares the headroom it is designed for: '
  '"minHeadroom" is a member 0.4 adds.', ['1.2.8'], d, SCH)
n('model', 'version-0.4-with-everything', 'A 0.4 document using every member 0.4 adds - a winder stair with a newel '
  'and a stair that declares its minHeadroom - valid; neither has a constant default, so the canonical form keeps both.',
  ['1.2.7', '9.2.1', '17.1.3', '17.2.3'],
  house(x0=1000, x1=2800, y1=2800, form={**WINDER_Q, 'newel': 100 * MM}, minHeadroom=2000 * MM), WELL)

# =================================================================================== stairs (0.4): 17.6, 17.7
# The standard stair rises east from (1000 mm, 600 mm), 900 mm wide, with 250 mm treads (author03). A quarter turn's
# square is from x = 1750 mm to 2650 mm; its pivot, the inner corner of the turn, is at (1750 mm, 1050 mm).
NEWEL = 100 * MM
WQN = {**WINDER_Q, 'newel': NEWEL}
WH = {'kind': 'winder', 'turn': 'left', 'angle': 'half', 'risersBeforeTurn': 4, 'winders': 6, 'gap': 100 * MM}

n('stairs', 'winder-with-newel', 'The quarter-turn winder stair with a 100 mm newel at the inner corner of its turn: '
  'the newel occupies x = 1750 mm to 1850 mm, y = 950 mm to 1050 mm, and the winders\' nosing lines start on its faces. '
  'The first and the last winder are each a quadrilateral whose narrow end is 100 tan 30 mm deep along the newel; the '
  'middle one wraps the outer corner of the square, and its narrow end, from one face of the newel to the other, '
  'is 100 (1 - tan 30) sqrt 2 mm - deeper than the others. The stair\'s narrowGoing is the least, and nothing narrows '
  'to a point, so there is no FS-LINT-018. The walkline, 450 mm from the pivot, is outside the newel (17.7.4).',
  ['17.2.3', '17.7.3', '17.7.4'], house(x0=1000, x1=2800, y1=2800, form=WQN), WELL)
n('stairs', 'winder-turning-right-rotated', 'A quarter-turn winder stair with a newel that rises at 30 degrees and '
  'turns right: in its frame the mirror image of a left turn, its pivot on its right. Its frame faces F(30000000), so '
  'every corner of its winders, every walkline point and its head are irrational, each rounded once; the goings are '
  'distances in its frame, the same as the left turn\'s.',
  ['17.7.3', '2.2.1'],
  storeys(Draw('L1', 'D').walls((0, 0), (0, 6000), (8000, 6000), (8000, 0), (0, 0)),
          rooms={'R1': ('L1', 6000, 5000, {})},
          stairs={'ST1': stair(x=2000, y=3000, rotation=30_000_000, form={**WQN, 'turn': 'right'})},
          levels=LEVELS2) | {'floorspec': '0.4'})
n('stairs', 'winder-half-with-newel', 'A half-turn winder stair with a 100 mm gap and a 50 mm newel along the gap\'s '
  'side, from y = 1000 mm to 1200 mm: its six winders of 30 degrees radiate from the middle of that side, the first and '
  'last nosing lines start at the newel\'s two ends, and the winders around the two outer corners of the turn wrap '
  'them. The walkline\'s arc, 500 mm from the pivot, crosses each nosing line beyond the newel.',
  ['17.2.3', '17.7.3', '17.7.4'], house(x0=400, x1=2800, y1=2100, risers=15, form={**WH, 'newel': 50 * MM}), WELL)
n('stairs', 'two-winders', 'A quarter turn on two winders of 45 degrees: the nosing line between them runs from the '
  'pivot through the outer corner of the turn, so neither winder has the corner strictly inside it - each is a '
  'triangle.', ['17.7.3'],
  house(x0=1000, x1=2800, y1=2800, risers=13, form={**WINDER_Q, 'winders': 2}), WELL + L18)
n('stairs', 'one-winder', 'A quarter turn on one winder: a single tread from the first nosing line round to the '
  'second, its outline the square of the turn less its newel - a hexagon, whose narrow end runs round the newel from '
  'one face to the other. Its going on the walkline is the chord of a quarter circle of 450 mm.',
  ['17.7.3'], house(x0=1000, x1=2800, y1=2800, risers=12, form={**WQN, 'winders': 1}), WELL)
n('stairs', 'winders-only', 'A winder stair whose first riser rises onto the first winder - its first flight has '
  'no tread - and whose last winder rises onto the floor at its head: 1 riser before the turn, 3 winders and 4 '
  'risers in all, each 675 mm. Its walkline starts at the first nosing line and ends at the head, on the turn\'s '
  'arc: a quarter of a circle of 450 mm, with no straight part.',
  ['17.7.3', '17.4.2'],
  house(x0=1000, x1=2800, y1=2800, risers=4, form={**WQN, 'risersBeforeTurn': 1}), WELL)
# headroom of tapered treads (17.6)
def spiral_under_a_floor():
    """The spiral stair of stairs/016 under L2's 300 mm floor, rising into a well north of y = 1500 mm."""
    return v4(storeys(lower(), Draw('L2', 'U').walls((0, 0), (0, 4000), (1000, 4000), (3000, 4000), (6000, 4000), (6000, 0),
                                                   (0, 0)).seps((1000, 4000), (1000, 1500), (3000, 1500), (3000, 4000)),
                      rooms={'R1': ('L1', 3000, 2500, {}), 'R2': ('L2', 4500, 3000, {})},
                      stairs={'ST1': stair(x=2000, y=1000, width=800, tread=220, risers=13, form=SPIRAL)},
                      levels={'L1': {**LEVELS2['L1'], 'ceilingHeight': 2400 * MM},
                              'L2': {**LEVELS2['L2'], 'floorThickness': 300 * MM}}))


n('stairs', 'winder-under-the-floor', 'The quarter-turn winder stair with a newel under L2\'s floor, 300 mm thick, '
  'which covers the whole turn: the well starts only at y = 1700 mm. Its winders are level at their tops, and their '
  'lanes - the edges of their outlines and their walkline chords - are under the floor\'s bottom at 2400 mm; the least '
  'clearance is under the floor at the edge of the well, over the second flight.',
  ['17.6.2', '17.7.3'],
  v4(storeys(lower(), Draw('L2', 'U').walls((0, 0), (0, 4000), (1700, 4000), (2700, 4000), (6000, 4000), (6000, 0),
                                            (0, 0)).seps((1700, 4000), (1700, 1700), (2700, 1700), (2700, 4000)),
             rooms=HALLS, stairs={'ST1': stair(form=WQN)},
             levels={'L1': {**LEVELS2['L1'], 'ceilingHeight': 2400 * MM},
                     'L2': {**LEVELS2['L2'], 'floorThickness': 300 * MM}})), WELL)
n('stairs', 'spiral-under-a-floor', 'The spiral stair of 1800 mm under L2\'s 300 mm floor, rising into a well that '
  'starts at y = 1500 mm, its centre\'s line: the treads of its first half-turn, south of that line, are under the '
  'floor, and its lanes - each tread\'s edges and its walkline chord, level at its top - meet the floor\'s bottom, '
  'at 2400 mm; the least clearance is where the treads pass under the edge of the well.',
  ['17.6.2', '17.7.3'], spiral_under_a_floor(), WELL)
# the opening a stair needs (17.6)
n('stairs', 'opening', 'The straight stair designed for 1800 mm of headroom. The floor above has its bottom at 2400 '
  'mm, 3072000, so a step needs it open when its top is above 600 mm, 768000: the third tread\'s, 740571.43, is not, and '
  'the fourth\'s, 987428.57, is - the opening starts at the fourth step, index 3, and every step after it needs it too. '
  'Its headroom, 2331428.57 - about 1821 mm - is more than it declares, so there is no FS-LINT-019.',
  ['17.6.3', '17.1.3'], house(minHeadroom=1800 * MM), WELL)
n('stairs', 'headroom-less-than-declared', 'The same stair designed for 2000 mm: its headroom, 2331428.57, is less '
  'than 2560000, so the validator reports FS-LINT-019, a warning. Its opening starts at the third step, index 2, '
  'whose top, 740571.43, is above 3072000 - 2560000.',
  ['17.6.3', '17.6.4'], house(minHeadroom=2000 * MM), WELL + [('FS-LINT-019', ['ST1'])])
d = v4(as_03('l-stair-turning-right'))
d['stairs']['ST1']['minHeadroom'] = 100 * MM
n('stairs', 'no-opening-needed', 'The L-shaped stair turning right under a floor with no thickness, designed for '
  '100 mm of headroom: its highest tread, at 3209142.86, is more than 100 mm below the floor at 3456000, so no step '
  'needs an opening, and it has no opening member. Its headroom is 0, less than it declares: FS-LINT-019.',
  ['17.6.3', '17.6.4'], d, [('FS-LINT-019', ['ST1'])])
n('stairs', 'winder-opening', 'The quarter-turn winder stair with a newel, designed for 2000 mm of headroom under '
  'L2\'s 300 mm floor, whose bottom is at 2400 mm: a step needs the floor open when its top is above 400 mm, 512000, '
  'and the third tread of its first flight, at 740571.43, is the first that does - index 2, before the winders, '
  'which need it too, as does every later step.',
  ['17.6.3', '17.7.3'], house(x0=1000, x1=2800, y1=2800, form=WQN, minHeadroom=2000 * MM), WELL)
# ---- invalid tapered stairs
n('stairs', 'newel-reaches-the-walkline', 'A quarter turn whose newel is 320 mm deep: its far corner is 320 sqrt 2 '
  'mm from the pivot, beyond the walkline 450 mm away. FS-INV-905.', ['17.7.4'],
  house(x0=1000, x1=2800, y1=2800, form={**WINDER_Q, 'newel': 320 * MM}), [('FS-INV-905', ['ST1'])])
n('stairs', 'newel-just-inside', 'A newel of 318 mm: 8 x 318^2 is less than 900^2, so its far corner is inside the '
  'walkline\'s circle (17.7.4).', ['17.7.4', '17.7.3'],
  house(x0=1000, x1=2800, y1=2800, form={**WINDER_Q, 'newel': 318 * MM}), WELL)
n('stairs', 'newel-on-the-walkline', 'A half turn 800 mm wide with a 200 mm gap and a newel of 300 mm: the newel\'s '
  'far corners are 400 mm along and 500 mm across from the pivot - exactly the walkline\'s radius of 500 mm, which '
  'is not inside it. FS-INV-905.', ['17.7.4'],
  house(x0=400, x1=2800, y1=2100, width=800, risers=15, form={**WH, 'gap': 200 * MM, 'newel': 300 * MM}),
  [('FS-INV-905', ['ST1'])])
n('stairs', 'gap-wider-than-the-stair', 'A half-turn winder stair 900 mm wide with a gap of 1000 mm: its walkline\'s '
  'arc, of radius 950 mm, would run outside the turn. FS-INV-905.', ['17.7.4'],
  house(x0=400, x1=2800, y1=3200, risers=15, form={**WH, 'gap': 1000 * MM}), [('FS-INV-905', ['ST1'])])
n('stairs', 'spiral-tread-of-half-a-turn', 'A spiral stair of 3 risers through 360 degrees: each of its 2 treads '
  'turns 180 degrees, which no tread can. FS-INV-906.', ['17.7.5'],
  house(x0=1000, x1=3000, y1=2500, x=2000, y=1000, width=800, risers=3, form={**SPIRAL, 'sweep': 360_000_000}),
  [('FS-INV-906', ['ST1'])])
n('stairs', 'spiral-sweep-too-small', 'A spiral stair of 13 risers that turns through 10 microdegrees: its treads\' '
  'nosing lines are 10 x k / 12 rounded, so some treads turn through no angle at all. FS-INV-906.', ['17.7.5'],
  house(x0=1000, x1=3000, y1=2500, x=2000, y=1000, width=800, form={**SPIRAL, 'sweep': 10}), [('FS-INV-906', ['ST1'])])
n('stairs', 'more-winders-than-microdegrees', 'A quarter turn on 90000001 winders - more than its 90000000 '
  'microdegrees - with risers enough for them: some winder turns through no angle. FS-INV-906.', ['17.7.5'],
  house(x0=1000, x1=2800, y1=2800, risers=90_000_005, form={**WINDER_Q, 'winders': 90_000_001}),
  [('FS-INV-906', ['ST1'])])
n('stairs', 'angles-after-fit', 'A spiral stair of 1 riser through 10 microdegrees: its riser count does not fit '
  '(FS-INV-903), and FS-INV-906 is not evaluated for it (10.3).', ['10.3.1', '17.4.2'],
  house(x0=1000, x1=3000, y1=2500, x=2000, y=1000, width=800, risers=1, form={**SPIRAL, 'sweep': 10}),
  [('FS-INV-903', ['ST1'])])


def sch(slug, description, covers, mut, **kw):
    d = house(**kw)
    mut(d['stairs']['ST1'])
    n('stairs', slug, description, covers, d, SCH)


sch('min-headroom-zero', 'A stair designed for 0 headroom: minHeadroom is greater than zero.', ['17.1.3'],
    lambda s: s.update(minHeadroom=0))
sch('min-headroom-negative', 'A minHeadroom of -1.', ['17.1.3'], lambda s: s.update(minHeadroom=-1))
sch('newel-zero', 'A winder stair whose newel is 0 deep: a newel is greater than zero, and a turn without one has none.',
    ['17.2.3'], lambda s: s.update(form={**WINDER_Q, 'newel': 0}))
sch('newel-on-an-l-stair', 'An L-shaped stair has a landing, not a newel the treads stand on.', ['17.2.3', '17.2.1'],
    lambda s: s.update(form={**L_FORM, 'newel': NEWEL}))
sch('newel-on-a-spiral', 'A spiral stair\'s column is the space its treads leave: it has no newel member.',
    ['17.2.3', '17.2.1'], lambda s: s.update(form={**SPIRAL, 'newel': NEWEL}))
sch('newel-on-a-u-stair', 'A U-shaped stair has no newel.', ['17.2.3'], lambda s: s.update(form={**U_FORM, 'newel': NEWEL}))

roofs04.declare()

NEW = list(TESTS)
del TESTS[:]


def main(argv) -> int:
    tests = BASE + NEW
    return 1 if write_all(prune='--prune' in argv, tests=tests, suite=SUITE04, reader=READER_04) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

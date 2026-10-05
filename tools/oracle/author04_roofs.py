"""The roofs of the Core 0.4 suite: the weighted straight skeleton (16.4.3 to 16.4.6), as author04.py uses it.

- RETIRED: the roof statements 0.4 retires, with the statements that replace them.
- retarget(tc): a 0.3 roof test as 0.4 reads it. The roofs 0.3 left underived that 0.4 derives - mixed pitches,
  gables beside one another, a gable whose clearance a neighbouring wing blocked - lose FS-LINT-015 and gain their
  surface; the descriptions that spoke of 0.3's class of equal-pitch roofs say what 0.4 does instead. Every other
  expected value is the 0.3 suite's: on every roof 0.3 derives, 0.4 derives the same values.
- declare(): the tests of what 0.4 adds, at the end of the group `roofs`: saltboxes and hips at mixed pitches, and
  the degenerate cases of the wavefront - parallel edges, collinear eaves, coincident events, a very thin lobe, reflex
  corners, an edge event and a split event at one point - and the roofs 16.4.6 still leaves underived.

Expected diagnostics are written by hand and cross-checked against the oracle (validate.READER_04); geometry, hashes
and canonical forms come from the oracle.
"""
import copy

from tools.oracle.author03 import FT, L_FP, LINT15, SIX, gables, rf, roof_doc
from tools.oracle.author_lib import _diag, cov, t

RETIRED = {'FS-CORE-16.4.1': 'FS-CORE-16.4.2', 'FS-CORE-16.5.1': 'FS-CORE-16.5.2'}
SKELETON = ['16.4.2', '16.4.3', '16.5.2']


def P(rise, run=12):
    return {'pitch': {'rise': rise, 'run': run}}


# 0.3 roof tests whose expected values or wording change under 0.4: slug -> (description, covers, diagnostics)
CHANGED = {
    'mixed-pitches': (
        'A hip roof whose south edge rises at 12 in 12 and the rest at 6 in 12. Core 0.3 did not derive it; 0.4\'s '
        'weighted straight skeleton does (16.4.3). The south plane, at twice the others\' pitch, would meet the north '
        'plane 1033 1/3 mm above the eave, but the east and west planes meet first, 2050 mm in from each end and 1025 mm '
        'up: the roof\'s high, where the south plane\'s two hips end. The ridge between the east and west faces is 25 mm '
        'long, running north-south; there is no FS-LINT-015.',
        SKELETON, []),
    'adjacent-gables': (
        'A rectangle with gables on edges 1 and 2, the east and the north, which meet at a corner. Core 0.3 derived a '
        'gable only at the end of a wing; 0.4 derives this one: the corner of the two gables stands still, and the south '
        'and west planes, at 6 in 12, meet in one hip from the south-west corner, 3100 mm up the room, to (3050 mm, '
        '3050 mm) on the north gable, 1550 mm above the eave. From there the south plane runs on to the north-east '
        'corner, level along the north gable, so the east gable end is a triangle and the north one a quadrilateral.',
        SKELETON, []),
    'gable-on-an-inner-face': (
        'A U-shaped house with a gable on the inner face of its west arm, edge 5: both ends of that edge are reflex '
        'corners beside sloped edges, so the wavefront would move its ends away from each other along its line, past the '
        'ends of the gable, and the roof would need a vertical step inside its outline (16.4.6, condition 3). Its surface '
        'is not derived: FS-LINT-015.', ['16.4.2'], LINT15),
    'gable-clearance-clear': (
        'A G-shaped house whose west arm, 10 feet wide, ends in a gable, edge 8, facing the south eave of the top wing '
        '5 feet away across a gap outside the outline. The wavefront moves inside the outline, so the top wing does not '
        'reach the gable: the arm\'s two planes meet in a ridge that runs to the gable\'s midpoint, as Core 0.3 derived '
        'it.', SKELETON, []),
    'gable-clearance-blocked': (
        'The same house with the top wing 4 feet from the gable. Core 0.3 did not derive it, because a pointwise '
        'distance would have reached the gable through the gap; 0.4\'s wavefront moves inside the outline, so the top '
        'wing never reaches the gable, and the roof is derived like the one 5 feet away: the arm\'s ridge runs to its '
        'gable\'s midpoint, and there is no FS-LINT-015.', SKELETON, []),
    'hip-roof-on-an-oblique-outline': (
        'A hip roof on the five-sided footprint: its oblique edges run 2000 mm by 1000 mm, so each is the square root '
        'of 5 times 1000 mm long, which is not an integer, and the planes rising from them have irrational '
        'coefficients. Its surface is not derived (16.4.6, condition 2): FS-LINT-015.', ['16.4.2', '10.2.1'], LINT15),
    'collinear-eaves-share-a-plane': (
        'A rectangle with a narrow bay, 2 feet square, pushed out of its south side: the south eave is two collinear '
        'edges, 0 and 4, either side of the bay, facing the same way at one pitch. Once the bay\'s little hip closes, '
        'their wavefront edges meet on one line and continue as one (16.4.4), in one plane: the boundary between their '
        'faces, midway between them, from the valleys\' meeting point to the main ridge, is a seam and not a line, and '
        'each face is still its own edge\'s.', ['16.4.2', '16.4.4', '16.5.2'], []),
}


def retarget(tc):
    """A 0.3 roof test, as author04.retarget leaves it, as 0.4 reads it."""
    if tc['group'] != 'roofs' or tc['slug'] not in CHANGED:
        return tc
    tc = copy.deepcopy(tc)
    description, covers, diags = CHANGED[tc['slug']]
    tc['description'], tc['covers'], tc['diags'] = description, cov(*covers), [_diag(*x) for x in diags]
    return tc


def v4(d):
    d = copy.deepcopy(d)
    d['floorspec'] = '0.4'
    return d


def n(slug, description, covers, inp, diags=(), **kw):
    t('roofs', slug, description, covers, inp, diags, **kw)


def declare():
    """The roof tests 0.4 adds, after the 0.3 ones in the group `roofs`."""
    house = [[0, 0], [32 * FT, 0], [32 * FT, 24 * FT], [0, 24 * FT]]
    n('saltbox', 'A saltbox: a house 32 feet by 24 under a roof whose short ends, edges 1 and 3, are gables, whose '
      'front, the south edge, rises steeply at 12 in 12, and whose back, the north edge, at 6 in 12 - the back slope '
      'twice as long in plan. With a 1-foot overhang the eave outline is 26 feet deep; the two planes meet in a level '
      'ridge 26/3 feet north of the south eave and 26/3 feet above it, and each gable end is a triangle that rises to '
      'it off centre. Every coordinate is exact and rounded once.',
      SKELETON + ['16.2.2', '16.3.1'], v4(roof_doc(rf(house, pitch=SIX, overhang=FT, edges={'0': P(12), **gables(1, 3)}))))
    n('hip-at-four-pitches', 'A hip roof 40 feet by 24 with every edge at its own pitch: south 12 in 12, east 8, '
      'north 6 and west 4. The planes of the north and the south meet in a ridge where the south plane, steepest, has '
      'risen 8 feet in 8 feet and the north one 8 feet in 16; the west plane, shallowest, runs in 24 feet to its end, '
      'and the east one 12 feet. Hips run from the four corners at four different angles in plan, none of them at '
      '45 degrees.', SKELETON, v4(roof_doc(rf([[0, 0], [40 * FT, 0], [40 * FT, 24 * FT], [0, 24 * FT]], pitch=SIX,
                                                 edges={'0': P(12), '1': P(8), '3': P(4)}))))
    n('l-shaped-hip-at-two-pitches', 'The L-shaped house, its wing along X at 6 in 12 and its wing along Y - edges 3, 4 '
      'and 5 - at 9 in 12. The reflex corner\'s valley does not run at 45 degrees: it bends the wavefront between two '
      'speeds, and the two wings\' ridges meet at different heights - the Y wing\'s, steeper, 9 feet above the eave and '
      'the X wing\'s 6 feet - joined by a hip down from the higher to the lower.',
      SKELETON, v4(roof_doc(rf(L_FP, pitch=SIX, edges={'3': P(9), '4': P(9), '5': P(9)}))))
    U = [[0, 0], [36 * FT, 0], [36 * FT, 30 * FT], [24 * FT, 30 * FT], [24 * FT, 12 * FT], [12 * FT, 12 * FT],
         [12 * FT, 30 * FT], [0, 30 * FT]]
    n('u-shaped-wings-at-three-pitches', 'A U-shaped house whose east arm rises at 9 in 12, its west arm at 4 in 12, and '
      'the rest at 6 in 12: two reflex corners, each between edges at different pitches, whose valleys run at '
      'different angles, and three ridges at three heights - 2 feet over the west arm, 3 over the base and 4 1/2 over '
      'the east arm - joined by hips.',
      SKELETON, v4(roof_doc(rf(U, pitch=SIX, edges={'1': P(9), '2': P(9), '3': P(9), '5': P(4), '6': P(4), '7': P(4)}))))
    n('four-hips-meet-at-one-point', 'A rectangle 24 feet by 12 whose long edges rise at 12 in 12 and short ones at 6 in '
      '12: every plane reaches the centre 6 feet above the eave at once, so the four edges of the wavefront vanish '
      'together at one point, at one event elevation, and the roof is a pyramid with no ridge - four hips, from the '
      'corners, in two directions in plan.', SKELETON,
      v4(roof_doc(rf([[0, 0], [24 * FT, 0], [24 * FT, 12 * FT], [0, 12 * FT]], pitch=SIX, edges={'0': P(12), '2': P(12)}))))
    n('saltbox-parallel-edges-meet-head-on', 'The saltbox\'s two sloped edges are parallel and face each other: their '
      'wavefront edges reach one line at the same elevation, cover it once in each direction, and close up together '
      'with the gables between them (16.4.4) - here at a 6 in 12 front and a 2 in 12 back, the ridge 6 feet from the '
      'front of a house 24 feet deep and 3 feet above the eave.',
      SKELETON, v4(roof_doc(rf(house, pitch={'rise': 2, 'run': 12}, edges={'0': P(6), **gables(1, 3)}))))
    n('stepped-eave-break', 'A south eave that steps: edge 0, from x = 0 to 10 feet, at 3 in 12, and edge 2, a foot '
      'further in from 10 to 30 feet, at 12 in 12, joined by edge 1, a foot long; the rest at 12 in 12. Edge 0\'s line '
      'moves 4 feet for each foot it rises, edge 2\'s 1: a third of a foot up they lie on one line and edge 1 has no '
      'length. They face the same way, so the faster, edge 0, continues over the whole run and edge 2 stops (16.4.4): '
      'edge 2\'s face is a strip a third of a foot deep, and above it the roof turns shallower along a level break, '
      '"break", from the end of edge 1\'s valley to the east hip.',
      SKELETON + ['16.4.4'], v4(roof_doc(rf([[0, 0], [10 * FT, 0], [10 * FT, FT], [30 * FT, FT], [30 * FT, 20 * FT],
                                              [0, 20 * FT]], pitch={'rise': 12, 'run': 12}, edges={'0': P(3)}))))
    n('two-fast-edges-overtake-a-slow-one', 'A south eave of three edges: edges 0 and 4 at 3 in 12 either side of edge '
      '2, a foot further in at 12 in 12. A third of a foot up all three lie on one line: the two fast edges continue '
      'over the run as one wavefront edge, sharing one plane, and the slow one stops (16.4.4). Their plane\'s pieces are '
      'divided between them midway between their facing ends, at x = 15 feet: a seam, not a line, while the slow '
      'face\'s top is two breaks, one either side of it.',
      SKELETON + ['16.4.4'], v4(roof_doc(rf([[0, 0], [10 * FT, 0], [10 * FT, FT], [20 * FT, FT], [20 * FT, 0], [30 * FT, 0],
                                              [30 * FT, 20 * FT], [0, 20 * FT]], pitch={'rise': 12, 'run': 12},
                                             edges={'0': P(3), '4': P(3)}))))
    n('collinear-eaves-at-two-pitches', 'The rectangle with the 2-foot bay, its south eave on two collinear edges, but '
      'edge 4, east of the bay, at 9 in 12 and edge 0 at 6 in 12: on one line, facing the same way, at two pitches, so '
      'they do not share a plane. Their lines move apart as they rise and never lie on one line again. The bay\'s west '
      'side, at 6 in 12, moves faster than edge 4: its face spreads east between those of edges 0 and 4, bounded by a '
      'valley and a hip, until it meets the east end\'s face in a short ridge 4 feet up, at x = 22 feet.',
      SKELETON, v4(roof_doc(rf([[0, 0], [14 * FT, 0], [14 * FT, -2 * FT], [16 * FT, -2 * FT], [16 * FT, 0], [30 * FT, 0],
                                [30 * FT, 20 * FT], [0, 20 * FT]], pitch=SIX, edges={'4': P(9)}))))
    bay = [(0, 0), (4, 0), (4, -1), (10, -1), (10, 0), (20, 0), (20, 8), (4, 8), (4, 6), (2, 6), (2, 8), (0, 8)]
    n('edge-and-split-events-at-one-point', 'A house 20 feet by 8 with a 6-foot bay a foot deep on its south side and '
      'a notch 2 feet wide and 2 deep in its north, at 6 in 12. Three feet in, the bay\'s front has closed - its '
      'wavefront edge has no length - and the bay\'s two sides overlap head on, at (7 feet, 3 feet), just as the '
      'notch\'s east reflex corner reaches that point: an edge event and a split event at one point and one elevation, '
      'resolved together (16.4.4). The roof is the one Core 0.3 derived for the house, value for value.',
      SKELETON, v4(roof_doc(rf([[x * FT, y * FT] for x, y in bay], pitch=SIX))))
    two = [(0, 0), (2, 0), (2, -1), (4, -1), (4, 0), (20, 0), (20, 8), (4, 8), (4, 6), (2, 6), (2, 8), (0, 8)]
    n('edge-and-split-events-at-one-elevation', 'A house 20 feet by 8 with a 2-foot bay on its south side and a notch '
      'in its north above it, at 6 in 12. Half a foot up - a foot in - the bay\'s front closes at (3 feet, 0) while the '
      'notch\'s west corner reaches the west eave\'s wavefront at (1 foot, 5 feet) and splits it: two events at one '
      'elevation and two points, resolved at once from the wavefront there (16.4.4). The roof is the one Core 0.3 '
      'derived for the house, value for value.', SKELETON, v4(roof_doc(rf([[x * FT, y * FT] for x, y in two], pitch=SIX))))
    x = 15 * FT
    n('very-thin-lobe', 'A fin 3 base units wide and 4 feet long sticks out of the south side of a house 30 feet by '
      '20, its end at 12 in 12 and the house\'s east edge at 4 in 12: the fin\'s two sides close up 1.5 base units in, '
      'in a ridge on x = 15 feet + 1.5 units, which is rounded once, ties to even. The fin\'s faces are 1.5 base units '
      'wide - its end\'s is 1.5 square units in area - and every coordinate of them is rounded once; lines shorter than '
      'a base unit keep the points they round to.',
      SKELETON, v4(roof_doc(rf([[0, 0], [x, 0], [x, -4 * FT], [x + 3, -4 * FT], [x + 3, 0], [30 * FT, 0], [30 * FT, 20 * FT],
                                [0, 20 * FT]], pitch=SIX, edges={'2': P(12), '5': P(4)}))))
    chamfered = [[3 * FT, 0], [27 * FT, 0], [30 * FT, 4 * FT], [30 * FT, 20 * FT], [0, 20 * FT], [0, 4 * FT]]
    n('pythagorean-oblique-edges', 'A house 30 feet by 20 whose south corners are cut on a 3 : 4 slope, 3 feet by 4: '
      'each oblique edge is 5 feet long, an integer, so its plane has rational coefficients and the roof is derived '
      '(16.4.3). The two oblique edges rise at 9 in 12, the north at 4 in 12 and the rest at 6; the points where the '
      'oblique faces close are rational but not integers, and are rounded once.',
      SKELETON, v4(roof_doc(rf(chamfered, pitch=SIX, edges={'1': P(9), '5': P(9), '3': P(4)}))))
    n('gables-on-four-sides', 'The chamfered house with only its two cut corners sloped, at 6 in 12, and its four sides '
      'gables: each oblique edge\'s wavefront edge grows as it rises, sliding along the gables beside it, until the two '
      'meet in a level ridge that runs diagonally from the south side to the north. The four gable ends are walls up to '
      'the two planes.',
      SKELETON, v4(roof_doc(rf([[3 * FT, 0], [30 * FT, 0], [30 * FT, 16 * FT], [27 * FT, 20 * FT], [0, 20 * FT],
                                [0, 4 * FT]], pitch=SIX, edges=gables(0, 1, 3, 4)))))
    n('oblique-gable', 'A house 30 feet by 20 with its south-east corner cut at 45 degrees and that cut a gable, at 9 in '
      '12 to its south: a gable\'s length is never in question, since it does not move, so the roof is derived though '
      'the gable is 4 feet times the square root of 2 long. Its gable end is a triangle up to the point where the south '
      'and east planes meet over it.',
      SKELETON, v4(roof_doc(rf([[0, 0], [26 * FT, 0], [30 * FT, 4 * FT], [30 * FT, 20 * FT], [0, 20 * FT]], pitch=SIX,
                               edges={'1': {'gable': True}, '0': P(9)}))))
    n('oblique-sloped-edge-at-45-degrees', 'The same house with its 45-degree cut sloped: the cut is 4 feet times the '
      'square root of 2 long, so its plane has irrational coefficients. Its surface is not derived (16.4.6, condition '
      '2): FS-LINT-015.', ['16.4.2', '10.2.1'],
      v4(roof_doc(rf([[0, 0], [26 * FT, 0], [30 * FT, 4 * FT], [30 * FT, 20 * FT], [0, 20 * FT]], pitch=SIX))), LINT15)
    late = [(39, 12), (39, 34), (21, 34), (21, 21), (7, 21), (7, 34), (3, 34), (3, 12)]
    n('gable-passed-after-an-event', 'A U-shaped house open to the north whose inner faces, edges 2, 3 and 4, and the '
      'east arm\'s end, edge 1, are gables, and whose west arm\'s end, edge 5, rises at 3 in 12. Edge 5\'s line moves 4 '
      'feet for each foot it rises, so 13/4 feet up it lies on the line of edge 3, the gable across the bottom of the '
      'opening, facing the same way, with edge 4 gone between them: the faster continues over the run and the gable '
      'stops (16.4.4). Its wavefront edge then meets edge 2\'s, whose end it would push down past the gable\'s end '
      '(16.4.6, condition 3): the surface is not derived, FS-LINT-015. At t = 0 every gable was sound.',
      ['16.4.2', '16.4.4'],
      v4(roof_doc(rf([[x_ * FT, y_ * FT] for x_, y_ in late], pitch=SIX,
                     edges={**gables(1, 2, 3, 4), '5': P(3), '6': P(12)}))), LINT15)
    d = roof_doc(rf(pitch=SIX, edges={'0': P(12)}))
    n('read-0.3-mixed-pitch-roof', 'The 0.3 suite\'s mixed-pitch hip roof (roofs/011 of conformance/core/0.3), exactly '
      'as it is there, declaring "0.3", read by a reader of 0.4: valid, and its surface derived as 0.4 derives it, '
      'with no FS-LINT-015, which a reader of 0.3 reports for it.', ['1.2.8', '16.4.2', '16.5.2'], d)
    n('overhangs-at-mixed-pitches', 'The saltbox with a 2-foot overhang at the back and none elsewhere: the eave '
      'outline is computed first, 26 feet deep, and the skeleton from it, so the ridge, a third of the way across from '
      'the steep front, lies 26/3 feet north of the south eave and 26/3 feet above it.',
      SKELETON + ['16.3.1'], v4(roof_doc(rf(house, pitch=SIX, edges={'0': P(12), '2': {'overhang': 2 * FT}, **gables(1, 3)}))))
    n('pitch-ratios-share-a-plane', 'The rectangle with the 2-foot bay, edge 0 at 1 in 2 and edge 4 at 6 in 12: one '
      'pitch, compared as a ratio, so the two collinear edges share a plane and their faces meet in a seam, as if both '
      'said 6 in 12.', SKELETON + ['16.4.4'],
      v4(roof_doc(rf([[0, 0], [14 * FT, 0], [14 * FT, -2 * FT], [16 * FT, -2 * FT], [16 * FT, 0], [30 * FT, 0],
                      [30 * FT, 20 * FT], [0, 20 * FT]], pitch=SIX, edges={'0': P(1, 2)}))))

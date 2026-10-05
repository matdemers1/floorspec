"""Stairs in the oracle (Core 0.3, chapter 17): the layout of each form by hand, the riser count found from a
greatest riser when the head room depends on it, headroom at the edge of a floor and across a vault's ridge,
and the stair links of circulation, which leave a building without a stair as 0.2 left it."""
import json
import unittest
from fractions import Fraction

from tools.oracle import stairs
from tools.oracle.derive import Doc
from tools.oracle.validate import READER_03, check

MM = 1280
H = 2700 * MM


def box(level, p, x0, y0, x1, y1):
    js = {f'{p}1': [x0, y0], f'{p}2': [x0, y1], f'{p}3': [x1, y1], f'{p}4': [x1, y0]}
    junctions = {j: {'level': level, 'position': [x * MM, y * MM]} for j, (x, y) in js.items()}
    ids = list(js)
    walls = {f'{p}W{i}': {'level': level, 'start': ids[i], 'end': ids[(i + 1) % 4], 'type': 'WT'} for i in range(4)}
    return junctions, walls


def house(st=None, l2_rooms=True, functions=None, **levels):
    j1, w1 = box('L1', 'JA', 0, 0, 6000, 4000)
    j2, w2 = box('L2', 'JB', 0, 0, 6000, 4000)
    d = {'floorspec': '0.3', 'project': {'name': 'x'}, 'buildings': {'B1': {}},
         'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': H},
                    'L2': {'building': 'B1', 'elevation': H, 'height': H}},
         'types': {'WT': {'kind': 'wallType', 'layers': [{'thickness': 100 * MM, 'function': 'core'}]}},
         'junctions': {**j1, **j2}, 'walls': {**w1, **w2},
         'rooms': {'R1': {'level': 'L1', 'anchor': [3000 * MM, 2500 * MM]}}}
    if l2_rooms:
        d['rooms']['R2'] = {'level': 'L2', 'anchor': [3000 * MM, 2500 * MM]}
    for rid, f in (functions or {}).items():
        d['rooms'][rid]['function'] = f
    for lid, members in levels.items():
        d['levels'][lid].update(members)
    if st is not None:
        d['stairs'] = {'ST1': st}
    return d


def stair(**kw):
    st = {'level': 'L1', 'to': 'L2', 'position': [1000 * MM, 600 * MM], 'width': 900 * MM, 'tread': 250 * MM, 'risers': 14}
    st.update(kw)
    return {k: v for k, v in st.items() if v is not None}


def run(d):
    r, _, notes = check(json.dumps(d).encode(), READER_03)
    return r


class Layout(unittest.TestCase):
    def test_l_left_and_right_are_mirror_images(self):
        f = {'kind': 'lShaped', 'turn': 'left', 'risersBeforeTurn': 7}
        left = stairs.layout(stair(form=f), 14)
        right = stairs.layout(stair(form={**f, 'turn': 'right'}), 14)
        self.assertEqual(left.head, (Fraction(1500 + 450) * MM, Fraction(450 + 1500) * MM))
        self.assertEqual(right.head, (left.head[0], -left.head[1]))
        kinds = [p[0] for p in left.pieces]
        self.assertEqual(kinds, ['flight', 'landing', 'flight'])
        self.assertEqual(sum(len(p[1].treads()) for p in left.pieces if p[0] == 'flight'), 12)

    def test_u_head_is_back_above_the_first_flight(self):
        lay = stairs.layout(stair(form={'kind': 'uShaped', 'turn': 'left', 'risersBeforeTurn': 7, 'gap': 200 * MM}), 14)
        self.assertEqual(lay.head, (0, (900 + 200) * MM))
        landing = lay.pieces[1][1]
        self.assertEqual((landing.q0, landing.q1), (-450 * MM, (1350 + 200) * MM))

    def test_winder_bounds_without_steps(self):
        f = {'kind': 'winder', 'turn': 'left', 'angle': 'quarter', 'risersBeforeTurn': 4, 'winders': 3}
        lay = stairs.layout(stair(form=f), 14)
        self.assertEqual(lay.pieces, [])
        self.assertEqual(lay.head, (Fraction((750 + 450) * MM), Fraction((450 + 1750) * MM)))

    def test_fits(self):
        self.assertFalse(stairs.fits(stair(), 1))
        self.assertTrue(stairs.fits(stair(), 2))
        f = {'kind': 'lShaped', 'turn': 'left', 'risersBeforeTurn': 2}
        self.assertTrue(stairs.fits(stair(form=f), 4))
        self.assertFalse(stairs.fits(stair(form=f), 3))
        w = {'kind': 'winder', 'turn': 'left', 'angle': 'half', 'risersBeforeTurn': 1, 'winders': 6}
        self.assertTrue(stairs.fits(stair(form=w), 7))
        self.assertFalse(stairs.fits(stair(form=w), 6))


class Risers(unittest.TestCase):
    def test_least_count_whose_risers_are_low_enough(self):
        # 2700 mm / 14 is 246857.14 base units: a greatest riser of 246858 takes 14, one of 246857 takes 15
        d = house(stair(risers=None, maxRiser=H // 14 + 1))
        v = run(d)['derived']['stairs']['ST1']
        self.assertEqual((v['risers'], v['riserHeight']), (14, 246857))
        d = house(stair(risers=None, maxRiser=H // 14))
        self.assertEqual(run(d)['derived']['stairs']['ST1']['risers'], 15)

    def test_the_head_room_is_found_for_each_count_tried(self):
        """L2 is split at x = 4000 mm: R3 west of the partition, its floor raised 500 mm, and R2 east of it. With 12
        risers or fewer the head is in R3, 3200 mm up, and 3200 / 12 mm is too tall for 208 mm risers; with 13 it is
        at x = 4000 mm, on the partition's line - in no room - so the top is L2's elevation and 2700 / 13 mm fits."""
        d = house(stair(risers=None, maxRiser=208 * MM))
        pos = {'C1': (0, 0), 'C2': (0, 4000), 'CN': (4000, 4000), 'C3': (6000, 4000), 'C4': (6000, 0), 'CS': (4000, 0)}
        d['junctions'] = {k: v for k, v in d['junctions'].items() if v['level'] == 'L1'}
        d['junctions'].update({j: {'level': 'L2', 'position': [x * MM, y * MM]} for j, (x, y) in pos.items()})
        d['walls'] = {k: v for k, v in d['walls'].items() if v['level'] == 'L1'}
        for i, (a, b) in enumerate([('C1', 'C2'), ('C2', 'CN'), ('CN', 'C3'), ('C3', 'C4'), ('C4', 'CS'), ('CS', 'C1'),
                                    ('CS', 'CN')]):
            d['walls'][f'CW{i}'] = {'level': 'L2', 'start': a, 'end': b, 'type': 'WT'}
        d['rooms']['R2']['anchor'] = [5000 * MM, 2000 * MM]
        d['rooms']['R3'] = {'level': 'L2', 'anchor': [2000 * MM, 2000 * MM], 'floor': {'offset': 500 * MM}}
        r = run(d)
        self.assertTrue(r['valid'], r['diagnostics'])
        v = r['derived']['stairs']['ST1']
        self.assertEqual(v['risers'], 13)
        self.assertNotIn('headRoom', v)
        self.assertEqual(v['top'], H)


class Headroom(unittest.TestCase):
    def test_at_the_edge_of_the_floor_above(self):
        """No well: the floor above is over the whole stair, and the least clearance is at the head: the bottom of
        L2's 300 mm floor less the head's elevation."""
        d = house(stair(), L2={'elevation': H, 'height': H, 'floorThickness': 300 * MM, 'building': 'B1'})
        self.assertEqual(run(d)['derived']['stairs']['ST1']['headroom'], -300 * MM)

    def test_nothing_above(self):
        # L2's walls with no room in them are a well over the whole stair: L1's ceiling is cut, and nothing is above
        d = house(stair(), l2_rooms=False, L1={'ceilingHeight': 6000 * MM})
        self.assertNotIn('headroom', run(d)['derived']['stairs']['ST1'])
        # with no walls on L2 either, L1's ceiling is over the stair
        for c in ('junctions', 'walls'):
            d[c] = {k: v for k, v in d[c].items() if v['level'] == 'L1'}
        v = run(d)['derived']['stairs']['ST1']
        self.assertEqual(v['headroom'], (6000 - 2700) * MM)
        del d['rooms']['R1']
        v = run(d)['derived']['stairs']['ST1']
        self.assertNotIn('headroom', v)
        self.assertNotIn('footRoom', v)

    def test_crossings_split_a_lane_at_edges_and_ridges(self):
        c = {'kind': 'vaulted', 'ridge': [[0, 0], [10, 0]], 'pitch': {'rise': 1, 'run': 1}}
        ss = stairs._crossings((0, -5), (0, 5), [((-1, 2), (1, 2))], [c])
        self.assertEqual(ss, [0, Fraction(1, 2), Fraction(7, 10), 1])
        # collinear: both ends of the edge, where they are on the segment
        self.assertEqual(stairs._crossings((0, 0), (10, 0), [((2, 0), (20, 0))], []), [0, Fraction(1, 5), 1])


class Circulation(unittest.TestCase):
    def test_a_stair_links_its_foot_room_and_head_room_or_nothing(self):
        d = house(stair(position=[1000 * MM, 20 * MM], width=40 * MM))
        self.assertEqual(stairs.links(Doc(d)), [])                      # its head is in L2's wall: no head room
        self.assertEqual(stairs.links(Doc(house(stair()))), [('R1', 'R2')])


if __name__ == '__main__':
    unittest.main()

"""Core 0.4 in the oracle: the 0.4 schema tier, the tapered treads of winder and spiral stairs worked by hand
(17.7), the opening a stair with a minHeadroom needs (17.6), FS-INV-905 and FS-INV-906, and the step of a
migration from 0.3 to 0.4 (20.7)."""
import json
import math
import unittest
from fractions import Fraction

from tools.oracle import schema, stairs
from tools.oracle.migrate import DRAFTS_03, migrate
from tools.oracle.surd import Surd
from tools.oracle.test_stairs import house, stair
from tools.oracle.validate import READER_03, READER_04, check

MM = 1280
WQ = {'kind': 'winder', 'turn': 'left', 'angle': 'quarter', 'risersBeforeTurn': 4, 'winders': 3}
SPIRAL = {'kind': 'spiral', 'turn': 'left', 'diameter': 1800 * MM, 'sweep': 270_000_000}


def v4(d):
    return {**d, 'floorspec': '0.4'}


def run(d, reader=READER_04):
    r, _, _ = check(json.dumps(d).encode(), reader)
    return r


class Schema(unittest.TestCase):
    def test_newel_and_min_headroom_are_0_4_members(self):
        d = house(stair(form={**WQ, 'newel': 100 * MM}, minHeadroom=2000 * MM))
        self.assertNotEqual(schema.check(d, '0.3'), [])
        self.assertEqual(schema.check(v4(d), '0.4'), [])

    def test_newel_only_on_winders_and_positive(self):
        for form in ({'kind': 'lShaped', 'turn': 'left', 'risersBeforeTurn': 7, 'newel': 1}, {**SPIRAL, 'newel': 1},
                     {**WQ, 'newel': 0}):
            self.assertNotEqual(schema.check(v4(house(stair(form=form))), '0.4'), [], form)
        self.assertNotEqual(schema.check(v4(house(stair(minHeadroom=0))), '0.4'), [])


class Exact(unittest.TestCase):
    def test_round_sqrt(self):
        self.assertEqual(stairs.round_sqrt(Surd(Fraction(25, 4))), 2)              # 2.5, a tie, to even
        self.assertEqual(stairs.round_sqrt(Surd(Fraction(49, 4))), 4)              # 3.5 -> 4
        self.assertEqual(stairs.round_sqrt(Surd(2)), 1)
        self.assertEqual(stairs.round_sqrt(Surd(0, {2: 8})), 3)                     # sqrt(8 sqrt 2) = 3.36
        for x in (0, 1, 99, 10 ** 12 + 7):
            self.assertEqual(stairs.round_sqrt(Surd(x)), round(math.sqrt(x)))

    def test_arc_length(self):
        self.assertEqual(stairs.arc_length(0, 1, 180_000_000), 3)                  # pi
        self.assertEqual(stairs.arc_length(0, 450 * MM, 90_000_000), 904779)         # 706.858 mm
        self.assertEqual(stairs.arc_length(Fraction(1, 2), Fraction(1, 2), 360_000_000), 4)

    def test_divisions_round_each_end_once(self):
        self.assertEqual(stairs._divisions(90_000_000, 3), [0, 30_000_000, 60_000_000, 90_000_000])
        self.assertEqual(stairs._divisions(10, 4), [0, 2, 5, 8, 10])                 # 2.5 -> 2, 7.5 -> 8


class Winders(unittest.TestCase):
    def test_pie_winders_of_a_quarter_turn(self):
        """Three winders of 30 degrees about the inner corner of a 900 mm square: by hand, nosing line 1 meets the
        far side at 900 tan 30 mm, and each winder's going on the walkline (450 mm) is 900 sin 15 mm."""
        st = stair(form=WQ)
        turn = stairs.Turn(st)
        P = 3 * 250 * MM
        self.assertEqual(turn.O, (P, Fraction(450 * MM)))
        e1 = turn.outer[1]
        self.assertEqual(e1[1], -450 * MM)
        self.assertAlmostEqual(float(e1[0] - P), 900 * MM * math.tan(math.radians(30)), delta=0.5)
        self.assertEqual(turn.inner, [turn.O] * 4)
        self.assertEqual(len(turn.winder(2)), 4)                                     # O, E1, the corner, E2
        walk, narrow = turn.goings(1)
        self.assertEqual(stairs.round_sqrt(walk), round(900 * MM * math.sin(math.radians(15))))
        self.assertEqual(narrow.sign(), 0)

    def test_newel(self):
        st = stair(form={**WQ, 'newel': 100 * MM})
        turn = stairs.Turn(st)
        P, a = Fraction(3 * 250 * MM), 100 * MM
        self.assertEqual(turn.inner[0], (P, Fraction(350 * MM)))
        self.assertEqual(turn.inner[3], (P + a, Fraction(450 * MM)))
        # the middle winder wraps the newel's corner and the turn's
        w2 = turn.winder(2)
        self.assertIn((P + a, Fraction(350 * MM)), w2)
        self.assertIn((P + 900 * MM, Fraction(-450 * MM)), w2)
        _, narrow = turn.goings(1)
        self.assertEqual(stairs.round_sqrt(narrow), round(100 * MM * math.tan(math.radians(30))))

    def test_newel_inside_the_walkline(self):
        self.assertTrue(stairs.newel_inside(stair(form={**WQ, 'newel': 318 * MM})))
        self.assertFalse(stairs.newel_inside(stair(form={**WQ, 'newel': 320 * MM})))
        half = {**WQ, 'angle': 'half', 'gap': 200 * MM, 'newel': 300 * MM}
        self.assertFalse(stairs.newel_inside(stair(width=800 * MM, form=half)))      # exactly on the circle
        self.assertFalse(stairs.newel_inside(stair(form={**WQ, 'angle': 'half', 'gap': 1000 * MM})))

    def test_a_right_turn_is_the_mirror_image(self):
        left = run(v4(house(stair(form={**WQ, 'newel': 100 * MM}))))['derived']['stairs']['ST1']
        right = run(v4(house(stair(position=[1000 * MM, 3400 * MM], form={**WQ, 'turn': 'right', 'newel': 100 * MM}))))
        right = right['derived']['stairs']['ST1']
        self.assertEqual(left['walklineGoing'], right['walklineGoing'])
        self.assertEqual(left['narrowGoing'], right['narrowGoing'])
        mirror = [sorted((x, 4000 * MM - y) for x, y in s['outline']) for s in left['steps']]
        self.assertEqual(mirror, [sorted(map(tuple, s['outline'])) for s in right['steps']])

    def test_steps_in_walking_order(self):
        st = run(v4(house(stair(form=WQ))))['derived']['stairs']['ST1']
        self.assertEqual([s.get('winder', False) for s in st['steps']], [False] * 3 + [True] * 3 + [False] * 7)
        tops = [s['top'] for s in st['steps']]
        self.assertEqual(tops, sorted(tops))
        self.assertEqual(st['run'], st['walkline']['length'])


class Spirals(unittest.TestCase):
    def test_goings_and_centre(self):
        d = v4(house(stair(position=[2000 * MM, 1000 * MM], width=800 * MM, tread=220 * MM, risers=13, form=SPIRAL),
                     l2_rooms=False))
        st = run(d)['derived']['stairs']['ST1']
        self.assertEqual(st['centre'], [2000 * MM, 1500 * MM])
        step = math.radians(270 / 12)
        self.assertEqual(st['walklineGoing'], round(2 * 500 * MM * math.sin(step / 2)))
        self.assertEqual(st['narrowGoing'], round(2 * 100 * MM * math.sin(step / 2)))
        self.assertEqual(st['walkline']['length'], round(500 * MM * math.radians(270)))
        self.assertEqual(st['walkline']['points'][0], st['foot'])
        self.assertEqual(st['walkline']['points'][-1], st['head'])
        self.assertEqual(len(st['steps']), 12)

    def test_tread_angles(self):
        self.assertTrue(stairs.angles_ok(stair(form=SPIRAL), 13))
        self.assertFalse(stairs.angles_ok(stair(form={**SPIRAL, 'sweep': 360_000_000}), 3))
        self.assertFalse(stairs.angles_ok(stair(form={**SPIRAL, 'sweep': 10}), 13))
        self.assertTrue(stairs.angles_ok(stair(form={**WQ, 'winders': 90_000_000}), 0))
        self.assertFalse(stairs.angles_ok(stair(form={**WQ, 'winders': 90_000_001}), 0))


class Readers(unittest.TestCase):
    def test_a_0_3_reader_does_not_step_a_winder(self):
        d = house(stair(form=WQ))
        r3 = run(d, READER_03)
        r4 = run(d, READER_04)
        self.assertIn('FS-LINT-016', [x['code'] for x in r3['diagnostics']])
        self.assertNotIn('FS-LINT-016', [x['code'] for x in r4['diagnostics']])
        self.assertIn('FS-LINT-018', [x['code'] for x in r4['diagnostics']])
        s3, s4 = r3['derived']['stairs']['ST1'], r4['derived']['stairs']['ST1']
        self.assertNotIn('steps', s3)
        self.assertEqual({k: v for k, v in s4.items() if k in s3}, s3)               # every 0.3 value kept
        self.assertEqual(r3['hash'], r4['hash'])

    def test_opening(self):
        d = v4(house(stair(minHeadroom=1800 * MM), L2={'floorThickness': 300 * MM}))
        st = run(d)['derived']['stairs']['ST1']
        # the floor's bottom is 2400 mm; 2400 - 1800 = 600 mm: the fourth tread (987428.57) is the first above it
        self.assertEqual(st['opening'], {'first': 3})


class Migration(unittest.TestCase):
    def test_step_0_3_to_0_4_changes_only_the_version(self):
        d = house(stair(form=WQ))
        r = migrate(json.dumps(d).encode(), '0.4')
        self.assertEqual(r['status'], 'migrated')
        self.assertEqual(r['document'], v4(d))
        self.assertEqual(migrate(json.dumps(d).encode(), '0.4', DRAFTS_03)['diagnostics'][0]['code'], 'FS-MIG-001')


if __name__ == '__main__':
    unittest.main()

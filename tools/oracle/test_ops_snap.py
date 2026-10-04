"""Snap rounding (Ops 5.2): pixels, hot pixels, routing, and planarizing a small level. Every
expected value is worked out in the comment beside it."""

import unittest
from fractions import Fraction

from tools.oracle.ops.normalize import crossing, hot_pixels, normalize, planarize, round_point, route, segment_in_pixel


class PixelTest(unittest.TestCase):
    def test_round_ties_to_even(self):
        self.assertEqual(round_point((Fraction(5, 2), Fraction(7, 2))), (2, 4))
        self.assertEqual(round_point((Fraction(-5, 2), Fraction(-1, 2))), (-2, 0))

    def test_even_pixel_is_closed(self):
        # the pixel of (0, 0) is [-1/2, 1/2] x [-1/2, 1/2]: a vertical segment at x = 1/2 is not
        # integral, so use one along its corner: (0, 1) -> (1, 0) touches it only at (1/2, 1/2)
        self.assertEqual(segment_in_pixel((0, 1), (1, 0), (0, 0)), (Fraction(1, 2), True, Fraction(1, 2), True))

    def test_odd_pixel_is_open(self):
        # the pixel of (1, 0) is (1/2, 3/2) x [-1/2, 1/2]: (1, 1) -> (2, 0) touches its corner (3/2, 1/2)
        # only, which rounds to (2, 0), not (1, 0)
        self.assertIsNone(segment_in_pixel((1, 1), (2, 0), (1, 0)))
        self.assertIsNotNone(segment_in_pixel((1, 1), (2, 0), (2, 0)))

    def test_along_an_edge(self):
        # a horizontal segment y = 0 from (-3, 0) to (3, 0) passes through the pixels of (k, 0)
        self.assertIsNotNone(segment_in_pixel((-3, 0), (3, 0), (2, 0)))
        self.assertIsNone(segment_in_pixel((-3, 0), (3, 0), (2, 1)))
        # ...and between pixels (1, 0) and (2, 0) the point (3/2, 0) belongs to (2, 0) only
        self.assertEqual(segment_in_pixel((-3, 0), (3, 0), (1, 0))[2:], (Fraction(3, 4), False))
        self.assertEqual(segment_in_pixel((-3, 0), (3, 0), (2, 0))[:2], (Fraction(3, 4), True))

    def test_degenerate_axis(self):
        self.assertIsNone(segment_in_pixel((5, -3), (5, 3), (4, 0)))       # x = 5 is not in (7/2, 9/2]
        self.assertIsNotNone(segment_in_pixel((5, -3), (5, 3), (5, 0)))


class CrossingTest(unittest.TestCase):
    def test_interior_crossing(self):
        self.assertEqual(crossing((0, 0), (4, 4), (0, 4), (4, 0)), (2, 2))
        # (0, -3) -> (10, 4) meets y = 0 at x = 30 / 7
        self.assertEqual(crossing((0, -3), (10, 4), (-5, 0), (20, 0)), (Fraction(30, 7), 0))

    def test_t_junction_is_interior_to_one(self):
        self.assertEqual(crossing((0, 0), (10, 0), (5, 0), (5, 5)), (5, 0))

    def test_shared_endpoint_is_not_hot(self):
        self.assertIsNone(crossing((0, 0), (10, 0), (10, 0), (10, 5)))

    def test_parallel_and_apart(self):
        self.assertIsNone(crossing((0, 0), (10, 0), (0, 1), (10, 1)))
        self.assertIsNone(crossing((0, 0), (10, 0), (0, 0), (5, 0)))      # collinear: not a single point
        self.assertIsNone(crossing((0, 0), (1, 1), (5, 0), (6, -1)))

    def test_hot_pixels(self):
        # two diagonals crossing at (2.5, 2.5): the hot pixel is (2, 2), ties to even
        segs = [((0, 0), (5, 5)), ((0, 5), (5, 0))]
        self.assertEqual(hot_pixels([(0, 0), (5, 5), (0, 5), (5, 0)], segs), {(0, 0), (5, 5), (0, 5), (5, 0), (2, 2)})


class RouteTest(unittest.TestCase):
    def test_order_along_the_edge(self):
        hot = {(0, 0), (10, 0), (7, 0), (3, 0), (5, 9)}
        self.assertEqual(route((10, 0), (0, 0), hot), [(10, 0), (7, 0), (3, 0), (0, 0)])

    def test_passing_near_a_junction(self):
        # (0, 0) -> (10, 1) passes (5, 0.5): 0.5 rounds to 0, so it is in the pixel of (5, 0)
        self.assertEqual(route((0, 0), (10, 1), {(0, 0), (10, 1), (5, 0)}), [(0, 0), (5, 0), (10, 1)])
        # (0, 0) -> (10, 4) has y in [1.8, 2.2] while x is in (4.5, 5.5): it misses the pixel of
        # (5, 1), whose y interval is (0.5, 1.5), and passes through that of (5, 2)
        self.assertEqual(route((0, 0), (10, 4), {(0, 0), (10, 4), (5, 1)}), [(0, 0), (10, 4)])
        self.assertEqual(route((0, 0), (10, 4), {(0, 0), (10, 4), (5, 2)}), [(0, 0), (5, 2), (10, 4)])
        # (0, 0) -> (10, 3) has y = 1.38 at x = 4.6: inside the pixel of (5, 1), though it passes
        # x = 5 at y = 1.5, outside it
        self.assertEqual(route((0, 0), (10, 3), {(0, 0), (10, 3), (5, 1)}), [(0, 0), (5, 1), (10, 3)])

    def test_touch_then_enter(self):
        # (0, 1) -> (2, -1) touches the pixel of (0, 0) at its corner (1/2, 1/2) at t = 1/4 and
        # enters the pixel of (1, 0) just after it, at t > 1/4 (its x interval is open at 1/2)
        self.assertEqual(route((0, 1), (2, -1), {(0, 1), (2, -1), (0, 0), (1, 0)}),
                         [(0, 1), (0, 0), (1, 0), (2, -1)])


class PlanarizeTest(unittest.TestCase):
    def test_cross_mints_and_splits(self):
        wc = {
            'junctions': {'A': {'level': 'L', 'position': [0, 0]}, 'B': {'level': 'L', 'position': [10, 10]},
                          'C': {'level': 'L', 'position': [0, 10]}, 'D': {'level': 'L', 'position': [10, 0]}},
            'walls': {'W1': {'level': 'L', 'start': 'A', 'end': 'B', 'name': 'x'}},
            'separators': {'S1': {'level': 'L', 'start': 'C', 'end': 'D'}},
            'openings': {},
        }
        minted = iter(['J1', 'W2', 'S2'])
        straddles = []
        planarize(wc, 'L', lambda prefix: next(minted), straddles)
        self.assertEqual(wc['junctions']['J1'], {'level': 'L', 'position': [5, 5]})
        self.assertEqual(wc['walls'], {'W1': {'level': 'L', 'start': 'A', 'end': 'J1', 'name': 'x'},
                                       'W2': {'level': 'L', 'start': 'J1', 'end': 'B', 'name': 'x'}})
        self.assertEqual(wc['separators'], {'S1': {'level': 'L', 'start': 'C', 'end': 'J1'},
                                            'S2': {'level': 'L', 'start': 'J1', 'end': 'D'}})
        self.assertEqual(straddles, [])

    def test_opening_offsets(self):
        # W1 from (0, 0) to (100, 0) split at (40, 0) by a junction J: an opening at 50 (width 10)
        # moves to the second piece at offset 10; one at 35 (width 10) straddles
        wc = {
            'junctions': {'A': {'level': 'L', 'position': [0, 0]}, 'B': {'level': 'L', 'position': [100, 0]},
                          'J': {'level': 'L', 'position': [40, 0]}},
            'walls': {'W1': {'level': 'L', 'start': 'A', 'end': 'B'}},
            'openings': {'O1': {'wall': 'W1', 'offset': 50, 'width': 10}, 'O2': {'wall': 'W1', 'offset': 35, 'width': 10},
                         'O3': {'wall': 'W1', 'offset': 0, 'width': 40}},
        }
        straddles = []
        planarize(wc, 'L', lambda prefix: 'W2', straddles)
        self.assertEqual(wc['openings']['O1'], {'wall': 'W2', 'offset': 10, 'width': 10})
        self.assertEqual(wc['openings']['O3'], {'wall': 'W1', 'offset': 0, 'width': 40})
        self.assertEqual(straddles, ['O2'])


class GateTest(unittest.TestCase):
    """5.2: only a level that breaks Core 5.3 is planarized."""

    def level(self):
        # W1 runs along x + y = 5 and touches the pixel of the post P (2, 2) only at its corner
        # (2.5, 2.5) - which, P's coordinates being even, belongs to that pixel: a near miss
        return {
            'junctions': {'A': {'level': 'L', 'position': [0, 5]}, 'B': {'level': 'L', 'position': [5, 0]},
                          'P': {'level': 'L', 'position': [2, 2]}},
            'walls': {'W1': {'level': 'L', 'start': 'A', 'end': 'B'}},
        }

    def test_a_planar_level_is_left_alone(self):
        wc = self.level()
        before = repr(wc)
        normalize(wc, set(wc['junctions']), lambda prefix: next(iter([])))
        self.assertEqual(repr(wc), before)

    def test_a_crossed_level_is_snap_rounded_whole(self):
        # a second wall from (4, -1) to (4, 3) crosses W1 at (4, 1): now the near miss is routed too
        wc = self.level()
        wc['junctions'].update({'C': {'level': 'L', 'position': [4, -1]}, 'D': {'level': 'L', 'position': [4, 3]}})
        wc['walls']['W2'] = {'level': 'L', 'start': 'C', 'end': 'D'}
        ids = iter(['J1', 'W3', 'W4', 'W5'])
        normalize(wc, set(wc['junctions']), lambda prefix: next(ids))
        self.assertEqual(wc['junctions']['J1']['position'], [4, 1])
        self.assertEqual([(w['start'], w['end']) for w in wc['walls'].values()],
                         [('A', 'P'), ('C', 'J1'), ('P', 'J1'), ('J1', 'B'), ('J1', 'D')])


if __name__ == '__main__':
    unittest.main()

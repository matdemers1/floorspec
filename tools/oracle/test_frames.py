import math
import unittest

from tools.oracle import frames
from tools.oracle.surd import Surd


class FacingVectors(unittest.TestCase):
    def test_exact_quarter_turns(self):
        self.assertEqual(frames.facing_vector(0), (10 ** 9, 0))
        self.assertEqual(frames.facing_vector(90_000_000), (0, 10 ** 9))
        self.assertEqual(frames.facing_vector(180_000_000), (-10 ** 9, 0))
        self.assertEqual(frames.facing_vector(-90_000_000), (0, -10 ** 9))

    def test_known_values(self):
        self.assertEqual(frames.facing_vector(45_000_000), (707106781, 707106781))
        self.assertEqual(frames.facing_vector(30_000_000), (866025404, 500000000))
        self.assertEqual(frames.facing_vector(60_000_000), (500000000, 866025404))
        self.assertEqual(frames.facing_vector(-135_000_000), (-707106781, -707106781))

    def test_agrees_with_floats_far_from_a_tie(self):
        for theta in (1, 123_456_789, -17_000_001, 179_999_999, 89_999_999):
            r = math.radians(theta / 1e6)
            fx, fy = frames.facing_vector(theta)
            self.assertLessEqual(abs(fx - 1e9 * math.cos(r)), 0.5 + 1e-6)
            self.assertLessEqual(abs(fy - 1e9 * math.sin(r)), 0.5 + 1e-6)

    def test_direction_of_facing_vector_is_the_angle(self):
        for theta in (0, 1, -1, 45_000_000, 30_000_000, 123_456_789, -179_999_999, 180_000_000, 90_000_001):
            self.assertEqual(frames.direction(*frames.facing_vector(theta)), theta)


class Directions(unittest.TestCase):
    def test_axes_and_diagonals(self):
        self.assertEqual(frames.direction(5, 0), 0)
        self.assertEqual(frames.direction(-5, 0), 180_000_000)
        self.assertEqual(frames.direction(0, -2), -90_000_000)
        self.assertEqual(frames.direction(-3, -3), -135_000_000)

    def test_irrational(self):
        self.assertEqual(frames.direction(1, -2), -63_434_949)          # atan(2) = 63.43494882...
        self.assertEqual(frames.direction(3, 4), 53_130_102)            # atan(4/3) = 53.13010235...
        self.assertEqual(frames.direction(-10 ** 9, -1), 180_000_000)   # rounds to -180 deg, written as 180


class Footprints(unittest.TestCase):
    def test_identity_frame(self):
        f = frames.Frame(0, 0, 100, (1, 0))
        ring, bottom, top = frames.footprint(f, {'min': [0, 0, -10], 'max': [2000, 1500, 50]})
        self.assertEqual(ring, [[0, 0], [2000, 0], [2000, 1500], [0, 1500]])
        self.assertEqual((bottom, top), (90, 150))

    def test_rotated_quarter_turn(self):
        f = frames.Frame(Surd(10), Surd(20), 0, (0, 7))
        ring, _, _ = frames.footprint(f, {'min': [0, 0, 0], 'max': [3000, 2000, 1280]})
        # x runs north, y runs west
        self.assertEqual(ring, [[-1990, 20], [10, 20], [10, 3020], [-1990, 3020]])

    def test_extents(self):
        self.assertTrue(frames.extents_ok({'min': [0, 0, 0], 'max': [1280, 1280, 1280]}))
        self.assertFalse(frames.extents_ok({'min': [0, 0, 0], 'max': [1280, 1279, 1280]}))


class Overlap(unittest.TestCase):
    sq = staticmethod(lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]])

    def test_touching_is_not_overlap(self):
        self.assertFalse(frames.footprints_overlap(self.sq(0, 0, 10, 10), self.sq(10, 0, 20, 10)))
        self.assertFalse(frames.footprints_overlap(self.sq(0, 0, 10, 10), self.sq(10, 10, 20, 20)))
        self.assertTrue(frames.footprints_overlap(self.sq(0, 0, 10, 10), self.sq(9, 9, 20, 20)))

    def test_contained(self):
        self.assertTrue(frames.footprints_overlap(self.sq(0, 0, 100, 100), self.sq(10, 10, 20, 20)))

    def test_diamonds_with_overlapping_bounding_boxes(self):
        d1 = [[0, -10], [10, 0], [0, 10], [-10, 0]]
        d2 = [[p[0] + 11, p[1] + 11] for p in d1]
        self.assertFalse(frames.footprints_overlap(d1, d2))
        d3 = [[p[0] + 9, p[1] + 9] for p in d1]
        self.assertTrue(frames.footprints_overlap(d1, d3))

    def test_vertical_ranges(self):
        a = {'footprint': self.sq(0, 0, 10, 10), 'bottom': 0, 'top': 10}
        self.assertFalse(frames.envelopes_overlap(a, {**a, 'bottom': 10, 'top': 20}))
        self.assertTrue(frames.envelopes_overlap(a, {**a, 'bottom': 9, 'top': 20}))


if __name__ == '__main__':
    unittest.main()

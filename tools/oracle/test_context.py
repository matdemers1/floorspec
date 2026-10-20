"""FS_context 0.1.0's oracle (tools/oracle/ext/context.py): the rectangle test of 3.2 against a brute force with
fractions, and the rounding of a street's length (8.2)."""

import itertools
import unittest
from fractions import Fraction
from math import sqrt

from tools.oracle.ext import context


def right_angles(ring):
    """3.2 by another route: each corner's angle, as the cosine between its edges, is exactly 0."""
    if len(ring) != 4:
        return False
    for i in range(4):
        a, b, c = ring[i - 1], ring[i], ring[(i + 1) % 4]
        u, v = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
        nu, nv = u[0] ** 2 + u[1] ** 2, v[0] ** 2 + v[1] ** 2
        if nu == 0 or nv == 0 or Fraction(u[0] * v[0] + u[1] * v[1]) ** 2 / (nu * nv) != 0:
            return False
    return True


class Rectangles(unittest.TestCase):
    def test_every_small_quadrilateral(self):
        pts = [(x, y) for x in range(-2, 3) for y in range(-2, 3)]
        seen = 0
        for a, b, c in itertools.combinations(pts, 3):
            for d in pts:
                ring = [a, b, c, d]
                if len(set(ring)) < 4:
                    continue
                self.assertEqual(context.is_rectangle(ring), right_angles(ring), ring)
                seen += context.is_rectangle(ring)
        self.assertGreater(seen, 0)

    def test_turned(self):
        self.assertTrue(context.is_rectangle([(0, 0), (3, 4), (-1, 7), (-4, 3)]))
        self.assertFalse(context.is_rectangle([(0, 0), (3, 4), (-1, 7), (-4, 4)]))
        self.assertFalse(context.is_rectangle([(0, 0), (1, 0), (1, 1)]))


class Lengths(unittest.TestCase):
    def test_round_sqrt(self):
        for n in range(0, 5000):
            self.assertEqual(context.round_sqrt(n), round(sqrt(n)), n)


if __name__ == '__main__':
    unittest.main()

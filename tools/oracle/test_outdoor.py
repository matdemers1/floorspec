"""FS_outdoor's oracle: a shelter's bays and spacing against a brute force of their definition (spec.md
6.4), a fence's posts segment by segment (6.3), and rounding once, ties to even (Core 2.2)."""

import unittest
from fractions import Fraction

from tools.oracle.ext import outdoor


def brute_bays(span: int, spacing: int) -> int:
    """6.4: the fewest bays whose spacing is at most `spacing`, by trying each."""
    b = 1
    while Fraction(span, b) > spacing:
        b += 1
    return b


class Shelter(unittest.TestCase):
    def shelter(self, x, y, size, spacing, attached=False):
        return {'fallback': {'box': {'min': [0, 0, 0], 'max': [x, y, 3000]}}, 'postSize': size, 'postSpacing': spacing,
                'attached': attached}

    def test_bays_are_the_fewest(self):
        for x in (1281, 2560, 2561, 3841, 10000, 123457):
            for s in (1280, 1281, 2000, 5000):
                bays, spacing, _ = outdoor.shelter_layout(self.shelter(x + 100, x + 100, 100, s))
                self.assertEqual(bays[0], brute_bays(x, s))
                self.assertEqual(spacing[0], round(Fraction(x, bays[0])))          # Python rounds half to even

    def test_posts(self):
        self.assertEqual(outdoor.shelter_layout(self.shelter(1000, 1000, 100, 2000))[2], 4)
        self.assertEqual(outdoor.shelter_layout(self.shelter(1000, 1000, 100, 2000, attached=True))[2], 2)
        # three bays along x and two along y: ten round the perimeter, and three fewer along an attached back
        self.assertEqual(outdoor.shelter_layout(self.shelter(3100, 2100, 100, 1000))[2], 10)
        self.assertEqual(outdoor.shelter_layout(self.shelter(3100, 2100, 100, 1000, attached=True))[2], 7)


class Rounding(unittest.TestCase):
    def test_ties_to_even(self):
        self.assertEqual([outdoor._round_div(n, 2) for n in (1, 3, 5, 7)], [0, 2, 2, 4])
        self.assertEqual(outdoor._round_div(10, 3), 3)
        self.assertEqual(outdoor._round_div(11, 3), 4)


class Fence(unittest.TestCase):
    def fence(self, points, spacing):
        return {'points': points, 'postSpacing': spacing}

    def test_posts_segment_by_segment(self):
        self.assertEqual(outdoor.posts_of_fence(self.fence([[0, 0], [10, 0]], 5)), 3)
        self.assertEqual(outdoor.posts_of_fence(self.fence([[0, 0], [10, 0]], 4)), 4)
        self.assertEqual(outdoor.posts_of_fence(self.fence([[0, 0], [10, 0], [10, 1]], 4)), 5)

    def test_a_closed_line_counts_its_first_post_once(self):
        self.assertEqual(outdoor.posts_of_fence(self.fence([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], 10)), 4)


if __name__ == '__main__':
    unittest.main()

"""FS_landscape's oracle: the size classes at their bounds (spec.md 2.3), a line's length rounded segment
by segment (6.4), and the box that covers an element's geometry (3.5)."""

import unittest
from decimal import Decimal, ROUND_HALF_EVEN, getcontext

from tools.oracle.ext import landscape
from tools.oracle.ext_author import FT, garden

MM = 1280


def reference(n: int) -> int:
    """round(sqrt(n)) in 80-digit decimal arithmetic."""
    getcontext().prec = 80
    return int(Decimal(n).sqrt().quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


class SizeClass(unittest.TestCase):
    def test_bounds(self):
        for form, (m, l) in landscape.BOUNDS.items():
            self.assertEqual(landscape.size_class(form, m * MM - 1), 'small')
            self.assertEqual(landscape.size_class(form, m * MM), 'medium')
            self.assertEqual(landscape.size_class(form, l * MM - 1), 'medium')
            self.assertEqual(landscape.size_class(form, l * MM), 'large')


class Length(unittest.TestCase):
    def test_round_sqrt_agrees_with_decimal(self):
        for n in (0, 1, 2, 3, 4, 5, 6, 8, 9, 2 * MM * MM, 20 * FT * FT, 2 ** 53 - 1, 10 ** 30 + 7):
            self.assertEqual(landscape._round_sqrt(n), reference(n), n)

    def test_each_segment_rounded_once(self):
        self.assertEqual(landscape.length([[0, 0], [MM, MM], [MM + 3, MM + 4]]), 1810 + 5)
        self.assertEqual(landscape.length([[0, 0], [3, 4]]), landscape.length([[3, 4], [0, 0]]))


class Box(unittest.TestCase):
    def test_the_garden_covers_its_geometry(self):
        d = garden()
        for kind in landscape.KINDS:
            for eid, el in d['extensions'][landscape.NAME]['collections'][kind].items():
                self.assertTrue(landscape.inside_box(kind, el), eid)

    def test_a_line_grown_by_half_its_width(self):
        el = {'fallback': {'box': {'min': [-150, -150, 0], 'max': [1150, 150, 10]}}, 'points': [[0, 0], [1000, 0]], 'width': 300}
        self.assertTrue(landscape.inside_box('hardscape', el))
        el['width'] = 302
        self.assertFalse(landscape.inside_box('hardscape', el))


if __name__ == '__main__':
    unittest.main()

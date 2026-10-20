"""FS_energy 0.1.0's oracle (tools/oracle/ext/energy.py): the projection to plan of 2.4 against decimals carried far
beyond a tie, the distance test of 4.3 against a brute force with fractions, and the kinds of a face's edges (4.2)."""

import unittest
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction

from tools.oracle.ext import energy


def to_plan_decimal(length, rise, run):
    with localcontext() as c:
        c.prec = 80
        v = Decimal(length * run) / Decimal(rise * rise + run * run).sqrt()
        return int(v.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def near_brute(c, a, b, s):
    """4.3 by another route: the nearest point of the segment by its parameter, clamped, in fractions."""
    ab = (b[0] - a[0], b[1] - a[1])
    L2 = ab[0] ** 2 + ab[1] ** 2
    t = Fraction(0) if L2 == 0 else min(Fraction(1), max(Fraction(0), Fraction((c[0] - a[0]) * ab[0] + (c[1] - a[1]) * ab[1], L2)))
    px, py = a[0] + t * ab[0], a[1] + t * ab[1]
    return (c[0] - px) ** 2 + (c[1] - py) ** 2 < s * s


class Projection(unittest.TestCase):
    def test_against_decimals(self):
        for rise in (1, 2, 3, 4, 6, 9, 12, 17):
            for run in (1, 4, 12):
                for length in (1, 2, 5, 1280, 1950720, 3902433, 12345679):
                    self.assertEqual(energy.to_plan(length, {'rise': rise, 'run': run}), to_plan_decimal(length, rise, run),
                                     (length, rise, run))

    def test_exact_hypotenuses(self):
        # a pitch whose hypotenuse is whole projects exactly: 3:4 (5), 24:7 (25) - and never to a tie (2.4)
        self.assertEqual(energy.to_plan(5, {'rise': 3, 'run': 4}), 4)
        self.assertEqual(energy.to_plan(25, {'rise': 3, 'run': 4}), 20)
        self.assertEqual(energy.to_plan(25, {'rise': 24, 'run': 7}), 7)
        self.assertEqual(energy.to_plan(1, {'rise': 4, 'run': 3}), 1)          # 0.6


class Distance(unittest.TestCase):
    def test_against_fractions(self):
        segs = [((0, 0), (10, 0)), ((0, 0), (0, 0)), ((-3, 2), (7, -5)), ((5, 5), (5, -5))]
        for a, b in segs:
            for x in range(-8, 13):
                for y in range(-8, 9):
                    for s in (0, 1, 2, 3, 5):
                        self.assertEqual(energy.too_near((x, y), a, b, s), near_brute((x, y), a, b, s), (x, y, a, b, s))


class EdgeKinds(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(energy.edge_kind((0, 0, 10), (5, 0, 10), 10), 'eave')
        self.assertEqual(energy.edge_kind((0, 0, 20), (5, 0, 20), 10), 'ridge')
        self.assertEqual(energy.edge_kind((0, 0, 10), (5, 5, 20), 10), 'rake')


if __name__ == '__main__':
    unittest.main()

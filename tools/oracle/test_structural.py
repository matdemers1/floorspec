"""FS_structural's oracle: the exact rounding of a span's extent (spec.md 3.2), and its schema tier over
the data on core elements (1.3)."""

import copy
import json
import unittest
from decimal import Decimal, ROUND_HALF_EVEN, getcontext
from fractions import Fraction

from tools.oracle.derive import Doc
from tools.oracle.ext import structural
from tools.oracle.ext_author import FT, framed


def reference(q: Fraction, n: int) -> int:
    """round(q / sqrt(n)), ties to even, in 80-digit decimal arithmetic - far from every tie here."""
    getcontext().prec = 80
    v = Decimal(q.numerator) / Decimal(q.denominator) / Decimal(n).sqrt()
    return int(v.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


class Extent(unittest.TestCase):
    def test_round_div_sqrt_agrees_with_decimal(self):
        for q in (0, 1, 2, 7, 99, 5852160, 2 ** 53 - 1, Fraction(7, 3), Fraction(10 ** 12 + 1, 7)):
            for n in (1, 2, 3, 5, 25, 1000003, 2 ** 52 + 1):
                self.assertEqual(structural._round_div_sqrt(q, n), reference(Fraction(q), n), (q, n))

    def test_exact_squares(self):
        self.assertEqual(structural._round_div_sqrt(15, 25), 3)            # 15 / 5
        self.assertEqual(structural._round_div_sqrt(7, 4), 4)              # 3.5 rounds to even
        self.assertEqual(structural._round_div_sqrt(5, 4), 2)              # 2.5 rounds to even

    def test_extent_of_a_rectangle(self):
        ring = [(0, 0), (8 * FT, 0), (8 * FT, 7 * FT), (0, 7 * FT)]
        self.assertEqual(structural.extent(ring, (0, 1)), 7 * FT)
        self.assertEqual(structural.extent(ring, (0, -5)), 7 * FT)
        self.assertEqual(structural.extent(ring, (1, 1)), reference(Fraction(15 * FT), 2))


class SchemaTier(unittest.TestCase):
    def errors(self, d):
        d = json.loads(json.dumps(d))
        return structural.schema_errors(Doc(d), d.get('extensions', {}).get(structural.NAME, {}))

    def test_the_framed_house_matches(self):
        self.assertEqual(self.errors(framed()), [])

    def test_data_on_each_collection_is_its_own(self):
        d = framed()
        d['walls']['W1']['extensions'][structural.NAME]['span'] = {'direction': [1, 0]}     # a slab's member on a wall
        self.assertTrue(self.errors(d))
        d = framed()
        d['slabs']['S1']['extensions'][structural.NAME]['framing']['system'] = 'rafters'  # a roof's system on a slab
        self.assertTrue(self.errors(d))

    def test_no_other_element_carries_data(self):
        for c, eid in (('levels', 'L1'), ('junctions', 'J1'), ('types', 'EXT')):
            d = copy.deepcopy(framed())
            d[c][eid]['extensions'] = {structural.NAME: {}}
            self.assertEqual(len(self.errors(d)), 1, (c, eid))


if __name__ == '__main__':
    unittest.main()

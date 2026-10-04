"""The reference grammar (Ops chapter 3): lengths, sides, points, vectors and positions, each
expected value worked out by hand in the comment or the table beside it."""

import unittest
from fractions import Fraction

from tools.oracle.ops.errors import OpsError
from tools.oracle.ops.refs import exact_length, half, length
from tools.oracle.ops.select import Resolver, side_of

FT, IN, MM = 390144, 32512, 1280


class LengthTest(unittest.TestCase):
    def test_grammar(self):
        cases = {
            "12'": 12 * FT,
            "12' 6\"": 12 * FT + 6 * IN,
            "12'6-1/2\"": 12 * FT + 6 * IN + IN // 2,          # 4893056
            "12'-6\"": 12 * FT + 6 * IN,
            "12' - 6 1/2\"": 12 * FT + 6 * IN + IN // 2,
            '6 1/2"': 211328,
            '6-1/2"': 211328,
            '6 - 1/2 in': 211328,
            '3/4 in': 24384,
            '3/4"': 24384,
            '6.25"': 203200,
            "1.5'": 585216,
            '1.5 ft': 585216,
            '3810mm': 4876800,
            '381 cm': 4876800,
            '3.81 m': 4876800,
            '.5m': 640000,
            "-2'": -780288,
            " - 2 ' ": -780288,
            '-6 1/2"': -211328,
            '12 FT 6 IN': 12 * FT + 6 * IN,
            '3 MM': 3 * MM,
            '0"': 0,
            "0'": 0,
            '61/2"': 61 * IN // 2,                             # a fraction, not a mixed number
        }
        for s, v in cases.items():
            with self.subTest(s=s):
                self.assertEqual(length(s), v)

    def test_exact_values(self):
        self.assertEqual(exact_length('1/3"'), Fraction(32512, 3))
        self.assertEqual(exact_length('0.1 mm'), 128)
        self.assertEqual(exact_length('1/256 in'), 127)
        self.assertEqual(exact_length('1/16"'), 2032)

    def test_rounding_ties_to_even(self):
        self.assertEqual(length('1/3"'), 10837)              # 10837.33
        self.assertEqual(length('2/3"'), 21675)              # 21674.67
        self.assertEqual(length('1/65024 in'), 0)            # 0.5 -> 0
        self.assertEqual(length('3/65024 in'), 2)            # 1.5 -> 2
        self.assertEqual(length('5/65024 in'), 2)            # 2.5 -> 2
        self.assertEqual(length('7/65024 in'), 4)            # 3.5 -> 4
        self.assertEqual(length('-1/65024 in'), 0)           # -0.5 -> 0
        self.assertEqual(length('-3/65024 in'), -2)          # -1.5 -> -2
        self.assertEqual(length('0.000390625 mm'), 0)        # 0.5
        self.assertEqual(length('0.001171875mm'), 2)         # 1.5

    def test_not_lengths(self):
        for s in ['', '12', '3810', '12 feet', "1 1/2'", "12'-", '1 2"', '1/2', 'mm', '- 3', "12'6", '1.2.3 m',
                  '1 / 2 / 3 in', "2'6\"3", '++2"', '1e3 mm', '½"', "12' 6 ft", '6"6\'']:
            with self.subTest(s=s):
                with self.assertRaises(OpsError) as e:
                    length(s)
                self.assertEqual(e.exception.code, 'FS-OPS-012')

    def test_zero_denominator(self):
        for s in ['1/0"', '0/0 in', '3 1/0"', "2' 1/0\""]:
            with self.subTest(s=s):
                with self.assertRaises(OpsError) as e:
                    length(s)
                self.assertEqual(e.exception.code, 'FS-OPS-012')

    def test_integers_pass_through(self):
        self.assertEqual(length(-7), -7)
        with self.assertRaises(OpsError):
            length(True)
        with self.assertRaises(OpsError):
            length(1.5)

    def test_half(self):
        self.assertEqual([half(v) for v in (3, 1, -1, -3, 4, 5)], [2, 0, 0, -2, 2, 2])


class SideTest(unittest.TestCase):
    def test_axes_and_diagonals(self):
        # each diagonal belongs to the side counter-clockwise before it
        self.assertEqual(side_of((1, 0)), 'east')
        self.assertEqual(side_of((1, 1)), 'east')
        self.assertEqual(side_of((0, 1)), 'north')
        self.assertEqual(side_of((-1, 1)), 'north')
        self.assertEqual(side_of((-1, 0)), 'west')
        self.assertEqual(side_of((-1, -1)), 'west')
        self.assertEqual(side_of((0, -1)), 'south')
        self.assertEqual(side_of((1, -1)), 'south')

    def test_near_diagonals(self):
        self.assertEqual(side_of((1000, 999)), 'east')
        self.assertEqual(side_of((999, 1000)), 'north')
        self.assertEqual(side_of((-1000, 999)), 'west')
        self.assertEqual(side_of((-999, -1000)), 'south')


def doc():
    """J1 (0, 0), J2 (12', 10'), J3 (3', 4'); a wall W1 from J1 to J2."""
    return {
        'junctions': {'J1': {'level': 'L1', 'position': [0, 0]}, 'J2': {'level': 'L1', 'position': [12 * FT, 10 * FT]},
                      'J3': {'level': 'L1', 'position': [3 * FT, 4 * FT]}},
        'walls': {'W1': {'level': 'L1', 'start': 'J1', 'end': 'J2'}},
    }


class PointTest(unittest.TestCase):
    def setUp(self):
        self.r = Resolver(doc())

    def test_forms(self):
        self.assertEqual(self.r.point([FT, '6"'], ''), (FT, 6 * IN))
        self.assertEqual(self.r.point('J3', ''), (3 * FT, 4 * FT))
        self.assertEqual(self.r.point('end of W1', ''), (12 * FT, 10 * FT))
        self.assertEqual(self.r.point("2' east of J3", ''), (5 * FT, 4 * FT))
        self.assertEqual(self.r.point("6\" SOUTH of start of W1", ''), (0, -6 * IN))
        # 5' from J1 toward J3 is J3 itself on a 3-4-5 line; 1' is (0.6', 0.8') rounded per coordinate
        self.assertEqual(self.r.point("5' from J1 toward J3", ''), (3 * FT, 4 * FT))
        self.assertEqual(self.r.point("1' from J1 toward J3", ''), (234086, 312115))     # 234086.4, 312115.2
        # 1 m toward J2 on the irrational diagonal: 1280000 * (12, 10) / sqrt(244)
        self.assertEqual(self.r.point('1 m from J1 toward J2', ''), (983323, 819436))   # 983323.24, 819436.03

    def test_failures(self):
        for v, code in [('nowhere at all', 'FS-OPS-012'), ('J9', 'FS-OPS-003'), ("2' east of J9", 'FS-OPS-003'),
                        ("two feet east of J1", 'FS-OPS-012'), ("1' from J1 toward J1", 'FS-OPS-003'),
                        ('start of W9', 'FS-OPS-003')]:
            with self.subTest(v=v):
                with self.assertRaises(OpsError) as e:
                    self.r.point(v, '')
                self.assertEqual(e.exception.code, code)

    def test_vectors(self):
        self.assertEqual(self.r.vector("2' east", ''), (780288, 0))
        self.assertEqual(self.r.vector("1' 6\" west", ''), (-585216, 0))
        self.assertEqual(self.r.vector(['1 m', -5], ''), (1280000, -5))
        with self.assertRaises(OpsError):
            self.r.vector("2' up", '')

    def test_positions(self):
        D = 3 ** 2 + 5 ** 2                       # a wall of sqrt(34) base units... scaled below
        self.assertEqual(Resolver.position(7, D, 1, ''), 7)
        self.assertEqual(Resolver.position('3"', D, 1, ''), 3 * IN)
        # 12' wall, 36" door: centred at (4681728 - 1170432) / 2
        self.assertEqual(Resolver.position('centered', (12 * FT) ** 2, 36 * IN, ''), 1755648)
        self.assertEqual(Resolver.position("2' from end", (12 * FT) ** 2, 36 * IN, ''), 12 * FT - 2 * FT - 36 * IN)
        self.assertEqual(Resolver.position('18" FROM START', (12 * FT) ** 2, 36 * IN, ''), 18 * IN)
        # sqrt(34) ft = 2274910.896...: centred 30" -> 649775.448 -> 649775
        self.assertEqual(Resolver.position('centered', 34 * FT * FT, 30 * IN, ''), 649775)
        # an odd excess rounds to even: L = 5, w = 2 -> 1.5 -> 2; L = 5, w = 0 -> 2.5 -> 2
        self.assertEqual(Resolver.position('centered', 25, 2, ''), 2)
        self.assertEqual(Resolver.position('centered', 25, 0, ''), 2)


if __name__ == '__main__':
    unittest.main()

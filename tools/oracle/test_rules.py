"""Unit tests of the Floorspec Rules oracle (tools/oracle/rules/): exact arithmetic, display, the
assurance pattern, geometry, wall-line stretches, typing and editions in force."""

import unittest
from fractions import Fraction

from tools.oracle.rules import display, geometry, structure
from tools.oracle.rules.evaluate import DEFAULT_PROFILE, applying_amendments, editions_in_force, type_rule
from tools.oracle.rules.qr import QR, round_div_sqrt, round_frac, round_sqrt
from tools.oracle.rules.wallline import stretches


class QRTest(unittest.TestCase):
    def test_field(self):
        a = QR(1, 1, 2)
        self.assertEqual(a * QR(1, -1, 2), QR(-1))
        self.assertEqual((a / a), QR(1))
        self.assertTrue(QR(0, 1, 2) > Fraction(141, 100) and QR(0, 1, 2) < Fraction(142, 100))
        self.assertEqual(QR(3, 2, 4), QR(7))                    # a perfect square folds into the rational part

    def test_rounding_ties_to_even(self):
        self.assertEqual(QR(Fraction(5, 2)).round(), 2)
        self.assertEqual(QR(Fraction(7, 2)).round(), 4)
        self.assertEqual(QR(Fraction(-5, 2)).round(), -2)
        self.assertEqual(QR(0, 1, 2).round(), 1)
        self.assertEqual(round_frac(Fraction(-3, 2)), -2)

    def test_round_div_sqrt(self):
        self.assertEqual(round_div_sqrt(10, 4), 5)
        self.assertEqual(round_div_sqrt(5, 4), 2)              # 2.5 -> 2
        self.assertEqual(round_div_sqrt(7, 4), 4)              # 3.5 -> 4
        self.assertEqual(round_div_sqrt(-7, 4), -4)
        self.assertEqual(round_div_sqrt(3, 2), 2)              # 2.1213...
        self.assertEqual(round_sqrt(2), 1)
        self.assertEqual(round_sqrt(8), 3)
        self.assertEqual(round_sqrt(6), 2)


class DisplayTest(unittest.TestCase):
    def test_examples_of_9_6(self):
        self.assertEqual(display.length(390144, 'imperial'), '1\' 0"')
        self.assertEqual(display.length(1148080, 'imperial'), '2\' 11 5/16"')
        self.assertEqual(display.area(Fraction(152212340736), 'imperial'), '1.00 sq ft')

    def test_lengths(self):
        self.assertEqual(display.length(0, 'imperial'), '0\' 0"')
        self.assertEqual(display.length(-12800, 'imperial'), '-0\' 0 3/8"')
        self.assertEqual(display.length(1016, 'imperial'), '0\' 0"')     # half a sixteenth: ties to even
        self.assertEqual(display.length(3048, 'imperial'), '0\' 0 1/8"')  # one and a half sixteenths: to 2
        self.assertEqual(display.length(1920, 'metric'), '2 mm')          # 1.5 mm -> 2
        self.assertEqual(display.length(3200, 'metric'), '2 mm')          # 2.5 mm -> 2

    def test_values(self):
        self.assertEqual(display.value('integer', 20, 'imperial', 'A'), '20 A')
        self.assertEqual(display.value('terms', ['smoke', 'heat'], 'imperial'), 'heat, smoke')
        self.assertEqual(display.value('terms', [], 'imperial'), 'none')
        self.assertEqual(display.value('boolean', False, 'imperial'), 'no')
        self.assertEqual(display.value('length', None, 'imperial'), 'not stated')
        self.assertEqual(display.threshold('term', 'in', ['a', 'b'], 'imperial'), 'a, b')


class AssuranceTest(unittest.TestCase):
    def test_matches(self):
        for t in ('It complies.', 'COMPLIANT', 'noncompliance', 'non-compliant', 'comply', 'meets code', 'Meets the codes',
                  'passes the code', 'passed code', 'up to code', 'code approved', 'code-approved'):
            self.assertTrue(structure.assures(t), t)

    def test_does_not_match(self):
        for t in ('complimentary', 'compliances', 'the code passes through', 'encode', 'may not meet IRC 2024 R310',
                  'Check it with a professional or the authority having jurisdiction.', structure.NOTICE):
            self.assertFalse(structure.assures(t), t)


class GeometryTest(unittest.TestCase):
    def test_least_width(self):
        self.assertEqual(geometry.least_width([(0, 0), (10, 0), (10, 4), (0, 4)]), (40, 100))
        c, L = geometry.least_width([(0, 0), (4, 0), (0, 3)])    # a 3-4-5 triangle: its least width is 12/5
        self.assertEqual(Fraction(c * c, L), Fraction(144, 25))

    def test_triangulate_a_concave_polygon(self):
        ring = [(0, 0), (4, 0), (4, 4), (2, 1), (0, 4)]
        tris = geometry.triangulate(ring)
        self.assertEqual(len(tris), 3)
        self.assertEqual(sum(geometry.cross(*t) for t in tris), 20)     # twice the area, 10, as the shoelace gives

    def test_clip(self):
        tri = [(QR(0), QR(0)), (QR(4), QR(0)), (QR(0), QR(4))]
        self.assertEqual(geometry.area_sign(geometry.clip(tri, [(0, 1, 1), (1, 1, 1)])), 1)
        self.assertEqual(geometry.area_sign(geometry.clip(tri, [(0, 2, 1), (1, 2, 1)])), 0)   # only the point (2, 2)


class StretchTest(unittest.TestCase):
    def test_no_break_is_closed(self):
        self.assertEqual(stretches(100, []), [(0, 100, True)])

    def test_breaks_merge_and_wrap(self):
        self.assertEqual(stretches(100, [(10, 20), (15, 30), (90, 100)]), [(30, 90, False), (100, 110, False)])
        self.assertEqual(stretches(100, [(0, 10), (90, 100)]), [(10, 90, False)])


class TypingTest(unittest.TestCase):
    PROV = {'verifiedBy': 'x', 'verifiedOn': '2026-10-04', 'edition': '2024'}

    def rule(self, applies, requirement, **kw):
        return {'title': 't', 'citation': {'code': 'X', 'edition': '2024', 'section': '1'}, 'paraphrase': 'p',
                'applies': applies, 'requirement': requirement, 'severity': 'note', 'provenance': self.PROV, **kw}

    def test_well_typed(self):
        ok, deferred, reads = type_rule(self.rule({'to': 'room'}, {'measure': 'elementCount', 'op': '>=', 'value': 1,
                                                                    'args': {'extension': 'FS_electrical', 'match': {'detects': 'smoke'}}}))
        self.assertEqual((ok, deferred, reads), (True, False, {'FS_electrical'}))

    def test_member_needs_a_named_extension(self):
        req = {'measure': 'elementMember', 'op': '=', 'value': 1, 'args': {'name': 'rating', 'type': 'integer'}}
        self.assertFalse(type_rule(self.rule({'to': 'element'}, req))[0])
        self.assertEqual(type_rule(self.rule({'to': 'element', 'extension': 'FS_electrical'}, req)),
                         (True, False, {'FS_electrical'}))

    def test_deferred(self):
        self.assertEqual(type_rule(self.rule({'to': 'room'}, {'measure': 'ceilingHeight', 'op': 'has', 'value': 'x'}))[:2], (True, True))


class ProfileTest(unittest.TestCase):
    def test_default(self):
        self.assertEqual(editions_in_force(DEFAULT_PROFILE),
                         {'IFGC': '2024', 'IMC': '2024', 'IPC': '2024', 'IRC': '2024', 'NEC': '2026'})

    def test_effective_dates(self):
        p = {'adopts': [{'code': 'A', 'edition': '1', 'effective': '2020-01-01'}, {'code': 'A', 'edition': '2', 'effective': '2025-01-01'},
                        {'code': 'B', 'edition': '9'}]}
        self.assertEqual(editions_in_force(p), {'A': '2', 'B': '9'})
        self.assertEqual(editions_in_force({**p, 'asOf': '2024-12-31'}), {'A': '1', 'B': '9'})
        self.assertEqual(editions_in_force({**p, 'asOf': '2019-12-31'}), {'B': '9'})

    def test_amendments(self):
        p = {'asOf': '2026-01-01', 'amendments': [{'effective': '2026-01-01'}, {'effective': '2026-01-02'}, {}]}
        self.assertEqual(len(applying_amendments(p)), 2)


if __name__ == '__main__':
    unittest.main()

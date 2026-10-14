"""FS_annotation's oracle: the exact field its lengths live in (spec.md 2.3), the lines of a wall's faces
(2.2), an opening's centre, the scenes and views read as data (1.3), `oneOf` in the schema
interpreter, and the derived values of the house with annotation (chapter 6)."""

import json
import math
import unittest
from decimal import Decimal, getcontext
from fractions import Fraction

from tools.oracle.derive import Doc
from tools.oracle.ext import annotation, official
from tools.oracle.ext.annotation import Num
from tools.oracle.ext.common import Context
from tools.oracle.ext.jsonschema import Schema
from tools.oracle.ext_author import (ANNO, ANNOTATED, FT, LGHT, MM, VIEW, annotation_house, chamfer, entry, dim, jA,
                                     oA, pA, wA)
from tools.oracle.validate import check, ext_reader


def ctx(d):
    return Context(Doc(d), annotation.NAME, annotation.SEVERITY)


def codes(ds):
    return sorted((x['code'], tuple(x['elements'])) for x in ds)


def DMS(d):
    return d['extensions'][ANNO]['dimensions']


def NTS(d):
    return d['extensions'][ANNO]['notes']


def measure(d, did):
    return annotation.measure(Doc(d), DMS(d)[did])


class Field(unittest.TestCase):
    def test_signs_of_one_root(self):
        g = (2,)
        self.assertEqual(Num.of(g, 0, [(0, 1)]).sign(), 1)
        self.assertEqual(Num.of(g, 1, [(0, -1)]).sign(), -1)                 # 1 - sqrt 2
        self.assertEqual(Num.of(g, Fraction(3, 2), [(0, -1)]).sign(), 1)     # 1.5 - sqrt 2
        self.assertEqual(Num.of(g, 0).sign(), 0)

    def test_signs_of_three_roots(self):
        # sqrt 2 + sqrt 3 - sqrt 10 = 3.146 - 3.162 < 0; and sqrt 2 + sqrt 3 - pi-ish rational
        g = (2, 3, 10)
        self.assertEqual(Num.of(g, 0, [(0, 1), (1, 1), (2, -1)]).sign(), -1)
        self.assertEqual(Num.of(g, Fraction(-314, 100), [(0, 1), (1, 1)]).sign(), 1)
        self.assertEqual(Num.of(g, Fraction(-315, 100), [(0, 1), (1, 1)]).sign(), -1)

    def test_perfect_squares_and_equal_roots(self):
        self.assertEqual(Num.of((4, 9), 5, [(0, -1), (1, -1)]).sign(), 0)      # 5 - 2 - 3
        self.assertEqual(Num.of((2, 2), 0, [(0, 1), (1, -1)]).sign(), 0)       # sqrt 2 - sqrt 2
        self.assertEqual((Num.of((2, 2), 0, [(0, 1)]) * Num.of((2, 2), 0, [(1, 1)])).sign(), 1)

    def test_products(self):
        a = Num.of((2, 3), 1, [(0, 1)])             # 1 + sqrt 2
        b = Num.of((2, 3), 0, [(1, 1)])             # sqrt 3
        self.assertAlmostEqual(float(a * b), (1 + math.sqrt(2)) * math.sqrt(3))
        self.assertEqual((a * a - Num.of((2, 3), 3, [(0, 2)])).sign(), 0)     # (1 + sqrt 2)^2 = 3 + 2 sqrt 2

    def test_round_half_to_even(self):
        self.assertEqual(Num.of((1,), Fraction(5, 2)).round(), 2)
        self.assertEqual(Num.of((1,), Fraction(7, 2)).round(), 4)
        self.assertEqual(Num.of((2,), 0, [(0, 1)]).round(), 1)
        self.assertEqual(Num.of((2,), 0, [(0, 4681728 * 12)]).round(), round(4681728 * 12 * math.sqrt(2)))

    def test_rounding_against_decimals(self):
        getcontext().prec = 60
        for a, b, m, n in ((7, 3, 13, 2), (-5, 11, 26, 5), (123456789, -7, 2 ** 40 + 1, 3)):
            x = Num.of((m, n), a, [(0, b)]) * Num.of((m, n), 0, [(1, 1)])
            want = (Decimal(a) + Decimal(b) * Decimal(m).sqrt()) * Decimal(n).sqrt()
            self.assertEqual(x.round(), int(want.to_integral_value()))


class Anchors(unittest.TestCase):
    def test_the_faces_of_a_centred_wall(self):
        doc = Doc(annotation_house())
        S, e, nu, lam = annotation.wall_line(doc, wA('W1', 'left'))
        self.assertEqual((S, e, nu, lam), ([0, 0], (0, 12 * FT), (-12 * FT, 0), 50 * MM))
        self.assertEqual(annotation.wall_line(doc, wA('W1', 'right'))[3], -50 * MM)
        self.assertEqual(annotation.wall_line(doc, wA('W1', 'location'))[3], 0)

    def test_a_justified_wall(self):
        d = annotation_house()
        d['walls']['W1']['justification'] = 'exteriorFace'
        doc = Doc(d)
        self.assertEqual(annotation.wall_line(doc, wA('W1', 'left'))[3], 0)
        self.assertEqual(annotation.wall_line(doc, wA('W1', 'right'))[3], -100 * MM)

    def test_positions(self):
        d = annotation_house()
        doc, dm = Doc(d), DMS(d)['DM2']
        # the west wall's outside face, x = -50 mm; the window's centre, 6' east; J3, 12' east
        a, b, m = annotation.scaled_position(doc, dm, wA('W1', 'left'))
        self.assertEqual((m, a + b * math.isqrt(m)), (144 * FT * FT, -50 * MM))
        a, b, m = annotation.scaled_position(doc, dm, oA('O1'))
        self.assertEqual(a + b * Fraction(math.isqrt(m)), 6 * FT)
        self.assertEqual(annotation.scaled_position(doc, dm, jA('J3')), (12 * FT, 0, 1))

    def test_levels(self):
        doc = Doc(annotation_house())
        self.assertEqual(annotation.anchor_level(doc, jA('J1')), 'L1')
        self.assertEqual(annotation.anchor_level(doc, oA('O1')), 'L1')
        self.assertIsNone(annotation.anchor_level(doc, jA('W1')))
        self.assertIsNone(annotation.anchor_level(doc, oA('J1')))
        self.assertIs(annotation.anchor_level(doc, pA(0, 0)), True)


class Measuring(unittest.TestCase):
    def test_the_house(self):
        d = annotation_house()
        for did, want in ANNOTATED['dimensions'].items():
            lengths, total, zero = measure(d, did)
            self.assertEqual((lengths, total, zero), (want['lengths'], want['total'], False), did)

    def test_direction_scale_and_sign_do_not_matter(self):
        for direction in ([2, 0], [-1, 0], [-7, 0]):
            d = annotation_house()
            DMS(d)['DM1']['direction'] = direction
            self.assertEqual(measure(d, 'DM1')[:2], (ANNOTATED['dimensions']['DM1']['lengths'], ANNOTATED['dimensions']['DM1']['total']))

    def test_through_moves_an_oblique_line_only(self):
        d = annotation_house()
        chamfer(d)
        for y, want in ((9 * FT + 6 * 32512, 4 * 32512), (10 * FT + 6 * 32512, 12 * 32512)):
            DMS(d)['DM9'] = dim('L1', [1, 0], [0, y], [jA('J9'), wA('W11', 'location')])
            self.assertEqual(measure(d, 'DM9')[1], want)
        DMS(d)['DM9'] = dim('L1', [1, 0], [0, 123], [jA('J9'), jA('J3')])
        self.assertEqual(measure(d, 'DM9')[1], 12 * FT)

    def test_oblique_thickness(self):
        # a 100 mm wall crossed at 45 degrees is 100 mm x sqrt 2 thick along the string
        d = annotation_house()
        DMS(d)['DM9'] = dim('L1', [1, 1], [0, 3 * FT], [wA('W1', 'left'), wA('W1', 'right')])
        self.assertEqual(measure(d, 'DM9')[1], round(100 * MM * math.sqrt(2)))

    def test_zero_segments_are_exact(self):
        d = annotation_house()
        DMS(d)['DM9'] = dim('L1', [1, 2], [0, 0], [pA(0, 0), pA(1, 0), pA(1, 0)])
        lengths, total, zero = measure(d, 'DM9')
        self.assertEqual((lengths, total, zero), ([0, 0], 0, True))
        DMS(d)['DM9'] = dim('L1', [1, 2], [0, 0], [pA(0, 0), pA(1, 0)])
        self.assertFalse(measure(d, 'DM9')[2])

    def test_the_total_is_not_the_sum(self):
        d = annotation_house()
        DMS(d)['DM9'] = dim('L1', [1, 2], [0, 0], [pA(k, 0) for k in range(4)])
        self.assertEqual(measure(d, 'DM9')[:2], ([0, 0, 0], 1))

    def test_large_lengths_are_exact(self):
        big = 2 ** 53 - 1
        d = annotation_house()
        DMS(d)['DM9'] = dim('L1', [big, big - 1], [-big, big], [pA(-big, -big), pA(big, big)])
        getcontext().prec = 80
        n = Decimal(big) ** 2 + Decimal(big - 1) ** 2
        want = abs((Decimal(2 * big) * big + Decimal(2 * big) * (big - 1)) / n.sqrt())
        self.assertEqual(measure(d, 'DM9')[1], int(want.to_integral_value()))


class ReadAsData(unittest.TestCase):
    def test_the_scenes_and_the_views(self):
        self.assertEqual(annotation.read_as_data(ctx(annotation_house())), {'LS1', 'LS2', 'SV1', 'SV2', 'SV3', 'SV4'})

    def test_none_when_the_data_is_not_an_object(self):
        for data in ('x', [], None, {'scenes': [], 'views': []}, {}):
            d = annotation_house()
            d['extensions'][LGHT] = data
            d['extensions'][VIEW] = data
            self.assertEqual(annotation.read_as_data(ctx(d)), set(), data)


class OneOf(unittest.TestCase):
    def test_the_interpreter(self):
        s = Schema({'oneOf': [{'type': 'string'}, {'type': 'integer', 'minimum': 0}, {'type': 'integer', 'maximum': 5}]})
        self.assertEqual(s.errors('a'), [])
        self.assertEqual(s.errors(9), [])
        self.assertEqual(s.errors(-1), [])
        self.assertEqual(len(s.errors(3)), 1)             # two branches
        self.assertEqual(len(s.errors(True)), 1)          # none

    def test_anchors(self):
        base = {'level': 'L1', 'direction': [1, 0], 'through': [0, 0]}
        for a in (jA('J1'), wA('W1', 'left'), oA('O1'), pA(0, 0)):
            self.assertEqual(annotation.SCHEMA.errors({'dimensions': {'DM1': {**base, 'anchors': [a, a]}}}), [], a)
        for a in ({}, {'junction': 'J1', 'opening': 'O1'}, {'wall': 'W1'}, {'face': 'left'}, {'point': [0, 0, 0]}):
            self.assertNotEqual(annotation.SCHEMA.errors({'dimensions': {'DM1': {**base, 'anchors': [a, jA('J1')]}}}), [], a)


class Rules(unittest.TestCase):
    def test_the_house_breaks_nothing(self):
        self.assertEqual(annotation.invariants(ctx(annotation_house())), [])
        self.assertEqual(annotation.lints(ctx(annotation_house())), [])

    def test_a_note_and_a_string_of_one_id(self):
        d = annotation_house()
        NTS(d)['DM1'] = NTS(d).pop('NT1')
        self.assertEqual(codes(annotation.invariants(ctx(d))), [('FS-ANNO-INV-001', ('DM1',))])

    def test_unresolved_strings_are_not_measured(self):
        d = annotation_house()
        DMS(d)['DM1']['anchors'] = [jA('J9'), jA('J6'), jA('J6')]
        self.assertEqual(codes(annotation.lints(ctx(d))), [('FS-ANNO-LINT-001', ('DM1',))])
        self.assertEqual(annotation.derive(ctx(d))['dimensions']['DM1'], {'level': 'L1', 'lengths': None, 'total': None})


class Derived(unittest.TestCase):
    def test_the_house_with_annotation(self):
        data = json.dumps(annotation_house()).encode('utf-8')
        result, _, _ = check(data, ext_reader(data), json.dumps([entry(ANNO)]).encode('utf-8'), official.implemented(ANNO))
        self.assertTrue(result['valid'], result['diagnostics'])
        self.assertEqual(result['derived']['extensions'], {ANNO: ANNOTATED})


if __name__ == '__main__':
    unittest.main()

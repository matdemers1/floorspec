"""FS_views's oracle: FS_lighting's scenes read as data (spec.md 1.3), the Gregorian rule for `at`
(3.2.1), the exact test of a steep line of sight (5.3), `dependentRequired` in the schema interpreter,
and the derived values of the house with views (chapter 6)."""

import json
import unittest

from tools.oracle.derive import Doc
from tools.oracle.ext import official, views
from tools.oracle.ext.common import Context
from tools.oracle.ext.jsonschema import Schema
from tools.oracle.ext_author import LGHT, VIEW, VIEWED, entry, views_house
from tools.oracle.validate import check, ext_reader


def ctx(d):
    return Context(Doc(d), views.NAME, views.SEVERITY)


def codes(ds):
    return sorted((x['code'], tuple(x['elements'])) for x in ds)


def VWS(d):
    return d['extensions'][VIEW]['views']


class Scenes(unittest.TestCase):
    def test_the_scenes_of_lighting_data(self):
        self.assertEqual(views.scenes(ctx(views_house())), {'LS1', 'LS2'})

    def test_no_scenes_when_the_data_is_not_an_object(self):
        for data in ('evening', [], None, {'scenes': []}, {'scenes': 'LS1'}, {}):
            d = views_house()
            d['extensions'][LGHT] = data
            self.assertEqual(views.scenes(ctx(d)), set(), data)

    def test_no_scenes_without_lighting(self):
        d = views_house()
        d['extensions'].pop(LGHT)
        self.assertEqual(views.scenes(ctx(d)), set())


class Days(unittest.TestCase):
    def test_the_gregorian_rule(self):
        self.assertTrue(views.leap(2028))
        self.assertTrue(views.leap(2000))
        self.assertTrue(views.leap(0))
        self.assertFalse(views.leap(2027))
        self.assertFalse(views.leap(2100))
        self.assertFalse(views.leap(1900))

    def test_the_days_a_month_has(self):
        self.assertTrue(views.day_exists('2028-02-29T12:00'))
        self.assertFalse(views.day_exists('2027-02-29T12:00'))
        self.assertFalse(views.day_exists('2028-02-30T12:00'))
        self.assertFalse(views.day_exists('2026-04-31T12:00'))
        self.assertTrue(views.day_exists('2026-05-31T12:00+14:00'))
        self.assertTrue(views.day_exists('2026-12-31T23:59:59Z'))
        for month, days in enumerate(views.DAYS, 1):
            self.assertTrue(views.day_exists(f'2026-{month:02d}-{days:02d}T00:00'))
            if days < 31:
                self.assertFalse(views.day_exists(f'2026-{month:02d}-{days + 1:02d}T00:00'))


class Steep(unittest.TestCase):
    def v(self, d):
        return {'eye': [0, 0, 0], 'target': d}

    def test_either_side_of_30_degrees(self):
        self.assertTrue(views.steep(self.v([1732, 0, 1000])))        # 3,000,000 > 2,999,824
        self.assertFalse(views.steep(self.v([1733, 0, 1000])))       # 3,000,000 < 3,003,289
        self.assertTrue(views.steep(self.v([0, -1732, -1000])))      # looking down, north-south
        self.assertFalse(views.steep(self.v([5, 5, 0])))             # level

    def test_straight_up_and_down(self):
        self.assertTrue(views.steep(self.v([0, 0, 1])))
        self.assertTrue(views.steep(self.v([0, 0, -1])))

    def test_exactly_30_degrees_never_happens(self):
        # x^2 + y^2 = 3 z^2 has no integer solution but 0: 3 never divides a sum of two squares
        # an odd number of times
        self.assertEqual([(x, y, z) for x in range(60) for y in range(60) for z in range(1, 40)
                          if x * x + y * y == 3 * z * z], [])

    def test_large_lengths_are_exact(self):
        big = 2 ** 53 - 1
        self.assertTrue(views.steep({'eye': [-big, 0, -big], 'target': [big, 0, big]}))
        self.assertFalse(views.steep({'eye': [-big, -big, 0], 'target': [big, big, big]}))


class DependentRequired(unittest.TestCase):
    def test_the_interpreter(self):
        s = Schema({'type': 'object', 'dependentRequired': {'focus': ['aperture']}})
        self.assertEqual(s.errors({}), [])
        self.assertEqual(s.errors({'aperture': 'f/8'}), [])
        self.assertEqual(s.errors({'aperture': 'f/8', 'focus': 1}), [])
        self.assertEqual(len(s.errors({'focus': 1})), 1)

    def test_the_schema(self):
        v = {'name': 'N', 'eye': [0, 0, 0], 'target': [1, 0, 0]}
        self.assertEqual(views.SCHEMA.errors({'views': {'SV1': v}}), [])
        self.assertNotEqual(views.SCHEMA.errors({'views': {'SV1': {**v, 'focus': 1}}}), [])
        self.assertNotEqual(views.SCHEMA.errors({'views': {'SV1': {**v, 'levels': 'only'}}}), [])
        self.assertEqual(views.SCHEMA.errors({'views': {'SV1': {**v, 'level': 'L1', 'levels': 'only'}}}), [])


class Invariants(unittest.TestCase):
    def test_the_house_breaks_none(self):
        self.assertEqual(views.invariants(ctx(views_house())), [])

    def test_lights_off_only_when_written(self):
        d = views_house()
        self.assertNotIn('lights', VWS(d)['SV3'])
        VWS(d)['SV3']['lights'] = 'off'
        self.assertEqual(codes(views.invariants(ctx(d))), [('FS-VIEW-INV-005', ('SV3',))])

    def test_a_view_named_as_a_scene(self):
        d = views_house()
        VWS(d)['LS2'] = VWS(d).pop('SV4')
        VWS(d)['SV3']['name'] = 'Evening'
        self.assertEqual(codes(views.invariants(ctx(d))), [('FS-VIEW-INV-001', ('LS2',))])


class Lints(unittest.TestCase):
    def test_the_house_reports_none(self):
        self.assertEqual(views.lints(ctx(views_house())), [])

    def test_only_two_point_views(self):
        d = views_house()
        VWS(d)['SV4']['twoPoint'] = True
        self.assertEqual(codes(views.lints(ctx(d))), [('FS-VIEW-LINT-001', ('SV4',))])


class Derived(unittest.TestCase):
    def test_the_house_with_views(self):
        data = json.dumps(views_house()).encode('utf-8')
        result, _, _ = check(data, ext_reader(data), json.dumps([entry(VIEW)]).encode('utf-8'),
                             official.implemented(VIEW))
        self.assertTrue(result['valid'], result['diagnostics'])
        self.assertEqual(result['derived']['extensions'], {VIEW: VIEWED})


if __name__ == '__main__':
    unittest.main()

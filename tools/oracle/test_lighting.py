"""FS_lighting's oracle: what gives light (spec.md 2.1.1, 3.1.1), a range's order before its colour
temperature (2.1.2, 2.1.3, 5.2), the lints' conditions (5.3) - reading FS_electrical's switches as they
are - and the derived values of the lit house (chapter 6)."""

import json
import unittest

from tools.oracle.ext import lighting, official
from tools.oracle.ext.common import Context
from tools.oracle.derive import Doc
from tools.oracle.ext_author import ELEC, LGHT, entry, lit_house
from tools.oracle.validate import check, ext_reader


def ctx(d):
    return Context(Doc(d), lighting.NAME, lighting.SEVERITY)


def codes(ds):
    return sorted((x['code'], tuple(x['elements'])) for x in ds)


class GivesLight(unittest.TestCase):
    def test_lights_and_other_extensions_elements(self):
        c = ctx(lit_house())
        self.assertTrue(lighting.gives_light(c, 'X2'))          # a light of FS_electrical
        self.assertTrue(lighting.gives_light(c, 'X20'))         # an FS_furniture lamp
        self.assertFalse(lighting.gives_light(c, 'X10'))        # a switch
        self.assertFalse(lighting.gives_light(c, 'X1'))         # a panel
        self.assertFalse(lighting.gives_light(c, 'W1'))         # a core element
        self.assertFalse(lighting.gives_light(c, 'LS1'))        # a scene
        self.assertFalse(lighting.gives_light(c, 'X99'))        # nothing


class Invariants(unittest.TestCase):
    def test_the_lit_house_breaks_none(self):
        self.assertEqual(lighting.invariants(ctx(lit_house())), [])

    def test_a_reversed_range_hides_the_cct_check(self):
        d = lit_house()
        d['extensions'][LGHT]['luminaires']['X4'].update(cctRange=[5000, 2700], cct=6500)
        d['extensions'][LGHT]['luminaires']['X5'].update(cct=6500)
        self.assertEqual(codes(lighting.invariants(ctx(d))),
                         [('FS-LGHT-INV-003', ('X4',)), ('FS-LGHT-INV-004', ('X5',))])

    def test_names_compared_exactly(self):
        d = lit_house()
        d['extensions'][LGHT]['scenes'].update(LS3={'name': 'evening'}, LS4={'name': 'Evening '})
        self.assertEqual(lighting.invariants(ctx(d)), [])


class Lints(unittest.TestCase):
    def test_the_lit_house_reports_none(self):
        self.assertEqual(lighting.lints(ctx(lit_house())), [])

    def test_cct_against_a_range_and_a_fixed_cct(self):
        d = lit_house()
        on = d['extensions'][LGHT]['scenes']['LS1']['on']
        on['X4']['cct'] = 2699                                   # under the range
        on['X5']['cct'] = 5000                                   # its coolest: fine
        on['X2']['cct'] = 2701                                   # not the one it gives
        on['X3']['cct'] = 2700                                   # the one it gives
        self.assertEqual(codes(lighting.lints(ctx(d))),
                         [('FS-LGHT-LINT-002', ('LS1', 'X2')), ('FS-LGHT-LINT-002', ('LS1', 'X4'))])

    def test_switches_read_as_they_are(self):
        d = lit_house()
        sw = d['extensions'][ELEC]['collections']['switches']
        sw['X10']['controls'] = 'X2'                              # not an array: lists nothing
        sw['X11']['control'] = ['smart']                          # not "dimmer" or "smart"
        self.assertEqual(codes(lighting.lints(ctx(d))),
                         [('FS-LGHT-LINT-003', ('LS1', 'X2')), ('FS-LGHT-LINT-003', ('LS1', 'X3')),
                          ('FS-LGHT-LINT-003', ('LS1', 'X4')), ('FS-LGHT-LINT-003', ('LS1', 'X5')),
                          ('FS-LGHT-LINT-003', ('LS2', 'X3'))])


class Derived(unittest.TestCase):
    def test_the_lit_house(self):
        data = json.dumps(lit_house()).encode('utf-8')
        r, _, _ = check(data, ext_reader(data), json.dumps([entry(LGHT)]).encode('utf-8'), official.implemented(LGHT))
        x = r['derived']['extensions'][LGHT]
        self.assertEqual(x['scenes']['LS2'], {'name': 'Night light', 'on': ['X20', 'X3'], 'dimmed': ['X20', 'X3']})
        self.assertEqual(list(x['luminaires']), ['X2', 'X20', 'X3', 'X4', 'X5', 'X6', 'X7'])
        self.assertEqual(x['luminaires']['X6'], {'scenes': []})


if __name__ == '__main__':
    unittest.main()

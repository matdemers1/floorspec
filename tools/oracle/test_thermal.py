"""FS_thermal's oracle: a layer's resistance and heat capacity, rounded once, ties to even (spec.md 3.1),
checked against decimal arithmetic; the paths of an assembly (3.2); and its schema tier over the data on
core elements (1.3)."""

import copy
import unittest
from decimal import Decimal, ROUND_HALF_EVEN, getcontext

from tools.oracle.derive import Doc
from tools.oracle.ext import thermal
from tools.oracle.ext_author import IN, envelope_house


def reference(num: int, den: int) -> int:
    getcontext().prec = 60
    return int((Decimal(num) / Decimal(den)).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def with_material(**t):
    return {'materials': {'M': {'extensions': {thermal.NAME: t}}}}


class Layer(unittest.TestCase):
    def test_resistance_agrees_with_decimal(self):
        for t in (1, 16, 48, 16256, 178816, 9 * IN, 2 ** 40 + 7):
            for k in (1, 25, 35, 160, 1700, 390000, 1000000):
                r, _ = thermal.layer_values(with_material(conductivity=k), t, 'M')
                self.assertEqual(r, reference(25 * t, 32 * k), (t, k))

    def test_ties_to_even(self):
        d = with_material(conductivity=25, density=1, specificHeat=1)
        self.assertEqual(thermal.layer_values(d, 16, 'M'), (0, 0))         # 0.5 -> 0
        self.assertEqual(thermal.layer_values(d, 48, 'M'), (2, 0))         # 1.5 -> 2
        self.assertEqual(thermal.layer_values(d, 80, 'M')[0], 2)           # 2.5 -> 2
        self.assertEqual(thermal.layer_values(d, 640000, 'M')[1], 0)       # 0.5 -> 0
        self.assertEqual(thermal.layer_values(d, 1920000, 'M')[1], 2)      # 1.5 -> 2

    def test_stated_resistance_ignores_thickness(self):
        for t in (1, 12192, 10 ** 9):
            self.assertEqual(thermal.layer_values(with_material(resistance=35), t, 'M'), (35, None))

    def test_unknown(self):
        self.assertEqual(thermal.layer_values(with_material(density=800), 100, 'M'), (None, None))
        self.assertEqual(thermal.layer_values(with_material(conductivity=160), 100, None), (None, None))
        self.assertEqual(thermal.layer_values({'materials': {'M': {}}}, 100, 'M'), (None, None))


class Paths(unittest.TestCase):
    def test_framed_path_replaces_core_layers_only(self):
        d = envelope_house()
        ew1 = d['types']['EW1']
        out = thermal.derive_assembly(d, ew1['layers'], ew1['extensions'][thermal.NAME]['framing'])
        rs = [x['resistance'] for x in out['layers']]
        stud, _ = thermal.layer_values(d, 11 * IN // 2, 'M-SPF')
        self.assertEqual(out['clear']['resistance'], sum(rs))
        self.assertEqual(out['framed']['resistance'], sum(rs) - rs[5] + stud)
        self.assertEqual(out['framed']['fraction'], 230)

    def test_a_null_makes_the_path_null(self):
        d = envelope_house()
        layers = copy.deepcopy(d['types']['IW1']['layers'])
        layers[1].pop('material')
        out = thermal.derive_assembly(d, layers, None)
        self.assertIsNone(out['clear']['resistance'])
        self.assertNotIn('framed', out)


class SchemaTier(unittest.TestCase):
    def test_house_passes(self):
        self.assertEqual(thermal.schema_errors(Doc(envelope_house()), {}), [])

    def test_type_checked_by_its_kind(self):
        d = envelope_house()
        d['types']['WT1']['extensions'][thermal.NAME]['framing'] = {'material': 'M-SPF', 'fraction': 100}
        self.assertTrue(thermal.schema_errors(Doc(d), {}))
        d = envelope_house()
        d['types']['EW1']['extensions'][thermal.NAME]['uFactor'] = 200
        self.assertTrue(thermal.schema_errors(Doc(d), {}))

    def test_data_on_a_wall_is_refused(self):
        d = envelope_house()
        d['walls']['W1']['extensions'] = {thermal.NAME: {}}
        self.assertEqual(thermal.schema_errors(Doc(d), {}), ['walls/W1: may not carry FS_thermal data'])


if __name__ == '__main__':
    unittest.main()

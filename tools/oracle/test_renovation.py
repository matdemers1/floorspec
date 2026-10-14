"""FS_renovation's oracle: statuses and their defaults (spec.md 2.1), the views of the two states
(2.2), references across states (2.3), and the quantities and areas of the kitchen remodel (chapter 5)."""

import unittest

from tools.oracle.derive import Doc
from tools.oracle.ext import renovation
from tools.oracle.ext.common import Context
from tools.oracle.ext_author import FT, RENO, remodel, unmark_all


def ctx(d):
    return Context(Doc(d), renovation.NAME, renovation.SEVERITY)


class Statuses(unittest.TestCase):
    def test_an_absent_status_is_existing(self):
        st = renovation.statuses(remodel())
        self.assertEqual(st['W1'], 'existing')
        self.assertEqual(st['X3'], 'existing')
        self.assertEqual((st['W8'], st['W12'], st['X1'], st['X2']), ('demolish', 'new', 'demolish', 'new'))

    def test_junctions_and_levels_have_none(self):
        st = renovation.statuses(remodel())
        self.assertNotIn('J7', st)
        self.assertNotIn('L1', st)

    def test_an_entry_naming_nothing_is_ignored(self):
        d = remodel()
        d['extensions'][RENO]['elements']['X9'] = 'new'
        self.assertNotIn('X9', renovation.statuses(d))


class Views(unittest.TestCase):
    def test_the_existing_state_has_no_new_element(self):
        v = renovation.view(remodel(), 'existing')
        self.assertNotIn('W12', v['walls'])
        self.assertIn('W8', v['walls'])
        self.assertNotIn('X2', v['extensions']['FS_furniture']['collections']['casework'])

    def test_the_proposed_state_has_no_demolished_element_and_drops_the_join(self):
        d = remodel()
        v = renovation.view(d, 'proposed')
        self.assertNotIn('W8', v['walls'])
        self.assertNotIn('join', v['junctions']['J7'])
        self.assertIn('join', d['junctions']['J7'])

    def test_both_views_are_valid_core(self):
        d = remodel()
        self.assertEqual(renovation.core_errors(renovation.view(d, 'existing')), [])
        self.assertEqual(renovation.core_errors(renovation.view(d, 'proposed')), [])


class Invariants(unittest.TestCase):
    def test_a_reference_into_the_other_state(self):
        d = remodel()
        d['walls']['W10']['extensions'] = {RENO: {'status': 'demolish'}}
        self.assertEqual([(x['code'], x['elements']) for x in renovation.invariants(ctx(d))],
                         [('FS-RENO-INV-002', ['O3', 'W10'])])

    def test_the_house_as_it_stands_reports_the_lint(self):
        d = remodel()
        unmark_all(d)
        self.assertEqual(renovation.invariants(ctx(d)), [])
        self.assertEqual([x['code'] for x in renovation.lints(ctx(d))], ['FS-RENO-LINT-001'])


class Derived(unittest.TestCase):
    def test_wall_lengths_and_slab_area(self):
        x = renovation.derive(ctx(remodel()))
        self.assertEqual(x['quantities']['demolish']['wallLength'], 6 * FT)
        self.assertEqual(x['quantities']['new']['slabArea'], str(56 * FT * FT))
        self.assertEqual(x['quantities']['existing']['walls'], 11)

    def test_the_states_rooms(self):
        x = renovation.derive(ctx(remodel()))
        self.assertEqual(sorted(x['states']['existing']['rooms']), ['R1', 'R2', 'R3'])
        self.assertEqual(sorted(x['states']['proposed']['rooms']), ['R1', 'R2', 'R4'])
        self.assertGreater(int(x['states']['proposed']['rooms']['R1']), int(x['states']['existing']['rooms']['R1']))

    def test_a_half_area(self):
        self.assertEqual(renovation._area2('12.5'), 25)
        self.assertEqual(renovation._area2('12'), 24)


if __name__ == '__main__':
    unittest.main()

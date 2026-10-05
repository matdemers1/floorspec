"""Unit tests of design options (Core 0.3, chapter 19): views, checked designs, design inputs, how an
option design's diagnostics are merged with the primary design's, and `affected`."""

import unittest

from tools.oracle import options


def doc():
    return {
        'floorspec': '0.3', 'project': {'name': 't'},
        'junctions': {'J1': {'level': 'L1', 'position': [0, 0]},
                      'JA': {'level': 'L1', 'position': [1, 0], 'option': 'A'},
                      'JB': {'level': 'L1', 'position': [2, 0], 'option': 'B'}},
        'optionSets': {'S': {'primary': 'A'}, 'T': {'primary': 'C'}},
        'options': {'A': {'set': 'S'}, 'B': {'set': 'S'}, 'C': {'set': 'T'}, 'D': {'set': 'T'}},
        'extensions': {'FS_x': {'collections': {'things': {'X1': {'fallback': {}, 'option': 'D'},
                                                            'X2': {'fallback': {}}}}}},
    }


class Views(unittest.TestCase):
    def test_view_keeps_common_and_chosen_and_strips_membership(self):
        v = options.view(doc(), {'S': 'B', 'T': 'C'})
        self.assertEqual(sorted(v['junctions']), ['J1', 'JB'])
        self.assertNotIn('option', v['junctions']['JB'])
        self.assertNotIn('optionSets', v)
        self.assertNotIn('options', v)
        self.assertEqual(sorted(v['extensions']['FS_x']['collections']['things']), ['X2'])

    def test_view_leaves_the_document_unchanged(self):
        d = doc()
        options.view(d, {'S': 'B', 'T': 'D'})
        self.assertEqual(d, doc())

    def test_membership_includes_extension_elements(self):
        self.assertEqual(options.membership(doc()), {'JA': 'A', 'JB': 'B', 'X1': 'D'})


class Designs(unittest.TestCase):
    def test_checked_designs_are_the_primary_then_each_other_option(self):
        self.assertEqual(options.checked_designs(doc()), [
            (None, {'S': 'A', 'T': 'C'}), ('B', {'S': 'B', 'T': 'C'}), ('D', {'S': 'A', 'T': 'D'})])

    def test_resolve_fills_in_primaries_and_rejects_strangers(self):
        self.assertEqual(options.resolve(doc(), {'T': 'D'}), {'S': 'A', 'T': 'D'})
        self.assertEqual(options.resolve(doc(), {}), {'S': 'A', 'T': 'C'})
        self.assertIsNone(options.resolve(doc(), {'S': 'D'}))
        self.assertIsNone(options.resolve(doc(), {'U': 'A'}))
        self.assertIsNone(options.resolve(doc(), {'S': 1}))
        self.assertIsNone(options.resolve(doc(), ['S']))

    def test_tag_of(self):
        self.assertIsNone(options.tag_of(doc(), {'S': 'A', 'T': 'C'}))
        self.assertEqual(options.tag_of(doc(), {'S': 'B', 'T': 'C'}), 'B')
        self.assertIs(options.tag_of(doc(), {'S': 'B', 'T': 'D'}), False)


def dg(code, *elements):
    return {'code': code, 'severity': 'info', 'elements': list(elements)}


class Merge(unittest.TestCase):
    def test_an_option_design_reports_only_what_is_new_counted(self):
        primary = [dg('FS-LINT-003'), dg('FS-LINT-002', 'J1')]
        b = [dg('FS-LINT-003'), dg('FS-LINT-003'), dg('FS-LINT-002', 'J1'), dg('FS-LINT-002', 'J9')]
        out = options.merge([(None, primary), ('B', b)])
        self.assertEqual(out, primary + [{**dg('FS-LINT-003'), 'design': 'B'}, {**dg('FS-LINT-002', 'J9'), 'design': 'B'}])

    def test_each_option_design_is_compared_with_the_primary_alone(self):
        out = options.merge([(None, []), ('B', [dg('X')]), ('D', [dg('X')])])
        self.assertEqual([x.get('design') for x in out], ['B', 'D'])


class Affected(unittest.TestCase):
    def test_only_ids_in_both_whose_values_differ(self):
        a = {'walls': {'W1': {'x': 1}, 'W2': {'x': 1}, 'WA': {'x': 1}}, 'unanchored': [],
             'program': {'items': {'P': {'rooms': ['R1']}}, 'adjacency': []}, 'options': {'S': {}}}
        b = {'walls': {'W1': {'x': 1}, 'W2': {'x': 2}, 'WB': {'x': 1}}, 'unanchored': [1],
             'program': {'items': {'P': {'rooms': ['R2']}}, 'adjacency': []}}
        self.assertEqual(options.affected(a, b), ['P', 'W2'])


if __name__ == '__main__':
    unittest.main()

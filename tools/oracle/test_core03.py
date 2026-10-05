"""Core 0.3 in the oracle: the schema tier's new members, the clear-opening invariants, the derived
clear opening, and a 0.3 reader reading earlier drafts exactly (1.2.6)."""
import copy
import json
import os
import unittest

from tools.oracle import schema
from tools.oracle.validate import READER_02, READER_03, check

MM = 1280
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))


def doc(version='0.3', door=None, opening=None):
    d = {'floorspec': version, 'project': {'name': 'x'}, 'buildings': {'B1': {}},
         'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': 2700 * MM}},
         'junctions': {'J1': {'level': 'L1', 'position': [0, 0]}, 'J2': {'level': 'L1', 'position': [4000 * MM, 0]}},
         'walls': {'W1': {'level': 'L1', 'start': 'J1', 'end': 'J2', 'layers': [{'thickness': 100 * MM, 'function': 'core'}]}},
         'types': {'D': door or {'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM}},
         'openings': {'O1': opening or {'wall': 'W1', 'offset': 1000 * MM, 'fill': 'D'}}}
    return d


def run(d, reader=READER_03):
    result, _, _ = check(json.dumps(d).encode(), reader)
    return result


def codes(result):
    return [x['code'] for x in result['diagnostics'] if x['severity'] == 'error']


class SchemaTier(unittest.TestCase):
    def test_new_members_only_in_0_3(self):
        door = {'kind': 'doorType', 'operation': 'swing', 'clearOpening': {'width': 1, 'height': 1}}
        d = doc(door=door)
        self.assertEqual(schema.check(d, '0.3'), [])
        d['floorspec'] = '0.2'
        self.assertNotEqual(schema.check(d, '0.2'), [])

    def test_operations_by_kind(self):
        self.assertNotEqual(schema.check(doc(door={'kind': 'doorType', 'operation': 'casement'}), '0.3'), [])
        self.assertEqual(schema.check(doc(door={'kind': 'windowType', 'operation': 'casement'}), '0.3'), [])

    def test_door_clear_opening_has_no_area(self):
        door = {'kind': 'doorType', 'clearOpening': {'width': 1, 'height': 1, 'area': 1}}
        self.assertNotEqual(schema.check(doc(door=door), '0.3'), [])


class ClearOpenings(unittest.TestCase):
    def test_derived_as_declared_and_area_never_computed(self):
        d = doc(door={'kind': 'windowType', 'width': 900 * MM, 'height': 900 * MM,
                      'clearOpening': {'width': 800 * MM, 'height': 800 * MM}})
        r = run(d)
        self.assertTrue(r['valid'], r)
        self.assertEqual(r['derived']['openings']['O1']['clearOpening'], {'width': 800 * MM, 'height': 800 * MM})

    def test_override_is_whole(self):
        d = doc(door={'kind': 'windowType', 'width': 900 * MM, 'height': 900 * MM,
                      'clearOpening': {'width': 800 * MM, 'height': 800 * MM, 'area': 1}},
                opening={'wall': 'W1', 'offset': 1000 * MM, 'fill': 'D', 'clearOpening': {'width': 700 * MM, 'height': 700 * MM}})
        self.assertNotIn('area', run(d)['derived']['openings']['O1']['clearOpening'])

    def test_invariants(self):
        wide = doc(door={'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM,
                         'clearOpening': {'width': 900 * MM + 1, 'height': 1}})
        self.assertEqual(codes(run(wide)), ['FS-INV-305', 'FS-INV-307'])
        area = doc(door={'kind': 'windowType', 'width': 900 * MM, 'height': 900 * MM,
                         'clearOpening': {'width': 2, 'height': 3, 'area': 7}})
        self.assertEqual(codes(run(area)), ['FS-INV-306'])
        door_area = doc(opening={'wall': 'W1', 'offset': 0, 'fill': 'D', 'clearOpening': {'width': 1, 'height': 1, 'area': 1}})
        self.assertEqual(codes(run(door_area)), ['FS-INV-308'])


class EarlierDrafts(unittest.TestCase):
    def test_a_0_2_document_reads_as_0_2_reads_it(self):
        path = os.path.join(ROOT, 'conformance', 'core', '0.2', 'model', '068-version-0.2-with-everything', 'input.json')
        with open(path, 'rb') as f:
            data = f.read()
        self.assertEqual(check(data, READER_03), check(data, READER_02))

    def test_a_0_3_document_is_unknown_to_a_0_2_reader(self):
        r = run(doc(), READER_02)
        self.assertEqual(codes(r), ['FS-DOC-001'])
        self.assertTrue(run(copy.deepcopy(doc()))['valid'])


if __name__ == '__main__':
    unittest.main()

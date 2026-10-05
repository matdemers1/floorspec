"""Core 0.3 in the oracle: the schema tier's new members, the clear-opening invariants, the derived
clear opening, floors, ceilings and slabs (chapter 15), and a 0.3 reader reading earlier drafts
exactly (1.2.6): every value an earlier draft derives is unchanged, and only the floors, ceilings and
slabs are new."""
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


NEW_DERIVED = ('floors', 'ceilings', 'slabs')
NEW_DERIVED += ('roofs',)                            # chapter 16: none in an earlier draft's document


def without_new(result):
    r = copy.deepcopy(result)
    for k in NEW_DERIVED:
        r.get('derived', {}).pop(k, None)
    return r


class EarlierDrafts(unittest.TestCase):
    def test_a_0_2_document_reads_as_0_2_reads_it(self):
        path = os.path.join(ROOT, 'conformance', 'core', '0.2', 'model', '068-version-0.2-with-everything', 'input.json')
        with open(path, 'rb') as f:
            data = f.read()
        r3, r2 = check(data, READER_03), check(data, READER_02)
        self.assertEqual((without_new(r3[0]),) + r3[1:], r2)
        self.assertEqual(sorted(r3[0]['derived']), sorted(list(r2[0]['derived']) + list(NEW_DERIVED)))

    def test_every_earlier_suite_document_derives_what_its_draft_derives(self):
        """Every test of the published 0.1 and 0.2 suites, read by a reader of 0.3 (1.2.6, 15.6): the same validity,
        diagnostics, hash, canonical form and derived values - placements of surface hosts included - as its own
        reader of 0.2 gives, except for the floors, ceilings and slabs 0.3 adds. (A reader of 0.2 reads a 0.1
        document as 0.1 does, except for circulation, which the 0.2 suite pins.)"""
        seen = 0
        for version in ('0.1', '0.2'):
            suite = os.path.join(ROOT, 'conformance', 'core', version)
            for dirpath, _, files in sorted(os.walk(suite)):
                if 'input.json' not in files or 'registry.json' in files:
                    continue
                with open(os.path.join(dirpath, 'input.json'), 'rb') as f:
                    data = f.read()
                try:
                    declared = json.loads(data).get('floorspec')
                except (ValueError, AttributeError):
                    declared = None
                if declared not in ('0.1', '0.2'):
                    continue                                    # what a reader of each draft rejects differently
                r3, c3, _ = check(data, READER_03)
                r2, c2, _ = check(data, READER_02)
                self.assertEqual(without_new(r3), r2, dirpath)
                self.assertEqual(c3, c2, dirpath)
                if r3['valid']:
                    self.assertEqual(set(r3['derived']) - set(r2['derived']), set(NEW_DERIVED), dirpath)
                seen += 1
        self.assertGreater(seen, 700)

    def test_a_0_3_document_is_unknown_to_a_0_2_reader(self):
        r = run(doc(), READER_02)
        self.assertEqual(codes(r), ['FS-DOC-001'])
        self.assertTrue(run(copy.deepcopy(doc()))['valid'])


def room(version='0.3', **members):
    """A 4 m x 3 m room inside 100 mm walls - its room polygon (50 mm, 50 mm) to (3950 mm, 2950 mm) - on L1 at 0,
    2700 mm high."""
    js = {'J1': (0, 0), 'J2': (0, 3000), 'J3': (4000, 3000), 'J4': (4000, 0)}
    d = {'floorspec': version, 'project': {'name': 'x'}, 'buildings': {'B1': {}},
         'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': 2700 * MM}},
         'junctions': {j: {'level': 'L1', 'position': [x * MM, y * MM]} for j, (x, y) in js.items()},
         'walls': {f'W{i}': {'level': 'L1', 'start': a, 'end': b, 'layers': [{'thickness': 100 * MM, 'function': 'core'}]}
                   for i, (a, b) in enumerate((('J1', 'J2'), ('J2', 'J3'), ('J3', 'J4'), ('J4', 'J1')), 1)},
         'rooms': {'R1': {'level': 'L1', 'anchor': [2000 * MM, 1500 * MM], **members}}}
    return d


class FloorsAndCeilings(unittest.TestCase):
    def test_defaults_are_the_0_2_elevations(self):
        r = run(room())
        self.assertEqual(r['derived']['floors']['R1']['top'], 0)
        self.assertEqual(r['derived']['floors']['R1']['bottom'], 0)
        self.assertEqual((r['derived']['ceilings']['R1']['low'], r['derived']['ceilings']['R1']['high']), (2700 * MM, 2700 * MM))

    def test_vault_low_and_high_by_hand(self):
        c = {'kind': 'vaulted', 'height': 3200 * MM, 'ridge': [[0, 1500 * MM], [4000 * MM, 1500 * MM]], 'pitch': {'rise': 1, 'run': 2}}
        v = run(room(ceiling=c))['derived']['ceilings']['R1']
        self.assertEqual((v['low'], v['high']), (2475 * MM, 3200 * MM))
        c['slopes'] = 'left'                                 # one plane: falls north of an eastward ridge, rises south
        v = run(room(ceiling=c))['derived']['ceilings']['R1']
        self.assertEqual((v['low'], v['high']), (2475 * MM, 3925 * MM))

    def test_vault_rounds_once_ties_to_even(self):
        from tools.oracle.floors import vault_z
        c = {'ridge': [[0, 0], [2, 0]], 'pitch': {'rise': 1, 'run': 2}}
        self.assertEqual(vault_z(10, c, 2).round(), 10)       # 10 - (1/2)(2/2) = 9.5: ties to even
        self.assertEqual(vault_z(11, c, 2).round(), 10)       # 10.5 -> 10
        self.assertEqual(vault_z(12, c, 2).round(), 12)       # 11.5 -> 12

    def test_tray_inset_and_fit(self):
        from tools.oracle.floors import tray_rings
        outer = [(0, 0), (100, 0), (100, 60), (0, 60)]
        self.assertEqual(tray_rings(outer, [], 10), ([(10, 10), (90, 10), (90, 50), (10, 50)], []))
        self.assertIsNone(tray_rings(outer, [], 30))           # zero-height centre: an edge has no length
        self.assertIsNotNone(tray_rings(outer, [], 29))
        hole = [(40, 20), (40, 40), (60, 40), (60, 20)]       # clockwise: grows outwards
        self.assertEqual(tray_rings(outer, [hole], 5), ([(5, 5), (95, 5), (95, 55), (5, 55)], [[(35, 15), (35, 45), (65, 45), (65, 15)]]))
        self.assertIsNone(tray_rings(outer, [hole], 12))       # the hole's ring reaches the outer one

    def test_collinear_vertex_moves_along_its_normal(self):
        from tools.oracle.floors import tray_rings
        outer = [(0, 0), (50, 0), (100, 0), (100, 60), (0, 60)]
        self.assertEqual(tray_rings(outer, [], 10)[0], [(10, 10), (50, 10), (90, 10), (90, 50), (10, 50)])

    def test_invariants(self):
        self.assertEqual(codes(run(room(floor={'offset': 2700 * MM}))), ['FS-INV-701'])
        self.assertEqual(codes(run(room(floor={'offset': 2700 * MM - 1}))), [])
        self.assertEqual(codes(run(room(ceiling={'kind': 'vaulted', 'ridge': [[0, 0], [0, 0]], 'pitch': {'rise': 1, 'run': 1}}))),
                         ['FS-INV-702'])
        self.assertEqual(codes(run(room(ceiling={'kind': 'tray', 'border': 1450 * MM, 'depth': 1}))), ['FS-INV-703'])

    def test_ceiling_host_on_a_vault_and_a_tray(self):
        def host(c, p):
            d = room(ceiling=c)
            d['extensionsUsed'] = {'EXT_x': '1.0.0'}
            d['extensions'] = {'EXT_x': {'collections': {'lights': {'X1': {
                'fallback': {'level': 'L1', 'box': {'min': [-1280, -1280, -1280], 'max': [1280, 1280, 0]}},
                'host': {'mode': 'surface', 'room': 'R1', 'surface': 'ceiling', 'position': p}}}}}}
            return run(d)['derived']['placements']['X1']['point'][2]
        vault = {'kind': 'vaulted', 'height': 3200 * MM, 'ridge': [[0, 1500 * MM], [4000 * MM, 1500 * MM]], 'pitch': {'rise': 1, 'run': 2}}
        self.assertEqual(host(vault, [1000 * MM, 1000 * MM]), 2950 * MM)
        tray = {'kind': 'tray', 'border': 300 * MM, 'depth': 200 * MM}
        self.assertEqual(host(tray, [2000 * MM, 1500 * MM]), 2900 * MM)
        self.assertEqual(host(tray, [2000 * MM, 349 * MM]), 2700 * MM)
        self.assertEqual(host(tray, [2000 * MM, 350 * MM]), 2900 * MM)


if __name__ == '__main__':
    unittest.main()

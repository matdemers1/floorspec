"""Unit tests of what Ops 0.2 adds to the oracle: the draft profiles, areas (3.6), the one space of
IDs (0.3), and hosted elements on a split wall (5.2 step 6). The conformance suite exercises all of
it end to end; these pin the pieces."""

import os
import unittest

from tools.oracle.ops.engine import apply
from tools.oracle.ops.errors import OpsError
from tools.oracle.ops.normalize import _rehost_hosted
from tools.oracle.ops.refs import area
from tools.oracle.ops.space import all_ids, locate
from tools.oracle.ops.version import OPS_01, OPS_02, OPS_03, profile_for

FT = 390144
M2 = 1_638_400_000_000


def doc(**members):
    d = {'floorspec': '0.2', 'project': {'name': 'x'}}
    d.update(members)
    return d


class ProfileTest(unittest.TestCase):
    def test_profile_for(self):
        self.assertIs(profile_for(os.path.join('conformance', 'ops', '0.2', 'program', '001-x')), OPS_02)
        self.assertIs(profile_for(os.path.join('conformance', 'ops', '0.1', 'ids', '001-x')), OPS_01)
        self.assertIs(profile_for('elsewhere'), OPS_01)
        self.assertIs(profile_for(os.path.join('conformance', 'ops', '0.3', 'ids', '001-x')), OPS_03)

    def test_a_0_3_document_needs_ops_0_3(self):
        a = b'{"floorspec": "0.3", "project": {"name": "x"}}'
        req = b'{"batch": [{"op": "setProperty", "id": "$project", "path": "/name", "value": "y"}]}'
        self.assertEqual(apply(a, req, OPS_02)[0]['diagnostics'][0]['code'], 'FS-OPS-002')
        self.assertEqual(apply(a, req, OPS_03)[0]['status'], 'committed')

    def test_items_exist_in_0_3_documents_under_ops_0_3(self):
        d = {'floorspec': '0.3', 'project': {'name': 'x'}, 'program': {'items': {'P1': {'function': 'kitchen'}}}}
        self.assertIsNotNone(locate(d, 'P1', OPS_03))
        self.assertIsNone(locate(d, 'P1', OPS_02))

    def test_a_0_2_document_is_rejected_by_ops_0_1(self):
        a = b'{"floorspec": "0.2", "project": {"name": "x"}}'
        req = b'{"batch": [{"op": "setProperty", "id": "$project", "path": "/name", "value": "y"}]}'
        self.assertEqual(apply(a, req, OPS_01)[0]['diagnostics'][0]['code'], 'FS-OPS-002')
        self.assertEqual(apply(a, req, OPS_02)[0]['status'], 'committed')

    def test_program_is_a_document_member_in_0_2_only(self):
        """Ops 0.1's $document has no `program` (FS-OPS-003); Ops 0.2's has, so the program is set -
        and a document that declares "0.1" with a program fails Core 0.1's schema."""
        a = b'{"floorspec": "0.1", "project": {"name": "x"}}'
        req = b'{"batch": [{"op": "setProperty", "id": "$document", "path": "/program", "value": {}}]}'
        self.assertEqual(apply(a, req, OPS_01)[0]['diagnostics'][0]['code'], 'FS-OPS-003')
        self.assertEqual(apply(a, req, OPS_02)[0]['diagnostics'][0]['code'], 'FS-SCH-001')


class AreaTest(unittest.TestCase):
    def test_units(self):
        self.assertEqual(area('11 m2'), 11 * M2)
        self.assertEqual(area('11 M²'), 11 * M2)
        self.assertEqual(area(' 120  sq\tft '), 120 * FT * FT)
        self.assertEqual(area('1 in2'), 32512 ** 2)
        self.assertEqual(area('1 cm2'), 12800 ** 2)
        self.assertEqual(area('.5 mm2'), 819200)
        self.assertEqual(area(7), 7)

    def test_ties_to_even(self):
        self.assertEqual(area('0.00000091552734375 mm2'), 2)     # 1.5
        self.assertEqual(area('0.00000152587890625 mm2'), 2)     # 2.5

    def test_not_areas(self):
        for s in ('11 m', '11', '-1 m2', '120 sqft', '1 m 2', '1 km2', 'sq ft'):
            with self.subTest(s):
                with self.assertRaises(OpsError) as e:
                    area(s)
                self.assertEqual(e.exception.code, 'FS-OPS-012')


class SpaceTest(unittest.TestCase):
    def test_items_and_extension_elements_in_0_2(self):
        d = doc(walls={'W1': {}}, program={'items': {'P1': {}}},
                extensions={'FS_x': {'collections': {'things': {'X1': {}}}, 'style': 'y'}})
        self.assertEqual(all_ids(d, OPS_02), {'W1', 'P1', 'X1'})
        self.assertEqual(locate(d, 'X1', OPS_02)[0], ('ext', 'FS_x', 'things'))
        self.assertEqual(locate(d, 'P1', OPS_02)[0], ('items',))
        self.assertEqual(all_ids(d, OPS_01), {'W1'})

    def test_opaque_in_a_0_1_document(self):
        d = doc(program={'items': {'P1': {}}}, extensions={'FS_x': {'collections': {'things': {'X1': {}}}}})
        d['floorspec'] = '0.1'
        self.assertEqual(all_ids(d, OPS_02), set())


class SplitTest(unittest.TestCase):
    def wc(self, *offsets):
        els = {f'X{i}': {'host': {'mode': 'wallFace', 'wall': 'W1', 'side': 'left', 'offset': o, 'height': 0}}
               for i, o in enumerate(offsets, 1)}
        return doc(extensions={'FS_x': {'collections': {'things': els}}})

    def hosts(self, wc):
        return {k: (v['host']['wall'], v['host']['offset'])
                for k, v in wc['extensions']['FS_x']['collections']['things'].items()}

    def test_half_open_pieces(self):
        """A 12' wall split at 4' and 8': an element at a split point goes to the piece that starts
        there; the last piece includes the wall's end; one past the end stays."""
        wc = self.wc(0, 4 * FT - 1, 4 * FT, 8 * FT, 12 * FT, 12 * FT + 1, -1)
        _rehost_hosted(wc, 'W1', (0, 0), (12 * FT, 0), [(4 * FT, 0), (8 * FT, 0)], ['W1', 'W2', 'W3'], OPS_02)
        self.assertEqual(self.hosts(wc), {'X1': ('W1', 0), 'X2': ('W1', 4 * FT - 1), 'X3': ('W2', 0), 'X4': ('W3', 0),
                                          'X5': ('W3', 4 * FT), 'X6': ('W1', 12 * FT + 1), 'X7': ('W1', -1)})

    def test_rounding_on_an_oblique_wall(self):
        """A wall from (0, 0) to (3, 4) split at its middle-ish point (1, 1) projected: s is
        (1*3 + 1*4) / 5 = 7/5 along the line; an element at 4 goes to 4 - 7/5 = 2.6, rounded to 3."""
        wc = self.wc(4)
        _rehost_hosted(wc, 'W1', (0, 0), (3, 4), [(1, 1)], ['W1', 'W2'], OPS_02)
        self.assertEqual(self.hosts(wc), {'X1': ('W2', 3)})


if __name__ == '__main__':
    unittest.main()

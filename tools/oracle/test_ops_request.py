"""The oracle's request check (Ops 1.1.1 in 0.1, 1.1.2 in 0.2) against tools/fixtures/ops-requests.json
(Ops 0.1) and ops-requests-0.2.json (Ops 0.2) - the same cases tools/ops-schema.test.ts runs through
each draft's JSON Schema - so that the two agree on FS-OPS-001. A 0.2 case marked `new` uses a form
only Ops 0.2 has, so Ops 0.1 rejects it."""

import json
import os
import unittest

from tools.oracle.ops.engine import apply
from tools.oracle.ops.errors import OpsError
from tools.oracle.ops.request import check_request
from tools.oracle.ops.version import OPS_01, OPS_02, OPS_03

FIXTURES = os.path.join(os.path.dirname(__file__), '..', 'fixtures')


def load(name):
    with open(os.path.join(FIXTURES, name), encoding='utf-8') as f:
        return json.load(f)


def malformed(request, profile):
    try:
        check_request(request, profile)
        return False
    except OpsError as e:
        assert e.code == 'FS-OPS-001', e.code
        return True


class RequestTest(unittest.TestCase):
    def test_fixture_01(self):
        for c in load('ops-requests.json'):
            with self.subTest(c['name']):
                self.assertEqual(malformed(c['request'], OPS_01), c['malformed'])

    def test_fixture_02(self):
        for c in load('ops-requests-0.2.json'):
            with self.subTest(c['name']):
                self.assertEqual(malformed(c['request'], OPS_02), c['malformed'])

    def test_fixture_03(self):
        """Ops 0.3 adds no operation and no member: its requests have Ops 0.2's shape, and addElement may name
        Core 0.3's `roofs` (Ops 0.4)."""
        for c in load('ops-requests-0.3.json'):
            with self.subTest(c['name']):
                self.assertEqual(malformed(c['request'], OPS_03), c['malformed'])

    def test_03_forms_are_malformed_in_02(self):
        for c in load('ops-requests-0.3.json'):
            if c.get('new03'):
                with self.subTest(c['name']):
                    self.assertTrue(malformed(c['request'], OPS_02))

    def test_02_forms_are_malformed_in_01(self):
        for c in load('ops-requests-0.2.json'):
            if c.get('new'):
                with self.subTest(c['name']):
                    self.assertTrue(malformed(c['request'], OPS_01))

    def test_lexical_integers(self):
        a = b'{"floorspec": "0.1", "project": {"name": "x"}}'
        for profile in (OPS_01, OPS_02):
            r, _ = apply(a, b'{"batch": [{"op": "moveWall", "wall": "W1", "by": 2.0}]}', profile)
            self.assertEqual([d['code'] for d in r['diagnostics']], ['FS-OPS-001'])
            r, _ = apply(a, b'{"batch": [{"op": "moveWall", "wall": "W1", "by": 2}]}', profile)
            self.assertEqual([d['code'] for d in r['diagnostics']], ['FS-OPS-003'])

    def test_not_json(self):
        a = b'{"floorspec": "0.1", "project": {"name": "x"}}'
        for profile in (OPS_01, OPS_02):
            for req in (b'{"batch": [', b'{"batch": [], "batch": []}', b'\xef\xbb\xbf{"batch": []}'):
                r, _ = apply(a, req, profile)
                self.assertEqual([d['code'] for d in r['diagnostics']], ['FS-OPS-001'])


if __name__ == '__main__':
    unittest.main()

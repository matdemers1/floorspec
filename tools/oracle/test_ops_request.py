"""The oracle's request check (Ops 1.1.1) against tools/fixtures/ops-requests.json - the same cases
tools/ops-schema.test.ts runs through the JSON Schema - so that the two agree on FS-OPS-001."""

import json
import os
import unittest

from tools.oracle.ops.engine import apply
from tools.oracle.ops.errors import OpsError
from tools.oracle.ops.request import check_request

FIXTURE = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'ops-requests.json')


class RequestTest(unittest.TestCase):
    def test_fixture(self):
        with open(FIXTURE, encoding='utf-8') as f:
            cases = json.load(f)
        for c in cases:
            with self.subTest(c['name']):
                try:
                    check_request(c['request'])
                    malformed = False
                except OpsError as e:
                    self.assertEqual(e.code, 'FS-OPS-001')
                    malformed = True
                self.assertEqual(malformed, c['malformed'])

    def test_lexical_integers(self):
        a = b'{"floorspec": "0.1", "project": {"name": "x"}}'
        r, _ = apply(a, b'{"batch": [{"op": "moveWall", "wall": "W1", "by": 2.0}]}')
        self.assertEqual([d['code'] for d in r['diagnostics']], ['FS-OPS-001'])
        r, _ = apply(a, b'{"batch": [{"op": "moveWall", "wall": "W1", "by": 2}]}')
        self.assertEqual([d['code'] for d in r['diagnostics']], ['FS-OPS-003'])

    def test_not_json(self):
        a = b'{"floorspec": "0.1", "project": {"name": "x"}}'
        for req in (b'{"batch": [', b'{"batch": [], "batch": []}', b'\xef\xbb\xbf{"batch": []}'):
            r, _ = apply(a, req)
            self.assertEqual([d['code'] for d in r['diagnostics']], ['FS-OPS-001'])


if __name__ == '__main__':
    unittest.main()

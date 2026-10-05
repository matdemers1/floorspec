"""The oracle's extension machinery: the JSON Schema subset, and the room of an element."""

import json
import unittest

from tools.oracle.derive import Doc
from tools.oracle.ext.common import Context
from tools.oracle.ext.jsonschema import Schema
from tools.oracle.ext_author import FT, demo


class SchemaSubset(unittest.TestCase):
    def test_integers_are_json_integers(self):
        s = Schema({'type': 'integer', 'minimum': 1})
        self.assertEqual(s.errors(3), [])
        self.assertTrue(s.errors(3.0))            # jsonparse keeps 3.0 a float (2.1.1)
        self.assertTrue(s.errors(True))
        self.assertTrue(s.errors(0))

    def test_closed_objects_and_refs(self):
        s = Schema({'$defs': {'id': {'type': 'string', 'pattern': '^[A-Z][0-9]+$'}},
                    'type': 'object', 'required': ['a'], 'additionalProperties': False,
                    'properties': {'a': {'$ref': '#/$defs/id'}, 'b': {'type': 'array', 'items': {'$ref': '#/$defs/id'}, 'uniqueItems': True}}})
        self.assertEqual(s.errors({'a': 'X1', 'b': ['X2', 'X3']}), [])
        self.assertTrue(s.errors({'a': 'X1', 'c': 1}))
        self.assertTrue(s.errors({'b': []}))
        self.assertTrue(s.errors({'a': 'X1', 'b': ['X2', 'X2']}))
        self.assertTrue(s.errors({'a': 'x1'}))

    def test_a_keyword_outside_the_subset_is_refused(self):
        with self.assertRaises(ValueError):
            Schema({'oneOf': [{'type': 'string'}]})


class RoomOfAnElement(unittest.TestCase):
    def rooms(self, d):
        return Context(Doc(json.loads(json.dumps(d))), 'FS_electrical', {}).rooms()

    def test_wall_faces(self):
        r = self.rooms(demo())
        self.assertEqual(r['X5'], 'R1')       # W1 runs north: its right face looks east, into the Kitchen
        self.assertEqual(r['X25'], None)      # its left face looks west, outside
        self.assertEqual(r['X4'], 'R1')       # W9 runs north: its left face is the Kitchen's
        self.assertEqual(r['X26'], 'R2')      # and its right face the Bath's
        self.assertEqual(r['X1'], 'R3')

    def test_surfaces_and_free_hosts(self):
        d = demo()
        lights = d['extensions']['FS_electrical']['collections']['lights']
        lights['XA'] = {'fallback': {'level': 'L1', 'box': {'min': [0, 0, 0], 'max': [1280, 1280, 1280]}},
                        'host': {'mode': 'free', 'level': 'L1', 'position': [16 * FT, 3 * FT]}}
        lights['XB'] = {'fallback': {'level': 'L1', 'box': {'min': [0, 0, 0], 'max': [1280, 1280, 1280]}},
                        'host': {'mode': 'free', 'level': 'L1', 'position': [12 * FT, 3 * FT]}}      # on W8's line
        r = self.rooms(d)
        self.assertEqual((r['X22'], r['XA'], r['XB']), ('R1', 'R3', None))


if __name__ == '__main__':
    unittest.main()

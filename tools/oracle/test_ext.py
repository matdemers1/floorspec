"""The oracle's extension machinery: the JSON Schema subset, the room of an element, and FS_furniture's
reading of its starter library."""

import json
import os
import unittest

from tools.oracle.derive import Doc
from tools.oracle.ext.common import Context
from tools.oracle.ext.jsonschema import Schema
from tools.oracle.ext import furniture
from tools.oracle.ext_author import FT, LIBRARY, demo


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


class FurnitureLibrary(unittest.TestCase):
    """The starter library is written by tools/furniture-library.ts; its default envelopes are checked
    here against FS_furniture 4.2 as the oracle reads it, so the two languages agree on the table."""
    MM = 1280
    # 4.2: category -> (names, form, distance in mm); the purpose is the oracle's own furniture.PURPOSE
    FORMS = {'refrigerator': (['door'], 'front', 900), 'freezer': (['door'], 'front', 900),
             'range': (['door'], 'front', 600), 'wallOven': (['door'], 'front', 600),
             'dishwasher': (['door'], 'front', 700), 'washer': (['door'], 'front', 700), 'dryer': (['door'], 'front', 700),
             'sofa': (['front'], 'standing', 600), 'armchair': (['front'], 'standing', 600), 'desk': (['front'], 'standing', 750),
             'diningTable': (['around'], 'around', 750), 'bed': (['left', 'right'], 'sides', 600),
             'dresser': (['front'], 'front', 500), 'sideboard': (['front'], 'front', 500), 'wardrobe': (['front'], 'front', 600),
             'baseCabinet': (['front'], 'front', 600), 'tallCabinet': (['front'], 'front', 600),
             'wallCabinet': (['front'], 'front', 400), 'vanity': (['front'], 'front', 500),
             'island': (['front'], 'standing', 1000)}

    def envelopes(self, category, box):
        if category not in self.FORMS:
            return {}
        names, form, mm = self.FORMS[category]
        D, p = mm * self.MM, furniture.PURPOSE[category]
        (x0, y0, z0), (x1, y1, z1) = box['min'], box['max']
        top = max(z1, z0 + 2000 * self.MM)
        e = lambda mn, mx: {'purpose': p, 'shape': 'box', 'min': mn, 'max': mx}      # noqa: E731
        if form == 'front':
            return {names[0]: e([x1, y0, z0], [x1 + D, y1, z1])}
        if form == 'standing':
            return {names[0]: e([x1, y0, z0], [x1 + D, y1, top])}
        if form == 'around':
            return {names[0]: e([x0 - D, y0 - D, z0], [x1 + D, y1 + D, top])}
        return {names[0]: e([x0, y1, z0], [x1, y1 + D, top]), names[1]: e([x0, y0 - D, z0], [x1, y0, top])}

    def test_default_envelopes_and_mounting(self):
        with open(os.path.join(LIBRARY, 'library.json'), encoding='utf-8') as f:
            items = json.load(f)['items']
        self.assertGreaterEqual(len(items), 20)
        self.assertEqual(set(self.FORMS), set(furniture.PURPOSE))
        for lib, it in items.items():
            el = it['element']
            self.assertEqual(el.get('clearances', {}), self.envelopes(el['category'], el['fallback']['box']), lib)
            self.assertEqual(it['mounting'], furniture.mounting(el['category']), lib)
            x0, y0, z0 = el['fallback']['box']['min']
            self.assertEqual((x0, z0, y0 + el['fallback']['box']['max'][1]), (0, 0, 0), lib)    # 3.1: back on x = 0, centred

    def test_grouped(self):
        own = {'T': {}, 'C1': {'with': 'T'}, 'C2': {'with': 'T'}, 'B': {}}
        self.assertTrue(furniture.grouped(own, 'C1', 'T'))
        self.assertTrue(furniture.grouped(own, 'T', 'C2'))
        self.assertTrue(furniture.grouped(own, 'C1', 'C2'))
        self.assertFalse(furniture.grouped(own, 'C1', 'B'))
        self.assertFalse(furniture.grouped(own, 'O1', 'B'))             # an opening is never grouped


if __name__ == '__main__':
    unittest.main()

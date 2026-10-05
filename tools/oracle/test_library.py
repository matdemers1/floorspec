"""The US starter type library (library/us-starter/, FLR-T-10.4): every item's published Ops batch embeds it,
and the document it gives is valid Core 0.3 - checked by the oracle's own Ops applier and validator."""
import json
import unittest

from tools.oracle import us_library
from tools.oracle.ops.engine import apply
from tools.oracle.ops.version import OPS_03
from tools.oracle.validate import READER_03, check

BASE = {'floorspec': '0.3', 'project': {'name': 'Library'}}


def as_bytes(d):
    return json.dumps(d).encode('utf-8')


class TestLibrary(unittest.TestCase):
    def test_index(self):
        self.assertEqual(us_library.INDEX['library'], 'https://d3cloud.io/floorspec/library/us-starter')
        self.assertEqual(us_library.INDEX['version'], us_library.VERSION)
        self.assertTrue(us_library.INDEX['clearOpenings'].startswith("generic, replace with your product's declared values"))
        kinds = {}
        for item, e in us_library.ITEMS.items():
            kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
            self.assertEqual(e['element']['source'], {'library': us_library.INDEX['library'], 'version': us_library.VERSION,
                                                      'item': item})
        self.assertEqual(set(kinds), {'wallType', 'doorType', 'windowType', 'material'})

    def test_every_batch_embeds_its_item_and_the_result_is_valid(self):
        for item, e in us_library.ITEMS.items():
            with self.subTest(item=item):
                result, b = apply(as_bytes(BASE), {'batch': e['embed']}, OPS_03)
                self.assertEqual(result['status'], 'committed', result.get('diagnostics'))
                self.assertEqual(result['created'], sorted(op['id'] for op in e['embed']))
                doc = json.loads(b)
                for op in e['embed']:
                    self.assertEqual(doc[op['collection']][op['id']], op['element'], 'embedded byte for byte')
                v, _, _ = check(b, READER_03)
                self.assertTrue(v['valid'])
                # Nothing uses an item embedded on its own, and a material only its wall type uses.
                unused = {d['elements'][0] for d in v['diagnostics']}
                self.assertTrue(all(d['code'] == 'FS-LINT-006' for d in v['diagnostics']), v['diagnostics'])
                self.assertEqual(unused, {item})

    def test_embedding_everything_is_valid_and_idempotent(self):
        doc = us_library.embed(BASE, *us_library.ITEMS)
        self.assertEqual(us_library.embed(doc, *us_library.ITEMS), doc)
        v, _, _ = check(as_bytes(doc), READER_03)
        self.assertTrue(v['valid'], v['diagnostics'])
        self.assertEqual({d['code'] for d in v['diagnostics']}, {'FS-LINT-006'})
        # A wall type's layers name its materials by their library IDs: once embedded, they are used.
        used = {l['material'] for t in doc['types'].values() for l in t.get('layers', []) if 'material' in l}
        unused = {d['elements'][0] for d in v['diagnostics']}
        self.assertEqual(unused, set(doc['types']) | (set(doc['materials']) - used))

    def test_source_is_never_read_by_derivation(self):
        doc = us_library.embed(BASE, 'wall-2x4-interior')
        bare = json.loads(json.dumps(doc))
        for coll in ('types', 'materials'):
            for el in bare[coll].values():
                del el['source']
        a, _, _ = check(as_bytes(doc), READER_03)
        b, _, _ = check(as_bytes(bare), READER_03)
        self.assertEqual(a['derived'], b['derived'])
        self.assertEqual(a['diagnostics'], b['diagnostics'])
        self.assertNotEqual(a['hash'], b['hash'], 'source is content: it is in the canonical form and the hash')


if __name__ == '__main__':
    unittest.main()

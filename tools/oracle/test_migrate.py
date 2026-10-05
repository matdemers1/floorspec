"""The oracle's migrator (Core 0.3, chapter 20): its steps, its refusals, and the property chapter 20
promises - every document of an earlier draft in the published suites migrates to 0.3, and a reader
of 0.3 reads the migration exactly as it reads the document (20.6.1)."""

import json
import os
import unittest

from tools.oracle import canon
from tools.oracle.migrate import RECORD, migrate, step
from tools.oracle.validate import READER_03, check

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))


def doc(version='0.1', **members):
    d = {'floorspec': version, 'project': {'name': 'M'}}
    d.update(members)
    return d


def raw(d):
    return json.dumps(d).encode('utf-8')


class Steps(unittest.TestCase):
    def test_version_only(self):
        self.assertEqual(step(doc()), doc('0.2'))
        self.assertEqual(step(doc('0.2')), doc('0.3'))

    def test_01_moves_top_level_collections_only(self):
        d = doc(extensionsUsed={'EXT_a': '1.0', 'EXT_b': '1.0'},
                extensions={'EXT_b': {'collections': 1, 'keep': True}, 'EXT_a': {'collections': {}}})
        out = step(d)
        self.assertEqual(out['extensions'], {'EXT_b': {'keep': True}, 'EXT_a': {}})
        self.assertEqual(out['extras'][RECORD], [{'from': '0.1', 'to': '0.2', 'moved': [
            {'pointer': '/extensions/EXT_a/collections', 'value': {}},
            {'pointer': '/extensions/EXT_b/collections', 'value': 1}]}])
        self.assertIn('collections', d['extensions']['EXT_a'], 'the step does not change its input')

    def test_02_moves_extension_element_options(self):
        el = {'fallback': {'level': 'L1', 'box': {'min': [0, 0, 0], 'max': [1, 1, 1]}}, 'option': 'X'}
        d = doc('0.2', extensions={'EXT_a': {'collections': {'c': {'E1': el}}}}, extras={RECORD: [1]})
        out = step(d)
        self.assertNotIn('option', out['extensions']['EXT_a']['collections']['c']['E1'])
        self.assertEqual(out['extras'][RECORD][0], 1)
        self.assertEqual(out['extras'][RECORD][1]['moved'], [{'pointer': '/extensions/EXT_a/collections/c/E1/option', 'value': 'X'}])

    def test_pointers_sorted_by_utf16(self):
        d = doc(extensions={'EXT_b': {'collections': 0}, 'EXT_B': {'collections': 0}, 'EXT_a': {'collections': 0}})
        ptrs = [m['pointer'] for m in step(d)['extras'][RECORD][0]['moved']]
        self.assertEqual(ptrs, ['/extensions/EXT_B/collections', '/extensions/EXT_a/collections', '/extensions/EXT_b/collections'])


class Refusals(unittest.TestCase):
    def codes(self, data, to='0.3'):
        r = migrate(data, to)
        return r['status'], [d['code'] for d in r['diagnostics']]

    def test_tiers(self):
        self.assertEqual(self.codes(b'{'), ('refused', ['FS-JSON-001']))
        self.assertEqual(self.codes(raw(doc('0.9'))), ('refused', ['FS-DOC-001']))
        self.assertEqual(self.codes(raw(doc(program={}))), ('refused', ['FS-SCH-001']))
        self.assertEqual(self.codes(raw(doc('0.3')), '0.2'), ('refused', ['FS-MIG-001']))
        self.assertEqual(self.codes(raw(doc()), '1.0'), ('refused', ['FS-MIG-001']))
        bad = doc(extras={RECORD: {}}, extensionsUsed={'EXT_a': '1.0'}, extensions={'EXT_a': {'collections': {}}})
        self.assertEqual(self.codes(raw(bad)), ('refused', ['FS-MIG-002']))

    def test_required_extension_is_no_obstacle(self):
        d = doc(extensionsUsed={'EXT_a': '1.0'}, extensionsRequired=['EXT_a'])
        self.assertEqual(self.codes(raw(d)), ('migrated', []))

    def test_written_not_canonicalized(self):
        d = doc('0.3', extras={})
        self.assertEqual(migrate(raw(d), '0.3')['bytes'], (canon.pretty(d) + '\n').encode())


class ExtensionElementOption(unittest.TestCase):
    """In a 0.2 document an extension element's `option` is the extension's (12.5 of 0.2): no reference
    to an option, for a reader of 0.2 or of 0.3 (1.2.6). Only a 0.3 document's is core's (19.2)."""

    def test_read_as_the_extensions_own(self):
        from tools.oracle.validate import READER_02
        with open(os.path.join(ROOT, 'conformance', 'migration', '0.3', 'step-0.2-0.3',
                               '002-extension-element-option-moved', 'input.json'), 'rb') as f:
            data = f.read()
        for reader in (READER_02, READER_03):
            self.assertEqual(check(data, reader, None)[0]['diagnostics'], [])
        d = json.loads(data)
        d['floorspec'] = '0.3'
        self.assertEqual([x['code'] for x in check(raw(d), READER_03, None)[0]['diagnostics']], ['FS-INV-002'])


class Preserved(unittest.TestCase):
    """20.6.1 over every schema-valid input of the Core 0.1 and 0.2 suites, migrated to 0.3."""

    def test_every_earlier_suite_document(self):
        n = 0
        for v in ('0.1', '0.2'):
            for dirpath, _, files in sorted(os.walk(os.path.join(ROOT, 'conformance', 'core', v))):
                if 'input.json' not in files or 'registry.json' in files:
                    continue
                with open(os.path.join(dirpath, 'input.json'), 'rb') as f:
                    data = f.read()
                r = migrate(data, '0.3')
                if r['status'] != 'migrated':
                    continue
                n += 1
                a, _, _ = check(data, READER_03, None)
                b, _, _ = check(r['bytes'], READER_03, None)
                rel = os.path.relpath(dirpath, ROOT)
                self.assertEqual(r['document']['floorspec'], '0.3', rel)
                self.assertEqual((a['valid'], a['diagnostics']), (b['valid'], b['diagnostics']), rel)
                self.assertEqual(a.get('derived'), b.get('derived'), rel)
        self.assertGreater(n, 400)


if __name__ == '__main__':
    unittest.main()

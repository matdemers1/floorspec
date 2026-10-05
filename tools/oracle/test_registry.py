import json
import unittest

from tools.oracle import registry as reg


def entry(name='EXT_a', version='1.0.0', **kw):
    return {'name': name, 'version': version, 'status': 'draft', 'schema': 'https://example.com/s.json', **kw}


class Precedence(unittest.TestCase):
    def test_semver_11_example_order(self):
        # Semantic Versioning 2.0.0, 11.4: each is less than the next.
        order = ['1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta', '1.0.0-beta.2',
                 '1.0.0-beta.11', '1.0.0-rc.1', '1.0.0', '1.0.1', '1.1.0', '2.0.0']
        for a, b in zip(order, order[1:]):
            self.assertEqual(reg.compare(a, b), -1, (a, b))
            self.assertEqual(reg.compare(b, a), 1, (a, b))

    def test_missing_patch_reads_as_zero(self):
        self.assertEqual(reg.compare('1.2', '1.2.0'), 0)
        self.assertEqual(reg.compare('1.2-rc.1', '1.2.0-rc.1'), 0)


class Ranges(unittest.TestCase):
    CASES = [
        ('^1.2.3', '1.2.3', True), ('^1.2.3', '1.9.9', True), ('^1.2.3', '2.0.0', False), ('^1.2.3', '1.2.2', False),
        ('^0.3.1', '0.3.9', True), ('^0.3.1', '0.4.0', False), ('^0.0.3', '0.0.3', True), ('^0.0.3', '0.0.4', False),
        ('~1.2.0', '1.2.9', True), ('~1.2.0', '1.3.0', False), ('1.4.2', '1.4.2', True), ('=1.4.2', '1.4.3', False),
        ('>=1.0.0 <1.2.0 || >=2.0.0', '1.1.5', True), ('>=1.0.0 <1.2.0 || >=2.0.0', '1.2.0', False),
        ('>=1.0.0 <1.2.0 || >=2.0.0', '3.0.0', True), ('<=1.5.0', '1.5', True), ('>1.5.0', '1.5', False),
        ('^1.0.0', '2.0.0-rc.1', True), ('^1.0.0', '1.0.0-beta', False),
    ]

    def test_cases(self):
        for rng, v, ok in self.CASES:
            self.assertTrue(reg.RANGE_RE.fullmatch(rng), rng)
            self.assertEqual(reg.satisfies(v, rng), ok, (rng, v))

    def test_grammar(self):
        for bad in ['1.x', '^1.2', '>= 1.0.0', '1.0.0||2.0.0', '', ' 1.0.0', '01.0.0']:
            self.assertFalse(reg.RANGE_RE.fullmatch(bad), bad)


class Load(unittest.TestCase):
    def load(self, entries):
        return reg.load(json.dumps(entries).encode())

    def test_valid(self):
        self.assertEqual(len(self.load([entry(), entry('EXT_b', requires={'EXT_a': '^1.0.0'})])), 2)
        self.assertEqual(self.load([]), [])

    def test_cycle_by_name(self):
        self.assertIsNone(self.load([entry(requires={'EXT_a': '^1.0.0'})]))
        self.assertIsNone(self.load([entry(requires={'EXT_b': '^1.0.0'}), entry('EXT_b', '2.0.0', requires={'EXT_a': '^1.0.0'})]))

    def test_duplicate_name_and_version(self):
        self.assertIsNone(self.load([entry(), entry()]))
        self.assertEqual(len(self.load([entry(), entry(version='1.0.1')])), 2)

    def test_malformed(self):
        self.assertIsNone(reg.load(b'{'))
        self.assertIsNone(reg.load(b'{}'))
        self.assertIsNone(self.load([entry(status='final')]))
        self.assertIsNone(self.load([entry(version='1.0')]))
        self.assertIsNone(self.load([entry(schema='http://example.com/s.json')]))
        self.assertIsNone(self.load([entry(kinds={'Pieces': {}})]))
        self.assertIsNone(self.load([entry(kinds={'pieces': {'fallback': {'asset': 'yes'}}})]))
        self.assertIsNone(self.load([entry(terms={'roomFunctions': ['sauna', 'sauna']})]))
        self.assertIsNone(self.load([entry(status='ratified', implementations=[{'name': 'x', 'url': 'https://x.example/'}])]))
        self.assertIsNone(self.load([{**entry(), 'extra': 1}]))

    def test_entry_for(self):
        known = [entry(version='1.0.0'), entry(version='1.1.0')]
        self.assertEqual(reg.entry_for(known, 'EXT_a', '1.1')['version'], '1.1.0')
        self.assertIsNone(reg.entry_for(known, 'EXT_a', '1.2'))
        self.assertIsNone(reg.entry_for(None, 'EXT_a', '1.0'))


if __name__ == '__main__':
    unittest.main()

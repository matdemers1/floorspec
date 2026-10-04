import hashlib
import unittest

from tools.oracle import canon
from tools.oracle.jsonparse import Malformed, parse


class ParseTest(unittest.TestCase):
    def test_integers_and_non_integers_are_kept_apart(self):
        v, _ = parse(b'[1, 1.0, 1e0, -0]')
        self.assertEqual([type(x) for x in v], [int, float, float, int])

    def test_bom_and_malformed(self):
        for bad in (b'\xef\xbb\xbf{}', b'{"a":1,}', b'{"a":01}', b"{'a':1}", b'{"a":"\x01"}',
                    b'{"a":NaN}', b'\xff', b'{"a":1} x', b'{"a":"\xed\xa0\x80"}'):
            with self.assertRaises(Malformed, msg=bad):
                parse(bad)

    def test_duplicates_and_surrogates(self):
        self.assertEqual(parse(b'{"a":1,"a":1}')[1], ['FS-JSON-002'])
        self.assertEqual(parse(b'{"a":1,"\\u0061":2}')[1], ['FS-JSON-002'])
        self.assertEqual(parse(b'["\\ud800"]')[1], ['FS-JSON-003'])
        self.assertEqual(parse(b'["\\udc00\\ud800"]')[1], ['FS-JSON-003', 'FS-JSON-003'])
        self.assertEqual(parse(b'["\\ud83d\\ude00"]'), (['\U0001F600'], []))


class WriteTest(unittest.TestCase):
    def test_es_numbers(self):
        cases = {1.5: '1.5', 100.0: '100', 1e21: '1e+21', 1e-7: '1e-7', 0.000001: '0.000001',
                 -0.0: '0', 123456789012345680000.0: '123456789012345680000', 0.1 + 0.2: '0.30000000000000004',
                 1.2345e-10: '1.2345e-10', 5e-324: '5e-324', 2 ** 53 + 1: '9007199254740992', -3: '-3'}
        for v, s in cases.items():
            self.assertEqual(canon.es_number(v), s, v)

    def test_strings(self):
        self.assertEqual(canon.es_string('a"\\\n\x1f é'), '"a\\"\\\\\\n\\u001f é"')

    def test_utf16_member_order(self):
        # U+FB01 sorts after U+1F600 in code points but before it in UTF-16 code units
        d = {'\U0001F600': 1, 'ﬁ': 2, 'b': 3, 'B': 4}
        self.assertEqual(canon.jcs(d), '{"B":4,"b":3,"\U0001F600":1,"ﬁ":2}')

    def test_pretty_matches_json_stringify(self):
        v = {'b': [1, {'c': []}], 'a': {}}
        self.assertEqual(canon.pretty(v), '{\n  "a": {},\n  "b": [\n    1,\n    {\n      "c": []\n    }\n  ]\n}')

    def test_rfc8785_hash_of_a_known_value(self):
        self.assertEqual(canon.jcs({'b': 1, 'a': [True, None, 'x']}), '{"a":[true,null,"x"],"b":1}')


class DefaultsTest(unittest.TestCase):
    def doc(self, **kw):
        d = {'floorspec': '0.1', 'project': {'name': 'p', 'extras': {}}}
        d.update(kw)
        return d

    def test_constant_defaults_omitted_innermost_first(self):
        d = self.doc(walls={'W': {'level': 'L', 'start': 'A', 'end': 'B', 'justification': 'center',
                                  'base': {'offset': 0}, 'extras': {}, 'extensions': {}}},
                     junctions={'A': {'level': 'L', 'position': [0, 0], 'join': {'kind': 'mitre'}}},
                     rooms={'R': {'level': 'L', 'anchor': [0, 0], 'function': 'unspecified'}},
                     slabs={}, extensionsRequired=[], site={'trueNorth': 0})
        o = canon.omit_defaults(d)
        self.assertEqual(o['walls']['W'], {'level': 'L', 'start': 'A', 'end': 'B'})
        self.assertEqual(o['junctions']['A'], {'level': 'L', 'position': [0, 0]})
        self.assertEqual(o['rooms']['R'], {'level': 'L', 'anchor': [0, 0]})
        self.assertNotIn('slabs', o)
        self.assertNotIn('extensionsRequired', o)
        self.assertEqual(o['site'], {})
        self.assertEqual(o['project'], {'name': 'p'})

    def test_derived_defaults_and_typed_properties_kept(self):
        d = self.doc(walls={'W': {'level': 'L', 'start': 'A', 'end': 'B', 'base': {'level': 'L', 'offset': 0},
                                  'top': {'level': 'L2', 'offset': 0}}},
                     openings={'O': {'wall': 'W', 'offset': 0, 'sill': 0, 'hinge': 'start', 'swing': 'left'}})
        o = canon.omit_defaults(d)
        self.assertEqual(o['walls']['W']['base'], {'level': 'L'})
        self.assertEqual(o['walls']['W']['top'], {'level': 'L2'})
        self.assertEqual(o['openings']['O'], {'wall': 'W', 'offset': 0, 'sill': 0, 'swing': 'left'})

    def test_extras_content_untouched(self):
        d = self.doc(extras={'x': {}, 'justification': 'center', 'n': 1.50})
        o = canon.omit_defaults(d)
        self.assertEqual(o['extras'], {'x': {}, 'justification': 'center', 'n': 1.5})
        self.assertIn('"n": 1.5', canon.canonical_bytes(d).decode())

    def test_hash_is_sha256_of_jcs(self):
        d = self.doc()
        self.assertEqual(canon.content_hash(d),
                         hashlib.sha256(b'{"floorspec":"0.1","project":{"name":"p"}}').hexdigest())


if __name__ == '__main__':
    unittest.main()

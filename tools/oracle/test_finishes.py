"""Materials, assets and finishes in the oracle (Core 0.3, chapter 18): which room each side of a wall faces,
the order a face's finish is resolved in, the exact region tests, a package validator's checks, and the
constant defaults the canonical form omits - each value worked out by hand."""
import copy
import hashlib
import json
import unittest

from tools.oracle import canon
from tools.oracle.validate import READER_02, READER_03, check

MM = 1280
IN = 32512
H = 2700 * MM
WT = {'kind': 'wallType', 'layers': [{'thickness': 100 * MM, 'function': 'core'}]}


def house(**members):
    """Two rooms, W (west) and E (east), in a 6 m x 4 m box drawn clockwise, split by W7 from J6 (3 m, 0)
    north to J3 (3 m, 4 m)."""
    p = {'J1': [0, 0], 'J2': [0, 4000], 'J3': [3000, 4000], 'J4': [6000, 4000], 'J5': [6000, 0], 'J6': [3000, 0]}
    d = {'floorspec': '0.3', 'project': {'name': 'x'}, 'buildings': {'B1': {}},
         'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
         'types': {'WT': copy.deepcopy(WT)},
         'junctions': {j: {'level': 'L1', 'position': [x * MM, y * MM]} for j, (x, y) in p.items()},
         'walls': {f'W{i + 1}': {'level': 'L1', 'start': a, 'end': b, 'type': 'WT'}
                   for i, (a, b) in enumerate([('J1', 'J2'), ('J2', 'J3'), ('J3', 'J4'), ('J4', 'J5'), ('J5', 'J6'),
                                               ('J6', 'J1'), ('J6', 'J3')])},
         'rooms': {'W': {'level': 'L1', 'anchor': [1500 * MM, 2000 * MM]},
                   'E': {'level': 'L1', 'anchor': [4500 * MM, 2000 * MM]}},
         'materials': {}}
    for k, v in members.items():
        d[k] = {**d.get(k, {}), **v}
    return d


def run(d, reader=READER_03, package=None):
    result, canonical, notes = check(json.dumps(d).encode('utf-8'), reader, package=package)
    return result, canonical


def codes(result):
    return [(x['code'], x['elements']) for x in result['diagnostics'] if x['severity'] == 'error']


def finishes(d):
    result, _ = run(d)
    assert result['valid'], result['diagnostics']
    return result['derived']['finishes']


class Facing(unittest.TestCase):
    def test_each_side_of_a_wall_faces_the_room_on_that_side(self):
        d = house(materials={'A': {}, 'B': {}})
        d['rooms']['W']['wallFinish'], d['rooms']['E']['wallFinish'] = 'A', 'B'
        walls = finishes(d)['walls']
        # W7 runs north: west is its left, east its right
        self.assertEqual((walls['W7']['left']['room'], walls['W7']['right']['room']), ('W', 'E'))
        # the box is drawn clockwise, so every outer wall's right face is inside and its left face outside
        for wid, rid in (('W1', 'W'), ('W2', 'W'), ('W3', 'E'), ('W4', 'E'), ('W5', 'E'), ('W6', 'W')):
            self.assertEqual(walls[wid], {'right': {'room': rid, 'material': 'AB'[rid == 'E'], 'source': 'room',
                                                    'regions': []}})

    def test_an_unanchored_face_is_no_room(self):
        d = house(materials={'A': {}})
        del d['rooms']['E']
        d['rooms']['W']['wallFinish'] = 'A'
        walls = finishes(d)['walls']
        self.assertEqual(walls['W7'], {'left': {'room': 'W', 'material': 'A', 'source': 'room', 'regions': []}})
        self.assertNotIn('W3', walls)


class Precedence(unittest.TestCase):
    def setUp(self):
        self.d = house(materials={'ROOM': {}, 'FACE': {}, 'OUT': {}, 'IN': {}, 'R': {}, 'FLOOR': {}})
        self.d['types']['WT']['layers'] = [{'thickness': 20 * MM, 'function': 'finish', 'material': 'OUT'},
                                           {'thickness': 80 * MM, 'function': 'core'},
                                           {'thickness': 10 * MM, 'function': 'finish', 'material': 'IN'}]

    def face(self, wid, side):
        return finishes(self.d)['walls'][wid][side]

    def test_layer_then_room_then_face(self):
        self.assertEqual(self.face('W1', 'right'), {'room': 'W', 'material': 'IN', 'source': 'layer', 'regions': []})
        self.assertEqual(self.face('W1', 'left'), {'material': 'OUT', 'source': 'layer', 'regions': []})
        self.d['rooms']['W']['wallFinish'] = 'ROOM'
        self.assertEqual(self.face('W1', 'right')['material'], 'ROOM')
        self.assertEqual(self.face('W1', 'left')['material'], 'OUT')       # faces the outside: no room
        self.d['walls']['W1']['finishes'] = {'right': {'material': 'FACE'}, 'left': {'material': 'FACE'}}
        self.assertEqual((self.face('W1', 'right')['source'], self.face('W1', 'left')['source']), ('face', 'face'))

    def test_a_region_is_listed_as_declared_over_the_face(self):
        r = {'from': 0, 'to': 1000 * MM, 'bottom': 36 * IN, 'top': 54 * IN, 'material': 'R'}
        self.d['walls']['W2']['finishes'] = {'right': {'regions': [r]}}
        self.assertEqual(self.face('W2', 'right'), {'room': 'W', 'material': 'IN', 'source': 'layer', 'regions': [r]})

    def test_regions_alone(self):
        self.d['types']['WT']['layers'] = [WT['layers'][0]]
        r = {'from': 0, 'to': 1, 'bottom': 0, 'top': 1, 'material': 'R'}
        self.d['walls']['W2']['finishes'] = {'left': {'regions': [r]}}
        self.assertEqual(finishes(self.d)['walls'], {'W2': {'left': {'regions': [r]}}})

    def test_floor_and_ceiling(self):
        self.d['rooms']['E'].update(floorFinish='FLOOR', ceilingFinish='ROOM')
        self.d['rooms']['W']['ceilingFinish'] = 'ROOM'
        self.assertEqual(finishes(self.d)['rooms'], {'E': {'floor': 'FLOOR', 'ceiling': 'ROOM'}, 'W': {'ceiling': 'ROOM'}})


class Regions(unittest.TestCase):
    def doc(self, *regions, wid='W2', side='right'):
        d = house(materials={'R': {}})
        d['walls'][wid]['finishes'] = {side: {'regions': [{'from': f, 'to': t, 'bottom': b, 'top': u, 'material': 'R'}
                                                          for f, t, b, u in regions]}}
        return d

    def test_extent(self):
        L = 3000 * MM                                                   # W2: J2 (0, 4 m) to J3 (3 m, 4 m)
        self.assertEqual(codes(run(self.doc((0, L, 0, H)))[0]), [])
        self.assertEqual(codes(run(self.doc((0, L + 1, 0, H)))[0]), [('FS-INV-1002', ['W2'])])
        self.assertEqual(codes(run(self.doc((0, L, 0, H + 1)))[0]), [('FS-INV-1002', ['W2'])])
        self.assertEqual(codes(run(self.doc((5, 5, 0, H)))[0]), [('FS-INV-1001', ['W2'])])
        self.assertEqual(codes(run(self.doc((0, 5, 7, 7)))[0]), [('FS-INV-1001', ['W2'])])

    def test_touching_is_not_overlapping(self):
        self.assertEqual(codes(run(self.doc((0, 10, 0, 10), (10, 20, 0, 10), (0, 10, 10, 20)))[0]), [])
        self.assertEqual(codes(run(self.doc((0, 10, 0, 10), (9, 20, 9, 20)))[0]), [('FS-INV-1003', ['W2'])])
        # an empty region overlaps nothing it is not tested against
        self.assertEqual(codes(run(self.doc((0, 10, 0, 10), (5, 5, 0, 10)))[0]), [('FS-INV-1001', ['W2'])])

    def test_oblique_length_is_exact(self):
        d = house(materials={'R': {}})
        d['junctions']['J7'] = {'level': 'L1', 'position': [7000 * MM, 1000 * MM]}
        d['junctions']['J8'] = {'level': 'L1', 'position': [8000 * MM, 3000 * MM]}
        d['walls']['W8'] = {'level': 'L1', 'start': 'J7', 'end': 'J8', 'type': 'WT'}
        # |d| = 1280000 * sqrt(5) = 2862167.0807...
        for to, want in ((2862167, []), (2862168, [('FS-INV-1002', ['W8'])])):
            d['walls']['W8']['finishes'] = {'left': {'regions': [{'from': 0, 'to': to, 'bottom': 0, 'top': 1, 'material': 'R'}]}}
            self.assertEqual(codes(run(d)[0]), want)


class Maps(unittest.TestCase):
    def test_media_types(self):
        for media, want in (('image/png', []), ('image/jpeg', []), ('image/webp', []), ('image/ktx2', []),
                            ('image/svg+xml', [('FS-INV-1004', ['A', 'M'])]), ('image/gif', [('FS-INV-1004', ['A', 'M'])])):
            for m in ('asset', 'normal', 'metallicRoughness', 'occlusion'):
                d = house(materials={'M': {'texture': {m: 'A', 'size': [1, 1]}}},
                          assets={'A': {'path': 'a', 'sha256': 'ab' * 32, 'mediaType': media}})
                self.assertEqual(codes(run(d)[0]), want, (media, m))

    def test_every_map_is_a_reference(self):
        d = house(materials={'M': {'texture': {'occlusion': 'NONE', 'size': [1, 1]}}})
        self.assertEqual(codes(run(d)[0]), [('FS-INV-002', ['M'])])


class Package(unittest.TestCase):
    DATA = b'not really a png'

    def doc(self, **asset):
        a = {'path': 'assets/a.png', 'sha256': hashlib.sha256(self.DATA).hexdigest(), 'mediaType': 'image/png',
             'byteLength': len(self.DATA)}
        a.update(asset)
        return house(materials={'M': {'texture': {'asset': 'A', 'size': [1, 1]}}}, assets={'A': a})

    def test_checks(self):
        ok = {'assets/a.png': self.DATA}
        self.assertEqual(codes(run(self.doc(), package=ok)[0]), [])
        self.assertEqual(codes(run(self.doc(), package={})[0]), [('FS-INV-1005', ['A'])])
        self.assertEqual(codes(run(self.doc(), package={'assets/A.png': self.DATA})[0]), [('FS-INV-1005', ['A'])])
        self.assertEqual(codes(run(self.doc(), package={'assets/a.png': self.DATA + b'!'})[0]),
                         [('FS-INV-1006', ['A']), ('FS-INV-1007', ['A'])])
        self.assertEqual(codes(run(self.doc(byteLength=1), package=ok)[0]), [('FS-INV-1007', ['A'])])
        self.assertEqual(codes(run(self.doc(byteLength=1), package={})[0]), [('FS-INV-1005', ['A'])])

    def test_not_a_package_validator(self):
        self.assertEqual(codes(run(self.doc(byteLength=1, sha256='00' * 32))[0]), [])

    def test_uri_assets_are_not_checked(self):
        d = self.doc()
        del d['assets']['A']['path']
        d['assets']['A']['uri'] = 'https://example.com/a.png'
        self.assertEqual(codes(run(d, package={})[0]), [])


class Canonical(unittest.TestCase):
    def test_constant_defaults(self):
        d = house(materials={'M': {'metallic': 0, 'roughness': 1000,
                                   'texture': {'asset': 'A', 'size': [1, 1], 'offset': [0, 0], 'rotation': 0}}},
                  assets={'A': {'path': 'a', 'sha256': 'ab' * 32, 'mediaType': 'image/png'}})
        d['walls']['W1']['finishes'] = {'left': {'regions': []}, 'right': {}}
        d['walls']['W2']['finishes'] = {'left': {'material': 'M', 'regions': []}}
        out = canon.omit_defaults(d)
        self.assertEqual(out['materials']['M'], {'metallic': 0, 'roughness': 1000, 'texture': {'asset': 'A', 'size': [1, 1]}})
        self.assertNotIn('finishes', out['walls']['W1'])
        self.assertEqual(out['walls']['W2']['finishes'], {'left': {'material': 'M'}})
        d['materials']['M']['texture'].update(offset=[0, 1], rotation=1)
        self.assertEqual(canon.omit_defaults(d)['materials']['M']['texture']['offset'], [0, 1])


class EarlierDrafts(unittest.TestCase):
    def test_a_0_2_reader_derives_no_finishes(self):
        d = house(materials={'A': {}})
        d['floorspec'] = '0.2'
        d['rooms']['W']['wallFinish'] = 'A'
        r2, r3 = run(d, READER_02)[0], run(d, READER_03)[0]
        self.assertNotIn('finishes', r2['derived'])
        self.assertEqual(r3['derived']['finishes']['walls']['W1']['right']['material'], 'A')


if __name__ == '__main__':
    unittest.main()

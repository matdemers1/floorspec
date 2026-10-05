"""The Core 0.3 tests of materials, assets and finishes (chapter 18): the group `materials`.

Declared by tools/oracle/author03.py, which calls declare() among its new tests and retarget() on
every 0.2 test it carries forward; kept in a module of its own so that the chapter's tests read as
one piece. Every expected diagnostic is written by hand; the derived `finishes`, hashes and canonical
forms come from the oracle (tools/oracle/finishes.py), whose own tests (test_finishes.py) pin the
values that matter by hand. A test with a `package` is run by a package validator (18.4): its files
are written under the test's package/ directory.
"""
import copy
import hashlib
import struct
import zlib

from tools.oracle.author import CX, CY, X, Y
from tools.oracle.author import room_doc as room_doc_01
from tools.oracle.author_lib import IN, MM, H, J, R, W, t

SCH = [('FS-SCH-001', [])]
T100 = 100 * MM


def v3(d):
    d = copy.deepcopy(d)
    d['floorspec'] = '0.3'
    return d


def room_doc(**extra):
    """The 4 m x 3 m room R1 inside four 100 mm walls drawn clockwise - W1 west, W2 north, W3 east,
    W4 south, their right faces inside - 2700 mm high, declaring 0.3."""
    return v3(room_doc_01(**extra))


def png(rgb: tuple[int, int, int]) -> bytes:
    """A 2 x 2 PNG of one colour: real image bytes for a package, written the same way every time."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    raw = b''.join(b'\x00' + bytes(rgb) * 2 for _ in range(2))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def packaged(path, data, media='image/png', **kw):
    """An asset located by `path` whose digest and length are those of `data`."""
    return {'path': path, 'sha256': sha(data), 'mediaType': media, 'byteLength': len(data), **kw}


def asset(path, media='image/png', byte='ab'):
    return {'path': path, 'sha256': byte * 32, 'mediaType': media}


TILE_PNG = png((216, 212, 204))                   # a grey-white tile
OAK_PNG = png((200, 161, 101))
FT12 = 12 * IN                                    # 390,144: one foot
COUNTER, CABINETS = 36 * IN, 54 * IN              # 1,170,432 and 1,755,648
BACKSPLASH = {'from': 600 * MM, 'to': 3400 * MM, 'bottom': COUNTER, 'top': CABINETS, 'material': 'TILE'}
PAINT = {'name': 'Eggshell paint', 'color': '#e9e6df', 'roughness': 700}
TILE = {'name': 'Porcelain tile, 12 inch', 'color': '#d8d4cc', 'roughness': 300,
        'texture': {'asset': 'TILE-PHOTO', 'size': [FT12, FT12]}}


def finished(**members):
    """room_doc with these top-level members merged in."""
    d = room_doc()
    for k, v in members.items():
        d[k] = {**d.get(k, {}), **copy.deepcopy(v)} if isinstance(v, dict) else copy.deepcopy(v)
    return d


def kitchen(**members):
    """The room as a painted kitchen with the 12-inch tile photo as its backsplash on W2's right face, the
    exit demo of FLR-P-8: the photo is in the package at assets/tile-12in.png."""
    d = finished(materials={'PAINT': PAINT, 'TILE': TILE},
                 assets={'TILE-PHOTO': packaged('assets/tile-12in.png', TILE_PNG)}, **members)
    d['rooms']['R1'].update(name='Kitchen', function='kitchen', wallFinish='PAINT')
    d['walls']['W2']['finishes'] = {'right': {'regions': [dict(BACKSPLASH)]}}
    return d


def regions(d, wid, side, *rs, material=None):
    face = {}
    if material is not None:
        face['material'] = material
    if rs:
        face['regions'] = [dict(r) for r in rs]
    d['walls'][wid].setdefault('finishes', {})[side] = face
    return d


def reg(f, to, bottom, top, material='TILE'):
    return {'from': f, 'to': to, 'bottom': bottom, 'top': top, 'material': material}


def retarget(tc):
    """A 0.2 test whose document uses, as a member a texture does not have, one that 0.3 gives it."""
    if tc['slug'] == 'texture-unknown-member':
        tex = tc['inp']['materials']['M1']['texture']
        del tex['rotation']
        tex['repeat'] = False
        tc['description'] = ('A texture has only the members of its table (18.2): "repeat" is not one of them - '
                             'every texture repeats.')
    return tc


def declare():
    n = t
    # ---------------------------------------------------------------------------- materials (18.1, 18.2)
    d = finished(materials={'OAK': {'name': 'White oak, oiled', 'color': '#c8a165', 'metallic': 0, 'roughness': 450,
                                    'texture': {'asset': 'OAK-COLOR', 'normal': 'OAK-NORMAL',
                                                'metallicRoughness': 'OAK-MR', 'occlusion': 'OAK-AO',
                                                'size': [150 * MM, 1200 * MM], 'offset': [75 * MM, 0],
                                                'rotation': 90_000_000}}},
                 assets={'OAK-COLOR': asset('textures/oak/color.jpg', 'image/jpeg'),
                         'OAK-NORMAL': asset('textures/oak/normal.png', 'image/png', 'cd'),
                         'OAK-MR': asset('textures/oak/mr.webp', 'image/webp', 'ef'),
                         'OAK-AO': {**asset('textures/oak/ao.ktx2', 'image/ktx2', '01'), 'byteLength': 65536}})
    d['rooms']['R1']['floorFinish'] = 'OAK'
    n('materials', 'pbr-material-with-every-map', 'A physically based oak floor: a colour, metallic 0, roughness '
      '450 thousandths, and a texture with all four maps - base colour (JPEG), normal (PNG), metallic-roughness '
      '(WebP) and occlusion (KTX2, with a byteLength) - laid in 150 mm x 1200 mm tiles, offset 75 mm and turned '
      '90 degrees. Valid; the validator is not given the package, so nothing is said of the files; every asset is '
      'used, and the room\'s floor derives the oak.', ['18.1.1', '18.2.1', '18.2.2', '8.5.2', '18.4.1', '18.4.4',
                                                        '18.6.1', '3.2.1'], d)
    d = finished(materials={'STEEL': {'name': 'Brushed stainless', 'color': '#c0c0c0', 'metallic': 1000, 'roughness': 0},
                            'MATTE': {'metallic': 0, 'roughness': 1000}})
    d['rooms']['R1'].update(wallFinish='STEEL', ceilingFinish='MATTE')
    n('materials', 'metallic-and-roughness-at-their-limits', 'metallic and roughness are integers from 0 to 1000: a '
      'bare metal at 1000 and 0, and a matte dielectric at 0 and 1000, with no texture.', ['18.1.1', '18.6.1'], d)
    d = finished(materials={'DETAIL': {'roughness': 600, 'texture': {'normal': 'PLASTER-N', 'size': [FT12, FT12]}}},
                 assets={'PLASTER-N': asset('textures/plaster-normal.png')})
    d['rooms']['R1']['wallFinish'] = 'DETAIL'
    n('materials', 'texture-with-only-a-normal-map', 'A texture needs at least one map, not a base colour map: a '
      'plaster wall that is only a normal map, at 12 inches, has no declared base colour (18.1). Valid.',
      ['18.2.1', '18.6.1'], d)
    d = finished(materials={'BRICK': {'color': '#9c4a32',
                                      'texture': {'asset': 'BRICK-PHOTO', 'normal': 'BRICK-N', 'size': [FT12, FT12]}}},
                 assets={'BRICK-PHOTO': asset('textures/brick.png'),
                         'BRICK-N': {'uri': 'https://textures.example.com/brick/normal.png', 'sha256': '9a' * 32,
                                     'mediaType': 'image/png'}})
    d['rooms']['R1']['wallFinish'] = 'BRICK'
    n('materials', 'texture-map-by-uri', 'A brick texture whose normal map is located by uri: valid, and the asset is '
      'warned as not portable (FS-LINT-007). It is used, so it is not FS-LINT-006.', ['18.2.1', '8.7.1', '8.6.1'],
      d, [('FS-LINT-007', ['BRICK-N'])])
    d = finished(materials={'OAK': {'metallic': 0, 'texture': {'asset': 'OAK-COLOR', 'size': [FT12, FT12],
                                                               'offset': [0, 0], 'rotation': 0}}},
                 assets={'OAK-COLOR': asset('textures/oak.png')})
    d['rooms']['R1']['floorFinish'] = 'OAK'
    d['walls']['W1']['finishes'] = {'left': {'regions': []}, 'right': {}}
    n('materials', 'constant-defaults-omitted', 'A texture\'s offset [0, 0] and rotation 0, a face finish with no '
      'regions, an empty face finish and so empty finishes are constant defaults, which the canonical form omits; '
      'metallic 0 is not - absent, it is its map\'s - so it is kept.', ['9.2.1', '1.5.1', '18.2.1', '18.5.1'], d)

    # ---------------------------------------------------------------------------- finishes (18.5, 18.6)
    d = finished(materials={'PAINT': PAINT, 'OAK': {'color': '#c8a165'}, 'WHITE': {'color': '#ffffff'}})
    d['rooms']['R1'].update(wallFinish='PAINT', floorFinish='OAK', ceilingFinish='WHITE')
    n('materials', 'room-finishes-inherited', 'A room that names its wall, floor and ceiling finishes: the right '
      'face of each of its four walls faces it and inherits its paint (source "room"); its floor is oak and its '
      'ceiling white. The walls\' left faces face the outside and have no finish.', ['18.6.1'], d)
    d = finished(materials={'PAINT': PAINT, 'ACCENT': {'name': 'Accent wall', 'color': '#2f4f6f'}})
    d['rooms']['R1']['wallFinish'] = 'PAINT'
    regions(d, 'W2', 'right', material='ACCENT')
    n('materials', 'face-overrides-the-room', 'The same painted room with one accent wall: W2\'s right face names its '
      'own material, which wins over the room\'s on that face alone (source "face"); the other three faces inherit '
      'the paint.', ['18.5.1', '18.6.1'], d)
    d = kitchen()
    n('materials', 'tile-photo-on-the-backsplash', 'The exit demo of FLR-P-8: a photo of a tile, set to 12 inches, '
      'applied to the kitchen\'s backsplash - a region of W2\'s right face from 600 mm to 3400 mm along the wall '
      'and from the counter at 36 inches to the cabinets at 54 inches. The kitchen\'s paint finishes the rest of the '
      'face and the other walls. Run by a package validator: the photo is in the package at its path, with its '
      'digest and length. Valid.', ['18.5.1', '18.5.2', '18.5.3', '18.6.1', '18.2.1', '18.4.2', '18.4.3'],
      d, package={'assets/tile-12in.png': TILE_PNG})
    wt = {'kind': 'wallType', 'name': 'Exterior 2x6, sided',
          'layers': [{'thickness': 20 * MM, 'function': 'finish', 'material': 'SIDING'},
                     {'thickness': 140 * MM, 'function': 'core', 'material': 'STUD'},
                     {'thickness': 13 * MM, 'function': 'finish', 'material': 'GWB'}]}
    d = finished(types={'EXT': wt},
                 materials={'SIDING': {'color': '#7d8c80'}, 'STUD': {'color': '#e8d3a3'}, 'GWB': {'color': '#f2f0eb'},
                            'STONE': {'color': '#8a8178'}})
    del d['types']['WT']
    for w in ('W1', 'W2', 'W3', 'W4'):
        d['walls'][w]['type'] = 'EXT'
    regions(d, 'W4', 'left', reg(0, 4000 * MM, 0, 900 * MM, 'STONE'))
    n('materials', 'faces-finished-by-their-layers', 'An unfinished room in sided exterior walls drawn clockwise: '
      'each wall\'s left face faces the outside and shows its first layer\'s siding, each right face faces the room, '
      'which names no finish, and shows its last layer\'s gypsum board (source "layer"). A stone wainscot is a '
      'region of W4\'s left face, which faces no room.', ['18.6.1', '18.5.1'], d)
    d = v3(room_doc_01())
    d['junctions'] = {'J1': J(0, 0), 'J2': J(0, Y), 'J3': J(X // 2, Y), 'J4': J(X, Y), 'J5': J(X, 0), 'J6': J(X // 2, 0)}
    d['walls'] = {'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J5'),
                  'W5': W('J5', 'J6'), 'W6': W('J6', 'J1'), 'W7': W('J6', 'J3')}
    d['rooms'] = {'BED': R(X // 4, CY, name='Bedroom', function='sleeping', wallFinish='BLUE'),
                  'OFF': R(3 * X // 4, CY, name='Office', function='office', wallFinish='GREEN')}
    d['materials'] = {'BLUE': {'color': '#9db4c8'}, 'GREEN': {'color': '#a9c2a0'}, 'CORK': {'color': '#b58a5a'}}
    regions(d, 'W7', 'left', material='CORK')
    n('materials', 'two-rooms-either-side-of-a-wall', 'A bedroom and an office either side of W7, drawn north from '
      'J6 on the south wall to J3 on the north wall: the bedroom (west) is on its left and the office (east) on its '
      'right. Its left face names cork, which only the bedroom sees; its right face inherits the office\'s green.',
      ['18.6.1'], d)
    d = room_doc()
    d['rooms']['R1']['anchor'] = [CX, 800 * MM]
    d['junctions'].update({'J5': J(1500 * MM, CY), 'J6': J(2500 * MM, CY)})
    d['walls']['W5'] = W('J5', 'J6')
    d['materials'] = {'PAINT': PAINT}
    d['rooms']['R1']['wallFinish'] = 'PAINT'
    n('materials', 'wall-inside-a-room', 'A free-standing wall W5 inside the room - an inner cycle of its face '
      '(6.1): both its sides face the room, and both inherit its paint.', ['18.6.1'], d)
    d = kitchen()
    d['materials']['PANEL'] = {'color': '#ffffff'}
    regions(d, 'W2', 'right', reg(600 * MM, 3400 * MM, 0, COUNTER, 'PANEL'), BACKSPLASH,
            reg(600 * MM, 2000 * MM, CABINETS, H, 'PANEL'))
    regions(d, 'W4', 'right', reg(0, X, 0, H, 'TILE'))
    n('materials', 'regions-sharing-edges', 'Regions of one face may share an edge: W2\'s right face has panelling '
      'below the backsplash and above part of it, each meeting it along its whole edge. W4\'s right face is tiled '
      'by one region the whole length of its location line and the whole height of the wall, the largest a region '
      'may be. Valid; each face lists its regions in the order the wall does.', ['18.5.3', '18.5.4', '18.6.1'], d,
      package={'assets/tile-12in.png': TILE_PNG})
    d = room_doc()
    d['junctions'] = {'J1': J(0, 0), 'J2': J(1000 * MM, 2000 * MM)}
    d['walls'] = {'W1': W('J1', 'J2')}
    d['rooms'] = {}
    d['materials'] = {'TILE': {'color': '#d8d4cc'}}
    edge = 2862167          # sqrt(1280000^2 + 2560000^2) = 2862167.08...
    regions(d, 'W1', 'left', reg(0, edge, 0, H))
    regions(d, 'W1', 'right', reg(0, edge + 1, 0, H))
    n('materials', 'region-to-on-an-oblique-wall', 'A wall from (0, 0) to (1000 mm, 2000 mm) is 2,862,167.08... base '
      'units long. A region on its left face that ends at 2,862,167 fits; one on its right face that ends at '
      '2,862,168 does not (18.5.3): the test is exact, to^2 <= dx^2 + dy^2.', ['18.5.3'], d, [('FS-INV-1002', ['W1'])])

    # ---------------------------------------------------------------------------- invalid finishes
    d = kitchen()
    d['walls']['W2']['finishes']['right']['regions'][0]['to'] = 600 * MM
    n('materials', 'region-with-no-width', 'A region whose to is its from: FS-INV-1001.', ['18.5.2'], d,
      [('FS-INV-1001', ['W2'])], package={'assets/tile-12in.png': TILE_PNG})
    d = kitchen()
    d['walls']['W2']['finishes']['right']['regions'][0].update(bottom=CABINETS, top=COUNTER)
    n('materials', 'region-upside-down', 'A region whose top is below its bottom: FS-INV-1001.', ['18.5.2'], d,
      [('FS-INV-1001', ['W2'])], package={'assets/tile-12in.png': TILE_PNG})
    d = kitchen()
    d['walls']['W2']['finishes']['right']['regions'][0]['to'] = X + 1
    n('materials', 'region-past-the-wall-end', 'A region that ends one base unit past W2\'s 4 m location line: '
      'FS-INV-1002.', ['18.5.3'], d, [('FS-INV-1002', ['W2'])], package={'assets/tile-12in.png': TILE_PNG})
    d = kitchen()
    d['walls']['W2']['finishes']['right']['regions'][0]['top'] = H + 1
    n('materials', 'region-above-the-wall', 'A region whose top is one base unit above the wall\'s 2700 mm height: '
      'FS-INV-1002.', ['18.5.3'], d, [('FS-INV-1002', ['W2'])], package={'assets/tile-12in.png': TILE_PNG})
    d = kitchen()
    d['walls']['W2']['finishes']['right']['regions'][0].update({'from': X + 100, 'to': X + 100})
    n('materials', 'empty-region-not-measured', 'A region with no width, starting and ending past the wall\'s end: '
      'FS-INV-1001 only - FS-INV-1002 is not evaluated for a region that has FS-INV-1001 (10.3).',
      ['18.5.2', '10.3.1'], d, [('FS-INV-1001', ['W2'])], package={'assets/tile-12in.png': TILE_PNG})
    d = kitchen()
    d['walls']['W2']['top'] = {'height': 0}
    d['walls']['W2']['finishes']['right']['regions'][0]['top'] = 2 * H
    n('materials', 'region-on-a-wall-without-height', 'W2\'s top is not above its base (FS-INV-112), and its '
      'backsplash reaches twice the level\'s height: FS-INV-1002 does not test a region\'s top on a wall that has '
      'FS-INV-112 (10.3), so FS-INV-112 alone is reported.', ['10.3.1', '18.5.3'], d, [('FS-INV-112', ['W2'])],
      package={'assets/tile-12in.png': TILE_PNG})
    d = kitchen()
    regions(d, 'W2', 'right', BACKSPLASH, reg(3000 * MM, 3800 * MM, 1200 * MM, 2000 * MM),
            reg(0, 700 * MM, 0, CABINETS))
    n('materials', 'regions-overlap', 'Two regions of W2\'s right face overlap the backsplash, one at its east end and '
      'one at its west: FS-INV-1003 once for each pair. A region on the other face may be anywhere.', ['18.5.4'], d,
      [('FS-INV-1003', ['W2']), ('FS-INV-1003', ['W2'])], package={'assets/tile-12in.png': TILE_PNG})
    d = kitchen()
    regions(d, 'W2', 'left', reg(0, X, 0, H, 'PAINT'))
    n('materials', 'regions-on-two-faces-never-overlap', 'A region covering the whole of W2\'s left face, behind the '
      'backsplash on its right face: regions of different faces do not overlap.', ['18.5.4', '18.6.1'], d,
      package={'assets/tile-12in.png': TILE_PNG})
    d = kitchen()
    d['walls']['W2']['finishes']['right']['regions'][0]['material'] = 'GLASS'
    n('materials', 'region-material-missing', 'The backsplash names a material that does not exist: FS-INV-002, '
      'naming the wall; the photo it no longer uses is not evaluated, as no lint is for an invalid document.',
      ['3.2.1'], d, [('FS-INV-002', ['W2'])], package={'assets/tile-12in.png': TILE_PNG})
    d = finished(materials={'DETAIL': {'texture': {'normal': 'NOPE', 'size': [FT12, FT12]}}})
    d['rooms']['R1']['wallFinish'] = 'DETAIL'
    n('materials', 'normal-map-missing', 'A texture\'s normal map names an asset that does not exist: FS-INV-002, '
      'naming the material.', ['3.2.1'], d, [('FS-INV-002', ['DETAIL'])])
    d = finished(materials={'ODD': {'texture': {'asset': 'VECTOR', 'normal': 'MODEL', 'size': [FT12, FT12]}}},
                 assets={'VECTOR': asset('textures/tile.svg', 'image/svg+xml'),
                         'MODEL': asset('models/tile.glb', 'model/gltf-binary', 'cd')})
    d['rooms']['R1']['floorFinish'] = 'ODD'
    n('materials', 'maps-that-are-not-images', 'A base colour map that is an SVG and a normal map that is a glTF '
      'model: a map is a PNG, JPEG, WebP or KTX2 image. FS-INV-1004 once for each, naming the material and the '
      'asset.', ['18.2.2'], d, [('FS-INV-1004', ['ODD', 'VECTOR']), ('FS-INV-1004', ['MODEL', 'ODD'])])

    # ---------------------------------------------------------------------------- the package (18.4)
    d = kitchen()
    d['materials']['OAK'] = {'texture': {'asset': 'OAK-PHOTO', 'size': [150 * MM, 1200 * MM]}}
    d['assets']['OAK-PHOTO'] = {'uri': 'https://textures.example.com/oak.png', 'sha256': sha(OAK_PNG),
                                'mediaType': 'image/png'}
    d['assets']['SPARE'] = packaged('assets/spare.png', OAK_PNG)
    d['rooms']['R1']['floorFinish'] = 'OAK'
    n('materials', 'package-checks-only-packaged-assets', 'A package validator checks every asset located by path: '
      'the photo and an unused spare are in the package, and match; the oak, located by uri, is not checked - it is '
      'warned (FS-LINT-007) and never fetched. Valid, and the spare is unused (FS-LINT-006).', ['18.4.2', '18.4.3'],
      d, [('FS-LINT-006', ['SPARE']), ('FS-LINT-007', ['OAK-PHOTO'])],
      package={'assets/tile-12in.png': TILE_PNG, 'assets/spare.png': OAK_PNG})
    d = kitchen()
    d['assets']['TILE-PHOTO']['byteLength'] = 1
    n('materials', 'package-file-missing', 'The package has no file at the photo\'s path: FS-INV-1005. Its digest '
      'and its (wrong) byteLength are not evaluated (10.3).', ['18.4.2', '10.3.1'], d,
      [('FS-INV-1005', ['TILE-PHOTO'])], package={'assets/oak.png': OAK_PNG})
    d = kitchen()
    n('materials', 'package-path-is-exact', 'The package\'s file is assets/Tile-12in.png and the asset\'s path '
      'assets/tile-12in.png: a path names one file exactly, case and all, so there is no file at it: FS-INV-1005.',
      ['18.4.2'], d, [('FS-INV-1005', ['TILE-PHOTO'])], package={'assets/Tile-12in.png': TILE_PNG})
    d = kitchen()
    other = png((216, 212, 205))
    assert len(other) == len(TILE_PNG)
    n('materials', 'package-digest-mismatch', 'The file at the photo\'s path is another image of the same length: '
      'its SHA-256 is not the asset\'s sha256: FS-INV-1006.', ['18.4.3'], d, [('FS-INV-1006', ['TILE-PHOTO'])],
      package={'assets/tile-12in.png': other})
    d = kitchen()
    d['assets']['TILE-PHOTO']['byteLength'] = len(TILE_PNG) + 1
    n('materials', 'package-length-mismatch', 'The photo is the file its digest names, but its byteLength is one more '
      'than the file\'s length: FS-INV-1007.', ['18.4.3'], d, [('FS-INV-1007', ['TILE-PHOTO'])],
      package={'assets/tile-12in.png': TILE_PNG})
    d = kitchen()
    d['assets']['TILE-PHOTO']['byteLength'] = 1
    n('materials', 'package-not-given', 'The kitchen with a wrong byteLength, read by a validator that is not given '
      'the package: valid - FS-INV-1005 to FS-INV-1007 are a package validator\'s alone.', ['18.4.4'], d)

    # ---------------------------------------------------------------------------- earlier drafts (1.2.6)
    d = room_doc_01()
    d['types']['WT']['layers'][0]['material'] = 'BLOCK'
    d['materials'] = {'BLOCK': {'color': '#9a9a9a'}, 'PAINT': {'color': '#e9e6df'},
                      'OAK': {'texture': {'asset': 'A1', 'size': [150 * MM, 1200 * MM]}}}
    d['assets'] = {'A1': asset('textures/oak.png')}
    d['rooms']['R1'].update(wallFinish='PAINT', floorFinish='OAK')
    d['walls']['W3']['layers'] = [{'thickness': T100, 'function': 'core'}]
    n('materials', 'read-0.1-finishes', 'A 0.1 document with a room\'s wall and floor finishes and a layer material, '
      'read by a reader of 0.3: it derives its finishes - the room\'s paint on every right face, the block on the '
      'left faces of the walls of type WT, and nothing on W3\'s left face, whose own layer has no material.',
      ['1.2.6', '18.6.1'], d)

    # ---------------------------------------------------------------------------- the schema
    def sch(slug, description, covers, mut, base=kitchen):
        d = base()
        mut(d)
        n('materials', slug, description, covers, d, SCH)
    tile = lambda d: d['materials']['TILE']                         # noqa: E731
    tex = lambda d: d['materials']['TILE']['texture']               # noqa: E731
    face = lambda d: d['walls']['W2']['finishes']['right']          # noqa: E731
    region = lambda d: face(d)['regions'][0]                        # noqa: E731
    sch('metallic-above-1000', 'metallic is in thousandths, at most 1000.', ['18.1.1'], lambda d: tile(d).update(metallic=1001))
    sch('roughness-negative', 'roughness is at least 0.', ['18.1.1'], lambda d: tile(d).update(roughness=-1))
    sch('roughness-fraction', 'roughness 0.3 is a fraction, not thousandths.', ['18.1.1'],
        lambda d: tile(d).update(roughness=0.3))
    sch('texture-without-a-map', 'A texture with a size and no map.', ['18.2.1'], lambda d: tex(d).pop('asset'))
    sch('texture-rotation-out-of-range', 'A texture\'s rotation of -180,000,000: the range is (-180,000,000, '
        '180,000,000].', ['18.2.1'], lambda d: tex(d).update(rotation=-180_000_000))
    sch('texture-offset-not-a-point', 'A texture\'s offset is a point, two lengths.', ['18.2.1'],
        lambda d: tex(d).update(offset=[0]))
    sch('texture-emissive', 'A texture has no emissive map in this draft (0.5).', ['18.2.1', '1.4.3'],
        lambda d: tex(d).update(emissive='TILE-PHOTO'))
    sch('byte-length-negative', 'An asset\'s byteLength is at least 0.', ['18.4.1'],
        lambda d: d['assets']['TILE-PHOTO'].update(byteLength=-1))
    sch('finishes-unknown-side', 'A wall\'s finishes are of its left and right faces: there is no "top".', ['18.5.1'],
        lambda d: d['walls']['W2']['finishes'].update(top={}))
    sch('face-finish-colour', 'A face finish names a material; it has no colour of its own.', ['18.5.1'],
        lambda d: face(d).update(color='#ffffff'))
    sch('region-without-material', 'A region without its material.', ['18.5.1'], lambda d: region(d).pop('material'))
    sch('region-bottom-negative', 'A region\'s bottom is not negative.', ['18.5.1'], lambda d: region(d).update(bottom=-1))
    sch('regions-not-an-array', 'A face\'s regions are an array.', ['18.5.1'],
        lambda d: face(d).update(regions=region(d)))
    d = kitchen()
    d['floorspec'] = '0.2'
    n('materials', '0.2-document-with-finishes', 'A document that declares "0.2" and gives a wall finishes, which 0.3 '
      'adds: Core 0.2\'s schema has none (1.2.6).', ['1.2.6', '18.5.1'], d, SCH)
    d = room_doc_01()
    d['floorspec'] = '0.2'
    d['materials'] = {'M': {'texture': {'normal': 'A1', 'size': [FT12, FT12]}}}
    d['assets'] = {'A1': asset('textures/n.png')}
    n('materials', '0.2-document-with-a-normal-map', 'A document that declares "0.2" with a texture that is only a '
      'normal map: Core 0.2\'s texture has an asset and a size, nothing else (1.2.6).', ['1.2.6', '18.2.1'], d, SCH)
    d = room_doc_01()
    d['materials'] = {'M': {'color': '#ffffff', 'roughness': 500}}
    n('materials', '0.1-document-with-roughness', 'A document that declares "0.1" with a material\'s roughness, which '
      '0.3 adds (1.2.6).', ['1.2.6', '18.1.1'], d, SCH)

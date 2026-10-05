"""The Ops 0.3 tests of materials, assets and finishes (Core 0.3, chapter 18).

Declared by tools/oracle/ops_author03.py, which calls declare() after its other new tests, so that every
earlier test keeps its number: materials and textures edited with setProperty, the FLR-P-8 exit demo
(a tile photo added, set to 12 inches and laid on the kitchen's backsplash in one batch), a wall's face
finish and regions, the Core invariants a batch is judged by, the removal table for a material or asset
that a finish or a texture's map names, a split wall cutting its regions (5.2 step 7) and the inverse.
Every expected status and diagnostic is written by hand; each check asserts the values that matter.
"""
import copy
import json

from tools.oracle.ops_author import ensure
from tools.oracle.ops_author_lib import FT, IN, MM, T, box, req

PAINT = {'name': 'Eggshell paint', 'color': '#e9e6df', 'roughness': 700}
PHOTO = {'path': 'assets/tile-12in.jpg', 'sha256': '5e' * 32, 'mediaType': 'image/jpeg', 'byteLength': 48213}
TILE = {'name': 'Porcelain tile, 12 inch', 'color': '#d8d4cc', 'roughness': 300,
        'texture': {'asset': 'TILE-PHOTO', 'size': [12 * IN, 12 * IN]}}
COUNTER, CABINETS = 36 * IN, 54 * IN
H = 2700 * MM


def splash(f, t, bottom=COUNTER, top=CABINETS, material='TILE'):
    return {'from': f, 'to': t, 'bottom': bottom, 'top': top, 'material': material}


def kitchen(tile=True, **walls):
    """The 12' x 10' box (W1 west, W2 north, W3 east, W4 south, drawn clockwise: their right faces inside) as a
    Core 0.3 document: R1 is a painted kitchen, and with `tile`, the 12-inch tile and its photo are in it. Each
    of `walls` is given those finishes."""
    d = box()
    d['floorspec'] = '0.3'
    d['rooms']['R1'].update(name='Kitchen', function='kitchen', wallFinish='PAINT')
    d['materials'] = {'PAINT': copy.deepcopy(PAINT)}
    if tile:
        d['materials']['TILE'] = copy.deepcopy(TILE)
        d['assets'] = {'TILE-PHOTO': copy.deepcopy(PHOTO)}
    for wid, f in walls.items():
        d['walls'][wid]['finishes'] = copy.deepcopy(f)
    return d


def finishes(B):
    """What a Core 0.3 deriver derives for B's finishes."""
    from tools.oracle.validate import READER_03, check
    result, _, _ = check(json.dumps(B).encode('utf-8'), READER_03)
    assert result['valid'], result['diagnostics']
    return result['derived']['finishes']


def face(B, wid, side='right'):
    return finishes(B)['walls'][wid][side]


BACKSPLASH = splash(2 * FT, 10 * FT)


def declare():
    T('primitives', 'tile-photo-on-the-backsplash', 'The exit demo of FLR-P-8, as one batch: addElement adds the '
      'photo of a tile as an asset and a material whose texture is that photo at 12 inches, and setProperty lays '
      'it on the kitchen\'s backsplash - a region of W2\'s right face from 2\' to 10\' along the wall, between the '
      'counter at 36" and the cabinets at 54", creating /finishes and /finishes/right on the way. The rest of the '
      'face is the kitchen\'s paint.', ['2.1.1', '2.3.1', '1.3.1'], kitchen(tile=False),
      req({'op': 'addElement', 'collection': 'assets', 'id': 'TILE-PHOTO', 'element': PHOTO},
          {'op': 'addElement', 'collection': 'materials', 'id': 'TILE', 'element': TILE},
          {'op': 'setProperty', 'id': 'W2', 'path': '/finishes/right/regions', 'value': [BACKSPLASH]}),
      check=lambda r, B: ensure(r['created'] == ['TILE', 'TILE-PHOTO'] and face(B, 'W2') == {
          'room': 'R1', 'material': 'PAINT', 'source': 'room', 'regions': [BACKSPLASH]}, face(B, 'W2')))
    T('primitives', 'set-a-face-finish', 'setProperty of W1\'s /finishes/right/material: the west wall\'s inside face '
      'is tiled, overriding the kitchen\'s paint on that face alone.', ['2.3.1'], kitchen(),
      req({'op': 'setProperty', 'id': 'W1', 'path': '/finishes/right/material', 'value': 'TILE'}),
      check=lambda r, B: ensure(face(B, 'W1')['source'] == 'face' and face(B, 'W3')['material'] == 'PAINT', finishes(B)))
    T('primitives', 'turn-a-tile-and-make-it-smaller', 'setProperty sets the tile\'s texture to 6 inches, turned 45 '
      'degrees, and declares it metallic 0: a material is edited like any other element.', ['2.3.1'],
      kitchen(W2={'right': {'regions': [BACKSPLASH]}}),
      req({'op': 'setProperty', 'id': 'TILE', 'path': '/texture/size', 'value': [6 * IN, 6 * IN]},
          {'op': 'setProperty', 'id': 'TILE', 'path': '/texture/rotation', 'value': 45_000_000},
          {'op': 'setProperty', 'id': 'TILE', 'path': '/metallic', 'value': 0}),
      check=lambda r, B: ensure(B['materials']['TILE']['texture'] == {'asset': 'TILE-PHOTO', 'size': [6 * IN, 6 * IN],
                                                                       'rotation': 45_000_000}
                                and B['materials']['TILE']['metallic'] == 0, B['materials']['TILE']))
    T('primitives', 'region-past-the-wall', 'setProperty of a backsplash that runs to 13\' on the 12\' north wall: '
      'the result has FS-INV-1002 (Core 18.5.3), so the batch is rejected with it.', ['1.2.3', '2.3.1'], kitchen(),
      req({'op': 'setProperty', 'id': 'W2', 'path': '/finishes/right/regions', 'value': [splash(2 * FT, 13 * FT)]}),
      'rejected', [('FS-INV-1002', ['W2'])])
    T('primitives', 'normal-map-not-an-image', 'setProperty makes the tile\'s normal map an asset that is a glTF '
      'model: FS-INV-1004 (Core 18.2.2) rejects the batch.', ['1.2.3', '2.3.1'],
      kitchen(W2={'right': {'regions': [BACKSPLASH]}}),
      req({'op': 'addElement', 'collection': 'assets', 'id': 'TILE-GLB',
           'element': {'path': 'assets/tile.glb', 'sha256': '7f' * 32, 'mediaType': 'model/gltf-binary'}},
          {'op': 'setProperty', 'id': 'TILE', 'path': '/texture/normal', 'value': 'TILE-GLB'}),
      'rejected', [('FS-INV-1004', ['TILE', 'TILE-GLB'])])
    T('primitives', 'remove-a-material-a-region-uses', 'Removing the tile is blocked by W2, whose backsplash region '
      'names it (2.2).', ['2.2.1'], kitchen(W2={'right': {'regions': [BACKSPLASH]}}),
      req({'op': 'removeElement', 'id': 'TILE'}), 'rejected', [('FS-OPS-006', ['TILE', 'W2'])])
    T('primitives', 'remove-a-material-a-face-uses', 'Removing the tile is blocked by W1, whose right face names it, '
      'with cascade or without: cascade does not apply to a material (2.2).', ['2.2.1'],
      kitchen(W1={'right': {'material': 'TILE'}}), req({'op': 'removeElement', 'id': 'TILE', 'cascade': True}),
      'rejected', [('FS-OPS-006', ['TILE', 'W1'])])
    d = kitchen(W2={'right': {'regions': [BACKSPLASH]}})
    d['assets']['TILE-N'] = {'path': 'assets/tile-normal.png', 'sha256': '6a' * 32, 'mediaType': 'image/png'}
    d['materials']['TILE']['texture']['normal'] = 'TILE-N'
    T('primitives', 'remove-an-asset-a-normal-map-uses', 'Removing the tile\'s normal map asset is blocked by the '
      'material whose texture names it (2.2): every map refers to its asset.', ['2.2.1'], d,
      req({'op': 'removeElement', 'id': 'TILE-N'}), 'rejected', [('FS-OPS-006', ['TILE', 'TILE-N'])])

    regions = [BACKSPLASH, splash(0, FT, CABINETS, H), splash(6 * FT, 8 * FT, 0, COUNTER)]
    T('normalization', 'split-wall-cuts-its-regions', 'W4, the south wall, runs west from J4 (12\', 0); its right face '
      'is tiled, with a backsplash from 2\' to 10\' along it, a band from 0 to 1\' above the cabinets and a panel '
      'from 6\' to 8\' below the counter. A wall drawn across it at 8\' east - 4\' along W4 - splits it (5.2): both '
      'pieces keep the face\'s tile, and each takes the regions cut to its interval, measured from its own start '
      '(step 7). W4, [0, 4\'], keeps the backsplash from 2\' to 4\' and the band; W7, [4\', 12\'], takes the '
      'backsplash from 0 to 6\' and the panel from 2\' to 4\'.', ['5.2.3', '5.2.1'],
      kitchen(W4={'right': {'material': 'TILE', 'regions': regions}}),
      req({'op': 'drawWall', 'level': 'L1', 'from': ["8'", 0], 'to': ["8'", "10'"], 'type': 'WT'}),
      check=lambda r, B: ensure(
          B['walls']['W4']['finishes'] == {'right': {'material': 'TILE', 'regions': [splash(2 * FT, 4 * FT), splash(0, FT, CABINETS, H)]}}
          and B['walls']['W7']['finishes'] == {'right': {'material': 'TILE', 'regions': [splash(0, 6 * FT), splash(2 * FT, 4 * FT, 0, COUNTER)]}}
          and (B['walls']['W7']['start'], B['walls']['W4']['end']) == (B['walls']['W4']['end'], B['walls']['W7']['start']),
          {w: B['walls'][w] for w in ('W4', 'W7')}))
    T('inverse', 'region-added-and-undone', 'Laying the backsplash on a wall with no finishes: the inverse unsets what '
      'the setProperty created, and applying it gives back A exactly (1.6.1).', ['1.6.1'], kitchen(),
      req({'op': 'setProperty', 'id': 'W2', 'path': '/finishes/right/regions', 'value': [BACKSPLASH]}),
      check=lambda r, B: ensure(r['inverse'] == [{'op': 'unsetProperty', 'id': 'W2', 'path': '/finishes'}], r['inverse']))
    a = kitchen(tile=False)
    a['floorspec'] = '0.2'
    del a['materials']['PAINT']['roughness']
    T('transactions', 'finishes-in-a-0.2-document', 'A backsplash laid on a wall of a Core 0.2 document that does not '
      'declare "0.3": Core 0.2\'s schema has no wall finishes (Core 1.2.6), so the result is invalid: FS-SCH-001.',
      ['1.2.3', '2.3.1'], a,
      req({'op': 'setProperty', 'id': 'W2', 'path': '/finishes/right/regions', 'value': [BACKSPLASH]}),
      'rejected', [('FS-SCH-001', [])])

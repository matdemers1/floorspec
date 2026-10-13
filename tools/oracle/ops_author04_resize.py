"""The tests of resizeElement (Ops 0.4, 4.11): the group `resize` of conformance/ops/0.4.

Imported by ops_author04.py. An extension element is resized by its box, from an anchor, in its frame; its
clearance envelopes are stretched with it, an FS_landscape element's outline or line kept in its box, and the
elements grouped with it (FS_furniture's `with`) moved by the part of it they stand by. Every expected status
and diagnostic is written by hand; the values that matter are asserted, by a person's arithmetic, in each
test's check.
"""
import copy
import math

from tools.oracle.ops_author import ensure
from tools.oracle.ops_author_lib import FT, IN, MM, T, house, req

G = 'resize'
FURN, LAND = 'FS_furniture', 'FS_landscape'


def h04(furniture=None, landscape=None):
    """The house of ops_author_lib as a Core 0.4 document, with these FS_furniture and FS_landscape collections."""
    d = house()
    d['floorspec'] = '0.4'
    used, ext = {}, {}
    if furniture is not None:
        used[FURN] = '0.1.0'
        ext[FURN] = {'collections': copy.deepcopy(furniture)}
    if landscape is not None:
        used[LAND] = '0.1.0'
        ext[LAND] = {'collections': copy.deepcopy(landscape)}
    d['extensionsUsed'] = used
    d['extensions'] = ext
    return d


def box(w, d, h, bottom=0):
    """FS_furniture 3.1's box of an item w wide, d deep and h tall, its bottom at `bottom`."""
    return {'min': [0, -(w // 2), bottom], 'max': [d, w - w // 2, bottom + h]}


def on_floor(x, y, rotation=None, room='R3'):
    h = {'mode': 'surface', 'room': room, 'surface': 'floor', 'position': [x, y]}
    if rotation is not None:
        h['rotation'] = rotation
    return h


def item(category, b, host=None, **kw):
    e = {'category': category, 'fallback': {'level': 'L1', 'box': b}, **kw}
    if host is not None:
        e['host'] = host
    return e


ISLAND_BOX = box(72 * IN, 36 * IN, 36 * IN)
WORKING = {'purpose': 'workingSpace', 'shape': 'box',               # FS_furniture 4.2: front, standing 1,000 mm
           'min': [36 * IN, -36 * IN, 0], 'max': [36 * IN + 1000 * MM, 36 * IN, 2000 * MM]}


def kitchen(rotation=None, at=(16 * FT, 4 * FT)):
    """An island X1 in the Dining room (R3: 12' to 24' east, 0 to 12' north), 72" wide, 36" deep and 36" tall,
    its back at `at`, facing east (or turned by `rotation`), with its working space in front; on it a bowl X2,
    at its middle, standing on its top; a stool X3 with it, behind it and past its north end; a picture X5 with
    it, hung on the Dining room's east wall; and a chair X4 that is with nothing."""
    x, y = at
    return h04(furniture={
        'casework': {'X1': item('island', copy.deepcopy(ISLAND_BOX), on_floor(x, y, rotation),
                                clearances={'working': copy.deepcopy(WORKING)})},
        'pieces': {'X2': item('other', box(10 * IN, 10 * IN, 4 * IN, bottom=36 * IN), on_floor(x + 18 * IN, y), **{'with': 'X1'}),
                   'X3': item('stool', box(16 * IN, 16 * IN, 30 * IN), on_floor(x - 12 * IN, y + 40 * IN), **{'with': 'X1'}),
                   'X4': item('chair', box(18 * IN, 18 * IN, 34 * IN), on_floor(21 * FT, 6 * FT)),
                   'X5': item('other', box(24 * IN, 1 * IN, 30 * IN),
                              {'mode': 'wallFace', 'wall': 'W5', 'side': 'right', 'offset': 6 * FT, 'height': 48 * IN},
                              **{'with': 'X1'})}})


def X(B, eid):
    for c in B['extensions'][FURN]['collections'].values():
        if eid in c:
            return c[eid]
    raise KeyError(eid)


def pos(B, eid):
    return X(B, eid)['host']['position']


def bx(B, eid):
    return X(B, eid)['fallback']['box']


A = kitchen()

T(G, 'make-the-island-ten-feet-long', 'resizeElement makes the island 10\' wide, holding its right (south) end: its '
  'box runs from -36" to 84" along its width now, its working space is as wide as it is, the bowl at its middle moves '
  'with its middle - 24" north - and the stool past its north end with that end, 48"; the picture with it on the '
  'wall, and the chair with nothing, stay where they are.', ['4.11.1', '4.11.2'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'right', 'width': "10'"}),
  check=lambda r, B: ensure(bx(B, 'X1') == {'min': [0, -36 * IN, 0], 'max': [36 * IN, 84 * IN, 36 * IN]}
                            and X(B, 'X1')['clearances']['working']['min'] == [36 * IN, -36 * IN, 0]
                            and X(B, 'X1')['clearances']['working']['max'] == [36 * IN + 1000 * MM, 84 * IN, 2000 * MM]
                            and pos(B, 'X2') == [16 * FT + 18 * IN, 4 * FT + 24 * IN]
                            and pos(B, 'X3') == [15 * FT, 4 * FT + 88 * IN]
                            and X(B, 'X4') == X(A, 'X4') and X(B, 'X5') == X(A, 'X5') and bx(B, 'X2') == bx(A, 'X2'), B))
T(G, 'grow-from-the-middle', 'resizeElement makes the island 96" wide from its center: it keeps FS_furniture\'s '
  'convention, -48" to 48"; the bowl at its middle does not move, and the stool past its north end moves 12" with '
  'that end.', ['4.11.1', '4.11.2'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'center', 'width': '96"'}),
  check=lambda r, B: ensure(bx(B, 'X1') == box(96 * IN, 36 * IN, 36 * IN) and pos(B, 'X2') == pos(A, 'X2')
                            and pos(B, 'X3') == [15 * FT, 4 * FT + 52 * IN]
                            and all(p['path'] != '/host/position' or p['id'] != 'X2' for p in r['resolved']), r['resolved']))
T(G, 'raise-the-counter', 'resizeElement makes the island 42" tall: it grows up from its bottom; the bowl standing on '
  'its top - its box\'s bottom at the island\'s old top, on the same floor - rises 6" with it; the stool, standing on '
  'the floor, does not; and the working space\'s top, above the island\'s, rises with it.', ['4.11.1', '4.11.2'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'center', 'height': '42"'}),
  check=lambda r, B: ensure(bx(B, 'X1') == box(72 * IN, 36 * IN, 42 * IN)
                            and bx(B, 'X2') == box(10 * IN, 10 * IN, 4 * IN, bottom=42 * IN)
                            and bx(B, 'X3') == bx(A, 'X3') and pos(B, 'X2') == pos(A, 'X2')
                            and X(B, 'X1')['clearances']['working']['max'][2] == 2000 * MM + 6 * IN, B))
T(G, 'deeper-from-the-back', 'resizeElement makes the island 42" deep holding its back: its front moves 6" forward, and '
  'its working space with it, as deep as it was; the bowl, inside its depth, moves 3" - what its middle moves - and '
  'the stool behind its back stays.', ['4.11.1', '4.11.2'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'back', 'depth': '42"'}),
  check=lambda r, B: ensure(bx(B, 'X1') == box(72 * IN, 42 * IN, 36 * IN)
                            and X(B, 'X1')['clearances']['working']['min'][0] == 42 * IN
                            and X(B, 'X1')['clearances']['working']['max'][0] == 42 * IN + 1000 * MM
                            and pos(B, 'X2') == [16 * FT + 21 * IN, 4 * FT] and pos(B, 'X3') == pos(A, 'X3'), B))
T(G, 'from-a-corner', 'resizeElement makes the island 84" wide and 30" deep holding its front-left corner: its box '
  'runs from 6" to 36" deep and from -48" to 36" wide; the bowl moves by what its middle moves on both axes, 3" '
  'forward and 6" south, and the stool, behind its old back and past its left end, by what each of those sides moves: '
  '6" forward and not at all along it.', ['4.11.1', '4.11.2'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'front-left', 'width': '84"', 'depth': '30"'}),
  check=lambda r, B: ensure(bx(B, 'X1') == {'min': [6 * IN, -48 * IN, 0], 'max': [36 * IN, 36 * IN, 36 * IN]}
                            and pos(B, 'X2') == [16 * FT + 21 * IN, 4 * FT - 6 * IN]
                            and pos(B, 'X3') == [15 * FT + 6 * IN, 4 * FT + 40 * IN], B))

TURNED = kitchen(rotation=90_000_000, at=(17 * FT, 4 * FT))
T(G, 'turned-island', 'The island turned 90 degrees, facing north - its x is north and its y west. resizeElement makes '
  'it 8\' wide holding its left, west, end: it grows 24" east; the bowl on its back edge, 18" east of its middle, and the '
  'stool past its front, 12" west of its middle - both between its ends - move with its middle, 12" east.',
  ['4.11.1', '4.11.2'], TURNED,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'left', 'width': "8'"}),
  check=lambda r, B: ensure(bx(B, 'X1') == {'min': [0, -60 * IN, 0], 'max': [36 * IN, 36 * IN, 36 * IN]}
                            and pos(B, 'X2') == [17 * FT + 30 * IN, 4 * FT] and pos(B, 'X3') == [17 * FT, 4 * FT + 40 * IN], B))

SKEW = kitchen(rotation=45_000_000, at=(17 * FT, 4 * FT))
SKEW['extensions'][FURN]['collections']['pieces']['X2']['host']['position'] = [18 * FT, 5 * FT]
SHIFT = round(12 * IN / math.sqrt(2))     # 12" along the island's y, (-1, 1) / sqrt 2: not a tie, so a float decides it
T(G, 'island-at-45-degrees', 'The island turned 45 degrees, and the bowl 1\' east and 1\' north of its back: sqrt 2 '
  'feet along its depth and on its middle line. resizeElement makes it 96" wide holding its right end: the bowl '
  'moves with its middle, 12" along the island\'s y, (-1, 1) / sqrt 2 - each coordinate of the move computed exactly '
  'and rounded once.', ['4.11.2'], SKEW,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'right', 'width': '96"'}),
  check=lambda r, B: ensure(pos(B, 'X2') == [18 * FT - SHIFT, 5 * FT + SHIFT], pos(B, 'X2')))


def tall(oven_offset=4 * FT):
    """A tall cabinet X1, 24" wide, on the inner (right) face of the Dining room's east wall W5 - which runs south,
    from J5 (24', 12') to J6 (24', 0) - 4' from J5, with a wall oven X2 set into it, on the same face at the same
    height, and a microwave X3 with it on another wall."""
    face = {'mode': 'wallFace', 'wall': 'W5', 'side': 'right', 'height': 0}
    return h04(furniture={
        'casework': {'X1': item('tallCabinet', box(24 * IN, 24 * IN, 84 * IN), {**face, 'offset': 4 * FT})},
        'appliances': {'X2': item('wallOven', box(24 * IN, 22 * IN, 30 * IN, bottom=30 * IN), {**face, 'offset': oven_offset},
                                  **{'with': 'X1'}),
                       'X3': item('microwave', box(20 * IN, 14 * IN, 12 * IN),
                                  {'mode': 'wallFace', 'wall': 'W6', 'side': 'right', 'offset': 4 * FT, 'height': 54 * IN},
                                  **{'with': 'X1'})}})


T(G, 'oven-follows-its-cabinet', 'A tall cabinet on a wall face made 30" wide, holding its right: a right face\'s y '
  'runs towards the wall\'s end, so it grows 6" towards J6, south; the wall oven set into it, on the same face, moves '
  'with its middle - its offset 3" more - and the microwave with it on another wall stays where it is.',
  ['4.11.2'], tall(),
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'right', 'width': '30"'}),
  check=lambda r, B: ensure(bx(B, 'X1') == {'min': [0, -12 * IN, 0], 'max': [24 * IN, 18 * IN, 84 * IN]}
                            and X(B, 'X2')['host']['offset'] == 4 * FT + 3 * IN
                            and X(B, 'X3') == X(tall(), 'X3'), B))
T(G, 'half-a-unit-to-even', 'The cabinet made one base unit wider holding its right, and the oven one unit past its '
  'middle, at an odd offset: the oven moves half a unit, which is rounded to even - from 1,560,577 to 1,560,578.',
  ['4.11.2'], tall(oven_offset=4 * FT + 1),
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'right', 'width': 24 * IN + 1}),
  check=lambda r, B: ensure(X(B, 'X2')['host']['offset'] == 4 * FT + 2, B))

T(G, 'within-its-limits', 'resizeElement with the sizes the island comes in, 72" to 120" wide: 96" is one of them, '
  'and the batch commits.', ['4.11.1'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'center', 'width': '96"',
       'limits': {'width': {'min': '72"', 'max': '120"'}}}),
  check=lambda r, B: ensure(bx(B, 'X1') == box(96 * IN, 36 * IN, 36 * IN), B))
T(G, 'past-its-limits', 'The same island made 10\' wide when it comes no wider than 8\': FS-OPS-008, naming it.',
  ['4.11.1'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'center', 'width': "10'", 'limits': {'width': {'max': "8'"}}}),
  'rejected', [('FS-OPS-008', ['X1'])])
T(G, 'limits-of-an-axis-not-set', 'A limit on the depth, which the island already exceeds, and a batch that sets only '
  'its width: only the extents it sets are checked, and it commits.', ['4.11.1'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'center', 'width': '84"', 'limits': {'depth': {'max': '30"'}}}),
  check=lambda r, B: ensure(bx(B, 'X1') == box(84 * IN, 36 * IN, 36 * IN), B))
T(G, 'resize-a-room', 'resizeElement of R3, a room: the member expects an extension element, and a room is not one - '
  'FS-OPS-003.', ['4.11.1', '3.3.1'], A,
  req({'op': 'resizeElement', 'element': 'R3', 'anchor': 'center', 'width': "10'"}), 'rejected', [('FS-OPS-003', [])])
T(G, 'no-box-to-resize', 'The island\'s box unset earlier in the batch: there is no box to resize - FS-OPS-003, naming '
  'it.', ['4.11.1'], A,
  req({'op': 'unsetProperty', 'id': 'X1', 'path': '/fallback/box'},
      {'op': 'resizeElement', 'element': 'X1', 'anchor': 'center', 'width': "10'"}), 'rejected', [('FS-OPS-003', ['X1'])])
T(G, 'too-thin', 'resizeElement makes the island 0 wide: its box, and its working space stretched with it, are each '
  'narrower than 1 mm (Core 13.2.2), and the batch is rejected with FS-INV-505 once for each.', ['4.11.1', '1.2.3'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'center', 'width': 0}), 'rejected',
  [('FS-INV-505', ['X1']), ('FS-INV-505', ['X1'])])
T(G, 'resize-without-a-size', 'resizeElement with none of width, depth and height, of which it takes at least one: '
  'the request is malformed, FS-OPS-001.', ['1.1.4'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'center'}), 'rejected', [('FS-OPS-001', [])])
T(G, 'limits-of-a-length', 'resizeElement whose limits name a "length", which is not one of its axes: malformed, '
  'FS-OPS-001.', ['1.1.4'], A,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'center', 'width': "8'", 'limits': {'length': {'max': "8'"}}}),
  'rejected', [('FS-OPS-001', [])])

RUG = h04(furniture={'pieces': {
    'X1': item('other', {'min': [30 * FT, 0, 0], 'max': [38 * FT, 5 * FT, 16 * IN // 32]}),
    'X2': item('coffeeTable', box(48 * IN, 24 * IN, 18 * IN), {'mode': 'free', 'level': 'L1', 'position': [34 * FT, 30 * IN]},
               **{'with': 'X1'})}})
T(G, 'rug-without-a-host', 'A rug with no host - its box is in the level\'s own frame, east of the house - and a coffee '
  'table standing free on it: resizeElement makes the rug 10\' deep holding its back, at x = 30\'; the table, between '
  'its back and its front, moves with its middle, 1\' east.', ['4.11.2'], RUG,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'back', 'depth': "10'"}),
  check=lambda r, B: ensure(bx(B, 'X1')['max'][0] == 40 * FT and pos(B, 'X2') == [35 * FT, 30 * IN], B))

BED = h04(landscape={'beds': {'X1': {
    'fallback': {'level': 'L1', 'box': {'min': [0, 0, 0], 'max': [4 * FT, 3 * FT, 6 * IN]}},
    'host': {'mode': 'free', 'level': 'L1', 'position': [30 * FT, 2 * FT]},
    'boundary': [[0, 0], [4 * FT, 0], [4 * FT, 2 * FT], [2 * FT, 3 * FT], [0, 2 * FT]]}}})
T(G, 'stretch-a-bed', 'An FS_landscape bed standing free east of the house, its outline in its frame: resizeElement '
  'makes it 6\' deep holding its back. The outline follows its box: the points on its back stay, those on its front '
  'move 2\' with it, and the point between, 2\' from the back, moves in proportion to 3\'.', ['4.11.1'], BED,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'back', 'depth': "6'"}),
  check=lambda r, B: ensure(B['extensions'][LAND]['collections']['beds']['X1']['boundary']
                            == [[0, 0], [6 * FT, 0], [6 * FT, 2 * FT], [3 * FT, 3 * FT], [0, 2 * FT]], B))

PATH = h04(landscape={'hardscape': {'X1': {
    'fallback': {'level': 'L1', 'box': {'min': [0, -18 * IN, 0], 'max': [10 * FT, 18 * IN, 2 * IN]}},
    'host': {'mode': 'free', 'level': 'L1', 'position': [30 * FT, 6 * FT]},
    'form': 'path', 'points': [[0, 0], [10 * FT, 0]], 'width': 3 * FT}}})
T(G, 'lengthen-a-path', 'An FS_landscape path 10\' long, its line in its frame: resizeElement makes its box 12\' deep '
  'holding its back, and its line runs to the new front; its width, across the line, is its own and stays 3\'.',
  ['4.11.1'], PATH,
  req({'op': 'resizeElement', 'element': 'X1', 'anchor': 'back', 'depth': "12'"}),
  check=lambda r, B: ensure(B['extensions'][LAND]['collections']['hardscape']['X1']['points'] == [[0, 0], [12 * FT, 0]]
                            and B['extensions'][LAND]['collections']['hardscape']['X1']['width'] == 3 * FT, B))

"""The tests of arc edges (Core 0.4, chapter 21) in Ops 0.4: the group `arcs` of conformance/ops/0.4.

Imported by ops_author04.py. An arc edge is added with the primitives Ops already has - addElement, or a wall drawn
and then given its `arc` with setProperty in the same batch - and edited with setProperty, unsetProperty and
moveJunction; planarization never routes or splits one (5.2, FS-OPS-013). Every expected status and diagnostic is
written by hand; the values that matter are asserted in each test's check.
"""
import json

from tools.oracle import arcs
from tools.oracle.ops_author import ensure
from tools.oracle.ops_author_lib import DOOR_W, FT, T, house, req

G = 'arcs'


def h04(**members):
    d = house(**members)
    d['floorspec'] = '0.4'
    return d


def bent(h=1 * FT):
    """The house with W8, the wall from J7 (12', 0) north to J8 (12', 8') between the Kitchen and the Dining room,
    an arc: a positive sagitta bulges to its left, west, into the Kitchen."""
    d = h04()
    d['walls']['W8']['arc'] = {'sagitta': h}
    return d


def derived(B):
    from tools.oracle.validate import READER_04, check as core_check
    result, _, _ = core_check(json.dumps(B).encode('utf-8'), READER_04)
    assert result['valid'], result['diagnostics']
    return result['derived']


def area(B, rid):
    return int(derived(B)['rooms'][rid]['area'].split('.')[0])


W8 = arcs.polyline((12 * FT, 0), (12 * FT, 8 * FT), 1 * FT)
W8_L = arcs.length(W8)

T(G, 'bend-a-wall', 'setProperty gives the wall between the Kitchen and the Dining room an arc of 1\': it bulges '
  'west, into the Kitchen, whose net area shrinks as the Dining room\'s grows; the wall derives its polyline. The '
  'level stays planar, so nothing is planarized.', ['2.3.1', '1.3.1'], h04(),
  req({'op': 'setProperty', 'id': 'W8', 'path': '/arc', 'value': {'sagitta': 1 * FT}}),
  check=lambda r, B: ensure(B['walls']['W8']['arc'] == {'sagitta': 1 * FT}
                            and derived(B)['walls']['W8']['polyline'] == [list(p) for p in W8]
                            and area(B, 'R1') < area(h04(), 'R1') and area(B, 'R3') > area(h04(), 'R3'), B))
T(G, 'straighten-a-wall', 'unsetProperty of the arc: the wall is straight again, and the result is A\'s house.',
  ['2.3.1'], bent(), req({'op': 'unsetProperty', 'id': 'W8', 'path': '/arc'}),
  check=lambda r, B: ensure('arc' not in B['walls']['W8'] and 'polyline' not in derived(B)['walls']['W8'], B))
T(G, 'flip-the-bulge', 'setProperty of /arc/sagitta to its negative: the wall bulges east, into the Dining room, by '
  'the same amount - its polyline is the old one mirrored in the chord.', ['2.3.1'], bent(),
  req({'op': 'setProperty', 'id': 'W8', 'path': '/arc/sagitta', 'value': -1 * FT}),
  check=lambda r, B: ensure(derived(B)['walls']['W8']['polyline'] == [[24 * FT - x, y] for x, y in W8], B))
T(G, 'move-a-junction-of-an-arc', 'moveJunction of J8 north by 1\': the arc keeps its sagitta and follows its '
  'junctions - its chord is 9\' long now, and it bends exactly as far from it.', ['2.4.1'], bent(),
  req({'op': 'moveJunction', 'id': 'J8', 'to': [12 * FT, 9 * FT]}),
  check=lambda r, B: ensure(B['walls']['W8']['arc'] == {'sagitta': 1 * FT}
                            and derived(B)['walls']['W8']['polyline']
                            == [list(p) for p in arcs.polyline((12 * FT, 0), (12 * FT, 9 * FT), 1 * FT)], B))


T(G, 'draw-an-arc-separator-onto-a-wall', 'drawSeparator from J8 to (24\', 8\'), a point inside the east wall W5, '
  'named S1 so that setProperty can give it an arc of 1\' in the same batch. Normalization then planarizes the level, '
  'because the new junction lies inside W5: W5, a straight wall, is split there; the arc separator, which ends at '
  'that junction and meets nothing else, is never routed, and keeps its arc (5.2).',
  ['5.2.4', '5.2.1', '4.1.1', '2.3.1'], h04(),
  req({'op': 'drawSeparator', 'id': 'S1', 'level': 'L1', 'from': 'J8', 'to': [24 * FT, 8 * FT]},
      {'op': 'setProperty', 'id': 'S1', 'path': '/arc', 'value': {'sagitta': 1 * FT}}),
  check=lambda r, B: ensure(B['separators']['S1']['arc'] == {'sagitta': 1 * FT}
                            and B['junctions'][B['separators']['S1']['end']]['position'] == [24 * FT, 8 * FT]
                            and len(B['walls']) == len(h04()['walls']) + 1, B))
T(G, 'arc-drawn-across-a-wall', 'A wall drawn from the Kitchen to the Dining room across W8 and given an arc in the '
  'same batch: planarization would have to split the arc where it crosses W8, and an arc edge is never routed or '
  'split - the batch is rejected with FS-OPS-013, naming the arc.', ['5.2.4'], h04(),
  req({'op': 'drawWall', 'id': 'W20', 'level': 'L1', 'from': [6 * FT, 2 * FT], 'to': [18 * FT, 2 * FT]},
      {'op': 'setProperty', 'id': 'W20', 'path': '/arc', 'value': {'sagitta': 1 * FT}}),
  'rejected', [('FS-OPS-013', ['W20'])])
T(G, 'wall-drawn-across-an-arc', 'A straight wall drawn across the arc W8: the straight wall could be split, but the '
  'crossing is on the arc too, which cannot - FS-OPS-013, naming W8.', ['5.2.4'], bent(),
  req({'op': 'drawWall', 'level': 'L1', 'from': [6 * FT, 2 * FT], 'to': [18 * FT, 2 * FT]}),
  'rejected', [('FS-OPS-013', ['W8'])])
T(G, 'straight-walls-split-beside-an-arc', 'A straight wall drawn across the Pantry, from (4\', 7\') to (4\', 13\'), '
  'on a level whose W8 is an arc: W10 and W3 are split where it meets them, as 5.2 splits straight edges; the arc, '
  'which nothing touches, is left exactly as it is.', ['5.2.4', '5.2.1'], bent(),
  req({'op': 'drawWall', 'level': 'L1', 'from': [4 * FT, 7 * FT], 'to': [4 * FT, 13 * FT], 'type': 'WT'}),
  check=lambda r, B: ensure(B['walls']['W8'] == bent()['walls']['W8'] and len(B['walls']) == len(bent()['walls']) + 5, B))
T(G, 'door-centered-on-an-arc', 'addOpening of a 36" door "centered" on the arc W8: the offset is half its length '
  'less the door\'s width, where the length is the arc\'s, along its polyline (Core 21.6): (L - w) / 2, rounded.',
  ['3.5.1', '4.5.3'], bent(),
  req({'op': 'addOpening', 'wall': 'W8', 'at': 'centered', 'fill': 'T-door-36'}),
  check=lambda r, B: ensure([o['offset'] for o in B['openings'].values()] == [round((W8_L - DOOR_W) / 2)], B))
T(G, 'door-from-the-end-of-an-arc', 'addOpening 1\' "from end" on the arc W8: L - 1\' - w.', ['3.5.1'], bent(),
  req({'op': 'addOpening', 'wall': 'W8', 'at': "1' from end", 'fill': 'T-door-36'}),
  check=lambda r, B: ensure([o['offset'] for o in B['openings'].values()] == [W8_L - FT - DOOR_W], B))
T(G, 'bend-too-far', 'setProperty of a sagitta of 5\' on the 8\' wall W8: more than a semicircle, so the result has '
  'FS-INV-113 and the batch is rejected with it.', ['1.2.3', '2.3.1'], h04(),
  req({'op': 'setProperty', 'id': 'W8', 'path': '/arc', 'value': {'sagitta': 5 * FT}}), 'rejected',
  [('FS-INV-113', ['W8'])])
T(G, 'length-lock-on-an-arc', 'A length lock on the arc W8, and a batch that bends it further: its length along its '
  'polyline changes, so the lock is broken - FS-OPS-011.', ['6.1.2'], bent(),
  req({'op': 'setProperty', 'id': 'W8', 'path': '/arc/sagitta', 'value': 2 * FT}, locks=[{'length': 'W8'}]),
  'rejected', [('FS-OPS-011', ['W8'])])
T(G, 'length-lock-on-an-arc-held', 'The same lock, and a batch that flips the bulge: the arc is the same length, so '
  'the lock holds.', ['6.1.2'], bent(),
  req({'op': 'setProperty', 'id': 'W8', 'path': '/arc/sagitta', 'value': -1 * FT}, locks=[{'length': 'W8'}]))
T(G, 'select-the-arc-between-two-rooms', 'setProperty of /name on "the wall between Kitchen and Dining": the faces of '
  'the two rooms meet along the arc\'s polyline (Core 21.5), and the selector finds the arc wall.', ['3.3.1', '3.4.1'],
  bent(), req({'op': 'setProperty', 'id': 'wall between Kitchen and Dining', 'path': '/name', 'value': 'Curved wall'}),
  check=lambda r, B: ensure(B['walls']['W8']['name'] == 'Curved wall', B))
T(G, 'move-an-arc-wall', 'moveWall of W8 by 1\' toward the Dining room: an arc wall moves along its chord\'s normal, '
  'both junctions by the same vector, and keeps its arc.', ['4.2.1'], bent(),
  req({'op': 'moveWall', 'wall': 'W8', 'by': "1'", 'toward': 'Dining'}),
  check=lambda r, B: ensure(B['junctions']['J7']['position'] == [13 * FT, 0]
                            and B['junctions']['J8']['position'] == [13 * FT, 8 * FT]
                            and B['walls']['W8']['arc'] == {'sagitta': 1 * FT}, B))

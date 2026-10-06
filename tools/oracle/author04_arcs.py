"""The tests of Core 0.4's chapter 21, arc edges: the group `arcs` of conformance/core/0.4.

Imported by author04.py, which writes them with the rest of the 0.4 suite. Every expected diagnostic is
written by hand; the values a reviewer can check - which side an arc bulges to, that a point lies between a
polyline and its circle, a length, a vertex count - are asserted here by hand, from exact arithmetic,
before the oracle writes the rest.
"""
import copy
from fractions import Fraction

from tools.oracle import arcs, plane
from tools.oracle.author02 import element, swing, wall_face, with_elements
from tools.oracle.author_lib import MM, J, R, S, W, level_doc, t

SCH = [('FS-SCH-001', [])]
G = 'arcs'


def n(slug, description, covers, inp, diags=(), **kw):
    t(G, slug, description, covers, inp, diags, **kw)


def doc04(**members):
    return level_doc(floorspec='0.4', **members)


def bay(h=1000 * MM, **kw):
    """A 5000 mm by 4000 mm room drawn clockwise with 100 mm walls, its north wall W2 an arc from J2 (0, 4000 mm)
    to J3 (5000 mm, 4000 mm) with sagitta h - positive bulges north, out of the room - and the room R1."""
    d = doc04(junctions={'J1': J(0, 0), 'J2': J(0, 4000 * MM), 'J3': J(5000 * MM, 4000 * MM), 'J4': J(5000 * MM, 0)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3', arc={'sagitta': h}), 'W3': W('J3', 'J4'),
                     'W4': W('J4', 'J1')},
              rooms={'R1': R(2500 * MM, 2000 * MM)})
    for k, v in kw.items():
        d[k] = {**d.get(k, {}), **v}
    return d


J2, J3 = (0, 4000 * MM), (5000 * MM, 4000 * MM)
BAY = arcs.polyline(J2, J3, 1000 * MM)
BAY_L = arcs.length(BAY)
# The bay's arc: chord 5000 mm along +X, so its centre (2500 mm, 4000 mm + h - R) and radius R are rational.
_R = arcs.radius(J2, J3, 1000 * MM)
_C = (Fraction(2500 * MM), 4000 * MM + 1000 * MM - _R)
assert _R == Fraction(25 * 10 ** 6 + 4 * 10 ** 6, 8000) * MM            # (5000^2 + 4 * 1000^2) / 8000 mm = 3625 mm
assert len(BAY) == 65 and arcs.depth_of(J2, J3, 1000 * MM) == 6
assert all(abs((x - _C[0]) ** 2 + (y - _C[1]) ** 2 - _R ** 2) < 4 * _R for x, y in BAY)    # within 2 units of the circle


def inside_circle(p) -> bool:
    return (p[0] - _C[0]) ** 2 + (p[1] - _C[1]) ** 2 < _R ** 2


def sliver_point():
    """An integer point north of the bay's polyline - outside the room by its polyline - and inside its circle:
    a point the polyline and the circle disagree on. Two base units north of the middle of the 33rd segment."""
    a, b = BAY[32], BAY[33]
    mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2 + 2)
    assert plane.orient(a, b, mid) > 0 and inside_circle(mid)
    return mid


# =================================================================================== the arc (21.1, 21.2)
n('bay-room', 'A room whose north wall is an arc bulging 1000 mm out of it, over a 5000 mm chord: radius 3625 mm, a '
  'sweep of about 87 degrees. Its polyline halves the arc six times on its deepest branch - 64 segments, every vertex '
  'within two base units of the circle - and the wall derives its polyline, its length (the sum of its segments\' '
  'rounded lengths) and its face vertices; the room polygon runs along the wall\'s inner face, through its right face '
  'vertices, and its net area is exact from them.',
  ['21.2.1', '21.3.2', '21.4.2', '21.5.1', '5.7.1', '6.2.1', '6.4.1', '2.2.1'], bay())
n('bay-inward', 'The same wall with a sagitta of -1000 mm: it bulges to its right, south, into the room, whose net area '
  'is smaller than its chord\'s rectangle by the segment the arc cuts off.', ['21.1.1', '21.2.1', '21.5.1'],
  bay(-1000 * MM))
n('semicircle', 'A sagitta of exactly half the chord, 2500 mm: a semicircle, which 21.1.2 allows. Its radius is its '
  'sagitta, and its polyline\'s first vertex is the arc\'s midpoint, (2500 mm, 6500 mm), an integer point.',
  ['21.1.2', '21.2.1'], bay(2500 * MM))
n('more-than-a-semicircle', 'A sagitta one base unit more than half the 5000 mm chord: 4 h^2 exceeds the chord\'s '
  'square, so the arc is more than a semicircle. FS-INV-113, a graph invariant: no room is checked on the level.',
  ['21.1.2'], bay(2500 * MM + 1), [('FS-INV-113', ['W2'])])
d = bay()
d['walls']['W2']['arc'] = {'sagitta': -2500 * MM - 1}
n('more-than-a-semicircle-inward', 'The same, bulging into the room: the sign of the sagitta does not change the '
  'test.', ['21.1.2'], d, [('FS-INV-113', ['W2'])])
n('oblique-arc', 'An arc on an oblique chord, from (0, 0) to (3000 mm, 1000 mm), with a sagitta of 500 mm: the chord\'s '
  'length is 1000 sqrt 10 mm, so the arc\'s midpoint, (1500 mm, 500 mm) + 500 (-1, 3) / sqrt 10 mm, and every vertex '
  'after it is irrational before it is rounded, each coordinate once, ties to even, decided exactly.',
  ['21.2.1', '2.2.1'],
  doc04(junctions={'J1': J(0, 0), 'J2': J(3000 * MM, 1000 * MM)}, walls={'W1': W('J1', 'J2', arc={'sagitta': 500 * MM})}))
FLAT = 1000
d = doc04(junctions={'J1': J(0, 0), 'J2': J(3000 * MM, 0)}, walls={'W1': W('J1', 'J2', arc={'sagitta': FLAT})})
assert arcs.polyline((0, 0), (3000 * MM, 0), FLAT) == ((0, 0), (3000 * MM, 0))
n('flat-arc', 'An arc whose sagitta, 1000 base units, is less than 1 mm: its polyline is its chord, so it is derived as a '
  'straight wall - its face vertices are none, its length 3000 mm - and the validator reports FS-LINT-020, '
  'information.', ['21.2.1', '21.8.1'], d, [('FS-LINT-020', ['W1'])])
d = doc04(junctions={'J1': J(0, 0), 'J2': J(3000 * MM, 0)}, walls={'W1': W('J1', 'J2', arc={'sagitta': 1281})})
assert len(arcs.polyline((0, 0), (3000 * MM, 0), 1281)) == 3
n('just-not-flat', 'A sagitta of 1281, one more than the tolerance: the arc is halved once, at its midpoint (1500 mm, '
  '1281), and each half, whose sagitta rounds to 320, is its chord - a polyline of two segments, and no lint.',
  ['21.2.1'], d)
# ---- schema (21.1.1)
for slug, arc, why in [
        ('sagitta-zero', {'sagitta': 0}, 'A sagitta of zero: a straight edge has no arc member.'),
        ('arc-without-sagitta', {}, 'An arc with no sagitta.'),
        ('arc-with-radius', {'sagitta': 1000 * MM, 'radius': 3625 * MM}, 'An arc has exactly the member sagitta: its '
         'radius is derived, never stored.'),
        ('sagitta-not-an-integer', {'sagitta': 1.5}, 'A sagitta of 1.5 base units is not a length.'),
        ('arc-not-an-object', 1000 * MM, 'An arc is an object, not a bare sagitta.')]:
    d = bay()
    d['walls']['W2']['arc'] = arc
    n(slug, why, ['21.1.1'], d, SCH)
d = bay()
d['floorspec'] = '0.3'
n('arc-in-a-0.3-document', 'A document that declares "0.3" with an arc wall: it is checked against Core 0.3\'s schema, '
  'which has no "arc" member (1.2.8).', ['1.2.8', '21.1.1'], d, SCH)

# =================================================================================== in the graph (21.3)
d = bay()
d['separators'] = {}
d['junctions'].update({'J5': J(0, 2000 * MM), 'J6': J(5000 * MM, 2000 * MM)})
d['walls'] = {'W1a': W('J1', 'J5'), 'W1b': W('J5', 'J2'), 'W2': W('J2', 'J3'), 'W3a': W('J3', 'J6'),
              'W3b': W('J6', 'J4'), 'W4': W('J4', 'J1')}
d['separators'] = {'S1': S('J5', 'J6')}
d['separators']['S1']['arc'] = {'sagitta': 800 * MM}
d['rooms'] = {'R1': R(2500 * MM, 1000 * MM), 'R2': R(2500 * MM, 3500 * MM)}
n('arc-separator', 'A rectangle split by a room separator that arcs 800 mm north from (0, 2000 mm) to (5000 mm, '
  '2000 mm): the separator has no thickness, so each room polygon runs along its polyline itself - R1\'s outward, '
  'R2\'s inward - and the two net areas differ from the straight split by the same exact amount.',
  ['21.2.1', '21.3.2', '21.5.1', '6.2.1', '6.4.1'], d)
SEP = arcs.polyline((0, 2000 * MM), (5000 * MM, 2000 * MM), 800 * MM)


def sep_sliver():
    """An integer point north of the separator's polyline and inside its circle."""
    Rs = arcs.radius((0, 2000 * MM), (5000 * MM, 2000 * MM), 800 * MM)
    C = (Fraction(2500 * MM), 2000 * MM + 800 * MM - Rs)
    a, b = SEP[16], SEP[17]
    p = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2 + 2)
    assert plane.orient(a, b, p) > 0 and (p[0] - C[0]) ** 2 + (p[1] - C[1]) ** 2 < Rs ** 2
    return p


d2 = copy.deepcopy(d)
d2['rooms']['R1'] = R(*sep_sliver())
n('anchor-between-polyline-and-circle', 'R1\'s anchor is two base units north of the middle of one of the separator\'s '
  'segments: inside the circle the separator follows, but north of its polyline - so in R2\'s face, not R1\'s. A room '
  'is the face its polyline bounds (21.5): both anchors are in one face, FS-INV-202.',
  ['21.5.1', '21.3.1', '6.3.2'], d2, [('FS-INV-202', ['R1', 'R2'])])
d = bay(junctions={'J5': J(2500 * MM, 3000 * MM), 'J6': J(2500 * MM, 6000 * MM)}, walls={'W5': W('J5', 'J6')})
n('arc-crosses-a-wall', 'A straight wall from inside the room to beyond the bay, through its arc: the two location '
  'lines cross where the straight wall crosses one of the arc\'s segments. FS-INV-104.', ['21.3.1'], d,
  [('FS-INV-104', ['W2', 'W5'])])
V = BAY[20]
u = (BAY[21][0] - BAY[19][0], BAY[21][1] - BAY[19][1])
d = bay(junctions={'J5': J(V[0] - u[0], V[1] - u[1]), 'J6': J(V[0] + u[0], V[1] + u[1])}, walls={'W5': W('J5', 'J6')})
assert all(plane.orient(d['junctions']['J5']['position'], d['junctions']['J6']['position'], p) <= 0 for p in BAY)
n('wall-touches-an-arc', 'A straight wall outside the bay through one vertex of its polyline, parallel to the chord of '
  'the two vertices either side: it touches the polyline at that vertex and nowhere else, crossing nothing. Two '
  'straight location lines cannot meet like that; a polyline\'s can, and meeting at a point interior to both is '
  'FS-INV-104 (21.3.1).', ['21.3.1'], d, [('FS-INV-104', ['W2', 'W5'])])
d = bay(junctions={'J5': J(*BAY[20]), 'J6': J(BAY[20][0], BAY[20][1] + 1000 * MM)}, walls={'W5': W('J5', 'J6')})
n('junction-on-an-arc-vertex', 'A wall that starts at a vertex of the bay\'s polyline and runs north: a vertex is no '
  'junction, so the arc does not end there - its junction lies inside the arc. FS-INV-105, and nothing else: the two '
  'lines meet only at the straight wall\'s end.', ['21.3.1'], d, [('FS-INV-105', ['J5', 'W2'])])
a0, a1 = BAY[0], BAY[1]
d = bay(junctions={'J5': J(2 * a1[0] - a0[0], 2 * a1[1] - a0[1])}, walls={'W5': W('J2', 'J5')})
n('wall-along-an-arc-segment', 'A straight wall from the arc\'s start junction along its first segment and on, twice as '
  'far: it overlaps that segment, and the vertex at its end, which is no junction, lies inside the straight wall. '
  'FS-INV-106 without FS-INV-105, which two straight edges never give.', ['21.3.1'], d, [('FS-INV-106', ['W2', 'W5'])])
p = sliver_point()
d = bay(junctions={'J5': J(*p), 'J6': J(p[0], p[1] + 1000 * MM)}, walls={'W5': W('J5', 'J6')})
n('wall-from-inside-the-circle', 'A straight wall that starts two base units north of the bay\'s polyline - between it '
  'and its circle - and runs north. It would cross the circle; it does not meet the polyline, which is the wall\'s '
  'location line, so the document is valid.', ['21.3.1', '21.2.1'], d)
d = bay()
d['junctions'].update({'J5': J(500 * MM, 3800 * MM), 'J6': J(4500 * MM, 3800 * MM)})
d['walls']['W5'] = W('J5', 'J6', arc={'sagitta': 1800 * MM})
n('two-arcs-cross', 'A second arc wall inside the room, from (500 mm, 3800 mm) to (4500 mm, 3800 mm) and bulging '
  '1800 mm north, out through the bay and back: two polylines cross. FS-INV-104.', ['21.3.1'], d, [('FS-INV-104', ['W2', 'W5'])])
d = bay(2500 * MM + 1, junctions={'J5': J(2500 * MM, 3000 * MM), 'J6': J(2500 * MM, 9000 * MM)},
        walls={'W5': W('J5', 'J6')}, openings={'O1': {'wall': 'W2', 'offset': 9000 * MM, 'width': 900 * MM,
                                                      'height': 2100 * MM}})
n('unfit-arc-is-not-tested-further', 'The arc of more than a semicircle with a straight wall across where it would be, '
  'and an opening 9 m along it: it has no polyline, so it is not tested for crossings, and has no length to test the '
  'opening against (10.3). FS-INV-113 alone.', ['10.3.1', '21.1.2'], d, [('FS-INV-113', ['W2'])])
d = bay()
d['junctions']['J2']['join'] = {'kind': 'butt', 'through': ['W2']}
n('arc-through-a-butt-join', 'The bay wall runs through the corner at J2, a butt join: the join acts on its first '
  'segment, which runs out to the outer corner while W1 stops against it.', ['21.3.2', '5.8.4'], d)
d = bay(junctions={'J5': J(7000 * MM, 7000 * MM)}, walls={'W5': W('J3', 'J5')})
n('junction-fill-at-an-arc', 'A third wall at the bay\'s end junction J3, running north-east: three edges meet there, '
  'one of them an arc, and the junction fill closes the gap between the arc\'s last segment and the two straight '
  'walls.', ['21.3.2', '5.7.3'], d)


def round_room():
    """A round room of three arcs of 120 degrees on a circle of 3000 mm about the origin, drawn clockwise."""
    pts = {'J1': (0, 3000 * MM), 'J2': (2598076 * MM // 1000, -1500 * MM), 'J3': (-2598076 * MM // 1000, -1500 * MM)}
    d = doc04(junctions={k: J(*v) for k, v in pts.items()}, rooms={'R1': R(0, 0)})
    walls = {}
    for wid, (a, b) in {'W1': ('J1', 'J2'), 'W2': ('J2', 'J3'), 'W3': ('J3', 'J1')}.items():
        A, B = pts[a], pts[b]
        C = (B[0] - A[0]) ** 2 + (B[1] - A[1]) ** 2
        h = arcs.sagitta_on(Fraction(3000 * MM), A, B, 1)
        assert 4 * h * h <= C
        walls[wid] = W(a, b, arc={'sagitta': h})
    d['walls'] = walls
    return d


n('round-room', 'A round room: three arc walls of 120 degrees between three junctions on a circle of 3000 mm, each with '
  'the sagitta of its chord on that circle, rounded. At each junction two arcs meet in a mitre of their end segments; '
  'the room polygon is the inner face all the way round, and its net area is within a fraction of a percent of the '
  'circle of 2950 mm.', ['21.3.2', '21.5.1', '21.2.1'], round_room())
d = doc04(junctions={'J1': J(0, 0), 'J2': J(200 * MM, 0)},
          walls={'W1': W('J1', 'J2', arc={'sagitta': 100 * MM}, type=None,
                         layers=[{'thickness': 300 * MM, 'function': 'core'}])})
n('wall-tighter-than-its-thickness', 'A semicircular wall of radius 100 mm, 300 mm thick and centred on its arc: its '
  'inner face would turn on a radius of -50 mm, so its face vertices on that side cross, and its outline is not '
  'simple. FS-INV-109.', ['21.4.3'], d, [('FS-INV-109', ['W1'])])

# =================================================================================== openings, hosts, regions (21.6)
DOOR = {'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM, 'clearances': {'swing': swing()}}
d = bay(types={'D': DOOR}, openings={'O1': {'wall': 'W2', 'offset': 2000 * MM, 'fill': 'D'}})
n('door-on-an-arc', 'A 900 mm door 2000 mm along the bay wall, measured on its polyline: its start and end points are '
  'the points at those distances, and the door stands on the chord between them; its swing clearance is a box in the '
  'frame at the middle of that chord, facing across it into the room. The door opens the room to the outside, so it '
  'is an entry.', ['21.6.1', '7.4.1', '13.5.2', '13.1.1'], d)
d = bay(types={'D': DOOR}, openings={'O1': {'wall': 'W2', 'offset': 2000 * MM, 'fill': 'D', 'swing': 'left'}})
n('door-on-an-arc-swinging-out', 'The same door swinging to the wall\'s left, out of the room: its frame faces the '
  'other way across its chord.', ['21.6.1', '13.5.2'], d)
d = bay(openings={'O1': {'wall': 'W2', 'offset': BAY_L - 900 * MM, 'width': 900 * MM, 'height': 2100 * MM}})
n('opening-to-the-end-of-an-arc', 'An opening that ends exactly at the bay wall\'s length - the sum of its segments\' '
  'rounded lengths: valid. It reaches into the join at J3, so FS-LINT-005.', ['21.6.2', '21.6.1'], d,
  [('FS-LINT-005', ['O1'])])
d = bay(openings={'O1': {'wall': 'W2', 'offset': BAY_L - 900 * MM + 1, 'width': 900 * MM, 'height': 2100 * MM}})
n('opening-past-an-arc', 'The same opening one base unit further along: it ends past the wall\'s length. FS-INV-302.',
  ['21.6.2'], d, [('FS-INV-302', ['O1'])])
d = bay(openings={'O1': {'wall': 'W2', 'offset': 2000 * MM, 'width': 900 * MM, 'height': 2100 * MM}})
n('opening-clear-of-the-joins', 'A cased opening in the middle of the bay: clear of both joins, measured along the first '
  'and the last segment, so no FS-LINT-005.', ['21.6.1', '7.5.1'], d)
d = bay(openings={'O1': {'wall': 'W2', 'offset': 20 * MM, 'width': 900 * MM, 'height': 2100 * MM}})
n('opening-in-the-join-of-an-arc', 'An opening 20 mm from the bay wall\'s start: the join at J2 reaches 50 mm along its '
  'first segment, so the opening is in it. FS-LINT-005.', ['7.5.1'], d, [('FS-LINT-005', ['O1'])])
PANEL = element(size=(400 * MM, 100 * MM, 600 * MM), origin=(-200 * MM, 0, 0))
d = with_elements(bay(), {'21.4.1': element(size=(400 * MM, 100 * MM, 600 * MM), origin=(-200 * MM, 0, 0),
                                        host=wall_face('W2', 'right', 2500 * MM, 1200 * MM)),
                          '21.4.2': element(size=(400 * MM, 100 * MM, 600 * MM), origin=(-200 * MM, 0, 0),
                                        host=wall_face('W2', 'left', BAY_L, 1200 * MM))})
n('hosts-on-an-arc', 'Two elements on the bay wall\'s faces: 21.4.1 2500 mm along its inner face, 21.4.2 at its very end on its '
  'outer face. Each frame is on its face, half the wall\'s thickness along the normal of the segment its distance '
  'falls on - 21.4.2\'s, at the end, on the last segment - and faces along that normal: into the room, and out of it.',
  ['21.6.1', '13.4.1', '13.1.1'], d)
d = with_elements(bay(), {'21.4.1': element(host=wall_face('W2', 'right', BAY_L + 1, 1200 * MM))})
n('host-past-an-arc', 'An element one base unit past the bay wall\'s length. FS-INV-501.', ['21.6.2'], d,
  [('FS-INV-501', ['21.4.1'])])
TILE = {'name': 'Tile', 'color': '#d8d4cc'}
d = bay(materials={'TILE': TILE})
d['walls']['W2']['finishes'] = {'right': {'regions': [{'from': 1000 * MM, 'to': BAY_L, 'bottom': 0, 'top': 1000 * MM,
                                                        'material': 'TILE'}]}}
n('region-on-an-arc', 'A tiled region of the bay wall\'s inner face, from 1000 mm to the wall\'s length: valid, and the '
  'face\'s finish lists it.', ['21.6.2', '18.6.1'], d)
d = bay(materials={'TILE': TILE})
d['walls']['W2']['finishes'] = {'right': {'regions': [{'from': 1000 * MM, 'to': BAY_L + 1, 'bottom': 0,
                                                        'top': 1000 * MM, 'material': 'TILE'}]}}
n('region-past-an-arc', 'The same region one base unit longer. FS-INV-1002.', ['21.6.2'], d, [('FS-INV-1002', ['W2'])])
d = bay(rooms={'R1': R(2500 * MM, 2000 * MM, ceiling={'kind': 'tray', 'border': 30 * MM, 'depth': 200 * MM})})
n('tray-in-a-curved-room', 'The bay room with a tray ceiling 30 mm in from its walls: the tray\'s centre is the room '
  'polygon moved in, edge by edge along the curve as along the straight walls, and its floor spans the polygon that '
  'follows the arc.', ['21.5.1', '15.4.2'], d)
d = bay(rooms={'R1': R(2500 * MM, 2000 * MM, ceiling={'kind': 'tray', 'border': 600 * MM, 'depth': 200 * MM})})
n('wide-tray-in-a-curved-room', 'The same tray 600 mm in from the walls: 15.4 moves every edge of the room polygon, '
  'and next to the corners at J2 and J3 the arc\'s edges are shorter than the corners move, so a moved edge runs '
  'backwards. FS-INV-703: a tray wider than an arc\'s segments does not fit (21.9).', ['15.4.1', '21.5.1'], d,
  [('FS-INV-703', ['R1'])])


def arch(join=None, thick=None):
    """A pointed arch: two arc walls rising from (0, 0) and (5000 mm, 0) to an apex at (2500 mm, 4000 mm), each
    bulging 600 mm outwards, closed by a straight wall below; drawn clockwise."""
    d = doc04(junctions={'J1': J(0, 0), 'J2': J(2500 * MM, 4000 * MM), 'J3': J(5000 * MM, 0)},
              walls={'W1': W('J1', 'J2', arc={'sagitta': 600 * MM}), 'W2': W('J2', 'J3', arc={'sagitta': 600 * MM}),
                     'W3': W('J3', 'J1')},
              rooms={'R1': R(2500 * MM, 1500 * MM)})
    if thick is not None:
        d['types']['WT']['layers'][0]['thickness'] = thick
    if join is not None:
        d['junctions']['J2']['join'] = join
    return d


n('pointed-arch', 'Two arcs, 300 mm walls, rising from a straight wall to an apex. At each foot an arc meets the straight '
  'wall at a sharp angle, and the two inner faces meet beyond the arc\'s first segment: the corner is found by moving '
  'along the arc\'s face path to its second piece (21.4), and the face vertex passed is cut off the wall\'s outline and '
  'the room polygon.', ['21.4.2', '21.4.1', '21.3.2', '21.5.1'], arch(thick=300 * MM))
n('pointed-arch-with-a-butt-join', 'The same arch with W1 running through the apex: W1\'s face on the convex side runs '
  'to the point where it meets W2\'s face on the reflex side, which lies beyond W2\'s first segment, so it is found on '
  'W2\'s second piece and W2\'s first face vertex there is cut off its outline. The room polygon is the same as under '
  'the mitre (5.8).', ['21.4.2', '21.4.1', '5.8.4'], arch(join={'kind': 'butt', 'through': ['W1']}, thick=300 * MM))

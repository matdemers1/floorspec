"""Hand-checked geometries: each expected value below is worked out in the comment beside it."""

import json
import unittest

from tools.oracle.derive import Doc, LevelGraph, derive, rpoint
from tools.oracle.validate import check


def doc(junctions, walls, rooms=None, separators=None, thickness=200, extra=None):
    d = {
        'floorspec': '0.1', 'project': {'name': 't'}, 'buildings': {'BLD': {}},
        'levels': {'L': {'building': 'BLD', 'elevation': 0, 'height': 1000}},
        'types': {'T': {'kind': 'wallType', 'layers': [{'thickness': thickness, 'function': 'core'}]}},
        'junctions': {k: {'level': 'L', 'position': list(p)} for k, p in junctions.items()},
        'walls': {k: {'level': 'L', 'start': s, 'end': e, 'type': 'T', **(extra or {}).get(k, {})}
                  for k, (s, e) in walls.items()},
        'separators': {k: {'level': 'L', 'start': s, 'end': e} for k, (s, e) in (separators or {}).items()},
        'rooms': {k: {'level': 'L', 'anchor': list(p)} for k, p in (rooms or {}).items()},
    }
    return d


def ends(d, wid):
    g = LevelGraph(Doc(d), 'L')
    return {k: rpoint(v) for k, v in g.face_ends(wid).items()}


class GeometryTest(unittest.TestCase):
    def test_free_end_is_square(self):
        # one wall (0,0)->(1000,0), T=200 centred: left face y=100, right face y=-100
        d = doc({'A': (0, 0), 'B': (1000, 0)}, {'W': ('A', 'B')})
        self.assertEqual(ends(d, 'W'), {'startLeft': (0, 100), 'startRight': (0, -100),
                                        'endLeft': (1000, 100), 'endRight': (1000, -100)})

    def test_l_corner_mitres(self):
        # W1 east from A, W2 north from B=(1000,0): outer corner (1100,-100), inner (900,100)
        d = doc({'A': (0, 0), 'B': (1000, 0), 'C': (1000, 1000)}, {'W1': ('A', 'B'), 'W2': ('B', 'C')})
        self.assertEqual(ends(d, 'W1')['endRight'], (1100, -100))
        self.assertEqual(ends(d, 'W1')['endLeft'], (900, 100))
        self.assertEqual(ends(d, 'W2')['startRight'], (1100, -100))
        self.assertEqual(ends(d, 'W2')['startLeft'], (900, 100))

    def test_odd_thickness_on_a_3_4_5_direction_ties_to_even(self):
        # (0,0)->(3000,4000), T=5 centred: offsets 5/2, unit normal (-4/5, 3/5).
        # start feet: (-2, 1.5) and (2, -1.5) -> y ties -> (-2, 2) and (2, -2)
        # end feet: (3002, 3998.5) -> (3002, 3998); (2998, 4001.5) -> (2998, 4002)
        d = doc({'A': (0, 0), 'B': (3000, 4000)}, {'W': ('A', 'B')}, thickness=5)
        self.assertEqual(ends(d, 'W'), {'startLeft': (-2, 2), 'startRight': (2, -2),
                                        'endRight': (3002, 3998), 'endLeft': (2998, 4002)})

    def test_diagonal_corner_is_irrational(self):
        # (0,0)->(1000,1000), T=2 centred: feet at +-(1/sqrt2)(-1, 1) = +-(-0.707, 0.707)
        d = doc({'A': (0, 0), 'B': (1000, 1000)}, {'W': ('A', 'B')}, thickness=2)
        e = ends(d, 'W')
        self.assertEqual(e['startLeft'], (-1, 1))
        self.assertEqual(e['startRight'], (1, -1))

    def test_t_junction_fill_is_a_triangle(self):
        # through walls east and west of J=(0,0), stem south; T=200:
        # wedge E->W: feet coincide at (0,100); W->S: (-100,-100); S->E: (100,-100)
        d = doc({'J': (0, 0), 'E': (1000, 0), 'W': (-1000, 0), 'S': (0, -1000)},
                {'WE': ('J', 'E'), 'WW': ('J', 'W'), 'WS': ('J', 'S')})
        out = derive(Doc(d))
        self.assertEqual(out['junctionFills']['J'], [[-100, -100], [100, -100], [0, 100]])

    def test_room_with_a_freestanding_wall_hole(self):
        # a 1000x1000 room of T=20 walls drawn clockwise, a freestanding wall (400,500)->(600,500)
        # inside: the room ring is the inner faces (10..990), the hole is the wall's rectangle,
        # clockwise from its least vertex (390, 490)
        d = doc({'A': (0, 0), 'B': (0, 1000), 'C': (1000, 1000), 'D': (1000, 0), 'P': (400, 500), 'Q': (600, 500)},
                {'N1': ('A', 'B'), 'N2': ('B', 'C'), 'N3': ('C', 'D'), 'N4': ('D', 'A'), 'F': ('P', 'Q')},
                rooms={'R': (200, 200)}, thickness=20)
        result, _, _ = check(json.dumps(d).encode())
        self.assertTrue(result['valid'], result)
        r = result['derived']['rooms']['R']
        self.assertEqual(r['outer'], [[10, 10], [990, 10], [990, 990], [10, 990]])
        self.assertEqual(r['holes'], [[[400, 490], [400, 510], [600, 510], [600, 490]]])
        self.assertEqual(r['area'], str(980 * 980 - 200 * 20))

    def test_separator_splits_a_room(self):
        d = doc({'A': (0, 0), 'B': (0, 1000), 'C': (1000, 1000), 'D': (1000, 0), 'M': (500, 0), 'N': (500, 1000)},
                {'W1': ('A', 'B'), 'W2': ('B', 'N'), 'W3': ('N', 'C'), 'W4': ('C', 'D'), 'W5': ('D', 'M'), 'W6': ('M', 'A')},
                separators={'S': ('M', 'N')}, rooms={'R1': (250, 500), 'R2': (750, 500)}, thickness=20)
        result, _, _ = check(json.dumps(d).encode())
        self.assertTrue(result['valid'], result)
        self.assertEqual(result['derived']['rooms']['R1']['outer'], [[10, 10], [500, 10], [500, 990], [10, 990]])


if __name__ == '__main__':
    unittest.main()

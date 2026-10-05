"""Roofs (Core 0.3, chapter 16): the eave outline, the class whose surface is derived, the rise distance and
faces of an equal-pitch roof, and the sweep that finds them checked against the pointwise definition (16.4.3)
on random rectilinear footprints."""

import json
import random
import unittest
from collections import Counter
from fractions import Fraction

from tools.oracle import canon, plane, roofs
from tools.oracle.validate import READER_03, check

SIX = {'rise': 6, 'run': 12}


class _Doc:
    def __init__(self, roof, height=0):
        self.levels = {'L1': {'elevation': 0, 'height': height}}
        self.roofs = {'R': roof}


def derive(roof):
    return roofs.derive(_Doc(roof))['roofs']['R']


def roof(fp, **members):
    return {'level': 'L1', 'footprint': [list(p) for p in fp], **members}


def blob(rng):
    """A random rectilinear polygon with no hole and no pinch, or None: the union of grid cells grown at random."""
    nx, ny = rng.randint(2, 5), rng.randint(2, 5)
    xs, ys = sorted(rng.sample(range(40), nx + 1)), sorted(rng.sample(range(40), ny + 1))
    cells = {(rng.randrange(nx), rng.randrange(ny))}
    for _ in range(rng.randint(1, nx * ny)):
        c = rng.choice(sorted(cells))
        d = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        m = (c[0] + d[0], c[1] + d[1])
        if 0 <= m[0] < nx and 0 <= m[1] < ny:
            cells.add(m)
    count = Counter()
    for i, j in cells:
        q = [(xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])]
        for k in range(4):
            count[(q[k], q[(k + 1) % 4])] += 1
    nxt = {}
    for (a, b) in count:
        if not count.get((b, a)):
            nxt.setdefault(a, []).append(b)
    if any(len(v) > 1 for v in nxt.values()):
        return None
    start = next(iter(nxt))
    ring, cur = [start], nxt[start][0]
    while cur != start:
        ring.append(cur)
        cur = nxt[cur][0]
    if len(ring) != len(nxt):
        return None
    changed = True
    while changed:
        changed = False
        for i in range(len(ring)):
            a, b, c = ring[i - 1], ring[i], ring[(i + 1) % len(ring)]
            if plane.cross(plane.sub(b, a), plane.sub(c, b)) == 0:
                ring.pop(i)
                changed = True
                break
    return ring


class EaveOutline(unittest.TestCase):
    def test_rectilinear_overhangs_are_exact(self):
        r = roof([(0, 0), (10, 0), (10, 4), (0, 4)], overhang=1, edges={'0': {'overhang': 3}})
        self.assertEqual(roofs.eave_outline(r), [(-1, -3), (11, -3), (11, 5), (-1, 5)])

    def test_clockwise_footprint_moves_out(self):
        r = roof([(0, 0), (0, 4), (10, 4), (10, 0)], overhang=1)
        self.assertEqual(roofs.eave_outline(r), [(-1, -1), (-1, 5), (11, 5), (11, -1)])

    def test_oblique_edges_round_once(self):
        r = roof([(0, 0), (4, 0), (4, 3), (2, 4), (0, 3)], overhang=1000)
        apex = roofs.eave_outline(r)[3]
        self.assertEqual(apex, (2, round(4 + 1000 * 5 ** 0.5 / 2)))  # 500 * sqrt(5) is far from a tie

    def test_an_edge_that_runs_backwards_does_not_fit(self):
        notch = [(0, 0), (20, 0), (20, 10), (11, 10), (11, 6), (9, 6), (9, 10), (0, 10)]
        self.assertIsNotNone(roofs.eave_outline(roof(notch, overhang=0)))
        self.assertIsNone(roofs.eave_outline(roof(notch, overhang=1)))


class Surfaces(unittest.TestCase):
    def test_hip_rectangle(self):
        s = derive(roof([(0, 0), (10, 0), (10, 4), (0, 4)], pitch={'rise': 1, 'run': 1}))['surface']
        self.assertEqual(s['high'], 2)
        self.assertEqual([(x['kind'], x['from'], x['to']) for x in s['lines'] if x['kind'] == 'ridge'],
                         [('ridge', [2, 2, 2], [8, 2, 2])])

    def test_rise_distance_is_the_chebyshev_distance_to_the_nearest_sloped_edge(self):
        o = roofs.Outline([(0, 0), (10, 0), (10, 4), (4, 4), (4, 10), (0, 10)], ['sloped'] * 6)
        segs = [roofs._seg(o, j) for j in range(6)]
        h = lambda x, y: roofs.rise_distance((roofs._k(x), roofs._k(y)), segs)[0]
        self.assertEqual(h(2, 2), 2)
        self.assertEqual(h(Fraction(5), Fraction(3)), 1)
        self.assertEqual(h(3, 3), 1)              # the reflex corner (4, 4) is 1 away in both axes
        self.assertEqual(h(Fraction(7, 2), Fraction(7, 2)), Fraction(1, 2))

    def test_gable_and_shed(self):
        g = derive(roof([(0, 0), (10, 0), (10, 4), (0, 4)], pitch={'rise': 1, 'run': 1},
                        edges={'1': {'gable': True}, '3': {'gable': True}}))
        self.assertEqual(g['kind'], 'gable')
        self.assertEqual([x['polygon'] for x in g['surface']['gables']],
                         [[[10, 0, 0], [10, 4, 0], [10, 2, 2]], [[0, 4, 0], [0, 0, 0], [0, 2, 2]]])
        s = derive(roof([(0, 0), (10, 0), (10, 4), (0, 4)], pitch={'rise': 1, 'run': 2},
                        edges={str(i): {'gable': True} for i in (1, 2, 3)}))
        self.assertEqual((s['kind'], s['surface']['high']), ('shed', 2))

    def test_what_is_not_derived(self):
        rect = [(0, 0), (10, 0), (10, 4), (0, 4)]
        mixed = roof(rect, pitch=SIX, edges={'0': {'pitch': {'rise': 1, 'run': 1}}})
        oblique = roof([(0, 0), (10, 0), (12, 4), (0, 4)], pitch=SIX)
        adjacent = roof(rect, pitch=SIX, edges={'1': {'gable': True}, '2': {'gable': True}})
        for r in (mixed, oblique, adjacent):
            self.assertIsNone(derive(r)['surface'])
        ratio = roof(rect, pitch=SIX, edges={'0': {'pitch': {'rise': 1, 'run': 2}}})
        self.assertIsNotNone(derive(ratio)['surface'])


class Sweep(unittest.TestCase):
    def test_random_rectilinear_roofs(self):
        """The sweep's faces are labelled by 16.4.3 at every trapezoid (an assertion inside skeleton()); here, they
        also tile the outline exactly, each counter-clockwise, and the lines join nodes of the faces."""
        rng = random.Random(7)
        derived = 0
        for _ in range(120):
            fp = blob(rng)
            if fp is None:
                continue
            fp = [(2 * x, 2 * y) for x, y in fp]           # even coordinates: every node is an integer point
            r = roof(fp, pitch={'rise': rng.randint(1, 12), 'run': 12})
            edges = {}
            for i in range(len(fp)):
                if rng.random() < 0.15:
                    edges[str(i)] = {'gable': True}
                if rng.random() < 0.3:
                    edges.setdefault(str(i), {})['overhang'] = rng.randint(0, 3)
            if edges:
                r['edges'] = edges
            doc = _Doc(r)
            if roofs.invariants(doc, lambda c, e: c):
                continue
            v = derive(r)
            if v['surface'] is None:
                continue
            derived += 1
            outline = [tuple(p) for p in v['outline']]
            faces = v['surface']['faces']
            self.assertEqual(sum(plane.area2([tuple(p[:2]) for p in f['polygon']]) for f in faces),
                             plane.area2(outline))
            for f in faces:
                self.assertGreater(plane.area2([tuple(p[:2]) for p in f['polygon']]), 0)
            corners = {tuple(p) for f in faces for p in f['polygon']}
            for line in v['surface']['lines']:
                self.assertIn(tuple(line['from']), corners)
                self.assertIn(tuple(line['to']), corners)
        self.assertGreater(derived, 30)


class Document(unittest.TestCase):
    def doc(self, **roof_members):
        d = {'floorspec': '0.3', 'project': {'name': 'x'}, 'buildings': {'B1': {}},
             'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': 1000}},
             'roofs': {'RF1': roof([(0, 0), (100, 0), (100, 40), (0, 40)], **roof_members)}}
        return check(json.dumps(d).encode(), READER_03)

    def test_canonical_form_omits_constant_defaults(self):
        r, c, _ = self.doc(pitch=SIX, overhang=0, edges={'0': {'gable': False}, '1': {}})
        self.assertTrue(r['valid'])
        self.assertEqual(set(json.loads(c)['roofs']['RF1']), {'level', 'footprint', 'pitch'})

    def test_invariants_and_lint(self):
        codes = lambda r: [x['code'] for x in r[0]['diagnostics']]
        self.assertEqual(codes(self.doc(pitch=SIX, edges={'9': {}})), ['FS-INV-801'])
        self.assertEqual(codes(self.doc(edges={'0': {'gable': True}})), ['FS-INV-802'])
        self.assertEqual(codes(self.doc(pitch=SIX, edges={str(i): {'gable': True} for i in range(4)})), ['FS-INV-803'])
        self.assertEqual(codes(self.doc(pitch=SIX, edges={'0': {'pitch': {'rise': 1, 'run': 1}}})), ['FS-LINT-015'])

    def test_roofs_is_a_collection(self):
        self.assertIn('roofs', canon.COLLECTIONS)


if __name__ == '__main__':
    unittest.main()

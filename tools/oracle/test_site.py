"""FS_site's oracle: the surface's triangulation against an independent brute force of the Delaunay faces
(spec.md 3.2), exact cut and fill on ground checked by hand (4.2), the setback distance test (2.3) and the
derived values of the garden on its slope (chapter 7)."""

import itertools
import json
import random
import unittest
from fractions import Fraction
from functools import cmp_to_key

from tools.oracle.derive import Doc
from tools.oracle.ext import official, site
from tools.oracle.ext.common import Context
from tools.oracle.ext_author import FT, SITE, entry, site_house
from tools.oracle.validate import check, ext_reader


def ctx(d):
    return Context(Doc(d), site.NAME, site.SEVERITY)


def brute(P):
    """3.2 read literally: every circle through three positions with none strictly inside gives the face of all the
    positions on it; each face fanned from its least vertex."""
    faces = set()
    for a, b, c in itertools.combinations(range(len(P)), 3):
        o = site.orient(P[a], P[b], P[c])
        if o == 0:
            continue
        if o < 0:
            b, c = c, b
        ins = [site.incircle(P[a], P[b], P[c], P[d]) for d in range(len(P))]
        if any(x > 0 for x in ins):
            continue
        faces.add(frozenset(d for d in range(len(P)) if ins[d] == 0))
    out = []
    for S in faces:
        v0 = min(S, key=lambda i: P[i])
        rest = sorted((v for v in S if v != v0), key=cmp_to_key(lambda i, j: -site.orient(P[v0], P[i], P[j])))
        out += [site._norm((v0, rest[i], rest[i + 1])) for i in range(len(rest) - 1)]
    return sorted(out)


class Surface(unittest.TestCase):
    def test_matches_the_definition_on_grids_full_of_cocircular_points(self):
        rnd = random.Random(15)
        n = 0
        for _ in range(300):
            R = rnd.choice([3, 5, 8, 1000])
            P = sorted({(rnd.randint(0, R), rnd.randint(0, R)) for _ in range(rnd.randint(3, 16))})
            T = site.triangulate(P)
            if T is None:
                self.assertTrue(len(P) < 3 or all(site.orient(P[0], P[1], p) == 0 for p in P))
                continue
            self.assertEqual(T, brute(P), P)
            n += 1
        self.assertGreater(n, 250)

    def test_a_square_is_divided_from_its_least_corner(self):
        self.assertEqual(site.triangulate([(0, 0), (0, 10), (10, 0), (10, 10)]), [(0, 2, 3), (0, 3, 1)])

    def test_points_on_a_line_make_no_surface(self):
        self.assertIsNone(site.triangulate([(0, 0), (1, 1), (5, 5)]))
        self.assertIsNone(site.triangulate([(0, 0), (1, 1)]))

    def test_a_collinear_start_is_fanned(self):
        T = site.triangulate([(0, 0), (0, 1), (0, 2), (0, 3), (5, 1)])
        self.assertEqual(len(T), 3)


class Volumes(unittest.TestCase):
    PLANE = [(0, 0, 0), (100, 0, 0), (100, 100, 10), (0, 100, 10)]   # z = y / 10

    def measure(self, ring, e):
        pts = sorted(self.PLANE)
        tris = site.triangulate([(x, y) for x, y, _ in pts])
        return site.measure(ring, e, pts, tris)

    def test_a_pad_across_the_zero_line(self):
        cut, fill, low, high = self.measure([(10, 30), (30, 30), (30, 70), (10, 70)], 5)
        # z - 5 = (y - 50) / 10 over 20 x 40: each half 20 * 20^2 / 20 = 400
        self.assertEqual((cut, fill, low, high), (400, 400, 3, 7))

    def test_a_non_convex_outline_keeps_its_winding(self):
        ring = [(0, 0), (40, 0), (40, 60), (30, 60), (30, 10), (10, 10), (10, 60), (0, 60)]   # a U, opening north
        cut, fill, _, _ = self.measure(ring, 0)
        exact = Fraction(0)
        for x0, x1, y0, y1 in ((0, 40, 0, 10), (0, 10, 10, 60), (30, 40, 10, 60)):
            exact += Fraction(x1 - x0) * Fraction(y1 * y1 - y0 * y0, 20)
        self.assertEqual((cut, fill), (exact, 0))

    def test_beyond_the_hull_nothing_is_measured(self):
        self.assertEqual(self.measure([(200, 200), (300, 200), (300, 300)], 0), (0, 0, None, None))

    def test_volumes_round_ties_to_even(self):
        self.assertEqual(site.round_half_even(Fraction(5, 2)), 2)
        self.assertEqual(site.round_half_even(Fraction(7, 2)), 4)


class Setbacks(unittest.TestCase):
    def test_nearer_than_a_segment_not_its_line(self):
        a, b = (0, 0), (10, 0)
        self.assertTrue(site.nearer_than((5, 3), a, b, 4))
        self.assertFalse(site.nearer_than((5, 4), a, b, 4))         # exactly the setback: clear
        self.assertFalse(site.nearer_than((-10, 1), a, b, 4))       # beyond the end: measured to it
        self.assertTrue(site.nearer_than((13, 2), a, b, 4))         # sqrt(13) from the end

    def test_edge_kinds(self):
        self.assertEqual(site.edge_kinds(4, {'street': [0]}), ['front', 'side', 'rear', 'side'])
        self.assertEqual(site.edge_kinds(5, {'street': [0]}), ['front', 'side', 'rear', 'rear', 'side'])
        self.assertEqual(site.edge_kinds(3, {'street': [1]}), ['side', 'front', 'side'])
        self.assertEqual(site.edge_kinds(4, None), [None] * 4)


class Garden(unittest.TestCase):
    def test_the_garden_on_its_slope(self):
        d = site_house()
        data = json.dumps(d).encode('utf-8')
        r, _, _ = check(data, ext_reader(data), json.dumps([entry(SITE)]).encode('utf-8'), official.implemented(SITE))
        self.assertTrue(r['valid'], r['diagnostics'])
        x = r['derived']['extensions'][SITE]
        self.assertEqual(x['lot']['area'], str(70 * 70 * FT * FT))
        self.assertEqual(len(x['surface']['points']), 11)
        self.assertEqual(int(x['fill']), int(x['grading']['GP1']['fill']) + int(x['grading']['S1']['fill']))

    def test_records_share_the_space_of_ids(self):
        d = site_house()
        d['extensions'][SITE]['spots']['W1'] = d['extensions'][SITE]['spots'].pop('SP5')
        self.assertEqual([x['elements'] for x in site.invariants(ctx(d))], [['W1']])


if __name__ == '__main__':
    unittest.main()

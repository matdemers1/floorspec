"""Tests of the oracle's arc edges (Core 0.4, chapter 21): the polyline by iterated snap rounding, its bounds, and
its stations. The fuzz cases are the tripwire of FLR-R-004: a polyline that crossed or touched itself, or turned
the wrong way, would break planarity after rounding."""

import math
import random
import unittest
from fractions import Fraction

from tools.oracle import arcs, plane

MM = 1280


def centre(S, E, h):
    """The exact circle of an arc, in floats - for bounds only."""
    dx, dy = E[0] - S[0], E[1] - S[1]
    L = math.hypot(dx, dy)
    R = float(arcs.radius(S, E, h))
    mx, my = (S[0] + E[0]) / 2, (S[1] + E[1]) / 2
    k = (h - math.copysign(R, h)) / L
    return (mx - dy * k, my + dx * k), R


class Polyline(unittest.TestCase):
    def test_flat_arc_is_its_chord(self):
        self.assertEqual(arcs.polyline((0, 0), (5000, 0), 1280), ((0, 0), (5000, 0)))
        self.assertEqual(arcs.polyline((0, 0), (5000, 0), -1280), ((0, 0), (5000, 0)))

    def test_semicircle_midpoint(self):
        p = arcs.polyline((0, 4000 * MM), (5000 * MM, 4000 * MM), 2500 * MM)
        self.assertIn((2500 * MM, 6500 * MM), p)
        self.assertEqual(arcs.radius((0, 0), (5000 * MM, 0), 2500 * MM), 2500 * MM)

    def test_sign_bulges_left_or_right(self):
        up = arcs.polyline((0, 0), (5000 * MM, 0), 1000 * MM)
        down = arcs.polyline((0, 0), (5000 * MM, 0), -1000 * MM)
        self.assertTrue(all(y > 0 for _, y in up[1:-1]))
        self.assertEqual(down, tuple((x, -y) for x, y in up))

    def test_one_halving(self):
        self.assertEqual(arcs.polyline((0, 0), (3000 * MM, 0), 1281), ((0, 0), (1500 * MM, 1281), (3000 * MM, 0)))

    def test_round_sqrt(self):
        for m in list(range(0, 5000)) + [10 ** 30 + k for k in range(-50, 50)]:
            self.assertEqual(arcs.round_sqrt(m), (math.isqrt(4 * m) + 1) // 2)     # floor(sqrt(m) + 1/2)

    def test_reversed_edge_has_the_reversed_polyline(self):
        rnd = random.Random(7)
        for _ in range(300):
            S = (rnd.randint(-10 ** 7, 10 ** 7), rnd.randint(-10 ** 7, 10 ** 7))
            E = (rnd.randint(-10 ** 7, 10 ** 7), rnd.randint(-10 ** 7, 10 ** 7))
            if S == E:
                continue
            D = (E[0] - S[0]) ** 2 + (E[1] - S[1]) ** 2
            h = rnd.randint(1, math.isqrt(D // 4)) * rnd.choice((1, -1))
            self.assertEqual(arcs.polyline(E, S, -h), tuple(reversed(arcs.polyline(S, E, h))))

    def test_fuzz_simple_convex_and_close(self):
        """Every polyline is simple, turns one way at every vertex, keeps every vertex within a few base units of
        its circle, every segment within the tolerance of it, and every segment long."""
        rnd = random.Random(2026)
        cases = 0
        for _ in range(400):
            scale = rnd.choice((10 ** 4, 10 ** 6, 10 ** 7, 10 ** 8))
            S = (rnd.randint(-scale, scale), rnd.randint(-scale, scale))
            E = (rnd.randint(-scale, scale), rnd.randint(-scale, scale))
            D = (E[0] - S[0]) ** 2 + (E[1] - S[1]) ** 2
            if D < 4 * 1281 * 1281:
                continue
            hmax = math.isqrt(D // 4)
            h = rnd.choice((rnd.randint(1281, hmax), hmax, 1281 + rnd.randint(0, 100))) * rnd.choice((1, -1))
            p = arcs.polyline(S, E, h)
            cases += 1
            self.assertEqual((p[0], p[-1]), (S, E))
            self.assertTrue(len(set(p)) == len(p))
            turns = {plane.orient(p[i - 1], p[i], p[i + 1]) for i in range(1, len(p) - 1)}
            self.assertEqual(turns, {-1 if h > 0 else 1} if len(p) > 2 else set())
            for i in range(len(p) - 1):                          # no two segments that are not neighbours touch
                for k in range(i + 2, len(p) - 1):
                    self.assertFalse(plane.segments_touch(p[i], p[i + 1], p[k], p[k + 1]))
            (cx, cy), R = centre(S, E, h)
            depth = arcs.depth_of(S, E, h)
            for x, y in p:
                self.assertLess(abs(math.hypot(x - cx, y - cy) - R), 1 + depth)
            for a, b in zip(p, p[1:]):                            # the arc between two vertices bulges at most tau
                c = math.dist(a, b)
                self.assertLess(R - math.sqrt(max(R * R - c * c / 4, 0)), arcs.TAU + 2 + depth)
                self.assertGreater(c, 1000)
        self.assertGreater(cases, 300)


class Stations(unittest.TestCase):
    def test_points_at_distances(self):
        p = ((0, 0), (3000, 4000), (3000, 10000))
        self.assertEqual(arcs.lengths(p), [5000, 6000])
        self.assertEqual(arcs.length(p), 11000)
        self.assertEqual(arcs.point_at(p, 2500), (Fraction(1500), Fraction(2000)))
        self.assertEqual(arcs.segment_at(p, 5000), (1, 5000))     # half-open: a vertex starts the next segment
        self.assertEqual(arcs.segment_at(p, 11000), (1, 5000))    # the end is on the last
        self.assertIsNone(arcs.segment_at(p, 11001))
        self.assertEqual(arcs.point_at(p, 11000), (3000, 10000))


if __name__ == '__main__':
    unittest.main()

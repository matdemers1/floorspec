"""The weighted straight skeleton (Core 0.4, 16.4.3 to 16.4.6): checked against Core 0.3's pointwise roofs on random
rectilinear equal-pitch outlines, against the lower envelope of the edges' planes on convex outlines at mixed pitches,
for its own invariants on random outlines at mixed pitches with gables, for independence from where the footprint
starts, and on the cases it resolves and the ones it leaves underived."""

import math
import random
import unittest
from fractions import Fraction as F
from math import isqrt

from tools.oracle import plane, roofs, skeleton as sk
from tools.oracle.test_roofs import blob

SIX = {'rise': 6, 'run': 12}


class _Doc:
    def __init__(self, roof):
        self.levels = {'L1': {'elevation': 0, 'height': 0}}
        self.roofs = {'R': roof}


def roof(fp, **members):
    return {'level': 'L1', 'footprint': [list(p) for p in fp], **members}


def derive(r, v04=True):
    return roofs.derive(_Doc(r), v04)['roofs']['R']


def usable(r):
    return (not roofs.collinear_vertex(roofs.footprint(r)) and roofs.eave_outline(r) is not None
            and roofs.kinds(r).count('sloped') >= 2)


def faces_of(r):
    o = roofs.Outline(roofs.eave_outline(r), roofs.kinds(r))
    return o, roofs.weighted_faces(r, o)


class Skeleton(unittest.TestCase):
    def test_equal_pitches_are_0_3s_roofs(self):
        """On every roof Core 0.3 derives, 0.4 derives the same values (16.4.3, the note): lines with equal rounded
        ends, which 0.3 left unordered, are compared in 0.4's order."""
        rng = random.Random(7)
        n = 0
        while n < 60:
            fp = blob(rng)
            if fp is None:
                continue
            edges = {str(k): {'gable': True} for k in range(len(fp)) if rng.random() < 0.15}
            r = roof(fp, pitch=SIX, edges=edges)
            if not usable(r):
                continue
            a = derive(r, False)
            if a['surface'] is None:
                continue
            a['surface']['lines'].sort(key=lambda x: (x['from'], x['to'], x['kind']))
            self.assertEqual(derive(r), a, fp)
            n += 1

    def test_convex_roofs_are_the_lower_envelope(self):
        """On a convex outline every point of the roof is in the lowest of the edges' planes, at any pitches, on
        edges along axes and Pythagorean directions."""
        rng = random.Random(5)
        dirs = sorted([(1, 0), (4, 3), (3, 4), (0, 1), (-3, 4), (-4, 3), (-1, 0), (-4, -3), (-3, -4), (0, -1), (3, -4),
                       (4, -3), (12, 5), (5, 12), (-5, 12), (-12, 5), (-12, -5), (-5, -12), (5, -12), (12, -5)],
                      key=lambda d: math.atan2(d[1], d[0]))
        checked = 0
        for _ in range(3000):
            ds = sorted(rng.sample(dirs, rng.randint(3, 7)), key=lambda d: math.atan2(d[1], d[0]))
            lens = [rng.randint(1, 6) for _ in ds]
            d1, d2 = ds[-2], ds[-1]
            rx = -sum(l * d[0] for l, d in zip(lens[:-2], ds[:-2]))
            ry = -sum(l * d[1] for l, d in zip(lens[:-2], ds[:-2]))
            det = d1[0] * d2[1] - d1[1] * d2[0]
            if det == 0:
                continue
            a, b = F(rx * d2[1] - ry * d2[0], det), F(d1[0] * ry - d1[1] * rx, det)
            if a <= 0 or b <= 0 or a.denominator != 1 or b.denominator != 1:
                continue
            lens[-2:] = [int(a), int(b)]
            ring = [(0, 0)]
            for l, d in zip(lens, ds):
                ring.append((ring[-1][0] + 10 * l * d[0], ring[-1][1] + 10 * l * d[1]))
            ring = ring[:-1]
            m = len(ring)
            if any(plane.cross(plane.sub(ring[i], ring[i - 1]), plane.sub(ring[(i + 1) % m], ring[i])) == 0
                   for i in range(m)):
                continue
            pit = [F(rng.choice([2, 3, 4, 6, 8, 12]), 12) for _ in ring]

            def z(j, p):
                a, b = ring[j], ring[(j + 1) % m]
                nn = (-(b[1] - a[1]), b[0] - a[0])
                return pit[j] * (plane.dot(nn, p) - plane.dot(nn, a)) / isqrt(plane.dot(nn, nn))
            for j, rs in sk.skeleton(ring, ['sloped'] * m, pit).items():
                for rg in rs:
                    c = (sum(p[0] for p in rg) / len(rg), sum(p[1] for p in rg) / len(rg))
                    self.assertEqual(z(j, c), min(z(i, c) for i in range(m)))
            checked += 1
            if checked == 40:
                break
        self.assertEqual(checked, 40)

    def test_mixed_pitches_with_gables_keep_their_invariants(self):
        """The faces cover the outline without overlapping (asserted in skeleton()), meet at one elevation at every
        point they share (asserted in the derivation), and have no holes; or the roof is underived (16.4.6)."""
        rng = random.Random(3)
        done = derived = 0
        while done < 150:
            fp = blob(rng)
            if fp is None:
                continue
            edges = {}
            for k in range(len(fp)):
                x = rng.random()
                if x < 0.15:
                    edges[str(k)] = {'gable': True}
                elif x < 0.6:
                    edges[str(k)] = {'pitch': {'rise': rng.choice([3, 4, 6, 8, 12, 18]), 'run': 12}}
            r = roof(fp, pitch=SIX, edges=edges)
            if not usable(r):
                continue
            done += 1
            v = derive(r)
            if v['surface'] is not None:
                derived += 1
                self.assertGreaterEqual(min(p[2] for f in v['surface']['faces'] for p in f['polygon']), 0)
        self.assertGreater(derived, 100)

    def test_where_the_footprint_starts_does_not_matter(self):
        """Every event at an elevation is resolved at once (16.4.4): numbering the footprint from another vertex
        renumbers the faces and changes nothing else."""
        rng = random.Random(11)
        n = 0
        while n < 40:
            fp = blob(rng)
            if fp is None:
                continue
            pitches = [{'rise': rng.choice([3, 6, 12]), 'run': 12} for _ in fp]
            r = roof(fp, edges={str(k): {'pitch': p} for k, p in enumerate(pitches)})
            if not usable(r) or derive(r)['surface'] is None:
                continue
            k = rng.randrange(1, len(fp))
            m = len(fp)
            s = roof(fp[k:] + fp[:k], edges={str((i - k) % m): {'pitch': p} for i, p in enumerate(pitches)})
            a, b = derive(r)['surface'], derive(s)['surface']
            self.assertEqual(sorted((f['polygon'], f['area']) for f in a['faces']),
                             sorted((f['polygon'], f['area']) for f in b['faces']))
            self.assertEqual({(f['edge'] - k) % m for f in a['faces']}, {f['edge'] for f in b['faces']})
            self.assertEqual(a['lines'], b['lines'])
            self.assertEqual(a['high'], b['high'])
            n += 1

    def test_saltbox(self):
        """A 24-deep house, front at 12 in 12, back at 6, short ends gables: the ridge is 8 from the front, 8 up."""
        v = derive(roof([(0, 0), (32, 0), (32, 24), (0, 24)], pitch=SIX,
                        edges={'0': {'pitch': {'rise': 12, 'run': 12}}, '1': {'gable': True}, '3': {'gable': True}}))
        s = v['surface']
        self.assertEqual(s['lines'], [{'kind': 'ridge', 'from': [0, 8, 8], 'to': [32, 8, 8]}])
        self.assertEqual([g['polygon'] for g in s['gables']], [[[32, 0, 0], [32, 24, 0], [32, 8, 8]],
                                                                [[0, 24, 0], [0, 0, 0], [0, 8, 8]]])

    def test_a_faster_edge_overtakes_a_slower_one(self):
        """16.4.4: on a stepped eave the shallower edge catches the steeper one and continues over its run; the
        steeper face ends in a level break."""
        v = derive(roof([(0, 0), (30, 0), (30, 3), (90, 3), (90, 60), (0, 60)], pitch={'rise': 12, 'run': 12},
                        edges={'0': {'pitch': {'rise': 3, 'run': 12}}}))
        self.assertIn({'kind': 'break', 'from': [29, 4, 1], 'to': [89, 4, 1]}, v['surface']['lines'])

    def test_events_together(self):
        """A rectangle whose four planes reach its centre at one elevation: four edges vanish at once."""
        v = derive(roof([(0, 0), (24, 0), (24, 12), (0, 12)], pitch=SIX, edges={'0': {'pitch': {'rise': 12, 'run': 12}},
                                                                                  '2': {'pitch': {'rise': 12, 'run': 12}}}))
        self.assertEqual([x['kind'] for x in v['surface']['lines']], ['hip'] * 4)
        self.assertEqual(v['surface']['high'], 6)

    def test_what_is_not_derived(self):
        """16.4.6: an oblique sloped edge of irrational length; a gable with a reflex end beside a sloped edge; a
        gable the wavefront passes the end of after an event."""
        self.assertIsNone(derive(roof([(0, 0), (26, 0), (30, 4), (30, 20), (0, 20)], pitch=SIX))['surface'])
        u = [(0, 0), (36, 0), (36, 30), (24, 30), (24, 12), (12, 12), (12, 30), (0, 30)]
        self.assertIsNone(derive(roof(u, pitch=SIX, edges={'5': {'gable': True}}))['surface'])
        late = [(39, 12), (39, 34), (21, 34), (21, 21), (7, 21), (7, 34), (3, 34), (3, 12)]
        edges = {**{str(i): {'gable': True} for i in (1, 2, 3, 4)}, '5': {'pitch': {'rise': 3, 'run': 12}},
                 '6': {'pitch': {'rise': 12, 'run': 12}}}
        o = roofs.Outline(roofs.eave_outline(roof(late, pitch=SIX, edges=edges)), roofs.kinds(roof(late, edges=edges, pitch=SIX)))
        pitches = [roofs.pitch_of(roof(late, pitch=SIX, edges=edges), o.index[j]) if o.kind[j] == 'sloped' else None
                   for j in range(o.n)]
        polys = [sk.eave_edges(o.ring, o.kind, pitches)]
        sk.check(polys, F(0))                                 # sound at t = 0 ...
        with self.assertRaises(sk.Unsupported):
            sk.skeleton(o.ring, o.kind, pitches)              # ... and passed at 13/4

    def test_lint(self):
        """FS-LINT-015 for 0.3's mixed-pitch roof under 0.3, and none under 0.4."""
        class Doc(_Doc):
            pass
        d = Doc(roof([(0, 0), (40, 0), (40, 30), (0, 30)], pitch=SIX, edges={'0': {'pitch': {'rise': 12, 'run': 12}}}))

        def diag(code, els):
            return code
        self.assertEqual(roofs.lints(d, diag, False), ['FS-LINT-015'])
        self.assertEqual(roofs.lints(d, diag, True), [])


if __name__ == '__main__':
    unittest.main()

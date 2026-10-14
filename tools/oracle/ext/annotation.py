"""FS_annotation 0.1.0 (registry/FS_annotation/spec.md): its invariants, lints and derived values,
written from the extension's specification alone.

FS_annotation adds no kind of element and requires no other extension. It reads, of FS_lighting's and
FS_views's data, only the IDs of their scenes and views, as they are (spec.md 1.3).

A dimension string's lengths (2.3) are exact: each anchor's position along the string, times |d|, is
a + b*sqrt(m) with rational a, b and m the squared length of the wall it measures (or 1), so a length
|p' - p| = |s' - s| / |d| lives in Q(sqrt(m), sqrt(m'), sqrt(|d|^2)). Num below is an element of such a
field, on the basis of the products of its generators' square roots, with an exact sign by repeated
squaring - a small, independent cousin of tools/oracle/surd.py, which stops at two radicands."""

from __future__ import annotations

import math
from fractions import Fraction

from .. import arcs
from ..derive import opening_points
from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_annotation', '0.1.0', 'ANNO'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'annotation')
SEVERITY = {'FS-ANNO-LINT-001': 'warning', 'FS-ANNO-LINT-002': 'warning', 'FS-ANNO-LINT-003': 'warning',
            'FS-ANNO-LINT-004': 'warning'}
LGHT, VIEW = 'FS_lighting', 'FS_views'


# ------------------------------------------------------------------------------ exact numbers

def _sgn(x) -> int:
    return (x > 0) - (x < 0)


class Num:
    """sum over masks S of c_S * prod_{i in S} sqrt(gens[i]), with rational c_S and integer gens >= 0."""

    __slots__ = ('gens', 'c')

    def __init__(self, gens, c):
        self.gens = tuple(gens)
        self.c = {m: Fraction(v) for m, v in c.items() if v != 0}

    @staticmethod
    def of(gens, a=0, terms=()):
        """a + sum(b * sqrt(gens[i])) for (i, b) in terms."""
        c = {0: Fraction(a)}
        for i, b in terms:
            c[1 << i] = c.get(1 << i, Fraction(0)) + Fraction(b)
        return Num(gens, c)

    def __add__(self, o):
        c = dict(self.c)
        for m, v in o.c.items():
            c[m] = c.get(m, Fraction(0)) + v
        return Num(self.gens, c)

    def __neg__(self):
        return Num(self.gens, {m: -v for m, v in self.c.items()})

    def __sub__(self, o):
        return self + (-o)

    def __mul__(self, o):
        out = {}
        for m1, v1 in self.c.items():
            for m2, v2 in o.c.items():
                f = v1 * v2
                for i, g in enumerate(self.gens):
                    if m1 & m2 & (1 << i):
                        f *= g
                out[m1 ^ m2] = out.get(m1 ^ m2, Fraction(0)) + f
        return Num(self.gens, out)

    def scale(self, q):
        return Num(self.gens, {m: v * q for m, v in self.c.items()})

    def sign(self, k=None) -> int:
        """Exact: x = u + v*sqrt(g_k) with u, v over the first k - 1 generators."""
        k = len(self.gens) if k is None else k
        if k == 0:
            return _sgn(self.c.get(0, Fraction(0)))
        bit = 1 << (k - 1)
        u = Num(self.gens, {m: v for m, v in self.c.items() if not m & bit})
        v = Num(self.gens, {m ^ bit: x for m, x in self.c.items() if m & bit})
        su, sv = u.sign(k - 1), v.sign(k - 1)
        if sv == 0:
            return su
        if su == 0 or su == sv:
            return sv
        t = u * u - (v * v).scale(self.gens[k - 1])
        return su * t.sign(k - 1)

    def __float__(self):
        return 0.0 + sum(float(v) * math.prod(math.sqrt(g) for i, g in enumerate(self.gens) if m & (1 << i))
                   for m, v in self.c.items())

    def floor(self) -> int:
        k = math.floor(float(self))
        while (self - Num.of(self.gens, k)).sign() < 0:
            k -= 1
        while (self - Num.of(self.gens, k + 1)).sign() >= 0:
            k += 1
        return k

    def round(self) -> int:
        """round(): nearest integer, ties to even (Core 2.2), decided exactly."""
        k = self.floor()
        s = (self - Num.of(self.gens, Fraction(2 * k + 1, 2))).sign()
        return k if s < 0 or (s == 0 and k % 2 == 0) else k + 1


# ------------------------------------------------------------------------------ reading

def _dims(ctx: Context) -> dict:
    return ctx.data.get('dimensions', {})


def _notes(ctx: Context) -> dict:
    return ctx.data.get('notes', {})


def _ids_of(ctx: Context, name: str, member: str) -> set:
    data = ctx.d.get('extensions', {}).get(name)
    s = data.get(member) if isinstance(data, dict) else None
    return set(s) if isinstance(s, dict) else set()


def read_as_data(ctx: Context) -> set:
    """1.3: the IDs of extensions.FS_lighting.scenes and extensions.FS_views.views, read as data."""
    return _ids_of(ctx, LGHT, 'scenes') | _ids_of(ctx, VIEW, 'views')


# ------------------------------------------------------------------------------ anchors (2.2)

def anchor_level(doc, a):
    """The level of the feature an anchor names, or None when it names none of its kind; True for a point."""
    if 'point' in a:
        return True
    if 'junction' in a:
        j = doc.junctions.get(a['junction'])
        return None if j is None else j['level']
    if 'wall' in a:
        w = doc.walls.get(a['wall'])
        return None if w is None else w['level']
    o = doc.openings.get(a['opening'])
    return None if o is None else doc.walls[o['wall']]['level']


def wall_line(doc, a):
    """(S, e, nu, lam): the line a wall anchor names, nu . (P - S) = lam * |e| (2.2)."""
    w = doc.walls[a['wall']]
    S = doc.junctions[w['start']]['position']
    E = doc.junctions[w['end']]['position']
    e = (E[0] - S[0], E[1] - S[1])
    a_, b_ = doc.offsets(a['wall'])
    lam = {'left': a_, 'right': -b_, 'location': Fraction(0)}[a['face']]
    return S, e, (-e[1], e[0]), lam


def lints_of(doc, dim):
    """(LINT-001, LINT-002) of one dimension string."""
    l1 = l2 = False
    d = dim['direction']
    for a in dim['anchors']:
        lv = anchor_level(doc, a)
        if lv is True:
            continue
        if lv != dim['level']:
            l1 = True
            continue
        if 'wall' in a:
            if arcs.sagitta(doc.walls[a['wall']]) is not None:
                l2 = True
                continue
            _, _, nu, _ = wall_line(doc, a)
            if nu[0] * d[0] + nu[1] * d[1] == 0:
                l2 = True
    return l1, l2


def scaled_position(doc, dim, a):
    """(alpha, beta, m): an anchor's position times |d|, alpha + beta * sqrt(m), exactly (2.3)."""
    d, T = dim['direction'], dim['through']
    N = d[0] * d[0] + d[1] * d[1]
    if 'wall' in a:
        S, e, nu, lam = wall_line(doc, a)
        nd = nu[0] * d[0] + nu[1] * d[1]
        m = e[0] * e[0] + e[1] * e[1]
        nts = nu[0] * (T[0] - S[0]) + nu[1] * (T[1] - S[1])
        # p * |d| = t * |d|^2, t = (lam * sqrt(m) - nu . (T - S)) / (nu . d)
        return Fraction(-N * nts, nd), Fraction(N, nd) * lam, m
    if 'opening' in a:
        s, e = opening_points(doc, a['opening'])
        cx, cy = (s[0] + e[0]) / 2, (s[1] + e[1]) / 2          # Surds of one radicand, or rationals
        v = cx * d[0] + cy * d[1] - (T[0] * d[0] + T[1] * d[1])
        if v.t:
            (m, b), = v.t.items()
            return v.a, b, m
        return v.a, Fraction(0), 1
    P = doc.junctions[a['junction']]['position'] if 'junction' in a else a['point']
    return Fraction((P[0] - T[0]) * d[0] + (P[1] - T[1]) * d[1]), Fraction(0), 1


def gap(dim, x, y) -> Num:
    """|p_y - p_x| as an exact Num: |s_y - s_x| * sqrt(N) / N."""
    d = dim['direction']
    N = d[0] * d[0] + d[1] * d[1]
    gens = (x[2], y[2], N)
    diff = Num.of(gens, y[0] - x[0], [(1, y[1]), (0, -x[1])])
    sgn = diff.sign()
    return (diff * Num.of(gens, 0, [(2, 1)])).scale(Fraction(sgn, N))


def measure(doc, dim):
    """(lengths, total, zero) of a resolved dimension string: its rounded segments and total, and whether
    two consecutive anchors are at the same position (2.3)."""
    pos = [scaled_position(doc, dim, a) for a in dim['anchors']]
    segs = [gap(dim, pos[i], pos[i + 1]) for i in range(len(pos) - 1)]
    zero = any(g.sign() == 0 for g in segs)
    return [g.round() for g in segs], gap(dim, pos[0], pos[-1]).round(), zero


# ------------------------------------------------------------------------------ the rules

def invariants(ctx: Context):
    ds = []
    taken = ctx.space() | read_as_data(ctx)
    levels = ctx.d.get('levels', {})
    dims, notes = _dims(ctx), _notes(ctx)
    for aid, a in list(dims.items()) + list(notes.items()):
        if aid in taken or (a is notes.get(aid) and aid in dims):                         # 1.3.2
            ds.append(ctx.diag('FS-ANNO-INV-001', [aid]))
        if a['level'] not in levels:                                                     # 1.3.3
            ds.append(ctx.diag('FS-ANNO-INV-002', [aid]))
    for did, dim in dims.items():
        if dim['direction'] == [0, 0]:                                                   # 2.1.1
            ds.append(ctx.diag('FS-ANNO-INV-003', [did]))
    return ds


def lints(ctx: Context):
    ds = []
    for did, dim in _dims(ctx).items():
        l1, l2 = lints_of(ctx.doc, dim)
        if l1:
            ds.append(ctx.diag('FS-ANNO-LINT-001', [did]))
        if l2:
            ds.append(ctx.diag('FS-ANNO-LINT-002', [did]))
        if not (l1 or l2) and measure(ctx.doc, dim)[2]:
            ds.append(ctx.diag('FS-ANNO-LINT-003', [did]))
    about = ctx.space() | read_as_data(ctx) | set(_dims(ctx))
    for nid, n in _notes(ctx).items():
        if 'about' in n and n['about'] not in about:                                     # 3.1.1
            ds.append(ctx.diag('FS-ANNO-LINT-004', [nid]))
    return ds


def derive(ctx: Context) -> dict:
    dims = {}
    for did, dim in sorted(_dims(ctx).items()):
        if any(lints_of(ctx.doc, dim)):
            dims[did] = {'level': dim['level'], 'lengths': None, 'total': None}
        else:
            lengths, total, _ = measure(ctx.doc, dim)
            dims[did] = {'level': dim['level'], 'lengths': lengths, 'total': total}
    return {'dimensions': dims,
            'notes': {nid: {'level': n['level'], 'about': n.get('about')} for nid, n in sorted(_notes(ctx).items())}}

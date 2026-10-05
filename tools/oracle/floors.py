"""Floors, ceilings and slabs (Core 0.3, chapter 15): the members' resolution, the exact geometry of
flat, tray and vaulted ceilings, the floor and ceiling invariants FS-INV-701 to FS-INV-703, the
derived `floors`, `ceilings` and `slabs`, and the elevation of a `surface` host (15.6).

Everything is exact and rounded once. A vaulted ceiling's elevation at a plan point P is

    z(P) = E + h - (rise / run) * delta(P)

with delta the distance from the ridge line ("both"), or the signed distance, positive on the side
the ceiling falls to ("left" or "right"); with A, B the ridge points, d = B - A, D = |d|^2 and
c(P) = d x (P - A), the distance is |c| / sqrt(D) and z(P) = E + h - rise * c' * sqrt(D) / (run * D),
one radicand. A tray's centre is the room polygon with every edge moved `border` to its left - into
the room, for the outer ring walked counter-clockwise and for each hole walked clockwise - each
vertex the intersection of its two edges' moved lines (5.5's face lines, with integer radicands),
or, where the two edges are collinear, the vertex moved along their common normal.
"""

from __future__ import annotations

from fractions import Fraction

from . import plane
from .derive import Doc, LevelGraph, degenerate, rpoint
from .surd import Surd

FLAT = {'kind': 'flat'}


# ------------------------------------------------------------------------------ resolution (15.1, 15.2)

def floor_offset(doc: Doc, rid) -> int:
    return doc.rooms[rid].get('floor', {}).get('offset', 0)


def floor_top(doc: Doc, rid) -> int:
    """15.1: the level's elevation plus the room's floor offset."""
    r = doc.rooms[rid]
    return doc.levels[r['level']]['elevation'] + floor_offset(doc, rid)


def floor_thickness(doc: Doc, rid) -> int:
    """15.1: the room's own floor thickness, else its level's floorThickness, else 0 (not declared)."""
    r = doc.rooms[rid]
    t = r.get('floor', {}).get('thickness')
    if t is None:
        t = doc.levels[r['level']].get('floorThickness', 0)
    return t


def ceiling(doc: Doc, rid) -> dict:
    return doc.rooms[rid].get('ceiling', FLAT)


def ceiling_height(doc: Doc, rid) -> int:
    """15.2: the ceiling's own height, else its level's ceilingHeight, else the level's height."""
    lvl = doc.levels[doc.rooms[rid]['level']]
    return ceiling(doc, rid).get('height', lvl.get('ceilingHeight', lvl['height']))


def ceiling_base(doc: Doc, rid) -> int:
    """The elevation of a flat ceiling, a tray's border, or a vault's ridge: E + h."""
    return doc.levels[doc.rooms[rid]['level']]['elevation'] + ceiling_height(doc, rid)


# ------------------------------------------------------------------------------ room polygons

def room_rings(doc: Doc, rid, graph: LevelGraph | None = None):
    """The room polygon of the room's face (6.2), rounded, each ring in its walk order: the outer ring
    counter-clockwise and the holes clockwise, the face on the left of every edge."""
    r = doc.rooms[rid]
    g = graph if graph is not None else LevelGraph(doc, r['level'])
    face = g.face_of(tuple(r['anchor']), g.faces())
    return g.room_polygon(face)


# ------------------------------------------------------------------------------ vaults (15.3)

def _vault(c: dict):
    (ax, ay), (bx, by) = c['ridge']
    dx, dy = bx - ax, by - ay
    return (ax, ay), (dx, dy), dx * dx + dy * dy, Fraction(c['pitch']['rise'], c['pitch']['run'])


def _cross_at(c: dict, p) -> int:
    (ax, ay), (dx, dy), _, _ = _vault(c)
    return dx * (p[1] - ay) - dy * (p[0] - ax)


def _fall(c: dict, cr: int) -> int:
    """The (signed) distance-times-sqrt(D) the ceiling has fallen at a point whose cross is cr: |cr| for
    "both"; cr on the left (positive cr) for "left"; -cr for "right"."""
    slopes = c.get('slopes', 'both')
    if slopes == 'both':
        return abs(cr)
    return cr if slopes == 'left' else -cr


def vault_z(base: int, c: dict, fall: int) -> Surd:
    """E + h - (rise/run) * fall / sqrt(D), exactly."""
    _, _, D, k = _vault(c)
    return Surd(base) + Surd.sqrt(D, -k * fall / D)


def vault_at(doc: Doc, rid, p) -> Surd:
    c = ceiling(doc, rid)
    return vault_z(ceiling_base(doc, rid), c, _fall(c, _cross_at(c, p)))


def vault_range(doc: Doc, rid, outer):
    """(least, greatest) exact elevation of the vault over the room polygon (15.3): over the outer ring's
    vertices, except that a two-sided vault whose ridge line meets the polygon reaches E + h."""
    c = ceiling(doc, rid)
    base = ceiling_base(doc, rid)
    crosses = [_cross_at(c, p) for p in outer]
    falls = [_fall(c, cr) for cr in crosses]
    low = vault_z(base, c, max(falls))
    if c.get('slopes', 'both') == 'both' and min(crosses) <= 0 <= max(crosses):
        high = Surd(base)
    else:
        high = vault_z(base, c, min(falls))
    return low, high


# ------------------------------------------------------------------------------ trays (15.4)

def _inset_ring(ring, w):
    """Every vertex of a ring moved: the intersection of its two edges' lines moved w to their left, or
    the vertex moved w along their common left normal where the edges are collinear. Exact."""
    n = len(ring)
    out = []
    for i in range(n):
        p0, p1, p2 = ring[i - 1], ring[i], ring[(i + 1) % n]
        d0 = (p1[0] - p0[0], p1[1] - p0[1])
        d1 = (p2[0] - p1[0], p2[1] - p1[1])

        def line(d, p):
            nx, ny = -d[1], d[0]
            D = d[0] * d[0] + d[1] * d[1]
            return nx, ny, Surd(nx * p[0] + ny * p[1]) + Surd.sqrt(D, w)
        if plane.cross(d0, d1) != 0:
            out.append(LevelGraph.intersect(line(d0, p0), line(d1, p1)))
        else:
            D = d1[0] * d1[0] + d1[1] * d1[1]
            out.append((Surd(p1[0]) + Surd.sqrt(D, Fraction(-d1[1] * w, D)),
                        Surd(p1[1]) + Surd.sqrt(D, Fraction(d1[0] * w, D))))
    return out


def tray_rings(outer, holes, border):
    """15.4: the tray's centre - (outer, holes), rounded, in the orientation of the room polygon's rings -
    or None when it does not fit: an edge of a rounded moved ring does not run the way its edge of the
    room polygon runs, or the moved rings are degenerate (6.2)."""
    rings = []
    for ring in [outer] + list(holes):
        moved = [rpoint(p) for p in _inset_ring(ring, border)]
        n = len(ring)
        for i in range(n):
            e = (ring[(i + 1) % n][0] - ring[i][0], ring[(i + 1) % n][1] - ring[i][1])
            m = (moved[(i + 1) % n][0] - moved[i][0], moved[(i + 1) % n][1] - moved[i][1])
            if plane.dot(e, m) <= 0:
                return None
        rings.append(moved)
    if degenerate(rings[0], rings[1:]):
        return None
    return rings[0], rings[1:]


def in_tray(point, tray) -> bool:
    """A plan point in the closed tray centre: inside or on its outer ring, and not strictly inside a hole."""
    outer, holes = tray
    return plane.locate(point, outer) != 'out' and all(plane.locate(point, h) != 'in' for h in holes)


# ------------------------------------------------------------------------------ hosting (15.6)

def surface_elevation(doc: Doc, host) -> int:
    """15.6: Oz of a `surface` host - the room's floor top, or its ceiling's elevation at the host's
    position, rounded once."""
    rid = host['room']
    if host['surface'] == 'floor':
        return floor_top(doc, rid)
    c = ceiling(doc, rid)
    base = ceiling_base(doc, rid)
    if c['kind'] == 'flat':
        return base
    p = tuple(host['position'])
    if c['kind'] == 'vaulted':
        return vault_at(doc, rid, p).round()
    outer, holes = room_rings(doc, rid)
    tray = tray_rings(outer, holes, c['border'])
    return base + c['depth'] if in_tray(p, tray) else base


# ------------------------------------------------------------------------------ invariants (15.2, 15.4)

def invariants(doc: Doc, bad_levels, bad_rooms, diag):
    """FS-INV-701 to FS-INV-703, for every room on a level where room invariants are evaluated and with
    none of FS-INV-201 to FS-INV-204 (10.3); FS-INV-701 not for a room with FS-INV-702."""
    ds = []
    graphs = {}
    for rid in sorted(doc.rooms):
        r = doc.rooms[rid]
        if r['level'] in bad_levels or rid in bad_rooms:
            continue
        c = ceiling(doc, rid)
        if c['kind'] == 'vaulted' and c['ridge'][0] == c['ridge'][1]:
            ds.append(diag('FS-INV-702', [rid]))
            continue
        if r['level'] not in graphs:
            graphs[r['level']] = LevelGraph(doc, r['level'])
        outer, holes = room_rings(doc, rid, graphs[r['level']])
        if c['kind'] == 'vaulted':
            low, _ = vault_range(doc, rid, outer)
        else:
            low = Surd(ceiling_base(doc, rid))
        if (low - floor_top(doc, rid)).sign() <= 0:
            ds.append(diag('FS-INV-701', [rid]))
        if c['kind'] == 'tray' and tray_rings(outer, holes, c['border']) is None:
            ds.append(diag('FS-INV-703', [rid]))
    return ds


# ------------------------------------------------------------------------------ derived values (15.5, 15.7)

def _box(ring, z0, z1):
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return {'min': [min(xs), min(ys), z0], 'max': [max(xs), max(ys), z1]}


def _ring_value(r):
    return [list(p) for p in plane.least_first(r)]


def derive(doc: Doc) -> dict:
    """{floors, ceilings, slabs} of a valid document."""
    floors, ceilings, slabs = {}, {}, {}
    graphs = {}
    for rid in sorted(doc.rooms):
        level = doc.rooms[rid]['level']
        if level not in graphs:
            graphs[level] = LevelGraph(doc, level)
        outer, holes = room_rings(doc, rid, graphs[level])
        top = floor_top(doc, rid)
        bottom = top - floor_thickness(doc, rid)
        floors[rid] = {'top': top, 'bottom': bottom, 'box': _box(outer, bottom, top)}
        c = ceiling(doc, rid)
        base = ceiling_base(doc, rid)
        v = {'kind': c['kind']}
        if c['kind'] == 'flat':
            low = high = base
        elif c['kind'] == 'tray':
            low, high = base, base + c['depth']
            t_outer, t_holes = tray_rings(outer, holes, c['border'])
            v['tray'] = {'outer': _ring_value(t_outer),
                         'holes': sorted((_ring_value(h) for h in t_holes), key=lambda r: r[0])}
        else:
            lo, hi = vault_range(doc, rid, outer)
            low, high = lo.round(), hi.round()
        v.update(low=low, high=high, box=_box(outer, low, high))
        ceilings[rid] = v
    for sid in sorted(doc.slabs):
        s = doc.slabs[sid]
        ring = [tuple(p) for p in s['boundary']]
        if plane.area2(ring) < 0:
            ring = ring[::-1]
        top = doc.levels[s['level']]['elevation'] + s.get('offset', 0)
        bottom = top - s['thickness']
        slabs[sid] = {'outline': _ring_value(ring), 'top': top, 'bottom': bottom, 'box': _box(ring, bottom, top)}
    return {'floors': floors, 'ceilings': ceilings, 'slabs': slabs}

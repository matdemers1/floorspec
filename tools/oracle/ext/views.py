"""FS_views 0.1.0 (registry/FS_views/spec.md): its invariants, lints and derived values, written from
the extension's specification alone.

FS_views adds no kind of element and requires no other extension. It reads, of FS_lighting's data,
only the IDs of its scenes, as they are (spec.md 1.3): an `extensions.FS_lighting` or a `scenes` that
is not an object holds no scene."""

from __future__ import annotations

from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_views', '0.1.0', 'VIEW'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'views')
SEVERITY = {'FS-VIEW-LINT-001': 'warning'}
LGHT = 'FS_lighting'
DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _views(ctx: Context) -> dict:
    return ctx.data.get('views', {})


def scenes(ctx: Context) -> set:
    """1.3: the IDs of extensions.FS_lighting.scenes, read as data."""
    data = ctx.d.get('extensions', {}).get(LGHT)
    s = data.get('scenes') if isinstance(data, dict) else None
    return set(s) if isinstance(s, dict) else set()


def leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def day_exists(at: str) -> bool:
    """3.2.1: the day of `at` (the schema's form, YYYY-MM-DDT...) is one its month has."""
    year, month, day = int(at[0:4]), int(at[5:7]), int(at[8:10])
    return day <= (29 if month == 2 and leap(year) else DAYS[month - 1])


def steep(v: dict) -> bool:
    """5.3: a line of sight more than 30 degrees from level - 3 dz^2 > dx^2 + dy^2, exactly."""
    dx, dy, dz = (v['target'][i] - v['eye'][i] for i in range(3))
    return 3 * dz * dz > dx * dx + dy * dy


def invariants(ctx: Context):
    ds = []
    views = _views(ctx)
    lscenes = scenes(ctx)
    taken = ctx.space() | lscenes
    levels = ctx.d.get('levels', {})
    for vid, v in views.items():
        if vid in taken:                                                       # 1.3.2
            ds.append(ctx.diag('FS-VIEW-INV-001', [vid]))
        if v['eye'] == v['target']:                                            # 2.2.1
            ds.append(ctx.diag('FS-VIEW-INV-002', [vid]))
        if 'level' in v and v['level'] not in levels:                          # 3.1.1
            ds.append(ctx.diag('FS-VIEW-INV-003', [vid]))
        if 'scene' in v and v['scene'] not in lscenes:                         # 3.3.1
            ds.append(ctx.diag('FS-VIEW-INV-004', [vid]))
        if 'scene' in v and v.get('lights') == 'off':                          # 3.3.2
            ds.append(ctx.diag('FS-VIEW-INV-005', [vid]))
        if 'at' in v and not day_exists(v['at']):                              # 3.2.1
            ds.append(ctx.diag('FS-VIEW-INV-007', [vid]))
    ids = sorted(views)
    for i, a in enumerate(ids):                                                # 2.1.1, once for each pair
        for b in ids[i + 1:]:
            if views[a]['name'] == views[b]['name']:
                ds.append(ctx.diag('FS-VIEW-INV-006', [a, b]))
    return ds


def lints(ctx: Context):
    return [ctx.diag('FS-VIEW-LINT-001', [vid]) for vid, v in _views(ctx).items()
            if v.get('twoPoint', False) and steep(v)]                          # 5.3


def derive(ctx: Context) -> dict:
    return {'views': {vid: {'name': v['name'], 'level': v.get('level'),
                            'lights': 'on' if v.get('lights') == 'on' or 'scene' in v else 'off',
                            'scene': v.get('scene')}
                      for vid, v in sorted(_views(ctx).items())}}

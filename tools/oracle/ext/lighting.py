"""FS_lighting 0.1.0 (registry/FS_lighting/spec.md): its invariants, lints and derived values,
written from the extension's specification alone.

FS_lighting adds no kind of element. It reads, of FS_electrical's data, only which collection an
element is in and a switch's `control` and `controls`, as they are (spec.md 1.3): a `controls` that
is not an array lists nothing."""

from __future__ import annotations

from .common import Context, check_ids, load_schema

NAME, VERSION, CODE = 'FS_lighting', '0.1.0', 'LGHT'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'lighting')
SEVERITY = {'FS-LGHT-LINT-001': 'warning', 'FS-LGHT-LINT-002': 'warning', 'FS-LGHT-LINT-003': 'info'}
ELEC = 'FS_electrical'
DIMMING = ('dimmer', 'smart')                 # 5.3: the switch controls that dim (FS_electrical 2.3)


def gives_light(ctx: Context, eid) -> bool:
    """2.1.1, 3.1.1: a light of FS_electrical, or an extension element of another extension."""
    x = ctx.ext.get(eid)
    return x is not None and (x[0] != ELEC or x[1] == 'lights')


def _luminaires(ctx: Context) -> dict:
    return ctx.data.get('luminaires', {})


def _scenes(ctx: Context) -> dict:
    return ctx.data.get('scenes', {})


def invariants(ctx: Context):
    ds = check_ids(ctx, 'scenes', 'FS-LGHT-INV-001')                          # 1.3.2
    for lid, lum in _luminaires(ctx).items():
        if not gives_light(ctx, lid):                                          # 2.1.1
            ds.append(ctx.diag('FS-LGHT-INV-002', [lid]))
        rng = lum.get('cctRange')
        if rng is not None and not rng[0] < rng[1]:                            # 2.1.2
            ds.append(ctx.diag('FS-LGHT-INV-003', [lid]))
        elif rng is not None and 'cct' in lum and not rng[0] <= lum['cct'] <= rng[1]:
            ds.append(ctx.diag('FS-LGHT-INV-004', [lid]))                      # 2.1.3, only without INV-003
    scenes = _scenes(ctx)
    for sid, s in scenes.items():
        for t in s.get('on', {}):
            if not gives_light(ctx, t):                                        # 3.1.1, once for each
                ds.append(ctx.diag('FS-LGHT-INV-005', [sid]))
    ids = sorted(scenes)
    for i, a in enumerate(ids):                                                # 3.1.2, once for each pair
        for b in ids[i + 1:]:
            if scenes[a]['name'] == scenes[b]['name']:
                ds.append(ctx.diag('FS-LGHT-INV-006', [a, b]))
    return ds


def _dimmed(ctx: Context) -> set:
    """The lights of FS_electrical that a switch whose `control` is "dimmer" or "smart" controls."""
    out = set()
    for x, c, s in ctx.ext.values():
        if (x == ELEC and c == 'switches' and isinstance(s, dict) and s.get('control', 'single') in DIMMING
                and isinstance(s.get('controls'), list)):
            out.update(t for t in s['controls'] if isinstance(t, str))
    return out


def lints(ctx: Context):
    ds = []
    lums = _luminaires(ctx)
    dimmed = _dimmed(ctx)
    for sid, s in _scenes(ctx).items():
        for t, setting in s.get('on', {}).items():
            lum = lums.get(t, {})
            output = setting.get('output', 100)
            if output < 100 and lum.get('dimmable') is False:                  # 5.3: dimmed, not dimmable
                ds.append(ctx.diag('FS-LGHT-LINT-001', [sid, t]))
            if 'cct' in setting:                                               # 5.3: a colour it cannot give
                k = setting['cct']
                if 'cctRange' in lum:
                    if not lum['cctRange'][0] <= k <= lum['cctRange'][1]:
                        ds.append(ctx.diag('FS-LGHT-LINT-002', [sid, t]))
                elif 'cct' in lum and k != lum['cct']:
                    ds.append(ctx.diag('FS-LGHT-LINT-002', [sid, t]))
            x = ctx.ext.get(t)
            if output < 100 and x is not None and x[0] == ELEC and x[1] == 'lights' and t not in dimmed:
                ds.append(ctx.diag('FS-LGHT-LINT-003', [sid, t]))              # 5.3: no switch dims it
    return ds


def derive(ctx: Context) -> dict:
    scenes = _scenes(ctx)
    out_s, by_lum = {}, {lid: [] for lid in _luminaires(ctx)}
    for sid, s in sorted(scenes.items()):
        on = s.get('on', {})
        out_s[sid] = {'name': s['name'], 'on': sorted(on),
                      'dimmed': sorted(t for t, v in on.items() if v.get('output', 100) < 100)}
        for t in on:
            by_lum.setdefault(t, []).append(sid)
    return {'scenes': out_s, 'luminaires': {lid: {'scenes': sorted(v)} for lid, v in sorted(by_lum.items())}}

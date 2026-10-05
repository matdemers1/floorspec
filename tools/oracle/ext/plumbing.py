"""FS_plumbing 0.1.0 (registry/FS_plumbing/spec.md): its invariants, lints and derived values,
written from the extension's specification alone."""

from __future__ import annotations

from .common import Context, check_ids, load_schema

NAME, VERSION, CODE = 'FS_plumbing', '0.1.0', 'PLMB'
CORE = ('0.2', '0.3')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'plumbing')
SEVERITY = {'FS-PLMB-LINT-001': 'warning', 'FS-PLMB-LINT-002': 'warning', 'FS-PLMB-LINT-003': 'info',
            'FS-PLMB-LINT-004': 'warning', 'FS-PLMB-LINT-005': 'info'}
FUELS = ('naturalGas', 'propane', 'oil')
NO_DRAIN = ('hoseBibb', 'iceMaker')


def _drainers(ctx: Context):
    for kind in ('fixtures', 'waterHeaters', 'drains'):
        for eid, el in ctx.coll(kind).items():
            if 'drain' in el:
                yield kind, eid, el


def invariants(ctx: Context):
    ds = check_ids(ctx, 'stacks', 'FS-PLMB-INV-001')
    stacks, drains = ctx.data.get('stacks', {}), ctx.coll('drains')

    def to_stack(eid, el, sid):
        s = stacks[sid]
        if s.get('stack', 'drainWasteVent') == 'vent':                   # 3.1.3
            ds.append(ctx.diag('FS-PLMB-INV-003', [eid, sid]))
        elif el['fallback']['level'] not in s['levels']:                  # 3.1.4
            ds.append(ctx.diag('FS-PLMB-INV-004', [eid, sid]))

    for kind, eid, el in _drainers(ctx):                                  # 3.1.2
        t = el['drain']
        if t in stacks:
            to_stack(eid, el, t)
        elif not (kind != 'drains' and t in drains):
            ds.append(ctx.diag('FS-PLMB-INV-002', [eid]))
    for eid, el in ctx.coll('cleanouts').items():
        if el['stack'] not in stacks:                                     # 3.1.5
            ds.append(ctx.diag('FS-PLMB-INV-007', [eid]))
        elif el['fallback']['level'] not in stacks[el['stack']]['levels']:
            ds.append(ctx.diag('FS-PLMB-INV-004', [eid, el['stack']]))
    for sid, s in stacks.items():                                         # 3.1.1
        if any(lid not in ctx.doc.levels for lid in s['levels']):
            ds.append(ctx.diag('FS-PLMB-INV-006', [sid]))
    heaters = ctx.coll('waterHeaters')
    for eid, el in ctx.coll('fixtures').items():
        if 'hotFrom' not in el:
            continue
        if el['hotFrom'] not in heaters:                                  # 3.2.1
            ds.append(ctx.diag('FS-PLMB-INV-005', [eid]))
        elif 'supply' in el and 'hot' not in el['supply']:                # 3.2.2
            ds.append(ctx.diag('FS-PLMB-INV-008', [eid]))
    for eid, el in heaters.items():                                       # 2.2.1
        if el['energy'] not in FUELS and 'combustionAir' in el:
            ds.append(ctx.diag('FS-PLMB-INV-009', [eid]))
    return ds


def lints(ctx: Context):
    ds = []
    for eid, el in ctx.coll('fixtures').items():
        if 'drain' not in el and el['fixture'] not in NO_DRAIN:
            ds.append(ctx.diag('FS-PLMB-LINT-001', [eid]))
        if 'hot' in el.get('supply', []) and 'hotFrom' not in el:
            ds.append(ctx.diag('FS-PLMB-LINT-005', [eid]))
        if el['fixture'] == 'waterCloset' and not ctx.has_purpose(el, 'fixtureClearance'):
            ds.append(ctx.diag('FS-PLMB-LINT-004', [eid]))
    for eid, el in ctx.coll('waterHeaters').items():
        if el['energy'] in FUELS and 'combustionAir' not in el:
            ds.append(ctx.diag('FS-PLMB-LINT-002', [eid]))
        if not ctx.has_purpose(el, 'access'):
            ds.append(ctx.diag('FS-PLMB-LINT-004', [eid]))
    for eid, el in ctx.coll('cleanouts').items():
        if not ctx.has_purpose(el, 'access'):
            ds.append(ctx.diag('FS-PLMB-LINT-004', [eid]))
    used = {el['drain'] for _, _, el in _drainers(ctx)}
    for sid in ctx.data.get('stacks', {}):
        if sid not in used:
            ds.append(ctx.diag('FS-PLMB-LINT-003', [sid]))
    return ds


def derive(ctx: Context) -> dict:
    stacks = ctx.data.get('stacks', {})
    drains = ctx.coll('drains')
    out_s = {}
    for sid in sorted(stacks):
        connected = set()
        for _, eid, el in _drainers(ctx):
            t = el['drain']
            if t == sid or (t in drains and drains[t].get('drain') == sid):
                connected.add(eid)
        out_s[sid] = {'connected': sorted(connected),
                      'cleanouts': sorted(c for c, el in ctx.coll('cleanouts').items() if el['stack'] == sid)}
    out_h = {hid: {'fixtures': sorted(f for f, el in ctx.coll('fixtures').items() if el.get('hotFrom') == hid)}
             for hid in sorted(ctx.coll('waterHeaters'))}
    return {'stacks': out_s, 'waterHeaters': out_h, 'rooms': ctx.rooms_derived()}

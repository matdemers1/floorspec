"""FS_lowvoltage 0.1.0 (registry/FS_lowvoltage/spec.md): its invariants, lints and derived values,
written from the extension's specification alone."""

from __future__ import annotations

from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_lowvoltage', '0.1.0', 'LOWV'
CORE = ('0.2', '0.3')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'lowvoltage')
SEVERITY = {'FS-LOWV-LINT-001': 'info', 'FS-LOWV-LINT-002': 'warning', 'FS-LOWV-LINT-003': 'warning'}
RUN = ('outlets', 'doorbells', 'security', 'speakers')
BUTTONS = ('button', 'videoButton')


def systems(kind: str, el) -> list:
    """3.1: the systems an element belongs to."""
    if kind == 'outlets':
        return list(el['media'])
    return [{'doorbells': 'doorbell', 'security': 'security', 'speakers': 'audio'}[kind]]


def invariants(ctx: Context):
    ds = []
    heads = ctx.coll('headEnds')
    for kind in RUN:
        for eid, el in ctx.coll(kind).items():
            if 'headEnd' not in el:
                continue
            h = el['headEnd']
            if h not in heads:                                            # 3.1.1
                ds.append(ctx.diag('FS-LOWV-INV-001', [eid]))
            elif any(s not in heads[h]['serves'] for s in systems(kind, el)):   # 3.1.2
                ds.append(ctx.diag('FS-LOWV-INV-003', [eid, h]))
    bells = ctx.coll('doorbells')
    for eid, el in bells.items():                                         # 3.2.1
        if 'chime' in el:
            c = bells.get(el['chime'])
            if el['part'] not in BUTTONS or c is None or c['part'] != 'chime':
                ds.append(ctx.diag('FS-LOWV-INV-002', [eid]))
    return ds


def lints(ctx: Context):
    ds = []
    for kind in ('outlets', 'speakers', 'security'):
        for eid, el in ctx.coll(kind).items():
            if 'headEnd' not in el and not el.get('wireless', False):
                ds.append(ctx.diag('FS-LOWV-LINT-001', [eid]))
    for eid, el in ctx.coll('doorbells').items():
        if el['part'] in BUTTONS and 'chime' not in el:
            ds.append(ctx.diag('FS-LOWV-LINT-002', [eid]))
    for eid, el in ctx.coll('headEnds').items():
        if not ctx.has_purpose(el, 'access'):
            ds.append(ctx.diag('FS-LOWV-LINT-003', [eid]))
    return ds


def derive(ctx: Context) -> dict:
    out = {}
    for hid in sorted(ctx.coll('headEnds')):
        runs, ports = [], {}
        for kind in RUN:
            for eid, el in ctx.coll(kind).items():
                if el.get('headEnd') == hid:
                    runs.append(eid)
                    if kind == 'outlets':
                        for m in el['media']:
                            ports[m] = ports.get(m, 0) + el.get('ports', 1)
        out[hid] = {'runs': sorted(runs), 'ports': dict(sorted(ports.items()))}
    return {'headEnds': out, 'rooms': ctx.rooms_derived()}

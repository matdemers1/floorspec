"""FS_electrical 0.1.0 (registry/FS_electrical/spec.md): its invariants, lints and derived values,
written from the extension's specification alone."""

from __future__ import annotations

from .common import Context, check_ids, load_schema

NAME, VERSION, CODE = 'FS_electrical', '0.1.0', 'ELEC'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'electrical')
SEVERITY = {'FS-ELEC-LINT-001': 'warning', 'FS-ELEC-LINT-002': 'info', 'FS-ELEC-LINT-003': 'warning',
            'FS-ELEC-LINT-004': 'warning', 'FS-ELEC-LINT-005': 'info', 'FS-ELEC-LINT-006': 'warning',
            'FS-ELEC-LINT-007': 'warning'}
VOLTS = {'receptacles': 120, 'lights': 120, 'alarms': 120, 'evChargers': 240}     # 2.2-2.6 defaults
LOADS = tuple(VOLTS)


def _battery(el) -> bool:
    return el.get('power', 'mainsWithBattery') == 'battery'


def invariants(ctx: Context):
    ds = check_ids(ctx, 'circuits', 'FS-ELEC-INV-001')
    panels, circuits = ctx.coll('panels'), ctx.data.get('circuits', {})
    on_panel = {}
    for cid, c in circuits.items():
        pid = c['panel']
        if pid not in panels:                                             # 3.1.1
            ds.append(ctx.diag('FS-ELEC-INV-002', [cid]))
            continue
        p = panels[pid]
        if c["volts"] not in p["volts"]:                                  # 3.1.2
            ds.append(ctx.diag('FS-ELEC-INV-007', [cid, pid]))
        if 'space' in c:
            first, last = c['space'], c['space'] + c.get('poles', 1) - 1
            if last > p['spaces']:                                        # 3.3.1
                ds.append(ctx.diag('FS-ELEC-INV-008', [cid, pid]))
            on_panel.setdefault(pid, []).append((cid, first, last))
    for pid, cs in on_panel.items():                                      # 3.3.2
        cs.sort()
        for i, (a, a0, a1) in enumerate(cs):
            for b, b0, b1 in cs[i + 1:]:
                if max(a0, b0) <= min(a1, b1):
                    ds.append(ctx.diag('FS-ELEC-INV-009', [a, b]))
    feeding = {}
    for cid, c in circuits.items():
        for load in c.get('loads', []):
            if load not in ctx.ext:                                       # 3.2.1
                ds.append(ctx.diag('FS-ELEC-INV-003', [cid]))
                continue
            own = ctx.own(load)
            if own is not None and own[0] in ('panels', 'switches'):      # 3.2.2
                ds.append(ctx.diag('FS-ELEC-INV-004', [cid, load]))
                continue
            feeding.setdefault(load, []).append(cid)
            if own is None:
                continue
            kind, el = own
            if kind == 'alarms' and _battery(el):                         # 3.2.5
                ds.append(ctx.diag('FS-ELEC-INV-013', [cid, load]))
            elif el.get('volts', VOLTS[kind]) != c['volts']:              # 3.2.4
                ds.append(ctx.diag('FS-ELEC-INV-006', [cid, load]))
    for load, cids in feeding.items():                                    # 3.2.3
        if len({circuits[c]['panel'] for c in cids}) > 1:
            ds.append(ctx.diag('FS-ELEC-INV-005', [load]))
    for sid, s in ctx.coll('switches').items():                           # 4.1.1
        for t in s.get('controls', []):
            own = ctx.own(t)
            if t not in ctx.ext or (own is not None and own[0] not in ('lights', 'receptacles')):
                ds.append(ctx.diag('FS-ELEC-INV-010', [sid]))
    for pid, p in panels.items():
        if 'fedBy' in p and p['fedBy'] not in circuits:                   # 3.4.1
            ds.append(ctx.diag('FS-ELEC-INV-011', [pid]))
    for pid, p in panels.items():                                         # 3.4.2
        cur, seen = pid, set()
        while True:
            c = circuits.get(panels[cur].get('fedBy')) if 'fedBy' in panels[cur] else None
            if c is None or c['panel'] not in panels:
                break
            cur = c['panel']
            if cur == pid:
                ds.append(ctx.diag('FS-ELEC-INV-012', [pid]))
                break
            if cur in seen:
                break
            seen.add(cur)
    return ds


def _loads_of(ctx: Context):
    out = {}
    for cid, c in ctx.data.get('circuits', {}).items():
        for load in c.get('loads', []):
            out.setdefault(load, []).append(cid)
    return out


def _connected(ctx: Context, c) -> int:
    total = 0
    for load in c.get('loads', []):
        own = ctx.own(load)
        if own is not None:
            total += own[1].get('watts', 0)
    return total


def lints(ctx: Context):
    ds = []
    loads = _loads_of(ctx)
    for kind in LOADS:
        for eid, el in ctx.coll(kind).items():
            if kind == 'alarms' and _battery(el):
                continue
            if eid not in loads:                                          # 5.3
                ds.append(ctx.diag('FS-ELEC-LINT-001', [eid]))
    controlled = {t for s in ctx.coll('switches').values() for t in s.get('controls', [])}
    for lid in ctx.coll('lights'):
        if lid not in controlled:
            ds.append(ctx.diag('FS-ELEC-LINT-002', [lid]))
    for cid, c in ctx.data.get('circuits', {}).items():
        if 'rating' in c and c['breaker'] > c['rating']:
            ds.append(ctx.diag('FS-ELEC-LINT-003', [cid]))
        if _connected(ctx, c) > c['breaker'] * c['volts']:
            ds.append(ctx.diag('FS-ELEC-LINT-004', [cid]))
        if not c.get('loads'):
            ds.append(ctx.diag('FS-ELEC-LINT-005', [cid]))
        for load in c.get('loads', []):
            own = ctx.own(load)
            if own is not None and own[0] == 'evChargers' and own[1]['amps'] > c['breaker']:
                ds.append(ctx.diag('FS-ELEC-LINT-007', [cid, load]))
    for pid, p in ctx.coll('panels').items():
        if not ctx.has_purpose(p, 'workingSpace'):
            ds.append(ctx.diag('FS-ELEC-LINT-006', [pid]))
    return ds


def derive(ctx: Context) -> dict:
    circuits = ctx.data.get('circuits', {})
    out_c, out_p = {}, {}
    for cid, c in sorted(circuits.items()):
        out_c[cid] = {'panel': c['panel'], 'loads': sorted(c.get('loads', [])),
                      'connectedLoad': _connected(ctx, c), 'capacity': c['breaker'] * c['volts']}
    for pid in sorted(ctx.coll('panels')):
        mine = sorted(cid for cid, c in circuits.items() if c['panel'] == pid)
        out_p[pid] = {'circuits': mine, 'spacesUsed': sum(circuits[c].get('poles', 1) for c in mine),
                      'connectedLoad': sum(out_c[c]['connectedLoad'] for c in mine)}
    controls = {}
    for sid, s in ctx.coll('switches').items():
        for t in s.get('controls', []):
            controls.setdefault(t, []).append(sid)
    return {'circuits': out_c, 'panels': out_p,
            'controls': {t: sorted(v) for t, v in sorted(controls.items())},
            'rooms': ctx.rooms_derived()}

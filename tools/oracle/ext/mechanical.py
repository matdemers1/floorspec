"""FS_mechanical 0.1.0 (registry/FS_mechanical/spec.md): its invariants, lints and derived values,
written from the extension's specification alone."""

from __future__ import annotations

from .common import Context, check_ids, load_schema

NAME, VERSION, CODE = 'FS_mechanical', '0.1.0', 'MECH'
SCHEMA = load_schema(NAME, 'mechanical')
SEVERITY = {'FS-MECH-LINT-001': 'warning', 'FS-MECH-LINT-002': 'warning', 'FS-MECH-LINT-003': 'warning',
            'FS-MECH-LINT-004': 'warning', 'FS-MECH-LINT-005': 'info'}
GASES = ('naturalGas', 'propane')
SERVICED = ('furnace', 'airHandler', 'boiler')


def _burners(ctx: Context):
    """(ID, element, fuel) of every element that may burn fuel: equipment and gas appliances."""
    for eid, el in ctx.coll('equipment').items():
        yield eid, el, el.get('fuel', 'electric')
    for eid, el in ctx.coll('gasAppliances').items():
        yield eid, el, el['fuel']


def invariants(ctx: Context):
    ds = check_ids(ctx, 'gasSources', 'FS-MECH-INV-001')
    sources = ctx.data.get('gasSources', {})
    for eid, el, fuel in _burners(ctx):
        if 'gasFrom' in el:
            g = el['gasFrom']
            if g not in sources:                                          # 3.1.1
                ds.append(ctx.diag('FS-MECH-INV-002', [eid]))
            elif sources[g]['fuel'] != fuel:                              # 3.1.2
                ds.append(ctx.diag('FS-MECH-INV-003', [eid, g]))
    for eid, el in ctx.coll('equipment').items():                         # 2.1.1
        if el.get('fuel', 'electric') == 'electric' and ('combustionAir' in el or 'vent' in el):
            ds.append(ctx.diag('FS-MECH-INV-005', [eid]))
    equipment = ctx.coll('equipment')
    for eid, el in ctx.coll('terminals').items():                         # 3.2.1
        if 'equipment' in el and el['equipment'] not in equipment:
            ds.append(ctx.diag('FS-MECH-INV-004', [eid]))
    return ds


def lints(ctx: Context):
    ds = []
    for eid, el, fuel in _burners(ctx):
        if fuel != 'electric' and 'combustionAir' not in el:
            ds.append(ctx.diag('FS-MECH-LINT-001', [eid]))
        if fuel in GASES and 'gasFrom' not in el:
            ds.append(ctx.diag('FS-MECH-LINT-002', [eid]))
    for eid, el in ctx.coll('terminals').items():
        if el['terminal'] != 'transfer' and 'equipment' not in el:
            ds.append(ctx.diag('FS-MECH-LINT-003', [eid]))
    for eid, el in ctx.coll('equipment').items():
        if el['equipment'] in SERVICED and not ctx.has_purpose(el, 'workingSpace'):
            ds.append(ctx.diag('FS-MECH-LINT-004', [eid]))
    drawn = {el['gasFrom'] for _, el, _ in _burners(ctx) if 'gasFrom' in el}
    for gid in ctx.data.get('gasSources', {}):
        if gid not in drawn:
            ds.append(ctx.diag('FS-MECH-LINT-005', [gid]))
    return ds


def derive(ctx: Context) -> dict:
    burners = list(_burners(ctx))
    out_g = {}
    for gid, g in sorted(ctx.data.get('gasSources', {}).items()):
        mine = [(eid, el) for eid, el, _ in burners if el.get('gasFrom') == gid]
        out_g[gid] = {'fuel': g['fuel'], 'appliances': sorted(eid for eid, _ in mine),
                      'input': sum(el.get('input', 0) for _, el in mine)}
    out_e = {}
    for eid in sorted(ctx.coll('equipment')):
        ts = [(tid, t) for tid, t in ctx.coll('terminals').items() if t.get('equipment') == eid]
        out_e[eid] = {'terminals': sorted(tid for tid, _ in ts), 'airflow': sum(t.get('airflow', 0) for _, t in ts)}
    return {'gasSources': out_g, 'equipment': out_e, 'rooms': ctx.rooms_derived()}

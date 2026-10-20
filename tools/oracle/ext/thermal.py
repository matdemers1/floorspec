"""FS_thermal 0.1.0 (registry/FS_thermal/spec.md): its schema tier over the data on core elements,
its invariants, lints and derived values, written from the extension's specification alone.

FS_thermal adds no kind of element: its data is each material's, type's, roof's and room's own
`extensions.FS_thermal` (1.3). What it derives is exact - a layer's resistance is 25 t / (32 k)
thousandths of m2.K/W and its heat capacity t x density x specific heat / 1,280,000 J/(m2.K), each
rounded once, ties to even (3.1) - and a path's values are sums of its layers' rounded values (3.2).
Nothing here is a U-factor, a heat loss or a judgement of an envelope (1.4, 3.3).
"""

from __future__ import annotations

from fractions import Fraction

from .common import Context, load_schema

NAME, VERSION, CODE = 'FS_thermal', '0.1.0', 'THRM'
CORE = ('0.2', '0.3', '0.4')                  # the Core drafts whose documents it is evaluated for (1.1, 1.2)
SCHEMA = load_schema(NAME, 'thermal')
SEVERITY = {'FS-THRM-LINT-001': 'warning', 'FS-THRM-LINT-002': 'info'}
DEFINED = ('materials', 'roofs', 'rooms')     # 1.3: the collections whose elements carry data as { C: data }
TYPE_KINDS = ('wallType', 'doorType', 'windowType')   # 1.3: a type's data is checked as { K: data }
# 1.3.3: every other element that has an `extensions` member (Core 0.2, 0.3 and 0.4)
OTHERS = ('buildings', 'levels', 'junctions', 'walls', 'separators', 'openings', 'slabs', 'assets', 'stairs',
          'optionSets', 'options')


def _data(el):
    x = el.get('extensions', {}) if isinstance(el, dict) else {}
    return x.get(NAME) if isinstance(x, dict) else None


def schema_errors(doc, data) -> list[str]:
    """1.3.1 to 1.3.3: the top-level data, and the data on every element, against the schema."""
    d = doc.d
    out = list(SCHEMA.errors(data))
    core = SCHEMA.root['$defs']['coreElements']
    for c in DEFINED:
        for eid, el in d.get(c, {}).items():
            v = _data(el)
            if v is not None:
                out.extend(f'{c}/{eid}{e}' for e in SCHEMA.errors({c: v}, core))
    for tid, t in d.get('types', {}).items():
        v = _data(t)
        if v is not None:
            out.extend(f'types/{tid}{e}' for e in SCHEMA.errors({t['kind']: v}, core))
    others = [(c, d.get(c, {})) for c in OTHERS] + [('items', d.get('program', {}).get('items', {}))]
    for c, elements in others:
        for eid, el in elements.items():
            if _data(el) is not None:
                out.append(f'{c}/{eid}: may not carry {NAME} data')
    return out


# ------------------------------------------------------------------------------- assemblies

def assemblies(d):
    """(section, ID, carrier ID, layers, framing) of every assembly of 5.1, in the derived order:
    every wall type; every roof whose data has layers; every room whose floor has layers."""
    out = []
    for tid in sorted(d.get('types', {})):
        t = d['types'][tid]
        if t['kind'] == 'wallType':
            out.append(('wallTypes', tid, t['layers'], (_data(t) or {}).get('framing')))
    for rid in sorted(d.get('roofs', {})):
        v = _data(d['roofs'][rid])
        if v is not None:
            out.append(('roofs', rid, v['layers'], v.get('framing')))
    for rid in sorted(d.get('rooms', {})):
        f = (_data(d['rooms'][rid]) or {}).get('floor', {})
        if 'layers' in f:
            out.append(('floors', rid, f['layers'], f.get('framing')))
    return out


def _thermal(d, mid):
    m = d.get('materials', {}).get(mid) if mid is not None else None
    return None if m is None else (_data(m) or {})


def layer_values(d, thickness, mid):
    """3.1: (resistance, heat capacity) of a layer of `thickness` made of material `mid`."""
    t = _thermal(d, mid)
    if t is None:
        return None, None
    if 'resistance' in t:
        r = t['resistance']
    elif 'conductivity' in t:
        r = round(Fraction(25 * thickness, 32 * t['conductivity']))
    else:
        r = None
    c = round(Fraction(thickness * t['density'] * t['specificHeat'], 1280000)) \
        if 'density' in t and 'specificHeat' in t else None
    return r, c


def _sum(xs):
    return None if any(x is None for x in xs) else sum(xs)


def derive_assembly(d, layers, framing):
    """5.1: an assembly's derived values."""
    vals = [layer_values(d, lay['thickness'], lay.get('material')) for lay in layers]
    out = {'layers': [{'resistance': r, 'heatCapacity': c} for r, c in vals],
           'clear': {'resistance': _sum([r for r, _ in vals]), 'heatCapacity': _sum([c for _, c in vals])}}
    if framing is not None:
        fv = [layer_values(d, lay['thickness'], framing['material']) if lay['function'] == 'core' else v
              for lay, v in zip(layers, vals)]
        out['framed'] = {'fraction': framing['fraction'], 'resistance': _sum([r for r, _ in fv]),
                         'heatCapacity': _sum([c for _, c in fv])}
    return out


# ------------------------------------------------------------------------------- the rules

def invariants(ctx: Context):
    d = ctx.d
    ds = []
    for mid in sorted(d.get('materials', {})):
        v = _data(d['materials'][mid])
        if v is not None and 'conductivity' in v and 'resistance' in v:                  # 2.1.1
            ds.append(ctx.diag('FS-THRM-INV-001', [mid]))
    mats = d.get('materials', {})

    def refs(v, floor):
        f = v.get('floor', {}) if floor else v
        out = [lay['material'] for lay in f.get('layers', []) if 'material' in lay]
        if 'framing' in f:
            out.append(f['framing']['material'])
        return out
    carriers = [(tid, _data(t), False) for tid, t in d.get('types', {}).items()] + \
               [(rid, _data(r), False) for rid, r in d.get('roofs', {}).items()] + \
               [(rid, _data(r), True) for rid, r in d.get('rooms', {}).items()]
    for eid, v, floor in carriers:
        if v is not None and any(m not in mats for m in refs(v, floor)):                  # 2.2.1
            ds.append(ctx.diag('FS-THRM-INV-002', [eid]))
    return ds


def lints(ctx: Context):
    ds = []
    for _, eid, layers, framing in assemblies(ctx.d):
        if framing is not None and not any(lay['function'] == 'core' for lay in layers):
            ds.append(ctx.diag('FS-THRM-LINT-001', [eid]))
        if derive_assembly(ctx.d, layers, None)['clear']['resistance'] is None:
            ds.append(ctx.diag('FS-THRM-LINT-002', [eid]))
    return ds


def derive(ctx: Context) -> dict:
    out = {'wallTypes': {}, 'roofs': {}, 'floors': {}}
    for section, eid, layers, framing in assemblies(ctx.d):
        out[section][eid] = derive_assembly(ctx.d, layers, framing)
    return out

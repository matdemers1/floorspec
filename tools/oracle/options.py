"""Design options (Core 0.3, chapter 19): option sets and options, membership, designs and their
views, the checked designs, the option invariants and lint, and the derived `options` member.

A **design** chooses one option of every option set; the **primary design** chooses every set's
primary (19.3). The **view** of a design is the document as seen in it: every element that is in
an option the design does not choose is gone, and so are `optionSets`, `options` and every
remaining element's `option` member - a document without design options, to which chapters 1-17
apply as they stand. The **checked designs** are the primary design and, for every option that is
not its set's primary, its **option design**: the primary design with that one option chosen
instead (19.5). A document is valid when each checked design's view is, and every diagnostic found
in an option design that the primary design does not also have is reported with `design`, the
option's ID.
"""

from __future__ import annotations

import copy
from collections import Counter

from . import canon

# 19.2: the collections whose elements may be in an option; extension elements may be too
OPTIONAL = ('junctions', 'walls', 'separators', 'openings', 'rooms', 'slabs', 'roofs', 'stairs')
# 19.6.3: the derived members keyed by element ID that `affected` compares, beside the program's items
NOT_COMPARED = ('program', 'options', 'extensions')


def present(d: dict) -> bool:
    """Whether a (0.3) document has design options at all."""
    return bool(d.get('optionSets')) or bool(d.get('options'))


def _ext_collections(d: dict):
    """(collection object) of every extension collection of a 0.3 document (12.5)."""
    if d.get('floorspec') != '0.3':
        return []
    out = []
    for data in d.get('extensions', {}).values():
        if isinstance(data, dict) and isinstance(data.get('collections'), dict):
            out.extend(c for c in data['collections'].values() if isinstance(c, dict))
    return out


def membership(d: dict) -> dict:
    """element ID -> the option it is in, for every element in an option (19.2)."""
    out = {}
    for c in OPTIONAL:
        for eid, e in d.get(c, {}).items():
            if 'option' in e:
                out[eid] = e['option']
    for coll in _ext_collections(d):
        for eid, el in coll.items():
            if isinstance(el, dict) and 'option' in el:
                out[eid] = el['option']
    return out


def primary_design(d: dict) -> dict:
    return {sid: s['primary'] for sid, s in d.get('optionSets', {}).items()}


def checked_designs(d: dict):
    """(tag, design) of every checked design (19.5): the primary design, tagged None, then every
    option design, tagged with its option's ID, in order of that ID."""
    primary = primary_design(d)
    out = [(None, primary)]
    for oid in sorted(d.get('options', {})):
        sid = d['options'][oid]['set']
        if primary.get(sid) != oid:
            out.append((oid, {**primary, sid: oid}))
    return out


def view(d: dict, design: dict) -> dict:
    """19.3: the document as seen in a design."""
    chosen = set(design.values())

    def keep(e):
        return 'option' not in e or e['option'] in chosen

    def strip(e):
        return {k: v for k, v in e.items() if k != 'option'}

    v = {k: x for k, x in d.items() if k not in ('optionSets', 'options')}
    for c in OPTIONAL:
        if c in d:
            v[c] = {eid: strip(e) for eid, e in d[c].items() if keep(e)}
    if d.get('floorspec') == '0.3' and isinstance(d.get('extensions'), dict):
        exts = copy.deepcopy(d['extensions'])
        for data in exts.values():
            if isinstance(data, dict) and isinstance(data.get('collections'), dict):
                for cname, coll in data['collections'].items():
                    if isinstance(coll, dict):
                        data['collections'][cname] = {eid: (strip(el) if isinstance(el, dict) else el)
                                                      for eid, el in coll.items()
                                                      if not isinstance(el, dict) or keep(el)}
        v['extensions'] = exts
    return v


def resolve(d: dict, design) -> dict | None:
    """A design given as an evaluation input (19.6): an object naming option sets of the document,
    each mapped to one of its own options; every set it does not name takes its primary. None when
    the input is not such an object."""
    if not isinstance(design, dict):
        return None
    sets, opts = d.get('optionSets', {}), d.get('options', {})
    out = primary_design(d)
    for sid, oid in design.items():
        if sid not in sets or not isinstance(oid, str) or oid not in opts or opts[oid]['set'] != sid:
            return None
        out[sid] = oid
    return out


def tag_of(d: dict, design: dict):
    """The checked design a design is - None for the primary design, an option's ID for its option
    design - or False for a design that is not a checked one."""
    primary = primary_design(d)
    differ = [design[s] for s in sorted(design) if design[s] != primary[s]]
    if not differ:
        return None
    return differ[0] if len(differ) == 1 else False


# ------------------------------------------------------------------------------ validation

def invariants(d: dict, refs, diag):
    """FS-INV-1101 and FS-INV-1102 (19.1.2, 19.4.1), on the document, once its references resolve."""
    ds = []
    opts = d.get('options', {})
    for sid, s in sorted(d.get('optionSets', {}).items()):
        if opts[s['primary']]['set'] != sid:
            ds.append(diag('FS-INV-1101', [sid, s['primary']]))
    m = membership(d)
    seen = set()
    for _, eid, target_id, _, _ in refs:
        if eid is None:
            continue
        t = m.get(target_id)
        if t is not None and t != m.get(eid) and (eid, target_id) not in seen:
            seen.add((eid, target_id))
            ds.append(diag('FS-INV-1102', [eid, target_id]))
    return ds


def merge(per):
    """19.5.2: per = [(tag, diagnostics)], the primary design first. Every diagnostic of the primary
    design is reported as it is; one of an option design is reported, with `design`, unless the
    primary design has one with the same code, severity and elements not already matched."""
    if not per:
        return []
    base = per[0][1]
    out = list(base)

    def key(x):
        return (x['code'], x['severity'], tuple(x['elements']))
    for tag, ds in per[1:]:
        pool = Counter(key(x) for x in base)
        for x in ds:
            k = key(x)
            if pool[k] > 0:
                pool[k] -= 1
            else:
                out.append({**x, 'design': tag})
    return out


def lints(d: dict, diag):
    """FS-LINT-018 (19.8): an option set with one option."""
    count = Counter(o['set'] for o in d.get('options', {}).values())
    return [diag('FS-LINT-018', [sid]) for sid in sorted(d.get('optionSets', {})) if count[sid] == 1]


# ------------------------------------------------------------------------------ derived values

def affected(a: dict, b: dict) -> list[str]:
    """19.6.3: the IDs present in both designs' derived values whose values there differ."""
    ids = set()

    def compare(x, y):
        for i in x.keys() & y.keys():
            if canon.jcs(x[i]) != canon.jcs(y[i]):
                ids.add(i)
    for k, va in a.items():
        if k in NOT_COMPARED or not isinstance(va, dict):
            continue
        vb = b.get(k)
        if isinstance(vb, dict):
            compare(va, vb)
    pa, pb = a.get('program'), b.get('program')
    if isinstance(pa, dict) and isinstance(pb, dict):
        compare(pa.get('items', {}), pb.get('items', {}))
    return sorted(ids)


def derived(d: dict, design: dict, derived_by: dict) -> dict:
    """19.6.3: the derived `options` member. derived_by maps the tag of every checked design to its
    derived values."""
    m = membership(d)
    primary = primary_design(d)
    base = derived_by[None]
    out = {}
    for sid in sorted(d.get('optionSets', {})):
        opts = {}
        for oid in sorted(o for o, x in d.get('options', {}).items() if x['set'] == sid):
            dv = base if oid == primary[sid] else derived_by[oid]
            opts[oid] = {'members': sorted(e for e, o in m.items() if o == oid),
                         'rooms': {r: v['area'] for r, v in sorted(dv['rooms'].items())},
                         'affected': affected(base, dv)}
        out[sid] = {'chosen': design[sid], 'options': opts}
    return out

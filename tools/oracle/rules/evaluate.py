"""The evaluator of Floorspec Rules 0.1 (spec/rules): a request, a document and the known extensions
in; the report of chapter 9 out, as bytes (9.8). The steps are those of 1.3, in order."""

from __future__ import annotations

import json
from fractions import Fraction

from .. import canon, plane, registry as reg
from ..derive import Doc
from ..ext import official
from ..jsonparse import Malformed, parse
from .. import options
from ..validate import READER_03, check
from . import display, structure
from .context import Ctx
from .measures import DEFERRED, MEASURES, a_coll, a_ext, a_function, compute, get, PURPOSES

DEFAULT_PROFILE = {
    'floorspecRules': '0.1', 'name': 'Model Codes (latest)',
    'adopts': [{'code': 'IFGC', 'edition': '2024'}, {'code': 'IMC', 'edition': '2024'}, {'code': 'IPC', 'edition': '2024'},
               {'code': 'IRC', 'edition': '2024'}, {'code': 'NEC', 'edition': '2026'}],
}
SEVERITY = {'FS-RULES-008': 'info', 'FS-RULES-009': 'info', 'FS-RULES-010': 'warning', 'FS-RULES-011': 'warning'}
ALL_OFFICIAL = ('FS_electrical', 'FS_plumbing', 'FS_mechanical', 'FS_lowvoltage')

# 3.5: candidate sets by subject kind, their arguments, and the kind of their candidates
CANDIDATES = {
    ('room', 'openings'): ({'to': lambda v: v in ('outside', 'any')}, 'opening'),
    ('room', 'elements'): ({'extension': a_ext, 'collection': a_coll}, 'element'),
    ('opening', 'envelopes'): ({'purpose': lambda v: v in PURPOSES}, 'envelope'),
    ('element', 'envelopes'): ({'purpose': lambda v: v in PURPOSES}, 'envelope'),
    ('level', 'rooms'): ({'function': a_function}, 'room'),
    ('level', 'elements'): ({'extension': a_ext, 'collection': a_coll}, 'element'),
}
NUMERIC = ('length', 'count', 'integer')


def diag(code, **members):
    return {'code': code, 'severity': SEVERITY.get(code, 'error'), **members}


def _diag_key(d):
    def part(k):
        return (0,) if k not in d else (1, d[k] if isinstance(d[k], int) else canon.utf16_key(d[k]))
    return (d['code'], part('packIndex'), part('pack'), part('rule'))


def k16(s):
    return canon.utf16_key(s)


# ============================================================================ typing (3.9)
def _value_ok(typ, op, v) -> bool:
    def num(x):
        return structure.is_int(x)
    if typ in NUMERIC or typ == 'area':
        if op in ('<', '<=', '>', '>=', '=', '!='):
            return num(v)
        if op == 'in' and typ != 'area':
            return isinstance(v, list) and len(v) >= 1 and all(num(x) for x in v)
        return False
    if typ == 'term':
        if op in ('=', '!='):
            return isinstance(v, str)
        return op == 'in' and isinstance(v, list) and len(v) >= 1 and all(isinstance(x, str) for x in v)
    if typ == 'boolean':
        return op in ('=', '!=') and isinstance(v, bool)
    if typ == 'terms':
        return op == 'has' and isinstance(v, str)
    return False


def type_rule(rule):
    """(well typed, uses a deferred measure, the extensions it reads)."""
    a = rule['applies']
    subj = a['to']
    state = {'ok': True, 'deferred': False, 'reads': set()}
    if ('extension' in a or 'collection' in a) and subj != 'element':
        state['ok'] = False
    if 'collection' in a and 'extension' not in a:
        state['ok'] = False
    subj_ext = a.get('extension') if subj == 'element' else None

    def test(t, kind, ext):
        if 'measure' in t:
            name, args = t['measure'], t.get('args', {})
            if name in DEFERRED:
                state['deferred'] = True
                return
            m = get(name, kind)
            if m is None or not m.args_ok(args):
                state['ok'] = False
                return
            if not _value_ok(m.type_of(args), t['op'], t['value']):
                state['ok'] = False
            state['reads'] |= m.reads(args)
            if name == 'elementMember':
                if ext is None:
                    state['ok'] = False
                else:
                    state['reads'].add(ext)
            return
        for k in ('all', 'any'):
            if k in t:
                for x in t[k]:
                    test(x, kind, ext)
                return
        test(t['not'], kind, ext)

    if 'where' in a:
        test(a['where'], subj, subj_ext)
    for e in rule.get('exceptions', []):
        test(e['when'], subj, subj_ext)
    sel = rule.get('select')
    if sel is not None:
        spec = CANDIDATES.get((subj, sel['from']))
        args = sel.get('args', {})
        if spec is None:
            state['ok'] = False
            kind, cext = None, None
        else:
            argspec, kind = spec
            if not set(args) <= set(argspec) or not all(argspec[k](v) for k, v in args.items()) \
                    or ('collection' in args and 'extension' not in args):
                state['ok'] = False
            cext = args.get('extension') if sel['from'] == 'elements' else None
        if kind is not None:
            if 'where' in sel:
                test(sel['where'], kind, cext)
            test(rule['requirement'], kind, cext)
    else:
        test(rule['requirement'], subj, subj_ext)
    if rule['provenance']['edition'] != rule['citation']['edition']:
        state['ok'] = False
    return state['ok'], state['deferred'], state['reads']


# ============================================================================ tests (3.8)
def _compare(typ, value, op, t) -> bool:
    if value is None:
        return op == '!='
    if typ == 'terms':
        return t in value
    if op == 'in':
        return value in t
    if typ in NUMERIC or typ == 'area':
        v = Fraction(value)
        return {'<': v < t, '<=': v <= t, '>': v > t, '>=': v >= t, '=': v == t, '!=': v != t}[op]
    return {'=': value == t, '!=': value != t}[op]


def _json_value(typ, v):
    if v is None:
        return None
    if typ == 'area':
        return plane.area_string(int(2 * v))
    return v


class Evaluation:
    def __init__(self, ctx: Ctx):
        self.ctx = ctx
        self.cache = {}

    def result(self, name, target, args):
        """4.7: the measure result, and the internal value."""
        key = (name, json.dumps(target, sort_keys=True), json.dumps(args, sort_keys=True))
        if key not in self.cache:
            m = MEASURES[(name, target['kind'])]
            value, involved = compute(self.ctx, name, target, args)
            typ = m.type_of(args)
            r = {'type': typ, 'value': _json_value(typ, value), 'display': display.value(typ, value, self.ctx.units, args.get('unit'))}
            if m.involved:
                r['involved'] = sorted(involved, key=k16)                      # 9.7: UTF-16 code units
            self.cache[key] = (r, value)
        return self.cache[key]

    def test(self, t, target):
        """(holds, [measured condition, ...]) - every leaf evaluated, depth first (9.3)."""
        if 'measure' in t:
            args = t.get('args', {})
            r, value = self.result(t['measure'], target, args)
            holds = _compare(r['type'], value, t['op'], t['value'])
            mc = {'target': target, 'measure': t['measure'], **r, 'op': t['op'], 'threshold': t['value'],
                  'thresholdDisplay': display.threshold(r['type'], t['op'], t['value'], self.ctx.units, args.get('unit')),
                  'holds': holds}
            if 'args' in t:
                mc['args'] = t['args']
            return holds, [mc]
        for k in ('all', 'any'):
            if k in t:
                out, leaves = [], []
                for x in t[k]:
                    h, ls = self.test(x, target)
                    out.append(h)
                    leaves.extend(ls)
                return (all(out) if k == 'all' else any(out)), leaves
        h, ls = self.test(t['not'], target)
        return (not h), ls

    def holds(self, t, target) -> bool:
        return self.test(t, target)[0]

    # ------------------------------------------------------------ subjects and candidates
    def subjects(self, a):
        doc, ctx = self.ctx.doc, self.ctx
        kind = a['to']
        if kind == 'room':
            ids = sorted(doc.rooms, key=k16)
        elif kind == 'opening':
            ids = sorted(doc.openings, key=k16)
        elif kind == 'level':
            ids = sorted(doc.levels, key=k16)
        elif kind == 'stair':
            ids = sorted(doc.stairs, key=k16)
        else:
            ids = sorted((e for e, (x, c, _) in ctx.ext.items()
                          if ('extension' not in a or x == a['extension']) and ('collection' not in a or c == a['collection'])), key=k16)
        targets = [{'kind': kind, 'id': i} for i in ids]
        return [t for t in targets if 'where' not in a or self.holds(a['where'], t)]

    def candidates(self, subject, sel):
        ctx, doc = self.ctx, self.ctx.doc
        args = sel.get('args', {})
        sid = subject['id']
        frm = sel['from']
        if frm == 'openings':
            lv = ctx.level(doc.rooms[sid]['level'])
            face = lv.room_face[sid]
            out = []
            for oid in sorted(doc.openings, key=k16):
                hs = lv.half_edges(doc.openings[oid]['wall'])
                owners = [lv.owner.get(h) for h in hs]
                if face not in owners:
                    continue
                if args.get('to', 'any') == 'outside' and None not in owners:
                    continue
                out.append({'kind': 'opening', 'id': oid})
        elif frm == 'envelopes':
            out = [{'kind': 'envelope', 'id': sid, 'envelope': n} for n in ctx.envelopes_of(sid)
                   if 'purpose' not in args or ctx.derived['clearances'][sid][n]['purpose'] == args['purpose']]
        elif frm == 'rooms':
            out = [{'kind': 'room', 'id': r} for r in sorted(doc.rooms, key=k16)
                   if doc.rooms[r]['level'] == sid and ('function' not in args or doc.rooms[r].get('function', 'unspecified') == args['function'])]
        else:
            def inside(e):
                el = ctx.ext[e][2]
                return ctx.room_of(e) == sid if subject['kind'] == 'room' else el['fallback']['level'] == sid
            out = [{'kind': 'element', 'id': e} for e in sorted(ctx.ext, key=k16)
                   if inside(e) and ('extension' not in args or ctx.ext[e][0] == args['extension'])
                   and ('collection' not in args or ctx.ext[e][1] == args['collection'])]
        return [c for c in out if 'where' not in sel or self.holds(sel['where'], c)]

    # ------------------------------------------------------------ shapes (9.4)
    def shape(self, t):
        d, k = self.ctx.derived, t['kind']
        if k == 'room':
            r = d['rooms'][t['id']]
            return {'kind': 'polygon', 'outer': r['outer'], 'holes': r['holes']}
        if k == 'opening':
            o = d['openings'][t['id']]
            return {'kind': 'segment', 'points': [o['start'], o['end']]}
        if k == 'element':
            return {'kind': 'polygon', 'outer': d['fallbacks'][t['id']]['footprint'], 'holes': []}
        if k == 'envelope':
            return {'kind': 'polygon', 'outer': d['clearances'][t['id']][t['envelope']]['footprint'], 'holes': []}
        if k == 'stair':                                                  # 9.4: its box, in plan
            (x0, y0, _), (x1, y1, _) = d['stairs'][t['id']]['box']['min'], d['stairs'][t['id']]['box']['max']
            return {'kind': 'polygon', 'outer': [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], 'holes': []}
        if k == 'wall':
            w = self.ctx.doc.walls[t['id']]
            ring = plane.least_first(self.ctx.level(w['level']).g.outline(t['id']))
            return {'kind': 'polygon', 'outer': [list(p) for p in ring], 'holes': []}
        return None

    def finding(self, pack, rid, rule, subject, cands, measured):
        ctx = self.ctx
        c = rule['citation']
        ids = {subject['id']} | {x['id'] for x in cands}
        involved = sorted({i for mc in measured for i in mc.get('involved', [])}, key=k16)
        ids |= set(involved)
        shapes, drawn = [], set()
        for t in [subject] + cands:
            key = (t['kind'], t['id'], t.get('envelope'))
            s = self.shape(t)
            if s is not None and key not in drawn:
                drawn.add(key)
                shapes.append(s)
        for i in involved:                                              # 9.4: every involved ID with a shape
            kind = ('wall' if i in ctx.doc.walls else 'element' if i in ctx.ext else 'opening' if i in ctx.doc.openings
                    else 'room' if i in ctx.doc.rooms else None)
            if kind is None or (kind, i, None) in drawn:
                continue
            drawn.add((kind, i, None))
            shapes.append(self.shape({'kind': kind, 'id': i}))
        msg = f"{subject['id']} may not meet {c['code']} {c['edition']} {c['section']} ({rule['title']})."
        if rule['severity'] == 'check':
            msg += ' Check it with a professional or the authority having jurisdiction.'
        elif rule['severity'] == 'note':
            msg += ' This is for information.'
        f = {'pack': pack['name'], 'version': pack['version'], 'rule': rid, 'title': rule['title'], 'citation': c,
             'severity': rule['severity'], 'subject': subject, 'measures': measured,
             'elements': sorted(ids, key=k16), 'location': {'level': ctx.target_level(subject), 'shapes': shapes},
             'message': msg}
        if 'select' in rule:
            f['candidates'] = cands
        return f

    def evaluate_rule(self, pack, rid, rule):
        """(subjects, exempt, findings)."""
        subjects = self.subjects(rule['applies'])
        exempt, findings = 0, []
        sel = rule.get('select')
        for s in subjects:
            if any(self.holds(e['when'], s) for e in rule.get('exceptions', [])):
                exempt += 1
                continue
            if sel is not None:
                cands = self.candidates(s, sel)
                outs = [self.test(rule['requirement'], c) for c in cands]
                passed = any(h for h, _ in outs) if sel['need'] == 'any' else all(h for h, _ in outs)
                measured = [mc for _, ls in outs for mc in ls]
            else:
                cands = []
                passed, measured = self.test(rule['requirement'], s)
            if not passed:
                findings.append(self.finding(pack, rid, rule, s, cands, measured))
        return len(subjects), exempt, findings


# ============================================================================ profiles (10)
def editions_in_force(profile):
    as_of = profile.get('asOf')
    best = {}
    for a in profile['adopts']:
        eff = a.get('effective')
        if as_of is not None and eff is not None and eff > as_of:
            continue
        cur = best.get(a['code'])
        if cur is None or (eff is not None and (cur[0] is None or eff > cur[0])):
            best[a['code']] = (eff, a['edition'])
    return {k: v[1] for k, v in best.items()}


def applying_amendments(profile):
    as_of = profile.get('asOf')
    return [a for a in profile.get('amendments', [])
            if as_of is None or 'effective' not in a or a['effective'] <= as_of]


# ============================================================================ the pipeline (1.3)
def _report(**members):
    base = {'floorspecRules': '0.1', 'notice': structure.NOTICE, 'diagnostics': [], 'evaluated': [], 'notEvaluated': [],
            'coverage': [], 'findings': []}
    base.update(members)
    return base


def check_document(document: bytes, registry: bytes | None, design=None):
    return check(document, READER_03, registry, official.implemented(*ALL_OFFICIAL), design=design)


def design_doc(document: bytes, design):
    """1.2: the document as seen in the request's design (Core 19.3) - the primary design without one."""
    d = _parsed(document)
    if not options.present(d):
        return d
    chosen = options.primary_design(d) if design is None else options.resolve(d, design)
    return options.view(d, chosen)


def evaluate(document: bytes, registry: bytes | None, request: bytes) -> dict:
    # 1. the request
    try:
        req, codes = parse(request)
    except Malformed:
        req, codes = None, ['FS-JSON-001']
    if codes or not structure.request(req):
        return _report(diagnostics=[diag('FS-RULES-001')])
    units = req.get('units', 'imperial')
    # 2. the profile
    profile = req.get('profile', DEFAULT_PROFILE)
    if not structure.profile_ok(profile):
        return _report(units=units, diagnostics=[diag('FS-RULES-002')])
    # 3. the document
    result, _, _ = check_document(document, registry, req.get('design'))
    if not result['valid'] or 'derived' not in result:              # 1.2.1, 1.2.2: Core derives nothing for the design
        return _report(units=units, profile=profile['name'], diagnostics=[diag('FS-RULES-003')])
    ds = []
    # 4. the packs
    packs = req['packs']
    valid = [i for i, p in enumerate(packs) if structure.pack(p)]
    ds += [diag('FS-RULES-004', packIndex=i) for i in range(len(packs)) if i not in valid]
    usable = set(valid)
    for i in valid:
        if sum(1 for j in valid if packs[j]['name'] == packs[i]['name']) > 1:
            ds.append(diag('FS-RULES-005', packIndex=i))
            usable.discard(i)
        if any(structure.assures(t) for t in structure.pack_text(packs[i])):
            ds.append(diag('FS-RULES-006', packIndex=i))
            usable.discard(i)
    usable = [packs[i] for i in sorted(usable)]
    # 5. the profile's packs and amendments
    if 'packs' in profile:
        selected = []
        for sel in profile['packs']:
            hits = [p for p in usable if p['name'] == sel['name'] and reg.satisfies(p['version'], sel['version'])]
            if not hits:
                ds.append(diag('FS-RULES-010', pack=sel['name']))
            selected += [p for p in hits if p not in selected]
    else:
        selected = list(usable)
    withdrawn = set()
    for am in applying_amendments(profile):
        for w in am['withdraws']:
            withdrawn.add((w['pack'], w['rule']))
            if not any(p['name'] == w['pack'] and w['rule'] in p['rules'] for p in usable):
                ds.append(diag('FS-RULES-011', pack=w['pack'], rule=w['rule']))
    in_force = editions_in_force(profile)
    # 6. each rule; 7. its subjects
    doc = Doc(design_doc(document, req.get('design')))
    derived = result['derived']
    ctx = Ctx(doc, derived, set(derived.get('extensions', {})), units)
    ev = Evaluation(ctx)
    evaluated, not_evaluated, findings, coverage = [], [], [], []
    for p in usable:
        for rid in sorted(p['rules'], key=k16):
            rule = p['rules'][rid]
            base = {'pack': p['name'], 'version': p['version'], 'rule': rid}
            if p not in selected:
                not_evaluated.append({**base, 'reason': 'profile'})
                continue
            ok, deferred, reads = type_rule(rule)
            if not ok:
                ds.append(diag('FS-RULES-007', pack=p['name'], rule=rid))
                not_evaluated.append({**base, 'reason': 'invalid'})
                continue
            if deferred:
                ds.append(diag('FS-RULES-008', pack=p['name'], rule=rid))
                not_evaluated.append({**base, 'reason': 'deferred'})
                continue
            c = rule['citation']
            if in_force.get(c['code']) != c['edition']:
                not_evaluated.append({**base, 'reason': 'edition'})
                continue
            if (p['name'], rid) in withdrawn:
                not_evaluated.append({**base, 'reason': 'withdrawn'})
                continue
            if not reads <= ctx.evaluated:
                ds.append(diag('FS-RULES-009', pack=p['name'], rule=rid))
                not_evaluated.append({**base, 'reason': 'extension'})
                continue
            n, exempt, fs = ev.evaluate_rule(p, rid, rule)
            evaluated.append({**base, 'citation': c, 'subjects': n, 'exempt': exempt, 'findings': len(fs)})
            findings += fs
        if p in selected:
            for cv in p.get('coverage', []):
                if in_force.get(cv['code']) == cv['edition']:
                    coverage.append({'pack': p['name'], **cv})
    rk = lambda e: (k16(e['pack']), k16(e['rule']))     # noqa: E731
    evaluated.sort(key=rk)
    not_evaluated.sort(key=rk)
    coverage.sort(key=lambda e: (k16(e['pack']), k16(e['code']), k16(e['edition']), k16(e['section']), k16(e['status']),
                                 (0,) if 'note' not in e else (1, k16(e['note']))))
    findings.sort(key=lambda f: (k16(f['pack']), k16(f['rule']), k16(f['subject']['id'])))
    return _report(units=units, profile=profile['name'], hash=result['hash'], diagnostics=sorted(ds, key=_diag_key),
                   evaluated=evaluated, notEvaluated=not_evaluated, coverage=coverage, findings=findings)


def _parsed(document: bytes):
    value, _ = parse(document)
    return value


def report_bytes(report: dict) -> bytes:
    """9.8: as Core 9.2 step 2 writes a value."""
    return (canon.pretty(report) + '\n').encode('utf-8')


def call_measures(document: bytes, registry: bytes | None, calls: dict) -> dict:
    """The measure results (4.7) of a measure test's calls."""
    result, _, _ = check_document(document, registry)
    assert result['valid'], result['diagnostics']
    doc = Doc(_parsed(document))
    derived = result['derived']
    ctx = Ctx(doc, derived, set(derived.get('extensions', {})), calls.get('units', 'imperial'))
    ev = Evaluation(ctx)
    out = []
    for c in calls['calls']:
        m = get(c['measure'], c['target']['kind'])
        assert m is not None and m.args_ok(c.get('args', {})), c
        out.append(ev.result(c['measure'], c['target'], c.get('args', {}))[0])
    return {'results': out}

"""Helpers for tools/oracle/author.py and author02.py, the scripts the Core suites are written with.

A test is declared with t(group, slug, description, covers, input, diagnostics). The diagnostics
are written by hand; write_all() asks the oracle for its own and reports any disagreement, and
takes hash, derived and canonical.json from the oracle. Directories are numbered in declaration
order within a group, so add new tests at the end of their group's section. A Core 0.2 test may
also give the known extensions (registry=[entries]), written to registry.json.
"""
import copy  # noqa: F401  (re-exported for author.py)
import json
import os
import shutil
import sys

from tools.oracle.report import dumps
from tools.oracle.validate import READER_01, SEVERITY, check

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

SUITE = os.path.join(REPO, 'conformance', 'core', '0.1')
MM = 1280
FT = 390144
IN = 32512
H = 2700 * MM          # level height
T100 = 100 * MM        # 128000

TESTS = []


def fmt(v, depth=0, indent=2):
    """Insertion-ordered JSON with points inline - deliberately not the canonical form."""
    pad = ' ' * (indent * depth)
    inner = ' ' * (indent * (depth + 1))
    if isinstance(v, dict):
        if not v:
            return '{}'
        return '{\n' + ',\n'.join(f'{inner}{json.dumps(k, ensure_ascii=False)}: {fmt(x, depth + 1, indent)}' for k, x in v.items()) + '\n' + pad + '}'
    if isinstance(v, list):
        if not v:
            return '[]'
        if all(not isinstance(x, (dict, list)) for x in v):
            return '[' + ', '.join(json.dumps(x, ensure_ascii=False) for x in v) + ']'
        if all(isinstance(x, list) and all(not isinstance(y, (dict, list)) for y in x) for x in v) and len(v) <= 6:
            return '[' + ', '.join(fmt(x) for x in v) + ']'
        return '[\n' + ',\n'.join(inner + fmt(x, depth + 1, indent) for x in v) + '\n' + pad + ']'
    return json.dumps(v, ensure_ascii=False)


def doc(**members):
    d = {'floorspec': '0.1', 'project': {'name': 'Conformance'}}
    d.update(members)
    return d


def level_doc(**members):
    """A project with one building B1 and one level L1, and the 100 mm wall type WT."""
    d = doc(buildings={'B1': {}}, levels={'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
            types={'WT': {'kind': 'wallType', 'layers': [{'thickness': T100, 'function': 'core'}]}})
    for k, v in members.items():
        if k in d and isinstance(d[k], dict) and isinstance(v, dict):
            d[k] = {**d[k], **v}
        else:
            d[k] = v
    return d


def J(x, y, level='L1', **kw):
    return {'level': level, 'position': [x, y], **kw}


def W(s, e, level='L1', type='WT', **kw):
    w = {'level': level, 'start': s, 'end': e}
    if type is not None:
        w['type'] = type
    w.update(kw)
    return w


def S(s, e, level='L1'):
    return {'level': level, 'start': s, 'end': e}


def R(x, y, level='L1', **kw):
    return {'level': level, 'anchor': [x, y], **kw}


def box(p, x0, y0, x1, y1, level='L1', **wallkw):
    """A closed rectangle drawn clockwise (exterior sides out): junctions pJ1..pJ4, walls pW1..pW4."""
    js = {f'{p}J1': J(x0, y0, level), f'{p}J2': J(x0, y1, level), f'{p}J3': J(x1, y1, level), f'{p}J4': J(x1, y0, level)}
    ws = {f'{p}W1': W(f'{p}J1', f'{p}J2', level, **wallkw), f'{p}W2': W(f'{p}J2', f'{p}J3', level, **wallkw),
          f'{p}W3': W(f'{p}J3', f'{p}J4', level, **wallkw), f'{p}W4': W(f'{p}J4', f'{p}J1', level, **wallkw)}
    return js, ws


def cov(*ids):
    return [i if i.startswith('FS-') else f'FS-CORE-{i}' for i in ids]


def t(group, slug, description, covers, inp, diags=(), raw=None, registry=None, registry_raw=None):
    """diags: list of (code, [elements]) - written by hand, cross-checked by the oracle."""
    TESTS.append(dict(group=group, slug=slug, description=description, covers=cov(*covers),
                      inp=inp, raw=raw, registry=registry, registry_raw=registry_raw,
                      diags=[{'code': c, 'severity': SEVERITY.get(c, 'error'), 'elements': sorted(e)}
                             for c, e in diags]))


def write_all(only_group=None, prune=False, tests=None, suite=None, reader=READER_01):
    tests = TESTS if tests is None else tests
    suite = SUITE if suite is None else suite
    counters = {}
    failures = 0
    seen_dirs = set()
    for tc in tests:
        g = tc['group']
        counters[g] = counters.get(g, 0) + 1
        name = f"{counters[g]:03d}-{tc['slug']}"
        d = os.path.join(suite, g, name)
        seen_dirs.add(d)
        if only_group and g != only_group:
            continue
        os.makedirs(d, exist_ok=True)
        data = tc['raw'] if tc['raw'] is not None else (fmt(tc['inp']) + '\n').encode('utf-8')
        with open(os.path.join(d, 'input.json'), 'wb') as f:
            f.write(data)
        with open(os.path.join(d, 'test.json'), 'w') as f:
            f.write(json.dumps({'description': tc['description'], 'covers': tc['covers']}, indent=2, ensure_ascii=False) + '\n')
        registry = tc.get('registry_raw')
        if registry is None and tc.get('registry') is not None:
            registry = (fmt(tc['registry']) + '\n').encode('utf-8')
        rp = os.path.join(d, 'registry.json')
        if registry is not None:
            with open(rp, 'wb') as f:
                f.write(registry)
        elif os.path.exists(rp):
            os.remove(rp)
        result, canonical, notes = check(data, reader, registry)
        hand = sorted(tc['diags'], key=lambda x: (x['code'], x['elements']))
        valid = not any(x['severity'] == 'error' for x in hand)
        if hand != result['diagnostics'] or valid != result['valid']:
            failures += 1
            print(f'MISMATCH {g}/{name}\n  hand   {json.dumps(hand)}\n  oracle {json.dumps(result["diagnostics"])}')
            for n in notes[:5]:
                print('  note', n)
        exp = {'valid': valid, 'diagnostics': hand}
        if 'hash' in result:
            exp['hash'] = result['hash']
            exp['derived'] = result['derived']
        with open(os.path.join(d, 'expected.json'), 'w') as f:
            f.write(dumps(exp))
        cp = os.path.join(d, 'canonical.json')
        if canonical is not None:
            with open(cp, 'wb') as f:
                f.write(canonical)
        elif os.path.exists(cp):
            os.remove(cp)
    # remove directories no test declares (only when asked: --prune)
    if prune and not only_group:
        for g in os.listdir(suite):
            gp = os.path.join(suite, g)
            if os.path.isdir(gp):
                for n in os.listdir(gp):
                    if os.path.join(gp, n) not in seen_dirs:
                        print('removing', os.path.join(gp, n))
                        shutil.rmtree(os.path.join(gp, n))
    print(f'{len(tests)} tests, {failures} mismatches')
    return failures

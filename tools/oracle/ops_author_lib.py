"""Helpers for tools/oracle/ops_author.py and ops_author02.py, the scripts the Floorspec Ops 0.1 and
0.2 conformance suites are written with.

A test is declared with T(group, slug, description, covers, a, request, status, diags, check).
`status` and `diags` are written by hand; write_all() asks the oracle for its own and reports any
disagreement. `check`, when given, is a hand-written assertion about the result (with document A as its `_a`) - the resolved
integers, where a junction ends up, which wall an opening is on - run against the oracle's output,
so that the values that matter are checked by a person's arithmetic, not only by the oracle.
hash, created, removed, resolved, inverse and output.json come from the oracle, and every
committed test is checked for 1.3.1, 1.3.2, 1.4.1 and 1.6.1 (tools/oracle/ops/suite.py).

Directories are numbered in declaration order within a group: add new tests at the end of their
group's section. write_all() writes the Ops 0.1 suite with the Ops 0.1 oracle unless it is given
another list of tests, suite directory and draft (ops_author02.py does).
"""
import copy  # noqa: F401  (re-exported)
import json
import os
import shutil
import sys

from tools.oracle.author_lib import fmt
from tools.oracle.jsonparse import parse
from tools.oracle.ops.engine import apply
from tools.oracle.ops.suite import dumps, expected_view, properties
from tools.oracle.ops.version import OPS_01
from tools.oracle.validate import SEVERITY

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
SUITE = os.path.join(REPO, 'conformance', 'ops', '0.1')

MM = 1280
IN = 32512
FT = 390144
H = 2700 * MM                  # level height
T100 = 100 * MM                # the wall type's thickness
DOOR_W, DOOR_H = 36 * IN, 80 * IN

TESTS = []


def doc(**members):
    d = {'floorspec': '0.1', 'project': {'name': 'Conformance'}}
    d.update(members)
    return d


def level_doc(**members):
    """Building B1, level L1, the 100 mm wall type WT and the 36-inch door type T-door-36."""
    d = doc(buildings={'B1': {}}, levels={'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
            types={'WT': {'kind': 'wallType', 'layers': [{'thickness': T100, 'function': 'core'}]},
                   'T-door-36': {'kind': 'doorType', 'width': DOOR_W, 'height': DOOR_H}})
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


def R(x, y, name=None, level='L1', **kw):
    r = {'level': level, 'anchor': [x, y]}
    if name is not None:
        r['name'] = name
    r.update(kw)
    return r


def box(**members):
    """One 12' x 10' room, Living (R1), drawn clockwise: J1 (0, 0), J2 (0, 10'), J3 (12', 10'),
    J4 (12', 0); W1 west, W2 north, W3 east, W4 south."""
    d = level_doc(
        junctions={'J1': J(0, 0), 'J2': J(0, 10 * FT), 'J3': J(12 * FT, 10 * FT), 'J4': J(12 * FT, 0)},
        walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J1')},
        rooms={'R1': R(6 * FT, 5 * FT, 'Living')})
    for k, v in members.items():
        d[k] = {**d.get(k, {}), **v} if isinstance(v, dict) and isinstance(d.get(k), dict) else v
    return d


def house(**members):
    """A 24' x 12' house of three rooms, drawn clockwise, exterior walls out:

        J3 ------- W3 ------- J4 ------- W4 ------- J5
        |     Pantry (R2)     |                     |
        W2                    W9                    |
        |                     |                     W5
        J2 ------- W10 ------ J8    Dining (R3)     |
        |     Kitchen (R1)    |                     |
        W1                    W8                    |
        |                     |                     |
        J1 ------- W7 ------- J7 ------- W6 ------- J6

    J1 (0, 0), J2 (0, 8'), J3 (0, 12'), J4 (12', 12'), J5 (24', 12'), J6 (24', 0), J7 (12', 0),
    J8 (12', 8'). The Kitchen's east side, W8, continues north as the Pantry's, W9."""
    d = level_doc(
        junctions={'J1': J(0, 0), 'J2': J(0, 8 * FT), 'J3': J(0, 12 * FT), 'J4': J(12 * FT, 12 * FT),
                   'J5': J(24 * FT, 12 * FT), 'J6': J(24 * FT, 0), 'J7': J(12 * FT, 0), 'J8': J(12 * FT, 8 * FT)},
        walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J5'),
               'W5': W('J5', 'J6'), 'W6': W('J6', 'J7'), 'W7': W('J7', 'J1'), 'W8': W('J7', 'J8'),
               'W9': W('J8', 'J4'), 'W10': W('J2', 'J8')},
        rooms={'R1': R(6 * FT, 4 * FT, 'Kitchen', function='kitchen'),
               'R2': R(6 * FT, 10 * FT, 'Pantry', function='storage'),
               'R3': R(18 * FT, 6 * FT, 'Dining', function='dining')})
    for k, v in members.items():
        d[k] = {**d.get(k, {}), **v} if isinstance(v, dict) and isinstance(d.get(k), dict) else v
    return d


def req(*ops, locks=None, retired=None):
    r = {'batch': list(ops)}
    ctx = {}
    if locks is not None:
        ctx['locks'] = locks
    if retired is not None:
        ctx['retired'] = retired
    if ctx:
        r['context'] = ctx
    return r


def cov(*ids):
    return [i if i.startswith('FS-') else f'FS-OPS-{i}' for i in ids]


def T(group, slug, description, covers, a, request, status='committed', diags=(), check=None,
      raw_a=None, raw_req=None, same_as=None):
    """diags: (code, [elements]) pairs, written by hand. same_as: the slug of an earlier test in
    the same group whose output.json must be byte-identical (shorthand / primitive equivalence)."""
    TESTS.append(dict(group=group, slug=slug, description=description, covers=cov(*covers), a=a,
                      request=request, raw_a=raw_a, raw_req=raw_req, status=status, check=check, same_as=same_as,
                      diags=[{'code': c, 'severity': SEVERITY.get(c, 'error'), 'elements': sorted(set(e))}
                             for c, e in diags]))


def ops(result):
    return result.get('resolved', [])


def write_all(prune=False, tests=None, suite=None, profile=OPS_01):
    tests = TESTS if tests is None else tests
    suite = SUITE if suite is None else suite
    counters, failures, seen, outputs = {}, 0, set(), {}
    for tc in tests:
        g = tc['group']
        counters[g] = counters.get(g, 0) + 1
        name = f"{counters[g]:03d}-{tc['slug']}"
        d = os.path.join(suite, g, name)
        seen.add(d)
        os.makedirs(d, exist_ok=True)
        a = tc['raw_a'] if tc['raw_a'] is not None else (fmt(tc['a']) + '\n').encode('utf-8')
        r = tc['raw_req'] if tc['raw_req'] is not None else (fmt(tc['request']) + '\n').encode('utf-8')
        with open(os.path.join(d, 'input.json'), 'wb') as f:
            f.write(a)
        with open(os.path.join(d, 'request.json'), 'wb') as f:
            f.write(r)
        with open(os.path.join(d, 'test.json'), 'w') as f:
            f.write(json.dumps({'description': tc['description'], 'covers': tc['covers']}, indent=2, ensure_ascii=False) + '\n')
        result, b = apply(a, r, profile)
        view = expected_view(result)
        hand = sorted(tc['diags'], key=lambda x: (x['code'], x['elements']))
        problems = []
        if view['status'] != tc['status'] or view['diagnostics'] != hand:
            problems.append(f'hand   {tc["status"]} {json.dumps(hand)}\n  oracle {view["status"]} {json.dumps(result["diagnostics"])}')
        if tc['check'] is not None:
            try:
                # a check sees the result, with A as `_a`, and B
                tc['check']({**result, '_a': parse(a)[0]}, parse(b)[0] if b is not None else None)
            except Exception as e:                          # noqa: BLE001 - any failure is a mismatch
                problems.append(f'hand-written check failed: {type(e).__name__}: {e}')
        if b is not None:
            problems.extend(properties(a, r, result, b, profile))
            outputs[(g, tc['slug'])] = b
        if tc['same_as'] is not None and outputs.get((g, tc['same_as'])) != b:
            problems.append(f'output differs from {tc["same_as"]}')
        if problems:
            failures += 1
            print(f'MISMATCH {g}/{name}')
            for p in problems:
                print('  ' + p)
        exp = {'status': tc['status'], 'diagnostics': hand}
        for k in ('hash', 'created', 'removed', 'resolved', 'inverse'):
            if k in view:
                exp[k] = view[k]
        with open(os.path.join(d, 'expected.json'), 'w') as f:
            f.write(dumps(exp))
        out = os.path.join(d, 'output.json')
        if b is not None:
            with open(out, 'wb') as f:
                f.write(b)
        elif os.path.exists(out):
            os.remove(out)
    if prune and os.path.isdir(suite):
        for g in os.listdir(suite):
            gp = os.path.join(suite, g)
            if os.path.isdir(gp):
                for n in os.listdir(gp):
                    if os.path.join(gp, n) not in seen:
                        print('removing', os.path.join(gp, n))
                        shutil.rmtree(os.path.join(gp, n))
    print(f'{len(tests)} tests, {failures} mismatches')
    return failures


def run():
    sys.exit(1 if write_all(prune='--prune' in sys.argv) else 0)

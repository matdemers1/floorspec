"""Verifying the Floorspec Ops 0.1 conformance suite (conformance/ops/0.1) against the oracle.

For every test directory - test.json, input.json (document A), request.json, expected.json and,
when the batch commits, output.json (B's canonical bytes) - it recomputes the result from
input.json and request.json alone and compares:

- `status` and `diagnostics` (written by hand, so only ever cross-checked; --write never changes
  them), on code, severity and elements;
- `hash`, `created`, `removed`, `resolved`, `inverse` and output.json (taken from the oracle).

For every committed result it also checks the properties the specification promises:
B is in canonical form (1.3.1); applying the batch again gives the same bytes (1.3.2); applying
`resolved` to A in place of the batch, with the same context, commits the same B (1.4.1); and
applying `inverse` to B commits a document whose canonical form is exactly A's (1.6.1) - or, when
the inverse is empty, B is A.
"""

from __future__ import annotations

import json
import os

from ..jsonparse import Malformed, parse
from ..validate import check as core_check
from .engine import apply

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SUITE = os.path.join(ROOT, 'conformance', 'ops', '0.1')

TOP = ['status', 'diagnostics', 'hash', 'created', 'removed', 'resolved', 'inverse']
INNER = ['op', 'code', 'severity', 'elements', 'collection', 'id', 'level', 'start', 'end', 'position',
         'to', 'path', 'value', 'cascade', 'element']


def _key(order):
    return lambda k: (order.index(k), '') if k in order else (len(order), k)


def dumps(v, depth=0, order=TOP) -> str:
    """Readable JSON for expected.json: two-space indentation, points on one line, members in a
    fixed, meaningful order."""
    ind, inner = '  ' * depth, '  ' * (depth + 1)
    if isinstance(v, dict):
        if not v:
            return '{}'
        keys = sorted(v, key=_key(order))
        body = ',\n'.join(f'{inner}{json.dumps(k, ensure_ascii=False)}: {dumps(v[k], depth + 1, INNER)}' for k in keys)
        return '{\n' + body + '\n' + ind + '}' + ('\n' if depth == 0 else '')
    if isinstance(v, list):
        if not v:
            return '[]'
        if all(not isinstance(x, (list, dict)) for x in v):
            return '[' + ', '.join(json.dumps(x, ensure_ascii=False) for x in v) + ']'
        if all(isinstance(x, list) and all(not isinstance(y, (list, dict)) for y in x) for x in v) and len(v) <= 6:
            return '[' + ', '.join(dumps(x, depth + 1, INNER) for x in v) + ']'
        return '[\n' + ',\n'.join(inner + dumps(x, depth + 1, INNER) for x in v) + '\n' + ind + ']'
    return json.dumps(v, ensure_ascii=False)


def expected_view(result: dict) -> dict:
    """The members of a result that expected.json holds: everything but `document`, with each
    diagnostic reduced to code, severity and elements."""
    out = {'status': result['status'],
           'diagnostics': [{'code': d['code'], 'severity': d['severity'], 'elements': d['elements']}
                           for d in result['diagnostics']]}
    if result['status'] == 'committed':
        for k in ('hash', 'created', 'removed', 'resolved', 'inverse'):
            out[k] = result[k]
    return out


def request_context(req_bytes: bytes) -> dict:
    try:
        value, _ = parse(req_bytes)
    except Malformed:
        return {}
    return value.get('context', {}) if isinstance(value, dict) and isinstance(value.get('context'), dict) else {}


def properties(a_bytes: bytes, req_bytes: bytes, result: dict, b_bytes: bytes) -> list[str]:
    """1.3.1, 1.3.2, 1.4.1 and 1.6.1 for a committed result."""
    errors = []
    _, b_canon, _ = core_check(b_bytes)
    if b_canon != b_bytes:
        errors.append('the committed document is not in canonical form (1.3.1)')
    r2, b2 = apply(a_bytes, req_bytes)
    if json.dumps(r2, sort_keys=True) != json.dumps(result, sort_keys=True) or b2 != b_bytes:
        errors.append('applying the batch again gives a different result (1.3.2)')
    ctx = request_context(req_bytes)
    replay = {'batch': result['resolved'], **({'context': ctx} if ctx else {})}
    r3, b3 = apply(a_bytes, json.dumps(replay).encode('utf-8'))
    if r3['status'] != 'committed' or b3 != b_bytes:
        errors.append('applying `resolved` to A does not commit the same B (1.4.1): '
                      + json.dumps(r3.get('diagnostics')))
    _, a_canon, _ = core_check(a_bytes)
    if not result['inverse']:
        if b_bytes != a_canon:
            errors.append('the inverse is empty but B is not A (1.6.1)')
    else:
        r4, b4 = apply(b_bytes, json.dumps({'batch': result['inverse']}).encode('utf-8'))
        if r4['status'] != 'committed' or b4 != a_canon:
            errors.append('applying `inverse` to B does not commit A (1.6.1): ' + json.dumps(r4.get('diagnostics')))
    return errors


def test_dirs(suite=SUITE):
    for dirpath, _, files in sorted(os.walk(suite)):
        if 'test.json' in files:
            yield dirpath


def verify(path: str, write: bool = False) -> list[str]:
    rel = os.path.relpath(path, ROOT)
    errors = []
    try:
        with open(os.path.join(path, 'test.json'), encoding='utf-8') as f:
            meta = json.load(f)
        if not isinstance(meta.get('description'), str) or not isinstance(meta.get('covers'), list):
            errors.append('test.json needs "description" and "covers"')
    except (OSError, ValueError) as e:
        errors.append(f'test.json: {e}')
    try:
        with open(os.path.join(path, 'input.json'), 'rb') as f:
            a_bytes = f.read()
        with open(os.path.join(path, 'request.json'), 'rb') as f:
            req_bytes = f.read()
        with open(os.path.join(path, 'expected.json'), encoding='utf-8') as f:
            expected = json.load(f)
    except (OSError, ValueError) as e:
        return [f'{rel}: {e}']
    result, b_bytes = apply(a_bytes, req_bytes)
    view = expected_view(result)
    if expected.get('status') != view['status']:
        errors.append(f'status: expected {expected.get("status")}, oracle {view["status"]}')
    if expected.get('diagnostics') != view['diagnostics']:
        errors.append('diagnostics differ:\n    expected ' + json.dumps(expected.get('diagnostics'))
                      + '\n    oracle   ' + json.dumps(result['diagnostics']))
    out_path = os.path.join(path, 'output.json')
    on_disk = None
    if os.path.exists(out_path):
        with open(out_path, 'rb') as f:
            on_disk = f.read()
    if write:
        new = {k: expected[k] for k in ('status', 'diagnostics') if k in expected}
        for k in ('hash', 'created', 'removed', 'resolved', 'inverse'):
            if k in view:
                new[k] = view[k]
        with open(os.path.join(path, 'expected.json'), 'w', encoding='utf-8') as f:
            f.write(dumps(new))
        if b_bytes is not None:
            with open(out_path, 'wb') as f:
                f.write(b_bytes)
        elif on_disk is not None:
            os.remove(out_path)
    else:
        for k in ('hash', 'created', 'removed', 'resolved', 'inverse'):
            if expected.get(k) != view.get(k):
                errors.append(f'{k} differs from the oracle')
        if b_bytes != on_disk:
            errors.append('output.json differs from the oracle' if b_bytes is not None and on_disk is not None
                          else 'output.json must exist exactly when the batch commits')
    if b_bytes is not None:
        errors.extend(properties(a_bytes, req_bytes, result, b_bytes))
    return [f'{rel}: {e}' for e in errors]


def verify_all(write: bool = False) -> tuple[int, list[str]]:
    dirs = list(test_dirs())
    errors = []
    for d in dirs:
        errors.extend(verify(d, write))
    return len(dirs), errors

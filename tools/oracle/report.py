"""Readable JSON for expected.json: like JSON.stringify(v, null, 2), except that an array of
numbers - a point - stays on one line, and members keep a fixed, meaningful order."""

from __future__ import annotations

import json

ORDER = ['valid', 'diagnostics', 'hash', 'derived', 'code', 'severity', 'elements',
         'walls', 'junctionFills', 'rooms', 'unanchored', 'openings',
         'startRight', 'endRight', 'endLeft', 'startLeft', 'baseElevation', 'topElevation',
         'level', 'outer', 'holes', 'area', 'start', 'end', 'sillElevation', 'headElevation']


def _key(k):
    return (ORDER.index(k), '') if k in ORDER else (len(ORDER), k)


def _flat(v) -> bool:
    return isinstance(v, list) and all(not isinstance(x, (list, dict)) for x in v)


def dumps(v, depth: int = 0) -> str:
    return _dump(v, depth) + ('\n' if depth == 0 else '')


def _dump(v, depth):
    ind, inner = '  ' * depth, '  ' * (depth + 1)
    if isinstance(v, dict):
        if not v:
            return '{}'
        keys = sorted(v, key=_key)
        return '{\n' + ',\n'.join(f'{inner}{json.dumps(k, ensure_ascii=False)}: {_dump(v[k], depth + 1)}' for k in keys) + '\n' + ind + '}'
    if isinstance(v, list):
        if not v:
            return '[]'
        if _flat(v):
            return '[' + ', '.join(json.dumps(x, ensure_ascii=False) for x in v) + ']'
        if all(_flat(x) for x in v) and sum(len(x) for x in v) <= 12:
            return '[' + ', '.join(_dump(x, depth + 1) for x in v) + ']'
        return '[\n' + ',\n'.join(inner + _dump(x, depth + 1) for x in v) + '\n' + ind + ']'
    return json.dumps(v, ensure_ascii=False)

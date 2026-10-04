"""Re-verify the whole conformance suite against the oracle.

    python3.13 -m tools.oracle.regenerate            check; exit 1 on any difference
    python3.13 -m tools.oracle.regenerate --write    rewrite hash, derived and canonical.json

For every test directory under conformance/core/0.1 it recomputes, from input.json alone:

- `valid` and `diagnostics` - these are written by hand and only ever cross-checked here; --write
  never changes them, so a disagreement is always reported for a person to resolve;
- `hash`, `derived` and canonical.json - present exactly when the document is valid;

and, for every valid document, that its canonical form is itself valid, canonicalizes to the same
bytes, has the same hash and derives exactly the same values (9.2.2).
"""

from __future__ import annotations

import json
import os
import sys

from .report import dumps
from .validate import check

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
SUITE = os.path.join(ROOT, 'conformance', 'core', '0.1')


def test_dirs():
    for dirpath, _, files in sorted(os.walk(SUITE)):
        if 'input.json' in files or 'test.json' in files:
            yield dirpath


def verify(path: str, write: bool) -> list[str]:
    rel = os.path.relpath(path, ROOT)
    errors = []
    try:
        with open(os.path.join(path, 'test.json'), encoding='utf-8') as f:
            meta = json.load(f)
        if not isinstance(meta.get('description'), str) or not isinstance(meta.get('covers'), list):
            errors.append('test.json needs "description" and "covers"')
    except (OSError, ValueError) as e:
        errors.append(f'test.json: {e}')
    with open(os.path.join(path, 'input.json'), 'rb') as f:
        data = f.read()
    result, canonical, notes = check(data)
    exp_path = os.path.join(path, 'expected.json')
    try:
        with open(exp_path, encoding='utf-8') as f:
            expected = json.load(f)
    except (OSError, ValueError) as e:
        return [f'{rel}: expected.json: {e}']
    if expected.get('valid') != result['valid']:
        errors.append(f'valid: expected {expected.get("valid")}, oracle {result["valid"]}')
    if expected.get('diagnostics') != result['diagnostics']:
        errors.append('diagnostics differ:\n    expected ' + json.dumps(expected.get('diagnostics'))
                      + '\n    oracle   ' + json.dumps(result['diagnostics'])
                      + ''.join('\n    note: ' + n for n in notes[:5]))
    can_path = os.path.join(path, 'canonical.json')
    on_disk = None
    if os.path.exists(can_path):
        with open(can_path, 'rb') as f:
            on_disk = f.read()
    if write:
        new = dict(expected)
        for k in ('hash', 'derived'):
            new.pop(k, None)
            if k in result:
                new[k] = result[k]
        text = dumps(new)
        with open(exp_path, 'w', encoding='utf-8') as f:
            f.write(text)
        if canonical is not None:
            with open(can_path, 'wb') as f:
                f.write(canonical)
        elif on_disk is not None:
            os.remove(can_path)
    else:
        for k in ('hash', 'derived'):
            if expected.get(k) != result.get(k):
                errors.append(f'{k} differs from the oracle')
        if canonical != on_disk:
            errors.append('canonical.json differs from the oracle' if canonical is not None and on_disk is not None
                          else 'canonical.json must exist exactly when the document is valid')
    if canonical is not None:
        again, canonical2, _ = check(canonical)
        if not again['valid'] or canonical2 != canonical:
            errors.append('the canonical form does not canonicalize to itself')
        elif again.get('hash') != result.get('hash') or again.get('derived') != result.get('derived'):
            errors.append('the canonical form derives different values or hash (9.2.2)')
    return [f'{rel}: {e}' for e in errors]


def main(argv) -> int:
    write = '--write' in argv
    dirs = list(test_dirs())
    errors = []
    for d in dirs:
        errors.extend(verify(d, write))
    for e in errors:
        print(e)
    print(f'{len(dirs)} tests, {len(errors)} differences from the oracle')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

"""Re-verify the migration suites (chapter 20): conformance/migration/<draft>/<group>/<NNN-slug>/ - 0.3's
with a migrator of Core 0.3, as published, and 0.4's with a migrator of Core 0.4.

For every test, from input.json and request.json alone, with the oracle's migrator (migrate.py):

- `status` and `diagnostics` - written by hand, only ever cross-checked;
- `hash` and output.json - present exactly when the document is migrated; recomputed, and rewritten
  with --write;
- `validation` - written by hand and cross-checked: what a reader of the target draft (implementing no
  extension, knowing none) reports for input.json, and for output.json alike, and the two derive
  exactly the same values (20.6.1);

and, for every migrated test, that migrating output.json to the same target gives its own bytes
(20.1.2), and that the migration is the steps applied one at a time (20.1.3).
"""

from __future__ import annotations

import json
import os

from .migrate import DRAFTS_03, DRAFTS_04, migrate
from .author_lib import fmt
from .validate import READERS, check

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
SUITES = {'0.3': (os.path.join(ROOT, 'conformance', 'migration', '0.3'), DRAFTS_03),
          '0.4': (os.path.join(ROOT, 'conformance', 'migration', '0.4'), DRAFTS_04)}
SUITE = SUITES['0.3'][0]


def test_dirs(suite=SUITE):
    for dirpath, _, files in sorted(os.walk(suite)):
        if 'test.json' in files:
            yield dirpath


def reading(data: bytes, to: str):
    """What a reader of `to` reports and derives for a document: (validation, derived)."""
    result, _, _ = check(data, READERS[to], None)
    return {'valid': result['valid'], 'diagnostics': result['diagnostics']}, result.get('derived')


def expected_text(status, diagnostics, hash_=None, validation=None) -> str:
    """expected.json: status, diagnostics, and - for a migrated document - hash and validation."""
    exp = {'status': status, 'diagnostics': diagnostics}
    if hash_ is not None:
        exp['hash'] = hash_
    if validation is not None:
        exp['validation'] = validation
    return fmt(exp) + '\n'


def verify(path: str, write: bool, drafts=DRAFTS_03) -> list[str]:
    rel = os.path.relpath(path, ROOT)
    errors = []
    with open(os.path.join(path, 'test.json'), encoding='utf-8') as f:
        meta = json.load(f)
    if not isinstance(meta.get('description'), str) or not isinstance(meta.get('covers'), list):
        errors.append('test.json needs "description" and "covers"')
    with open(os.path.join(path, 'input.json'), 'rb') as f:
        data = f.read()
    with open(os.path.join(path, 'request.json'), encoding='utf-8') as f:
        to = json.load(f).get('to')
    exp_path = os.path.join(path, 'expected.json')
    with open(exp_path, encoding='utf-8') as f:
        expected = json.load(f)
    r = migrate(data, to, drafts)
    if expected.get('status') != r['status']:
        errors.append(f'status: expected {expected.get("status")}, oracle {r["status"]}')
    if expected.get('diagnostics') != r['diagnostics']:
        errors.append(f'diagnostics: expected {json.dumps(expected.get("diagnostics"))}, oracle {json.dumps(r["diagnostics"])}')
    out_path = os.path.join(path, 'output.json')
    on_disk = None
    if os.path.exists(out_path):
        with open(out_path, 'rb') as f:
            on_disk = f.read()
    if r['status'] == 'migrated':
        validation, derived = reading(data, to)
        again, derived_again = reading(r['bytes'], to)
        if expected.get('validation') != validation:
            errors.append(f'validation: expected {json.dumps(expected.get("validation"))}, a reader of {to} reports {json.dumps(validation)}')
        if again != validation or derived_again != derived:
            errors.append(f'a reader of {to} reads the migration differently from the document (20.6.1)')
        if migrate(r['bytes'], to, drafts).get('bytes') != r['bytes']:
            errors.append('migrating the migration to its own draft changes it (20.1.2)')
        declared = json.loads(data)['floorspec']
        stepwise = migrate(data, declared, drafts)['bytes']
        for v in drafts[drafts.index(declared) + 1:drafts.index(to) + 1]:
            stepwise = migrate(stepwise, v, drafts)['bytes']
        if stepwise != r['bytes']:
            errors.append('the migration is not its steps applied in order (20.1.3)')
    if write:
        with open(exp_path, 'w', encoding='utf-8') as f:
            f.write(expected_text(expected['status'], expected['diagnostics'], r.get('hash'), expected.get('validation')))
        if r['status'] == 'migrated':
            with open(out_path, 'wb') as f:
                f.write(r['bytes'])
        elif on_disk is not None:
            os.remove(out_path)
    else:
        if expected.get('hash') != r.get('hash'):
            errors.append('hash differs from the oracle')
        if r.get('bytes') != on_disk:
            errors.append('output.json differs from the oracle' if on_disk is not None and 'bytes' in r
                          else 'output.json must exist exactly when the document is migrated')
    return [f'{rel}: {e}' for e in errors]


def verify_all(write: bool = False, version: str = '0.3'):
    suite, drafts = SUITES[version]
    dirs = list(test_dirs(suite))
    errors = []
    for d in dirs:
        errors.extend(verify(d, write, drafts))
    return len(dirs), errors

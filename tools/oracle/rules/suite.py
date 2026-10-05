"""Re-verifying the Floorspec Rules 0.1 suite (conformance/rules/0.1/) against the oracle: every
expected.json recomputed from input.json, registry.json and request.json (or measures.json) alone,
and compared byte for byte (spec/rules 9.8). For every report it also checks what the specification
promises of any report: no match of the assurance pattern (9.5.2), the notice (9.9), and - where the
document was evaluated - the document's own content hash, so that evaluating rules changed nothing
about it (1.5.1)."""

from __future__ import annotations

import json
import os

from .evaluate import call_measures, check_document, evaluate, report_bytes
from .structure import NOTICE, assures

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SUITE = os.path.join(ROOT, 'conformance', 'rules', '0.1')


def test_dirs(suite=SUITE):
    for dirpath, _, files in sorted(os.walk(suite)):
        if 'test.json' in files:
            yield dirpath


def _read(path):
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return f.read()


def compute(path):
    """The expected bytes of one test, as the oracle computes them."""
    doc, registry = _read(os.path.join(path, 'input.json')), _read(os.path.join(path, 'registry.json'))
    calls = _read(os.path.join(path, 'measures.json'))
    if calls is not None:
        return report_bytes(call_measures(doc, registry, json.loads(calls))), None
    report = evaluate(doc, registry, _read(os.path.join(path, 'request.json')))
    return report_bytes(report), report


def verify(path, write=False):
    rel = os.path.relpath(path, ROOT)
    errors = []
    try:
        meta = json.loads(_read(os.path.join(path, 'test.json')))
        if not isinstance(meta.get('description'), str) or not isinstance(meta.get('covers'), list):
            errors.append('test.json needs "description" and "covers"')
    except ValueError as e:
        errors.append(f'test.json: {e}')
    expected, report = compute(path)
    on_disk = _read(os.path.join(path, 'expected.json'))
    if write:
        with open(os.path.join(path, 'expected.json'), 'wb') as f:
            f.write(expected)
    elif on_disk != expected:
        errors.append('expected.json differs from the oracle')
    if assures(expected.decode('utf-8')):
        errors.append('the expected output matches the assurance pattern (9.5.2)')
    if report is not None:
        if report['notice'] != NOTICE:
            errors.append('the report has no notice (9.9)')
        if 'hash' in report:
            result, _, _ = check_document(_read(os.path.join(path, 'input.json')), _read(os.path.join(path, 'registry.json')))
            if not result['valid'] or result['hash'] != report['hash']:
                errors.append('the evaluated document is not the valid document it was given (1.5.1)')
    return [f'{rel}: {e}' for e in errors]


def verify_all(write=False):
    dirs = list(test_dirs())
    errors = []
    for d in dirs:
        errors.extend(verify(d, write))
    return len(dirs), errors

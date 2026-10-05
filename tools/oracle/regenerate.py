"""Re-verify the whole conformance suite - Floorspec Core 0.1, 0.2, 0.3 and 0.4, Floorspec Ops 0.1, 0.2 and 0.3,
every official extension's suite (conformance/ext/<NAME>/<version>/), Floorspec Rules 0.1 and 0.2
(conformance/rules/<v>/, by tools/oracle/rules/suite.py) and the migration suites of chapter 20 of Core
0.3 and 0.4 (conformance/migration/<v>/, by tools/oracle/migration_suite.py) - against the oracle.

    python3.13 -m tools.oracle.regenerate            check; exit 1 on any difference
    python3.13 -m tools.oracle.regenerate --write    rewrite what the oracle computes (below)

The Ops suites are verified by tools/oracle/ops/suite.py - conformance/ops/<v> applied as Ops <v>: status and diagnostics are cross-checked, hash, created, removed, resolved, inverse and output.json are
recomputed (and rewritten with --write), and every committed result is checked for 1.3.1, 1.3.2,
1.4.1 and 1.6.1.

For every test directory under conformance/core/<v> - read as a Core <v> reader reads it: 0.1
alone; 0.2, which also reads 0.1 documents; 0.3, which also reads 0.1 and 0.2 documents (1.2.6 of 0.3);
0.4, which also reads 0.1, 0.2 and 0.3 documents (1.2.8) -
configured with the test's registry.json as its known extensions when the test has one (12.2),
and deriving the design its design.json names when it has one (Core 0.3, 19.6), it recomputes, from
input.json (and registry.json and design.json) alone:

- `valid` and `diagnostics` - these are written by hand and only ever cross-checked here; --write
  never changes them, so a disagreement is always reported for a person to resolve;
- `hash` and canonical.json - present exactly when the document is valid - and `derived`, present
  when it is valid and the design is one Core derives (19.6.2);

as a package validator (Core 0.3, 18.4) given the files under the test's package/ directory, when it
has one;

and, for every valid document, that its canonical form is itself valid, canonicalizes to the same
bytes, has the same hash and derives exactly the same values (9.2.2).
"""

from __future__ import annotations

import json
import os
import sys

from .ops.suite import verify_all as verify_ops
from .ops.version import PROFILES as OPS_VERSIONS
from .report import dumps
from .author_lib import read_package
from .validate import READER_01, READERS, check, ext_reader

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
SUITES = {v: (os.path.join(ROOT, 'conformance', 'core', v), reader) for v, reader in READERS.items()}
SUITE = SUITES['0.1'][0]


def test_dirs(suite=SUITE):
    for dirpath, _, files in sorted(os.walk(suite)):
        if 'input.json' in files or 'test.json' in files:
            yield dirpath


def reader_for(path: str):
    """The reader and known extensions a test directory is checked with."""
    where = os.path.abspath(path) + os.sep
    reader = next((r for v, r in READERS.items() if os.sep + os.path.join('core', v) + os.sep in where), READER_01)
    registry = None
    rp = os.path.join(path, 'registry.json')
    if os.path.exists(rp):
        with open(rp, 'rb') as f:
            registry = f.read()
    return reader, registry


def design_for(path: str):
    """The design a test derives (Core 0.3, 19.6): its design.json, or None for the primary design."""
    dp = os.path.join(path, 'design.json')
    if not os.path.exists(dp):
        return None
    with open(dp, encoding='utf-8') as f:
        return json.load(f)


def verify(path: str, write: bool, extensions=None) -> list[str]:
    """One Core-format test. ``extensions``: the official extensions the reader implements (an
    extension suite's tests), or None for a core-only reader (the Core suites)."""
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
    reader, registry = reader_for(path)
    if extensions is not None:
        reader = ext_reader(data)
    design = design_for(path)
    package = read_package(path)                     # Core 0.3, 18.4: run as a package validator
    result, canonical, notes = check(data, reader, registry, extensions, package, design)
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
        again, canonical2, _ = check(canonical, reader, registry, extensions, package, design)
        if not again['valid'] or canonical2 != canonical:
            errors.append('the canonical form does not canonicalize to itself')
        elif again.get('hash') != result.get('hash') or again.get('derived') != result.get('derived'):
            errors.append('the canonical form derives different values or hash (9.2.2)')
    return [f'{rel}: {e}' for e in errors]


EXT_ROOT = os.path.join(ROOT, 'conformance', 'ext')


def ext_suites():
    """(extension name, suite directory) of every extension suite, conformance/ext/<NAME>/<version>/."""
    if not os.path.isdir(EXT_ROOT):
        return []
    return [(name, os.path.join(EXT_ROOT, name, v)) for name in sorted(os.listdir(EXT_ROOT))
            for v in sorted(os.listdir(os.path.join(EXT_ROOT, name)))]


def verify_ext(name: str, suite: str, write: bool):
    """An extension suite, run by an implementation of that one extension: its Core-format tests as
    verify() checks them, its Ops tests (those with a request.json) as the Ops 0.2 suite's are - as
    the Ops 0.3 suite's for a document declaring "0.3" - by an applier whose validator implements the
    extension and has the test's known extensions."""
    from .ext import official
    from .ops.suite import verify as verify_op
    from .ops.version import OPS_02, OPS_03, OPS_04
    implemented = official.implemented(name)
    dirs = list(test_dirs(suite))
    errors = []
    for d in dirs:
        if os.path.exists(os.path.join(d, 'request.json')):
            _, registry = reader_for(d)
            with open(os.path.join(d, 'input.json'), 'rb') as f:
                reader = ext_reader(f.read())
                profile = OPS_04 if reader.v04 else OPS_03 if reader.v03 else OPS_02
            errors.extend(verify_op(d, write, profile.configured(registry, implemented)))
        else:
            errors.extend(verify(d, write, implemented))
    return len(dirs), errors


def main(argv) -> int:
    write = '--write' in argv
    counts, all_errors = {}, []
    for version, (suite, _) in SUITES.items():
        dirs = list(test_dirs(suite))
        errors = []
        for d in dirs:
            errors.extend(verify(d, write))
        counts[version] = (len(dirs), len(errors))
        all_errors.extend(errors)
    ops_counts, ops_errors = {}, []
    for version in OPS_VERSIONS:
        n, errors = verify_ops(write, version)
        ops_counts[version] = (n, len(errors))
        ops_errors.extend(errors)
    ext_counts = {}
    for name, suite in ext_suites():
        n, errors = verify_ext(name, suite, write)
        ext_counts[f'{name} {os.path.basename(suite)}'] = (n, len(errors))
        ops_errors.extend(errors)
    from .rules.suite import SUITES as RULES_SUITES, verify_all as verify_rules
    rules_counts = {}
    for version in RULES_SUITES:
        rules_n, rules_errors = verify_rules(write, version)
        rules_counts[version] = (rules_n, len(rules_errors))
        ops_errors.extend(rules_errors)
    from .migration_suite import SUITES as MIGRATION_SUITES, verify_all as verify_migration
    migration_counts = {}
    for version in MIGRATION_SUITES:
        migration_n, migration_errors = verify_migration(write, version)
        migration_counts[version] = (migration_n, len(migration_errors))
        ops_errors.extend(migration_errors)
    for e in all_errors + ops_errors:
        print(e)
    for version, (n, k) in counts.items():
        print(f'Core {version}: {n} tests, {k} differences from the oracle')
    for version, (n, k) in ops_counts.items():
        print(f'Ops {version}: {n} tests, {k} differences from the oracle')
    for label, (n, k) in ext_counts.items():
        print(f'{label}: {n} tests, {k} differences from the oracle')
    for version, (n, k) in rules_counts.items():
        print(f'Rules {version}: {n} tests, {k} differences from the oracle')
    for version, (n, k) in migration_counts.items():
        print(f'Migration (Core {version}, chapter 20): {n} tests, {k} differences from the oracle')
    return 1 if all_errors or ops_errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

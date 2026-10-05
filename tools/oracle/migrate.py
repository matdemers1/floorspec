"""The reference migrator of Floorspec Core 0.3, chapter 20 - written from the specification alone.

``migrate(data: bytes, to) -> dict`` is what a conformant migrator returns for a document's bytes and
a target draft: ``{'status': 'migrated', 'diagnostics': [], 'hash', 'document', 'bytes'}`` or
``{'status': 'refused', 'diagnostics': [...]}``.

    python3.13 -m tools.oracle.migrate <document> --to 0.3    print the migration (20.1.1)

Order (20.2): the document's tiers 1 to 3 as a validator implementing every extension and knowing
none reports them (FS-JSON-, FS-DOC-001, FS-SCH-001; never FS-DOC-002 or FS-CFG-001), then the
target (FS-MIG-001), then the steps in order, each of which may refuse with FS-MIG-002 (20.3.3).
"""

from __future__ import annotations

import copy
import json
import sys

from . import canon, schema
from .jsonparse import Malformed, parse
from .validate import diag, sort_diags

DRAFTS = ('0.1', '0.2', '0.3')
RECORD = 'floorspec:migration'


def pointer(*parts: str) -> str:
    """An RFC 6901 JSON Pointer of member names."""
    return ''.join('/' + p.replace('~', '~0').replace('/', '~1') for p in parts)


def utf16(s: str) -> bytes:
    return s.encode('utf-16-be')


def _moves_01_02(d: dict):
    """20.4.1: the member `collections` of every extension's top-level data that is an object with one."""
    out = []
    for name, data in d.get('extensions', {}).items():
        if isinstance(data, dict) and 'collections' in data:
            out.append(((name,), 'collections'))
    return out


def _moves_02_03(d: dict):
    """20.5.1: the member `option` of every extension element (12.5) that has one."""
    out = []
    for name, data in d.get('extensions', {}).items():
        if not isinstance(data, dict) or not isinstance(data.get('collections'), dict):
            continue
        for cname, coll in data['collections'].items():
            if not isinstance(coll, dict):
                continue
            for eid, el in coll.items():
                if isinstance(el, dict) and 'option' in el:
                    out.append(((name, 'collections', cname, eid), 'option'))
    return out


# draft -> (the next draft, the members its step moves)
STEPS = {'0.1': ('0.2', _moves_01_02), '0.2': ('0.3', _moves_02_03)}


class Refused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def step(d: dict) -> dict:
    """One step (20.1), from the draft d declares to the next: a new document; d is not changed."""
    nxt, moves_of = STEPS[d['floorspec']]
    out = copy.deepcopy(d)
    moves = moves_of(out)
    if moves:
        extras = out.get('extras', {})
        if RECORD in extras and not isinstance(extras[RECORD], list):
            raise Refused('FS-MIG-002')                            # 20.3.3
        moved = []
        for path, member in moves:
            holder = out['extensions']
            for p in path:
                holder = holder[p]
            moved.append({'pointer': pointer('extensions', *path, member), 'value': holder.pop(member)})
        moved.sort(key=lambda m: utf16(m['pointer']))
        record = {'from': d['floorspec'], 'to': nxt, 'moved': moved}
        out['extras'] = {**extras, RECORD: [*extras.get(RECORD, []), record]}   # 20.3.1
    out['floorspec'] = nxt
    return out


def migrate_value(d: dict, to: str) -> dict:
    """20.1.2, 20.1.3: every step from the draft d declares to ``to``, in order."""
    while d['floorspec'] != to:
        d = step(d)
    return d


def migrate(data: bytes, to) -> dict:
    """The migration of a document's bytes to the draft ``to`` (20.2, 20.1.1)."""
    try:
        value, codes = parse(data)
    except Malformed:
        return {'status': 'refused', 'diagnostics': [diag('FS-JSON-001')]}
    if codes:
        return {'status': 'refused', 'diagnostics': sort_diags(diag(c) for c in codes)}
    declared = value.get('floorspec') if isinstance(value, dict) else None
    if isinstance(declared, str) and declared not in DRAFTS:
        return {'status': 'refused', 'diagnostics': [diag('FS-DOC-001')]}
    if schema.check(value, declared if declared in DRAFTS else DRAFTS[-1]):
        return {'status': 'refused', 'diagnostics': [diag('FS-SCH-001')]}
    if not isinstance(to, str) or to not in DRAFTS or DRAFTS.index(to) < DRAFTS.index(declared):
        return {'status': 'refused', 'diagnostics': [diag('FS-MIG-001')]}
    try:
        out = migrate_value(value, to)
    except Refused as e:
        return {'status': 'refused', 'diagnostics': [diag(e.code)]}
    return {'status': 'migrated', 'diagnostics': [], 'hash': canon.content_hash(out), 'document': out,
            'bytes': written(out)}


def written(d: dict) -> bytes:
    """20.1.1: a value written as step 2 of 9.2 writes it - members sorted, two spaces, a final line
    feed - with no default omitted."""
    return (canon.pretty(d) + '\n').encode('utf-8')


def main(argv) -> int:
    if len(argv) != 3 or argv[1] != '--to':
        print('usage: python3.13 -m tools.oracle.migrate <document> --to <draft>', file=sys.stderr)
        return 2
    with open(argv[0], 'rb') as f:
        result = migrate(f.read(), argv[2])
    if result['status'] != 'migrated':
        print(json.dumps(result['diagnostics']), file=sys.stderr)
        return 1
    sys.stdout.write(result['bytes'].decode('utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

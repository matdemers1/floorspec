"""FS-OPS diagnostics (Ops chapter 7) and the exception that ends a transaction with them."""

from __future__ import annotations

MESSAGES = {
    'FS-OPS-001': 'the request is malformed',
    'FS-OPS-002': 'the document the batch applies to is not valid',
    'FS-OPS-003': 'a reference resolves to nothing',
    'FS-OPS-004': 'a selector matches more than one element',
    'FS-OPS-005': 'an operation names an ID already in use or retired',
    'FS-OPS-006': 'a removal is blocked by elements that depend on it',
    'FS-OPS-007': 'a selector needs faces on a level that has none to give',
    'FS-OPS-008': 'a composite does not apply',
    'FS-OPS-009': 'an opening straddles a junction that planarization inserts',
    'FS-OPS-010': 'a lock names elements that do not exist, or walls that are not parallel',
    'FS-OPS-011': 'the result breaks a lock',
    'FS-OPS-012': 'a length, point or vector string does not match the grammar',
}


def diagnostic(code: str, elements=(), pointer: str | None = None, note: str = '') -> dict:
    """A diagnostic in the shape of Core 10.2. Elements are sorted and unique."""
    d = {'code': code, 'severity': 'error',
         'message': MESSAGES[code] + (f': {note}' if note else ''),
         'elements': sorted(set(elements))}
    if pointer is not None:
        d['location'] = {'pointer': pointer}
    return d


class OpsError(Exception):
    """One failure: its code, its elements, and where in the request it happened."""

    def __init__(self, code: str, elements=(), pointer: str | None = None, note: str = ''):
        super().__init__(f'{code} {note}'.strip())
        self.code = code
        self.elements = sorted(set(elements))
        self.pointer = pointer
        self.note = note

    def diagnostic(self) -> dict:
        return diagnostic(self.code, self.elements, self.pointer, self.note)


class Rejected(Exception):
    """The transaction failed; `diagnostics` are what the rejection carries (7.1)."""

    def __init__(self, diagnostics: list[dict]):
        super().__init__(', '.join(d['code'] for d in diagnostics))
        self.diagnostics = sorted(diagnostics, key=lambda d: (d['code'], d['elements']))


def esc(token: str) -> str:
    """One JSON Pointer reference token (RFC 6901)."""
    return token.replace('~', '~0').replace('/', '~1')

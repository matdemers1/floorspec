"""The draft of Floorspec Rules the oracle evaluates as: 0.1, as published at 8a99d02, reading documents
as a Core 0.3 reader; or 0.2, reading them as a Core 0.4 reader, with the stair measures 0.2 adds
(spec/rules 8.5). Requests, packs, profiles and reports declare the draft (`floorspecRules`), and an
evaluator of one draft rejects another's (1.1, 2.1, 10.1). Each suite is evaluated with its own draft,
as the Core suites are read with their own reader; 0.1 is the default, so that a caller that names no
draft gets the published behaviour."""

from __future__ import annotations

from contextlib import contextmanager

from ..validate import READER_03, READER_04

DRAFTS = ('0.1', '0.2')
CURRENT = '0.2'                                    # the draft spec/rules/ is
_current = ['0.1']


def current() -> str:
    return _current[0]


def reader():
    """The Core reader an evaluator of the current draft reads documents with (1.2)."""
    return READER_04 if current() == '0.2' else READER_03


def at_least(v: str) -> bool:
    return DRAFTS.index(current()) >= DRAFTS.index(v)


@contextmanager
def using(version: str):
    assert version in DRAFTS, version
    prev = _current[0]
    _current[0] = version
    try:
        yield
    finally:
        _current[0] = prev

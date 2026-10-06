"""The drafts of Floorspec Ops the oracle applies, as profiles.

Ops 0.1 was published at commit 3bf4f35 and does not change: it applies batches to Core 0.1
documents, with the operations, members and rules of that text. Ops 0.2 (published at 6f9bc07)
applies them to Core 0.2 documents - and, because a Core 0.2 reader reads 0.1 documents, to 0.1
documents too - and adds the program and extension elements as things an edit can address. Ops 0.3
applies the same operations to Core 0.3 documents, and to 0.2 and 0.1 documents as a Core 0.3
reader reads them (Core 1.2.6); it adds no operation, and its requests have Ops 0.2's shape. Ops 0.4
applies Ops 0.3's operations to Core 0.4 documents, and to 0.3, 0.2 and 0.1 documents as a Core 0.4
reader reads them (Core 1.2.8); its requests have Ops 0.3's shape, and match schema/ops/0.3. An arc edge (Core 0.4,
chapter 21) is added with addElement, or drawn and then given its `arc` with setProperty, and is never routed
or split by planarization (5.2).

A profile is chosen per run, the way the Core reader is (validate.READERS): each Ops suite is
applied with its own draft. OPS_01 is the default, so that a caller that names no draft gets the
published behaviour.
"""

from __future__ import annotations

import os

from ..validate import READER_01, READER_02, READER_03, READER_04, Reader


class Profile:
    def __init__(self, version: str, reader: Reader, registry: bytes | None = None, extensions=None):
        self.version = version
        self.reader = reader                    # how A and the result are validated (1.2 steps 1, 6)
        self.v02 = version in ('0.2', '0.3', '0.4')   # the program and extension elements are elements (0.3)
        self.v03 = version in ('0.3', '0.4')          # stairs are a collection (Core 0.3, chapter 17)
        self.v04 = version == '0.4'                   # arc edges (Core 0.4, chapter 21): never routed or split (5.2)
        # The Core drafts whose documents have them: those the reader implements, but 0.1 (Ops 0.3).
        self.element_drafts = reader.versions - {'0.1'}
        # The validator's known extensions (Core 12.2) and the official extensions it implements
        # (tools/oracle/ext): none in the Ops suites (Ops 0.2); an extension suite's Ops tests
        # (conformance/ext/) configure them from the test.
        self.registry = registry
        self.extensions = extensions

    def validate(self, data: bytes):
        """Core validation as this applier's validator performs it."""
        from ..validate import check
        return check(data, self.reader, self.registry, self.extensions)

    def configured(self, registry: bytes | None, extensions) -> 'Profile':
        return Profile(self.version, self.reader, registry, extensions)

    def __repr__(self):
        return f'Ops {self.version}'


OPS_01 = Profile('0.1', READER_01)
OPS_02 = Profile('0.2', READER_02)
OPS_03 = Profile('0.3', READER_03)
OPS_04 = Profile('0.4', READER_04)
PROFILES = {'0.1': OPS_01, '0.2': OPS_02, '0.3': OPS_03, '0.4': OPS_04}


def profile_for(path: str) -> Profile:
    """The draft a test directory belongs to: Ops <v> under conformance/ops/<v>, else 0.1."""
    where = os.path.abspath(path) + os.sep
    return next((p for v, p in PROFILES.items() if os.sep + os.path.join('ops', v) + os.sep in where), OPS_01)

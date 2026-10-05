"""The drafts of Floorspec Ops the oracle applies, as profiles.

Ops 0.1 was published at commit 3bf4f35 and does not change: it applies batches to Core 0.1
documents, with the operations, members and rules of that text. Ops 0.2 applies them to Core 0.2
documents - and, because a Core 0.2 reader reads 0.1 documents (Core 1.2.4), to 0.1 documents
too - and adds the program and extension elements as things an edit can address.

A profile is chosen per run, the way the Core reader is (validate.READER_01 / READER_02): the
Ops 0.1 suite is applied with OPS_01, the 0.2 suite with OPS_02. OPS_01 is the default, so that a
caller that names no draft gets the published behaviour.
"""

from __future__ import annotations

import os

from ..validate import READER_01, READER_02, Reader


class Profile:
    def __init__(self, version: str, reader: Reader, registry: bytes | None = None, extensions=None):
        self.version = version
        self.reader = reader                    # how A and the result are validated (1.2 steps 1, 6)
        self.v02 = version == '0.2'
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
PROFILES = {'0.1': OPS_01, '0.2': OPS_02}


def profile_for(path: str) -> Profile:
    """The draft a test directory belongs to: Ops 0.2 under conformance/ops/0.2, else 0.1."""
    marker = os.sep + os.path.join('ops', '0.2') + os.sep
    return OPS_02 if marker in os.path.abspath(path) + os.sep else OPS_01

"""python3.13 -m tools.oracle.rules <test-dir>

Prints one Floorspec Rules test's expected output - the report, or the measure results - as the
oracle computes it, byte for byte as expected.json holds it - by an evaluator of the draft whose suite
(conformance/rules/<draft>/) the directory is in, 0.1 otherwise."""

from __future__ import annotations

import os
import sys

from .draft import DRAFTS
from .suite import compute


def main(argv) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    where = os.path.abspath(argv[0]) + os.sep
    version = next((v for v in DRAFTS if os.sep + os.path.join('rules', v) + os.sep in where), '0.1')
    expected, _ = compute(argv[0], version)
    sys.stdout.buffer.write(expected)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

"""python3.13 -m tools.oracle.rules <test-dir>

Prints one Floorspec Rules test's expected output - the report, or the measure results - as the
oracle computes it, byte for byte as expected.json holds it."""

from __future__ import annotations

import sys

from .suite import compute


def main(argv) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    expected, _ = compute(argv[0])
    sys.stdout.buffer.write(expected)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

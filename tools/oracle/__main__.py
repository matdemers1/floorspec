"""python3.13 -m tools.oracle <test-dir | input.json> [--canonical] [--notes]

Prints the expected result for a document - {valid, diagnostics, hash?, derived?} - as JSON.
--canonical prints the canonical form instead (valid documents only); --notes also prints the
oracle's reasons for a parse or schema failure on stderr.
"""

from __future__ import annotations

import os
import sys

from .report import dumps
from .validate import check


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith('--')]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    path = args[0]
    if os.path.isdir(path):
        path = os.path.join(path, 'input.json')
    with open(path, 'rb') as f:
        data = f.read()
    result, canonical, notes = check(data)
    if '--notes' in argv:
        for n in notes:
            print(n, file=sys.stderr)
    if '--canonical' in argv:
        if canonical is None:
            print('the document is not valid; it has no canonical form', file=sys.stderr)
            return 1
        sys.stdout.buffer.write(canonical)
        return 0
    sys.stdout.write(dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

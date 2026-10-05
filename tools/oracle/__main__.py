"""python3.13 -m tools.oracle <test-dir | input.json> [--core 0.1|0.2] [--canonical] [--notes]

Prints the expected result for a document - {valid, diagnostics, hash?, derived?} - as JSON.
The reader is Core 0.2 for a test under conformance/core/0.2 and Core 0.1 otherwise, unless
--core says; a test directory's registry.json is the known extensions (Core 0.2, 12.2).
--canonical prints the canonical form instead (valid documents only); --notes also prints the
oracle's reasons for a parse or schema failure on stderr.
"""

from __future__ import annotations

import os
import sys

from .regenerate import reader_for
from .report import dumps
from .validate import READER_01, READER_02, check


def main(argv: list[str]) -> int:
    core = None
    if '--core' in argv:
        i = argv.index('--core')
        core = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith('--')]
    if len(args) != 1 or core not in (None, '0.1', '0.2'):
        print(__doc__, file=sys.stderr)
        return 2
    path = args[0]
    reader, registry = reader_for(path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path)))
    if core is not None:
        reader = READER_02 if core == '0.2' else READER_01
    if os.path.isdir(path):
        path = os.path.join(path, 'input.json')
    with open(path, 'rb') as f:
        data = f.read()
    result, canonical, notes = check(data, reader, registry)
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

"""python3.13 -m tools.oracle <test-dir | input.json> [--core 0.1|0.2|0.3] [--canonical] [--notes]

Prints the expected result for a document - {valid, diagnostics, hash?, derived?} - as JSON.
The reader is Core <v> for a test under conformance/core/<v> and Core 0.1 otherwise, unless
--core says; a test directory's registry.json is the known extensions (Core 12.2), and its
design.json the design derived (Core 19.6).
--canonical prints the canonical form instead (valid documents only); --notes also prints the
oracle's reasons for a parse or schema failure on stderr.
"""

from __future__ import annotations

import os
import sys

from .regenerate import design_for, reader_for
from .report import dumps
from .validate import READERS, check


def main(argv: list[str]) -> int:
    core = None
    if '--core' in argv:
        i = argv.index('--core')
        core = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith('--')]
    if len(args) != 1 or (core is not None and core not in READERS):
        print(__doc__, file=sys.stderr)
        return 2
    path = args[0]
    reader, registry = reader_for(path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path)))
    if core is not None:
        reader = READERS[core]
    if os.path.isdir(path):
        path = os.path.join(path, 'input.json')
    with open(path, 'rb') as f:
        data = f.read()
    design = design_for(os.path.dirname(os.path.abspath(path)))
    result, canonical, notes = check(data, reader, registry, design=design)
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

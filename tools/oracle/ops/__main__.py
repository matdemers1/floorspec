"""python3.13 -m tools.oracle.ops <test-dir> [--ops 0.1|0.2] [--document]

Prints the result the oracle computes for one Ops test - input.json (document A) and
request.json - as JSON, with every diagnostic in full (message and location included).
The draft is Ops 0.2 for a test under conformance/ops/0.2 and Ops 0.1 otherwise, unless --ops
says. --document prints B's canonical bytes instead (committed batches only).
"""

from __future__ import annotations

import json
import os
import sys

from .engine import apply
from .version import PROFILES, profile_for


def main(argv: list[str]) -> int:
    version = None
    if '--ops' in argv:
        i = argv.index('--ops')
        version = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith('--')]
    if len(args) != 1 or not os.path.isdir(args[0]) or (version is not None and version not in PROFILES):
        print(__doc__, file=sys.stderr)
        return 2
    profile = PROFILES[version] if version else profile_for(args[0])
    with open(os.path.join(args[0], 'input.json'), 'rb') as f:
        a = f.read()
    with open(os.path.join(args[0], 'request.json'), 'rb') as f:
        req = f.read()
    result, b = apply(a, req, profile)
    if '--document' in argv:
        if b is None:
            print('the batch was rejected; there is no document', file=sys.stderr)
            return 1
        sys.stdout.buffer.write(b)
        return 0
    result.pop('document', None)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

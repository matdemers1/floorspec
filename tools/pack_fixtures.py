"""python3.13 -m tools.pack_fixtures < cases.json

Evaluates rule-pack fixtures (rules/<pack>/rules/<rule>/fixtures/, FLR-T-6.3) with the oracle's
evaluator (tools/oracle/rules), for tools/build-pack.ts. Reads one JSON object from standard input,

    {"cases": [{"document": <the document's text>, "registry": [<registry entry>, ...] | null,
                "request": <an evaluation request, spec/rules 1.1>}, ...]}

and writes {"reports": [<the report of spec/rules chapter 9, as its bytes>, ...]} to standard
output. It reads nothing else and never touches the network."""

from __future__ import annotations

import json
import sys

from tools.oracle.rules.draft import CURRENT, DRAFTS
from tools.oracle.rules.evaluate import evaluate, report_bytes


def main() -> int:
    data = json.load(sys.stdin)
    reports = []
    for case in data['cases']:
        registry = case.get('registry')
        registry_bytes = None if registry is None else json.dumps(registry).encode('utf-8')
        version = case['request'].get('floorspecRules') if case['request'].get('floorspecRules') in DRAFTS else CURRENT
        report = evaluate(case['document'].encode('utf-8'), registry_bytes, json.dumps(case['request']).encode('utf-8'),
                          version)
        reports.append(report_bytes(report).decode('utf-8'))
    json.dump({'reports': reports}, sys.stdout)
    return 0


if __name__ == '__main__':
    sys.exit(main())

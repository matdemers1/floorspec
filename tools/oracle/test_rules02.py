"""Floorspec Rules 0.2 in the oracle: requests, packs and profiles of one draft only, documents read as Core 0.4
reads them, and the stair measures 0.2 adds (spec/rules 8.5) - which an evaluator of 0.1 does not know."""
import json
import unittest

from tools.oracle.rules import draft
from tools.oracle.rules.evaluate import call_measures, evaluate
from tools.oracle.rules.measures import get
from tools.oracle.rules_author02 import NO_NEWEL_DOC, SPIRAL_DOC, STRAIGHT_DOC, TAPERED_PACK, WINDER_DOC, req2


def calls(*names):
    return {'calls': [{'target': {'kind': 'stair', 'id': 'ST1'}, 'measure': n} for n in names]}


def values(doc, *names, version='0.2'):
    out = call_measures(json.dumps(doc).encode(), None, calls(*names), version)
    return [r['value'] for r in out['results']]


class Drafts(unittest.TestCase):
    def test_new_measures_are_0_2s(self):
        with draft.using('0.1'):
            self.assertIsNone(get('stairNarrowGoing', 'stair'))
            self.assertIsNotNone(get('stairHeadroom', 'stair'))
        with draft.using('0.2'):
            for n in ('stairForm', 'stairWalklineGoing', 'stairNarrowGoing'):
                self.assertIsNotNone(get(n, 'stair'), n)

    def test_an_evaluator_reads_its_own_draft(self):
        r = json.loads(json.dumps(evaluate(json.dumps(WINDER_DOC).encode(), None, json.dumps(req2(TAPERED_PACK)).encode(), '0.1')))
        self.assertEqual([d['code'] for d in r['diagnostics']], ['FS-RULES-001'])
        self.assertEqual(r['floorspecRules'], '0.1')
        r = evaluate(json.dumps(WINDER_DOC).encode(), None, json.dumps(req2(TAPERED_PACK)).encode(), '0.2')
        self.assertEqual(r['floorspecRules'], '0.2')
        self.assertEqual(r['diagnostics'], [])


class Measures(unittest.TestCase):
    def test_tapered_goings(self):
        self.assertEqual(values(WINDER_DOC, 'stairForm', 'stairWalklineGoing', 'stairNarrowGoing'), ['winder', 298160, 73901])
        self.assertEqual(values(NO_NEWEL_DOC, 'stairNarrowGoing'), [0])
        self.assertEqual(values(SPIRAL_DOC, 'stairForm', 'stairHeadroom'), ['spiral', 2008615])
        self.assertEqual(values(STRAIGHT_DOC, 'stairForm', 'stairWalklineGoing', 'stairNarrowGoing'), ['straight', None, None])

    def test_spiral_headroom_needs_core_0_4(self):
        d = dict(SPIRAL_DOC, floorspec='0.4')
        self.assertEqual(values(d, 'stairHeadroom'), [2008615])


if __name__ == '__main__':
    unittest.main()

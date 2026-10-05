"""The Floorspec Rules 0.2 conformance suite, as the script that writes it.

    python3.13 -m tools.oracle.rules_author02            rewrite every test from its declaration below
    python3.13 -m tools.oracle.rules_author02 --prune    ...and delete test directories no longer declared

The suite is the Rules 0.1 suite carried forward to 0.2 - every 0.1 test, in the same group under the
same number, on the same documents, its request, packs and profile declaring `"floorspecRules": "0.2"`
where they declared "0.1" (the two tests of a draft the evaluator does not implement now name "0.3"),
covering FS-RULES-1.2.3 and FS-RULES-8.5.2 where the 0.1 test covered the retired 1.2.1 and 8.5.1 -
evaluated by an evaluator of Rules 0.2, which reads documents as a Core 0.4 reader. A Core 0.4 reader
derives the headroom of a spiral stair, so the two stair tests whose spiral had none under 0.1 measure
it now. After them, in their groups, come the tests of what 0.2 adds: the stair measures `stairForm`,
`stairWalklineGoing` and `stairNarrowGoing` (8.5) on winder and spiral stairs of Core 0.4 documents,
synthetic rules on them, and a request and a pack of Rules 0.1, which a 0.2 evaluator does not read.

Every rule here is SYNTHETIC, as in the 0.1 suite (tools/oracle/rules_author.py): it cites the invented
code TEST-CODE with invented sections and thresholds, and states no requirement of any real code.
"""
import copy
import os
import sys

import tools.oracle.rules_author as v01                # declares the 0.1 suite: v01.TESTS
from tools.oracle.author03 import SPIRAL, WINDER_Q, hall_house
from tools.oracle.author04 import spiral_under_a_floor
from tools.oracle.rules_author import C, D, MT, R, IN, ensure, findings_of, pack, req, rule, stair

SUITE02 = os.path.join(v01.REPO, 'conformance', 'rules', '0.2')
RETIRED = {'FS-RULES-1.2.1': 'FS-RULES-1.2.3', 'FS-RULES-8.5.1': 'FS-RULES-8.5.2'}
OTHER_DRAFT = {
    # slug: its 0.2 description - the draft the evaluator does not implement moves from "0.2" to "0.3"
    'wrong-draft': 'A request that declares `"floorspecRules": "0.3"` is FS-RULES-001: this draft is 0.2.',
    'a-pack-for-another-draft': 'A pack that declares `"floorspecRules": "0.3"`: FS-RULES-004.',
}


def _redraft(v, old, new):
    """Every object's floorspecRules `old` made `new`, through requests, packs and profiles."""
    if isinstance(v, dict):
        return {k: (new if k == 'floorspecRules' and x == old else _redraft(x, old, new)) for k, x in v.items()}
    if isinstance(v, list):
        return [_redraft(x, old, new) for x in v]
    return v


def carry(tc):
    tc = copy.deepcopy(tc)
    tc['covers'] = [RETIRED.get(c, c) for c in tc['covers']]
    if tc['kind'] == 'report':
        if tc['slug'] in OTHER_DRAFT:
            tc['request'] = _redraft(tc['request'], '0.2', '0.3')
            tc['description'] = OTHER_DRAFT[tc['slug']]
        tc['request'] = _redraft(tc['request'], '0.1', '0.2')
        if tc['raw_request'] is not None:
            tc['raw_request'] = tc['raw_request'].replace(b'"floorspecRules": "0.1"', b'"floorspecRules": "0.2"')
    if tc['slug'] in STAIRS_02:
        STAIRS_02[tc['slug']](tc)
    return tc


# The two 0.1 tests on the rules house's stairs: its spiral, ST2, has a headroom under Rules 0.2, which reads the
# document as Core 0.4 does - under the bedroom's ceiling, 2700 mm above its foot - so its value is measured, and the
# headroom rule applies to it and finds it too low.
def _stair_measures(tc):
    tc['description'] = tc['description'].replace(
        'the spiral has neither a headroom Core derives nor a handrail, so both are null.',
        'the spiral has a headroom Core 0.4 derives - under the bedroom\'s ceiling at 2700 mm, over its highest tread, '
        'its 14th riser up, 180 mm - and no handrail, which is null.')
    tc['expect'][8] = 180 * 1280


def _stair_rules(tc):
    tc['description'] = tc['description'].replace(
        'only ST1 has a headroom - the rule applies only where one is derived - and at about 4\' 11" it may not meet 6\' 8";',
        'both have a headroom under Rules 0.2, which reads the document as Core 0.4 does - ST1\'s, at about 4\' 11", and the '
        'spiral\'s, 180 mm under the bedroom\'s ceiling - and both may not meet 6\' 8";')
    tc['found'] = sorted(tc['found'] + [('test-pack', 'HEADROOM', 'ST2')])

    def check(r):
        f = findings_of(r, 'HEADROOM')
        ensure([x['subject'] for x in f] == [stair('ST1'), stair('ST2')], f)
        ensure([e['subjects'] for e in r['evaluated'] if e['rule'] == 'HEADROOM'] == [2], r['evaluated'])
    tc['check'] = check


def _same_report(tc):
    import json
    from tools.oracle.rules.evaluate import evaluate, report_bytes
    def check(r):
        expected = evaluate(json.dumps(v01.DEMO).encode(), json.dumps(v01.KNOWN).encode(),
                            json.dumps(_redraft(req(v01.EXAMPLE_PACK), '0.1', '0.2')).encode(), '0.2')
        ensure(report_bytes(r) == report_bytes(expected), 'the same report')
    tc['check'] = check


STAIRS_02 = {'stair-measures': _stair_measures, 'stair-rules': _stair_rules, 'same-report-whatever-the-order': _same_report}

BASE = [carry(tc) for tc in v01.TESTS]
del v01.TESTS[:]


def v4(d):
    d = copy.deepcopy(d)
    d['floorspec'] = '0.4'
    return d


def req2(*packs, **kw):
    return _redraft(req(*packs, **kw), '0.1', '0.2')


def pack2(rules, **kw):
    return {**pack(rules, **kw), 'floorspecRules': '0.2'}


# ============================================================================= request and packs (0.2)
R('request', 'a-rules-0.1-request', 'A request that declares `"floorspecRules": "0.1"`: an evaluator of Rules 0.2 '
  'implements 0.2 alone, so it is FS-RULES-001 (1.1.1).', ['FS-RULES-1.1.1'], v01.house(),
  {**req2(v01.SIMPLE), 'floorspecRules': '0.1'}, diags=[D('FS-RULES-001')])
R('packs', 'a-rules-0.1-pack', 'A pack that declares `"floorspecRules": "0.1"` in a 0.2 request: FS-RULES-004 (2.1.1).',
  ['FS-RULES-2.1.1'], v01.house(), {**req2(), 'packs': [pack({'SMOKE': v01.SMOKE})]},
  diags=[D('FS-RULES-004', packIndex=0)])

# ============================================================================= tapered stairs (0.2): 8.5
# The Core 0.4 suite's quarter-turn winder stair with a 100 mm newel (core/0.4/stairs/050-winder-with-newel): 3
# winders of 30 degrees, each 900 sin 15 mm deep on the walkline and 100 tan 30 mm at its narrow end; and its spiral
# stair under a floor (core/0.4/stairs/057): 12 treads of 22.5 degrees, 1000 sin 11.25 mm deep on the walkline and
# 200 sin 11.25 mm at its column.
WINDER_DOC = v4(hall_house(x0=1000, x1=2800, y1=2800, form={**WINDER_Q, 'newel': 100 * 1280}))
NO_NEWEL_DOC = v4(hall_house(x0=1000, x1=2800, y1=2800, form=WINDER_Q))
SPIRAL_DOC = spiral_under_a_floor()
STRAIGHT_DOC = v4(hall_house())
ST1 = stair('ST1')
TAPERED = [(ST1, 'stairForm', None), (ST1, 'stairWalklineGoing', None), (ST1, 'stairNarrowGoing', None)]
MT('measures-stairs', 'winder-measures',
   'The stair measures 0.2 adds on a quarter-turn winder stair with a newel, a Core 0.4 document: its form, the least '
   'going of its winders at the walkline, 900 sin 15 mm, and at their narrow ends, 100 tan 30 mm - Core\'s '
   'walklineGoing and narrowGoing (Core 17.7) - and its tread depth, 250 mm, the going of its straight treads.',
   ['FS-RULES-8.5.2', 'FS-RULES-4.7.1'], WINDER_DOC, TAPERED + [(ST1, 'stairTreadDepth', None)],
   ['winder', 298160, 73901, 250 * 1280], registry=None)
MT('measures-stairs', 'spiral-measures',
   'The same measures on a spiral stair 1800 mm across and 800 mm wide, with a 100 mm column, under a floor: its form, '
   'its going at the walkline, 1000 sin 11.25 mm, and at its column, 200 sin 11.25 mm; its width, the clear width '
   'from its column to its edge; and its headroom, which Core 0.4 derives for a spiral and Core 0.3 did not.',
   ['FS-RULES-8.5.2', 'FS-RULES-4.7.1'], SPIRAL_DOC,
   TAPERED + [(ST1, 'stairWidth', None), (ST1, 'stairHeadroom', None), (ST1, 'stairRiserHeight', None)],
   ['spiral', 249716, 49943, 800 * 1280, 2008615, 265846], registry=None)
MT('measures-stairs', 'straight-has-no-tapered-treads',
   'A straight stair has no tapered treads: its form is "straight", and the two goings of tapered treads have no '
   'value (4.2).', ['FS-RULES-8.5.2', 'FS-RULES-4.7.1'], STRAIGHT_DOC, TAPERED, ['straight', None, None], registry=None)

WINDERS = {'to': 'stair', 'where': C('stairForm', '=', 'winder')}
SPIRALS = {'to': 'stair', 'where': C('stairForm', '=', 'spiral')}
TAPERED_PACK = pack2({
    'WINDER-WALKLINE': rule(WINDERS, C('stairWalklineGoing', '>=', 10 * IN), section='§4.5',
                            title='Winders at least 10 in deep at the walkline'),
    'WINDER-NARROW': rule(WINDERS, C('stairNarrowGoing', '>=', 6 * IN), section='§4.6',
                          title='Winders at least 6 in deep at the narrow end'),
    'SPIRAL-WIDTH': rule(SPIRALS, C('stairWidth', '>=', 26 * IN), section='§4.7', title='Spiral stairs 26 in wide'),
})
R('measures-stairs', 'winder-rules',
  'Synthetic winder rules on the winder stair with a newel: its winders are 232.9 mm deep at the walkline, under 10 in, '
  'and 57.7 mm at their narrow ends, under 6 in, so it may not meet either; the spiral rule applies to no stair here.',
  ['FS-RULES-8.5.2', 'FS-RULES-3.4.1', 'FS-RULES-3.8.1'], WINDER_DOC, req2(TAPERED_PACK), registry=None,
  found=[('WINDER-NARROW', 'ST1'), ('WINDER-WALKLINE', 'ST1')],
  check=lambda r: ensure([(e['rule'], e['subjects']) for e in r['evaluated']]
                         == [('SPIRAL-WIDTH', 0), ('WINDER-NARROW', 1), ('WINDER-WALKLINE', 1)], r['evaluated']))
R('measures-stairs', 'spiral-rules',
  'The same pack on the spiral stair, 800 mm wide - more than 26 in - so the spiral rule finds nothing, and the winder '
  'rules apply to no stair.', ['FS-RULES-8.5.2', 'FS-RULES-3.4.1'], SPIRAL_DOC, req2(TAPERED_PACK), registry=None,
  check=lambda r: ensure([(e['rule'], e['subjects']) for e in r['evaluated']]
                         == [('SPIRAL-WIDTH', 1), ('WINDER-NARROW', 0), ('WINDER-WALKLINE', 0)], r['evaluated']))
R('measures-stairs', 'winders-to-a-point',
  'A winder stair with no newel: its winders meet at the pivot, so its narrowGoing is 0 and the narrow-end rule finds '
  'it; at the walkline its winders are as deep as with a newel.', ['FS-RULES-8.5.2'], NO_NEWEL_DOC, req2(TAPERED_PACK),
  registry=None, found=[('WINDER-NARROW', 'ST1'), ('WINDER-WALKLINE', 'ST1')])
R('measures-stairs', 'tapered-measures-in-rules-0.1',
  'A request of Rules 0.2 whose rule reads stairNarrowGoing is well typed; the same measure in a rule of a 0.1 pack '
  'is never read, since the pack is FS-RULES-004 - an evaluator of 0.2 reads only 0.2 packs.', ['FS-RULES-2.1.1', 'FS-RULES-3.9.1'],
  WINDER_DOC, {**req2(), 'packs': [{**TAPERED_PACK, 'floorspecRules': '0.1'}]}, registry=None,
  diags=[D('FS-RULES-004', packIndex=0)])

NEW = list(v01.TESTS)
del v01.TESTS[:]


def main(argv) -> int:
    return 1 if v01.write_all(prune='--prune' in argv, tests=BASE + NEW, suite=SUITE02, version='0.2') else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

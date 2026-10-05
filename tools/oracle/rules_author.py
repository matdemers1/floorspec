"""The Floorspec Rules 0.1 conformance suite, as the script that writes it.

    python3.13 -m tools.oracle.rules_author            rewrite every test from its declaration below
    python3.13 -m tools.oracle.rules_author --prune    ...and delete test directories no longer declared

The suite is conformance/rules/0.1/, run by an evaluator that implements the four official
extensions at 0.1.0 and is configured with the test's registry.json as its known extensions (none
when the test has none). Two kinds of test share it:

- **report tests**: input.json (a document), request.json (an evaluation request: packs, profile,
  units) and expected.json - the report, byte for byte (spec/rules 9.8);
- **measure tests**, in the `measures-*` groups: input.json, measures.json (a list of measure calls,
  each a target, a measure and its arguments) and expected.json - `{ "results": [ ... ] }`, the
  measure results (4.7), written as a report is.

Every rule in every pack here is SYNTHETIC: it cites the invented codes TEST-CODE and TEST-ELEC (or,
for the default profile only, the real codes' names with a section `TEST-n` and a paraphrase that
says it states no requirement of that code), with invented thresholds. No requirement of a real
code is encoded in this suite; real packs are rules/ (FLR-T-6.4 to 6.7).

Every expected diagnostic and every expected finding (pack, rule, subject) is written by hand and
cross-checked against the oracle; measure values are written by hand where a reviewer can check
them (axis-aligned walls, round numbers) and the oblique ones come from the oracle, bounded by hand.
"""
import copy
import json
import os
import shutil
import sys

from tools.oracle import canon
from tools.oracle.author_lib import fmt
from tools.oracle.ext_author import box, entry, env, on_surface, on_wall, PLATE
from tools.oracle.rules.evaluate import call_measures, check_document, evaluate, report_bytes
from tools.oracle.rules.structure import NOTICE, assures

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
SUITE = os.path.join(REPO, 'conformance', 'rules', '0.1')
MM, FT, IN = 1280, 390144, 32512
H = 2700 * MM
SQFT = 152212340736
ELEC, PLMB, MECH, LOWV = 'FS_electrical', 'FS_plumbing', 'FS_mechanical', 'FS_lowvoltage'
KNOWN = [entry(ELEC), entry(MECH), entry(LOWV)]
INSIDE = 12 * FT - 128000          # a 12' bay between 100 mm centred walls, inside the finished faces


# ============================================================================= the rules house

def J(x, y, level='L1'):
    return {'level': level, 'position': [x, y]}


def W(s, e, level='L1', **kw):
    return {'level': level, 'start': s, 'end': e, 'type': 'WT', **kw}


def house():
    """Three 12'-deep rooms in a row on L1, every wall 100 mm thick, centred, drawn clockwise:

        J2 ----W2---- J3 ----W3---- J4 ---W4--- J5
        |  Bedroom R1 |  Living R2  | Utility R3 |
        W1     O1     W9  O5       W10          W5   X1 panel on W5 (inside)
        |            O2            O4            |
        J1 ----W8---- J8 ----W7---- J7 ---W6--- J6
                            O3 (front door)

    J1 (0, 0), J2 (0, 12'), J3 (12', 12'), J4 (24', 12'), J5 (32', 12'), J6 (32', 0), J7 (24', 0),
    J8 (12', 0). O1 and O5 are 3' x 4' windows with a 2' sill in the north walls; O2, O3 and O4 are
    3' x 6'8" doors. R1 has a smoke alarm X3 on its ceiling and receptacles X4 (west wall) and X5
    (south wall), on circuit C1 with the alarm; R3 has the panel X1, 3' from the north-east corner,
    with a working space 1000 mm deep, and an electric boiler X2 standing free of it."""
    return {
        'floorspec': '0.2', 'project': {'name': 'The rules house'},
        'buildings': {'B1': {}}, 'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
        'types': {'WT': {'kind': 'wallType', 'layers': [{'thickness': 100 * MM, 'function': 'core'}]},
                  'WIN': {'kind': 'windowType', 'width': 3 * FT, 'height': 4 * FT, 'sill': 2 * FT},
                  'DOOR': {'kind': 'doorType', 'width': 3 * FT, 'height': 80 * IN}},
        'junctions': {'J1': J(0, 0), 'J2': J(0, 12 * FT), 'J3': J(12 * FT, 12 * FT), 'J4': J(24 * FT, 12 * FT),
                      'J5': J(32 * FT, 12 * FT), 'J6': J(32 * FT, 0), 'J7': J(24 * FT, 0), 'J8': J(12 * FT, 0)},
        'walls': {'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J5'),
                  'W5': W('J5', 'J6'), 'W6': W('J6', 'J7'), 'W7': W('J7', 'J8'), 'W8': W('J8', 'J1'),
                  'W9': W('J8', 'J3'), 'W10': W('J7', 'J4')},
        'openings': {'O1': {'wall': 'W2', 'offset': 4 * FT, 'fill': 'WIN'},
                     'O2': {'wall': 'W9', 'offset': 4 * FT, 'fill': 'DOOR'},
                     'O3': {'wall': 'W7', 'offset': 4 * FT, 'fill': 'DOOR'},
                     'O4': {'wall': 'W10', 'offset': 4 * FT, 'fill': 'DOOR'},
                     'O5': {'wall': 'W3', 'offset': 4 * FT, 'fill': 'WIN'}},
        'rooms': {'R1': {'level': 'L1', 'anchor': [6 * FT, 6 * FT], 'name': 'Bedroom', 'function': 'sleeping'},
                  'R2': {'level': 'L1', 'anchor': [18 * FT, 6 * FT], 'name': 'Living', 'function': 'living'},
                  'R3': {'level': 'L1', 'anchor': [28 * FT, 6 * FT], 'name': 'Utility', 'function': 'mechanical'}},
        'extensionsUsed': {ELEC: '0.1.0', MECH: '0.1.0'},
        'extensions': {
            ELEC: {
                'collections': {
                    'panels': {'X1': on_wall('W5', 'right', 3 * FT, 1200, box(0, -200, -400, 100, 200, 400),
                                             volts=[120, 240], rating=100, mainBreaker=100, spaces=20,
                                             clearances={'working': env('workingSpace', box(0, -400, -1200, 1000, 400, 800))})},
                    'alarms': {'X3': on_surface('R1', 'ceiling', 6 * FT, 6 * FT, box(-75, -75, -50, 75, 75, 0), detects=['smoke'])},
                    'receptacles': {'X4': on_wall('W1', 'right', 6 * FT, 300, PLATE),
                                    'X5': on_wall('W8', 'right', 6 * FT, 300, PLATE)}},
                'circuits': {'C1': {'panel': 'X1', 'breaker': 15, 'volts': 120, 'rating': 15, 'space': 1,
                                    'protection': ['afci'], 'loads': ['X3', 'X4', 'X5']}}},
            MECH: {
                'collections': {
                    'equipment': {'X2': on_surface('R3', 'floor', 26 * FT, 3 * FT, box(-300, -300, 0, 300, 300, 900),
                                                   equipment='boiler',
                                                   clearances={'service': env('workingSpace', box(300, -375, 0, 1050, 375, 2000))})}}},
        },
    }


def edit(fn, base=house):
    d = base()
    fn(d)
    return d


def coll(d, name, c):
    return d['extensions'][name]['collections'][c]


def boiler_beside_panel(d):
    """The boiler moved against the east wall, facing west, its side 200 mm into the panel's
    working space (the Phase 6 demo)."""
    x = coll(d, MECH, 'equipment')['X2']
    x['host'] = {'mode': 'surface', 'room': 'R3', 'surface': 'floor',
                 'position': [32 * FT - 64000 - 300 * MM, 9 * FT - 500 * MM], 'rotation': 180000000}


def no_bedroom_window(d):
    del d['openings']['O1']


def furniture(d, pieces):
    """An optional extension no evaluator implements: its elements are found from their core
    members alone (Core 1.6.9)."""
    d['extensionsUsed']['EXT_furniture'] = '0.1'
    d['extensions']['EXT_furniture'] = {'collections': {'pieces': pieces}}


# ============================================================================= packs, rules, profiles

PROV = {'verifiedBy': 'Floorspec conformance suite', 'verifiedOn': '2026-10-04', 'edition': '2024'}


def C(measure, op, value, **args):
    t = {'measure': measure, 'op': op, 'value': value}
    if args:
        t['args'] = args
    return t


def rule(applies, requirement, select=None, exceptions=None, severity='mayNotMeet', code='TEST-CODE', edition='2024',
         section='§1.1', title='A synthetic rule', paraphrase=None, link=None, provenance=None):
    r = {'title': title, 'citation': {'code': code, 'edition': edition, 'section': section},
         'paraphrase': paraphrase or f'A synthetic rule for the conformance suite ({title.lower()}); it states no requirement of any real code.',
         'applies': applies}
    if link:
        r['citation']['link'] = link
    if select is not None:
        r['select'] = select
    r['requirement'] = requirement
    if exceptions is not None:
        r['exceptions'] = exceptions
    r['severity'] = severity
    r['provenance'] = provenance or {**PROV, 'edition': edition}
    return r


def pack(rules, name='test-pack', version='0.1.0', coverage=None, title='Synthetic conformance rules', **extra):
    p = {'floorspecRules': '0.1', 'name': name, 'version': version, 'title': title, 'license': 'CC-BY-4.0', 'rules': rules}
    if coverage is not None:
        p['coverage'] = coverage
    p.update(extra)
    return p


PROFILE = {'floorspecRules': '0.1', 'name': 'Test jurisdiction',
           'adopts': [{'code': 'TEST-CODE', 'edition': '2024'}, {'code': 'TEST-ELEC', 'edition': '2026'}]}


def req(*packs, profile=PROFILE, units=None, design=None):
    r = {'floorspecRules': '0.1', 'packs': list(packs)}
    if profile is not None:
        r['profile'] = profile
    if units is not None:
        r['units'] = units
    if design is not None:
        r['design'] = design
    return r


SLEEPING = {'to': 'room', 'where': C('roomFunction', '=', 'sleeping')}
PANELS = {'to': 'element', 'extension': ELEC, 'collection': 'panels'}

# The synthetic rules of the examples: invented sections, invented thresholds.
ESCAPE = rule(SLEEPING, {'all': [C('openingArea', '>=', 5 * SQFT), C('openingSillHeight', '<=', 40 * IN),
                                 C('openingWidth', '>=', 18 * IN), C('openingHeight', '>=', 22 * IN)]},
              select={'from': 'openings', 'args': {'to': 'outside'}, 'where': C('openingKind', 'in', ['window', 'door']), 'need': 'any'},
              severity='check', section='§3.1', title='Escape opening in every sleeping room',
              paraphrase='Synthetic: every sleeping room has a window or door to the outside of at least 5 sq ft, with its '
                         'sill no higher than 40 in, at least 18 in wide and 22 in high. The rule measures the opening as drawn, '
                         'not its net clear opening. It states no requirement of any real code.',
              link='https://example.com/test-code/2024/3.1')
WORKSPACE = rule(PANELS, {'all': [C('envelopeObstructions', '=', 0), C('clearDepthInFront', '>=', 30 * IN, limit=30 * IN)]},
                 select={'from': 'envelopes', 'args': {'purpose': 'workingSpace'}, 'need': 'any'},
                 code='TEST-ELEC', edition='2026', section='§4.2', title='Clear working space in front of a panel',
                 paraphrase='Synthetic: a panel has a declared working space that nothing stands in, clear for 30 in in front '
                            'of it. It states no requirement of any real code.')
SMOKE = rule(SLEEPING, C('elementCount', '>=', 1, extension=ELEC, collection='alarms', match={'detects': 'smoke'}),
             section='§5.1', title='A smoke alarm in every sleeping room')
EXAMPLE_PACK = pack({'ESCAPE': ESCAPE, 'SMOKE': SMOKE, 'WORKSPACE': WORKSPACE},
                    coverage=[{'code': 'TEST-CODE', 'edition': '2024', 'section': '§3', 'status': 'partial',
                               'note': 'The escape opening is measured as drawn; net clear openings are not checked.'},
                              {'code': 'TEST-CODE', 'edition': '2024', 'section': '§5', 'status': 'addressed'},
                              {'code': 'TEST-ELEC', 'edition': '2026', 'section': '§4', 'status': 'partial'},
                              {'code': 'TEST-ELEC', 'edition': '2026', 'section': '§9', 'status': 'notAddressed'}])


# ============================================================================= declaring tests

TESTS = []


def D(code, **members):
    sev = {'FS-RULES-008': 'info', 'FS-RULES-009': 'info', 'FS-RULES-010': 'warning', 'FS-RULES-011': 'warning'}.get(code, 'error')
    return {'code': code, 'severity': sev, **members}


def R(group, slug, description, covers, doc, request, registry=KNOWN, diags=(), found=(), check=None, raw_request=None):
    """A report test. diags: the expected diagnostics; found: the expected findings, as
    (rule, subject) for the pack test-pack or (pack, rule, subject) - both written by hand."""
    TESTS.append(dict(kind='report', group=group, slug=slug, description=description, covers=list(covers), doc=doc,
                      request=request, raw_request=raw_request, registry=registry, diags=list(diags),
                      found=sorted(f if len(f) == 3 else ('test-pack',) + tuple(f) for f in found), check=check))


def MT(group, slug, description, covers, doc, calls, expect, registry=KNOWN, units=None, check=None):
    """A measure test. calls: (target, measure, args); expect: the value each call returns, by hand,
    or Ellipsis where the oracle computes it (and check bounds it)."""
    c = {'calls': [{'target': t, 'measure': m, **({'args': a} if a else {})} for t, m, a in calls]}
    if units is not None:
        c['units'] = units
    TESTS.append(dict(kind='measures', group=group, slug=slug, description=description, covers=list(covers), doc=doc,
                      calls=c, expect=list(expect), registry=registry, check=check))


def room(i):
    return {'kind': 'room', 'id': i}


def opening(i):
    return {'kind': 'opening', 'id': i}


def element(i):
    return {'kind': 'element', 'id': i}


def envelope(i, n):
    return {'kind': 'envelope', 'id': i, 'envelope': n}


def level(i):
    return {'kind': 'level', 'id': i}


def ensure(cond, what):
    if not cond:
        raise AssertionError(what)


def findings_of(r, rule_id):
    return [f for f in r['findings'] if f['rule'] == rule_id]


# ============================================================================= examples
DEMO = edit(lambda d: (boiler_beside_panel(d), no_bedroom_window(d)))

R('examples', 'rules-house-no-findings',
  'The rules house under the test jurisdiction, with the three synthetic rules of the examples: an escape opening in '
  'every sleeping room, a smoke alarm in every sleeping room, and a clear working space in front of every panel. Each '
  'rule is evaluated, on one subject, and none gives a finding; the report lists them in `evaluated` with 0 findings, '
  'carries the coverage entries of the editions in force and the notice, and names nothing as passing.',
  ['FS-RULES-1.1.1', 'FS-RULES-1.2.1', 'FS-RULES-3.4.1', 'FS-RULES-3.5.1', 'FS-RULES-9.1.1', 'FS-RULES-9.1.2',
   'FS-RULES-9.8.1', 'FS-RULES-9.9.1', 'FS-RULES-11.1.1'],
  house(), req(EXAMPLE_PACK),
  check=lambda r: (ensure([e['findings'] for e in r['evaluated']] == [0, 0, 0], 'no findings'),
                   ensure(r['notice'] == NOTICE, 'the notice'), ensure(len(r['coverage']) == 4, 'four coverage entries')))


def check_demo(r):
    ws = findings_of(r, 'WORKSPACE')[0]
    ensure(ws['subject'] == element('X1') and ws['candidates'] == [envelope('X1', 'working')], 'the panel and its space')
    ensure([(m['measure'], m['value'], m['holds'], m['involved']) for m in ws['measures']]
           == [('envelopeObstructions', 1, False, ['X2']), ('clearDepthInFront', 0, False, ['X2'])], 'the boiler obstructs')
    ensure(ws['elements'] == ['X1', 'X2'], 'elements')
    ensure([s['kind'] for s in ws['location']['shapes']] == ['polygon'] * 3 and ws['location']['level'] == 'L1', 'three shapes')
    ensure(ws['message'] == 'X1 may not meet TEST-ELEC 2026 §4.2 (Clear working space in front of a panel).', 'message')
    es = findings_of(r, 'ESCAPE')[0]
    ensure(es['candidates'] == [] and es['measures'] == [] and es['severity'] == 'check', 'no escape opening at all')
    ensure(es['location']['shapes'][0]['outer'][0] == [64000, 64000], 'the bedroom is drawn')
    ensure(es['message'].startswith('R1 may not meet TEST-CODE 2024 §3.1 (Escape opening in every sleeping room). Check it'), 'message')


R('examples', 'p6-demo-boiler-beside-panel-bedroom-without-window',
  'The Phase 6 demo, with synthetic rules: the boiler is moved beside the panel, into its working space, and the '
  'bedroom loses its only window. Two findings: X1 may not meet TEST-ELEC 2026 §4.2 - its working space is '
  'obstructed by X2 and clear for 0 in, both measured conditions listed with X2 involved, and the panel, the space and '
  'the boiler drawn on L1 - and R1 may not meet TEST-CODE 2024 §3.1, with no candidate opening to the outside, as a '
  '`check` because the rule measures openings as drawn. Each message names the code, edition and section.',
  ['FS-RULES-3.5.1', 'FS-RULES-3.6.1', 'FS-RULES-9.2.1', 'FS-RULES-9.3.1', 'FS-RULES-9.4.1', 'FS-RULES-9.5.1',
   'FS-RULES-9.5.2', 'FS-RULES-1.5.1', 'FS-RULES-1.5.2', 'FS-RULES-7.6.1', 'FS-RULES-7.7.1', 'FS-RULES-9.8.1'],
  DEMO, req(EXAMPLE_PACK), found=[('ESCAPE', 'R1'), ('WORKSPACE', 'X1')], check=check_demo)

R('examples', 'same-report-whatever-the-order',
  'The Phase 6 demo again, with the pack\'s rules and its coverage entries written in another order, and an empty '
  'second pack before it in the request: the report is the same, finding for finding and byte for byte, except for '
  'the second pack\'s absence from every list (it has no rules). Evaluation is a function of its inputs, not of the '
  'order they are written in.',
  ['FS-RULES-1.4.1', 'FS-RULES-9.7.1'],
  DEMO, req(pack({}, name='empty-pack', title='No rules'),
            pack({'WORKSPACE': WORKSPACE, 'SMOKE': SMOKE, 'ESCAPE': ESCAPE}, coverage=list(reversed(EXAMPLE_PACK['coverage'])))),
  found=[('ESCAPE', 'R1'), ('WORKSPACE', 'X1')],
  check=lambda r: ensure(report_bytes(r) == report_bytes(evaluate(json.dumps(DEMO).encode(), json.dumps(KNOWN).encode(),
                                                                  json.dumps(req(EXAMPLE_PACK)).encode())), 'the same report'))

ESCAPE_2021 = rule(SLEEPING, C('openingArea', '>=', 7 * SQFT),
                   select={'from': 'openings', 'args': {'to': 'outside'}, 'need': 'any'},
                   edition='2021', section='§3.1', title='Escape opening in every sleeping room (2021)')
R('examples', 'the-profile-changes-and-the-findings-follow',
  'The rules house with the escape rule written for two editions of TEST-CODE, and a profile adopting 2021: only the '
  '2021 rule, whose synthetic threshold is 7 sq ft, is in force, and the bedroom\'s 12 sq ft window passes it; the '
  '2024 rule is listed with the reason "edition". Evaluating the same document and pack under another profile is how '
  'findings follow a jurisdiction (10.7).',
  ['FS-RULES-10.3.1', 'FS-RULES-1.4.1'],
  house(), req(pack({'ESCAPE': ESCAPE, 'ESCAPE-2021': ESCAPE_2021}),
               profile={**PROFILE, 'adopts': [{'code': 'TEST-CODE', 'edition': '2021'}]}),
  check=lambda r: (ensure([e['rule'] for e in r['evaluated']] == ['ESCAPE-2021'], 'only 2021'),
                   ensure(r['notEvaluated'] == [{'pack': 'test-pack', 'version': '0.1.0', 'rule': 'ESCAPE', 'reason': 'edition'}], 'edition')))

R('examples', 'the-same-under-2021-with-a-smaller-window',
  'The same pack and profile as the previous test, with the bedroom window 3\' x 2\' (6 sq ft): now the 2021 rule, in '
  'force, gives R1 a finding; the 2024 rule is not evaluated.',
  ['FS-RULES-10.3.1', 'FS-RULES-3.6.1'],
  edit(lambda d: d['openings']['O1'].update(height=2 * FT)),
  req(pack({'ESCAPE': ESCAPE, 'ESCAPE-2021': ESCAPE_2021}), profile={**PROFILE, 'adopts': [{'code': 'TEST-CODE', 'edition': '2021'}]}),
  found=[('ESCAPE-2021', 'R1')])


# ============================================================================= the request (1.1, 1.3)
SIMPLE = pack({'SMOKE': SMOKE})
INVALID_DOC = edit(lambda d: d['walls']['W1'].update(start='J9'))         # a dangling reference: FS-INV-002

R('request', 'not-json', 'A request that is not a well-formed JSON text is reported with FS-RULES-001 and nothing else is '
  'evaluated: the report has the notice and empty lists, and no units, profile or hash.',
  ['FS-RULES-1.1.1', 'FS-RULES-11.1.1', 'FS-RULES-9.1.1'], house(), None, raw_request=b'{"floorspecRules": "0.1", "packs": [}\n',
  diags=[D('FS-RULES-001')], check=lambda r: ensure('units' not in r and 'profile' not in r and 'hash' not in r, 'bare report'))
R('request', 'no-packs', 'A request without `packs` does not match the request schema: FS-RULES-001.',
  ['FS-RULES-1.1.1'], house(), {'floorspecRules': '0.1', 'profile': PROFILE}, diags=[D('FS-RULES-001')])
R('request', 'unknown-member', 'A request with a member the request schema does not list (`document`) is FS-RULES-001.',
  ['FS-RULES-1.1.1'], house(), {**req(SIMPLE), 'document': {}}, diags=[D('FS-RULES-001')])
R('request', 'units-not-a-unit', 'A request whose `units` is "furlongs" is FS-RULES-001.',
  ['FS-RULES-1.1.1'], house(), req(SIMPLE, units='furlongs'), diags=[D('FS-RULES-001')])
R('request', 'wrong-draft', 'A request that declares `"floorspecRules": "0.2"` is FS-RULES-001: this draft is 0.1.',
  ['FS-RULES-1.1.1'], house(), {**req(SIMPLE), 'floorspecRules': '0.2'}, diags=[D('FS-RULES-001')])
_dup = json.dumps(req(SIMPLE), indent=2).replace('"SMOKE": {', '"SMOKE": {"title": "x"}, "SMOKE": {', 1).encode('utf-8')
R('request', 'two-rules-of-one-id', 'A pack whose `rules` object names SMOKE twice makes the request a JSON text with a '
  'duplicate member name, which is not well formed (Core 9.1.2): FS-RULES-001, and nothing is evaluated.',
  ['FS-RULES-1.1.1'], house(), None, raw_request=_dup + b'\n', diags=[D('FS-RULES-001')])
R('request', 'only-the-first-failing-step', 'A malformed request, with a malformed profile, for an invalid document: only '
  'FS-RULES-001 is reported - an evaluator stops at the first of steps 1 to 3 that fails.',
  ['FS-RULES-1.3.1', 'FS-RULES-1.1.1'], INVALID_DOC, {'floorspecRules': '0.1', 'packs': 'none', 'profile': {'name': 'x'}},
  diags=[D('FS-RULES-001')])
R('request', 'metric-units', 'A request with `"units": "metric"`: the report says so, and every display is in millimetres '
  'and square metres, each rounded once: R1 is 4,553,728 base units wide (3,557.6 mm, displayed `3558 mm`) and its net '
  'area 12.6565 m2 (displayed `12.66 m²`); the thresholds, 4 m and 20 m2, display the same way.',
  ['FS-RULES-1.1.1', 'FS-RULES-9.6.1'], house(),
  req(pack({'WIDE': rule(SLEEPING, {'all': [C('roomLeastWidth', '>=', 4 * 1280000), C('roomNetArea', '>=', 20 * 1638400000000)]})}),
      units='metric'), found=[('WIDE', 'R1')],
  check=lambda r: ensure([m['display'] for m in r['findings'][0]['measures']] == ['3558 mm', '12.66 m²']
                         and [m['thresholdDisplay'] for m in r['findings'][0]['measures']] == ['4000 mm', '20.00 m²']
                         and r['units'] == 'metric', 'metric displays'))


# ============================================================================= the document (1.2)
R('document', 'invalid-document', 'A document with a wall whose start junction does not exist is invalid (Core FS-INV-002): '
  'the report has FS-RULES-003, its units and profile, no hash and no finding.',
  ['FS-RULES-1.2.1', 'FS-RULES-11.1.1'], INVALID_DOC, req(SIMPLE), diags=[D('FS-RULES-003')],
  check=lambda r: ensure(r['profile'] == 'Test jurisdiction' and 'hash' not in r and r['evaluated'] == [], 'nothing evaluated'))
R('document', 'invalid-by-an-extension-the-evaluator-knows', 'The rules house with circuit C1 on a panel that does not '
  'exist: valid to a reader that does not know FS_electrical, but this evaluator knows it (registry.json) and its '
  'validator reports FS-ELEC-INV-002, so the document is invalid: FS-RULES-003.',
  ['FS-RULES-1.2.1'], edit(lambda d: d['extensions'][ELEC]['circuits']['C1'].update(panel='X99')), req(SIMPLE),
  diags=[D('FS-RULES-003')])
R('document', 'valid-without-known-extensions', 'The same document, for an evaluator configured with no known '
  'extensions: FS_electrical is not evaluated, the document is valid, and the rules that read only core members are '
  'evaluated - the smoke-alarm rule reads FS_electrical\'s `detects` and is not (FS-RULES-009).',
  ['FS-RULES-1.2.1', 'FS-RULES-3.10.1'], edit(lambda d: d['extensions'][ELEC]['circuits']['C1'].update(panel='X99')),
  req(pack({'SMOKE': SMOKE, 'ROOMS': rule({'to': 'level'}, C('roomCount', '>=', 3))})), registry=None,
  diags=[D('FS-RULES-009', pack='test-pack', rule='SMOKE')])
R('document', 'invalid-document-and-a-bad-pack', 'An invalid document and a malformed pack: only FS-RULES-003 - the packs '
  'are step 4, which is not taken.', ['FS-RULES-1.3.1'], INVALID_DOC, req(pack({}, license='MIT')),
  diags=[D('FS-RULES-003')])



def utility_options(d):
    """The rules house as a Core 0.3 document with an option set for the utility room, RS: option RA (primary)
    leaves it as it is; option RB draws a closed square of separators in it, 25' to 26'6" by 7' to 9', with a pantry
    room R4 inside - a fourth room on L1."""
    d['floorspec'] = '0.3'
    d['optionSets'] = {'RS': {'name': 'Utility', 'primary': 'RA'}}
    d['options'] = {'RA': {'set': 'RS'}, 'RB': {'set': 'RS'}}
    pts = [(25 * FT, 7 * FT), (25 * FT, 9 * FT), (53 * FT // 2, 9 * FT), (53 * FT // 2, 7 * FT)]
    for i, (x, y) in enumerate(pts, 1):
        d['junctions'][f'P{i}'] = {**J(x, y), 'option': 'RB'}
    d['separators'] = {f'PS{i}': {'level': 'L1', 'start': f'P{i}', 'end': f'P{i % 4 + 1}', 'option': 'RB'} for i in range(1, 5)}
    d['rooms']['R4'] = {'level': 'L1', 'anchor': [103 * FT // 4, 8 * FT], 'name': 'Pantry', 'function': 'storage',
                        'option': 'RB'}


FEW_ROOMS = pack({'ROOMS': rule({'to': 'level'}, C('roomCount', '<=', 3), title='At most three rooms on a level')})
R('document', 'primary-design', 'The rules house with a utility option set whose option RB adds a pantry: with no '
  'design in the request, the primary design is evaluated - three rooms on L1, no finding.',
  ['FS-RULES-1.2.2'], edit(utility_options), req(FEW_ROOMS),
  check=lambda r: ensure(r['findings'] == [] and r['evaluated'][0]['subjects'] == 1, 'no finding'))
R('document', 'requested-design', 'The same house and pack, the request naming the design {"RS": "RB"}: its view has '
  'the pantry, four rooms on L1, and the rule finds that.', ['FS-RULES-1.2.2', 'FS-RULES-1.1.1'], edit(utility_options),
  req(FEW_ROOMS, design={'RS': 'RB'}), found=[('ROOMS', 'L1')])
R('document', 'design-core-does-not-derive', 'The request names the design {"RS": "RC"}, and the house has no option '
  'RC: Core derives nothing for it (Core 19.6.2), so FS-RULES-003 and no finding.', ['FS-RULES-1.2.2'],
  edit(utility_options), req(FEW_ROOMS, design={'RS': 'RC'}), diags=[D('FS-RULES-003')])
R('request', 'design-not-an-object', 'A request whose design is a string: it does not match the request schema, '
  'FS-RULES-001.', ['FS-RULES-1.1.1'], house(), req(FEW_ROOMS, design='RB'), diags=[D('FS-RULES-001')])

# ============================================================================= packs (2)
R('packs', 'no-licence', 'Two packs, the first without `license`: it does not match the pack schema (FS-RULES-004, '
  '`packIndex` 0) and is not evaluated; the second is.', ['FS-RULES-2.1.1', 'FS-RULES-11.1.1'], house(),
  req({k: v for k, v in pack({'SMOKE': SMOKE}, name='first').items() if k != 'license'}, pack({'SMOKE': SMOKE}, name='second')),
  diags=[D('FS-RULES-004', packIndex=0)], check=lambda r: ensure([e['pack'] for e in r['evaluated']] == ['second'], 'second only'))
R('packs', 'another-licence', 'A pack licensed `"MIT"`: every pack is CC BY 4.0 (2.3), so FS-RULES-004.',
  ['FS-RULES-2.1.1'], house(), req(pack({'SMOKE': SMOKE}, license='MIT')), diags=[D('FS-RULES-004', packIndex=0)])
R('packs', 'a-threshold-with-a-fraction', 'A rule whose threshold is written `1.5`: thresholds are JSON integers, so the '
  'pack does not match its schema (FS-RULES-004).', ['FS-RULES-2.1.1'], house(),
  None, raw_request=(json.dumps(req(pack({'SMOKE': SMOKE})), indent=2).replace('"value": 1', '"value": 1.5') + '\n').encode(),
  diags=[D('FS-RULES-004', packIndex=0)])
R('packs', 'a-rule-member-the-schema-does-not-list', 'A rule with a member `note`, which a rule record does not have: '
  'FS-RULES-004.', ['FS-RULES-2.1.1'], house(), req(pack({'SMOKE': {**SMOKE, 'note': 'x'}})), diags=[D('FS-RULES-004', packIndex=0)])
R('packs', 'a-section-that-starts-with-a-space', 'A citation whose section is `" 3.1"`: FS-RULES-004.', ['FS-RULES-2.1.1'],
  house(), req(pack({'S': rule(SLEEPING, C('roomNetArea', '>=', 1), section=' 3.1')})), diags=[D('FS-RULES-004', packIndex=0)])
R('packs', 'a-pack-for-another-draft', 'A pack that declares `"floorspecRules": "0.2"`: FS-RULES-004.', ['FS-RULES-2.1.1'],
  house(), req({**pack({'SMOKE': SMOKE}), 'floorspecRules': '0.2'}), diags=[D('FS-RULES-004', packIndex=0)])
R('packs', 'a-severity-of-error', 'A rule whose severity is "error": a finding is never an error (3.11), so FS-RULES-004.',
  ['FS-RULES-2.1.1', 'FS-RULES-1.5.2'], house(), req(pack({'SMOKE': {**SMOKE, 'severity': 'error'}})), diags=[D('FS-RULES-004', packIndex=0)])
R('packs', 'two-packs-of-one-name', 'Three packs: two schema-valid packs named `same` (FS-RULES-005 for each, neither '
  'evaluated) and a third, also named `same`, that does not match the schema (FS-RULES-004; it does not count as a '
  'name). Other packs are unaffected.', ['FS-RULES-2.2.1', 'FS-RULES-11.1.1'], house(),
  req(pack({'SMOKE': SMOKE}, name='same'), pack({'S2': SMOKE}, name='same', version='0.2.0'), pack({}, name='same', license='MIT'),
      pack({'SMOKE': SMOKE}, name='other')),
  diags=[D('FS-RULES-004', packIndex=2), D('FS-RULES-005', packIndex=0), D('FS-RULES-005', packIndex=1)],
  check=lambda r: ensure([e['pack'] for e in r['evaluated']] == ['other'], 'other only'))
for _slug, _where, _p in [
        ('assurance-in-a-paraphrase', 'a paraphrase that says a design "complies"',
         pack({'SMOKE': {**SMOKE, 'paraphrase': 'A design complies when every bedroom has an alarm.'}})),
        ('assurance-in-an-exception', 'an exception note that says "meets the code"',
         pack({'SMOKE': {**SMOKE, 'exceptions': [{'when': C('roomNetArea', '<', 1), 'note': 'A room this small meets the code.'}]}})),
        ('assurance-in-a-coverage-note', 'a coverage note that says "up to code"',
         pack({'SMOKE': SMOKE}, coverage=[{'code': 'TEST-CODE', 'edition': '2024', 'section': '§5', 'status': 'addressed',
                                            'note': 'Designs that pass are up to code.'}])),
        ('assurance-in-a-title', 'a pack title "Code-approved rules"', pack({'SMOKE': SMOKE}, title='Code-approved rules')),
        ('assurance-in-a-provenance-note', 'a provenance note that says "Non-compliant designs are flagged"',
         pack({'SMOKE': {**SMOKE, 'provenance': {**PROV, 'note': 'Non-compliant designs are flagged.'}}}))]:
    R('packs', _slug, f'A pack with {_where}: its text matches the assurance pattern, so FS-RULES-006 and it is not evaluated.',
      ['FS-RULES-2.5.1', 'FS-RULES-11.1.1'], house(), req(_p), diags=[D('FS-RULES-006', packIndex=0)])
R('packs', 'words-that-are-not-assurance', 'A pack whose text uses "complimentary", "the code passes through" and '
  '"compliances" (a word the pattern does not list) has no match of the assurance pattern, and is evaluated.',
  ['FS-RULES-2.5.1'], house(),
  req(pack({'SMOKE': {**SMOKE, 'paraphrase': 'A complimentary alarm; the code passes through review; compliances aside.'}})),
  check=lambda r: ensure(len(r['evaluated']) == 1, 'evaluated'))
R('packs', 'a-shared-name-and-assurance', 'A pack that shares its name with another and says "compliant": it is reported '
  'with both FS-RULES-005 and FS-RULES-006.', ['FS-RULES-2.2.1', 'FS-RULES-2.5.1'], house(),
  req(pack({'SMOKE': SMOKE}, title='Compliant rules'), pack({'SMOKE': SMOKE})),
  diags=[D('FS-RULES-005', packIndex=0), D('FS-RULES-005', packIndex=1), D('FS-RULES-006', packIndex=0)])


# ============================================================================= typing (3.9, 3.10, 4.8)
GOOD = rule({'to': 'level'}, C('roomCount', '>=', 0), title='Well typed')
TYPED = pack({
    'GOOD': GOOD,
    'UNKNOWN-MEASURE': rule(SLEEPING, C('roomVolume', '>=', 1), title='A measure the library does not define'),
    'WRONG-TARGET': rule(SLEEPING, C('openingWidth', '>=', 1), title='An opening measure on a room'),
    'MISSING-ARG': rule(SLEEPING, C('roomAdjacentTo', '=', True), title='A required argument missing'),
    'EXTRA-ARG': rule(SLEEPING, C('roomNetArea', '>=', 1, per='room'), title='An argument the measure does not take'),
    'ARG-TYPE': rule(SLEEPING, C('roomAdjacentTo', '=', True, function='bedroom'), title='An argument of the wrong type'),
    'VALUE-TYPE': rule(SLEEPING, C('roomLeastWidth', '>=', '7 ft'), title='A length compared with a string'),
    'OP-FOR-TYPE': rule(SLEEPING, C('roomLeastWidth', 'has', 'x'), title='has on a length'),
    'IN-AN-AREA': rule(SLEEPING, C('roomNetArea', 'in', [1, 2]), title='in on an area'),
    'BOOLEAN-ORDER': rule(SLEEPING, C('roomIsEntry', '>', 0), title='An order on a boolean'),
    'APPLIES-EXTENSION': rule({'to': 'room', 'extension': ELEC}, C('roomNetArea', '>=', 1), title='An extension on a room'),
    'COLLECTION-ALONE': rule({'to': 'element', 'collection': 'panels'}, C('elementTopAboveFloor', '>=', 1), title='A collection without its extension'),
    'NO-SUCH-SET': rule(SLEEPING, C('envelopeDepth', '>=', 1), select={'from': 'envelopes', 'need': 'any'}, title='Envelopes of a room'),
    'SET-ARG': rule(SLEEPING, C('openingWidth', '>=', 1), select={'from': 'openings', 'args': {'to': 'inside'}, 'need': 'any'}, title='An opening set argument'),
    'MEMBER-OF-WHAT': rule({'to': 'element'}, C('elementMember', '=', 1, name='rating', type='integer'), title='A member of an unnamed extension'),
    'UNIT-ON-A-TERM': rule(PANELS, C('elementMember', '=', 'x', name='rating', type='term', unit='A'), title='A unit on a term'),
    'ZERO-LIMIT': rule(PANELS, C('clearDepthInFront', '>=', 1, limit=0), select={'from': 'envelopes', 'need': 'any'}, title='A limit of zero'),
    'PROVENANCE': rule(SLEEPING, C('roomNetArea', '>=', 1), title='Verified against another edition', provenance={**PROV, 'edition': '2021'}),
    'DEFERRED-AND-BAD': rule(SLEEPING, {'all': [C('roomNarrowestDimension', '>=', 1), C('roomVolume', '>=', 1)]}, title='Deferred and unknown'),
})
R('typing', 'rules-that-are-not-well-typed',
  'One pack, one well-typed rule and seventeen that are not, each broken in one way: a measure the library does not '
  'define, a measure on a target it does not take, a missing, an extra or a mistyped argument, a value or an operator '
  'that does not fit the type, `in` on an area, an extension or a collection where applicability does not allow one, a '
  'candidate set the subject does not have or an argument it does not take, `elementMember` on elements of an extension '
  'the rule does not name, a unit on a term, a limit of zero, provenance for another edition, and a deferred measure '
  'beside an unknown one (FS-RULES-007, not 008). Each is reported with FS-RULES-007 and listed as "invalid"; the '
  'well-typed rule is evaluated.',
  ['FS-RULES-3.9.1', 'FS-RULES-11.1.1', 'FS-RULES-9.1.1'], house(), req(TYPED),
  diags=[D('FS-RULES-007', pack='test-pack', rule=r) for r in TYPED['rules'] if r != 'GOOD'],
  check=lambda r: ensure([e['rule'] for e in r['evaluated']] == ['GOOD'] and all(e['reason'] == 'invalid' for e in r['notEvaluated']), 'invalid'))

DEFERRED_NAMES = ['countertopReceptacleReach', 'countertopWallRunBetweenReceptacles',
                  'floorElevationDifference', 'roomNarrowestDimension', 'travelDistance']
DEFERRED_PACK = pack({f'D-{n}': rule(SLEEPING, C(n, '>=', 1, anything=True), title=f'Uses {n}') for n in DEFERRED_NAMES})
R('typing', 'every-deferred-measure',
  'A rule for each of the five deferred measures of 4.8, each with an argument no measure takes: a deferred measure '
  'counts as taking any arguments, so each rule is well typed, and each is reported with FS-RULES-008 (an `info`) and '
  'listed as "deferred". None is evaluated.',
  ['FS-RULES-3.9.2', 'FS-RULES-4.8.1', 'FS-RULES-11.1.1'], house(), req(DEFERRED_PACK),
  diags=[D('FS-RULES-008', pack='test-pack', rule=f'D-{n}') for n in DEFERRED_NAMES],
  check=lambda r: ensure(r['evaluated'] == [] and len(r['notEvaluated']) == 5, 'all deferred'))

FURN_MEMBER = rule({'to': 'element', 'extension': 'EXT_furniture'}, C('elementMember', '=', 'oak', name='finish', type='term'),
                   title='A member of an extension nobody implements')
EXT_PACK = pack({
    'SMOKE': SMOKE,
    'COUNT': rule(SLEEPING, C('elementCount', '>=', 1, extension=ELEC, collection='alarms'), title='Any alarm, by core members'),
    'MEMBER': rule(PANELS, C('elementMember', '>=', 60, name='rating', type='integer', unit='A'), title='A panel rating'),
    'PROTECTED': rule({**PANELS, 'collection': 'panels'}, C('elementProtectedBy', '=', False, protection='gfci'), title='Protection'),
    'CIRCUITS': rule(SLEEPING, C('circuitCount', '>=', 1), title='A receptacle circuit'),
    'REACH': rule(SLEEPING, C('receptacleReach', '<=', 30 * FT), title='Receptacles, by core members'),
    'REACH-MATCH': rule(SLEEPING, C('receptacleReach', '<=', 30 * FT, match={'amps': 15}), title='Receptacles of 15 A'),
    'FURNITURE': FURN_MEMBER,
    'OLD-SMOKE': rule(SLEEPING, SMOKE['requirement'], edition='2021', title='A smoke alarm (2021)'),
})
R('typing', 'rules-that-read-an-extension-that-is-not-evaluated',
  'The rules house, with a furniture piece of EXT_furniture, for an evaluator with no known extensions: neither '
  'FS_electrical nor EXT_furniture is evaluated. Rules that read their members - a match on `detects`, `elementMember`, '
  '`elementProtectedBy`, `circuitCount`, a receptacle match - are reported with FS-RULES-009 and listed as "extension"; '
  'rules that read only core members (an alarm count without a match, receptacle reach without one) are evaluated; '
  'and a rule that reads FS_electrical but is not in force is listed as "edition", with no FS-RULES-009.',
  ['FS-RULES-3.10.1', 'FS-RULES-11.1.1'],
  edit(lambda d: furniture(d, {'P1': {'fallback': {'level': 'L1', 'box': box(-300, -300, 0, 300, 300, 900)},
                                      'host': {'mode': 'free', 'level': 'L1', 'position': [18 * FT, 6 * FT]}, 'finish': 'oak'}})),
  req(EXT_PACK), registry=None,
  diags=[D('FS-RULES-009', pack='test-pack', rule=r) for r in ('CIRCUITS', 'FURNITURE', 'MEMBER', 'PROTECTED', 'REACH-MATCH', 'SMOKE')],
  check=lambda r: (ensure([e['rule'] for e in r['evaluated']] == ['COUNT', 'REACH'], 'core-only rules'),
                   ensure({e['rule']: e['reason'] for e in r['notEvaluated']}['OLD-SMOKE'] == 'edition', 'edition first')))
R('typing', 'the-same-rules-with-the-extensions-known',
  'The same document and pack for an evaluator that knows FS_electrical and FS_mechanical: every FS_electrical rule is '
  'evaluated; only the EXT_furniture rule, which no evaluator implements, is still FS-RULES-009.',
  ['FS-RULES-3.10.1'],
  edit(lambda d: furniture(d, {'P1': {'fallback': {'level': 'L1', 'box': box(-300, -300, 0, 300, 300, 900)},
                                      'host': {'mode': 'free', 'level': 'L1', 'position': [18 * FT, 6 * FT]}, 'finish': 'oak'}})),
  req(EXT_PACK), diags=[D('FS-RULES-009', pack='test-pack', rule='FURNITURE')])
R('typing', 'extension-rules-on-a-core-0.3-document',
  'The same document and pack, declaring Core "0.3", for an evaluator that knows FS_electrical and FS_mechanical: the '
  'official extensions at 0.1.0 are evaluated for Core 0.3 documents too (each one\'s 1.2), so every FS_electrical rule '
  'is evaluated, exactly as for the "0.2" document; only the EXT_furniture rule is FS-RULES-009.',
  ['FS-RULES-3.10.1', 'FS-RULES-1.2.1'],
  edit(lambda d: (furniture(d, {'P1': {'fallback': {'level': 'L1', 'box': box(-300, -300, 0, 300, 300, 900)},
                                       'host': {'mode': 'free', 'level': 'L1', 'position': [18 * FT, 6 * FT]},
                                       'finish': 'oak'}}), d.update(floorspec='0.3'))),
  req(EXT_PACK), diags=[D('FS-RULES-009', pack='test-pack', rule='FURNITURE')],
  check=lambda r: ensure('CIRCUITS' in [e['rule'] for e in r['evaluated']], [e['rule'] for e in r['evaluated']]))


# ============================================================================= subjects and selection (3.4 - 3.6)
SUBJECTS = pack({
    'ROOMS': rule({'to': 'room'}, C('roomNetArea', '>', 0), title='Every room'),
    'SLEEPING-ROOMS': rule(SLEEPING, C('roomNetArea', '>', 0), title='Sleeping rooms'),
    'WINDOWS': rule({'to': 'opening', 'where': C('openingKind', '=', 'window')}, C('openingSillHeight', '<=', FT),
                    title='Windows with a sill of at most a foot'),
    'PANELS': rule(PANELS, C('elementTopAboveFloor', '<=', 3 * FT), title='Panels below three feet'),
    'ELECTRICAL': rule({'to': 'element', 'extension': ELEC}, C('elementBottomAboveFloor', '>=', 0), title='Every electrical element'),
    'ELEMENTS': rule({'to': 'element'}, C('elementRoomFunction', '!=', 'none'), title='Every element is in a room'),
    'LEVELS': rule({'to': 'level'}, C('roomCount', '>=', 4), title='Four rooms on a level'),
})
R('selection', 'subjects-of-each-kind',
  'Rules applying to every room (3 subjects), to sleeping rooms (1), to windows (2: O1 and O5), to the panels of '
  'FS_electrical (1), to every FS_electrical element (4: the panel, the alarm and two receptacles), to every extension '
  'element (5) and to every level (1). The windows, whose sills are 2\', the panel, whose top is 5\' 3", and the level, '
  'with 3 rooms, each give a finding.',
  ['FS-RULES-3.4.1', 'FS-RULES-3.6.1'], house(), req(SUBJECTS),
  found=[('LEVELS', 'L1'), ('PANELS', 'X1'), ('WINDOWS', 'O1'), ('WINDOWS', 'O5')],
  check=lambda r: ensure({e['rule']: e['subjects'] for e in r['evaluated']}
                         == {'ROOMS': 3, 'SLEEPING-ROOMS': 1, 'WINDOWS': 2, 'PANELS': 1, 'ELECTRICAL': 4, 'ELEMENTS': 5, 'LEVELS': 1},
                         'subject counts'))

SELECTION = pack({
    'OUTSIDE-DOOR': rule(SLEEPING, C('openingKind', '=', 'door'), select={'from': 'openings', 'args': {'to': 'outside'}, 'need': 'any'},
                         title='A door to the outside'),
    'ANY-DOOR': rule(SLEEPING, C('openingKind', '=', 'door'), select={'from': 'openings', 'need': 'any'}, title='Any door'),
    'ALL-WINDOWS': rule(SLEEPING, C('openingKind', '=', 'window'), select={'from': 'openings', 'need': 'all'}, title='Only windows'),
    'NONE-ANY': rule(SLEEPING, C('openingWidth', '>=', 1), select={'from': 'openings', 'where': C('openingKind', '=', 'empty'), 'need': 'any'},
                     title='An empty opening'),
    'NONE-ALL': rule(SLEEPING, C('openingWidth', '>=', 1), select={'from': 'openings', 'where': C('openingKind', '=', 'empty'), 'need': 'all'},
                     title='Every empty opening'),
    'RECEPTACLES-LOW': rule(SLEEPING, C('elementBottomAboveFloor', '<=', 200 * MM),
                            select={'from': 'elements', 'args': {'extension': ELEC, 'collection': 'receptacles'}, 'need': 'all'},
                            title='Receptacles low'),
    'LEVEL-SLEEPING': rule({'to': 'level'}, C('roomNetArea', '>=', 200 * SQFT), select={'from': 'rooms', 'args': {'function': 'sleeping'}, 'need': 'any'},
                           title='A big bedroom'),
    'LEVEL-CO': rule({'to': 'level'}, C('elementMember', 'has', 'carbonMonoxide', name='detects', type='terms'),
                     select={'from': 'elements', 'args': {'extension': ELEC, 'collection': 'alarms'}, 'need': 'any'},
                     title='A carbon monoxide alarm on every level'),
    'DOOR-SWINGS': rule({'to': 'opening', 'where': C('openingKind', '=', 'door')}, C('envelopeDepth', '>=', 1),
                        select={'from': 'envelopes', 'args': {'purpose': 'swing'}, 'need': 'any'}, title='A door swing'),
})


def check_selection(r):
    f = {(x['rule'], x['subject']['id']): x for x in r['findings']}
    ensure(f[('OUTSIDE-DOOR', 'R1')]['candidates'] == [opening('O1')], 'the window is its only opening to the outside')
    ensure(f[('ALL-WINDOWS', 'R1')]['candidates'] == [opening('O1'), opening('O2')], 'both openings')
    ensure([m['holds'] for m in f[('ALL-WINDOWS', 'R1')]['measures']] == [True, False], 'the door is not a window')
    ensure(f[('NONE-ANY', 'R1')]['candidates'] == [] and f[('NONE-ANY', 'R1')]['measures'] == [], 'no candidate')
    ensure(f[('RECEPTACLES-LOW', 'R1')]['candidates'] == [element('X4'), element('X5')], 'two receptacles')
    ensure(f[('LEVEL-SLEEPING', 'L1')]['location']['shapes'][0]['kind'] == 'polygon', 'a level draws its candidates')
    ensure([d['subject']['id'] for d in r['findings'] if d['rule'] == 'DOOR-SWINGS'] == ['O2', 'O3', 'O4'], 'three doors')


R('selection', 'candidates-any-all-and-none',
  'Selection on the rules house\'s bedroom, its level and its doors: the bedroom\'s only opening to the outside is its '
  'window, so "a door to the outside" fails while "any door" passes (O2 is to the living room); "only windows" over all its '
  'openings fails on O2; with no empty opening, a rule that needs any fails and one that needs all passes; both '
  'receptacles stand 240 mm above the floor, so "all at most 200 mm" fails; the level\'s one sleeping room is under 200 '
  'sq ft; its one alarm detects only smoke; and each of the three doors has no swing envelope.',
  ['FS-RULES-3.5.1', 'FS-RULES-3.6.1'], house(), req(SELECTION),
  found=[('ALL-WINDOWS', 'R1'), ('DOOR-SWINGS', 'O2'), ('DOOR-SWINGS', 'O3'), ('DOOR-SWINGS', 'O4'), ('LEVEL-CO', 'L1'),
         ('LEVEL-SLEEPING', 'L1'), ('NONE-ANY', 'R1'), ('OUTSIDE-DOOR', 'R1'), ('RECEPTACLES-LOW', 'R1')],
  check=check_selection)


# ============================================================================= exceptions (3.7)
EXCEPT = pack({'SLEEP-EVERYWHERE': rule({'to': 'room'}, C('roomFunction', '=', 'sleeping'),
                                        exceptions=[{'when': C('roomFunction', '=', 'mechanical'), 'note': 'Not in a mechanical room.'},
                                                    {'when': {'not': C('roomIsReachable', '=', True)}, 'note': 'Not in a room nobody reaches.'}],
                                        title='Every room is a bedroom')})
R('exceptions', 'an-exempt-subject',
  'A rule that every room be a sleeping room, except a mechanical room or one nobody can reach: R1 passes, R3 is exempt '
  '(counted in `exempt`, with no finding), and R2 gets the only finding. The subjects are still 3.',
  ['FS-RULES-3.7.1', 'FS-RULES-9.1.1'], house(), req(EXCEPT), found=[('SLEEP-EVERYWHERE', 'R2')],
  check=lambda r: ensure((r['evaluated'][0]['subjects'], r['evaluated'][0]['exempt'], r['evaluated'][0]['findings']) == (3, 1, 1), 'counts'))
R('exceptions', 'an-exception-on-a-subject-that-passes',
  'The same rule with the doors O2 and O3 removed, so that no room is reachable: every room is now exempt by the '
  'second exception - R3 by both - including R1, which would pass the requirement: an exempt subject is not tried on it.',
  ['FS-RULES-3.7.1'], edit(lambda d: [d['openings'].pop(o) for o in ('O2', 'O3')]), req(EXCEPT),
  check=lambda r: ensure((r['evaluated'][0]['exempt'], r['evaluated'][0]['findings']) == (3, 0), 'counts'))


# ============================================================================= tests (3.8)
R1_AREA = INSIDE * INSIDE
TESTS_PACK = pack({
    'EVERY-OPERATOR': rule(SLEEPING, {'not': {'all': [
        C('roomNetArea', '>', R1_AREA - 1), C('roomNetArea', '>=', R1_AREA), C('roomNetArea', '<=', R1_AREA),
        C('roomNetArea', '=', R1_AREA), C('roomNetArea', '!=', 0), C('roomNetArea', '<', R1_AREA + 1),
        C('roomLeastWidth', 'in', [1, INSIDE]), C('roomFunction', 'in', ['bath', 'sleeping']), C('roomFunction', '!=', 'living'),
        C('roomIsReachable', '=', True), C('roomIsEntry', '!=', True), C('elementCount', '=', 3, extension=ELEC)]}},
        title='Every operator holds'),
    'ANY-NONE': rule(SLEEPING, {'any': [C('roomNetArea', '<', R1_AREA), C('roomIsEntry', '=', True)]}, title='Neither holds'),
    'ANY-ONE': rule(SLEEPING, {'any': [C('roomNetArea', '<', R1_AREA), C('roomIsReachable', '=', True)]}, title='One holds'),
    'NO-VALUE': rule({'to': 'element', 'extension': ELEC, 'collection': 'receptacles'},
                     {'all': [C('elementMember', '=', 0, name='watts', type='integer'), C('elementMember', '<', 1, name='watts', type='integer'),
                              C('elementMember', '!=', 0, name='watts', type='integer'),
                              C('elementMember', 'has', 'gfci', name='features', type='terms')]},
                     title='A receptacle load'),
})


def check_tests(r):
    f = {(x['rule'], x['subject']['id']): x for x in r['findings']}
    ensure(all(m['holds'] for m in f[('EVERY-OPERATOR', 'R1')]['measures']) and len(f[('EVERY-OPERATOR', 'R1')]['measures']) == 12,
           'every leaf holds, so its negation fails')
    ensure([m['holds'] for m in f[('NO-VALUE', 'X4')]['measures']] == [False, False, True, False], 'no value: only != holds')
    ensure(f[('NO-VALUE', 'X4')]['measures'][0]['value'] is None and f[('NO-VALUE', 'X4')]['measures'][0]['display'] == 'not stated', 'null')
    ensure(f[('NO-VALUE', 'X4')]['measures'][3]['display'] == 'none', 'no features')


R('tests', 'every-operator-all-any-not-and-no-value',
  'Tests on the bedroom and its receptacles: twelve conditions, one of each operator and type - an area compared '
  'exactly with integers just either side of it, `in` on a length and a term, booleans and a count - all hold, so `not` '
  'of their `all` fails, and the finding lists all twelve; `any` of two false conditions fails and of one true one '
  'passes; and a receptacle\'s `watts`, which it does not state and has no default, has no value: `=`, `<` and `has` on '
  'it fail and `!=` holds, and `features` (default `[]`) displays as `none`.',
  ['FS-RULES-3.8.1', 'FS-RULES-9.3.1', 'FS-RULES-9.6.1'], house(), req(TESTS_PACK),
  found=[('ANY-NONE', 'R1'), ('EVERY-OPERATOR', 'R1'), ('NO-VALUE', 'X4'), ('NO-VALUE', 'X5')], check=check_tests)


def oblique():
    """A four-sided room with oblique walls, whose rounded corners give a net area with a half."""
    d = house()
    d.pop('openings')
    d['extensions'] = {}
    d['extensionsUsed'] = {}
    d['junctions'] = {'J1': J(0, 0), 'J2': J(4000 * MM, 700 * MM), 'J3': J(3300 * MM, 5100 * MM), 'J4': J(-400 * MM, 4100 * MM)}
    d['walls'] = {'W1': W('J1', 'J4'), 'W2': W('J4', 'J3'), 'W3': W('J3', 'J2'), 'W4': W('J2', 'J1')}
    d['rooms'] = {'R1': {'level': 'L1', 'anchor': [1800 * MM, 2400 * MM], 'function': 'sleeping'}}
    return d


def _oblique_area2():
    r, _, _ = check_document(json.dumps(oblique()).encode(), None)
    a = r['derived']['rooms']['R1']['area']
    assert a.endswith('.5'), a
    return int(a[:-2])


_HALF = _oblique_area2()          # the room's net area is _HALF + 1/2
R('tests', 'an-area-with-a-half',
  'A room with oblique walls whose net area, from its rounded corners, is an integer and a half (computed by the '
  'oracle). Areas compare exactly: it is greater than the integer below it and less than the integer above, and equal to '
  'neither, so of four conditions `>` and `<` hold and `>=` the integer above and `=` the integer below fail.',
  ['FS-RULES-3.8.1', 'FS-RULES-5.2.1'], oblique(),
  req(pack({'HALF': rule(SLEEPING, {'all': [C('roomNetArea', '>', _HALF), C('roomNetArea', '<', _HALF + 1),
                                            C('roomNetArea', '>=', _HALF + 1), C('roomNetArea', '=', _HALF)]}, title='Half')})),
  registry=None, found=[('HALF', 'R1')],
  check=lambda r: ensure([m['holds'] for m in r['findings'][0]['measures']] == [True, True, False, False]
                         and r['findings'][0]['measures'][0]['value'] == f'{_HALF}.5', 'exact halves'))


# ============================================================================= findings and the report (9)
SEVERITIES = pack({
    'A-MAY-NOT-MEET': rule(SLEEPING, C('roomNetArea', '>=', 200 * SQFT), title='A big bedroom', section='§7.1'),
    'B-CHECK': rule(SLEEPING, C('roomLeastWidth', '>=', 13 * FT), severity='check', title='A wide bedroom', section='§7.2'),
    'C-NOTE': rule(SLEEPING, C('roomIsEntry', '=', True), severity='note', title='A bedroom with its own way in', section='§7.3(a)'),
})
R('findings', 'one-message-for-each-severity',
  'Three rules the bedroom fails, one of each severity: every message names the subject, the code, the edition, the '
  'section and the rule\'s title, says "may not meet", and for `check` asks for a check by a professional or the '
  'authority having jurisdiction, and for `note` says it is for information.',
  ['FS-RULES-9.5.1', 'FS-RULES-9.5.2', 'FS-RULES-1.5.2', 'FS-RULES-9.2.1', 'FS-RULES-9.6.1'], house(), req(SEVERITIES),
  found=[('A-MAY-NOT-MEET', 'R1'), ('B-CHECK', 'R1'), ('C-NOTE', 'R1')],
  check=lambda r: ensure([f['message'] for f in r['findings']] == [
      'R1 may not meet TEST-CODE 2024 §7.1 (A big bedroom).',
      'R1 may not meet TEST-CODE 2024 §7.2 (A wide bedroom). Check it with a professional or the authority having jurisdiction.',
      'R1 may not meet TEST-CODE 2024 §7.3(a) (A bedroom with its own way in). This is for information.']
      and [f['measures'][0]['display'] for f in r['findings']] == ['136.23 sq ft', "11' 8 1/16\"", 'no']
      and [f['measures'][0]['thresholdDisplay'] for f in r['findings']] == ['200.00 sq ft', "13' 0\"", 'yes'], 'messages and displays'))

ORDER_A = pack({'Z': rule({'to': 'room'}, C('roomFunction', '=', 'garage'), title='Z rule'),
                'A': rule({'to': 'opening'}, C('openingWidth', '>', 4 * FT), title='A rule'),
                'DEFERRED': rule(SLEEPING, C('roomNarrowestDimension', '>=', 1), title='Deferred')}, name='b-pack')
ORDER_B = pack({'M': rule({'to': 'room', 'where': C('roomFunction', '!=', 'sleeping')}, C('roomNetArea', '<', 1), title='M rule'),
                'BAD': rule(SLEEPING, C('roomVolume', '>', 1), title='Bad')}, name='a-pack',
               coverage=[{'code': 'TEST-CODE', 'edition': '2024', 'section': '§9', 'status': 'notAddressed'},
                         {'code': 'TEST-CODE', 'edition': '2024', 'section': '§1', 'status': 'partial', 'note': 'b'},
                         {'code': 'TEST-CODE', 'edition': '2024', 'section': '§1', 'status': 'partial'},
                         {'code': 'TEST-CODE', 'edition': '2024', 'section': '§1', 'status': 'partial', 'note': 'a'}])


def check_order(r):
    ensure([(f['pack'], f['rule'], f['subject']['id']) for f in r['findings']]
           == [('a-pack', 'M', 'R2'), ('a-pack', 'M', 'R3'), ('b-pack', 'A', 'O1'), ('b-pack', 'A', 'O2'), ('b-pack', 'A', 'O3'),
               ('b-pack', 'A', 'O4'), ('b-pack', 'A', 'O5'), ('b-pack', 'Z', 'R1'), ('b-pack', 'Z', 'R2'), ('b-pack', 'Z', 'R3')], 'findings')
    ensure([d['code'] for d in r['diagnostics']] == ['FS-RULES-004', 'FS-RULES-007', 'FS-RULES-008'], 'diagnostics')
    ensure([(c['section'], c.get('note')) for c in r['coverage']] == [('§1', None), ('§1', 'a'), ('§1', 'b'), ('§9', None)], 'coverage')
    ensure([(e['pack'], e['rule']) for e in r['notEvaluated']] == [('a-pack', 'BAD'), ('b-pack', 'DEFERRED')], 'not evaluated')


R('findings', 'everything-in-order',
  'Two packs given as b-pack then a-pack, rules declared Z then A, and a malformed third pack: diagnostics are sorted by '
  'code, `evaluated` and `notEvaluated` by pack and rule, coverage by pack, code, edition, section, status and note (an '
  'absent note first), and findings by pack, rule and subject.',
  ['FS-RULES-9.7.1', 'FS-RULES-11.1.1'], house(), req(ORDER_A, ORDER_B, pack({}, license='none')),
  diags=[D('FS-RULES-004', packIndex=2), D('FS-RULES-007', pack='a-pack', rule='BAD'), D('FS-RULES-008', pack='b-pack', rule='DEFERRED')],
  found=[('a-pack', 'M', 'R2'), ('a-pack', 'M', 'R3'), ('b-pack', 'A', 'O1'), ('b-pack', 'A', 'O2'), ('b-pack', 'A', 'O3'),
         ('b-pack', 'A', 'O4'), ('b-pack', 'A', 'O5'), ('b-pack', 'Z', 'R1'), ('b-pack', 'Z', 'R2'), ('b-pack', 'Z', 'R3')],
  check=check_order)

COVERAGE = pack({'SMOKE': SMOKE}, name='main', coverage=[
    {'code': 'TEST-CODE', 'edition': '2021', 'section': '§5', 'status': 'addressed'},
    {'code': 'TEST-CODE', 'edition': '2024', 'section': '§5', 'status': 'addressed'},
    {'code': 'TEST-ELEC', 'edition': '2026', 'section': '§2', 'status': 'notAddressed', 'note': 'No rules for section 2 yet.'},
    {'code': 'OTHER', 'edition': '2024', 'section': '§1', 'status': 'partial'}])
R('findings', 'coverage-of-the-editions-in-force',
  'A selected pack\'s coverage entries for TEST-CODE 2021 and 2024, TEST-ELEC 2026 and OTHER 2024, under a profile that '
  'adopts TEST-CODE 2024 and TEST-ELEC 2026 and selects only that pack: the report carries the 2024 and 2026 entries, each '
  'with its pack\'s name; a second, unselected pack\'s entries are not carried, and its rule is listed as "profile".',
  ['FS-RULES-9.1.2', 'FS-RULES-9.1.1', 'FS-RULES-10.4.1'], house(),
  req(COVERAGE, pack({'SMOKE': SMOKE}, name='other', coverage=[{'code': 'TEST-CODE', 'edition': '2024', 'section': '§6', 'status': 'partial'}]),
      profile={**PROFILE, 'packs': [{'name': 'main', 'version': '0.1.0'}]}),
  check=lambda r: (ensure([(c['pack'], c['code'], c['edition']) for c in r['coverage']]
                          == [('main', 'TEST-CODE', '2024'), ('main', 'TEST-ELEC', '2026')], 'coverage'),
                   ensure(r['notEvaluated'] == [{'pack': 'other', 'version': '0.1.0', 'rule': 'SMOKE', 'reason': 'profile'}], 'profile')))

REASONS = pack({
    'EVALUATED': SMOKE, 'INVALID': rule(SLEEPING, C('roomVolume', '>', 1), title='Invalid'),
    'DEFERRED': rule(SLEEPING, C('travelDistance', '<', 1), title='Deferred'),
    'EDITION': rule(SLEEPING, C('roomNetArea', '>', 1), edition='1999', title='Another edition'),
    'WITHDRAWN': rule(SLEEPING, C('roomNetArea', '>', 1), title='Withdrawn'),
    'EXTENSION': FURN_MEMBER}, name='main')
R('findings', 'every-reason-not-to-evaluate',
  'One rule for each way a rule of a usable pack is not evaluated - an unselected pack ("profile"), FS-RULES-007 '
  '("invalid"), FS-RULES-008 ("deferred"), an edition not in force ("edition"), an amendment ("withdrawn") and '
  'FS-RULES-009 ("extension") - beside one that is evaluated: every rule is in exactly one of the two lists.',
  ['FS-RULES-9.1.1', 'FS-RULES-10.5.1'],
  edit(lambda d: furniture(d, {'P1': {'fallback': {'level': 'L1', 'box': box(-300, -300, 0, 300, 300, 900)}}})),
  req(REASONS, pack({'SMOKE': SMOKE}, name='unselected'),
      profile={**PROFILE, 'packs': [{'name': 'main', 'version': '^0.1.0'}],
               'amendments': [{'citation': {'authority': 'Town of Example', 'reference': 'Ord. 1 §1'},
                               'withdraws': [{'pack': 'main', 'rule': 'WITHDRAWN'}]}]}),
  diags=[D('FS-RULES-007', pack='main', rule='INVALID'), D('FS-RULES-008', pack='main', rule='DEFERRED'),
         D('FS-RULES-009', pack='main', rule='EXTENSION')],
  check=lambda r: ensure({e['rule']: e['reason'] for e in r['notEvaluated'] if e['pack'] == 'main'}
                         == {'INVALID': 'invalid', 'DEFERRED': 'deferred', 'EDITION': 'edition', 'WITHDRAWN': 'withdrawn',
                             'EXTENSION': 'extension'} and [e['rule'] for e in r['evaluated']] == ['EVALUATED'], 'reasons'))


# ============================================================================= profiles (10)
for _slug, _desc, _profile in [
        ('no-adoptions', 'a profile without `adopts`', {k: v for k, v in PROFILE.items() if k != 'adopts'}),
        ('an-unknown-member', 'a profile with a member `country`', {**PROFILE, 'country': 'US'}),
        ('one-code-twice', 'a profile that adopts TEST-CODE 2021 and 2024, neither with an effective date',
         {**PROFILE, 'adopts': [{'code': 'TEST-CODE', 'edition': '2021'}, {'code': 'TEST-CODE', 'edition': '2024'}]}),
        ('one-code-twice-on-one-date', 'a profile that adopts TEST-CODE twice, both effective 2025-01-01',
         {**PROFILE, 'adopts': [{'code': 'TEST-CODE', 'edition': '2021', 'effective': '2025-01-01'},
                                {'code': 'TEST-CODE', 'edition': '2024', 'effective': '2025-01-01'}]}),
        ('one-pack-twice', 'a profile that selects the pack `test-pack` twice',
         {**PROFILE, 'packs': [{'name': 'test-pack', 'version': '^0.1.0'}, {'name': 'test-pack', 'version': '0.1.0'}]}),
        ('assurance-in-its-name', 'a profile named "Code compliance profile"', {**PROFILE, 'name': 'Code compliance profile'}),
        ('assurance-in-an-amendment', 'an amendment whose note says a design "complies"',
         {**PROFILE, 'amendments': [{'citation': {'authority': 'Town', 'reference': 'Ord. 2'}, 'withdraws': [{'pack': 'test-pack', 'rule': 'SMOKE'}],
                                     'note': 'A design complies without it.'}]}),
        ('a-date-that-is-not-a-date', 'a profile `asOf` "2026-13-01"', {**PROFILE, 'asOf': '2026-13-01'})]:
    R('profiles', _slug, f'The request\'s profile is {_desc}: FS-RULES-002, the report has its units but no profile '
      'name, and nothing is evaluated.', ['FS-RULES-10.1.1', 'FS-RULES-11.1.1'], house(), req(SIMPLE, profile=_profile),
      diags=[D('FS-RULES-002')], check=lambda r: ensure('profile' not in r and r['units'] == 'imperial', 'no profile'))
R('profiles', 'a-bad-profile-and-an-invalid-document', 'A malformed profile for an invalid document: only FS-RULES-002.',
  ['FS-RULES-1.3.1'], INVALID_DOC, req(SIMPLE, profile={'name': 'x'}), diags=[D('FS-RULES-002')])

TWO_EDITIONS = pack({'ESCAPE': ESCAPE, 'ESCAPE-2021': ESCAPE_2021})
TRANSITION = {**PROFILE, 'adopts': [{'code': 'TEST-CODE', 'edition': '2021', 'effective': '2022-01-01'},
                                    {'code': 'TEST-CODE', 'edition': '2024', 'effective': '2025-07-01'}]}
for _slug, _as_of, _in in [('before-the-new-edition', '2025-06-30', 'ESCAPE-2021'), ('on-the-day-it-takes-effect', '2025-07-01', 'ESCAPE'),
                           ('with-no-date-the-latest', None, 'ESCAPE'), ('before-either', '2021-12-31', None)]:
    _p = dict(TRANSITION) if _as_of is None else {**TRANSITION, 'asOf': _as_of}
    R('profiles', f'editions-in-force-{_slug}',
      f'A jurisdiction that adopted TEST-CODE 2021 from 2022-01-01 and 2024 from 2025-07-01, evaluated '
      f'{"with no asOf" if _as_of is None else "asOf " + _as_of}: '
      + (f'the edition in force is {"2021" if _in == "ESCAPE-2021" else "2024"}, so only {_in} is evaluated.' if _in
         else 'no adoption applies yet, so neither escape rule is in force.'),
      ['FS-RULES-10.2.1', 'FS-RULES-10.3.1'], house(), req(TWO_EDITIONS, profile=_p),
      check=(lambda want: lambda r: ensure([e['rule'] for e in r['evaluated']] == ([want] if want else []), 'in force'))(_in))
R('profiles', 'an-adoption-without-a-date-and-one-with',
  'TEST-CODE 2024 adopted with no effective date and 2021 with one: an adoption without a date counts as earlier than '
  'every date, so 2021 is in force.', ['FS-RULES-10.2.1'], house(),
  req(TWO_EDITIONS, profile={**PROFILE, 'adopts': [{'code': 'TEST-CODE', 'edition': '2024'},
                                                    {'code': 'TEST-CODE', 'edition': '2021', 'effective': '2020-01-01'}]}),
  check=lambda r: ensure([e['rule'] for e in r['evaluated']] == ['ESCAPE-2021'], '2021'))

MODEL = pack({f'{c}-{e}': rule({'to': 'level'}, C('roomCount', '>=', 0), code=c, edition=e, section=f'TEST-{i}',
                               title=f'Synthetic rule {i}',
                               paraphrase='A synthetic rule for the conformance suite, citing a code only to test which editions the '
                                          'default profile adopts; it states no requirement of that code.')
              for i, (c, e) in enumerate([('IRC', '2021'), ('IRC', '2024'), ('NEC', '2023'), ('NEC', '2026'), ('IPC', '2024'),
                                          ('IMC', '2024'), ('IFGC', '2024'), ('TEST-CODE', '2024')], start=1)}, name='model-editions')
R('profiles', 'the-default-profile',
  'A request with no profile is evaluated under "Model Codes (latest)": of synthetic rules citing editions of the model '
  'codes (with sections TEST-n, and no requirement of those codes), IRC 2024, NEC 2026, IPC 2024, IMC 2024 and IFGC 2024 '
  'are in force and evaluated; IRC 2021, NEC 2023 and TEST-CODE 2024 are not. The report names the profile.',
  ['FS-RULES-10.6.1', 'FS-RULES-10.3.1'], house(), req(MODEL, profile=None),
  check=lambda r: (ensure(r['profile'] == 'Model Codes (latest)', 'name'),
                   ensure([e['rule'] for e in r['evaluated']] == ['IFGC-2024', 'IMC-2024', 'IPC-2024', 'IRC-2024', 'NEC-2026'], 'adopted')))
R('profiles', 'packs-a-profile-selects',
  'A profile that selects `main` at `^0.1.0`, `old` at `>=2.0.0` and `missing` at any 1.x: `main` 0.1.3 is evaluated; '
  '`old` is given at 1.0.0, outside its range, and `missing` is not given, so each is FS-RULES-010; the rules of `old` '
  'and of `extra`, which the profile does not name, are listed as "profile".',
  ['FS-RULES-10.4.1', 'FS-RULES-11.1.1'], house(),
  req(pack({'SMOKE': SMOKE}, name='main', version='0.1.3'), pack({'SMOKE': SMOKE}, name='old', version='1.0.0'),
      pack({'SMOKE': SMOKE}, name='extra'),
      profile={**PROFILE, 'packs': [{'name': 'main', 'version': '^0.1.0'}, {'name': 'old', 'version': '>=2.0.0'},
                                    {'name': 'missing', 'version': '^1.0.0'}]}),
  diags=[D('FS-RULES-010', pack='missing'), D('FS-RULES-010', pack='old')],
  check=lambda r: ensure([e['pack'] for e in r['evaluated']] == ['main']
                         and [(e['pack'], e['reason']) for e in r['notEvaluated']] == [('extra', 'profile'), ('old', 'profile')], 'selection'))
R('profiles', 'amendments-that-withdraw-rules',
  'Three amendments: one with no date withdraws SMOKE ("withdrawn"); one effective 2027-01-01, after the profile\'s asOf '
  '2026-10-04, would withdraw ESCAPE but does not apply yet, so ESCAPE is evaluated; and one withdraws a rule the pack '
  'does not have and a rule of a pack that is not given - FS-RULES-011 for each. An amendment that does not apply is '
  'not checked.',
  ['FS-RULES-10.5.1', 'FS-RULES-11.1.1'], house(),
  req(EXAMPLE_PACK, profile={**PROFILE, 'asOf': '2026-10-04', 'jurisdiction': 'Town of Example', 'amendments': [
      {'citation': {'authority': 'Town of Example', 'reference': 'Ord. 2025-14 §3', 'link': 'https://example.com/ord/2025-14'},
       'withdraws': [{'pack': 'test-pack', 'rule': 'SMOKE'}], 'note': 'The town asks for its own alarm rule instead.'},
      {'citation': {'authority': 'Town of Example', 'reference': 'Ord. 2026-2'}, 'effective': '2027-01-01',
       'withdraws': [{'pack': 'test-pack', 'rule': 'ESCAPE'}, {'pack': 'gone-pack', 'rule': 'NEVER'}]},
      {'citation': {'authority': 'State', 'reference': 'Code §9'}, 'effective': '2026-01-01',
       'withdraws': [{'pack': 'test-pack', 'rule': 'NOPE'}, {'pack': 'gone-pack', 'rule': 'X'}]}]}),
  diags=[D('FS-RULES-011', pack='gone-pack', rule='X'), D('FS-RULES-011', pack='test-pack', rule='NOPE')],
  check=lambda r: ensure([e['rule'] for e in r['evaluated']] == ['ESCAPE', 'WORKSPACE']
                         and r['notEvaluated'] == [{'pack': 'test-pack', 'version': '0.1.0', 'rule': 'SMOKE', 'reason': 'withdrawn'}], 'amended'))


# ============================================================================= measures of rooms (5)
R3W = 8 * FT - 128000                  # R3's width inside its walls
MT('measures-rooms', 'the-rules-house',
   'Every room measure on the rules house: functions, net areas (R1 12\' x 12\' between centred 100 mm walls, '
   'R3 8\' x 12\'), least widths, circulation (R2 has the front door; R1 is reached through it), neighbours and element '
   'counts, by core members and with a match on FS_electrical\'s `detects`.',
   ['FS-RULES-5.1.1', 'FS-RULES-5.2.1', 'FS-RULES-5.3.1', 'FS-RULES-5.4.1', 'FS-RULES-5.5.1', 'FS-RULES-5.6.1', 'FS-RULES-4.3.1',
    'FS-RULES-4.4.1', 'FS-RULES-4.7.1'],
   house(),
   [(room('R1'), 'roomFunction', None), (room('R3'), 'roomFunction', None),
    (room('R1'), 'roomNetArea', None), (room('R3'), 'roomNetArea', None),
    (room('R1'), 'roomLeastWidth', None), (room('R3'), 'roomLeastWidth', None),
    (room('R2'), 'roomIsEntry', None), (room('R1'), 'roomIsEntry', None), (room('R1'), 'roomIsReachable', None),
    (room('R1'), 'roomThroughSleeping', None), (room('R2'), 'roomThroughSleeping', None),
    (room('R1'), 'roomAdjacentTo', {'function': 'living'}), (room('R1'), 'roomAdjacentTo', {'function': 'mechanical'}),
    (room('R2'), 'roomConnectedTo', {'function': 'mechanical'}),
    (room('R1'), 'elementCount', {'extension': ELEC}),
    (room('R1'), 'elementCount', {'extension': ELEC, 'collection': 'alarms', 'match': {'detects': 'smoke'}}),
    (room('R1'), 'elementCount', {'extension': ELEC, 'collection': 'alarms', 'match': {'detects': 'carbonMonoxide'}}),
    (room('R3'), 'elementCount', {'extension': MECH})],
   ['sleeping', 'mechanical', str(INSIDE * INSIDE), str(R3W * INSIDE), INSIDE, R3W, True, False, True, False, False,
    True, False, True, 3, 1, 0, 1])
MT('measures-rooms', 'reached-through-a-sleeping-room',
   'The rules house with R2 made a sleeping room: R1 is reachable only through it, so `roomThroughSleeping` is true for '
   'R1; R2, an entry, is not reached through another; R3 is not a sleeping room, so false.',
   ['FS-RULES-5.4.1'], edit(lambda d: d['rooms']['R2'].update(function='sleeping')),
   [(room('R1'), 'roomThroughSleeping', None), (room('R2'), 'roomThroughSleeping', None), (room('R3'), 'roomThroughSleeping', None)],
   [True, False, False])
MT('measures-rooms', 'adjacent-but-not-connected',
   'The rules house without the door O2: R1 is still adjacent to the living room, no longer connected to it, and no '
   'longer reachable.', ['FS-RULES-5.4.1', 'FS-RULES-5.5.1'], edit(lambda d: d['openings'].pop('O2')),
   [(room('R1'), 'roomAdjacentTo', {'function': 'living'}), (room('R1'), 'roomConnectedTo', {'function': 'living'}),
    (room('R1'), 'roomIsReachable', None)], [True, False, False])
MT('measures-rooms', 'functions-by-default-and-by-extension',
   'R2 with no `function` is `unspecified`; R3 with the extension term `EXT_furniture:sauna` has it as written; the '
   'level counts one room of each.', ['FS-RULES-5.1.1', 'FS-RULES-8.4.1'],
   edit(lambda d: (d['rooms']['R2'].pop('function'), d['rooms']['R3'].update(function='EXT_furniture:sauna'), furniture(d, {}))),
   [(room('R2'), 'roomFunction', None), (room('R3'), 'roomFunction', None),
    (level('L1'), 'roomCount', {'function': 'EXT_furniture:sauna'}), (level('L1'), 'roomCount', {'function': 'unspecified'})],
   ['unspecified', 'EXT_furniture:sauna', 1, 1])


def check_oblique(results):
    w = results[0]['value']
    ensure(3500 * MM < w < 4600 * MM, f'least width {w}')
    ensure(results[1]['value'] == f'{_HALF}.5', 'the area with a half')


MT('measures-rooms', 'oblique-walls',
   'A four-sided room with oblique walls: its least width is the least, over its hull\'s edges, of the greatest distance '
   'of a vertex from the edge - a quotient of an integer by a square root, rounded once - and its net area has a half. '
   'Both values are the oracle\'s; the check bounds the width by hand.',
   ['FS-RULES-5.3.1', 'FS-RULES-5.2.1', 'FS-RULES-4.3.1'], oblique(),
   [(room('R1'), 'roomLeastWidth', None), (room('R1'), 'roomNetArea', None)], [..., ...], registry=None, check=check_oblique)


def ceilings(d):
    """The rules house as a Core 0.3 document with floors and ceilings (Core 15): L1's ceilings at 8'; the bedroom R1
    under a cathedral ceiling whose ridge runs east along its middle (y = 6') at 3200 mm, falling 6 in 12; the living
    room R2 sunk 6" with a flat ceiling at the level's height; the utility room R3 under a tray with a 1' border."""
    d['floorspec'] = '0.3'
    d['levels']['L1']['ceilingHeight'] = 8 * FT
    d['rooms']['R1']['ceiling'] = {'kind': 'vaulted', 'height': 3200 * MM, 'ridge': [[0, 6 * FT], [12 * FT, 6 * FT]],
                                   'pitch': {'rise': 6, 'run': 12}}
    d['rooms']['R2'].update(floor={'offset': -6 * IN}, ceiling={'kind': 'flat', 'height': H})
    d['rooms']['R3']['ceiling'] = {'kind': 'tray', 'border': FT, 'depth': 6 * IN}


HALF_DEPTH = 6 * FT - 64000                 # R1's walls' inner faces from its ridge line
MT('measures-rooms', 'ceiling-height',
   'The rules house with ceilings: the bedroom\'s cathedral ceiling comes down to 3200 mm less half of 6\' less 50 mm '
   'at its walls; the sunken living room\'s is the level\'s 2700 mm plus the 6" its floor is sunk; the utility '
   'room\'s is its tray\'s border at the level\'s 8\', not its raised centre. Each is Core\'s derived ceiling low minus '
   'its floor top.', ['FS-RULES-5.7.1', 'FS-RULES-4.3.1', 'FS-RULES-4.7.1'], edit(ceilings),
   [(room('R1'), 'ceilingHeight', None), (room('R2'), 'ceilingHeight', None), (room('R3'), 'ceilingHeight', None)],
   [3200 * MM - HALF_DEPTH // 2, H + 6 * IN, 8 * FT])
MT('measures-rooms', 'ceiling-height-in-a-0.2-document',
   'The rules house as it is, a Core 0.2 document: a reader of Core 0.3 derives every room a flat ceiling at the '
   'level\'s height over a floor at its elevation, so each room\'s ceiling height is 2700 mm.', ['FS-RULES-5.7.1'],
   house(), [(room('R1'), 'ceilingHeight', None), (room('R3'), 'ceilingHeight', None)], [H, H])
CEILING = rule(SLEEPING, C('ceilingHeight', '>=', 7 * FT), section='§2.1', title='Sleeping rooms are 7\' high')
R('measures-rooms', 'ceiling-height-rule',
  'A synthetic rule that a sleeping room\'s ceiling is at least 7\' high, on the rules house whose bedroom has a flat '
  'ceiling at 6\' 10": the bedroom may not meet it, and its finding shows 6\' 10" against 7\' 0". Under the cathedral '
  'ceiling - about 7\' 7" at its walls - it would meet it.', ['FS-RULES-5.7.1', 'FS-RULES-3.8.1', 'FS-RULES-9.6.1'],
  edit(lambda d: (d.update(floorspec='0.3'), d['rooms']['R1'].update(ceiling={'kind': 'flat', 'height': 82 * IN}))),
  req(pack({'CEILING': CEILING})), found=[('CEILING', 'R1')],
  check=lambda r: ensure(r['findings'][0]['measures'][0]['display'] == '6\' 10"', r['findings'][0]['measures']))


# ============================================================================= measures of openings (6)
def with_empty_opening(d):
    d['openings']['O6'] = {'wall': 'W6', 'offset': 2 * FT, 'width': 2 * FT, 'height': 7 * FT}


MT('measures-openings', 'the-rules-house',
   'Opening measures on the bedroom window O1 (3\' x 4\', sill 2\'), the door O2 (3\' x 6\' 8") between bedroom and '
   'living room, the front door O3 and an empty opening O6 in R3\'s south wall: kind, size as drawn, area, sill and head '
   'above the floor, and whether the wall faces the outside.',
   ['FS-RULES-6.1.1', 'FS-RULES-6.2.1', 'FS-RULES-6.3.1', 'FS-RULES-6.4.1', 'FS-RULES-4.7.1', 'FS-RULES-9.6.1'],
   edit(with_empty_opening),
   [(opening('O1'), 'openingKind', None), (opening('O2'), 'openingKind', None), (opening('O6'), 'openingKind', None),
    (opening('O1'), 'openingWidth', None), (opening('O1'), 'openingHeight', None), (opening('O2'), 'openingHeight', None),
    (opening('O1'), 'openingArea', None), (opening('O2'), 'openingArea', None),
    (opening('O1'), 'openingSillHeight', None), (opening('O2'), 'openingSillHeight', None),
    (opening('O1'), 'openingHeadHeight', None), (opening('O2'), 'openingHeadHeight', None),
    (opening('O1'), 'openingToOutside', None), (opening('O2'), 'openingToOutside', None),
    (opening('O3'), 'openingToOutside', None), (opening('O6'), 'openingToOutside', None)],
   ['window', 'door', 'empty', 3 * FT, 4 * FT, 80 * IN, str(3 * FT * 4 * FT), str(3 * FT * 80 * IN), 2 * FT, 0, 6 * FT, 80 * IN,
    True, False, True, True])
MT('measures-openings', 'heights-above-a-raised-floor',
   'The rules house on a level at 1,000 mm, with the bedroom\'s north wall W2 based 100 mm above it: the window\'s sill and '
   'head are measured from the level\'s floor, so both are 100 mm higher than in the rules house, and the level\'s own '
   'elevation does not count. Displayed in millimetres.',
   ['FS-RULES-6.3.1', 'FS-RULES-9.6.1'],
   edit(lambda d: (d['levels']['L1'].update(elevation=1000 * MM), d['walls']['W2'].update(base={'offset': 100 * MM}))),
   [(opening('O1'), 'openingSillHeight', None), (opening('O1'), 'openingHeadHeight', None)],
   [2 * FT + 100 * MM, 6 * FT + 100 * MM], units='metric',
   check=lambda rs: ensure([r['display'] for r in rs] == ['710 mm', '1929 mm'], 'metric'))


# ============================================================================= measures of elements (7.1 - 7.4)
def elements_doc(d):
    furniture(d, {'P1': {'fallback': {'level': 'L1', 'box': box(-300, -300, 0, 300, 300, 900)},
                         'host': {'mode': 'free', 'level': 'L1', 'position': [18 * FT, 6 * FT]}},
                  'P2': {'fallback': {'level': 'L1', 'box': box(-300, -300, 0, 300, 300, 900)},
                         'host': {'mode': 'free', 'level': 'L1', 'position': [12 * FT, 2 * FT]}},
                  'P3': {'fallback': {'level': 'L1', 'box': box(0, 0, -10, 300, 300, 900)}}})
    d['extensionsUsed'][LOWV] = '0.1.0'
    d['extensions'][LOWV] = {'collections': {'security': {
        'X6': on_wall('W2', 'right', 2 * FT, 2200, box(0, -40, -60, 40, 40, 60), device='motion', wireless=True),
        'X7': on_wall('W2', 'right', 8 * FT, 2200, box(0, -40, -60, 40, 40, 60), device='contact')}}}
    coll(d, ELEC, 'receptacles')['X5']['features'] = ['gfci']


MT('measures-elements', 'members-rooms-heights-and-protection',
   'Element measures on the rules house with three furniture pieces of EXT_furniture (P1 free in the living room, P2 free '
   'on the location line of W9, P3 unhosted) and two FS_lowvoltage security devices: members read with their '
   'defaults (a receptacle\'s 15 A, an alarm\'s `mainsWithBattery`, a contact\'s `wireless` false), a member of another '
   'type than asked (the panel\'s `volts` is an array) and one with no default (`watts`) have no value; the room each '
   'element is in, by its host; heights of fallbacks above the floor, one below it; and protection by a circuit (X4, '
   'on C1 with AFCI) or by the device itself (X5, a GFCI receptacle).',
   ['FS-RULES-7.1.1', 'FS-RULES-7.2.1', 'FS-RULES-7.3.1', 'FS-RULES-7.4.1', 'FS-RULES-4.4.1', 'FS-RULES-4.7.1', 'FS-RULES-9.6.1'],
   edit(elements_doc),
   [(element('X1'), 'elementMember', {'name': 'rating', 'type': 'integer', 'unit': 'A'}),
    (element('X1'), 'elementMember', {'name': 'volts', 'type': 'integer'}),
    (element('X3'), 'elementMember', {'name': 'detects', 'type': 'terms'}),
    (element('X4'), 'elementMember', {'name': 'amps', 'type': 'integer', 'unit': 'A'}),
    (element('X4'), 'elementMember', {'name': 'watts', 'type': 'integer', 'unit': 'W'}),
    (element('X3'), 'elementMember', {'name': 'power', 'type': 'term'}),
    (element('X4'), 'elementMember', {'name': 'features', 'type': 'terms'}),
    (element('X2'), 'elementMember', {'name': 'equipment', 'type': 'term'}),
    (element('X6'), 'elementMember', {'name': 'wireless', 'type': 'boolean'}),
    (element('X7'), 'elementMember', {'name': 'wireless', 'type': 'boolean'}),
    (element('X4'), 'elementRoomFunction', None), (element('X5'), 'elementRoomFunction', None),
    (element('X1'), 'elementRoomFunction', None), (element('X3'), 'elementRoomFunction', None),
    (element('P1'), 'elementRoomFunction', None), (element('P2'), 'elementRoomFunction', None),
    (element('P3'), 'elementRoomFunction', None),
    (element('X1'), 'elementBottomAboveFloor', None), (element('X1'), 'elementTopAboveFloor', None),
    (element('X3'), 'elementBottomAboveFloor', None), (element('P3'), 'elementBottomAboveFloor', None),
    (element('X4'), 'elementProtectedBy', {'protection': 'afci'}), (element('X4'), 'elementProtectedBy', {'protection': 'gfci'}),
    (element('X5'), 'elementProtectedBy', {'protection': 'gfci'})],
   [100, None, ['smoke'], 15, None, 'mainsWithBattery', [], 'boiler', True, False,
    'sleeping', 'sleeping', 'mechanical', 'sleeping', 'living', 'none', 'none',
    800 * MM, 1600 * MM, H - 50 * MM, -10 * MM, True, False, True],
   registry=KNOWN,
   check=lambda rs: ensure([rs[i]['display'] for i in (0, 1, 4, 6, 20)] == ['100 A', 'not stated', 'not stated', 'none', '-0\' 0 3/8"']
                           and rs[21]['involved'] == ['C1'] and rs[23]['involved'] == [], 'displays and involved'))
MT('measures-elements', 'heights-on-a-raised-level',
   'The rules house on a level at 1,000 mm: the panel\'s fallback is still 800 mm to 1,600 mm above its floor.',
   ['FS-RULES-7.3.1'], edit(lambda d: d['levels']['L1'].update(elevation=1000 * MM)),
   [(element('X1'), 'elementBottomAboveFloor', None), (element('X1'), 'elementTopAboveFloor', None)], [800 * MM, 1600 * MM])


# ============================================================================= measures of envelopes (7.5 - 7.8)
MT('measures-envelopes', 'the-rules-house',
   'The panel\'s working space (1000 mm deep, 800 mm wide, floor to 2,000 mm) and the boiler\'s service space as declared; '
   'nothing obstructs either; in front of the panel the space is clear to the 3\' limit, and with a 10\' limit it reaches '
   'the far wall of the utility room, W10, at 8\' less 100 mm; and no envelope overlaps another.',
   ['FS-RULES-7.5.1', 'FS-RULES-7.6.1', 'FS-RULES-7.7.1', 'FS-RULES-7.8.1', 'FS-RULES-4.7.1'], house(),
   [(envelope('X1', 'working'), 'envelopePurpose', None), (envelope('X1', 'working'), 'envelopeDepth', None),
    (envelope('X1', 'working'), 'envelopeWidth', None), (envelope('X1', 'working'), 'envelopeHeight', None),
    (envelope('X1', 'working'), 'envelopeBottomAboveFloor', None), (envelope('X2', 'service'), 'envelopeDepth', None),
    (envelope('X1', 'working'), 'envelopeObstructions', None), (envelope('X2', 'service'), 'envelopeObstructions', None),
    (envelope('X1', 'working'), 'clearDepthInFront', {'limit': 3 * FT}),
    (envelope('X1', 'working'), 'clearDepthInFront', {'limit': 10 * FT}),
    (envelope('X1', 'working'), 'envelopeOverlaps', None)],
   ['workingSpace', 1000 * MM, 800 * MM, 2000 * MM, 0, 750 * MM, 0, 0, 3 * FT, R3W, 0],
   check=lambda rs: ensure(rs[9]['involved'] == ['W10'] and rs[8]['involved'] == [], 'the far wall'))
MT('measures-envelopes', 'the-boiler-beside-the-panel',
   'The Phase 6 demo: the boiler stands in the panel\'s working space, so it obstructs it, the space is clear for 0, and '
   'the boiler\'s own service space overlaps the panel\'s.',
   ['FS-RULES-7.6.1', 'FS-RULES-7.7.1', 'FS-RULES-7.8.1'], DEMO,
   [(envelope('X1', 'working'), 'envelopeObstructions', None), (envelope('X1', 'working'), 'clearDepthInFront', {'limit': 3 * FT}),
    (envelope('X1', 'working'), 'envelopeOverlaps', None), (envelope('X1', 'working'), 'envelopeOverlaps', {'purpose': 'swing'})],
   [1, 0, 1, 0], check=lambda rs: ensure([r['involved'] for r in rs] == [['X2'], ['X2'], ['X2'], []], 'the boiler'))


def closet(d):
    d['junctions'].update({'J9': J(31 * FT, 8 * FT), 'J10': J(31 * FT, 10 * FT)})
    d['walls']['W11'] = W('J9', 'J10')


MT('measures-envelopes', 'a-wall-in-front-of-the-panel',
   'A free-standing wall W11 a foot in front of the panel\'s wall, across its working space: it obstructs the space, and '
   'the space is clear for 1\' less the two half-thicknesses, 200 mm (262,144 base units).',
   ['FS-RULES-7.6.1', 'FS-RULES-7.7.1'], edit(closet),
   [(envelope('X1', 'working'), 'envelopeObstructions', None), (envelope('X1', 'working'), 'clearDepthInFront', {'limit': 3 * FT})],
   [1, FT - 128000], check=lambda rs: ensure(rs[0]['involved'] == ['W11'] and rs[1]['involved'] == ['W11'], 'the wall'))


def swinging_doors(d):
    d['types']['DOOR']['clearances'] = {'swing': {'purpose': 'swing', 'shape': 'box', 'min': [0, -FT - FT // 2, 0],
                                                  'max': [3 * FT, FT + FT // 2, 80 * IN]}}


MT('measures-envelopes', 'door-swings',
   'Every door of the rules house with a swing envelope 3\' deep and wide: the swing of O4, into the utility room, is not '
   'obstructed by its own wall W10 (an owner\'s host is not its obstacle), is clear to the east wall W5, 8\' less 50 mm '
   'away, and overlaps the boiler\'s service space - as the boiler\'s space overlaps it, once of each purpose.',
   ['FS-RULES-7.6.1', 'FS-RULES-7.7.1', 'FS-RULES-7.8.1', 'FS-RULES-7.5.1'], edit(swinging_doors),
   [(envelope('O4', 'swing'), 'envelopePurpose', None), (envelope('O4', 'swing'), 'envelopeObstructions', None),
    (envelope('O4', 'swing'), 'clearDepthInFront', {'limit': 10 * FT}), (envelope('O4', 'swing'), 'envelopeOverlaps', None),
    (envelope('X2', 'service'), 'envelopeOverlaps', {'purpose': 'swing'}), (envelope('X2', 'service'), 'envelopeOverlaps', {'purpose': 'workingSpace'})],
   ['swing', 0, 8 * FT - 64000, 1, 1, 0],
   check=lambda rs: ensure(rs[2]['involved'] == ['W5'] and rs[3]['involved'] == ['X2'] and rs[4]['involved'] == ['O4'], 'involved'))


def turned_piece(d):
    furniture(d, {'P1': {'fallback': {'level': 'L1', 'box': box(-300, -300, 0, 300, 300, 900)},
                         'host': {'mode': 'free', 'level': 'L1', 'position': [18 * FT, 4 * FT], 'rotation': 30000000},
                         'clearances': {'front': env('access', box(300, -300, 0, 1300, 300, 900))}}})


MT('measures-envelopes', 'a-piece-turned-thirty-degrees',
   'A furniture piece in the living room turned 30 degrees, with an access space in front of it: the strip in front of '
   'it reaches the living room\'s east wall W10 obliquely, so its clear depth is irrational before it is rounded - about '
   '2,023,400 base units, the oracle\'s exact value - and nothing obstructs the space itself.',
   ['FS-RULES-7.7.1', 'FS-RULES-7.6.1', 'FS-RULES-4.3.1'], edit(turned_piece),
   [(envelope('P1', 'front'), 'clearDepthInFront', {'limit': 20 * FT}), (envelope('P1', 'front'), 'envelopeObstructions', None)],
   [..., 0], check=lambda rs: ensure(2000000 < rs[0]['value'] < 2050000 and rs[0]['involved'] == ['W10'], f'{rs[0]["value"]}'))


def high_shelf(d):
    furniture(d, {'S1': {'fallback': {'level': 'L1', 'box': box(-200, -300, 2100, 200, 300, 2400)},
                         'host': {'mode': 'free', 'level': 'L1', 'position': [32 * FT - 64000 - 500 * MM, 9 * FT]}},
                  'S2': {'fallback': {'level': 'L1', 'box': box(-200, -300, 0, 200, 300, 900)},
                         'host': {'mode': 'free', 'level': 'L1', 'position': [32 * FT - 64000 - 500 * MM, 9 * FT - 800 * MM]}}})


MT('measures-envelopes', 'above-and-beside-the-space',
   'A shelf S1 hung 2,100 mm up, right in front of the panel, and a cabinet S2 on the floor beside the space, 800 mm to the '
   'panel\'s right: the shelf is above the working space\'s 2,000 mm top and the cabinet\'s footprint ends 100 mm before '
   'the space\'s side, so neither obstructs it, and the space is clear to the limit.',
   ['FS-RULES-7.6.1', 'FS-RULES-7.7.1'], edit(high_shelf),
   [(envelope('X1', 'working'), 'envelopeObstructions', None), (envelope('X1', 'working'), 'clearDepthInFront', {'limit': 3 * FT})],
   [0, 3 * FT], check=lambda rs: ensure(rs[0]['involved'] == [] and rs[1]['involved'] == [], 'nothing'))


# ============================================================================= wall lines and receptacles (8.1, 8.2)
R1_LINE = 4 * INSIDE - 3 * FT          # R1's wall line less the doorway O2
MT('measures-walllines', 'the-rules-house',
   'Receptacle measures on the rules house. R1\'s wall line is 4 x 4,553,728 long, broken once by the door O2, so one '
   'stretch of 17,044,480 starting at the door\'s north jamb; its receptacles X4 and X5 are at 8,717,312 and 13,271,040 '
   'along it, so the longest run with no receptacle is the first 8,717,312, which is also the greatest reach. R2 has three '
   'doors and no receptacle, so its measures are its longest stretch, 8,327,168; R3, one door, 13,923,328.',
   ['FS-RULES-8.1.1', 'FS-RULES-8.2.1', 'FS-RULES-4.7.1'], house(),
   [(room('R1'), 'receptacleReach', None), (room('R1'), 'wallRunBetweenReceptacles', None),
    (room('R2'), 'receptacleReach', None), (room('R2'), 'wallRunBetweenReceptacles', None),
    (room('R3'), 'wallRunBetweenReceptacles', None)],
   [8717312, 8717312, 8327168, 8327168, 2 * (R3W + INSIDE) - 3 * FT],
   check=lambda rs: ensure(rs[0]['involved'] == ['X4', 'X5'] and rs[2]['involved'] == [], 'involved'))
MT('measures-walllines', 'which-receptacles-count',
   'R1 with a match and a height limit: no receptacle is 20 A (both are the default 15 A), and none is at most 200 mm '
   'above the floor, so none counts and the measure is the whole stretch; both are at 300 mm and 15 A, so with those '
   'they count.', ['FS-RULES-8.2.1'], house(),
   [(room('R1'), 'receptacleReach', {'match': {'amps': 20}}), (room('R1'), 'receptacleReach', {'maxHeight': 200 * MM}),
    (room('R1'), 'receptacleReach', {'maxHeight': 300 * MM}), (room('R1'), 'wallRunBetweenReceptacles', {'match': {'amps': 15}})],
   [R1_LINE, R1_LINE, 8717312, 8717312])


def closed_r3(n):
    def fn(d):
        d['openings'].pop('O4')
        r = coll(d, ELEC, 'receptacles')
        r['X6'] = on_wall('W5', 'right', 9 * FT, 300, PLATE)
        if n == 2:
            r['X7'] = on_wall('W10', 'right', 6 * FT, 300, PLATE)
        d['extensions'][ELEC]['circuits']['C1']['loads'] += sorted(k for k in r if k in ('X6', 'X7'))
    return fn


MT('measures-walllines', 'a-closed-wall-line-one-receptacle',
   'R3 without its door: its wall line has no break, so it is one closed stretch of 15,093,760, with no ends. With one '
   'receptacle the longest run is the whole loop and the greatest reach half of it.', ['FS-RULES-8.1.1', 'FS-RULES-8.2.1'],
   edit(closed_r3(1)), [(room('R3'), 'wallRunBetweenReceptacles', None), (room('R3'), 'receptacleReach', None)],
   [2 * (R3W + INSIDE), R3W + INSIDE])
MT('measures-walllines', 'a-closed-wall-line-two-receptacles',
   'R3 without its door, with receptacles on its east wall 3\' up from the south and on its west wall 6\' up: around the '
   'loop they are 8,717,312 apart one way and 6,376,448 the other; the longest run is 8,717,312, the greatest reach half.',
   ['FS-RULES-8.2.1'], edit(closed_r3(2)),
   [(room('R3'), 'wallRunBetweenReceptacles', None), (room('R3'), 'receptacleReach', None)], [8717312, 4358656])


def stub(d):
    d['junctions'].update({'J9': J(18 * FT, 12 * FT), 'J10': J(18 * FT, 9 * FT)})
    d['walls']['W3'] = W('J3', 'J9')
    d['walls']['W12'] = W('J9', 'J4')
    d['walls']['W11'] = W('J9', 'J10')
    d['openings']['O5'] = {'wall': 'W3', 'offset': FT, 'fill': 'WIN'}
    coll(d, ELEC, 'receptacles')['X8'] = on_wall('W11', 'left', FT, 300, PLATE)
    d['extensions'][ELEC]['circuits']['C1']['loads'].append('X8')


MT('measures-walllines', 'a-wall-that-stops-free',
   'A 3\' wall W11 standing out from the living room\'s north wall: the wall line runs down its east face, across its free '
   'end - a return 100 mm long - and up its west face. The long stretch, from O4 round to O2, is 10,540,032; a receptacle '
   'X8 on W11\'s east face, 1\' from the north wall, is 4,425,728 along it, so the longest run is the other 6,114,304.',
   ['FS-RULES-8.1.1', 'FS-RULES-8.2.1'], edit(stub),
   [(room('R2'), 'wallRunBetweenReceptacles', None), (room('R2'), 'receptacleReach', None),
    (room('R2'), 'wallRunBetweenReceptacles', {'match': {'amps': 20}})],
   [6114304, 6114304, 10540032])


# ============================================================================= circuits and levels (8.3, 8.4)
def second_circuit(d):
    c = d['extensions'][ELEC]['circuits']
    c['C1']['loads'].remove('X5')
    c['C2'] = {'panel': 'X1', 'breaker': 20, 'volts': 120, 'rating': 20, 'space': 2, 'loads': ['X5']}


MT('measures-circuits-and-levels', 'the-rules-house',
   'Circuits and levels: R1\'s receptacles and its alarm are all on C1 (15 A); no 20 A circuit feeds it; the living room '
   'has no circuit; the level has four FS_electrical elements, one FS_mechanical, one smoke alarm and three rooms, one '
   'of them a sleeping room.', ['FS-RULES-8.3.1', 'FS-RULES-8.4.1', 'FS-RULES-4.7.1'], house(),
   [(room('R1'), 'circuitCount', None), (room('R1'), 'circuitCount', {'circuit': {'breaker': 20}}),
    (room('R1'), 'circuitCount', {'collection': 'alarms'}), (room('R1'), 'circuitCount', {'match': {'amps': 15}}),
    (room('R1'), 'circuitCount', {'match': {'amps': 20}}), (room('R2'), 'circuitCount', None),
    (level('L1'), 'elementCount', {'extension': ELEC}), (level('L1'), 'elementCount', {'extension': MECH}),
    (level('L1'), 'elementCount', {'extension': ELEC, 'collection': 'alarms', 'match': {'detects': 'smoke'}}),
    (level('L1'), 'roomCount', None), (level('L1'), 'roomCount', {'function': 'sleeping'})],
   [1, 0, 1, 1, 0, 0, 4, 1, 1, 3, 1],
   check=lambda rs: ensure(rs[0]['involved'] == ['C1'] and rs[1]['involved'] == [], 'involved'))
MT('measures-circuits-and-levels', 'two-circuits',
   'X5 moved to a 20 A circuit C2 without AFCI: R1 has two receptacle circuits, one of them 20 A, and X5 is no longer '
   'AFCI-protected.', ['FS-RULES-8.3.1', 'FS-RULES-7.4.1'], edit(second_circuit),
   [(room('R1'), 'circuitCount', None), (room('R1'), 'circuitCount', {'circuit': {'breaker': 20}}),
    (element('X5'), 'elementProtectedBy', {'protection': 'afci'})], [2, 1, False],
   check=lambda rs: ensure(rs[0]['involved'] == ['C1', 'C2'] and rs[1]['involved'] == ['C2'], 'circuits'))



# ============================================================================= net clear openings (6.1, 6.5)
WIN_CLEAR = {'width': 30 * IN, 'height': 44 * IN, 'area': 8 * SQFT}       # 30" x 44", 8 sq ft declared
DOOR_CLEAR = {'width': 32 * IN, 'height': 78 * IN}


def clear_openings(d):
    """The rules house as a Core 0.3 document: its window type a casement and its door type a swing
    door, each with the clear opening its maker declares; the living room's window O5 overrides
    its clear opening without an area; and an empty opening O6 in R3's south wall states its own."""
    d['floorspec'] = '0.3'
    d['types']['WIN'].update(operation='casement', clearOpening=dict(WIN_CLEAR))
    d['types']['DOOR'].update(operation='swing', clearOpening=dict(DOOR_CLEAR))
    d['openings']['O5']['clearOpening'] = {'width': 28 * IN, 'height': 40 * IN}
    d['openings']['O6'] = {'wall': 'W6', 'offset': 2 * FT, 'width': 2 * FT, 'height': 7 * FT,
                           'clearOpening': {'width': 22 * IN, 'height': 82 * IN}}


CLEAR_HOUSE = edit(clear_openings)
MT('measures-openings', 'net-clear-openings',
   'The rules house as a Core 0.3 document whose window and door types declare their operation and clear opening. The '
   'bedroom window O1 has its type\'s 30" x 44" and 8 sq ft - not 30" times 44" - and no door clear width; the door O2 '
   'has its type\'s 32" x 78", no area, and a door clear width of 32"; the living-room window O5 overrides its clear '
   'opening without an area, so its area has no value; the empty opening O6 states its own clear opening, and has no '
   'door clear width and no operation.',
   ['FS-RULES-6.1.1', 'FS-RULES-6.5.1', 'FS-RULES-4.7.1', 'FS-RULES-9.6.1'], CLEAR_HOUSE,
   [(opening('O1'), 'openingOperation', None), (opening('O1'), 'openingNetClearWidth', None),
    (opening('O1'), 'openingNetClearHeight', None), (opening('O1'), 'openingNetClearArea', None),
    (opening('O1'), 'doorClearWidth', None),
    (opening('O2'), 'openingOperation', None), (opening('O2'), 'openingNetClearWidth', None),
    (opening('O2'), 'openingNetClearArea', None), (opening('O2'), 'doorClearWidth', None),
    (opening('O5'), 'openingNetClearWidth', None), (opening('O5'), 'openingNetClearArea', None),
    (opening('O6'), 'openingOperation', None), (opening('O6'), 'openingNetClearHeight', None),
    (opening('O6'), 'doorClearWidth', None)],
   ['casement', 30 * IN, 44 * IN, str(8 * SQFT), None, 'swing', 32 * IN, None, 32 * IN, 28 * IN, None, None, 82 * IN, None],
   check=lambda rs: ensure([rs[i]['display'] for i in (1, 3, 4, 7)] == ['2\' 6"', '8.00 sq ft', 'not stated', 'not stated'],
                           [r['display'] for r in rs]))
MT('measures-openings', 'net-clear-in-a-0.2-document',
   'The rules house as it is, a Core 0.2 document: it declares no operation and no clear opening, so every net clear '
   'measure has no value - none is computed from the openings\' sizes.', ['FS-RULES-6.5.1', 'FS-RULES-6.1.1'], house(),
   [(opening('O1'), 'openingNetClearWidth', None), (opening('O1'), 'openingNetClearHeight', None),
    (opening('O1'), 'openingNetClearArea', None), (opening('O2'), 'doorClearWidth', None),
    (opening('O2'), 'openingOperation', None)],
   [None, None, None, None, None])

NET_ESCAPE = rule(SLEEPING, {'all': [C('openingNetClearArea', '>=', 5 * SQFT), C('openingNetClearWidth', '>=', 20 * IN),
                                     C('openingNetClearHeight', '>=', 24 * IN), C('openingSillHeight', '<=', 44 * IN)]},
                  select={'from': 'openings', 'args': {'to': 'outside'},
                          'where': {'not': C('openingOperation', '=', 'fixed')}, 'need': 'any'},
                  section='§3.2', title='Net clear escape opening in every sleeping room')
R('selection', 'net-clear-escape-opening',
  'A synthetic escape rule on net clear openings, of any opening to the outside that is not fixed: the bedroom\'s '
  'casement O1 declares 8 sq ft, 30" by 44" clear, so R1 passes and the rule gives no finding.',
  ['FS-RULES-6.5.1', 'FS-RULES-3.5.1', 'FS-RULES-3.8.1'], CLEAR_HOUSE, req(pack({'NET-ESCAPE': NET_ESCAPE})),
  check=lambda r: ensure(r['evaluated'][0]['subjects'] == 1 and r['evaluated'][0]['findings'] == 0, 'no finding'))


def area_not_declared(d):
    clear_openings(d)
    del d['types']['WIN']['clearOpening']['area']


def check_not_stated(r):
    f = findings_of(r, 'NET-ESCAPE')[0]
    area = f['measures'][0]
    ensure(area['measure'] == 'openingNetClearArea' and area['value'] is None and area['display'] == 'not stated'
           and area['holds'] is False, area)
    ensure([m['holds'] for m in f['measures']] == [False, True, True, True], 'only the area fails')


R('selection', 'net-clear-area-not-stated',
  'The same rule when the casement\'s clear opening declares no area: its area is not 30" times 44" but has no value, '
  'which no threshold is met by (3.8), so R1 may not meet the rule; the finding shows the area as `not stated`.',
  ['FS-RULES-6.5.1', 'FS-RULES-3.8.1', 'FS-RULES-9.3.1', 'FS-RULES-9.6.1'], edit(area_not_declared),
  req(pack({'NET-ESCAPE': NET_ESCAPE})), found=[('NET-ESCAPE', 'R1')], check=check_not_stated)

DOOR_WIDTH = rule({'to': 'opening', 'where': C('openingKind', '=', 'door')}, C('doorClearWidth', '>=', 32 * IN),
                  section='§4.1', title='Door clear width')


def narrow_door(d):
    clear_openings(d)
    d['openings']['O2']['width'] = 32 * IN
    d['openings']['O2']['clearOpening'] = {'width': 30 * IN, 'height': 78 * IN}


R('selection', 'door-clear-width',
  'A synthetic door-width rule on every door: O3 and O4 have their type\'s 32" clear and pass; O2, a 32" door with its '
  'own 30" clear opening, may not meet it. The window and the empty opening are not subjects.',
  ['FS-RULES-6.5.1', 'FS-RULES-3.4.1', 'FS-RULES-3.6.1'], edit(narrow_door), req(pack({'DOOR-WIDTH': DOOR_WIDTH})),
  found=[('DOOR-WIDTH', 'O2')],
  check=lambda r: ensure(r['evaluated'][0]['subjects'] == 3
                         and findings_of(r, 'DOOR-WIDTH')[0]['measures'][0]['display'] == '2\' 6"', r['evaluated']))


# ============================================================================= what the text says, as TS found (9.4, 9.7)
SERVICE_CLEAR = rule({'to': 'element', 'extension': MECH, 'collection': 'equipment'}, C('envelopeOverlaps', '=', 0),
                     select={'from': 'envelopes', 'args': {'purpose': 'workingSpace'}, 'need': 'all'},
                     section='§6.1', title='Service space clear of other spaces')


def check_opening_drawn(r):
    f = findings_of(r, 'SERVICE')[0]
    ensure(f['measures'][0]['involved'] == ['O4'] and f['elements'] == ['O4', 'X2'], f['elements'])
    shapes = f['location']['shapes']
    ensure([s['kind'] for s in shapes] == ['polygon', 'polygon', 'segment'], shapes)
    ensure(shapes[2]['points'] == [[24 * FT, 4 * FT], [24 * FT, 7 * FT]], shapes[2])


R('findings', 'an-involved-opening-is-drawn',
  'A synthetic rule that the boiler\'s service space overlaps no other space, with every door swinging 3\': the space '
  'overlaps O4\'s swing, so X2 may not meet it, O4 is involved, and the finding draws the boiler, its service space '
  'and - as every involved ID with a shape (9.4) - the door O4, as the segment from its start to its end point.',
  ['FS-RULES-9.4.1', 'FS-RULES-7.8.1'], edit(swinging_doors), req(pack({'SERVICE': SERVICE_CLEAR})),
  found=[('SERVICE', 'X2')], check=check_opening_drawn)


def tagged_piece(d):
    furniture(d, {'P1': {'fallback': {'level': 'L1', 'box': box(-300, -300, 0, 300, 300, 900)},
                         'host': {'mode': 'free', 'level': 'L1', 'position': [18 * FT, 6 * FT]},
                         'tags': ['ﬁ', 'z', '\U0001f600', 'A']}})


MT('measures-elements', 'terms-in-utf-16-order',
   'A furniture piece whose `tags` member is the strings U+FB01, "z", U+1F600 and "A": a `terms` value is sorted as '
   'sequences of UTF-16 code units (9.7), so U+1F600 - the surrogates 0xD83D 0xDE00 - comes before U+FB01, although its '
   'code point is the larger; and the display lists them in the same order.',
   ['FS-RULES-9.7.1', 'FS-RULES-7.1.1', 'FS-RULES-4.7.1'], edit(tagged_piece),
   [(element('P1'), 'elementMember', {'name': 'tags', 'type': 'terms'})],
   [['A', 'z', '\U0001f600', 'ﬁ']],
   check=lambda rs: ensure(rs[0]['display'] == 'A, z, \U0001f600, ﬁ', rs[0]['display']))


# ============================================================================= stairs (8.5)
def stair(i):
    return {'kind': 'stair', 'id': i}


def stairs(d):
    """The rules house as a Core 0.3 document with a second level, L2, over the living room - a room U1 with 12" floors,
    and a well, from x = 16' to 23' 6" and y = 0 to 4', that no room is in - and two stairs. ST1 rises east in the
    living room from (13', 2'): 15 risers of 180 mm on 9" treads, 3' wide, with 34" handrails. ST2, in the bedroom, is
    a spiral 5' across and 30" wide, turning a full circle on 15 risers, with a 7 1/2" going at its walkline and no
    handrail."""
    d['floorspec'] = '0.3'
    d['levels']['L2'] = {'building': 'B1', 'elevation': H, 'height': H, 'floorThickness': 12 * IN}
    pts = {'K1': (12, 0), 'K2': (12, 12), 'K3': (24, 12), 'K4': (24, 0), 'K5': (23.5, 0), 'K6': (16, 0),
           'K7': (16, 4), 'K8': (23.5, 4)}
    d['junctions'].update({k: J(int(x * FT), int(y * FT), 'L2') for k, (x, y) in pts.items()})
    d['walls'].update({'V1': W('K1', 'K2', 'L2'), 'V2': W('K2', 'K3', 'L2'), 'V3': W('K3', 'K4', 'L2'),
                       'V4': W('K4', 'K5', 'L2'), 'V5': W('K5', 'K6', 'L2'), 'V6': W('K6', 'K1', 'L2')})
    d['separators'] = {'S1': {'level': 'L2', 'start': 'K6', 'end': 'K7'}, 'S2': {'level': 'L2', 'start': 'K7', 'end': 'K8'},
                       'S3': {'level': 'L2', 'start': 'K8', 'end': 'K5'}}
    d['rooms']['U1'] = {'level': 'L2', 'anchor': [18 * FT, 8 * FT], 'name': 'Upper hall', 'function': 'circulation'}
    d['stairs'] = {
        'ST1': {'level': 'L1', 'to': 'L2', 'position': [13 * FT, 2 * FT], 'width': 3 * FT, 'tread': 9 * IN, 'risers': 15,
                'handrail': {'height': 34 * IN}},
        'ST2': {'level': 'L1', 'to': 'L2', 'position': [6 * FT, 3 * FT], 'width': 30 * IN, 'tread': 15 * IN // 2, 'risers': 15,
                'form': {'kind': 'spiral', 'turn': 'left', 'diameter': 5 * FT, 'sweep': 360_000_000}}}


ST1_HEADROOM = H - 12 * IN - 5 * (H // 15)      # the floor's bottom over the nosing line at the well's edge, 5 risers up
MT('measures-stairs', 'stair-measures',
   'The five stair measures of 8.5 on the straight stair ST1 and the spiral ST2: each riser height is Core\'s, 2700 mm '
   'over 15 risers; each tread depth and width is the stair\'s own; ST1\'s headroom is Core\'s - at the well\'s west '
   'edge, 3\' past its first nosing, the nosing line is 5 risers up, under U1\'s floor, 12" thick - and its handrail is '
   '34"; the spiral has neither a headroom Core derives nor a handrail, so both are null.',
   ['FS-RULES-8.5.1', 'FS-RULES-4.7.1', 'FS-RULES-4.3.1'], edit(stairs),
   [(stair('ST1'), 'stairRiserHeight', None), (stair('ST1'), 'stairTreadDepth', None), (stair('ST1'), 'stairWidth', None),
    (stair('ST1'), 'stairHeadroom', None), (stair('ST1'), 'stairHandrailHeight', None),
    (stair('ST2'), 'stairRiserHeight', None), (stair('ST2'), 'stairTreadDepth', None), (stair('ST2'), 'stairWidth', None),
    (stair('ST2'), 'stairHeadroom', None), (stair('ST2'), 'stairHandrailHeight', None)],
   [H // 15, 9 * IN, 3 * FT, ST1_HEADROOM, 34 * IN, H // 15, 15 * IN // 2, 30 * IN, None, None])
STAIRS = {'to': 'stair'}
STAIR_PACK = pack({
    'RISER': rule(STAIRS, C('stairRiserHeight', '<=', 31 * IN // 4), section='§4.1', title='Risers no taller than 7 3/4 in'),
    'HEADROOM': rule({'to': 'stair', 'where': C('stairHeadroom', '>=', 0)}, C('stairHeadroom', '>=', 80 * IN), section='§4.2',
                     title='Headroom of 6 ft 8 in'),
    'HANDRAIL': rule(STAIRS, {'all': [C('stairHandrailHeight', '>=', 34 * IN), C('stairHandrailHeight', '<=', 38 * IN)]},
                     section='§4.3', title='A handrail 34 to 38 in high'),
    'TREAD': rule(STAIRS, C('stairTreadDepth', '>=', 10 * IN), exceptions=[{'when': C('stairWidth', '<', 36 * IN),
                                                                            'note': 'Synthetic: narrow stairs are exempt.'}],
                  section='§4.4', title='Treads at least 10 in deep'),
})


def check_stairs(r):
    f = findings_of(r, 'HEADROOM')[0]
    ensure(f['subject'] == stair('ST1') and f['location']['level'] == 'L1', f)
    ensure(f['location']['shapes'] == [{'kind': 'polygon', 'holes': [],
                                        'outer': [[13 * FT, 2 * FT - 18 * IN], [13 * FT + 14 * 9 * IN, 2 * FT - 18 * IN],
                                                  [13 * FT + 14 * 9 * IN, 2 * FT + 18 * IN], [13 * FT, 2 * FT + 18 * IN]]}],
           f['location'])
    ensure([e['subjects'] for e in r['evaluated'] if e['rule'] == 'HEADROOM'] == [1], r['evaluated'])


R('measures-stairs', 'stair-rules',
  'Four synthetic rules on the stairs: both have risers of 180 mm, under 7 3/4 in; only ST1 has a headroom - the rule '
  'applies only where one is derived - and at about 4\' 11" it may not meet 6\' 8"; the spiral declares no handrail, so '
  'both handrail conditions fail on it; and the spiral is exempt from the tread rule as narrower than 3\', while ST1\'s 9" '
  'treads may not meet 10". A stair\'s finding is on its level, L1, and draws its box.',
  ['FS-RULES-8.5.1', 'FS-RULES-3.4.1', 'FS-RULES-3.7.1', 'FS-RULES-3.8.1', 'FS-RULES-9.4.1'], edit(stairs), req(STAIR_PACK),
  found=[('HANDRAIL', 'ST2'), ('HEADROOM', 'ST1'), ('TREAD', 'ST1')], check=check_stairs)
STAIR_TYPED = pack({
    'GOOD': rule(STAIRS, C('stairWidth', '>=', 36 * IN), title='Well typed'),
    'ON-A-ROOM': rule(SLEEPING, C('stairWidth', '>=', 36 * IN), title='A stair measure on a room'),
    'ROOM-ON-A-STAIR': rule(STAIRS, C('roomNetArea', '>=', 1), title='A room measure on a stair'),
    'NO-SET': rule(STAIRS, C('stairWidth', '>=', 1), select={'from': 'rooms', 'need': 'any'}, title='Rooms of a stair'),
    'EXTENSION': rule({'to': 'stair', 'extension': ELEC}, C('stairWidth', '>=', 1), title='An extension on a stair'),
})
R('measures-stairs', 'stair-rules-typed',
  'A stair measure on a room, a room measure on a stair, a candidate set a stair does not have and an extension on a '
  'stair subject are not well typed (FS-RULES-007); the stair measures are no longer deferred, so a well-typed rule '
  'on stairs is evaluated - on a document with none it has no subject.',
  ['FS-RULES-3.9.1', 'FS-RULES-4.8.1'], house(), req(STAIR_TYPED),
  diags=[D('FS-RULES-007', pack='test-pack', rule=r) for r in ('EXTENSION', 'NO-SET', 'ON-A-ROOM', 'ROOM-ON-A-STAIR')],
  check=lambda r: ensure([(e['rule'], e['subjects']) for e in r['evaluated']] == [('GOOD', 0)], r['evaluated']))


# ============================================================================= writing the suite
def _json_bytes(v) -> bytes:
    return (fmt(v) + '\n').encode('utf-8')


def run(tc, doc_bytes, registry_bytes, request_bytes):
    """(expected bytes, problems) of one test."""
    problems = []
    if tc['kind'] == 'measures':
        out = call_measures(doc_bytes, registry_bytes, tc['calls'])
        got = [r['value'] for r in out['results']]
        for i, (want, have) in enumerate(zip(tc['expect'], got)):
            if want is not ... and want != have:
                problems.append(f'call {i} ({tc["calls"]["calls"][i]["measure"]}): hand {want!r}, oracle {have!r}')
        if len(tc['expect']) != len(got):
            problems.append('one hand value per call')
        if tc['check'] is not None and not problems:
            try:
                tc['check'](out['results'])
            except Exception as e:                       # noqa: BLE001
                problems.append(f'hand-written check failed: {type(e).__name__}: {e}')
        return report_bytes(out), problems
    report = evaluate(doc_bytes, registry_bytes, request_bytes)
    if report['diagnostics'] != sorted(tc['diags'], key=lambda d: (d['code'], d.get('packIndex', -1), d.get('pack', ''), d.get('rule', ''))):
        problems.append(f'diagnostics: hand {json.dumps(tc["diags"])}\n    oracle {json.dumps(report["diagnostics"])}')
    found = sorted((f['pack'], f['rule'], f['subject']['id']) for f in report['findings'])
    if found != tc['found']:
        problems.append(f'findings: hand {tc["found"]}\n    oracle {found}')
    if tc['check'] is not None and not problems:
        try:
            tc['check'](report)
        except Exception as e:                           # noqa: BLE001
            problems.append(f'hand-written check failed: {type(e).__name__}: {e}')
    return report_bytes(report), problems


def write_all(prune=False):
    counters, failures, seen = {}, 0, set()
    for tc in TESTS:
        g = tc['group']
        counters[g] = counters.get(g, 0) + 1
        d = os.path.join(SUITE, g, f"{counters[g]:03d}-{tc['slug']}")
        seen.add(d)
        os.makedirs(d, exist_ok=True)
        for stale in ('request.json', 'measures.json', 'registry.json'):
            if os.path.exists(os.path.join(d, stale)):
                os.remove(os.path.join(d, stale))
        doc_bytes = _json_bytes(tc['doc'])
        with open(os.path.join(d, 'input.json'), 'wb') as f:
            f.write(doc_bytes)
        with open(os.path.join(d, 'test.json'), 'w', encoding='utf-8') as f:
            f.write(json.dumps({'description': tc['description'], 'covers': sorted(set(tc['covers']))}, indent=2, ensure_ascii=False) + '\n')
        registry_bytes = None
        if tc['registry'] is not None:
            registry_bytes = _json_bytes(tc['registry'])
            with open(os.path.join(d, 'registry.json'), 'wb') as f:
                f.write(registry_bytes)
        if tc['kind'] == 'measures':
            request_bytes = _json_bytes(tc['calls'])
            with open(os.path.join(d, 'measures.json'), 'wb') as f:
                f.write(request_bytes)
        else:
            request_bytes = tc['raw_request'] if tc['raw_request'] is not None else _json_bytes(tc['request'])
            with open(os.path.join(d, 'request.json'), 'wb') as f:
                f.write(request_bytes)
        expected, problems = run(tc, doc_bytes, registry_bytes, request_bytes)
        if assures(expected.decode('utf-8')):
            problems.append('the expected output matches the assurance pattern (9.5.2)')
        with open(os.path.join(d, 'expected.json'), 'wb') as f:
            f.write(expected)
        if problems:
            failures += 1
            print(f'MISMATCH {os.path.relpath(d, REPO)}')
            for p in problems:
                print('  ' + p)
    if prune and os.path.isdir(SUITE):
        for g in sorted(os.listdir(SUITE)):
            for n in sorted(os.listdir(os.path.join(SUITE, g))):
                if os.path.join(SUITE, g, n) not in seen:
                    print('removing', os.path.join(SUITE, g, n))
                    shutil.rmtree(os.path.join(SUITE, g, n))
    print(f'{len(TESTS)} tests, {failures} mismatches')
    return failures


if __name__ == '__main__':
    sys.exit(1 if write_all(prune='--prune' in sys.argv) else 0)

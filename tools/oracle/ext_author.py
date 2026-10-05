"""The conformance suites of the official extensions - FS_electrical, FS_plumbing, FS_mechanical and
FS_lowvoltage 0.1.0 - as the script that writes them.

    python3.13 -m tools.oracle.ext_author            rewrite every test from its declaration below
    python3.13 -m tools.oracle.ext_author --prune    ...and delete test directories no longer declared

Each suite is conformance/ext/<NAME>/0.1.0/, run by an implementation of that one extension (a Core
0.2 reader that implements <NAME> 0.1.0 and no other extension), configured with the test's
registry.json as its known extensions, or with none when the test has no registry.json. Most tests
are validator and deriver tests, laid out as Core's (input.json, registry.json, expected.json,
canonical.json; expected.json's `derived` has an `extensions` member); the tests in `ops` are Ops
0.2 tests (input.json, request.json, registry.json, expected.json, output.json), applied by an
applier whose validator is that implementation.

Almost every test starts from one document: the Phase 5 demo house (demo() below) - a kitchen, a
bath and a utility room with a panel, kitchen receptacles on two 20 A circuits, a toilet, a wall-hung
lavatory, an electric water heater on a 240 V circuit, a gas furnace and range on a meter, a bath
fan a switch controls, and data, doorbell, speaker and security devices run to a structured media
enclosure - and breaks one rule of it. Every expected diagnostic is written by hand and
cross-checked against the oracle; the derived values that matter are asserted by hand in `check`.
"""
import copy
import json
import os
import shutil
import sys

from tools.oracle.author_lib import fmt
from tools.oracle.ext import official
from tools.oracle.jsonparse import parse
from tools.oracle.ops.engine import apply
from tools.oracle.ops.suite import dumps as ops_dumps, expected_view, properties
from tools.oracle.ops.version import OPS_02
from tools.oracle.report import dumps
from tools.oracle.validate import READER_02, SEVERITY, check

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
MM, FT = 1280, 390144
H = 2700 * MM
ELEC, PLMB, MECH, LOWV = 'FS_electrical', 'FS_plumbing', 'FS_mechanical', 'FS_lowvoltage'
EXTS = (ELEC, PLMB, MECH, LOWV)
CODE = {ELEC: 'ELEC', PLMB: 'PLMB', MECH: 'MECH', LOWV: 'LOWV'}
SEV = {**SEVERITY, **official.SEVERITY}


def entry(name, version=None):
    with open(os.path.join(REPO, 'registry', name, 'extension.json'), encoding='utf-8') as f:
        e = json.load(f)
    if version is not None:
        e['version'] = version
    return e


# ============================================================================= the demo house

def J(x, y):
    return {'level': 'L1', 'position': [x, y]}


def W(s, e):
    return {'level': 'L1', 'start': s, 'end': e, 'type': 'WT'}


def box(x0, y0, z0, x1, y1, z1):
    return {'min': [x0 * MM, y0 * MM, z0 * MM], 'max': [x1 * MM, y1 * MM, z1 * MM]}


def env(purpose, b):
    return {'purpose': purpose, 'shape': 'box', **b}


def on_wall(wall, side, offset, height, b, **members):
    return {'fallback': {'level': 'L1', 'box': b},
            'host': {'mode': 'wallFace', 'wall': wall, 'side': side, 'offset': offset, 'height': height * MM},
            **members}


def on_surface(room, surface, x, y, b, rotation=None, **members):
    host = {'mode': 'surface', 'room': room, 'surface': surface, 'position': [x, y]}
    if rotation is not None:
        host['rotation'] = rotation
    return {'fallback': {'level': 'L1', 'box': b}, 'host': host, **members}


PLATE = box(0, -40, -60, 25, 40, 60)                     # a receptacle, a switch, a data outlet
AGAINST_NORTH = 12 * FT - 76800                          # 10 mm in from the north walls' faces


def demo():
    """The Phase 5 demo house, 20' x 12', on L1, with every wall 100 mm thick and drawn clockwise:

        J2 ------ W2 ------ J3 ---- W3 ---- J4
        |                   |               |
        W1   Kitchen R1     W9   Bath R2    W4
        |                   |               |
        |                   J7 ---- W10 --- J8
        |                   |               |
        |                   W8  Utility R3  W5
        |                   |               |
        J1 ------ W7 ------ J6 ---- W6 ---- J5

    J1 (0, 0), J2 (0, 12'), J3 (12', 12'), J4 (20', 12'), J5 (20', 0), J6 (12', 0), J7 (12', 6'),
    J8 (20', 6'). An exterior wall's right face is inside; W8 and W9 (running north) have the
    Kitchen on their left, W10 (running east) has the Bath on its left and the Utility room on its
    right."""
    d = {
        'floorspec': '0.2', 'project': {'name': 'Phase 5 demo house'},
        'buildings': {'B1': {}}, 'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
        'types': {'WT': {'kind': 'wallType', 'layers': [{'thickness': 100 * MM, 'function': 'core'}]}},
        'junctions': {'J1': J(0, 0), 'J2': J(0, 12 * FT), 'J3': J(12 * FT, 12 * FT), 'J4': J(20 * FT, 12 * FT),
                      'J5': J(20 * FT, 0), 'J6': J(12 * FT, 0), 'J7': J(12 * FT, 6 * FT), 'J8': J(20 * FT, 6 * FT)},
        'walls': {'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J8'),
                  'W5': W('J8', 'J5'), 'W6': W('J5', 'J6'), 'W7': W('J6', 'J1'), 'W8': W('J6', 'J7'),
                  'W9': W('J7', 'J3'), 'W10': W('J7', 'J8')},
        'rooms': {'R1': {'level': 'L1', 'anchor': [6 * FT, 6 * FT], 'name': 'Kitchen', 'function': 'kitchen'},
                  'R2': {'level': 'L1', 'anchor': [16 * FT, 9 * FT], 'name': 'Bath', 'function': 'bath'},
                  'R3': {'level': 'L1', 'anchor': [16 * FT, 3 * FT], 'name': 'Utility', 'function': 'mechanical'}},
        'extensionsUsed': {x: '0.1.0' for x in EXTS},
        'extensions': {
            ELEC: {
                'collections': {
                    'panels': {'X1': on_wall('W5', 'right', 3 * FT, 1200, box(0, -200, -400, 100, 200, 400),
                                             name='Main panel', volts=[120, 240], rating=200, mainBreaker=200, spaces=40,
                                             clearances={'working': env('workingSpace', box(0, -400, -1200, 1000, 400, 800))})},
                    'receptacles': {
                        'X2': on_wall('W2', 'right', 6 * FT, 1100, PLATE, amps=20, features=['gfci', 'tamperResistant']),
                        'X3': on_wall('W2', 'right', 9 * FT, 1100, PLATE, amps=20, features=['gfci', 'tamperResistant']),
                        'X4': on_wall('W9', 'left', 3 * FT, 1100, PLATE, amps=20, features=['gfci', 'tamperResistant']),
                        'X5': on_wall('W1', 'right', 6 * FT, 1100, PLATE, amps=20, features=['gfci', 'tamperResistant'])},
                    'switches': {'X21': on_wall('W8', 'left', FT, 1200, PLATE, controls=['X22']),
                                 'X26': on_wall('W9', 'right', FT, 1200, PLATE, controls=['X13'])},
                    'lights': {'X22': on_surface('R1', 'ceiling', 6 * FT, 6 * FT, box(-100, -100, -150, 100, 100, 0),
                                                 fixture='recessed', watts=12)},
                    'alarms': {'X23': on_surface('R1', 'ceiling', 9 * FT, 9 * FT, box(-75, -75, -50, 75, 75, 0),
                                                 detects=['smoke', 'carbonMonoxide'], interconnect='A')},
                    'evChargers': {'X24': on_wall('W7', 'left', 3 * FT, 1200, box(0, -150, -200, 100, 150, 200),
                                                  amps=32, connector='j1772')}},
                'circuits': {
                    'C1': {'panel': 'X1', 'breaker': 20, 'volts': 120, 'rating': 20, 'space': 1, 'protection': ['afci'],
                           'loads': ['X2', 'X3'], 'name': 'Kitchen counter 1'},
                    'C2': {'panel': 'X1', 'breaker': 20, 'volts': 120, 'rating': 20, 'space': 2, 'protection': ['afci'],
                           'loads': ['X4', 'X5'], 'name': 'Kitchen counter 2'},
                    'C3': {'panel': 'X1', 'breaker': 30, 'poles': 2, 'volts': 240, 'rating': 30, 'space': 3,
                           'loads': ['X8'], 'name': 'Water heater'},
                    'C4': {'panel': 'X1', 'breaker': 15, 'volts': 120, 'rating': 15, 'space': 5, 'protection': ['afci'],
                           'loads': ['X22', 'X23', 'X13'], 'name': 'Kitchen and bath lights'},
                    'C5': {'panel': 'X1', 'breaker': 40, 'poles': 2, 'volts': 240, 'rating': 40, 'space': 6,
                           'loads': ['X24'], 'name': 'EV charger'}}},
            PLMB: {
                'collections': {
                    'fixtures': {
                        'X6': on_surface('R2', 'floor', 16 * FT, AGAINST_NORTH, box(0, -190, 0, 700, 190, 800), -90000000,
                                         fixture='waterCloset', supply=['cold'], drain='K1',
                                         clearances={'front': env('fixtureClearance', box(700, -400, 0, 1300, 400, 2000))}),
                        'X7': on_wall('W4', 'right', 3 * FT, 800, box(0, -250, -200, 500, 250, 0),
                                      fixture='lavatory', supply=['cold', 'hot'], hotFrom='X8', drain='K1',
                                      clearances={'front': env('fixtureClearance', box(500, -250, -800, 1100, 250, 1200))}),
                        'X25': on_wall('W1', 'left', 2 * FT, 500, box(0, -40, -40, 100, 40, 40),
                                       fixture='hoseBibb', supply=['cold'])},
                    'waterHeaters': {'X8': on_surface('R3', 'floor', 14 * FT, 2 * FT, box(-280, -280, 0, 280, 280, 1500), 90000000,
                                                      heater='storage', energy='electric', capacity=189000, input=4500, drain='X9',
                                                      clearances={'service': env('access', box(280, -280, 0, 880, 280, 1500))})},
                    'drains': {'X9': on_surface('R3', 'floor', 16 * FT, 2 * FT, box(-75, -75, -10, 75, 75, 0),
                                                receptor='floor', drain='K1')},
                    'cleanouts': {'X27': on_wall('W5', 'right', 5 * FT, 300, box(0, -60, -60, 20, 60, 60), stack='K1',
                                                 clearances={'access': env('access', box(20, -225, -60, 470, 225, 390))})}},
                'stacks': {'K1': {'levels': ['L1'], 'size': 97536, 'outlet': 'sewer', 'name': 'Main stack'}}},
            MECH: {
                'collections': {
                    'equipment': {'X10': on_surface('R3', 'floor', 18 * FT, 4 * FT, box(-280, -280, 0, 280, 280, 1400), 180000000,
                                                    equipment='furnace', fuel='naturalGas', input=17600, heating=16000,
                                                    airflow=188000, combustionAir='direct', vent='direct', gasFrom='G1',
                                                    clearances={'service': env('workingSpace', box(280, -375, 0, 1030, 375, 2000))})},
                    'terminals': {'X11': on_surface('R1', 'floor', 6 * FT, FT, box(-150, -50, -20, 150, 50, 0),
                                                    terminal='supply', equipment='X10', airflow=94000),
                                  'X12': on_wall('W1', 'right', 9 * FT, 300, box(0, -200, -150, 20, 200, 150),
                                                 terminal='return', equipment='X10', airflow=94000)},
                    'exhaust': {'X13': on_surface('R2', 'ceiling', 16 * FT, 8 * FT, box(-130, -130, -150, 130, 130, 0),
                                                  exhaust='bathFan', airflow=37750, discharge='outdoors')},
                    'gasAppliances': {'X14': on_surface('R1', 'floor', 3 * FT, AGAINST_NORTH, box(0, -380, 0, 650, 380, 920), -90000000,
                                                        appliance='range', fuel='naturalGas', input=17600,
                                                        combustionAir='indoor', vent='none', gasFrom='G1')}},
                'gasSources': {'G1': {'fuel': 'naturalGas', 'name': 'Utility meter'}}},
            LOWV: {
                'collections': {
                    'headEnds': {'X15': on_wall('W6', 'right', 2 * FT, 1500, box(0, -180, -450, 100, 180, 450),
                                                headEnd='structuredMedia', serves=['data', 'coax', 'doorbell', 'security', 'audio'],
                                                clearances={'access': env('access', box(100, -180, -450, 700, 180, 450))})},
                    'outlets': {'X16': on_wall('W1', 'right', 2 * FT, 300, PLATE, media=['data', 'coax'], ports=2, headEnd='X15')},
                    'doorbells': {'X17': on_wall('W7', 'left', 7 * FT, 1200, box(0, -20, -40, 20, 20, 40), part='button', chime='X18'),
                                  'X18': on_wall('W9', 'left', 5 * FT, 2000, box(0, -100, -100, 50, 100, 100), part='chime', headEnd='X15')},
                    'speakers': {'X19': on_surface('R1', 'ceiling', 3 * FT, 6 * FT, box(-100, -100, -100, 100, 100, 0),
                                                   speaker='inCeiling', zone='Kitchen', headEnd='X15')},
                    'security': {'X20': on_wall('W8', 'right', 5 * FT, 2200, box(0, -40, -60, 40, 40, 60),
                                                device='motion', zone='Utility', headEnd='X15')}}},
        },
    }
    return d


def ext(d, name):
    return d['extensions'][name]


def coll(d, name, c):
    return d['extensions'][name]['collections'][c]


def edit(fn):
    """The demo house, changed by fn(d) in place."""
    d = demo()
    fn(d)
    return d


# ============================================================================= declaring tests

TESTS = []
KNOWN = 'known'          # the default: the suite's own extension's registry entry


def cov(name, ids):
    return [i if i.startswith('FS-') else f'FS-{CODE[name]}-{i}' for i in ids]


def V(name, group, slug, description, covers, doc, diags=(), registry=KNOWN, check=None, raw=None):
    """A validator and deriver test. registry: KNOWN (the extension's own entry), None (no known
    extensions) or a list of entries. check(result) is a hand-written assertion."""
    TESTS.append(dict(kind='core', ext=name, group=group, slug=slug, description=description, covers=cov(name, covers),
                      doc=doc, raw=raw, registry=[entry(name)] if registry is KNOWN else registry, check=check,
                      diags=[{'code': c, 'severity': SEV.get(c, 'error'), 'elements': sorted(set(e))} for c, e in diags]))


def O(name, slug, description, covers, a, request, status='committed', diags=(), check=None):
    """An Ops 0.2 test, applied by an applier that implements the extension and knows it."""
    TESTS.append(dict(kind='ops', ext=name, group='ops', slug=slug, description=description, covers=cov(name, covers),
                      doc=a, request=request, registry=[entry(name)], status=status, check=check,
                      diags=[{'code': c, 'severity': SEV.get(c, 'error'), 'elements': sorted(set(e))} for c, e in diags]))


def ensure(cond, what):
    if not cond:
        raise AssertionError(what)


def derived_of(name):
    return lambda r: r['derived']['extensions'][name]


def placements(d, name):
    """What an implementation of `name` that knows it derives as placements, for a check."""
    result, _, _ = check(json.dumps(d).encode('utf-8'), READER_02, json.dumps([entry(name)]).encode('utf-8'),
                         official.implemented(name))
    assert result['valid'], result['diagnostics']
    return result['derived']['placements']


def moved(a, b, name, eid):
    pa, pb = placements(a, name)[eid]['point'], placements(b, name)[eid]['point']
    return [pb[i] - pa[i] for i in range(3)]


# ============================================================================= every suite: the shared tests

def shared(name):
    code = CODE[name]
    T = lambda *a, **k: V(name, *a, **k)    # noqa: E731
    T('examples', 'p5-demo-house', f'The Phase 5 demo house, read by an implementation of {name} that knows it: a panel, '
      'kitchen receptacles on two 20 A circuits, a toilet, a lavatory, an electric water heater on a 240 V circuit, a '
      'gas furnace and range, a bath fan, and low-voltage devices run to a structured media enclosure. It is valid, '
      f'reports nothing, and derives {name}\'s values as `derived.extensions.{name}`.',
      ['1.2.1', '1.2.3', '1.2.4', '1.3.1', DERIVE[name]], demo(), check=DEMO_CHECK[name])
    T('examples', 'core-only-reader', f'The same house read with no known extensions: {name} is not evaluated, so '
      'nothing of it is derived (`derived.extensions` is empty) - only what Core derives from every extension '
      'element\'s fallback, host and clearances (Core 1.6.9): their fallbacks, placements and clearances.',
      ['1.2.1', '1.2.4', 'FS-CORE-1.6.9', 'FS-CORE-12.6.2', 'FS-CORE-13.4.1', 'FS-CORE-13.5.2'], demo(), registry=None,
      check=lambda r: ensure(r['derived']['extensions'] == {} and 'X1' in r['derived']['fallbacks']
                             and r['derived']['placements']['X6']['facing'] == -90000000
                             and 'service' in r['derived']['clearances']['X8'], r['derived']['extensions']))
    T('examples', 'all-four-known', f'The house read with all four official entries known, by an implementation of '
      f'{name} alone: the other three are checked only as Core 12 checks a known extension, and only {name} is '
      'evaluated and derived.', ['1.2.1', '1.2.4'], demo(), registry=[entry(x) for x in EXTS],
      check=lambda r: ensure(list(r['derived']['extensions']) == [name], list(r['derived']['extensions'])))
    T('activation', 'unknown-data-not-evaluated', f'{name}\'s data does not match its schema, but no extension is '
      'known: nothing of it is evaluated, and the document is valid.', ['1.2.1'],
      edit(lambda d: ext(d, name).update(colour='red')), registry=None)
    T('activation', 'another-version-known', f'The document uses {name} at 0.2.0, which is known (a later entry), but '
      'the implementation implements 0.1.0: not evaluated, so the data that breaks 0.1.0\'s schema is not reported.',
      ['1.2.1'], edit(lambda d: (ext(d, name).update(colour='red'), d['extensionsUsed'].update({name: '0.2.0'}))),
      registry=[entry(name, '0.2.0')])
    T('activation', 'version-without-patch', f'"0.1" equals 0.1.0 (Core 12.3), so {name} is evaluated: its data breaks '
      f'the schema, FS-{code}-SCH-001.', ['1.2.1', '1.3.1'],
      edit(lambda d: (ext(d, name).update(colour='red'), d['extensionsUsed'].update({name: '0.1'}))),
      [(f'FS-{code}-SCH-001', [])])
    T('activation', 'declaration-object', f'A declaration object with a schema URI is its version string (Core 12.1.3): '
      f'{name} is evaluated.', ['1.2.1', '1.3.1'],
      edit(lambda d: (ext(d, name).update(colour='red'),
                      d['extensionsUsed'].update({name: {'version': '0.1.0', 'schema': entry(name)['schema']}}))),
      [(f'FS-{code}-SCH-001', [])])
    T('activation', 'core-0.1-document', f'A document declaring "0.1" has no extension elements and its extension data is '
      f'opaque (Core 1.2.4): {name} is not evaluated, even though it is known.', ['1.2.1'],
      {'floorspec': '0.1', 'project': {'name': 'Old'}, 'extensionsUsed': {name: '0.1.0'},
       'extensions': {name: {'colour': 'red'}}})
    T('order', 'core-error-first', 'A Core invariant breaks - an element 13\' along the 12\' wall W2, FS-INV-501 - '
      f'and so does {name}\'s schema: Core\'s error is reported, and {name} is not evaluated.', ['1.2.2'],
      edit(lambda d: (ext(d, name).update(colour='red'), WALL_ELEMENT[name](d)['host'].update(wall='W2', offset=13 * FT))),
      [('FS-INV-501', [WALL_ELEMENT_ID[name]])])
    T('order', 'schema-before-invariants', f'The data breaks the schema and an invariant: only FS-{code}-SCH-001.',
      ['1.2.2', '1.3.1'], edit(lambda d: (ext(d, name).update(colour='red'), BREAK[name](d))), [(f'FS-{code}-SCH-001', [])])
    T('order', 'no-lints-when-invalid', f'An invariant breaks and a lint would apply too: the document is invalid, so no '
      f'lint is reported, {name}\'s or Core\'s.', ['1.2.2', '1.2.3'], edit(lambda d: (BREAK[name](d), LINT[name](d))),
      BREAK_DIAG[name])
    T('schema', 'data-not-an-object', f'{name}\'s top-level data is an array: Core allows any JSON there, {name}\'s '
      'schema does not.', ['1.3.1'], edit(lambda d: d['extensions'].update({name: []})), [(f'FS-{code}-SCH-001', [])])
    T('schema', 'unknown-collection-member', 'An element has a member its kind does not define.', ['1.3.1'],
      edit(lambda d: WALL_ELEMENT[name](d).update(colour='red')), [(f'FS-{code}-SCH-001', [])])
    T('schema', 'length-with-a-fraction', 'A number written with a fraction is not an integer, even when it is a whole '
      'number.', ['1.3.1'], None, [(f'FS-{code}-SCH-001', [])],
      raw=(fmt(demo()) + '\n').replace(FRACTION[name][0], FRACTION[name][1], 1).encode('utf-8'))


# what each suite's shared tests reach for
WALL_ELEMENT_ID = {ELEC: 'X5', PLMB: 'X25', MECH: 'X12', LOWV: 'X16'}
WALL_ELEMENT = {ELEC: lambda d: coll(d, ELEC, 'receptacles')['X5'], PLMB: lambda d: coll(d, PLMB, 'fixtures')['X25'],
                MECH: lambda d: coll(d, MECH, 'terminals')['X12'], LOWV: lambda d: coll(d, LOWV, 'outlets')['X16']}
BREAK = {ELEC: lambda d: ext(d, ELEC)['circuits']['C1'].update(panel='X99'),
         PLMB: lambda d: coll(d, PLMB, 'fixtures')['X6'].update(drain='X25'),
         MECH: lambda d: coll(d, MECH, 'gasAppliances')['X14'].update(gasFrom='G9'),
         LOWV: lambda d: coll(d, LOWV, 'outlets')['X16'].update(headEnd='X1')}
BREAK_DIAG = {ELEC: [('FS-ELEC-INV-002', ['C1'])], PLMB: [('FS-PLMB-INV-002', ['X6'])],
              MECH: [('FS-MECH-INV-002', ['X14'])], LOWV: [('FS-LOWV-INV-001', ['X16'])]}
LINT = {ELEC: lambda d: coll(d, ELEC, 'panels')['X1'].pop('clearances'),
        PLMB: lambda d: coll(d, PLMB, 'waterHeaters')['X8'].pop('clearances'),
        MECH: lambda d: coll(d, MECH, 'equipment')['X10'].pop('clearances'),
        LOWV: lambda d: coll(d, LOWV, 'headEnds')['X15'].pop('clearances')}
FRACTION = {ELEC: ('"rating": 200', '"rating": 200.0'), PLMB: ('"capacity": 189000', '"capacity": 189000.0'),
            MECH: ('"airflow": 94000', '"airflow": 94000.0'), LOWV: ('"ports": 2', '"ports": 2.0')}
DERIVE = {ELEC: '6.1.1', PLMB: '5.1.1', MECH: '5.1.1', LOWV: '5.1.1'}


def check_elec(r):
    x = r['derived']['extensions'][ELEC]
    ensure(x['circuits']['C1'] == {'panel': 'X1', 'loads': ['X2', 'X3'], 'connectedLoad': 0, 'capacity': 2400}, x['circuits']['C1'])
    ensure(x['circuits']['C4']['loads'] == ['X13', 'X22', 'X23'] and x['circuits']['C4']['connectedLoad'] == 12, x['circuits']['C4'])
    ensure(x['circuits']['C3']['capacity'] == 7200, x['circuits']['C3'])
    ensure(x['panels'] == {'X1': {'circuits': ['C1', 'C2', 'C3', 'C4', 'C5'], 'spacesUsed': 7, 'connectedLoad': 12}}, x['panels'])
    ensure(x['controls'] == {'X13': ['X26'], 'X22': ['X21']}, x['controls'])
    # the room of an element: X5 on W1's right (east) face and X4 on W9's left (west) face are in
    # the Kitchen; the panel on W5's right face is in the Utility room; the EV charger on W7's left
    # (south, outside) face is in no room
    ensure(x['rooms'] == {'R1': ['X2', 'X21', 'X22', 'X23', 'X3', 'X4', 'X5'], 'R2': ['X26'], 'R3': ['X1']}, x['rooms'])


def check_plmb(r):
    x = r['derived']['extensions'][PLMB]
    ensure(x['stacks'] == {'K1': {'connected': ['X6', 'X7', 'X8', 'X9'], 'cleanouts': ['X27']}}, x['stacks'])
    ensure(x['waterHeaters'] == {'X8': {'fixtures': ['X7']}}, x['waterHeaters'])
    ensure(x['rooms'] == {'R2': ['X6', 'X7'], 'R3': ['X27', 'X8', 'X9']}, x['rooms'])      # the hose bibb is outside


def check_mech(r):
    x = r['derived']['extensions'][MECH]
    ensure(x['gasSources'] == {'G1': {'fuel': 'naturalGas', 'appliances': ['X10', 'X14'], 'input': 35200}}, x['gasSources'])
    ensure(x['equipment'] == {'X10': {'terminals': ['X11', 'X12'], 'airflow': 188000}}, x['equipment'])
    ensure(x['rooms'] == {'R1': ['X11', 'X12', 'X14'], 'R2': ['X13'], 'R3': ['X10']}, x['rooms'])


def check_lowv(r):
    x = r['derived']['extensions'][LOWV]
    ensure(x['headEnds'] == {'X15': {'runs': ['X16', 'X18', 'X19', 'X20'], 'ports': {'coax': 2, 'data': 2}}}, x['headEnds'])
    # the doorbell button is outside; the motion sensor on W8's right (east) face is in the Utility room
    ensure(x['rooms'] == {'R1': ['X16', 'X18', 'X19'], 'R3': ['X15', 'X20']}, x['rooms'])


DEMO_CHECK = {ELEC: check_elec, PLMB: check_plmb, MECH: check_mech, LOWV: check_lowv}


def follow_check(name, ids):
    """Moving W1 1' west: the extension's data is unchanged, and the elements on W1 - and on W2,
    measured from W2's start J2, which moved - are placed 1' further west."""
    def check_(r, B):
        ensure(B['extensions'][name] == r['_a']['extensions'][name], 'the extension data changed')
        for eid in ids:
            ensure(moved(r['_a'], B, name, eid) == [-FT, 0, 0], (eid, moved(r['_a'], B, name, eid)))
    return check_


def shared_ops(name, ids):
    O(name, 'move-a-wall-and-watch-them-follow', f'The Phase 5 demo: the Kitchen\'s west wall W1 moved 1\' west, by an '
      f'applier that implements {name} and knows it. No element changes - every host is relative - and the result is '
      f'valid under {name}; the elements on W1 ({", ".join(ids)}) now derive placements 1\' further west.',
      ['1.2.1', 'FS-OPS-2.7.1', 'FS-OPS-4.2.1'], demo(), {'batch': [{'op': 'moveWall', 'wall': 'W1', 'by': "1'"}]},
      check=follow_check(name, ids))


# ============================================================================= FS_electrical

shared(ELEC)
E = lambda *a, **k: V(ELEC, *a, **k)    # noqa: E731
ELC = lambda d: ext(d, ELEC)['circuits']                                           # noqa: E731
ELK = lambda d, c: coll(d, ELEC, c)                                                # noqa: E731


def second_panel(d, **panel):
    ELK(d, 'panels')['X28'] = on_wall('W6', 'right', 5 * FT, 1200, box(0, -200, -400, 100, 200, 400),
                                      volts=[120, 240], rating=100, spaces=20, **panel,
                                      clearances={'working': env('workingSpace', box(0, -400, -1200, 1000, 400, 800))})


E('schema', 'receptacle-feature-unknown', '"ground" is not a receptacle feature.', ['1.3.1'],
  edit(lambda d: ELK(d, 'receptacles')['X2'].update(features=['ground'])), [('FS-ELEC-SCH-001', [])])
E('schema', 'circuit-without-breaker', 'A circuit always has a breaker.', ['1.3.1'],
  edit(lambda d: ELC(d)['C1'].pop('breaker')), [('FS-ELEC-SCH-001', [])])
E('schema', 'alarm-detects-nothing', 'An alarm detects at least one thing.', ['1.3.1'],
  edit(lambda d: ELK(d, 'alarms')['X23'].update(detects=[])), [('FS-ELEC-SCH-001', [])])
E('schema', 'circuit-four-poles', 'A breaker has one, two or three poles.', ['1.3.1'],
  edit(lambda d: ELC(d)['C3'].update(poles=4)), [('FS-ELEC-SCH-001', [])])
E('schema', 'collection-not-of-the-kind', 'FS_electrical has no collection "outlets": Core reports it first, as '
  'FS-INV-604 of a known extension (Core 12.4.1), and FS_electrical is not evaluated.', ['1.2.2'],
  edit(lambda d: ext(d, ELEC)['collections'].update(outlets={})), [('FS-INV-604', [])])

E('invariants', 'circuit-id-used-by-a-wall', 'A circuit called W1 - a wall\'s ID.', ['1.3.2'],
  edit(lambda d: ELC(d).update(W1=ELC(d).pop('C5'))), [('FS-ELEC-INV-001', ['W1'])])
E('invariants', 'circuit-id-used-by-an-element', 'A circuit called X2 - a receptacle\'s ID.', ['1.3.2'],
  edit(lambda d: ELC(d).update(X2=ELC(d).pop('C5'))), [('FS-ELEC-INV-001', ['X2'])])
E('invariants', 'circuit-panel-missing', 'C1 is on X99, which does not exist.', ['3.1.1'],
  edit(lambda d: ELC(d)['C1'].update(panel='X99')), [('FS-ELEC-INV-002', ['C1'])])
E('invariants', 'circuit-panel-not-a-panel', 'C1 is "on" the receptacle X2.', ['3.1.1'],
  edit(lambda d: ELC(d)['C1'].update(panel='X2')), [('FS-ELEC-INV-002', ['C1'])])
E('invariants', 'circuit-volts-not-the-panels', 'The water heater circuit at 208 V on a 120/240 V panel.', ['3.1.2'],
  edit(lambda d: ELC(d)['C3'].update(volts=208)), [('FS-ELEC-INV-007', ['C3', 'X1'])])
E('invariants', 'load-missing', 'C2 feeds X99, which does not exist, and the wall W2, which is no extension element: '
  'once for each.', ['3.2.1'], edit(lambda d: ELC(d)['C2']['loads'].extend(['X99', 'W2'])),
  [('FS-ELEC-INV-003', ['C2']), ('FS-ELEC-INV-003', ['C2'])])
E('invariants', 'load-is-a-switch', 'C4 lists the switch X21 among its loads.', ['3.2.2'],
  edit(lambda d: ELC(d)['C4']['loads'].append('X21')), [('FS-ELEC-INV-004', ['C4', 'X21'])])
E('invariants', 'load-is-a-panel', 'A subpanel X28 is listed as a load of C5, not fed through its fedBy.', ['3.2.2'],
  edit(lambda d: (second_panel(d), ELC(d)['C5']['loads'].append('X28'))), [('FS-ELEC-INV-004', ['C5', 'X28'])])
E('invariants', 'load-on-two-panels', 'The receptacle X2 is on C1 of the main panel and on C6 of a second panel.',
  ['3.2.3'], edit(lambda d: (second_panel(d), ELC(d).update(C6={'panel': 'X28', 'breaker': 20, 'volts': 120, 'space': 1, 'loads': ['X2']}))),
  [('FS-ELEC-INV-005', ['X2'])])
E('invariants', 'split-wired-receptacle', 'The receptacle X2 is a load of C1 and C2 of one panel - a split-wired '
  'kitchen receptacle - which is allowed.', ['3.2.3'], edit(lambda d: ELC(d)['C2']['loads'].append('X2')))
E('invariants', '240-volt-charger-on-a-120-volt-circuit', 'The 240 V EV charger on C5, made a 120 V circuit.', ['3.2.4'],
  edit(lambda d: ELC(d)['C5'].update(volts=120, poles=1)), [('FS-ELEC-INV-006', ['C5', 'X24'])])
E('invariants', '240-volt-receptacle-on-a-120-volt-circuit', 'A range receptacle (240 V) on the 120 V counter circuit.',
  ['3.2.4'], edit(lambda d: ELK(d, 'receptacles')['X3'].update(volts=240)), [('FS-ELEC-INV-006', ['C1', 'X3'])])
E('invariants', 'battery-alarm-on-a-circuit', 'The alarm X23 runs on battery alone, yet C4 lists it.', ['3.2.5'],
  edit(lambda d: ELK(d, 'alarms')['X23'].update(power='battery')), [('FS-ELEC-INV-013', ['C4', 'X23'])])
E('invariants', 'circuit-past-the-last-space', 'The 2-pole EV circuit at space 40 of a 40-space panel takes space 41.',
  ['3.3.1'], edit(lambda d: ELC(d)['C5'].update(space=40)), [('FS-ELEC-INV-008', ['C5', 'X1'])])
E('invariants', 'circuit-at-the-last-space', 'The 2-pole EV circuit at space 39 takes spaces 39 and 40: allowed.',
  ['3.3.1'], edit(lambda d: ELC(d)['C5'].update(space=39)))
E('invariants', 'circuits-share-a-space', 'C2 moved to space 1, which C1 takes; and the 2-pole C3 (spaces 3-4) '
  'overlaps C4 moved to space 4.', ['3.3.2'], edit(lambda d: (ELC(d)['C2'].update(space=1), ELC(d)['C4'].update(space=4))),
  [('FS-ELEC-INV-009', ['C1', 'C2']), ('FS-ELEC-INV-009', ['C3', 'C4'])])
E('invariants', 'fed-by-a-missing-circuit', 'The panel is fed by C9, which does not exist.', ['3.4.1'],
  edit(lambda d: ELK(d, 'panels')['X1'].update(fedBy='C9')), [('FS-ELEC-INV-011', ['X1'])])
E('invariants', 'fed-by-its-own-circuit', 'The main panel is fed by its own circuit C5.', ['3.4.2'],
  edit(lambda d: ELK(d, 'panels')['X1'].update(fedBy='C5')), [('FS-ELEC-INV-012', ['X1'])])
E('invariants', 'feeder-loop', 'X28 is fed by C6 on X1, and X1 by C7 on X28: each panel is on the loop.', ['3.4.2'],
  edit(lambda d: (second_panel(d, fedBy='C6'), ELK(d, 'panels')['X1'].update(fedBy='C7'),
                  ELC(d).update(C6={'panel': 'X1', 'breaker': 60, 'poles': 2, 'volts': 240, 'space': 8},
                                C7={'panel': 'X28', 'breaker': 60, 'poles': 2, 'volts': 240, 'space': 1}))),
  [('FS-ELEC-INV-012', ['X1']), ('FS-ELEC-INV-012', ['X28'])])
E('invariants', 'switch-controls-a-panel', 'X21 controls the light X22, the panel X1 and the wall W1: twice FS-ELEC-INV-010.',
  ['4.1.1'], edit(lambda d: ELK(d, 'switches')['X21']['controls'].extend(['X1', 'W1'])),
  [('FS-ELEC-INV-010', ['X21']), ('FS-ELEC-INV-010', ['X21'])])
E('invariants', 'switch-controls-a-receptacle', 'A switched receptacle: X21 controls X5 as well as the light.', ['4.1.1'],
  edit(lambda d: ELK(d, 'switches')['X21']['controls'].append('X5')))
E('invariants', 'not-evaluated-after-a-missing-panel', 'The water heater circuit C3\'s panel is missing; its 208 V and '
  'its spaces past the end are not evaluated against a panel (5.2): only FS-ELEC-INV-002.', ['5.2.1', '3.1.1'],
  edit(lambda d: ELC(d)['C3'].update(panel='X99', volts=208, space=40)), [('FS-ELEC-INV-002', ['C3'])])
E('invariants', 'not-evaluated-for-a-battery-alarm', 'A battery alarm at 24 V listed by C4: FS-ELEC-INV-013 only, not '
  'its voltage too.', ['5.2.1', '3.2.5'], edit(lambda d: ELK(d, 'alarms')['X23'].update(power='battery', volts=24)),
  [('FS-ELEC-INV-013', ['C4', 'X23'])])
E('invariants', 'not-evaluated-for-a-switch-load', 'A switch listed as a load of C1 and of a circuit of another panel: '
  'FS-ELEC-INV-004 twice, and no FS-ELEC-INV-005 - those circuits do not count.', ['5.2.1', '3.2.2'],
  edit(lambda d: (second_panel(d), ELC(d)['C1']['loads'].append('X21'),
                  ELC(d).update(C6={'panel': 'X28', 'breaker': 20, 'volts': 120, 'space': 1, 'loads': ['X21']}))),
  [('FS-ELEC-INV-004', ['C1', 'X21']), ('FS-ELEC-INV-004', ['C6', 'X21'])])

E('lints', 'receptacle-on-no-circuit', 'X5 is taken off C2: on no circuit.', ['1.2.3'],
  edit(lambda d: ELC(d)['C2'].update(loads=['X4'])), [('FS-ELEC-LINT-001', ['X5'])])
E('lints', 'battery-alarm-on-no-circuit', 'A battery alarm on no circuit is as it should be: no lint.', ['1.2.3'],
  edit(lambda d: (ELK(d, 'alarms')['X23'].update(power='battery'), ELC(d)['C4']['loads'].remove('X23'))))
E('lints', 'light-no-switch-controls', 'No switch controls the kitchen light.', ['1.2.3'],
  edit(lambda d: ELK(d, 'switches')['X21'].update(controls=[])), [('FS-ELEC-LINT-002', ['X22'])])
E('lints', 'breaker-above-rating', 'A 30 A breaker on 20 A conductors.', ['1.2.3'],
  edit(lambda d: ELC(d)['C1'].update(breaker=30)), [('FS-ELEC-LINT-003', ['C1'])])
E('lints', 'connected-load-above-capacity', 'A 1,500 W and a 1,000 W appliance on C1: 2,500 W on a 2,400 W circuit.',
  ['1.2.3'], edit(lambda d: (ELK(d, 'receptacles')['X2'].update(watts=1500), ELK(d, 'receptacles')['X3'].update(watts=1000))),
  [('FS-ELEC-LINT-004', ['C1'])],
  check=lambda r: ensure(r['derived']['extensions'][ELEC]['circuits']['C1']['connectedLoad'] == 2500
                         and r['derived']['extensions'][ELEC]['panels']['X1']['connectedLoad'] == 2512, r))
E('lints', 'connected-load-at-capacity', '2,400 W on a 2,400 W circuit: at capacity, not above it.', ['1.2.3'],
  edit(lambda d: ELK(d, 'receptacles')['X2'].update(watts=2400)))
E('lints', 'circuit-with-no-loads', 'A spare circuit C6 at space 10 feeds nothing.', ['1.2.3'],
  edit(lambda d: ELC(d).update(C6={'panel': 'X1', 'breaker': 20, 'volts': 120, 'space': 10})), [('FS-ELEC-LINT-005', ['C6'])])
E('lints', 'panel-without-working-space', 'The panel has no clearance envelope of purpose workingSpace (2.7).',
  ['1.2.3'], edit(lambda d: ELK(d, 'panels')['X1'].pop('clearances')), [('FS-ELEC-LINT-006', ['X1'])])
E('lints', 'charger-above-breaker', 'A 48 A charger on a 40 A breaker.', ['1.2.3'],
  edit(lambda d: ELK(d, 'evChargers')['X24'].update(amps=48)), [('FS-ELEC-LINT-007', ['C5', 'X24'])])

E('derived', 'subpanel', 'A subpanel X28 in the Utility room, fed by the 60 A, 2-pole C6 on the main panel, with one '
  'circuit C7 for the bath receptacle X29: each panel lists its own circuits and spaces; C6 feeds nothing directly.',
  ['6.1.1', '3.4.1', '3.4.2'],
  edit(lambda d: (second_panel(d, fedBy='C6'),
                  ELK(d, 'receptacles').update(X29=on_wall('W10', 'left', 4 * FT, 1100, PLATE, amps=20, features=['gfci'], watts=1800)),
                  ELC(d).update(C6={'panel': 'X1', 'breaker': 60, 'poles': 2, 'volts': 240, 'rating': 60, 'space': 8},
                                C7={'panel': 'X28', 'breaker': 20, 'volts': 120, 'space': 1, 'loads': ['X29']}))),
  [('FS-ELEC-LINT-005', ['C6'])],
  check=lambda r: ensure(r['derived']['extensions'][ELEC]['panels'] == {
      'X1': {'circuits': ['C1', 'C2', 'C3', 'C4', 'C5', 'C6'], 'spacesUsed': 9, 'connectedLoad': 12},
      'X28': {'circuits': ['C7'], 'spacesUsed': 1, 'connectedLoad': 1800}}
      and r['derived']['extensions'][ELEC]['rooms']['R2'] == ['X26', 'X29']
      and r['derived']['extensions'][ELEC]['rooms']['R3'] == ['X1', 'X28'], r['derived']['extensions'][ELEC]))
E('derived', 'rooms-of-free-and-unhosted-elements', 'A floor lamp standing free in the Kitchen is in the Kitchen; one '
  'standing free outside the house, and an alarm with no host, are in no room.', ['6.1.1'],
  edit(lambda d: (ELK(d, 'lights').update(
      X30={'fallback': {'level': 'L1', 'box': box(-200, -200, 0, 200, 200, 1600)},
           'host': {'mode': 'free', 'level': 'L1', 'position': [2 * FT, 2 * FT]}, 'fixture': 'wall'},
      X31={'fallback': {'level': 'L1', 'box': box(-200, -200, 0, 200, 200, 1600)},
           'host': {'mode': 'free', 'level': 'L1', 'position': [-4 * FT, 2 * FT]}, 'fixture': 'exterior'}),
      ELK(d, 'alarms').update(X32={'fallback': {'level': 'L1', 'box': box(0, 0, 0, 100, 100, 50)}, 'detects': ['heat'],
                                   'power': 'battery'}),
      ELK(d, 'switches')['X21']['controls'].extend(['X30', 'X31']), ELC(d)['C4']['loads'].extend(['X30', 'X31']))),
  check=lambda r: ensure(r['derived']['extensions'][ELEC]['rooms']['R1'] == ['X2', 'X21', 'X22', 'X23', 'X3', 'X30', 'X4', 'X5']
                         and 'X31' not in sum(r['derived']['extensions'][ELEC]['rooms'].values(), [])
                         and 'X32' not in sum(r['derived']['extensions'][ELEC]['rooms'].values(), []), r['derived']['extensions'][ELEC]))

shared_ops(ELEC, ['X5', 'X2', 'X3'])
O(ELEC, 'remove-a-load-is-rejected', 'Removing the receptacle X5 leaves C2 naming it: the result breaks 3.2.1, and an '
  'applier that implements FS_electrical and knows it rejects the batch (Ops 1.2.3) with FS-ELEC-INV-003.',
  ['3.2.1', '1.2.1', 'FS-OPS-1.2.3'], demo(), {'batch': [{'op': 'removeElement', 'id': 'X5'}]}, 'rejected',
  [('FS-ELEC-INV-003', ['C2'])])
O(ELEC, 'remove-a-load-and-its-reference', 'The same removal, with C2\'s loads set without X5 in the same batch: it '
  'commits.', ['3.2.1', '1.2.1'], demo(),
  {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_electrical/circuits/C2/loads', 'value': ['X4']},
             {'op': 'removeElement', 'id': 'X5'}]},
  check=lambda r, B: ensure(r['removed'] == ['X5'], r['removed']))

# ============================================================================= FS_plumbing

shared(PLMB)
P = lambda *a, **k: V(PLMB, *a, **k)    # noqa: E731
PLK = lambda d, c: coll(d, PLMB, c)                                                # noqa: E731
STK = lambda d: ext(d, PLMB)['stacks']                                             # noqa: E731

P('schema', 'fixture-kind-unknown', '"toilet" is not a fixture of 2.1 ("waterCloset" is).', ['1.3.1'],
  edit(lambda d: PLK(d, 'fixtures')['X6'].update(fixture='toilet')), [('FS-PLMB-SCH-001', [])])
P('schema', 'stack-without-levels', 'A stack passes through at least one level.', ['1.3.1'],
  edit(lambda d: STK(d)['K1'].update(levels=[])), [('FS-PLMB-SCH-001', [])])
P('schema', 'water-heater-without-energy', 'A water heater always says what it runs on.', ['1.3.1'],
  edit(lambda d: PLK(d, 'waterHeaters')['X8'].pop('energy')), [('FS-PLMB-SCH-001', [])])

P('invariants', 'stack-id-used-by-a-room', 'A stack called R1 - a room\'s ID.', ['1.3.2'],
  edit(lambda d: (STK(d).update(R1=STK(d).pop('K1')), [el.update(drain='R1') for c in ('fixtures', 'drains') for el in PLK(d, c).values() if el.get('drain') == 'K1'],
                  PLK(d, 'cleanouts')['X27'].update(stack='R1'))),
  [('FS-PLMB-INV-001', ['R1'])])
P('invariants', 'drains-to-a-fixture', 'The toilet drains to the hose bibb X25, which is neither a stack nor a drain.',
  ['3.1.2'], edit(lambda d: PLK(d, 'fixtures')['X6'].update(drain='X25')), [('FS-PLMB-INV-002', ['X6'])])
P('invariants', 'drain-drains-to-a-drain', 'The floor drain X9 drains to a second floor drain: a drain drains only to a '
  'stack.', ['3.1.2'], edit(lambda d: (PLK(d, 'drains').update(X28=on_surface('R3', 'floor', 17 * FT, 4 * FT, box(-75, -75, -10, 75, 75, 0), receptor='floor', drain='K1')),
                                         PLK(d, 'drains')['X9'].update(drain='X28'))), [('FS-PLMB-INV-002', ['X9'])])
P('invariants', 'drains-to-a-vent-stack', 'The toilet drains to K2, a vent stack.', ['3.1.3'],
  edit(lambda d: (STK(d).update(K2={'stack': 'vent', 'levels': ['L1']}), PLK(d, 'fixtures')['X6'].update(drain='K2'))),
  [('FS-PLMB-INV-003', ['K2', 'X6'])])
P('invariants', 'stack-not-on-the-level', 'K1 passes through L2 only: the toilet, the lavatory and the floor drain that '
  'drain to it, and its cleanout, are all on L1.', ['3.1.4'],
  edit(lambda d: (d['levels'].update(L2={'building': 'B1', 'elevation': H, 'height': H}), STK(d)['K1'].update(levels=['L2']))),
  [('FS-PLMB-INV-004', ['K1', 'X6']), ('FS-PLMB-INV-004', ['K1', 'X7']), ('FS-PLMB-INV-004', ['K1', 'X9']),
   ('FS-PLMB-INV-004', ['K1', 'X27'])])
P('invariants', 'hot-from-a-fixture', 'The lavatory\'s hot water comes from the toilet.', ['3.2.1'],
  edit(lambda d: PLK(d, 'fixtures')['X7'].update(hotFrom='X6')), [('FS-PLMB-INV-005', ['X7'])])
P('invariants', 'stack-on-a-missing-level', 'K1 passes through L1 and L9, which does not exist.', ['3.1.1'],
  edit(lambda d: STK(d)['K1'].update(levels=['L1', 'L9'])), [('FS-PLMB-INV-006', ['K1'])])
P('invariants', 'cleanout-on-a-missing-stack', 'The cleanout opens K9, which does not exist.', ['3.1.5'],
  edit(lambda d: PLK(d, 'cleanouts')['X27'].update(stack='K9')), [('FS-PLMB-INV-007', ['X27'])])
P('invariants', 'hot-from-without-hot-supply', 'The lavatory has a hot-water source but is supplied cold only.', ['3.2.2'],
  edit(lambda d: PLK(d, 'fixtures')['X7'].update(supply=['cold'])), [('FS-PLMB-INV-008', ['X7'])])
P('invariants', 'electric-heater-with-combustion-air', 'An electric water heater has no combustion air.', ['2.2.1'],
  edit(lambda d: PLK(d, 'waterHeaters')['X8'].update(combustionAir='indoor')), [('FS-PLMB-INV-009', ['X8'])])
P('invariants', 'gas-heater-with-combustion-air', 'A natural-gas water heater with direct combustion air: valid.', ['2.2.1'],
  edit(lambda d: PLK(d, 'waterHeaters')['X8'].update(energy='naturalGas', combustionAir='direct')))
P('invariants', 'not-evaluated-for-a-vent-stack', 'The toilet drains to a vent stack on L2 only: FS-PLMB-INV-003, and '
  'not FS-PLMB-INV-004 (4.2).', ['4.2.1', '3.1.3'],
  edit(lambda d: (d['levels'].update(L2={'building': 'B1', 'elevation': H, 'height': H}),
                  STK(d).update(K2={'stack': 'vent', 'levels': ['L2']}), PLK(d, 'fixtures')['X6'].update(drain='K2'))),
  [('FS-PLMB-INV-003', ['K2', 'X6'])])
P('invariants', 'not-evaluated-after-a-bad-hot-from', 'The lavatory\'s hotFrom is the toilet and its supply is cold: '
  'FS-PLMB-INV-005 only.', ['4.2.1', '3.2.1'],
  edit(lambda d: PLK(d, 'fixtures')['X7'].update(hotFrom='X6', supply=['cold'])), [('FS-PLMB-INV-005', ['X7'])])

P('lints', 'fixture-drains-nowhere', 'The toilet drains to nothing.', ['1.2.3'],
  edit(lambda d: PLK(d, 'fixtures')['X6'].pop('drain')), [('FS-PLMB-LINT-001', ['X6'])])
P('lints', 'gas-heater-without-combustion-air', 'A propane water heater that does not say where its combustion air '
  'comes from.', ['1.2.3'], edit(lambda d: PLK(d, 'waterHeaters')['X8'].update(energy='propane')),
  [('FS-PLMB-LINT-002', ['X8'])])
P('lints', 'stack-nothing-drains-to', 'A second stack K2 that nothing drains to.', ['1.2.3'],
  edit(lambda d: STK(d).update(K2={'levels': ['L1']})), [('FS-PLMB-LINT-003', ['K2'])])
P('lints', 'missing-default-envelopes', 'The toilet without its fixtureClearance, the water heater and the cleanout '
  'without their access envelopes.', ['1.2.3'],
  edit(lambda d: [PLK(d, c)[x].pop('clearances') for c, x in (('fixtures', 'X6'), ('waterHeaters', 'X8'), ('cleanouts', 'X27'))]),
  [('FS-PLMB-LINT-004', ['X6']), ('FS-PLMB-LINT-004', ['X8']), ('FS-PLMB-LINT-004', ['X27'])])
P('lints', 'hot-supply-from-nowhere', 'The lavatory is supplied hot water but names no water heater.', ['1.2.3'],
  edit(lambda d: PLK(d, 'fixtures')['X7'].pop('hotFrom')), [('FS-PLMB-LINT-005', ['X7'])],
  check=lambda r: ensure(r['derived']['extensions'][PLMB]['waterHeaters'] == {'X8': {'fixtures': []}}, r))

P('derived', 'connected-through-a-drain', 'A clothes washer X28 in the Utility room drains to the floor drain X9, '
  'which drains to K1: the washer is connected to K1 through it.', ['5.1.1'],
  edit(lambda d: PLK(d, 'fixtures').update(X28=on_surface('R3', 'floor', 13 * FT + 6 * 32512, 4 * FT, box(-300, -300, 0, 300, 300, 900),
                                                          fixture='clothesWasher', supply=['cold', 'hot'], hotFrom='X8', drain='X9'))),
  check=lambda r: ensure(r['derived']['extensions'][PLMB]['stacks']['K1']['connected'] == ['X28', 'X6', 'X7', 'X8', 'X9']
                         and r['derived']['extensions'][PLMB]['waterHeaters']['X8']['fixtures'] == ['X28', 'X7'], r))

shared_ops(PLMB, ['X25'])

# ============================================================================= FS_mechanical

shared(MECH)
M = lambda *a, **k: V(MECH, *a, **k)    # noqa: E731
MCK = lambda d, c: coll(d, MECH, c)                                                # noqa: E731
GAS = lambda d: ext(d, MECH)['gasSources']                                         # noqa: E731
HEAT_PUMP = lambda **kw: on_surface('R3', 'floor', 14 * FT, 4 * FT, box(-200, -200, 0, 200, 200, 900), equipment='heatPump', **kw)  # noqa: E731

M('schema', 'equipment-kind-unknown', '"stove" is not equipment of 2.1.', ['1.3.1'],
  edit(lambda d: MCK(d, 'equipment')['X10'].update(equipment='stove')), [('FS-MECH-SCH-001', [])])
M('schema', 'gas-appliance-burns-oil', 'A gas appliance burns natural gas or propane.', ['1.3.1'],
  edit(lambda d: MCK(d, 'gasAppliances')['X14'].update(fuel='oil')), [('FS-MECH-SCH-001', [])])
M('schema', 'terminal-without-terminal', 'A terminal always says what it does.', ['1.3.1'],
  edit(lambda d: MCK(d, 'terminals')['X11'].pop('terminal')), [('FS-MECH-SCH-001', [])])
M('schema', 'airflow-zero', 'An air flow is at least 1 mL/s.', ['1.3.1'],
  edit(lambda d: MCK(d, 'terminals')['X11'].update(airflow=0)), [('FS-MECH-SCH-001', [])])

M('invariants', 'gas-source-id-used-by-a-level', 'A gas source called L1 - a level\'s ID.', ['1.3.2'],
  edit(lambda d: (GAS(d).update(L1=GAS(d).pop('G1')), MCK(d, 'equipment')['X10'].update(gasFrom='L1'),
                  MCK(d, 'gasAppliances')['X14'].update(gasFrom='L1'))), [('FS-MECH-INV-001', ['L1'])])
M('invariants', 'gas-from-a-missing-source', 'The range draws from G9, which does not exist.', ['3.1.1'],
  edit(lambda d: MCK(d, 'gasAppliances')['X14'].update(gasFrom='G9')), [('FS-MECH-INV-002', ['X14'])])
M('invariants', 'propane-range-on-a-natural-gas-meter', 'A propane range on the natural gas meter.', ['3.1.2'],
  edit(lambda d: MCK(d, 'gasAppliances')['X14'].update(fuel='propane')), [('FS-MECH-INV-003', ['G1', 'X14'])])
M('invariants', 'electric-equipment-on-a-meter', 'An electric heat pump that draws from the gas meter.', ['3.1.2'],
  edit(lambda d: MCK(d, 'equipment').update(X28=HEAT_PUMP(gasFrom='G1'))), [('FS-MECH-INV-003', ['G1', 'X28'])])
M('invariants', 'terminal-served-by-a-range', 'The supply register is served by the range.', ['3.2.1'],
  edit(lambda d: MCK(d, 'terminals')['X11'].update(equipment='X14')), [('FS-MECH-INV-004', ['X11'])])
M('invariants', 'electric-equipment-with-a-vent', 'An electric heat pump with a power vent.', ['2.1.1'],
  edit(lambda d: MCK(d, 'equipment').update(X28=HEAT_PUMP(vent='power'))), [('FS-MECH-INV-005', ['X28'])])
M('invariants', 'electric-equipment-with-combustion-air', 'An electric heat pump with indoor combustion air.', ['2.1.1'],
  edit(lambda d: MCK(d, 'equipment').update(X28=HEAT_PUMP(combustionAir='indoor'))), [('FS-MECH-INV-005', ['X28'])])
M('invariants', 'not-evaluated-after-a-missing-source', 'A propane range drawing from a missing source: '
  'FS-MECH-INV-002 only.', ['4.2.1', '3.1.1'],
  edit(lambda d: MCK(d, 'gasAppliances')['X14'].update(gasFrom='G9', fuel='propane')), [('FS-MECH-INV-002', ['X14'])])

M('lints', 'burner-without-combustion-air', 'The range does not say where its combustion air comes from.', ['1.2.3'],
  edit(lambda d: MCK(d, 'gasAppliances')['X14'].pop('combustionAir')), [('FS-MECH-LINT-001', ['X14'])])
M('lints', 'gas-furnace-without-a-source', 'The furnace burns natural gas from nowhere.', ['1.2.3'],
  edit(lambda d: MCK(d, 'equipment')['X10'].pop('gasFrom')), [('FS-MECH-LINT-002', ['X10'])])
M('lints', 'terminals-without-equipment', 'The supply register names no equipment; a transfer grille X28 does not '
  'need to.', ['1.2.3'],
  edit(lambda d: (MCK(d, 'terminals')['X11'].pop('equipment'),
                  MCK(d, 'terminals').update(X28=on_wall('W10', 'left', 2 * FT, 2300, box(0, -200, -100, 20, 200, 100), terminal='transfer')))),
  [('FS-MECH-LINT-003', ['X11'])])
M('lints', 'furnace-without-working-space', 'The furnace has no workingSpace envelope (2.5).', ['1.2.3'],
  edit(lambda d: MCK(d, 'equipment')['X10'].pop('clearances')), [('FS-MECH-LINT-004', ['X10'])])
M('lints', 'unused-gas-source', 'A propane tank G2 nothing draws from.', ['1.2.3'],
  edit(lambda d: GAS(d).update(G2={'fuel': 'propane', 'source': 'tank'})), [('FS-MECH-LINT-005', ['G2'])],
  check=lambda r: ensure(r['derived']['extensions'][MECH]['gasSources']['G2'] == {'fuel': 'propane', 'appliances': [], 'input': 0}, r))

M('derived', 'equipment-without-terminals', 'A heat pump with no terminals derives no terminals and no air flow; an '
  'appliance without an input adds nothing to its source\'s.', ['5.1.1'],
  edit(lambda d: (MCK(d, 'equipment').update(X28=HEAT_PUMP()), MCK(d, 'gasAppliances')['X14'].pop('input'))),
  check=lambda r: ensure(r['derived']['extensions'][MECH]['equipment']['X28'] == {'terminals': [], 'airflow': 0}
                         and r['derived']['extensions'][MECH]['gasSources']['G1']['input'] == 17600, r))

shared_ops(MECH, ['X12'])

# ============================================================================= FS_lowvoltage

shared(LOWV)
L = lambda *a, **k: V(LOWV, *a, **k)    # noqa: E731
LVK = lambda d, c: coll(d, LOWV, c)                                                # noqa: E731

L('schema', 'outlet-with-no-media', 'An outlet carries at least one medium.', ['1.3.1'],
  edit(lambda d: LVK(d, 'outlets')['X16'].update(media=[])), [('FS-LOWV-SCH-001', [])])
L('schema', 'head-end-serves-power', '"power" is not a system a head-end serves.', ['1.3.1'],
  edit(lambda d: LVK(d, 'headEnds')['X15']['serves'].append('power')), [('FS-LOWV-SCH-001', [])])
L('schema', 'own-data-beside-collections', 'FS_lowvoltage has no top-level member but collections.', ['1.3.1'],
  edit(lambda d: ext(d, LOWV).update(runs={})), [('FS-LOWV-SCH-001', [])])

L('invariants', 'run-to-a-panel', 'The data outlet is run to X1, the electrical panel - not a head-end.', ['3.1.1'],
  edit(lambda d: LVK(d, 'outlets')['X16'].update(headEnd='X1')), [('FS-LOWV-INV-001', ['X16'])])
L('invariants', 'run-to-a-head-end-that-does-not-serve-it', 'The enclosure no longer terminates audio, so the speaker '
  'run to it is a contradiction.', ['3.1.2'],
  edit(lambda d: LVK(d, 'headEnds')['X15']['serves'].remove('audio')), [('FS-LOWV-INV-003', ['X15', 'X19'])])
L('invariants', 'outlet-medium-not-served', 'The enclosure terminates data but not coax, and the outlet carries both.',
  ['3.1.2'], edit(lambda d: LVK(d, 'headEnds')['X15']['serves'].remove('coax')), [('FS-LOWV-INV-003', ['X15', 'X16'])])
L('invariants', 'button-rings-an-outlet', 'The doorbell button rings the data outlet.', ['3.2.1'],
  edit(lambda d: LVK(d, 'doorbells')['X17'].update(chime='X16')), [('FS-LOWV-INV-002', ['X17'])])
L('invariants', 'button-rings-a-button', 'A second button rings the first.', ['3.2.1'],
  edit(lambda d: LVK(d, 'doorbells').update(X28=on_wall('W1', 'left', 9 * FT, 1200, box(0, -20, -40, 20, 20, 40), part='button', chime='X17'))),
  [('FS-LOWV-INV-002', ['X28'])])
L('invariants', 'chime-with-a-chime', 'A chime that names a chime.', ['3.2.1'],
  edit(lambda d: LVK(d, 'doorbells')['X18'].update(chime='X18')), [('FS-LOWV-INV-002', ['X18'])])
L('invariants', 'not-evaluated-after-a-missing-head-end', 'The speaker is run to X99, which does not exist: '
  'FS-LOWV-INV-001 only.', ['4.2.1', '3.1.1'], edit(lambda d: LVK(d, 'speakers')['X19'].update(headEnd='X99')),
  [('FS-LOWV-INV-001', ['X19'])])

L('lints', 'outlet-run-nowhere', 'The data outlet is run to no head-end; a wireless contact X28 need not be.', ['1.2.3'],
  edit(lambda d: (LVK(d, 'outlets')['X16'].pop('headEnd'),
                  LVK(d, 'security').update(X28=on_wall('W7', 'right', 2 * FT, 2000, box(0, -20, -40, 20, 20, 40), device='contact', wireless=True)))),
  [('FS-LOWV-LINT-001', ['X16'])])
L('lints', 'button-rings-nothing', 'The doorbell button rings no chime.', ['1.2.3'],
  edit(lambda d: LVK(d, 'doorbells')['X17'].pop('chime')), [('FS-LOWV-LINT-002', ['X17'])])
L('lints', 'head-end-without-access', 'The enclosure has no access envelope (2.6).', ['1.2.3'],
  edit(lambda d: LVK(d, 'headEnds')['X15'].pop('clearances')), [('FS-LOWV-LINT-003', ['X15'])])

L('derived', 'ports-by-medium', 'A second outlet X28 with four data ports, run to the enclosure: data ports add up.',
  ['5.1.1'], edit(lambda d: LVK(d, 'outlets').update(X28=on_wall('W2', 'right', 4 * FT, 300, PLATE, media=['data'], ports=4, headEnd='X15'))),
  check=lambda r: ensure(r['derived']['extensions'][LOWV]['headEnds']['X15']['ports'] == {'coax': 2, 'data': 6}, r))

shared_ops(LOWV, ['X16'])


# ============================================================================= write

def suite_dir(name):
    return os.path.join(REPO, 'conformance', 'ext', name, '0.1.0')


def write_all(prune=False):
    counters, failures, seen = {}, 0, set()
    for tc in TESTS:
        key = (tc['ext'], tc['group'])
        counters[key] = counters.get(key, 0) + 1
        d = os.path.join(suite_dir(tc['ext']), tc['group'], f"{counters[key]:03d}-{tc['slug']}")
        seen.add(d)
        os.makedirs(d, exist_ok=True)
        data = tc['raw'] if tc.get('raw') is not None else (fmt(tc['doc']) + '\n').encode('utf-8')
        with open(os.path.join(d, 'input.json'), 'wb') as f:
            f.write(data)
        with open(os.path.join(d, 'test.json'), 'w') as f:
            f.write(json.dumps({'description': tc['description'], 'covers': tc['covers']}, indent=2, ensure_ascii=False) + '\n')
        registry = None if tc['registry'] is None else (fmt(tc['registry']) + '\n').encode('utf-8')
        rp = os.path.join(d, 'registry.json')
        if registry is not None:
            with open(rp, 'wb') as f:
                f.write(registry)
        elif os.path.exists(rp):
            os.remove(rp)
        implemented = official.implemented(tc['ext'])
        hand = sorted(tc['diags'], key=lambda x: (x['code'], x['elements']))
        problems = []
        if tc['kind'] == 'core':
            result, canonical, notes = check(data, READER_02, registry, implemented)
            valid = not any(x['severity'] == 'error' for x in hand)
            if hand != result['diagnostics'] or valid != result['valid']:
                problems.append(f'hand   {json.dumps(hand)}\n  oracle {json.dumps(result["diagnostics"])}'
                                + ''.join(f'\n  note {n}' for n in notes[:5]))
            elif tc['check'] is not None:
                try:
                    tc['check'](result)
                except Exception as e:                      # noqa: BLE001
                    problems.append(f'hand-written check failed: {type(e).__name__}: {e}')
            exp = {'valid': valid, 'diagnostics': hand}
            if 'hash' in result:
                exp['hash'], exp['derived'] = result['hash'], result['derived']
            with open(os.path.join(d, 'expected.json'), 'w') as f:
                f.write(dumps(exp))
            cp = os.path.join(d, 'canonical.json')
            if canonical is not None:
                with open(cp, 'wb') as f:
                    f.write(canonical)
            elif os.path.exists(cp):
                os.remove(cp)
        else:
            profile = OPS_02.configured(registry, implemented)
            r = (fmt(tc['request']) + '\n').encode('utf-8')
            with open(os.path.join(d, 'request.json'), 'wb') as f:
                f.write(r)
            result, b = apply(data, r, profile)
            view = expected_view(result)
            if view['status'] != tc['status'] or view['diagnostics'] != hand:
                problems.append(f'hand   {tc["status"]} {json.dumps(hand)}\n  oracle {view["status"]} {json.dumps(result["diagnostics"])}')
            if tc['check'] is not None and b is not None:
                try:
                    tc['check']({**result, '_a': parse(data)[0]}, parse(b)[0])
                except Exception as e:                      # noqa: BLE001
                    problems.append(f'hand-written check failed: {type(e).__name__}: {e}')
            if b is not None:
                problems.extend(properties(data, r, result, b, profile))
            exp = {'status': tc['status'], 'diagnostics': hand}
            for k in ('hash', 'created', 'removed', 'resolved', 'inverse'):
                if k in view:
                    exp[k] = view[k]
            with open(os.path.join(d, 'expected.json'), 'w') as f:
                f.write(ops_dumps(exp))
            out = os.path.join(d, 'output.json')
            if b is not None:
                with open(out, 'wb') as f:
                    f.write(b)
            elif os.path.exists(out):
                os.remove(out)
        if problems:
            failures += 1
            print(f'MISMATCH {os.path.relpath(d, REPO)}')
            for p in problems:
                print('  ' + p)
    if prune:
        for name in EXTS:
            base = suite_dir(name)
            for g in sorted(os.listdir(base)) if os.path.isdir(base) else []:
                for n in sorted(os.listdir(os.path.join(base, g))):
                    if os.path.join(base, g, n) not in seen:
                        print('removing', os.path.join(base, g, n))
                        shutil.rmtree(os.path.join(base, g, n))
    print(f'{len(TESTS)} tests, {failures} mismatches')
    return failures


if __name__ == '__main__':
    sys.exit(1 if write_all(prune='--prune' in sys.argv) else 0)

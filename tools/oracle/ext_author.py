"""The conformance suites of the official extensions - FS_electrical, FS_plumbing, FS_mechanical,
FS_lowvoltage, FS_furniture and FS_structural 0.1.0 - as the script that writes them.

    python3.13 -m tools.oracle.ext_author            rewrite every test from its declaration below
    python3.13 -m tools.oracle.ext_author --prune    ...and delete test directories no longer declared

Each suite is conformance/ext/<NAME>/0.1.0/, run by an implementation of that one extension (a reader
of the Core draft each document declares - 0.2, or 0.3 for a document declaring "0.3" - that implements
<NAME> 0.1.0 and no other extension), configured with the test's
registry.json as its known extensions, or with none when the test has no registry.json. Most tests
are validator and deriver tests, laid out as Core's (input.json, registry.json, expected.json,
canonical.json; expected.json's `derived` has an `extensions` member; a test run by a package
validator has a package/ directory, and one that derives another design than the primary a
design.json, as Core's do); the tests in `ops` are Ops tests (input.json, request.json,
registry.json, expected.json, output.json), applied as Ops 0.2 - Ops 0.3 for a document declaring
"0.3" - by an applier whose validator is that implementation.

Almost every test starts from one document: the Phase 5 demo house (demo() below) - a kitchen, a
bath and a utility room with a panel, kitchen receptacles on two 20 A circuits, a toilet, a wall-hung
lavatory, an electric water heater on a 240 V circuit, a gas furnace and range on a meter, a bath
fan a switch controls, and data, doorbell, speaker and security devices run to a structured media
enclosure - and breaks one rule of it. FS_furniture's start from its own: the Phase 8 demo flat
(flat() below) - a kitchen with a refrigerator, a range, a dishwasher, cabinets and a dining table
with its chairs, a bedroom with a bed, a nightstand and a wardrobe, and a laundry with a washer and a
dryer - every item from the starter library (registry/FS_furniture/library/), its model and symbol
the library's own files. FS_structural's start from the Phase 10 framed house (framed() below) - the
demo house's plan with bearing and shear walls, studs, headers, floor joists, a slab on grade and a
deck, recorded on the walls, openings, rooms and slab themselves, since FS_structural adds no kind
of element. Every expected diagnostic is written by hand and cross-checked against the
oracle; the derived values that matter are asserted by hand in `check`.
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
from tools.oracle.ops.version import OPS_02, OPS_03
from tools.oracle.report import dumps
from tools.oracle.validate import SEVERITY, check, ext_reader

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
MM, FT = 1280, 390144
H = 2700 * MM
ELEC, PLMB, MECH, LOWV, FURN = 'FS_electrical', 'FS_plumbing', 'FS_mechanical', 'FS_lowvoltage', 'FS_furniture'
EXTS = (ELEC, PLMB, MECH, LOWV)          # the building systems of the Phase 5 demo house
ALL = EXTS + (FURN,)                      # every official extension, each with a suite
CODE = {ELEC: 'ELEC', PLMB: 'PLMB', MECH: 'MECH', LOWV: 'LOWV', FURN: 'FURN'}
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


def hand(diags):
    """Hand-written diagnostics: (code, elements) or (code, elements, design) (Core 0.3, 19.5.2)."""
    out = []
    for c, e, *design in diags:
        x = {'code': c, 'severity': SEV.get(c, 'error'), 'elements': sorted(set(e))}
        if design:
            x['design'] = design[0]
        out.append(x)
    return out


def V(name, group, slug, description, covers, doc, diags=(), registry=KNOWN, check=None, raw=None, package=None,
      design=None):
    """A validator and deriver test. registry: KNOWN (the extension's own entry), None (no known
    extensions) or a list of entries. package: the files of the document's package, {path: bytes},
    for a package validator (Core 0.3, 18.4). design: the design to derive (Core 0.3, 19.6), written
    as design.json. check(result) is a hand-written assertion."""
    TESTS.append(dict(kind='core', ext=name, group=group, slug=slug, description=description, covers=cov(name, covers),
                      doc=doc, raw=raw, registry=[entry(name)] if registry is KNOWN else registry, check=check,
                      package=package, design=design, diags=hand(diags)))


def O(name, slug, description, covers, a, request, status='committed', diags=(), check=None):
    """An Ops test - Ops 0.2, or Ops 0.3 for a document declaring "0.3" - applied by an applier that
    implements the extension and knows it."""
    TESTS.append(dict(kind='ops', ext=name, group='ops', slug=slug, description=description, covers=cov(name, covers),
                      doc=a, request=request, registry=[entry(name)], status=status, check=check, diags=hand(diags)))


def ops_profile(doc):
    """The Ops draft an extension suite's Ops test is applied as: Ops 0.3 for a document declaring "0.3"."""
    return OPS_03 if isinstance(doc, dict) and doc.get('floorspec') == '0.3' else OPS_02


def ensure(cond, what):
    if not cond:
        raise AssertionError(what)


def derived_of(name):
    return lambda r: r['derived']['extensions'][name]


def placements(d, name):
    """What an implementation of `name` that knows it derives as placements, for a check."""
    data = json.dumps(d).encode('utf-8')
    result, _, _ = check(data, ext_reader(data), json.dumps([entry(name)]).encode('utf-8'),
                         official.implemented(name))
    assert result['valid'], result['diagnostics']
    return result['derived']['placements']


def same_as_02(name):
    """A check: what the run derives for the extension is what it derives for its demo declaring "0.2"."""
    def check_(r):
        data = json.dumps(BASE[name]()).encode('utf-8')
        r02, _, _ = check(data, ext_reader(data), json.dumps([entry(name)]).encode('utf-8'), official.implemented(name))
        ensure(r['derived']['extensions'] == r02['derived']['extensions'] and list(r['derived']['extensions']) == [name],
               r['derived']['extensions'])
    return check_


def moved(a, b, name, eid):
    pa, pb = placements(a, name)[eid]['point'], placements(b, name)[eid]['point']
    return [pb[i] - pa[i] for i in range(3)]


# ============================================================================= every suite: the shared tests

def shared(name):
    code = CODE[name]
    T = lambda *a, **k: V(name, *a, **k)    # noqa: E731
    base = BASE[name]

    def ed(fn):
        d = base()
        fn(d)
        return d
    slug, text = EXAMPLE[name]
    T('examples', slug, text, ['1.2.1', '1.2.3', '1.2.4', '1.3.1', DERIVE[name]], base(), check=DEMO_CHECK[name])
    T('examples', 'core-only-reader', f'The same house read with no known extensions: {name} is not evaluated, so '
      'nothing of it is derived (`derived.extensions` is empty) - only what Core derives from every extension '
      'element\'s fallback, host and clearances (Core 1.6.9): their fallbacks, placements and clearances.',
      ['1.2.1', '1.2.4', 'FS-CORE-1.6.9', 'FS-CORE-12.6.2', 'FS-CORE-13.4.1', 'FS-CORE-13.5.2'], base(), registry=None,
      check=CORE_ONLY_CHECK[name])
    if name in EXTS:
        T('examples', 'all-four-known', f'The house read with all four official entries known, by an implementation of '
          f'{name} alone: the other three are checked only as Core 12 checks a known extension, and only {name} is '
          'evaluated and derived.', ['1.2.1', '1.2.4'], base(), registry=[entry(x) for x in EXTS],
          check=lambda r: ensure(list(r['derived']['extensions']) == [name], list(r['derived']['extensions'])))
    else:
        T('examples', 'all-official-known', f'The flat read with every official entry known, by an implementation of '
          f'{name} alone: the others are checked only as Core 12 checks a known extension, and only {name} is '
          'evaluated and derived.', ['1.2.1', '1.2.4'], base(), registry=[entry(x) for x in ALL],
          check=lambda r: ensure(list(r['derived']['extensions']) == [name], list(r['derived']['extensions'])))
    T('activation', 'unknown-data-not-evaluated', f'{name}\'s data does not match its schema, but no extension is '
      'known: nothing of it is evaluated, and the document is valid.', ['1.2.1'],
      ed(lambda d: ext(d, name).update(colour='red')), registry=None)
    T('activation', 'another-version-known', f'The document uses {name} at 0.2.0, which is known (a later entry), but '
      'the implementation implements 0.1.0: not evaluated, so the data that breaks 0.1.0\'s schema is not reported.',
      ['1.2.1'], ed(lambda d: (ext(d, name).update(colour='red'), d['extensionsUsed'].update({name: '0.2.0'}))),
      registry=[entry(name, '0.2.0')])
    T('activation', 'version-without-patch', f'"0.1" equals 0.1.0 (Core 12.3), so {name} is evaluated: its data breaks '
      f'the schema, FS-{code}-SCH-001.', ['1.2.1', '1.3.1'],
      ed(lambda d: (ext(d, name).update(colour='red'), d['extensionsUsed'].update({name: '0.1'}))),
      [(f'FS-{code}-SCH-001', [])])
    T('activation', 'declaration-object', f'A declaration object with a schema URI is its version string (Core 12.1.3): '
      f'{name} is evaluated.', ['1.2.1', '1.3.1'],
      ed(lambda d: (ext(d, name).update(colour='red'),
                    d['extensionsUsed'].update({name: {'version': '0.1.0', 'schema': entry(name)['schema']}}))),
      [(f'FS-{code}-SCH-001', [])])
    T('activation', 'core-0.1-document', f'A document declaring "0.1" has no extension elements and its extension data is '
      f'opaque (Core 1.2.4): {name} is not evaluated, even though it is known.', ['1.2.1'],
      {'floorspec': '0.1', 'project': {'name': 'Old'}, 'extensionsUsed': {name: '0.1.0'},
       'extensions': {name: {'colour': 'red'}}})
    T('activation', 'core-0.3-document', f'The {HOUSE[name]} declaring Core "0.3", a draft {name} 0.1.0 lists (1.1): {name} is '
      f'evaluated, reports nothing, and derives exactly what it derives for the {HOUSE[name].split()[-1]} declaring "0.2". The suite reads a '
      'document declaring "0.3" as a Core 0.3 reader.', ['1.2.1', '1.2.3', '1.2.4', DERIVE[name]],
      ed(lambda d: d.update(floorspec='0.3')), check=same_as_02(name))
    T('activation', 'core-0.3-invariants', f'The same "0.3" {HOUSE[name].split()[-1]} with {name}\'s data breaking one of its invariants: '
      f'{name} is evaluated for a Core 0.3 document, so the invariant is reported.', ['1.2.1', '1.2.3'],
      ed(lambda d: (d.update(floorspec='0.3'), BREAK[name](d))), BREAK_DIAG[name])
    T('order', 'core-error-first', 'A Core invariant breaks - an element 13\' along the 12\' wall W2, FS-INV-501 - '
      f'and so does {name}\'s schema: Core\'s error is reported, and {name} is not evaluated.', ['1.2.2'],
      ed(lambda d: (ext(d, name).update(colour='red'), WALL_ELEMENT[name](d)['host'].update(wall='W2', offset=13 * FT))),
      [('FS-INV-501', [WALL_ELEMENT_ID[name]])])
    T('order', 'schema-before-invariants', f'The data breaks the schema and an invariant: only FS-{code}-SCH-001.',
      ['1.2.2', '1.3.1'], ed(lambda d: (ext(d, name).update(colour='red'), BREAK[name](d))), [(f'FS-{code}-SCH-001', [])])
    T('order', 'no-lints-when-invalid', f'An invariant breaks and a lint would apply too: the document is invalid, so no '
      f'lint is reported, {name}\'s or Core\'s.', ['1.2.2', '1.2.3'], ed(lambda d: (BREAK[name](d), LINT[name](d))),
      BREAK_DIAG[name])
    T('schema', 'data-not-an-object', f'{name}\'s top-level data is an array: Core allows any JSON there, {name}\'s '
      'schema does not.', ['1.3.1'], ed(lambda d: d['extensions'].update({name: []})), [(f'FS-{code}-SCH-001', [])])
    T('schema', 'unknown-collection-member', 'An element has a member its kind does not define.', ['1.3.1'],
      ed(lambda d: WALL_ELEMENT[name](d).update(colour='red')), [(f'FS-{code}-SCH-001', [])])
    T('schema', 'length-with-a-fraction', 'A number written with a fraction is not an integer, even when it is a whole '
      'number.', ['1.3.1'], None, [(f'FS-{code}-SCH-001', [])],
      raw=(fmt(base()) + '\n').replace(FRACTION[name][0], FRACTION[name][1], 1).encode('utf-8'))
    if name in EXTS:
        c, eid = OPTION_ELEMENT[name]

        def optioned(d):
            d.update(floorspec='0.3', optionSets={'OS1': {'primary': 'OP1', 'name': 'Utility'}},
                     options={'OP1': {'set': 'OS1', 'name': 'A'}, 'OP2': {'set': 'OS1', 'name': 'B'}})
            coll(d, name, c)[eid]['option'] = 'OP1'
        T('options', 'element-in-an-option', f'The house as a Core 0.3 document with an option set: {eid} is in option A, '
          f'the primary, and option B leaves it out (Core 19). {name}\'s data matches its schema with the element\'s '
          f'`option` member - a Core member, checked by Core - and {name} is evaluated in each checked design: '
          'valid, nothing reported, and the primary design derived.', ['1.2.1', '1.2.4', '1.3.1'], ed(optioned),
          check=lambda r: ensure(name in r['derived']['extensions']
                                 and r['derived']['options']['OS1']['options']['OP1']['members'] == [eid], r['derived']['options']))


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
OPTION_ELEMENT = {ELEC: ('switches', 'X26'), PLMB: ('fixtures', 'X25'), MECH: ('terminals', 'X12'), LOWV: ('outlets', 'X16')}
BASE = {x: demo for x in EXTS}
HOUSE = {x: 'demo house' for x in EXTS}
PHASE = {x: 'Phase 5 demo' for x in EXTS}
EXAMPLE = {x: ('p5-demo-house', f'The Phase 5 demo house, read by an implementation of {x} that knows it: a panel, '
               'kitchen receptacles on two 20 A circuits, a toilet, a lavatory, an electric water heater on a 240 V circuit, a '
               'gas furnace and range, a bath fan, and low-voltage devices run to a structured media enclosure. It is valid, '
               f'reports nothing, and derives {x}\'s values as `derived.extensions.{x}`.') for x in EXTS}
CORE_ONLY_CHECK = {x: lambda r: ensure(r['derived']['extensions'] == {} and 'X1' in r['derived']['fallbacks']
                                       and r['derived']['placements']['X6']['facing'] == -90000000
                                       and 'service' in r['derived']['clearances']['X8'], r['derived']['extensions'])
                   for x in EXTS}


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


def shared_ops(name, ids, which=None):
    which = f'the elements on W1 ({", ".join(ids)})' if which is None else which
    O(name, 'move-a-wall-and-watch-them-follow', f'The {PHASE[name]}: the Kitchen\'s west wall W1 moved 1\' west, by an '
      f'applier that implements {name} and knows it. No element changes - every host is relative - and the result is '
      f'valid under {name}; {which} now derive placements 1\' further west.',
      ['1.2.1', 'FS-OPS-2.7.1', 'FS-OPS-4.2.1'], BASE[name](), {'batch': [{'op': 'moveWall', 'wall': 'W1', 'by': "1'"}]},
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


# ============================================================================= FS_furniture

LIBRARY = os.path.join(REPO, 'registry', 'FS_furniture', 'library')
with open(os.path.join(LIBRARY, 'library.json'), encoding='utf-8') as _f:
    LIB = json.load(_f)['items']


def lib_file(item, part):
    """The bytes of a library item's model or symbol."""
    with open(os.path.join(LIBRARY, LIB[item][part]['path']), 'rb') as f:
        return f.read()


def lib_asset(item, part, byte_length=False):
    """The asset of a library item's model or symbol, packaged at furniture/<file>."""
    f = LIB[item][part]
    a = {'path': 'furniture/' + f['path'].split('/')[-1], 'sha256': f['sha256'], 'mediaType': f['mediaType']}
    if byte_length:
        a['byteLength'] = f['byteLength']
    return a


def wall_host(wall, side, offset, height=0):
    return {'mode': 'wallFace', 'wall': wall, 'side': side, 'offset': offset, 'height': height}


def floor_host(room, x, y, rotation=None):
    h = {'mode': 'surface', 'room': room, 'surface': 'floor', 'position': [x, y]}
    if rotation is not None:
        h['rotation'] = rotation
    return h


def free_host(x, y, rotation=None, level='L1'):
    h = {'mode': 'free', 'level': level, 'position': [x, y]}
    if rotation is not None:
        h['rotation'] = rotation
    return h


def item(lib, host, level='L1', **members):
    """An element made from the starter library's item `lib`, as a writer makes one (spec.md 7): its
    category, catalogue, name, seats, box and default envelopes from the library, its model and
    symbol the assets M-<lib> and S-<lib>, placed on `host`."""
    src = LIB[lib]['element']
    el = {'fallback': {'level': level, 'box': copy.deepcopy(src['fallback']['box']), 'asset': f'M-{lib}', 'symbol': f'S-{lib}'}}
    if host is not None:
        el['host'] = host
    for k in ('category', 'catalogue', 'name', 'seats', 'clearances'):
        if k in src:
            el[k] = copy.deepcopy(src[k])
    el.update(members)
    return el


def assets_of(d, byte_length=False):
    """The model and symbol assets of every library item the document's FS_furniture elements use."""
    used = sorted({el['fallback'][k][2:] for c in ext(d, FURN)['collections'].values() for el in c.values()
                   for k in ('asset', 'symbol') if el['fallback'].get(k, '')[:2] in ('M-', 'S-')})
    out = {}
    for lib in used:
        out[f'M-{lib}'] = lib_asset(lib, 'model', byte_length)
        out[f'S-{lib}'] = lib_asset(lib, 'symbol', byte_length)
    return out


def put(d, kind, eid, el):
    """Adds an FS_furniture element, and the assets of its library item."""
    coll(d, FURN, kind)[eid] = el
    d['assets'] = {**d['assets'], **{k: v for k, v in assets_of(d).items() if k not in d['assets']}}
    return d


MM_ = lambda v: v * MM                    # noqa: E731


def flat():
    """The Phase 8 demo flat, 24' x 16', on L1, with every wall 100 mm thick and drawn clockwise:

        J2 ------ W2 ------ J3 ---- W3 ---- J4
        |                   |               |
        W1   Kitchen R1     W9  Bedroom R2  W4
        |                   |               |
        |                   J7 ---- W10 --- J8
        |                   |               |
        |                   W8  Laundry R3  W5
        |                   |               |
        J1 ------ W7 ------ J6 ---- W6 ---- J5

    J1 (0, 0), J2 (0, 16'), J3 (12', 16'), J4 (24', 16'), J5 (24', 0), J6 (12', 0), J7 (12', 7'),
    J8 (24', 7'). Against the Kitchen's north wall W2, from the west: a refrigerator X1, a base cabinet
    X2 with a wall cabinet X6 above it, a range X3, a base cabinet X4 and a dishwasher X5; a pantry
    X15 on its west wall W1; a dining table X7 with two chairs X8 and X9. In the Bedroom a bed X10
    against W3 with a nightstand X11, and a wardrobe X12 on W4; in the Laundry a washer X13 and a
    dryer X14 on W6. Every item is the starter library's, every one in the convention of spec.md 3.1,
    and every one stands against a wall on a wallFace host but the table and its chairs, which stand
    on the Kitchen's floor."""
    d = {
        'floorspec': '0.2', 'project': {'name': 'Phase 8 demo flat'},
        'buildings': {'B1': {}}, 'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
        'types': {'WT': {'kind': 'wallType', 'layers': [{'thickness': 100 * MM, 'function': 'core'}]}},
        'junctions': {'J1': J(0, 0), 'J2': J(0, 16 * FT), 'J3': J(12 * FT, 16 * FT), 'J4': J(24 * FT, 16 * FT),
                      'J5': J(24 * FT, 0), 'J6': J(12 * FT, 0), 'J7': J(12 * FT, 7 * FT), 'J8': J(24 * FT, 7 * FT)},
        'walls': {'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J8'),
                  'W5': W('J8', 'J5'), 'W6': W('J5', 'J6'), 'W7': W('J6', 'J1'), 'W8': W('J6', 'J7'),
                  'W9': W('J7', 'J3'), 'W10': W('J7', 'J8')},
        'rooms': {'R1': {'level': 'L1', 'anchor': [6 * FT, 8 * FT], 'name': 'Kitchen', 'function': 'kitchen'},
                  'R2': {'level': 'L1', 'anchor': [18 * FT, 12 * FT], 'name': 'Bedroom', 'function': 'sleeping'},
                  'R3': {'level': 'L1', 'anchor': [18 * FT, 3 * FT], 'name': 'Laundry', 'function': 'laundry'}},
        'assets': {},
        'extensionsUsed': {FURN: '0.1.0'},
        'extensions': {FURN: {'collections': {
            'appliances': {
                'X1': item('refrigerator-900', wall_host('W2', 'right', MM_(500))),
                'X3': item('range-760', wall_host('W2', 'right', MM_(1930))),
                'X5': item('dishwasher-600', wall_host('W2', 'right', MM_(3210))),
                'X13': item('washer-690', wall_host('W6', 'right', 3 * FT)),
                'X14': item('dryer-690', wall_host('W6', 'right', 3 * FT + MM_(700)))},
            'casework': {
                'X2': item('base-cabinet-600', wall_host('W2', 'right', MM_(1250))),
                'X4': item('base-cabinet-600', wall_host('W2', 'right', MM_(2610))),
                'X6': item('wall-cabinet-600', wall_host('W2', 'right', MM_(1250), MM_(1400))),
                'X15': item('tall-cabinet-600', wall_host('W1', 'right', MM_(1200)))},
            'pieces': {
                'X7': item('dining-table-1500', floor_host('R1', 6 * FT, 7 * FT)),
                'X8': item('dining-chair-450', floor_host('R1', 6 * FT - MM_(550), 7 * FT), **{'with': 'X7'}),
                'X9': item('dining-chair-450', floor_host('R1', 6 * FT + MM_(1450), 7 * FT, 180000000), **{'with': 'X7'}),
                'X10': item('bed-queen-1600', wall_host('W3', 'right', 5 * FT)),
                'X11': item('nightstand-500', wall_host('W3', 'right', 5 * FT + MM_(1100)), **{'with': 'X10'}),
                'X12': item('wardrobe-1000', wall_host('W4', 'right', 7 * FT))}}}},
    }
    d['assets'] = assets_of(d)
    return d


def fedit(fn):
    """The Phase 8 demo flat, changed by fn(d) in place."""
    d = flat()
    fn(d)
    return d


FK = lambda d, c: coll(d, FURN, c)                                                 # noqa: E731
APP = lambda d: FK(d, 'appliances')                                                # noqa: E731
PCS = lambda d: FK(d, 'pieces')                                                    # noqa: E731
CSW = lambda d: FK(d, 'casework')                                                  # noqa: E731
KITCHEN = ['X1', 'X15', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9']


def area(*mm2):
    """The decimal string of a sum of rectangles' areas, each given in square millimetres."""
    return str(sum(mm2) * MM * MM)


def check_furn(r):
    x = r['derived']['extensions'][FURN]
    ensure(x['items']['X1'] == {'kind': 'appliances', 'category': 'refrigerator', 'width': MM_(900), 'depth': MM_(700),
                                'height': MM_(1780), 'room': 'R1'}, x['items']['X1'])
    ensure(x['items']['X6'] == {'kind': 'casework', 'category': 'wallCabinet', 'width': MM_(600), 'depth': MM_(350),
                                'height': MM_(750), 'room': 'R1'}, x['items']['X6'])
    # the floor each room's items stand on: the wall cabinet X6 hangs, so it is not counted
    ensure(x['rooms'] == {
        'R1': {'items': KITCHEN, 'floorArea': area(900 * 700, 600 * 600, 760 * 650, 600 * 600, 600 * 600, 1500 * 900,
                                                   450 * 500, 450 * 500, 600 * 600)},
        'R2': {'items': ['X10', 'X11', 'X12'], 'floorArea': area(1600 * 2050, 500 * 450, 1000 * 600)},
        'R3': {'items': ['X13', 'X14'], 'floorArea': area(690 * 650, 690 * 650)}}, x['rooms'])
    ensure(x['groups'] == {'X10': ['X11'], 'X7': ['X8', 'X9']}, x['groups'])
    # Core derives the refrigerator's door swing, 900 mm deep, in front of it, facing south into the Kitchen
    door = r['derived']['clearances']['X1']['door']
    ensure(door['purpose'] == 'swing' and door['bottom'] == 0 and door['top'] == MM_(1780), door)
    face = 16 * FT - MM_(50)
    ensure(door['footprint'] == [[MM_(50), face - MM_(1600)], [MM_(950), face - MM_(1600)], [MM_(950), face - MM_(700)],
                                 [MM_(50), face - MM_(700)]], door['footprint'])


BASE[FURN] = flat
HOUSE[FURN] = 'demo flat'
PHASE[FURN] = 'Phase 8 demo'
EXAMPLE[FURN] = ('p8-demo-flat', 'The Phase 8 demo flat, read by an implementation of FS_furniture that knows it: a '
                 'kitchen with a refrigerator, a range, a dishwasher, base and wall cabinets, a pantry and a dining table '
                 'with two chairs, a bedroom with a bed, a nightstand and a wardrobe, and a laundry with a washer and a '
                 'dryer - every one the starter library\'s item, with its model, its symbol and its default envelopes. It is '
                 'valid, reports nothing - the chairs in the table\'s envelope and the nightstand beside the bed are with '
                 'them, and the wall cabinet hangs clear of the counter - and derives FS_furniture\'s values as '
                 '`derived.extensions.FS_furniture`: each item\'s kind, category, dimensions and room, each room\'s items '
                 'and the floor they stand on, and the groups.')
CORE_ONLY_CHECK[FURN] = lambda r: ensure(
    r['derived']['extensions'] == {} and 'X1' in r['derived']['fallbacks']
    and r['derived']['placements']['X1']['facing'] == -90000000 and 'door' in r['derived']['clearances']['X1'],
    r['derived']['extensions'])
WALL_ELEMENT_ID[FURN] = 'X1'
WALL_ELEMENT[FURN] = lambda d: APP(d)['X1']
BREAK[FURN] = lambda d: PCS(d)['X8'].update({'with': 'W1'})
BREAK_DIAG[FURN] = [('FS-FURN-INV-002', ['X8'])]
LINT[FURN] = lambda d: APP(d)['X1'].pop('clearances')
FRACTION[FURN] = ('"seats": 6', '"seats": 6.0')
DERIVE[FURN] = '6.1.1'
DEMO_CHECK[FURN] = check_furn

shared(FURN)
F = lambda *a, **k: V(FURN, *a, **k)    # noqa: E731


def plumbing_fixture(d, eid='X16', offset=MM_(3210)):
    """An FS_plumbing fixture behind the dishwasher: the connection of its water and drain."""
    d['extensionsUsed'][PLMB] = '0.1.0'
    d['extensions'][PLMB] = {'collections': {'fixtures': {eid: {
        'fallback': {'level': 'L1', 'box': box(0, -50, 0, 50, 50, 100)}, 'host': wall_host('W2', 'right', offset, MM_(100)),
        'fixture': 'dishwasher', 'supply': ['hot'], 'drain': 'K1'}}}, 'stacks': {'K1': {'levels': ['L1']}}}


def door(d):
    """A 900 mm door O1 in W10, 300 mm from J7, swinging into the Laundry, its type's swing a box (Core 13.5)."""
    d['types']['DT'] = {'kind': 'doorType', 'width': MM_(900), 'height': MM_(2000),
                        'clearances': {'swing': env('swing', box(0, -450, 0, 900, 450, 2000))}}
    d['openings'] = {'O1': {'wall': 'W10', 'offset': MM_(300), 'fill': 'DT', 'swing': 'right'}}


F('schema', 'category-of-another-kind', '"refrigerator" is a category of appliances, not of pieces (2.5).', ['1.3.1'],
  fedit(lambda d: PCS(d)['X7'].update(category='refrigerator')), [('FS-FURN-SCH-001', [])])
F('schema', 'element-without-category', 'Every element says what it is.', ['1.3.1'],
  fedit(lambda d: APP(d)['X5'].pop('category')), [('FS-FURN-SCH-001', [])])
F('schema', 'seats-zero', 'A piece seats at least one person when it says how many.', ['1.3.1'],
  fedit(lambda d: PCS(d)['X7'].update(seats=0)), [('FS-FURN-SCH-001', [])])
F('schema', 'seats-on-an-appliance', 'Only a piece has seats.', ['1.3.1'],
  fedit(lambda d: APP(d)['X1'].update(seats=1)), [('FS-FURN-SCH-001', [])])
F('schema', 'connections-empty', 'An appliance\'s connections, when present, name at least one element.', ['1.3.1'],
  fedit(lambda d: APP(d)['X5'].update(connections=[])), [('FS-FURN-SCH-001', [])])
F('schema', 'connections-repeated', 'An appliance names each connection once.', ['1.3.1'],
  fedit(lambda d: (plumbing_fixture(d), APP(d)['X5'].update(connections=['X16', 'X16']))), [('FS-FURN-SCH-001', [])])
F('schema', 'collection-not-of-the-kind', 'FS_furniture has no collection "rugs": Core reports it first, as FS-INV-604 '
  'of a known extension (Core 12.4.1), and FS_furniture is not evaluated.', ['1.2.2', 'FS-CORE-12.4.1'],
  fedit(lambda d: ext(d, FURN)['collections'].update(rugs={})), [('FS-INV-604', [])])
F('schema', 'appliance-without-a-model', 'Every kind of FS_furniture requires a model in its fallback (1.1): the '
  'refrigerator without one is FS-INV-603 of a known extension (Core 12.4.2), and FS_furniture is not evaluated.',
  ['1.2.2', 'FS-CORE-12.4.2'], fedit(lambda d: APP(d)['X1']['fallback'].pop('asset')), [('FS-INV-603', ['X1'])])
F('schema', 'piece-without-a-symbol-unknown', 'The same requirement is a known extension\'s: read with no known '
  'extensions, a chair without a symbol is valid, and nothing of FS_furniture is evaluated.', ['1.2.1'],
  fedit(lambda d: PCS(d)['X8']['fallback'].pop('symbol')), registry=None,
  check=lambda r: ensure(r['derived']['extensions'] == {}, r['derived']['extensions']))
F('schema', 'symbol-a-jpeg', 'A plan symbol is SVG or PNG (Core 12.6.1): the refrigerator\'s, made a JPEG, is '
  'FS-INV-506, and FS_furniture is not evaluated.', ['1.2.2', 'FS-CORE-12.6.1'],
  fedit(lambda d: d['assets']['S-refrigerator-900'].update(mediaType='image/jpeg')), [('FS-INV-506', ['X1'])])

F('invariants', 'connection-to-its-own-extension', 'The dishwasher names the base cabinet X4 as a connection: an '
  'element of FS_furniture, not of the system that serves it.', ['4.4.1'],
  fedit(lambda d: APP(d)['X5'].update(connections=['X4'])), [('FS-FURN-INV-001', ['X5'])])
F('invariants', 'connections-to-a-wall-and-to-nothing', 'The dishwasher names the wall W2 and X99, which does not '
  'exist: once for each.', ['4.4.1'], fedit(lambda d: APP(d)['X5'].update(connections=['W2', 'X99'])),
  [('FS-FURN-INV-001', ['X5']), ('FS-FURN-INV-001', ['X5'])])
F('invariants', 'connections-to-other-extensions', 'The dishwasher names the FS_plumbing fixture X16 that supplies and '
  'drains it and the FS_electrical receptacle X17 that powers it. Neither extension is known or implemented: the IDs '
  'are checked against the document\'s extension elements, and both are. Valid.', ['4.4.1', '1.2.1'],
  fedit(lambda d: (plumbing_fixture(d), d['extensionsUsed'].update({ELEC: '0.1.0'}),
                   d['extensions'].update({ELEC: {'collections': {'receptacles': {'X17': on_wall('W2', 'right', MM_(3210), 300, PLATE, amps=15)}}}}),
                   APP(d)['X5'].update(connections=['X16', 'X17']))),
  check=lambda r: ensure(list(r['derived']['extensions']) == [FURN]
                         and r['derived']['extensions'][FURN]['items']['X5']['room'] == 'R1', r['derived']['extensions']))
F('invariants', 'with-a-wall', 'A chair with the wall W1.', ['4.3.1'],
  fedit(lambda d: PCS(d)['X8'].update({'with': 'W1'})), [('FS-FURN-INV-002', ['X8'])])
F('invariants', 'with-itself', 'A chair with itself.', ['4.3.1'],
  fedit(lambda d: PCS(d)['X8'].update({'with': 'X8'})), [('FS-FURN-INV-002', ['X8'])])
F('invariants', 'with-an-element-of-another-extension', 'A chair with the FS_plumbing fixture X16: an element, but '
  'not of FS_furniture.', ['4.3.1'],
  fedit(lambda d: (plumbing_fixture(d), PCS(d)['X8'].update({'with': 'X16'}))), [('FS-FURN-INV-002', ['X8'])])
F('invariants', 'with-an-element-that-is-with-another', 'The bed is made to go with the table, so the nightstand, '
  'with the bed, names an element that has a with of its own: grouping is one level deep. The bed itself is fine.',
  ['4.3.1'], fedit(lambda d: PCS(d)['X10'].update({'with': 'X7'})), [('FS-FURN-INV-002', ['X11'])])
F('invariants', 'table-on-the-ceiling', 'The dining table on the Kitchen\'s ceiling, as a surface host may put a '
  'light: nothing of FS_furniture hangs from a ceiling.', ['4.1.1'],
  fedit(lambda d: PCS(d)['X7']['host'].update(surface='ceiling')), [('FS-FURN-INV-003', ['X7'])])

F('lints', 'refrigerator-without-a-door-swing', 'The refrigerator has no swing envelope (4.2).', ['1.2.3'],
  fedit(lambda d: APP(d)['X1'].pop('clearances')), [('FS-FURN-LINT-001', ['X1'])])
F('lints', 'bed-with-only-swings', 'The bed\'s two envelopes are made swings: it has none of its category\'s purpose, '
  'access.', ['1.2.3'],
  fedit(lambda d: [e.update(purpose='swing') for e in PCS(d)['X10']['clearances'].values()]), [('FS-FURN-LINT-001', ['X10'])])
F('lints', 'refrigerator-inside-the-wall', 'The refrigerator\'s box starts 100 mm behind the face it stands against.',
  ['1.2.3'], fedit(lambda d: APP(d)['X1']['fallback']['box']['min'].__setitem__(0, MM_(-100))), [('FS-FURN-LINT-002', ['X1'])])
F('lints', 'wall-cabinet-standing-free', 'The wall cabinet stands free on the floor, facing south: a wall cabinet hangs '
  'on a wall face. It still does not count towards the floor area.', ['1.2.3', '6.1.1'],
  fedit(lambda d: CSW(d)['X6'].update(host=free_host(4 * FT, MM_(600), -90000000))), [('FS-FURN-LINT-003', ['X6'])],
  check=lambda r: ensure(r['derived']['extensions'][FURN]['rooms']['R1']['floorArea'] == area(
      900 * 700, 600 * 600, 760 * 650, 600 * 600, 600 * 600, 1500 * 900, 450 * 500, 450 * 500, 600 * 600), r))
F('lints', 'refrigerator-door-into-a-coffee-table', 'A coffee table X16 stands in front of the refrigerator: the door '
  'swing runs into it (4.5).', ['1.2.3'],
  fedit(lambda d: put(d, 'pieces', 'X16', item('coffee-table-1200', floor_host('R1', MM_(100), MM_(3500))))),
  [('FS-FURN-LINT-004', ['X1', 'X16'])])
F('lints', 'door-swing-into-a-dresser', 'A door O1 from the Bedroom swings into the Laundry, where a dresser X16 stands '
  'in its swing: an opening\'s envelope runs into it as an element\'s does. (With a door, the flat\'s circulation is '
  'evaluated, and it has no entry: Core\'s FS-LINT-014.)', ['1.2.3'],
  fedit(lambda d: (door(d), put(d, 'pieces', 'X16', item('dresser-1200', floor_host('R3', MM_(4400), MM_(1200), 90000000))))),
  [('FS-FURN-LINT-004', ['O1', 'X16']), ('FS-LINT-014', ['B1'])])
F('lints', 'bookcase-in-a-panels-working-space', 'An FS_electrical panel X16 on the Laundry\'s east wall, with its '
  'working space, and a bookcase X17 in it. FS_electrical is neither known nor implemented, but its envelope is '
  'Core\'s (Core 13.5): it runs into the bookcase.', ['1.2.3'],
  fedit(lambda d: (d['extensionsUsed'].update({ELEC: '0.1.0'}),
                   d['extensions'].update({ELEC: {'collections': {'panels': {'X16': on_wall(
                       'W5', 'right', MM_(600), 1200, box(0, -200, -400, 100, 200, 400),
                       clearances={'working': env('workingSpace', box(0, -400, -1200, 1000, 400, 800))})}}}}),
                   put(d, 'pieces', 'X17', item('bookcase-900', floor_host('R3', MM_(6600), MM_(1900), -90000000))))),
  [('FS-FURN-LINT-004', ['X16', 'X17'])])
F('lints', 'two-chairs-in-one-place', 'A third chair X16 where X8 stands, not with the table: it collides with X8, and '
  'the table\'s envelope runs into it.', ['1.2.3'],
  fedit(lambda d: put(d, 'pieces', 'X16', item('dining-chair-450', floor_host('R1', 6 * FT - MM_(550), 7 * FT)))),
  [('FS-FURN-LINT-004', ['X16', 'X7']), ('FS-FURN-LINT-005', ['X16', 'X8'])])
F('lints', 'grouped-chairs-may-overlap', 'The same third chair, with the table: grouped with the table and with X8, '
  'so neither lint applies.', ['1.2.3', '6.1.1'],
  fedit(lambda d: put(d, 'pieces', 'X16', item('dining-chair-450', floor_host('R1', 6 * FT - MM_(550), 7 * FT), **{'with': 'X7'}))),
  check=lambda r: ensure(r['derived']['extensions'][FURN]['groups']['X7'] == ['X16', 'X8', 'X9'], r))
F('lints', 'microwave-on-the-counter', 'A microwave X16 on the base cabinet X4, its bottom on the counter at 900 mm: '
  'the two only touch, so they do not collide. It is built in, so the floor area does not count it.', ['1.2.3', '6.1.1'],
  fedit(lambda d: put(d, 'appliances', 'X16', item('microwave-600', wall_host('W2', 'right', MM_(2610), MM_(900))))),
  check=lambda r: ensure(r['derived']['extensions'][FURN]['rooms']['R1'] == {
      'items': ['X1', 'X15', 'X16', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9'],
      'floorArea': area(900 * 700, 600 * 600, 760 * 650, 600 * 600, 600 * 600, 1500 * 900, 450 * 500, 450 * 500, 600 * 600)}, r))

F('derived', 'outside-and-unhosted', 'An armchair X16 standing free outside the flat, and a bookcase X17 with no host, '
  'placed by its fallback alone: both are items, and neither is in a room.', ['6.1.1'],
  fedit(lambda d: (put(d, 'pieces', 'X16', item('armchair-850', free_host(-6 * FT, 4 * FT))),
                   put(d, 'pieces', 'X17', item('bookcase-900', None)))),
  check=lambda r: ensure(r['derived']['extensions'][FURN]['items']['X16'] == {
      'kind': 'pieces', 'category': 'armchair', 'width': MM_(850), 'depth': MM_(850), 'height': MM_(850)}
      and 'room' not in r['derived']['extensions'][FURN]['items']['X17']
      and list(r['derived']['extensions'][FURN]['rooms']) == ['R1', 'R2', 'R3'], r['derived']['extensions'][FURN]))


def kitchen_options(d):
    """Core 0.3 design options: the Kitchen's option set OS1, with option A (OP1, the primary) keeping the
    refrigerator X1 on the north wall, and option B (OP2) a refrigerator X16 on the west wall W1 instead."""
    d['floorspec'] = '0.3'
    d['optionSets'] = {'OS1': {'primary': 'OP1', 'name': 'Kitchen'}}
    d['options'] = {'OP1': {'set': 'OS1', 'name': 'A'}, 'OP2': {'set': 'OS1', 'name': 'B'}}
    APP(d)['X1']['option'] = 'OP1'
    APP(d)['X16'] = item('refrigerator-900', wall_host('W1', 'right', MM_(3300)), option='OP2')


def in_design(eid, room, absent):
    def check_(r):
        x = r['derived']['extensions'][FURN]
        ensure(x['items'][eid]['room'] == room and absent not in x['items'] and eid in x['rooms'][room]['items'], x)
        o = r['derived']['options']['OS1']
        ensure(o['options']['OP1']['members'] == ['X1'] and o['options']['OP2']['members'] == ['X16'], o)
    return check_


F('options', 'kitchen-option-a', 'Kitchen option A and B as Core 0.3 design options (Core 19): the refrigerator X1 '
  'is in A, the primary, and a refrigerator X16 on the west wall is in B. The primary design is derived: X1 is in '
  'the Kitchen, and X16 is not an item of it.', ['1.2.1', '1.2.4', '6.1.1', 'FS-CORE-19.3.1'],
  fedit(kitchen_options), check=in_design('X1', 'R1', 'X16'))
F('options', 'kitchen-option-b', 'The same document, deriving the design that chooses B (design.json): X16 is the '
  'Kitchen\'s refrigerator, facing east from W1, and X1 is not an item of it.', ['1.2.4', '6.1.1', 'FS-CORE-19.3.1'],
  fedit(kitchen_options), design={'OS1': 'OP2'},
  check=lambda r: (in_design('X16', 'R1', 'X1')(r),
                   ensure(r['derived']['placements']['X16']['facing'] == 0, r['derived']['placements']['X16'])))
F('options', 'invariant-in-option-b', 'Option B\'s refrigerator is with the wall W9: FS_furniture is evaluated in each '
  'checked design, so FS-FURN-INV-002 is reported for option B\'s design, with `design`.', ['1.2.1', '1.2.3', '4.3.1'],
  fedit(lambda d: (kitchen_options(d), APP(d)['X16'].update({'with': 'W9'}))), [('FS-FURN-INV-002', ['X16'], 'OP2')])

F('package', 'library-files-in-the-package', 'The flat as a Core 0.3 document whose assets declare their byteLength, '
  'run by a package validator given the starter library\'s files at the paths its assets name (Core 18.4): every '
  'model and symbol is there, with the digest and length the library gives. Valid.',
  ['1.2.1', 'FS-CORE-18.4.2', 'FS-CORE-18.4.3'],
  fedit(lambda d: d.update(floorspec='0.3', assets=assets_of(d, byte_length=True))),
  package={lib_asset(lib, part)['path']: lib_file(lib, part) for lib in sorted({a[2:] for a in flat()['assets']})
           for part in ('model', 'symbol')})
F('package', 'a-model-that-is-not-the-librarys', 'The same package, with the range\'s model at the path of the '
  'refrigerator\'s: its digest and its length are not the asset\'s (FS-INV-1006, FS-INV-1007), and FS_furniture is not '
  'evaluated.', ['1.2.2', 'FS-CORE-18.4.3'],
  fedit(lambda d: d.update(floorspec='0.3', assets=assets_of(d, byte_length=True))),
  [('FS-INV-1006', ['M-refrigerator-900']), ('FS-INV-1007', ['M-refrigerator-900'])],
  package={**{lib_asset(lib, part)['path']: lib_file(lib, part) for lib in sorted({a[2:] for a in flat()['assets']})
              for part in ('model', 'symbol')},
           'furniture/refrigerator-900.glb': lib_file('range-760', 'model')})

shared_ops(FURN, ['X1', 'X15', 'X2', 'X3', 'X4', 'X5', 'X6'],
           'the pantry on W1 (X15), and the refrigerator, cabinets, range and dishwasher on W2 (X1 to X6), measured from '
           'W2\'s start J2, which moved,')


def without_x1(d):
    del APP(d)['X1']


def placed_like_flat(r, B):
    ensure(B['extensions'][FURN] == flat()['extensions'][FURN], B['extensions'][FURN]['collections']['appliances'].get('X1'))


FRIDGE = {k: v for k, v in item('refrigerator-900', None).items()}
FRIDGE['fallback'] = {k: v for k, v in FRIDGE['fallback'].items() if k != 'level'}

O(FURN, 'place-a-refrigerator', 'The flat without its refrigerator; placeElement puts the starter library\'s '
  'refrigerator on the Kitchen\'s north wall, on the face toward the Kitchen, 500 mm from its start, at height 0. The '
  'result is the flat, byte for byte in FS_furniture\'s data, and valid under FS_furniture.',
  ['1.2.1', 'FS-OPS-4.10.1'], fedit(without_x1),
  {'batch': [{'op': 'placeElement', 'extension': FURN, 'collection': 'appliances', 'id': 'X1',
              'host': {'mode': 'wallFace', 'wall': 'W2', 'toward': 'Kitchen', 'at': '500mm from start', 'height': 0},
              'element': FRIDGE}]},
  check=placed_like_flat)
O(FURN, 'move-the-refrigerator', 'moveElement moves the refrigerator to the Kitchen\'s west wall, 3300 mm from its '
  'start: it now faces east, and its door swing goes with it.', ['1.2.1', 'FS-OPS-4.10.1'], flat(),
  {'batch': [{'op': 'moveElement', 'element': 'X1',
              'host': {'mode': 'wallFace', 'wall': 'W1', 'toward': 'Kitchen', 'at': '3300mm from start', 'height': 0}}]},
  check=lambda r, B: ensure(placements(B, FURN)['X1']['facing'] == 0
                            and APP(B)['X1']['host'] == wall_host('W1', 'right', MM_(3300)), APP(B)['X1']))
O(FURN, 'remove-the-table-is-rejected', 'Removing the dining table leaves its two chairs with an element that is gone: '
  'the result breaks 4.3.1, and an applier that implements FS_furniture and knows it rejects the batch (Ops 1.2.3).',
  ['4.3.1', '1.2.1', 'FS-OPS-1.2.3'], flat(), {'batch': [{'op': 'removeElement', 'id': 'X7'}]}, 'rejected',
  [('FS-FURN-INV-002', ['X8']), ('FS-FURN-INV-002', ['X9'])])
O(FURN, 'remove-the-table-and-its-chairs', 'The same removal with the chairs removed in the same batch: it commits.',
  ['4.3.1', '1.2.1'], flat(),
  {'batch': [{'op': 'removeElement', 'id': 'X8'}, {'op': 'removeElement', 'id': 'X9'}, {'op': 'removeElement', 'id': 'X7'}]},
  check=lambda r, B: ensure(sorted(r['removed']) == ['X7', 'X8', 'X9'], r['removed']))
O(FURN, 'place-a-refrigerator-in-option-b', 'Kitchen options A and B in a Core 0.3 document, applied as Ops 0.3 with '
  'context.option B: placeElement puts option B\'s refrigerator on the west wall, and the applier adds it to B (Ops '
  '2.8.1). Both designs are valid under FS_furniture.', ['1.2.1', 'FS-OPS-2.8.1'],
  fedit(lambda d: (kitchen_options(d), APP(d).pop('X16'))),
  {'context': {'option': 'OP2'},
   'batch': [{'op': 'placeElement', 'extension': FURN, 'collection': 'appliances', 'id': 'X16',
              'host': {'mode': 'wallFace', 'wall': 'W1', 'toward': 'Kitchen', 'at': '3300mm from start', 'height': 0},
              'element': FRIDGE}]},
  check=lambda r, B: ensure(APP(B)['X16'] == item('refrigerator-900', wall_host('W1', 'right', MM_(3300)), option='OP2'),
                            APP(B)['X16']))


# ============================================================================= FS_structural

STRC = 'FS_structural'
CODE[STRC] = 'STRC'
IN = 32512                                # an inch, 25.4 mm
EXT_T, INT_T = 13 * IN // 2, 9 * IN // 2  # 6 1/2" exterior and 4 1/2" interior walls


def member(designation, w_in2, d_in4):
    """A member of `designation`, its actual width and depth given in half and quarter inches."""
    return {'designation': designation, 'width': w_in2 * IN // 2, 'depth': d_in4 * IN // 4}


TWO_BY = {4: member('2x4', 3, 14), 6: member('2x6', 3, 22), 8: member('2x8', 3, 29), 10: member('2x10', 3, 37),
          12: member('2x12', 3, 45)}
OC16, OC24 = 16 * IN, 24 * IN


def studs(n, spacing=OC16, material='wood'):
    return {'material': material, 'system': 'studs', 'member': copy.deepcopy(TWO_BY[n]), 'spacing': spacing}


def joists(n, spacing=OC16, material='wood'):
    return {'material': material, 'system': 'joists', 'member': copy.deepcopy(TWO_BY[n]), 'spacing': spacing}


def header(n, plies=2, material='wood'):
    return {'material': material, 'member': copy.deepcopy(TWO_BY[n]), 'plies': plies}


def SW(s, e, t, **data):
    w = {'level': 'L1', 'start': s, 'end': e, 'type': t}
    if data:
        w['extensions'] = {STRC: data}
    return w


def framed():
    """The Phase 10 framed house: the Phase 5 demo house's plan, 20' x 12', on L1, drawn clockwise
    (see demo()), with 6 1/2" exterior walls (EXT: 2x6 studs and their sheathing and drywall) and
    4 1/2" interior walls (INT: 2x4 studs), and its structure recorded for handoff:

    - every exterior wall bears, framed with 2x6 studs at 16"; W1, W2 and W4 are also shear walls;
    - W8 and W9, the interior line at 12', bear the floor joists' middle, framed with 2x4 studs at
      16"; W10, between the Bath and the Utility room, is non-bearing, 2x4 studs at 24";
    - a door O1 in the south wall W7, 3' wide and 80" high, under a two-ply 2x10 header; a window O2
      in the north wall W2, 4' wide and 48" high on a 36" sill, under a two-ply 2x10 header that is
      flagged for an engineer; a door O4 from the Kitchen to the Utility room in the bearing W8, under
      a two-ply 2x6 header; and a door O3 from the Utility room to the Bath in the non-bearing W10,
      with no header;
    - the Kitchen's floor (R1), 2x10 joists at 16" spanning east-west, from W1 to the interior line;
      the Bath's floor (R2) a concrete slab on grade;
    - a deck S1 south of the house, 8' x 7', on 2x8 joists at 16" spanning north-south, with a
      recorded clear span of 6' (a beam the record does not model carries its south end)."""
    d = {
        'floorspec': '0.2', 'project': {'name': 'Phase 10 framed house'},
        'buildings': {'B1': {}}, 'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
        'types': {'EXT': {'kind': 'wallType', 'layers': [{'thickness': EXT_T, 'function': 'core'}]},
                  'INT': {'kind': 'wallType', 'layers': [{'thickness': INT_T, 'function': 'core'}]}},
        'junctions': {'J1': J(0, 0), 'J2': J(0, 12 * FT), 'J3': J(12 * FT, 12 * FT), 'J4': J(20 * FT, 12 * FT),
                      'J5': J(20 * FT, 0), 'J6': J(12 * FT, 0), 'J7': J(12 * FT, 6 * FT), 'J8': J(20 * FT, 6 * FT)},
        'walls': {
            'W1': SW('J1', 'J2', 'EXT', bearing=True, shear=True, framing=studs(6)),
            'W2': SW('J2', 'J3', 'EXT', bearing=True, shear=True, framing=studs(6)),
            'W3': SW('J3', 'J4', 'EXT', bearing=True, framing=studs(6)),
            'W4': SW('J4', 'J8', 'EXT', bearing=True, shear=True, framing=studs(6)),
            'W5': SW('J8', 'J5', 'EXT', bearing=True, framing=studs(6)),
            'W6': SW('J5', 'J6', 'EXT', bearing=True, framing=studs(6)),
            'W7': SW('J6', 'J1', 'EXT', bearing=True, framing=studs(6)),
            'W8': SW('J6', 'J7', 'INT', bearing=True, framing=studs(4)),
            'W9': SW('J7', 'J3', 'INT', bearing=True, framing=studs(4)),
            'W10': SW('J7', 'J8', 'INT', bearing=False, framing=studs(4, OC24))},
        'openings': {
            'O1': {'wall': 'W7', 'offset': 3 * FT, 'width': 3 * FT, 'height': 80 * IN, 'name': 'Back door',
                   'extensions': {STRC: {'header': header(10)}}},
            'O2': {'wall': 'W2', 'offset': 4 * FT, 'width': 4 * FT, 'height': 48 * IN, 'sill': 36 * IN, 'name': 'Kitchen window',
                   'extensions': {STRC: {'header': header(10), 'needsEngineer': True,
                                         'note': 'Widening this window is planned: the header is to be sized by an engineer.'}}},
            'O3': {'wall': 'W10', 'offset': 2 * FT, 'width': 30 * IN, 'height': 80 * IN, 'name': 'Bath door'},
            'O4': {'wall': 'W8', 'offset': FT, 'width': 30 * IN, 'height': 80 * IN, 'name': 'Utility door',
                   'extensions': {STRC: {'header': header(6)}}}},
        'rooms': {'R1': {'level': 'L1', 'anchor': [6 * FT, 6 * FT], 'name': 'Kitchen', 'function': 'kitchen',
                         'extensions': {STRC: {'floor': {'framing': joists(10), 'span': {'direction': [1, 0]}}}}},
                  'R2': {'level': 'L1', 'anchor': [16 * FT, 9 * FT], 'name': 'Bath', 'function': 'bath',
                         'extensions': {STRC: {'floor': {'framing': {'material': 'concrete', 'system': 'solid'}}}}},
                  'R3': {'level': 'L1', 'anchor': [16 * FT, 3 * FT], 'name': 'Utility', 'function': 'mechanical'}},
        'slabs': {'S1': {'level': 'L1', 'boundary': [[2 * FT, -8 * FT], [10 * FT, -8 * FT], [10 * FT, -FT], [2 * FT, -FT]],
                         'thickness': 3 * IN // 2, 'name': 'Deck',
                         'extensions': {STRC: {'framing': joists(8), 'span': {'direction': [0, 1], 'length': 6 * FT}}}}},
        'extensionsUsed': {STRC: '0.1.0'},
    }
    return d


def sedit(fn):
    """The Phase 10 framed house, changed by fn(d) in place."""
    d = framed()
    fn(d)
    return d


def SD(d, c, eid):
    """The FS_structural data on an element, created when missing."""
    return d[c][eid].setdefault('extensions', {}).setdefault(STRC, {})


S = lambda *a, **k: V(STRC, *a, **k)    # noqa: E731
SDER = derived_of(STRC)
KITCHEN_EW = 12 * FT - EXT_T // 2 - INT_T // 2                 # W1's east face to the interior line's west face
KITCHEN_NS = 12 * FT - EXT_T                                   # W7's north face to W2's south face
LEVEL_L1 = {'bearing': ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9'], 'shear': ['W1', 'W2', 'W4'],
            'openings': ['O1', 'O2', 'O4']}


def check_strc(r):
    x = r['derived']['extensions'][STRC]
    ensure(x == {'levels': {'L1': LEVEL_L1},
                 'spans': {'R1': {'direction': [1, 0], 'extent': KITCHEN_EW, 'span': KITCHEN_EW},
                           'S1': {'direction': [0, 1], 'extent': 7 * FT, 'span': 6 * FT}},
                 'needsEngineer': ['O2']}, x)


def strc_derived(d, name=STRC, design=None):
    """What an implementation of FS_structural that knows it derives for d."""
    data = json.dumps(d).encode('utf-8')
    result, _, _ = check(data, ext_reader(data), json.dumps([entry(name)]).encode('utf-8'), official.implemented(name),
                         None, design)
    assert result['valid'], result['diagnostics']
    return result['derived']['extensions'][name]


BAD = lambda d: SD(d, 'walls', 'W1').update(bearing='yes')                    # noqa: E731  the schema tier
INVALID = lambda d: SD(d, 'walls', 'W10')['framing'].update(spacing=IN)       # noqa: E731  FS-STRC-INV-002
INVALID_DIAG = [('FS-STRC-INV-002', ['W10'])]

S('examples', 'p10-framed-house', 'The Phase 10 framed house, read by an implementation of FS_structural that knows it: '
  'bearing and shear walls framed with 2x6 and 2x4 studs, a door and a window under two-ply 2x10 headers - the window '
  'flagged for an engineer - a door in a non-bearing wall with no header, the Kitchen\'s 2x10 floor joists spanning '
  'east-west, the Bath\'s slab on grade, and a deck on 2x8 joists with a recorded span. The document has no top-level '
  'FS_structural data: all of it is on walls, openings, rooms and the slab. It is valid, reports nothing, and derives '
  'the bearing and shear walls and the openings in bearing walls of L1, the Kitchen\'s span - its extent the clear '
  'distance between W1\'s east face and the interior line\'s west face - and the deck\'s, whose recorded 6\' stands '
  'for its 7\' extent, and what needs an engineer.',
  ['1.2.1', '1.2.3', '1.2.4', '1.3.1', '1.3.2', '3.2.1', '5.1.1'], framed(), check=check_strc)
S('examples', 'core-only-reader', 'The same house read with no known extensions: FS_structural is not evaluated, so '
  'nothing of it is derived (`derived.extensions` is empty), and Core derives the walls, rooms and openings as it '
  'would without the data (Core 1.6.9).', ['1.2.1', '1.2.4', 'FS-CORE-1.6.9'], framed(), registry=None,
  check=lambda r: ensure(r['derived']['extensions'] == {} and sorted(r['derived']['openings']) == ['O1', 'O2', 'O3', 'O4'],
                         r['derived']['extensions']))
S('examples', 'all-official-known', 'The house read with every official entry known, by an implementation of '
  'FS_structural alone: only FS_structural is evaluated and derived.', ['1.2.1', '1.2.4'], framed(),
  registry=[entry(x) for x in ALL + (STRC,)],
  check=lambda r: ensure(list(r['derived']['extensions']) == [STRC], list(r['derived']['extensions'])))
S('examples', 'empty-top-level-data', 'The house with an empty object as FS_structural\'s top-level data, which this '
  'version gives no members: valid, and derived as without it.', ['1.3.1', '5.1.1'],
  sedit(lambda d: d.update(extensions={STRC: {}})), check=check_strc)
S('examples', 'a-framed-roof', 'The house as a Core 0.3 document with a roof over it, framed with 2x8 rafters at 24" '
  '(Core 16): FS_structural\'s data on a roof is its framing, of the roof systems. Valid, and the derived values are '
  'the 0.2 house\'s.', ['1.2.1', '1.3.2', '5.1.1'],
  sedit(lambda d: d.update(floorspec='0.3', roofs={'RF1': {
      'level': 'L1', 'footprint': [[-FT, -FT], [21 * FT, -FT], [21 * FT, 13 * FT], [-FT, 13 * FT]],
      'pitch': {'rise': 6, 'run': 12},
      'extensions': {STRC: {'framing': {'material': 'wood', 'system': 'rafters', 'member': TWO_BY[8], 'spacing': OC24},
                            'needsEngineer': True}}}})),
  check=lambda r: ensure(SDER(r)['needsEngineer'] == ['O2', 'RF1'] and SDER(r)['levels'] == {'L1': LEVEL_L1}, SDER(r)))

S('activation', 'unknown-data-not-evaluated', 'W1\'s FS_structural data does not match the schema, but no extension '
  'is known: nothing of it is evaluated, and the document is valid.', ['1.2.1'], sedit(BAD), registry=None)
S('activation', 'another-version-known', 'The document uses FS_structural at 0.2.0, which is known (a later entry), '
  'but the implementation implements 0.1.0: not evaluated, so the data that breaks 0.1.0\'s schema is not reported.',
  ['1.2.1'], sedit(lambda d: (BAD(d), d['extensionsUsed'].update({STRC: '0.2.0'}))), registry=[entry(STRC, '0.2.0')])
S('activation', 'version-without-patch', '"0.1" equals 0.1.0 (Core 12.3), so FS_structural is evaluated: W1\'s data '
  'breaks the schema, FS-STRC-SCH-001.', ['1.2.1', '1.3.2'],
  sedit(lambda d: (BAD(d), d['extensionsUsed'].update({STRC: '0.1'}))), [('FS-STRC-SCH-001', [])])
S('activation', 'declaration-object', 'A declaration object with a schema URI is its version string (Core 12.1.3): '
  'FS_structural is evaluated.', ['1.2.1', '1.3.2'],
  sedit(lambda d: (BAD(d), d['extensionsUsed'].update({STRC: {'version': '0.1.0', 'schema': entry(STRC)['schema']}}))),
  [('FS-STRC-SCH-001', [])])
S('activation', 'core-0.1-document', 'A document declaring "0.1" whose extension data is opaque (Core 1.2.4): '
  'FS_structural is not evaluated, even though it is known.', ['1.2.1'],
  {'floorspec': '0.1', 'project': {'name': 'Old'}, 'extensionsUsed': {STRC: '0.1.0'}, 'extensions': {STRC: {'colour': 'red'}}})
S('activation', 'core-0.3-document', 'The framed house declaring Core "0.3", a draft FS_structural 0.1.0 lists (1.1): '
  'FS_structural is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
  ['1.2.1', '1.2.3', '1.2.4', '5.1.1'], sedit(lambda d: d.update(floorspec='0.3')), check=check_strc)
S('activation', 'core-0.3-invariants', 'The same "0.3" house with W10\'s studs closer than they are wide: '
  'FS_structural is evaluated for a Core 0.3 document, so the invariant is reported.', ['1.2.1', '1.2.3', '2.2.2'],
  sedit(lambda d: (d.update(floorspec='0.3'), INVALID(d))), INVALID_DIAG)

S('order', 'core-error-first', 'A Core invariant breaks - the door O3 runs past the end of W10, FS-INV-302 - and '
  'so does FS_structural\'s schema: Core\'s error is reported, and FS_structural is not evaluated.', ['1.2.2'],
  sedit(lambda d: (BAD(d), d['openings']['O3'].update(offset=7 * FT))), [('FS-INV-302', ['O3'])])
S('order', 'schema-before-invariants', 'The data breaks the schema and an invariant: only FS-STRC-SCH-001.',
  ['1.2.2', '1.3.2'], sedit(lambda d: (BAD(d), INVALID(d))), [('FS-STRC-SCH-001', [])])
S('order', 'no-lints-when-invalid', 'An invariant breaks and a lint would apply too - O1 has no header in its bearing '
  'wall: the document is invalid, so no lint is reported, FS_structural\'s or Core\'s.', ['1.2.2', '1.2.3'],
  sedit(lambda d: (INVALID(d), d['openings']['O1'].pop('extensions'))), INVALID_DIAG)

S('schema', 'top-level-data-not-an-object', 'FS_structural\'s top-level data is an array: Core allows any JSON there, '
  'FS_structural\'s schema does not.', ['1.3.1'], sedit(lambda d: d.update(extensions={STRC: []})),
  [('FS-STRC-SCH-001', [])])
S('schema', 'top-level-data-with-a-member', 'FS_structural 0.1 gives its top-level data no members.', ['1.3.1'],
  sedit(lambda d: d.update(extensions={STRC: {'defaults': {'bearing': True}}})), [('FS-STRC-SCH-001', [])])
S('schema', 'bearing-not-a-boolean', 'W1\'s `bearing` is "yes": a flag is a boolean.', ['1.3.2'], sedit(BAD),
  [('FS-STRC-SCH-001', [])])
S('schema', 'wall-data-unknown-member', 'W1\'s data has a member a wall\'s data does not define.', ['1.3.2'],
  sedit(lambda d: SD(d, 'walls', 'W1').update(loadPath='roof')), [('FS-STRC-SCH-001', [])])
S('schema', 'framing-without-a-system', 'A framing always says how it is built.', ['1.3.2'],
  sedit(lambda d: SD(d, 'walls', 'W1')['framing'].pop('system')), [('FS-STRC-SCH-001', [])])
S('schema', 'wall-system-under-a-floor', '"studs" is a wall\'s system, not a floor\'s.', ['1.3.2'],
  sedit(lambda d: SD(d, 'rooms', 'R1')['floor']['framing'].update(system='studs')), [('FS-STRC-SCH-001', [])])
S('schema', 'member-without-a-depth', 'A member always has its actual width and depth.', ['1.3.2'],
  sedit(lambda d: SD(d, 'walls', 'W2')['framing']['member'].pop('depth')), [('FS-STRC-SCH-001', [])])
S('schema', 'length-with-a-fraction', 'A length written with a fraction is not an integer, even when it is a whole '
  'number.', ['1.3.2'], None, [('FS-STRC-SCH-001', [])],
  raw=(fmt(framed()) + '\n').replace('"spacing": 780288', '"spacing": 780288.0', 1).encode('utf-8'))
S('schema', 'header-of-nine-plies', 'A header has 1 to 8 plies.', ['1.3.2'],
  sedit(lambda d: SD(d, 'openings', 'O1')['header'].update(plies=9)), [('FS-STRC-SCH-001', [])])
S('schema', 'span-direction-of-three-numbers', 'A direction is two integers.', ['1.3.2'],
  sedit(lambda d: SD(d, 'slabs', 'S1')['span'].update(direction=[0, 1, 0])), [('FS-STRC-SCH-001', [])])
S('schema', 'span-on-a-wall', 'A wall\'s data has no span.', ['1.3.2'],
  sedit(lambda d: SD(d, 'walls', 'W1').update(span={'direction': [1, 0]})), [('FS-STRC-SCH-001', [])])
S('schema', 'roof-system-on-a-roof', '"joists" is a floor\'s system, not a roof\'s (a Core 0.3 document).', ['1.3.2'],
  sedit(lambda d: d.update(floorspec='0.3', roofs={'RF1': {
      'level': 'L1', 'footprint': [[-FT, -FT], [21 * FT, -FT], [21 * FT, 13 * FT], [-FT, 13 * FT]],
      'pitch': {'rise': 6, 'run': 12}, 'extensions': {STRC: {'framing': joists(8)}}}})),
  [('FS-STRC-SCH-001', [])])
S('schema', 'data-on-a-level', 'L1 carries FS_structural data, which this version defines on no level.', ['1.3.3'],
  sedit(lambda d: d['levels']['L1'].update(extensions={STRC: {}})), [('FS-STRC-SCH-001', [])])
S('schema', 'data-on-a-wall-type', 'The wall type EXT carries a framing: FS_structural 0.1 records framing on walls, '
  'never on types.', ['1.3.3'], sedit(lambda d: d['types']['EXT'].update(extensions={STRC: {'framing': studs(6)}})),
  [('FS-STRC-SCH-001', [])])
S('schema', 'data-on-a-junction', 'A junction carries an FS_structural note.', ['1.3.3'],
  sedit(lambda d: d['junctions']['J1'].update(extensions={STRC: {'note': 'Corner post'}})), [('FS-STRC-SCH-001', [])])

S('invariants', 'solid-floor-with-a-spacing', 'The Bath\'s concrete slab on grade has a spacing.', ['2.2.1'],
  sedit(lambda d: SD(d, 'rooms', 'R2')['floor']['framing'].update(spacing=OC16)), [('FS-STRC-INV-001', ['R2'])])
S('invariants', 'panel-wall-with-a-member', 'W10 is built of panels, and has a member.', ['2.2.1'],
  sedit(lambda d: SD(d, 'walls', 'W10')['framing'].update(system='panels')),
  [('FS-STRC-INV-001', ['W10'])])
S('invariants', 'panel-wall', 'W10 built of panels, with no member or spacing: valid.', ['2.2.1'],
  sedit(lambda d: SD(d, 'walls', 'W10').update(framing={'material': 'wood', 'system': 'panels'})))
S('invariants', 'spacing-less-than-width', 'W10\'s 2x4 studs, 1 1/2" wide, are 1" on centre.', ['2.2.2'],
  sedit(INVALID), INVALID_DIAG)
S('invariants', 'spacing-equal-to-width', 'The deck\'s joists 1 1/2" on centre, as wide as they are: side by side, a '
  'built-up deck. Valid.', ['2.2.2'], sedit(lambda d: SD(d, 'slabs', 'S1')['framing'].update(spacing=3 * IN // 2)))
S('invariants', 'masonry-studs', 'W1 framed with concrete masonry studs.', ['2.2.3'],
  sedit(lambda d: SD(d, 'walls', 'W1')['framing'].update(material='concreteMasonry')), [('FS-STRC-INV-003', ['W1'])])
S('invariants', 'concrete-joists', 'The Kitchen\'s floor on concrete joists.', ['2.2.3'],
  sedit(lambda d: SD(d, 'rooms', 'R1')['floor']['framing'].update(material='concrete')), [('FS-STRC-INV-003', ['R1'])])
S('invariants', 'masonry-wall', 'W1 a solid concrete masonry wall: valid.', ['2.2.3'],
  sedit(lambda d: SD(d, 'walls', 'W1').update(framing={'material': 'concreteMasonry', 'system': 'solid'})))
S('invariants', 'steel-joists', 'The deck on cold-formed steel joists: valid.', ['2.2.3'],
  sedit(lambda d: SD(d, 'slabs', 'S1')['framing'].update(material='coldFormedSteel')))
S('invariants', 'span-direction-zero', 'The Kitchen\'s floor spans along [0, 0], which is no direction.', ['3.1.1'],
  sedit(lambda d: SD(d, 'rooms', 'R1')['floor']['span'].update(direction=[0, 0])), [('FS-STRC-INV-004', ['R1'])])
S('invariants', 'slab-span-direction-zero', 'The deck spans along [0, 0], with a recorded length.', ['3.1.1'],
  sedit(lambda d: SD(d, 'slabs', 'S1')['span'].update(direction=[0, 0])), [('FS-STRC-INV-004', ['S1'])])
S('invariants', 'not-evaluated-for-masonry-studs', 'W1\'s concrete masonry studs are also 1" on centre: '
  'FS-STRC-INV-003 only, and not FS-STRC-INV-002 (4.2).', ['4.2.1', '2.2.3'],
  sedit(lambda d: SD(d, 'walls', 'W1')['framing'].update(material='concreteMasonry', spacing=IN)),
  [('FS-STRC-INV-003', ['W1'])])
S('invariants', 'not-evaluated-for-a-solid-floor', 'The Bath\'s slab on grade has a 2x10 member at 1": '
  'FS-STRC-INV-001 only, and not FS-STRC-INV-002 (4.2).', ['4.2.1', '2.2.1'],
  sedit(lambda d: SD(d, 'rooms', 'R2')['floor']['framing'].update(member=TWO_BY[10], spacing=IN)),
  [('FS-STRC-INV-001', ['R2'])])
S('invariants', 'every-one-once', 'Four framings break three rules at once, and the deck\'s span has no direction: '
  'each is reported once, naming its element.', ['1.2.3', '2.2.1', '2.2.2', '2.2.3', '3.1.1'],
  sedit(lambda d: (INVALID(d), SD(d, 'walls', 'W1')['framing'].update(material='masonry'),
                   SD(d, 'rooms', 'R2')['floor']['framing'].update(spacing=OC16),
                   SD(d, 'walls', 'W8')['framing'].update(spacing=IN),
                   SD(d, 'slabs', 'S1')['span'].update(direction=[0, 0]))),
  [('FS-STRC-INV-001', ['R2']), ('FS-STRC-INV-002', ['W10']), ('FS-STRC-INV-002', ['W8']),
   ('FS-STRC-INV-003', ['W1']), ('FS-STRC-INV-004', ['S1'])])
S('invariants', 'no-judgement-of-adequacy', 'A house framed as no engineer would accept: the Kitchen\'s floor on 2x4 '
  'joists at 48" across its 11\'6 1/2", the deck on 2x4 joists at 48" with no span recorded, and the back door widened to '
  '10\' under one 2x4 laid flat. FS_structural compares no member with a load, a span table or a code: the document '
  'is valid, reports nothing, and derives only the values of chapter 5 - the spans as recorded and measured, and '
  'nothing that says whether anything is adequate.', ['1.4.1', '1.4.2', '5.1.1'],
  sedit(lambda d: (SD(d, 'rooms', 'R1')['floor'].update(framing=joists(4, 48 * IN)),
                   SD(d, 'slabs', 'S1').update(framing=joists(4, 48 * IN), span={'direction': [0, 1]}),
                   d['openings']['O1'].update(offset=FT, width=10 * FT),
                   SD(d, 'openings', 'O1').update(header={'material': 'wood', 'member': TWO_BY[4]}))),
  check=lambda r: ensure(SDER(r) == {'levels': {'L1': LEVEL_L1},
                                     'spans': {'R1': {'direction': [1, 0], 'extent': KITCHEN_EW, 'span': KITCHEN_EW},
                                               'S1': {'direction': [0, 1], 'extent': 7 * FT, 'span': 7 * FT}},
                                     'needsEngineer': ['O2']}, SDER(r)))

S('lints', 'opening-in-a-bearing-wall-without-a-header', 'The back door O1, in the bearing wall W7, has no header.',
  ['1.2.3', '2.4.1'], sedit(lambda d: d['openings']['O1'].pop('extensions')), [('FS-STRC-LINT-001', ['O1', 'W7'])])
S('lints', 'opening-in-a-wall-not-stated-to-bear', 'W10 does not say whether it bears, and its door O3 has no header: '
  'no lint, since only a wall whose `bearing` is true asks for one.', ['1.2.3'],
  sedit(lambda d: SD(d, 'walls', 'W10').pop('bearing')))
S('lints', 'header-wider-than-the-wall', 'O1\'s header has five plies of 2x10, 7 1/2" wide, in a 6 1/2" wall.',
  ['1.2.3'], sedit(lambda d: SD(d, 'openings', 'O1')['header'].update(plies=5)), [('FS-STRC-LINT-002', ['O1', 'W7'])])
S('lints', 'header-as-wide-as-the-wall', 'O1\'s header is a 6 1/2" wide member, exactly the wall\'s thickness: no '
  'lint.', ['1.2.3'],
  sedit(lambda d: SD(d, 'openings', 'O1').update(header={'material': 'engineeredWood', 'member': {'width': EXT_T, 'depth': 12 * IN}})))
S('lints', 'studs-deeper-than-the-wall', 'W10, 4 1/2" thick, is framed with 2x6 studs, 5 1/2" deep.', ['1.2.3'],
  sedit(lambda d: SD(d, 'walls', 'W10').update(framing=studs(6, OC24))), [('FS-STRC-LINT-003', ['W10'])])
S('lints', 'header-that-does-not-fit', 'The window O2\'s head is at 84" in a wall 2700 mm high, which leaves '
  '566.4 mm above it: a 24" (609.6 mm) deep glulam header does not fit.', ['1.2.3'],
  sedit(lambda d: SD(d, 'openings', 'O2').update(header={'material': 'engineeredWood', 'member': {'designation': '5-1/8 x 24 GLB', 'width': 41 * IN // 8, 'depth': 24 * IN}})),
  [('FS-STRC-LINT-004', ['O2', 'W2'])])
S('lints', 'header-that-just-fits', 'O2\'s header exactly 566.4 mm deep, the space above its head: no lint.', ['1.2.3'],
  sedit(lambda d: SD(d, 'openings', 'O2')['header']['member'].update(depth=H - 84 * IN)))
S('lints', 'header-in-a-wall-with-its-own-height', 'W2 is 2300 mm high (its top unconnected, Core 5.9), and O2\'s '
  '2x10 header, 9 1/4" deep, no longer fits in the 166.4 mm left above the window.', ['1.2.3'],
  sedit(lambda d: d['walls']['W2'].update(top={'height': 2300 * MM})), [('FS-STRC-LINT-004', ['O2', 'W2'])])
S('lints', 'span-longer-than-the-deck', 'The deck\'s recorded span is 8\', and it reaches only 7\' along its '
  'direction.', ['1.2.3', '3.2.1'], sedit(lambda d: SD(d, 'slabs', 'S1')['span'].update(length=8 * FT)),
  [('FS-STRC-LINT-005', ['S1'])])
S('lints', 'span-as-long-as-the-room', 'The Kitchen\'s recorded span is exactly its extent: no lint; one unit more, '
  'in the next test, is.', ['1.2.3', '3.2.1'],
  sedit(lambda d: SD(d, 'rooms', 'R1')['floor']['span'].update(length=KITCHEN_EW)),
  check=lambda r: ensure(SDER(r)['spans']['R1'] == {'direction': [1, 0], 'extent': KITCHEN_EW, 'span': KITCHEN_EW}, SDER(r)))
S('lints', 'span-one-unit-longer-than-the-room', 'The Kitchen\'s recorded span is its extent plus 1/1280 mm.',
  ['1.2.3', '3.2.1'], sedit(lambda d: SD(d, 'rooms', 'R1')['floor']['span'].update(length=KITCHEN_EW + 1)),
  [('FS-STRC-LINT-005', ['R1'])])
S('lints', 'bearing-wall-without-framing', 'W8 bears, and says nothing of how it is built.', ['1.2.3'],
  sedit(lambda d: SD(d, 'walls', 'W8').pop('framing')), [('FS-STRC-LINT-006', ['W8'])])

S('derived', 'span-on-the-diagonal', 'The deck spans along [1, 1], with no recorded length: its corners project on '
  'the direction from -6\' to 9\', 15\' times the direction\'s length, so its extent is 15\' / sqrt 2 - 4138102.02... - '
  'rounded once to 4138102.', ['3.2.1', '5.1.1'],
  sedit(lambda d: SD(d, 'slabs', 'S1').update(span={'direction': [1, 1]})),
  check=lambda r: ensure(SDER(r)['spans']['S1'] == {'direction': [1, 1], 'extent': 4138102, 'span': 4138102}, SDER(r)))
S('derived', 'direction-length-does-not-matter', 'The Kitchen\'s span along [3, 0] and the Bath\'s floor along [0, -7]: '
  'a direction\'s length changes nothing, and its sign changes nothing. The Kitchen reaches the same clear width as '
  'along [1, 0]; the Bath, from W10\'s north face to W3\'s south face, 6\' less half of each wall.', ['3.2.1', '5.1.1'],
  sedit(lambda d: (SD(d, 'rooms', 'R1')['floor']['span'].update(direction=[3, 0]),
                   SD(d, 'rooms', 'R2')['floor'].update(span={'direction': [0, -7]}))),
  check=lambda r: ensure(SDER(r)['spans'] == {
      'R1': {'direction': [3, 0], 'extent': KITCHEN_EW, 'span': KITCHEN_EW},
      'R2': {'direction': [0, -7], 'extent': 6 * FT - EXT_T // 2 - INT_T // 2, 'span': 6 * FT - EXT_T // 2 - INT_T // 2},
      'S1': {'direction': [0, 1], 'extent': 7 * FT, 'span': 6 * FT}}, SDER(r)))
S('derived', 'kitchen-spanning-north-south', 'The Kitchen\'s joists turned to span north-south: its extent is the '
  'clear distance between W7\'s north face and W2\'s south face.', ['3.2.1', '5.1.1'],
  sedit(lambda d: SD(d, 'rooms', 'R1')['floor']['span'].update(direction=[0, 1])),
  check=lambda r: ensure(SDER(r)['spans']['R1'] == {'direction': [0, 1], 'extent': KITCHEN_NS, 'span': KITCHEN_NS}, SDER(r)))
S('derived', 'flags-absent-and-false', 'W3 says nothing of bearing, W5 says it does not bear, and W10 says it is a '
  'shear wall: `bearing` lists only the walls whose flag is true, the openings only those in them, and an absent '
  'flag is never false. A second level L2, with no walls, has empty lists. W10 and the Kitchen are flagged for an '
  'engineer.', ['5.1.1'],
  sedit(lambda d: (SD(d, 'walls', 'W3').pop('bearing'), SD(d, 'walls', 'W5').update(bearing=False),
                   SD(d, 'walls', 'W10').update(shear=True, needsEngineer=True), SD(d, 'rooms', 'R1').update(needsEngineer=True),
                   d['levels'].update(L2={'building': 'B1', 'elevation': H, 'height': H}))),
  check=lambda r: ensure(SDER(r)['levels'] == {
      'L1': {'bearing': ['W1', 'W2', 'W4', 'W6', 'W7', 'W8', 'W9'], 'shear': ['W1', 'W10', 'W2', 'W4'], 'openings': ['O1', 'O2', 'O4']},
      'L2': {'bearing': [], 'shear': [], 'openings': []}} and SDER(r)['needsEngineer'] == ['O2', 'R1', 'W10'], SDER(r)))
S('derived', 'an-opening-in-a-bearing-wall', 'W10 is said to bear: its door O3 joins the openings in L1\'s bearing '
  'walls, and has no header (FS-STRC-LINT-001).',
  ['5.1.1', '1.2.3'], sedit(lambda d: SD(d, 'walls', 'W10').update(bearing=True)),
  [('FS-STRC-LINT-001', ['O3', 'W10'])],
  check=lambda r: ensure(SDER(r)['levels']['L1']['openings'] == ['O1', 'O2', 'O3', 'O4']
                         and 'W10' in SDER(r)['levels']['L1']['bearing'], SDER(r)))


def deck_options(d):
    """Core 0.3 design options: the deck's option set OS1, with option A (OP1, the primary) keeping the
    8' x 7' deck S1, and option B (OP2) a larger deck S2, 10' x 9', on 2x10 joists spanning east-west."""
    d['floorspec'] = '0.3'
    d['optionSets'] = {'OS1': {'primary': 'OP1', 'name': 'Deck'}}
    d['options'] = {'OP1': {'set': 'OS1', 'name': 'A'}, 'OP2': {'set': 'OS1', 'name': 'B'}}
    d['slabs']['S1']['option'] = 'OP1'
    d['slabs']['S2'] = {'level': 'L1', 'boundary': [[FT, -10 * FT], [11 * FT, -10 * FT], [11 * FT, -FT], [FT, -FT]],
                        'thickness': 3 * IN // 2, 'name': 'Larger deck', 'option': 'OP2',
                        'extensions': {STRC: {'framing': joists(10), 'span': {'direction': [1, 0]}, 'needsEngineer': True}}}


S('options', 'deck-option-a', 'Deck options A and B as Core 0.3 design options (Core 19): the 8\' x 7\' deck S1 is in A, '
  'the primary, and a 10\' x 9\' deck S2 on 2x10 joists in B. FS_structural is evaluated in each checked design; the '
  'primary design is derived, with S1\'s span and not S2\'s.', ['1.2.1', '1.2.4', '1.3.2', '5.1.1', 'FS-CORE-19.3.1'],
  sedit(deck_options),
  check=lambda r: ensure(sorted(SDER(r)['spans']) == ['R1', 'S1'] and SDER(r)['needsEngineer'] == ['O2'], SDER(r)))
S('options', 'deck-option-b', 'The same document, deriving the design that chooses B (design.json): S2 spans 10\' '
  'east-west, and it is flagged for an engineer.', ['1.2.4', '5.1.1', 'FS-CORE-19.3.1'], sedit(deck_options),
  design={'OS1': 'OP2'},
  check=lambda r: ensure(SDER(r)['spans']['S2'] == {'direction': [1, 0], 'extent': 10 * FT, 'span': 10 * FT}
                         and 'S1' not in SDER(r)['spans'] and SDER(r)['needsEngineer'] == ['O2', 'S2'], SDER(r)))
S('options', 'invariant-in-option-b', 'Option B\'s deck has joists closer than they are wide: FS_structural is '
  'evaluated in each checked design, so FS-STRC-INV-002 is reported for option B\'s design, with `design`.',
  ['1.2.1', '1.2.3', '2.2.2'],
  sedit(lambda d: (deck_options(d), SD(d, 'slabs', 'S2')['framing'].update(spacing=IN))),
  [('FS-STRC-INV-002', ['S2'], 'OP2')])
S('options', 'lint-in-option-b', 'Option B\'s deck records a 12\' span across its 10\': the lint is reported for '
  'option B\'s design, with `design`.', ['1.2.3', '3.2.1'],
  sedit(lambda d: (deck_options(d), SD(d, 'slabs', 'S2')['span'].update(length=12 * FT))),
  [('FS-STRC-LINT-005', ['S2'], 'OP2')])

SO = lambda *a, **k: O(STRC, *a, **k)    # noqa: E731
SO('mark-a-wall-bearing', 'setProperty of W10 /extensions/FS_structural/bearing: W10 now bears, by an applier that '
   'implements FS_structural and knows it. Ops never judges a structure: the batch commits, and the result is valid, '
   'with its door O3 now an opening in a bearing wall with no header (FS-STRC-LINT-001, 6.1.1 is the editor\'s to act '
   'on).', ['1.2.1', '6.1.1', 'FS-OPS-2.3.1'], framed(),
   {'batch': [{'op': 'setProperty', 'id': 'W10', 'path': '/extensions/FS_structural/bearing', 'value': True}]},
   check=lambda r, B: ensure(strc_derived(B)['levels']['L1']['openings'] == ['O1', 'O2', 'O3', 'O4'], strc_derived(B)))
SO('add-a-header', 'setProperty of O3 /extensions/FS_structural/header, creating O3\'s extensions and its FS_structural '
   'data on the way (Ops 2.3): a single 2x6 header over the utility door. It commits.', ['1.2.1', '1.3.2', 'FS-OPS-2.3.1'],
   framed(), {'batch': [{'op': 'setProperty', 'id': 'O3', 'path': '/extensions/FS_structural/header',
                         'value': {'material': 'wood', 'member': TWO_BY[6]}}]},
   check=lambda r, B: ensure(B['openings']['O3']['extensions'] == {STRC: {'header': {'material': 'wood', 'member': TWO_BY[6]}}},
                             B['openings']['O3']))
SO('studs-closer-than-wide-is-rejected', 'Setting W1\'s stud spacing to 1": the result breaks 2.2.2, and an applier that '
   'implements FS_structural and knows it rejects the batch (Ops 1.2.3) with FS-STRC-INV-002.',
   ['2.2.2', '1.2.1', 'FS-OPS-1.2.3'], framed(),
   {'batch': [{'op': 'setProperty', 'id': 'W1', 'path': '/extensions/FS_structural/framing/spacing', 'value': IN}]},
   'rejected', [('FS-STRC-INV-002', ['W1'])])
SO('data-on-a-level-is-rejected', 'Setting a note on L1: the result breaks 1.3.3, and the batch is rejected with '
   'FS-STRC-SCH-001.', ['1.3.3', '1.2.1', 'FS-OPS-1.2.3'], framed(),
   {'batch': [{'op': 'setProperty', 'id': 'L1', 'path': '/extensions/FS_structural', 'value': {'note': 'Check'}}]},
   'rejected', [('FS-STRC-SCH-001', [])])
SO('move-a-wall-and-the-span-follows', 'The Kitchen\'s west wall W1 moved 1\' west: nothing in FS_structural\'s data '
   'changes, and the Kitchen\'s span, derived from its room polygon, is 1\' longer.', ['3.2.1', '5.1.1', 'FS-OPS-2.7.1',
                                                                                       'FS-OPS-4.2.1'],
   framed(), {'batch': [{'op': 'moveWall', 'wall': 'W1', 'by': "1'"}]},
   check=lambda r, B: ensure(strc_derived(B)['spans']['R1']['extent'] == KITCHEN_EW + FT
                             and B['walls']['W1']['extensions'] == framed()['walls']['W1']['extensions'], strc_derived(B)))
SO('unset-a-flag', 'unsetProperty of W2 /extensions/FS_structural/shear: W2 no longer says whether it is a shear '
   'wall, and leaves the shear walls.', ['1.2.1', 'FS-OPS-2.3.1'], framed(),
   {'batch': [{'op': 'unsetProperty', 'id': 'W2', 'path': '/extensions/FS_structural/shear'}]},
   check=lambda r, B: ensure(strc_derived(B)['levels']['L1']['shear'] == ['W1', 'W4'], strc_derived(B)))


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
        hand = sorted(tc['diags'], key=lambda x: (x['code'], x['elements'], 'design' in x, x.get('design', '')))
        problems = []
        package, design = tc.get('package'), tc.get('design')
        pd = os.path.join(d, 'package')
        if os.path.isdir(pd):
            shutil.rmtree(pd)
        for path, b in (package or {}).items():
            fp = os.path.join(pd, *path.split('/'))
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, 'wb') as f:
                f.write(b)
        dp = os.path.join(d, 'design.json')
        if design is not None:
            with open(dp, 'w') as f:
                f.write(json.dumps(design, indent=2) + '\n')
        elif os.path.exists(dp):
            os.remove(dp)
        if tc['kind'] == 'core':
            result, canonical, notes = check(data, ext_reader(data), registry, implemented, package, design)
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
            profile = ops_profile(tc['doc']).configured(registry, implemented)
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
        for name in ALL + (STRC,):
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

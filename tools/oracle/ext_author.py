"""The conformance suites of the official extensions - FS_electrical, FS_plumbing, FS_mechanical,
FS_lowvoltage, FS_furniture, FS_structural, FS_landscape, FS_lighting and FS_views 0.1.0 - as the script that writes them.

    python3.13 -m tools.oracle.ext_author            rewrite every test from its declaration below
    python3.13 -m tools.oracle.ext_author --prune    ...and delete test directories no longer declared

Each suite is conformance/ext/<NAME>/0.1.0/, run by an implementation of that one extension (a reader
of the Core draft each document declares - 0.2, or 0.3 or 0.4 for a document declaring it - that implements
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
of element. FS_landscape's start from the Phase 13 garden (garden() below) - the demo house's plan with
a walled exterior courtyard, a patio, a lawn, beds, a raised planter, trees, shrubs, a grass and a
groundcover, stepping stones and a seat wall. FS_lighting's start from the Phase 13 lit house (lit_house() below) -
the demo house's plan with FS_electrical's pendants over an island on a dimmer, tunable downlights on a smart
switch, a downlight that does not dim, a porch light, and an FS_furniture table lamp, each described as a
luminaire, and the scenes "Evening" and "Night light". FS_views's start from the lit house with four saved views
(views_house() below) - a two-point hero shot of the exterior, a two-point view of the Kitchen's island with every light
on, a view from the garden at dusk with the "Evening" scene, and a cutaway from above. Every expected diagnostic is written by hand and cross-checked against the
oracle; the derived values that matter are asserted by hand in `check`.
"""
import copy
import json
import os
import shutil
import sys

from tools.oracle.author_lib import fmt
from tools.oracle.ext import landscape as land, official
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
    T('activation', 'core-0.4-document', f'The {HOUSE[name]} declaring Core "0.4", a draft {name} 0.1.0 lists (1.1): {name} is '
      f'evaluated, reports nothing, and derives exactly what it derives for the {HOUSE[name].split()[-1]} declaring "0.2". The suite reads a '
      'document declaring "0.4" as a Core 0.4 reader.', ['1.2.1', '1.2.3', '1.2.4', DERIVE[name]],
      ed(lambda d: d.update(floorspec='0.4')), check=same_as_02(name))
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
S('activation', 'core-0.4-document', 'The framed house declaring Core "0.4", a draft FS_structural 0.1.0 lists (1.1): '
  'FS_structural is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
  ['1.2.1', '1.2.3', '1.2.4', '5.1.1'], sedit(lambda d: d.update(floorspec='0.4')), check=check_strc)

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


# ============================================================================= FS_landscape

LAND = 'FS_landscape'
CODE[LAND] = 'LAND'


def plant_box(spread_mm, height_mm, bottom_mm=0):
    """FS_landscape 3.3: a plant's box, centred on its position, planted bottom_mm above the ground."""
    s, h, b = spread_mm * MM, height_mm * MM, bottom_mm * MM
    r = s // 2
    return {'min': [-r, -r, b], 'max': [s - r, s - r, b + h]}


def free_at(x, y, rotation=None, level='L1'):
    h = {'mode': 'free', 'level': level, 'position': [x, y]}
    if rotation is not None:
        h['rotation'] = rotation
    return h


def plant(form, host, spread_mm, height_mm, bottom_mm=0, level='L1', **members):
    el = {'fallback': {'level': level, 'box': plant_box(spread_mm, height_mm, bottom_mm)}}
    if host is not None:
        el['host'] = host
    return {**el, 'form': form, **members}


def outline_box(points, z0_mm, z1_mm, grow=0):
    """FS_landscape 3.3: the box that bounds a geometry in plan, grown by `grow` on every side."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return {'min': [min(xs) - grow, min(ys) - grow, z0_mm * MM], 'max': [max(xs) + grow, max(ys) + grow, z1_mm * MM]}


def area_el(boundary, z0_mm, z1_mm, host=None, level='L1', **members):
    el = {'fallback': {'level': level, 'box': outline_box(boundary, z0_mm, z1_mm)}}
    if host is not None:
        el['host'] = host
    return {**el, 'boundary': boundary, **members}


def line_el(form, points, width, z0_mm, z1_mm, level='L1', **members):
    return {'fallback': {'level': level, 'box': outline_box(points, z0_mm, z1_mm, width // 2)},
            'form': form, 'points': points, 'width': width, **members}


def P(x, y):
    """A point in feet."""
    return [round(x * FT), round(y * FT)]


BED_WEST = [P(-4, -4), P(2, -4), P(2, -1), P(-1, -1), P(-1, 12), P(-4, 12)]
PLANTER = [P(8, -9), P(11, -9), P(11, -6), P(8, -6)]
COURT_BED = [P(-3, -3), P(3, -3), P(3, 3), P(-3, 3)]          # in the courtyard host's frame
LAWN = [P(-24, -24), P(30, -24), P(30, -12), P(-4, -12), P(-4, 18), P(-24, 18)]
STONES = [P(2, -6), P(-2, -8), P(-8, -8)]
SEAT_WALL = [P(2, -11), P(12, -11)]


def garden():
    """The Phase 13 garden: the Phase 5 demo house's plan (see demo()), 20' x 12', with no building
    systems, and a walled courtyard R4 east of it, 8' x 12', whose function is exterior:

        J2 ------ W2 ------ J3 ---- W3 ---- J4 ---- W11 ---- J9
        |                   |               |                |
        W1   Kitchen R1     W9   Bath R2    W4               |
        |                   |               |   Courtyard    W12
        |                   J7 ---- W10 --- J8      R4       |
        |                   |               |                |
        |                   W8  Utility R3  W5               |
        |                   |               |                |
        J1 ------ W7 ------ J6 ---- W6 ---- J5 ---- W13 ---- J10

    J9 (28', 12') and J10 (28', 0). A patio slab S1, 10' x 8', south of the Kitchen, and around the
    house:

    - a medium tree X1 in the lawn to the south-west (8 m across, 11 m tall, clear to 2.2 m);
    - an L-shaped bed X10 along the west wall and the patio's west end, steel-edged, with two shrubs
      (X2, X3) and a groundcover (X5);
    - a raised concrete planter X11 on the patio, 450 mm high, with an ornamental grass X4 planted in
      its soil, 400 mm up;
    - a small tree X6 in the courtyard, on R4's floor, in a 6' square bed X12 hosted at the same
      point - its outline in its host's frame;
    - a lawn X20 wrapping the house's west and south sides;
    - stepping stones X15 from the patio to the lawn, and a 450 mm concrete seat wall X16 along the
      patio's south edge."""
    d = {
        'floorspec': '0.2', 'project': {'name': 'Phase 13 garden'},
        'buildings': {'B1': {}}, 'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
        'types': {'WT': {'kind': 'wallType', 'layers': [{'thickness': 100 * MM, 'function': 'core'}]}},
        'junctions': {'J1': J(0, 0), 'J2': J(0, 12 * FT), 'J3': J(12 * FT, 12 * FT), 'J4': J(20 * FT, 12 * FT),
                      'J5': J(20 * FT, 0), 'J6': J(12 * FT, 0), 'J7': J(12 * FT, 6 * FT), 'J8': J(20 * FT, 6 * FT),
                      'J9': J(28 * FT, 12 * FT), 'J10': J(28 * FT, 0)},
        'walls': {'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J8'),
                  'W5': W('J8', 'J5'), 'W6': W('J5', 'J6'), 'W7': W('J6', 'J1'), 'W8': W('J6', 'J7'),
                  'W9': W('J7', 'J3'), 'W10': W('J7', 'J8'),
                  'W11': W('J4', 'J9'), 'W12': W('J9', 'J10'), 'W13': W('J10', 'J5')},
        'rooms': {'R1': {'level': 'L1', 'anchor': [6 * FT, 6 * FT], 'name': 'Kitchen', 'function': 'kitchen'},
                  'R2': {'level': 'L1', 'anchor': [16 * FT, 9 * FT], 'name': 'Bath', 'function': 'bath'},
                  'R3': {'level': 'L1', 'anchor': [16 * FT, 3 * FT], 'name': 'Utility', 'function': 'mechanical'},
                  'R4': {'level': 'L1', 'anchor': [24 * FT, 6 * FT], 'name': 'Courtyard', 'function': 'exterior'}},
        'slabs': {'S1': {'level': 'L1', 'boundary': [P(2, -10), P(12, -10), P(12, -1), P(2, -1)],
                         'thickness': 100 * MM, 'name': 'Patio'}},
        'extensionsUsed': {LAND: '0.1.0'},
        'extensions': {LAND: {'collections': {
            'plants': {
                'X1': plant('tree', free_at(-14 * FT, -6 * FT), 8000, 11000, clearHeight=2200 * MM, habit='spreading',
                            foliage='deciduous', species='Acer rubrum', commonName='Red maple', catalogue='tree-medium'),
                'X2': plant('shrub', free_at(-30 * FT // 12, 6 * FT), 1200, 1200, foliage='evergreen', catalogue='shrub-medium'),
                'X3': plant('shrub', free_at(-30 * FT // 12, 2 * FT), 600, 500, catalogue='shrub-small'),
                'X4': plant('grass', free_at(19 * FT // 2, -15 * FT // 2), 900, 900, 400, catalogue='grass-medium'),
                'X5': plant('groundcover', free_at(FT // 2, -5 * FT // 2), 900, 200),
                'X6': plant('tree', {'mode': 'surface', 'room': 'R4', 'surface': 'floor', 'position': [24 * FT, 6 * FT]},
                            4500, 6000, clearHeight=1500 * MM, habit='rounded', name='Courtyard tree')},
            'beds': {
                'X10': area_el(BED_WEST, -100, 25, edging='steel', cover='bark'),
                'X11': area_el(PLANTER, 0, 450, cover='soil', edging='concrete', name='Patio planter'),
                'X12': area_el(COURT_BED, -100, 25, {'mode': 'surface', 'room': 'R4', 'surface': 'floor', 'position': [24 * FT, 6 * FT]},
                               edging='stone')},
            'lawns': {'X20': area_el(LAWN, -50, 10)},
            'hardscape': {
                'X15': line_el('steppingStones', STONES, 600 * MM, -30, 15, material='stone'),
                'X16': line_el('wall', SEAT_WALL, 300 * MM, 0, 450, material='concrete', name='Seat wall')}}}},
    }
    return copy.deepcopy(d)          # the shared outlines and lines are never edited in place


def ledit(fn):
    """The Phase 13 garden, changed by fn(d) in place."""
    d = garden()
    fn(d)
    return d


LK = lambda d, c: coll(d, LAND, c)                                                 # noqa: E731
PL = lambda d: LK(d, 'plants')                                                     # noqa: E731
BD = lambda d: LK(d, 'beds')                                                       # noqa: E731
HS = lambda d: LK(d, 'hardscape')                                                  # noqa: E731
LDER = derived_of(LAND)
L_ = lambda *a, **k: V(LAND, *a, **k)    # noqa: E731


GARDEN_PLANTS = {
    'X1': {'form': 'tree', 'size': 'medium', 'spread': 8000 * MM, 'height': 11000 * MM, 'position': [-14 * FT, -6 * FT]},
    'X2': {'form': 'shrub', 'size': 'medium', 'spread': 1200 * MM, 'height': 1200 * MM, 'position': [-30 * FT // 12, 6 * FT]},
    'X3': {'form': 'shrub', 'size': 'small', 'spread': 600 * MM, 'height': 500 * MM, 'position': [-30 * FT // 12, 2 * FT]},
    'X4': {'form': 'grass', 'size': 'medium', 'spread': 900 * MM, 'height': 900 * MM, 'position': [19 * FT // 2, -15 * FT // 2]},
    'X5': {'form': 'groundcover', 'size': 'medium', 'spread': 900 * MM, 'height': 200 * MM, 'position': [FT // 2, -5 * FT // 2]},
    'X6': {'form': 'tree', 'size': 'small', 'spread': 4500 * MM, 'height': 6000 * MM, 'position': [24 * FT, 6 * FT], 'room': 'R4'},
}


def check_land(r):
    x = LDER(r)
    ensure(x['plants'] == GARDEN_PLANTS, x['plants'])
    # the L-shaped bed: 6' x 3' along the patio's west end and 3' x 13' up the west wall, less their overlap
    ensure(x['beds'] == {'X10': {'area': str((6 * 3 + 3 * 13) * FT * FT), 'plants': ['X2', 'X3', 'X5']},
                         'X11': {'area': str(3 * 3 * FT * FT), 'plants': ['X4']},
                         'X12': {'area': str(6 * 6 * FT * FT), 'plants': ['X6']}}, x['beds'])
    ensure(x['lawns'] == {'X20': {'area': str((54 * 12 + 20 * 30) * FT * FT)}}, x['lawns'])
    # sqrt(4'^2 + 2'^2), rounded once, then 6' exactly; and 10'
    ensure(x['hardscape'] == {'X15': {'form': 'steppingStones', 'length': land._round_sqrt(20 * FT * FT) + 6 * FT},
                              'X16': {'form': 'wall', 'length': 10 * FT}}, x['hardscape'])


ON_WALL = {'mode': 'wallFace', 'wall': 'W7', 'side': 'left', 'offset': 3 * FT, 'height': 0}
BAD_L = lambda d: PL(d)['X1'].update(form='palm')                                 # noqa: E731  the schema tier
INV_L = lambda d: PL(d)['X1'].pop('host')                                         # noqa: E731  FS-LAND-INV-002
INV_L_DIAG = [('FS-LAND-INV-002', ['X1'])]
COURT_HOST = {'mode': 'surface', 'room': 'R4', 'surface': 'floor', 'position': [24 * FT, 6 * FT]}

L_('examples', 'p13-garden', 'The Phase 13 garden, read by an implementation of FS_landscape that knows it: a medium '
   'tree in the lawn, a steel-edged bed with two shrubs and a groundcover along the west wall, a raised concrete planter '
   'on the patio with a grass planted in its soil, a small tree in a bed in the walled courtyard - both hosted on the '
   'courtyard\'s floor, the bed\'s outline in its host\'s frame - a lawn, stepping stones and a seat wall. It is valid, '
   'reports nothing - the grass on the patio stands in its planter, and the courtyard is exterior - and derives each '
   'plant\'s form, size class, spread, height, position and room, each bed\'s area and the plants in it, the lawn\'s '
   'area and each hardscape line\'s length.',
   ['1.2.1', '1.2.3', '1.2.4', '1.3.1', '6.1.1'], garden(), check=check_land)
L_('examples', 'core-only-reader', 'The same garden read with no known extensions: FS_landscape is not evaluated, so '
   'nothing of it is derived (`derived.extensions` is empty) - only what Core derives from every element\'s fallback '
   'and host (Core 1.6.9): each one\'s box, and the placements of the hosted ones.',
   ['1.2.1', '1.2.4', 'FS-CORE-1.6.9', 'FS-CORE-12.6.2', 'FS-CORE-13.4.1'], garden(), registry=None,
   check=lambda r: ensure(r['derived']['extensions'] == {} and sorted(r['derived']['fallbacks'])
                          == ['X1', 'X10', 'X11', 'X12', 'X15', 'X16', 'X2', 'X20', 'X3', 'X4', 'X5', 'X6']
                          and r['derived']['placements']['X6']['point'] == [24 * FT, 6 * FT, 0]
                          and 'X10' not in r['derived']['placements'], r['derived']['extensions']))
L_('examples', 'all-official-known', 'The garden read with every official entry known, by an implementation of '
   'FS_landscape alone: only FS_landscape is evaluated and derived.', ['1.2.1', '1.2.4'], garden(),
   registry=[entry(x) for x in ALL + (STRC, LAND)],
   check=lambda r: ensure(list(r['derived']['extensions']) == [LAND], list(r['derived']['extensions'])))
L_('examples', 'no-elements', 'FS_landscape used with empty top-level data: valid, and every derived member empty.',
   ['1.3.1', '6.1.1'], ledit(lambda d: d['extensions'].update({LAND: {}})),
   check=lambda r: ensure(LDER(r) == {'plants': {}, 'beds': {}, 'lawns': {}, 'hardscape': {}}, LDER(r)))

L_('activation', 'unknown-data-not-evaluated', 'The tree\'s form is "palm", which FS_landscape\'s schema does not '
   'allow, but no extension is known: nothing of it is evaluated, and the document is valid.', ['1.2.1'],
   ledit(BAD_L), registry=None)
L_('activation', 'another-version-known', 'The document uses FS_landscape at 0.2.0, which is known (a later entry), but '
   'the implementation implements 0.1.0: not evaluated, so the data that breaks 0.1.0\'s schema is not reported.',
   ['1.2.1'], ledit(lambda d: (BAD_L(d), d['extensionsUsed'].update({LAND: '0.2.0'}))), registry=[entry(LAND, '0.2.0')])
L_('activation', 'version-without-patch', '"0.1" equals 0.1.0 (Core 12.3), so FS_landscape is evaluated: its data '
   'breaks the schema, FS-LAND-SCH-001.', ['1.2.1', '1.3.1'],
   ledit(lambda d: (BAD_L(d), d['extensionsUsed'].update({LAND: '0.1'}))), [('FS-LAND-SCH-001', [])])
L_('activation', 'declaration-object', 'A declaration object with a schema URI is its version string (Core 12.1.3): '
   'FS_landscape is evaluated.', ['1.2.1', '1.3.1'],
   ledit(lambda d: (BAD_L(d), d['extensionsUsed'].update({LAND: {'version': '0.1.0', 'schema': entry(LAND)['schema']}}))),
   [('FS-LAND-SCH-001', [])])
L_('activation', 'core-0.1-document', 'A document declaring "0.1" has no extension elements and its extension data is '
   'opaque (Core 1.2.4): FS_landscape is not evaluated, even though it is known.', ['1.2.1'],
   {'floorspec': '0.1', 'project': {'name': 'Old'}, 'extensionsUsed': {LAND: '0.1.0'}, 'extensions': {LAND: {'colour': 'red'}}})
L_('activation', 'core-0.3-document', 'The garden declaring Core "0.3", a draft FS_landscape 0.1.0 lists (1.1): '
   'FS_landscape is evaluated, reports nothing, and derives exactly what it derives for the garden declaring "0.2".',
   ['1.2.1', '1.2.3', '1.2.4', '6.1.1'], ledit(lambda d: d.update(floorspec='0.3')), check=check_land)
L_('activation', 'core-0.3-invariants', 'The same "0.3" garden with its tree unhosted: FS_landscape is evaluated for a '
   'Core 0.3 document, so the invariant is reported.', ['1.2.1', '1.2.3', '3.2.1'],
   ledit(lambda d: (d.update(floorspec='0.3'), INV_L(d))), INV_L_DIAG)
L_('activation', 'core-0.4-document', 'The garden declaring Core "0.4", a draft FS_landscape 0.1.0 lists (1.1): '
   'FS_landscape is evaluated, reports nothing, and derives exactly what it derives for the garden declaring "0.2".',
   ['1.2.1', '1.2.3', '1.2.4', '6.1.1'], ledit(lambda d: d.update(floorspec='0.4')), check=check_land)

L_('order', 'core-error-first', 'A Core invariant breaks - the courtyard tree\'s floor position is outside the '
   'courtyard - and so does FS_landscape\'s schema: Core\'s error is reported, and FS_landscape is not evaluated.',
   ['1.2.2'], ledit(lambda d: (BAD_L(d), PL(d)['X6']['host'].update(position=[32 * FT, 6 * FT]))),
   [('FS-INV-503', ['X6'])])
L_('order', 'schema-before-invariants', 'The data breaks the schema and an invariant: only FS-LAND-SCH-001.',
   ['1.2.2', '1.3.1'], ledit(lambda d: (BAD_L(d), PL(d)['X2'].pop('host'))), [('FS-LAND-SCH-001', [])])
L_('order', 'no-lints-when-invalid', 'An invariant breaks and a lint would apply too - the grass is moved out of its '
   'planter, onto the patio: the document is invalid, so no lint is reported, FS_landscape\'s or Core\'s.',
   ['1.2.2', '1.2.3'], ledit(lambda d: (INV_L(d), PL(d)['X4']['host'].update(position=[4 * FT, -3 * FT]))), INV_L_DIAG)

L_('schema', 'data-not-an-object', 'FS_landscape\'s top-level data is an array: Core allows any JSON there, '
   'FS_landscape\'s schema does not.', ['1.3.1'], ledit(lambda d: d['extensions'].update({LAND: []})),
   [('FS-LAND-SCH-001', [])])
L_('schema', 'unknown-collection', 'A collection FS_landscape does not define, `ponds`, with no element in it: '
   'FS_landscape\'s registry entry names no such kind, so Core 12.4.1 reports it (FS-INV-604), and FS_landscape is '
   'not evaluated.', ['1.2.2', 'FS-CORE-12.4.1'], ledit(lambda d: ext(d, LAND)['collections'].update(ponds={})),
   [('FS-INV-604', [])])
L_('schema', 'bed-with-an-unknown-member', 'A bed has a member a bed does not define: `depth`.', ['1.3.1'],
   ledit(lambda d: BD(d)['X10'].update(depth=300 * MM)), [('FS-LAND-SCH-001', [])])
L_('schema', 'unknown-member', 'A plant has a member a plant does not define.', ['1.3.1'],
   ledit(lambda d: PL(d)['X1'].update(colour='red')), [('FS-LAND-SCH-001', [])])
L_('schema', 'form-not-known', 'A plant whose form is "palm".', ['1.3.1'], ledit(BAD_L), [('FS-LAND-SCH-001', [])])
L_('schema', 'plant-without-a-form', 'A plant always says what kind of plant it is.', ['1.3.1'],
   ledit(lambda d: PL(d)['X3'].pop('form')), [('FS-LAND-SCH-001', [])])
L_('schema', 'species-too-long', 'A species is a label of 1 to 200 characters.', ['1.3.1'],
   ledit(lambda d: PL(d)['X1'].update(species='A' * 201)), [('FS-LAND-SCH-001', [])])
L_('schema', 'boundary-of-two-points', 'A bed\'s outline is a polygon: at least three points.', ['1.3.1'],
   ledit(lambda d: BD(d)['X11'].update(boundary=PLANTER[:2])), [('FS-LAND-SCH-001', [])])
L_('schema', 'point-of-three-numbers', 'A point is two lengths.', ['1.3.1'],
   ledit(lambda d: HS(d)['X15']['points'][0].append(0)), [('FS-LAND-SCH-001', [])])
L_('schema', 'width-below-a-millimetre', 'A hardscape line is at least 1 mm wide.', ['1.3.1'],
   ledit(lambda d: HS(d)['X16'].update(width=1279)), [('FS-LAND-SCH-001', [])])
L_('schema', 'line-of-one-point', 'A hardscape line has at least two points.', ['1.3.1'],
   ledit(lambda d: HS(d)['X16'].update(points=SEAT_WALL[:1])), [('FS-LAND-SCH-001', [])])
L_('schema', 'length-with-a-fraction', 'A length written with a fraction is not an integer, even when it is a whole '
   'number.', ['1.3.1'], None, [('FS-LAND-SCH-001', [])],
   raw=(fmt(garden()) + '\n').replace('"width": 384000', '"width": 384000.0', 1).encode('utf-8'))
L_('schema', 'edging-not-known', 'A bed edged with "hedge", which is no edging of this version.', ['1.3.1'],
   ledit(lambda d: BD(d)['X10'].update(edging='hedge')), [('FS-LAND-SCH-001', [])])

L_('invariants', 'plant-on-a-wall-face', 'The tree hosted on the south wall\'s outer face: a plant stands on the '
   'ground, never on a wall.', ['3.2.2'], ledit(lambda d: PL(d)['X1'].update(host=ON_WALL)), [('FS-LAND-INV-001', ['X1'])])
L_('invariants', 'bed-on-a-ceiling', 'The courtyard bed hosted on the Kitchen\'s ceiling.', ['3.2.2'],
   ledit(lambda d: BD(d)['X12'].update(host={'mode': 'surface', 'room': 'R1', 'surface': 'ceiling', 'position': [6 * FT, 6 * FT]})),
   [('FS-LAND-INV-001', ['X12'])])
L_('invariants', 'plant-without-a-host', 'The tree has no host: a plant stands at its host\'s position.', ['3.2.1'],
   ledit(INV_L), INV_L_DIAG)
L_('invariants', 'path-on-a-wall-face', 'The stepping stones hosted on a wall face.', ['3.2.2'],
   ledit(lambda d: HS(d)['X15'].update(host=ON_WALL)), [('FS-LAND-INV-001', ['X15'])])
L_('invariants', 'lawn-hosted-free', 'The lawn placed with a free host at the level\'s origin: its outline is in that '
   'frame, which is the level\'s own. Valid, and its area is unchanged.', ['3.2.2', '6.1.1'],
   ledit(lambda d: LK(d, 'lawns')['X20'].update(host=free_at(0, 0))),
   check=lambda r: ensure(LDER(r)['lawns'] == {'X20': {'area': str((54 * 12 + 20 * 30) * FT * FT)}}, LDER(r)))
L_('invariants', 'clear-height-equal-to-height', 'The courtyard tree\'s canopy starts 6 m up, at its top.', ['2.2.1'],
   ledit(lambda d: PL(d)['X6'].update(clearHeight=6000 * MM)), [('FS-LAND-INV-003', ['X6'])])
L_('invariants', 'clear-height-just-under-height', 'The courtyard tree\'s canopy starts one base unit under its top: '
   'valid.', ['2.2.1'], ledit(lambda d: PL(d)['X6'].update(clearHeight=6000 * MM - 1)))
L_('invariants', 'clear-height-of-a-planted-grass', 'The grass in the planter, 900 mm tall and planted 400 mm up, '
   'clear to 899 mm: the height is the box\'s extent, not its top. Valid.', ['2.2.1'],
   ledit(lambda d: PL(d)['X4'].update(clearHeight=899 * MM)))
L_('invariants', 'self-crossing-bed', 'The planter\'s outline crosses itself: a bow tie.', ['3.4.1'],
   ledit(lambda d: BD(d)['X11'].update(boundary=[P(8, -9), P(11, -6), P(11, -9), P(8, -6)])), [('FS-LAND-INV-004', ['X11'])])
L_('invariants', 'bed-with-a-repeated-vertex', 'The planter\'s outline repeats a vertex.', ['3.4.1'],
   ledit(lambda d: BD(d)['X11'].update(boundary=PLANTER + [PLANTER[0]])), [('FS-LAND-INV-004', ['X11'])])
L_('invariants', 'collinear-lawn', 'The lawn\'s outline is three points on a line: no area.', ['3.4.1'],
   ledit(lambda d: LK(d, 'lawns')['X20'].update(boundary=[P(-24, -24), P(0, -24), P(30, -24)])), [('FS-LAND-INV-004', ['X20'])])
L_('invariants', 'path-with-a-repeated-point', 'The stepping stones\' line repeats its middle point.', ['3.4.2'],
   ledit(lambda d: HS(d)['X15'].update(points=[STONES[0], STONES[1], STONES[1], STONES[2]])), [('FS-LAND-INV-005', ['X15'])])
L_('invariants', 'path-that-loops', 'A path that comes back to where it started and crosses itself is a line, not an '
   'outline: valid, and its length is every segment\'s.', ['3.4.2', '6.1.1'],
   ledit(lambda d: HS(d)['X15'].update(points=[P(-8, -8), P(-2, -8), P(-2, -14), P(-6, -14), P(-6, -6)],
                                       fallback={'level': 'L1', 'box': outline_box([P(-8, -8), P(-2, -14), P(-6, -6)], -30, 15, 300 * MM)})),
   check=lambda r: ensure(LDER(r)['hardscape']['X15'] == {'form': 'steppingStones', 'length': 24 * FT}, LDER(r)['hardscape']))
L_('invariants', 'every-one-once', 'Five elements break five rules at once: each is reported once, naming its '
   'element.', ['1.2.3', '2.2.1', '3.2.1', '3.2.2', '3.4.1', '3.4.2'],
   ledit(lambda d: (INV_L(d), PL(d)['X2'].update(host=ON_WALL), PL(d)['X6'].update(clearHeight=7000 * MM),
                    BD(d)['X11'].update(boundary=PLANTER + [PLANTER[2]]),
                    HS(d)['X16'].update(points=SEAT_WALL + [SEAT_WALL[1]]))),
   [('FS-LAND-INV-001', ['X2']), ('FS-LAND-INV-002', ['X1']), ('FS-LAND-INV-003', ['X6']), ('FS-LAND-INV-004', ['X11']),
    ('FS-LAND-INV-005', ['X16'])])

L_('lints', 'plant-box-off-its-position', 'The tree\'s box is drawn wholly east of its position: a reader without '
   'FS_landscape draws it in the wrong place.', ['1.2.3', '3.3.1'],
   ledit(lambda d: PL(d)['X1']['fallback'].update(box={'min': [MM, -4000 * MM, 0], 'max': [8000 * MM, 4000 * MM, 11000 * MM]})),
   [('FS-LAND-LINT-001', ['X1'])])
L_('lints', 'bed-outside-its-box', 'The bed\'s box stops a foot short of its west edge.', ['1.2.3', '3.3.2'],
   ledit(lambda d: BD(d)['X10']['fallback']['box']['min'].__setitem__(0, -3 * FT)), [('FS-LAND-LINT-001', ['X10'])])
L_('lints', 'path-grown-past-its-box', 'The seat wall\'s box is its line grown by 100 mm, not by half its 300 mm '
   'width.', ['1.2.3', '3.3.2'],
   ledit(lambda d: HS(d)['X16']['fallback'].update(box=outline_box(SEAT_WALL, 0, 450, 100 * MM))),
   [('FS-LAND-LINT-001', ['X16'])])
L_('lints', 'path-exactly-in-its-box', 'The seat wall\'s box is exactly its line grown by 150 mm: no lint.', ['1.2.3'],
   ledit(lambda d: HS(d)['X16']['fallback'].update(box=outline_box(SEAT_WALL, 0, 450, 150 * MM))))
L_('lints', 'tree-on-the-patio', 'A third tree X7 planted in the middle of the patio, in no bed: a plant on paving.',
   ['1.2.3'], ledit(lambda d: PL(d).update(X7=plant('tree', free_at(5 * FT, -5 * FT), 4500, 6000))),
   [('FS-LAND-LINT-002', ['S1', 'X7'])])
L_('lints', 'grass-out-of-its-planter', 'The grass moved out of its planter onto the patio.', ['1.2.3'],
   ledit(lambda d: PL(d)['X4']['host'].update(position=[4 * FT, -3 * FT])), [('FS-LAND-LINT-002', ['S1', 'X4'])])
L_('lints', 'plant-on-the-patio-edge', 'A shrub whose position is on the patio\'s edge is not strictly inside it: no '
   'lint.', ['1.2.3'], ledit(lambda d: PL(d).update(X7=plant('shrub', free_at(12 * FT, -5 * FT), 600, 500))))
L_('lints', 'tree-in-the-kitchen', 'A tree X7 standing on the Kitchen\'s floor: a plant indoors.', ['1.2.3'],
   ledit(lambda d: PL(d).update(X7=plant('tree', {'mode': 'surface', 'room': 'R1', 'surface': 'floor',
                                                   'position': [6 * FT, 6 * FT]}, 1500, 2400))),
   [('FS-LAND-LINT-003', ['R1', 'X7'])])
L_('lints', 'free-plant-in-a-room-without-a-function', 'A shrub standing free on L1 inside the Utility room, which '
   'has no function once its own is removed: not exterior, so a plant indoors.', ['1.2.3'],
   ledit(lambda d: (d['rooms']['R3'].pop('function'), PL(d).update(X7=plant('shrub', free_at(17 * FT, 2 * FT), 600, 500)))),
   [('FS-LAND-LINT-003', ['R3', 'X7'])])
L_('lints', 'every-lint-once', 'The tree\'s box off its position, a tree on the patio and a shrub in the Bath: each '
   'lint once.', ['1.2.3'],
   ledit(lambda d: (PL(d)['X1']['fallback'].update(box={'min': [MM, -4000 * MM, 0], 'max': [8000 * MM, 4000 * MM, 11000 * MM]}),
                    PL(d).update(X7=plant('tree', free_at(5 * FT, -5 * FT), 4500, 6000)),
                    PL(d).update(X8=plant('shrub', free_at(16 * FT, 9 * FT), 600, 500)))),
   [('FS-LAND-LINT-001', ['X1']), ('FS-LAND-LINT-002', ['S1', 'X7']), ('FS-LAND-LINT-003', ['R2', 'X8'])])

L_('derived', 'size-class-bounds', 'Trees 8,000 mm less one base unit, 8,000 mm and 14,000 mm tall, and a '
   'groundcover 150 mm tall: small, medium, large and medium (2.3). The class follows the box\'s height, planted at '
   'any height.', ['6.1.1'],
   ledit(lambda d: PL(d).update(
       X7=plant('tree', free_at(-20 * FT, -20 * FT), 4000, 8000, level='L1'),
       X8=plant('tree', free_at(20 * FT, -20 * FT), 4000, 14000, 300),
       X9=plant('groundcover', free_at(0, -20 * FT), 900, 150),
       X1=PL(d)['X1'] | {'fallback': {'level': 'L1', 'box': {'min': [-4000 * MM, -4000 * MM, 0], 'max': [4000 * MM, 4000 * MM, 8000 * MM - 1]}}})),
   check=lambda r: ensure([LDER(r)['plants'][k]['size'] for k in ('X1', 'X7', 'X8', 'X9')] == ['small', 'medium', 'large', 'medium'],
                          LDER(r)['plants']))
L_('derived', 'spread-is-the-greater-extent', 'A shrub clipped to an oval, 1,800 mm along x and 900 mm along y: its '
   'spread is 1,800 mm.', ['6.1.1'],
   ledit(lambda d: PL(d)['X2']['fallback'].update(box={'min': [-900 * MM, -450 * MM, 0], 'max': [900 * MM, 450 * MM, 1200 * MM]})),
   check=lambda r: ensure(LDER(r)['plants']['X2']['spread'] == 1800 * MM, LDER(r)['plants']['X2']))
L_('derived', 'courtyard-turned', 'The courtyard bed\'s host turned by 45 degrees: its outline turns with it, about '
   'its host\'s position, each corner rounded once - the diamond\'s area is close to, and not exactly, the square\'s '
   '- and the tree at its centre is still in it.', ['3.4.1', '6.1.1'],
   ledit(lambda d: BD(d)['X12']['host'].update(rotation=45000000)),
   check=lambda r: ensure(LDER(r)['beds']['X12']['plants'] == ['X6']
                          and abs(float(LDER(r)['beds']['X12']['area']) - 36 * FT * FT) < 24 * FT
                          and LDER(r)['beds']['X12']['area'] != str(36 * FT * FT), LDER(r)['beds']['X12']))
L_('derived', 'plant-on-a-bed-edge', 'A shrub whose position is on the west bed\'s edge is not in the bed; one a base '
   'unit inside it is.', ['6.1.1'],
   ledit(lambda d: PL(d).update(X7=plant('shrub', free_at(-4 * FT, 0), 600, 500),
                                X8=plant('shrub', free_at(-4 * FT + 1, 1), 600, 500))),
   check=lambda r: ensure(LDER(r)['beds']['X10']['plants'] == ['X2', 'X3', 'X5', 'X8'], LDER(r)['beds']['X10']))
L_('derived', 'bed-inside-a-lawn', 'A bed X13 laid inside the lawn: the lawn\'s area is its outline\'s, the bed\'s '
   'not taken from it (2.5).', ['6.1.1'],
   ledit(lambda d: BD(d).update(X13=area_el([P(-20, -20), P(-16, -20), P(-16, -16), P(-20, -16)], -100, 25))),
   check=lambda r: ensure(LDER(r)['lawns'] == {'X20': {'area': str((54 * 12 + 20 * 30) * FT * FT)}}
                          and LDER(r)['beds']['X13'] == {'area': str(16 * FT * FT), 'plants': []}, LDER(r)))
L_('derived', 'length-of-a-diagonal', 'A path along [1 mm, 1 mm] then [3, 4] base units: sqrt 2 mm is 1810.19... '
   'base units, rounded to 1810, and 5 exactly - each segment rounded once.', ['6.1.1'],
   ledit(lambda d: HS(d).update(X17=line_el('path', [[0, -20 * FT], [MM, -20 * FT + MM], [MM + 3, -20 * FT + MM + 4]], 900 * MM, -30, 15))),
   check=lambda r: ensure(LDER(r)['hardscape']['X17'] == {'form': 'path', 'length': 1810 + 5}, LDER(r)['hardscape']))


def court_options(d):
    """Core 0.3 design options for the courtyard: option A (OP1, the primary) keeps the small tree X6;
    option B (OP2) plants a columnar tree X7 in its place."""
    d['floorspec'] = '0.3'
    d['optionSets'] = {'OS1': {'primary': 'OP1', 'name': 'Courtyard tree'}}
    d['options'] = {'OP1': {'set': 'OS1', 'name': 'A'}, 'OP2': {'set': 'OS1', 'name': 'B'}}
    PL(d)['X6']['option'] = 'OP1'
    PL(d)['X7'] = plant('tree', dict(COURT_HOST), 2000, 9000, clearHeight=1200 * MM, habit='columnar', option='OP2')


L_('options', 'courtyard-option-a', 'Courtyard options A and B as Core 0.3 design options (Core 19): the small tree '
   'in A, the primary, and a columnar tree 9 m tall in B. FS_landscape\'s data matches its schema with the elements\' '
   '`option` members, and it is evaluated in each checked design; the primary design is derived, with A\'s tree.',
   ['1.2.1', '1.2.4', '1.3.1', '6.1.1', 'FS-CORE-19.3.1'], ledit(court_options),
   check=lambda r: ensure('X6' in LDER(r)['plants'] and 'X7' not in LDER(r)['plants'] and LDER(r)['beds']['X12']['plants'] == ['X6'],
                          LDER(r)['plants']))
L_('options', 'courtyard-option-b', 'The same document, deriving the design that chooses B (design.json): the '
   'columnar tree, a medium tree by its height, in the courtyard bed.', ['1.2.4', '6.1.1', 'FS-CORE-19.3.1'],
   ledit(court_options), design={'OS1': 'OP2'},
   check=lambda r: ensure(LDER(r)['plants']['X7']['size'] == 'medium' and 'X6' not in LDER(r)['plants']
                          and LDER(r)['beds']['X12']['plants'] == ['X7'], LDER(r)['plants']))
L_('options', 'invariant-in-option-b', 'Option B\'s tree is clear to above its top: FS-LAND-INV-003 is reported for '
   'option B\'s design, with `design`.', ['1.2.1', '1.2.3', '2.2.1'],
   ledit(lambda d: (court_options(d), PL(d)['X7'].update(clearHeight=9500 * MM))), [('FS-LAND-INV-003', ['X7'], 'OP2')])


def land_derived(d):
    data = json.dumps(d).encode('utf-8')
    result, _, _ = check(data, ext_reader(data), json.dumps([entry(LAND)]).encode('utf-8'), official.implemented(LAND))
    assert result['valid'], result['diagnostics']
    return result['derived']['extensions'][LAND]


TREE_M = {'form': 'tree', 'catalogue': 'tree-medium', 'name': 'Medium tree', 'clearHeight': 2200 * MM,
          'fallback': {'box': plant_box(8000, 11000)}}

LO = lambda *a, **k: O(LAND, *a, **k)    # noqa: E731
LO('place-a-tree', 'The garden; placeElement puts the starter size tree-medium (chapter 7) in the lawn with a free '
   'host 20\' west and 2\' south of the house\'s south-west corner. It commits, valid under FS_landscape: a medium tree '
   'in no room.', ['1.2.1', '3.2.1', 'FS-OPS-4.10.1'], garden(),
   {'batch': [{'op': 'placeElement', 'extension': LAND, 'collection': 'plants', 'id': 'X7',
               'host': {'mode': 'free', 'level': 'L1', 'at': ["-20'", "-2'"]}, 'element': TREE_M}]},
   check=lambda r, B: ensure(land_derived(B)['plants']['X7'] == {'form': 'tree', 'size': 'medium', 'spread': 8000 * MM,
                                                                  'height': 11000 * MM, 'position': [-20 * FT, -2 * FT]}
                             and PL(B)['X7']['fallback']['level'] == 'L1', PL(B)['X7']))
LO('move-the-tree-into-the-courtyard', 'moveElement moves the lawn\'s tree onto the courtyard\'s floor: it is now in '
   'R4, an exterior room, and in the courtyard bed beside the small tree.', ['1.2.1', '6.1.1', 'FS-OPS-4.10.1'], garden(),
   {'batch': [{'op': 'moveElement', 'element': 'X1',
               'host': {'mode': 'surface', 'room': 'Courtyard', 'surface': 'floor', 'at': ["25'", "7'"]}}]},
   check=lambda r, B: ensure(land_derived(B)['plants']['X1'].get('room') == 'R4'
                             and land_derived(B)['beds']['X12']['plants'] == ['X1', 'X6'], land_derived(B)['beds']))
LO('plant-on-a-wall-is-rejected', 'placeElement of a shrub on the south wall\'s outer face: the result breaks 3.2.2, '
   'and an applier that implements FS_landscape and knows it rejects the batch (Ops 1.2.3).',
   ['3.2.2', '1.2.1', 'FS-OPS-1.2.3'], garden(),
   {'batch': [{'op': 'placeElement', 'extension': LAND, 'collection': 'plants', 'id': 'X7',
               'host': {'mode': 'wallFace', 'wall': 'W7', 'side': 'left', 'at': "3'", 'height': 0},
               'element': {'form': 'shrub', 'fallback': {'box': plant_box(600, 500)}}}]},
   'rejected', [('FS-LAND-INV-001', ['X7'])])
LO('move-the-courtyard-bed', 'moveElement moves the courtyard bed and its tree 1\' east on the courtyard\'s floor, '
   'in one batch: the bed\'s outline, in its host\'s frame, is unchanged and moves with it, and the tree still stands '
   'in it. It commits.', ['3.4.1', '6.1.1', 'FS-OPS-4.10.1'], garden(),
   {'batch': [{'op': 'moveElement', 'element': 'X12', 'host': {'mode': 'surface', 'room': 'R4', 'surface': 'floor', 'at': ["25'", "6'"]}},
              {'op': 'moveElement', 'element': 'X6', 'host': {'mode': 'surface', 'room': 'R4', 'surface': 'floor', 'at': ["25'", "6'"]}}]},
   check=lambda r, B: ensure(land_derived(B)['beds']['X12']['plants'] == ['X6']
                             and BD(B)['X12']['boundary'] == COURT_BED, BD(B)['X12']))


# ============================================================================= FS_lighting

LGHT = 'FS_lighting'
CODE[LGHT] = 'LGHT'
PENDANT = box(-150, -150, -900, 150, 150, 0)
DOWNLIGHT = box(-100, -100, -150, 100, 100, 0)


def lit_house():
    """The Phase 13 lit house: the Phase 5 demo house's plan (see demo()), with a Living room R2 where
    the Bath was, and the house's lighting on one circuit C1 of the panel X1:

    - a pair of pendants X2 and X3 over the Kitchen's island, on a dimmer X10;
    - recessed tunable-white downlights X4 and X5 in the Kitchen, on a smart switch X11;
    - a recessed downlight X6 in the Living room, on a single switch X12, that does not dim;
    - an exterior light X7 on the south wall's outer face, on a single switch X13 inside the Kitchen;
    - a table lamp X20 of FS_furniture in the Living room, the starter library's lamp-table-600,
      plugged in and on no switch.

    FS_lighting describes what each gives and two scenes: LS1 "Evening" - the pendants at 60 %, the
    downlights at 40 % and warm, the exterior light and the lamp at full - and LS2 "Night light" -
    one pendant at 10 % and the lamp at 20 %. The Living room's downlight is in neither."""
    d = {
        'floorspec': '0.2', 'project': {'name': 'Phase 13 lit house'},
        'buildings': {'B1': {}}, 'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
        'types': {'WT': {'kind': 'wallType', 'layers': [{'thickness': 100 * MM, 'function': 'core'}]}},
        'junctions': {'J1': J(0, 0), 'J2': J(0, 12 * FT), 'J3': J(12 * FT, 12 * FT), 'J4': J(20 * FT, 12 * FT),
                      'J5': J(20 * FT, 0), 'J6': J(12 * FT, 0), 'J7': J(12 * FT, 6 * FT), 'J8': J(20 * FT, 6 * FT)},
        'walls': {'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J8'),
                  'W5': W('J8', 'J5'), 'W6': W('J5', 'J6'), 'W7': W('J6', 'J1'), 'W8': W('J6', 'J7'),
                  'W9': W('J7', 'J3'), 'W10': W('J7', 'J8')},
        'rooms': {'R1': {'level': 'L1', 'anchor': [6 * FT, 6 * FT], 'name': 'Kitchen', 'function': 'kitchen'},
                  'R2': {'level': 'L1', 'anchor': [16 * FT, 9 * FT], 'name': 'Living', 'function': 'living'},
                  'R3': {'level': 'L1', 'anchor': [16 * FT, 3 * FT], 'name': 'Utility', 'function': 'mechanical'}},
        'extensionsUsed': {ELEC: '0.1.0', FURN: '0.1.0', LGHT: '0.1.0'},
        'extensions': {
            ELEC: {
                'collections': {
                    'panels': {'X1': on_wall('W5', 'right', 3 * FT, 1200, box(0, -200, -400, 100, 200, 400),
                                             name='Main panel', volts=[120, 240], rating=200, mainBreaker=200, spaces=40,
                                             clearances={'working': env('workingSpace', box(0, -400, -1200, 1000, 400, 800))})},
                    'lights': {
                        'X2': on_surface('R1', 'ceiling', 5 * FT, 6 * FT, PENDANT, fixture='pendant', watts=10, name='Island pendant'),
                        'X3': on_surface('R1', 'ceiling', 7 * FT, 6 * FT, PENDANT, fixture='pendant', watts=10, name='Island pendant'),
                        'X4': on_surface('R1', 'ceiling', 3 * FT, 9 * FT, DOWNLIGHT, fixture='recessed', watts=12),
                        'X5': on_surface('R1', 'ceiling', 9 * FT, 9 * FT, DOWNLIGHT, fixture='recessed', watts=12),
                        'X6': on_surface('R2', 'ceiling', 16 * FT, 9 * FT, DOWNLIGHT, fixture='recessed', watts=12),
                        'X7': on_wall('W7', 'left', 6 * FT, 2000, box(0, -100, -150, 150, 100, 150), fixture='exterior',
                                      watts=15, name='Porch light')},
                    'switches': {
                        'X10': on_wall('W8', 'left', FT, 1200, PLATE, control='dimmer', controls=['X2', 'X3']),
                        'X11': on_wall('W8', 'left', 2 * FT, 1200, PLATE, control='smart', controls=['X4', 'X5']),
                        'X12': on_wall('W9', 'right', FT, 1200, PLATE, controls=['X6']),
                        'X13': on_wall('W1', 'right', 2 * FT, 1200, PLATE, controls=['X7'])}},
                'circuits': {'C1': {'panel': 'X1', 'breaker': 15, 'volts': 120, 'rating': 15, 'space': 1, 'protection': ['afci'],
                                    'loads': ['X2', 'X3', 'X4', 'X5', 'X6', 'X7'], 'name': 'Lights'}}},
            FURN: {'collections': {'pieces': {'X20': item('lamp-table-600', floor_host('R2', 18 * FT, 10 * FT))}}},
            LGHT: {
                'luminaires': {
                    'X2': {'lumens': 450, 'cct': 2700, 'dimmable': True},
                    'X3': {'lumens': 450, 'cct': 2700, 'dimmable': True},
                    'X4': {'lumens': 800, 'cct': 3000, 'cctRange': [2700, 5000], 'dimmable': True},
                    'X5': {'lumens': 800, 'cct': 3000, 'cctRange': [2700, 5000], 'dimmable': True},
                    'X6': {'lumens': 800, 'cct': 2700, 'dimmable': False},
                    'X7': {'lumens': 600, 'cct': 3000},
                    'X20': {'lumens': 400, 'cct': 2700, 'dimmable': True}},
                'scenes': {
                    'LS1': {'name': 'Evening', 'on': {'X2': {'output': 60}, 'X3': {'output': 60},
                                                      'X4': {'output': 40, 'cct': 2700}, 'X5': {'output': 40, 'cct': 2700},
                                                      'X7': {}, 'X20': {}}},
                    'LS2': {'name': 'Night light', 'on': {'X3': {'output': 10}, 'X20': {'output': 20}}}}}},
    }
    d['assets'] = assets_of(d)
    return d


def gedit(fn):
    """The Phase 13 lit house, changed by fn(d) in place."""
    d = lit_house()
    fn(d)
    return d


LUM = lambda d: ext(d, LGHT)['luminaires']                                         # noqa: E731
SCN = lambda d: ext(d, LGHT)['scenes']                                             # noqa: E731
ON = lambda d, s: SCN(d)[s]['on']                                                  # noqa: E731
GK = lambda d, c: coll(d, ELEC, c)                                                 # noqa: E731
GDER = derived_of(LGHT)
G = lambda *a, **k: V(LGHT, *a, **k)    # noqa: E731
LIT = {'scenes': {'LS1': {'name': 'Evening', 'on': ['X2', 'X20', 'X3', 'X4', 'X5', 'X7'], 'dimmed': ['X2', 'X3', 'X4', 'X5']},
                  'LS2': {'name': 'Night light', 'on': ['X20', 'X3'], 'dimmed': ['X20', 'X3']}},
       'luminaires': {'X2': {'scenes': ['LS1']}, 'X20': {'scenes': ['LS1', 'LS2']}, 'X3': {'scenes': ['LS1', 'LS2']},
                      'X4': {'scenes': ['LS1']}, 'X5': {'scenes': ['LS1']}, 'X6': {'scenes': []}, 'X7': {'scenes': ['LS1']}}}


def check_lght(r):
    # every list sorted and every object in ID order, by code unit: X20 before X3; the Living room's
    # downlight in no scene, with an empty list
    ensure(GDER(r) == LIT and list(GDER(r)['luminaires']) == ['X2', 'X20', 'X3', 'X4', 'X5', 'X6', 'X7'], GDER(r))


BAD_G = lambda d: ON(d, 'LS1')['X2'].update(output=0)                             # noqa: E731  the schema tier
INV_G = lambda d: ON(d, 'LS2').update(X10={})                                     # noqa: E731  FS-LGHT-INV-005
INV_G_DIAG = [('FS-LGHT-INV-005', ['LS2'])]
ALL_KNOWN = ALL + (STRC, LAND, LGHT)

G('examples', 'p13-lit-house', 'The Phase 13 lit house, read by an implementation of FS_lighting that knows it: '
  'pendants over the Kitchen\'s island on a dimmer, tunable-white downlights on a smart switch, a downlight in the '
  'Living room that does not dim, a porch light, and an FS_furniture table lamp - each described as a luminaire - and '
  'two scenes, "Evening" and "Night light". It is valid, reports nothing, and derives each scene\'s name, the '
  'luminaires it turns on and those it dims, and each luminaire\'s scenes - none, for the Living room\'s downlight.',
  ['1.2.1', '1.2.3', '1.2.4', '1.3.1', '2.1.1', '2.1.3', '3.1.1', '6.1.1'], lit_house(), check=check_lght)
G('examples', 'core-only-reader', 'The same house read with no known extensions: FS_lighting is not evaluated, so '
  'nothing of it is derived (`derived.extensions` is empty) - only what Core derives from every extension element\'s '
  'fallback and host (Core 1.6.9); FS_lighting has no elements of its own.',
  ['1.2.1', '1.2.4', 'FS-CORE-1.6.9', 'FS-CORE-12.6.2'], lit_house(), registry=None,
  check=lambda r: ensure(r['derived']['extensions'] == {} and sorted(r['derived']['fallbacks'])
                         == ['X1', 'X10', 'X11', 'X12', 'X13', 'X2', 'X20', 'X3', 'X4', 'X5', 'X6', 'X7'],
                         r['derived']['extensions']))
G('examples', 'all-official-known', 'The house read with every official entry known, by an implementation of '
  'FS_lighting alone: FS_electrical and FS_furniture are checked only as Core 12 checks a known extension - the lamp '
  'has the model and symbol its kind requires - and only FS_lighting is evaluated and derived.', ['1.2.1', '1.2.4'],
  lit_house(), registry=[entry(x) for x in ALL_KNOWN],
  check=lambda r: ensure(list(r['derived']['extensions']) == [LGHT] and GDER(r) == LIT, list(r['derived']['extensions'])))
G('examples', 'no-scenes', 'FS_lighting used with empty top-level data: valid, and both derived members empty.',
  ['1.3.1', '6.1.1'], gedit(lambda d: d['extensions'].update({LGHT: {}})),
  check=lambda r: ensure(GDER(r) == {'scenes': {}, 'luminaires': {}}, GDER(r)))

G('activation', 'unknown-data-not-evaluated', 'The Evening scene sets a pendant\'s output to 0, which FS_lighting\'s '
  'schema does not allow, but no extension is known: nothing of it is evaluated, and the document is valid.', ['1.2.1'],
  gedit(BAD_G), registry=None)
G('activation', 'another-version-known', 'The document uses FS_lighting at 0.2.0, which is known (a later entry), but '
  'the implementation implements 0.1.0: not evaluated, so the data that breaks 0.1.0\'s schema is not reported.',
  ['1.2.1'], gedit(lambda d: (BAD_G(d), d['extensionsUsed'].update({LGHT: '0.2.0'}))), registry=[entry(LGHT, '0.2.0')])
G('activation', 'version-without-patch', '"0.1" equals 0.1.0 (Core 12.3), so FS_lighting is evaluated: its data '
  'breaks the schema, FS-LGHT-SCH-001.', ['1.2.1', '1.3.1'],
  gedit(lambda d: (BAD_G(d), d['extensionsUsed'].update({LGHT: '0.1'}))), [('FS-LGHT-SCH-001', [])])
G('activation', 'declaration-object', 'A declaration object with a schema URI is its version string (Core 12.1.3): '
  'FS_lighting is evaluated.', ['1.2.1', '1.3.1'],
  gedit(lambda d: (BAD_G(d), d['extensionsUsed'].update({LGHT: {'version': '0.1.0', 'schema': entry(LGHT)['schema']}}))),
  [('FS-LGHT-SCH-001', [])])
G('activation', 'core-0.1-document', 'A document declaring "0.1" has no extension elements and its extension data is '
  'opaque (Core 1.2.4): FS_lighting is not evaluated, even though it is known.', ['1.2.1'],
  {'floorspec': '0.1', 'project': {'name': 'Old'}, 'extensionsUsed': {ELEC: '0.1.0', LGHT: '0.1.0'},
   'extensions': {LGHT: {'colour': 'red'}}})
G('activation', 'core-0.3-document', 'The lit house declaring Core "0.3", a draft FS_lighting 0.1.0 lists (1.1): '
  'FS_lighting is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
  ['1.2.1', '1.2.3', '1.2.4', '6.1.1'], gedit(lambda d: d.update(floorspec='0.3')), check=check_lght)
G('activation', 'core-0.3-invariants', 'The same "0.3" house with the Night light turning on a switch: FS_lighting is '
  'evaluated for a Core 0.3 document, so the invariant is reported.', ['1.2.1', '1.2.3', '3.1.1'],
  gedit(lambda d: (d.update(floorspec='0.3'), INV_G(d))), INV_G_DIAG)
G('activation', 'core-0.4-document', 'The lit house declaring Core "0.4", a draft FS_lighting 0.1.0 lists (1.1): '
  'FS_lighting is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
  ['1.2.1', '1.2.3', '1.2.4', '6.1.1'], gedit(lambda d: d.update(floorspec='0.4')), check=check_lght)
G('activation', 'electrical-known-too', 'The house read with FS_electrical\'s entry known as well as FS_lighting\'s, by '
  'an implementation of FS_lighting alone: FS_electrical is checked only as Core 12 checks a known extension, and '
  'FS_lighting is evaluated and derived exactly as with its own entry alone.', ['1.2.1', '1.2.4', '6.1.1'],
  lit_house(), registry=[entry(ELEC), entry(LGHT)],
  check=lambda r: ensure(list(r['derived']['extensions']) == [LGHT] and GDER(r) == LIT, r['derived']['extensions']))

G('order', 'core-error-first', 'A Core invariant breaks - the porch light\'s switch 13\' along the 12\' wall W2, '
  'FS-INV-501 - and so does FS_lighting\'s schema: Core\'s error is reported, and FS_lighting is not evaluated.',
  ['1.2.2'], gedit(lambda d: (BAD_G(d), GK(d, 'switches')['X13']['host'].update(wall='W2', offset=13 * FT))),
  [('FS-INV-501', ['X13'])])
G('order', 'requires-not-used', 'The document uses FS_lighting, which requires FS_electrical (1.1), and no longer '
  'uses FS_electrical - neither its declaration nor its data, so the lights the scenes turn on are gone: Core reports '
  'FS-INV-601 (Core 12.3.2), a tier 4 error, so FS_lighting is not evaluated, and none of its broken references is '
  'reported.', ['1.2.2', 'FS-CORE-12.3.2'],
  gedit(lambda d: (d['extensionsUsed'].pop(ELEC), d['extensions'].pop(ELEC))), [('FS-INV-601', [])])
G('order', 'requires-out-of-range', 'The document uses FS_electrical at 0.2.0, outside the range ^0.1.0 FS_lighting '
  'requires: Core reports FS-INV-602 (Core 12.3.3), and FS_lighting is not evaluated.', ['1.2.2', 'FS-CORE-12.3.3'],
  gedit(lambda d: (INV_G(d), d['extensionsUsed'].update({ELEC: '0.2.0'}))), [('FS-INV-602', [])])
G('order', 'schema-before-invariants', 'The data breaks the schema and an invariant: only FS-LGHT-SCH-001.',
  ['1.2.2', '1.3.1'], gedit(lambda d: (BAD_G(d), INV_G(d))), [('FS-LGHT-SCH-001', [])])
G('order', 'no-lints-when-invalid', 'An invariant breaks and a lint would apply too - the Evening scene dims the '
  'Living room\'s downlight, which does not dim: the document is invalid, so no lint is reported, FS_lighting\'s or '
  'Core\'s.', ['1.2.2', '1.2.3'], gedit(lambda d: (INV_G(d), ON(d, 'LS1').update(X6={'output': 50}))), INV_G_DIAG)

G('schema', 'data-not-an-object', 'FS_lighting\'s top-level data is an array: Core allows any JSON there, '
  'FS_lighting\'s schema does not.', ['1.3.1'], gedit(lambda d: d['extensions'].update({LGHT: []})),
  [('FS-LGHT-SCH-001', [])])
G('schema', 'unknown-member', 'A top-level member FS_lighting does not define, `fixtures`.', ['1.3.1'],
  gedit(lambda d: ext(d, LGHT).update(fixtures={})), [('FS-LGHT-SCH-001', [])])
G('schema', 'empty-collections', 'An empty `collections` member: FS_lighting adds no kind of element, so its data has '
  'no `collections`, even an empty one. Core finds no collection in it; FS_lighting\'s schema rejects it.', ['1.3.1'],
  gedit(lambda d: ext(d, LGHT).update(collections={})), [('FS-LGHT-SCH-001', [])])
G('schema', 'a-collection', 'A collection `fixtures` in FS_lighting\'s data: its registry entry names no kind, so Core '
  '12.4.1 reports it (FS-INV-604), and FS_lighting is not evaluated.', ['1.2.2', 'FS-CORE-12.4.1'],
  gedit(lambda d: ext(d, LGHT).update(collections={'fixtures': {}})), [('FS-INV-604', [])])
G('schema', 'scene-without-a-name', 'A scene always has a name.', ['1.3.1'],
  gedit(lambda d: SCN(d)['LS2'].pop('name')), [('FS-LGHT-SCH-001', [])])
G('schema', 'empty-name', 'A scene\'s name is 1 to 200 characters: never empty.', ['1.3.1'],
  gedit(lambda d: SCN(d)['LS2'].update(name='')), [('FS-LGHT-SCH-001', [])])
G('schema', 'name-too-long', 'A scene\'s name is 1 to 200 characters.', ['1.3.1'],
  gedit(lambda d: SCN(d)['LS2'].update(name='N' * 201)), [('FS-LGHT-SCH-001', [])])
G('schema', 'scene-id-not-an-id', 'A scene keyed by "Night light", which is not an ID (Core 3.1.1).', ['1.3.1'],
  gedit(lambda d: SCN(d).update({'Night light': SCN(d).pop('LS2')})), [('FS-LGHT-SCH-001', [])])
G('schema', 'output-zero', 'An output of 0: a light a scene does not turn on is left out of its `on`.', ['1.3.1'],
  gedit(BAD_G), [('FS-LGHT-SCH-001', [])])
G('schema', 'output-above-full', 'An output of 101 percent.', ['1.3.1'],
  gedit(lambda d: ON(d, 'LS1')['X2'].update(output=101)), [('FS-LGHT-SCH-001', [])])
G('schema', 'output-with-a-fraction', 'An output written with a fraction is not an integer, even when it is a whole '
  'number (1.4).', ['1.3.1'], None, [('FS-LGHT-SCH-001', [])],
  raw=(fmt(lit_house()) + '\n').replace('"output": 60', '"output": 60.0', 1).encode('utf-8'))
G('schema', 'on-not-an-object', 'A scene\'s `on` is an object of settings, not a list of IDs.', ['1.3.1'],
  gedit(lambda d: SCN(d)['LS2'].update(on=['X3', 'X20'])), [('FS-LGHT-SCH-001', [])])
G('schema', 'setting-with-an-unknown-member', 'A setting has a member a setting does not define: `colour`.', ['1.3.1'],
  gedit(lambda d: ON(d, 'LS2')['X3'].update(colour='amber')), [('FS-LGHT-SCH-001', [])])
G('schema', 'setting-cct-above-the-range', 'A setting\'s colour temperature of 10,001 K.', ['1.3.1'],
  gedit(lambda d: ON(d, 'LS1')['X4'].update(cct=10001)), [('FS-LGHT-SCH-001', [])])
G('schema', 'cct-below-the-range', 'A luminaire\'s colour temperature of 999 K.', ['1.3.1'],
  gedit(lambda d: LUM(d)['X2'].update(cct=999)), [('FS-LGHT-SCH-001', [])])
G('schema', 'cct-range-of-three', 'A tunable range is two colour temperatures, not three.', ['1.3.1'],
  gedit(lambda d: LUM(d)['X4'].update(cctRange=[2700, 4000, 5000])), [('FS-LGHT-SCH-001', [])])
G('schema', 'lumens-zero', 'A luminaire\'s light output is at least one lumen.', ['1.3.1'],
  gedit(lambda d: LUM(d)['X6'].update(lumens=0)), [('FS-LGHT-SCH-001', [])])
G('schema', 'dimmable-not-a-boolean', 'Whether a luminaire dims is true or false, not "yes".', ['1.3.1'],
  gedit(lambda d: LUM(d)['X6'].update(dimmable='yes')), [('FS-LGHT-SCH-001', [])])
G('schema', 'luminaire-with-an-unknown-member', 'A luminaire has a member a luminaire does not define: `watts`, '
  'which is FS_electrical\'s.', ['1.3.1'], gedit(lambda d: LUM(d)['X2'].update(watts=10)), [('FS-LGHT-SCH-001', [])])

G('invariants', 'scene-id-of-a-light', 'The Night light is keyed by X3, a pendant\'s ID: a scene\'s ID is in the '
  'document\'s one space of IDs. Its own `on` names X3 too.', ['1.3.2'],
  gedit(lambda d: SCN(d).update(X3=SCN(d).pop('LS2'))), [('FS-LGHT-INV-001', ['X3'])])
G('invariants', 'scene-id-of-a-room', 'The Night light is keyed by R2, the Living room\'s ID.', ['1.3.2'],
  gedit(lambda d: SCN(d).update(R2=SCN(d).pop('LS2'))), [('FS-LGHT-INV-001', ['R2'])])
G('invariants', 'scene-id-of-a-lamp', 'The Night light is keyed by X20, the table lamp\'s ID: an extension element of '
  'any extension.', ['1.3.2'],
  gedit(lambda d: SCN(d).update(X20=SCN(d).pop('LS2'))), [('FS-LGHT-INV-001', ['X20'])])
G('invariants', 'luminaire-of-a-switch', 'A luminaire keyed by the dimmer X10: a switch of FS_electrical gives no '
  'light.', ['2.1.1'], gedit(lambda d: LUM(d).update(X10={'lumens': 450})), [('FS-LGHT-INV-002', ['X10'])])
G('invariants', 'luminaire-of-a-panel', 'A luminaire keyed by the panel X1.', ['2.1.1'],
  gedit(lambda d: LUM(d).update(X1={'cct': 3000})), [('FS-LGHT-INV-002', ['X1'])])
G('invariants', 'luminaire-of-a-wall', 'A luminaire keyed by the wall W1: a core element is no extension element.',
  ['2.1.1'], gedit(lambda d: LUM(d).update(W1={})), [('FS-LGHT-INV-002', ['W1'])])
G('invariants', 'luminaire-of-nothing', 'A luminaire keyed by X99, which is no element.', ['2.1.1'],
  gedit(lambda d: LUM(d).update(X99={'lumens': 800})), [('FS-LGHT-INV-002', ['X99'])])
G('invariants', 'cct-range-reversed', 'The downlight X4\'s range is written coolest first, [5000, 2700].', ['2.1.2'],
  gedit(lambda d: LUM(d)['X4'].update(cctRange=[5000, 2700])), [('FS-LGHT-INV-003', ['X4'])])
G('invariants', 'cct-range-of-one-value', 'The downlight X4\'s range is [3000, 3000]: a luminaire that gives one '
  'colour temperature is not tunable, and has a `cct`.', ['2.1.2'],
  gedit(lambda d: LUM(d)['X4'].update(cctRange=[3000, 3000])), [('FS-LGHT-INV-003', ['X4'])])
G('invariants', 'cct-outside-its-range', 'The downlight X5\'s own colour temperature, 2,200 K, is warmer than its '
  'range\'s warmest.', ['2.1.3'], gedit(lambda d: LUM(d)['X5'].update(cct=2200)), [('FS-LGHT-INV-004', ['X5'])])
G('invariants', 'cct-at-the-bounds', 'X4\'s own colour temperature is its range\'s warmest and X5\'s its coolest: '
  'the bounds are in the range. Valid.', ['2.1.3'],
  gedit(lambda d: (LUM(d)['X4'].update(cct=2700), LUM(d)['X5'].update(cct=5000))))
G('invariants', 'reversed-range-and-cct-outside-it', 'X4\'s range is reversed and its colour temperature, 6,500 K, '
  'is outside it either way: FS-LGHT-INV-003 only, since FS-LGHT-INV-004 is evaluated only for a luminaire without '
  'it (5.2).', ['2.1.2', '5.2.1'], gedit(lambda d: LUM(d)['X4'].update(cctRange=[5000, 2700], cct=6500)),
  [('FS-LGHT-INV-003', ['X4'])])
G('invariants', 'scene-turns-on-a-switch', 'The Night light turns on the dimmer X10.', ['3.1.1'], gedit(INV_G),
  INV_G_DIAG)
G('invariants', 'scene-turns-on-a-room', 'The Evening scene turns on R1, the Kitchen: a room is no extension element.',
  ['3.1.1'], gedit(lambda d: ON(d, 'LS1').update(R1={})), [('FS-LGHT-INV-005', ['LS1'])])
G('invariants', 'scene-turns-on-two-unknowns', 'The Night light turns on X98 and X99, which are no elements: reported '
  'once for each, both naming the scene.', ['1.2.3', '3.1.1'],
  gedit(lambda d: ON(d, 'LS2').update(X98={}, X99={'output': 50})),
  [('FS-LGHT-INV-005', ['LS2']), ('FS-LGHT-INV-005', ['LS2'])])
G('invariants', 'scene-turns-on-an-undescribed-light', 'A scene LS3 "Living" turns on the Living room\'s downlight '
  'X6 and the porch light X7, and X7\'s luminaire is removed: a scene may turn on a light FS_lighting says nothing of '
  '(2.2). Valid, and X7 is still among the derived luminaires, by its scenes.', ['3.1.1', '6.1.1'],
  gedit(lambda d: (LUM(d).pop('X7'), SCN(d).update(LS3={'name': 'Living', 'on': {'X6': {}, 'X7': {}}}))),
  check=lambda r: ensure(GDER(r)['luminaires']['X7'] == {'scenes': ['LS1', 'LS3']}
                         and GDER(r)['luminaires']['X6'] == {'scenes': ['LS3']}, GDER(r)['luminaires']))
G('invariants', 'two-scenes-one-name', 'The Night light renamed "Evening".', ['3.1.2'],
  gedit(lambda d: SCN(d)['LS2'].update(name='Evening')), [('FS-LGHT-INV-006', ['LS1', 'LS2'])])
G('invariants', 'three-scenes-one-name', 'Three scenes named "Evening": once for each pair.', ['1.2.3', '3.1.2'],
  gedit(lambda d: (SCN(d)['LS2'].update(name='Evening'), SCN(d).update(LS3={'name': 'Evening'}))),
  [('FS-LGHT-INV-006', ['LS1', 'LS2']), ('FS-LGHT-INV-006', ['LS1', 'LS3']), ('FS-LGHT-INV-006', ['LS2', 'LS3'])])
G('invariants', 'names-differ-in-case', 'A scene LS3 named "evening": names are compared exactly, so it is another '
  'name. Valid.', ['3.1.2'], gedit(lambda d: SCN(d).update(LS3={'name': 'evening'})))
G('invariants', 'every-one-once', 'Six rules broken at once: each is reported once, naming its element.',
  ['1.2.3', '1.3.2', '2.1.1', '2.1.2', '2.1.3', '3.1.1', '3.1.2'],
  gedit(lambda d: (SCN(d).update(R1={'name': 'Kitchen'}), LUM(d).update(X10={}), LUM(d)['X4'].update(cctRange=[5000, 2700]),
                   LUM(d)['X5'].update(cct=6500), INV_G(d), SCN(d).update(LS3={'name': 'Night light'}))),
  [('FS-LGHT-INV-001', ['R1']), ('FS-LGHT-INV-002', ['X10']), ('FS-LGHT-INV-003', ['X4']), ('FS-LGHT-INV-004', ['X5']),
   ('FS-LGHT-INV-005', ['LS2']), ('FS-LGHT-INV-006', ['LS2', 'LS3'])])

G('lints', 'lamp-that-does-not-dim', 'The table lamp does not dim, and the Night light sets it to 20 %.', ['1.2.3'],
  gedit(lambda d: LUM(d)['X20'].update(dimmable=False)), [('FS-LGHT-LINT-001', ['LS2', 'X20'])])
G('lints', 'not-dimmable-at-full', 'A scene LS3 turns on the Living room\'s downlight, which does not dim, at full: '
  'no lint.', ['1.2.3'], gedit(lambda d: SCN(d).update(LS3={'name': 'Living', 'on': {'X6': {'output': 100}}})))
G('lints', 'dimmable-not-stated', 'The pendants\' luminaires no longer say whether they dim: dimming them is no '
  'lint (5.3), and they are on a dimmer.', ['1.2.3'],
  gedit(lambda d: (LUM(d)['X2'].pop('dimmable'), LUM(d)['X3'].pop('dimmable'))))
G('lints', 'cct-outside-the-range', 'The Evening scene sets the downlight X4 to 2,200 K, warmer than its range.',
  ['1.2.3'], gedit(lambda d: ON(d, 'LS1')['X4'].update(cct=2200)), [('FS-LGHT-LINT-002', ['LS1', 'X4'])])
G('lints', 'cct-at-the-range-bound', 'The Evening scene sets the downlight X4 to 5,000 K, its range\'s coolest: no '
  'lint.', ['1.2.3'], gedit(lambda d: ON(d, 'LS1')['X4'].update(cct=5000)))
G('lints', 'cct-of-a-fixed-luminaire', 'The Night light sets the pendant X3, which gives 2,700 K and is not tunable, '
  'to 3,000 K.', ['1.2.3'], gedit(lambda d: ON(d, 'LS2')['X3'].update(cct=3000)), [('FS-LGHT-LINT-002', ['LS2', 'X3'])])
G('lints', 'cct-a-fixed-luminaire-gives', 'The Night light sets the pendant X3 to 2,700 K, the one it gives: no lint.',
  ['1.2.3'], gedit(lambda d: ON(d, 'LS2')['X3'].update(cct=2700)))
G('lints', 'cct-of-an-undescribed-light', 'The Evening scene sets the porch light to 5,000 K, and the porch light\'s '
  'luminaire says nothing of its colour: no lint.', ['1.2.3'],
  gedit(lambda d: (LUM(d)['X7'].pop('cct'), ON(d, 'LS1')['X7'].update(cct=5000))))
G('lints', 'dimmed-on-a-single-switch', 'The Evening scene sets the porch light, on a single switch, to 50 %.',
  ['1.2.3'], gedit(lambda d: ON(d, 'LS1')['X7'].update(output=50)), [('FS-LGHT-LINT-003', ['LS1', 'X7'])])
G('lints', 'dimmer-and-single-switch', 'The porch light is controlled from a second switch X14 by the door, a '
  'dimmer, as well as by X13: the Evening scene sets it to 50 %, and some switch that controls it dims. No lint.',
  ['1.2.3'],
  gedit(lambda d: (ON(d, 'LS1')['X7'].update(output=50), GK(d, 'switches').update(
      X14=on_wall('W1', 'right', 4 * FT, 1200, PLATE, control='dimmer', controls=['X7'])))))
G('lints', 'smart-switch-made-occupancy', 'The downlights\' smart switch is now an occupancy sensor: the Evening scene '
  'dims both downlights, which no dimmer or smart switch controls.', ['1.2.3'],
  gedit(lambda d: GK(d, 'switches')['X11'].update(control='occupancy')),
  [('FS-LGHT-LINT-003', ['LS1', 'X4']), ('FS-LGHT-LINT-003', ['LS1', 'X5'])])
G('lints', 'control-absent-is-single', 'The pendants\' dimmer no longer says how it switches, so it is a single '
  'switch (FS_electrical 2.3): both scenes dim a pendant it controls.', ['1.2.3'],
  gedit(lambda d: GK(d, 'switches')['X10'].pop('control')),
  [('FS-LGHT-LINT-003', ['LS1', 'X2']), ('FS-LGHT-LINT-003', ['LS1', 'X3']), ('FS-LGHT-LINT-003', ['LS2', 'X3'])])
G('lints', 'not-dimmable-on-a-single-switch', 'A scene LS3 sets the Living room\'s downlight, which does not dim and is '
  'on a single switch, to 50 %: both lints.', ['1.2.3'],
  gedit(lambda d: SCN(d).update(LS3={'name': 'Living', 'on': {'X6': {'output': 50}}})),
  [('FS-LGHT-LINT-001', ['LS3', 'X6']), ('FS-LGHT-LINT-003', ['LS3', 'X6'])])
G('lints', 'every-lint-once', 'The lamp does not dim, the downlight X4 is set past its range and the porch light '
  'is dimmed on a single switch: each lint once.', ['1.2.3'],
  gedit(lambda d: (LUM(d)['X20'].update(dimmable=False), ON(d, 'LS1')['X4'].update(cct=6500),
                   ON(d, 'LS1')['X7'].update(output=50))),
  [('FS-LGHT-LINT-001', ['LS2', 'X20']), ('FS-LGHT-LINT-002', ['LS1', 'X4']), ('FS-LGHT-LINT-003', ['LS1', 'X7'])])

G('derived', 'scene-with-nothing-on', 'A scene LS3 "Off" with an empty `on` turns every light off: it turns on '
  'nothing and dims nothing.', ['6.1.1'], gedit(lambda d: SCN(d).update(LS3={'name': 'Off'})),
  check=lambda r: ensure(GDER(r)['scenes']['LS3'] == {'name': 'Off', 'on': [], 'dimmed': []}, GDER(r)['scenes']))
G('derived', 'full-output-is-not-dimmed', 'The Night light sets the pendant to 100 % written out and the lamp to 99 %: '
  'a setting without `output` and one of 100 are full, and 99 is dimmed.', ['6.1.1'],
  gedit(lambda d: (ON(d, 'LS2')['X3'].update(output=100), ON(d, 'LS2')['X20'].update(output=99))),
  check=lambda r: ensure(GDER(r)['scenes']['LS2']['dimmed'] == ['X20'] and GDER(r)['scenes']['LS1']['dimmed'] == ['X2', 'X3', 'X4', 'X5'],
                         GDER(r)['scenes']))
G('derived', 'scenes-in-id-order', 'A third scene LS10 "Late": scenes are in ID order by code unit, LS1, LS10, LS2, and '
  'a luminaire\'s scenes are sorted the same way.', ['6.1.1'],
  gedit(lambda d: SCN(d).update(LS10={'name': 'Late', 'on': {'X3': {'output': 30}}})),
  check=lambda r: ensure(list(GDER(r)['scenes']) == ['LS1', 'LS10', 'LS2']
                         and GDER(r)['luminaires']['X3'] == {'scenes': ['LS1', 'LS10', 'LS2']}, GDER(r)))


def island_options(d):
    """Core 0.3 design options for the island: option A (OP1, the primary) keeps the pendants X2 and
    X3; option B (OP2) hangs one linear pendant X8 in their place, on the same dimmer."""
    d['floorspec'] = '0.3'
    d['optionSets'] = {'OS1': {'primary': 'OP1', 'name': 'Island light'}}
    d['options'] = {'OP1': {'set': 'OS1', 'name': 'A'}, 'OP2': {'set': 'OS1', 'name': 'B'}}
    GK(d, 'lights')['X2']['option'] = 'OP1'
    GK(d, 'lights')['X3']['option'] = 'OP1'
    GK(d, 'lights')['X8'] = on_surface('R1', 'ceiling', 6 * FT, 6 * FT, box(-600, -60, -900, 600, 60, 0), fixture='pendant',
                                       watts=20, option='OP2')


G('options', 'pendants-only-in-option-a', 'Island options A and B as Core 0.3 design options (Core 19): the pair of '
  'pendants in A, the primary, and a linear pendant in B. The pendants\' luminaires and the scenes that turn them on '
  'name lights that option B\'s design does not have: FS_lighting is evaluated in each checked design, so B\'s design '
  'breaks 2.1.1 and 3.1.1, each reported with `design` (Core 19.5.2).',
  ['1.2.1', '1.2.3', '2.1.1', '3.1.1', 'FS-CORE-19.3.1'], gedit(island_options),
  [('FS-LGHT-INV-002', ['X2'], 'OP2'), ('FS-LGHT-INV-002', ['X3'], 'OP2'), ('FS-LGHT-INV-005', ['LS1'], 'OP2'),
   ('FS-LGHT-INV-005', ['LS1'], 'OP2'), ('FS-LGHT-INV-005', ['LS2'], 'OP2')])
G('options', 'scenes-of-every-design', 'The same options, with the pendants taken out of FS_lighting: no luminaire '
  'describes them and no scene turns them, or B\'s pendant, on, so every scene names lights of every design. Valid, '
  'and the primary design is derived.', ['1.2.1', '1.2.4', '3.1.1', '6.1.1', 'FS-CORE-19.3.1'],
  gedit(lambda d: (island_options(d), LUM(d).pop('X2'), LUM(d).pop('X3'), ON(d, 'LS1').pop('X2'), ON(d, 'LS1').pop('X3'),
                   ON(d, 'LS2').pop('X3'))),
  check=lambda r: ensure(GDER(r)['scenes']['LS2'] == {'name': 'Night light', 'on': ['X20'], 'dimmed': ['X20']}
                         and r['derived']['options']['OS1']['chosen'] == 'OP1', GDER(r)))


def lght_derived(d):
    data = json.dumps(d).encode('utf-8')
    result, _, _ = check(data, ext_reader(data), json.dumps([entry(LGHT)]).encode('utf-8'), official.implemented(LGHT))
    assert result['valid'], result['diagnostics']
    return result['derived']['extensions'][LGHT]


GO = lambda *a, **k: O(LGHT, *a, **k)    # noqa: E731
GO('add-a-scene', 'setProperty of $document /extensions/FS_lighting/scenes/LS3 adds a scene "Reading" - the Living '
   'room\'s downlight and the lamp at full - with an ID Ops does not mint (1.3.2). It commits, valid under FS_lighting.',
   ['1.2.1', '1.3.2', '3.1.1', '6.1.1', 'FS-OPS-2.3.1'], lit_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_lighting/scenes/LS3',
               'value': {'name': 'Reading', 'on': {'X6': {}, 'X20': {}}}}]},
   check=lambda r, B: ensure(lght_derived(B)['scenes']['LS3'] == {'name': 'Reading', 'on': ['X20', 'X6'], 'dimmed': []}
                             and lght_derived(B)['luminaires']['X6'] == {'scenes': ['LS3']}, lght_derived(B)))
GO('rename-to-a-name-in-use-is-rejected', 'setProperty of the Night light\'s name to "Evening": the result breaks '
   '3.1.2, and an applier that implements FS_lighting and knows it rejects the batch (Ops 1.2.3).',
   ['3.1.2', '1.2.1', 'FS-OPS-1.2.3'], lit_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_lighting/scenes/LS2/name', 'value': 'Evening'}]},
   'rejected', [('FS-LGHT-INV-006', ['LS1', 'LS2'])])
GO('remove-a-light-in-a-scene-is-rejected', 'Removing the pendant X3 leaves its luminaire and both scenes naming it: '
   'Ops does not follow references inside an extension\'s members, so the result breaks 2.1.1 and 3.1.1, and the batch '
   'is rejected.', ['2.1.1', '3.1.1', '1.2.1', 'FS-OPS-1.2.3'], lit_house(),
   {'batch': [{'op': 'removeElement', 'id': 'X3'}]}, 'rejected',
   [('FS-LGHT-INV-002', ['X3']), ('FS-LGHT-INV-005', ['LS1']), ('FS-LGHT-INV-005', ['LS2'])])
GO('remove-a-light-and-its-references', 'The same removal, with the pendant\'s luminaire and its settings in both '
   'scenes unset in the same batch (3.1): it commits.', ['2.1.1', '3.1.1', '1.2.1', 'FS-OPS-2.3.1'], lit_house(),
   {'batch': [{'op': 'unsetProperty', 'id': '$document', 'path': '/extensions/FS_lighting/luminaires/X3'},
              {'op': 'unsetProperty', 'id': '$document', 'path': '/extensions/FS_lighting/scenes/LS1/on/X3'},
              {'op': 'unsetProperty', 'id': '$document', 'path': '/extensions/FS_lighting/scenes/LS2/on/X3'},
              {'op': 'removeElement', 'id': 'X3'}]},
   check=lambda r, B: ensure(r['removed'] == ['X3'] and lght_derived(B)['scenes']['LS2']['on'] == ['X20'], r['removed']))
GO('first-scene-creates-the-data', 'The lit house declaring FS_lighting with no data of it yet: setProperty of '
   '$document /extensions/FS_lighting/scenes/LS1 creates FS_lighting\'s data, and its `scenes`, on the way (Ops 2.3) - '
   'an "Evening" of the pendants at 60 %. It commits, valid under FS_lighting.', ['1.2.1', '1.3.1', '6.1.1', 'FS-OPS-2.3.1'],
   gedit(lambda d: d['extensions'].pop(LGHT)),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_lighting/scenes/LS1',
               'value': {'name': 'Evening', 'on': {'X2': {'output': 60}, 'X3': {'output': 60}}}}]},
   check=lambda r, B: ensure(B['extensions'][LGHT] == {'scenes': {'LS1': {'name': 'Evening', 'on': {'X2': {'output': 60}, 'X3': {'output': 60}}}}}
                             and lght_derived(B) == {'scenes': {'LS1': {'name': 'Evening', 'on': ['X2', 'X3'], 'dimmed': ['X2', 'X3']}},
                                                     'luminaires': {'X2': {'scenes': ['LS1']}, 'X3': {'scenes': ['LS1']}}},
                             B['extensions'].get(LGHT)))
GO('rename-a-scene', 'setProperty of $document /extensions/FS_lighting/scenes/LS2/name: the Night light is now "Late". '
   'It commits.', ['1.2.1', '3.1.2', 'FS-OPS-2.3.1'], lit_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_lighting/scenes/LS2/name', 'value': 'Late'}]},
   check=lambda r, B: ensure(lght_derived(B)['scenes']['LS2']['name'] == 'Late', lght_derived(B)['scenes']))
GO('remove-a-scene', 'unsetProperty of $document /extensions/FS_lighting/scenes/LS2 removes the Night light: the lamp '
   'and the pendant X3 are turned on by the Evening scene alone. It commits.', ['1.2.1', '6.1.1', 'FS-OPS-2.3.1'],
   lit_house(), {'batch': [{'op': 'unsetProperty', 'id': '$document', 'path': '/extensions/FS_lighting/scenes/LS2'}]},
   check=lambda r, B: ensure(list(lght_derived(B)['scenes']) == ['LS1']
                             and lght_derived(B)['luminaires']['X3'] == {'scenes': ['LS1']}, lght_derived(B)))
GO('describe-a-luminaire', 'setProperty of $document /extensions/FS_lighting/luminaires/X6 replaces what the Living '
   'room\'s downlight gives: now dimmable and tunable from 2,700 K to 4,000 K, at 3,000 K. It commits.',
   ['1.2.1', '2.1.1', '2.1.2', '2.1.3', 'FS-OPS-2.3.1'], lit_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_lighting/luminaires/X6',
               'value': {'lumens': 900, 'cct': 3000, 'cctRange': [2700, 4000], 'dimmable': True}}]},
   check=lambda r, B: ensure(ext(B, LGHT)['luminaires']['X6']['cctRange'] == [2700, 4000]
                             and lght_derived(B)['luminaires']['X6'] == {'scenes': []}, ext(B, LGHT)['luminaires']))
GO('scene-turns-on-a-switch-is-rejected', 'setProperty of $document /extensions/FS_lighting/scenes/LS2/on/X10 has the '
   'Night light turn on the dimmer X10: the result breaks 3.1.1, and the batch is rejected with FS-LGHT-INV-005.',
   ['3.1.1', '1.2.1', 'FS-OPS-1.2.3'], lit_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_lighting/scenes/LS2/on/X10', 'value': {}}]},
   'rejected', [('FS-LGHT-INV-005', ['LS2'])])


# ============================================================================= FS_views

VIEW = 'FS_views'
CODE[VIEW] = 'VIEW'


def pt(x_mm, y_mm, z_mm):
    """A point of a view, from millimetres: plan x and y, and a height above project zero."""
    return [x_mm * MM, y_mm * MM, z_mm * MM]


VIEWS = {
    'SV1': {'name': 'Hero exterior', 'eye': pt(-4000, -7000, 1600), 'target': pt(3048, 1829, 1350),
            'focalLength': 24, 'twoPoint': True, 'aperture': 'f/8', 'exposure': 3, 'sky': 'clear',
            'at': '2026-06-21T17:30'},
    'SV2': {'name': 'Kitchen island', 'eye': pt(600, 600, 1500), 'target': pt(1829, 1829, 950),
            'focalLength': 20, 'twoPoint': True, 'aspect': '16:9', 'aperture': 'f/2.8', 'focus': 1800 * MM,
            'sky': 'overcast', 'lights': 'on'},
    'SV3': {'name': 'Dusk from the garden', 'eye': pt(7500, -3000, 1700), 'target': pt(3048, 1829, 1200),
            'twoPoint': True, 'exposure': -3, 'sky': 'dusk', 'at': '2026-10-15T18:40-04:00', 'scene': 'LS1'},
    'SV4': {'name': 'Cutaway', 'eye': pt(-3000, -5000, 9000), 'target': pt(3048, 1829, 0), 'focalLength': 50,
            'aspect': '1:1', 'level': 'L1', 'levels': 'cutaway', 'sky': 'studio'},
}


def views_house():
    """The Phase 13 lit house (lit_house()) with four saved views of FS_views:

    - SV1 "Hero exterior": from the south-west, outside, at eye height, a 24 mm two-point view of
      the house at f/8 on a June evening;
    - SV2 "Kitchen island": from the Kitchen's south-west corner, a 20 mm two-point view of the
      island, 16:9, at f/2.8 focused on the pendants, under an overcast sky, with every light on;
    - SV3 "Dusk from the garden": from the south-east, a 35 mm two-point view at dusk in October,
      the lights as FS_lighting's scene LS1 "Evening" sets them;
    - SV4 "Cutaway": from high above the south-west, a 50 mm square view looking down into L1 with
      the roof and ceilings cut away, in a studio light.

    FS_views requires no other extension; the house uses FS_electrical, FS_furniture and FS_lighting
    as well, and FS_views reads FS_lighting's scenes as data."""
    d = lit_house()
    d['extensionsUsed'][VIEW] = '0.1.0'
    d['extensions'][VIEW] = {'views': copy.deepcopy(VIEWS)}
    return d


def vedit(fn):
    """The Phase 13 house with views, changed by fn(d) in place."""
    d = views_house()
    fn(d)
    return d


def without_lighting(d):
    """No FS_lighting: neither its declaration nor its data, and no view showing its scene."""
    d['extensionsUsed'].pop(LGHT)
    d['extensions'].pop(LGHT)
    VWS(d)['SV3'].pop('scene')


def views_alone(d):
    """FS_views the only extension the house uses: no lights, no lamp, no scenes."""
    for x in (ELEC, FURN, LGHT):
        d['extensionsUsed'].pop(x)
        d['extensions'].pop(x)
    d.pop('assets')
    VWS(d)['SV3'].pop('scene')


VWS = lambda d: ext(d, VIEW)['views']                                              # noqa: E731
VDER = derived_of(VIEW)
VW = lambda *a, **k: V(VIEW, *a, **k)    # noqa: E731
VIEWED = {'views': {'SV1': {'name': 'Hero exterior', 'level': None, 'lights': 'off', 'scene': None},
                    'SV2': {'name': 'Kitchen island', 'level': None, 'lights': 'on', 'scene': None},
                    'SV3': {'name': 'Dusk from the garden', 'level': None, 'lights': 'on', 'scene': 'LS1'},
                    'SV4': {'name': 'Cutaway', 'level': 'L1', 'lights': 'off', 'scene': None}}}
VIEW_KNOWN = ALL_KNOWN + (VIEW,)


def check_view(r):
    # SV3's lights are on by its scene, though it says nothing of `lights`; a view without a level
    # or a scene derives null for it
    ensure(VDER(r) == VIEWED and list(VDER(r)['views']) == ['SV1', 'SV2', 'SV3', 'SV4'], VDER(r))


BAD_V = lambda d: VWS(d)['SV1'].update(aspect='2:1')                               # noqa: E731  the schema tier
INV_V = lambda d: VWS(d)['SV2'].update(target=pt(600, 600, 1500))                 # noqa: E731  FS-VIEW-INV-002
INV_V_DIAG = [('FS-VIEW-INV-002', ['SV2'])]
LINT_V = lambda d: VWS(d)['SV4'].update(twoPoint=True)                            # noqa: E731  FS-VIEW-LINT-001

VW('examples', 'p13-house-with-views', 'The Phase 13 lit house with four saved views, read by an implementation of '
   'FS_views that knows it: a 24 mm two-point hero shot from the south-west on a June evening, a 20 mm two-point view '
   'of the Kitchen\'s island at f/2.8 with every light on, a two-point view from the garden at dusk with the lights as '
   'FS_lighting\'s "Evening" scene sets them - FS_lighting unknown to it, its scenes read as data - and a square '
   'view from high above with the roof and ceilings cut away above L1. It is valid, reports nothing, and derives each '
   'view\'s name, level, lights and scene.',
   ['1.2.1', '1.2.3', '1.2.4', '1.3.1', '1.3.2', '2.1.1', '2.2.1', '3.1.1', '3.2.1', '3.3.1', '3.3.2', '6.1.1'],
   views_house(), check=check_view)
VW('examples', 'core-only-reader', 'The same house read with no known extensions: FS_views is not evaluated, so '
   'nothing of it is derived (`derived.extensions` is empty) - only what Core derives from every extension element\'s '
   'fallback and host (Core 1.6.9); FS_views has no elements of its own.',
   ['1.2.1', '1.2.4', 'FS-CORE-1.6.9', 'FS-CORE-12.6.2'], views_house(), registry=None,
   check=lambda r: ensure(r['derived']['extensions'] == {} and sorted(r['derived']['fallbacks'])
                          == ['X1', 'X10', 'X11', 'X12', 'X13', 'X2', 'X20', 'X3', 'X4', 'X5', 'X6', 'X7'],
                          r['derived']['extensions']))
VW('examples', 'all-official-known', 'The house read with every official entry known, by an implementation of '
   'FS_views alone: FS_electrical, FS_furniture and FS_lighting are checked only as Core 12 checks a known extension - '
   'FS_lighting\'s requirement of FS_electrical among them - and only FS_views is evaluated and derived.',
   ['1.2.1', '1.2.4'], views_house(), registry=[entry(x) for x in VIEW_KNOWN],
   check=lambda r: ensure(list(r['derived']['extensions']) == [VIEW] and VDER(r) == VIEWED, list(r['derived']['extensions'])))
VW('examples', 'no-views', 'FS_views used with empty top-level data: valid, and no view derived.',
   ['1.3.1', '6.1.1'], vedit(lambda d: d['extensions'].update({VIEW: {}})),
   check=lambda r: ensure(VDER(r) == {'views': {}}, VDER(r)))
VW('examples', 'without-lighting', 'The house without FS_lighting - neither its declaration nor its data - and the '
   'dusk view without a scene: FS_views requires no other extension, so the views are valid as they are, and the dusk '
   'view\'s lights are off.', ['1.2.1', '1.3.1', '3.3.1', '6.1.1'], vedit(without_lighting),
   check=lambda r: ensure(VDER(r)['views']['SV3'] == {'name': 'Dusk from the garden', 'level': None, 'lights': 'off',
                                                      'scene': None} and list(r['derived']['extensions']) == [VIEW], VDER(r)))
VW('examples', 'views-alone', 'The house with FS_views the only extension it uses - no lights, no lamp, no scenes - '
   'and the dusk view without a scene: valid, and the four views derived.', ['1.2.1', '1.2.4', '1.3.1', '6.1.1'],
   vedit(views_alone),
   check=lambda r: ensure(sorted(VDER(r)['views']) == ['SV1', 'SV2', 'SV3', 'SV4'] and r['derived']['fallbacks'] == {}, VDER(r)))

VW('activation', 'unknown-data-not-evaluated', 'The hero shot\'s aspect is "2:1", which FS_views\'s schema does not '
   'allow, but no extension is known: nothing of it is evaluated, and the document is valid.', ['1.2.1'],
   vedit(BAD_V), registry=None)
VW('activation', 'another-version-known', 'The document uses FS_views at 0.2.0, which is known (a later entry), but '
   'the implementation implements 0.1.0: not evaluated, so the data that breaks 0.1.0\'s schema is not reported.',
   ['1.2.1'], vedit(lambda d: (BAD_V(d), d['extensionsUsed'].update({VIEW: '0.2.0'}))), registry=[entry(VIEW, '0.2.0')])
VW('activation', 'version-without-patch', '"0.1" equals 0.1.0 (Core 12.3), so FS_views is evaluated: its data '
   'breaks the schema, FS-VIEW-SCH-001.', ['1.2.1', '1.3.1'],
   vedit(lambda d: (BAD_V(d), d['extensionsUsed'].update({VIEW: '0.1'}))), [('FS-VIEW-SCH-001', [])])
VW('activation', 'declaration-object', 'A declaration object with a schema URI is its version string (Core 12.1.3): '
   'FS_views is evaluated.', ['1.2.1', '1.3.1'],
   vedit(lambda d: (BAD_V(d), d['extensionsUsed'].update({VIEW: {'version': '0.1.0', 'schema': entry(VIEW)['schema']}}))),
   [('FS-VIEW-SCH-001', [])])
VW('activation', 'core-0.1-document', 'A document declaring "0.1" has no extension elements and its extension data is '
   'opaque (Core 1.2.4): FS_views is not evaluated, even though it is known.', ['1.2.1'],
   {'floorspec': '0.1', 'project': {'name': 'Old'}, 'extensionsUsed': {VIEW: '0.1.0'},
    'extensions': {VIEW: {'colour': 'red'}}})
VW('activation', 'core-0.3-document', 'The house declaring Core "0.3", a draft FS_views 0.1.0 lists (1.1): FS_views '
   'is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
   ['1.2.1', '1.2.3', '1.2.4', '6.1.1'], vedit(lambda d: d.update(floorspec='0.3')), check=check_view)
VW('activation', 'core-0.3-invariants', 'The same "0.3" house with the island view\'s eye at its target: FS_views is '
   'evaluated for a Core 0.3 document, so the invariant is reported.', ['1.2.1', '1.2.3', '2.2.1'],
   vedit(lambda d: (d.update(floorspec='0.3'), INV_V(d))), INV_V_DIAG)
VW('activation', 'core-0.4-document', 'The house declaring Core "0.4", a draft FS_views 0.1.0 lists (1.1): FS_views '
   'is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
   ['1.2.1', '1.2.3', '1.2.4', '6.1.1'], vedit(lambda d: d.update(floorspec='0.4')), check=check_view)
VW('activation', 'lighting-known-too', 'The house read with FS_lighting\'s entry known as well as FS_views\'s, by an '
   'implementation of FS_views alone: FS_lighting is checked only as Core 12 checks a known extension, and FS_views '
   'is evaluated and derived exactly as with its own entry alone, reading the scenes as data.',
   ['1.2.1', '1.2.4', '3.3.1', '6.1.1'], views_house(), registry=[entry(LGHT), entry(VIEW)],
   check=lambda r: ensure(list(r['derived']['extensions']) == [VIEW] and VDER(r) == VIEWED, r['derived']['extensions']))

VW('order', 'core-error-first', 'A Core invariant breaks - the porch light\'s switch 13\' along the 12\' wall W2, '
   'FS-INV-501 - and so does FS_views\'s schema: Core\'s error is reported, and FS_views is not evaluated.',
   ['1.2.2'], vedit(lambda d: (BAD_V(d), GK(d, 'switches')['X13']['host'].update(wall='W2', offset=13 * FT))),
   [('FS-INV-501', ['X13'])])
VW('order', 'schema-before-invariants', 'The data breaks the schema and an invariant: only FS-VIEW-SCH-001.',
   ['1.2.2', '1.3.1'], vedit(lambda d: (BAD_V(d), INV_V(d))), [('FS-VIEW-SCH-001', [])])
VW('order', 'no-lints-when-invalid', 'An invariant breaks and a lint would apply too - the cutaway, looking steeply '
   'down, is made two-point: the document is invalid, so no lint is reported, FS_views\'s or Core\'s.',
   ['1.2.2', '1.2.3'], vedit(lambda d: (INV_V(d), LINT_V(d))), INV_V_DIAG)
VW('order', 'lighting-not-evaluated', 'FS_lighting\'s data breaks FS_lighting\'s own rules - a scene turns on the dimmer '
   'X10, and the Night light is named "Evening" - but this implementation does not implement FS_lighting: it reports '
   'nothing of FS_lighting, and reads its scenes as data, so the dusk view\'s scene is a scene. Valid.',
   ['3.3.1'],
   vedit(lambda d: (ON(d, 'LS2').update(X10={}), SCN(d)['LS2'].update(name='Evening'))))

VW('schema', 'data-not-an-object', 'FS_views\'s top-level data is an array: Core allows any JSON there, FS_views\'s '
   'schema does not.', ['1.3.1'], vedit(lambda d: d['extensions'].update({VIEW: []})), [('FS-VIEW-SCH-001', [])])
VW('schema', 'unknown-member', 'A top-level member FS_views does not define, `cameras`.', ['1.3.1'],
   vedit(lambda d: ext(d, VIEW).update(cameras={})), [('FS-VIEW-SCH-001', [])])
VW('schema', 'empty-collections', 'An empty `collections` member: FS_views adds no kind of element, so its data has '
   'no `collections`, even an empty one. Core finds no collection in it; FS_views\'s schema rejects it.', ['1.3.1'],
   vedit(lambda d: ext(d, VIEW).update(collections={})), [('FS-VIEW-SCH-001', [])])
VW('schema', 'a-collection', 'A collection `cameras` in FS_views\'s data: its registry entry names no kind, so Core '
   '12.4.1 reports it (FS-INV-604), and FS_views is not evaluated.', ['1.2.2', 'FS-CORE-12.4.1'],
   vedit(lambda d: ext(d, VIEW).update(collections={'cameras': {}})), [('FS-INV-604', [])])
VW('schema', 'views-not-an-object', 'FS_views\'s `views` is a list of views, not an object of them.', ['1.3.1'],
   vedit(lambda d: ext(d, VIEW).update(views=list(VWS(d).values()))), [('FS-VIEW-SCH-001', [])])
VW('schema', 'view-id-not-an-id', 'A view keyed by "Hero exterior", which is not an ID (Core 3.1.1).', ['1.3.1'],
   vedit(lambda d: VWS(d).update({'Hero exterior': VWS(d).pop('SV1')})), [('FS-VIEW-SCH-001', [])])
VW('schema', 'view-without-a-name', 'A view always has a name.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV4'].pop('name')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'empty-name', 'A view\'s name is 1 to 200 characters: never empty.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV4'].update(name='')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'name-too-long', 'A view\'s name is 1 to 200 characters.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV4'].update(name='N' * 201)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'view-without-an-eye', 'A view always has an eye.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].pop('eye')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'view-without-a-target', 'A view always has a target.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].pop('target')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'eye-of-two-lengths', 'An eye is a point in space, three lengths: [x, y] is a plan point, not one.',
   ['1.3.1'], vedit(lambda d: VWS(d)['SV1'].update(eye=VWS(d)['SV1']['eye'][:2])), [('FS-VIEW-SCH-001', [])])
VW('schema', 'target-of-four-lengths', 'A target of four lengths.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(target=VWS(d)['SV1']['target'] + [0])), [('FS-VIEW-SCH-001', [])])
VW('schema', 'eye-with-a-fraction', 'A length written with a fraction is not an integer, even when it is a whole '
   'number (1.4).', ['1.3.1'], None, [('FS-VIEW-SCH-001', [])],
   raw=(fmt(views_house()) + '\n').replace(f'{1600 * MM}', f'{1600 * MM}.0', 1).encode('utf-8'))
VW('schema', 'eye-in-millimetres', 'An eye written in millimetres as strings, ["-4000 mm", ...]: a length is an '
   'integer of base units.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(eye=['-4000 mm', '-7000 mm', '1600 mm'])), [('FS-VIEW-SCH-001', [])])
VW('schema', 'eye-beyond-a-length', 'An eye\'s height of 2^53 base units, one more than any length (Core 2.1).',
   ['1.3.1'], vedit(lambda d: VWS(d)['SV4']['eye'].__setitem__(2, 2 ** 53)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'focal-length-below-8', 'A focal length of 7 mm.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV2'].update(focalLength=7)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'focal-length-above-1200', 'A focal length of 1,201 mm.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV2'].update(focalLength=1201)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'two-point-not-a-boolean', 'Whether a view is two-point is true or false, not "yes".', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(twoPoint='yes')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'aspect-not-listed', 'An aspect of "2:1", which is not one of the four.', ['1.3.1'],
   vedit(BAD_V), [('FS-VIEW-SCH-001', [])])
VW('schema', 'aperture-not-listed', 'An aperture of "f/3.5", which is not one of the nine.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV2'].update(aperture='f/3.5')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'aperture-a-number', 'An aperture of 2.8: an aperture is written as its f-number, "f/2.8".', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV2'].update(aperture=28)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'focus-without-an-aperture', 'The island view focused at 1.8 m with no aperture: a distance in focus '
   'means nothing to a pinhole, and the schema requires `aperture` with `focus` (2.1).', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV2'].pop('aperture')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'focus-zero', 'A focus of 0: the distance in focus is a positive length.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV2'].update(focus=0)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'exposure-above-30', 'An exposure compensation of 31 tenths of a stop.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(exposure=31)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'exposure-below-minus-30', 'An exposure compensation of -31 tenths of a stop.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(exposure=-31)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'level-not-an-id', 'A level written as its name, "Ground floor", which is not an ID.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV4'].update(level='Ground floor')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'levels-without-a-level', 'The cutaway\'s `levels` without its `level`: the schema requires `level` with '
   '`levels` (2.1).', ['1.3.1'], vedit(lambda d: VWS(d)['SV4'].pop('level')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'levels-not-listed', 'A `levels` of "above", which is neither "cutaway" nor "only".', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV4'].update(levels='above')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'sky-not-listed', 'A sky of "sunset", which is not one of the five.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV3'].update(sky='sunset')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'at-without-a-time', 'An `at` of a date alone, "2026-06-21": it is a date and a time.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2026-06-21')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'at-with-a-space', 'An `at` of "2026-06-21 17:30", with a space for the T.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2026-06-21 17:30')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'at-hour-24', 'An `at` at 24:00: the hours are 00 to 23.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2026-06-21T24:00')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'at-month-13', 'An `at` in month 13.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2026-13-01T12:00')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'at-day-32', 'An `at` on day 32.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2026-01-32T12:00')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'at-with-fractional-seconds', 'An `at` with fractional seconds, "17:30:00.5": whole seconds only.',
   ['1.3.1'], vedit(lambda d: VWS(d)['SV1'].update(at='2026-06-21T17:30:00.5')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'at-offset-beyond-14-hours', 'An `at` with an offset of +15:00: offsets are at most 14 hours.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV3'].update(at='2026-10-15T18:40+15:00')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'at-offset-without-a-colon', 'An `at` with an offset of -0400: the offset is written ±HH:MM.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV3'].update(at='2026-10-15T18:40-0400')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'at-every-form', 'An `at` in each form the schema allows - with seconds, with Z, and with seconds and an '
   'offset of -14:00 - and the bounds of a focal length, an exposure and a focus: 8 mm and 1,200 mm, -30 and 30, a focus '
   'of 1. Valid.', ['1.3.1', '3.2.1'],
   vedit(lambda d: (VWS(d)['SV1'].update(at='2026-06-21T17:30:45', focalLength=8, exposure=-30),
                    VWS(d)['SV2'].update(at='2026-12-31T23:59Z', focalLength=1200, exposure=30, focus=1),
                    VWS(d)['SV3'].update(at='2026-10-15T18:40:00-14:00'))),
   check=lambda r: ensure(VDER(r) == VIEWED, VDER(r)))
VW('schema', 'lights-not-listed', 'Lights "dim", which is neither "off" nor "on": a dimmed house is a scene of '
   'FS_lighting.', ['1.3.1'], vedit(lambda d: VWS(d)['SV2'].update(lights='dim')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'lights-a-boolean', 'Lights true: they are "off" or "on".', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV2'].update(lights=True)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'scene-not-an-id', 'A scene written as its name, "Night light", which is not an ID (Core 3.1.1).',
   ['1.3.1'], vedit(lambda d: VWS(d)['SV3'].update(scene='Night light')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'view-with-an-unknown-member', 'A view has a member a view does not define: `fov`, an angle of view, '
   'which FS_views gives as a focal length.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(fov=74)), [('FS-VIEW-SCH-001', [])])
VW('schema', 'extras-not-an-object', 'A view\'s `extras` is an object (Core 1.7).', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(extras='shot list')), [('FS-VIEW-SCH-001', [])])
VW('schema', 'extras', 'A view\'s `extras`, data no specification defines: valid, and read by no one.', ['1.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(extras={'renderer': {'samples': 512}})),
   check=lambda r: ensure(VDER(r) == VIEWED, VDER(r)))

VW('invariants', 'view-id-of-a-light', 'The cutaway is keyed by X2, a pendant\'s ID: a view\'s ID is in the document\'s '
   'one space of IDs.', ['1.3.2'], vedit(lambda d: VWS(d).update(X2=VWS(d).pop('SV4'))), [('FS-VIEW-INV-001', ['X2'])])
VW('invariants', 'view-id-of-a-room', 'The island view is keyed by R1, the Kitchen\'s ID.', ['1.3.2'],
   vedit(lambda d: VWS(d).update(R1=VWS(d).pop('SV2'))), [('FS-VIEW-INV-001', ['R1'])])
VW('invariants', 'view-id-of-a-level', 'The cutaway is keyed by L1, the level it cuts away at.', ['1.3.2'],
   vedit(lambda d: VWS(d).update(L1=VWS(d).pop('SV4'))), [('FS-VIEW-INV-001', ['L1'])])
VW('invariants', 'view-id-of-a-lamp', 'The island view is keyed by X20, the table lamp\'s ID: an extension element of '
   'any extension, known or not.', ['1.3.2'],
   vedit(lambda d: VWS(d).update(X20=VWS(d).pop('SV2'))), [('FS-VIEW-INV-001', ['X20'])])
VW('invariants', 'view-id-of-a-program-item', 'The house has a program with an item P1, and the hero shot is keyed '
   'by P1.', ['1.3.2'],
   vedit(lambda d: (d.update(program={'items': {'P1': {'function': 'kitchen'}}}), VWS(d).update(P1=VWS(d).pop('SV1')))),
   [('FS-VIEW-INV-001', ['P1'])])
VW('invariants', 'view-id-of-a-scene', 'The dusk view is keyed by LS1, the ID of the FS_lighting scene it shows: a '
   'scene\'s ID is in the one space of IDs, read as data.', ['1.3.2'],
   vedit(lambda d: VWS(d).update(LS1=VWS(d).pop('SV3'))), [('FS-VIEW-INV-001', ['LS1'])])
VW('invariants', 'view-id-of-a-scene-without-lighting', 'The house without FS_lighting, and the cutaway keyed by '
   'LS1: there are no scenes, so LS1 is no one\'s ID. Valid.', ['1.3.2'],
   vedit(lambda d: (without_lighting(d), VWS(d).update(LS1=VWS(d).pop('SV4')))),
   check=lambda r: ensure(sorted(VDER(r)['views']) == ['LS1', 'SV1', 'SV2', 'SV3'], VDER(r)))
VW('invariants', 'eye-at-the-target', 'The island view\'s target is its eye.', ['2.2.1'], vedit(INV_V), INV_V_DIAG)
VW('invariants', 'eye-below-the-target', 'The island view looks straight up from its eye, at a point 1 base unit '
   'above it: the two differ, so it looks somewhere. Valid.', ['2.2.1'],
   vedit(lambda d: VWS(d)['SV2'].update(target=pt(600, 600, 1500)[:2] + [1500 * MM + 1], twoPoint=False)),
   check=lambda r: ensure(r['valid'] and r['diagnostics'] == [], r['diagnostics']))
VW('invariants', 'level-of-nothing', 'The cutaway cuts away above L2, which the house does not have.', ['3.1.1'],
   vedit(lambda d: VWS(d)['SV4'].update(level='L2')), [('FS-VIEW-INV-003', ['SV4'])])
VW('invariants', 'level-of-a-room', 'The cutaway cuts away above R1, the Kitchen: a room is no level.', ['3.1.1'],
   vedit(lambda d: VWS(d)['SV4'].update(level='R1')), [('FS-VIEW-INV-003', ['SV4'])])
VW('invariants', 'level-only', 'The cutaway shows L1 only: valid, and its level derived.', ['3.1.1', '6.1.1'],
   vedit(lambda d: VWS(d)['SV4'].update(levels='only')),
   check=lambda r: ensure(VDER(r)['views']['SV4']['level'] == 'L1', VDER(r)))
VW('invariants', 'scene-of-nothing', 'The dusk view shows the scene LS9, which FS_lighting\'s data does not have.',
   ['3.3.1'], vedit(lambda d: VWS(d)['SV3'].update(scene='LS9')), [('FS-VIEW-INV-004', ['SV3'])])
VW('invariants', 'scene-of-a-light', 'The dusk view shows X2, a pendant: a light is no scene.', ['3.3.1'],
   vedit(lambda d: VWS(d)['SV3'].update(scene='X2')), [('FS-VIEW-INV-004', ['SV3'])])
VW('invariants', 'scene-of-another-scene', 'The dusk view shows LS2, the Night light: any scene of FS_lighting\'s data. '
   'Valid.', ['3.3.1', '6.1.1'], vedit(lambda d: VWS(d)['SV3'].update(scene='LS2')),
   check=lambda r: ensure(VDER(r)['views']['SV3'] == {'name': 'Dusk from the garden', 'level': None, 'lights': 'on',
                                                      'scene': 'LS2'}, VDER(r)))
VW('invariants', 'scene-without-lighting', 'The house without FS_lighting, and the dusk view still showing LS1: a '
   'document without FS_lighting\'s data has no scenes (1.3).', ['3.3.1'],
   vedit(lambda d: (without_lighting(d), VWS(d)['SV3'].update(scene='LS1'))), [('FS-VIEW-INV-004', ['SV3'])])
VW('invariants', 'scene-of-lighting-data-not-an-object', 'FS_lighting\'s data is a string, which no implementation of '
   'FS_views checks: it holds no scene, so LS1 names none.', ['3.3.1'],
   vedit(lambda d: d['extensions'].update({LGHT: 'evening only'})), [('FS-VIEW-INV-004', ['SV3'])])
VW('invariants', 'scene-of-scenes-not-an-object', 'FS_lighting\'s `scenes` is a list of scenes: a `scenes` that is not '
   'an object holds no scene (1.3), and a view keyed LS1 is then no scene\'s either.', ['1.3.2', '3.3.1'],
   vedit(lambda d: (ext(d, LGHT).update(scenes=list(SCN(d).values())), VWS(d).update(LS1=VWS(d).pop('SV4')))),
   [('FS-VIEW-INV-004', ['SV3'])])
VW('invariants', 'scene-and-lights-off', 'The dusk view shows the Evening scene with its lights "off".', ['3.3.2'],
   vedit(lambda d: VWS(d)['SV3'].update(lights='off')), [('FS-VIEW-INV-005', ['SV3'])])
VW('invariants', 'scene-and-lights-on', 'The dusk view shows the Evening scene and says its lights are "on": valid.',
   ['3.3.2', '6.1.1'], vedit(lambda d: VWS(d)['SV3'].update(lights='on')),
   check=lambda r: ensure(VDER(r) == VIEWED, VDER(r)))
VW('invariants', 'scene-of-nothing-and-lights-off', 'The dusk view shows the scene LS9, which does not exist, with its '
   'lights "off": both reported.', ['1.2.3', '3.3.1', '3.3.2'],
   vedit(lambda d: VWS(d)['SV3'].update(scene='LS9', lights='off')),
   [('FS-VIEW-INV-004', ['SV3']), ('FS-VIEW-INV-005', ['SV3'])])
VW('invariants', 'two-views-one-name', 'The cutaway renamed "Hero exterior".', ['2.1.1'],
   vedit(lambda d: VWS(d)['SV4'].update(name='Hero exterior')), [('FS-VIEW-INV-006', ['SV1', 'SV4'])])
VW('invariants', 'three-views-one-name', 'Three views named "Kitchen island": once for each pair.', ['1.2.3', '2.1.1'],
   vedit(lambda d: (VWS(d)['SV3'].update(name='Kitchen island'), VWS(d)['SV4'].update(name='Kitchen island'))),
   [('FS-VIEW-INV-006', ['SV2', 'SV3']), ('FS-VIEW-INV-006', ['SV2', 'SV4']), ('FS-VIEW-INV-006', ['SV3', 'SV4'])])
VW('invariants', 'names-differ-in-case', 'The cutaway named "hero exterior": names are compared exactly, so it is '
   'another name. Valid.', ['2.1.1'], vedit(lambda d: VWS(d)['SV4'].update(name='hero exterior')))
VW('invariants', 'name-of-a-scene', 'The dusk view named "Evening", as the scene it shows is: a view and a scene may '
   'share a name. Valid.', ['2.1.1'], vedit(lambda d: VWS(d)['SV3'].update(name='Evening')))
VW('invariants', 'at-31-april', 'The hero shot at 17:30 on 31 April, a day April does not have.', ['3.2.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2026-04-31T17:30')), [('FS-VIEW-INV-007', ['SV1'])])
VW('invariants', 'at-31-june', 'The hero shot on 31 June.', ['3.2.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2026-06-31T17:30')), [('FS-VIEW-INV-007', ['SV1'])])
VW('invariants', 'at-30-february', 'The hero shot on 30 February, a day no February has.', ['3.2.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2028-02-30T12:00')), [('FS-VIEW-INV-007', ['SV1'])])
VW('invariants', 'at-29-february-2027', 'The hero shot on 29 February 2027, which is not a leap year.', ['3.2.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2027-02-29T12:00')), [('FS-VIEW-INV-007', ['SV1'])])
VW('invariants', 'at-29-february-2028', 'The hero shot on 29 February 2028, a leap year. Valid.', ['3.2.1'],
   vedit(lambda d: VWS(d)['SV1'].update(at='2028-02-29T12:00')))
VW('invariants', 'at-29-february-2100', 'The hero shot on 29 February 2100: divisible by 100 and not by 400, so not a '
   'leap year.', ['3.2.1'], vedit(lambda d: VWS(d)['SV1'].update(at='2100-02-29T12:00')), [('FS-VIEW-INV-007', ['SV1'])])
VW('invariants', 'at-29-february-2000', 'The hero shot on 29 February 2000: divisible by 400, so a leap year. Valid.',
   ['3.2.1'], vedit(lambda d: VWS(d)['SV1'].update(at='2000-02-29T12:00Z')))
VW('invariants', 'at-the-last-days', 'The views on the last day of months of 30 and 31 days - 30 April, 31 May, '
   '30 September, 31 December - with an offset of -14:00 and +14:00 on the last two. Valid.', ['3.2.1'],
   vedit(lambda d: (VWS(d)['SV1'].update(at='2026-04-30T17:30'), VWS(d)['SV2'].update(at='2026-05-31T09:00'),
                    VWS(d)['SV3'].update(at='2026-09-30T19:00-14:00'), VWS(d)['SV4'].update(at='2026-12-31T23:59:59+14:00'))))
VW('invariants', 'every-one-once', 'Every invariant broken at once - SV5 breaking three: each is reported once, '
   'naming its view, or both views of a name.', ['1.2.3', '1.3.2', '2.1.1', '2.2.1', '3.1.1', '3.2.1', '3.3.1', '3.3.2'],
   vedit(lambda d: (VWS(d).update(X1=VWS(d).pop('SV1')), INV_V(d), VWS(d)['SV4'].update(level='L9'),
                    VWS(d)['SV3'].update(scene='LS9'),
                    VWS(d).update(SV5={'name': 'Porch', 'eye': pt(2000, -2000, 1600), 'target': pt(1829, 0, 2000),
                                       'scene': 'LS2', 'lights': 'off', 'at': '2027-02-29T20:00'},
                                  SV6={'name': 'Porch', 'eye': pt(2000, -3000, 1600), 'target': pt(1829, 0, 2000)}))),
   [('FS-VIEW-INV-001', ['X1']), ('FS-VIEW-INV-002', ['SV2']), ('FS-VIEW-INV-003', ['SV4']),
    ('FS-VIEW-INV-004', ['SV3']), ('FS-VIEW-INV-005', ['SV5']), ('FS-VIEW-INV-006', ['SV5', 'SV6']),
    ('FS-VIEW-INV-007', ['SV5'])])

VW('lints', 'two-point-looking-down-steeply', 'The cutaway, looking down at about 45 degrees from high above, is made '
   'two-point: steeper than 30 degrees.', ['1.2.3', '2.3.1'], vedit(LINT_V), [('FS-VIEW-LINT-001', ['SV4'])])
VW('lints', 'steep-without-two-point', 'The cutaway looks down just as steeply, without two-point perspective: no '
   'lint.', ['1.2.3', '2.3.1'], views_house())
VW('lints', 'two-point-looking-up-steeply', 'The hero shot looks up at the ridge from close to the south wall - 2 m '
   'across and 3 m up: steeper than 30 degrees.', ['1.2.3', '2.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(eye=pt(3048, -2000, 1600), target=pt(3048, 0, 4600))),
   [('FS-VIEW-LINT-001', ['SV1'])])
VW('lints', 'two-point-just-steeper-than-30', 'The hero shot\'s line of sight rises 1,000 units over 1,732 across: '
   '3 x 1,000,000 > 2,999,824, just steeper than 30 degrees.', ['1.2.3', '2.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(eye=[0, -2000000, 1600000], target=[1732, -2000000, 1601000])),
   [('FS-VIEW-LINT-001', ['SV1'])])
VW('lints', 'two-point-just-shallower-than-30', 'The hero shot\'s line of sight rises 1,000 units over 1,733 across: '
   '3 x 1,000,000 < 3,003,289, just shallower than 30 degrees. No lint.', ['1.2.3', '2.3.1'],
   vedit(lambda d: VWS(d)['SV1'].update(eye=[0, -2000000, 1600000], target=[1733, -2000000, 1601000])))
VW('lints', 'two-point-across-a-diagonal', 'The hero shot rises 1,000 units over 1,000 east and 1,000 north - '
   '3,000,000 > 2,000,000 - and the island view falls 1,000 over 1,000 east and 1,500 north - 3,000,000 < 3,250,000: '
   'the horizontal distance counts both ways. One lint.', ['1.2.3', '2.3.1'],
   vedit(lambda d: (VWS(d)['SV1'].update(eye=[0, -2000000, 1600000], target=[1000, -1999000, 1601000]),
                    VWS(d)['SV2'].update(eye=[768000, 768000, 1920000], target=[769000, 769500, 1919000]))),
   [('FS-VIEW-LINT-001', ['SV1'])])
VW('lints', 'two-point-straight-down', 'A two-point view SV5 straight down onto the island, its eye above its target: '
   'no level line of sight at all.', ['1.2.3', '2.3.1'],
   vedit(lambda d: VWS(d).update(SV5={'name': 'Island from above', 'eye': pt(1829, 1829, 2600),
                                      'target': pt(1829, 1829, 900), 'twoPoint': True})),
   [('FS-VIEW-LINT-001', ['SV5'])])
VW('lints', 'two-point-level', 'The hero shot looks level, its eye and target at the same height. No lint.',
   ['1.2.3', '2.3.1'], vedit(lambda d: VWS(d)['SV1'].update(target=pt(3048, 1829, 1600))))
VW('lints', 'every-view-once', 'The cutaway and a straight-down view SV5 both two-point: each view once.',
   ['1.2.3', '2.3.1'],
   vedit(lambda d: (LINT_V(d), VWS(d).update(SV5={'name': 'Island from above', 'eye': pt(1829, 1829, 2600),
                                                   'target': pt(1829, 1829, 900), 'twoPoint': True}))),
   [('FS-VIEW-LINT-001', ['SV4']), ('FS-VIEW-LINT-001', ['SV5'])])

VW('derived', 'defaults', 'A view SV5 "Porch" of only a name, an eye and a target: no level and no scene, so both '
   'null, and its lights off.', ['6.1.1'],
   vedit(lambda d: VWS(d).update(SV5={'name': 'Porch', 'eye': pt(1829, -3000, 1600), 'target': pt(1829, 0, 1800)})),
   check=lambda r: ensure(VDER(r)['views']['SV5'] == {'name': 'Porch', 'level': None, 'lights': 'off', 'scene': None},
                          VDER(r)['views']))
VW('derived', 'lights-on-by-a-scene', 'The dusk view says nothing of `lights` and shows a scene: its lights are on; '
   'the island view says "on" and shows no scene: on as well; the hero shot says "off": off.', ['6.1.1'],
   vedit(lambda d: VWS(d)['SV1'].update(lights='off')),
   check=lambda r: ensure([VDER(r)['views'][v]['lights'] for v in ('SV1', 'SV2', 'SV3', 'SV4')] == ['off', 'on', 'on', 'off'],
                          VDER(r)['views']))
VW('derived', 'views-in-id-order', 'A fifth view SV10 "Late": views are in ID order by code unit, SV1, SV10, SV2.',
   ['6.1.1'],
   vedit(lambda d: VWS(d).update(SV10={'name': 'Late', 'eye': pt(7500, -3000, 1700), 'target': pt(3048, 1829, 1200),
                                       'sky': 'night', 'scene': 'LS2', 'lights': 'on'})),
   check=lambda r: ensure(list(VDER(r)['views']) == ['SV1', 'SV10', 'SV2', 'SV3', 'SV4']
                          and VDER(r)['views']['SV10'] == {'name': 'Late', 'level': None, 'lights': 'on', 'scene': 'LS2'},
                          VDER(r)))


def view_options(d):
    """The lit house's island options (island_options()) - the pendants in option A, the primary, and
    a linear pendant X8 in option B - with the house's views."""
    island_options(d)


VW('options', 'view-id-of-an-option-element', 'Island options A and B as Core 0.3 design options (Core 19), and the '
   'island view keyed by X8, the ID of option B\'s linear pendant: FS_views is evaluated in each checked design, so '
   'B\'s design breaks 1.3.2, reported with `design` (Core 19.5.2); A\'s, without X8, does not.',
   ['1.2.1', '1.2.3', '1.3.2', 'FS-CORE-19.3.1'],
   vedit(lambda d: (view_options(d), VWS(d).update(X8=VWS(d).pop('SV2')))), [('FS-VIEW-INV-001', ['X8'], 'OP2')])
VW('options', 'views-of-every-design', 'The same options with the views as they are: every view is valid in every '
   'design. Valid, and the primary design derived.', ['1.2.1', '1.2.4', '6.1.1', 'FS-CORE-19.3.1'],
   vedit(view_options),
   check=lambda r: ensure(VDER(r) == VIEWED and r['derived']['options']['OS1']['chosen'] == 'OP1', VDER(r)))


def view_derived(d):
    data = json.dumps(d).encode('utf-8')
    result, _, _ = check(data, ext_reader(data), json.dumps([entry(VIEW)]).encode('utf-8'), official.implemented(VIEW))
    assert result['valid'], result['diagnostics']
    return result['derived']['extensions'][VIEW]


BATH = {'name': 'Living room', 'eye': pt(5900, 3400, 1500), 'target': pt(4300, 2400, 1100), 'focalLength': 16,
        'twoPoint': True, 'aspect': '4:5', 'scene': 'LS2', 'sky': 'night'}
VO = lambda *a, **k: O(VIEW, *a, **k)    # noqa: E731
VO('add-a-view', 'setProperty of $document /extensions/FS_views/views/SV5 adds a view "Living room" - a 16 mm '
   'portrait two-point view at night with the Night light on - with an ID Ops does not mint (1.3.2). It commits, '
   'valid under FS_views.', ['1.2.1', '1.3.2', '3.3.1', '6.1.1', 'FS-OPS-2.3.1'], views_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_views/views/SV5', 'value': BATH}]},
   check=lambda r, B: ensure(view_derived(B)['views']['SV5'] == {'name': 'Living room', 'level': None, 'lights': 'on',
                                                                 'scene': 'LS2'}, view_derived(B)))
VO('first-view-creates-the-data', 'The house declaring FS_views with no data of it yet: setProperty of $document '
   '/extensions/FS_views/views/SV1 creates FS_views\'s data, and its `views`, on the way (Ops 2.3) - the hero shot. It '
   'commits, valid under FS_views.', ['1.2.1', '1.3.1', '6.1.1', 'FS-OPS-2.3.1'],
   vedit(lambda d: d['extensions'].pop(VIEW)),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_views/views/SV1', 'value': VIEWS['SV1']}]},
   check=lambda r, B: ensure(B['extensions'][VIEW] == {'views': {'SV1': VIEWS['SV1']}}
                             and view_derived(B) == {'views': {'SV1': VIEWED['views']['SV1']}}, B['extensions'].get(VIEW)))
VO('rename-a-view', 'setProperty of $document /extensions/FS_views/views/SV1/name: the hero shot is now "Front of '
   'house". It commits.', ['1.2.1', '2.1.1', 'FS-OPS-2.3.1'], views_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_views/views/SV1/name',
               'value': 'Front of house'}]},
   check=lambda r, B: ensure(view_derived(B)['views']['SV1']['name'] == 'Front of house', view_derived(B)['views']))
VO('rename-to-a-name-in-use-is-rejected', 'setProperty of the cutaway\'s name to "Hero exterior": the result breaks '
   '2.1.1, and an applier that implements FS_views and knows it rejects the batch (Ops 1.2.3).',
   ['2.1.1', '1.2.1', 'FS-OPS-1.2.3'], views_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_views/views/SV4/name',
               'value': 'Hero exterior'}]},
   'rejected', [('FS-VIEW-INV-006', ['SV1', 'SV4'])])
VO('remove-a-view', 'unsetProperty of $document /extensions/FS_views/views/SV4 removes the cutaway. It commits.',
   ['1.2.1', '6.1.1', 'FS-OPS-2.3.1'], views_house(),
   {'batch': [{'op': 'unsetProperty', 'id': '$document', 'path': '/extensions/FS_views/views/SV4'}]},
   check=lambda r, B: ensure(list(view_derived(B)['views']) == ['SV1', 'SV2', 'SV3'], view_derived(B)))
VO('replace-a-view', 'setProperty of $document /extensions/FS_views/views/SV2 replaces the island view\'s record: a '
   '35 mm view from the Kitchen\'s north-east corner, 3:2, everything in focus, with the Evening scene at dusk. It '
   'commits, and nothing of the old record is left.', ['1.2.1', '2.2.1', '3.3.1', '6.1.1', 'FS-OPS-2.3.1'],
   views_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_views/views/SV2',
               'value': {'name': 'Kitchen island', 'eye': pt(3300, 3300, 1500), 'target': pt(1829, 1829, 950),
                         'twoPoint': True, 'sky': 'dusk', 'scene': 'LS1'}}]},
   check=lambda r, B: ensure('aperture' not in ext(B, VIEW)['views']['SV2']
                             and view_derived(B)['views']['SV2'] == {'name': 'Kitchen island', 'level': None,
                                                                     'lights': 'on', 'scene': 'LS1'},
                             ext(B, VIEW)['views']['SV2']))
VO('eye-at-the-target-is-rejected', 'setProperty of $document /extensions/FS_views/views/SV1/target to the hero '
   'shot\'s own eye: the result breaks 2.2.1, and the batch is rejected with FS-VIEW-INV-002.',
   ['2.2.1', '1.2.1', 'FS-OPS-1.2.3'], views_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_views/views/SV1/target',
               'value': VIEWS['SV1']['eye']}]},
   'rejected', [('FS-VIEW-INV-002', ['SV1'])])
VO('remove-a-scene-a-view-shows-is-rejected', 'unsetProperty of $document /extensions/FS_lighting/scenes/LS1 removes the '
   'Evening scene, which the dusk view shows: an applier that implements FS_views - and not FS_lighting - reads the '
   'scenes as data, so the result breaks 3.3.1, and the batch is rejected.', ['3.3.1', '1.2.1', 'FS-OPS-1.2.3'],
   views_house(), {'batch': [{'op': 'unsetProperty', 'id': '$document', 'path': '/extensions/FS_lighting/scenes/LS1'}]},
   'rejected', [('FS-VIEW-INV-004', ['SV3'])])


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
        for name in ALL + (STRC, LAND, LGHT, VIEW):
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

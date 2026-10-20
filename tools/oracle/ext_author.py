"""The conformance suites of the official extensions - FS_electrical, FS_plumbing, FS_mechanical,
FS_lowvoltage, FS_furniture, FS_structural, FS_landscape, FS_lighting, FS_views, FS_renovation, FS_annotation and FS_site 0.1.0 - as the script that
writes them.

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
on, a view from the garden at dusk with the "Evening" scene, and a cutaway from above. FS_renovation's start from a kitchen
remodel (remodel() below) - the framed house's plan with a wall, its door, a room and a counter to be demolished, and a
new wall, door, window, room, island and deck. FS_annotation's start from the lit house with views, a kitchen window and its
owner's annotation (annotation_house() below) - an overall string along the south side, a string locating the window by its
centre, the Kitchen's clear width between two wall faces, a north-south string of clear dimensions through two rooms, and two
notes with leaders. FS_site's start from the garden on a slope (site_house() below) - the Phase 13 garden as a Core 0.4
document on a 70' lot that falls to the street, with setbacks, a survey of spots and contour lines, the patio as a patio
slab and a pad under the house. Every expected diagnostic is written by hand and cross-checked against the
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
from tools.oracle.ops.version import OPS_02, OPS_03, OPS_04
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
    """An Ops test - Ops 0.2, or Ops 0.3 or 0.4 for a document declaring "0.3" or "0.4" - applied by an applier that
    implements the extension and knows it."""
    TESTS.append(dict(kind='ops', ext=name, group='ops', slug=slug, description=description, covers=cov(name, covers),
                      doc=a, request=request, registry=[entry(name)], status=status, check=check, diags=hand(diags)))


def ops_profile(doc):
    """The Ops draft an extension suite's Ops test is applied as: Ops 0.3 for a document declaring "0.3", Ops 0.4 for
    one declaring "0.4" (FS_site's), Ops 0.2 for every other."""
    v = doc.get('floorspec') if isinstance(doc, dict) else None
    return OPS_04 if v == '0.4' else OPS_03 if v == '0.3' else OPS_02


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


# ============================================================================= FS_renovation

RENO = 'FS_renovation'
CODE[RENO] = 'RENO'


def RS(status):
    """FS_renovation's data on a core element."""
    return {RENO: {'status': status}}


def RW(s, e, t, status=None):
    w = {'level': 'L1', 'start': s, 'end': e, 'type': t}
    if status is not None:
        w['extensions'] = RS(status)
    return w


def remodel():
    """The kitchen remodel: the framed house's plan, 20' x 12', on L1 (see framed()), with 6 1/2"
    exterior and 4 1/2" interior walls, as it stands and as it will be. The south wall and the
    Bath's south wall are drawn in two, at x = 16', where a new wall meets them.

    As it stands: the Kitchen R1 (12' x 12', west), the Bath R2 (north-east) and the Utility room R3
    (south-east), with the back door O1 and the Kitchen window O2, the Bath's door O3 from the
    Utility room, and the Utility room's door O4 from the Kitchen in the interior wall W8; a
    refrigerator X3 against W9, and an old counter X1 against W8, FS_furniture elements read as
    extension elements (FS_furniture is not known to the suite's implementation).

    The work: W8 comes down with its door O4, the Utility room R3 and the counter X1 ("demolish"), so
    the Kitchen takes the Utility room's west half; a new wall W12 at x = 16' with a new door O5 makes a
    Laundry R4 of its east half; a new window O6 in the existing south wall W11 lights the Kitchen's new
    floor; an island X2 stands in the Kitchen; and a deck S1, 8' x 7', is built south of the house
    ("new"). J7's join, W8 and W9 running through and W10 butting, goes with W8 in the proposed state."""
    d = {
        'floorspec': '0.2', 'project': {'name': 'Kitchen remodel'},
        'buildings': {'B1': {}}, 'levels': {'L1': {'building': 'B1', 'elevation': 0, 'height': H}},
        'types': {'EXT': {'kind': 'wallType', 'layers': [{'thickness': EXT_T, 'function': 'core'}]},
                  'INT': {'kind': 'wallType', 'layers': [{'thickness': INT_T, 'function': 'core'}]}},
        'junctions': {'J1': J(0, 0), 'J2': J(0, 12 * FT), 'J3': J(12 * FT, 12 * FT), 'J4': J(20 * FT, 12 * FT),
                      'J5': J(20 * FT, 0), 'J6': J(12 * FT, 0), 'J7': {**J(12 * FT, 6 * FT), 'join': {'kind': 'butt', 'through': ['W8', 'W9']}},
                      'J8': J(20 * FT, 6 * FT), 'J9': J(16 * FT, 0), 'J10': J(16 * FT, 6 * FT)},
        'walls': {
            'W1': RW('J1', 'J2', 'EXT'), 'W2': RW('J2', 'J3', 'EXT'), 'W3': RW('J3', 'J4', 'EXT'),
            'W4': RW('J4', 'J8', 'EXT'), 'W5': RW('J8', 'J5', 'EXT'), 'W6': RW('J5', 'J9', 'EXT'),
            'W11': RW('J9', 'J6', 'EXT'), 'W7': RW('J6', 'J1', 'EXT'),
            'W8': RW('J6', 'J7', 'INT', 'demolish'), 'W9': RW('J7', 'J3', 'INT'),
            'W10': RW('J7', 'J10', 'INT'), 'W13': RW('J10', 'J8', 'INT'),
            'W12': RW('J9', 'J10', 'INT', 'new')},
        'openings': {
            'O1': {'wall': 'W7', 'offset': 3 * FT, 'width': 3 * FT, 'height': 80 * IN, 'name': 'Back door'},
            'O2': {'wall': 'W2', 'offset': 4 * FT, 'width': 4 * FT, 'height': 48 * IN, 'sill': 36 * IN, 'name': 'Kitchen window'},
            'O3': {'wall': 'W10', 'offset': FT, 'width': 30 * IN, 'height': 80 * IN, 'name': 'Bath door'},
            'O4': {'wall': 'W8', 'offset': FT, 'width': 30 * IN, 'height': 80 * IN, 'name': 'Utility door',
                   'extensions': RS('demolish')},
            'O5': {'wall': 'W12', 'offset': FT, 'width': 30 * IN, 'height': 80 * IN, 'name': 'Laundry door',
                   'extensions': RS('new')},
            'O6': {'wall': 'W11', 'offset': FT, 'width': 2 * FT, 'height': 36 * IN, 'sill': 42 * IN, 'name': 'New window',
                   'extensions': RS('new')}},
        'rooms': {'R1': {'level': 'L1', 'anchor': [6 * FT, 6 * FT], 'name': 'Kitchen', 'function': 'kitchen'},
                  'R2': {'level': 'L1', 'anchor': [16 * FT, 9 * FT], 'name': 'Bath', 'function': 'bath'},
                  'R3': {'level': 'L1', 'anchor': [14 * FT, 3 * FT], 'name': 'Utility', 'function': 'mechanical',
                         'extensions': RS('demolish')},
                  'R4': {'level': 'L1', 'anchor': [18 * FT, 3 * FT], 'name': 'Laundry', 'function': 'laundry',
                         'extensions': RS('new')}},
        'slabs': {'S1': {'level': 'L1', 'boundary': [[2 * FT, -8 * FT], [10 * FT, -8 * FT], [10 * FT, -FT], [2 * FT, -FT]],
                         'thickness': 3 * IN // 2, 'name': 'Deck', 'extensions': RS('new')}},
        'extensionsUsed': {FURN: '0.1.0', RENO: '0.1.0'},
        'extensions': {
            FURN: {'collections': {
                'casework': {
                    'X1': {'fallback': {'level': 'L1', 'box': box(0, -900, 0, 600, 900, 900)},
                           'host': wall_host('W8', 'left', 3 * FT), 'name': 'Old counter'},
                    'X2': {'fallback': {'level': 'L1', 'box': box(-500, -1000, 0, 500, 1000, 900)},
                           'host': floor_host('R1', 6 * FT, 6 * FT), 'name': 'Island'}},
                'appliances': {
                    'X3': {'fallback': {'level': 'L1', 'box': box(0, -450, 0, 700, 450, 1800)},
                           'host': wall_host('W9', 'left', 3 * FT), 'name': 'Refrigerator'}}}},
            RENO: {'elements': {'X1': 'demolish', 'X2': 'new'}}},
    }
    return d


def redit(fn):
    """The kitchen remodel, changed by fn(d) in place."""
    d = remodel()
    fn(d)
    return d


def RD(d, c, eid):
    """The FS_renovation data on a core element, created when missing."""
    return d[c][eid].setdefault('extensions', {}).setdefault(RENO, {})


def RTOP(d):
    return d['extensions'][RENO].setdefault('elements', {})


def unmark_all(d):
    """Every status removed: the house as it stands, nothing to do."""
    for c in ('walls', 'openings', 'rooms', 'slabs'):
        for el in d[c].values():
            el.get('extensions', {}).pop(RENO, None)
            if el.get('extensions') == {}:
                el.pop('extensions')
    d['extensions'][RENO] = {}
    d['walls'].pop('W12')
    d['openings'].pop('O5')
    d['openings'].pop('O6')
    d['rooms'].pop('R4')
    d['slabs'].pop('S1')
    coll(d, FURN, 'casework').pop('X2')


R = lambda *a, **k: V(RENO, *a, **k)    # noqa: E731
RDER = derived_of(RENO)
KITCHEN_W, KITCHEN_D = 12 * FT - EXT_T // 2 - INT_T // 2, 12 * FT - EXT_T      # the Kitchen as it stands
SQ = lambda a2: (str(a2 // 2) if a2 % 2 == 0 else f'{a2 // 2}.5')              # noqa: E731
STATUS = {'existing': ['O1', 'O2', 'O3', 'R1', 'R2', 'W1', 'W10', 'W11', 'W13', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7',
                       'W9', 'X3'],
          'demolish': ['O4', 'R3', 'W8', 'X1'],
          'new': ['O5', 'O6', 'R4', 'S1', 'W12', 'X2']}


def q(walls=0, wall_length=0, separators=0, openings=0, rooms=0, slabs=0, slab_area='0', roofs=0, stairs=0, elements=0):
    return {'walls': walls, 'wallLength': wall_length, 'separators': separators, 'openings': openings, 'rooms': rooms,
            'slabs': slabs, 'slabArea': slab_area, 'roofs': roofs, 'stairs': stairs, 'elements': elements}


QUANTITIES = {
    'existing': q(11, 2 * 12 * FT + 2 * 20 * FT + 6 * FT + 4 * FT + 4 * FT, openings=3, rooms=2, elements=1),
    'demolish': q(1, 6 * FT, openings=1, rooms=1, elements=1),
    'new': q(1, 6 * FT, openings=2, rooms=1, slabs=1, slab_area=str(8 * 7 * FT * FT), elements=1),
}


def check_reno(r):
    x = RDER(r)
    ensure(x['status'] == STATUS and x['quantities'] == QUANTITIES, x)
    ex, pr = x['states']['existing'], x['states']['proposed']
    ensure(sorted(ex['rooms']) == ['R1', 'R2', 'R3'] and sorted(pr['rooms']) == ['R1', 'R2', 'R4'], x['states'])
    # the Kitchen as it stands is the clear 12' x 12' less half of each wall around it; in the proposed state
    # it takes the Utility room's west half; the Bath does not change; the house's net area grows by the
    # 4 1/2" of floor W8 stood on, less the new wall W12's
    ensure(ex['rooms']['R1'] == SQ(2 * KITCHEN_W * KITCHEN_D), ex['rooms']['R1'])
    ensure(int(pr['rooms']['R1']) > int(ex['rooms']['R1']) and pr['rooms']['R2'] == ex['rooms']['R2'], x['states'])
    total = lambda s: sum(int(a) for a in s['rooms'].values())                     # noqa: E731
    ensure(str(total(ex)) == ex['area'] and str(total(pr)) == pr['area'], x['states'])
    ensure(total(pr) - total(ex) == INT_T * (6 * FT - EXT_T // 2 - INT_T // 2) - INT_T * (6 * FT - EXT_T // 2 - INT_T // 2),
           (total(pr), total(ex)))


def reno_derived(d, design=None):
    """What an implementation of FS_renovation that knows it derives for d."""
    data = json.dumps(d).encode('utf-8')
    result, _, _ = check(data, ext_reader(data), json.dumps([entry(RENO)]).encode('utf-8'), official.implemented(RENO),
                         None, design)
    assert result['valid'], result['diagnostics']
    return result['derived']['extensions'][RENO]


BAD_R = lambda d: RD(d, 'walls', 'W8').update(status='remove')                   # noqa: E731  the schema tier
INVALID_R = lambda d: RD(d, 'openings', 'O3').update(status='new')               # noqa: E731  FS-RENO-INV-002
INVALID_R_DIAG = [('FS-RENO-INV-002', ['O3', 'W10'])]

R('examples', 'kitchen-remodel', 'The kitchen remodel, read by an implementation of FS_renovation that knows it: the '
  'wall between the Kitchen and the Utility room is to come down with its door, the Utility room and an old counter; a '
  'new wall and door make a Laundry of the Utility room\'s east half, a new window lights the Kitchen\'s new floor, an '
  'island is new, and so is a deck. It is valid - the combined document, and each state\'s view - reports nothing, and '
  'derives the IDs of each status, the quantities of each - walls, wall length, openings, rooms, slabs and slab area, '
  'extension elements - and the rooms of each state with their net areas: the Kitchen 12\' x 12\' as it stands and '
  'with the Utility room\'s west half when the work is done.',
  ['1.2.1', '1.2.3', '1.2.4', '1.3.1', '1.3.2', '2.3.1', '2.4.1', '2.4.2', '5.1.1'], remodel(), check=check_reno)
R('examples', 'core-only-reader', 'The same house read with no known extensions: FS_renovation is not evaluated, so '
  'nothing of it is derived (`derived.extensions` is empty), and Core reads the combined document - W8 and W12 both '
  'standing, and the Utility room R3 and the Laundry R4 each a room (Core 1.6.9).', ['1.2.1', '1.2.4', 'FS-CORE-1.6.9'],
  remodel(), registry=None,
  check=lambda r: ensure(r['derived']['extensions'] == {} and sorted(r['derived']['rooms']) == ['R1', 'R2', 'R3', 'R4'],
                         r['derived']['extensions']))
R('examples', 'all-official-known', 'The house read with every official entry known but FS_furniture\'s - whose kinds '
  'ask for a model and a symbol the remodel\'s casework does not carry - by an implementation of FS_renovation alone: '
  'only FS_renovation is evaluated and derived.',
  ['1.2.1', '1.2.4'], remodel(), registry=[entry(x) for x in ALL_KNOWN + (VIEW, RENO) if x != FURN],
  check=lambda r: ensure(list(r['derived']['extensions']) == [RENO], list(r['derived']['extensions'])))
R('examples', 'the-house-as-it-stands', 'The house before the remodel is drawn: no element has a status, so every one '
  'is existing (2.1) and both states are the document. Valid, with FS-RENO-LINT-001 - the document uses FS_renovation '
  'and describes no work - and the two states derive the same rooms and areas.',
  ['1.2.3', '1.3.1', '5.1.1'], redit(unmark_all), [('FS-RENO-LINT-001', [])],
  check=lambda r: ensure(RDER(r)['status']['demolish'] == [] and RDER(r)['status']['new'] == []
                         and RDER(r)['states']['existing'] == RDER(r)['states']['proposed'], RDER(r)))
R('examples', 'every-status-written', 'Every element that may have a status says "existing" when it is: the same '
  'remodel, the same derived values. An absent status and "existing" are one status.', ['1.3.2', '5.1.1'],
  redit(lambda d: ([RD(d, c, eid).setdefault('status', 'existing') for c in ('walls', 'openings', 'rooms', 'slabs')
                    for eid in d[c]], RTOP(d).setdefault('X3', 'existing'))),
  check=check_reno)

R('activation', 'unknown-data-not-evaluated', 'W8\'s FS_renovation data does not match the schema, but no extension '
  'is known: nothing of it is evaluated, and the document is valid.', ['1.2.1'], redit(BAD_R), registry=None)
R('activation', 'another-version-known', 'The document uses FS_renovation at 0.2.0, which is known (a later entry), '
  'but the implementation implements 0.1.0: not evaluated, so the data that breaks 0.1.0\'s schema is not reported.',
  ['1.2.1'], redit(lambda d: (BAD_R(d), d['extensionsUsed'].update({RENO: '0.2.0'}))), registry=[entry(RENO, '0.2.0')])
R('activation', 'version-without-patch', '"0.1" equals 0.1.0 (Core 12.3), so FS_renovation is evaluated: W8\'s data '
  'breaks the schema, FS-RENO-SCH-001.', ['1.2.1', '1.3.2'],
  redit(lambda d: (BAD_R(d), d['extensionsUsed'].update({RENO: '0.1'}))), [('FS-RENO-SCH-001', [])])
R('activation', 'declaration-object', 'A declaration object with a schema URI is its version string (Core 12.1.3): '
  'FS_renovation is evaluated.', ['1.2.1', '1.3.2'],
  redit(lambda d: (BAD_R(d), d['extensionsUsed'].update({RENO: {'version': '0.1.0', 'schema': entry(RENO)['schema']}}))),
  [('FS-RENO-SCH-001', [])])
R('activation', 'core-0.1-document', 'A document declaring "0.1" whose extension data is opaque (Core 1.2.4): '
  'FS_renovation is not evaluated, even though it is known.', ['1.2.1'],
  {'floorspec': '0.1', 'project': {'name': 'Old'}, 'extensionsUsed': {RENO: '0.1.0'}, 'extensions': {RENO: {'colour': 'red'}}})
R('activation', 'core-0.3-document', 'The remodel declaring Core "0.3", a draft FS_renovation 0.1.0 lists (1.1): '
  'FS_renovation is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
  ['1.2.1', '1.2.3', '1.2.4', '5.1.1'], redit(lambda d: d.update(floorspec='0.3')), check=check_reno)
R('activation', 'core-0.3-invariants', 'The same "0.3" house with the Bath\'s wall W10 to be demolished and a new door '
  'O3 in it: FS_renovation is evaluated for a Core 0.3 document, so the invariant is reported.',
  ['1.2.1', '1.2.3', '2.3.1'], redit(lambda d: (d.update(floorspec='0.3'), INVALID_R(d), RD(d, 'walls', 'W10').update(status='demolish'))),
  [('FS-RENO-INV-002', ['O3', 'W10'])])
R('activation', 'core-0.4-document', 'The remodel declaring Core "0.4", a draft FS_renovation 0.1.0 lists (1.1): '
  'FS_renovation is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
  ['1.2.1', '1.2.3', '1.2.4', '5.1.1'], redit(lambda d: d.update(floorspec='0.4')), check=check_reno)

R('order', 'core-error-first', 'A Core invariant breaks - the door O3 runs past the end of W10, FS-INV-302 - and so '
  'does FS_renovation\'s schema: Core\'s error is reported, and FS_renovation is not evaluated.', ['1.2.2'],
  redit(lambda d: (BAD_R(d), d['openings']['O3'].update(offset=3 * FT))), [('FS-INV-302', ['O3'])])
R('order', 'schema-before-invariants', 'The data breaks the schema and an invariant: only FS-RENO-SCH-001.',
  ['1.2.2', '1.3.2'], redit(lambda d: (BAD_R(d), RD(d, 'openings', 'O4').update(status='existing'))),
  [('FS-RENO-SCH-001', [])])
R('order', 'no-lints-when-invalid', 'Nothing is renovated, so FS-RENO-LINT-001 would apply, and `elements` names the '
  'wall W1: the document is invalid, so no lint is reported, FS_renovation\'s or Core\'s.', ['1.2.2', '1.2.3', '1.3.4'],
  redit(lambda d: (unmark_all(d), d['extensions'][RENO].update(elements={'W1': 'existing'}))),
  [('FS-RENO-INV-001', ['W1'])])

R('schema', 'top-level-data-not-an-object', 'FS_renovation\'s top-level data is an array: Core allows any JSON there, '
  'FS_renovation\'s schema does not.', ['1.3.1'], redit(lambda d: d['extensions'].update({RENO: []})),
  [('FS-RENO-SCH-001', [])])
R('schema', 'top-level-data-with-another-member', 'FS_renovation 0.1 gives its top-level data one member, `elements`.',
  ['1.3.1'], redit(lambda d: d['extensions'][RENO].update(phases=['Phase 1'])), [('FS-RENO-SCH-001', [])])
R('schema', 'an-element-status-not-a-status', 'X1\'s status in `elements` is "removed".', ['1.3.1'],
  redit(lambda d: RTOP(d).update(X1='removed')), [('FS-RENO-SCH-001', [])])
R('schema', 'an-element-id-not-an-id', '`elements` names "-X1", which no ID matches (Core 3.1).', ['1.3.1'],
  redit(lambda d: RTOP(d).update({'-X1': 'new'})), [('FS-RENO-SCH-001', [])])
R('schema', 'status-not-a-status', 'W8\'s status is "remove".', ['1.3.2'], redit(BAD_R), [('FS-RENO-SCH-001', [])])
R('schema', 'data-without-a-status', 'O5\'s FS_renovation data is an empty object: the status is always present.',
  ['1.3.2'], redit(lambda d: d['openings']['O5']['extensions'].update({RENO: {}})), [('FS-RENO-SCH-001', [])])
R('schema', 'data-with-another-member', 'R4\'s data has a phase as well as its status.', ['1.3.2'],
  redit(lambda d: RD(d, 'rooms', 'R4').update(phase=2)), [('FS-RENO-SCH-001', [])])
R('schema', 'data-not-an-object', 'S1\'s FS_renovation data is the string "new".', ['1.3.2'],
  redit(lambda d: d['slabs']['S1']['extensions'].update({RENO: 'new'})), [('FS-RENO-SCH-001', [])])
R('schema', 'data-on-a-junction', 'J7 carries a status: a junction has none.', ['1.3.3'],
  redit(lambda d: d['junctions']['J7'].update(extensions=RS('demolish'))), [('FS-RENO-SCH-001', [])])
R('schema', 'data-on-a-level', 'L1 carries a status.', ['1.3.3'],
  redit(lambda d: d['levels']['L1'].update(extensions=RS('existing'))), [('FS-RENO-SCH-001', [])])
R('schema', 'data-on-a-wall-type', 'The wall type INT carries a status: a type is a library entry, not part of the '
  'house.', ['1.3.3'], redit(lambda d: d['types']['INT'].update(extensions=RS('new'))), [('FS-RENO-SCH-001', [])])
R('schema', 'data-on-a-program-item', 'A program item carries a status.', ['1.3.3'],
  redit(lambda d: d.update(program={'items': {'P1': {'name': 'Laundry', 'function': 'laundry', 'extensions': RS('new')}}})),
  [('FS-RENO-SCH-001', [])])
R('schema', 'a-new-roof', 'The remodel as a Core 0.3 document with a new roof over the house (Core 16): a roof may '
  'carry a status. Valid, and the roof is counted with the new work.', ['1.3.2', '5.1.1'],
  redit(lambda d: d.update(floorspec='0.3', roofs={'RF1': {
      'level': 'L1', 'footprint': [[-FT, -FT], [21 * FT, -FT], [21 * FT, 13 * FT], [-FT, 13 * FT]],
      'pitch': {'rise': 6, 'run': 12}, 'extensions': RS('new')}})),
  check=lambda r: ensure(RDER(r)['quantities']['new']['roofs'] == 1 and 'RF1' in RDER(r)['status']['new'],
                         RDER(r)['quantities']))

R('invariants', 'elements-names-a-wall', '`elements` gives the wall W1 a status: a core element\'s status is on the '
  'element.', ['1.3.4'], redit(lambda d: RTOP(d).update(W1='demolish')), [('FS-RENO-INV-001', ['W1'])])
R('invariants', 'elements-names-a-room', '`elements` names the Laundry R4, which is new on its own data too.',
  ['1.3.4'], redit(lambda d: RTOP(d).update(R4='new')), [('FS-RENO-INV-001', ['R4'])])
R('invariants', 'elements-names-a-program-item', '`elements` names a program item.', ['1.3.4'],
  redit(lambda d: (d.update(program={'items': {'P1': {'name': 'Laundry', 'function': 'laundry'}}}), RTOP(d).update(P1='new'))),
  [('FS-RENO-INV-001', ['P1'])])
R('invariants', 'elements-names-nothing', '`elements` names X9, which is no element - one removed since: it means '
  'nothing, and is ignored (1.3). Valid, and derived as without it.', ['1.3.4', '5.1.1'],
  redit(lambda d: RTOP(d).update(X9='demolish')), check=check_reno)
R('invariants', 'existing-door-in-a-demolished-wall', 'W10 is to be demolished and the Bath\'s door O3 in it is to '
  'stay: the existing state has both, the proposed state has the door and not its wall.', ['2.3.1'],
  redit(lambda d: RD(d, 'walls', 'W10').update(status='demolish')), [('FS-RENO-INV-002', ['O3', 'W10'])])
R('invariants', 'existing-door-in-a-new-wall', 'The Laundry\'s door O5 is said to stand today, in the new wall W12.',
  ['2.3.1'], redit(lambda d: d['openings']['O5'].pop('extensions')), [('FS-RENO-INV-002', ['O5', 'W12'])])
R('invariants', 'new-door-in-a-demolished-wall', 'A new door O4 in W8, which is to come down.', ['2.3.1'],
  redit(lambda d: RD(d, 'openings', 'O4').update(status='new')), [('FS-RENO-INV-002', ['O4', 'W8'])])
R('invariants', 'demolished-door-in-a-new-wall', 'O5 is to be demolished, in the new wall W12: no state has both.',
  ['2.3.1'], redit(lambda d: RD(d, 'openings', 'O5').update(status='demolish')), [('FS-RENO-INV-002', ['O5', 'W12'])])
R('invariants', 'demolished-window-in-an-existing-wall', 'The Kitchen window O2 is to be filled in: a demolished '
  'element may be in an existing wall. Valid.', ['2.3.1'], redit(lambda d: RD(d, 'openings', 'O2').update(status='demolish')),
  check=lambda r: ensure('O2' in RDER(r)['status']['demolish'], RDER(r)['status']))
R('invariants', 'new-cabinet-on-a-demolished-wall', 'The island X2 is moved onto the face of W8, which is to come down.',
  ['2.3.1'], redit(lambda d: coll(d, FURN, 'casework')['X2'].update(host=wall_host('W8', 'left', 2 * FT))),
  [('FS-RENO-INV-002', ['W8', 'X2'])])
R('invariants', 'existing-appliance-in-a-new-room', 'The refrigerator X3, which stands today, is put on the floor of '
  'the new Laundry R4.', ['2.3.1'],
  redit(lambda d: coll(d, FURN, 'appliances')['X3'].update(host=floor_host('R4', 18 * FT, 2 * FT))),
  [('FS-RENO-INV-002', ['R4', 'X3'])])
R('invariants', 'every-reference-once', 'Three references across states at once: each reported once, naming both '
  'elements.', ['1.2.3', '2.3.1'],
  redit(lambda d: (RD(d, 'walls', 'W10').update(status='demolish'), d['openings']['O5'].pop('extensions'),
                   RD(d, 'openings', 'O4').update(status='new'))),
  [('FS-RENO-INV-002', ['O3', 'W10']), ('FS-RENO-INV-002', ['O4', 'W8']), ('FS-RENO-INV-002', ['O5', 'W12'])])
R('invariants', 'two-rooms-in-the-proposed-kitchen', 'The Utility room R3 is to stay while the wall between it and '
  'the Kitchen comes down: in the proposed state the Kitchen and the Utility room are one face with two anchors, which '
  'Core refuses (FS-INV-202).', ['2.4.2'], redit(lambda d: d['rooms']['R3'].pop('extensions')),
  [('FS-RENO-INV-004', ['R1', 'R3'])])
R('invariants', 'two-rooms-in-the-existing-utility', 'The Laundry R4 is said to stand today, with the new wall that '
  'makes it a room: in the existing state the Utility room and the Laundry are one face (FS-INV-202).', ['2.4.1'],
  redit(lambda d: d['rooms']['R4'].pop('extensions')), [('FS-RENO-INV-003', ['R3', 'R4'])])
R('invariants', 'both-states-broken', 'R3 stays and R4 stands today: each state breaks Core, and each is reported.',
  ['2.4.1', '2.4.2', '1.2.3'], redit(lambda d: (d['rooms']['R3'].pop('extensions'), d['rooms']['R4'].pop('extensions'))),
  [('FS-RENO-INV-003', ['R3', 'R4']), ('FS-RENO-INV-004', ['R1', 'R3'])])
R('invariants', 'not-evaluated-with-a-reference-across-states', 'R3 stays while its wall comes down, and the Laundry\'s '
  'door is said to stand today in the new wall: FS-RENO-INV-002 is reported, and the states\' views are not checked, '
  'so FS-RENO-INV-004 is not (4.2).', ['4.2.1', '2.3.1'],
  redit(lambda d: (d['rooms']['R3'].pop('extensions'), d['openings']['O5'].pop('extensions'))),
  [('FS-RENO-INV-002', ['O5', 'W12'])])
R('invariants', 'a-join-through-a-demolished-wall', 'J7\'s join runs W8 and W9 through it, and W8 is to come down: '
  'the proposed state\'s view drops the join (2.2), so it names no missing wall. Valid.', ['2.4.2'], remodel(),
  check=lambda r: ensure(RDER(r)['states']['proposed']['rooms']['R1'] != RDER(r)['states']['existing']['rooms']['R1'],
                         RDER(r)['states']))
R('invariants', 'a-wall-whose-room-goes-with-it', 'W10 comes down with the Bath\'s door and the Bath itself: the Bath '
  'joins the Kitchen in the proposed state, and is not a room of it. Valid.', ['2.3.1', '2.4.2'],
  redit(lambda d: (RD(d, 'walls', 'W10').update(status='demolish'), RD(d, 'openings', 'O3').update(status='demolish'),
                   RD(d, 'rooms', 'R2').update(status='demolish'))),
  check=lambda r: ensure(sorted(RDER(r)['states']['proposed']['rooms']) == ['R1', 'R4'], RDER(r)['states']))

R('derived', 'a-diagonal-wall', 'A new wall W14 across the Bath\'s north-east corner, 3\' each way, cutting off a closet '
  'whose face is unanchored: its length is 3\' times the square root of 2, rounded once (5.3).', ['5.1.1'],
  redit(lambda d: (d['junctions'].update(J11=J(17 * FT, 12 * FT), J12=J(20 * FT, 9 * FT)),
                   d['walls'].update(W3=RW('J3', 'J11', 'EXT'), W15=RW('J11', 'J4', 'EXT'), W4=RW('J4', 'J12', 'EXT'),
                                     W16=RW('J12', 'J8', 'EXT'), W14=RW('J11', 'J12', 'INT', 'new')))),
  [('FS-LINT-003', [])],
  check=lambda r: ensure(RDER(r)['quantities']['new']['wallLength'] == 6 * FT + land._round_sqrt(2 * (3 * FT) ** 2)
                         and RDER(r)['quantities']['new']['walls'] == 2, RDER(r)['quantities']['new']))
R('derived', 'the-deck-demolished', 'The deck stands today and is to come down: its area moves to `demolish`.',
  ['5.1.1'], redit(lambda d: RD(d, 'slabs', 'S1').update(status='demolish')),
  check=lambda r: ensure(RDER(r)['quantities']['demolish']['slabArea'] == str(8 * 7 * FT * FT)
                         and RDER(r)['quantities']['new']['slabArea'] == '0', RDER(r)['quantities']))
R('derived', 'a-second-level', 'A second level L2 with no walls: the states have the rooms of every level, and L2 has '
  'none. Derived as without it.', ['5.1.1'],
  redit(lambda d: d['levels'].update(L2={'building': 'B1', 'elevation': H, 'height': H})), check=check_reno)


def kitchen_options(d):
    """Core 0.3 design options: the island's option set OS1, with option A (OP1, the primary) having no
    island and option B (OP2) the new island X2."""
    d['floorspec'] = '0.3'
    d['optionSets'] = {'OS1': {'primary': 'OP1', 'name': 'Island'}}
    d['options'] = {'OP1': {'set': 'OS1', 'name': 'No island'}, 'OP2': {'set': 'OS1', 'name': 'Island'}}
    coll(d, FURN, 'casework')['X2']['option'] = 'OP2'


R('options', 'island-option-a', 'An island as a Core 0.3 design option (Core 19): option A, the primary, has none, and '
  'B has the new island X2, whose status is in `elements`. In the primary design X2 is not in the view, and its member '
  'of `elements` names nothing there, and is ignored: valid, and X2 is in no status.',
  ['1.2.1', '1.2.4', '1.3.4', '5.1.1', 'FS-CORE-19.3.1'], redit(kitchen_options),
  check=lambda r: ensure(RDER(r)['status']['new'] == ['O5', 'O6', 'R4', 'S1', 'W12'], RDER(r)['status']))
R('options', 'island-option-b', 'The same document, deriving the design that chooses B (design.json): the island is new.',
  ['1.2.4', '5.1.1', 'FS-CORE-19.3.1'], redit(kitchen_options), design={'OS1': 'OP2'},
  check=lambda r: ensure(RDER(r)['status']['new'] == ['O5', 'O6', 'R4', 'S1', 'W12', 'X2'], RDER(r)['status']))
R('options', 'invariant-in-option-b', 'Option B\'s island stands on W8, which is to come down: FS_renovation is '
  'evaluated in each checked design, so FS-RENO-INV-002 is reported for option B\'s design, with `design`.',
  ['1.2.1', '1.2.3', '2.3.1'],
  redit(lambda d: (kitchen_options(d), coll(d, FURN, 'casework')['X2'].update(host=wall_host('W8', 'left', 2 * FT)))),
  [('FS-RENO-INV-002', ['W8', 'X2'], 'OP2')])

RO = lambda *a, **k: O(RENO, *a, **k)    # noqa: E731
RO('mark-a-window-demolished', 'setProperty of O2 /extensions/FS_renovation/status, creating O2\'s extensions and its '
   'FS_renovation data on the way (Ops 2.3): the Kitchen window is to be filled in. It commits.',
   ['1.2.1', '1.3.2', 'FS-OPS-2.3.1'], remodel(),
   {'batch': [{'op': 'setProperty', 'id': 'O2', 'path': '/extensions/FS_renovation/status', 'value': 'demolish'}]},
   check=lambda r, B: ensure('O2' in reno_derived(B)['status']['demolish'], reno_derived(B)['status']))
RO('mark-a-wall-and-its-door', 'W10 and the Bath\'s door O3 are marked "demolish" in one batch, and the Bath R2 with '
   'them: it commits, and the Bath is no room of the proposed state.', ['1.2.1', '2.3.1', '2.4.2', '6.1.1', 'FS-OPS-2.3.1'],
   remodel(),
   {'batch': [{'op': 'setProperty', 'id': i, 'path': '/extensions/FS_renovation/status', 'value': 'demolish'}
              for i in ('W10', 'O3', 'R2')]},
   check=lambda r, B: ensure(sorted(reno_derived(B)['states']['proposed']['rooms']) == ['R1', 'R4'], reno_derived(B)['states']))
RO('a-wall-without-its-door-is-rejected', 'W10 alone is marked "demolish", its door O3 left standing: the result '
   'breaks 2.3.1, and an applier that implements FS_renovation and knows it rejects the batch (Ops 1.2.3).',
   ['2.3.1', '1.2.1', 'FS-OPS-1.2.3'], remodel(),
   {'batch': [{'op': 'setProperty', 'id': 'W10', 'path': '/extensions/FS_renovation/status', 'value': 'demolish'}]},
   'rejected', [('FS-RENO-INV-002', ['O3', 'W10'])])
RO('keeping-a-room-whose-wall-goes-is-rejected', 'unsetProperty of R3 /extensions/FS_renovation: the Utility room '
   'would stay while its wall to the Kitchen comes down, two rooms in one face of the proposed state; the batch is '
   'rejected with FS-RENO-INV-004.', ['2.4.2', '1.2.1', 'FS-OPS-1.2.3'], remodel(),
   {'batch': [{'op': 'unsetProperty', 'id': 'R3', 'path': '/extensions/FS_renovation'}]},
   'rejected', [('FS-RENO-INV-004', ['R1', 'R3'])])
RO('mark-an-extension-element', 'setProperty of $document /extensions/FS_renovation/elements/X3: the refrigerator is to '
   'go. It commits.', ['1.2.1', '1.3.1', 'FS-OPS-2.3.1'], remodel(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_renovation/elements/X3', 'value': 'demolish'}]},
   check=lambda r, B: ensure(reno_derived(B)['status']['demolish'] == ['O4', 'R3', 'W8', 'X1', 'X3'], reno_derived(B)['status']))
RO('remove-an-element-and-its-status', 'removeElement X1 and unsetProperty of its member of `elements`, in one batch, '
   'as 6.1.2 says: it commits, and X1 is in no status.', ['1.3.4', '6.1.2', 'FS-OPS-2.3.1'], remodel(),
   {'batch': [{'op': 'removeElement', 'id': 'X1'},
              {'op': 'unsetProperty', 'id': '$document', 'path': '/extensions/FS_renovation/elements/X1'}]},
   check=lambda r, B: ensure('X1' not in ext(B, RENO)['elements'] and 'X1' not in reno_derived(B)['status']['demolish'],
                             reno_derived(B)['status']))
RO('remove-an-element-and-not-its-status', 'removeElement X1 alone: its member of `elements` names nothing, and is '
   'ignored (1.3). It commits.', ['1.3.4', 'FS-OPS-2.3.1'], remodel(), {'batch': [{'op': 'removeElement', 'id': 'X1'}]},
   check=lambda r, B: ensure(ext(B, RENO)['elements'] == {'X1': 'demolish', 'X2': 'new'}
                             and reno_derived(B)['status']['demolish'] == ['O4', 'R3', 'W8'], reno_derived(B)['status']))
RO('a-status-on-a-junction-is-rejected', 'setProperty of J7 /extensions/FS_renovation: a junction has no status, and '
   'the batch is rejected with FS-RENO-SCH-001.', ['1.3.3', '1.2.1', 'FS-OPS-1.2.3'], remodel(),
   {'batch': [{'op': 'setProperty', 'id': 'J7', 'path': '/extensions/FS_renovation', 'value': {'status': 'demolish'}}]},
   'rejected', [('FS-RENO-SCH-001', [])])


# ============================================================================= FS_annotation

ANNO = 'FS_annotation'
CODE[ANNO] = 'ANNO'
MM50 = 50 * MM                                     # half the demo walls' 100 mm


def jA(j):
    return {'junction': j}


def wA(w, face):
    return {'wall': w, 'face': face}


def oA(o):
    return {'opening': o}


def pA(x, y):
    return {'point': [x, y]}


def dim(level, direction, through, anchors, name=None):
    out = {'level': level, 'direction': direction, 'through': through, 'anchors': anchors}
    if name is not None:
        out['name'] = name
    return out


WINDOW_T = {'kind': 'windowType', 'width': 4 * FT, 'height': 48 * IN, 'sill': 36 * IN}
ANNOTATION = {
    'dimensions': {
        'DM1': dim('L1', [1, 0], [0, -1200 * MM], [wA('W1', 'left'), jA('J6'), wA('W5', 'left')], 'Overall, south'),
        'DM2': dim('L1', [1, 0], [0, 12 * FT + 1200 * MM], [wA('W1', 'left'), oA('O1'), jA('J3')], 'Kitchen window'),
        'DM3': dim('L1', [1, 0], [0, 3 * FT], [wA('W1', 'right'), wA('W8', 'left')], 'Kitchen, clear'),
        'DM4': dim('L1', [0, 1], [16 * FT, 0], [wA('W6', 'right'), wA('W10', 'right'), wA('W10', 'left'), wA('W3', 'right')],
                   'Utility and living, clear'),
    },
    'notes': {
        'NT1': {'level': 'L1', 'text': 'Verify the rough opening on site\nbefore ordering the window.',
                'at': [2 * FT, 15 * FT], 'leader': [6 * FT, 12 * FT], 'about': 'O1'},
        'NT2': {'level': 'L1', 'text': 'Keep the panel\'s working space clear.', 'at': [13 * FT, FT],
                'leader': [20 * FT - 100 * MM, 3 * FT], 'about': 'X1'},
    },
}


def annotation_house():
    """The Phase 13 lit house with its four saved views (views_house()), a 4' kitchen window O1 in the
    north wall W2 - 4' from J2, so its centre is 6' east of the west wall's location line - and the
    owner's annotation of FS_annotation:

    - DM1 "Overall, south": below the house, from the west wall's outside face, through the corner
      J6 under the interior wall, to the east wall's outside face - 12' 2" (12' and 50 mm) and 8' and
      50 mm, 20' and 100 mm in all;
    - DM2 "Kitchen window": above the house, from the west wall's outside face to the window's centre
      and on to the corner J3 - 6' and 50 mm, then 6';
    - DM3 "Kitchen, clear": across the Kitchen, from the west wall's inside face to the interior
      wall's - 12' less 100 mm;
    - DM4 "Utility and living, clear": north-south through the Utility room and the Living room, from
      the south wall's inside face to the north wall's, with the wall between them: 6' less 100 mm,
      100 mm, 6' less 100 mm;
    - NT1, a note of two lines north of the house, its leader at the window's centre, about O1;
    - NT2, a note in the Utility room, its leader at the panel's face, about the panel X1.

    FS_annotation requires no other extension; the house uses FS_electrical, FS_furniture,
    FS_lighting and FS_views as well, and FS_annotation reads the scenes and the views as data."""
    d = views_house()
    d['types']['WN'] = dict(WINDOW_T)
    d['openings'] = {'O1': {'wall': 'W2', 'offset': 4 * FT, 'fill': 'WN', 'name': 'Kitchen window'}}
    d['extensionsUsed'][ANNO] = '0.1.0'
    d['extensions'][ANNO] = copy.deepcopy(ANNOTATION)
    return d


def aedit(fn):
    """The Phase 13 house with annotation, changed by fn(d) in place."""
    d = annotation_house()
    fn(d)
    return d


DMS = lambda d: ext(d, ANNO)['dimensions']                                          # noqa: E731
NTS = lambda d: ext(d, ANNO)['notes']                                               # noqa: E731
ADER = derived_of(ANNO)
AN = lambda *a, **k: V(ANNO, *a, **k)    # noqa: E731
ANNOTATED = {'dimensions': {'DM1': {'level': 'L1', 'lengths': [12 * FT + MM50, 8 * FT + MM50], 'total': 20 * FT + 2 * MM50},
                            'DM2': {'level': 'L1', 'lengths': [6 * FT + MM50, 6 * FT], 'total': 12 * FT + MM50},
                            'DM3': {'level': 'L1', 'lengths': [12 * FT - 2 * MM50], 'total': 12 * FT - 2 * MM50},
                            'DM4': {'level': 'L1', 'lengths': [6 * FT - 2 * MM50, 2 * MM50, 6 * FT - 2 * MM50],
                                    'total': 12 * FT - 2 * MM50}},
             'notes': {'NT1': {'level': 'L1', 'about': 'O1'}, 'NT2': {'level': 'L1', 'about': 'X1'}}}
ANNO_KNOWN = VIEW_KNOWN + (ANNO,)
UNRESOLVED = {'level': 'L1', 'lengths': None, 'total': None}


def check_anno(r):
    # every length by hand: the walls are 100 mm thick and centred on their location lines, so a face is
    # 50 mm from the line; the window's centre is 4' + 4'/2 from J2
    ensure(ADER(r) == ANNOTATED and list(ADER(r)['dimensions']) == ['DM1', 'DM2', 'DM3', 'DM4'], ADER(r))


def level2(d):
    """A second level L2 above L1, with nothing on it."""
    d['levels']['L2'] = {'building': 'B1', 'elevation': H, 'height': H}


def without_scenes_and_views(d):
    """Neither FS_lighting nor FS_views: their declarations and their data."""
    for x in (LGHT, VIEW):
        d['extensionsUsed'].pop(x)
        d['extensions'].pop(x)


def annotation_alone(d):
    """FS_annotation the only extension the house uses - no lights, no lamp, no scenes, no views - and
    the panel's note about nothing in particular."""
    for x in (ELEC, FURN, LGHT, VIEW):
        d['extensionsUsed'].pop(x)
        d['extensions'].pop(x)
    d.pop('assets')
    NTS(d)['NT2'].pop('about')


def chamfer(d):
    """The Kitchen's north-west corner cut off: J2 gone, the west wall W1 ending at J9 (0, 9'), a wall
    W11 from J9 to J10 (2', 12') - 2' east for every 3' north, sqrt(13) feet long - and the north wall
    W2 starting at J10; and a 2' window O2 in W11, 6" from J9."""
    d['junctions'].pop('J2')
    d['junctions']['J9'] = J(0, 9 * FT)
    d['junctions']['J10'] = J(2 * FT, 12 * FT)
    d['walls']['W1']['end'] = 'J9'
    d['walls']['W2']['start'] = 'J10'
    d['walls']['W11'] = W('J9', 'J10')
    d['openings']['O2'] = {'wall': 'W11', 'offset': 6 * IN, 'width': 2 * FT, 'fill': 'WN', 'name': 'Corner window'}


def arc_w3(d):
    """The house as a Core 0.4 document whose north wall W3, over the Living room, bulges 2' out
    northwards as an arc (Core 0.4, 21.1)."""
    d['floorspec'] = '0.4'
    d['walls']['W3']['arc'] = {'sagitta': 2 * FT}


def _dec_sqrt(n):
    from decimal import Decimal
    return Decimal(n).sqrt()


def chamfer_check(r):
    """DM5's lengths by an independent route: each position in 60-digit decimals, rounded at the end."""
    from decimal import Decimal, getcontext, ROUND_HALF_EVEN
    getcontext().prec = 60
    d, T = (1, -1), (FT, 10 * FT + 6 * IN)
    nd = _dec_sqrt(2)
    S, e = (0, 9 * FT), (2 * FT, 3 * FT)
    le = _dec_sqrt(e[0] ** 2 + e[1] ** 2)
    nu = (-e[1], e[0])
    nud = nu[0] * d[0] + nu[1] * d[1]

    def face(lam):
        t = (Decimal(lam) * le - (nu[0] * (T[0] - S[0]) + nu[1] * (T[1] - S[1]))) / nud
        return t * nd

    def at(P):
        return ((P[0] - T[0]) * d[0] + (P[1] - T[1]) * d[1]) / nd

    c = Decimal(6 * IN + FT) / le                          # the window's centre, 6" + 1' along W11
    centre = (S[0] + e[0] * c, S[1] + e[1] * c)
    p = [face(MM50), at(centre), face(-MM50), at((12 * FT, 12 * FT))]
    q = lambda x: int(abs(x).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))      # noqa: E731
    want = {'level': 'L1', 'lengths': [q(p[i + 1] - p[i]) for i in range(3)], 'total': q(p[3] - p[0])}
    ensure(ADER(r)['dimensions']['DM5'] == want, (ADER(r)['dimensions']['DM5'], want))


BAD_A = lambda d: DMS(d)['DM1'].update(direction=[1, 0, 0])                         # noqa: E731  the schema tier
INV_A = lambda d: DMS(d)['DM3'].update(direction=[0, 0])                           # noqa: E731  FS-ANNO-INV-003
INV_A_DIAG = [('FS-ANNO-INV-003', ['DM3'])]
LINT_A = lambda d: DMS(d)['DM1']['anchors'].__setitem__(1, jA('J9'))              # noqa: E731  FS-ANNO-LINT-001

AN('examples', 'p13-house-with-annotation', 'The Phase 13 lit house with a kitchen window and its owner\'s annotation, '
   'read by an implementation of FS_annotation that knows it: an overall string along the south side, from the west '
   'wall\'s outside face through the corner J6 to the east wall\'s outside face; a string locating the kitchen window '
   'by its centre; the Kitchen\'s clear width between two wall faces; a north-south string of clear dimensions through '
   'the Utility and Living rooms, the wall between them included; and two notes with leaders, about the window and '
   'about the panel. FS_lighting and FS_views are unknown to it, their scenes and views read as data. It is valid, '
   'reports nothing, and derives every length exactly - 20\' and 100 mm south, 12\' less 100 mm across the Kitchen - '
   'and each note\'s level and what it is about.',
   ['1.2.1', '1.2.3', '1.2.4', '1.3.1', '1.3.2', '1.3.3', '2.1.1', '2.2.1', '2.2.2', '2.3.1', '3.1.1', '6.1.1'],
   annotation_house(), check=check_anno)
AN('examples', 'core-only-reader', 'The same house read with no known extensions: FS_annotation is not evaluated, so '
   'nothing of it is derived (`derived.extensions` is empty) - only what Core derives from every extension element\'s '
   'fallback and host (Core 1.6.9), and the window; FS_annotation has no elements of its own.',
   ['1.2.1', '1.2.4', 'FS-CORE-1.6.9', 'FS-CORE-12.6.2'], annotation_house(), registry=None,
   check=lambda r: ensure(r['derived']['extensions'] == {} and sorted(r['derived']['fallbacks'])
                          == ['X1', 'X10', 'X11', 'X12', 'X13', 'X2', 'X20', 'X3', 'X4', 'X5', 'X6', 'X7']
                          and list(r['derived']['openings']) == ['O1'], r['derived']['extensions']))
AN('examples', 'all-official-known', 'The house read with every official entry known, by an implementation of '
   'FS_annotation alone: FS_electrical, FS_furniture, FS_lighting and FS_views are checked only as Core 12 checks a '
   'known extension, and only FS_annotation is evaluated and derived.',
   ['1.2.1', '1.2.4'], annotation_house(), registry=[entry(x) for x in ANNO_KNOWN],
   check=lambda r: ensure(list(r['derived']['extensions']) == [ANNO] and ADER(r) == ANNOTATED, list(r['derived']['extensions'])))
AN('examples', 'no-annotation', 'FS_annotation used with empty top-level data: valid, and no dimension string or note '
   'derived.', ['1.3.1', '6.1.1'], aedit(lambda d: d['extensions'].update({ANNO: {}})),
   check=lambda r: ensure(ADER(r) == {'dimensions': {}, 'notes': {}}, ADER(r)))
AN('examples', 'notes-only', 'FS_annotation\'s data with notes and no `dimensions`: valid, and no dimension string '
   'derived.', ['1.3.1', '6.1.1'], aedit(lambda d: ext(d, ANNO).pop('dimensions')),
   check=lambda r: ensure(ADER(r) == {'dimensions': {}, 'notes': ANNOTATED['notes']}, ADER(r)))
AN('examples', 'without-scenes-and-views', 'The house without FS_lighting and FS_views - neither their declarations '
   'nor their data: FS_annotation requires no other extension, so the annotation is valid as it is, and measures the '
   'same.', ['1.2.1', '1.3.1', '1.3.2', '6.1.1'], aedit(without_scenes_and_views),
   check=lambda r: ensure(ADER(r) == ANNOTATED and list(r['derived']['extensions']) == [ANNO], ADER(r)))
AN('examples', 'annotation-alone', 'The house with FS_annotation the only extension it uses - no lights, no lamp, no '
   'scenes, no views - and the panel\'s note about nothing in particular: valid, and the four strings measured as '
   'before.', ['1.2.1', '1.2.4', '1.3.1', '3.1.1', '6.1.1'], aedit(annotation_alone),
   check=lambda r: ensure(ADER(r)['dimensions'] == ANNOTATED['dimensions'] and r['derived']['fallbacks'] == {}
                          and ADER(r)['notes']['NT2'] == {'level': 'L1', 'about': None}, ADER(r)))

AN('activation', 'unknown-data-not-evaluated', 'The overall string\'s direction is three numbers, which FS_annotation\'s '
   'schema does not allow, but no extension is known: nothing of it is evaluated, and the document is valid.', ['1.2.1'],
   aedit(BAD_A), registry=None)
AN('activation', 'another-version-known', 'The document uses FS_annotation at 0.2.0, which is known (a later entry), but '
   'the implementation implements 0.1.0: not evaluated, so the data that breaks 0.1.0\'s schema is not reported.',
   ['1.2.1'], aedit(lambda d: (BAD_A(d), d['extensionsUsed'].update({ANNO: '0.2.0'}))), registry=[entry(ANNO, '0.2.0')])
AN('activation', 'version-without-patch', '"0.1" equals 0.1.0 (Core 12.3), so FS_annotation is evaluated: its data '
   'breaks the schema, FS-ANNO-SCH-001.', ['1.2.1', '1.3.1'],
   aedit(lambda d: (BAD_A(d), d['extensionsUsed'].update({ANNO: '0.1'}))), [('FS-ANNO-SCH-001', [])])
AN('activation', 'declaration-object', 'A declaration object with a schema URI is its version string (Core 12.1.3): '
   'FS_annotation is evaluated.', ['1.2.1', '1.3.1'],
   aedit(lambda d: (BAD_A(d), d['extensionsUsed'].update({ANNO: {'version': '0.1.0', 'schema': entry(ANNO)['schema']}}))),
   [('FS-ANNO-SCH-001', [])])
AN('activation', 'core-0.1-document', 'A document declaring "0.1" has no extension elements and its extension data is '
   'opaque (Core 1.2.4): FS_annotation is not evaluated, even though it is known.', ['1.2.1'],
   {'floorspec': '0.1', 'project': {'name': 'Old'}, 'extensionsUsed': {ANNO: '0.1.0'},
    'extensions': {ANNO: {'colour': 'red'}}})
AN('activation', 'core-0.3-document', 'The house declaring Core "0.3", a draft FS_annotation 0.1.0 lists (1.1): '
   'FS_annotation is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
   ['1.2.1', '1.2.3', '1.2.4', '6.1.1'], aedit(lambda d: d.update(floorspec='0.3')), check=check_anno)
AN('activation', 'core-0.3-invariants', 'The same "0.3" house with the Kitchen\'s clear width measured along no '
   'direction: FS_annotation is evaluated for a Core 0.3 document, so the invariant is reported.', ['1.2.1', '1.2.3', '2.1.1'],
   aedit(lambda d: (d.update(floorspec='0.3'), INV_A(d))), INV_A_DIAG)
AN('activation', 'core-0.4-document', 'The house declaring Core "0.4", a draft FS_annotation 0.1.0 lists (1.1): '
   'FS_annotation is evaluated, reports nothing, and derives exactly what it derives for the house declaring "0.2".',
   ['1.2.1', '1.2.3', '1.2.4', '6.1.1'], aedit(lambda d: d.update(floorspec='0.4')), check=check_anno)
AN('activation', 'scenes-and-views-known-too', 'The house read with FS_lighting\'s and FS_views\'s entries known as '
   'well as FS_annotation\'s, by an implementation of FS_annotation alone: FS_lighting and FS_views are checked only as '
   'Core 12 checks a known extension, and FS_annotation is evaluated and derived exactly as with its own entry alone.',
   ['1.2.1', '1.2.4', '6.1.1'], annotation_house(), registry=[entry(ELEC), entry(LGHT), entry(VIEW), entry(ANNO)],
   check=lambda r: ensure(list(r['derived']['extensions']) == [ANNO] and ADER(r) == ANNOTATED, r['derived']['extensions']))

AN('order', 'core-error-first', 'A Core invariant breaks - the porch light\'s switch 13\' along the 12\' wall W2, '
   'FS-INV-501 - and so does FS_annotation\'s schema: Core\'s error is reported, and FS_annotation is not evaluated.',
   ['1.2.2'], aedit(lambda d: (BAD_A(d), GK(d, 'switches')['X13']['host'].update(wall='W2', offset=13 * FT))),
   [('FS-INV-501', ['X13'])])
AN('order', 'schema-before-invariants', 'The data breaks the schema and an invariant: only FS-ANNO-SCH-001.',
   ['1.2.2', '1.3.1'], aedit(lambda d: (BAD_A(d), INV_A(d))), [('FS-ANNO-SCH-001', [])])
AN('order', 'no-lints-when-invalid', 'An invariant breaks and a lint would apply too - the overall string measures to '
   'a junction J9 the house does not have: the document is invalid, so no lint is reported, FS_annotation\'s or Core\'s.',
   ['1.2.2', '1.2.3'], aedit(lambda d: (INV_A(d), LINT_A(d))), INV_A_DIAG)
AN('order', 'views-not-evaluated', 'FS_views\'s data breaks FS_views\'s own rules - the island view looks at its own eye, '
   'and the cutaway is named "Hero exterior" - but this implementation does not implement FS_views: it reports nothing '
   'of FS_views, and reads its views as data. Valid.', ['1.2.1', '1.3.2'],
   aedit(lambda d: (VWS(d)['SV2'].update(target=VWS(d)['SV2']['eye']), VWS(d)['SV4'].update(name='Hero exterior'))),
   check=check_anno)

AS = lambda slug, text, fn: AN('schema', slug, text, ['1.3.1'], aedit(fn), [('FS-ANNO-SCH-001', [])])   # noqa: E731
AS('data-not-an-object', 'FS_annotation\'s top-level data is an array: Core allows any JSON there, FS_annotation\'s '
   'schema does not.', lambda d: d['extensions'].update({ANNO: []}))
AS('unknown-member', 'A top-level member FS_annotation does not define, `tags`: tags are derived, never stored.',
   lambda d: ext(d, ANNO).update(tags={}))
AS('empty-collections', 'An empty `collections` member: FS_annotation adds no kind of element, so its data has no '
   '`collections`, even an empty one. Core finds no collection in it; FS_annotation\'s schema rejects it.',
   lambda d: ext(d, ANNO).update(collections={}))
AN('schema', 'a-collection', 'A collection `labels` in FS_annotation\'s data: its registry entry names no kind, so Core '
   '12.4.1 reports it (FS-INV-604), and FS_annotation is not evaluated.', ['1.2.2', 'FS-CORE-12.4.1'],
   aedit(lambda d: ext(d, ANNO).update(collections={'labels': {}})), [('FS-INV-604', [])])
AS('dimensions-not-an-object', 'FS_annotation\'s `dimensions` is a list of strings, not an object of them.',
   lambda d: ext(d, ANNO).update(dimensions=list(DMS(d).values())))
AS('notes-not-an-object', 'FS_annotation\'s `notes` is a string.', lambda d: ext(d, ANNO).update(notes='see the plan'))
AS('dimension-id-not-an-id', 'A dimension string keyed by "Overall south", which is not an ID (Core 3.1.1).',
   lambda d: DMS(d).update({'Overall south': DMS(d).pop('DM1')}))
AS('note-id-not-an-id', 'A note keyed by "#1", which is not an ID.', lambda d: NTS(d).update({'#1': NTS(d).pop('NT1')}))
AS('dimension-without-a-level', 'A dimension string is always drawn on a level.', lambda d: DMS(d)['DM1'].pop('level'))
AS('dimension-without-a-direction', 'A dimension string always has a direction.', lambda d: DMS(d)['DM1'].pop('direction'))
AS('dimension-without-through', 'A dimension string always has a point its line passes through.',
   lambda d: DMS(d)['DM1'].pop('through'))
AS('dimension-without-anchors', 'A dimension string always has anchors.', lambda d: DMS(d)['DM1'].pop('anchors'))
AS('direction-of-three-lengths', 'A direction is two lengths, [dx, dy]: [1, 0, 0] is not one.', BAD_A)
AS('direction-of-one-length', 'A direction of one length.', lambda d: DMS(d)['DM1'].update(direction=[1]))
AN('schema', 'direction-with-a-fraction', 'A direction written with a fraction is not a vector of lengths, even when '
   'its numbers are whole (1.4).', ['1.3.1'], None, [('FS-ANNO-SCH-001', [])],
   raw=(fmt(annotation_house()) + '\n').replace('"direction": [1, 0]', '"direction": [1.0, 0]', 1).encode('utf-8'))
AS('direction-an-angle', 'A direction written as an angle, 90: it is a vector of two lengths.',
   lambda d: DMS(d)['DM4'].update(direction=90))
AS('through-of-three-lengths', 'A point of the plan is two lengths: [x, y, z] is not one.',
   lambda d: DMS(d)['DM1'].update(through=[0, -1200 * MM, 0]))
AS('through-beyond-a-length', 'A point 2^53 base units east, one more than any length (Core 2.1).',
   lambda d: DMS(d)['DM1'].update(through=[2 ** 53, 0]))
AS('through-in-millimetres', 'A point written in millimetres as strings: a length is an integer of base units.',
   lambda d: DMS(d)['DM1'].update(through=['0 mm', '-1200 mm']))
AS('one-anchor', 'A dimension string of one anchor measures nothing: it has 2 to 64.',
   lambda d: DMS(d)['DM3'].update(anchors=DMS(d)['DM3']['anchors'][:1]))
AS('sixty-five-anchors', 'A dimension string of 65 anchors: it has 2 to 64.',
   lambda d: DMS(d)['DM1'].update(anchors=[pA(k * FT, 0) for k in range(65)]))
AS('anchors-not-an-array', 'A dimension string\'s anchors are an array, not an object of them.',
   lambda d: DMS(d)['DM3'].update(anchors={'from': wA('W1', 'right'), 'to': wA('W8', 'left')}))
AS('anchor-of-two-forms', 'An anchor naming a junction and an opening at once: it is exactly one of the four forms.',
   lambda d: DMS(d)['DM2']['anchors'].__setitem__(1, {'opening': 'O1', 'junction': 'J3'}))
AS('anchor-of-no-form', 'An empty anchor, {}: it is exactly one of the four forms.',
   lambda d: DMS(d)['DM2']['anchors'].__setitem__(1, {}))
AS('anchor-wall-without-a-face', 'A wall anchor without its face: which of the wall\'s lines it measures to is always '
   'said.', lambda d: DMS(d)['DM3']['anchors'].__setitem__(0, {'wall': 'W1'}))
AS('anchor-face-not-listed', 'A wall anchor whose face is "centre": the faces are "left", "right" and "location".',
   lambda d: DMS(d)['DM3']['anchors'].__setitem__(0, wA('W1', 'centre')))
AS('anchor-face-without-a-wall', 'A face without its wall.', lambda d: DMS(d)['DM3']['anchors'].__setitem__(0, {'face': 'right'}))
AS('anchor-wall-and-a-junction', 'A wall anchor that also names a junction.',
   lambda d: DMS(d)['DM3']['anchors'].__setitem__(0, {**wA('W1', 'right'), 'junction': 'J1'}))
AS('anchor-junction-not-an-id', 'A junction anchor naming "J 1", which is not an ID.',
   lambda d: DMS(d)['DM1']['anchors'].__setitem__(1, jA('J 1')))
AS('anchor-point-of-one-length', 'A point anchor of one length.', lambda d: DMS(d)['DM1']['anchors'].__setitem__(1, pA(0, 0) | {'point': [0]}))
AS('anchor-with-an-offset', 'An anchor with a member no anchor defines, `offset`: an anchor measures to its feature, '
   'never to a point beside it.', lambda d: DMS(d)['DM2']['anchors'].__setitem__(1, {'opening': 'O1', 'offset': 0}))
AS('anchor-a-string', 'An anchor written as the ID it names, "J6": it is an object of one of the four forms.',
   lambda d: DMS(d)['DM1']['anchors'].__setitem__(1, 'J6'))
AS('name-empty', 'A dimension string\'s name is 1 to 200 characters: never empty.', lambda d: DMS(d)['DM1'].update(name=''))
AS('name-too-long', 'A dimension string\'s name is 1 to 200 characters.', lambda d: DMS(d)['DM1'].update(name='N' * 201))
AS('dimension-with-an-unknown-member', 'A dimension string has a member a string does not define: `lengths`, which '
   'are derived, never stored.', lambda d: DMS(d)['DM1'].update(lengths=[12 * FT, 8 * FT]))
AS('dimension-extras-not-an-object', 'A dimension string\'s `extras` is an object (Core 1.7).',
   lambda d: DMS(d)['DM1'].update(extras='site'))
AS('note-without-a-level', 'A note is always drawn on a level.', lambda d: NTS(d)['NT1'].pop('level'))
AS('note-without-text', 'A note always says something.', lambda d: NTS(d)['NT1'].pop('text'))
AS('note-without-at', 'A note\'s text is always drawn somewhere.', lambda d: NTS(d)['NT1'].pop('at'))
AS('text-empty', 'A note\'s text is 1 to 500 characters: never empty.', lambda d: NTS(d)['NT1'].update(text=''))
AS('text-too-long', 'A note\'s text is 1 to 500 characters.', lambda d: NTS(d)['NT1'].update(text='x' * 501))
AS('text-not-a-string', 'A note\'s text is a string, not a list of its lines.',
   lambda d: NTS(d)['NT1'].update(text=['Verify the rough opening on site', 'before ordering the window.']))
AS('at-of-three-lengths', 'A note\'s `at` is a point of the plan, two lengths.', lambda d: NTS(d)['NT1'].update(at=[0, 0, 0]))
AS('leader-of-one-length', 'A note\'s `leader` is a point of the plan, two lengths.', lambda d: NTS(d)['NT1'].update(leader=[0]))
AS('about-not-an-id', 'A note about "the kitchen window", which is not an ID.',
   lambda d: NTS(d)['NT1'].update(about='the kitchen window'))
AS('note-with-a-rotation', 'A note with a member a note does not define, `rotation`: FS_annotation 0.1 draws a note\'s '
   'text along +x.', lambda d: NTS(d)['NT1'].update(rotation=90))
AS('note-extras-not-an-object', 'A note\'s `extras` is an object (Core 1.7).', lambda d: NTS(d)['NT1'].update(extras=1))
AN('schema', 'every-form', 'Every form the schema allows at its bounds - a string of 64 anchors, the last a point; a '
   'string of two anchors, a point and a location line; a name of 200 characters; a note of 500 characters with line '
   'feeds and no leader, and a note without `about`; `extras` on a string and a note. Valid.', ['1.3.1', '6.1.1'],
   aedit(lambda d: (DMS(d).update(DM5=dim('L1', [1, 0], [0, 20 * FT], [pA(k * FT // 4, 0) for k in range(64)], 'N' * 200),
                                  DM6=dim('L1', [1, 0], [0, -2 * FT], [pA(-FT, 0), wA('W1', 'location')])),
                    DMS(d)['DM1'].update(extras={'style': 'architectural'}),
                    NTS(d).update(NT3={'level': 'L1', 'text': ('Line\n' * 100)[:500], 'at': [0, 0], 'extras': {'pen': 2}}),
                    NTS(d)['NT2'].pop('about'))),
   check=lambda r: ensure(ADER(r)['dimensions']['DM5']['lengths'] == [FT // 4] * 63
                          and ADER(r)['dimensions']['DM5']['total'] == 63 * FT // 4
                          and ADER(r)['dimensions']['DM6'] == {'level': 'L1', 'lengths': [FT], 'total': FT}
                          and ADER(r)['notes']['NT3'] == {'level': 'L1', 'about': None}
                          and ADER(r)['notes']['NT2'] == {'level': 'L1', 'about': None}, ADER(r)))

AI = lambda slug, text, covers, fn, diags=(), **k: AN('invariants', slug, text, covers, aedit(fn), diags, **k)   # noqa: E731
AI('dimension-id-of-a-wall', 'The overall string is keyed by W7, the south wall\'s ID: an annotation\'s ID is in the '
   'document\'s one space of IDs.', ['1.3.2'], lambda d: DMS(d).update(W7=DMS(d).pop('DM1')), [('FS-ANNO-INV-001', ['W7'])])
AI('dimension-id-of-a-room', 'The Kitchen\'s clear width is keyed by R1, the Kitchen\'s ID.', ['1.3.2'],
   lambda d: DMS(d).update(R1=DMS(d).pop('DM3')), [('FS-ANNO-INV-001', ['R1'])])
AI('dimension-id-of-a-level', 'A string keyed by L1, the level it is drawn on.', ['1.3.2'],
   lambda d: DMS(d).update(L1=DMS(d).pop('DM4')), [('FS-ANNO-INV-001', ['L1'])])
AI('dimension-id-of-an-opening', 'The window\'s string keyed by O1, the window it locates.', ['1.3.2'],
   lambda d: DMS(d).update(O1=DMS(d).pop('DM2')), [('FS-ANNO-INV-001', ['O1'])])
AI('note-id-of-a-lamp', 'A note keyed by X20, the table lamp\'s ID: an extension element of any extension, known or '
   'not.', ['1.3.2'], lambda d: NTS(d).update(X20=NTS(d).pop('NT2')), [('FS-ANNO-INV-001', ['X20'])])
AI('note-id-of-a-program-item', 'The house has a program with an item P1, and a note is keyed by P1.', ['1.3.2'],
   lambda d: (d.update(program={'items': {'P1': {'function': 'kitchen'}}}), NTS(d).update(P1=NTS(d).pop('NT1'))),
   [('FS-ANNO-INV-001', ['P1'])])
AI('dimension-id-of-a-scene', 'A string keyed by LS1, an FS_lighting scene\'s ID: a scene\'s ID is in the one space of '
   'IDs, read as data.', ['1.3.2'], lambda d: DMS(d).update(LS1=DMS(d).pop('DM4')), [('FS-ANNO-INV-001', ['LS1'])])
AI('note-id-of-a-view', 'A note keyed by SV2, the ID of FS_views\'s view of the Kitchen island, read as data.', ['1.3.2'],
   lambda d: NTS(d).update(SV2=NTS(d).pop('NT2')), [('FS-ANNO-INV-001', ['SV2'])])
AI('note-id-of-a-dimension', 'The window\'s note is keyed by DM2, the ID of the string that locates the window: a note '
   'and a dimension string never share an ID. Reported once, for the note.', ['1.3.2', '1.2.3'],
   lambda d: NTS(d).update(DM2=NTS(d).pop('NT1')), [('FS-ANNO-INV-001', ['DM2'])])
AI('ids-without-scenes-and-views', 'The house without FS_lighting and FS_views, a string keyed by LS1 and a note by SV2: '
   'there are no scenes and no views, so neither is anyone\'s ID. Valid.', ['1.3.2'],
   lambda d: (without_scenes_and_views(d), DMS(d).update(LS1=DMS(d).pop('DM4')), NTS(d).update(SV2=NTS(d).pop('NT2'))),
   check=lambda r: ensure(sorted(ADER(r)['dimensions']) == ['DM1', 'DM2', 'DM3', 'LS1'] and sorted(ADER(r)['notes']) == ['NT1', 'SV2'], ADER(r)))
AI('ids-of-data-not-an-object', 'FS_views\'s data is a string and FS_lighting\'s `scenes` a list, which no implementation '
   'of FS_annotation checks: they hold no view and no scene, so a string keyed SV1 and a note keyed LS1 take no one\'s '
   'ID. Valid.', ['1.3.2'],
   lambda d: (d['extensions'].update({VIEW: 'four views'}), ext(d, LGHT).update(scenes=list(SCN(d).values())),
              DMS(d).update(SV1=DMS(d).pop('DM4')), NTS(d).update(LS1=NTS(d).pop('NT2'))),
   check=lambda r: ensure(sorted(ADER(r)['dimensions']) == ['DM1', 'DM2', 'DM3', 'SV1'], ADER(r)))
AI('level-of-nothing', 'The overall string is drawn on L2, which the house does not have.', ['1.3.3'],
   lambda d: DMS(d)['DM1'].update(level='L2'), [('FS-ANNO-INV-002', ['DM1'])])
AI('note-level-of-nothing', 'The window\'s note is drawn on L0, which the house does not have.', ['1.3.3'],
   lambda d: NTS(d)['NT1'].update(level='L0'), [('FS-ANNO-INV-002', ['NT1'])])
AI('level-of-a-room', 'The Kitchen\'s clear width is drawn on R1, the Kitchen: a room is no level.', ['1.3.3'],
   lambda d: DMS(d)['DM3'].update(level='R1'), [('FS-ANNO-INV-002', ['DM3'])])
AI('level-of-another-level', 'A second level L2, and the panel\'s note drawn on it: any level of the document. Valid, '
   'and its level derived.', ['1.3.3', '6.1.1'], lambda d: (level2(d), NTS(d)['NT2'].update(level='L2')),
   check=lambda r: ensure(ADER(r)['notes']['NT2'] == {'level': 'L2', 'about': 'X1'}, ADER(r)['notes']))
AI('direction-zero', 'The Kitchen\'s clear width measured along [0, 0]: no direction at all.', ['2.1.1'], INV_A, INV_A_DIAG)
AI('direction-reversed', 'The overall string measured along [-2, 0]: the same direction as [1, 0], backwards and longer. '
   'Valid, and its lengths the same.', ['2.1.1', '6.1.1'], lambda d: DMS(d)['DM1'].update(direction=[-2, 0]),
   check=check_anno)
AI('direction-zero-on-a-level-of-nothing', 'The Kitchen\'s clear width measured along [0, 0] on a level L9 the house '
   'does not have: both reported.', ['1.2.3', '1.3.3', '2.1.1'],
   lambda d: (INV_A(d), DMS(d)['DM3'].update(level='L9')), [('FS-ANNO-INV-002', ['DM3']), ('FS-ANNO-INV-003', ['DM3'])])
AI('every-one-once', 'Every invariant broken at once - a string keyed X1, the panel\'s ID; a note keyed DM3, a string\'s; '
   'a note on L9; and a string along [0, 0]: each reported once, naming its annotation.',
   ['1.2.3', '1.3.2', '1.3.3', '2.1.1'],
   lambda d: (DMS(d).update(X1=DMS(d).pop('DM1')), NTS(d).update(DM3=NTS(d).pop('NT2')), NTS(d)['NT1'].update(level='L9'),
              DMS(d)['DM4'].update(direction=[0, 0])),
   [('FS-ANNO-INV-001', ['DM3']), ('FS-ANNO-INV-001', ['X1']), ('FS-ANNO-INV-002', ['NT1']), ('FS-ANNO-INV-003', ['DM4'])])

AL = lambda slug, text, covers, fn, diags=(), **k: AN('lints', slug, text, covers, aedit(fn), diags, **k)   # noqa: E731
L1 = lambda did: ('FS-ANNO-LINT-001', [did])                                                               # noqa: E731
L2_ = lambda did: ('FS-ANNO-LINT-002', [did])                                                              # noqa: E731
AL('junction-of-nothing', 'The overall string measures to J9, which the house does not have: it is not resolved, '
   'and derives no lengths.', ['1.2.3', '2.2.1', '6.1.1'], LINT_A, [L1('DM1')],
   check=lambda r: ensure(ADER(r)['dimensions']['DM1'] == UNRESOLVED, ADER(r)['dimensions']))
AL('wall-of-nothing', 'The Kitchen\'s clear width measures to the right face of W12, which the house does not have.',
   ['1.2.3', '2.2.1'], lambda d: DMS(d)['DM3']['anchors'].__setitem__(0, wA('W12', 'right')), [L1('DM3')])
AL('opening-of-nothing', 'The window\'s string measures to the centre of O2, which the house does not have.',
   ['1.2.3', '2.2.1'], lambda d: DMS(d)['DM2']['anchors'].__setitem__(1, oA('O2')), [L1('DM2')])
AL('junction-of-a-wall', 'The overall string\'s junction anchor names W8, a wall: an anchor names a feature of its own '
   'kind.', ['1.2.3', '2.2.1'], lambda d: DMS(d)['DM1']['anchors'].__setitem__(1, jA('W8')), [L1('DM1')])
AL('wall-of-a-separator', 'The wall W10 between the Living and Utility rooms made a room separator S1, and the north-south '
   'string measuring to S1 as a wall: a separator is no wall.', ['1.2.3', '2.2.1'],
   lambda d: (d['walls'].pop('W10'), d.update(separators={'S1': {'level': 'L1', 'start': 'J7', 'end': 'J8'}}),
              DMS(d)['DM4'].update(anchors=[wA('W6', 'right'), wA('S1', 'location'), wA('W3', 'right')])),
   [L1('DM4')])
AL('on-another-level', 'A second level L2, and the overall string drawn on it: its anchors are walls and a junction of '
   'L1, another level, so it is not resolved.', ['1.2.3', '2.2.1', '6.1.1'],
   lambda d: (level2(d), DMS(d)['DM1'].update(level='L2')), [L1('DM1')],
   check=lambda r: ensure(ADER(r)['dimensions']['DM1'] == {'level': 'L2', 'lengths': None, 'total': None}, ADER(r)['dimensions']))
AL('opening-on-another-level', 'A string DM5 on L2 from a point to the window\'s centre: the window is on its wall\'s '
   'level, L1.', ['1.2.3', '2.2.1'],
   lambda d: (level2(d), DMS(d).update(DM5=dim('L2', [1, 0], [0, 0], [pA(0, 0), oA('O1')]))), [L1('DM5')])
AL('points-on-any-level', 'A string DM5 on L2 between two points: a point is associated with nothing, so on any level. '
   'Resolved, 3\' long.', ['2.2.1', '6.1.1'],
   lambda d: (level2(d), DMS(d).update(DM5=dim('L2', [0, 1], [0, 0], [pA(5 * FT, 0), pA(-7 * FT, 3 * FT)]))),
   check=lambda r: ensure(ADER(r)['dimensions']['DM5'] == {'level': 'L2', 'lengths': [3 * FT], 'total': 3 * FT}, ADER(r)['dimensions']))
AL('two-anchors-of-nothing', 'The window\'s string measures to J9 and to O2, neither of which the house has: reported '
   'once, for the string.', ['1.2.3', '2.2.1'],
   lambda d: DMS(d)['DM2'].update(anchors=[jA('J9'), oA('O2'), jA('J3')]), [L1('DM2')])
AL('face-parallel-to-the-direction', 'The window\'s string measures east-west to the inside face of the north wall W2, '
   'which runs east-west too: the face never crosses the dimension line.', ['1.2.3', '2.2.2', '6.1.1'],
   lambda d: DMS(d)['DM2']['anchors'].append(wA('W2', 'right')), [L2_('DM2')],
   check=lambda r: ensure(ADER(r)['dimensions']['DM2'] == UNRESOLVED, ADER(r)['dimensions']))
AL('location-parallel-to-the-direction', 'A string along [3, 0] to the location line of W7, the south wall, which runs '
   'east-west.', ['1.2.3', '2.2.2'],
   lambda d: DMS(d)['DM1']['anchors'].__setitem__(1, wA('W7', 'location')) or DMS(d)['DM1'].update(direction=[3, 0]),
   [L2_('DM1')])
AL('arc-wall', 'The house as a Core 0.4 document whose north wall over the Living room, W3, is an arc bulging 2\' '
   'out: the north-south string through the Living room measures to its inside face, a curve, which FS_annotation '
   '0.1 does not measure to.', ['1.2.3', '2.2.2', '6.1.1'], arc_w3, [L2_('DM4')],
   check=lambda r: ensure(ADER(r)['dimensions']['DM4'] == UNRESOLVED and ADER(r)['dimensions']['DM1'] == ANNOTATED['dimensions']['DM1'],
                          ADER(r)['dimensions']))
AL('arc-wall-location', 'The same arc wall W3, measured to its location line by a string along its chord\'s normal: an '
   'arc wall\'s lines are curves, whichever is named.', ['1.2.3', '2.2.2'],
   lambda d: (arc_w3(d), DMS(d)['DM4']['anchors'].__setitem__(3, wA('W3', 'location'))), [L2_('DM4')])
AL('both-lints', 'The overall string measures to the face of W12, which the house does not have, and along [1, 0] to '
   'the face of W10, which runs east-west: each lint reported once.', ['1.2.3', '2.2.1', '2.2.2'],
   lambda d: DMS(d)['DM1'].update(anchors=[wA('W12', 'right'), wA('W10', 'right'), jA('J5')]),
   [L1('DM1'), L2_('DM1')])
AL('same-junction-twice', 'The overall string measures to J6 twice in a row: a segment of no length.',
   ['1.2.3', '2.3.1'], lambda d: DMS(d)['DM1']['anchors'].insert(1, jA('J6')), [('FS-ANNO-LINT-003', ['DM1'])],
   check=lambda r: ensure(ADER(r)['dimensions']['DM1']['lengths'] == [12 * FT + MM50, 0, 8 * FT + MM50], ADER(r)['dimensions']))
AL('a-junction-and-its-location-line', 'A string along [1, 0] from the location line of W1 to J2, a junction on it: '
   'two anchors at the same position.', ['1.2.3', '2.3.1'],
   lambda d: DMS(d).update(DM5=dim('L1', [1, 0], [0, 14 * FT], [wA('W1', 'location'), jA('J2'), jA('J3')])),
   [('FS-ANNO-LINT-003', ['DM5'])])
AL('not-consecutive', 'A string from J1 to J6 and back to J1: no two consecutive anchors at one position, so no lint; '
   'its total is from J1 to J1, 0.', ['2.3.1', '6.1.1'],
   lambda d: DMS(d).update(DM5=dim('L1', [1, 0], [0, -3 * FT], [jA('J1'), jA('J6'), jA('J1')])),
   check=lambda r: ensure(ADER(r)['dimensions']['DM5'] == {'level': 'L1', 'lengths': [12 * FT, 12 * FT], 'total': 0},
                          ADER(r)['dimensions']))
AL('less-than-half-a-unit', 'A string along [1, 2] between the points (0, 0) and (1, 0), 1/sqrt(5) of a base unit apart '
   'along it: not of no length, though it is written 0. No lint.', ['2.3.1', '6.1.1'],
   lambda d: DMS(d).update(DM5=dim('L1', [1, 2], [0, 0], [pA(0, 0), pA(1, 0)])),
   check=lambda r: ensure(ADER(r)['dimensions']['DM5'] == {'level': 'L1', 'lengths': [0], 'total': 0}, ADER(r)['dimensions']))
AL('unresolved-not-tested', 'The overall string measures to J9, which the house does not have, and to J6 twice: it is '
   'not resolved, so it has no positions to compare - FS-ANNO-LINT-001 alone.', ['1.2.3', '2.3.1'],
   lambda d: DMS(d)['DM1'].update(anchors=[jA('J9'), jA('J6'), jA('J6')]), [L1('DM1')])
AL('about-nothing', 'The window\'s note is about O2, which the house does not have.', ['1.2.3', '3.1.1', '6.1.1'],
   lambda d: NTS(d)['NT1'].update(about='O2'), [('FS-ANNO-LINT-004', ['NT1'])],
   check=lambda r: ensure(ADER(r)['notes']['NT1'] == {'level': 'L1', 'about': 'O2'}, ADER(r)['notes']))
AL('about-a-dimension', 'The window\'s note is about DM2, the string that locates the window. No lint.', ['3.1.1'],
   lambda d: NTS(d)['NT1'].update(about='DM2'))
AL('about-a-scene-and-a-view', 'The notes are about LS1, the Evening scene, and SV3, the dusk view: read as data. No '
   'lint.', ['3.1.1'], lambda d: (NTS(d)['NT1'].update(about='LS1'), NTS(d)['NT2'].update(about='SV3')))
AL('about-another-note', 'The panel\'s note is about NT1, another note: a note is not among what a note is about.',
   ['1.2.3', '3.1.1'], lambda d: NTS(d)['NT2'].update(about='NT1'), [('FS-ANNO-LINT-004', ['NT2'])])
AL('about-a-scene-without-lighting', 'The house without FS_lighting and FS_views, and a note about LS1: there are no '
   'scenes.', ['1.2.3', '3.1.1'], lambda d: (without_scenes_and_views(d), NTS(d)['NT1'].update(about='LS1')),
   [('FS-ANNO-LINT-004', ['NT1'])])
AL('every-one-once', 'Every lint at once: a string of a missing junction, one along a parallel face, one of a '
   'segment of no length, and two notes about nothing - each once.', ['1.2.3', '2.2.1', '2.2.2', '2.3.1', '3.1.1'],
   lambda d: (LINT_A(d), DMS(d)['DM2']['anchors'].append(wA('W2', 'right')), DMS(d)['DM3']['anchors'].insert(1, wA('W1', 'right')),
              NTS(d)['NT1'].update(about='O9'), NTS(d)['NT2'].update(about='X99')),
   [L1('DM1'), L2_('DM2'), ('FS-ANNO-LINT-003', ['DM3']), ('FS-ANNO-LINT-004', ['NT1']), ('FS-ANNO-LINT-004', ['NT2'])])

AD = lambda slug, text, fn, check, covers=('6.1.1',), diags=(): AN('derived', slug, text, list(covers), aedit(fn), diags, check=check)   # noqa: E731
AD('note-defaults', 'A note NT3 of only a level, a text and a point: no leader, and about nothing, so `about` null.',
   lambda d: NTS(d).update(NT3={'level': 'L1', 'text': 'North', 'at': [10 * FT, 14 * FT]}),
   lambda r: ensure(ADER(r)['notes']['NT3'] == {'level': 'L1', 'about': None}, ADER(r)['notes']))
AD('in-id-order', 'A string DM10 and a note NT10: annotations are in ID order by code unit, DM1, DM10, DM2.',
   lambda d: (DMS(d).update(DM10=dim('L1', [0, 1], [-FT, 0], [jA('J1'), jA('J2')])),
              NTS(d).update(NT10={'level': 'L1', 'text': 'West', 'at': [-3 * FT, 6 * FT]})),
   lambda r: ensure(list(ADER(r)['dimensions']) == ['DM1', 'DM10', 'DM2', 'DM3', 'DM4'] and list(ADER(r)['notes']) == ['NT1', 'NT10', 'NT2']
                    and ADER(r)['dimensions']['DM10'] == {'level': 'L1', 'lengths': [12 * FT], 'total': 12 * FT}, ADER(r)))
AD('total-not-the-sum', 'A string along [1, 2] through four points a base unit apart east-west, each 1/sqrt(5) of a unit '
   'from the next along it: each segment is 0, and the total, 3/sqrt(5), is 1 - measured, not added up.',
   lambda d: DMS(d).update(DM5=dim('L1', [1, 2], [0, 0], [pA(k, 0) for k in range(4)])),
   lambda r: ensure(ADER(r)['dimensions']['DM5'] == {'level': 'L1', 'lengths': [0, 0, 0], 'total': 1}, ADER(r)['dimensions']))
AD('anchors-in-any-order', 'A string from J6 to J1 to J5: segments are lengths, whichever way they run, and the total '
   'is from the first anchor to the last, J6 to J5 - 8\'.',
   lambda d: DMS(d).update(DM5=dim('L1', [1, 0], [0, -3 * FT], [jA('J6'), jA('J1'), jA('J5')])),
   lambda r: ensure(ADER(r)['dimensions']['DM5'] == {'level': 'L1', 'lengths': [12 * FT, 20 * FT], 'total': 8 * FT},
                    ADER(r)['dimensions']))
AD('kitchen-diagonal', 'A string along [1, 1] from J1 to J3, the Kitchen\'s diagonal: 12\' x sqrt(2), irrational, rounded '
   'once.', lambda d: DMS(d).update(DM5=dim('L1', [1, 1], [0, 0], [jA('J1'), jA('J3')])),
   lambda r: ensure(ADER(r)['dimensions']['DM5']['total'] == 6620963 and ADER(r)['dimensions']['DM5']['lengths'] == [6620963],
                    ADER(r)['dimensions']['DM5']))
AD('oblique-across-faces', 'The Kitchen\'s clear width measured along [1, 1]: the faces of W1 and W8 cross the oblique '
   'line sqrt(2) times as far apart as they are, (12\' - 100 mm) x sqrt(2), and where it is drawn does not change it.',
   lambda d: DMS(d)['DM3'].update(direction=[1, 1], through=[0, -5 * FT]),
   lambda r: ensure(ADER(r)['dimensions']['DM3']['total'] == 6439944, ADER(r)['dimensions']['DM3']))
AD('oblique-face-moves-with-through', 'The Kitchen\'s north-west corner cut off by a wall W11, 2\' east for every 3\' '
   'north, and two strings along [1, 0] from J9, at its foot, to its location line: drawn 6" above J9 the line is 4" '
   'east of it, and drawn 1\' 6" above, 1\' east. Where a string crosses an oblique wall\'s line depends on where it is '
   'drawn; where it measures a junction does not.',
   lambda d: (chamfer(d), DMS(d).pop('DM2'),
              DMS(d).update(DM5=dim('L1', [1, 0], [0, 9 * FT + 6 * IN], [jA('J9'), wA('W11', 'location')]),
                            DM6=dim('L1', [1, 0], [0, 10 * FT + 6 * IN], [jA('J9'), wA('W11', 'location')]))),
   lambda r: ensure(ADER(r)['dimensions']['DM5']['total'] == 4 * IN and ADER(r)['dimensions']['DM6']['total'] == 12 * IN,
                    ADER(r)['dimensions']))
AD('chamfered-corner', 'The Kitchen\'s north-west corner cut off by a wall W11, 2\' east for every 3\' north, with a 2\' '
   'window O2 in it, and a string along [1, -1] across the corner, through the middle of W11, from its outside face to '
   'O2\'s centre, its inside face and J3: '
   'every position irrational - sqrt(13) from the wall, sqrt(2) from the direction - and each length rounded once, as '
   'an independent computation in 60-digit decimals finds.',
   lambda d: (chamfer(d), DMS(d).pop('DM2'),
              DMS(d).update(DM5=dim('L1', [1, -1], [FT, 10 * FT + 6 * IN], [wA('W11', 'left'), oA('O2'), wA('W11', 'right'), jA('J3')],
                                    'Chamfer'))),
   chamfer_check)
AD('opening-on-an-arc-wall', 'The house as a Core 0.4 document with an arc north wall W3, a 3\' window O2 in it 2\' '
   'along it, and a string from J3 to O2\'s centre - the middle of its chord (Core 21.6) - to J4: the window\'s centre is '
   'measured - about 2\' 11" east of J3, since the window stands 2\' to 5\' along the arc\'s polyline, not its chord - and '
   'the total is exactly 8\'.',
   lambda d: (arc_w3(d), DMS(d).pop('DM4'),
              d['openings'].update(O2={'wall': 'W3', 'offset': 2 * FT, 'width': 3 * FT, 'fill': 'WN', 'name': 'Bay window'}),
              DMS(d).update(DM5=dim('L1', [1, 0], [0, 16 * FT], [jA('J3'), oA('O2'), jA('J4')]))),
   lambda r: ensure(ADER(r)['dimensions']['DM5']['total'] == 8 * FT and sum(ADER(r)['dimensions']['DM5']['lengths']) == 8 * FT
                    # on a circle of radius 5' about (16', 9'), 2' and 5' along the arc from J3: x = 13.484' and 16.364'
                    and abs(ADER(r)['dimensions']['DM5']['lengths'][0] - round(2.924 * FT)) < FT // 100, ADER(r)['dimensions']['DM5']),
   covers=('6.1.1', 'FS-CORE-21.6.1'))
AD('moved-junction', 'The interior corner J6 moved 1\' east, to (13\', 0), with the walls that meet there: the overall '
   'string follows it - 13\' and 50 mm, then 7\' and 50 mm - and its total is unchanged.',
   lambda d: d['junctions']['J6'].update(position=[13 * FT, 0]),
   lambda r: ensure(ADER(r)['dimensions']['DM1'] == {'level': 'L1', 'lengths': [13 * FT + MM50, 7 * FT + MM50], 'total': 20 * FT + 2 * MM50},
                    ADER(r)['dimensions']['DM1']))
AD('thicker-wall', 'The west wall W1 200 mm thick, still centred: its outside face moves 50 mm west and its inside face '
   '50 mm east, and every string that measures to them changes with it.',
   lambda d: (d['types'].update(WT2={'kind': 'wallType', 'layers': [{'thickness': 200 * MM, 'function': 'core'}]}),
              d['walls']['W1'].update(type='WT2')),
   lambda r: ensure([ADER(r)['dimensions'][x]['total'] for x in ('DM1', 'DM2', 'DM3')]
                    == [20 * FT + 3 * MM50, 12 * FT + 2 * MM50, 12 * FT - 3 * MM50], ADER(r)['dimensions']))
AD('justified-wall', 'The west wall W1 justified "interiorFace": its location line is its inside face, and its outside '
   'face 100 mm west of it. The overall string grows by 50 mm, the Kitchen\'s clear width by 50 mm.',
   lambda d: d['walls']['W1'].update(justification='interiorFace'),
   lambda r: ensure([ADER(r)['dimensions'][x]['total'] for x in ('DM1', 'DM3')] == [20 * FT + 3 * MM50, 12 * FT - MM50],
                    ADER(r)['dimensions']))


def anno_options(d):
    """Core 0.3 design options for the Kitchen's window: option A (OP1, the primary) keeps O1; option B
    (OP2) has a wider window O2 of 6', 3' from J2, in its place."""
    d['floorspec'] = '0.3'
    d['optionSets'] = {'OS1': {'primary': 'OP1', 'name': 'Kitchen window'}}
    d['options'] = {'OP1': {'set': 'OS1', 'name': 'A'}, 'OP2': {'set': 'OS1', 'name': 'B'}}
    d['openings']['O1']['option'] = 'OP1'
    d['openings']['O2'] = {'wall': 'W2', 'offset': 3 * FT, 'width': 6 * FT, 'fill': 'WN', 'option': 'OP2'}


AN('options', 'window-of-one-option', 'Kitchen window options A and B as Core 0.3 design options (Core 19), the window '
   'string measuring A\'s window O1: FS_annotation is evaluated in each checked design, so in B\'s design, without O1, '
   'the string is not resolved, reported with `design` (Core 19.5.2), and so is the note about O1; A\'s, the primary, '
   'derives its lengths.', ['1.2.1', '1.2.3', '2.2.1', '3.1.1', 'FS-CORE-19.3.1'], aedit(anno_options),
   [('FS-ANNO-LINT-001', ['DM2'], 'OP2'), ('FS-ANNO-LINT-004', ['NT1'], 'OP2')],
   check=lambda r: ensure(ADER(r) == ANNOTATED and r['derived']['options']['OS1']['chosen'] == 'OP1', ADER(r)))
AN('options', 'derived-for-a-design', 'The same options, the derived values asked for B\'s design (Core 19.6): the '
   'window string is not resolved there, and derives no lengths.', ['1.2.4', '6.1.1', 'FS-CORE-19.6.1'], aedit(anno_options),
   [('FS-ANNO-LINT-001', ['DM2'], 'OP2'), ('FS-ANNO-LINT-004', ['NT1'], 'OP2')], design={'OS1': 'OP2'},
   check=lambda r: ensure(ADER(r)['dimensions']['DM2'] == UNRESOLVED and r['derived']['options']['OS1']['chosen'] == 'OP2', ADER(r)))
AN('options', 'dimension-id-of-an-option-element', 'The same options, and a string keyed by O2, the ID of B\'s window: '
   'in B\'s design it takes an element\'s ID, reported with `design`; in A\'s, without O2, it does not.',
   ['1.2.1', '1.2.3', '1.3.2', 'FS-CORE-19.3.1'],
   aedit(lambda d: (anno_options(d), DMS(d).update(O2=DMS(d).pop('DM4')))), [('FS-ANNO-INV-001', ['O2'], 'OP2')])


def anno_lints(d):
    data = json.dumps(d).encode('utf-8')
    result, _, _ = check(data, ext_reader(data), json.dumps([entry(ANNO)]).encode('utf-8'), official.implemented(ANNO))
    return [(x['code'], x['elements']) for x in result['diagnostics'] if x['code'].startswith('FS-ANNO-')]


def anno_derived(d):
    data = json.dumps(d).encode('utf-8')
    result, _, _ = check(data, ext_reader(data), json.dumps([entry(ANNO)]).encode('utf-8'), official.implemented(ANNO))
    assert result['valid'], result['diagnostics']
    return result['derived']['extensions'][ANNO]


PORCH = dim('L1', [0, 1], [21 * FT, 0], [wA('W6', 'left'), jA('J8'), wA('W3', 'left')], 'Overall, east')
AO = lambda *a, **k: O(ANNO, *a, **k)    # noqa: E731
AO('add-a-dimension', 'setProperty of $document /extensions/FS_annotation/dimensions/DM5 adds an overall string up the '
   'east side, from the south wall\'s outside face through J8 to the north wall\'s, with an ID Ops does not mint (1.3.2). '
   'It commits, valid under FS_annotation, and measures 6\' and 50 mm twice.',
   ['1.2.1', '1.3.2', '2.2.1', '6.1.1', 'FS-OPS-2.3.1'], annotation_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_annotation/dimensions/DM5', 'value': PORCH}]},
   check=lambda r, B: ensure(anno_derived(B)['dimensions']['DM5'] == {'level': 'L1', 'lengths': [6 * FT + MM50] * 2,
                                                                     'total': 12 * FT + 2 * MM50}, anno_derived(B)))
AO('first-note-creates-the-data', 'The house declaring FS_annotation with no data of it yet: setProperty of $document '
   '/extensions/FS_annotation/notes/NT1 creates FS_annotation\'s data, and its `notes`, on the way (Ops 2.3) - the '
   'window\'s note. It commits, valid under FS_annotation.', ['1.2.1', '1.3.1', '6.1.1', 'FS-OPS-2.3.1'],
   aedit(lambda d: d['extensions'].pop(ANNO)),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_annotation/notes/NT1',
               'value': ANNOTATION['notes']['NT1']}]},
   check=lambda r, B: ensure(B['extensions'][ANNO] == {'notes': {'NT1': ANNOTATION['notes']['NT1']}}
                             and anno_derived(B) == {'dimensions': {}, 'notes': {'NT1': {'level': 'L1', 'about': 'O1'}}},
                             B['extensions'].get(ANNO)))
AO('move-a-dimension', 'setProperty of $document /extensions/FS_annotation/dimensions/DM1/through: the overall string '
   'is drawn 2\' further south. It commits, and measures exactly what it did.', ['1.2.1', '6.1.1', 'FS-OPS-2.3.1'],
   annotation_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_annotation/dimensions/DM1/through',
               'value': [0, -1200 * MM - 2 * FT]}]},
   check=lambda r, B: ensure(anno_derived(B) == ANNOTATED and ext(B, ANNO)['dimensions']['DM1']['through'] == [0, -1200 * MM - 2 * FT],
                             anno_derived(B)))
AO('remove-a-dimension', 'unsetProperty of $document /extensions/FS_annotation/dimensions/DM3 removes the Kitchen\'s '
   'clear width. It commits.', ['1.2.1', '6.1.1', 'FS-OPS-2.3.1'], annotation_house(),
   {'batch': [{'op': 'unsetProperty', 'id': '$document', 'path': '/extensions/FS_annotation/dimensions/DM3'}]},
   check=lambda r, B: ensure(list(anno_derived(B)['dimensions']) == ['DM1', 'DM2', 'DM4'], anno_derived(B)))
AO('direction-zero-is-rejected', 'setProperty of $document /extensions/FS_annotation/dimensions/DM3/direction to [0, 0]: '
   'the result breaks 2.1.1, and an applier that implements FS_annotation and knows it rejects the batch (Ops 1.2.3).',
   ['2.1.1', '1.2.1', 'FS-OPS-1.2.3'], annotation_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_annotation/dimensions/DM3/direction',
               'value': [0, 0]}]},
   'rejected', INV_A_DIAG)
AO('note-on-a-level-of-nothing-is-rejected', 'setProperty of $document /extensions/FS_annotation/notes/NT3, a note on '
   'L2, which the house does not have: the result breaks 1.3.3, and the batch is rejected.',
   ['1.3.3', '1.2.1', 'FS-OPS-1.2.3'], annotation_house(),
   {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_annotation/notes/NT3',
               'value': {'level': 'L2', 'text': 'Upstairs', 'at': [0, 0]}}]},
   'rejected', [('FS-ANNO-INV-002', ['NT3'])])
AO('remove-a-wall-a-dimension-measures', 'removeWall W10, keeping the Living room: the Utility room joins it, and the '
   'north-south string that measures to both faces of W10 names a wall the house no longer has. That is not an error '
   'of FS_annotation: the batch commits - a committed result carries no lints (Ops 1.2) - and the document it makes, '
   'validated, reports FS-ANNO-LINT-001 for the string, which derives no lengths until its owner mends it.',
   ['2.2.1', '1.2.1', '6.1.1', 'FS-OPS-4.7.1'], annotation_house(),
   {'batch': [{'op': 'removeWall', 'wall': 'W10', 'keep': 'R2'}]},
   check=lambda r, B: ensure(anno_derived(B)['dimensions']['DM4'] == UNRESOLVED and 'W10' not in B['walls']
                             and anno_lints(B) == [('FS-ANNO-LINT-001', ['DM4'])], anno_derived(B)['dimensions']))
AO('move-a-junction-a-dimension-measures', 'moveJunction J6 to (13\', 0): the walls that meet there move with it, and '
   'so do the strings that measure them - the overall string is 13\' and 50 mm, then 7\' and 50 mm. It commits.',
   ['1.2.1', '6.1.1', 'FS-OPS-2.4.1'], annotation_house(),
   {'batch': [{'op': 'moveJunction', 'id': 'J6', 'to': [13 * FT, 0]}]},
   check=lambda r, B: ensure(anno_derived(B)['dimensions']['DM1']['lengths'] == [13 * FT + MM50, 7 * FT + MM50],
                             anno_derived(B)['dimensions']))


# ============================================================================= FS_site

SITE = 'FS_site'
CODE[SITE] = 'SITE'
FT3 = FT ** 3                                      # a cubic foot, in cubic base units


def F(x, y):
    """A point in feet, exactly: x and y in whole or half feet."""
    return [int(x * 2) * FT // 2, int(y * 2) * FT // 2]


SURVEY_DATUM = 814 * FT + FT // 2                  # the survey's 814' 6": the first floor
LOT = [F(-30, -40), F(40, -40), F(40, 30), F(-30, 30)]
SITE_DATA = {
    'benchmark': SURVEY_DATUM,
    'spots': {
        'SP1': {'at': F(-30, 30), 'elevation': 5 * FT // 2, 'name': 'NW corner'},
        'SP2': {'at': F(40, 30), 'elevation': 2 * FT, 'name': 'NE corner'},
        'SP3': {'at': F(40, -40), 'elevation': -5 * FT, 'name': 'SE corner'},
        'SP4': {'at': F(-30, -40), 'elevation': -9 * FT // 2, 'name': 'SW corner'},
        'SP5': {'at': F(5, 6), 'elevation': -FT // 2},
    },
    'contours': {
        'CT1': {'elevation': -3 * FT // 2, 'points': [F(-30, -8), F(0, -6), F(40, -10)], 'name': '813\''},
        'CT2': {'elevation': FT // 2, 'points': [F(-30, 16), F(10, 18), F(40, 14)], 'name': '815\''},
    },
    'setbacks': {'street': [0], 'front': 25 * FT, 'side': 5 * FT, 'rear': 10 * FT},
    'pads': {'GP1': {'name': 'House', 'elevation': -8 * IN, 'boundary': [F(-1, -1), F(29, -1), F(29, 13), F(-1, 13)]}},
}


def site_house():
    """The Phase 13 garden (garden()) on a lot that falls to the street, as a Core 0.4 document:

    - the lot, the site's boundary: 70' x 70', from (-30', -40') to (40', 30'), its south edge (edge 0)
      on the street;
    - setbacks of 25' at the front, 5' at the sides and 10' at the rear - the house, 20' x 12' with its
      8' courtyard, from (0, 0) to (28', 12'), and its patio, 2' to 12' east and 1' to 10' south, sit
      well inside them;
    - a survey whose datum puts the first floor at 814' 6": spots at the four corners - 817' at the
      north-west, 816' 6" at the north-east, 809' 6" at the south-east and 810' at the south-west - and
      one in the Kitchen at 814', and two contour lines across the lot at 813' and 815';
    - the patio S1 a patio slab (Core 0.3), stepped down 6" from the floor, 100 mm thick, which grades
      the ground to its bottom; and a pad GP1 under the house, 1' beyond its walls, at 8" below the
      floor."""
    d = garden()
    d['floorspec'] = '0.4'
    d['project']['name'] = 'Phase 15 garden on a slope'
    d['site'] = {'boundary': copy.deepcopy(LOT)}
    d['slabs']['S1'].update(purpose='patio', offset=-6 * IN)
    d['extensionsUsed'][SITE] = '0.1.0'
    d['extensions'][SITE] = copy.deepcopy(SITE_DATA)
    return d


def sedit_(fn):
    """The garden on its slope, changed by fn(d) in place."""
    d = site_house()
    fn(d)
    return d


SD_ = lambda d: ext(d, SITE)                                                       # noqa: E731
SPOTS = lambda d: ext(d, SITE)['spots']                                            # noqa: E731
CONT = lambda d: ext(d, SITE)['contours']                                          # noqa: E731
PADS = lambda d: ext(d, SITE)['pads']                                              # noqa: E731
SITE_DER = derived_of(SITE)
SI = lambda *a, **k: V(SITE, *a, **k)    # noqa: E731
SITE_ENTRY_KNOWN = ALL_KNOWN + (VIEW, RENO, ANNO, SITE)
PATIO_BOTTOM = -6 * IN - 100 * MM
LOT_EDGES = [{'kind': 'front', 'length': 70 * FT, 'setback': 25 * FT}, {'kind': 'side', 'length': 70 * FT, 'setback': 5 * FT},
             {'kind': 'rear', 'length': 70 * FT, 'setback': 10 * FT}, {'kind': 'side', 'length': 70 * FT, 'setback': 5 * FT}]


def check_site(r):
    x = SITE_DER(r)
    ensure(x['lot'] == {'area': str(70 * 70 * FT * FT), 'edges': LOT_EDGES}, x['lot'])
    s = x['surface']
    # 5 spots and 6 contour vertices, all at distinct positions; the low is the SE corner, the high the NW
    ensure(s['low'] == -5 * FT and s['high'] == 5 * FT // 2 and len(s['points']) == 11, s)
    ensure(s['points'][0] == F(-30, -40) + [-9 * FT // 2] and s['points'][-1] == F(40, 30) + [2 * FT], s['points'])
    # Euler: 11 points, 8 of them on the hull - the four corners and the contour lines' ends on its west and east
    # edges: 2n - h - 2 triangles
    ensure(len(s['triangles']) == 2 * 11 - 8 - 2, len(s['triangles']))
    g = x['grading']
    ensure(list(g) == ['GP1', 'S1'] and g['GP1']['kind'] == 'pad' and g['GP1']['elevation'] == -8 * IN
           and g['S1'] == {**g['S1'], 'kind': 'slab', 'elevation': PATIO_BOTTOM}, g)
    # the house pad cuts into the slope at its north side and fills at its south; the patio, down the slope, is filled
    ensure(int(g['GP1']['cut']) > 0 and int(g['GP1']['fill']) > 0 and g['S1']['cut'] == '0' and int(g['S1']['fill']) > 0, g)
    ensure(g['GP1']['low'] < -8 * IN < g['GP1']['high'], g['GP1'])
    # each total is rounded once from the exact sum: within a unit of the sum of the rounded volumes
    ensure(abs(int(x['cut']) - int(g['GP1']['cut']) - int(g['S1']['cut'])) <= 1, x)
    ensure(abs(int(x['fill']) - int(g['GP1']['fill']) - int(g['S1']['fill'])) <= 1, x)


def plane_ground(d):
    """The survey replaced by the four corners of the lot on one plane rising 1' for every 10' north: z = y / 10, 0
    at y = 0 - so every elevation and volume over it can be checked by hand."""
    SD_(d)['spots'] = {f'SP{i + 1}': {'at': p, 'elevation': p[1] // 10} for i, p in enumerate(LOT)}
    SD_(d)['contours'] = {}


def only_pad(d, boundary, e=0):
    """The patio no longer graded, and one pad GP1 with this outline at elevation e."""
    d['slabs']['S1'].pop('purpose')
    PADS(d).clear()
    PADS(d)['GP1'] = {'boundary': boundary, 'elevation': e}


BAD_SI = lambda d: SPOTS(d)['SP5'].update(at=[0, 0, 0])                           # noqa: E731  the schema tier
INV_SI = lambda d: CONT(d)['CT1']['points'].insert(1, F(-30, -8))                  # noqa: E731  FS-SITE-INV-003
INV_SI_DIAG = [('FS-SITE-INV-003', ['CT1'])]

SI('examples', 'p15-garden-on-a-slope', 'The Phase 13 garden on a 70\' square lot that falls about 7\' to the street, '
   'read by an implementation of FS_site that knows it: setbacks of 25\' at the front, 5\' at the sides and 10\' at the '
   'rear; a survey of five spot elevations and two contour lines; the patio, a patio slab stepped 6" down, and a pad '
   'under the house 8" below its floor. It is valid, reports nothing - the house, its patio and its pad are clear of '
   'the setbacks, and the survey covers the lot - and derives the lot\'s area and its edges (front, side, rear, side, '
   'each 70\' with its setback), the surface\'s eleven points and their triangles, and the cut and fill under the pad '
   'and the patio.',
   ['1.2.1', '1.2.3', '1.2.4', '1.3.1', '1.3.2', '2.2.1', '3.1.1', '3.1.2', '3.2.1', '4.1.1', '4.2.1', '7.1.1'],
   site_house(), check=check_site)
SI('examples', 'core-only-reader', 'The same garden read with no known extensions: FS_site is not evaluated, so nothing '
   'of it is derived (`derived.extensions` is empty); FS_site has no elements of its own, and Core derives the patio slab '
   'as ever.', ['1.2.1', '1.2.4', 'FS-CORE-1.6.9'], site_house(), registry=None,
   check=lambda r: ensure(r['derived']['extensions'] == {} and r['derived']['slabs']['S1']['bottom'] == PATIO_BOTTOM,
                          r['derived']['extensions']))
SI('examples', 'all-official-known', 'The garden read with every official entry known, by an implementation of FS_site '
   'alone: FS_landscape is checked only as Core 12 checks a known extension, and only FS_site is evaluated and derived.',
   ['1.2.1', '1.2.4'], site_house(), registry=[entry(x) for x in SITE_ENTRY_KNOWN],
   check=lambda r: ensure(list(r['derived']['extensions']) == [SITE], list(r['derived']['extensions'])))
SI('examples', 'no-data', 'FS_site used with empty top-level data: valid. The lot is Core\'s, so its area and edges are '
   'derived - each edge of no kind and no setback, since there are no setbacks - but there is no surface, and the patio, '
   'still a grading slab, has nothing to be measured against: its low, high, cut and fill are null, and so are the '
   'totals.', ['1.3.1', '2.2.1', '7.1.1'], sedit_(lambda d: d['extensions'].update({SITE: {}})),
   check=lambda r: ensure(SITE_DER(r) == {'lot': {'area': str(70 * 70 * FT * FT), 'edges': [{'kind': None, 'length': 70 * FT, 'setback': None}] * 4},
                                          'surface': None, 'grading': {'S1': {'kind': 'slab', 'elevation': PATIO_BOTTOM, 'low': None,
                                                                              'high': None, 'cut': None, 'fill': None}},
                                          'cut': None, 'fill': None}, SITE_DER(r)))
SI('examples', 'without-a-lot', 'The garden with no site and no setbacks, its survey and grading as before: no lot, and '
   'everything else as on the lot.', ['1.2.4', '2.2.1', '7.1.1'],
   sedit_(lambda d: (d.pop('site'), SD_(d).pop('setbacks'))),
   check=lambda r: ensure(SITE_DER(r)['lot'] is None and SITE_DER(r)['surface'] is not None and SITE_DER(r)['cut'] is not None,
                          SITE_DER(r)))
SI('examples', 'the-benchmark-is-a-label', 'The survey\'s datum moved by 100\' - a survey that measured from another '
   'benchmark: nothing derived changes, since every elevation is a height above project zero (1.4).', ['1.3.1', '7.1.1'],
   sedit_(lambda d: SD_(d).update(benchmark=SURVEY_DATUM + 100 * FT)),
   check=lambda r: ensure(SITE_DER(r)['surface']['low'] == -5 * FT and SITE_DER(r)['lot']['edges'] == LOT_EDGES, SITE_DER(r)))

SI('activation', 'unknown-data-not-evaluated', 'A spot\'s position has three numbers, which FS_site\'s schema does not '
   'allow, but no extension is known: nothing of it is evaluated, and the document is valid.', ['1.2.1'],
   sedit_(BAD_SI), registry=None)
SI('activation', 'another-version-known', 'The document uses FS_site at 0.2.0, which is known (a later entry), but the '
   'implementation implements 0.1.0: not evaluated, so the data that breaks 0.1.0\'s schema is not reported.', ['1.2.1'],
   sedit_(lambda d: (BAD_SI(d), d['extensionsUsed'].update({SITE: '0.2.0'}))), registry=[entry(SITE, '0.2.0')])
SI('activation', 'version-without-patch', '"0.1" equals 0.1.0 (Core 12.3), so FS_site is evaluated: its data breaks the '
   'schema, FS-SITE-SCH-001.', ['1.2.1', '1.3.1'],
   sedit_(lambda d: (BAD_SI(d), d['extensionsUsed'].update({SITE: '0.1'}))), [('FS-SITE-SCH-001', [])])
SI('activation', 'declaration-object', 'A declaration object with a schema URI is its version string (Core 12.1.3): '
   'FS_site is evaluated.', ['1.2.1', '1.3.1'],
   sedit_(lambda d: (BAD_SI(d), d['extensionsUsed'].update({SITE: {'version': '0.1.0', 'schema': entry(SITE)['schema']}}))),
   [('FS-SITE-SCH-001', [])])
SI('activation', 'core-0.1-document', 'A document declaring "0.1" has no extension elements and its extension data is '
   'opaque (Core 1.2.4): FS_site is not evaluated, even though it is known.', ['1.2.1'],
   {'floorspec': '0.1', 'project': {'name': 'Old'}, 'extensionsUsed': {SITE: '0.1.0'}, 'extensions': {SITE: {'colour': 'red'}}})


def as_02(d):
    """The garden on its slope declaring Core "0.2": a 0.2 slab has no purpose and no offset."""
    d['floorspec'] = '0.2'
    d['slabs']['S1'].pop('purpose')
    d['slabs']['S1'].pop('offset')


SI('activation', 'core-0.2-document', 'The garden on its slope declaring Core "0.2", a draft FS_site 0.1.0 lists (1.1): '
   'FS_site is evaluated and reports nothing. A Core 0.2 slab has no purpose, so the patio grades nothing: only the pad '
   'is measured (4.1).', ['1.2.1', '1.2.3', '1.2.4', '7.1.1'], sedit_(as_02),
   check=lambda r: ensure(list(SITE_DER(r)['grading']) == ['GP1'] and SITE_DER(r)['lot']['edges'] == LOT_EDGES, SITE_DER(r)))
SI('activation', 'core-0.3-document', 'The garden on its slope declaring Core "0.3", a draft FS_site 0.1.0 lists (1.1): '
   'FS_site is evaluated, reports nothing, and derives exactly what it derives for the garden declaring "0.4".',
   ['1.2.1', '1.2.3', '1.2.4', '7.1.1'], sedit_(lambda d: d.update(floorspec='0.3')), check=check_site)
SI('activation', 'core-0.3-invariants', 'The same "0.3" garden with a contour line\'s point written twice: FS_site is '
   'evaluated for a Core 0.3 document, so the invariant is reported.', ['1.2.1', '1.2.3', '3.1.1'],
   sedit_(lambda d: (d.update(floorspec='0.3'), INV_SI(d))), INV_SI_DIAG)

SI('order', 'core-error-first', 'A Core invariant breaks - the lot\'s boundary crosses itself, FS-INV-009 - and so does '
   'FS_site\'s schema: Core\'s error is reported, and FS_site is not evaluated.', ['1.2.2'],
   sedit_(lambda d: (BAD_SI(d), d['site'].update(boundary=[LOT[0], LOT[2], LOT[1], LOT[3]]))), [('FS-INV-009', [])])
SI('order', 'schema-before-invariants', 'The data breaks the schema and an invariant: only FS-SITE-SCH-001.',
   ['1.2.2', '1.3.1'], sedit_(lambda d: (BAD_SI(d), INV_SI(d))), [('FS-SITE-SCH-001', [])])
SI('order', 'no-lints-when-invalid', 'An invariant breaks and a lint would apply too - the rear setback is 20\', which '
   'the house\'s north wall is nearer than: the document is invalid, so no lint is reported, FS_site\'s or Core\'s.',
   ['1.2.2', '1.2.3'], sedit_(lambda d: (INV_SI(d), SD_(d)['setbacks'].update(rear=20 * FT))), INV_SI_DIAG)

SI('schema', 'data-not-an-object', 'FS_site\'s top-level data is an array: Core allows any JSON there, FS_site\'s schema '
   'does not.', ['1.3.1'], sedit_(lambda d: d['extensions'].update({SITE: []})), [('FS-SITE-SCH-001', [])])
SI('schema', 'unknown-member', 'FS_site\'s data has a member it does not define: `grid`.', ['1.3.1'],
   sedit_(lambda d: SD_(d).update(grid=FT)), [('FS-SITE-SCH-001', [])])
SI('schema', 'spot-with-an-unknown-member', 'A spot has a member a spot does not define.', ['1.3.1'],
   sedit_(lambda d: SPOTS(d)['SP1'].update(accuracy=IN)), [('FS-SITE-SCH-001', [])])
SI('schema', 'spot-without-an-elevation', 'A spot always says its elevation.', ['1.3.1'],
   sedit_(lambda d: SPOTS(d)['SP5'].pop('elevation')), [('FS-SITE-SCH-001', [])])
SI('schema', 'point-of-three-numbers', 'A point is two lengths.', ['1.3.1'], sedit_(BAD_SI), [('FS-SITE-SCH-001', [])])
SI('schema', 'elevation-with-a-fraction', 'A number written with a fraction is not an integer, even when it is a whole '
   'number.', ['1.3.1'], None, [('FS-SITE-SCH-001', [])],
   raw=(fmt(sedit_(lambda d: SPOTS(d)['SP5'].update(elevation=-195071))) + '\n').replace('-195071', '-195072.0', 1).encode('utf-8'))
SI('schema', 'contour-of-one-point', 'A contour line has at least two points.', ['1.3.1'],
   sedit_(lambda d: CONT(d)['CT1'].update(points=[F(0, -6)])), [('FS-SITE-SCH-001', [])])
SI('schema', 'contour-without-an-elevation', 'A contour line always says its elevation.', ['1.3.1'],
   sedit_(lambda d: CONT(d)['CT2'].pop('elevation')), [('FS-SITE-SCH-001', [])])
SI('schema', 'pad-of-two-points', 'A pad\'s outline is a polygon: at least three points.', ['1.3.1'],
   sedit_(lambda d: PADS(d)['GP1'].update(boundary=[F(-1, -1), F(29, -1)])), [('FS-SITE-SCH-001', [])])
SI('schema', 'setbacks-without-street', 'Setbacks always say which edges are on the street.', ['1.3.1'],
   sedit_(lambda d: SD_(d)['setbacks'].pop('street')), [('FS-SITE-SCH-001', [])])
SI('schema', 'street-empty', 'At least one edge is on the street.', ['1.3.1'],
   sedit_(lambda d: SD_(d)['setbacks'].update(street=[])), [('FS-SITE-SCH-001', [])])
SI('schema', 'street-repeated', 'The street edges are distinct.', ['1.3.1'],
   sedit_(lambda d: SD_(d)['setbacks'].update(street=[0, 0])), [('FS-SITE-SCH-001', [])])
SI('schema', 'negative-setback', 'A setback is a distance: at least 0.', ['1.3.1'],
   sedit_(lambda d: SD_(d)['setbacks'].update(side=-FT)), [('FS-SITE-SCH-001', [])])
SI('schema', 'name-too-long', 'A record\'s name is 1 to 200 characters.', ['1.3.1'],
   sedit_(lambda d: PADS(d)['GP1'].update(name='H' * 201)), [('FS-SITE-SCH-001', [])])
SI('schema', 'zero-setbacks', 'A setback of 0 is allowed: the lot line itself.', ['1.3.1', '7.1.1'],
   sedit_(lambda d: SD_(d)['setbacks'].update(front=0, side=0, rear=0)),
   check=lambda r: ensure([e['setback'] for e in SITE_DER(r)['lot']['edges']] == [0, 0, 0, 0], SITE_DER(r)['lot']))


def with_scene(rid):
    def fn(d):
        d['extensionsUsed']['FS_lighting'] = '0.1.0'
        d['extensions']['FS_lighting'] = {'scenes': {rid: {'name': 'Evening', 'lights': {}}}}
    return fn


SI('invariants', 'id-of-an-element', 'A spot keyed by W1, the ID of a wall: FS-SITE-INV-001.', ['1.3.2'],
   sedit_(lambda d: SPOTS(d).update(W1=SPOTS(d).pop('SP5'))), [('FS-SITE-INV-001', ['W1'])])
SI('invariants', 'id-of-an-extension-element', 'A pad keyed by X1, the ID of FS_landscape\'s tree - an extension element, '
   'though FS_landscape is not known: FS-SITE-INV-001.', ['1.3.2'],
   sedit_(lambda d: PADS(d).update(X1=PADS(d).pop('GP1'))), [('FS-SITE-INV-001', ['X1'])])
SI('invariants', 'id-of-a-scene', 'A contour line keyed by SC1, the ID of a scene in FS_lighting\'s data, which an '
   'implementation of FS_site reads as data without knowing FS_lighting: FS-SITE-INV-001.', ['1.3.2'],
   sedit_(lambda d: (with_scene('SC1')(d), CONT(d).update(SC1=CONT(d).pop('CT2')))), [('FS-SITE-INV-001', ['SC1'])])
SI('invariants', 'id-of-a-dimension-string', 'A spot keyed by DM1, the ID of a dimension string in FS_annotation\'s '
   'data, read as data: FS-SITE-INV-001.', ['1.3.2'],
   sedit_(lambda d: (d['extensionsUsed'].update(FS_annotation='0.1.0'),
                     d['extensions'].update(FS_annotation={'dimensions': {'DM1': {'level': 'L1', 'direction': [1, 0], 'through': [0, 0],
                                                                                    'anchors': [{'junction': 'J1'}, {'junction': 'J6'}]}}}),
                     SPOTS(d).update(DM1=SPOTS(d).pop('SP5')))),
   [('FS-SITE-INV-001', ['DM1'])])
SI('invariants', 'id-of-two-records', 'A spot and a pad both keyed GP1: the ID is reported once.', ['1.3.2'],
   sedit_(lambda d: SPOTS(d).update(GP1=SPOTS(d).pop('SP5'))), [('FS-SITE-INV-001', ['GP1'])])
SI('invariants', 'survey-points-disagree', 'A spot at the 813\' contour line\'s middle vertex, (0, -6\'), at 813\' 6": '
   'two elevations at one position, FS-SITE-INV-002, naming the contour line and the spot.', ['3.1.2'],
   sedit_(lambda d: SPOTS(d).update(SP6={'at': F(0, -6), 'elevation': -FT})), [('FS-SITE-INV-002', ['CT1', 'SP6'])])
SI('invariants', 'two-spots-disagree', 'Two spots at the Kitchen\'s spot\'s position, one at its elevation and one 1" '
   'higher: one diagnostic for the position, naming all three.', ['3.1.2'],
   sedit_(lambda d: SPOTS(d).update(SP6={'at': F(5, 6), 'elevation': -FT // 2}, SP7={'at': F(5, 6), 'elevation': -FT // 2 + IN})),
   [('FS-SITE-INV-002', ['SP5', 'SP6', 'SP7'])])
SI('invariants', 'survey-points-agree', 'A spot at the 813\' contour line\'s middle vertex at 813\', its elevation: valid, '
   'and one point of the surface - still eleven.', ['3.1.2', '7.1.1'],
   sedit_(lambda d: SPOTS(d).update(SP6={'at': F(0, -6), 'elevation': -3 * FT // 2})),
   check=lambda r: ensure(len(SITE_DER(r)['surface']['points']) == 11, SITE_DER(r)['surface']))
SI('invariants', 'contours-cross-at-one-elevation', 'A second contour line at 813\' crossing the first at its middle '
   'vertex: one elevation at the shared position, valid.', ['3.1.2'],
   sedit_(lambda d: CONT(d).update(CT3={'elevation': -3 * FT // 2, 'points': [F(-2, -10), F(0, -6), F(2, -2)]})))
SI('invariants', 'contour-repeated-point', 'A contour line with a point written twice in a row: FS-SITE-INV-003.',
   ['3.1.1'], sedit_(INV_SI), INV_SI_DIAG)
SI('invariants', 'closed-contour', 'A closed contour line - a knoll at 816\' - that repeats its first point last: its '
   'consecutive points differ, so it is valid; its first and last vertex are one survey point.', ['3.1.1', '3.1.2', '7.1.1'],
   sedit_(lambda d: CONT(d).update(CT3={'elevation': 3 * FT // 2, 'points': [F(-20, 22), F(-14, 22), F(-14, 26), F(-20, 26), F(-20, 22)]})),
   check=lambda r: ensure(len(SITE_DER(r)['surface']['points']) == 15, len(SITE_DER(r)['surface']['points'])))
SI('invariants', 'pad-not-simple', 'A pad whose outline crosses itself, a bow tie: FS-SITE-INV-004.', ['4.1.1'],
   sedit_(lambda d: PADS(d)['GP1'].update(boundary=[F(-1, -1), F(29, 13), F(29, -1), F(-1, 13)])),
   [('FS-SITE-INV-004', ['GP1'])])
SI('invariants', 'pad-without-area', 'A pad whose three points are on one line: FS-SITE-INV-004.', ['4.1.1'],
   sedit_(lambda d: PADS(d)['GP1'].update(boundary=[F(-1, -1), F(14, -1), F(29, -1)])), [('FS-SITE-INV-004', ['GP1'])])
SI('invariants', 'setbacks-without-a-lot', 'Setbacks in a document with no site: FS-SITE-INV-005.', ['2.2.1'],
   sedit_(lambda d: d.pop('site')), [('FS-SITE-INV-005', [])])
SI('invariants', 'setbacks-on-a-site-without-a-boundary', 'Setbacks on a site that has a true north and no boundary: '
   'FS-SITE-INV-005.', ['2.2.1'], sedit_(lambda d: d.update(site={'trueNorth': 12000000})), [('FS-SITE-INV-005', [])])
SI('invariants', 'street-edge-of-nothing', 'Edge 4 on the street, on a lot of four edges, 0 to 3: FS-SITE-INV-005.',
   ['2.2.1'], sedit_(lambda d: SD_(d)['setbacks'].update(street=[0, 4])), [('FS-SITE-INV-005', [])])
SI('invariants', 'street-edge-of-the-last', 'Edge 3, the last, from the north-west corner back to the first vertex: valid, '
   'and the lot\'s west edge is its front.', ['2.2.1', '7.1.1'], sedit_(lambda d: SD_(d)['setbacks'].update(street=[3])),
   check=lambda r: ensure([e['kind'] for e in SITE_DER(r)['lot']['edges']] == ['side', 'rear', 'side', 'front'], SITE_DER(r)['lot']))
SI('invariants', 'no-judgement-of-grading', 'A pad 6\' below the floor and a patio 4\' above the ground under it - a '
   'basement no one excavated and a terrace on stilts: valid, with nothing derived that says otherwise. FS_site '
   'measures, it never judges (4.2).', ['4.1.1', '4.2.1'],
   sedit_(lambda d: (PADS(d)['GP1'].update(elevation=-6 * FT), d['slabs']['S1'].update(offset=4 * FT))))

SI('lints', 'lot-beyond-the-surface', 'The south-west corner\'s spot removed: the lot\'s corner is outside the surface\'s '
   'hull, FS-SITE-LINT-001 (info), and nothing graded is.', ['1.2.3'],
   sedit_(lambda d: SPOTS(d).pop('SP4')), [('FS-SITE-LINT-001', [])])
SI('lints', 'pad-beyond-the-surface', 'Every spot north of the house removed and the contour line at 815\' too: the '
   'surface stops at the 813\' line and the Kitchen\'s spot, and the house\'s pad runs off it - FS-SITE-LINT-002 for '
   'the pad, and FS-SITE-LINT-001 for the lot.', ['1.2.3'],
   sedit_(lambda d: (SPOTS(d).pop('SP1'), SPOTS(d).pop('SP2'), CONT(d).pop('CT2'))),
   [('FS-SITE-LINT-001', []), ('FS-SITE-LINT-002', ['GP1'])])
SI('lints', 'slab-beyond-the-surface', 'A survey of the house\'s ground alone, from 2\' south of it: the patio, further '
   'south, runs off it - FS-SITE-LINT-002 for the slab - and so does the lot.', ['1.2.3'],
   sedit_(lambda d: (SPOTS(d).pop('SP3'), SPOTS(d).pop('SP4'), CONT(d).pop('CT1'),
                     SPOTS(d).update(SP6={'at': F(-30, -2), 'elevation': -FT}, SP7={'at': F(40, -2), 'elevation': -FT}))),
   [('FS-SITE-LINT-001', []), ('FS-SITE-LINT-002', ['S1'])])
SI('lints', 'house-in-the-rear-setback', 'A rear setback of 20\': the north wall\'s junctions, 18\' from the rear lot '
   'line, and the pad, 17\' from it, are in it - FS-SITE-LINT-003 (info) for each, once.', ['1.2.3', '2.3.1'],
   sedit_(lambda d: SD_(d)['setbacks'].update(rear=20 * FT)),
   [('FS-SITE-LINT-003', [j]) for j in ('GP1', 'J2', 'J3', 'J4', 'J9')])
SI('lints', 'at-the-setback-is-clear', 'A front setback of exactly 30\', the distance from the street to the patio\'s south '
   'edge: it is clear - at least the setback, exactly.', ['1.2.3', '2.3.1'],
   sedit_(lambda d: SD_(d)['setbacks'].update(front=30 * FT)))
SI('lints', 'a-unit-inside-the-setback', 'A front setback of 30\' and one base unit: the patio is 1/1280 mm inside it, '
   'FS-SITE-LINT-003 for the slab.', ['1.2.3', '2.3.1'], sedit_(lambda d: SD_(d)['setbacks'].update(front=30 * FT + 1)),
   [('FS-SITE-LINT-003', ['S1'])])
SI('lints', 'patio-in-the-front-setback', 'The patio run 9\' further south, to 19\' south of the house: 21\' from the '
   'street, inside the 25\' front setback - FS-SITE-LINT-003 for the slab.', ['1.2.3', '2.3.1'],
   sedit_(lambda d: d['slabs']['S1'].update(boundary=[F(2, -19), F(12, -19), F(12, -1), F(2, -1)])),
   [('FS-SITE-LINT-003', ['S1'])])
SI('lints', 'drive-and-walk-cross-the-front-setback', 'A driveway and a front walk from the house to the street, across '
   'the 25\' front setback: a walkway or a driveway reaches the street by design, so neither is tested (2.3) - nothing '
   'is reported.', ['1.2.3', '2.3.1'],
   sedit_(lambda d: d['slabs'].update(
       S2={'level': 'L1', 'boundary': [F(14, -40), F(24, -40), F(24, -2), F(14, -2)], 'thickness': 100 * MM, 'purpose': 'driveway'},
       S3={'level': 'L1', 'boundary': [F(6, -40), F(9, -40), F(9, -2), F(6, -2)], 'thickness': 100 * MM, 'purpose': 'walkway'})))
SI('lints', 'outside-the-lot', 'Setbacks of 0, and a shed\'s pad over the east lot line: a point outside the lot is never '
   'clear, whatever the setbacks - FS-SITE-LINT-003 for the pad.', ['1.2.3', '2.3.1'],
   sedit_(lambda d: (SD_(d)['setbacks'].update(front=0, side=0, rear=0),
                     PADS(d).update(GP2={'name': 'Shed', 'elevation': 0, 'boundary': [F(36, 20), F(42, 20), F(42, 26), F(36, 26)]}))),
   [('FS-SITE-LINT-002', ['GP2']), ('FS-SITE-LINT-003', ['GP2'])])
SI('lints', 'on-the-lot-line', 'Setbacks of 0, and a shed\'s pad against the east lot line: a point on the lot line is '
   'clear.', ['1.2.3', '2.3.1'],
   sedit_(lambda d: (SD_(d)['setbacks'].update(front=0, side=0, rear=0),
                     PADS(d).update(GP2={'name': 'Shed', 'elevation': 0, 'boundary': [F(34, 20), F(40, 20), F(40, 26), F(34, 26)]}))))


def notched_lot(d):
    """The lot with its north-east corner notched: 10' x 10' out of it, a lot of six edges - south (the street), east,
    the notch's south and west sides, north, west."""
    d['site']['boundary'] = [F(-30, -40), F(40, -40), F(40, 20), F(30, 20), F(30, 30), F(-30, 30)]
    SD_(d)['setbacks']['side'] = 5 * FT


SI('lints', 'near-the-end-of-an-edge', 'The lot notched at its north-east corner (six edges; the notch\'s two are rear '
   'edges), a rear setback of 7\' and a shed\'s pad near the notch\'s inner corner, (30\', 20\'): the shed\'s corner '
   '(26\', 16\') is beyond the ends of both of the notch\'s edges, so its distance to them is to that corner, sqrt(32) '
   'feet - FS-SITE-LINT-003 for the shed\'s pad.', ['1.2.3', '2.3.1'],
   sedit_(lambda d: (notched_lot(d), SD_(d)['setbacks'].update(rear=7 * FT),
                     PADS(d).update(GP2={'name': 'Shed', 'elevation': 0, 'boundary': [F(20, 10), F(26, 10), F(26, 16), F(20, 16)]}))),
   [('FS-SITE-LINT-003', ['GP2'])])
SI('lints', 'beyond-the-end-of-an-edge-is-clear', 'The same notched lot and setback, the shed further west: its corner '
   '(10\', 19\') is 1\' from the line of the notch\'s south edge, but beyond its end - 20\' from the edge itself - so '
   'it is clear (2.3): the distance is to the edge, not to its line.', ['1.2.3', '2.3.1'],
   sedit_(lambda d: (notched_lot(d), SD_(d)['setbacks'].update(rear=7 * FT),
                     PADS(d).update(GP2={'name': 'Shed', 'elevation': 0, 'boundary': [F(4, 15), F(10, 15), F(10, 19), F(4, 19)]}))))

PLANE_PAD = [F(0, -10), F(20, -10), F(20, 10), F(0, 10)]
L_PAD = [F(0, 0), F(20, 0), F(20, 10), F(10, 10), F(10, 20), F(0, 20)]
SI('derived', 'plane-hand-checked', 'Ground on one plane, rising 1\' for every 10\' north, and one pad 20\' wide from 10\' '
   'south to 10\' north of where the ground is at 0, graded to 0: the north half is cut by 1\' at its edge, the south '
   'half filled by as much - each 20\' x 10\' x 1\' / 2 = 100 cubic feet, exactly - and the ground under it runs from -1\' '
   'to 1\'. The lot\'s four corners are cocircular, so the surface is two triangles, fanned from the least corner.',
   ['3.2.1', '4.2.1', '7.1.1'], sedit_(lambda d: (plane_ground(d), only_pad(d, PLANE_PAD))),
   check=lambda r: ensure(SITE_DER(r)['grading'] == {'GP1': {'kind': 'pad', 'elevation': 0, 'low': -FT, 'high': FT,
                                                             'cut': str(100 * FT3), 'fill': str(100 * FT3)}}
                          and SITE_DER(r)['surface']['triangles'] == [[0, 2, 3], [0, 3, 1]]
                          and SITE_DER(r)['cut'] == str(100 * FT3), SITE_DER(r)))
SI('derived', 'l-shaped-pad', 'The same plane and an L-shaped pad at 0, north of the zero line - 20\' x 10\' and 10\' x 10\' '
   'above it - all cut: 20 x 10 x 0.5\' + 10 x 10 x 1.5\' = 250 cubic feet, nothing filled. The clipping keeps every point '
   'of the outline, which is not convex.', ['4.2.1', '7.1.1'], sedit_(lambda d: (plane_ground(d), only_pad(d, L_PAD))),
   check=lambda r: ensure(SITE_DER(r)['grading']['GP1'] == {'kind': 'pad', 'elevation': 0, 'low': 0, 'high': 2 * FT,
                                                            'cut': str(250 * FT3), 'fill': '0'}, SITE_DER(r)['grading']))
SI('derived', 'clockwise-pad', 'The L-shaped pad written clockwise: the same volumes - an outline is measured whichever way '
   'round it runs.', ['4.2.1', '7.1.1'], sedit_(lambda d: (plane_ground(d), only_pad(d, L_PAD[::-1]))),
   check=lambda r: ensure(SITE_DER(r)['grading']['GP1']['cut'] == str(250 * FT3), SITE_DER(r)['grading']))
SI('derived', 'pad-above-the-ground', 'The plane and the square pad raised to 2\', above the ground everywhere under it: '
   'all fill, 20\' x 20\' x 2\' = 800 cubic feet.', ['4.2.1', '7.1.1'],
   sedit_(lambda d: (plane_ground(d), only_pad(d, PLANE_PAD, 2 * FT))),
   check=lambda r: ensure(SITE_DER(r)['grading']['GP1'] == {'kind': 'pad', 'elevation': 2 * FT, 'low': -FT, 'high': FT,
                                                            'cut': '0', 'fill': str(800 * FT3)}, SITE_DER(r)['grading']))
SI('derived', 'a-volume-rounded-once', 'The plane and a pad one base unit square at 0, just north of the zero line: it '
   'cuts 1/20 of a cubic unit, which rounds to 0, and the ground under it rises to 1/10 of a unit, which rounds to 0 '
   'too.', ['4.2.1', '7.1.1'],
   sedit_(lambda d: (plane_ground(d), only_pad(d, [[0, 0], [1, 0], [1, 1], [0, 1]]))),
   check=lambda r: ensure(SITE_DER(r)['grading']['GP1'] == {'kind': 'pad', 'elevation': 0, 'low': 0, 'high': 0,
                                                            'cut': '0', 'fill': '0'}, SITE_DER(r)['grading']))
SI('derived', 'totals-rounded-once', 'The plane and three pads at 0, each one base unit wide and three long, running '
   'north from the zero line: each cuts 9/20 of a cubic unit, rounded to 0; the three together cut 27/20, rounded once '
   'to 1. The total is not the sum of the rounded volumes.', ['4.2.1', '7.1.1'],
   sedit_(lambda d: (plane_ground(d), only_pad(d, [[0, 0], [1, 0], [1, 3], [0, 3]]),
                     PADS(d).update(GP2={'boundary': [[10, 0], [11, 0], [11, 3], [10, 3]], 'elevation': 0},
                                    GP3={'boundary': [[20, 0], [21, 0], [21, 3], [20, 3]], 'elevation': 0}))),
   check=lambda r: ensure([SITE_DER(r)['grading'][g]['cut'] for g in ('GP1', 'GP2', 'GP3')] == ['0', '0', '0']
                          and SITE_DER(r)['cut'] == '1', SITE_DER(r)))
SI('derived', 'pad-partly-beyond-the-surface', 'The plane, its survey cut back to the north half of the lot - from the '
   'zero line - and the square pad across it: only its north half is over the surface, so only it is measured, 100 '
   'cubic feet cut and nothing filled; FS-SITE-LINT-002 says so, and the lot is beyond the surface too.',
   ['1.2.3', '4.2.1', '7.1.1'],
   sedit_(lambda d: (plane_ground(d), only_pad(d, PLANE_PAD),
                     SPOTS(d).update(SP1={'at': F(-30, 0), 'elevation': 0}, SP2={'at': F(40, 0), 'elevation': 0}))),
   [('FS-SITE-LINT-001', []), ('FS-SITE-LINT-002', ['GP1'])],
   check=lambda r: ensure(SITE_DER(r)['grading']['GP1'] == {'kind': 'pad', 'elevation': 0, 'low': 0, 'high': FT,
                                                            'cut': str(100 * FT3), 'fill': '0'}, SITE_DER(r)['grading']))
SI('derived', 'pad-off-the-surface', 'A shed\'s pad wholly beyond the survey, which covers the lot\'s north half: it has '
   'no point over the surface - no low, no high, and nothing cut or filled.', ['1.2.3', '4.2.1', '7.1.1'],
   sedit_(lambda d: (plane_ground(d), only_pad(d, [F(0, -14), F(10, -14), F(10, -4), F(0, -4)]),
                     SPOTS(d).update(SP1={'at': F(-30, 0), 'elevation': 0}, SP2={'at': F(40, 0), 'elevation': 0}))),
   [('FS-SITE-LINT-001', []), ('FS-SITE-LINT-002', ['GP1'])],
   check=lambda r: ensure(SITE_DER(r)['grading']['GP1'] == {'kind': 'pad', 'elevation': 0, 'low': None, 'high': None,
                                                            'cut': '0', 'fill': '0'}, SITE_DER(r)['grading']))
SI('derived', 'stepped-patio', 'The patio in three steps down the slope, each a patio slab 6" below the one before, 3\' '
   'deep: each grades the ground under it to its own bottom, and each is measured.', ['4.1.1', '4.2.1', '7.1.1'],
   sedit_(lambda d: d['slabs'].update(
       S1={'level': 'L1', 'boundary': [F(2, -4), F(12, -4), F(12, -1), F(2, -1)], 'thickness': 100 * MM, 'offset': -6 * IN, 'purpose': 'patio'},
       S2={'level': 'L1', 'boundary': [F(2, -7), F(12, -7), F(12, -4), F(2, -4)], 'thickness': 100 * MM, 'offset': -12 * IN, 'purpose': 'patio'},
       S3={'level': 'L1', 'boundary': [F(2, -10), F(12, -10), F(12, -7), F(2, -7)], 'thickness': 100 * MM, 'offset': -18 * IN, 'purpose': 'patio'})),
   check=lambda r: ensure([SITE_DER(r)['grading'][s]['elevation'] for s in ('S1', 'S2', 'S3')]
                          == [-6 * IN - 100 * MM, -12 * IN - 100 * MM, -18 * IN - 100 * MM], SITE_DER(r)['grading']))
SI('derived', 'what-grades-the-ground', 'Five more slabs: a walkway, a driveway, a stoop and an equipment pad grade the '
   'ground; a deck, and a slab of no purpose, do not (4.1).', ['4.1.1', '7.1.1'],
   sedit_(lambda d: d['slabs'].update(
       {f'S{i}': {'level': 'L1', 'boundary': [F(-20 + 4 * i, -14), F(-18 + 4 * i, -14), F(-18 + 4 * i, -12), F(-20 + 4 * i, -12)],
                  'thickness': 100 * MM, **({'purpose': p} if p else {})}
        for i, p in enumerate(('walkway', 'driveway', 'stoop', 'equipmentPad', 'deck', None), start=2)})),
   check=lambda r: ensure(sorted(SITE_DER(r)['grading']) == ['GP1', 'S1', 'S2', 'S3', 'S4', 'S5'], sorted(SITE_DER(r)['grading'])))
SI('derived', 'garage-slab', 'A garage slab - the floor of a garage that is not a room\'s - grades the ground.',
   ['4.1.1', '7.1.1'],
   sedit_(lambda d: d['slabs'].update(S2={'level': 'L1', 'boundary': [F(-12, 0), F(-2, 0), F(-2, 12), F(-12, 12)],
                                          'thickness': 100 * MM, 'purpose': 'garage'})),
   check=lambda r: ensure(SITE_DER(r)['grading']['S2']['kind'] == 'slab', SITE_DER(r)['grading']))
SI('derived', 'cocircular-square', 'A survey of four spots at the corners of a square, all on one circle: the Delaunay '
   'face is the square, divided by the diagonal from its least vertex, the south-west corner - never the other '
   'diagonal.', ['3.2.1', '7.1.1'],
   sedit_(lambda d: (SD_(d).update(spots={'A': {'at': F(0, 0), 'elevation': 0}, 'B': {'at': F(10, 0), 'elevation': FT},
                                          'C': {'at': F(10, 10), 'elevation': 0}, 'D': {'at': F(0, 10), 'elevation': FT}},
                                   contours={}),
                     SD_(d).pop('setbacks'), d.pop('site'), only_pad(d, [F(2, 2), F(4, 2), F(4, 4), F(2, 4)]))),
   check=lambda r: ensure(SITE_DER(r)['surface'] == {'low': 0, 'high': FT, 'points': [F(0, 0) + [0], F(0, 10) + [FT], F(10, 0) + [FT], F(10, 10) + [0]],
                                                    'triangles': [[0, 2, 3], [0, 3, 1]]}, SITE_DER(r)['surface']))
EIGHT = [(5, 0), (4, 3), (3, 4), (0, 5), (-3, 4), (-4, 3), (-5, 0), (0, -5)]
SI('derived', 'eight-on-a-circle', 'Eight spots on one circle of radius 5\' and none inside: one Delaunay face of eight '
   'vertices, fanned from its least, (-5\', 0) - six triangles, each from it.', ['3.2.1', '7.1.1'],
   sedit_(lambda d: (SD_(d).update(spots={f'E{i}': {'at': F(x, y), 'elevation': i * IN} for i, (x, y) in enumerate(EIGHT)},
                                   contours={}),
                     SD_(d).pop('setbacks'), d.pop('site'), only_pad(d, [F(-1, -1), F(1, -1), F(1, 1), F(-1, 1)]))),
   check=lambda r: ensure(all(t[0] == 0 for t in SITE_DER(r)['surface']['triangles']) and len(SITE_DER(r)['surface']['triangles']) == 6
                          and SITE_DER(r)['surface']['points'][0] == F(-5, 0) + [6 * IN], SITE_DER(r)['surface']))
SI('derived', 'collinear-survey', 'Three spots on one line: no surface, and nothing measured - every graded outline\'s '
   'low, high, cut and fill null, and so are the totals.', ['3.2.1', '7.1.1'],
   sedit_(lambda d: SD_(d).update(spots={'A': {'at': F(-30, -40), 'elevation': 0}, 'B': {'at': F(5, -5), 'elevation': FT},
                                         'C': {'at': F(40, 30), 'elevation': 2 * FT}}, contours={})),
   check=lambda r: ensure(SITE_DER(r)['surface'] is None and SITE_DER(r)['cut'] is None
                          and SITE_DER(r)['grading']['GP1']['cut'] is None, SITE_DER(r)))
SI('derived', 'a-contour-line-alone', 'A survey of one contour line along the street, its three points on one line, and '
   'one spot at the back of the lot: a surface of two triangles, the line\'s middle point a vertex of both - and the '
   'lot\'s back corners and the house\'s pad beyond it.', ['3.2.1', '7.1.1'],
   sedit_(lambda d: SD_(d).update(spots={'A': {'at': F(0, 30), 'elevation': FT}},
                                  contours={'C': {'elevation': 0, 'points': [F(-30, -40), F(0, -40), F(40, -40)]}})),
   [('FS-SITE-LINT-001', []), ('FS-SITE-LINT-002', ['GP1'])],
   check=lambda r: ensure(SITE_DER(r)['surface']['triangles'] == [[0, 1, 2], [1, 3, 2]], SITE_DER(r)['surface']))
SI('derived', 'oblique-lot', 'A lot of five edges, its street edge 0 along the south and its north-east side oblique: edges '
   '1 and 4, which meet the street edge, are its sides, and 2 and 3 its rear; the oblique edge is 50\' long (a 30-40-50 '
   'triangle) and the others as written. Its rear setback, drawn from the oblique edge, reaches the house\'s north-east '
   'corner - FS-SITE-LINT-003 for three junctions and the pad - and the lot runs beyond the survey.', ['2.2.1', '7.1.1'],
   sedit_(lambda d: d['site'].update(boundary=[F(-30, -40), F(40, -40), F(40, 0), F(10, 40), F(-30, 40)])),
   [('FS-SITE-LINT-001', [])] + [('FS-SITE-LINT-003', [x]) for x in ('GP1', 'J10', 'J4', 'J9')],
   check=lambda r: ensure(SITE_DER(r)['lot']['edges'] == [{'kind': 'front', 'length': 70 * FT, 'setback': 25 * FT},
                                                          {'kind': 'side', 'length': 40 * FT, 'setback': 5 * FT},
                                                          {'kind': 'rear', 'length': 50 * FT, 'setback': 10 * FT},
                                                          {'kind': 'rear', 'length': 40 * FT, 'setback': 10 * FT},
                                                          {'kind': 'side', 'length': 80 * FT, 'setback': 5 * FT}]
                          and SITE_DER(r)['lot']['area'] == str((70 * 80 - 30 * 40 // 2) * FT * FT), SITE_DER(r)['lot']))
SI('derived', 'corner-lot', 'A corner lot, its south and east edges both on streets, with a front setback of 10\': both '
   'are front edges, the two that meet them sides, and none is a rear.', ['2.2.1', '7.1.1'],
   sedit_(lambda d: SD_(d)['setbacks'].update(street=[0, 1], front=10 * FT)),
   check=lambda r: ensure([e['kind'] for e in SITE_DER(r)['lot']['edges']] == ['front', 'front', 'side', 'side'], SITE_DER(r)['lot']))
SI('derived', 'irrational-edge', 'The lot\'s north-east corner moved 1\' north, beyond the survey: its east edge is 71\' '
   'and its north edge sqrt(70^2 + 1^2) feet, rounded once.', ['7.1.1'],
   sedit_(lambda d: d['site']['boundary'].__setitem__(2, F(40, 31))), [('FS-SITE-LINT-001', [])],
   check=lambda r: ensure(SITE_DER(r)['lot']['edges'][1]['length'] == 71 * FT
                          and SITE_DER(r)['lot']['edges'][2]['length'] == land._round_sqrt(70 * 70 * FT * FT + FT * FT),
                          SITE_DER(r)['lot']['edges']))
SI('derived', 'setbacks-partly-given', 'Setbacks giving the front alone: the side and rear edges have no setback.',
   ['2.2.1', '7.1.1'], sedit_(lambda d: SD_(d).update(setbacks={'street': [0], 'front': 25 * FT})),
   check=lambda r: ensure([e['setback'] for e in SITE_DER(r)['lot']['edges']] == [25 * FT, None, None, None], SITE_DER(r)['lot']))


def site_options(d):
    """Core 0.3 design options for the patio: option A (OP1, the primary) keeps S1; option B (OP2) has a larger patio
    S2 in its place, 2' to 16' east."""
    d['optionSets'] = {'OS1': {'primary': 'OP1', 'name': 'Patio'}}
    d['options'] = {'OP1': {'set': 'OS1', 'name': 'A'}, 'OP2': {'set': 'OS1', 'name': 'B'}}
    d['slabs']['S1']['option'] = 'OP1'
    d['slabs']['S2'] = {'level': 'L1', 'boundary': [F(2, -10), F(16, -10), F(16, -1), F(2, -1)], 'thickness': 100 * MM,
                        'offset': -6 * IN, 'purpose': 'patio', 'option': 'OP2'}


SI('options', 'patio-of-one-option', 'Patio options A and B as Core 0.3 design options (Core 19): FS_site is evaluated in '
   'each checked design and reports nothing, and the primary design grades A\'s patio.', ['1.2.1', '1.2.4', '7.1.1'],
   sedit_(site_options), check=lambda r: ensure(sorted(SITE_DER(r)['grading']) == ['GP1', 'S1'], SITE_DER(r)['grading']))
SI('options', 'derived-for-a-design', 'The same options, the derived values asked for B\'s design (Core 19.6): B\'s larger '
   'patio is the one graded.', ['1.2.4', '7.1.1', 'FS-CORE-19.6.1'], sedit_(site_options), design={'OS1': 'OP2'},
   check=lambda r: ensure(sorted(SITE_DER(r)['grading']) == ['GP1', 'S2'], SITE_DER(r)['grading']))
SI('options', 'patio-of-one-option-in-a-setback', 'The same options with a front setback of 31\': each design\'s patio is '
   '30\' from the street, inside it - A\'s in the primary design, and B\'s reported with `design` (Core 19.5.2).',
   ['1.2.3', '2.3.1', 'FS-CORE-19.3.1'],
   sedit_(lambda d: (site_options(d), SD_(d)['setbacks'].update(front=31 * FT))),
   [('FS-SITE-LINT-003', ['S1']), ('FS-SITE-LINT-003', ['S2'], 'OP2')])


def site_derived(d):
    data = json.dumps(d).encode('utf-8')
    result, _, _ = check(data, ext_reader(data), json.dumps([entry(SITE)]).encode('utf-8'), official.implemented(SITE))
    assert result['valid'], result['diagnostics']
    return result['derived']['extensions'][SITE]


SO_ = lambda *a, **k: O(SITE, *a, **k)    # noqa: E731
SO_('add-a-spot', 'setProperty of $document /extensions/FS_site/spots/SP6 adds a spot at the top of the bank, with an ID '
    'Ops does not mint (1.3.2). It commits, valid under FS_site, and the surface has twelve points.',
    ['1.2.1', '1.3.2', '3.1.2', '7.1.1', 'FS-OPS-2.3.1'], site_house(),
    {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_site/spots/SP6',
                'value': {'at': F(-10, 24), 'elevation': 2 * FT, 'name': 'Top of bank'}}]},
    check=lambda r, B: ensure(len(site_derived(B)['surface']['points']) == 12, site_derived(B)['surface']))
SO_('first-spot-creates-the-data', 'The garden declaring FS_site with no data of it yet: setProperty of $document '
    '/extensions/FS_site/spots/SP1 creates FS_site\'s data, and its `spots`, on the way (Ops 2.3). It commits, valid, with '
    'no surface yet.', ['1.2.1', '1.3.1', '7.1.1', 'FS-OPS-2.3.1'], sedit_(lambda d: d['extensions'].pop(SITE)),
    {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_site/spots/SP1', 'value': SITE_DATA['spots']['SP1']}]},
    check=lambda r, B: ensure(B['extensions'][SITE] == {'spots': {'SP1': SITE_DATA['spots']['SP1']}}
                              and site_derived(B)['surface'] is None, B['extensions'].get(SITE)))
SO_('set-the-setbacks', 'setProperty of $document /extensions/FS_site/setbacks: a side setback of 10\'. It commits, and '
    'the side edges derive it.', ['2.2.1', '7.1.1', 'FS-OPS-2.3.1'], site_house(),
    {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_site/setbacks/side', 'value': 10 * FT}]},
    check=lambda r, B: ensure([e['setback'] for e in site_derived(B)['lot']['edges']] == [25 * FT, 10 * FT, 10 * FT, 10 * FT],
                              site_derived(B)['lot']))
SO_('move-a-lot-corner', 'setProperty of $site /boundary moves the lot\'s north-east corner 10\' east: a Core edit of the '
    'site, which FS_site\'s lot follows - its area and its east and north edges change. It commits.',
    ['2.2.1', '7.1.1', 'FS-OPS-2.3.1'], site_house(),
    {'batch': [{'op': 'setProperty', 'id': '$site', 'path': '/boundary', 'value': [F(-30, -40), F(40, -40), F(50, 30), F(-30, 30)]}]},
    check=lambda r, B: ensure(site_derived(B)['lot']['area'] == str((70 * 75) * FT * FT)
                              and site_derived(B)['lot']['edges'][2]['length'] == 80 * FT, site_derived(B)['lot']))
SO_('lower-the-patio', 'setProperty of S1 /offset lowers the patio another 6": it grades the ground to its new bottom, and '
    'fills less. It commits.', ['4.1.1', '4.2.1', '7.1.1', 'FS-OPS-2.3.1'], site_house(),
    {'batch': [{'op': 'setProperty', 'id': 'S1', 'path': '/offset', 'value': -12 * IN}]},
    check=lambda r, B: ensure(site_derived(B)['grading']['S1']['elevation'] == -12 * IN - 100 * MM
                              and int(site_derived(B)['grading']['S1']['fill']) < int(site_derived(site_house())['grading']['S1']['fill']),
                              site_derived(B)['grading']['S1']))
SO_('remove-a-pad', 'unsetProperty of $document /extensions/FS_site/pads/GP1 removes the house\'s pad. It commits, and '
    'only the patio is graded.', ['1.2.1', '7.1.1', 'FS-OPS-2.3.1'], site_house(),
    {'batch': [{'op': 'unsetProperty', 'id': '$document', 'path': '/extensions/FS_site/pads/GP1'}]},
    check=lambda r, B: ensure(list(site_derived(B)['grading']) == ['S1'], site_derived(B)['grading']))
SO_('remove-the-patio', 'removeElement S1: the slab goes, and with it what it graded. It commits.', ['1.2.1', '7.1.1'],
    site_house(), {'batch': [{'op': 'removeElement', 'id': 'S1'}]},
    check=lambda r, B: ensure(list(site_derived(B)['grading']) == ['GP1'], site_derived(B)['grading']))
SO_('conflicting-spot-is-rejected', 'setProperty of $document /extensions/FS_site/spots/SP6 at the 815\' contour line\'s '
    'middle vertex, 1\' higher than it: the result breaks 3.1.2, and an applier that implements FS_site and knows it '
    'rejects the batch (Ops 1.2.3).', ['3.1.2', '1.2.1', 'FS-OPS-1.2.3'], site_house(),
    {'batch': [{'op': 'setProperty', 'id': '$document', 'path': '/extensions/FS_site/spots/SP6',
                'value': {'at': F(10, 18), 'elevation': 3 * FT // 2}}]},
    'rejected', [('FS-SITE-INV-002', ['CT2', 'SP6'])])
SO_('setbacks-on-a-removed-lot-are-rejected', 'unsetProperty of $document /site removes the site, and its lot, while '
    'setbacks remain: the result breaks 2.2.1, and the batch is rejected.', ['2.2.1', '1.2.1', 'FS-OPS-1.2.3'], site_house(),
    {'batch': [{'op': 'unsetProperty', 'id': '$document', 'path': '/site'}]}, 'rejected', [('FS-SITE-INV-005', [])])


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
        for name in ALL + (STRC, LAND, LGHT, VIEW, RENO, ANNO, SITE):
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

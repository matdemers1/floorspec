"""The conformance suite of Floorspec Core 0.1, as the script that writes it.

    python3.13 -m tools.oracle.author            rewrite every test from its declaration below
    python3.13 -m tools.oracle.author --prune    ...and delete test directories no longer declared

Every expected diagnostic is written by hand here and cross-checked against the oracle; geometry,
hashes and canonical forms come from the oracle. Afterwards, `python3.13 -m tools.oracle.regenerate`
re-verifies the suite from the files alone.
"""
import copy
import json
import sys

from tools.oracle.author_lib import *  # noqa: F401,F403

X, Y = 4000 * MM, 3000 * MM            # the standard room: 4 m x 3 m
CX, CY = X // 2, Y // 2


def room_doc(**extra):
    js, ws = box('', 0, 0, X, Y)
    d = level_doc(junctions=js, walls=ws, rooms={'R1': R(CX, CY)})
    for k, v in extra.items():
        d[k] = {**d.get(k, {}), **v} if isinstance(v, dict) else v
    return d


def baseline():
    """One 4 m x 3 m room with an empty opening: the model several tests vary."""
    d = room_doc()
    d['openings'] = {'O1': {'wall': 'W4', 'offset': 1000 * MM, 'width': 900 * MM, 'height': 2100 * MM}}
    return d


def drop(d, path):
    d = copy.deepcopy(d)
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    del cur[path[-1]]
    return d


def setp(d, path, v):
    d = copy.deepcopy(d)
    cur = d
    for k in path[:-1]:
        cur = cur.setdefault(k, {})
    cur[path[-1]] = v
    return d


SCH = [('FS-SCH-001', [])]


def no_wt(d):
    del d['types']['WT']
    if not d['types']:
        del d['types']
    return d

# =================================================================================== model
t('model', 'minimal-document', 'The smallest valid document: a version and a named project. Every collection is '
  'absent and so empty; nothing is derived.', ['1.1.1', '1.2.1', '9.2.1', '9.3.1', '10.1.1'], doc())
t('model', 'root-not-an-object', 'A JSON array is well-formed JSON but not a document: FS-SCH-001.',
  ['1.1.1', '10.2.1'], None, SCH, raw=b'[\n  "floorspec",\n  "0.1"\n]\n')
t('model', 'root-is-a-string', 'A JSON string is not a document either; it has no floorspec member to name a version, '
  'so it fails the schema, not the version check.', ['1.1.1'], None, SCH, raw=b'"0.1"\n')
t('model', 'reserved-top-level-member', 'A top-level member the table does not list - here "roofs", reserved for a '
  'later draft (0.5) - makes the document invalid.', ['1.1.2'], doc(roofs={}), SCH)
t('model', 'unknown-top-level-member', 'New data enters through extensions or extras, never a new top-level member.',
  ['1.1.2'], doc(furniture={'F1': {'kind': 'sofa'}}), SCH)
t('model', 'missing-version', 'A document without "floorspec" does not declare the draft it targets.',
  ['1.2.1'], drop(doc(), ['floorspec']), SCH)
t('model', 'version-is-a-number', '"floorspec": 0.1 is a number, not the string "0.1". FS-DOC-001 applies only to a '
  'string naming another version, so this is a schema error.', ['1.2.1'], doc(floorspec=0.1), SCH)
t('model', 'version-with-patch', '"0.1.0" is not "0.1": patch releases are not declared. A reader that implements '
  'only 0.1 rejects it with FS-DOC-001.', ['1.2.1', '1.2.2'], doc(floorspec='0.1.0'), [('FS-DOC-001', [])])
t('model', 'unknown-version', 'A reader that implements 0.1 rejects a document declaring 0.2 with FS-DOC-001, '
  'whatever else the document contains.', ['1.2.2', '10.2.1'], doc(floorspec='0.2'), [('FS-DOC-001', [])])
t('model', 'level-without-building', 'Every level references a building.', ['1.3.1'],
  drop(room_doc(), ['levels', 'L1', 'building']), SCH)
t('model', 'wall-without-level', 'Every wall references a level.', ['1.3.2'], drop(room_doc(), ['walls', 'W1', 'level']), SCH)
t('model', 'room-without-level', 'Every room references a level.', ['1.3.2'], drop(room_doc(), ['rooms', 'R1', 'level']), SCH)
t('model', 'junction-without-level', 'Every junction references a level.', ['1.3.2'],
  drop(room_doc(), ['junctions', 'J3', 'level']), SCH)
t('model', 'level-building-null', 'A level\'s building is a reference: null is not one.', ['1.3.1', '3.2.3'],
  setp(room_doc(), ['levels', 'L1', 'building'], None), SCH)
t('model', 'unknown-element-member', 'A wall with a "thickness" member - thickness comes from layers - has a member '
  'its kind\'s table does not list.', ['1.4.1'], setp(room_doc(), ['walls', 'W1', 'thickness'], T100), SCH)
t('model', 'element-id-member', 'An element does not repeat its ID inside itself: an "id" member is unknown.',
  ['1.4.1'], setp(room_doc(), ['rooms', 'R1', 'id'], 'R1'), SCH)
t('model', 'member-of-another-kind', 'A separator may not carry a wall\'s "type" member.', ['1.4.1'],
  level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0)}, separators={'S1': {**S('J1', 'J2'), 'type': 'WT'}}), SCH)

b = baseline()
explicit = copy.deepcopy(b)
for w in explicit['walls'].values():
    w['justification'] = 'center'
    w['base'] = {'offset': 0}
    w['extensions'] = {}
    w['extras'] = {}
for j in explicit['junctions'].values():
    j['join'] = {'kind': 'mitre'}
explicit['rooms']['R1']['function'] = 'unspecified'
explicit['openings']['O1'].update(hinge='start', swing='right')
explicit.update(separators={}, slabs={}, materials={}, assets={}, extensionsUsed={}, extensionsRequired=[],
                extensions={}, extras={})
t('model', 'defaults-omitted', 'The baseline model: one 4 m by 3 m room of 100 mm centred walls with an empty '
  'opening, every defaulted member absent. model/018 states the same model with every default written out; a reader '
  'treats them identically, so both derive the same values and have the same hash.',
  ['1.5.1', '5.6.1', '5.7.1', '5.9.3', '6.2.1', '6.4.1', '7.4.1', '9.3.1'], b)
t('model', 'defaults-explicit', 'model/017 with every constant default written out - "center", base offset 0, the '
  'mitre join, "unspecified", hinge and swing, and every empty collection and object. Its derived values and hash are '
  'exactly those of model/017, and its canonical form is byte-identical.',
  ['1.5.1', '9.2.1', '9.2.2', '9.3.1'], explicit)

t('model', 'extension-name-pattern', 'An extension name without a registered prefix ("acoustics") fails the schema.',
  ['1.6.1'], doc(extensionsUsed={'acoustics': '1.0'}), SCH)
t('model', 'extension-name-lowercase-prefix', '"Ext_acoustics": the prefix is case-sensitive.', ['1.6.1'],
  doc(extensionsUsed={'Ext_acoustics': '1.0'}), SCH)
t('model', 'element-extension-name-pattern', 'Extension data on an element is keyed by extension names too.',
  ['1.6.1'], setp(room_doc(), ['walls', 'W1', 'extensions'], {'acoustics': {'stc': 45}}), SCH)
t('model', 'required-extension-not-used',
  'extensionsRequired names EXT_acoustics, which extensionsUsed does not declare. FS-DOC-002 applies only when every '
  'required name is declared, so the document reaches the invariant tier and FS-INV-004 is reported.',
  ['1.6.2', '10.2.1'], doc(extensionsRequired=['EXT_acoustics']), [('FS-INV-004', [])])
t('model', 'required-extension-unimplemented', 'A required extension, properly declared, that the reader does not '
  'implement: rejected with FS-DOC-002. (The suite\'s readers implement no extension.)', ['1.6.4'],
  doc(extensionsUsed={'EXT_acoustics': '1.0'}, extensionsRequired=['EXT_acoustics']), [('FS-DOC-002', [])])
t('model', 'element-extension-data-undeclared', 'A wall carries EXT_acoustics data that extensionsUsed does not '
  'declare: FS-INV-005 naming the wall.', ['1.6.3', '10.2.1'],
  setp(room_doc(), ['walls', 'W1', 'extensions'], {'EXT_acoustics': {'stc': 45}}), [('FS-INV-005', ['W1'])])
t('model', 'top-level-extension-data-undeclared', 'Top-level extension data for an undeclared extension: FS-INV-005 '
  'with no element.', ['1.6.3'], doc(extensions={'EXT_acoustics': {'zones': []}}), [('FS-INV-005', [])])
ext = baseline()
ext['extensionsUsed'] = {'EXT_acoustics': '2.1'}
ext['extensions'] = {'EXT_acoustics': {'zones': [{'name': 'quiet', 'rooms': ['R1']}], 'override': {'W1': {'justification': 'exteriorFace'}}}}
ext['walls']['W1']['extensions'] = {'EXT_acoustics': {'stc': 52, 'layers': [{'thickness': 999999, 'function': 'core'}]}}
ext['rooms']['R1']['extensions'] = {'EXT_acoustics': {'anchor': [0, 0], 'rt60': 0.45}}
t('model', 'optional-extension-preserved', 'The baseline model (model/017) with an optional extension the reader '
  'does not implement: data at the top level, on a wall and on a room, some of it shaped like core members. The '
  'document is valid, derives exactly what model/017 derives, and its canonical form keeps the extension data.',
  ['1.6.5', '1.6.6', '9.2.1'], ext)
ex = baseline()
ex['extras'] = {'viewer': {'camera': [1, 2, 3], 'zoom': 1.25}}
ex['project']['extras'] = {'importedFrom': 'plan.dxf'}
ex['walls']['W1']['extras'] = {'justification': 'interiorFace', 'layers': [], 'colour': 'red'}
ex['junctions']['J1']['extras'] = {'position': [999, 999]}
ex['rooms']['R1']['extras'] = {'anchor': [-1, -1], 'note': None}
ex['openings']['O1']['extras'] = {'offset': 0, 'width': 1}
t('model', 'extras-do-not-affect-derivation', 'The baseline model (model/017) with extras on the document, the '
  'project, a wall, a junction, a room and an opening - including members named like core members. The derived values '
  'are exactly those of model/017, and every extra is kept in the canonical form.',
  ['1.7.1', '1.7.2', '9.2.1'], ex)
t('model', 'site-at-range-limits', 'A site at the edges of every range: trueNorth 180,000,000 (included), latitude '
  '-90,000,000 and longitude 180,000,000 (both included), with a clockwise boundary.',
  ['1.8.1', '1.8.2', '2.6.1'], doc(site={'trueNorth': 180_000_000, 'location': {'latitude': -90_000_000, 'longitude': 180_000_000},
                                         'boundary': [[0, 0], [0, 20000 * MM], [30000 * MM, 20000 * MM], [30000 * MM, 0]]}))
t('model', 'site-without-anything', 'An empty site is a site: the project has a site, so canonical form keeps '
  '"site": {} (its default is absent, not {}), while trueNorth 0 is omitted.', ['9.2.1', '1.5.1'],
  doc(site={'trueNorth': 0}))
t('model', 'true-north-lower-bound', 'trueNorth must be greater than -180,000,000: the bound itself is out.',
  ['1.8.1'], doc(site={'trueNorth': -180_000_000}), SCH)
t('model', 'true-north-above-range', 'trueNorth 180,000,001 is more than a half turn.', ['1.8.1'],
  doc(site={'trueNorth': 180_000_001}), SCH)
t('model', 'latitude-out-of-range', 'A latitude of 90,000,001 microdegrees is beyond the pole.', ['1.8.2'],
  doc(site={'location': {'latitude': 90_000_001, 'longitude': 0}}), SCH)
t('model', 'longitude-lower-bound', 'A longitude of -180,000,000 is excluded (180,000,000 is the same meridian and '
  'is the one included).', ['1.8.2'], doc(site={'location': {'latitude': 0, 'longitude': -180_000_000}}), SCH)
t('model', 'level-height-zero', 'A level\'s height must be greater than zero.', ['1.8.3'],
  setp(room_doc(), ['levels', 'L1', 'height'], 0), SCH)
t('model', 'level-height-negative', 'A negative level height.', ['1.8.3'], setp(room_doc(), ['levels', 'L1', 'height'], -H), SCH)

# =================================================================================== units
uj = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0)}, walls={'W1': W('J1', 'J2')})
t('units', 'length-with-fraction', 'A junction coordinate of 1000.5 base units is not a length.', ['2.1.1'],
  setp(uj, ['junctions', 'J2', 'position'], [1000.5, 0]), SCH)
raw = (fmt(uj) + '\n').replace(f'"position": [{X}, 0]', '"position": [5.12e6, 0]').encode()
t('units', 'length-with-exponent', '5.12e6 is the integer 5,120,000 written with an exponent; a length is a JSON '
  'integer with no exponent.', ['2.1.1'], None, SCH, raw=raw)
raw = (fmt(uj) + '\n').replace(f'"position": [{X}, 0]', f'"position": [{X}.0, 0]').encode()
t('units', 'length-with-zero-fraction', f'{X}.0 has an integer value but a fraction part. (A JSON Schema "integer" '
  'accepts it; Floorspec does not.)', ['2.1.1'], None, SCH, raw=raw)
t('units', 'length-beyond-2-53', 'A length of 2^53 is beyond the bound.', ['2.1.1'],
  setp(uj, ['junctions', 'J2', 'position'], [2 ** 53, 0]), SCH)
t('units', 'length-negative-beyond-2-53', 'A length of -2^53 is beyond the bound.', ['2.1.1'],
  setp(uj, ['levels', 'L1', 'elevation'], -2 ** 53), SCH)
t('units', 'length-at-bound', 'Lengths of exactly +-(2^53 - 1) are valid. The junction is unused, which is only a '
  'lint, so the document is valid.', ['2.1.1', '10.1.1'],
  no_wt(level_doc(junctions={'J1': J(2 ** 53 - 1, -(2 ** 53 - 1))})), [('FS-LINT-002', ['J1'])])
t('units', 'angle-with-fraction', 'An angle is an integer number of microdegrees.', ['2.4.1'], doc(site={'trueNorth': 1.5}), SCH)
raw = (fmt(doc(site={'trueNorth': 90000000})) + '\n').replace('90000000', '9e7').encode()
t('units', 'angle-with-exponent', '9e7 microdegrees written with an exponent is not a JSON integer.', ['2.4.1'], None, SCH, raw=raw)
t('units', 'odd-thickness-ties-to-even', 'Two free-standing centred walls of odd thickness put every face half a '
  'base unit off the grid: 128,001 gives offsets 64,000.5, which round to 64,000; 128,003 gives 64,001.5, which '
  'rounds to 64,002. Ties go to even, in both directions and on both signs.', ['2.2.1', '5.6.1', '5.7.1'],
  no_wt(level_doc(types={'T1': {'kind': 'wallType', 'layers': [{'thickness': 128001, 'function': 'core'}]},
                   'T3': {'kind': 'wallType', 'layers': [{'thickness': 128003, 'function': 'core'}]}},
            junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(0, Y), 'J4': J(X, Y)},
            walls={'W1': W('J1', 'J2', type='T1'), 'W2': W('J3', 'J4', type='T3')})))
t('units', 'oblique-3-4-5-tie', 'A wall along (3, 4): its length is rational (5 per step), and with thickness '
  '128,005 its feet are at (-51,202, 38,401.5) from each end - an exact tie, rounded to 38,402. A deriver that '
  'computes the unit normal in floating point does not land exactly on the tie.', ['2.2.1', '5.6.1', '5.7.1'],
  no_wt(level_doc(types={'T5': {'kind': 'wallType', 'layers': [{'thickness': 128005, 'function': 'core'}]}},
            junctions={'J1': J(0, 0), 'J2': J(3 * 640000, 4 * 640000)}, walls={'W1': W('J1', 'J2', type='T5')})))
t('units', 'oblique-1-2-corner', 'Two perpendicular walls along (2, 1) and (-1, 2): |d| is a multiple of sqrt(5), '
  'so every corner is irrational and is rounded once, exactly.', ['2.2.1', '5.6.1', '5.7.1'],
  level_doc(junctions={'J1': J(0, 0), 'J2': J(2 * 1280000, 1280000), 'J3': J(2 * 1280000 - 1280000, 1280000 + 2 * 1280000)},
            walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3')}))
t('units', 'handedness', 'A wall from west to east justified "exteriorFace": its location line is its left face, '
  'and its right face lies to the south (negative y), because +Y is north and a rotation from +X to +Y is '
  'counter-clockwise. A deriver with Y pointing down puts the wall on the wrong side.', ['2.3.1', '5.7.1'],
  level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0)}, walls={'W1': W('J1', 'J2', justification='exteriorFace')}))
sl = no_wt(level_doc(slabs={'SL1': {'level': 'L1', 'boundary': [[0, 0], [X, 0], [X, Y], [0, Y]], 'thickness': 150 * MM}}))
t('units', 'slab-polygon-valid', 'A counter-clockwise slab boundary: a simple polygon with positive area.', ['2.6.1', '6.7.1'], sl)
t('units', 'slab-polygon-bowtie', 'A slab boundary whose edges cross (a bow tie) is not simple.', ['2.6.1', '10.2.1'],
  setp(sl, ['slabs', 'SL1', 'boundary'], [[0, 0], [X, Y], [X, 0], [0, Y]]), [('FS-INV-009', ['SL1'])])
t('units', 'slab-polygon-repeated-vertex', 'Two vertices of a slab boundary coincide.', ['2.6.1'],
  setp(sl, ['slabs', 'SL1', 'boundary'], [[0, 0], [X, 0], [X, Y], [CX, CY], [X, Y], [0, Y]]), [('FS-INV-009', ['SL1'])])
t('units', 'site-boundary-no-area', 'A site boundary whose three vertices are collinear encloses no area: '
  'FS-INV-009 with no element.', ['2.6.1'], doc(site={'boundary': [[0, 0], [X, 0], [2 * X, 0]]}), [('FS-INV-009', [])])
t('units', 'slab-polygon-touching', 'A slab boundary that touches itself at a vertex lying on another edge.',
  ['2.6.1'], setp(sl, ['slabs', 'SL1', 'boundary'], [[0, 0], [X, 0], [X, Y], [CX, 0], [0, Y]]), [('FS-INV-009', ['SL1'])])

# =================================================================================== identity
t('identity', 'id-with-space', 'An element ID may not contain a space.', ['3.1.1'],
  setp(drop(room_doc(), ['rooms', 'R1']), ['rooms', 'Living room'], R(CX, CY)), SCH)
t('identity', 'id-leading-punctuation', 'An element ID starts with a letter or digit.', ['3.1.1'],
  setp(drop(room_doc(), ['rooms', 'R1']), ['rooms', '-R1'], R(CX, CY)), SCH)
t('identity', 'id-too-long', 'An element ID of 65 characters is one too many.', ['3.1.1'],
  setp(drop(room_doc(), ['rooms', 'R1']), ['rooms', 'R' * 65], R(CX, CY)), SCH)
t('identity', 'id-non-ascii', 'An element ID is ASCII: "Küche" is not an ID (it is a fine name).', ['3.1.1'],
  setp(drop(room_doc(), ['rooms', 'R1']), ['rooms', 'Küche'], R(CX, CY)), SCH)
long_id = 'x' + '0123456789' * 6 + 'abc'
idd = level_doc(junctions={'0': J(0, 0), 'a.b_c-D': J(X, 0)},
                walls={long_id: W('0', 'a.b_c-D')})
t('identity', 'ids-at-the-limits', f'IDs of one digit ("0"), with every permitted punctuation ("a.b_c-D"), and of '
  f'exactly 64 characters are valid, and are opaque: nothing is inferred from their spelling.', ['3.1.1'], idd)
d = room_doc()
d['materials'] = {'WT': {'color': '#c0c0c0'}}
t('identity', 'id-in-two-collections', 'The ID "WT" names a wall type and a material: IDs are unique across all '
  'collections, so a reference can never be ambiguous. FS-INV-001 names the ID.', ['3.1.2', '10.2.1'], d,
  [('FS-INV-001', ['WT'])])
d = room_doc()
d['rooms'] = {'W1': R(CX, CY)}
t('identity', 'room-and-wall-share-an-id', 'A room and a wall both called "W1".', ['3.1.2'], d, [('FS-INV-001', ['W1'])])
d = room_doc()
d['walls']['W2']['end'] = 'J9'
t('identity', 'dangling-junction-reference', 'Wall W2 ends at junction J9, which does not exist.', ['3.2.1', '10.2.1'], d,
  [('FS-INV-002', ['W2'])])
d = room_doc()
d['separators'] = {'S1': S('J1', 'J3')}
d['separators'] = {}
d['junctions']['J5'] = J(CX, 0)
d['junctions']['J6'] = J(CX, Y)
d['walls']['W4'] = W('J4', 'J5')
d['walls']['W5'] = W('J5', 'J1')
d['walls']['W2'] = W('J2', 'J6')
d['walls']['W6'] = W('J6', 'J3')
d['separators'] = {'S1': S('J5', 'J6')}
d['rooms'] = {'R1': R(CX // 2, CY), 'R2': R(CX + CX // 2, CY)}
d['openings'] = {'O1': {'wall': 'S1', 'offset': 0, 'width': 900 * MM, 'height': 2100 * MM}}
t('identity', 'reference-to-wrong-collection', 'An opening hosted on separator S1: "wall" must resolve in the walls '
  'collection, and S1 is a separator - a separator has nothing to cut.', ['3.2.1'], d, [('FS-INV-002', ['O1'])])
d = room_doc()
d['rooms']['R1']['floorFinish'] = 'OAK'
t('identity', 'dangling-material-reference', 'A room\'s floor finish names a material that does not exist.',
  ['3.2.1'], d, [('FS-INV-002', ['R1'])])
d = room_doc()
d['types']['WT']['layers'][0]['material'] = 'STUD'
t('identity', 'dangling-layer-material', 'A wall type\'s layer names a material that does not exist; the referring '
  'element is the type.', ['3.2.1'], d, [('FS-INV-002', ['WT'])])
d = level_doc(materials={'M1': {'texture': {'asset': 'A1', 'size': [300 * MM, 300 * MM]}}})
t('identity', 'dangling-texture-asset', 'A material\'s texture names an asset that does not exist.', ['3.2.1'], d,
  [('FS-INV-002', ['M1'])])
d = room_doc()
d['types']['DT'] = {'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM}
d['walls']['W3']['type'] = 'DT'
t('identity', 'wall-type-of-wrong-kind', 'Wall W3\'s type is a door type: FS-INV-003.', ['3.2.2', '10.2.1'], d,
  [('FS-INV-003', ['W3'])])
d = room_doc()
d['openings'] = {'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'WT'}}
t('identity', 'opening-fill-of-wrong-kind', 'An opening filled with a wall type: FS-INV-003.', ['3.2.2'], d,
  [('FS-INV-003', ['O1'])])
two = level_doc(levels={'L2': {'building': 'B1', 'elevation': H, 'height': H}})
d = copy.deepcopy(two)
d['junctions'] = {'J1': J(0, 0), 'J2': J(X, 0, level='L2')}
d['walls'] = {'W1': W('J1', 'J2')}
t('identity', 'junction-on-another-level', 'Wall W1 is on L1 but ends at J2, which is on L2.', ['3.3.1', '10.2.1'], d,
  [('FS-INV-007', ['J2', 'W1'])])
d = copy.deepcopy(two)
d['junctions'] = {'J1': J(0, 0, level='L2'), 'J2': J(X, 0, level='L2')}
d['separators'] = {'S1': S('J1', 'J2')}
t('identity', 'separator-junctions-on-another-level', 'Separator S1 is on L1 but both its junctions are on L2: one '
  'diagnostic for each.', ['3.3.1'], d, [('FS-INV-007', ['J1', 'S1']), ('FS-INV-007', ['J2', 'S1'])])
garage = level_doc(buildings={'B2': {'name': 'Garage'}}, levels={'G1': {'building': 'B2', 'elevation': 0, 'height': H}})
d = copy.deepcopy(garage)
d['junctions'] = {'J1': J(0, 0), 'J2': J(X, 0)}
d['walls'] = {'W1': W('J1', 'J2', top={'level': 'G1', 'offset': 2000 * MM})}
t('identity', 'top-level-in-another-building', 'Wall W1 on the house\'s level L1 takes its top from the garage\'s '
  'level G1.', ['3.3.2', '10.2.1'], d, [('FS-INV-008', ['G1', 'W1'])])
d = copy.deepcopy(garage)
d['junctions'] = {'J1': J(0, 0), 'J2': J(X, 0)}
d['walls'] = {'W1': W('J1', 'J2', base={'level': 'G1'})}
t('identity', 'base-level-in-another-building', 'Wall W1 takes its base from another building\'s level.',
  ['3.3.2'], d, [('FS-INV-008', ['G1', 'W1'])])

# =================================================================================== taxonomy
FUNCS = ['unspecified', 'sleeping', 'bath', 'kitchen', 'living', 'dining', 'office', 'laundry', 'utility',
         'storage', 'circulation', 'mechanical', 'garage', 'exterior']
STRIP = 1000 * MM
n = len(FUNCS)
js = {}
for i in range(n + 1):
    js[f'JS{i}'] = J(i * STRIP, 0)
    js[f'JN{i}'] = J(i * STRIP, Y)
ws = {'WW': W('JS0', 'JN0'), 'WE': W(f'JN{n}', f'JS{n}')}
for i in range(n):
    ws[f'WN{i}'] = W(f'JN{i}', f'JN{i + 1}')
    ws[f'WS{i}'] = W(f'JS{i + 1}', f'JS{i}')
seps = {f'S{i}': S(f'JS{i}', f'JN{i}') for i in range(1, n)}
rooms = {f'R{i}': R(i * STRIP + STRIP // 2, CY, function=f) for i, f in enumerate(FUNCS)}
t('taxonomy', 'every-room-function', 'Fourteen rooms divided by separators, one for every room function of 4.1.',
  ['4.1.1', '6.2.1'], level_doc(junctions=js, walls=ws, separators=seps, rooms=rooms))
t('taxonomy', 'unknown-room-function', '"bedroom" is a name, not a function: the function is "sleeping".',
  ['4.1.1'], setp(room_doc(), ['rooms', 'R1', 'function'], 'bedroom'), SCH)
t('taxonomy', 'room-function-wrong-case', 'Functions are case-sensitive: "Kitchen" is not a term.', ['4.1.1'],
  setp(room_doc(), ['rooms', 'R1', 'function'], 'Kitchen'), SCH)
d = setp(room_doc(), ['rooms', 'R1', 'function'], 'EXT_wellness:sauna')
d['extensionsUsed'] = {'EXT_wellness': '1.0'}
t('taxonomy', 'extension-term-declared', 'A room function from an extension the document declares: valid; a reader '
  'that does not implement EXT_wellness treats the room as unspecified and keeps the term.', ['4.1.1', '4.2.1', '1.6.6'], d)
t('taxonomy', 'extension-term-undeclared', 'The same room function without EXT_wellness in extensionsUsed: '
  'FS-INV-006 naming the room.', ['4.2.1', '10.2.1'], setp(room_doc(), ['rooms', 'R1', 'function'], 'EXT_wellness:sauna'),
  [('FS-INV-006', ['R1'])])
d = setp(room_doc(), ['rooms', 'R1', 'function'], 'EXT_wellness:Sauna')
d['extensionsUsed'] = {'EXT_wellness': '1.0'}
t('taxonomy', 'extension-term-bad-term', 'An extension term must match ^[a-z][A-Za-z0-9]*$ after the colon.',
  ['4.1.1'], d, SCH)
d = setp(room_doc(), ['rooms', 'R1', 'function'], 'wellness:sauna')
t('taxonomy', 'extension-term-bad-extension', 'The part before the colon must be an extension name.', ['4.1.1'], d, SCH)
d = room_doc()
d['types']['WT']['layers'] = [{'thickness': 12 * MM, 'function': 'drywall'}, {'thickness': 88 * MM, 'function': 'core'}]
t('taxonomy', 'unknown-layer-function', '"drywall" is a material; its function is "finish".', ['4.3.1'], d, SCH)
d = room_doc()
d['types']['WT']['layers'] = [{'thickness': 12 * MM, 'function': 'finish'}, {'thickness': 25 * MM, 'function': 'airGap'},
                              {'thickness': 1 * MM, 'function': 'membrane'}, {'thickness': 50 * MM, 'function': 'insulation'},
                              {'thickness': 12 * MM, 'function': 'substrate'}, {'thickness': 140 * MM, 'function': 'core'},
                              {'thickness': 13 * MM, 'function': 'finish'}]
t('taxonomy', 'every-layer-function', 'A wall type using every layer function of 4.3; the room is bounded by its '
  '253 mm centred walls.', ['4.3.1', '5.7.1', '6.2.1'], d)
d = room_doc()
d['types']['WT']['layers'][0]['function'] = 'Core'
t('taxonomy', 'layer-function-wrong-case', 'Layer functions are case-sensitive.', ['4.3.1'], d, SCH)

# ------------------------------------------------------------ model: closed objects and member types (1.4.3, 1.4.4)
t('model', 'project-unknown-member', 'The project is not an element but is closed all the same: "client" is not in '
  'its table.', ['1.4.3'], doc(project={'name': 'Conformance', 'client': 'Someone'}), SCH)
t('model', 'site-unknown-member', 'The site is closed: "elevation" is not a site member.', ['1.4.3'],
  doc(site={'elevation': 0}), SCH)
t('model', 'location-unknown-member', 'A site location has latitude and longitude and nothing else.', ['1.4.3'],
  doc(site={'location': {'latitude': 0, 'longitude': 0, 'altitude': 0}}), SCH)
t('model', 'base-unknown-member', 'A wall\'s base has level and offset only.', ['1.4.3'],
  setp(room_doc(), ['walls', 'W1', 'base'], {'height': 0}), SCH)
t('model', 'top-unknown-member', 'A wall\'s level-constrained top has level and offset only.', ['1.4.3', '5.9.1'],
  setp(room_doc(), ['walls', 'W1', 'top'], {'level': 'L1', 'offset': 0, 'clearance': 1}), SCH)
t('model', 'layer-unknown-member', 'A layer is not an element: it may not carry a "name".', ['1.4.3'],
  setp(room_doc(), ['types', 'WT', 'layers'], [{'thickness': T100, 'function': 'core', 'name': 'Studs'}]), SCH)
d = level_doc(materials={'M1': {'texture': {'asset': 'A1', 'size': [300 * MM, 300 * MM], 'rotation': 0}}},
              assets={'A1': {'path': 'oak.png', 'sha256': '0' * 64, 'mediaType': 'image/png'}})
t('model', 'texture-unknown-member', 'A texture has asset and size only.', ['1.4.3'], d, SCH)
t('model', 'justification-unknown-value', '"middle" is not a justification.', ['1.4.4'],
  setp(room_doc(), ['walls', 'W1', 'justification'], 'middle'), SCH)
t('model', 'name-empty', 'A name has 1 to 200 characters: the empty string is not one.', ['1.4.4'],
  setp(room_doc(), ['rooms', 'R1', 'name'], ''), SCH)
t('model', 'name-too-long', 'A name of 201 characters.', ['1.4.4'], setp(room_doc(), ['rooms', 'R1', 'name'], 'a' * 201), SCH)
t('model', 'name-limits-in-code-points', 'Names of exactly 200 characters, counted in Unicode code points: 200 '
  'astral characters (400 UTF-16 code units) and 200 ASCII characters are both valid.', ['1.4.4', '9.2.1'],
  setp(setp(room_doc(), ['rooms', 'R1', 'name'], '\U0001F3E0' * 200), ['walls', 'W1', 'name'], 'w' * 200))
t('model', 'hinge-unknown-value', 'An opening\'s hinge is "start" or "end".', ['1.4.4'],
  setp(baseline(), ['openings', 'O1', 'hinge'], 'left'), SCH)
t('model', 'location-missing-longitude', 'A site location has both a latitude and a longitude.', ['1.4.4', '1.8.2'],
  doc(site={'location': {'latitude': 0}}), SCH)
t('model', 'latitude-as-string', 'A latitude is an angle, not a string.', ['1.4.4', '2.4.1'],
  doc(site={'location': {'latitude': '42.3', 'longitude': 0}}), SCH)
t('model', 'extras-not-an-object', 'extras is an object.', ['1.4.4'], setp(room_doc(), ['walls', 'W1', 'extras'], ['note']), SCH)
t('model', 'collection-not-an-object', 'A collection is an object keyed by ID, not an array.', ['1.4.4'],
  doc(buildings=[{'name': 'House'}]), SCH)
t('model', 'extension-version-pattern', 'An extension version is <major>.<minor>[.<patch>][-prerelease]: "v1" is not.',
  ['1.6.7'], doc(extensionsUsed={'EXT_acoustics': 'v1'}), SCH)
t('model', 'extension-version-number', 'An extension version is a string, not a number.', ['1.6.7'],
  doc(extensionsUsed={'EXT_acoustics': 1}), SCH)
d = baseline()
d['extensionsUsed'] = {'EXT_a': '1.0', 'EXT_b': '2.10.3', 'EXT_c': '0.1.0-rc.1'}
t('model', 'extension-versions-valid', 'Versions "1.0", "2.10.3" and "0.1.0-rc.1" all match the pattern. The '
  'extensions are declared and unused, which is valid.', ['1.6.7'], d)
t('model', 'required-extension-twice',
  'extensionsRequired names EXT_acoustics twice. FS-DOC-002 applies only to an array of distinct names, so the '
  'document reaches the schema tier, which rejects the duplicate.',
  ['1.6.8'], doc(extensionsUsed={'EXT_acoustics': '1.0'}, extensionsRequired=['EXT_acoustics', 'EXT_acoustics']),
  SCH)

# ------------------------------------------------------------ identity: reference syntax (3.2.3)
t('identity', 'reference-not-an-id', 'A reference that does not match the ID pattern ("Wall 1") is a schema error, '
  'not a dangling reference.', ['3.2.3'], setp(baseline(), ['openings', 'O1', 'wall'], 'Wall 1'), SCH)
t('identity', 'reference-not-a-string', 'A reference is a string: 4 is not one.', ['3.2.3'],
  setp(room_doc(), ['walls', 'W1', 'start'], 1), SCH)
t('identity', 'through-reference-not-an-id', 'The IDs in a join\'s through list are references too.', ['3.2.3', '5.8.5'],
  setp(room_doc(), ['junctions', 'J1', 'join'], {'kind': 'butt', 'through': ['W 1']}), SCH)

# =================================================================================== walls
fw = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0)}, walls={'W1': W('J1', 'J2')})
t('walls', 'free-standing-wall', 'One centred wall with two free ends: each junction has one edge, so each wedge is a '
  'full turn with parallel face lines and the corner sequence is the two feet - the ends are cut square.',
  ['5.6.1', '5.7.1', '5.7.2', '5.9.3', '2.3.1'], fw)
lc = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(X, Y)}, walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3')})
t('walls', 'l-corner', 'Two centred walls meeting at a right angle with the default mitre: both walls end at the '
  'outer corner (X + 64,000, -64,000) and the inner corner (X - 64,000, 64,000).', ['5.6.1', '5.7.1', '5.7.2'], lc)
lr = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(X, Y)}, walls={'W1': W('J1', 'J2'), 'W2': W('J3', 'J2')})
t('walls', 'l-corner-reversed-wall', 'walls/002 with W2 drawn the other way, ending at the corner: its face ends are '
  'the same points, read from its end junction where its sides are reversed.', ['5.6.1', '5.7.1'], lr)
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(2 * X, 0)}, walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3')})
t('walls', 'collinear-equal-offsets', 'Two collinear walls of the same thickness and justification: at J2 the face '
  'lines are parallel and the two feet coincide, so the walls continue as one with a square seam.', ['5.6.1', '5.7.1'], d)
d = level_doc(types={'WT2': {'kind': 'wallType', 'layers': [{'thickness': 2 * T100, 'function': 'core'}]}},
              junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(2 * X, 0)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3', type='WT2')})
t('walls', 'collinear-step', 'Two collinear walls of 100 mm and 200 mm: the feet differ, so each wedge\'s corner '
  'sequence is two points and the faces meet in a step.', ['5.6.1', '5.7.1'], d)
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(2 * X, 0)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3', justification='exteriorFace')})
t('walls', 'collinear-step-by-justification', 'Two collinear walls of equal thickness but different justification '
  'also step: the offsets differ, not the thickness.', ['5.6.1', '5.7.1'], d)
for just, slug, what in (('exteriorFace', 'justification-exterior-face', 'the location line is the exterior (left) face, '
                          'so the room is the location-line rectangle shrunk by the full 100 mm'),
                         ('interiorFace', 'justification-interior-face', 'the location line is the interior (right) '
                          'face, so the room polygon is exactly the location-line rectangle')):
    js_, ws_ = box('', 0, 0, X, Y, justification=just)
    t('walls', slug, f'A room drawn clockwise with every wall justified "{just}": {what}.',
      ['5.6.1', '5.7.1', '6.2.1', '6.4.1'], level_doc(junctions=js_, walls=ws_, rooms={'R1': R(CX, CY)}))
LAYERED = [{'thickness': 19 * MM, 'function': 'finish'}, {'thickness': 11 * MM, 'function': 'substrate'},
           {'thickness': 140 * MM, 'function': 'core'}, {'thickness': 13 * MM, 'function': 'finish'}]
js_, ws_ = box('', 0, 0, X, Y, type='EXT', justification='coreFace')
t('walls', 'justification-core-face', 'A room of layered walls (finish 19, substrate 11, core 140, finish 13 mm) '
  'justified "coreFace": a = 30 mm (the layers before the core) and b = 153 mm.', ['5.6.1', '5.7.1', '6.2.1', '8.2.1'],
  no_wt(level_doc(types={'EXT': {'kind': 'wallType', 'layers': LAYERED}}, junctions=js_, walls=ws_, rooms={'R1': R(CX, CY)})))
d = no_wt(level_doc(types={'ODD': {'kind': 'wallType', 'layers': [{'thickness': 128001, 'function': 'core'}]}}))
d['junctions'], d['walls'] = box('', 0, 0, X, Y, type='ODD')
d['rooms'] = {'R1': R(CX, CY)}
t('walls', 'odd-thickness-room', 'A room of centred walls 128,001 units thick: every corner is at a half unit in '
  'both coordinates, and rounds to even - so the room polygon is not symmetric about the location lines.',
  ['2.2.1', '5.6.1', '5.7.1', '6.2.1', '6.4.1'], d)
# diamond: walls along (1, 1) directions
A = 3000 * MM
d = level_doc(junctions={'J1': J(0, -A), 'J2': J(-A, 0), 'J3': J(0, A), 'J4': J(A, 0)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J1')},
              rooms={'R1': R(0, 0)})
t('walls', 'oblique-1-1-room', 'A square room turned 45 degrees: every face line is offset by 64,000 along a unit '
  'normal of (1, 1)/sqrt(2), so every corner is irrational and is rounded once.', ['2.2.1', '5.6.1', '5.7.1', '6.2.1', '6.4.1'], d)
u = 1280000
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(-u, 2 * u), 'J3': J(3 * u, 4 * u), 'J4': J(4 * u, 2 * u)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J1')},
              rooms={'R1': R(u + u // 2, 2 * u)})
t('walls', 'oblique-1-2-room', 'A rectangular room whose walls run along (-1, 2) and (2, 1): lengths are multiples of '
  'sqrt(5), so the corners are irrational.', ['2.2.1', '5.6.1', '5.7.1', '6.2.1', '6.4.1'], d)
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(3 * u, 4 * u), 'J3': J(3 * u + 4 * u, 4 * u - 3 * u)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3')})
t('walls', 'oblique-3-4-5-corner', 'An L corner of walls along (3, 4) and (4, -3): every length is rational, so '
  'the corners are rational too.', ['5.6.1', '5.7.1'], d)
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(2 * u, 0), 'J3': J(2 * u + 5 * u, 2 * u)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3')})
t('walls', 'obtuse-corner', 'Two walls meeting at an obtuse angle (direction (5, 2) after (1, 0)): the mitre '
  'corner is the exact intersection of an axis-aligned and an oblique face line.', ['5.6.1', '5.7.1'], d)
# elevations
el = level_doc(levels={'L2': {'building': 'B1', 'elevation': 3000 * MM, 'height': H}},
               junctions={f'J{i}': J(i * 2000 * MM, 0) for i in range(10)})
el['walls'] = {
    'WA': W('J0', 'J1'),
    'WB': W('J2', 'J3', top={'level': 'L2', 'offset': -200 * MM}),
    'WC': W('J4', 'J5', base={'offset': 100 * MM}, top={'height': 1200 * MM}),
    'WD': W('J6', 'J7', base={'level': 'L2'}, top={'height': 900 * MM}),
    'WE': W('J8', 'J9', base={'level': 'L1', 'offset': -300 * MM}, top={'level': 'L2'}),
}
t('walls', 'elevations', 'Five free-standing walls on L1 (elevation 0, height 2700 mm) with L2 at 3000 mm: WA '
  'follows its level (0 to 2700 mm); WB tops out at L2 - 200 mm; WC has base offset 100 mm and an unconnected height '
  'of 1200 mm; WD sits on L2 with height 900 mm; WE starts 300 mm below L1 and rises to L2.',
  ['5.9.1', '5.9.3', '3.3.2'], el)
t('walls', 'top-level-and-height', 'A top with both level and height.', ['5.9.1'],
  setp(fw, ['walls', 'W1', 'top'], {'level': 'L1', 'height': 1000 * MM}), SCH)
t('walls', 'top-offset-with-height', 'offset belongs to a level-constrained top, never to a height.', ['5.9.1'],
  setp(fw, ['walls', 'W1', 'top'], {'height': 1000 * MM, 'offset': 0}), SCH)
t('walls', 'top-empty', 'A top with neither level nor height.', ['5.9.1'], setp(fw, ['walls', 'W1', 'top'], {}), SCH)
t('walls', 'top-not-above-base', 'A wall whose unconnected height is zero: its top is not above its base.',
  ['5.9.2', '10.2.1'], setp(fw, ['walls', 'W1', 'top'], {'height': 0}), [('FS-INV-112', ['W1'])])
t('walls', 'top-below-base-by-level', 'A wall based on L2 (3000 mm) whose top follows its own level L1 (0 + 2700 mm).',
  ['5.9.2'], setp(setp(fw, ['levels', 'L2'], {'building': 'B1', 'elevation': 3000 * MM, 'height': H}),
                  ['walls', 'W1', 'base'], {'level': 'L2'}), [('FS-INV-112', ['W1'])])
d = setp(fw, ['junctions', 'J3'], J(0, 0))
t('walls', 'junctions-share-a-position', 'Junction J3 is at the same position as J1, on the same level.', ['5.1.1', '10.2.1'],
  d, [('FS-INV-101', ['J1', 'J3'])])
d = setp(fw, ['levels', 'L2'], {'building': 'B1', 'elevation': 3000 * MM, 'height': H})
d['junctions']['J3'] = J(0, 0, level='L2')
t('walls', 'same-position-on-other-levels', 'Junctions on different levels may share a position - a corner '
  'directly above another. J3 is unused, a lint.', ['5.1.1'], d, [('FS-LINT-002', ['J3'])])
t('walls', 'edge-from-junction-to-itself', 'Wall W2 starts and ends at J2.', ['5.2.1', '10.2.1'],
  setp(fw, ['walls', 'W2'], W('J2', 'J2')), [('FS-INV-102', ['W2'])])
t('walls', 'separator-from-junction-to-itself', 'A separator that starts and ends at J1.', ['5.2.1'],
  setp(fw, ['separators'], {'S1': S('J1', 'J1')}), [('FS-INV-102', ['S1'])])
t('walls', 'duplicate-walls', 'Two walls from J1 to J2: one wall drawn twice.', ['5.2.2'],
  setp(fw, ['walls', 'W2'], W('J1', 'J2')), [('FS-INV-103', ['W1', 'W2'])])
d = setp(fw, ['separators'], {'S1': S('J2', 'J1')})
t('walls', 'two-edges-same-junctions', 'A wall and a separator both connect J1 and J2 (in opposite orders).',
  ['5.2.2', '10.2.1'], d, [('FS-INV-103', ['S1', 'W1'])])
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(CX, -CY), 'J4': J(CX, CY)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J3', 'J4')})
t('walls', 'crossing-walls', 'Two walls cross at (X/2, 0), a point interior to both, with no junction there.',
  ['5.3.1', '10.2.1'], d, [('FS-INV-104', ['W1', 'W2'])])
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(CX, 0), 'J4': J(CX, CY)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J3', 'J4')})
t('walls', 't-without-a-junction', 'A wall ends against the middle of another: J3 lies in the interior of W1. The '
  'through wall must be two edges.', ['5.3.2', '10.2.1'], d, [('FS-INV-105', ['J3', 'W1'])])
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(CX, 0)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J1', 'J3')})
t('walls', 'overlapping-walls', 'W2 runs from J1 along W1 to J3, halfway: the two overlap along a segment. An '
  'overlap always leaves a junction inside the other edge, so FS-INV-105 is reported with it.',
  ['5.3.3', '5.3.2', '10.2.1'], d, [('FS-INV-105', ['J3', 'W1']), ('FS-INV-106', ['W1', 'W2'])])
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(X, Y)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3')}, separators={'S1': S('J1', 'J3')})
t('walls', 'separator-touching-at-junctions', 'A separator meeting walls only at shared junctions is planar.',
  ['5.3.1', '5.3.2', '5.3.3'], d, [('FS-LINT-003', [])])
t('walls', 'no-effective-layers', 'A wall with neither layers nor a type has no thickness.', ['5.4.1', '10.2.1'],
  setp(fw, ['walls', 'W1'], W('J1', 'J2', type=None)), [('FS-INV-107', ['W1'])])
d = setp(fw, ['walls', 'W1'], W('J1', 'J2', justification='coreFace'))
t('walls', 'core-face-without-core', 'A "coreFace" wall whose only layer is insulation has no core face.',
  ['5.4.2', '10.2.1'], setp(d, ['types', 'WT', 'layers'], [{'thickness': T100, 'function': 'insulation'}]),
  [('FS-INV-108', ['W1'])])
t('walls', 'core-face-split-core', 'A "coreFace" wall whose two core layers are separated by insulation.', ['5.4.2'],
  setp(d, ['types', 'WT', 'layers'], [{'thickness': T100, 'function': 'core'}, {'thickness': T100, 'function': 'insulation'},
                                      {'thickness': T100, 'function': 'core'}]), [('FS-INV-108', ['W1'])])
t('walls', 'core-face-two-consecutive-cores', 'Two consecutive core layers are one core: the location line is on the '
  'exterior face of the first.', ['5.4.2', '5.7.1'],
  setp(d, ['types', 'WT', 'layers'], [{'thickness': 20 * MM, 'function': 'finish'}, {'thickness': T100, 'function': 'core'},
                                      {'thickness': T100, 'function': 'core'}]))
T200 = 200 * MM
d = no_wt(level_doc(types={'THICK': {'kind': 'wallType', 'layers': [{'thickness': T200, 'function': 'core'}]}},
                    junctions={'J1': J(0, 0), 'J2': J(50 * MM, 0), 'J3': J(0, 2000 * MM), 'J4': J(50 * MM, 2000 * MM)},
                    walls={'W1': W('J3', 'J1', type='THICK'), 'W2': W('J1', 'J2', type='THICK'), 'W3': W('J2', 'J4', type='THICK')}))
t('walls', 'stub-outline-not-simple', 'A 50 mm wall W2 between two parallel 200 mm walls: the mitres at its ends cross, '
  'so its outline is not a simple polygon.', ['5.7.2', '10.2.1'], d, [('FS-INV-109', ['W2'])])

# =================================================================================== joins
def tj(join=None, stem=True, extra_walls=None, rooms=None):
    js_ = {'J0': J(CX, 0), 'JE': J(X, 0), 'JW': J(0, 0), 'JS': J(CX, -Y)}
    ws_ = {'W1': W('J0', 'JE'), 'W2': W('JW', 'J0'), 'W3': W('JS', 'J0')}
    if join:
        js_['J0']['join'] = join
    d = level_doc(junctions=js_, walls=ws_)
    return d


t('joins', 't-mitre-fill', 'A T of three centred walls with the default join: the outlines leave a triangular gap '
  'at J0, closed by its junction fill.', ['5.6.1', '5.7.1', '5.7.3', '5.7.4'], tj())
d = level_doc(junctions={'J0': J(0, 0), 'JE': J(X, 0), 'JN': J(0, Y), 'JW': J(-X, 0), 'JS': J(0, -Y)},
              walls={'W1': W('J0', 'JE'), 'W2': W('J0', 'JN'), 'W3': W('JW', 'J0'), 'W4': W('JS', 'J0')})
t('joins', 'x-mitre-fill', 'An X of four centred walls: every wedge is 90 degrees, and the fill is the square around '
  'J0.', ['5.6.1', '5.7.1', '5.7.3', '5.7.4'], d)
d = level_doc(junctions={'J0': J(0, 0), 'JA': J(0, 2 * u), 'JB': J(-1732 * MM, -1000 * MM), 'JC': J(1732 * MM, -1000 * MM)},
              walls={'W1': W('J0', 'JA'), 'W2': W('J0', 'JB'), 'W3': W('J0', 'JC')})
t('joins', 'y-mitre-fill', 'A Y of three walls about 120 degrees apart: the corners are irrational and the fill is '
  'a triangle around J0.', ['2.2.1', '5.6.1', '5.7.1', '5.7.3', '5.7.4'], d)
d = level_doc(junctions={'J0': J(0, 0), 'J1': J(X, 0), 'J2': J(u, 3 * u), 'J3': J(-2 * u, 2 * u), 'J4': J(-3 * u, -u), 'J5': J(u, -3 * u)},
              walls={f'W{i}': W('J0', f'J{i}') for i in range(1, 6)})
t('joins', 'five-way-mitre-fill', 'Five walls meeting at one junction: the fill is the pentagon of the five wedge '
  'corners.', ['5.6.1', '5.7.1', '5.7.3', '5.7.4'], d)
d = level_doc(junctions={'J0': J(0, 0), 'JE': J(X, 0), 'JW': J(-X, 0), 'JS': J(0, -Y)},
              walls={'W1': W('J0', 'JE'), 'W2': W('JW', 'J0')}, separators={'S1': S('J0', 'JS')})
t('joins', 't-with-separator', 'Two walls continue through J0 and a separator leaves it: the separator\'s face lines '
  'are its location line, so the fill degenerates to fewer than three distinct points and is empty.',
  ['5.6.1', '5.7.3', '5.7.4'], d, [])
d = no_wt(level_doc(types={'TRUNK': {'kind': 'wallType', 'layers': [{'thickness': 400 * MM, 'function': 'core'}]},
                           'ARM': {'kind': 'wallType', 'layers': [{'thickness': T100, 'function': 'core'}]}},
                    junctions={'J0': J(0, 0), 'JS': J(0, -Y), 'JA': J(u, 2 * u), 'JB': J(-u, 2 * u)},
                    walls={'W1': W('J0', 'JS', type='TRUNK'), 'W2': W('J0', 'JA', type='ARM'), 'W3': W('J0', 'JB', type='ARM')}))
t('joins', 'fill-clockwise', 'A Y whose 400 mm trunk is much thicker than its two 100 mm arms: the wedge corners '
  'come out in clockwise order, so the junction fill is clockwise.', ['5.7.4', '10.2.1'], d, [('FS-INV-110', ['J0'])])
# butt L
lb = copy.deepcopy(lc)
lb['junctions']['J2']['join'] = {'kind': 'butt', 'through': ['W1']}
t('joins', 'butt-l-corner', 'walls/002 with a butt join at the corner, W1 running through: W1 runs out to the '
  'outer corner, and W2 stops against W1\'s inner face. The corner points are unchanged; only the division between '
  'the walls moves.', ['5.8.2', '5.8.4', '5.7.1'], lb)
lb2 = copy.deepcopy(lc)
lb2['junctions']['J2']['join'] = {'kind': 'butt', 'through': ['W2']}
t('joins', 'butt-l-corner-other-wall', 'The same corner with W2 running through instead.', ['5.8.2', '5.8.4'], lb2)
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(2 * u, 0), 'J3': J(2 * u + u, 2 * u)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3')})
d['junctions']['J2']['join'] = {'kind': 'butt', 'through': ['W2']}
t('joins', 'butt-oblique-corner', 'A butt join at a 63.4-degree corner (directions (1, 0) and (1, 2)): p, the '
  'intersection of W2\'s convex-side face and W1\'s reflex-side face, is irrational.', ['2.2.1', '5.8.2', '5.8.4'], d)
d = no_wt(level_doc(types={'A': {'kind': 'wallType', 'layers': [{'thickness': 200 * MM, 'function': 'core'}]},
                           'B': {'kind': 'wallType', 'layers': [{'thickness': T100, 'function': 'core'}]}},
                    junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(X - u, 2 * u)},
                    walls={'W1': W('J1', 'J2', type='A'), 'W2': W('J2', 'J3', type='B', justification='interiorFace')}))
d['junctions']['J2']['join'] = {'kind': 'butt', 'through': ['W1']}
t('joins', 'butt-acute-corner-mixed', 'A butt join at an acute (63.4-degree) corner between a 200 mm centred wall '
  'W1, which runs through, and a 100 mm wall W2 justified "interiorFace".', ['5.8.2', '5.8.4'], d)
tb = tj({'kind': 'butt', 'through': ['W1', 'W2']})
t('joins', 'butt-t-two-through', 'A T with W1 and W2 running through: their faces end square at the feet of J0, so '
  'they read as one wall, and the stem W3 stops against their common face. A butt join has no junction fill.',
  ['5.8.3', '5.8.4', '5.7.3'], tb)
d = level_doc(junctions={'J0': J(0, 0), 'JE': J(X, 0), 'JN': J(0, Y), 'JW': J(-X, 0), 'JS': J(0, -Y)},
              walls={'W1': W('J0', 'JE'), 'W2': W('J0', 'JN'), 'W3': W('JW', 'J0'), 'W4': W('JS', 'J0')})
d['junctions']['J0']['join'] = {'kind': 'butt', 'through': ['W2', 'W4']}
t('joins', 'butt-x-two-through', 'An X with the north-south walls W2 and W4 running through, one other edge on each '
  'side.', ['5.8.3', '5.8.4'], d)
t('joins', 'through-wall-not-at-junction', 'A butt join at J0 naming W9, a wall elsewhere on the level.', ['5.8.1', '10.2.1'],
  setp(setp(setp(tj({'kind': 'butt', 'through': ['W9']}), ['junctions', 'JX'], J(0, Y)), ['junctions', 'JY'], J(X, Y)),
       ['walls', 'W9'], W('JX', 'JY')), [('FS-INV-111', ['J0'])])
d = setp(tj({'kind': 'butt', 'through': ['S1']}), ['separators', 'S1'], S('J0', 'JN'))
d['junctions']['JN'] = J(CX, Y)
t('joins', 'through-names-a-separator', 'A butt join naming separator S1: through refers to the walls collection, so '
  'the reference does not resolve - FS-INV-002, at the reference tier, before FS-INV-111 could be evaluated.',
  ['3.2.1'], d, [('FS-INV-002', ['J0'])])
t('joins', 'one-through-at-a-t', 'One through wall at a junction with three edges.', ['5.8.2', '10.2.1'],
  tj({'kind': 'butt', 'through': ['W1']}), [('FS-INV-111', ['J0'])])
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(2 * X, 0)}, walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3')})
d['junctions']['J2']['join'] = {'kind': 'butt', 'through': ['W1']}
t('joins', 'one-through-collinear', 'One through wall where the two edges are collinear: nothing to butt against.',
  ['5.8.2'], d, [('FS-INV-111', ['J2'])])
t('joins', 'two-through-not-opposite', 'W1 and W3 of a T leave J0 at a right angle, not in opposite directions.',
  ['5.8.3', '10.2.1'], tj({'kind': 'butt', 'through': ['W1', 'W3']}), [('FS-INV-111', ['J0'])])
d = tj({'kind': 'butt', 'through': ['W1', 'W2']})
d['walls']['W2']['justification'] = 'exteriorFace'
t('joins', 'two-through-face-lines-differ', 'W1 and W2 are opposite but W2 is justified differently, so their face '
  'lines do not coincide.', ['5.8.3'], d, [('FS-INV-111', ['J0'])])
d = tj({'kind': 'butt', 'through': ['W1', 'W2']})
d['junctions']['JS2'] = J(CX + u, -Y)
d['walls']['W4'] = W('J0', 'JS2')
t('joins', 'two-through-two-on-one-side', 'Two through walls with two other edges on the same side.', ['5.8.3'], d,
  [('FS-INV-111', ['J0'])])
for join, slug, why in (({'kind': 'mitre', 'through': ['W1']}, 'join-mitre-with-through', 'a mitre join names no walls'),
                       ({'kind': 'butt'}, 'join-butt-without-through', 'a butt join names the walls that run through'),
                       ({'kind': 'butt', 'through': []}, 'join-through-empty', 'through names one or two walls, not none'),
                       ({'kind': 'butt', 'through': ['W1', 'W2', 'W3']}, 'join-through-three', 'through names at most two walls'),
                       ({'kind': 'miter'}, 'join-kind-miter', '"miter" is not a join kind; the spelling is "mitre"'),
                       ({'through': ['W1', 'W2']}, 'join-without-kind', 'a join always has a kind')):
    t('joins', slug, f'A join that has none of the three forms of 5.8: {why}.', ['5.8.5'], tj(join), SCH)
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(0, 1280000)}, walls={'W1': W('J2', 'J1'), 'W2': W('J1', 'J3')})
d['junctions']['J3']['position'] = [X, 1280000]
t('joins', 'acute-join-lint', 'Two walls meeting at about 14 degrees: valid, with an acute-join warning naming the '
  'junction and both walls.', ['5.6.1', '5.7.1', '10.1.1'], d, [('FS-LINT-001', ['J1', 'W1', 'W2'])])
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(X, 2200 * MM)}, walls={'W1': W('J2', 'J1'), 'W2': W('J1', 'J3')})
t('joins', 'acute-join-boundary', 'Two walls at about 28.8 degrees - under 30, so the lint applies by the exact test '
  '4(d1.d2)^2 > 3|d1|^2|d2|^2.', ['5.6.1'], d, [('FS-LINT-001', ['J1', 'W1', 'W2'])])
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(X, 2400 * MM)}, walls={'W1': W('J2', 'J1'), 'W2': W('J1', 'J3')})
t('joins', 'acute-join-not-acute', 'At about 31 degrees the join is not acute: no lint.', ['5.6.1', '5.7.1'], d)

# =================================================================================== rooms
t('rooms', 'one-room', 'One 4 m by 3 m room of 100 mm centred walls drawn clockwise: its polygon is the '
  'rectangle of the walls\' inner faces, counter-clockwise from its least vertex, and its net area is '
  '4,992,000 x 3,712,000 square base units.', ['6.2.1', '6.3.1', '6.3.4', '6.4.1'], room_doc())
js_, ws_ = box('', 0, 0, X, Y)
js_['J5'] = J(CX, 0)
js_['J6'] = J(CX, Y)
ws_['W2'] = W('J2', 'J6')
ws_['W5'] = W('J6', 'J3')
ws_['W4'] = W('J4', 'J5')
ws_['W6'] = W('J5', 'J1')
ws_['W7'] = W('J5', 'J6')
t('rooms', 'two-rooms-sharing-a-wall', 'Two rooms divided by a centred interior wall W7: each room polygon stops at '
  'that wall\'s face, and the T junctions get fills.', ['6.2.1', '6.3.2', '6.4.1', '5.7.3'],
  level_doc(junctions=js_, walls=ws_, rooms={'R1': R(CX // 2, CY, name='Kitchen', function='kitchen'),
                                             'R2': R(CX + CX // 2, CY, name='Dining', function='dining')}))
ws2 = {k: v for k, v in ws_.items() if k != 'W7'}
open_plan = level_doc(junctions=js_, walls=ws2, separators={'S1': S('J5', 'J6')},
                      rooms={'R1': R(CX // 2, CY, function='kitchen'), 'R2': R(CX + CX // 2, CY, function='dining')})
t('rooms', 'separator-splits-open-plan', 'An open kitchen and dining room divided by separator S1: the separator '
  'has no thickness, so both room polygons run to its location line.', ['6.2.1', '6.3.2', '6.4.1'], open_plan)
d = level_doc(junctions=js_, walls=ws_, rooms={'R1': R(CX // 2, CY)})
t('rooms', 'unanchored-face', 'rooms/002 with only one room: the other bounded face is unanchored - derived, '
  'reported as an informational lint, and not an error.', ['6.2.1', '6.4.1', '10.1.1'], d, [('FS-LINT-003', [])])
BIGX, BIGY = 6000 * MM, 5000 * MM
js_, ws_ = box('', 0, 0, BIGX, BIGY)
cj, cw = box('C', 1000 * MM, 1000 * MM, 2000 * MM, 2000 * MM)
js_.update(cj)
ws_.update(cw)
js_['F1'] = J(4000 * MM, 2500 * MM)
js_['F2'] = J(5000 * MM, 2500 * MM)
ws_['FW'] = W('F1', 'F2')
t('rooms', 'room-with-holes', 'A 6 m by 5 m room with a freestanding closet (four walls, its own room R2) and a '
  'freestanding wall inside it: the room polygon has two hole rings, each clockwise from its least vertex - the '
  'closet\'s outer faces and the wall\'s rectangle - and its net area excludes both.',
  ['6.1', '6.2.1', '6.3.4', '6.4.1'] and ['6.2.1', '6.3.4', '6.4.1'],
  level_doc(junctions=js_, walls=ws_, rooms={'R1': R(3000 * MM, 4000 * MM), 'R2': R(1500 * MM, 1500 * MM, function='storage')}))
js_, ws_ = box('', 0, 0, X, Y)
js_['J5'] = J(CX, 0)
js_['J6'] = J(CX, CY)
ws_['W4'] = W('J4', 'J5')
ws_['W5'] = W('J5', 'J1')
ws_['W6'] = W('J5', 'J6')
t('rooms', 'dangling-wall', 'A wall W6 runs from the south wall into the room and ends freely: the room ring goes '
  'up one face of W6, around its square free end and back down the other.', ['6.2.1', '6.4.1', '5.6.1'],
  level_doc(junctions=js_, walls=ws_, rooms={'R1': R(CX // 2, CY)}))
ja, wa = box('A', 0, 0, X, Y)
jb, wb = box('B', X + 2000 * MM, 0, 2 * X + 2000 * MM, Y)
t('rooms', 'disconnected-groups', 'Two separate rectangles of walls on one level - a house and a detached studio '
  'drawn on the same plan: two components, neither inside the other, and a room in each.', ['6.2.1', '6.4.1'],
  level_doc(junctions={**ja, **jb}, walls={**wa, **wb}, rooms={'R1': R(CX, CY), 'R2': R(X + 2000 * MM + CX, CY)}))
d = room_doc()
d['rooms']['R2'] = R(CX + 1000 * MM, CY)
t('rooms', 'two-anchors-in-one-face', 'Two rooms anchored in the same face: FS-INV-202 names both, and Floorspec '
  'does not choose which survives.', ['6.3.2', '10.2.1'], d, [('FS-INV-202', ['R1', 'R2'])])
d = drop(open_plan, ['separators'])
t('rooms', 'separator-removed', 'rooms/003 with the separator removed: kitchen and dining are now in one face, so the '
  'document is invalid until a room is removed or the space divided again.', ['6.3.2'], d, [('FS-INV-202', ['R1', 'R2'])])
t('rooms', 'anchor-outside', 'A room anchored outside every wall: in the unbounded face.', ['6.3.1', '10.2.1'],
  setp(room_doc(), ['rooms', 'R1', 'anchor'], [-1000 * MM, CY]), [('FS-INV-201', ['R1'])])
t('rooms', 'anchor-on-location-line', 'A room anchored exactly on wall W1\'s location line.', ['6.3.1'],
  setp(room_doc(), ['rooms', 'R1', 'anchor'], [0, CY]), [('FS-INV-201', ['R1'])])
t('rooms', 'anchor-on-junction', 'A room anchored exactly on a junction, the end of a location line.', ['6.3.1'],
  setp(room_doc(), ['rooms', 'R1', 'anchor'], [X, Y]), [('FS-INV-201', ['R1'])])
t('rooms', 'anchor-on-separator', 'A room anchored on a separator\'s location line.', ['6.3.1'],
  setp(open_plan, ['rooms', 'R2', 'anchor'], [CX, CY]), [('FS-INV-201', ['R2'])])
t('rooms', 'anchor-on-another-level', 'A room on level L2, which has no walls: its anchor is in L2\'s unbounded face, '
  'whatever lies under it on L1.', ['6.3.1'],
  setp(setp(room_doc(), ['levels', 'L2'], {'building': 'B1', 'elevation': H, 'height': H}), ['rooms', 'R2'], R(CX, CY, level='L2')),
  [('FS-INV-201', ['R2'])])
t('rooms', 'anchor-in-wall-thickness', 'A room anchored 32,000 units inside W1\'s location line: in the face, but in '
  'the wall\'s thickness, not inside the room polygon.', ['6.3.4', '10.2.1'],
  setp(room_doc(), ['rooms', 'R1', 'anchor'], [32000, CY]), [('FS-INV-204', ['R1'])])
t('rooms', 'anchor-on-room-polygon', 'A room anchored exactly on its polygon\'s edge (the inner face of W1): not '
  'strictly inside.', ['6.3.4'], setp(room_doc(), ['rooms', 'R1', 'anchor'], [64000, CY]), [('FS-INV-204', ['R1'])])
js_, ws_ = box('', 0, 0, X, Y)
js_['F1'] = J(1000 * MM, CY)
js_['F2'] = J(3000 * MM, CY)
ws_['FW'] = W('F1', 'F2')
t('rooms', 'anchor-in-a-hole', 'A room anchored in the thickness of a freestanding wall standing inside it: in the '
  'face, but inside a hole ring.', ['6.3.4'],
  level_doc(junctions=js_, walls=ws_, rooms={'R1': R(CX, CY + 32000)}), [('FS-INV-204', ['R1'])])
SL = 40 * MM
sj = {'J1': J(0, 0), 'J2': J(0, SL), 'J3': J(X, SL), 'J4': J(X, 0)}
sliver = level_doc(junctions=sj, walls={'W1': W('J2', 'J3'), 'W2': W('J4', 'J1')},
                   separators={'S1': S('J1', 'J2'), 'S2': S('J3', 'J4')})
t('rooms', 'degenerate-room', 'Two parallel 100 mm walls only 40 mm apart, closed at their ends by separators, enclose '
  'an anchored sliver: the walls\' inner faces cross, so the outer ring turns clockwise and the room polygon is '
  'degenerate.', ['6.3.3', '10.2.1'], setp(sliver, ['rooms'], {'R1': R(CX, SL // 2)}), [('FS-INV-203', ['R1'])])
t('rooms', 'degenerate-unanchored-face', 'The same sliver without a room: valid. It is an unanchored face (FS-LINT-003) '
  'and a degenerate one (FS-LINT-004), and it is not listed among the unanchored faces of derived, which lists only '
  'faces whose polygon is not degenerate.', ['6.2.1', '10.1.1'], sliver, [('FS-LINT-003', []), ('FS-LINT-004', [])])
js_, ws_ = box('', 0, 0, X, Y)
js_['F1'] = J(1000 * MM, 90 * MM)
js_['F2'] = J(3000 * MM, 90 * MM)
ws_['FW'] = W('F1', 'F2')
t('rooms', 'hole-touching-outer-ring', 'A freestanding wall 90 mm from the room\'s south wall: its body overlaps the '
  'south wall\'s, so the hole ring is not strictly inside the outer ring and the room polygon is degenerate.',
  ['6.3.3'], level_doc(junctions=js_, walls=ws_, rooms={'R1': R(CX, CY)}), [('FS-INV-203', ['R1'])])
d = room_doc()
d['slabs'] = {'SL1': {'level': 'L1', 'boundary': [[-1000 * MM, -1000 * MM], [X + 1000 * MM, -1000 * MM], [X, CY]],
                      'thickness': 150 * MM, 'offset': -150 * MM}}
t('rooms', 'slab-does-not-bound-rooms', 'A slab overlapping the room: slabs take no part in room derivation, so the '
  'room is exactly rooms/001\'s.', ['6.2.1', '6.7.1', '2.6.1'], d)
t('rooms', 'slab-thickness-zero', 'A slab\'s thickness must be greater than zero.', ['6.7.1'],
  setp(d, ['slabs', 'SL1', 'thickness'], 0), SCH)

# =================================================================================== openings
TYPES = {'WT': {'kind': 'wallType', 'layers': [{'thickness': T100, 'function': 'core'}]},
         'DT': {'kind': 'doorType', 'name': 'Door 900', 'width': 900 * MM, 'height': 2100 * MM},
         'WIN': {'kind': 'windowType', 'width': 1200 * MM, 'height': 1200 * MM, 'sill': 900 * MM}}


def od(openings, types=None):
    d = room_doc()
    d['types'] = copy.deepcopy(types or TYPES)
    d['openings'] = openings
    used = {o.get('fill') for o in openings.values()}
    for k in ('DT', 'WIN'):
        if k not in used:
            d['types'].pop(k, None)
    return d


t('openings', 'door-from-type', 'A door filled by door type DT takes its width and height from the type: it runs '
  'from 1000 mm to 1900 mm along W4 (which runs west from (X, 0)), sill 0, head 2100 mm.', ['7.2.1', '7.4.1', '8.2.1'],
  od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT'}}))
t('openings', 'door-overrides-width', 'The same door with its own width of 800 mm: the opening\'s own member wins over '
  'the type\'s.', ['7.2.1', '7.4.1', '8.2.1'], od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT', 'width': 800 * MM}}))
t('openings', 'window-sill-from-type', 'A window on W1 takes width, height and its 900 mm sill from its type.',
  ['7.2.1', '7.4.1', '8.2.1'], od({'O1': {'wall': 'W1', 'offset': 900 * MM, 'fill': 'WIN'}}))
t('openings', 'sill-zero-overrides-type', 'A window whose own "sill": 0 overrides its type\'s 900 mm: the sill is 0, '
  'and the canonical form keeps "sill": 0 because sill is a typed property.', ['8.2.1', '7.4.1', '9.2.1'],
  od({'O1': {'wall': 'W1', 'offset': 900 * MM, 'fill': 'WIN', 'sill': 0, 'height': 2100 * MM}}))
t('openings', 'empty-opening', 'An empty opening (no fill) states its own width and height; its sill defaults to 0.',
  ['7.2.1', '7.4.1', '8.2.1'], od({'O1': {'wall': 'W2', 'offset': 500 * MM, 'width': 1500 * MM, 'height': 2400 * MM}}))
t('openings', 'transom-above-door', 'A door and a transom window above it at the same offset: their intervals '
  'along the wall overlap, but the vertical ones only touch at 2100 mm, so they do not overlap.', ['7.3.3', '7.4.1'],
  od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT'},
      'O2': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'WIN', 'width': 900 * MM, 'height': 300 * MM, 'sill': 2100 * MM}}))
t('openings', 'openings-touching', 'Two doors side by side, the second starting exactly where the first ends.',
  ['7.3.3'], od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT'}, 'O2': {'wall': 'W4', 'offset': 1900 * MM, 'fill': 'DT'}}))
t('openings', 'openings-overlap', 'Two doors on W4 at 1000 mm and 1500 mm: they overlap along the wall and '
  'vertically.', ['7.3.3', '10.2.1'],
  od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT'}, 'O2': {'wall': 'W4', 'offset': 1500 * MM, 'fill': 'DT'}}),
  [('FS-INV-304', ['O1', 'O2'])])
t('openings', 'beyond-wall-length', 'A door at 3500 mm on a 4000 mm wall: it ends at 4400 mm.', ['7.3.1', '10.2.1'],
  od({'O1': {'wall': 'W4', 'offset': 3500 * MM, 'fill': 'DT'}}), [('FS-INV-302', ['O1'])])
d345 = level_doc(junctions={'J1': J(0, 0), 'J2': J(2400 * MM, 3200 * MM)}, walls={'W1': W('J1', 'J2')})
t('openings', 'fits-oblique-wall-exactly', 'A wall along (3, 4) exactly 4000 mm long, and an opening ending exactly '
  'at its end: offset + width = L is allowed.', ['7.3.1', '7.4.1'],
  setp(d345, ['openings'], {'O1': {'wall': 'W1', 'offset': 3100 * MM, 'width': 900 * MM, 'height': 2000 * MM}}))
t('openings', 'one-unit-beyond-oblique-wall', 'The same opening one base unit wider.', ['7.3.1'],
  setp(d345, ['openings'], {'O1': {'wall': 'W1', 'offset': 3100 * MM, 'width': 900 * MM + 1, 'height': 2000 * MM}}),
  [('FS-INV-302', ['O1'])])
d11 = level_doc(junctions={'J1': J(0, 0), 'J2': J(2000 * MM, 2000 * MM)}, walls={'W1': W('J1', 'J2')})
L11 = 3620386   # floor(2560000 * sqrt 2) = floor(3620386.7...)
t('openings', 'fits-irrational-length', f'A wall along (1, 1), 2000 mm by 2000 mm: its length is 2,560,000 sqrt(2) = '
  f'3,620,386.7... base units, irrational. An opening reaching {L11} fits.', ['7.3.1', '7.4.1', '2.2.1'],
  setp(d11, ['openings'], {'O1': {'wall': 'W1', 'offset': 0, 'width': L11, 'height': 2000 * MM}}))
t('openings', 'beyond-irrational-length', f'The same opening reaching {L11 + 1}: (offset + width)^2 exceeds dx^2 + dy^2.',
  ['7.3.1'], setp(d11, ['openings'], {'O1': {'wall': 'W1', 'offset': 0, 'width': L11 + 1, 'height': 2000 * MM}}),
  [('FS-INV-302', ['O1'])])
t('openings', 'above-wall-height', 'A window with sill 900 mm and height 2000 mm in a 2700 mm wall.', ['7.3.2', '10.2.1'],
  od({'O1': {'wall': 'W1', 'offset': 900 * MM, 'fill': 'WIN', 'height': 2000 * MM}}), [('FS-INV-303', ['O1'])])
t('openings', 'up-to-wall-height', 'An opening reaching exactly the wall\'s top: allowed.', ['7.3.2', '7.4.1'],
  od({'O1': {'wall': 'W1', 'offset': 900 * MM, 'width': 900 * MM, 'height': H}}))
t('openings', 'height-unresolved', 'An empty opening that states its width but not its height.', ['7.2.1', '10.2.1'],
  od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'width': 900 * MM}}), [('FS-INV-301', ['O1'])])
t('openings', 'type-without-height', 'A door type with a width and no height, filling an opening that states no '
  'height either.', ['7.2.1', '8.2.1'],
  od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT'}},
     types={**TYPES, 'DT': {'kind': 'doorType', 'width': 900 * MM}}), [('FS-INV-301', ['O1'])])
t('openings', 'negative-offset', 'An opening\'s offset is not negative.', ['7.1.1'],
  od({'O1': {'wall': 'W4', 'offset': -1, 'fill': 'DT'}}), SCH)
t('openings', 'zero-width', 'An opening\'s width is greater than zero.', ['7.1.2'],
  od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT', 'width': 0}}), SCH)
t('openings', 'zero-height', 'An opening\'s height is greater than zero.', ['7.1.2'],
  od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT', 'height': 0}}), SCH)
t('openings', 'negative-sill', 'An opening\'s sill is not negative.', ['7.1.2'],
  od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT', 'sill': -1}}), SCH)
lco = copy.deepcopy(lc)
lco['openings'] = {'O1': {'wall': 'W2', 'offset': 0, 'width': 900 * MM, 'height': 2100 * MM},
                   'O2': {'wall': 'W1', 'offset': X - 930 * MM, 'width': 900 * MM, 'height': 2100 * MM},
                   'O3': {'wall': 'W1', 'offset': 1000 * MM, 'width': 900 * MM, 'height': 2100 * MM}}
t('openings', 'opening-in-join', 'At an L corner, O1 starts at W2\'s start junction and O2 ends 30 mm short of W1\'s end '
  'junction: both reach into the part of the wall the mitre occupies, which runs 50 mm (64,000 units) from the corner, and are warned about. O3, in the middle '
  'of W1, is not.', ['7.4.1', '10.1.1'], lco, [('FS-LINT-005', ['O1']), ('FS-LINT-005', ['O2'])])
lco2 = copy.deepcopy(lco)
del lco2['openings']['O1'], lco2['openings']['O3']
lco2['openings']['O2']['offset'] = X - 950 * MM
t('openings', 'opening-clear-of-join', 'O2 ending exactly 50 mm before the corner junction - at the farther of W1\'s '
  'end face ends, measured along the location line - does not reach into the join.', ['7.4.1'], lco2)
d12 = level_doc(junctions={'J1': J(0, 0), 'J2': J(2 * 1280000, 1280000)}, walls={'W1': W('J1', 'J2')})
t('openings', 'opening-on-oblique-wall', 'A door on a wall along (2, 1): its start and end points are irrational '
  'and are rounded once; its elevations are exact.', ['7.4.1', '2.2.1'],
  setp(d12, ['openings'], {'O1': {'wall': 'W1', 'offset': 500 * MM, 'width': 900 * MM, 'height': 2100 * MM, 'sill': 15 * MM}}))
d = setp(copy.deepcopy(el), ['openings'], {'O1': {'wall': 'WC', 'offset': 500 * MM, 'width': 600 * MM, 'height': 600 * MM, 'sill': 300 * MM},
                                           'O2': {'wall': 'WD', 'offset': 500 * MM, 'width': 600 * MM, 'height': 600 * MM}})
t('openings', 'elevations-follow-wall-base', 'Openings measure their sill from their wall\'s base: in WC (base 100 '
  'mm) a 300 mm sill is at 400 mm; in WD (based on L2 at 3000 mm) a sill of 0 is at 3000 mm.', ['7.4.1', '5.9.3'], d)
d = od({'O1': {'wall': 'W4', 'offset': 1000 * MM, 'fill': 'DT', 'hinge': 'end', 'swing': 'left'},
        'O2': {'wall': 'W2', 'offset': 1000 * MM, 'fill': 'DT', 'hinge': 'start', 'swing': 'right'}})
t('openings', 'hinge-and-swing', 'Two doors: O1 hinged at the end and swinging left keeps both members in canonical '
  'form; O2 states the defaults, which canonical form omits. Neither changes placement.', ['9.2.1', '7.4.1'], d)

# =================================================================================== types
d = room_doc()
d['walls']['W1']['layers'] = [{'thickness': 200 * MM, 'function': 'core'}]
t('types', 'wall-layers-override-type', 'Wall W1 keeps its type WT (100 mm) but states its own layers (200 mm): its '
  'own layers replace the type\'s entirely, so W1 is 200 mm thick and the room is narrower on that side.',
  ['8.2.1', '5.4.1', '5.7.1', '6.2.1'], d)
d = room_doc()
for w in d['walls'].values():
    del w['type']
    w['layers'] = [{'thickness': T100, 'function': 'core'}]
del d['types']
t('types', 'wall-layers-without-type', 'Every wall states its own layers and has no type: the same room as '
  'rooms/001, with the same derived values.', ['8.2.1', '5.4.1'], d)
t('types', 'unknown-kind', '"roofType" is not a type kind in this draft.', ['8.1.1'],
  setp(room_doc(), ['types', 'RT'], {'kind': 'roofType'}), SCH)
t('types', 'missing-kind', 'A type without a kind.', ['8.1.1'],
  setp(room_doc(), ['types', 'WT'], {'layers': [{'thickness': T100, 'function': 'core'}]}), SCH)
t('types', 'door-type-with-layers', 'A door type has no layers: members follow the kind.', ['8.1.1', '1.4.1'],
  setp(room_doc(), ['types', 'DT'], {'kind': 'doorType', 'width': 900 * MM, 'layers': []}), SCH)
t('types', 'empty-layers', 'A wall type with no layers.', ['8.3.1'], setp(room_doc(), ['types', 'WT', 'layers'], []), SCH)
t('types', 'zero-thickness-layer', 'A layer of zero thickness - a membrane is thin, but not that thin.', ['8.3.1'],
  setp(room_doc(), ['types', 'WT', 'layers'], [{'thickness': T100, 'function': 'core'}, {'thickness': 0, 'function': 'membrane'}]), SCH)
t('types', 'wall-own-layers-empty', 'A wall\'s own layers follow the same rules: an empty array is invalid (it does '
  'not mean "no override").', ['8.3.1'], setp(room_doc(), ['walls', 'W1', 'layers'], []), SCH)
t('types', 'door-type-zero-width', 'A door type\'s width, when present, is greater than zero.', ['8.4.1'],
  setp(room_doc(), ['types', 'DT'], {'kind': 'doorType', 'width': 0, 'height': 2100 * MM}), SCH)
t('types', 'window-type-negative-sill', 'A window type\'s sill is not negative.', ['8.4.1'],
  setp(room_doc(), ['types', 'WIN'], {'kind': 'windowType', 'sill': -1}), SCH)
t('types', 'door-type-zero-height', 'A door type\'s height, when present, is greater than zero.', ['8.4.1'],
  setp(room_doc(), ['types', 'DT'], {'kind': 'doorType', 'height': 0}), SCH)
MAT = level_doc(materials={'M1': {'color': '#a0522d'}})
t('types', 'color-uppercase', 'Colours are lowercase hexadecimal.', ['8.5.1'], setp(MAT, ['materials', 'M1', 'color'], '#A0522D'), SCH)
t('types', 'color-short-form', '"#fff" is not #rrggbb.', ['8.5.1'], setp(MAT, ['materials', 'M1', 'color'], '#fff'), SCH)
ASSET = {'path': 'textures/oak.png', 'sha256': 'ab' * 32, 'mediaType': 'image/png'}
TEX = level_doc(materials={'M1': {'texture': {'asset': 'A1', 'size': [300 * MM, 1200 * MM]}}}, assets={'A1': dict(ASSET)})
t('types', 'texture-size-zero', 'A texture tile has positive size.', ['8.5.2'],
  setp(TEX, ['materials', 'M1', 'texture', 'size'], [0, 1200 * MM]), SCH)
t('types', 'texture-size-one-number', 'A texture size is two lengths.', ['8.5.2'],
  setp(TEX, ['materials', 'M1', 'texture', 'size'], [300 * MM]), SCH)
t('types', 'asset-path-and-uri', 'An asset has exactly one of path and uri: not both.', ['8.6.1'],
  setp(TEX, ['assets', 'A1', 'uri'], 'https://example.com/oak.png'), SCH)
t('types', 'asset-neither-path-nor-uri', '...and not neither.', ['8.6.1'], drop(TEX, ['assets', 'A1', 'path']), SCH)
for p, why in (('../oak.png', 'a ".." segment'), ('/textures/oak.png', 'an absolute path'), ('textures//oak.png', 'an empty segment'),
               ('./oak.png', 'a "." segment'), ('textures\\oak.png', 'a backslash separator'), ('C:/oak.png', 'a colon in its first segment'),
               ('textures/', 'a trailing slash (an empty last segment)')):
    slug = {'../oak.png': 'asset-path-dot-dot', '/textures/oak.png': 'asset-path-absolute', 'textures//oak.png': 'asset-path-empty-segment',
            './oak.png': 'asset-path-dot', 'textures\\oak.png': 'asset-path-backslash', 'C:/oak.png': 'asset-path-colon',
            'textures/': 'asset-path-trailing-slash'}[p]
    t('types', slug, f'An asset path with {why}.', ['8.6.2'], setp(TEX, ['assets', 'A1', 'path'], p), SCH)
t('types', 'asset-uri-not-https', 'An asset URI uses https.', ['1.4.4'],
  setp(drop(TEX, ['assets', 'A1', 'path']), ['assets', 'A1', 'uri'], 'http://example.com/oak.png'), SCH)
d = room_doc()
d['types']['DT'] = {'kind': 'doorType', 'name': 'Unused door', 'width': 900 * MM, 'height': 2100 * MM, 'extras': {'sku': 'D-900'}}
d['materials'] = {'OAK': {'name': 'White oak', 'color': '#c8a165', 'texture': {'asset': 'A1', 'size': [150 * MM, 1200 * MM]}},
                  'TILE': {'texture': {'asset': 'A2', 'size': [300 * MM, 300 * MM]}},
                  'SPARE': {'color': '#ffffff'}}
d['assets'] = {'A1': {'path': 'textures/oak floor.png', 'sha256': 'ab' * 32, 'mediaType': 'image/png'},
               'A2': {'uri': 'https://example.com/tile%20grey.jpg', 'sha256': 'cd' * 32, 'mediaType': 'image/jpeg'},
               'A3': {'path': 'a:b/../x', 'sha256': 'ef' * 32, 'mediaType': 'image/webp'}}
d['assets']['A3']['path'] = 'spare/x:y.webp'
d['rooms']['R1'].update(floorFinish='OAK', wallFinish='TILE', name='Bath', function='bath')
t('types', 'materials-and-assets', 'Materials with a colour and textures, assets by path (with a space and, after the '
  'first segment, a colon) and by URI: valid. The lints name the unused door type, material and asset (FS-LINT-006) '
  'and the asset located by URI (FS-LINT-007).', ['8.1.1', '8.5.1', '8.5.2', '8.6.1', '8.6.2', '10.1.1'], d,
  [('FS-LINT-006', ['A3']), ('FS-LINT-006', ['DT']), ('FS-LINT-006', ['SPARE']), ('FS-LINT-007', ['A2'])])

# =================================================================================== serialization
b = baseline()
good = (fmt(b) + '\n').encode()
t('serialization', 'malformed-trailing-comma', 'A trailing comma is not JSON.', ['9.1.1', '10.2.1'], None,
  [('FS-JSON-001', [])], raw=good.replace(b'"name": "Conformance"', b'"name": "Conformance",'))
t('serialization', 'byte-order-mark', 'A document that begins with a UTF-8 byte order mark.', ['9.1.1'], None,
  [('FS-JSON-001', [])], raw=b'\xef\xbb\xbf' + good)
t('serialization', 'not-utf-8', 'A project name containing the byte 0xE9 (Latin-1 "e acute"), which is not UTF-8.',
  ['9.1.1'], None, [('FS-JSON-001', [])], raw=good.replace(b'"Conformance"', b'"Conformance caf\xe9"'))
t('serialization', 'empty-file', 'An empty file is not a JSON text.', ['9.1.1'], None, [('FS-JSON-001', [])], raw=b'')
t('serialization', 'single-quotes', 'JSON strings use double quotes.', ['9.1.1'], None, [('FS-JSON-001', [])],
  raw=good.replace(b'"floorspec": "0.1"', b"'floorspec': '0.1'"))
t('serialization', 'duplicate-member', 'The wall W1 has "type" twice. Parsers that keep the last copy and parsers that '
  'keep the first would read different buildings, so the document is rejected.', ['9.1.2', '10.2.1'], None,
  [('FS-JSON-002', [])], raw=good.replace(b'"type": "WT"', b'"type": "WT", "type": "WT"', 1))
t('serialization', 'duplicate-member-escaped', '"name" and "n\\u0061me" are the same member name once unescaped.',
  ['9.1.2'], None, [('FS-JSON-002', [])], raw=good.replace(b'"name": "Conformance"', b'"name": "Conformance", "n\\u0061me": "Other"'))
t('serialization', 'duplicate-collection-member', 'Two rooms with the same ID: the second R1 is a duplicate member '
  'of the rooms object.', ['9.1.2'], None, [('FS-JSON-002', [])],
  raw=good.replace(b'"rooms": {', b'"rooms": {\n    "R1": {"level": "L1", "anchor": [1, 1]},', 1))
t('serialization', 'unpaired-high-surrogate', 'A room name containing the escape \\ud83c with no low surrogate after '
  'it.', ['9.1.3', '10.2.1'], None, [('FS-JSON-003', [])],
  raw=good.replace(b'"anchor": [', b'"name": "Den \\ud83c", "anchor": [', 1))
t('serialization', 'unpaired-low-surrogate', 'An extras string containing a lone low surrogate \\udfe0.', ['9.1.3'], None,
  [('FS-JSON-003', [])], raw=good.replace(b'"name": "Conformance"', b'"name": "Conformance", "extras": {"x": "\\udfe0"}'))
pair = fmt(setp(b, ['rooms', 'R1', 'name'], 'Den \U0001F3E0'))
t('serialization', 'surrogate-pair', 'A properly paired escape \\ud83c\\udfe0 is one character, U+1F3E0, written '
  'literally in canonical form.', ['9.1.3', '9.2.1'], None, raw=(pair.replace('\U0001F3E0', '\\ud83c\\udfe0') + '\n').encode())

shuffled = {'walls': {k: dict(reversed(list(v.items()))) for k, v in reversed(list(b['walls'].items()))},
            'rooms': b['rooms'], 'openings': {'O1': dict(reversed(list(b['openings']['O1'].items())))},
            'junctions': dict(reversed(list(b['junctions'].items()))), 'types': b['types'], 'project': b['project'],
            'levels': b['levels'], 'floorspec': '0.1', 'buildings': b['buildings']}
raw_a = fmt(shuffled, indent=4).replace('\n', '\n\t ').replace(': ', ' :  ') + '\n\n'
t('serialization', 'member-order-and-whitespace', 'The baseline model (model/017) with every object\'s members in a '
  'different order, four-space and tab indentation and spaces before colons. Its canonical form, hash and derived '
  'values are exactly model/017\'s.', ['9.2.1', '9.2.2', '9.3.1'], None, raw=raw_a.encode())
t('serialization', 'one-line-crlf', 'The baseline model minified onto one line, then with CR LF line breaks between '
  'members: whitespace is not content. Same canonical form and hash as model/017.', ['9.2.1', '9.3.1'], None,
  raw=json.dumps(b, separators=(',', ':')).replace(',"', ',\r\n"').encode() + b'\r\n')
cd = baseline()
for w in cd['walls'].values():
    w['justification'] = 'center'
    w['base'] = {'offset': 0}
cd['junctions']['J1']['join'] = {'kind': 'mitre'}
cd['openings']['O1'].update(hinge='start', swing='right', extras={}, extensions={})
cd['rooms']['R1']['function'] = 'unspecified'
cd['project']['extras'] = {}
cd['site'] = {'trueNorth': 0, 'extras': {}}
cd.update(slabs={}, separators={}, extensionsRequired=[], extensionsUsed={}, extensions={}, extras={})
t('serialization', 'constant-defaults-removed', 'Every constant default present, including an empty site with '
  'trueNorth 0 and base {"offset": 0} (omitted innermost first, so base disappears entirely): canonical form removes '
  'them all except the site, whose default is absent rather than {}.', ['9.2.1', '9.2.2', '1.5.1'], cd)
kd = baseline()
kd['levels']['L2'] = {'building': 'B1', 'elevation': 3000 * MM, 'height': H}
kd['walls']['W1']['base'] = {'level': 'L1', 'offset': 0}
kd['walls']['W2']['top'] = {'level': 'L2', 'offset': 0}
kd['walls']['W3']['layers'] = [{'thickness': T100, 'function': 'core'}]
kd['openings']['O1']['sill'] = 0
kd['types']['WIN'] = {'kind': 'windowType', 'sill': 0}
kd['openings']['O2'] = {'wall': 'W2', 'offset': 1000 * MM, 'fill': 'WIN', 'width': 1000 * MM, 'height': 1000 * MM, 'sill': 0}
t('serialization', 'typed-and-derived-defaults-kept', 'Members that look like defaults but are not constant defaults '
  'are kept: base.level naming the wall\'s own level (a derived default), a top at L2 with offset 0 (only the offset '
  'goes), a wall\'s own layers equal to its type\'s, and "sill": 0 on two openings - typed properties are never '
  'omitted.', ['9.2.1', '9.2.2', '8.2.1'], kd)
xd = baseline()
xd['extensionsUsed'] = {'EXT_acoustics': '1.0'}
xd['extensions'] = {'EXT_acoustics': {'z': {}, 'a': [], 'nested': {'justification': 'center', 'extras': {}}, 'n': 1.50,
                                      'e': 1e2, 'neg0': -0.0, 'tiny': 0.000001, 'tinier': 1e-7, 'big': 12345678901234567890,
                                      'text': 'line\nbreak \u00e9 \u2028 / \\ "q"', 'nul': None, 't': True}}
xd['extras'] = {'defaults': {'kind': 'mitre'}, 'emptyObj': {}, 'emptyArr': []}
xd['walls']['W1']['extras'] = {}
xd['walls']['W2']['extras'] = {'k': {}}
raw_x = fmt(xd) + '\n'
raw_x = raw_x.replace('"e": 100.0', '"e": 1E2').replace('"n": 1.5', '"n": 1.50').replace('"neg0": -0.0', '"neg0": -0')
raw_x = raw_x.replace('"tinier": 1e-07', '"tinier": 1e-7')
t('serialization', 'extension-data-and-extras-preserved', 'Extension data and extras keep their content exactly - '
  'empty objects and arrays inside them, members named like core defaults, null and booleans - while canonical form '
  'only sorts their members and writes their numbers and strings as RFC 8785 does: 1.50 as 1.5, 1E2 as 100, -0 as 0, '
  '1e-7 as 1e-7, 12345678901234567890 as 12345678901234567000. An element\'s empty extras is removed; a non-empty one '
  'stays. None of it is read by derivation: the derived values are exactly model/017\'s.',
  ['1.6.5', '1.6.6', '1.7.1', '1.7.2', '9.2.1', '9.3.1'], None, raw=raw_x.encode())
ud = baseline()
ud['project']['name'] = 'Caf\u00e9 \U0001F3E0 \uFB01'
ud['extras'] = {'\U0001F600': 1, '\uFB01': 2, 'b': 3, 'B': 4, '\u00e9': 5, 'a\u0000': 6, 'a': 7, '\u007f': 8}
raw_u = (fmt(ud) + '\n').replace('Caf\u00e9', 'Caf\\u00e9').replace('"a\\u0000"', '"a\\u0000"')
t('serialization', 'member-order-utf-16', 'Members are sorted by UTF-16 code units, not code points: U+1F600 (the '
  'surrogates 0xD83D 0xDE00) sorts before U+FB01 (one unit, 0xFB01) although its code point is larger; capitals sort '
  'before lowercase, "a" before "a\\u0000", and U+007F after "b". An escaped \\u00e9 in the input is written '
  'literally, U+007F literally, and U+0000 as \\u0000.', ['9.2.1', '9.3.1'], None, raw=raw_u.encode())
t('serialization', 'escapes-normalized', 'Strings with escapes that canonical form writes differently: \\/ becomes /, '
  '\\u0041 becomes A, and a control character U+001F stays escaped, as \\u001f.', ['9.2.1'], None,
  raw=good.replace(b'"name": "Conformance"', b'"name": "Con\\/form\\u0041nce\\u001F"'))

# =================================================================================== diagnostics
d = level_doc(junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(CX, -CY), 'J4': J(CX, CY)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J3', 'J9')})
t('diagnostics', 'reference-error-stops-invariants', 'A dangling reference (W2 ends at J9) and walls that would cross: '
  'once a reference invariant is reported no other invariant is evaluated, so only FS-INV-002 is reported.',
  ['10.3.1', '3.2.1', '10.2.1'], d, [('FS-INV-002', ['W2'])])
d = level_doc(levels={'L2': {'building': 'B1', 'elevation': H, 'height': H}},
              junctions={'J1': J(0, 0), 'J2': J(X, 0), 'J3': J(CX, -CY), 'J4': J(CX, CY)},
              walls={'W1': W('J1', 'J2'), 'W2': W('J3', 'J4')}, rooms={'R1': R(-X, 0)})
kj, kw = box('K', 0, 0, X, Y, level='L2')
d['junctions'].update(kj)
d['walls'].update(kw)
d['rooms'].update({'R2': R(CX, CY, level='L2'), 'R3': R(-X, 0, level='L2')})
t('diagnostics', 'graph-error-stops-rooms-on-its-level', 'On L1 two walls cross (FS-INV-104), so L1\'s room '
  'invariants are not evaluated - R1, anchored outside, is not reported. L2 has no graph error: its rooms are '
  'checked, and R3, anchored outside, is reported.', ['10.3.1', '5.3.1', '6.3.1'], d,
  [('FS-INV-104', ['W1', 'W2']), ('FS-INV-201', ['R3'])])
d = room_doc()
d['walls']['W1']['top'] = {'height': 0}
d['rooms']['R2'] = R(-X, 0)
t('diagnostics', 'top-error-does-not-stop-rooms', 'FS-INV-112 is the one graph invariant that does not stop the room '
  'invariants of its level: W1\'s top is not above its base, and R2, anchored outside, is still reported.',
  ['10.3.1', '5.9.2', '6.3.1'], d, [('FS-INV-112', ['W1']), ('FS-INV-201', ['R2'])])
d = room_doc()
d['walls']['W1']['thickness'] = T100
d['walls']['W2']['end'] = 'J9'
t('diagnostics', 'schema-error-stops-invariants', 'A schema error (an unknown wall member) and a dangling reference: '
  'only FS-SCH-001, because invariants are evaluated only when the schema tier passed.', ['10.3.1', '1.4.1'], d, SCH)
d = doc(floorspec='0.2', furniture={})
t('diagnostics', 'document-error-stops-schema', 'A version this reader does not implement and an unknown top-level '
  'member: only FS-DOC-001.', ['10.3.1', '1.2.2'], d, [('FS-DOC-001', [])])
dd = room_doc()
dd['walls']['W2']['end'] = 'J9'
t('diagnostics', 'parse-error-stops-everything', 'A duplicate member, a dangling reference and an unknown member: '
  'only FS-JSON-002.', ['10.3.1', '9.1.2'], None, [('FS-JSON-002', [])],
  raw=(fmt(dd) + '\n').replace('"level": "L1",', '"level": "L1", "level": "L1", "colour": "red",', 1).encode())
d = room_doc()
d['junctions']['J9'] = J(-X, -Y)
d['rooms']['R1']['anchor'] = [-X, 0]
t('diagnostics', 'lints-only-for-valid-documents', 'An unused junction (a lint) in a document with an error: lints '
  'are evaluated only for a valid document, so FS-LINT-002 is not reported.', ['10.3.1', '10.1.1'], d,
  [('FS-INV-201', ['R1'])])
d = od({'O1': {'wall': 'W4', 'offset': 3500 * MM, 'width': 900 * MM},
        'O2': {'wall': 'W4', 'offset': 3200 * MM, 'width': 600 * MM, 'height': 2100 * MM}})
t('diagnostics', 'unresolved-opening-skips-placement', 'O1 has no height and would also run past the wall\'s end '
  'and overlap O2: FS-INV-302, -303 and -304 are evaluated only for openings without FS-INV-301, so only FS-INV-301 '
  'is reported.', ['10.3.1', '7.2.1'], d, [('FS-INV-301', ['O1'])])
t('diagnostics', 'merged-face-skips-degeneracy', 'Two rooms anchored in one degenerate sliver: FS-INV-203 and -204 '
  'are evaluated only for rooms without FS-INV-201 or -202, so only FS-INV-202 is reported.', ['10.3.1', '6.3.2'],
  setp(sliver, ['rooms'], {'R1': R(CX, SL // 2), 'R2': R(CX + 1000 * MM, SL // 2)}), [('FS-INV-202', ['R1', 'R2'])])
d = copy.deepcopy(setp(level_doc(), ['types', 'THICK'], {'kind': 'wallType', 'layers': [{'thickness': T200, 'function': 'core'}]}))
del d['types']['WT']
stub = no_wt(level_doc(types={'THICK': {'kind': 'wallType', 'layers': [{'thickness': T200, 'function': 'core'}]}},
                       junctions={'J1': J(0, 0), 'J2': J(50 * MM, 0), 'J3': J(0, 2000 * MM), 'J4': J(50 * MM, 2000 * MM),
                                  'J5': J(X, 0), 'J6': J(X + 1000 * MM, 0), 'J7': J(X + 500 * MM, -500 * MM), 'J8': J(X + 500 * MM, 500 * MM)},
                       walls={'W1': W('J3', 'J1', type='THICK'), 'W2': W('J1', 'J2', type='THICK'), 'W3': W('J2', 'J4', type='THICK'),
                              'W4': W('J5', 'J6', type='THICK'), 'W5': W('J7', 'J8', type='THICK')}))
t('diagnostics', 'graph-error-stops-join-invariants', 'walls/039\'s stub W2, whose outline is not simple, on a level '
  'where W4 and W5 also cross: join invariants are not evaluated on a level with a graph error, so only FS-INV-104 '
  'is reported.', ['10.3.1', '5.3.1'], stub, [('FS-INV-104', ['W4', 'W5'])])
d = od({'O1': {'wall': 'W1', 'offset': 900 * MM, 'fill': 'WIN', 'height': 2000 * MM}})
d['walls']['W1']['top'] = {'height': -100 * MM}
t('diagnostics', 'top-error-skips-height-check', 'W1\'s top is below its base, and its window would rise above it: '
  'FS-INV-303 is not evaluated for an opening whose wall has FS-INV-112.', ['10.3.1', '5.9.2'], d, [('FS-INV-112', ['W1'])])
d = od({'O1': {'wall': 'W4', 'offset': 3500 * MM, 'fill': 'DT'}})
d['junctions']['J9'] = J(CX, -CY)
d['junctions']['J8'] = J(CX, CY)
d['walls']['W9'] = W('J9', 'J8')
t('diagnostics', 'graph-error-does-not-stop-openings', 'W9 crosses the room\'s south wall W4, and a door runs past '
  'the end of W4: opening invariants are evaluated for every opening, so FS-INV-302 is reported with the crossing; '
  'the room invariants of the level are not evaluated.', ['10.3.1', '7.3.1', '5.3.1'], d,
  [('FS-INV-104', ['W4', 'W9']), ('FS-INV-302', ['O1'])])
d = copy.deepcopy(room_doc())
d['walls']['W1']['top'] = {'height': 0}
d['walls']['W3']['top'] = {'level': 'L1', 'offset': -1}
d['junctions']['J9'] = J(0, 0)
t('diagnostics', 'diagnostics-sorted', 'Three errors, listed sorted by code and then by elements: FS-INV-101 before '
  'FS-INV-112, and the two FS-INV-112 by wall ID.', ['10.2.1', '10.3.1'], d,
  [('FS-INV-101', ['J1', 'J9']), ('FS-INV-112', ['W1']), ('FS-INV-112', ['W3'])])
lint = room_doc()
del lint['rooms']
lint['junctions'].update({'A1': J(-3 * X, 0), 'A2': J(-2 * X, 0), 'A3': J(-2 * X, 1000 * MM), 'U1': J(-3 * X, -Y)})
lint['walls'].update({'AW1': W('A2', 'A1'), 'AW2': W('A1', 'A3')})
lint['junctions']['A3']['position'] = [-2 * X, 900 * MM]
lint['openings'] = {'O1': {'wall': 'W4', 'offset': 0, 'width': 900 * MM, 'height': 2100 * MM}}
lint['types']['DT'] = {'kind': 'doorType', 'width': 900 * MM, 'height': 2100 * MM}
lint['materials'] = {'TILE': {'texture': {'asset': 'IMG', 'size': [300 * MM, 300 * MM]}}}
lint['assets'] = {'IMG': {'uri': 'https://example.com/tile.png', 'sha256': '12' * 32, 'mediaType': 'image/png'}}
sj2 = {f'S{k}': J(v['position'][0], v['position'][1] - 2 * Y) for k, v in sj.items()}
lint['junctions'].update(sj2)
lint['walls'].update({'SW1': W('SJ2', 'SJ3'), 'SW2': W('SJ4', 'SJ1')})
lint['separators'] = {'SS1': S('SJ1', 'SJ2'), 'SS2': S('SJ3', 'SJ4')}
t('diagnostics', 'every-lint', 'A valid document with one of every lint: an acute join (A1, AW1, AW2), an unused '
  'junction (U1), two unanchored faces - the room and a degenerate sliver - with the sliver also degenerate, an '
  'opening in a join (O1), an unused door type and material (FS-LINT-006), and an asset located by URI.',
  ['10.1.1', '10.2.1'], lint,
  [('FS-LINT-001', ['A1', 'AW1', 'AW2']), ('FS-LINT-002', ['U1']), ('FS-LINT-003', []), ('FS-LINT-003', []),
   ('FS-LINT-004', []), ('FS-LINT-005', ['O1']), ('FS-LINT-006', ['DT']), ('FS-LINT-006', ['TILE']), ('FS-LINT-007', ['IMG'])])

# =================================================================================== examples
house_types = {
    'EXT26': {'kind': 'wallType', 'name': '2x6 exterior wall', 'layers': [
        {'thickness': 24384, 'function': 'finish', 'material': 'SIDING'},       # 3/4 in fibre-cement lap siding
        {'thickness': 14224, 'function': 'substrate', 'material': 'OSB'},       # 7/16 in OSB sheathing
        {'thickness': 178816, 'function': 'core', 'material': 'STUD'},         # 2x6 studs, 5-1/2 in
        {'thickness': 16256, 'function': 'finish', 'material': 'GWB'}]},        # 1/2 in drywall
    'INT24': {'kind': 'wallType', 'name': '2x4 partition', 'layers': [
        {'thickness': 16256, 'function': 'finish', 'material': 'GWB'},
        {'thickness': 113792, 'function': 'core', 'material': 'STUD'},          # 2x4 studs, 3-1/2 in
        {'thickness': 16256, 'function': 'finish', 'material': 'GWB'}]},
    'D36': {'kind': 'doorType', 'name': '36 in entry door', 'width': 36 * IN, 'height': 80 * IN},
    'D32': {'kind': 'doorType', 'name': '32 in interior door', 'width': 32 * IN, 'height': 80 * IN},
    'W4848': {'kind': 'windowType', 'name': '48 x 48 in window', 'width': 48 * IN, 'height': 48 * IN, 'sill': 36 * IN},
    'W3636': {'kind': 'windowType', 'name': '36 x 36 in window', 'width': 36 * IN, 'height': 36 * IN, 'sill': 42 * IN},
}
house = {
    'floorspec': '0.1',
    'project': {'name': 'Three-room house', 'extras': {}},
    'site': {'trueNorth': -12_500_000, 'location': {'latitude': 42_360_100, 'longitude': -71_058_900}},
    'buildings': {'HOUSE': {'name': 'House'}},
    'levels': {'MAIN': {'name': 'Main floor', 'building': 'HOUSE', 'elevation': 0, 'height': 9 * FT}},
    'walls': {
        'WW': {'level': 'MAIN', 'start': 'C1', 'end': 'C2', 'type': 'EXT26', 'justification': 'coreFace', 'base': {'offset': 0}},
        'WN1': {'level': 'MAIN', 'start': 'C2', 'end': 'TN', 'type': 'EXT26', 'justification': 'coreFace'},
        'WN2': {'level': 'MAIN', 'start': 'TN', 'end': 'C3', 'type': 'EXT26', 'justification': 'coreFace'},
        'WE1': {'level': 'MAIN', 'start': 'C3', 'end': 'TE', 'type': 'EXT26', 'justification': 'coreFace'},
        'WE2': {'level': 'MAIN', 'start': 'TE', 'end': 'C4', 'type': 'EXT26', 'justification': 'coreFace'},
        'WS1': {'level': 'MAIN', 'start': 'C4', 'end': 'TS', 'type': 'EXT26', 'justification': 'coreFace'},
        'WS2': {'level': 'MAIN', 'start': 'TS', 'end': 'C1', 'type': 'EXT26', 'justification': 'coreFace', 'extras': {}},
        'WI1': {'level': 'MAIN', 'start': 'TS', 'end': 'TM', 'type': 'INT24', 'justification': 'center'},
        'WI2': {'level': 'MAIN', 'start': 'TM', 'end': 'TE', 'type': 'INT24'},
    },
    'junctions': {
        'C1': {'level': 'MAIN', 'position': [0, 0], 'name': 'SW corner'},
        'C2': {'level': 'MAIN', 'position': [0, 24 * FT], 'join': {'kind': 'mitre'}},
        'C3': {'level': 'MAIN', 'position': [36 * FT, 24 * FT]},
        'C4': {'level': 'MAIN', 'position': [36 * FT, 0]},
        'TN': {'level': 'MAIN', 'position': [20 * FT, 24 * FT], 'join': {'kind': 'butt', 'through': ['WN1', 'WN2']}},
        'TS': {'level': 'MAIN', 'position': [20 * FT, 0], 'join': {'kind': 'butt', 'through': ['WS1', 'WS2']}},
        'TE': {'level': 'MAIN', 'position': [36 * FT, 12 * FT], 'join': {'kind': 'butt', 'through': ['WE1', 'WE2']}},
        'TM': {'level': 'MAIN', 'position': [20 * FT, 12 * FT]},
    },
    'separators': {'SK': {'level': 'MAIN', 'start': 'TM', 'end': 'TN', 'name': 'Kitchen counter line'}},
    'rooms': {
        'LIV': {'level': 'MAIN', 'anchor': [10 * FT, 12 * FT], 'name': 'Living room', 'function': 'living', 'floorFinish': 'OAK'},
        'KIT': {'level': 'MAIN', 'anchor': [28 * FT, 18 * FT], 'name': 'Kitchen', 'function': 'kitchen', 'floorFinish': 'TILE'},
        'BED': {'level': 'MAIN', 'anchor': [28 * FT, 6 * FT], 'name': 'Bedroom', 'function': 'sleeping', 'floorFinish': 'OAK',
                'wallFinish': 'PAINT'},
    },
    'openings': {
        'FD': {'wall': 'WS2', 'offset': 6 * FT, 'fill': 'D36', 'hinge': 'start', 'swing': 'left', 'name': 'Front door'},
        'LW1': {'wall': 'WW', 'offset': 8 * FT, 'fill': 'W4848'},
        'LW2': {'wall': 'WN1', 'offset': 6 * FT, 'fill': 'W4848', 'width': 72 * IN, 'name': 'Picture window'},
        'KW': {'wall': 'WN2', 'offset': 6 * FT, 'fill': 'W3636'},
        'BW': {'wall': 'WE2', 'offset': 3 * FT, 'fill': 'W4848', 'swing': 'right'},
        'BD': {'wall': 'WI1', 'offset': 8 * FT, 'fill': 'D32', 'hinge': 'end', 'swing': 'right'},
    },
    'types': house_types,
    'materials': {
        'SIDING': {'name': 'Fibre-cement lap siding', 'color': '#5b6d7a'},
        'OSB': {'name': 'OSB sheathing', 'color': '#c9a66b'},
        'STUD': {'name': 'SPF framing', 'color': '#e8d3a3'},
        'GWB': {'name': 'Gypsum board', 'color': '#f2f0eb'},
        'PAINT': {'name': 'Eggshell paint, "Sea Salt"', 'color': '#cdd2ca'},
        'OAK': {'name': 'White oak strip', 'texture': {'asset': 'OAKIMG', 'size': [3 * IN, 48 * IN]}},
        'TILE': {'name': 'Porcelain tile 12 x 24', 'color': '#d9d6d0'},
    },
    'assets': {'OAKIMG': {'path': 'textures/white-oak.png', 'mediaType': 'image/png',
                          'sha256': '3f6c2a8e9d1b4c7f0a5e8d2b6c9f1a4e7d0b3c6f9a2e5d8b1c4f7a0e3d6b9c2f'}},
    'extras': {'author': {'tool': 'hand-written for FLR-T-1.12'}},
}
raw_h = fmt(house, indent=4).replace('\n            "', '\n            "', ) + '\n'
t('examples', 'three-room-house', 'The Phase 1 exit demo: a 36 by 24 ft single-storey house of 2x6 exterior walls '
  '(siding, OSB, studs, drywall; justified on the exterior face of the studs and drawn clockwise) and 2x4 partitions. '
  'A living room open to the kitchen across a separator, a bedroom behind a partition, a front door, an interior door '
  'and four windows. Dimensions are feet and inches in base units (1 ft = 390,144, 1 in = 32,512). The exterior '
  'tees are butt joins with the exterior walls running through; the corners and the interior tee are mitred. The '
  'input is deliberately not canonical - member order, four-space indentation, constant defaults written out - so '
  'canonical.json is a real re-serialization.',
  ['5.6.1', '5.7.1', '5.7.3', '5.8.4', '5.9.3', '6.2.1', '6.4.1', '7.4.1', '8.2.1', '9.2.1', '9.2.2', '9.3.1'],
  None, [], raw=raw_h.encode())

# =================================================================================== added after the first release
# New tests go at the end, so that existing test directories keep their numbers.
t('model', 'two-required-extensions-unimplemented', 'Two declared required extensions the reader does not implement: '
  'one FS-DOC-002 for each.', ['1.6.4', '10.2.1'],
  doc(extensionsUsed={'EXT_acoustics': '1.0', 'EXT_wellness': '2.0'}, extensionsRequired=['EXT_acoustics', 'EXT_wellness']),
  [('FS-DOC-002', []), ('FS-DOC-002', [])])

t('model', 'project-description', 'A project with a description of exactly 2000 characters: valid, and kept in '
  'canonical form.', ['1.4.4', '9.2.1'], doc(project={'name': 'Conformance', 'description': 'A house. ' * 222 + 'xx'}))
t('model', 'project-description-too-long', 'A project description of 2001 characters.', ['1.4.4'],
  doc(project={'name': 'Conformance', 'description': 'A house. ' * 222 + 'xxx'}), SCH)
t('model', 'two-undeclared-extensions', 'Top-level data for two undeclared extensions: one FS-INV-005 for each name.',
  ['1.6.3', '10.2.1'], doc(extensions={'EXT_acoustics': {}, 'EXT_wellness': {}}), [('FS-INV-005', []), ('FS-INV-005', [])])

d = tj({'kind': 'butt', 'through': ['W1']})
d['walls']['W3'] = W('JS', 'J0', type=None)
t('joins', 'join-not-checked-without-layers', 'joins/015\'s inapplicable one-through join, at a junction where W3 '
  'has no effective layers: FS-INV-111 is not evaluated for a junction with a wall that has FS-INV-107, so only '
  'FS-INV-107 is reported.', ['10.3.1', '5.4.1'], d, [('FS-INV-107', ['W3'])])

d = setp(fw, ['junctions', 'J3'], J(0, 0))
d['junctions']['J4'] = J(0, 0)
t('walls', 'three-junctions-share-a-position', 'Three junctions at one position: FS-INV-101 is pairwise, so it is '
  'reported once for each of the three pairs.', ['5.1.1', '10.2.1'], d,
  [('FS-INV-101', ['J1', 'J3']), ('FS-INV-101', ['J1', 'J4']), ('FS-INV-101', ['J3', 'J4'])])

d = room_doc()
d['rooms']['R1'].update(floorFinish='OAK', wallFinish='PAINT')
t('identity', 'two-dangling-references-in-one-element', 'A room whose floor and wall finishes both name missing '
  'materials: one FS-INV-002 for each unresolved reference, both naming the room.', ['3.2.1', '10.2.1'], d,
  [('FS-INV-002', ['R1']), ('FS-INV-002', ['R1'])])

if __name__ == '__main__':
    sys.exit(1 if write_all(prune='--prune' in sys.argv) else 0)

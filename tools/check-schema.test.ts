import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { checkSuite, createAjv, defaults, formatErrors, parseForSchema, rootValidator, undefinedRequired, validateText } from './schema.ts';

const validate = rootValidator(createAjv());

function check(text: string) {
  return validateText(text, validate);
}

/** Asserts that the schema accepts a document (an object, or a JSON text written as-is). */
function accepts(doc: unknown) {
  const r = check(typeof doc === 'string' ? doc : JSON.stringify(doc));
  assert.ok(r.valid, `expected the schema to accept, got:\n${formatErrors(r.errors).join('\n')}`);
}

/** Asserts that the schema rejects a document: FS-SCH-001. */
function rejects(doc: unknown) {
  const r = check(typeof doc === 'string' ? doc : JSON.stringify(doc));
  assert.ok(!r.valid, `expected the schema to reject ${typeof doc === 'string' ? doc : JSON.stringify(doc)}`);
}

const minimal = () => ({ floorspec: '0.1', project: { name: 'House' } });

/** Two walls at a corner, each with a typed door, a room, a slab, a material, an asset. */
function twoWalls(): Record<string, any> {
  return {
    floorspec: '0.1',
    project: { name: 'Two walls', description: 'An L corner.', extras: { camera: [1.5, 2.25] } },
    site: { trueNorth: -12500000, location: { latitude: 42360083, longitude: -71058880 }, boundary: [[0, 0], [10, 0], [10, 10]] },
    buildings: { B1: { name: 'House' } },
    levels: { L1: { building: 'B1', elevation: 0, height: 3200000 } },
    junctions: {
      J1: { level: 'L1', position: [0, 0] },
      J2: { level: 'L1', position: [3840000, 0], join: { kind: 'butt', through: ['W1'] } },
      J3: { level: 'L1', position: [3840000, 2560000], join: { kind: 'mitre' } },
    },
    walls: {
      W1: { level: 'L1', start: 'J1', end: 'J2', type: 'WT1', justification: 'center', base: {} },
      W2: {
        level: 'L1',
        start: 'J2',
        end: 'J3',
        layers: [{ thickness: 12800, function: 'core', material: 'M1' }],
        base: { level: 'L1', offset: 0 },
        top: { level: 'L1', offset: -12800 },
      },
    },
    separators: { S1: { level: 'L1', start: 'J1', end: 'J3' } },
    openings: {
      O1: { wall: 'W1', offset: 1000000, fill: 'D1', hinge: 'end', swing: 'left' },
      O2: { wall: 'W2', offset: 0, width: 900000, height: 1200000, sill: 0, fill: 'WN1' },
    },
    rooms: { R1: { level: 'L1', anchor: [2000000, 500000], function: 'kitchen', floorFinish: 'M1' } },
    slabs: { SL1: { level: 'L1', boundary: [[0, 0], [100, 0], [100, 100]], thickness: 1280, material: 'M1' } },
    types: {
      WT1: {
        kind: 'wallType',
        name: '2x4 interior',
        layers: [
          { thickness: 16256, function: 'finish' },
          { thickness: 113792, function: 'core' },
          { thickness: 16256, function: 'finish' },
        ],
      },
      D1: { kind: 'doorType', width: 1170432, height: 2621280 },
      WN1: { kind: 'windowType', sill: 1000000 },
    },
    materials: { M1: { color: '#a0522d', texture: { asset: 'A1', size: [384000, 384000] } } },
    assets: { A1: { path: 'textures/oak.png', sha256: 'a'.repeat(64), mediaType: 'image/png' } },
    extensionsUsed: { FS_electrical: '0.1', EXT_acoustics: '1.2.3-draft.1' },
    extensionsRequired: ['FS_electrical'],
    extensions: { FS_electrical: { panels: [{ amps: 200.5 }] } },
    extras: { importer: { file: 'house.dwg', scale: 0.5 } },
  };
}

test('a minimal document is valid', () => accepts(minimal()));

test('a document with two walls, openings, a room, a slab, types, a material and an asset is valid', () => accepts(twoWalls()));

test('every member at its constant default is valid', () => {
  const d = twoWalls();
  Object.assign(d.walls.W1, { justification: 'center', base: { offset: 0 }, extensions: {}, extras: {} });
  Object.assign(d.rooms.R1, { function: 'unspecified' });
  Object.assign(d.slabs.SL1, { offset: 0 });
  Object.assign(d.site, { trueNorth: 0 });
  accepts(d);
});

test('every default sits on a member whose default is constant, and nowhere else', () => {
  // The canonicalizer's table of constant defaults (9.2 step 1): exactly these, and no others.
  const element = (file: string, at = '') => [`${file}#${at}/properties/extensions {}`, `${file}#${at}/properties/extras {}`];
  const expected = [
    ...element('asset.schema.json'),
    ...element('building.schema.json'),
    ...['buildings', 'levels', 'junctions', 'walls', 'separators', 'openings', 'rooms', 'slabs', 'types', 'materials', 'assets', 'extensionsUsed'].map(
      (c) => `floorspec.schema.json#/properties/${c} {}`,
    ),
    'floorspec.schema.json#/properties/extensionsRequired []',
    'floorspec.schema.json#/properties/extensions {}',
    'floorspec.schema.json#/properties/extras {}',
    'junction.schema.json#/properties/join {"kind":"mitre"}',
    ...element('junction.schema.json'),
    ...element('level.schema.json'),
    ...element('material.schema.json'),
    'opening.schema.json#/properties/hinge "start"',
    'opening.schema.json#/properties/swing "right"',
    ...element('opening.schema.json'),
    'project.schema.json#/properties/extras {}',
    'room.schema.json#/properties/function "unspecified"',
    ...element('room.schema.json'),
    ...element('separator.schema.json'),
    'site.schema.json#/properties/trueNorth 0',
    'site.schema.json#/properties/extras {}',
    'slab.schema.json#/properties/offset 0',
    ...element('slab.schema.json'),
    ...element('type.schema.json', '/$defs/wallType'),
    ...element('type.schema.json', '/$defs/doorType'),
    ...element('type.schema.json', '/$defs/windowType'),
    'wall.schema.json#/properties/justification "center"',
    'wall.schema.json#/properties/base {}',
    'wall.schema.json#/properties/base/properties/offset 0',
    'wall.schema.json#/properties/top/oneOf/0/properties/offset 0',
    ...element('wall.schema.json'),
  ];
  const actual = [...defaults()].map(([where, d]) => `${where} ${JSON.stringify(d.value)}`);
  assert.deepEqual(actual.sort(), expected.sort());
});

test('every required member is declared', () => assert.deepEqual(undefinedRequired(), []));

test('1.1: the document is an object with exactly the members of its table', () => {
  rejects([]);
  rejects('"0.1"');
  rejects({ project: { name: 'x' } });
  rejects({ floorspec: '0.1' });
  rejects({ ...minimal(), floorspec: 0.1 });
  rejects({ ...minimal(), walls2: {} });
  for (const reserved of ['roofs', 'stairs', 'optionSets']) rejects({ ...minimal(), [reserved]: {} });
});

test('1.3: every level references a building, and every plan element a level', () => {
  const d = twoWalls();
  delete d.levels.L1.building;
  rejects(d);
  for (const [collection, id] of [['junctions', 'J1'], ['walls', 'W1'], ['separators', 'S1'], ['rooms', 'R1'], ['slabs', 'SL1']] as const) {
    const e = twoWalls();
    delete e[collection][id].level;
    rejects(e);
  }
});

test('1.4: an element has only the members of its table, and a name of 1–200 characters', () => {
  for (const [collection, id] of [['buildings', 'B1'], ['levels', 'L1'], ['walls', 'W1'], ['openings', 'O1'], ['types', 'D1'], ['assets', 'A1']] as const) {
    const d = twoWalls();
    d[collection][id].colour = 'red';
    rejects(d);
  }
  const d = twoWalls();
  d.walls.W1.id = 'W1';
  rejects(d);
  rejects({ ...twoWalls(), buildings: { B1: { name: '' } } });
  rejects({ ...twoWalls(), buildings: { B1: { name: 'x'.repeat(201) } } });
  accepts({ ...twoWalls(), buildings: { B1: { name: 'x'.repeat(200) } } });
});

test('1.6.1: extension names match the pattern wherever they appear', () => {
  rejects({ ...minimal(), extensionsUsed: { electrical: '1.0' } });
  rejects({ ...minimal(), extensionsUsed: { FS_: '1.0' } });
  rejects({ ...minimal(), extensionsUsed: { ABCDEFGHI_x: '1.0' } });
  accepts({ ...minimal(), extensionsUsed: { ABCDEFGH_x: '1.0', D3_x: '1.0' } });
  rejects({ ...minimal(), extensionsRequired: ['fs_electrical'] });
  rejects({ ...minimal(), extensionsUsed: { FS_a: '1.0' }, extensionsRequired: ['FS_a', 'FS_a'] });
  rejects({ ...minimal(), extensionsUsed: { FS_a: 'v1' } });
  rejects({ ...minimal(), extensions: { 'my-ext': {} } });
  const d = twoWalls();
  d.walls.W1.extensions = { 'FS-electrical': {} };
  rejects(d);
});

test('1.8: project, site and level members', () => {
  rejects({ ...minimal(), project: {} });
  rejects({ ...minimal(), project: { name: 'x', description: 'y'.repeat(2001) } });
  rejects({ ...minimal(), project: { name: 'x', extensions: {} } });
  rejects({ ...minimal(), site: { trueNorth: -180000000 } });
  accepts({ ...minimal(), site: { trueNorth: 180000000 } });
  rejects({ ...minimal(), site: { trueNorth: 180000001 } });
  rejects({ ...minimal(), site: { location: { latitude: 90000001, longitude: 0 } } });
  accepts({ ...minimal(), site: { location: { latitude: -90000000, longitude: 180000000 } } });
  rejects({ ...minimal(), site: { location: { latitude: 0, longitude: -180000000 } } });
  rejects({ ...minimal(), site: { location: { latitude: 0 } } });
  rejects({ ...minimal(), site: { name: 'Lot 4' } });
  const d = twoWalls();
  d.levels.L1.height = 0;
  rejects(d);
  const e = twoWalls();
  delete e.levels.L1.elevation;
  rejects(e);
});

test('2.1: a length is an integer, written without a fraction or an exponent, within 2^53 − 1', () => {
  const text = JSON.stringify(twoWalls());
  accepts(text);
  rejects(text.replace('"elevation":0', '"elevation":0.5'));
  rejects(text.replace('"elevation":0', '"elevation":0.0'));
  rejects(text.replace('"elevation":0', '"elevation":0e0'));
  rejects(text.replace('"position":[0,0]', '"position":[1E3,0]'));
  rejects(text.replace('"elevation":0', '"elevation":9007199254740992'));
  accepts(text.replace('"elevation":0', '"elevation":-9007199254740991'));
  rejects(text.replace('"elevation":0', '"elevation":"0"'));
  rejects(text.replace('"position":[0,0]', '"position":[0,0,0]'));
  rejects(text.replace('"position":[0,0]', '"position":[0]'));
  // Any JSON number is valid inside extras and extension data (9.1).
  assert.ok(text.includes('"scale":0.5') && text.includes('"amps":200.5'));
});

test('2.4: an angle is an integer', () => {
  rejects('{"floorspec":"0.1","project":{"name":"x"},"site":{"trueNorth":1.5}}');
  rejects('{"floorspec":"0.1","project":{"name":"x"},"site":{"trueNorth":1.0}}');
  accepts('{"floorspec":"0.1","project":{"name":"x"},"site":{"trueNorth":-1}}');
});

test('3.1.1: element IDs match the pattern', () => {
  rejects({ ...minimal(), buildings: { '-B1': {} } });
  rejects({ ...minimal(), buildings: { 'B 1': {} } });
  rejects({ ...minimal(), buildings: { ['B'.repeat(65)]: {} } });
  accepts({ ...minimal(), buildings: { ['B'.repeat(64)]: {}, '0.b_c-d': {}, '550e8400-e29b-41d4-a716-446655440000': {} } });
});

test('4.1.1: a room function is a core term or an extension term', () => {
  const room = (fn: string) => {
    const d = twoWalls();
    d.rooms.R1.function = fn;
    return d;
  };
  for (const fn of ['unspecified', 'sleeping', 'bath', 'garage', 'exterior', 'EXT_wellness:sauna', 'FS_x:a1B']) accepts(room(fn));
  for (const fn of ['bedroom', 'Kitchen', '', 'EXT_wellness:Sauna', 'wellness:sauna', 'EXT_wellness:', 'EXT_wellness']) rejects(room(fn));
});

test('4.3.1: a layer function is one of the six terms', () => {
  const d = twoWalls();
  d.walls.W2.layers[0].function = 'structure';
  rejects(d);
});

test('5.9.1: top has level or height, not both, and offset never with height', () => {
  const top = (t: unknown) => {
    const d = twoWalls();
    d.walls.W2.top = t;
    return d;
  };
  accepts(top({ level: 'L1' }));
  accepts(top({ height: 2400000 }));
  accepts(top({ height: -1 })); // top above base is an invariant (FS-INV-112), not the schema
  rejects(top({ level: 'L1', height: 2400000 }));
  rejects(top({ height: 2400000, offset: 0 }));
  rejects(top({ offset: 0 }));
  rejects(top({}));
  rejects(top({ level: 'L1', offset: 0.5 }));
});

test('5.8: a join is a mitre or a butt join through one or two walls', () => {
  const join = (j: unknown) => {
    const d = twoWalls();
    d.junctions.J2.join = j;
    return d;
  };
  accepts(join({ kind: 'butt', through: ['W1', 'W2'] }));
  rejects(join({ kind: 'butt' }));
  rejects(join({ kind: 'butt', through: [] }));
  rejects(join({ kind: 'butt', through: ['W1', 'W2', 'W3'] }));
  rejects(join({ kind: 'mitre', through: ['W1'] }));
  rejects(join({ kind: 'bevel' }));
});

test('6.7.1: a slab has a polygon boundary and a thickness greater than zero', () => {
  const d = twoWalls();
  d.slabs.SL1.thickness = 0;
  rejects(d);
  const e = twoWalls();
  e.slabs.SL1.boundary = [[0, 0], [1, 1]];
  rejects(e);
});

test('7.1: opening offset, width, height, sill, hinge and swing', () => {
  const opening = (patch: Record<string, unknown>) => {
    const d = twoWalls();
    Object.assign(d.openings.O2, patch);
    return d;
  };
  rejects(opening({ offset: -1 }));
  rejects(opening({ width: 0 }));
  rejects(opening({ height: -5 }));
  rejects(opening({ sill: -1 }));
  rejects(opening({ hinge: 'middle' }));
  rejects(opening({ swing: 'in' }));
  const d = twoWalls();
  delete d.openings.O1.offset;
  rejects(d);
});

test('8.1: a type has a kind from the table and the members of that kind', () => {
  const type = (t: unknown) => {
    const d = twoWalls();
    d.types.T9 = t;
    return d;
  };
  rejects(type({ width: 900000 }));
  rejects(type({ kind: 'roofType' }));
  rejects(type({ kind: 'wallType' }));
  rejects(type({ kind: 'doorType', layers: [{ thickness: 1, function: 'core' }] }));
  rejects(type({ kind: 'windowType', justification: 'center' }));
  accepts(type({ kind: 'windowType' }));
});

test('8.3: layers are non-empty and every thickness is greater than zero', () => {
  const d = twoWalls();
  d.types.WT1.layers = [];
  rejects(d);
  const e = twoWalls();
  e.walls.W2.layers = [];
  rejects(e);
  const f = twoWalls();
  f.types.WT1.layers[1].thickness = 0;
  rejects(f);
  const g = twoWalls();
  delete g.walls.W2.layers[0].function;
  rejects(g);
});

test('8.4: door and window type dimensions', () => {
  const d = twoWalls();
  d.types.D1.width = 0;
  rejects(d);
  const e = twoWalls();
  e.types.WN1.sill = -1;
  rejects(e);
});

test('8.5: material colour and texture size', () => {
  const material = (m: unknown) => ({ ...twoWalls(), materials: { M1: m } });
  rejects(material({ color: '#A0522D' }));
  rejects(material({ color: '#a0522' }));
  rejects(material({ color: 'sienna' }));
  rejects(material({ texture: { asset: 'A1', size: [0, 384000] } }));
  rejects(material({ texture: { asset: 'A1', size: [384000] } }));
  rejects(material({ texture: { asset: 'A1' } }));
});

test('8.6: an asset has exactly one of path and uri, a relative path, an https uri and a digest', () => {
  const asset = (a: Record<string, unknown>) => ({ ...twoWalls(), assets: { A1: { sha256: 'a'.repeat(64), mediaType: 'image/png', ...a } } });
  for (const path of ['oak.png', 'textures/oak.png', '.hidden/a', '..a', 'a/...', 'a/b:c.png', 'x']) accepts(asset({ path }));
  for (const path of ['', '/abs/oak.png', 'a//b', 'a/', './a', 'a/./b', '../a', 'a/..', 'a\\b', 'C:/x.png', 'C:x', 'https://x/y'])
    rejects(asset({ path }));
  accepts(asset({ uri: 'https://example.com/textures/oak.png?v=1' }));
  for (const uri of ['http://example.com/oak.png', 'https:oak.png', 'https://exa mple.com/', 'ftp://x', 'https://x/%zz', 'https://x/a%2']) rejects(asset({ uri }));
  accepts(asset({ uri: 'https://example.com/a%20b.png' }));
  rejects(asset({}));
  rejects(asset({ path: 'a.png', uri: 'https://example.com/a.png' }));
  rejects(asset({ path: 'a.png', sha256: 'A'.repeat(64) }));
  rejects(asset({ path: 'a.png', sha256: 'a'.repeat(63) }));
  rejects(asset({ path: 'a.png', mediaType: 'png' }));
  const d = twoWalls();
  delete d.assets.A1.sha256;
  rejects(d);
});

test('invariants are not the schema’s: they pass the schema tier', () => {
  const d = twoWalls();
  d.walls.W1.end = 'J404'; // FS-INV-002
  d.levels.W2 = { building: 'B1', elevation: 0, height: 1 }; // FS-INV-001
  d.walls.W2.extensions = { FS_plumbing: {} }; // FS-INV-005
  d.extensionsRequired = ['EXT_missing']; // FS-INV-004
  d.rooms.R1.function = 'EXT_wellness:sauna'; // FS-INV-006
  d.slabs.SL1.boundary = [[0, 0], [1, 1], [2, 2]]; // FS-INV-009
  d.separators.S1.end = 'J1'; // FS-INV-102
  d.junctions.J2.join = { kind: 'butt', through: ['S1'] }; // FS-INV-111
  accepts(d);
});

test('numbers written with a fraction or an exponent become NaN, everywhere', () => {
  assert.deepEqual(parseForSchema('{"a":1,"b":-0}'), { a: 1, b: -0 });
  const v = parseForSchema('{"a":[1.0,2e3,3]}') as { a: number[] };
  assert.ok(Number.isNaN(v.a[0]) && Number.isNaN(v.a[1]) && v.a[2] === 3);
});

test('the suite check: FS-SCH-001 tests must be rejected, other schema-tier tests accepted, parser and document tiers skipped', () => {
  const suite = mkdtempSync(join(tmpdir(), 'fs-suite-'));
  const write = (name: string, input: string, codes: string[]) => {
    const dir = join(suite, 'model', name);
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, 'test.json'), JSON.stringify({ description: name, covers: [] }));
    writeFileSync(join(dir, 'input.json'), input);
    writeFileSync(join(dir, 'expected.json'), JSON.stringify({ valid: codes.length === 0, diagnostics: codes.map((code) => ({ code })) }));
  };
  assert.deepEqual(checkSuite(suite, validate), { checked: 0, skipped: 0, problems: [] });
  write('001-valid', JSON.stringify(minimal()), []);
  write('002-sch', '{"floorspec":"0.1"}', ['FS-SCH-001']);
  write('003-inv', JSON.stringify({ ...minimal(), levels: { L1: { building: 'B404', elevation: 0, height: 1 } } }), ['FS-INV-002']);
  write('004-json', '{"floorspec":', ['FS-JSON-001']);
  write('005-doc', '{"floorspec":"9.9","project":{"name":"x"}}', ['FS-DOC-001']);
  assert.deepEqual(checkSuite(suite, validate), { checked: 3, skipped: 2, problems: [] });
  write('006-wrong-accept', '{"floorspec":"0.1","project":{"name":"x"},"roofs":{}}', []);
  write('007-wrong-reject', JSON.stringify(minimal()), ['FS-SCH-001']);
  write('008-lexical', '{"floorspec":"0.1","project":{"name":"x"},"site":{"trueNorth":0.0}}', ['FS-SCH-001']);
  const r = checkSuite(suite, validate);
  assert.equal(r.checked, 6);
  assert.equal(r.problems.length, 2);
  assert.match(r.problems[0]!, /006-wrong-accept: expects \[\], but the schema rejects/);
  assert.match(r.problems[1]!, /007-wrong-reject: expects \[FS-SCH-001\], but the schema accepts/);
});

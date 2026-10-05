import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  coreSchemaDir,
  coreValidator,
  createAjv,
  defaults,
  formatErrors,
  loadSchemaFiles,
  undefinedRequired,
  validateText,
  versionedValidator,
} from './schema.ts';

/** Floorspec Core 0.3's schema: what it adds to 0.2 - a door or window type's operation, and clear openings (8.4). */
const files = loadSchemaFiles(coreSchemaDir('0.3'));
const v03 = coreValidator('0.3', createAjv(files));
const v02 = coreValidator('0.2');
const v01 = coreValidator('0.1');
const reader = versionedValidator({ '0.1': v01, '0.2': v02, '0.3': v03 });
const reader02 = versionedValidator({ '0.1': v01, '0.2': v02, '0.3': v03 }, '0.2');

const accepts = (doc: unknown, v = v03) => {
  const r = validateText(typeof doc === 'string' ? doc : JSON.stringify(doc), v);
  assert.ok(r.valid, `expected the schema to accept, got:\n${formatErrors(r.errors).join('\n')}`);
};
const rejects = (doc: unknown, v = v03) => {
  const r = validateText(typeof doc === 'string' ? doc : JSON.stringify(doc), v);
  assert.ok(!r.valid, `expected the schema to reject ${typeof doc === 'string' ? doc : JSON.stringify(doc)}`);
};

const MM = 1280;
function house(): Record<string, any> {
  return {
    floorspec: '0.3',
    project: { name: 'House' },
    types: {
      D: { kind: 'doorType', width: 900 * MM, height: 2100 * MM, operation: 'swing', clearOpening: { width: 1040384, height: 2600960 } },
      G: { kind: 'windowType', width: 1200 * MM, height: 1200 * MM, sill: 900 * MM, operation: 'casement', clearOpening: { width: 560 * MM, height: 1050 * MM, area: 901120000000 } },
    },
    openings: {
      O1: { wall: 'W1', offset: 0, fill: 'D' },
      O2: { wall: 'W2', offset: 0, fill: 'G', clearOpening: { width: 500 * MM, height: 1000 * MM } },
    },
  };
}
const p = (mut: (d: Record<string, any>) => void) => {
  const d = house();
  mut(d);
  return d;
};

test('core 0.3: a document using every member 0.3 adds is valid', () => accepts(house()));

test('core 0.3: the declared version is "0.3"; a 0.3 reader checks "0.1" and "0.2" documents against their own drafts', () => {
  rejects({ ...house(), floorspec: '0.2' });
  rejects({ ...house(), floorspec: '0.2' }, reader);
  accepts({ floorspec: '0.2', project: { name: 'x' }, program: {} }, reader);
  accepts({ floorspec: '0.1', project: { name: 'x' } }, reader);
  rejects({ floorspec: '0.1', project: { name: 'x' }, program: {} }, reader);
  accepts(house(), reader);
  rejects({ floorspec: '0.3', project: { name: 'x' } }, v02);
  // a reader of 0.2 checks a "0.3" document against 0.2's schema, which rejects its version
  rejects({ floorspec: '0.3', project: { name: 'x' } }, reader02);
});

test('core 0.3: no member 0.3 adds has a default', () => {
  const found = [...defaults(files)].map(([where, d]) => `${where} ${JSON.stringify(d.value)}`);
  for (const f of found) assert.ok(!/clearOpening|operation/.test(f), f);
  assert.ok(found.includes('type.schema.json#/$defs/doorType/properties/clearances {}'));
  assert.deepEqual(undefinedRequired(files), []);
});

test('core 0.3, 8.4.2: operations', () => {
  for (const op of ['swing', 'doubleSwing', 'doubleActing', 'bypassSlide', 'pocket', 'surfaceSlide', 'bifold', 'overhead', 'cased'])
    accepts(p((d) => (d.types.D.operation = op)));
  for (const op of ['fixed', 'casement', 'awning', 'hopper', 'singleHung', 'doubleHung', 'horizontalSlider', 'tiltTurn', 'pivot'])
    accepts(p((d) => (d.types.G.operation = op)));
  rejects(p((d) => (d.types.D.operation = 'casement')));
  rejects(p((d) => (d.types.G.operation = 'swing')));
  rejects(p((d) => (d.types.D.operation = 'Swing')));
  rejects(p((d) => (d.types.D.operation = ['swing'])));
  rejects(p((d) => (d.openings.O1.operation = 'swing')));
  rejects(p((d) => (d.types.W = { kind: 'wallType', layers: [{ thickness: 1, function: 'core' }], operation: 'fixed' })));
});

test('core 0.3, 8.4.3: clear openings', () => {
  rejects(p((d) => (d.types.D.clearOpening.width = 0)));
  rejects(p((d) => (d.types.G.clearOpening.height = -1)));
  rejects(p((d) => delete d.types.D.clearOpening.height));
  rejects(p((d) => delete d.openings.O2.clearOpening.width));
  rejects(p((d) => (d.types.G.clearOpening.area = 0)));
  rejects(p((d) => (d.types.G.clearOpening.area = 2 ** 53)));
  rejects(p((d) => (d.types.D.clearOpening.area = 1)));
  rejects(p((d) => (d.types.D.clearOpening.depth = 1)));
  rejects(p((d) => (d.types.D.clearOpening = [1040384, 2600960])));
  rejects(JSON.stringify(house()).replace('"area":901120000000', '"area":9.0112e11'));
  accepts(p((d) => (d.types.G.clearOpening.area = 2 ** 53 - 1)));
  // an opening's own may have an area whatever fills it: whether it may is an invariant (7.1.3)
  accepts(p((d) => (d.openings.O1.clearOpening = { width: 1, height: 1, area: 1 })));
  // and its size against the opening's, the type's, or its own width times height (7.2.2, 8.4.4, 8.4.5)
  accepts(p((d) => (d.types.D.clearOpening = { width: 2 * 900 * MM, height: 1 })));
  accepts(p((d) => (d.types.G.clearOpening.area = 560 * MM * 1050 * MM + 1)));
});

// Chapter 15: floors, ceilings and slabs
function rooms(): Record<string, any> {
  return {
    floorspec: '0.3',
    project: { name: 'Rooms' },
    buildings: { B1: {} },
    levels: { L1: { building: 'B1', elevation: 0, height: 3456000, floorThickness: 384000, ceilingHeight: 3072000 } },
    rooms: {
      R1: { level: 'L1', anchor: [0, 0], floor: { offset: -192000, thickness: 256000 }, ceiling: { kind: 'flat', height: 2944000 } },
      R2: { level: 'L1', anchor: [1, 0], ceiling: { kind: 'tray', border: 384000, depth: 256000 } },
      R3: { level: 'L1', anchor: [2, 0], ceiling: { kind: 'vaulted', height: 4000000, ridge: [[0, 0], [1, 0]], pitch: { rise: 6, run: 12 }, slopes: 'left' } },
    },
    slabs: { S1: { level: 'L1', boundary: [[0, 0], [1, 0], [1, 1]], thickness: 1, purpose: 'patio' } },
  };
}
const r = (mut: (d: Record<string, any>) => void) => {
  const d = rooms();
  mut(d);
  return d;
};

test('core 0.3, chapter 15: a document with every floor, ceiling and slab member is valid', () => accepts(rooms()));

test('core 0.3, 1.8.4: a level\'s floor thickness and ceiling height are greater than zero', () => {
  rejects(r((d) => (d.levels.L1.floorThickness = 0)));
  rejects(r((d) => (d.levels.L1.ceilingHeight = -1)));
  rejects(r((d) => (d.levels.L1.ceilingHeight = 1.5)));
  const level02 = { floorspec: '0.2', project: { name: 'x' }, buildings: { B1: {} }, levels: { L1: { building: 'B1', elevation: 0, height: 1 } } };
  accepts(level02, reader);
  rejects({ ...level02, levels: { L1: { ...level02.levels.L1, floorThickness: 1 } } }, reader);
});

test('core 0.3, 15.1.1: a floor has an offset of any sign and a positive thickness, nothing else', () => {
  accepts(r((d) => (d.rooms.R1.floor = {})));
  accepts(r((d) => (d.rooms.R1.floor = { offset: 192000 })));
  rejects(r((d) => (d.rooms.R1.floor.thickness = 0)));
  rejects(r((d) => (d.rooms.R1.floor.finish = 'M1')));
  rejects(r((d) => (d.rooms.R1.floor = 0)));
});

test('core 0.3, 15.2.1: a ceiling is exactly one of three forms', () => {
  accepts(r((d) => (d.rooms.R1.ceiling = { kind: 'flat' })));
  accepts(r((d) => (d.rooms.R3.ceiling.slopes = 'both')));
  accepts(r((d) => delete d.rooms.R3.ceiling.height));
  rejects(r((d) => (d.rooms.R1.ceiling = { kind: 'dome' })));
  rejects(r((d) => (d.rooms.R1.ceiling = { height: 1 })));
  rejects(r((d) => (d.rooms.R1.ceiling.height = 0)));
  rejects(r((d) => (d.rooms.R1.ceiling.border = 1)));
  rejects(r((d) => delete d.rooms.R2.ceiling.depth));
  rejects(r((d) => (d.rooms.R2.ceiling.border = 0)));
  rejects(r((d) => (d.rooms.R2.ceiling.depth = -5)));
  rejects(r((d) => (d.rooms.R2.ceiling.ridge = [[0, 0], [1, 0]])));
  rejects(r((d) => delete d.rooms.R3.ceiling.pitch));
  rejects(r((d) => delete d.rooms.R3.ceiling.ridge));
  rejects(r((d) => (d.rooms.R3.ceiling.ridge = [[0, 0]])));
  rejects(r((d) => (d.rooms.R3.ceiling.ridge = [[0, 0], [1, 0], [2, 0]])));
  rejects(r((d) => (d.rooms.R3.ceiling.pitch = { rise: 0, run: 12 })));
  rejects(r((d) => (d.rooms.R3.ceiling.pitch = { rise: 6 })));
  rejects(r((d) => (d.rooms.R3.ceiling.slopes = 'up')));
  rejects(r((d) => (d.rooms.R1.ceiling.slopes = 'both')));
  // two equal ridge points are an invariant (15.3.1), not the schema's
  accepts(r((d) => (d.rooms.R3.ceiling.ridge = [[0, 0], [0, 0]])));
});

test('core 0.3, 6.7.2: a slab\'s purpose is a term of 6.7', () => {
  for (const p of ['patio', 'deck', 'porch', 'stoop', 'landing', 'balcony', 'garage', 'walkway', 'driveway', 'equipmentPad', 'other'])
    accepts(r((d) => (d.slabs.S1.purpose = p)));
  rejects(r((d) => (d.slabs.S1.purpose = 'Patio')));
  rejects(r((d) => (d.slabs.S1.purpose = 'pool')));
});

test('core 0.3, chapter 15: the constant defaults are a floor {}, its offset 0, a flat ceiling and a vault\'s two slopes', () => {
  const found = new Map([...defaults(files)].map(([where, d]) => [where, JSON.stringify(d.value)]));
  assert.equal(found.get('room.schema.json#/properties/floor'), '{}');
  assert.equal(found.get('room.schema.json#/$defs/floor/properties/offset'), '0');
  assert.equal(found.get('room.schema.json#/properties/ceiling'), '{"kind":"flat"}');
  assert.equal(found.get('room.schema.json#/$defs/ceiling/oneOf/2/properties/slopes'), '"both"');
  for (const [where] of found) assert.ok(!/floorThickness|ceilingHeight|thickness|\/height|purpose/.test(where) || where.includes('positiveLength'), where);
});

// ---- Core 0.3, chapter 16: roofs
const roofDoc = (roof: Record<string, unknown>) => ({
  floorspec: '0.3',
  project: { name: 'Roofs' },
  roofs: { RF1: { level: 'L1', footprint: [[0, 0], [10, 0], [10, 4], [0, 4]], ...roof } },
});

test('core 0.3, 16.1.1: a roof has its table\'s members, each of its type', () => {
  accepts(roofDoc({}));
  accepts(roofDoc({ pitch: { rise: 6, run: 12 }, overhang: 0, height: -5, thickness: 1, material: 'M1', name: 'Main' }));
  accepts(roofDoc({ pitch: { rise: 6, run: 12 }, edges: { '0': { gable: true, overhang: 3 }, '1': { pitch: { rise: 1, run: 2 } }, '12': {} } }));
  accepts(roofDoc({ edges: { '0': { gable: false, pitch: { rise: 1, run: 1 } } } }));
  rejects(roofDoc({ pitch: { rise: 0, run: 12 } }));
  rejects(roofDoc({ pitch: { rise: 6 } }));
  rejects(roofDoc({ overhang: -1 }));
  rejects(roofDoc({ thickness: 0 }));
  rejects(roofDoc({ kind: 'hip' }));
  rejects(roofDoc({ edges: { '01': {} } }));
  rejects(roofDoc({ edges: { north: {} } }));
  rejects(roofDoc({ edges: { '-1': {} } }));
  rejects(roofDoc({ edges: { '0': { gable: true, pitch: { rise: 6, run: 12 } } } }));
  rejects(roofDoc({ edges: { '0': { gable: 'yes' } } }));
  rejects(roofDoc({ edges: { '0': { overhang: -1 } } }));
  rejects(roofDoc({ edges: { '0': { fascia: 1 } } }));
  rejects({ floorspec: '0.3', project: { name: 'x' }, roofs: { RF1: { level: 'L1' } } });
  rejects({ floorspec: '0.3', project: { name: 'x' }, roofs: { RF1: { level: 'L1', footprint: [[0, 0], [1, 0]] } } });
  // an edge index that names no edge (16.1.2) is an invariant, FS-INV-801, not the schema's
  accepts(roofDoc({ edges: { '9': {} } }));
  // a 0.2 document has no roofs
  rejects({ floorspec: '0.2', project: { name: 'x' }, roofs: {} }, reader);
});

test('core 0.3, chapter 16: the constant defaults are no roofs, an overhang of 0, no edges, and an edge that is not a gable', () => {
  const found = new Map([...defaults(files)].map(([where, d]) => [where, JSON.stringify(d.value)]));
  assert.equal(found.get('floorspec.schema.json#/properties/roofs'), '{}');
  assert.equal(found.get('roof.schema.json#/properties/overhang'), '0');
  assert.equal(found.get('roof.schema.json#/properties/edges'), '{}');
  assert.equal(found.get('roof.schema.json#/$defs/edge'), '{}');
  assert.equal(found.get('roof.schema.json#/$defs/edge/properties/gable'), 'false');
  for (const [where] of found) assert.ok(!/roof\.schema\.json#\/(properties\/(height|pitch|thickness)|\$defs\/edge\/properties\/(pitch|overhang))/.test(where), where);
});

// Chapter 17: stairs
function stairs(): Record<string, any> {
  return {
    floorspec: '0.3',
    project: { name: 'Stairs' },
    buildings: { B1: {} },
    levels: { L1: { building: 'B1', elevation: 0, height: 3456000 }, L2: { building: 'B1', elevation: 3456000, height: 3456000 } },
    stairs: {
      ST1: { level: 'L1', to: 'L2', position: [0, 0], width: 1152000, tread: 320000, risers: 15 },
      ST2: { level: 'L1', to: 'L2', position: [0, 0], rotation: 90000000, width: 1152000, tread: 320000, maxRiser: 245000,
             form: { kind: 'lShaped', turn: 'left', risersBeforeTurn: 8 }, handrail: { height: 1100000, sides: 'right' } },
      ST3: { level: 'L1', to: 'L2', position: [0, 0], width: 1152000, tread: 320000, risers: 16, form: { kind: 'uShaped', turn: 'right', risersBeforeTurn: 8, gap: 128000 } },
      ST4: { level: 'L1', to: 'L2', position: [0, 0], width: 1152000, tread: 320000, risers: 15, form: { kind: 'winder', turn: 'left', angle: 'quarter', risersBeforeTurn: 4, winders: 3 } },
      ST5: { level: 'L1', to: 'L2', position: [0, 0], width: 1152000, tread: 320000, risers: 15, form: { kind: 'winder', turn: 'left', angle: 'half', risersBeforeTurn: 4, winders: 6, gap: 0 } },
      ST6: { level: 'L1', to: 'L2', position: [0, 0], width: 896000, tread: 320000, risers: 13, form: { kind: 'spiral', turn: 'right', diameter: 1920000, sweep: 270000000 } },
    },
  };
}
const s = (mut: (d: Record<string, any>) => void) => {
  const d = stairs();
  mut(d);
  return d;
};

test('core 0.3, chapter 17: a document with a stair of every form is valid', () => accepts(stairs()));

test('core 0.3, 17.1.1: a stair has its members, of their types, and exactly one of risers and maxRiser', () => {
  for (const m of ['level', 'to', 'position', 'width', 'tread']) rejects(s((d) => delete d.stairs.ST1[m]));
  rejects(s((d) => delete d.stairs.ST1.risers));
  rejects(s((d) => (d.stairs.ST1.maxRiser = 245000)));
  rejects(s((d) => (d.stairs.ST1.risers = 0)));
  rejects(s((d) => (d.stairs.ST1.width = 0)));
  rejects(s((d) => (d.stairs.ST1.tread = -1)));
  rejects(s((d) => (d.stairs.ST2.maxRiser = 0)));
  rejects(s((d) => (d.stairs.ST1.rotation = -180000000)));
  accepts(s((d) => (d.stairs.ST1.rotation = 180000000)));
  rejects(s((d) => (d.stairs.ST1.nosing = 25600)));
  rejects(s((d) => (d.stairs.ST2.handrail = { sides: 'both' })));
  rejects(s((d) => (d.stairs.ST2.handrail.height = 0)));
  rejects(s((d) => (d.stairs.ST2.handrail.sides = 'neither')));
  rejects(JSON.stringify(stairs()).replace('"risers":15', '"risers":15.0'));
  // to and level in one building, its rise and its risers fitting its form are invariants
  accepts(s((d) => (d.stairs.ST1.to = 'L1')));
  accepts(s((d) => (d.stairs.ST1.risers = 1)));
});

test('core 0.3, 17.2.1: a form is exactly one of five, and a quarter-turn winder has no gap', () => {
  accepts(s((d) => (d.stairs.ST1.form = { kind: 'straight' })));
  rejects(s((d) => (d.stairs.ST1.form = { kind: 'curved' })));
  rejects(s((d) => (d.stairs.ST1.form = { kind: 'straight', turn: 'left' })));
  rejects(s((d) => delete d.stairs.ST2.form.turn));
  rejects(s((d) => (d.stairs.ST2.form.turn = 'up')));
  rejects(s((d) => (d.stairs.ST2.form.risersBeforeTurn = 0)));
  rejects(s((d) => (d.stairs.ST2.form.gap = 0)));
  rejects(s((d) => (d.stairs.ST3.form.gap = -1)));
  rejects(s((d) => (d.stairs.ST4.form.gap = 0)));
  rejects(s((d) => (d.stairs.ST4.form.angle = 'full')));
  rejects(s((d) => delete d.stairs.ST4.form.winders));
  rejects(s((d) => (d.stairs.ST5.form.winders = 0)));
  rejects(s((d) => (d.stairs.ST6.form.sweep = 0)));
  rejects(s((d) => (d.stairs.ST6.form.diameter = 0)));
  rejects(s((d) => delete d.stairs.ST6.form.turn));
  // a spiral's width against its diameter is an invariant (17.2.2)
  accepts(s((d) => (d.stairs.ST6.width = 2 * 1920000)));
});

test('core 0.3, chapter 17: stairs are a 0.3 collection, with the constant defaults of 17.1 and 17.2', () => {
  rejects({ floorspec: '0.2', project: { name: 'x' }, stairs: {} }, reader);
  accepts({ floorspec: '0.3', project: { name: 'x' }, stairs: {} });
  const found = new Map([...defaults(files)].map(([where, d]) => [where, JSON.stringify(d.value)]));
  assert.equal(found.get('floorspec.schema.json#/properties/stairs'), '{}');
  assert.equal(found.get('stair.schema.json#/properties/rotation'), '0');
  assert.equal(found.get('stair.schema.json#/properties/form'), '{"kind":"straight"}');
  assert.equal(found.get('stair.schema.json#/$defs/form/oneOf/2/properties/gap'), '0');
  assert.equal(found.get('stair.schema.json#/$defs/form/oneOf/4/properties/gap'), '0');
  assert.equal(found.get('stair.schema.json#/$defs/handrail/properties/sides'), '"both"');
  for (const [where] of found) if (where.startsWith('stair.schema.json')) assert.ok(!/risers|maxRiser|width|tread|level|position|winders|sweep|diameter/.test(where), where);
});

// Chapter 19: design options
function optioned(): Record<string, any> {
  return {
    floorspec: '0.3',
    project: { name: 'Options' },
    buildings: { B1: {} },
    levels: { L1: { building: 'B1', elevation: 0, height: 3456000 }, L2: { building: 'B1', elevation: 3456000, height: 3456000 } },
    optionSets: { KS: { name: 'Kitchen', primary: 'KA', extras: {} } },
    options: { KA: { set: 'KS', name: 'A' }, KB: { set: 'KS', name: 'B', extras: { colour: 'blue' } } },
    junctions: { J1: { level: 'L1', position: [0, 0], option: 'KA' }, J2: { level: 'L1', position: [1, 0] } },
    walls: { W1: { level: 'L1', start: 'J1', end: 'J2', option: 'KA' } },
    separators: { S1: { level: 'L1', start: 'J1', end: 'J2', option: 'KB' } },
    openings: { O1: { wall: 'W1', offset: 0, width: 1, height: 1, option: 'KA' } },
    rooms: { R1: { level: 'L1', anchor: [0, 0], option: 'KB' } },
    slabs: { SL1: { level: 'L1', boundary: [[0, 0], [1, 0], [1, 1]], thickness: 1, option: 'KB' } },
    roofs: { RF1: { level: 'L1', footprint: [[0, 0], [1, 0], [1, 1]], option: 'KB' } },
    stairs: { ST1: { level: 'L1', to: 'L2', position: [0, 0], width: 1, tread: 1, risers: 2, option: 'KB' } },
    extensionsUsed: { FS_furniture: '0.1' },
    extensions: { FS_furniture: { collections: { pieces: { F1: { fallback: { level: 'L1', box: { min: [0, 0, 0], max: [1, 1, 1] } }, option: 'KB' } } } } },
  };
}
const o = (mut: (d: Record<string, any>) => void) => {
  const d = optioned();
  mut(d);
  return d;
};

test('core 0.3, 19.1.1 and 19.2: option sets, options, and every kind that may be in an option', () => accepts(optioned()));

test('core 0.3, 19.1.1: an option set has a primary, an option a set, and nothing else', () => {
  rejects(o((d) => delete d.optionSets.KS.primary));
  rejects(o((d) => delete d.options.KA.set));
  rejects(o((d) => (d.optionSets.KS.options = ['KA', 'KB'])));
  rejects(o((d) => (d.options.KA.order = 1)));
  rejects(o((d) => (d.optionSets.KS.primary = 1)));
  rejects(o((d) => (d.options.KA.set = 'not an id!')));
  // that the primary is one of the set's own options is an invariant (FS-INV-1101)
  accepts(o((d) => (d.optionSets.KS.primary = 'KZ')));
});

test('core 0.3, 19.2.1: only the kinds that may be in an option have an option member', () => {
  rejects(o((d) => (d.levels.L1.option = 'KA')));
  rejects(o((d) => (d.buildings.B1.option = 'KA')));
  rejects(o((d) => (d.options.KB.option = 'KA')));
  rejects(o((d) => (d.optionSets.KS.option = 'KA')));
  rejects(o((d) => (d.types = { T: { kind: 'doorType', option: 'KA' } })));
  rejects(o((d) => (d.program = { items: { P1: { function: 'kitchen', option: 'KA' } } })));
  rejects(o((d) => (d.walls.W1.option = 7)));
  rejects(o((d) => (d.extensions.FS_furniture.collections.pieces.F1.option = 7)));
});

test('core 0.3, chapter 19: option sets and options are 0.3 collections, and only their common members have defaults', () => {
  rejects({ floorspec: '0.2', project: { name: 'x' }, optionSets: {} }, reader);
  rejects({ floorspec: '0.2', project: { name: 'x' }, options: {} }, reader);
  accepts({ floorspec: '0.3', project: { name: 'x' }, optionSets: {}, options: {} });
  const found = new Map([...defaults(files)].map(([where, d]) => [where, JSON.stringify(d.value)]));
  assert.equal(found.get('floorspec.schema.json#/properties/optionSets'), '{}');
  assert.equal(found.get('floorspec.schema.json#/properties/options'), '{}');
  for (const [where] of found) if (where.startsWith('option.schema.json')) assert.ok(/\/properties\/(extensions|extras)$/.test(where), where);
  for (const [where] of found) assert.ok(!/\/properties\/option$/.test(where), where);
});

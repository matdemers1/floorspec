import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  coreSchemaDir,
  coreValidator,
  createAjv,
  defaults,
  formatErrors,
  loadSchemaFiles,
  registryValidator,
  undefinedRequired,
  validateText,
  versionedValidator,
} from './schema.ts';

/** Floorspec Core 0.2's schema: what it adds to 0.1, and the registry entry schema (12.2). */
const files = loadSchemaFiles(coreSchemaDir('0.2'));
const v02 = coreValidator('0.2', createAjv(files));
const v01 = coreValidator('0.1');
const reader = versionedValidator({ '0.1': v01, '0.2': v02 });
const entry = registryValidator();

const accepts = (doc: unknown, v = v02) => {
  const r = validateText(typeof doc === 'string' ? doc : JSON.stringify(doc), v);
  assert.ok(r.valid, `expected the schema to accept, got:\n${formatErrors(r.errors).join('\n')}`);
};
const rejects = (doc: unknown, v = v02) => {
  const r = validateText(typeof doc === 'string' ? doc : JSON.stringify(doc), v);
  assert.ok(!r.valid, `expected the schema to reject ${typeof doc === 'string' ? doc : JSON.stringify(doc)}`);
};

const MM = 1280;
const box = (x = 600 * MM) => ({ min: [0, 0, 0], max: [x, x, x] });
function house(): Record<string, any> {
  return {
    floorspec: '0.2',
    project: { name: 'House' },
    buildings: { B1: {} },
    levels: { L1: { building: 'B1', elevation: 0, height: 3456000 } },
    rooms: { R1: { level: 'L1', anchor: [1, 1], brief: 'K' } },
    types: {
      D: { kind: 'doorType', width: 1152000, height: 2688000, clearances: { swing: { purpose: 'swing', shape: 'box', min: [0, -576000, 0], max: [1152000, 576000, 2688000] } } },
    },
    program: {
      items: { K: { function: 'kitchen', count: 1, targetArea: 19660800000000, minArea: 1, level: 'L1' }, D: { function: 'EXT_x:diner' } },
      adjacency: [{ a: 'K', b: 'D', kind: 'required', weight: 10 }],
    },
    extensionsUsed: { FS_furniture: { version: '0.1', schema: 'https://example.com/s.json' }, EXT_x: '1.0' },
    extensions: {
      FS_furniture: {
        style: 'mid-century',
        collections: {
          pieces: {
            SOFA: { fallback: { level: 'L1', box: box(), asset: 'A', symbol: 'S' }, host: { mode: 'free', level: 'L1', position: [0, 0], rotation: 90000000 }, colour: 0.5 },
            WC: { fallback: { level: 'L1', box: box() }, host: { mode: 'surface', room: 'R1', surface: 'floor', position: [0, 0] }, clearances: {} },
            OUT: { fallback: { level: 'L1', box: box() }, host: { mode: 'wallFace', wall: 'W1', side: 'left', offset: 0, height: 0 }, name: 'Outlet', extras: {} },
          },
        },
      },
      EXT_x: [1, 2],
    },
  };
}

test('core 0.2: a document using every member 0.2 adds is valid', () => accepts(house()));

test('core 0.2: the declared version is "0.2"; a 0.2 reader checks a "0.1" document against 0.1', () => {
  rejects({ ...house(), floorspec: '0.1' });
  accepts({ floorspec: '0.1', project: { name: 'x' } }, reader);
  rejects({ floorspec: '0.1', project: { name: 'x' }, program: {} }, reader);
  accepts({ floorspec: '0.2', project: { name: 'x' }, program: {} }, reader);
  rejects({ floorspec: '0.2', project: { name: 'x' } }, v01);
});

test('core 0.2: every default sits on a constant default of the 0.2 tables', () => {
  const found = [...defaults(files)].map(([where, d]) => `${where} ${JSON.stringify(d.value)}`);
  for (const expected of [
    'floorspec.schema.json#/properties/program {}',
    'program.schema.json#/properties/items {}',
    'program.schema.json#/properties/adjacency []',
    'program.schema.json#/$defs/item/properties/count 1',
    'program.schema.json#/$defs/item/properties/extensions {}',
    'program.schema.json#/$defs/item/properties/extras {}',
    'program.schema.json#/$defs/adjacency/properties/weight 5',
    'type.schema.json#/$defs/doorType/properties/clearances {}',
    'type.schema.json#/$defs/windowType/properties/clearances {}',
  ])
    assert.ok(found.includes(expected), expected);
  // Extension elements are extension data, which canonicalization never changes: no defaults there.
  for (const f of ['host.schema.json', 'fallback.schema.json', 'clearance.schema.json', 'extension.schema.json'])
    assert.deepEqual(found.filter((x) => x.startsWith(f)), [], f);
  assert.deepEqual(undefinedRequired(files), []);
});

test('core 0.2, 11.1.1: program, items and adjacencies', () => {
  const p = (mut: (d: Record<string, any>) => void) => {
    const d = house();
    mut(d);
    return d;
  };
  rejects(p((d) => (d.program.items.K.count = 0)));
  rejects(p((d) => (d.program.items.K.targetArea = 0)));
  rejects(p((d) => (d.program.items.K.minArea = 2 ** 53)));
  rejects(p((d) => delete d.program.items.K.function));
  rejects(p((d) => (d.program.items.K.function = 'bedroom')));
  rejects(p((d) => (d.program.adjacency[0].weight = 0)));
  rejects(p((d) => (d.program.adjacency[0].weight = 11)));
  rejects(p((d) => (d.program.adjacency[0].kind = 'adjacent')));
  rejects(p((d) => (d.program.solver = 'x')));
  rejects(p((d) => (d.program.items.K.rooms = [])));
  rejects(p((d) => (d.rooms.R1.brief = 5)));
  rejects(JSON.stringify(house()).replace('"targetArea":19660800000000', '"targetArea":1.96608e13'));
  // self-adjacency, duplicates and contradictions are invariants, not the schema's
  accepts(p((d) => d.program.adjacency.push({ a: 'K', b: 'K', kind: 'forbidden' }, { a: 'D', b: 'K', kind: 'required' })));
});

test('core 0.2, 12.1: declarations', () => {
  const decl = (v: unknown) => ({ ...house(), extensionsUsed: { ...house().extensionsUsed, FS_furniture: v } });
  accepts(decl('0.1'));
  accepts(decl({ version: '0.1' }));
  rejects(decl({ version: 'v1' }));
  rejects(decl({ schema: 'https://example.com/s.json' }));
  rejects(decl({ version: '0.1', schema: 'http://example.com/s.json' }));
  rejects(decl({ version: '0.1', required: true }));
  rejects(decl(['0.1']));
  rejects(decl(1));
});

test('core 0.2, 12.5 and 12.6: extension elements and fallbacks', () => {
  const el = (mut: (e: Record<string, any>, d: Record<string, any>) => void) => {
    const d = house();
    mut(d.extensions.FS_furniture.collections.pieces.SOFA, d);
    return d;
  };
  rejects(el((e) => delete e.fallback));
  rejects(el((e) => (e.fallback.colour = 'red')));
  rejects(el((e) => delete e.fallback.level));
  rejects(el((e) => (e.fallback.box = { min: [0, 0], max: [1, 1, 1] })));
  rejects(el((e) => (e.fallback.box.size = [1, 1, 1])));
  rejects(el((e) => (e.name = '')));
  rejects(el((e) => (e.clearances = [])));
  rejects(el((_, d) => (d.extensions.FS_furniture.collections = { Pieces: {} })));
  rejects(el((_, d) => (d.extensions.FS_furniture.collections = [])));
  rejects(el((_, d) => (d.extensions.FS_furniture.collections.pieces['SOFA 2'] = { fallback: { level: 'L1', box: box() } })));
  rejects(el((_, d) => (d.extensions.FS_furniture.collections.pieces.X = 'sofa')));
  accepts(el((e) => (e.anything = { at: [1.5] })));
  // `collections` means nothing in element-level extension data
  accepts(el((_, d) => (d.rooms.R1.extensions = { FS_furniture: { collections: 'opaque' } })));
  // ... nor in a 0.1 document
  accepts({ floorspec: '0.1', project: { name: 'x' }, extensionsUsed: { FS_furniture: '0.1' }, extensions: { FS_furniture: { collections: 3 } } }, reader);
});

test('core 0.2, 13.3: hosts', () => {
  const host = (h: unknown) => {
    const d = house();
    d.extensions.FS_furniture.collections.pieces.SOFA.host = h;
    return d;
  };
  accepts(host({ mode: 'free', level: 'L1', position: [0, 0], rotation: 180000000 }));
  rejects(host({ mode: 'free', level: 'L1', position: [0, 0], rotation: -180000000 }));
  rejects(host({ mode: 'free', level: 'L1', position: [0, 0], rotation: 180000001 }));
  rejects(host({ mode: 'free', level: 'L1', position: [0, 0], room: 'R1' }));
  rejects(host({ mode: 'ceiling', room: 'R1', position: [0, 0] }));
  rejects(host({ mode: 'surface', room: 'R1', surface: 'wall', position: [0, 0] }));
  rejects(host({ mode: 'wallFace', wall: 'W1', offset: 0, height: 0 }));
  rejects(host({ mode: 'wallFace', wall: 'W1', side: 'left', offset: -1, height: 0 }));
  rejects(host({ mode: 'wallFace', wall: 'W1', side: 'left', offset: 0, height: 0, rotation: 0 }));
});

test('core 0.2, 13.5.1: clearances only on door and window types and extension elements', () => {
  const t = (mut: (d: Record<string, any>) => void) => {
    const d = house();
    mut(d);
    return d;
  };
  rejects(t((d) => (d.types.D.clearances.swing.purpose = 'privacy')));
  rejects(t((d) => (d.types.D.clearances.swing.shape = 'arc')));
  rejects(t((d) => delete d.types.D.clearances.swing.shape));
  rejects(t((d) => delete d.types.D.clearances.swing.max));
  rejects(t((d) => (d.types.D.clearances = { Swing: d.types.D.clearances.swing })));
  rejects(t((d) => (d.types.W = { kind: 'wallType', layers: [{ thickness: 1, function: 'core' }], clearances: {} })));
  accepts(t((d) => (d.types.WN = { kind: 'windowType', clearances: {} })));
});

test('registry: an entry and its edges', () => {
  const e = { name: 'EXT_lighting', version: '1.2.0', status: 'draft', schema: 'https://example.com/s.json' };
  const ok = (x: unknown) => assert.ok(entry(x), formatErrors(entry.errors ?? []).join('\n'));
  const bad = (x: unknown) => assert.ok(!entry(x), JSON.stringify(x));
  ok(e);
  ok({ ...e, requires: { EXT_a: '^1.0.0', EXT_b: '>=1.0.0 <1.2.0 || >=2.0.0-rc.1' }, kinds: { fixtures: { title: 'Fixture', fallback: { symbol: true } } }, terms: { roomFunctions: ['sauna'] } });
  ok({ ...e, status: 'ratified', implementations: [{ name: 'a', url: 'https://a.example/' }, { name: 'b', url: 'https://b.example/' }] });
  bad({ ...e, status: 'ratified', implementations: [{ name: 'a', url: 'https://a.example/' }] });
  bad({ ...e, status: 'ratified' });
  bad({ ...e, status: 'final' });
  bad({ ...e, version: '1.2' });
  bad({ ...e, version: '01.2.0' });
  bad({ ...e, requires: { EXT_a: '1.x' } });
  bad({ ...e, requires: { EXT_a: '>= 1.0.0' } });
  bad({ ...e, requires: { lighting: '^1.0.0' } });
  bad({ ...e, kinds: { Fixtures: {} } });
  bad({ ...e, kinds: { fixtures: { fallback: { box: true } } } });
  bad({ ...e, terms: { layerFunctions: ['x'] } });
  bad({ ...e, terms: { roomFunctions: ['sauna', 'sauna'] } });
  bad({ ...e, schema: 'http://example.com/s.json' });
  bad({ ...e, homepage: 'https://example.com/' });
});

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { coreSchemaDir, coreValidator, createAjv, defaults, formatErrors, loadSchemaFiles, undefinedRequired, validateText, versionedValidator } from './schema.ts';

/** Floorspec Core 0.3's schema, chapter 18: materials, textures, assets and wall finishes. */
const files = loadSchemaFiles(coreSchemaDir('0.3'));
const v03 = coreValidator('0.3', createAjv(files));
const reader = versionedValidator({ '0.1': coreValidator('0.1'), '0.2': coreValidator('0.2'), '0.3': v03 });

const accepts = (doc: unknown, v = v03) => {
  const r = validateText(JSON.stringify(doc), v);
  assert.ok(r.valid, `expected the schema to accept, got:\n${formatErrors(r.errors).join('\n')}`);
};
const rejects = (doc: unknown, v = v03) => {
  const r = validateText(JSON.stringify(doc), v);
  assert.ok(!r.valid, `expected the schema to reject ${JSON.stringify(doc)}`);
};

const FT = 390144;
function kitchen(): Record<string, any> {
  return {
    floorspec: '0.3',
    project: { name: 'Kitchen' },
    walls: {
      W2: {
        level: 'L1', start: 'J2', end: 'J3',
        finishes: { right: { material: 'PAINT', regions: [{ from: 0, to: 4 * FT, bottom: 36 * 32512, top: 54 * 32512, material: 'TILE' }] } },
      },
    },
    materials: {
      PAINT: { color: '#e9e6df', roughness: 700 },
      TILE: { color: '#d8d4cc', metallic: 0, roughness: 300, texture: { asset: 'A1', normal: 'A2', metallicRoughness: 'A3', occlusion: 'A4', size: [FT, FT], offset: [0, -FT], rotation: 45_000_000 } },
    },
    assets: {
      A1: { path: 'assets/tile.png', sha256: 'ab'.repeat(32), mediaType: 'image/png', byteLength: 0 },
      A2: { path: 'assets/tile-n.png', sha256: 'cd'.repeat(32), mediaType: 'image/png', byteLength: 9007199254740991 },
      A3: { uri: 'https://example.com/mr.webp', sha256: 'ef'.repeat(32), mediaType: 'image/webp' },
      A4: { path: 'assets/ao.ktx2', sha256: '01'.repeat(32), mediaType: 'image/ktx2' },
    },
  };
}
const k = (mut: (d: Record<string, any>) => void) => {
  const d = kitchen();
  mut(d);
  return d;
};

test('core 0.3, chapter 18: a document using every member chapter 18 adds is valid', () => accepts(kitchen()));

test('core 0.3, 18.1.1: metallic and roughness are integers in thousandths, 0 to 1000', () => {
  for (const v of [0, 1, 999, 1000]) {
    accepts(k((d) => (d.materials.TILE.metallic = v)));
    accepts(k((d) => (d.materials.TILE.roughness = v)));
  }
  for (const v of [-1, 1001, 0.5, '500', null]) {
    rejects(k((d) => (d.materials.TILE.metallic = v)));
    rejects(k((d) => (d.materials.TILE.roughness = v)));
  }
});

test('core 0.3, 18.2.1: a texture has a size and at least one map, an offset point and a rotation in (-180°, 180°]', () => {
  for (const map of ['asset', 'normal', 'metallicRoughness', 'occlusion'])
    accepts(k((d) => (d.materials.TILE.texture = { [map]: 'A1', size: [FT, FT] })));
  rejects(k((d) => (d.materials.TILE.texture = { size: [FT, FT] })));
  rejects(k((d) => (d.materials.TILE.texture = { size: [FT, FT], offset: [0, 0], rotation: 0 })));
  rejects(k((d) => delete d.materials.TILE.texture.size));
  rejects(k((d) => (d.materials.TILE.texture.size = [FT, 0])));
  rejects(k((d) => (d.materials.TILE.texture.offset = [0])));
  rejects(k((d) => (d.materials.TILE.texture.offset = [0.5, 0])));
  accepts(k((d) => (d.materials.TILE.texture.rotation = 180_000_000)));
  rejects(k((d) => (d.materials.TILE.texture.rotation = -180_000_000)));
  rejects(k((d) => (d.materials.TILE.texture.emissive = 'A1')));
  rejects(k((d) => (d.materials.TILE.texture.normal = 7)));
  // that a map is an image (18.2.2) is an invariant, FS-INV-1004, not the schema's
  accepts(k((d) => (d.assets.A2.mediaType = 'model/gltf-binary')));
});

test('core 0.3, 18.4.1: an asset\'s byteLength is an integer from 0 to 2^53 - 1', () => {
  rejects(k((d) => (d.assets.A1.byteLength = -1)));
  rejects(k((d) => (d.assets.A1.byteLength = 9007199254740992)));
  rejects(k((d) => (d.assets.A1.byteLength = 1.5)));
  rejects(k((d) => (d.assets.A1.byteLength = '1')));
});

test('core 0.3, 18.5.1: a wall\'s finishes are of its two faces, each a material and regions', () => {
  accepts(k((d) => (d.walls.W2.finishes = {})));
  accepts(k((d) => (d.walls.W2.finishes = { left: {}, right: { regions: [] } })));
  accepts(k((d) => (d.walls.W2.finishes.left = { material: 'TILE' })));
  // an empty or upside-down region (18.5.2), one past its wall (18.5.3) and two that overlap (18.5.4) are invariants
  accepts(k((d) => Object.assign(d.walls.W2.finishes.right.regions[0], { from: 5, to: 5, bottom: 9, top: 3 })));
  rejects(k((d) => (d.walls.W2.finishes.top = {})));
  rejects(k((d) => (d.walls.W2.finishes.right.color = '#ffffff')));
  rejects(k((d) => (d.walls.W2.finishes.right.regions = d.walls.W2.finishes.right.regions[0])));
  for (const m of ['from', 'to', 'bottom', 'top', 'material']) {
    rejects(k((d) => delete d.walls.W2.finishes.right.regions[0][m]));
    if (m !== 'material') rejects(k((d) => (d.walls.W2.finishes.right.regions[0][m] = -1)));
  }
  rejects(k((d) => (d.walls.W2.finishes.right.regions[0].side = 'right')));
});

test('core 0.3, 1.2.6: a 0.2 or 0.1 document has none of chapter 18\'s members', () => {
  const old = (v: string, mut: (d: Record<string, any>) => void) => {
    const d: Record<string, any> = { floorspec: v, project: { name: 'x' }, materials: { M: { texture: { asset: 'A', size: [1, 1] } } }, assets: { A: { path: 'a.png', sha256: 'ab'.repeat(32), mediaType: 'image/png' } } };
    mut(d);
    return d;
  };
  for (const v of ['0.1', '0.2']) {
    accepts(old(v, () => {}), reader);
    rejects(old(v, (d) => (d.materials.M.roughness = 1)), reader);
    rejects(old(v, (d) => (d.materials.M.texture.rotation = 0)), reader);
    rejects(old(v, (d) => (d.materials.M.texture = { normal: 'A', size: [1, 1] })), reader);
    rejects(old(v, (d) => (d.assets.A.byteLength = 1)), reader);
    rejects(old(v, (d) => (d.walls = { W: { level: 'L', start: 'a', end: 'b', finishes: {} } })), reader);
  }
});

test('core 0.3, chapter 18: the constant defaults are an offset [0, 0], a rotation 0, finishes and face finishes {}, and regions []', () => {
  const found = new Map([...defaults(files)].map(([where, d]) => [where, JSON.stringify(d.value)]));
  assert.equal(found.get('material.schema.json#/properties/texture/properties/offset'), '[0,0]');
  assert.equal(found.get('material.schema.json#/properties/texture/properties/rotation'), '0');
  assert.equal(found.get('wall.schema.json#/properties/finishes'), '{}');
  assert.equal(found.get('finish.schema.json#/properties/left'), '{}');
  assert.equal(found.get('finish.schema.json#/properties/right'), '{}');
  assert.equal(found.get('finish.schema.json#/$defs/faceFinish/properties/regions'), '[]');
  // metallic and roughness default to their map's value, a face's material to its room's or layer's: derived
  for (const [where] of found) assert.ok(!/metallic|roughness|byteLength|faceFinish\/properties\/material|region\//.test(where), where);
  assert.deepEqual(undefinedRequired(files), []);
});

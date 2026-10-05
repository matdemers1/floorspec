import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cpSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { coreSchemaDir, coreValidator, createAjv, formatErrors, loadSchemaFiles, requestValidator, validateText } from './schema.ts';
import {
  build, CLEAR_OPENINGS_NOTE, DOORS, embed, EmbedConflict, entries, IN, inches, inchText, LIBRARY, listFiles, MATERIALS,
  VERSION, VERSION_DIR, VERSION_URI, verifyVersion, WALLS, WINDOWS,
} from './us-library.ts';

/** The US starter type library (FLR-T-10.4, FLR-REQ-139, FLR-REQ-169; Core 0.3 8.1). */
type Obj = Record<string, any>;
const files = build();
const index = JSON.parse(files.get('index.json')!.toString('utf8')) as Obj;
const all = entries();
const v03 = coreValidator('0.3', createAjv(loadSchemaFiles(coreSchemaDir('0.3'))));
const v02 = coreValidator('0.2', createAjv(loadSchemaFiles(coreSchemaDir('0.2'))));
const opsRequest = requestValidator(undefined, '0.3');

const empty = (): Obj => ({ floorspec: '0.3', project: { name: 'Library test' } });
function apply(doc: Obj, ops: Obj[]): Obj {
  const out = structuredClone(doc);
  for (const op of ops) {
    assert.equal(op.op, 'addElement');
    out[op.collection] ??= {};
    assert.equal(out[op.collection][op.id], undefined, `${op.id} is already used`);
    out[op.collection][op.id] = structuredClone(op.element);
  }
  return out;
}
const accepts = (doc: unknown, v = v03) => {
  const r = validateText(JSON.stringify(doc), v);
  assert.ok(r.valid, formatErrors(r.errors).join('\n'));
};

test('the current version on disk is exactly what the generator writes, and writing it twice gives the same bytes', () => {
  const again = build();
  assert.deepEqual([...again.keys()], [...files.keys()]);
  for (const [path, bytes] of files) {
    assert.ok(again.get(path)!.equals(bytes), `${path} is not deterministic`);
    assert.ok(readFileSync(join(VERSION_DIR, path)).equals(bytes), `${path} differs from the generator's: run pnpm library:us`);
  }
  assert.deepEqual(listFiles(VERSION_DIR), [...files.keys()].sort(), 'no file in the version directory that the generator does not write');
});

test('every published file matches SHA256SUMS, and a changed byte is caught', () => {
  assert.deepEqual(verifyVersion(VERSION_DIR), []);
  const copy = join(mkdtempSync(join(tmpdir(), 'us-library-')), VERSION);
  cpSync(VERSION_DIR, copy, { recursive: true });
  const item = join(copy, 'items', 'wall-2x4-interior.json');
  writeFileSync(item, readFileSync(item, 'utf8').replace('113792', '113793'));
  writeFileSync(join(copy, 'items', 'extra.json'), '{}\n');
  const problems = verifyVersion(copy);
  assert.ok(problems.some((p) => p.endsWith('items/wall-2x4-interior.json: differs from SHA256SUMS')), problems.join('\n'));
  assert.ok(problems.some((p) => p.endsWith('items/extra.json: not in SHA256SUMS')), problems.join('\n'));
});

test('a versioned library of US wall, door and window types and their materials, published by URI', () => {
  assert.equal(index.library, LIBRARY);
  assert.equal(index.version, VERSION);
  assert.equal(index.uri, `${LIBRARY}/${VERSION}/`);
  assert.match(VERSION, /^\d+\.\d+\.\d+$/);
  assert.equal(index.status, 'non-normative');
  assert.equal(index.floorspec, '0.3');
  assert.equal(index.clearOpenings, CLEAR_OPENINGS_NOTE);
  assert.match(index.clearOpenings, /^generic, replace with your product's declared values/);
  const kinds: Record<string, number> = {};
  for (const e of all.values()) kinds[e.kind] = (kinds[e.kind] ?? 0) + 1;
  assert.deepEqual(kinds, { material: MATERIALS.length, wallType: WALLS.length, doorType: DOORS.length, windowType: WINDOWS.length });
  assert.ok(WALLS.length >= 10 && DOORS.length >= 15 && WINDOWS.length >= 20);
  for (const [id, e] of all) {
    assert.equal(e.uri, `${VERSION_URI}items/${id}.json`);
    assert.deepEqual(e.element.source, { item: id, library: LIBRARY, version: VERSION });
    assert.equal(e.element.name, e.name);
    const file = JSON.parse(files.get(`items/${id}.json`)!.toString('utf8')) as Obj;
    assert.equal(file.item, id);
    assert.deepEqual(file.element, index.items[id].element, `${id}: its own file and the index embed the same element`);
  }
  // The operations Core 8.4 lists, and the door and window sizes the task names.
  assert.deepEqual(new Set(DOORS.map((d) => d.operation)), new Set(['swing', 'pocket', 'bifold', 'bypassSlide', 'doubleSwing', 'overhead']));
  assert.deepEqual(new Set(WINDOWS.map((w) => w.operation)), new Set(['singleHung', 'doubleHung', 'casement', 'horizontalSlider', 'fixed', 'awning']));
  for (const w of [24, 28, 30, 32, 36]) assert.ok(all.has(`door-interior-swing-${w}x80`));
  for (const id of ['door-exterior-swing-36x80', 'door-double-swing-60x80', 'door-double-swing-72x80', 'door-garage-overhead-9x7', 'door-garage-overhead-16x7'])
    assert.ok(all.has(id), id);
});

test('every length is an exact integer number of base units from its inch size, as the README states', () => {
  assert.equal(IN, 25.4 * 1280);
  assert.equal(inches(3, 1, 2), 113792);              // a 2x4's actual depth: 3 1/2 in
  assert.equal(inches(5, 1, 2), 178816);              // a 2x6's: 5 1/2 in
  assert.equal(inches(7, 5, 8), 247904);              // an 8 in CMU's actual thickness: 7 5/8 in
  assert.throws(() => inches(0, 1, 3));               // a third of an inch is not a whole number of base units
  assert.equal(inchText(inches(82, 1, 2)), '82 1/2 in');
  const walk = (v: unknown, path: string) => {
    if (typeof v === 'number') assert.ok(Number.isSafeInteger(v), `${path} = ${v}`);
    else if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) walk(x, `${path}/${k}`);
  };
  for (const [id, e] of all) walk(e.element, id);
  const stud = all.get('wall-2x4-interior')!.element as Obj;
  assert.deepEqual(stud.layers.map((l: Obj) => l.thickness), [inches(0, 1, 2), inches(3, 1, 2), inches(0, 1, 2)]);
  const door = all.get('door-interior-swing-30x80')!.element as Obj;
  assert.deepEqual([door.width, door.height], [inches(32), inches(82, 1, 2)]);   // the rough opening
  const dh = all.get('window-double-hung-36x48')!.element as Obj;
  assert.deepEqual([dh.width, dh.height, dh.sill], [inches(36, 1, 2), inches(48, 1, 2), inches(34)]);
  assert.equal(dh.sill + dh.height, inches(82, 1, 2));
});

test('every door and window type keeps Core 8.4: sizes, an operation of its kind, a clear opening that fits', () => {
  for (const [id, e] of all) {
    const el = e.element as Obj;
    if (el.kind === 'wallType') {
      assert.ok(el.layers.length >= 1 && el.layers.every((l: Obj) => l.thickness > 0), id);
      for (const l of el.layers) if (l.material) assert.ok(e.materials.includes(l.material) && all.get(l.material)?.kind === 'material', `${id}: ${l.material}`);
      continue;
    }
    if (e.kind === 'material') {
      assert.match(el.color, /^#[0-9a-f]{6}$/);
      assert.ok(el.roughness >= 0 && el.roughness <= 1000);
      assert.equal(el.texture, undefined);
      continue;
    }
    assert.ok(el.width > 0 && el.height > 0 && (el.sill ?? 0) >= 0, id);
    const c = el.clearOpening;
    if (el.operation === 'fixed') { assert.equal(c, undefined, `${id}: a fixed window has no clear opening`); continue; }
    assert.ok(c && c.width > 0 && c.height > 0 && c.width <= el.width && c.height <= el.height, id);
    if (el.kind === 'doorType') assert.equal(c.area, undefined, `${id}: a door's clear opening has no area`);
    else assert.ok(c.area >= 1 && c.area <= c.width * c.height && Number.isSafeInteger(c.area), id);
    for (const env of Object.values((el.clearances ?? {}) as Obj))
      for (const k of [0, 1, 2]) assert.ok(env.min[k] < env.max[k], `${id}: an envelope with volume`);
  }
});

test('projects embed the types they use: a document embedding every item matches Core 0.3\'s schema, and Core 0.2\'s has no source', () => {
  let doc = empty();
  for (const id of all.keys()) doc = apply(doc, embed(doc, id));
  assert.equal(Object.keys(doc.types).length, WALLS.length + DOORS.length + WINDOWS.length);
  assert.equal(Object.keys(doc.materials).length, MATERIALS.length);
  accepts(doc);
  const old: Obj = { ...structuredClone(doc), floorspec: '0.2' };
  assert.ok(!validateText(JSON.stringify(old), v02).valid, 'Core 0.2 has no source member');
  for (const t of Object.values(old.types as Obj)) delete t.source;
  for (const m of Object.values(old.materials as Obj)) { delete m.source; delete m.roughness; }
  for (const t of Object.values(old.types as Obj)) { delete t.operation; delete t.clearOpening; }
  accepts(old, v02);
});

test('each item\'s embed batch is the Ops 0.3 request that embeds it into a document without it', () => {
  for (const [id, e] of all) {
    assert.deepEqual(e.embed, embed(empty(), id), id);
    assert.deepEqual(index.items[id].embed, e.embed);
    const r = validateText(JSON.stringify({ batch: e.embed }), opsRequest);
    assert.ok(r.valid, `${id}: ${formatErrors(r.errors).join('\n')}`);
    accepts(apply(empty(), e.embed));
  }
  const wall = all.get('wall-2x6-exterior-brick-veneer')!;
  assert.deepEqual(wall.embed.map((op) => op.id), [...wall.materials, 'wall-2x6-exterior-brick-veneer']);
  assert.deepEqual(wall.materials, ['brick-veneer', 'weather-resistive-barrier', 'osb-sheathing', 'wood-stud-framing-insulated', 'gypsum-board']);
});

test('embedding is idempotent, shares materials, and a different element under the same ID is a conflict resolved by other IDs', () => {
  let doc = apply(empty(), embed(empty(), 'wall-2x4-interior'));
  assert.deepEqual(embed(doc, 'wall-2x4-interior'), [], 'embedding the same item again adds nothing');
  const next = embed(doc, 'wall-2x6-exterior-fibre-cement');
  assert.deepEqual(next.map((op) => op.id), ['fibre-cement-siding', 'weather-resistive-barrier', 'osb-sheathing', 'wood-stud-framing-insulated', 'wall-2x6-exterior-fibre-cement'],
    'gypsum board is already there, and is not embedded twice');
  doc = apply(doc, next);
  accepts(doc);

  const edited = structuredClone(doc);
  edited.materials['gypsum-board'].color = '#ffffff';
  assert.throws(() => embed(edited, 'wall-2x6-interior'), EmbedConflict);
  const ops = embed(edited, 'wall-2x6-interior', { 'gypsum-board': 'gypsum-board-2', 'wall-2x6-interior': 'W26' });
  assert.deepEqual(ops.map((op) => op.id), ['gypsum-board-2', 'W26']);
  const placed = apply(edited, ops);
  assert.deepEqual(placed.types.W26.layers.map((l: Obj) => l.material), ['gypsum-board-2', 'wood-stud-framing', 'gypsum-board-2']);
  assert.equal(placed.types.W26.source.item, 'wall-2x6-interior', 'the source still names the library item');
  accepts(placed);
  assert.deepEqual(embed(placed, 'wall-2x6-interior', { 'gypsum-board': 'gypsum-board-2', 'wall-2x6-interior': 'W26' }), []);
  assert.throws(() => embed(doc, 'no-such-item'), /no item/);
});

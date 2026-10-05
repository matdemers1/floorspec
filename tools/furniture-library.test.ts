import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { build, conventionalBox, defaultEnvelopes, ITEMS, LIBRARY_DIR, MM, mounting } from './furniture-library.ts';

/** The FS_furniture starter library (FLR-T-8.3, registry/FS_furniture/spec.md chapters 3, 4.2 and 7). */
const files = build();
const catalogue = JSON.parse(files.get('library.json')!.toString('utf8')) as {
  license: string;
  items: Record<string, {
    kind: string; mounting: string;
    element: { category: string; catalogue: string; clearances?: Record<string, unknown>; fallback: { box: { min: number[]; max: number[] } } };
    model: { path: string; mediaType: string; sha256: string; byteLength: number };
    symbol: { path: string; mediaType: string; sha256: string; byteLength: number };
  }>;
};

test('the library on disk is exactly what the generator writes, and writing it twice gives the same bytes', () => {
  const again = build();
  for (const [path, bytes] of files) {
    assert.ok(again.get(path)!.equals(bytes), `${path} is not deterministic`);
    assert.ok(readFileSync(join(LIBRARY_DIR, path)).equals(bytes), `${path} differs from the generator's: run pnpm library`);
  }
});

test('at least twenty items, CC0, each with its model and symbol named by digest and length', () => {
  assert.ok(ITEMS.length >= 20);
  assert.equal(catalogue.license, 'CC0-1.0');
  for (const [id, it] of Object.entries(catalogue.items)) {
    assert.equal(it.element.catalogue, id);
    for (const f of [it.model, it.symbol]) {
      const bytes = files.get(f.path)!;
      assert.equal(f.byteLength, bytes.length, `${f.path} byteLength`);
      assert.equal(f.sha256, createHash('sha256').update(bytes).digest('hex'), `${f.path} sha256`);
    }
    assert.equal(it.model.mediaType, 'model/gltf-binary');
    assert.equal(it.symbol.mediaType, 'image/svg+xml');
    assert.equal(it.mounting, mounting(it.element.category));
  }
});

test('every box is in the convention of 3.1 and carries its category\'s default envelopes (4.2)', () => {
  for (const it of ITEMS) {
    const el = catalogue.items[it.id]!.element;
    assert.deepEqual(el.fallback.box, conventionalBox(it.width * MM, it.depth * MM, it.height * MM));
    assert.deepEqual(el.clearances ?? {}, defaultEnvelopes(it.category, el.fallback.box as never));
  }
  const fridge = catalogue.items['refrigerator-900']!.element;
  assert.deepEqual(fridge.clearances, { door: { purpose: 'swing', shape: 'box', min: [700 * MM, -450 * MM, 0], max: [1600 * MM, 450 * MM, 1780 * MM] } });
  const bed = catalogue.items['bed-queen-1600']!.element.clearances!;
  assert.deepEqual(Object.keys(bed), ['left', 'right']);
  assert.deepEqual(bed.left, { purpose: 'access', shape: 'box', min: [0, 800 * MM, 0], max: [2050 * MM, 1400 * MM, 2000 * MM] });
});

test('each model is a binary glTF 2.0 whose bounds, mapped as 3.2 says, are its item\'s box', () => {
  for (const it of ITEMS) {
    const b = files.get(`models/${it.id}.glb`)!;
    assert.equal(b.readUInt32LE(0), 0x46546c67, 'magic glTF');
    assert.equal(b.readUInt32LE(4), 2);
    assert.equal(b.readUInt32LE(8), b.length);
    const jsonLength = b.readUInt32LE(12);
    assert.equal(b.readUInt32LE(16), 0x4e4f534a, 'a JSON chunk first');
    const gltf = JSON.parse(b.subarray(20, 20 + jsonLength).toString('utf8')) as { asset: { version: string }; accessors: { min?: number[]; max?: number[] }[] };
    assert.equal(gltf.asset.version, '2.0');
    const binHeader = 20 + jsonLength;
    assert.equal(b.readUInt32LE(binHeader + 4), 0x004e4942, 'a BIN chunk second');
    // glTF (X, Y, Z) m is the local point (1,280,000 X, -1,280,000 Z, 1,280,000 Y): back to millimetres
    const [min, max] = [gltf.accessors[0]!.min!, gltf.accessors[0]!.max!];
    const mm = (v: number) => Math.round(v * 1000);
    const box = conventionalBox(it.width, it.depth, it.height);   // in millimetres
    assert.deepEqual([mm(min[0]!), mm(-max[2]!), mm(min[1]!)].map((v) => v || 0), box.min, `${it.id} model min`);
    assert.deepEqual([mm(max[0]!), mm(-min[2]!), mm(max[1]!)], box.max, `${it.id} model max`);
  }
});

test('each symbol is drawn to its footprint in millimetres, front along the bottom edge (3.3)', () => {
  for (const it of ITEMS) {
    const svg = files.get(`symbols/${it.id}.svg`)!.toString('utf8');
    assert.match(svg, new RegExp(`viewBox="0 0 ${it.width} ${it.depth}"`));
    assert.doesNotMatch(svg, /<text|<image|href=/, 'no fonts, no linked images: the same drawing everywhere');
  }
  // the sofa's back is at the top of its symbol: its first part after the seat is a band 200 mm deep at y = 0
  assert.match(files.get('symbols/sofa-2100.svg')!.toString('utf8'), /<rect x="0" y="0" width="2100" height="200"/);
});

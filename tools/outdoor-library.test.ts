import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { build, FT, IN, ITEMS, LIBRARY_FILE } from './outdoor-library.ts';

/** The FS_outdoor starter library (FLR-T-15.2, registry/FS_outdoor/spec.md chapters 2, 3.3 and 7). */
const catalogue = JSON.parse(build()) as {
  license: string;
  items: Record<string, { kind: string; element: Record<string, unknown> & { catalogue: string; name: string; fallback: { box: { min: number[]; max: number[] } } } }>;
};

const ext = (b: { min: number[]; max: number[] }): number[] => [0, 1, 2].map((i) => b.max[i]! - b.min[i]!);

test('library.json is exactly what the generator writes, the same bytes every time', () => {
  assert.equal(build(), build());
  assert.equal(readFileSync(LIBRARY_FILE, 'utf8'), build(), 'run pnpm library:outdoor');
});

test('every item is CC0, labelled with its ID, centred on its frame and keeps the invariants of chapter 2', () => {
  assert.equal(catalogue.license, 'CC0-1.0');
  assert.equal(Object.keys(catalogue.items).length, ITEMS.length);
  for (const [id, it] of Object.entries(catalogue.items)) {
    const el = it.element;
    const box = el.fallback.box;
    const [x, y, z] = ext(box);
    assert.equal(el.catalogue, id);
    for (const v of [...box.min, ...box.max]) assert.ok(Number.isInteger(v));
    assert.deepEqual([box.min[0], box.min[1]], [0 - Math.floor(x! / 2) || 0, 0 - Math.floor(y! / 2) || 0], `${id}: centred (3.3.1)`);
    assert.ok(z! > 0, `${id}: has a height`);
    if (it.kind === 'pools') {
      assert.ok(2 * (el['coping'] as number) < Math.min(x!, y!), `${id}: 2.2.1`);
      assert.ok((el['waterLine'] as number) < z!, `${id}: 2.2.2`);
    }
    if (it.kind === 'shelters') {
      assert.ok((el['postSize'] as number) < Math.min(x!, y!), `${id}: 2.4.1`);
      assert.ok((el['postSpacing'] as number) > (el['postSize'] as number), `${id}: 2.4.2`);
      if (el['clearHeight'] !== undefined) assert.ok((el['clearHeight'] as number) < z!, `${id}: 2.4.3`);
    }
    if (it.kind === 'fences') assert.ok(x === 0 && y === 0 && el['points'] === undefined, `${id}: a style to draw`);
  }
});

test('the plunge pool of the board: 8 by 14 feet, 5 feet 6 deep, a foot of coping', () => {
  const box = catalogue.items['plunge-pool-8x14']!.element.fallback.box;
  assert.deepEqual(ext(box), [8 * FT, 14 * FT, 66 * IN]);
  assert.equal(catalogue.items['plunge-pool-8x14']!.element['coping'], 12 * IN);
});

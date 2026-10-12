import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { build, ITEMS, LIBRARY_FILE, MM, sizeClass, type Form } from './landscape-library.ts';

/** The FS_landscape starter sizes (FLR-T-13.5, registry/FS_landscape/spec.md 2.3, 3.3 and chapter 7). */
const catalogue = JSON.parse(build()) as {
  license: string;
  items: Record<string, { kind: string; size: string; element: { form: Form; catalogue: string; clearHeight?: number; fallback: { box: { min: number[]; max: number[] } } } }>;
};

test('library.json is exactly what the generator writes, the same bytes every time', () => {
  assert.equal(build(), build());
  assert.equal(readFileSync(LIBRARY_FILE, 'utf8'), build(), 'run pnpm library:landscape');
});

test('a plant of each form in each size class, CC0, each in the class its box puts it in', () => {
  assert.equal(catalogue.license, 'CC0-1.0');
  assert.equal(Object.keys(catalogue.items).length, 12);
  for (const [id, it] of Object.entries(catalogue.items)) {
    const { form, catalogue: label, clearHeight, fallback } = it.element;
    const { min, max } = fallback.box;
    assert.equal(label, id);
    assert.equal(it.kind, 'plants');
    assert.equal(id, `${form}-${it.size}`);
    const h = max[2]! - min[2]!;
    assert.equal(sizeClass(form, h), it.size, `${id}: its height puts it in another class`);
    // 3.3: centred on its position, planted at grade, square in plan
    assert.deepEqual([min[0], min[1], min[2]], [-Math.floor((max[0]! - min[0]!) / 2), -Math.floor((max[1]! - min[1]!) / 2), 0]);
    assert.equal(max[0]! - min[0]!, max[1]! - min[1]!);
    for (const v of [...min, ...max]) assert.ok(Number.isInteger(v));
    if (clearHeight !== undefined) assert.ok(form === 'tree' && clearHeight < h, `${id}: clearHeight (2.2.1)`);
  }
});

test('the class bounds of spec.md 2.3', () => {
  assert.equal(sizeClass('tree', 8000 * MM - 1), 'small');
  assert.equal(sizeClass('tree', 8000 * MM), 'medium');
  assert.equal(sizeClass('tree', 14000 * MM), 'large');
  assert.equal(sizeClass('groundcover', 150 * MM), 'medium');
  assert.equal(ITEMS.length, 12);
});

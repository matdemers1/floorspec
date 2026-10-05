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

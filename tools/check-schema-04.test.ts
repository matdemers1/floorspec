import { test } from 'node:test';
import assert from 'node:assert/strict';
import { coreSchemaDir, coreValidator, createAjv, defaults, formatErrors, loadSchemaFiles, undefinedRequired, validateText, versionedValidator } from './schema.ts';

/** Floorspec Core 0.4's schema: what it adds to 0.3 - a stair's minHeadroom (17.1) and a winder stair's newel (17.2). */
const files = loadSchemaFiles(coreSchemaDir('0.4'));
const v04 = coreValidator('0.4', createAjv(files));
const v03 = coreValidator('0.3');
const reader = versionedValidator({ '0.1': coreValidator('0.1'), '0.2': coreValidator('0.2'), '0.3': v03, '0.4': v04 });
const reader03 = versionedValidator({ '0.1': coreValidator('0.1'), '0.2': coreValidator('0.2'), '0.3': v03, '0.4': v04 }, '0.3');

const accepts = (doc: unknown, v = v04) => {
  const r = validateText(JSON.stringify(doc), v);
  assert.ok(r.valid, `expected the schema to accept, got:\n${formatErrors(r.errors).join('\n')}`);
};
const rejects = (doc: unknown, v = v04) => assert.ok(!validateText(JSON.stringify(doc), v).valid, `expected the schema to reject ${JSON.stringify(doc)}`);

const MM = 1280;
const WQ = { kind: 'winder', turn: 'left', angle: 'quarter', risersBeforeTurn: 4, winders: 3 };
function stairs(): Record<string, any> {
  return {
    floorspec: '0.4',
    project: { name: 'Stairs' },
    stairs: {
      ST1: { level: 'L1', to: 'L2', position: [0, 0], width: 900 * MM, tread: 250 * MM, risers: 14, minHeadroom: 2032 * MM, form: { ...WQ, newel: 100 * MM } },
      ST2: { level: 'L1', to: 'L2', position: [0, 0], width: 900 * MM, tread: 250 * MM, risers: 15, form: { ...WQ, angle: 'half', winders: 6, gap: 100 * MM, newel: 50 * MM } },
      ST3: { level: 'L1', to: 'L2', position: [0, 0], width: 800 * MM, tread: 220 * MM, risers: 13, form: { kind: 'spiral', turn: 'left', diameter: 1800 * MM, sweep: 270_000_000 } },
    },
  };
}
const s = (mut: (d: Record<string, any>) => void) => {
  const d = stairs();
  mut(d);
  return d;
};

test('core 0.4: every file compiles strictly and declares what it requires', () => {
  assert.deepEqual(undefinedRequired(files), []);
});

test('core 0.4: a document using both members 0.4 adds is valid', () => accepts(stairs()));

test('core 0.4: the declared version is "0.4"; a 0.4 reader checks "0.1", "0.2" and "0.3" documents against their own drafts', () => {
  rejects({ ...stairs(), floorspec: '0.3' }, reader);
  accepts({ floorspec: '0.3', project: { name: 'x' }, stairs: {} }, reader);
  accepts({ floorspec: '0.2', project: { name: 'x' }, program: {} }, reader);
  rejects({ floorspec: '0.4', project: { name: 'x' } }, v03);
  // a reader of 0.3 checks a "0.4" document against 0.3's schema, which rejects its version
  rejects({ floorspec: '0.4', project: { name: 'x' } }, reader03);
  accepts({ floorspec: '0.4', project: { name: 'x' } }, reader);
});

test('core 0.4, 17.1.3 and 17.2.3: minHeadroom and newel are greater than zero, and only a winder has a newel', () => {
  rejects(s((d) => (d.stairs.ST1.minHeadroom = 0)));
  rejects(s((d) => (d.stairs.ST1.minHeadroom = -1)));
  rejects(s((d) => (d.stairs.ST1.form.newel = 0)));
  rejects(s((d) => (d.stairs.ST3.form.newel = 1)));
  rejects(s((d) => (d.stairs.ST3.form = { kind: 'lShaped', turn: 'left', risersBeforeTurn: 7, newel: 1 })));
  rejects(s((d) => (d.stairs.ST3.form = { kind: 'uShaped', turn: 'left', risersBeforeTurn: 7, newel: 1 })));
  // a newel that reaches the walkline (17.7.4) is an invariant, not the schema's
  accepts(s((d) => (d.stairs.ST1.form.newel = 900 * MM)));
});

test('core 0.4: neither member 0.4 adds has a default', () => {
  const found = [...defaults(files)].map(([where]) => where);
  for (const f of found) assert.ok(!/newel|minHeadroom/.test(f), f);
});

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { buildAll } from './build-pack.ts';
import {
  buildPack,
  buildRule,
  canonicalJson,
  compareSections,
  deferredMeasures,
  formatValidators,
  loadPack,
  RULES_DIR,
  ruleMeasures,
  within,
  type RuleFile,
} from './packs.ts';
import { formatErrors } from './schema.ts';

/** The rule-pack format (FLR-T-6.3): its schemas, its assembly into the evaluator's pack object, and its helpers. */
const v = formatValidators();
const example = loadPack(join(RULES_DIR, 'example'));
const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x)) as T;
const ruleOf = (id: string) => clone(example.rules.find((r) => r.id === id)!.rule);

const accepts = (validate: typeof v.rule, value: unknown) => assert.ok(validate(value), formatErrors(validate.errors ?? []).join('\n'));
const rejects = (validate: typeof v.rule, value: unknown) => assert.ok(!validate(value), `expected a rejection of ${JSON.stringify(value)}`);

test('the example pack reads cleanly: a manifest, three rules, six fixtures', () => {
  assert.deepEqual(example.problems, []);
  assert.deepEqual(example.rules.map((r) => r.id), ['ROOM-SIZE', 'SMOKE-ALARM', 'STAIR-RISER']);
  assert.equal(example.rules.flatMap((r) => r.fixtures).length, 6);
});

test('a rule on disk carries a viewer link, the certification and a review mark (FLR-REQ-094, 163, 164)', () => {
  const r = ruleOf('SMOKE-ALARM');
  accepts(v.rule, r);
  const { link: _, ...unlinked } = r.citation;
  rejects(v.rule, { ...r, citation: unlinked });
  rejects(v.rule, { ...r, citation: { ...r.citation, link: 'http://example.org/x' } });
  for (const k of ['verifiedBy', 'verifiedOn', 'edition', 'method', 'certifiedBy', 'certification', 'review'] as const) {
    const p: Record<string, unknown> = { ...r.provenance };
    delete p[k];
    rejects(v.rule, { ...r, provenance: p });
  }
  rejects(v.rule, { ...r, provenance: { ...r.provenance, certification: 'original-paraphrase' } });
  rejects(v.rule, { ...r, provenance: { ...r.provenance, method: 'scraped' } });
});

test('a review is the unreviewed mark, or a badge naming a licensed reviewer, their credential and the date', () => {
  const r = ruleOf('SMOKE-ALARM');
  const review = (x: unknown) => ({ ...r, provenance: { ...r.provenance, review: x } });
  accepts(v.rule, review({ status: 'unreviewed' }));
  accepts(v.rule, review({ status: 'reviewed', by: 'A Reviewer', on: '2026-10-05', credential: 'Licensed architect (ME)' }));
  accepts(v.rule, review({ status: 'reviewed', by: 'A Reviewer', on: '2026-10-05', credential: 'Licensed architect (ME)', scope: 'The thresholds.' }));
  rejects(v.rule, review({ status: 'reviewed', by: 'A Reviewer', on: '2026-10-05' }));
  rejects(v.rule, review({ status: 'unreviewed', by: 'A Reviewer' }));
  rejects(v.rule, review({}));
});

test('only the verbatim heuristics can be overridden, and only with a reviewer, a date and a note', () => {
  const r = ruleOf('SMOKE-ALARM');
  const o = (x: unknown) => ({ ...r, provenance: { ...r.provenance, lintOverrides: [x] } });
  accepts(v.rule, o({ check: 'verbatim-shall', reviewer: 'R', on: '2026-10-05', note: 'A defined term of the code.' }));
  rejects(v.rule, o({ check: 'assurance', reviewer: 'R', on: '2026-10-05', note: 'n' }));
  rejects(v.rule, o({ check: 'viewer-host', reviewer: 'R', on: '2026-10-05', note: 'n' }));
  rejects(v.rule, o({ check: 'verbatim-shall', reviewer: 'R', on: '2026-10-05' }));
});

test('extras.packFormat is the format\'s, never a contributor\'s', () => {
  rejects(v.rule, { ...ruleOf('SMOKE-ALARM'), extras: { packFormat: {} } });
  rejects(v.manifest, { ...clone(example.manifest), extras: { packFormat: {} } });
});

test('a manifest is CC BY 4.0 with attribution, jurisdiction, editions, maintainers, domains and coverage (FLR-REQ-096)', () => {
  const m = clone(example.manifest);
  accepts(v.manifest, m);
  rejects(v.manifest, { ...m, license: 'CC-BY-SA-4.0' });
  for (const k of ['attribution', 'jurisdiction', 'editions', 'maintainers', 'domains', 'coverage'] as const) {
    const x: Record<string, unknown> = { ...m };
    delete x[k];
    rejects(v.manifest, x);
  }
  rejects(v.manifest, { ...m, editions: [] });
  rejects(v.manifest, { ...m, coverage: [{ code: 'TEST-CODE', edition: '2024', section: '§9', status: 'addressed' }] });
});

test('a fixture expects pass, deferred, or fail with exactly the subjects that get findings', () => {
  accepts(v.fixture, { description: 'd', outcome: 'pass' });
  accepts(v.fixture, { description: 'd', outcome: 'fail', findings: ['R1'] });
  accepts(v.fixture, { description: 'd', outcome: 'deferred', document: 'rules-house' });
  rejects(v.fixture, { description: 'd', outcome: 'fail' });
  rejects(v.fixture, { description: 'd', outcome: 'pass', findings: ['R1'] });
  rejects(v.fixture, { description: 'd', outcome: 'maybe' });
});

test('assembly: the evaluator\'s minimum provenance, the badge as provenance.reviewed, the rest in extras.packFormat', () => {
  const reviewed = buildRule(ruleOf('ROOM-SIZE')) as Record<string, any>;
  assert.deepEqual(reviewed.provenance, {
    verifiedBy: 'Floorspec contributors', verifiedOn: '2026-10-05', edition: '2024',
    reviewed: { by: 'Example Reviewer (synthetic)', on: '2026-10-05', credential: 'Licensed architect (synthetic example)' },
  });
  assert.equal(reviewed.extras.packFormat.review, 'reviewed');
  assert.equal(reviewed.extras.packFormat.certification, 'original-paraphrase-v1');
  assert.equal(reviewed.citation.link, 'https://example.org/test-code/2024/1.2');
  const unreviewed = buildRule(ruleOf('SMOKE-ALARM')) as Record<string, any>;
  assert.equal(unreviewed.provenance.reviewed, undefined);
  assert.equal(unreviewed.extras.packFormat.review, 'unreviewed');
});

test('a built pack matches the evaluator\'s pack schema, and builds to the same bytes every time', () => {
  const pack = buildPack(example);
  accepts(v.pack, pack);
  assert.equal(canonicalJson(buildPack(loadPack(join(RULES_DIR, 'example')))), canonicalJson(pack));
  const r = clone(ruleOf('SMOKE-ALARM')) as RuleFile;
  r.select = { from: 'elements', need: 'any' };
  r.exceptions = [{ when: { measure: 'roomIsEntry', op: '=', value: true }, note: 'Entries are left out.' }];
  accepts(v.pack, { ...pack, rules: { X: buildRule(r) } });
});

test('canonical JSON: members sorted by UTF-16 code units, two-space indent, a final line feed, integers only', () => {
  assert.equal(canonicalJson({ b: 1, a: [{ d: 2, c: 'é' }], A: true }), '{\n  "A": true,\n  "a": [\n    {\n      "c": "é",\n      "d": 2\n    }\n  ],\n  "b": 1\n}\n');
  assert.throws(() => canonicalJson({ a: 1.5 }));
});

test('sections: containment and natural order', () => {
  assert.ok(within('R310.2.1', 'R310'));
  assert.ok(within('210.52(A)(1)', '210.52'));
  assert.ok(within('§1.2', '§1'));
  assert.ok(within('R310', 'R310'));
  assert.ok(!within('R3101', 'R310'));
  assert.ok(!within('R31', 'R310'));
  const sorted = ['R310.10', 'R310.2', 'R302', 'R310', '§10', '§2'].sort(compareSections);
  assert.deepEqual(sorted, ['R302', 'R310', 'R310.2', 'R310.10', '§2', '§10']);
});

test('the deferred measures are read from spec/rules 4.8', () => {
  const d = deferredMeasures();
  for (const m of ['roomNarrowestDimension', 'floorElevationDifference', 'travelDistance', 'countertopReceptacleReach']) assert.ok(d.has(m), m);
  assert.ok(!d.has('roomNetArea'));
  // defined since Core 0.3 derives ceilings (spec/rules 5.7) and stairs (spec/rules 8.5)
  assert.ok(!d.has('ceilingHeight'));
  for (const m of ['stairRiserHeight', 'stairTreadDepth', 'stairWidth', 'stairHeadroom', 'stairHandrailHeight']) assert.ok(!d.has(m), m);
});

test('a rule\'s measures are found in where, select, requirement and exceptions', () => {
  const m = ruleMeasures({
    applies: { where: { measure: 'a', op: '=', value: 1 } },
    select: { where: { not: { measure: 'b', op: '=', value: 1 } } },
    requirement: { all: [{ measure: 'c', op: '=', value: 1 }, { any: [{ measure: 'd', op: '=', value: 1 }] }] },
    exceptions: [{ when: { measure: 'e', op: '=', value: 1 } }],
  });
  assert.deepEqual([...m].sort(), ['a', 'b', 'c', 'd', 'e']);
});

test('the generated files under rules/ are what the packs build to (pnpm packs)', () => {
  const result = buildAll({ fixtures: false });
  assert.deepEqual(result.problems, []);
  for (const o of result.outputs) {
    assert.ok(existsSync(o.path), `${o.path} is missing: run pnpm packs`);
    assert.equal(readFileSync(o.path, 'utf8'), o.text, `${o.path} differs: run pnpm packs`);
  }
});

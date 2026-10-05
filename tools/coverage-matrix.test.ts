import { test } from 'node:test';
import assert from 'node:assert/strict';
import { coverageMatrix, matrixMarkdown, type Matrix } from './coverage-matrix.ts';
import { assurancePattern } from './lint-rules.ts';
import { canonicalJson, deferredMeasures } from './packs.ts';

/** The coverage matrix (FLR-T-6.3, FLR-REQ-096), from a synthetic pack built by hand. */
const deferred = deferredMeasures();
const C = (measure: string, op = '>=', value: unknown = 1) => ({ measure, op, value });
const R = (section: string, requirement: unknown, verifiedOn: string, reviewed?: { by: string; on: string; credential?: string }, code = 'TEST-CODE') => ({
  title: `Rule at ${section}`,
  citation: { code, edition: '2024', section, link: `https://example.org/${section}` },
  paraphrase: 'A synthetic rule.',
  applies: { to: 'room' },
  requirement,
  severity: 'mayNotMeet',
  provenance: { verifiedBy: 'Tests', verifiedOn, edition: '2024', ...(reviewed ? { reviewed } : {}) },
  extras: { packFormat: { review: reviewed ? 'reviewed' : 'unreviewed' } },
});
const pack = {
  floorspecRules: '0.1',
  name: 'synthetic',
  version: '1.2.0',
  title: 'Synthetic pack',
  license: 'CC-BY-4.0',
  rules: {
    'A-1': R('§1.1', C('roomNetArea'), '2026-10-01', { by: 'An Architect', on: '2026-10-03', credential: 'Licensed architect (ME)' }),
    'A-2': R('§1.10', C('roomLeastWidth'), '2026-09-01'),
    'B-1': R('§2.1', C('travelDistance'), '2026-10-02'),
    'C-1': R('§3.1', C('roomNetArea'), '2026-10-04'),
    'C-2': R('§3.2', C('countertopReceptacleReach'), '2026-10-04'),
    'D-1': R('§5.1', C('roomNetArea'), '2026-10-04'),
    'E-1': R('§9', C('roomNetArea'), '2026-10-05'),
  },
  coverage: [
    { code: 'TEST-CODE', edition: '2024', section: '§1', status: 'addressed', note: 'All of chapter 1.' },
    { code: 'TEST-CODE', edition: '2024', section: '§2', status: 'addressed' },
    { code: 'TEST-CODE', edition: '2024', section: '§3', status: 'addressed' },
    { code: 'TEST-CODE', edition: '2024', section: '§4', status: 'notAddressed', note: 'Later.' },
    { code: 'TEST-CODE', edition: '2024', section: '§5', status: 'partial' },
    { code: 'TEST-CODE', edition: '2024', section: '§6', status: 'notAddressed' },
  ],
  extras: {
    packFormat: {
      attribution: 'Tests, CC BY 4.0',
      jurisdiction: 'Nowhere',
      synthetic: true,
      domains: [{ id: 'rooms', title: 'Rooms' }, { id: 'heights', title: 'Heights' }],
      coverage: [{ domain: 'rooms' }, { domain: 'heights' }, { domain: 'rooms' }, { domain: 'rooms' }, { domain: 'rooms' }, { domain: 'heights', needs: ['travelDistance'] }],
    },
  },
};

const m: Matrix = coverageMatrix([pack], deferred);
const row = (section: string) => m.rows.find((r) => r.section === section)!;

test('status: covered, partial, deferred with the measure named, not covered', () => {
  assert.equal(row('§1').status, 'covered');
  assert.deepEqual(row('§1').rules.map((r) => r.rule), ['A-1', 'A-2']);
  assert.equal(row('§2').status, 'deferred');
  assert.deepEqual(row('§2').needs, ['travelDistance']);
  assert.equal(row('§3').status, 'partial');
  assert.deepEqual(row('§3').needs, ['countertopReceptacleReach']);
  assert.equal(row('§4').status, 'notCovered');
  assert.equal(row('§5').status, 'partial');
  assert.equal(row('§6').status, 'deferred');
  assert.deepEqual(row('§6').needs, ['travelDistance']);
});

test('a rule within no coverage entry still gets a row, declared "undeclared"', () => {
  assert.equal(row('§9').declared, 'undeclared');
  assert.equal(row('§9').status, 'covered');
  assert.equal(row('§9').domain, null);
});

test('reviewed badges and verification dates, per rule, per row and per domain', () => {
  assert.equal(row('§1').reviewed, 1);
  assert.equal(row('§1').oldestVerification, '2026-09-01');
  assert.equal(row('§1').newestVerification, '2026-10-01');
  const a1 = m.rules.find((r) => r.rule === 'A-1')!;
  assert.equal(a1.review, 'reviewed');
  assert.deepEqual(a1.reviewed, { by: 'An Architect', on: '2026-10-03', credential: 'Licensed architect (ME)' });
  assert.equal(m.rules.find((r) => r.rule === 'A-2')!.review, 'unreviewed');
  const rooms = m.domains.find((d) => d.domain === 'rooms')!;
  assert.deepEqual(rooms.sections, { covered: 1, partial: 2, deferred: 0, notCovered: 1 });
  assert.equal(rooms.rules, 5);
  assert.equal(rooms.reviewed, 1);
  assert.equal(rooms.oldestVerification, '2026-09-01');
  const heights = m.domains.find((d) => d.domain === 'heights')!;
  assert.deepEqual(heights.sections, { covered: 0, partial: 0, deferred: 2, notCovered: 0 });
  assert.deepEqual(m.domains.map((d) => d.title), ['Rooms', 'Heights', 'No domain']);
  assert.deepEqual(m.packs[0], {
    name: 'synthetic', version: '1.2.0', title: 'Synthetic pack', license: 'CC-BY-4.0', attribution: 'Tests, CC BY 4.0',
    jurisdiction: 'Nowhere', synthetic: true, rules: 7, reviewed: 1,
  });
});

test('rows run in natural section order, and the matrix is deterministic', () => {
  assert.deepEqual(m.rows.map((r) => r.section), ['§1', '§2', '§3', '§4', '§5', '§6', '§9']);
  const shuffled = { ...pack, rules: Object.fromEntries(Object.entries(pack.rules).reverse()) };
  assert.equal(canonicalJson(coverageMatrix([shuffled], deferred)), canonicalJson(m));
  assert.equal(matrixMarkdown(coverageMatrix([shuffled], deferred), 'T'), matrixMarkdown(m, 'T'));
});

test('a pack without the format\'s extras still has a matrix', () => {
  const { extras: _, ...bare } = pack;
  const b = coverageMatrix([{ ...bare, rules: { 'A-1': { ...pack.rules['A-1'], extras: {} } } }], deferred);
  assert.equal(b.rows[0]!.status, 'covered');
  assert.equal(b.rows[0]!.domain, null);
  assert.equal(b.rules[0]!.review, 'reviewed');
  assert.equal(b.packs[0]!.attribution, null);
});

test('the Markdown carries the notice, every section and status, and never the assurance pattern', () => {
  const md = matrixMarkdown(m, 'Coverage: synthetic');
  assert.match(md, /^# Coverage: synthetic\n/);
  assert.match(md, /They are not a plan review/);
  assert.match(md, /\| §2 \| `synthetic` \| Heights \| deferred \(needs data\): `travelDistance` \|/);
  assert.match(md, /\| §4 \| `synthetic` \| Rooms \| not covered \|/);
  assert.match(md, /reviewed by An Architect \(Licensed architect \(ME\)\), 2026-10-03/);
  assert.match(md, /`synthetic\/A-2` Rule at §1.10 \| \[TEST-CODE 2024 §1.10\]\(https:\/\/example.org\/§1.10\) \| mayNotMeet \| 2026-09-01 \| Tests \| unreviewed \|/);
  assert.ok(!assurancePattern().test(md));
  assert.ok(!assurancePattern().test(canonicalJson(m)));
  assert.match(matrixMarkdown(coverageMatrix([], deferred), 'Empty'), /No pack is published yet/);
});

test('a table cell never breaks the table', () => {
  const p = { ...pack, coverage: [{ ...pack.coverage[0]!, note: 'a | b\nc' }] };
  assert.match(matrixMarkdown(coverageMatrix([p], deferred), 'T'), /a \\\| b c/);
});

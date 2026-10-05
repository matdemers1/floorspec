import { test } from 'node:test';
import assert from 'node:assert/strict';
import { defaultProfile, formatErrors, hasDuplicateMember, rulesValidators, validateText } from './schema.ts';

/** Floorspec Rules 0.1's schemas: request, pack, rule, profile, report (spec/rules 1.1, 2.1, 3, 10.1, 9.1). */
const rv = rulesValidators();

const accepts = (v: typeof rv.pack, value: unknown) => {
  const r = validateText(JSON.stringify(value), v);
  assert.ok(r.valid, `expected the schema to accept, got:\n${formatErrors(r.errors).join('\n')}`);
};
const rejects = (v: typeof rv.pack, value: unknown) => {
  const r = validateText(typeof value === 'string' ? value : JSON.stringify(value), v);
  assert.ok(!r.valid, `expected the schema to reject ${typeof value === 'string' ? value : JSON.stringify(value)}`);
};

const condition = { measure: 'roomNetArea', op: '>=', value: 7600000000000 };
const rule = (extra: Record<string, unknown> = {}) => ({
  title: 'A synthetic rule',
  citation: { code: 'TEST-CODE', edition: '2024', section: '§1.1', link: 'https://example.com/1.1' },
  paraphrase: 'A synthetic rule for the schema tests.',
  applies: { to: 'room', where: { measure: 'roomFunction', op: '=', value: 'sleeping' } },
  requirement: condition,
  severity: 'mayNotMeet',
  provenance: { verifiedBy: 'Tests', verifiedOn: '2026-10-04', edition: '2024' },
  ...extra,
});
const pack = (extra: Record<string, unknown> = {}) => ({
  floorspecRules: '0.1', name: 'test-pack', version: '0.1.0', title: 'Tests', license: 'CC-BY-4.0', rules: { R1: rule() }, ...extra,
});

test('a pack with a well-formed rule matches the pack schema', () => {
  accepts(rv.pack, pack({ coverage: [{ code: 'TEST-CODE', edition: '2024', section: '§1', status: 'partial', note: 'n' }], extras: {} }));
  accepts(rv.pack, pack({ rules: {} }));
});

test('every pack is CC BY 4.0 and declares Rules 0.1', () => {
  rejects(rv.pack, pack({ license: 'MIT' }));
  rejects(rv.pack, pack({ floorspecRules: '0.2' }));
  const { license: _, ...unlicensed } = pack();
  rejects(rv.pack, unlicensed);
});

test('a pack name is lowercase words joined by hyphens, and a rule ID is a Core ID', () => {
  rejects(rv.pack, pack({ name: 'Test_Pack' }));
  rejects(rv.pack, pack({ name: 'test--pack' }));
  rejects(rv.pack, pack({ rules: { 'R 1': rule() } }));
});

test('tests: a condition, all, any or not - exactly one form', () => {
  accepts(rv.pack, pack({ rules: { R1: rule({ requirement: { all: [condition, { any: [condition, { not: condition }] }] } }) } }));
  accepts(rv.pack, pack({ rules: { R1: rule({ requirement: { measure: 'roomFunction', op: 'in', value: ['a', 'b'] } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ requirement: { all: [] } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ requirement: { all: [condition], any: [condition] } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ requirement: { ...condition, op: '~' } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ requirement: { ...condition, measure: 'RoomNetArea' } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ requirement: { ...condition, value: [] } }) } }));
});

test('a threshold is a JSON integer: 1.0 and 1e3 are not', () => {
  rejects(rv.pack, JSON.stringify(pack()).replace('"value":7600000000000', '"value":7600000000000.0'));
  rejects(rv.pack, JSON.stringify(pack()).replace('"value":7600000000000', '"value":76e11'));
  rejects(rv.pack, pack({ rules: { R1: rule({ requirement: { ...condition, value: 2 ** 53 } }) } }));
});

test('a severity is advisory: never an error', () => {
  for (const s of ['mayNotMeet', 'check', 'note']) accepts(rv.pack, pack({ rules: { R1: rule({ severity: s }) } }));
  for (const s of ['error', 'warning', 'info', 'pass']) rejects(rv.pack, pack({ rules: { R1: rule({ severity: s }) } }));
});

test('a citation has a code, an edition and a section, and an https link', () => {
  rejects(rv.pack, pack({ rules: { R1: rule({ citation: { code: 'irc', edition: '2024', section: 'R310' } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ citation: { code: 'IRC', edition: '2024', section: ' R310' } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ citation: { code: 'IRC', edition: '2024', section: 'R310\n' } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ citation: { code: 'IRC', edition: '2024', section: 'R310', link: 'http://x.org' } }) } }));
  accepts(rv.pack, pack({ rules: { R1: rule({ citation: { code: 'NEC', edition: '2026', section: '110.26(A)(1)' } }) } }));
});

test('provenance: who, when and which edition; a review is optional', () => {
  accepts(rv.pack, pack({ rules: { R1: rule({ provenance: { verifiedBy: 'A', verifiedOn: '2026-10-04', edition: '2024', reviewed: { by: 'B', on: '2026-10-05', credential: 'RA' } } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ provenance: { verifiedBy: 'A', verifiedOn: '2026-13-04', edition: '2024' } }) } }));
  rejects(rv.pack, pack({ rules: { R1: rule({ provenance: { verifiedBy: 'A', edition: '2024' } }) } }));
});

test('the request: Rules 0.1, packs, and optionally a profile and units', () => {
  accepts(rv.request, { floorspecRules: '0.1', packs: [] });
  accepts(rv.request, { floorspecRules: '0.1', packs: [{ anything: true }], profile: 'checked later', units: 'metric' });
  rejects(rv.request, { floorspecRules: '0.1' });
  rejects(rv.request, { floorspecRules: '0.1', packs: [], units: 'furlongs' });
  rejects(rv.request, { floorspecRules: '0.1', packs: [], document: {} });
});

test('a duplicate member name is found, wherever it is', () => {
  assert.equal(hasDuplicateMember('{"a": 1, "b": {"c": [1, {"d": 1, "d": 2}]}}'), true);
  assert.equal(hasDuplicateMember('{"a": 1, "b": {"a": "\\"a\\""}}'), false);
});

test('the default profile is the one of 10.6, and matches the profile schema of its draft', () => {
  const p = defaultProfile() as { name: string; adopts: { code: string; edition: string }[] };
  accepts(rulesValidators(undefined, '0.2').profile, p);
  accepts(rv.profile, { ...p, floorspecRules: '0.1' });
  assert.equal(p.name, 'Model Codes (latest)');
  assert.deepEqual(p.adopts.map((a) => `${a.code} ${a.edition}`), ['IFGC 2024', 'IMC 2024', 'IPC 2024', 'IRC 2024', 'NEC 2026']);
});

test('profiles: adoptions, asOf, packs by range, amendments that withdraw rules', () => {
  const base = { floorspecRules: '0.1', name: 'Town', adopts: [{ code: 'IRC', edition: '2021', effective: '2022-01-01' }] };
  accepts(rv.profile, { ...base, asOf: '2026-10-04', packs: [{ name: 'us-model-latest', version: '^0.1.0 || >=1.0.0 <2.0.0' }],
    amendments: [{ citation: { authority: 'Town', reference: 'Ord. 1', link: 'https://example.com/ord' }, effective: '2025-01-01',
      withdraws: [{ pack: 'us-model-latest', rule: 'R310-1' }], note: 'n' }] });
  rejects(rv.profile, { ...base, packs: [{ name: 'p', version: 'latest' }] });
  rejects(rv.profile, { ...base, amendments: [{ citation: { authority: 'T', reference: 'O' }, withdraws: [] }] });
  rejects(rv.profile, { ...base, adopts: [{ code: 'IRC' }] });
});

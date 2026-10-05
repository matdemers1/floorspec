import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { failing, heuristics, lintContext, lintPack, lintRepository, type LintContext } from './lint-rules.ts';
import { loadPack, RULES_DIR, type PackSource } from './packs.ts';

/** The rule-text lint (FLR-T-6.3): every check fires on what it is for, and only heuristics yield to a reviewer. */
const base = loadPack(join(RULES_DIR, 'example'));
const ctx = lintContext();
const copy = (): PackSource => JSON.parse(JSON.stringify(base)) as PackSource;
const rule = (p: PackSource, id: string) => p.rules.find((r) => r.id === id)!.rule;
const checks = (p: PackSource, c: LintContext = ctx) => failing(lintPack(p, c)).map((f) => f.check);

// A real pack, against a viewer list of made-up hosts: no test names a real viewer.
const realCtx: LintContext = {
  ...ctx,
  viewers: { viewers: [{ host: 'viewer.invalid', publisher: 'A publisher', codes: ['XC'] }], synthetic: ['example.org'] },
};
const realPack = (): PackSource => {
  const p = copy();
  p.manifest.synthetic = false;
  p.manifest.editions = [{ code: 'XC', edition: '2024' }];
  p.manifest.domains = [{ id: 'rooms', title: 'Rooms' }];
  p.manifest.coverage = [{ code: 'XC', edition: '2024', section: '1', status: 'addressed', domain: 'rooms' }];
  p.rules = p.rules.filter((r) => r.id === 'ROOM-SIZE');
  const r = p.rules[0]!.rule;
  r.citation = { code: 'XC', edition: '2024', section: '1.2', link: 'https://viewer.invalid/xc/2024/1.2' };
  r.provenance.edition = '2024';
  r.provenance.method = 'freePublicViewer';
  return p;
};

test('the example pack lints clean', () => {
  assert.deepEqual(lintPack(base, ctx), []);
  assert.deepEqual(checks(realPack(), realCtx), []);
});

test('assurance: the pattern of spec/rules 2.5, in every text of the pack, never overridable', () => {
  for (const [where, set] of [
    ['paraphrase', (p: PackSource) => (rule(p, 'ROOM-SIZE').paraphrase += ' A compliant room is fine.')],
    ['title', (p: PackSource) => (p.manifest.title = 'Up to code checks')],
    ['attribution', (p: PackSource) => (p.manifest.attribution = 'Code-approved by everyone')],
    ['coverage note', (p: PackSource) => (p.manifest.coverage[0]!.note = 'Meets code where it can')],
    ['provenance note', (p: PackSource) => (rule(p, 'SMOKE-ALARM').provenance.note = 'It complies.')],
    ['fixture description', (p: PackSource) => (p.rules[0]!.fixtures[0]!.expect.description = 'A compliant house.')],
  ] as const) {
    const p = copy();
    set(p);
    assert.ok(checks(p).includes('assurance'), where);
  }
  const p = copy();
  const r = rule(p, 'ROOM-SIZE');
  r.paraphrase += ' It is noncompliant otherwise.';
  r.provenance.lintOverrides = [{ check: 'advice-wording', reviewer: 'R', on: '2026-10-05', note: 'n' }];
  assert.ok(checks(p).includes('assurance'));
});

test('heuristics: each fires on what it guards against', () => {
  const fired = (t: string) => heuristics(t).map((h) => h.check);
  assert.deepEqual(fired('Every bedroom needs a window a person can climb out of, low enough to reach from the floor.'), []);
  assert.ok(fired('The design passes when the room is large enough for a bed.').includes('advice-wording'));
  assert.ok(fired('The opening shall have a net clear area of at least the stated value.').includes('verbatim-shall'));
  assert.ok(fired('It asks for "an opening that a person can use to escape" in each room.').includes('verbatim-quote'));
  assert.ok(fired('Applies as R310.1, R310.2.1 and R310.2.2 say together.').includes('verbatim-sections'));
  assert.ok(fired('Sizes: 5 by 20 by 24 by 44 and 57 and 70 apply.').includes('verbatim-table'));
  assert.ok(fired('Widths | 24 | 36 are listed.').includes('verbatim-table'));
  assert.ok(fired('Every room needs one. Exception: rooms with sprinklers.').includes('verbatim-structure'));
  assert.ok(fired('It applies to 1. Bedrooms of any size and 2. Dens used for sleeping.').includes('verbatim-structure'));
  assert.ok(fired(`${'word '.repeat(51)}end.`).includes('verbatim-sentence'));
});

test('a heuristic finding yields to a recorded reviewer note; an override that no longer fires is stale', () => {
  const p = copy();
  const r = rule(p, 'ROOM-SIZE');
  r.paraphrase = 'Every room used for sleeping shall have at least 100 square feet of floor inside the wall faces.';
  assert.ok(checks(p).includes('verbatim-shall'));
  r.provenance.lintOverrides = [{ check: 'verbatim-shall', reviewer: 'A Reviewer', on: '2026-10-05', note: 'Checked against the viewer: the wording is ours.' }];
  assert.deepEqual(checks(p), []);
  const all = lintPack(p, ctx);
  assert.equal(all.length, 1);
  assert.match(all[0]!.overriddenBy!, /A Reviewer on 2026-10-05/);
  rule(p, 'SMOKE-ALARM').provenance.lintOverrides = [{ check: 'verbatim-quote', reviewer: 'R', on: '2026-10-05', note: 'n' }];
  assert.deepEqual(checks(p), ['stale-override']);
});

test('paraphrase length: 40-1200 characters and at least 8 words', () => {
  const p = copy();
  rule(p, 'ROOM-SIZE').paraphrase = 'Bedrooms need enough floor.';
  assert.deepEqual(checks(p), ['paraphrase-length']);
  rule(p, 'ROOM-SIZE').paraphrase = 'Bedrooms need floor. '.repeat(70);
  assert.ok(checks(p).includes('paraphrase-length'));
});

test('viewer-host: a real pack links to a listed viewer that publishes the code; a synthetic pack to example.org', () => {
  let p = realPack();
  p.rules[0]!.rule.citation.link = 'https://mirror.invalid/xc/2024/1.2';
  assert.deepEqual(checks(p, realCtx), ['viewer-host']);
  p = realPack();
  realCtx.viewers.viewers[0]!.codes = ['OTHER'];
  assert.deepEqual(checks(p, realCtx), ['viewer-host']);
  realCtx.viewers.viewers[0]!.codes = ['XC'];
  p = copy();
  rule(p, 'ROOM-SIZE').citation.link = 'https://viewer.invalid/test-code/1.2';
  assert.deepEqual(checks(p), ['viewer-host']);
});

test('provenance: the verified edition is the cited one, and method "synthetic" goes with a synthetic pack', () => {
  let p = copy();
  rule(p, 'ROOM-SIZE').provenance.edition = '2021';
  assert.deepEqual(checks(p), ['provenance']);
  p = copy();
  rule(p, 'ROOM-SIZE').provenance.method = 'freePublicViewer';
  assert.deepEqual(checks(p), ['provenance']);
  p = realPack();
  p.rules[0]!.rule.provenance.method = 'synthetic';
  assert.deepEqual(checks(p, realCtx), ['provenance']);
});

test('editions: every cited edition is listed, every listed edition cited; TEST- codes only in a synthetic pack', () => {
  let p = copy();
  p.manifest.editions.push({ code: 'TEST-CODE', edition: '2021' });
  assert.deepEqual(checks(p), ['edition-declared']);
  p = copy();
  p.manifest.editions = p.manifest.editions.filter((e) => e.code !== 'TEST-ELEC');
  assert.deepEqual(checks(p), ['edition-declared']);
  p = realPack();
  p.manifest.editions.push({ code: 'TEST-CODE', edition: '2024' });
  p.manifest.coverage.push({ code: 'TEST-CODE', edition: '2024', section: '9', status: 'notAddressed', domain: 'rooms' });
  assert.deepEqual(checks(p, realCtx), ['synthetic-code']);
});

test('coverage: every rule within an entry; addressed entries have rules, not-addressed ones none; needs are deferred measures', () => {
  let p = copy();
  rule(p, 'ROOM-SIZE').citation.section = '§9.1';
  assert.ok(checks(p).includes('coverage'));
  p = copy();
  p.manifest.coverage[2]!.status = 'addressed';
  assert.deepEqual(checks(p), ['coverage']);
  p = copy();
  p.manifest.coverage.push({ code: 'TEST-CODE', edition: '2024', section: '§1.2', status: 'notAddressed', domain: 'room-sizes' });
  assert.deepEqual(checks(p), ['coverage']);
  p = copy();
  p.manifest.coverage[1]!.needs = ['roomNetArea'];
  assert.deepEqual(checks(p), ['coverage']);
  p = copy();
  p.manifest.coverage[0]!.domain = 'nowhere';
  assert.ok(checks(p).includes('coverage'));
  p = copy();
  p.manifest.coverage.push({ ...p.manifest.coverage[2]! });
  assert.deepEqual(checks(p), ['coverage']);
});

test('fixtures: a passing and a failing one, or for a deferred measure a deferred one', () => {
  let p = copy();
  p.rules[0]!.fixtures = p.rules[0]!.fixtures.filter((f) => f.expect.outcome !== 'fail');
  assert.deepEqual(checks(p), ['fixtures']);
  p = copy();
  p.rules.find((r) => r.id === 'STAIR-RISER')!.fixtures[0]!.expect.outcome = 'pass';
  assert.deepEqual(checks(p), ['fixtures', 'fixtures']);
  p = copy();
  p.rules[0]!.fixtures[0]!.expect.extensions = ['FS_unknown'];
  assert.deepEqual(checks(p), ['fixtures']);
});

test('no-automation: a script that names a viewer host fails, wherever it is', () => {
  const root = mkdtempSync(join(tmpdir(), 'floorspec-lint-'));
  try {
    mkdirSync(join(root, 'tools'));
    mkdirSync(join(root, 'rules'));
    writeFileSync(join(root, 'tools', 'fetch.py'), "URL = 'https://viewer.invalid/x'\n");
    writeFileSync(join(root, 'rules', 'notes.md'), 'The viewer is at viewer.invalid.\n');
    const found = lintRepository(root, realCtx.viewers);
    assert.deepEqual(found.map((f) => [f.check, f.file]), [['no-automation', join('tools', 'fetch.py')]]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
  assert.deepEqual(lintRepository(), []);
});

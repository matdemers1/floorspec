import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildAll, checkFixture, fixtureCases, python } from './build-pack.ts';
import { buildPack, loadPack, RULES_DIR } from './packs.ts';

/** Building packs (FLR-T-6.3): fixture requests, and the comparison of the oracle's report with expect.json. */
const example = loadPack(join(RULES_DIR, 'example'));
const cases = fixtureCases(example, buildPack(example) as never);
const find = (rule: string, outcome: string) => cases.find((c) => c.rule.id === rule && c.fixture.expect.outcome === outcome)!;

const report = (over: Partial<Parameters<typeof checkFixture>[1]> = {}) => ({ diagnostics: [], evaluated: [], notEvaluated: [], findings: [], ...over });
const ev = (rule: string, subjects = 1, findings = 0) => ({ pack: 'example', rule, subjects, exempt: 0, findings });
const finding = (rule: string, id: string) => ({ pack: 'example', rule, subject: { id } });

test('each fixture is a request for the built pack under a profile adopting the rule\'s cited edition', () => {
  assert.equal(cases.length, 5);
  const c = find('SMOKE-ALARM', 'pass');
  const req = c.request as { packs: { name: string }[]; profile: { adopts: unknown[] } };
  assert.equal(req.packs[0]!.name, 'example');
  assert.deepEqual(req.profile.adopts, [{ code: 'TEST-ELEC', edition: '2026' }]);
  assert.deepEqual(c.registry.map((e) => (e as { name: string }).name), ['FS_electrical', 'FS_lowvoltage', 'FS_mechanical', 'FS_plumbing']);
});

test('pass: evaluated, with a subject, and no finding', () => {
  const c = find('ROOM-SIZE', 'pass');
  assert.deepEqual(checkFixture(c, report({ evaluated: [ev('ROOM-SIZE')] })), []);
  assert.equal(checkFixture(c, report({ evaluated: [ev('ROOM-SIZE', 1, 1)], findings: [finding('ROOM-SIZE', 'R1')] })).length, 1);
  assert.equal(checkFixture(c, report({ evaluated: [ev('ROOM-SIZE', 2)] })).length, 1, 'the fixture pins one subject');
  assert.equal(checkFixture(c, report({ notEvaluated: [{ pack: 'example', rule: 'ROOM-SIZE', reason: 'edition' }] })).length, 1);
  const d = find('SMOKE-ALARM', 'pass');
  assert.equal(checkFixture(d, report({ evaluated: [ev('SMOKE-ALARM', 0)] })).length, 1, 'a pass with no subject proves nothing');
});

test('fail: findings on exactly the subjects listed', () => {
  const c = find('ROOM-SIZE', 'fail');
  assert.deepEqual(checkFixture(c, report({ evaluated: [ev('ROOM-SIZE', 2, 1)], findings: [finding('ROOM-SIZE', 'R3')] })), []);
  assert.equal(checkFixture(c, report({ evaluated: [ev('ROOM-SIZE', 2, 2)], findings: [finding('ROOM-SIZE', 'R1'), finding('ROOM-SIZE', 'R3')] })).length, 1);
  assert.equal(checkFixture(c, report({ evaluated: [ev('ROOM-SIZE', 2, 0)] })).length, 1);
});

test('deferred: not evaluated, for a deferred measure', () => {
  const c = find('STAIR-RISER', 'deferred');
  assert.deepEqual(checkFixture(c, report({ notEvaluated: [{ pack: 'example', rule: 'STAIR-RISER', reason: 'deferred' }] })), []);
  assert.equal(checkFixture(c, report({ evaluated: [ev('STAIR-RISER')] })).length, 1);
});

test('a rejected pack or document stops the fixture', () => {
  const c = find('ROOM-SIZE', 'pass');
  assert.match(checkFixture(c, report({ diagnostics: [{ code: 'FS-RULES-006', packIndex: 0 }] }))[0]!, /FS-RULES-006/);
  assert.match(checkFixture(c, report({ diagnostics: [{ code: 'FS-RULES-003' }] }))[0]!, /FS-RULES-003/);
});

let py: string | undefined;
try {
  py = python();
  if (spawnSync(py, ['-c', 'import sys; assert sys.version_info >= (3, 13)']).status !== 0) py = undefined;
} catch {
  py = undefined;
}

test('end to end with the oracle: the example pack builds, and a wrong expectation fails the build', { skip: py ? false : 'no Python 3.13 (set FLOORSPEC_PYTHON)' }, () => {
  assert.deepEqual(buildAll().problems, []);
  const root = mkdtempSync(join(tmpdir(), 'floorspec-packs-'));
  try {
    cpSync(join(RULES_DIR, 'example'), join(root, 'example'), { recursive: true });
    const f = join(root, 'example', 'rules', 'ROOM-SIZE', 'fixtures', 'small-second-bedroom', 'expect.json');
    const e = JSON.parse(readFileSync(f, 'utf8')) as { findings: string[] };
    e.findings = ['R1'];
    writeFileSync(f, JSON.stringify(e));
    const problems = buildAll({ root }).problems;
    assert.equal(problems.length, 1, problems.join('\n'));
    assert.match(problems[0]!, /expected findings of ROOM-SIZE on R1, the oracle found R3/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

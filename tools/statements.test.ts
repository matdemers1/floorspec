import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { extract } from './statements.ts';

function spec(markdown: string) {
  const root = mkdtempSync(join(tmpdir(), 'fs-'));
  mkdirSync(join(root, 'spec', 'core'), { recursive: true });
  writeFileSync(join(root, 'spec', 'core', '01-x.md'), markdown);
  return extract(root, 'core');
}

test('a tagged statement is extracted with its level and section', () => {
  const r = spec('# 1. Model\n\n## 1.2 Members\n\nReaders MUST apply defaults. {#FS-CORE-1.2.1 MUST}\n');
  assert.deepEqual(r.problems, []);
  assert.equal(r.statements[0]!.id, 'FS-CORE-1.2.1');
  assert.equal(r.statements[0]!.level, 'MUST');
  assert.equal(r.statements[0]!.text, 'Readers MUST apply defaults.');
});

test('an untagged MUST fails', () => {
  const r = spec('# 1. Model\n\n## 1.2 Members\n\nReaders MUST apply defaults.\n');
  assert.match(r.problems[0]!.message, /untagged/);
});

test('a tag in the wrong section fails', () => {
  const r = spec('# 1. Model\n\n## 1.2 Members\n\nReaders MUST apply defaults. {#FS-CORE-1.3.1 MUST}\n');
  assert.match(r.problems[0]!.message, /sits in section 1.2/);
});

test('a tag whose level is not in its text fails', () => {
  const r = spec('# 1. Model\n\n## 1.2 Members\n\nReaders SHOULD apply defaults. {#FS-CORE-1.2.1 MUST}\n');
  assert.ok(r.problems.some((p) => /tagged MUST/.test(p.message)));
});

test('a duplicated ID fails', () => {
  const r = spec('# 1. Model\n\n## 1.2 Members\n\nA MUST b. {#FS-CORE-1.2.1 MUST}\n\nC MUST d. {#FS-CORE-1.2.1 MUST}\n');
  assert.ok(r.problems.some((p) => /already used/.test(p.message)));
});

test('keywords in code spans, code fences and lowercase prose are not normative', () => {
  const r = spec('# 1. Model\n\n## 1.2 Members\n\nThe word `MUST` and must are fine.\n\n```\nMUST\n```\n');
  assert.deepEqual(r.problems, []);
});

test('an informative callout may not use a keyword', () => {
  const r = spec('# 1. Model\n\n## 1.2 Members\n\n> [!note]\n> Writers MUST do this.\n');
  assert.match(r.problems[0]!.message, /callout/);
});

test('SHALL is not a Floorspec keyword', () => {
  const r = spec('# 1. Model\n\n## 1.2 Members\n\nReaders SHALL apply defaults. {#FS-CORE-1.2.1 MUST}\n');
  assert.ok(r.problems.some((p) => /not a Floorspec keyword/.test(p.message)));
});

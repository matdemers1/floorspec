import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  checkEntries,
  checkTransitions,
  compareVersions,
  MAINTAINER_LABEL,
  STATUS_NAME,
  type Entry,
  type Git,
  type Status,
} from './registry-gates.ts';

/** The registry's lifecycle gates (FLR-T-10.3, registry/README.md), on throwaway registries. */

const SHA = 'a'.repeat(40);
const RATIFYING = 'b'.repeat(40);

function entry(status: Status, over: Partial<Entry> = {}): Entry {
  return {
    name: 'EXT_demo',
    version: '0.1.0',
    status,
    schema: 'https://example.com/schema/ext/EXT_demo/0.1.0/demo.schema.json',
    requires: {},
    kinds: {},
    terms: { roomFunctions: [] },
    implementations: [],
    ...over,
  };
}

const impl = (n: number) => ({ name: `Impl ${n}`, url: `https://example.com/impl${n}` });

function evidence(n: number, over: Record<string, unknown> = {}) {
  return {
    implementation: { ...impl(n), version: '1.0.0' },
    maintainer: `Maintainer ${n}`,
    sharesCodeWith: [],
    extension: 'EXT_demo',
    extensionVersion: '0.1.0',
    suite: { commit: SHA, tests: 1 },
    result: { passed: 1, failed: 0 },
    ran: '2026-10-05',
    ...over,
  };
}

interface Build {
  entry: Entry;
  spec?: boolean;
  schema?: boolean;
  suite?: boolean;
  proposal?: boolean;
  evidence?: Record<string, unknown>[];
  exceptions?: unknown;
  readme?: string;
}

function registry(b: Build): string {
  const root = mkdtempSync(join(tmpdir(), 'fs-registry-'));
  const dir = join(root, 'registry', 'EXT_demo');
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, 'extension.json'), JSON.stringify(b.entry));
  if (b.proposal) writeFileSync(join(dir, 'proposal.md'), '# EXT_demo\n\nWhy.\n');
  if (b.spec !== false && b.entry.status !== 'proposal')
    writeFileSync(join(dir, 'spec.md'), [
      `# EXT_demo ${b.entry.version}`, '', '# 1. Conventions', '', '## 1.1 Status', '', '| | |', '|---|---|',
      `| Version | \`${b.entry.version}\` |`, `| Status | ${STATUS_NAME[b.entry.status]} |`, '', '## 1.2 Conformance', '',
      'A validator MUST evaluate it. {#FS-XDEMO-1.2.1 MUST}', '',
    ].join('\n'));
  if (b.schema !== false && b.entry.status !== 'proposal')
    writeFileSync(join(dir, 'demo.schema.json'), JSON.stringify({ $id: b.entry.schema, type: 'object' }));
  if (b.suite !== false && b.entry.status !== 'proposal') {
    const t = join(root, 'conformance', 'ext', 'EXT_demo', b.entry.version, 'examples', '001-a');
    mkdirSync(t, { recursive: true });
    writeFileSync(join(t, 'test.json'), JSON.stringify({ description: 'a', covers: ['FS-XDEMO-1.2.1'] }));
  }
  if (b.evidence?.length) {
    mkdirSync(join(dir, 'evidence'));
    b.evidence.forEach((e, i) => writeFileSync(join(dir, 'evidence', `${i}.json`), JSON.stringify(e)));
  }
  if (b.exceptions) writeFileSync(join(root, 'registry', 'exceptions.json'), JSON.stringify(b.exceptions));
  writeFileSync(join(root, 'registry', 'README.md'), b.readme ??
    `| Extension | Version | Status |\n|---|---|---|\n| [\`EXT_demo\`](EXT_demo/spec.md) | ${b.entry.version} | ${STATUS_NAME[b.entry.status]} |\n`);
  return root;
}

function git(over: Partial<Git> = {}): Git {
  return {
    testsAt: () => 1,
    changedSince: () => false,
    show: () => null,
    log: () => [],
    namesAt: () => [],
    ...over,
  };
}

const errors = (b: Build, g = git()) => checkEntries(registry(b), g).errors;

test('versions compare by Semantic Versioning precedence', () => {
  assert.equal(compareVersions('0.1.0', '0.1.0'), 0);
  assert.equal(compareVersions('0.2.0', '0.10.0'), -1);
  assert.equal(compareVersions('1.0.0-rc.1', '1.0.0'), -1);
  assert.equal(compareVersions('1.0.0-rc.2', '1.0.0-rc.10'), -1);
  assert.equal(compareVersions('1.0.0-alpha', '1.0.0-1'), 1);
});

test('a Proposal is an entry and a written rationale', () => {
  assert.deepEqual(errors({ entry: entry('proposal'), proposal: true }), []);
  assert.match(errors({ entry: entry('proposal') }).join('\n'), /proposal\.md/);
});

test('a Draft has a specification whose 1.1 table agrees, a schema at a versioned URL, and a suite covering every MUST', () => {
  assert.deepEqual(errors({ entry: entry('draft') }), []);
  assert.match(errors({ entry: entry('draft'), spec: false }).join('\n'), /has spec\.md/);
  assert.match(errors({ entry: entry('draft'), schema: false }).join('\n'), /no schema file/);
  assert.match(errors({ entry: entry('draft'), suite: false }).join('\n'), /conformance suite/);
  const unversioned = entry('draft', { schema: 'https://example.com/schema/demo.schema.json' });
  assert.match(errors({ entry: unversioned }).join('\n'), /not versioned/);
  const root = registry({ entry: entry('draft') });
  writeFileSync(join(root, 'registry', 'EXT_demo', 'spec.md'), '# x\n\n## 1.1 Status\n\n| Version | `0.1.0` |\n| Status | Release Candidate |\n\n## 1.2 C\n\nIt MUST. {#FS-XDEMO-1.2.1 MUST}\n');
  assert.match(checkEntries(root, git()).errors.join('\n'), /1\.1 table gives version 0\.1\.0 and status Release Candidate/);
});

test('every extension has a row in registry/README.md that agrees with its entry', () => {
  assert.match(errors({ entry: entry('draft'), readme: '' }).join('\n'), /lists every extension/);
  assert.match(errors({ entry: entry('draft'), readme: '| [`EXT_demo`](x) | 0.1.0 | Ratified |\n' }).join('\n'), /lists it as Ratified/);
});

test('a Release Candidate lists an implementation with evidence of a passing run of the suite', () => {
  const rc = entry('releaseCandidate', { implementations: [impl(1)] });
  assert.deepEqual(errors({ entry: rc, evidence: [evidence(1)] }), []);
  assert.match(errors({ entry: rc }).join('\n'), /listed with no evidence/);
  assert.match(errors({ entry: entry('releaseCandidate') }).join('\n'), /at least one implementation/);
  assert.match(errors({ entry: rc, evidence: [evidence(1, { result: { passed: 0, failed: 1 } })] }).join('\n'), /passing run/);
  assert.match(errors({ entry: rc, evidence: [evidence(1)] }, git({ testsAt: () => 7 })).join('\n'), /held 7 tests/);
  assert.match(errors({ entry: rc, evidence: [evidence(1), evidence(2)] }).join('\n'), /does not list/);
  assert.match(errors({ entry: rc, evidence: [{ ...evidence(1), colour: 'red' }] }).join('\n'), /is not evidence/);
  const stale = checkEntries(registry({ entry: rc, evidence: [evidence(1)] }), git({ changedSince: () => true }));
  assert.deepEqual(stale.errors, []);
  assert.match(stale.warnings.join('\n'), /suite has changed/);
});

test('an owner\'s recorded exception waives the Release Candidate implementation rule for one version, until it passes', () => {
  const exceptions = (version = '0.1.0') => ({
    exceptions: [{ extension: 'EXT_demo', version, waives: 'releaseCandidate.implementation', decision: 'Owner.', until: 'Listed.' }],
  });
  assert.deepEqual(errors({ entry: entry('releaseCandidate'), exceptions: exceptions() }), []);
  assert.match(errors({ entry: entry('releaseCandidate'), exceptions: exceptions('0.2.0') }).join('\n'), /not in the registry/);
  assert.match(errors({ entry: entry('draft'), exceptions: exceptions() }).join('\n'), /remove it/);
  const rc = entry('releaseCandidate', { implementations: [impl(1)] });
  assert.match(errors({ entry: rc, evidence: [evidence(1)], exceptions: exceptions() }).join('\n'), /remove its exception/);
  const ratified = { exceptions: [{ extension: 'EXT_demo', version: '0.1.0', waives: 'ratified.independence', decision: 'x', until: 'y' }] };
  assert.match(errors({ entry: entry('releaseCandidate'), exceptions: ratified }).join('\n'), /exceptions\.json/);
});

test('Ratified needs two implementations with current evidence, independent of each other, and freezes at the ratifying commit', () => {
  const ratified = entry('ratified', { implementations: [impl(1), impl(2)] });
  const history = git({
    log: () => [RATIFYING, SHA],
    show: (c) => (c === RATIFYING ? JSON.stringify({ ...ratified, implementations: [impl(1), impl(2)] }) : JSON.stringify(entry('releaseCandidate'))),
  });
  assert.deepEqual(errors({ entry: ratified, evidence: [evidence(1), evidence(2)] }, history), []);
  assert.match(errors({ entry: ratified, evidence: [evidence(1), evidence(2, { maintainer: 'Maintainer 1' })] }, history).join('\n'), /different maintainers/);
  assert.match(errors({ entry: ratified, evidence: [evidence(1), evidence(2, { sharesCodeWith: ['Impl 1'] })] }, history).join('\n'), /sharing no code/);
  assert.match(errors({ entry: ratified, evidence: [evidence(1), evidence(2)] }, { ...history, changedSince: () => true }).join('\n'), /has changed|frozen/);
  const retitled = { ...ratified, title: 'Renamed' };
  assert.match(errors({ entry: retitled, evidence: [evidence(1), evidence(2)] }, history).join('\n'), /other than implementations/);
  // more implementations may be listed after ratification
  const three = { ...ratified, implementations: [impl(1), impl(2), impl(3)] };
  assert.deepEqual(errors({ entry: three, evidence: [evidence(1), evidence(2), evidence(3)] }, history), []);
});

test('a pull request moves a version forward one status at a time, and a new extension or version enters as a Proposal or a Draft', () => {
  const m = (...es: Entry[]) => new Map(es.map((e) => [e.name, e]));
  const t = (a: Entry[], b: Entry[], labels: string[] = []) => checkTransitions(m(...a), m(...b), labels).errors;
  assert.deepEqual(t([entry('draft')], [entry('releaseCandidate')]), []);
  assert.deepEqual(t([entry('releaseCandidate')], [entry('ratified')]), []);
  assert.deepEqual(t([], [entry('proposal')]), []);
  assert.deepEqual(t([entry('ratified')], [entry('draft', { version: '0.2.0' })]), []);
  assert.match(t([entry('draft')], [entry('ratified')]).join('\n'), /more than one step/);
  assert.match(t([entry('releaseCandidate')], [entry('draft')]).join('\n'), /goes back/);
  assert.match(t([], [entry('releaseCandidate')]).join('\n'), /enters as a Proposal or a Draft/);
  assert.match(t([entry('ratified')], [entry('releaseCandidate', { version: '0.2.0' })]).join('\n'), /new version/);
  assert.match(t([entry('draft', { version: '0.2.0' })], [entry('draft')]).join('\n'), /goes back from 0\.2\.0/);
  assert.match(t([entry('draft')], []).join('\n'), /removed/);
  assert.deepEqual(t([entry('draft')], [entry('ratified')], [MAINTAINER_LABEL]), []);
  assert.deepEqual(t([entry('draft')], [], [MAINTAINER_LABEL]), []);
});

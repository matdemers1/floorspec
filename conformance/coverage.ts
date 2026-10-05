/**
 * The MUST-coverage gate (FLR-ADR-009, FLR-REQ-032, FLR-REQ-159): every mandatory statement of Core,
 * Ops and every extension specification in registry/ (gated against conformance/ext/<NAME>/<version>/)
 * (MUST / MUST NOT) has at least one conformance test whose test.json `covers` names it, and every
 * ID a test names exists. Fails the build otherwise. Writes build/coverage.json and
 * build/coverage.md, which the spec site publishes.
 *
 * The spec text in spec/core/ is one draft (CURRENT_CORE, 0.2), the text in spec/ops/ one draft
 * (CURRENT_OPS, 0.2) and the text in spec/rules/ one draft (CURRENT_RULES, 0.1), so each is gated
 * against that draft's suite alone: conformance/core/0.2/, conformance/ops/0.2/ and
 * conformance/rules/0.1/. Earlier drafts' suites stay as they were
 * published, gated by the text of their own pinned commit; here they are only checked to name
 * statement IDs that exist now or that a later draft retired (spec/core/00-conventions.md, 0.6;
 * spec/ops/00-conventions.md, 0.4), so that a retired ID is never reused for something else.
 */
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { CORE_VERSIONS, CURRENT_CORE, CURRENT_OPS, CURRENT_RULES, OPS_VERSIONS, RULES_VERSIONS } from '../tools/schema.ts';
import { extensionSpecs, extract, extractExtension, MANDATORY, retired, type Statement } from '../tools/statements.ts';

const root = join(import.meta.dirname, '..');

interface TestCase {
  path: string;
  covers: string[];
}

function tests(dir: string): TestCase[] {
  if (!existsSync(dir)) return [];
  const found: TestCase[] = [];
  for (const entry of readdirSync(dir).sort()) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) found.push(...tests(p));
    else if (entry === 'test.json') {
      const t = JSON.parse(readFileSync(p, 'utf8')) as { covers?: unknown };
      if (!Array.isArray(t.covers) || t.covers.some((c) => typeof c !== 'string'))
        throw new Error(`${relative(root, p)}: "covers" must be an array of statement IDs`);
      found.push({ path: relative(root, dir), covers: t.covers as string[] });
    }
  }
  return found;
}

let failed = false;
const report: Record<string, unknown> = {};
const lines: string[] = ['# Conformance coverage', ''];

for (const spec of ['core', 'ops', 'rules'] as const) {
  const hasChapters = readdirSync(join(root, 'spec', spec)).some((f) => f.endsWith('.md') && f !== 'README.md');
  if (!hasChapters) continue;
  const { statements, problems } = extract(root, spec);
  if (problems.length) {
    for (const p of problems) console.error(`${p.file}:${p.line}: ${p.message}`);
    failed = true;
  }
  const byId = new Map<string, Statement>(statements.map((s) => [s.id, s]));
  const drafts: Record<string, { current: string; versions: readonly string[]; section: string }> = {
    core: { current: CURRENT_CORE, versions: CORE_VERSIONS, section: '0.6' },
    ops: { current: CURRENT_OPS, versions: OPS_VERSIONS, section: '0.4' },
    rules: { current: CURRENT_RULES, versions: RULES_VERSIONS, section: '0.8' },
  };
  const draft = drafts[spec];
  const suiteDir = draft ? join(root, 'conformance', spec, draft.current) : join(root, 'conformance', spec);
  const cases = tests(suiteDir);
  if (draft) {
    const name = { core: 'Core', ops: 'Ops', rules: 'Rules' }[spec];
    const gone = retired(root, spec);
    for (const id of gone)
      if (byId.has(id)) {
        console.error(`spec/${spec}: ${id} is retired (00-conventions.md, ${draft.section}) and must not be used again`);
        failed = true;
      }
    for (const v of draft.versions.filter((x) => x !== draft.current))
      for (const t of tests(join(root, 'conformance', spec, v)))
        for (const id of t.covers)
          if (!byId.has(id) && !gone.has(id)) {
            console.error(`${t.path}: covers ${id}, which is neither a statement of ${name} ${draft.current} nor retired`);
            failed = true;
          }
  }
  const coveredBy = new Map<string, string[]>();
  for (const t of cases)
    for (const id of t.covers) {
      if (!byId.has(id)) {
        console.error(`${t.path}: covers ${id}, which no FS-${spec.toUpperCase()} statement has`);
        failed = true;
        continue;
      }
      coveredBy.set(id, [...(coveredBy.get(id) ?? []), t.path]);
    }
  const mandatory = statements.filter((s) => MANDATORY.includes(s.level));
  const uncovered = mandatory.filter((s) => !coveredBy.has(s.id));
  for (const s of uncovered) console.error(`${s.file}:${s.line}: ${s.id} (${s.level}) has no conformance test`);
  failed ||= uncovered.length > 0;

  const pct = mandatory.length ? Math.floor((100 * (mandatory.length - uncovered.length)) / mandatory.length) : 100;
  console.log(`FS-${spec.toUpperCase()}${draft ? ` ${draft.current}` : ''}: ${mandatory.length - uncovered.length}/${mandatory.length} mandatory statements covered (${pct}%) by ${cases.length} tests`);
  report[spec] = {
    tests: cases.length,
    statements: statements.map((s) => ({ id: s.id, level: s.level, section: s.section, tests: coveredBy.get(s.id) ?? [] })),
    mandatory: mandatory.length,
    covered: mandatory.length - uncovered.length,
  };
  lines.push(`## Floorspec ${spec[0]!.toUpperCase()}${spec.slice(1)}`, '', `${mandatory.length - uncovered.length} of ${mandatory.length} mandatory statements covered by ${cases.length} tests.`, '', '| Statement | Level | Tests |', '|---|---|---|');
  for (const s of statements) lines.push(`| ${s.id} | ${s.level} | ${(coveredBy.get(s.id) ?? []).length} |`);
  lines.push('');
}

// Each extension's specification (registry/<NAME>/spec.md) is gated against its own suite,
// conformance/ext/<NAME>/<version>/, in its own ID space.
const exts = extensionSpecs(root);
const coreAndOps = new Set([...extract(root, 'core').statements, ...extract(root, 'ops').statements].map((s) => s.id));
for (const p of exts.problems) console.error(`${p.file}:${p.line}: ${p.message}`);
failed ||= exts.problems.length > 0;
for (const ext of exts.specs) {
  const { statements, problems } = extractExtension(root, ext);
  for (const p of problems) console.error(`${p.file}:${p.line}: ${p.message}`);
  failed ||= problems.length > 0;
  const byId = new Set(statements.map((s) => s.id));
  const cases = tests(ext.suite);
  const coveredBy = new Map<string, string[]>();
  for (const t of cases)
    for (const id of t.covers) {
      // An extension's test may also cover Core or Ops statements; it must name only real ones.
      if (!byId.has(id) && !coreAndOps.has(id)) {
        console.error(`${t.path}: covers ${id}, which is no statement of FS-${ext.code}, Core or Ops`);
        failed = true;
        continue;
      }
      coveredBy.set(id, [...(coveredBy.get(id) ?? []), t.path]);
    }
  const mandatory = statements.filter((s) => MANDATORY.includes(s.level));
  const uncovered = mandatory.filter((s) => !coveredBy.has(s.id));
  for (const s of uncovered) console.error(`${s.file}:${s.line}: ${s.id} (${s.level}) has no conformance test`);
  failed ||= uncovered.length > 0 || cases.length === 0;
  if (cases.length === 0) console.error(`${ext.name}: no conformance tests in ${relative(root, ext.suite)}`);
  const pct = mandatory.length ? Math.floor((100 * (mandatory.length - uncovered.length)) / mandatory.length) : 100;
  console.log(`FS-${ext.code} (${ext.name} ${ext.version}): ${mandatory.length - uncovered.length}/${mandatory.length} mandatory statements covered (${pct}%) by ${cases.length} tests`);
  report[ext.name] = {
    version: ext.version,
    tests: cases.length,
    statements: statements.map((s) => ({ id: s.id, level: s.level, section: s.section, tests: coveredBy.get(s.id) ?? [] })),
    mandatory: mandatory.length,
    covered: mandatory.length - uncovered.length,
  };
  lines.push(`## ${ext.name} ${ext.version}`, '', `${mandatory.length - uncovered.length} of ${mandatory.length} mandatory statements covered by ${cases.length} tests.`, '', '| Statement | Level | Tests |', '|---|---|---|');
  for (const s of statements) lines.push(`| ${s.id} | ${s.level} | ${(coveredBy.get(s.id) ?? []).length} |`);
  lines.push('');
}

if (!existsSync(join(root, 'build'))) mkdirSync(join(root, 'build'));
writeFileSync(join(root, 'build', 'coverage.json'), JSON.stringify(report, null, 2) + '\n');
writeFileSync(join(root, 'build', 'coverage.md'), lines.join('\n'));
if (failed) {
  console.error('coverage gate failed');
  process.exit(1);
}

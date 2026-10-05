/**
 * The MUST-coverage gate (FLR-ADR-009, FLR-REQ-032, FLR-REQ-159): every mandatory statement
 * (MUST / MUST NOT) has at least one conformance test whose test.json `covers` names it, and every
 * ID a test names exists. Fails the build otherwise. Writes build/coverage.json and
 * build/coverage.md, which the spec site publishes.
 *
 * The spec text in spec/core/ is one draft (CURRENT_CORE, 0.2), so it is gated against that
 * draft's suite alone, conformance/core/0.2/. Earlier drafts' suites stay as they were published,
 * gated by the text of their own pinned commit; here they are only checked to name statement IDs
 * that exist now or that a later draft retired (00-conventions.md, 0.6), so that a retired ID is
 * never reused for something else.
 */
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { CORE_VERSIONS, CURRENT_CORE } from '../tools/schema.ts';
import { extract, MANDATORY, retired, type Statement } from '../tools/statements.ts';

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
  const suiteDir = spec === 'core' ? join(root, 'conformance', 'core', CURRENT_CORE) : join(root, 'conformance', spec);
  const cases = tests(suiteDir);
  if (spec === 'core') {
    const gone = retired(root);
    for (const id of gone)
      if (byId.has(id)) {
        console.error(`spec/core: ${id} is retired (00-conventions.md, 0.6) and must not be used again`);
        failed = true;
      }
    for (const v of CORE_VERSIONS.filter((x) => x !== CURRENT_CORE))
      for (const t of tests(join(root, 'conformance', 'core', v)))
        for (const id of t.covers)
          if (!byId.has(id) && !gone.has(id)) {
            console.error(`${t.path}: covers ${id}, which is neither a statement of Core ${CURRENT_CORE} nor retired`);
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
  console.log(`FS-${spec.toUpperCase()}${spec === 'core' ? ` ${CURRENT_CORE}` : ''}: ${mandatory.length - uncovered.length}/${mandatory.length} mandatory statements covered (${pct}%) by ${cases.length} tests`);
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

if (!existsSync(join(root, 'build'))) mkdirSync(join(root, 'build'));
writeFileSync(join(root, 'build', 'coverage.json'), JSON.stringify(report, null, 2) + '\n');
writeFileSync(join(root, 'build', 'coverage.md'), lines.join('\n'));
if (failed) {
  console.error('coverage gate failed');
  process.exit(1);
}

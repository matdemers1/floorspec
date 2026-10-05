/**
 * Builds the rule packs under rules/ (FLR-T-6.3, rules/README.md): for each pack directory,
 *
 *   1. reads its manifest, rules and fixtures, each against its schema (pack-manifest, pack-rule,
 *      pack-fixture in schema/rules/0.1/);
 *   2. lints them (tools/lint-rules.ts) - and the repository for scripts naming a code viewer;
 *   3. assembles the pack object an evaluator reads and checks it against the evaluator's pack
 *      schema (spec/rules 2.1) - rules/<pack>/generated/pack.json, canonical JSON;
 *   4. evaluates every fixture with the oracle (tools/pack_fixtures.py over tools/oracle/rules) under
 *      a profile adopting the rule's cited edition, and compares the outcome with expect.json;
 *   5. generates the coverage matrices (tools/coverage-matrix.ts).
 *
 *   pnpm packs                      build and write rules/<pack>/generated/ and rules/coverage.{json,md}
 *   pnpm packs:check                the same, writing nothing: fails if a generated file differs
 *   ... --skip-fixtures             without step 4 (no Python)
 *
 * The oracle runs under $FLOORSPEC_PYTHON, else python3.13, else python3. Nothing here reads a
 * viewer link, let alone fetches one.
 */
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { matrixOutputs, writeOrCheck, type MatrixOutput } from './coverage-matrix.ts';
import { failing, formatFinding, lintContext, lintPack, lintRepository } from './lint-rules.ts';
import { buildPack, canonicalJson, formatValidators, loadPack, officialRegistry, packDirs, REPO, RULES_DIR, type Fixture, type PackSource, type RuleSource } from './packs.ts';
import { formatErrors, type Json } from './schema.ts';

export interface FixtureCase {
  pack: string;
  rule: RuleSource;
  fixture: Fixture;
  request: Json;
  registry: Json[];
}

interface Report {
  diagnostics: { code: string; pack?: string; rule?: string; packIndex?: number }[];
  evaluated: { pack: string; rule: string; subjects: number; exempt: number; findings: number }[];
  notEvaluated: { pack: string; rule: string; reason: string }[];
  findings: { pack: string; rule: string; subject: { id: string } }[];
}

/** One evaluation request per fixture: the built pack, under a profile adopting the rule's cited edition. */
export function fixtureCases(src: PackSource, built: Json, registry = officialRegistry()): FixtureCase[] {
  const cases: FixtureCase[] = [];
  for (const r of src.rules)
    for (const f of r.fixtures) {
      const known = f.expect.extensions ?? [...registry.keys()];
      cases.push({
        pack: src.manifest.name,
        rule: r,
        fixture: f,
        registry: known.filter((x) => registry.has(x)).map((x) => registry.get(x)!),
        request: {
          floorspecRules: '0.1',
          packs: [built],
          profile: {
            floorspecRules: '0.1',
            name: `Fixture profile: ${r.rule.citation.code} ${r.rule.citation.edition}`,
            adopts: [{ code: r.rule.citation.code, edition: r.rule.citation.edition }],
          },
        },
      });
    }
  return cases;
}

export function python(): string {
  if (process.env.FLOORSPEC_PYTHON) return process.env.FLOORSPEC_PYTHON;
  for (const p of ['python3.13', 'python3']) if (spawnSync(p, ['--version']).status === 0) return p;
  throw new Error('no Python found: set FLOORSPEC_PYTHON to a Python 3.13');
}

/** The oracle's reports for a batch of cases, in order. */
export function evaluateCases(cases: FixtureCase[], py = python()): Report[] {
  if (!cases.length) return [];
  const input = JSON.stringify({ cases: cases.map((c) => ({ document: c.fixture.documentText, registry: c.registry, request: c.request })) });
  const run = spawnSync(py, ['-m', 'tools.pack_fixtures'], { cwd: REPO, input, encoding: 'utf8', maxBuffer: 1 << 30 });
  if (run.status !== 0) throw new Error(`the oracle failed (${py} -m tools.pack_fixtures):\n${run.stderr}`);
  return (JSON.parse(run.stdout) as { reports: string[] }).reports.map((r) => JSON.parse(r) as Report);
}

/** What is wrong with one fixture's report, against its expect.json. */
export function checkFixture(c: FixtureCase, report: Report): string[] {
  const at = `${c.fixture.file}`;
  const e = c.fixture.expect;
  const id = c.rule.id;
  const problems: string[] = [];
  const blocking = report.diagnostics.filter((d) => ['FS-RULES-001', 'FS-RULES-002', 'FS-RULES-003', 'FS-RULES-004', 'FS-RULES-005', 'FS-RULES-006'].includes(d.code));
  if (blocking.length) return [`${at}: the evaluation stopped short: ${blocking.map((d) => d.code).join(', ')} (FS-RULES-003 is an invalid document; 004-006 a pack the evaluator rejects)`];
  const ev = report.evaluated.find((x) => x.pack === c.pack && x.rule === id);
  const ne = report.notEvaluated.find((x) => x.pack === c.pack && x.rule === id);
  if (e.outcome === 'deferred') {
    if (ne?.reason !== 'deferred') problems.push(`${at}: expected ${id} not to be evaluated for a deferred measure, but it was ${ev ? 'evaluated' : `not evaluated (${ne?.reason ?? 'absent'})`}`);
    return problems;
  }
  if (!ev) return [`${at}: expected ${id} to be evaluated, but it was not (${ne?.reason ?? 'absent'}; diagnostics ${report.diagnostics.map((d) => d.code).join(', ') || 'none'})`];
  const subjects = report.findings.filter((f) => f.pack === c.pack && f.rule === id).map((f) => f.subject.id).sort();
  if (e.subjects !== undefined && ev.subjects !== e.subjects) problems.push(`${at}: expected ${e.subjects} subjects, the oracle found ${ev.subjects}`);
  if (e.exempt !== undefined && ev.exempt !== e.exempt) problems.push(`${at}: expected ${e.exempt} exempt subjects, the oracle found ${ev.exempt}`);
  if (e.outcome === 'pass') {
    if (e.subjects === undefined && ev.subjects === 0) problems.push(`${at}: a passing fixture with no subject proves nothing; give the rule a subject, or pin "subjects": 0`);
    if (subjects.length) problems.push(`${at}: expected no finding of ${id}, the oracle found ${subjects.join(', ')}`);
  } else {
    const want = [...(e.findings ?? [])].sort();
    if (JSON.stringify(want) !== JSON.stringify(subjects)) problems.push(`${at}: expected findings of ${id} on ${want.join(', ')}, the oracle found ${subjects.join(', ') || 'none'}`);
  }
  return problems;
}

export interface BuildResult {
  problems: string[];
  outputs: MatrixOutput[];
  fixtures: number;
  rules: number;
  overridden: number;
}

/** Builds every pack under root (rules/ by default); writes nothing. */
export function buildAll(opts: { root?: string; fixtures?: boolean } = {}): BuildResult {
  const root = opts.root ?? RULES_DIR;
  const v = formatValidators();
  const ctx = lintContext();
  const problems: string[] = [];
  const outputs: MatrixOutput[] = [];
  const built: { dir: string; built: Json; synthetic: boolean }[] = [];
  const cases: FixtureCase[] = [];
  let rules = 0;
  let overridden = 0;
  const registry = officialRegistry();
  for (const dir of packDirs(root)) {
    const src = loadPack(dir);
    problems.push(...src.problems);
    if (!src.manifest || src.problems.length) continue;
    const findings = lintPack(src, ctx);
    problems.push(...failing(findings).map(formatFinding));
    overridden += findings.length - failing(findings).length;
    const pack = buildPack(src) as Json;
    if (!v.pack(pack)) problems.push(`${src.file}: the built pack does not match the evaluator's pack schema (spec/rules 2.1):\n    ${formatErrors(v.pack.errors ?? []).join('\n    ')}`);
    rules += src.rules.length;
    built.push({ dir, built: pack, synthetic: src.manifest.synthetic === true });
    outputs.push({ path: join(dir, 'generated', 'pack.json'), text: canonicalJson(pack) });
    cases.push(...fixtureCases(src, pack, registry));
  }
  problems.push(...lintRepository().map(formatFinding));
  if (opts.fixtures !== false && cases.length) {
    const reports = evaluateCases(cases);
    cases.forEach((c, i) => problems.push(...checkFixture(c, reports[i]!)));
  }
  outputs.push(...matrixOutputs(built, undefined, root));
  // Everything this tool writes is pack text too: none of it may read as assurance.
  for (const o of outputs) {
    const hit = ctx.assurance.exec(o.text);
    if (hit) problems.push(`${o.path}: "${hit[0]}" matches the assurance pattern`);
  }
  return { problems, outputs, fixtures: opts.fixtures === false ? 0 : cases.length, rules, overridden };
}

function main(argv: string[]): number {
  const check = argv.includes('--check');
  const result = buildAll({ fixtures: !argv.includes('--skip-fixtures') });
  for (const p of result.problems) console.error(p);
  if (result.problems.length) {
    console.error(`pack build failed: ${result.problems.length} problem${result.problems.length === 1 ? '' : 's'}`);
    return 1;
  }
  const differ = writeOrCheck(result.outputs, check);
  for (const d of differ) (check ? console.error : console.log)(`${check ? 'differs' : 'wrote'}: ${d}`);
  if (check && differ.length) {
    console.error('pack build check failed: a generated file differs; run pnpm packs');
    return 1;
  }
  console.log(
    `packs: ${result.rules} rules built, ${result.fixtures} fixtures evaluated by the oracle, ${result.overridden} lint findings overridden by a reviewer, ` +
      `${result.outputs.length} generated files ${check ? 'up to date' : 'written'}`,
  );
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) process.exit(main(process.argv.slice(2)));

/**
 * The rule-pack format (FLR-T-6.3, rules/README.md): a pack as it is kept on disk, and how it is
 * assembled into the one pack object an evaluator reads (spec/rules chapter 2, pack.schema.json).
 *
 *   rules/<name>/pack.json                                  the manifest (pack-manifest.schema.json)
 *   rules/<name>/rules/<rule ID>/rule.json                  one rule (pack-rule.schema.json)
 *   rules/<name>/rules/<rule ID>/fixtures/<slug>/expect.json    what the rule does on a document
 *                                                (pack-fixture.schema.json), with document.json beside
 *                                                it or a shared rules/<name>/documents/<doc>.json
 *   rules/<name>/generated/                                 written by `pnpm packs`, never by hand
 *
 * Assembly is a pure function of those files: the same files give the same bytes. The evaluator's
 * pack schema stays the single definition of what an evaluator reads; everything the format adds
 * (attribution, jurisdiction, editions, maintainers, domains, method, certification, the review
 * mark, lint overrides) travels in `extras.packFormat`, which an evaluator ignores (Core §1.7).
 *
 * Nothing here, or anywhere in this repository, fetches a viewer link (FLR-REQ-106).
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { basename, join, relative } from 'node:path';
import type { ValidateFunction } from 'ajv/dist/2020.js';
import { createAjv, formatErrors, hasDuplicateMember, loadSchemaFiles, rulesId, rulesSchemaDir, type Json } from './schema.ts';

export const REPO = join(import.meta.dirname, '..');
export const RULES_DIR = join(REPO, 'rules');
/** The version of the pack format: the certification a rule names is this format's. */
export const CERTIFICATION = 'original-paraphrase-v1';

type Obj = { [key: string]: Json };

export interface Manifest {
  floorspecRules: '0.1';
  name: string;
  version: string;
  title: string;
  description?: string;
  license: 'CC-BY-4.0';
  attribution: string;
  jurisdiction: string;
  editions: { code: string; edition: string; title?: string }[];
  maintainers: { name: string; url?: string }[];
  synthetic?: boolean;
  domains: { id: string; title: string }[];
  coverage: CoverageEntry[];
  extras?: Obj;
}

export interface CoverageEntry {
  code: string;
  edition: string;
  section: string;
  status: 'addressed' | 'partial' | 'notAddressed';
  note?: string;
  domain: string;
  needs?: string[];
}

export type Review = { status: 'unreviewed' } | { status: 'reviewed'; by: string; on: string; credential: string; scope?: string };

export interface LintOverride {
  check: string;
  reviewer: string;
  on: string;
  note: string;
}

export interface Test {
  measure?: string;
  args?: Obj;
  op?: string;
  value?: Json;
  all?: Test[];
  any?: Test[];
  not?: Test;
}

export interface RuleFile {
  title: string;
  citation: { code: string; edition: string; section: string; link: string };
  paraphrase: string;
  applies: { to: string; extension?: string; collection?: string; where?: Test };
  select?: { from: string; args?: Obj; where?: Test; need: string };
  requirement: Test;
  exceptions?: { when: Test; note: string }[];
  severity: 'mayNotMeet' | 'check' | 'note';
  provenance: {
    verifiedBy: string;
    verifiedOn: string;
    edition: string;
    method: 'freePublicViewer' | 'ownedCopy' | 'synthetic';
    certifiedBy: string;
    certification: string;
    review: Review;
    note?: string;
    lintOverrides?: LintOverride[];
  };
  extras?: Obj;
}

export interface FixtureExpect {
  description: string;
  outcome: 'pass' | 'fail' | 'deferred';
  findings?: string[];
  subjects?: number;
  exempt?: number;
  document?: string;
  extensions?: string[];
}

export interface Fixture {
  slug: string;
  /** expect.json, relative to the repository. */
  file: string;
  expect: FixtureExpect;
  /** The document's path relative to the repository, and its bytes as text. */
  documentFile: string;
  documentText: string;
}

export interface RuleSource {
  id: string;
  /** rule.json, relative to the repository. */
  file: string;
  rule: RuleFile;
  fixtures: Fixture[];
}

export interface PackSource {
  dir: string;
  /** pack.json, relative to the repository. */
  file: string;
  manifest: Manifest;
  rules: RuleSource[];
  /** Problems found while reading: unreadable files, bad JSON, schema mismatches, misnamed directories. */
  problems: string[];
}

/** The pack directories under rules/: each subdirectory holding a pack.json, by name. */
export function packDirs(root = RULES_DIR): string[] {
  if (!existsSync(root)) return [];
  return readdirSync(root)
    .filter((d) => statSync(join(root, d)).isDirectory() && existsSync(join(root, d, 'pack.json')))
    .sort()
    .map((d) => join(root, d));
}

export interface FormatValidators {
  manifest: ValidateFunction;
  rule: ValidateFunction;
  fixture: ValidateFunction;
  /** The evaluator's pack schema (spec/rules 2.1): what a built pack must match. */
  pack: ValidateFunction;
}

let cached: FormatValidators | undefined;
export function formatValidators(): FormatValidators {
  if (cached) return cached;
  const ajv = createAjv(loadSchemaFiles(rulesSchemaDir('0.1')));
  const get = (name: string) => {
    const f = ajv.getSchema(rulesId('0.1', name));
    if (!f) throw new Error(`schema ${name} is not loaded`);
    return f;
  };
  cached = { manifest: get('pack-manifest'), rule: get('pack-rule'), fixture: get('pack-fixture'), pack: get('pack') };
  return cached;
}

const ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;

function readJson(path: string, problems: string[], validate: ValidateFunction, label: string): unknown {
  const rel = relative(REPO, path);
  let text: string;
  try {
    text = readFileSync(path, 'utf8');
  } catch {
    problems.push(`${rel}: missing`);
    return undefined;
  }
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch (e) {
    problems.push(`${rel}: not JSON: ${(e as Error).message}`);
    return undefined;
  }
  if (hasDuplicateMember(text)) problems.push(`${rel}: an object has two members of one name`);
  if (!validate(value)) problems.push(`${rel}: does not match the ${label} schema:\n    ${formatErrors(validate.errors ?? []).join('\n    ')}`);
  return value;
}

const subdirs = (dir: string) =>
  existsSync(dir) ? readdirSync(dir).filter((d) => statSync(join(dir, d)).isDirectory()).sort() : [];

/** Reads one pack directory: its manifest, rules and fixtures, each checked against its schema. */
export function loadPack(dir: string): PackSource {
  const v = formatValidators();
  const problems: string[] = [];
  const file = join(dir, 'pack.json');
  const manifest = readJson(file, problems, v.manifest, 'pack manifest') as Manifest;
  if (manifest && manifest.name !== basename(dir))
    problems.push(`${relative(REPO, file)}: the pack is named "${manifest.name}", but its directory is "${basename(dir)}"`);
  const rules: RuleSource[] = [];
  const rulesDir = join(dir, 'rules');
  for (const id of subdirs(rulesDir)) {
    const ruleFile = join(rulesDir, id, 'rule.json');
    if (!ID.test(id)) problems.push(`${relative(REPO, join(rulesDir, id))}: "${id}" is not a rule ID (spec/rules 2.1)`);
    const rule = readJson(ruleFile, problems, v.rule, 'rule') as RuleFile;
    const fixtures: Fixture[] = [];
    const fixturesDir = join(rulesDir, id, 'fixtures');
    for (const slug of subdirs(fixturesDir)) {
      const fdir = join(fixturesDir, slug);
      const expect = readJson(join(fdir, 'expect.json'), problems, v.fixture, 'fixture') as FixtureExpect;
      if (!expect) continue;
      const docPath = expect.document ? join(dir, 'documents', `${expect.document}.json`) : join(fdir, 'document.json');
      if (expect.document && existsSync(join(fdir, 'document.json')))
        problems.push(`${relative(REPO, fdir)}: has both document.json and a shared document "${expect.document}"`);
      if (!existsSync(docPath)) {
        problems.push(`${relative(REPO, fdir)}: its document ${relative(REPO, docPath)} is missing`);
        continue;
      }
      fixtures.push({ slug, file: relative(REPO, join(fdir, 'expect.json')), expect, documentFile: relative(REPO, docPath), documentText: readFileSync(docPath, 'utf8') });
    }
    if (rule) rules.push({ id, file: relative(REPO, ruleFile), rule, fixtures });
  }
  return { dir, file: relative(REPO, file), manifest, rules, problems };
}

/** A rule's built record: the evaluator's rule record (spec/rules 3.1) with the format's additions in extras.packFormat. */
export function buildRule(r: RuleFile): Obj {
  const p = r.provenance;
  const provenance: Obj = { verifiedBy: p.verifiedBy, verifiedOn: p.verifiedOn, edition: p.edition };
  if (p.review.status === 'reviewed') {
    provenance.reviewed = { by: p.review.by, on: p.review.on, credential: p.review.credential };
  }
  if (p.note !== undefined) provenance.note = p.note;
  const packFormat: Obj = {
    method: p.method,
    certifiedBy: p.certifiedBy,
    certification: p.certification,
    review: p.review.status,
  };
  if (p.review.status === 'reviewed' && p.review.scope !== undefined) packFormat.reviewScope = p.review.scope;
  if (p.lintOverrides?.length) packFormat.lintOverrides = p.lintOverrides as unknown as Json;
  const out: Obj = {
    title: r.title,
    citation: r.citation,
    paraphrase: r.paraphrase,
    applies: r.applies as unknown as Json,
    requirement: r.requirement as unknown as Json,
    severity: r.severity,
    provenance,
    extras: { ...(r.extras ?? {}), packFormat },
  };
  if (r.select !== undefined) out.select = r.select as unknown as Json;
  if (r.exceptions?.length) out.exceptions = r.exceptions as unknown as Json;
  return out;
}

/** Assembles a pack's files into the pack object an evaluator reads (spec/rules 2.1). */
export function buildPack(src: PackSource): Obj {
  const m = src.manifest;
  const rules: Obj = {};
  for (const r of src.rules) rules[r.id] = buildRule(r.rule);
  const coverage = m.coverage.map((c) => {
    const e: Obj = { code: c.code, edition: c.edition, section: c.section, status: c.status };
    if (c.note !== undefined) e.note = c.note;
    return e;
  });
  const packFormat: Obj = {
    attribution: m.attribution,
    jurisdiction: m.jurisdiction,
    editions: m.editions,
    maintainers: m.maintainers,
    synthetic: m.synthetic === true,
    domains: m.domains,
    // Aligned with coverage by index: what the evaluator's coverage entry has no member for.
    coverage: m.coverage.map((c): Obj => (c.needs ? { domain: c.domain, needs: c.needs } : { domain: c.domain })),
  };
  const pack: Obj = {
    floorspecRules: m.floorspecRules,
    name: m.name,
    version: m.version,
    title: m.title,
    license: m.license,
    rules,
    coverage,
    extras: { ...(m.extras ?? {}), packFormat },
  };
  if (m.description !== undefined) pack.description = m.description;
  return pack;
}

/**
 * JSON.stringify(v, null, 2) with every object's members sorted by UTF-16 code units, and a final
 * line feed: the form Core 9.2 writes a value in, which the oracle's canon.pretty also writes.
 */
export function canonicalJson(v: unknown): string {
  const sort = (x: unknown): unknown => {
    if (Array.isArray(x)) return x.map(sort);
    if (x !== null && typeof x === 'object') {
      const o: Record<string, unknown> = {};
      for (const k of Object.keys(x).sort()) o[k] = sort((x as Record<string, unknown>)[k]);
      return o;
    }
    if (typeof x === 'number' && !Number.isInteger(x)) throw new Error(`a pack holds integers only, not ${x}`);
    return x;
  };
  return `${JSON.stringify(sort(v), null, 2)}\n`;
}

/** The deferred measures, read from the table of spec/rules 4.8 - so the list follows the spec. */
export function deferredMeasures(root = REPO): Set<string> {
  const md = readFileSync(join(root, 'spec', 'rules', '04-measures.md'), 'utf8');
  const start = md.indexOf('\n## 4.8');
  if (start < 0) throw new Error('spec/rules/04-measures.md has no section 4.8');
  const end = md.indexOf('\n## ', start + 1);
  const section = md.slice(start, end < 0 ? undefined : end);
  const names = new Set<string>();
  for (const line of section.split('\n')) {
    if (!line.startsWith('| `')) continue;
    const first = line.split('|')[1] ?? '';
    for (const m of first.matchAll(/`([a-z][A-Za-z0-9]*)`/g)) names.add(m[1]!);
  }
  if (!names.size) throw new Error('spec/rules 4.8 lists no deferred measure');
  return names;
}

/** Every measure a rule names, in applies.where, select.where, its requirement and its exceptions. */
export function ruleMeasures(rule: { applies: { where?: Test }; select?: { where?: Test }; requirement: Test; exceptions?: { when: Test }[] }): Set<string> {
  const out = new Set<string>();
  const walk = (t: Test | undefined) => {
    if (!t) return;
    if (typeof t.measure === 'string') out.add(t.measure);
    t.all?.forEach(walk);
    t.any?.forEach(walk);
    walk(t.not);
  };
  walk(rule.applies.where);
  walk(rule.select?.where);
  walk(rule.requirement);
  rule.exceptions?.forEach((e) => walk(e.when));
  return out;
}

/** Whether a rule's cited section falls within a coverage entry's: the same, or a subsection (R310 holds R310.2.1 and R310(a), not R3101). */
export function within(section: string, entry: string): boolean {
  if (section === entry) return true;
  if (!section.startsWith(entry)) return false;
  return /[^A-Za-z0-9]/.test(section[entry.length]!);
}

/** Natural order of section references: R310.2 before R310.10. */
export function compareSections(a: string, b: string): number {
  const parts = (s: string) => s.match(/\d+|\D+/g) ?? [];
  const pa = parts(a);
  const pb = parts(b);
  for (let i = 0; i < Math.min(pa.length, pb.length); i++) {
    const x = pa[i]!;
    const y = pb[i]!;
    if (x === y) continue;
    const nx = /^\d/.test(x);
    const ny = /^\d/.test(y);
    if (nx && ny) {
      const d = BigInt(x) - BigInt(y);
      if (d !== 0n) return d < 0n ? -1 : 1;
      return x.length - y.length;
    }
    return x < y ? -1 : 1;
  }
  if (pa.length !== pb.length) return pa.length - pb.length;
  return a < b ? -1 : a > b ? 1 : 0;
}

/** The official extensions' registry entries (registry/<NAME>/extension.json), by name. */
export function officialRegistry(root = REPO): Map<string, Json> {
  const out = new Map<string, Json>();
  const dir = join(root, 'registry');
  for (const name of subdirs(dir)) {
    const f = join(dir, name, 'extension.json');
    if (existsSync(f)) out.set(name, JSON.parse(readFileSync(f, 'utf8')) as Json);
  }
  return out;
}

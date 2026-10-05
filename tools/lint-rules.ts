/**
 * The rule-text lint of the rule-pack format (FLR-T-6.3, rules/CONTRIBUTING.md): what a pack's
 * files must satisfy beyond their schemas before `pnpm packs` builds them.
 *
 * Checks that never yield (an error stops the build):
 *   assurance            the assurance pattern of spec/rules 2.5 in any of the pack's text, read from the spec
 *   paraphrase-length    a paraphrase is 40-1200 characters and at least 8 words
 *   viewer-host          a citation's link is https on a publisher's free public viewer (rules/viewers.json),
 *                        for a code that viewer publishes; a synthetic pack links to example.org or example.com
 *   provenance           the verified edition is the cited one; method "synthetic" exactly in a synthetic pack
 *   edition-declared     every cited edition is in the manifest's editions, and every listed edition is cited
 *   synthetic-code       a synthetic pack cites TEST- codes only, and a real pack none
 *   coverage             coverage entries are distinct and in a declared domain; every rule falls within one;
 *                        addressed and partial entries have a rule, not-addressed ones none; needs names deferred measures
 *   fixtures             every rule has a passing and a failing fixture, or - using a deferred measure - a deferred one
 *   stale-override       an override for a heuristic that does not fire
 *   no-automation        no script in tools/, rules/ or .github/ names a viewer host: nothing automated goes near one
 *
 * Heuristics, which a rule may override with a reviewer's recorded note (provenance.lintOverrides):
 *   advice-wording       pass, passes, passed, satisfies, conforms, approved, guaranteed: words that grade a design
 *   verbatim-shall       "shall": code text's word; a paraphrase says what is asked in plain words
 *   verbatim-quote       a quoted span of six words or more
 *   verbatim-sections    three or more section numbers: pasted text is dense with cross-references
 *   verbatim-table       a pipe, a tab, a line starting with a number, or six or more numbers: thresholds belong
 *                        in the rule's values, never a table in prose
 *   verbatim-structure   an "Exception:" label, or numbered items "1. ... 2." or "(1) ... (2)"
 *   verbatim-sentence    a sentence of more than 50 words
 * They are applied to every paraphrase and exception note. No heuristic can prove text original:
 * the certification of rules/CONTRIBUTING.md is what does; these catch the common accidents.
 *
 *   pnpm lint:rules [pack ...]
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { pathToFileURL } from 'node:url';
import { deferredMeasures, loadPack, officialRegistry, packDirs, REPO, ruleMeasures, RULES_DIR, within, type PackSource } from './packs.ts';

export const HEURISTICS = [
  'advice-wording',
  'verbatim-shall',
  'verbatim-quote',
  'verbatim-sections',
  'verbatim-table',
  'verbatim-structure',
  'verbatim-sentence',
] as const;

export interface LintFinding {
  check: string;
  file: string;
  rule?: string;
  message: string;
  /** Set when a reviewer's override accepts a heuristic finding: it is reported, and does not fail. */
  overriddenBy?: string;
}

export interface Viewer {
  host: string;
  publisher: string;
  codes?: string[];
  note?: string;
}

export interface Viewers {
  viewers: Viewer[];
  synthetic: string[];
}

export interface LintContext {
  viewers: Viewers;
  deferred: Set<string>;
  assurance: RegExp;
  extensions: Set<string>;
}

export function loadViewers(root = REPO): Viewers {
  return JSON.parse(readFileSync(join(root, 'rules', 'viewers.json'), 'utf8')) as Viewers;
}

/** The assurance pattern, as spec/rules 2.5 states it (ECMAScript, flag i). */
export function assurancePattern(root = REPO): RegExp {
  const md = readFileSync(join(root, 'spec', 'rules', '02-packs.md'), 'utf8');
  const at = md.indexOf('**assurance pattern**');
  const m = /```text\n(.+)\n```/.exec(md.slice(at));
  if (at < 0 || !m) throw new Error('spec/rules/02-packs.md: the assurance pattern was not found');
  return new RegExp(m[1]!, 'i');
}

export function lintContext(root = REPO): LintContext {
  return { viewers: loadViewers(root), deferred: deferredMeasures(root), assurance: assurancePattern(root), extensions: new Set(officialRegistry(root).keys()) };
}

const ADVICE = /\b(pass(es|ed)?|satisf(y|ies|ied)|conform(s|ed|ing|ance)?|approved|guarantee[sd]?)\b/i;
const SECTION_REF = /(?:§\s*\d+(?:\.\d+)*|\b[A-Z]{0,2}\d+(?:\.\d+)+(?:\([A-Za-z0-9]+\))*|\bsection\s+\d+)/gi;
const words = (s: string) => s.split(/\s+/).filter(Boolean).length;

/** The verbatim heuristics and advice wording that fire on one piece of text. */
export function heuristics(text: string): { check: (typeof HEURISTICS)[number]; message: string }[] {
  const out: { check: (typeof HEURISTICS)[number]; message: string }[] = [];
  const advice = ADVICE.exec(text);
  if (advice) out.push({ check: 'advice-wording', message: `"${advice[0]}" grades a design; say what the requirement asks instead` });
  if (/\bshall\b/i.test(text)) out.push({ check: 'verbatim-shall', message: '"shall" is code text\'s word; write what is asked in plain words' });
  for (const m of text.matchAll(/"([^"]*)"|“([^”]*)”/g)) {
    const span = m[1] ?? m[2] ?? '';
    if (words(span) >= 6) {
      out.push({ check: 'verbatim-quote', message: `a quoted span of ${words(span)} words: never quote a code` });
      break;
    }
  }
  const refs = new Set([...text.matchAll(SECTION_REF)].map((m) => m[0]));
  if (refs.size >= 3) out.push({ check: 'verbatim-sections', message: `${refs.size} section references (${[...refs].join(', ')}): pasted text is dense with them` });
  const numbers = text.match(/\b\d+(?:[.,/]\d+)*\b/g) ?? [];
  if (/[|\t]/.test(text) || /\n\s*\d/.test(text) || numbers.length >= 6)
    out.push({ check: 'verbatim-table', message: 'table-like text (a pipe, a tab, a line starting with a number, or six or more numbers): thresholds go in the rule\'s values' });
  const enumerated = (text.match(/(?:^|\s)\d+\.\s+[A-Z]/g) ?? []).length + (text.match(/(?:^|\s)\(\d+\)\s/g) ?? []).length;
  if (/\bexceptions?\s*:/i.test(text) || enumerated >= 2) out.push({ check: 'verbatim-structure', message: 'a code\'s structure (an "Exception:" label or numbered items)' });
  const long = text.split(/(?<=[.;:!?])\s+/).find((s) => words(s) > 50);
  if (long) out.push({ check: 'verbatim-sentence', message: `a sentence of ${words(long)} words` });
  return out;
}

/** Every text of a pack's files: the evaluator's text (spec/rules 2.5) and the format's own. */
function packTexts(src: PackSource): { file: string; rule?: string; where: string; text: string }[] {
  const m = src.manifest;
  const out: { file: string; rule?: string; where: string; text: string }[] = [];
  const add = (file: string, where: string, text: string | undefined, rule?: string) => {
    if (text !== undefined) out.push({ file, rule, where, text });
  };
  add(src.file, 'title', m.title);
  add(src.file, 'description', m.description);
  add(src.file, 'attribution', m.attribution);
  add(src.file, 'jurisdiction', m.jurisdiction);
  m.editions.forEach((e, i) => add(src.file, `editions[${i}].title`, e.title));
  m.domains.forEach((d, i) => add(src.file, `domains[${i}].title`, d.title));
  m.coverage.forEach((c, i) => add(src.file, `coverage[${i}].note`, c.note));
  for (const r of src.rules) {
    const p = r.rule.provenance;
    add(r.file, 'title', r.rule.title, r.id);
    add(r.file, 'paraphrase', r.rule.paraphrase, r.id);
    r.rule.exceptions?.forEach((e, i) => add(r.file, `exceptions[${i}].note`, e.note, r.id));
    add(r.file, 'provenance.note', p.note, r.id);
    if (p.review.status === 'reviewed') add(r.file, 'provenance.review.scope', p.review.scope, r.id);
    p.lintOverrides?.forEach((o, i) => add(r.file, `provenance.lintOverrides[${i}].note`, o.note, r.id));
    for (const f of r.fixtures) add(f.file, 'description', f.expect.description, r.id);
  }
  return out;
}

/** Lints one pack's files. Overridden heuristic findings are returned with overriddenBy set. */
export function lintPack(src: PackSource, ctx: LintContext): LintFinding[] {
  const out: LintFinding[] = [];
  const m = src.manifest;
  if (!m) return out;
  const synthetic = m.synthetic === true;
  const push = (check: string, file: string, message: string, rule?: string) => out.push({ check, file, message, ...(rule ? { rule } : {}) });

  // assurance, everywhere
  for (const t of packTexts(src)) {
    const hit = ctx.assurance.exec(t.text);
    if (hit) push('assurance', t.file, `${t.where}: "${hit[0]}" matches the assurance pattern (spec/rules 2.5); a pack is advice and never says a design meets a code`, t.rule);
  }

  // editions
  const key = (c: { code: string; edition: string }) => `${c.code} ${c.edition}`;
  const listed = new Set<string>();
  for (const e of m.editions) {
    if (listed.has(key(e))) push('edition-declared', src.file, `editions: ${key(e)} is listed twice`);
    listed.add(key(e));
  }
  const cited = new Set<string>();
  for (const c of m.coverage) cited.add(key(c));
  for (const r of src.rules) cited.add(key(r.rule.citation));
  for (const k of cited) if (!listed.has(k)) push('edition-declared', src.file, `${k} is cited but not listed in editions`);
  for (const k of listed) if (!cited.has(k)) push('edition-declared', src.file, `editions lists ${k}, which no rule or coverage entry cites`);

  // synthetic codes
  for (const k of cited) {
    const test = k.startsWith('TEST-');
    if (synthetic && !test) push('synthetic-code', src.file, `a synthetic pack cites only TEST- codes, and cites ${k}`);
    if (!synthetic && test) push('synthetic-code', src.file, `${k} is a synthetic code; only a pack marked "synthetic" may cite it`);
  }

  // coverage
  const domains = new Set<string>();
  for (const d of m.domains) {
    if (domains.has(d.id)) push('coverage', src.file, `domains: "${d.id}" is declared twice`);
    domains.add(d.id);
  }
  const used = new Set(m.coverage.map((c) => c.domain));
  for (const d of domains) if (!used.has(d)) push('coverage', src.file, `domain "${d}" has no coverage entry`);
  const entries = new Set<string>();
  m.coverage.forEach((c, i) => {
    const k = `${key(c)} ${c.section}`;
    if (entries.has(k)) push('coverage', src.file, `coverage[${i}]: ${k} is listed twice`);
    entries.add(k);
    if (!domains.has(c.domain)) push('coverage', src.file, `coverage[${i}]: domain "${c.domain}" is not declared in domains`);
    for (const n of c.needs ?? [])
      if (!ctx.deferred.has(n)) push('coverage', src.file, `coverage[${i}]: needs "${n}", which is not a deferred measure of spec/rules 4.8`);
    if (c.needs && c.status === 'addressed') push('coverage', src.file, `coverage[${i}]: an addressed entry needs nothing; mark it partial or notAddressed`);
    const inside = src.rules.filter((r) => key(r.rule.citation) === key(c) && within(r.rule.citation.section, c.section));
    if (c.status !== 'notAddressed' && !inside.length) push('coverage', src.file, `coverage[${i}]: ${k} is ${c.status}, but no rule cites it or a section within it`);
  });
  for (const r of src.rules) {
    const c = r.rule.citation;
    const holders = m.coverage.filter((e) => key(e) === key(c) && within(c.section, e.section));
    if (!holders.length) {
      push('coverage', r.file, `${key(c)} ${c.section} falls within no coverage entry of the manifest`, r.id);
      continue;
    }
    const nearest = holders.reduce((a, b) => (b.section.length > a.section.length ? b : a));
    if (nearest.status === 'notAddressed')
      push('coverage', r.file, `${key(c)} ${c.section} falls within ${nearest.section}, which the manifest says is notAddressed`, r.id);
  }

  // each rule
  const synthHosts = new Set(ctx.viewers.synthetic);
  for (const r of src.rules) {
    const rule = r.rule;
    const p = rule.provenance;
    // paraphrase length
    const n = rule.paraphrase.length;
    if (n < 40 || n > 1200 || words(rule.paraphrase) < 8)
      push('paraphrase-length', r.file, `the paraphrase is ${n} characters and ${words(rule.paraphrase)} words; it is 40-1200 characters and at least 8 words`, r.id);
    // viewer link
    let url: URL | undefined;
    try {
      url = new URL(rule.citation.link);
    } catch {
      push('viewer-host', r.file, `citation.link is not a URL`, r.id);
    }
    if (url) {
      if (url.protocol !== 'https:' || url.username || url.password) push('viewer-host', r.file, 'citation.link is https, with no user name or password', r.id);
      const host = url.hostname.toLowerCase();
      if (synthetic) {
        if (!synthHosts.has(host)) push('viewer-host', r.file, `a synthetic pack links only to ${[...synthHosts].join(' or ')}, not ${host}`, r.id);
      } else {
        const v = ctx.viewers.viewers.find((x) => x.host === host);
        if (!v) push('viewer-host', r.file, `${host} is not a publisher's free public viewer listed in rules/viewers.json`, r.id);
        else if (v.codes && !v.codes.includes(rule.citation.code))
          push('viewer-host', r.file, `${host} (${v.publisher}) does not publish ${rule.citation.code}`, r.id);
      }
    }
    // provenance
    if (p.edition !== rule.citation.edition)
      push('provenance', r.file, `provenance.edition ${p.edition} is not the cited edition ${rule.citation.edition} (spec/rules 3.9)`, r.id);
    if ((p.method === 'synthetic') !== synthetic)
      push('provenance', r.file, synthetic ? 'a synthetic pack\'s rules are verified by method "synthetic"' : 'method "synthetic" is for synthetic packs only', r.id);
    // fixtures
    const deferred = [...ruleMeasures(rule)].filter((x) => ctx.deferred.has(x));
    const outcomes = new Set(r.fixtures.map((f) => f.expect.outcome));
    if (deferred.length) {
      if (!outcomes.has('deferred')) push('fixtures', r.file, `the rule uses the deferred measure ${deferred.join(', ')}, and has no deferred fixture`, r.id);
      if (outcomes.has('pass') || outcomes.has('fail')) push('fixtures', r.file, 'a rule using a deferred measure is not evaluated; its fixtures are deferred ones', r.id);
    } else {
      for (const o of ['pass', 'fail'] as const) if (!outcomes.has(o)) push('fixtures', r.file, `the rule has no ${o === 'pass' ? 'passing' : 'failing'} fixture`, r.id);
      if (outcomes.has('deferred')) push('fixtures', r.file, 'the rule uses no deferred measure, and has a deferred fixture', r.id);
    }
    for (const f of r.fixtures)
      for (const x of f.expect.extensions ?? []) if (!ctx.extensions.has(x)) push('fixtures', f.file, `${x} is not an extension in registry/`, r.id);
    // heuristics, and their overrides
    const fired = new Set<string>();
    const texts = [{ where: 'paraphrase', text: rule.paraphrase }, ...(rule.exceptions ?? []).map((e, i) => ({ where: `exceptions[${i}].note`, text: e.note }))];
    for (const t of texts)
      for (const h of heuristics(t.text)) {
        fired.add(h.check);
        const o = p.lintOverrides?.find((x) => x.check === h.check);
        out.push({ check: h.check, file: r.file, rule: r.id, message: `${t.where}: ${h.message}`, ...(o ? { overriddenBy: `${o.reviewer} on ${o.on}: ${o.note}` } : {}) });
      }
    for (const o of p.lintOverrides ?? [])
      if (!fired.has(o.check)) push('stale-override', r.file, `the override of ${o.check} accepts a finding that no longer fires; remove it`, r.id);
  }
  return out;
}

/** no-automation: no script in tools/, rules/ or .github/ names a viewer host listed in rules/viewers.json. */
export function lintRepository(root = REPO, viewers = loadViewers(root)): LintFinding[] {
  const out: LintFinding[] = [];
  const hosts = viewers.viewers.map((v) => v.host.toLowerCase());
  const scripts = /\.(ts|mts|cts|js|mjs|cjs|py|sh|ya?ml)$/;
  const walk = (dir: string) => {
    if (!existsSync(dir)) return;
    for (const name of readdirSync(dir).sort()) {
      if (name === 'node_modules' || name === '__pycache__') continue;
      const p = join(dir, name);
      if (statSync(p).isDirectory()) walk(p);
      else if (scripts.test(name)) {
        const text = readFileSync(p, 'utf8').toLowerCase();
        for (const h of hosts)
          if (text.includes(h))
            out.push({ check: 'no-automation', file: relative(root, p), message: `names ${h}: no script may reach a code viewer (FLR-REQ-106); a viewer link lives only in a rule's citation` });
      }
    }
  };
  for (const d of ['tools', 'rules', '.github']) walk(join(root, d));
  return out;
}

export const failing = (findings: LintFinding[]) => findings.filter((f) => !f.overriddenBy);

export function formatFinding(f: LintFinding): string {
  const at = f.rule ? `${f.file} (${f.rule})` : f.file;
  return `${at}: [${f.check}] ${f.message}${f.overriddenBy ? `\n    overridden by ${f.overriddenBy}` : ''}`;
}

function main(argv: string[]): number {
  const ctx = lintContext();
  const dirs = argv.length ? argv.map((a) => join(RULES_DIR, a)) : packDirs();
  let errors = 0;
  for (const dir of dirs) {
    const src = loadPack(dir);
    for (const p of src.problems) console.error(p);
    errors += src.problems.length;
    const findings = lintPack(src, ctx);
    for (const f of findings) (f.overriddenBy ? console.log : console.error)(formatFinding(f));
    const bad = failing(findings).length;
    errors += bad;
    console.log(`lint: ${src.manifest?.name ?? dir}: ${src.rules.length} rules, ${bad} problem${bad === 1 ? '' : 's'}, ${findings.length - bad} overridden`);
  }
  const repo = lintRepository();
  for (const f of repo) console.error(formatFinding(f));
  errors += repo.length;
  if (errors) {
    console.error(`rule lint failed: ${errors} problem${errors === 1 ? '' : 's'}`);
    return 1;
  }
  console.log('rule lint passed');
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) process.exit(main(process.argv.slice(2)));

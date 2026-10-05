/**
 * The coverage matrix of the rule-pack format (FLR-T-6.3, FLR-REQ-096): from built packs, every
 * section of every code edition they address - and the ones they say they do not - with its status,
 * the rules that check it, their reviewed badges and their verification dates, and a summary per
 * domain. Deterministic: the same packs give the same bytes, JSON and Markdown.
 *
 * A row is a coverage entry a pack declares (spec/rules 2.4). Its status:
 *   covered     declared addressed, and every rule within it is evaluated
 *   partial     declared partial; or addressed, with some of its rules on deferred measures
 *   deferred    every rule within it uses a deferred measure (spec/rules 4.8), or it is declared
 *               notAddressed and names the deferred measures it needs: it waits on data Core lacks
 *   notCovered  declared notAddressed, and waiting on nothing named
 * A rule belongs to the most specific entry its cited section falls within; a rule within no entry
 * (a pack without the format's lint) gets a row of its own, declared "undeclared".
 *
 *   pnpm coverage:matrix            writes rules/<pack>/generated/coverage.{json,md} and rules/coverage.{json,md}
 *   pnpm coverage:matrix --check    fails if any of them differs from what it would write
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { pathToFileURL } from 'node:url';
import { buildPack, canonicalJson, compareSections, deferredMeasures, loadPack, packDirs, REPO, ruleMeasures, RULES_DIR, within, type Test } from './packs.ts';
import { CURRENT_RULES, type Json, type RulesVersion } from './schema.ts';

export type MatrixStatus = 'covered' | 'partial' | 'deferred' | 'notCovered';
export const STATUSES: MatrixStatus[] = ['covered', 'partial', 'deferred', 'notCovered'];
const LABEL: Record<MatrixStatus, string> = { covered: 'covered', partial: 'partial', deferred: 'deferred (needs data)', notCovered: 'not covered' };

export interface MatrixRule {
  pack: string;
  rule: string;
  title: string;
  section: string;
  severity: string;
  link?: string;
  verifiedBy: string;
  verifiedOn: string;
  review: 'reviewed' | 'unreviewed';
  reviewed?: { by: string; on: string; credential?: string };
  deferred: string[];
}

export interface MatrixRow {
  pack: string;
  version: string;
  code: string;
  edition: string;
  section: string;
  domain: string | null;
  declared: 'addressed' | 'partial' | 'notAddressed' | 'undeclared';
  status: MatrixStatus;
  note?: string;
  /** The deferred measures the row waits on: those its entry needs and those its rules use. */
  needs: string[];
  rules: MatrixRule[];
  reviewed: number;
  oldestVerification: string | null;
  newestVerification: string | null;
}

export interface DomainSummary {
  pack: string;
  domain: string | null;
  title: string;
  sections: Record<MatrixStatus, number>;
  rules: number;
  reviewed: number;
  oldestVerification: string | null;
  newestVerification: string | null;
}

export interface MatrixPack {
  name: string;
  version: string;
  title: string;
  license: string;
  attribution: string | null;
  jurisdiction: string | null;
  synthetic: boolean;
  rules: number;
  reviewed: number;
}

export interface Matrix {
  floorspecRules: RulesVersion;
  packs: MatrixPack[];
  domains: DomainSummary[];
  rows: MatrixRow[];
  rules: MatrixRule[];
}

interface BuiltRule {
  title: string;
  citation: { code: string; edition: string; section: string; link?: string };
  severity: string;
  applies: { where?: Test };
  select?: { where?: Test };
  requirement: Test;
  exceptions?: { when: Test }[];
  provenance: { verifiedBy: string; verifiedOn: string; reviewed?: { by: string; on: string; credential?: string } };
  extras?: { packFormat?: { review?: string } };
}
interface BuiltPack {
  name: string;
  version: string;
  title: string;
  license: string;
  rules: Record<string, BuiltRule>;
  coverage?: { code: string; edition: string; section: string; status: 'addressed' | 'partial' | 'notAddressed'; note?: string }[];
  extras?: {
    packFormat?: {
      attribution?: string;
      jurisdiction?: string;
      synthetic?: boolean;
      domains?: { id: string; title: string }[];
      coverage?: { domain?: string; needs?: string[] }[];
    };
  };
}

const minMax = (dates: string[]) => {
  const s = [...dates].sort();
  return { oldest: s[0] ?? null, newest: s[s.length - 1] ?? null };
};

/** The matrix of a set of built packs (spec/rules 2.1 objects, with or without extras.packFormat). */
export function coverageMatrix(packs: unknown[], deferred: Set<string>): Matrix {
  const rows: MatrixRow[] = [];
  const allRules: MatrixRule[] = [];
  const domains: DomainSummary[] = [];
  const meta: MatrixPack[] = [];
  for (const raw of [...(packs as BuiltPack[])].sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))) {
    const fmt = raw.extras?.packFormat ?? {};
    const titles = new Map((fmt.domains ?? []).map((d) => [d.id, d.title]));
    const rules: MatrixRule[] = Object.keys(raw.rules)
      .sort()
      .map((id) => {
        const r = raw.rules[id]!;
        const reviewed = r.provenance.reviewed;
        const mr: MatrixRule = {
          pack: raw.name,
          rule: id,
          title: r.title,
          section: r.citation.section,
          severity: r.severity,
          verifiedBy: r.provenance.verifiedBy,
          verifiedOn: r.provenance.verifiedOn,
          review: reviewed ? 'reviewed' : 'unreviewed',
          deferred: [...ruleMeasures(r)].filter((m) => deferred.has(m)).sort(),
        };
        if (r.citation.link) mr.link = r.citation.link;
        if (reviewed) mr.reviewed = reviewed;
        return mr;
      });
    allRules.push(...rules);
    const entries = (raw.coverage ?? []).map((c, i) => ({ ...c, domain: fmt.coverage?.[i]?.domain ?? null, needs: fmt.coverage?.[i]?.needs ?? [] }));
    const assigned = new Map<number, MatrixRule[]>();
    const loose = new Map<string, MatrixRule[]>();
    for (const mr of rules) {
      const c = raw.rules[mr.rule]!.citation;
      let best = -1;
      entries.forEach((e, i) => {
        if (e.code === c.code && e.edition === c.edition && within(c.section, e.section) && (best < 0 || e.section.length > entries[best]!.section.length)) best = i;
      });
      if (best >= 0) assigned.set(best, [...(assigned.get(best) ?? []), mr]);
      else {
        const k = JSON.stringify([c.code, c.edition, c.section]);
        loose.set(k, [...(loose.get(k) ?? []), mr]);
      }
    }
    const row = (code: string, edition: string, section: string, domain: string | null, declared: MatrixRow['declared'], inRow: MatrixRule[], needs0: string[], note?: string): MatrixRow => {
      const deferredRules = inRow.filter((r) => r.deferred.length);
      const needs = [...new Set([...needs0, ...deferredRules.flatMap((r) => r.deferred)])].sort();
      let status: MatrixStatus;
      if (declared === 'notAddressed') status = needs0.length ? 'deferred' : 'notCovered';
      else if (inRow.length && deferredRules.length === inRow.length) status = 'deferred';
      else if (declared === 'partial' || deferredRules.length) status = 'partial';
      else status = inRow.length ? 'covered' : 'notCovered';
      const { oldest, newest } = minMax(inRow.map((r) => r.verifiedOn));
      const out: MatrixRow = {
        pack: raw.name, version: raw.version, code, edition, section, domain, declared, status, needs,
        rules: inRow, reviewed: inRow.filter((r) => r.review === 'reviewed').length, oldestVerification: oldest, newestVerification: newest,
      };
      if (note !== undefined) out.note = note;
      return out;
    };
    const packRows: MatrixRow[] = [];
    entries.forEach((e, i) => packRows.push(row(e.code, e.edition, e.section, e.domain, e.status, assigned.get(i) ?? [], e.needs, e.note)));
    for (const [k, inRow] of loose) {
      const [code, edition, section] = JSON.parse(k) as [string, string, string];
      packRows.push(row(code, edition, section, null, 'undeclared', inRow, []));
    }
    rows.push(...packRows);
    // the summary per domain, in the order the pack declares its domains
    const order = [...(fmt.domains ?? []).map((d) => d.id as string | null)];
    for (const r of packRows) if (!order.includes(r.domain)) order.push(r.domain);
    for (const d of order) {
      const inDomain = packRows.filter((r) => r.domain === d);
      if (!inDomain.length) continue;
      const sections = Object.fromEntries(STATUSES.map((s) => [s, inDomain.filter((r) => r.status === s).length])) as Record<MatrixStatus, number>;
      const dr = inDomain.flatMap((r) => r.rules);
      const { oldest, newest } = minMax(dr.map((r) => r.verifiedOn));
      domains.push({
        pack: raw.name, domain: d, title: d === null ? 'No domain' : (titles.get(d) ?? d), sections,
        rules: dr.length, reviewed: dr.filter((r) => r.review === 'reviewed').length, oldestVerification: oldest, newestVerification: newest,
      });
    }
    meta.push({
      name: raw.name, version: raw.version, title: raw.title, license: raw.license,
      attribution: fmt.attribution ?? null, jurisdiction: fmt.jurisdiction ?? null, synthetic: fmt.synthetic === true,
      rules: rules.length, reviewed: rules.filter((r) => r.review === 'reviewed').length,
    });
  }
  const cmp = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
  rows.sort((a, b) => cmp(a.code, b.code) || compareSections(a.edition, b.edition) || compareSections(a.section, b.section) || cmp(a.pack, b.pack));
  allRules.sort((a, b) => cmp(a.pack, b.pack) || cmp(a.rule, b.rule));
  return { floorspecRules: CURRENT_RULES, packs: meta, domains, rows, rules: allRules };
}

const cell = (s: string) => s.replace(/\\/g, '\\\\').replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');

export const MATRIX_NOTICE =
  'Floorspec findings are advisory. They are not a plan review, and the authority having jurisdiction decides. ' +
  'A covered section is one these rules check; a design with no finding there is one these rules found nothing to flag in, and nothing more.';

/** The matrix as Markdown. */
export function matrixMarkdown(m: Matrix, heading: string): string {
  const L: string[] = [];
  L.push(`# ${heading}`, '');
  L.push('Generated by `pnpm coverage:matrix` from the packs\' files; do not edit it by hand.', '');
  L.push(`> ${MATRIX_NOTICE}`, '');
  if (!m.packs.length) {
    L.push('No pack is published yet.', '');
    return `${L.join('\n').trimEnd()}\n`;
  }
  L.push('## Packs', '', '| Pack | Version | Title | Licence | Jurisdiction | Rules | Reviewed |', '|---|---|---|---|---|---|---|');
  for (const p of m.packs)
    L.push(`| \`${p.name}\`${p.synthetic ? ' (synthetic)' : ''} | ${p.version} | ${cell(p.title)} | ${p.license} | ${cell(p.jurisdiction ?? '—')} | ${p.rules} | ${p.reviewed} of ${p.rules} |`);
  L.push('');
  for (const p of m.packs) if (p.attribution) L.push(`- \`${p.name}\`: ${cell(p.attribution)}`);
  L.push('', '## Summary by domain', '', '| Pack | Domain | Covered | Partial | Deferred (needs data) | Not covered | Rules | Reviewed | Oldest verification | Newest verification |', '|---|---|---|---|---|---|---|---|---|---|');
  for (const d of m.domains)
    L.push(`| \`${d.pack}\` | ${cell(d.title)} | ${d.sections.covered} | ${d.sections.partial} | ${d.sections.deferred} | ${d.sections.notCovered} | ${d.rules} | ${d.reviewed} of ${d.rules} | ${d.oldestVerification ?? '—'} | ${d.newestVerification ?? '—'} |`);
  L.push('');
  const groups = new Map<string, MatrixRow[]>();
  for (const r of m.rows) {
    const k = `${r.code} ${r.edition}`;
    groups.set(k, [...(groups.get(k) ?? []), r]);
  }
  const titles = new Map(m.domains.map((d) => [`${d.pack}\u0000${d.domain}`, d.title]));
  for (const [k, rs] of groups) {
    L.push(`## ${k}`, '', '| Section | Pack | Domain | Status | Rules | Reviewed | Verified (oldest) | Note |', '|---|---|---|---|---|---|---|---|');
    for (const r of rs) {
      const status = r.needs.length ? `${LABEL[r.status]}: ${r.needs.map((n) => `\`${n}\``).join(', ')}` : LABEL[r.status];
      const rules = r.rules.length ? r.rules.map((x) => `\`${x.rule}\` (${cell(x.section)})`).join(', ') : '—';
      const domain = titles.get(`${r.pack}\u0000${r.domain}`) ?? r.domain ?? '—';
      L.push(`| ${cell(r.section)} | \`${r.pack}\` | ${cell(domain)} | ${status} | ${rules} | ${r.rules.length ? `${r.reviewed} of ${r.rules.length}` : '—'} | ${r.oldestVerification ?? '—'} | ${cell(r.note ?? (r.declared === 'undeclared' ? 'no coverage entry declares this section' : ''))} |`);
    }
    L.push('');
  }
  L.push('## Rules', '', '| Rule | Citation | Severity | Verified | Verified by | Review |', '|---|---|---|---|---|---|');
  const cites = new Map(m.rows.flatMap((r) => r.rules.map((x) => [`${x.pack}/${x.rule}`, `${r.code} ${r.edition}`])));
  for (const r of m.rules) {
    const cite = `${cites.get(`${r.pack}/${r.rule}`) ?? ''} ${r.section}`.trim();
    const review = r.reviewed ? `reviewed by ${cell(r.reviewed.by)}${r.reviewed.credential ? ` (${cell(r.reviewed.credential)})` : ''}, ${r.reviewed.on}` : 'unreviewed';
    const deferredNote = r.deferred.length ? `; not evaluated until ${r.deferred.map((n) => `\`${n}\``).join(', ')} is defined` : '';
    L.push(`| \`${r.pack}/${r.rule}\` ${cell(r.title)} | ${r.link ? `[${cell(cite)}](${r.link})` : cell(cite)} | ${r.severity}${deferredNote} | ${r.verifiedOn} | ${cell(r.verifiedBy)} | ${review} |`);
  }
  return `${L.join('\n').trimEnd()}\n`;
}

export interface MatrixOutput {
  path: string;
  text: string;
}

/** The files the matrix of the packs under rules/ is written to: one per pack, and one across every non-synthetic pack. */
export function matrixOutputs(packs: { dir: string; built: unknown; synthetic: boolean }[], deferred = deferredMeasures(), root = RULES_DIR): MatrixOutput[] {
  const out: MatrixOutput[] = [];
  for (const p of packs) {
    const m = coverageMatrix([p.built], deferred);
    const meta = m.packs[0]!;
    out.push({ path: join(p.dir, 'generated', 'coverage.json'), text: canonicalJson(m as unknown as Json) });
    out.push({ path: join(p.dir, 'generated', 'COVERAGE.md'), text: matrixMarkdown(m, `Coverage: ${meta.title} (\`${meta.name}\` ${meta.version})`) });
  }
  const published = coverageMatrix(packs.filter((p) => !p.synthetic).map((p) => p.built), deferred);
  out.push({ path: join(root, 'coverage.json'), text: canonicalJson(published as unknown as Json) });
  out.push({ path: join(root, 'COVERAGE.md'), text: matrixMarkdown(published, 'Floorspec rule packs: coverage') });
  return out;
}

/** Writes outputs, or with check compares them: the differing paths. */
export function writeOrCheck(outputs: MatrixOutput[], check: boolean): string[] {
  const differ: string[] = [];
  for (const o of outputs) {
    const now = existsSync(o.path) ? readFileSync(o.path, 'utf8') : undefined;
    if (now === o.text) continue;
    differ.push(relative(REPO, o.path));
    if (!check) {
      mkdirSync(dirname(o.path), { recursive: true });
      writeFileSync(o.path, o.text);
    }
  }
  return differ;
}

function main(argv: string[]): number {
  const check = argv.includes('--check');
  const packs = packDirs().map((dir) => {
    const src = loadPack(dir);
    if (src.problems.length) throw new Error(src.problems.join('\n'));
    return { dir, built: buildPack(src), synthetic: src.manifest.synthetic === true };
  });
  const differ = writeOrCheck(matrixOutputs(packs), check);
  for (const d of differ) (check ? console.error : console.log)(`${check ? 'differs' : 'wrote'}: ${d}`);
  if (check && differ.length) {
    console.error('coverage matrix check failed: run pnpm coverage:matrix');
    return 1;
  }
  console.log(`coverage matrix: ${packs.length} pack${packs.length === 1 ? '' : 's'}${check ? ', up to date' : ''}`);
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) process.exit(main(process.argv.slice(2)));

/**
 * The extension registry's lifecycle gates (FLR-T-10.3, FLR-REQ-138, FLR-REQ-092; registry/README.md):
 * what an entry in registry/<NAME>/ must have at each status, Proposal → Draft → Release Candidate →
 * Ratified, and how a pull request may move it.
 *
 *   pnpm registry:check                                  every entry, as it stands
 *   pnpm registry:check --base <commit> [--labels a,b]   ... and every change since <commit>, a
 *                                                        pull request's base (REGISTRY_BASE and
 *                                                        REGISTRY_LABELS in CI)
 *
 * Each status keeps the previous one's requirements:
 *
 * - **Proposal** — `extension.json` matching the registry entry schema, its directory named after it,
 *   and `proposal.md`, the written rationale.
 * - **Draft** — `spec.md` with tagged statements in its own ID space, whose 1.1 table gives the
 *   entry's version and status; a schema file whose `$id` is the entry's `schema`, a versioned URL;
 *   a conformance suite at conformance/ext/<NAME>/<version>/ covering every MUST and MUST NOT.
 * - **Release Candidate** — at least one implementation listed, each with evidence that it passes
 *   the suite (registry/<NAME>/evidence/*.json), unless registry/exceptions.json records an owner's
 *   decision to waive that one rule for that one version.
 * - **Ratified** — at least two implementations, each with current evidence, two of them independent
 *   of each other: different maintainers, neither sharing code with the other. The entry's schema
 *   files, its suite and every member but `implementations` are frozen at the commit that ratified it.
 *
 * And a change: a new extension or a new version enters as a Proposal or a Draft; a version moves
 * forward one status at a time and never back; a version only ever increases; nothing is removed -
 * unless the pull request carries the maintainer label (MAINTAINER_LABEL), which a maintainer adds.
 *
 * Statements, schemas and suites are also checked by pnpm statements, schema:check and coverage;
 * this script checks what the lifecycle adds to them. Evidence older than the suite it ran is a
 * warning for a Release Candidate and an error for a Ratified entry.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { pathToFileURL } from 'node:url';
import { Ajv2020 } from 'ajv/dist/2020.js';
import { registryValidator, testDirs, formatErrors } from './schema.ts';
import { extensionSpecs, extractExtension, MANDATORY } from './statements.ts';

export const STATUSES = ['proposal', 'draft', 'releaseCandidate', 'ratified'] as const;
export type Status = (typeof STATUSES)[number];
export const STATUS_NAME: Record<Status, string> = {
  proposal: 'Proposal',
  draft: 'Draft',
  releaseCandidate: 'Release Candidate',
  ratified: 'Ratified',
};
/** The label a maintainer adds to a pull request to allow a change the transition rules refuse. */
export const MAINTAINER_LABEL = 'registry-maintainer';
/** The rules an exception may waive. Nothing of Ratified can be waived. */
export const WAIVABLE = ['releaseCandidate.implementation'] as const;

export interface Entry {
  name: string;
  version: string;
  status: Status;
  schema: string;
  implementations?: { name: string; url: string }[];
  [k: string]: unknown;
}

export interface Evidence {
  file: string;
  implementation: { name: string; url: string; version: string };
  maintainer: string;
  sharesCodeWith: string[];
  extension: string;
  extensionVersion: string;
  suite: { commit: string; tests: number };
  result: { passed: number; failed: number };
  ran: string;
  run?: string;
  command?: string;
}

export interface Exception {
  extension: string;
  version: string;
  waives: (typeof WAIVABLE)[number];
  decision: string;
  until: string;
}

export interface Report {
  errors: string[];
  warnings: string[];
  notes: string[];
}

/** What the gates need from git; null when it cannot say (a shallow clone, an unknown commit). */
export interface Git {
  /** How many tests (test.json files) the directory held at the commit. */
  testsAt(commit: string, dir: string): number | null;
  /** Whether any of the paths differ between the commit and the working tree. */
  changedSince(commit: string, paths: string[]): boolean | null;
  /** The text of a file at a commit, or null when it did not exist there. */
  show(commit: string, path: string): string | null;
  /** The commits that changed a path, newest first. */
  log(path: string): string[];
  /** The registry/<NAME> directories at a commit. */
  namesAt(commit: string): string[];
}

export function gitOf(root: string): Git {
  const run = (args: string[]) => execFileSync('git', args, { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  const safe = <T>(f: () => T): T | null => {
    try {
      return f();
    } catch {
      return null;
    }
  };
  return {
    testsAt: (commit, dir) => safe(() => run(['ls-tree', '-r', '--name-only', commit, '--', dir]).split('\n').filter((p) => p.endsWith('/test.json')).length),
    changedSince: (commit, paths) =>
      safe(() => {
        try {
          execFileSync('git', ['diff', '--quiet', commit, '--', ...paths], { cwd: root, stdio: 'ignore' });
          return false;
        } catch (e) {
          if ((e as { status?: number }).status === 1) return true;
          throw e;
        }
      }),
    show: (commit, path) => safe(() => run(['show', `${commit}:${path}`])),
    log: (path) => safe(() => run(['log', '--format=%H', '--', path]).split('\n').filter(Boolean)) ?? [],
    namesAt: (commit) => safe(() => run(['ls-tree', '--name-only', `${commit}:registry`]).split('\n').filter(Boolean)) ?? [],
  };
}

const rank = (s: Status) => STATUSES.indexOf(s);

/** Semantic Versioning 2.0.0 precedence, as Core 12.3 compares versions. */
export function compareVersions(a: string, b: string): number {
  const parse = (v: string) => {
    const [core, pre] = v.split(/-(.*)/s, 2) as [string, string | undefined];
    return { nums: core.split('.').map(Number), pre: pre === undefined ? [] : pre.split('.') };
  };
  const x = parse(a);
  const y = parse(b);
  for (let i = 0; i < 3; i++) if (x.nums[i] !== y.nums[i]) return x.nums[i]! < y.nums[i]! ? -1 : 1;
  if (!x.pre.length || !y.pre.length) return x.pre.length === y.pre.length ? 0 : x.pre.length ? -1 : 1;
  for (let i = 0; i < Math.max(x.pre.length, y.pre.length); i++) {
    const p = x.pre[i];
    const q = y.pre[i];
    if (p === undefined) return -1;
    if (q === undefined) return 1;
    if (p === q) continue;
    const pn = /^\d+$/.test(p);
    const qn = /^\d+$/.test(q);
    if (pn && qn) return Number(p) < Number(q) ? -1 : 1;
    if (pn !== qn) return pn ? -1 : 1;
    return p < q ? -1 : 1;
  }
  return 0;
}

const EVIDENCE_SCHEMA = {
  type: 'object',
  required: ['implementation', 'maintainer', 'sharesCodeWith', 'extension', 'extensionVersion', 'suite', 'result', 'ran'],
  properties: {
    $comment: { type: 'string' },
    implementation: {
      type: 'object',
      required: ['name', 'url', 'version'],
      properties: {
        name: { type: 'string', minLength: 1, maxLength: 200 },
        url: { type: 'string', pattern: '^https://' },
        version: { type: 'string', minLength: 1, maxLength: 100 },
      },
      additionalProperties: false,
    },
    maintainer: { type: 'string', minLength: 1, maxLength: 200 },
    sharesCodeWith: { type: 'array', items: { type: 'string', minLength: 1 }, uniqueItems: true },
    extension: { type: 'string' },
    extensionVersion: { type: 'string' },
    suite: {
      type: 'object',
      required: ['commit', 'tests'],
      properties: { commit: { type: 'string', pattern: '^[0-9a-f]{40}$' }, tests: { type: 'integer', minimum: 1 } },
      additionalProperties: false,
    },
    result: {
      type: 'object',
      required: ['passed', 'failed'],
      properties: { passed: { type: 'integer', minimum: 0 }, failed: { type: 'integer', minimum: 0 } },
      additionalProperties: false,
    },
    ran: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}$' },
    run: { type: 'string', pattern: '^https://' },
    command: { type: 'string' },
  },
  additionalProperties: false,
} as const;

const EXCEPTIONS_SCHEMA = {
  type: 'object',
  required: ['exceptions'],
  properties: {
    $comment: { type: 'string' },
    exceptions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['extension', 'version', 'waives', 'decision', 'until'],
        properties: {
          extension: { type: 'string' },
          version: { type: 'string' },
          waives: { enum: [...WAIVABLE] },
          decision: { type: 'string', minLength: 1 },
          until: { type: 'string', minLength: 1 },
        },
        additionalProperties: false,
      },
    },
  },
  additionalProperties: false,
} as const;

const ajv = new Ajv2020({ allErrors: true, strict: true });
const validateEvidence = ajv.compile(EVIDENCE_SCHEMA);
const validateExceptions = ajv.compile(EXCEPTIONS_SCHEMA);
const validateEntry = registryValidator();

function readJson(path: string): unknown {
  return JSON.parse(readFileSync(path, 'utf8')) as unknown;
}

/** A spec.md's 1.1 table: its `| Version | `x` |` and `| Status | X |` rows. */
export function specIdentity(text: string): { version?: string; status?: string } {
  return {
    version: /^\| Version \| `([^`]+)` \|\s*$/m.exec(text)?.[1],
    status: /^\| Status \| ([^|]+?) \|\s*$/m.exec(text)?.[1],
  };
}

/** The rows of registry/README.md's extension tables: name → { version, status }. */
export function readmeRows(text: string): Map<string, { version: string; status: string }> {
  const out = new Map<string, { version: string; status: string }>();
  for (const m of text.matchAll(/^\| \[`([A-Za-z0-9_]+)`\]\([^)]*\) \| ([^|]+?) \| ([^|]+?) \|/gm)) out.set(m[1]!, { version: m[2]!, status: m[3]! });
  return out;
}

export function loadEntries(root: string): { entries: Map<string, Entry>; errors: string[] } {
  const dir = join(root, 'registry');
  const entries = new Map<string, Entry>();
  const errors: string[] = [];
  for (const name of existsSync(dir) ? readdirSync(dir).sort() : []) {
    const d = join(dir, name);
    if (!statSync(d).isDirectory()) continue;
    const f = join(d, 'extension.json');
    if (!existsSync(f)) {
      errors.push(`registry/${name}: a directory in registry/ holds an extension, and this one has no extension.json`);
      continue;
    }
    const e = readJson(f) as Entry;
    if (!validateEntry(e)) {
      errors.push(`registry/${name}/extension.json does not match the registry entry schema:\n    ${formatErrors(validateEntry.errors ?? []).join('\n    ')}`);
      continue;
    }
    if (e.name !== name) errors.push(`registry/${name}/extension.json names ${e.name}: the directory is named after the extension`);
    entries.set(name, e);
  }
  return { entries, errors };
}

export function loadEvidence(root: string, name: string, report: Report): Evidence[] {
  const dir = join(root, 'registry', name, 'evidence');
  const out: Evidence[] = [];
  if (!existsSync(dir)) return out;
  for (const f of readdirSync(dir).sort()) {
    const path = join(dir, f);
    const rel = relative(root, path);
    if (!f.endsWith('.json')) {
      report.errors.push(`${rel}: evidence is a JSON file`);
      continue;
    }
    const v = readJson(path);
    if (!validateEvidence(v)) {
      report.errors.push(`${rel} is not evidence (registry/README.md, "Evidence"):\n    ${formatErrors(validateEvidence.errors ?? []).join('\n    ')}`);
      continue;
    }
    out.push({ ...(v as unknown as Omit<Evidence, 'file'>), file: rel });
  }
  return out;
}

export function loadExceptions(root: string, report: Report): Exception[] {
  const path = join(root, 'registry', 'exceptions.json');
  if (!existsSync(path)) return [];
  const v = readJson(path);
  if (!validateExceptions(v)) {
    report.errors.push(`registry/exceptions.json:\n    ${formatErrors(validateExceptions.errors ?? []).join('\n    ')}`);
    return [];
  }
  return (v as { exceptions: Exception[] }).exceptions;
}

/** The suite's mandatory statements that no test covers, or null when the extension has no spec.md. */
function uncovered(root: string, name: string, suite: string): string[] | null {
  const spec = extensionSpecs(root).specs.find((s) => s.name === name);
  if (!spec) return null;
  const covered = new Set<string>();
  for (const d of testDirs(suite)) {
    const t = readJson(join(d, 'test.json')) as { covers?: string[] };
    for (const id of t.covers ?? []) covered.add(id);
  }
  return extractExtension(root, spec).statements.filter((s) => MANDATORY.includes(s.level) && !covered.has(s.id)).map((s) => s.id);
}

/** The commit at which the entry's current version became ratified, or null. */
export function ratifiedAt(git: Git, name: string, entry: Entry): string | null {
  let at: string | null = null;
  for (const c of git.log(`registry/${name}/extension.json`)) {
    const text = git.show(c, `registry/${name}/extension.json`);
    if (text === null) break;
    let e: Entry;
    try {
      e = JSON.parse(text) as Entry;
    } catch {
      break;
    }
    if (e.status !== 'ratified' || e.version !== entry.version) break;
    at = c;
  }
  return at;
}

const strip = (e: Entry) => {
  const { implementations: _, ...rest } = e;
  return JSON.stringify(rest);
};

/** Every entry, against what its status asks. */
export function checkEntries(root: string, git: Git): Report & { summary: string[] } {
  const report: Report & { summary: string[] } = { errors: [], warnings: [], notes: [], summary: [] };
  const { entries, errors } = loadEntries(root);
  report.errors.push(...errors);
  const exceptions = loadExceptions(root, report);
  const readmePath = join(root, 'registry', 'README.md');
  const readme = existsSync(readmePath) ? readmeRows(readFileSync(readmePath, 'utf8')) : new Map();
  for (const x of exceptions) {
    const e = entries.get(x.extension);
    if (!e || e.version !== x.version) report.errors.push(`registry/exceptions.json: ${x.extension} ${x.version} is not in the registry; remove the exception`);
    else if (e.status !== 'releaseCandidate') report.errors.push(`registry/exceptions.json: ${x.extension} ${x.version} is ${STATUS_NAME[e.status]}, and the exception waives a Release Candidate rule; remove it`);
  }

  for (const [name, e] of entries) {
    const dir = join(root, 'registry', name);
    const at = (rule: string) => `registry/${name} (${STATUS_NAME[e.status]} ${e.version}): ${rule}`;
    const fail = (rule: string) => report.errors.push(at(rule));
    const row = readme.get(name);
    if (!row) fail(`registry/README.md lists every extension in a table row \`| [\`${name}\`](...) | version | status |\``);
    else if (row.version !== e.version || row.status !== STATUS_NAME[e.status])
      fail(`registry/README.md lists it as ${row.status} ${row.version}`);

    // Proposal: a written rationale.
    if (e.status === 'proposal' && !existsSync(join(dir, 'proposal.md'))) fail('a Proposal has proposal.md, its written rationale');
    const evidence = loadEvidence(root, name, report);
    for (const ev of evidence)
      if (ev.extension !== name || ev.extensionVersion !== e.version)
        fail(`${ev.file} is evidence for ${ev.extension} ${ev.extensionVersion}, not this version`);
    if (rank(e.status) < rank('draft')) {
      report.summary.push(`${name} ${e.version}: ${STATUS_NAME[e.status]}`);
      continue;
    }

    // Draft: a specification, a schema at a versioned URL, a suite covering every MUST.
    const specPath = join(dir, 'spec.md');
    if (!existsSync(specPath)) fail('a Draft has spec.md');
    else {
      const id = specIdentity(readFileSync(specPath, 'utf8'));
      if (id.version !== e.version || id.status !== STATUS_NAME[e.status])
        fail(`spec.md's 1.1 table gives version ${id.version ?? '(none)'} and status ${id.status ?? '(none)'}: it gives the entry's, \`${e.version}\` and ${STATUS_NAME[e.status]}`);
    }
    const schemaFiles = readdirSync(dir).filter((f) => f.endsWith('.schema.json'));
    const own = schemaFiles.find((f) => (readJson(join(dir, f)) as { $id?: string }).$id === e.schema);
    if (!own) fail(`no schema file in registry/${name}/ has the $id ${e.schema} that the entry names`);
    if (!e.schema.includes(`/${e.version}/`)) fail(`its schema URL ${e.schema} is not versioned: it has a path segment /${e.version}/`);
    const suite = join(root, 'conformance', 'ext', name, e.version);
    const tests = testDirs(suite).length;
    if (tests === 0) fail(`a Draft has a conformance suite, conformance/ext/${name}/${e.version}/`);
    const holes = uncovered(root, name, suite);
    if (holes && holes.length) fail(`its suite does not cover ${holes.join(', ')}`);

    // Release Candidate: an implementation passing the suite, shown by evidence.
    const listed = e.implementations ?? [];
    const evidenced = new Map<string, Evidence>();
    for (const impl of listed) {
      const ev = evidence.find((x) => x.implementation.name === impl.name);
      if (!ev) {
        if (rank(e.status) >= rank('releaseCandidate')) fail(`${impl.name} is listed with no evidence in registry/${name}/evidence/`);
        continue;
      }
      if (ev.implementation.url !== impl.url) fail(`${ev.file} gives ${ev.implementation.url} for ${impl.name}, and the entry ${impl.url}`);
      if (ev.result.failed !== 0 || ev.result.passed !== ev.suite.tests) {
        fail(`${ev.file}: ${impl.name} passed ${ev.result.passed} of ${ev.suite.tests} tests, with ${ev.result.failed} failing - evidence is of a passing run`);
        continue;
      }
      const then = git.testsAt(ev.suite.commit, `conformance/ext/${name}/${e.version}`);
      if (then === null) report.warnings.push(at(`${ev.file}: cannot read commit ${ev.suite.commit.slice(0, 7)} (a shallow clone?), so its test count is not checked`));
      else if (then !== ev.suite.tests) {
        fail(`${ev.file}: the suite held ${then} tests at ${ev.suite.commit.slice(0, 7)}, and the evidence says ${ev.suite.tests}`);
        continue;
      }
      const stale = git.changedSince(ev.suite.commit, [`conformance/ext/${name}/${e.version}`]);
      if (stale) {
        const msg = `${ev.file}: the suite has changed since ${ev.suite.commit.slice(0, 7)}, the commit ${impl.name} passed - run it again and refresh the evidence`;
        if (e.status === 'ratified') {
          fail(msg);
          continue;
        }
        report.warnings.push(at(msg));
      }
      evidenced.set(impl.name, ev);
    }
    for (const ev of evidence)
      if (!listed.some((i) => i.name === ev.implementation.name))
        fail(`${ev.file} is evidence for ${ev.implementation.name}, which the entry does not list in implementations`);
    if (e.status === 'releaseCandidate') {
      const waived = exceptions.find((x) => x.extension === name && x.version === e.version && x.waives === 'releaseCandidate.implementation');
      if (evidenced.size === 0 && !waived) fail('a Release Candidate lists at least one implementation with evidence that it passes the suite');
      if (evidenced.size > 0 && waived) fail(`${[...evidenced.keys()].join(', ')} now passes with evidence: remove its exception from registry/exceptions.json`);
      if (waived) report.notes.push(at(`no implementation yet, by recorded exception: ${waived.decision} Until: ${waived.until}`));
    }

    // Ratified: two independent implementations, and frozen.
    if (e.status === 'ratified') {
      const evs = [...evidenced.values()];
      const independent = evs.some((a, i) =>
        evs.slice(i + 1).some((b) => a.maintainer !== b.maintainer && !a.sharesCodeWith.includes(b.implementation.name) && !b.sharesCodeWith.includes(a.implementation.name)),
      );
      if (!independent) fail('Ratified needs two implementations with current evidence, by different maintainers and sharing no code (FLR-REQ-092)');
      const c = ratifiedAt(git, name, e);
      if (c === null) report.warnings.push(at('not yet committed as Ratified: its schema, suite and entry freeze at the commit that ratifies it'));
      else {
        const frozen = [...schemaFiles.map((f) => `registry/${name}/${f}`), `conformance/ext/${name}/${e.version}`];
        if (git.changedSince(c, frozen)) fail(`its schema or suite changed after ${c.slice(0, 7)}, the commit that ratified it: a Ratified version is frozen, so publish a new version`);
        const then = git.show(c, `registry/${name}/extension.json`);
        if (then !== null && strip(JSON.parse(then) as Entry) !== strip(e)) fail(`its entry changed after ${c.slice(0, 7)} in a member other than implementations`);
      }
    }
    report.summary.push(`${name} ${e.version}: ${STATUS_NAME[e.status]}, ${tests} tests, ${evidenced.size} of ${listed.length} implementations with evidence`);
  }
  return report;
}

/** A pull request's changes to the registry, against its base's entries. */
export function checkTransitions(base: Map<string, Entry>, head: Map<string, Entry>, labels: string[]): Report {
  const report: Report = { errors: [], warnings: [], notes: [] };
  const override = labels.includes(MAINTAINER_LABEL);
  const refuse = (msg: string) => {
    if (override) report.notes.push(`${msg} - allowed by the ${MAINTAINER_LABEL} label`);
    else report.errors.push(`${msg}: a maintainer may allow it with the ${MAINTAINER_LABEL} label`);
  };
  for (const name of [...new Set([...base.keys(), ...head.keys()])].sort()) {
    const a = base.get(name);
    const b = head.get(name);
    if (a && !b) refuse(`${name} is removed from the registry - a name, once registered, stays reserved`);
    else if (!a && b) {
      if (rank(b.status) > rank('draft')) refuse(`${name} enters the registry as ${STATUS_NAME[b.status]}: a new extension enters as a Proposal or a Draft`);
      else report.notes.push(`${name} ${b.version} enters the registry as ${STATUS_NAME[b.status]}`);
    } else if (a && b) {
      const order = compareVersions(b.version, a.version);
      if (order < 0) refuse(`${name} goes back from ${a.version} to ${b.version}`);
      else if (order > 0) {
        if (rank(b.status) > rank('draft')) refuse(`${name} ${b.version} is a new version and enters as ${STATUS_NAME[b.status]}: a new version enters as a Proposal or a Draft`);
        else report.notes.push(`${name}: ${a.version} (${STATUS_NAME[a.status]}) is followed by ${b.version} (${STATUS_NAME[b.status]})`);
      } else {
        const step = rank(b.status) - rank(a.status);
        if (step < 0) refuse(`${name} ${b.version} goes back from ${STATUS_NAME[a.status]} to ${STATUS_NAME[b.status]}`);
        else if (step > 1) refuse(`${name} ${b.version} moves from ${STATUS_NAME[a.status]} to ${STATUS_NAME[b.status]}, more than one step`);
        else if (step === 1) report.notes.push(`${name} ${b.version}: ${STATUS_NAME[a.status]} → ${STATUS_NAME[b.status]}`);
      }
    }
  }
  return report;
}

export function entriesAt(git: Git, commit: string): Map<string, Entry> {
  const out = new Map<string, Entry>();
  for (const name of git.namesAt(commit)) {
    const text = git.show(commit, `registry/${name}/extension.json`);
    if (text !== null) out.set(name, JSON.parse(text) as Entry);
  }
  return out;
}

function main(argv: string[]) {
  const root = join(import.meta.dirname, '..');
  const arg = (flag: string) => {
    const i = argv.indexOf(flag);
    return i >= 0 ? argv[i + 1] : undefined;
  };
  const base = arg('--base') ?? process.env.REGISTRY_BASE ?? '';
  const labels = (arg('--labels') ?? process.env.REGISTRY_LABELS ?? '').split(',').map((s) => s.trim()).filter(Boolean);
  const git = gitOf(root);
  const r = checkEntries(root, git);
  for (const s of r.summary) console.log(`registry: ${s}`);
  const all: Report = { errors: [...r.errors], warnings: [...r.warnings], notes: [...r.notes] };
  if (base) {
    const t = checkTransitions(entriesAt(git, base), loadEntries(root).entries, labels);
    all.errors.push(...t.errors);
    all.warnings.push(...t.warnings);
    all.notes.push(...t.notes);
    if (git.namesAt(base).length === 0) all.warnings.push(`cannot read registry/ at ${base} (a shallow clone?): transitions not checked`);
  }
  for (const n of all.notes) console.log(`note: ${n}`);
  for (const w of all.warnings) console.warn(`warning: ${w}`);
  for (const e of all.errors) console.error(`error: ${e}`);
  if (all.errors.length) {
    console.error('registry gates failed');
    process.exit(1);
  }
  console.log(`registry gates passed${base ? ` (transitions since ${base.slice(0, 7)} checked)` : ''}`);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) main(process.argv.slice(2));

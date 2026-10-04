/**
 * Extracts every normative statement from the specifications and fails on any tagging problem
 * (FLR-T-1.1). Writes build/statements.json — the input to the coverage gate and to the spec
 * site's coverage page.
 *
 *   pnpm statements            # all specs that have chapters
 *   pnpm statements --list     # also print each mandatory statement
 */
import { existsSync, mkdirSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { extract, MANDATORY, type Statement } from './statements.ts';

const root = join(import.meta.dirname, '..');
const specs = (['core', 'ops', 'rules'] as const).filter((s) =>
  readdirSync(join(root, 'spec', s)).some((f) => f.endsWith('.md') && f !== 'README.md'),
);

const all: Statement[] = [];
let failed = false;
for (const spec of specs) {
  const { statements, problems } = extract(root, spec);
  for (const p of problems) console.error(`${p.file}:${p.line}: ${p.message}`);
  failed ||= problems.length > 0;
  all.push(...statements);
  const mandatory = statements.filter((s) => MANDATORY.includes(s.level)).length;
  console.log(`FS-${spec.toUpperCase()}: ${statements.length} statements, ${mandatory} mandatory`);
}

if (process.argv.includes('--list'))
  for (const s of all.filter((s) => MANDATORY.includes(s.level))) console.log(`  ${s.id} ${s.level}: ${s.text}`);

if (!existsSync(join(root, 'build'))) mkdirSync(join(root, 'build'));
writeFileSync(join(root, 'build', 'statements.json'), JSON.stringify(all, null, 2) + '\n');
if (failed) {
  console.error('statement extraction failed');
  process.exit(1);
}

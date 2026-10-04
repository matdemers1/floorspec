/**
 * Normative statements: how they are written, and how they are read back out.
 *
 * A normative statement is a sentence that uses an RFC 2119 / RFC 8174 keyword in capitals and
 * ends with a tag naming its stable ID and its level:
 *
 *     Readers MUST apply the default of an absent member. {#FS-CORE-1.4.2 MUST}
 *
 * The ID is `FS-<SPEC>-<chapter>.<section>.<n>`, and `<chapter>.<section>` must be the number of
 * the `##` heading the statement sits under. IDs are never reused, even when a statement is
 * deleted (FLR-ADR-009).
 *
 * The rules this module enforces, so that "every MUST has a test" cannot be dodged by an untagged
 * MUST:
 * - every block (paragraph, list item, table row) that uses a capitalised keyword carries a tag;
 * - every tag's level appears as a keyword in its block;
 * - informative callouts (`> [!note]`, `> [!example]` …) use no capitalised keywords at all;
 * - IDs are unique and match their section.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { join, relative } from 'node:path';

export const LEVELS = ['MUST NOT', 'MUST', 'SHOULD NOT', 'SHOULD', 'MAY'] as const;
export type Level = (typeof LEVELS)[number];

/** Levels a conformance test is required for (FLR-REQ-032). */
export const MANDATORY: readonly Level[] = ['MUST', 'MUST NOT'];

export interface Statement {
  id: string;
  level: Level;
  spec: string;
  section: string;
  heading: string;
  text: string;
  file: string;
  line: number;
}

export interface Problem {
  file: string;
  line: number;
  message: string;
}

const TAG = /\{#(FS-([A-Z]+)-(\d+)\.(\d+)\.(\d+)) (MUST NOT|MUST|SHOULD NOT|SHOULD|MAY)\}/g;
/** Capitalised keywords. SHALL, REQUIRED, RECOMMENDED and OPTIONAL are not used in Floorspec. */
const KEYWORD = /\b(MUST NOT|MUST|SHOULD NOT|SHOULD|MAY|SHALL NOT|SHALL|REQUIRED|RECOMMENDED|OPTIONAL)\b/g;
const BANNED = new Set(['SHALL', 'SHALL NOT', 'REQUIRED', 'RECOMMENDED', 'OPTIONAL']);
const HEADING = /^(#{1,6})\s+(.*)$/;
const SECTION = /^##\s+(\d+)\.(\d+)\s+(.*)$/;
const CHAPTER = /^#\s+(\d+)\.?\s+(.*)$/;

interface Block {
  /** The block with code spans blanked, for finding keywords. */
  text: string;
  /** The block as written, for the statement text. */
  raw: string;
  line: number;
  callout: boolean;
}

/** Splits Markdown into blocks, skipping fenced code. Inline code spans are blanked. */
function blocks(source: string): { heading: string; level: number; line: number; blocks: Block[] }[] {
  const lines = source.split('\n');
  const sections: { heading: string; level: number; line: number; blocks: Block[] }[] = [
    { heading: '', level: 0, line: 1, blocks: [] },
  ];
  let fenced = false;
  let current: Block | null = null;
  const flush = () => {
    if (current && current.text.trim()) sections[sections.length - 1]!.blocks.push(current);
    current = null;
  };
  lines.forEach((raw, i) => {
    const lineNo = i + 1;
    if (/^\s*(```|~~~)/.test(raw)) {
      flush();
      fenced = !fenced;
      return;
    }
    if (fenced) return;
    const h = HEADING.exec(raw);
    if (h) {
      flush();
      sections.push({ heading: raw, level: h[1]!.length, line: lineNo, blocks: [] });
      return;
    }
    const text = raw.replace(/`[^`]*`/g, '``');
    if (!text.trim()) {
      flush();
      return;
    }
    const callout = /^\s*>/.test(text);
    // A list item or a table row starts a new block; a callout continues while lines start with >.
    const startsItem = /^\s*([-*+]|\d+\.)\s/.test(text) || /^\s*\|/.test(text);
    if (current && (startsItem || current.callout !== callout)) flush();
    if (!current) current = { text: '', raw: '', line: lineNo, callout: callout && /\[!(note|example|info|tip)\]/i.test(text) };
    else if (callout && /\[!(note|example|info|tip)\]/i.test(text)) current.callout = true;
    current.text += (current.text ? ' ' : '') + text.trim();
    current.raw += (current.raw ? ' ' : '') + raw.trim();
  });
  flush();
  return sections;
}

export function parseFile(path: string, root: string, spec: string): { statements: Statement[]; problems: Problem[] } {
  const source = readFileSync(path, 'utf8');
  const file = relative(root, path);
  const statements: Statement[] = [];
  const problems: Problem[] = [];
  let chapter: string | null = null;
  let section: { number: string; heading: string } | null = null;

  for (const s of blocks(source)) {
    const c = CHAPTER.exec(s.heading);
    if (c) {
      chapter = c[1]!;
      section = null;
    }
    const m = SECTION.exec(s.heading);
    if (m) {
      section = { number: `${m[1]}.${m[2]}`, heading: m[3]!.trim() };
      if (chapter !== null && m[1] !== chapter)
        problems.push({ file, line: s.line, message: `section ${section.number} sits in chapter ${chapter}` });
    } else if (s.level === 2) {
      section = null;
    }

    for (const block of s.blocks) {
      const tags = [...block.text.matchAll(TAG)];
      const prose = block.text.replace(TAG, '');
      const keywords = [...prose.matchAll(KEYWORD)].map((k) => k[1]!);

      for (const k of keywords)
        if (BANNED.has(k))
          problems.push({ file, line: block.line, message: `"${k}" is not a Floorspec keyword; use MUST, MUST NOT, SHOULD, SHOULD NOT or MAY` });

      if (block.callout) {
        if (keywords.length || tags.length)
          problems.push({ file, line: block.line, message: 'an informative callout uses a normative keyword or tag' });
        continue;
      }
      if (keywords.length && !tags.length)
        problems.push({ file, line: block.line, message: `untagged normative keyword(s): ${keywords.join(', ')}` });

      const rawTags = [...block.raw.matchAll(TAG)];
      tags.forEach((t, n) => {
        const [, id, specCode, ch, sec, , level] = t;
        // The statement is the text from the previous tag (or the block's start) to this one.
        const end = rawTags[n]?.index ?? block.raw.length;
        const begin = n === 0 ? 0 : (rawTags[n - 1]!.index ?? 0) + rawTags[n - 1]![0].length;
        const sentence = block.raw.slice(begin, end);
        if (specCode !== spec) problems.push({ file, line: block.line, message: `${id} is not an FS-${spec} ID` });
        if (!section) {
          problems.push({ file, line: block.line, message: `${id} is not under a numbered "## n.n" section` });
          return;
        }
        if (`${ch}.${sec}` !== section.number)
          problems.push({ file, line: block.line, message: `${id} sits in section ${section.number}` });
        if (!keywords.includes(level!))
          problems.push({ file, line: block.line, message: `${id} is tagged ${level} but its text has no ${level}` });
        statements.push({
          id: id!,
          level: level as Level,
          spec: specCode!,
          section: section.number,
          heading: section.heading,
          text: sentence.replace(/^\s*[-*+]\s+/, '').replace(/\s+/g, ' ').trim(),
          file,
          line: block.line,
        });
      });
    }
  }
  return { statements, problems };
}

/** Every statement of one specification (`core` → FS-CORE), in file and line order. */
export function extract(root: string, spec: 'core' | 'ops' | 'rules'): { statements: Statement[]; problems: Problem[] } {
  const dir = join(root, 'spec', spec);
  const files = readdirSync(dir)
    .filter((f) => f.endsWith('.md') && f !== 'README.md')
    .sort();
  const statements: Statement[] = [];
  const problems: Problem[] = [];
  for (const f of files) {
    const r = parseFile(join(dir, f), root, spec.toUpperCase());
    statements.push(...r.statements);
    problems.push(...r.problems);
  }
  const seen = new Map<string, Statement>();
  for (const s of statements) {
    const prior = seen.get(s.id);
    if (prior) problems.push({ file: s.file, line: s.line, message: `${s.id} is already used at ${prior.file}:${prior.line}` });
    else seen.set(s.id, s);
  }
  return { statements, problems };
}

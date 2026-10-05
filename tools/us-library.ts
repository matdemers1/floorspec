/**
 * The US starter type library (FLR-T-10.4, FLR-REQ-139, Core 0.3 8.1): common US wall, door and window
 * types and the materials their layers use, as Core 0.3 types and materials ready to embed in a
 * document (FLR-REQ-169), published by URI, one immutable directory per version.
 *
 *   library/us-starter/<version>/index.json          every item: its ID, kind, name, URI, a summary of its
 *                                                     sizes, the element exactly as it is embedded,
 *                                                     and the Ops batch that embeds it
 *   library/us-starter/<version>/items/<item>.json   one item, at its own URI
 *   library/us-starter/<version>/README.md           the human-readable catalogue
 *   library/us-starter/<version>/SHA256SUMS          the digest of every file above
 *
 *   pnpm library:us          writes the current version
 *   pnpm library:us:check    fails if the current version differs from what this script writes, or if
 *                            any file of any version differs from its SHA256SUMS
 *
 * Published at https://d3cloud.io/floorspec/library/us-starter/<version>/<path>. A published version
 * never changes: a change to the table below is a new version, in a new directory.
 *
 * Everything is a pure function of the tables below: the same tables give the same bytes. Sizes are
 * written in inches and fractions of an inch, and every length is an exact integer number of base
 * units (1/1280 mm; one inch is 32,512 of them, Core 2.1). The library states generic sizes and
 * generic clear openings: no manufacturer's data, and no building-code text or table.
 */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { pathToFileURL } from 'node:url';

export const IN = 32512;                       // one inch in base units (25.4 mm x 1280)
export const LIBRARY = 'https://d3cloud.io/floorspec/library/us-starter';
export const VERSION = '0.1.0';
export const VERSION_URI = `${LIBRARY}/${VERSION}/`;
export const LIBRARY_ROOT = join(import.meta.dirname, '..', 'library', 'us-starter');
export const VERSION_DIR = join(LIBRARY_ROOT, VERSION);

/** A length of `whole` inches and `num`/`den` of an inch, in base units; it must be exact. */
export function inches(whole: number, num = 0, den = 1): number {
  const v = whole * IN * den + num * IN;
  if (!Number.isInteger(whole) || !Number.isInteger(num) || v % den !== 0) throw new Error(`${whole} ${num}/${den} in is not a whole number of base units`);
  return v / den;
}
const ft = (feet: number, inch = 0) => inches(feet * 12 + inch);

/** "3 1/2 in" for a length in base units (to a sixty-fourth of an inch). */
export function inchText(v: number): string {
  const s64 = v / (IN / 64);
  if (!Number.isInteger(s64)) throw new Error(`${v} is not a whole number of sixty-fourths of an inch`);
  const whole = Math.floor(s64 / 64);
  let num = s64 % 64, den = 64;
  while (num && num % 2 === 0) { num /= 2; den /= 2; }
  return `${whole ? whole : ''}${whole && num ? ' ' : ''}${num ? `${num}/${den}` : whole ? '' : '0'} in`;
}

// ------------------------------------------------------------------------------------- materials

interface MaterialItem { id: string; name: string; color: string; roughness: number; note: string }

/** Materials: a plausible linear colour and roughness each, no texture, never metallic. */
export const MATERIALS: MaterialItem[] = [
  { id: 'gypsum-board', name: 'Gypsum board, painted', color: '#efede8', roughness: 900, note: 'interior finish' },
  { id: 'wood-stud-framing', name: 'Wood stud framing', color: '#c8a46e', roughness: 850, note: 'studs at regular spacing, cavities empty' },
  { id: 'wood-stud-framing-insulated', name: 'Wood stud framing, insulated cavities', color: '#dcc28c', roughness: 900, note: 'studs with insulation filling the cavities between them' },
  { id: 'osb-sheathing', name: 'OSB sheathing', color: '#c09a5b', roughness: 900, note: 'oriented strand board' },
  { id: 'weather-resistive-barrier', name: 'Weather-resistive barrier', color: '#e9edf0', roughness: 600, note: 'a house wrap or building paper' },
  { id: 'fibre-cement-siding', name: 'Fibre-cement lap siding, painted', color: '#8f9aa1', roughness: 750, note: 'exterior cladding' },
  { id: 'rigid-foam-insulation', name: 'Rigid foam insulation board', color: '#cfdbe3', roughness: 700, note: 'continuous insulation outside the sheathing' },
  { id: 'brick-veneer', name: 'Brick veneer', color: '#9a4b34', roughness: 950, note: 'a single wythe of brick tied to the frame behind it' },
  { id: 'concrete-masonry-unit', name: 'Concrete masonry units', color: '#a6a49e', roughness: 950, note: 'hollow concrete block (CMU)' },
  { id: 'cast-in-place-concrete', name: 'Cast-in-place concrete', color: '#aaa9a3', roughness: 900, note: 'poured concrete' },
];

// ------------------------------------------------------------------------------------- walls

type LayerFunction = 'core' | 'substrate' | 'insulation' | 'membrane' | 'airGap' | 'finish';
interface Layer { thickness: number; function: LayerFunction; material?: string; what: string }

const gyp = (t = inches(0, 1, 2)): Layer => ({ thickness: t, function: 'finish', material: 'gypsum-board', what: `${inchText(t)} gypsum board` });
const studs = (nominal: '2x4' | '2x6', insulated: boolean): Layer => {
  const t = nominal === '2x4' ? inches(3, 1, 2) : inches(5, 1, 2);
  return { thickness: t, function: 'core', material: insulated ? 'wood-stud-framing-insulated' : 'wood-stud-framing',
    what: `${nominal} studs (${inchText(t)} deep)${insulated ? ', insulated cavities' : ''}` };
};
const osb: Layer = { thickness: inches(0, 7, 16), function: 'substrate', material: 'osb-sheathing', what: '7/16 in OSB sheathing' };
const wrb: Layer = { thickness: inches(0, 1, 64), function: 'membrane', material: 'weather-resistive-barrier', what: 'weather-resistive barrier, 1/64 in' };
const siding: Layer = { thickness: inches(0, 5, 16), function: 'finish', material: 'fibre-cement-siding', what: '5/16 in fibre-cement lap siding' };
const foam: Layer = { thickness: inches(1), function: 'insulation', material: 'rigid-foam-insulation', what: '1 in rigid foam board' };
const brick: Layer = { thickness: inches(3, 5, 8), function: 'finish', material: 'brick-veneer', what: 'brick veneer (3 5/8 in actual)' };
const gap = (t: number, what: string): Layer => ({ thickness: t, function: 'airGap', what });
const cmu: Layer = { thickness: inches(7, 5, 8), function: 'core', material: 'concrete-masonry-unit', what: '8 in nominal CMU (7 5/8 in actual)' };
const concrete = (t: number): Layer => ({ thickness: t, function: 'core', material: 'cast-in-place-concrete', what: `${inchText(t)} cast-in-place concrete` });

interface WallItem { id: string; name: string; layers: Layer[] }

/** Wall types, their layers from the left (exterior) face to the right (interior) face (Core 8.3). */
export const WALLS: WallItem[] = [
  { id: 'wall-2x4-interior', name: '2x4 interior partition, gypsum both faces', layers: [gyp(), studs('2x4', false), gyp()] },
  { id: 'wall-2x6-interior', name: '2x6 interior partition, gypsum both faces', layers: [gyp(), studs('2x6', false), gyp()] },
  { id: 'wall-2x4-exterior-fibre-cement', name: '2x4 exterior wall, fibre-cement siding', layers: [siding, wrb, osb, studs('2x4', true), gyp()] },
  { id: 'wall-2x6-exterior-fibre-cement', name: '2x6 exterior wall, fibre-cement siding', layers: [siding, wrb, osb, studs('2x6', true), gyp()] },
  { id: 'wall-2x6-exterior-fibre-cement-ci', name: '2x6 exterior wall, fibre-cement siding over continuous insulation', layers: [siding, wrb, foam, osb, studs('2x6', true), gyp()] },
  { id: 'wall-2x4-exterior-brick-veneer', name: '2x4 exterior wall, brick veneer', layers: [brick, gap(inches(1), '1 in air space'), wrb, osb, studs('2x4', true), gyp()] },
  { id: 'wall-2x6-exterior-brick-veneer', name: '2x6 exterior wall, brick veneer', layers: [brick, gap(inches(1), '1 in air space'), wrb, osb, studs('2x6', true), gyp()] },
  { id: 'wall-cmu-8', name: '8 in CMU wall, exposed both faces', layers: [cmu] },
  { id: 'wall-cmu-8-furred', name: '8 in CMU wall, furred and finished with gypsum inside', layers: [cmu, gap(inches(0, 3, 4), '3/4 in furring space'), gyp()] },
  { id: 'wall-concrete-foundation-8', name: '8 in cast-in-place concrete foundation wall', layers: [concrete(inches(8))] },
  { id: 'wall-concrete-foundation-10', name: '10 in cast-in-place concrete foundation wall', layers: [concrete(inches(10))] },
];

// ------------------------------------------------------------------------------------- doors

type DoorOperation = 'swing' | 'doubleSwing' | 'pocket' | 'bifold' | 'bypassSlide' | 'overhead';
interface DoorItem {
  id: string; name: string; operation: DoorOperation;
  unit: [number, number];        // the door's nominal size: slab (or pair, or panel set) width and height
  rough: [number, number];       // the rough opening: the type's width and height
  clear: [number, number];       // the generic clear opening
  swingDepth?: number;           // how far forward of the opening its leaves sweep
  exterior?: boolean;
}

// Generic conventions of this library (README): a door's rough opening is its unit 2 in wider and
// 2 1/2 in taller; a garage door's opening is its door's size. The clear-opening deductions are
// the library's own generic values, never a manufacturer's.
function door(id: string, name: string, operation: DoorOperation, w: number, h: number, extra: Partial<DoorItem> = {}): DoorItem {
  const garage = operation === 'overhead';
  const rough: [number, number] = garage ? [w, h] : [w + inches(2), h + inches(2, 1, 2)];
  const exterior = extra.exterior ?? false;
  let clear: [number, number];
  let swingDepth: number | undefined;
  switch (operation) {
    case 'swing':
      clear = exterior ? [w - inches(2, 1, 4), h - inches(1)] : [w - inches(2), h];
      swingDepth = w;
      break;
    case 'doubleSwing': clear = [w - inches(4), h]; swingDepth = w / 2; break;
    case 'pocket': clear = [w - inches(1, 1, 2), h]; break;
    case 'bifold': clear = [w - inches(4), h]; swingDepth = w / 2; break;
    case 'bypassSlide': clear = [w / 2 - inches(1), h]; break;
    case 'overhead': clear = [w - inches(1, 1, 2), h - inches(2)]; break;
  }
  return { id, name, operation, unit: [w, h], rough, clear, swingDepth, ...extra };
}

export const DOORS: DoorItem[] = [
  ...[24, 28, 30, 32, 36].map((w) => door(`door-interior-swing-${w}x80`, `Interior swing door, ${w} x 80 in`, 'swing', inches(w), inches(80))),
  door('door-exterior-swing-36x80', 'Exterior swing door, 36 x 80 in', 'swing', inches(36), inches(80), { exterior: true }),
  door('door-pocket-30x80', 'Pocket door, 30 x 80 in', 'pocket', inches(30), inches(80)),
  door('door-bifold-30x80', 'Bifold door, two panels, 30 x 80 in', 'bifold', inches(30), inches(80)),
  door('door-bifold-36x80', 'Bifold door, two panels, 36 x 80 in', 'bifold', inches(36), inches(80)),
  door('door-bypass-48x80', 'Bypass sliding doors, two leaves, 48 x 80 in', 'bypassSlide', inches(48), inches(80)),
  door('door-bypass-60x80', 'Bypass sliding doors, two leaves, 60 x 80 in', 'bypassSlide', inches(60), inches(80)),
  door('door-double-swing-60x80', 'Double swing doors, a pair, 60 x 80 in', 'doubleSwing', inches(60), inches(80)),
  door('door-double-swing-72x80', 'Double swing doors, a pair, 72 x 80 in', 'doubleSwing', inches(72), inches(80)),
  door('door-garage-overhead-9x7', 'Overhead garage door, 9 x 7 ft', 'overhead', ft(9), ft(7)),
  door('door-garage-overhead-16x7', 'Overhead garage door, 16 x 7 ft', 'overhead', ft(16), ft(7)),
];

// ------------------------------------------------------------------------------------- windows

type WindowOperation = 'singleHung' | 'doubleHung' | 'casement' | 'horizontalSlider' | 'fixed' | 'awning';
interface WindowItem {
  id: string; name: string; operation: WindowOperation;
  unit: [number, number]; rough: [number, number]; sill: number; clear?: [number, number];
}

const HEAD = inches(82, 1, 2);   // the head of every window's rough opening, level with a door's

const WINDOW_NAMES: Record<WindowOperation, [string, string]> = {
  singleHung: ['single-hung', 'Single-hung window'], doubleHung: ['double-hung', 'Double-hung window'],
  casement: ['casement', 'Casement window'], horizontalSlider: ['slider', 'Horizontal sliding window'],
  fixed: ['fixed', 'Fixed window'], awning: ['awning', 'Awning window'],
};

// Generic conventions (README): the rough opening is the unit 1/2 in wider and taller, its head at
// 82 1/2 in; the clear opening is the library's generic deduction for the operation.
function win(operation: WindowOperation, wIn: number, hIn: number): WindowItem {
  const w = inches(wIn), h = inches(hIn);
  const rough: [number, number] = [w + inches(0, 1, 2), h + inches(0, 1, 2)];
  let clear: [number, number] | undefined;
  switch (operation) {
    case 'singleHung': case 'doubleHung': clear = [w - inches(4), h / 2 - inches(3)]; break;
    case 'horizontalSlider': clear = [w / 2 - inches(3), h - inches(4)]; break;
    case 'casement': clear = [w - inches(6), h - inches(4)]; break;
    case 'awning': clear = [w - inches(4), h / 2 - inches(2)]; break;
    case 'fixed': clear = undefined; break;
  }
  const [slug, label] = WINDOW_NAMES[operation];
  return { id: `window-${slug}-${wIn}x${hIn}`, name: `${label}, ${wIn} x ${hIn} in`, operation, unit: [w, h], rough, sill: HEAD - rough[1], clear };
}

export const WINDOWS: WindowItem[] = [
  ...([[24, 36], [30, 48], [36, 48], [36, 60]] as const).map(([w, h]) => win('singleHung', w, h)),
  ...([[24, 36], [30, 48], [36, 48], [36, 60], [36, 72]] as const).map(([w, h]) => win('doubleHung', w, h)),
  ...([[24, 36], [24, 48], [30, 48], [30, 60]] as const).map(([w, h]) => win('casement', w, h)),
  ...([[36, 24], [48, 36], [60, 36], [60, 48], [72, 48]] as const).map(([w, h]) => win('horizontalSlider', w, h)),
  ...([[24, 48], [36, 36], [48, 48], [72, 48]] as const).map(([w, h]) => win('fixed', w, h)),
  ...([[24, 24], [36, 24], [48, 24]] as const).map(([w, h]) => win('awning', w, h)),
];

// ------------------------------------------------------------------------------------- the elements

export type Kind = 'wallType' | 'doorType' | 'windowType' | 'material';
type Obj = Record<string, unknown>;
export interface Entry {
  kind: Kind;
  name: string;
  uri: string;
  collection: 'types' | 'materials';
  materials: string[];
  summary: Record<string, string>;
  element: Obj;
  embed: Obj[];
}

const source = (item: string) => ({ library: LIBRARY, version: VERSION, item });

function materialElement(m: MaterialItem): Obj {
  return { color: m.color, name: m.name, roughness: m.roughness, source: source(m.id) };
}

function wallElement(w: WallItem): Obj {
  return {
    kind: 'wallType',
    layers: w.layers.map((l) => (l.material ? { function: l.function, material: l.material, thickness: l.thickness } : { function: l.function, thickness: l.thickness })),
    name: w.name,
    source: source(w.id),
  };
}

function doorElement(d: DoorItem): Obj {
  const [rw, rh] = d.rough;
  const el: Obj = { kind: 'doorType', name: d.name, operation: d.operation, width: rw, height: rh, clearOpening: { width: d.clear[0], height: d.clear[1] } };
  if (d.swingDepth !== undefined) {
    const half = rw / 2;
    el.clearances = { swing: { purpose: 'swing', shape: 'box', min: [0, -half, 0], max: [d.swingDepth, half, rh] } };
  }
  el.source = source(d.id);
  return el;
}

function windowElement(w: WindowItem): Obj {
  const el: Obj = { kind: 'windowType', name: w.name, operation: w.operation, width: w.rough[0], height: w.rough[1], sill: w.sill };
  if (w.clear) el.clearOpening = { width: w.clear[0], height: w.clear[1], area: w.clear[0] * w.clear[1] };
  el.source = source(w.id);
  return el;
}

/** A value with every object's members in sorted order, as the canonical form writes them (Core 9.2). */
function sorted(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(sorted);
  if (v === null || typeof v !== 'object') return v;
  return Object.fromEntries(Object.keys(v).sort().map((k) => [k, sorted((v as Obj)[k])]));
}

const sizeText = ([w, h]: [number, number]) => `${inchText(w)} x ${inchText(h)}`;

/** Every item of the library, by ID, in the order of the tables. */
export function entries(): Map<string, Entry> {
  const out = new Map<string, Entry>();
  const uri = (id: string) => `${VERSION_URI}items/${id}.json`;
  for (const m of MATERIALS)
    out.set(m.id, { kind: 'material', name: m.name, uri: uri(m.id), collection: 'materials', materials: [], summary: { description: m.note }, element: materialElement(m), embed: [] });
  for (const w of WALLS) {
    const total = w.layers.reduce((s, l) => s + l.thickness, 0);
    const mats = [...new Set(w.layers.flatMap((l) => (l.material ? [l.material] : [])))];
    out.set(w.id, { kind: 'wallType', name: w.name, uri: uri(w.id), collection: 'types', materials: mats,
      summary: { layers: w.layers.map((l) => l.what).join('; '), thickness: inchText(total) }, element: wallElement(w), embed: [] });
  }
  for (const d of DOORS)
    out.set(d.id, { kind: 'doorType', name: d.name, uri: uri(d.id), collection: 'types', materials: [],
      summary: { unit: sizeText(d.unit), roughOpening: sizeText(d.rough), clearOpening: `${sizeText(d.clear)} (generic)` }, element: doorElement(d), embed: [] });
  for (const w of WINDOWS)
    out.set(w.id, { kind: 'windowType', name: w.name, uri: uri(w.id), collection: 'types', materials: [],
      summary: { unit: sizeText(w.unit), roughOpening: sizeText(w.rough), sill: inchText(w.sill), clearOpening: w.clear ? `${sizeText(w.clear)} (generic)` : 'none: a fixed window does not open' },
      element: windowElement(w), embed: [] });
  for (const e of out.values()) e.element = sorted(e.element) as Obj;
  for (const [id, e] of out) e.embed = embedBatch(out, id);
  return out;
}

/** The Ops batch that embeds an item into a document that has none of its elements, under the
 *  library's own IDs: its materials first, then the item (Ops 2.1 addElement). */
function embedBatch(all: Map<string, Entry>, id: string): Obj[] {
  const e = all.get(id)!;
  return [...e.materials.map((m) => ({ op: 'addElement', collection: 'materials', id: m, element: all.get(m)!.element })),
    { op: 'addElement', collection: e.collection, id, element: e.element }];
}

// ------------------------------------------------------------------------------------- embedding

const same = (a: unknown, b: unknown): boolean => {
  if (a === b) return true;
  if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null || Array.isArray(a) !== Array.isArray(b)) return false;
  const ka = Object.keys(a), kb = Object.keys(b);
  return ka.length === kb.length && ka.every((k) => same((a as Obj)[k], (b as Obj)[k]));
};

export class EmbedConflict extends Error {}

/**
 * The operations that embed `item` in `doc` (FLR-REQ-169): an addElement for each of its materials
 * and for the item itself that the document does not already hold. An element already there under
 * the same ID with the same content is left alone, so embedding twice adds nothing; one there with
 * different content is a conflict, which `ids` resolves by embedding under other IDs (library ID →
 * document ID), the layers' material references following them.
 */
export function embed(doc: Obj, item: string, ids: Record<string, string> = {}, all = entries()): Obj[] {
  const e = all.get(item);
  if (!e) throw new Error(`no item "${item}" in ${LIBRARY} ${VERSION}`);
  const to = (id: string) => ids[id] ?? id;
  const ops: Obj[] = [];
  const want: [string, string, Obj][] = e.materials.map((m) => ['materials', m, all.get(m)!.element]);
  let element = e.element;
  if (e.kind === 'wallType')
    element = { ...element, layers: (element.layers as Obj[]).map((l) => (l.material ? { ...l, material: to(l.material as string) } : l)) };
  want.push([e.collection, item, element]);
  for (const [collection, id, el] of want) {
    const existing = ((doc[collection] ?? {}) as Obj)[to(id)];
    if (existing === undefined) ops.push({ op: 'addElement', collection, id: to(id), element: el });
    else if (!same(existing, el)) throw new EmbedConflict(`"${to(id)}" in ${collection} is not ${item === id ? 'the item' : `its material ${id}`}: embed it under another ID`);
  }
  return ops;
}

// ------------------------------------------------------------------------------------- the files

const json = (v: unknown) => `${JSON.stringify(v, null, 2)}\n`;
const sha256 = (b: Buffer | string) => createHash('sha256').update(b).digest('hex');

export const CLEAR_OPENINGS_NOTE = 'generic, replace with your product\'s declared values: every clearOpening in this library is the '
  + 'library\'s own generic deduction from the nominal size for the operation (README), not a manufacturer\'s declared value; '
  + 'Core 8.4 makes a clear opening the value a product\'s maker declares, so a project replaces it with its product\'s, '
  + 'on the type or on the opening (Core 7.2), before relying on it.';

function header(): Obj {
  return {
    name: 'Floorspec US starter type library',
    library: LIBRARY,
    version: VERSION,
    uri: VERSION_URI,
    floorspec: '0.3',
    status: 'non-normative',
    license: 'CC0-1.0',
    licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
    description: 'Common US wall, door and window types and the materials their layers use, as Floorspec Core 0.3 types and '
      + 'materials ready to embed: a document copies each one it uses into its own types and materials collections, with its '
      + 'source, and never refers to the library by URL (Core 8.1). Lengths are integers in base units of 1/1280 mm '
      + '(one inch is 32,512). Generic values only: no manufacturer\'s data, no building-code text or table. Written by '
      + 'tools/us-library.ts; a published version never changes.',
    clearOpenings: CLEAR_OPENINGS_NOTE,
  };
}

function readme(all: Map<string, Entry>): string {
  const rows = (kind: Kind, cols: [string, (e: Entry, id: string) => string][]) => {
    const list = [...all].filter(([, e]) => e.kind === kind);
    return [`| ${cols.map((c) => c[0]).join(' | ')} |`, `|${cols.map(() => '---').join('|')}|`,
      ...list.map(([id, e]) => `| ${cols.map((c) => c[1](e, id)).join(' | ')} |`)].join('\n');
  };
  const count = (k: Kind) => [...all.values()].filter((e) => e.kind === k).length;
  return `# Floorspec US starter type library ${VERSION}

Common US wall, door and window types, and the materials their layers use, as Floorspec Core 0.3
types and materials ready to embed in a document. **Non-normative**: nothing in Floorspec requires
these items, and a document that uses one is exactly as valid as one that defines its own.

- Library: \`${LIBRARY}\`
- This version: \`${VERSION_URI}\` — published once, never changed; a change is a new version
- Index: \`${VERSION_URI}index.json\`; each item at \`${VERSION_URI}items/<item>.json\`
- Digests: \`SHA256SUMS\` beside this file
- License: CC0 1.0 — dedicated to the public domain

${count('wallType')} wall types, ${count('doorType')} door types, ${count('windowType')} window types and ${count('material')} materials.

## Embedding an item

A document embeds every type it uses (Core 8.1): it copies the item's \`element\` into its \`types\`
or \`materials\` collection, and each of a wall type's materials into \`materials\`, and never refers
to the library by URL. Each copy keeps its \`source\` — \`library\`, \`version\` and \`item\` — which
records where it came from and is never read by derivation.

Each item in \`index.json\` carries \`embed\`, the Floorspec Ops batch that embeds it into a document
that has none of its elements, under the library's own IDs:

\`\`\`json
{ "batch": [
  { "op": "addElement", "collection": "materials", "id": "gypsum-board", "element": { … } },
  { "op": "addElement", "collection": "materials", "id": "wood-stud-framing", "element": { … } },
  { "op": "addElement", "collection": "types", "id": "wall-2x4-interior", "element": { … } }
] }
\`\`\`

- **Already embedded.** Leave out every \`addElement\` whose ID the document already holds with
  identical content: embedding an item twice adds nothing. (\`addElement\` of a used ID fails the
  batch, Ops 2.1.)
- **A different element under the same ID.** Embed under other IDs, and point the wall type's
  layers at the materials' new IDs. An element's ID is the document's choice; \`source.item\` is
  what names the library item.
- **A newer version.** Never automatic. To move an embedded type to a later version of this
  library, read that version's item and \`setProperty\` each member that differs — the layers, the
  sizes, \`/source/version\` — in one batch, so the document says which version it now follows.
- **Edited after embedding.** Allowed: the copy is the document's own. Keep \`source\` to say where
  it started, or \`unsetProperty\` it.

\`tools/us-library.ts\` exports \`embed(document, item, ids)\`, which computes exactly these
operations.

## Conventions

- **Units.** Every length is an integer number of base units, 1/1280 mm: one inch is 32,512, so
  every size here to a sixty-fourth of an inch is exact. Sizes are stated in inches below.
- **Lumber.** Sizes are nominal; actual sizes are smaller: a nominal 2x4 is 1 1/2 in x 3 1/2 in and a
  2x6 is 1 1/2 in x 5 1/2 in, so a stud layer is 3 1/2 in or 5 1/2 in thick. A nominal 8 in concrete
  masonry unit is 7 5/8 in thick.
- **Layers** run from the wall's left (exterior) face to its right (interior) face (Core 8.3). A thin
  membrane is given 1/64 in, because a layer's thickness is greater than zero.
- **Doors.** A door type's \`width\` and \`height\` are its rough opening — the hole in the wall
  (Core 7.1) — taken generically as the door unit 2 in wider and 2 1/2 in taller; a garage door's
  opening is the door's own size. A pocket door's opening is its passage: its pocket, inside the
  wall beside it, needs about another door's width of wall free of other openings. A swinging door,
  a pair and a bifold carry a \`swing\` clearance envelope (Core 13.5) as deep as their leaves
  sweep.
- **Windows.** Unit sizes are width x height in inches. A window type's \`width\` and \`height\` are
  its rough opening, the unit 1/2 in wider and taller, and its \`sill\` puts the head of the rough
  opening at 82 1/2 in, level with a door's. An opening overrides the sill where it differs.
- **Clear openings: generic, replace with your product's declared values.** Core makes a clear
  opening the value its product's maker declares, never a computed one (8.4). These are the
  library's own generic deductions from the nominal size, stated once here so that they are
  plausible and consistent — not any manufacturer's figures:
  - interior swing door: 2 in less than the door's width, its full height; exterior swing door:
    2 1/4 in less wide and 1 in less high; a pair: 4 in less than the pair's width; pocket door:
    1 1/2 in less wide; two-panel bifold: 4 in less wide; bypass doors: 1 in less than half the
    width; overhead garage door: 1 1/2 in less wide and 2 in less high;
  - single- and double-hung: 4 in less than the unit's width, and 3 in less than half its height;
    horizontal slider: 3 in less than half the width, 4 in less than the height; casement: 6 in less
    wide, 4 in less high; awning: 4 in less wide, 2 in less than half the height; and the clear area
    of every window is the clear width times the clear height. A fixed window does not open and has
    no clear opening.

  A project replaces them with its product's declared values, on the type or on the opening (Core
  7.2), before a check relies on them.

## Wall types

${rows('wallType', [['Item', (_, id) => `\`${id}\``], ['Name', (e) => e.name], ['Layers, exterior to interior', (e) => e.summary.layers!], ['Thickness', (e) => e.summary.thickness!]])}

## Door types

${rows('doorType', [['Item', (_, id) => `\`${id}\``], ['Operation', (e) => `\`${e.element.operation}\``], ['Unit', (e) => e.summary.unit!], ['Rough opening', (e) => e.summary.roughOpening!], ['Clear opening', (e) => e.summary.clearOpening!]])}

## Window types

${rows('windowType', [['Item', (_, id) => `\`${id}\``], ['Operation', (e) => `\`${e.element.operation}\``], ['Unit', (e) => e.summary.unit!], ['Rough opening', (e) => e.summary.roughOpening!], ['Sill', (e) => e.summary.sill!], ['Clear opening', (e) => e.summary.clearOpening!]])}

## Materials

${rows('material', [['Item', (_, id) => `\`${id}\``], ['Name', (e) => e.name], ['Colour', (e) => `\`${e.element.color}\``], ['Roughness', (e) => `${e.element.roughness}`], ['What it is', (e) => e.summary.description!]])}

Colours are plausible sRGB base colours and roughness is in thousandths (Core 18.1); no material
has a texture.
`;
}

/** Every file of the current version, by path relative to its directory. */
export function build(): Map<string, Buffer> {
  const all = entries();
  const files = new Map<string, Buffer>();
  const items: Obj = {};
  for (const [id, e] of all) {
    items[id] = e;
    files.set(`items/${id}.json`, Buffer.from(json({ ...header(), item: id, ...e }), 'utf8'));
  }
  files.set('index.json', Buffer.from(json({ ...header(), items }), 'utf8'));
  files.set('README.md', Buffer.from(readme(all), 'utf8'));
  const sums = [...files].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)).map(([p, b]) => `${sha256(b)}  ${p}\n`).join('');
  files.set('SHA256SUMS', Buffer.from(sums, 'utf8'));
  return files;
}

/** Every file under a directory, by path relative to it with / separators. */
export function listFiles(dir: string): string[] {
  const out: string[] = [];
  const walk = (d: string) => {
    for (const name of readdirSync(d)) {
      const full = join(d, name);
      if (statSync(full).isDirectory()) walk(full);
      else out.push(relative(dir, full).split(sep).join('/'));
    }
  };
  walk(dir);
  return out.sort();
}

/** Problems with a published version directory: a file not in its SHA256SUMS, or not matching it. */
export function verifyVersion(dir: string): string[] {
  const sumsPath = join(dir, 'SHA256SUMS');
  if (!existsSync(sumsPath)) return [`${dir}: no SHA256SUMS`];
  const want = new Map(readFileSync(sumsPath, 'utf8').split('\n').filter(Boolean).map((l) => {
    const [digest, path] = l.split('  ');
    return [path!, digest!] as const;
  }));
  const problems: string[] = [];
  const have = listFiles(dir).filter((p) => p !== 'SHA256SUMS');
  for (const p of have) {
    if (!want.has(p)) problems.push(`${p}: not in SHA256SUMS`);
    else if (sha256(readFileSync(join(dir, p))) !== want.get(p)) problems.push(`${p}: differs from SHA256SUMS`);
  }
  for (const p of want.keys()) if (!have.includes(p)) problems.push(`${p}: missing`);
  return problems.map((p) => `${relative(LIBRARY_ROOT, dir)}/${p}`);
}

function main(argv: string[]): number {
  const check = argv.includes('--check');
  const files = build();
  const problems: string[] = [];
  if (check) {
    for (const [path, bytes] of files) {
      const full = join(VERSION_DIR, path);
      if (!existsSync(full) || !readFileSync(full).equals(bytes)) problems.push(`${VERSION}/${path}: differs from what tools/us-library.ts writes`);
    }
    if (existsSync(VERSION_DIR))
      for (const p of listFiles(VERSION_DIR)) if (!files.has(p)) problems.push(`${VERSION}/${p}: not written by tools/us-library.ts`);
    for (const v of readdirSync(LIBRARY_ROOT).filter((n) => statSync(join(LIBRARY_ROOT, n)).isDirectory()))
      problems.push(...verifyVersion(join(LIBRARY_ROOT, v)));
  } else {
    for (const [path, bytes] of files) {
      const full = join(VERSION_DIR, path);
      mkdirSync(dirname(full), { recursive: true });
      writeFileSync(full, bytes);
    }
  }
  if (problems.length) {
    console.error(`the US starter library is not as published:\n  ${problems.join('\n  ')}`);
    return 1;
  }
  const n = files.size - 3;
  console.log(`US starter library ${VERSION}: ${n} items ${check ? 'checked' : 'written'}`);
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) process.exit(main(process.argv.slice(2)));

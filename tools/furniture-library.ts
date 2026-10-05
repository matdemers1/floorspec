/**
 * The FS_furniture starter library (FLR-T-8.3, registry/FS_furniture/spec.md chapter 7): twenty-five
 * generic furniture, appliance and casework items, each an FS_furniture element ready to place - its
 * category, fallback box and Floorspec's default clearance envelopes - with a glTF 2.0 proxy model and
 * an SVG plan symbol generated here from a few boxes, and the SHA-256 digest and length of each file.
 *
 *   registry/FS_furniture/library/library.json        the catalogue (written, never edited by hand)
 *   registry/FS_furniture/library/models/<item>.glb    each item's model (model/gltf-binary)
 *   registry/FS_furniture/library/symbols/<item>.svg   each item's plan symbol (image/svg+xml)
 *
 *   pnpm library            writes them
 *   pnpm library:check      fails if any of them differs from what it would write
 *
 * Everything is a pure function of the ITEMS table below: the same table gives the same bytes. No
 * third-party asset is used; the library is dedicated to the public domain under CC0 1.0.
 *
 * Conventions (spec.md chapter 3, Core 0.3 12.6): an item's frame has its origin at the middle of its
 * back at its bottom, forward (+x) the side it is used from, +y to its left and +z up. A fallback model
 * maps the local point (p, q, r) to the glTF point (p, r, -q) / 1,280,000 - Core 2.3's mapping applied to
 * the frame (Core 12.6), so the model's front faces glTF +X - and a fallback symbol is the box's
 * footprint seen from above with the item's front along the image's bottom edge (Core 12.6).
 */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';

export const MM = 1280;
export const LIBRARY_DIR = join(import.meta.dirname, '..', 'registry', 'FS_furniture', 'library');

export type Kind = 'pieces' | 'appliances' | 'casework';
export type Purpose = 'workingSpace' | 'fixtureClearance' | 'swing' | 'access';
/** A box in millimetres in an item's frame: [x0, y0, z0, x1, y1, z1]. */
export type MmBox = [number, number, number, number, number, number];

/** The default envelopes of spec.md 4.2, by category: name, purpose, form and distance in mm. */
type Form = 'front' | 'frontTall' | 'sides' | 'around';
const DEFAULTS: Record<string, [string[], Purpose, Form, number]> = {
  sofa: [['front'], 'access', 'frontTall', 600],
  armchair: [['front'], 'access', 'frontTall', 600],
  diningTable: [['around'], 'access', 'around', 750],
  desk: [['front'], 'access', 'frontTall', 750],
  bed: [['left', 'right'], 'access', 'sides', 600],
  dresser: [['front'], 'swing', 'front', 500],
  wardrobe: [['front'], 'swing', 'front', 600],
  sideboard: [['front'], 'swing', 'front', 500],
  refrigerator: [['door'], 'swing', 'front', 900],
  freezer: [['door'], 'swing', 'front', 900],
  range: [['door'], 'swing', 'front', 600],
  wallOven: [['door'], 'swing', 'front', 600],
  dishwasher: [['door'], 'swing', 'front', 700],
  washer: [['door'], 'swing', 'front', 700],
  dryer: [['door'], 'swing', 'front', 700],
  baseCabinet: [['front'], 'swing', 'front', 600],
  tallCabinet: [['front'], 'swing', 'front', 600],
  wallCabinet: [['front'], 'swing', 'front', 400],
  island: [['front'], 'workingSpace', 'frontTall', 1000],
  vanity: [['front'], 'swing', 'front', 500],
};

/** How an item of a category is mounted (spec.md 2.4): every category not listed stands on the floor. */
export function mounting(category: string): 'floor' | 'wall' | 'builtIn' {
  if (['shelf', 'wallCabinet', 'shelving'].includes(category)) return 'wall';
  if (['wallOven', 'cooktop', 'microwave'].includes(category)) return 'builtIn';
  return 'floor';
}

export interface Box { min: [number, number, number]; max: [number, number, number] }
export interface Envelope { purpose: Purpose; shape: 'box'; min: [number, number, number]; max: [number, number, number] }

/** The box of spec.md 3.1, in base units: its back on x = 0, centred on y = 0, its bottom on z = 0. */
export function conventionalBox(width: number, depth: number, height: number): Box {
  const half = Math.floor(width / 2);
  return { min: [0, -half, 0], max: [depth, width - half, height] };
}

/** Floorspec's default envelopes for a category (spec.md 4.2), in base units, for a box. */
export function defaultEnvelopes(category: string, box: Box): Record<string, Envelope> {
  const d = DEFAULTS[category];
  if (!d) return {};
  const [names, purpose, form, mm] = d;
  const D = mm * MM;
  const [x0, y0, z0] = box.min;
  const [x1, y1, z1] = box.max;
  const top = Math.max(z1, z0 + 2000 * MM);
  const env = (min: [number, number, number], max: [number, number, number]): Envelope => ({ purpose, shape: 'box', min, max });
  switch (form) {
    case 'front': return { [names[0]!]: env([x1, y0, z0], [x1 + D, y1, z1]) };
    case 'frontTall': return { [names[0]!]: env([x1, y0, z0], [x1 + D, y1, top]) };
    case 'around': return { [names[0]!]: env([x0 - D, y0 - D, z0], [x1 + D, y1 + D, top]) };
    case 'sides': return { [names[0]!]: env([x0, y1, z0], [x1, y1 + D, top]), [names[1]!]: env([x0, y0 - D, z0], [x1, y0, top]) };
  }
}

interface Item {
  id: string;
  kind: Kind;
  category: string;
  name: string;
  width: number;   // mm, along y
  depth: number;   // mm, along x
  height: number;  // mm, along z
  seats?: number;
  parts: MmBox[];
  marks?: Mark[];
}

/** Extra plan marks of a symbol, in mm of the item's frame. */
type Mark = { circle: [number, number, number] } | { line: [number, number, number, number] };

const legs = (d: number, w: number, h: number, t = 50): MmBox[] => {
  const y = w / 2;
  return [[0, -y, 0, t, -y + t, h], [d - t, -y, 0, d, -y + t, h], [0, y - t, 0, t, y, h], [d - t, y - t, 0, d, y, h]];
};
const table = (d: number, w: number, h: number, top = 40): MmBox[] => [[0, -w / 2, h - top, d, w / 2, h], ...legs(d, w, h - top)];
const body = (d: number, w: number, h: number): MmBox[] => [[0, -w / 2, 0, d, w / 2, h]];
const doorLine = (d: number, w: number, inset = 30): Mark => ({ line: [d - inset, -w / 2, d - inset, w / 2] });
const seat = (d: number, w: number, h: number, back: number, arm: number): MmBox[] => {
  const y = w / 2;
  const out: MmBox[] = [[0, -y, 0, d, y, 450], [0, -y, 450, back, y, h]];
  if (arm > 0) out.push([back, -y, 450, d, -y + arm, 650], [back, y - arm, 450, d, y, 650]);
  return out;
};
const cabinet = (d: number, w: number, h: number): MmBox[] =>
  [[0, -w / 2, 0, d - 80, w / 2, 100], [0, -w / 2, 100, d - 20, w / 2, h - 30], [0, -w / 2, h - 30, d, w / 2, h]];

/** The starter items. Dimensions are whole millimetres, so every box is centred exactly. */
export const ITEMS: Item[] = [
  // ---------------------------------------------------------------- appliances
  { id: 'refrigerator-900', kind: 'appliances', category: 'refrigerator', name: 'Refrigerator, 900 mm', width: 900, depth: 700, height: 1780,
    parts: [[0, -450, 0, 680, 450, 1780], [680, 330, 900, 700, 350, 1500]], marks: [doorLine(700, 900, 20)] },
  { id: 'freezer-600', kind: 'appliances', category: 'freezer', name: 'Upright freezer, 600 mm', width: 600, depth: 650, height: 1700,
    parts: [[0, -300, 0, 630, 300, 1700], [630, 200, 800, 650, 220, 1400]], marks: [doorLine(650, 600, 20)] },
  { id: 'range-760', kind: 'appliances', category: 'range', name: 'Range, 760 mm', width: 760, depth: 650, height: 920,
    parts: [[0, -380, 0, 650, 380, 900], [0, -380, 900, 60, 380, 920]],
    marks: [{ circle: [230, -190, 90] }, { circle: [230, 190, 90] }, { circle: [480, -190, 90] }, { circle: [480, 190, 90] }] },
  { id: 'wall-oven-760', kind: 'appliances', category: 'wallOven', name: 'Wall oven, 760 mm', width: 760, depth: 600, height: 720,
    parts: body(600, 760, 720), marks: [doorLine(600, 760)] },
  { id: 'cooktop-760', kind: 'appliances', category: 'cooktop', name: 'Cooktop, 760 mm', width: 760, depth: 520, height: 60,
    parts: body(520, 760, 60),
    marks: [{ circle: [140, -190, 90] }, { circle: [140, 190, 90] }, { circle: [380, -190, 90] }, { circle: [380, 190, 90] }] },
  { id: 'microwave-600', kind: 'appliances', category: 'microwave', name: 'Microwave, 600 mm', width: 600, depth: 400, height: 350,
    parts: body(400, 600, 350), marks: [doorLine(400, 600)] },
  { id: 'dishwasher-600', kind: 'appliances', category: 'dishwasher', name: 'Dishwasher, 600 mm', width: 600, depth: 600, height: 850,
    parts: body(600, 600, 850), marks: [{ line: [0, -300, 600, 300] }, { line: [0, 300, 600, -300] }] },
  { id: 'washer-690', kind: 'appliances', category: 'washer', name: 'Front-loading washer, 690 mm', width: 690, depth: 650, height: 850,
    parts: body(650, 690, 850), marks: [{ circle: [325, 0, 250] }] },
  { id: 'dryer-690', kind: 'appliances', category: 'dryer', name: 'Dryer, 690 mm', width: 690, depth: 650, height: 850,
    parts: body(650, 690, 850), marks: [{ circle: [325, 0, 250] }, { circle: [325, 0, 120] }] },
  // ---------------------------------------------------------------- pieces
  { id: 'sofa-2100', kind: 'pieces', category: 'sofa', name: 'Three-seat sofa', width: 2100, depth: 900, height: 850, seats: 3,
    parts: seat(900, 2100, 850, 200, 150) },
  { id: 'armchair-850', kind: 'pieces', category: 'armchair', name: 'Armchair', width: 850, depth: 850, height: 850, seats: 1,
    parts: seat(850, 850, 850, 200, 150) },
  { id: 'dining-table-1500', kind: 'pieces', category: 'diningTable', name: 'Dining table, 1500 x 900 mm', width: 1500, depth: 900, height: 750, seats: 6,
    parts: table(900, 1500, 750) },
  { id: 'dining-chair-450', kind: 'pieces', category: 'chair', name: 'Dining chair', width: 450, depth: 500, height: 850, seats: 1,
    parts: [[0, -225, 420, 500, 225, 460], [0, -225, 460, 50, 225, 850], ...legs(500, 450, 420, 40)] },
  { id: 'coffee-table-1200', kind: 'pieces', category: 'coffeeTable', name: 'Coffee table', width: 1200, depth: 600, height: 450,
    parts: table(600, 1200, 450) },
  { id: 'bed-queen-1600', kind: 'pieces', category: 'bed', name: 'Queen bed, 1600 x 2050 mm', width: 1600, depth: 2050, height: 1000,
    parts: [[0, -800, 0, 2050, 800, 550], [0, -800, 550, 80, 800, 1000], [120, -750, 550, 520, -50, 650], [120, 50, 550, 520, 750, 650]],
    marks: [{ line: [700, -800, 700, 800] }] },
  { id: 'nightstand-500', kind: 'pieces', category: 'nightstand', name: 'Nightstand', width: 500, depth: 450, height: 600,
    parts: body(450, 500, 600), marks: [doorLine(450, 500)] },
  { id: 'dresser-1200', kind: 'pieces', category: 'dresser', name: 'Dresser', width: 1200, depth: 500, height: 800,
    parts: body(500, 1200, 800), marks: [doorLine(500, 1200)] },
  { id: 'wardrobe-1000', kind: 'pieces', category: 'wardrobe', name: 'Wardrobe', width: 1000, depth: 600, height: 2100,
    parts: body(600, 1000, 2100), marks: [doorLine(600, 1000), { line: [570, 0, 600, 0] }] },
  { id: 'desk-1200', kind: 'pieces', category: 'desk', name: 'Desk', width: 1200, depth: 600, height: 750, seats: 1,
    parts: [[0, -600, 720, 600, 600, 750], [0, -600, 0, 600, -570, 720], [0, 570, 0, 600, 600, 720]] },
  { id: 'bookcase-900', kind: 'pieces', category: 'bookcase', name: 'Bookcase', width: 900, depth: 350, height: 1800,
    parts: body(350, 900, 1800) },
  // ---------------------------------------------------------------- casework
  { id: 'base-cabinet-600', kind: 'casework', category: 'baseCabinet', name: 'Base cabinet with counter, 600 mm', width: 600, depth: 600, height: 900,
    parts: cabinet(600, 600, 900), marks: [doorLine(600, 600, 20)] },
  { id: 'wall-cabinet-600', kind: 'casework', category: 'wallCabinet', name: 'Wall cabinet, 600 mm', width: 600, depth: 350, height: 750,
    parts: body(350, 600, 750), marks: [doorLine(350, 600, 20)] },
  { id: 'tall-cabinet-600', kind: 'casework', category: 'tallCabinet', name: 'Tall pantry cabinet, 600 mm', width: 600, depth: 600, height: 2100,
    parts: [[0, -300, 0, 520, 300, 100], [0, -300, 100, 600, 300, 2100]], marks: [doorLine(600, 600, 20)] },
  { id: 'island-1800', kind: 'casework', category: 'island', name: 'Kitchen island, 1800 x 900 mm', width: 1800, depth: 900, height: 900,
    parts: [[30, -870, 0, 870, 870, 870], [0, -900, 870, 900, 900, 900]] },
  { id: 'vanity-900', kind: 'casework', category: 'vanity', name: 'Vanity cabinet, 900 mm', width: 900, depth: 550, height: 850,
    parts: cabinet(550, 900, 850), marks: [doorLine(550, 900, 20)] },
];

/** The linear base colour of each kind's material. */
const COLOUR: Record<Kind, [number, number, number]> = {
  appliances: [0.8, 0.8, 0.82], pieces: [0.45, 0.3, 0.18], casework: [0.86, 0.84, 0.78],
};

// ------------------------------------------------------------------------------------- glTF

const f32 = (v: number) => { const x = Math.fround(v); return x === 0 ? 0 : x; };

/** One part's six faces in glTF coordinates (metres), each counter-clockwise seen from outside. */
function boxFaces([x0, y0, z0, x1, y1, z1]: MmBox): { corners: number[][]; normal: number[] }[] {
  // local (p, q, r) mm -> glTF (p, r, -q) m
  const X = [x0 / 1000, x1 / 1000], Y = [z0 / 1000, z1 / 1000], Z = [-y1 / 1000, -y0 / 1000];
  const faces: { corners: number[][]; normal: number[] }[] = [];
  for (const axis of [0, 1, 2])
    for (const side of [0, 1]) {
      const normal = [0, 0, 0];
      normal[axis] = side ? 1 : -1;
      const [u, v] = [(axis + 1) % 3, (axis + 2) % 3];
      const range = [X, Y, Z];
      let corners = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([a, b]) => {
        const p = [0, 0, 0];
        p[axis] = range[axis]![side]!;
        p[u] = range[u]![a!]!;
        p[v] = range[v]![b!]!;
        return p;
      });
      const e1 = corners[1]!.map((c, i) => c - corners[0]![i]!), e2 = corners[2]!.map((c, i) => c - corners[0]![i]!);
      const cross = [e1[1]! * e2[2]! - e1[2]! * e2[1]!, e1[2]! * e2[0]! - e1[0]! * e2[2]!, e1[0]! * e2[1]! - e1[1]! * e2[0]!];
      if (cross[axis]! * normal[axis]! < 0) corners = corners.reverse();
      faces.push({ corners, normal });
    }
  return faces;
}

const pad = (b: Buffer, fill: number) => (b.length % 4 ? Buffer.concat([b, Buffer.alloc(4 - (b.length % 4), fill)]) : b);

/** A binary glTF 2.0 file of an item's parts: one mesh, one primitive, one material. */
export function glb(item: Item): Buffer {
  const pos: number[] = [], nor: number[] = [], idx: number[] = [];
  for (const part of item.parts)
    for (const face of boxFaces(part)) {
      const base = pos.length / 3;
      for (const c of face.corners) { pos.push(...c.map(f32)); nor.push(...face.normal.map(f32)); }
      idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
  const count = pos.length / 3;
  const min = [0, 1, 2].map((k) => Math.min(...pos.filter((_, i) => i % 3 === k)));
  const max = [0, 1, 2].map((k) => Math.max(...pos.filter((_, i) => i % 3 === k)));
  const posBuf = Buffer.from(new Float32Array(pos).buffer);
  const norBuf = Buffer.from(new Float32Array(nor).buffer);
  const idxBuf = pad(Buffer.from(new Uint16Array(idx).buffer), 0);
  const bin = Buffer.concat([posBuf, norBuf, idxBuf]);
  const json = {
    asset: { version: '2.0', generator: 'Floorspec FS_furniture starter library', copyright: 'CC0-1.0' },
    scene: 0,
    scenes: [{ nodes: [0] }],
    nodes: [{ mesh: 0, name: item.id }],
    meshes: [{ name: item.id, primitives: [{ attributes: { POSITION: 0, NORMAL: 1 }, indices: 2, material: 0 }] }],
    materials: [{ name: item.kind, pbrMetallicRoughness: { baseColorFactor: [...COLOUR[item.kind], 1], metallicFactor: 0, roughnessFactor: 1 } }],
    accessors: [
      { bufferView: 0, componentType: 5126, count, type: 'VEC3', min, max },
      { bufferView: 1, componentType: 5126, count, type: 'VEC3' },
      { bufferView: 2, componentType: 5123, count: idx.length, type: 'SCALAR' },
    ],
    bufferViews: [
      { buffer: 0, byteOffset: 0, byteLength: posBuf.length, target: 34962 },
      { buffer: 0, byteOffset: posBuf.length, byteLength: norBuf.length, target: 34962 },
      { buffer: 0, byteOffset: posBuf.length + norBuf.length, byteLength: idx.length * 2, target: 34963 },
    ],
    buffers: [{ byteLength: bin.length }],
  };
  const jsonBuf = pad(Buffer.from(JSON.stringify(json), 'utf8'), 0x20);
  const header = Buffer.alloc(12);
  header.writeUInt32LE(0x46546c67, 0);                 // 'glTF'
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(12 + 8 + jsonBuf.length + 8 + bin.length, 8);
  const chunk = (data: Buffer, type: number) => {
    const h = Buffer.alloc(8);
    h.writeUInt32LE(data.length, 0);
    h.writeUInt32LE(type, 4);
    return Buffer.concat([h, data]);
  };
  return Buffer.concat([header, chunk(jsonBuf, 0x4e4f534a), chunk(bin, 0x004e4942)]);
}

// ------------------------------------------------------------------------------------- SVG

/** The plan symbol: the footprint seen from above, the item's front along the bottom edge. A local
 *  point (x, y) in mm is the image point (y + width / 2, x): right is the item's left, down its front. */
export function svg(item: Item): string {
  const w = item.width, d = item.depth;
  const u = (y: number) => y + w / 2;
  const n = (v: number) => String(Math.round(v * 10) / 10);
  const wall = item.category === 'wallCabinet' || item.category === 'shelf' || item.category === 'shelving';
  const lines: string[] = [];
  const stroke = wall ? ' stroke-dasharray="40 20"' : '';
  lines.push(`<rect x="5" y="5" width="${n(w - 10)}" height="${n(d - 10)}" fill="#ffffff" stroke="#000000" stroke-width="10"${stroke}/>`);
  for (const [x0, y0, , x1, y1] of item.parts) {
    if (x0 === 0 && x1 === d && y0 === -w / 2 && y1 === w / 2) continue;      // the outline itself
    lines.push(`<rect x="${n(u(y0))}" y="${n(x0)}" width="${n(y1 - y0)}" height="${n(x1 - x0)}" fill="none" stroke="#000000" stroke-width="5"/>`);
  }
  for (const m of item.marks ?? []) {
    if ('circle' in m) lines.push(`<circle cx="${n(u(m.circle[1]))}" cy="${n(m.circle[0])}" r="${n(m.circle[2])}" fill="none" stroke="#000000" stroke-width="5"/>`);
    else lines.push(`<line x1="${n(u(m.line[1]))}" y1="${n(m.line[0])}" x2="${n(u(m.line[3]))}" y2="${n(m.line[2])}" stroke="#000000" stroke-width="5"/>`);
  }
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${d}" width="${w}mm" height="${d}mm">`,
    `<title>${item.name} (FS_furniture ${item.category}; CC0-1.0)</title>`,
    ...lines,
    '</svg>',
    '',
  ].join('\n');
}

// ------------------------------------------------------------------------------------- the catalogue

const sha256 = (b: Buffer | string) => createHash('sha256').update(b).digest('hex');

/** Every file of the library, by path relative to its directory. */
export function build(): Map<string, Buffer> {
  const files = new Map<string, Buffer>();
  const items: Record<string, unknown> = {};
  for (const it of ITEMS) {
    const model = glb(it), symbol = Buffer.from(svg(it), 'utf8');
    const box = conventionalBox(it.width * MM, it.depth * MM, it.height * MM);
    const clearances = defaultEnvelopes(it.category, box);
    const element: Record<string, unknown> = { category: it.category, catalogue: it.id, name: it.name };
    if (it.seats !== undefined) element.seats = it.seats;
    if (Object.keys(clearances).length) element.clearances = clearances;
    element.fallback = { box };
    const mp = `models/${it.id}.glb`, sp = `symbols/${it.id}.svg`;
    files.set(mp, model);
    files.set(sp, symbol);
    items[it.id] = {
      kind: it.kind,
      mounting: mounting(it.category),
      element,
      model: { path: mp, mediaType: 'model/gltf-binary', sha256: sha256(model), byteLength: model.length },
      symbol: { path: sp, mediaType: 'image/svg+xml', sha256: sha256(symbol), byteLength: symbol.length },
    };
  }
  const catalogue = {
    library: 'FS_furniture starter library',
    extension: 'FS_furniture',
    version: '0.1.0',
    license: 'CC0-1.0',
    licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
    description: 'Generic furniture, appliances and casework as FS_furniture 0.1.0 elements ready to place: '
      + 'lengths in base units (1/1280 mm), each item\'s box and default clearance envelopes in its frame (spec.md 3.1, 4.2), '
      + 'and a generated proxy model and plan symbol with their SHA-256 digests and lengths. Written by tools/furniture-library.ts.',
    items,
  };
  files.set('library.json', Buffer.from(`${JSON.stringify(catalogue, null, 2)}\n`, 'utf8'));
  return files;
}

function main(argv: string[]): number {
  const check = argv.includes('--check');
  const differ: string[] = [];
  for (const [path, bytes] of build()) {
    const full = join(LIBRARY_DIR, path);
    if (check) {
      if (!existsSync(full) || !readFileSync(full).equals(bytes)) differ.push(path);
    } else {
      mkdirSync(dirname(full), { recursive: true });
      writeFileSync(full, bytes);
    }
  }
  if (check && differ.length) {
    console.error(`the FS_furniture library differs from what tools/furniture-library.ts writes:\n  ${differ.join('\n  ')}`);
    return 1;
  }
  console.log(`FS_furniture library: ${ITEMS.length} items ${check ? 'checked' : 'written'}`);
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) process.exit(main(process.argv.slice(2)));

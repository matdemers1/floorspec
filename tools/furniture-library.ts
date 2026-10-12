/**
 * The FS_furniture starter library (FLR-T-8.3, registry/FS_furniture/spec.md chapter 7): twenty-five
 * generic furniture, appliance and casework items, and since 0.2.0 (FLR-T-13.11) thirty decor items -
 * rugs, wall art and a mirror, lamps, plants, cushions and throws, curtains and a blind, a media
 * console and a television, books and kitchen and bath accessories - each an FS_furniture element ready to place - its
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
  /** Decor (FLR-T-13.11): a flat or hung item whose symbol is drawn unfilled — a rug, a curtain — so what stands on or in front of it stays seen; and its proxy's colour. */
  decor?: { colour: [number, number, number]; outline?: 'dashed' };
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
const FURNITURE_ITEMS: Item[] = [
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

// ---------------------------------------------------------------- decor (FLR-T-13.11)
// Rugs, wall art, lamps, plants, textiles, window dressings, media, books and kitchen and bath
// accessories: the things that stage a furnished room. Each is a piece of category `other` (2.5)
// — no category of FS_furniture 0.1 names them — except the media console, a `mediaUnit`. A
// reader that knows the library draws each as what it is; any other draws its box, model and symbol.

/** A flat rectangle of rug: its field inset from a border band. */
const rug = (d: number, w: number, h: number): MmBox[] => [[0, -w / 2, 0, d, w / 2, h - 2], [80, -w / 2 + 80, h - 2, d - 80, w / 2 - 80, h]];
/** A framed picture hung on a wall: its frame, and the canvas set back in it. */
const framed = (d: number, w: number, h: number): MmBox[] => [[0, -w / 2, 0, d, w / 2, h], [d - 10, -w / 2 + 60, 60, d, w / 2 - 60, h - 60]];
/** A drum shade on a stem over a base. */
const lamp = (w: number, h: number, base: number, shade: number): MmBox[] => [
  [w / 2 - base / 2, -base / 2, 0, w / 2 + base / 2, base / 2, h * 0.08],
  [w / 2 - 15, -15, h * 0.08, w / 2 + 15, 15, h - shade * 0.6],
  [0, -w / 2, h - shade, w, w / 2, h],
];
/** A planter and the foliage over it. */
const potted = (w: number, h: number, pot: number, potH: number): MmBox[] => [
  [w / 2 - pot / 2, -pot / 2, 0, w / 2 + pot / 2, pot / 2, potH],
  [0, -w / 2, potH, w, w / 2, h],
];
const ring = (d: number, w: number, r: number): Mark => ({ circle: [d / 2, 0, Math.min(r, d / 2, w / 2)] });

const DECOR_ITEMS: Item[] = [
  // Rugs: a field and a border, flat on the floor; the front is the side a seating group faces from.
  { id: 'rug-3000x2000', kind: 'pieces', category: 'other', name: 'Rug, 3000 x 2000 mm', width: 3000, depth: 2000, height: 12,
    parts: rug(2000, 3000, 12), decor: { colour: [0.55, 0.47, 0.38], outline: 'dashed' } },
  { id: 'rug-2400x1700', kind: 'pieces', category: 'other', name: 'Rug, 2400 x 1700 mm', width: 2400, depth: 1700, height: 12,
    parts: rug(1700, 2400, 12), decor: { colour: [0.55, 0.47, 0.38], outline: 'dashed' } },
  { id: 'rug-2000x1400', kind: 'pieces', category: 'other', name: 'Rug, 2000 x 1400 mm', width: 2000, depth: 1400, height: 12,
    parts: rug(1400, 2000, 12), decor: { colour: [0.55, 0.47, 0.38], outline: 'dashed' } },
  { id: 'runner-2400x800', kind: 'pieces', category: 'other', name: 'Runner, 2400 x 800 mm', width: 2400, depth: 800, height: 10,
    parts: rug(800, 2400, 10), decor: { colour: [0.55, 0.47, 0.38], outline: 'dashed' } },
  { id: 'bath-mat-800x500', kind: 'pieces', category: 'other', name: 'Bath mat', width: 800, depth: 500, height: 15,
    parts: rug(500, 800, 15), decor: { colour: [0.85, 0.83, 0.78], outline: 'dashed' } },
  // Wall art and a mirror: hung on a wall face, their backs against it.
  { id: 'art-1200x800', kind: 'pieces', category: 'other', name: 'Framed art, 1200 x 800 mm', width: 1200, depth: 40, height: 800,
    parts: framed(40, 1200, 800), decor: { colour: [0.62, 0.58, 0.52] } },
  { id: 'art-600x800', kind: 'pieces', category: 'other', name: 'Framed art, 600 x 800 mm', width: 600, depth: 40, height: 800,
    parts: framed(40, 600, 800), decor: { colour: [0.62, 0.58, 0.52] } },
  { id: 'art-500x500', kind: 'pieces', category: 'other', name: 'Framed art, 500 x 500 mm', width: 500, depth: 35, height: 500,
    parts: framed(35, 500, 500), decor: { colour: [0.62, 0.58, 0.52] } },
  { id: 'mirror-800x1000', kind: 'pieces', category: 'other', name: 'Wall mirror, 800 x 1000 mm', width: 800, depth: 30, height: 1000,
    parts: framed(30, 800, 1000), decor: { colour: [0.75, 0.78, 0.8] } },
  // Lamps.
  { id: 'lamp-floor-1600', kind: 'pieces', category: 'other', name: 'Floor lamp', width: 450, depth: 450, height: 1600,
    parts: lamp(450, 1600, 300, 380), marks: [ring(450, 450, 225), ring(450, 450, 60)], decor: { colour: [0.9, 0.86, 0.76] } },
  { id: 'lamp-table-600', kind: 'pieces', category: 'other', name: 'Table lamp', width: 360, depth: 360, height: 600,
    parts: lamp(360, 600, 160, 250), marks: [ring(360, 360, 180), ring(360, 360, 50)], decor: { colour: [0.9, 0.86, 0.76] } },
  // Plants in planters.
  { id: 'plant-tree-1700', kind: 'pieces', category: 'other', name: 'Indoor tree in a planter', width: 750, depth: 750, height: 1700,
    parts: potted(750, 1700, 420, 400), marks: [ring(750, 750, 375), ring(750, 750, 210)], decor: { colour: [0.3, 0.42, 0.28] } },
  { id: 'plant-floor-900', kind: 'pieces', category: 'other', name: 'Floor plant in a planter', width: 550, depth: 550, height: 900,
    parts: potted(550, 900, 340, 340), marks: [ring(550, 550, 275), ring(550, 550, 170)], decor: { colour: [0.3, 0.42, 0.28] } },
  { id: 'plant-small-350', kind: 'pieces', category: 'other', name: 'Potted plant, small', width: 220, depth: 220, height: 350,
    parts: potted(220, 350, 140, 130), marks: [ring(220, 220, 110)], decor: { colour: [0.3, 0.42, 0.28] } },
  // Textiles.
  { id: 'cushion-450', kind: 'pieces', category: 'other', name: 'Cushion, 450 mm', width: 450, depth: 150, height: 450,
    parts: [[0, -225, 0, 150, 225, 450]], decor: { colour: [0.72, 0.6, 0.45] } },
  // A throw over a sofa's right arm: down the arm's outside (its own right, -y), over the arm and onto the seat (+y).
  { id: 'throw-sofa', kind: 'pieces', category: 'other', name: 'Throw over a sofa arm', width: 420, depth: 520, height: 240,
    parts: [[0, -210, 0, 520, -192, 240], [0, -192, 222, 520, 26, 240], [0, 26, 0, 520, 210, 222]], decor: { colour: [0.72, 0.6, 0.45] } },
  // A throw across the foot of a queen bed, over its sides.
  { id: 'throw-bed-1640', kind: 'pieces', category: 'other', name: 'Bed throw, 1640 mm', width: 1640, depth: 600, height: 320,
    parts: [[0, -820, 300, 600, 820, 320], [0, -820, 0, 600, -800, 300], [0, 800, 0, 600, 820, 300]], decor: { colour: [0.72, 0.6, 0.45], outline: 'dashed' } },
  // Window dressings: hung on the wall face over a window, sized to it.
  { id: 'curtains-2000', kind: 'pieces', category: 'other', name: 'Curtains on a rod, 2000 mm', width: 2000, depth: 140, height: 2400,
    parts: [[0, -990, 2330, 140, -950, 2400], [0, 950, 2330, 140, 990, 2400], [90, -1000, 2340, 120, 1000, 2370], [20, -1000, 0, 140, -680, 2340], [20, 680, 0, 140, 1000, 2340]], decor: { colour: [0.9, 0.88, 0.83], outline: 'dashed' } },
  { id: 'blind-roman-900', kind: 'pieces', category: 'other', name: 'Roman blind, 900 mm', width: 900, depth: 60, height: 500,
    parts: [[0, -450, 440, 60, 450, 500], [0, -450, 0, 50, 450, 440]], decor: { colour: [0.9, 0.88, 0.83], outline: 'dashed' } },
  // Media.
  { id: 'media-console-1800', kind: 'pieces', category: 'mediaUnit', name: 'Media console, 1800 mm', width: 1800, depth: 450, height: 500,
    parts: [[0, -900, 80, 450, 900, 500], [20, -880, 0, 400, 880, 80]], marks: [doorLine(450, 1800)] },
  { id: 'tv-65', kind: 'pieces', category: 'other', name: 'Television, 65 in, on its stand', width: 1450, depth: 280, height: 900,
    parts: [[120, -725, 60, 160, 725, 900], [0, -300, 0, 280, 300, 20], [125, -30, 20, 155, 30, 60]], decor: { colour: [0.08, 0.08, 0.09] } },
  // Books and accessories set on tables, consoles and counters.
  { id: 'books-stack', kind: 'pieces', category: 'other', name: 'Books, a stack of three', width: 280, depth: 210, height: 95,
    parts: [[0, -140, 0, 210, 140, 35], [10, -130, 35, 200, 125, 65], [20, -120, 65, 190, 115, 95]], decor: { colour: [0.5, 0.4, 0.32] } },
  { id: 'vase-stems-450', kind: 'pieces', category: 'other', name: 'Vase with stems', width: 260, depth: 260, height: 520,
    parts: [[60, -70, 0, 200, 70, 260], [0, -130, 260, 260, 130, 520]], marks: [ring(260, 260, 70)], decor: { colour: [0.86, 0.84, 0.8] } },
  { id: 'bowl-fruit-320', kind: 'pieces', category: 'other', name: 'Fruit bowl', width: 320, depth: 320, height: 150,
    parts: [[0, -160, 0, 320, 160, 150]], marks: [ring(320, 320, 160), ring(320, 320, 90)], decor: { colour: [0.86, 0.84, 0.8] } },
  { id: 'cutting-board-450', kind: 'pieces', category: 'other', name: 'Cutting board, leaning', width: 450, depth: 70, height: 340,
    parts: [[0, -225, 0, 70, 225, 340]], decor: { colour: [0.62, 0.45, 0.3] } },
  { id: 'kettle', kind: 'pieces', category: 'other', name: 'Kettle', width: 240, depth: 200, height: 260,
    parts: [[0, -100, 0, 200, 100, 220], [80, -120, 160, 120, 120, 260]], marks: [ring(200, 240, 95)], decor: { colour: [0.75, 0.76, 0.78] } },
  { id: 'canisters-3', kind: 'pieces', category: 'other', name: 'Canisters, three', width: 400, depth: 130, height: 240,
    parts: [[0, -200, 0, 130, -70, 240], [0, -65, 0, 130, 65, 200], [0, 70, 0, 130, 200, 160]], decor: { colour: [0.86, 0.84, 0.8] } },
  // Bath.
  { id: 'towel-bar-600', kind: 'pieces', category: 'other', name: 'Towel bar with towel', width: 600, depth: 90, height: 480,
    parts: [[0, -300, 440, 90, 300, 470], [20, -240, 0, 80, 240, 480]], decor: { colour: [0.9, 0.88, 0.83] } },
  { id: 'towels-folded', kind: 'pieces', category: 'other', name: 'Towels, folded', width: 320, depth: 240, height: 170,
    parts: [[0, -160, 0, 240, 160, 170]], decor: { colour: [0.9, 0.88, 0.83] } },
  { id: 'soap-set', kind: 'pieces', category: 'other', name: 'Soap dispenser and tumbler', width: 220, depth: 130, height: 190,
    parts: [[0, -110, 0, 130, 110, 12], [25, -90, 12, 105, -10, 190], [30, 20, 12, 100, 90, 110]], decor: { colour: [0.86, 0.84, 0.8] } },
];

/** Every item: the furniture, appliances and casework of 0.1.0, then the decor of 0.2.0. */
export const ITEMS: Item[] = [...FURNITURE_ITEMS, ...DECOR_ITEMS];

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
    materials: [{ name: item.kind, pbrMetallicRoughness: { baseColorFactor: [...(item.decor?.colour ?? COLOUR[item.kind]), 1], metallicFactor: 0, roughnessFactor: 1 } }],
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
  const stroke = wall || item.decor?.outline === 'dashed' ? ' stroke-dasharray="40 20"' : '';
  // Decor is drawn unfilled: a rug under a sofa, curtains before a window, art on a wall leave what is under or behind them seen.
  const fill = item.decor === undefined ? '#ffffff' : 'none';
  lines.push(`<rect x="5" y="5" width="${n(w - 10)}" height="${n(d - 10)}" fill="${fill}" stroke="#000000" stroke-width="10"${stroke}/>`);
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
    version: '0.2.0',
    license: 'CC0-1.0',
    licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
    description: 'Generic furniture, appliances, casework and decor as FS_furniture 0.1.0 elements ready to place: '
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

/**
 * The FS_landscape starter sizes (FLR-T-13.5, registry/FS_landscape/spec.md chapter 7): a generic
 * plant of each form in each size class, as an FS_landscape element ready to place - its form, a
 * tree's clear height and its box in the convention of spec.md 3.3, planted at grade.
 *
 *   registry/FS_landscape/library.json   the catalogue (written, never edited by hand)
 *
 *   pnpm library:landscape          writes it
 *   pnpm library:landscape:check    fails if it differs from what it would write
 *
 * Everything is a pure function of the ITEMS table below. The sizes are Floorspec's own round numbers,
 * no species' and no nursery's; the file is dedicated to the public domain under CC0 1.0.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

export const MM = 1280;
export const LIBRARY_FILE = join(import.meta.dirname, '..', 'registry', 'FS_landscape', 'library.json');

export type Form = 'tree' | 'shrub' | 'grass' | 'groundcover';
export type Size = 'small' | 'medium' | 'large';

/** spec.md 2.3: the lower bounds of medium and large, by form, in millimetres. */
export const CLASS_BOUNDS: Record<Form, [number, number]> = {
  tree: [8000, 14000],
  shrub: [900, 2000],
  grass: [600, 1200],
  groundcover: [150, 300],
};

/** spec.md 2.3: the size class of a plant of `form` whose height is `h` base units. */
export function sizeClass(form: Form, h: number): Size {
  const [m, l] = CLASS_BOUNDS[form];
  return h < m * MM ? 'small' : h < l * MM ? 'medium' : 'large';
}

/** spec.md chapter 7: [form, size, spread, height, clear height] in millimetres. */
export const ITEMS: [Form, Size, number, number, number | null][] = [
  ['tree', 'small', 4500, 6000, 1500],
  ['tree', 'medium', 8000, 11000, 2200],
  ['tree', 'large', 13000, 18000, 3000],
  ['shrub', 'small', 600, 500, null],
  ['shrub', 'medium', 1200, 1200, null],
  ['shrub', 'large', 2400, 2700, null],
  ['grass', 'small', 450, 350, null],
  ['grass', 'medium', 900, 900, null],
  ['grass', 'large', 1500, 1800, null],
  ['groundcover', 'small', 450, 100, null],
  ['groundcover', 'medium', 900, 200, null],
  ['groundcover', 'large', 1500, 350, null],
];

const NAMES: Record<Form, string> = { tree: 'tree', shrub: 'shrub', grass: 'ornamental grass', groundcover: 'groundcover' };
const cap = (s: string): string => s[0]!.toUpperCase() + s.slice(1);

/** spec.md 3.3: a plant's box for spread s and height h, planted at grade. */
export function plantBox(s: number, h: number): { min: number[]; max: number[] } {
  const r = Math.floor(s / 2);
  return { min: [-r, -r, 0], max: [s - r, s - r, h] };
}

export function build(): string {
  const items: Record<string, unknown> = {};
  for (const [form, size, spread, height, clear] of ITEMS) {
    const id = `${form}-${size}`;
    items[id] = {
      kind: 'plants',
      size,
      element: {
        form,
        catalogue: id,
        name: `${cap(size)} ${NAMES[form]}`,
        ...(clear === null ? {} : { clearHeight: clear * MM }),
        fallback: { box: plantBox(spread * MM, height * MM) },
      },
    };
  }
  const lib = {
    library: 'FS_landscape starter sizes',
    extension: 'FS_landscape',
    version: '0.1.0',
    license: 'CC0-1.0',
    licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
    description:
      'A generic plant of each form in each size class as an FS_landscape 0.1.0 element ready to place: lengths in base units (1/1280 mm), its box in the convention of spec.md 3.3, planted at grade. Written by tools/landscape-library.ts.',
    items,
  };
  return JSON.stringify(lib, null, 2) + '\n';
}

function main(argv: string[]): number {
  const text = build();
  if (argv.includes('--check')) {
    const now = readFileSync(LIBRARY_FILE, 'utf8');
    if (now !== text) {
      console.error('FS_landscape library.json differs from what tools/landscape-library.ts writes: run pnpm library:landscape');
      return 1;
    }
  } else writeFileSync(LIBRARY_FILE, text);
  console.log(`FS_landscape starter sizes: ${ITEMS.length} items ${argv.includes('--check') ? 'checked' : 'written'}`);
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) process.exit(main(process.argv.slice(2)));

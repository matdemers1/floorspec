/**
 * The FS_outdoor starter library (FLR-T-15.2, registry/FS_outdoor/spec.md chapter 7): a plunge pool,
 * a pool and a spa; a pergola, a covered porch and a shade sail; two outdoor kitchens; a fire pit, a
 * fire table and a fireplace; and three fence and wall styles to draw - each an FS_outdoor element
 * ready to place, its box in the convention of spec.md 3.3, at grade.
 *
 *   registry/FS_outdoor/library.json   the catalogue (written, never edited by hand)
 *
 *   pnpm library:outdoor          writes it
 *   pnpm library:outdoor:check    fails if it differs from what it would write
 *
 * Everything is a pure function of the ITEMS table below, in feet and inches as the board reads
 * them. The sizes are Floorspec's own round numbers, no maker's; the file is dedicated to the public
 * domain under CC0 1.0.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

export const IN = 32512;
export const FT = 12 * IN;
export const LIBRARY_FILE = join(import.meta.dirname, '..', 'registry', 'FS_outdoor', 'library.json');

export type Kind = 'pools' | 'fences' | 'shelters' | 'kitchens' | 'fires';

/** spec.md 3.3: a box centred on its frame horizontally, from z0 to z1. */
export function centred(x: number, y: number, z0: number, z1: number): { min: number[]; max: number[] } {
  const hx = Math.floor(x / 2);
  const hy = Math.floor(y / 2);
  return { min: [-hx, -hy, z0], max: [x - hx, y - hy, z1] };
}

interface Item {
  id: string;
  kind: Kind;
  name: string;
  /** Members of the element, besides its catalogue, name and fallback. */
  members: Record<string, unknown>;
  /** [X, Y, bottom, top]: a fence's X and Y are 0 - it has no box until it is drawn. */
  box: [number, number, number, number];
}

/** spec.md chapter 7: every item, in the order the table lists them. */
export const ITEMS: Item[] = [
  { id: 'plunge-pool-8x14', kind: 'pools', name: 'Plunge pool, 8′ × 14′', box: [8 * FT, 14 * FT, -66 * IN, 0], members: { form: 'plunge', coping: 12 * IN, waterLine: 6 * IN, copingMaterial: 'stone', interior: 'plaster', heated: true } },
  { id: 'pool-16x32', kind: 'pools', name: 'Pool, 16′ × 32′', box: [16 * FT, 32 * FT, -6 * FT, 0], members: { form: 'pool', coping: 12 * IN, waterLine: 6 * IN, copingMaterial: 'concrete', interior: 'plaster' } },
  { id: 'spa-7x7', kind: 'pools', name: 'Spa, 7′ × 7′', box: [7 * FT, 7 * FT, -24 * IN, 18 * IN], members: { form: 'spa', coping: 6 * IN, waterLine: 4 * IN, copingMaterial: 'stone', interior: 'tile', heated: true } },
  { id: 'pergola-12x16', kind: 'shelters', name: 'Pergola, 12′ × 16′', box: [12 * FT, 16 * FT, 0, 114 * IN], members: { top: 'slats', material: 'timber', postSize: 6 * IN, postSpacing: 8 * FT, rafterSpacing: 24 * IN, clearHeight: 96 * IN } },
  { id: 'porch-10x16', kind: 'shelters', name: 'Covered porch, 10′ × 16′', box: [10 * FT, 16 * FT, 0, 132 * IN], members: { top: 'solid', material: 'timber', postSize: 6 * IN, postSpacing: 8 * FT, rafterSpacing: 16 * IN, clearHeight: 102 * IN, attached: true } },
  { id: 'shade-sail-12x12', kind: 'shelters', name: 'Shade sail, 12′ × 12′', box: [12 * FT, 12 * FT, 0, 120 * IN], members: { top: 'sail', material: 'steel', postSize: 4 * IN, postSpacing: 12 * FT, clearHeight: 96 * IN } },
  { id: 'kitchen-10', kind: 'kitchens', name: 'Outdoor kitchen, 10′ run', box: [30 * IN, 10 * FT, 0, 36 * IN], members: { appliances: ['grill', 'sink', 'refrigerator'], counter: 'stone', fuel: 'gas' } },
  { id: 'kitchen-6', kind: 'kitchens', name: 'Grill station, 6′ run', box: [30 * IN, 6 * FT, 0, 36 * IN], members: { appliances: ['grill', 'sideBurner'], counter: 'concrete', fuel: 'propane' } },
  { id: 'fire-pit-4', kind: 'fires', name: 'Fire pit, 4′', box: [4 * FT, 4 * FT, 0, 18 * IN], members: { form: 'pit', fuel: 'gas' } },
  { id: 'fire-table-5', kind: 'fires', name: 'Fire table, 5′ × 2′ 6″', box: [30 * IN, 5 * FT, 0, 24 * IN], members: { form: 'table', fuel: 'propane' } },
  { id: 'fireplace-6', kind: 'fires', name: 'Outdoor fireplace, 6′', box: [3 * FT, 6 * FT, 0, 10 * FT], members: { form: 'fireplace', fuel: 'wood' } },
  { id: 'fence-privacy-6', kind: 'fences', name: 'Privacy fence, 6′', box: [0, 0, 0, 6 * FT], members: { form: 'fence', width: 4 * IN, style: 'privacy', material: 'timber', postSpacing: 8 * FT } },
  { id: 'fence-picket-4', kind: 'fences', name: 'Picket fence, 4′', box: [0, 0, 0, 4 * FT], members: { form: 'fence', width: 3 * IN, style: 'picket', material: 'timber', postSpacing: 8 * FT } },
  { id: 'wall-garden-3', kind: 'fences', name: 'Garden wall, 3′', box: [0, 0, 0, 3 * FT], members: { form: 'wall', width: 8 * IN, style: 'solid', material: 'brick', postSpacing: 10 * FT } },
];

export function build(): string {
  const items: Record<string, unknown> = {};
  for (const it of ITEMS) {
    const [x, y, z0, z1] = it.box;
    items[it.id] = {
      kind: it.kind,
      element: { ...it.members, catalogue: it.id, name: it.name, fallback: { box: centred(x, y, z0, z1) } },
    };
  }
  const lib = {
    library: 'FS_outdoor starter library',
    extension: 'FS_outdoor',
    version: '0.1.0',
    license: 'CC0-1.0',
    licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
    description:
      'Pools, shelters, outdoor kitchens and fire features as FS_outdoor 0.1.0 elements ready to place, and fence and wall styles ready to draw (a fence item has no points, and its box is its height alone until it is drawn): lengths in base units (1/1280 mm), boxes in the convention of spec.md 3.3, at grade. Written by tools/outdoor-library.ts.',
    items,
  };
  return JSON.stringify(lib, null, 2) + '\n';
}

function main(argv: string[]): number {
  const text = build();
  if (argv.includes('--check')) {
    const now = readFileSync(LIBRARY_FILE, 'utf8');
    if (now !== text) {
      console.error('FS_outdoor library.json differs from what tools/outdoor-library.ts writes: run pnpm library:outdoor');
      return 1;
    }
  } else writeFileSync(LIBRARY_FILE, text);
  console.log(`FS_outdoor starter library: ${ITEMS.length} items ${argv.includes('--check') ? 'checked' : 'written'}`);
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) process.exit(main(process.argv.slice(2)));

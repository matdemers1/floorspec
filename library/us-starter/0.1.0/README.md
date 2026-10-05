# Floorspec US starter type library 0.1.0

Common US wall, door and window types, and the materials their layers use, as Floorspec Core 0.3
types and materials ready to embed in a document. **Non-normative**: nothing in Floorspec requires
these items, and a document that uses one is exactly as valid as one that defines its own.

- Library: `https://d3cloud.io/floorspec/library/us-starter`
- This version: `https://d3cloud.io/floorspec/library/us-starter/0.1.0/` — published once, never changed; a change is a new version
- Index: `https://d3cloud.io/floorspec/library/us-starter/0.1.0/index.json`; each item at `https://d3cloud.io/floorspec/library/us-starter/0.1.0/items/<item>.json`
- Digests: `SHA256SUMS` beside this file
- License: CC0 1.0 — dedicated to the public domain

11 wall types, 15 door types, 25 window types and 10 materials.

## Embedding an item

A document embeds every type it uses (Core 8.1): it copies the item's `element` into its `types`
or `materials` collection, and each of a wall type's materials into `materials`, and never refers
to the library by URL. Each copy keeps its `source` — `library`, `version` and `item` — which
records where it came from and is never read by derivation.

Each item in `index.json` carries `embed`, the Floorspec Ops batch that embeds it into a document
that has none of its elements, under the library's own IDs:

```json
{ "batch": [
  { "op": "addElement", "collection": "materials", "id": "gypsum-board", "element": { … } },
  { "op": "addElement", "collection": "materials", "id": "wood-stud-framing", "element": { … } },
  { "op": "addElement", "collection": "types", "id": "wall-2x4-interior", "element": { … } }
] }
```

- **Already embedded.** Leave out every `addElement` whose ID the document already holds with
  identical content: embedding an item twice adds nothing. (`addElement` of a used ID fails the
  batch, Ops 2.1.)
- **A different element under the same ID.** Embed under other IDs, and point the wall type's
  layers at the materials' new IDs. An element's ID is the document's choice; `source.item` is
  what names the library item.
- **A newer version.** Never automatic. To move an embedded type to a later version of this
  library, read that version's item and `setProperty` each member that differs — the layers, the
  sizes, `/source/version` — in one batch, so the document says which version it now follows.
- **Edited after embedding.** Allowed: the copy is the document's own. Keep `source` to say where
  it started, or `unsetProperty` it.

`tools/us-library.ts` exports `embed(document, item, ids)`, which computes exactly these
operations.

## Conventions

- **Units.** Every length is an integer number of base units, 1/1280 mm: one inch is 32,512, so
  every size here to a sixty-fourth of an inch is exact. Sizes are stated in inches below.
- **Lumber.** Sizes are nominal; actual sizes are smaller: a nominal 2x4 is 1 1/2 in x 3 1/2 in and a
  2x6 is 1 1/2 in x 5 1/2 in, so a stud layer is 3 1/2 in or 5 1/2 in thick. A nominal 8 in concrete
  masonry unit is 7 5/8 in thick.
- **Layers** run from the wall's left (exterior) face to its right (interior) face (Core 8.3). A thin
  membrane is given 1/64 in, because a layer's thickness is greater than zero.
- **Doors.** A door type's `width` and `height` are its rough opening — the hole in the wall
  (Core 7.1) — taken generically as the door unit 2 in wider and 2 1/2 in taller; a garage door's
  opening is the door's own size. A pocket door's opening is its passage: its pocket, inside the
  wall beside it, needs about another door's width of wall free of other openings. A swinging door,
  a pair and a bifold carry a `swing` clearance envelope (Core 13.5) as deep as their leaves
  sweep.
- **Windows.** Unit sizes are width x height in inches. A window type's `width` and `height` are
  its rough opening, the unit 1/2 in wider and taller, and its `sill` puts the head of the rough
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

| Item | Name | Layers, exterior to interior | Thickness |
|---|---|---|---|
| `wall-2x4-interior` | 2x4 interior partition, gypsum both faces | 1/2 in gypsum board; 2x4 studs (3 1/2 in deep); 1/2 in gypsum board | 4 1/2 in |
| `wall-2x6-interior` | 2x6 interior partition, gypsum both faces | 1/2 in gypsum board; 2x6 studs (5 1/2 in deep); 1/2 in gypsum board | 6 1/2 in |
| `wall-2x4-exterior-fibre-cement` | 2x4 exterior wall, fibre-cement siding | 5/16 in fibre-cement lap siding; weather-resistive barrier, 1/64 in; 7/16 in OSB sheathing; 2x4 studs (3 1/2 in deep), insulated cavities; 1/2 in gypsum board | 4 49/64 in |
| `wall-2x6-exterior-fibre-cement` | 2x6 exterior wall, fibre-cement siding | 5/16 in fibre-cement lap siding; weather-resistive barrier, 1/64 in; 7/16 in OSB sheathing; 2x6 studs (5 1/2 in deep), insulated cavities; 1/2 in gypsum board | 6 49/64 in |
| `wall-2x6-exterior-fibre-cement-ci` | 2x6 exterior wall, fibre-cement siding over continuous insulation | 5/16 in fibre-cement lap siding; weather-resistive barrier, 1/64 in; 1 in rigid foam board; 7/16 in OSB sheathing; 2x6 studs (5 1/2 in deep), insulated cavities; 1/2 in gypsum board | 7 49/64 in |
| `wall-2x4-exterior-brick-veneer` | 2x4 exterior wall, brick veneer | brick veneer (3 5/8 in actual); 1 in air space; weather-resistive barrier, 1/64 in; 7/16 in OSB sheathing; 2x4 studs (3 1/2 in deep), insulated cavities; 1/2 in gypsum board | 9 5/64 in |
| `wall-2x6-exterior-brick-veneer` | 2x6 exterior wall, brick veneer | brick veneer (3 5/8 in actual); 1 in air space; weather-resistive barrier, 1/64 in; 7/16 in OSB sheathing; 2x6 studs (5 1/2 in deep), insulated cavities; 1/2 in gypsum board | 11 5/64 in |
| `wall-cmu-8` | 8 in CMU wall, exposed both faces | 8 in nominal CMU (7 5/8 in actual) | 7 5/8 in |
| `wall-cmu-8-furred` | 8 in CMU wall, furred and finished with gypsum inside | 8 in nominal CMU (7 5/8 in actual); 3/4 in furring space; 1/2 in gypsum board | 8 7/8 in |
| `wall-concrete-foundation-8` | 8 in cast-in-place concrete foundation wall | 8 in cast-in-place concrete | 8 in |
| `wall-concrete-foundation-10` | 10 in cast-in-place concrete foundation wall | 10 in cast-in-place concrete | 10 in |

## Door types

| Item | Operation | Unit | Rough opening | Clear opening |
|---|---|---|---|---|
| `door-interior-swing-24x80` | `swing` | 24 in x 80 in | 26 in x 82 1/2 in | 22 in x 80 in (generic) |
| `door-interior-swing-28x80` | `swing` | 28 in x 80 in | 30 in x 82 1/2 in | 26 in x 80 in (generic) |
| `door-interior-swing-30x80` | `swing` | 30 in x 80 in | 32 in x 82 1/2 in | 28 in x 80 in (generic) |
| `door-interior-swing-32x80` | `swing` | 32 in x 80 in | 34 in x 82 1/2 in | 30 in x 80 in (generic) |
| `door-interior-swing-36x80` | `swing` | 36 in x 80 in | 38 in x 82 1/2 in | 34 in x 80 in (generic) |
| `door-exterior-swing-36x80` | `swing` | 36 in x 80 in | 38 in x 82 1/2 in | 33 3/4 in x 79 in (generic) |
| `door-pocket-30x80` | `pocket` | 30 in x 80 in | 32 in x 82 1/2 in | 28 1/2 in x 80 in (generic) |
| `door-bifold-30x80` | `bifold` | 30 in x 80 in | 32 in x 82 1/2 in | 26 in x 80 in (generic) |
| `door-bifold-36x80` | `bifold` | 36 in x 80 in | 38 in x 82 1/2 in | 32 in x 80 in (generic) |
| `door-bypass-48x80` | `bypassSlide` | 48 in x 80 in | 50 in x 82 1/2 in | 23 in x 80 in (generic) |
| `door-bypass-60x80` | `bypassSlide` | 60 in x 80 in | 62 in x 82 1/2 in | 29 in x 80 in (generic) |
| `door-double-swing-60x80` | `doubleSwing` | 60 in x 80 in | 62 in x 82 1/2 in | 56 in x 80 in (generic) |
| `door-double-swing-72x80` | `doubleSwing` | 72 in x 80 in | 74 in x 82 1/2 in | 68 in x 80 in (generic) |
| `door-garage-overhead-9x7` | `overhead` | 108 in x 84 in | 108 in x 84 in | 106 1/2 in x 82 in (generic) |
| `door-garage-overhead-16x7` | `overhead` | 192 in x 84 in | 192 in x 84 in | 190 1/2 in x 82 in (generic) |

## Window types

| Item | Operation | Unit | Rough opening | Sill | Clear opening |
|---|---|---|---|---|---|
| `window-single-hung-24x36` | `singleHung` | 24 in x 36 in | 24 1/2 in x 36 1/2 in | 46 in | 20 in x 15 in (generic) |
| `window-single-hung-30x48` | `singleHung` | 30 in x 48 in | 30 1/2 in x 48 1/2 in | 34 in | 26 in x 21 in (generic) |
| `window-single-hung-36x48` | `singleHung` | 36 in x 48 in | 36 1/2 in x 48 1/2 in | 34 in | 32 in x 21 in (generic) |
| `window-single-hung-36x60` | `singleHung` | 36 in x 60 in | 36 1/2 in x 60 1/2 in | 22 in | 32 in x 27 in (generic) |
| `window-double-hung-24x36` | `doubleHung` | 24 in x 36 in | 24 1/2 in x 36 1/2 in | 46 in | 20 in x 15 in (generic) |
| `window-double-hung-30x48` | `doubleHung` | 30 in x 48 in | 30 1/2 in x 48 1/2 in | 34 in | 26 in x 21 in (generic) |
| `window-double-hung-36x48` | `doubleHung` | 36 in x 48 in | 36 1/2 in x 48 1/2 in | 34 in | 32 in x 21 in (generic) |
| `window-double-hung-36x60` | `doubleHung` | 36 in x 60 in | 36 1/2 in x 60 1/2 in | 22 in | 32 in x 27 in (generic) |
| `window-double-hung-36x72` | `doubleHung` | 36 in x 72 in | 36 1/2 in x 72 1/2 in | 10 in | 32 in x 33 in (generic) |
| `window-casement-24x36` | `casement` | 24 in x 36 in | 24 1/2 in x 36 1/2 in | 46 in | 18 in x 32 in (generic) |
| `window-casement-24x48` | `casement` | 24 in x 48 in | 24 1/2 in x 48 1/2 in | 34 in | 18 in x 44 in (generic) |
| `window-casement-30x48` | `casement` | 30 in x 48 in | 30 1/2 in x 48 1/2 in | 34 in | 24 in x 44 in (generic) |
| `window-casement-30x60` | `casement` | 30 in x 60 in | 30 1/2 in x 60 1/2 in | 22 in | 24 in x 56 in (generic) |
| `window-slider-36x24` | `horizontalSlider` | 36 in x 24 in | 36 1/2 in x 24 1/2 in | 58 in | 15 in x 20 in (generic) |
| `window-slider-48x36` | `horizontalSlider` | 48 in x 36 in | 48 1/2 in x 36 1/2 in | 46 in | 21 in x 32 in (generic) |
| `window-slider-60x36` | `horizontalSlider` | 60 in x 36 in | 60 1/2 in x 36 1/2 in | 46 in | 27 in x 32 in (generic) |
| `window-slider-60x48` | `horizontalSlider` | 60 in x 48 in | 60 1/2 in x 48 1/2 in | 34 in | 27 in x 44 in (generic) |
| `window-slider-72x48` | `horizontalSlider` | 72 in x 48 in | 72 1/2 in x 48 1/2 in | 34 in | 33 in x 44 in (generic) |
| `window-fixed-24x48` | `fixed` | 24 in x 48 in | 24 1/2 in x 48 1/2 in | 34 in | none: a fixed window does not open |
| `window-fixed-36x36` | `fixed` | 36 in x 36 in | 36 1/2 in x 36 1/2 in | 46 in | none: a fixed window does not open |
| `window-fixed-48x48` | `fixed` | 48 in x 48 in | 48 1/2 in x 48 1/2 in | 34 in | none: a fixed window does not open |
| `window-fixed-72x48` | `fixed` | 72 in x 48 in | 72 1/2 in x 48 1/2 in | 34 in | none: a fixed window does not open |
| `window-awning-24x24` | `awning` | 24 in x 24 in | 24 1/2 in x 24 1/2 in | 58 in | 20 in x 10 in (generic) |
| `window-awning-36x24` | `awning` | 36 in x 24 in | 36 1/2 in x 24 1/2 in | 58 in | 32 in x 10 in (generic) |
| `window-awning-48x24` | `awning` | 48 in x 24 in | 48 1/2 in x 24 1/2 in | 58 in | 44 in x 10 in (generic) |

## Materials

| Item | Name | Colour | Roughness | What it is |
|---|---|---|---|---|
| `gypsum-board` | Gypsum board, painted | `#efede8` | 900 | interior finish |
| `wood-stud-framing` | Wood stud framing | `#c8a46e` | 850 | studs at regular spacing, cavities empty |
| `wood-stud-framing-insulated` | Wood stud framing, insulated cavities | `#dcc28c` | 900 | studs with insulation filling the cavities between them |
| `osb-sheathing` | OSB sheathing | `#c09a5b` | 900 | oriented strand board |
| `weather-resistive-barrier` | Weather-resistive barrier | `#e9edf0` | 600 | a house wrap or building paper |
| `fibre-cement-siding` | Fibre-cement lap siding, painted | `#8f9aa1` | 750 | exterior cladding |
| `rigid-foam-insulation` | Rigid foam insulation board | `#cfdbe3` | 700 | continuous insulation outside the sheathing |
| `brick-veneer` | Brick veneer | `#9a4b34` | 950 | a single wythe of brick tied to the frame behind it |
| `concrete-masonry-unit` | Concrete masonry units | `#a6a49e` | 950 | hollow concrete block (CMU) |
| `cast-in-place-concrete` | Cast-in-place concrete | `#aaa9a3` | 900 | poured concrete |

Colours are plausible sRGB base colours and roughness is in thousandths (Core 18.1); no material
has a texture.

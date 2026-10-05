# 8. Types, materials and assets

## 8.1 Types

A **type** is a reusable definition — a wall assembly, a door, a window — that elements refer to
instead of repeating (FLR-ADR-003). Change the type, and every element that uses it changes.

Types live in the `types` collection, and each has a `kind`:

| `kind` | Used by | Its members |
|---|---|---|
| `"wallType"` | `Wall.type` | 8.3 |
| `"doorType"` | `Opening.fill` | 8.4 |
| `"windowType"` | `Opening.fill` | 8.4 |

A type MUST have a `kind` from this table. {#FS-CORE-8.1.1 MUST}

Every type MAY also carry `name`, `extensions` and `extras` (1.4). {#FS-CORE-8.1.2 MAY}

Common types — a 2×4 interior partition, a 2×6 exterior wall, a 36-inch door — are published as a
non-normative starter library. A document embeds every type it uses; it never refers to a library
by URL, so it is always complete on its own.

## 8.2 Resolving typed properties

Some members of an element are **typed properties**: the element may set them itself, or inherit
them from its type. They are a wall's `layers` (from its `type`) and an opening's `width`,
`height`, `sill` and `clearOpening` (from its `fill`).

A reader MUST resolve a typed property to the element's own member if present, otherwise to its type's member if present, otherwise to the property's default if it has one. {#FS-CORE-8.2.1 MUST}

An element's own value always wins over its type's — the rule IFC calls an occurrence overriding
its type. A typed property that is an object or an array is resolved whole: a wall's own `layers`
replace its type's, and an opening's own `clearOpening` replaces its type's, so an opening that
states a clear width and height but no `area` has no declared area, whatever its type declares. A typed property has no constant default at the element (1.5): an opening that states
`"sill": 0` overrides a window type's sill, so a writer never omits it.

## 8.3 Wall types and layers

| Member | Type | Default | Meaning |
|---|---|---|---|
| `kind` | `"wallType"` | — | 8.1 |
| `layers` | array of at least one layer | — (always present) | the assembly, from the wall's left (exterior) face to its right (interior) face |
| `name`, `extensions`, `extras` | | | 1.4 |

A **layer**:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `thickness` | length | — (always present) | the layer's thickness |
| `function` | layer function (4.3) | — (always present) | what the layer does |
| `material` | reference to a material | absent | what it is made of |

A `layers` array MUST contain at least one layer, and every layer's `thickness` MUST be greater than zero. {#FS-CORE-8.3.1 MUST}

A wall's own `layers` member, when present, follows the same rules and replaces its type's layers
entirely.

## 8.4 Door and window types

| Member | Type | Default | Meaning |
|---|---|---|---|
| `kind` | `"doorType"` or `"windowType"` | — | 8.1 |
| `width` | length | absent | the width of every opening it fills, unless the opening overrides it |
| `height` | length | absent | likewise, the height |
| `sill` | length | absent | likewise, the sill |
| `operation` | a door operation or a window operation (below) | absent: not declared | how its leaves or sashes move |
| `clearOpening` | clear opening (below) | absent | the net clear opening of every opening it fills, as its maker declares it, unless the opening overrides it |
| `clearances` | object: envelope name → clearance envelope (13.5) | `{}` | the space every opening it fills needs kept clear — a door's swing, the space in front of a window |
| `name`, `extensions`, `extras` | | | 1.4 |

A door or window type's `width` and `height`, when present, MUST be greater than zero, and its `sill` MUST NOT be negative. {#FS-CORE-8.4.1 MUST}

**Operation.** A door type's `operation` is one of these:

| Door operation | The door |
|---|---|
| `"swing"` | one leaf, hinged at one jamb, swinging one way |
| `"doubleSwing"` | a pair of leaves, hinged at both jambs, swinging the same way |
| `"doubleActing"` | one leaf that swings both ways, closing itself |
| `"bypassSlide"` | two or more leaves sliding past each other on parallel tracks |
| `"pocket"` | a leaf sliding into a pocket inside the wall |
| `"surfaceSlide"` | a leaf sliding along the face of the wall, as a barn door does |
| `"bifold"` | leaves hinged to each other, folding to the side |
| `"overhead"` | a door that lifts above the opening, as a sectional or a roll-up garage door does |
| `"cased"` | no leaf: a cased opening with a frame or trim and nothing to close |

A window type's `operation` is one of these:

| Window operation | The window |
|---|---|
| `"fixed"` | does not open |
| `"casement"` | a sash hinged at one side, swinging out or in |
| `"awning"` | a sash hinged at the top, opening out at the bottom |
| `"hopper"` | a sash hinged at the bottom, opening in at the top |
| `"singleHung"` | two sashes, one above the other; the lower one slides up |
| `"doubleHung"` | two sashes, one above the other; both slide |
| `"horizontalSlider"` | sashes side by side; at least one slides sideways |
| `"tiltTurn"` | a sash that tilts in at the top or swings in from the side |
| `"pivot"` | a sash that turns about a central axis |

A door type's `operation`, when present, MUST be a door operation of this section, and a window type's a window operation. {#FS-CORE-8.4.2 MUST}

An operation that is absent is not declared: a reader does not assume that a door swings. The
operation says nothing about size; it says how to read the opening's `hinge` and `swing` (7.1) and
what an exporter writes (Annex A). This draft does not record a casement's or a tilt-turn's hand,
a pivot's axis, or which sash of a slider moves.

**Clear opening.** A **clear opening** is the net clear opening of a door or window: the opening a
person or an object can pass through when it is open as far as it goes — for a swinging door, the
width between the stop and the face of the leaf standing open at 90°; for a pair, both leaves open;
for a window, the open sash's clear width, height and area. It is an object:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `width` | length | — (always present) | the clear width |
| `height` | length | — (always present) | the clear height |
| `area` | area: an integer number of square base units, from 1 to 2⁵³ − 1 (2.5) | absent: not declared | the clear area; a window's only |

A clear opening's `width` and `height` MUST be greater than zero, its `area`, when present, MUST be an integer from 1 to 2⁵³ − 1, and a door type's clear opening MUST NOT have an `area`. {#FS-CORE-8.4.3 MUST}

A clear opening's `area` MUST NOT exceed the product of its `width` and its `height`. {#FS-CORE-8.4.4 MUST NOT}

A door or window type's clear opening MUST NOT be wider than the type's `width`, when the type has one, nor taller than its `height`, when it has one. {#FS-CORE-8.4.5 MUST NOT}

> [!note] Why the clear opening is declared, not derived
> A door's clear width depends on its leaf's thickness, its hinges, its stops and how far it
> opens; a window's clear area on its frame, its sash, its hinges and how far the sash travels.
> None of these is in the document, and no formula over the rough opening gives the same answer
> for two products of the same size. So Floorspec stores the clear opening as the integers its
> maker declares — on the type, and on an opening where one opening differs — and never computes
> one. An opening without one has no clear opening: a check that needs it says so, and does not
> guess.

Frame, glazing and hardware are defined in a later draft. A type's `clearances` are not a typed
property (8.2): an opening cannot override them in this draft, and they are placed in the frame of
each opening the type fills (13.5). Neither is a type's `operation`: an opening has the operation
of the type that fills it.

## 8.5 Materials

| Member | Type | Default | Meaning |
|---|---|---|---|
| `color` | `"#rrggbb"`, lowercase hexadecimal sRGB | absent | the material's base colour |
| `texture` | `{ "asset": reference to an asset, "size": [w, h] }`, both always present | absent | an image tiled across the surface; one tile covers `w` by `h` base units |
| `name`, `extensions`, `extras` | | | 1.4 |

A material's `color` MUST match `^#[0-9a-f]{6}$`. {#FS-CORE-8.5.1 MUST}

A texture's `size` MUST be two lengths greater than zero. {#FS-CORE-8.5.2 MUST}

Physically based rendering properties are defined in a later draft. A texture's real-world size is
what makes a dropped-in photo of a tile the right scale on every wall.

## 8.6 Assets

An **asset** is a file a document refers to — a texture image now; a glTF model or a 2D symbol in
later drafts and extensions.

| Member | Type | Default | Meaning |
|---|---|---|---|
| `path` | relative path | absent | where the file is, relative to the document (packaged with it) |
| `uri` | an absolute URI (RFC 3986) whose scheme is `https` and which has an authority | absent | where the file is on the web |
| `sha256` | 64 lowercase hexadecimal digits | — (always present) | the SHA-256 digest of the file's bytes |
| `mediaType` | a media type `type/subtype` as RFC 6838 §4.2 defines it, without parameters, such as `"image/png"` | — (always present) | what kind of file it is |
| `name`, `extensions`, `extras` | | | 1.4 |

An asset MUST have exactly one of `path` and `uri`. {#FS-CORE-8.6.1 MUST}

A `path` MUST be relative, use `/` as its separator, contain no empty, `.` or `..` segment, and have no `:` in its first segment. {#FS-CORE-8.6.2 MUST}
A path is a path, not a URI reference: it is not percent-encoded.

The digest makes an asset verifiable wherever it is found, and lets a store keep one copy of a
texture used by many projects. An asset by `uri` makes the document depend on someone else's
server; validators report it as a lint (`FS-LINT-007`).

## 8.7 Lints

A validator SHOULD report these with the codes of chapter 10. {#FS-CORE-8.7.1 SHOULD}

- **Unused type, material or asset** (`FS-LINT-006`, information): nothing refers to it.
- **External asset** (`FS-LINT-007`, warning): an asset located by `uri`.

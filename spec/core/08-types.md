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
them from its type. In core 0.1 they are a wall's `layers` (from its `type`) and an opening's
`width`, `height` and `sill` (from its `fill`).

A reader MUST resolve a typed property to the element's own member if present, otherwise to its type's member if present, otherwise to the property's default if it has one. {#FS-CORE-8.2.1 MUST}

An element's own value always wins over its type's — the rule IFC calls an occurrence overriding
its type. A typed property has no constant default at the element (1.5): an opening that states
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
| `clearances` | object: envelope name → clearance envelope (13.5) | `{}` | the space every opening it fills needs kept clear — a door's swing, the space in front of a window |
| `name`, `extensions`, `extras` | | | 1.4 |

A door or window type's `width` and `height`, when present, MUST be greater than zero, and its `sill` MUST NOT be negative. {#FS-CORE-8.4.1 MUST}

Operation, frame, glazing and hardware are defined in a later draft. A type's `clearances` are not
a typed property (8.2): an opening cannot override them in this draft, and they are placed in the
frame of each opening the type fills (13.5).

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

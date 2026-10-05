# 18. Materials, assets and finishes

A photo of a tile is only useful if it is the right size on every wall it is put on, and only
portable if the file travels with the document and can be checked when it arrives. A kitchen's
walls are painted because the kitchen is, not because someone painted each wall; and the strip of
tile behind the counter is a rectangle on one wall's face, not a new wall. This chapter defines
what a material is — a physically based surface at real-world scale, in the metallic-roughness
model glTF 2.0 uses — how its images are placed on a surface, how the files a document refers to
are packaged and checked, and how a room's finishes reach the faces of the walls around it, with
overrides on one face and on a rectangle of one face.

Materials and assets are elements of the `materials` and `assets` collections (1.1), whose members
8.5 and 8.6 list. This chapter defines what 0.3 adds to them, and the finishes of walls.

## 18.1 Materials

A material describes a surface: its **base colour**, how **metallic** it is and how **rough**. Each
may vary across the surface by a map of its texture (18.2).

| Member | Meaning |
|---|---|
| `color` | the base colour, `"#rrggbb"` in sRGB (8.5); with a base colour map, the colour to show where the map is not drawn — a plan, a swatch, a distant view |
| `metallic` | how metallic the surface is, in thousandths: `0` a dielectric (paint, wood, tile, stone), `1000` a bare metal |
| `roughness` | how rough it is, in thousandths: `0` a mirror finish, `1000` fully matte |
| `texture` | the images tiled across the surface, and the size of one tile (18.2) |

The **base colour** of a point of a surface is the texel of the base colour map there (18.3), when
the material's texture has one, and otherwise its `color`; a material with neither has no declared
base colour. Where the texture has a metallic-roughness map, a point's **metallic** is the map's
blue channel there and its **roughness** its green channel, each multiplied by `metallic` / 1000 or
`roughness` / 1000 when that member is present. Without the map they are `metallic` / 1000 — `0`
when it is absent — and `roughness` / 1000 — `1` when it is absent: so a material that states only
its colour is a matte, non-metallic surface, as it was before 0.3 said anything about it.

A material's `metallic` and `roughness`, when present, MUST be integers from 0 to 1000. {#FS-CORE-18.1.1 MUST}

Neither has a constant default: an absent `metallic` or `roughness` lets the map's value through,
where `0` would not. A writer never omits one that is written.

> [!note] Why thousandths, and why metallic-roughness
> Floats are not normative anywhere in Floorspec (2.5), and a factor between 0 and 1 is a scaled
> decimal. A thousandth is finer than the 1/255 step of an 8-bit map, so no map's value is
> lost when it is written as a factor. Metallic-roughness is the model glTF 2.0, USD's
> `UsdPreviewSurface` and every real-time renderer share, so a material exports to each without
> conversion.

## 18.2 Textures

A material's `texture` is the images that vary its surface, and how one tile of them is laid:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `asset` | reference to an asset | absent: no base colour map | the **base colour map**: an sRGB image of the surface's colour |
| `normal` | reference to an asset | absent: no normal map | the **normal map**: a tangent-space normal in the red, green and blue channels, linear, as glTF 2.0 defines it (+X towards increasing `s'`, +Y towards increasing `t'`, 18.3) |
| `metallicRoughness` | reference to an asset | absent: no metallic-roughness map | roughness in the green channel and metalness in the blue, linear, as glTF 2.0 defines it |
| `occlusion` | reference to an asset | absent: no occlusion map | ambient occlusion in the red channel, linear |
| `size` | `[w, h]`, two lengths | — (always present) | the **real-world size** of one tile: the image covers `w` by `h` base units of the surface |
| `offset` | point | `[0, 0]` | where on the surface a tile's corner is, in the surface's coordinates (18.3) |
| `rotation` | angle | `0` | how far the tiles are turned on the surface, counter-clockwise as seen by someone facing it; in (−180,000,000, 180,000,000] |

The four members that name an asset are the texture's **maps**. Every map is laid with the same
tile — the same size, offset and rotation — so a tile's normals, roughness and occlusion stay on its
colour.

A texture MUST have at least one map, and MUST have exactly the members of its table, each of the type its table gives: `size` two lengths greater than zero (8.5.2), `offset` a point, and `rotation` an angle in (−180,000,000, 180,000,000]. {#FS-CORE-18.2.1 MUST}

Every map MUST be an asset whose `mediaType` is `image/png`, `image/jpeg`, `image/webp` or `image/ktx2`. {#FS-CORE-18.2.2 MUST}

A texture of Core 0.1 or 0.2 has an `asset` and a `size` and nothing else: it is a base colour map
at a real-world size, with no offset and no rotation, which is exactly what it means here. A
texture's real-world size is what makes a dropped-in photo of a 12-inch tile the right scale on
every wall: `"size": [390144, 390144]`.

## 18.3 Texture space

Every surface that a material is put on has two **surface coordinates** `(s, t)`, lengths in base
units, that grow to the right and upwards as seen by someone facing the surface:

| Surface | `s` | `t` |
|---|---|---|
| the `"right"` face of wall `W` (5.4) | `(P − S) · e` | `z − b` |
| the `"left"` face of wall `W` | `(S − P) · e` | `z − b` |
| a room's floor (15.1) | `x` | `y` |
| a room's ceiling (15.2), but for the vertical step of a tray | `−x` | `y` |

For a point `P = (x, y)` in plan at elevation `z`: `S` is the position of `W`'s start junction, `e`
the unit vector along `W`'s direction (5.2) and `b` its base elevation (5.9). So a wall's two faces
are both measured from the line through its start junction, each running to the right of a person
looking at it, and a ceiling is seen from below; a floor's and a ceiling's coordinates are the
plan's own, so a floor laid through a doorway runs on unbroken.

A texture's **tile coordinates** `(s', t')` of a point are its surface coordinates moved by
`offset = [ox, oy]` and turned back by `rotation`, through the facing vector `F(rotation) = (fx, fy)`
of 13.1:

```text
s' = ((s − ox)·fx + (t − oy)·fy) / |F|
t' = ((t − oy)·fx − (s − ox)·fy) / |F|
```

The point shows the texel of each map at `frac(s' / w)` of the image's width from its left edge
and `frac(t' / h)` of its height from its bottom edge, where `[w, h]` is the texture's `size` and
`frac(v) = v − ⌊v⌋`. A map therefore appears upright and unmirrored to a person facing the surface,
one tile `w` wide and `h` high, a tile's corner at `offset`, turned by `rotation`, and repeated in
both directions. An exporter to glTF writes `u = s' / w` and `v = −t' / h`, because glTF's `v`
runs down its image.

Software that draws a material's maps on a surface this section lists SHOULD place them exactly as this section defines. {#FS-CORE-18.3.1 SHOULD}

Where a surface slopes — a vaulted ceiling, or a tray's raised centre seen past its border — its
coordinates are still its plan's, so a map is projected straight up onto it and its tiles stretch
across the slope. This draft does not define the coordinates of a tray's vertical step, the end of
a wall at a free end, a slab, a roof or a stair (0.5).

## 18.4 Assets and the package

A document's **package** is the directory that holds the document's file (9.4). An asset's `path`
(8.6) names a file in the package, relative to that directory, with `/` between the names of its
directories; nothing can name a file outside the package, because a path has no `..` and is never
absolute (8.6.2). A path names one file exactly: it is compared as a sequence of Unicode code
points, case and all, and is not percent-encoded. A document and its assets are moved and shared
together, as one directory:

```text
kitchen/
  house.floorspec.json
  assets/
    tile-12in.jpg        ← "path": "assets/tile-12in.jpg"
```

Core 0.3 adds an asset's `byteLength`: the length of its file in bytes, as its maker declares it.

An asset's `byteLength`, when present, MUST be an integer from 0 to 2⁵³ − 1. {#FS-CORE-18.4.1 MUST}

An asset's `sha256` and `mediaType` are always present (8.6), so a file is identified by what it
is, not by where it is: two assets with one digest are one file, wherever each is kept, and a store
keeps one copy of a texture that many documents use. An asset located by `uri` is someone else's
file on the web: the document is not complete without that server, and a validator reports it with
the warning `FS-LINT-007` (8.7), but never fetches it.

A validator is given a document; it is not necessarily given the files of its package, and a
digest cannot be checked without the bytes. A **package validator** is a validator that is also
given the files of the document's package. It checks every asset located by `path` against its
file, as part of the invariant tier (10.1):

A package validator MUST report `FS-INV-1005` for each asset located by `path` for which the package has no file at that path. {#FS-CORE-18.4.2 MUST}

A package validator MUST report `FS-INV-1006` for each asset whose file's SHA-256 digest is not its `sha256`, and `FS-INV-1007` for each asset with a `byteLength` that is not its file's length in bytes. {#FS-CORE-18.4.3 MUST}

A validator that is not given the files of the package MUST NOT report `FS-INV-1005`, `FS-INV-1006` or `FS-INV-1007`. {#FS-CORE-18.4.4 MUST NOT}

So a document can be valid while its package is not: a document whose texture is missing from the
directory it was copied into is a valid document in a broken package, and a package validator says
which file is missing, or which file is not the one the document names.

## 18.5 Finishes

A **finish** is the material a surface shows. A room names the finishes of the surfaces that face
it — its walls, its floor and its ceiling — with `wallFinish`, `floorFinish` and `ceilingFinish`
(6.5). A wall names the finishes of its own faces, where one face, or a rectangle of one face, is
finished differently from the room it faces, with `finishes` (5.2):

| Member | Type | Default | Meaning |
|---|---|---|---|
| `left` | face finish | `{}` | the finish of the wall's left face (5.4): its exterior, when the wall is drawn clockwise around a room |
| `right` | face finish | `{}` | the finish of its right face |

A **face finish**:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `material` | reference to a material | absent: from the room the face faces, or the wall's layer (18.6) | the material of the whole face |
| `regions` | array of regions | `[]` | rectangles of the face finished with another material |

A **region** is a rectangle on a face, in the wall's own measures — the distances along its
location line from its start junction (as an opening's `offset` is, 7.1), and the heights above its
base elevation (as a `wallFace` host's `height` is, 13.3):

| Member | Type | Default | Meaning |
|---|---|---|---|
| `from` | length | — (always present) | where the region starts, along the location line from the start junction |
| `to` | length | — (always present) | where it ends |
| `bottom` | length | — (always present) | the height of its bottom edge above the wall's base elevation |
| `top` | length | — (always present) | the height of its top edge |
| `material` | reference to a material | — (always present) | its material |

A wall's `finishes`, its face finishes and their regions MUST have exactly the members of their tables, each of the type its table gives: a region's `from`, `to`, `bottom` and `top` MUST NOT be negative. {#FS-CORE-18.5.1 MUST}

A region's `to` MUST be greater than its `from`, and its `top` greater than its `bottom`. {#FS-CORE-18.5.2 MUST}

A region MUST NOT extend beyond its wall: its `to` MUST NOT exceed the length of the wall's location line, and its `top` MUST NOT exceed the wall's top elevation minus its base elevation. {#FS-CORE-18.5.3 MUST NOT}
As for openings (7.3), the test of the length is exact: `to² ≤ dx² + dy²`.

Two regions of one face MUST NOT overlap: no point may lie strictly inside both. {#FS-CORE-18.5.4 MUST NOT}
Two regions may share an edge, so a band of tile can sit on a band of paint.

A region is measured on the wall, not on the face: the face's own ends, where it meets other walls
(5.7), are where the wall's rectangle is cut, and a region that reaches past them is cut with it.
An opening in the wall is cut out of a region as it is out of the face; a region is a finish, never
a hole.

> [!example] The backsplash
> A kitchen counter runs along the 3 m wall `W2`, whose right face faces the kitchen. The kitchen is
> painted; between the counter at 36 inches and the cabinets at 54 inches, the wall is tiled with
> a 12-inch tile:
> ```json
> "rooms": { "KIT": { "level": "L1", "anchor": [1920000, 1280000], "function": "kitchen", "wallFinish": "PAINT" } },
> "walls": { "W2": { "level": "L1", "start": "J2", "end": "J3", "type": "WT",
>                    "finishes": { "right": { "regions": [
>                      { "from": 0, "to": 3840000, "bottom": 1170432, "top": 1755648, "material": "TILE" } ] } } } },
> "materials": { "TILE": { "color": "#d8d4cc", "roughness": 300,
>                          "texture": { "asset": "TILE-PHOTO", "size": [390144, 390144] } } }
> ```

## 18.6 Resolving finishes

A wall's side **faces** a room when the room's face (6.3) lies on that side of the wall's location
line: when one of the half-edges that bound the face (6.1) is the wall taken from its start to its
end, the face is on the wall's left; taken from its end to its start, on its right. Each side of a
wall bounds exactly one face of its level's plane graph, which may be a room's, an unanchored face,
or the outside; a wall inside a room, with a free end, faces that room on both sides.

The finish of each surface is resolved in this order, the first that applies winning:

| Surface | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| a point of a wall's face inside one of its regions | the region's `material` | | | |
| any other point of the face | the face finish's `material` | the `wallFinish` of the room the face faces | the `material` of the wall's outermost effective layer on that side — its first for `"left"`, its last for `"right"` (8.3) | none |
| a room's floor | the room's `floorFinish` | none | | |
| a room's ceiling | the room's `ceilingFinish` | none | | |

So a room's finishes are inherited by every face that faces it; a face's own `material` overrides
the room's on that face alone; a region overrides both on its rectangle; and a face that faces no
room — the outside of an exterior wall — shows its own `material`, or else what its assembly is
made of, its siding or its plaster.

A deriver MUST derive the finishes of every valid document: for each room, its floor's and its ceiling's finish, when it has one; and for each side of each wall whose finish resolves to a material or that has regions, the room it faces, if any, the material that finishes the rest of the face, if any, where that material comes from, and the face's regions. {#FS-CORE-18.6.1 MUST}

A derived face lists its regions as the wall's face finish lists them: a region names its own
material, so resolving it adds nothing, and what a renderer needs — the face's material, with the
regions drawn over it — is all there. `source` is `"face"`, `"room"` or `"layer"`: the column of
the table that the face's material came from.

## 18.7 Related

FLR-REQ-116 (PBR metallic-roughness materials with a real-world tile size), FLR-REQ-118 (room-driven
finishes inherited by bounding faces, with face and region overrides), FLR-REQ-125 (assets by
relative path, media type and SHA-256), FLR-REQ-166 (an external asset is warned as not portable),
FLR-ADR-002 (derived, not drawn), FLR-ADR-004 (exact integers), FLR-ADR-027 (Core 0.3). Chapters 5
(walls and their sides), 6 (rooms and their faces), 8 (materials and assets), 13 (facing vectors),
15 (floors and ceilings) and Annex A (`IfcMaterial`, `IfcSurfaceStyle`, `IfcSurfaceStyleRendering`,
`IfcImageTexture`, `IfcCovering`).

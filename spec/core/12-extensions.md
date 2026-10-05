# 12. Extensions

Core is deliberately small (FLR-ADR-001). Furniture, appliances, electrical, plumbing and every
other building system enter Floorspec as **extensions**: named, versioned specifications of their
own, each with a schema and a conformance suite, listed in a public registry (FLR-ADR-007).
Section 1.6 gives the rules every document follows — names, `extensionsUsed`,
`extensionsRequired`, required and optional extensions. This chapter defines the rest: how a
document declares an extension, the registry entries that describe extensions to a validator, how
extensions depend on each other, the elements extensions add and the fallbacks that keep those
elements visible to software that has never heard of them.

## 12.1 Declarations

Each member of `extensionsUsed` declares one extension. Its value is either a **version string**,
as in 0.1, or a **declaration object**:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `version` | version string (1.6.7) | — (always present) | the version of the extension the document targets |
| `schema` | an absolute URI whose scheme is `https` and which has an authority | absent | where the extension's JSON Schema for that version is published |

```json
"extensionsUsed": {
  "EXT_acoustics": "1.2",
  "FS_furniture": { "version": "0.3.0", "schema": "https://d3cloud.io/floorspec/schema/ext/FS_furniture/0.3.0/furniture.schema.json" }
}
```

Every value in `extensionsUsed` MUST be a version string or a declaration object, and a declaration object MUST have a `version` and no member but `version` and `schema`. {#FS-CORE-12.1.1 MUST}

A declaration's `schema` MUST be an absolute `https` URI with an authority, as an asset's `uri` is (8.6). {#FS-CORE-12.1.2 MUST}

A reader MUST treat a declaration object exactly as the version string of its `version` member: the `schema` member never changes what a document means. {#FS-CORE-12.1.3 MUST}
The two forms are one declaration written two ways, so the canonical form writes a declaration
object without a `schema` as its version string (9.2), and the object form only when `schema` is
present.

A reader MAY use a declaration's `schema` to validate the extension's data. {#FS-CORE-12.1.4 MAY}
A reader never needs it to read core data, and never needs a network to read a document.

## 12.2 Registry entries and known extensions

The registry (`registry/` in the standard's repository) holds a **registry entry** for each
extension, at `registry/<name>/extension.json`. An entry describes one version of an extension:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `name` | extension name (1.6.1) | — (always present) | the extension |
| `version` | `<major>.<minor>.<patch>`, optionally with a `-prerelease` suffix (Semantic Versioning 2.0.0, without build metadata) | — (always present) | the version this entry describes |
| `status` | `"proposal"`, `"draft"`, `"releaseCandidate"` or `"ratified"` | — (always present) | where it is in the lifecycle (`registry/README.md`) |
| `schema` | an absolute `https` URI | — (always present) | where its JSON Schema for this version is published |
| `title` | string, 1–200 characters | absent | a human-readable name |
| `requires` | object: extension name → version range (12.3) | `{}` | the extensions it depends on |
| `kinds` | object: collection name → kind | `{}` | the kinds of element it adds (12.5), each named by the collection that holds it |
| `terms` | `{ "roomFunctions"?: array of terms }` | `{}` | the taxonomy terms it adds (4.2), without the extension-name prefix |
| `implementations` | array of `{ "name": string, "url": https URI }` | `[]` | software that implements it; a ratified extension lists at least two |

A **kind** in `kinds`:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `title` | string, 1–200 characters | absent | what it is: "Furniture piece" |
| `fallback` | `{ "asset"?: boolean, "symbol"?: boolean }` | `{}` | which optional parts of a fallback (12.6) every element of the kind carries: `true` requires that part |

The schema of a registry entry is `schema/registry/0.1/extension.schema.json`, published at
`https://d3cloud.io/floorspec/schema/registry/0.1/extension.schema.json`.

A validator is configured with a set of **known extensions**: the registry entries it has, which
may include several versions of one extension. A validator configured with none — the default,
and what the conformance suite assumes unless a test says otherwise — checks nothing that this
chapter defines in terms of known extensions. Known extensions are an input to validation, like
the extensions a reader implements (1.6.4); they never change what a document means, only what a
validator can check about it.

Known extensions MUST be a set of registry entries each matching the registry entry schema, no two with the same `name` and `version`, in which the relation "an entry of X requires Y" between extension names has no cycle. {#FS-CORE-12.2.1 MUST}

A validator configured with known extensions that break 12.2.1 MUST report the diagnostic `FS-CFG-001`, and no other diagnostic, for every document. {#FS-CORE-12.2.2 MUST}
Such a validator cannot judge a document against its configuration. `FS-CFG-001` is an error, so
it does not report the document as valid either (10.1).

A document **uses X at version v** when `extensionsUsed` declares X with version v. X is **known
at v** when a known entry has name X and a version equal to v, comparing versions as 12.3 does
(so `"1.2"` equals `1.2.0`). The rules of 12.3 and 12.4 apply to each extension a document uses at
a version at which it is known, and to no other.

## 12.3 Dependencies

An entry's `requires` maps an extension name to a **version range**: the versions of that
extension the entry's extension works with. Ranges use this grammar, where `version` is a full
`<major>.<minor>.<patch>` with an optional `-prerelease`:

```text
range      = set *( 1*" " "||" 1*" " set )
set        = comparator *( 1*" " comparator )
comparator = [ ">=" / ">" / "<=" / "<" / "=" / "^" / "~" ] version
```

A version satisfies a range when it satisfies every comparator of at least one of its sets. With
versions compared by Semantic Versioning 2.0.0 precedence (§11) — a prerelease is less than its
release, and `1.2` reads as `1.2.0`:

| Comparator | Satisfied by `x` when |
|---|---|
| `v` or `=v` | `x` equals `v` |
| `>=v`, `>v`, `<=v`, `<v` | `x` compares so with `v` |
| `~M.m.p` | `x >= M.m.p` and `x < M.(m+1).0` |
| `^M.m.p`, `M > 0` | `x >= M.m.p` and `x < (M+1).0.0` |
| `^0.m.p`, `m > 0` | `x >= 0.m.p` and `x < 0.(m+1).0` |
| `^0.0.p` | `x >= 0.0.p` and `x < 0.0.(p+1)` |

Unlike some package managers, Floorspec gives prereleases no special treatment: `2.0.0-rc.1`
satisfies `^1.0.0`, because it is less than `2.0.0`.

A validator MUST evaluate a version range exactly as this section defines. {#FS-CORE-12.3.1 MUST}

A document that uses X at a version at which X is known MUST also use every extension that X's entry `requires`. {#FS-CORE-12.3.2 MUST}

Each extension it requires MUST be used at a version that satisfies the range X's entry gives for it. {#FS-CORE-12.3.3 MUST}

Dependencies are declared by an extension's registry entry, never by the document: a document says
which extensions it uses, and the registry says what each of them needs. An extension that depends
on another does so because it uses the other's data — an electrical extension's circuits that
refer to a lighting extension's fixtures.

## 12.4 Kinds and terms of a known extension

When a document uses X at a version at which X is known, X's entry also says which collections and
terms X may use.

Every collection in X's top-level extension data (12.5) MUST be named in the `kinds` of X's entry. {#FS-CORE-12.4.1 MUST}

Every element in a collection of X MUST have the fallback parts that its kind in X's entry requires: an `asset` when the kind's `fallback.asset` is true, and a `symbol` when its `fallback.symbol` is true. {#FS-CORE-12.4.2 MUST}

Every extension term of X (4.2) in a room's or a program item's `function` MUST be listed in the `roomFunctions` of X's entry. {#FS-CORE-12.4.3 MUST}

## 12.5 Extension elements

An extension adds a **kind** of element by giving it a **collection** in its top-level extension
data, under the reserved member `collections`:

```json
"extensions": {
  "FS_furniture": {
    "collections": {
      "pieces": {
        "SOFA1": {
          "fallback": { "level": "L1", "box": { "min": [0, 0, 0], "max": [2133600, 914400, 838200] } },
          "host": { "mode": "free", "level": "L1", "position": [1280000, 640000], "rotation": 90000000 },
          "catalogue": "Bauhaus three-seat"
        }
      }
    },
    "style": "mid-century"
  }
}
```

`collections` maps a collection name — `^[a-z][A-Za-z0-9]*$` — to a collection: an object whose
member names are IDs and whose member values are **extension elements**. The rest of an
extension's top-level data, `style` above, is the extension's own. An extension element's ID
shares the document's single space of IDs (3.1.3).

An extension element is an object. Core defines six of its members; the extension defines the
rest, and core neither restricts nor reads them:

| Member | Type | Default | Meaning |
|---|---|---|---|
| `fallback` | fallback (12.6) | — (always present) | what to show when the extension is not implemented |
| `host` | host (13.3) | absent: the element is placed only by its fallback | what the element is placed on |
| `clearances` | object: envelope name → clearance envelope (13.5) | `{}` | the space it needs kept clear |
| `option` | reference to an option | absent: in no option | the option it is in (19.2); new in 0.3 |
| `name` | string, 1–200 characters | absent | a human-readable label |
| `extras` | object | `{}` | 1.7 |

Top-level extension data that has a `collections` member MUST have, as its value, an object whose member names are collection names and whose members are objects mapping IDs to extension elements. {#FS-CORE-12.5.1 MUST}

Every extension element MUST have a `fallback`, and its core members MUST have the types their tables give. {#FS-CORE-12.5.2 MUST}

The `collections` member has this meaning only in top-level extension data, and only in a document
that declares 0.2, 0.3 or 0.4 (1.2.8); extension data on an element is never searched for collections.
Extension elements are extension data: the canonical form never changes them (9.2), so a writer
that wants one hash for one meaning omits their default members itself. A reader that does not
implement an extension still finds its elements, checks their core members, and derives their
fallbacks, placements and clearances (1.6.9) — and nothing else.

## 12.6 Fallbacks

A **fallback** is what a reader without the extension shows: a box, and optionally a 3D model and
a 2D plan symbol.

| Member | Type | Default | Meaning |
|---|---|---|---|
| `level` | reference to a level | — (always present) | the level the element is on |
| `box` | box (13.2) | — (always present) | the space the element occupies, in its frame (13.1) |
| `asset` | reference to an asset | absent | a glTF 2.0 model of the element, in its frame, in metres |
| `symbol` | reference to an asset | absent | a 2D plan symbol, an image drawn to the footprint of `box` |

The **frame** of an extension element is its host's frame (13.1) when it has a `host`, and
otherwise the frame of its fallback's level. A hosted element's box therefore moves with its
host, and an unhosted one is placed in the level's own coordinates.

A fallback's `asset` MUST be an asset whose `mediaType` is `model/gltf-binary` or `model/gltf+json`, and its `symbol` an asset whose `mediaType` is `image/svg+xml` or `image/png`. {#FS-CORE-12.6.1 MUST}

For every extension element, a deriver derives its **fallback**: the element's extension and
collection, the fallback's level, and the footprint, bottom and top of its box in the element's
frame (13.2).

A deriver MUST derive the fallback of every extension element of a valid document as this section and 13.2 define. {#FS-CORE-12.6.2 MUST}

**Drawing a fallback** (new in 0.3). A reader that has never heard of an extension still draws its
elements, so where a fallback's model and symbol go is Core's to say, once, for every extension.
Both are placed in the element's frame (13.1), whose x axis is the element's **front** — the way it
faces: out of the wall for a `wallFace` host, its `rotation` for a `surface` or `free` host.

A fallback's model is in metres, with glTF 2.0's +Y up. It is placed by the mapping of 2.3, which
converts Floorspec's axes to glTF's, applied to the frame instead of the plan: the point
`(X, Y, Z)` of the model's default scene is the local point

```text
p = 1,280,000 · X        q = −1,280,000 · Z        r = 1,280,000 · Y
```

of the element's frame. So the model's origin is the frame's origin, its +X is the element's front,
+Y is up, and −Z is the element's left (+y). The model is drawn as it is, never stretched to the
box: the box is what a deriver and a rule measure.

> [!note] Which way a model faces
> glTF 2.0 suggests that the front of an asset face +Z. Floorspec places a model by 2.3 instead,
> because the same conversion then takes an element and the house around it to glTF, and an
> exporter writes a placed element as a node whose rotation is its facing alone. A model made to
> face +Z is used by putting its scene under one node rotated by +90° about +Y — the quaternion
> `[0, √½, 0, √½]` — which turns its +Z to +X and its +X to −Z.

A fallback's symbol is drawn on the footprint of its box (13.2) as seen from above, with the
element's front along the bottom edge of the image, so that it reads as a person standing in front
of the element sees its plan, and is never mirrored. The whole image — an SVG's `viewBox`, a PNG's
grid of pixels — is stretched to the footprint:

| Corner of the image | Local point of the box |
|---|---|
| top left | `(box.min.x, box.min.y)` |
| top right | `(box.min.x, box.max.y)` |
| bottom right | `(box.max.x, box.max.y)` |
| bottom left | `(box.max.x, box.min.y)` |

Software that draws a fallback's model SHOULD place it in the element's frame exactly by this mapping. {#FS-CORE-12.6.3 SHOULD}

Software that draws a fallback's symbol in plan SHOULD draw it on the footprint of the element's box exactly as this table defines. {#FS-CORE-12.6.4 SHOULD}
As with a texture (18.3.1), where a renderer puts a model or an image is not a value a deriver
reports, so the suite cannot test it; an exporter's placement of a fallback model can be, and is
tested with export (FLR-T-9.2).

## 12.7 What an extension may and may not do

An extension may add members to core elements (under `extensions.<name>` on the element), add
kinds of element (12.5) and add taxonomy terms (4.2). Every kind it adds carries a fallback. An
extension never changes what core data means: a reader that ignores an optional extension derives
exactly what a reader that implements it derives from the core data. A building system that
needs to change core geometry — a wall that a plumbing chase thickens — does so by editing the
core data, never by reinterpreting it.

Extensions depend on each other through version ranges and never in a cycle (12.2.1, 12.3). Their
lifecycle — Proposal, Draft, Release Candidate, Ratified — and the requirements for ratification
— a schema, a conformance suite, and two independent implementations — are in
`registry/README.md`.

## 12.8 Related

FLR-ADR-001 (a tiny core; building systems are first-party `FS_` extensions), FLR-ADR-007 (the
extension model), FLR-ADR-018 (schemas at immutable, versioned URLs).

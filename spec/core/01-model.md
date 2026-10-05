# 1. Document model

## 1.1 The document

A Floorspec document is a JSON object. Its members are the version declaration, the project, an
optional site, the element collections, the program, the extension declarations and extras.

| Member | Type | Default | Defined in |
|---|---|---|---|
| `floorspec` | version string | — (present in every document) | 1.2 |
| `project` | Project | — (present in every document) | 1.8 |
| `site` | Site | absent: the project has no site | 1.8 |
| `buildings` | collection of Building | `{}` | 1.8 |
| `levels` | collection of Level | `{}` | 1.8 |
| `junctions` | collection of Junction | `{}` | 5.1 |
| `walls` | collection of Wall | `{}` | 5.2 |
| `separators` | collection of Separator | `{}` | 5.2 |
| `openings` | collection of Opening | `{}` | 7.1 |
| `rooms` | collection of Room | `{}` | 6.5 |
| `slabs` | collection of Slab | `{}` | 6.7 |
| `roofs` | collection of Roof | `{}` | 16.1 |
| `types` | collection of Type | `{}` | 8.1 |
| `materials` | collection of Material | `{}` | 8.5 |
| `assets` | collection of Asset | `{}` | 8.6 |
| `program` | Program | `{}` | 11.1 |
| `extensionsUsed` | object: extension name → version, or declaration (12.1) | `{}` | 1.6, 12.1 |
| `extensionsRequired` | array of extension names | `[]` | 1.6 |
| `extensions` | object: extension name → extension data | `{}` | 1.6, 12.5 |
| `extras` | object | `{}` | 1.7 |

A document MUST be a JSON object. {#FS-CORE-1.1.1 MUST}

A document MUST NOT contain a top-level member that the table above does not list. {#FS-CORE-1.1.2 MUST NOT}
New kinds of data enter a document through extensions (1.6) or extras (1.7), never as new
top-level members; this is what lets a reader tell an unknown extension from a malformed document.

## 1.2 Version declaration

The `floorspec` member declares the version of Floorspec Core the document targets, as
`"<major>.<minor>"`. Patch releases of the specification are editorial and are not declared.

A document that targets this draft MUST declare `"floorspec": "0.3"`. {#FS-CORE-1.2.5 MUST}

A reader MUST reject a document that declares a version the reader does not implement, with the
diagnostic `FS-DOC-001`. {#FS-CORE-1.2.2 MUST}

A reader that implements this draft MUST also read a document that declares `"0.1"` or `"0.2"`: it MUST apply the schema of the draft the document declares to it at the schema tier, and otherwise read it as a 0.3 document in which every member that a later draft than the one it declares adds is absent. {#FS-CORE-1.2.6 MUST}

The members 0.2 added are the top-level `program` (11.1), a room's `brief` (11.3), the
declaration object in `extensionsUsed` (12.1), a door or window type's `clearances` (13.5) and the
`collections` member of top-level extension data (12.5). The members 0.3 adds are a door or window
type's `operation` and `clearOpening` (8.4), an opening's `clearOpening` (7.1), a level's
`floorThickness` and `ceilingHeight` (1.8), a room's `floor` and `ceiling` (15.1, 15.2) and a slab's
`purpose` (6.7). Each is optional, and its absence means what a document of an earlier draft means
without it: an empty program, a room that fulfils no program item, a version string, no
clearances, extension data that core does not look inside, an operation that is not declared, no
declared clear opening, a floor at its level's elevation with no declared thickness, a flat
ceiling at its level's height, and a slab whose purpose is not stated.
The `roofs` collection (chapter 16) is new in 0.3 too: its absence means no roof, and a reader of
this draft derives an empty set of roofs for a document of any draft. So reading an earlier document this way is exact: a document valid under 0.2, read by a validator
configured with the same known extensions (12.2), is valid under 0.3 with the same diagnostics,
the same derived values, the same canonical form and the same content hash; and a document valid
under 0.1, read by a validator configured with no known extensions, is valid under 0.3 with the
same diagnostics, the same derived values (with nothing derived for a program, hosts, clearances
or clear openings), the same canonical form and the same content hash — except for circulation
(chapter 14), which needs no new member: it is derived for the document's rooms, and its lints
are reported when the plan has doors but no way in. Floors, ceilings and slabs (chapter 15) need
no new member either: a reader of this draft derives them for a document of any draft, from the
defaults — so a valid 0.2 or 0.1 document read as 0.3 also derives its rooms' floors and ceilings
and its slabs' bounding geometry, and every value its own draft derives is unchanged, the
placements of `surface` hosts included (15.6), and it has no roofs. In a 0.1 document, top-level extension data is
opaque, as 0.1 says, even where it has a member named `collections`. Core 0.1's schema rejects
every member and collection 0.2 and 0.3 add, and Core 0.2's every one 0.3 adds, so a document that declares
`"0.1"` or `"0.2"` and uses one is invalid (`FS-SCH-001`).

> [!note] Versioning policy
> Floorspec follows Semantic Versioning. While the major version is 0, any draft may change
> anything, and a reader implements the drafts it names. From 1.0, a minor version will only add
> optional members and new extension points, so a 1.x reader can read every 1.y document with
> y ≤ x; a major version will ship a normative migration from the previous major, and a reader
> of a major will read the previous one by migrating it on load.

## 1.3 Spatial structure

A document describes one **project**. The project may have a **site**, and has zero or more
**buildings** — a house, a detached garage and an accessory dwelling are three buildings. Each
building has **levels**. Every element that sits on a plan belongs to exactly one level by
reference; elements are never nested inside their level.

```text
Project ─ Site (optional)
   └─ Building (1..n) ─ Level (1..n) ◄── junctions, walls, separators, rooms, slabs, roofs (by "level")
                                           openings (by their wall)
```

Every level MUST reference a building. {#FS-CORE-1.3.1 MUST}

Every junction, wall, separator, room and slab MUST reference a level. {#FS-CORE-1.3.2 MUST}

An opening has no level of its own: it is on its host wall's level (chapter 7).

## 1.4 Collections and elements

A **collection** is a JSON object whose member names are element IDs and whose member values are
elements. The ID of an element is its member name; an element does not repeat its ID inside
itself, and its kind is given by its collection (and, in `types`, by its `kind` member).

An element MUST NOT contain a member that its kind's table in this specification does not list. {#FS-CORE-1.4.1 MUST NOT}

Every object this specification defines that is not an element — the project, the site and its
`location`, a wall's `base` and `top`, a junction's `join`, a layer, a texture — MUST NOT contain a
member that its table does not list. The content of `extras` and of extension data is not
restricted. {#FS-CORE-1.4.3 MUST NOT}

Every member MUST have the type, and lie in the range, that its table and its section give. {#FS-CORE-1.4.4 MUST}

A string that a table limits to a number of characters is measured in Unicode code points.

Every element MAY carry these members, in addition to those of its kind: {#FS-CORE-1.4.2 MAY}

| Member | Type | Default | Meaning |
|---|---|---|---|
| `name` | string, 1–200 characters | absent | a human-readable label; never read by derivation |
| `extensions` | object: extension name → extension data | `{}` | 1.6 |
| `extras` | object | `{}` | 1.7 |

## 1.5 Defaults

Every member that a document may omit has a **default**, given in its table. A default is either
**constant** — a fixed value, such as `"center"` — or **derived** from other values in the
document, such as a wall's top, which follows its level's height.

A reader MUST treat an absent member exactly as if it were present with its default value. {#FS-CORE-1.5.1 MUST}

A writer MAY omit a member whose value equals its constant default. {#FS-CORE-1.5.2 MAY}
A member whose default is derived is different: omitting it binds it to the values it derives
from, so a writer that omits a present member with a derived default changes the document's
meaning. The canonical form (9.2) omits constant defaults only.

## 1.6 Extensions

Extensions add data that core does not define: new members on core elements, new kinds of
element, and new taxonomy terms (4.2). They are how building systems, furniture and appliances
enter Floorspec (FLR-ADR-001, FLR-ADR-007).

An extension name is a prefix and a name joined by an underscore: `FS_electrical` (an official,
ratified extension), `EXT_acoustics` (a multi-implementer extension) or a vendor prefix of 2 to 8
capitals or digits reserved in the registry.

- `extensionsUsed` maps the name of every extension the document uses to the version of that
  extension it targets — as a version string, or as a declaration object that also names the
  extension's schema (12.1).
- `extensionsRequired` lists the extensions a reader must implement to read the document
  correctly. A document lists an extension here when ignoring it would change what the core data
  means; otherwise the extension is optional.
- An element's `extensions` member, and the document's top-level `extensions` member, map an
  extension name to that extension's data. Top-level extension data may hold the extension's own
  kinds of element, in its `collections` member (12.5).

Every extension name MUST match the pattern `^(FS|EXT|[A-Z0-9]{2,8})_[A-Za-z0-9]+$`. {#FS-CORE-1.6.1 MUST}

Every version in `extensionsUsed` MUST match `^\d+\.\d+(\.\d+)?(-[0-9A-Za-z.-]+)?$`. {#FS-CORE-1.6.7 MUST}

`extensionsRequired` MUST NOT name an extension twice. {#FS-CORE-1.6.8 MUST NOT}

Every name in `extensionsRequired` MUST also be a member of `extensionsUsed`. {#FS-CORE-1.6.2 MUST}

Every member name of an `extensions` object, at the top level or on an element, MUST be a member
of `extensionsUsed`. {#FS-CORE-1.6.3 MUST}

A reader MUST reject a document whose `extensionsRequired` names an extension the reader does not
implement, with the diagnostic `FS-DOC-002`. {#FS-CORE-1.6.4 MUST}

A reader MUST accept a document that uses optional extensions it does not implement, and MUST
NOT let their data affect anything it derives, except the core members of their extension
elements — `fallback`, `host` and `clearances` (12.5) — from which it derives exactly what
chapters 12 and 13 define, and nothing else. {#FS-CORE-1.6.9 MUST}

A writer MUST preserve the data of every extension it does not implement, unchanged. {#FS-CORE-1.6.6 MUST}

> [!note] What an extension may and may not do
> An extension's own specification defines its schema, its version and its conformance tests. It
> may add members to core kinds, add kinds of its own (under its name in the top-level
> `extensions` object, 12.5) and add taxonomy terms. Every kind it adds carries a fallback — a
> bounding box, and optionally a glTF asset and a 2D symbol — so that a reader without the
> extension can still show that something is there. It never changes the meaning of core data.
> Chapter 12 defines the mechanism in full: declarations, registry entries and dependencies,
> extension elements and fallbacks. The lifecycle (Proposal, Draft, Release Candidate, Ratified)
> is described in `registry/`.

## 1.7 Extras

`extras` is an object for application-specific data that no specification defines — a viewer's
camera position, an importer's original file name. The project, the site, every element and the
document itself may carry `extras`. Their content is any JSON.

A deriver MUST NOT let `extras` affect any derived value. {#FS-CORE-1.7.1 MUST NOT}

A writer MUST preserve `extras` it does not itself manage, unchanged. {#FS-CORE-1.7.2 MUST}

Anything that changes what the building is belongs in core or an extension, never in `extras`.

## 1.8 Project, site, buildings and levels

**Project.**

| Member | Type | Default | Meaning |
|---|---|---|---|
| `name` | string, 1–200 characters | — (always present) | the project's name |
| `description` | string, up to 2000 characters | absent | free text |
| `extras` | object | `{}` | 1.7 |

**Site.** A project with no site yet — a house designed before a lot is chosen — omits `site`.

| Member | Type | Default | Meaning |
|---|---|---|---|
| `trueNorth` | angle (2.4) | `0` | the angle from project north (+Y) to true north, counter-clockwise positive |
| `location` | `{ "latitude": angle, "longitude": angle }`, both always present | absent | WGS 84, in microdegrees |
| `boundary` | polygon (2.6) | absent | the lot line, in project coordinates |
| `extras` | object | `{}` | 1.7 |

`trueNorth` MUST be greater than −180,000,000 and at most 180,000,000. {#FS-CORE-1.8.1 MUST}

A `latitude` MUST lie in [−90,000,000, 90,000,000] and a `longitude` in (−180,000,000, 180,000,000]. {#FS-CORE-1.8.2 MUST}

**Building.**

| Member | Type | Default | Meaning |
|---|---|---|---|
| `name`, `extensions`, `extras` | | | 1.4 |

**Level.**

| Member | Type | Default | Meaning |
|---|---|---|---|
| `building` | reference to a building | — (always present) | the building the level is in |
| `elevation` | length | — (always present) | the level's datum: the height of its finished floor above project zero |
| `height` | length | — (always present) | floor-to-floor height: the default top of the level's walls (5.9) |
| `floorThickness` | length | absent: not declared | the thickness of its rooms' floors, unless a room's `floor` says otherwise (15.1) |
| `ceilingHeight` | length | absent: its `height` | the height of its rooms' ceilings above its elevation, unless a room's `ceiling` says otherwise (15.2) |
| `name`, `extensions`, `extras` | | | 1.4 |

A level's `height` MUST be greater than zero. {#FS-CORE-1.8.3 MUST}

A level's `floorThickness` and `ceilingHeight`, when present, MUST be greater than zero. {#FS-CORE-1.8.4 MUST}

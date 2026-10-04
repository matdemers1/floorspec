# 0. Conventions

> [!warning] Floorspec Core 0.1 — Draft
> This is a working draft. It carries no compatibility promise: a later 0.x draft may change any
> part of it. Floorspec stays 0.x until the 1.0 criteria are met (FLR-ADR-017).

Floorspec Core defines a document that describes a building as code: its levels, the walls on a
junction graph, the rooms that walls enclose, the openings hosted on walls, and the types and
materials they use. It defines what makes a document valid, the exact geometry a conformant tool
derives from it, and the one byte sequence that every conformant writer produces for it.

## 0.1 Normative language

The key words `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT` and `MAY` in this specification are to be
interpreted as described in BCP 14 (RFC 2119, RFC 8174) when, and only when, they appear in
capitals, as shown here. Floorspec does not use `SHALL`, `REQUIRED`, `RECOMMENDED` or `OPTIONAL`.

Every sentence that uses one of those keywords is a *normative statement* and ends with a tag
giving its stable identifier and level, for example `{#FS-CORE-5.3.1 MUST}`. The identifier is
`FS-CORE-<chapter>.<section>.<n>`. An identifier is never reused, including after the statement it
named is removed.

Every statement at level `MUST` or `MUST NOT` is exercised by at least one test in the conformance
suite (`conformance/core/0.1/`), and the build that publishes this specification fails if one is
not. Tables, figures and informative callouts are normative only where a tagged statement says so.

## 0.2 Conformance classes

Floorspec Core 0.1 places requirements on five kinds of thing:

| Class | What it is | What it must do |
|---|---|---|
| **Document** | a JSON text claiming to be Floorspec | satisfy every requirement on documents (chapters 1–8) |
| **Reader** | software that loads documents | apply defaults and the version and extension rules (1.2, 1.5, 1.6) |
| **Writer** | software that produces documents | produce valid documents; preserve what it does not understand (1.6, 1.7) |
| **Canonicalizer** | software that produces the canonical form | produce exactly the bytes of chapter 9 |
| **Validator** | software that reports validity | report the diagnostics of chapter 10 |
| **Deriver** | software that computes geometry | produce exactly the derived values of chapters 5–7 |

One program is usually several of these. The conformance suite tests each class separately; the
reference implementation, D3 Floorspec, claims all of them.

## 0.3 Notation

- A **JSON integer** is a JSON number written with neither a fraction nor an exponent. A
  **length** is a JSON integer number of base units (chapter 2). A **point** is `[x, y]`, two
  lengths. Code-like names (`walls`, `justification`) are JSON member names.
- **Exact value** means the mathematically exact real number. Derived values are defined as exact
  values and then rounded once, as chapter 2 specifies; no intermediate rounding is permitted.
- `round(v)` is rounding of a real number to the nearest integer, ties to even.
- An **element** is a member of one of the document's collections (1.4). Its **ID** is its member
  name in that collection.
- **Left** and **right** of a directed line are as seen from above (from +Z), looking along the
  line.

## 0.4 References

Normative: RFC 8259 (JSON), RFC 8785 (JSON Canonicalization Scheme), RFC 6901 (JSON Pointer),
FIPS 180-4 (SHA-256), JSON Schema 2020-12, BCP 14 (RFC 2119, RFC 8174), Semantic Versioning
2.0.0, RFC 3986 (URI).

Informative: ISO 16739-1:2024 (IFC 4.3) and IFC4 ADD2 TC1, for the mapping in Annex A.

## 0.5 What this draft does not yet define

Floorspec Core 0.1 is the walls-and-rooms draft. These are reserved for later drafts and a 0.1
document cannot contain them:

- roofs and stairs (their collections, `roofs` and `stairs`, are reserved names);
- design options (`optionSets`, and option membership on elements);
- arc walls (core 0.1 walls are straight);
- derivation of floors, ceilings and 3D geometry, which is not normative in any 0.x draft yet;
- finish overrides on a wall face or a region of one;
- the packaged `.floorspec` form (a ZIP of `model.json` and `assets/`);
- edit operations, which are a separate specification, Floorspec Ops.

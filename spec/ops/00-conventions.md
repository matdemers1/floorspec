# 0. Conventions

> [!warning] Floorspec Ops 0.1 — Draft
> This is a working draft with no compatibility promise. It operates on Floorspec Core 0.1
> documents. Floorspec Ops is versioned independently of Core (FLR-ADR-008).

Floorspec Core says what a building *is*. Floorspec Ops says how one **changes**: a small set of
**primitive** operations with exact semantics, **composite** operations defined as sequences of
primitives, a **reference grammar** that lets a person or an agent say "the north wall of R5" or
"2' 6\"" instead of computing coordinates, and a **transaction** that either commits a whole
batch or changes nothing. Every editor binding — the D3 Floorspec web app, its MCP server, a CLI —
is a binding of these operations, so two tools that implement Floorspec Ops make the same edit the
same way, to the byte.

## 0.1 Normative language

The key words `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT` and `MAY` are used as in Floorspec Core
§0.1, and every normative statement ends with a tag `{#FS-OPS-<chapter>.<section>.<n> LEVEL}`.
Every `MUST` and `MUST NOT` is exercised by the conformance suite in `conformance/ops/0.1/`.

## 0.2 Conformance

An **applier** is software that applies a batch of operations to a Floorspec Core document. It is
the only conformance class of Floorspec Ops. An applier is tested by giving it a document A and a
batch, and comparing what it returns — a committed document B in canonical form, or a rejection
with diagnostics — with the expected result.

Terms from Floorspec Core keep their meanings: element, collection, junction, edge, face, room
polygon, canonical form, content hash, diagnostic.

## 0.3 Not in this draft

Operations on roofs, stairs, design options and extension data; dimension locks other than the
two of chapter 6; operations that edit several documents at once.

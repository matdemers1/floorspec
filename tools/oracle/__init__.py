"""The Floorspec Core 0.1 oracle (FLR-ADR-009).

An exact, independent implementation of what Floorspec Core 0.1 says a validator, a deriver and a
canonicalizer produce for a document. It exists to compute and cross-check the expected outputs
of the conformance suite; it is written from the specification alone, never from an engine, and
uses only the Python standard library.

    python3.13 -m tools.oracle <test-dir | input.json>      print the expected result
    python3.13 -m tools.oracle.regenerate                   re-verify the whole suite

Modules:
    jsonparse   strict RFC 8259 / I-JSON parsing (9.1): FS-JSON-001/002/003
    canon       constant-default omission, canonical form (9.2), RFC 8785 and the content hash (9.3)
    surd        exact numbers of the form a + b*sqrt(m) + c*sqrt(n), exact sign and rounding (2.2)
    plane       exact integer plane geometry: orientation, segments, polygons
    schema      a hand-written structural check standing in for the JSON Schema tier (FS-SCH-001)
    derive      face lines, corner sequences, face ends, joins, fills, elevations, faces, rings,
                anchors, areas and openings (chapters 5-7)
    floors      floors, flat, tray and vaulted ceilings, slabs and surface hosts on them (Core 0.3, chapter 15)
    validate    the tiers and the order of evaluation of chapter 10, and the lints
    ext         the official extensions (registry/), each written from its own specification:
                FS_electrical, FS_plumbing, FS_mechanical and FS_lowvoltage 0.1.0
"""

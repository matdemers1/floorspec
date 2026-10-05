"""The Floorspec Ops oracle (FLR-ADR-009), for Ops 0.1 and Ops 0.2.

An exact, independent applier: it applies an apply request to a Floorspec Core document exactly
as the draft of Floorspec Ops it is run as says an applier does - Ops 0.1 as published at
3bf4f35, on Core 0.1 documents, or Ops 0.2, on Core 0.2 (and 0.1) documents - and returns the
result object of Ops 1.3. Like the Core oracle it extends, it is written from the specification
alone and uses only the Python standard library; every decision is made with integer, Fraction or
Surd arithmetic.

    python3.13 -m tools.oracle.ops <test-dir> [--ops 0.1|0.2]   print the result for one test
    python3.13 -m tools.oracle.regenerate                       re-verify every suite (Core and Ops)

Modules:
    version     the drafts, as profiles: OPS_01 (the default) and OPS_02
    space       the one space of IDs: elements, and in 0.2 program items and extension elements
    errors      the FS-OPS diagnostics and the exception that carries them
    request     the shape of an apply request (1.1.1): what FS-OPS-001 rejects
    refs        the reference grammar's strings: lengths, directions, the point, vector and
                position forms (3.1, 3.2, 3.5), and in 0.2 areas (3.6)
    faces       the faces of a level in the working copy, and when a level has none to give (3.4)
    select      resolving references against the working copy: selectors, sides, points (ch. 3)
    normalize   merging junctions, snap rounding and join cleanup (ch. 5)
    engine      the transaction (1.2): expand, apply, normalize, validate, locks, the result,
                minting (1.5) and the inverse (1.6)
    suite       verifying conformance/ops/0.1 and 0.2 test directories, each with its draft
"""

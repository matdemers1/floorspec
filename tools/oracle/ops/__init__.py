"""The Floorspec Ops 0.1 oracle (FLR-ADR-009).

An exact, independent applier: it applies an apply request to a Floorspec Core document exactly
as Floorspec Ops 0.1 says an applier does, and returns the result object of Ops 1.3. Like the
Core oracle it extends, it is written from the specification alone and uses only the Python
standard library; every decision is made with integer, Fraction or Surd arithmetic.

    python3.13 -m tools.oracle.ops <test-dir>       print the result for one test
    python3.13 -m tools.oracle.regenerate           re-verify both suites (Core and Ops)

Modules:
    errors      the FS-OPS diagnostics and the exception that carries them
    request     the shape of an apply request (1.1.1): what FS-OPS-001 rejects
    refs        the reference grammar's strings: lengths, directions, the point, vector and
                position forms (3.1, 3.2, 3.5)
    faces       the faces of a level in the working copy, and when a level has none to give (3.4)
    select      resolving references against the working copy: selectors, sides, points (ch. 3)
    normalize   merging junctions, snap rounding and join cleanup (ch. 5)
    engine      the transaction (1.2): expand, apply, normalize, validate, locks, the result,
                minting (1.5) and the inverse (1.6)
    suite       verifying conformance/ops/0.1 test directories
"""

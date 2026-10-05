"""The Floorspec Rules 0.1 oracle: an exact evaluator of rule packs, written from spec/rules/ alone.

    python3.13 -m tools.oracle.rules <test-dir>     one rules test's expected output, as the oracle computes it

evaluate.evaluate(document, registry, request) returns the report of spec/rules chapter 9;
evaluate.call_measures(document, registry, calls, units) the measure results of 4.7.
"""

# conformance/ops

The conformance suite of Floorspec Ops, one directory per draft:

- `0.2/` tests Ops 0.2, the current text, and is the suite `pnpm coverage` gates it against. It
  holds every 0.1 test re-targeted to 0.2 - same group, same number, the same Core 0.1 document A,
  covering `FS-OPS-1.1.2` and `FS-OPS-4.5.3` where the 0.1 test covered the retired `1.1.1` and
  `4.5.1` - and, after them in each group, the tests of what 0.2 adds: `composites/040` to `063`
  (relative `moveOpening` and `addLevel`), and the groups `program` (items, adjacencies, briefs,
  areas, the bubble diagram) and `hosting` (placing and moving extension elements, what removal
  takes, hosted elements following their walls and split walls), with more in `ids`, `locks`,
  `inverse`, `references` and `transactions`, mostly on Core 0.2 documents.
- `0.1/` tests Ops 0.1 against Core 0.1 documents, exactly as it was published at `3bf4f35`, so
  that a 0.1 applier can still be tested against it; CI fails if it changes.

The layout of a test, what expected.json holds and how the suites are checked are in
[`../README.md`](../README.md#floorspec-ops).

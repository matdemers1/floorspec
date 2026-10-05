# US starter type library

A non-normative library of common US wall, door and window types, and the materials their layers
use, as Floorspec Core 0.3 types and materials ready to embed in a document (Core 8.1). Nothing in
Floorspec requires it.

| Version | Core | Published at | Items |
|---|---|---|---|
| [0.1.0](0.1.0/README.md) | 0.3 | `https://d3cloud.io/floorspec/library/us-starter/0.1.0/` | 11 wall types, 15 door types, 25 window types, 10 materials |

## URIs

```text
https://d3cloud.io/floorspec/library/us-starter                          the library: a document's source.library
https://d3cloud.io/floorspec/library/us-starter/<version>/               one version
https://d3cloud.io/floorspec/library/us-starter/<version>/index.json     every item, as embedded, with its embed batch
https://d3cloud.io/floorspec/library/us-starter/<version>/items/<item>.json
https://d3cloud.io/floorspec/library/us-starter/<version>/README.md
https://d3cloud.io/floorspec/library/us-starter/<version>/SHA256SUMS
```

Each version's directory here is published as it is, at its URL, as the schemas are. **A published
version never changes**: a change to an item, however small, is a new version in a new directory,
and the old one stays where it is, so a document's `source` always names exactly what it copied.

## How a document uses it

A document never refers to the library by URL (Core 8.1): it copies each item it uses into its own
`types` or `materials` collection, with the item's `source` — `library`, `version`, `item`. Each
version's README says how, with the Ops batch each item publishes, how embedding twice adds nothing,
and how a newer version is adopted by an explicit edit.

**Clear openings are generic.** Every door's and window's `clearOpening` is the library's own
generic value, not a manufacturer's: replace it with your product's declared values (Core 8.4, 7.2).
`index.json` says so in its `clearOpenings` member.

## Making it

Every file of the current version is written by [`tools/us-library.ts`](../../tools/us-library.ts)
from its tables, the same bytes every time:

```sh
pnpm library:us          # write library/us-starter/<current version>/
pnpm library:us:check    # the current version is exactly what the script writes, and every file of
                         # every version matches its SHA256SUMS
```

To change the library, raise `VERSION` in the script, change its tables and run `pnpm library:us`:
the new version is written beside the old ones, which the check keeps as they were published.

The library uses no manufacturer's data and no building-code text or table. It is dedicated to the
public domain under CC0 1.0.

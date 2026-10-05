# Floorspec Core

The normative specification of the Floorspec document — **Draft 0.3: walls and rooms, the program, extensions, hosting and clearances, circulation, door and window operation and net clear openings**.

| Chapter | |
|---|---|
| [0. Conventions](00-conventions.md) | normative language, conformance classes, notation, what this draft does not define, changes from 0.2 and from 0.1 |
| [1. Document model](01-model.md) | the document, version, spatial structure, collections, defaults, extensions, extras |
| [2. Units, quantities and coordinates](02-units.md) | base unit, exact derivation and rounding, axes, angles, polygons |
| [3. Identity and references](03-identity.md) | IDs, references, level consistency |
| [4. Taxonomies](04-taxonomy.md) | room functions, extension terms, layer functions |
| [5. Walls](05-walls.md) | junctions, walls, separators, planarity, face lines, wedges, outlines, joins, heights |
| [6. Rooms](06-rooms.md) | faces, room polygons, anchors and identity, net area, slabs |
| [7. Openings](07-openings.md) | hosted openings, typed dimensions and clear openings, placement |
| [8. Types, materials and assets](08-types.md) | types and overrides, layers, door and window types, their operation and clear opening, materials, assets |
| [9. Serialization](09-serialization.md) | encoding, canonical form, content hash |
| [10. Validation and diagnostics](10-diagnostics.md) | tiers, diagnostics, order of evaluation, the catalogue, fixes |
| [11. The program](11-program.md) | program items, the adjacency graph, rooms that fulfil items, adjacent and connected rooms |
| [12. Extensions](12-extensions.md) | declarations, the registry and known extensions, dependencies, extension elements, fallbacks |
| [13. Hosting and clearances](13-hosting.md) | local frames, boxes, hosts and placement, clearance envelopes, the overlap measure |
| [14. Circulation](14-circulation.md) | the door graph, entries, reachable rooms, sleeping rooms reached through another |
| [A. IFC4 mapping](annex-ifc.md) | every core kind and its IFC4 entity |

Every normative statement ends with a tag such as `{#FS-CORE-5.3.1 MUST}`. `pnpm statements`
extracts them; `pnpm coverage` fails if a `MUST` or `MUST NOT` has no conformance test.

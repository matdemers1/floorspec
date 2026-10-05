# Floorspec Core

The normative specification of the Floorspec document — **Draft 0.4: walls and rooms, the program, extensions, hosting and clearances, circulation, door and window operation and net clear openings, floors, ceilings and slabs, roofs, stairs — straight, turning on landings or winders, and spiral — materials and finishes, design options, migration from earlier drafts, and arc walls**.

| Chapter | |
|---|---|
| [0. Conventions](00-conventions.md) | normative language, conformance classes, notation, what this draft does not define, changes from 0.3, from 0.2 and from 0.1 |
| [1. Document model](01-model.md) | the document, version, spatial structure, collections, defaults, extensions, extras |
| [2. Units, quantities and coordinates](02-units.md) | base unit, exact derivation and rounding, axes, angles, polygons |
| [3. Identity and references](03-identity.md) | IDs, references, level consistency |
| [4. Taxonomies](04-taxonomy.md) | room functions, extension terms, layer functions |
| [5. Walls](05-walls.md) | junctions, walls, separators, planarity, face lines, wedges, outlines, joins, heights |
| [6. Rooms](06-rooms.md) | faces, room polygons, anchors and identity, net area, a room's floor and ceiling members, slabs |
| [7. Openings](07-openings.md) | hosted openings, typed dimensions and clear openings, placement |
| [8. Types, materials and assets](08-types.md) | types and overrides, layers, door and window types, their operation and clear opening, materials, assets |
| [9. Serialization](09-serialization.md) | encoding, canonical form, content hash |
| [10. Validation and diagnostics](10-diagnostics.md) | tiers, diagnostics, order of evaluation, the catalogue, fixes |
| [11. The program](11-program.md) | program items, the adjacency graph, rooms that fulfil items, adjacent and connected rooms |
| [12. Extensions](12-extensions.md) | declarations, the registry and known extensions, dependencies, extension elements, fallbacks |
| [13. Hosting and clearances](13-hosting.md) | local frames, boxes, hosts and placement, clearance envelopes, the overlap measure |
| [14. Circulation](14-circulation.md) | the door graph, entries, reachable rooms, sleeping rooms reached through another |
| [15. Floors, ceilings and slabs](15-floors-ceilings-slabs.md) | floors, sunken and raised; flat, tray and vaulted ceilings; hosting on them; slabs |
| [16. Roofs](16-roofs.md) | footprints, gables, pitches and overhangs; the eave outline; flat, shed and equal-pitch surfaces; faces, ridges, hips and valleys |
| [17. Stairs](17-stairs.md) | straight, L, U, winder and spiral stairs; foot, head, rise and risers; steps, run and walkline; headroom and the opening a stair needs; winders, a newel and spiral treads, their walkline and goings; circulation |
| [18. Materials, assets and finishes](18-materials.md) | metallic-roughness materials; textures, their maps and real-world size; texture space; the package and the package validator; room, face and region finishes, resolved |
| [19. Design options](19-options.md) | option sets, options and their primary; membership; designs and their views; references across options; the checked designs; deriving a design, and comparing options side by side |
| [20. Migration](20-migration.md) | migrating a document to a later draft: the steps from 0.1 to 0.2, from 0.2 to 0.3 and from 0.3 to 0.4, moved members and their record, what a migration preserves, the previous major |
| [21. Arc edges](21-arcs.md) | walls and separators along circular arcs: the sagitta; the polyline by iterated snap rounding; arc edges in the graph, wall outlines and curved rooms; lengths and stations, openings on their chords |
| [A. IFC4 mapping](annex-ifc.md) | every core kind and its IFC4 entity |

Every normative statement ends with a tag such as `{#FS-CORE-5.3.1 MUST}`. `pnpm statements`
extracts them; `pnpm coverage` fails if a `MUST` or `MUST NOT` has no conformance test.

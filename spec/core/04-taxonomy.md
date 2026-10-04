# 4. Taxonomies

A taxonomy is a controlled list of terms that rules and tools key on. A room's free-text `name`
says what its owner calls it ("Mudroom", "Kid's room"); its `function` says what it is for, from
a list every tool understands — so a rule about sleeping rooms finds every bedroom, whatever it
is called.

## 4.1 Room functions

| Term | A room for |
|---|---|
| `unspecified` | not yet decided (the default) |
| `sleeping` | sleeping: bedrooms, bunk rooms, nurseries |
| `bath` | bathing and toilets: full and half baths, powder rooms, toilet rooms |
| `kitchen` | preparing food, including a kitchen open to other spaces |
| `living` | living and gathering: living, family and great rooms, dens, playrooms |
| `dining` | eating |
| `office` | working and studying |
| `laundry` | washing and drying clothes |
| `utility` | household work and services not covered elsewhere: mudrooms, workshops, pantries with appliances |
| `storage` | storage: closets, walk-in closets, pantries, attic and under-stair storage |
| `circulation` | moving between rooms: halls, foyers, stair halls, landings |
| `mechanical` | building equipment: furnace and water-heater rooms, electrical rooms |
| `garage` | parking vehicles |
| `exterior` | outdoor floor area under the project's control: porches, decks, patios, balconies |

A room's `function` MUST be either one of the terms in this table or an extension term (4.2). {#FS-CORE-4.1.1 MUST}

A room has exactly one function. A kitchen open to a living room is two rooms divided by a
separator (5.2), or one room whose function is the one its rules should treat it as; Floorspec
does not guess.

## 4.2 Extension terms

An extension may add terms to a taxonomy. An extension term is written
`<extension name>:<term>` — `EXT_wellness:sauna` — where the term matches `^[a-z][A-Za-z0-9]*$`.

The extension named in an extension term MUST be a member of `extensionsUsed`. {#FS-CORE-4.2.1 MUST}

A reader that does not implement the extension treats the room's function as `unspecified` for
every purpose except preserving it.

## 4.3 Layer functions

Every layer of a wall type (8.3) has a function:

| Term | The layer is |
|---|---|
| `core` | the structural or primary layer — studs, block, CLT |
| `substrate` | a backing for a finish: sheathing, cement board |
| `insulation` | thermal or acoustic insulation outside the core |
| `membrane` | a water, air or vapour barrier; usually thin |
| `airGap` | a ventilated or unventilated cavity |
| `finish` | the visible surface: drywall, siding, plaster, tile |

A layer's `function` MUST be one of the terms in this table. {#FS-CORE-4.3.1 MUST}

The layer functions are closed in this draft. Data about a layer that core does not define goes in
the wall type's extension data, not in a new layer function.

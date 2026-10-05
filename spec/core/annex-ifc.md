# A. Annex: IFC4 mapping

This annex maps every Floorspec Core kind, the program, extension elements and hosting to the IFC4 (ADD2 TC1) entity that represents it, and
names the relationships that connect them. It is normative as a vocabulary: an exporter that
writes a Floorspec kind to IFC uses the class and relationships given here. It doubles as the
dictionary between the two vocabularies, which is why it lists derived kinds too.

Every exported element carries its Floorspec ID in a property set named `Floorspec_Identity`
(property `ID`, `IfcIdentifier`), so a file exported to IFC, edited in another tool and brought
back can be reconciled element by element (FLR-ADR-012).

| Floorspec | IFC4 entity | Relationship and notes |
|---|---|---|
| Document | `IfcProject` | units in millimetres; the base unit is not an IFC unit, so lengths are converted (÷ 1,280) |
| Project | `IfcProject` | `Name` = `project.name`; `Description` = `project.description` |
| Site | `IfcSite` | `IfcRelAggregates` (project → site); `RefLatitude`, `RefLongitude` from `location` (converted from microdegrees to degrees, minutes, seconds, millionths); `trueNorth` sets the `TrueNorth` of the model's geometric context |
| Building | `IfcBuilding` | `IfcRelAggregates` (site → building, or project → building when there is no site) |
| Level | `IfcBuildingStorey` | `IfcRelAggregates` (building → storey); `Elevation` = `elevation` |
| Junction | — | no entity; the junction graph travels as the `Floorspec_Graph` property set on each wall (`StartJunction`, `EndJunction`, and the junction's position) and as `IfcRelConnectsPathElements` between walls that share a junction (`RelatingConnectionType` / `RelatedConnectionType` `ATSTART` or `ATEND`) |
| Wall | `IfcWall` (`PredefinedType` `STANDARD`) | `IfcRelContainedInSpatialStructure` (storey → wall); axis representation = location line; body = the derived outline extruded from base to top elevation; `IfcRelDefinesByType` → its `IfcWallType` |
| Wall's layers | `IfcMaterialLayerSetUsage` over an `IfcMaterialLayerSet` | `IfcRelAssociatesMaterial`; layers in the same order (left to right); `DirectionSense` `POSITIVE`; `OffsetFromReferenceLine` from the justification's `a` |
| Separator | `IfcVirtualElement` | `IfcRelContainedInSpatialStructure`; `IfcRelSpaceBoundary` (`PhysicalOrVirtualBoundary` `VIRTUAL`) to the spaces either side |
| Opening | `IfcOpeningElement` | `IfcRelVoidsElement` (wall → opening); an opening with a fill adds `IfcDoor` or `IfcWindow` and `IfcRelFillsElement` (opening → door or window) |
| Door type, window type | `IfcDoorType`, `IfcWindowType` | `IfcRelDefinesByType` → the `IfcDoor` or `IfcWindow` |
| Room | `IfcSpace` (`PredefinedType` `INTERNAL`, or `EXTERNAL` for function `exterior`) | `IfcRelAggregates` (storey → space); `Name` = `name`; footprint = the derived room polygon; the room function as `Floorspec_Room.Function`; `IfcRelSpaceBoundary` to bounding walls and separators |
| Room finishes | `IfcCovering` | `IfcRelCoversSpaces` (space → covering) for floor and ceiling finishes; `IfcRelCoversBldgElements` for a wall finish |
| Slab | `IfcSlab` (`PredefinedType` `FLOOR`) | `IfcRelContainedInSpatialStructure`; body = `boundary` extruded down by `thickness` from the level's elevation plus `offset` |
| Wall type | `IfcWallType` | owns the `IfcMaterialLayerSet` |
| Material | `IfcMaterial` | `color` as an `IfcSurfaceStyleRendering`; texture as `IfcImageTexture` |
| Asset | — | carried by the material or extension that uses it; never exported on its own |
| Net area (derived) | `IfcQuantityArea` in `Qto_SpaceBaseQuantities.NetFloorArea` | converted to square metres |
| Program | — | no entity of its own; its items and adjacencies are exported as below |
| Program item | `IfcSpaceType` (`PredefinedType` `USERDEFINED`, `ElementType` = the item's function) | `IfcRelDefinesByType` (space type → the `IfcSpace` of every room whose `brief` names it); `count`, `targetArea`, `minArea` (converted to square metres) and `level` in the property set `Floorspec_Program`. IFC4 has no requirement entity for a brief, so the requirements travel as properties of the type, and the type stands for the item even when no room fulfils it |
| Adjacency | — | no IFC4 entity; exported in the property set `Floorspec_Adjacency` on the `IfcSpaceType` of `a`, one `IfcPropertyListValue` per kind listing the IDs of the `b` items, and a parallel list of weights |
| Room's `brief` | `IfcRelDefinesByType` | the space's type is its item's `IfcSpaceType` |
| Extension element (a core-only exporter) | `IfcBuildingElementProxy` | body = the fallback box, or the fallback's glTF asset converted to a tessellated body; `ObjectType` = `<extension>:<collection>`. An exporter that implements the extension uses the entity the extension's own annex names |
| Hosted element, `wallFace` | the element's entity | `IfcRelContainedInSpatialStructure` (storey → element) and `IfcRelConnectsElements` (wall → element); placement relative to the wall's (`IfcLocalPlacement` with `PlacementRelTo` the wall's placement) |
| Hosted element, `surface` | the element's entity | `IfcRelContainedInSpatialStructure` (space → element): the room's `IfcSpace` contains it |
| Hosted element, `free` | the element's entity | `IfcRelContainedInSpatialStructure` (storey → element) |
| Clearance envelope | — | not exported. Envelopes are derived from types and hosts, so an importer derives them again; exporting them as `IfcVirtualElement` would add elements with space-boundary semantics that IFC tools would treat as walls of a space |

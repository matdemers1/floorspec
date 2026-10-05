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
| Door type's `operation` | `IfcDoorType.OperationType` (`IfcDoorTypeOperationEnum`) | by name, below; `NOTDEFINED` when no operation is declared |
| Window type's `operation` | `IfcWindowType.PartitioningType` (`IfcWindowTypePartitioningEnum`) and the `OperationType` of each `IfcWindowPanelProperties` (`IfcWindowPanelOperationEnum`) | by name, below; `NOTDEFINED` when no operation is declared |
| Clear opening | — | no IFC4 attribute holds a declared net clear opening; it travels as the property set `Floorspec_ClearOpening` (`ClearWidth`, `ClearHeight`, `ClearArea`, converted to millimetres and square metres) on the `IfcDoorType` or `IfcWindowType`, and on the `IfcDoor` or `IfcWindow` of an opening that overrides it |
| Room | `IfcSpace` (`PredefinedType` `INTERNAL`, or `EXTERNAL` for function `exterior`) | `IfcRelAggregates` (storey → space); `Name` = `name`; footprint = the derived room polygon; the room function as `Floorspec_Room.Function`; `IfcRelSpaceBoundary` to bounding walls and separators |
| Room finishes | `IfcCovering` | `IfcRelCoversSpaces` (space → covering) for floor and ceiling finishes; `IfcRelCoversBldgElements` for a wall finish |
| Room's floor (15.1) | `IfcSlab` (`PredefinedType` `FLOOR`) when its thickness is declared; otherwise `IfcCovering` (`PredefinedType` `FLOORING`) | `IfcRelContainedInSpatialStructure` (storey → slab or covering) and `IfcRelSpaceBoundary` to the space; body = the room polygon extruded from its bottom to its top; `Name` = the room's name; the room's `floorFinish` as an `IfcCovering` (`FLOORING`) on it by `IfcRelCoversBldgElements` |
| Room's ceiling (15.2–15.5) | `IfcCovering` (`PredefinedType` `CEILING`) | `IfcRelCoversSpaces` (space → covering); body = the ceiling surface — flat, its tray's border and raised centre joined by the step, or a vault's planes clipped to the room polygon — as an `IfcShellBasedSurfaceModel`; the form, `height`, `border`, `depth`, `ridge`, `pitch` and `slopes` in the property set `Floorspec_Ceiling`; the room's `ceilingFinish` as its material |
| Floor offset, ceiling low and high (derived) | `IfcQuantityLength` in the property set `Floorspec_Ceiling` (`Low`, `High`) and `Floorspec_Floor` (`Offset`, `Thickness`) | converted to millimetres; `Qto_SpaceBaseQuantities.FinishCeilingHeight` = the ceiling's low minus the floor's top |
| Slab | `IfcSlab` (`PredefinedType` `FLOOR`, or `LANDING` for the purpose `landing`) | `IfcRelContainedInSpatialStructure`; body = `boundary` extruded down by `thickness` from the level's elevation plus `offset`; `purpose` as `ObjectType` and in the property set `Floorspec_Slab` (`Purpose`) |
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

**Door operations.** The left or right of an IFC4 operation type is the hand IFC4 defines for it;
an exporter takes it from the opening's `hinge` and `swing` (7.1), and writes the door's own
`OperationType` on the `IfcDoor`.

| Floorspec | `IfcDoorTypeOperationEnum` |
|---|---|
| `swing` | `SINGLE_SWING_LEFT` or `SINGLE_SWING_RIGHT` |
| `doubleSwing` | `DOUBLE_DOOR_SINGLE_SWING` |
| `doubleActing` | `DOUBLE_SWING_LEFT` or `DOUBLE_SWING_RIGHT` |
| `bypassSlide` | `DOUBLE_DOOR_SLIDING` |
| `pocket`, `surfaceSlide` | `SLIDING_TO_LEFT` or `SLIDING_TO_RIGHT` |
| `bifold` | `FOLDING_TO_LEFT` or `FOLDING_TO_RIGHT` |
| `overhead` | `USERDEFINED`, with `UserDefinedOperationType` `"overhead"` |
| `cased` | `USERDEFINED`, with `UserDefinedOperationType` `"cased"` |

**Window operations.** Core 0.3 records no casement's or tilt-turn's hand and no pivot's axis
(8.4), so a core-only exporter writes `OTHEROPERATION` where the hand or the axis decides the
value.

| Floorspec | `IfcWindowTypePartitioningEnum` | Panels' `IfcWindowPanelOperationEnum` |
|---|---|---|
| `fixed` | `SINGLE_PANEL` | `FIXEDCASEMENT` |
| `casement` | `SINGLE_PANEL` | `SIDEHUNGLEFTHAND` or `SIDEHUNGRIGHTHAND` |
| `awning` | `SINGLE_PANEL` | `TOPHUNG` |
| `hopper` | `SINGLE_PANEL` | `BOTTOMHUNG` |
| `singleHung` | `DOUBLE_PANEL_HORIZONTAL` | `FIXEDCASEMENT` above, `SLIDINGVERTICAL` below |
| `doubleHung` | `DOUBLE_PANEL_HORIZONTAL` | `SLIDINGVERTICAL`, both |
| `horizontalSlider` | `DOUBLE_PANEL_VERTICAL` | `SLIDINGHORIZONTAL`, and `FIXEDCASEMENT` or `SLIDINGHORIZONTAL` |
| `tiltTurn` | `SINGLE_PANEL` | `TILTANDTURNLEFTHAND` or `TILTANDTURNRIGHTHAND` |
| `pivot` | `SINGLE_PANEL` | `PIVOTHORIZONTAL` or `PIVOTVERTICAL` |

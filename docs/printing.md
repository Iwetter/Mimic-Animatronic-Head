# Printing the R5a release

This package targets a Flashforge Adventurer 5M, a **0.4 mm nozzle**, and **PLA**, as confirmed by the owner. Its 220 × 220 × 220 mm build volume uses the Orca profile's centered XY coordinates (−110 to +110 mm). No printer has been operated or physically calibrated during generation of this release.

## Which files to open

- `3mf/individual/`: one genuine geometry-only 3MF per unique printable part. Each is already oriented and seated at Z = 0. These files contain **no verified printer presets**. Use them for replacement parts after applying the supplied profiles.
- `3mf/plates/*_models.3mf`: grouped geometry-only plates containing the specified quantities. Preserve their placement and orientation.
- `3mf/plates/*_AD5M_PLA_0p4_sliced.3mf`: OrcaSlicer projects containing the actual settings and generated G-code from the recorded slice run. Open these **as projects** in OrcaSlicer 2.4.2 to review the configured print. Do not import them as geometry only and assume the settings were retained.
- `bom/PRINT_MAP.csv` and `bom/plates.json`: the authoritative print order and quantity map. Print each listed plate once. The fit-coupon plate is first. Do not also print every individual file: those duplicate the grouped quantities.
- `renders/plates/`: labeled arrangement images. `renders/layers/`: raster previews derived from actual generated extrusion moves, showing first, middle, top, and the layer with the most support segments where applicable.

Read `validation/printing_report.json` for the actual slice status of every plate. A filename alone does not establish that a slice completed.

## Final plate order

All 31 unique printed designs are represented by 36 pieces on 10 plates: 35 installed pieces plus one fit coupon. Print each plate once. The final slice run completed for all 10 plates; this establishes digital slice completion, not a physical print result.

| Plate | Contents | Slicer estimate: time / PLA |
|---|---|---|
| PL01 | P90 fit coupon ×1 | 1h 03m / 15.39 g |
| PL02 | P45, P39, P40, P46 ×1; P34, P37, P35, P49, P38 ×2 | 4h 45m / 53.41 g |
| PL03 | P23, P24 ×1 | 3h 28m / 53.22 g |
| PL04 | P28, P21 ×1 | 3h 18m / 46.18 g |
| PL05 | P22 ×1 | 2h 48m / 39.80 g |
| PL06 | P33, P20 ×1 | 5h 59m / 83.47 g |
| PL07 | P29, P26 ×1 | 2h 44m / 37.44 g |
| PL08 | P27, P03 ×1 | 4h 33m / 66.62 g |
| PL09 | P32, P41, P01, P30, P31 ×1 | 7h 47m / 102.60 g |
| PL10 | P25, P36, P44, P42, P43 ×1 | 4h 59m / 57.62 g |

The predicted total is **555.75 g of PLA including generated supports and brims**, excluding failed prints, extra coupons and calibration. Individual 3MF files are replacement geometry; do not print those in addition to this plate set.

## Baseline settings

| Setting | Supplied baseline |
|---|---|
| Printer / material | Adventurer 5M, 0.4 mm, 1.75 mm PLA |
| Layer / first layer | 0.20 / 0.20 mm |
| Walls / top / bottom | 4 walls; 5 top and 5 bottom layers, 1 mm target shell thickness |
| Infill | 25% crosshatch |
| Outer / inner wall | 40 / 60 mm/s |
| First layer / initial infill | 20 / 25 mm/s |
| Top / infill / internal solid | 35 / 80 / 60 mm/s |
| Support / support interface | 50 / 30 mm/s |
| Default / outer acceleration | 2000 / 1000 mm/s² |
| PLA maximum volumetric flow | 12 mm³/s baseline cap |
| Adhesion | 5 mm outer brim; 0.1 mm brim separation |
| Supports | Normal automatic supports, including supports originating on the model where needed; 0.2 mm top/bottom separation |
| Nozzle / textured plate | 220°C; bed 55°C first layer then 60°C, inherited from the Flashforge PLA profile |
| Print sequence | By layer, with automatic rearrangement and orientation disabled |

The machine profile and starting PLA profile are resolved from the [official OrcaSlicer 2.4.2 release](https://github.com/OrcaSlicer/OrcaSlicer/releases/tag/v2.4.2). `scripts/profiles/provenance.json` records upstream profile hashes and every engineering override; the resolved JSON files are alongside it. The listed temperatures, flow ratio, pressure advance and retraction remain **baseline values**, not measurements of the owner's filament or printer. Perform the printer's normal calibration and follow the actual PLA spool's temperature range before production printing.

## Fit and first-print sequence

1. Clean the build plate and use the correct AD5M nozzle and PLA profile. Confirm the printer's bed leveling and nozzle offset using its normal procedure.
2. Print the fit-coupon plate first with the supplied process. Measure its features and trial-fit the actual shafts, fasteners, nuts and servo body specified in the mechanical instructions. Record measured dimensions and free movement without forcing the parts. The owner's tentative servo names are unconfirmed; do not treat a nominal micro-servo envelope as proof of fit.
3. Remove the brim and support material before judging a fit. Remove elephant-foot lips carefully; do not drill a pivot hole arbitrarily oversize to hide misalignment. Adjust the parametric feature or a documented process compensation when measurements require it, then rebuild and revalidate the affected exports.
4. Inspect each grouped project's preview before printing. Verify all parts contact the bed or are supported, supports can be removed, the narrow links have continuous extrusion, and no part is clipped or missing. The exact orientation and local cautions are in `PRINT_MAP.csv`.
5. Follow the plate map after the coupon passes. Use the mechanism plate to confirm shaft, link and servo-dependent fits before committing to all large parts. Dry-assemble completed assemblies with the electronics unpowered; check bolt access, mating faces, free pivot travel and cable space.
6. Keep labels with the parts until assembly. Reject cracked parts, layer separation, distorted mounting faces, weak bridges or binding pivots. PLA parts require observation during warm electronics tests; this release does not establish hot-environment durability.

Models are at least 10 mm from the nominal bed boundary and at least 14 mm apart in the packing plan. The latter reserves 5 mm for each neighboring brim plus 4 mm separation. Sliced model/support/brim extrusion bounds are independently checked against the full bed. The printer's manufacturer-profile purge line is excluded from model-bound measurements and remains in the starting G-code. Do not use automatic rearrangement or change brim/support settings without rechecking the resulting spacing.

Eye and eyelid surfaces need careful support removal and finishing. Protect pivot bores, linkage centers, mounting pads and contact surfaces from sanding or paint buildup. A cosmetic surface that looks satisfactory can still bind mechanically; check the complete assembled travel by hand before applying servo power.

P34 eyes print with the iris upward and their hidden rear opening downward. Their direct planar mesh contact is extremely small; retain the generated support structure and brim, observe the first layers, and trial-print this geometry before relying on it. P39/P40 lids rest on their broad outer arm faces; support still carries the curved shell. P03 prints flange down, and P42 prints its root strip down with the teeth upward. P21/P22 walls, P32 maxilla, P41 deck and P44 servo cradle still require support beneath projecting features; all support must be removed from holes, bearing faces, servo pockets and the cable channel before assembly.

## Digital checks and their limits

The packaging script validates every source mesh for watertightness, consistent winding and positive volume; checks build boundaries and the quantity sum; writes real 3MF resources and instances; opens each result with lib3mf; and compares every exported mesh instance to its source vertices, face count and volume within a 0.002 mm numerical tolerance. STEP-to-mesh and mechanical checks are reported separately by the CAD workflow.

For the actual Orca projects, the script verifies the saved nozzle, layer, wall, infill, brim, support, material and print-sequence settings, preserves the source arrangement, reads the embedded G-code, checks all model/support/brim extrusion bounds, and produces sampled layer previews. These are software checks. They do not establish adhesion, achievable dimensions, support removability, servo fit, mechanical strength or successful physical printing.

OrcaSlicer's command-line exporter writes thumbnail relationships without emitting their image files. The packaging script adds generated plate-preview PNGs to satisfy those relationships and checks that **all original slicer ZIP parts remain byte-for-byte unchanged**. Geometry, slicer settings and G-code are unmodified. lib3mf may report unknown vendor metadata/attributes in an Orca project; these warnings are recorded alongside successful core geometry validation.

## Reproduction

The print toolchain was run with Python 3.12.14 on Windows. Install `scripts/requirements_printing.txt` for the tested mesh/3MF library versions. From the release directory, run:

```text
python scripts/package_prints.py --release . --work PATH_TO_SCRATCH --orca PATH_TO_ORCA_SLICER_EXE --profiles-source PATH_TO_ORCA/resources/profiles/Flashforge
```

The source STEP/STL release and `bom/parts.json` must already have passed the CAD review. The script does not redesign or export CAD. `--no-slice` creates geometry-only packages and explicitly records that the slicing checks were not run. A replacement or revised part must follow the same CAD review, export, packaging and physical fit sequence.

# Editable CAD and release workflow

Use CadQuery as the mechanical geometry authority. The supplied Python source exposes dimensions, datums, Boolean features and the assembly contract. Edit a versioned working copy; keep the approved concept archive and this release intact. `parameters.json` records the generated parameter snapshot; it is not a GUI-driven FreeCAD feature tree. Read source comments before changing dimensions, as several coupled linkage dimensions must change together.

FreeCAD is suitable for STEP inspection, section views, measuring actual mating parts and additional drawings. Importing a STEP does not recover the original parametric feature history. Blender is used only for presentation renders and appearance references; its mesh exports are not the authority for bores, pivots or manufacturing clearances. Retain the approved outer silhouette when adjusting internal engineering.

## Rebuild sequence

The exercised Windows environment uses Python 3.12, CadQuery 2.8.0, Blender 5.2 and OrcaSlicer 2.4.2. Python dependency versions are listed in `scripts/requirements.txt`. Blender, OrcaSlicer and Arduino tooling are separate applications and are not bundled in the ZIP.

Run commands from a **copy** of the release directory with the Python environment activated. Rebuilding overwrites generated files in the selected output directory. Preserve measured calibration records before any rebuild.

```powershell
python cad_source/build_release.py .
```

First inspect the STEP parts, complete assembly and mechanical reports. Confirm source/STEP volumes, fastener stacks, all-pose linkage closure, clearances, stops and actual hardware dimensions. Mesh generation follows this review; changing the geometry invalidates the previous STL, 3MF, slicer and drawing evidence. Refer to the release's mechanical build/export scripts for the recorded tessellation method.

```powershell
python scripts/assess_loads.py .
python scripts/generate_drawings.py --release .
python scripts/render_assembly.py step/assembly/Mimic_R5a_E1_complete.step --blender "C:\path\to\blender.exe" --out renders --work work/render_final
python scripts/annotate_renders.py --release . --scene work/render_final/scene.json
python scripts/package_prints.py --release . --orca "C:\path\to\orca-slicer.exe" --profiles-source "C:\path\to\OrcaSlicer\resources\profiles\Flashforge" --work work/printing
python scripts/build_manual.py --release .
```

Printing requires final reviewed meshes and the matching BOM. The pipeline emits geometry-only individual/model 3MFs and separately named actual sliced Orca projects. It checks all required quantities, transformed mesh identity, bed/toolpath bounds and selected embedded settings. Review every plate's layer images and all support-removal paths; a successful slice is not a successful print.

Render and inspect every PDF page after building the manual. Run the independent release verifier, check source/report hashes, then regenerate `SHA256SUMS.txt` and the ZIP. The report timestamps and hashes must belong to the final geometry. Do not retain a passing report from an earlier revision after editing a source or generated artifact.

## Hardware and firmware changes

Measure the servo body, tabs, output axis, horn radii, spline screw, cable exit and voltage/current requirements before changing mounts. Preserve CH0–CH4 semantics where feasible; remeasure pulse endpoints after any linkage change. Firmware compile instructions and tested toolchain versions are in `firmware/README.md`. The default calibration deliberately leaves outputs disabled.

To add an active neck, use the preserved flange datums and measured final head mass/center of mass. Neck, torso, arms and piano-playing hands require new load cases and verification; the present head release does not establish their structural or control capability.

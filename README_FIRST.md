# Mimic R5a Manufacturing Release

**Revision R5a-E1 — engineering prototype manufacturing package.**

Prepared for Flashforge Adventurer 5M, 220 x 220 x 220 mm, **0.4 mm nozzle and PLA**. The approved visual design is retained with necessary internal mechanism, joint and service changes. The original archive is preserved.

This is a **digitally prepared prototype**, with actual CAD, print projects, firmware and instructions. No physical print, assembly, powered motion or endurance qualification has been performed. The final digital check results are in `validation/release_qa.json`, `validation/motion_report.json`, `validation/mesh_report.json` and `validation/printing_report.json`. Any failed report is a release hold; do not infer a pass from the folder name.

**Before manufacturing servo-specific interfaces:** servo markings were reported tentatively as “sg950 and mg950”; exact identification, dimensions, OEM horns, spline screws and supply voltage/current rating remain unconfirmed. CAD uses a clearly labeled nominal microservo envelope. Measure actual hardware and print the fit coupon first. Do not assume the reported names identify SG90/MG90S. A different servo package requires revised mounts and revalidation.

Start with [Assembly_Manual.pdf](docs/Assembly_Manual.pdf) or its [Markdown version](docs/Assembly_Manual.md), then use [PRINT_MAP.csv](bom/PRINT_MAP.csv). There are **31 unique printable designs, 36 total pieces including the fit coupon, and 10 grouped plates**. Print each plate once. P90 is a bench coupon; 35 printed pieces belong to the head/interface assembly.

- `3mf/individual/`: one geometry-only 3MF for each unique part, in reviewed print orientation.
- `3mf/plates/*_models.3mf`: quantity-complete grouped geometry. These files do not contain verified printer settings.
- `3mf/plates/*_AD5M_PLA_0p4_sliced.3mf`: actual OrcaSlicer projects with saved AD5M/PLA settings and embedded G-code. Review the layer previews and calibrate the actual printer/filament before printing. No printer has executed these files.
- `cad_source/`, `step/`, `stl_backup/`: editable CadQuery, named assembly/part STEP and verified compatibility meshes. STEP parts retain assembly coordinates; manufacturing meshes are oriented and placed on the bed.
- `firmware/`: ESP32/PCA9685 commissioning firmware, build instructions and host tests. **Outputs default OFF; all assembled motion is locked pending measured calibration.**
- `bom/`, `docs/`, `renders/`, `validation/`: parts/hardware, drawings, illustrated instructions, geometry-derived views and evidence.

**FlashPrint application compatibility is unverified.** The individual files and `*_models.3mf` plates are standard geometry 3MFs, validated structurally and geometrically; try these for import. The separately named sliced projects use OrcaSlicer metadata and are verified in that toolchain. Successful opening, settings preservation or printing in FlashPrint has not been tested.

The electrical design preserves CH0 yaw, CH1 jaw, CH2 pitch and CH3/4 lids. Actuator power uses a protected independent distribution and common ground. Confirm actual module pinout, servo voltage/current, wiring and protection before energizing. OE disables pulses; it does not disconnect power. See [electronics.md](docs/electronics.md).

The nominal soft envelope is yaw ±20°, pitch ±12°, jaw 0–14° and lids 0–50°. These are mechanism design coordinates, not a universal pulse-to-angle map. Positive pitch points the gaze down in this coordinate convention. Physical stops and the manual sweep must be measured; software limits stay inside the measured envelope. The jaw range deliberately precedes the original neck collision.

Follow [physical_verification.csv](docs/physical_verification.csv) and [calibration_record.csv](firmware/calibration_record.csv). Results begin **NOT TESTED**. Record fastener engagement/access, pivot play, stop angles, combined clearances, cable sweeps, supply behavior, torque/current/temperature, reset/fault behavior and endurance before routine operation.

Editable-source and reproduction details are in [cad_workflow.md](docs/cad_workflow.md); the modular head/future-body boundary is in [engineering_architecture.md](docs/engineering_architecture.md). Future neck, torso, arms and piano-playing hands require new measured load cases and separate verification.

Original concept archive SHA-256: `2e1f1e0b98dad0a01ebfbdc5d0f4584d23513b93667c1e906cfc79f197be6a52`.

The actual R4 release and actual voice firmware were not supplied. Embedded P01/P03 geometry and reference notes are available; independent comparison to the absent original release cannot be claimed.

P01/P03 have been preserved from the supplied named assembly. INMP441/MAX98357A hardware and pins are reserved, but working original speech firmware integration is not claimed. Historical concept audit/report findings apply to the supplied concept; final revised reports supersede them for this package.

Check `SHA256SUMS.txt` after extracting the ZIP. Rebuilding or modifying any file invalidates the previous manifest and affected validation. The manifest does not include itself.

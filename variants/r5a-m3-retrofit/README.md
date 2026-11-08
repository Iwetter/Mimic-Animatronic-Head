# V5 M3 retrofit development

This draft starts from the five-axis **R5a-E1** head. The goal is to reuse existing V5 prints wherever the mating geometry supports a fastener from the M3 kit. The first stage covers the structural joints. Wait for a complete fastener and movement check before committing to the full set of reprints.

| Original V5 joint | Draft change | Changed prints |
| --- | --- | --- |
| P01 socket side locks | Four M3×12 screws engage ordinary nuts in the neck insert. | P03 |
| Crest to arches | Open the three original M2 axes to 3.4 mm. | P25, P26, P27, P28 |
| Face to cheeks | Open the two cheek joints for M3. | P29, P30, P31 |
| Upper jaw carrier to lower walls and face | Open the four mounting axes for M3. | P21, P22, P29, P32 |
| Tooth rows to their carriers | Add wider rear lugs and matching recesses around the M3 axes. | P32, P33, P42, P43 |

The draft includes 14 distinct changed prints. Compare the [structural reprint list](draft/structural_reprint_list.csv) to the existing V5 parts. The [fixed-joint hardware schedule](draft/fixed_joint_hardware.csv) lists proposed lengths. It also identifies joints such as the upper plate attachments where the hole already accepts M3 and the length can be evaluated without a reprint. The schedule covers the structural stage only.

## Structural checks

The changed CAD solids each exported to a single watertight, consistently wound STL within a 220 mm cube. The nominal neck lock shanks and nut envelopes clear the P01/P03 parts. The added tooth lugs had no overlaps above 0.05 mm³ across 16 sampled V5 poses. The [clearance report](draft/structural_clearance.json) records the scope. Physical print fit, head and washer clearance, fastener access, and the complete five-axis retrofit still need verification.

## Remaining interfaces

- Five servo tab mounts need M3 bridges that fit the actual servos and clear the surrounding shell.
- The OEM horns need adapters that preserve the V5 linkage radii and keep the original servo center screws. The larger M3 hardware must clear the yaw, pitch, jaw, and lid linkages at their measured limits.
- Eyelid hinges, stop slots, and linkage pins need M3 running clearances and a way to retain the screws without clamping the moving parts.
- Eye shaft clamps, the jaw pivot retention, and the complete kit quantity totals still need checking. Preserve the existing smooth bearing interfaces where they fit.

## Rebuild the structural draft

From the repository root, use the CadQuery and trimesh environment listed in [scripts/requirements.txt](../../scripts/requirements.txt):

```powershell
New-Item -ItemType Directory -Force work/v5-base/cad_source
python cad_source/build_release.py work/v5-base
python variants/r5a-m3-retrofit/build_structural.py work/v5-base work/v5-structural
python variants/r5a-m3-retrofit/check_structural.py work/v5-base work/v5-structural
```

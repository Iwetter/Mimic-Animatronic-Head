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

## Hardware fit plate

The [sliced fit plate](draft/fit_slice/PL01_AD5M_PLA_0p4_sliced.3mf) uses the Adventurer 5M profile with a 0.4 mm nozzle, PLA, and 0.20 mm layers. It contains ten small pieces. Confirm the printer profile and review the [layer preview](draft/fit_slice/PL01_layers.png) before printing.

1. Use A90 with the A10 side bridge and A91 with the A11 end bridge. Set a servo tab against the fixture face and use an M3×12 screw and ordinary nut through the bridge. The nose should hold the tab and the heel should rest on the fixture. Check the clip clears the motor body and holds the tab without bending it.
2. Pair A40 with A41 for yaw, A42 with A43 for pitch, and A44 with A45 for a lid. Place the OEM arm between the plates, retain its original center screw, and use one M3×10 and plain nut through the two plates beyond the horn tip. The adapters use 12, 14, and 10 mm pivot radii respectively. Check that the arm seats flat between the locating cheeks and does not slip during a gentle hand twist.
3. Load an ordinary M3 nut in the adapter’s side pocket. Confirm the new pivot screw threads smoothly into the nut while leaving clearance to the original horn. The fit test is unpowered. Keep the clamp pieces for final assembly if their fit is good.

## Mechanism checks in progress

The files in `draft` record individual CAD checks. Several stages contain versions of the same part. The eventual print manifest will select one final version of each reprint.

| Check | Current result |
| --- | --- |
| Five servo mounts | [17 sampled poses clear](draft/mounts/servo_mount_clearance.json) |
| Four lid hinges | [25 sampled poses clear](draft/lid_hinges/lid_hinge_clearance.json) |
| Globe and crank clamps | [Nine sampled poses clear](draft/yaw_clamps/yaw_clamp_clearance.json) with the original smooth shafts |
| Jaw horn clamp | [Eight sampled jaw angles clear](draft/jaw_drive/jaw_horn_clearance.json) |
| Single-arm horn adapters | [13 sampled poses clear](draft/horn_adapters/horn_adapter_clearance.json) with the link arms removed for the scoped check |

The complete assembled linkage and stop checks still govern the larger print plates. Keep the existing V5 parts until the final reprint list is ready.

## Rebuild the structural draft

From the repository root, use the CadQuery and trimesh environment listed in [scripts/requirements.txt](../../scripts/requirements.txt):

```powershell
New-Item -ItemType Directory -Force work/v5-base/cad_source
python cad_source/build_release.py work/v5-base
python variants/r5a-m3-retrofit/build_structural.py work/v5-base work/v5-structural
python variants/r5a-m3-retrofit/check_structural.py work/v5-base work/v5-structural
```

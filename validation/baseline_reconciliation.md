# R5a baseline reconciliation and independent acceptance plan

Revision: baseline audit 2026-10-19. Scope: the supplied R5a concept before engineering correction. This report is not final release QA and does not certify the revised design. **Hardware tested: false.** All numerical findings below are nominal digital results.

## Evidence and provenance

The concept archive SHA-256 is `2e1f1e0b98dad0a01ebfbdc5d0f4584d23513b93667c1e906cfc79f197be6a52`. The original archive and extracted source were not edited. Its checksum inventory passed the prior read-only audit. The archive contains 25 unique new printed parts, 28 new printed instances, and a 56-component named assembly including recovered P01/P03. It does not contain the original R4 release, R4 generating source, or actual motion/voice firmware. Attached reference notes describe R4 but cannot authenticate it.

Independent measurements use CadQuery 2.8.0/OpenCascade and trimesh. `baseline_measurements.json` contains raw dimensions, cylindrical features, comparisons, report inventories, and input identity. The auditor independently reconstructed the original P38 expression. The mechanisms specialist separately rebuilt all original source using P01/P03 recovered from the named assembly; the auditor then re-imported and compared all 25 rebuilt and delivered part STEP files. This was a baseline rebuild, not a fabrication authorization for the original geometry.

## Reconciled findings

| Topic | What the evidence actually establishes | Disposition for the revised release |
|---|---|---|
| Source versus delivered geometry | All 25 original rebuilt STEP volumes agree with the 25 supplied STEP volumes to numerical precision. The baseline source is reproducible after restoring missing interface inputs. | Preserve source lineage; do not describe the whole supplied model as stale geometry. |
| P38 metadata discrepancy | Source P38 has volume **1571.19145 mm³**; supplied STEP and assembly each have **1427.74868 mm³**. Exporting the freshly reconstructed source to STEP and re-importing reproduces **1427.74868 mm³**. Metadata 1571 mm³ follows source. | This is a repeatable geometry/exchange anomaly, not sufficient evidence of an outdated source. Replace the defective socket mechanism and require source/STEP/mesh consistency. |
| P38 anomaly localization | Source left end section x −40…−20 has volume 219.38121 mm³; delivered STEP section has 75.93845 mm³. Other section volumes agree. The left outer spherical face area changes from about 94.71 to 98.31 mm². Both solids report valid; Boolean differences misleadingly return zero. Fresh raw tessellations of both are non-watertight. | A valid-solid flag or a zero Boolean difference is insufficient. Compare volume, connected shells, tessellation manifoldness, and round-trip geometry independently. Root cause within STEP/topology handling was not isolated further. Supplied repaired STL validity does not repair source provenance. |
| Eye mechanism freedom | Two universal-jointed eyes provide four coordinates; the floating bar provides six. Two eye/bar spherical joints impose six constraints and two fixed-horn ball-link rods impose two: generically **two passive freedoms remain**. The pose code instead directly enforces equal eye angles and pure bar translation. | Require a physically deterministic two-input mechanism. A common supported pitch cradle plus a pinned yaw parallelogram can supply the missing constraints while retaining visible globes, lids, and face. Verify its own topology and paths. |
| Eye reachability | Original nominal yaw +25°, pitch ±18° needs minimum rod length **30.187036 mm**, exceeding the specified 30 mm. These poses appear in the supplied lookup and combined-motion checks. | Reject closure failures; do not rely on rod flex/backlash. Revised motion must be calculated from actual joints, not imposed transforms. |
| Jaw range | Original jaw/neck clearance: **3.165 mm at 16°**, **0.132 mm at 19°**, overlap **67.123 mm³ at 20°**. The 22° brief is not supported. | Recheck source-generated revised geometry. Explicitly publish the revised operating range and stops; do not retain incompatible 22° claims. |
| Eye/post gap | Original extreme sampled globe/post gap is **0.672 mm**. Other running gaps are 0.4–0.5 mm. | Include print error, misalignment, paint, axle play, and deflection in a clearance budget; inspect revised combined motion. |
| Servo/horn interfaces | P41/P44 original cradles lack tab bolt holes. Jaw placeholder is a one-arm 9 mm horn while ramus holes are ±8 mm. Real horn dimensions and tab spacing are not supplied. | Dimension retained OEM horn adapters and servo mounting slots from explicit hardware envelopes; mark measurements still required. Never print a servo spline. |
| Pivots and retention | Original eye rear stud neck is printed Ø1.6 mm; yaw dowel Ø2 enters nominal Ø1.7; retention and washer stacks are incomplete. Cross-block orthogonal bores have only a 0.1 mm modeled separating web. | Use retained smooth metal pivots and practical assembly access. Specify which member rotates and which is clamped. Account for joint axial play rather than clamping through a rotating stack. |
| Blinks and saccades | Supplied speed calculations fail 0.12 s and 0.22 s lid strokes and a 50° eye sweep in 0.20 s. Original torque models omit friction/spring torque and underestimate the shared eye load. | Revised budgets must use full moving mass and position-dependent transmission. Firmware limits must follow achievable mechanism speed with margin. |
| Printing | Supplied 25 STLs were watertight and fit individually inside 200×200×220 mm. This does not establish printability or assembly. P34/lids have unsuitable exact-plane contact in supplied orientation. | Review orientation/support accessibility, first-layer contact, quantity-complete plates, and fit coupons for revised geometry. |

The revised eye cradle changes the sequence of physical rotations from the original imposed transform. Software must describe its actual axes and map desired gaze to those axes; reusing the old lookup merely because CH0/CH2 are retained is invalid.

## Original interface geometry, independently measured

P01 and P03 are supplied assembly solids labeled as reused R4 components. Their nominal geometry can be preserved; identity to the absent R4 original cannot be proven.

| Interface | Actual geometry and assembly implication |
|---|---|
| P03 neck flange to P20 head base | P03 overall bounds **96×61×55 mm**, Z −55…0. Flange is Z −6…0. Four Ø3.4 through-holes at X ±40, Y ±22.5, parallel Z. P20 is Z 0…6 with the same holes. Nominal contact has zero overlap. The original 12 mm total grip supports a proposed M3×20 stack once actual washers/nut thickness and access are confirmed. |
| Neck tenon/socket | At Z −43, P03 tenon spans X −14…14 and Y −10…26: **28×36 mm**. P01 socket spans X −14.3…14.3 and Y −10.3…26.3: **28.6×36.6 mm**, nominal **0.3 mm per side**. Rounded-corner compatibility and real printed fit remain physical checks. |
| Neck cross-lock holes | Ø3.4 holes parallel X, at Y 21, Z −48 and −38. P01 outer side faces are X ±19 at these holes; nominal total across-stack grip is **38 mm**. A proposed M3×45 with two thin washers and nut must be checked against actual hardware and protrusion. |
| Torso interface | Four Ø3.4 holes parallel **Y**, at X ±23 and Z −55/−31, through the rear plate Y 31…37. Thus the **46×24 mm pattern is in the XZ plane**, not a horizontal mounting deck. No actual mating torso part is supplied. |
| Harness passage | P03 central passage at Z −43 is X −8…8, Y −1…17 (**16×18 mm**). This agrees with P20 opening centered at X 0, Y 8. Check connector insertion and strain relief before fixing electronics locations. |

P01/P03 nominal intersection volume is zero. Their reported minimum separation is zero because seating faces contact; this does not mean the 0.3 mm side clearance is absent. Future active neck integration needs a separate load case and bearing structure based on measured head mass/COM. The present socket is not a load rating for torso, arms, or piano-playing hands.

## Superseded report reconciliation

The supplied `validation_report.json` cites a yaw step of 5°, but `motion_eyes.json` contains **15 in-range poses** (yaw −25, −15, 0, 15, 25 crossed with pitch −18, 0, 18) and **four overtravel poses**. The 143-row lookup is a different kinematic calculation, not a dense solid-collision sweep. Maximum rod error in the eye report is approximately 1.62 mm including overtravel; the four combined-16° poses retain a 0.187 mm in-range error despite zero listed collisions. `check_motion_r5a.py` records rod error without failing on it.

The original report chronology is retained only as development history:

- `neutral_allpairs_v1…v5`: superseded by v6. v6 lists two 6.626 mm³ dowel/post overlaps classified as intentional press fits; their physical feasibility was not tested.
- `motion_lids_jaw.json`: 29 poses, 22 listed unintended overlap instances; its jaw geometry is superseded by `motion_jaw_v3.json`.
- `motion_jaw_v2.json`: 14 poses, 18 overlap instances; superseded by v3.
- `motion_jaw_v3.json`: 14 poses, eight overlap instances including outside-range trials. It supports a reduced working range, not a blanket all-poses pass.
- `motion_jawfine.json`: only 17°, 18°, 19°; zero overlaps is not adequate tolerance margin at 19°.
- `motion_combined16.json`: four corner poses, zero listed overlap, but includes the unreachable eye poses.

None of these historic reports validates revised source. Final QA needs its own revision-bound outputs, actual sample intervals, excluded pairs, measured minima, and failure exit codes.

## Independent acceptance criteria for release QA

These criteria are a test plan, **not a statement that the final release has passed**. Any unmet criterion must be recorded as an open item with scope and consequence.

1. **Provenance and completeness:** original archive hash unchanged; all revised geometry generated from included parameter/source files; P01/P03 extraction provenance explicit; one metadata/BOM record per unique printable design; assembly instance counts, print quantities, and grouped-plate counts agree; no retired design remains accidentally in print plates.
2. **Geometry consistency:** every STEP opens, has positive volume and intended solid count, and declares millimetres. Compare source and re-imported STEP volume to the tighter practical threshold of 0.1% or 0.5 mm³, with exceptions investigated rather than hidden. Mesh volume should agree within 0.5% at recorded tessellation settings. Require watertight consistent-winding meshes with no unintended disconnected shells; inspect small holes and all suspicious round-trip differences.
3. **Mobility and assembly:** for fixed input positions no unintended passive gaze DOF remains. Each pivot has axis, axle, spacers, retention, and installation direction; each fastener has a hole/seat, accessible driver path, grip, nut engagement, and removal sequence. Purchased envelopes include tab holes, horns, rod ends, screw heads, nuts, and wire exits. A part touching another part is not evidence of fastening.
4. **Motion:** use physical joint transforms; reject closure error above 0.01 mm and branch jumps/toggles. Sweep jaw at ≤1° and eye/lid individual coordinates at ≤2°, plus combined extrema and approach-to-stop cases. State actual sample grids. For collision tests, fail unintended intersection above 0.05 mm³; record smaller overlaps and minimum gaps. Nominal moving clearances target ≥1 mm (cosmetic gaps ≥2 mm) except explicitly budgeted bearing/fit contacts. Any relaxed value needs a tolerance rationale and physical check.
5. **Limits and actuation:** show soft limits inside real hard stops, with travel and polarity linked to firmware channel definitions. Report torque and speed at worst transmission ratio; include both eyes, yoke, tie-bar, horns, rods, hardware, wiring load, friction allowance, and jaw spring. Target holding ≤30% nominal stall, peak ≤50%, speed ≤60% no-load; these are engineering margins, not guaranteed servo ratings. An estimate requires disclosed density, fill, inertia, spring/friction assumptions, and current hardware identity.
6. **Manufacturing:** genuine OPC/3MF containers with valid relationships/model XML, millimetre units, valid indices and all intended build items. Transforms must be applied before bed checks. Minimum Z zero; transformed extents within the 220 mm cube with documented brim/edge spacing. Grouped plates contain every required quantity, allow support/brim space, and name orientation/material/support recommendations. Generic model 3MF must not claim verified slicer settings. Record slicer version, profile, preview checks and G-code status only if actually performed.
7. **Electrical/firmware:** pin/channel map matches diagrams and code; no servo current through ESP32 or PCA logic supply; fuse/disconnect and common-ground return paths explicit; supply calculation includes coincident stalls/starts and audio/logic load. Boot and fault hold OE disabled; disabled PWM is not power isolation. Calibrated endpoints cannot be invented from pulse-angle estimates. Firmware compile and host-test logs identify exact versions and mocks; absent R4/voice source is an explicit integration limit.
8. **Documentation/package:** manual matches final IDs, quantity, hardware location, assembly order, connector polarity and firmware commands. Diagrams originate from final geometry. PDF rendered and visually reviewed. All promised files exist; ZIP opens, manifest hashes match, reproducible build instructions are exercised or marked untested. Final release status distinguishes digital validation from an assembled, measured machine.

## Physical gates before routine use

The physical test log must begin with all results **NOT TESTED**. Print fit coupons first; measure actual servo tabs, horn holes, pins, bearings/rod ends and insert/nut fit. Assemble without power and record full manual travel, end-stop contact, tooth clearance, wiring movement and tool access. Commission one servo at a time with restricted endpoints and a current-limited supply, then weigh moving modules and measure current, supply voltage drop, temperature, backlash and speed. Test power loss, reset, disconnected I²C, motion timeout and actuator-power disconnect. Only after this should simultaneous motion/audio and a documented endurance run be attempted. These outcomes cannot be inferred from compilation, CAD validity, or simulation.

# Mimic R5a-E1
## Assembly and commissioning manual

**Flashforge Adventurer 5M | 220 x 220 x 220 mm | 0.4 mm nozzle | PLA**

This manual accompanies the revised parametric model, print plates, electrical design and commissioning firmware. The approved external appearance is retained. The package records digital engineering work; no head has been printed, assembled, powered or physically qualified by this workflow.

**Release scope:** supervised prototype manufacture and measured commissioning. Actual servo identity, dimensions, spline, voltage/current limits and power-supply rating remain unresolved. The user's tentative markings `sg950` and `mg950` are not interpreted as SG90 or MG90S. Do not order a final mount-compatible servo or energize the assembled mechanism by relying on those names.

![Final revised assembly - three-quarter view](../renders/assembly_three_quarter.png)

## 1. How to use this package

1. Read `README_FIRST.md` and the final validation reports before printing. Release limitations and open issues override historical concept reports.
2. Inventory the parts and hardware in sections 2-4. Confirm the actual servo dimensions against the mechanical interface contract before printing actuator mounts.
3. Print and measure the fit coupons, then print the approved plates in the sequence in section 5. A valid mesh or bed-fit result alone does not establish print success.
4. Assemble the supported mechanism unpowered using section 6. Keep cosmetic covers removable until travel, retention and cable access are checked.
5. Wire and inspect with all supplies isolated. Commission each detached servo before coupling it to the mechanism. The firmware starts with assembled motion locked.
6. Complete `docs/physical_verification.csv` and `firmware/calibration_record.csv`. Enter only measured results. A simulation, compile or host test does not change a physical result from NOT TESTED to PASS.

### Tools and consumables

- Digital caliper, metric ruler, feeler gauges and an angle gauge; record instrument resolution.
- Appropriate metric hex keys, nut drivers and screwdrivers for the actual purchased fasteners and servo OEM screws.
- Deburring knife, flush cutters, small files and hand reamers/drills for measured fit finishing; eye protection when cutting or drilling.
- Pliers, correct crimp tool and terminals, heat-shrink, cable labels and removable strain relief.
- Multimeter, current-limited regulated bench supply and scope or logic analyzer for pulse and reset verification.
- Stable bench support for the head and jaw; the assembly can move or drop when servo torque is absent.
- PLA filament suitable for the chosen profile. Keep lubricant, paint and adhesive off fits, electrical contacts and service joints unless a step expressly requires them.

### Datum and service conventions

Assembly coordinates are X right, Y rear and Z up; the face looks toward -Y. Left/right part names follow the final CAD labels. Match the labeled views and IDs instead of mirroring parts by intuition. Dimensions in this manual and the drawing set are millimetres unless stated otherwise.

The drawing set is a geometry reference from the final STEP parts, with independent orthographic view scales and overall dimensions. Do not measure lengths from the page. Critical fits and fastener stacks come from the source/contract and the assembly steps. The preserved P01/P03 interfaces are extracted from the supplied assembly; the actual original R4 release was not supplied.

Keep modules removable. Do not glue structural joints as a substitute for missing retention or excessive clearance. Record any approved finishing/rework in the physical log and preserve the release files as the baseline for the next revision.

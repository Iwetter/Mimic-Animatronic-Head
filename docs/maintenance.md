## Required physical verification

All initial physical results are **NOT TESTED**. Use `physical_verification.csv` for the build serial number, inspector, date, instruments, measured values and evidence references. Re-run affected checks after changing a printed part, servo, supply, horn index, firmware calibration or motion limit.

1. Confirm hardware identity and supply ratings. Measure body/tab/horn dimensions and connector polarity before committing actuator mount prints. Verify the reference neck interface against the real intended mating part.
2. Print coupons and measure every specified fit. Reject cracked, warped or delaminated parts. Record any drilling/reaming; do not alter an interference blindly.
3. Assemble unpowered. Verify every axle and spline screw is retained, every nut has full engagement, pivots rotate without binding, and tools can reach service fasteners.
4. Move the jaw, eye mechanism and lids manually through their permitted ranges. Check combined extreme poses, tooth clearance, full cable service loops and hard-stop contact. Do not use servo stall to find a stop.
5. Complete electrical continuity, polarity and logic-only reset checks before powering one detached servo. Verify the physical actuator disconnect and OE behavior separately; OE does not remove motor power.
6. Record per-axis measured neutral/end pulses and angles, current, rail voltage, backlash and clearance at conservative speeds. Complete the five-axis combined-envelope review before accepting the firmware mechanical gate.
7. Run the fault checks in section 7 with supported or detached loads. Record timeout, reset, I2C loss and power loss behavior on the real hardware.
8. Run a supervised 100-cycle low-excursion screening sequence, then inspect screws, pivots, printed layers, temperatures and cable wear. The cycle count is an initial commissioning screen, not a service-life rating. Set the next inspection interval from observed wear/load history.
9. Record the final build mass and center-of-mass estimate before considering neck/torso integration. The static socket is not a rated active-neck or humanoid support system. Arms and piano-playing hands require their own actuator, structural and feedback design.

## Troubleshooting

| Observation | Check and corrective action |
| --- | --- |
| `arm PARKED` rejected | Expected until all five measured calibrations and the mechanical-review gate are valid. Do not bypass the gate to make the demonstration run. |
| Servo jumps on enable | Switch off actuator power, support the mechanism and detach the horn. Recheck measured neutral, OEM horn index, pulse waveform and physical parked position. Software cannot know off-state position. |
| Motion stops after about 3 s | External command lease expired. During an intentional bench test send `ping` at least once each second; do not disable timeout protection. |
| Clicking, high current or no motion | Remove actuator power immediately. Check obstruction, hard-stop contact, pivot clamping, cable snag, wrong horn length and stripped spline before retrying. |
| Eye mismatch or excess backlash | Check pinned linkage retention, axle fits, tie-bar length and neutral indexing. A loose drive joint must be repaired before widening limits. |
| Lid rubs or misses coverage | Inspect the actual globe/lid gap at combined gaze extremes; remove paint/support residue from the swept path and verify pivot stack. Do not force clearance by servo torque. |
| Jaw droops or hits neck | Support jaw, isolate actuators and inspect retention and measured limits. Recheck load/current and collision path; never expand to historical 22 deg based on the old brief. |
| ESP32 resets or audio crackles | Measure rail droop and ground routing. Check separate power branches, conductor/connector ratings and transient demand. A larger capacitor alone does not resolve an undersized supply. |
| Loose printed mount | Inspect cracks, compression and fastener engagement. Replace damaged PLA; do not keep tightening until deformation stops. |

## Maintenance and disassembly

Before each session, inspect visible fasteners, servo spline screws, pivot retention, cracks, harness slack and the accessible actuator-power disconnect. Stop if a joint shifts, current rises, or a new noise appears.

For service, park if motion is still reliable, support the head and jaw, switch off the actuator rail, disconnect logic/audio supplies, and verify stored capacitor voltage has discharged. Label connectors before unplugging. Remove cosmetic parts first and work backward through the numbered module assembly steps. Keep pivot spacers and retained hardware with their module.

Do not solvent-clean PLA, heat it to reshape a precision joint, or lubricate electrical connectors. Clean dust with a soft brush. Replace damaged pivots, worn holes, cracked links and frayed cables. Record rework and re-run calibration/combined-envelope checks after replacing any motion component.

Maintain a build history containing source revision/hash, printed material/profile, measured fit results, servo identities, supply specification, calibration record, firmware build and observed wear. Keep the initial R5a concept archive unchanged as provenance; it is not the manufacturing master for revised parts.

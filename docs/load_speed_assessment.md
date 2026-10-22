# Conditional load and speed assessment

Revision R5a-E1. Analytical calculation only; no physical test.

| Axis | Moving mass incl. allowance (g) | Screened demand (N m) | Conditional rated stall target (kg cm) | Motor sweep (deg) |
|---|---:|---:|---:|---:|
| jaw | 59.4 | 0.0349 | 1.42 | 14.0 |
| pitch | 87.4 | 0.0121 | 0.49 | 41.8 |
| lid_L | 7.8 | 0.0052 | 0.21 | 53.8 |
| lid_R | 7.8 | 0.0052 | 0.21 | 53.8 |
| yaw | 37.5 | 0.0071 | 0.29 | 40.0 |

Mass uses a chosen 1.25 g/cm3 solid PLA density and explicit purchased-hardware allowances. Gravity follows CAD centers of mass. The output acceleration is assumed 180 deg/s2; inertia uses an enclosing-radius bound. Virtual work converts output load to motor load using the solved linkage derivative. A chosen friction reserve is included. The 4x stall target is a sizing heuristic; it does not establish continuous-duty capability.

The actual servo markings remain uncertain (reported SG950/MG950). Do not substitute a named microservo specification for measured identification. Compare these targets to the real manufacturer curve at the measured rail voltage, then measure current, temperature, lost motion and margin in the assembled mechanism.

A rapid blink requires both closing and reopening strokes. Minimum time is bounded by actual motor sweep divided by measured loaded speed, with extra acceleration time. The firmware is deliberately calibrated in pulse units; no angular speed claim follows until pulse-to-angle measurements are entered.

## Printed linkage strength screening

| Rod | Ideal pinned Euler load with assumed effective E=500 MPa (N) |
|---|---:|
| P46 pitch pushrod | 9.41 |
| P49 eyelid pushrod | 3.28 |

These ideal values omit end holes, print anisotropy, creep and imperfect straightness. Inspect rods and perform a measured compression/tension proof test with at least the chosen design load margin. No printed-part load rating is released from this calculation.

## Outstanding limits

- No measured servo model, torque-speed curve, supply drop, current or thermal data.
- CAD solid-density mass overestimates infill but may miss cables/fasteners; weigh final assemblies.
- First-order inertia bound omits exact coupled linkage dynamics and compliance.
- No FEA, fatigue, screw pullout, spline or clamp strength qualification.
- Pulse-per-degree mapping is unknown; firmware speed in us/s must be calibrated against actual angles.
- Neck load rating and future torso/arm/hand loads are not established.

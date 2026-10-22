# Mimic R5a engineering architecture

Revision R5a-E1 develops the approved appearance as a serviceable head prototype. The supplied concept archive is retained unchanged. Editable CadQuery source and assembly-coordinate STEP are the geometry authorities; print files are derived only after geometry review. Nothing in this release is a physical test result.

## Modules and interfaces

| Module | Function and service boundary |
|---|---|
| Base, lower/upper side frame and cranial arches | Bolted load path between face, mechanism decks and neck flange. Remove the face and top access pieces to service actuators. |
| Eye cassette | Fixed P36 supports the common-pitch carrier P45. Two metal yaw shafts carry the globes. Equal-radius yaw cranks and independent planar tie links constrain shared yaw; the servo moves with the carrier. This replaces the original spatial linkage's passive freedoms and unreachable rod positions. |
| Pitch drive | Fixed CH2 servo drives the carrier through a planar pushrod. Solve the horn/rod closure rather than assuming motor angle equals eye angle. |
| Eyelids | CH3/CH4 drive separate pinned pushrods. Stops and software margins are independent of eye-gaze control; combined eye/lid poses require checking. |
| Jaw | CH1 drives a retained, supported jaw pivot through its original equipment horn. Removable teeth and a mechanical stop permit inspection before powered operation. |
| Electronics | ESP32 communicates with PCA9685. CH0 yaw, CH1 jaw, CH2 pitch, CH3/4 lids. Separate actuator distribution, common signal reference, external OE pull-up and a physical actuator disconnect. |
| Voice | INMP441 and MAX98357A pins and supply requirements are reserved. The original voice source was not supplied, so working speech integration is an outstanding milestone. |

Servo dimensions are nominal placeholders for a microservo package. The user's tentative SG950/MG950 markings have not established the model, size, voltage, spline or current. Record each actual unit and OEM horn before manufacturing its mounting interfaces. A standard-size servo cannot be accepted by scaling a microservo bracket or forcing it into place.

## Recovered neck and torso boundaries

P01 and P03 are exact named solids recovered from the supplied R5a assembly, not independently verified against an absent standalone R4 release. The head flange uses an 80 x 45 mm rectangular hole pattern; the recovered torso mounting pattern is 46 x 24 mm in the XZ plane. Coordinates, bores, fasteners and cable passages are recorded in the final contract and drawings. Preserve these datums for the next assembly.

Before adding an active neck, weigh the finished head, measure its center of mass relative to the flange, and establish the required acceleration, orientation and fall/rest loads. Size neck bearings, gearing, structure, power and brakes from those measurements. The current printed socket is not a qualified full-humanoid load rating. Neck torque and a stable support fixture must be verified separately.

Torso, arms and piano-playing hands should have separate mechanical load paths, local motor power protection and calibrated motion controllers. Reserve a documented command interface for high-level speech/gaze/expression requests. Keep pulse generation, limits and fault handling local to the head. A future bus protocol must define heartbeat, timestamps, sequence handling, neutral behavior and explicit rearming; those features are not claimed by this standalone serial commissioning firmware.

## Milestones and evidence

1. Digital geometry: rebuild editable source, confirm STEP solid and volume round trips, check joint geometry and solve/sweep the revised mechanism.
2. Manufacturing preparation: export final meshes, validate source agreement, arrange all required quantities, slice actual AD5M/PLA profiles and inspect layer previews.
3. Fit qualification: identify servos/horns and supply; print the coupon; measure holes, shafts, insert seats and mating neck geometry. Revise source if actual hardware differs.
4. Unpowered assembly: record fastener access and engagement, retention, axial play, mechanical stops, combined-motion clearance and cable sweeps.
5. Electrical commissioning: test polarity, rail behavior, OE/reset/timeout behavior, measured pulses and detached actuators; enter measured calibration.
6. Coupled testing: gradually widen one axis at a time, then check combined poses under current/temperature observation. Validate speed, load margin and repeated-cycle reliability before routine operation.

The machine-readable reports and physical-verification log define which evidence exists. A successful CAD Boolean, manifold mesh, firmware compile or slicer run cannot establish assembly fit, torque, durability or safe physical behavior.

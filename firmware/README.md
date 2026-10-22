# Mimic R5a motion firmware — 1.0.0

This is new commissioning firmware, compiled for a **classic ESP32-WROOM-32 / ESP32 Dev Module**. It retains the reported R4 PCA9685 pin/channel interface. The original R4 motion and voice source packages were not supplied, so this is not a verified merge with those programs. No live board was flashed or physically tested. The release is deliberately unable to arm the assembled head until measured calibration is entered.

## Build and flash

Dependencies: Arduino CLI 1.5.1 used for the recorded build; Arduino-ESP32 **2.0.17**, FQBN `esp32:esp32:esp32`. Only core-supplied Wire and watchdog APIs are used. No external Arduino library is required. Keep core 2.0.17 for future legacy I2S voice compatibility; core 3.x requires a deliberate port.

From the release folder, after installing Arduino CLI:

```powershell
arduino-cli core update-index --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32@2.0.17 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli compile --fqbn esp32:esp32:esp32 --build-path "$env:TEMP/Mimic_R5a_build" firmware/Mimic_R5a
arduino-cli board list
```

Keep servo power disconnected during upload. Select the actual listed port; `COM7` below is an example, not an identified device:

```powershell
arduino-cli upload --fqbn esp32:esp32:esp32 --port COM7 --input-dir "$env:TEMP/Mimic_R5a_build" firmware/Mimic_R5a
arduino-cli monitor --port COM7 --config baudrate=115200
```

Alternatively open `Mimic_R5a/Mimic_R5a.ino` in Arduino IDE, select the pinned core and ESP32 Dev Module. Do not choose an ESP32-C3/S3 board for this pin map. No compiled binary is supplied: build the source with the calibration intended for that head.

## States and commands

Use newline-terminated commands, 115200 baud. Commands are case-sensitive. Boot, reset, fault and demo completion disable outputs. `off` disables OE **before** attempting I2C writes. Unknown commands while active fault the controller. A fault requires explicit `off` or `reset`; it never automatically restarts.

| Command | Action / prerequisite |
|---|---|
| `status` | Display state and target pulses; does not renew lease. |
| `off` | Immediate OE HIGH, all PCA channels full-off, cancel demo. |
| `reset` | Reinitialize PCA only while inactive; OE remains HIGH. |
| `commission 0 FREE` | Enable only CH0 at 1500 us. Replace 0 with 0–4. The word FREE confirms the horn/linkage is detached or the start pose is physically proved free. |
| `set 0 1505` | Slew the selected axis toward an integer pulse in its current permitted range. All other enabled axes retain their targets. |
| `ping` | Renew the 3 s external command lease. Send at least once each second while motion remains enabled. |
| `arm PARKED` | Enable all five at their **measured neutral** pulses, only after all calibration/review gates pass and the mechanism is physically parked. |
| `demo` | Twenty-second, slow coordinated neutral/low/neutral/high/neutral sequence. Excursion is 15% toward each measured endpoint. Keep sending `ping`; internal demo targets do not renew the lease. |

`commission` defaults to 1400–1600 us, 20 us/s and 40 us/s². Calibrated default caps are 30 or 40 us/s and 60 or 80 us/s² by axis. These are **electrical command limits, not measured angular speeds**. Actual PWM quantization is about 4.88 us/tick at the nominal oscillator, so very small pulse commands can produce the same output tick. Continuous internal profiles limit velocity and acceleration; a physical servo may still jump, stall or lose tracking. A 1500 us pulse does not imply a known mechanical angle.

## Commission one detached servo first

1. Identify each actual servo marking, voltage, connector polarity, dimensions and spline. The user's `sg950` / `mg950` names are unresolved; do not substitute MG90S or SG90 data without identification. Resolve the supply and protection in `docs/electronics.md` before powering actuators.
2. Wire the 1 kΩ OE pull-up to 3V3. With servo supply OFF, power ESP32/PCA logic. Measure OE HIGH during boot/reset. Verify I2C address 0x40. Check the physical emergency servo-power disconnect.
3. Remove the first servo's horn/linkage or prove the commanded start cannot hit anything. Power only that servo from a current-limited supply within its specified voltage. Send `commission 0 FREE`, then periodic `ping`. At 1500 us inspect for unexpected rotation/current. Use `off` immediately if either occurs.
4. Measure PCA pulse and period with a scope/logic analyzer. Nominal prescale 121 with 25 MHz oscillator gives 50.0288 Hz. If measured oscillator differs, update `kPcaOscillatorHz` before collecting calibration. The prescale is explicit and pulses use its real nominal period; no generic us/degree conversion is used.
5. Use `set 0 1505`, observe, then widen in 5 us target increments. Check free travel, load current and heat at each step. `kCommissionMinimumUs`/`MaximumUs` may be expanded **10–20 us at a time**, only after the previous range is physically checked. Rebuild/reflash with servo supply OFF. The 900–2100 us absolute software envelope is not a servo specification.
6. While the servo is holding the measured assembly neutral, install its OEM horn, retain the OEM spline screw, and attach linkage with actuator power isolated. Manually support the mechanism against dropping. Repeat with the linkage assembled, one channel at a time and a narrower safe range. Enter any off-state neutral carefully: re-enabling does not know actual position.
7. Measure the output angle with an angle gauge at both permitted limits and neutral. Stop short of the mechanism stops, allowing measured backlash, elastic flex and PWM quantization. Record pulses, actual output angles, direction, supply voltage/current and clearance in `calibration_record.csv`. Check the final mechanical contract; nominal yaw/pitch/jaw/lid angles are not pulse conversions.
8. Set each `AxisCalibration` row to the **measured** minimum/neutral/maximum pulses and `measured=true`. A neutral is allowed at an endpoint (e.g. jaw closed), but minimum must be less than maximum. Keep the measured caps conservative. The source rejects caps above 100 us/s or 200 us/s²; increases beyond those require engineering review and tests.
9. Validate every permitted combined corner pose, cables, stops, lid/globe spacing, jaw/neck clearance and load current. Only then set `kMechanicalReviewAccepted=true`. This gate asserts the full five-dimensional calibrated envelope is physically acceptable; separate single-axis tests alone do not establish it.
10. Place all axes physically at their recorded neutral, support the head, send `arm PARKED`, keep `ping` running, then request `demo`. Observe the slow sequence before increasing excursion/speed. Do not run unattended.

## Fault behavior and limitations

- A missing external command for more than 3 s, main-loop gap over 100 ms, I2C NACK/readback mismatch, PCA mode/prescale change, invalid target, invalid active command or line overflow disables OE. Every PWM batch checks MODE1 auto-increment/sleep bits, MODE2 and PRE_SCALE before writing pulses; this includes the batch before OE is enabled. Pin/channel constants are in `PinMap.h`.
- A 2 s task watchdog resets a hung CPU; the external pull-up then holds OE high. No software or this non-safety-rated controller guarantees a stop time under every electrical fault. PCA9685 continues generating pulses independently of the ESP32 until OE changes or servo power is removed.
- OE disables control pulses, **not servo power**. Behavior after lost pulses depends on the actual servo. Gravity loads can fall when torque is removed. Use the physical actuator-power disconnect and supports for work near moving parts.
- There is no encoder, limit-switch, current or voltage feedback. Firmware cannot detect a jam, stripped horn, stalled servo, wrong neutral, physical stop contact or servo-supply dip. The supplied electrical design therefore requires supervised bench validation; it is not a protective control system.
- The I2S pins26/25/34/32 are reserved and untouched. No network, cloud credential, microphone capture, speaker playback, audio check or voice integration is claimed. Import the actual voice source later, retain this motion supervisor, then compile and repeat fault/timing tests under audio load.

## Verification

`validation/firmware_compile.log` records the real ESP32 build. The host tests compile the shared motion core and the **actual sketch** against mocked Arduino/Wire interfaces. Re-run from the release folder with Python and g++:

```powershell
python scripts/test_firmware.py --build-dir "$env:TEMP/Mimic_R5a_host_tests"
```

Covered behaviors include default calibration lock, single-channel enable, range rejection, acceleration/speed limits through reversal, five-channel movement, timeout and millis wrap, loop overrun, startup full-off, invalid serial commands, I2C faults/readback corruption, demo lease behavior and off/reset recovery. Mocks do not establish real pin timing, electrical protection, waveform accuracy, loaded servo behavior or mechanical safety.

Physical bench acceptance must include the matrix in `docs/electronics.md`. Record measured results before marking any item physically passed.

Official references: [Arduino ESP32 2.0.17](https://github.com/espressif/arduino-esp32/releases/tag/2.0.17), [NXP PCA9685 datasheet](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf), [legacy ESP-IDF I2S API](https://docs.espressif.com/projects/esp-idf/en/v4.4.2/esp32/api-reference/peripherals/i2s.html).

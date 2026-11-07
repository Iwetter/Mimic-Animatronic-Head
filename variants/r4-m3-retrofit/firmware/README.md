# ESP32 commissioning and slow demo

Open `Mimic_ESP32/Mimic_ESP32.ino`. The head uses two MG90S position servos:
PCA9685 channel **0 = linked eyes**, channel **1 = jaw**. The remaining channels
are disabled. The printed mechanism is revision R4.

## Identify the ESP32 before wiring

The supplied default is a **classic ESP32 DevKit using ESP32-WROOM-32**, built as
**ESP32 Dev Module**. A board having about 38 pins does not identify its chip.
Check the metal module marking and board labels before connecting it. The
numbers below are **GPIO numbers, not positions along a connector**. This wiring
is not a pin map for ESP32-C3, ESP32-S3, ESP32-S2 or ESP32-CAM boards. If the board
is one of those, its target and pins must be adapted before use.

## Wire with power disconnected

| Connection | Destination |
| --- | --- |
| ESP32 **3V3** | PCA9685 **VCC**, logic power |
| ESP32 **GPIO21** | PCA9685 **SDA** |
| ESP32 **GPIO22** | PCA9685 **SCL** |
| ESP32 **GPIO27** | PCA9685 **OE** |
| **1 kohm resistor** | Between PCA9685 **OE** and ESP32 **3V3** |
| ESP32 **GND** | PCA9685 **GND** and external supply **negative** |
| External regulated **5 V positive** | PCA9685 servo **V+**, preferably its screw terminal |
| Eye MG90S plug | PCA9685 channel **0**, matching signal / V+ / GND labels |
| Jaw MG90S plug | PCA9685 channel **1**, matching signal / V+ / GND labels |
| ESP32 USB | Computer, for controller power and Serial Monitor |

PCA9685 **VCC is 3.3 V logic; V+ is 5 V servo power**. Keep the positive rails
separate. Never connect servo 5 V to ESP32 3V3, a GPIO, or PCA9685 VCC. Servo
power comes from the external supply, not the ESP32. Connect all grounds.
Read the supply's current rating before operating both servos under load.

The 1 kohm pull-up holds outputs disabled while the ESP32 resets; OE high
disables pulses, and OE low permits them. Inspect your particular module first:
OE must not be hard-wired to ground. The resistor must overcome any weak OE
pull-down on the board. Check OE stays high during reset before connecting the
servos. This disables signal pulses, not servo power; unplug the external supply
before handling the linkage. Some servo clones respond poorly to 3.3 V signals;
verify your servo's behavior during detached-horn commissioning.

## Install and upload

1. In Arduino IDE Preferences, add the official stable Boards Manager URL:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
2. Install **esp32 by Espressif Systems, version 2.0.17** in Boards Manager. This
   is the version used for the delivered compile check, not a claim that it is
   the latest release.
3. In Library Manager install **Adafruit PWM Servo Driver Library 3.0.3** and
   **Adafruit BusIO 1.17.4**.
4. Open `Mimic_ESP32/Mimic_ESP32.ino`, choose **ESP32 Dev Module** and your
   board's port. Leave default board options. Keep servo power disconnected
   while uploading; only upload after confirming a classic ESP32 board.
5. Open Serial Monitor at **115200 baud**. The normal message says outputs are
   OFF. It will not move automatically. The firmware reports a missing PCA9685
   or failed I2C configuration and keeps OE high if startup checks fail.

Arduino CLI target: `esp32:esp32:esp32`. The verified build uses core 2.0.17,
Arduino CLI 1.5.1, and the library versions above. The compile log and structured
validation record are in `../checks/`. No hardware upload or movement test has
been performed. Additionally, 22 host logic checks executed the supplied sketch
with mocked Arduino/I2C interfaces, covering boot inhibition, command guards,
selection, stop behavior and startup/write faults. These checks do not verify
real wiring, timing, servo response or mechanical movement. Their source and
run instructions are in `../checks/firmware_host_logic/`.

## Commands and calibration

| Command | Action |
| --- | --- |
| `0` | Select eyes and disable both channels |
| `1` | Select jaw and disable both channels |
| `c` | Enable only the selected servo at nominal 1500 us before calibration |
| `+` / `-` | Nudge selected servo by 5 us inside the guard |
| `p` | Print selection, last pulses and enabled state |
| `x` | Disable every output and stop the demo |
| `r` | Start the slow demo only after measured calibration is enabled |

Line endings and spaces are ignored. The initial guard is **1400-1600 us**;
all five saved positions are initially 1500 us, and `CALIBRATED=false` locks the
demo. Pulse values are microseconds, not degrees.

1. Detach both horns and all linkages before the first `c`. Connect one servo
   at a time. Send `0`, then `c` to center the eye servo; send `x` to disable it.
   Repeat with the jaw servo using `1`, then `c`. A first center command can
   move an uncentered shaft immediately.
2. Disconnect servo power. Install the stock horns in the neutral orientation
   described in the assembly guide, then fit their linkages. Support the jaw
   while outputs are off; it may move under gravity.
3. Check one mechanism at a time using 5 us nudges. Stop before contact, buzzing
   or strain. The geometric design ranges are eye yaw +/-18 degrees and jaw
   opening 0-20 degrees. These are mechanism angles, not servo pulse mappings.
   The initial 1400-1600 us guard does **not** promise this full travel. With the
   bare mechanism checked free, calibrate one axis at a time. If more travel is
   needed, extend one guard endpoint deliberately by **10-20 us**, recompile and
   upload, then test from the last verified free pose. Recheck the horn alignment
   and the entire linkage at every step. There is no automatic widening. Do not
   calculate final endpoints from an assumed microseconds-per-degree value.
4. Record five measured positions below, with endpoints short of mechanical
   contact. Edit the corresponding constants in the sketch. Keep each within
   the guard. Set `CALIBRATED=true` only after checking the complete mechanism.
5. Recompile and upload with servo power disconnected. Put the mechanism in its
   neutral pose before `r`: the demo first commands both saved neutral values,
   then ramps slowly between the measured limits at 1 us per 20 ms. A jaw sweep
   may take several seconds, depending on your measured pulse span. `x` stops
   pulses. A `+` or
   `-` during the demo stops and disables it; select and center before nudging.

| Constant | Your measured pulse (us) |
| --- | --- |
| `EYE_LEFT_US` | __________ |
| `EYE_CENTER_US` | __________ |
| `EYE_RIGHT_US` | __________ |
| `JAW_CLOSED_US` | __________ |
| `JAW_OPEN_US` | __________ |

The demo requires distinct eye endpoints with the center strictly between them,
and distinct jaw endpoints. Either servo direction is supported. After setting
calibration, `c` uses the saved eye center or jaw closed value. PCA9685 oscillator
variation makes pulse values nominal, so calibrate with your actual board at the
sketch's 50 Hz setting. On an I2C write failure the sketch raises OE and locks
motion until reset. The firmware supplies manual commissioning and a slow demo;
it has no microphone response or wireless control yet.

## Primary references

- [Espressif installation instructions](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html)
- [Espressif I2C API: pin selection and timeout in milliseconds](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/i2c.html)
- [Arduino-ESP32 2.0.17 Wire API source](https://github.com/espressif/arduino-esp32/blob/2.0.17/libraries/Wire/src/Wire.h)
- [Adafruit PCA9685 power and control pin guide](https://learn.adafruit.com/16-channel-pwm-servo-driver?view=all)

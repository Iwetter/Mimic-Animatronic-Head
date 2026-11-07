/* Mimic-inspired head R4 - classic ESP32 DevKit / ESP32-WROOM-32 + PCA9685.
   Two MG90S position servos: eye = channel 0, jaw = channel 1.
   Serial Monitor: 115200 baud. No automatic motion after power-up.
   GPIO21->SDA, GPIO22->SCL, GPIO27->OE, 3V3->VCC, GND->GND.
   Add 1k ohm from OE to 3V3 (overrides a typical weak OE pull-down).
   External regulated 5V -> servo V+; all grounds common.
   Servo 5V must NOT connect to ESP32 3V3, GPIO, or PCA9685 logic VCC.
   Check the actual module: OE must not be hard-wired to ground.
   This pin map is for a classic ESP32, not an ESP32-C3/S3/CAM board.

   First calibration: detach horns and linkages before the first 'c'.
   0/1 selects a servo and disables both; c centers the selected servo;
   +/- nudges 5 us; x disables all pulses; p prints state; r starts a slow
   demo only after CALIBRATED is true and distinct measured limits are set.
   All calibration values are microseconds, NOT angles.
   Compiled for ESP32 Dev Module; not tested on the physical mechanism.
*/
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Edit ONLY after measuring your own mechanism. Defaults do not run a demo.
constexpr bool CALIBRATED = false;
// This small initial guard is for commissioning, not the full CAD travel.
// With the bare mechanism checked free, calibrate one axis at a time. If needed,
// extend one guard endpoint deliberately by 10-20 us, recompile/upload and test
// from the last verified free pose. Never derive endpoints from us/degree alone.
constexpr int GUARD_MIN_US = 1400;
constexpr int GUARD_MAX_US = 1600;
constexpr int EYE_LEFT_US = 1500;
constexpr int EYE_CENTER_US = 1500;
constexpr int EYE_RIGHT_US = 1500;
constexpr int JAW_CLOSED_US = 1500;
constexpr int JAW_OPEN_US = 1500;
constexpr uint8_t SDA_PIN = 21;
constexpr uint8_t SCL_PIN = 22;
constexpr uint8_t OE_PIN = 27;
constexpr uint32_t I2C_HZ = 100000UL;
constexpr uint16_t I2C_TIMEOUT_MS = 25;
constexpr uint8_t PCA_ADDRESS = 0x40;
constexpr uint32_t OSCILLATOR_HZ = 25000000UL;

Adafruit_PWMServoDriver pwm(PCA_ADDRESS);
bool ready = false, active[2] = {false, false}, demo = false;
uint8_t selected = 0, pose = 0;
int currentUs[2] = {1500, 1500};
int targetUs[2] = {1500, 1500};
uint8_t prescale = 121;
uint32_t lastStepMs = 0, reachedMs = 0;
bool atPose = false;

bool inGuard(int us) { return us >= GUARD_MIN_US && us <= GUARD_MAX_US; }

void stopOutputs() {
  // OE first: disabling pulses must not depend on an I2C transaction.
  digitalWrite(OE_PIN, HIGH);
  demo = false;
  active[0] = active[1] = false;
  if (ready) {
    bool cleared = true;
    for (uint8_t ch = 0; ch < 16; ++ch) {
      if (pwm.setPWM(ch, 0, 4096) != 0) cleared = false;
    }
    if (!cleared) {
      ready = false;
      Serial.println(F("I2C clear failed. OE stays disabled; check wiring and reset."));
    }
  }
}

bool readRegister(uint8_t reg, uint8_t &value) {
  Wire.beginTransmission(PCA_ADDRESS);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(PCA_ADDRESS, uint8_t(1), uint8_t(true)) != 1) return false;
  value = uint8_t(Wire.read());
  return true;
}

bool writeUs(uint8_t ch, int us) {
  if (!ready || ch > 1 || !inGuard(us)) return false;
  // Use the actual frequency divider. Pulse widths are nominal until
  // measured; calibration absorbs oscillator variation on clone boards.
  const float ticksPerUs = float(OSCILLATOR_HZ) / (prescale + 1) / 1000000.0f;
  const uint16_t ticks = uint16_t(us * ticksPerUs + 0.5f);
  if (pwm.setPWM(ch, 0, ticks) != 0) {
    stopOutputs();
    ready = false;
    Serial.println(F("I2C write failed. Outputs disabled; check wiring and reset."));
    return false;
  }
  currentUs[ch] = us;
  return true;
}

bool validDemo() {
  const int lowEye = min(EYE_LEFT_US, EYE_RIGHT_US);
  const int highEye = max(EYE_LEFT_US, EYE_RIGHT_US);
  return CALIBRATED && inGuard(EYE_LEFT_US) && inGuard(EYE_CENTER_US) &&
    inGuard(EYE_RIGHT_US) && inGuard(JAW_CLOSED_US) && inGuard(JAW_OPEN_US) &&
    lowEye < EYE_CENTER_US && EYE_CENTER_US < highEye &&
    JAW_CLOSED_US != JAW_OPEN_US;
}

void choosePose(uint8_t next) {
  pose = next % 6;
  targetUs[0] = EYE_CENTER_US;
  targetUs[1] = JAW_CLOSED_US;
  switch (pose) {
    case 1: targetUs[0] = EYE_LEFT_US; break;
    case 2: targetUs[0] = EYE_LEFT_US; targetUs[1] = JAW_OPEN_US; break;
    case 3: targetUs[0] = EYE_RIGHT_US; break;
    case 4: targetUs[0] = EYE_RIGHT_US; targetUs[1] = JAW_OPEN_US; break;
    default: break;
  }
  atPose = false;
}

void printState() {
  Serial.print(F("Selected ")); Serial.print(selected);
  Serial.print(F(" | eye ")); Serial.print(currentUs[0]);
  Serial.print(active[0] ? F(" ON") : F(" OFF"));
  Serial.print(F(" | jaw ")); Serial.print(currentUs[1]);
  Serial.print(active[1] ? F(" ON") : F(" OFF"));
  Serial.print(F(" | guard ")); Serial.print(GUARD_MIN_US);
  Serial.print('-'); Serial.println(GUARD_MAX_US);
}

void handleCommand(char command) {
  if (command == '\r' || command == '\n' || command == ' ') return;
  if (command == 'x' || command == 'X') {
    stopOutputs(); Serial.println(F("All pulses OFF.")); return;
  }
  if (command == 'p') { printState(); return; }
  if (command == '0' || command == '1') {
    stopOutputs(); selected = command - '0'; printState(); return;
  }
  if (!ready) { Serial.println(F("Driver unavailable. Check wiring and reset.")); return; }
  if (command == 'c') {
    stopOutputs();
    const int center = CALIBRATED ? (selected == 0 ? EYE_CENTER_US : JAW_CLOSED_US) : 1500;
    if (writeUs(selected, center)) {
      active[selected] = true;
      digitalWrite(OE_PIN, LOW);
    }
    printState();
  } else if (command == '+' || command == '-') {
    if (demo) { stopOutputs(); Serial.println(F("Demo stopped. Select and center first.")); return; }
    if (!active[selected]) { Serial.println(F("Use c with horn detached before nudging.")); return; }
    const int next = currentUs[selected] + (command == '+' ? 5 : -5);
    if (!inGuard(next)) { Serial.println(F("Guard reached. No movement.")); return; }
    writeUs(selected, next); printState();
  } else if (command == 'r') {
    if (!validDemo()) {
      Serial.println(F("Demo locked. Measure all 5 positions and set CALIBRATED=true.")); return;
    }
    stopOutputs();
    // Starting the demo deliberately goes to the recorded neutral pose.
    // Use c on both channels first, then attach horns in their neutral pose.
    if (!writeUs(0, EYE_CENTER_US) || !writeUs(1, JAW_CLOSED_US)) return;
    active[0] = active[1] = true;
    choosePose(0); demo = true; lastStepMs = millis();
    digitalWrite(OE_PIN, LOW);
    Serial.println(F("Slow demo. x stops immediately."));
  } else {
    Serial.println(F("0/1 select; c center; +/- 5us; p state; r calibrated demo; x OFF"));
  }
}

void setup() {
  digitalWrite(OE_PIN, HIGH);
  pinMode(OE_PIN, OUTPUT);
  Serial.begin(115200);
  // setPins also preserves the chosen pins if a library calls Wire.begin().
  if (!Wire.setPins(SDA_PIN, SCL_PIN) || !Wire.begin(SDA_PIN, SCL_PIN, I2C_HZ)) {
    Serial.println(F("I2C initialization failed. OE stays disabled.")); return;
  }
  Wire.setTimeOut(I2C_TIMEOUT_MS); // ESP32 API uses milliseconds.
  ready = pwm.begin();
  if (!ready) {
    Serial.println(F("PCA9685 missing at 0x40. OE stays disabled.")); return;
  }
  pwm.setOscillatorFrequency(OSCILLATOR_HZ);
  pwm.setPWMFreq(50);
  pwm.setOutputMode(true); // Actively driven 3.3 V servo signal.
  // Read back the 50 Hz divider and mode with checked I2C transactions.
  // The library's readPrescale() alone does not report I2C read failures.
  uint8_t mode1 = 0, mode2 = 0;
  if (!readRegister(0xFE, prescale) || !readRegister(0x00, mode1) ||
      !readRegister(0x01, mode2) || prescale != 121 ||
      (mode1 & 0x10) || !(mode1 & 0x20) || !(mode2 & 0x04)) {
    ready = false;
    Serial.println(F("PCA9685 configuration check failed. OE stays disabled.")); return;
  }
  stopOutputs();
  if (!ready) return;
  if (GUARD_MIN_US >= GUARD_MAX_US || !inGuard(1500)) {
    ready = false; Serial.println(F("Invalid guard. Restore a range containing 1500 us.")); return;
  }
  Serial.println(F("Mimic R4 ESP32 ready, outputs OFF. Detach horns before first c."));
  Serial.println(F("Configured pulse guard is a commissioning limit, not a travel guarantee."));
  Serial.println(F("0/1 select; c center; +/- 5us; p state; r calibrated demo; x OFF"));
}

void loop() {
  while (Serial.available()) handleCommand(char(Serial.read()));
  if (!demo || !ready) return;
  const uint32_t now = millis();
  if (uint32_t(now - lastStepMs) < 20) return;
  lastStepMs = now;
  bool arrived = true;
  for (uint8_t ch = 0; ch < 2; ++ch) {
    if (currentUs[ch] != targetUs[ch]) {
      arrived = false;
      const int next = currentUs[ch] + (targetUs[ch] > currentUs[ch] ? 1 : -1);
      if (!writeUs(ch, next)) return;
    }
  }
  if (!arrived) { atPose = false; return; }
  if (!atPose) { reachedMs = now; atPose = true; }
  if (uint32_t(now - reachedMs) >= 1200) choosePose(pose + 1);
}

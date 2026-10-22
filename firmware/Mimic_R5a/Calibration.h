#pragma once
#include <stdint.h>

namespace mimic {
struct AxisCalibration {
  uint16_t minimumUs, neutralUs, maximumUs;
  float maxSpeedUsPerSecond, maxAccelerationUsPerSecond2;
  bool measured;
};
// Deliberately non-actuating release defaults. Replace only with measured data.
// Names and channel order are fixed; pulse direction is measured, not assumed.
static const AxisCalibration kCalibration[5] = {
  {1500, 1500, 1500, 40, 80, false},  // CH0 linked eye yaw
  {1500, 1500, 1500, 30, 60, false},  // CH1 jaw
  {1500, 1500, 1500, 30, 60, false},  // CH2 linked eye pitch
  {1500, 1500, 1500, 40, 80, false},  // CH3 left upper lid
  {1500, 1500, 1500, 40, 80, false}   // CH4 right upper lid
};
static const bool kMechanicalReviewAccepted = false;
// Widen one channel by 10-20 us only after its prior range is physically checked.
// 900..2100 is a software envelope, NOT a claim that any servo/linkage accepts it.
static const uint16_t kCommissionMinimumUs[5] = {1400,1400,1400,1400,1400};
static const uint16_t kCommissionMaximumUs[5] = {1600,1600,1600,1600,1600};
// Measure actual PCA clock/pulse width before recording endpoint calibration.
static const uint32_t kPcaOscillatorHz = 25000000;
static const uint8_t kPcaPrescale = 121; // nominal 50.029 Hz, not exactly 50 Hz
static const uint32_t kCommandLeaseMs = 3000;
static const uint32_t kMaxLoopGapMs = 100;
}

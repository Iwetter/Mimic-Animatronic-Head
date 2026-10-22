#pragma once
#include <stdint.h>
namespace mimic {
static const uint8_t kSdaPin=21, kSclPin=22, kOePin=27, kPcaAddress=0x40;
static const uint8_t kI2sBclkPin=26, kI2sWsPin=25, kI2sMicDataPin=34, kI2sAmpDataPin=32;
static const uint8_t kYawChannel=0, kJawChannel=1, kPitchChannel=2;
static const uint8_t kLeftLidChannel=3, kRightLidChannel=4;
static const uint8_t kAxisCount=5;
}

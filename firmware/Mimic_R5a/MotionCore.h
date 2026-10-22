#pragma once
#include <stdint.h>
#include <math.h>
#include "Calibration.h"

namespace mimic {
enum class Mode { Off, Commission, Armed, Fault };
struct AxisState { float position, velocity, target; bool enabled; };
class MotionCore {
 public:
  AxisState axis[5];
  Mode mode = Mode::Off;
  const char* reason = "power-up: outputs disabled";
  uint32_t lastCommand = 0;
  explicit MotionCore(const AxisCalibration* calibration=kCalibration,
                      bool mechanicalReview=kMechanicalReviewAccepted)
      : cfg(calibration), reviewed(mechanicalReview) { off(); }
  void off() {
    for (int i=0;i<5;i++) axis[i]={float(cfg[i].neutralUs),0,float(cfg[i].neutralUs),false};
    mode=Mode::Off; reason="off";
  }
  void fail(const char* why) {
    for (auto& a:axis) {a.enabled=false; a.velocity=0;}
    mode=Mode::Fault; reason=why;
  }
  bool active() const {return mode==Mode::Armed || mode==Mode::Commission;}
  void heartbeat(uint32_t now) {lastCommand=now;}
  bool validCalibration() const {
    if (!reviewed) return false;
    for(int i=0;i<5;i++) {
      const auto& c=cfg[i];
      if(!c.measured || c.minimumUs<900 || c.maximumUs>2100 ||
         c.minimumUs>=c.maximumUs || c.neutralUs<c.minimumUs || c.neutralUs>c.maximumUs ||
         !isfinite(c.maxSpeedUsPerSecond) || !isfinite(c.maxAccelerationUsPerSecond2) ||
         c.maxSpeedUsPerSecond<=0 || c.maxSpeedUsPerSecond>100 ||
         c.maxAccelerationUsPerSecond2<=0 || c.maxAccelerationUsPerSecond2>200) return false;
    }
    return true;
  }
  bool commission(unsigned n, uint32_t now) {
    if(mode!=Mode::Off || n>=5) return false;
    if(kCommissionMinimumUs[n]<900 || kCommissionMaximumUs[n]>2100 ||
       kCommissionMinimumUs[n]>1500 || kCommissionMaximumUs[n]<1500) return false;
    axis[n]={1500,0,1500,true};
    mode=Mode::Commission; heartbeat(now); return true;
  }
  bool arm(uint32_t now) {
    if(mode!=Mode::Off || !validCalibration()) return false;
    for(int i=0;i<5;i++) axis[i]={float(cfg[i].neutralUs),0,float(cfg[i].neutralUs),true};
    mode=Mode::Armed; heartbeat(now); return true;
  }
  bool target(unsigned n, float us, uint32_t now) {
    if(!active() || n>=5 || !axis[n].enabled || !isfinite(us)) return false;
    float lo=mode==Mode::Commission?kCommissionMinimumUs[n]:cfg[n].minimumUs;
    float hi=mode==Mode::Commission?kCommissionMaximumUs[n]:cfg[n].maximumUs;
    if(us<lo || us>hi) {fail("target outside calibrated limits");return false;}
    axis[n].target=us; heartbeat(now); return true;
  }
  bool step(uint32_t now, uint32_t elapsedMs) {
    if(!active()) return true;
    if(uint32_t(now-lastCommand)>kCommandLeaseMs) {fail("command lease expired");return false;}
    if(elapsedMs>kMaxLoopGapMs) {fail("control loop overrun");return false;}
    if(elapsedMs==0) return true;
    // Small fixed internal steps bound integration and reversal acceleration.
    unsigned count=(elapsedMs+1)/2;
    float dt=elapsedMs*0.001f/count;
    for(unsigned j=0;j<count;j++) for(int i=0;i<5;i++) {
      auto& a=axis[i]; if(!a.enabled) continue;
      float vmax=mode==Mode::Commission?20.0f:cfg[i].maxSpeedUsPerSecond;
      float accel=mode==Mode::Commission?40.0f:cfg[i].maxAccelerationUsPerSecond2;
      float delta=a.target-a.position;
      // Smooth critically damped target controller with explicit speed and acceleration caps.
      // Requested acceleration reverses gradually; never snaps position to a new target.
      float acceleration=16.0f*delta-8.0f*a.velocity;
      acceleration=fmaxf(-accel,fminf(accel,acceleration));
      float v=fmaxf(-vmax,fminf(vmax,a.velocity+acceleration*dt));
      float p=a.position+(a.velocity+v)*0.5f*dt;
      float lo=mode==Mode::Commission?float(kCommissionMinimumUs[i]):float(cfg[i].minimumUs);
      float hi=mode==Mode::Commission?float(kCommissionMaximumUs[i]):float(cfg[i].maximumUs);
      if(p<lo-0.001f || p>hi+0.001f || !isfinite(p)) {
        fail("trajectory reached travel boundary"); return false;
      }
      a.position=fmaxf(lo,fminf(hi,p)); a.velocity=v;
    }
    return true;
  }
 private:
  const AxisCalibration* cfg;
  bool reviewed;
};
}

#include "../../firmware/Mimic_R5a/MotionCore.h"
#include <stdio.h>
#include <stdlib.h>
#include <limits>
int assertions=0;
#define CHECK(x) do {++assertions;if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
using namespace mimic;
int main() {
 MotionCore defaultCore;
 CHECK(defaultCore.mode==Mode::Off);CHECK(!defaultCore.active());
 CHECK(!defaultCore.validCalibration());CHECK(!defaultCore.arm(0));
 CHECK(!defaultCore.target(0,1500,0));CHECK(!defaultCore.commission(5,0));
 CHECK(defaultCore.commission(2,0));
 for(int i=0;i<5;i++) CHECK(defaultCore.axis[i].enabled==(i==2));
 CHECK(!defaultCore.commission(0,0));CHECK(!defaultCore.target(1,1500,0));
 CHECK(!defaultCore.target(2,std::numeric_limits<float>::quiet_NaN(),0));
 CHECK(!defaultCore.target(2,1601,0));CHECK(defaultCore.mode==Mode::Fault);
 for(auto& a:defaultCore.axis) CHECK(!a.enabled);
 defaultCore.off();CHECK(defaultCore.commission(0,0));
 CHECK(defaultCore.step(3000,20));CHECK(!defaultCore.step(3001,1));
 CHECK(defaultCore.mode==Mode::Fault);
 defaultCore.off();CHECK(defaultCore.commission(0,0));
 CHECK(!defaultCore.step(101,101));CHECK(!defaultCore.active());
 // Unsigned elapsed arithmetic must survive the millis() wrap.
 defaultCore.off();CHECK(defaultCore.commission(0,0xFFFFFF00u));
 CHECK(defaultCore.step(0x100u,20));
 CHECK(!defaultCore.step(0x1000u,20));
 AxisCalibration measured[5];
 for(auto& c:measured)c={1400,1500,1600,40,80,true};
 MotionCore reviewMissing(measured,false);CHECK(!reviewMissing.arm(0));
 measured[4].measured=false; MotionCore missing(measured,true);CHECK(!missing.arm(0));
 measured[4].measured=true;measured[4].maximumUs=2200;
 MotionCore invalid(measured,true);CHECK(!invalid.arm(0));
 measured[4].maximumUs=1600;measured[4].maxSpeedUsPerSecond=std::numeric_limits<float>::infinity();
 MotionCore inf(measured,true);CHECK(!inf.arm(0));measured[4].maxSpeedUsPerSecond=40;
 MotionCore m(measured,true);CHECK(m.validCalibration());CHECK(m.arm(0));
 CHECK(m.target(0,1590,0));
 float priorPosition=m.axis[0].position,priorVelocity=0;
 for(uint32_t now=20;now<=20000;now+=20) {
   if(now==500) CHECK(m.target(0,1410,now)); // reversal while already moving
   if(now==11000) CHECK(m.target(0,1590,now));
   m.heartbeat(now);CHECK(m.step(now,20));
   CHECK(fabs(m.axis[0].velocity)<=40.001);
   CHECK(fabs(m.axis[0].velocity-priorVelocity)<=80*0.02+0.001);
   CHECK(fabs(m.axis[0].position-priorPosition)<=40*0.02+0.001);
   CHECK(m.axis[0].position>=1400 && m.axis[0].position<=1600);
   priorVelocity=m.axis[0].velocity;priorPosition=m.axis[0].position;
 }
 CHECK(fabs(m.axis[0].position-1590)<0.1);
 CHECK(!m.target(0,1399,20000));CHECK(m.mode==Mode::Fault);
 for(auto& a:m.axis)CHECK(!a.enabled);
 m.off();CHECK(m.arm(0));
 for(int i=0;i<5;i++) CHECK(m.target(i,i%2?1420:1580,0));
 for(uint32_t t=20;t<6000;t+=20){m.heartbeat(t);CHECK(m.step(t,20));}
 for(int i=0;i<5;i++) CHECK(fabs(m.axis[i].position-(i%2?1420:1580))<0.2);
 m.off();for(auto& a:m.axis)CHECK(!a.enabled && a.velocity==0);
 printf("{\"suite\":\"motion\",\"assertions\":%d,\"passed\":true}\n",assertions);
}

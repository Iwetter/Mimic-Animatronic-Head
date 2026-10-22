#include "Arduino.h"
#include "Wire.h"
#include <stdlib.h>
uint32_t mockMillis=0;int mockOe=-1;MockSerial Serial;MockWire Wire;
#include "../Mimic_R5a/Mimic_R5a.ino"
int assertions=0;
#define CHECK(x) do{++assertions;if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
void cmd(const char* s){char local[96];snprintf(local,sizeof(local),"%s",s);command(local);}
int main(){
 setup();CHECK(mockOe==HIGH);CHECK(pcaReady);CHECK(!motion.active());
 CHECK(mimic::kSdaPin==21 && mimic::kSclPin==22 && mimic::kOePin==27 && mimic::kPcaAddress==0x40);
 CHECK(mimic::kI2sBclkPin==26 && mimic::kI2sWsPin==25 && mimic::kI2sMicDataPin==34 && mimic::kI2sAmpDataPin==32);
 CHECK(mimic::kYawChannel==0 && mimic::kJawChannel==1 && mimic::kPitchChannel==2 && mimic::kLeftLidChannel==3 && mimic::kRightLidChannel==4);
 for(int c=0;c<16;c++)CHECK(Wire.registers[9+4*c]==0x10);
 cmd("arm PARKED");CHECK(mockOe==HIGH);CHECK(!motion.active());
 cmd("commission 0 FREE");CHECK(mockOe==LOW);CHECK(motion.active());
 for(int c=1;c<16;c++)CHECK(Wire.registers[9+4*c]==0x10);
 cmd("set 0 1601");CHECK(mockOe==HIGH);CHECK(motion.mode==mimic::Mode::Fault);
 cmd("off");CHECK(mockOe==HIGH);CHECK(motion.mode==mimic::Mode::Off);
 cmd("commission 1 FREE");CHECK(mockOe==LOW);
 cmd("set 1 1510");mockMillis+=20;loop();CHECK(motion.axis[1].position>1500);
 cmd("bad-command");CHECK(mockOe==HIGH);CHECK(!motion.active());
 cmd("off");cmd("commission 2 FREE");CHECK(mockOe==LOW);
 Wire.fail=true;mockMillis+=20;loop();CHECK(mockOe==HIGH);CHECK(!motion.active());
 Wire.fail=false;cmd("reset");CHECK(pcaReady);CHECK(mockOe==HIGH);
 Wire.corrupt=true;cmd("commission 3 FREE");CHECK(mockOe==HIGH);CHECK(!motion.active());
 Wire.corrupt=false;cmd("reset");cmd("commission 4 FREE");
 CHECK(mockOe==LOW);mockMillis+=3001;loop();CHECK(mockOe==HIGH);
 cmd("reset");cmd("commission 0 FREE");CHECK(mockOe==LOW);
 Wire.registers[0]=0x01;mockMillis+=20;loop();CHECK(mockOe==HIGH);CHECK(!motion.active());
 cmd("reset");cmd("commission 0 FREE");CHECK(mockOe==LOW);
 Wire.registers[0xFE]=30;mockMillis+=20;loop();CHECK(mockOe==HIGH);CHECK(!motion.active());
 cmd("reset");Wire.registers[1]=0x00;cmd("commission 0 FREE");CHECK(mockOe==HIGH);CHECK(!motion.active());
 cmd("reset");cmd("commission 0 FREE");CHECK(mockOe==LOW);
 Serial.feed("set 0 1505\n");mockMillis+=10;loop();CHECK(motion.axis[0].target==1505);
 Serial.feed("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx");
 mockMillis+=10;loop();CHECK(mockOe==HIGH);CHECK(!motion.active());
 cmd("reset");cmd("commission 0 FREE");CHECK(mockOe==LOW);
 cmd("set 0 1500junk");CHECK(mockOe==HIGH);CHECK(!motion.active());
 // Demo and status cannot silently renew operator presence.
 mimic::AxisCalibration measured[5];for(auto& c:measured)c={1400,1500,1600,40,80,true};
 cmd("off");motion=mimic::MotionCore(measured,true);cmd("arm PARKED");CHECK(mockOe==LOW);
 cmd("demo");CHECK(demo);uint32_t lease=motion.lastCommand;
 mockMillis+=500;runDemo(mockMillis);CHECK(motion.lastCommand==lease);
 cmd("status");CHECK(motion.lastCommand==lease);
 mockMillis+=2600;loop();CHECK(mockOe==HIGH);CHECK(!demo);
 cmd("reset");CHECK(mockOe==HIGH);Wire.fail=true;cmd("reset");CHECK(!pcaReady);CHECK(mockOe==HIGH);
 printf("{\"suite\":\"sketch_mock\",\"assertions\":%d,\"passed\":true}\n",assertions);
}

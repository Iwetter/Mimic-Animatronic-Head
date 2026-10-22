#include <Arduino.h>
#include <Wire.h>
#include <esp_task_wdt.h>
#include "MotionCore.h"
#include "PinMap.h"
#include <stdlib.h>
#include <string.h>

// Classic ESP32-WROOM-32 only. Audio pins remain reserved; no audio driver is started.
constexpr uint8_t OE_PIN=mimic::kOePin, PCA_ADDRESS=mimic::kPcaAddress;
constexpr uint8_t SDA_PIN=mimic::kSdaPin, SCL_PIN=mimic::kSclPin;
mimic::MotionCore motion;
char line[96]; size_t lineLength=0;
uint32_t lastStep=0, lastPwm=0, demoStart=0;
bool pcaReady=false, demo=false;
int demoPhase=-1;

bool writeRegisters(uint8_t reg, const uint8_t* data, size_t n) {
  Wire.beginTransmission(PCA_ADDRESS); Wire.write(reg); Wire.write(data,n);
  return Wire.endTransmission()==0;
}
bool writeRegister(uint8_t reg,uint8_t value) {return writeRegisters(reg,&value,1);}
bool readRegisters(uint8_t reg,uint8_t* result,size_t n) {
  Wire.beginTransmission(PCA_ADDRESS); Wire.write(reg);
  if(Wire.endTransmission(false)!=0) return false;
  if(Wire.requestFrom(PCA_ADDRESS,(uint8_t)n)!=(int)n) return false;
  for(size_t i=0;i<n;i++) result[i]=Wire.read();
  return true;
}
void disableHardware() {
  digitalWrite(OE_PIN,HIGH); // FIRST: synchronous I2C failure must not delay disabling OE.
  const uint8_t stopped[4]={0,0,0,0x10};
  for(uint8_t c=0;c<16;c++) if(!writeRegisters(6+4*c,stopped,4)) break;
}
void fault(const char* reason) {
  digitalWrite(OE_PIN,HIGH); demo=false; motion.fail(reason); disableHardware();
  Serial.print("FAULT: "); Serial.println(reason);
}
bool initializePca() {
  digitalWrite(OE_PIN,HIGH);
  if(!writeRegister(0,0x10) || !writeRegister(1,0x04) ||
     !writeRegister(0xFE,mimic::kPcaPrescale)) return false;
  const uint8_t stopped[4]={0,0,0,0x10};
  for(uint8_t c=0;c<16;c++) if(!writeRegisters(6+4*c,stopped,4)) return false;
  if(!writeRegister(0,0x20)) return false;
  delay(1);
  if(!writeRegister(0,0xA0)) return false;
  uint8_t p=0,m=0;
  return readRegisters(0xFE,&p,1) && p==mimic::kPcaPrescale &&
         readRegisters(1,&m,1) && m==0x04;
}
bool updatePwm() {
  // Detect an independent PCA reset: pulse register readback alone would miss a
  // changed oscillator divider or disabled auto-increment and could send wrong pulses.
  uint8_t mode1=0,mode2=0,prescale=0;
  if(!readRegisters(0,&mode1,1) || (mode1&0x30)!=0x20 ||
     !readRegisters(1,&mode2,1) || mode2!=0x04 ||
     !readRegisters(0xFE,&prescale,1) || prescale!=mimic::kPcaPrescale) return false;
  for(uint8_t c=0;c<5;c++) {
    uint8_t payload[4]={0,0,0,0x10};
    if(motion.axis[c].enabled) {
      const double tickUs=1000000.0*(mimic::kPcaPrescale+1)/mimic::kPcaOscillatorHz;
      uint16_t count=(uint16_t)lround(motion.axis[c].position/tickUs);
      if(count<1 || count>4095) return false;
      payload[2]=count&255; payload[3]=count>>8;
    }
    if(!writeRegisters(6+4*c,payload,4)) return false;
    uint8_t actual[4];
    if(!readRegisters(6+4*c,actual,4) || memcmp(actual,payload,4)) return false;
  }
  return true;
}
bool parseInt(const char* text,long& value) {
  if(!text || !*text) return false;
  char* end=nullptr; value=strtol(text,&end,10); return *end=='\0';
}
void status() {
  Serial.printf("mode=%d calibration=%s review=%d demo=%d reason=%s\n",(int)motion.mode,
    motion.validCalibration()?"VALID":"LOCKED",mimic::kMechanicalReviewAccepted,demo,motion.reason);
  for(unsigned i=0;i<5;i++) Serial.printf("CH%u current=%.2f target=%.2f active=%d\n",
    i,motion.axis[i].position,motion.axis[i].target,motion.axis[i].enabled);
}
void command(char* text) {
  char* args[5]={}; unsigned n=0;
  char* cursor=nullptr;
  for(char* t=strtok_r(text," \t",&cursor); t && n<5; t=strtok_r(nullptr," \t",&cursor)) args[n++]=t;
  if(!n) return;
  const uint32_t now=millis();
  if(!strcmp(args[0],"off") && n==1) {demo=false;disableHardware();motion.off();Serial.println("OFF");return;}
  if(!strcmp(args[0],"status") && n==1) {status();return;}
  if(!strcmp(args[0],"ping") && n==1) {motion.heartbeat(now);return;}
  if(!strcmp(args[0],"reset") && n==1) {
    if(motion.active()) {fault("reset while active");return;}
    disableHardware();motion.off();pcaReady=initializePca();
    if(!pcaReady) fault("PCA initialization failed");
    return;
  }
  if(!pcaReady || motion.mode==mimic::Mode::Fault) {Serial.println("REJECTED: fault; off/reset required");return;}
  if(!strcmp(args[0],"commission") && n==3 && !strcmp(args[2],"FREE")) {
    long channel;
    if(parseInt(args[1],channel) && channel>=0 && channel<5 && motion.commission(channel,now)) {
      if(!updatePwm()) {fault("PCA write/readback failed");return;}
      digitalWrite(OE_PIN,LOW);Serial.println("COMMISSION: selected detached servo at 1500 us");return;
    }
  } else if(!strcmp(args[0],"arm") && n==2 && !strcmp(args[1],"PARKED") && motion.arm(now)) {
    if(!updatePwm()) {fault("PCA write/readback failed");return;}
    digitalWrite(OE_PIN,LOW);Serial.println("ARMED: measured neutral positions");return;
  } else if(!strcmp(args[0],"set") && n==3) {
    long channel,pulse;
    if(parseInt(args[1],channel) && parseInt(args[2],pulse) && channel>=0 && channel<5 && pulse>=0 && pulse<65536) {
      demo=false;
      if(motion.target(channel,float(pulse),now)) return;
    }
  } else if(!strcmp(args[0],"demo") && n==1 && motion.mode==mimic::Mode::Armed) {
    demo=true;demoStart=now;demoPhase=-1;motion.heartbeat(now);return;
  }
  // Malformed or rejected commands cannot silently continue an active motion.
  if(motion.active() || motion.mode==mimic::Mode::Fault) fault("invalid or unsafe command");
  else Serial.println("REJECTED: check syntax/calibration/state");
}
void runDemo(uint32_t now) {
  if(!demo) return;
  const int phase=(uint32_t(now-demoStart))/4000;
  if(phase>=5) {demo=false;disableHardware();motion.off();Serial.println("DEMO COMPLETE / OFF");return;}
  if(phase==demoPhase) return;
  demoPhase=phase;
  // Slow coordinated pulse-space excursion, at most 15% toward measured endpoints.
  // No angles or eye poses are inferred. Neutral -> low -> neutral -> high -> neutral.
  // Internal demo targets must NOT renew the external command lease.
  uint32_t externalLease=motion.lastCommand;
  for(unsigned i=0;i<5;i++) {
    const auto& c=mimic::kCalibration[i];
    float f=(phase==1?-0.15f:(phase==3?0.15f:0.0f));
    float target=c.neutralUs + (f<0?f*(c.neutralUs-c.minimumUs):f*(c.maximumUs-c.neutralUs));
    if(!motion.target(i,target,now)) {fault("demo target rejected");return;}
  }
  motion.lastCommand=externalLease;
}
void setup() {
  digitalWrite(OE_PIN,HIGH);pinMode(OE_PIN,OUTPUT);
  Serial.begin(115200);
  Wire.begin(SDA_PIN,SCL_PIN,100000);Wire.setTimeOut(25);
  pcaReady=initializePca();
  if(!pcaReady) fault("PCA initialization failed");
  // CPU/task stall protection; reset returns GPIO to external OE pull-up.
  if(esp_task_wdt_init(2,true)!=ESP_OK || esp_task_wdt_add(nullptr)!=ESP_OK) fault("watchdog initialization failed");
  lastStep=millis();lastPwm=lastStep;
  Serial.println("Mimic R5a 1.0.0 -- outputs OFF; use README commissioning procedure");status();
}
void loop() {
  esp_task_wdt_reset();
  const uint32_t now=millis();
  if(!motion.step(now,uint32_t(now-lastStep))) fault(motion.reason);
  lastStep=now;
  // Bounded serial work prevents a noisy port from starving the control loop.
  for(unsigned budget=0;budget<96 && Serial.available();budget++) {
    char c=(char)Serial.read();
    if(c=='\r') continue;
    if(c=='\n') {line[lineLength]='\0';command(line);lineLength=0;}
    else if(lineLength<sizeof(line)-1) line[lineLength++]=c;
    else {lineLength=0;fault("serial line overflow");}
  }
  runDemo(now);
  if(motion.active() && uint32_t(now-lastPwm)>=20) {
    lastPwm=now;
    if(!updatePwm()) fault("PCA write/readback failed");
  }
  delay(1);
}

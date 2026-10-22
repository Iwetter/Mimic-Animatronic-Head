#pragma once
#include <stdint.h>
#include <stddef.h>
#include <vector>
struct MockWire {
 uint8_t registers[256]={};std::vector<uint8_t> tx;
 unsigned ptr=0,remaining=0;bool fail=false,corrupt=false;
 void begin(int,int,int){}void setTimeOut(int){}
 void beginTransmission(uint8_t){tx.clear();}
 size_t write(uint8_t b){tx.push_back(b);return 1;}
 size_t write(const uint8_t* b,size_t n){tx.insert(tx.end(),b,b+n);return n;}
 int endTransmission(bool=true){
   if(fail)return 4;
   if(tx.empty())return 0;
   ptr=tx[0];
   for(size_t i=1;i<tx.size();i++)registers[(ptr+i-1)%256]=tx[i];
   return 0;
 }
 int requestFrom(uint8_t,uint8_t n){remaining=fail?0:n;return remaining;}
 uint8_t read(){if(!remaining)return 0;--remaining;return registers[(ptr++)%256]^(corrupt?1:0);}
};
extern MockWire Wire;

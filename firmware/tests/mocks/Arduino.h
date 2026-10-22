#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string>
#include <deque>
#include <stdio.h>
#include <stdarg.h>
constexpr int HIGH=1,LOW=0,OUTPUT=1;
extern uint32_t mockMillis;
extern int mockOe;
inline uint32_t millis(){return mockMillis;}
inline void delay(unsigned ms){mockMillis+=ms;}
inline void digitalWrite(int pin,int value){if(pin==27)mockOe=value;}
inline void pinMode(int,int){}
struct MockSerial {
 std::deque<char> input;std::string output;
 void begin(int){} int available(){return (int)input.size();}
 char read(){char c=input.front();input.pop_front();return c;}
 void print(const char* s){output+=s;}void println(const char* s){output+=s;output+='\n';}
 void printf(const char* f,...){char b[512];va_list a;va_start(a,f);vsnprintf(b,sizeof(b),f,a);va_end(a);output+=b;}
 void feed(const char* s){for(;*s;s++)input.push_back(*s);}
};
extern MockSerial Serial;

//======================================================================
// LIBRARIES:
//----------------------------------------------------------------------
#include "pwm.h"
//======================================================================
// MACRO DEFINITIONS:
//----------------------------------------------------------------------
#define BAUDRATE 115200
#define POTPIN A0
#define CURPIN A1
#define PULSEPIN 5
#define DIRPIN   4
#define RIGHTLIMITSW 2
#define LEFTLIMITSW 3
#define RIGHT HIGH
#define LEFT LOW
#define MICROSTEP 400.0
#define GEARRATIO 2500.0
#define LEAD 5.0
#define WINDOW_SIZE 10
//======================================================================
// FUNCTION PROTOTYPES:
//----------------------------------------------------------------------
float movingAverage(float, float*, float*);
//======================================================================
// GLOBAL VARIABLES:
//----------------------------------------------------------------------
// Gefran potentiometer calibration and acquisition variable:
const float A = -0.0061926375;
const float B = 100.719884;
float vpos = 0.0;
float hpos = 0.0;
// ACS712 current sensor acquisition variable:
const float adcmax = 16383.0;
const float curmax = 5.0;
float curr = 0.0;
// clock variables for horizontal position measurement:
unsigned long previous_ms, current_ms, t_elapsed;
// initialize stepper control variables:
PwmOut stepperpulse(PULSEPIN);
volatile int direction = LEFT;
float freq = 1000.0f;
bool isStepperRunning = false;
bool isHomedLeft    = false;
bool isHomedRight   = false;
// moving average variables:
float ss1, ss2;
float vals1[WINDOW_SIZE];
float vals2[WINDOW_SIZE];
float vpos_ma, curr_ma;
// serial communication with PC:
char msg;
//======================================================================
// MAIN PROGRAM SETUP:
//----------------------------------------------------------------------
void setup() {
  // initialize serial communication:
  Serial.begin(BAUDRATE);
  // set ADC resolution to 14-bits
  analogReadResolution(14);
  // configure limit switches and interrupts:
  pinMode(RIGHTLIMITSW, INPUT_PULLUP);
  pinMode( LEFTLIMITSW, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(RIGHTLIMITSW), rightlimit_ISR, FALLING);
  attachInterrupt(digitalPinToInterrupt( LEFTLIMITSW),  leftlimit_ISR, FALLING);
  // set stepper motor control pins:
  pinMode(PULSEPIN, OUTPUT);
  pinMode(DIRPIN, OUTPUT);
  digitalWrite(DIRPIN, direction);
  // initialize moving average variables:
  vpos = A*((float)analogRead(POTPIN)) + B;
  curr = (( (float)analogRead(CURPIN))/adcmax*5.0 - 2.5)/0.185;
  for(int i = 0; i<WINDOW_SIZE; i++){
    vals1[i] = vpos;
    vals2[i] = curr;
  }
  ss1 = vpos*(float) WINDOW_SIZE;
  ss2 = curr*(float) WINDOW_SIZE;
  // check limit switches:
  if(digitalRead(RIGHTLIMITSW) == LOW){
    isHomedRight = true;
  }
  if(digitalRead(LEFTLIMITSW) == LOW){
    isHomedLeft = true;
  }

}
//======================================================================
// MAIN PROGRAM LOOP:
//----------------------------------------------------------------------
void loop() {
  // wait for message from PC
  while(!Serial.available());
  msg = Serial.read();
  switch(msg){
    case 'L':     // start moving left
      if(!isHomedLeft){
        direction = LEFT;
        digitalWrite(DIRPIN, direction);
        stepperpulse.begin(freq, 50.0f);
        isStepperRunning = true;
        Serial.println("moving left");
      }
      else if(isStepperRunning & (direction == RIGHT)){
        stepperpulse.end();
        direction = LEFT;
        digitalWrite(DIRPIN, direction);
        stepperpulse.begin(freq, 50.0f);
        Serial.println("moving left");
      }
      else{
        Serial.println("nothing changed: either homed left or already moving");
      }      
      break;
    case 'R':     // start moving right
      if(!isHomedRight){
        direction = RIGHT;
        digitalWrite(DIRPIN, direction);
        stepperpulse.begin(freq, 50.0f);
        isStepperRunning = true;
        Serial.println("moving right");
      }
      else if(isStepperRunning & (direction == LEFT)){
        stepperpulse.end();
        delay()
        direction = RIGHT;
        digitalWrite(DIRPIN, direction);
        stepperpulse.begin(freq, 50.0f);
        Serial.println("moving right");
      }
      else{
        Serial.println("nothing changed: either homed right or already moving");
      }
      break;
    case 'S':     // stop stepper
      if(isStepperRunning){
        stepperpulse.end();
        isStepperRunning = false;
        Serial.println("Stepper stopped");
      }
      break;
    case 'F':     // set frequency
      Serial.println('F');
      while(!Serial.available());
      freq = Serial.parseFloat();
      if(isStepperRunning){
        stepperpulse.end();
        stepperpulse.begin(freq, 50.0f);
      }
      break;
    case 'D':     // read data  
      current_ms = millis();
      t_elapsed = current_ms - previous_ms;
      if(isStepperRunning & (direction == LEFT)){
        hpos += ((float)t_elapsed)/1000.0*freq/MICROSTEP/GEARRATIO*LEAD;
      }
      else if(isStepperRunning & (direction == RIGHT)){
        hpos -= ((float)t_elapsed)/1000.0*freq/MICROSTEP/GEARRATIO*LEAD;
      }
      vpos = A*((float)analogRead(POTPIN)) + B;
      curr = (( (float)analogRead(CURPIN))/adcmax*5.0 - 2.5)/0.185;

      vpos_ma = movingAverage(vpos, vals1, &ss1);
      curr_ma = movingAverage(curr, vals2, &ss2);

      Serial.print(hpos, 4);
      Serial.print(", ");  
      Serial.print(vpos_ma, 4);
      Serial.print(", ");
      Serial.println(curr_ma, 4);
      previous_ms = current_ms;
    //default:
      //break;   
  }
}
//======================================================================
// ISR DEFINITIONS:
//----------------------------------------------------------------------
void rightlimit_ISR(){
  stepperpulse.end();
  isStepperRunning = false;
}
void leftlimit_ISR(){
  stepperpulse.end();
  isStepperRunning = false;
}
//======================================================================
// FUNCTION DEFINITIONS:
//----------------------------------------------------------------------
float movingAverage(float newval, float vals[], float* ssptr){
  *ssptr = *ssptr - vals[0] + newval;
  // update array
  for(int j=0; j<(WINDOW_SIZE-1); j++){
    vals[j] = vals[j+1];          // shift values to the left by one
  }
  vals[WINDOW_SIZE-1] = newval; // add the new value at the end
  return *ssptr / (float) WINDOW_SIZE;
}
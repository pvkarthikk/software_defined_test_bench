/*

* Project: HIL Simulator for Engine ECU
 * Target Hardware: Arduino R4 Minima
 */

const int PIN_IGNITION_OUT = 2;   // DO1: ECU Ignition
const int PIN_RPM_DAC      = A0;  // AO1: ECU RPM (True Analog)
const int PIN_PEDAL_PWM    = 3;   // AO2: ECU Pedal Position
const int PIN_BATT_PWM     = 6;   // AO3: ECU System Voltage
const int PIN_OIL_PWM      = 9;   // AO4: ECU Oil Pressure

const int PIN_CEL_IN       = 7;   // Monitor ECU Check Engine Light
const int PIN_THROTTLE_IN  = 8;   // Monitor ECU Throttle PWM

String inputString = "";         
bool stringComplete = false;  

void setup() {
  Serial.begin(115200);
  inputString.reserve(50);

  analogWriteResolution(12); 
  analogReadResolution(12);  

  pinMode(PIN_IGNITION_OUT, OUTPUT);
  pinMode(PIN_RPM_DAC, OUTPUT);
  pinMode(PIN_PEDAL_PWM, OUTPUT);
  pinMode(PIN_BATT_PWM, OUTPUT);
  pinMode(PIN_OIL_PWM, OUTPUT);

  pinMode(PIN_CEL_IN, INPUT);
  pinMode(PIN_THROTTLE_IN, INPUT);
  
  digitalWrite(PIN_IGNITION_OUT, LOW);
  analogWrite(PIN_RPM_DAC, 0);
}

static uint32_t prev_millis = 0;
void loop() {
  serialEvent();
  uint32_t curr_millis = millis();
  if (stringComplete) {
    parseCommand(inputString);
    inputString = "";
    stringComplete = false;
  }
  if((curr_millis - prev_millis) < 500){
    return;
  }
  prev_millis = millis();

  // DATA:CEL_STATUS,THROTTLE_PWM_US
  Serial.print("DATA:");
  Serial.print(digitalRead(PIN_CEL_IN)); 
  Serial.print(",");
  Serial.println(pulseIn(PIN_THROTTLE_IN, HIGH, 25000));

  delay(10); 
}

void parseCommand(String cmd) {
  int colonIndex = cmd.indexOf(':');
  if (colonIndex == -1) return;
  
  String key = cmd.substring(0, colonIndex);
  int val = cmd.substring(colonIndex + 1).toInt();

  if      (key == "DO1")  digitalWrite(PIN_IGNITION_OUT, val > 0 ? HIGH : LOW);
  else if (key == "AO1")  analogWrite(PIN_RPM_DAC, val);
  else if (key == "AO2")  analogWrite(PIN_PEDAL_PWM, val);
  else if (key == "AO3")  analogWrite(PIN_BATT_PWM, val);
  else if (key == "AO4")  analogWrite(PIN_OIL_PWM, val);
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') stringComplete = true;
    else inputString += inChar;
  }
}
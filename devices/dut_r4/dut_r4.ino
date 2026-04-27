/*
 * Engine ECU Simulator (Demobale DUT) - PWM Input Update
 * Target Hardware: Arduino UNO R4 Minima
 */

#include <Arduino_CAN.h>

// --- Hardware Pin Definitions ---
const int pinIgnition    = 2;  // D2: Ignition Switch (ISR)
const int pinThrottleCMD = 3;  // D3: PWM Output to Throttle
const int pinCheckEngine = 6;  // D6: Fault Indicator
const int pinPedalIn     = A1; // A1: PWM Input (Pedal Position)
const int pinBatteryIn   = A2; // A2: PWM Input (System Voltage)
const int pinRPMIn       = A3; // A3: Analog Input (RPM from Simulator DAC)
const int pinOilPressIn  = A4; // A4: PWM Input (Oil Pressure)

// --- System States ---
enum EngineState { ENGINE_OFF, ENGINE_STARTING, ENGINE_RUNNING, ENGINE_STOPPING };
EngineState currentState = ENGINE_OFF;

// --- Configurable Constants ---
const int IDLE_RPM = 800;
const float MIN_BATT_VOLTAGE = 10.0;
const int PEDAL_MIN = 41;  // ~0.2V
const int PEDAL_MAX = 982; // ~4.8V
const int CMD_IDLE = 25;   // ~10% duty cycle
const int CMD_MAX = 255;   // 100% duty cycle

// --- Global State Variables ---
bool limpMode = false;
bool activeFaults = false;
float batteryVoltage = 0.0;
int pedalRaw = 0;
int actualRPM = 0;
float oilPressureV = 0.0;
int targetThrottleCMD = 0;

unsigned long lastControlTime = 0;
unsigned long lastCANTime = 0;
volatile bool ignitionISRFlag = false;
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY = 200;
bool ignitionToggledFlag = false;

// CAN J1939 EEC1 Parameters
const uint32_t PGN_EEC1 = 0xF004;
const uint32_t CAN_ID_EEC1 = (0x0C << 24) | (PGN_EEC1 << 8) | 0x01;

// ==========================================
// HELPER: READ PWM AS ANALOG (0-1023)
// ==========================================
int readPWMAsAnalog(int pin) {
  unsigned long highTime = pulseIn(pin, HIGH, 3000); 
  unsigned long lowTime  = pulseIn(pin, LOW, 3000);
  unsigned long period = highTime + lowTime;

  if (period == 0) return (digitalRead(pin) == HIGH) ? 1023 : 0;
  return (int)((highTime * 1023) / period);
}

void ignitionISR() {
  ignitionISRFlag = true;
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  pinMode(pinIgnition, INPUT_PULLUP);
  pinMode(pinThrottleCMD, OUTPUT);
  pinMode(pinCheckEngine, OUTPUT);
  
  pinMode(pinPedalIn, INPUT);
  pinMode(pinBatteryIn, INPUT);
  pinMode(pinOilPressIn, INPUT);

  analogWrite(pinThrottleCMD, 0);
  digitalWrite(pinCheckEngine, LOW);

  attachInterrupt(digitalPinToInterrupt(pinIgnition), ignitionISR, FALLING);
  
  if (!CAN.begin(CanBitRate::BR_250k)) {
    digitalWrite(pinCheckEngine, HIGH);
  }
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
  unsigned long currentMillis = millis();
  
  if (currentMillis - lastControlTime >= 10) {
    lastControlTime = currentMillis;
    manageInputs(currentMillis);
    evaluateFaults();
    updateStateMachine();
    updateOutputs();
  }

  if (currentMillis - lastCANTime >= 50) {
    lastCANTime = currentMillis;
    transmitCAN();
  }
}

void manageInputs(unsigned long currentMillis) {
  ignitionToggledFlag = false;
  if (ignitionISRFlag) {
    if ((currentMillis - lastDebounceTime) > DEBOUNCE_DELAY) {
      ignitionToggledFlag = true;
      lastDebounceTime = currentMillis;
    }
    ignitionISRFlag = false;
  }

  // Scale PWM duty cycle to 0-15V for battery
  batteryVoltage = (readPWMAsAnalog(pinBatteryIn) * (5.0 / 1023.0)) * 3.0; 
  
  // Read pedal position from PWM
  pedalRaw = readPWMAsAnalog(pinPedalIn);

  // Read RPM from TRUE ANALOG DAC signal
  actualRPM = map(analogRead(pinRPMIn), 0, 1023, 0, 8000);

  // Read oil pressure from PWM
  oilPressureV = readPWMAsAnalog(pinOilPressIn) * (5.0 / 1023.0);
}

void evaluateFaults() {
  bool batteryFault = (batteryVoltage < MIN_BATT_VOLTAGE);
  bool pedalFault = (pedalRaw < PEDAL_MIN || pedalRaw > PEDAL_MAX);
  bool oilFault = (actualRPM > 2000 && oilPressureV < 1.0);
  
  activeFaults = (batteryFault || pedalFault || oilFault);
  digitalWrite(pinCheckEngine, activeFaults ? HIGH : LOW);

  if (pedalFault || oilFault) limpMode = true;
  if (!activeFaults && currentState == ENGINE_OFF) limpMode = false;
}

void updateStateMachine() {
  switch (currentState) {
    case ENGINE_OFF:
      targetThrottleCMD = 0;
      if (ignitionToggledFlag) currentState = ENGINE_STARTING;
      break;

    case ENGINE_STARTING:
      targetThrottleCMD = CMD_IDLE;
      if (actualRPM >= IDLE_RPM) currentState = ENGINE_RUNNING;
      break;

    case ENGINE_RUNNING:
      if (ignitionToggledFlag) {
        currentState = ENGINE_STOPPING;
        break;
      }
      if (limpMode) {
         targetThrottleCMD = CMD_IDLE;
      } else {
         targetThrottleCMD = map(pedalRaw, PEDAL_MIN, PEDAL_MAX, CMD_IDLE, CMD_MAX);
         targetThrottleCMD = constrain(targetThrottleCMD, CMD_IDLE, CMD_MAX);
      }
      break;
      
    case ENGINE_STOPPING:
      targetThrottleCMD = 0;
      if (actualRPM <= 0) currentState = ENGINE_OFF;
      break;
  }
}

void updateOutputs() {
  analogWrite(pinThrottleCMD, targetThrottleCMD);
}

void transmitCAN() {
  uint16_t canRPM = (uint16_t)(actualRPM / 0.125);
  uint8_t txData[8] = {0xFF, 0xFF, 0xFF, (uint8_t)(canRPM & 0xFF), (uint8_t)((canRPM >> 8) & 0xFF), 0xFF, 0xFF, 0xFF};

  CanMsg msg;
  msg.id = CAN_ID_EEC1;
  msg.data_length = 8;
  msg.is_extended_id = true;
  memcpy(msg.data, txData, 8);

  CAN.write(msg);
}
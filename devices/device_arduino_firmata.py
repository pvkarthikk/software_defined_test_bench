import logging
from typing import List, Any, Dict, Optional
from core.base_device import BaseDevice, SignalDefinition
from pymata4 import pymata4
import time

logger = logging.getLogger(__name__)

class ArduinoFirmataDevice(BaseDevice):
    def __init__(self):
        self._board = None
        self._connected = False
        self._port = None
        self._enabled = True
        self._signals: List[SignalDefinition] = []
        self._signal_map: Dict[str, SignalDefinition] = {}
        self._create_signals()

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def vendor(self) -> str:
        return "Arduino"

    @property
    def model(self) -> str:
        return "Firmata"

    @property
    def firmware_version(self) -> str:
        if self._board:
            # pymata4 stores firmware version in an internal attribute or we can query it
            return str(self._board.get_firmware_version())
        return "Unknown"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def connect(self, connection_params: dict) -> None:
        self._port = connection_params.get("port")
        baud = connection_params.get("baud", 57600)
        arduino_wait = connection_params.get("arduino_wait", 2)

        try:
            logger.info(f"Connecting to Arduino on {self._port}...")
            self._board = pymata4.Pymata4(com_port=self._port, baud_rate=baud, arduino_wait=arduino_wait, shutdown_on_exception=False)
            logging.info(
                f"board capabilities: {self._board.get_capability_report()}"
            )
            self._connected = True
            self._initialize_hardware()
            logger.info("Arduino Firmata connected and hardware initialized.")
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to Arduino: {e}")
            raise

    def _create_signals(self):
        """
        Defines the signals available on a standard Arduino.
        This happens at instantiation, allowing the system to know about signals 
        even before the hardware is connected.
        """
        self._signals = []
        
        # Standard Digital Pins 2-13
        for pin in range(2, 14):
            sig = SignalDefinition(
                signal_id=f"D{pin}",
                name=f"Digital Pin {pin}",
                type="digital",
                direction="bidirectional",
                resolution=1.0,
                unit="bool",
                offset=0.0,
                min=0.0,
                max=1.0,
                value=0.0,
                description=f"GPIO Pin {pin}"
            )
            self._signals.append(sig)
            
        # Standard Analog Pins A0-A5
        for pin in range(6):
            sig = SignalDefinition(
                signal_id=f"A{pin}",
                name=f"Analog Input {pin}",
                type="analog",
                direction="input",
                resolution=1,
                unit="V",
                offset=0.0,
                min=0.0,
                max=5.0,
                value=0.0,
                description=f"ADC Pin {pin}"
            )
            self._signals.append(sig)

        self._signal_map = {s.signal_id: s for s in self._signals}

    def _initialize_hardware(self):
        """
        Configures physical pin modes on the connected Arduino board.
        """
        if not self._board:
            return

        # 1. Initialize Analog Inputs
        for i in range(6):
            try:
                self._board.set_pin_mode_analog_input(i)
                logger.info(f"Hardware initialized: A{i} as Analog Input")
            except Exception as e:
                logger.warning(f"Failed to initialize Analog Input A{i}: {e}")
        
        # 2. Initialize Digital Outputs (Default)
        for pin in range(2, 14):
            try:
                self._board.set_pin_mode_digital_output(pin)
            except Exception as e:
                logger.warning(f"Failed to initialize Digital Pin D{pin}: {e}")

    def disconnect(self) -> None:
        try:
            self._board.shutdown()
        except Exception as e:
            logger.error(f"Failed to disconnect from Arduino: {e}")
        self._connected = False
        logger.info("Arduino Firmata disconnected.")

    def get_signals(self) -> List[SignalDefinition]:
        return self._signals

    def read_signal(self, signal_id: str) -> Any:
        if not self._connected:
            raise RuntimeError("Device not connected")
        
        if signal_id not in self._signal_map:
            raise ValueError(f"Signal {signal_id} not found")
        
        sig = self._signal_map[signal_id]
        if sig.type == "digital" and sig.direction == "input":
             # For digital inputs, we might want to trigger a read if not using callbacks
             # But here we just return the last known value
             pass
        
        return sig.value

    def write_signal(self, signal_id: str, value: Any) -> None:
        if not self._connected:
            raise RuntimeError("Device not connected")

        if signal_id not in self._signal_map:
            raise ValueError(f"Signal {signal_id} not found")

        sig = self._signal_map[signal_id]
        pin = int(signal_id[1:])

        if sig.type == "digital":
            logger.debug(f"Digital write for pin {pin}: {value}")
            self._board.digital_write(pin, 1 if value else 0)
            sig.value = 1 if value else 0
        elif sig.type == "pwm" or (sig.type == "analog" and sig.direction == "output"):
            # pymata4 uses 0-255 for PWM
            pwm_val = int((value / sig.max) * 255)
            logger.debug(f"PWM write for pin {pin}: {pwm_val}") 
            self._board.set_pin_mode_pwm_output(pin)
            self._board.pwm_write(pin, pwm_val)
            sig.value = value

    def update(self) -> None:
        """
        Periodically called by the system.
        Performs manual polling of all input signals.
        """
        if not self._connected or not self._board:
            return
            
        for sig in self._signals:
            try:
                pin = int(sig.signal_id[1:])
                if sig.type == "analog":
                    # analog_read returns (value, timestamp)
                    res = self._board.analog_read(pin)
                    if res:
                        val = res[0]
                        # Convert 10-bit raw (0-1023) to Voltage (0-5V)
                        sig.value = (val / 1023.0) * 5.0
                elif sig.type == "digital" and sig.direction in ["input", "bidirectional"]:
                    res = self._board.digital_read(pin)
                    if res:
                        sig.value = res[0]
            except Exception as e:
                # Silently ignore errors during polling of individual pins
                continue
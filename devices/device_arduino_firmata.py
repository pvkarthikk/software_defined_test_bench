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
        self._signals: List[SignalDefinition] = []
        self._signal_map: Dict[str, SignalDefinition] = {}

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

    def connect(self, connection_params: dict) -> None:
        self._port = connection_params.get("port")
        baud = connection_params.get("baud", 57600)
        arduino_wait = connection_params.get("arduino_wait", 2)

        try:
            logger.info(f"Connecting to Arduino on {self._port}...")
            self._board = pymata4.Pymata4(com_port=self._port, baud_rate=baud, arduino_wait=arduino_wait)
            self._connected = True
            self._initialize_signals()
            logger.info("Arduino Firmata connected and signals initialized.")
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to Arduino: {e}")
            raise

    def _initialize_signals(self):
        """
        Hardcoded signal definitions for a standard Arduino (Uno/Nano).
        In a more advanced implementation, these could be loaded from a config.
        """
        self._signals = []
        
        # Digital Pins 2-13
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
            
        # Analog Pins A0-A5
        for pin in range(6):
            sig = SignalDefinition(
                signal_id=f"A{pin}",
                name=f"Analog Input {pin}",
                type="analog",
                direction="input",
                resolution=0.00488, # 5V / 1024
                unit="V",
                offset=0.0,
                min=0.0,
                max=5.0,
                value=0.0,
                description=f"ADC Pin {pin}"
            )
            self._signals.append(sig)

        self._signal_map = {s.signal_id: s for s in self._signals}
        self._setup_pin_modes()

    def _setup_pin_modes(self):
        # By default, we'll set analog pins to report
        for i in range(6):
            self._board.set_pin_mode_analog_input(i, callback=self._analog_callback)
        
        # Digital pins will be set to output by default for now, 
        # but ideally this should be based on the signal direction in config.
        for pin in range(2, 14):
            self._board.set_pin_mode_digital_output(pin)

    def _analog_callback(self, data):
        # data format: [pin_type, pin_number, pin_value, timestamp]
        pin_number = data[1]
        raw_value = data[2]
        signal_id = f"A{pin_number}"
        logger.debug(f"Analog callback for pin {pin_number}: {raw_value}")
        if signal_id in self._signal_map:
            # Convert 10-bit raw (0-1023) to Voltage (0-5V)
            voltage = (raw_value / 1023.0) * 5.0
            self._signal_map[signal_id].value = voltage

    def disconnect(self) -> None:
        if self._board:
            self._board.shutdown()
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
            self._board.digital_write(pin, 1 if value else 0)
            sig.value = 1 if value else 0
        elif sig.type == "pwm" or (sig.type == "analog" and sig.direction == "output"):
            # pymata4 uses 0-255 for PWM
            pwm_val = int((value / sig.max) * 255)
            self._board.set_pin_mode_pwm_output(pin)
            self._board.pwm_write(pin, pwm_val)
            sig.value = value

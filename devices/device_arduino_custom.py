import serial
import time
from typing import List, Any
from core.base_device import BaseDevice, SignalDefinition, BaseDeviceException


class ArduinoSerialDevice(BaseDevice):
    RX_HEADER = 0xAA
    RX_FOOTER = 0xBB

    TX_HEADER = 0x55
    TX_FOOTER = 0xCC

    def __init__(self):
        self._ser = None
        self._connected = False
        self._signals = self._init_signals()

        # Cached values
        self._digital_in = 0
        self._pwm_in = 0

        # Outputs cache
        self._d2 = 0
        self._d13 = 0
        self._pwm = [0, 0, 0, 0]

    # -------------------------
    # Properties
    # -------------------------
    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def vendor(self) -> str:
        return "Custom Arduino"

    @property
    def model(self) -> str:
        return "Serial PWM Controller"

    @property
    def firmware_version(self) -> str:
        return "1.0"

    # -------------------------
    # Connection
    # -------------------------
    def connect(self, connection_params: dict) -> None:
        try:
            port = connection_params.get("comport")
            baud = connection_params.get("baud", 115200)

            if not port:
                raise BaseDeviceException("Missing 'comport' in connection params")

            self._ser = serial.Serial(port, baud, timeout=0.1)
            time.sleep(2)  # Arduino reset delay

            self._connected = True

        except Exception as e:
            raise BaseDeviceException(f"Connection failed: {e}")

    def disconnect(self) -> None:
        if self._ser:
            self._ser.close()
        self._connected = False

    # -------------------------
    # Signals
    # -------------------------
    def _init_signals(self) -> List[SignalDefinition]:
        return [
            SignalDefinition("d2_out", "Digital Out D2", "digital", "output", 1, "", 0, 0, 1, 0, ""),
            SignalDefinition("d13_out", "LED D13", "digital", "output", 1, "", 0, 0, 1, 0, ""),
            SignalDefinition("pwm1", "PWM Out 1", "pwm", "output", 1, "", 0, 0, 255, 0, ""),
            SignalDefinition("pwm2", "PWM Out 2", "pwm", "output", 1, "", 0, 0, 255, 0, ""),
            SignalDefinition("pwm3", "PWM Out 3", "pwm", "output", 1, "", 0, 0, 255, 0, ""),
            SignalDefinition("pwm4", "PWM Out 4", "pwm", "output", 1, "", 0, 0, 255, 0, ""),
            SignalDefinition("d3_in", "Digital In D3", "digital", "input", 1, "", 0, 0, 1, 0, ""),
            SignalDefinition("pwm_in", "PWM Input", "pwm", "input", 1, "", 0, 0, 255, 0, ""),
        ]

    def get_signals(self) -> List[SignalDefinition]:
        return self._signals

    # -------------------------
    # Core Protocol
    # -------------------------
    def _checksum(self, data):
        cs = 0
        for b in data:
            cs ^= b
        return cs

    def _send_frame(self):
        frame = [
            self.RX_HEADER,
            self._d2,
            self._d13,
            self._pwm[0],
            self._pwm[1],
            self._pwm[2],
            self._pwm[3],
        ]

        cs = self._checksum(frame[1:])
        frame.append(cs)
        frame.append(self.RX_FOOTER)

        self._ser.write(bytes(frame))

    def _read_frame(self):
        if self._ser.in_waiting < 5:
            return

        data = self._ser.read(5)

        if data[0] != self.TX_HEADER or data[4] != self.TX_FOOTER:
            return

        if self._checksum(data[1:3]) != data[3]:
            return

        self._digital_in = data[1]
        self._pwm_in = data[2]

    # -------------------------
    # Read / Write API
    # -------------------------
    def read_signal(self, signal_id: str) -> Any:
        if not self._connected:
            raise BaseDeviceException("Device not connected")

        self._read_frame()

        if signal_id == "d3_in":
            return self._digital_in
        elif signal_id == "pwm_in":
            return self._pwm_in
        else:
            raise BaseDeviceException(f"Unknown signal: {signal_id}")

    def write_signal(self, signal_id: str, value: Any) -> None:
        if not self._connected:
            raise BaseDeviceException("Device not connected")

        if signal_id == "d2_out":
            self._d2 = int(value)
        elif signal_id == "d13_out":
            self._d13 = int(value)
        elif signal_id.startswith("pwm"):
            idx = int(signal_id[-1]) - 1
            self._pwm[idx] = int(value)
        else:
            raise BaseDeviceException(f"Unknown signal: {signal_id}")

        self._send_frame()
import serial
import time
import threading
import logging

logger = logging.getLogger(__name__)

class ArduinoR4Controller:
    def __init__(self, port, baudrate=115200, timeout=1):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(2)  # Wait for Arduino to reset
            logger.info(f"Connected to Arduino on {port}")
        except Exception as e:
            logger.error(f"Error connecting to serial port: {e}")
            self.ser = None

        self.latest_data = [] # List of values from DATA: stream
        self.running = True
        
        # Start background thread to listen for data
        if self.ser:
            self.listener_thread = threading.Thread(target=self._listen, daemon=True)
            self.listener_thread.start()

    def _listen(self):
        """Internal method to continuously parse data from Arduino."""
        while self.running:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line.startswith("DATA:"):
                        # Split string: DATA:v1,v2,v3...
                        raw_values = line.replace("DATA:", "").split(',')
                        self.latest_data = [int(v) for v in raw_values]
                except Exception as e:
                    pass # Ignore partial/corrupt frames

    def _send_command(self, cmd, val):
        """Sends command in format CMD:VAL\n"""
        if self.ser:
            # Basic 12-bit clamping for AO/PWM if requested
            if "AO" in cmd:
                val = max(0, min(4095, int(val)))
            
            message = f"{cmd}:{val}\n"
            self.ser.write(message.encode('utf-8'))
            logger.info(f"Sent command: {message.strip()}")

    # --- GENERIC CONTROL METHODS ---
    def set_digital_out(self, cmd, state):
        """Set Digital Output (e.g., cmd='DO1') to True/False"""
        self._send_command(cmd, 1 if state else 0)

    def set_analog_out(self, cmd, value):
        """Set Analog Output (e.g., cmd='AO1') 0-4095"""
        self._send_command(cmd, value)

    def get_latest_data(self):
        """Returns the latest list of data values from the board"""
        return self.latest_data

    def close(self):
        self.running = False
        if self.ser:
            self.ser.close()

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # Update 'COM3' or '/dev/ttyACM0' to match your board's port
    board = ArduinoR4Controller(port='COM3') 

    try:
        print("Testing Digital Output DO1...")
        board.set_digital_out("DO1", True)
        time.sleep(1)
        
        print("Testing Analog Output AO1 at 50%...")
        board.set_analog_out("AO1", 2048) 
        
        while True:
            data = board.get_latest_data()
            print(f"\rBoard Data -> {data}", end="")
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        board.close()

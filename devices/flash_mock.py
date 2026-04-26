import time
import uuid
import threading
import logging
from typing import Dict, List, Any
from core.base_flash import BaseFlash, BaseFlashException

logger = logging.getLogger(__name__)

class FlashMock(BaseFlash):
    def __init__(self):
        super().__init__()
        self._connected = False
        self._enabled = True
        self._executions: Dict[str, Dict[str, Any]] = {}
        self._logs: Dict[str, List[str]] = {}

    @property
    def vendor(self) -> str:
        return "SDTB"

    @property
    def model(self) -> str:
        return "MockFlasher-v1"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def connect(self, params: Dict[str, Any]):
        logger.info(f"Mock Flash connecting with params: {params}")
        time.sleep(0.5) # Simulate connection delay
        self._connected = True

    def disconnect(self):
        logger.info("Mock Flash disconnected")
        self._connected = False

    def flash(self, data: bytes, params: Dict[str, Any]) -> str:
        if not self._connected:
            raise BaseFlashException("Not connected to target", code=401)

        execution_id = str(uuid.uuid4())
        self._executions[execution_id] = {
            "status": "Starting",
            "progress": 0,
            "start_time": time.time()
        }
        self._logs[execution_id] = [f"Initiating flash for {len(data)} bytes..."]

        # Start background flashing process
        thread = threading.Thread(
            target=self._background_flash, 
            args=(execution_id, len(data)), 
            daemon=True
        )
        thread.start()

        return execution_id

    def get_status(self, execution_id: str) -> Dict[str, Any]:
        if execution_id not in self._executions:
            raise ValueError(f"Execution {execution_id} not found")
        return self._executions[execution_id]

    def get_log(self, execution_id: str) -> List[str]:
        return self._logs.get(execution_id, [])

    def abort(self, execution_id: str):
        if execution_id in self._executions:
            if self._executions[execution_id]["status"] not in ["Success", "Failed", "Aborted"]:
                self._executions[execution_id]["status"] = "Aborted"
                self._logs[execution_id].append("Flash operation ABORTED by user.")

    def _background_flash(self, execution_id: str, total_size: int):
        try:
            steps = [
                ("Erasing Flash Memory...", 0, 20, 2.0),
                ("Programming Blocks...", 20, 80, 5.0),
                ("Verifying Checksum...", 80, 100, 1.5)
            ]

            for step_name, start_p, end_p, duration in steps:
                if self._executions[execution_id]["status"] == "Aborted":
                    return

                self._executions[execution_id]["status"] = step_name
                self._logs[execution_id].append(f"Task: {step_name}")
                
                # Sub-steps for progress
                sub_steps = 10
                for i in range(sub_steps):
                    if self._executions[execution_id]["status"] == "Aborted":
                        return
                    
                    time.sleep(duration / sub_steps)
                    progress = start_p + ((end_p - start_p) * (i + 1) / sub_steps)
                    self._executions[execution_id]["progress"] = int(progress)
                    
                    if step_name == "Programming Blocks...":
                        self._logs[execution_id].append(f"Writing block {i+1}/{sub_steps}...")

            self._executions[execution_id]["status"] = "Success"
            self._executions[execution_id]["progress"] = 100
            self._logs[execution_id].append("Flashing completed successfully!")
            
        except Exception as e:
            self._executions[execution_id]["status"] = "Error"
            self._logs[execution_id].append(f"CRITICAL ERROR: {str(e)}")

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseFlashException(Exception):
    """Custom exception for flashing protocol errors."""
    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.code = code
        self.message = message

class BaseFlash(ABC):
    """
    Base class for all flashing protocol plugins.
    Each implementation should be in a file named flash_*.py.
    """
    
    @property
    @abstractmethod
    def vendor(self) -> str:
        """Returns the protocol/tool vendor name."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Returns the specific protocol or tool model."""
        pass

    @abstractmethod
    def connect(self, connection_params: dict) -> None:
        """Establishes connection with the flashing target."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Safely disconnects from the flashing target."""
        pass

    @abstractmethod
    def flash(self, data: bytes, params: dict) -> str:
        """
        Initiates the flash process and returns a unique execution_id.
        Should be non-blocking or start a thread/task.
        """
        pass

    @abstractmethod
    def get_status(self, execution_id: str) -> dict:
        """
        Returns the current status of the flashing operation.
        Expected keys: status (str), progress (float 0-100), message (str).
        """
        pass

    @abstractmethod
    def get_log(self, execution_id: str) -> List[str]:
        """Returns the detailed log messages for a specific execution."""
        pass

    @abstractmethod
    def abort(self, execution_id: str) -> None:
        """Aborts an ongoing flash operation."""
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Getter for the enabled state."""
        pass

    @enabled.setter
    @abstractmethod
    def enabled(self, value: bool):
        """Setter for the enabled state."""
        pass

"""
Signal Type Registry
====================
Loads `config/signal_types.json` once and exposes validation helpers.

Usage
-----
    from core.signal_registry import SignalRegistry

    registry = SignalRegistry()
    sig_type = registry.get("engine_speed")   # SignalTypeDefinition
    warnings = registry.validate_signal(my_signal_def)
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic model — mirrors one entry in signal_types.json
# ---------------------------------------------------------------------------

class SignalTypeDefinition(BaseModel):
    """Typed definition for a single AUTOSAR signal category."""
    display_name: str
    category_ids: List[int]
    hardware_type: str          # "analog", "digital", "pwm"
    impl_type: str              # "uint8", "uint16", "sint16", "float32", "boolean"
    bit_width: int
    signed: bool
    unit: str
    resolution_options: List[float]
    default_resolution: float
    min_physical: float
    max_physical: float
    offset: float
    description: str

    @field_validator("hardware_type")
    @classmethod
    def validate_hardware_type(cls, v: str) -> str:
        allowed = {"analog", "digital", "pwm"}
        if v not in allowed:
            raise ValueError(f"hardware_type must be one of {allowed}, got '{v}'")
        return v

    @field_validator("impl_type")
    @classmethod
    def validate_impl_type(cls, v: str) -> str:
        allowed = {"uint8", "uint16", "sint16", "sint32", "float32", "boolean"}
        if v not in allowed:
            raise ValueError(f"impl_type must be one of {allowed}, got '{v}'")
        return v


# ---------------------------------------------------------------------------
# Singleton registry
# ---------------------------------------------------------------------------

_REGISTRY_PATH = Path(__file__).parent.parent / "config" / "signal_types.json"


class SignalRegistry:
    """
    Singleton that loads the signal type registry from ``config/signal_types.json``
    on first access and provides lookup and validation helpers.

    Parameters
    ----------
    registry_path : Path, optional
        Override the path to ``signal_types.json`` (useful for testing).
    """

    _instance: Optional["SignalRegistry"] = None
    _types: Dict[str, SignalTypeDefinition] = {}
    _loaded: bool = False

    def __new__(cls, registry_path: Optional[Path] = None) -> "SignalRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        if self._loaded:
            return
        path = registry_path or _REGISTRY_PATH
        self._load(path)

    def _load(self, path: Path) -> None:
        """Parse and validate ``signal_types.json``."""
        try:
            raw: dict = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.error(f"Signal type registry not found at '{path}'. No signal types loaded.")
            SignalRegistry._loaded = True
            return
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse signal type registry: {exc}")
            SignalRegistry._loaded = True
            return

        loaded: Dict[str, SignalTypeDefinition] = {}
        for key, data in raw.items():
            try:
                loaded[key] = SignalTypeDefinition(**data)
            except Exception as exc:
                logger.warning(f"Skipping malformed signal type '{key}': {exc}")

        SignalRegistry._types = loaded
        SignalRegistry._loaded = True
        logger.info(f"SignalRegistry: loaded {len(loaded)} signal type(s) from '{path}'.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, signal_type_key: str) -> Optional[SignalTypeDefinition]:
        """Return the ``SignalTypeDefinition`` for *signal_type_key*, or ``None``."""
        return self._types.get(signal_type_key)

    def list_types(self) -> List[str]:
        """Return all registered signal type keys."""
        return list(self._types.keys())

    def validate_signal(self, signal) -> List[str]:
        """
        Validate a ``SignalDefinition`` against the registry entry for its
        declared ``signal_type``.

        Parameters
        ----------
        signal : SignalDefinition
            A device signal definition (from ``core.base_device``).

        Returns
        -------
        List[str]
            A list of human-readable warning strings. Empty list means no issues.
        """
        warnings: List[str] = []

        signal_type_key: str = getattr(signal, "signal_type", None)
        if not signal_type_key:
            warnings.append(
                f"Signal '{signal.signal_id}' has no 'signal_type' declared — "
                "cannot validate against registry."
            )
            return warnings

        typedef = self.get(signal_type_key)
        if typedef is None:
            warnings.append(
                f"Signal '{signal.signal_id}' references unknown signal_type "
                f"'{signal_type_key}'. Valid types: {self.list_types()}"
            )
            return warnings

        # --- impl_type consistency ---
        sig_impl = getattr(signal, "impl_type", None)
        if sig_impl and sig_impl != typedef.impl_type:
            warnings.append(
                f"Signal '{signal.signal_id}': impl_type '{sig_impl}' does not match "
                f"registry default '{typedef.impl_type}' for type '{signal_type_key}'."
            )

        # --- bit_width consistency ---
        sig_bits = getattr(signal, "bit_width", None)
        if sig_bits and sig_bits > typedef.bit_width:
            warnings.append(
                f"Signal '{signal.signal_id}': bit_width {sig_bits} exceeds registry "
                f"maximum {typedef.bit_width} for type '{signal_type_key}'."
            )

        # --- unit consistency ---
        if typedef.unit and signal.unit and signal.unit != typedef.unit:
            warnings.append(
                f"Signal '{signal.signal_id}': unit '{signal.unit}' does not match "
                f"registry unit '{typedef.unit}' for type '{signal_type_key}'."
            )

        # --- resolution plausibility ---
        if signal.resolution not in typedef.resolution_options:
            # Soft warning only — custom resolutions are acceptable
            logger.debug(
                f"Signal '{signal.signal_id}': resolution {signal.resolution} is not a "
                f"standard option for '{signal_type_key}' ({typedef.resolution_options}). "
                "This is allowed but may indicate misconfiguration."
            )

        # --- physical range check ---
        if signal.min < typedef.min_physical:
            warnings.append(
                f"Signal '{signal.signal_id}': min {signal.min} is below registry "
                f"min_physical {typedef.min_physical} for type '{signal_type_key}'."
            )
        if signal.max > typedef.max_physical:
            warnings.append(
                f"Signal '{signal.signal_id}': max {signal.max} exceeds registry "
                f"max_physical {typedef.max_physical} for type '{signal_type_key}'."
            )

        return warnings

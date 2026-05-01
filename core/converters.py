from abc import ABC, abstractmethod
from typing import List
import logging

logger = logging.getLogger(__name__)

class Converter(ABC):
    """Abstract base class for channel conversion strategies."""
    
    @abstractmethod
    def to_physical(self, raw_value: float) -> float:
        """Converts a raw hardware value to a physical unit."""
        pass

    @abstractmethod
    def to_raw(self, physical_value: float) -> float:
        """Converts a physical unit value to a raw hardware value."""
        pass

class LinearConverter(Converter):
    """Standard affine scaling: physical = (raw * resolution) + offset"""
    
    def __init__(self, resolution: float, offset: float):
        self.resolution = resolution
        self.offset = offset

    def to_physical(self, raw_value: float) -> float:
        return (raw_value * self.resolution) + self.offset

    def to_raw(self, physical_value: float) -> float:
        if self.resolution == 0:
            return physical_value - self.offset
        return (physical_value - self.offset) / self.resolution

class PolynomialConverter(Converter):
    """
    Polynomial scaling: physical = c0 + c1*raw + c2*raw^2 + ...
    Inversion uses a bounded binary search, assuming monotonicity.
    """
    
    def __init__(self, coefficients: List[float], min_raw: float, max_raw: float):
        self.coefficients = coefficients
        self.min_raw = min_raw
        self.max_raw = max_raw

    def to_physical(self, raw_value: float) -> float:
        result = 0.0
        for i, c in enumerate(self.coefficients):
            result += c * (raw_value ** i)
        return result

    def to_raw(self, physical_value: float) -> float:
        # Binary search for the root
        low = self.min_raw
        high = self.max_raw
        
        val_low = self.to_physical(low)
        val_high = self.to_physical(high)
        
        increasing = val_high > val_low
        
        epsilon = 1e-6
        for _ in range(100):
            mid = (low + high) / 2.0
            val_mid = self.to_physical(mid)
            
            if abs(val_mid - physical_value) < epsilon:
                return mid
                
            if increasing:
                if val_mid < physical_value:
                    low = mid
                else:
                    high = mid
            else:
                if val_mid < physical_value:
                    high = mid
                else:
                    low = mid
                    
        return (low + high) / 2.0

class LutConverter(Converter):
    """
    Lookup Table scaling with linear interpolation.
    Out-of-bounds values are clamped to the nearest table endpoint.
    """
    
    def __init__(self, table: List[List[float]]):
        # Sort table by raw value (column 0)
        self.table = sorted(table, key=lambda x: x[0])
        
        # Check monotonicity of physical values for invertibility
        phys_values = [p[1] for p in self.table]
        is_increasing = all(x <= y for x, y in zip(phys_values, phys_values[1:]))
        is_decreasing = all(x >= y for x, y in zip(phys_values, phys_values[1:]))
        
        if not (is_increasing or is_decreasing):
            logger.warning("LUT is not monotonic. `to_raw` (write) may produce ambiguous results.")

    def _interpolate(self, x: float, x_col: int, y_col: int) -> float:
        if not self.table:
            return 0.0

        # Create sorted tuples based on the search column to ensure proper clamping
        sorted_by_x = sorted(self.table, key=lambda row: row[x_col])

        # Clamp to bounds
        if x <= sorted_by_x[0][x_col]:
            return sorted_by_x[0][y_col]
        if x >= sorted_by_x[-1][x_col]:
            return sorted_by_x[-1][y_col]
            
        # Linear interpolation
        for i in range(len(sorted_by_x) - 1):
            x0 = sorted_by_x[i][x_col]
            x1 = sorted_by_x[i+1][x_col]
            
            if min(x0, x1) <= x <= max(x0, x1):
                y0 = sorted_by_x[i][y_col]
                y1 = sorted_by_x[i+1][y_col]
                
                if x0 == x1:
                    return y0
                    
                fraction = (x - x0) / (x1 - x0)
                return y0 + fraction * (y1 - y0)
                
        return sorted_by_x[-1][y_col]

    def to_physical(self, raw_value: float) -> float:
        return self._interpolate(raw_value, x_col=0, y_col=1)

    def to_raw(self, physical_value: float) -> float:
        return self._interpolate(physical_value, x_col=1, y_col=0)

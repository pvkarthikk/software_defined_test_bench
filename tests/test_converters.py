import pytest
from core.converters import LinearConverter, PolynomialConverter, LutConverter

def test_linear_converter():
    conv = LinearConverter(resolution=0.1, offset=-40.0)
    
    # Raw to Physical
    assert conv.to_physical(0.0) == -40.0
    assert conv.to_physical(100.0) == -30.0
    
    # Physical to Raw
    assert conv.to_raw(-40.0) == 0.0
    assert conv.to_raw(-30.0) == 100.0

def test_polynomial_converter():
    # y = 1.0 + 2.0*x + 0.5*x^2
    conv = PolynomialConverter(coefficients=[1.0, 2.0, 0.5], min_raw=-100, max_raw=100)
    
    # to_physical
    assert conv.to_physical(0.0) == 1.0
    assert conv.to_physical(2.0) == 1.0 + 4.0 + 2.0  # 7.0
    
    # to_raw (binary search)
    raw = conv.to_raw(7.0)
    assert abs(raw - 2.0) < 1e-4

def test_lut_converter():
    table = [
        [0.0, 10.0],
        [100.0, 50.0],
        [200.0, 20.0]  # Non-monotonic
    ]
    conv = LutConverter(table=table)
    
    # to_physical
    assert conv.to_physical(-10.0) == 10.0  # clamp low
    assert conv.to_physical(0.0) == 10.0
    assert conv.to_physical(50.0) == 30.0   # interp
    assert conv.to_physical(100.0) == 50.0
    assert conv.to_physical(150.0) == 35.0  # interp down
    assert conv.to_physical(200.0) == 20.0
    assert conv.to_physical(300.0) == 20.0  # clamp high

    # Let's test a monotonic one for invertibility
    table_mono = [
        [0.0, -40.0],
        [100.0, 0.0],
        [200.0, 100.0]
    ]
    conv_mono = LutConverter(table=table_mono)
    assert conv_mono.to_raw(-40.0) == 0.0
    assert conv_mono.to_raw(-20.0) == 50.0
    assert conv_mono.to_raw(0.0) == 100.0
    assert conv_mono.to_raw(50.0) == 150.0
    assert conv_mono.to_raw(100.0) == 200.0

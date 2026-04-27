import pytest
from core.test_engine import TestEngine
from unittest.mock import MagicMock

def test_evaluate_assertion_tolerance():
    engine = TestEngine(MagicMock())
    
    # Direct equality (should work)
    assert engine._evaluate_assertion(2.5, "==", 2.5)
    
    # Precision mismatch (should work with tolerance)
    assert engine._evaluate_assertion(2.5000001, "==", 2.5)
    assert engine._evaluate_assertion(2.4999999, "==", 2.5)
    
    # Significant difference (should fail)
    assert not engine._evaluate_assertion(2.51, "==", 2.5)
    
    # Inequality with tolerance
    assert not engine._evaluate_assertion(2.5000001, "!=", 2.5)
    assert engine._evaluate_assertion(2.51, "!=", 2.5)

    # Greater than (tolerance doesn't apply to > or < usually, or does it? 
    # Usually it's strictly >. Let's check.)
    assert engine._evaluate_assertion(2.5000001, ">", 2.5)
    assert not engine._evaluate_assertion(2.5, ">", 2.5)

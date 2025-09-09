"""Helper utilities for testing with Decimal values."""

from decimal import Decimal
from typing import Any, Union


def decimal_equal(actual: Any, expected: Union[float, int, str, Decimal]) -> bool:
    """
    Compare a Decimal value with expected numeric value, handling precision differences.
    
    Args:
        actual: The actual value (should be Decimal)
        expected: The expected value (can be float, int, str, or Decimal)
        
    Returns:
        bool: True if values are equal within expected precision
    """
    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        return False
        
    # Convert expected to Decimal for comparison
    if isinstance(expected, (float, int, str)):
        expected_decimal = Decimal(str(expected))
    elif isinstance(expected, Decimal):
        expected_decimal = expected
    else:
        return False
        
    # Compare as Decimal values
    return isinstance(actual, Decimal) and actual == expected_decimal


def assert_decimal_equal(actual: Any, expected: Union[float, int, str, Decimal], message: str = None):
    """
    Assert that a Decimal value equals the expected value.
    
    Args:
        actual: The actual value (should be Decimal) 
        expected: The expected value (can be float, int, str, or Decimal)
        message: Optional custom error message
    """
    if not decimal_equal(actual, expected):
        default_message = f"Expected {actual} (type: {type(actual)}) to equal {expected} (type: {type(expected)})"
        raise AssertionError(message or default_message)
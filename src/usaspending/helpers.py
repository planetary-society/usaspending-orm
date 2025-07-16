"""Helper functions for USASpending API models."""

from __future__ import annotations
from typing import Any, Optional


def smart_sentence_case(text: str) -> str:
    """Convert text to smart sentence case.
    
    Args:
        text: Input text to convert
        
    Returns:
        Text in sentence case
    """
    if not text:
        return ""
    
    # Basic sentence case conversion
    return text.strip().capitalize()


def to_float(value: Any) -> Optional[float]:
    """Convert value to float, returning None if not possible.
    
    Args:
        value: Value to convert
        
    Returns:
        Float value or None if conversion fails
    """
    if value is None:
        return None
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
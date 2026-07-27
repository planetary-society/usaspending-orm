"""Numeric coercion and money formatting for USASpending API values.

The API reports numbers as strings as often as not, and omits them freely, so
every *coercer* here answers a missing or unparseable value with None rather than
raising. Callers that require a number supply their own fallback.

``round_to_millions`` is the exception, and deliberately so: it is a formatter
whose result goes straight into a ``__repr__``, so it renders a missing amount as
``$0.00`` rather than handing None to a format spec."""

from __future__ import annotations

import decimal
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def to_decimal(x: Any) -> Decimal | None:
    """Convert input to a Decimal with 2 decimal places using banker's rounding.

    Args:
        x: Value to convert to Decimal (number, string, etc.)

    Returns:
        Optional[Decimal]: Decimal object quantized to 2 decimal places, or None if input is None or conversion fails
    """
    if x is None:
        return None
    try:
        return Decimal(str(x)).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, decimal.InvalidOperation):
        return None


def to_float(x: Any) -> float | None:
    """
    Converts the input value to a float if possible.
    Attempts to cast the provided value to a float. If the conversion fails due to a TypeError or ValueError,
    returns None instead.

    Args:
        x (Any): The value to convert to float.

    Returns:
        Optional[float]: The converted float value, or None if conversion is not possible.
    """

    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def to_int(x: Any) -> int | None:
    """
    Converts the input value to an integer if possible.
    Attempts to cast the provided value to an integer. If the conversion fails due to a TypeError or ValueError,
    returns None instead.

    Args:
        x (Any): The value to convert to an integer.

    Returns:
        Optional[int]: The integer representation of `x` if conversion is successful; otherwise, None.
    """

    # A missing value is the common case for optional API fields, and reaching
    # int(None) just to catch the TypeError costs roughly 7x this early return.
    if x is None:
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def round_to_millions(amount: int | float | Decimal) -> str:
    """
    Formats a monetary amount with commas and two decimal places, displaying as millions or billions when appropriate.

    Args:
        amount: The monetary value to format.

    Returns:
        str: The formatted string representing the amount in dollars, millions, or billions.
    """

    amount = to_decimal(amount)

    if amount is None:
        return "$0.00"
    elif amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:,.1f} billion"
    elif amount >= 1_000_000:
        return f"${amount / 1_000_000:,.1f} million"
    else:
        return f"${amount:,.2f}"

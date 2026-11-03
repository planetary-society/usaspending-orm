"""State, district, and territory reference data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class State:
    """One U.S. state, district, or territory in USAspending's reference data.

    Attributes:
        fips: The FIPS code as a string, preserving leading zeros.
        code: The two-letter state, district, or territory code.
        name: The name as reported by the API.
    """

    fips: str
    code: str
    name: str

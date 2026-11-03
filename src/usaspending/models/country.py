"""Country reference data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Country:
    """One country or special location in USAspending's reference data.

    Attributes:
        code: The API's country code, including special codes such as AX2.
        name: The country or location name as reported by the API.
    """

    code: str
    name: str

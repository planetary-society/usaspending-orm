from __future__ import annotations
from typing import Dict, Any, Optional, TYPE_CHECKING
from titlecase import titlecase
from ..utils.formatter import contracts_titlecase
from .base_model import BaseModel

if TYPE_CHECKING:
    from ..client import USASpendingClient


class Location(BaseModel):
    """Location model for USASpending data."""

    def __init__(
        self, data: Dict[str, Any], client: Optional[USASpendingClient] = None
    ):
        """Initialize Location.

        Args:
            data: Dictionary containing location data.
            client: USASpendingClient instance (ignored, kept for compatibility).
        """
        super().__init__(data)

    # simple direct fields --------------------------------------------------
    @property
    def address_line1(self) -> Optional[str]:
        """First line of the address.

        Returns:
            Optional[str]: Address line 1 in title case, or None.
        """
        return self._format_location_string_property(self.get_value(["address_line1"]))

    @property
    def address_line2(self) -> Optional[str]:
        """Second line of the address.

        Returns:
            Optional[str]: Address line 2 in title case, or None.
        """
        return self._format_location_string_property(self.get_value(["address_line2"]))

    @property
    def address_line3(self) -> Optional[str]:
        """Third line of the address.

        Returns:
            Optional[str]: Address line 3 in title case, or None.
        """
        return self._format_location_string_property(self.get_value(["address_line3"]))

    @property
    def city_name(self) -> Optional[str]:
        """Name of the city.

        Returns:
            Optional[str]: City name in title case, or None.
        """
        city_name = self.get_value(["city_name", "city"])
        if not isinstance(city_name, str):
            return None
        return titlecase(city_name)

    @property
    def city(self) -> Optional[str]:
        """Alias for city_name.

        Returns:
            Optional[str]: City name in title case, or None.
        """
        return self.city_name

    @property
    def state_name(self) -> Optional[str]:
        """Full name of the state.

        Returns:
            Optional[str]: State name in title case, or None.
        """
        state_name = titlecase(self.get_value(["state_name", "state"]))
        if not isinstance(state_name, str):
            return None
        return titlecase(state_name)

    @property
    def country_name(self) -> Optional[str]:
        """Name of the country.

        Returns:
            Optional[str]: Country name (USA is normalized to 'USA'), or None.
        """
        country = self._format_location_string_property(
            self.get_value(["country_name"])
        )
        if country and country.lower() == "usa":
            country = "USA"
        return country

    @property
    def zip4(self) -> Optional[str]:
        """ZIP+4 postal code.

        Returns:
            Optional[str]: The ZIP+4 code, or None.
        """
        return self.get_value(["zip4"])

    @property
    def county_name(self) -> Optional[str]:
        """Name of the county.

        Returns:
            Optional[str]: County name in title case, or None.
        """
        county_name = titlecase(self.get_value(["county_name", "county"]))
        if not isinstance(county_name, str):
            return None
        return county_name

    @property
    def county_code(self) -> Optional[str]:
        """County code.

        Returns:
            Optional[str]: The county code, or None.
        """
        return self.get_value(["county_code"])

    @property
    def congressional_code(self) -> Optional[str]:
        """Congressional district code.

        Returns:
            Optional[str]: The congressional district code, or None.
        """
        return self.get_value(["congressional_code", "district"])

    @property
    def foreign_province(self) -> Optional[str]:
        """Province name for foreign locations.

        Returns:
            Optional[str]: The foreign province name, or None.
        """
        return self.get_value(["foreign_province"])

    @property
    def foreign_postal_code(self) -> Optional[str]:
        """Postal code for foreign locations.

        Returns:
            Optional[str]: The foreign postal code, or None.
        """
        return self.get_value(["foreign_postal_code"])

    # dual-source fields ----------------------------------------------------
    @property
    def state_code(self) -> Optional[str]:
        """Two-letter state abbreviation.

        Returns:
            Optional[str]: The state code (e.g., 'CA', 'NY'), or None.
        """
        return self.get_value(["state_code", "Place of Performance State Code"])

    @property
    def country_code(self) -> Optional[str]:
        """Country code.

        Returns:
            Optional[str]: The country code (e.g., 'USA', 'GBR'), or None.
        """
        return self.get_value(
            ["location_country_code", "Place of Performance Country Code"]
        )

    @property
    def zip5(self) -> Optional[str]:
        """5-digit ZIP code.

        Returns:
            Optional[str]: The 5-digit ZIP code, or empty string.
        """
        val = self.get_value(["zip5", "Place of Performance Zip5"])
        return str(val) if val is not None else ""

    # convenience -----------------------------------------------------------
    @property
    def district(self) -> Optional[str]:
        """Formatted district string (State-District).

        Returns:
            Optional[str]: String formatted as 'State-District' (e.g., 'CA-12'), or empty string.
        """
        pieces = [p for p in (self.state_code, self.congressional_code) if p]
        return "-".join(pieces) or ""

    @property
    def formatted_address(self) -> Optional[str]:
        """Full address formatted as a multi-line string.

        Returns:
            Optional[str]: Formatted address string, or None if no address components exist.
        """
        lines: list[str] = [
            line
            for line in (self.address_line1, self.address_line2, self.address_line3)
            if line
        ]
        trailing = [p for p in (self.city, self.state_code, self.zip5) if p]
        if trailing:
            lines.append(", ".join(trailing))
        if self.country_name:
            lines.append(self.country_name)
        return "\n".join(lines) or None

    def _format_location_string_property(self, text: str) -> Optional[str]:
        """Format a location string with string check.

        Args:
            text: Input text to format.

        Returns:
            Optional[str]: Title-cased string or None if input is not a string.
        """
        if not isinstance(text, str):
            return None
        return contracts_titlecase(text.strip())

    def __repr__(self) -> str:
        """String representation of Location.

        Returns:
            str: String containing city, state code, and country code.
        """
        return f"<Location {self.city or '?'} {self.state_code or ''} {self.country_code or ''}>"

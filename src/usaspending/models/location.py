from __future__ import annotations
from typing import Dict, Any, Optional

from .base_model import BaseModel

class Location(BaseModel):
    """Location model for USASpending data."""
    
    def __init__(self, data: Dict[str, Any], client=None):
        """Initialize Location. Client parameter is ignored for compatibility."""
        super().__init__(data)

    # simple direct fields --------------------------------------------------
    @property
    def address_line1(self) -> Optional[str]:          return self.get_value(["address_line1"])
    @property
    def address_line2(self) -> Optional[str]:          return self.get_value(["address_line2"])
    @property
    def address_line3(self) -> Optional[str]:          return self.get_value(["address_line3"])
    @property
    def city_name(self) -> Optional[str]:
        return self.get_value(["city_name"])
    
    @property  
    def city(self) -> Optional[str]:
        return self.city_name
    
    @property
    def state_name(self)  -> Optional[str]:            return self.get_value(["state_name"])
    @property
    def country_name(self)-> Optional[str]:            return self.get_value(["country_name"])
    @property
    def zip4(self)        -> Optional[str]:            return self.get_value(["zip4"])
    @property
    def county_name(self) -> Optional[str]:            return self.get_value(["county_name"])
    @property
    def county_code(self) -> Optional[str]:            return self.get_value(["county_code"])
    @property
    def congressional_code(self) -> Optional[str]:     return self.get_value(["congressional_code"])
    @property
    def foreign_province(self) -> Optional[str]:       return self.get_value(["foreign_province"])
    @property
    def foreign_postal_code(self) -> Optional[str]:    return self.get_value(["foreign_postal_code"])

    # dual-source fields ----------------------------------------------------
    @property
    def state_code(self) -> Optional[str]:
        return self.get_value(["state_code", "Place of Performance State Code"])

    @property
    def country_code(self) -> Optional[str]:
        return self.get_value(["location_country_code", "Place of Performance Country Code"])

    @property
    def zip5(self) -> Optional[str]:
        val = self.get_value(["zip5", "Place of Performance Zip5"])
        return str(val) if val is not None else ""

    # convenience -----------------------------------------------------------
    @property
    def district(self) -> Optional[str]:
        pieces = [p for p in (self.state_code, self.congressional_code) if p]
        return "-".join(pieces) or ""

    @property
    def formatted_address(self) -> Optional[str]:
        lines: list[str] = [l for l in (self.address_line1,
                                        self.address_line2,
                                        self.address_line3) if l]
        trailing = [p for p in (self.city, self.state_code, self.zip5) if p]
        if trailing:
            lines.append(", ".join(trailing))
        if self.country_name:
            lines.append(self.country_name)
        return "\n".join(lines) or None

    # misc ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<Location {self.city or '?'} {self.state_code or ''} {self.country_code or ''}>"
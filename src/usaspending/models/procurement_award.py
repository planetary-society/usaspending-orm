"""Shared behavior for procurement awards: contracts and IDVs."""

from __future__ import annotations

from decimal import Decimal
from functools import cached_property
from typing import Any

from ..utils.formatter import to_decimal
from .award import Award


# Maintainer note, deliberately not in the docstring below, which ships to users
# via help(): the four unshared classification accessors look like accidental
# drift rather than design. Contract reaches into naics_hierarchy and
# latest_transaction_contract_data where IDV stops at the flat dict, even though
# IDV populates those same hierarchies; and contract_award_type diverges
# entirely, Contract delegating to type_description while IDV reads its own key
# first. Unifying them would change which values the library reports, so they are
# preserved as-is. Deciding what each field *should* consult is tracked
# separately. base_exercised_options and base_and_all_options also appear on
# Grant with identical bodies, so they arguably belong on Award; that is a public
# surface change and likewise tracked separately.
class ProcurementAward(Award):
    """An award made through procurement, as opposed to financial assistance.

    Contracts and Indefinite Delivery Vehicles are both procurement instruments,
    so they share a PIID, the NAICS and PSC classification hierarchies, option
    values, and the latest contract transaction.

    Note:
        Contract resolves ``naics_code``, ``naics_description`` and
        ``psc_description`` from more sources than IDV does, and the two define
        ``contract_award_type`` differently, so those four stay on each subclass.
        See :class:`Contract` and :class:`IDV` for what each consults.
    """

    @property
    def piid(self) -> str | None:
        """Procurement Instrument Identifier (PIID).

        A unique identifier assigned to a federal contract, purchase order, basic
        ordering agreement, basic agreement, and blanket purchase agreement. It is
        used to track the contract, and any modifications or transactions related
        to it. After October 2017, it is between 13 and 17 digits, both letters
        and numbers.

        Returns:
            Optional[str]: The PIID, or None.
        """
        return self._lazy_get("piid")

    @property
    def base_exercised_options(self) -> Decimal | None:
        """Value of the base contract and any exercised options.

        Summed from the award's associated transactions.

        Returns:
            Optional[Decimal]: The total base exercised options amount, or None.
        """
        return to_decimal(self._lazy_get("base_exercised_options", default=None))

    @property
    def base_and_all_options(self) -> Decimal | None:
        """Total value including options.

        For a contract, the mutually agreed upon total contract value including
        all options. For an IDV, this also includes the estimated value of all
        potential orders. For modifications, it reflects the change, positive or
        negative, of these values.

        Returns:
            Optional[Decimal]: The total base and all options amount, or None.
        """
        return to_decimal(self._lazy_get("base_and_all_options", default=None))

    @property
    def psc_code(self) -> str | None:
        """Product/Service Code (PSC).

        Returns:
            Optional[str]: The PSC code, or None.
        """
        psc_data = self._lazy_get("psc", "PSC")
        if isinstance(psc_data, dict):
            return psc_data.get("code")
        if self.psc_hierarchy and isinstance(self.psc_hierarchy.get("base_code"), dict):
            return self.psc_hierarchy["base_code"].get("code")
        return None

    @cached_property
    def psc_hierarchy(self) -> dict[str, Any] | None:
        """Product/Service Code (PSC) hierarchy information.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing PSC hierarchy data, or None.
        """
        return self._lazy_get("psc_hierarchy")

    @cached_property
    def naics_hierarchy(self) -> dict[str, Any] | None:
        """North American Industry Classification System (NAICS) hierarchy.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing NAICS hierarchy data, or None.
        """
        return self._lazy_get("naics_hierarchy")

    @cached_property
    def latest_transaction_contract_data(self) -> dict[str, Any] | None:
        """Latest contract transaction data with procurement-specific details.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing latest transaction data, or None.
        """
        return self._lazy_get("latest_transaction_contract_data")

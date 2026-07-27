"""FederalAccount model for TAS hierarchy data."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar

from .base_model import ClientAwareModel

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..queries.tas_codes_query import TASCodesQuery
    from .treasury_account_symbol import TreasuryAccountSymbol


class FederalAccount(ClientAwareModel):
    """Federal account node in the TAS hierarchy.

    Represents a federal account (budget account) which contains one or more
    Treasury Account Symbols (TAS). Federal accounts are the intermediate
    level between agencies and individual TAS codes.

    Federal Account ID Format: AID-MAIN
    Example: 080-0120 (NASA Science account)

    Attributes:
        id: The federal account code (e.g., "080-0120")
        description: Human-readable account title
        ancestors: List containing parent toptier_code
        count: Number of TAS codes under this account
    """

    _REATTACH_INVALIDATES: ClassVar[tuple[str, ...]] = ("_tas_codes_level",)

    def __init__(
        self,
        data: dict[str, Any],
        client: USASpendingClient,
        toptier_code: str | None = None,
    ):
        """Initialize FederalAccount.

        Args:
            data: Raw API response data for this federal account.
            client: USASpendingClient instance.
            toptier_code: Parent agency toptier code for navigation.
        """
        raw = self.validate_init_data(data, "FederalAccount", allow_string_id=False)
        super().__init__(raw, client)
        self._toptier_code = toptier_code or (self.ancestors[0] if self.ancestors else None)

    @property
    def id(self) -> str | None:
        """The federal account code (e.g., '080-0120')."""
        return self.get_value("id")

    @property
    def code(self) -> str | None:
        """Alias for id property."""
        return self.id

    @property
    def federal_account_code(self) -> str | None:
        """Alias for id property."""
        return self.id

    @property
    def description(self) -> str | None:
        """Human-readable account title/description."""
        return self.get_value("description")

    @property
    def name(self) -> str | None:
        """Alias for description property."""
        return self.description

    @property
    def title(self) -> str | None:
        """Alias for description property."""
        return self.description

    @property
    def count(self) -> int:
        """Number of TAS codes under this federal account.

        Counting the TAS codes costs an API request, so it is only used when the
        filter tree omits the key. No cache is needed here: :attr:`tas_codes`
        fetches its level once per account, so a repeated fallback is free.
        """
        count = self.get_value("count")
        return self.tas_codes.count() if count is None else count

    @property
    def ancestors(self) -> list[str]:
        """List of ancestor node IDs (contains toptier_code)."""
        ancestors = self.get_value("ancestors", default=[])
        return ancestors if isinstance(ancestors, list) else []

    @property
    def toptier_code(self) -> str | None:
        """Parent agency toptier code."""
        return self._toptier_code

    @property
    def tas_codes(self) -> TASCodesQuery:
        """Get TAS codes under this federal account.

        Returns a query-like object that supports iteration, filtering,
        ordering, and .count().

        The level is fetched once per FederalAccount, so the reads below cost one
        request between them rather than one each. The corollary is that a
        long-lived account keeps reporting the codes it first saw; construct a
        fresh one to pick up changes.

        Returns:
            TASCodesQuery: Lazy query for TAS codes.

        Example:
            >>> account = agency.federal_accounts[0]
            >>> for tas in account.tas_codes:
            ...     print(tas.id, tas.bpoa, tas.epoa)
            >>>
            >>> # Get count
            >>> print(len(account.tas_codes))
            >>> print(account.tas_codes.count())
            >>>
            >>> # Filter by availability or fiscal year
            >>> no_year = account.tas_codes.availability_type_code("X").all()
            >>> fy2024 = account.tas_codes.fiscal_year(2024).all()
        """
        return self._new_tas_codes_query()._seed(lambda: self._tas_codes_level)

    def _new_tas_codes_query(self) -> TASCodesQuery:
        """Build an unfetched query for this account's TAS codes.

        An account that does not know its own codes yields an unscoped query,
        which the base answers with an empty result set and no request.
        """
        from ..queries.tas_codes_query import TASCodesQuery

        return TASCodesQuery(
            self._client,
            self._toptier_code or "",
            self.federal_account_code or "",
        )

    @cached_property
    def _tas_codes_level(self) -> list[TreasuryAccountSymbol]:
        """Fetch this account's TAS codes once, as models rather than as a query.

        See "Who caches what" in :mod:`usaspending.queries.filter_tree_query` for
        why a model caches the models where a resource may cache the query.
        """
        return self._new_tas_codes_query().all()

    def __repr__(self) -> str:
        """String representation of FederalAccount."""
        code = self.federal_account_code or "?"
        title = self.title or "?"
        # Truncate long titles
        if len(title) > 50:
            title = title[:47] + "..."
        return f"<FederalAccount {code}: {title}>"

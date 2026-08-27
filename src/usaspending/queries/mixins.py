"""Reusable slices of query-builder behavior shared by several builders.

Each mixin owns one cohesive concern and nothing else: it declares its own
state, carries that state across clones, and exposes the method that sets it.
Mixins here never read state owned by another mixin, so they can be combined in
any order without the combination itself needing to be understood.

Compose them ahead of the builder base, so their ``_clone`` joins the
cooperative chain rather than being shadowed by it::

    class FundingSearch(AwardScopedQuery, SortableQuery, QueryBuilder["Funding"]): ...

Two invariants matter when using these. Compose ahead of the base, as above; and
any ``_clone`` override must call ``super()._clone()``, because that is what
propagates state and skipping it fails silently rather than loudly.
"""

from __future__ import annotations

from typing import ClassVar, Generic, TypeVar

from ..exceptions import ValidationError
from ..utils.validations import validate_non_empty_string, validate_sort_direction

# Self types, so a chained call keeps the concrete builder's type rather than
# widening to the mixin (or to Any) partway through the chain.
ASQ = TypeVar("ASQ", bound="AwardScopedQuery")
SQ = TypeVar("SQ", bound="SortableQuery")

# Item type for MaterializedIndexingQuery, so indexing keeps the concrete
# builder's item type.
MI = TypeVar("MI")


class MaterializedIndexingQuery(Generic[MI]):
    """List-like indexing for queries that answer from one materialized result.

    For builders whose full result comes from a single request or an in-memory
    collection, an index or slice addresses the materialized list directly;
    translating indices into page arithmetic would invent pages the source
    does not have.
    """

    def __getitem__(self, key: int | slice) -> MI | list[MI]:
        """Support list-like indexing and slicing.

        Args:
            key (Union[int, slice]): Integer index or slice object.

        Returns:
            Union[MI, list[MI]]: Single item for integer index, list for slice.

        Raises:
            IndexError: If index is out of bounds.
            TypeError: If key is not int or slice.
        """
        if not isinstance(key, (int, slice)):
            raise TypeError(f"indices must be integers or slices, not {type(key).__name__}")
        return self.all()[key]


class AwardScopedQuery:
    """Scopes a query to exactly one award, which the endpoint requires.

    For the builders whose endpoint is meaningless without an award: the ID is
    mandatory, and requesting without it is a usage error rather than an empty
    result. Builders where an award is one optional filter among many, such as
    ``SubAwardsSearch``, deliberately do not use this.
    """

    # Class-level default rather than an __init__ assignment. A cooperative
    # __init__ here would replace the concrete builder's constructor signature
    # with (*args, **kwargs) in help() and editor hovers, and these defaults are
    # immutable, so a class attribute is safe and invisible.
    _award_id: str | None = None

    def _clone(self: ASQ) -> ASQ:
        """Carry the award scope onto a clone."""
        clone = super()._clone()
        clone._award_id = self._award_id
        return clone

    def _require_award_id(self) -> str:
        """Return the award ID, or explain that it is missing.

        Returns:
            str: The award identifier this query is scoped to.

        Raises:
            ValidationError: If no award ID has been set.
        """
        if not self._award_id:
            raise ValidationError("An award_id is required. Use the .award_id() method.")
        return self._award_id

    def award_id(self: ASQ, award_id: str) -> ASQ:
        """Scope the query to a single award.

        Args:
            award_id: The unique generated award identifier.

        Returns:
            A new instance scoped to that award.
        """
        validated_id = validate_non_empty_string(award_id, "award_id")

        clone = self._clone()
        clone._award_id = validated_id
        return clone


class SortableQuery:
    """Sorting for endpoints that accept ``sort`` and ``order`` parameters.

    Subclasses declare :attr:`SORT_FIELD_MAP`, mapping the friendly names
    callers use to the field names the API expects. The set of valid fields is
    derived from that mapping rather than listed separately, which is what kept
    drifting when each builder maintained its own copy.
    """

    #: Friendly sort name to API field name.
    SORT_FIELD_MAP: ClassVar[dict[str, str]] = {}

    # The current selection, defaulted at class level. Subclasses override
    # _sort_field with the field their endpoint sorts by by default; order_by()
    # then shadows it per instance. Declaring these as class attributes rather
    # than assigning them in a cooperative __init__ keeps the concrete builder's
    # constructor signature intact for help() and editor hovers.
    _sort_field: str = ""
    _sort_order: str = "desc"

    def _clone(self: SQ) -> SQ:
        """Carry the sort selection onto a clone."""
        clone = super()._clone()
        clone._sort_field = self._sort_field
        clone._sort_order = self._sort_order
        return clone

    def _sort_payload(self) -> dict[str, str]:
        """Return the sort parameters for a request payload.

        Returns:
            dict[str, str]: The ``sort`` and ``order`` parameters.

        Raises:
            ValidationError: If the class declared no default sort field, which
                would otherwise send an empty sort to the API silently.
        """
        if not self._sort_field:
            raise ValidationError(
                f"{type(self).__name__} sets no default _sort_field, so there is nothing "
                "to sort by. Declare one on the class, or call order_by() first."
            )
        return {"sort": self._sort_field, "order": self._sort_order}

    def order_by(self: SQ, field: str, direction: str = "desc") -> SQ:
        """Set the sort field and direction.

        Args:
            field: A friendly name from :attr:`SORT_FIELD_MAP`, or an API field
                name directly.
            direction: ``"asc"`` or ``"desc"``.

        Returns:
            A new instance with the sort applied.

        Raises:
            ValidationError: If the direction or field is not supported.
        """
        validate_sort_direction(direction)

        api_field = self.SORT_FIELD_MAP.get(field.lower(), field)

        # Not `validate_sort_field`: tested against the API names, but the
        # caller is shown the friendly ones.
        if api_field not in self.SORT_FIELD_MAP.values():
            raise ValidationError(
                f"Invalid sort field '{field}'. "
                f"Valid fields are: {', '.join(sorted(self.SORT_FIELD_MAP))}"
            )

        clone = self._clone()
        clone._sort_field = api_field
        clone._sort_order = direction
        return clone

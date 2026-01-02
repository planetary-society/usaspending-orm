"""Client-side query builder for in-memory collections."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import (
    Any,
    Callable,
    TypeVar,
    cast,
)

from .base_query import BaseQuery
from .filters import BaseFilter, KeywordsFilter, SimpleListFilter, SimpleStringFilter

T = TypeVar("T")
Q = TypeVar("Q", bound="ClientSideQueryBuilder[T]")


def _identity(value: T) -> T:
    """Return the input value unchanged.

    Args:
        value (T): Value to return.

    Returns:
        T: The same value.
    """
    return value


class FilterAdapter:
    """Adapter that converts API filters into client-side predicates."""

    def __init__(
        self,
        resolve_field: Callable[[Any, str], Any],
        keyword_fields: Sequence[str] | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            resolve_field (Callable[[Any, str], Any]): Field resolver for items.
            keyword_fields (Optional[Sequence[str]]): Fields to search for
                KeywordsFilter matches.
        """
        self._resolve_field = resolve_field
        self._keyword_fields = list(keyword_fields or [])

    def to_predicate(self, filter_obj: BaseFilter) -> Callable[[Any], bool]:
        """Convert a filter object into a predicate function.

        Args:
            filter_obj (BaseFilter): Filter definition to adapt.

        Returns:
            Callable[[Any], bool]: Predicate that returns True for matches.

        Raises:
            NotImplementedError: If the filter is not supported.
        """
        if isinstance(filter_obj, SimpleStringFilter):
            return self._string_equals(filter_obj)
        if isinstance(filter_obj, SimpleListFilter):
            return self._list_contains(filter_obj)
        if isinstance(filter_obj, KeywordsFilter):
            return self._keywords_match(filter_obj)
        raise NotImplementedError(
            f"Client-side evaluation not implemented for {type(filter_obj).__name__}"
        )

    def _string_equals(self, filter_obj: SimpleStringFilter) -> Callable[[Any], bool]:
        """Build a predicate for a SimpleStringFilter."""
        field = filter_obj.key
        expected = filter_obj.value

        def predicate(item: Any) -> bool:
            return self._resolve_field(item, field) == expected

        return predicate

    def _list_contains(self, filter_obj: SimpleListFilter) -> Callable[[Any], bool]:
        """Build a predicate for a SimpleListFilter."""
        field = filter_obj.key
        if not filter_obj.values:
            return lambda item: True
        values = set(filter_obj.values)

        def predicate(item: Any) -> bool:
            value = self._resolve_field(item, field)
            if isinstance(value, (list, set, tuple)):
                return any(entry in values for entry in value)
            return value in values

        return predicate

    def _keywords_match(self, filter_obj: KeywordsFilter) -> Callable[[Any], bool]:
        """Build a predicate for a KeywordsFilter."""
        keywords = [word.lower() for word in filter_obj.values if word]
        if not keywords:
            return lambda item: True
        if not self._keyword_fields:
            raise NotImplementedError(
                "KeywordsFilter requires keyword_fields for client-side evaluation"
            )

        def predicate(item: Any) -> bool:
            for field in self._keyword_fields:
                value = self._resolve_field(item, field)
                if value is None:
                    continue
                haystack = str(value).lower()
                if any(keyword in haystack for keyword in keywords):
                    return True
            return False

        return predicate


class ClientSideQueryBuilder(BaseQuery[T]):
    """Query builder that filters and sorts data in memory.

    This class provides a consistent interface for one-to-many relationships
    where the API does not offer search, filtering, or ordering support.
    Subclasses should expose explicit filter methods that call _add_filter,
    _add_filter_object, or _where to mirror the QueryBuilder interface style.
    """

    def __init__(
        self,
        items: Iterable[Any],
        transform: Callable[[Any], T] | None = None,
        keyword_fields: Sequence[str] | None = None,
    ) -> None:
        """Initialize the client-side query builder.

        Args:
            items (Iterable[Any]): Source items to query.
            transform (Optional[Callable[[Any], T]]): Optional transformer that
                converts raw items into model instances.
            keyword_fields (Optional[Sequence[str]]): Fields used for keyword
                searches with KeywordsFilter.
        """
        super().__init__()
        self._items: list[Any] = list(items)
        if transform is None:
            self._transform = cast(Callable[[Any], T], _identity)
        else:
            self._transform = transform
        self._keyword_fields = list(keyword_fields or [])
        self._filter_adapter = FilterAdapter(
            self._resolve_field, keyword_fields=self._keyword_fields
        )
        self._filter_objects: list[BaseFilter] = []
        self._predicate_filters: list[Callable[[T], bool]] = []

    def _add_filter(self: Q, predicate: Callable[[T], bool]) -> Q:
        """Add a predicate filter for subclasses.

        Args:
            predicate (Callable[[T], bool]): Function that returns True for
                matching items.

        Returns:
            ClientSideQueryBuilder: A new query with the predicate applied.
        """
        clone = self._clone()
        clone._predicate_filters.append(predicate)
        return clone

    def _add_filter_object(self: Q, filter_obj: BaseFilter) -> Q:
        """Add a filter object for subclasses.

        Args:
            filter_obj (BaseFilter): Filter definition to apply.

        Returns:
            ClientSideQueryBuilder: A new query with the filter applied.
        """
        clone = self._clone()
        clone._filter_objects.append(filter_obj)
        return clone

    def _where(self: Q, **conditions: Any) -> Q:
        """Filter results by equality on fields for subclasses.

        Args:
            **conditions (Any): Field equality checks. Use double underscores to
                represent nested fields (for example, recipient__name).

        Returns:
            ClientSideQueryBuilder: A new query with the conditions applied.
        """
        normalized = {
            key.replace("__", "."): value for key, value in conditions.items()
        }
        clone = self._clone()

        for field, expected in normalized.items():
            if isinstance(expected, str):
                clone._filter_objects.append(
                    SimpleStringFilter(key=field, value=expected)
                )
                continue

            if isinstance(expected, (list, set, tuple)) and all(
                isinstance(entry, str) for entry in expected
            ):
                clone._filter_objects.append(
                    SimpleListFilter(key=field, values=list(expected))
                )
                continue

            def predicate(item: T, field=field, expected=expected) -> bool:
                return clone._resolve_field(item, field) == expected

            clone._predicate_filters.append(predicate)

        return clone

    def __iter__(self) -> Iterator[T]:
        """Iterate over results after applying filters and ordering."""
        items = self._materialize()
        items = self._apply_filters(items)
        items = self._apply_ordering(items)
        items = self._apply_limits(items)
        yield from items

    def __getitem__(self, key: int | slice) -> T | list[T]:
        """Support list-like indexing and slicing.

        Args:
            key (Union[int, slice]): Integer index or slice object.

        Returns:
            Union[T, list[T]]: Single item for integer index, list for slice.

        Raises:
            IndexError: If index is out of bounds.
            TypeError: If key is not int or slice.
        """
        items = self._apply_ordering(self._apply_filters(self._materialize()))

        if isinstance(key, int):
            return items[key]
        if isinstance(key, slice):
            return items[key]
        raise TypeError(
            f"indices must be integers or slices, not {type(key).__name__}"
        )

    def count(self) -> int:
        """Return the total number of matching results."""
        return len(self._apply_filters(self._materialize()))

    def _clone(self: Q) -> Q:
        """Return a copy for method chaining."""
        clone = self.__class__(
            self._items,
            transform=self._transform,
            keyword_fields=self._keyword_fields,
        )
        clone._filter_objects = self._filter_objects.copy()
        clone._predicate_filters = self._predicate_filters.copy()
        clone._page_size = self._page_size
        clone._total_limit = self._total_limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
        return clone

    def _materialize(self) -> list[T]:
        """Convert raw items into model instances."""
        return [self._transform(item) for item in self._items]

    def _apply_filters(self, items: list[T]) -> list[T]:
        """Apply all predicate filters to the item list."""
        predicates = [
            self._filter_adapter.to_predicate(filter_obj)
            for filter_obj in self._filter_objects
        ]
        predicates.extend(self._predicate_filters)

        filtered = items
        for predicate in predicates:
            filtered = [item for item in filtered if predicate(item)]
        return filtered

    def _apply_ordering(self, items: list[T]) -> list[T]:
        """Apply ordering if configured."""
        if not self._order_by:
            return items
        reverse = str(self._order_direction).lower() == "desc"
        return sorted(items, key=self._sort_key, reverse=reverse)

    def _apply_limits(self, items: list[T]) -> list[T]:
        """Apply limit and max_pages constraints to the item list."""
        max_items = len(items)

        if self._max_pages is not None:
            max_items = min(max_items, self._max_pages * self._page_size)

        if self._total_limit is not None:
            max_items = min(max_items, self._total_limit)

        return items[:max_items]

    def _sort_key(self, item: T) -> tuple[bool, Any]:
        """Build a stable sort key for the configured order field."""
        value = self._resolve_field(item, self._order_by or "")
        return (value is None, value)

    def _resolve_field(self, item: Any, field: str) -> Any:
        """Resolve a field on a dict or object instance."""
        value = item
        for part in field.split("."):
            value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)
        return value

"""Shared query interfaces for API and client-side query builders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, Iterator, Optional, TypeVar

from ..exceptions import ValidationError

T = TypeVar("T")
Q = TypeVar("Q", bound="BaseQuery[T]")


class BaseQuery(ABC, Generic[T]):
    """Base query interface for chainable query builders."""

    def __init__(self) -> None:
        """Initialize base query state."""
        self._page_size = 100
        self._total_limit: Optional[int] = None
        self._max_pages: Optional[int] = None
        self._order_by: Optional[str] = None
        self._order_direction = "desc"

    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        """Return an iterator over results."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of matching results."""

    @abstractmethod
    def _clone(self: Q) -> Q:
        """Return an immutable clone of the query."""

    def limit(self: Q, num: int) -> Q:
        """Set the total number of items to return across all pages.

        Args:
            num (int): Maximum number of results to return.

        Returns:
            BaseQuery: A new query instance with the limit applied.

        Raises:
            ValidationError: If num is negative.
        """
        if num < 0:
            raise ValidationError("limit must be non-negative")
        clone = self._clone()
        clone._total_limit = num
        return clone

    def page_size(self: Q, num: int) -> Q:
        """Set page size for fetching results.

        Args:
            num (int): Number of items per page.

        Returns:
            BaseQuery: A new query instance with the page size applied.

        Raises:
            ValidationError: If num is not positive.
        """
        if num <= 0:
            raise ValidationError("page_size must be a positive integer")
        clone = self._clone()
        clone._page_size = min(num, 100)
        return clone

    def max_pages(self: Q, num: int) -> Q:
        """Limit total number of pages fetched.

        Args:
            num (int): Maximum number of pages to fetch.

        Returns:
            BaseQuery: A new query instance with the max pages applied.

        Raises:
            ValidationError: If num is negative.
        """
        if num < 0:
            raise ValidationError("max_pages must be non-negative")
        clone = self._clone()
        clone._max_pages = num
        return clone

    def order_by(self: Q, field: str, direction: str = "desc") -> Q:
        """Set sort order for results.

        Args:
            field (str): Field name to sort by.
            direction (str): Sort direction (asc or desc).

        Returns:
            BaseQuery: A new query instance with ordering applied.
        """
        clone = self._clone()
        clone._order_by = field
        clone._order_direction = direction
        return clone

    def first(self) -> Optional[T]:
        """Return the first result, or None if no results are available."""
        for result in self.limit(1):
            return result
        return None

    def all(self) -> list[T]:
        """Return all results as a list."""
        return list(self)

    def __len__(self) -> int:
        """Return the total number of items."""
        return self.count()

    def _get_effective_page_size(self) -> int:
        """Return the effective page size based on limit and page size."""
        if self._total_limit is not None:
            return min(self._page_size, self._total_limit)
        return self._page_size

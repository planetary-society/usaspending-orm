"""Shared query interfaces for API and client-side query builders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Generic, TypeVar

from ..exceptions import ValidationError

T = TypeVar("T")
Q = TypeVar("Q", bound="BaseQuery[T]")


class BaseQuery(ABC, Generic[T]):
    """Base query interface for chainable query builders."""

    _MAX_PAGE_SIZE: int = 100

    def __init__(self) -> None:
        """Initialize base query state."""
        self._page_size = 100
        self._total_limit: int | None = None
        self._max_pages: int | None = None
        self._order_by: str | None = None
        self._order_direction = "desc"

    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        """Return an iterator over results."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of matching results."""

    def _new_instance(self: Q) -> Q:
        """Construct a fresh instance of this class, carrying no query state.

        This is the seam for subclasses whose ``__init__`` takes more than the
        defaults: override this rather than reimplementing :meth:`_clone`, so
        base-class state is still copied by one shared implementation.

        Returns:
            BaseQuery: A new, empty instance of the same class.
        """
        raise NotImplementedError

    def _clone(self: Q) -> Q:
        """Return an immutable clone of the query.

        Subclasses that add state override this, call ``super()._clone()``, and
        copy their own fields onto the result. Subclasses whose ``__init__``
        needs arguments override :meth:`_new_instance` instead.

        Returns:
            BaseQuery: A copy carrying the same query state.
        """
        clone = self._new_instance()
        clone._page_size = self._page_size
        clone._total_limit = self._total_limit
        clone._max_pages = self._max_pages
        clone._order_by = self._order_by
        clone._order_direction = self._order_direction
        return clone

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
        clone._page_size = min(num, self._MAX_PAGE_SIZE)
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

    def first(self) -> T | None:
        """Return the first result, or None if no results are available."""
        for result in self.limit(1):
            return result
        return None

    def all(self) -> list[T]:
        """Return all results as a list.

                Iterates rather than passing ``self`` to ``list()``, which asks for a
                length hint and so calls :meth:`__len__`. For a paginated query that means
                a request to the count endpoint whose answer is then discarded, making
                every ``all()`` cost one request more than iterating the same query.
        ``__length_hint__`` is not a way out:
                CPython consults ``__len__`` first and only falls back to it when that
                raises, so a query cannot decline the hint while ``len()`` still means
                something.

                Everything that asks for the hint still pays it: ``list(query)``,
                ``tuple(query)``, ``sorted(query)``, ``[*query]`` and ``f(*query)``, and
                also ``bool(query)``, since ``__len__`` with no ``__bool__`` makes
                truthiness a count. ``set()``, ``dict.fromkeys()``, ``sum()``, ``in`` and
                comprehensions do not. So this method, or a plain loop, is the cheap way to
                read a query.
        """
        return list(iter(self))

    def __len__(self) -> int:
        """Return the effective number of items respecting limit/max_pages."""
        return self._effective_count()

    def _get_effective_page_size(self) -> int:
        """Return the effective page size based on limit and page size."""
        if self._total_limit is not None:
            return min(self._page_size, self._total_limit)
        return self._page_size

    def _effective_count(self) -> int:
        """Return count capped by limit() and max_pages() constraints.

        Returns:
            The smaller of the raw API count and any user-set constraints.
        """
        raw = self.count()
        caps = [raw]
        if self._total_limit is not None:
            caps.append(self._total_limit)
        if self._max_pages is not None:
            caps.append(self._max_pages * self._page_size)
        return min(caps)

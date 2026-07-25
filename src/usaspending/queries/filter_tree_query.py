"""Shared base for queries over the API's filter-tree endpoints.

The ``/references/filter_tree/`` endpoints return a whole level of a hierarchy
in one unpaginated response, so the useful shape is: fetch once, cache, then
filter and sort in memory. ``FederalAccountsQuery`` and ``TASCodesQuery`` are
both that shape and were ~90% identical, down to their cache handling, their
code/description filters and their clone semantics.

A subclass supplies three things: the endpoint it reads, how to turn a response
row into a model, and any filters specific to its level of the tree.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from ..logging_config import USASpendingLogger
from ..utils.validations import validate_non_empty_string
from .client_side_query_builder import ClientSideQueryBuilder
from .filters import KeywordsFilter, SimpleListFilter, SimpleStringFilter

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)

T = TypeVar("T")
FTQ = TypeVar("FTQ", bound="FilterTreeQuery[Any]")


class FilterTreeQuery(ClientSideQueryBuilder[T], ABC):
    """A filter-tree level, fetched once and then queried in memory."""

    #: Endpoint template, formatted with :meth:`_scope`. Deliberately has no
    #: default: a subclass that forgets it should fail, not GET the API root.
    ENDPOINT: ClassVar[str]

    #: Fields a keyword filter searches. A level with more overrides this. Note
    #: that :meth:`description` searches all of them, which is what makes an
    #: alias like ``account_name`` honest rather than merely a synonym.
    KEYWORD_FIELDS: ClassVar[tuple[str, ...]] = ("description", "name")

    #: Response key holding the code that :meth:`code` and :meth:`codes` match.
    #: Filter-tree rows key their identifier under ``id`` at every level, even
    #: where the resulting model exposes it under another name.
    CODE_KEY: ClassVar[str] = "id"

    def __init__(self, client: USASpendingClient) -> None:
        """Initialize the query.

        Args:
            client: USASpendingClient instance.
        """
        self._client = client
        self._results: list[T] | None = None
        super().__init__(items=[], keyword_fields=self.KEYWORD_FIELDS)

    # ==========================================================================
    # Subclass responsibilities
    # ==========================================================================

    @abstractmethod
    def _scope(self) -> dict[str, str]:
        """Return the hierarchy path this query is scoped to.

        One value with three consumers: it formats :attr:`ENDPOINT`, it decides
        whether the query is answerable at all, and it names the scope in
        ``repr``.

        Returning any empty value means this query has no scope yet, which is a
        legitimate state rather than an error, so the result set is empty and no
        request is made. A model that does not know its own agency code
        constructs exactly this.
        """

    @abstractmethod
    def _build_model(self, data: dict[str, Any]) -> T:
        """Turn one response row into a model instance.

        A method rather than a class attribute, because the model import has to
        be deferred to break the models-to-queries import cycle.
        """

    @abstractmethod
    def _new_instance(self: FTQ) -> FTQ:
        """Reconstruct an empty instance, passing this query's scope through.

        Declared abstract because the scope arrives via ``__init__``: a subclass
        that omits this inherits a constructor call that does not match its own
        signature, and the resulting failure surfaces far from the cause.
        """

    # ==========================================================================
    # Fetching
    # ==========================================================================

    @property
    def _endpoint(self) -> str:
        """The endpoint this query reads, matching the rest of the package."""
        return self.ENDPOINT.format(**self._scope())

    def _fetch(self) -> list[T]:
        """Fetch this level of the tree, once per instance.

        Returns:
            list[T]: The fetched models, cached for subsequent calls.
        """
        if self._results is not None:
            return self._results

        if not all(self._scope().values()):
            self._results = []
            return self._results

        endpoint = self._endpoint
        logger.debug("Fetching %s from %s", type(self).__name__, endpoint)

        response = self._client._make_request("GET", endpoint)
        self._results = [
            self._build_model(data)
            for data in response.get("results", [])
            if isinstance(data, dict)
        ]

        logger.debug("Fetched %d results", len(self._results))

        return self._results

    def _materialize(self) -> list[T]:
        """Return the fetched models for client-side filtering."""
        return list(self._fetch())

    def _clone(self: FTQ) -> FTQ:
        """Copy the query, sharing anything already fetched.

        The fetched rows are shared rather than re-requested, since filtering is
        what varies between clones, not the underlying data.
        """
        clone = super()._clone()
        clone._results = self._results
        return clone

    # ==========================================================================
    # Filters common to every level
    # ==========================================================================

    def code(self: FTQ, code: str) -> FTQ:
        """Filter to one code.

        Args:
            code: The code to match exactly.

        Returns:
            A new query with the filter applied.
        """
        validated = validate_non_empty_string(code, "code")
        return self._add_filter_object(SimpleStringFilter(key=self.CODE_KEY, value=validated))

    def codes(self: FTQ, *codes: str) -> FTQ:
        """Filter to any of several codes.

        Args:
            *codes: One or more codes to match.

        Returns:
            A new query with the filter applied.
        """
        return self._add_filter_object(SimpleListFilter(key=self.CODE_KEY, values=list(codes)))

    def description(self: FTQ, text: str) -> FTQ:
        """Filter by description text, case-insensitive substring.

        Args:
            text: Text to search for.

        Returns:
            A new query with the filter applied.
        """
        validated = validate_non_empty_string(text, "description")
        return self._add_filter_object(KeywordsFilter(values=[validated]))

    def __repr__(self) -> str:
        """String representation, showing whether the level has been fetched.

        Coerces each scope value, because ``_fetch`` tolerates any falsy scope
        and a repr that raises is worse than useless in a log line or debugger.
        """
        scope = "/".join(str(value) for value in self._scope().values())
        state = f"{len(self._results)} results" if self._results is not None else "not fetched"
        return f"<{type(self).__name__} {scope} [{state}]>"

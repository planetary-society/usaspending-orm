"""count() honors limit() and max_pages(), whichever way a builder counts.

There are four ways a query answers "how many", and they used to disagree under
a bound. The two that ask the API for a figure -- a dedicated count endpoint and
the first page's metadata -- reported the server's total whatever the caller had
asked for, so ``q.limit(3).count()`` said 510 while ``len(q)`` and ``len(q.all())``
said 3. The two that produce their own figure -- walking pages, and filtering an
in-memory collection -- stopped where they were told.

The mechanism is an implementation detail, so these run one set of cases against
all four of them: ``count()`` reports what the query yields, and bounds that
forbid every result are answered without asking the API at all.

``config.default_result_limit`` stays out of it and is covered by
``tests/test_characterization.py::TestCountIgnoresDefaultResultLimit``.
"""

from __future__ import annotations

from typing import Any, Callable, ClassVar, NamedTuple

import pytest
from tests.mocks.mock_client import MockUSASpendingClient

from usaspending.queries.award_accounts_query import AwardAccountsQuery
from usaspending.queries.award_transactions_search import AwardTransactionsSearch
from usaspending.queries.base_query import BaseQuery

TAS_ENDPOINT = "/references/filter_tree/tas/"
ACCOUNTS_ENDPOINT = "/awards/accounts/"

AWARD_ID = "CONT_AWD_123"
TRANSACTION_COUNT_ENDPOINT = MockUSASpendingClient.Endpoints.TRANSACTION_COUNT.format(
    award_id=AWARD_ID
)

#: Every mechanism is paged ten rows at a time where the arithmetic depends on it.
PAGE_SIZE = 10

#: The server total for the award search, deliberately far larger than the rows
#: the search endpoint serves, so a count that ignored the bound is unmistakable.
SERVER_TOTAL = 510


class Mechanism(NamedTuple):
    """A query, and what each bounded case should report for it.

    Attributes:
        query: The query under test, with no bounds applied.
        total: What an unbounded ``count()`` reports.
        two_pages: What ``page_size(10).max_pages(2)`` reports. A table value
            rather than a derived one, because the paging mechanism filters rows
            in memory and so keeps 19 of the 20 rows those pages hold.
    """

    query: BaseQuery[Any]
    total: int
    two_pages: int


def _count_endpoint(mock_usa_client, load_fixture) -> Mechanism:
    """AwardsSearch, counting from /search/spending_by_award_count/."""
    mock_usa_client.mock_award_count(contracts=SERVER_TOTAL)
    mock_usa_client.mock_award_search(
        [{"Award ID": f"AWD-{index}"} for index in range(25)], page_size=PAGE_SIZE
    )
    return Mechanism(
        query=mock_usa_client.awards.search().contracts(), total=SERVER_TOTAL, two_pages=20
    )


def _page_metadata(mock_usa_client, load_fixture) -> Mechanism:
    """AwardAccountsQuery, counting from page_metadata.count."""
    mock_usa_client.set_paginated_response(
        ACCOUNTS_ENDPOINT,
        [
            {"federal_account": f"FA-{index}", "total_transaction_obligated_amount": 1.0}
            for index in range(25)
        ],
        page_size=PAGE_SIZE,
        metadata={"count": 25},
    )
    return Mechanism(
        query=AwardAccountsQuery(mock_usa_client).award_id(AWARD_ID), total=25, two_pages=20
    )


def _paging(mock_usa_client, load_fixture) -> Mechanism:
    """A date-bounded AwardTransactionsSearch, counting by walking pages.

    The endpoint has no date filter, so the bound is applied in memory and the
    count endpoint cannot answer for it. One of the 25 rows falls outside the
    bound, and it sits on the first page.
    """
    rows = [{"id": "old", "action_date": "2023-05-01"}] + [
        {"id": f"row-{index}", "action_date": "2024-06-01"} for index in range(24)
    ]
    mock_usa_client.set_paginated_response(
        MockUSASpendingClient.Endpoints.TRANSACTIONS, rows, page_size=PAGE_SIZE
    )
    mock_usa_client.set_response(TRANSACTION_COUNT_ENDPOINT, {"transactions": len(rows)})
    return Mechanism(
        query=AwardTransactionsSearch(mock_usa_client).award_id(AWARD_ID).since("2024-01-01"),
        total=24,
        two_pages=19,
    )


def _client_side(mock_usa_client, load_fixture) -> Mechanism:
    """The TAS agency level, filtered in memory after one unpaginated fetch."""
    mock_usa_client.set_response(TAS_ENDPOINT, load_fixture("tas_agencies.json"))
    return Mechanism(query=mock_usa_client.tas.agencies, total=91, two_pages=20)


MECHANISMS: dict[str, Callable[..., Mechanism]] = {
    "count_endpoint": _count_endpoint,
    "page_metadata": _page_metadata,
    "paging": _paging,
    "client_side": _client_side,
}


@pytest.fixture(params=list(MECHANISMS))
def case(request, mock_usa_client, load_fixture) -> Mechanism:
    """One counting mechanism, mocked and ready, having made no requests yet."""
    return MECHANISMS[request.param](mock_usa_client, load_fixture)


class TestCountRespectsBounds:
    """One contract, four mechanisms."""

    def test_unbounded_count_is_the_total(self, case):
        """Nothing is bounding it, so the whole result set is reported."""
        assert case.query.count() == case.total

    def test_page_size_alone_does_not_cap(self, case):
        """page_size() sizes requests; it is not a bound on the result set."""
        assert case.query.page_size(PAGE_SIZE).count() == case.total

    def test_limit_caps_the_count(self, case):
        """What the query reports and what it yields are the same number."""
        bounded = case.query.limit(3)

        assert bounded.count() == 3
        assert len(bounded.all()) == 3

    def test_limit_above_the_total_reports_the_total(self, case):
        """A bound the result set never reaches changes nothing."""
        assert case.query.limit(1000).count() == case.total

    def test_zero_limit_costs_no_request(self, case, mock_usa_client):
        """A bound that forbids every row is answerable without the API."""
        assert case.query.limit(0).count() == 0
        assert mock_usa_client.get_request_count() == 0

    def test_zero_max_pages_costs_no_request(self, case, mock_usa_client):
        """Fetching no pages yields nothing, so nothing needs fetching."""
        assert case.query.max_pages(0).count() == 0
        assert mock_usa_client.get_request_count() == 0

    def test_max_pages_caps_the_count(self, case):
        """Two pages of ten, minus whatever those pages do not keep."""
        bounded = case.query.page_size(PAGE_SIZE).max_pages(2)

        assert bounded.count() == case.two_pages
        assert len(bounded.all()) == case.two_pages

    def test_the_stricter_of_limit_and_max_pages_wins(self, case):
        """Either bound can be the binding one."""
        bounded = case.query.page_size(PAGE_SIZE)

        # limit(15) is stricter than the 20 rows two pages would allow.
        assert bounded.limit(15).max_pages(2).count() == 15
        # max_pages(2) is stricter than a limit of 25.
        assert bounded.limit(25).max_pages(2).count() == case.two_pages

    def test_len_delegates_to_count(self, case):
        """len() is count(), so a bound cannot reach one and not the other."""
        bounded = case.query.limit(3)

        assert len(bounded) == bounded.count()


class TestBoundedAndUnboundedTransactionsAgree:
    """One builder, two counting mechanisms, one answer under a limit.

    AwardTransactionsSearch counts by paging when a date bound is set and from the
    count endpoint when one is not. The mechanism is an implementation detail;
    the caller's limit is not.
    """

    ROWS: ClassVar[list[dict[str, str]]] = [
        {"id": f"row-{index}", "action_date": "2024-06-01"} for index in range(25)
    ]

    @pytest.fixture
    def query(self, mock_usa_client):
        mock_usa_client.set_paginated_response(
            MockUSASpendingClient.Endpoints.TRANSACTIONS, self.ROWS, page_size=PAGE_SIZE
        )
        mock_usa_client.set_response(TRANSACTION_COUNT_ENDPOINT, {"transactions": len(self.ROWS)})
        return AwardTransactionsSearch(mock_usa_client).award_id(AWARD_ID).page_size(PAGE_SIZE)

    def test_both_paths_report_the_limit(self, query):
        """Every row matches the bound, so only the mechanism differs."""
        unbounded_by_date = query.limit(5)
        bounded_by_date = query.since("2024-01-01").limit(5)

        assert unbounded_by_date.count() == 5
        assert bounded_by_date.count() == 5
        assert len(unbounded_by_date.all()) == len(bounded_by_date.all()) == 5

    def test_the_count_endpoint_is_still_the_cheap_path(self, mock_usa_client, query):
        """Capping must not turn a one-request count into a pagination."""
        assert query.limit(5).count() == 5
        assert mock_usa_client.get_request_count(MockUSASpendingClient.Endpoints.TRANSACTIONS) == 0
        assert mock_usa_client.get_request_count(TRANSACTION_COUNT_ENDPOINT) == 1

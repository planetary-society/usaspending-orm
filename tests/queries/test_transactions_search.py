"""Tests for TransactionsSearch query builder."""

import logging
from datetime import date, datetime
from typing import ClassVar

import pytest
from tests.mocks.mock_client import MockUSASpendingClient

from usaspending.exceptions import ValidationError
from usaspending.models.transaction import Transaction
from usaspending.queries.transactions_search import TransactionsSearch


class TestFilteredCount:
    """count(), len() and negative indexing must agree with iteration.

    The date bounds are applied in memory, so a count taken from the API, or from
    summing raw response rows, counts rows the caller will never see.
    """

    #: One row before the bound and two after, so a filtered count differs from
    #: the raw one and a negative index lands differently under each.
    ROWS: ClassVar[list[dict[str, str]]] = [
        {"id": "old", "action_date": "2023-05-01", "modification_number": "0"},
        {"id": "mid", "action_date": "2024-06-01", "modification_number": "1"},
        {"id": "new", "action_date": "2024-07-01", "modification_number": "2"},
    ]

    def _filtered(self, mock_usa_client, page_size=100):
        mock_usa_client.set_paginated_response("/transactions/", self.ROWS, page_size=page_size)
        mock_usa_client.set_response(
            "/awards/count/transaction/CONT_AWD_123/", {"transactions": len(self.ROWS)}
        )
        return TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123").since("2024-01-01")

    def test_count_matches_iteration(self, mock_usa_client):
        query = self._filtered(mock_usa_client)

        assert query.count() == len(query.all()) == 2

    def test_len_agrees_with_slicing(self, mock_usa_client):
        """A query whose len() disagrees with its own slice is indefensible."""
        query = self._filtered(mock_usa_client)

        assert len(query[0 : len(query)]) == len(query)

    def test_negative_index_reaches_the_last_matching_row(self, mock_usa_client):
        """Offsetting by an unfiltered total lands past the end of the stream."""
        query = self._filtered(mock_usa_client)

        assert query[-1].id == "new"
        assert query[-2].id == "mid"

    def test_the_count_spans_pages(self, mock_usa_client):
        """Filtering happens per page, so the tally must accumulate across them."""
        query = self._filtered(mock_usa_client, page_size=1)

        assert query.count() == 2

    def test_truthiness_agrees_with_the_filtered_count(self, mock_usa_client):
        """The bounds narrow the results, so they must narrow what limit() bounds.

        Truthiness reads one row. If `limit(1)` bounded rows fetched rather than
        rows kept, that one row could be a non-matching one, the stream would end
        empty, and a query with matches would report itself as empty.
        """
        query = self._filtered(mock_usa_client)

        assert bool(query) is True
        assert len(query) == 2

    def test_first_returns_the_first_matching_row(self, mock_usa_client):
        """Not the first fetched row, which the bounds exclude."""
        query = self._filtered(mock_usa_client)

        assert query.first().id == "mid"

    def test_a_limit_counts_matching_rows(self, mock_usa_client):
        """limit(1) means one row the caller will see, not one row fetched."""
        query = self._filtered(mock_usa_client)

        assert [transaction.id for transaction in query.limit(1)] == ["mid"]
        assert [transaction.id for transaction in query.limit(2)] == ["mid", "new"]

    def test_an_unfiltered_query_still_uses_the_count_endpoint(self, mock_usa_client):
        """The cheap path must survive: no filter, no reason to page anything."""
        mock_usa_client.set_paginated_response("/transactions/", self.ROWS)
        mock_usa_client.set_response("/awards/count/transaction/CONT_AWD_123/", {"transactions": 3})
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        assert query.count() == 3
        assert mock_usa_client.get_request_count("/transactions/") == 0


class TestDateFilterParsing:
    """since()/until() parse once, at filter time, not once per row."""

    def test_the_bound_is_stored_parsed(self, mock_usa_client):
        """Storing the string instead would leave every behavioral test green."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123").since("2024-01-11")

        assert query._since == date(2024, 1, 11)
        assert query._until is None

    def test_chaining_keeps_both_bounds(self, mock_usa_client):
        """Each filter clones, so a clone that drops a bound loses the earlier one.

        The rows are chosen so that losing `since` changes the answer: without it
        the 2023 row passes the upper bound and comes back.
        """
        mock_usa_client.set_paginated_response(
            "/transactions/",
            [
                {"id": "too_early", "action_date": "2023-01-01"},
                {"id": "inside", "action_date": "2024-01-05"},
                {"id": "too_late", "action_date": "2024-02-01"},
            ],
        )
        query = (
            TransactionsSearch(mock_usa_client)
            .award_id("CONT_AWD_123")
            .since("2024-01-01")
            .until("2024-01-10")
        )

        assert query._since == date(2024, 1, 1)
        assert query._until == date(2024, 1, 10)
        assert [transaction.id for transaction in query] == ["inside"]

    @pytest.mark.parametrize("bound", ["since", "until"])
    def test_a_datetime_bound_is_narrowed_to_a_date(self, mock_usa_client, bound):
        """A datetime bound is stored as a date, so the row comparison works.

        The predicate compares the bound against `Transaction.action_date`, a
        date, and `datetime <= date` raises TypeError. Because the bound is only
        read during iteration, an unnarrowed one failed there rather than at the
        call, which puts the traceback a long way from the mistake.
        """
        mock_usa_client.set_paginated_response(
            "/transactions/", [{"id": "row", "action_date": "2024-01-05"}]
        )
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        bounded = getattr(query, bound)(datetime(2024, 1, 5, 14, 30))

        assert getattr(bounded, f"_{bound}") == date(2024, 1, 5)
        assert [transaction.id for transaction in bounded] == ["row"]

    @pytest.mark.parametrize("bound", ["since", "until"])
    def test_a_malformed_bound_is_rejected_at_filter_time(self, mock_usa_client, bound):
        """Not deferred to iteration, which is where the value is used."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        with pytest.raises(ValidationError, match="Expected"):
            getattr(query, bound)("15/01/2024")


class TestDateBoundValidation:
    """since()/until() hold their bounds to the same rules as time_period()."""

    @pytest.mark.parametrize("bound", ["since", "until"])
    def test_a_bound_before_the_api_floor_is_rejected(self, mock_usa_client, bound):
        """The API has no data before FY2008, so such a bound is a caller mistake.

        Previously accepted, and it then matched everything the API returned,
        which looks like a working filter that is silently doing nothing.
        """
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        with pytest.raises(ValidationError, match="before the minimum supported date"):
            getattr(query, bound)("2007-09-30")

    @pytest.mark.parametrize("bound", ["since", "until"])
    def test_the_first_day_of_fy2008_is_accepted(self, mock_usa_client, bound):
        """The floor itself is valid, so the comparison cannot be exclusive."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        bounded = getattr(query, bound)("2007-10-01")

        assert getattr(bounded, f"_{bound}") == date(2007, 10, 1)

    def test_an_inverted_range_is_rejected(self, mock_usa_client):
        """A range that cannot match is a mistake, not an empty result set.

        The predicate is `since <= action_date <= until`, so this previously
        yielded nothing while looking like a working query.
        """
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        with pytest.raises(ValidationError, match="must be on or after"):
            query.since("2024-06-01").until("2024-01-01")

    def test_an_inverted_range_is_rejected_in_either_order(self, mock_usa_client):
        """Chaining order must not decide whether the range is checked.

        Each filter clones, so whichever call comes second is the only one that
        can see both bounds. Checking in just one of them would leave
        `.until(x).since(y)` unvalidated.
        """
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        with pytest.raises(ValidationError, match="must be on or after"):
            query.until("2024-01-01").since("2024-06-01")

    def test_a_single_day_range_is_accepted(self, mock_usa_client):
        """Equal bounds select one day, so the check cannot reject equality."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        bounded = query.since("2024-01-05").until("2024-01-05")

        assert bounded._since == bounded._until == date(2024, 1, 5)

    def test_replacing_a_bound_is_checked_against_the_new_value(self, mock_usa_client):
        """Calling since() twice validates against the bound that survives.

        The second call replaces the first, so an inverted range must be judged
        on the replacement rather than on the value it displaced.
        """
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        widened = query.since("2024-01-01").until("2024-03-01").since("2024-02-01")
        assert widened._since == date(2024, 2, 1)

        with pytest.raises(ValidationError, match="must be on or after"):
            query.since("2024-01-01").until("2024-03-01").since("2024-06-01")


def payload_sent_for(mock_usa_client, query):
    """Run a query and return the JSON body the transactions endpoint received."""
    mock_usa_client.set_paginated_response(MockUSASpendingClient.Endpoints.TRANSACTIONS, [])
    mock_usa_client.set_response(
        MockUSASpendingClient.Endpoints.TRANSACTION_COUNT.format(award_id="CONT_AWD_123"),
        {"transactions": 0},
    )
    list(query)
    return mock_usa_client.get_last_request(MockUSASpendingClient.Endpoints.TRANSACTIONS)["json"]


class TestTransactionsSearchOrdering:
    """order_by() validates both arguments and reaches the request payload."""

    def test_the_sortable_fields_are_the_documented_ones(self):
        """Written out rather than read off the constant, which is the thing under test.

        Every other test here takes its field from VALID_SORT_FIELDS, so dropping
        an entry would quietly shrink what they cover instead of failing.
        """
        assert TransactionsSearch.VALID_SORT_FIELDS == frozenset(
            {
                "modification_number",
                "action_date",
                "federal_action_obligation",
                "face_value_loan_guarantee",
                "original_loan_subsidy_cost",
                "action_type_description",
                "description",
            }
        )

    @pytest.mark.parametrize("direction", ["sideways", "ASC"])
    def test_an_unsupported_direction_is_rejected(self, mock_usa_client, direction):
        """Only "asc" and "desc" are sortable directions the API understands."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        with pytest.raises(ValidationError, match="Invalid sort direction"):
            query.order_by("action_date", direction)

    def test_an_unsupported_field_is_rejected(self, mock_usa_client):
        """The endpoint sorts on a fixed list, so anything else is a mistake."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        with pytest.raises(ValidationError, match="Invalid sort field 'recipient_name'"):
            query.order_by("recipient_name")

    def test_a_sort_reaches_the_payload(self, mock_usa_client):
        """A sort the caller asked for must be sent, not just stored."""
        query = (
            TransactionsSearch(mock_usa_client)
            .award_id("CONT_AWD_123")
            .order_by("action_date", "asc")
        )

        payload = payload_sent_for(mock_usa_client, query)

        assert payload["sort"] == "action_date"
        assert payload["order"] == "asc"

    def test_the_default_direction_is_descending(self, mock_usa_client):
        """Omitting the direction must still send one, matching the signature."""
        query = (
            TransactionsSearch(mock_usa_client)
            .award_id("CONT_AWD_123")
            .order_by("federal_action_obligation")
        )

        assert payload_sent_for(mock_usa_client, query)["order"] == "desc"

    def test_an_unsorted_query_sends_no_sort(self, mock_usa_client):
        """The keys are optional, so an untouched query must not invent them."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        payload = payload_sent_for(mock_usa_client, query)

        assert "sort" not in payload
        assert "order" not in payload

    def test_order_by_returns_a_new_instance(self, mock_usa_client):
        """Every filter clones, so the receiver must be left unsorted."""
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        sorted_query = query.order_by("action_date", "asc")

        assert sorted_query is not query
        assert query._order_by is None


class TestTransactionsSearchPageSize:
    """Test TransactionsSearch endpoint-specific page size caps."""

    def test_page_size_allows_up_to_5000(self, mock_usa_client):
        """Test TransactionsSearch allows page_size up to 5000 in API payloads."""
        search = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123").page_size(5000)
        assert search._page_size == 5000

        # Prove it flows through to the actual API request payload
        mock_usa_client.set_paginated_response(
            MockUSASpendingClient.Endpoints.TRANSACTIONS, [], page_size=5000
        )
        mock_usa_client.set_response("/awards/count/transaction/CONT_AWD_123/", {"transactions": 0})
        list(search)
        last_req = mock_usa_client.get_last_request(MockUSASpendingClient.Endpoints.TRANSACTIONS)
        assert last_req["json"]["limit"] == 5000

    def test_page_size_caps_at_5000(self, mock_usa_client):
        """Test TransactionsSearch caps page_size at 5000."""
        search = TransactionsSearch(mock_usa_client).page_size(10000)
        assert search._page_size == 5000


class TestTransactionsSearchIndexing:
    """Test TransactionsSearch indexing and slicing support."""

    @pytest.fixture
    def transactions_data(self):
        """Create sample transaction data."""
        return [
            {
                "id": f"id_{i}",
                "modification_number": str(i),
                "action_date": f"2024-01-{i + 1:02d}",
                "federal_action_obligation": 1000.0 * i,
                "description": f"Transaction {i}",
            }
            for i in range(20)
        ]

    @pytest.fixture
    def setup_client(self, mock_usa_client, transactions_data):
        """Setup client with mocked transaction responses."""
        # Mock transactions endpoint - match page_size used in tests
        mock_usa_client.set_paginated_response("/transactions/", transactions_data, page_size=5)

        # Mock count endpoint
        mock_usa_client.set_response(
            "/awards/count/transaction/CONT_AWD_123/", {"transactions": len(transactions_data)}
        )
        return mock_usa_client

    def test_getitem_index_no_client_filters(self, setup_client, transactions_data):
        """Test accessing by index without client filters (should use efficient paging)."""
        query = TransactionsSearch(setup_client).award_id("CONT_AWD_123").page_size(5)

        # Access item at index 12 (should be in 3rd page)
        item = query[12]

        assert isinstance(item, Transaction)
        assert item.modification_number == "12"

        # Verify specific page fetch logic was triggered (internal implementation detail check)
        # Note: QueryBuilder.__getitem__ fetches specific page.
        # Index 12 with page_size 5 is page 3 (items 10-14).
        # We can't easily assert the specific page call without spying on _execute_query,
        # but the result correctness implies it worked.

    def test_getitem_slice_no_client_filters(self, setup_client, transactions_data):
        """Test slicing without client filters."""
        query = TransactionsSearch(setup_client).award_id("CONT_AWD_123").page_size(5)

        # Slice from 8 to 13
        items = query[8:13]

        assert len(items) == 5
        assert items[0].modification_number == "8"
        assert items[-1].modification_number == "12"

    def test_getitem_index_with_client_filters(self, setup_client, transactions_data):
        """Test accessing by index with client filters (forces iteration)."""
        # Filter: Transactions after Jan 10th (indices 10-19)
        query = (
            TransactionsSearch(setup_client)
            .award_id("CONT_AWD_123")
            .since("2024-01-11")  # matches 2024-01-11 onwards (index 10+)
        )

        # After filter, index 0 is original index 10
        item = query[0]
        assert item.modification_number == "10"

        item = query[5]
        assert item.modification_number == "15"

    def test_getitem_slice_with_client_filters(self, setup_client, transactions_data):
        """Test slicing with client filters."""
        # Filter: Transactions before Jan 10th (indices 0-9)
        query = TransactionsSearch(setup_client).award_id("CONT_AWD_123").until("2024-01-10")

        # Slice first 5 filtered items
        items = query[0:5]

        assert len(items) == 5
        assert items[0].modification_number == "0"
        assert items[4].modification_number == "4"

    def test_an_unfiltered_query_does_not_read_action_dates(self, mock_usa_client, caplog):
        """Reading action_date re-parses the row's string, so it must not happen here.

        Observable because an unparseable date makes to_date warn: a query with no
        date bound has no reason to look at the field, so no warning should appear.
        Without the guard this costs a parse per row, measured at 21 ms versus 7 ms
        over a 5000-row page.
        """
        mock_usa_client.set_paginated_response(
            "/transactions/", [{"id": "1", "action_date": "not a date"}]
        )
        query = TransactionsSearch(mock_usa_client).award_id("CONT_AWD_123")

        with caplog.at_level(logging.WARNING):
            assert [transaction.id for transaction in query] == ["1"]

        assert "Could not parse date string" not in caplog.text

    def test_an_undated_row_survives_both_bounds(self, mock_usa_client):
        """An unknown date cannot be shown to fall outside the range.

        Read through iteration rather than off the predicate, so it also shows the
        kept row reaching the caller and the bounds still excluding what they should.
        """
        mock_usa_client.set_paginated_response(
            "/transactions/",
            [
                {"id": "undated", "action_date": None},
                {"id": "inside", "action_date": "2024-01-05"},
                {"id": "outside", "action_date": "2024-02-01"},
            ],
        )
        query = (
            TransactionsSearch(mock_usa_client)
            .award_id("CONT_AWD_123")
            .since("2024-01-05")
            .until("2024-01-06")
        )

        assert [transaction.id for transaction in query] == ["undated", "inside"]

    def test_getitem_out_of_bounds_with_filters(self, setup_client):
        """Test out of bounds access with filters."""
        query = (
            TransactionsSearch(setup_client)
            .award_id("CONT_AWD_123")
            .since("2099-01-01")  # Matches nothing
        )

        with pytest.raises(IndexError):
            _ = query[0]

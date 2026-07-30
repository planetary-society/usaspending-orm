"""Tests for the TransactionsSearch global transaction search query builder."""

from __future__ import annotations

import pytest

from usaspending.exceptions import ValidationError
from usaspending.models.transaction import Transaction
from usaspending.queries.transactions_search import TransactionsSearch

SEARCH_ENDPOINT = "/search/spending_by_transaction/"
COUNT_ENDPOINT = "/search/spending_by_transaction_count/"


@pytest.fixture
def transactions_search(mock_usa_client):
    """Create a TransactionsSearch instance bound to a mock client."""
    return TransactionsSearch(mock_usa_client)


@pytest.fixture
def transaction_results(load_fixture):
    """Recorded rows from a real spending_by_transaction response."""
    return load_fixture("spending_by_transaction.json")


@pytest.fixture
def transaction_count_response(load_fixture):
    """Recorded response from a real spending_by_transaction_count request."""
    return load_fixture("spending_by_transaction_count.json")


class TestPayloadBuilding:
    """Test payload construction and the filters the API requires."""

    def test_endpoint(self, transactions_search):
        """Test that the global transaction search endpoint is used."""
        assert transactions_search._endpoint == "/search/spending_by_transaction/"

    def test_build_payload_basic(self, transactions_search):
        """Test that the payload carries filters, fields, paging and sorting."""
        payload = transactions_search.award_type_codes("A", "B")._build_payload(page=1)

        assert payload == {
            "filters": {"award_type_codes": ["A", "B"]},
            "fields": Transaction.SEARCH_FIELDS,
            "limit": 100,
            "page": 1,
            "sort": "Transaction Amount",
            "order": "desc",
        }

    def test_build_payload_fields_are_the_model_search_fields(self, transactions_search):
        """Test that the requested fields are exactly Transaction.SEARCH_FIELDS."""
        payload = transactions_search.contracts()._build_payload(page=1)

        assert payload["fields"] == Transaction.SEARCH_FIELDS
        # A copy, so a caller mutating the payload cannot corrupt the model constant.
        assert payload["fields"] is not Transaction.SEARCH_FIELDS

    def test_build_payload_aggregates_filters(self, transactions_search):
        """Test that every applied filter reaches the aggregated filters block."""
        search = (
            transactions_search.contracts()
            .keywords("space exploration")
            .agency("National Aeronautics and Space Administration")
            .fiscal_year(2024)
        )

        payload = search._build_payload(page=3)

        assert sorted(payload["filters"]["award_type_codes"]) == ["A", "B", "C", "D"]
        assert payload["filters"]["keywords"] == ["space exploration"]
        assert payload["filters"]["agencies"][0]["name"] == (
            "National Aeronautics and Space Administration"
        )
        assert "time_period" in payload["filters"]
        assert payload["page"] == 3

    def test_build_payload_honors_page_size_and_limit(self, transactions_search):
        """Test that limit() and page_size() shape the requested page length."""
        assert transactions_search.contracts().page_size(25)._build_payload(1)["limit"] == 25
        assert transactions_search.contracts().limit(5)._build_payload(1)["limit"] == 5

    def test_build_payload_requires_award_type_codes(self, transactions_search):
        """Test that a missing award_type_codes filter is a usage error."""
        search = transactions_search.keywords("space")

        with pytest.raises(ValidationError, match="award_type_codes"):
            search._build_payload(page=1)

    def test_iteration_requires_award_type_codes(self, transactions_search):
        """Test that iterating without award_type_codes raises rather than requesting."""
        with pytest.raises(ValidationError, match="award_type_codes"):
            transactions_search.keywords("space").all()


class TestAwardTypeCodes:
    """Test the award_type_codes override."""

    def test_empty_raises(self, transactions_search):
        """Test that calling award_type_codes with no codes raises."""
        with pytest.raises(ValidationError, match="At least one award type code"):
            transactions_search.award_type_codes()

    def test_invalid_code_named_in_error(self, transactions_search):
        """Test that an invalid code is named in the error message."""
        with pytest.raises(ValidationError, match="ZZZ"):
            transactions_search.award_type_codes("A", "ZZZ")

    def test_mixed_categories_accepted(self, transactions_search):
        """Test that mixing award type categories is allowed by this endpoint."""
        search = transactions_search.award_type_codes("A", "B", "C", "D", "02", "03", "04", "05")

        payload = search._build_payload(page=1)

        assert sorted(payload["filters"]["award_type_codes"]) == [
            "02",
            "03",
            "04",
            "05",
            "A",
            "B",
            "C",
            "D",
        ]

    def test_convenience_methods_merge_codes(self, transactions_search):
        """Test that .contracts() and .grants() chain and merge their codes."""
        search = transactions_search.contracts().grants()

        codes = set(search._build_payload(page=1)["filters"]["award_type_codes"])

        assert {"A", "B", "C", "D"} <= codes
        assert {"02", "03", "04", "05"} <= codes


class TestChaining:
    """Test that chained methods keep the concrete builder type."""

    def test_chain_returns_transactions_search(self, mock_usa_client):
        """Test that a full chain of filters and sorts stays a TransactionsSearch."""
        search = (
            mock_usa_client.transactions.search()
            .contracts()
            .keywords("space")
            .order_by("action_date", "asc")
            .limit(5)
        )

        assert isinstance(search, TransactionsSearch)

    @pytest.mark.parametrize(
        "apply_method",
        [
            lambda search: search.contracts(),
            lambda search: search.grants(),
            lambda search: search.award_type_codes("A"),
            lambda search: search.keywords("space"),
            lambda search: search.fiscal_year(2024),
            lambda search: search.agency("National Aeronautics and Space Administration"),
            lambda search: search.recipient_search_text("Caltech"),
            lambda search: search.order_by("action_date"),
            lambda search: search.limit(5),
            lambda search: search.page_size(10),
            lambda search: search.max_pages(2),
        ],
        ids=[
            "contracts",
            "grants",
            "award_type_codes",
            "keywords",
            "fiscal_year",
            "agency",
            "recipient_search_text",
            "order_by",
            "limit",
            "page_size",
            "max_pages",
        ],
    )
    def test_each_method_returns_transactions_search(self, transactions_search, apply_method):
        """Test that every chainable method returns a new TransactionsSearch."""
        result = apply_method(transactions_search)

        assert isinstance(result, TransactionsSearch)
        assert result is not transactions_search


class TestSorting:
    """Test the SortableQuery composition."""

    def test_sort_field_map_targets_requested_fields(self):
        """Test that every sortable field is one the query actually requests."""
        assert set(TransactionsSearch.SORT_FIELD_MAP.values()) <= set(Transaction.SEARCH_FIELDS)

    def test_default_sort_field(self, transactions_search):
        """Test that the builder defaults to the API's own default sort."""
        assert transactions_search._sort_field == "Transaction Amount"
        assert transactions_search._sort_order == "desc"

    def test_friendly_name_maps_to_display_name(self, transactions_search):
        """Test that a snake-case name resolves to the API display name."""
        search = transactions_search.order_by("place_of_performance", "asc")

        assert search._sort_field == "Primary Place of Performance"
        assert search._sort_order == "asc"

    def test_all_friendly_names_map_into_search_fields(self, transactions_search):
        """Test that each friendly name resolves to its mapped display name."""
        for friendly, api_field in TransactionsSearch.SORT_FIELD_MAP.items():
            assert transactions_search.order_by(friendly)._sort_field == api_field

    def test_display_name_accepted_directly(self, transactions_search):
        """Test that an API display name can be passed to order_by unchanged."""
        search = transactions_search.order_by("Action Date", "desc")

        assert search._sort_field == "Action Date"

    def test_invalid_field_lists_friendly_names(self, transactions_search):
        """Test that an unknown sort field is reported with the friendly names."""
        with pytest.raises(ValidationError, match="Invalid sort field") as exc_info:
            transactions_search.order_by("nonexistent_field")

        assert "transaction_amount" in str(exc_info.value)

    def test_invalid_direction_raises(self, transactions_search):
        """Test that an unsupported sort direction raises."""
        with pytest.raises(ValidationError, match="Invalid sort direction"):
            transactions_search.order_by("action_date", "sideways")

    def test_sort_reaches_the_payload(self, transactions_search):
        """Test that an applied sort is what the payload sends."""
        payload = transactions_search.contracts().order_by("action_date", "asc")._build_payload(1)

        assert payload["sort"] == "Action Date"
        assert payload["order"] == "asc"


class TestCloning:
    """Test immutable query construction."""

    def test_clone_carries_filters_sort_and_bounds(self, transactions_search):
        """Test that _clone copies filters, sort selection and paging bounds."""
        search = (
            transactions_search.contracts()
            .keywords("space")
            .order_by("action_date", "asc")
            .limit(25)
            .page_size(10)
            .max_pages(3)
        )

        clone = search._clone()

        assert clone is not search
        assert clone._filter_objects == search._filter_objects
        assert clone._filter_objects is not search._filter_objects
        assert clone._sort_field == "Action Date"
        assert clone._sort_order == "asc"
        assert clone._total_limit == 25
        assert clone._page_size == 10
        assert clone._max_pages == 3

    def test_original_is_not_mutated(self, transactions_search):
        """Test that chaining leaves the query it was called on untouched."""
        contracts = transactions_search.contracts()

        contracts.keywords("space").order_by("action_date", "asc").limit(5)

        assert len(contracts._filter_objects) == 1
        assert contracts._sort_field == "Transaction Amount"
        assert contracts._sort_order == "desc"
        assert contracts._total_limit is None
        assert transactions_search._filter_objects == []

    def test_page_size_clamps_to_endpoint_maximum(self, transactions_search):
        """Test that a page size above the endpoint cap is held to the cap."""
        assert TransactionsSearch._MAX_PAGE_SIZE == 100
        assert transactions_search.page_size(500)._page_size == 100


class TestIteration:
    """Test iteration against recorded API responses."""

    def test_yields_transaction_models(self, mock_usa_client, transaction_results):
        """Test that recorded rows are transformed into Transaction models."""
        mock_usa_client.set_paginated_response(
            SEARCH_ENDPOINT, transaction_results["results"], page_size=100
        )

        results = mock_usa_client.transactions.search().contracts().all()

        assert len(results) == len(transaction_results["results"])
        assert all(isinstance(result, Transaction) for result in results)

    def test_raw_returns_the_row(self, mock_usa_client, transaction_results):
        """Test that a model's raw data is the response row it came from."""
        rows = transaction_results["results"]
        mock_usa_client.set_paginated_response(SEARCH_ENDPOINT, rows, page_size=100)

        first = mock_usa_client.transactions.search().contracts().first()

        assert first.raw == rows[0]

    def test_server_appended_keys_present_in_raw(self, mock_usa_client, transaction_results):
        """Test that the unrequested identifiers the server appends survive."""
        mock_usa_client.set_paginated_response(
            SEARCH_ENDPOINT, transaction_results["results"], page_size=100
        )

        first = mock_usa_client.transactions.search().contracts().first()

        assert "internal_id" in first.raw
        assert "generated_internal_id" in first.raw

    def test_mixed_category_rows_iterate(self, mock_usa_client, load_fixture):
        """Test iteration over a recorded response spanning two award categories."""
        fixture = load_fixture("spending_by_transaction_mixed.json")
        mock_usa_client.set_paginated_response(SEARCH_ENDPOINT, fixture["results"], page_size=100)

        results = mock_usa_client.transactions.search().contracts().grants().all()

        assert len(results) == len(fixture["results"])
        assert all(isinstance(result, Transaction) for result in results)

    def test_iteration_requests_the_search_endpoint(self, mock_usa_client, transaction_results):
        """Test that iteration posts to the global transaction search endpoint."""
        mock_usa_client.set_paginated_response(
            SEARCH_ENDPOINT, transaction_results["results"], page_size=100
        )

        mock_usa_client.transactions.search().contracts().all()

        last_request = mock_usa_client.get_last_request(SEARCH_ENDPOINT)
        assert last_request["method"] == "POST"
        assert last_request["json"]["fields"] == Transaction.SEARCH_FIELDS


class TestCount:
    """Test counting through the dedicated count endpoint."""

    def test_count_sums_selected_categories(self, mock_usa_client, transaction_count_response):
        """Test that only the buckets for the selected categories are summed."""
        mock_usa_client.set_response(COUNT_ENDPOINT, transaction_count_response)
        buckets = transaction_count_response["results"]

        count = mock_usa_client.transactions.search().contracts().grants().count()

        assert count == buckets["contracts"] + buckets["grants"]

    def test_count_excludes_unselected_categories(
        self, mock_usa_client, transaction_count_response
    ):
        """Test that a nonzero bucket for an unselected category is left out."""
        mock_usa_client.set_response(COUNT_ENDPOINT, transaction_count_response)
        buckets = transaction_count_response["results"]
        assert buckets["contracts"] > 0

        count = mock_usa_client.transactions.search().grants().count()

        assert count == buckets["grants"]
        assert count != buckets["contracts"] + buckets["grants"]

    def test_count_sends_the_filters(self, mock_usa_client, transaction_count_response):
        """Test that the count request carries the same filters as the search."""
        mock_usa_client.set_response(COUNT_ENDPOINT, transaction_count_response)

        mock_usa_client.transactions.search().contracts().keywords("space").count()

        request = mock_usa_client.get_last_request(COUNT_ENDPOINT)
        assert request["method"] == "POST"
        assert set(request["json"]) == {"filters"}
        assert set(request["json"]["filters"]) == {"award_type_codes", "keywords"}
        assert request["json"]["filters"]["keywords"] == ["space"]
        assert sorted(request["json"]["filters"]["award_type_codes"]) == ["A", "B", "C", "D"]

    def test_count_requires_award_type_codes(self, transactions_search):
        """Test that counting without award_type_codes is a usage error."""
        with pytest.raises(ValidationError, match="award_type_codes"):
            transactions_search.keywords("space").count()

    def test_count_honors_limit(self, mock_usa_client, transaction_count_response):
        """Test that an explicit limit caps the reported count."""
        mock_usa_client.set_response(COUNT_ENDPOINT, transaction_count_response)

        count = mock_usa_client.transactions.search().contracts().limit(10).count()

        assert count == 10


class TestProgramActivitiesCount:
    """The count endpoint rejects program_activities, so counting fails loudly.

    Everything that consults the count raises `ValidationError`; everything
    that merely fetches rows still works. `list(query)` is the trap: CPython
    asks `__len__` for a length hint before iterating, so it raises where a
    plain loop or `.all()` does not (see `BaseQuery.all` for the mechanics).
    """

    @pytest.fixture
    def pa_query(self, mock_usa_client, transaction_results):
        """A query with program_activities set, over a working search endpoint."""
        # The recorded page reports hasNext, and the mock returns a default
        # response identically for every page, so close the pagination here.
        single_page = {
            **transaction_results,
            "page_metadata": {**transaction_results["page_metadata"], "hasNext": False},
        }
        mock_usa_client.set_response(SEARCH_ENDPOINT, single_page)
        return (
            mock_usa_client.transactions.search().contracts().program_activities({"code": "0001"})
        )

    def test_count_raises_with_pointer_to_iteration(self, pa_query):
        """count() names the unsupported filter and the working alternatives."""
        with pytest.raises(ValidationError, match="program_activities") as exc_info:
            pa_query.count()
        assert ".all()" in str(exc_info.value)

    def test_len_raises(self, pa_query):
        """len() delegates to count() and raises the same error."""
        with pytest.raises(ValidationError, match="program_activities"):
            len(pa_query)

    def test_list_constructor_raises_via_length_hint(self, pa_query):
        """list(query), like [*query], consults __len__ for a hint, so it raises."""
        with pytest.raises(ValidationError, match="program_activities"):
            list(pa_query)
        with pytest.raises(ValidationError, match="program_activities"):
            _ = [*pa_query]

    def test_indexing_and_slicing_raise(self, pa_query):
        """Indexing and slicing consult the count before fetching, so both raise."""
        with pytest.raises(ValidationError, match="program_activities"):
            pa_query[0]
        with pytest.raises(ValidationError, match="program_activities"):
            pa_query[-1]
        with pytest.raises(ValidationError, match="program_activities"):
            pa_query[:2]

    def test_iteration_still_works(self, pa_query):
        """A plain loop never counts, so the filter reaches the search intact."""
        rows = [txn for txn in pa_query]

        assert len(rows) == 3
        assert all(isinstance(txn, Transaction) for txn in rows)
        request = pa_query._client.get_last_request(SEARCH_ENDPOINT)
        assert request["json"]["filters"]["program_activities"] == [{"code": "0001"}]

    def test_all_first_and_bool_still_work(self, pa_query):
        """all(), first() and bool() avoid __len__ by design, so they work."""
        assert len(pa_query.all()) == 3
        assert pa_query.first() is not None
        assert bool(pa_query)

    def test_limit_zero_short_circuits_before_the_guard(self, pa_query):
        """Bounds that forbid every result answer count() without the API."""
        assert pa_query.limit(0).count() == 0


class TestResultWindowEdge:
    """Requests past the API's 50,000-row window raise rather than truncate."""

    def test_iteration_past_the_window_raises_api_error(self, mock_usa_client, transaction_results):
        """A mid-iteration 422 from the API surfaces as APIError, uncaught."""
        from usaspending.exceptions import APIError

        rows = transaction_results["results"]
        # Two full-looking pages that both claim more data follows, so the
        # iterator asks for page 3, where the mocked window edge answers 422
        # with the upstream error text.
        pages = [
            {
                "limit": 100,
                "results": rows,
                "page_metadata": {"page": page, "hasNext": True},
            }
            for page in (1, 2)
        ]
        mock_usa_client.add_response_sequence(SEARCH_ENDPOINT, pages)

        original = mock_usa_client._make_request

        def with_window_edge(method, endpoint, json=None, params=None):
            if endpoint == SEARCH_ENDPOINT and json and json.get("page", 1) > 2:
                raise APIError(
                    "Page 3 of size 100 is over the maximum result limit (50000). "
                    "Consider using custom data downloads to obtain large data sets.",
                    status_code=422,
                )
            return original(method, endpoint, json=json, params=params)

        mock_usa_client._make_request = with_window_edge

        query = mock_usa_client.transactions.search().contracts()
        seen = 0
        with pytest.raises(APIError, match="maximum result limit"):
            for _ in query:
                seen += 1

        # Both mocked pages were yielded before the edge raised: the failure
        # is loud and late, never a silent truncation.
        assert seen == len(rows) * 2

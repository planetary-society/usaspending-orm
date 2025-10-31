"""Tests for SpendingSearch query builder functionality."""

from __future__ import annotations

import datetime
import pytest

from usaspending.queries.spending_search import SpendingSearch
from usaspending.models.recipient_spending import RecipientSpending
from usaspending.models.district_spending import DistrictSpending
from usaspending.exceptions import ValidationError


class TestSpendingSearchInitialization:
    """Test SpendingSearch initialization."""

    def test_init(self, mock_usa_client):
        """Test SpendingSearch initialization."""
        search = SpendingSearch(mock_usa_client)

        assert search._client is mock_usa_client
        assert search._category is None
        assert search._spending_level == "transactions"
        assert search._subawards is False


class TestCategorySelection:
    """Test category selection methods."""

    def test_by_recipient(self, mock_usa_client):
        """Test by_recipient category selection."""
        search = SpendingSearch(mock_usa_client)
        recipient_search = search.by_recipient()

        assert recipient_search._spending_level == "transactions"
        assert recipient_search is not search  # Should return new instance

    def test_by_district(self, mock_usa_client):
        """Test by_district category selection."""
        search = SpendingSearch(mock_usa_client)
        district_search = search.by_district()

        assert district_search._category == "district"
        assert district_search is not search  # Should return new instance

    def test_by_state(self, mock_usa_client):
        """Test by_state category selection."""
        search = SpendingSearch(mock_usa_client)
        state_search = search.by_state()

        assert state_search._category == "state"
        assert state_search is not search  # Should return new instance

    def test_endpoint_with_recipient_category(self, mock_usa_client):
        """Test endpoint property with recipient category."""
        search = SpendingSearch(mock_usa_client).by_recipient()

        assert search._endpoint == mock_usa_client.Endpoints.SPENDING_BY_RECIPIENT

    def test_endpoint_with_district_category(self, mock_usa_client):
        """Test endpoint property with district category."""
        search = SpendingSearch(mock_usa_client).by_district()

        assert search._endpoint == mock_usa_client.Endpoints.SPENDING_BY_DISTRICT

    def test_endpoint_with_state_category(self, mock_usa_client):
        """Test endpoint property with state category."""
        search = SpendingSearch(mock_usa_client).by_state()

        assert search._endpoint == mock_usa_client.Endpoints.SPENDING_BY_STATE

    def test_endpoint_without_category_raises_error(self, mock_usa_client):
        """Test endpoint property without category raises ValidationError."""
        search = SpendingSearch(mock_usa_client)

        with pytest.raises(ValidationError, match="Category must be set"):
            _ = search._endpoint


class TestSpendingLevelConfiguration:
    """Test spending level configuration methods."""

    def test_spending_level(self, mock_usa_client):
        """Test spending_level method."""
        search = SpendingSearch(mock_usa_client)

        # Test transactions level
        transactions_search = search.spending_level("transactions")
        assert transactions_search._spending_level == "transactions"

        # Test awards level
        awards_search = search.spending_level("awards")
        assert awards_search._spending_level == "awards"

        # Test subawards level
        subawards_search = search.spending_level("subawards")
        assert subawards_search._spending_level == "subawards"

    def test_subawards_only(self, mock_usa_client):
        """Test subawards_only method."""
        search = SpendingSearch(mock_usa_client)

        subawards_search = search.subawards_only()
        assert subawards_search._subawards is True

        no_subawards_search = search.subawards_only(False)
        assert no_subawards_search._subawards is False


class TestFilterMethods:
    """Test filter methods."""

    def test_with_recipient_id(self, mock_usa_client):
        """Test with_recipient_id filter method."""
        search = SpendingSearch(mock_usa_client)
        recipient_id = "1c3edaaa-611b-840c-bf2b-fd34df49f21f-P"

        filtered_search = search.recipient_id(recipient_id)

        assert len(filtered_search._filter_objects) == 1
        filter_dict = filtered_search._filter_objects[0].to_dict()
        assert "recipient_id" in filter_dict
        assert filter_dict["recipient_id"] == [recipient_id]


class TestResultTransformation:
    """Test result transformation."""

    def test_transform_result_recipient(self, mock_usa_client):
        """Test _transform_result for recipient category."""
        search = SpendingSearch(mock_usa_client).by_recipient()

        result_data = {
            "id": 12345,
            "name": "Test Recipient",
            "amount": 1000000.0,
            "recipient_id": "test-recipient-id",
        }

        transformed = search._transform_result(result_data)

        assert isinstance(transformed, RecipientSpending)
        assert transformed.name == "Test Recipient"
        assert transformed.spending_level == "transactions"

    def test_transform_result_district(self, mock_usa_client):
        """Test _transform_result for district category."""
        search = SpendingSearch(mock_usa_client).by_district()

        result_data = {"id": None, "name": "TX-12", "amount": 1500000.0, "code": "12"}

        transformed = search._transform_result(result_data)

        assert isinstance(transformed, DistrictSpending)
        assert transformed.name == "TX-12"
        assert transformed.category == "district"


class TestBuildPayload:
    """Test _build_payload method."""

    def test_build_payload_recipient(self, mock_usa_client):
        """Test _build_payload for recipient search."""
        search = SpendingSearch(mock_usa_client).by_recipient().agency("NASA")

        payload = search._build_payload(1)

        assert payload["category"] == "recipient"
        assert payload["page"] == 1
        assert payload["spending_level"] == "transactions"
        assert payload["limit"] == 100
        assert "filters" in payload
        assert "agencies" in payload["filters"]

    def test_build_payload_district_with_spending_level(self, mock_usa_client):
        """Test _build_payload for district search with custom spending level."""
        search = SpendingSearch(mock_usa_client).by_district().spending_level("awards")

        payload = search._build_payload(2)

        assert payload["category"] == "district"
        assert payload["page"] == 2
        assert payload["spending_level"] == "awards"

    def test_build_payload_with_subawards(self, mock_usa_client):
        """Test _build_payload with subawards flag."""
        search = SpendingSearch(mock_usa_client).by_recipient().subawards_only()

        payload = search._build_payload(1)

        assert payload["subawards"] is True

    def test_build_payload_without_category_raises_error(self, mock_usa_client):
        """Test _build_payload without category raises ValidationError."""
        search = SpendingSearch(mock_usa_client)

        with pytest.raises(ValidationError, match="Category must be set"):
            search._build_payload(1)


class TestCloning:
    """Test query builder cloning."""

    def test_clone_preserves_state(self, mock_usa_client):
        """Test that _clone preserves all state."""
        original = (
            SpendingSearch(mock_usa_client)
            .by_recipient()
            .spending_level("awards")
            .subawards_only()
        )

        clone = original._clone()

        assert clone._category == "recipient"
        assert clone._spending_level == "awards"
        assert clone._subawards is True
        assert clone is not original

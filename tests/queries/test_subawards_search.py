"""Tests for SubAwardsSearch query builder."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from usaspending.exceptions import ValidationError
from usaspending.models.subaward import SubAward
from usaspending.queries.subawards_search import SubAwardsSearch


class TestSubAwardsSearch:
    """Test SubAwardsSearch query builder functionality."""

    @pytest.fixture
    def subawards_response(self):
        """Load subawards fixture data."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "search_results_subawards.json"
        with open(fixture_path, "r") as f:
            return json.load(f)

    def test_subawards_search_initialization(self, mock_usa_client):
        """Test SubAwardsSearch can be initialized."""
        search = SubAwardsSearch(mock_usa_client)
        assert search._client is mock_usa_client
        assert search._award_id is None

    def test_build_payload_includes_subawards_flag(self, mock_usa_client):
        """Test that payload always includes subawards=true."""
        search = SubAwardsSearch(mock_usa_client).with_award_types("A", "B", "C")
        
        payload = search._build_payload(page=1)
        
        assert payload["subawards"] is True
        assert payload["spending_level"] == "subawards"
        assert "filters" in payload
        assert payload["filters"]["award_type_codes"] == ["A", "B", "C"]

    def test_build_payload_with_award_filter(self, mock_usa_client):
        """Test that payload includes prime_award_generated_internal_id when filtering by award."""
        search = (SubAwardsSearch(mock_usa_client)
                 .with_award_types("A", "B", "C")
                 .for_award("CONT_AWD_123_456"))
        
        payload = search._build_payload(page=1)
        
        assert payload["filters"]["prime_award_generated_internal_id"] == "CONT_AWD_123_456"
        assert payload["subawards"] is True
        assert payload["spending_level"] == "subawards"

    def test_transform_result_returns_subaward(self, mock_usa_client, subawards_response):
        """Test that transform_result returns SubAward instances."""
        from usaspending.utils.formatter import contracts_titlecase
        
        search = SubAwardsSearch(mock_usa_client)
        
        subaward_data = subawards_response["results"][0]
        result = search._transform_result(subaward_data)
        
        assert isinstance(result, SubAward)
        assert result.id == subaward_data["internal_id"]
        expected_name = contracts_titlecase(subaward_data["Sub-Awardee Name"])
        assert result.sub_awardee_name == expected_name

    def test_get_fields_for_contract_subawards(self, mock_usa_client):
        """Test field selection for contract subawards."""
        search = SubAwardsSearch(mock_usa_client).with_award_types("A", "B", "C", "D")
        
        fields = search._get_fields()
        
        # Should return contract subaward fields
        assert "NAICS" in fields
        assert "PSC" in fields
        assert "Assistance Listing" not in fields

    def test_get_fields_for_grant_subawards(self, mock_usa_client):
        """Test field selection for grant subawards."""
        search = SubAwardsSearch(mock_usa_client).with_award_types("02", "03", "04", "05")
        
        fields = search._get_fields()
        
        # Should return grant subaward fields
        assert "Assistance Listing" in fields
        assert "NAICS" not in fields
        assert "PSC" not in fields

    def test_get_fields_for_mixed_award_types(self, mock_usa_client):
        """Test field selection when mixing contract and grant types returns union."""
        # This should normally raise an error in AwardsSearch validation,
        # but if it gets through, we return all fields
        search = SubAwardsSearch(mock_usa_client)
        search._filter_objects = []  # Clear filters to bypass validation
        
        # Manually set both contract and grant codes
        from usaspending.queries.filters import SimpleListFilter
        search._filter_objects.append(SimpleListFilter(key="award_type_codes", values=["A", "02"]))
        
        fields = search._get_fields()
        
        # Should return union of both field sets
        assert "NAICS" in fields
        assert "PSC" in fields
        assert "Assistance Listing" in fields

    def test_for_award_method(self, mock_usa_client):
        """Test for_award method sets award_id."""
        search = SubAwardsSearch(mock_usa_client).for_award("CONT_AWD_123")
        
        assert search._award_id == "CONT_AWD_123"

    def test_for_award_strips_whitespace(self, mock_usa_client):
        """Test for_award strips whitespace from award_id."""
        search = SubAwardsSearch(mock_usa_client).for_award("  CONT_AWD_123  ")
        
        assert search._award_id == "CONT_AWD_123"

    def test_for_award_empty_raises_error(self, mock_usa_client):
        """Test for_award with empty string raises ValidationError."""
        with pytest.raises(ValidationError, match="award_id cannot be empty"):
            SubAwardsSearch(mock_usa_client).for_award("")

    def test_count_with_award_id(self, mock_usa_client):
        """Test count method uses efficient endpoint when award_id is set."""
        mock_usa_client._make_request = MagicMock(return_value={"subawards": 7})
        
        search = SubAwardsSearch(mock_usa_client).for_award("CONT_AWD_123")
        count = search.count()
        
        assert count == 7
        mock_usa_client._make_request.assert_called_once_with(
            "GET", "/v2/awards/count/subaward/CONT_AWD_123/"
        )

    def test_count_without_award_id(self, mock_usa_client):
        """Test count method falls back to parent implementation without award_id."""
        search = SubAwardsSearch(mock_usa_client).with_award_types("A", "B")
        
        # Mock the API response for the count endpoint (parent class count)
        mock_usa_client._make_request = MagicMock(return_value={
            "aggregations": {
                "contracts": 5,
                "idvs": 0,
                "grants": 0,
                "direct_payments": 0,
                "loans": 0,
                "other": 0
            }
        })
        
        count = search.count()
        assert count == 5

    def test_query_chaining(self, mock_usa_client):
        """Test that SubAwardsSearch supports query chaining."""
        search = (SubAwardsSearch(mock_usa_client)
                 .with_award_types("A", "B", "C")
                 .for_award("CONT_AWD_123")
                 .limit(50)
                 .page_size(25))
        
        assert search._award_id == "CONT_AWD_123"
        assert search._total_limit == 50
        assert search._page_size == 25

    def test_inherits_award_search_filters(self, mock_usa_client):
        """Test that SubAwardsSearch inherits filter methods from AwardsSearch."""
        search = SubAwardsSearch(mock_usa_client)
        
        # Should have all AwardsSearch filter methods
        assert hasattr(search, "with_keywords")
        assert hasattr(search, "in_time_period")
        assert hasattr(search, "for_agency")
        assert hasattr(search, "with_award_types")
        assert hasattr(search, "with_place_of_performance_scope")
        assert hasattr(search, "with_place_of_performance_locations")
        assert hasattr(search, "with_recipient_locations")
        assert hasattr(search, "with_award_amounts")

    def test_immutability(self, mock_usa_client):
        """Test that SubAwardsSearch maintains immutability."""
        search1 = SubAwardsSearch(mock_usa_client).with_award_types("A", "B")
        search2 = search1.for_award("CONT_AWD_123")
        search3 = search2.limit(10)
        
        # Each should be a different instance
        assert search1 is not search2
        assert search2 is not search3
        
        # Original should not be modified
        assert search1._award_id is None
        assert search2._award_id == "CONT_AWD_123"
        assert search1._total_limit is None
        assert search3._total_limit == 10
"""Tests for Award model functionality."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from usaspending.models.award import Award
from usaspending.models.recipient import Recipient
from usaspending.models.location import Location

from usaspending.exceptions import ValidationError


class TestAwardInitialization:
    """Test Award model initialization."""
    
    def test_init_with_dict_data(self, mock_usa_client):
        """Test Award initialization with dictionary data."""
        data = {"generated_unique_award_id": "CONT_AWD_123", "description": "Test Award"}
        award = Award(data, mock_usa_client)
        
        assert award._data["generated_unique_award_id"] == "CONT_AWD_123"
        assert award._data["description"] == "Test Award"
        assert award._client is not None
    
    def test_init_with_string_id(self, mock_usa_client):
        """Test Award initialization with string award ID."""
        award_id = "CONT_AWD_123"
        award = Award(award_id, mock_usa_client)
        
        assert award._data["generated_unique_award_id"] == "CONT_AWD_123"
        assert award._client is not None
    
    def test_init_with_invalid_type_raises_error(self, mock_usa_client):
        """Test that Award initialization with invalid type raises ValidationError."""
        with pytest.raises(ValidationError):
            Award(123, mock_usa_client)
    
    def test_init_copies_data_dict(self, mock_usa_client):
        """Test that Award initialization copies the data dictionary."""
        original_data = {"generated_unique_award_id": "CONT_AWD_123"}
        award = Award(original_data, mock_usa_client)
        
        # Modify original data
        original_data["new_field"] = "new_value"
        
        # Award should not be affected
        assert "new_field" not in award._data


class TestAwardFetchDetails:
    """Test the _fetch_details() method specifically."""
    
    def test_fetch_details_success(self, mock_usa_client, award_fixture_data):
        """Test successful fetching of award details."""
        # Set up fixture response for award details
        mock_usa_client.set_fixture_response(
            "/v2/awards/CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-/",
            "awards/contract"
        )
        
        # Create an award with minimal data
        award = Award({"generated_unique_award_id": "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"}, mock_usa_client)
        
        # Call _fetch_details
        result = award._fetch_details()
        
        # Verify the result
        assert result == award_fixture_data
    
    def test_fetch_details_no_award_id(self, mock_usa_client):
        """Test _fetch_details raises ValidationError when no award ID is available."""
        # Create award without award ID
        award = Award({}, mock_usa_client)
        
        with pytest.raises(ValidationError):
            award._fetch_details()
    
    def test_fetch_details_api_exception(self, mock_usa_client):
        """Test _fetch_details handles API exceptions gracefully."""
        # Set up error response
        mock_usa_client.set_error_response(
            "/v2/awards/CONT_AWD_123/",
            500,
            error_message="Internal Server Error"
        )
        
        award = Award({"generated_unique_award_id": "CONT_AWD_123"}, mock_usa_client)
        
        # Should return None instead of raising
        result = award._fetch_details()
        
        assert result is None
    
    def test_ensure_details_integration(self, mock_usa_client, award_fixture_data):
        """Test that _ensure_details() properly uses _fetch_details()."""
        # Set up fixture response
        mock_usa_client.set_fixture_response(
            "/v2/awards/CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-/",
            "awards/contract"
        )
        
        # Create award with minimal data
        award = Award({"generated_unique_award_id": "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"}, mock_usa_client)
        
        # Initially should not have description
        assert "description" not in award._data
        
        # Call _ensure_details
        award._ensure_details()
        
        # Now should have the full data merged
        assert award._data["description"] == award_fixture_data["description"]
        assert award._details_fetched is True
    
    def test_ensure_details_only_called_once(self, mock_usa_client, award_fixture_data):
        """Test that _ensure_details() only fetches once."""
        # Set up fixture response
        mock_usa_client.set_fixture_response(
            "/v2/awards/CONT_AWD_123/",
            "awards/contract"
        )
        
        award = Award({"generated_unique_award_id": "CONT_AWD_123"}, mock_usa_client)
        
        # Call multiple times
        award._ensure_details()
        award._ensure_details()
        award._ensure_details()
        
        # Should only fetch once (check request history)
        assert mock_usa_client.get_request_count("/v2/awards/CONT_AWD_123/") == 1


class TestAwardPropertiesWithRealData:
    """Test Award model properties using real fixture data."""
    
    def test_prime_award_id_property(self, mock_usa_client, award_fixture_data):
        """Test prime_award_id property extraction with real data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        assert award.prime_award_id == "80GSFC18C0008"
    
    def test_generated_unique_award_id_property(self, mock_usa_client, award_fixture_data):
        """Test generated_unique_award_id property with real data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        assert award.generated_unique_award_id == "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
    
    def test_description_property(self, mock_usa_client, award_fixture_data):
        """Test description property with real data and smart sentence casing."""
        award = Award(award_fixture_data, mock_usa_client)
        
        description = award.description
        assert isinstance(description, str)
        assert len(description) > 0
        # Real data description should start with "The" due to smart_sentence_case
        assert description.startswith("The")
    
    def test_total_obligation_property(self, mock_usa_client, award_fixture_data):
        """Test total_obligation property with real financial data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        assert award.total_obligation == 168657782.95
        assert isinstance(award.total_obligation, float)
    
    def test_total_outlay_property(self, mock_usa_client, award_fixture_data):
        """Test total_outlay property with real financial data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        assert award.total_outlay == 150511166.49
        assert isinstance(award.total_outlay, float)
    
    def test_award_amount_property(self, mock_usa_client, award_fixture_data):
        """Test award_amount property with real data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        # Real fixture data doesn't have "Award Amount" or "Loan Amount" keys
        assert award.award_amount == 0.0
    
    def test_potential_value_property(self, mock_usa_client, award_fixture_data):
        """Test potential_value property fallback with real data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        # Should fall back to total_obligation since no "Award Amount" or "Loan Amount"
        assert award.potential_value == award.total_obligation
        assert award.potential_value == 168657782.95
    
    def test_period_of_performance_from_real_data(self, mock_usa_client, award_fixture_data):
        """Test period_of_performance creation from real fixture data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        pop = award.period_of_performance
        assert pop is not None
        
        # Test the structure - PeriodOfPerformance uses raw not _data
        assert hasattr(pop, 'raw')
        expected_pop_data = award_fixture_data["period_of_performance"]
        assert pop.raw == expected_pop_data


class TestAwardHelperMethods:
    """Test Award helper methods with real data."""
    
    def test_get_method_with_real_data(self, mock_usa_client, award_fixture_data):
        """Test the get() helper method with real fixture data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        assert award.raw.get("piid") == "80GSFC18C0008"
        assert award.raw.get("type") == "D"
        assert award.raw.get("category") == "contract"
        assert award.raw.get("nonexistent_key", "default") == "default"
        assert award.raw.get("nonexistent_key") is None
    
    def testraw_property(self, mock_usa_client, award_fixture_data):
        """Test the raw property returns the data dictionary."""
        award = Award(award_fixture_data, mock_usa_client)
        
        assert award.raw == award._data
        assert award.raw is award._data
        assert award.raw["piid"] == "80GSFC18C0008"
    
    def test_usa_spending_url_property_with_real_data(self, mock_usa_client, award_fixture_data):
        """Test USA spending URL generation with real data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        expected_url = "https://www.usaspending.gov/award/CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-/"
        assert award.usa_spending_url == expected_url


class TestAwardTransactions:
    """Test Award transactions property (current implementation)."""
    
    def test_transactions_current_implementation_with_real_data(self, mock_usa_client, award_fixture_data):
        """Test current transactions implementation returns transactions from fixture data."""
        from unittest.mock import Mock
        
        # Set up mock transactions response using the helper method
        award_id = "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        mock_usa_client.mock_transactions_for_award(award_id, fixture_name="awards/transactions")
        
        # Mock the transactions resource to return a mock query builder
        mock_transactions_resource = Mock()
        mock_query = Mock()
        
        # Make the query builder's for_award method return itself for chaining
        mock_query.for_award = Mock(return_value=mock_query)
        
        # Mock the all() method to return Transaction objects from the fixture data
        from usaspending.models.transaction import Transaction
        # Get the fixture data from the mock client
        response = mock_usa_client._make_request("POST", "/v2/transactions/", {})
        mock_transactions = [
            Transaction(result) for result in response["results"]
        ]
        mock_query.all = Mock(return_value=mock_transactions)
        
        # Set up the mock resource to return the mock query
        mock_transactions_resource.for_award = Mock(return_value=mock_query)
        mock_usa_client._resources["transactions"] = mock_transactions_resource
        
        award = Award(award_fixture_data, mock_usa_client)
        
        # Get transactions
        transactions = award.transactions
        
        # Verify the result
        assert isinstance(transactions, list)
        assert len(transactions) == 3
        
        # Verify the correct methods were called
        mock_transactions_resource.for_award.assert_called_once_with("CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-")
        mock_query.all.assert_called_once()
        
        # Verify transaction data
        assert transactions[0].id == "CONT_TX_8000_-NONE-_80GSFC18C0008_P00065_-NONE-_0"
        assert transactions[0].federal_action_obligation == 1600000.0
        assert transactions[1].id == "CONT_TX_8000_-NONE-_80GSFC18C0008_P00064_-NONE-_0"
        assert transactions[2].id == "CONT_TX_8000_-NONE-_80GSFC18C0008_P00063_-NONE-_0"


class TestAwardTypeInformation:
    """Test Award type information extraction from real data."""
    
    def test_award_type_information_from_real_data(self, mock_usa_client, award_fixture_data):
        """Test extraction of award type information from real fixture data."""
        award = Award(award_fixture_data, mock_usa_client)
        
        # Test that we can access type information that exists in real data
        assert award.raw.get("type") == "D"
        assert award.raw.get("type_description") == "DEFINITIVE CONTRACT"
        assert award.raw.get("category") == "contract"
        
        # Test financial amounts from real data
        assert award.raw.get("total_obligation") == 168657782.95
        assert award.raw.get("total_account_outlay") == 150511166.49
        assert award.raw.get("base_exercised_options") == 168657782.95
        assert award.raw.get("base_and_all_options") == 168657782.95


class TestAwardEdgeCases:
    """Test Award behavior with edge cases and missing data."""

    
    def test_get_value_integration_with_truthy_logic(self, mock_usa_client):
        """Test that Award properly uses the updated get_value() method for truthy values."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "field1": "",  # Falsy
            "field2": None,  # Falsy
            "field3": "actual_value"  # Truthy
        }
        award = Award(data, mock_usa_client)
        
        # Should skip falsy values and return the truthy one
        result = award.get_value(["field1", "field2", "field3"])
        assert result == "actual_value"
    
    def test_financial_properties_with_award_amount_key(self, mock_usa_client):
        """Test financial properties when Award Amount is present."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "Award Amount": 1000000.50,
            "total_obligation": 500000.25
        }
        award = Award(data, mock_usa_client)
        
        # total_obligation should prefer "total_obligation" over "Award Amount"
        assert award.total_obligation == 500000.25
        # award_amount should use "Award Amount"
        assert award.award_amount == 1000000.50
        # potential_value should use "Award Amount" over fallback
        assert award.potential_value == 1000000.50


class TestAwardPropertyCaching:
    """Test that Award properties are properly cached using @cached_property."""
    
    def test_recipient_property_is_cached(self, mock_usa_client):
        """Test that recipient property is only created once per Award instance."""
        # Create award with recipient data
        award_data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "recipient": {
                "recipient_id": "REC123",
                "recipient_name": "Test Company",
                "location": {
                    "country_name": "UNITED STATES",
                    "state_code": "CA"
                }
            }
        }
        
        award = Award(award_data, mock_usa_client)
        
        # Access recipient property multiple times
        recipient1 = award.recipient
        recipient2 = award.recipient
        recipient3 = award.recipient
        
        # Should be the exact same object instance (cached)
        assert recipient1 is recipient2
        assert recipient2 is recipient3
        assert isinstance(recipient1, Recipient)
        assert recipient1.name == "Test Company"
    
    def test_place_of_performance_property_is_cached(self, mock_usa_client):
        """Test that place_of_performance property is only created once."""
        award_data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "place_of_performance": {
                "country_name": "UNITED STATES",
                "state_code": "TX",
                "city_name": "Houston"
            }
        }
        
        award = Award(award_data, mock_usa_client)
        
        # Access property multiple times
        location1 = award.place_of_performance
        location2 = award.place_of_performance
        
        # Should be the same instance
        assert location1 is location2
        assert isinstance(location1, Location)
        assert location1._data["state_code"] == "TX"
    
    def test_recipient_with_lazy_loading_only_calls_api_once(self, mock_usa_client):
        """Test that recipient property uses fallback fields efficiently without API calls."""
        # Award with minimal data that includes fallback recipient fields
        award_data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "Recipient Name": "Test Recipient",  # Has name but no full recipient object
            "recipient_id": "0b441d38-e3c0-de89-ee08-69fc9e6ee58a-C"
        }
        
        award = Award(award_data, mock_usa_client)
        
        # Access recipient multiple times
        recipient1 = award.recipient
        recipient2 = award.recipient
        recipient3 = award.recipient
        
        # Should NOT call API since we have fallback fields (verify no requests made)
        assert mock_usa_client.get_request_count() == 0
        
        # All references should be to the same recipient instance (cached)
        assert recipient1 is recipient2
        assert recipient2 is recipient3
        assert recipient1.name == "Test Recipient"  # Uses the fallback data
        assert recipient1.recipient_id == "0b441d38-e3c0-de89-ee08-69fc9e6ee58a-C"
    
    def test_period_of_performance_property_is_cached(self, mock_usa_client):
        """Test that period_of_performance property is cached."""
        award_data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "period_of_performance": {
                "start_date": "2023-01-01",
                "end_date": "2023-12-31"
            }
        }
        
        award = Award(award_data, mock_usa_client)
        
        # Access property multiple times
        period1 = award.period_of_performance
        period2 = award.period_of_performance
        
        # Should be the same instance
        assert period1 is period2
        assert period1.raw["start_date"] == "2023-01-01"
    
    # TODO: Fix this test - same MockUSASpendingClient endpoint matching issue as transactions test above
    # def test_transactions_property_only_queries_once(self, mock_usa_client):
    #     """Test that transactions property only makes one query."""
    #     # Set up mock transactions response
    #     mock_usa_client.set_response("/v2/transactions/", {
    #         "results": [
    #             {"transaction_id": "1"},
    #             {"transaction_id": "2"}
    #         ],
    #         "page_metadata": {
    #             "total": 2,
    #             "count": 2,
    #             "page": 1,
    #             "has_next": False,
    #             "has_previous": False,
    #             "next": None,
    #             "previous": None
    #         }
    #     })
    #     
    #     award_data = {
    #         "generated_unique_award_id": "CONT_AWD_123"
    #     }
    #     
    #     award = Award(award_data, mock_usa_client)
    #     
    #     # Access transactions multiple times
    #     trans1 = award.transactions
    #     trans2 = award.transactions
    #     trans3 = award.transactions
    #     
    #     # Should only make one API call (cached property)
    #     assert mock_usa_client.get_request_count("/v2/transactions/") == 1
    #     
    #     # Should return the same list instance
    #     assert trans1 is trans2
    #     assert trans2 is trans3
    #     assert len(trans1) == 2
    
    def test_multiple_awards_have_separate_caches(self, mock_usa_client):
        """Test that different Award instances maintain separate caches."""
        award1_data = {
            "generated_unique_award_id": "AWARD1",
            "recipient": {"recipient_name": "Company A"}
        }
        award2_data = {
            "generated_unique_award_id": "AWARD2", 
            "recipient": {"recipient_name": "Company B"}
        }
        
        award1 = Award(award1_data, mock_usa_client)
        award2 = Award(award2_data, mock_usa_client)
        
        # Access recipients
        recipient1 = award1.recipient
        recipient2 = award2.recipient
        
        # Should be different instances with different data
        assert recipient1 is not recipient2
        assert recipient1.name == "Company A"
        assert recipient2.name == "Company B"
        
        # But repeated access to same award should return cached instance
        assert award1.recipient is recipient1
        assert award2.recipient is recipient2
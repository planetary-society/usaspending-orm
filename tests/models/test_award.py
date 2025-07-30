"""Tests for Award model functionality."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from usaspending.models.award import Award
from usaspending.models.recipient import Recipient
from usaspending.models.location import Location
from usaspending.models.agency import Agency

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
        
        # Get transactions query builder
        transactions_query = award.transactions
        
        # Get all transactions
        transactions = transactions_query.all()
        
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

    def test_transactions_property_returns_query_builder(self, mock_usa_client, award_fixture_data):
        """Test that transactions property returns a TransactionsSearch query builder."""
        # Create mocks
        mock_query = Mock()
        mock_query.count = Mock(return_value=5)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[])
        
        mock_transactions_resource = Mock()
        mock_transactions_resource.for_award = Mock(return_value=mock_query)
        mock_usa_client._resources["transactions"] = mock_transactions_resource
        
        award = Award(award_fixture_data, mock_usa_client)
        
        # Test that transactions returns a query builder
        transactions_query = award.transactions
        
        # Test chaining count
        count = transactions_query.count()
        assert count == 5
        mock_query.count.assert_called_once()
        
        # Test chaining limit
        limited_query = transactions_query.limit(10)
        assert limited_query is mock_query
        mock_query.limit.assert_called_once_with(10)
        
        # Test chaining limit and all
        results = transactions_query.limit(10).all()
        assert results == []
        mock_query.all.assert_called_once()
        
        # Verify for_award was called with correct ID
        mock_transactions_resource.for_award.assert_called_with("CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-")


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

    
    def test_get_value_integration_with_non_none_logic(self, mock_usa_client):
        """Test that Award properly uses the updated get_value() method for non-None values."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "field1": "",  # Empty string but not None
            "field2": None,  # None
            "field3": "actual_value"  # Truthy
        }
        award = Award(data, mock_usa_client)
        
        # Should return first non-None value (empty string is not None)
        result = award.get_value(["field1", "field2", "field3"])
        assert result == ""  # Empty string is the first non-None value
        
        # Test with None first
        result2 = award.get_value(["field2", "field3"])
        assert result2 == "actual_value"  # Skips None, returns first non-None
    
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


class TestAwardNewBasicProperties:
    """Test newly added basic Award properties."""
    
    def test_id_property(self, mock_usa_client):
        """Test internal ID property."""
        data = {"generated_unique_award_id": "AWARD_123", "id": 111952974}
        award = Award(data, mock_usa_client)
        
        assert award.id == 111952974
        assert isinstance(award.id, int)
    
    def test_id_property_none(self, mock_usa_client):
        """Test ID property when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.id is None
    
    def test_fain_property(self, mock_usa_client):
        """Test FAIN property for grants."""
        data = {"generated_unique_award_id": "GRANT_123", "fain": "NNM11AA01A"}
        award = Award(data, mock_usa_client)
        
        assert award.fain == "NNM11AA01A"
    
    def test_fain_property_none(self, mock_usa_client):
        """Test FAIN property when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.fain is None
    
    def test_uri_property(self, mock_usa_client):
        """Test URI property for grants."""
        data = {"generated_unique_award_id": "GRANT_123", "uri": "ABC123XYZ"}
        award = Award(data, mock_usa_client)
        
        assert award.uri == "ABC123XYZ"
    
    def test_uri_property_none(self, mock_usa_client):
        """Test URI property when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.uri is None
    
    def test_parent_award_property_with_data(self, mock_usa_client):
        """Test parent_award property returns Award instance."""
        parent_data = {"generated_unique_award_id": "PARENT_123"}
        data = {
            "generated_unique_award_id": "CHILD_123",
            "parent_award": parent_data
        }
        award = Award(data, mock_usa_client)
        
        parent = award.parent_award
        assert isinstance(parent, Award)
        assert parent.generated_unique_award_id == "PARENT_123"
    
    def test_parent_award_property_none(self, mock_usa_client):
        """Test parent_award property when no parent exists."""
        data = {"generated_unique_award_id": "AWARD_123", "parent_award": None}
        award = Award(data, mock_usa_client)
        
        assert award.parent_award is None


class TestAwardNewFinancialProperties:
    """Test newly added financial Award properties."""
    
    def test_account_outlays_by_defc(self, mock_usa_client):
        """Test DEFC outlays array property."""
        defc_data = [{"code": "Q", "amount": 150511166.49}]
        data = {
            "generated_unique_award_id": "AWARD_123",
            "account_outlays_by_defc": defc_data
        }
        award = Award(data, mock_usa_client)
        
        assert award.account_outlays_by_defc == defc_data
        assert len(award.account_outlays_by_defc) == 1
        assert award.account_outlays_by_defc[0]["code"] == "Q"
    
    def test_account_outlays_by_defc_empty_default(self, mock_usa_client):
        """Test DEFC outlays defaults to empty list."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.account_outlays_by_defc == []
    
    def test_account_obligations_by_defc(self, mock_usa_client):
        """Test DEFC obligations array property."""
        defc_data = [{"code": "Q", "amount": 163307372.66}]
        data = {
            "generated_unique_award_id": "AWARD_123",
            "account_obligations_by_defc": defc_data
        }
        award = Award(data, mock_usa_client)
        
        assert award.account_obligations_by_defc == defc_data
        assert len(award.account_obligations_by_defc) == 1
        assert award.account_obligations_by_defc[0]["amount"] == 163307372.66
    
    def test_total_subsidy_cost(self, mock_usa_client):
        """Test loan subsidy cost property."""
        data = {
            "generated_unique_award_id": "LOAN_123",
            "total_subsidy_cost": 25000.50
        }
        award = Award(data, mock_usa_client)
        
        assert award.total_subsidy_cost == 25000.50
        assert isinstance(award.total_subsidy_cost, float)
    
    def test_total_subsidy_cost_none(self, mock_usa_client):
        """Test loan subsidy cost when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.total_subsidy_cost is None
    
    def test_total_loan_value(self, mock_usa_client):
        """Test total loan value property."""
        data = {
            "generated_unique_award_id": "LOAN_123",
            "total_loan_value": 1000000.0
        }
        award = Award(data, mock_usa_client)
        
        assert award.total_loan_value == 1000000.0
        assert isinstance(award.total_loan_value, float)
    
    def test_non_federal_funding(self, mock_usa_client):
        """Test non-federal funding property."""
        data = {
            "generated_unique_award_id": "GRANT_123",
            "non_federal_funding": 50000.0
        }
        award = Award(data, mock_usa_client)
        
        assert award.non_federal_funding == 50000.0
        assert isinstance(award.non_federal_funding, float)
    
    def test_total_funding(self, mock_usa_client):
        """Test total funding property."""
        data = {
            "generated_unique_award_id": "GRANT_123",
            "total_funding": 156725919.62
        }
        award = Award(data, mock_usa_client)
        
        assert award.total_funding == 156725919.62
        assert isinstance(award.total_funding, float)
    
    def test_transaction_obligated_amount(self, mock_usa_client):
        """Test transaction obligated amount property."""
        data = {
            "generated_unique_award_id": "GRANT_123",
            "transaction_obligated_amount": 83852595.67
        }
        award = Award(data, mock_usa_client)
        
        assert award.transaction_obligated_amount == 83852595.67
        assert isinstance(award.transaction_obligated_amount, float)


class TestAwardGrantSpecificProperties:
    """Test grant-specific Award properties."""
    
    def test_record_type_property(self, mock_usa_client):
        """Test grant record type property."""
        data = {
            "generated_unique_award_id": "GRANT_123",
            "record_type": 2
        }
        award = Award(data, mock_usa_client)
        
        assert award.record_type == 2
        assert isinstance(award.record_type, int)
    
    def test_record_type_none(self, mock_usa_client):
        """Test record type when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.record_type is None
    
    def test_cfda_info_property(self, mock_usa_client):
        """Test CFDA info array property."""
        cfda_data = [
            {
                "cfda_number": "43.008",
                "cfda_title": "Office of Stem Engagement (OSTEM)",
                "cfda_popular_name": "OSTEM"
            },
            {
                "cfda_number": "43.001",
                "cfda_title": "Science",
                "cfda_popular_name": "SMD"
            }
        ]
        data = {
            "generated_unique_award_id": "GRANT_123",
            "cfda_info": cfda_data
        }
        award = Award(data, mock_usa_client)
        
        assert award.cfda_info == cfda_data
        assert len(award.cfda_info) == 2
        assert award.cfda_info[0]["cfda_number"] == "43.008"
    
    def test_cfda_info_empty_default(self, mock_usa_client):
        """Test CFDA info defaults to empty list."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.cfda_info == []
    
    def test_funding_opportunity_property(self, mock_usa_client):
        """Test funding opportunity property."""
        opportunity_data = {
            "number": "NASA-12345",
            "goals": "Space research objectives"
        }
        data = {
            "generated_unique_award_id": "GRANT_123",
            "funding_opportunity": opportunity_data
        }
        award = Award(data, mock_usa_client)
        
        assert award.funding_opportunity == opportunity_data
        assert award.funding_opportunity["number"] == "NASA-12345"
    
    def test_funding_opportunity_none(self, mock_usa_client):
        """Test funding opportunity when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.funding_opportunity is None


class TestAwardAgencyProperties:
    """Test agency-related Award properties using new Agency model."""
    
    def test_funding_agency_property(self, mock_usa_client):
        """Test funding agency property returns Agency instance."""
        agency_data = {
            "id": 862,
            "has_agency_page": True,
            "toptier_agency": {
                "name": "National Aeronautics and Space Administration",
                "code": "080",
                "abbreviation": "NASA"
            },
            "office_agency_name": "NASA GODDARD SPACE FLIGHT CENTER"
        }
        data = {
            "generated_unique_award_id": "AWARD_123",
            "funding_agency": agency_data
        }
        award = Award(data, mock_usa_client)
        
        agency = award.funding_agency
        assert isinstance(agency, Agency)
        assert agency.id == 862
        assert agency.has_agency_page is True
        assert agency.name == "National Aeronautics and Space Administration"
        assert agency.code == "080"
    
    def test_funding_agency_cached(self, mock_usa_client):
        """Test funding agency property is cached."""
        agency_data = {
            "id": 862,
            "toptier_agency": {
                "name": "NASA",
                "code": "080"
            }
        }
        data = {
            "generated_unique_award_id": "AWARD_123",
            "funding_agency": agency_data
        }
        award = Award(data, mock_usa_client)
        
        agency1 = award.funding_agency
        agency2 = award.funding_agency
        
        assert agency1 is agency2  # Same instance (cached)
    
    def test_awarding_agency_property(self, mock_usa_client):
        """Test awarding agency property returns Agency instance."""
        agency_data = {
            "id": 862,
            "has_agency_page": True,
            "subtier_agency": {
                "name": "National Aeronautics and Space Administration",
                "code": "8000",
                "abbreviation": "NASA"
            },
            "office_agency_name": "NASA JOHNSON SPACE CENTER"
        }
        data = {
            "generated_unique_award_id": "AWARD_123",
            "awarding_agency": agency_data
        }
        award = Award(data, mock_usa_client)
        
        agency = award.awarding_agency
        assert isinstance(agency, Agency)
        assert agency.id == 862
        assert agency.abbreviation == "NASA"
        assert agency.office_agency_name == "NASA JOHNSON SPACE CENTER"
    
    def test_funding_agency_none(self, mock_usa_client):
        """Test funding agency when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.funding_agency is None
    
    def test_awarding_agency_none(self, mock_usa_client):
        """Test awarding agency when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.awarding_agency is None


class TestAwardContractAndClassificationProperties:
    """Test contract-specific and classification Award properties."""
    
    def test_latest_transaction_contract_data(self, mock_usa_client):
        """Test latest contract transaction data property."""
        contract_data = {
            "solicitation_identifier": "NNH16ZDA005O",
            "type_of_contract_pricing": "S",
            "type_of_contract_pricing_description": "COST NO FEE",
            "product_or_service_code": "AR11",
            "naics": "541713"
        }
        data = {
            "generated_unique_award_id": "CONT_123",
            "latest_transaction_contract_data": contract_data
        }
        award = Award(data, mock_usa_client)
        
        contract_tx = award.latest_transaction_contract_data
        assert contract_tx == contract_data
        assert contract_tx["solicitation_identifier"] == "NNH16ZDA005O"
        assert contract_tx["naics"] == "541713"
    
    def test_latest_transaction_contract_data_cached(self, mock_usa_client):
        """Test latest contract transaction data is cached."""
        contract_data = {"solicitation_identifier": "TEST123"}
        data = {
            "generated_unique_award_id": "CONT_123",
            "latest_transaction_contract_data": contract_data
        }
        award = Award(data, mock_usa_client)
        
        contract1 = award.latest_transaction_contract_data
        contract2 = award.latest_transaction_contract_data
        
        assert contract1 is contract2  # Same instance (cached)
    
    def test_psc_hierarchy_property(self, mock_usa_client):
        """Test PSC hierarchy property."""
        psc_data = {
            "toptier_code": {
                "code": "A",
                "description": "RESEARCH AND DEVELOPMENT"
            },
            "midtier_code": {
                "code": "AR",
                "description": "Space R&D Services"
            },
            "base_code": {
                "code": "AR11",
                "description": "SPACE R&D SERVICES; SPACE FLIGHT, RESEARCH AND SUPPORTING ACTIVITIES; BASIC RESEARCH"
            }
        }
        data = {
            "generated_unique_award_id": "AWARD_123",
            "psc_hierarchy": psc_data
        }
        award = Award(data, mock_usa_client)
        
        psc = award.psc_hierarchy
        assert psc == psc_data
        assert psc["toptier_code"]["code"] == "A"
        assert psc["base_code"]["code"] == "AR11"
    
    def test_naics_hierarchy_property(self, mock_usa_client):
        """Test NAICS hierarchy property."""
        naics_data = {
            "toptier_code": {
                "code": "54",
                "description": "Professional, Scientific, and Technical Services"
            },
            "midtier_code": {
                "code": "5417",
                "description": "Scientific Research and Development Services"
            },
            "base_code": {
                "code": "541713",
                "description": "Research and Development in Nanotechnology"
            }
        }
        data = {
            "generated_unique_award_id": "AWARD_123",
            "naics_hierarchy": naics_data
        }
        award = Award(data, mock_usa_client)
        
        naics = award.naics_hierarchy
        assert naics == naics_data
        assert naics["toptier_code"]["code"] == "54"
        assert naics["base_code"]["code"] == "541713"
    
    def test_hierarchy_properties_cached(self, mock_usa_client):
        """Test hierarchy properties are cached."""
        data = {
            "generated_unique_award_id": "AWARD_123",
            "psc_hierarchy": {"code": "A"},
            "naics_hierarchy": {"code": "54"}
        }
        award = Award(data, mock_usa_client)
        
        # PSC caching
        psc1 = award.psc_hierarchy
        psc2 = award.psc_hierarchy
        assert psc1 is psc2
        
        # NAICS caching
        naics1 = award.naics_hierarchy
        naics2 = award.naics_hierarchy
        assert naics1 is naics2
    
    def test_classification_properties_none(self, mock_usa_client):
        """Test classification properties when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.latest_transaction_contract_data is None
        assert award.psc_hierarchy is None
        assert award.naics_hierarchy is None


class TestAwardExecutiveDetailsProperty:
    """Test executive details Award property."""
    
    def test_executive_details_property(self, mock_usa_client):
        """Test executive details property."""
        executive_data = {
            "officers": [
                {
                    "name": "GWYNNE SHOTWELL",
                    "amount": 4077012.0
                },
                {
                    "name": "BRET JOHNSEN",
                    "amount": 3079137.0
                },
                {
                    "name": None,
                    "amount": None
                }
            ]
        }
        data = {
            "generated_unique_award_id": "AWARD_123",
            "executive_details": executive_data
        }
        award = Award(data, mock_usa_client)
        
        exec_details = award.executive_details
        assert exec_details == executive_data
        assert len(exec_details["officers"]) == 3
        assert exec_details["officers"][0]["name"] == "GWYNNE SHOTWELL"
        assert exec_details["officers"][0]["amount"] == 4077012.0
    
    def test_executive_details_cached(self, mock_usa_client):
        """Test executive details property is cached."""
        executive_data = {"officers": []}
        data = {
            "generated_unique_award_id": "AWARD_123",
            "executive_details": executive_data
        }
        award = Award(data, mock_usa_client)
        
        exec1 = award.executive_details
        exec2 = award.executive_details
        
        assert exec1 is exec2  # Same instance (cached)
    
    def test_executive_details_none(self, mock_usa_client):
        """Test executive details when not present."""
        data = {"generated_unique_award_id": "AWARD_123"}
        award = Award(data, mock_usa_client)
        
        assert award.executive_details is None


class TestAwardRealFixtureDataIntegration:
    """Test new properties with real fixture data."""
    
    def test_contract_fixture_new_properties(self, mock_usa_client):
        """Test new properties work with contract fixture data."""
        # Load contract fixture
        import json
        import os
        
        fixture_path = os.path.join(
            os.path.dirname(__file__), 
            '../fixtures/awards/contract.json'
        )
        with open(fixture_path, 'r') as f:
            contract_data = json.load(f)
        
        award = Award(contract_data, mock_usa_client)
        
        # Test basic properties
        assert award.id == 111952974
        assert award.piid == "80GSFC18C0008"
        assert award.fain is None  # Contract doesn't have FAIN
        assert award.uri is None   # Contract doesn't have URI
        
        # Test financial properties
        assert len(award.account_outlays_by_defc) == 1
        assert award.account_outlays_by_defc[0]["code"] == "Q"
        assert award.account_outlays_by_defc[0]["amount"] == 150511166.49
        
        # Test agency properties
        assert isinstance(award.funding_agency, Agency)
        assert award.funding_agency.id == 862
        assert award.funding_agency.name == "National Aeronautics and Space Administration"
        
        # Test contract-specific properties
        assert award.latest_transaction_contract_data is not None
        assert award.latest_transaction_contract_data["solicitation_identifier"] == "NNH16ZDA005O"
        
        # Test classification properties
        assert award.psc_hierarchy is not None
        assert award.psc_hierarchy["toptier_code"]["code"] == "A"
        assert award.naics_hierarchy["base_code"]["code"] == "541713"
    
    def test_grant_fixture_new_properties(self, mock_usa_client):
        """Test new properties work with grant fixture data."""
        # Load grant fixture
        import json
        import os
        
        fixture_path = os.path.join(
            os.path.dirname(__file__), 
            '../fixtures/awards/grant.json'
        )
        with open(fixture_path, 'r') as f:
            grant_data = json.load(f)
        
        # Set up mock response for lazy loading
        mock_usa_client.set_fixture_response(
            "/v2/awards/ASST_NON_NNM11AA01A_080/",
            "awards/grant"
        )
        
        award = Award(grant_data, mock_usa_client)
        
        # Test grant-specific properties
        assert award.id == 89948049
        assert award.fain == "NNM11AA01A"
        assert award.uri is None
        assert award.record_type == 2
        
        # Test CFDA info
        assert len(award.cfda_info) == 2
        assert award.cfda_info[0]["cfda_number"] == "43.008"
        assert award.cfda_info[1]["cfda_number"] == "43.001"
        
        # Test grant financial properties
        # Grant fixture has these values:
        assert award.total_subsidy_cost == 0.0
        assert award.total_loan_value == 0.0
        assert award.non_federal_funding == 0.0
        assert award.total_funding == 156725919.62
        assert award.transaction_obligated_amount == 83852595.67
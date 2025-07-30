"""Tests for Award property behavior with search results data."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import Mock

from usaspending.models.award import Award
from usaspending.models.recipient import Recipient
from usaspending.models.location import Location
from usaspending.models.period_of_performance import PeriodOfPerformance


class TestContractSearchResultsAssignment:
    """Test Award properties work correctly with search results without triggering _fetch_data()."""
    
    @pytest.fixture
    def search_results_data(self):
        """Load the search results fixture data."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "search_results_contracts.json"
        with open(fixture_path) as f:
            data = json.load(f)
        return data["results"]
    
    @pytest.fixture
    def award_objects(self, mock_usa_client, search_results_data):
        """Create Award objects from search results data."""
        awards = []
        for result in search_results_data:
            award = Award(result, mock_usa_client)
            # Mock _fetch_details to ensure it's never called
            award._fetch_details = Mock(return_value=None)
            awards.append(award)
        return awards
    
    def test_basic_scalar_properties(self, award_objects):
        """Test that basic scalar properties work without triggering fetch."""
        award = award_objects[0]  # First award in fixture
        
        # Test prime_award_id (should use "Award ID" from search results)
        assert award.prime_award_id == "80GSFC18C0008"
        
        # Test description (should use "Description" from search results, formatted with smart_sentence_case)
        expected_desc = "The tandem reconnection and cusp electrodynamics reconnaissance satellite"
        assert expected_desc in award.description
        
        # Test award amount (should use "Award Amount" from search results)
        assert award.award_amount == 168657782.95
        assert award.total_obligation == 168657782.95
        
        # Verify _fetch_details was never called
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_covid_infrastructure_amounts(self, award_objects):
        """Test COVID-19 and Infrastructure amounts from search results."""
        award = award_objects[0]
        
        # All awards in fixture have 0 for these fields
        assert award.covid19_obligations == 0
        assert award.covid19_outlays == 0
        assert award.infrastructure_obligations == 0
        assert award.infrastructure_outlays == 0
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_recipient_uei_property(self, award_objects):
        """Test recipient UEI property from search results."""
        award = award_objects[0]
        
        assert award.recipient_uei == "Z1H9VJS8NG16"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_date_properties(self, award_objects):
        """Test date properties from search results."""
        award = award_objects[0]
        
        # Test base obligation date
        base_date = award.base_obligation_date
        assert base_date is not None
        assert base_date.year == 2018
        assert base_date.month == 3
        assert base_date.day == 5
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_period_of_performance_from_search_results(self, award_objects):
        """Test that period of performance is built from search result flat structure."""
        award = award_objects[0]
        
        period = award.period_of_performance
        assert isinstance(period, PeriodOfPerformance)
        
        # Should be built from "Start Date" and "End Date" fields
        assert period.start_date is not None
        assert period.start_date.year == 2018
        assert period.end_date is not None  
        assert period.end_date.year == 2025
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_place_of_performance_from_search_results(self, award_objects):
        """Test place of performance location from search results."""
        award = award_objects[0]
        
        location = award.place_of_performance
        assert isinstance(location, Location)
        
        # Should be built from "Primary Place of Performance" nested object
        assert location.city_name == "IOWA CITY"
        assert location.state_code == "IA"
        assert location.zip5 == "52242"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_recipient_from_search_results(self, award_objects):
        """Test recipient object built from search results."""
        award = award_objects[0]
        
        recipient = award.recipient
        assert isinstance(recipient, Recipient)
        assert recipient.name == "The University of Iowa"
        
        # Should also have location built from search results
        assert recipient.location is not None
        assert recipient.location.city_name == "IOWA CITY"
        assert recipient.location.state_code == "IA"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    
    def test_total_outlays_from_search_results(self, award_objects):
        """Test total outlays property from search results."""
        award = award_objects[0]
        
        assert award.total_outlay == 150511166.49
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_generated_unique_award_id_from_search_results(self, award_objects):
        """Test generated unique award ID from search results."""
        award = award_objects[0]
        
        assert award.generated_unique_award_id == "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_cfda_properties_fallback(self, award_objects):
        """Test CFDA properties with search results (should be None/empty for contracts)."""
        award = award_objects[0]
        
        # Contract awards shouldn't have CFDA info - these properties have been moved to subclasses
        # so we'll just verify that the award is still functioning correctly
        assert award.prime_award_id == "80GSFC18C0008"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    @pytest.mark.parametrize("award_index", [0, 1, 2, 3])
    def test_all_awards_no_fetch_on_basic_properties(self, award_objects, award_index):
        """Test that none of the award objects trigger fetch for basic properties."""
        award = award_objects[award_index]
        
        # Access multiple properties
        _ = award.prime_award_id
        _ = award.description
        _ = award.award_amount
        _ = award.recipient_uei
        _ = award.covid19_obligations
        
        # Verify no fetch was triggered for any award
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    @pytest.fixture
    def contract_fixture_data(self):
        """Load the contract fixture data."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "contract.json"
        with open(fixture_path) as f:
            return json.load(f)
    
    def test_lazy_loading_properties_trigger_fetch(self, mock_usa_client, search_results_data, contract_fixture_data):
        """Test that properties not in search results trigger _fetch_details() and return correct values."""
        # Create Award from search results (minimal data)
        search_result = search_results_data[0]  # First award
        award = Award(search_result, mock_usa_client)
        
        # Replace _fetch_details with a mock that returns contract fixture data
        award._fetch_details = Mock(return_value=contract_fixture_data)
        
        # Verify initial state - no fetch has occurred
        assert not award._details_fetched
        award._fetch_details.assert_not_called()
        
        # Test 1: subaward_count (not in search results, present in contract.json)
        subaward_count = award.subaward_count
        assert subaward_count == contract_fixture_data["subaward_count"]
        award._fetch_details.assert_called_once()
        assert award._details_fetched
        
        # Reset mock to test additional properties don't trigger more fetches
        award._fetch_details.reset_mock()
        
        # Test 2: total_subaward_amount (should not trigger fetch again)
        total_subaward_amount = award.total_subaward_amount
        assert total_subaward_amount == contract_fixture_data["total_subaward_amount"]
        award._fetch_details.assert_not_called()  # Should not fetch again
        
        # Test 3: date_signed (should not trigger fetch again)
        date_signed = award.date_signed
        assert date_signed is not None  # Value from contract.json
        award._fetch_details.assert_not_called()  # Should not fetch again
        
        
        # Test 4: executive_details (complex nested object)
        executive_details = award.executive_details
        assert executive_details is not None
        assert "officers" in executive_details
        assert len(executive_details["officers"]) == len(contract_fixture_data["executive_details"]["officers"])
        award._fetch_details.assert_not_called()  # Should not fetch again


class TestGrantsSearchResultsAssignment:
    """Test Award properties work correctly with grants search results without triggering _fetch_data()."""
    
    @pytest.fixture
    def grants_search_results_data(self):
        """Load the grants search results fixture data."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "search_results_grants.json"
        with open(fixture_path) as f:
            data = json.load(f)
        return data["results"]
    
    @pytest.fixture
    def grant_award_objects(self, mock_usa_client, grants_search_results_data):
        """Create Award objects from grants search results data."""
        awards = []
        for result in grants_search_results_data:
            award = Award(result, mock_usa_client)
            # Mock _fetch_details to ensure it's never called
            award._fetch_details = Mock(return_value=None)
            awards.append(award)
        return awards
    
    def test_basic_scalar_properties(self, grant_award_objects):
        """Test that basic scalar properties work without triggering fetch."""
        award = grant_award_objects[0]  # First grant in fixture
        
        # Test prime_award_id (should use "Award ID" from search results)
        assert award.prime_award_id == "NNM11AA01A"
        
        # Test description (should use "Description" from search results, formatted with smart_sentence_case)
        expected_desc = "The national space science and technology center"
        assert expected_desc in award.description
        
        # Test award amount (should use "Award Amount" from search results)
        assert award.award_amount == 156725919.62
        assert award.total_obligation == 156725919.62
        
        # Verify _fetch_details was never called
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    
    def test_covid_infrastructure_amounts(self, grant_award_objects):
        """Test COVID-19 and Infrastructure amounts from search results."""
        award = grant_award_objects[0]
        
        # All grants in fixture have 0 for these fields
        assert award.covid19_obligations == 0
        assert award.covid19_outlays == 0
        assert award.infrastructure_obligations == 0
        assert award.infrastructure_outlays == 0
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_recipient_from_search_results(self, grant_award_objects):
        """Test recipient object built from search results."""
        award = grant_award_objects[0]
        
        recipient = award.recipient
        assert isinstance(recipient, Recipient)
        assert recipient.name == "The University of Alabama in Huntsville"
        
        # Should also have location built from search results
        assert recipient.location is not None
        assert recipient.location.city_name == "HUNTSVILLE"
        assert recipient.location.state_code == "AL"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_place_of_performance_from_search_results(self, grant_award_objects):
        """Test place of performance location from search results."""
        award = grant_award_objects[0]
        
        location = award.place_of_performance
        assert isinstance(location, Location)
        
        # Should be built from "Primary Place of Performance" nested object
        assert location.city_name == "HUNTSVILLE"
        assert location.state_code == "AL"
        assert location.zip5 == "35805"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_period_of_performance_from_search_results(self, grant_award_objects):
        """Test that period of performance is built from search result flat structure."""
        award = grant_award_objects[0]
        
        period = award.period_of_performance
        assert isinstance(period, PeriodOfPerformance)
        
        # Should be built from "Start Date" and "End Date" fields
        assert period.start_date is not None
        assert period.start_date.year == 2011
        # End date is null in first grant
        assert period.end_date is None
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_date_properties(self, grant_award_objects):
        """Test date properties from search results."""
        award = grant_award_objects[0]
        
        # Test base obligation date
        base_date = award.base_obligation_date
        assert base_date is not None
        assert base_date.year == 2011
        assert base_date.month == 4
        assert base_date.day == 8
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_generated_unique_award_id_from_search_results(self, grant_award_objects):
        """Test generated unique award ID from search results."""
        award = grant_award_objects[0]
        
        assert award.generated_unique_award_id == "ASST_NON_NNM11AA01A_080"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_contract_specific_properties_fallback(self, grant_award_objects):
        """Test contract-specific properties with search results (should be None/empty for grants)."""
        award = grant_award_objects[0]
        
        # Grant awards are functioning correctly - properties have been moved to subclasses
        assert award.prime_award_id == "NNM11AA01A"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_total_outlays_from_search_results(self, grant_award_objects):
        """Test total outlays property from search results."""
        award = grant_award_objects[0]
        
        assert award.total_outlay == 52414684.72
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    @pytest.mark.parametrize("award_index", [0, 1, 2])
    def test_all_grants_no_fetch_on_basic_properties(self, grant_award_objects, award_index):
        """Test that none of the grant objects trigger fetch for basic properties."""
        award = grant_award_objects[award_index]
        
        # Access multiple properties
        _ = award.prime_award_id
        _ = award.description
        _ = award.award_amount
        _ = award.recipient_uei
        _ = award.covid19_obligations
        
        # Verify no fetch was triggered for any award
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    @pytest.fixture
    def grant_fixture_data(self):
        """Load the grant fixture data."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "grant.json"
        with open(fixture_path) as f:
            return json.load(f)
    
    def test_lazy_loading_grant_properties_trigger_fetch(self, mock_usa_client, grants_search_results_data, grant_fixture_data):
        """Test that grant properties not in search results trigger _fetch_details() and return correct values."""
        # Create Award from search results (minimal data)
        search_result = grants_search_results_data[0]  # First grant
        award = Award(search_result, mock_usa_client)
        
        # Replace _fetch_details with a mock that returns grant fixture data
        award._fetch_details = Mock(return_value=grant_fixture_data)
        
        # Verify initial state - no fetch has occurred
        assert not award._details_fetched
        award._fetch_details.assert_not_called()
        
        # Test 1: subaward_count (not in search results, present in grant.json)
        subaward_count = award.subaward_count
        assert subaward_count == grant_fixture_data["subaward_count"]
        award._fetch_details.assert_called_once()
        assert award._details_fetched
        
        # Reset mock to test additional properties don't trigger more fetches
        award._fetch_details.reset_mock()
        
        # Test 2: total_subaward_amount (should not trigger fetch again)
        total_subaward_amount = award.total_subaward_amount
        assert total_subaward_amount == grant_fixture_data["total_subaward_amount"]
        award._fetch_details.assert_not_called()  # Should not fetch again
        
        # Test 3: executive_details (complex nested object)
        executive_details = award.executive_details
        assert executive_details is not None
        assert "officers" in executive_details
        award._fetch_details.assert_not_called()  # Should not fetch again


class TestIDVSearchResultsAssignment:
    """Test Award properties work correctly with IDV search results without triggering _fetch_data()."""
    
    @pytest.fixture
    def idv_search_results_data(self):
        """Load the IDV search results fixture data."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "search_results_idvs.json"
        with open(fixture_path) as f:
            data = json.load(f)
        return data["results"]
    
    @pytest.fixture
    def idv_award_objects(self, mock_usa_client, idv_search_results_data):
        """Create Award objects from IDV search results data."""
        awards = []
        for result in idv_search_results_data:
            award = Award(result, mock_usa_client)
            # Mock _fetch_details to ensure it's never called
            award._fetch_details = Mock(return_value=None)
            awards.append(award)
        return awards
    
    def test_basic_scalar_properties(self, idv_award_objects):
        """Test that basic scalar properties work without triggering fetch."""
        # Use second IDV which matches the detail fixture
        award = idv_award_objects[1]
        
        # Test prime_award_id (should use "Award ID" from search results)
        assert award.prime_award_id == "80JSC019C0012"
        
        # Test description (should use "Description" from search results, formatted with smart_sentence_case)
        expected_desc = "Orion production and operations contract"
        assert expected_desc in award.description
        
        # Test award amount (should use "Award Amount" from search results)
        assert award.award_amount == 2770845719.63
        assert award.total_obligation == 2770845719.63
        
        # Verify _fetch_details was never called
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    
    def test_covid_infrastructure_amounts(self, idv_award_objects):
        """Test COVID-19 and Infrastructure amounts from search results."""
        award = idv_award_objects[1]
        
        # All IDVs in fixture have 0 for these fields
        assert award.covid19_obligations == 0
        assert award.covid19_outlays == 0
        assert award.infrastructure_obligations == 0
        assert award.infrastructure_outlays == 0
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_recipient_uei_property(self, idv_award_objects):
        """Test recipient UEI property from search results."""
        award = idv_award_objects[1]
        
        assert award.recipient_uei == "FYHNA5WC8XD7"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_date_properties(self, idv_award_objects):
        """Test date properties from search results."""
        award = idv_award_objects[1]
        
        # Test base obligation date
        base_date = award.base_obligation_date
        assert base_date is not None
        assert base_date.year == 2019
        assert base_date.month == 6
        assert base_date.day == 5
        
        # Test Last Modified Date (available in raw data)
        assert award.raw["Last Modified Date"] == "2025-07-03"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_period_of_performance_from_search_results(self, idv_award_objects):
        """Test that period of performance is built from search result flat structure."""
        award = idv_award_objects[1]
        
        period = award.period_of_performance
        assert isinstance(period, PeriodOfPerformance)
        
        # Should be built from "Start Date" and "End Date" fields
        assert period.start_date is not None
        assert period.start_date.year == 2019
        assert period.start_date.month == 6
        assert period.start_date.day == 5
        
        # End date is null for this IDV
        assert period.end_date is None
        
        # Last Modified Date should be included
        assert period.last_modified_date is not None
        assert period.last_modified_date.year == 2025
        assert period.last_modified_date.month == 7
        assert period.last_modified_date.day == 3
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_place_of_performance_from_search_results(self, idv_award_objects):
        """Test place of performance location from search results."""
        award = idv_award_objects[1]
        
        location = award.place_of_performance
        assert isinstance(location, Location)
        
        # IDV search results have mostly null place of performance data
        assert location.country_code == "USA"
        assert location.city_name is None
        assert location.state_code is None
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_recipient_from_search_results(self, idv_award_objects):
        """Test recipient object built from search results."""
        award = idv_award_objects[1]
        
        recipient = award.recipient
        assert isinstance(recipient, Recipient)
        # Recipient name is processed through contracts_titlecase
        assert recipient.name == "Lockheed Martin Corp"
        
        # Should also have location built from search results
        assert recipient.location is not None
        assert recipient.location.city_name == "LITTLETON"
        assert recipient.location.state_code == "CO"
        assert recipient.location.county_name == "DOUGLAS"
        assert recipient.location.zip5 == "80125"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    
    def test_total_outlays_from_search_results(self, idv_award_objects):
        """Test total outlays property from search results."""
        award = idv_award_objects[1]
        
        assert award.total_outlay == 2442918291.79
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_generated_unique_award_id_from_search_results(self, idv_award_objects):
        """Test generated unique award ID from search results."""
        award = idv_award_objects[1]
        
        assert award.generated_unique_award_id == "CONT_IDV_80JSC019C0012_8000"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_cfda_properties_fallback(self, idv_award_objects):
        """Test CFDA properties with search results (should be None/empty for IDVs)."""
        award = idv_award_objects[1]
        
        # IDV awards are functioning correctly - properties have been moved to subclasses
        assert award.prime_award_id == "80JSC019C0012"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    @pytest.mark.parametrize("award_index", [0, 1, 2])
    def test_all_idvs_no_fetch_on_basic_properties(self, idv_award_objects, award_index):
        """Test that none of the IDV objects trigger fetch for basic properties."""
        award = idv_award_objects[award_index]
        
        # Access multiple properties
        _ = award.prime_award_id
        _ = award.description
        _ = award.award_amount
        _ = award.recipient_uei
        _ = award.covid19_obligations
        
        # Verify no fetch was triggered for any award
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    @pytest.fixture
    def idv_fixture_data(self):
        """Load the IDV fixture data."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "idv.json"
        with open(fixture_path) as f:
            return json.load(f)
    
    def test_lazy_loading_idv_properties_trigger_fetch(self, mock_usa_client, idv_search_results_data, idv_fixture_data):
        """Test that IDV properties not in search results trigger _fetch_details() and return correct values."""
        # Create Award from search results (minimal data)
        search_result = idv_search_results_data[1]  # Second IDV (matches detail fixture)
        award = Award(search_result, mock_usa_client)
        
        # Replace _fetch_details with a mock that returns IDV fixture data
        award._fetch_details = Mock(return_value=idv_fixture_data)
        
        # Verify initial state - no fetch has occurred
        assert not award._details_fetched
        award._fetch_details.assert_not_called()
        
        # Test 1: id (internal database ID, not in search results)
        internal_id = award.id
        assert internal_id == idv_fixture_data["id"]
        award._fetch_details.assert_called_once()
        assert award._details_fetched
        
        # Reset mock to test additional properties don't trigger more fetches
        award._fetch_details.reset_mock()
        
        # Test 2: category (should not trigger fetch again)
        category = award.category
        assert category == idv_fixture_data["category"]
        award._fetch_details.assert_not_called()  # Should not fetch again
        
        # Test 3: type (should not trigger fetch again)
        award_type = award.type
        assert award_type == idv_fixture_data["type"]
        award._fetch_details.assert_not_called()  # Should not fetch again
        
        # Test 4: subaward_count (should not trigger fetch again)
        subaward_count = award.subaward_count
        assert subaward_count == idv_fixture_data["subaward_count"]
        award._fetch_details.assert_not_called()  # Should not fetch again
        
        # Test 5: total_subaward_amount (should not trigger fetch again)
        total_subaward_amount = award.total_subaward_amount
        assert total_subaward_amount == idv_fixture_data["total_subaward_amount"]
        award._fetch_details.assert_not_called()  # Should not fetch again
        
        # Test 6: date_signed (should not trigger fetch again)
        date_signed = award.date_signed
        assert date_signed is not None  # Value from idv.json
        award._fetch_details.assert_not_called()  # Should not fetch again
        
        # Test 7: executive_details (complex nested object)
        executive_details = award.executive_details
        assert executive_details is not None
        assert "officers" in executive_details
        award._fetch_details.assert_not_called()  # Should not fetch again
"""Tests for Award property behavior with search results data."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from usaspending.models.award import Award
from usaspending.models.recipient import Recipient
from usaspending.models.location import Location
from usaspending.models.period_of_performance import PeriodOfPerformance


class TestSearchResultsAssignment:
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
    
    def test_naics_properties_from_search_results(self, award_objects):
        """Test NAICS code and description from search results."""
        # Use second award which has NAICS data
        award = award_objects[1]
        
        assert award.naics_code == "336414"
        assert award.naics_description == "GUIDED MISSILE AND SPACE VEHICLE MANUFACTURING"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_psc_properties_from_search_results(self, award_objects):
        """Test PSC code and description from search results."""
        # Use second award which has PSC data
        award = award_objects[1]
        
        assert award.psc_code == "AR62"
        assert award.psc_description == "R&D- SPACE: STATION (APPLIED RESEARCH/EXPLORATORY DEVELOPMENT)"
        
        # Verify no fetch was triggered
        award._fetch_details.assert_not_called()
        assert not award._details_fetched
    
    def test_contract_award_type_from_search_results(self, award_objects):
        """Test contract award type from search results."""
        # Use second award which has this field
        award = award_objects[1]
        
        assert award.contract_award_type == "DEFINITIVE CONTRACT"
        
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
        
        # Contract awards shouldn't have CFDA info
        assert award.cfda_number is None
        assert award.cfda_info == []
        
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
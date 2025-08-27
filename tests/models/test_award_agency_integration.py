"""Tests for Award model integration with restructured Agency."""

from __future__ import annotations

from usaspending.models.award import Award
from usaspending.models.agency import Agency
from usaspending.models.subtier_agency import SubTierAgency


class TestAwardAgencyIntegration:
    """Test Award model integration with Agency structure."""

    def test_awards_query(self, mock_usa_client):
        """Test that AwardsSearch can be initiated from Agency."""
        # This test ensures that the AwardsSearch can be initiated from an Agency instance
        # without raising errors. We won't execute the search, just ensure the chaining works.
        agency_data = {
            "id": 862,
            "has_agency_page": True,
            "office_agency_name": "NASA GODDARD SPACE FLIGHT CENTER",
            "name": "National Aeronautics and Space Administration",
            "code": "080",
            "abbreviation": "NASA",
            "slug": "national-aeronautics-and-space-administration"
        }
        
        agency = Agency(agency_data,mock_usa_client)
        
        # Attempt to create an AwardsSearch filtered by this agency
        awards_search = agency.awards
        
        # Ensure we get an AwardsSearch instance (type check)
        from usaspending.queries.awards_search import AwardsSearch
        assert isinstance(awards_search, AwardsSearch)
        
        filters = awards_search._aggregate_filters()
        assert "agencies" in filters
        assert filters.get("agencies")[0].get("name") == "National Aeronautics and Space Administration"

    def test_award_funding_agency_structure(self, mock_usa_client, contract_fixture_data):
        """Test funding_agency property with Agency structure."""
        award = Award(contract_fixture_data, mock_usa_client)
        
        funding_agency = award.funding_agency
        
        # Should be an Agency instance
        assert isinstance(funding_agency, Agency)
        
        # Should have toptier data
        assert funding_agency.agency_id == 862
        assert funding_agency.has_agency_page is True
        assert funding_agency.name == "National Aeronautics and Space Administration"
        assert funding_agency.code == "080"
        assert funding_agency.abbreviation == "NASA"
        assert funding_agency.slug == "national-aeronautics-and-space-administration"
        assert funding_agency.office_agency_name == "NASA GODDARD SPACE FLIGHT CENTER"
        
        # Test that we can get subtier data via Award's subtier properties
        funding_subtier = award.funding_subtier_agency
        assert isinstance(funding_subtier, SubTierAgency)
        assert funding_subtier.code == "8000"
        assert funding_subtier.name == "National Aeronautics and Space Administration"
        assert funding_subtier.abbreviation == "NASA"

    def test_award_awarding_agency_structure(self, mock_usa_client, contract_fixture_data):
        """Test awarding_agency property with Agency structure."""
        award = Award(contract_fixture_data, mock_usa_client)
        
        awarding_agency = award.awarding_agency
        
        # Should be an Agency instance
        assert isinstance(awarding_agency, Agency)
        
        # Should have toptier data
        assert awarding_agency.agency_id == 862
        assert awarding_agency.name == "National Aeronautics and Space Administration"
        assert awarding_agency.code == "080"
        assert awarding_agency.abbreviation == "NASA"
        
        # Test that we can get subtier data via Award's subtier properties  
        awarding_subtier = award.awarding_subtier_agency
        assert isinstance(awarding_subtier, SubTierAgency)
        assert awarding_subtier.code == "8000"

    def test_award_subtier_agency_properties(self, mock_usa_client, contract_fixture_data):
        """Test subtier agency properties on Award."""
        award = Award(contract_fixture_data, mock_usa_client)
        
        # Test funding subtier agency
        funding_subtier = award.funding_subtier_agency
        assert isinstance(funding_subtier, SubTierAgency)
        assert funding_subtier.code == "8000"
        assert funding_subtier.name == "National Aeronautics and Space Administration"
        assert funding_subtier.abbreviation == "NASA"
        
        # Test awarding subtier agency
        awarding_subtier = award.awarding_subtier_agency
        assert isinstance(awarding_subtier, SubTierAgency)
        assert awarding_subtier.code == "8000"
        assert awarding_subtier.name == "National Aeronautics and Space Administration"
        assert awarding_subtier.abbreviation == "NASA"

    def test_award_agencies_are_separate_instances(self, mock_usa_client, contract_fixture_data):
        """Test that funding and awarding agencies are separate instances."""
        award = Award(contract_fixture_data, mock_usa_client)
        
        funding_agency = award.funding_agency
        awarding_agency = award.awarding_agency
        
        # Should be different instances even if they have the same data
        assert funding_agency is not awarding_agency
        
        # But should have the same data
        assert funding_agency.code == awarding_agency.code
        assert funding_agency.name == awarding_agency.name

    def test_award_agency_consistency(self, mock_usa_client, contract_fixture_data):
        """Test consistency between agency and subtier_agency properties."""
        award = Award(contract_fixture_data, mock_usa_client)
        
        # Test that funding and awarding agencies have consistent data
        funding_agency = award.funding_agency
        awarding_agency = award.awarding_agency
        
        # Should have the same toptier data (since it's the same agency in this fixture)
        assert funding_agency.code == awarding_agency.code
        assert funding_agency.name == awarding_agency.name
        assert funding_agency.abbreviation == awarding_agency.abbreviation
        
        # Test that subtier agencies also have consistent data
        funding_subtier = award.funding_subtier_agency
        awarding_subtier = award.awarding_subtier_agency
        
        # Should have the same subtier data (since it's the same agency in this fixture)
        assert funding_subtier.code == awarding_subtier.code
        assert funding_subtier.name == awarding_subtier.name
        assert funding_subtier.abbreviation == awarding_subtier.abbreviation

    def test_award_with_missing_agency_data(self, mock_usa_client):
        """Test award with missing agency data."""
        # Minimal award data without agency info
        minimal_data = {
            "id": 111952974,
            "generated_unique_award_id": "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-",
            "category": "contract",
            "type": "D"
        }
        
        award = Award(minimal_data, mock_usa_client)
        
        # Should return None for missing agencies
        assert award.funding_agency is None
        assert award.awarding_agency is None
        assert award.funding_subtier_agency is None
        assert award.awarding_subtier_agency is None
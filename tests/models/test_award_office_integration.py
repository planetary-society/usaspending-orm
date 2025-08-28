"""Tests for Award model office integration with SubTierAgency."""

import pytest
from usaspending.models.award import Award
from usaspending.models.subtier_agency import SubTierAgency


class TestAwardOfficeIntegration:
    """Test Award model creates offices from office_agency_name."""

    def test_awarding_subtier_agency_creates_office_from_office_agency_name(self, mock_usa_client):
        """Test that awarding_subtier_agency creates office from office_agency_name."""
        award_data = {
            "id": 111952974,
            "generated_unique_award_id": "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-",
            "awarding_agency": {
                "id": 862,
                "has_agency_page": True,
                "toptier_agency": {
                    "name": "National Aeronautics and Space Administration",
                    "code": "080",
                    "abbreviation": "NASA"
                },
                "subtier_agency": {
                    "name": "National Aeronautics and Space Administration",
                    "code": "8000",
                    "abbreviation": "NASA"
                },
                "office_agency_name": "NASA GODDARD SPACE FLIGHT CENTER"
            }
        }
        
        award = Award(award_data, mock_usa_client)
        subtier_agency = award.awarding_subtier_agency
        
        # Verify subtier agency exists
        assert subtier_agency is not None
        assert isinstance(subtier_agency, SubTierAgency)
        assert subtier_agency.name == "National Aeronautics and Space Administration"
        assert subtier_agency.abbreviation == "NASA"
        
        # Verify office was created from office_agency_name
        offices = subtier_agency.offices
        assert len(offices) == 1
        
        office = offices[0]
        assert isinstance(office, SubTierAgency)
        assert office.name == "NASA Goddard Space Flight Center"  # Should be titlecased

    def test_funding_subtier_agency_creates_office_from_office_agency_name(self, mock_usa_client):
        """Test that funding_subtier_agency creates office from office_agency_name."""
        award_data = {
            "id": 111952974,
            "generated_unique_award_id": "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-",
            "funding_agency": {
                "id": 862,
                "has_agency_page": True,
                "toptier_agency": {
                    "name": "National Aeronautics and Space Administration",
                    "code": "080",
                    "abbreviation": "NASA"
                },
                "subtier_agency": {
                    "name": "National Aeronautics and Space Administration", 
                    "code": "8000",
                    "abbreviation": "NASA"
                },
                "office_agency_name": "NASA MARSHALL SPACE FLIGHT CENTER"
            }
        }
        
        award = Award(award_data, mock_usa_client)
        subtier_agency = award.funding_subtier_agency
        
        # Verify subtier agency exists
        assert subtier_agency is not None
        assert isinstance(subtier_agency, SubTierAgency)
        
        # Verify office was created from office_agency_name
        offices = subtier_agency.offices
        assert len(offices) == 1
        
        office = offices[0]
        assert isinstance(office, SubTierAgency)
        assert office.name == "NASA Marshall Space Flight Center"  # Should be titlecased

    def test_subtier_agency_no_office_when_no_office_agency_name(self, mock_usa_client):
        """Test that no office is created when office_agency_name is not present."""
        award_data = {
            "id": 111952974,
            "generated_unique_award_id": "CONT_AWD_80GSFC18C0008_8000_-NONE-_-NONE-",
            "awarding_agency": {
                "id": 862,
                "subtier_agency": {
                    "name": "National Aeronautics and Space Administration",
                    "code": "8000",
                    "abbreviation": "NASA"
                }
                # No office_agency_name
            }
        }
        
        award = Award(award_data, mock_usa_client)
        subtier_agency = award.awarding_subtier_agency
        
        # Verify subtier agency exists but has no offices
        assert subtier_agency is not None
        assert subtier_agency.offices == []

    def test_subtier_agency_preserves_existing_children(self, mock_usa_client):
        """Test that existing children are preserved when office_agency_name is present."""
        # Create SubTierAgency directly with existing children
        subtier_data = {
            "name": "National Aeronautics and Space Administration",
            "code": "8000",
            "abbreviation": "NASA",
            "office_agency_name": "NASA GODDARD SPACE FLIGHT CENTER",
            "children": [
                {"name": "Existing Office", "code": "EXIST1"}
            ]
        }
        
        subtier_agency = SubTierAgency(subtier_data, mock_usa_client)
        
        # Should preserve existing children, not create new office
        offices = subtier_agency.offices
        assert len(offices) == 1
        assert offices[0].name == "Existing Office"
        assert offices[0].code == "EXIST1"

    def test_subtier_agency_handles_empty_office_agency_name(self, mock_usa_client):
        """Test that empty office_agency_name doesn't create office."""
        subtier_data = {
            "name": "National Aeronautics and Space Administration",
            "code": "8000",
            "abbreviation": "NASA",
            "office_agency_name": ""  # Empty string
        }
        
        subtier_agency = SubTierAgency(subtier_data, mock_usa_client)
        
        # Should not create office for empty string
        assert subtier_agency.offices == []

    def test_subtier_agency_handles_none_office_agency_name(self, mock_usa_client):
        """Test that None office_agency_name doesn't create office."""
        subtier_data = {
            "name": "National Aeronautics and Space Administration", 
            "code": "8000",
            "abbreviation": "NASA",
            "office_agency_name": None
        }
        
        subtier_agency = SubTierAgency(subtier_data, mock_usa_client)
        
        # Should not create office for None
        assert subtier_agency.offices == []

    def test_titlecase_application(self, mock_usa_client):
        """Test that office names are properly titlecased."""
        test_cases = [
            ("NASA GODDARD SPACE FLIGHT CENTER", "NASA Goddard Space Flight Center"),
            ("nasa johnson space center", "NASA Johnson Space Center"), 
            ("NASA JPL", "NASA JPL"),  # JPL should stay uppercase
            ("UNIVERSITY OF CALIFORNIA", "University of California")
        ]
        
        for input_name, expected_name in test_cases:
            subtier_data = {
                "name": "Test Agency",
                "office_agency_name": input_name
            }
            
            subtier_agency = SubTierAgency(subtier_data, mock_usa_client)
            offices = subtier_agency.offices
            
            assert len(offices) == 1
            assert offices[0].name == expected_name
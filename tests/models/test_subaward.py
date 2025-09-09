"""Tests for SubAward model."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from usaspending.models.subaward import SubAward
from usaspending.models.recipient import Recipient
from usaspending.models.location import Location
from usaspending.models.award import Award


class TestSubAwardModel:
    """Test SubAward model functionality."""

    @pytest.fixture
    def subaward_data(self):
        """Load subaward fixture data."""
        fixture_path = (
            Path(__file__).parent.parent
            / "fixtures"
            / "awards"
            / "search_results_subawards.json"
        )
        with open(fixture_path, "r") as f:
            data = json.load(f)
        return data["results"][0]  # First subaward from the fixture

    def test_subaward_initialization(self, subaward_data, mock_usa_client):
        """Test SubAward can be initialized with data."""
        subaward = SubAward(subaward_data, mock_usa_client)
        assert subaward.raw == subaward_data

    def test_subaward_id_properties(self, subaward_data, mock_usa_client):
        """Test SubAward ID-related properties."""
        subaward = SubAward(subaward_data, mock_usa_client)

        assert subaward.id == subaward_data["internal_id"]
        assert subaward.sub_award_id == subaward_data["Sub-Award ID"]
        assert subaward.prime_award_id == subaward_data["Prime Award ID"]
        assert (
            subaward.prime_award_generated_internal_id
            == subaward_data["prime_award_generated_internal_id"]
        )
        assert (
            subaward.prime_award_internal_id == subaward_data["prime_award_internal_id"]
        )
        assert (
            subaward.prime_award_recipient_id
            == subaward_data["prime_award_recipient_id"]
        )

    def test_subaward_type_and_description(self, subaward_data, mock_usa_client):
        """Test SubAward type and description properties."""
        from usaspending.utils.formatter import smart_sentence_case

        subaward = SubAward(subaward_data, mock_usa_client)

        assert subaward.sub_award_type == subaward_data["Sub-Award Type"]
        # Test that smart_sentence_case is applied to the fixture data
        expected_description = smart_sentence_case(
            subaward_data["Sub-Award Description"]
        )
        assert subaward.sub_award_description == expected_description

    def test_subaward_amount_and_date(self, subaward_data, mock_usa_client):
        """Test SubAward amount and date properties."""
        from usaspending.utils.formatter import to_date

        subaward = SubAward(subaward_data, mock_usa_client)

        assert subaward.sub_award_amount == subaward_data["Sub-Award Amount"]
        assert isinstance(subaward.sub_award_date, datetime)
        expected_date = to_date(subaward_data["Sub-Award Date"])
        assert subaward.sub_award_date == expected_date

    def test_subaward_recipient_properties(self, subaward_data, mock_usa_client):
        """Test SubAward recipient-related properties."""
        from usaspending.utils.formatter import contracts_titlecase

        subaward = SubAward(subaward_data, mock_usa_client)

        # Test that contracts_titlecase is applied to fixture data
        expected_sub_awardee = contracts_titlecase(subaward_data["Sub-Awardee Name"])
        expected_prime_recipient = contracts_titlecase(
            subaward_data["Prime Recipient Name"]
        )

        assert subaward.sub_awardee_name == expected_sub_awardee
        assert subaward.prime_recipient_name == expected_prime_recipient
        assert subaward.sub_recipient_uei == subaward_data["Sub-Recipient UEI"]
        assert (
            subaward.prime_award_recipient_uei
            == subaward_data["Prime Award Recipient UEI"]
        )

    def test_subaward_agency_properties(self, subaward_data, mock_usa_client):
        """Test SubAward agency properties."""
        subaward = SubAward(subaward_data, mock_usa_client)

        assert subaward.awarding_agency == subaward_data["Awarding Agency"]
        assert subaward.awarding_sub_agency == subaward_data["Awarding Sub Agency"]

    def test_subaward_naics_psc_from_fixture(self, subaward_data, mock_usa_client):
        """Test NAICS and PSC properties with fixture data structure."""
        subaward = SubAward(subaward_data, mock_usa_client)

        # The fixture has NAICS and PSC as nested dicts, but the model returns the raw value
        assert subaward.naics == subaward_data["NAICS"]
        assert subaward.psc == subaward_data["PSC"]

        # Since they're dicts in the fixture, verify the structure
        if isinstance(subaward_data["NAICS"], dict):
            assert isinstance(subaward.naics, dict)
            assert "code" in subaward.naics
            assert "description" in subaward.naics

        if isinstance(subaward_data["PSC"], dict):
            assert isinstance(subaward.psc, dict)
            assert "code" in subaward.psc
            assert "description" in subaward.psc

    def test_subaward_contract_specific_fields(self, mock_usa_client):
        """Test contract-specific subaward fields with string values."""
        contract_subaward_data = {
            "internal_id": "Z123",
            "Sub-Award ID": "Z123",
            "Sub-Award Type": "sub-contract",
            "NAICS": "541511",  # String value for this test
            "PSC": "D399",  # String value for this test
            "Sub-Awardee Name": "TECH COMPANY",
            "Sub-Award Amount": 100000.0,
        }

        subaward = SubAward(contract_subaward_data, mock_usa_client)
        assert subaward.naics == contract_subaward_data["NAICS"]
        assert subaward.psc == contract_subaward_data["PSC"]
        assert subaward.assistance_listing is None  # Not present in contract subawards

    def test_subaward_grant_specific_fields(self, mock_usa_client):
        """Test grant-specific subaward fields."""
        grant_subaward_data = {
            "internal_id": "G123",
            "Sub-Award ID": "G123",
            "Sub-Award Type": "sub-grant",
            "Assistance Listing": "10.500",
            "Sub-Awardee Name": "UNIVERSITY",
            "Sub-Award Amount": 50000.0,
        }

        subaward = SubAward(grant_subaward_data, mock_usa_client)
        assert subaward.assistance_listing == grant_subaward_data["Assistance Listing"]
        assert subaward.naics is None  # Not present in grant subawards
        assert subaward.psc is None  # Not present in grant subawards

    def test_subaward_place_of_performance(self, subaward_data, mock_usa_client):
        """Test SubAward place_of_performance property."""
        from titlecase import titlecase
        from usaspending.utils.formatter import contracts_titlecase

        subaward = SubAward(subaward_data, mock_usa_client)

        pop = subaward.place_of_performance
        assert isinstance(pop, Location)

        # Verify the Location object has the correct data from fixture
        pop_data = subaward_data["Sub-Award Primary Place of Performance"]
        assert pop.raw == pop_data
        # Location applies titlecase formatting to city_name
        assert pop.city_name == titlecase(pop_data["city_name"])
        assert pop.state_code == pop_data["state_code"]
        # Location applies contracts_titlecase to country_name
        assert pop.country_name == contracts_titlecase(pop_data["country_name"])

    def test_subaward_recipient(self, subaward_data, mock_usa_client):
        """Test SubAward recipient property."""
        subaward = SubAward(subaward_data, mock_usa_client)

        recipient = subaward.recipient
        assert isinstance(recipient, Recipient)

        # Verify the Recipient object has the correct mapped data
        assert recipient.raw["recipient_name"] == subaward_data["Sub-Awardee Name"]
        assert (
            recipient.raw["recipient_unique_id"]
            == subaward_data["sub_award_recipient_id"]
        )
        assert recipient.raw["recipient_uei"] == subaward_data["Sub-Recipient UEI"]

        # Check that location is attached if available
        if isinstance(subaward_data.get("Sub-Recipient Location"), dict):
            assert recipient.location is not None
            assert isinstance(recipient.location, Location)
            assert recipient.location.raw == subaward_data["Sub-Recipient Location"]

    def test_subaward_parent_award(self, subaward_data, mock_usa_client):
        """Test SubAward parent_award property."""
        subaward = SubAward(subaward_data, mock_usa_client)

        if subaward_data.get("prime_award_generated_internal_id"):
            parent = subaward.parent_award
            assert isinstance(parent, Award)
            assert (
                parent.raw["generated_unique_award_id"]
                == subaward_data["prime_award_generated_internal_id"]
            )
        else:
            assert subaward.parent_award is None

    def test_subaward_helper_properties(self, subaward_data, mock_usa_client):
        """Test SubAward helper properties (name, amount, description, award_date)."""
        from usaspending.utils.formatter import (
            contracts_titlecase,
            smart_sentence_case,
            to_date,
        )

        subaward = SubAward(subaward_data, mock_usa_client)

        # Test helper properties map to main properties correctly
        expected_name = (
            contracts_titlecase(subaward_data["Sub-Awardee Name"])
            if subaward_data.get("Sub-Awardee Name")
            else None
        )
        assert subaward.name == expected_name
        assert subaward.name == subaward.sub_awardee_name

        assert subaward.amount == subaward_data["Sub-Award Amount"]
        assert subaward.amount == subaward.sub_award_amount

        expected_desc = (
            smart_sentence_case(subaward_data["Sub-Award Description"])
            if subaward_data.get("Sub-Award Description")
            else None
        )
        assert subaward.description == expected_desc
        assert subaward.description == subaward.sub_award_description

        expected_date = (
            to_date(subaward_data["Sub-Award Date"])
            if subaward_data.get("Sub-Award Date")
            else None
        )
        assert subaward.award_date == expected_date
        assert subaward.award_date == subaward.sub_award_date

    def test_subaward_repr(self, subaward_data, mock_usa_client):
        """Test SubAward string representation."""
        from usaspending.utils.formatter import contracts_titlecase

        subaward = SubAward(subaward_data, mock_usa_client)

        repr_str = repr(subaward)
        assert "<SubAward" in repr_str
        assert subaward_data["Sub-Award ID"] in repr_str
        expected_name = contracts_titlecase(subaward_data["Sub-Awardee Name"])
        assert expected_name in repr_str
        # Format the amount as it would appear in repr
        amount_str = f"{subaward_data['Sub-Award Amount']:,.2f}"
        assert amount_str in repr_str

    def test_subaward_field_constants(self):
        """Test SubAward field constants."""
        # Contract fields should include contract-specific fields
        assert "NAICS" in SubAward.CONTRACT_SUBAWARD_FIELDS
        assert "PSC" in SubAward.CONTRACT_SUBAWARD_FIELDS
        assert "Assistance Listing" not in SubAward.CONTRACT_SUBAWARD_FIELDS

        # Grant fields should include grant-specific fields
        assert "Assistance Listing" in SubAward.GRANT_SUBAWARD_FIELDS
        assert "NAICS" not in SubAward.GRANT_SUBAWARD_FIELDS
        assert "PSC" not in SubAward.GRANT_SUBAWARD_FIELDS

        # Both should have common fields
        common_fields = [
            "Sub-Award ID",
            "Sub-Award Amount",
            "Sub-Awardee Name",
            "Prime Award ID",
        ]
        for field in common_fields:
            assert field in SubAward.CONTRACT_SUBAWARD_FIELDS
            assert field in SubAward.GRANT_SUBAWARD_FIELDS

    def test_subaward_with_missing_fields(self, mock_usa_client):
        """Test SubAward handles missing fields gracefully."""
        minimal_data = {"internal_id": "TEST123"}

        subaward = SubAward(minimal_data, mock_usa_client)

        # All properties should return None for missing fields
        assert subaward.id == minimal_data["internal_id"]
        assert subaward.sub_award_id is None
        assert subaward.sub_award_type is None
        assert subaward.sub_awardee_name is None
        assert subaward.sub_award_date is None
        assert subaward.sub_award_amount is None
        assert subaward.awarding_agency is None
        assert subaward.prime_award_id is None
        assert subaward.naics is None
        assert subaward.psc is None
        assert subaward.assistance_listing is None

        # Helper properties should also return None
        assert subaward.name is None
        assert subaward.amount is None
        assert subaward.description is None
        assert subaward.award_date is None

        # Cached properties should handle missing data
        assert subaward.place_of_performance is None
        assert subaward.parent_award is None

        # Recipient should still be created but with minimal data
        recipient = subaward.recipient
        assert isinstance(recipient, Recipient)
        assert recipient.raw["recipient_name"] is None
        assert recipient.raw["recipient_unique_id"] is None
        assert recipient.raw["recipient_uei"] is None

        # repr should handle None values
        repr_str = repr(subaward)
        assert "<SubAward ? ? $0.00>" == repr_str

    def test_subaward_with_null_internal_id(self, mock_usa_client):
        """Test SubAward handles null internal_id from fixture."""
        # The fixture has null internal_id values
        data_with_null_id = {
            "internal_id": None,
            "Sub-Award ID": "TEST456",
            "Sub-Awardee Name": "Test Company",
            "Sub-Award Amount": 25000.0,
        }

        subaward = SubAward(data_with_null_id, mock_usa_client)

        assert subaward.id is None
        assert subaward.sub_award_id == data_with_null_id["Sub-Award ID"]

        # repr should use sub_award_id when internal_id is None
        from usaspending.utils.formatter import contracts_titlecase

        expected_name = contracts_titlecase(data_with_null_id["Sub-Awardee Name"])
        repr_str = repr(subaward)
        assert data_with_null_id["Sub-Award ID"] in repr_str
        assert expected_name in repr_str

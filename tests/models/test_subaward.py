"""Tests for SubAward model."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from usaspending.models.subaward import SubAward


class TestSubAwardModel:
    """Test SubAward model functionality."""

    @pytest.fixture
    def subaward_data(self):
        """Load subaward fixture data."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "awards" / "search_results_subawards.json"
        with open(fixture_path, "r") as f:
            data = json.load(f)
        return data["results"][0]  # First subaward from the fixture

    def test_subaward_initialization(self, subaward_data):
        """Test SubAward can be initialized with data."""
        subaward = SubAward(subaward_data)
        assert subaward.raw == subaward_data

    def test_subaward_id_properties(self, subaward_data):
        """Test SubAward ID-related properties."""
        subaward = SubAward(subaward_data)
        
        assert subaward.id == subaward_data["internal_id"]
        assert subaward.sub_award_id == subaward_data["Sub-Award ID"]
        assert subaward.prime_award_id == subaward_data["Prime Award ID"]
        assert subaward.prime_award_generated_internal_id == subaward_data["prime_award_generated_internal_id"]
        assert subaward.prime_award_internal_id == subaward_data["prime_award_internal_id"]
        assert subaward.prime_award_recipient_id == subaward_data["prime_award_recipient_id"]

    def test_subaward_type_and_description(self, subaward_data):
        """Test SubAward type and description properties."""
        from usaspending.utils.formatter import smart_sentence_case
        
        subaward = SubAward(subaward_data)
        
        assert subaward.sub_award_type == subaward_data["Sub-Award Type"]
        # Test that smart_sentence_case is applied
        expected_description = smart_sentence_case(subaward_data["Sub-Award Description"])
        assert subaward.sub_award_description == expected_description

    def test_subaward_amount_and_date(self, subaward_data):
        """Test SubAward amount and date properties."""
        from usaspending.utils.formatter import to_date
        
        subaward = SubAward(subaward_data)
        
        assert subaward.sub_award_amount == subaward_data["Sub-Award Amount"]
        assert isinstance(subaward.sub_award_date, datetime)
        expected_date = to_date(subaward_data["Sub-Award Date"])
        assert subaward.sub_award_date == expected_date

    def test_subaward_recipient_properties(self, subaward_data):
        """Test SubAward recipient-related properties."""
        from usaspending.utils.formatter import contracts_titlecase
        
        subaward = SubAward(subaward_data)
        
        # Test that contracts_titlecase is applied
        expected_sub_awardee = contracts_titlecase(subaward_data["Sub-Awardee Name"])
        expected_prime_recipient = contracts_titlecase(subaward_data["Prime Recipient Name"])
        
        assert subaward.sub_awardee_name == expected_sub_awardee
        assert subaward.prime_recipient_name == expected_prime_recipient
        assert subaward.sub_recipient_uei == subaward_data["Sub-Recipient UEI"]
        assert subaward.prime_award_recipient_uei == subaward_data["Prime Award Recipient UEI"]

    def test_subaward_agency_properties(self, subaward_data):
        """Test SubAward agency properties."""
        subaward = SubAward(subaward_data)
        
        assert subaward.awarding_agency == subaward_data["Awarding Agency"]
        assert subaward.awarding_sub_agency == subaward_data["Awarding Sub Agency"]

    def test_subaward_contract_specific_fields(self):
        """Test contract-specific subaward fields."""
        contract_subaward_data = {
            "internal_id": "Z123",
            "Sub-Award ID": "Z123",
            "Sub-Award Type": "sub-contract",
            "NAICS": "541511",
            "PSC": "D399",
            "Sub-Awardee Name": "TECH COMPANY",
            "Sub-Award Amount": 100000.0
        }
        
        subaward = SubAward(contract_subaward_data)
        assert subaward.naics == "541511"
        assert subaward.psc == "D399"
        assert subaward.assistance_listing is None  # Not present in contract subawards

    def test_subaward_grant_specific_fields(self):
        """Test grant-specific subaward fields."""
        grant_subaward_data = {
            "internal_id": "G123",
            "Sub-Award ID": "G123",
            "Sub-Award Type": "sub-grant",
            "Assistance Listing": "10.500",
            "Sub-Awardee Name": "UNIVERSITY",
            "Sub-Award Amount": 50000.0
        }
        
        subaward = SubAward(grant_subaward_data)
        assert subaward.assistance_listing == "10.500"
        assert subaward.naics is None  # Not present in grant subawards
        assert subaward.psc is None  # Not present in grant subawards

    def test_subaward_repr(self, subaward_data):
        """Test SubAward string representation."""
        from usaspending.utils.formatter import contracts_titlecase
        
        subaward = SubAward(subaward_data)
        
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
        common_fields = ["Sub-Award ID", "Sub-Award Amount", "Sub-Awardee Name", "Prime Award ID"]
        for field in common_fields:
            assert field in SubAward.CONTRACT_SUBAWARD_FIELDS
            assert field in SubAward.GRANT_SUBAWARD_FIELDS

    def test_subaward_with_missing_fields(self):
        """Test SubAward handles missing fields gracefully."""
        minimal_data = {
            "internal_id": "TEST123"
        }
        
        subaward = SubAward(minimal_data)
        
        # All properties should return None for missing fields
        assert subaward.id == "TEST123"
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
        
        # repr should handle None values
        repr_str = repr(subaward)
        assert "<SubAward ? ? $0.00>" == repr_str
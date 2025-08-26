"""
This file contains the concrete test classes for each Award model type.
Each class inherits from the shared AwardTestingMixin and provides the
specific model and fixture information. It also contains tests that are
unique to that award type.
"""

from __future__ import annotations

import pytest

from .test_award_common import AwardTestingMixin
from usaspending.models import Contract, Grant, IDV, Loan
from tests.mocks.mock_client import MockUSASpendingClient


class TestContract(AwardTestingMixin):
    """Test the Contract model."""
    AWARD_MODEL = Contract
    FIXTURE_NAME = "contract_fixture_data"
    FIXTURE_PATH = "awards/contract"

    def test_type_fields_defined(self):
        """Test that Contract has the correct TYPE_FIELDS defined."""
        expected_fields = [
            "piid", "base_exercised_options", "base_and_all_options",
            "contract_award_type", "naics_code", "naics_description",
            "psc_code", "psc_description"
        ]
        for field in expected_fields:
            assert field in Contract.TYPE_FIELDS

    def test_specific_properties_from_fixture(self, mock_usa_client, fixture_data):
        """Test contract-specific properties using fixture data."""
        contract = self.AWARD_MODEL(fixture_data, mock_usa_client)

        assert contract.piid == fixture_data["piid"]
        assert contract.base_exercised_options == fixture_data["base_exercised_options"]
        assert contract.base_and_all_options == fixture_data["base_and_all_options"]
        assert contract.contract_award_type == fixture_data["type_description"]
        assert contract.naics_code == fixture_data["latest_transaction_contract_data"]["naics"]
        assert contract.naics_description.lower() == fixture_data["latest_transaction_contract_data"]["naics_description"].lower()
        assert contract.psc_code == fixture_data["psc_hierarchy"]["base_code"]["code"]
        assert contract.psc_description == fixture_data["psc_hierarchy"]["base_code"]["description"]

    def test_cached_properties_from_fixture(self, mock_usa_client, fixture_data):
        """Test contract-specific cached properties using fixture data."""
        contract = self.AWARD_MODEL(fixture_data, mock_usa_client)

        # Test latest_transaction_contract_data
        latest_txn = contract.latest_transaction_contract_data
        assert latest_txn is not None
        assert latest_txn == fixture_data["latest_transaction_contract_data"]
        assert contract.latest_transaction_contract_data is latest_txn  # Check caching

        # Test psc_hierarchy
        psc_hierarchy = contract.psc_hierarchy
        assert psc_hierarchy is not None
        assert psc_hierarchy == fixture_data["psc_hierarchy"]
        assert contract.psc_hierarchy is psc_hierarchy  # Check caching

        # Test naics_hierarchy
        naics_hierarchy = contract.naics_hierarchy
        assert naics_hierarchy is not None
        assert naics_hierarchy == fixture_data["naics_hierarchy"]
        assert contract.naics_hierarchy is naics_hierarchy  # Check caching

    def test_subawards_applies_correct_filters(self, mock_usa_client, fixture_data):
        """Test that contract.subawards automatically applies contract award type filters."""
        contract = self.AWARD_MODEL(fixture_data, mock_usa_client)
        mock_usa_client.set_paginated_response(MockUSASpendingClient.Endpoints.AWARD_SEARCH, [])

        # Iterate to trigger the API call
        list(contract.subawards)

        # Verify the API call included the correct award type codes for contracts
        last_request = mock_usa_client.get_last_request(MockUSASpendingClient.Endpoints.AWARD_SEARCH)
        payload = last_request["json"]
        assert set(payload["filters"]["award_type_codes"]) == {"A", "B", "C", "D"}


class TestGrant(AwardTestingMixin):
    """Test the Grant model."""
    AWARD_MODEL = Grant
    FIXTURE_NAME = "grant_fixture_data"
    FIXTURE_PATH = "awards/grant"

    def test_type_fields_defined(self):
        """Test that Grant has the correct TYPE_FIELDS defined."""
        expected_fields = [
            "fain", "uri", "cfda_info", "cfda_number", "funding_opportunity"
        ]
        for field in expected_fields:
            assert field in Grant.TYPE_FIELDS

    def test_specific_properties_from_fixture(self, mock_usa_client, fixture_data):
        """Test grant-specific properties using fixture data."""
        grant = self.AWARD_MODEL(fixture_data, mock_usa_client)

        assert grant.fain == fixture_data["fain"]
        assert grant.uri == fixture_data["uri"]
        assert grant.record_type == fixture_data["record_type"]
        if "primary_cfda_info" in fixture_data and fixture_data["primary_cfda_info"]:
            assert grant.cfda_number == fixture_data["primary_cfda_info"]["cfda_number"]
        else:
            assert grant.cfda_number == fixture_data["cfda_info"][0]["cfda_number"]
        assert grant.sai_number == fixture_data.get("sai_number")
        assert grant.non_federal_funding == fixture_data["non_federal_funding"]
        assert grant.total_funding == fixture_data["total_funding"]
        assert grant.transaction_obligated_amount == fixture_data["transaction_obligated_amount"]

    def test_cached_and_complex_properties_from_fixture(self, mock_usa_client, fixture_data):
        """Test grant-specific cached and complex properties using fixture data."""
        grant = self.AWARD_MODEL(fixture_data, mock_usa_client)

        # Test cfda_info
        cfda_info = grant.cfda_info
        assert cfda_info is not None
        assert cfda_info == fixture_data["cfda_info"]
        assert grant.cfda_info is cfda_info  # Check caching

        # Test primary_cfda_info
        primary_cfda = grant.primary_cfda_info
        if "primary_cfda_info" in fixture_data and fixture_data["primary_cfda_info"]:
            assert primary_cfda is not None
            assert primary_cfda == fixture_data["primary_cfda_info"]
            assert grant.primary_cfda_info is primary_cfda  # Check caching
        else:
            assert primary_cfda is None

        # Test funding_opportunity
        funding_opp = grant.funding_opportunity
        assert funding_opp is not None
        assert funding_opp == fixture_data["funding_opportunity"]
        assert grant.funding_opportunity is funding_opp  # Check caching

    def test_subawards_applies_correct_filters(self, mock_usa_client, fixture_data):
        """Test that grant.subawards automatically applies assistance award type filters."""
        grant = self.AWARD_MODEL(fixture_data, mock_usa_client)
        mock_usa_client.set_paginated_response(MockUSASpendingClient.Endpoints.AWARD_SEARCH, [])

        # Iterate to trigger the API call
        list(grant.subawards)

        # Verify the API call included the correct award type codes for grants
        last_request = mock_usa_client.get_last_request(MockUSASpendingClient.Endpoints.AWARD_SEARCH)
        payload = last_request["json"]
        assert set(payload["filters"]["award_type_codes"]) == {"02", "03", "04", "05"}


class TestIDV(AwardTestingMixin):
    """Test the IDV model."""
    AWARD_MODEL = IDV
    FIXTURE_NAME = "idv_fixture_data"
    FIXTURE_PATH = "awards/idv"

    def test_type_fields_defined(self):
        """Test that IDV has the correct TYPE_FIELDS defined."""
        expected_fields = [
            "piid", "contract_award_type", "naics_code", "psc_code"
        ]
        for field in expected_fields:
            assert field in IDV.TYPE_FIELDS

    def test_specific_properties_from_fixture(self, mock_usa_client, fixture_data):
        """Test IDV-specific properties using fixture data."""
        idv = self.AWARD_MODEL(fixture_data, mock_usa_client)

        assert idv.piid == fixture_data["piid"]
        assert idv.base_and_all_options == fixture_data["base_and_all_options"]
        assert idv.contract_award_type == fixture_data["type_description"]
        assert idv.naics_code == fixture_data["naics_hierarchy"]["base_code"]["code"]
        assert idv.psc_code == fixture_data["psc_hierarchy"]["base_code"]["code"]

    def test_place_of_performance_is_none(self, mock_usa_client, fixture_data):
        """Test that place_of_performance is None for IDVs as per fixture."""
        idv = self.AWARD_MODEL(fixture_data, mock_usa_client)
        # IDVs typically don't have a place of performance; the fixture has null values
        assert idv.place_of_performance is None


class TestLoan(AwardTestingMixin):
    """Test the Loan model."""
    AWARD_MODEL = Loan
    FIXTURE_NAME = "loan_fixture_data"
    FIXTURE_PATH = "awards/loan"

    def test_type_fields_defined(self):
        """Test that Loan has the correct TYPE_FIELDS defined."""
        expected_fields = [
            "fain", "uri", "total_subsidy_cost", "total_loan_value", "cfda_number"
        ]
        for field in expected_fields:
            assert field in Loan.TYPE_FIELDS

    def test_specific_properties_from_fixture(self, mock_usa_client, fixture_data):
        """Test loan-specific properties using fixture data."""
        loan = self.AWARD_MODEL(fixture_data, mock_usa_client)

        assert loan.fain == fixture_data["fain"]
        # The 'uri' is None in the fixture, so we test that
        assert loan.uri is None
        assert loan.total_subsidy_cost == fixture_data["total_subsidy_cost"]
        assert loan.total_loan_value == fixture_data["total_loan_value"]
        if loan.cfda_number:
            assert loan.cfda_number == fixture_data["cfda_info"][0]["cfda_number"]
        else:
            assert loan.cfda_number is None

    def test_cfda_info_from_fixture(self, mock_usa_client, fixture_data):
        """Test loan-specific CFDA properties using fixture data."""
        loan = self.AWARD_MODEL(fixture_data, mock_usa_client)

        # Test cfda_info
        cfda_info = loan.cfda_info
        assert cfda_info is not None
        assert cfda_info == fixture_data["cfda_info"]
        assert loan.cfda_info is cfda_info  # Check caching

        # Test primary_cfda_info
        primary_cfda = loan.primary_cfda_info
        if "primary_cfda_info" in fixture_data and fixture_data["primary_cfda_info"]:
            assert primary_cfda is not None
            assert primary_cfda == fixture_data["primary_cfda_info"]
            assert loan.primary_cfda_info is primary_cfda  # Check caching
        else:
            assert primary_cfda is None

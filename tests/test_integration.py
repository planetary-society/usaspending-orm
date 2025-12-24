"""Integration tests that hit the real USASpending.gov API.

These tests are skipped by default. Run with:
    pytest -m integration

Run with verbose output:
    pytest -m integration -v
"""

from __future__ import annotations

import pytest

from usaspending import USASpendingClient

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    """Real USASpending client for integration tests."""
    return USASpendingClient()


class TestAwardResourceIntegration:
    """Integration tests for AwardResource."""

    def test_search_contracts(self, client):
        """Test award search for contracts."""
        results = list(
            client.awards.search().contracts().fiscal_year(2024).limit(3)
        )
        assert len(results) > 0
        assert results[0].generated_unique_award_id is not None

    def test_search_grants(self, client):
        """Test award search for grants."""
        results = list(
            client.awards.search().grants().fiscal_year(2024).limit(3)
        )
        assert len(results) > 0
        assert results[0].generated_unique_award_id is not None

    def test_find_by_generated_id(self, client):
        """Test finding award by generated ID."""
        # First get an award ID from search
        search_results = list(client.awards.search().contracts().limit(1))
        assert len(search_results) > 0, "Need at least one contract to test"

        award_id = search_results[0].generated_unique_award_id
        award = client.awards.find_by_generated_id(award_id)

        assert award is not None
        assert award.generated_unique_award_id == award_id
        assert award.recipient is not None


class TestAwardFiltersIntegration:
    """Integration tests for award search filters."""

    def test_program_activity_filter(self, client):
        """Test program_activity filter with integer codes."""
        # Search for awards with a specific program activity code
        # Using common program activity codes that should have results
        results = list(
            client.awards.search()
            .grants()
            .fiscal_year(2024)
            .program_activity(1)
            .limit(3)
        )
        # May or may not have results depending on data availability
        assert isinstance(results, list)

    def test_program_activities_filter(self, client):
        """Test program_activities filter with name/code dicts."""
        # Search for awards using program activities filter
        results = list(
            client.awards.search()
            .grants()
            .fiscal_year(2024)
            .program_activities({"name": "Research"})
            .limit(3)
        )
        # May or may not have results depending on data availability
        assert isinstance(results, list)


class TestRecipientsResourceIntegration:
    """Integration tests for RecipientsResource."""

    def test_search_recipients(self, client):
        """Test recipient search."""
        results = list(client.recipients.search().keyword("university").limit(3))
        assert len(results) > 0
        assert results[0].name is not None

    def test_find_by_recipient_id(self, client):
        """Test finding recipient by ID with year parameter."""
        # Get a recipient ID from spending search
        spending = list(
            client.spending.search().by_recipient().fiscal_year(2024).limit(5)
        )
        recipient_id = None
        for s in spending:
            if s.recipient_id:
                recipient_id = s.recipient_id
                break

        if recipient_id:
            recipient = client.recipients.find_by_recipient_id(
                recipient_id, year="latest"
            )
            assert recipient is not None
            assert recipient.name is not None


class TestAgencyResourceIntegration:
    """Integration tests for AgencyResource."""

    def test_find_by_toptier_code(self, client):
        """Test finding agency by toptier code."""
        # NASA toptier code
        agency = client.agencies.find_by_toptier_code("080")
        assert agency is not None
        assert "NASA" in agency.name or "Aeronautics" in agency.name

    def test_find_funding_agencies(self, client):
        """Test funding agency search."""
        results = list(
            client.agencies.find_all_funding_agencies_by_name("Defense").limit(3)
        )
        assert len(results) > 0


class TestSpendingResourceIntegration:
    """Integration tests for SpendingResource."""

    def test_spending_by_recipient(self, client):
        """Test spending by recipient."""
        results = list(
            client.spending.search().by_recipient().fiscal_year(2024).limit(3)
        )
        assert len(results) > 0
        assert results[0].name is not None
        assert results[0].amount is not None

    def test_spending_by_district(self, client):
        """Test spending by congressional district."""
        results = list(
            client.spending.search().by_district().fiscal_year(2024).limit(3)
        )
        assert len(results) > 0

    def test_spending_by_state(self, client):
        """Test spending by state."""
        results = list(
            client.spending.search().by_state().fiscal_year(2024).limit(3)
        )
        assert len(results) > 0


class TestAwardTransactionsIntegration:
    """Integration tests for award.transactions property."""

    def test_transactions_via_award_object(self, client):
        """Test getting transactions through award object."""
        # Get a contract award
        awards = list(
            client.awards.search().contracts().fiscal_year(2024).limit(1)
        )
        assert len(awards) > 0, "Need at least one contract to test"

        award = awards[0]
        # Access transactions through the award object
        transactions = list(award.transactions.limit(3))

        # Award should have at least one transaction
        assert isinstance(transactions, list)
        if len(transactions) > 0:
            assert transactions[0].action_date is not None


class TestAwardFundingIntegration:
    """Integration tests for award.funding property."""

    def test_funding_via_award_object(self, client):
        """Test getting funding history through award object."""
        # Get a contract award
        awards = list(
            client.awards.search().contracts().fiscal_year(2024).limit(1)
        )
        assert len(awards) > 0, "Need at least one contract to test"

        award = awards[0]
        # Access funding through the award object
        funding = list(award.funding.limit(3))

        # Award may or may not have funding records
        assert isinstance(funding, list)


class TestAwardSubawardsIntegration:
    """Integration tests for award.subawards property."""

    def test_subawards_via_contract_object(self, client):
        """Test getting subawards through contract award object."""
        # Get contract awards
        awards = list(
            client.awards.search().contracts().fiscal_year(2024).limit(5)
        )
        assert len(awards) > 0, "Need at least one contract to test"

        # Find an award with subawards
        for award in awards:
            if award.subaward_count and award.subaward_count > 0:
                # Access subawards through the award object
                subawards = list(award.subawards.limit(3))
                assert isinstance(subawards, list)
                assert len(subawards) > 0
                return

        # If no awards with subawards found, still verify the property works
        award = awards[0]
        subawards = list(award.subawards.limit(1))
        assert isinstance(subawards, list)

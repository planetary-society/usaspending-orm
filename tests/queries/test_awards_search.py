"""Tests for the AwardsSearch query builder."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from usaspending.exceptions import ValidationError, APIError
from usaspending.models import Award
from usaspending.queries.awards_search import AwardsSearch
from usaspending.models.award_types import (
    CONTRACT_CODES,
    IDV_CODES,
    LOAN_CODES,
    GRANT_CODES,
)


@pytest.fixture
def awards_search(mock_usa_client):
    """Create an AwardsSearch instance with a mock client."""
    return AwardsSearch(mock_usa_client)


class TestAwardsSearchInitialization:
    """Test initialization and basic properties of AwardsSearch."""

    def test_initialization(self, mock_usa_client):
        """Test that AwardsSearch initializes correctly."""
        search = AwardsSearch(mock_usa_client)
        assert search._client == mock_usa_client
        assert search._filter_objects == []
        assert search._page_size == 100
        assert search._max_pages is None

    def test_endpoint(self, awards_search):
        """Test that the correct endpoint is returned."""
        assert awards_search._endpoint == "/search/spending_by_award/"

    def test_clone_immutability(self, awards_search):
        """Test that _clone creates a new instance with copied attributes."""
        # Add some filters first
        awards_search._filter_objects.append(Mock())
        awards_search._page_size = 50

        # Clone the search
        cloned = awards_search._clone()

        # Verify it's a different instance
        assert cloned is not awards_search
        assert cloned._filter_objects is not awards_search._filter_objects

        # But has same content
        assert len(cloned._filter_objects) == len(awards_search._filter_objects)
        assert cloned._page_size == awards_search._page_size



class TestPayloadBuilding:
    """Test payload construction and validation."""

    def test_build_payload_basic(self, awards_search):
        """Test basic payload building with required filters."""
        search = awards_search.award_type_codes("A", "B")

        payload = search._build_payload(page=1)

        assert payload["filters"] == {"award_type_codes": ["A", "B"]}
        # Verify base fields are included
        assert "Award ID" in payload["fields"]
        assert "Recipient Name" in payload["fields"]
        assert "Awarding Agency" in payload["fields"]
        assert len(payload["fields"]) > 20  # Should have many base fields
        assert payload["limit"] == 100
        assert payload["page"] == 1

    def test_build_payload_multiple_filters(self, awards_search):
        """Test payload building with multiple filters."""
        search = (
            awards_search.award_type_codes("A")
            .keywords("test")
            .fiscal_year(2024)
        )

        payload = search._build_payload(page=2)

        assert "award_type_codes" in payload["filters"]
        assert "keywords" in payload["filters"]
        assert "time_period" in payload["filters"]
        assert payload["page"] == 2

    def test_build_payload_missing_required_filter(self, awards_search):
        """Test that missing award_type_codes raises ValidationError."""
        search = awards_search.keywords("test")

        with pytest.raises(ValidationError) as exc_info:
            search._build_payload(page=1)

        assert "award_type_codes" in str(exc_info.value)

    def test_build_payload_aggregates_agency_filters(self, awards_search):
        """Test that multiple agency filters are aggregated into a single list."""
        search = (
            awards_search.award_type_codes("A")
            .agency("NASA", "awarding")
            .agency("DOD", "funding")
        )

        payload = search._build_payload(page=1)

        assert len(payload["filters"]["agencies"]) == 2
        assert payload["filters"]["agencies"][0]["name"] == "NASA"
        assert payload["filters"]["agencies"][1]["name"] == "DOD"

    def test_build_payload_custom_page_size(self, awards_search):
        """Test payload with custom page size."""
        search = awards_search.award_type_codes("A").page_size(50)

        payload = search._build_payload(page=1)

        assert payload["limit"] == 50

    def test_contract_fields_included(self, awards_search):
        """Test that contract-specific fields are included for contract types."""
        search = awards_search.award_type_codes("A", "B")

        fields = search._get_fields()

        # Check contract-specific fields are present
        assert "Start Date" in fields
        assert "End Date" in fields
        assert "Award Amount" in fields
        assert "Total Outlays" in fields
        assert "Contract Award Type" in fields
        assert "NAICS" in fields
        assert "PSC" in fields

    def test_idv_fields_included(self, awards_search):
        """Test that IDV-specific fields are included for IDV types."""
        search = awards_search.award_type_codes("IDV_A", "IDV_B")

        fields = search._get_fields()

        # Check IDV-specific fields are present
        assert "Start Date" in fields
        assert "Award Amount" in fields
        assert "Total Outlays" in fields
        assert "Contract Award Type" in fields
        assert "Last Date to Order" in fields
        assert "NAICS" in fields
        assert "PSC" in fields
        # Should not have End Date (IDV-specific difference)

    def test_loan_fields_included(self, awards_search):
        """Test that loan-specific fields are included for loan types."""
        search = awards_search.award_type_codes("07", "08")

        fields = search._get_fields()

        # Check loan-specific fields are present
        assert "Issued Date" in fields
        assert "Loan Value" in fields
        assert "Subsidy Cost" in fields
        assert "SAI Number" in fields
        assert "CFDA Number" in fields
        assert "Assistance Listings" in fields
        assert "primary_assistance_listing" in fields

    def test_assistance_fields_included(self, awards_search):
        """Test that assistance-specific fields are included for assistance types."""
        search = awards_search.award_type_codes("02", "03", "04")

        fields = search._get_fields()

        # Check assistance-specific fields are present
        assert "Start Date" in fields
        assert "End Date" in fields
        assert "Award Amount" in fields
        assert "Total Outlays" in fields
        assert "Award Type" in fields
        assert "SAI Number" in fields
        assert "CFDA Number" in fields
        assert "Assistance Listings" in fields
        assert "primary_assistance_listing" in fields

    def test_mixed_award_types_fields_now_forbidden(self, awards_search):
        """Test that mixing award types from different categories is now forbidden."""
        # This should raise a ValidationError due to our new validation
        with pytest.raises(
            ValidationError, match="Cannot mix different award type categories"
        ):
            awards_search.award_type_codes("A", "07")  # Contract + Loan

    def test_no_award_types_base_fields_only(self, awards_search):
        """Test that only base fields are returned when no award types specified."""
        # Don't set award types, but access fields directly
        fields = awards_search._get_fields()

        # Should only have base fields
        assert "Award ID" in fields
        assert "Recipient Name" in fields
        assert "Awarding Agency" in fields

        # Should not have type-specific fields
        assert "Contract Award Type" not in fields
        assert "Loan Value" not in fields
        assert "Last Date to Order" not in fields


class TestOrderByFunctionality:
    """Test order_by method and payload generation."""

    def test_order_by_included_in_payload(self, awards_search):
        """Test that sort and order parameters are included in payload when order_by is used."""
        search = awards_search.award_type_codes("A", "B").order_by(
            "Award Amount", "desc"
        )

        payload = search._build_payload(page=1)

        assert "sort" in payload
        assert payload["sort"] == "Award Amount"
        assert "order" in payload
        assert payload["order"] == "desc"

    def test_order_by_ascending(self, awards_search):
        """Test order_by with ascending direction."""
        search = awards_search.award_type_codes("A").order_by("Award ID", "asc")

        payload = search._build_payload(page=1)

        assert payload["sort"] == "Award ID"
        assert payload["order"] == "asc"

    def test_order_by_default_direction(self, awards_search):
        """Test order_by defaults to descending when direction not specified."""
        search = awards_search.award_type_codes("A").order_by("Recipient Name")

        payload = search._build_payload(page=1)

        assert payload["sort"] == "Recipient Name"
        assert payload["order"] == "desc"

    def test_no_order_by_no_sort_params(self, awards_search):
        """Test that sort and order are not in payload when order_by is not used."""
        search = awards_search.award_type_codes("A", "B")

        payload = search._build_payload(page=1)

        assert "sort" not in payload
        assert "order" not in payload

    def test_order_by_invalid_field_raises_error(self, awards_search):
        """Test that order_by raises ValidationError for invalid field names."""
        search = awards_search.award_type_codes("A")

        with pytest.raises(ValidationError) as exc_info:
            search.order_by("invalid_field_name")

        error_msg = str(exc_info.value)
        assert "Invalid sort field 'invalid_field_name'" in error_msg
        assert "contracts" in error_msg  # Should mention the category
        assert "Valid fields are:" in error_msg

    def test_order_by_validates_contract_fields(self, awards_search):
        """Test that contract-specific fields are accepted for contract awards."""
        # These should all work without raising
        search = awards_search.contracts()

        # Test base fields
        search.order_by("Award ID")
        search.order_by("Recipient Name")
        search.order_by("Award Amount")

        # Test contract-specific fields
        search.order_by("Contract Award Type")
        search.order_by("NAICS")
        search.order_by("PSC")
        search.order_by("Start Date")
        search.order_by("End Date")

    def test_order_by_validates_grant_fields(self, awards_search):
        """Test that grant-specific fields are accepted for grant awards."""
        search = awards_search.grants()

        # Test base fields
        search.order_by("Award ID")
        search.order_by("Recipient Name")

        # Test grant-specific fields
        search.order_by("Award Type")
        search.order_by("SAI Number")
        search.order_by("CFDA Number")
        search.order_by("Assistance Listings")

    def test_order_by_validates_loan_fields(self, awards_search):
        """Test that loan-specific fields are accepted for loan awards."""
        search = awards_search.loans()

        # Test loan-specific fields
        search.order_by("Issued Date")
        search.order_by("Loan Value")
        search.order_by("Subsidy Cost")
        search.order_by("SAI Number")

    def test_order_by_validates_idv_fields(self, awards_search):
        """Test that IDV-specific fields are accepted for IDV awards."""
        search = awards_search.idvs()

        # Test IDV-specific fields
        search.order_by("Last Date to Order")
        search.order_by("Contract Award Type")
        search.order_by("NAICS")
        search.order_by("PSC")

    def test_order_by_rejects_wrong_category_field(self, awards_search):
        """Test that fields from wrong category are rejected."""
        # Contract search should reject loan-specific field
        search = awards_search.contracts()

        with pytest.raises(ValidationError) as exc_info:
            search.order_by("Loan Value")

        error_msg = str(exc_info.value)
        assert "Invalid sort field 'Loan Value' for contracts" in error_msg

    def test_order_by_case_sensitive(self, awards_search):
        """Test that field names must match exactly (case-sensitive)."""
        search = awards_search.contracts()

        # Should fail with lowercase
        with pytest.raises(ValidationError):
            search.order_by("award amount")

        # Should fail with different capitalization
        with pytest.raises(ValidationError):
            search.order_by("award Amount")

        # Should succeed with exact match
        search.order_by("Award Amount")  # Should not raise

    def test_order_by_immutability(self, awards_search):
        """Test that order_by returns a new instance."""
        search1 = awards_search.contracts()
        search2 = search1.order_by("Award Amount", "asc")

        # Should be different instances
        assert search1 is not search2

        # Original should not have ordering
        payload1 = search1._build_payload(1)
        assert "sort" not in payload1

        # New instance should have ordering
        payload2 = search2._build_payload(1)
        assert payload2["sort"] == "Award Amount"
        assert payload2["order"] == "asc"

    def test_order_by_chaining(self, awards_search):
        """Test that order_by can be chained with other methods."""
        search = (
            awards_search.agency("NASA")
            .contracts()
            .fiscal_year(2024)
            .order_by("Award Amount", "desc")
            .limit(10)
        )

        payload = search._build_payload(1)

        # Should have all the filters and ordering
        assert "agencies" in payload["filters"]
        assert "award_type_codes" in payload["filters"]
        assert "time_period" in payload["filters"]
        assert payload["sort"] == "Award Amount"
        assert payload["order"] == "desc"
        assert payload["limit"] == 10

    def test_order_by_without_award_type_validates_fields(self, awards_search):
        """Test order_by validation when no award type is set."""
        # The award_type_codes filter is required by the API, but we can test
        # that validation happens before payload generation

        # Should fail with type-specific field when no award type is set
        with pytest.raises(ValidationError) as exc_info:
            awards_search.order_by("Contract Award Type")

        error_msg = str(exc_info.value)
        assert "Invalid sort field 'Contract Award Type'" in error_msg
        assert "all award types (no type filter applied)" in error_msg

        # Base field should pass validation (even though payload would still fail without award types)
        search = awards_search.order_by("Award ID")
        # The order_by itself should succeed, even if _build_payload would fail
        assert search._order_by == "Award ID"
        assert search._order_direction == "desc"


class TestAwardTypeHelperMethods:
    """Test the helper methods for award types."""

    def test_contracts_helper(self, awards_search):
        """Test the contracts() helper method."""
        search = awards_search.contracts()

        award_types = search._get_award_type_codes()
        assert award_types == CONTRACT_CODES

        # Should include contract-specific fields
        fields = search._get_fields()
        assert "Contract Award Type" in fields
        assert "NAICS" in fields
        assert "PSC" in fields

    def test_idvs_helper(self, awards_search):
        """Test the idvs() helper method."""
        search = awards_search.idvs()

        award_types = search._get_award_type_codes()
        assert award_types == IDV_CODES

        # Should include IDV-specific fields
        fields = search._get_fields()
        assert "Last Date to Order" in fields
        assert "Contract Award Type" in fields
        assert "NAICS" in fields

    def test_loans_helper(self, awards_search):
        """Test the loans() helper method."""
        search = awards_search.loans()

        award_types = search._get_award_type_codes()
        assert award_types == LOAN_CODES

        # Should include loan-specific fields
        fields = search._get_fields()
        assert "Loan Value" in fields
        assert "Subsidy Cost" in fields
        assert "CFDA Number" in fields

    def test_grants_helper(self, awards_search):
        """Test the grants() helper method."""
        search = awards_search.grants()

        award_types = search._get_award_type_codes()
        assert award_types == GRANT_CODES

        # Should include grant-specific fields
        fields = search._get_fields()
        assert "Award Type" in fields
        assert "CFDA Number" in fields
        assert "Assistance Listings" in fields


class TestAwardTypeValidation:
    """Test validation of award type categories."""

    def test_single_category_contracts_allowed(self, awards_search):
        """Test that multiple codes within contract category are allowed."""
        search = awards_search.award_type_codes("A", "B", "C")

        # Should not raise an error
        award_types = search._get_award_type_codes()
        assert award_types == {"A", "B", "C"}

    def test_single_category_grants_allowed(self, awards_search):
        """Test that multiple codes within grant category are allowed."""
        search = awards_search.award_type_codes("02", "03", "04")

        # Should not raise an error
        award_types = search._get_award_type_codes()
        assert award_types == {"02", "03", "04"}

    def test_mixing_contracts_and_loans_forbidden(self, awards_search):
        """Test that mixing contracts and loans raises ValidationError."""
        with pytest.raises(
            ValidationError, match="Cannot mix different award type categories"
        ):
            awards_search.award_type_codes("A", "07")

    def test_mixing_idvs_and_grants_forbidden(self, awards_search):
        """Test that mixing IDVs and grants raises ValidationError."""
        with pytest.raises(
            ValidationError, match="Cannot mix different award type categories"
        ):
            awards_search.award_type_codes("IDV_A", "02")

    def test_chaining_different_categories_forbidden(self, awards_search):
        """Test that chaining different categories is forbidden."""
        # First set contracts
        search = awards_search.contracts()

        # Then try to add loans - should fail
        with pytest.raises(
            ValidationError, match="Cannot mix different award type categories"
        ):
            search.award_type_codes("07")

    def test_helper_methods_cannot_be_mixed(self, awards_search):
        """Test that helper methods cannot be chained with different types."""
        # First use contracts
        search = awards_search.contracts()

        # Then try to add loans via helper - should fail
        with pytest.raises(
            ValidationError, match="Cannot mix different award type categories"
        ):
            search.loans()

    def test_adding_same_category_allowed(self, awards_search):
        """Test that adding more codes from the same category is allowed."""
        # Start with some contracts
        search = awards_search.award_type_codes("A", "B")

        # Add more contracts - should be allowed (validation should pass)
        search2 = search.award_type_codes("C", "D")

        # The search should have two separate award_type_codes filters
        # When building the payload, they should be combined
        payload = search2._build_payload(page=1)
        combined_types = set(payload["filters"]["award_type_codes"])

        # Should have all four types combined
        assert combined_types == {"A", "B", "C", "D"}

    def test_contracts_helper_after_contracts_allowed(self, awards_search):
        """Test that using contracts() after setting contract codes is allowed."""
        # Start with some contract codes
        search = awards_search.award_type_codes("A", "B")

        # Use contracts() helper - should work since same category
        search2 = search.contracts()

        # Should combine the original codes with all contract codes
        payload = search2._build_payload(page=1)
        combined_types = set(payload["filters"]["award_type_codes"])

        # Should have all contract codes (original A,B plus all from CONTRACT_CODES)
        assert combined_types == CONTRACT_CODES


class TestTransformResult:
    """Test result transformation."""

    def test_transform_result(self, mock_usa_client):
        """Test that _transform_result creates Award instances."""
        # Set up a single award
        award_data = {"Award ID": "123", "Recipient Name": "Test Corp"}
        mock_usa_client.mock_award_search([award_data])

        # Get the award through the query
        search = mock_usa_client.awards.search().award_type_codes("A")
        award = search.first()

        assert isinstance(award, Award)
        assert award._data["Award ID"] == "123"
        assert award._data["Recipient Name"] == "Test Corp"


class TestPaginationAndIteration:
    """Test pagination functionality."""

    def test_iteration_single_page(self, mock_usa_client):
        """Test iteration with a single page of results."""
        # Set up mock response
        awards = [
            {"Award ID": "1", "Recipient Name": "Corp 1"},
            {"Award ID": "2", "Recipient Name": "Corp 2"},
        ]
        mock_usa_client.mock_award_search(awards)

        search = mock_usa_client.awards.search().award_type_codes("A")
        results = list(search)

        assert len(results) == 2
        assert all(isinstance(r, Award) for r in results)
        assert mock_usa_client.get_request_count("/search/spending_by_award/") == 1

    def test_iteration_multiple_pages(self, mock_usa_client):
        """Test iteration with multiple pages."""
        # Create 250 awards that will be automatically paginated
        awards = [{"Award ID": f"{i}"} for i in range(1, 251)]
        mock_usa_client.mock_award_search(awards, page_size=100)

        search = mock_usa_client.awards.search().award_type_codes("A")
        results = list(search)

        assert len(results) == 250
        assert mock_usa_client.get_request_count("/search/spending_by_award/") == 3

    def test_iteration_with_max_pages(self, mock_usa_client):
        """Test iteration respects max_pages limit."""
        # Create 300 awards but limit to 2 pages
        awards = [{"Award ID": f"{i}"} for i in range(300)]
        mock_usa_client.mock_award_search(awards, page_size=100)

        search = mock_usa_client.awards.search().award_type_codes("A").max_pages(2)
        results = list(search)

        assert len(results) == 200
        assert mock_usa_client.get_request_count("/search/spending_by_award/") == 2

    def test_first_method(self, mock_usa_client):
        """Test the first() method returns only the first result."""
        awards = [
            {"Award ID": "1", "Recipient Name": "Corp 1"},
            {"Award ID": "2", "Recipient Name": "Corp 2"},
        ]
        mock_usa_client.mock_award_search(awards)

        search = mock_usa_client.awards.search().award_type_codes("A")
        result = search.first()

        assert isinstance(result, Award)
        assert result._data["Award ID"] == "1"
        # Verify the request was made correctly
        assert mock_usa_client.get_request_count("/search/spending_by_award/") == 1

    def test_first_method_no_results(self, mock_usa_client):
        """Test first() returns None when no results."""
        mock_usa_client.mock_award_search([])  # Empty results

        search = mock_usa_client.awards.search().award_type_codes("A")
        result = search.first()

        assert result is None

    def test_all_method(self, mock_usa_client):
        """Test the all() method returns all results as a list."""
        awards = [{"Award ID": "1"}, {"Award ID": "2"}, {"Award ID": "3"}]
        mock_usa_client.mock_award_search(awards)

        search = mock_usa_client.awards.search().award_type_codes("A")
        results = search.all()

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, Award) for r in results)

    def test_count_method_contracts(self, mock_usa_client):
        """Test the count() method for contract awards."""
        # Mock response with structured count format
        mock_usa_client.mock_award_count(
            contracts=3287, direct_payments=0, grants=7821, idvs=105, loans=0, other=0
        )

        search = mock_usa_client.awards.search().award_type_codes("A")
        count = search.count()

        assert count == 3287

        # Verify the correct endpoint was called
        mock_usa_client.assert_called_with(
            endpoint="/search/spending_by_award_count/", method="POST"
        )

    def test_count_method_grants(self, mock_usa_client):
        """Test the count() method for grant awards."""
        mock_usa_client.mock_award_count(
            contracts=3287, direct_payments=0, grants=7821, idvs=105, loans=0, other=0
        )

        search = mock_usa_client.awards.search().award_type_codes("02", "03")
        count = search.count()

        assert count == 7821

    def test_count_method_idvs(self, mock_usa_client):
        """Test the count() method for IDV awards."""
        mock_usa_client.mock_award_count(
            contracts=3287, direct_payments=0, grants=7821, idvs=105, loans=0, other=0
        )

        search = mock_usa_client.awards.search().award_type_codes("IDV_A")
        count = search.count()

        assert count == 105

    def test_count_method_loans(self, mock_usa_client):
        """Test the count() method for loan awards."""
        mock_usa_client.mock_award_count(
            contracts=3287, direct_payments=0, grants=7821, idvs=105, loans=42, other=0
        )

        search = mock_usa_client.awards.search().award_type_codes("07")
        count = search.count()

        assert count == 42

    def test_count_method_direct_payments(self, mock_usa_client):
        """Test the count() method for direct payment awards."""
        mock_usa_client.mock_award_count(
            contracts=3287, direct_payments=123, grants=7821, idvs=105, loans=0, other=0
        )

        search = mock_usa_client.awards.search().award_type_codes("06")
        count = search.count()

        assert count == 123

    def test_count_method_other(self, mock_usa_client):
        """Test the count() method for other assistance awards."""
        mock_usa_client.mock_award_count(
            contracts=3287, direct_payments=0, grants=7821, idvs=105, loans=0, other=89
        )

        search = mock_usa_client.awards.search().award_type_codes("09")
        count = search.count()

        assert count == 89

    def test_count_method_convenience_methods(self, mock_usa_client):
        """Test the count() method with convenience methods."""
        mock_usa_client.mock_award_count(
            contracts=3287,
            direct_payments=123,
            grants=7821,
            idvs=105,
            loans=42,
            other=89,
        )

        # Test each convenience method
        assert mock_usa_client.awards.search().contracts().count() == 3287
        assert mock_usa_client.awards.search().grants().count() == 7821
        assert mock_usa_client.awards.search().idvs().count() == 105
        assert mock_usa_client.awards.search().loans().count() == 42
        assert mock_usa_client.awards.search().direct_payments().count() == 123
        assert mock_usa_client.awards.search().other_assistance().count() == 89

        # Verify 6 calls were made (one for each convenience method)
        assert (
            mock_usa_client.get_request_count("/search/spending_by_award_count/") == 6
        )

    def test_count_method_missing_category(self, mock_usa_client):
        """Test count() method when category is missing from response."""
        # Only provide some categories
        mock_usa_client.mock_award_count(
            contracts=3287,
            grants=7821,
            # Missing other categories
        )

        search = mock_usa_client.awards.search().award_type_codes("07")  # loans
        count = search.count()

        # Should return 0 when category is missing
        assert count == 0

    def test_count_method_requires_award_types(self, mock_usa_client):
        """Test that count() method requires award types to be set."""
        # Try to call count() without setting award types
        with pytest.raises(ValidationError) as exc_info:
            mock_usa_client.awards.search().count()

        assert "award_type_codes" in str(exc_info.value)
        assert "required" in str(exc_info.value)


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_api_error_propagation(self, mock_usa_client):
        """Test that API errors are propagated correctly."""
        # Set up error response for count endpoint (called by __len__)
        mock_usa_client.set_error_response(
            "/search/spending_by_award_count/", error_code=400, detail="Bad request"
        )

        search = mock_usa_client.awards.search().award_type_codes("A")

        with pytest.raises(APIError):
            list(search)

    def test_empty_award_types_filter(self, awards_search):
        """Test that empty award types raises appropriate error."""
        # This should work but payload building should fail
        search = awards_search.award_type_codes()  # No types provided

        # Filter should still be added, just empty
        assert len(search._filter_objects) == 1

        # But building payload should fail
        with pytest.raises(ValidationError):
            search._build_payload(1)


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    def test_nasa_contracts_fy2024(self, mock_usa_client):
        """Test a realistic query for NASA contracts in FY2024."""
        awards = [
            {
                "Award ID": "80NSSC24CA001",
                "Recipient Name": "SpaceX",
                "Award Amount": 2500000000,
                "Awarding Agency": "NASA",
            }
        ]
        mock_usa_client.mock_award_search(awards)

        search = (
            mock_usa_client.awards.search()
            .award_type_codes("A", "B", "C", "D")
            .agency("NASA", "awarding")
            .fiscal_year(2024)
            .keywords("space", "launch")
        )

        results = list(search)

        # Verify the request was made with correct filters
        last_request = mock_usa_client.get_last_request("/search/spending_by_award/")
        payload = last_request["json"]

        assert "award_type_codes" in payload["filters"]
        assert "agencies" in payload["filters"]
        assert "time_period" in payload["filters"]
        assert "keywords" in payload["filters"]

        assert len(results) == 1
        assert isinstance(results[0], Award)

    def test_small_business_grants(self, mock_usa_client):
        """Test query for small business grants with location filters."""
        mock_usa_client.mock_award_search([])  # Empty results

        ca_location = {"country_code": "USA", "state_code": "CA"}

        search = (
            mock_usa_client.awards.search()
            .award_type_codes("02", "03", "04", "05")  # Grant types
            .recipient_type_names("small_business")
            .recipient_locations(ca_location)
            .award_amounts({"lower_bound": 100000, "upper_bound": 500000})
        )

        _ = search.all()

        # Verify filters were applied using request tracking
        last_request = mock_usa_client.get_last_request("/search/spending_by_award/")
        payload = last_request["json"]
        assert payload["filters"]["recipient_type_names"] == ["small_business"]
        assert payload["filters"]["recipient_locations"] == [
            {"country": "USA", "state": "CA"}
        ]
        assert len(payload["filters"]["award_amounts"]) == 1

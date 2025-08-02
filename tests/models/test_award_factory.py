"""Tests for Award factory functionality."""

from __future__ import annotations

import pytest

from usaspending.models.award_factory import create_award
from usaspending.models.award import Award
from usaspending.models.contract import Contract
from usaspending.models.grant import Grant
from usaspending.models.idv import IDV
from usaspending.models.loan import Loan
from usaspending.exceptions import ValidationError


class TestAwardFactory:
    """Test award factory creates correct subclasses."""

    def test_factory_with_string_id(self, mock_usa_client):
        """Test factory with string ID returns base Award."""
        award_id = "CONT_AWD_123"
        award = create_award(award_id, mock_usa_client)

        assert isinstance(award, Award)
        assert award._data["generated_unique_award_id"] == "CONT_AWD_123"
        # Should be base Award class for string IDs
        assert award.__class__ == Award

    def test_factory_with_invalid_type_raises_error(self, mock_usa_client):
        """Test factory with invalid type raises ValidationError."""
        with pytest.raises(ValidationError):
            create_award(123, mock_usa_client)


class TestFactoryWithCategoryField:
    """Test factory using category field for type detection."""

    def test_factory_creates_contract_from_category(self, mock_usa_client):
        """Test factory creates Contract from category field."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "category": "contract",
            "type": "D",
        }
        award = create_award(data, mock_usa_client)

        assert isinstance(award, Contract)
        assert isinstance(award, Award)  # Should inherit from Award
        assert award.category == "contract"

    def test_factory_creates_grant_from_category(self, mock_usa_client):
        """Test factory creates Grant from category field."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "category": "grant",
            "type": "05",
        }
        award = create_award(data, mock_usa_client)

        assert isinstance(award, Grant)
        assert isinstance(award, Award)
        assert award.category == "grant"

    def test_factory_creates_idv_from_category(self, mock_usa_client):
        """Test factory creates IDV from category field."""
        data = {
            "generated_unique_award_id": "CONT_IDV_123",
            "category": "idv",
            "type": "IDV_B_B",
        }
        award = create_award(data, mock_usa_client)

        assert isinstance(award, IDV)
        assert isinstance(award, Award)
        assert award.category == "idv"

    def test_factory_creates_loan_from_category(self, mock_usa_client):
        """Test factory creates Loan from category field."""
        data = {
            "generated_unique_award_id": "ASST_NON_LOAN_123",
            "category": "loan",
            "type": "07",
        }
        award = create_award(data, mock_usa_client)

        assert isinstance(award, Loan)
        assert isinstance(award, Award)
        assert award.category == "loan"


class TestFactoryWithTypeCodeFallback:
    """Test factory using type code when category is not available."""

    def test_factory_creates_contract_from_type_code(self, mock_usa_client):
        """Test factory creates Contract from type code."""
        data = {
            "generated_unique_award_id": "CONT_AWD_123",
            "type": "D",  # Contract code
        }
        award = create_award(data, mock_usa_client)

        assert isinstance(award, Contract)
        assert award.type == "D"

    def test_factory_creates_contract_from_various_codes(self, mock_usa_client):
        """Test factory creates Contract from various contract codes."""
        contract_codes = ["A", "B", "C", "D"]

        for code in contract_codes:
            data = {"generated_unique_award_id": f"CONT_AWD_{code}", "type": code}
            award = create_award(data, mock_usa_client)
            assert isinstance(award, Contract)
            assert award.type == code

    def test_factory_creates_idv_from_type_code(self, mock_usa_client):
        """Test factory creates IDV from type code."""
        idv_codes = [
            "IDV_A",
            "IDV_B",
            "IDV_B_A",
            "IDV_B_B",
            "IDV_B_C",
            "IDV_C",
            "IDV_D",
            "IDV_E",
        ]

        for code in idv_codes:
            data = {"generated_unique_award_id": f"CONT_IDV_{code}", "type": code}
            award = create_award(data, mock_usa_client)
            assert isinstance(award, IDV)
            assert award.type == code

    def test_factory_creates_grant_from_type_code(self, mock_usa_client):
        """Test factory creates Grant from grant type codes."""
        grant_codes = ["02", "03", "04", "05"]

        for code in grant_codes:
            data = {"generated_unique_award_id": f"ASST_NON_{code}", "type": code}
            award = create_award(data, mock_usa_client)
            assert isinstance(award, Grant)
            assert award.type == code

    def test_factory_creates_award_from_direct_payment_codes(self, mock_usa_client):
        """Test factory creates Grant from direct payment codes."""
        dp_codes = ["06", "10"]

        for code in dp_codes:
            data = {"generated_unique_award_id": f"ASST_NON_{code}", "type": code}
            award = create_award(data, mock_usa_client)
            assert isinstance(award, Award)  # Direct payments use Grant class
            assert award.type == code

    def test_factory_creates_award_from_other_assistance_codes(self, mock_usa_client):
        """Test factory creates Grant from other assistance codes."""
        other_codes = ["09", "11", "-1"]

        for code in other_codes:
            data = {"generated_unique_award_id": f"ASST_NON_{code}", "type": code}
            award = create_award(data, mock_usa_client)
            assert isinstance(award, Award)  # Other assistance uses Grant class

    def test_factory_creates_loan_from_type_code(self, mock_usa_client):
        """Test factory creates Loan from loan type codes."""
        loan_codes = ["07", "08"]

        for code in loan_codes:
            data = {"generated_unique_award_id": f"ASST_NON_{code}", "type": code}
            award = create_award(data, mock_usa_client)
            assert isinstance(award, Loan)


class TestFactoryPriority:
    """Test factory prioritizes category over type code."""

    def test_category_overrides_conflicting_type_code(self, mock_usa_client):
        """Test that category field takes priority over conflicting type code."""
        data = {
            "generated_unique_award_id": "ASST_NON_123",
            "category": "grant",  # Category says grant
            "type": "D",  # Type code says contract
        }
        award = create_award(data, mock_usa_client)

        # Should create Grant based on category, not Contract based on type
        assert isinstance(award, Grant)


class TestFactoryWithRealFixtureData:
    """Test factory with real fixture data."""

    def test_factory_with_contract_fixture(
        self, mock_usa_client, contract_fixture_data
    ):
        """Test factory creates Contract from contract fixture."""
        award = create_award(contract_fixture_data, mock_usa_client)
        assert isinstance(award, Contract)

    def test_factory_with_grant_fixture(self, mock_usa_client, grant_fixture_data):
        """Test factory creates Grant from grant fixture."""
        award = create_award(grant_fixture_data, mock_usa_client)
        assert isinstance(award, Grant)

    def test_factory_with_idv_fixture(self, mock_usa_client, idv_fixture_data):
        """Test factory creates IDV from IDV fixture."""
        award = create_award(idv_fixture_data, mock_usa_client)
        assert isinstance(award, IDV)

    def test_factory_with_loan_fixture(self, mock_usa_client, loan_fixture_data):
        """Test factory creates Loan from loan fixture."""
        award = create_award(loan_fixture_data, mock_usa_client)
        assert isinstance(award, Loan)


class TestFactoryFallbackToBaseAward:
    """Test factory falls back to base Award when type cannot be determined."""

    def test_factory_returns_base_award_for_unknown_type(self, mock_usa_client):
        """Test factory returns base Award for unknown type."""
        data = {"generated_unique_award_id": "UNKNOWN_123", "type": "UNKNOWN"}
        award = create_award(data, mock_usa_client)

        assert isinstance(award, Award)
        assert award.__class__ == Award  # Should be base Award, not subclass
        assert award.type == "UNKNOWN"

    def test_factory_returns_base_award_for_no_type_info(self, mock_usa_client):
        """Test factory returns base Award when no type information is available."""
        data = {
            "generated_unique_award_id": "NO_TYPE_123",
            "description": "Award with no type info",
        }
        award = create_award(data, mock_usa_client)

        assert isinstance(award, Award)
        assert award.__class__ == Award  # Should be base Award, not subclass
        assert award.description == "Award with no type info"

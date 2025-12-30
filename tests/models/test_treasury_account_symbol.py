"""Tests for TreasuryAccountSymbol model."""

import pytest

from usaspending.models.treasury_account_symbol import TreasuryAccountSymbol


class TestTreasuryAccountSymbolBasicProperties:
    """Test basic TreasuryAccountSymbol properties."""

    def test_basic_properties(self, mock_usa_client):
        """Test basic property access."""
        data = {
            "id": "080-2011/2012-0120-000",
            "ancestors": ["080", "080-0120"],
            "description": "Science, National Aeronautics and Space Administration",
            "count": 0,
            "children": None,
        }

        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.id == "080-2011/2012-0120-000"
        assert tas.tas_code == "080-2011/2012-0120-000"
        assert tas.description == "Science, National Aeronautics and Space Administration"
        assert tas.name == "Science, National Aeronautics and Space Administration"
        assert tas.count == 0
        assert tas.ancestors == ["080", "080-0120"]

    def test_parent_codes_from_ancestors(self, mock_usa_client):
        """Test toptier_code and federal_account_code from ancestors."""
        data = {
            "id": "080-2011/2012-0120-000",
            "ancestors": ["080", "080-0120"],
        }

        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.toptier_code == "080"
        assert tas.federal_account_code == "080-0120"

    def test_parent_codes_from_constructor(self, mock_usa_client):
        """Test toptier_code and federal_account_code from constructor."""
        data = {
            "id": "080-2011/2012-0120-000",
            "ancestors": [],
        }

        tas = TreasuryAccountSymbol(
            data,
            mock_usa_client,
            toptier_code="080",
            federal_account="080-0120",
        )

        assert tas.toptier_code == "080"
        assert tas.federal_account_code == "080-0120"


class TestTreasuryAccountSymbolParsing:
    """Test TAS ID parsing."""

    def test_parse_year_range_tas(self, mock_usa_client):
        """Test parsing TAS with year range (BPOA/EPOA)."""
        data = {"id": "080-2011/2012-0120-000"}
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.aid == "080"
        assert tas.main == "0120"
        assert tas.sub == "000"
        assert tas.bpoa == 2011
        assert tas.epoa == 2012
        assert tas.availability_type_code is None

    def test_parse_no_year_tas(self, mock_usa_client):
        """Test parsing no-year TAS (X availability)."""
        data = {"id": "080-X-0120-000"}
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.aid == "080"
        assert tas.main == "0120"
        assert tas.sub == "000"
        assert tas.bpoa is None
        assert tas.epoa is None
        assert tas.availability_type_code == "X"

    def test_parse_various_agency_ids(self, mock_usa_client):
        """Test parsing TAS with different agency ID lengths."""
        # 2-digit agency
        tas1 = TreasuryAccountSymbol({"id": "12-2024/2025-1234-000"}, mock_usa_client)
        assert tas1.aid == "12"

        # 3-digit agency
        tas2 = TreasuryAccountSymbol({"id": "080-2024/2025-1234-000"}, mock_usa_client)
        assert tas2.aid == "080"

        # 4-digit agency
        tas3 = TreasuryAccountSymbol({"id": "1601-2024/2025-1234-000"}, mock_usa_client)
        assert tas3.aid == "1601"

    def test_parse_invalid_format_returns_none(self, mock_usa_client):
        """Test parsing invalid TAS format returns None for components."""
        data = {"id": "invalid-format"}
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.aid is None
        assert tas.main is None
        assert tas.sub is None
        assert tas.bpoa is None
        assert tas.epoa is None


class TestTreasuryAccountSymbolFiscalYear:
    """Test fiscal_year() method."""

    def test_fiscal_year_within_range(self, mock_usa_client):
        """Test fiscal_year returns True for year within range."""
        data = {"id": "080-2011/2012-0120-000"}
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.fiscal_year(2011) is True
        assert tas.fiscal_year(2012) is True

    def test_fiscal_year_outside_range(self, mock_usa_client):
        """Test fiscal_year returns False for year outside range."""
        data = {"id": "080-2011/2012-0120-000"}
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.fiscal_year(2010) is False
        assert tas.fiscal_year(2013) is False

    def test_fiscal_year_no_year_account(self, mock_usa_client):
        """Test fiscal_year returns True for no-year accounts."""
        data = {"id": "080-X-0120-000"}
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.fiscal_year(2011) is True
        assert tas.fiscal_year(2024) is True
        assert tas.fiscal_year(2030) is True

    def test_fiscal_year_single_year(self, mock_usa_client):
        """Test fiscal_year for single-year appropriation (BPOA == EPOA)."""
        data = {"id": "080-2024/2024-0120-000"}
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.fiscal_year(2024) is True
        assert tas.fiscal_year(2023) is False
        assert tas.fiscal_year(2025) is False

    def test_fiscal_year_invalid_format(self, mock_usa_client):
        """Test fiscal_year returns False for invalid TAS format."""
        data = {"id": "invalid"}
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert tas.fiscal_year(2024) is False


class TestTreasuryAccountSymbolRepr:
    """Test string representation."""

    def test_repr_basic(self, mock_usa_client):
        """Test repr includes code and description."""
        data = {
            "id": "080-2011/2012-0120-000",
            "description": "Science, NASA",
        }
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert "080-2011/2012-0120-000" in repr(tas)
        assert "Science, NASA" in repr(tas)
        assert "TreasuryAccountSymbol" in repr(tas)

    def test_repr_long_description_truncated(self, mock_usa_client):
        """Test repr truncates long descriptions."""
        data = {
            "id": "080-2011/2012-0120-000",
            "description": "A" * 100,  # Very long description
        }
        tas = TreasuryAccountSymbol(data, mock_usa_client)

        assert "..." in repr(tas)
        assert len(repr(tas)) < 150


class TestTreasuryAccountSymbolFromFixture:
    """Test TreasuryAccountSymbol with real fixture data."""

    def test_from_fixture_data(self, mock_usa_client, load_fixture):
        """Test creating TreasuryAccountSymbol from fixture data."""
        fixture = load_fixture("tas_codes.json")
        first_result = fixture["results"][0]

        tas = TreasuryAccountSymbol(
            first_result,
            mock_usa_client,
            toptier_code="080",
            federal_account="080-0120",
        )

        assert tas.id == "080-2011/2012-0120-000"
        assert tas.bpoa == 2011
        assert tas.epoa == 2012
        assert tas.fiscal_year(2011) is True
        assert tas.fiscal_year(2012) is True

    def test_no_year_tas_from_fixture(self, mock_usa_client, load_fixture):
        """Test no-year TAS from fixture data."""
        fixture = load_fixture("tas_codes.json")
        # Find the X (no-year) entry
        no_year_result = next(
            r for r in fixture["results"] if "-X-" in r["id"]
        )

        tas = TreasuryAccountSymbol(no_year_result, mock_usa_client)

        assert tas.availability_type_code == "X"
        assert tas.bpoa is None
        assert tas.epoa is None
        assert tas.fiscal_year(2024) is True

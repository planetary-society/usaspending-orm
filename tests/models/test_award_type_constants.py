"""Tests for award type constants and utility functions.

This module tests the constants and helper functions defined in
src/usaspending/models/award_types.py, ensuring data integrity and
proper function behavior.
"""

from __future__ import annotations

import pytest

from usaspending.models.award_types import (
    AWARD_TYPE_GROUPS,
    AWARD_TYPE_DESCRIPTIONS,
    CONTRACT_CODES,
    IDV_CODES,
    LOAN_CODES,
    GRANT_CODES,
    DIRECT_PAYMENT_CODES,
    OTHER_CODES,
    ALL_AWARD_CODES,
    get_category_for_code,
    is_valid_award_type,
    get_description,
)


class TestAwardTypeConstants:
    """Test award type constants are properly defined."""

    def test_award_type_groups_structure(self):
        """Test AWARD_TYPE_GROUPS has expected structure."""
        expected_categories = {
            "contracts",
            "loans", 
            "idvs",
            "grants",
            "direct_payments",
            "other_assistance",
        }
        assert set(AWARD_TYPE_GROUPS.keys()) == expected_categories
        
        # Ensure all categories have at least one code
        for category, codes in AWARD_TYPE_GROUPS.items():
            assert len(codes) > 0, f"Category {category} should have codes"
            assert isinstance(codes, dict), f"Category {category} should be a dict"

    def test_award_type_groups_immutability(self):
        """Test that AWARD_TYPE_GROUPS is properly defined as a dict."""
        assert isinstance(AWARD_TYPE_GROUPS, dict)
        
        # Test that nested dictionaries contain string keys and values
        for category, codes in AWARD_TYPE_GROUPS.items():
            assert isinstance(category, str)
            assert isinstance(codes, dict)
            for code, description in codes.items():
                assert isinstance(code, str), f"Code {code} in {category} should be string"
                assert isinstance(description, str), f"Description for {code} should be string"

    def test_contract_codes(self):
        """Test CONTRACT_CODES contains expected values."""
        expected_codes = {"A", "B", "C", "D"}
        assert CONTRACT_CODES == expected_codes
        assert isinstance(CONTRACT_CODES, frozenset)

    def test_idv_codes(self):
        """Test IDV_CODES contains expected values."""
        expected_codes = {
            "IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", 
            "IDV_B_C", "IDV_C", "IDV_D", "IDV_E"
        }
        assert IDV_CODES == expected_codes
        assert isinstance(IDV_CODES, frozenset)

    def test_loan_codes(self):
        """Test LOAN_CODES contains expected values."""
        expected_codes = {"07", "08"}
        assert LOAN_CODES == expected_codes
        assert isinstance(LOAN_CODES, frozenset)

    def test_grant_codes(self):
        """Test GRANT_CODES contains expected values."""
        expected_codes = {"02", "03", "04", "05"}
        assert GRANT_CODES == expected_codes
        assert isinstance(GRANT_CODES, frozenset)

    def test_direct_payment_codes(self):
        """Test DIRECT_PAYMENT_CODES contains expected values."""
        expected_codes = {"06", "10"}
        assert DIRECT_PAYMENT_CODES == expected_codes
        assert isinstance(DIRECT_PAYMENT_CODES, frozenset)

    def test_other_codes(self):
        """Test OTHER_CODES contains expected values."""
        expected_codes = {"09", "11", "-1"}
        assert OTHER_CODES == expected_codes
        assert isinstance(OTHER_CODES, frozenset)

    def test_all_award_codes_completeness(self):
        """Test ALL_AWARD_CODES contains all individual code sets."""
        expected_all = (
            CONTRACT_CODES | IDV_CODES | LOAN_CODES | 
            GRANT_CODES | DIRECT_PAYMENT_CODES | OTHER_CODES
        )
        assert ALL_AWARD_CODES == expected_all
        assert isinstance(ALL_AWARD_CODES, frozenset)

    def test_no_code_overlap(self):
        """Test that no codes appear in multiple categories."""
        all_individual_codes = []
        for codes in [CONTRACT_CODES, IDV_CODES, LOAN_CODES, 
                     GRANT_CODES, DIRECT_PAYMENT_CODES, OTHER_CODES]:
            all_individual_codes.extend(codes)
        
        # If there are duplicates, set length will be less than list length
        assert len(set(all_individual_codes)) == len(all_individual_codes)

    def test_award_type_descriptions_completeness(self):
        """Test AWARD_TYPE_DESCRIPTIONS contains all codes from AWARD_TYPE_GROUPS."""
        expected_codes = set()
        for group_codes in AWARD_TYPE_GROUPS.values():
            expected_codes.update(group_codes.keys())
        
        assert set(AWARD_TYPE_DESCRIPTIONS.keys()) == expected_codes

    def test_award_type_descriptions_values(self):
        """Test AWARD_TYPE_DESCRIPTIONS has string descriptions."""
        for code, description in AWARD_TYPE_DESCRIPTIONS.items():
            assert isinstance(code, str), f"Code {code} should be string"
            assert isinstance(description, str), f"Description for {code} should be string"
            assert len(description) > 0, f"Description for {code} should not be empty"

    def test_frozenset_immutability(self):
        """Test that frozensets are actually immutable."""
        # Try to modify a frozenset - should raise AttributeError
        with pytest.raises(AttributeError):
            CONTRACT_CODES.add("X")
        
        with pytest.raises(AttributeError):
            ALL_AWARD_CODES.remove("A")


class TestGetCategoryForCode:
    """Test get_category_for_code function."""

    def test_contract_codes(self):
        """Test contract codes return 'contracts' category."""
        for code in CONTRACT_CODES:
            assert get_category_for_code(code) == "contracts"

    def test_idv_codes(self):
        """Test IDV codes return 'idvs' category.""" 
        for code in IDV_CODES:
            assert get_category_for_code(code) == "idvs"

    def test_loan_codes(self):
        """Test loan codes return 'loans' category."""
        for code in LOAN_CODES:
            assert get_category_for_code(code) == "loans"

    def test_grant_codes(self):
        """Test grant codes return 'grants' category."""
        for code in GRANT_CODES:
            assert get_category_for_code(code) == "grants"

    def test_direct_payment_codes(self):
        """Test direct payment codes return 'direct_payments' category."""
        for code in DIRECT_PAYMENT_CODES:
            assert get_category_for_code(code) == "direct_payments"

    def test_other_codes(self):
        """Test other codes return 'other_assistance' category."""
        for code in OTHER_CODES:
            assert get_category_for_code(code) == "other_assistance"

    @pytest.mark.parametrize("invalid_code", [
        "INVALID", "99", "XYZ", "", "ABC123", "Z", "00", "13"
    ])
    def test_invalid_codes_return_empty_string(self, invalid_code):
        """Test invalid codes return empty string."""
        assert get_category_for_code(invalid_code) == ""

    def test_case_sensitive(self):
        """Test function is case sensitive."""
        assert get_category_for_code("a") == ""  # lowercase 'a' vs 'A'
        assert get_category_for_code("A") == "contracts"
        assert get_category_for_code("idv_a") == ""  # lowercase vs 'IDV_A'

    @pytest.mark.parametrize("code_with_whitespace", [
        " A ", "A ", " A", "\tA", "A\n", "\rA\r"
    ])
    def test_whitespace_handling(self, code_with_whitespace):
        """Test function doesn't match codes with whitespace."""
        assert get_category_for_code(code_with_whitespace) == ""

    def test_special_characters(self):
        """Test handling of special characters."""
        assert get_category_for_code("-1") == "other_assistance"  # Valid negative
        assert get_category_for_code("-2") == ""  # Invalid negative
        assert get_category_for_code("+1") == ""  # Plus sign


class TestIsValidAwardType:
    """Test is_valid_award_type function."""

    def test_all_valid_codes_return_true(self):
        """Test all codes in ALL_AWARD_CODES return True."""
        for code in ALL_AWARD_CODES:
            assert is_valid_award_type(code) is True

    @pytest.mark.parametrize("invalid_code", [
        "INVALID", "99", "XYZ", "", "ABC123", "a", " A ", "Z", "13"
    ])
    def test_invalid_codes_return_false(self, invalid_code):
        """Test invalid codes return False."""
        assert is_valid_award_type(invalid_code) is False

    def test_none_input_handling(self):
        """Test None input is handled gracefully."""
        # Should not raise an exception, should return False
        assert is_valid_award_type(None) is False

    def test_numeric_string_codes(self):
        """Test numeric string codes work correctly."""
        assert is_valid_award_type("02") is True
        assert is_valid_award_type("07") is True
        assert is_valid_award_type("2") is False  # Missing leading zero
        assert is_valid_award_type("7") is False  # Missing leading zero

    def test_negative_one_code(self):
        """Test special '-1' code is valid."""
        assert is_valid_award_type("-1") is True
        assert is_valid_award_type("-2") is False

    def test_case_sensitivity(self):
        """Test function is case sensitive."""
        assert is_valid_award_type("IDV_A") is True
        assert is_valid_award_type("idv_a") is False
        assert is_valid_award_type("A") is True
        assert is_valid_award_type("a") is False

    def test_type_validation(self):
        """Test function handles non-string inputs properly."""
        # Numbers should be converted to string and validated
        assert is_valid_award_type(2) is False  # int 2 != "02"
        assert is_valid_award_type(7) is False  # int 7 != "07"
        
        # Other types should return False
        assert is_valid_award_type([]) is False
        assert is_valid_award_type({}) is False


class TestGetDescription:
    """Test get_description function."""

    def test_valid_codes_return_descriptions(self):
        """Test valid codes return non-empty descriptions."""
        for code in ALL_AWARD_CODES:
            description = get_description(code)
            assert isinstance(description, str)
            assert len(description) > 0, f"Code {code} should have non-empty description"

    @pytest.mark.parametrize("invalid_code", [
        "INVALID", "99", "XYZ", "", "ABC123", "Z", "13"
    ])
    def test_invalid_codes_return_empty_string(self, invalid_code):
        """Test invalid codes return empty string."""
        assert get_description(invalid_code) == ""

    @pytest.mark.parametrize("code,expected_desc", [
        ("A", "BPA Call"),
        ("D", "Definitive Contract"),
        ("02", "Block Grant"),
        ("07", "Direct Loan"),
        ("IDV_A", "GWAC Government Wide Acquisition Contract"),
        ("06", "Direct Payment for Specified Use"),
        ("09", "Insurance"),
        ("-1", "Not Specified"),
    ])
    def test_specific_descriptions(self, code, expected_desc):
        """Test specific codes return expected descriptions."""
        assert get_description(code) == expected_desc

    def test_case_sensitive_descriptions(self):
        """Test descriptions are case sensitive."""
        assert get_description("a") == ""  # lowercase 'a'
        assert get_description("A") == "BPA Call"
        assert get_description("idv_a") == ""
        assert get_description("IDV_A") == "GWAC Government Wide Acquisition Contract"

    def test_none_input_handling(self):
        """Test None input is handled gracefully."""
        assert get_description(None) == ""

    def test_whitespace_handling(self):
        """Test function handles whitespace properly."""
        assert get_description(" A ") == ""
        assert get_description("A") == "BPA Call"


class TestDataConsistency:
    """Test consistency between different constants and functions."""

    def test_functions_consistent_with_constants(self):
        """Test helper functions are consistent with constant definitions."""
        for code in ALL_AWARD_CODES:
            # Every valid code should have a category
            category = get_category_for_code(code)
            assert category != "", f"Code {code} should have a category"
            
            # Every valid code should have a description
            description = get_description(code)
            assert description != "", f"Code {code} should have a description"
            
            # Every valid code should validate as valid
            assert is_valid_award_type(code) is True

    def test_award_type_groups_match_frozensets(self):
        """Test individual frozensets match AWARD_TYPE_GROUPS content."""
        assert CONTRACT_CODES == frozenset(AWARD_TYPE_GROUPS["contracts"].keys())
        assert IDV_CODES == frozenset(AWARD_TYPE_GROUPS["idvs"].keys())
        assert LOAN_CODES == frozenset(AWARD_TYPE_GROUPS["loans"].keys())
        assert GRANT_CODES == frozenset(AWARD_TYPE_GROUPS["grants"].keys())
        assert DIRECT_PAYMENT_CODES == frozenset(AWARD_TYPE_GROUPS["direct_payments"].keys())
        assert OTHER_CODES == frozenset(AWARD_TYPE_GROUPS["other_assistance"].keys())

    def test_descriptions_match_groups(self):
        """Test AWARD_TYPE_DESCRIPTIONS matches AWARD_TYPE_GROUPS values."""
        for codes_dict in AWARD_TYPE_GROUPS.values():
            for code, expected_desc in codes_dict.items():
                assert AWARD_TYPE_DESCRIPTIONS[code] == expected_desc

    def test_all_codes_represented_in_groups(self):
        """Test every code in ALL_AWARD_CODES appears in exactly one group."""
        codes_in_groups = set()
        for category_codes in AWARD_TYPE_GROUPS.values():
            codes_in_groups.update(category_codes.keys())
        
        assert ALL_AWARD_CODES == codes_in_groups

    def test_category_function_matches_group_membership(self):
        """Test get_category_for_code returns correct category for each group."""
        for category, codes_dict in AWARD_TYPE_GROUPS.items():
            for code in codes_dict.keys():
                assert get_category_for_code(code) == category


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.parametrize("func", [get_category_for_code, get_description])
    def test_empty_string_input(self, func):
        """Test functions handle empty string input gracefully."""
        assert func("") == ""

    def test_is_valid_award_type_empty_string(self):
        """Test is_valid_award_type handles empty string."""
        assert is_valid_award_type("") is False

    @pytest.mark.parametrize("whitespace_input", [" ", "\t", "\n", "\r\n", "  \t  "])
    def test_whitespace_only_input(self, whitespace_input):
        """Test functions handle whitespace-only input."""
        assert get_category_for_code(whitespace_input) == ""
        assert is_valid_award_type(whitespace_input) is False
        assert get_description(whitespace_input) == ""

    @pytest.mark.parametrize("unicode_input", ["café", "🎯", "测试", "ñoño"])
    def test_unicode_input(self, unicode_input):
        """Test functions handle unicode input gracefully."""
        assert get_category_for_code(unicode_input) == ""
        assert is_valid_award_type(unicode_input) is False
        assert get_description(unicode_input) == ""

    def test_very_long_string_input(self):
        """Test functions handle very long string input."""
        long_string = "A" * 1000
        assert get_category_for_code(long_string) == ""
        assert is_valid_award_type(long_string) is False
        assert get_description(long_string) == ""

    @pytest.mark.parametrize("numeric_input", [0, 1, 2, 7, 99, -1])
    def test_numeric_input_handling(self, numeric_input):
        """Test functions handle numeric inputs properly."""
        # Functions should handle non-string inputs gracefully
        assert get_category_for_code(numeric_input) == ""
        assert is_valid_award_type(numeric_input) is False
        assert get_description(numeric_input) == ""


class TestPerformance:
    """Test performance characteristics of the functions."""

    def test_constant_lookup_performance(self):
        """Test that lookups are efficient (using sets/dicts, not loops)."""
        # This is more of a design validation - the functions should use
        # efficient lookups rather than iterating through all codes
        
        # Test a reasonable number of lookups don't take too long
        import time
        
        start_time = time.time()
        for _ in range(1000):
            for code in ["A", "02", "IDV_A", "INVALID"]:
                is_valid_award_type(code)
                get_category_for_code(code)
                get_description(code)
        end_time = time.time()
        
        # Should complete 12,000 function calls in well under a second
        assert (end_time - start_time) < 1.0, "Function calls should be efficient"
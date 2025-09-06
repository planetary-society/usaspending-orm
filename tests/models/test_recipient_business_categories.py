"""Tests for recipient business category constants and utility functions.

This module tests the constants and helper functions defined in
src/usaspending/models/recipient_business_categories.py, ensuring data integrity,
proper function behavior, and correct handling of overlapping categories.
"""

from __future__ import annotations

import pytest
import time

from usaspending.models.recipient_business_categories import (
    BUSINESS_CATEGORY_GROUPS,
    BUSINESS_CATEGORY_DESCRIPTIONS,
    BUSINESS_CATEGORIES,
    ALL_BUSINESS_CATEGORIES,
    CATEGORY_BUSINESS_CODES,
    MINORITY_OWNED_CODES,
    WOMEN_OWNED_CODES,
    VETERAN_OWNED_CODES,
    SPECIAL_DESIGNATIONS_CODES,
    NONPROFIT_CODES,
    HIGHER_EDUCATION_CODES,
    GOVERNMENT_CODES,
    INDIVIDUALS_CODES,
    OVERLAPPING_CATEGORIES,
    get_category_group,
    get_all_groups_for_code,
    is_valid_business_category,
    get_description,
    is_small_business,
    is_minority_owned,
    is_women_owned,
    is_veteran_owned,
    is_government_entity,
    is_educational_institution,
    is_nonprofit_organization,
)


class TestBusinessCategoryConstants:
    """Test business category constants are properly defined."""

    def test_business_category_groups_structure(self):
        """Test BUSINESS_CATEGORY_GROUPS has expected structure."""
        expected_groups = {
            "category_business",
            "minority_owned",
            "women_owned",
            "veteran_owned",
            "special_designations",
            "nonprofit",
            "higher_education",
            "government",
            "individuals",
        }
        assert set(BUSINESS_CATEGORY_GROUPS.keys()) == expected_groups
        
        # Ensure all groups have at least one category
        for group_name, categories in BUSINESS_CATEGORY_GROUPS.items():
            assert len(categories) > 0, f"Group {group_name} should have categories"
            assert isinstance(categories, dict), f"Group {group_name} should be a dict"

    def test_business_category_groups_immutability(self):
        """Test that BUSINESS_CATEGORY_GROUPS is properly defined as a dict."""
        assert isinstance(BUSINESS_CATEGORY_GROUPS, dict)
        
        # Test that nested dictionaries contain string keys and values
        for group_name, categories in BUSINESS_CATEGORY_GROUPS.items():
            assert isinstance(group_name, str)
            assert isinstance(categories, dict)
            for code, description in categories.items():
                assert isinstance(code, str), f"Code {code} in {group_name} should be string"
                assert isinstance(description, str), f"Description for {code} should be string"

    def test_category_business_codes(self):
        """Test CATEGORY_BUSINESS_CODES contains expected values."""
        expected_codes = {
            "category_business",
            "small_business",
            "other_than_small_business",
            "corporate_entity_tax_exempt",
            "corporate_entity_not_tax_exempt",
            "partnership_or_limited_liability_partnership",
            "sole_proprietorship",
            "manufacturer_of_goods",
            "subchapter_s_corporation",
            "limited_liability_corporation",
        }
        assert CATEGORY_BUSINESS_CODES == expected_codes
        assert isinstance(CATEGORY_BUSINESS_CODES, frozenset)

    def test_minority_owned_codes(self):
        """Test MINORITY_OWNED_CODES contains expected values."""
        expected_codes = {
            "minority_owned_business",
            "alaskan_native_corporation_owned_firm",
            "american_indian_owned_business",
            "asian_pacific_american_owned_business",
            "black_american_owned_business",
            "hispanic_american_owned_business",
            "native_american_owned_business",
            "native_hawaiian_organization_owned_firm",
            "subcontinent_asian_indian_american_owned_business",
            "tribally_owned_firm",
            "other_minority_owned_business",
        }
        assert MINORITY_OWNED_CODES == expected_codes
        assert isinstance(MINORITY_OWNED_CODES, frozenset)

    def test_women_owned_codes(self):
        """Test WOMEN_OWNED_CODES contains expected values."""
        expected_codes = {
            "woman_owned_business",
            "women_owned_small_business",
            "economically_disadvantaged_women_owned_small_business",
            "joint_venture_women_owned_small_business",
            "joint_venture_economically_disadvantaged_women_owned_small_business",
        }
        assert WOMEN_OWNED_CODES == expected_codes
        assert isinstance(WOMEN_OWNED_CODES, frozenset)

    def test_veteran_owned_codes(self):
        """Test VETERAN_OWNED_CODES contains expected values."""
        expected_codes = {
            "veteran_owned_business",
            "service_disabled_veteran_owned_business",
        }
        assert VETERAN_OWNED_CODES == expected_codes
        assert isinstance(VETERAN_OWNED_CODES, frozenset)

    def test_special_designations_codes(self):
        """Test SPECIAL_DESIGNATIONS_CODES contains key special designation values."""
        # Check for some key codes that should be present
        key_codes = {
            "special_designations",
            "8a_program_participant",
            "ability_one_program",
            "emerging_small_business",
            "historically_underutilized_business_firm",
            "small_disadvantaged_business",
            "us_owned_business",
            "foreign_owned",
            "hospital",
        }
        assert key_codes.issubset(SPECIAL_DESIGNATIONS_CODES)
        assert isinstance(SPECIAL_DESIGNATIONS_CODES, frozenset)

    def test_nonprofit_codes(self):
        """Test NONPROFIT_CODES contains expected values."""
        expected_codes = {
            "nonprofit",
            "foundation",
            "community_development_corporations",
        }
        assert NONPROFIT_CODES == expected_codes
        assert isinstance(NONPROFIT_CODES, frozenset)

    def test_higher_education_codes(self):
        """Test HIGHER_EDUCATION_CODES contains expected values."""
        expected_codes = {
            "higher_education",
            "public_institution_of_higher_education",
            "private_institution_of_higher_education",
            "minority_serving_institution_of_higher_education",
            "educational_institution",
            "school_of_forestry",
            "veterinary_college",
        }
        assert HIGHER_EDUCATION_CODES == expected_codes
        assert isinstance(HIGHER_EDUCATION_CODES, frozenset)

    def test_government_codes(self):
        """Test GOVERNMENT_CODES contains expected values."""
        expected_codes = {
            "government",
            "national_government",
            "regional_and_state_government",
            "regional_organization",
            "interstate_entity",
            "us_territory_or_possession",
            "local_government",
            "indian_native_american_tribal_government",
            "authorities_and_commissions",
            "council_of_governments",
        }
        assert GOVERNMENT_CODES == expected_codes
        assert isinstance(GOVERNMENT_CODES, frozenset)

    def test_individuals_codes(self):
        """Test INDIVIDUALS_CODES contains expected values."""
        expected_codes = {"individuals"}
        assert INDIVIDUALS_CODES == expected_codes
        assert isinstance(INDIVIDUALS_CODES, frozenset)

    def test_all_business_categories_completeness(self):
        """Test ALL_BUSINESS_CATEGORIES contains all codes from all groups."""
        all_codes = set()
        for group_codes in BUSINESS_CATEGORY_GROUPS.values():
            all_codes.update(group_codes.keys())
        
        assert ALL_BUSINESS_CATEGORIES == all_codes
        assert isinstance(ALL_BUSINESS_CATEGORIES, frozenset)

    def test_backward_compatibility(self):
        """Test BUSINESS_CATEGORIES exists for backward compatibility."""
        assert BUSINESS_CATEGORIES == ALL_BUSINESS_CATEGORIES
        assert isinstance(BUSINESS_CATEGORIES, frozenset)

    def test_business_category_descriptions_completeness(self):
        """Test BUSINESS_CATEGORY_DESCRIPTIONS contains all codes."""
        all_codes = set()
        for group_codes in BUSINESS_CATEGORY_GROUPS.values():
            all_codes.update(group_codes.keys())
        
        assert set(BUSINESS_CATEGORY_DESCRIPTIONS.keys()) == all_codes

    def test_business_category_descriptions_values(self):
        """Test BUSINESS_CATEGORY_DESCRIPTIONS has string descriptions."""
        for code, description in BUSINESS_CATEGORY_DESCRIPTIONS.items():
            assert isinstance(code, str), f"Code {code} should be string"
            assert isinstance(description, str), f"Description for {code} should be string"
            assert len(description) > 0, f"Description for {code} should not be empty"

    def test_frozenset_immutability(self):
        """Test that frozensets are actually immutable."""
        # Try to modify a frozenset - should raise AttributeError
        with pytest.raises(AttributeError):
            CATEGORY_BUSINESS_CODES.add("X")
        
        with pytest.raises(AttributeError):
            ALL_BUSINESS_CATEGORIES.remove("small_business")


class TestOverlappingCategories:
    """Test handling of categories that belong to multiple groups."""

    def test_overlapping_categories_structure(self):
        """Test OVERLAPPING_CATEGORIES has correct structure."""
        assert isinstance(OVERLAPPING_CATEGORIES, dict)
        
        for code, groups in OVERLAPPING_CATEGORIES.items():
            assert isinstance(code, str), f"Code {code} should be string"
            assert isinstance(groups, list), f"Groups for {code} should be list"
            assert len(groups) >= 2, f"Overlapping category {code} should belong to at least 2 groups"
            for group in groups:
                assert group in BUSINESS_CATEGORY_GROUPS, f"Group {group} should exist"

    def test_women_owned_small_business_overlap(self):
        """Test women-owned small businesses are in both categories."""
        women_small_businesses = [
            "women_owned_small_business",
            "economically_disadvantaged_women_owned_small_business",
            "joint_venture_women_owned_small_business",
            "joint_venture_economically_disadvantaged_women_owned_small_business",
        ]
        
        for code in women_small_businesses:
            assert code in OVERLAPPING_CATEGORIES
            assert "women_owned" in OVERLAPPING_CATEGORIES[code]
            assert "category_business" in OVERLAPPING_CATEGORIES[code]

    def test_special_designation_small_business_overlap(self):
        """Test special designation small businesses are in both categories."""
        special_small_businesses = [
            "emerging_small_business",
            "small_agricultural_cooperative",
            "small_disadvantaged_business",
            "self_certified_small_disadvanted_business",
        ]
        
        for code in special_small_businesses:
            assert code in OVERLAPPING_CATEGORIES
            assert "category_business" in OVERLAPPING_CATEGORIES[code]
            assert "special_designations" in OVERLAPPING_CATEGORIES[code]


class TestGetCategoryGroup:
    """Test get_category_group function."""

    def test_business_category_codes(self):
        """Test business category codes return 'category_business'."""
        test_codes = ["small_business", "other_than_small_business", "sole_proprietorship"]
        for code in test_codes:
            assert get_category_group(code) == "category_business"

    def test_minority_owned_codes(self):
        """Test minority owned codes return 'minority_owned'."""
        test_codes = ["minority_owned_business", "black_american_owned_business", "tribally_owned_firm"]
        for code in test_codes:
            assert get_category_group(code) == "minority_owned"

    def test_women_owned_codes(self):
        """Test women owned codes return 'women_owned'."""
        assert get_category_group("woman_owned_business") == "women_owned"

    def test_veteran_owned_codes(self):
        """Test veteran owned codes return 'veteran_owned'."""
        test_codes = ["veteran_owned_business", "service_disabled_veteran_owned_business"]
        for code in test_codes:
            assert get_category_group(code) == "veteran_owned"

    def test_special_designations_codes(self):
        """Test special designation codes return 'special_designations'."""
        test_codes = ["8a_program_participant", "hospital", "foreign_owned"]
        for code in test_codes:
            assert get_category_group(code) == "special_designations"

    def test_nonprofit_codes(self):
        """Test nonprofit codes return 'nonprofit'."""
        test_codes = ["nonprofit", "foundation", "community_development_corporations"]
        for code in test_codes:
            assert get_category_group(code) == "nonprofit"

    def test_higher_education_codes(self):
        """Test higher education codes return 'higher_education'."""
        test_codes = ["higher_education", "veterinary_college", "school_of_forestry"]
        for code in test_codes:
            assert get_category_group(code) == "higher_education"

    def test_government_codes(self):
        """Test government codes return 'government'."""
        test_codes = ["government", "local_government", "national_government"]
        for code in test_codes:
            assert get_category_group(code) == "government"

    def test_individuals_code(self):
        """Test individuals code returns 'individuals'."""
        assert get_category_group("individuals") == "individuals"

    def test_overlapping_categories_return_primary(self):
        """Test overlapping categories return their primary group."""
        # Women-owned small businesses should return women_owned as primary
        assert get_category_group("women_owned_small_business") == "women_owned"
        
        # Special small businesses should return category_business as primary
        assert get_category_group("emerging_small_business") == "category_business"

    @pytest.mark.parametrize("invalid_code", [
        "INVALID", "99", "XYZ", "", "ABC123", "Z", "00", "nonexistent"
    ])
    def test_invalid_codes_return_empty_string(self, invalid_code):
        """Test invalid codes return empty string."""
        assert get_category_group(invalid_code) == ""

    def test_case_sensitive(self):
        """Test function is case sensitive."""
        assert get_category_group("SMALL_BUSINESS") == ""  # uppercase should not match
        assert get_category_group("small_business") == "category_business"

    def test_none_input_handling(self):
        """Test None input is handled gracefully."""
        assert get_category_group(None) == ""


class TestGetAllGroupsForCode:
    """Test get_all_groups_for_code function."""

    def test_single_group_categories(self):
        """Test categories that belong to a single group."""
        assert get_all_groups_for_code("small_business") == ["category_business"]
        assert get_all_groups_for_code("nonprofit") == ["nonprofit"]
        assert get_all_groups_for_code("individuals") == ["individuals"]

    def test_overlapping_categories(self):
        """Test categories that belong to multiple groups."""
        # Women-owned small businesses
        groups = get_all_groups_for_code("women_owned_small_business")
        assert set(groups) == {"women_owned", "category_business"}
        assert len(groups) == 2
        
        # Special designation small businesses
        groups = get_all_groups_for_code("emerging_small_business")
        assert set(groups) == {"category_business", "special_designations"}
        assert len(groups) == 2

    def test_invalid_codes(self):
        """Test invalid codes return empty list."""
        assert get_all_groups_for_code("invalid_code") == []
        assert get_all_groups_for_code("") == []
        assert get_all_groups_for_code(None) == []

    def test_returns_copy_not_reference(self):
        """Test function returns a copy, not a reference to internal data."""
        groups1 = get_all_groups_for_code("emerging_small_business")
        groups2 = get_all_groups_for_code("emerging_small_business")
        assert groups1 is not groups2  # Should be different objects
        assert groups1 == groups2  # But with same content


class TestIsValidBusinessCategory:
    """Test is_valid_business_category function."""

    def test_all_valid_codes_return_true(self):
        """Test all codes in ALL_BUSINESS_CATEGORIES return True."""
        for code in ALL_BUSINESS_CATEGORIES:
            assert is_valid_business_category(code) is True

    @pytest.mark.parametrize("invalid_code", [
        "INVALID", "99", "XYZ", "", "ABC123", "SMALL_BUSINESS", " small_business ", "Z"
    ])
    def test_invalid_codes_return_false(self, invalid_code):
        """Test invalid codes return False."""
        assert is_valid_business_category(invalid_code) is False

    def test_none_input_handling(self):
        """Test None input is handled gracefully."""
        assert is_valid_business_category(None) is False

    def test_case_sensitivity(self):
        """Test function is case sensitive."""
        assert is_valid_business_category("small_business") is True
        assert is_valid_business_category("SMALL_BUSINESS") is False
        assert is_valid_business_category("Small_Business") is False

    def test_type_validation(self):
        """Test function handles non-string inputs properly."""
        assert is_valid_business_category(123) is False
        assert is_valid_business_category([]) is False
        assert is_valid_business_category({}) is False


class TestGetDescription:
    """Test get_description function."""

    def test_valid_codes_return_descriptions(self):
        """Test valid codes return non-empty descriptions."""
        for code in ALL_BUSINESS_CATEGORIES:
            description = get_description(code)
            assert isinstance(description, str)
            assert len(description) > 0, f"Code {code} should have non-empty description"

    @pytest.mark.parametrize("invalid_code", [
        "INVALID", "99", "XYZ", "", "ABC123", "Z"
    ])
    def test_invalid_codes_return_empty_string(self, invalid_code):
        """Test invalid codes return empty string."""
        assert get_description(invalid_code) == ""

    @pytest.mark.parametrize("code,expected_desc", [
        ("small_business", "Small Business"),
        ("nonprofit", "Nonprofit Organization"),
        ("8a_program_participant", "8(a) Program Participant"),
        ("woman_owned_business", "Woman Owned Business"),
        ("veteran_owned_business", "Veteran Owned Business"),
        ("individuals", "Individuals"),
        ("government", "Government"),
        ("foreign_owned", "Foreign Owned"),
    ])
    def test_specific_descriptions(self, code, expected_desc):
        """Test specific codes return expected descriptions."""
        assert get_description(code) == expected_desc

    def test_case_sensitive_descriptions(self):
        """Test descriptions are case sensitive."""
        assert get_description("small_business") == "Small Business"
        assert get_description("SMALL_BUSINESS") == ""

    def test_none_input_handling(self):
        """Test None input is handled gracefully."""
        assert get_description(None) == ""


class TestConvenienceMethods:
    """Test convenience helper methods."""

    def test_is_small_business(self):
        """Test is_small_business function."""
        # Direct small business
        assert is_small_business("small_business") is True
        
        # Women-owned small businesses
        assert is_small_business("women_owned_small_business") is True
        assert is_small_business("economically_disadvantaged_women_owned_small_business") is True
        
        # Special designation small businesses
        assert is_small_business("emerging_small_business") is True
        assert is_small_business("small_disadvantaged_business") is True
        assert is_small_business("small_agricultural_cooperative") is True
        
        # Non-small businesses
        assert is_small_business("other_than_small_business") is False
        assert is_small_business("nonprofit") is False
        assert is_small_business("government") is False
        
        # Invalid input
        assert is_small_business(None) is False
        assert is_small_business("") is False

    def test_is_minority_owned(self):
        """Test is_minority_owned function."""
        assert is_minority_owned("minority_owned_business") is True
        assert is_minority_owned("black_american_owned_business") is True
        assert is_minority_owned("hispanic_american_owned_business") is True
        assert is_minority_owned("tribally_owned_firm") is True
        
        assert is_minority_owned("woman_owned_business") is False
        assert is_minority_owned("small_business") is False
        assert is_minority_owned(None) is False

    def test_is_women_owned(self):
        """Test is_women_owned function."""
        assert is_women_owned("woman_owned_business") is True
        assert is_women_owned("women_owned_small_business") is True
        assert is_women_owned("joint_venture_women_owned_small_business") is True
        
        assert is_women_owned("minority_owned_business") is False
        assert is_women_owned("small_business") is False
        assert is_women_owned(None) is False

    def test_is_veteran_owned(self):
        """Test is_veteran_owned function."""
        assert is_veteran_owned("veteran_owned_business") is True
        assert is_veteran_owned("service_disabled_veteran_owned_business") is True
        
        assert is_veteran_owned("small_business") is False
        assert is_veteran_owned("woman_owned_business") is False
        assert is_veteran_owned(None) is False

    def test_is_government_entity(self):
        """Test is_government_entity function."""
        assert is_government_entity("government") is True
        assert is_government_entity("local_government") is True
        assert is_government_entity("national_government") is True
        assert is_government_entity("authorities_and_commissions") is True
        
        assert is_government_entity("small_business") is False
        assert is_government_entity("nonprofit") is False
        assert is_government_entity(None) is False

    def test_is_educational_institution(self):
        """Test is_educational_institution function."""
        assert is_educational_institution("higher_education") is True
        assert is_educational_institution("veterinary_college") is True
        assert is_educational_institution("school_of_forestry") is True
        assert is_educational_institution("public_institution_of_higher_education") is True
        
        assert is_educational_institution("government") is False
        assert is_educational_institution("small_business") is False
        assert is_educational_institution(None) is False

    def test_is_nonprofit_organization(self):
        """Test is_nonprofit_organization function."""
        assert is_nonprofit_organization("nonprofit") is True
        assert is_nonprofit_organization("foundation") is True
        assert is_nonprofit_organization("community_development_corporations") is True
        
        assert is_nonprofit_organization("small_business") is False
        assert is_nonprofit_organization("government") is False
        assert is_nonprofit_organization(None) is False


class TestDataConsistency:
    """Test consistency between different constants and functions."""

    def test_functions_consistent_with_constants(self):
        """Test helper functions are consistent with constant definitions."""
        for code in ALL_BUSINESS_CATEGORIES:
            # Every valid code should have at least one group
            primary_group = get_category_group(code)
            assert primary_group != "", f"Code {code} should have a primary group"
            
            # Every valid code should have a description
            description = get_description(code)
            assert description != "", f"Code {code} should have a description"
            
            # Every valid code should validate as valid
            assert is_valid_business_category(code) is True

    def test_group_frozensets_match_business_category_groups(self):
        """Test individual frozensets match BUSINESS_CATEGORY_GROUPS content."""
        assert CATEGORY_BUSINESS_CODES == frozenset(BUSINESS_CATEGORY_GROUPS["category_business"].keys())
        assert MINORITY_OWNED_CODES == frozenset(BUSINESS_CATEGORY_GROUPS["minority_owned"].keys())
        assert WOMEN_OWNED_CODES == frozenset(BUSINESS_CATEGORY_GROUPS["women_owned"].keys())
        assert VETERAN_OWNED_CODES == frozenset(BUSINESS_CATEGORY_GROUPS["veteran_owned"].keys())
        assert SPECIAL_DESIGNATIONS_CODES == frozenset(BUSINESS_CATEGORY_GROUPS["special_designations"].keys())
        assert NONPROFIT_CODES == frozenset(BUSINESS_CATEGORY_GROUPS["nonprofit"].keys())
        assert HIGHER_EDUCATION_CODES == frozenset(BUSINESS_CATEGORY_GROUPS["higher_education"].keys())
        assert GOVERNMENT_CODES == frozenset(BUSINESS_CATEGORY_GROUPS["government"].keys())
        assert INDIVIDUALS_CODES == frozenset(BUSINESS_CATEGORY_GROUPS["individuals"].keys())

    def test_descriptions_match_groups(self):
        """Test BUSINESS_CATEGORY_DESCRIPTIONS matches BUSINESS_CATEGORY_GROUPS values."""
        for group_dict in BUSINESS_CATEGORY_GROUPS.values():
            for code, expected_desc in group_dict.items():
                assert BUSINESS_CATEGORY_DESCRIPTIONS[code] == expected_desc

    def test_all_codes_represented_in_groups(self):
        """Test every code in ALL_BUSINESS_CATEGORIES appears in at least one group."""
        codes_in_groups = set()
        for category_codes in BUSINESS_CATEGORY_GROUPS.values():
            codes_in_groups.update(category_codes.keys())
        
        assert ALL_BUSINESS_CATEGORIES == codes_in_groups

    def test_overlapping_categories_exist_in_groups(self):
        """Test all overlapping categories actually exist in their specified groups."""
        for code, groups in OVERLAPPING_CATEGORIES.items():
            # Code should be valid
            assert is_valid_business_category(code), f"Overlapping code {code} should be valid"
            
            # Code should exist in at least one of its specified groups
            found_in_groups = []
            for group_name in groups:
                if code in BUSINESS_CATEGORY_GROUPS.get(group_name, {}):
                    found_in_groups.append(group_name)
            
            # For overlapping categories, we expect them to be in special_designations
            # but they might be listed in category_business through overlap logic
            assert len(found_in_groups) > 0, f"Code {code} not found in any of its groups: {groups}"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.parametrize("func", [get_category_group, get_description])
    def test_empty_string_input(self, func):
        """Test functions handle empty string input gracefully."""
        assert func("") == ""

    def test_is_valid_business_category_empty_string(self):
        """Test is_valid_business_category handles empty string."""
        assert is_valid_business_category("") is False

    @pytest.mark.parametrize("whitespace_input", [" ", "\t", "\n", "\r\n", "  \t  "])
    def test_whitespace_only_input(self, whitespace_input):
        """Test functions handle whitespace-only input."""
        assert get_category_group(whitespace_input) == ""
        assert is_valid_business_category(whitespace_input) is False
        assert get_description(whitespace_input) == ""
        assert get_all_groups_for_code(whitespace_input) == []

    @pytest.mark.parametrize("whitespace_wrapped", [
        " small_business ", "small_business ", " small_business", "\tsmall_business\n"
    ])
    def test_whitespace_wrapped_input(self, whitespace_wrapped):
        """Test functions don't match codes with surrounding whitespace."""
        assert get_category_group(whitespace_wrapped) == ""
        assert is_valid_business_category(whitespace_wrapped) is False
        assert get_description(whitespace_wrapped) == ""

    @pytest.mark.parametrize("unicode_input", ["café", "🎯", "测试", "ñoño"])
    def test_unicode_input(self, unicode_input):
        """Test functions handle unicode input gracefully."""
        assert get_category_group(unicode_input) == ""
        assert is_valid_business_category(unicode_input) is False
        assert get_description(unicode_input) == ""
        assert get_all_groups_for_code(unicode_input) == []

    def test_very_long_string_input(self):
        """Test functions handle very long string input."""
        long_string = "small_business" * 100
        assert get_category_group(long_string) == ""
        assert is_valid_business_category(long_string) is False
        assert get_description(long_string) == ""

    @pytest.mark.parametrize("numeric_input", [0, 1, 123, -1, 3.14])
    def test_numeric_input_handling(self, numeric_input):
        """Test functions handle numeric inputs properly."""
        assert get_category_group(numeric_input) == ""
        assert is_valid_business_category(numeric_input) is False
        assert get_description(numeric_input) == ""
        assert get_all_groups_for_code(numeric_input) == []

    @pytest.mark.parametrize("collection_input", [[], {}, set(), ["small_business"]])
    def test_collection_input_handling(self, collection_input):
        """Test functions handle collection inputs properly."""
        assert get_category_group(collection_input) == ""
        assert is_valid_business_category(collection_input) is False
        assert get_description(collection_input) == ""
        assert get_all_groups_for_code(collection_input) == []


class TestPerformance:
    """Test performance characteristics of the functions."""

    def test_constant_lookup_performance(self):
        """Test that lookups are efficient (using sets/dicts, not loops)."""
        # Test a reasonable number of lookups don't take too long
        
        start_time = time.time()
        for _ in range(1000):
            for code in ["small_business", "nonprofit", "government", "INVALID"]:
                is_valid_business_category(code)
                get_category_group(code)
                get_description(code)
                get_all_groups_for_code(code)
        end_time = time.time()
        
        # Should complete 16,000 function calls in well under a second
        assert (end_time - start_time) < 1.0, "Function calls should be efficient"

    def test_convenience_methods_performance(self):
        """Test that convenience methods are efficient."""
        start_time = time.time()
        for _ in range(1000):
            for code in ["small_business", "nonprofit", "woman_owned_business"]:
                is_small_business(code)
                is_minority_owned(code)
                is_women_owned(code)
                is_veteran_owned(code)
                is_government_entity(code)
                is_educational_institution(code)
                is_nonprofit_organization(code)
        end_time = time.time()
        
        # Should complete 21,000 function calls in well under a second
        assert (end_time - start_time) < 1.0, "Convenience methods should be efficient"


class TestSpecialCases:
    """Test specific business logic and special cases."""

    def test_8a_program_formatting(self):
        """Test 8(a) program participant has correct formatting."""
        assert is_valid_business_category("8a_program_participant") is True
        assert get_description("8a_program_participant") == "8(a) Program Participant"
        assert get_category_group("8a_program_participant") == "special_designations"

    def test_hubzone_description(self):
        """Test HUBZone has correct description."""
        assert get_description("historically_underutilized_business_firm") == "HUBZone Firm"

    def test_us_owned_vs_foreign_owned(self):
        """Test US-owned and foreign-owned are in special designations."""
        for code in ["us_owned_business", "foreign_owned", "foreign_government"]:
            assert get_category_group(code) == "special_designations"
            assert is_valid_business_category(code) is True

    def test_hospital_categories(self):
        """Test hospital categories are in special designations."""
        for code in ["hospital", "veterinary_hospital", "domestic_shelter"]:
            assert get_category_group(code) == "special_designations"
            assert is_valid_business_category(code) is True

    def test_top_level_categories_exist(self):
        """Test that top-level category codes exist in their own groups."""
        top_level_mappings = {
            "category_business": "category_business",
            "minority_owned_business": "minority_owned",
            "woman_owned_business": "women_owned",
            "veteran_owned_business": "veteran_owned",
            "special_designations": "special_designations",
            "nonprofit": "nonprofit",
            "higher_education": "higher_education",
            "government": "government",
            "individuals": "individuals",
        }
        
        for code, expected_group in top_level_mappings.items():
            assert is_valid_business_category(code) is True
            assert get_category_group(code) == expected_group
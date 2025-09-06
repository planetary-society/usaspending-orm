"""Recipient business category constants and categorizations for USASpending data.

This module contains all business category codes, groupings, and descriptions
as defined by the USASpending.gov API. Categories are organized hierarchically,
with some categories intentionally belonging to multiple groups.
"""

from __future__ import annotations

# Dictionary of business category groups with their codes and descriptions
# This mirrors the hierarchical structure used by the USASpending API
BUSINESS_CATEGORY_GROUPS = {
    "category_business": {
        "category_business": "Category Business",
        "small_business": "Small Business",
        "other_than_small_business": "Not Designated a Small Business",
        "corporate_entity_tax_exempt": "Corporate Entity Tax Exempt",
        "corporate_entity_not_tax_exempt": "Corporate Entity Not Tax Exempt",
        "partnership_or_limited_liability_partnership": "Partnership or Limited Liability Partnership",
        "sole_proprietorship": "Sole Proprietorship",
        "manufacturer_of_goods": "Manufacturer of Goods",
        "subchapter_s_corporation": "Subchapter S Corporation",
        "limited_liability_corporation": "Limited Liability Corporation",
    },
    "minority_owned": {
        "minority_owned_business": "Minority Owned Business",
        "alaskan_native_corporation_owned_firm": "Alaskan Native Corporation Owned Firm",
        "american_indian_owned_business": "American Indian Owned Business",
        "asian_pacific_american_owned_business": "Asian Pacific American Owned Business",
        "black_american_owned_business": "Black American Owned Business",
        "hispanic_american_owned_business": "Hispanic American Owned Business",
        "native_american_owned_business": "Native American Owned Business",
        "native_hawaiian_organization_owned_firm": "Native Hawaiian Organization Owned Firm",
        "subcontinent_asian_indian_american_owned_business": "Indian (Subcontinent) American Owned Business",
        "tribally_owned_firm": "Tribally Owned Firm",
        "other_minority_owned_business": "Other Minority Owned Business",
    },
    "women_owned": {
        "woman_owned_business": "Woman Owned Business",
        "women_owned_small_business": "Women Owned Small Business",
        "economically_disadvantaged_women_owned_small_business": "Economically Disadvantaged Women Owned Small Business",
        "joint_venture_women_owned_small_business": "Joint Venture Women Owned Small Business",
        "joint_venture_economically_disadvantaged_women_owned_small_business": "Joint Venture Economically Disadvantaged Women Owned Small Business",
    },
    "veteran_owned": {
        "veteran_owned_business": "Veteran Owned Business",
        "service_disabled_veteran_owned_business": "Service Disabled Veteran Owned Business",
    },
    "special_designations": {
        "special_designations": "Special Designations",
        "8a_program_participant": "8(a) Program Participant",
        "ability_one_program": "AbilityOne Program Participant",
        "dot_certified_disadvantaged_business_enterprise": "DoT Certified Disadvantaged Business Enterprise",
        "emerging_small_business": "Emerging Small Business",
        "federally_funded_research_and_development_corp": "Federally Funded Research and Development Corp",
        "historically_underutilized_business_firm": "HUBZone Firm",
        "labor_surplus_area_firm": "Labor Surplus Area Firm",
        "sba_certified_8a_joint_venture": "SBA Certified 8 a Joint Venture",
        "self_certified_small_disadvanted_business": "Self-Certified Small Disadvantaged Business",
        "small_agricultural_cooperative": "Small Agricultural Cooperative",
        "small_disadvantaged_business": "Small Disadvantaged Business",
        "community_developed_corporation_owned_firm": "Community Developed Corporation Owned Firm",
        "us_owned_business": "U.S.-Owned Business",
        "foreign_owned_and_us_located_business": "Foreign-Owned and U.S.-Incorporated Business",
        "foreign_owned": "Foreign Owned",
        "foreign_government": "Foreign Government",
        "international_organization": "International Organization",
        "domestic_shelter": "Domestic Shelter",
        "hospital": "Hospital",
        "veterinary_hospital": "Veterinary Hospital",
    },
    "nonprofit": {
        "nonprofit": "Nonprofit Organization",
        "foundation": "Foundation",
        "community_development_corporations": "Community Development Corporation",
    },
    "higher_education": {
        "higher_education": "Higher Education",
        "public_institution_of_higher_education": "Higher Education (Public)",
        "private_institution_of_higher_education": "Higher Education (Private)",
        "minority_serving_institution_of_higher_education": "Higher Education (Minority Serving)",
        "educational_institution": "Educational Institution",
        "school_of_forestry": "School of Forestry",
        "veterinary_college": "Veterinary College",
    },
    "government": {
        "government": "Government",
        "national_government": "U.S. National Government",
        "regional_and_state_government": "U.S. Regional/State Government",
        "regional_organization": "U.S. Regional Government Organization",
        "interstate_entity": "U.S. Interstate Government Entity",
        "us_territory_or_possession": "U.S. Territory Government",
        "local_government": "U.S. Local Government",
        "indian_native_american_tribal_government": "Native American Tribal Government",
        "authorities_and_commissions": "U.S. Government Authorities",
        "council_of_governments": "Council of Governments",
    },
    "individuals": {
        "individuals": "Individuals",
    },
}

# Categories that intentionally appear in multiple groups
# Based on USASpending API logic
OVERLAPPING_CATEGORIES = {
    # These appear in both category_business and special_designations
    "emerging_small_business": ["category_business", "special_designations"],
    "small_agricultural_cooperative": ["category_business", "special_designations"],
    "small_disadvantaged_business": ["category_business", "special_designations"],
    "self_certified_small_disadvanted_business": ["category_business", "special_designations"],
    # Women-owned small businesses also trigger small_business
    "women_owned_small_business": ["women_owned", "category_business"],
    "economically_disadvantaged_women_owned_small_business": ["women_owned", "category_business"],
    "joint_venture_women_owned_small_business": ["women_owned", "category_business"],
    "joint_venture_economically_disadvantaged_women_owned_small_business": ["women_owned", "category_business"],
}

# Create a complete mapping including overlaps
def _build_complete_descriptions():
    """Build complete description map including overlapping categories."""
    descriptions = {}
    for group_name, group_dict in BUSINESS_CATEGORY_GROUPS.items():
        for code, description in group_dict.items():
            if code not in descriptions:
                descriptions[code] = description
    return descriptions

BUSINESS_CATEGORY_DESCRIPTIONS = _build_complete_descriptions()

# Create frozensets for each group
CATEGORY_BUSINESS_CODES = frozenset(BUSINESS_CATEGORY_GROUPS["category_business"].keys())
MINORITY_OWNED_CODES = frozenset(BUSINESS_CATEGORY_GROUPS["minority_owned"].keys())
WOMEN_OWNED_CODES = frozenset(BUSINESS_CATEGORY_GROUPS["women_owned"].keys())
VETERAN_OWNED_CODES = frozenset(BUSINESS_CATEGORY_GROUPS["veteran_owned"].keys())
SPECIAL_DESIGNATIONS_CODES = frozenset(BUSINESS_CATEGORY_GROUPS["special_designations"].keys())
NONPROFIT_CODES = frozenset(BUSINESS_CATEGORY_GROUPS["nonprofit"].keys())
HIGHER_EDUCATION_CODES = frozenset(BUSINESS_CATEGORY_GROUPS["higher_education"].keys())
GOVERNMENT_CODES = frozenset(BUSINESS_CATEGORY_GROUPS["government"].keys())
INDIVIDUALS_CODES = frozenset(BUSINESS_CATEGORY_GROUPS["individuals"].keys())

# All valid business category codes
ALL_BUSINESS_CATEGORIES = frozenset(BUSINESS_CATEGORY_DESCRIPTIONS.keys())

# For backward compatibility - matches original frozenset structure
BUSINESS_CATEGORIES = ALL_BUSINESS_CATEGORIES


def get_category_group(code: str) -> str:
    """Get the primary category group name for a given business category code.
    
    For categories that belong to multiple groups, returns the first/primary group.
    Use get_all_groups_for_code() to get all groups.
    
    Args:
        code: Business category code (e.g., "small_business", "nonprofit")
        
    Returns:
        Primary category group name (e.g., "category_business", "nonprofit") or empty string if not found
    """
    if not isinstance(code, str):
        return ""
    
    # Check overlapping categories first for their primary group
    if code in OVERLAPPING_CATEGORIES:
        return OVERLAPPING_CATEGORIES[code][0]
    
    # Check each group
    for group_name, codes in BUSINESS_CATEGORY_GROUPS.items():
        if code in codes:
            return group_name
    return ""


def get_all_groups_for_code(code: str) -> list[str]:
    """Get all category groups that a business category code belongs to.
    
    Handles categories that belong to multiple groups (e.g., emerging_small_business).
    
    Args:
        code: Business category code
        
    Returns:
        List of all category group names the code belongs to
    """
    if not isinstance(code, str):
        return []
    
    groups = []
    
    # Check if it's an overlapping category
    if code in OVERLAPPING_CATEGORIES:
        return OVERLAPPING_CATEGORIES[code].copy()
    
    # Otherwise check each group
    for group_name, codes in BUSINESS_CATEGORY_GROUPS.items():
        if code in codes:
            groups.append(group_name)
    
    return groups


def is_valid_business_category(code: str) -> bool:
    """Check if a code is a valid business category.
    
    Args:
        code: Business category code to validate
        
    Returns:
        True if the code is valid, False otherwise
    """
    if not isinstance(code, str):
        return False
    return code in ALL_BUSINESS_CATEGORIES


def get_description(code: str) -> str:
    """Get the description for a given business category code.
    
    Args:
        code: Business category code
        
    Returns:
        Description string or empty string if not found
    """
    if not isinstance(code, str):
        return ""
    return BUSINESS_CATEGORY_DESCRIPTIONS.get(code, "")


# Convenience functions for common category checks
def is_small_business(code: str) -> bool:
    """Check if a code represents a small business.
    
    Args:
        code: Business category code
        
    Returns:
        True if the code represents a small business
    """
    if not isinstance(code, str):
        return False
    
    # Direct small business code
    if code == "small_business":
        return True
    
    # Women-owned small businesses
    if code in {
        "women_owned_small_business",
        "economically_disadvantaged_women_owned_small_business", 
        "joint_venture_women_owned_small_business",
        "joint_venture_economically_disadvantaged_women_owned_small_business",
    }:
        return True
    
    # Special designation small businesses
    if code in {
        "emerging_small_business",
        "self_certified_small_disadvanted_business",
        "small_agricultural_cooperative",
        "small_disadvantaged_business",
    }:
        return True
    
    return False


def is_minority_owned(code: str) -> bool:
    """Check if a code represents a minority-owned business.
    
    Args:
        code: Business category code
        
    Returns:
        True if the code represents a minority-owned business
    """
    if not isinstance(code, str):
        return False
    return code in MINORITY_OWNED_CODES


def is_women_owned(code: str) -> bool:
    """Check if a code represents a women-owned business.
    
    Args:
        code: Business category code
        
    Returns:
        True if the code represents a women-owned business
    """
    if not isinstance(code, str):
        return False
    return code in WOMEN_OWNED_CODES


def is_veteran_owned(code: str) -> bool:
    """Check if a code represents a veteran-owned business.
    
    Args:
        code: Business category code
        
    Returns:
        True if the code represents a veteran-owned business
    """
    if not isinstance(code, str):
        return False
    return code in VETERAN_OWNED_CODES


def is_government_entity(code: str) -> bool:
    """Check if a code represents a government entity.
    
    Args:
        code: Business category code
        
    Returns:
        True if the code represents a government entity
    """
    if not isinstance(code, str):
        return False
    return code in GOVERNMENT_CODES


def is_educational_institution(code: str) -> bool:
    """Check if a code represents an educational institution.
    
    Args:
        code: Business category code
        
    Returns:
        True if the code represents an educational institution
    """
    if not isinstance(code, str):
        return False
    return code in HIGHER_EDUCATION_CODES


def is_nonprofit_organization(code: str) -> bool:
    """Check if a code represents a nonprofit organization.
    
    Args:
        code: Business category code
        
    Returns:
        True if the code represents a nonprofit organization
    """
    if not isinstance(code, str):
        return False
    return code in NONPROFIT_CODES
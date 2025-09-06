"""Award type constants and categorizations for USASpending data.

This module contains all award type codes, groupings, and descriptions
as defined by the USASpending.gov API.
"""

from __future__ import annotations

# Dictionary of award type groups with their codes and descriptions
# This is the single source of truth for award type categorization
AWARD_TYPE_GROUPS = {
    "contracts": {
        "A": "BPA Call",
        "B": "Purchase Order",
        "C": "Delivery Order",
        "D": "Definitive Contract",
    },
    "loans": {"07": "Direct Loan", "08": "Guaranteed/Insured Loan"},
    "idvs": {
        "IDV_A": "GWAC Government Wide Acquisition Contract",
        "IDV_B": "IDC Multi-Agency Contract, Other Indefinite Delivery Contract",
        "IDV_B_A": "IDC Indefinite Delivery Contract / Requirements",
        "IDV_B_B": "IDC Indefinite Delivery Contract / Indefinite Quantity",
        "IDV_B_C": "IDC Indefinite Delivery Contract / Definite Quantity",
        "IDV_C": "FSS Federal Supply Schedule",
        "IDV_D": "BOA Basic Ordering Agreement",
        "IDV_E": "BPA Blanket Purchase Agreement",
    },
    "grants": {
        "02": "Block Grant",
        "03": "Formula Grant",
        "04": "Project Grant",
        "05": "Cooperative Agreement",
    },
    "direct_payments": {
        "06": "Direct Payment for Specified Use",
        "10": "Direct Payment with Unrestricted Use",
    },
    "other_assistance": {
        "09": "Insurance",
        "11": "Other Financial Assistance",
        "-1": "Not Specified",
    },
}

# Create a flattened map for easy description lookups
AWARD_TYPE_DESCRIPTIONS = {
    code: description
    for group in AWARD_TYPE_GROUPS.values()
    for code, description in group.items()
}

# Regenerate frozensets from this single source of truth
CONTRACT_CODES = frozenset(AWARD_TYPE_GROUPS["contracts"].keys())
IDV_CODES = frozenset(AWARD_TYPE_GROUPS["idvs"].keys())
LOAN_CODES = frozenset(AWARD_TYPE_GROUPS["loans"].keys())
GRANT_CODES = frozenset(AWARD_TYPE_GROUPS["grants"].keys())
DIRECT_PAYMENT_CODES = frozenset(AWARD_TYPE_GROUPS["direct_payments"].keys())
OTHER_CODES = frozenset(AWARD_TYPE_GROUPS["other_assistance"].keys())

# All valid award type codes
ALL_AWARD_CODES = (
    CONTRACT_CODES
    | IDV_CODES
    | LOAN_CODES
    | GRANT_CODES
    | DIRECT_PAYMENT_CODES
    | OTHER_CODES
)


def get_category_for_code(code: str) -> str:
    """Get the category name for a given award type code.
    
    Args:
        code: Award type code (e.g., "A", "02", "IDV_A")
        
    Returns:
        Category name (e.g., "contracts", "grants", "idvs") or empty string if not found
    """
    if not isinstance(code, str):
        return ""
    for category_name, codes in AWARD_TYPE_GROUPS.items():
        if code in codes:
            return category_name
    return ""


def is_valid_award_type(code: str) -> bool:
    """Check if a code is a valid award type.
    
    Args:
        code: Award type code to validate
        
    Returns:
        True if the code is valid, False otherwise
    """
    if not isinstance(code, str):
        return False
    return code in ALL_AWARD_CODES


def get_description(code: str) -> str:
    """Get the description for a given award type code.
    
    Args:
        code: Award type code
        
    Returns:
        Description string or empty string if not found
    """
    if not isinstance(code, str):
        return ""
    return AWARD_TYPE_DESCRIPTIONS.get(code, "")
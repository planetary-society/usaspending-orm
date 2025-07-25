from __future__ import annotations
from dataclasses import dataclass
from typing import Optional



@dataclass
class Config:
    """Configuration for USASpending client.
    
    Attributes:
        base_url: Base URL for USASpending API
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        retry_backoff: Backoff multiplier for retries
        rate_limit_calls: Number of calls allowed per period
        rate_limit_period: Period in seconds for rate limiting
        cache_enabled: Enable/disable caching
        cache_dir: Directory for file-based cache
        cache_ttl: Cache time-to-live in seconds
        user_agent: User agent string for requests
        logging_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        debug_mode: Enable verbose debug logging
        log_file: Optional file path for log output
    """
    
    base_url: str = "https://api.usaspending.gov/api/v2"
    user_agent: str = "usaspendingapi-python/0.1.0"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    rate_limit_calls: int = 30
    rate_limit_period: int = 1
    
    # Caching via cachier
    cache_enabled: bool = True
    cache_dir: str = ".usaspending_cache"
    cache_ttl: int = 604800  # 1 week
    
    
    # Logging configuration
    logging_level: str = "DEBUG"
    debug_mode: bool = True
    log_file: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.rate_limit_calls <= 0:
            raise ValueError("rate_limit_calls must be positive")
        if self.logging_level.upper() not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError("logging_level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")

# In src/usaspendingapi/config.py

AWARD_TYPE_GROUPS = {
    "contracts": {
        "A": "BPA Call",
        "B": "Purchase Order",
        "C": "Delivery Order",
        "D": "Definitive Contract"
    },
    "loans": {
        "07": "Direct Loan",
        "08": "Guaranteed/Insured Loan"
    },
    "idvs": {
        "IDV_A": "GWAC Government Wide Acquisition Contract",
        "IDV_B": "IDC Multi-Agency Contract, Other Indefinite Delivery Contract",
        "IDV_B_A": "IDC Indefinite Delivery Contract / Requirements",
        "IDV_B_B": "IDC Indefinite Delivery Contract / Indefinite Quantity",
        "IDV_B_C": "IDC Indefinite Delivery Contract / Definite Quantity",
        "IDV_C": "FSS Federal Supply Schedule",
        "IDV_D": "BOA Basic Ordering Agreement",
        "IDV_E": "BPA Blanket Purchase Agreement"
    },
    "grants": {
        "02": "Block Grant",
        "03": "Formula Grant",
        "04": "Project Grant",
        "05": "Cooperative Agreement"
    },
    "direct_payments": {
        "06": "Direct Payment for Specified Use",
        "10": "Direct Payment with Unrestricted Use"
    },
    "other_assistance": {
        "09": "Insurance",
        "11": "Other Financial Assistance",
        "-1": "Not Specified"
    }
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

# Dictionary of Business Categories that pair them with their human readable name
# Taken directly from USASpending API source
BUSINESS_CATEGORIES = frozenset({
    # Category Business
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
    # Minority Owned Business
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
    # Women Owned Business
    "woman_owned_business": "Woman Owned Business",
    "women_owned_small_business": "Women Owned Small Business",
    "economically_disadvantaged_women_owned_small_business": "Economically Disadvantaged Women Owned Small Business",
    "joint_venture_women_owned_small_business": "Joint Venture Women Owned Small Business",
    "joint_venture_economically_disadvantaged_women_owned_small_business": "Joint Venture Economically Disadvantaged Women Owned Small Business",
    # Veteran Owned Business
    "veteran_owned_business": "Veteran Owned Business",
    "service_disabled_veteran_owned_business": "Service Disabled Veteran Owned Business",
    # Special Designations
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
    # Nonprofit
    "nonprofit": "Nonprofit Organization",
    "foundation": "Foundation",
    "community_development_corporations": "Community Development Corporation",
    # Higher education
    "higher_education": "Higher Education",
    "public_institution_of_higher_education": "Higher Education (Public)",
    "private_institution_of_higher_education": "Higher Education (Private)",
    "minority_serving_institution_of_higher_education": "Higher Education (Minority Serving)",
    "educational_institution": "Educational Institution",
    "school_of_forestry": "School of Forestry",
    "veterinary_college": "Veterinary College",
    # Government
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
    # Individuals
    "individuals": "Individuals",
})

# List of CFO CGACS (Common Government-wide Accounting Classification)
# for all U.S. government agencies.
CFO_CGACS_MAPPING = {
    "012": "Department of Agriculture",
    "013": "Department of Commerce",
    "097": "Department of Defense",
    "091": "Department of Education",
    "089": "Department of Energy",
    "075": "Department of Health and Human Services",
    "070": "Department of Homeland Security",
    "086": "Department of Housing and Urban Development",
    "015": "Department of Justice",
    "1601": "Department of Labor",
    "019": "Department of State",
    "014": "Department of the Interior",
    "020": "Department of the Treasury",
    "069": "Department of Transportation",
    "036": "Department of Veterans Affairs",
    "068": "Environmental Protection Agency",
    "047": "General Services Administration",
    "080": "National Aeronautics and Space Administration",
    "049": "National Science Foundation",
    "031": "Nuclear Regulatory Commission",
    "024": "Office of Personnel Management",
    "073": "Small Business Administration",
    "028": "Social Security Administration",
    "072": "Agency for International Development",
}
CFO_CGACS = list(CFO_CGACS_MAPPING.keys())
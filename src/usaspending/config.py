from __future__ import annotations
from datetime import timedelta
from typing import Optional
from usaspending.logging_config import USASpendingLogger
from usaspending.exceptions import ConfigurationError
import cachier

logger = USASpendingLogger.get_logger(__name__)



class _Config:
    """
    A container for all library configuration settings.
    Do not instantiate this class directly. Instead, import and use the global `config` object.
    """
    def __init__(self):
        # Default settings are defined here as instance attributes
        self.base_url: str = "https://api.usaspending.gov/api/v2"
        self.user_agent: str = "usaspendingapi-python/0.1.0"
        self.timeout: int = 30
        self.max_retries: int = 3
        self.retry_delay: float = 1.0
        self.retry_backoff: float = 2.0
        self.rate_limit_calls: int = 30
        self.rate_limit_period: int = 1

        # Caching via cachier
        self.cache_enabled: bool = True
        self.cache_backend: str = 'pickle' # Default file-based backend for cachier
        self.cache_dir: str = ".usaspending_cache"
        self.cache_ttl: timedelta = timedelta(weeks=1)

        # Logging configuration
        self.logging_level: str = "DEBUG"
        self.debug_mode: bool = True
        self.log_file: Optional[str] = None

        # Apply the initial default settings when the object is created
        self._apply_cachier_settings()

    def configure(self, **kwargs):
        """
        Updates configuration settings and applies them across the library.

        This is the primary method for users to modify the library's behavior.
        Any keyword argument passed will overwrite the existing configuration value.

        Args:
            **kwargs: Configuration keys and their new values.
        
        Raises:
            ValueError: If any provided configuration value is invalid.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == 'cache_ttl' and isinstance(value, (int, float)):
                    self.cache_ttl = timedelta(seconds=value)
                else:
                    setattr(self, key, value)
            else:
                logger.warning(f"Warning: Unknown configuration key '{key}' was ignored.")

        self.validate()
        self._apply_cachier_settings()

    def _apply_cachier_settings(self):
        """Applies the current caching settings to the cachier library."""
        if self.cache_enabled:
            if self.cache_backend == 'file':
                cache_backend = 'pickle'  # cachier uses 'pickle' for file caching
            else:
                cache_backend = self.cache_backend
            cachier.set_global_params(
                stale_after=self.cache_ttl,
                cache_dir=self.cache_dir,
                backend=cache_backend
            )
            cachier.enable_caching()
        else:
            cachier.disable_caching()

    def _apply_logging_settings(self):
        """Applies the current logging settings to the logger."""
        # This is the logic moved from your client file
        USASpendingLogger.configure(
            level=self.logging_level,
            debug_mode=self.debug_mode,
            log_file=self.log_file,
        )

    def validate(self) -> None:
        """Validate the current configuration values."""
        if self.timeout <= 0:
            raise ConfigurationError("timeout must be positive")
        if self.max_retries < 0:
            raise ConfigurationError("max_retries must be non-negative")
        if self.rate_limit_calls <= 0:
            raise ConfigurationError("rate_limit_calls must be positive")
        
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.logging_level.upper() not in valid_log_levels:
            raise ConfigurationError(f"logging_level must be one of: {valid_log_levels}")
        
        valid_backends = {'file', 'memory'}
        if self.cache_enabled and (self.cache_backend not in valid_backends):
            raise ConfigurationError(f"cache_backend must be one of: {valid_backends}")

# Global configuration object
# This is the single instance that should be used throughout the library
config = _Config()


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
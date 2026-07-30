"""Award type categories: the single source of truth for award-type knowledge.

USASpending groups awards into six categories, and the library needs a
different projection of that grouping in almost every layer: the factory needs
the model class, the search builder needs the API count key and the field set,
the resource layer needs the convenience-method name, and the download layer
needs the bulk-download type.

Each of those projections used to be hand-maintained in a separate dict or
if/elif chain across ``models/``, ``queries/`` and ``resources/``, which meant a
change had to be applied consistently in several places at once.
:data:`AWARD_CATEGORIES` holds them all in one table instead, and every other
module reads from it.

Adding a category is therefore mostly a matter of adding one
:class:`AwardCategory` entry. Two things still live outside this table because
they are hand-written code rather than data: the matching convenience method on
``SearchQueryBuilder`` (whose name must equal ``group``), and, for a category
with its own model, the subclass plus its ``_download_type``. The invariant
tests in ``tests/models/test_award_category_registry.py`` fail if either is
missing, so the omission surfaces immediately.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType

from ..exceptions import ValidationError


@dataclass(frozen=True)
class AwardCategory:
    """One award-type category and every projection the library needs of it.

    Attributes:
        group: Plural category name used by :data:`AWARD_TYPE_GROUPS` and by the
            award-search field and count logic (for example ``"contracts"``).
        singular: Value the API reports in an award's ``category`` field, and the
            key the model factory dispatches on (for example ``"contract"``).
        api_count_key: Key this category appears under in the
            ``spending_by_award_count`` response. Mostly equal to ``group``, but
            ``other_assistance`` is reported as ``other``.
        search_fields_model: Name of the model whose ``SEARCH_FIELDS`` this
            category requests. Categories without a dedicated model still need a
            field set, so direct payments and other assistance use ``Grant``.
        model_name: Name of the specialized ``Award`` subclass for this
            category, or ``None`` when the base ``Award`` is used.
        download_type: Value the bulk-download API expects, or ``None`` when the
            category does not support downloads.
        types: Mapping of award type code to human-readable description.
    """

    group: str
    singular: str
    api_count_key: str
    search_fields_model: str
    model_name: str | None
    download_type: str | None
    types: Mapping[str, str]

    def __post_init__(self) -> None:
        """Freeze the supplied code mapping.

        Entries below are written as plain dict literals for readability; making
        them immutable here means no future entry can forget to.
        """
        object.__setattr__(self, "types", MappingProxyType(dict(self.types)))

    @cached_property
    def codes(self) -> frozenset[str]:
        """Award type codes belonging to this category.

        Cached because this is read per result row while transforming a search
        response, and the registry is static for the life of the process.
        """
        return frozenset(self.types)

    @property
    def has_dedicated_model(self) -> bool:
        """Whether this category has a specialized ``Award`` subclass."""
        return self.model_name is not None


# Declaration order is meaningful: several call sites resolve a set of codes to
# the first matching category, so this order defines that precedence.
AWARD_CATEGORIES: tuple[AwardCategory, ...] = (
    AwardCategory(
        group="contracts",
        singular="contract",
        api_count_key="contracts",
        search_fields_model="Contract",
        model_name="Contract",
        download_type="contract",
        types={
            "A": "BPA Call",
            "B": "Purchase Order",
            "C": "Delivery Order",
            "D": "Definitive Contract",
        },
    ),
    AwardCategory(
        group="loans",
        singular="loan",
        api_count_key="loans",
        search_fields_model="Loan",
        model_name="Loan",
        download_type="assistance",
        types={
            "07": "Direct Loan",
            "08": "Guaranteed/Insured Loan",
            "F003": "Direct Loan",
            "F004": "Loan Guarantee",
        },
    ),
    AwardCategory(
        group="idvs",
        singular="idv",
        api_count_key="idvs",
        search_fields_model="IDV",
        model_name="IDV",
        download_type="idv",
        types={
            "IDV_A": "GWAC Government Wide Acquisition Contract",
            "IDV_B": "IDC Multi-Agency Contract, Other Indefinite Delivery Contract",
            "IDV_B_A": "IDC Indefinite Delivery Contract / Requirements",
            "IDV_B_B": "IDC Indefinite Delivery Contract / Indefinite Quantity",
            "IDV_B_C": "IDC Indefinite Delivery Contract / Definite Quantity",
            "IDV_C": "FSS Federal Supply Schedule",
            "IDV_D": "BOA Basic Ordering Agreement",
            "IDV_E": "BPA Blanket Purchase Agreement",
        },
    ),
    AwardCategory(
        group="grants",
        singular="grant",
        api_count_key="grants",
        search_fields_model="Grant",
        model_name="Grant",
        download_type="assistance",
        types={
            "02": "Block Grant",
            "03": "Formula Grant",
            "04": "Project Grant",
            "05": "Cooperative Agreement",
            "F001": "Grant",
            "F002": "Cooperative Agreement",
        },
    ),
    AwardCategory(
        group="direct_payments",
        singular="direct_payment",
        api_count_key="direct_payments",
        search_fields_model="Grant",
        model_name=None,
        download_type=None,
        types={
            "06": "Direct Payment for Specified Use",
            "10": "Direct Payment with Unrestricted Use",
            "F006": "Direct Payment for Specified Use",
            "F007": "Direct Payment with Unrestricted Use",
        },
    ),
    AwardCategory(
        group="other_assistance",
        singular="other_assistance",
        api_count_key="other",
        search_fields_model="Grant",
        model_name=None,
        download_type=None,
        types={
            "09": "Insurance",
            "11": "Other Financial Assistance",
            "-1": "Not Specified",
            "F005": "Indemnity / Insurance (non-loan)",
            "F008": "Asset Forfeiture / Equitable Sharing",
            "F009": "Sale, Exchange, or Donation of Property and Goods",
            "F010": "Other Financial Assistance",
        },
    ),
)

_BY_GROUP: Mapping[str, AwardCategory] = MappingProxyType(
    {category.group: category for category in AWARD_CATEGORIES}
)
_BY_CODE: Mapping[str, AwardCategory] = MappingProxyType(
    {code: category for category in AWARD_CATEGORIES for code in category.types}
)
_BY_SINGULAR: Mapping[str, AwardCategory] = MappingProxyType(
    {category.singular: category for category in AWARD_CATEGORIES}
)
_BY_API_COUNT_KEY: Mapping[str, AwardCategory] = MappingProxyType(
    {category.api_count_key: category for category in AWARD_CATEGORIES}
)

# Award type groups as a plain nested dict, derived from the registry above.
# This is the historical shape of this module's public data.
AWARD_TYPE_GROUPS = {category.group: dict(category.types) for category in AWARD_CATEGORIES}

# Flattened map for description lookups.
AWARD_TYPE_DESCRIPTIONS = {
    code: description
    for category in AWARD_CATEGORIES
    for code, description in category.types.items()
}

# Lowercased descriptions, so resolving a description is a lookup rather than a
# scan over every description in the registry.
_BY_DESCRIPTION: Mapping[str, AwardCategory] = MappingProxyType(
    {
        description.lower(): category
        for category in AWARD_CATEGORIES
        for description in category.types.values()
    }
)

# Download types the bulk-download API accepts. Award.download() validates
# against this before resolving the matching DownloadResource method by name.
DOWNLOAD_TYPES = frozenset(
    category.download_type for category in AWARD_CATEGORIES if category.download_type
)

# Per-category code sets, derived from the registry.
CONTRACT_CODES = _BY_GROUP["contracts"].codes
IDV_CODES = _BY_GROUP["idvs"].codes
LOAN_CODES = _BY_GROUP["loans"].codes
GRANT_CODES = _BY_GROUP["grants"].codes
DIRECT_PAYMENT_CODES = _BY_GROUP["direct_payments"].codes
OTHER_CODES = _BY_GROUP["other_assistance"].codes

# All valid award type codes.
ALL_AWARD_CODES = frozenset(_BY_CODE)


def category_for_singular(singular: str) -> AwardCategory | None:
    """Look up a category by its singular name.

    Args:
        singular: Singular category name such as ``"contract"``, as reported in
            an award's ``category`` field and returned by :func:`get_award_group`.

    Returns:
        Optional[AwardCategory]: The category, or None if the name is unknown.
    """
    return _BY_SINGULAR.get(singular)


def category_for_api_count_key(api_count_key: str) -> AwardCategory | None:
    """Look up a category by the key the count endpoint reports it under.

    Args:
        api_count_key: Key from a ``spending_by_award_count`` response.

    Returns:
        Optional[AwardCategory]: The category, or None if the key is unknown.
    """
    return _BY_API_COUNT_KEY.get(api_count_key)


def categories_for_codes(codes: frozenset[str] | set[str]) -> list[AwardCategory]:
    """Return every category represented in a set of award type codes.

    Args:
        codes: Award type codes, typically taken from a query's filters.

    Returns:
        list[AwardCategory]: Matching categories in declaration order.
    """
    requested = frozenset(codes)
    return [category for category in AWARD_CATEGORIES if requested & category.codes]


def category_for_exclusive_codes(codes: frozenset[str] | set[str]) -> AwardCategory | None:
    """Return the dedicated-model category that fully contains ``codes``.

    Used when a query filtered to a single category needs to tell the model
    factory which subclass to build, even though the API response may not carry
    explicit type information.

    Args:
        codes: Award type codes, typically taken from a query's filters.

    Returns:
        Optional[AwardCategory]: The category containing every supplied code, or
        None when ``codes`` is empty or spans more than one category.
    """
    if not codes:
        return None

    requested = frozenset(codes)
    for category in AWARD_CATEGORIES:
        if category.has_dedicated_model and requested <= category.codes:
            return category
    return None


def is_valid_award_type(code: str) -> bool:
    """Check if a code is a valid award type.

    Args:
        code: Award type code to validate.

    Returns:
        bool: True if the code is valid, False otherwise.
    """
    if not isinstance(code, str):
        return False
    return code in ALL_AWARD_CODES


def validate_award_type_codes(codes: Iterable[str]) -> None:
    """Raise if any supplied code is not a valid award type code.

    The award-search and transaction-search builders both accept caller-supplied
    codes and share this check, so the error message cannot drift between them.

    Args:
        codes: Award type codes to validate.

    Raises:
        ValidationError: If any code is not in :data:`ALL_AWARD_CODES`, naming
            the offending codes and listing the valid ones.
    """
    invalid_codes = [code for code in codes if code not in ALL_AWARD_CODES]
    if invalid_codes:
        raise ValidationError(
            f"Invalid award type code(s): {', '.join(sorted(invalid_codes))}. "
            f"Valid codes are: {', '.join(sorted(ALL_AWARD_CODES))}"
        )


def get_description(code: str) -> str:
    """Get the description for a given award type code.

    Args:
        code: Award type code.

    Returns:
        str: Description string or empty string if not found.
    """
    if not isinstance(code, str):
        return ""
    return AWARD_TYPE_DESCRIPTIONS.get(code, "")


def get_award_group(value: str) -> str:
    """Get singular group name from any identifier.

    Accepts a group name, type code, or description. Case-insensitive.
    Only returns names for the award types that have dedicated model classes.

    Args:
        value: Any of:
            - Group name (e.g., "contracts", "loans", "contract", "loan")
            - Type code (e.g., "D", "07", "IDV_A")
            - Description (e.g., "Direct Loan", "BPA Call")

    Returns:
        str: Singular group name ("contract", "grant", "idv", "loan")
            or empty string if not found or not a specialized type.
    """
    if not isinstance(value, str) or not value.strip():
        return ""

    normalized = value.strip()
    lowered = normalized.lower()

    category = (
        _BY_GROUP.get(lowered)
        or _BY_SINGULAR.get(lowered)
        or _BY_CODE.get(normalized.upper())
        or _BY_DESCRIPTION.get(lowered)
    )

    if category is None or not category.has_dedicated_model:
        return ""
    return category.singular

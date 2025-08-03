from typing import List, Any, Optional, Set
from datetime import datetime
import re
import yaml
from pathlib import Path

from ..config import BUSINESS_CATEGORIES
from titlecase import titlecase
from ..logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)


def to_date(date_string: str) -> Optional[datetime]:
    """Convert date string to datetime object.

    Args:
        date_string: Date string in YYYY-MM-DD format

    Returns:
        datetime object or None if parsing fails
    """
    try:
        if not date_string:
            return None
        # Parse date string to datetime object
        return datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Could not parse date string: {date_string}")
        # If parsing fails, return None
        return None


def round_to_millions(amount: float) -> str:
    """Format money amount with commas and 2 decimal places, display as millions or billions based on the amount."""
    if amount is None:
        return "$0.00"
    if amount >= 1_000_000_000:
        return "${:,.1f} billion".format(amount / 1_000_000_000)
    elif amount >= 10_000_000:
        return "${:,.1f} million".format(amount / 1_000_000)
    elif amount >= 1_000_000:
        return "${:,.1f} million".format(amount / 1_000_000)
    return "${:,.2f}".format(amount)


def current_fiscal_year() -> int:
    """Returns the current fiscal year"""
    current_date = datetime.now()
    current_month = datetime.now().month
    if current_month < 10:
        return current_date.year
    else:
        return current_date.year + 1


def get_past_fiscal_years(num_years: int = 3) -> List[int]:
    """
    Get the past N fiscal years.
    In the US, the federal fiscal year starts on October 1.

    Args:
        num_years: Number of past fiscal years to return

    Returns:
        List of fiscal years, starting with the most recent
    """
    current_date = datetime.now()
    current_year = current_date.year

    # We always want the last completed fiscal year
    if current_date.month < 10:
        current_fiscal_year = current_year - 1
    else:
        current_fiscal_year = current_year

    return [current_fiscal_year - i for i in range(num_years)]


def to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return x


# --- Configuration ---
# Set of acronyms and initialisms to always keep uppercase.
# This could be loaded from a config file or environment variables in a larger application.
DEFAULT_KEEP_UPPERCASE: Set[str] = {
    # Common Business / Legal
    "LLC",
    "INC",
    "LLP",
    "LTD",
    "L.L.C.",
    "I.N.C.",
    "L.L.P.",
    "L.T.D.",
    # Geographical / Governmental
    "USA",
    "US",
    "UK",
    # Organizations / Agencies
    "NASA",
    "ESA",
    "JAXA",
    # NASA Facilities & Major Programs (add more as needed)
    "JPL",  # Jet Propulsion Laboratory
    "JSC",  # Johnson Space Center
    "KSC",  # Kennedy Space Center
    "GSFC",  # Goddard Space Flight Center
    "MSFC",  # Marshall Space Flight Center
    "ARC",  # Ames Research Center
    "GRC",  # Glenn Research Center
    "LARC",  # Langley Research Center (or LaRC - handled by case-insensitive check)
    "AFRC",  # Armstrong Flight Research Center
    "SSC",  # Stennis Space Center
    "ISS",  # International Space Station
    "JWST",  # James Webb Space Telescope
    # Specific examples from user input
    "CSOS",
    "CL",
    "FL",
    "FPRW",
    "PADF",
    "ICAT",
    "ICATEQ",
    "AC"  # For A.C. style
    # Add other common contract/technical acronyms as needed
    "RFQ",
    "RFP",
    "SOW",
    "CDR",
    "PDR",
    "QA",
    "PI",
    "COTS",
}

# Maximum length for parenthesized text to be uppercased
PAREN_UPPERCASE_MAX_LEN: int = 9  # Fewer than 10 characters

# --- Helper Function ---


def smart_sentence_case(
    text: Optional[str],
    paren_max_len: int = PAREN_UPPERCASE_MAX_LEN,
) -> str:
    """
    Converts an uppercase string to sentence case, preserving specified acronyms
    and short parenthesized text in uppercase.

    Rules:
    1. Converts the text to lowercase as a base.
    2. Capitalizes the first letter of the resulting string.
    3. Keeps special cases from YAML configuration in proper case.
    4. Keeps text within parentheses uppercase if its length is less than
       paren_max_len + 1 characters.
    5. Handles standard punctuation like apostrophes correctly.

    Args:
        text: The input string, expected to be mostly uppercase.
              Can be None or empty.
        paren_max_len: The maximum character length of text inside parentheses
                       to be kept uppercase. Defaults to PAREN_UPPERCASE_MAX_LEN.

    Returns:
        The processed string in smart sentence case, or an empty string if
        the input was None or empty.
    """
    # Use the new TextFormatter class
    return TextFormatter.to_sentence_case(text, paren_max_len)


class TextFormatter:
    """Unified text formatting utility class for sentence and title case conversions."""
    
    _special_cases_cache = None
    
    @classmethod
    def _load_special_cases(cls):
        """Load and cache special cases from YAML file."""
        if cls._special_cases_cache is None:
            yaml_path = Path(__file__).parent / "special_cases.yaml"
            try:
                with open(yaml_path, "r") as f:
                    cls._special_cases_cache = yaml.safe_load(f) or []
            except FileNotFoundError:
                logger.warning(f"Special cases file not found: {yaml_path}")
                cls._special_cases_cache = []
            except Exception as e:
                logger.error(f"Error loading special cases: {e}")
                cls._special_cases_cache = []
        return cls._special_cases_cache
    
    @classmethod
    def _get_special_cases_set(cls):
        """Get special cases as a set for fast lookups."""
        special_cases = cls._load_special_cases()
        return {case.upper() for case in special_cases if isinstance(case, str)}
    
    @classmethod
    def _split_word_punctuation(cls, word):
        """Split a word into clean word and trailing punctuation."""
        if not word:
            return word, ""
            
        trailing_punct = ""
        clean_word = word

        # Handle contractions separately
        if "'" in word:
            # For words like "NASA's", split at apostrophe
            parts = word.split("'", 1)
            if len(parts) == 2:
                clean_word = parts[0]
                trailing_punct = "'" + parts[1]
            else:
                clean_word = word
                trailing_punct = ""
        else:
            # Find where the alphanumeric part ends
            i = len(word) - 1
            while i >= 0 and not word[i].isalnum():
                i -= 1
            if i >= 0:
                clean_word = word[: i + 1]
                trailing_punct = word[i + 1 :]
            else:
                # All punctuation, no alphanumeric chars
                clean_word = word
                trailing_punct = ""
                
        return clean_word, trailing_punct
    
    @classmethod
    def _preserve_special_case(cls, word):
        """Check if word should be preserved as special case, return preserved version or None."""
        if not isinstance(word, str):
            return None
            
        # If the word is enclosed in parentheses, preserve the case inside
        if word.startswith("(") and word.endswith(")"):
            return word

        # Load special cases YAML file
        special_cases = cls._load_special_cases()
        clean_word, trailing_punct = cls._split_word_punctuation(word)

        # Check for case-insensitive match
        for special_word in special_cases:
            # Ensure special_word is a string
            if not isinstance(special_word, str):
                continue

            # First try exact match with full word (including punctuation)
            if word.lower() == special_word.lower():
                return special_word

            # Then try match with clean word
            if clean_word.lower() == special_word.lower():
                return special_word + trailing_punct

            # Also try if special_word has punctuation that matches
            if (
                special_word.endswith(".")
                and clean_word.lower() == special_word[:-1].lower()
            ):
                # Word like "inc" matching "Inc."
                return special_word + trailing_punct

        return None
    
    @classmethod
    def to_sentence_case(cls, text: Optional[str], paren_max_len: int = 9) -> str:
        """
        Convert text to sentence case, preserving special cases from YAML.
        
        True sentence case: only capitalize first word of sentences and special cases.
        Includes progressive acronym expansion for parenthetical content.
        
        Args:
            text: Input text to convert
            paren_max_len: Max length for parenthesized text to keep uppercase
            
        Returns:
            Text in sentence case with special cases preserved
        """
        if not text:
            return ""

        try:
            # Start with lowercase
            processed_text = text.lower()
            special_cases_set = cls._get_special_cases_set()
            
            # Small words to ignore in acronym expansion
            SMALL_WORDS = r'\b(a|an|and|as|at|but|by|en|for|if|in|of|on|or|the|to|v\.?|via|vs\.?)\b'
            
            # First, handle acronym expansion for parenthetical content
            def expand_acronyms(match):
                full_match = match.group(0)
                paren_content = match.group(1)
                
                # If content is too long, handle normally
                if len(paren_content) > paren_max_len:
                    return full_match
                
                # Always try acronym expansion first, even for known acronyms
                # This allows us to capitalize the expanded form
                
                # Try progressive acronym expansion
                start_pos = match.start()
                text_before = processed_text[:start_pos].strip()
                
                if text_before:
                    # Split into words
                    words_before = re.findall(r'\b\w+\b', text_before)
                    acronym_letters = [c.lower() for c in paren_content if c.isalpha()]
                    
                    if len(acronym_letters) > 0:
                        # Try direct match first
                        if len(words_before) >= len(acronym_letters):
                            last_n_words = words_before[-len(acronym_letters):]
                            if [w[0].lower() for w in last_n_words] == acronym_letters:
                                # Mark these words for capitalization
                                cls._acronym_expansion_words = getattr(cls, '_acronym_expansion_words', set())
                                cls._acronym_expansion_words.update(last_n_words)
                            else:
                                # If direct match failed, try skipping small words
                                # Filter out small words
                                content_words = []
                                for word in words_before:
                                    if not re.match(SMALL_WORDS, word, re.IGNORECASE):
                                        content_words.append(word)
                                
                                if len(content_words) >= len(acronym_letters):
                                    last_n_content = content_words[-len(acronym_letters):]
                                    if [w[0].lower() for w in last_n_content] == acronym_letters:
                                        # Mark these words for capitalization
                                        cls._acronym_expansion_words = getattr(cls, '_acronym_expansion_words', set())
                                        cls._acronym_expansion_words.update(last_n_content)
                
                # Return uppercase parenthetical if short enough
                if len(paren_content) <= paren_max_len:
                    return f"({paren_content.upper()})"
                else:
                    return full_match
            
            # Initialize acronym expansion tracking
            cls._acronym_expansion_words = set()
            
            # Apply acronym expansion
            processed_text = re.sub(r'\(([^)]+)\)', expand_acronyms, processed_text)
            
            # Handle special cases and sentence boundaries
            def word_replacer(match):
                word = match.group(1)
                word_start = match.start()
                
                # Check if word should be capitalized due to acronym expansion
                if hasattr(cls, '_acronym_expansion_words') and word in cls._acronym_expansion_words:
                    return word.capitalize()
                
                # Check if word is a special case from YAML
                if word.upper() in special_cases_set:
                    for special_case in cls._load_special_cases():
                        if isinstance(special_case, str) and word.upper() == special_case.upper():
                            return special_case
                
                # Check if this is the start of a sentence (beginning or after . ! ? + space)
                if word_start == 0:
                    return word.capitalize()
                
                # Look for sentence boundaries (punctuation + one or more spaces)
                text_before = processed_text[:word_start]
                if re.search(r'[.!?]\s+$', text_before):
                    return word.capitalize()
                
                return word
            
            processed_text = re.sub(r'\b([a-zA-Z]+(?:-[a-zA-Z]+)*)\b', word_replacer, processed_text)
            
            # Clean up acronym expansion tracking
            if hasattr(cls, '_acronym_expansion_words'):
                delattr(cls, '_acronym_expansion_words')

            return processed_text

        except Exception as e:
            logger.error(f"Error processing text: '{text[:50]}...' - {e}", exc_info=True)
            return text  # Fallback to original text on error
    
    @classmethod
    def titlecase_callback(cls, word, **kwargs):
        """Custom titlecase callback using YAML configuration."""
        if not isinstance(word, str):
            return word
            
        # normalizations for common business suffixes
        normalized_words = {"L.L.C.": "LLC", "I.N.C.": "Inc", "L.L.P.": "LLP", "L.T.D.": "LTD",
                            "P.L.L.C.": "PLLC", "P.A.": "PA", "P.C.": "PC"}

        if word.upper() in normalized_words.keys():
            word = normalized_words[word.upper()]

        return cls._preserve_special_case(word)


# Cache for special cases from YAML (keep for backward compatibility)
_special_cases_cache = None


def _load_special_cases():
    """Load and cache special cases from YAML file."""
    return TextFormatter._load_special_cases()


# Define a callback function for custom word handling
def custom_titlecase_callback(word, **kwargs):
    """Custom titlecase callback using YAML configuration."""
    return TextFormatter.titlecase_callback(word, **kwargs)


def contracts_titlecase(text):
    """Apply NASA-specific title casing rules to text"""
    if text is None:
        return None
    return titlecase(text, callback=TextFormatter.titlecase_callback)


def get_business_category_display_names(business_category_list):
    business_category_display_name_list = []
    for business_category in business_category_list:
        display_name = BUSINESS_CATEGORIES.get(business_category)
        if display_name:
            business_category_display_name_list.append(display_name)
    return business_category_display_name_list

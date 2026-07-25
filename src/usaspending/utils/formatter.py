from __future__ import annotations

import decimal
import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import yaml
from titlecase import titlecase

from ..logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)


def to_date(date_string: str | date | None) -> date | None:
    """Convert date string to date object.

    Supports multiple date formats:
    - YYYY-MM-DD (date only)
    - YYYY-MM-DD HH:MM:SS (space-separated datetime)
    - YYYY-MM-DD HH:MM:SS.ffffff (space-separated datetime with microseconds)
    - YYYY-MM-DDTHH:MM:SS (ISO datetime)
    - YYYY-MM-DDTHH:MM:SS.ffffff (ISO datetime with microseconds)
    - YYYY-MM-DDTHH:MM:SSZ (ISO datetime with UTC indicator)
    - YYYY-MM-DDTHH:MM:SS+/-HH:MM (ISO datetime with timezone offset)

    Note: For formats with time components, only the date portion is returned.
    If input is already a date object, returns it unchanged.

    Args:
        date_string: Date string in any supported format, or a date object

    Returns:
        date object or None if parsing fails
    """
    if not date_string:
        return None

    if isinstance(date_string, datetime):
        return date_string.date()
    if isinstance(date_string, date):
        return date_string

    # Define formats to try, in order of likelihood
    formats = [
        "%Y-%m-%d",  # Date only (original format)
        "%Y-%m-%d %H:%M:%S",  # Datetime with space separator
        "%Y-%m-%d %H:%M:%S.%f",  # Datetime with space separator and microseconds
        "%Y-%m-%dT%H:%M:%S",  # ISO datetime without timezone
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO datetime with microseconds
        "%Y-%m-%dT%H:%M:%SZ",  # ISO datetime with UTC indicator
        "%Y-%m-%dT%H:%M:%S%z",  # ISO datetime with timezone offset
    ]

    for fmt in formats:
        try:
            parsed_datetime = datetime.strptime(date_string, fmt)
            # Return only the date portion
            return parsed_datetime.date()
        except ValueError:
            continue

    # If no format matched, log warning and return None
    logger.warning(f"Could not parse date string: {date_string}")
    return None


def round_to_millions(amount: int | float | Decimal) -> str:
    """
    Formats a monetary amount with commas and two decimal places, displaying as millions or billions when appropriate.

    Args:
        amount (Any): The monetary value to format.

    Returns:
        str: The formatted string representing the amount in dollars, millions, or billions.
    """

    amount = to_decimal(amount)

    if amount is None:
        return "$0.00"
    elif amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:,.1f} billion"
    elif amount >= 1_000_000:
        return f"${amount / 1_000_000:,.1f} million"
    else:
        return f"${amount:,.2f}"


def current_fiscal_year() -> int:
    """
    Returns the current fiscal year based on the current date.

    The fiscal year starts in October. If the current month is October or later,
    the fiscal year is considered to be the next calendar year.

    Returns:
        int: The current fiscal year.
    """
    current_date = datetime.now()
    current_month = datetime.now().month
    if current_month < 10:
        return current_date.year
    else:
        return current_date.year + 1


def to_decimal(x: Any) -> Decimal | None:
    """Convert input to a Decimal with 2 decimal places using banker's rounding.

    Args:
        x: Value to convert to Decimal (number, string, etc.)

    Returns:
        Optional[Decimal]: Decimal object quantized to 2 decimal places, or None if input is None or conversion fails
    """
    if x is None:
        return None
    try:
        return Decimal(str(x)).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, decimal.InvalidOperation):
        return None


def to_float(x: Any) -> float | None:
    """
    Converts the input value to a float if possible.
    Attempts to cast the provided value to a float. If the conversion fails due to a TypeError or ValueError,
    returns None instead.

    Args:
        x (Any): The value to convert to float.

    Returns:
        Optional[float]: The converted float value, or None if conversion is not possible.
    """

    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def to_int(x: Any) -> int | None:
    """
    Converts the input value to an integer if possible.
    Attempts to cast the provided value to an integer. If the conversion fails due to a TypeError or ValueError,
    returns None instead.

    Args:
        x (Any): The value to convert to an integer.

    Returns:
        Optional[int]: The integer representation of `x` if conversion is successful; otherwise, None.
    """

    # A missing value is the common case for optional API fields, and reaching
    # int(None) just to catch the TypeError costs roughly 7x this early return.
    if x is None:
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


# Maximum length for parenthesized text to be uppercased
PAREN_UPPERCASE_MAX_LEN: int = 9  # Fewer than 10 characters

# --- Helper Function ---


def smart_sentence_case(
    text: str | None,
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
                with open(yaml_path) as f:
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
            if special_word.endswith(".") and clean_word.lower() == special_word[:-1].lower():
                # Word like "inc" matching "Inc."
                return special_word + trailing_punct

        return None

    @classmethod
    def to_sentence_case(cls, text: str | None, paren_max_len: int = 9) -> str:
        """
        Convert text to sentence case, preserving special cases from YAML.

        True sentence case: only capitalize first word of sentences and special cases.
        Includes progressive acronym expansion for parenthetical content.

        Args:
            text: Input text to convert
            paren_max_len: Max length for parenthesized text to keep uppercase

        Returns:
            str: Text in sentence case with special cases preserved
        """
        if not text:
            return ""

        try:
            # Start with lowercase
            processed_text = text.lower()
            special_cases_set = cls._get_special_cases_set()

            # Small words to ignore in acronym expansion
            SMALL_WORDS = r"\b(a|an|and|as|at|but|by|en|for|if|in|of|on|or|the|to|v\.?|via|vs\.?)\b"

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
                    words_before = re.findall(r"\b\w+\b", text_before)
                    acronym_letters = [c.lower() for c in paren_content if c.isalpha()]

                    if len(acronym_letters) > 0 and len(words_before) >= len(acronym_letters):
                        # Try direct match first
                        last_n_words = words_before[-len(acronym_letters) :]
                        if [w[0].lower() for w in last_n_words] == acronym_letters:
                            # Mark these words for capitalization
                            acronym_expansion_words.update(last_n_words)
                        else:
                            # If direct match failed, try skipping small words
                            # Filter out small words
                            content_words = []
                            for word in words_before:
                                if not re.match(SMALL_WORDS, word, re.IGNORECASE):
                                    content_words.append(word)

                            if len(content_words) >= len(acronym_letters):
                                last_n_content = content_words[-len(acronym_letters) :]
                                if [w[0].lower() for w in last_n_content] == acronym_letters:
                                    # Mark these words for capitalization
                                    acronym_expansion_words.update(last_n_content)

                # Return uppercase parenthetical if short enough
                if len(paren_content) <= paren_max_len:
                    return f"({paren_content.upper()})"
                else:
                    return full_match

            # Initialize acronym expansion tracking (local to this call)
            acronym_expansion_words: set[str] = set()

            # Apply acronym expansion
            processed_text = re.sub(r"\(([^)]+)\)", expand_acronyms, processed_text)

            # Handle special cases and sentence boundaries
            def word_replacer(match):
                word = match.group(1)
                word_start = match.start()

                # Check if word should be capitalized due to acronym expansion
                if word in acronym_expansion_words:
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
                if re.search(r"[.!?]\s+$", text_before):
                    return word.capitalize()

                return word

            processed_text = re.sub(
                r"\b([a-zA-Z]+(?:-[a-zA-Z]+)*)\b", word_replacer, processed_text
            )

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
        normalized_words = {
            "L.L.C.": "LLC",
            "I.N.C.": "Inc",
            "L.L.P.": "LLP",
            "L.T.D.": "LTD",
            "P.L.L.C.": "PLLC",
            "P.A.": "PA",
            "P.C.": "PC",
        }

        if word.upper() in normalized_words:
            word = normalized_words[word.upper()]

        return cls._preserve_special_case(word)


def contracts_titlecase(text):
    """
    Applies NASA-relevant title casing rules to the given text.

    Args:
        text (str or None): The input text to be title-cased. If None, returns None.

    Returns:
        str or None: The title-cased text according to NASA-specific rules, or None if input is None.
    """
    if text is None:
        return None
    return titlecase(text, callback=TextFormatter.titlecase_callback)

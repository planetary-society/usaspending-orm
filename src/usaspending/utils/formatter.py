from __future__ import annotations

import decimal
import re
import warnings
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, NamedTuple

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
    # One reading of the clock, not two: separate calls could straddle the
    # October boundary and report a year the calendar never had.
    today = datetime.now()
    return today.year + 1 if today.month >= 10 else today.year


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


class _SpecialCaseLookups(NamedTuple):
    """The lookups casing resolves through, and the list they were built from.

    Carrying ``source`` alongside them is what lets them rebuild when the loaded
    list is replaced, so clearing ``TextFormatter._special_cases_cache`` remains
    the single way to invalidate casing state. Holding all three together makes
    that one assignment, so a reader can never see a lookup paired with the wrong
    source.
    """

    #: The loaded list these were derived from, compared by identity.
    source: list

    #: Lowercase keys, used by title casing. Carries each entry's lowercase form
    #: plus, for an entry ending in a period, that form without it, so "inc"
    #: matches "Inc.".
    by_lower_form: dict[str, str]

    #: Uppercase keys, used by sentence casing, which matches an entry as
    #: written. Deliberately without the period-stripped variants: 15 forms such
    #: as "l.l.c" would start being rewritten if it carried them.
    by_upper_form: dict[str, str]


class TextFormatter:
    """Unified text formatting utility class for sentence and title case conversions."""

    _special_cases_cache = None

    #: Derived from ``_special_cases_cache``; see :class:`_SpecialCaseLookups`.
    _special_cases_lookups: _SpecialCaseLookups | None = None

    @classmethod
    def _load_special_cases(cls):
        """Load and cache the special-case list from YAML.

        Failures degrade to no special casing rather than raising. Casing runs
        inside ``__repr__`` on several models, so an exception here would break
        debuggers, logging and error messages over what is a cosmetic problem: a
        mis-cased name is still the right name.

        A corrupt or wrongly shaped file is still a packaging or editing mistake
        rather than a configuration, so it also emits a ``UserWarning``, which is
        visible by default unlike the log record this replaced. Escalating that to
        an error with ``-W error::UserWarning`` does reintroduce the raising
        ``__repr__`` described above, so it suits a test run rather than
        production. A merely absent file warns only in the log, since an
        installation can legitimately lack it.
        """
        if cls._special_cases_cache is None:
            yaml_path = Path(__file__).parent / "special_cases.yaml"
            loaded: Any = []
            try:
                with open(yaml_path) as f:
                    loaded = yaml.safe_load(f) or []
            except FileNotFoundError:
                logger.warning(f"Special cases file not found: {yaml_path}")
            except yaml.YAMLError as e:
                warnings.warn(
                    f"Could not parse {yaml_path}, so names will not be special-cased: {e}",
                    UserWarning,
                    stacklevel=2,
                )
                loaded = []
            else:
                if not isinstance(loaded, list):
                    warnings.warn(
                        f"{yaml_path} must contain a list of special cases, got "
                        f"{type(loaded).__name__}, so names will not be special-cased.",
                        UserWarning,
                        stacklevel=2,
                    )
                    loaded = []

            cls._special_cases_cache = loaded
        return cls._special_cases_cache

    @classmethod
    def _special_case_lookups(cls) -> _SpecialCaseLookups:
        """Return the casing lookups, building them once per loaded list.

        Both map a normalized word to its canonical spelling and let the earliest
        entry win, matching the scans they replace. See
        :class:`_SpecialCaseLookups` for why they key differently.
        """
        special_cases = cls._load_special_cases()

        lookups = cls._special_cases_lookups
        if lookups is None or lookups.source is not special_cases:
            by_lower_form: dict[str, str] = {}
            by_upper_form: dict[str, str] = {}
            collisions: list[tuple[str, str]] = []

            def claim(key: str, special_word: str) -> None:
                held = by_lower_form.setdefault(key, special_word)
                if held != special_word:
                    collisions.append((held, special_word))

            for special_word in special_cases:
                if not isinstance(special_word, str):
                    continue
                claim(special_word.lower(), special_word)
                if special_word.endswith("."):
                    claim(special_word[:-1].lower(), special_word)
                by_upper_form.setdefault(special_word.upper(), special_word)

            if collisions:
                warnings.warn(
                    "special_cases.yaml has entries whose lowercase forms collide, so "
                    "which spelling wins depends on their order: "
                    f"{collisions}. Remove the duplicates.",
                    UserWarning,
                    stacklevel=3,
                )

            lookups = _SpecialCaseLookups(special_cases, by_lower_form, by_upper_form)
            cls._special_cases_lookups = lookups

        return lookups

    @classmethod
    def _split_word_punctuation(cls, word):
        """Split a word into clean word and trailing punctuation."""
        if not word:
            return word, ""

        trailing_punct = ""
        clean_word = word

        # Handle contractions separately
        if "'" in word:
            # For a possessive like "NASA's", split at the apostrophe
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

        by_lower_form = cls._special_case_lookups().by_lower_form

        # The whole word, punctuation included, so that "u.s." matches as written.
        special_word = by_lower_form.get(word.lower())
        if special_word is not None:
            return special_word

        # Then the word without its trailing punctuation, which is restored.
        clean_word, trailing_punct = cls._split_word_punctuation(word)
        special_word = by_lower_form.get(clean_word.lower())
        if special_word is not None:
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
            special_cases_by_upper_form = cls._special_case_lookups().by_upper_form

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
                special_case = special_cases_by_upper_form.get(word.upper())
                if special_case is not None:
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


def titlecase_name(text: str | None) -> str | None:
    """Title-case a name reported by the API, preserving known special cases.

    Recipient, agency and place names arrive uppercased. Plain title casing
    mangles the acronyms, mixed-case marks and suffixes they contain, so casing
    goes through ``special_cases.yaml``, which lists the forms to leave alone.

    Note:
        That list is deliberately NASA-centric. Alongside generic business and
        address forms such as ``LLC`` and ``NE``, it carries National Aeronautics
        and Space Administration centers and programs -- ``GSFC``, ``JPL``,
        ``EPSCoR``, ``OSIRIS-REx`` and the rest -- because that is the data this
        library was built to read. Keeping the list as data means it can grow
        without touching this function. Lifting the whole special-case mechanism
        into a plugin, so another agency's vocabulary could be supplied instead,
        is deferred rather than attempted here.

    Args:
        text: The text to title-case, or None.

    Returns:
        Optional[str]: The title-cased text, or None if the input was None.

    Example:
        >>> titlecase_name("THE UNIVERSITY OF IOWA")
        'The University of Iowa'
    """
    if text is None:
        return None
    return titlecase(text, callback=TextFormatter.titlecase_callback)

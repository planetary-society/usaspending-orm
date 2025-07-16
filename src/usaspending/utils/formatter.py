from typing import List, Dict, List, Any, Optional, Set
from datetime import datetime
import re
from titlecase import titlecase
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def round_to_millions(amount: float) -> str:
    """Format money amount with commas and 2 decimal places, display as millions or billions based on the amount."""
    if amount is None:
        return format_money(amount)
    if amount >= 1_000_000_000:
        return "${:,.1f} billion".format(amount / 1_000_000_000)
    elif amount >= 10_000_000:
        return "${:,.1f} million".format(amount / 1_000_000)
    elif amount >= 1_000_000:
        return "${:,.1f} million".format(amount / 1_000_000)
    return "${:,.2f}".format(amount)


def current_fiscal_year() -> int:
    """ Returns the current fiscal year """
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
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return x


# --- Configuration ---
# Set of acronyms and initialisms to always keep uppercase.
# This could be loaded from a config file or environment variables in a larger application.
DEFAULT_KEEP_UPPERCASE: Set[str] = {
    # Common Business / Legal
    "LLC", "INC", "LLP", "LTD", "L.L.C.", "I.N.C.", "L.L.P.", "L.T.D.",
    # Geographical / Governmental
    "USA", "US", "UK",
    # Organizations / Agencies
    "NASA", "ESA", "JAXA",
    # NASA Facilities & Major Programs (add more as needed)
    "JPL", # Jet Propulsion Laboratory
    "JSC", # Johnson Space Center
    "KSC", # Kennedy Space Center
    "GSFC", # Goddard Space Flight Center
    "MSFC", # Marshall Space Flight Center
    "ARC", # Ames Research Center
    "GRC", # Glenn Research Center
    "LARC", # Langley Research Center (or LaRC - handled by case-insensitive check)
    "AFRC", # Armstrong Flight Research Center
    "SSC", # Stennis Space Center
    "ISS", # International Space Station
    "JWST", # James Webb Space Telescope
    # Specific examples from user input
    "CSOS", "CL", "FL", "FPRW", "PADF", "ICAT", "ICATEQ", "AC" # For A.C. style
    # Add other common contract/technical acronyms as needed
    "RFQ", "RFP", "SOW", "CDR", "PDR", "QA", "PI", "COTS",
}

# Maximum length for parenthesized text to be uppercased
PAREN_UPPERCASE_MAX_LEN: int = 9 # Fewer than 10 characters

# --- Helper Function ---

def smart_sentence_case(
    text: Optional[str],
    keep_uppercase: Set[str] = DEFAULT_KEEP_UPPERCASE,
    paren_max_len: int = PAREN_UPPERCASE_MAX_LEN
) -> str:
    """
    Converts an uppercase string to sentence case, preserving specified acronyms
    and short parenthesized text in uppercase.

    Rules:
    1. Converts the text to lowercase as a base.
    2. Capitalizes the first letter of the resulting string.
    3. Keeps specified words/acronyms (case-insensitive match) in uppercase.
    4. Keeps text within parentheses uppercase if its length is less than
       paren_max_len + 1 characters.
    5. Handles standard punctuation like apostrophes correctly.

    Args:
        text: The input string, expected to be mostly uppercase.
              Can be None or empty.
        keep_uppercase: A set of strings (acronyms, initialisms) that should
                        remain in uppercase. Defaults to DEFAULT_KEEP_UPPERCASE.
        paren_max_len: The maximum character length of text inside parentheses
                       to be kept uppercase. Defaults to PAREN_UPPERCASE_MAX_LEN.

    Returns:
        The processed string in smart sentence case, or an empty string if
        the input was None or empty.
    """
    if not text:
        return ""

    try:
        # 1. Start with lowercase
        processed_text = text.lower()

        # 2. Handle parenthesized text: Uppercase if short
        # Uses a lambda function to check length and conditionally uppercase
        def paren_replacer(match):
            content = match.group(1) # Content inside parentheses
            if len(content) <= paren_max_len:
                return f"({content.upper()})"
            else:
                # Return original match (lowercase parens + content)
                return match.group(0)

        processed_text = re.sub(r'\(([^)]+)\)', paren_replacer, processed_text)

        # 3. Handle specified acronyms/words: Uppercase if in the set
        # Uses a lambda function to check against the keep_uppercase set
        # We use word boundaries (\b) to match whole words only.
        # Need to handle cases like "NASA's" correctly - the regex only matches letters.
        # We convert the matched word to upper to check against the set.
        def acronym_replacer(match):
            word = match.group(1)
            if word.upper() in keep_uppercase:
                return word.upper()
            else:
                # If not in the set, return the word as it is (lowercase)
                return word

        # This regex finds sequences of letters bounded by non-word characters (or start/end)
        # It won't capture A.C. directly but will process A and C individually if AC is in the set.
        processed_text = re.sub(r'\b([a-zA-Z]+)\b', acronym_replacer, processed_text)

        # 4. Capitalize the first letter of the entire string
        if processed_text:
            processed_text = processed_text[0].upper() + processed_text[1:]

        return processed_text

    except Exception as e:
        logging.error(f"Error processing text: '{text[:50]}...' - {e}", exc_info=True)
        # Decide on fallback behavior: return original text or empty string?
        # Returning original might be safer if processing fails unexpectedly.
        return text # Fallback to original text on error


# Define a callback function for custom word handling
def custom_titlecase_callback(word, **kwargs):
    # If the word is enclosed in parentheses, preserve the case inside.
    if word.startswith('(') and word.endswith(')'):
        return word

    # Special NASA acronyms - always uppercase.
    nasa_acronyms = ['nasa', 'sbir', 'sttr', 'iss', 'tdm', 'tdrs', 'fy', 'scan', 'epscor', 'stem']
    if word.lower() in nasa_acronyms:
        return word.upper()

    # Special NASA acronyms - always uppercase.
    business_acronyms = ['llc', 'inc', 'llp', 'ltd', 'l.l.c.', 'i.n.c.', 'l.l.p.', 'l.t.d.']
    if word.lower() in business_acronyms:
        return word.upper()

    # Handle special cases.
    if word.upper() == 'OSIRIS-REX':
        return 'OSIRIS-REx'
    if word.upper() == 'SCAN':
        return 'SCaN'
    if word.upper() == 'EPSCOR':
        return 'EPSCoR'

    # For small words that should be lowercase (like 'and', 'of', 'the', etc.).
    small_words = ['and', 'of', 'for', 'the', 'a', 'an', 'in', 'on', 'at', 'to']
    if word.lower() in small_words and not word.istitle() and kwargs.get('index', 0) != 0:
        return word.lower()

    # Return None to let titlecase handle it normally.
    return None

def contracts_titlecase(text):
    """Apply NASA-specific title casing rules to text"""
    return titlecase(text, callback=custom_titlecase_callback)

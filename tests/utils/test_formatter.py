"""Tests for formatter utility functions."""

import pytest
from unittest.mock import patch, mock_open
import yaml

from usaspending.utils.formatter import (
    custom_titlecase_callback,
    contracts_titlecase,
    smart_sentence_case,
    TextFormatter,
    _load_special_cases,
)


class TestCustomTitlecaseCallback:
    """Test the custom titlecase callback function."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset the special cases cache before each test."""
        import usaspending.utils.formatter

        usaspending.utils.formatter._special_cases_cache = None
        yield
        usaspending.utils.formatter._special_cases_cache = None

    def test_parentheses_preserved(self):
        """Test that words in parentheses are preserved."""
        assert custom_titlecase_callback("(test)") == "(test)"
        assert custom_titlecase_callback("(NASA)") == "(NASA)"

    def test_special_cases_loaded(self):
        """Test that special cases are loaded from YAML."""
        mock_yaml_content = yaml.dump(["NASA", "Inc.", "and"])

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            with patch("pathlib.Path.exists", return_value=True):
                # Test uppercase acronym
                assert custom_titlecase_callback("nasa") == "NASA"
                assert custom_titlecase_callback("NASA") == "NASA"
                assert custom_titlecase_callback("Nasa") == "NASA"

                # Test business suffix
                assert custom_titlecase_callback("inc.") == "Inc."
                assert custom_titlecase_callback("INC.") == "Inc."

                # Test lowercase word
                assert custom_titlecase_callback("and") == "and"
                assert custom_titlecase_callback("AND") == "and"

    def test_no_match_returns_none(self):
        """Test that words not in special cases return None."""
        mock_yaml_content = yaml.dump(["NASA"])

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            assert custom_titlecase_callback("example") is None
            assert custom_titlecase_callback("test") is None

    def test_file_not_found_handled(self):
        """Test graceful handling when YAML file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            # Should return None and not crash
            assert custom_titlecase_callback("nasa") is None

    def test_yaml_error_handled(self):
        """Test graceful handling of YAML parsing errors."""
        with patch("builtins.open", mock_open(read_data="invalid: yaml: content:")):
            with patch("yaml.safe_load", side_effect=yaml.YAMLError):
                # Should return None and not crash
                assert custom_titlecase_callback("nasa") is None

    def test_caching_works(self):
        """Test that special cases are cached after first load."""
        mock_yaml_content = yaml.dump(["NASA"])

        with patch(
            "builtins.open", mock_open(read_data=mock_yaml_content)
        ) as mock_file:
            # First call loads from file
            custom_titlecase_callback("test")
            assert mock_file.call_count == 1

            # Second call uses cache
            custom_titlecase_callback("test")
            assert mock_file.call_count == 1  # Still 1, not 2


class TestContractsTitlecase:
    """Test the contracts_titlecase function."""

    @pytest.fixture(autouse=True)
    def setup_yaml(self):
        """Mock the YAML file for consistent tests."""
        import usaspending.utils.formatter

        usaspending.utils.formatter._special_cases_cache = None

        mock_special_cases = [
            "NASA",
            "ESA",
            "USA",
            "SBIR",
            "LLC",
            "Inc.",
            "Ltd.",
            "and",
            "or",
            "of",
            "the",
            "for",
            "with",
            "NE",
            "SW",
            "St.",
            "Ave.",
            "OSIRIS-REx",
            "SCaN",
            "EPSCoR",
        ]
        mock_yaml_content = yaml.dump(mock_special_cases)

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            yield

        usaspending.utils.formatter._special_cases_cache = None

    def test_none_input(self):
        """Test handling of None input."""
        assert contracts_titlecase(None) is None

    def test_basic_titlecase(self):
        """Test basic title casing."""
        assert contracts_titlecase("hello world") == "Hello World"
        assert contracts_titlecase("HELLO WORLD") == "Hello World"

    def test_acronyms_preserved(self):
        """Test that acronyms are preserved."""
        assert contracts_titlecase("nasa research") == "NASA Research"
        assert contracts_titlecase("working with nasa") == "Working with NASA"
        assert contracts_titlecase("sbir program") == "SBIR Program"

    def test_business_suffixes(self):
        """Test business suffixes."""
        assert contracts_titlecase("acme inc.") == "Acme Inc."
        assert contracts_titlecase("technology llc") == "Technology LLC"
        assert contracts_titlecase("services ltd.") == "Services Ltd."

    def test_small_words(self):
        """Test that small words are lowercase in middle."""
        assert contracts_titlecase("bread and butter") == "Bread and Butter"
        assert contracts_titlecase("the quick fox") == "the Quick Fox"
        assert contracts_titlecase("of the people") == "of the People"

    def test_directional_abbreviations(self):
        """Test directional abbreviations."""
        assert contracts_titlecase("123 main st. ne") == "123 Main St. NE"
        assert contracts_titlecase("456 oak ave. sw") == "456 Oak Ave. SW"

    def test_directional_with_punctuation(self):
        """Test directional abbreviations with punctuation."""
        # Debug callback behavior with punctuation
        from titlecase import titlecase

        # Track what words the callback sees
        words_seen = []

        def debug_callback(word, **kwargs):
            words_seen.append(word)
            # Use our real callback
            return custom_titlecase_callback(word, **kwargs)

        # Clear the tracking list
        words_seen.clear()
        result = titlecase("123 main st. ne, suite 100", callback=debug_callback)

        # Print debug info if test fails
        if result != "123 Main St. NE, Suite 100":
            print(f"Words seen by callback: {words_seen}")
            print(f"Actual result: {result}")

        # The issue is likely that titlecase passes "ne," as one word
        # Let's test various punctuation scenarios
        assert contracts_titlecase("ne, suite") == "NE, Suite"
        assert contracts_titlecase("st. ne,") == "St. NE,"
        assert (
            contracts_titlecase("123 main st. ne, suite 100")
            == "123 Main St. NE, Suite 100"
        )

    def test_special_casing(self):
        """Test special casing rules."""
        assert contracts_titlecase("osiris-rex mission") == "OSIRIS-REx Mission"
        assert contracts_titlecase("scan network") == "SCaN Network"
        assert contracts_titlecase("epscor funding") == "EPSCoR Funding"

    def test_complex_examples(self):
        """Test complex real-world examples."""
        assert (
            contracts_titlecase("nasa sbir program for small business llc")
            == "NASA SBIR Program for Small Business LLC"
        )

        assert (
            contracts_titlecase("123 main st. ne, suite 100")
            == "123 Main St. NE, Suite 100"
        )

        assert (
            contracts_titlecase("the university of maryland and nasa")
            == "the University of Maryland and NASA"
        )


class TestSmartSentenceCase:
    """Test the smart_sentence_case function."""

    @pytest.fixture(autouse=True)
    def setup_yaml(self):
        """Mock the YAML file for consistent tests."""
        import usaspending.utils.formatter

        usaspending.utils.formatter._special_cases_cache = None
        TextFormatter._special_cases_cache = None

        mock_special_cases = [
            "NASA",
            "ESA", 
            "USA",
            "SBIR",
            "LLC",
            "Inc.",
            "Ltd.",
            "and",
            "or",
            "of",
            "the",
            "for",
            "with",
            "NE",
            "SW",
            "St.",
            "Ave.",
            "OSIRIS-REx",
            "SCaN",
            "EPSCoR",
        ]
        mock_yaml_content = yaml.dump(mock_special_cases)

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            yield

        usaspending.utils.formatter._special_cases_cache = None
        TextFormatter._special_cases_cache = None

    def test_none_input(self):
        """Test handling of None input."""
        assert smart_sentence_case(None) == ""

    def test_empty_input(self):
        """Test handling of empty input."""
        assert smart_sentence_case("") == ""

    def test_basic_sentence_case(self):
        """Test basic sentence case behavior."""
        assert smart_sentence_case("HELLO WORLD") == "Hello world"
        assert smart_sentence_case("THIS IS A TEST") == "This is a test"

    def test_special_cases_preserved(self):
        """Test that special cases from YAML are preserved."""
        assert smart_sentence_case("NASA HEADQUARTERS") == "NASA headquarters"
        assert smart_sentence_case("WORKING WITH NASA") == "Working with NASA"
        assert smart_sentence_case("OSIRIS-REX MISSION") == "OSIRIS-REx mission"

    def test_sentence_boundaries(self):
        """Test sentence boundary detection."""
        assert smart_sentence_case("FIRST SENTENCE. SECOND SENTENCE") == "First sentence. Second sentence"
        assert smart_sentence_case("QUESTION HERE? ANSWER THERE") == "Question here? Answer there"
        assert smart_sentence_case("EXCLAMATION! ANOTHER SENTENCE") == "Exclamation! Another sentence"

    def test_multiple_spaces_after_punctuation(self):
        """Test sentence boundaries with multiple spaces."""
        assert smart_sentence_case("FIRST SENTENCE.  SECOND SENTENCE") == "First sentence.  Second sentence"
        assert smart_sentence_case("FIRST SENTENCE.   THIRD SENTENCE") == "First sentence.   Third sentence"

    def test_short_parenthetical_content(self):
        """Test short parenthetical content stays uppercase."""
        assert smart_sentence_case("CONTRACT (RFP) FOR NASA") == "Contract (RFP) for NASA"
        assert smart_sentence_case("USING SCAN NETWORK") == "Using SCaN network"

    def test_acronym_expansion_direct_match(self):
        """Test direct acronym expansion."""
        # Direct match: N-A-S-A
        assert smart_sentence_case("NATIONAL AERONAUTICS SPACE ADMINISTRATION (NASA)") == "National Aeronautics Space Administration (NASA)"

    def test_acronym_expansion_skip_small_words(self):
        """Test acronym expansion skipping small words."""
        # Should skip "OF", "AND" to match N-A-S-E-M
        result = smart_sentence_case("NATIONAL ACADEMIES OF SCIENCES, ENGINEERING, AND MEDICINE (NASEM)")
        assert result == "National Academies of Sciences, Engineering, and Medicine (NASEM)"

    def test_acronym_expansion_no_match(self):
        """Test when acronym expansion finds no match."""
        assert smart_sentence_case("RANDOM WORDS HERE (XYZ)") == "Random words here (XYZ)"

    def test_mixed_content(self):
        """Test complex mixed content."""
        text = "THIS CONTRACT WILL ENSURE NASA OSIRIS-REX DATA IS PRETTY. WILL PROCESS USING COMMUNICATIONS (SCAN) DATA."
        expected = "This contract will ensure NASA OSIRIS-REx data is pretty. Will process using communications (SCaN) data."
        assert smart_sentence_case(text) == expected

    def test_vs_contracts_titlecase(self):
        """Test that smart_sentence_case differs from contracts_titlecase."""
        text = "UNITED LAUNCH ALLIANCE FOR NASA AND AMERICA"
        sentence_result = smart_sentence_case(text)
        title_result = contracts_titlecase(text)
        
        # Should be different
        assert sentence_result != title_result
        assert sentence_result == "United launch alliance for NASA and america"
        assert title_result == "United Launch Alliance for NASA and America"

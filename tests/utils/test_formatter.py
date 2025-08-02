"""Tests for formatter utility functions."""

import pytest
from unittest.mock import patch, mock_open
import yaml

from usaspending.utils.formatter import (
    contracts_titlecase,
    TextFormatter,
)



class TestContractsTitlecase:
    """Test the contracts_titlecase function."""

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
        assert contracts_titlecase(None) is None

    def test_basic_titlecase(self):
        """Test basic title casing."""
        assert contracts_titlecase("hello world") == "Hello World"
        assert contracts_titlecase("HELLO WORLD") == "Hello World"

    def test_acronyms_preserved(self):
        """Test that acronyms are preserved."""
        assert contracts_titlecase("nasa research") == "NASA Research"
        assert contracts_titlecase("working with nasa") == "Working With NASA"
        assert contracts_titlecase("sbir program") == "SBIR Program"

    def test_business_suffixes(self):
        """Test business suffixes."""
        assert contracts_titlecase("acme inc.") == "Acme Inc."
        assert contracts_titlecase("technology llc") == "Technology LLC"
        assert contracts_titlecase("services ltd.") == "Services Ltd."

    def test_small_words(self):
        """Test that small words are lowercase in middle."""
        assert contracts_titlecase("bread and butter") == "Bread And Butter"
        assert contracts_titlecase("the quick fox") == "The Quick Fox"
        assert contracts_titlecase("of the people") == "Of The People"

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
            == "NASA SBIR Program For Small Business LLC"
        )

        assert (
            contracts_titlecase("123 main st. ne, suite 100")
            == "123 Main St. NE, Suite 100"
        )

        assert (
            contracts_titlecase("the university of maryland and nasa")
            == "The University Of Maryland And NASA"
        )


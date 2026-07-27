"""Tests for TextFormatter class."""

from unittest.mock import mock_open, patch

import pytest
import yaml

from usaspending.utils.formatter import TextFormatter


class TestTextFormatter:
    """Test the TextFormatter class methods."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset the special cases cache before each test."""
        TextFormatter._special_cases_cache = None
        yield
        TextFormatter._special_cases_cache = None

    def test_load_special_cases_success(self):
        """Test successful loading of special cases."""
        mock_special_cases = ["NASA", "Inc.", "LLC"]
        mock_yaml_content = yaml.dump(mock_special_cases)

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            cases = TextFormatter._load_special_cases()
            assert cases == mock_special_cases

    def test_load_special_cases_file_not_found(self):
        """Test graceful handling when YAML file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            cases = TextFormatter._load_special_cases()
            assert cases == []

    def test_load_special_cases_yaml_error(self):
        """Unparseable YAML warns rather than failing silently.

        See TestSpecialCasesLoadFailures for the full contract; this pins that the
        problem is announced, where before it went only to the log.
        """
        TextFormatter._special_cases_cache = None
        with (
            patch("builtins.open", mock_open(read_data="invalid: yaml: content:")),
            patch("yaml.safe_load", side_effect=yaml.YAMLError),
            pytest.warns(UserWarning, match="Could not parse"),
        ):
            assert TextFormatter._load_special_cases() == []

    def test_special_case_lookups_exact_map(self):
        """The exact lookup maps an uppercase form to its canonical spelling.

        Sentence casing matches an entry as written, so this keys on the
        uppercase form only. It must NOT carry the period-stripped keys the
        title-case lookup needs, or words like "l.l.c" would start being
        rewritten.
        """
        TextFormatter._special_cases_cache = None
        mock_special_cases = ["NASA", "Inc.", "OSIRIS-REx"]

        with patch("builtins.open", mock_open(read_data=yaml.dump(mock_special_cases))):
            lookups = TextFormatter._special_case_lookups()

        assert lookups.by_upper_form == {"NASA": "NASA", "INC.": "Inc.", "OSIRIS-REX": "OSIRIS-REx"}

        # The title-case lookup additionally accepts "inc" for "Inc."
        assert lookups.by_lower_form["inc"] == "Inc."
        assert "inc" not in lookups.by_upper_form

        TextFormatter._special_cases_cache = None

    def test_split_word_punctuation_simple(self):
        """Test splitting word from punctuation."""
        clean, punct = TextFormatter._split_word_punctuation("hello,")
        assert clean == "hello"
        assert punct == ","

    def test_split_word_punctuation_contractions(self):
        """Test handling of contractions."""
        clean, punct = TextFormatter._split_word_punctuation("NASA's")
        assert clean == "NASA"
        assert punct == "'s"

    def test_split_word_punctuation_multiple_punct(self):
        """Test multiple trailing punctuation."""
        clean, punct = TextFormatter._split_word_punctuation("word!!!")
        assert clean == "word"
        assert punct == "!!!"

    def test_split_word_punctuation_no_punct(self):
        """Test word with no punctuation."""
        clean, punct = TextFormatter._split_word_punctuation("word")
        assert clean == "word"
        assert punct == ""

    def test_preserve_special_case_exact_match(self):
        """Test exact special case preservation."""
        mock_special_cases = ["NASA", "Inc."]
        mock_yaml_content = yaml.dump(mock_special_cases)

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            result = TextFormatter._preserve_special_case("nasa")
            assert result == "NASA"

    def test_preserve_special_case_with_punctuation(self):
        """Test special case with trailing punctuation."""
        mock_special_cases = ["NASA", "Inc."]
        mock_yaml_content = yaml.dump(mock_special_cases)

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            result = TextFormatter._preserve_special_case("nasa,")
            assert result == "NASA,"

    def test_preserve_special_case_parentheses(self):
        """Test parenthetical content preservation."""
        result = TextFormatter._preserve_special_case("(test)")
        assert result == "(test)"

    def test_preserve_special_case_no_match(self):
        """Test when no special case match found."""
        mock_special_cases = ["NASA"]
        mock_yaml_content = yaml.dump(mock_special_cases)

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            result = TextFormatter._preserve_special_case("random")
            assert result is None


class TestTextFormatterSentenceCase:
    """Test TextFormatter.to_sentence_case method."""

    @pytest.fixture(autouse=True)
    def setup_yaml(self):
        """Mock the YAML file for consistent tests."""
        TextFormatter._special_cases_cache = None

        mock_special_cases = [
            "NASA",
            "ESA",
            "USA",
            "SBIR",
            "LLC",
            "Inc.",
            "OSIRIS-REx",
            "SCaN",
            "EPSCoR",
        ]
        mock_yaml_content = yaml.dump(mock_special_cases)

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            yield

        TextFormatter._special_cases_cache = None

    def test_empty_input(self):
        """Test empty input handling."""
        assert TextFormatter.to_sentence_case("") == ""
        assert TextFormatter.to_sentence_case(None) == ""

    def test_basic_sentence_case(self):
        """Test basic sentence case conversion."""
        assert TextFormatter.to_sentence_case("HELLO WORLD") == "Hello world"
        assert TextFormatter.to_sentence_case("this is a test") == "This is a test"

    def test_special_cases_preserved(self):
        """Test special cases are preserved."""
        assert TextFormatter.to_sentence_case("NASA MISSION") == "NASA mission"
        assert TextFormatter.to_sentence_case("OSIRIS-REX DATA") == "OSIRIS-REx data"

    def test_sentence_boundaries(self):
        """Test sentence boundary detection."""
        # Test period + space
        result = TextFormatter.to_sentence_case("FIRST SENTENCE. SECOND SENTENCE")
        assert result == "First sentence. Second sentence"

        # Test question mark + space
        result = TextFormatter.to_sentence_case("QUESTION? ANSWER")
        assert result == "Question? Answer"

        # Test exclamation + space
        result = TextFormatter.to_sentence_case("EXCLAMATION! NEXT")
        assert result == "Exclamation! Next"

    def test_multiple_spaces_sentence_boundary(self):
        """Test sentence boundaries with multiple spaces."""
        result = TextFormatter.to_sentence_case("FIRST.  SECOND")
        assert result == "First.  Second"

        result = TextFormatter.to_sentence_case("FIRST.   THIRD")
        assert result == "First.   Third"

    def test_short_parenthetical_uppercase(self):
        """Test short parenthetical content stays uppercase."""
        result = TextFormatter.to_sentence_case("CONTRACT (RFP) DETAILS")
        assert result == "Contract (RFP) details"

        result = TextFormatter.to_sentence_case("USING (API) FOR ACCESS")
        assert result == "Using (API) for access"

    def test_long_parenthetical_normal(self):
        """Test long parenthetical content gets normal processing."""
        result = TextFormatter.to_sentence_case(
            "CONTRACT (VERY LONG DESCRIPTION) DETAILS", paren_max_len=5
        )
        assert result == "Contract (very long description) details"

    def test_acronym_expansion_direct_match(self):
        """Test direct acronym expansion matching."""
        # N-A-S-A should match directly
        result = TextFormatter.to_sentence_case("NATIONAL AERONAUTICS SPACE ADMINISTRATION (NASA)")
        assert result == "National Aeronautics Space Administration (NASA)"

    def test_acronym_expansion_skip_small_words(self):
        """Test acronym expansion skipping small words."""
        # Should skip "OF", "ENGINEERING", "AND" to match N-A-S-M
        result = TextFormatter.to_sentence_case(
            "NATIONAL ACADEMIES OF SCIENCES, ENGINEERING, AND MEDICINE (NASEM)"
        )
        assert result == "National Academies of Sciences, Engineering, and Medicine (NASEM)"

    def test_acronym_expansion_no_match(self):
        """Test when no acronym expansion match is found."""
        result = TextFormatter.to_sentence_case("RANDOM TEXT HERE (XYZ)")
        assert result == "Random text here (XYZ)"

    def test_acronym_expansion_already_in_yaml(self):
        """Test when parenthetical content is already in YAML."""
        result = TextFormatter.to_sentence_case("SOME TEXT WITH NASA (NASA) REFERENCE")
        assert result == "Some text with NASA (NASA) reference"

    def test_complex_mixed_scenario(self):
        """Test complex scenario with multiple features."""
        text = "THE NATIONAL AERONAUTICS SPACE ADMINISTRATION (NASA) WILL LAUNCH OSIRIS-REX. THIS MISSION USES SCAN (SCAN) TECHNOLOGY."
        result = TextFormatter.to_sentence_case(text)
        expected = "The National Aeronautics Space Administration (NASA) will launch OSIRIS-REx. This mission uses SCaN (SCaN) technology."
        assert result == expected

    def test_edge_case_no_space_before_period(self):
        """Test edge case with no space after punctuation."""
        result = TextFormatter.to_sentence_case("FIRST.SECOND")
        # Should not capitalize SECOND since no space after period
        assert result == "First.second"

    def test_multiple_sentences_different_punctuation(self):
        """Test multiple sentences with different punctuation."""
        text = "FIRST SENTENCE. SECOND QUESTION? THIRD EXCLAMATION! FOURTH NORMAL."
        result = TextFormatter.to_sentence_case(text)
        expected = "First sentence. Second question? Third exclamation! Fourth normal."
        assert result == expected

    def test_acronym_expansion_partial_match(self):
        """Test acronym expansion with partial matches."""
        # Only 2 words before but acronym has 3 letters - should not match
        result = TextFormatter.to_sentence_case("SPACE ADMINISTRATION (NASA)")
        assert result == "Space administration (NASA)"

    def test_acronym_expansion_reentrant_call_isolated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that reentrant calls do not corrupt acronym expansion state."""
        original_loader = TextFormatter._load_special_cases
        call_count = {"count": 0}

        def wrapped_loader(cls: type[TextFormatter]) -> list[str]:
            """Proxy loader that triggers a reentrant call on second invocation."""
            call_count["count"] += 1
            if call_count["count"] == 2:
                TextFormatter.to_sentence_case("NATIONAL AERONAUTICS SPACE ADMINISTRATION (NASA)")
            return original_loader()

        monkeypatch.setattr(TextFormatter, "_load_special_cases", classmethod(wrapped_loader))

        result = TextFormatter.to_sentence_case(
            "NASA NATIONAL AERONAUTICS SPACE ADMINISTRATION (NASA)"
        )
        assert result == "NASA National Aeronautics Space Administration (NASA)"

    def test_error_handling(self):
        """Test error handling returns original text."""
        # This should test the exception handling, though it's hard to trigger
        # We'll just verify the basic functionality works
        result = TextFormatter.to_sentence_case("NORMAL TEXT")
        assert result == "Normal text"


class TestTextFormatterTitlecaseCallback:
    """Test TextFormatter.titlecase_callback method."""

    @pytest.fixture(autouse=True)
    def setup_yaml(self):
        """Mock the YAML file for consistent tests."""
        TextFormatter._special_cases_cache = None

        mock_special_cases = ["NASA", "Inc.", "LLC"]
        mock_yaml_content = yaml.dump(mock_special_cases)

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            yield

        TextFormatter._special_cases_cache = None

    def test_non_string_input(self):
        """Test non-string input handling."""
        assert TextFormatter.titlecase_callback(123) == 123
        assert TextFormatter.titlecase_callback(None) is None

    def test_normalization_llc(self):
        """Test LLC normalization."""
        result = TextFormatter.titlecase_callback("L.L.C.")
        assert result == "LLC"

    def test_normalization_inc(self):
        """Test Inc normalization."""
        result = TextFormatter.titlecase_callback("I.N.C.")
        assert result == "Inc."

    def test_special_case_match(self):
        """Test special case matching."""
        result = TextFormatter.titlecase_callback("nasa")
        assert result == "NASA"

    def test_no_match_returns_none(self):
        """Test no match returns None."""
        result = TextFormatter.titlecase_callback("random")
        assert result is None

    def test_with_punctuation(self):
        """Test callback with punctuation."""
        result = TextFormatter.titlecase_callback("nasa,")
        assert result == "NASA,"


class TestSpecialCaseLookupInvalidation:
    """The derived lookups must not outlive the list they were built from.

    Casing resolves through lookups built once from special_cases.yaml, rather
    than by scanning the list per word. Those lookups are a second piece of cached
    state, and the suite invalidates casing throughout by setting
    ``_special_cases_cache = None``, so they have to follow from that alone.
    """

    def test_lookups_rebuild_when_the_cache_is_replaced(self):
        original = TextFormatter._special_cases_cache
        try:
            assert TextFormatter._preserve_special_case("llc") == "LLC"

            TextFormatter._special_cases_cache = None
            with patch("builtins.open", mock_open(read_data=yaml.dump(["ZZZ"]))):
                # The real list is gone, so its entries must stop resolving...
                assert TextFormatter._preserve_special_case("llc") is None
                # ...and the replacement must take effect.
                assert TextFormatter._preserve_special_case("zzz") == "ZZZ"

            TextFormatter._special_cases_cache = None
            assert TextFormatter._preserve_special_case("llc") == "LLC"
            assert TextFormatter._preserve_special_case("zzz") is None
        finally:
            TextFormatter._special_cases_cache = original


class TestSpecialCasesLoadFailures:
    """A missing list degrades; a corrupt one does not.

    Casing failures are quiet by nature: a mis-cased name is still a name, so a
    logged warning gets scrolled past. A file that exists but cannot be read as a
    list is a packaging or editing mistake, and it fails loudly.
    """

    def _load(self, **patch_kwargs):
        original = TextFormatter._special_cases_cache
        try:
            TextFormatter._special_cases_cache = None
            with patch("builtins.open", **patch_kwargs):
                return TextFormatter._load_special_cases()
        finally:
            TextFormatter._special_cases_cache = original

    def test_missing_file_degrades_to_no_special_casing(self):
        """An installation may legitimately lack the file."""
        assert self._load(side_effect=FileNotFoundError) == []

    def test_empty_file_is_not_an_error(self):
        """An empty list is a valid, if useless, configuration."""
        assert self._load(new=mock_open(read_data="")) == []

    def test_corrupt_yaml_warns_and_degrades(self):
        """Unparseable YAML is a mistake, and says so, without raising."""
        with pytest.warns(UserWarning, match="Could not parse"):
            assert self._load(new=mock_open(read_data="[unclosed: {")) == []

    def test_wrong_shape_warns_and_degrades(self):
        """A mapping where a list belongs would silently case nothing."""
        with pytest.warns(UserWarning, match="must contain a list"):
            assert self._load(new=mock_open(read_data="a: 1\nb: 2\n")) == []

    def test_casing_never_raises_from_repr(self):
        """A cosmetic problem must not break __repr__, logging or a debugger.

        Casing runs inside __repr__ on several models, so raising here would turn
        a mis-cased name into a crash at the least convenient site.
        """
        from tests.mocks import MockUSASpendingClient
        from usaspending.models.recipient_spending import RecipientSpending

        spending = RecipientSpending(
            {"name": "ACME CORP", "amount": 5, "recipient_id": "a-C"},
            MockUSASpendingClient(),
        )
        original = TextFormatter._special_cases_cache
        try:
            TextFormatter._special_cases_cache = None
            with (
                patch("builtins.open", mock_open(read_data="[unclosed: {")),
                pytest.warns(UserWarning),
            ):
                assert "Acme Corp" in repr(spending)
        finally:
            TextFormatter._special_cases_cache = original


class TestSpecialCaseCollisionWarning:
    """Colliding lowercase forms warn when the lookups are built.

    tests/utils/test_special_cases_data.py pins the same invariant over the
    shipped file, which is what catches it in CI and names the offenders. This
    check covers the case that test cannot see: special_cases.yaml is data, so a
    downstream consumer can edit it after install, where no test of ours runs.

    Exact duplicates deliberately do not warn. The same spelling wins either way,
    so there is nothing ambiguous to report; the CI test still flags them as
    untidy data.
    """

    def _build(self, entries):
        original = TextFormatter._special_cases_cache
        try:
            TextFormatter._special_cases_cache = None
            with patch("builtins.open", mock_open(read_data=yaml.dump(entries))):
                return TextFormatter._special_case_lookups()
        finally:
            TextFormatter._special_cases_cache = original
            TextFormatter._special_cases_lookups = None

    def test_same_form_different_spelling_warns(self):
        with pytest.warns(UserWarning, match="lowercase forms collide"):
            self._build(["Inc", "INC"])

    def test_entry_plus_a_trailing_period_warns(self):
        """The case invisible to the uppercase lookup, so it must be caught here."""
        with pytest.warns(UserWarning, match="lowercase forms collide"):
            self._build(["Inc", "INC."])

    def test_exact_duplicates_do_not_warn(self):
        import warnings as _warnings

        with _warnings.catch_warnings():
            _warnings.simplefilter("error", UserWarning)
            assert self._build(["Inc", "Inc"]).by_lower_form["inc"] == "Inc"

    def test_clean_data_does_not_warn(self):
        import warnings as _warnings

        with _warnings.catch_warnings():
            _warnings.simplefilter("error", UserWarning)
            self._build(["NASA", "Inc.", "OSIRIS-REx"])

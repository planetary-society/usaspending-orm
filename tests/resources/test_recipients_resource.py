from __future__ import annotations

from typing import Any

from tests.mocks.mock_client import MockUSASpendingClient


def seed_search_results(mock_usa_client, results: list[dict[str, Any]]) -> None:
    """Answer the recipient search with one page holding `results`."""
    mock_usa_client.set_response(
        MockUSASpendingClient.Endpoints.RECIPIENT_SEARCH,
        {"results": results, "page_metadata": {"hasNext": False}},
    )


class TestRecipientsResource:
    def test_find_by_duns_handles_missing_recipient_id(self, mock_usa_client):
        seed_search_results(mock_usa_client, [{"name": "Test Recipient"}])

        result = mock_usa_client.recipients.find_by_duns("123456789")

        assert result is not None
        assert result.recipient_id is None

    def test_find_by_uei_prefers_the_parent_level_result(self, mock_usa_client):
        """The parent record aggregates its children, so it wins over the others.

        The parent is deliberately last, so neither returning the first result
        nor returning the second can pass by looking like a preference.
        """
        seed_search_results(
            mock_usa_client,
            [
                {"recipient_id": "abc123-C", "name": "ACME Division"},
                {"recipient_id": "def456-R", "name": "ACME Regular"},
                {"recipient_id": "abc123-P", "name": "ACME Holdings"},
            ],
        )

        result = mock_usa_client.recipients.find_by_uei("UEI123456")

        assert result.recipient_id == "abc123-P"
        assert result.name == "ACME Holdings"

    def test_find_by_duns_falls_back_to_the_first_result(self, mock_usa_client):
        """With no parent among the results, the first match is the answer."""
        seed_search_results(
            mock_usa_client,
            [
                {"recipient_id": "abc123-C", "name": "ACME Division"},
                {"recipient_id": "def456-R", "name": "ACME Regular"},
            ],
        )

        result = mock_usa_client.recipients.find_by_duns("123456789")

        assert result.recipient_id == "abc123-C"

    def test_find_by_uei_returns_none_when_nothing_matches(self, mock_usa_client):
        """No results means no fallback either, rather than an empty model."""
        seed_search_results(mock_usa_client, [])

        assert mock_usa_client.recipients.find_by_uei("UEI123456") is None

    def test_find_by_uei_handles_missing_recipient_id(self, mock_usa_client):
        seed_search_results(mock_usa_client, [{"name": "Test Recipient"}])

        result = mock_usa_client.recipients.find_by_uei("UEI123456")

        assert result is not None
        assert result.recipient_id is None

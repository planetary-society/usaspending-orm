from __future__ import annotations

from tests.mocks.mock_client import MockUSASpendingClient


class TestRecipientsResource:
    def test_find_by_duns_handles_missing_recipient_id(self, mock_usa_client):
        response = {
            "results": [{"name": "Test Recipient"}],
            "page_metadata": {"hasNext": False},
        }
        mock_usa_client.set_response(MockUSASpendingClient.Endpoints.RECIPIENT_SEARCH, response)

        result = mock_usa_client.recipients.find_by_duns("123456789")

        assert result is not None
        assert result.recipient_id is None

    def test_find_by_uei_handles_missing_recipient_id(self, mock_usa_client):
        response = {
            "results": [{"name": "Test Recipient"}],
            "page_metadata": {"hasNext": False},
        }
        mock_usa_client.set_response(MockUSASpendingClient.Endpoints.RECIPIENT_SEARCH, response)

        result = mock_usa_client.recipients.find_by_uei("UEI123456")

        assert result is not None
        assert result.recipient_id is None

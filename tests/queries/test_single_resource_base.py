"""Tests for SingleResourceBase error handling."""

import pytest

from usaspending.exceptions import ValidationError
from usaspending.queries.single_resource_base import SingleResourceBase


class DummyResource(SingleResourceBase):
    @property
    def _endpoint(self) -> str:
        return "/dummy/"

    def find_by_id(self, resource_id: str):
        return self._get_resource(resource_id)

    def _clean_resource_id(self, resource_id: str) -> str:
        return ""


def test_get_resource_cleaning_error_message_is_formatted(mock_usa_client):
    resource = DummyResource(mock_usa_client)

    with pytest.raises(ValidationError) as exc_info:
        resource.find_by_id("test-id")

    message = str(exc_info.value)
    assert "Original: test-id" in message
    assert "Cleaned: " in message

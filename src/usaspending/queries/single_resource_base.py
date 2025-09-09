from ..exceptions import ValidationError
from ..client import USASpendingClient
from typing import Any
from abc import ABC, abstractmethod
from ..logging_config import USASpendingLogger

logger = USASpendingLogger.get_logger(__name__)


class SingleResourceBase(ABC):
    """
    Base class for retrieving single resources like awards or recipients,
    anything with a simple GET request, generally.
    """

    def __init__(self, client: USASpendingClient):
        self._client = client

    @property
    @abstractmethod
    def _endpoint(self) -> str:
        """Base endpoint for single resource retrieval."""
        pass

    @abstractmethod
    def find_by_id(self, resource_id: str) -> Any:
        """Filter by unique resource identifier."""
        pass

    def _get_resource(self, resource_id: str) -> dict:
        """Retrieve a single resource by ID."""
        if (
            not resource_id
            or not isinstance(resource_id, str)
            or not resource_id.strip()
        ):
            raise ValidationError("A non-empty resource_id string is required")

        # Clean recipient ID
        cleaned_resource_id = self._clean_resource_id(resource_id)

        if not cleaned_resource_id:
            raise ValidationError(
                "No resource id found after cleaning. Original: %s. Cleaned: %s",
                resource_id,
                cleaned_resource_id,
            )

        # Construct valid endpoint
        endpoint = self._construct_endpoint(cleaned_resource_id)

        # Make API request
        response = self._client._make_request("GET", endpoint)

        return response

    def _construct_endpoint(self, resource_id: str) -> str:
        """Construct the full endpoint URL for a specific resource ID."""
        return f"{self._endpoint}{resource_id}/"

    def _clean_resource_id(self, resource_id: str) -> str:
        """Very basic resource ID cleaning.

        More complex logic is implemented in specific resource classes.

        Args:
            resource_id: The raw resource ID string

        Returns:
            Cleaned resource ID string
        """
        return str(resource_id).strip()

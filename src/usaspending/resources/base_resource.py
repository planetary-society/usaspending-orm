from __future__ import annotations
from typing import TYPE_CHECKING

from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..client import USASpendingClient

logger = USASpendingLogger.get_logger(__name__)


class BaseResource:
    """Base class for API resources.

    Resources provide structured gateways to USASpending API endpoints
    and return appropriate query builders or model instances.
    """

    def __init__(self, client: USASpendingClient):
        """Initialize resource with client reference.

        Args:
            client: USASpendingClient client instance
        """
        self._client: USASpendingClient = client
        logger.debug(f"Initialized {self.__class__.__name__} resource")

    @property
    def client(self) -> USASpendingClient:
        """Get client instance."""
        return self._client

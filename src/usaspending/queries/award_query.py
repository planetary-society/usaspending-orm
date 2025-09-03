from typing import TYPE_CHECKING
from .single_resource_base import SingleResourceBase
from ..exceptions import ValidationError
from ..client import USASpending
from ..logging_config import USASpendingLogger

if TYPE_CHECKING:
    from ..models.award import Award

logger = USASpendingLogger.get_logger(__name__)


class AwardQuery(SingleResourceBase):
    """Retrieve a single-award from the USAspending API."""

    def __init__(self, client: USASpending):
        super().__init__(client)
        logger.debug("AwardQuery initialized with client: %s", client)

    @property
    def _endpoint(self) -> str:
        """Base endpoint for single award retrieval."""
        return "/awards/"

    def find_by_id(self, award_id: str) -> "Award":
        """Filter by unique award identifier."""
        return self.find_by_generated_id(award_id)

    def find_by_generated_id(self, award_id: str) -> "Award":
        """Filter by USASpending's internally generated unique award identifier."""
        if not award_id:
            raise ValidationError("award_id is required")

        # Make API request
        response = self._get_resource(award_id)

        # Create model instance using factory
        from ..models.award_factory import create_award

        return create_award(response, client=self._client)

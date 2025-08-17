# src/usaspending/resources/download_resource.py

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from .base_resource import BaseResource
from ..logging_config import USASpendingLogger
# Import the manager and type aliases
from ..download.manager import DownloadManager, FileFormat
from ..download.job import DownloadJob
from ..models.download import DownloadStatus

if TYPE_CHECKING:
    from ..client import USASpending

logger = USASpendingLogger.get_logger(__name__)

class DownloadResource(BaseResource):
    """Resource for award data download operations."""

    def __init__(self, client: USASpending):
        super().__init__(client)
        self._manager = DownloadManager(client)

    def contract(self, award_id: str, file_format: FileFormat = "csv", destination_dir: Optional[str] = None) -> DownloadJob:
        """
        Queue a download job for contract award data.

        Args:
            award_id: The unique award identifier (e.g., CONT_AWD_...).
            file_format: Format of the file (csv, tsv, pstxt).
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            A DownloadJob object. Use job.wait_for_completion() to block until finished.
        """
        return self._manager.queue_download("contract", award_id, file_format, destination_dir)

    def assistance(self, award_id: str, file_format: FileFormat = "csv", destination_dir: Optional[str] = None) -> DownloadJob:
        """
        Queue a download job for assistance award data.

        Args:
            award_id: The unique award identifier (e.g., ASST_NON_...).
            file_format: Format of the file (csv, tsv, pstxt).
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            A DownloadJob object. Use job.wait_for_completion() to block until finished.
        """
        return self._manager.queue_download("assistance", award_id, file_format, destination_dir)

    def status(self, file_name: str) -> DownloadStatus:
        """
        Check the status of a specific download job directly via the API.
        
        Note: Using DownloadJob.refresh_status() is generally preferred.

        Args:
            file_name: The name of the file returned by the download request.

        Returns:
            The DownloadStatus model representation.
        """
        return self._manager.check_status(file_name)
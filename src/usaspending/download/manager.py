# src/usaspending/download/manager.py

from __future__ import annotations
import zipfile
import os
from typing import TYPE_CHECKING, Optional, List

from ..exceptions import APIError, DownloadError
from ..logging_config import USASpendingLogger
from ..models.download import DownloadStatus, AwardType, FileFormat

if TYPE_CHECKING:
    from ..client import USASpending
    from .job import DownloadJob

logger = USASpendingLogger.get_logger(__name__)

class DownloadManager:
    """Handles the core logic for queuing, monitoring, downloading, and processing award data."""

    BASE_ENDPOINT = "/v2/download/"

    def __init__(self, client: USASpending):
        self._client = client

    def queue_download(self, download_type: AwardType, award_id: str, file_format: FileFormat, destination_dir: Optional[str]) -> DownloadJob:
        """
        Sends the initial request to the API to start the download job.
        """

        endpoint = f"{self.BASE_ENDPOINT}{download_type}/"
        payload = {
            "award_id": award_id,
            "file_format": file_format
        }

        logger.info(f"Queueing {download_type} download for award {award_id} (Format: {file_format})")
        
        try:
            response_data = self._client._make_uncached_request("POST", endpoint, json=payload)
        except APIError as e:
            logger.error(f"Failed to queue download for award {award_id}: {e}")
            raise DownloadError(f"Failed to queue download: {e}") from e

        # Import DownloadJob here to avoid circular dependency
        from .job import DownloadJob
        
        file_name = response_data.get("file_name")
        if not file_name:
             raise DownloadError("API response missing required field 'file_name'.")

        job = DownloadJob(
            manager=self,
            file_name=file_name,
            initial_file_url=response_data.get("file_url"),
            request_details=response_data.get("download_request"),
            destination_dir=destination_dir
        )
        
        return job

    def check_status(self, file_name: str) -> DownloadStatus:
        """
        Checks the status of a download job via the API.
        """
        endpoint = f"{self.BASE_ENDPOINT}status"
        params = {"file_name": file_name}
        
        # Never cache this endpoint
        response_data = self._client._make_uncached_request("GET", endpoint, params=params)
        return DownloadStatus(response_data)

    def download_file(self, file_url: str, destination_path: str, file_name: str) -> None:
        """
        Downloads the zipped file from the provided URL using the client's binary download method.
        
        This delegates to the client's _download_binary_file method which handles:
        - Session management with proper headers
        - Retry logic with exponential backoff
        - Streaming for large files
        - Cleanup of partial downloads on failure
        """
        logger.info(f"Initiating download of {file_name}")
        
        try:
            # Use the client's binary download method for consistency
            self._client._download_binary_file(file_url, destination_path)
            
        except Exception as e:
            # Log with file_name context
            logger.error(f"Failed to download file {file_name}: {e}")
            # Ensure the exception includes the file_name
            if hasattr(e, 'file_name') and not e.file_name:
                e.file_name = file_name
            raise

    def unzip_file(self, zip_path: str, extract_dir: str) -> List[str]:
        """
        Unzips the downloaded file.
        """
        logger.info(f"Unzipping {zip_path} to {extract_dir}")
        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                extracted_files = zip_ref.namelist()
                zip_ref.extractall(extract_dir)
            
            logger.info(f"Successfully extracted {len(extracted_files)} files.")
            return [os.path.join(extract_dir, f) for f in extracted_files]

        except zipfile.BadZipFile:
            raise DownloadError(f"Downloaded file is not a valid zip archive: {zip_path}", file_name=os.path.basename(zip_path))
        except Exception as e:
            raise DownloadError(f"An error occurred during unzipping: {e}", file_name=os.path.basename(zip_path)) from e
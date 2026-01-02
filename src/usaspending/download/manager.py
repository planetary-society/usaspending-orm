# src/usaspending/download/manager.py
"""
This module defines the DownloadManager class, responsible for orchestrating the
download process of award data from the USASpending API. It handles queuing
download requests, checking their status, downloading the completed files,
and extracting their contents.
"""

from __future__ import annotations

import os
import zipfile
from typing import TYPE_CHECKING

from ..exceptions import APIError, DownloadError
from ..logging_config import USASpendingLogger
from ..models.download import AwardType, DownloadStatus, FileFormat

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from .job import DownloadJob

logger = USASpendingLogger.get_logger(__name__)


class DownloadManager:
    """Handles the core logic for queuing, monitoring, downloading, and processing award data."""

    BASE_ENDPOINT = "/download/"

    def __init__(self, client: USASpendingClient):
        self._client = client

    def queue_download(
        self,
        download_type: AwardType,
        award_id: str,
        file_format: FileFormat,
        destination_dir: str | None,
    ) -> DownloadJob:
        """
        Sends the initial request to the API to start the download job.
        """

        endpoint = f"{self.BASE_ENDPOINT}{download_type}/"
        payload = {"award_id": award_id, "file_format": file_format}

        logger.info(
            f"Queueing {download_type} download for award {award_id} (Format: {file_format})"
        )

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
            destination_dir=destination_dir,
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
            if hasattr(e, "file_name") and not e.file_name:
                e.file_name = file_name
            raise

    def unzip_file(self, zip_path: str, extract_dir: str) -> list[str]:
        """
        Unzips the downloaded file with path traversal protection.

        This method validates that all files in the ZIP archive extract to
        paths within the specified extract_dir, preventing ZipSlip attacks
        where malicious archives contain entries like "../../../etc/passwd".

        Args:
            zip_path: Path to the ZIP file to extract.
            extract_dir: Directory where contents will be extracted.

        Returns:
            List of absolute paths to extracted files.

        Raises:
            DownloadError: If the ZIP contains path traversal attempts,
                          is not a valid archive, or extraction fails.
        """
        logger.info(f"Unzipping {zip_path} to {extract_dir}")

        # Resolve to absolute path for security comparison
        extract_dir = os.path.realpath(extract_dir)

        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Validate all paths before extraction (ZipSlip protection)
                for member in zip_ref.namelist():
                    member_path = os.path.realpath(os.path.join(extract_dir, member))
                    # Ensure extracted path is within extract_dir
                    if (
                        not member_path.startswith(extract_dir + os.sep)
                        and member_path != extract_dir
                    ):
                        raise DownloadError(
                            f"Attempted path traversal in ZIP archive: {member}",
                            file_name=os.path.basename(zip_path),
                        )

                extracted_files = zip_ref.namelist()
                zip_ref.extractall(extract_dir)

            logger.info(f"Successfully extracted {len(extracted_files)} files.")
            return [os.path.join(extract_dir, f) for f in extracted_files]

        except zipfile.BadZipFile:
            raise DownloadError(
                f"Downloaded file is not a valid zip archive: {zip_path}",
                file_name=os.path.basename(zip_path),
            ) from None
        except DownloadError:
            # Re-raise DownloadError (including path traversal errors)
            raise
        except Exception as e:
            raise DownloadError(
                f"An error occurred during unzipping: {e}",
                file_name=os.path.basename(zip_path),
            ) from e

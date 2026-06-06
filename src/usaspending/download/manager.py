# src/usaspending/download/manager.py
"""
This module defines the DownloadManager class, responsible for orchestrating the
download process of award data from the USASpending API. It handles queuing
download requests, checking their status, downloading the completed files,
and extracting their contents.
"""

from __future__ import annotations

import ntpath
import os
import posixpath
import zipfile
from typing import TYPE_CHECKING, Any

from ..exceptions import APIError, DownloadError
from ..logging_config import USASpendingLogger
from ..models.download import AwardType, DownloadStatus, FileFormat, SpendingLevel

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
        payload: dict[str, Any] = {"award_id": award_id, "file_format": file_format}

        logger.info(
            f"Queueing {download_type} download for award {award_id} (Format: {file_format})"
        )

        return self._post_and_build_job(endpoint, payload, destination_dir)

    def queue_search_download(
        self,
        filters: dict[str, Any],
        *,
        file_format: FileFormat = "csv",
        spending_level: list[SpendingLevel] | None = None,
        columns: list[str] | None = None,
        limit: int | None = None,
        destination_dir: str | None = None,
    ) -> DownloadJob:
        """
        Queues a download combining award, transaction, and subaward data.

        Sends a request to the ``/download/search/`` endpoint, which generates a single
        zip file of records matching the supplied search filters.

        Args:
            filters: The standard search ``filters`` object, as built by an
                ``AwardsSearch`` query (see ``QueryBuilder.to_filters_payload``).
            file_format: Format of the file(s) in the zip (csv, tsv, pstxt).
            spending_level: Which datasets to include. When None, the API includes all
                of awards, transactions, and subawards.
            columns: Specific columns to include. When None, the API returns its default
                column set.
            limit: Maximum number of records to include. When None, the API default applies.
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            A DownloadJob object. Use job.wait_for_completion() to block until finished.
        """
        endpoint = f"{self.BASE_ENDPOINT}search/"
        payload: dict[str, Any] = {"filters": filters, "file_format": file_format}
        if spending_level is not None:
            payload["spending_level"] = spending_level
        if columns is not None:
            payload["columns"] = columns
        if limit is not None:
            payload["limit"] = limit

        logger.info(
            f"Queueing search download (Format: {file_format}, Levels: {spending_level or 'all'})"
        )

        return self._post_and_build_job(endpoint, payload, destination_dir)

    def _post_and_build_job(
        self,
        endpoint: str,
        payload: dict[str, Any],
        destination_dir: str | None,
    ) -> DownloadJob:
        """
        POSTs a download request and builds a DownloadJob from the response.

        Shared by the single-award and search download paths.

        Args:
            endpoint: The download endpoint to POST to.
            payload: The JSON request body.
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            A DownloadJob tracking the queued download.

        Raises:
            DownloadError: If the request fails or the response omits 'file_name'.
        """
        try:
            response_data = self._client._make_uncached_request("POST", endpoint, json=payload)
        except APIError as e:
            logger.error(f"Failed to queue download via {endpoint}: {e}")
            raise DownloadError(f"Failed to queue download: {e}") from e

        # Import DownloadJob here to avoid circular dependency
        from .job import DownloadJob

        file_name = response_data.get("file_name")
        if not file_name:
            raise DownloadError("API response missing required field 'file_name'.")

        return DownloadJob(
            manager=self,
            file_name=file_name,
            initial_file_url=response_data.get("file_url"),
            request_details=response_data.get("download_request"),
            destination_dir=destination_dir,
        )

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

        # Resolve to absolute path for security comparison.
        extract_dir = os.path.realpath(extract_dir)

        # Create with restrictive permissions so extracted CSVs are not
        # readable/writable by other local users on shared hosts.
        os.makedirs(extract_dir, mode=0o700, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # ZipSlip protection: reject absolute paths (POSIX or Windows,
                # including drive letters and UNC prefixes) and any relative
                # member that normalizes outside extract_dir. Because
                # extract_dir was realpath'd above, normpath is sufficient
                # and avoids per-member stat syscalls.
                extract_prefix = extract_dir + os.sep
                for member in zip_ref.namelist():
                    if posixpath.isabs(member) or ntpath.isabs(member):
                        raise DownloadError(
                            f"Refusing absolute path in ZIP archive: {member}",
                            file_name=os.path.basename(zip_path),
                        )
                    member_path = os.path.normpath(os.path.join(extract_dir, member))
                    if member_path != extract_dir and not member_path.startswith(extract_prefix):
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

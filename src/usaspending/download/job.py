# src/usaspending/download/job.py

from __future__ import annotations
import time
import os
from typing import TYPE_CHECKING, Dict, Any, Optional, List

from ..exceptions import DownloadError, APIError
from ..logging_config import USASpendingLogger
from ..models.download import DownloadStatus, DownloadState

if TYPE_CHECKING:
    from .manager import DownloadManager

logger = USASpendingLogger.get_logger(__name__)

class DownloadJob:
    """
    Represents a single award data download task, managing its lifecycle (polling, downloading, extraction).
    """
    
    DEFAULT_POLL_INTERVAL = 30 # seconds
    DEFAULT_TIMEOUT = 1800 # 30 minutes

    def __init__(self, manager: DownloadManager, file_name: str, initial_file_url: Optional[str], request_details: Optional[Dict[str, Any]], destination_dir: Optional[str] = None):
        self._manager = manager
        self.file_name = file_name
        self._initial_file_url = initial_file_url # URL provided at initiation
        self.request_details = request_details
        self.destination_dir = destination_dir or os.getcwd()
        
        self._status_details: Optional[DownloadStatus] = None
        self._state: DownloadState = DownloadState.PENDING
        self._result_files: Optional[List[str]] = None
        self._error_message: Optional[str] = None

    @property
    def state(self) -> DownloadState:
        """Current state of the job."""
        return self._state

    @property
    def status_details(self) -> Optional[DownloadStatus]:
        """Detailed status information from the API (cached)."""
        return self._status_details

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @property
    def result_files(self) -> Optional[List[str]]:
        """List of extracted file paths upon successful completion."""
        return self._result_files
    
    @property
    def is_complete(self) -> bool:
        """True if the job is finished (success or failure)."""
        return self._state in [DownloadState.FINISHED, DownloadState.FAILED]

    def refresh_status(self) -> DownloadState:
        """Polls the API for the latest status and updates the internal state."""
        if self.is_complete:
            return self._state

        logger.debug(f"Checking status for {self.file_name}...")
        try:
            self._status_details = self._manager.check_status(self.file_name)
            self._state = self._status_details.api_status
            
            if self._state == DownloadState.FAILED:
                self._error_message = self._status_details.message or "API reported failure."
            
            return self._state

        except APIError as e:
            # Handle transient API errors during polling without failing the job immediately
            logger.warning(f"API Error checking status for {self.file_name}: {e}. Will retry.")
            return self._state # Return previous state
        except Exception as e:
            logger.error(f"Unexpected error checking status for {self.file_name}: {e}")
            self._error_message = f"Status check failed: {e}"
            self._state = DownloadState.FAILED
            return self._state

    def wait_for_completion(self, timeout: int = DEFAULT_TIMEOUT, poll_interval: int = DEFAULT_POLL_INTERVAL, cleanup_zip: bool = False) -> List[str]:
        """
        Blocks until the download is complete, then downloads and unzips the file.
        """
        logger.info(f"Waiting for download job {self.file_name}. Timeout: {timeout}s. Polling every {poll_interval}s.")
        start_time = time.time()

        while True:
            current_state = self.refresh_status()
            
            if current_state == DownloadState.FINISHED:
                logger.info(f"Download job finished. Total wait time: {time.time() - start_time:.2f}s. Proceeding to process.")
                return self._process_download(cleanup_zip)
            
            if current_state == DownloadState.FAILED:
                raise DownloadError(f"Download job failed: {self.error_message}", file_name=self.file_name, status=DownloadState.FAILED.value)

            if time.time() - start_time > timeout:
                self._state = DownloadState.FAILED
                self._error_message = f"Timeout waiting for download job after {timeout} seconds."
                raise DownloadError(self._error_message, file_name=self.file_name, status="timeout")

            logger.info(f"Job status: {current_state.value}. Waiting...")
            time.sleep(poll_interval)

    def _process_download(self, cleanup_zip: bool) -> List[str]:
        """Downloads the finished file, unzips it, and optionally cleans up the zip."""
        os.makedirs(self.destination_dir, exist_ok=True)
            
        zip_path = os.path.join(self.destination_dir, self.file_name)
        
        # Create a subdirectory for extraction based on the filename (without .zip)
        extract_subdir_name = os.path.splitext(self.file_name)[0]
        extract_path = os.path.join(self.destination_dir, extract_subdir_name)

        try:
            # Use the latest file_url from the status details if available, fallback to initial URL
            final_url = self._status_details.file_url if self._status_details else self._initial_file_url
            
            if not final_url:
                raise DownloadError("File URL is missing, cannot download.", file_name=self.file_name)

            self._manager.download_file(final_url, zip_path, self.file_name)
            self._result_files = self._manager.unzip_file(zip_path, extract_path)
            
            if cleanup_zip:
                logger.info(f"Cleaning up zip file: {zip_path}")
                try:
                    os.remove(zip_path)
                except OSError as e:
                    logger.warning(f"Could not remove zip file {zip_path}: {e}")
                
            return self._result_files

        except DownloadError as e:
            self._error_message = str(e)
            self._state = DownloadState.FAILED
            raise
        except Exception as e:
            self._error_message = f"Error during file download or extraction: {e}"
            self._state = DownloadState.FAILED
            raise DownloadError(self._error_message, file_name=self.file_name) from e

    def __repr__(self) -> str:
        return f"<DownloadJob file_name='{self.file_name}' state='{self.state.value}'>"
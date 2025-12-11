# src/usaspending/models/download.py

from __future__ import annotations
from typing import Optional, Literal
from enum import Enum

from ..utils.formatter import to_float, to_int
from .base_model import BaseModel

AwardType = Literal["contract", "assistance", "idv"]
FileFormat = Literal["csv", "tsv", "pstxt"]


class DownloadState(Enum):
    """Enumeration for download job states."""

    PENDING = "pending"  # Custom state before first API check
    READY = "ready"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    UNKNOWN = "unknown"  # Custom state if API returns unexpected value


class DownloadStatus(BaseModel):
    """Represents the status details of a download job returned by the API."""

    @property
    def file_name(self) -> Optional[str]:
        """Name of the downloaded file.

        Returns:
            Optional[str]: The file name, or None.
        """
        return self.get_value("file_name")

    @property
    def message(self) -> Optional[str]:
        """Error message if the status is failed.

        Returns:
            Optional[str]: A human readable error message, or None.
        """
        return self.get_value("message")

    @property
    def seconds_elapsed(self) -> Optional[float]:
        """Time elapsed for the download job.

        Returns:
            Optional[float]: Time in seconds, or None.
        """
        return to_float(self.get_value("seconds_elapsed"))

    @property
    def api_status(self) -> DownloadState:
        """Current state of the request from the API.

        Returns:
            DownloadState: The current download state.
        """
        status_str = self.get_value("status")
        if status_str:
            try:
                return DownloadState(status_str)
            except ValueError:
                return DownloadState.UNKNOWN
        return DownloadState.UNKNOWN

    @property
    def total_columns(self) -> Optional[int]:
        """Total number of columns in the result.

        Returns:
            Optional[int]: The column count, or None.
        """
        return to_int(self.get_value("total_columns"))

    @property
    def total_rows(self) -> Optional[int]:
        """Total number of rows in the result.

        Returns:
            Optional[int]: The row count, or None.
        """
        return to_int(self.get_value("total_rows"))

    @property
    def total_size_kb(self) -> Optional[float]:
        """Estimated file size in kilobytes.

        Returns:
            Optional[float]: The file size in KB, or None.
        """
        return to_float(self.get_value("total_size"))

    @property
    def file_url(self) -> Optional[str]:
        """URL for the file (relative path).

        Returns:
            Optional[str]: The file URL, or None.
        """
        return self.get_value("file_url")

    def __repr__(self) -> str:
        """String representation of DownloadStatus.

        Returns:
            str: String containing status and file name.
        """
        return (
            f"<DownloadStatus status='{self.api_status.value}' file='{self.file_name}'>"
        )
